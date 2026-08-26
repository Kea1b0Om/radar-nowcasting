"""Generate and save an S-member ensemble on a chosen split, EnsembleWriter layout.

Purpose: produce the input for ``tools/calibrate_band_spread.py`` (and any
other offline ensemble analysis) from a frozen checkpoint, WITHOUT touching
any production file.  The sampling protocol replicates
``experiments/sevir/runner/flowcast/test_flowcast.py`` step by step:

* per-member seeding: ``torch.manual_seed(batch_idx * S + member)`` +
  ``cuda.manual_seed_all``, then ``autoregressive_sample(generator=None)`` --
  the exact production convention, so saved members are what the legacy
  runner would have produced on this file (note: streams depend on the batch
  size; it is recorded in the manifest);
* conditioning: ``/255`` when the AE is normalized, ``latent_dist.mode()``,
  permute to ``(B, T, h, w, c)``, ``model.normalize``;
* output view: decode -> ``decoded_to_eval_scale`` -> CIKM crop ``13:-14``
  -> clamp ``[0, pixel_scale]`` -> float16, i.e. the metric view documented
  in ``common/evaluation/ensemble_h5``.

Typical run (server, single spare GPU):

    CUDA_VISIBLE_DEVICES=3 python tools/write_validation_ensemble.py \
        --config experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml \
        --checkpoint artifacts/cikm/flowcast/teacher_v4.pt \
        --test-file datasets/cikm/data/cikm_full/nowcast_validation_full.h5 \
        --test-meta datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv \
        --output audit_outputs/controlled_eval/v4_validation_members.h5 \
        --split-label validation
"""

import argparse
import hashlib
import os
import sys

import numpy as np
import torch
from omegaconf import OmegaConf
from torch.utils.data import DataLoader, Subset

sys.path.append(os.getcwd())

from common.evaluation.ensemble_h5 import EnsembleWriter
from common.models.flowcast.gated_rollout import (
    BandGate,
    SpreadToAlpha,
    build_codec_fns,
    gated_autoregressive_ensemble,
)
from common.models.flowcast.rf_stdit import (
    FlowCastSTDiTWrapper,
    autoregressive_sample,
)
from experiments.sevir.dataset.sevirfulldataset import (
    DynamicSequentialSevirDataset,
    dynamic_sequential_collate,
)


