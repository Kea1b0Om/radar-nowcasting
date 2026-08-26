#!/usr/bin/env python3
"""SYNTHETIC LOWER-BOUND smoke.  NOT the gate for a real run.

This builds three STDiT copies (student, evaluation EMA, frozen teacher) plus
a plain AdamW and drives them with random latents.  What it does NOT include:

  * the distributed process group and DDP gradient buckets,
  * the frozen UOT autoencoder's parameters,
  * the decoder activations the UOT term keeps alive for backward,
  * the Sinkhorn intermediates,
  * the real dataloader's pinned host buffers.

So its number is a floor, not a peak: passing here does not show that the real
recipe fits.  Use it only for a quick "does the wiring hold together" check,
e.g. on a laptop.

**The actual gate is the real trainer:**

    torchrun --nproc_per_node=3 \
      experiments/sevir/runner/flowcast/dist_train_flowcast.py \
      --config experiments/cikm/runner/flowcast/flowcast_config_rmlf_r2.yaml \
      --smoke_batches 10

which runs the full path -- parent load, DDP, evaluation EMA, frozen teacher,
frozen UOT autoencoder, decode + Sinkhorn, AdamW, bridge, backward -- reports
peak allocated/reserved reduced over ranks, refuses to pass if no batch was
rollout-conditioned, and exits without checkpointing or validating.  To force
the worst-case single-batch peak, temporarily set

    rmlf_params:
      rollout_probability: 1.0
      warmup_steps: 0

for the smoke only.

IF THE REAL SMOKE OOMs, do not "fix" it by weakening the experiment: reverting
R1 to a 4-step teacher, reusing the co-evolving evaluation EMA as the rollout
teacher, or dropping the frozen-teacher constraint each redefine what is being
measured.  Change model residency or how the evaluation EMA is stored instead.

    python tools/smoke_rmlf_memory_lower_bound.py \
      --config experiments/cikm/runner/flowcast/flowcast_config_rmlf_r2.yaml \
      --steps 10
"""

from __future__ import annotations

import argparse
import os
import sys

import torch
from omegaconf import OmegaConf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.models.flowcast.chunked_training import compute_chunked_rflow_loss
from common.models.flowcast.rf_stdit import FlowCastSTDiTWrapper
from common.models.flowcast.rmlf import (
    RMLFController,
    freeze_module,
    rmlf_config_from_mapping,
)


def build_model(config, latent_channels, device):
    model = FlowCastSTDiTWrapper(
        latent_channels=latent_channels,
        hidden_size=int(OmegaConf.select(config, "stdit.hidden_size")),
        depth=int(OmegaConf.select(config, "stdit.depth")),
        num_heads=int(OmegaConf.select(config, "stdit.num_heads")),
        patch_size=tuple(OmegaConf.select(config, "stdit.patch_size")),
        mlp_ratio=float(OmegaConf.select(config, "stdit.mlp_ratio", default=4.0)),
        drop_path=float(OmegaConf.select(config, "stdit.drop_path", default=0.0)),
        qk_norm=bool(OmegaConf.select(config, "stdit.qk_norm", default=True)),
        mean=0.0,
        std=1.0,
    )
    return model.to(device)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--latent_channels", type=int, default=4)
    parser.add_argument("--latent_hw", type=int, default=16)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    device = torch.device(args.device)
    if device.type != "cuda":
        print("WARNING: not CUDA; this reports nothing about GPU residency.")

    config = OmegaConf.load(args.config)
    batch = int(OmegaConf.select(config, "training_params.micro_batch_size"))
    input_length = int(OmegaConf.select(config, "data_params.input_length"))
    output_length = int(OmegaConf.select(config, "data_params.output_length"))
    num_train_timesteps = int(
        OmegaConf.select(config, "rflow_params.num_train_timesteps")
    )
    use_fp16 = bool(OmegaConf.select(config, "training_params.fp16", default=False))

    node = OmegaConf.select(config, "rmlf_params", default=None)
    rmlf_config = rmlf_config_from_mapping(
        None if node is None else OmegaConf.to_container(node, resolve=True)
    )
    controller = RMLFController(rmlf_config) if rmlf_config.enabled else None

    student = build_model(config, args.latent_channels, device)
    eval_ema = build_model(config, args.latent_channels, device)
    teacher = None
    if rmlf_config.enabled:
        teacher = freeze_module(build_model(config, args.latent_channels, device))

    params = sum(p.numel() for p in student.parameters())
    resident = 2 + (1 if teacher is not None else 0)
    print(
        "NOTE: synthetic lower bound -- no DDP buckets, no UOT autoencoder, no\n"
        "      decoder activations, no Sinkhorn.  The real gate is\n"
        "      dist_train_flowcast.py --smoke_batches 10.\n"
        f"config={args.config}\n"
        f"  parameters/model : {params/1e6:.1f}M\n"
        f"  resident models  : {resident} "
        f"(student, eval EMA{', frozen teacher' if teacher is not None else ''})\n"
        f"  rmlf enabled     : {rmlf_config.enabled} "
        f"(coupling={rmlf_config.coupling_mode}, "
        f"bridge_steps={rmlf_config.bridge_euler_steps})\n"
        f"  fp16 autocast    : {use_fp16}"
    )

    optimizer = torch.optim.AdamW(
        student.parameters(),
        lr=float(OmegaConf.select(config, "optimizer_params.learning_rate")),
    )
    scaler = torch.amp.GradScaler(device.type, enabled=use_fp16)

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)

    shape = (batch, input_length, args.latent_hw, args.latent_hw, args.latent_channels)
    out_shape = (batch, output_length) + shape[2:]

    class _Identity:
        @staticmethod
        def normalize(x):
            return x

    rollout_batches = 0
    # `global_step` starts past the warmup anchor so the bridge actually fires;
    # a smoke test that never rolls out measures the wrong thing.
    global_step = int(rmlf_config.warmup_start_global_step) + int(
        rmlf_config.warmup_steps
    )
    for step in range(args.steps):
        inputs = torch.randn(shape, device=device)
        outputs = torch.randn(out_shape, device=device)
        with torch.amp.autocast(device_type=device.type, enabled=use_fp16):
            loss, _, stats = compute_chunked_rflow_loss(
                model_forward=student,
                normalizer_model=_Identity(),
                inputs=inputs,
                outputs=outputs,
                input_length=input_length,
                output_length=output_length,
                num_train_timesteps=num_train_timesteps,
                rmlf_controller=controller,
                rmlf_teacher=teacher,
                global_step=global_step + step,
                return_rmlf_stats=True,
            )
        optimizer.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        if stats and stats.get("rmlf_rollout_fraction", 0.0) > 0:
            rollout_batches += 1
        print(
            f"  step {step:2d} loss={float(loss):.4f} "
            f"rollout_fraction={(stats or {}).get('rmlf_rollout_fraction', 0.0):.2f}"
        )

    if device.type == "cuda":
        print(
            f"\npeak allocated : {torch.cuda.max_memory_allocated(device)/2**30:.2f} GiB\n"
            f"peak reserved  : {torch.cuda.max_memory_reserved(device)/2**30:.2f} GiB"
        )
    if rmlf_config.enabled and rollout_batches == 0:
        raise SystemExit(
            "No batch was rollout-conditioned, so the teacher bridge never ran "
            "and this smoke test did not measure the arm's real peak memory."
        )
    print(f"rollout-conditioned batches: {rollout_batches}/{args.steps}")


if __name__ == "__main__":
    main()
