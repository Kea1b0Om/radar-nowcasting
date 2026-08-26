"""Step 1b: score checkpoints on validation and dump EVENT-LEVEL statistics.

This does inference only.  It never picks a winner -- ``select_checkpoint.py``
does that offline from the dumps, so re-scoring under different stratum
weights costs nothing and never needs a GPU again.

Protocol (all of it read from the frozen rule, not from flags):
  * full validation split, fixed sample order (``shuffle=False``);
  * common random numbers -- member noise is drawn from an explicit
    ``torch.Generator`` seeded ``base_seed + batch_index * S + sample_index``,
    so every checkpoint sees the identical noise sequence and checkpoint
    differences are paired;
  * float32 accumulation (the legacy ``test_flowcast.py`` path casts
    predictions to float16; that is fine for a headline number but throws
    away resolution we need to rank near-tied checkpoints);
  * stage 1 = S=1 over every checkpoint, stage 2 = S=8 over the shortlist.

Everything else -- the 13:-14 crop back to 101x101, ``pixel_scale`` 90,
thresholds [20,30,35,40], strict ``>``, max-pool-16 for the pooled CSI,
clamping to [0, pixel_scale] -- is copied from ``test_flowcast.py`` so the
per-event counts aggregate to the same micro CSI the published tables use.

EMA and raw checkpoints must not be ranked against each other (an EMA at
decay 0.999 has already filtered out recent trajectory noise; comparing it
to a raw checkpoint compares different objects).  The script refuses a mixed
pool unless you force it.

Example
-------
    python tools/score_checkpoints.py \
        --config experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml \
        --rule artifacts/cikm/selection/selection_rule.json \
        --stage 1 \
        --checkpoint_glob 'artifacts/cikm/selection/pool/*.pt' \
        --out_dir artifacts/cikm/selection/dumps
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F
from omegaconf import OmegaConf
from torch.utils.data import DataLoader

sys.path.append(os.getcwd())
os.environ.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")

from common.metrics.crps import crps_ensemble  # noqa: E402
from common.models.flowcast.rf_stdit import (  # noqa: E402
    FlowCastSTDiTWrapper,
    autoregressive_sample,
)
from experiments.sevir.dataset.sevirfulldataset import (  # noqa: E402
    DynamicSequentialSevirDataset,
    dynamic_sequential_collate,
)
from tools.selection_rule import SelectionRule, sha256_file  # noqa: E402

DUMP_SCHEMA_VERSION = 1


# --------------------------------------------------------------------------
# checkpoint handling
# --------------------------------------------------------------------------
def classify_checkpoint(payload: dict) -> str:
    """Which *object* the weights are: an EMA average or a raw iterate.

    These must never be ranked against each other -- an EMA at decay 0.999
    has already filtered out recent trajectory noise, so it is not the same
    thing as the raw weights at the same step.

    Periodic snapshots say so explicitly (``is_ema``).  For the older files
    we infer: ``EarlyStopping.save_checkpoint`` (common/utils/utils.py)
    stores model+optimizer+best_metric with no scheduler and no epoch, and
    the model it is handed is the EMA copy whenever ``ema_model_saving`` is
    on; the ``*_latest.pt`` rescue path additionally stores
    scheduler_state_dict and epoch, and always holds raw weights.
    """
    if "is_ema" in payload:
        return "ema" if payload["is_ema"] else "raw"
    if "scheduler_state_dict" in payload:
        return "raw"
    return "ema"


def is_resumable(payload: dict) -> bool:
    """Whether training can continue from this file.

    Orthogonal to ema/raw: a periodic snapshot holds weights only, so it can
    be scored and reported but not resumed.  Resuming needs the raw model
    plus optimizer plus scheduler plus global step.
    """
    return all(
        k in payload
        for k in ("model_state_dict", "optimizer_state_dict", "scheduler_state_dict")
    )


def load_checkpoint_meta(path: str) -> dict:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if "model_state_dict" not in payload:
        raise ValueError(f"{path}: no 'model_state_dict' key")
    mean = payload.get("mean", None)
    std = payload.get("std", None)
    # These are stored as 0-dim tensors.  Note `.get("mean", 0.0)` returns
    # None when the key exists holding None, so the default is not a safety
    # net -- check explicitly.
    if mean is None:
        print(f"[warn] {path}: no 'mean' stored, falling back to 0.0")
        mean = 0.0
    if std is None:
        print(f"[warn] {path}: no 'std' stored, falling back to 1.0")
        std = 1.0
    return {
        "payload": payload,
        "kind": classify_checkpoint(payload),
        "resumable": is_resumable(payload),
        "global_step": int(payload.get("global_step", -1)),
        "epoch": int(payload["epoch"]) if payload.get("epoch") is not None else -1,
        "best_metric": payload.get("best_metric", None),
        "mean": float(mean),
        "std": float(std),
    }


# --------------------------------------------------------------------------
# per-event accumulation
# --------------------------------------------------------------------------
def event_statistics(
    y_true: torch.Tensor,
    y_pred: torch.Tensor,
    thresholds: torch.Tensor,
    pool_size: int = 16,
    crps_estimator: str = "almost_fair",
) -> dict:
    """Per-event contingency + error statistics for one batch.

    Args:
        y_true: (B, T, H, W) float32 on the evaluation scale.
        y_pred: (B, S, T, H, W) float32 on the evaluation scale, clamped.
        thresholds: (Q,) float32.

    Returns arrays with leading dim B.
    """
    B, S, T, H, W = y_pred.shape
    Q = thresholds.numel()
    mean_pred = y_pred.mean(dim=1)  # (B, T, H, W)

    th = thresholds.view(1, 1, Q, 1, 1)
    t_bin = (y_true.unsqueeze(2) > th)          # (B, T, Q, H, W)
    p_bin = (mean_pred.unsqueeze(2) > th)

    tp = (t_bin & p_bin).sum(dim=(-1, -2))
    fn = (t_bin & ~p_bin).sum(dim=(-1, -2))
    fp = (~t_bin & p_bin).sum(dim=(-1, -2))
    tn = (~t_bin & ~p_bin).sum(dim=(-1, -2))

    # pooled (max-pool 16, stride 16) -- identical to MetricsAccumulator,
    # including the fact that 101 // 16 = 6 drops the right/bottom edge.
    if pool_size > 1:
        yt = F.max_pool2d(
            y_true.reshape(B * T, 1, H, W), kernel_size=pool_size, stride=pool_size
        ).reshape(B, T, 1, -1)
        yp = F.max_pool2d(
            mean_pred.reshape(B * T, 1, H, W), kernel_size=pool_size, stride=pool_size
        ).reshape(B, T, 1, -1)
        th_p = thresholds.view(1, 1, Q, 1)
        tb = yt > th_p
        pb = yp > th_p
        tp_pool = (tb & pb).sum(dim=-1)
        fn_pool = (tb & ~pb).sum(dim=-1)
        fp_pool = (~tb & pb).sum(dim=-1)
    else:
        tp_pool, fn_pool, fp_pool = tp.clone(), fn.clone(), fp.clone()

    diff2 = (mean_pred - y_true) ** 2
    sse = diff2.sum(dim=(-1, -2))                       # (B, T)
    npix = torch.full_like(sse, float(H * W))

    # fair CRPS.  With S == 1 every estimator degenerates to |x - y| (MAE);
    # that is recorded honestly rather than compared against an S=8 number.
    crps_map = crps_ensemble(
        y_true.reshape(B, T * H * W),
        y_pred.reshape(B, S, T * H * W),
        estimator=crps_estimator,
    ).reshape(B, T, H, W)
    crps_sum = crps_map.sum(dim=(-1, -2))

    if S > 1:
        spread_sum = y_pred.std(dim=1, unbiased=True).sum(dim=(-1, -2))
    else:
        spread_sum = torch.zeros_like(sse)

    return {
        "tp": tp.to(torch.int64).cpu().numpy(),
        "fn": fn.to(torch.int64).cpu().numpy(),
        "fp": fp.to(torch.int64).cpu().numpy(),
        "tn": tn.to(torch.int64).cpu().numpy(),
        "tp_pool": tp_pool.to(torch.int64).cpu().numpy(),
        "fn_pool": fn_pool.to(torch.int64).cpu().numpy(),
        "fp_pool": fp_pool.to(torch.int64).cpu().numpy(),
        "sse": sse.to(torch.float64).cpu().numpy(),
        "npix": npix.to(torch.float64).cpu().numpy(),
        "crps_sum": crps_sum.to(torch.float64).cpu().numpy(),
        "spread_sum": spread_sum.to(torch.float64).cpu().numpy(),
    }


# --------------------------------------------------------------------------
def build_autoencoder(config, device):
    from diffusers.models.autoencoders import AutoencoderKL

    ap = config.autoencoder_params
    ae = AutoencoderKL(
        in_channels=1,
        out_channels=1,
        down_block_types=ap.down_block_types,
        up_block_types=ap.up_block_types,
        block_out_channels=ap.block_out_channels,
        act_fn=ap.act_fn,
        latent_channels=ap.latent_channels,
        norm_num_groups=ap.norm_num_groups,
        layers_per_block=ap.layers_per_block,
    )
    ck = torch.load(ap.autoencoder_checkpoint, map_location="cpu", weights_only=False)
    sd = {k.replace("module.", "", 1) if k.startswith("module.") else k: v
          for k, v in ck["model_state_dict"].items()}
    ae.load_state_dict(sd)
    return ae.to(device).eval()


def score_one_checkpoint(
    ckpt_path: str,
    *,
    config,
    rule: SelectionRule,
    stage: int,
    ae_model,
    loader,
    device,
    out_dir: str,
    config_path: str,
    kind_override: str | None = None,
) -> str:
    """Run inference for one checkpoint and write its event-level dump."""
    dp = config.data_params
    ep = config.evaluation_params
    S = rule.stage1_samples if stage == 1 else rule.stage2_samples
    thresholds = torch.tensor(list(rule.thresholds), device=device, dtype=torch.float32)
    pixel_scale = float(rule.pixel_scale)
    crop = rule.crop
    input_length = int(dp.input_length)
    output_length = int(dp.output_length)

    meta = load_checkpoint_meta(ckpt_path)
    kind = kind_override or meta["kind"]

    # peek one batch for latent shape
    first = next(iter(loader))
    with torch.no_grad():
        peek = first[0][:, :, 0, :, :].to(device)
        if bool(config.autoencoder_params.normalized_autoencoder):
            peek = peek / 255.0
        latent_channels = ae_model.encode(peek).latent_dist.mode().shape[1]

    model = FlowCastSTDiTWrapper(
        latent_channels=latent_channels,
        hidden_size=config.stdit.hidden_size,
        depth=config.stdit.depth,
        num_heads=config.stdit.num_heads,
        patch_size=tuple(config.stdit.patch_size),
        mlp_ratio=OmegaConf.select(config, "stdit.mlp_ratio", default=4.0),
        drop_path=OmegaConf.select(config, "stdit.drop_path", default=0.0),
        qk_norm=OmegaConf.select(config, "stdit.qk_norm", default=True),
        mean=meta["mean"],
        std=meta["std"],
    )
    missing, unexpected = model.load_state_dict(meta["payload"]["model_state_dict"],
                                                strict=False)
    if missing or unexpected:
        raise ValueError(
            f"{ckpt_path}: state_dict mismatch "
            f"(missing={len(missing)}, unexpected={len(unexpected)}); "
            f"the config's STDiT dims probably do not match this checkpoint."
        )
    model = model.to(device).eval()
    del meta["payload"]

    n_events = len(loader.dataset)
    T, Q = output_length, len(rule.thresholds)
    acc = {
        "tp": np.zeros((n_events, T, Q), np.int64),
        "fn": np.zeros((n_events, T, Q), np.int64),
        "fp": np.zeros((n_events, T, Q), np.int64),
        "tn": np.zeros((n_events, T, Q), np.int64),
        "tp_pool": np.zeros((n_events, T, Q), np.int64),
        "fn_pool": np.zeros((n_events, T, Q), np.int64),
        "fp_pool": np.zeros((n_events, T, Q), np.int64),
        "sse": np.zeros((n_events, T), np.float64),
        "npix": np.zeros((n_events, T), np.float64),
        "crps_sum": np.zeros((n_events, T), np.float64),
        "spread_sum": np.zeros((n_events, T), np.float64),
    }
    member_seed = np.zeros((n_events, S), np.int64)
    severity_check = np.zeros(n_events, np.float64)

    normalized_ae = bool(config.autoencoder_params.normalized_autoencoder)
    ae_batch = config.test_params.batch_size_autoencoder
    euler_steps = int(rule.euler_steps)
    num_train_timesteps = int(config.rflow_params.num_train_timesteps)

    cursor = 0
    t0 = time.time()
    for batch_idx, (x_cond, x_true, _meta) in enumerate(loader):
        B = x_cond.shape[0]
        Cc, T_in, H, W = x_cond.shape[1:]
        x_cond = x_cond.permute(0, 2, 1, 3, 4).reshape(B * T_in, Cc, H, W).to(device)
        with torch.no_grad():
            if normalized_ae:
                x_cond = x_cond / 255.0
            z = ae_model.encode(x_cond).latent_dist.mode()
        lc, lh, lw = z.shape[1], z.shape[2], z.shape[3]
        z = z.reshape(B, T_in, lc, lh, lw).permute(0, 1, 3, 4, 2).contiguous()
        z = model.normalize(z)

        # ---- ground truth on the evaluation scale --------------------
        x_true = x_true.squeeze(1)
        if crop is not None:
            lo, hi = crop
            x_true = x_true[:, :, lo:hi, lo:hi]
        x_true = (x_true * (pixel_scale / 255.0)).to(device).float()

        # ---- ensemble ------------------------------------------------
        members = []
        for s in range(S):
            seed = rule.base_seed + batch_idx * S + s
            member_seed[cursor:cursor + B, s] = seed
            gen = torch.Generator(device=device)
            gen.manual_seed(seed)
            with torch.no_grad():
                pred = autoregressive_sample(
                    model=model,
                    initial_cond=z,
                    input_length=input_length,
                    output_length=output_length,
                    num_train_timesteps=num_train_timesteps,
                    euler_steps=euler_steps,
                    generator=gen,
                )
                pred = model.denormalize(pred)
            members.append(pred.unsqueeze(1))
        pred = torch.cat(members, dim=1)  # (B, S, T, lh, lw, lc)

        Bp, Sp, Tp = pred.shape[:3]
        pred = pred.reshape(Bp * Sp * Tp, lh, lw, lc).permute(0, 3, 1, 2).contiguous()
        with torch.no_grad():
            if ae_batch:
                chunks = [ae_model.decode(pred[i:i + ae_batch]).sample
                          for i in range(0, pred.shape[0], ae_batch)]
                pred = torch.cat(chunks, dim=0)
            else:
                pred = ae_model.decode(pred).sample
        pred = pred * pixel_scale if normalized_ae else pred
        if crop is not None:
            lo, hi = crop
            pred = pred[:, :, lo:hi, lo:hi]
        pred = pred.reshape(Bp, Sp, Tp, pred.shape[-2], pred.shape[-1]).float()
        pred = pred.clamp(0.0, pixel_scale)

        stats = event_statistics(x_true, pred, thresholds)
        for k, v in stats.items():
            acc[k][cursor:cursor + B] = v
        # severity recomputed here purely as a tripwire against a
        # rule/dataset mismatch (different h5, different crop, ...)
        sev = torch.zeros(B, device=device)
        for th in thresholds:
            sev += (x_true > th).sum(dim=(1, 2, 3)).float()
        severity_check[cursor:cursor + B] = (
            sev / float(x_true.shape[1] * x_true.shape[2] * x_true.shape[3])
        ).cpu().numpy()

        cursor += B
        if batch_idx % 25 == 0:
            done = cursor / max(n_events, 1)
            el = time.time() - t0
            print(f"    {cursor}/{n_events} ({done:5.1%})  "
                  f"{el:6.0f}s elapsed, eta {el / max(done, 1e-9) - el:6.0f}s",
                  flush=True)

    if cursor != n_events:
        raise RuntimeError(f"processed {cursor} events, expected {n_events}")

    tag = os.path.splitext(os.path.basename(ckpt_path))[0]
    os.makedirs(out_dir, exist_ok=True)
    npz_path = os.path.join(out_dir, f"stage{stage}__{tag}.npz")
    np.savez_compressed(
        npz_path,
        event_id=np.arange(n_events, dtype=np.int64),
        member_seed=member_seed,
        severity_check=severity_check,
        **acc,
    )
    manifest = {
        "dump_schema_version": DUMP_SCHEMA_VERSION,
        "stage": stage,
        "checkpoint_path": os.path.abspath(ckpt_path),
        "checkpoint_sha256": sha256_file(ckpt_path),
        "checkpoint_type": kind,
        "checkpoint_resumable": meta["resumable"],
        "checkpoint_epoch": meta["epoch"],
        "checkpoint_global_step": meta["global_step"],
        "checkpoint_best_metric": (
            float(meta["best_metric"]) if meta["best_metric"] is not None else None
        ),
        "mean": meta["mean"],
        "std": meta["std"],
        "samples": S,
        "batch_size": loader.batch_size,
        "euler_steps": euler_steps,
        "num_train_timesteps": num_train_timesteps,
        "dtype": "float32",
        "seed_formula": rule.seed_formula,
        "base_seed": rule.base_seed,
        "thresholds": list(rule.thresholds),
        "pixel_scale": pixel_scale,
        "crop": rule.crop,
        "pool_size": 16,
        "crps_estimator": "almost_fair",
        "n_events": n_events,
        "rule_sha256": rule.payload_hash(),
        "config": os.path.abspath(config_path),
        "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "wall_seconds": round(time.time() - t0, 1),
    }
    with open(npz_path.replace(".npz", ".json"), "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"    -> {npz_path}")
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return npz_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--rule", required=True)
    ap.add_argument("--stage", type=int, choices=(1, 2), required=True)
    ap.add_argument("--checkpoints", nargs="*", default=[])
    ap.add_argument("--checkpoint_glob", default=None)
    ap.add_argument("--out_dir", default="artifacts/cikm/selection/dumps")
    ap.add_argument("--val_h5", default=None)
    ap.add_argument("--val_meta", default=None)
    ap.add_argument("--num_workers", type=int, default=4)
    ap.add_argument("--allow_mixed_types", action="store_true")
    ap.add_argument("--limit_events", type=int, default=0, help="smoke test only")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    config = OmegaConf.load(args.config)
    rule = SelectionRule.load(args.rule)
    print(f"rule ok, sha256 = {rule.payload_hash()[:16]}...")

    paths = list(args.checkpoints)
    if args.checkpoint_glob:
        paths += sorted(glob.glob(args.checkpoint_glob))
    paths = sorted(dict.fromkeys(os.path.abspath(p) for p in paths))
    if not paths:
        raise SystemExit("no checkpoints given (--checkpoints / --checkpoint_glob)")

    kinds = {}
    for p in paths:
        head = torch.load(p, map_location="cpu", weights_only=False)
        kinds[p] = classify_checkpoint(head)
        del head
    distinct = set(kinds.values())
    print(f"{len(paths)} checkpoints, types: "
          + ", ".join(f"{k}={sum(v == k for v in kinds.values())}" for k in distinct))
    if len(distinct) > 1 and not args.allow_mixed_types:
        for p, k in kinds.items():
            print(f"  [{k}] {p}")
        raise SystemExit(
            "refusing to rank EMA and raw checkpoints in one pool: an EMA "
            "(decay 0.999) has already averaged away recent trajectory noise, "
            "so it is not the same object as a raw snapshot.  Score them in "
            "separate runs, or pass --allow_mixed_types if you really mean to."
        )
    if distinct == {"raw"}:
        print(
            "[note] this pool is raw weights.  Selection and the final test "
            "report should use EMA checkpoints; raw ones are for resuming "
            "training (they carry optimizer + scheduler state)."
        )

    dp = config.data_params
    data_dir = f"datasets/{dp.dataset_name}/data/{dp.dataset_name}_full"
    val_h5 = args.val_h5 or f"{data_dir}/nowcast_validation_full.h5"
    val_meta = args.val_meta or f"{data_dir}/nowcast_validation_full_META.csv"
    if "test" in os.path.basename(val_h5).lower():
        raise SystemExit("this script scores validation only; test is off limits here")

    got = sha256_file(val_h5)
    if got != rule.val_h5_sha256:
        raise SystemExit(
            f"validation h5 hash mismatch:\n  rule says {rule.val_h5_sha256}\n"
            f"  file is  {got}\nThe frozen strata refer to a different file."
        )

    dataset = DynamicSequentialSevirDataset(
        meta_csv=val_meta,
        data_file=val_h5,
        data_type=dp.data_key,
        raw_seq_len=dp.raw_seq_len,
        lag_time=dp.input_length,
        lead_time=dp.output_length,
        time_spacing=dp.time_spacing,
        stride=dp.stride,
        channel_last=False,
        debug_mode=False,
    )
    if len(dataset) != len(rule.val_event_id):
        raise SystemExit(
            f"dataset has {len(dataset)} samples but the rule assigns "
            f"{len(rule.val_event_id)} events.  For CIKM these must be equal "
            f"(one sequence per event)."
        )
    if args.limit_events:
        from torch.utils.data import Subset
        dataset = Subset(dataset, range(args.limit_events))
        print(f"[smoke] limited to {len(dataset)} events -- dumps are NOT valid "
              f"for selection")

    batch_size = rule.stage1_batch_size if args.stage == 1 else rule.stage2_batch_size
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=dynamic_sequential_collate,
        num_workers=args.num_workers,
        pin_memory=True,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}  stage={args.stage}  S="
          f"{rule.stage1_samples if args.stage == 1 else rule.stage2_samples}  "
          f"batch_size={batch_size}")

    ae_model = build_autoencoder(config, device)

    for i, p in enumerate(paths, 1):
        tag = os.path.splitext(os.path.basename(p))[0]
        out = os.path.join(args.out_dir, f"stage{args.stage}__{tag}.npz")
        if os.path.exists(out) and not args.overwrite:
            print(f"[{i}/{len(paths)}] skip (exists): {out}")
            continue
        print(f"[{i}/{len(paths)}] {p}")
        score_one_checkpoint(
            p,
            config=config,
            rule=rule,
            stage=args.stage,
            ae_model=ae_model,
            loader=loader,
            device=device,
            out_dir=args.out_dir,
            config_path=args.config,
            kind_override=kinds[p],
        )


if __name__ == "__main__":
    main()
