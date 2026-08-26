"""Score gate arms chunk-by-chunk with paired, per-event statistics.

Built for the gated-rollout dose-response probe and A/B.  Three things it does
that a plain metric dump does not:

1.  **Pairing verification.**  The gate only rewrites the *condition* for
    chunk 2, so chunk 1 (leads 0..input_length-1) must be identical across
    every arm.  If it is not, the arms are not paired and no comparison is
    valid; this is checked first and reported as max |delta|.
2.  **Chunk-resolved scores.**  Chunk-1 numbers are the null channel (they
    cannot move); chunk-2 numbers are where any effect must appear.  Pooling
    both, as a 10-lead average would, dilutes the effect by more than half.
3.  **Per-event sufficient statistics.**  TP/FP/FN, FSS numerator/denominator
    and CRPS sums are kept per event so a later event-cluster bootstrap can
    resample events and only then form ratios (forming CSI first and averaging
    is a different statistic).

Usage:

    python tools/score_gate_arms.py \
        --arms plain=...plain.h5 a0665=...a0665.h5 graded=...graded.h5 \
        --reference plain --input-length 5 \
        --output-dir audit_outputs/gate_dose_probe/scores
"""

import argparse
import json
import os
import sys

import h5py
import numpy as np

sys.path.append(os.getcwd())

from common.metrics.ensemble_probabilistic import crps_empirical_fair

THRESHOLDS = (20.0, 30.0, 35.0, 40.0)
FSS_SCALES = (2, 4, 8, 16, 32)


def box_mean(field: np.ndarray, scale: int) -> np.ndarray:
    """Uniform box filter via summed-area table; matches pysteps' FSS window."""
    if scale <= 1:
        return field
    pad = scale // 2
    padded = np.pad(field, ((0, 0), (pad, pad), (pad, pad)), mode="constant")
    csum = padded.cumsum(axis=1).cumsum(axis=2)
    csum = np.pad(csum, ((0, 0), (1, 0), (1, 0)), mode="constant")
    h, w = field.shape[-2:]
    out = (
        csum[:, scale:scale + h, scale:scale + w]
        - csum[:, 0:h, scale:scale + w]
        - csum[:, scale:scale + h, 0:w]
        + csum[:, 0:h, 0:w]
    )
    return out / float(scale * scale)


def score_event(members: np.ndarray, truth: np.ndarray) -> dict:
    """Per-event sufficient statistics on one lead window.

    members ``(M, T, H, W)``, truth ``(T, H, W)``, metric scale (dBZ).
    """
    ens_mean = members.mean(axis=0)
    stats = {}

    crps = crps_empirical_fair(truth, members, member_axis=0)
    for key in ("crps_empirical", "crps_fair", "skill_term", "spread_fair"):
        stats[key] = float(np.nanmean(crps[key]))

    stats["mse_mean"] = float(np.mean((ens_mean - truth) ** 2))
    stats["mae_mean"] = float(np.mean(np.abs(ens_mean - truth)))

    for thr in THRESHOLDS:
        # deterministic scores on the ensemble mean, evaluator convention '>='
        pred_hit = ens_mean >= thr
        obs_hit = truth >= thr
        stats[f"tp{int(thr)}"] = float(np.sum(pred_hit & obs_hit))
        stats[f"fp{int(thr)}"] = float(np.sum(pred_hit & ~obs_hit))
        stats[f"fn{int(thr)}"] = float(np.sum(~pred_hit & obs_hit))
        # member-0 sharpness reference: area fraction above threshold
        stats[f"area_pred{int(thr)}"] = float(np.mean(pred_hit))
        stats[f"area_obs{int(thr)}"] = float(np.mean(obs_hit))
        stats[f"area_member{int(thr)}"] = float(np.mean(members >= thr))

    for thr in (30.0,):
        pf = (ens_mean >= thr).astype(np.float64)
        of = (truth >= thr).astype(np.float64)
        for scale in FSS_SCALES:
            pm, om = box_mean(pf, scale), box_mean(of, scale)
            stats[f"fss_num_s{scale}"] = float(np.sum((pm - om) ** 2))
            stats[f"fss_den_s{scale}"] = float(np.sum(pm**2 + om**2))
    return stats


