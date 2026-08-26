"""Full check of the GRPO pieces before any GPU time is spent on RL.

The point of this file is that a policy-gradient run fails *silently* when the
log-prob is wrong: the loss goes down, the reward moves, and nothing raises.  So
every load-bearing property is asserted directly rather than inferred:

* the per-step log-prob is a genuine normalised density (quadrature, not a
  formula comparison against itself);
* the policy we score is bit-for-bit the sampler we deploy - if these drift, RL
  optimises a model that is never actually run;
* the gradient reaches the velocity and provably does *not* reach the std;
* the degenerate paths that this model actually produces (11.45% of groups score
  identically under a single-threshold CSI reward) return zero, not NaN.
"""

import math
import os
import sys

import pytest
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models.flowcast.grpo import (  # noqa: E402
    clipped_policy_loss,
    group_advantages,
    kl_k3,
    sde_noise_std,
    sde_step_with_logprob,
)
from common.models.flowcast.rf_stdit import sample_chunk_euler  # noqa: E402
from common.models.flowcast.schedule import build_sampling_timesteps  # noqa: E402

TIMESTEPS = 1000


class LinearVelocity:
    """A deterministic, differentiable stand-in for the network."""

    def __init__(self, gain=0.3, bias=0.05):
        self.gain, self.bias = gain, bias

    def __call__(self, z, t, cond, chunk_index):
        return self.gain * z + self.bias


# ------------------------------------------------------------ density
def test_log_prob_integrates_to_one():
    """Quadrature check: the step really is a normalised density in x_next."""
    z = torch.zeros((1, 1, 1, 1, 1))
    v = torch.full_like(z, 0.4)
    _, _, mean, std = sde_step_with_logprob(
        z, v, 0.6, 0.5, kappa=0.9, prev_sample=z, reduction="sum"
    )
    grid = torch.linspace(float(mean) - 8 * std, float(mean) + 8 * std, 20001)
    cand = grid.view(-1, 1, 1, 1, 1)
    _, log_prob, _, _ = sde_step_with_logprob(
        z, v, 0.6, 0.5, kappa=0.9, prev_sample=cand, reduction="sum"
    )
    integral = torch.trapz(torch.exp(log_prob), grid)
    assert float(integral) == pytest.approx(1.0, abs=1e-4)


def test_log_prob_matches_closed_form_gaussian():
    z = torch.randn(3, 2, 2, 2, 1)
    v = torch.randn_like(z)
    x_next = torch.randn_like(z)
    _, log_prob, mean, std = sde_step_with_logprob(
        z, v, 0.4, 0.3, kappa=0.7, prev_sample=x_next, reduction="sum"
    )
    expected = torch.distributions.Normal(mean, std).log_prob(x_next)
    expected = expected.sum(dim=tuple(range(1, expected.ndim)))
    assert torch.allclose(log_prob, expected, atol=1e-5)


def test_sampled_step_is_calibrated_to_its_own_mean_and_std():
    """Monte-Carlo: the draws must match the mean/std the log-prob assumes."""
    z = torch.zeros((60000, 1, 1, 1, 1))
    v = torch.full_like(z, -0.2)
    g = torch.Generator().manual_seed(4)
    draw, _, mean, std = sde_step_with_logprob(z, v, 0.5, 0.4, kappa=0.8, generator=g)
    assert float(draw.mean()) == pytest.approx(float(mean[0]), abs=4e-3)
    assert float(draw.std()) == pytest.approx(std, rel=0.02)


def test_reduction_mean_and_sum_differ_by_the_dimension_count():
    """Flow-GRPO reduces with mean; that is the density divided by D, which is
    why their clip_range is 1e-3..1e-5 rather than PPO's 0.2."""
    z = torch.randn(2, 3, 4, 4, 1)
    v = torch.randn_like(z)
    x = torch.randn_like(z)
    kw = dict(kappa=0.6, prev_sample=x)
    _, lp_mean, _, _ = sde_step_with_logprob(z, v, 0.5, 0.4, reduction="mean", **kw)
    _, lp_sum, _, _ = sde_step_with_logprob(z, v, 0.5, 0.4, reduction="sum", **kw)
    dims = z[0].numel()
    assert dims == 3 * 4 * 4 * 1
    assert torch.allclose(lp_sum, lp_mean * dims, rtol=1e-5)


def test_zero_kappa_is_rejected_because_it_has_no_density():
    with pytest.raises(ValueError, match="no density"):
        sde_step_with_logprob(torch.zeros(1, 1), torch.zeros(1, 1), 0.5, 0.4, kappa=0.0)


