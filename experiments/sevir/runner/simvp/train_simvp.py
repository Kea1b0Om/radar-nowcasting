"""
SimVP calibration baseline.

This trains SimVP on raw pixel frames through *our* dataloader and scores it
through *our* MetricsAccumulator, so the resulting CSI-M is directly comparable
to the FlowCast/CRFT numbers produced by test_flowcast.py.

The point is not to build a good model.  It is to check whether our pipeline
lands on the published CIKM scale (SDIR reports SimVP CSI-M = 0.3047, DuoCast
reports 0.3052).  If we reproduce ~0.305, every number our pipeline emits can be
placed next to the published tables.  If we land far above it, the discrepancy
is in our pipeline and must be found before any comparison is written up.

Usage:
    python -m experiments.sevir.runner.simvp.train_simvp \
        --config experiments/cikm/runner/simvp/simvp_config_cikm.yaml
    python -m experiments.sevir.runner.simvp.train_simvp \
        --config ... --eval_only --checkpoint <path>
"""

import argparse
import os
import random
import sys
import time

import numpy as np
import torch
from omegaconf import OmegaConf
from torch.utils.data import DataLoader, Subset
from tqdm import tqdm

sys.path.append(os.getcwd())

from common.models.simvp.simvp_iter import SimVP_Model, configs as simvp_configs
from common.metrics.metrics_streaming_probabilistic import MetricsAccumulator
from common.utils.utils import calculate_metrics
from experiments.sevir.dataset.sevirfulldataset import (
    DynamicSequentialSevirDataset,
    dynamic_sequential_collate,
    post_process_samples,
)

DEBUG_PRINT_PREFIX = "[SimVP] "


def raw_to_eval_scale(tensor, dataset_name, pixel_scale):
    """Identical to test_flowcast.raw_to_eval_scale -- do not diverge."""
    del dataset_name  # the scale is fully determined by pixel_scale
    return tensor * (pixel_scale / 255.0)


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_loader(meta_csv, data_file, cfg, batch_size, num_workers, shuffle):
    dataset = DynamicSequentialSevirDataset(
        meta_csv=meta_csv,
        data_file=data_file,
        data_type=cfg.data_key,
        raw_seq_len=cfg.raw_seq_len,
        lag_time=cfg.input_length,
        lead_time=cfg.output_length,
        time_spacing=cfg.time_spacing,
        stride=cfg.stride,
        channel_last=False,
        debug_mode=cfg.debug_mode,
    )
    if cfg.debug_mode:
        dataset = Subset(dataset, range(min(len(dataset), 64)))
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=dynamic_sequential_collate,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=shuffle,
    )
    return dataset, loader


def to_model_input(x, dataset_name):
    """(B, C, T, H, W) raw 0..255 -> (B, T, C, H, W) in [0, 1]."""
    x = x.permute(0, 2, 1, 3, 4).contiguous()
    if dataset_name == "cikm":
        x = x / 255.0
    return x


@torch.no_grad()
def evaluate(model, loader, cfg, device, max_batches=None, desc="Eval"):
    """Scores SimVP exactly the way test_flowcast.py scores FlowCast.

    Predictions carry a singleton ensemble axis (S=1), matching the S=1 protocol
    the FlowCast baselines were re-run under.
    """
    model.eval()
    thresholds = np.array(cfg.thresholds, dtype=np.float32)
    accumulators = [
        MetricsAccumulator(
            lead_time=lead_time,
            thresholds=thresholds,
            pool_size=16,
            compute_mse=True,
            compute_threshold=True,
            compute_crps=True,
            compute_fss=True,
            fss_scales=[1, 4, 16],
            device=device,
        )
        for lead_time in range(cfg.output_length)
    ]

    y_pred_buf, y_true_buf = [], []

    def flush():
        if not y_pred_buf:
            return
        y_pred_array = post_process_samples(
            np.concatenate(y_pred_buf, axis=0), clamp_min=0.0, clamp_max=cfg.pixel_scale
        )
        y_true_array = np.concatenate(y_true_buf, axis=0)
        for acc in accumulators:
            acc.update(y_true_array, y_pred_array)
        y_pred_buf.clear()
        y_true_buf.clear()

    for idx, batch in enumerate(tqdm(loader, desc=desc, leave=False)):
        if max_batches is not None and idx >= max_batches:
            break
        x_cond, x_true, _ = batch
        x_cond = to_model_input(x_cond, cfg.dataset_name).to(device, non_blocking=True)

        frames_pred, _ = model.predict(frames_in=x_cond, compute_loss=False)

        # (B, T, C, H, W) in [0, 1] -> (B, T, H, W) on the metric scale.
        x_pred = frames_pred.squeeze(2) * cfg.pixel_scale
        x_true = x_true.squeeze(1)
        if cfg.dataset_name == "cikm":
            x_pred = x_pred[:, :, 13:-14, 13:-14]
            x_true = x_true[:, :, 13:-14, 13:-14]
        x_true = raw_to_eval_scale(x_true, cfg.dataset_name, cfg.pixel_scale)

        y_pred_buf.append(
            x_pred.unsqueeze(1).cpu().numpy().astype(np.float16)
        )  # (B, S=1, T, H, W)
        y_true_buf.append(x_true.cpu().numpy())

        if len(y_pred_buf) * loader.batch_size >= 400:
            flush()

    flush()
    results = calculate_metrics(
        num_lead_times=cfg.output_length,
        metrics_accumulators=accumulators,
        thresholds=thresholds,
    )
    model.train()
    return results


