"""Score a saved ensemble offline: every collapse, every metric, one pass.

Reads the HDF5 written by `common/evaluation/ensemble_h5.EnsembleWriter` and
produces, from *one* set of members:

* deterministic scores (CSI/POD/FAR/HSS/bias, MSE/MAE) for the ensemble mean,
  for member 0, and for every individual member,
* probabilistic scores (empirical CRPS, fair CRPS, threshold Brier with its
  background decomposition, spread-skill),
* per-event contingency counts and error sums, so a later paired bootstrap can
  resample events, re-sum TP/FP/FN, and only then form CSI.

The point of doing this offline is that "member 0 of the S=8 run" and "the S=1
run" become the same array by construction, instead of two inference runs whose
noise streams diverge after the first batch.

Usage:

    python tools/evaluate_saved_ensemble.py \
        --input  audit_outputs/controlled_eval/v4_validation_members.h5 \
        --output-dir audit_outputs/controlled_eval/v4_validation_metrics \
        --thresholds 20 30 35 40
"""

import argparse
import csv
import json
import os
import sys

import h5py
import numpy as np

sys.path.append(os.getcwd())

from common.evaluation.ensemble_h5 import read_manifest
from common.metrics.ensemble_probabilistic import (
    EnsembleProbabilisticAccumulator,
    contingency_counts,
    scores_from_counts,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Offline scoring of a saved ensemble member array."
    )
    parser.add_argument("--input", required=True, help="HDF5 written by EnsembleWriter.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=[20.0, 30.0, 35.0, 40.0],
        help="Thresholds on the metric scale (CIKM: dBZ).",
    )
    parser.add_argument(
        "--comparison",
        choices=[">=", ">"],
        default=">=",
        help=(
            "Threshold operator. '>=' matches common/metrics/crft_evaluation.py, "
            "which produced the published CIKM numbers we compare against; '>' "
            "matches FlowCast's own metrics_streaming_probabilistic path. They are "
            "different rulers - pick one and record it."
        ),
    )
    parser.add_argument("--chunk-size", type=int, default=4, help="Events per read.")
    parser.add_argument("--member0-index", type=int, default=0)
    parser.add_argument(
        "--max-events", type=int, default=None, help="Truncate for smoke runs."
    )
    parser.add_argument(
        "--gaussian-fit-legacy",
        action="store_true",
        help=(
            "Also report the legacy Gaussian-fit CRPS on the same members, so the "
            "gap between it and the empirical CRPS is measured rather than argued."
        ),
    )
    parser.add_argument(
        "--skip-per-member",
        action="store_true",
        help="Skip per-member deterministic scores (faster; loses memberwise spread).",
    )
    return parser.parse_args()


class DeterministicAccumulator:
    """Population (accumulate-then-divide) scores for one collapsed field.

    Matches `crft_evaluation.Evaluation`: counts are summed over the whole test
    set first and the ratio is formed once, rather than averaging per-event
    ratios.  Per-event counts are retained separately for bootstrapping.
    """

    def __init__(self, output_length, thresholds, comparison):
        self.output_length = output_length
        self.thresholds = [float(t) for t in thresholds]
        self.comparison = comparison
        shape = (output_length, len(self.thresholds))
        self.hits = np.zeros(shape, dtype=np.int64)
        self.false_alarms = np.zeros(shape, dtype=np.int64)
        self.misses = np.zeros(shape, dtype=np.int64)
        self.correct_negatives = np.zeros(shape, dtype=np.int64)
        self.squared_error_sum = np.zeros(output_length, dtype=np.float64)
        self.absolute_error_sum = np.zeros(output_length, dtype=np.float64)
        self.bias_sum = np.zeros(output_length, dtype=np.float64)
        self.pixel_count = np.zeros(output_length, dtype=np.float64)
        self.per_event_counts = []
        self.per_event_errors = []

    def update(self, truth, prediction):
        difference = prediction.astype(np.float64) - truth.astype(np.float64)
        spatial_axes = (2, 3)
        self.squared_error_sum += np.sum(difference**2, axis=(0, 2, 3))
        self.absolute_error_sum += np.sum(np.abs(difference), axis=(0, 2, 3))
        self.bias_sum += np.sum(difference, axis=(0, 2, 3))
        self.pixel_count += truth.shape[0] * truth.shape[2] * truth.shape[3]

        # (events, leads) error sums for the bootstrap.
        self.per_event_errors.append(
            np.stack(
                [
                    np.sum(difference**2, axis=spatial_axes),
                    np.sum(np.abs(difference), axis=spatial_axes),
                ],
                axis=-1,
            )
        )

        counts = contingency_counts(
            truth, prediction, self.thresholds, self.comparison, axis=spatial_axes
        )
        event_block = np.zeros(
            (truth.shape[0], self.output_length, len(self.thresholds), 4), dtype=np.int64
        )
        for index, threshold in enumerate(self.thresholds):
            per_event = counts[threshold]
            self.hits[:, index] += np.sum(per_event["hits"], axis=0)
            self.false_alarms[:, index] += np.sum(per_event["false_alarms"], axis=0)
            self.misses[:, index] += np.sum(per_event["misses"], axis=0)
            self.correct_negatives[:, index] += np.sum(
                per_event["correct_negatives"], axis=0
            )
            event_block[:, :, index, 0] = per_event["hits"]
            event_block[:, :, index, 1] = per_event["false_alarms"]
            event_block[:, :, index, 2] = per_event["misses"]
            event_block[:, :, index, 3] = per_event["correct_negatives"]
        self.per_event_counts.append(event_block)

    def compute(self):
        scores = scores_from_counts(
            self.hits, self.false_alarms, self.misses, self.correct_negatives
        )
        result = {
            "mse": self.squared_error_sum / self.pixel_count,
            "mae": self.absolute_error_sum / self.pixel_count,
            "bias_additive": self.bias_sum / self.pixel_count,
        }
        result.update(scores)
        # CSI-M / HSS-M: mean over thresholds then over leads, the aggregation
        # the published CIKM tables use.
        result["csi_m"] = float(np.mean(np.nanmean(scores["csi"], axis=1)))
        result["hss_m"] = float(np.mean(np.nanmean(scores["hss"], axis=1)))
        return result

    def stacked_per_event(self):
        return (
            np.concatenate(self.per_event_counts, axis=0),
            np.concatenate(self.per_event_errors, axis=0),
        )


