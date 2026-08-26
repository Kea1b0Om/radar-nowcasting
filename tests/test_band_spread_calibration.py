"""Tests for the band-spread calibration gate.

The suite constructs synthetic ensembles where the ground truth of the
verdict is known by construction:

* noise amplitude varying across events -> spread and error co-vary -> green;
* constant spread regardless of error -> degenerate dynamic range -> red
  (the "static band weight" collision rule);
* displacement-only disagreement -> only the spatial definition passes,
  which is the pre-registered prediction the calibration exists to check;
* shuffled input order -> byte-identical report (the bootstrap-vs-DataLoader
  P0 from the AE-gate line, pinned here from day one).
"""

import os
import sys

import numpy as np
import pytest
import torch

sys.path.append(os.getcwd())

from common.evaluation.band_spread_calibration import (
    GREEN,
    RED,
    UNDETERMINED,
    CalibrationProtocol,
    iter_records_from_arrays,
    run_band_calibration,
    spearman,
)
from common.metrics.band_spectral import bandpass_decompose, radial_band_masks

HEIGHT = WIDTH = 32
FRAMES = 4
MEMBERS = 4
PROTOCOL = CalibrationProtocol(min_events=30, bootstrap_iterations=200)


def _smooth_field(rng, height=HEIGHT, width=WIDTH):
    noise = torch.as_tensor(rng.standard_normal((height, width)))
    spectrum = torch.fft.rfft2(noise)
    fy = torch.fft.fftfreq(height).abs()
    fx = torch.fft.rfftfreq(width)
    radius = torch.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
    spectrum = spectrum / (1.0 + (radius / 0.08) ** 2)
    return torch.fft.irfft2(spectrum, s=(height, width))


def make_noise_scaled_dataset(n_events=40, seed=0):
    """Events whose per-event noise amplitude drives both spread and error."""
    rng = np.random.default_rng(seed)
    predictions = np.zeros((n_events, MEMBERS, FRAMES, HEIGHT, WIDTH), np.float32)
    truth = np.zeros((n_events, FRAMES, HEIGHT, WIDTH), np.float32)
    for e in range(n_events):
        sigma = 0.2 + 2.0 * rng.random()
        base = _smooth_field(rng).numpy()
        for t in range(FRAMES):
            truth[e, t] = base
            for m in range(MEMBERS):
                predictions[e, m, t] = base + sigma * rng.standard_normal(
                    (HEIGHT, WIDTH)
                )
    return predictions, truth, list(range(n_events))


def test_spearman_perfect_and_ties():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert spearman(x, 2 * x + 1) == pytest.approx(1.0)
    assert spearman(x, -x) == pytest.approx(-1.0)
    tied = np.array([1.0, 1.0, 2.0, 3.0, 3.0])
    rho = spearman(tied, tied)
    assert rho == pytest.approx(1.0)
    assert np.isnan(spearman(np.ones(5), x))


def test_correlated_noise_amplitude_goes_green():
    predictions, truth, indices = make_noise_scaled_dataset()
    records = iter_records_from_arrays(predictions, truth, indices, PROTOCOL)
    result = run_band_calibration(records, PROTOCOL)
    assert result["verdict"] == GREEN
    passing = result["definition_comparison"]["spatial_bands_passing"]
    assert len(passing) >= PROTOCOL.green_min_bands
    for band in result["bands"]:
        assert band["ci_spatial"][0] <= band["rho_spatial"] <= band["ci_spatial"][1]


