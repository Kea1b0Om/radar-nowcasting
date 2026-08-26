"""Mechanism gate for the quantile-axis score (``qwcrps_window``).

The three refuted arms (threshold weighting, soft chaining, both) shared one
property the tests below turn into an explicit theorem check: for a collapsed
ensemble, ANY outcome-axis weighting keeps the optimum at the conditional
median, while the quantile-axis window moves it to the conditional quantile
(1 + tau0)/2.  The dichotomy is pinned in one test that scans both losses
over the same skewed sample -- the test that, had it existed three arms ago,
would have predicted all three deaths and the direction of the fix.

Everything else pins the estimator against the plain-CRPS identity, the
closed-form collapsed loss, the 9x gradient asymmetry at tau0 = 0.8, the
rank routing through torch.sort, and the guards.
"""

import os
import sys

import numpy as np
import pytest
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.metrics.crps import crps_ensemble  # noqa: E402
from common.models.flowcast.distill import (  # noqa: E402
    COMPOSITE_THRESHOLDS,
    qwcrps_window,
    twcrps_composite,
)


def _rand(shape, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(*shape, generator=g, dtype=torch.float64) * 60.0


# --------------------------------------------------------------- identities
def test_tau0_zero_equals_biased_crps():
    """w(a) = 1 integrates the quantile decomposition back to the exact
    empirical CRPS, which is crps_ensemble's "biased" (NRG) estimator."""
    obs = _rand((4, 5, 7), seed=1)
    ens = _rand((4, 8, 5, 7), seed=2)
    qw = qwcrps_window(obs, ens, tau0=0.0)
    ref = crps_ensemble(obs, ens, estimator="biased")
    assert torch.allclose(qw, ref, atol=1e-10), (qw - ref).abs().max().item()


def test_collapsed_closed_form():
    """All members at x: loss = 2(W-V)(x-y)+ + 2V(y-x)+ with W = 1-tau0,
    V = (1-tau0^2)/2 -- the pinball loss at level tau* = V/W = (1+tau0)/2."""
    for tau0 in (0.0, 0.5, 0.8):
        w_tot = 1.0 - tau0
        v_tot = (1.0 - tau0 ** 2) / 2.0
        for x, y in ((30.0, 20.0), (20.0, 30.0), (25.0, 25.0)):
            obs = torch.full((1, 3), y, dtype=torch.float64)
            ens = torch.full((1, 8, 3), x, dtype=torch.float64)
            got = qwcrps_window(obs, ens, tau0=tau0)
            want = 2.0 * ((w_tot - v_tot) * max(x - y, 0.0)
                          + v_tot * max(y - x, 0.0))
            assert torch.allclose(got, torch.full_like(got, want), atol=1e-10)


# ------------------------------------------------------------- the theorem
def test_collapsed_optimum_median_vs_upper_quantile():
    """The z-vs-tau dichotomy on one skewed sample.

    Scan a collapsed ensemble's value x over a grid against right-skewed
    observations.  The tw composite's minimiser stays at the sample median
    for ANY threshold weighting -- including the tilted weights of the dead
    tiltA arm -- while the qw window's minimiser is the upper sample
    quantile (1 + tau0)/2.  This is the mechanism the three refuted arms
    ran into and the constructive claim of the qw arm, in one assertion.
    """
    g = torch.Generator().manual_seed(7)
    # Right-skewed "reflectivity": most mass low, a heavy upper tail.
    y = 8.0 * torch.rand(4000, generator=g, dtype=torch.float64) ** 0.5
    y = torch.where(torch.rand(4000, generator=g) < 0.15,
                    35.0 + 15.0 * torch.rand(4000, generator=g,
                                             dtype=torch.float64), y)
    grid = torch.linspace(0.0, 50.0, 501, dtype=torch.float64)

    def collapsed_loss(fn):
        losses = []
        for x in grid:
            obs = y.reshape(1, -1)
            ens = torch.full((1, 2, y.numel()), float(x), dtype=torch.float64)
            losses.append(float(fn(obs, ens)))
        return grid[int(np.argmin(losses))].item()

    median = y.quantile(0.5).item()
    q90 = y.quantile(0.9).item()
    assert q90 - median > 10.0  # the sample separates the two claims

    plain_min = collapsed_loss(
        lambda o, e: qwcrps_window(o, e, tau0=0.0).mean())
    qw_min = collapsed_loss(
        lambda o, e: qwcrps_window(o, e, tau0=0.8).mean())
    tw_equal_min = collapsed_loss(
        lambda o, e: twcrps_composite(o, e, thresholds=COMPOSITE_THRESHOLDS))
    tw_tilt_min = collapsed_loss(
        lambda o, e: twcrps_composite(o, e, thresholds=COMPOSITE_THRESHOLDS,
                                      threshold_weights=(1, 1, 2, 4, 8)))

    tol = 0.6  # grid pitch 0.1; empirical quantiles of 4000 draws
    assert abs(plain_min - median) < tol, (plain_min, median)
    assert abs(tw_equal_min - median) < tol, (tw_equal_min, median)
    assert abs(tw_tilt_min - median) < tol, (tw_tilt_min, median)
    assert abs(qw_min - q90) < tol, (qw_min, q90)


def test_collapsed_optimum_monotone_in_tau0():
    g = torch.Generator().manual_seed(11)
    y = 50.0 * torch.rand(2000, generator=g, dtype=torch.float64) ** 2
    grid = torch.linspace(0.0, 50.0, 501, dtype=torch.float64)
    mins = []
    for tau0 in (0.0, 0.3, 0.5, 0.8):
        losses = []
        for x in grid:
            obs = y.reshape(1, -1)
            ens = torch.full((1, 2, y.numel()), float(x), dtype=torch.float64)
            losses.append(float(qwcrps_window(obs, ens, tau0=tau0).mean()))
        mins.append(grid[int(np.argmin(losses))].item())
    assert all(b >= a - 1e-9 for a, b in zip(mins, mins[1:])), mins
    assert mins[-1] > mins[0] + 5.0, mins  # the tilt is material, not epsilon


# ------------------------------------------------------------- gradients
def test_gradient_asymmetry_9x_at_tau0_08():
    """Collapsed ensemble: under-prediction is pushed up V/(W-V) = 9x harder
    than over-prediction is pushed down, at tau0 = 0.8."""
    obs = torch.full((1, 1), 30.0, dtype=torch.float64)

    def total_grad(x):
        ens = torch.full((1, 8, 1), x, dtype=torch.float64, requires_grad=True)
        qwcrps_window(obs, ens, tau0=0.8).sum().backward()
        return float(ens.grad.sum())

    g_below = total_grad(20.0)   # members below truth
    g_above = total_grad(40.0)   # members above truth
    v_tot = (1.0 - 0.8 ** 2) / 2.0            # 0.18
    w_tot = 1.0 - 0.8                          # 0.20
    assert g_below == pytest.approx(-2.0 * v_tot, abs=1e-12)
    assert g_above == pytest.approx(2.0 * (w_tot - v_tot), abs=1e-12)
    assert abs(g_below) / abs(g_above) == pytest.approx(9.0, abs=1e-9)


def test_no_dead_zone_below_high_threshold():
    """The scenario that killed the tw arms: everything below 40 dBZ.  The
    t=40 chained slot is exactly flat there (max(x,40) == max(y,40) == 40);
    the qw window still pushes every member toward the truth."""
    obs = torch.full((1, 4), 35.0, dtype=torch.float64)
    ens = torch.full((1, 8, 4), 25.0, dtype=torch.float64, requires_grad=True)

    hard = crps_ensemble(obs.clamp_min(40.0), ens.clamp_min(40.0),
                         estimator="almost_fair").detach()
    assert float(hard.abs().max()) == 0.0  # the tw slot cannot even see it

    qwcrps_window(obs, ens, tau0=0.8).sum().backward()
    assert float(ens.grad.abs().sum()) > 0.0
    assert float(ens.grad.sum()) < 0.0  # and it points up (loss falls as ens rises)


def test_gradient_routes_by_rank():
    """Unsorted input: member j's gradient is the coefficient of its rank,
    2 * (1{y <= x_j} * W_r - V_r), permuted back through torch.sort."""
    obs = torch.tensor([[25.0]], dtype=torch.float64)
    vals = torch.tensor([40.0, 10.0, 30.0, 20.0], dtype=torch.float64)
    ens = vals.reshape(1, 4, 1).clone().requires_grad_(True)
    tau0 = 0.5
    qwcrps_window(obs, ens, tau0=tau0).sum().backward()

    m = 4
    idx = np.arange(1, m + 1)
    lo, hi = (idx - 1) / m, idx / m
    a = np.maximum(lo, tau0)
    w_i = np.where(hi > a, hi - a, 0.0)
    v_i = np.where(hi > a, (hi ** 2 - a ** 2) / 2.0, 0.0)
    order = np.argsort(vals.numpy())          # ranks of the sorted values
    expected = np.empty(m)
    for rank, member in enumerate(order):
        c = 1.0 if 25.0 <= vals[member] else 0.0
        expected[member] = 2.0 * (c * w_i[rank] - v_i[rank])
    assert np.allclose(ens.grad.reshape(-1).numpy(), expected, atol=1e-12)


# ------------------------------------------------------------------ guards
def test_guards():
    obs = _rand((2, 3), seed=3)
    with pytest.raises(ValueError, match="at least 2"):
        qwcrps_window(obs, obs.unsqueeze(1), tau0=0.5)
    with pytest.raises(ValueError, match="tau0"):
        qwcrps_window(obs, _rand((2, 4, 3), seed=4), tau0=1.0)
    with pytest.raises(ValueError, match="tau0"):
        qwcrps_window(obs, _rand((2, 4, 3), seed=4), tau0=-0.1)
    with pytest.raises(ValueError, match="member dim"):
        qwcrps_window(obs, _rand((2, 3), seed=4), tau0=0.5)


def test_half_precision_upcasts_and_matches():
    obs = _rand((2, 6, 6), seed=5).float()
    ens = _rand((2, 8, 6, 6), seed=6).float()
    ref = qwcrps_window(obs, ens, tau0=0.8)
    half = qwcrps_window(obs.to(torch.bfloat16), ens.to(torch.bfloat16), tau0=0.8)
    assert half.dtype == torch.float32
    # bf16 inputs quantise the values themselves; agreement is loose but the
    # score must be finite and correlated, not degenerate.
    assert torch.isfinite(half).all()
    assert float((half - ref).abs().mean()) < 0.5
