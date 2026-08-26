"""Ensemble-based probabilistic scores computed from the raw member array.

The scores here read the *empirical* member distribution.  This is the
difference that matters for us: `common/metrics/metrics_streaming_probabilistic.crps`
first collapses the members to a per-pixel `(mean, std)` pair and then evaluates a
Gaussian closed form, so an ensemble that splits into two separated modes and an
ensemble smeared into one wide unimodal blob receive the same score.  Any claim
about multi-modality (K-mode) is invisible to that metric by construction.

Conventions, all inherited from the existing evaluation path so that numbers stay
on the same ruler as the legacy tables:

* arrays are on the dBZ metric scale (CIKM: 0-90 after `raw_to_eval_scale`),
* truth is `(N, T, H, W)`, members are `(N, M, T, H, W)`,
* threshold comparison defaults to `>=`, matching
  `common/metrics/crft_evaluation.get_hit_miss_counts`, which produced the CIKM
  numbers we compare against.  `metrics_streaming_probabilistic` uses `>`
  instead, so the operator is explicit everywhere in this module rather than
  hard-coded.

All accumulators are streaming: `update()` takes a chunk and only keeps scalar
sums, so a 4000-event ensemble never has to be held in memory at once.
"""

from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

# Sentinel for scores that are mathematically undefined rather than merely
# missing.  fair CRPS needs at least two members; reporting 0.0 or falling back
# to the empirical value would silently turn "cannot be measured" into a number
# that looks comparable.
UNDEFINED = float("nan")


def _as_float64(array: np.ndarray) -> np.ndarray:
    """Promote to float64 for accumulation.

    The inference path stores predictions as float16 (see `test_flowcast.py`,
    where decoded samples are cast before any metric is computed).  Summing tens
    of billions of float16 pixel terms in low precision loses digits we later
    want to compare at the 1e-4 level, so every reduction here runs in float64.
    """
    return np.asarray(array, dtype=np.float64)


def _pairwise_absolute_sum(sorted_members: np.ndarray, member_axis: int) -> np.ndarray:
    """Return ``sum_{m,n} |x_m - x_n| / 2`` for members sorted along `member_axis`.

    Computing the double sum directly costs O(M^2) arrays; for the ensemble sizes
    we run (M=8) that is only 64 temporaries per pixel, but it is both slower and
    much heavier on memory than the order-statistic identity

        sum_{m<n} (x_(n) - x_(m)) = sum_i (2i - M + 1) * x_(i)

    with `x_(i)` the ascending order statistics.  The returned value is that
    right-hand side, i.e. exactly half of the full double sum (self-pairs
    contribute zero, so it is also half of the m != n sum).
    """
    member_count = sorted_members.shape[member_axis]
    weight_shape = [1] * sorted_members.ndim
    weight_shape[member_axis] = member_count
    weights = (
        2 * np.arange(member_count, dtype=np.float64) - member_count + 1
    ).reshape(weight_shape)
    return np.sum(sorted_members * weights, axis=member_axis)


