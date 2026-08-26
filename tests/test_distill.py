"""Correctness gate for the distillation module (``flowcast.distill``).

Four properties carry the whole training design, so they are pinned at the
bit level rather than argued about:

1.  **The explicit-noise sampler is the production sampler.**  Fed the same
    initial draw, ``sample_chunk_euler_from_noise`` must reproduce
    ``sample_chunk_euler(kappa=0)`` bitwise, and the autoregressive wrapper
    must reproduce ``autoregressive_sample`` bitwise.  Without that, no
    teacher endpoint is comparable to a stored baseline and the identity
    arm below is meaningless.

2.  **The identity arm is exact.**  A student with the teacher's weights on
    the teacher's grid has distill loss exactly 0.0 -- not small, zero.
    This is the no-op control every later ablation is diffed against.

3.  **``grad_last_k`` changes gradients, never values.**  Outputs are
    bitwise identical for every ``k``; only the autograd graph differs.

4.  **The torch composite score is the gated reward.**  The ``fair`` path
    must match the numpy reference in ``tools/reward_dispersion_gate`` --
    the offline dispersion/dead-zone numbers were measured on that code,
    and they transfer to training only if the two are the same function.
"""

import math
import os
import sys

import numpy as np
import pytest
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models.flowcast.distill import (  # noqa: E402
    COMPOSITE_THRESHOLDS,
    soft_chain,
    autoregressive_sample_from_noises,
    clamp_straight_through,
    draw_chunk_noises,
    endpoint_distill_loss,
    sample_chunk_euler_from_noise,
    twcrps_composite,
)
from common.models.flowcast.rf_stdit import (  # noqa: E402
    autoregressive_sample,
    sample_chunk_euler,
)
from tools.reward_dispersion_gate import (  # noqa: E402
    TW_THRESHOLDS,
    ensemble_terms,
    fair_crps_from_terms,
)

TIMESTEPS = 1000
TEACHER_STEPS = 10
STUDENT_STEPS = 4
SHAPE = (3, 2, 5, 5, 4)  # (B, T, H, W, C), channel-last like the wrapper


class TinyVelocity(nn.Module):
    """Small, smooth, parameter-bearing stand-in for the STDiT wrapper.

    Depends on all four inputs (state, time, condition, chunk index) so a
    wiring mistake in any of them changes the output, and carries a Linear
    so gradient-flow assertions have parameters to reach.
    """

    def __init__(self, channels: int, seed: int = 0):
        super().__init__()
        g = torch.Generator().manual_seed(seed)
        self.lin = nn.Linear(channels, channels)
        with torch.no_grad():
            self.lin.weight.copy_(
                0.2 * torch.randn(self.lin.weight.shape, generator=g)
            )
            self.lin.bias.zero_()

    def forward(self, z, t, cond, chunk_index):
        s = (t.float() / float(TIMESTEPS - 1)).view(-1, 1, 1, 1, 1)
        c = chunk_index.float().view(-1, 1, 1, 1, 1)
        return self.lin(z) * (0.5 + 0.5 * s) + 0.3 * cond - 0.4 * z + 0.01 * c


@pytest.fixture()
def model():
    torch.manual_seed(0)
    return TinyVelocity(SHAPE[-1])


@pytest.fixture()
def cond():
    g = torch.Generator().manual_seed(123)
    return torch.randn(SHAPE, generator=g)


# ---------------------------------------------------------------- property 1
def test_from_noise_matches_production_sampler_bitwise(model, cond):
    g = torch.Generator().manual_seed(7)
    ref = sample_chunk_euler(
        model=model, cond=cond, chunk_idx=1,
        num_train_timesteps=TIMESTEPS, euler_steps=TEACHER_STEPS, generator=g,
    )
    g2 = torch.Generator().manual_seed(7)
    noise = torch.randn(cond.shape, dtype=cond.dtype, generator=g2)
    mine = sample_chunk_euler_from_noise(
        model=model, cond=cond, chunk_idx=1,
        num_train_timesteps=TIMESTEPS, euler_steps=TEACHER_STEPS, noise=noise,
    )
    assert torch.equal(ref, mine)