def test_constant_spread_goes_red_as_static_band_weight():
    """Same noise amplitude everywhere: spread has no dynamic range.

    Even though error varies across events (different truth offsets), a gate
    driven by this spread would be a constant band weight -- the pre-
    registered red condition.
    """
    rng = np.random.default_rng(1)
    n_events = 40
    predictions = np.zeros((n_events, MEMBERS, FRAMES, HEIGHT, WIDTH), np.float32)
    truth = np.zeros((n_events, FRAMES, HEIGHT, WIDTH), np.float32)
    for e in range(n_events):
        base = _smooth_field(rng).numpy()
        offset = 3.0 * rng.random()  # error varies across events...
        for t in range(FRAMES):
            truth[e, t] = base + offset
            for m in range(MEMBERS):
                # ...but member disagreement does not
                predictions[e, m, t] = base + 0.5 * rng.standard_normal(
                    (HEIGHT, WIDTH)
                )
    records = iter_records_from_arrays(predictions, truth, list(range(n_events)), PROTOCOL)
    result = run_band_calibration(records, PROTOCOL)
    assert result["verdict"] == RED
    assert any("static band weight" in r for r in result["reasons"])


def test_displacement_disagreement_passes_only_spatially():
    """Members are shifts of a common field; error scales with displacement.

    Power spread sees almost nothing (amplitudes invariant under circular
    shift, up to a tiny jitter added so ranks are defined); spatial spread
    tracks the displacement magnitude that also drives the error.  This is
    the scenario the naive proposal would have failed on silently.
    """
    rng = np.random.default_rng(2)
    n_events = 40
    predictions = np.zeros((n_events, MEMBERS, FRAMES, HEIGHT, WIDTH), np.float32)
    truth = np.zeros((n_events, FRAMES, HEIGHT, WIDTH), np.float32)
    for e in range(n_events):
        shift_scale = 1 + int(6 * rng.random())  # px, varies across events
        base = _smooth_field(rng).numpy()
        for t in range(FRAMES):
            truth[e, t] = base
            for m in range(MEMBERS):
                dy = int(rng.integers(-shift_scale, shift_scale + 1))
                dx = int(rng.integers(-shift_scale, shift_scale + 1))
                shifted = np.roll(np.roll(base, dy, axis=0), dx, axis=1)
                jitter = 1e-4 * rng.standard_normal((HEIGHT, WIDTH))
                predictions[e, m, t] = shifted + jitter
    records = iter_records_from_arrays(predictions, truth, list(range(n_events)), PROTOCOL)
    result = run_band_calibration(records, PROTOCOL)
    comparison = result["definition_comparison"]
    assert len(comparison["spatial_bands_passing"]) >= 2
    assert comparison["spatial_bands_passing"] != comparison["power_bands_passing"]
    assert result["verdict"] == GREEN


def test_insufficient_events_is_undetermined_not_red():
    predictions, truth, indices = make_noise_scaled_dataset(n_events=10)
    records = iter_records_from_arrays(predictions, truth, indices, PROTOCOL)
    result = run_band_calibration(records, PROTOCOL)
    assert result["verdict"] == UNDETERMINED
    assert any("insufficient events" in r for r in result["reasons"])


def test_report_is_invariant_to_input_order():
    predictions, truth, indices = make_noise_scaled_dataset(seed=5)
    records = iter_records_from_arrays(predictions, truth, indices, PROTOCOL)
    forward = run_band_calibration(list(records), PROTOCOL)
    backward = run_band_calibration(list(reversed(records)), PROTOCOL)
    assert forward == backward


def test_duplicate_event_index_raises():
    predictions, truth, _ = make_noise_scaled_dataset(n_events=31)
    indices = [0] + list(range(30))
    records = iter_records_from_arrays(predictions, truth, indices, PROTOCOL)
    with pytest.raises(ValueError):
        run_band_calibration(records, PROTOCOL)


def test_alpha_mapping_quantiles_are_ordered():
    predictions, truth, indices = make_noise_scaled_dataset(seed=6)
    records = iter_records_from_arrays(predictions, truth, indices, PROTOCOL)
    result = run_band_calibration(records, PROTOCOL)
    exported = 0
    for band in result["bands"]:
        mapping = band["alpha_mapping"]
        if band["degenerate"]:
            assert mapping is None  # excluded bands must not export quantiles
        else:
            exported += 1
            assert mapping["q_hi"] > mapping["q_lo"] >= 0.0
    assert exported >= 2