def crps_empirical_fair(
    y_true: np.ndarray,
    y_pred_members: np.ndarray,
    member_axis: int = 1,
) -> Dict[str, np.ndarray]:
    """Per-pixel empirical and fair CRPS from the member distribution.

    empirical:  1/M sum_m |x_m - y|  -  1/(2 M^2)   sum_{m,n} |x_m - x_n|
    fair:       1/M sum_m |x_m - y|  -  1/(2 M(M-1)) sum_{m!=n} |x_m - x_n|

    The empirical estimator is the plug-in CRPS of the finite ensemble; its
    spread term is biased low for small M, which rewards under-dispersed
    ensembles.  The fair estimator removes that bias and is the one to use when
    comparing models at fixed M.

    At M=1 the spread term vanishes and empirical CRPS is *exactly* the absolute
    error, so a "CRPS" reported from a single member is MAE under another name.
    fair CRPS is undefined there and returns NaN rather than a number.

    Returns a dict of arrays shaped like `y_true`, plus the bare skill and
    spread components so callers can inspect which side moved.
    """
    truth = _as_float64(y_true)
    members = _as_float64(y_pred_members)

    truth_expanded = np.expand_dims(truth, axis=member_axis)
    if members.shape[:member_axis] != truth_expanded.shape[:member_axis] or (
        members.shape[member_axis + 1 :] != truth_expanded.shape[member_axis + 1 :]
    ):
        raise ValueError(
            "member array and truth are not broadcast-compatible: "
            f"members {members.shape}, truth {truth.shape} (member_axis={member_axis})"
        )

    member_count = members.shape[member_axis]
    skill = np.mean(np.abs(members - truth_expanded), axis=member_axis)

    half_pairwise_sum = _pairwise_absolute_sum(
        np.sort(members, axis=member_axis), member_axis
    )
    # sum_{m,n} |x_m - x_n| = 2 * half_pairwise_sum, hence the factors below.
    spread_empirical = half_pairwise_sum / (member_count**2)
    if member_count > 1:
        spread_fair = half_pairwise_sum / (member_count * (member_count - 1))
        crps_fair = skill - spread_fair
    else:
        spread_fair = np.full_like(skill, UNDEFINED)
        crps_fair = np.full_like(skill, UNDEFINED)

    return {
        "crps_empirical": skill - spread_empirical,
        "crps_fair": crps_fair,
        "skill_term": skill,
        "spread_empirical": spread_empirical,
        "spread_fair": spread_fair,
    }


def crps_gaussian_fit(
    y_true: np.ndarray,
    y_pred_members: np.ndarray,
    member_axis: int = 1,
    eps: float = 1e-10,
) -> np.ndarray:
    """Legacy Gaussian-fit CRPS, reimplemented here for side-by-side reporting.

    Numerically equivalent to `metrics_streaming_probabilistic.crps` (same
    closed form, same eps, same unbiased std).  It exists in this module only so
    that a single pass over a saved ensemble can report both the legacy number
    and the empirical one, making the gap between them measurable instead of
    argued.  Do not use it as a headline probabilistic score.
    """
    from scipy.stats import norm  # local import: only the legacy path needs scipy

    truth = _as_float64(y_true)
    members = _as_float64(y_pred_members)

    member_count = members.shape[member_axis]
    mean = np.mean(members, axis=member_axis)
    if member_count > 1:
        std = np.std(members, axis=member_axis, ddof=1)
    else:
        std = np.zeros_like(mean)

    normed = (mean - truth) / (std + eps)
    return (std + eps) * (
        normed * (2 * norm.cdf(normed) - 1) + 2 * norm.pdf(normed) - 1 / np.sqrt(np.pi)
    )


def exceedance_probability(
    y_pred_members: np.ndarray,
    threshold: float,
    member_axis: int = 1,
    comparison: str = ">=",
) -> np.ndarray:
    """Fraction of members exceeding `threshold`."""
    members = np.asarray(y_pred_members)
    if comparison == ">=":
        exceeds = members >= threshold
    elif comparison == ">":
        exceeds = members > threshold
    else:
        raise ValueError(f"comparison must be '>=' or '>', got {comparison!r}")
    return np.mean(exceeds.astype(np.float64), axis=member_axis)