def test_autoregressive_from_noises_matches_production_bitwise(model, cond):
    g = torch.Generator().manual_seed(11)
    ref = autoregressive_sample(
        model=model, initial_cond=cond, input_length=SHAPE[1],
        output_length=2 * SHAPE[1], num_train_timesteps=TIMESTEPS,
        euler_steps=TEACHER_STEPS, generator=g,
    )
    g2 = torch.Generator().manual_seed(11)
    noises = draw_chunk_noises(cond.shape, 2, cond.device, cond.dtype, g2)
    mine = autoregressive_sample_from_noises(
        model=model, initial_cond=cond, input_length=SHAPE[1],
        output_length=2 * SHAPE[1], num_train_timesteps=TIMESTEPS,
        euler_steps=TEACHER_STEPS, noises=noises,
    )
    assert torch.equal(ref, mine)


def test_noise_shape_mismatch_is_rejected(model, cond):
    bad = torch.zeros(1, *SHAPE[1:])
    with pytest.raises(ValueError, match="noise shape"):
        sample_chunk_euler_from_noise(
            model=model, cond=cond, chunk_idx=1,
            num_train_timesteps=TIMESTEPS, euler_steps=4, noise=bad,
        )


# ---------------------------------------------------------------- property 2
def test_identity_arm_distill_loss_is_exactly_zero(model, cond):
    g = torch.Generator().manual_seed(3)
    noises = draw_chunk_noises(cond.shape, 2, cond.device, cond.dtype, g)
    kwargs = dict(
        model=model, initial_cond=cond, input_length=SHAPE[1],
        output_length=2 * SHAPE[1], num_train_timesteps=TIMESTEPS,
        euler_steps=TEACHER_STEPS, noises=noises,
    )
    with torch.no_grad():
        teacher = autoregressive_sample_from_noises(**kwargs)
    student = autoregressive_sample_from_noises(**kwargs)
    loss = endpoint_distill_loss(student, teacher)
    assert float(loss.detach()) == 0.0


def test_fewer_steps_gives_strictly_positive_loss(model, cond):
    g = torch.Generator().manual_seed(3)
    noises = draw_chunk_noises(cond.shape, 2, cond.device, cond.dtype, g)
    common = dict(
        model=model, initial_cond=cond, input_length=SHAPE[1],
        output_length=2 * SHAPE[1], num_train_timesteps=TIMESTEPS,
        noises=noises,
    )
    with torch.no_grad():
        teacher = autoregressive_sample_from_noises(
            euler_steps=TEACHER_STEPS, **common
        )
    student = autoregressive_sample_from_noises(
        euler_steps=STUDENT_STEPS, **common
    )
    assert float(endpoint_distill_loss(student, teacher)) > 0.0


def test_distill_loss_shape_mismatch_is_rejected():
    with pytest.raises(ValueError, match="shape mismatch"):
        endpoint_distill_loss(torch.zeros(2, 3), torch.zeros(2, 4))


# ---------------------------------------------------------------- property 3
def test_grad_last_k_never_changes_values(model, cond):
    g = torch.Generator().manual_seed(5)
    noise = torch.randn(cond.shape, generator=g)
    outs = []
    for k in (None, 0, 1, STUDENT_STEPS):
        outs.append(sample_chunk_euler_from_noise(
            model=model, cond=cond, chunk_idx=1,
            num_train_timesteps=TIMESTEPS, euler_steps=STUDENT_STEPS,
            noise=noise, grad_last_k=k,
        ))
    for other in outs[1:]:
        assert torch.equal(outs[0], other)