def test_reversed_time_order_is_rejected():
    with pytest.raises(ValueError, match="s_next < s_cur"):
        sde_step_with_logprob(torch.zeros(1, 1), torch.zeros(1, 1), 0.4, 0.5, kappa=0.5)


# ------------------------------------------------------------ schedules
def test_sqrt_s_schedule_is_finite_at_the_grid_start():
    """This repository's grid starts at exactly s = 1."""
    assert sde_noise_std(1.0, 0.9, "sqrt_s") == pytest.approx(0.9)


def test_flow_grpo_schedule_has_a_pole_at_one_and_is_clamped():
    """Their sigma = noise_level*sqrt(s/(1-s)) diverges where our grid begins."""
    clamped = sde_noise_std(1.0, 0.9, "flow_grpo", max_s=0.999)
    assert math.isfinite(clamped)
    assert clamped == pytest.approx(0.9 * math.sqrt(0.999 / 0.001), rel=1e-6)
    assert clamped > 20 * sde_noise_std(1.0, 0.9, "sqrt_s")


def test_flow_grpo_schedule_matches_the_reference_formula_mid_trajectory():
    s, noise_level = 0.5, 0.9
    assert sde_noise_std(s, noise_level, "flow_grpo") == pytest.approx(
        noise_level * math.sqrt(s / (1 - s))
    )


# ------------------------------------------------------ gradient plumbing
def test_gradient_reaches_the_velocity():
    z = torch.randn(2, 1, 2, 2, 1)
    v = torch.randn_like(z).requires_grad_(True)
    x = torch.randn_like(z)
    _, log_prob, _, _ = sde_step_with_logprob(
        z, v, 0.5, 0.4, kappa=0.7, prev_sample=x, reduction="sum"
    )
    log_prob.sum().backward()
    assert v.grad is not None and float(v.grad.abs().max()) > 0


def test_gradient_does_not_flow_through_the_sampled_path():
    """``prev_sample`` is data, not a differentiable function of the policy: the
    score function must come from the mean only."""
    z = torch.randn(2, 1, 2, 2, 1)
    v = torch.randn_like(z).requires_grad_(True)
    draw, log_prob, _, _ = sde_step_with_logprob(
        z, v, 0.5, 0.4, kappa=0.7, generator=torch.Generator().manual_seed(1),
        reduction="sum",
    )
    assert not draw.requires_grad or draw.grad_fn is not None
    log_prob.sum().backward()
    grad_a = v.grad.clone()
    v.grad = None
    _, log_prob2, _, _ = sde_step_with_logprob(
        z, v, 0.5, 0.4, kappa=0.7, prev_sample=draw.detach(), reduction="sum"
    )
    log_prob2.sum().backward()
    assert torch.allclose(grad_a, v.grad, atol=1e-6)


def test_std_is_independent_of_the_velocity():
    z = torch.randn(2, 1, 2, 2, 1)
    kw = dict(s_cur=0.5, s_next=0.4, kappa=0.7, prev_sample=torch.randn_like(z))
    _, _, _, std_a = sde_step_with_logprob(z, torch.zeros_like(z), **kw)
    _, _, _, std_b = sde_step_with_logprob(z, torch.full_like(z, 9.0), **kw)
    assert std_a == std_b


# --------------------------------------- policy == deployed sampler
@pytest.mark.parametrize("compensate", [True, False])
def test_logprob_stepper_reproduces_the_deployed_sampler(compensate):
    """If these ever diverge, RL optimises a policy that is never actually run.

    Not bitwise: ``sample_chunk_euler`` forms ``ds`` with tensor arithmetic and
    this module with a Python float, which can differ by one float32 ulp.  The
    tolerance covers exactly that and nothing larger.
    """
    cond = torch.zeros((4, 2, 3, 3, 1), dtype=torch.float32)
    model = LinearVelocity()
    kappa, steps = 0.8, 6

    reference = sample_chunk_euler(
        model=model, cond=cond, chunk_idx=1, num_train_timesteps=TIMESTEPS,
        euler_steps=steps, generator=torch.Generator().manual_seed(9),
        sde_noise_scale=kappa, sde_drift_compensation=compensate,
    )

    grid = build_sampling_timesteps(TIMESTEPS, steps, torch.device("cpu"))
    scale = float(TIMESTEPS - 1)
    g = torch.Generator().manual_seed(9)
    z = torch.randn(cond.shape, generator=g)
    chunk_index = torch.full((cond.shape[0],), 1, dtype=torch.long)
    for cur, nxt in zip(grid[:-1], grid[1:]):
        t = torch.full((cond.shape[0],), int(cur.item()), dtype=torch.long)
        v = model(z, t, cond, chunk_index)
        s_cur, s_next = float(cur.item()) / scale, float(nxt.item()) / scale
        if s_next <= 0.0:
            # The deployed sampler suppresses the *noise* on the step landing at
            # s = 0 but still applies the drift compensation.  That step is a
            # deterministic map: it has no density, contributes nothing to the
            # policy gradient, and belongs to the environment rather than the
            # policy.  Getting this wrong is a 4% output error, not an ulp.
            eps_hat = z - (1.0 - s_cur) * v
            ds = s_cur - s_next
            z = z + v * ds
            if compensate:
                sigma_s = sde_noise_std(s_cur, kappa, "sqrt_s")
                z = z - (sigma_s * sigma_s / (2.0 * s_cur)) * ds * eps_hat
            continue
        z, _, _, _ = sde_step_with_logprob(
            z, v, s_cur, s_next, kappa=kappa, compensate=compensate, generator=g,
        )
    assert torch.allclose(reference, z, rtol=1e-5, atol=1e-6)


