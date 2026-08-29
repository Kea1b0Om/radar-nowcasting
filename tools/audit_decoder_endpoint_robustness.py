"""VE-B -- decoder robustness to *real* flow endpoint error (VE-Loss premise
check, diagnostic B).

The question
------------
The AE oracle (CSI_35 = 0.893, CSI_40 = 0.852 on encode->decode of clean
truth) certifies D(mu) on the data manifold.  VE-Loss instead worries about
D(mu + delta) where delta is a *generated-latent* offset.  Whether our
decoder amplifies the actual endpoint error of the deployed samplers -- and
amplifies the 4-step student's error MORE than the 10-step teacher's -- is
the empirical premise for any tokenizer-robustness work.  If the decoder
treats delta_4 like any same-norm perturbation, the s4-vs-s10 gap lives
upstream in the flow, and reshaping the AE cannot close it.

Design
------
For hash-selected validation events, with teacher and student integrating
the SAME per-chunk noises (``distill.autoregressive_sample_from_noises``,
the deployment wiring: each model feeds back its own chunk-1 output):

    z*      = E(Y)            (deterministic mode() encode, normalized)
    z_hat_k = k-step rollout  ->  delta_k = z_hat_k - z*        k in {4, 10}

then decode along the real error direction and matched controls

    z(alpha) = z* + alpha * dir,   alpha in {0.25, 0.5, 1.0, 1.5}
    dir in { delta_4, delta_10,
             gauss_matched      (same-norm isotropic noise),
             posterior_matched  (sigma*eps of the AE posterior, same norm),
             channel_shuffle    (delta_4, channels cyclically deranged),
             spatial_shuffle    (delta_4, spatial sites permuted) }

and measure, per event, against the unperturbed decode D(z*):

    A_D       = ||D(z*+a*dir) - D(z*)||_2 / (||a*dir||_2 + eps)
    flip@t    = exceedance flip rate at t in {35, 40} dBZ
    area@40   = exceedance-area ratio, peak = max-value ratio

plus CSI/FSS at 35/40 dBZ against the truth for context (the alpha = 1 rows
of delta_4 / delta_10 ARE the deployed s4 / s10 samples, so the s4-s10 CSI
gap on these events falls out for the attribution discussion).  A_D and
flip@40 are additionally split by chunk (leads 1-5 vs 6-10) because the CSI
regression concentrates in chunk 2.

Caution against over-reading: delta_4 also encodes *legitimate alternative
futures* (cell placement, intensity scenarios) that ensemble members must
keep.  A decoder trained to ignore these directions would collapse spread.
Only the *differential* amplification below justifies tokenizer work.

Pre-registered gates at alpha = 1 (fixed before measurement)
------------------------------------------------------------
  K1 (kill)      median A_D(delta_4) / median A_D(delta_10) < 1.2
                 -> decoder does not differentially amplify the few-step
                 error; close the tokenizer route.
  K2 (structure) median A_D(delta_4) / median A_D(gauss_matched) >= 1.25
                 -> the amplification is direction-structured, not generic.
  GO requires: not K1, and K2.

Identity arm (``--identity``): pushes a zero perturbation through the exact
metric wiring; flip rates and A_D must come back 0.0 exactly, else the real
numbers are uninterpretable (exit 1).  Decode determinism (two decodes of
the same z*) is reported informationally.

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
KILL_AMP_RATIO = 1.2       # A_D(delta_4)/A_D(delta_10) below this -> kill
STRUCTURE_MIN_RATIO = 1.25  # A_D(delta_4)/A_D(gauss) at least this -> structured
GATE_ALPHA = 1.0
THRESHOLDS_DBZ = (35.0, 40.0)
AREA_THRESHOLD_DBZ = 40.0
FSS_SCALES = (4, 16)
NORM_EPS = 1e-12

DIRECTION_NAMES = (
    "delta_s4",
    "delta_s10",
    "gauss_matched",
    "posterior_matched",
    "channel_shuffle",
    "spatial_shuffle",
)


# ---------------------------------------------------------------------------
# Pure functions (unit-tested; no model, no I/O)
# ---------------------------------------------------------------------------

def _flat_norm(x):
    return x.reshape(x.shape[0], -1).to(torch.float32).norm(dim=1)


def match_norm(direction, reference):
    """Scale each sample of ``direction`` to the flattened L2 norm of the
    matching sample of ``reference``.  Zero-norm directions raise (a control
    with no length cannot be matched); zero-norm references yield zeros."""
    d_norm = _flat_norm(direction)
    r_norm = _flat_norm(reference)
    if bool((d_norm <= NORM_EPS).any()):
        raise ValueError("zero-norm direction cannot be norm-matched.")
    scale = (r_norm / d_norm).reshape(-1, *([1] * (direction.dim() - 1)))
    return direction * scale


def channel_shuffle(delta):
    """Cyclically derange the latent channel axis (last dim, channel-last
    layout).  Deterministic, norm-preserving, destroys the cross-channel
    assignment of the error field."""
    if delta.shape[-1] < 2:
        raise ValueError("channel shuffle needs >= 2 channels.")
    return torch.roll(delta, shifts=1, dims=-1)


def spatial_shuffle(delta, generator=None):
    """Permute spatial sites (h, w) with one random permutation per sample,
    shared across frames and channels: per-site channel vectors survive,
    the spatial arrangement does not.  Norm-preserving."""
    b, t, h, w, c = delta.shape
    flat = delta.reshape(b, t, h * w, c)
    out = torch.empty_like(flat)
    for i in range(b):
        perm = torch.randperm(h * w, generator=generator)
        out[i] = flat[i][:, perm.to(flat.device)]
    return out.reshape(b, t, h, w, c)


def flip_rate(base, pert, threshold):
    """Fraction of pixels whose exceedance flips between base and perturbed
    decodes; per sample over all remaining dims."""
    base_ex = base >= threshold
    pert_ex = pert >= threshold
    flips = (base_ex ^ pert_ex).reshape(base.shape[0], -1)
    return flips.float().mean(dim=1)


def area_ratio(base, pert, threshold):
    """Perturbed / base exceedance area per sample; NaN where the base has
    no exceedance (undefined, not zero)."""
    base_area = (base >= threshold).reshape(base.shape[0], -1).sum(dim=1).float()
    pert_area = (pert >= threshold).reshape(pert.shape[0], -1).sum(dim=1).float()
    out = pert_area / base_area
    out[base_area == 0] = float("nan")
    return out


def peak_ratio(base, pert):
    """Perturbed / base field maximum per sample (B_peak_retention naming
    family from run_cikm_hidden_frame_oracle); NaN where the base decode is
    all-zero (undefined, same convention as area_ratio)."""
    base_max = base.reshape(base.shape[0], -1).max(dim=1).values
    pert_max = pert.reshape(pert.shape[0], -1).max(dim=1).values
    out = pert_max / base_max
    out[base_max == 0] = float("nan")
    return out


def decoder_amplification(base_pix, pert_pix, latent_delta):
    """A_D = ||D(z*+delta) - D(z*)||_2 / (||delta||_2 + eps) per sample."""
    num = _flat_norm(pert_pix - base_pix)
    den = _flat_norm(latent_delta) + NORM_EPS
    return num / den


def metric_view(pixels, is_cikm, pixel_scale):
    """Decoded metric-scale pixels -> the evaluator's view: CIKM crop
    13:-14, clamp [0, pixel_scale]."""
    if is_cikm:
        pixels = pixels[..., 13:-14, 13:-14]
    return pixels.clamp(0.0, float(pixel_scale))


def contingency(pred, obs, threshold):
    """Pooled (tp, fp, fn) with the repo's '>=' convention."""
    p = pred >= threshold
    o = obs >= threshold
    tp = int((p & o).sum())
    fp = int((p & ~o).sum())
    fn = int((~p & o).sum())
    return tp, fp, fn


