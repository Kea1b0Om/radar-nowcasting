"""Tests for tools/verifier_rank_gate.py.

The anchors that matter:

* ``realised_selection`` with ``score = target`` must recover **exactly** 1.0 -
  argmax of the selection target *is* the oracle, so any deviation means the
  oracle arm and the selection path disagree, and every recovery fraction in the
  report would be silently mis-scaled.
* ``within_event_spearman`` must equal scipy's ``spearmanr`` event by event,
  including the tie case - the vectorised Pearson-on-ranks shortcut is only valid
  with average ranks.
* pooled CSI must be sum-then-ratio, not mean-of-ratios, matching
  ``tools/score_gate_arms.py``; the two statistics differ and the repository
  reports the former.
"""

import json
import os
import subprocess
import sys
import tempfile

import h5py
import numpy as np
import pytest
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.verifier_rank_gate import (  # noqa: E402
    THRESHOLDS,
    RadialBinner,
    advantage_diagnostics,
    avg_rank,
    contingency,
    event_bootstrap_mean,
    per_event_csi,
    pooled_csi,
    rank_center,
    realised_selection,
    ridge_critic_cv,
    selection_arms,
    within_event_spearman,
)


# ---------------------------------------------------------------- primitives
def test_contingency_matches_naive_counts():
    rng = np.random.default_rng(0)
    pred = rng.uniform(0, 60, size=(3, 16, 16)).astype(np.float32)
    obs = rng.uniform(0, 60, size=(3, 16, 16)).astype(np.float32)
    for thr in (20.0, 35.0):
        tp, fp, fn = contingency(pred, obs, thr)
        p, o = pred >= thr, obs >= thr
        assert tp == float(np.sum(p & o))
        assert fp == float(np.sum(p & ~o))
        assert fn == float(np.sum(~p & o))


def test_contingency_uses_ge_convention():
    pred = np.full((1, 2, 2), 35.0, dtype=np.float32)
    obs = np.full((1, 2, 2), 35.0, dtype=np.float32)
    tp, fp, fn = contingency(pred, obs, 35.0)
    assert (tp, fp, fn) == (4.0, 0.0, 0.0)


def test_per_event_csi_nan_only_when_nothing_happens():
    tp = np.array([[0.0, 5.0]])
    fp = np.array([[0.0, 1.0]])
    fn = np.array([[0.0, 2.0]])
    csi = per_event_csi(tp, fp, fn)
    assert np.isnan(csi[0, 0])
    assert csi[0, 1] == pytest.approx(5.0 / 8.0)


def test_pooled_csi_is_sum_then_ratio_not_mean_of_ratios():
    tp = np.array([1.0, 100.0])
    fp = np.array([1.0, 0.0])
    fn = np.array([0.0, 0.0])
    pooled = pooled_csi(tp, fp, fn)
    mean_of_ratios = np.mean([1 / 2, 100 / 100])
    assert pooled == pytest.approx(101.0 / 102.0)
    assert pooled != pytest.approx(mean_of_ratios)


def test_radial_binner_frequency_grid_is_symmetric():
    """A row-index construction would break the negative-frequency half."""
    b = RadialBinner(16, 16, n_bins=8)
    assert b.counts.sum() == 16 * 16
    # DC lives alone in the innermost bin
    assert b.index[0] == 0
    # bin index must be invariant to the fftshift-symmetric pairing (i, -i)
    idx = b.index.reshape(16, 16)
    assert idx[1, 0] == idx[15, 0]
    assert idx[0, 3] == idx[0, 13]


def test_radial_binner_flat_field_has_power_only_at_dc():
    b = RadialBinner(32, 32, n_bins=8)
    lp = b.log_power(np.ones((2, 32, 32), dtype=np.float32))
    assert lp[0] > lp[1:].max() + 5.0


# ---------------------------------------------------------------- ranking
def test_avg_rank_shares_ties():
    x = np.array([[1.0, 1.0, 3.0, 4.0]])
    assert avg_rank(x)[0].tolist() == [1.5, 1.5, 3.0, 4.0]


def test_within_event_spearman_matches_scipy_including_ties():
    rng = np.random.default_rng(7)
    feat = rng.normal(size=(25, 8))
    targ = rng.normal(size=(25, 8))
    feat[3, :4] = 0.5  # plant ties
    targ[9, 2:5] = -1.0
    got = within_event_spearman(feat, targ)
    for i in range(feat.shape[0]):
        assert got[i] == pytest.approx(spearmanr(feat[i], targ[i]).statistic, abs=1e-12)


def test_within_event_spearman_nan_when_feature_constant():
    feat = np.zeros((1, 8))
    targ = np.arange(8.0)[None, :]
    assert np.isnan(within_event_spearman(feat, targ)[0])


def test_within_event_spearman_skips_events_with_nan_target():
    feat = np.tile(np.arange(8.0), (2, 1))
    targ = np.tile(np.arange(8.0), (2, 1))
    targ[1, 0] = np.nan
    got = within_event_spearman(feat, targ)
    assert got[0] == pytest.approx(1.0)
    assert np.isnan(got[1])


