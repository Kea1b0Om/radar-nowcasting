#!/usr/bin/env python
"""External arm: NFE sweep on a frozen StormScope.

Measure only.  The model is never trained, never fine-tuned, never touched --
we sweep the sampler's step count and watch what happens to the ensemble.

Why this exists
---------------
Our own result -- deterministic scores are blind to a 2.5x step cut while
ensemble spread drops 41% -- currently rests on one backbone.  A reviewer can
answer it with "maybe that is your model".  Reproducing the same curve on a
third-party foundation model (NVIDIA StormScope, zero external evaluations as
of 2026-08-15) removes that answer.  It doubles as the no-distillation
step-reduction control the argument needs anyway.

Output contract
---------------
One HDF5 per NFE arm, laid out exactly as write_validation_ensemble.py, so
tools/score_gate_arms.py scores it unchanged:

    predictions  (N, M, T, H, W)  float32, dBZ
    truth        (N, T, H, W)     float32, dBZ

*** UNIT DISCIPLINE ***
StormScope emits dBZ in roughly [0, 75] directly.  Our own pipeline carries
dBZ * 255 / 90.  Do NOT route this through raw_to_eval_scale -- that helper
special-cases on dataset name and would silently rescale a dataset it has
never seen (this is the exact shape of the unit bug we already ate once).
score_event()'s thresholds (20/30/35/40) are dBZ, so raw output is already in
the right units.  The range assertion below is the guard.

Pairing across arms
-------------------
Arms share per-event, per-member INITIAL noise (one fixed seed stream).  With
S_churn > 0 the sampler also injects noise at every step, and a 4-step arm
cannot receive the same injections as a 100-step arm -- so arms are paired at
the event+member-init level, NOT bitwise.  Run --s-churn 0 for an arm that IS
exactly pairable (deterministic ODE, spread comes only from the shared initial
noise); that arm isolates the step count from the churn.  Deployment default
is S_churn=10, which is why it is the default here.

*** earth2studio surface ***
Confined to _Adapter.  Signatures read from the repo, not executed -- fix in
one place if the API has moved.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import time

import h5py
import numpy as np
import torch

CLEAR_SKY_DBZ = -10.0  # NOT 0 -- the one public third-party failure was 0-fill
DBZ_VALID = (-15.0, 80.0)


# --------------------------------------------------------------------------
class _Adapter:
    """Everything version-fragile."""

    SHAPES = {"6km_1hr": (512, 896), "3km_10min": (1024, 1792)}

    def __init__(self, variant: str, device: str):
        self.variant, self.device = variant, device
        self.h, self.w = self.SHAPES[variant]

    def load_model(self):
        from earth2studio.models.px import StormScopeGOES  # noqa: PLC0415

        pkg = StormScopeGOES.load_default_package()
        return StormScopeGOES.load_model(pkg).to(self.device).eval()

    def data_source(self):
        """GOES + MRMS, anonymous S3.

        scan_mode='C' is mandatory: the 'F' default is 6x the volume
        (18.8 vs 3.1 TB/yr) and the official example uses 'C'.
        """
        from earth2studio.data import GOES, MRMS  # noqa: PLC0415

        return {"goes": GOES(scan_mode="C"), "mrms": MRMS()}

    def build_conditioning(self, model, sources, time: dt.datetime):
        """Returns (cond, truth) -- cond (1,C,H,W), truth (T,H,W), both dBZ.

        conditioning_data_source=None keeps this on the pure-observation path
        (no ERA5 / z500), which the official 3km example uses.
        """
        return model.prepare_inputs(
            sources,
            time,
            conditioning_data_source=None,
        )

    @staticmethod
    def step(model, cond, num_steps, s_churn, generator):
        return model.sample(cond, num_steps=num_steps, S_churn=s_churn,
                            generator=generator)


# --------------------------------------------------------------------------
def weight_digest(model) -> str:
    h = hashlib.sha256()
    for name, p in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(p.detach().cpu().numpy().tobytes())
    return h.hexdigest()[:12]


def code_fingerprint() -> dict:
    out = {}
    for path in (__file__, "tools/score_gate_arms.py",
                 "common/metrics/ensemble_probabilistic.py"):
        try:
            with open(path, "rb") as fh:
                out[os.path.basename(path)] = hashlib.sha256(
                    fh.read()).hexdigest()[:12]
        except OSError:
            out[os.path.basename(path)] = "unavailable"
    return out


def rollout(ad, model, cond, n_frames, num_steps, s_churn, generator):
    """Autoregressive rollout -- each forward emits one timestep."""
    frames, c = [], cond
    for _ in range(n_frames):
        nxt = ad.step(model, c, num_steps, s_churn, generator)
        frames.append(nxt)
        c = nxt
    return torch.cat(frames, dim=0)  # (T, H, W) after squeeze downstream


def rank_histogram(members: np.ndarray, truth: np.ndarray, n_bins: int):
    """Where does truth fall among the sorted members?

    Flat = calibrated.  U-shaped = underdispersed.  score_gate_arms.py does
    not compute this and it is the metric the spread claim actually needs.
    members (M,T,H,W), truth (T,H,W).
    """
    below = (members < truth[None]).sum(axis=0)  # (T,H,W), values 0..M
    return np.bincount(below.ravel(), minlength=n_bins).astype(np.int64)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--variant", default="6km_1hr",
                   choices=["6km_1hr", "3km_10min"])
    p.add_argument("--nfe", nargs="+", type=int, default=[100, 50, 20, 10, 4])
    p.add_argument("--members", type=int, default=8)
    p.add_argument("--frames", type=int, default=4, help="rollout length T")
    p.add_argument("--times-file", required=True,
                   help="one ISO timestamp per line; 2024 only (2025 crosses "
                        "GOES-16 -> GOES-19 at day 097)")
    p.add_argument("--s-churn", type=float, default=10.0,
                   help="10 = deployment. Use 0 for the exactly-pairable arm.")
    p.add_argument("--min-frac-ge30", type=float, default=0.005,
                   help="skip events too dry to carry a tail")
    p.add_argument("--seed", type=int, default=1000)
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--out-dir", default="audit_outputs/stormscope/nfe")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    ad = _Adapter(args.variant, args.device)

    with open(args.times_file) as fh:
        times = [dt.datetime.fromisoformat(l.strip())
                 for l in fh if l.strip() and not l.startswith("#")]
    if args.limit:
        times = times[: args.limit]
    for t in times:
        if t.year != 2024:
            raise SystemExit(f"{t}: use 2024 only (pure GOES-16). "
                             "2025 crosses satellites at day 097.")

    print(f"loading {args.variant} ...", flush=True)
    model = ad.load_model()
    digest_before = weight_digest(model)
    sources = ad.data_source()
    print(f"weight digest {digest_before}", flush=True)

    # ---- shared noise: one stream, replayed identically for every arm ----
    # Drawn on CPU so the arms are reproducible across devices.
    noise_seeds = [[args.seed + 977 * i + m for m in range(args.members)]
                   for i in range(len(times))]

    # ---- stage 0: no-op check ----------------------------------------------
    # Same arm twice with the same seeds must be bitwise identical.  This only
    # holds at S_churn=0; at S_churn>0 it is expected to differ and we say so
    # rather than silently skipping the check.
    if args.s_churn == 0.0:
        print("stage0: replaying arm nfe=%d twice ..." % args.nfe[0], flush=True)
        cond0, _ = ad.build_conditioning(model, sources, times[0])
        g1 = torch.Generator(device=args.device).manual_seed(noise_seeds[0][0])
        g2 = torch.Generator(device=args.device).manual_seed(noise_seeds[0][0])
        with torch.no_grad():
            a = rollout(ad, model, cond0, args.frames, args.nfe[0], 0.0, g1)
            b = rollout(ad, model, cond0, args.frames, args.nfe[0], 0.0, g2)
        delta = float((a - b).abs().max())
        print(f"stage0 max|a-b| = {delta:.6g} (must be 0.0)", flush=True)
        if delta != 0.0:
            raise SystemExit("stage0 FAILED: sampler is not reproducible at "
                             "S_churn=0; arms cannot be paired.")
    else:
        print(f"stage0 skipped: S_churn={args.s_churn} > 0, arms are paired at "
              "event+member-init level only (see module docstring).", flush=True)

    # ---- sweep -------------------------------------------------------------
    manifest = {
        "variant": args.variant, "nfe": args.nfe, "members": args.members,
        "frames": args.frames, "s_churn": args.s_churn, "seed": args.seed,
        "weight_digest_before": digest_before,
        "code_fingerprint": code_fingerprint(),
        "clear_sky_fill_dbz": CLEAR_SKY_DBZ,
        "unit_note": "raw dBZ, NOT scaled by 255/90; do not use raw_to_eval_scale",
        "arms": {},
    }

    truth_cache, kept_idx = {}, []
    for arm_i, nfe in enumerate(args.nfe):
        path = os.path.join(args.out_dir, f"nfe{nfe:03d}.h5")
        preds_all, truth_all, ranks = [], [], np.zeros(args.members + 1, np.int64)
        t_arm = time.perf_counter()

        for i, when in enumerate(times):
            if arm_i == 0:
                cond, truth = ad.build_conditioning(model, sources, when)
                truth = truth.detach().cpu().numpy().astype(np.float32)
                frac = float((truth >= 30.0).mean())
                if frac < args.min_frac_ge30:
                    print(f"  skip {when} (frac>=30dBZ {frac:.4f})", flush=True)
                    continue
                truth_cache[i] = (cond, truth)
                kept_idx.append(i)
            elif i not in truth_cache:
                continue
            cond, truth = truth_cache[i]

            members = []
            for m in range(args.members):
                g = torch.Generator(device=args.device).manual_seed(
                    noise_seeds[i][m])
                with torch.no_grad():
                    seq = rollout(ad, model, cond, args.frames, nfe,
                                  args.s_churn, g)
                members.append(seq.squeeze().detach().cpu().numpy())
            mem = np.stack(members).astype(np.float32)  # (M,T,H,W)

            lo, hi = float(mem.min()), float(mem.max())
            if not (DBZ_VALID[0] <= lo and hi <= DBZ_VALID[1]):
                raise SystemExit(
                    f"output range [{lo:.1f},{hi:.1f}] outside dBZ "
                    f"{DBZ_VALID} -- units are wrong, refusing to write a dump "
                    "score_gate_arms.py would misread.")

            preds_all.append(mem)
            truth_all.append(truth)
            ranks += rank_histogram(mem, truth, args.members + 1)
            print(f"  nfe={nfe} event {when} done", flush=True)

        if not preds_all:
            raise SystemExit("no events survived the wet-enough filter")

        with h5py.File(path, "w") as fh:
            fh.create_dataset("predictions", data=np.stack(preds_all),
                              compression="gzip", compression_opts=1)
            fh.create_dataset("truth", data=np.stack(truth_all),
                              compression="gzip", compression_opts=1)
            fh.attrs["units"] = "dBZ"
            fh.attrs["nfe"] = nfe
            fh.attrs["s_churn"] = args.s_churn
        np.savez(os.path.join(args.out_dir, f"rankhist_nfe{nfe:03d}.npz"),
                 counts=ranks, n_members=args.members)

        elapsed = time.perf_counter() - t_arm
        manifest["arms"][f"nfe{nfe:03d}"] = {
            "h5": path, "n_events": len(preds_all), "seconds": round(elapsed, 1),
            "rank_hist": ranks.tolist(),
        }
        print(f"arm nfe={nfe}: {len(preds_all)} events, {elapsed/60:.1f} min "
              f"-> {path}", flush=True)

    digest_after = weight_digest(model)
    manifest["weight_digest_after"] = digest_after
    if digest_after != digest_before:
        raise SystemExit("FATAL: frozen model changed during the sweep")
    manifest["events_kept"] = [times[i].isoformat() for i in kept_idx]
    try:
        manifest["git_head"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:  # noqa: BLE001 - workspace is not a git repo
        manifest["git_head"] = "not-a-git-repo"

    with open(os.path.join(args.out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)

    ref = f"nfe{max(args.nfe):03d}"
    arms = " ".join(f"{k}={v['h5']}" for k, v in manifest["arms"].items())
    print("\nscore with:\n"
          f"  python tools/score_gate_arms.py --arms {arms} \\\n"
          f"    --reference {ref} --input-length {args.frames // 2} \\\n"
          f"    --output-dir {args.out_dir}/scores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