def aggregate(rows: list) -> dict:
    """Form ratios only after summing sufficient statistics over events."""
    keys = rows[0].keys()
    total = {k: float(np.sum([r[k] for r in rows])) for k in keys}
    mean = {k: float(np.mean([r[k] for r in rows])) for k in keys}
    out = {
        "n_events": len(rows),
        "crps_empirical": mean["crps_empirical"],
        "crps_fair": mean["crps_fair"],
        "skill_term": mean["skill_term"],
        "spread_fair": mean["spread_fair"],
        "mse_mean": mean["mse_mean"],
        "mae_mean": mean["mae_mean"],
        "spread_skill_ratio": mean["spread_fair"] / max(mean["skill_term"], 1e-12),
    }
    for thr in THRESHOLDS:
        t = int(thr)
        tp, fp, fn = total[f"tp{t}"], total[f"fp{t}"], total[f"fn{t}"]
        out[f"csi{t}"] = tp / max(tp + fp + fn, 1.0)
        out[f"pod{t}"] = tp / max(tp + fn, 1.0)
        out[f"far{t}"] = fp / max(tp + fp, 1.0)
        out[f"bias{t}"] = (tp + fp) / max(tp + fn, 1.0)
        out[f"area_pred{t}"] = mean[f"area_pred{t}"]
        out[f"area_obs{t}"] = mean[f"area_obs{t}"]
        out[f"area_member{t}"] = mean[f"area_member{t}"]
    for scale in FSS_SCALES:
        num, den = total[f"fss_num_s{scale}"], total[f"fss_den_s{scale}"]
        out[f"fss30_s{scale}"] = 1.0 - num / max(den, 1e-12)
    return out


def paired_bootstrap(rows_a, rows_b, key, iterations=2000, seed=42):
    """Event-cluster bootstrap CI for the per-event mean difference a - b."""
    a = np.array([r[key] for r in rows_a], dtype=np.float64)
    b = np.array([r[key] for r in rows_b], dtype=np.float64)
    diff = a - b
    rng = np.random.default_rng(seed)
    stats = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(iterations)]
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return float(diff.mean()), float(lo), float(hi)


