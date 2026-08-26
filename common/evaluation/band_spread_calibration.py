"""Offline calibration: is band-wise ensemble spread a usable error proxy?

This is the pre-registered go/no-go gate for the band-spread gated rollout
(the trusted-prior post-mortem rule: measure that the gate signal correlates
with the actual error *before* building the gate).  It consumes a saved
ensemble (``common/evaluation/ensemble_h5.EnsembleWriter`` layout: members
``(N, M, T, H, W)``, truth ``(N, T, H, W)``, on the metric view) and answers,
per radial frequency band:

1.  Does cross-member spread correlate with the ensemble-mean error?
    Both spread definitions are measured side by side -- the phase-sensitive
    ``spatial`` one and the translation-invariant ``power`` one -- because the
    prediction on record is that only the spatial definition carries the
    displacement-driven part of the signal.
2.  Does the spread have dynamic range?  A band whose spread barely varies
    across events would make the gate a *static* band weight: that
    configuration is already published (PW-FouCast / FADiff) and holds no
    delta, so it fails the calibration even if the correlation is formally
    positive.

Verdict is three-state and fail-closed (green / red / undetermined):
``undetermined`` means the measurement is incomplete, never a weaker shade of
go -- the same discipline as the Stage -1 AE gates.  Statistical rules learned
the hard way and frozen here:

* the independent unit is the *event*, never the (event, lead) row;
* bootstrap resamples events after sorting by ``event_index`` -- resampling in
  input order makes the verdict depend on DataLoader order (a reproduced P0
  in the AE-gate line);
* Spearman, not Pearson: spread/error relations are monotone at best, and
  radar error magnitudes are heavy-tailed;
* non-finite *inputs* veto the verdict (measurement incomplete), but
  *estimator* degeneracies do not get to hide a pre-registered RED: exact
  spread collapse routes to the static-band-weight RED, and a power-definition
  breakdown on a displacement-dominated ensemble is the predicted
  confirmation, not a measurement failure (adversarial review 2026-08-10,
  findings on NaN fail-open and veto ordering);
* the exported alpha mapping carries a machine-readable view fingerprint;
  a report without one is explicitly marked not deployable.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import torch

from common.metrics.band_spectral import (
    DEFAULT_BAND_EDGES,
    ensemble_mean_band_rmse,
    power_band_spread,
    radial_band_masks,
    spatial_band_spread,
)

__all__ = [
    "CalibrationProtocol",
    "EventBandRecord",
    "run_band_calibration",
    "spearman",
]

GREEN = "green"
RED = "red"
UNDETERMINED = "undetermined"


def _average_ranks(values: np.ndarray) -> np.ndarray:
    """Ranks (1-based) with ties assigned their average rank."""
    values = np.asarray(values, dtype=np.float64)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    sorted_values = values[order]
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and sorted_values[j + 1] == sorted_values[i]:
            j += 1
        # positions i..j share the value -> average of ranks (i+1 .. j+1)
        ranks[order[i : j + 1]] = 0.5 * ((i + 1) + (j + 1))
        i = j + 1
    return ranks


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation with average-tie ranks; NaN if degenerate.

    Non-finite inputs return NaN (scipy semantics).  Without this guard,
    argsort places NaNs at the top rank and the function returns a finite
    *pseudo*-correlation -- the reproduced fake-GREEN path from the
    adversarial review.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.shape != y.shape or x.ndim != 1:
        raise ValueError("spearman expects two equal-length 1-D arrays")
    if len(x) < 3:
        return float("nan")
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        return float("nan")
    rx = _average_ranks(x)
    ry = _average_ranks(y)
    sx = rx.std()
    sy = ry.std()
    if sx == 0.0 or sy == 0.0:
        return float("nan")
    return float(np.mean((rx - rx.mean()) * (ry - ry.mean())) / (sx * sy))


@dataclass(frozen=True)
class CalibrationProtocol:
    """Frozen decision rules.  Change fields only by editing code, on purpose:

    the thresholds are part of the pre-registration, not run-time knobs.
    """

    band_edges: Tuple[float, ...] = DEFAULT_BAND_EDGES
    min_events: int = 30
    bootstrap_iterations: int = 1000
    bootstrap_seed: int = 42
    # green requires: among gated bands (all but band 0, which the gate pins
    # to full trust anyway), at least `green_min_bands` non-degenerate bands
    # with bootstrap ci_low > 0 under the *spatial* definition, and their
    # median rho >= green_min_rho.
    green_min_rho: float = 0.3
    green_min_bands: int = 2
    # dynamic range: a band is degenerate when IQR/median of its per-event
    # spread falls below this (or median is not positive).  Applied to each
    # spread definition separately -- a power-degenerate band must not enter
    # power_pass on the back of a conditioned bootstrap CI.
    dynamic_range_min: float = 0.1
    # absolute floor: spread must be a non-trivial fraction of the band error
    # (same units, view-invariant).  Float-noise-level spread in an
    # AE-suppressed top band would otherwise pass the pure-ratio dynamic
    # range check and export a deployable noise mapping.
    min_spread_skill_ratio: float = 1e-3
    # bootstrap CIs are reported only when at least this fraction of the
    # resampled statistics is finite; below it the CI is conditioned on
    # non-degenerate resamples and systematically optimistic.
    ci_min_finite_fraction: float = 0.95
    # alpha-mapping ingredients (quantiles of per-event spread).
    mapping_quantiles: Tuple[float, float] = (0.25, 0.75)
    # Leads whose spread informs the alpha mapping, as a half-open [lo, hi).
    # ``None`` pools ALL leads.  A deployment mapping must set this explicitly
    # to the leads of the first chunk (CIKM in5: ``(0, 5)``): the gate acts at
    # the first chunk boundary and sees only that chunk's spread, while
    # all-lead pooling inflates the quantiles with the later, larger spreads.
    mapping_lead_range: Optional[Tuple[int, int]] = None

    @property
    def num_bands(self) -> int:
        return len(self.band_edges) - 1


@dataclass
class EventBandRecord:
    """Per-event band statistics, all ``(T, J)`` float64 arrays."""

    event_index: int
    spread_spatial: np.ndarray
    spread_power: np.ndarray
    rmse_ensemble_mean: np.ndarray

    def pooled(self, lead_range: Optional[Tuple[int, int]] = None) -> Dict[str, np.ndarray]:
        leads = self.spread_spatial.shape[0]
        if lead_range is None:
            lo, hi = 0, leads
        else:
            lo, hi = lead_range
            if not (0 <= lo < hi <= leads):
                raise ValueError(
                    f"mapping_lead_range ({lo}, {hi}) invalid for T={leads} "
                    "leads; require 0 <= lo < hi <= T (fail-closed: an empty "
                    "slice would emit NaN quantiles and out-of-range values "
                    "would be silently truncated while the report records the "
                    "requested range)"
                )
        return {
            "spread_spatial": self.spread_spatial[lo:hi].mean(axis=0),
            "spread_power": self.spread_power[lo:hi].mean(axis=0),
            "rmse_ensemble_mean": self.rmse_ensemble_mean[lo:hi].mean(axis=0),
        }


def compute_event_record(
    event_index: int,
    members: torch.Tensor,
    truth: torch.Tensor,
    masks: torch.Tensor,
) -> EventBandRecord:
    """Band statistics for one event: members ``(M, T, H, W)``, truth ``(T, H, W)``."""
    with torch.no_grad():
        return EventBandRecord(
            event_index=int(event_index),
            spread_spatial=spatial_band_spread(members, masks).cpu().numpy(),
            spread_power=power_band_spread(members, masks).cpu().numpy(),
            rmse_ensemble_mean=ensemble_mean_band_rmse(members, truth, masks)
            .cpu()
            .numpy(),
        )


def _bootstrap_spearman_ci(
    spread: np.ndarray,
    error: np.ndarray,
    iterations: int,
    seed: int,
    min_finite_fraction: float,
) -> Tuple[float, float, float]:
    """Event-cluster bootstrap 95% CI for Spearman(spread, error).

    Inputs are per-event vectors already sorted by event_index (the caller
    guarantees ordering; this function only resamples).  Returns
    ``(lo, hi, finite_fraction)``; the CI is NaN when too many resamples were
    degenerate -- a CI conditioned on "the resample happened to carry rank
    information" is not the advertised CI.
    """
    rng = np.random.default_rng(seed)
    n = len(spread)
    stats = []
    for _ in range(iterations):
        idx = rng.integers(0, n, size=n)
        rho = spearman(spread[idx], error[idx])
        if np.isfinite(rho):
            stats.append(rho)
    finite_fraction = len(stats) / float(iterations)
    if finite_fraction < min_finite_fraction:
        return float("nan"), float("nan"), finite_fraction
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return float(lo), float(hi), finite_fraction


def _degenerate(median: float, iqr: float, threshold: float) -> bool:
    return (not np.isfinite(median)) or median <= 0.0 or (iqr / median) < threshold


def run_band_calibration(
    events: Iterable[EventBandRecord],
    protocol: CalibrationProtocol,
    view: Optional[Dict] = None,
) -> Dict:
    """Aggregate per-event records into per-band statistics and a verdict.

    ``events`` yields ``EventBandRecord``s in any order; everything downstream
    sorts by ``event_index`` first so the verdict cannot depend on input
    order.  ``view`` is the machine-readable fingerprint of the input view
    (height/width/value scale); without it the exported alpha mapping is
    marked not deployable.
    """
    records = sorted(events, key=lambda r: r.event_index)
    seen = set()
    for r in records:
        if r.event_index in seen:
            raise ValueError(f"duplicate event_index {r.event_index}")
        seen.add(r.event_index)

    n_events = len(records)
    result: Dict = {
        "n_events": n_events,
        "protocol": {
            "band_edges": list(protocol.band_edges),
            "min_events": protocol.min_events,
            "green_min_rho": protocol.green_min_rho,
            "green_min_bands": protocol.green_min_bands,
            "dynamic_range_min": protocol.dynamic_range_min,
            "min_spread_skill_ratio": protocol.min_spread_skill_ratio,
            "ci_min_finite_fraction": protocol.ci_min_finite_fraction,
            "bootstrap_iterations": protocol.bootstrap_iterations,
            "bootstrap_seed": protocol.bootstrap_seed,
            "mapping_quantiles": list(protocol.mapping_quantiles),
            "mapping_lead_range": (
                list(protocol.mapping_lead_range)
                if protocol.mapping_lead_range
                else None
            ),
        },
        "view": view,
        "deployable": view is not None,
        "bands": [],
        "verdict": UNDETERMINED,
        "reasons": [],
    }
    if view is None:
        result["reasons"].append(
            "no view fingerprint supplied: correlations are valid but the "
            "alpha mapping is NOT deployable (SpreadToAlpha.from_report will "
            "refuse this file)"
        )
    if n_events < protocol.min_events:
        result["reasons"].append(
            f"insufficient events: {n_events} < min_events={protocol.min_events}"
        )
        return result

    pooled = [r.pooled() for r in records]  # per-event (J,) vectors
    num_bands = protocol.num_bands
    spatial_pass = []
    power_pass = []
    input_nan_bands = []
    estimator_nan_bands = []
    mapping_nan_bands = []

    for j in range(num_bands):
        s_spatial = np.array([p["spread_spatial"][j] for p in pooled])
        s_power = np.array([p["spread_power"][j] for p in pooled])
        err = np.array([p["rmse_ensemble_mean"][j] for p in pooled])

        input_nan = not (
            np.isfinite(s_spatial).all()
            and np.isfinite(s_power).all()
            and np.isfinite(err).all()
        )
        if input_nan:
            input_nan_bands.append(j)

        # spread/skill ratio first: it doubles as the absolute floor of the
        # degeneracy check (a float-noise spread passes a pure IQR/median
        # ratio but not a same-units comparison against the band error).
        with np.errstate(divide="ignore", invalid="ignore"):
            ssr = float(np.nanmedian(np.where(err > 0, s_spatial / err, np.nan)))

        median = float(np.median(s_spatial))
        iqr = float(np.percentile(s_spatial, 75) - np.percentile(s_spatial, 25))
        degenerate_spatial = (
            _degenerate(median, iqr, protocol.dynamic_range_min)
            or (not np.isfinite(ssr))
            or ssr < protocol.min_spread_skill_ratio
        )
        median_p = float(np.median(s_power))
        iqr_p = float(np.percentile(s_power, 75) - np.percentile(s_power, 25))
        # Second clause: when members disagree almost purely by phase (pure
        # displacement), the amplitude spread is float-FFT rounding noise --
        # orders of magnitude below the spatial spread -- and rounding noise
        # can rank-correlate with anything.  A power spread that small carries
        # no signal by construction and must not enter power_pass.
        degenerate_power = _degenerate(
            median_p, iqr_p, protocol.dynamic_range_min
        ) or (median_p < protocol.min_spread_skill_ratio * median)

        rho_spatial = spearman(s_spatial, err)
        rho_power = spearman(s_power, err)
        ci_spatial = _bootstrap_spearman_ci(
            s_spatial,
            err,
            protocol.bootstrap_iterations,
            protocol.bootstrap_seed + j,
            protocol.ci_min_finite_fraction,
        )
        ci_power = _bootstrap_spearman_ci(
            s_power,
            err,
            protocol.bootstrap_iterations,
            protocol.bootstrap_seed + j,
            protocol.ci_min_finite_fraction,
        )

        # An estimator NaN on a quantity the verdict actually needs -- the
        # spatial definition of a gated, non-degenerate band -- means the
        # measurement is incomplete.  Band 0 (never gated) and the power
        # definition (whose breakdown is a predicted outcome, and which the
        # degeneracy flag already excludes from power_pass) do not veto.
        if (
            j != 0
            and not degenerate_spatial
            and not input_nan
            and not np.isfinite(rho_spatial)
        ):
            estimator_nan_bands.append(j)

        band = {
            "band": j,
            "edge_lo": protocol.band_edges[j],
            "edge_hi": protocol.band_edges[j + 1],
            "gated": j != 0,
            "input_nan": bool(input_nan),
            "degenerate": bool(degenerate_spatial),
            "degenerate_power": bool(degenerate_power),
            "dynamic_range_iqr_over_median": (iqr / median) if median > 0 else None,
            "rho_spatial": rho_spatial,
            "ci_spatial": list(ci_spatial[:2]),
            "ci_spatial_finite_fraction": ci_spatial[2],
            "rho_power": rho_power,
            "ci_power": list(ci_power[:2]),
            "ci_power_finite_fraction": ci_power[2],
            "spread_skill_ratio_spatial": ssr,
            "spread_spatial_median": median,
        }

        if degenerate_spatial or input_nan:
            # never export a mapping for a band the gate must not act on;
            # SpreadToAlpha.from_report turns excluded bands into
            # alpha == 1 pass-through
            band["alpha_mapping"] = None
        else:
            lo_q, hi_q = protocol.mapping_quantiles
            mapping_pool = [
                r.pooled(protocol.mapping_lead_range)["spread_spatial"][j]
                for r in records
            ]
            q_lo = float(np.quantile(mapping_pool, lo_q))
            q_hi = float(np.quantile(mapping_pool, hi_q))
            if not (np.isfinite(q_lo) and np.isfinite(q_hi)):
                mapping_nan_bands.append(j)
            band["alpha_mapping"] = {
                "q_lo": q_lo,
                "q_hi": q_hi,
                "view_note": (
                    "quantiles are on the view fingerprinted in result['view']; "
                    "the runtime gate must compute spread on that same view "
                    "(scale, crop, clamp)"
                ),
            }
        result["bands"].append(band)

        if j != 0 and not input_nan:
            if (
                not degenerate_spatial
                and np.isfinite(ci_spatial[0])
                and ci_spatial[0] > 0
            ):
                spatial_pass.append((j, rho_spatial))
            if (
                not degenerate_power
                and np.isfinite(ci_power[0])
                and ci_power[0] > 0
            ):
                power_pass.append((j, rho_power))

    result["definition_comparison"] = {
        "spatial_bands_passing": [j for j, _ in spatial_pass],
        "power_bands_passing": [j for j, _ in power_pass],
        "note": (
            "if only the spatial definition passes, the displacement-"
            "sensitivity prediction is confirmed and the gate must use it"
        ),
    }

    # ---- verdict, in pre-registered order ----
    # 1. corrupt inputs veto everything: measurement incomplete.
    if input_nan_bands:
        result["reasons"].append(
            f"non-finite input statistics in bands {input_nan_bands} "
            "(NaN members / decode failures upstream); measurement incomplete"
        )
        return result

    # 2. spread collapse reaches its pre-registered RED even when the
    #    collapse is exact (which makes the correlation estimator NaN).
    gated_bands = [b for b in result["bands"] if b["gated"]]
    degenerate_count = sum(1 for b in gated_bands if b["degenerate"])
    if degenerate_count > len(gated_bands) // 2:
        result["verdict"] = RED
        result["reasons"].append(
            f"{degenerate_count}/{len(gated_bands)} gated bands have no "
            "spread dynamic range: the gate would reduce to a static band "
            "weight (already published: PW-FouCast/FADiff), delta empty"
        )
        return result

    # 3. estimator/quantile breakdown on needed quantities.
    if estimator_nan_bands or mapping_nan_bands:
        if estimator_nan_bands:
            result["reasons"].append(
                f"spatial correlation undefined in non-degenerate gated bands "
                f"{estimator_nan_bands}; measurement incomplete"
            )
        if mapping_nan_bands:
            result["reasons"].append(
                f"alpha-mapping quantiles undefined in bands {mapping_nan_bands}"
            )
        return result

    # 4. green / red / weak.
    if (
        len(spatial_pass) >= protocol.green_min_bands
        and float(np.median([rho for _, rho in spatial_pass]))
        >= protocol.green_min_rho
    ):
        result["verdict"] = GREEN
        result["reasons"].append(
            f"spatial spread correlates with band error in bands "
            f"{[j for j, _ in spatial_pass]} (ci_low > 0), median rho = "
            f"{float(np.median([rho for _, rho in spatial_pass])):.3f}"
        )
    elif len(spatial_pass) == 0 and len(power_pass) == 0:
        result["verdict"] = RED
        result["reasons"].append(
            "no gated band shows ci_low > 0 under either spread definition: "
            "spread is not a usable error proxy on this checkpoint/split "
            "(same failure class as trusted-prior)"
        )
    else:
        result["reasons"].append(
            f"weak signal: spatial bands passing = {[j for j, _ in spatial_pass]}, "
            f"power bands passing = {[j for j, _ in power_pass]}; below the "
            f"green rule (>= {protocol.green_min_bands} bands, median rho >= "
            f"{protocol.green_min_rho})"
        )
    return result


def iter_records_from_arrays(
    predictions: np.ndarray,
    truth: np.ndarray,
    event_indices: Sequence[int],
    protocol: CalibrationProtocol,
    device: str = "cpu",
) -> List[EventBandRecord]:
    """Convenience: build records from in-memory ``(N, M, T, H, W)`` arrays."""
    if predictions.ndim != 5 or truth.ndim != 4:
        raise ValueError(
            "expected predictions (N, M, T, H, W) and truth (N, T, H, W), got "
            f"{predictions.shape} and {truth.shape}"
        )
    if predictions.shape[0] != truth.shape[0] or predictions.shape[0] != len(
        event_indices
    ):
        raise ValueError("N mismatch between predictions, truth, event_indices")
    height, width = truth.shape[-2:]
    masks = radial_band_masks(height, width, protocol.band_edges, device=device)
    records = []
    for n in range(predictions.shape[0]):
        members = torch.as_tensor(
            np.asarray(predictions[n], dtype=np.float32), device=device
        )
        target = torch.as_tensor(
            np.asarray(truth[n], dtype=np.float32), device=device
        )
        records.append(
            compute_event_record(event_indices[n], members, target, masks)
        )
    return records
