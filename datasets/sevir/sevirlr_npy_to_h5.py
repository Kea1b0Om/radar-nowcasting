"""
Convert PW-FouCast's SEVIR-LR .npy sequences into the HDF5 + META layout that
FlowCast_uot's DynamicSequentialSevirDataset expects.

Source layout (PW-FouCast / sevir_lr):
    <root>/vil_single/storm/storm_<YYYYMMDDHHMM>_<id>.npy    (128, 128, 25) uint8
    <root>/vil_single/random/random_<YYYYMMDDHHMM>_<id>.npy
    data_index/sevir_train_periods.txt   sequence ids, one per line
    data_index/sevir_test_periods.txt

Output layout (what our loader reads):
    nowcast_{training,validation,testing}_full.h5        dataset "vil": (N,H,W,T) uint8
    nowcast_{training,validation,testing}_full_META.csv  file_row,sample_id,split,time_utc

PW-FouCast ships no validation split, so we carve one out of the training list
*chronologically* (latest `--val-fraction` of training timestamps). A random
split would leak: SEVIR sequences overlap in time, and the official test set is
a later period, so a temporal holdout is both leak-free and structurally
matched to how the test set was built.
"""

import argparse
import csv
import os
import re
from datetime import datetime

import h5py
import numpy as np
from tqdm import tqdm

TIMESTAMP_RE = re.compile(r"^(storm|random)_(\d{12})_(\d+)$")


def parse_sequence_id(seq_id):
    """`storm_201801082218_364` -> ("storm", datetime(2018,1,8,22,18), "364")."""
    m = TIMESTAMP_RE.match(seq_id)
    if not m:
        raise ValueError(f"Unrecognised sequence id: {seq_id!r}")
    kind, stamp, tail = m.groups()
    return kind, datetime.strptime(stamp, "%Y%m%d%H%M"), tail


def read_index(path):
    with open(path) as fh:
        return [line.strip() for line in fh if line.strip()]


def resolve_paths(seq_ids, vil_single_root):
    """Map ids to on-disk paths, reporting anything missing rather than crashing."""
    resolved, missing = [], []
    for seq_id in seq_ids:
        kind, ts, _ = parse_sequence_id(seq_id)
        path = os.path.join(vil_single_root, kind, seq_id + ".npy")
        (resolved if os.path.exists(path) else missing).append(
            (seq_id, ts, path) if os.path.exists(path) else seq_id
        )
    return resolved, missing


def write_split(entries, out_dir, split_name, csv_split_label, expect_shape=None):
    """Stream one split into a single h5 + META csv."""
    h5_path = os.path.join(out_dir, f"nowcast_{split_name}_full.h5")
    csv_path = os.path.join(out_dir, f"nowcast_{split_name}_full_META.csv")
    n = len(entries)
    if n == 0:
        raise ValueError(f"Refusing to write an empty split: {split_name}")

    probe = np.load(entries[0][2])
    if probe.ndim != 3:
        raise ValueError(f"Expected (H,W,T) sequences, got {probe.shape}")
    if expect_shape is not None and probe.shape != expect_shape:
        raise ValueError(f"{entries[0][0]}: shape {probe.shape} != {expect_shape}")
    H, W, T = probe.shape

    with h5py.File(h5_path, "w") as hf:
        dset = hf.create_dataset(
            "vil",
            shape=(n, H, W, T),
            dtype=np.uint8,
            chunks=(1, H, W, T),
            compression=None,
        )
        with open(csv_path, "w", newline="") as cf:
            writer = csv.writer(cf)
            writer.writerow(["file_row", "sample_id", "split", "time_utc"])
            for row, (seq_id, ts, path) in enumerate(
                tqdm(entries, desc=f"writing {split_name}")
            ):
                arr = np.load(path)
                if arr.shape != (H, W, T):
                    raise ValueError(
                        f"{seq_id}: inconsistent shape {arr.shape}, expected {(H, W, T)}"
                    )
                dset[row] = arr
                writer.writerow(
                    [row, seq_id, csv_split_label, ts.strftime("%Y-%m-%dT%H:%M:%S")]
                )

    size_gb = os.path.getsize(h5_path) / 1e9
    print(
        f"[{split_name}] {n} sequences  shape=({H},{W},{T})  {size_gb:.2f} GB\n"
        f"           {h5_path}\n           {csv_path}",
        flush=True,
    )
    return n, (H, W, T)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--vil-single-root",
        default="${DATA_ROOT}/sevir_lr/data/vil_single",
    )
    p.add_argument("--train-index", required=True)
    p.add_argument("--test-index", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument(
        "--val-fraction",
        type=float,
        default=0.1,
        help="Chronologically latest fraction of the training list held out for validation.",
    )
    args = p.parse_args()

    if not (0.0 < args.val_fraction < 0.5):
        raise ValueError("--val-fraction must be in (0, 0.5)")
    os.makedirs(args.out_dir, exist_ok=True)

    train_ids = read_index(args.train_index)
    test_ids = read_index(args.test_index)
    print(f"index: train={len(train_ids)} test={len(test_ids)}")

    train_entries, train_missing = resolve_paths(train_ids, args.vil_single_root)
    test_entries, test_missing = resolve_paths(test_ids, args.vil_single_root)
    if train_missing or test_missing:
        print(
            f"WARNING: {len(train_missing)} train and {len(test_missing)} test ids "
            f"have no .npy on disk and are dropped. First few: "
            f"{(train_missing + test_missing)[:5]}"
        )

    # Temporal holdout: sort by timestamp, take the tail as validation.
    train_entries.sort(key=lambda e: (e[1], e[0]))
    test_entries.sort(key=lambda e: (e[1], e[0]))
    n_val = int(round(len(train_entries) * args.val_fraction))
    fit_entries, val_entries = train_entries[:-n_val], train_entries[-n_val:]

    print(
        f"temporal split: train {fit_entries[0][1]:%Y-%m-%d} .. {fit_entries[-1][1]:%Y-%m-%d} "
        f"({len(fit_entries)})  |  val {val_entries[0][1]:%Y-%m-%d} .. "
        f"{val_entries[-1][1]:%Y-%m-%d} ({len(val_entries)})  |  test "
        f"{test_entries[0][1]:%Y-%m-%d} .. {test_entries[-1][1]:%Y-%m-%d} ({len(test_entries)})"
    )
    overlap = {e[0] for e in fit_entries + val_entries} & {e[0] for e in test_entries}
    if overlap:
        raise ValueError(f"train/val and test share {len(overlap)} sequence ids")

    _, shape = write_split(fit_entries, args.out_dir, "training", "train")
    write_split(val_entries, args.out_dir, "validation", "valid", expect_shape=shape)
    write_split(test_entries, args.out_dir, "testing", "test", expect_shape=shape)
    print(
        f"\nDone. raw_seq_len = {shape[2]} -> set data_params.raw_seq_len accordingly."
    )


if __name__ == "__main__":
    main()
