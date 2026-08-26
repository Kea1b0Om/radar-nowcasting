"""Tests for the ensemble-based probabilistic scores.

The load-bearing test is `test_bimodal_and_unimodal_differ_only_for_empirical`:
it is the whole reason this module exists.  Two ensembles with identical
per-pixel mean and standard deviation - one split into two separated modes, one
spread out unimodally - must receive the same legacy Gaussian-fit CRPS and
different empirical CRPS.  If that ever stops holding, the metric has lost the
property that lets it see multi-modality.
"""

import os
import sys

import numpy as np
import pytest

sys.path.append(os.getcwd())

from common.metrics.crft_evaluation import Evaluation as CRFTEvaluation
from common.metrics.ensemble_probabilistic import (
    EnsembleProbabilisticAccumulator,
    contingency_counts,
    crps_empirical_fair,
    crps_gaussian_fit,
    scores_from_counts,
)


def brute_force_crps(members, truth, fair):
    """Direct O(M^2) definition, used to validate the order-statistic shortcut."""
    member_count = members.shape[0]
    skill = np.mean(np.abs(members - truth))
    pairwise = np.sum(np.abs(members[:, None] - members[None, :]))
    if fair:
        return skill - pairwise / (2 * member_count * (member_count - 1))
    return skill - pairwise / (2 * member_count**2)


def test_single_member_empirical_crps_is_exactly_mae():
    rng = np.random.default_rng(0)
    truth = rng.normal(size=(3, 4, 5, 5))
    members = rng.normal(size=(3, 1, 4, 5, 5))

    result = crps_empirical_fair(truth, members)

    np.testing.assert_allclose(
        result["crps_empirical"], np.abs(members[:, 0] - truth), rtol=0, atol=0
    )


def test_single_member_fair_crps_is_undefined():
    truth = np.zeros((2, 3, 4, 4))
    members = np.ones((2, 1, 3, 4, 4))

    result = crps_empirical_fair(truth, members)

    assert np.all(np.isnan(result["crps_fair"]))
    assert np.all(np.isnan(result["spread_fair"]))


def test_order_statistic_shortcut_matches_brute_force():
    rng = np.random.default_rng(7)
    truth = rng.normal(size=(2, 3, 4, 4))
    members = rng.normal(size=(2, 8, 3, 4, 4))

    result = crps_empirical_fair(truth, members)

    for event in range(truth.shape[0]):
        for lead in range(truth.shape[1]):
            for row in range(truth.shape[2]):
                for column in range(truth.shape[3]):
                    pixel_members = members[event, :, lead, row, column]
                    pixel_truth = truth[event, lead, row, column]
                    assert result["crps_empirical"][event, lead, row, column] == pytest.approx(
                        brute_force_crps(pixel_members, pixel_truth, fair=False)
                    )
                    assert result["crps_fair"][event, lead, row, column] == pytest.approx(
                        brute_force_crps(pixel_members, pixel_truth, fair=True)
                    )


def test_fair_crps_is_below_empirical_for_dispersed_ensembles():
    rng = np.random.default_rng(11)
    truth = rng.normal(size=(4, 2, 6, 6))
    members = rng.normal(size=(4, 8, 2, 6, 6))

    result = crps_empirical_fair(truth, members)

    # fair subtracts a larger spread term, so it is the stricter score.
    assert np.all(result["crps_fair"] <= result["crps_empirical"] + 1e-12)
    assert np.mean(result["crps_fair"]) < np.mean(result["crps_empirical"])


def test_bimodal_and_unimodal_differ_only_for_empirical():
    """Same (mean, std), different shape: Gaussian-fit is blind, empirical is not."""
    bimodal_values = np.array([-1.0, -1.0, -1.0, -1.0, 1.0, 1.0, 1.0, 1.0])
    spread_out = np.linspace(-1.0, 1.0, 8)
    # rescale the unimodal ensemble to the same unbiased std as the bimodal one
    spread_out = spread_out * (
        np.std(bimodal_values, ddof=1) / np.std(spread_out, ddof=1)
    )

    assert np.mean(bimodal_values) == pytest.approx(np.mean(spread_out))
    assert np.std(bimodal_values, ddof=1) == pytest.approx(np.std(spread_out, ddof=1))

    truth = np.zeros((1, 1, 1, 1))
    bimodal = bimodal_values.reshape(1, 8, 1, 1, 1)
    unimodal = spread_out.reshape(1, 8, 1, 1, 1)

    gaussian_bimodal = crps_gaussian_fit(truth, bimodal)
    gaussian_unimodal = crps_gaussian_fit(truth, unimodal)
    empirical_bimodal = crps_empirical_fair(truth, bimodal)["crps_empirical"]
    empirical_unimodal = crps_empirical_fair(truth, unimodal)["crps_empirical"]

    # the legacy metric cannot tell them apart ...
    np.testing.assert_allclose(gaussian_bimodal, gaussian_unimodal, rtol=1e-12)
    # ... the empirical one can.
    assert not np.isclose(empirical_bimodal, empirical_unimodal, rtol=1e-6)


def test_streaming_accumulator_matches_single_pass():
    rng = np.random.default_rng(3)
    truth = rng.uniform(0, 60, size=(12, 4, 8, 8))
    members = rng.uniform(0, 60, size=(12, 8, 4, 8, 8))
    thresholds = [20.0, 30.0, 35.0, 40.0]

    one_shot = EnsembleProbabilisticAccumulator(4, thresholds)
    one_shot.update(truth, members)

    chunked = EnsembleProbabilisticAccumulator(4, thresholds)
    for start in range(0, 12, 5):
        chunked.update(truth[start : start + 5], members[start : start + 5])

    for name, values in one_shot.compute()["per_lead"].items():
        np.testing.assert_allclose(
            values, chunked.compute()["per_lead"][name], rtol=1e-10, atol=1e-12
        )