def paired_bootstrap_ratio(rows_a, rows_b, thr, kind, iterations=2000, seed=42):
    """Event-cluster bootstrap CI for a ratio-of-sums difference (a - b).

    CSI and bias are ratios of SUMMED tp/fp/fn, so the resample must draw
    event indices once per iteration, apply them to BOTH arms (paired), sum
    the components, and only then form the ratio.  Forming per-event CSI
    first and averaging is a different statistic -- the same trap the
    verifier-gate work hit with rank correlations vs realized pooled gain.
    """
    t = int(thr)

    def arrs(rows):
        return (np.array([r[f"tp{t}"] for r in rows], dtype=np.float64),
                np.array([r[f"fp{t}"] for r in rows], dtype=np.float64),
                np.array([r[f"fn{t}"] for r in rows], dtype=np.float64))

    ta, fa, na = arrs(rows_a)
    tb, fb, nb = arrs(rows_b)

    def stat(tp, fp, fn):
        if kind == "csi":
            return tp.sum() / max(tp.sum() + fp.sum() + fn.sum(), 1.0)
        if kind == "bias":
            return (tp.sum() + fp.sum()) / max(tp.sum() + fn.sum(), 1.0)
        raise ValueError(f"unknown ratio kind {kind!r}")

    full = stat(ta, fa, na) - stat(tb, fb, nb)
    rng = np.random.default_rng(seed)
    n = len(ta)
    draws = np.empty(iterations)
    for i in range(iterations):
        idx = rng.integers(0, n, n)
        draws[i] = stat(ta[idx], fa[idx], na[idx]) - stat(tb[idx], fb[idx], nb[idx])
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(full), float(lo), float(hi)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", required=True, help="name=path.h5")
    parser.add_argument("--reference", required=True)
    parser.add_argument("--input-length", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    arms = {}
    for spec in args.arms:
        name, path = spec.split("=", 1)
        arms[name] = path
    if args.reference not in arms:
        raise ValueError(f"reference {args.reference} not among arms")

    chunk = args.input_length
    per_event = {}
    chunk1_hash = {}
    ref_chunk1 = None

    for name, path in arms.items():
        with h5py.File(path, "r") as handle:
            preds, truth = handle["predictions"], handle["truth"]
            n = preds.shape[0]
            rows_c1, rows_c2 = [], []
            c1_ref_block = None
            for i in range(n):
                m = np.asarray(preds[i], dtype=np.float32)
                t = np.asarray(truth[i], dtype=np.float32)
                rows_c1.append(score_event(m[:, :chunk], t[:chunk]))
                rows_c2.append(score_event(m[:, chunk:], t[chunk:]))
                if i < 4:
                    if c1_ref_block is None:
                        c1_ref_block = []
                    c1_ref_block.append(m[:, :chunk].copy())
            per_event[name] = {"chunk1": rows_c1, "chunk2": rows_c2}
            chunk1_hash[name] = np.concatenate(c1_ref_block, axis=0)
            print(f"scored {name}: {n} events", flush=True)

    # ---- pairing verification on chunk 1 ----
    ref_block = chunk1_hash[args.reference]
    pairing = {}
    for name, block in chunk1_hash.items():
        pairing[name] = float(np.max(np.abs(block - ref_block)))
    print("\n=== pairing check: max |chunk1 - reference chunk1| (must be 0) ===")
    for name, delta in pairing.items():
        print(f"  {name:10s} {delta:.6g}")

    # ---- report ----
    report = {"pairing_max_abs_chunk1_delta": pairing, "arms": {}}
    for name in arms:
        report["arms"][name] = {
            "chunk1": aggregate(per_event[name]["chunk1"]),
            "chunk2": aggregate(per_event[name]["chunk2"]),
        }
    ref_rows = per_event[args.reference]["chunk2"]
    keys = ["crps_fair", "crps_empirical", "mse_mean", "spread_fair", "skill_term"]
    report["paired_vs_reference_chunk2"] = {}
    for name in arms:
        if name == args.reference:
            continue
        report["paired_vs_reference_chunk2"][name] = {
            k: dict(zip(("delta", "ci_low", "ci_high"),
                        paired_bootstrap(per_event[name]["chunk2"], ref_rows, k)))
            for k in keys
        }
        ratio_cis = {}
        for t in (30, 35, 40):
            ratio_cis[f"csi{t}"] = paired_bootstrap_ratio(
                per_event[name]["chunk2"], ref_rows, t, "csi")
        for t in (35, 40):
            ratio_cis[f"bias{t}"] = paired_bootstrap_ratio(
                per_event[name]["chunk2"], ref_rows, t, "bias")
        report["paired_vs_reference_chunk2"][name].update({
            k: dict(zip(("delta", "ci_low", "ci_high"), v))
            for k, v in ratio_cis.items()
        })

    with open(os.path.join(args.output_dir, "scores.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print("\n=== chunk 2 (leads %d+) ===" % chunk)
    hdr = ("arm", "crps_fair", "csi30", "csi35", "csi40", "fss30_s8", "mse", "ssr", "area35")
    print("%-9s %10s %8s %8s %8s %9s %8s %7s %8s" % hdr)
    for name in arms:
        a = report["arms"][name]["chunk2"]
        print("%-9s %10.4f %8.4f %8.4f %8.4f %9.4f %8.2f %7.3f %8.5f" % (
            name, a["crps_fair"], a["csi30"], a["csi35"], a["csi40"],
            a["fss30_s8"], a["mse_mean"], a["spread_skill_ratio"], a["area_pred35"]))
    print("\n=== chunk 1 (null channel, must be identical) ===")
    for name in arms:
        a = report["arms"][name]["chunk1"]
        print("%-9s crps_fair=%.4f csi35=%.4f" % (name, a["crps_fair"], a["csi35"]))

    print("\n=== paired ratio CIs vs %s (chunk2, event-cluster bootstrap) ===" % args.reference)
    ci_keys = ("csi30", "csi35", "csi40", "bias35", "bias40")
    print("%-16s" % "arm" + "".join("%26s" % k for k in ci_keys))
    for name in arms:
        if name == args.reference:
            continue
        row = report["paired_vs_reference_chunk2"][name]
        cells = ""
        for k in ci_keys:
            c = row[k]
            cells += "  %+.4f[%+.4f,%+.4f]" % (c["delta"], c["ci_low"], c["ci_high"])
        print("%-16s%s" % (name, cells))
    print("\nreport: %s" % os.path.join(args.output_dir, "scores.json"))


if __name__ == "__main__":
    main()