@pytest.mark.parametrize("dtype", [torch.float16, torch.bfloat16])
def test_half_precision_input_is_promoted_for_the_density(dtype):
    """The reference carries an explicit 'bf16 can overflow' warning on this
    computation; this repository samples in fp16, which is worse."""
    z = (torch.randn(2, 1, 4, 4, 1) * 30.0).to(dtype)
    v = (torch.randn(2, 1, 4, 4, 1) * 30.0).to(dtype)
    x = (torch.randn(2, 1, 4, 4, 1) * 30.0).to(dtype)
    _, log_prob, mean, _ = sde_step_with_logprob(
        z, v, 0.5, 0.4, kappa=0.7, prev_sample=x, reduction="sum"
    )
    assert mean.dtype == torch.float32
    assert log_prob.dtype == torch.float32
    assert torch.isfinite(log_prob).all()


def test_half_precision_draw_keeps_the_deployed_rng_stream():
    """Noise is drawn in the caller's dtype, so a promoted density computation
    cannot silently desynchronise the sampler's random stream."""
    z = torch.zeros(3, 1, 2, 2, 1, dtype=torch.float16)
    v = torch.zeros_like(z)
    g_step = torch.Generator().manual_seed(21)
    draw, _, _, _ = sde_step_with_logprob(z, v, 0.5, 0.4, kappa=0.7, generator=g_step)
    g_ref = torch.Generator().manual_seed(21)
    ref_noise = torch.randn(z.shape, dtype=torch.float16, generator=g_ref)
    assert torch.equal(g_step.get_state(), g_ref.get_state())
    _, _, mean, std = sde_step_with_logprob(
        z, v, 0.5, 0.4, kappa=0.7, prev_sample=z
    )
    assert torch.allclose(draw, (mean.half() + std * ref_noise).float(), atol=1e-3)


def test_same_policy_gives_ratio_exactly_one():
    z = torch.randn(3, 1, 2, 2, 1)
    v = torch.randn_like(z)
    x = torch.randn_like(z)
    kw = dict(s_cur=0.5, s_next=0.4, kappa=0.7, prev_sample=x)
    _, lp_a, _, _ = sde_step_with_logprob(z, v, **kw)
    _, lp_b, _, _ = sde_step_with_logprob(z, v, **kw)
    assert torch.equal(lp_a, lp_b)
    assert torch.allclose(torch.exp(lp_a - lp_b), torch.ones_like(lp_a))


# ------------------------------------------------------------ advantages
def test_advantages_are_zero_mean_within_each_group():
    rewards = torch.rand(5, 8)
    adv = group_advantages(rewards, mode="group_std")
    assert torch.allclose(adv.mean(dim=1), torch.zeros(5), atol=1e-6)


@pytest.mark.parametrize("mode", ["global_std", "group_std"])
def test_degenerate_group_yields_exactly_zero(mode):
    """11.45% of groups on this model score identically under a csi40 reward.

    Exactly zero, not merely finite: ``mean`` over k identical float32 values is
    an ulp away from the value, and a clamped denominator turns that residue
    into an order-1 advantage with an arbitrary sign.  This reproduced on the
    server (torch 2.5.1, x86) while passing locally - a reduction-order
    accident, which is why the assertion is on exact zeros.
    """
    torch.manual_seed(0)
    rewards = torch.cat([torch.rand(4, 8), torch.full((1, 8), 0.42)], dim=0)
    adv = group_advantages(rewards, mode=mode)
    assert torch.isfinite(adv).all()
    assert torch.equal(adv[-1], torch.zeros(8))


