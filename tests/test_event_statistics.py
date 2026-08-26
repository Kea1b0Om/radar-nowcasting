"""The per-event dump must aggregate back to the published metric.

If ``official_csi_m`` over the dumped per-event contingency counts did not
equal what ``MetricsAccumulator`` + ``calculate_metrics`` produce on the same
arrays, then the selector would be ranking checkpoints on a different metric
from the one that gets reported.  These tests pin that equivalence.
"""

import os
import sys

import numpy as np
import pytest
import torch

sys.path.append(os.getcwd())

from common.metrics.metrics_streaming_probabilistic import MetricsAccumulator
from common.utils.utils import calculate_metrics
from tools.score_checkpoints import (
    classify_checkpoint,
    event_statistics,
    is_resumable,
)
from tools.selection_rule import official_csi_m

THRESHOLDS = np.array([20.0, 30.0, 35.0, 40.0], dtype=np.float32)


def _fake_batch(B=6, S=3, T=4, H=32, W=32, seed=0):
    """Radar-ish fields: mostly zero, a few strong cells."""
    rng = np.random.default_rng(seed)
    y_true = np.zeros((B, T, H, W), dtype=np.float32)
    y_pred = np.zeros((B, S, T, H, W), dtype=np.float32)
    for b in range(B):
        for t in range(T):
            m = rng.random((H, W)) < 0.25
            y_true[b, t][m] = rng.uniform(15, 55, m.sum())
            for s in range(S):
                m2 = rng.random((H, W)) < 0.25
                y_pred[b, s, t][m2] = rng.uniform(15, 55, m2.sum())
    return y_true, y_pred


def _reference_metrics(y_true, y_pred, pool_size=16):
    T = y_true.shape[1]
    accs = [
        MetricsAccumulator(
            lead_time=t,
            thresholds=THRESHOLDS,
            pool_size=pool_size,
            compute_mse=True,
            compute_threshold=True,
            compute_crps=False,
            compute_fss=False,
            device=torch.device("cpu"),
        )
        for t in range(T)
    ]
    for a in accs:
        a.update(y_true, y_pred)
    return calculate_metrics(
        num_lead_times=T, metrics_accumulators=accs, thresholds=THRESHOLDS
    )


def _dump(y_true, y_pred, pool_size=16):
    return event_statistics(
        torch.from_numpy(y_true),
        torch.from_numpy(y_pred),
        torch.from_numpy(THRESHOLDS),
        pool_size=pool_size,
    )


def test_pixel_csi_m_matches_metrics_accumulator():
    y_true, y_pred = _fake_batch(seed=1)
    ref = _reference_metrics(y_true, y_pred)
    st = _dump(y_true, y_pred)
    mask = np.ones(y_true.shape[0], dtype=bool)
    got = official_csi_m(st["tp"], st["fn"], st["fp"], mask)
    assert got == pytest.approx(ref["csi_from_mean_m"], rel=1e-9, abs=1e-12)


def test_pooled_csi_m_matches_metrics_accumulator():
    y_true, y_pred = _fake_batch(seed=2)
    ref = _reference_metrics(y_true, y_pred)
    st = _dump(y_true, y_pred)
    mask = np.ones(y_true.shape[0], dtype=bool)
    got = official_csi_m(st["tp_pool"], st["fn_pool"], st["fp_pool"], mask)
    assert got == pytest.approx(ref["csi_pool_from_mean_m"], rel=1e-9, abs=1e-12)


def test_per_threshold_csi_matches():
    y_true, y_pred = _fake_batch(seed=3)
    ref = _reference_metrics(y_true, y_pred)
    st = _dump(y_true, y_pred)
    tp = st["tp"].sum(0); fn = st["fn"].sum(0); fp = st["fp"].sum(0)
    for i, th in enumerate(THRESHOLDS):
        denom = tp[:, i] + fn[:, i] + fp[:, i]
        csi = np.where(denom > 0, tp[:, i] / np.maximum(denom, 1), np.nan)
        assert np.nanmean(csi) == pytest.approx(
            ref["csi_from_mean_mean"][float(th)], rel=1e-9, abs=1e-12
        )


