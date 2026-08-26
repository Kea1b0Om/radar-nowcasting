"""E0 -- per-threshold autoencoder ceiling AND frequency bias.

The question
------------
The model under-reports exceedance area at the higher thresholds.  A quantile
collapse on the read-out side can add area back, but only to a field the
decoder already produced.  If the FROZEN autoencoder itself destroys
exceedance area on a perfect input, that loss is invisible to every
read-out-side fix and bounds every latent-side method.

So: push the ground-truth FUTURE frames through encode->decode ONLY (no CFM,
no sampling) and score the reconstruction against the truth under the exact
published protocol.

Read-outs
---------
  CSI_AE(t)   the ceiling: no latent model can exceed this
  FBI_AE(t)   whether the decoder itself loses exceedance area

Decision rules are supplied by the caller and must be fixed before running;
this tool only reports the two read-outs.

Identity arm
------------
``--identity`` skips the codec and scores truth against truth.  It MUST return
CSI = 1.0 and FBI = 1.0 exactly; anything else means the eval view (crop,
scale, clamp, comparison operator) is wired wrong and the real numbers are
uninterpretable.  Always run it first.

Protocol
--------
Bit-identical to ``score_test_published.py``: per-(threshold, lead)
contingency tables -> per-lead CSI -> lead-equal-weight mean -> threshold mean.
Comparison uses ``>=``.  Eval view follows ``write_validation_ensemble.py``:
decode, to eval scale, CIKM crop ``13:-14``, clamp ``[0, pixel_scale]``.
"""

import argparse
import json
import os
import sys

import numpy as np
import torch
from omegaconf import OmegaConf
from torch.utils.data import DataLoader, Subset

sys.path.append(os.getcwd())

from common.models.flowcast.gated_rollout import build_codec_fns  # noqa: E402
from common.models.flowcast.rf_stdit import FlowCastSTDiTWrapper  # noqa: E402
from experiments.sevir.dataset.sevirfulldataset import (  # noqa: E402
    DynamicSequentialSevirDataset,
    dynamic_sequential_collate,
)

