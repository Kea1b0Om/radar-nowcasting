"""E2b lift probe: does predicted FN/FP risk clear the CSI break-even precision
at TRUE base rates, restricted to the bounded-residual-reachable set?

Why this exists: E1 measured AUC on per-bin balanced samples — rank skill, not
deployable precision.  But the CSI contingency algebra fixes hard break-even
lines for a corrector acting on single pixels (pooled counts, D = TP+FP+FN):

  * boosting a predicted-FN pixel:  correct (FN->TP) gains ~1/D,
    wrong (TN->FP) loses ~TP/D^2  =>  EV > 0  iff  precision > CSI/(1+CSI)
    (~0.19 at CSI40, ~0.22 at CSI35) — miss-fixing is 1/CSI-times forgiving;
  * killing a predicted-FP pixel:  correct gains ~TP/D^2, wrong (TP->FN)
    loses ~1/D  =>  EV > 0  iff  precision > 1/(1+CSI)  (~0.81) — false-alarm
    suppression is brutally unforgiving at low-CSI thresholds.

So the deployable question is: at true base rates, does the top-k of the
learned risk score reach precision above the break-even line, inside the set
the bounded head can actually move (depth <= b)?  This is the last zero-GPU
gate before E3 (training the real refiner).

Fit on even dump rows (same sampling spirit as E1), evaluate on odd rows over
ALL candidate pixels (no subsampling), so precision@k is at deployment base
rate.  Reports, per task and model: base rate, precision/recall at top-k
fractions, break-even precision, and a pooled-CSI delta estimate per k.

Usage:
    python tools/e2_lift_probe.py \
        --dump audit_outputs/distill/test_s8/qw_t80.h5 \
        --data datasets/cikm/data/cikm_full/nowcast_testing_full.h5 \
        --output audit_outputs/e2_lift_probe_qw_t80.json \
        [--fit-events 1500] [--eval-events 400]
"""

import argparse
import json

import h5py
import numpy as np

from e1_risk_probe import (
    event_features,
    fit_logistic,
    fit_mlp,
    load_dataset_event,
)

# task -> (theta, kind, reachable depth cap in dBZ)
TASKS = {
    "fn40_b8": (40.0, "fn", 8.0),
    "fn40_b5": (40.0, "fn", 5.0),
    "fn35_b8": (35.0, "fn", 8.0),
    "fp40_b5": (40.0, "fp", 5.0),
}
TOP_FRACS = (0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.25)
PER_EVENT = 120  # positives (and negatives) sampled per event per task at fit time


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dump", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--fit-events", type=int, default=1500)
    p.add_argument("--eval-events", type=int, default=400)
    p.add_argument("--seed", type=int, default=0)
    return p.parse_args()


def task_fields(planes, members, truth, theta, kind):
    """Return (feats(T,H,W,12), candidate mask, label mask, depth)."""
    zhat = planes[0]
    dist = zhat - theta
    exc = (members > theta).mean(axis=0)
    feats = np.stack([zhat, dist, exc] + planes[3:], axis=-1)
    pred_pos = zhat > theta
    true_pos = truth > theta
    if kind == "fn":
        return feats, ~pred_pos, true_pos, theta - zhat
    return feats, pred_pos, ~true_pos, zhat - theta


