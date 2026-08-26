"""Write the raw ensemble member array to HDF5, with a provenance manifest.

Why this exists: every collapse (member-0, per-member, ensemble mean) and every
score (CSI, empirical CRPS, fair CRPS, Brier) must be computed from *the same*
members.  The legacy path could not do that - S=1 and S=8 were separate
inference runs, and the seed rule `idx * S + sample_idx` makes the single member
of an S=1 run a different draw from member 0 of an S=8 run for every batch after
the first.  Saving the members once and scoring offline removes the whole class
of "which run produced this number" questions, and makes re-scoring under a new
metric cost minutes instead of a GPU-day.

The array is written exactly as the evaluation path produced it - after crop,
after `raw_to_eval_scale`, after clamping - so the saved file is what the metrics
saw, not an idealised version of it.

Storage: CIKM at 4000 events x 8 members x 10 leads x 101 x 101 is 12.2 GiB in
float32 and 6.1 GiB in float16, plus 1.5 / 0.8 GiB for truth.
"""

import hashlib
import json
import os
from typing import Any, Dict, Optional

import h5py
import numpy as np

MANIFEST_ATTR = "manifest_json"
SCHEMA_VERSION = "p0-controlled-eval/1"


def file_sha256(path: str, chunk_size: int = 1 << 20) -> Optional[str]:
    """SHA-256 of a file, or None if it is unreadable.

    Used for the config and the checkpoint.  A metric without a checkpoint hash
    cannot be traced back to the weights that produced it, which is exactly the
    state the legacy 0.3927 / 0.3918 numbers are in.
    """
    if not path or not os.path.isfile(path):
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


class EnsembleWriter:
    """Incrementally append `(N, M, T, H, W)` predictions and `(N, T, H, W)` truth."""

    def __init__(
        self,
        path: str,
        member_count: int,
        output_length: int,
        height: int,
        width: int,
        dtype: str = "float32",
        compression: Optional[str] = "lzf",
        manifest: Optional[Dict[str, Any]] = None,
    ):
        if dtype not in ("float16", "float32"):
            raise ValueError(f"dtype must be float16 or float32, got {dtype!r}")
        directory = os.path.dirname(os.path.abspath(path))
        if directory:
            os.makedirs(directory, exist_ok=True)

        self.path = path
        self.dtype = np.dtype(dtype)
        self.member_count = int(member_count)
        self.output_length = int(output_length)
        self.written = 0

        self._handle = h5py.File(path, "w")
        self._predictions = self._handle.create_dataset(
            "predictions",
            shape=(0, member_count, output_length, height, width),
            maxshape=(None, member_count, output_length, height, width),
            chunks=(1, member_count, output_length, height, width),
            dtype=self.dtype,
            compression=compression,
        )
        self._truth = self._handle.create_dataset(
            "truth",
            shape=(0, output_length, height, width),
            maxshape=(None, output_length, height, width),
            chunks=(1, output_length, height, width),
            dtype=self.dtype,
            compression=compression,
        )
        self._event_index = self._handle.create_dataset(
            "event_index",
            shape=(0,),
            maxshape=(None,),
            dtype=np.int64,
        )
        self.manifest = dict(manifest or {})
        self.manifest.setdefault("schema_version", SCHEMA_VERSION)
        self._flush_manifest()

    def _flush_manifest(self) -> None:
        self._handle.attrs[MANIFEST_ATTR] = json.dumps(
            self.manifest, indent=2, sort_keys=True, default=str
        )

    def append(self, predictions: np.ndarray, truth: np.ndarray) -> None:
        """Append one chunk. Shapes `(n, M, T, H, W)` and `(n, T, H, W)`."""
        if predictions.ndim != 5 or truth.ndim != 4:
            raise ValueError(
                "expected predictions (n, M, T, H, W) and truth (n, T, H, W), got "
                f"{predictions.shape} and {truth.shape}"
            )
        if predictions.shape[0] != truth.shape[0]:
            raise ValueError(
                f"batch mismatch: {predictions.shape[0]} predictions vs "
                f"{truth.shape[0]} truth"
            )
        if predictions.shape[1] != self.member_count:
            raise ValueError(
                f"expected {self.member_count} members, got {predictions.shape[1]}"
            )

        count = predictions.shape[0]
        start, stop = self.written, self.written + count
        self._predictions.resize(stop, axis=0)
        self._truth.resize(stop, axis=0)
        self._event_index.resize(stop, axis=0)
        self._predictions[start:stop] = predictions.astype(self.dtype, copy=False)
        self._truth[start:stop] = truth.astype(self.dtype, copy=False)
        self._event_index[start:stop] = np.arange(start, stop, dtype=np.int64)
        self.written = stop

    def close(self, extra_manifest: Optional[Dict[str, Any]] = None) -> None:
        if extra_manifest:
            self.manifest.update(extra_manifest)
        self.manifest["event_count"] = self.written
        # Hash the arrays themselves so a later re-score can prove it read the
        # same bytes, independent of filename or mtime.
        self.manifest["predictions_sha256"] = _dataset_sha256(self._predictions)
        self.manifest["truth_sha256"] = _dataset_sha256(self._truth)
        self._flush_manifest()
        self._handle.close()

    def __enter__(self) -> "EnsembleWriter":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is None:
            self.close()
        else:
            self._handle.close()


def _dataset_sha256(dataset: h5py.Dataset, events_per_block: int = 32) -> str:
    digest = hashlib.sha256()
    for start in range(0, dataset.shape[0], events_per_block):
        digest.update(np.ascontiguousarray(dataset[start : start + events_per_block]).tobytes())
    return digest.hexdigest()


def read_manifest(path: str) -> Dict[str, Any]:
    with h5py.File(path, "r") as handle:
        raw = handle.attrs.get(MANIFEST_ATTR)
        return json.loads(raw) if raw else {}


def build_inference_manifest(
    config_path: str,
    checkpoint_path: Optional[str],
    dataset_name: str,
    pixel_scale: float,
    thresholds: Any,
    euler_steps: Any,
    member_count: int,
    batch_size: int,
    seed_mode: str,
    seed_base: int,
    prediction_dtype: str,
    crop: Optional[str],
    test_file: Optional[str] = None,
    test_meta: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Collect everything needed to reproduce or invalidate a scored run.

    Common-random-number comparisons across checkpoints are only valid if event
    order, batch size, member count, seed rule, NFE, dtype and code version all
    match; recording them is what makes a later mismatch detectable rather than
    silently absorbed into the difference between two models.
    """
    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "config_path": config_path,
        "config_sha256": file_sha256(config_path),
        "checkpoint_path": checkpoint_path,
        "checkpoint_sha256": file_sha256(checkpoint_path) if checkpoint_path else None,
        "dataset_name": dataset_name,
        "pixel_scale": float(pixel_scale),
        "thresholds": list(thresholds),
        "euler_steps": euler_steps,
        "member_count": int(member_count),
        "batch_size": int(batch_size),
        "seed_mode": seed_mode,
        "seed_base": int(seed_base),
        "prediction_dtype": prediction_dtype,
        "crop": crop,
        "test_file": test_file,
        "test_meta": test_meta,
        "numpy_version": np.__version__,
    }
    try:
        import torch

        manifest["torch_version"] = torch.__version__
        manifest["cuda_version"] = torch.version.cuda
    except Exception:  # torch is always present in practice; never fail the run
        pass
    if extra:
        manifest.update(extra)
    return manifest
