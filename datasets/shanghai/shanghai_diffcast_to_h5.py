"""Convert DiffCast's official shanghai.h5 into our SEVIR-style HDF5 layout.

Input  (DiffCast, also what SDIR/DuoCast train on):
    ${DATA_ROOT}/DiffCast/Shanghai/shanghai.h5
    groups train (1535) / test (527); each key "<idx>" -> (25, 501, 501) uint8.
    Values are radar reflectivity stored as dBZ * 255 / 90 (PIXEL_SCALE = 90 in
    DiffCast's dataset_shanghai.py); evaluation thresholds [20, 30, 35, 40] dBZ.

Output (our layout, consumed by DynamicAutoencoderSevirDataset /
DynamicSequentialSevirDataset via --train_file/--train_meta/... args):
    nowcast_{training,validation,testing}_full.h5   key "vil",
        shape (N, 128, 128, 25) uint8
    nowcast_{...}_full_META.csv   cols [file_row, sample_id, split, time_utc]

Faithfulness to DiffCast's preprocessing: they load uint8, divide by 255 and
apply torchvision transforms.Resize((128, 128)) with default arguments
(bilinear). We do exactly that, then re-quantise to uint8 (max error 0.5/255
= 0.18 dBZ, negligible against the 20 dBZ lowest threshold).

Split: DiffCast has no validation split (their "val" IS the test set --
selecting checkpoints on it would be test peeking). We carve the LAST 10% of
train keys (event order) as validation: train 0..1380, val 1381..1534. The
official 527-event test set is converted untouched, so test-set numbers stay
on the same footing as DiffCast / SDIR / DuoCast tables.

time_utc: shanghai.h5 carries no timestamps. The loader parse_dates-es the
column, so we write synthetic monotonic placeholders (2020-01-01 + idx hours).
Nothing downstream orders by them; splits are fixed here at conversion time.
"""

import argparse

import h5py
import numpy as np
import pandas as pd
import torch
from torchvision import transforms

RESIZE = transforms.Resize((128, 128))  # DiffCast's exact call, default args


def convert_group(src, keys, dst_h5, dst_meta, split_name):
    n = len(keys)
    with h5py.File(dst_h5, "w") as out:
        dset = out.create_dataset(
            "vil", shape=(n, 128, 128, 25), dtype=np.uint8, chunks=(1, 128, 128, 25)
        )
        for row, key in enumerate(keys):
            frames = src[key][()]  # (25, 501, 501) uint8
            t = torch.from_numpy(frames).float() / 255.0
            t = RESIZE(t)  # (25, 128, 128)
            arr = (t.numpy() * 255.0).round().clip(0, 255).astype(np.uint8)
            dset[row] = arr.transpose(1, 2, 0)  # -> (128, 128, 25)
            if (row + 1) % 200 == 0 or row + 1 == n:
                print(f"  {split_name}: {row + 1}/{n}", flush=True)

    meta = pd.DataFrame(
        {
            "file_row": np.arange(n),
            "sample_id": [f"shanghai_{split_name}_{k}" for k in keys],
            "split": split_name,
            "time_utc": pd.date_range("2020-01-01", periods=n, freq="h"),
        }
    )
    meta.to_csv(dst_meta, index=False)
    print(f"[{split_name}] {n} sequences -> {dst_h5}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="DiffCast shanghai.h5")
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--val_fraction", type=float, default=0.10)
    args = ap.parse_args()

    with h5py.File(args.src, "r") as f:
        train_keys = sorted(
            (k for k in f["train"].keys() if k != "all_len"), key=int
        )
        test_keys = sorted((k for k in f["test"].keys() if k != "all_len"), key=int)
        n_val = int(round(len(train_keys) * args.val_fraction))
        split = {
            "training": train_keys[: len(train_keys) - n_val],
            "validation": train_keys[len(train_keys) - n_val :],
            "testing": test_keys,
        }
        for split_name, keys in split.items():
            src_group = f["test"] if split_name == "testing" else f["train"]
            convert_group(
                src_group,
                keys,
                f"{args.out_dir}/nowcast_{split_name}_full.h5",
                f"{args.out_dir}/nowcast_{split_name}_full_META.csv",
                split_name,
            )

    print("Done. Layout: (N, 128, 128, 25) uint8, key 'vil', pixel_scale 90.")


if __name__ == "__main__":
    main()