def main():
    args = parse_args()
    rng = np.random.default_rng(args.seed)
    fit_rows = {k: [] for k in TASKS}
    eval_scores = {k: {"y": []} for k in TASKS}
    counts = {t: {"tp": 0.0, "fp": 0.0, "fn": 0.0} for t in (35.0, 40.0)}

    with h5py.File(args.dump, "r") as dump, h5py.File(args.data, "r") as data:
        preds, truth_ds = dump["predictions"], dump["truth"]
        event_index = np.asarray(dump["event_index"]) if "event_index" in dump else None
        vil = data["vil"]
        n_all = preds.shape[0]
        even = [i for i in range(n_all) if i % 2 == 0][: args.fit_events]
        odd = [i for i in range(n_all) if i % 2 == 1][: args.eval_events]

        # ---- fit-side sampling ----
        for c, i in enumerate(even):
            ds_idx = int(event_index[i]) if event_index is not None else i
            members = np.asarray(preds[i], dtype=np.float32)
            truth = np.asarray(truth_ds[i], dtype=np.float32)
            frames = load_dataset_event(vil, ds_idx)
            planes = event_features(members, frames)
            for key, (theta, kind, cap) in TASKS.items():
                feats, cand, lab, depth = task_fields(planes, members, truth, theta, kind)
                in_set = cand & (depth > 0) & (depth <= cap)
                flat_f = feats.reshape(-1, feats.shape[-1])
                for want in (True, False):
                    idx = np.flatnonzero((in_set & (lab == want)).ravel())
                    if idx.size == 0:
                        continue
                    if idx.size > PER_EVENT:
                        idx = rng.choice(idx, PER_EVENT, replace=False)
                    fit_rows[key].append(
                        (flat_f[idx].astype(np.float32),
                         np.full(len(idx), float(want), dtype=np.float32))
                    )
            if (c + 1) % 300 == 0:
                print(f"fit event {c + 1}/{len(even)}", flush=True)

        models = {}
        norms = {}
        for key in TASKS:
            x = np.concatenate([r[0] for r in fit_rows[key]])
            y = np.concatenate([r[1] for r in fit_rows[key]])
            mu, sd = x.mean(axis=0), x.std(axis=0) + 1e-6
            xs = (x - mu) / sd
            models[key] = {
                "logit": fit_logistic(xs, y),
                "mlp": fit_mlp(xs, y, seed=args.seed),
            }
            norms[key] = (mu, sd)
            eval_scores[key].update({"logit": [], "mlp": []})
            print(f"fitted {key}: n={len(y)} pos_frac={y.mean():.3f}", flush=True)
        del fit_rows

        # ---- eval side: all candidate pixels, true base rate ----
        for c, i in enumerate(odd):
            ds_idx = int(event_index[i]) if event_index is not None else i
            members = np.asarray(preds[i], dtype=np.float32)
            truth = np.asarray(truth_ds[i], dtype=np.float32)
            frames = load_dataset_event(vil, ds_idx)
            planes = event_features(members, frames)
            for theta in (35.0, 40.0):
                pp, tp_ = planes[0] > theta, truth > theta
                counts[theta]["tp"] += float(np.sum(pp & tp_))
                counts[theta]["fp"] += float(np.sum(pp & ~tp_))
                counts[theta]["fn"] += float(np.sum(~pp & tp_))
            for key, (theta, kind, cap) in TASKS.items():
                feats, cand, lab, depth = task_fields(planes, members, truth, theta, kind)
                sel = (cand & (depth > 0) & (depth <= cap)).ravel()
                if not sel.any():
                    continue
                mu, sd = norms[key]
                f = (feats.reshape(-1, feats.shape[-1])[sel] - mu) / sd
                f = f.astype(np.float32)
                eval_scores[key]["y"].append(lab.ravel()[sel])
                for name in ("logit", "mlp"):
                    eval_scores[key][name].append(
                        models[key][name](f).astype(np.float32)
                    )
            if (c + 1) % 100 == 0:
                print(f"eval event {c + 1}/{len(odd)}", flush=True)

    out = {"dump": args.dump, "fit_events": len(even), "eval_events": len(odd),
           "pooled_baseline": {}, "tasks": {}}
    csi_pooled = {}
    for theta, c in counts.items():
        d = c["tp"] + c["fp"] + c["fn"]
        csi_pooled[theta] = c["tp"] / d if d else float("nan")
        out["pooled_baseline"][str(int(theta))] = {
            **c, "csi_pooled": csi_pooled[theta], "denominator": d,
        }

    for key, (theta, kind, cap) in TASKS.items():
        y = np.concatenate(eval_scores[key]["y"]).astype(np.float64)
        n = len(y)
        csi = csi_pooled[theta]
        break_even = csi / (1 + csi) if kind == "fn" else 1 / (1 + csi)
        entry = {
            "theta": theta, "kind": kind, "depth_cap": cap,
            "n_candidates": int(n), "n_pos": int(y.sum()),
            "base_rate": float(y.mean()),
            "break_even_precision": break_even,
            "models": {},
        }
        d_pool = out["pooled_baseline"][str(int(theta))]["denominator"]
        for name in ("logit", "mlp"):
            s = np.concatenate(eval_scores[key][name])
            order = np.argsort(-s)
            y_sorted = y[order]
            cum_pos = np.cumsum(y_sorted)
            curve = {}
            for frac in TOP_FRACS:
                k = max(1, int(n * frac))
                p_k = float(cum_pos[k - 1] / k)
                if kind == "fn":
                    ev = (p_k * 1.0 - (1 - p_k) * csi) * k / d_pool
                else:
                    ev = (p_k * csi - (1 - p_k) * 1.0) * k / d_pool
                curve[f"top{frac}"] = {
                    "k": k, "precision": p_k,
                    "recall": float(cum_pos[k - 1] / max(y.sum(), 1)),
                    "clears_break_even": bool(p_k > break_even),
                    "pooled_csi_delta_est": float(ev),
                }
            entry["models"][name] = curve
        out["tasks"][key] = entry

    # headline gate: any FN task whose top-2% precision clears break-even
    gate = {}
    for key, entry in out["tasks"].items():
        if entry["kind"] != "fn":
            continue
        best = max(
            entry["models"][m]["top0.02"]["precision"] for m in ("logit", "mlp")
        )
        gate[key] = {
            "top2pct_precision": best,
            "break_even": entry["break_even_precision"],
            "pass": bool(best > entry["break_even_precision"]),
        }
    out["endpoint"] = gate

    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(gate, indent=2))
    print(f"written: {args.output}")


if __name__ == "__main__":
    main()
