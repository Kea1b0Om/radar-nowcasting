"""Answer two questions about a live Shanghai run with ONE pass, read-only.

  Q1  Is partial_csi_m (which the trainer computes on the EMA weights, over a
      fixed 80-of-153 prefix, with fresh noise each epoch) understating the
      model? -> evaluate raw AND ema from the same checkpoint, on the FULL
      validation split, under a FIXED seed so the two see identical noise.

  Q2  How much does the chunked autoregression cost? Training conditions each
      5-frame chunk on the GROUND-TRUTH previous chunk, inference conditions
      it on its own prediction (rf_stdit.py: `cond = pred_chunk`). Shanghai's
      5->20 therefore crosses that teacher-forcing boundary 3 times, versus
      once for CIKM's 5->10. -> report CSI per 5-frame block: a healthy
      block 1 followed by a collapse in blocks 2-4 is the signature.

Read-only: loads a checkpoint, writes nothing but stdout. Safe to run against
the card a training job is using (uses ~6 GB).
"""

import argparse
import os
import sys

import h5py
import numpy as np
import torch

sys.path.insert(0, os.getcwd())

from omegaconf import OmegaConf  # noqa: E402

from common.models.flowcast.rf_stdit import autoregressive_sample  # noqa: E402


def build_models(config, device):
    """Rebuild STDiT + AE exactly as the runner does."""
    from diffusers import AutoencoderKL

    from common.models.flowcast.rf_stdit import RFSTDiT

    st = config.stdit
    ap = config.autoencoder_params
    model = RFSTDiT(
        input_size=(config.data_params.input_length, 16, 16),
        in_channels=ap.latent_channels,
        hidden_size=st.hidden_size,
        depth=st.depth,
        num_heads=st.num_heads,
        patch_size=tuple(st.patch_size),
        mlp_ratio=st.mlp_ratio,
        drop_path=st.drop_path,
        qk_norm=st.qk_norm,
    ).to(device)

    ae = AutoencoderKL(
        in_channels=1,
        out_channels=1,
        latent_channels=ap.latent_channels,
        norm_num_groups=ap.norm_num_groups,
        layers_per_block=ap.layers_per_block,
        act_fn=ap.act_fn,
        block_out_channels=list(ap.block_out_channels),
        down_block_types=list(ap.down_block_types),
        up_block_types=list(ap.up_block_types),
    )
    ck = torch.load(ap.autoencoder_checkpoint, map_location="cpu", weights_only=False)
    sd = ck.get("model_state_dict", ck)
    ae.load_state_dict({k.replace("module.", ""): v for k, v in sd.items()})
    return model, ae.eval().to(device)


def strip(sd):
    return {k.replace("module.", ""): v for k, v in sd.items()}


def csi_counts(gt, pred, thresholds):
    """Globally accumulated hits/misses/false alarms -- micro CSI, as in the runner."""
    out = {}
    for t in thresholds:
        g, p = gt >= t, pred >= t
        out[t] = (
            int((g & p).sum()),
            int((g & ~p).sum()),
            int((~g & p).sum()),
        )
    return out


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--config", required=True)
    ap_.add_argument("--checkpoint", required=True)
    ap_.add_argument("--latent-val", required=True)
    ap_.add_argument("--raw-val", required=True)
    ap_.add_argument("--events", type=int, default=153)
    ap_.add_argument("--batch", type=int, default=6)
    ap_.add_argument("--seed", type=int, default=1234)
    args = ap_.parse_args()

    device = torch.device("cuda")
    config = OmegaConf.load(args.config)
    thresholds = list(config.evaluation_params.thresholds)
    pixel_scale = float(config.evaluation_params.pixel_scale)
    in_len = config.data_params.input_length
    out_len = config.data_params.output_length

    model, ae = build_models(config, device)
    ck = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    print(f"checkpoint keys: {sorted(k for k in ck if 'state_dict' in k)}")
    print(f"  epoch={ck.get('epoch')} global_step={ck.get('global_step')}")

    variants = {}
    if "model_state_dict" in ck:
        variants["raw"] = ck["model_state_dict"]
    if "ema_model_state_dict" in ck:
        variants["ema"] = ck["ema_model_state_dict"]
    if not variants:
        raise SystemExit(f"no usable weights in {args.checkpoint}")

    with h5py.File(args.latent_val, "r") as f:
        lat = f["vil"][: args.events]          # (N,16,16,25,C)
    with h5py.File(args.raw_val, "r") as f:
        raw = f["vil"][: args.events]          # (N,128,128,25)
    n = lat.shape[0]
    print(f"evaluating {n} validation events, seed {args.seed}, S=1\n")

    n_blocks = out_len // in_len
    for name, sd in variants.items():
        model.load_state_dict(strip(sd))
        model.eval()
        # per-block accumulators plus an overall one
        acc = {b: {t: [0, 0, 0] for t in thresholds} for b in range(n_blocks)}
        gen = torch.Generator(device=device).manual_seed(args.seed)

        for s in range(0, n, args.batch):
            lb = torch.from_numpy(lat[s : s + args.batch]).float().to(device)
            # (B,h,w,T,C) -> (B,T,C,h,w)
            lb = lb.permute(0, 3, 4, 1, 2)
            cond = lb[:, :in_len]
            with torch.no_grad():
                pred_lat = autoregressive_sample(
                    model=model,
                    initial_cond=model.normalize(cond),
                    output_length=out_len,
                    input_length=in_len,
                    num_train_timesteps=config.rflow_params.num_train_timesteps,
                    euler_steps=config.sampling_params.euler_steps,
                    generator=gen,
                )
                pred_lat = model.denormalize(pred_lat)
                b, t = pred_lat.shape[:2]
                dec = ae.decode(pred_lat.reshape(b * t, *pred_lat.shape[2:])).sample
            pred = (dec.reshape(b, t, 128, 128) * pixel_scale).clamp(0, pixel_scale)
            gt = (
                torch.from_numpy(raw[s : s + args.batch]).float().to(device)
                .permute(0, 3, 1, 2)[:, in_len:]
                * (pixel_scale / 255.0)
            )
            for blk in range(n_blocks):
                sl = slice(blk * in_len, (blk + 1) * in_len)
                c = csi_counts(gt[:, sl], pred[:, sl], thresholds)
                for t_, (h, m, fa) in c.items():
                    acc[blk][t_][0] += h
                    acc[blk][t_][1] += m
                    acc[blk][t_][2] += fa

        print(f"===== {name.upper()} =====")
        header = "  block(frames)   " + "".join(f"CSI@{t:<6}" for t in thresholds) + "CSI-M"
        print(header)
        overall = {t: [0, 0, 0] for t in thresholds}
        for blk in range(n_blocks):
            vals = []
            for t_ in thresholds:
                h, m, fa = acc[blk][t_]
                vals.append(h / max(h + m + fa, 1))
                for i in range(3):
                    overall[t_][i] += acc[blk][t_][i]
            lbl = f"{blk * in_len + 1}-{(blk + 1) * in_len}"
            print(
                f"  block{blk + 1} ({lbl:>5})  "
                + "".join(f"{v:<10.4f}" for v in vals)
                + f"{sum(vals) / len(vals):.4f}"
            )
        vals = []
        for t_ in thresholds:
            h, m, fa = overall[t_]
            vals.append(h / max(h + m + fa, 1))
        print(
            "  ALL 1-20       "
            + "".join(f"{v:<10.4f}" for v in vals)
            + f"{sum(vals) / len(vals):.4f}\n"
        )


if __name__ == "__main__":
    main()
