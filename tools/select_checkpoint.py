"""Step 1c: apply the frozen selector to the event-level dumps.  No GPU.

Reads the dumps written by ``score_checkpoints.py``, verifies that every one
of them was produced under the frozen rule, then applies the lexicographic
selector:

    1. max S_balanced on dev
    2. among candidates within epsilon of the best, max micro CSI-M on dev
    3. tie-break on fair CRPS, then MSE

``epsilon`` is not chosen after looking at the ranking: the rule fixes it as
one stratified event-level bootstrap standard error of S_balanced on dev
(B and seed also fixed in the rule).

Everything else printed here is diagnostics, not part of the decision:
shadow-split scores (touched once, to see whether the dev choice transfers),
per-stratum breakdowns, sensitivity to the stratum weighting, and a paired
bootstrap of the winner against a named incumbent.

Example
-------
    python tools/select_checkpoint.py \
        --rule artifacts/cikm/selection/selection_rule.json \
        --dumps 'artifacts/cikm/selection/dumps/stage1__*.npz' \
        --incumbent v4_early_stopping \
        --report artifacts/cikm/selection/stage1_report.md
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Dict, List

import numpy as np

sys.path.append(os.getcwd())

from tools.selection_rule import (  # noqa: E402
    SelectionRule,
    balanced_score,
    bootstrap_balanced,
    bootstrap_multiplicities,
    csi_grid,
    epsilon_from_bootstrap,
    official_csi_m,
)

PROTOCOL_KEYS = (
    "samples", "batch_size", "euler_steps", "num_train_timesteps",
    "base_seed", "seed_formula", "thresholds", "pixel_scale", "crop",
    "pool_size", "dtype", "n_events",
)


class Dump:
    def __init__(self, npz_path: str):
        self.npz_path = npz_path
        self.tag = os.path.basename(npz_path).replace(".npz", "")
        with open(npz_path.replace(".npz", ".json")) as f:
            self.manifest = json.load(f)
        d = np.load(npz_path)
        self.tp = d["tp"]; self.fn = d["fn"]; self.fp = d["fp"]; self.tn = d["tn"]
        self.tp_pool = d["tp_pool"]; self.fn_pool = d["fn_pool"]
        self.fp_pool = d["fp_pool"]
        self.sse = d["sse"]; self.npix = d["npix"]
        self.crps_sum = d["crps_sum"]; self.spread_sum = d["spread_sum"]
        self.severity_check = d["severity_check"]

    @property
    def name(self) -> str:
        return os.path.splitext(os.path.basename(self.manifest["checkpoint_path"]))[0]

    def mse(self, mask: np.ndarray) -> float:
        return float(self.sse[mask].sum() / self.npix[mask].sum())

    def crps(self, mask: np.ndarray) -> float:
        return float(self.crps_sum[mask].sum() / self.npix[mask].sum())

    def spread(self, mask: np.ndarray) -> float:
        return float(self.spread_sum[mask].sum() / self.npix[mask].sum())


def verify(dumps: List[Dump], rule: SelectionRule) -> None:
    """Refuse to compare dumps that are not on the same protocol."""
    rule_hash = rule.payload_hash()
    ref = dumps[0].manifest
    for d in dumps:
        m = d.manifest
        if m.get("rule_sha256") != rule_hash:
            raise SystemExit(
                f"{d.tag}: produced under a different selection rule "
                f"({str(m.get('rule_sha256'))[:12]}... vs {rule_hash[:12]}...)"
            )
        for k in PROTOCOL_KEYS:
            if m.get(k) != ref.get(k):
                raise SystemExit(
                    f"{d.tag}: protocol key '{k}' differs from {dumps[0].tag} "
                    f"({m.get(k)!r} vs {ref.get(k)!r}).  Common random numbers "
                    f"and paired comparison are only valid when these match."
                )
    kinds = {d.manifest["checkpoint_type"] for d in dumps}
    if len(kinds) > 1:
        raise SystemExit(f"mixed checkpoint types in one selection: {kinds}")

    sev_rule = np.asarray(rule.val_severity, dtype=np.float64)
    for d in dumps:
        if len(d.severity_check) != len(sev_rule):
            raise SystemExit(f"{d.tag}: event count differs from the rule")
        drift = np.abs(d.severity_check - sev_rule).max()
        if drift > 1e-4:
            raise SystemExit(
                f"{d.tag}: recomputed severity differs from the frozen rule by "
                f"{drift:.2e} -- the dump was scored against different data, a "
                f"different crop, or a different scale."
            )


def evaluate(d: Dump, rule: SelectionRule, mask: np.ndarray) -> dict:
    strata = rule.strata
    s_bal, per_k, n_empty = balanced_score(d.tp, d.fn, d.fp, strata, mask)
    grid = csi_grid(d.tp[mask].sum(0), d.fn[mask].sum(0), d.fp[mask].sum(0))
    return {
        "balanced": s_bal,
        "per_stratum": per_k,
        "n_empty_cells": n_empty,
        "micro_csi_m": official_csi_m(d.tp, d.fn, d.fp, mask),
        "micro_csi_pool_m": official_csi_m(d.tp_pool, d.fn_pool, d.fp_pool, mask),
        "csi_per_threshold": {
            float(t): float(np.nanmean(grid[:, i]))
            for i, t in enumerate(rule.thresholds)
        },
        "csi_per_lead": [float(np.nanmean(grid[t])) for t in range(grid.shape[0])],
        "mse": d.mse(mask),
        "fair_crps": d.crps(mask),
        "spread": d.spread(mask),
    }


def select(rows: List[dict], epsilon: float) -> dict:
    """Frozen lexicographic selector."""
    best_bal = max(r["balanced"] for r in rows)
    band = [r for r in rows if r["balanced"] >= best_bal - epsilon]
    band.sort(key=lambda r: (-r["micro_csi_m"], r["fair_crps"], r["mse"]))
    return band[0]


def fmt(x, nd=5):
    return "n/a" if x is None else f"{x:.{nd}f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rule", required=True)
    ap.add_argument("--dumps", required=True, help="glob over stage*.npz")
    ap.add_argument("--incumbent", default=None,
                    help="checkpoint name currently selected by partial_csi_m")
    ap.add_argument("--report", default=None)
    ap.add_argument("--epsilon_n_se", type=float, default=1.0)
    args = ap.parse_args()

    rule = SelectionRule.load(args.rule)
    paths = sorted(glob.glob(args.dumps))
    if not paths:
        raise SystemExit(f"no dumps matched {args.dumps}")
    dumps = [Dump(p) for p in paths]
    verify(dumps, rule)

    dev = rule.event_mask("dev")
    shadow = rule.event_mask("shadow")
    strata = rule.strata
    lines: List[str] = []

    def out(s=""):
        print(s)
        lines.append(s)

    out(f"# Checkpoint reselection (stage {dumps[0].manifest['stage']})")
    out()
    out(f"- rule: `{args.rule}` sha256 `{rule.payload_hash()[:16]}`")
    out(f"- checkpoint type: **{dumps[0].manifest['checkpoint_type']}**, "
        f"S={dumps[0].manifest['samples']}, "
        f"euler_steps={dumps[0].manifest['euler_steps']}, float32")
    out(f"- validation events: {len(strata)}  "
        f"(dev {int(dev.sum())} / shadow {int(shadow.sum())}), "
        f"{rule.n_strata_realised} strata, weights `{rule.stratum_weights}`")
    out(f"- selector: {' > '.join(rule.selector_order)}; "
        f"epsilon = {args.epsilon_n_se} x bootstrap SE "
        f"(B={rule.bootstrap_B}, seed={rule.bootstrap_seed})")
    out()

    dev_rows = []
    for d in dumps:
        r = evaluate(d, rule, dev)
        r["name"] = d.name
        r["tag"] = d.tag
        r["dump"] = d
        r["epoch"] = d.manifest["checkpoint_epoch"]
        r["step"] = d.manifest["checkpoint_global_step"]
        dev_rows.append(r)

    # ---- epsilon from a bootstrap of the current leader ----------------
    idx, W = bootstrap_multiplicities(strata, dev, rule.bootstrap_B,
                                      rule.bootstrap_seed)
    leader = max(dev_rows, key=lambda r: r["balanced"])
    boot_leader = bootstrap_balanced(leader["dump"].tp, leader["dump"].fn,
                                     leader["dump"].fp, strata, idx, W)
    epsilon = epsilon_from_bootstrap(boot_leader, args.epsilon_n_se)
    out(f"Bootstrap SE of S_balanced on dev = {epsilon / max(args.epsilon_n_se, 1e-9):.5f}"
        f"  ->  epsilon = {epsilon:.5f}")
    out()

    # ---- ranking table -------------------------------------------------
    dev_rows.sort(key=lambda r: -r["balanced"])
    out("## dev ranking")
    out()
    out("| # | checkpoint | epoch | step | S_balanced | micro CSI-M | "
        "CSI@40 | fair CRPS | MSE |")
    out("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for i, r in enumerate(dev_rows, 1):
        mark = " **<- incumbent**" if args.incumbent and args.incumbent in r["name"] else ""
        out(f"| {i} | `{r['name']}`{mark} | {r['epoch']} | {r['step']} | "
            f"{fmt(r['balanced'])} | {fmt(r['micro_csi_m'])} | "
            f"{fmt(r['csi_per_threshold'][max(rule.thresholds)])} | "
            f"{fmt(r['fair_crps'], 4)} | {fmt(r['mse'], 3)} |")
    out()

    winner = select(dev_rows, epsilon)
    in_band = [r["name"] for r in dev_rows
               if r["balanced"] >= max(x["balanced"] for x in dev_rows) - epsilon]
    out(f"**Selected: `{winner['name']}`** "
        f"(epoch {winner['epoch']}, step {winner['step']})")
    out(f"- within-epsilon band had {len(in_band)} candidate(s): "
        + ", ".join(f"`{n}`" for n in in_band))
    out()

    # ---- per-stratum breakdown ----------------------------------------
    out("## per-stratum CSI on dev (equal weight across these rows)")
    out()
    ks = sorted(dev_rows[0]["per_stratum"].keys())
    header = "| checkpoint | " + " | ".join(f"stratum {k}" for k in ks) + " |"
    out(header)
    out("|---|" + "---:|" * len(ks))
    for r in dev_rows:
        out(f"| `{r['name']}` | "
            + " | ".join(fmt(r["per_stratum"][k]) for k in ks) + " |")
    out()
    n_per_k = {int(k): int(((strata == k) & dev).sum()) for k in ks}
    out(f"dev events per stratum: {n_per_k}")
    empty = dev_rows[0]["n_empty_cells"]
    if empty:
        out(f"empty (lead, threshold) cells excluded per the frozen policy: {empty}")
    out()

    # ---- concentration check ------------------------------------------
    out("## is the score dominated by a few very wet events?")
    out()
    d0 = dev_rows[0]["dump"]
    for k in ks:
        sel = dev & (strata == k)
        denom = (d0.tp + d0.fn + d0.fp)[sel].sum(axis=(1, 2)).astype(np.float64)
        if denom.sum() <= 0:
            out(f"- stratum {k}: no exceedances at any threshold")
            continue
        share = np.sort(denom)[::-1]
        top1 = share[:max(1, len(share) // 100)].sum() / share.sum()
        top10 = share[:max(1, len(share) // 10)].sum() / share.sum()
        out(f"- stratum {k}: top 1% of events carry {top1:5.1%} of the "
            f"contingency mass, top 10% carry {top10:5.1%}")
    out()

    # ---- sensitivity to the weighting ---------------------------------
    out("## sensitivity: does the winner survive other stratum weights?")
    out()
    train_like = {int(k): float(n_per_k[int(k)]) for k in ks}  # dev frequency
    schemes = {
        "equal (frozen)": None,
        "validation frequency": train_like,
        "high-intensity emphasis (k+1)": {int(k): float(int(k) + 1) for k in ks},
    }
    out("| weighting | best checkpoint | winner's rank |")
    out("|---|---|---:|")
    for label, w in schemes.items():
        scored = []
        for r in dev_rows:
            s, _, _ = balanced_score(r["dump"].tp, r["dump"].fn, r["dump"].fp,
                                     strata, dev, weights=w)
            scored.append((s, r["name"]))
        scored.sort(reverse=True)
        rank = 1 + [n for _, n in scored].index(winner["name"])
        out(f"| {label} | `{scored[0][1]}` | {rank} |")
    out()

    # ---- shadow split ---------------------------------------------------
    out("## shadow split (held out of the selection; read once)")
    out()
    out("| checkpoint | S_balanced (shadow) | micro CSI-M (shadow) |")
    out("|---|---:|---:|")
    shadow_rows = []
    for r in dev_rows:
        sr = evaluate(r["dump"], rule, shadow)
        shadow_rows.append((r["name"], sr))
        out(f"| `{r['name']}` | {fmt(sr['balanced'])} | {fmt(sr['micro_csi_m'])} |")
    best_shadow = max(shadow_rows, key=lambda t: t[1]["balanced"])[0]
    agree = best_shadow == winner["name"]
    out()
    out(f"shadow's own best is `{best_shadow}` -- "
        + ("**agrees** with the dev selection." if agree else
           "**disagrees** with the dev selection.  Treat the dev margin as "
           "noise-dominated and prefer the simpler/earlier checkpoint, or "
           "widen the pool before committing."))
    out()

    # ---- paired bootstrap vs incumbent ---------------------------------
    if args.incumbent:
        inc = next((r for r in dev_rows if args.incumbent in r["name"]), None)
        if inc is None:
            out(f"[warn] incumbent '{args.incumbent}' not found among dumps")
        elif inc["name"] == winner["name"]:
            out("## vs incumbent")
            out()
            out("The frozen selector picks the incumbent: there is no free "
                "gain available from reselection over this pool.")
            out()
        else:
            b_new = bootstrap_balanced(winner["dump"].tp, winner["dump"].fn,
                                       winner["dump"].fp, strata, idx, W)
            b_old = bootstrap_balanced(inc["dump"].tp, inc["dump"].fn,
                                       inc["dump"].fp, strata, idx, W)
            delta = b_new - b_old
            lo, hi = np.percentile(delta, [2.5, 97.5])
            out("## vs incumbent (paired, same resampled events)")
            out()
            out(f"- S_balanced: {fmt(inc['balanced'])} -> {fmt(winner['balanced'])}  "
                f"(delta {winner['balanced'] - inc['balanced']:+.5f}, "
                f"95% CI [{lo:+.5f}, {hi:+.5f}], "
                f"P(delta>0) = {float((delta > 0).mean()):.4f})")
            out(f"- micro CSI-M: {fmt(inc['micro_csi_m'])} -> "
                f"{fmt(winner['micro_csi_m'])} "
                f"({winner['micro_csi_m'] - inc['micro_csi_m']:+.5f})")
            out(f"- fair CRPS: {fmt(inc['fair_crps'], 4)} -> "
                f"{fmt(winner['fair_crps'], 4)}")
            out(f"- MSE: {fmt(inc['mse'], 3)} -> {fmt(winner['mse'], 3)}")
            out()
            out("Per-stratum change (dev):")
            for k in ks:
                out(f"  - stratum {k}: "
                    f"{inc['per_stratum'][k]:.5f} -> {winner['per_stratum'][k]:.5f} "
                    f"({winner['per_stratum'][k] - inc['per_stratum'][k]:+.5f})")
            out()

    out("---")
    out()
    out("These are validation numbers under a new float32 / explicit-generator "
        "protocol.  They are **not** comparable to the legacy full-test figures "
        "which use float16 accumulation on the test split.  "
        "Only the selected checkpoint goes to `test_flowcast.py`, unchanged, "
        "for the number that gets reported.")

    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"\nreport -> {args.report}")

    sel_path = (args.report or "selection").replace(".md", "") + "_selected.json"
    with open(sel_path, "w") as f:
        json.dump(
            {
                "selected_checkpoint": winner["dump"].manifest["checkpoint_path"],
                "selected_sha256": winner["dump"].manifest["checkpoint_sha256"],
                "checkpoint_type": winner["dump"].manifest["checkpoint_type"],
                "epoch": winner["epoch"],
                "global_step": winner["step"],
                "dev_balanced": winner["balanced"],
                "dev_micro_csi_m": winner["micro_csi_m"],
                "epsilon": epsilon,
                "band_size": len(in_band),
                "shadow_agrees": bool(agree),
                "rule_sha256": rule.payload_hash(),
            },
            f, indent=2, sort_keys=True,
        )
    print(f"selection -> {sel_path}")


if __name__ == "__main__":
    main()
