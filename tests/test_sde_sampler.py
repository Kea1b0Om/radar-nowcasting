"""Tests for the marginal-preserving SDE sampler in ``rf_stdit.sample_chunk_euler``.

Two things are pinned here, and the second one carries a conclusion that matters
more than the code:

1.  **kappa = 0 is the production sampler, bitwise, and consumes no extra RNG.**
    Without that, no ``kappa=0`` arm can be compared against a stored baseline,
    and the whole dose-response design loses its identity control.

2.  **A marginal-preserving SDE does not widen the terminal spread.**  The
    closed-form Gaussian case makes this measurable: for a target
    ``x_0 ~ N(mu, tau^2)`` with the *exact* velocity field, the terminal mean and
    standard deviation must be ``mu`` and ``tau`` for every ``kappa`` - the
    samples move, the distribution does not.  This is what "same marginals at
    all timesteps" means, so any hope of using ``kappa`` to widen within-group
    reward spread for GRPO is hoping for something the construction forbids.
    Widening the output distribution requires leaving marginal preservation,
    i.e. going off-distribution.

    A sign-flipped reference stepper is included so the check is shown to have
    power: with the score correction added instead of subtracted, the terminal
    standard deviation is visibly wrong.  Without that control, "std came out
    right" could just mean "the correction is too small to matter here".
"""

import math
import os
import sys

import pytest
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models.flowcast.rf_stdit import sample_chunk_euler  # noqa: E402
from common.models.flowcast.schedule import (  # noqa: E402
    build_sampling_timesteps,
    make_chunk_index,
)

TIMESTEPS = 1000
STEPS = 100
MU, TAU = 0.7, 0.8
N = 40000


class GaussianVelocity:
    """Exact ``v = E[x_0 - eps | x_s]`` for ``x_0 ~ N(mu, tau^2)``.

    With ``x_s = s*eps + (1-s)*x_0`` the pair is jointly Gaussian, so
    ``E[x_0|x_s]`` is the linear regression of ``x_0`` on ``x_s`` and
    ``E[eps|x_s] = (x_s - (1-s) E[x_0|x_s]) / s``.  Having the true velocity in
    closed form is what separates "the sampler is wrong" from "the network is
    imperfect" - with a learned velocity the two are inseparable.
    """

    def __init__(self, mu=MU, tau=TAU, num_train_timesteps=TIMESTEPS):
        self.mu, self.tau = float(mu), float(tau)
        self.scale = float(num_train_timesteps - 1)
        self.calls = 0

    def __call__(self, z, t, cond, chunk_index):
        self.calls += 1
        s = float(t[0].item()) / self.scale
        var = (1.0 - s) ** 2 * self.tau**2 + s**2
        e_x0 = self.mu + (1.0 - s) * self.tau**2 / var * (z - (1.0 - s) * self.mu)
        e_eps = (z - (1.0 - s) * e_x0) / s
        return e_x0 - e_eps


def _run(kappa, seed=0, steps=STEPS, final_step_noise=False, compensate=True):
    cond = torch.zeros((N, 1, 1, 1, 1), dtype=torch.float32)
    g = torch.Generator().manual_seed(seed)
    return sample_chunk_euler(
        model=GaussianVelocity(),
        cond=cond,
        chunk_idx=1,
        num_train_timesteps=TIMESTEPS,
        euler_steps=steps,
        generator=g,
        sde_noise_scale=kappa,
        sde_final_step_noise=final_step_noise,
        sde_drift_compensation=compensate,
    )


def _run_sign_flipped(kappa, seed=0, steps=STEPS):
    """Same update with the score correction added instead of subtracted."""
    model = GaussianVelocity()
    cond = torch.zeros((N, 1, 1, 1, 1), dtype=torch.float32)
    device, dtype = cond.device, cond.dtype
    timesteps = build_sampling_timesteps(TIMESTEPS, steps, device)
    chunk_index = make_chunk_index(N, 1, device)
    g = torch.Generator().manual_seed(seed)
    z = torch.randn(cond.shape, device=device, dtype=dtype, generator=g)
    scale = float(TIMESTEPS - 1)
    for cur, nxt in zip(timesteps[:-1], timesteps[1:]):
        t = torch.full((N,), int(cur.item()), device=device, dtype=torch.long)
        v = model(z, t, cond, chunk_index)
        s_cur, s_next = float(cur.item()) / scale, float(nxt.item()) / scale
        ds = s_cur - s_next
        eps_hat = z - (1.0 - s_cur) * v
        z = z + v * ds + (0.5 * kappa * kappa * ds) * eps_hat  # <-- flipped
        if s_next > 0.0:
            std = kappa * math.sqrt(max(s_cur * ds, 0.0))
            z = z + std * torch.randn(z.shape, device=device, dtype=dtype, generator=g)
    return z


