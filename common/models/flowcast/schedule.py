"""Euler timestep grid shared by FlowCast sampling and the RMLF bridge.

This module is intentionally free of any STDiT / rotary-embedding import so
that the RMLF bridge and its tests can reuse the *exact* deployment grid
without pulling in the backbone.  ``rf_stdit`` re-exports both helpers, so
``from common.models.flowcast.rf_stdit import make_chunk_index`` keeps
working unchanged.
"""

import torch


def build_sampling_timesteps(num_train_timesteps, euler_steps, device):
    if num_train_timesteps < 2:
        raise ValueError("num_train_timesteps must be at least 2.")
    if euler_steps < 1:
        raise ValueError("euler_steps must be at least 1.")

    boundaries = torch.linspace(
        num_train_timesteps - 1,
        0,
        steps=euler_steps + 1,
        device=device,
    )
    boundaries = boundaries.round().long()
    boundaries[0] = num_train_timesteps - 1
    boundaries[-1] = 0

    for idx in range(1, boundaries.numel()):
        max_allowed = max(boundaries[idx - 1].item() - 1, 0)
        if boundaries[idx].item() > max_allowed:
            boundaries[idx] = max_allowed

    if torch.any(boundaries[1:] >= boundaries[:-1]):
        raise ValueError(
            "Invalid Euler schedule. Increase num_train_timesteps or reduce euler_steps."
        )
    return boundaries


def make_chunk_index(batch_size, chunk_idx, device):
    return torch.full((batch_size,), chunk_idx, dtype=torch.long, device=device)