def test_grad_last_k_zero_detaches_and_positive_reaches_parameters(model, cond):
    g = torch.Generator().manual_seed(5)
    noise = torch.randn(cond.shape, generator=g)

    detached = sample_chunk_euler_from_noise(
        model=model, cond=cond, chunk_idx=1,
        num_train_timesteps=TIMESTEPS, euler_steps=STUDENT_STEPS,
        noise=noise, grad_last_k=0,
    )
    assert not detached.requires_grad

    model.zero_grad(set_to_none=True)
    pred = sample_chunk_euler_from_noise(
        model=model, cond=cond, chunk_idx=1,
        num_train_timesteps=TIMESTEPS, euler_steps=STUDENT_STEPS,
        noise=noise, grad_last_k=1,
    )
    assert pred.requires_grad
    pred.square().mean().backward()
    grad = model.lin.weight.grad
    assert grad is not None
    assert torch.isfinite(grad).all()
    assert float(grad.abs().sum()) > 0.0


def test_negative_grad_last_k_is_rejected(model, cond):
    with pytest.raises(ValueError, match="grad_last_k"):
        sample_chunk_euler_from_noise(
            model=model, cond=cond, chunk_idx=1,
            num_train_timesteps=TIMESTEPS, euler_steps=STUDENT_STEPS,
            noise=torch.zeros_like(cond), grad_last_k=-1,
        )


# ---------------------------------------------------------------- property 4
def test_composite_thresholds_match_the_offline_gate():
    assert tuple(COMPOSITE_THRESHOLDS) == tuple(float(t) for t in TW_THRESHOLDS)


def test_fair_composite_matches_numpy_gate_reference():
    rng = np.random.default_rng(42)
    members = rng.uniform(0.0, 55.0, size=(6, 3, 9, 11)).astype(np.float64)
    obs = rng.uniform(0.0, 55.0, size=(3, 9, 11)).astype(np.float64)

    ref_pieces = []
    for t in TW_THRESHOLDS:
        a, d = ensemble_terms(members, obs, t)
        ref_pieces.append(fair_crps_from_terms(a, d))
    ref = float(np.mean(ref_pieces))

    mine = twcrps_composite(
        torch.from_numpy(obs)[None],
        torch.from_numpy(members)[None],
        thresholds=TW_THRESHOLDS,
        estimator="fair",
    )
    assert abs(float(mine) - ref) < 1e-10


def test_single_high_threshold_has_dead_zone_composite_does_not():
    """The measured dead-zone geometry, reproduced as gradients.

    Every value below 40 dBZ: the t=40 score clamps everything to the
    constant 40, so the loss is exactly zero and so is its gradient.  The
    default composite keeps a gradient alive through its plain term --
    which is why a single tail threshold is not a usable objective.
    """
    g = torch.Generator().manual_seed(9)
    ens = (10.0 * torch.rand((1, 5, 2, 7, 7), generator=g)).requires_grad_(True)
    obs = 10.0 * torch.rand((1, 2, 7, 7), generator=g)

    tail_only = twcrps_composite(obs, ens, thresholds=(40.0,), estimator="fair")
    assert float(tail_only) == 0.0
    tail_only.backward()
    assert float(ens.grad.abs().sum()) == 0.0

    ens.grad = None
    composite = twcrps_composite(obs, ens, estimator="fair")
    composite.backward()
    assert float(composite) > 0.0
    assert float(ens.grad.abs().sum()) > 0.0


def test_fair_composite_penalises_collapse_member_mae_prefers_it():
    """The twmae trap, restated on the training loss.

    Against y ~ N(0,1) with the true predictive distribution N(0,1): a
    dispersed ensemble drawn from the truth must beat a collapsed one at
    the median under the fair score (0.23 vs 0.80 in expectation), while
    the per-member MAE prefers the collapse (0.80 vs 1.13).  Pixel count
    is chosen so sampling noise (~0.02) cannot cross either gap.
    """
    g = torch.Generator().manual_seed(1234)
    obs = torch.randn((1, 48, 48), generator=g)
    dispersed = torch.randn((1, 8, 48, 48), generator=g)
    collapsed = torch.zeros((1, 8, 48, 48))

    fair_disp = float(twcrps_composite(obs, dispersed, thresholds=(float("-inf"),),
                                       estimator="fair"))
    fair_coll = float(twcrps_composite(obs, collapsed, thresholds=(float("-inf"),),
                                       estimator="fair"))
    assert fair_disp < fair_coll

    mae_disp = float((dispersed - obs[:, None]).abs().mean())
    mae_coll = float((collapsed - obs[:, None]).abs().mean())
    assert mae_coll < mae_disp


