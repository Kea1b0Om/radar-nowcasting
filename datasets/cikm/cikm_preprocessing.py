"""
Convert the original CIKM HDF5 layout into FlowCast's standard HDF5 + META.csv format.
"""

import argparse
import os

import h5py
import numpy as np
import pandas as pd


SPLIT_TO_INPUT = {
    "training": "train",
    "validation": "valid",
    "testing": "test",
}


def center_pad_to_square(array_hw_t: np.ndarray, target_size: int) -> np.ndarray:
    """Match torchvision CenterCrop behavior for inputs smaller than the target."""
    height, width, _ = array_hw_t.shape
    if height > target_size or width > target_size:
        raise ValueError(
            f"Expected input smaller than target_size={target_size}, got {(height, width)}"
        )

    pad_h_total = target_size - height
    pad_w_total = target_size - width
    pad_top = pad_h_total // 2
    pad_bottom = pad_h_total - pad_top
    pad_left = pad_w_total // 2
    pad_right = pad_w_total - pad_left

    return np.pad(
        array_hw_t,
        ((pad_top, pad_bottom), (pad_left, pad_right), (0, 0)),
        mode="constant",
        constant_values=0,
    )


def convert_split(input_path: str, output_dir: str, split_name: str, img_size: int) -> None:
    input_split = SPLIT_TO_INPUT[split_name]
    h5_name = f"nowcast_{split_name}_full.h5"
    meta_name = f"nowcast_{split_name}_full_META.csv"
    output_h5_path = os.path.join(output_dir, h5_name)
    output_meta_path = os.path.join(output_dir, meta_name)

    with h5py.File(input_path, "r") as input_h5:
        num_samples = int(input_h5[f"{input_split}_len"][()])
        date_range = pd.date_range(
            start="2000-01-01",
            periods=num_samples,
            freq="15min",
        )

        os.makedirs(output_dir, exist_ok=True)
        with h5py.File(output_h5_path, "w") as output_h5:
            dataset = output_h5.create_dataset(
                "vil",
                shape=(num_samples, img_size, img_size, 15),
                dtype=np.uint8,
                chunks=(1, img_size, img_size, 15),
                compression="gzip",
                compression_opts=4,
            )

            meta_rows = []
            for idx in range(num_samples):
                sample_key = f"sample_{idx + 1}"
                sample_t_h_w = input_h5[input_split][sample_key][()]
                sample_h_w_t = np.transpose(sample_t_h_w, (1, 2, 0))
                sample_padded = center_pad_to_square(sample_h_w_t, img_size)
                dataset[idx] = sample_padded.astype(np.uint8)
                meta_rows.append(
                    {
                        "file_row": idx,
                        "sample_id": sample_key,
                        "split": input_split,
                        "time_utc": date_range[idx].isoformat(),
                    }
                )

    pd.DataFrame(meta_rows).to_csv(output_meta_path, index=False)
    print(f"Wrote {output_h5_path}")
    print(f"Wrote {output_meta_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess CIKM into FlowCast format.")
    parser.add_argument(
        "--input_h5",
        type=str,
        required=True,
        help="Path to the original cikm.h5 file.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="datasets/cikm/data/cikm_full",
        help="Directory for standardized FlowCast files.",
    )
    parser.add_argument(
        "--img_size",
        type=int,
        default=128,
        help="Target square size after center padding.",
    )
    args = parser.parse_args()

    for split_name in ("training", "validation", "testing"):
        convert_split(args.input_h5, args.output_dir, split_name, args.img_size)


if __name__ == "__main__":
    main()
