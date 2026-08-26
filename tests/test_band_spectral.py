"""Tests for the radial band decomposition and band-wise ensemble statistics.

The two load-bearing tests:

* ``test_negative_vertical_frequency_lands_in_lowest_band`` -- regression
  against the DRIFT-Net RadialBandGate bug (row index used as frequency
  magnitude, which throws negative low frequencies into the top band).
* ``test_shifted_members_visible_to_spatial_spread_only`` -- the design
  insight the whole gated-rollout candidate rests on: displacement
  disagreement between members is invisible to power-spectrum spread and
  visible to phase-preserving spatial spread.  If this stops holding, the
  calibration A/B loses its meaning.
"""

import os
import sys

import pytest
import torch

sys.path.append(os.getcwd())

from common.metrics.band_spectral import (
    DEFAULT_BAND_EDGES,
    band_energy,
    bandpass_decompose,
    ensemble_mean_band_rmse,
    power_band_spread,
    radial_band_masks,
    spatial_band_spread,
)

torch.manual_seed(0)


@pytest.mark.parametrize("height,width", [(32, 32), (101, 101), (64, 48)])
def test_masks_partition_the_grid(height, width):
    masks = radial_band_masks(height, width)
    coverage = masks.sum(dim=0)
    assert bool((coverage == 1).all())


def test_bad_edges_raise():
    with pytest.raises(ValueError):
        radial_band_masks(32, 32, band_edges=(0.1, 0.5, 1.0))
    with pytest.raises(ValueError):
        radial_band_masks(32, 32, band_edges=(0.0, 0.5, 0.9))
    with pytest.raises(ValueError):
        radial_band_masks(32, 32, band_edges=(0.0, 0.5, 0.5, 1.0))


def test_negative_vertical_frequency_lands_in_lowest_band():
    """A one-cycle vertical cosine is as low-frequency as it gets.

    Its rFFT2 support sits on rows 1 and H-1 (the +1/H and -1/H bins).  A
    row-index band assignment puts row H-1 in the top band; a frequency-
    correct assignment puts all of it in band 0.
    """
    height = width = 64
    y = torch.arange(height, dtype=torch.float64)
    field = torch.cos(2 * torch.pi * y / height)[:, None].expand(height, width)
    masks = radial_band_masks(height, width)
    energies = band_energy(field, masks)
    total = energies.sum()
    assert total > 0
    assert energies[0] / total > 0.999999
    bands = bandpass_decompose(field, masks)
    assert torch.allclose(bands[0], field, atol=1e-8)
    assert bands[1:].abs().max() < 1e-8


def test_parseval_band_energies_sum_to_signal_energy():
    x = torch.randn(3, 101, 101, dtype=torch.float64)
    masks = radial_band_masks(101, 101)
    energies = band_energy(x, masks)
    assert torch.allclose(
        energies.sum(dim=-1), x.pow(2).sum(dim=(-2, -1)), rtol=1e-10
    )


def test_band_sum_reconstructs_signal():
    x = torch.randn(2, 33, 47, dtype=torch.float64)
    masks = radial_band_masks(33, 47)
    bands = bandpass_decompose(x, masks)
    assert torch.allclose(bands.sum(dim=-3), x, atol=1e-10)


def _smooth_field(height, width, generator=None):
    """Random field with a steep spectrum (radar-like)."""
    noise = torch.randn(height, width, dtype=torch.float64, generator=generator)
    spectrum = torch.fft.rfft2(noise)
    fy = torch.fft.fftfreq(height).abs()
    fx = torch.fft.rfftfreq(width)
    radius = torch.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
    spectrum = spectrum / (1.0 + (radius / 0.05) ** 2)
    return torch.fft.irfft2(spectrum, s=(height, width))


def test_shifted_members_visible_to_spatial_spread_only():
    height = width = 64
    generator = torch.Generator().manual_seed(7)
    base = _smooth_field(height, width, generator)
    members = torch.stack(
        [
            torch.roll(base, shifts=(dy, dx), dims=(-2, -1))
            for dy, dx in [(0, 0), (3, -2), (-5, 4), (2, 6)]
        ]
    )[:, None]  # (M, T=1, H, W)
    masks = radial_band_masks(height, width)

    power = power_band_spread(members, masks)
    spatial = spatial_band_spread(members, masks)

    # circular shifts leave every band amplitude untouched
    assert power.abs().max() < 1e-10
    # but the band-passed fields disagree pixel-wise
    assert spatial.sum() > 1e-3


def test_spread_tracks_per_band_noise_amplitude():
    height = width = 64
    truth = _smooth_field(height, width, torch.Generator().manual_seed(1))
    masks = radial_band_masks(height, width)
    num_bands = masks.shape[0]

    # inject noise restricted to band 3, scaled up vs band 1
    def banded_noise(band, scale, seed):
        raw = torch.randn(
            height, width, dtype=torch.float64,
            generator=torch.Generator().manual_seed(seed),
        )
        return bandpass_decompose(raw, masks)[band] * scale

    members = torch.stack(
        [
            truth + banded_noise(1, 0.1, 10 + m) + banded_noise(3, 1.0, 100 + m)
            for m in range(4)
        ]
    )[:, None]
    spread = spatial_band_spread(members, masks)[0]  # (J,)
    assert spread[3] > 5 * spread[1]
    quiet = [j for j in range(num_bands) if j not in (1, 3)]
    assert spread[3] > 5 * spread[quiet].max()


def test_perfect_members_have_zero_mean_rmse():
    truth = _smooth_field(32, 32, torch.Generator().manual_seed(2))[None]
    members = truth[None].expand(3, -1, -1, -1).clone()
    masks = radial_band_masks(32, 32)
    rmse = ensemble_mean_band_rmse(members, truth, masks)
    assert rmse.abs().max() < 1e-10


def test_single_member_raises():
    masks = radial_band_masks(16, 16)
    members = torch.randn(1, 2, 16, 16)
    with pytest.raises(ValueError):
        spatial_band_spread(members, masks)
    with pytest.raises(ValueError):
        power_band_spread(members, masks)


def test_default_edges_are_frozen():
    # the calibration verdicts are stated per band; silently renumbering the
    # bands would detach every recorded conclusion from its evidence
    assert DEFAULT_BAND_EDGES == (0.0, 0.0625, 0.125, 0.25, 0.5, 1.0)
