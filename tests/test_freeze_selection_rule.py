"""The severity pass must see exactly the target frames the evaluator scores.

``compute_split_severity`` re-derives the target window itself instead of
going through ``DynamicSequentialSevirDataset`` (it only needs 10 frames per
event and no model).  If that re-derivation drifted -- off-by-one on the
window, wrong crop, wrong 0-255 -> dBZ scaling -- every stratum label would
be quietly wrong.  These tests build a small CIKM-shaped HDF5 and compare
against the real loader.
"""

import os
import subprocess
import sys

import h5py
import numpy as np
import pandas as pd
import pytest

sys.path.append(os.getcwd())

from experiments.sevir.dataset.sevirfulldataset import DynamicSequentialSevirDataset
from tools.selection_rule import (
    THRESHOLDS_CIKM,
    SelectionRule,
    compute_split_severity,
    severity_from_targets,
)

IMG, RAW_T, LAG, LEAD = 128, 15, 5, 10


def _make_split(dirpath, name, n_events, seed):
    """A CIKM-shaped split: uint8 (N, 128, 128, 15) + META.csv."""
    os.makedirs(dirpath, exist_ok=True)
    rng = np.random.default_rng(seed)
    data = np.zeros((n_events, IMG, IMG, RAW_T), dtype=np.uint8)
    for i in range(n_events):
        # varying wetness so the quantile boundaries are non-degenerate
        level = int(rng.integers(0, 200))
        m = rng.random((IMG, IMG, RAW_T)) < 0.3
        data[i][m] = rng.integers(0, level + 1, m.sum(), dtype=np.uint16).astype(
            np.uint8
        )
    h5_path = os.path.join(dirpath, f"nowcast_{name}_full.h5")
    with h5py.File(h5_path, "w") as f:
        f.create_dataset("vil", data=data, chunks=(1, IMG, IMG, RAW_T))
    meta = pd.DataFrame(
        {
            "file_row": np.arange(n_events),
            "sample_id": [f"sample_{i + 1}" for i in range(n_events)],
            "split": name,
            "time_utc": pd.date_range("2000-01-01", periods=n_events, freq="15min"),
        }
    )
    meta_path = os.path.join(dirpath, f"nowcast_{name}_full_META.csv")
    meta.to_csv(meta_path, index=False)
    return h5_path, meta_path


def test_severity_matches_the_real_dataset_loader(tmp_path):
    d = str(tmp_path / "data")
    h5_path, meta_path = _make_split(d, "validation", 12, seed=3)

    got = compute_split_severity(
        h5_path, meta_path, data_key="vil", raw_seq_len=RAW_T, lag_time=LAG,
        lead_time=LEAD, time_spacing=1, stride=1, crop=(13, -14),
        pixel_scale=90.0, progress=False,
    )

    ds = DynamicSequentialSevirDataset(
        meta_csv=meta_path, data_file=h5_path, data_type="vil",
        raw_seq_len=RAW_T, lag_time=LAG, lead_time=LEAD, time_spacing=1,
        stride=1, channel_last=False, debug_mode=False,
    )
    assert len(ds) == 12, "CIKM must yield exactly one sequence per event"

    for i in range(len(ds)):
        _x, y, _m = ds[i]
        # the loader hands back (C=1, T, H, W); test_flowcast squeezes C,
        # crops to 101x101 and rescales 0-255 -> dBZ before scoring
        y = y.numpy()[0][:, 13:-14, 13:-14] * (90.0 / 255.0)
        expect = severity_from_targets(y[None].astype(np.float32), THRESHOLDS_CIKM)[0]
        assert got["severity"][i] == pytest.approx(expect, rel=1e-6, abs=1e-9)


