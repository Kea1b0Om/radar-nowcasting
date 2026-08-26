"""Correctness gate for the flow-aligned ground cost.

The two tests that carry the design are the identity arm (``alpha = 0`` must
reproduce the Euclidean cost exactly, not approximately) and the physics
direction (along-flow displacement must get cheaper, cross-flow must not).
Everything else guards a specific way this could be silently wrong: an
asymmetric cost matrix, a metric that stops being positive definite, or a
speed outlier making a whole direction free.
"""

import numpy as np
import pytest
import torch

from common.losses.motion_cost import (
    MotionCostConfig,
    euclidean_cost_matrix,
    flow_to_metric,
    metric_cost_matrix,
)

H, W, SP, BLUR = 6, 7, 4.0, 3.0


def _cost(flow, alpha, mode, blur=BLUR, max_speed=None, h=H, w=W, spacing=SP):
    cfg = MotionCostConfig(alpha=alpha, mode=mode, max_speed=max_speed)
    m = flow_to_metric(flow, blur, cfg)
    return metric_cost_matrix(m, h, w, spacing, dtype=torch.float64)


# ------------------------------------------------------------- identity arm
@pytest.mark.parametrize("mode", ["global", "local"])
def test_alpha_zero_is_exactly_euclidean(mode):
    """The dose knob at zero must not perturb the cost at all."""
    flow = torch.randn(3, 2, H, W).double() * 5.0
    got = _cost(flow, alpha=0.0, mode=mode)
    ref = euclidean_cost_matrix(H, W, SP, flow.device, dtype=torch.float64)
    for b in range(got.shape[0]):
        torch.testing.assert_close(got[b], ref, rtol=0, atol=1e-10)


def test_zero_flow_is_euclidean_even_with_alpha():
    """A motionless field has no preferred direction; nothing may change."""
    flow = torch.zeros(2, 2, H, W).double()
    got = _cost(flow, alpha=0.9, mode="global")
    ref = euclidean_cost_matrix(H, W, SP, flow.device, dtype=torch.float64)
    torch.testing.assert_close(got[0], ref, rtol=0, atol=1e-10)


def test_config_rejects_out_of_range_alpha():
    with pytest.raises(ValueError):
        MotionCostConfig(alpha=1.0)
    with pytest.raises(ValueError):
        MotionCostConfig(alpha=-0.1)
    with pytest.raises(ValueError):
        MotionCostConfig(mode="diagonal")


# ----------------------------------------------------------------- physics
def test_along_flow_is_cheaper_and_cross_flow_is_not():
    """The whole point: timing errors get a discount, track errors do not."""
    # flow purely along +w, fast enough that s is near its ceiling
    flow = torch.zeros(1, 2, H, W).double()
    flow[:, 1] = 30.0
    c0 = _cost(flow, alpha=0.0, mode="global")[0]
    c1 = _cost(flow, alpha=0.8, mode="global")[0]

    def idx(i, j):
        return i * W + j

    # same source, one step along flow (w) vs one step across flow (h)
    src = idx(2, 2)
    along, cross = idx(2, 3), idx(3, 2)
    assert c1[src, along] < c0[src, along]              # timing error discounted
    torch.testing.assert_close(c1[src, cross], c0[src, cross], rtol=0, atol=1e-10)


def test_discount_is_monotone_in_alpha():
    flow = torch.zeros(1, 2, H, W).double()
    flow[:, 1] = 30.0
    src, along = 2 * W + 2, 2 * W + 3
    vals = [float(_cost(flow, alpha=a, mode="global")[0, src, along])
            for a in (0.0, 0.25, 0.5, 0.75)]
    assert all(x > y for x, y in zip(vals, vals[1:]))


def test_discount_saturates_with_speed():
    """s -> alpha, so a 10x faster storm cannot buy a 10x bigger discount."""
    src, along = 2 * W + 2, 2 * W + 3
    out = []
    for speed in (3.0, 30.0, 300.0):
        flow = torch.zeros(1, 2, H, W).double()
        flow[:, 1] = speed
        out.append(float(_cost(flow, alpha=0.5, mode="global")[0, src, along]))
    assert out[0] > out[1] > out[2]
    euclid = float(euclidean_cost_matrix(H, W, SP, torch.device("cpu"),
                                         dtype=torch.float64)[src, along])
    assert out[-1] >= 0.5 * euclid - 1e-9      # bounded by (1 - alpha)


# ------------------------------------------------------- structural safety
@pytest.mark.parametrize("mode", ["global", "local"])
def test_cost_matrix_is_symmetric(mode):
    """The g-update and both debiasing terms assume C == C^T."""
    flow = torch.randn(2, 2, H, W).double() * 8.0
    c = _cost(flow, alpha=0.7, mode=mode)
    torch.testing.assert_close(c, c.transpose(-1, -2), rtol=0, atol=1e-12)


