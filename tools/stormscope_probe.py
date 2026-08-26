#!/usr/bin/env python
"""T1 gate: does StormScope load and run here, and at what cost?

Runs ONE forward pass per requested variant and reports peak VRAM and wall
clock.  Nothing downstream is worth starting until this prints numbers.

The 3km_10min peak-VRAM figure does not exist anywhere public (checked
2026-08-15) -- whatever this prints is a first-hand measurement.

NOTE ON THE earth2studio SURFACE
--------------------------------
Every call that touches earth2studio is confined to `_Adapter` below.  Those
signatures are taken from reading the repo, NOT from running it -- if the API
has moved, this is the only place to fix.  Everything else is plain torch.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, asdict

import torch


# --------------------------------------------------------------------------
# Everything version-fragile lives here.
# --------------------------------------------------------------------------
class _Adapter:
    """Thin wrapper over earth2studio's StormScope package."""

    VARIANTS = {
        # name -> (checkpoint subdir, expected spatial shape)
        "6km_1hr": ("6km_1hr", (512, 896)),
        "3km_10min": ("3km_10min", (1024, 1792)),
    }

    def __init__(self, variant: str, device: str):
        if variant not in self.VARIANTS:
            raise ValueError(f"unknown variant {variant!r}")
        self.variant = variant
        self.device = device
        self.subdir, self.expect_shape = self.VARIANTS[variant]

    def load(self):
        from earth2studio.models.px import StormScopeGOES  # noqa: PLC0415

        package = StormScopeGOES.load_default_package()
        model = StormScopeGOES.load_model(package)
        # 6km_1hr carries deprecated=true in registry.json but stormscope.py
        # only emits logger.warning -- loading is not blocked.
        return model.to(self.device).eval()

    @staticmethod
    def sample(model, cond, num_steps: int, s_churn: float, generator):
        """One denoising rollout step. Returns (B, C, H, W) in dBZ."""
        return model.sample(
            cond,
            num_steps=num_steps,
            S_churn=s_churn,
            generator=generator,
        )


@dataclass
class ProbeResult:
    variant: str
    ok: bool
    peak_vram_gb: float | None = None
    seconds_per_forward: float | None = None
    out_shape: tuple | None = None
    out_min_dbz: float | None = None
    out_max_dbz: float | None = None
    error: str | None = None


def probe(variant: str, num_steps: int, s_churn: float, device: str,
          seed: int) -> ProbeResult:
    ad = _Adapter(variant, device)
    try:
        model = ad.load()
    except Exception as exc:  # noqa: BLE001 - we want the message verbatim
        return ProbeResult(variant, ok=False, error=f"load failed: {exc!r}")

    h, w = ad.expect_shape
    # Synthetic conditioning of the right shape: this gate measures the cost
    # of the forward pass, not forecast quality, so real GOES/MRMS frames are
    # not needed yet.  -10 dBZ is the clear-sky fill value StormScope expects
    # (NOT 0 -- the one public third-party failure was traced to filling 0).
    try:
        n_in = int(getattr(model, "n_input_frames", 2))
        n_ch = int(getattr(model, "n_input_channels", 1))
    except Exception:  # noqa: BLE001
        n_in, n_ch = 2, 1
    cond = torch.full((1, n_ch * n_in, h, w), -10.0, device=device)

    if device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()

    gen = torch.Generator(device=device).manual_seed(seed)
    t0 = time.perf_counter()
    try:
        with torch.no_grad():
            out = ad.sample(model, cond, num_steps, s_churn, gen)
    except Exception as exc:  # noqa: BLE001
        return ProbeResult(variant, ok=False, error=f"sample failed: {exc!r}")
    if device.startswith("cuda"):
        torch.cuda.synchronize()
    dt = time.perf_counter() - t0

    peak = (torch.cuda.max_memory_allocated() / 2**30
            if device.startswith("cuda") else None)
    return ProbeResult(
        variant=variant,
        ok=True,
        peak_vram_gb=peak,
        seconds_per_forward=dt,
        out_shape=tuple(out.shape),
        out_min_dbz=float(out.min()),
        out_max_dbz=float(out.max()),
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--variants", nargs="+", default=["6km_1hr", "3km_10min"])
    p.add_argument("--num-steps", type=int, default=100,
                   help="deployment default is 100 (EDM)")
    p.add_argument("--s-churn", type=float, default=10.0,
                   help="deployment default is 10")
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--seed", type=int, default=1000)
    p.add_argument("--out", default="audit_outputs/stormscope/probe.json")
    args = p.parse_args()

    results = []
    for v in args.variants:
        print(f"--- probing {v} (num_steps={args.num_steps}, "
              f"S_churn={args.s_churn}) ---", flush=True)
        r = probe(v, args.num_steps, args.s_churn, args.device, args.seed)
        results.append(r)
        if r.ok:
            print(f"  peak VRAM      {r.peak_vram_gb:.2f} GB")
            print(f"  s / forward    {r.seconds_per_forward:.1f}")
            print(f"  out shape      {r.out_shape}")
            print(f"  out dBZ range  [{r.out_min_dbz:.1f}, {r.out_max_dbz:.1f}]")
            if not (-15.0 <= r.out_min_dbz and r.out_max_dbz <= 80.0):
                print("  !! dBZ out of [-15, 80] -- output is NOT raw dBZ, "
                      "do not feed score_gate_arms.py without rescaling")
        else:
            print(f"  FAILED: {r.error}")
        print(flush=True)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump({"num_steps": args.num_steps, "s_churn": args.s_churn,
                   "results": [asdict(r) for r in results]}, fh, indent=2)
    print(f"wrote {args.out}")

    any_ok = any(r.ok for r in results)
    if not any_ok:
        print("\nNO-GO: neither variant ran. Do not proceed to the sweep.")
    return 0 if any_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