# ------------------------------------------------------- identity / RNG
def test_none_and_zero_are_bitwise_identical():
    a = _run(None, seed=5)
    b = _run(0.0, seed=5)
    assert torch.equal(a, b)


def test_kappa_zero_consumes_exactly_one_random_draw():
    """The production path must not shift the RNG stream for later members."""
    cond = torch.zeros((16, 1, 2, 2, 1), dtype=torch.float32)
    g_used = torch.Generator().manual_seed(11)
    sample_chunk_euler(
        model=GaussianVelocity(), cond=cond, chunk_idx=1,
        num_train_timesteps=TIMESTEPS, euler_steps=8, generator=g_used,
        sde_noise_scale=None,
    )
    g_ref = torch.Generator().manual_seed(11)
    torch.randn(cond.shape, generator=g_ref)
    assert torch.equal(g_used.get_state(), g_ref.get_state())


def test_positive_kappa_consumes_more_than_one_draw():
    cond = torch.zeros((16, 1, 2, 2, 1), dtype=torch.float32)
    g_used = torch.Generator().manual_seed(11)
    sample_chunk_euler(
        model=GaussianVelocity(), cond=cond, chunk_idx=1,
        num_train_timesteps=TIMESTEPS, euler_steps=8, generator=g_used,
        sde_noise_scale=0.5,
    )
    g_ref = torch.Generator().manual_seed(11)
    torch.randn(cond.shape, generator=g_ref)
    assert not torch.equal(g_used.get_state(), g_ref.get_state())


def test_positive_kappa_changes_the_samples():
    a = _run(0.0, seed=5)
    b = _run(0.5, seed=5)
    assert not torch.allclose(a, b)


def test_negative_kappa_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        _run(-0.1)


# --------------------------------------------- the marginal-preservation claim
@pytest.mark.parametrize("kappa", [0.0, 0.25, 0.5, 1.0])
def test_terminal_distribution_is_preserved_for_every_kappa(kappa):
    z = _run(kappa, seed=17).reshape(-1)
    assert z.mean().item() == pytest.approx(MU, abs=0.03)
    assert z.std().item() == pytest.approx(TAU, rel=0.04)


def test_spread_does_not_grow_with_kappa():
    """The load-bearing negative result: kappa is not a diversity knob.

    If this ever starts failing in the *increasing* direction it means the
    sampler has stopped preserving marginals, not that a wider ensemble has been
    unlocked for free.
    """
    stds = [_run(k, seed=23).std().item() for k in (0.0, 0.5, 1.0)]
    for value in stds:
        assert value == pytest.approx(stds[0], rel=0.05)
    assert max(stds) / min(stds) < 1.06


def test_sign_flipped_correction_is_detectably_wrong():
    """Shows the preservation test has power rather than being vacuous."""
    good = _run(1.0, seed=31).std().item()
    bad = _run_sign_flipped(1.0, seed=31).std().item()
    assert good == pytest.approx(TAU, rel=0.04)
    assert abs(bad - TAU) / TAU > 0.10


@pytest.mark.parametrize("steps", [10, 100])
def test_preservation_holds_on_the_deployed_step_count(steps):
    """The 10-step schedule is what ships; a fine-step-only check would miss an
    O(ds^2) slip such as evaluating E[eps|x_s] after the velocity step."""
    base = _run(0.0, seed=53, steps=steps).std().item()
    wide = _run(1.0, seed=53, steps=steps).std().item()
    assert wide == pytest.approx(base, rel=0.06)


