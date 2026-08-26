"""Radial frequency-band decomposition and band-wise ensemble statistics.

This module is the shared math for the band-spread gated rollout line
(K-mode band-wise trust gating).  It is written from scratch on purpose:
the DRIFT-Net reference implementation (arXiv 2509.24868, ``RadialBandGate``)
assigns bands by *row index* of the rFFT2 grid, which misclassifies the
negative vertical frequencies (rows > H/2 are low ``|f|`` but get the largest
"radius").  Everything here builds the radius from ``fftfreq().abs()`` /
``rfftfreq()`` so that a pure low-frequency mode lands in the lowest band
regardless of the sign of its frequency.  ``tests/test_band_spectral.py``
pins that property.

Two different "spreads" are exposed, and the difference is load-bearing:

* ``spatial_band_spread`` -- variance across members of the *band-passed
  spatial fields*, then pooled over space.  The band-pass keeps phase, so two
  members that are identical up to a spatial shift have nonzero spread.
  Displacement error is the dominant long-lead error mode, so this is the
  definition expected to correlate with actual error.
* ``power_band_spread`` -- variance across members of the per-band spectral
  *amplitude*.  Amplitude is translation invariant: members that are pure
  shifts of one another have spread exactly zero.  This is the naive
  definition; it is kept so the calibration can measure both and demonstrate
  which one carries the signal, rather than assuming it.

Conventions (matching ``common/metrics/ensemble_probabilistic``):

* members are ``(M, T, H, W)``, truth is ``(T, H, W)``; statistics are
  returned per ``(T, J)`` with ``J`` the number of radial bands,
* all reductions are performed in float64,
* inputs are torch tensors (CPU or CUDA); outputs are torch float64 tensors
  on the same device.
"""

from typing import Sequence, Tuple

import torch

__all__ = [
    "DEFAULT_BAND_EDGES",
    "radial_band_masks",
    "bandpass_decompose",
    "band_energy",
    "spatial_band_spread",
    "power_band_spread",
    "ensemble_mean_band_rmse",
    "member_mean_band_rmse",
]

# Dyadic-ish edges in units of the normalized radial frequency r/r_max with
# r = sqrt(fy^2 + fx^2), fy from fftfreq, fx from rfftfreq (cycles/pixel).
# r_max is the CORNER of the half-spectrum (~0.700 c/px at N=101, ~0.707 at
# N=128), NOT the Nyquist frequency 0.5 -- so a physical-scale reading must
# use wavelength = 1 / (edge * r_max).  On a 101 px crop at ~1 km/px the
# edges 0.0625/0.125/0.25/0.5 sit at wavelengths ~22.9/11.4/5.7/2.9 km:
# bands are roughly >23 km / 11.4-23 / 5.7-11.4 / 2.9-5.7 / <2.9 km (nearly
# identical on the 128 px grid).  The top two bands are below ~6 px
# wavelength, i.e. near radar effective resolution.  (An earlier comment
# quoted 64/32/16/8 km; that misread the normalization by ~2.8x --
# adversarial review 2026-08-10.)
DEFAULT_BAND_EDGES: Tuple[float, ...] = (0.0, 0.0625, 0.125, 0.25, 0.5, 1.0)


def _validate_edges(band_edges: Sequence[float]) -> None:
    if len(band_edges) < 2:
        raise ValueError("band_edges needs at least two entries.")
    edges = list(band_edges)
    if edges[0] != 0.0:
        raise ValueError(f"band_edges must start at 0.0, got {edges[0]}.")
    if edges[-1] != 1.0:
        raise ValueError(f"band_edges must end at 1.0, got {edges[-1]}.")
    for lo, hi in zip(edges[:-1], edges[1:]):
        if not hi > lo:
            raise ValueError(f"band_edges must be strictly increasing, got {edges}.")


def radial_band_masks(
    height: int,
    width: int,
    band_edges: Sequence[float] = DEFAULT_BAND_EDGES,
    device: torch.device = None,
) -> torch.Tensor:
    """Boolean masks ``(J, H, W//2+1)`` partitioning the rFFT2 grid by radius.

    The radius uses true frequency magnitudes -- ``fftfreq(H).abs()`` for the
    full (signed) vertical axis and ``rfftfreq(W)`` for the half horizontal
    axis -- normalized by the largest radius on the grid, so ``r`` is in
    ``[0, 1]`` and the masks are an exact partition: every frequency belongs
    to exactly one band.  Band ``j`` is ``edges[j] <= r < edges[j+1]``; the
    last band additionally includes ``r == 1``.
    """
    _validate_edges(band_edges)
    fy = torch.fft.fftfreq(height, device=device).abs()
    fx = torch.fft.rfftfreq(width, device=device)
    radius = torch.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
    radius = radius / radius.max()

    masks = []
    edges = list(band_edges)
    for j, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
        if j == len(edges) - 2:
            mask = (radius >= lo) & (radius <= hi)
        else:
            mask = (radius >= lo) & (radius < hi)
        masks.append(mask)
    stacked = torch.stack(masks, dim=0)

    coverage = stacked.sum(dim=0)
    if not bool((coverage == 1).all()):
        raise AssertionError(
            "band masks must partition the rFFT2 grid exactly once per bin"
        )
    return stacked