def evaluate_endpoint_gates(amp_s4_median, amp_s10_median, amp_gauss_median):
    ratio_s4_s10 = float(amp_s4_median / max(amp_s10_median, NORM_EPS))
    ratio_s4_gauss = float(amp_s4_median / max(amp_gauss_median, NORM_EPS))
    k1_kill = ratio_s4_s10 < KILL_AMP_RATIO
    k2_structure = ratio_s4_gauss >= STRUCTURE_MIN_RATIO
    return {
        "gates": {
            "K1_amp_ratio_kill": bool(k1_kill),
            "K2_directional_structure": bool(k2_structure),
        },
        "tokenizer_route_go": bool((not k1_kill) and k2_structure),
        "amp_ratio_s4_over_s10": ratio_s4_s10,
        "amp_ratio_s4_over_gauss": ratio_s4_gauss,
        "gate_alpha": GATE_ALPHA,
        "constants": {
            "kill_amp_ratio": KILL_AMP_RATIO,
            "structure_min_ratio": STRUCTURE_MIN_RATIO,
        },
    }


def select_event_rows(n_rows, max_events, seed_salt="ve-b"):
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


def state_dict_from_checkpoint(checkpoint, preference):
    keys = {"ema": ("ema_model_state_dict",), "raw": ("model_state_dict", "model")}
    for key in keys[preference]:
        if key in checkpoint:
            state = {
                (k[len("module."):] if k.startswith("module.") else k): v
                for k, v in checkpoint[key].items()
            }
            return state, key
    raise KeyError(
        f"checkpoint has none of {keys[preference]} "
        f"(available: {sorted(checkpoint.keys())})"
    )


