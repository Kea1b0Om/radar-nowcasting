"""Collate K1 oracle runs into the delta-plateau table and the kill-shot verdict.

Decision rule (pre-registered):
  co-primary 1 = A_nl1        (common-kernel mass-space L1, lower is better)
  co-primary 2 = B_fss35_w5   (operational 35 dBZ FSS, higher is better)
  B* = best of {flow, bot_fr} per pair.
  Pass = one co-primary significantly better than B* (paired bootstrap CI
  excluding 0) AND the other non-inferior (CI within the pre-registered margin)
  AND no material loss of peak / q99 / high-frequency energy.
"""

import argparse
import glob
import os

import numpy as np
import pandas as pd

CO_PRIMARY = [("A_nl1", True), ("B_fss35_w5", False)]
GUARDS = ["B_peak_retention", "B_q99_retention", "B_hf_energy_ratio", "B_mass_ratio"]


def paired(df, metric, lower_is_better, method="wfr", n_boot=4000, seed=0):
    piv = df.pivot_table(index=["file_row", "span_min", "hidden_frame"],
                         columns="method", values=metric)
    need = {method, "flow", "bot_fr"}
    if not need.issubset(piv.columns):
        return None
    piv = piv.dropna(subset=list(need))
    if len(piv) < 5:
        return None
    base = piv[["flow", "bot_fr"]].min(axis=1) if lower_is_better \
        else piv[["flow", "bot_fr"]].max(axis=1)
    diff = (piv[method] - base).to_numpy()
    rng = np.random.default_rng(seed)
    boots = np.array([np.median(rng.choice(diff, len(diff), replace=True))
                      for _ in range(n_boot)])
    return {
        "n": len(diff),
        "wfr": float(piv[method].median()),
        "flow": float(piv["flow"].median()),
        "bot_fr": float(piv["bot_fr"].median()),
        "best_base": float(base.median()),
        "diff": float(np.median(diff)),
        "lo": float(np.quantile(boots, 0.025)),
        "hi": float(np.quantile(boots, 0.975)),
        "win": float((diff < 0).mean() if lower_is_better else (diff > 0).mean()),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default="artifacts/cikm/wfr_oracle_sweep")
    p.add_argument("--pattern", default="k1_*.csv")
    p.add_argument("--per-span", action="store_true")
    args = p.parse_args()

    frames = []
    for path in sorted(glob.glob(os.path.join(args.dir, args.pattern))):
        df = pd.read_csv(path)
        df["source"] = os.path.basename(path)
        frames.append(df)
    if not frames:
        raise SystemExit(f"no CSVs in {args.dir}")
    all_df = pd.concat(frames, ignore_index=True)

    groups = ["delta_km"] + (["span_min"] if args.per_span else [])
    print(f"{'delta':>6} {'span':>5} {'metric':>14} {'wfr':>8} {'flow':>8} "
          f"{'bot_fr':>8} {'diff':>9} {'ci95':>20} {'win':>6} {'n':>5}")
    for keys, sub in all_df.groupby(groups):
        keys = keys if isinstance(keys, tuple) else (keys,)
        delta = keys[0]
        span = keys[1] if len(keys) > 1 else "all"
        for metric, lower in CO_PRIMARY:
            r = paired(sub, metric, lower)
            if r is None:
                continue
            print(f"{delta:>6g} {str(span):>5} {metric:>14} {r['wfr']:>8.4f} "
                  f"{r['flow']:>8.4f} {r['bot_fr']:>8.4f} {r['diff']:>+9.4f} "
                  f"[{r['lo']:+.4f},{r['hi']:+.4f}] {r['win']:>6.2f} {r['n']:>5d}")

    print("\nguard metrics (median, wfr / flow / bot_fr; 1.0 = matches truth):")
    for keys, sub in all_df.groupby(groups):
        keys = keys if isinstance(keys, tuple) else (keys,)
        tag = f"delta={keys[0]:g}" + (f" span={keys[1]}" if len(keys) > 1 else "")
        med = sub.pivot_table(index="method", values=GUARDS, aggfunc="median")
        for g in GUARDS:
            vals = " / ".join(f"{med.loc[m, g]:.3f}" if m in med.index else "  -  "
                              for m in ("wfr", "flow", "bot_fr"))
            print(f"  {tag:<22} {g:<22} {vals}")

    diag = [c for c in all_df.columns if c.startswith("diag_")]
    if diag:
        print("\nWFR coupling diagnostics (median by delta):")
        w = all_df[all_df.method == "wfr"]
        print(w.groupby("delta_km")[diag].median().to_string())


if __name__ == "__main__":
    main()