def test_mapping_lead_range_changes_quantiles():
    protocol = CalibrationProtocol(
        min_events=30, bootstrap_iterations=100, mapping_lead_range=(0, 1)
    )
    rng = np.random.default_rng(7)
    n_events = 32
    predictions = np.zeros((n_events, MEMBERS, FRAMES, HEIGHT, WIDTH), np.float32)
    truth = np.zeros((n_events, FRAMES, HEIGHT, WIDTH), np.float32)
    for e in range(n_events):
        sigma = 0.2 + 2.0 * rng.random()
        base = _smooth_field(rng).numpy()
        for t in range(FRAMES):
            grow = 1.0 + 3.0 * t  # spread grows strongly with lead
            truth[e, t] = base
            for m in range(MEMBERS):
                predictions[e, m, t] = base + sigma * grow * rng.standard_normal(
                    (HEIGHT, WIDTH)
                )
    records = iter_records_from_arrays(predictions, truth, list(range(n_events)), protocol)
    early = run_band_calibration(records, protocol)
    full = run_band_calibration(records, PROTOCOL)
    band_early = early["bands"][1]["alpha_mapping"]
    band_full = full["bands"][1]["alpha_mapping"]
    assert band_early["q_hi"] < band_full["q_hi"]


# ---- fixes from the adversarial review (2026-08-10) ----


def test_pooled_rejects_invalid_lead_range():
    predictions, truth, indices = make_noise_scaled_dataset(n_events=1)
    record = iter_records_from_arrays(predictions[:1], truth[:1], [0], PROTOCOL)[0]
    for bad in [(2, 2), (0, 100), (-1, 2), (3, 1)]:
        with pytest.raises(ValueError, match="mapping_lead_range"):
            record.pooled(bad)


def test_nan_inputs_veto_to_undetermined_not_green():
    predictions, truth, indices = make_noise_scaled_dataset(seed=8)
    predictions[3, 1, 2, 5, 5] = np.nan  # one corrupt member pixel
    records = iter_records_from_arrays(predictions, truth, indices, PROTOCOL)
    result = run_band_calibration(records, PROTOCOL)
    assert result["verdict"] == UNDETERMINED
    assert any("non-finite input" in r for r in result["reasons"])


def test_spearman_rejects_nonfinite_inputs():
    x = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert np.isnan(spearman(x, y))


def test_exact_spread_collapse_reaches_red_not_undetermined():
    """All members identical: spread is exactly zero everywhere.

    The correlation estimator is NaN, but the pre-registered verdict for
    total collapse is the static-band-weight RED, not 'measurement
    incomplete' -- exact degeneracy must not be softer than approximate
    degeneracy.
    """
    rng = np.random.default_rng(9)
    n_events = 32
    predictions = np.zeros((n_events, MEMBERS, FRAMES, HEIGHT, WIDTH), np.float32)
    truth = np.zeros((n_events, FRAMES, HEIGHT, WIDTH), np.float32)
    for e in range(n_events):
        base = _smooth_field(rng).numpy()
        for t in range(FRAMES):
            truth[e, t] = base + rng.random()
            for m in range(MEMBERS):
                predictions[e, m, t] = base  # mode collapse
    records = iter_records_from_arrays(predictions, truth, list(range(n_events)), PROTOCOL)
    result = run_band_calibration(records, PROTOCOL)
    assert result["verdict"] == RED
    assert any("static band weight" in r for r in result["reasons"])