class EnsembleProbabilisticAccumulator:
    """Streaming empirical/fair CRPS, threshold Brier, and spread-skill.

    Every score is accumulated per lead time so the lead-time curve is real
    rather than a constant repeated T times (the failure mode of the existing
    `MetricsAccumulator` CRPS path, which passes the whole chunk to `crps()`
    without slicing `self.lead_time`).

    Brier scores are reported in five flavours:

    * `brier_all` - the proper score over every pixel.  This is the only one
      that is a proper scoring rule and the only one admissible as a headline
      number.
    * `brier_observed_event`, `brier_observed_nonevent`, `brier_balanced`,
      `brier_active_region` - diagnostics.  Conditioning on the observation (or
      on the forecast) breaks propriety: a model can improve a conditioned score
      by shifting probability around rather than by being better calibrated.
      They are here because at 35/40 dBZ the event pixels are a vanishing
      fraction of a CIKM frame, so the proper score alone cannot tell "better
      probabilities on storms" from "more confident zeros on the background".
      Report them together, never alone.
    """

    def __init__(
        self,
        output_length: int,
        thresholds: Sequence[float],
        comparison: str = ">=",
        compute_gaussian_fit: bool = False,
    ):
        if comparison not in (">=", ">"):
            raise ValueError(f"comparison must be '>=' or '>', got {comparison!r}")
        self.output_length = int(output_length)
        self.thresholds = [float(threshold) for threshold in thresholds]
        self.comparison = comparison
        self.compute_gaussian_fit = compute_gaussian_fit

        zeros = lambda: np.zeros(self.output_length, dtype=np.float64)  # noqa: E731

        self.pixel_count = zeros()
        self.crps_empirical_sum = zeros()
        self.crps_fair_sum = zeros()
        self.skill_term_sum = zeros()
        self.spread_empirical_sum = zeros()
        self.crps_gaussian_sum = zeros()

        # spread-skill: ensemble variance vs squared error of the ensemble mean
        self.ensemble_variance_sum = zeros()
        self.mean_squared_error_sum = zeros()

        self.brier_sum: Dict[float, np.ndarray] = {}
        self.brier_event_sum: Dict[float, np.ndarray] = {}
        self.brier_nonevent_sum: Dict[float, np.ndarray] = {}
        self.brier_active_sum: Dict[float, np.ndarray] = {}
        self.event_count: Dict[float, np.ndarray] = {}
        self.nonevent_count: Dict[float, np.ndarray] = {}
        self.active_count: Dict[float, np.ndarray] = {}
        for threshold in self.thresholds:
            self.brier_sum[threshold] = zeros()
            self.brier_event_sum[threshold] = zeros()
            self.brier_nonevent_sum[threshold] = zeros()
            self.brier_active_sum[threshold] = zeros()
            self.event_count[threshold] = zeros()
            self.nonevent_count[threshold] = zeros()
            self.active_count[threshold] = zeros()

        self.member_count: Optional[int] = None
        self.event_total = 0

    def update(self, y_true_chunk: np.ndarray, y_pred_chunk: np.ndarray) -> None:
        """Accumulate one chunk.

        Args:
            y_true_chunk: `(N, T, H, W)` truth on the metric scale.
            y_pred_chunk: `(N, M, T, H, W)` members on the metric scale.
        """
        truth = _as_float64(y_true_chunk)
        members = _as_float64(y_pred_chunk)

        if truth.ndim != 4 or members.ndim != 5:
            raise ValueError(
                "expected truth (N, T, H, W) and members (N, M, T, H, W), got "
                f"{truth.shape} and {members.shape}"
            )
        if members.shape[0] != truth.shape[0] or members.shape[2:] != truth.shape[1:]:
            raise ValueError(
                f"member array {members.shape} does not match truth {truth.shape}"
            )
        if truth.shape[1] != self.output_length:
            raise ValueError(
                f"chunk has {truth.shape[1]} lead times, accumulator expects "
                f"{self.output_length}"
            )

        chunk_members = members.shape[1]
        if self.member_count is None:
            self.member_count = chunk_members
        elif self.member_count != chunk_members:
            raise ValueError(
                "member count changed between chunks "
                f"({self.member_count} then {chunk_members}); all collapses must "
                "read the same ensemble"
            )
        self.event_total += truth.shape[0]

        crps_terms = crps_empirical_fair(truth, members, member_axis=1)
        ensemble_mean = np.mean(members, axis=1)
        if chunk_members > 1:
            ensemble_variance = np.var(members, axis=1, ddof=1)
        else:
            ensemble_variance = np.zeros_like(ensemble_mean)
        squared_error = (ensemble_mean - truth) ** 2

        # Reduce over everything except the lead-time axis (axis 1 of the truth).
        spatial_axes = (0, 2, 3)
        self.pixel_count += np.full(
            self.output_length,
            truth.shape[0] * truth.shape[2] * truth.shape[3],
            dtype=np.float64,
        )
        self.crps_empirical_sum += np.sum(crps_terms["crps_empirical"], axis=spatial_axes)
        self.skill_term_sum += np.sum(crps_terms["skill_term"], axis=spatial_axes)
        self.spread_empirical_sum += np.sum(
            crps_terms["spread_empirical"], axis=spatial_axes
        )
        if chunk_members > 1:
            self.crps_fair_sum += np.sum(crps_terms["crps_fair"], axis=spatial_axes)
        else:
            self.crps_fair_sum += UNDEFINED
        self.ensemble_variance_sum += np.sum(ensemble_variance, axis=spatial_axes)
        self.mean_squared_error_sum += np.sum(squared_error, axis=spatial_axes)

        if self.compute_gaussian_fit:
            self.crps_gaussian_sum += np.sum(
                crps_gaussian_fit(truth, members, member_axis=1), axis=spatial_axes
            )

        for threshold in self.thresholds:
            forecast_probability = exceedance_probability(
                members, threshold, member_axis=1, comparison=self.comparison
            )
            if self.comparison == ">=":
                observed = (truth >= threshold).astype(np.float64)
            else:
                observed = (truth > threshold).astype(np.float64)

            squared_probability_error = (forecast_probability - observed) ** 2
            self.brier_sum[threshold] += np.sum(
                squared_probability_error, axis=spatial_axes
            )

            event_mask = observed > 0
            nonevent_mask = ~event_mask
            # "active" = the observation fired, or at least one member fired.
            # Pixels where nobody expected anything and nothing happened carry no
            # information about storm-scale probability quality.
            active_mask = event_mask | (forecast_probability > 0)

            self.brier_event_sum[threshold] += np.sum(
                squared_probability_error * event_mask, axis=spatial_axes
            )
            self.brier_nonevent_sum[threshold] += np.sum(
                squared_probability_error * nonevent_mask, axis=spatial_axes
            )
            self.brier_active_sum[threshold] += np.sum(
                squared_probability_error * active_mask, axis=spatial_axes
            )
            self.event_count[threshold] += np.sum(event_mask, axis=spatial_axes)
            self.nonevent_count[threshold] += np.sum(nonevent_mask, axis=spatial_axes)
            self.active_count[threshold] += np.sum(active_mask, axis=spatial_axes)

    @staticmethod
    def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
        result = np.full_like(numerator, UNDEFINED, dtype=np.float64)
        nonzero = denominator > 0
        result[nonzero] = numerator[nonzero] / denominator[nonzero]
        return result

    def compute(self) -> Dict[str, object]:
        """Return per-lead arrays and lead-averaged scalars."""
        if self.member_count is None:
            raise RuntimeError("compute() called before any update()")

        per_lead: Dict[str, np.ndarray] = {
            "crps_empirical": self._safe_divide(self.crps_empirical_sum, self.pixel_count),
            "crps_fair": self._safe_divide(self.crps_fair_sum, self.pixel_count),
            "crps_skill_term": self._safe_divide(self.skill_term_sum, self.pixel_count),
            "crps_spread_term": self._safe_divide(
                self.spread_empirical_sum, self.pixel_count
            ),
            "ensemble_variance": self._safe_divide(
                self.ensemble_variance_sum, self.pixel_count
            ),
            "ensemble_mean_mse": self._safe_divide(
                self.mean_squared_error_sum, self.pixel_count
            ),
        }
        if self.compute_gaussian_fit:
            per_lead["crps_gaussian_fit_legacy"] = self._safe_divide(
                self.crps_gaussian_sum, self.pixel_count
            )

        # spread-skill ratio: a perfectly calibrated ensemble of size M satisfies
        # E[var] * (M+1)/M = E[(mean - truth)^2], so the corrected ratio is 1.
        spread = np.sqrt(per_lead["ensemble_variance"])
        skill = np.sqrt(per_lead["ensemble_mean_mse"])
        member_correction = np.sqrt((self.member_count + 1) / self.member_count)
        per_lead["spread_skill_ratio"] = self._safe_divide(
            spread * member_correction, skill
        )

        for threshold in self.thresholds:
            per_lead[f"brier_all_proper@{threshold:g}"] = self._safe_divide(
                self.brier_sum[threshold], self.pixel_count
            )
            per_lead[f"brier_observed_event_diagnostic@{threshold:g}"] = (
                self._safe_divide(self.brier_event_sum[threshold], self.event_count[threshold])
            )
            per_lead[f"brier_observed_nonevent_diagnostic@{threshold:g}"] = (
                self._safe_divide(
                    self.brier_nonevent_sum[threshold], self.nonevent_count[threshold]
                )
            )
            per_lead[f"brier_active_region_diagnostic@{threshold:g}"] = (
                self._safe_divide(
                    self.brier_active_sum[threshold], self.active_count[threshold]
                )
            )
            per_lead[f"brier_balanced_diagnostic@{threshold:g}"] = 0.5 * (
                per_lead[f"brier_observed_event_diagnostic@{threshold:g}"]
                + per_lead[f"brier_observed_nonevent_diagnostic@{threshold:g}"]
            )

        summary = {name: float(np.mean(values)) for name, values in per_lead.items()}
        return {
            "per_lead": per_lead,
            "summary": summary,
            "member_count": self.member_count,
            "event_count": self.event_total,
            "comparison": self.comparison,
            "thresholds": list(self.thresholds),
        }