@pytest.mark.parametrize("mode", ["global", "local"])
def test_cost_is_non_negative_with_zero_diagonal(mode):
    flow = torch.randn(2, 2, H, W).double() * 8.0
    c = _cost(flow, alpha=0.9, mode=mode)
    assert float(c.min()) >= -1e-12
    d = torch.diagonal(c, dim1=-2, dim2=-1)
    torch.testing.assert_close(d, torch.zeros_like(d), rtol=0, atol=1e-12)


def test_metric_stays_positive_definite():
    flow = torch.randn(4, 2, H, W).double() * 50.0
    m = flow_to_metric(flow, BLUR, MotionCostConfig(alpha=0.99, mode="local"))
    ev = torch.linalg.eigvalsh(m)
    assert float(ev.min()) > 0.0


def test_max_speed_clamp_bounds_the_discount():
    """An optical-flow outlier must not make a direction free."""
    flow = torch.zeros(1, 2, H, W).double()
    flow[:, 1] = 1e4
    src, along = 2 * W + 2, 2 * W + 3
    loose = float(_cost(flow, alpha=0.9, mode="global")[0, src, along])
    tight = float(_cost(flow, alpha=0.9, mode="global", max_speed=1.0)[0, src, along])
    assert tight > loose


# ------------------------------------------------------------ local vs global
def test_local_reduces_to_global_for_uniform_flow():
    """A spatially constant field must give the same answer either way."""
    flow = torch.zeros(1, 2, H, W).double()
    flow[:, 0], flow[:, 1] = 4.0, 9.0
    torch.testing.assert_close(
        _cost(flow, alpha=0.6, mode="local"),
        _cost(flow, alpha=0.6, mode="global"),
        rtol=0, atol=1e-10,
    )


def test_global_mode_accepts_a_bare_vector():
    v = torch.tensor([[3.0, 4.0]]).double()
    field = torch.zeros(1, 2, H, W).double()
    field[:, 0], field[:, 1] = 3.0, 4.0
    torch.testing.assert_close(_cost(v, 0.5, "global"), _cost(field, 0.5, "global"),
                               rtol=0, atol=1e-10)


def test_flow_input_is_not_mutated():
    flow = torch.randn(2, 2, H, W).double() * 100.0
    before = flow.clone()
    _cost(flow, alpha=0.8, mode="local", max_speed=2.0)
    torch.testing.assert_close(flow, before, rtol=0, atol=0)