def test_exact_shift_power_breakdown_does_not_block_green():
    """Members are exact circular shifts: power spread is exactly zero.

    That is the *predicted confirmation* of the displacement-sensitivity
    thesis, so a NaN power correlation must not veto the verdict; the
    spatial definition carries the signal and the calibration goes green.
    """
    rng = np.random.default_rng(10)
    n_events = 40
    predictions = np.zeros((n_events, MEMBERS, FRAMES, HEIGHT, WIDTH), np.float32)
    truth = np.zeros((n_events, FRAMES, HEIGHT, WIDTH), np.float32)
    for e in range(n_events):
        shift_scale = 1 + int(6 * rng.random())
        base = _smooth_field(rng).numpy()
        for t in range(FRAMES):
            truth[e, t] = base
            for m in range(MEMBERS):
                dy = int(rng.integers(-shift_scale, shift_scale + 1))
                dx = int(rng.integers(-shift_scale, shift_scale + 1))
                predictions[e, m, t] = np.roll(np.roll(base, dy, axis=0), dx, axis=1)
    records = iter_records_from_arrays(predictions, truth, list(range(n_events)), PROTOCOL)
    result = run_band_calibration(records, PROTOCOL)
    assert result["verdict"] == GREEN
    assert result["definition_comparison"]["power_bands_passing"] == []
    for band in result["bands"]:
        if band["gated"]:
            assert band["degenerate_power"]


def test_noise_floor_band_is_excluded_by_ssr_floor():
    """A band whose spread is float-noise passes IQR/median but not the
    spread/skill floor; its mapping must not be exported."""
    predictions, truth, indices = make_noise_scaled_dataset(seed=11)
    protocol = PROTOCOL
    masks = radial_band_masks(HEIGHT, WIDTH, protocol.band_edges)
    # crush the top band of every member to ~float noise while truth keeps it
    top = len(protocol.band_edges) - 2
    for e in range(predictions.shape[0]):
        for m in range(MEMBERS):
            fields = torch.as_tensor(predictions[e, m])
            bands = bandpass_decompose(fields.double(), masks)
            bands[:, top] *= 1e-12
            predictions[e, m] = bands.sum(dim=1).float().numpy()
    records = iter_records_from_arrays(predictions, truth, indices, protocol)
    result = run_band_calibration(records, protocol)
    top_band = result["bands"][top]
    assert top_band["degenerate"]
    assert top_band["alpha_mapping"] is None


def test_view_fingerprint_controls_deployable_flag():
    predictions, truth, indices = make_noise_scaled_dataset(seed=12)
    records = iter_records_from_arrays(predictions, truth, indices, PROTOCOL)
    without = run_band_calibration(records, PROTOCOL)
    assert without["deployable"] is False
    assert any("NOT deployable" in r for r in without["reasons"])
    view = {"height": HEIGHT, "width": WIDTH, "view_id": "test"}
    with_view = run_band_calibration(records, PROTOCOL, view=view)
    assert with_view["deployable"] is True
    assert with_view["view"] == view


def test_from_report_end_to_end_with_calibration_output():
    from common.models.flowcast.gated_rollout import SpreadToAlpha

    predictions, truth, indices = make_noise_scaled_dataset(seed=13)
    records = iter_records_from_arrays(predictions, truth, indices, PROTOCOL)
    view = {"height": HEIGHT, "width": WIDTH, "view_id": "test"}
    report = run_band_calibration(records, PROTOCOL, view=view)
    mapping = SpreadToAlpha.from_report(report)
    assert mapping.view_height == HEIGHT
    assert mapping.q_lo.shape[0] == PROTOCOL.num_bands
    # bands excluded at calibration are inactive pass-through
    for j, band in enumerate(report["bands"]):
        assert bool(mapping.active[j]) == (band["alpha_mapping"] is not None)

    undeployable = run_band_calibration(records, PROTOCOL)
    with pytest.raises(ValueError, match="not.*deployable|deployable"):
        SpreadToAlpha.from_report(undeployable)


def test_ci_finite_fraction_is_reported():
    predictions, truth, indices = make_noise_scaled_dataset(seed=14)
    records = iter_records_from_arrays(predictions, truth, indices, PROTOCOL)
    result = run_band_calibration(records, PROTOCOL)
    for band in result["bands"]:
        assert 0.0 <= band["ci_spatial_finite_fraction"] <= 1.0
        assert 0.0 <= band["ci_power_finite_fraction"] <= 1.0