def write_csv(path, header, rows):
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    source_manifest = read_manifest(args.input)

    with h5py.File(args.input, "r") as handle:
        predictions = handle["predictions"]
        truth = handle["truth"]
        event_count = predictions.shape[0]
        if args.max_events is not None:
            event_count = min(event_count, args.max_events)
        member_count = predictions.shape[1]
        output_length = predictions.shape[2]

        if not 0 <= args.member0_index < member_count:
            raise ValueError(
                f"--member0-index {args.member0_index} out of range for "
                f"{member_count} members"
            )

        print(
            f"[eval] {event_count} events x {member_count} members x "
            f"{output_length} leads, comparison '{args.comparison}'"
        )

        probabilistic = EnsembleProbabilisticAccumulator(
            output_length=output_length,
            thresholds=args.thresholds,
            comparison=args.comparison,
            compute_gaussian_fit=args.gaussian_fit_legacy,
        )
        collapses = {
            "ensemble_mean": DeterministicAccumulator(
                output_length, args.thresholds, args.comparison
            ),
            f"member_{args.member0_index}": DeterministicAccumulator(
                output_length, args.thresholds, args.comparison
            ),
        }
        if not args.skip_per_member:
            for member in range(member_count):
                key = f"member_{member}"
                if key not in collapses:
                    collapses[key] = DeterministicAccumulator(
                        output_length, args.thresholds, args.comparison
                    )

        for start in range(0, event_count, args.chunk_size):
            stop = min(start + args.chunk_size, event_count)
            member_chunk = np.asarray(predictions[start:stop], dtype=np.float64)
            truth_chunk = np.asarray(truth[start:stop], dtype=np.float64)

            probabilistic.update(truth_chunk, member_chunk)
            collapses["ensemble_mean"].update(
                truth_chunk, np.mean(member_chunk, axis=1)
            )
            for name, accumulator in collapses.items():
                if name == "ensemble_mean":
                    continue
                member_index = int(name.split("_")[1])
                accumulator.update(truth_chunk, member_chunk[:, member_index])

            if (start // args.chunk_size) % 25 == 0:
                print(f"[eval]   {stop}/{event_count}", flush=True)

    probabilistic_result = probabilistic.compute()
    deterministic_results = {
        name: accumulator.compute() for name, accumulator in collapses.items()
    }

    member_keys = [
        name
        for name in deterministic_results
        if name.startswith("member_")
    ]
    memberwise = {}
    if len(member_keys) > 1:
        for metric in ("csi_m", "hss_m"):
            values = np.array(
                [deterministic_results[key][metric] for key in member_keys]
            )
            memberwise[f"{metric}_mean"] = float(np.mean(values))
            memberwise[f"{metric}_std"] = float(np.std(values, ddof=1))

    # ---- outputs -----------------------------------------------------------
    per_lead = probabilistic_result["per_lead"]
    probabilistic_columns = [
        name for name in per_lead if not name.startswith("brier_")
    ]
    write_csv(
        os.path.join(args.output_dir, "probabilistic_by_lead.csv"),
        ["lead"] + probabilistic_columns,
        [
            [lead] + [float(per_lead[name][lead]) for name in probabilistic_columns]
            for lead in range(probabilistic_result["per_lead"]["crps_empirical"].size)
        ],
    )

    brier_rows = []
    for threshold in args.thresholds:
        for lead in range(output_length):
            brier_rows.append(
                [
                    threshold,
                    lead,
                    float(per_lead[f"brier_all_proper@{threshold:g}"][lead]),
                    float(per_lead[f"brier_observed_event_diagnostic@{threshold:g}"][lead]),
                    float(
                        per_lead[f"brier_observed_nonevent_diagnostic@{threshold:g}"][lead]
                    ),
                    float(per_lead[f"brier_balanced_diagnostic@{threshold:g}"][lead]),
                    float(per_lead[f"brier_active_region_diagnostic@{threshold:g}"][lead]),
                ]
            )
    write_csv(
        os.path.join(args.output_dir, "brier_by_threshold_lead.csv"),
        [
            "threshold",
            "lead",
            "brier_all_proper",
            "brier_observed_event_diagnostic",
            "brier_observed_nonevent_diagnostic",
            "brier_balanced_diagnostic",
            "brier_active_region_diagnostic",
        ],
        brier_rows,
    )

    scalar_rows = []
    threshold_rows = []
    for name, result in deterministic_results.items():
        for lead in range(output_length):
            scalar_rows.append(
                [
                    name,
                    lead,
                    float(result["mse"][lead]),
                    float(result["mae"][lead]),
                    float(result["bias_additive"][lead]),
                ]
            )
            for index, threshold in enumerate(args.thresholds):
                threshold_rows.append(
                    [
                        name,
                        threshold,
                        lead,
                        float(result["csi"][lead, index]),
                        float(result["pod"][lead, index]),
                        float(result["far"][lead, index]),
                        float(result["hss"][lead, index]),
                        float(result["bias"][lead, index]),
                        int(collapses[name].hits[lead, index]),
                        int(collapses[name].false_alarms[lead, index]),
                        int(collapses[name].misses[lead, index]),
                    ]
                )
    write_csv(
        os.path.join(args.output_dir, "deterministic_scalar_by_collapse_lead.csv"),
        ["collapse", "lead", "mse", "mae", "bias_additive"],
        scalar_rows,
    )
    write_csv(
        os.path.join(args.output_dir, "deterministic_threshold_by_collapse_lead.csv"),
        [
            "collapse",
            "threshold",
            "lead",
            "csi",
            "pod",
            "far",
            "hss",
            "frequency_bias",
            "hits",
            "false_alarms",
            "misses",
        ],
        threshold_rows,
    )

    per_event_arrays = {}
    for name, accumulator in collapses.items():
        counts, errors = accumulator.stacked_per_event()
        per_event_arrays[f"{name}__counts"] = counts
        per_event_arrays[f"{name}__errors"] = errors
    per_event_arrays["thresholds"] = np.asarray(args.thresholds, dtype=np.float64)
    np.savez_compressed(
        os.path.join(args.output_dir, "per_event_metrics.npz"), **per_event_arrays
    )

    summary = {
        "input": os.path.abspath(args.input),
        "source_manifest": source_manifest,
        "comparison": args.comparison,
        "thresholds": list(args.thresholds),
        "event_count": probabilistic_result["event_count"],
        "member_count": probabilistic_result["member_count"],
        "probabilistic": probabilistic_result["summary"],
        "deterministic": {
            name: {
                "csi_m": result["csi_m"],
                "hss_m": result["hss_m"],
                "mse_mean": float(np.mean(result["mse"])),
                "mae_mean": float(np.mean(result["mae"])),
                "csi_per_threshold": [
                    float(value) for value in np.nanmean(result["csi"], axis=0)
                ],
            }
            for name, result in deterministic_results.items()
        },
        "memberwise": memberwise,
        "per_event_note": (
            "per_event_metrics.npz stores raw TP/FP/FN/TN and squared/absolute "
            "error sums per event and lead. A paired bootstrap must resample "
            "events, re-sum the counts, and only then form CSI/HSS - averaging "
            "per-event CSI is a different estimator from the population CSI "
            "reported here."
        ),
    }
    with open(os.path.join(args.output_dir, "summary.json"), "w") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True, default=str)

    print("\n[eval] ---- summary ----")
    print(f"[eval] events={summary['event_count']} members={summary['member_count']}")
    for name, result in summary["deterministic"].items():
        print(f"[eval] {name:>16}  CSI-M={result['csi_m']:.4f}  HSS-M={result['hss_m']:.4f}")
    if memberwise:
        print(
            f"[eval] memberwise CSI-M {memberwise['csi_m_mean']:.4f} "
            f"+/- {memberwise['csi_m_std']:.4f}"
        )
    print(f"[eval] empirical CRPS = {summary['probabilistic']['crps_empirical']:.4f}")
    print(f"[eval] fair      CRPS = {summary['probabilistic']['crps_fair']:.4f}")
    if args.gaussian_fit_legacy:
        print(
            "[eval] legacy Gaussian-fit CRPS = "
            f"{summary['probabilistic']['crps_gaussian_fit_legacy']:.4f}"
        )
    print(f"[eval] wrote {args.output_dir}")


if __name__ == "__main__":
    main()
