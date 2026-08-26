"""Bounded-oracle ceiling for a threshold-error-risk-gated pixel refiner.

Question this answers at zero GPU cost: if a corrector could add a per-pixel
residual bounded by +-b dBZ, with a PERFECT oracle telling it where the errors
are and which direction to move, how much published-protocol CSI-M is on the
table?  The oracle action `pred' = pred + clip(truth - pred, -b, b)` is the
exact supremum of the refiner's action space (per-pixel bounded residual):
moving toward truth maximises, for every pixel, the set of thresholds on the
correct side, and keeps the corrected field a single consistent continuous
map (M40 subset of M35 for free).  Any trained risk net + corrector is <= this.

Also dumps the error-depth distributions: for FN at k, depth = k - pred over
FN pixels; for FP, height = pred - k.  If most FN@40 sit far below 40 the
bounded head cannot reach them regardless of how good the risk map is
(mass-deficit errors, not graze errors).

Protocol matched to tools/score_test_published.py: strict `>`, thresholds
20/30/35/40 on the 0-90 metric view the writer already produced, one
accumulator per (threshold, lead), CSI per lead, equal-weight mean over
leads, then mean over thresholds.  Member --member-index only (S=1 protocol).

Usage:
    python oracle_bounded_ceiling.py --input <ensemble.h5> --output <out.json> \
        [--member-index 0] [--budgets 1 2 3 5 8] [--max-events N]
"""

import argparse
import json

import h5py
import numpy as np

THRESHOLDS = (20.0, 30.0, 35.0, 40.0)
DEPTH_THRESHOLDS = (35.0, 40.0)
DEPTH_BIN_EDGES = np.concatenate([np.arange(0.0, 30.5, 0.5), [90.0]])


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--member-index", type=int, default=0)
    p.add_argument("--budgets", type=float, nargs="+", default=[1, 2, 3, 5, 8])
    p.add_argument("--max-events", type=int, default=None)
    return p.parse_args()


def csi_published(tp, fp, fn):
    """tp/fp/fn: (n_thr, n_leads) -> per-threshold per-lead CSI, lead-mean, overall."""
    denom = tp + fp + fn
    with np.errstate(invalid="ignore", divide="ignore"):
        csi = np.where(denom > 0, tp / denom, np.nan)
    per_thr = np.nanmean(csi, axis=1)
    return csi, per_thr, float(np.nanmean(per_thr))


def main():
    args = parse_args()
    budgets = [float(b) for b in args.budgets]
    with h5py.File(args.input, "r") as handle:
        preds, truth = handle["predictions"], handle["truth"]
        n_all, n_members, n_leads = preds.shape[0], preds.shape[1], preds.shape[2]
        n = n_all if args.max_events is None else min(args.max_events, n_all)

        shape2 = (len(THRESHOLDS), n_leads)
        base = {k: np.zeros(shape2) for k in ("tp", "fp", "fn")}
        orac = {
            b: {k: np.zeros(shape2) for k in ("tp", "fp", "fn")} for b in budgets
        }
        # depth histograms pooled over events+leads, per threshold, fn/fp
        depth_hist = {
            f"{kind}{int(k)}": np.zeros(len(DEPTH_BIN_EDGES) - 1)
            for k in DEPTH_THRESHOLDS
            for kind in ("fn", "fp")
        }

        for i in range(n):
            p = np.asarray(preds[i, args.member_index], dtype=np.float32)  # (T,H,W)
            t = np.asarray(truth[i], dtype=np.float32)
            if t.ndim == 4:  # (1,T,H,W) guard
                t = t[0]
            gap = t - p

            for j, thr in enumerate(THRESHOLDS):
                pb, tb = p > thr, t > thr
                for lead in range(n_leads):
                    pbl, tbl = pb[lead], tb[lead]
                    base["tp"][j, lead] += np.sum(pbl & tbl)
                    base["fp"][j, lead] += np.sum(pbl & ~tbl)
                    base["fn"][j, lead] += np.sum(~pbl & tbl)

            for thr in DEPTH_THRESHOLDS:
                pb, tb = p > thr, t > thr
                fn_depth = (thr - p)[~pb & tb]  # how far below thr the missed pixels sit
                fp_height = (p - thr)[pb & ~tb]  # how far above thr the false alarms sit
                depth_hist[f"fn{int(thr)}"] += np.histogram(fn_depth, DEPTH_BIN_EDGES)[0]
                depth_hist[f"fp{int(thr)}"] += np.histogram(fp_height, DEPTH_BIN_EDGES)[0]

            for b in budgets:
                pc = p + np.clip(gap, -b, b)
                for j, thr in enumerate(THRESHOLDS):
                    pb, tb = pc > thr, t > thr
                    for lead in range(n_leads):
                        pbl, tbl = pb[lead], tb[lead]
                        orac[b]["tp"][j, lead] += np.sum(pbl & tbl)
                        orac[b]["fp"][j, lead] += np.sum(pbl & ~tbl)
                        orac[b]["fn"][j, lead] += np.sum(~pbl & tbl)

    _, base_per_thr, base_m = csi_published(base["tp"], base["fp"], base["fn"])
    out = {
        "input": args.input,
        "member_index": args.member_index,
        "n_events": int(n),
        "baseline": {
            "csi_m": base_m,
            "per_threshold": dict(zip([str(int(t)) for t in THRESHOLDS], base_per_thr.tolist())),
        },
        "oracle": {},
        "error_depth": {},
    }
    for b in budgets:
        _, per_thr, m = csi_published(orac[b]["tp"], orac[b]["fp"], orac[b]["fn"])
        out["oracle"][str(b)] = {
            "csi_m": m,
            "delta_csi_m": m - base_m,
            "per_threshold": dict(zip([str(int(t)) for t in THRESHOLDS], per_thr.tolist())),
        }
    centers = 0.5 * (DEPTH_BIN_EDGES[:-1] + DEPTH_BIN_EDGES[1:])
    for key, hist in depth_hist.items():
        tot = hist.sum()
        if tot == 0:
            out["error_depth"][key] = {"total_px": 0}
            continue
        cdf = np.cumsum(hist) / tot
        frac_within = {
            str(b): float(cdf[np.searchsorted(DEPTH_BIN_EDGES[1:], b)])
            for b in (1, 2, 3, 5, 8)
        }
        quantiles = {
            f"q{q}": float(centers[np.searchsorted(cdf, q / 100.0)])
            for q in (50, 75, 90, 95)
        }
        out["error_depth"][key] = {
            "total_px": float(tot),
            "frac_within_b": frac_within,
            "depth_quantiles_dbz": quantiles,
        }

    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