def test_local_metric_differs_from_global_when_flow_rotates():
    """Otherwise 'local' would be an expensive way to compute 'global'."""
    flow = torch.zeros(1, 2, H, W).double()
    flow[:, 0, : H // 2] = 20.0          # top half moves down
    flow[:, 1, H // 2:] = 20.0           # bottom half moves right
    a = _cost(flow, alpha=0.8, mode="local")
    b = _cost(flow, alpha=0.8, mode="global")
    assert float((a - b).abs().max()) > 1e-3


# =====================================================================
# dense Sinkhorn path (exercised only when motion is enabled)
# =====================================================================
from common.losses.uot import GridUOTConfig, GridUnbalancedSinkhorn  # noqa: E402


def _pair(seed=0, h=8, w=9):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(2, h, w, generator=g), torch.rand(2, h, w, generator=g)


def _module(alpha, mode="global", **kw):
    cfg = GridUOTConfig(
        blur=3.0, reach=16.0, downsample=1, n_iters=60, self_iters=30,
        motion=MotionCostConfig(alpha=alpha, mode=mode, **kw),
    )
    return GridUnbalancedSinkhorn(cfg)


def test_dense_path_matches_separable_when_flow_is_zero():
    """Validates the dense solver itself.

    Zero flow makes M = I, so the dense path computes the *same* cost as the
    separable one by a completely different route.  Any disagreement is a bug in
    the dense implementation, not a modelling choice.
    """
    a, b = _pair()
    zero = torch.zeros(2, 2, 8, 9)
    dense = _module(alpha=0.5)(a, b, flow=zero)      # enabled -> dense
    sep = _module(alpha=0.0)(a, b)                   # disabled -> separable
    torch.testing.assert_close(dense, sep, rtol=1e-5, atol=1e-4)


def test_motion_disabled_ignores_flow_entirely():
    a, b = _pair(seed=1)
    m = _module(alpha=0.0)
    torch.testing.assert_close(
        m(a, b), m(a, b, flow=torch.randn(2, 2, 8, 9) * 10.0), rtol=0, atol=0
    )


def test_enabled_motion_requires_a_flow():
    a, b = _pair(seed=2)
    with pytest.raises(ValueError, match="no flow"):
        _module(alpha=0.5)(a, b)


def test_along_flow_displacement_is_penalised_less():
    """The behaviour the whole change exists to produce, at the loss level."""
    # A single-pixel source, so the two displacements are geometrically
    # identical under a Euclidean cost.  (A blob elongated along one axis is
    # not: its own anisotropy would show up as a cost difference and the test
    # would pass for the wrong reason.)
    h = w = 16
    base = torch.zeros(1, h, w)
    base[0, 8, 8] = 1.0
    along = torch.zeros(1, h, w)
    along[0, 8, 11] = 1.0              # +3 along w
    across = torch.zeros(1, h, w)
    across[0, 11, 8] = 1.0             # +3 along h

    flow = torch.zeros(1, 2, h, w)
    flow[:, 1] = 12.0                  # motion along +w

    m = _module(alpha=0.8)
    d_along = float(m(base, along, flow=flow))
    d_across = float(m(base, across, flow=flow))
    assert d_along < d_across

    plain = _module(alpha=0.0)
    p_along = float(plain(base, along))
    p_across = float(plain(base, across))
    # Euclidean cost cannot tell the two apart; the motion cost can.
    assert abs(p_along - p_across) < 1e-3
    assert (d_across - d_along) > 10 * abs(p_along - p_across)


def test_dense_path_is_differentiable_into_the_mass():
    a, b = _pair(seed=3)
    a = a.clone().requires_grad_(True)
    flow = torch.randn(2, 2, 8, 9) * 5.0
    _module(alpha=0.6)(a, b, flow=flow).sum().backward()
    assert a.grad is not None and torch.isfinite(a.grad).all()
    assert float(a.grad.abs().sum()) > 0.0


def test_sequence_broadcasts_one_flow_over_leads():
    a, b = _pair(seed=4)
    a4 = a.unsqueeze(1).repeat(1, 3, 1, 1)
    b4 = b.unsqueeze(1).repeat(1, 3, 1, 1)
    flow = torch.randn(2, 2, 8, 9) * 4.0
    m = _module(alpha=0.5)
    seq = m.sequence(a4, b4, flow=flow, reduce=False)
    assert seq.shape == (2, 3)
    # identical frames -> identical values, i.e. the flow really was shared
    torch.testing.assert_close(seq[:, 0], seq[:, 1], rtol=1e-5, atol=1e-4)


def test_sequence_rejects_a_per_lead_flow():
    """A (B,T,2,H,W) flow would let a lead-dependent field in, which is where
    future information would enter."""
    a, b = _pair(seed=5)
    a4 = a.unsqueeze(1).repeat(1, 3, 1, 1)
    b4 = b.unsqueeze(1).repeat(1, 3, 1, 1)
    with pytest.raises(ValueError, match="flow must be"):
        _module(alpha=0.5).sequence(a4, b4, flow=torch.randn(2, 3, 2, 8, 9))


def test_flow_is_pooled_to_the_sinkhorn_grid():
    """Production shape: the flow arrives at 128x128, Sinkhorn runs at 32x32.

    Caught a real crash in ``local`` mode that the small-grid tests missed
    because they used downsample=1.  ``global`` never crashed here -- it reduces
    to a vector first -- so only the local path was exposed.
    """
    h = w = 32
    a = torch.rand(2, h, w)
    b = torch.rand(2, h, w)
    flow = torch.randn(2, 2, h, w) * 5.0
    for mode in ("global", "local"):
        cfg = GridUOTConfig(
            blur=3.0, reach=16.0, downsample=4, n_iters=20, self_iters=10,
            motion=MotionCostConfig(alpha=0.5, mode=mode),
        )
        v = GridUnbalancedSinkhorn(cfg)(a, b, flow=flow)   # 32 -> 8 grid
        assert v.shape == (2,) and torch.isfinite(v).all()


def test_pooled_flow_preserves_a_uniform_field():
    """Average pooling a constant flow must not change the metric, or the
    discount would depend on the downsample factor."""
    h = w = 16
    a = torch.rand(1, h, w)
    b = torch.rand(1, h, w)
    flow_full = torch.zeros(1, 2, h, w)
    flow_full[:, 1] = 10.0
    def build(mode):
        return GridUnbalancedSinkhorn(GridUOTConfig(
            blur=3.0, reach=16.0, downsample=4, n_iters=20, self_iters=10,
            motion=MotionCostConfig(alpha=0.5, mode=mode)))

    torch.testing.assert_close(
        build("local")(a, b, flow=flow_full),                    # pooled field
        build("global")(a, b, flow=torch.tensor([[0.0, 10.0]])),  # same, as vector
        rtol=1e-5, atol=1e-4,
    )