def test_brier_decomposition_is_internally_consistent():
    rng = np.random.default_rng(5)
    truth = rng.uniform(0, 60, size=(6, 2, 8, 8))
    members = rng.uniform(0, 60, size=(6, 8, 2, 8, 8))

    accumulator = EnsembleProbabilisticAccumulator(2, [30.0])
    accumulator.update(truth, members)
    per_lead = accumulator.compute()["per_lead"]

    balanced = per_lead["brier_balanced_diagnostic@30"]
    event = per_lead["brier_observed_event_diagnostic@30"]
    nonevent = per_lead["brier_observed_nonevent_diagnostic@30"]
    np.testing.assert_allclose(balanced, 0.5 * (event + nonevent), rtol=1e-12)

    # the proper score is the event-frequency-weighted mix of the two conditionals
    event_fraction = accumulator.event_count[30.0] / accumulator.pixel_count
    reconstructed = event_fraction * event + (1 - event_fraction) * nonevent
    np.testing.assert_allclose(
        per_lead["brier_all_proper@30"], reconstructed, rtol=1e-10
    )


def test_brier_is_zero_for_a_perfect_deterministic_forecast():
    truth = np.array([[[[10.0, 50.0]]]])  # (1, 1, 1, 2)
    members = np.repeat(truth[:, None], 8, axis=1)  # every member equals truth

    accumulator = EnsembleProbabilisticAccumulator(1, [30.0])
    accumulator.update(truth, members)
    per_lead = accumulator.compute()["per_lead"]

    assert per_lead["brier_all_proper@30"][0] == pytest.approx(0.0)
    assert per_lead["crps_empirical"][0] == pytest.approx(0.0)
    assert per_lead["crps_fair"][0] == pytest.approx(0.0)


def test_spread_skill_ratio_is_one_for_a_calibrated_ensemble():
    """A calibrated ensemble has spread matching the error of its own mean."""
    rng = np.random.default_rng(17)
    member_count = 8
    shape = (400, 1, 16, 16)
    latent_truth = rng.normal(size=shape)
    # truth and members are exchangeable draws around a common latent state,
    # which is exactly the calibrated case.
    truth = latent_truth + rng.normal(size=shape)
    members = latent_truth[:, None] + rng.normal(
        size=(shape[0], member_count, *shape[1:])
    )

    accumulator = EnsembleProbabilisticAccumulator(1, [0.0])
    accumulator.update(truth, members)
    ratio = accumulator.compute()["per_lead"]["spread_skill_ratio"][0]

    assert ratio == pytest.approx(1.0, abs=0.05)


def test_underdispersed_ensemble_has_ratio_below_one():
    rng = np.random.default_rng(19)
    shape = (400, 1, 16, 16)
    latent_truth = rng.normal(size=shape)
    truth = latent_truth + rng.normal(size=shape)
    members = latent_truth[:, None] + 0.2 * rng.normal(size=(shape[0], 8, *shape[1:]))

    accumulator = EnsembleProbabilisticAccumulator(1, [0.0])
    accumulator.update(truth, members)

    assert accumulator.compute()["per_lead"]["spread_skill_ratio"][0] < 0.5


def test_contingency_scores_match_the_crft_evaluator():
    """Our offline CSI must equal the evaluator that produced the published numbers.

    `crft_evaluation.Evaluation` is the vendored code behind the CIKM tables we
    compare against.  If this drifts, offline scores stop being comparable to
    the legacy ones and the whole point of the controlled protocol is lost.
    """
    rng = np.random.default_rng(23)
    thresholds = [20.0, 30.0, 35.0, 40.0]
    pixel_scale = 90.0
    output_length, events = 4, 6

    truth = rng.uniform(0, 70, size=(events, output_length, 12, 12))
    prediction = np.clip(truth + rng.normal(scale=12, size=truth.shape), 0, 90)

    evaluator = CRFTEvaluation(
        seq_len=output_length, value_scale=pixel_scale, thresholds=thresholds
    )
    evaluator.update(
        np.ascontiguousarray(truth.transpose(1, 0, 2, 3) / pixel_scale),
        np.ascontiguousarray(prediction.transpose(1, 0, 2, 3) / pixel_scale),
    )
    _, _, reference_csi, reference_hss, *_ = evaluator.calculate_stat()

    counts = contingency_counts(
        truth, prediction, thresholds, comparison=">=", axis=(2, 3)
    )
    for index, threshold in enumerate(thresholds):
        summed = {
            key: np.sum(value, axis=0) for key, value in counts[threshold].items()
        }
        scores = scores_from_counts(
            summed["hits"],
            summed["false_alarms"],
            summed["misses"],
            summed["correct_negatives"],
        )
        np.testing.assert_allclose(
            scores["csi"], reference_csi[:, index], rtol=1e-10, atol=1e-12
        )
        np.testing.assert_allclose(
            scores["hss"], reference_hss[:, index], rtol=1e-10, atol=1e-12
        )


def test_comparison_operator_changes_counts_at_exact_threshold():
    """'>=' and '>' are different rulers; the module must not silently pick one."""
    truth = np.full((1, 1, 2, 2), 30.0)
    prediction = np.full((1, 1, 2, 2), 30.0)

    inclusive = contingency_counts(truth, prediction, [30.0], comparison=">=")
    exclusive = contingency_counts(truth, prediction, [30.0], comparison=">")

    assert inclusive[30.0]["hits"] == 4
    assert exclusive[30.0]["hits"] == 0
    assert exclusive[30.0]["correct_negatives"] == 4
