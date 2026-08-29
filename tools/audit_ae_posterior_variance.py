"""VE-A -- posterior-variance audit of the frozen AutoencoderKL (VE-Loss
premise check, diagnostic A).

The question
------------
The VE-Loss paper's causal story is: reconstruction on sampled latents
``z = mu + sigma*eps`` exerts a ``sigma^2 * T(mu)`` gradient that collapses
the posterior variance (they measure sigma^2 ~ 1e-7 under KL 1e-6), leaving
the decoder brittle in a thin shell around ``mu``.  Whether that premise
holds HERE is an empirical question about our checkpoints, not the paper's.

Code-level premise (verified against this repo, recorded in the output)
-----------------------------------------------------------------------
Our AE trainer never enables posterior sampling:

    experiments/sevir/autoencoder/dist_train_autoencoder_kl.py:555
        outputs_dict = model(input_frame)          # training
    experiments/sevir/autoencoder/dist_train_autoencoder_kl.py:672
        outputs_dict = model(input_frame)          # validation

With ``diffusers==0.36.0`` (requirements.txt:8), ``AutoencoderKL.forward``
defaults ``sample_posterior=False`` and decodes ``posterior.mode()`` == mu.
So sigma NEVER touches the reconstruction path: the paper's collapse
mechanism has no gradient route in this trainer.  Only the KL term shapes
logvar -- weight 1e-4 and divided by batch_size twice
(common/autoencoder/losses/lpips.py:258-259) -- and pure KL is minimised at
logvar = 0, i.e. sigma^2 = 1.  The measurement below decides which story the
actual checkpoint tells.

Read-outs
---------
sigma^2 = exp(logvar) of the encoder posterior on validation target frames:
  * global median / p10 / p90 / mean,
  * per latent channel (4),
  * per pixel-intensity band of the latent site's 8x8 receptive patch
    (max-pooled dBZ: dry < 20, 20-30, 30-35, 35-40, >= 40),
  * per lead (output frame index),
  * saturation fraction at the DiagonalGaussianDistribution clamp
    (logvar = -30 -> sigma^2 ~ 9e-14 is a *saturation bin*, not a value),
  * mu magnitude stats for context.

Pre-registered gates (fixed before measurement)
-----------------------------------------------
  V1  collapse premise PRESENT:  median sigma^2 <  1e-3
  V2  collapse premise ABSENT (VE-Loss NO-GO as-is): median sigma^2 >= 1e-2
  between the two -> inconclusive; escalate only with diagnostic B
  (tools/audit_decoder_endpoint_robustness.py) also in hand.

Bands are computed on the uncropped 128x128 AE view, so CIKM's zero padding
counts as 'dry'; those latent sites are real decoder inputs, but do not read
the dry-band population share as a climatology.

This is a training-side decision: test-split paths are refused.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

import numpy as np
import torch

sys.path.append(os.getcwd())

# Pre-registered constants -- fixed before the first measurement.
GATE_COLLAPSE_MEDIAN_SIGMA2 = 1e-3
GATE_ABSENT_MEDIAN_SIGMA2 = 1e-2
BAND_EDGES_DBZ = (20.0, 30.0, 35.0, 40.0)
BAND_NAMES = ("dry", "20-30", "30-35", "35-40", ">=40")
LOGVAR_SATURATION_BOUND = -30.0  # DiagonalGaussianDistribution clamp floor

CODE_PREMISES = {
    "reconstruction_latent": "posterior.mode() == mu (sample_posterior never passed)",
    "evidence": [
        "experiments/sevir/autoencoder/dist_train_autoencoder_kl.py:555 "
        "'outputs_dict = model(input_frame)' (training, no sample_posterior)",
        "experiments/sevir/autoencoder/dist_train_autoencoder_kl.py:672 "
        "(validation, same call)",
        "diffusers==0.36.0 AutoencoderKL.forward(sample, sample_posterior=False, "
        "...) -> z = posterior.mode()",
        "common/autoencoder/losses/lpips.py:258-259 KL summed over all elements "
        "then divided by batch_size twice; kl_weight = 1e-4 "
        "(experiments/sevir/autoencoder/autoencoder_kl_config.yaml)",
    ],
    "implication": (
        "recon/NLL/GAN losses exert zero gradient on the posterior logvar; the "
        "VE-Loss paper's sigma^2*T(mu) collapse pressure does not exist in this "
        "trainer, and pure KL pushes logvar toward 0 (sigma^2 -> 1). Dropping "
        "KL for the VE variance bonus WITHOUT first enabling sample_posterior "
        "training would reward a sigma the decoder never sees: NO-GO as an "
        "implementation, independent of this measurement."
    ),
}


# ---------------------------------------------------------------------------
# Pure functions (unit-tested; no model, no I/O)
# ---------------------------------------------------------------------------

def patch_pool_max(frames, factor):
    """Max-pool (B, H, W) -> (B, H//factor, W//factor) over factor x factor
    patches: the pixel receptive footprint of each latent site."""
    frames = np.asarray(frames)
    b, h, w = frames.shape
    if h % factor or w % factor:
        raise ValueError(f"spatial dims {(h, w)} not divisible by {factor}")
    return frames.reshape(b, h // factor, factor, w // factor, factor).max(axis=(2, 4))


def assign_bands(pooled_dbz, edges=BAND_EDGES_DBZ):
    """Band ids 0..len(edges) with the repo's '>=' edge convention:
    19.99 -> 0 (dry), 20.0 -> 1, 30.0 -> 2, 35.0 -> 3, 40.0 -> 4."""
    return np.digitize(np.asarray(pooled_dbz), bins=np.asarray(edges), right=False)


def summarize_sigma2(values):
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        return {"count": 0}
    return {
        "count": int(values.size),
        "median": float(np.median(values)),
        "p10": float(np.percentile(values, 10)),
        "p90": float(np.percentile(values, 90)),
        "mean": float(values.mean()),
    }


def evaluate_posterior_gates(median_sigma2):
    median_sigma2 = float(median_sigma2)
    present = median_sigma2 < GATE_COLLAPSE_MEDIAN_SIGMA2
    absent = median_sigma2 >= GATE_ABSENT_MEDIAN_SIGMA2
    return {
        "gates": {
            "V1_variance_collapse_premise_present": bool(present),
            "V2_premise_absent_VE_NOGO": bool(absent),
        },
        "inconclusive": bool(not present and not absent),
        "median_sigma2": median_sigma2,
        "constants": {
            "collapse_median_sigma2": GATE_COLLAPSE_MEDIAN_SIGMA2,
            "absent_median_sigma2": GATE_ABSENT_MEDIAN_SIGMA2,
        },
    }


def select_event_rows(n_rows, max_events, seed_salt="ve-a"):
    """Order-stable subsample of manifest ROWS by sha256 rank; assumes one
    window per event (enforced in main; true for CIKM) -- the whole-event
    variant is estimate_rmlf_amplification.select_event_indices."""
    ranked = sorted(
        range(n_rows),
        key=lambda row: hashlib.sha256(
            f"{seed_salt}:{row}".encode("utf-8")
        ).hexdigest(),
    )
    if max_events is not None and max_events > 0:
        ranked = ranked[: int(max_events)]
    return sorted(ranked)


def refuse_test_path(*paths):
    for path in paths:
        if path and "test" in os.path.basename(str(path)).lower():
            raise SystemExit(
                f"refusing test-split path {path!r}: this audit feeds a "
                "training-side design decision and must run on validation."
            )


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# CLI / main (heavy imports stay inside so the pure functions above import
# without diffusers / the dataset stack)
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True,
                   help="flowcast yaml -- only autoencoder_params / data_params "
                        "/ evaluation_params are read")
    p.add_argument("--ae-checkpoint", default=None,
                   help="override config.autoencoder_params.autoencoder_checkpoint")
    p.add_argument("--data-file", required=True,
                   help="validation raw-pixel h5 (test paths are refused)")
    p.add_argument("--data-meta", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-events", type=int, default=400)
    p.add_argument("--micro-batch", type=int, default=6)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


def main():
    args = parse_args()
    refuse_test_path(args.data_file, args.data_meta)

    from omegaconf import OmegaConf  # noqa: E402
    from torch.utils.data import DataLoader, Subset  # noqa: E402
    from diffusers.models.autoencoders import AutoencoderKL  # noqa: E402
    from experiments.sevir.dataset.sevirfulldataset import (  # noqa: E402
        DynamicSequentialSevirDataset,
        dynamic_sequential_collate,
    )

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device(args.device)

    config = OmegaConf.load(args.config)
    dataset_name = OmegaConf.select(config, "data_params.dataset_name", default="sevir")
    pixel_scale = OmegaConf.select(config, "evaluation_params.pixel_scale", default=255.0)
    input_length = OmegaConf.select(config, "data_params.input_length",
                                    default=config.data_params.lag_time)
    output_length = OmegaConf.select(config, "data_params.output_length",
                                     default=config.data_params.lead_time)
    normalized_ae = config.autoencoder_params.normalized_autoencoder
    if args.ae_checkpoint:
        ae_ckpt_path = args.ae_checkpoint
    else:
        try:
            # The v4 config hides this behind an OmegaConf ${DATA_ROOT}
            # interpolation that only resolves in production.
            ae_ckpt_path = config.autoencoder_params.autoencoder_checkpoint
        except Exception as exc:
            raise SystemExit(
                "config.autoencoder_params.autoencoder_checkpoint did not "
                f"resolve ({exc}); pass --ae-checkpoint explicitly."
            )

    dataset = DynamicSequentialSevirDataset(
        meta_csv=args.data_meta,
        data_file=args.data_file,
        data_type=OmegaConf.select(config, "data_params.data_key", default="vil"),
        raw_seq_len=OmegaConf.select(config, "data_params.raw_seq_len", default=49),
        lag_time=input_length,
        lead_time=output_length,
        time_spacing=config.data_params.time_spacing,
        stride=OmegaConf.select(config, "data_params.stride", default=1),
        channel_last=False,
        debug_mode=False,
    )
    if len(dataset) != len(dataset.metadata):
        raise SystemExit(
            f"manifest yields {len(dataset)} windows over "
            f"{len(dataset.metadata)} events; row-hash selection assumes one "
            "window per event (the CIKM layout) -- extend to whole-event "
            "hashing before auditing this split."
        )
    rows = select_event_rows(len(dataset), args.max_events)
    loader = DataLoader(Subset(dataset, rows), batch_size=args.micro_batch,
                        shuffle=False, collate_fn=dynamic_sequential_collate,
                        num_workers=2, pin_memory=device.type == "cuda")

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
    ae_ckpt = torch.load(ae_ckpt_path, map_location="cpu")
    ae_state = {
        (k[len("module."):] if k.startswith("module.") else k): v
        for k, v in ae_ckpt["model_state_dict"].items()
    }
    ae_model.load_state_dict(ae_state)
    ae_model = ae_model.to(device).eval().requires_grad_(False)

    sigma2_cols = []
    logvar_cols = []
    band_cols = []
    chan_cols = []
    lead_cols = []
    mu_sq_sum = 0.0
    mu_abs_max = 0.0
    mu_count = 0
    n_events = 0
    latent_channels = int(config.autoencoder_params.latent_channels)

    for batch in loader:
        _x_cond, x_true, _meta = batch
        y_raw = x_true.squeeze(1).float()               # (B, T, H, W) 0-255
        b, t, h_pix, w_pix = y_raw.shape
        flat = y_raw.reshape(b * t, 1, h_pix, w_pix).to(device)
        if normalized_ae:
            flat = flat / 255.0
        with torch.no_grad():
            dist = ae_model.encode(flat).latent_dist
            logvar = dist.logvar.detach().float().cpu().numpy()  # (B*T, C, h, w)
            mu = dist.mean.detach().float().cpu().numpy()

        n_frames, n_chan, h_lat, w_lat = logvar.shape
        if n_chan != latent_channels:
            raise SystemExit(
                f"latent channels {n_chan} != config {latent_channels}")
        factor = h_pix // h_lat
        dbz = y_raw.reshape(b * t, h_pix, w_pix).numpy() * (pixel_scale / 255.0)
        bands = assign_bands(patch_pool_max(dbz, factor))          # (B*T, h, w)

        sigma2 = np.exp(logvar)
        sigma2_cols.append(sigma2.reshape(-1).astype(np.float32))
        logvar_cols.append(logvar.reshape(-1).astype(np.float32))
        band_cols.append(
            np.broadcast_to(bands[:, None], sigma2.shape).reshape(-1).astype(np.int8)
        )
        chan_cols.append(
            np.broadcast_to(
                np.arange(n_chan, dtype=np.int8)[None, :, None, None], sigma2.shape
            ).reshape(-1)
        )
        lead_idx = np.tile(np.arange(t, dtype=np.int16), b)
        lead_cols.append(
            np.broadcast_to(
                lead_idx[:, None, None, None], sigma2.shape
            ).reshape(-1).astype(np.int16)
        )
        mu_sq_sum += float((mu ** 2).sum())
        mu_abs_max = max(mu_abs_max, float(np.abs(mu).max()))
        mu_count += mu.size
        n_events += b
        print(f"  encoded {n_events} events", flush=True)

    if n_events == 0:
        raise SystemExit("no events encoded -- check --max-events.")

    sigma2_all = np.concatenate(sigma2_cols)
    logvar_all = np.concatenate(logvar_cols)
    band_all = np.concatenate(band_cols)
    chan_all = np.concatenate(chan_cols)
    lead_all = np.concatenate(lead_cols)

    overall = summarize_sigma2(sigma2_all)
    verdict = evaluate_posterior_gates(overall["median"])

    out = {
        "n_events": n_events,
        "dataset": dataset_name,
        "frames_audited": "target frames (leads 1..output_length)",
        "includes_padding": dataset_name == "cikm",
        "band_edges_dbz": list(BAND_EDGES_DBZ),
        "band_pooling": "max over the latent site's receptive patch",
        "sigma2_overall": overall,
        "sigma2_per_channel": {
            str(c): summarize_sigma2(sigma2_all[chan_all == c])
            for c in range(latent_channels)
        },
        "sigma2_per_band": {
            BAND_NAMES[k]: summarize_sigma2(sigma2_all[band_all == k])
            for k in range(len(BAND_NAMES))
        },
        "sigma2_per_lead": {
            str(k + 1): summarize_sigma2(sigma2_all[lead_all == k])
            for k in range(int(lead_all.max()) + 1)
        },
        "logvar_saturated_fraction": float(
            (logvar_all <= LOGVAR_SATURATION_BOUND + 1e-3).mean()
        ),
        "sigma2_below_1e-3_fraction": float((sigma2_all < 1e-3).mean()),
        "sigma2_below_1e-2_fraction": float((sigma2_all < 1e-2).mean()),
        "mu_rms": float(np.sqrt(mu_sq_sum / max(mu_count, 1))),
        "mu_abs_max": mu_abs_max,
        "verdict": verdict,
        "code_premises": CODE_PREMISES,
        "provenance": {
            "config": os.path.abspath(args.config),
            "config_sha256": sha256_file(args.config),
            "ae_checkpoint": os.path.abspath(str(ae_ckpt_path)),
            "ae_checkpoint_sha256": sha256_file(str(ae_ckpt_path)),
            "git_commit": git_commit(),
            "seed": args.seed,
            "device": str(device),
        },
    }
    txt = json.dumps(out, indent=2)
    print(txt)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write(txt + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