def test_composite_weight_validation():
    obs = torch.zeros((1, 2, 3, 3))
    ens = torch.zeros((1, 4, 2, 3, 3))
    with pytest.raises(ValueError, match="weights"):
        twcrps_composite(obs, ens, thresholds=(0.0, 1.0), threshold_weights=(1.0,))
    with pytest.raises(ValueError, match="positive sum"):
        twcrps_composite(obs, ens, thresholds=(0.0,), threshold_weights=(0.0,))
    with pytest.raises(ValueError, match="non-empty"):
        twcrps_composite(obs, ens, thresholds=())


# ----------------------------------------------- score view / straight-through
def test_straight_through_clamp_has_evaluator_values_and_live_gradient():
    """Value == clamp (so the score is the one the offline gate measured),
    gradient == identity (so a member decoding below zero where the truth
    has echo can still be pushed back into range)."""
    x = torch.tensor([-5.0, 0.0, 45.0, 95.0], requires_grad=True)
    y = clamp_straight_through(x, 0.0, 90.0)
    assert torch.equal(y.detach(), x.detach().clamp(0.0, 90.0))
    y.sum().backward()
    assert torch.equal(x.grad, torch.ones_like(x))

    hard = x.detach().clone().requires_grad_(True)
    hard.clamp(0.0, 90.0).sum().backward()
    # The plain clamp is exactly what the straight-through form is avoiding:
    # zero gradient on the out-of-range entries.
    assert float(hard.grad[0]) == 0.0 and float(hard.grad[-1]) == 0.0


def test_ste_score_equals_clamped_score_in_value():
    g = torch.Generator().manual_seed(31)
    raw = 100.0 * torch.randn((1, 4, 2, 6, 6), generator=g)  # far out of range
    obs = 40.0 * torch.rand((1, 2, 6, 6), generator=g)
    ste = twcrps_composite(obs, clamp_straight_through(raw, 0.0, 90.0))
    hard = twcrps_composite(obs, raw.clamp(0.0, 90.0))
    assert torch.allclose(ste, hard, atol=0, rtol=0)


def test_single_member_ensemble_is_rejected_as_the_twmae_trap():
    obs = torch.zeros((1, 2, 4, 4))
    ens = torch.zeros((1, 1, 2, 4, 4))
    with pytest.raises(ValueError, match="twmae trap"):
        twcrps_composite(obs, ens)


def test_components_sum_to_total_and_are_labelled():
    g = torch.Generator().manual_seed(77)
    ens = 50.0 * torch.rand((1, 5, 2, 8, 8), generator=g)
    obs = 50.0 * torch.rand((1, 2, 8, 8), generator=g)
    total, comps = twcrps_composite(obs, ens, return_components=True)
    assert set(comps) == {"plain", "t20", "t30", "t35", "t40"}
    assert torch.allclose(torch.stack(list(comps.values())).sum(), total)
    # The reason components must be logged: the tail terms are orders of
    # magnitude smaller, so a falling total says nothing about the tail.
    assert float(comps["t40"]) < float(comps["plain"])


