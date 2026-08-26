"""Segmentation-theoretic diagnostics for nowcasting ensembles (read-only).

Three measurements from the segmentation-to-CSI transfer map, all on frozen
dump h5 files, no retraining:

1.  **Best-member IoU (HM-IoU with a single GT) + GED.**  Mean CSI of an
    ensemble penalises diversity; best-member IoU asks whether the ensemble
    *contains* the truth.  With one ground truth the Hungarian matching
    degenerates to a max over members.  GED = 2*E d(m, y) - E d(m, m')
    with d = 1 - IoU separates accuracy from diversity.  Pre-registered
    expectation for this model: spread/skill ~0.04, so best-member ~= mean
    member and the diversity term ~= 0 -- the figure IS the collapse.

2.  **Panoptic-style object decomposition (PQ = SQ x RQ).**  CSI charges a
    2-px-displaced but otherwise perfect storm cell twice (miss + false
    alarm); PQ books it as RQ = 1 (detected) with SQ slightly below 1.
    Matching = connected components with IoU > 0.5 (unique by the panoptic
    theorem).  The SQ/RQ split quantifies how much of the CSI gap is
    "did not detect" vs "detected but displaced/misshapen".

3.  **Fragmentation.**  CSI is blind to connectivity: a rain band predicted
    as 20 shards can score identically to an intact one.  Connected-component
    counts (min size filter against speckle) per threshold, pred vs obs.

Pooling: per-(event, lead) sufficient statistics, summed before ratios --
same discipline as score_gate_arms.  Lead window = chunk2 (leads
input_length..end), where effects must live.
"""

import argparse
import json
import os

import h5py
import numpy as np
from scipy import ndimage

MIN_COMPONENT_PX = 4  # speckle filter for component counts and PQ instances


def binary_components(field: np.ndarray):
    """Labelled components (8-connectivity) with the speckle filter applied."""
    lab, n = ndimage.label(field, structure=np.ones((3, 3), dtype=int))
    if n == 0:
        return lab, 0
    sizes = np.bincount(lab.ravel())
    kill = np.flatnonzero(sizes < MIN_COMPONENT_PX)
    if kill.size:
        mask = np.isin(lab, kill)
        lab[mask] = 0
        keep = np.flatnonzero((sizes >= MIN_COMPONENT_PX))
        keep = keep[keep != 0]
        for new, old in enumerate(keep, start=1):
            lab[lab == old] = new
        n = len(keep)
    return lab, n


def panoptic_stats(pred_bin: np.ndarray, obs_bin: np.ndarray):
    """PQ sufficient statistics for one 2D field pair.

    Components with pairwise IoU > 0.5 match (unique, Kirillov et al. 2019).
    Returns (iou_sum_of_matches, n_tp, n_fp, n_fn).
    """
    plab, np_ = binary_components(pred_bin)
    olab, no_ = binary_components(obs_bin)
    if np_ == 0 and no_ == 0:
        return 0.0, 0, 0, 0
    matched_p, matched_o, iou_sum = set(), set(), 0.0
    if np_ and no_:
        # joint histogram of component overlaps
        joint = {}
        both = (plab > 0) & (olab > 0)
        for pi, oi in zip(plab[both].ravel(), olab[both].ravel()):
            joint[(pi, oi)] = joint.get((pi, oi), 0) + 1
        psz = np.bincount(plab.ravel())
        osz = np.bincount(olab.ravel())
        for (pi, oi), inter in joint.items():
            union = psz[pi] + osz[oi] - inter
            iou = inter / union
            if iou > 0.5:
                matched_p.add(pi)
                matched_o.add(oi)
                iou_sum += iou
    return iou_sum, len(matched_p), np_ - len(matched_p), no_ - len(matched_o)


def iou_pair(a: np.ndarray, b: np.ndarray):
    inter = float(np.sum(a & b))
    union = float(np.sum(a | b))
    return (inter / union) if union > 0 else None


