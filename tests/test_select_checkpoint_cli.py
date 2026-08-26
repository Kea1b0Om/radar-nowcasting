"""End-to-end offline test of the selector CLI: fabricated dumps, no GPU.

Exercises the guards that stop an invalid comparison from silently
producing a ranking, and checks that the frozen selector picks the
checkpoint the balanced score prefers rather than the one the wet-dominated
micro average prefers.
"""

import json
import os
import subprocess
import sys

import numpy as np
import pytest

sys.path.append(os.getcwd())

from tools.selection_rule import THRESHOLDS_CIKM, SelectionRule

N_DRY, N_WET = 90, 10
N_EVENTS = N_DRY + N_WET
T, Q = 2, 4


def _rule(tmp_path):
    sev = np.concatenate([np.full(N_DRY, 0.05), np.full(N_WET, 2.5)])
    strata = np.array([0] * N_DRY + [1] * N_WET)
    is_dev = np.zeros(N_EVENTS, dtype=int)
    is_dev[0:N_DRY:2] = 1                      # half the dry events
    is_dev[N_DRY:N_EVENTS:2] = 1               # half the wet events
    r = SelectionRule(
        schema_version=1, dataset_name="cikm", thresholds=list(THRESHOLDS_CIKM),
        pixel_scale=90.0, crop=[13, -14], n_strata_requested=2,
        boundaries=[1.0], n_strata_realised=2, stratum_weights="equal",
        empty_cell_policy="exclude", split_seed=1, frac_dev=0.5,
        selector_order=["balanced", "micro_csi_m", "fair_crps", "mse"],
        epsilon_rule="1 SE", bootstrap_B=200, bootstrap_seed=2,
        stage1_samples=1, stage2_samples=8, stage1_batch_size=8,
        stage2_batch_size=4, euler_steps=10, dtype="float32",
        seed_formula="base_seed + batch_index * S + sample_index",
        base_seed=42, train_h5_sha256="a" * 64, val_h5_sha256="b" * 64,
        created_utc="2026-08-01T00:00:00Z", notes="test",
        val_event_id=list(range(N_EVENTS)), val_file_row=list(range(N_EVENTS)),
        val_severity=sev.tolist(), val_stratum=strata.tolist(),
        val_is_dev=is_dev.tolist(),
    )
    path = str(tmp_path / "rule.json")
    r.save(path)
    return path, r, sev


def _write_dump(out_dir, name, rule, sev, dry_tp, wet_tp, mse, crps,
                protocol_override=None, severity_override=None):
    os.makedirs(out_dir, exist_ok=True)
    tp = np.concatenate([np.full((N_DRY, T, Q), dry_tp),
                         np.full((N_WET, T, Q), wet_tp)]).astype(np.int64)
    fn = np.concatenate([np.full((N_DRY, T, Q), 10 - dry_tp),
                         np.full((N_WET, T, Q), 1000 - wet_tp)]).astype(np.int64)
    fp = np.zeros_like(tp)
    tn = np.full_like(tp, 10000)
    npix = np.full((N_EVENTS, T), 10201.0)
    npz = os.path.join(out_dir, f"stage1__{name}.npz")
    np.savez_compressed(
        npz,
        event_id=np.arange(N_EVENTS, dtype=np.int64),
        member_seed=np.zeros((N_EVENTS, 1), np.int64),
        severity_check=(severity_override if severity_override is not None else sev),
        tp=tp, fn=fn, fp=fp, tn=tn,
        tp_pool=tp // 10, fn_pool=fn // 10, fp_pool=fp,
        sse=npix * mse, npix=npix,
        crps_sum=npix * crps, spread_sum=np.zeros((N_EVENTS, T)),
    )
    manifest = {
        "dump_schema_version": 1, "stage": 1,
        "checkpoint_path": f"/fake/{name}.pt", "checkpoint_sha256": "c" * 64,
        "checkpoint_type": "ema", "checkpoint_epoch": 100,
        "checkpoint_global_step": 12345, "checkpoint_best_metric": 0.7,
        "mean": 0.0, "std": 1.0,
        "samples": 1, "batch_size": 8, "euler_steps": 10,
        "num_train_timesteps": 1000, "dtype": "float32",
        "seed_formula": rule.seed_formula, "base_seed": 42,
        "thresholds": list(THRESHOLDS_CIKM), "pixel_scale": 90.0,
        "crop": [13, -14], "pool_size": 16, "crps_estimator": "almost_fair",
        "n_events": N_EVENTS, "rule_sha256": rule.payload_hash(),
        "config": "/fake/config.yaml", "created_utc": "2026-08-01T00:00:00Z",
        "wall_seconds": 1.0,
    }
    if protocol_override:
        manifest.update(protocol_override)
    with open(npz.replace(".npz", ".json"), "w") as f:
        json.dump(manifest, f)
    return npz


def _run(rule_path, dumps_glob, report, extra=()):
    return subprocess.run(
        [sys.executable, "tools/select_checkpoint.py",
         "--rule", rule_path, "--dumps", dumps_glob, "--report", report, *extra],
        capture_output=True, text=True, cwd=os.getcwd(),
    )


