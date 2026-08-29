"""Pins for the SCD separability audit's pure math.

Properties pinned here, because the GPU tool cannot be exercised in CI:
  * the block execution order reproduces STDiT.forward exactly
    (S0 T0 ST0 S1 T1 S2 T2 ST1 ... -- spatiotemporal after even iterations);
  * pairwise cosines and condition sensitivity behave at their closed-form
    anchors (identical -> 1, orthogonal -> 0, zero delta -> 0);
  * the speedup projection reproduces the memo's table
    (p = 0.30/0.50/0.60 -> ~1.35x/1.75x/2.06x at M=8, N=4, 2 chunks);
  * every pre-registered gate flips on exactly its own criterion;
  * FeatureTap never leaves hooks behind, and per-block timing attributes
    to the hooked modules.
"""

import os
import sys

import numpy as np
import pytest
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.audit_scd_separability import (  # noqa: E402
    FeatureTap,
    condition_sensitivity,
    evaluate_scd_gates,
    execution_order,
    measure_block_times,
    pairwise_cosines,
    projected_scd_speedup,
    refuse_test_path,
    select_event_rows,
    shuffle_condition,
    stage_of,
)


def test_execution_order_matches_stdit_forward():
    order = execution_order(12)
    assert len(order) == 30
    kinds = [k for k, _ in order]
    assert kinds.count("spatial") == 12
    assert kinds.count("temporal") == 12
    assert kinds.count("spatiotemporal") == 6
    # stdit.py:207-213 -- spatiotemporal fires after even iterations only.
    assert order[:8] == [
        ("spatial", 0), ("temporal", 0), ("spatiotemporal", 0),
        ("spatial", 1), ("temporal", 1),
        ("spatial", 2), ("temporal", 2), ("spatiotemporal", 1),
    ]
    assert order[-2:] == [("spatial", 11), ("temporal", 11)]


def test_execution_order_rejects_odd_depth():
    with pytest.raises(ValueError):
        execution_order(11)


def test_stage_thirds():
    stages = [stage_of(i, 30) for i in range(30)]
    assert stages[:10] == ["early"] * 10
    assert stages[10:20] == ["mid"] * 10
    assert stages[20:] == ["late"] * 10


def test_pairwise_cosines_anchors():
    same = torch.ones(4, 8)
    cos = pairwise_cosines(same)
    assert cos.shape == (6,)
    assert torch.allclose(cos, torch.ones(6), atol=1e-6)

    ortho = torch.eye(3, 8)
    assert torch.allclose(pairwise_cosines(ortho), torch.zeros(3), atol=1e-6)

    # zero rows are guarded, not NaN -- they read as "no stable response".
    zeros = torch.zeros(3, 8)
    assert torch.isfinite(pairwise_cosines(zeros)).all()


def test_condition_sensitivity_anchors():
    h = torch.randn(5, 16, generator=torch.Generator().manual_seed(0))
    assert torch.allclose(condition_sensitivity(h, torch.zeros_like(h)),
                          torch.zeros(5))
    r = condition_sensitivity(h, h)
    assert torch.allclose(r, torch.ones(5), atol=1e-5)


def test_shuffle_condition_batch_roll():
    cond = torch.arange(24.0).reshape(4, 2, 3)
    rolled = shuffle_condition(cond, "batch-roll")
    assert torch.equal(rolled[0], cond[3])
    assert torch.equal(rolled[1:], cond[:3])
    with pytest.raises(ValueError):
        shuffle_condition(cond[:1], "batch-roll")


def test_shuffle_condition_temporal_is_derangement():
    cond = torch.arange(2 * 5 * 3.0).reshape(2, 5, 3)
    shuf = shuffle_condition(cond, "temporal")
    # every frame moved, none dropped
    for t in range(5):
        assert not torch.equal(shuf[:, t], cond[:, t])
    assert torch.equal(shuf.sort(dim=1).values, cond.sort(dim=1).values)


@pytest.mark.parametrize("p,expected", [(0.30, 1.35), (0.50, 1.75), (0.60, 2.06)])
def test_projected_speedup_reproduces_memo_table(p, expected):
    assert projected_scd_speedup(p, members=8, nfe=4) == pytest.approx(
        expected, rel=5e-3)


