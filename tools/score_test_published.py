"""Score an ensemble HDF5 in the *published* CIKM protocol.

Why this exists rather than reusing ``score_gate_arms.py``: that tool pools
TP/FP/FN over every event **and every lead** in a chunk and divides once.
The number every published CIKM table reports is a different statistic --
one accumulator per lead, CSI computed per lead, then an equal-weight mean
over leads, then a mean over thresholds (verified against the evaluator:
mean(0.6626, 0.3564, 0.2520, 0.2000) = 0.36777 reproduces a logged CSI-M
of 0.3677738 exactly).  Comparing a pooled number against a published
per-lead number is the same class of error as comparing S=8 against S=1.

Conventions, all matched to ``common/metrics/metrics_streaming_probabilistic``:

* CSI/HSS use **strict** ``>`` (the evaluator does; measured to make no
  difference on CIKM, where no pixel quantises to exactly 30 dBZ, but the
  operator is matched anyway rather than argued about);
* thresholds 20/30/35/40 dBZ on the 0-90 scale;
* the writer has already applied ``decode -> x90 -> crop[13:-14] -> clamp``,
  so the arrays here are the metric view and nothing is rescaled;
* ``--members 1`` reproduces the single-sample protocol of the published
  tables; ``--collapse mean`` scores the ensemble mean and is **not**
  comparable to those tables (an ensemble mean inflates CSI substantially on
  this benchmark -- that is a protocol artefact, not a result).

Gate: run this on a fresh teacher dump and check CSI-M against the value
the training pipeline logged for the same checkpoint at S=1 on CIKM
test.  A mismatch means the chain is wrong
somewhere and no arm comparison is trustworthy.
"""

import argparse
import json
import os
import sys

import h5py
import numpy as np

sys.path.append(os.getcwd())

THRESHOLDS = (20.0, 30.0, 35.0, 40.0)


def score(path: str, collapse: str, max_events=None) -> dict:
    with h5py.File(path, "r") as handle:
        preds, truth = handle["predictions"], handle["truth"]
        n_all, n_members, n_leads = preds.shape[0], preds.shape[1], preds.shape[2]
        n = n_all if max_events is None else min(max_events, n_all)

        # One accumulator per (threshold, lead) -- the whole point of this tool.
        tp = np.zeros((len(THRESHOLDS), n_leads), dtype=np.float64)
        fp = np.zeros_like(tp)
        fn = np.zeros_like(tp)
        tn = np.zeros_like(tp)
        sse = np.zeros(n_leads, dtype=np.float64)
        sae = np.zeros(n_leads, dtype=np.float64)
        npix = np.zeros(n_leads, dtype=np.float64)

        for i in range(n):
            members = np.asarray(preds[i], dtype=np.float32)      # (S, T, H, W)
            obs = np.asarray(truth[i], dtype=np.float32)          # (T, H, W)
            if collapse == "member0":
                pred = members[0]
            elif collapse == "mean":
                pred = members.mean(axis=0)
            elif collapse == "max":
                pred = members.max(axis=0)
            elif collapse.startswith("q"):
                # Per-pixel quantile of the member distribution.  This is a
                # different *product*, not a different model: nobody issues an
                # ensemble mean as a severe-weather warning, and a mean is the
                # one collapse guaranteed to erode exceedances.  Reported so the
                # extreme-fidelity question is asked of the object an operator
                # would actually use.
                q = float(collapse[1:]) / 100.0
                if not 0.0 < q < 1.0:
                    raise ValueError(f"quantile out of range in {collapse!r}")
                pred = np.quantile(members, q, axis=0)
            else:
                raise ValueError(f"unknown collapse {collapse!r}")

            diff = pred - obs
            sse += (diff ** 2).sum(axis=(1, 2))
            sae += np.abs(diff).sum(axis=(1, 2))
            npix += float(diff.shape[1] * diff.shape[2])

            for k, thr in enumerate(THRESHOLDS):
                p = pred > thr
                o = obs > thr
                tp[k] += (p & o).sum(axis=(1, 2))
                fp[k] += (p & ~o).sum(axis=(1, 2))
                fn[k] += (~p & o).sum(axis=(1, 2))
                tn[k] += (~p & ~o).sum(axis=(1, 2))

    csi = tp / np.maximum(tp + fp + fn, 1.0)                      # (K, T)
    denom = (tp + fn) * (fn + tn) + (tp + fp) * (fp + tn)
    hss = 2.0 * (tp * tn - fn * fp) / np.maximum(denom, 1e-12)

    per_threshold_csi = csi.mean(axis=1)                          # lead-average
    per_threshold_hss = hss.mean(axis=1)
    return {
        "file": os.path.abspath(path),
        "collapse": collapse,
        "n_events": int(n),
        "n_members_in_file": int(n_members),
        "n_leads": int(n_leads),
        "csi_per_threshold": {str(int(t)): float(v)
                              for t, v in zip(THRESHOLDS, per_threshold_csi)},
        "hss_per_threshold": {str(int(t)): float(v)
                              for t, v in zip(THRESHOLDS, per_threshold_hss)},
        "csi_m": float(per_threshold_csi.mean()),
        "hss_m": float(per_threshold_hss.mean()),
        "mse": float((sse / npix).mean()),
        "mae": float((sae / npix).mean()),
        "csi_per_lead_m": [float(v) for v in csi.mean(axis=0)],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--arms", nargs="+", required=True, help="name=path.h5")
    p.add_argument("--collapse", default="member0",
                   help="member0 | mean | max | qNN (per-pixel NNth percentile)")
    p.add_argument("--max-events", type=int, default=None)
    p.add_argument("--output", default=None)
    p.add_argument("--gate-arm", default=None,
                   help="Arm whose CSI-M must match --gate-value.")
    p.add_argument("--gate-value", type=float, default=None)
    p.add_argument("--gate-tol", type=float, default=0.002)
    args = p.parse_args()

    results = {}
    for spec in args.arms:
        name, _, path = spec.partition("=")
        results[name] = score(path, args.collapse, args.max_events)
        print(f"scored {name}: {results[name]['n_events']} events", flush=True)

    print(f"\n=== published CIKM protocol (collapse={args.collapse}, "
          f"per-lead CSI then lead-average) ===")
    hdr = f"{'arm':<13}{'@20':>9}{'@30':>9}{'@35':>9}{'@40':>9}{'CSI-M':>9}{'HSS-M':>9}{'MSE':>9}"
    print(hdr)
    print("-" * len(hdr))
    for name, r in results.items():
        c = r["csi_per_threshold"]
        print(f"{name:<13}{c['20']:>9.4f}{c['30']:>9.4f}{c['35']:>9.4f}"
              f"{c['40']:>9.4f}{r['csi_m']:>9.5f}{r['hss_m']:>9.4f}{r['mse']:>9.2f}")

    ok = True
    if args.gate_arm and args.gate_value is not None:
        got = results[args.gate_arm]["csi_m"]
        ok = abs(got - args.gate_value) <= args.gate_tol
        print(f"\n=== CHAIN GATE ===")
        print(f"  {args.gate_arm} CSI-M = {got:.5f}, expected {args.gate_value:.5f} "
              f"(tol {args.gate_tol})")
        print(f"  VERDICT: {'PASS' if ok else 'FAIL - chain is wrong, do not read the arms'}")

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump({"collapse": args.collapse, "gate_passed": ok,
                       "results": results}, f, indent=2)
        print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