def test_selector_prefers_the_balanced_winner(tmp_path):
    rule_path, rule, sev = _rule(tmp_path)
    d = str(tmp_path / "dumps")
    # A: better on the 10 wet events, worse on the 90 dry ones -> wins micro
    _write_dump(d, "ckpt_A", rule, sev, dry_tp=4, wet_tp=800, mse=50.0, crps=5.0)
    # B: better on dry -> wins the equal-weight balanced score
    _write_dump(d, "ckpt_B", rule, sev, dry_tp=7, wet_tp=700, mse=60.0, crps=5.5)
    report = str(tmp_path / "report.md")
    r = _run(rule_path, os.path.join(d, "stage1__*.npz"), report)
    assert r.returncode == 0, r.stderr
    assert os.path.exists(report)
    sel = json.load(open(report.replace(".md", "") + "_selected.json"))
    assert sel["selected_checkpoint"].endswith("ckpt_B.pt")
    assert "## per-stratum CSI on dev" in open(report).read()
    assert "shadow split" in open(report).read()


def test_incumbent_comparison_reports_a_paired_interval(tmp_path):
    rule_path, rule, sev = _rule(tmp_path)
    d = str(tmp_path / "dumps")
    _write_dump(d, "ckpt_A", rule, sev, dry_tp=4, wet_tp=800, mse=50.0, crps=5.0)
    _write_dump(d, "ckpt_B", rule, sev, dry_tp=7, wet_tp=700, mse=60.0, crps=5.5)
    report = str(tmp_path / "report.md")
    r = _run(rule_path, os.path.join(d, "stage1__*.npz"), report,
             extra=("--incumbent", "ckpt_A"))
    assert r.returncode == 0, r.stderr
    text = open(report).read()
    assert "vs incumbent" in text
    assert "P(delta>0)" in text


def test_protocol_mismatch_is_refused(tmp_path):
    rule_path, rule, sev = _rule(tmp_path)
    d = str(tmp_path / "dumps")
    _write_dump(d, "ckpt_A", rule, sev, 4, 800, 50.0, 5.0)
    _write_dump(d, "ckpt_B", rule, sev, 7, 700, 60.0, 5.5,
                protocol_override={"euler_steps": 4})
    r = _run(rule_path, os.path.join(d, "stage1__*.npz"),
             str(tmp_path / "r.md"))
    assert r.returncode != 0
    assert "euler_steps" in (r.stdout + r.stderr)


def test_mixed_checkpoint_types_are_refused(tmp_path):
    rule_path, rule, sev = _rule(tmp_path)
    d = str(tmp_path / "dumps")
    _write_dump(d, "ckpt_A", rule, sev, 4, 800, 50.0, 5.0)
    _write_dump(d, "ckpt_B", rule, sev, 7, 700, 60.0, 5.5,
                protocol_override={"checkpoint_type": "raw"})
    r = _run(rule_path, os.path.join(d, "stage1__*.npz"), str(tmp_path / "r.md"))
    assert r.returncode != 0
    assert "mixed checkpoint types" in (r.stdout + r.stderr)


def test_dump_scored_against_different_data_is_refused(tmp_path):
    rule_path, rule, sev = _rule(tmp_path)
    d = str(tmp_path / "dumps")
    _write_dump(d, "ckpt_A", rule, sev, 4, 800, 50.0, 5.0)
    _write_dump(d, "ckpt_B", rule, sev, 7, 700, 60.0, 5.5,
                severity_override=sev + 0.01)
    r = _run(rule_path, os.path.join(d, "stage1__*.npz"), str(tmp_path / "r.md"))
    assert r.returncode != 0
    assert "recomputed severity" in (r.stdout + r.stderr)


def test_dump_from_another_rule_is_refused(tmp_path):
    rule_path, rule, sev = _rule(tmp_path)
    d = str(tmp_path / "dumps")
    _write_dump(d, "ckpt_A", rule, sev, 4, 800, 50.0, 5.0)
    _write_dump(d, "ckpt_B", rule, sev, 7, 700, 60.0, 5.5,
                protocol_override={"rule_sha256": "f" * 64})
    r = _run(rule_path, os.path.join(d, "stage1__*.npz"), str(tmp_path / "r.md"))
    assert r.returncode != 0
    assert "different selection rule" in (r.stdout + r.stderr)


def test_single_checkpoint_pool_still_produces_a_report(tmp_path):
    """The realistic case today: only one EMA snapshot survived."""
    rule_path, rule, sev = _rule(tmp_path)
    d = str(tmp_path / "dumps")
    _write_dump(d, "only_one", rule, sev, 5, 750, 55.0, 5.2)
    report = str(tmp_path / "r.md")
    r = _run(rule_path, os.path.join(d, "stage1__*.npz"), report,
             extra=("--incumbent", "only_one"))
    assert r.returncode == 0, r.stderr
    assert "no free gain available from reselection" in open(report).read()