def test_severity_uses_target_frames_not_input_frames(tmp_path):
    """Frames 0-4 are inputs and must not influence the stratum label."""
    d = str(tmp_path / "data2")
    os.makedirs(d, exist_ok=True)
    data = np.zeros((2, IMG, IMG, RAW_T), dtype=np.uint8)
    data[0, :, :, :LAG] = 255      # very wet INPUT, dry target
    data[1, :, :, LAG:] = 255      # dry input, very wet TARGET
    h5_path = os.path.join(d, "nowcast_validation_full.h5")
    with h5py.File(h5_path, "w") as f:
        f.create_dataset("vil", data=data, chunks=(1, IMG, IMG, RAW_T))
    meta_path = os.path.join(d, "nowcast_validation_full_META.csv")
    pd.DataFrame({"file_row": [0, 1], "sample_id": ["a", "b"],
                  "split": "validation",
                  "time_utc": pd.date_range("2000-01-01", periods=2, freq="15min")
                  }).to_csv(meta_path, index=False)

    got = compute_split_severity(
        h5_path, meta_path, raw_seq_len=RAW_T, lag_time=LAG, lead_time=LEAD,
        time_spacing=1, stride=1, crop=(13, -14), pixel_scale=90.0, progress=False,
    )
    assert got["severity"][0] == 0.0
    assert got["severity"][1] == pytest.approx(4.0)  # 255*90/255 = 90 dBZ


def test_multi_window_events_are_rejected(tmp_path):
    d = str(tmp_path / "data3")
    h5_path, meta_path = _make_split(d, "validation", 3, seed=5)
    with pytest.raises(ValueError, match="one sequence per event"):
        compute_split_severity(
            h5_path, meta_path, raw_seq_len=RAW_T, lag_time=LAG, lead_time=4,
            time_spacing=1, stride=1, crop=(13, -14), pixel_scale=90.0,
            progress=False,
        )


def test_freeze_cli_produces_a_sealed_rule(tmp_path):
    d = str(tmp_path / "data4")
    _make_split(d, "training", 60, seed=11)
    _make_split(d, "validation", 24, seed=12)
    out = str(tmp_path / "rule.json")
    r = subprocess.run(
        [sys.executable, "tools/freeze_selection_rule.py",
         "--data_dir", d, "--out", out, "--n_strata", "4", "--frac_dev", "0.5"],
        capture_output=True, text=True, cwd=os.getcwd(),
    )
    assert r.returncode == 0, r.stderr
    rule = SelectionRule.load(out)
    assert len(rule.val_event_id) == 24
    assert rule.is_dev.sum() > 0 and (1 - rule.is_dev).sum() > 0
    assert rule.n_strata_realised == len(rule.boundaries) + 1
    assert set(np.unique(rule.strata)).issubset(set(range(rule.n_strata_realised)))
    # every stratum present in validation must appear on both sides
    for k in np.unique(rule.strata):
        sel = rule.strata == k
        if sel.sum() >= 2:
            assert rule.is_dev[sel].sum() >= 1
            assert (1 - rule.is_dev[sel]).sum() >= 1

    # re-freezing over an existing file must be refused
    r2 = subprocess.run(
        [sys.executable, "tools/freeze_selection_rule.py",
         "--data_dir", d, "--out", out],
        capture_output=True, text=True, cwd=os.getcwd(),
    )
    assert r2.returncode != 0
    assert "already exists" in (r2.stdout + r2.stderr)


def test_freeze_cli_refuses_to_open_the_test_split(tmp_path):
    d = str(tmp_path / "data5")
    _make_split(d, "training", 8, seed=1)
    _make_split(d, "validation", 8, seed=2)
    r = subprocess.run(
        [sys.executable, "tools/freeze_selection_rule.py",
         "--data_dir", d, "--out", str(tmp_path / "r.json"),
         "--val_h5", os.path.join(d, "nowcast_testing_full.h5"),
         "--val_meta", os.path.join(d, "nowcast_testing_full_META.csv")],
        capture_output=True, text=True, cwd=os.getcwd(),
    )
    assert r.returncode != 0
    assert "without looking at the test split" in (r.stdout + r.stderr)