def contingency_counts(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    thresholds: Iterable[float],
    comparison: str = ">=",
    axis: Optional[Sequence[int]] = None,
) -> Dict[float, Dict[str, np.ndarray]]:
    """Hits/false alarms/misses/correct negatives for a deterministic field.

    Kept in this module so that the offline evaluator can store raw counts per
    event.  A paired bootstrap must resample events, re-sum TP/FP/FN, and only
    then form CSI: averaging per-event CSI values is a different (and wrong)
    estimator of the population CSI that `crft_evaluation` reports.
    """
    if comparison == ">=":
        truth_mask_fn = lambda array, th: array >= th  # noqa: E731
    elif comparison == ">":
        truth_mask_fn = lambda array, th: array > th  # noqa: E731
    else:
        raise ValueError(f"comparison must be '>=' or '>', got {comparison!r}")

    counts: Dict[float, Dict[str, np.ndarray]] = {}
    for threshold in thresholds:
        predicted_event = truth_mask_fn(y_pred, threshold)
        observed_event = truth_mask_fn(y_true, threshold)
        counts[float(threshold)] = {
            "hits": np.sum(predicted_event & observed_event, axis=axis),
            "false_alarms": np.sum(predicted_event & ~observed_event, axis=axis),
            "misses": np.sum(~predicted_event & observed_event, axis=axis),
            "correct_negatives": np.sum(~predicted_event & ~observed_event, axis=axis),
        }
    return counts


def scores_from_counts(
    hits: np.ndarray,
    false_alarms: np.ndarray,
    misses: np.ndarray,
    correct_negatives: np.ndarray,
) -> Dict[str, np.ndarray]:
    """CSI/POD/FAR/HSS from summed counts, matching `crft_evaluation`."""
    a = np.asarray(hits, dtype=np.float64)
    b = np.asarray(false_alarms, dtype=np.float64)
    c = np.asarray(misses, dtype=np.float64)
    d = np.asarray(correct_negatives, dtype=np.float64)

    with np.errstate(divide="ignore", invalid="ignore"):
        pod = a / (a + c)
        far = b / (a + b)
        csi = a / (a + b + c)
        total = a + b + c + d
        reference = (a + b) / total * (a + c)
        gss = (a - reference) / (a + b + c - reference)
        hss = 2 * gss / (gss + 1)
        bias = (a + b) / (a + c)
    return {"csi": csi, "pod": pod, "far": far, "hss": hss, "gss": gss, "bias": bias}