def test_uncompensated_noise_is_the_only_thing_that_widens_the_spread():
    """kappa alone is not a diversity knob; dropping the drift term is.

    This is the quantified tension: exploration width and staying on the model's
    own distribution are traded against each other, not obtained together.
    """
    compensated = _run(1.0, seed=61, compensate=True).std().item()
    uncompensated = _run(1.0, seed=61, compensate=False).std().item()
    assert compensated == pytest.approx(TAU, rel=0.05)
    assert uncompensated > compensated * 1.2


def test_uncompensated_reduces_to_production_at_kappa_zero():
    assert torch.equal(_run(0.0, seed=67, compensate=False), _run(None, seed=67))


def test_final_step_noise_inflates_the_terminal_spread():
    """Why the last step is deterministic by default."""
    clean = _run(1.0, seed=41).std().item()
    noisy = _run(1.0, seed=41, final_step_noise=True).std().item()
    assert noisy > clean


# ----------------------------------------------------------- threading
@pytest.mark.parametrize("entry", ["autoregressive_sample", "gated_autoregressive_ensemble"])
def test_every_wrapper_accepts_the_full_sde_keyword_set(entry):
    """Regression: ``sde_drift_compensation`` was added to the chunk sampler but
    not to the wrappers, so a real run died on an unexpected keyword while the
    unit tests - which never passed that keyword - stayed green."""
    import inspect

    if entry == "autoregressive_sample":
        from common.models.flowcast.rf_stdit import autoregressive_sample as fn
    else:
        from common.models.flowcast.gated_rollout import (
            gated_autoregressive_ensemble as fn,
        )
    params = inspect.signature(fn).parameters
    for name in ("sde_noise_scale", "sde_final_step_noise", "sde_drift_compensation"):
        assert name in params, f"{entry} is missing {name}"


def test_wrappers_forward_uncompensated_noise():
    from common.models.flowcast.rf_stdit import autoregressive_sample

    cond = torch.zeros((4, 2, 2, 2, 1), dtype=torch.float32)
    kwargs = dict(
        model=GaussianVelocity(), initial_cond=cond, input_length=2,
        output_length=4, num_train_timesteps=TIMESTEPS, euler_steps=6,
        sde_noise_scale=0.8,
    )
    comp = autoregressive_sample(
        generator=torch.Generator().manual_seed(3), sde_drift_compensation=True, **kwargs
    )
    bare = autoregressive_sample(
        generator=torch.Generator().manual_seed(3), sde_drift_compensation=False, **kwargs
    )
    assert not torch.allclose(comp, bare)


def test_autoregressive_sample_default_is_unchanged():
    from common.models.flowcast.rf_stdit import autoregressive_sample

    cond = torch.zeros((4, 2, 2, 2, 1), dtype=torch.float32)
    kwargs = dict(
        model=GaussianVelocity(), initial_cond=cond, input_length=2,
        output_length=4, num_train_timesteps=TIMESTEPS, euler_steps=6,
    )
    a = autoregressive_sample(generator=torch.Generator().manual_seed(3), **kwargs)
    b = autoregressive_sample(
        generator=torch.Generator().manual_seed(3), sde_noise_scale=None, **kwargs
    )
    c = autoregressive_sample(
        generator=torch.Generator().manual_seed(3), sde_noise_scale=0.4, **kwargs
    )
    assert torch.equal(a, b)
    assert not torch.allclose(a, c)


def test_gated_ensemble_default_is_unchanged():
    from common.models.flowcast.gated_rollout import gated_autoregressive_ensemble

    cond = torch.zeros((3, 2, 2, 2, 1), dtype=torch.float32)
    kwargs = dict(
        model=GaussianVelocity(), initial_cond=cond, num_members=2,
        input_length=2, output_length=4, num_train_timesteps=TIMESTEPS,
        euler_steps=6,
    )
    gens = lambda: [torch.Generator().manual_seed(7), torch.Generator().manual_seed(8)]
    a = gated_autoregressive_ensemble(member_generators=gens(), **kwargs)
    b = gated_autoregressive_ensemble(
        member_generators=gens(), sde_noise_scale=None, **kwargs
    )
    c = gated_autoregressive_ensemble(
        member_generators=gens(), sde_noise_scale=0.4, **kwargs
    )
    assert torch.equal(a, b)
    assert not torch.allclose(a, c)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