def sha256_head(path: str, blocks: int = 256) -> str:
    """Hash of the first ``blocks`` MiB: enough to fingerprint a checkpoint
    without reading 4.7 GB twice."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for _ in range(blocks):
            chunk = f.read(1 << 20)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--checkpoint", required=True, help="Direct .pt path.")
    parser.add_argument("--test-file", required=True)
    parser.add_argument("--test-meta", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--split-label", default="validation")
    parser.add_argument("--max-events", type=int, default=None)
    parser.add_argument(
        "--start-batch", type=int, default=0,
        help="Global batch index to start at (multi-GPU sharding). Seeds use "
        "the GLOBAL batch index, so sharded output is bitwise identical to "
        "the single-process run over the same events.",
    )
    parser.add_argument(
        "--end-batch", type=int, default=None,
        help="Global batch index to stop before (exclusive).",
    )
    parser.add_argument("--members", type=int, default=None,
                        help="Override test_params.probabilistic_samples.")
    parser.add_argument(
        "--euler-steps", type=int, default=None,
        help="Override the sampler's step count. None keeps the config value, "
        "so every existing invocation is bitwise unchanged. Needed to evaluate "
        "a few-step distilled student, whose step count is a property of the "
        "checkpoint rather than of the config it was trained under. The value "
        "actually used is recorded in the manifest.",
    )
    parser.add_argument("--dtype", default="float16", choices=["float16", "float32"])
    parser.add_argument(
        "--gate-mode", default="none",
        choices=["none", "uniform", "graded", "calibrated"],
        help="none: production sampler (bitwise baseline). uniform: constant "
        "alpha on every gated band (dose-response probe). graded: per-band "
        "constant alphas from --graded-alphas (the no-ensemble competitor). "
        "calibrated: spread-driven gate from --calibration-report.",
    )
    parser.add_argument("--uniform-alpha", type=float, default=None)
    parser.add_argument("--graded-alphas", type=float, nargs="+", default=None,
                        help="Per-band alphas for bands 1..J-1 (band 0 protected).")
    parser.add_argument("--calibration-report", default=None)
    parser.add_argument("--alpha-min", type=float, default=0.3)
    parser.add_argument("--subsample-stride", type=int, default=1,
                        help="Keep every k-th event (cheap probes).")
    parser.add_argument(
        "--sde-noise-scale", type=float, default=None,
        help="Exploration knob kappa for the marginal-preserving SDE sampler. "
        "None or 0 is the production deterministic sampler, bitwise (and it "
        "draws no extra RNG, so a kappa=0 arm reproduces a stored baseline). "
        "kappa>0 widens within-group sample diversity at fixed marginals to "
        "first order in the step size.",
    )
    parser.add_argument(
        "--sde-uncompensated", action="store_true",
        help="Drop the drift compensation, injecting noise bare. Deliberately "
        "off-distribution: this is the only setting that actually widens the "
        "terminal spread, since the compensated form preserves every marginal.",
    )
    parser.add_argument(
        "--sde-final-step-noise", action="store_true",
        help="Also inject noise on the step landing at s=0. Off by default: "
        "that noise has no remaining step to absorb it and would confound "
        "off-manifold damage with a wrong SDE.",
    )
    return parser.parse_args()


def build_gate(args, num_bands, crop_slices, pixel_scale):
    """Assemble the requested gate; None for the production baseline."""
    if args.gate_mode == "none":
        return None
    if args.gate_mode == "uniform":
        if args.uniform_alpha is None:
            raise ValueError("--uniform-alpha required for gate-mode=uniform")
        # q_hi just above 0 makes every positive spread saturate, so alpha is
        # exactly uniform_alpha on gated bands regardless of the spread value.
        mapping = SpreadToAlpha.from_calibration(
            q_lo=[0.0] * num_bands, q_hi=[1e-12] * num_bands,
            alpha_min=args.uniform_alpha, view_height=101, view_width=101,
        )
    elif args.gate_mode == "graded":
        if not args.graded_alphas or len(args.graded_alphas) != num_bands - 1:
            raise ValueError(
                f"--graded-alphas needs {num_bands - 1} values (bands 1..{num_bands-1})"
            )
        # encode a per-band constant by saturating each band at its own alpha:
        # alpha_j = alpha_min_j is not expressible with one alpha_min, so use a
        # degenerate-free trick: q_lo=0, q_hi=1e-12 saturates, and we scale the
        # per-band constant by folding it into a per-band mapping via active
        # bands plus a post-hoc multiply.  Simpler: use PrecomputedAlpha below.
        mapping = None
    else:
        import json
        with open(args.calibration_report) as f:
            report = json.load(f)
        mapping = SpreadToAlpha.from_report(report, alpha_min=args.alpha_min)

    if args.gate_mode == "graded":
        return GradedGate(args.graded_alphas, crop_slices, pixel_scale)
    return BandGate(
        spread_to_alpha=mapping,
        spread_view_crop=crop_slices,
        spread_view_clamp=(0.0, pixel_scale),
    )


class GradedGate(BandGate):
    """Fixed per-band alphas, no ensemble input at all.

    This is the competitor the calibration cannot beat by construction: if a
    static per-band attenuation profile matches the spread-driven gate, the
    "uncertainty signal" contributes nothing and only the spectral shaping
    does.  Implemented as a BandGate whose alpha ignores the members.
    """

    def __init__(self, alphas, crop_slices, pixel_scale):
        num_bands = len(alphas) + 1
        super().__init__(
            spread_to_alpha=SpreadToAlpha.identity(num_bands),
            spread_view_crop=crop_slices,
            spread_view_clamp=(0.0, pixel_scale),
        )
        self._fixed = [1.0] + list(alphas)

    def alpha_from_members(self, member_pixels):
        batch = member_pixels.shape[1]
        return torch.tensor(
            [self._fixed] * batch, dtype=torch.float64, device=member_pixels.device
        )


def main():
    args = parse_args()
    config = OmegaConf.load(args.config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    dataset_name = OmegaConf.select(config, "data_params.dataset_name", default="sevir")
    pixel_scale = OmegaConf.select(config, "evaluation_params.pixel_scale", default=255.0)
    batch_size = config.test_params.micro_batch_size
    members = args.members or config.test_params.probabilistic_samples
    batch_size_ae = config.test_params.batch_size_autoencoder
    input_length = OmegaConf.select(
        config, "data_params.input_length", default=config.data_params.lag_time
    )
    output_length = OmegaConf.select(
        config, "data_params.output_length", default=config.data_params.lead_time
    )
    num_train_timesteps = config.rflow_params.num_train_timesteps
    euler_steps = OmegaConf.select(
        config, "sampling_params.euler_steps", default=config.test_params.euler_steps
    )
    if args.euler_steps is not None:
        if args.euler_steps < 1:
            raise ValueError(f"--euler-steps must be >= 1, got {args.euler_steps}")
        euler_steps = args.euler_steps
    normalized_ae = config.autoencoder_params.normalized_autoencoder

    dataset = DynamicSequentialSevirDataset(
        meta_csv=args.test_meta,
        data_file=args.test_file,
        data_type=OmegaConf.select(config, "data_params.data_key", default="vil"),
        raw_seq_len=OmegaConf.select(config, "data_params.raw_seq_len", default=49),
        lag_time=input_length,
        lead_time=output_length,
        time_spacing=config.data_params.time_spacing,
        stride=OmegaConf.select(config, "data_params.stride", default=12),
        channel_last=False,
        debug_mode=False,
    )
    total_batches = (len(dataset) + batch_size - 1) // batch_size
    start_batch = args.start_batch
    end_batch = min(args.end_batch, total_batches) if args.end_batch else total_batches
    if not (0 <= start_batch < end_batch):
        raise ValueError(
            f"invalid shard [{start_batch}, {end_batch}) for {total_batches} batches"
        )
    if start_batch > 0 or end_batch < total_batches:
        first = start_batch * batch_size
        last = min(end_batch * batch_size, len(dataset))
        dataset = Subset(dataset, range(first, last))
    if args.subsample_stride > 1:
        # NOTE: subsampling changes which events land in a batch, hence the
        # per-batch seeds. A subsampled run is paired only with other runs
        # using the SAME stride.
        dataset = Subset(dataset, range(0, len(dataset), args.subsample_stride))
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=dynamic_sequential_collate,
        num_workers=2,
        pin_memory=True,
    )

    from diffusers.models.autoencoders import AutoencoderKL

    ae_model = AutoencoderKL(
        in_channels=1,
        out_channels=1,
        down_block_types=config.autoencoder_params.down_block_types,
        up_block_types=config.autoencoder_params.up_block_types,
        block_out_channels=config.autoencoder_params.block_out_channels,
        act_fn=config.autoencoder_params.act_fn,
        latent_channels=config.autoencoder_params.latent_channels,
        norm_num_groups=config.autoencoder_params.norm_num_groups,
        layers_per_block=config.autoencoder_params.layers_per_block,
    )
    ae_ckpt = torch.load(
        config.autoencoder_params.autoencoder_checkpoint, map_location=device
    )
    ae_state = {
        (k[len("module."):] if k.startswith("module.") else k): v
        for k, v in ae_ckpt["model_state_dict"].items()
    }
    ae_model.load_state_dict(ae_state)
    ae_model = ae_model.to(device).eval()

    checkpoint = torch.load(args.checkpoint, weights_only=False, map_location="cpu")
    model = FlowCastSTDiTWrapper(
        latent_channels=config.autoencoder_params.latent_channels,
        hidden_size=config.stdit.hidden_size,
        depth=config.stdit.depth,
        num_heads=config.stdit.num_heads,
        patch_size=tuple(config.stdit.patch_size),
        mlp_ratio=OmegaConf.select(config, "stdit.mlp_ratio", default=4.0),
        drop_path=OmegaConf.select(config, "stdit.drop_path", default=0.0),
        qk_norm=OmegaConf.select(config, "stdit.qk_norm", default=True),
        mean=checkpoint.get("mean", 0.0),
        std=checkpoint.get("std", 1.0),
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device).eval()

    is_cikm = dataset_name == "cikm"
    crop_slices = (slice(13, -14), slice(13, -14)) if is_cikm else None
    num_bands = 5
    gate = build_gate(args, num_bands, crop_slices, pixel_scale)
    decode_fn = encode_fn = None
    if gate is not None:
        decode_fn, encode_fn = build_codec_fns(
            ae_model, model, pixel_scale, normalized_ae
        )
        print(f"GATE ENABLED: mode={args.gate_mode}", flush=True)
    writer = None
    written = 0

    for local_idx, batch in enumerate(loader):
        idx = start_batch + local_idx  # GLOBAL batch index: seed protocol
        if args.max_events is not None and written >= args.max_events:
            break
        x_cond, x_true, _metadata = batch

        batch_events, channels, t_in, height, width = x_cond.shape
        x_cond = x_cond.permute(0, 2, 1, 3, 4).reshape(
            batch_events * t_in, channels, height, width
        )
        with torch.no_grad():
            x_cond = x_cond.to(device)
            if normalized_ae:
                x_cond = x_cond / 255.0
            x_cond = ae_model.encode(x_cond).latent_dist.mode()
        latent_c, latent_h, latent_w = x_cond.shape[1:]
        x_cond = x_cond.reshape(batch_events, t_in, latent_c, latent_h, latent_w)
        x_cond = x_cond.permute(0, 1, 3, 4, 2).contiguous()
        x_cond = model.normalize(x_cond)

        x_true = x_true.squeeze(1)
        if is_cikm:
            x_true = x_true[:, :, 13:-14, 13:-14]
        x_true = x_true.float() * (pixel_scale / 255.0)

        if gate is None:
            sample_predictions = []
            for sample_idx in range(members):
                seed = idx * members + sample_idx
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed_all(seed)
                with torch.no_grad():
                    pred = autoregressive_sample(
                        model=model,
                        initial_cond=x_cond,
                        input_length=input_length,
                        output_length=output_length,
                        num_train_timesteps=num_train_timesteps,
                        euler_steps=euler_steps,
                        sde_noise_scale=args.sde_noise_scale,
                        sde_final_step_noise=args.sde_final_step_noise,
                        sde_drift_compensation=not args.sde_uncompensated,
                    )
                    pred = model.denormalize(pred)
                sample_predictions.append(pred.unsqueeze(1))
            x_pred = torch.cat(sample_predictions, dim=1)  # (B, S, T, h, w, c)
        else:
            # Paired with the baseline: same per-member seeds, same streams.
            generators = []
            for sample_idx in range(members):
                seed = idx * members + sample_idx
                g = torch.Generator(device=device).manual_seed(seed)
                generators.append(g)
            with torch.no_grad():
                stacked = gated_autoregressive_ensemble(
                    model=model, initial_cond=x_cond, num_members=members,
                    input_length=input_length, output_length=output_length,
                    num_train_timesteps=num_train_timesteps,
                    euler_steps=euler_steps, member_generators=generators,
                    gate=gate, decode_fn=decode_fn, encode_fn=encode_fn,
                    sde_noise_scale=args.sde_noise_scale,
                    sde_final_step_noise=args.sde_final_step_noise,
                    sde_drift_compensation=not args.sde_uncompensated,
                )
                stacked = model.denormalize(stacked)
            x_pred = stacked.permute(1, 0, 2, 3, 4, 5).contiguous()

        b, s, t_out = x_pred.shape[:3]
        x_pred = x_pred.reshape(b * s * t_out, *x_pred.shape[3:])
        x_pred = x_pred.permute(0, 3, 1, 2).contiguous()
        with torch.no_grad():
            decoded = []
            step = batch_size_ae or x_pred.shape[0]
            for i in range(0, x_pred.shape[0], step):
                decoded.append(ae_model.decode(x_pred[i : i + step]).sample)
            x_pred = torch.cat(decoded, dim=0)

        if normalized_ae:
            x_pred = x_pred * pixel_scale
        else:
            x_pred = x_pred * (pixel_scale / 255.0)
        if is_cikm:
            x_pred = x_pred[:, :, 13:-14, 13:-14]
        x_pred = x_pred.reshape(b, s, t_out, *x_pred.shape[-2:])
        x_pred = x_pred.clamp(0.0, pixel_scale).cpu().numpy()
        x_true = x_true.clamp(0.0, pixel_scale).cpu().numpy()

        if writer is None:
            height_out, width_out = x_true.shape[-2:]
            writer = EnsembleWriter(
                path=args.output,
                member_count=members,
                output_length=t_out,
                height=height_out,
                width=width_out,
                dtype=args.dtype,
                manifest={
                    "source": "tools/write_validation_ensemble.py",
                    "split": args.split_label,
                    "test_file": os.path.abspath(args.test_file),
                    "config": os.path.abspath(args.config),
                    "checkpoint": os.path.abspath(args.checkpoint),
                    "checkpoint_sha256_head": sha256_head(args.checkpoint),
                    "seed_protocol": "torch.manual_seed(global_batch_idx*S+member), generator=None",
                    "batch_size": int(batch_size),
                    "start_batch": int(start_batch),
                    "end_batch": int(end_batch),
                    "event_offset": int(start_batch * batch_size),
                    "members": int(members),
                    "euler_steps": int(euler_steps),
                    "num_train_timesteps": int(num_train_timesteps),
                    "pixel_scale": float(pixel_scale),
                    "crop": "13:-14" if is_cikm else None,
                    "clamp": [0.0, float(pixel_scale)],
                    "value_view": "metric (raw_to_eval_scale + crop + clamp)",
                    "gate_mode": args.gate_mode,
                    "uniform_alpha": args.uniform_alpha,
                    "graded_alphas": args.graded_alphas,
                    "calibration_report": args.calibration_report,
                    "alpha_min": args.alpha_min,
                    "subsample_stride": args.subsample_stride,
                    "sde_noise_scale": args.sde_noise_scale,
                    "sde_final_step_noise": bool(args.sde_final_step_noise),
                    "sde_drift_compensation": not bool(args.sde_uncompensated),
                },
            )
        take = batch_events
        if args.max_events is not None:
            take = min(take, args.max_events - written)
        writer.append(x_pred[:take], x_true[:take])
        written += take
        if idx % 10 == 0:
            print(f"batch {idx}: {written} events written", flush=True)

    if writer is None:
        raise RuntimeError("no events were written; empty dataset?")
    writer.close()
    print(f"done: {written} events -> {args.output}")


if __name__ == "__main__":
    main()