def test_mse_matches():
    y_true, y_pred = _fake_batch(seed=4)
    ref = _reference_metrics(y_true, y_pred)
    st = _dump(y_true, y_pred)
    got = st["sse"].sum() / st["npix"].sum()
    assert got == pytest.approx(ref["mse_from_mean_mean"], rel=1e-6)


def test_contingency_cells_are_a_partition():
    y_true, y_pred = _fake_batch(seed=5)
    st = _dump(y_true, y_pred)
    total = st["tp"] + st["fn"] + st["fp"] + st["tn"]
    assert (total == 32 * 32).all()


def test_counts_are_per_event_not_pooled():
    """Splitting the batch must not change any event's own numbers."""
    y_true, y_pred = _fake_batch(B=6, seed=6)
    whole = _dump(y_true, y_pred)
    first = _dump(y_true[:2], y_pred[:2])
    rest = _dump(y_true[2:], y_pred[2:])
    for k in ("tp", "fn", "fp", "tn", "tp_pool", "sse"):
        joined = np.concatenate([first[k], rest[k]], axis=0)
        assert np.allclose(whole[k], joined)


def test_single_member_crps_is_mae():
    """With S=1 every CRPS estimator degenerates to |x - y|."""
    y_true, y_pred = _fake_batch(S=1, seed=7)
    st = _dump(y_true, y_pred)
    mae = np.abs(y_pred[:, 0] - y_true).sum(axis=(-1, -2))
    assert np.allclose(st["crps_sum"], mae, rtol=1e-5, atol=1e-4)
    assert np.allclose(st["spread_sum"], 0.0)


def test_multi_member_crps_is_below_mae_of_the_members():
    y_true, y_pred = _fake_batch(S=4, seed=8)
    st = _dump(y_true, y_pred)
    per_member_mae = np.abs(y_pred - y_true[:, None]).sum(axis=(-1, -2)).mean(axis=1)
    assert (st["crps_sum"] <= per_member_mae + 1e-6).all()
    assert (st["spread_sum"] > 0).all()


def test_threshold_comparison_is_strictly_greater():
    """A field sitting exactly on a threshold must not count as an exceedance."""
    y_true = np.full((1, 1, 4, 4), 30.0, dtype=np.float32)
    y_pred = np.full((1, 1, 1, 4, 4), 30.0, dtype=np.float32)
    st = event_statistics(
        torch.from_numpy(y_true), torch.from_numpy(y_pred),
        torch.from_numpy(THRESHOLDS), pool_size=1,
    )
    # threshold 20: 30 > 20, so every pixel is a hit
    assert st["tp"][0, 0, 0] == 16
    # thresholds 30/35/40: 30 is NOT > 30, so nothing exceeds anywhere
    for q in (1, 2, 3):
        assert st["tp"][0, 0, q] == 0
        assert st["fp"][0, 0, q] == 0
        assert st["fn"][0, 0, q] == 0
        assert st["tn"][0, 0, q] == 16


def test_classify_checkpoint_separates_ema_from_raw():
    # measured on the server: the early-stopping file carries optimizer but
    # no scheduler and no epoch, the *_latest.pt rescue file carries both
    ema = {"model_state_dict": {}, "optimizer_state_dict": {}, "best_metric": 0.7}
    raw = dict(ema, scheduler_state_dict={}, epoch=91)
    assert classify_checkpoint(ema) == "ema"
    assert classify_checkpoint(raw) == "raw"
    assert is_resumable(raw) and not is_resumable(ema)


def test_periodic_snapshots_declare_their_own_type():
    """Weights-only snapshots: scorable and reportable, never resumable."""
    snap_ema = {"model_state_dict": {}, "is_ema": True, "epoch": 12}
    snap_raw = {"model_state_dict": {}, "is_ema": False, "epoch": 12}
    assert classify_checkpoint(snap_ema) == "ema"
    assert classify_checkpoint(snap_raw) == "raw"
    assert not is_resumable(snap_ema)
    assert not is_resumable(snap_raw)
