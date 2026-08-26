"""Offline optical-flow cache for the motion-aligned UOT ground cost.

Why offline
-----------
The flow has to come from the *input* window and nothing else -- it is a
property of the event that is known at forecast time.  Computing it offline and
caching it makes that structural rather than a promise: no future frame is ever
opened by this tool, so the training loop cannot leak one no matter how it is
wired.  It also keeps the estimator (``skimage``'s TV-L1, the same one the WFR
mass-dynamics audit used) out of the training loop, where a CPU,
non-differentiable routine has no business being.

The cache is deterministic given the dataset, so a run is reproducible from the
file alone; the manifest records the estimator settings that produced it.

Sign convention (measured, not assumed)
---------------------------------------
``optical_flow_tvl1(reference, moving)`` returns the displacement that samples
``moving`` to reconstruct ``reference``, so the argument order decides the sign.
Measured on a blob translated +3 columns between two frames:

    optical_flow_tvl1(frame[t+1], frame[t])  ->  dw = -3.007   (backward)
    optical_flow_tvl1(frame[t],   frame[t+1]) ->  dw = +3.008   (forward)

This module wants the **forward** motion, so it calls ``(earlier, later)``.
Note the WFR mass-dynamics audit uses the other order -- correctly, because it
warps ``t`` onto ``t+1`` -- so the two tools are not interchangeable.

(The flow-aligned metric ``M = I - s*u*u^T`` happens to be invariant under
``u -> -u``, so this sign does not change the current ground cost.  It is fixed
anyway: the cache is a reusable artefact and anything that advects with it --
semi-Lagrangian warping, say -- would silently go backwards.)

Output: ``(N, 2, H, W)`` float16, channel order ``(dh, dw)``, pixels per frame
interval -- the unit ``MotionCostConfig`` expects, since the UOT coordinate grid
is scaled to original-pixel units.
"""

import argparse
import json
import os
import sys
from typing import Tuple

import h5py
import numpy as np

sys.path.append(os.getcwd())

DEFAULT_ATTACHMENT = 5.0
DEFAULT_TIGHTNESS = 0.3
DEFAULT_NUM_WARP = 3


def _flow_pair(a: np.ndarray, b: np.ndarray, attachment, tightness, num_warp):
    """Forward motion from ``a`` to ``b`` (both 2-D, same shape).

    Argument order is the sign convention -- see the module docstring; it was
    settled by measurement, and the unit tests pin it.
    """
    from skimage.registration import optical_flow_tvl1

    v, u = optical_flow_tvl1(
        a, b, attachment=attachment, tightness=tightness, num_warp=num_warp
    )
    return np.stack([v, u], axis=0)


def sample_flow(
    frames: np.ndarray,
    n_pairs: int,
    attachment: float = DEFAULT_ATTACHMENT,
    tightness: float = DEFAULT_TIGHTNESS,
    num_warp: int = DEFAULT_NUM_WARP,
    dry_threshold: float = 1e-6,
    reject_speed: float = None,
) -> Tuple[np.ndarray, bool]:
    """Mean forward flow over the last ``n_pairs`` consecutive input frames.

    Averaging several pairs rather than trusting the last one: TV-L1 on a
    single radar pair is noisy, and a bad estimate here does not fail loudly --
    it quietly tilts the ground cost.  Returns ``(flow, ok)``; ``ok`` is False
    when the window is too empty for the estimate to mean anything, in which
    case the flow is zeros and the cost falls back to Euclidean for that sample
    (``M = I`` at zero flow, proved in the motion-cost tests).
    """
    if frames.ndim != 3 or frames.shape[0] < 2:
        raise ValueError(f"expected (T>=2, H, W) input window, got {frames.shape}")
    t = frames.shape[0]
    pairs = min(max(int(n_pairs), 1), t - 1)
    start = t - 1 - pairs

    if float(np.abs(frames[start:]).max()) <= dry_threshold:
        return np.zeros((2, *frames.shape[1:]), dtype=np.float32), False

    acc = np.zeros((2, *frames.shape[1:]), dtype=np.float64)
    for k in range(start, t - 1):
        acc += _flow_pair(
            frames[k].astype(np.float64), frames[k + 1].astype(np.float64),
            attachment, tightness, num_warp,
        )
    flow = (acc / pairs).astype(np.float32)
    if not np.isfinite(flow).all():
        return np.zeros_like(flow), False

    if reject_speed is not None:
        # Measured on CIKM validation: p50 2.7, p99 14.4, but max 122 px/frame
        # -- impossible on a 128 px domain, so those vectors are estimator
        # failures.  Clamping their *magnitude* would not help: saturation means
        # 15 px/frame already buys 96% of the discount, so a clamped outlier
        # still hands a near-full discount to a direction that is simply wrong.
        # An untrusted vector must therefore be dropped, not shortened -- zero
        # flow gives M = I, i.e. the plain Euclidean cost for those pixels.
        bad = np.linalg.norm(flow, axis=0) > float(reject_speed)
        if bad.any():
            flow = flow.copy()
            flow[:, bad] = 0.0
        if bad.all():
            return flow, False
    return flow, True


