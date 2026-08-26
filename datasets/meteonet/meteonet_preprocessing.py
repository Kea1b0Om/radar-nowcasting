"""
Convert MeteoNet NW reflectivity into FlowCast's standard HDF5 + META.csv format.

The source data has appeared in three layouts across the sibling repositories, so
the layout is detected instead of assumed:

  sequence_npy  a flat directory of {YYYYMMDD_HHMM}.npy, each (T, H, W)
                (PW-FouCast / SlotCast `reflectivity_5to20`)
  frame_npy     a flat directory of {YYYYMMDD_HHMM}.npy, each (H, W)
                (`reflectivity_npy`; sequences are cut here with a sliding window)
  hdf5          a DiffCast-style file with {split}_len and per-sample datasets
                (`meteo_radar.h5`)

Values are stored on FlowCast's 0-255 convention so that the downstream
`normalized_autoencoder` division by 255 maps back onto dBZ / pixel_scale,
matching how CIKM and SEVIR are handled.
"""

import argparse
import os
import re
from datetime import datetime, timedelta

import h5py
import numpy as np
import pandas as pd


PERIOD_PATTERN = re.compile(r"^(\d{8}_\d{4})\.npy$")
SPLIT_NAMES = ("training", "validation", "testing")
DIFFCAST_SPLIT_KEYS = {"training": "train", "validation": "val", "testing": "test"}
FRAME_INTERVAL_MINUTES = 10
WINDOW_STRIDE_MINUTES = 50
DRY_SEQUENCE_THRESHOLD = 0.01


def parse_period(period: str) -> datetime:
    return datetime.strptime(period, "%Y%m%d_%H%M")


def detect_layout(source: str) -> str:
    if os.path.isfile(source):
        if source.endswith((".h5", ".hdf5")):
            return "hdf5"
        raise ValueError(f"Unsupported source file: {source}")

    if not os.path.isdir(source):
        raise ValueError(f"Source does not exist: {source}")

    probe_names = sorted(n for n in os.listdir(source) if PERIOD_PATTERN.match(n))
    if not probe_names:
        raise ValueError(f"No {{YYYYMMDD_HHMM}}.npy files found under {source}")

    ndim = np.load(os.path.join(source, probe_names[0]), mmap_mode="r").ndim
    if ndim == 3:
        return "sequence_npy"
    if ndim == 2:
        return "frame_npy"
    raise ValueError(f"Unexpected array rank {ndim} in {probe_names[0]}")


def list_periods(source: str) -> list:
    return sorted(
        PERIOD_PATTERN.match(n).group(1)
        for n in os.listdir(source)
        if PERIOD_PATTERN.match(n)
    )


def read_period_file(path: str) -> list:
    with open(path, "r") as handle:
        return [line.strip() for line in handle if line.strip()]


def cut_sequences_from_frames(source: str, seq_len: int) -> list:
    """Reproduce the PW-FouCast sliding window over a single-frame directory."""
    available = set(list_periods(source))
    if not available:
        return []

    stamps = sorted(parse_period(p) for p in available)
    cursor, last = stamps[0], stamps[-1]
    span = timedelta(minutes=FRAME_INTERVAL_MINUTES * (seq_len - 1))

    periods = []
    while cursor + span <= last:
        window = [
            (cursor + timedelta(minutes=FRAME_INTERVAL_MINUTES * i)).strftime(
                "%Y%m%d_%H%M"
            )
            for i in range(seq_len)
        ]
        if all(stamp in available for stamp in window):
            periods.append(window)
        cursor += timedelta(minutes=WINDOW_STRIDE_MINUTES)
    return periods


def load_sequence(source: str, layout: str, key, seq_len: int) -> np.ndarray:
    """Return one event as (T, H, W) float32."""
    if layout == "sequence_npy":
        array = np.load(os.path.join(source, f"{key}.npy"))
    else:
        array = np.stack(
            [np.load(os.path.join(source, f"{stamp}.npy")) for stamp in key], axis=0
        )

    array = np.asarray(array, dtype=np.float32).squeeze()
    if array.ndim != 3:
        raise ValueError(f"Expected a (T, H, W) event, got shape {array.shape}")
    if array.shape[0] < seq_len:
        raise ValueError(f"Event has {array.shape[0]} frames, need {seq_len}")
    return array[:seq_len]


