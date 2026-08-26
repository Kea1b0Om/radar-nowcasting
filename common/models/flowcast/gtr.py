"""Truncated sampling from an injected source (GTR pilot primitives).

ATFM-style truncation (arXiv 2511.06857) transplanted to this repository's
rectified-flow conventions: instead of running the Euler sampler from pure
noise at ``s = 1``, start at an interior grid point ``timesteps[start_index]``
from a caller-supplied ``source`` tensor.  In this codebase's conventions
(``rflow_objective``): ``s = t/(T-1)``, ``x_s = s*eps + (1-s)*x_0``, so the
marginal at the truncation point given a data sample is
``x_s | x_0 ~ N((1-s)*x_0, s^2 I)`` -- which is what ``noise_to_level``
constructs and what a learned Gaussian source must approximate.

Why the pilot injects sources instead of training one first: the two
zero-training arms bracket the question "can the frozen flow run from a
truncation point at all, and what does anchoring buy":

* ``oracle`` source = the TRUE future latent noised to the truncation level.
  Diagnostic ceiling only (it sees the answer); measures pure truncation
  compatibility and the fidelity/diversity curve vs ``start_index``.
* ``teacher_mean`` source = the teacher's own ensemble-mean latent noised to
  the level.  A zero-training proxy for the GTR prior's mean with the
  noise-floor covariance ``s^2 I``; a trained prior can only improve on it.

The grid is the PRODUCTION grid (``build_sampling_timesteps``), truncation is
by index into it, and ``start_index = 0`` with ``source`` equal to the
sampler's own noise draw reproduces ``sample_chunk_euler(kappa=0)`` bitwise --
the no-op control this repository requires of every new sampler (pinned by
tests).  ``start_index = euler_steps`` runs zero steps and returns the source
unchanged (also pinned).
"""

from typing import Callable, Optional

import torch

from .schedule import build_sampling_timesteps, make_chunk_index

__all__ = [
    "noise_to_level",
    "truncated_autoregressive_sample",
    "truncated_sample_chunk_euler",
]


def noise_to_level(
    x0: torch.Tensor, eps: torch.Tensor, t: int, num_train_timesteps: int
) -> torch.Tensor:
    """Forward marginal sample ``x_s = s*eps + (1-s)*x0`` at grid time ``t``."""
    if not (0 <= t <= num_train_timesteps - 1):
        raise ValueError(f"t={t} outside [0, {num_train_timesteps - 1}]")
    s = float(t) / float(num_train_timesteps - 1)
    return s * eps + (1.0 - s) * x0


def truncated_sample_chunk_euler(
    model,
    cond: torch.Tensor,
    chunk_idx: int,
    num_train_timesteps: int,
    euler_steps: int,
    source: torch.Tensor,
    start_index: int,
) -> torch.Tensor:
    """Deterministic Euler from ``timesteps[start_index]`` starting at ``source``.

    ``timesteps`` is the exact production grid for ``euler_steps``; the loop
    below is the ``kappa = 0`` body of ``sample_chunk_euler`` verbatim, so the
    ``start_index = 0`` arm is a bit-level identity (tested), not a claim.
    """
    batch_size = cond.shape[0]
    device = cond.device
    timesteps = build_sampling_timesteps(num_train_timesteps, euler_steps, device)
    if not (0 <= start_index <= euler_steps):
        raise ValueError(
            f"start_index={start_index} outside [0, {euler_steps}] "
            f"(grid has {euler_steps + 1} boundaries)"
        )
    if source.shape != cond.shape:
        raise ValueError(f"source shape {tuple(source.shape)} != cond {tuple(cond.shape)}")
    chunk_index = make_chunk_index(batch_size, chunk_idx, device)

    z = source
    for current_t, next_t in zip(timesteps[start_index:-1], timesteps[start_index + 1:]):
        t = torch.full(
            (batch_size,), int(current_t.item()), device=device, dtype=torch.long
        )
        velocity = model(z, t, cond, chunk_index)
        delta_t = (current_t - next_t).to(dtype=z.dtype) / float(num_train_timesteps - 1)
        z = z + velocity * delta_t
    return z


def truncated_autoregressive_sample(
    model,
    initial_cond: torch.Tensor,
    input_length: int,
    output_length: int,
    num_train_timesteps: int,
    euler_steps: int,
    start_index: int,
    source_fn: Callable[[int, torch.Tensor], torch.Tensor],
) -> torch.Tensor:
    """Chunked AR rollout where each chunk starts from ``source_fn(chunk_idx, cond)``.

    Mirrors ``autoregressive_sample``'s chunk loop; conditioning is the
    member's OWN previous chunk (standard AR), only the chunk's starting state
    is injected.  The per-chunk source draw is exactly the "per-member latent
    threaded through the rollout" carrier: one member = one source thread.
    """
    if output_length % input_length != 0:
        raise ValueError("output_length must be divisible by input_length.")
    num_chunks = output_length // input_length
    cond = initial_cond
    predictions = []
    for chunk_idx in range(1, num_chunks + 1):
        source = source_fn(chunk_idx, cond)
        pred_chunk = truncated_sample_chunk_euler(
            model=model,
            cond=cond,
            chunk_idx=chunk_idx,
            num_train_timesteps=num_train_timesteps,
            euler_steps=euler_steps,
            source=source,
            start_index=start_index,
        )
        predictions.append(pred_chunk)
        cond = pred_chunk
    return torch.cat(predictions, dim=1)
