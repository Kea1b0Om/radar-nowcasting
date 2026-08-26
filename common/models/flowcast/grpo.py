"""Per-step log-probabilities and GRPO objective pieces for the FlowCast sampler.

Policy-gradient RL on a flow model needs the sampler to be a *stochastic policy*
with a tractable per-step density.  The deterministic Euler ODE has none, which
is the actual reason Flow-GRPO converts the ODE to an SDE -- not, as is easy to
assume, to widen exploration: the marginal-preserving SDE provably leaves the
terminal distribution alone (see ``tests/test_sde_sampler.py``).

Correspondence with the reference implementation
------------------------------------------------
Flow-GRPO (``flow_grpo/diffusers_patch/sd3_sde_with_logprob.py``) writes, in
diffusers' convention where ``model_output = eps - x_0`` and ``dt < 0``::

    std_dev_t   = sqrt(sigma / (1 - sigma)) * noise_level
    mean        = sample*(1 + std_dev_t^2/(2*sigma)*dt)
                  + model_output*(1 + std_dev_t^2*(1-sigma)/(2*sigma))*dt
    prev_sample = mean + std_dev_t * sqrt(-dt) * noise

Grouping their two correction terms gives ``(std^2/(2*sigma))*dt*[x + (1-sigma)*v]``
and ``x + (1-sigma)*v`` is exactly ``E[eps | x]`` in that convention.  This
repository uses the opposite sign for the velocity (``v = x_0 - eps``) and a
positive step ``ds``, under which the same update reads::

    E[eps | x_s] = x_s - (1 - s) * v
    mean         = x_s + v*ds - (sigma_s^2 / (2*s)) * ds * E[eps | x_s]
    x_next       = mean + sigma_s * sqrt(ds) * noise

which is the update already implemented in ``sample_chunk_euler``.  The two
derivations were done independently and agree term by term.

Three differences from the reference are deliberate and are pinned by tests:

1.  **Noise schedule.**  Flow-GRPO uses ``sigma_s = noise_level*sqrt(s/(1-s))``,
    which *diverges at s = 1*.  This repository's grid starts at exactly
    ``s = 1`` (``t = num_train_timesteps - 1``), so that schedule is unusable
    here without a clamp; ``max_s`` provides it.  The ``"sqrt_s"`` schedule
    (``sigma_s = kappa*sqrt(s)``) is finite everywhere and is the default.
2.  **Reduction.**  Flow-GRPO reduces the log-prob with ``mean`` over all
    non-batch dimensions, not ``sum``.  That is not a log density -- it is the
    density divided by the dimension count -- and it is what makes their
    ``clip_range`` of 1e-3..1e-5 the right order of magnitude.  Both reductions
    are exposed; ``"sum"`` is the true log density and is what the normalization
    test checks.
3.  **Advantage denominator.**  ``global_std=True`` in their configs divides by a
    std pooled over the whole batch rather than per group.  With the narrow
    within-group reward spread measured on this model, that choice decides
    whether narrow groups contribute proportionally small gradients (global) or
    get renormalized up into noise (per-group).  Both are implemented.
"""

import math
from typing import Literal, Optional, Tuple

import torch

__all__ = [
    "clipped_policy_loss",
    "group_advantages",
    "kl_k3",
    "sde_noise_std",
    "sde_step_with_logprob",
]

Schedule = Literal["sqrt_s", "flow_grpo"]
Reduction = Literal["mean", "sum", "none"]


def sde_noise_std(
    s: float, kappa: float, schedule: Schedule = "sqrt_s", max_s: float = 0.999
) -> float:
    """Diffusion coefficient ``sigma_s`` at flow time ``s``.

    ``max_s`` clamps the ``flow_grpo`` schedule away from its pole at ``s = 1``.
    It is a no-op for ``sqrt_s``.
    """
    if kappa < 0.0:
        raise ValueError(f"kappa must be non-negative, got {kappa}")
    if not 0.0 <= s <= 1.0:
        raise ValueError(f"s must lie in [0, 1], got {s}")
    if schedule == "sqrt_s":
        return kappa * math.sqrt(s)
    if schedule == "flow_grpo":
        s_eff = min(s, max_s)
        return kappa * math.sqrt(s_eff / max(1.0 - s_eff, 1e-12))
    raise ValueError(f"unknown schedule {schedule!r}")