@pytest.mark.parametrize("mode", ["global_std", "group_std"])
def test_degenerate_group_zeroing_survives_a_float32_ulp_residue(mode):
    """The concrete numbers from the server failure, pinned."""
    rewards = torch.full((3, 8), 0.42, dtype=torch.float32)
    rewards[0] = torch.linspace(0.0, 1.0, 8)
    adv = group_advantages(rewards, mode=mode)
    assert torch.equal(adv[1], torch.zeros(8))
    assert torch.equal(adv[2], torch.zeros(8))
    assert float(adv[0].abs().max()) > 0.5


def test_narrow_but_nondegenerate_group_is_not_amplified_in_group_std_mode():
    """A spread of 1e-6 must not be renormalised into a full-magnitude signal."""
    rewards = torch.zeros(2, 8)
    rewards[0] = torch.linspace(0.0, 1.0, 8)
    rewards[1] = 0.5 + torch.linspace(0.0, 1e-6, 8)
    floored = group_advantages(rewards, mode="group_std", min_denom_frac=0.05)
    faithful = group_advantages(rewards, mode="group_std", min_denom_frac=0.0)
    assert float(floored[1].abs().max()) < 0.01
    assert float(faithful[1].abs().max()) > 0.9  # the reference behaviour


def test_global_std_keeps_narrow_groups_small_while_group_std_amplifies_them():
    """The choice that matters here: measured within-group spread is ~2% of the
    between-event spread, so the denominator decides whether narrow groups
    contribute proportionally little or get renormalised up into noise."""
    wide = torch.tensor([[0.0, 1.0, 2.0, 3.0]])
    narrow = torch.tensor([[0.50, 0.50, 0.51, 0.51]])
    rewards = torch.cat([wide, narrow], dim=0)
    glob = group_advantages(rewards, mode="global_std")
    # min_denom_frac=0 reproduces the reference semantics this test documents;
    # the module's non-zero default deliberately suppresses the amplification.
    per_group = group_advantages(rewards, mode="group_std", min_denom_frac=0.0)
    glob_ratio = float(glob[1].abs().max() / glob[0].abs().max())
    group_ratio = float(per_group[1].abs().max() / per_group[0].abs().max())
    # global_std: the narrow group is ~100x weaker, in proportion to its spread
    assert glob_ratio < 0.02
    # group_std: renormalised to the same order regardless of how narrow it was
    # (not exactly equal - the max depends on the shape of the group, and a
    # two-point group maxes at exactly 1 while a four-point uniform one maxes
    # at 1.34)
    assert group_ratio > 0.5


# ------------------------------------------------------------ objective
def test_unclipped_region_is_plain_policy_gradient():
    lp = torch.zeros(6)
    adv = torch.randn(6)
    loss, stats = clipped_policy_loss(lp, lp, adv, clip_range=0.2)
    assert float(loss) == pytest.approx(float((-adv).mean()), abs=1e-6)
    assert stats["ratio_mean"] == pytest.approx(1.0)
    assert stats["clip_fraction"] == pytest.approx(0.0)


def test_clip_binds_and_is_reported():
    adv = torch.tensor([1.0, 1.0, -1.0, -1.0])
    lp_new = torch.tensor([0.5, -0.5, 0.5, -0.5])
    lp_old = torch.zeros(4)
    _, stats = clipped_policy_loss(lp_new, lp_old, adv, clip_range=1e-3)
    assert stats["clip_fraction"] > 0.0
    assert stats["ratio_max_abs_dev"] > 0.5


def test_clip_is_a_pessimistic_bound():
    """max(unclipped, clipped) must never be below the unclipped surrogate."""
    torch.manual_seed(0)
    adv = torch.randn(256)
    delta = torch.randn(256) * 0.05
    loss, _ = clipped_policy_loss(delta, torch.zeros(256), adv, clip_range=0.01)
    plain = float((-adv * torch.exp(delta)).mean())
    assert float(loss) >= plain - 1e-6


# ------------------------------------------------------------ KL anchor
def test_k3_is_non_negative_where_the_naive_estimator_is_not():
    torch.manual_seed(3)
    lp_new = torch.randn(4096)
    lp_ref = lp_new + torch.randn(4096) * 0.3
    naive = float((lp_ref - lp_new).mean())
    k3 = float(kl_k3(lp_new, lp_ref))
    assert k3 >= 0.0
    assert (lp_ref - lp_new).min() < 0  # the naive per-sample term does go negative
    assert k3 > abs(naive)


def test_k3_is_zero_for_identical_policies():
    lp = torch.randn(64)
    assert float(kl_k3(lp, lp)) == pytest.approx(0.0, abs=1e-9)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
