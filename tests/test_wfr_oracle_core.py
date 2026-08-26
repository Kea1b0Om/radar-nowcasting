"""Minimal correctness pack for the WFR oracle core (must pass before K1 runs).

Covers exactly the five items the kill-shot spec requires:
  same-location growth/decay, small-displacement analytic path, endpoint
  marginal closure, non-negativity / no NaN, common-kernel rasterisation mass.
"""

import numpy as np
import pytest
import torch

from common.wfr_oracle import core


def _atoms(coords, masses):
    return (torch.tensor(coords, dtype=torch.float32),
            torch.tensor(masses, dtype=torch.float32))


def test_same_location_growth_transported_mass_is_geometric_mean():
    """d=0: the optimal transported mass is sqrt(m0 m1) (pure Hellinger)."""
    x0, a = _atoms([[0.0, 0.0]], [1.0])
    x1, b = _atoms([[0.0, 0.0]], [4.0])
    delta = 10.0
    cost, valid = core.wfr_cost(x0, x1, delta)
    gamma = core.sinkhorn_unbalanced(a, b, cost, valid, lam=2 * delta ** 2,
                                     eps=1e-3 * 2 * delta ** 2, n_iter=2000)
    assert gamma.sum().item() == pytest.approx(np.sqrt(1.0 * 4.0), rel=2e-2)


def test_equal_masses_at_distance_transported_mass_is_m_cos_phi():
    """Closed form for two equal Diracs: coupled mass = m cos(d / 2delta)."""
    delta, d, m = 10.0, 8.0, 3.0
    x0, a = _atoms([[0.0, 0.0]], [m])
    x1, b = _atoms([[0.0, d]], [m])
    cost, valid = core.wfr_cost(x0, x1, delta)
    gamma = core.sinkhorn_unbalanced(a, b, cost, valid, lam=2 * delta ** 2,
                                     eps=1e-3 * 2 * delta ** 2, n_iter=2000)
    expected = m * np.cos(d / (2 * delta))
    assert gamma.sum().item() == pytest.approx(expected, rel=2e-2)


def test_same_location_mass_path_is_hellinger_geodesic():
    """m(t) = ((1-t)sqrt(m0) + t sqrt(m1))^2 when the atoms coincide."""
    x0, a = _atoms([[5.0, 5.0]], [1.0])
    x1, b = _atoms([[5.0, 5.0]], [9.0])
    for t in (0.25, 0.5, 0.75):
        pos, mass, _ = core.wfr_interpolate(x0, x1, a, b, delta=10.0, t=t,
                                            eps_rel=1e-3, n_iter=2000)
        expected = ((1 - t) * 1.0 + t * 3.0) ** 2
        assert mass.sum().item() == pytest.approx(expected, rel=3e-2)


def test_small_displacement_analytic_path():
    """Equal masses, small d: position moves along the segment, mass dips."""
    delta, d, m = 20.0, 6.0, 2.0
    x0, a = _atoms([[0.0, 0.0]], [m])
    x1, b = _atoms([[0.0, d]], [m])
    t = 0.5
    pos, mass, _ = core.wfr_interpolate(x0, x1, a, b, delta=delta, t=t,
                                        eps_rel=1e-3, n_iter=2000)
    phi = d / (2 * delta)
    assert pos[0, 1].item() == pytest.approx(d / 2, abs=1e-2)
    expected_mass = m * (0.25 + 0.25 + 0.5 * np.cos(phi))
    assert mass.sum().item() == pytest.approx(expected_mass, rel=3e-2)


def test_endpoint_marginal_closure_random_config():
    """t=0 recovers source mass, t=1 recovers target mass."""
    g = torch.Generator().manual_seed(0)
    x0 = torch.rand((40, 2), generator=g) * 30
    x1 = torch.rand((35, 2), generator=g) * 30
    a = torch.rand((40,), generator=g) + 0.1
    b = torch.rand((35,), generator=g) + 0.1
    for t, ref in ((0.0, a.sum()), (1.0, b.sum())):
        _, mass, diag = core.wfr_interpolate(x0, x1, a, b, delta=12.0, t=t,
                                             eps_rel=0.01, n_iter=800)
        assert mass.sum().item() == pytest.approx(ref.item(), rel=1e-3)
        assert diag["pruned_mass_frac"] < 1e-3


def test_cutoff_beyond_pi_delta_is_pure_death_and_birth():
    """d >= pi*delta must decouple entirely: all source dies, all target is born."""
    delta = 2.0
    x0, a = _atoms([[0.0, 0.0]], [1.0])
    x1, b = _atoms([[0.0, 50.0]], [1.0])
    _, mass, diag = core.wfr_interpolate(x0, x1, a, b, delta=delta, t=0.5,
                                         eps_rel=0.01, n_iter=400)
    assert diag["dead_mass_frac"] == pytest.approx(1.0, abs=1e-6)
    assert diag["born_mass_frac"] == pytest.approx(1.0, abs=1e-6)
    assert mass.sum().item() == pytest.approx(0.25 * 1.0 + 0.25 * 1.0, rel=1e-6)


def test_non_negative_and_finite():
    g = torch.Generator().manual_seed(1)
    x0 = torch.rand((60, 2), generator=g) * 40
    x1 = torch.rand((60, 2), generator=g) * 40
    a = torch.rand((60,), generator=g)
    b = torch.rand((60,), generator=g)
    for t in (0.25, 0.5, 0.75):
        pos, mass, _ = core.wfr_interpolate(x0, x1, a, b, delta=10.0, t=t)
        assert torch.isfinite(pos).all() and torch.isfinite(mass).all()
        assert (mass >= -1e-8).all()


def test_bot_fr_follows_global_fisher_rao_mass_path():
    g = torch.Generator().manual_seed(2)
    x0 = torch.rand((30, 2), generator=g) * 20
    x1 = torch.rand((25, 2), generator=g) * 20
    a = torch.rand((30,), generator=g) + 0.05
    b = (torch.rand((25,), generator=g) + 0.05) * 3
    t = 0.5
    _, mass, _ = core.bot_fr_interpolate(x0, x1, a, b, t=t, eps_rel=0.05)
    expected = ((1 - t) * a.sum().sqrt() + t * b.sum().sqrt()) ** 2
    assert mass.sum().item() == pytest.approx(expected.item(), rel=1e-4)


def test_splat_conserves_mass_inside_domain():
    pos = torch.tensor([[10.3, 20.7], [50.0, 50.0], [3.5, 4.5]])
    mass = torch.tensor([1.0, 2.0, 0.5])
    field, lost = core.splat_bilinear(pos, mass, (101, 101), cell_km=1.0)
    assert field.sum().item() == pytest.approx(mass.sum().item(), rel=1e-6)
    assert lost.item() == pytest.approx(0.0, abs=1e-6)


def test_common_kernel_preserves_mass_away_from_border():
    field = torch.zeros((101, 101))
    field[50, 50] = 7.0
    blurred = core.gaussian_blur(field, sigma_cells=2.0)
    assert blurred.sum().item() == pytest.approx(7.0, rel=1e-4)
    assert (blurred >= 0).all()