# ------------------------------------------------------- end-to-end gradient
def test_reward_gradient_flows_through_sampler_into_parameters(model, cond):
    """The whole intended training path: K-step student sample (last step
    under grad) -> composite score -> backbone parameters."""
    g = torch.Generator().manual_seed(21)
    noises = draw_chunk_noises(cond.shape, 2, cond.device, cond.dtype, g)
    model.zero_grad(set_to_none=True)
    pred = autoregressive_sample_from_noises(
        model=model, initial_cond=cond, input_length=SHAPE[1],
        output_length=2 * SHAPE[1], num_train_timesteps=TIMESTEPS,
        euler_steps=STUDENT_STEPS, noises=noises, grad_last_k=1,
    )
    # (B, T, H, W, C) -> treat batch as members of one event on channel 0
    ens = pred[..., 0].unsqueeze(0)                       # (1, B, 2T, H, W)
    obs = torch.zeros_like(ens[:, 0])
    loss = twcrps_composite(obs, ens, thresholds=(float("-inf"), 0.5))
    loss.backward()
    grad = model.lin.weight.grad
    assert grad is not None
    assert torch.isfinite(grad).all()
    assert float(grad.abs().sum()) > 0.0


# ------------------------------------------------- soft chaining (extremes)
"""The tail-weighting arms failed because ``max(z, t)`` has exactly zero
gradient below ``t``: a model that under-predicts heavy echo gets no signal
to increase it, so moving weight onto the tail terms moved weight onto a
term that had nothing to give.  ``soft_chain`` replaces the hard transform
with a strictly increasing smooth one.  These tests pin the three properties
that make the replacement legitimate rather than merely different."""


def test_soft_chain_is_bitwise_hard_max_at_zero_softness():
    g = torch.Generator().manual_seed(31)
    z = 60.0 * torch.rand((4, 7, 7), generator=g)
    for thr in (20.0, 40.0):
        assert torch.equal(soft_chain(z, thr, 0.0), z.clamp_min(thr))
    # -inf is the identity for every softness, so one code path serves
    # plain CRPS and every finite threshold.
    for s in (0.0, 0.5, 3.0):
        assert torch.equal(soft_chain(z, float("-inf"), s), z)


def test_soft_chain_converges_uniformly_to_hard_max():
    """The gap is bounded by ``s * log 2``, so shrinking softness recovers
    the published score rather than approaching something else."""
    g = torch.Generator().manual_seed(32)
    z = 60.0 * torch.rand((512,), generator=g)
    hard = z.clamp_min(40.0)
    prev = None
    for s in (4.0, 2.0, 1.0, 0.5):
        gap = (soft_chain(z, 40.0, s) - hard).abs().max().item()
        assert gap <= s * math.log(2.0) + 1e-4
        if prev is not None:
            assert gap < prev
        prev = gap


def test_soft_chain_is_monotone_and_strictly_so_where_it_can_be():
    """Injectivity is the property that matters, and monotonicity delivers it.

    Propriety holds for any measurable chaining function (Allen, Ginsbourger
    & Ziegel 2023, Prop. 3); injectivity is necessary and sufficient for
    STRICT propriety.  The hard transform is non-injective below the
    threshold and is correspondingly proper-but-not-strict there.  So what
    this test pins is not "propriety survives" -- it never was at risk --
    but that the smooth transform is injective where it is numerically
    alive, hence strictly proper on that region.

    Mathematically ``v_s`` is strictly increasing everywhere, but in floating
    point it saturates far below the threshold (softplus underflows and the
    increment falls under ``eps(t)``), so strictness is asserted only inside
    the band where the transform is numerically alive.  That saturation is
    not a bug to fix -- it is the same statement as the reach table in
    ``test_soft_chain_gradient_reach_is_set_by_softness``: softness buys a
    finite window, not a global cure.
    """
    z = torch.linspace(-20.0, 90.0, 4000, dtype=torch.float64)
    s, thr = 2.0, 40.0
    v = soft_chain(z, thr, s)
    assert torch.all(v[1:] - v[:-1] >= 0.0)          # never decreasing
    assert torch.all(v >= thr)                        # never below the floor
    band = (z > thr - 5.0 * s) & (z < 90.0)           # numerically alive region
    idx = torch.nonzero(band).flatten()
    vb = v[idx]
    assert torch.all(vb[1:] - vb[:-1] > 0.0)