def summarize(values):
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"count": 0}
    return {
        "count": int(values.size),
        "median": float(np.median(values)),
        "p25": float(np.percentile(values, 25)),
        "p75": float(np.percentile(values, 75)),
        "mean": float(values.mean()),
    }


# ---------------------------------------------------------------------------
# Builders / main (heavy imports stay inside)
# ---------------------------------------------------------------------------

def build_flow_model(config, checkpoint_path, weights, device):
    from omegaconf import OmegaConf  # noqa: E402
    from common.models.flowcast.rf_stdit import FlowCastSTDiTWrapper  # noqa: E402

    checkpoint = torch.load(checkpoint_path, weights_only=False,
                            map_location="cpu")
    state, key_used = state_dict_from_checkpoint(checkpoint, weights)
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
    model.load_state_dict(state)
    return model.to(device).eval().requires_grad_(False), key_used


def resolve_ae_checkpoint(config, override):
    """The v4 config stores the AE path behind an OmegaConf ``${DATA_ROOT}``
    interpolation that only resolves in the production environment; fail with
    guidance instead of an InterpolationKeyError."""
    if override:
        return override
    try:
        return config.autoencoder_params.autoencoder_checkpoint
    except Exception as exc:
        raise SystemExit(
            "config.autoencoder_params.autoencoder_checkpoint did not "
            f"resolve ({exc}); pass --ae-checkpoint explicitly."
        )


def build_autoencoder(config, device, ae_checkpoint):
    from diffusers.models.autoencoders import AutoencoderKL  # noqa: E402

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
    ae_ckpt = torch.load(ae_checkpoint, map_location="cpu")
    ae_state = {
        (k[len("module."):] if k.startswith("module.") else k): v
        for k, v in ae_ckpt["model_state_dict"].items()
    }
    ae_model.load_state_dict(ae_state)
    return ae_model.to(device).eval().requires_grad_(False)


def posterior_direction(ae_model, pixels_metric, pixel_scale, normalized_ae,
                        flow_model, generator):
    """sigma * eps of the AE posterior of Y, mapped into the flow model's
    normalized latent space (a direction scales by 1/std)."""
    b, t, h, w = pixels_metric.shape
    x = pixels_metric.reshape(b * t, 1, h, w)
    x = x / pixel_scale if normalized_ae else x * (255.0 / pixel_scale)
    dist = ae_model.encode(x).latent_dist
    eps = torch.randn(dist.std.shape, generator=generator,
                      dtype=torch.float32).to(dist.std.device)
    raw_dir = dist.std * eps                                   # (B*T, C, h, w)
    raw_dir = raw_dir.reshape(b, t, *raw_dir.shape[1:]).permute(0, 1, 3, 4, 2)
    return (raw_dir / flow_model.std).contiguous(), _flat_norm(raw_dir)


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--checkpoint", required=True,
                   help="reference FlowCast .pt (10-step teacher)")
    p.add_argument("--student-checkpoint", default=None,
                   help="4-step distilled student .pt; omitted -> the "
                        "reference weights run at --euler-steps-low (a pure "
                        "reduced-NFE arm; recorded in the output)")
    p.add_argument("--data-file", required=True,
                   help="validation raw-pixel h5 (test paths are refused)")
    p.add_argument("--data-meta", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--ae-checkpoint", default=None,
                   help="override config.autoencoder_params.autoencoder_checkpoint")
    p.add_argument("--weights", choices=("ema", "raw"), default="raw")
    p.add_argument("--student-weights", choices=("ema", "raw"), default="raw")
    p.add_argument("--euler-steps-ref", type=int, default=10)
    p.add_argument("--euler-steps-low", type=int, default=4)
    p.add_argument("--alphas", type=float, nargs="+",
                   default=(0.25, 0.5, 1.0, 1.5))
    p.add_argument("--max-events", type=int, default=32)
    p.add_argument("--micro-batch", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--identity", action="store_true",
                   help="zero-perturbation wiring check; must be exact")
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


