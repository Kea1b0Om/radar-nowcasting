"""Measured cost account for one Flow-GRPO step on this model and this box.

Everything here is timed on the real STDiT and the real VAE rather than
extrapolated from parameter counts, because the last back-of-envelope estimate
in this project ("1/1000 the compute") was wrong by three orders of magnitude
once measured.

A GRPO iteration has three cost centres, and they scale differently:

*   **rollout** - sample ``G`` trajectories per condition with no grad.
    ``chunks x euler_steps`` forwards per member.
*   **reward** - decode every member to pixels and score it.  Non-differentiable
    rewards mean no backward here, but the VAE forward is not free.
*   **policy update** - re-run the network *with* grad at the stored states to
    get ``log_prob``, then backward.  Full-trajectory training costs
    ``chunks x euler_steps`` forward+backward per member; Flow-GRPO-Fast
    subsamples this to 1-2 transitions, which is the whole reason it fits.

The script reports both regimes so the choice is made on numbers.
"""

import argparse
import json
import os
import sys
import time

import torch
from omegaconf import OmegaConf

sys.path.append(os.getcwd())

from common.models.flowcast.grpo import sde_step_with_logprob
from common.models.flowcast.rf_stdit import FlowCastSTDiTWrapper, make_chunk_index


def timed(fn, repeats, warmup=2):
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    start = time.perf_counter()
    for _ in range(repeats):
        fn()
    torch.cuda.synchronize()
    return (time.perf_counter() - start) / repeats


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    p.add_argument("--checkpoint", default=None,
                   help="Optional; timings are architecture-bound, not weight-bound.")
    p.add_argument("--group-sizes", type=int, nargs="+", default=[4, 8, 16])
    p.add_argument("--repeats", type=int, default=8)
    p.add_argument("--precision", default="bf16", choices=["fp32", "bf16", "fp16"])
    p.add_argument("--output", default=None)
    args = p.parse_args()

    config = OmegaConf.load(args.config)
    device = torch.device("cuda")
    dtype = {"fp32": torch.float32, "bf16": torch.bfloat16, "fp16": torch.float16}[
        args.precision
    ]

    input_length = OmegaConf.select(config, "data_params.input_length",
                                    default=config.data_params.lag_time)
    output_length = OmegaConf.select(config, "data_params.output_length",
                                     default=config.data_params.lead_time)
    euler_steps = OmegaConf.select(config, "sampling_params.euler_steps",
                                   default=config.test_params.euler_steps)
    num_chunks = output_length // input_length
    latent_c = config.autoencoder_params.latent_channels
    hp = config.stdit

    model = FlowCastSTDiTWrapper(
        latent_channels=latent_c, hidden_size=hp.hidden_size, depth=hp.depth,
        num_heads=hp.num_heads, patch_size=hp.patch_size,
    ).to(device=device)
    if args.checkpoint:
        state = torch.load(args.checkpoint, map_location="cpu")
        sd = state.get("model_state_dict", state)
        sd = {(k[len("module."):] if k.startswith("module.") else k): v for k, v in sd.items()}
        model.load_state_dict(sd, strict=False)
    n_params = sum(p.numel() for p in model.parameters())

    # latent grid: infer from the AE downsampling factor in the config
    down = 2 ** (len(config.autoencoder_params.block_out_channels) - 1)
    img = OmegaConf.select(config, "data_params.img_size", default=128)
    h = w = img // down
    dims_per_step = input_length * h * w * latent_c

    report = {
        "config": os.path.abspath(args.config),
        "precision": args.precision,
        "stdit_params_M": n_params / 1e6,
        "latent_grid": [input_length, h, w, latent_c],
        "dims_per_transition": dims_per_step,
        "euler_steps": euler_steps,
        "chunks": num_chunks,
        "transitions_per_trajectory": euler_steps * num_chunks,
        "gpu": torch.cuda.get_device_name(0),
        "group": {},
    }
    print(json.dumps({k: v for k, v in report.items() if k != "group"}, indent=1))

    for group in args.group_sizes:
        cond = torch.randn(group, input_length, h, w, latent_c, device=device, dtype=dtype)
        z = torch.randn_like(cond)
        t = torch.full((group,), 500, device=device, dtype=torch.long)
        chunk_index = make_chunk_index(group, 1, device)
        model_ = model.to(dtype=dtype)

        entry = {}
        try:
            torch.cuda.reset_peak_memory_stats()
            with torch.no_grad():
                fwd = timed(lambda: model_(z, t, cond, chunk_index), args.repeats)
            entry["forward_s"] = fwd
            entry["forward_peak_GiB"] = torch.cuda.max_memory_allocated() / 2**30

            def fwd_bwd():
                model_.zero_grad(set_to_none=True)
                v = model_(z, t, cond, chunk_index)
                _, logp, _, _ = sde_step_with_logprob(
                    z, v, 0.5, 0.4, kappa=0.9, prev_sample=z, reduction="mean"
                )
                logp.mean().backward()

            torch.cuda.reset_peak_memory_stats()
            fb = timed(fwd_bwd, args.repeats)
            entry["forward_backward_s"] = fb
            entry["forward_backward_peak_GiB"] = torch.cuda.max_memory_allocated() / 2**30

            trans = euler_steps * num_chunks
            entry["rollout_s_no_grad"] = fwd * trans
            entry["update_full_trajectory_s"] = fb * trans
            entry["update_fast_1_transition_s"] = fb * 1.0
            entry["update_fast_2_transitions_s"] = fb * 2.0
            entry["step_full_s"] = fwd * trans + fb * trans
            entry["step_fast2_s"] = fwd * trans + fb * 2.0
        except torch.cuda.OutOfMemoryError as exc:
            entry["oom"] = str(exc)[:200]
            torch.cuda.empty_cache()

        report["group"][str(group)] = entry
        print(f"\n--- group={group} ---")
        for k, v in entry.items():
            print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
        del cond, z
        torch.cuda.empty_cache()

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(f"\nreport: {args.output}")


if __name__ == "__main__":
    main()
