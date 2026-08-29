"""SCD-0 -- zero-training separability audit for the SCD (history/denoise
split) base-model candidate.

The question
------------
SCD-style architectures (Weather-State Encoder + Future-Sequence Renderer)
pay off only if the monolithic STDiT really does recompute a *stable*
history/condition representation at every flow step.  Before building any
prototype, measure -- on frozen checkpoints -- whether that premise holds.

Raw feature cosines across flow times are not evidence: LayerNorm and the
shared positional embedding keep them high whether or not the block uses the
history.  So the audit isolates the *condition response* of every block

    dh_l(tau) = h_l(X, Z_tau) - h_l(shuffle(X), Z_tau)

with the target-noise interpolant Z_tau, the noise eps, and the event all
held fixed, and only the history condition X replaced by a shuffled variant.
Two read-outs per block:

    S_l = median_{i != j} cos(dh_l(tau_i), dh_l(tau_j))     [stability]
    R_l = median ||dh_l(tau)|| / (||h_l(X, Z_tau)|| + eps)  [sensitivity]

S_l ~ 1 means the block's condition computation does not change with the
flow time and could be evaluated once and cached; R_l ~ 0 means the block
barely reads the history at all.  A timing pass attributes per-block latency
so the cacheable share of compute (p) and the projected end-to-end speedup

    speedup(p) = chunks*M*N / ((1+M)*p + chunks*M*N*(1-p))

(the memo's C_old = chunks*M*N*(C_E+C_D) vs C_SCD = (1+M)*C_E +
chunks*M*N*C_D accounting: chunk-1 history is encoded once for the whole
ensemble, chunk-2 conditions are per-member, the renderer runs at every
member x flow step) can be computed for the deployed M=8 members, N=4 NFE.

Pre-registered gates (fixed here, before any measurement)
---------------------------------------------------------
  G1  >= 50% of early+mid blocks (first two thirds of the execution order)
      have S_l >= 0.90 on the probed grid.
  G2  late-block condition sensitivity is clearly lower than early/mid:
      median R_late <= 0.5 * median R_early_mid.
  G3  cacheable compute share p >= 0.35, where p sums the measured latency
      of blocks with S_l >= 0.90.
  G4  projected speedup at M=8, N=4, 2 chunks >= 1.3x.

All four pass -> GO for the Radar-SCD encoder/renderer prototype (everything
else in the recipe frozen).  Any failure -> NO-GO, close the direction.

This is a training-side decision: the tool refuses test-split paths.  Run it
on validation events selected by stable hash (order-independent).

Framing guard: this audit is *not* an exposure-bias probe (RMLF already
falsified that lever) and not a ForeDiff-style representation injection (also
falsified).  It measures only whether condition inference is repeated and
stable enough to amortise across flow steps and ensemble members.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np
import torch

sys.path.append(os.getcwd())

# Pre-registered constants.  Fixed before the first measurement; changing
# them after looking at results voids the gate.
S_CACHE_THRESHOLD = 0.90
G1_MIN_FRACTION_EARLY_MID = 0.50
G2_LATE_SENSITIVITY_RATIO = 0.50
G3_MIN_SEPARABLE_COMPUTE = 0.35
G4_MIN_PROJECTED_SPEEDUP = 1.30
DEPLOYED_MEMBERS = 8
DEPLOYED_NFE = 4
DEPLOYED_CHUNKS = 2
NORM_EPS = 1e-12


# ---------------------------------------------------------------------------
# Pure functions (unit-tested; no model, no I/O)
# ---------------------------------------------------------------------------

def execution_order(depth):
    """Block execution sequence of ``STDiT.forward`` (stdit.py:207-213).

    Returns ``[(kind, index_within_kind), ...]`` in the order the residual
    stream visits them: spatial_blocks[i], temporal_blocks[i], and after
    every even iteration spatiotemporal_blocks[i // 2].
    """
    if depth % 2 != 0:
        raise ValueError("stdit depth must be even.")
    order = []
    for itr in range(depth):
        order.append(("spatial", itr))
        order.append(("temporal", itr))
        if itr % 2 == 0:
            order.append(("spatiotemporal", itr // 2))
    return order


def stage_of(exec_index, n_blocks):
    """early / mid / late by thirds of the execution order."""
    third = n_blocks / 3.0
    if exec_index < third:
        return "early"
    if exec_index < 2.0 * third:
        return "mid"
    return "late"


def pairwise_cosines(deltas):
    """All off-diagonal pairwise cosines of a (K, D) tensor's rows.

    Returns a 1-D tensor of length K*(K-1)/2.  Zero-norm rows are guarded
    with NORM_EPS (their cosines are ~0, which correctly reads as
    "no stable condition response").
    """
    deltas = deltas.to(torch.float32)
    norms = deltas.norm(dim=1, keepdim=True).clamp_min(NORM_EPS)
    unit = deltas / norms
    gram = unit @ unit.t()
    k = deltas.shape[0]
    iu = torch.triu_indices(k, k, offset=1)
    return gram[iu[0], iu[1]]


def condition_sensitivity(h_real, delta):
    """R = ||delta|| / (||h_real|| + eps) per sample.

    ``h_real`` and ``delta`` are (B, D) flattened block features.
    """
    num = delta.to(torch.float32).norm(dim=1)
    den = h_real.to(torch.float32).norm(dim=1) + NORM_EPS
    return num / den


def shuffle_condition(cond, mode, generator=None):
    """Replace the history condition with a shuffled variant.

    ``batch-roll``: each event receives the *previous* event's history --
    the strongest condition change (a different storm entirely) while the
    marginal condition distribution is untouched.  Requires batch >= 2.

    ``temporal``: the event's own history frames in deranged temporal order
    (no frame stays in place) -- destroys motion/order information only.
    """
    if mode == "batch-roll":
        if cond.shape[0] < 2:
            raise ValueError("batch-roll shuffling needs a batch of >= 2 events.")
        return torch.roll(cond, shifts=1, dims=0)
    if mode == "temporal":
        t = cond.shape[1]
        if t < 2:
            raise ValueError("temporal shuffling needs >= 2 frames.")
        perm = torch.roll(torch.arange(t, device=cond.device), shifts=1)
        return cond[:, perm]
    raise ValueError(f"unknown shuffle mode: {mode!r}")


def projected_scd_speedup(p, members, nfe, chunks=DEPLOYED_CHUNKS):
    """Speedup of the SCD split over the monolithic model.

    C_old = chunks * M * N * (C_E + C_D);  C_SCD = (1 + M) * C_E
    + chunks * M * N * C_D, with C_E = p and C_D = 1 - p of one full call.
    (Chunk-1 history is shared by the ensemble -> one encode; later-chunk
    conditions are member-specific -> M encodes; renderer runs everywhere.)
    """
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p must be in [0, 1], got {p}")
    denom = (1.0 + members) * p + chunks * members * nfe * (1.0 - p)
    return chunks * members * nfe / denom


def evaluate_scd_gates(block_records, p_cond, members=DEPLOYED_MEMBERS,
                       nfe=DEPLOYED_NFE, chunks=DEPLOYED_CHUNKS):
    """Apply the four pre-registered gates to per-block audit records.

    Each record needs ``stage`` (early/mid/late), ``s_median``, ``r_median``.
    """
    early_mid = [r for r in block_records if r["stage"] in ("early", "mid")]
    late = [r for r in block_records if r["stage"] == "late"]
    if not early_mid or not late:
        raise ValueError("need blocks in both early/mid and late stages.")

    frac_cacheable = float(
        np.mean([r["s_median"] >= S_CACHE_THRESHOLD for r in early_mid])
    )
    r_early_mid = float(np.median([r["r_median"] for r in early_mid]))
    r_late = float(np.median([r["r_median"] for r in late]))
    speedup = projected_scd_speedup(p_cond, members, nfe, chunks)

    gates = {
        "G1_early_mid_stability": frac_cacheable >= G1_MIN_FRACTION_EARLY_MID,
        "G2_late_low_sensitivity": r_late <= G2_LATE_SENSITIVITY_RATIO * r_early_mid,
        "G3_separable_compute": p_cond >= G3_MIN_SEPARABLE_COMPUTE,
        "G4_projected_speedup": speedup >= G4_MIN_PROJECTED_SPEEDUP,
    }
    return {
        "gates": gates,
        "go_prototype": bool(all(gates.values())),
        "frac_early_mid_cacheable": frac_cacheable,
        "r_median_early_mid": r_early_mid,
        "r_median_late": r_late,
        "p_separable_compute": float(p_cond),
        "projected_speedup": float(speedup),
        "constants": {
            "s_cache_threshold": S_CACHE_THRESHOLD,
            "g1_min_fraction_early_mid": G1_MIN_FRACTION_EARLY_MID,
            "g2_late_sensitivity_ratio": G2_LATE_SENSITIVITY_RATIO,
            "g3_min_separable_compute": G3_MIN_SEPARABLE_COMPUTE,
            "g4_min_projected_speedup": G4_MIN_PROJECTED_SPEEDUP,
            "members": members,
            "nfe": nfe,
            "chunks": chunks,
        },
    }


def select_event_rows(n_rows, max_events, seed_salt="scd"):
    """Order-stable subsample of manifest ROWS by sha256 rank.

    Head-of-manifest truncation samples one season on chronologically
    sorted splits; hashing covers the manifest uniformly and reproduces
    without a stored index list.  This hashes row indices, so callers must
    ensure one window per event (enforced in main; true for CIKM where
    rows == events).  The whole-event variant for multi-window manifests
    is estimate_rmlf_amplification.select_event_indices.
    """
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


# ---------------------------------------------------------------------------
# Feature capture
# ---------------------------------------------------------------------------

class FeatureTap:
    """Forward hooks over an ordered list of modules, capturing outputs.

    Captures are detached float32 tensors flattened to (B, D).  Attach with
    a context manager so a crashed probe never leaves hooks behind.
    """

    def __init__(self, modules):
        self.modules = list(modules)
        self.handles = []
        self.captured = [None] * len(self.modules)

    def _hook(self, index):
        def fn(_module, _inputs, output):
            out = output[0] if isinstance(output, tuple) else output
            self.captured[index] = (
                out.detach().to(torch.float32).reshape(out.shape[0], -1)
            )
        return fn

    def __enter__(self):
        for i, module in enumerate(self.modules):
            self.handles.append(module.register_forward_hook(self._hook(i)))
        return self

    def __exit__(self, *exc):
        for handle in self.handles:
            handle.remove()
        self.handles = []
        return False

    def take(self):
        captured, self.captured = self.captured, [None] * len(self.modules)
        if any(c is None for c in captured):
            raise RuntimeError("a hooked block did not fire during forward.")
        return captured


def measure_block_times(blocks, forward_fn, iters=3, warmup=1, device=None):
    """Synchronized per-block latency plus the synchronized total forward.

    Synchronisation inflates absolute numbers; only the *shares* feed the
    p estimate, and every block pays the same synchronisation tax.  An
    unsynchronised total is also reported for reference.
    """
    use_cuda = device is not None and device.type == "cuda"

    def now():
        if use_cuda:
            torch.cuda.synchronize(device)
        return time.perf_counter()

    per_block = np.zeros(len(blocks), dtype=np.float64)
    starts = [0.0] * len(blocks)
    handles = []

    def pre_hook(index):
        def fn(_module, _inputs):
            starts[index] = now()
        return fn

    def post_hook(index):
        def fn(_module, _inputs, _output):
            per_block[index] += now() - starts[index]
        return fn

    for _ in range(warmup):
        forward_fn()

    total_sync = 0.0
    try:
        for i, block in enumerate(blocks):
            handles.append(block.register_forward_pre_hook(pre_hook(i)))
            handles.append(block.register_forward_hook(post_hook(i)))
        for _ in range(iters):
            t0 = now()
            forward_fn()
            total_sync += now() - t0
    finally:
        for handle in handles:
            handle.remove()

    t0 = now()
    for _ in range(iters):
        forward_fn()
    total_nosync = now() - t0

    return {
        "per_block_s": (per_block / iters).tolist(),
        "total_sync_s": total_sync / iters,
        "total_nosync_s": total_nosync / iters,
    }


# ---------------------------------------------------------------------------
# Heavy-dependency builders (lazy imports keep the pure functions above
# importable in environments without diffusers / the dataset stack)
# ---------------------------------------------------------------------------

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
    """EMA/raw selection with 'module.' stripping; returns (state, key)."""
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


def build_models(config, checkpoint_path, weights, device, ae_checkpoint):
    from omegaconf import OmegaConf  # noqa: E402
    from diffusers.models.autoencoders import AutoencoderKL  # noqa: E402
    from common.models.flowcast.rf_stdit import FlowCastSTDiTWrapper  # noqa: E402

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
    ae_model = ae_model.to(device).eval().requires_grad_(False)

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
    model = model.to(device).eval().requires_grad_(False)
    return ae_model, model, key_used


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--checkpoint", required=True,
                   help="FlowCast .pt (early_stopping_model.pt already holds "
                        "EMA weights under 'model_state_dict' -- use --weights raw "
                        "for it; --weights ema only for resume checkpoints that "
                        "carry a separate 'ema_model_state_dict').")
    p.add_argument("--data-file", required=True,
                   help="validation raw-pixel h5 (test paths are refused)")
    p.add_argument("--data-meta", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--ae-checkpoint", default=None,
                   help="override config.autoencoder_params.autoencoder_checkpoint")
    p.add_argument("--weights", choices=("ema", "raw"), default="raw")
    p.add_argument("--euler-steps", type=int, default=4,
                   help="tau grid source: build_sampling_timesteps(T, this)")
    p.add_argument("--taus", type=int, nargs="+", default=None,
                   help="explicit integer flow times in [1, T-1]; overrides "
                        "--euler-steps")
    p.add_argument("--chunk", type=int, default=1, choices=(1, 2),
                   help="probe chunk 1 (cond = clean history) or chunk 2 "
                        "(cond = clean previous target chunk, the training-"
                        "time teacher-forced wiring)")
    p.add_argument("--shuffle-mode", choices=("batch-roll", "temporal"),
                   default="batch-roll")
    p.add_argument("--max-events", type=int, default=32)
    p.add_argument("--micro-batch", type=int, default=4)
    p.add_argument("--members", type=int, default=DEPLOYED_MEMBERS)
    p.add_argument("--nfe", type=int, default=DEPLOYED_NFE)
    p.add_argument("--timing-iters", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


def main():
    args = parse_args()
    refuse_test_path(args.data_file, args.data_meta)

    from omegaconf import OmegaConf  # noqa: E402
    from torch.utils.data import DataLoader, Subset  # noqa: E402
    from common.models.flowcast.gated_rollout import build_codec_fns  # noqa: E402
    from common.models.flowcast.schedule import (  # noqa: E402
        build_sampling_timesteps,
        make_chunk_index,
    )
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

    if args.taus is not None:
        taus = sorted(set(int(t) for t in args.taus))
        if any(t < 1 or t > num_train_timesteps - 1 for t in taus):
            raise SystemExit(f"--taus must lie in [1, {num_train_timesteps - 1}]")
    else:
        grid = build_sampling_timesteps(num_train_timesteps, args.euler_steps, "cpu")
        # The model is evaluated at every boundary except the final t=0.
        taus = [int(t) for t in grid[:-1].tolist()]
    if len(taus) < 2:
        raise SystemExit("need at least 2 flow times to measure stability.")
    if args.micro_batch < 2 and args.shuffle_mode == "batch-roll":
        raise SystemExit("batch-roll shuffling needs --micro-batch >= 2.")

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
    rows = select_event_rows(len(dataset), args.max_events, seed_salt="scd")
    loader = DataLoader(Subset(dataset, rows), batch_size=args.micro_batch,
                        shuffle=False, collate_fn=dynamic_sequential_collate,
                        num_workers=2, pin_memory=device.type == "cuda",
                        drop_last=args.shuffle_mode == "batch-roll")

    ae_checkpoint = resolve_ae_checkpoint(config, args.ae_checkpoint)
    ae_model, model, weights_key = build_models(config, args.checkpoint,
                                                args.weights, device,
                                                ae_checkpoint)
    _decode_fn, encode_fn = build_codec_fns(ae_model, model, pixel_scale,
                                            normalized_ae)

    order = execution_order(config.stdit.depth)
    backbone = model.backbone
    blocks = [getattr(backbone, f"{kind}_blocks")[idx] for kind, idx in order]
    n_blocks = len(blocks)

    # Accumulators: per block, lists of per-(sample, tau-pair) cosines and
    # per-(sample, tau) sensitivities.
    cos_acc = [[] for _ in range(n_blocks)]
    r_acc = [[] for _ in range(n_blocks)]
    noise_gen = torch.Generator(device="cpu").manual_seed(args.seed)
    n_events = 0
    timing = None

    for batch_idx, batch in enumerate(loader):
        x_cond, x_true, _meta = batch
        x_hist = x_cond.squeeze(1).float().to(device) * (pixel_scale / 255.0)
        y_full = x_true.squeeze(1).float().to(device) * (pixel_scale / 255.0)
        with torch.no_grad():
            if args.chunk == 1:
                cond = encode_fn(x_hist)
                x_start = encode_fn(y_full[:, :input_length])
            else:
                cond = encode_fn(y_full[:, :input_length])
                x_start = encode_fn(y_full[:, input_length: 2 * input_length])
        cond_shuf = shuffle_condition(cond, args.shuffle_mode)
        t_seq = make_chunk_index(cond.shape[0], args.chunk, device)
        eps = torch.randn(x_start.shape, generator=noise_gen,
                          dtype=torch.float32).to(device)

        # deltas[l]: list over taus of (B, D) tensors; h_norms[l]: (B,) norms
        deltas = [[] for _ in range(n_blocks)]
        r_vals = [[] for _ in range(n_blocks)]
        for t_int in taus:
            t_vec = torch.full((cond.shape[0],), t_int, dtype=torch.long,
                               device=device)
            tau = t_int / float(num_train_timesteps - 1)
            x_t = tau * eps + (1.0 - tau) * x_start
            with torch.no_grad(), FeatureTap(blocks) as tap_real:
                model(x_t, t_vec, cond, t_seq)
                h_real = tap_real.take()
            with torch.no_grad(), FeatureTap(blocks) as tap_shuf:
                model(x_t, t_vec, cond_shuf, t_seq)
                h_shuf = tap_shuf.take()
            for l in range(n_blocks):
                delta = (h_real[l] - h_shuf[l]).cpu()
                deltas[l].append(delta)
                r_vals[l].append(condition_sensitivity(h_real[l].cpu(), delta))

        for l in range(n_blocks):
            stack = torch.stack(deltas[l], dim=0)  # (K, B, D)
            for b in range(stack.shape[1]):
                cos_acc[l].append(pairwise_cosines(stack[:, b, :]).numpy())
            r_acc[l].append(torch.stack(r_vals[l], dim=0).reshape(-1).numpy())
        n_events += int(cond.shape[0])
        print(f"  probed {n_events} events "
              f"({len(taus)} taus, chunk {args.chunk})", flush=True)

        if timing is None:
            t_vec = torch.full((cond.shape[0],), taus[len(taus) // 2],
                               dtype=torch.long, device=device)
            tau_mid = taus[len(taus) // 2] / float(num_train_timesteps - 1)
            x_t_mid = tau_mid * eps + (1.0 - tau_mid) * x_start

            def forward_fn():
                with torch.no_grad():
                    model(x_t_mid, t_vec, cond, t_seq)

            timing = measure_block_times(blocks, forward_fn,
                                         iters=args.timing_iters,
                                         device=device)

    if n_events == 0:
        raise SystemExit("no events probed -- check --max-events / --micro-batch.")

    per_block_s = np.asarray(timing["per_block_s"])
    total_sync = timing["total_sync_s"]
    block_records = []
    for l, (kind, idx) in enumerate(order):
        cosines = np.concatenate(cos_acc[l])
        r_all = np.concatenate(r_acc[l])
        block_records.append({
            "exec_index": l,
            "kind": kind,
            "index_within_kind": idx,
            "stage": stage_of(l, n_blocks),
            "s_median": float(np.median(cosines)),
            "s_p25": float(np.percentile(cosines, 25)),
            "s_p75": float(np.percentile(cosines, 75)),
            "r_median": float(np.median(r_all)),
            "r_p25": float(np.percentile(r_all, 25)),
            "r_p75": float(np.percentile(r_all, 75)),
            "time_s": float(per_block_s[l]),
            "time_share": float(per_block_s[l] / max(total_sync, NORM_EPS)),
            "cacheable": bool(np.median(cosines) >= S_CACHE_THRESHOLD),
        })

    p_cond = float(
        per_block_s[[r["cacheable"] for r in block_records]].sum()
        / max(total_sync, NORM_EPS)
    )
    verdict = evaluate_scd_gates(block_records, p_cond,
                                 members=args.members, nfe=args.nfe)

    out = {
        "n_events": n_events,
        "taus": taus,
        "chunk": args.chunk,
        "shuffle_mode": args.shuffle_mode,
        "weights_key": weights_key,
        "dataset": dataset_name,
        "blocks": block_records,
        "timing": {
            "total_sync_s": timing["total_sync_s"],
            "total_nosync_s": timing["total_nosync_s"],
            "block_sum_s": float(per_block_s.sum()),
            "overhead_share": float(
                1.0 - per_block_s.sum() / max(total_sync, NORM_EPS)
            ),
            "timing_iters": args.timing_iters,
        },
        "verdict": verdict,
        "provenance": {
            "config": os.path.abspath(args.config),
            "config_sha256": sha256_file(args.config),
            "checkpoint": os.path.abspath(args.checkpoint),
            "checkpoint_sha256": sha256_file(args.checkpoint),
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
