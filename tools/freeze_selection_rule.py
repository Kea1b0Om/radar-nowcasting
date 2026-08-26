"""Step 1a: build and FREEZE the checkpoint-selection rule.

Run this exactly once, before any checkpoint is scored.  It reads the
training split (to place intensity-stratum boundaries) and the validation
split (to assign every validation event to a stratum and to dev/shadow),
then writes a hash-sealed JSON rule file.

It refuses to open the test split.  The test wetness figures (>=30 dBZ
7.75%, >=40 dBZ 0.89%) are deliberately NOT used as a resampling target --
matching them would make this test-informed model selection.  The only
statistics that cross into the rule come from train.

Example
-------
    python tools/freeze_selection_rule.py \
        --data_dir datasets/cikm/data/cikm_full \
        --out artifacts/cikm/selection/selection_rule.json \
        --n_strata 4 --frac_dev 0.5
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys

import numpy as np

sys.path.append(os.getcwd())

from tools.selection_rule import (  # noqa: E402
    RULE_SCHEMA_VERSION,
    THRESHOLDS_CIKM,
    SelectionRule,
    assign_strata,
    compute_split_severity,
    quantile_boundaries,
    sha256_file,
    stratified_dev_shadow_split,
)


def _reject_test_paths(*paths: str) -> None:
    for p in paths:
        low = os.path.basename(p).lower()
        if "test" in low:
            raise SystemExit(
                f"refusing to read '{p}': the selection rule must be frozen "
                f"without looking at the test split."
            )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data_dir", default="datasets/cikm/data/cikm_full")
    ap.add_argument("--train_h5", default=None)
    ap.add_argument("--train_meta", default=None)
    ap.add_argument("--val_h5", default=None)
    ap.add_argument("--val_meta", default=None)
    ap.add_argument("--out", default="artifacts/cikm/selection/selection_rule.json")
    ap.add_argument("--dataset_name", default="cikm")
    ap.add_argument("--data_key", default="vil")
    ap.add_argument("--raw_seq_len", type=int, default=15)
    ap.add_argument("--lag_time", type=int, default=5)
    ap.add_argument("--lead_time", type=int, default=10)
    ap.add_argument("--time_spacing", type=int, default=1)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--pixel_scale", type=float, default=90.0)
    ap.add_argument(
        "--crop",
        default="13,-14",
        help="evaluator crop as 'lo,hi' (CIKM 128->101); 'none' to disable",
    )
    ap.add_argument("--n_strata", type=int, default=4)
    ap.add_argument("--frac_dev", type=float, default=0.5)
    ap.add_argument("--split_seed", type=int, default=20260801)
    ap.add_argument("--bootstrap_B", type=int, default=2000)
    ap.add_argument("--bootstrap_seed", type=int, default=12345)
    # protocol that every dump must match to be comparable
    ap.add_argument("--stage1_samples", type=int, default=1)
    ap.add_argument("--stage2_samples", type=int, default=8)
    ap.add_argument("--stage1_batch_size", type=int, default=8)
    ap.add_argument("--stage2_batch_size", type=int, default=4)
    ap.add_argument("--euler_steps", type=int, default=10)
    ap.add_argument("--base_seed", type=int, default=20260801)
    ap.add_argument("--notes", default="")
    ap.add_argument("--force", action="store_true", help="overwrite an existing rule")
    args = ap.parse_args()

    train_h5 = args.train_h5 or f"{args.data_dir}/nowcast_training_full.h5"
    train_meta = args.train_meta or f"{args.data_dir}/nowcast_training_full_META.csv"
    val_h5 = args.val_h5 or f"{args.data_dir}/nowcast_validation_full.h5"
    val_meta = args.val_meta or f"{args.data_dir}/nowcast_validation_full_META.csv"
    _reject_test_paths(train_h5, train_meta, val_h5, val_meta)

    if os.path.exists(args.out) and not args.force:
        raise SystemExit(
            f"{args.out} already exists.  A frozen rule must not be silently "
            f"replaced -- pass --force only if you intend to invalidate every "
            f"score computed under the old rule."
        )

    crop = None if args.crop.lower() == "none" else tuple(
        int(v) for v in args.crop.split(",")
    )

    common = dict(
        data_key=args.data_key,
        raw_seq_len=args.raw_seq_len,
        lag_time=args.lag_time,
        lead_time=args.lead_time,
        time_spacing=args.time_spacing,
        stride=args.stride,
        crop=crop,
        pixel_scale=args.pixel_scale,
        progress=False,
    )

    print(f"[1/3] severity over TRAIN  ({train_h5})")
    tr = compute_split_severity(train_h5, train_meta, **common)
    print(f"      {len(tr['severity'])} events, "
          f"sev mean={tr['severity'].mean():.4f} "
          f"median={np.median(tr['severity']):.4f} "
          f"max={tr['severity'].max():.4f}")

    boundaries = quantile_boundaries(tr["severity"], args.n_strata)
    realised = len(boundaries) + 1
    if realised < args.n_strata:
        print(
            f"      NOTE: requested {args.n_strata} strata but train severity "
            f"quantiles collapsed to {realised} distinct cut regions "
            f"(ties at the dry end).  Recorded as-is."
        )
    print(f"      boundaries (train quantiles): {np.round(boundaries, 5).tolist()}")

    print(f"[2/3] severity over VALIDATION  ({val_h5})")
    va = compute_split_severity(val_h5, val_meta, **common)
    strata = assign_strata(va["severity"], boundaries)
    is_dev = stratified_dev_shadow_split(strata, args.frac_dev, args.split_seed)

    print("      stratum   n_val   sev range              n_dev  n_shadow")
    for k in range(realised):
        sel = strata == k
        if not sel.any():
            print(f"      {k:^7d}   {0:5d}   (empty)")
            continue
        s = va["severity"][sel]
        print(
            f"      {k:^7d}   {sel.sum():5d}   "
            f"[{s.min():.4f}, {s.max():.4f}]   "
            f"{int((sel & (is_dev == 1)).sum()):5d}  "
            f"{int((sel & (is_dev == 0)).sum()):8d}"
        )

    print("[3/3] hashing data files (provenance)")
    rule = SelectionRule(
        schema_version=RULE_SCHEMA_VERSION,
        dataset_name=args.dataset_name,
        thresholds=list(THRESHOLDS_CIKM),
        pixel_scale=args.pixel_scale,
        crop=None if crop is None else list(crop),
        n_strata_requested=args.n_strata,
        boundaries=boundaries.tolist(),
        n_strata_realised=realised,
        stratum_weights="equal",
        empty_cell_policy="exclude",
        split_seed=args.split_seed,
        frac_dev=args.frac_dev,
        selector_order=["balanced", "micro_csi_m", "fair_crps", "mse"],
        epsilon_rule="1.0 * stratified event-level bootstrap SE of S_balanced on dev",
        bootstrap_B=args.bootstrap_B,
        bootstrap_seed=args.bootstrap_seed,
        stage1_samples=args.stage1_samples,
        stage2_samples=args.stage2_samples,
        stage1_batch_size=args.stage1_batch_size,
        stage2_batch_size=args.stage2_batch_size,
        euler_steps=args.euler_steps,
        dtype="float32",
        seed_formula="base_seed + batch_index * S + sample_index",
        base_seed=args.base_seed,
        train_h5_sha256=sha256_file(train_h5),
        val_h5_sha256=sha256_file(val_h5),
        created_utc=datetime.datetime.utcnow().isoformat() + "Z",
        notes=args.notes,
        val_event_id=va["event_id"].tolist(),
        val_file_row=va["file_row"].tolist(),
        val_severity=va["severity"].tolist(),
        val_stratum=strata.tolist(),
        val_is_dev=is_dev.tolist(),
    )
    digest = rule.save(args.out)
    print(f"\nfrozen -> {args.out}")
    print(f"rule_sha256 = {digest}")
    print(
        "\nThis file is now the contract.  score_checkpoints.py and "
        "select_checkpoint.py both verify its hash; editing it by hand will "
        "make them refuse to run."
    )


if __name__ == "__main__":
    main()