def test_rank_center_is_symmetric_and_scaled():
    r = rank_center(np.arange(8.0)[None, :])
    assert r.mean() == pytest.approx(0.0)
    assert r.min() == pytest.approx(-1.0)
    assert r.max() == pytest.approx(1.0)


def test_event_bootstrap_mean_brackets_the_mean():
    v = np.random.default_rng(1).normal(0.4, 0.1, size=500)
    out = event_bootstrap_mean(v, iterations=500, seed=3)
    assert out["ci_low"] < out["mean"] < out["ci_high"]
    assert out["n"] == 500


# ---------------------------------------------------------------- arms
def _toy_acc(n=40, m=6, seed=0):
    """Members whose skill is a known monotone function of member index."""
    rng = np.random.default_rng(seed)
    acc = {"n_events": n, "n_members": m}
    quality = np.linspace(0.2, 0.9, m)[None, :] * rng.uniform(0.8, 1.2, size=(n, 1))
    total = 1000.0
    acc["tp"] = np.repeat((quality * total)[:, :, None], len(THRESHOLDS), axis=2)
    acc["fp"] = np.repeat(((1 - quality) * total * 0.5)[:, :, None], len(THRESHOLDS), axis=2)
    acc["fn"] = np.repeat(((1 - quality) * total * 0.5)[:, :, None], len(THRESHOLDS), axis=2)
    acc["tp_mean"] = acc["tp"].mean(axis=1)
    acc["fp_mean"] = acc["fp"].mean(axis=1)
    acc["fn_mean"] = acc["fn"].mean(axis=1)
    acc["mse"] = 100.0 * (1.0 - quality)
    return acc, quality


def test_oracle_brackets_random_and_antioracle():
    acc, quality = _toy_acc()
    arms = selection_arms(acc, quality)
    for key in ("csi35", "csi_M"):
        assert arms["antioracle"][key] < arms["member_mean_over_index"][key] < arms["oracle"][key]


def test_recovery_is_exactly_one_when_score_equals_target():
    """argmax(target) is the oracle; any drift here mis-scales every recovery."""
    acc, quality = _toy_acc()
    arms = selection_arms(acc, quality, curve_draws=30, seed=0)
    got = realised_selection(acc,quality, arms)
    for key in ("csi30", "csi35", "csi40", "csi_M"):
        assert got[f"recovery_{key}"] == pytest.approx(1.0, abs=1e-12)


def test_recovery_is_zero_for_a_constant_score():
    """A score with no information picks member 0 everywhere - below random."""
    acc, quality = _toy_acc()
    arms = selection_arms(acc, quality, curve_draws=30, seed=0)
    got = realised_selection(acc,np.zeros_like(quality), arms)
    assert got["recovery_csi35"] < 0.0  # member 0 is the worst by construction
    assert got["n_fallback_to_member0"] == 0


def test_recovery_is_negative_when_score_is_inverted():
    acc, quality = _toy_acc()
    arms = selection_arms(acc, quality, curve_draws=30, seed=0)
    got = realised_selection(acc,-quality, arms)
    assert got["recovery_csi35"] < -0.5


def test_realised_selection_counts_all_nan_rows_as_fallback():
    acc, quality = _toy_acc()
    arms = selection_arms(acc, quality)
    score = quality.copy()
    score[:3] = np.nan
    got = realised_selection(acc, score, arms)
    assert got["n_fallback_to_member0"] == 3


# ---------------------------------------------------------------- advantage
def test_best_of_n_curve_is_monotone_and_hits_both_ends():
    """N=1 must reproduce the random-member arm; N=m must reproduce the oracle."""
    from tools.verifier_rank_gate import best_of_n_curve

    acc, quality = _toy_acc(n=120, m=6, seed=3)
    arms = selection_arms(acc, quality, curve_draws=40, seed=0)
    curve = best_of_n_curve(acc, quality, (1, 2, 3, 6), draws=40, seed=0)
    got = [curve[str(s)]["csi35"] for s in (1, 2, 3, 6)]
    assert got == sorted(got)
    # random_pick is the N=1 point of the same curve, so this must be exact
    assert got[0] == pytest.approx(arms["random_pick"]["csi35"], abs=1e-12)
    assert got[-1] == pytest.approx(arms["oracle"]["csi35"], abs=1e-12)
    # the fixed-member-index average is a *different* statistic; pooling is nonlinear
    assert got[0] != pytest.approx(arms["member_mean_over_index"]["csi35"], abs=1e-6)


def test_best_of_n_curve_skips_sizes_above_member_count():
    from tools.verifier_rank_gate import best_of_n_curve

    acc, quality = _toy_acc(n=30, m=4)
    curve = best_of_n_curve(acc, quality, (1, 4, 8), draws=5, seed=0)
    assert set(curve) == {"1", "4"}


