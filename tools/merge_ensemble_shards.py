"""Merge event-sharded EnsembleWriter files into one, verifying continuity.

Companion to ``tools/write_validation_ensemble.py --start-batch/--end-batch``
(multi-GPU sharding).  Because shard seeds use the GLOBAL batch index, the
merged file is bitwise identical to a single-process run over the same
events; this tool's job is only to concatenate and to *prove* the shards
actually tile the event range with no gap, overlap, or protocol drift.

    python tools/merge_ensemble_shards.py \
        --inputs shard0.h5 shard1.h5 shard2.h5 shard3.h5 \
        --output v4_validation_members.h5
"""

import argparse
import json
import os
import sys

import h5py
import numpy as np

sys.path.append(os.getcwd())

from common.evaluation.ensemble_h5 import EnsembleWriter

# manifest keys that must agree across shards for the merge to be meaningful
PROTOCOL_KEYS = [
    "checkpoint_sha256_head",
    "seed_protocol",
    "batch_size",
    "members",
    "euler_steps",
    "num_train_timesteps",
    "pixel_scale",
    "crop",
    "clamp",
    "test_file",
    "split",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", required=True,
                        help="Shard files in event order.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--chunk-size", type=int, default=16)
    args = parser.parse_args()

    manifests = []
    for path in args.inputs:
        with h5py.File(path, "r") as handle:
            manifests.append(json.loads(handle.attrs["manifest_json"]))

    reference = manifests[0]
    for path, manifest in zip(args.inputs[1:], manifests[1:]):
        for key in PROTOCOL_KEYS:
            if manifest.get(key) != reference.get(key):
                raise ValueError(
                    f"shard {path} disagrees on {key!r}: "
                    f"{manifest.get(key)!r} vs {reference.get(key)!r}"
                )

    order = sorted(range(len(args.inputs)),
                   key=lambda i: manifests[i].get("event_offset", 0))
    writer = None
    written = 0
    for i in order:
        path = args.inputs[i]
        offset = manifests[i].get("event_offset", 0)
        if offset != written:
            raise ValueError(
                f"shard {path} starts at event {offset} but {written} events "
                "have been merged so far: gap or overlap between shards"
            )
        with h5py.File(path, "r") as handle:
            predictions = handle["predictions"]
            truth = handle["truth"]
            if writer is None:
                _, members, leads, height, width = predictions.shape
                writer = EnsembleWriter(
                    path=args.output,
                    member_count=members,
                    output_length=leads,
                    height=height,
                    width=width,
                    dtype=str(predictions.dtype),
                    manifest={
                        **reference,
                        "source": "tools/merge_ensemble_shards.py",
                        "merged_from": [os.path.abspath(p) for p in args.inputs],
                    },
                )
            for start in range(0, predictions.shape[0], args.chunk_size):
                stop = min(start + args.chunk_size, predictions.shape[0])
                writer.append(
                    np.asarray(predictions[start:stop]),
                    np.asarray(truth[start:stop]),
                )
                written += stop - start
        print(f"merged {path}: total {written} events", flush=True)

    if writer is None:
        raise RuntimeError("no shards merged")
    writer.close()
    print(f"done: {written} events -> {args.output}")


if __name__ == "__main__":
    main()