def test_projected_speedup_edges():
    assert projected_scd_speedup(0.0, 8, 4) == pytest.approx(1.0)
    assert projected_scd_speedup(1.0, 8, 4) == pytest.approx(64.0 / 9.0)
    with pytest.raises(ValueError):
        projected_scd_speedup(1.5, 8, 4)


def _records(s_early_mid, r_early_mid, s_late, r_late, n=30):
    recs = []
    for i in range(n):
        stage = stage_of(i, n)
        late = stage == "late"
        recs.append({
            "stage": stage,
            "s_median": s_late if late else s_early_mid,
            "r_median": r_late if late else r_early_mid,
        })
    return recs


def test_gates_all_pass():
    v = evaluate_scd_gates(_records(0.95, 0.10, 0.50, 0.01), p_cond=0.40)
    assert v["go_prototype"] is True
    assert all(v["gates"].values())
    assert v["projected_speedup"] == pytest.approx(
        projected_scd_speedup(0.40, 8, 4))


@pytest.mark.parametrize("kwargs,failing", [
    # early/mid stability below 0.90 -> G1
    (dict(s_early_mid=0.85, r_early_mid=0.10, s_late=0.5, r_late=0.01, p=0.40),
     "G1_early_mid_stability"),
    # late sensitivity above half of early/mid -> G2
    (dict(s_early_mid=0.95, r_early_mid=0.10, s_late=0.5, r_late=0.06, p=0.40),
     "G2_late_low_sensitivity"),
    # separable compute below 0.35 -> G3 (and G4, which follows from p)
    (dict(s_early_mid=0.95, r_early_mid=0.10, s_late=0.5, r_late=0.01, p=0.20),
     "G3_separable_compute"),
])
def test_gates_flip_individually(kwargs, failing):
    p = kwargs.pop("p")
    v = evaluate_scd_gates(_records(**kwargs), p_cond=p)
    assert v["gates"][failing] is False
    assert v["go_prototype"] is False


def test_gate_g4_follows_speedup_threshold():
    # p = 0.30 projects ~1.35x (pass); p = 0.25 projects ~1.27x (fail).
    ok = evaluate_scd_gates(_records(0.95, 0.10, 0.5, 0.01), p_cond=0.30)
    assert ok["gates"]["G4_projected_speedup"] is True
    bad = evaluate_scd_gates(_records(0.95, 0.10, 0.5, 0.01), p_cond=0.25)
    assert bad["gates"]["G4_projected_speedup"] is False


def test_feature_tap_captures_and_cleans_up():
    blocks = nn.ModuleList([nn.Linear(4, 4) for _ in range(3)])
    x = torch.randn(2, 4, generator=torch.Generator().manual_seed(1))

    with FeatureTap(list(blocks)) as tap:
        h = x
        for block in blocks:
            h = block(h)
        captured = tap.take()
    assert len(captured) == 3
    assert captured[0].shape == (2, 4)
    for block in blocks:
        assert len(block._forward_hooks) == 0

    # take() refuses a forward in which a hooked block did not fire
    with FeatureTap(list(blocks)) as tap:
        blocks[0](x)
        with pytest.raises(RuntimeError):
            tap.take()


def test_measure_block_times_attributes_to_blocks():
    blocks = [nn.Linear(64, 64) for _ in range(3)]
    x = torch.randn(8, 64, generator=torch.Generator().manual_seed(2))

    def forward_fn():
        h = x
        for block in blocks:
            h = block(h)

    timing = measure_block_times(blocks, forward_fn, iters=2, warmup=1)
    per_block = timing["per_block_s"]
    assert len(per_block) == 3
    assert all(t >= 0.0 for t in per_block)
    assert timing["total_sync_s"] > 0.0
    assert sum(per_block) <= timing["total_sync_s"] * 1.5
    for block in blocks:
        assert len(block._forward_hooks) == 0
        assert len(block._forward_pre_hooks) == 0


def test_select_event_rows_is_stable_and_salted():
    a = select_event_rows(1000, 100, seed_salt="scd")
    b = select_event_rows(1000, 100, seed_salt="scd")
    c = select_event_rows(1000, 100, seed_salt="other")
    assert a == b == sorted(a)
    assert len(a) == 100
    assert a != c


def test_refuse_test_path():
    with pytest.raises(SystemExit):
        refuse_test_path("datasets/cikm/data/cikm_full/nowcast_testing_full.h5")
    refuse_test_path("datasets/cikm/data/cikm_full/nowcast_validation_full.h5")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