def main():
    args = parse_args()
    refuse_test_path(args.data_file, args.data_meta)
    alphas = sorted(set(float(a) for a in args.alphas))
    if any(a <= 0 for a in alphas):
        raise SystemExit("--alphas must be positive (alpha=0 is the base decode).")
    if GATE_ALPHA not in alphas:
        raise SystemExit(f"--alphas must include the gate alpha {GATE_ALPHA}.")

    from omegaconf import OmegaConf  # noqa: E402
    from torch.utils.data import DataLoader, Subset  # noqa: E402
    from common.metrics.fss import fss_accum, fss_compute, fss_init  # noqa: E402
    from common.models.flowcast.distill import (  # noqa: E402
        autoregressive_sample_from_noises,
        draw_chunk_noises,
    )
    from common.models.flowcast.gated_rollout import build_codec_fns  # noqa: E402
    from experiments.sevir.dataset.sevirfulldataset import (  # noqa: E402
        DynamicSequentialSevirDataset,
        dynamic_sequential_collate,
    )

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = torch.device(args.device)

    config = OmegaConf.load(args.config)
    dataset_name = OmegaConf.select(config, "data_params.dataset_name", default="sevir")
    pixel_scale = OmegaConf.select(config, "evaluation_params.pixel_scale", default=255.0)
    input_length = OmegaConf.select(config, "data_params.input_length",
                                    default=config.data_params.lag_time)
    output_length = OmegaConf.select(config, "data_params.output_length",
                                     default=config.data_params.lead_time)
    num_train_timesteps = config.rflow_params.num_train_timesteps
    normalized_ae = config.autoencoder_params.normalized_autoencoder
    is_cikm = dataset_name == "cikm"

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

    ae_model = build_autoencoder(
        config, device, resolve_ae_checkpoint(config, args.ae_checkpoint))
    model_ref, ref_key = build_flow_model(config, args.checkpoint,
                                          args.weights, device)
    if args.student_checkpoint:
        model_low, low_key = build_flow_model(config, args.student_checkpoint,
                                              args.student_weights, device)
        low_arm = "student_checkpoint"
    else:
        model_low, low_key = model_ref, ref_key
        low_arm = "reference_weights_at_low_steps"
    if not (torch.allclose(model_ref.mean, model_low.mean, atol=1e-6)
            and torch.allclose(model_ref.std, model_low.std, atol=1e-6)):
        raise SystemExit(
            "reference and student normalizer buffers differ -- their latent "
            "spaces are not comparable and delta arithmetic would be invalid."
        )
    decode_fn, encode_fn = build_codec_fns(ae_model, model_ref, pixel_scale,
                                           normalized_ae)
    num_chunks = output_length // input_length

    # Accumulators keyed (direction, alpha)
    per_event = {
        (d, a): {"amp": [], "flip": {t: [] for t in THRESHOLDS_DBZ},
                 "area40": [], "peak": [],
                 "amp_chunk1": [], "amp_chunk2": [],
                 "flip40_chunk1": [], "flip40_chunk2": []}
        for d in DIRECTION_NAMES for a in alphas
    }
    counts = {(d, a, t): [0, 0, 0]
              for d in DIRECTION_NAMES for a in alphas for t in THRESHOLDS_DBZ}
    base_counts = {t: [0, 0, 0] for t in THRESHOLDS_DBZ}
    fss_acc = {(d, a, t, s): fss_init(t, s)
               for d in DIRECTION_NAMES for a in alphas
               for t in THRESHOLDS_DBZ for s in FSS_SCALES}
    delta_norms = {"delta_s4": [], "delta_s10": [],
                   "posterior_sigma_eps_raw": []}
    identity_failures = []
    n_events = 0

    for batch_idx, batch in enumerate(loader):
        x_cond, x_true, _meta = batch
        x_hist = x_cond.squeeze(1).float().to(device) * (pixel_scale / 255.0)
        y_metric = x_true.squeeze(1).float().to(device) * (pixel_scale / 255.0)
        b = x_hist.shape[0]
        gen = torch.Generator(device="cpu").manual_seed(
            args.seed * 100003 + batch_idx)

        with torch.no_grad():
            cond = encode_fn(x_hist)
            z_star = encode_fn(y_metric)
            noises = [n.to(device) for n in draw_chunk_noises(
                tuple(cond.shape), num_chunks, "cpu", torch.float32,
                generator=gen)]
            z_low = autoregressive_sample_from_noises(
                model=model_low, initial_cond=cond,
                input_length=input_length, output_length=output_length,
                num_train_timesteps=num_train_timesteps,
                euler_steps=args.euler_steps_low, noises=noises,
                grad_last_k=0)
            z_ref = autoregressive_sample_from_noises(
                model=model_ref, initial_cond=cond,
                input_length=input_length, output_length=output_length,
                num_train_timesteps=num_train_timesteps,
                euler_steps=args.euler_steps_ref, noises=noises,
                grad_last_k=0)

            delta_low = z_low - z_star
            delta_ref = z_ref - z_star
            gauss = torch.randn(delta_low.shape, generator=gen,
                                dtype=torch.float32).to(device)
            post_dir, post_raw_norm = posterior_direction(
                ae_model, y_metric, pixel_scale, normalized_ae, model_ref, gen)
            delta_norms["posterior_sigma_eps_raw"].extend(
                post_raw_norm.tolist())
            directions = {
                "delta_s4": delta_low,
                "delta_s10": delta_ref,
                "gauss_matched": match_norm(gauss, delta_low),
                "posterior_matched": match_norm(post_dir.to(device), delta_low),
                "channel_shuffle": channel_shuffle(delta_low),
                "spatial_shuffle": spatial_shuffle(delta_low, generator=gen),
            }
            delta_norms["delta_s4"].extend(_flat_norm(delta_low).tolist())
            delta_norms["delta_s10"].extend(_flat_norm(delta_ref).tolist())

            base_pix = metric_view(decode_fn(z_star), is_cikm, pixel_scale)
            truth_view = metric_view(y_metric, is_cikm, pixel_scale)
            for t in THRESHOLDS_DBZ:
                tp, fp, fn = contingency(base_pix, truth_view, t)
                base_counts[t][0] += tp
                base_counts[t][1] += fp
                base_counts[t][2] += fn

            for name in DIRECTION_NAMES:
                direction = directions[name]
                for alpha in alphas:
                    latent_delta = alpha * direction
                    if args.identity:
                        latent_delta = torch.zeros_like(latent_delta)
                        pert_pix = base_pix.clone()
                    else:
                        pert_pix = metric_view(
                            decode_fn(z_star + latent_delta), is_cikm,
                            pixel_scale)
                    acc = per_event[(name, alpha)]
                    acc["amp"].extend(decoder_amplification(
                        base_pix, pert_pix, latent_delta).tolist())
                    pert_np = pert_pix.cpu().numpy()
                    truth_np = truth_view.cpu().numpy()
                    for t in THRESHOLDS_DBZ:
                        acc["flip"][t].extend(
                            flip_rate(base_pix, pert_pix, t).tolist())
                        tp, fp, fn = contingency(pert_pix, truth_view, t)
                        counts[(name, alpha, t)][0] += tp
                        counts[(name, alpha, t)][1] += fp
                        counts[(name, alpha, t)][2] += fn
                        for s in FSS_SCALES:
                            for i in range(pert_np.shape[0]):
                                for j in range(pert_np.shape[1]):
                                    fss_accum(fss_acc[(name, alpha, t, s)],
                                              pert_np[i, j], truth_np[i, j])
                    acc["area40"].extend(area_ratio(
                        base_pix, pert_pix, AREA_THRESHOLD_DBZ).tolist())
                    acc["peak"].extend(peak_ratio(base_pix, pert_pix).tolist())
                    c1, c2 = slice(0, input_length), slice(input_length, None)
                    acc["amp_chunk1"].extend(decoder_amplification(
                        base_pix[:, c1], pert_pix[:, c1],
                        latent_delta[:, c1]).tolist())
                    acc["amp_chunk2"].extend(decoder_amplification(
                        base_pix[:, c2], pert_pix[:, c2],
                        latent_delta[:, c2]).tolist())
                    acc["flip40_chunk1"].extend(flip_rate(
                        base_pix[:, c1], pert_pix[:, c1], 40.0).tolist())
                    acc["flip40_chunk2"].extend(flip_rate(
                        base_pix[:, c2], pert_pix[:, c2], 40.0).tolist())

                    if args.identity:
                        flips = per_event[(name, alpha)]["flip"][35.0][-b:]
                        amps = per_event[(name, alpha)]["amp"][-b:]
                        if any(f != 0.0 for f in flips) or any(
                                a_ != 0.0 for a_ in amps):
                            identity_failures.append((name, alpha))

        n_events += b
        print(f"  audited {n_events} events "
              f"({len(alphas)} alphas x {len(DIRECTION_NAMES)} directions)",
              flush=True)
        if args.identity:
            break

    if n_events == 0:
        raise SystemExit("no events audited -- check --max-events.")

    if args.identity:
        with torch.no_grad():
            twice = metric_view(decode_fn(z_star), is_cikm, pixel_scale)
        determinism_gap = float((twice - base_pix).abs().max())
        print(f"[identity] decode determinism max|diff| = {determinism_gap:.3e}"
              " (informational)")
        ok = not identity_failures
        print("IDENTITY ARM: " + ("PASS" if ok
                                  else f"FAIL at {identity_failures[:5]}"))
        sys.exit(0 if ok else 1)

    def csi_of(c):
        tp, fp, fn = c
        denom = tp + fp + fn
        return float(tp / denom) if denom else float("nan")

    results = {}
    for name in DIRECTION_NAMES:
        results[name] = {}
        for alpha in alphas:
            acc = per_event[(name, alpha)]
            results[name][f"alpha_{alpha:g}"] = {
                "amp": summarize(acc["amp"]),
                "amp_chunk1": summarize(acc["amp_chunk1"]),
                "amp_chunk2": summarize(acc["amp_chunk2"]),
                "flip@35": summarize(acc["flip"][35.0]),
                "flip@40": summarize(acc["flip"][40.0]),
                "flip40_chunk1": summarize(acc["flip40_chunk1"]),
                "flip40_chunk2": summarize(acc["flip40_chunk2"]),
                "area_ratio@40": summarize(acc["area40"]),
                "peak_ratio": summarize(acc["peak"]),
                "csi_vs_truth": {
                    f"{t:g}": csi_of(counts[(name, alpha, t)])
                    for t in THRESHOLDS_DBZ
                },
                "fss_vs_truth": {
                    f"{t:g}@{s}": float(fss_compute(fss_acc[(name, alpha, t, s)]))
                    for t in THRESHOLDS_DBZ for s in FSS_SCALES
                },
            }

    amp_s4 = np.median(np.asarray(per_event[("delta_s4", GATE_ALPHA)]["amp"]))
    amp_s10 = np.median(np.asarray(per_event[("delta_s10", GATE_ALPHA)]["amp"]))
    amp_gauss = np.median(
        np.asarray(per_event[("gauss_matched", GATE_ALPHA)]["amp"]))
    verdict = evaluate_endpoint_gates(amp_s4, amp_s10, amp_gauss)

    out = {
        "n_events": n_events,
        "dataset": dataset_name,
        "alphas": alphas,
        "euler_steps": {"low": args.euler_steps_low, "ref": args.euler_steps_ref},
        "low_arm": low_arm,
        "weights_keys": {"reference": ref_key, "low": low_key},
        "op": ">=",
        "latent_delta_norms": {k: summarize(v) for k, v in delta_norms.items()},
        "csi_base_vs_truth": {f"{t:g}": csi_of(base_counts[t])
                              for t in THRESHOLDS_DBZ},
        "directions": results,
        "verdict": verdict,
        "spread_caution": (
            "delta_4 includes legitimate alternative futures; a decoder made "
            "insensitive to these directions would collapse ensemble spread. "
            "Gate K2 (structure) is necessary but not sufficient for the "
            "tokenizer route -- any robust-decoder training must bound the "
            "perturbation radius and re-check spread-skill."
        ),
        "provenance": {
            "config": os.path.abspath(args.config),
            "config_sha256": sha256_file(args.config),
            "checkpoint": os.path.abspath(args.checkpoint),
            "checkpoint_sha256": sha256_file(args.checkpoint),
            "student_checkpoint": (os.path.abspath(args.student_checkpoint)
                                   if args.student_checkpoint else None),
            "student_checkpoint_sha256": (
                sha256_file(args.student_checkpoint)
                if args.student_checkpoint else None),
            "git_commit": git_commit(),
            "seed": args.seed,
            "device": str(device),
            "precision": "fp32",
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