def read_input_window(handle, dataset: str, idx: int, input_length: int,
                      time_last: bool) -> np.ndarray:
    """``(T, H, W)`` input window for one sample.

    CIKM stores ``vil`` as ``(N, H, W, T)`` -- time on the *last* axis.  Slicing
    that as if it were ``(N, T, H, W)`` silently cuts along height instead and
    produces a flow estimated from image rows, which would look entirely
    plausible downstream.  Hence the explicit layout switch.
    """
    if time_last:
        frames = np.asarray(handle[dataset][idx, :, :, :input_length],
                            dtype=np.float32)
        frames = np.transpose(frames, (2, 0, 1))
    else:
        frames = np.asarray(handle[dataset][idx, :input_length], dtype=np.float32)
        if frames.ndim == 4:        # (T, C, H, W) with a singleton channel
            frames = frames[:, 0]
    return frames


def infer_time_last(shape) -> bool:
    """``(N, H, W, T)`` when the two middle axes match and the last differs."""
    return len(shape) == 4 and shape[1] == shape[2] and shape[3] != shape[1]


def _worker(args):
    (idx, path, dataset, input_length, n_pairs, atten, tight, warps, time_last,
     reject) = args
    with h5py.File(path, "r") as f:
        frames = read_input_window(f, dataset, idx, input_length, time_last)
    flow, ok = sample_flow(frames, n_pairs, atten, tight, warps,
                           reject_speed=reject)
    return idx, flow.astype(np.float16), ok


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="dataset HDF5")
    p.add_argument("--dataset", default="vil", help="key holding the frames")
    p.add_argument("--time-last", dest="time_last", action="store_true", default=None,
                   help="frames stored as (N,H,W,T); auto-detected when unset")
    p.add_argument("--time-first", dest="time_last", action="store_false")
    p.add_argument("--output", required=True, help="destination .h5 cache")
    p.add_argument("--input-length", type=int, default=5)
    p.add_argument("--n-pairs", type=int, default=2,
                   help="consecutive input pairs averaged (>=1)")
    p.add_argument("--attachment", type=float, default=DEFAULT_ATTACHMENT)
    p.add_argument("--tightness", type=float, default=DEFAULT_TIGHTNESS)
    p.add_argument("--num-warp", type=int, default=DEFAULT_NUM_WARP)
    p.add_argument("--reject-speed", type=float, default=None,
                   help="zero out flow vectors faster than this (px/frame); "
                        "untrusted estimates fall back to the Euclidean cost")
    p.add_argument("--max-samples", type=int, default=None)
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    p.add_argument("--progress-every", type=int, default=200)
    args = p.parse_args()

    with h5py.File(args.input, "r") as f:
        if args.dataset not in f:
            raise SystemExit(
                f"{args.dataset!r} not in {args.input}; keys = {list(f.keys())}"
            )
        shape = f[args.dataset].shape
    time_last = infer_time_last(shape) if args.time_last is None else args.time_last
    n_all = shape[0]
    n = n_all if args.max_samples is None else min(args.max_samples, n_all)
    hw = shape[1:3] if time_last else shape[-2:]
    print(f"{args.input}: {n_all} samples, dataset shape {tuple(shape)}, "
          f"time_last={time_last}, frame shape {tuple(hw)}; computing {n}", flush=True)

    out = np.zeros((n, 2, *hw), dtype=np.float16)
    ok_mask = np.zeros(n, dtype=bool)
    jobs = [
        (i, args.input, args.dataset, args.input_length, args.n_pairs,
         args.attachment, args.tightness, args.num_warp, time_last,
         args.reject_speed)
        for i in range(n)
    ]

    if args.workers > 1:
        import multiprocessing as mp
        with mp.Pool(args.workers) as pool:
            for done, (idx, flow, ok) in enumerate(
                pool.imap_unordered(_worker, jobs, chunksize=8), start=1
            ):
                out[idx], ok_mask[idx] = flow, ok
                if args.progress_every and done % args.progress_every == 0:
                    print(f"  {done}/{n}", flush=True)
    else:
        for done, job in enumerate(jobs, start=1):
            idx, flow, ok = _worker(job)
            out[idx], ok_mask[idx] = flow, ok
            if args.progress_every and done % args.progress_every == 0:
                print(f"  {done}/{n}", flush=True)

    speed = np.linalg.norm(out.astype(np.float32), axis=1)
    stats = {
        "n": int(n),
        "n_usable": int(ok_mask.sum()),
        "n_dry_or_bad": int((~ok_mask).sum()),
        "speed_mean": float(speed.mean()),
        "speed_p50": float(np.percentile(speed, 50)),
        "speed_p99": float(np.percentile(speed, 99)),
        "speed_max": float(speed.max()),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with h5py.File(args.output, "w") as f:
        f.create_dataset("flow", data=out, compression="gzip", compression_opts=4)
        f.create_dataset("usable", data=ok_mask)
        f.attrs["manifest"] = json.dumps({
            "source": os.path.abspath(args.input),
            "dataset": args.dataset,
            "input_length": args.input_length,
            "n_pairs": args.n_pairs,
            "estimator": "skimage.registration.optical_flow_tvl1",
            "attachment": args.attachment,
            "tightness": args.tightness,
            "num_warp": args.num_warp,
            "time_last": bool(time_last),
            "reject_speed": args.reject_speed,
            "channel_order": "(dh, dw) pixels per frame interval",
            "stats": stats,
        })
    print(json.dumps(stats, indent=2))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