def report(results, tag):
    print(f"\n{'=' * 30} {tag} {'=' * 30}")
    print(f"CSI-M            : {results['csi_from_mean_m']:.4f}")
    print(f"HSS-M            : {results['hss_from_mean_m']:.4f}")
    print(f"POD-M            : {results['pod_from_mean_m']:.4f}")
    print(f"FAR-M            : {results['far_from_mean_m']:.4f}")
    print(f"MSE              : {results['mse_from_mean_mean']:.4f}")
    print(f"CRPS             : {results['crps_mean']:.4f}")
    print(f"CSI (16-pooled)-M: {results['csi_pool_from_mean_m']:.4f}")
    print(f"CSI per threshold: {results['csi_from_mean_mean']}")
    print(f"HSS per threshold: {results['hss_from_mean_mean']}")
    print(f"CSI-M by lead time: {results['csi_m_from_mean_lead_time']}")
    print("=" * (62 + len(tag)) + "\n", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--data_dir", default=None)
    parser.add_argument("--eval_only", action="store_true")
    parser.add_argument("--checkpoint", default=None)
    args = parser.parse_args()

    config = OmegaConf.load(args.config)
    sel = lambda k, d=None: OmegaConf.select(config, k, default=d)

    dataset_name = sel("data_params.dataset_name", "cikm")
    data_dir = args.data_dir or f"datasets/{dataset_name}/data/{dataset_name}_full"

    cfg = OmegaConf.create(
        {
            "dataset_name": dataset_name,
            "data_key": sel("data_params.data_key", "vil"),
            "raw_seq_len": sel("data_params.raw_seq_len", 15),
            "input_length": sel("data_params.input_length", 5),
            "output_length": sel("data_params.output_length", 10),
            "time_spacing": sel("data_params.time_spacing", 1),
            "stride": sel("data_params.stride", 1),
            "pixel_scale": sel("evaluation_params.pixel_scale", 90.0),
            "thresholds": list(sel("evaluation_params.thresholds", [20, 30, 35, 40])),
            "debug_mode": bool(sel("run_params.debug_mode", False)),
        }
    )

    if cfg.output_length % cfg.input_length != 0:
        raise ValueError(
            "SimVP rolls out in blocks of input_length; output_length must be a multiple."
        )

    seed = int(sel("run_params.seed", 0))
    set_seed(seed)

    batch_size = int(sel("training_params.micro_batch_size", 16))
    test_batch_size = int(sel("test_params.micro_batch_size", batch_size))
    num_workers = int(sel("training_params.num_workers", 8))
    num_epochs = int(sel("training_params.num_epochs", 100))
    patience = int(sel("training_params.early_stopping_patience", 20))
    clip_val = float(sel("training_params.gradient_clip_val", 1.0))
    lr = float(sel("optimizer_params.learning_rate", 1e-3))
    weight_decay = float(sel("optimizer_params.weight_decay", 0.0))

    best_path = sel("run_params.best_model_path", "artifacts/cikm/simvp/best.pt")
    latest_path = sel("run_params.resume_latest_path", "artifacts/cikm/simvp/latest.pt")
    os.makedirs(os.path.dirname(best_path), exist_ok=True)

    for key, value in simvp_configs.items():
        override = sel(f"simvp.{key}")
        if override is not None:
            simvp_configs[key] = override

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    _, train_loader = build_loader(
        f"{data_dir}/nowcast_training_full_META.csv",
        f"{data_dir}/nowcast_training_full.h5",
        cfg,
        batch_size,
        num_workers,
        shuffle=True,
    )
    _, val_loader = build_loader(
        f"{data_dir}/nowcast_validation_full_META.csv",
        f"{data_dir}/nowcast_validation_full.h5",
        cfg,
        test_batch_size,
        num_workers,
        shuffle=False,
    )
    _, test_loader = build_loader(
        f"{data_dir}/nowcast_testing_full_META.csv",
        f"{data_dir}/nowcast_testing_full.h5",
        cfg,
        test_batch_size,
        num_workers,
        shuffle=False,
    )

    sample_x, _, _ = next(iter(val_loader))
    _, C, _, H, W = sample_x.shape
    print(
        f"{DEBUG_PRINT_PREFIX}train={len(train_loader.dataset)} "
        f"val={len(val_loader.dataset)} test={len(test_loader.dataset)} "
        f"frame=({C},{H},{W}) {cfg.input_length}->{cfg.output_length} "
        f"thresholds={cfg.thresholds} pixel_scale={cfg.pixel_scale}",
        flush=True,
    )

    model = SimVP_Model(
        in_shape=(C, H, W), T_in=cfg.input_length, T_out=cfg.output_length
    ).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"{DEBUG_PRINT_PREFIX}SimVP parameters: {n_params / 1e6:.2f}M", flush=True)

    if args.eval_only:
        ckpt_path = args.checkpoint or best_path
        state = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(state["model"])
        print(
            f"{DEBUG_PRINT_PREFIX}Loaded {ckpt_path} "
            f"(epoch {state.get('epoch')}, val CSI-M {state.get('val_csi_m')})",
            flush=True,
        )
        report(evaluate(model, test_loader, cfg, device, desc="Test"), "TEST (4000)")
        return

    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    steps_per_epoch = max(1, len(train_loader))
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=lr, total_steps=num_epochs * steps_per_epoch
    )
    criterion = torch.nn.MSELoss()

    best_csi = -1.0
    best_epoch = -1
    epochs_without_improvement = 0

    for epoch in range(num_epochs):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        t0 = time.time()
        bar = tqdm(train_loader, desc=f"Epoch {epoch}", leave=False)
        for x_cond, x_true, _ in bar:
            x_cond = to_model_input(x_cond, cfg.dataset_name).to(
                device, non_blocking=True
            )
            x_gt = to_model_input(x_true, cfg.dataset_name).to(device, non_blocking=True)

            frames_pred, _ = model.predict(frames_in=x_cond, compute_loss=False)
            loss = criterion(frames_pred, x_gt)

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            if clip_val > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), clip_val)
            optimizer.step()
            scheduler.step()

            epoch_loss += loss.item()
            n_batches += 1
            bar.set_postfix(loss=f"{loss.item():.5f}")

        val_results = evaluate(model, val_loader, cfg, device, desc="Val")
        val_csi = float(val_results["csi_from_mean_m"])
        print(
            f"{DEBUG_PRINT_PREFIX}epoch {epoch} "
            f"train_mse={epoch_loss / max(1, n_batches):.6f} "
            f"val_csi_m={val_csi:.4f} "
            f"lr={scheduler.get_last_lr()[0]:.2e} "
            f"time={time.time() - t0:.0f}s",
            flush=True,
        )

        torch.save(
            {"model": model.state_dict(), "epoch": epoch, "val_csi_m": val_csi},
            latest_path,
        )
        if val_csi > best_csi:
            best_csi = val_csi
            best_epoch = epoch
            epochs_without_improvement = 0
            torch.save(
                {"model": model.state_dict(), "epoch": epoch, "val_csi_m": val_csi},
                best_path,
            )
            print(
                f"{DEBUG_PRINT_PREFIX}new best val CSI-M {best_csi:.4f} -> {best_path}",
                flush=True,
            )
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print(
                    f"{DEBUG_PRINT_PREFIX}early stopping at epoch {epoch} "
                    f"(best {best_csi:.4f} @ epoch {best_epoch})",
                    flush=True,
                )
                break

    state = torch.load(best_path, map_location=device)
    model.load_state_dict(state["model"])
    print(
        f"{DEBUG_PRINT_PREFIX}Final test with best checkpoint "
        f"(epoch {state['epoch']}, val CSI-M {state['val_csi_m']:.4f})",
        flush=True,
    )
    report(evaluate(model, test_loader, cfg, device, desc="Test"), "TEST (4000)")


if __name__ == "__main__":
    main()