def test_advantage_flags_degenerate_groups():
    reward = np.tile(np.array([0.3, 0.3, 0.3, 0.3])[None, :], (10, 1))
    d = advantage_diagnostics(reward, "flat")
    assert d["frac_degenerate_groups"] == pytest.approx(1.0)
    assert d["within_event_std_mean"] == pytest.approx(0.0)


def test_advantage_within_over_between_separates_the_two_variances():
    rng = np.random.default_rng(5)
    # large between-event spread, tiny within-event spread
    reward = rng.normal(0, 1.0, size=(200, 1)) + rng.normal(0, 0.01, size=(200, 8))
    d = advantage_diagnostics(reward, "narrow")
    assert d["within_over_between"] < 0.1
    assert d["frac_degenerate_groups"] == pytest.approx(0.0)


def test_advantage_drops_events_with_nan_reward():
    reward = np.random.default_rng(0).normal(size=(10, 4))
    reward[2, 1] = np.nan
    assert advantage_diagnostics(reward, "x")["n_events_usable"] == 9


# ---------------------------------------------------------------- critic
def test_ridge_critic_recovers_a_planted_linear_signal():
    rng = np.random.default_rng(11)
    n, m, p = 200, 8, 3
    feats = rng.normal(size=(n, m, p))
    target = 2.0 * feats[..., 0] - 1.0 * feats[..., 1] + 0.05 * rng.normal(size=(n, m))
    pred, meta = ridge_critic_cv(feats, target, n_folds=5, alpha=1.0)
    rho = np.nanmean(within_event_spearman(pred, target))
    assert rho > 0.8
    assert meta["coef_mean"][0] > meta["coef_mean"][2]
    assert meta["coef_mean"][1] < 0


def test_ridge_critic_finds_nothing_in_pure_noise():
    rng = np.random.default_rng(12)
    feats = rng.normal(size=(200, 8, 3))
    target = rng.normal(size=(200, 8))
    pred, _ = ridge_critic_cv(feats, target, n_folds=5, alpha=10.0)
    rho = np.nanmean(within_event_spearman(pred, target))
    assert abs(rho) < 0.15


def test_ridge_critic_reports_when_too_few_events():
    feats = np.random.default_rng(0).normal(size=(5, 8, 3))
    target = np.random.default_rng(1).normal(size=(5, 8))
    pred, meta = ridge_critic_cv(feats, target, n_folds=5, alpha=1.0)
    assert np.all(np.isnan(pred))
    assert "note" in meta


# ---------------------------------------------------------------- end to end
def _write_toy_h5(path, n=24, m=4, t=10, h=32, w=32, seed=0):
    """Members are truth blurred by a member-dependent amount, so skill is ordered."""
    rng = np.random.default_rng(seed)
    truth = np.zeros((n, t, h, w), dtype=np.float32)
    preds = np.zeros((n, m, t, h, w), dtype=np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    for i in range(n):
        cx, cy = rng.uniform(8, w - 8), rng.uniform(8, h - 8)
        for k in range(t):
            blob = 55.0 * np.exp(-(((xx - cx - k) ** 2 + (yy - cy) ** 2) / 40.0))
            truth[i, k] = blob
            for j in range(m):
                noise = rng.normal(0, 1.0 + 3.0 * j, size=(h, w))
                preds[i, j, k] = np.clip(blob + noise, 0, 90)
    with h5py.File(path, "w") as f:
        f.create_dataset("predictions", data=preds.astype(np.float16))
        f.create_dataset("truth", data=truth.astype(np.float16))
        f.create_dataset("event_index", data=np.arange(n, dtype=np.int64))
        f.attrs["manifest_json"] = json.dumps({"schema_version": "p0-controlled-eval/1", "toy": True})


def test_cli_end_to_end_on_toy_file():
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with tempfile.TemporaryDirectory() as tmp:
        h5_path = os.path.join(tmp, "toy.h5")
        out_dir = os.path.join(tmp, "out")
        _write_toy_h5(h5_path)
        proc = subprocess.run(
            [sys.executable, "tools/verifier_rank_gate.py", "--input", h5_path,
             "--output-dir", out_dir, "--input-length", "5", "--bootstrap", "200",
             "--progress-every", "0"],
            cwd=repo, capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        with open(os.path.join(out_dir, "verifier_gate_report.json")) as f:
            report = json.load(f)
        dumped = np.load(os.path.join(out_dir, "per_member_features.npz"))
        assert dumped["features"].shape == (24, 4, 9)
        assert dumped["target_csi35"].shape == (24, 4)

    arms = report["stage_a_arms"]
    assert arms["oracle"]["csi35"] > arms["member_mean_over_index"]["csi35"]
    assert arms["member_mean_over_index"]["csi35"] > arms["antioracle"]["csi35"]
    assert report["seam_lead"] == 5
    assert report["window_leads"] == [5, 6, 7, 8, 9]
    # noise level rises with member index, so consensus should carry real signal here
    cons = report["stage_b"]["features"]["consensus_l2"]["spearman_vs_csi35"]["mean"]
    assert cons > 0.3


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