def estimate_source_scale(
    source: str, layout: str, keys: list, seq_len: int, sample_size: int = 32
) -> float:
    """Peek at a few events so dBZ input is not confused with 0-255 input."""
    stride = max(1, len(keys) // sample_size)
    observed_max = 0.0
    for key in keys[::stride][:sample_size]:
        observed_max = max(observed_max, float(load_sequence(source, layout, key, seq_len).max()))
    return observed_max


def write_split(
    output_dir: str,
    split_name: str,
    events,
    num_events: int,
    img_size: int,
    seq_len: int,
) -> None:
    """Stream (sample_id, timestamp, (T, H, W) uint8) events into HDF5 + META.csv."""
    os.makedirs(output_dir, exist_ok=True)
    h5_path = os.path.join(output_dir, f"nowcast_{split_name}_full.h5")
    meta_path = os.path.join(output_dir, f"nowcast_{split_name}_full_META.csv")

    meta_rows = []
    with h5py.File(h5_path, "w") as output_h5:
        dataset = output_h5.create_dataset(
            "vil",
            shape=(num_events, img_size, img_size, seq_len),
            dtype=np.uint8,
            chunks=(1, img_size, img_size, seq_len),
            compression="gzip",
            compression_opts=4,
        )
        for idx, (sample_id, timestamp, event_t_h_w) in enumerate(events):
            if event_t_h_w.shape != (seq_len, img_size, img_size):
                raise ValueError(
                    f"{sample_id}: expected {(seq_len, img_size, img_size)}, "
                    f"got {event_t_h_w.shape}. Pass --img_size/--seq_len to match the source."
                )
            dataset[idx] = np.transpose(event_t_h_w, (1, 2, 0))
            meta_rows.append(
                {
                    "file_row": idx,
                    "sample_id": sample_id,
                    "split": split_name,
                    "time_utc": timestamp,
                }
            )

    pd.DataFrame(meta_rows).to_csv(meta_path, index=False)
    print(f"Wrote {h5_path} ({num_events} events)")
    print(f"Wrote {meta_path}")


def build_npy_splits(args, layout: str) -> dict:
    """Assign event keys to training/validation/testing for the directory layouts."""
    if layout == "frame_npy":
        all_keys = cut_sequences_from_frames(args.source, args.seq_len)
        train_keys = [k for k in all_keys if parse_period(k[0]) < args.test_split]
        test_keys = [k for k in all_keys if parse_period(k[0]) >= args.test_split]
    else:
        available = set(list_periods(args.source))
        if args.train_periods and args.test_periods:
            train_keys = [p for p in read_period_file(args.train_periods) if p in available]
            test_keys = [p for p in read_period_file(args.test_periods) if p in available]
            missing = len(read_period_file(args.train_periods)) + len(
                read_period_file(args.test_periods)
            ) - len(train_keys) - len(test_keys)
            if missing:
                print(f"[warn] {missing} indexed periods are absent from {args.source}")
        else:
            all_keys = sorted(available)
            train_keys = [p for p in all_keys if parse_period(p) < args.test_split]
            test_keys = [p for p in all_keys if parse_period(p) >= args.test_split]

    if not train_keys:
        raise ValueError("No training events were selected; check --source and the index files.")

    # Chronological tail of train becomes validation, so no future event leaks backwards.
    num_val = max(1, int(round(args.val_fraction * len(train_keys))))
    return {
        "training": train_keys[:-num_val],
        "validation": train_keys[-num_val:],
        "testing": test_keys,
    }


def convert_npy(args, layout: str) -> None:
    splits = build_npy_splits(args, layout)

    scale_reference = splits["training"] + splits["validation"]
    observed_max = estimate_source_scale(args.source, layout, scale_reference, args.seq_len)
    if args.source_scale == "auto":
        source_is_dbz = observed_max <= args.pixel_scale + 1.0
    else:
        source_is_dbz = args.source_scale == "dbz"
    gain = 255.0 / args.pixel_scale if source_is_dbz else 1.0
    print(
        f"Layout: {layout} | sampled max {observed_max:.1f} | "
        f"treating source as {'dBZ' if source_is_dbz else '0-255'} | gain {gain:.4f}"
    )

    for split_name in SPLIT_NAMES:
        keys = splits[split_name]
        if not keys:
            print(f"[warn] {split_name} split is empty, skipping")
            continue

        def events():
            for key in keys:
                sample_id = key if layout == "sequence_npy" else key[0]
                event = load_sequence(args.source, layout, key, args.seq_len)
                event = np.clip(event * gain, 0.0, 255.0).astype(np.uint8)
                yield sample_id, parse_period(sample_id).isoformat(), event

        write_split(
            args.output_dir,
            split_name,
            events(),
            len(keys),
            args.img_size,
            args.seq_len,
        )


def convert_hdf5(args) -> None:
    """DiffCast-style meteo_radar.h5: {split}_len plus per-sample datasets."""
    with h5py.File(args.source, "r") as input_h5:
        for split_name in SPLIT_NAMES:
            split_key = DIFFCAST_SPLIT_KEYS[split_name]
            if f"{split_key}_len" not in input_h5:
                print(f"[warn] {split_key}_len absent from {args.source}, skipping {split_name}")
                continue

            num_events = int(input_h5[f"{split_key}_len"][()])
            group = input_h5[split_key]
            sample_keys = [
                k for k in (str(i) for i in range(num_events)) if k in group
            ] or [f"sample_{i + 1}" for i in range(num_events)]

            observed_max = max(
                float(np.asarray(group[k]).max())
                for k in sample_keys[:: max(1, len(sample_keys) // 32)][:32]
            )
            source_is_dbz = (
                observed_max <= args.pixel_scale + 1.0
                if args.source_scale == "auto"
                else args.source_scale == "dbz"
            )
            gain = 255.0 / args.pixel_scale if source_is_dbz else 1.0
            print(
                f"Layout: hdf5/{split_key} | sampled max {observed_max:.1f} | "
                f"treating source as {'dBZ' if source_is_dbz else '0-255'} | gain {gain:.4f}"
            )

            # The DiffCast layout carries no timestamps, so synthesize a monotonic index.
            date_range = pd.date_range(
                start="2018-01-01", periods=len(sample_keys), freq="50min"
            )

            def events():
                for idx, sample_key in enumerate(sample_keys):
                    event = np.asarray(group[sample_key], dtype=np.float32).squeeze()
                    event = np.clip(event[: args.seq_len] * gain, 0.0, 255.0).astype(np.uint8)
                    yield sample_key, date_range[idx].isoformat(), event

            write_split(
                args.output_dir,
                split_name,
                events(),
                len(sample_keys),
                args.img_size,
                args.seq_len,
            )


def probe(args, layout: str) -> None:
    print(f"Source: {args.source}")
    print(f"Detected layout: {layout}")

    if layout == "hdf5":
        with h5py.File(args.source, "r") as input_h5:
            print(f"Top-level keys: {list(input_h5.keys())}")
            for split_key in ("train", "val", "test"):
                if f"{split_key}_len" in input_h5:
                    length = int(input_h5[f"{split_key}_len"][()])
                    member = list(input_h5[split_key].keys())[:1]
                    shape = np.asarray(input_h5[split_key][member[0]]).shape if member else None
                    print(f"  {split_key}: len={length} first={member} shape={shape}")
        return

    periods = list_periods(args.source)
    print(f"npy files: {len(periods)} (first {periods[:1]}, last {periods[-1:]})")
    if layout == "frame_npy":
        windows = cut_sequences_from_frames(args.source, args.seq_len)
        print(f"Sliding window would yield {len(windows)} events of {args.seq_len} frames")
        keys = windows[:8]
    else:
        keys = periods[:8]

    sample = load_sequence(args.source, layout, keys[0], args.seq_len)
    print(f"Event shape: {sample.shape} dtype={sample.dtype}")
    print(
        f"Value range over {len(keys)} sampled events: "
        f"min={min(float(load_sequence(args.source, layout, k, args.seq_len).min()) for k in keys):.2f} "
        f"max={max(float(load_sequence(args.source, layout, k, args.seq_len).max()) for k in keys):.2f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess MeteoNet into FlowCast format.")
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Directory of MeteoNet npy files, or a DiffCast-style meteo_radar.h5.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="datasets/meteonet/data/meteonet_full",
        help="Directory for standardized FlowCast files.",
    )
    parser.add_argument(
        "--layout",
        type=str,
        default="auto",
        choices=["auto", "sequence_npy", "frame_npy", "hdf5"],
    )
    parser.add_argument("--train_periods", type=str, default=None)
    parser.add_argument("--test_periods", type=str, default=None)
    parser.add_argument(
        "--test_split",
        type=lambda s: datetime.strptime(s, "%Y%m%d"),
        default=datetime(2018, 9, 1),
        help="First date of the test split when no period index files are given.",
    )
    parser.add_argument(
        "--val_fraction",
        type=float,
        default=0.1,
        help="Chronological tail of the training split held out for validation.",
    )
    parser.add_argument("--img_size", type=int, default=128)
    parser.add_argument("--seq_len", type=int, default=25)
    parser.add_argument(
        "--pixel_scale",
        type=float,
        default=90.0,
        help="dBZ value that maps to 255 in the stored uint8 data.",
    )
    parser.add_argument(
        "--source_scale",
        type=str,
        default="auto",
        choices=["auto", "dbz", "uint8"],
        help="Value convention of the source arrays.",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Report the detected layout and value range without writing anything.",
    )
    args = parser.parse_args()

    layout = detect_layout(args.source) if args.layout == "auto" else args.layout

    if args.probe:
        probe(args, layout)
    elif layout == "hdf5":
        convert_hdf5(args)
    else:
        convert_npy(args, layout)


if __name__ == "__main__":
    main()
