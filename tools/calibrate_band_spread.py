"""Pre-registered calibration gate for the band-spread gated rollout.

Reads a saved ensemble (``common/evaluation/ensemble_h5.EnsembleWriter``
layout, e.g. the controlled-eval validation members file) and decides whether
band-wise ensemble spread is a usable error proxy -- the go/no-go condition
for implementing the gated rollout as an experiment arm.

Zero training, zero model loading: this is pure offline analysis of arrays
already on disk.  Typical run:

    python tools/calibrate_band_spread.py \
        --input  audit_outputs/controlled_eval/v4_validation_members.h5 \
        --output-dir audit_outputs/band_spread_calibration \
        --mapping-leads 0 5

Outputs:

* ``calibration_report.json`` -- verdict (green/red/undetermined), per-band
  correlations with event-cluster bootstrap CIs, dynamic-range flags, the
  spread definition comparison, and alpha-mapping quantiles;
* ``per_event_band_rows.csv`` -- one row per (event, lead, band) with both
  spread definitions and the band error, for independent re-analysis;
* console summary with the same verdict string as the JSON (the three-state
  verdict must survive to every user-visible outlet).

The decision thresholds live in
``common/evaluation/band_spread_calibration.CalibrationProtocol`` and are not
CLI-tunable on purpose: they are part of the pre-registration.
"""

import argparse
import csv
import json
import os
import sys

import h5py
import numpy as np
import torch

sys.path.append(os.getcwd())

from common.evaluation.band_spread_calibration import (
    CalibrationProtocol,
    compute_event_record,
    run_band_calibration,
)
from common.metrics.band_spectral import radial_band_masks


def parse_args():
    parser = argparse.ArgumentParser(
        description="Band-spread calibration from a saved ensemble HDF5."
    )
    parser.add_argument(
        "--input", required=True, help="HDF5 written by EnsembleWriter."
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Cap on events read (debug only; the verdict on a capped run is "
        "not the pre-registered verdict).",
    )
    parser.add_argument("--chunk-size", type=int, default=8, help="Events per read.")
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Device for the FFT band math.",
    )
    parser.add_argument(
        "--mapping-leads",
        type=int,
        nargs=2,
        required=True,
        metavar=("LO", "HI"),
        help="Half-open lead range informing the alpha-mapping quantiles. "
        "REQUIRED and validated against the file's lead count: the gate acts "
        "at the first chunk boundary, so pass that chunk's leads (CIKM in5: "
        "'0 5'). All-lead pooling would inflate the quantiles with later, "
        "larger spreads and silently under-gate at runtime.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    protocol = CalibrationProtocol(mapping_lead_range=tuple(args.mapping_leads))

    with h5py.File(args.input, "r") as handle:
        predictions = handle["predictions"]
        truth = handle["truth"]
        event_index = handle["event_index"][:]
        manifest = handle.attrs.get("manifest_json", "{}")

        n_total = predictions.shape[0]
        n_events = min(n_total, args.max_events) if args.max_events else n_total
        height, width = truth.shape[-2:]
        masks = radial_band_masks(
            height, width, protocol.band_edges, device=args.device
        )

        records = []
        truth_value_max = 0.0
        for start in range(0, n_events, args.chunk_size):
            stop = min(start + args.chunk_size, n_events)
            pred_chunk = np.asarray(predictions[start:stop], dtype=np.float32)
            truth_chunk = np.asarray(truth[start:stop], dtype=np.float32)
            truth_value_max = max(truth_value_max, float(truth_chunk.max()))
            for offset in range(stop - start):
                members = torch.as_tensor(pred_chunk[offset], device=args.device)
                target = torch.as_tensor(truth_chunk[offset], device=args.device)
                records.append(
                    compute_event_record(
                        int(event_index[start + offset]), members, target, masks
                    )
                )
            print(f"processed events {stop}/{n_events}", flush=True)

    input_manifest = json.loads(manifest) if manifest else {}
    # Machine-readable fingerprint of the view the quantiles are measured on.
    # Height/width come from the data itself; the value ceiling is measured
    # from truth (clamped metric view, so ~pixel_scale) rather than trusted
    # from the manifest.  SpreadToAlpha.from_report refuses reports without
    # this block.
    view = {
        "height": int(height),
        "width": int(width),
        "value_ceiling_measured": truth_value_max,
        "pixel_scale_from_manifest": input_manifest.get("pixel_scale"),
        "crop_from_manifest": input_manifest.get("crop"),
        "spread_definition": "spatial",
        "view_id": "ensemble_h5_metric_view",
    }
    result = run_band_calibration(records, protocol, view=view)
    result["input"] = os.path.abspath(args.input)
    result["input_manifest"] = input_manifest
    if args.max_events and args.max_events < n_total:
        result["reasons"].append(
            f"DEBUG RUN: capped at {args.max_events}/{n_total} events; this "
            "verdict is not the pre-registered verdict"
        )

    report_path = os.path.join(args.output_dir, "calibration_report.json")
    with open(report_path, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)

    rows_path = os.path.join(args.output_dir, "per_event_band_rows.csv")
    with open(rows_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "event_index",
                "lead",
                "band",
                "spread_spatial",
                "spread_power",
                "rmse_ensemble_mean",
            ]
        )
        for record in sorted(records, key=lambda r: r.event_index):
            leads, bands = record.spread_spatial.shape
            for t in range(leads):
                for j in range(bands):
                    writer.writerow(
                        [
                            record.event_index,
                            t,
                            j,
                            f"{record.spread_spatial[t, j]:.8e}",
                            f"{record.spread_power[t, j]:.8e}",
                            f"{record.rmse_ensemble_mean[t, j]:.8e}",
                        ]
                    )

    print("\n=== band-spread calibration ===")
    print(f"events: {result['n_events']}")
    for band in result.get("bands", []):
        print(
            f"band {band['band']} [{band['edge_lo']:.4f},{band['edge_hi']:.4f}] "
            f"rho_spatial={band['rho_spatial']:.3f} "
            f"ci={tuple(round(v, 3) for v in band['ci_spatial'])} "
            f"rho_power={band['rho_power']:.3f} "
            f"degenerate={band['degenerate']} ssr={band['spread_skill_ratio_spatial']}"
        )
    print(f"VERDICT: {result['verdict']}")
    for reason in result["reasons"]:
        print(f"  - {reason}")
    print(f"report: {report_path}")
    print(f"rows:   {rows_path}")


if __name__ == "__main__":
    main()