def sde_step_with_logprob(
    z: torch.Tensor,
    velocity: torch.Tensor,
    s_cur: float,
    s_next: float,
    *,
    kappa: float,
    schedule: Schedule = "sqrt_s",
    compensate: bool = True,
    generator: Optional[torch.Generator] = None,
    prev_sample: Optional[torch.Tensor] = None,
    reduction: Reduction = "mean",
    max_s: float = 0.999,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    """One stochastic Euler step, returning ``(x_next, log_prob, mean, std)``.

    ``prev_sample`` supplies an already-drawn ``x_next`` so the *current* policy
    can score a trajectory sampled by an older one -- the importance ratio in
    GRPO is exactly ``exp(logp_new - logp_old)`` over the same stored path.
    When it is ``None`` a fresh sample is drawn.

    The returned std never depends on ``velocity``; the whole gradient path runs
    through the mean, which is what makes the score function well behaved.  That
    property is asserted in the tests rather than assumed.
    """
    if kappa <= 0.0:
        raise ValueError(
            "kappa must be strictly positive: a deterministic step has no "
            "density, so no per-step log-prob and no policy gradient."
        )
    if not s_next < s_cur:
        raise ValueError(f"expected s_next < s_cur, got {s_next} >= {s_cur}")

    # The reference implementation carries an explicit warning here -- "bf16 can
    # overflow when computing prev_sample_mean, we must convert all variables to
    # fp32" -- and this repository samples in fp16, which is worse.  The step is
    # therefore computed in fp32 and cast back at the end, so the log-prob never
    # inherits a half-precision mean.
    in_dtype = z.dtype
    z = z.float()
    velocity = velocity.float()
    if prev_sample is not None:
        prev_sample = prev_sample.float()

    ds = s_cur - s_next
    sigma_s = sde_noise_std(s_cur, kappa, schedule, max_s=max_s)
    std = sigma_s * math.sqrt(ds)
    if std <= 0.0:
        raise ValueError("degenerate step std; increase kappa or the step size")

    mean = z + velocity * ds
    if compensate:
        eps_hat = z - (1.0 - s_cur) * velocity
        mean = mean - (sigma_s * sigma_s / (2.0 * max(s_cur, 1e-12))) * ds * eps_hat

    if prev_sample is None:
        # Drawn in the caller's dtype so the RNG stream matches the deployed
        # sampler exactly, then promoted for the density computation.
        noise = torch.randn(
            z.shape, device=z.device, dtype=in_dtype, generator=generator
        )
        prev_sample = (mean.to(in_dtype) + std * noise).float()

    log_prob = (
        -((prev_sample.detach() - mean) ** 2) / (2.0 * std * std)
        - math.log(std)
        - 0.5 * math.log(2.0 * math.pi)
    )
    if reduction == "mean":
        log_prob = log_prob.mean(dim=tuple(range(1, log_prob.ndim)))
    elif reduction == "sum":
        log_prob = log_prob.sum(dim=tuple(range(1, log_prob.ndim)))
    elif reduction != "none":
        raise ValueError(f"unknown reduction {reduction!r}")
    return prev_sample, log_prob, mean, std


def group_advantages(
    rewards: torch.Tensor,
    mode: Literal["global_std", "group_std"] = "global_std",
    eps: float = 1e-8,
    degenerate_atol: float = 1e-12,
    min_denom_frac: float = 0.05,
) -> torch.Tensor:
    """Group-relative advantages for rewards shaped ``(num_groups, group_size)``.

    Two guards, both of which are load-bearing on this model rather than
    defensive boilerplate:

    ``degenerate_atol`` -- a group whose members all score identically must
    contribute *exactly* zero.  Clamping the denominator alone is not enough:
    ``mean`` over k identical float32 values differs from the value itself by an
    ulp, so ``centered`` is on the order of 1e-7 rather than 0, and dividing that
    by a clamped near-zero denominator manufactures an advantage of order 1 with
    an arbitrary sign.  Measured on this project, 11.45% of groups are degenerate
    under a single-threshold CSI reward, so that is roughly one in nine gradient
    contributions turned into signed noise.  Groups whose max-min spread is at or
    below ``degenerate_atol`` are zeroed explicitly.

    ``min_denom_frac`` -- in ``group_std`` mode a merely *narrow* group (spread
    1e-6, not 0) would otherwise be renormalised to full magnitude and dominate
    the batch.  The per-group denominator is floored at this fraction of the
    global std.  This is a deliberate deviation from the reference
    implementation, which sidesteps the issue by defaulting to
    ``global_std=True``; set it to 0.0 to reproduce the reference exactly.
    """
    if rewards.ndim != 2:
        raise ValueError(f"rewards must be (num_groups, group_size), got {tuple(rewards.shape)}")
    centered = rewards - rewards.mean(dim=1, keepdim=True)
    global_std = rewards.std(unbiased=False)
    if mode == "global_std":
        denom = global_std.expand_as(centered)
    elif mode == "group_std":
        denom = rewards.std(dim=1, keepdim=True, unbiased=False)
        if min_denom_frac > 0.0:
            denom = torch.maximum(denom, global_std * min_denom_frac)
        denom = denom.expand_as(centered)
    else:
        raise ValueError(f"unknown mode {mode!r}")

    advantages = centered / denom.clamp_min(eps)
    spread = rewards.amax(dim=1, keepdim=True) - rewards.amin(dim=1, keepdim=True)
    degenerate = (spread <= degenerate_atol).expand_as(advantages)
    return torch.where(degenerate, torch.zeros_like(advantages), advantages)


def clipped_policy_loss(
    log_prob_new: torch.Tensor,
    log_prob_old: torch.Tensor,
    advantages: torch.Tensor,
    clip_range: float,
) -> Tuple[torch.Tensor, dict]:
    """PPO-style clipped surrogate (minimised), plus diagnostics.

    Returns the loss and a dict with the mean ratio and the clipped fraction --
    a clipped fraction pinned at 0 means the clip range is inert and the run is
    effectively unguarded REINFORCE; pinned at 1 means every step is saturating.
    """
    ratio = torch.exp(log_prob_new - log_prob_old)
    unclipped = -advantages * ratio
    clipped = -advantages * ratio.clamp(1.0 - clip_range, 1.0 + clip_range)
    loss = torch.maximum(unclipped, clipped).mean()
    with torch.no_grad():
        stats = {
            "ratio_mean": float(ratio.mean()),
            "ratio_max_abs_dev": float((ratio - 1.0).abs().max()),
            "clip_fraction": float((torch.maximum(unclipped, clipped) != unclipped).float().mean()),
        }
    return loss, stats


def kl_k3(log_prob_new: torch.Tensor, log_prob_ref: torch.Tensor) -> torch.Tensor:
    """Schulman's low-variance, non-negative KL estimator ``exp(d) - d - 1``.

    Used as the ``beta`` anchor term.  Non-negativity is asserted in the tests:
    the naive ``logp_ref - logp_new`` estimator goes negative sample-wise and
    then a KL penalty can *reward* drifting from the reference.
    """
    diff = log_prob_ref - log_prob_new
    return (torch.exp(diff) - diff - 1.0).mean()
