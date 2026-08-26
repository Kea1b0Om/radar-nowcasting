"""GTR stage-A probe: zero-training truncated-source arms on a frozen model.

Writes standard EnsembleWriter dumps for arms that bracket the ATFM/GTR
transplant question before any prior net is trained:

* ``control``      -- production sampler, full grid from pure noise.
* ``oracle_k{K}``  -- start at grid index K from the TRUE future latent noised
                      to that level.  Diagnostic ceiling (sees the answer):
                      measures pure truncation compatibility of the frozen
                      flow and the fidelity/diversity curve vs K.
* ``tmean_k{K}``   -- start at grid index K from the teacher's mean-forced
                      rollout latent noised to the level.  Zero-training proxy
                      for a learned Gaussian source's mean with the noise-floor
                      covariance s^2 I; a trained GTR prior can only improve
                      on it.  The anchor rollout conditions on its own mean
                      (mean-forced), a documented pilot approximation.

Members thread their per-chunk source draws through the AR rollout, so one
member = one source thread (time-consistent identity preserved).

Pre-registered readouts (scored downstream by score_gate_arms vs control):
spread/skill toward 1 with CRPS improving = the mechanism works; MSE blowing
up = off-manifold (the k200c signature); tmean ~= control at all K = the
anchor buys nothing and a learned prior must carry everything.
"""

import argparse
import os
import sys

import torch
from omegaconf import OmegaConf
from torch.utils.data import DataLoader, Subset

sys.path.append(os.getcwd())

from common.evaluation.ensemble_h5 import EnsembleWriter
from common.models.flowcast.gtr import (
    noise_to_level,
    truncated_autoregressive_sample,
)
from common.models.flowcast.rf_stdit import (
    FlowCastSTDiTWrapper,
    autoregressive_sample,
    sample_chunk_euler,
)
from common.models.flowcast.schedule import build_sampling_timesteps
from experiments.sevir.dataset.sevirfulldataset import (
    DynamicSequentialSevirDataset,
    dynamic_sequential_collate,
)