def test_soft_chain_gradient_reach_is_set_by_softness():
    """How far below the threshold the score can see, quantified.

    The gradient of ``v_s`` at distance ``d`` below ``t`` is
    ``sigmoid(-d / s)``, so softness is not a cosmetic smoothing parameter --
    it is the width of the window in which an under-predicting member can be
    corrected at all.  Pinned because it is the parameter that has to be
    swept, and because it bounds what this fix can achieve: a pixel far below
    the threshold stays invisible for any softness small enough to keep the
    term tail-focused.
    """
    thr = 40.0
    for s, d, lo, hi in [
        (2.0, 5.0, 1e-2, 2e-1),      # near the threshold: usable gradient
        (2.0, 20.0, 1e-6, 1e-3),     # 20 dBZ below at s=2: effectively blind
        (5.0, 20.0, 1e-3, 1e-1),     # widening the window restores it
    ]:
        z = torch.full((1,), thr - d, requires_grad=True)
        soft_chain(z, thr, s).sum().backward()
        g = float(z.grad.abs().sum())
        assert lo < g < hi, f"softness={s} d={d}: grad {g:.3e} outside [{lo},{hi}]"


def test_soft_chaining_restores_gradient_in_the_under_prediction_region():
    """The measured failure, inverted.

    Every member sits below the threshold -- the regime this model is
    actually in (the deployed teacher produces 45% of the observed >=40 dBZ
    area on CIKM test).  With the hard transform the t=40 term is exactly
    zero with exactly zero gradient, so it cannot ask for more echo.  With
    soft chaining the gradient is finite, non-zero, and points the members
    *up* (negative gradient on a loss that is minimised).
    """
    g = torch.Generator().manual_seed(33)
    ens = (10.0 * torch.rand((1, 5, 2, 7, 7), generator=g)).requires_grad_(True)
    obs = 50.0 + 10.0 * torch.rand((1, 2, 7, 7), generator=g)  # truth IS extreme

    hard = twcrps_composite(obs, ens, thresholds=(40.0,), estimator="fair")
    hard.backward()
    # The sharp form of the failure: the loss is LARGE (every member clamps to
    # the threshold while the truth sits ~15 dBZ above it) and the gradient is
    # nevertheless exactly zero.  The objective knows the forecast is badly
    # wrong and can say nothing about which way to move.
    assert float(hard.detach()) > 10.0
    assert float(ens.grad.abs().sum()) == 0.0

    ens.grad = None
    soft = twcrps_composite(obs, ens, thresholds=(40.0,), estimator="fair",
                            chaining_softness=2.0)
    soft.backward()
    assert float(soft.detach()) > 0.0
    assert torch.isfinite(ens.grad).all()
    assert float(ens.grad.abs().sum()) > 0.0
    # descending the loss increases the members: the signal has the sign the
    # under-prediction problem needs.
    assert float(ens.grad.sum()) < 0.0


def test_soft_chaining_leaves_the_plain_term_untouched():
    """Softness must not silently change plain CRPS -- otherwise a tail
    experiment would also be a bulk experiment and nothing is attributable."""
    g = torch.Generator().manual_seed(34)
    ens = 40.0 * torch.rand((2, 6, 3, 5, 5), generator=g)
    obs = 40.0 * torch.rand((2, 3, 5, 5), generator=g)
    a = twcrps_composite(obs, ens, thresholds=(float("-inf"),), estimator="fair")
    b = twcrps_composite(obs, ens, thresholds=(float("-inf"),), estimator="fair",
                         chaining_softness=3.0)
    assert torch.equal(a, b)


def test_soft_chain_rejects_negative_softness():
    with pytest.raises(ValueError, match="softness"):
        soft_chain(torch.zeros(3), 40.0, -1.0)
