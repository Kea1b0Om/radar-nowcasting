"""Bit-level gates for the truncated sampler (GTR pilot primitives).

The house rule: every new sampler ships with an exact no-op control.  Here
that is ``start_index = 0`` + the production sampler's own noise draw, which
must reproduce ``sample_chunk_euler(kappa=0)`` bitwise; and
``start_index = euler_steps``, which runs zero steps and must return the
source unchanged.  Everything else is marginal algebra and AR chaining.
"""

import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models.flowcast.gtr import (  # noqa: E402
    noise_to_level,
    truncated_autoregressive_sample,
    truncated_sample_chunk_euler,
)
from common.models.flowcast.rf_stdit import (  # noqa: E402
    autoregressive_sample,
    sample_chunk_euler,
)

T_TRAIN = 1000
STEPS = 10


class DummyVelocity(torch.nn.Module):
    """Deterministic nonlinear velocity field with the production signature."""

    def forward(self, z, t, cond, chunk_index):
        tt = t.float().reshape(-1, *([1] * (z.dim() - 1))) / (T_TRAIN - 1)
        ci = chunk_index.float().reshape(-1, *([1] * (z.dim() - 1)))
        return 0.3 * cond - 0.5 * z + 0.1 * torch.sin(z + tt) + 0.01 * ci


def _cond(seed=0, shape=(2, 5, 4, 4, 3)):
    g = torch.Generator().manual_seed(seed)
    return torch.randn(*shape, generator=g)


def test_start_index_zero_is_bitwise_identity():
    model = DummyVelocity()
    cond = _cond(1)
    ref = sample_chunk_euler(
        model, cond, 1, T_TRAIN, STEPS,
        generator=torch.Generator().manual_seed(7),
    )
    eps = torch.randn(cond.shape, generator=torch.Generator().manual_seed(7))
    got = truncated_sample_chunk_euler(
        model, cond, 1, T_TRAIN, STEPS, source=eps, start_index=0
    )
    assert torch.equal(ref, got)


def test_start_index_last_returns_source_unchanged():
    model = DummyVelocity()
    cond = _cond(2)
    src = torch.randn(cond.shape, generator=torch.Generator().manual_seed(3))
    got = truncated_sample_chunk_euler(
        model, cond, 1, T_TRAIN, STEPS, source=src, start_index=STEPS
    )
    assert torch.equal(got, src)


def test_noise_to_level_endpoints_and_midpoint():
    g = torch.Generator().manual_seed(4)
    x0 = torch.randn(2, 3, generator=g)
    eps = torch.randn(2, 3, generator=g)
    assert torch.equal(noise_to_level(x0, eps, 0, T_TRAIN), x0)
    assert torch.equal(noise_to_level(x0, eps, T_TRAIN - 1, T_TRAIN), eps)
    mid = noise_to_level(x0, eps, (T_TRAIN - 1) // 2, T_TRAIN)
    s = ((T_TRAIN - 1) // 2) / (T_TRAIN - 1)
    assert torch.allclose(mid, s * eps + (1 - s) * x0)


def test_ar_wrapper_matches_manual_chunk_loop():
    model = DummyVelocity()
    cond = _cond(5)
    eps_by_chunk = {
        1: torch.randn(cond.shape, generator=torch.Generator().manual_seed(11)),
        2: torch.randn(cond.shape, generator=torch.Generator().manual_seed(12)),
    }
    out = truncated_autoregressive_sample(
        model, cond, input_length=5, output_length=10,
        num_train_timesteps=T_TRAIN, euler_steps=STEPS, start_index=4,
        source_fn=lambda k, c: eps_by_chunk[k],
    )
    c = cond
    chunks = []
    for k in (1, 2):
        p = truncated_sample_chunk_euler(
            model, c, k, T_TRAIN, STEPS, source=eps_by_chunk[k], start_index=4
        )
        chunks.append(p)
        c = p
    assert torch.equal(out, torch.cat(chunks, dim=1))


def test_full_grid_ar_identity_against_production_wrapper():
    """start_index=0 with the production noise draws reproduces the full AR
    sampler bitwise -- the chunk-level identity extended through the rollout."""
    model = DummyVelocity()
    cond = _cond(6)
    g = torch.Generator().manual_seed(21)
    ref = autoregressive_sample(
        model, cond, input_length=5, output_length=10,
        num_train_timesteps=T_TRAIN, euler_steps=STEPS, generator=g,
    )
    g2 = torch.Generator().manual_seed(21)
    draws = {k: torch.randn(cond.shape, generator=g2) for k in (1, 2)}
    got = truncated_autoregressive_sample(
        model, cond, input_length=5, output_length=10,
        num_train_timesteps=T_TRAIN, euler_steps=STEPS, start_index=0,
        source_fn=lambda k, c: draws[k],
    )
    assert torch.equal(ref, got)


def test_bounds_and_shape_guards():
    model = DummyVelocity()
    cond = _cond(8)
    src = torch.zeros_like(cond)
    for bad in (-1, STEPS + 1):
        try:
            truncated_sample_chunk_euler(
                model, cond, 1, T_TRAIN, STEPS, source=src, start_index=bad
            )
            raise AssertionError("should have raised")
        except ValueError:
            pass
    try:
        truncated_sample_chunk_euler(
            model, cond, 1, T_TRAIN, STEPS, source=src[:1], start_index=2
        )
        raise AssertionError("should have raised")
    except ValueError:
        pass