def score_arm(path: str, chunk: int, thresholds, max_events=None):
    acc = {t: {"iou_mean_field": [], "iou_member_mean": [], "iou_best_member": [],
               "ged_acc_term": [], "ged_div_term": [],
               "pq_iou_sum": 0.0, "pq_tp": 0, "pq_fp": 0, "pq_fn": 0,
               "ncomp_pred": 0, "ncomp_obs": 0, "n_samples": 0}
           for t in thresholds}
    with h5py.File(path, "r") as handle:
        preds, truth = handle["predictions"], handle["truth"]
        n = preds.shape[0] if max_events is None else min(preds.shape[0], max_events)
        for i in range(n):
            m = np.asarray(preds[i], dtype=np.float32)[:, chunk:]   # (M, T2, H, W)
            y = np.asarray(truth[i], dtype=np.float32)[chunk:]      # (T2, H, W)
            mean_f = m.mean(axis=0)
            for t in thresholds:
                a = acc[t]
                mb = m >= t                                          # (M, T2, H, W)
                ob = y >= t
                pb = mean_f >= t
                for lead in range(y.shape[0]):
                    o = ob[lead]
                    p = pb[lead]
                    # -- pixel IoU family (only where union > 0)
                    i_mean = iou_pair(p, o)
                    if i_mean is not None:
                        a["iou_mean_field"].append(i_mean)
                    member_ious = [iou_pair(mb[k, lead], o) for k in range(m.shape[0])]
                    member_ious = [v for v in member_ious if v is not None]
                    if member_ious:
                        a["iou_member_mean"].append(float(np.mean(member_ious)))
                        a["iou_best_member"].append(float(np.max(member_ious)))
                    # -- GED with d = 1 - IoU (define d = 0 when both empty)
                    M = m.shape[0]
                    d_acc = []
                    for k in range(M):
                        v = iou_pair(mb[k, lead], o)
                        d_acc.append(0.0 if v is None else 1.0 - v)
                    d_div = []
                    for k in range(M):
                        for j in range(k + 1, M):
                            v = iou_pair(mb[k, lead], mb[j, lead])
                            d_div.append(0.0 if v is None else 1.0 - v)
                    a["ged_acc_term"].append(float(np.mean(d_acc)))
                    a["ged_div_term"].append(float(np.mean(d_div)) if d_div else 0.0)
                    # -- panoptic + fragmentation on the deployed (mean) field
                    iou_sum, tp, fp, fn = panoptic_stats(p, o)
                    a["pq_iou_sum"] += iou_sum
                    a["pq_tp"] += tp
                    a["pq_fp"] += fp
                    a["pq_fn"] += fn
                    _, ncp = binary_components(p)
                    _, nco = binary_components(o)
                    a["ncomp_pred"] += ncp
                    a["ncomp_obs"] += nco
                    a["n_samples"] += 1
            if (i + 1) % 500 == 0:
                print(f"  {os.path.basename(path)}: {i + 1}/{n} events", flush=True)
    out = {}
    for t in thresholds:
        a = acc[t]
        tp, fp, fn = a["pq_tp"], a["pq_fp"], a["pq_fn"]
        sq = a["pq_iou_sum"] / tp if tp else 0.0
        rq = tp / (tp + 0.5 * fp + 0.5 * fn) if (tp + fp + fn) else 0.0
        ged_acc = float(np.mean(a["ged_acc_term"]))
        ged_div = float(np.mean(a["ged_div_term"]))
        out[f"t{int(t)}"] = {
            "iou_mean_field": float(np.mean(a["iou_mean_field"])),
            "iou_member_mean": float(np.mean(a["iou_member_mean"])),
            "iou_best_member": float(np.mean(a["iou_best_member"])),
            "ged_sq": 2.0 * ged_acc - ged_div,
            "ged_acc_term": ged_acc,
            "ged_div_term": ged_div,
            "pq": sq * rq, "sq": sq, "rq": rq,
            "pq_tp": tp, "pq_fp": fp, "pq_fn": fn,
            "frag_ratio": a["ncomp_pred"] / max(a["ncomp_obs"], 1),
            "ncomp_pred_per_frame": a["ncomp_pred"] / max(a["n_samples"], 1),
            "ncomp_obs_per_frame": a["ncomp_obs"] / max(a["n_samples"], 1),
        }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arms", nargs="+", required=True, help="name=path.h5")
    ap.add_argument("--input-length", type=int, default=5)
    ap.add_argument("--thresholds", type=float, nargs="+", default=(30.0, 35.0, 40.0))
    ap.add_argument("--max-events", type=int, default=None)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    report = {}
    for spec in args.arms:
        name, path = spec.split("=", 1)
        print(f"scoring {name} ...", flush=True)
        report[name] = score_arm(path, args.input_length, tuple(args.thresholds),
                                 args.max_events)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    for t in args.thresholds:
        key = f"t{int(t)}"
        print(f"\n=== threshold {int(t)} dBZ (chunk2, pooled) ===")
        hdr = ("arm", "IoU_mean", "IoU_membermean", "IoU_best", "GED", "div_term",
               "PQ", "SQ", "RQ", "frag")
        print("%-13s%9s%15s%9s%8s%9s%7s%7s%7s%7s" % hdr)
        for name, r in report.items():
            a = r[key]
            print("%-13s%9.4f%15.4f%9.4f%8.4f%9.4f%7.4f%7.4f%7.4f%7.2f" % (
                name, a["iou_mean_field"], a["iou_member_mean"],
                a["iou_best_member"], a["ged_sq"], a["ged_div_term"],
                a["pq"], a["sq"], a["rq"], a["frag_ratio"]))
    print(f"\nwrote {args.output}")


if __name__ == "__main__":
    main()