def bandpass_decompose(x: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
    """Split ``x (..., H, W)`` into per-band fields ``(..., J, H, W)``.

    The decomposition is linear and exact: summing over the band dimension
    reconstructs ``x`` up to float error (the masks partition the spectrum).
    Phase is preserved inside every band -- this is what makes the spatial
    spread displacement-sensitive.
    """
    height, width = x.shape[-2], x.shape[-1]
    # contiguous(): MKL's FFT (older torch CPU backend) rejects broadcast /
    # sliced inputs with "Inconsistent configuration parameters"; crops and
    # expanded test fields are exactly such tensors.
    spectrum = torch.fft.rfft2(x.contiguous(), norm="ortho")
    # (..., 1, Hf, Wf) * (J, Hf, Wf) -> (..., J, Hf, Wf)
    banded = spectrum.unsqueeze(-3) * masks.to(spectrum.device)
    return torch.fft.irfft2(banded, s=(height, width), norm="ortho")


def _rfft2_energy_weights(
    height: int, width: int, device: torch.device = None
) -> torch.Tensor:
    """Multiplicity of each rFFT2 bin in the full FFT2 spectrum.

    ``rfft2`` stores only the non-negative horizontal frequencies; every
    column except ``fx == 0`` (and, for even W, the Nyquist column) represents
    two conjugate bins of the full spectrum.  Without these weights, band
    energies would under-count the duplicated columns and Parseval would fail.
    """
    weights = torch.full((width // 2 + 1,), 2.0, device=device)
    weights[0] = 1.0
    if width % 2 == 0:
        weights[-1] = 1.0
    return weights.expand(height, -1)


def band_energy(x: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
    """Per-band spectral energy of ``x (..., H, W)`` -> ``(..., J)``.

    With ``norm="ortho"`` and the conjugate-multiplicity weights, the band
    energies sum to ``sum(x**2)`` exactly (Parseval); the test suite pins
    this identity.
    """
    height, width = x.shape[-2], x.shape[-1]
    spectrum = torch.fft.rfft2(x.contiguous(), norm="ortho")
    power = (spectrum.real.double() ** 2 + spectrum.imag.double() ** 2)
    power = power * _rfft2_energy_weights(height, width, device=x.device)
    # (..., 1, Hf, Wf) x (J, Hf, Wf) summed over the grid -> (..., J)
    flat_masks = masks.to(power.device).double()
    return torch.einsum("...hw,jhw->...j", power, flat_masks)


def _check_members(members: torch.Tensor) -> None:
    if members.ndim != 4:
        raise ValueError(f"members must be (M, T, H, W), got {tuple(members.shape)}")
    if members.shape[0] < 2:
        raise ValueError(
            "band spread needs at least two members "
            f"(got M={members.shape[0]}); with one member the estimator is "
            "undefined, not zero"
        )


def spatial_band_spread(
    members: torch.Tensor, masks: torch.Tensor
) -> torch.Tensor:
    """Phase-sensitive band spread of ``members (M, T, H, W)`` -> ``(T, J)``.

    Per band: unbiased (ddof=1) variance across members at every pixel of the
    band-passed fields, averaged over space, square-rooted.  Members that are
    spatial shifts of one another produce nonzero spread here (and zero spread
    under ``power_band_spread``) -- ``tests/test_band_spectral.py`` pins the
    discrimination.
    """
    _check_members(members)
    banded = bandpass_decompose(members.double(), masks)  # (M, T, J, H, W)
    variance = banded.var(dim=0, unbiased=True)  # (T, J, H, W)
    return variance.mean(dim=(-2, -1)).sqrt()


def power_band_spread(
    members: torch.Tensor, masks: torch.Tensor
) -> torch.Tensor:
    """Translation-invariant band spread (per-band amplitude std) -> ``(T, J)``.

    Std (ddof=1) across members of the per-band spectral amplitude.  Kept for
    the calibration A/B: it is blind to displacement disagreement by
    construction, which is the predicted failure mode of the naive proposal.
    """
    _check_members(members)
    amplitude = band_energy(members.double(), masks).sqrt()  # (M, T, J)
    return amplitude.std(dim=0, unbiased=True)


def ensemble_mean_band_rmse(
    members: torch.Tensor, truth: torch.Tensor, masks: torch.Tensor
) -> torch.Tensor:
    """Band-wise RMSE of the ensemble mean vs truth -> ``(T, J)``.

    This is the "skill" half of the spread/skill pairing: for a reliable
    ensemble, the std of members around their mean matches the RMSE of that
    mean against truth (per band, up to the usual M-dependent factors).
    """
    _check_members(members)
    if truth.shape != members.shape[1:]:
        raise ValueError(
            f"truth {tuple(truth.shape)} must match members[1:] "
            f"{tuple(members.shape[1:])}"
        )
    mean_bands = bandpass_decompose(members.double().mean(dim=0), masks)
    truth_bands = bandpass_decompose(truth.double(), masks)
    return (mean_bands - truth_bands).pow(2).mean(dim=(-2, -1)).sqrt()


def member_mean_band_rmse(
    members: torch.Tensor, truth: torch.Tensor, masks: torch.Tensor
) -> torch.Tensor:
    """Mean over members of each member's band-wise RMSE vs truth -> ``(T, J)``.

    Secondary skill diagnostic: unlike the ensemble-mean RMSE it does not
    reward mean-blurring, so comparing the two localizes where averaging is
    doing the work.
    """
    _check_members(members)
    if truth.shape != members.shape[1:]:
        raise ValueError(
            f"truth {tuple(truth.shape)} must match members[1:] "
            f"{tuple(members.shape[1:])}"
        )
    member_bands = bandpass_decompose(members.double(), masks)
    truth_bands = bandpass_decompose(truth.double(), masks)
    per_member = (member_bands - truth_bands).pow(2).mean(dim=(-2, -1)).sqrt()
    return per_member.mean(dim=0)