THRESHOLDS = (20.0, 30.0, 35.0, 40.0)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--checkpoint", required=True,
                   help="FlowCast .pt -- only its normalize/denormalize stats are used.")
    p.add_argument("--test-file", required=True)
    p.add_argument("--test-meta", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-events", type=int, default=None)
    p.add_argument("--identity", action="store_true",
                   help="Skip the codec; must give CSI=1, FBI=1 exactly.")
    return p.parse_args()


def main():
    args = parse_args()
    config = OmegaConf.load(args.config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    dataset_name = OmegaConf.select(config, "data_params.dataset_name", default="sevir")
    pixel_scale = OmegaConf.select(config, "evaluation_params.pixel_scale", default=255.0)
    input_length = OmegaConf.select(config, "data_params.input_length",
                                    default=config.data_params.lag_time)
    output_length = OmegaConf.select(config, "data_params.output_length",
                                     default=config.data_params.lead_time)
    normalized_ae = config.autoencoder_params.normalized_autoencoder
    batch_size = config.test_params.micro_batch_size
    is_cikm = dataset_name == "cikm"

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
    if args.max_events is not None:
        dataset = Subset(dataset, range(min(args.max_events, len(dataset))))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False,
                        collate_fn=dynamic_sequential_collate,
                        num_workers=2, pin_memory=True)

    decode_fn = encode_fn = None
    if not args.identity:
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
        decode_fn, encode_fn = build_codec_fns(ae_model, model, pixel_scale, normalized_ae)

    n_leads = output_length
    tp = np.zeros((len(THRESHOLDS), n_leads), dtype=np.float64)
    fp = np.zeros_like(tp); fn = np.zeros_like(tp); tn = np.zeros_like(tp)
    sse = np.zeros(n_leads); npix = np.zeros(n_leads)
    n_events = 0

    for batch in loader:
        _x_cond, x_true, _meta = batch
        x_true = x_true.squeeze(1).to(device)                   # (B, T, Hp, Wp) raw
        truth_full = x_true.float() * (pixel_scale / 255.0)     # eval scale, uncropped

        with torch.no_grad():
            if args.identity:
                recon_full = truth_full
            else:
                recon_full = decode_fn(encode_fn(truth_full))

        if n_events == 0 and not args.identity:
            print(f"[codec sanity] truth mean={truth_full.mean():.4f} max={truth_full.max():.4f}"
                  f" | recon mean={recon_full.mean():.4f} max={recon_full.max():.4f}"
                  f" | pixel_scale={pixel_scale}", flush=True)

        sl = (slice(13, -14), slice(13, -14)) if is_cikm else (slice(None), slice(None))
        obs = truth_full[..., sl[0], sl[1]]
        rec = recon_full[..., sl[0], sl[1]].clamp(0.0, pixel_scale)

        d = (rec - obs)
        sse += (d ** 2).sum(dim=(0, 2, 3)).double().cpu().numpy()
        npix += float(obs.shape[0] * obs.shape[2] * obs.shape[3])
        n_events += int(obs.shape[0])

        for k, thr in enumerate(THRESHOLDS):
            p_ = rec >= thr
            o_ = obs >= thr
            tp[k] += (p_ & o_).sum(dim=(0, 2, 3)).double().cpu().numpy()
            fp[k] += (p_ & ~o_).sum(dim=(0, 2, 3)).double().cpu().numpy()
            fn[k] += (~p_ & o_).sum(dim=(0, 2, 3)).double().cpu().numpy()
            tn[k] += (~p_ & ~o_).sum(dim=(0, 2, 3)).double().cpu().numpy()

    csi = tp / np.maximum(tp + fp + fn, 1.0)
    pod = tp / np.maximum(tp + fn, 1.0)
    far = fp / np.maximum(tp + fp, 1.0)
    fbi = (tp + fp) / np.maximum(tp + fn, 1.0)
    key = lambda a: {str(int(t)): float(v) for t, v in zip(THRESHOLDS, a.mean(axis=1))}

    csi_ae = key(csi); fbi_ae = key(fbi)
    verdict = {
        "R1_ceiling_not_binding": csi_ae["30"] >= 0.60,
        "R2_decoder_NOT_eating_area_lever_E_NOGO": fbi_ae["30"] >= 0.97,
        "R3_decoder_eating_area_lever_E_GO": fbi_ae["30"] <= 0.92,
    }
    out = {
        "identity_arm": bool(args.identity),
        "n_events": n_events, "n_leads": int(n_leads),
        "pixel_scale": float(pixel_scale), "dataset": dataset_name, "op": ">=",
        "csi_ae_per_threshold": csi_ae,
        "truth_exceedance_per_threshold": key(tp + fn),
        "empty_cells_per_threshold": {str(int(t)): int((c == 0).sum())
                                      for t, c in zip(THRESHOLDS, (tp + fn))},
        "fbi_ae_per_threshold": fbi_ae,
        "pod_ae_per_threshold": key(pod),
        "far_ae_per_threshold": key(far),
        "csi_ae_m": float(csi.mean(axis=1).mean()),
        "mse_ae": float((sse / npix).mean()),
        "verdict": verdict,
    }
    txt = json.dumps(out, indent=2)
    print(txt)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(txt + "\n")

    if args.identity:
        # A (threshold, lead) cell with no truth exceedance yields csi = 0/1 = 0
        # under the published aggregation.  That is an empty cell, not a wiring
        # fault, so the identity check evaluates only non-empty cells.  The real
        # arm's aggregation is untouched.
        occupied = (tp + fn) > 0
        bad = []
        for k, t in enumerate(THRESHOLDS):
            m = occupied[k]
            if not m.any():
                print(f"  [identity] @{int(t)}: no truth exceedance in this subset -- skipped")
                continue
            if not (np.allclose(csi[k][m], 1.0, atol=1e-12)
                    and np.allclose(fbi[k][m], 1.0, atol=1e-12)):
                bad.append(str(int(t)))
        print("\nIDENTITY ARM: " + ("PASS" if not bad else f"FAIL at {bad}"))
        if bad:
            sys.exit(1)


if __name__ == "__main__":
    main()