ARM_STREAM_OFFSET = {"oracle": 10_000_019, "tmean": 20_000_003}
ANCHOR_STREAM_BASE = 900_000_001


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--test-file", required=True)
    p.add_argument("--test-meta", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--split-label", default="validation")
    p.add_argument("--start-batch", type=int, default=0)
    p.add_argument("--end-batch", type=int, default=None)
    p.add_argument("--max-events", type=int, default=250)
    p.add_argument("--members", type=int, default=8)
    p.add_argument("--start-indices", type=int, nargs="+", default=[3, 5, 7],
                   help="Grid indices K into the production Euler grid; "
                        "s_trunc = timesteps[K]/(T-1). Larger K = later start "
                        "= less noise.")
    p.add_argument("--arms", nargs="+", default=["control", "oracle", "tmean"],
                   choices=["control", "oracle", "tmean"])
    p.add_argument("--anchor-samples", type=int, default=8,
                   help="Teacher draws per chunk for the mean-forced anchor.")
    p.add_argument("--dtype", default="float16", choices=["float16", "float32"])
    return p.parse_args()


def encode_frames(ae_model, model, frames, normalized_ae, device):
    """(B, 1, T, H, W) raw pixels -> normalized latent (B, T, h, w, c)."""
    b, ch, t, h, w = frames.shape
    flat = frames.permute(0, 2, 1, 3, 4).reshape(b * t, ch, h, w).to(device)
    with torch.no_grad():
        if normalized_ae:
            flat = flat / 255.0
        lat = ae_model.encode(flat).latent_dist.mode()
    lc, lh, lw = lat.shape[1:]
    lat = lat.reshape(b, t, lc, lh, lw).permute(0, 1, 3, 4, 2).contiguous()
    return model.normalize(lat)


def main():
    args = parse_args()
    config = OmegaConf.load(args.config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    dataset_name = OmegaConf.select(config, "data_params.dataset_name", default="sevir")
    pixel_scale = OmegaConf.select(config, "evaluation_params.pixel_scale", default=255.0)
    batch_size = config.test_params.micro_batch_size
    batch_size_ae = config.test_params.batch_size_autoencoder
    input_length = OmegaConf.select(
        config, "data_params.input_length", default=config.data_params.lag_time
    )
    output_length = OmegaConf.select(
        config, "data_params.output_length", default=config.data_params.lead_time
    )
    num_chunks = output_length // input_length
    T = config.rflow_params.num_train_timesteps
    euler_steps = OmegaConf.select(
        config, "sampling_params.euler_steps", default=config.test_params.euler_steps
    )
    normalized_ae = config.autoencoder_params.normalized_autoencoder
    members = args.members

    timesteps = build_sampling_timesteps(T, euler_steps, torch.device("cpu"))
    for k in args.start_indices:
        if not (0 < k < euler_steps):
            raise ValueError(f"start index {k} outside (0, {euler_steps})")
    s_levels = {k: float(timesteps[k].item()) / (T - 1) for k in args.start_indices}
    print(f"grid={timesteps.tolist()}  s_trunc={s_levels}", flush=True)

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
    if start_batch > 0 or end_batch < total_batches:
        first = start_batch * batch_size
        last = min(end_batch * batch_size, len(dataset))
        dataset = Subset(dataset, range(first, last))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False,
                        collate_fn=dynamic_sequential_collate, num_workers=2,
                        pin_memory=True)

    from diffusers.models.autoencoders import AutoencoderKL

    ae_model = AutoencoderKL(
        in_channels=1, out_channels=1,
        down_block_types=config.autoencoder_params.down_block_types,
        up_block_types=config.autoencoder_params.up_block_types,
        block_out_channels=config.autoencoder_params.block_out_channels,
        act_fn=config.autoencoder_params.act_fn,
        latent_channels=config.autoencoder_params.latent_channels,
        norm_num_groups=config.autoencoder_params.norm_num_groups,
        layers_per_block=config.autoencoder_params.layers_per_block,
    )
    ae_ckpt = torch.load(config.autoencoder_params.autoencoder_checkpoint,
                         map_location=device)
    ae_model.load_state_dict({
        (k[len("module."):] if k.startswith("module.") else k): v
        for k, v in ae_ckpt["model_state_dict"].items()
    })
    ae_model = ae_model.to(device).eval()

    ckpt = torch.load(args.checkpoint, weights_only=False, map_location="cpu")
    model = FlowCastSTDiTWrapper(
        latent_channels=config.autoencoder_params.latent_channels,
        hidden_size=config.stdit.hidden_size,
        depth=config.stdit.depth,
        num_heads=config.stdit.num_heads,
        patch_size=tuple(config.stdit.patch_size),
        mlp_ratio=OmegaConf.select(config, "stdit.mlp_ratio", default=4.0),
        drop_path=OmegaConf.select(config, "stdit.drop_path", default=0.0),
        qk_norm=OmegaConf.select(config, "stdit.qk_norm", default=True),
        mean=ckpt.get("mean", 0.0), std=ckpt.get("std", 1.0),
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(device).eval()

    is_cikm = dataset_name == "cikm"

    def decode_ensemble(latents):
        """(B, S, T, h, w, c) normalized latents -> (B, S, T, H, W) metric pixels."""
        b, s, t_out = latents.shape[:3]
        flat = model.denormalize(latents).reshape(b * s * t_out, *latents.shape[3:])
        flat = flat.permute(0, 3, 1, 2).contiguous()
        with torch.no_grad():
            outs = []
            step = batch_size_ae or flat.shape[0]
            for i in range(0, flat.shape[0], step):
                outs.append(ae_model.decode(flat[i:i + step]).sample)
        px = torch.cat(outs, dim=0)
        px = px * pixel_scale if normalized_ae else px * (pixel_scale / 255.0)
        if is_cikm:
            px = px[:, :, 13:-14, 13:-14]
        px = px.reshape(b, s, t_out, *px.shape[-2:])
        return px.clamp(0.0, pixel_scale).cpu().numpy()

    arm_names = []
    if "control" in args.arms:
        arm_names.append("control")
    for k in args.start_indices:
        for arm in ("oracle", "tmean"):
            if arm in args.arms:
                arm_names.append(f"{arm}_k{k}")
    writers = {}
    os.makedirs(args.output_dir, exist_ok=True)
    written = 0

    for local_idx, batch in enumerate(loader):
        idx = start_batch + local_idx
        if written >= args.max_events:
            break
        x_cond_raw, x_true_raw, _meta = batch
        x_cond = encode_frames(ae_model, model, x_cond_raw, normalized_ae, device)
        need_truth_lat = any(a.startswith("oracle") for a in arm_names)
        truth_lat = (encode_frames(ae_model, model, x_true_raw, normalized_ae, device)
                     if need_truth_lat else None)

        x_true = x_true_raw.squeeze(1)
        if is_cikm:
            x_true = x_true[:, :, 13:-14, 13:-14]
        x_true = (x_true.float() * (pixel_scale / 255.0)).clamp(0.0, pixel_scale)
        x_true = x_true.cpu().numpy()

        # ---- teacher mean-forced anchor rollout (shared by all tmean arms)
        anchor = None
        if any(a.startswith("tmean") for a in arm_names):
            anchor = []
            c = x_cond
            for chunk in range(1, num_chunks + 1):
                draws = []
                for g_i in range(args.anchor_samples):
                    g = torch.Generator(device=device).manual_seed(
                        ANCHOR_STREAM_BASE + idx * 1009 + chunk * 31 + g_i)
                    with torch.no_grad():
                        draws.append(sample_chunk_euler(
                            model, c, chunk, T, euler_steps, generator=g))
                mean_k = torch.stack(draws, dim=0).mean(dim=0)
                anchor.append(mean_k)
                c = mean_k

        preds = {}
        for name in arm_names:
            member_out = []
            for m in range(members):
                if name == "control":
                    seed = idx * members + m
                    torch.manual_seed(seed)
                    if torch.cuda.is_available():
                        torch.cuda.manual_seed_all(seed)
                    with torch.no_grad():
                        pred = autoregressive_sample(
                            model=model, initial_cond=x_cond,
                            input_length=input_length,
                            output_length=output_length,
                            num_train_timesteps=T, euler_steps=euler_steps)
                else:
                    arm, k_str = name.split("_k")
                    k = int(k_str)
                    t_start = int(timesteps[k].item())
                    g = torch.Generator(device=device).manual_seed(
                        ARM_STREAM_OFFSET[arm] + idx * members + m)

                    def source_fn(chunk_idx, cond, _arm=arm, _k=k,
                                  _t=t_start, _g=g):
                        target = (truth_lat[:, (chunk_idx - 1) * input_length:
                                            chunk_idx * input_length]
                                  if _arm == "oracle" else anchor[chunk_idx - 1])
                        eps = torch.randn(cond.shape, device=cond.device,
                                          dtype=cond.dtype, generator=_g)
                        return noise_to_level(target, eps, _t, T)

                    with torch.no_grad():
                        pred = truncated_autoregressive_sample(
                            model=model, initial_cond=x_cond,
                            input_length=input_length,
                            output_length=output_length,
                            num_train_timesteps=T, euler_steps=euler_steps,
                            start_index=k, source_fn=source_fn)
                member_out.append(pred.unsqueeze(1))
            preds[name] = torch.cat(member_out, dim=1)

        take = min(x_true.shape[0], args.max_events - written)
        for name in arm_names:
            px = decode_ensemble(preds[name])
            if name not in writers:
                h, w = x_true.shape[-2:]
                writers[name] = EnsembleWriter(
                    path=os.path.join(args.output_dir, f"{name}.h5"),
                    member_count=members, output_length=px.shape[2],
                    height=h, width=w, dtype=args.dtype,
                    manifest={
                        "source": "tools/gtr_probe.py", "arm": name,
                        "split": args.split_label,
                        "checkpoint": os.path.abspath(args.checkpoint),
                        "euler_steps": int(euler_steps),
                        "start_indices": list(args.start_indices),
                        "s_levels": {str(k): v for k, v in s_levels.items()},
                        "anchor_samples": int(args.anchor_samples),
                        "members": int(members),
                        "seed_protocol": "arm-offset generators; control uses "
                                         "torch.manual_seed(idx*S+m)",
                    })
            writers[name].append(px[:take], x_true[:take])
        written += take
        print(f"batch {idx}: {written}/{args.max_events} events", flush=True)

    for w in writers.values():
        w.close()
    print(f"done: {written} events x {len(arm_names)} arms -> {args.output_dir}")


if __name__ == "__main__":
    main()
