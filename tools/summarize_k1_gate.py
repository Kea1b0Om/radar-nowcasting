"""Event-level statistics for the K1 gate (v1.1).

Fixes the two statistical defects of the v1.0 summariser:
  * hidden frames inside one file_row are averaged BEFORE bootstrapping, so the
    bootstrap unit is the event, not the (correlated) hidden frame;
  * every baseline is compared as a FIXED method -- no per-sample "best of
    {flow, bot_fr}" oracle selector.

Reports, per span and per (fixed) baseline, the paired median difference with a
95% event-level bootstrap CI, plus the guard metrics.
"""

import argparse
import glob
import os

import numpy as np
import pandas as pd

CO_PRIMARY = [("A_nl1", True), ("B_fss35_wN", False), ("B_fss40_wN", False)]
GUARDS = ["B_peak_retention", "B_q99_retention", "B_hf_energy_ratio",
          "B_mass_ratio", "B_nl1_raw"]


def event_table(df, metric):
    """Average hidden frames within an event -> one value per (event, method)."""
    return df.pivot_table(index="file_row", columns="method", values=metric,
                          aggfunc="mean")


def paired(df, metric, lower_is_better, method, baseline, n_boot=4000, seed=0):
    piv = event_table(df, metric)
    if method not in piv.columns or baseline not in piv.columns:
        return None
    piv = piv[[method, baseline]].dropna()
    if len(piv) < 5:
        return None
    diff = (piv[method] - piv[baseline]).to_numpy()
    rng = np.random.default_rng(seed)
    boots = np.array([np.median(rng.choice(diff, len(diff), replace=True))
                      for _ in range(n_boot)])
    return {
        "n_events": int(len(diff)),
        "method": float(piv[method].median()),
        "baseline": float(piv[baseline].median()),
        "diff": float(np.median(diff)),
        "lo": float(np.quantile(boots, 0.025)),
        "hi": float(np.quantile(boots, 0.975)),
        "win": float((diff < 0).mean() if lower_is_better else (diff > 0).mean()),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default="artifacts/cikm/wfr_oracle_v11")
    p.add_argument("--pattern", default="k1_v1.1_*.csv")
    p.add_argument("--method", default="wfr")
    p.add_argument("--baselines", nargs="+",
                   default=["flow_proxy", "flow_full", "bot_fr", "linear"])
    p.add_argument("--group-cols", nargs="+", default=["span_min"])
    args = p.parse_args()

    frames = [pd.read_csv(f) for f in sorted(glob.glob(os.path.join(args.dir,
                                                                   args.pattern)))]
    if not frames:
        raise SystemExit(f"no CSVs matching {args.pattern} in {args.dir}")
    df = pd.concat(frames, ignore_index=True)
    if "stratum" in df.columns:
        strata = df.groupby("stratum").file_row.nunique().to_dict()
        print(f"strata: {strata}")

    print(f"\n{'group':>26} {'metric':>12} {'baseline':>11} {args.method:>8} "
          f"{'base':>8} {'diff':>9} {'ci95':>20} {'win':>5} {'n':>4}")
    for keys, sub in df.groupby(args.group_cols):
        keys = keys if isinstance(keys, tuple) else (keys,)
        tag = ",".join(f"{c}={v}" for c, v in zip(args.group_cols, keys))
        for metric, lower in CO_PRIMARY:
            for base in args.baselines:
                r = paired(sub, metric, lower, args.method, base)
                if r is None:
                    continue
                print(f"{tag:>26} {metric:>12} {base:>11} {r['method']:>8.4f} "
                      f"{r['baseline']:>8.4f} {r['diff']:>+9.4f} "
                      f"[{r['lo']:+.4f},{r['hi']:+.4f}] {r['win']:>5.2f} "
                      f"{r['n_events']:>4d}")

    print("\nguards (event-mean median by method):")
    for keys, sub in df.groupby(args.group_cols):
        keys = keys if isinstance(keys, tuple) else (keys,)
        tag = ",".join(f"{c}={v}" for c, v in zip(args.group_cols, keys))
        med = sub.pivot_table(index="method", values=GUARDS, aggfunc="median")
        print(f"  [{tag}]")
        print("    " + med.round(4).to_string().replace("\n", "\n    "))

    diag = [c for c in df.columns if c.startswith("diag_")]
    if diag:
        print("\ncoupling diagnostics (median):")
        d = df[df.method.isin(["wfr", "bot_fr"])].groupby("method")[diag].median()
        print("  " + d.round(4).to_string().replace("\n", "\n  "))
    if "truth_mass_in_source_dry_frac" in df.columns:
        print("\ninitiation proxy (median share of truth mass in cells dry at t0): "
              f"{df.truth_mass_in_source_dry_frac.median():.4f}")


if __name__ == "__main__":
    main()
