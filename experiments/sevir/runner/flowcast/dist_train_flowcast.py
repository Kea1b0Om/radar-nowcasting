"""
Distributed training script for the FlowCast model on the SEVIR dataset.

This script uses `torchrun` for multi-GPU/multi-node training. It trains an
RFLOW-style model with an STDiT backbone on latent SEVIR sequences using
chunked autoregressive prediction. Training is configured via a YAML file and
includes features like partial evaluation, EMA checkpointing, early stopping,
and WandB logging.
"""

import sys
import os
import copy
import hashlib
import argparse
import datetime
import random
import numpy as np
import wandb
try:
    import namegenerator
except Exception:  # optional: only used to make a random run name
    namegenerator = None
from tqdm import tqdm
from matplotlib import pyplot as plt

import torch
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import LambdaLR, CosineAnnealingLR, SequentialLR
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data.distributed import DistributedSampler

sys.path.append(os.getcwd())
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
os.environ["TOKENIZERS_PARALLELISM"] = "false"


from experiments.sevir.dataset.sevirfulldataset import (
    DynamicEncodedSequentialSevirDataset,
    dynamic_encoded_sequential_collate,
    DynamicSequentialSevirDataset,
    dynamic_sequential_collate,
    post_process_samples,
)
from common.utils.utils import EarlyStopping, compute_mean_std
from common.utils.continuation import assert_strict_continuation
from common.models.flowcast.rf_stdit import (
    FlowCastSTDiTWrapper,
    autoregressive_sample,
)
from common.models.flowcast.chunked_training import compute_chunked_rflow_loss
from common.models.flowcast.rmlf import (
    RMLFController,
    freeze_module,
    rmlf_config_from_mapping,
)
from omegaconf import OmegaConf
from common.utils.utils import warmup_lambda

from common.metrics.metrics_streaming_probabilistic import (
    MetricsAccumulator,
)
from common.utils.utils import (
    calculate_metrics,
    ema,
)
from common.losses.uot import GridUOTConfig, GridUnbalancedSinkhorn
try:
    from experiments.sevir.display.cartopy import make_animation
except Exception as _anim_exc:  # cartopy optional: only used for eval animations
    make_animation = None
    print(f"[warn] make_animation unavailable ({_anim_exc}); eval animations disabled.")


def setup_ddp():
    """Initializes the distributed environment."""
    if "RANK" in os.environ and "WORLD_SIZE" in os.environ:
        rank = int(os.environ["RANK"])
        world_size = int(os.environ["WORLD_SIZE"])
        local_rank = int(os.environ["LOCAL_RANK"])
        print(f"Initializing DDP: Rank {rank}/{world_size}, Local Rank {local_rank}")
        dist.init_process_group(
            backend="nccl", init_method="env://", rank=rank, world_size=world_size
        )
        torch.cuda.set_device(local_rank)
        dist.barrier()
        return rank, world_size, local_rank, torch.device(f"cuda:{local_rank}")
    else:
        print("Not running in distributed mode. Using single device.")
        return (
            0,
            1,
            0,
            torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        )


def cleanup_ddp():
    """Cleans up the distributed environment."""
    if dist.is_initialized():
        dist.destroy_process_group()
        print("Cleaned up DDP.")


def reduce_tensor(tensor: torch.Tensor, world_size: int) -> torch.Tensor:
    """
    Reduces a tensor's value across all DDP processes by averaging.

    Args:
        tensor (torch.Tensor): The tensor to reduce.
        world_size (int): The total number of processes.

    Returns:
        torch.Tensor: The reduced tensor with the averaged value.
    """
    rt = tensor.clone()
    dist.all_reduce(rt, op=dist.ReduceOp.SUM)
    rt /= world_size
    return rt


def raw_to_eval_scale(
    tensor: torch.Tensor, dataset_name: str, pixel_scale: float
) -> torch.Tensor:
    """Map raw dataset values to the metric scale for the current dataset.

    Raw HDF5 frames are stored on a 0-255 scale for every dataset, so the
    conversion is always pixel_scale/255 -- a no-op for SEVIR (pixel_scale
    255) and x90/255 for the dBZ datasets. This used to be keyed on the name
    "cikm", which silently left Shanghai truth on the 0-255 scale while
    decoded predictions were scaled to 0-90 dBZ. That 2.83x unit mismatch
    made the AE oracle report CSI@40 = 0.123 when the true reconstruction
    ceiling was 0.65, and would have corrupted partial_csi_m model selection
    during training. Behaviour for CIKM and SEVIR is unchanged.
    """
    del dataset_name  # the scale is fully determined by pixel_scale
    return tensor * (pixel_scale / 255.0)


def decoded_to_eval_scale(
    tensor: torch.Tensor,
    dataset_name: str,
    pixel_scale: float,
    normalized_autoencoder: bool,
) -> torch.Tensor:
    """Map decoded autoencoder outputs to the metric scale."""
    if normalized_autoencoder:
        return tensor * pixel_scale
    if dataset_name == "cikm":
        return tensor * (pixel_scale / 255.0)
    return tensor


def build_autoencoder(config, device):
    """Frozen AutoencoderKL for the decoded-pixel path of the UOT loss."""
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
    checkpoint = torch.load(
        config.autoencoder_params.autoencoder_checkpoint, map_location=device
    )
    new_state_dict = {}
    for k, v in checkpoint["model_state_dict"].items():
        new_key = k.replace("module.", "") if k.startswith("module.") else k
        new_state_dict[new_key] = v
    ae_model.load_state_dict(new_state_dict)
    ae_model = ae_model.to(device)
    ae_model.eval()
    ae_model.requires_grad_(False)
    return ae_model


def make_decode_fn(
    normalizer_module,
    ae_model,
    normalized_autoencoder,
    pixel_scale,
    dataset_name,
    batch_size_ae=None,
):
    """Differentiable map: normalized latent chunk (B, T, h, w, c) ->
    pixel fields in eval units (B, T, H, W). Gradients flow through the
    frozen decoder; runs in fp32 regardless of surrounding autocast.

    NOTE: mean/std are captured as PLAIN FLOATS here, not read from the
    module buffers inside the graph. DDP broadcasts buffers in-place at
    the start of every forward; with multiple chunk forwards per
    iteration, a buffer saved for backward by an earlier chunk's UOT
    graph would be version-bumped by the next chunk's forward and
    backward would fail with "modified by an inplace operation"."""
    mean_val = float(normalizer_module.mean)
    std_val = float(normalizer_module.std)

    def decode_fn(latent_norm):
        device_type = latent_norm.device.type
        with torch.amp.autocast(device_type=device_type, enabled=False):
            lat = latent_norm.float() * std_val + mean_val
            b, t, h, w, c = lat.shape
            lat = lat.reshape(b * t, h, w, c).permute(0, 3, 1, 2).contiguous()
            bs = batch_size_ae if batch_size_ae is not None else lat.shape[0]
            chunks = []
            for i in range(0, lat.shape[0], bs):
                chunks.append(ae_model.decode(lat[i : i + bs]).sample)
            dec = torch.cat(chunks, dim=0)
            dec = decoded_to_eval_scale(
                dec, dataset_name, pixel_scale, normalized_autoencoder
            )
            dec = torch.relu(dec[:, 0])
            return dec.reshape(b, t, dec.shape[-2], dec.shape[-1])

    return decode_fn


parser = argparse.ArgumentParser(description="Script for configuring hyperparameters.")

parser.add_argument(
    "--config",
    type=str,
    default="experiments/sevir/runner/flowcast/flowcast_config.yaml",
)
parser.add_argument(
    "--train_file",
    type=str,
    default=None,
)
parser.add_argument(
    "--train_meta",
    type=str,
    default=None,
)
parser.add_argument(
    "--val_file",
    type=str,
    default=None,
)
parser.add_argument(
    "--val_meta",
    type=str,
    default=None,
)

parser.add_argument(
    "--partial_evaluation_file",
    type=str,
    default=None,
)
parser.add_argument(
    "--partial_evaluation_meta",
    type=str,
    default=None,
)
parser.add_argument(
    "--smoke_batches",
    type=int,
    default=0,
    help=(
        "Run this many training batches through the REAL path -- parent load, "
        "DDP, evaluation EMA, frozen RMLF teacher, frozen UOT autoencoder, "
        "decode + Sinkhorn, AdamW, bridge, backward -- then report peak CUDA "
        "memory and exit.  Nothing is checkpointed and validation is skipped.  "
        "A synthetic harness cannot substitute: it misses the DDP buckets, the "
        "autoencoder parameters and the decoder activations the UOT term keeps "
        "alive, so it only ever produces a lower bound."
    ),
)


def main():
    """
    Main function to run the distributed training and validation loop.

    Orchestrates the entire process, from DDP setup and configuration loading
    to the training loop, evaluation, and final cleanup.
    """
    args = parser.parse_args()
    config = OmegaConf.load(args.config)

    rank, world_size, local_rank, device = setup_ddp()
    is_main_process = rank == 0

    DEBUG_MODE = config.run_params.debug_mode
    RUN_STRING = config.run_params.run_string
    CARTOPY_FEATURES = config.partial_evaluation_params.cartopy_features

    run_id_base = (
        datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        + "_"
        + RUN_STRING
        + "_"
        + (namegenerator.gen() if namegenerator is not None else os.urandom(3).hex())
    )
    MAIN_RUN_ID = f"{run_id_base}_main"

    DEBUG_PRINT_PREFIX = (
        f"[DEBUG Rank {rank}] " if DEBUG_MODE else f"[Rank {rank}] "
    )

    ENABLE_WANDB = (
        config.run_params.enable_wandb and is_main_process
    )
    PARTIAL_EVALUATION = config.partial_evaluation_params.partial_evaluation
    PARTIAL_EVALUATION_INTERVAL = (
        config.partial_evaluation_params.partial_evaluation_interval
    )
    PARTIAL_EVALUATION_BATCHES = (
        config.partial_evaluation_params.partial_evaluation_batches
    )
    AUTOENCODER_CHECKPOINT = config.autoencoder_params.autoencoder_checkpoint
    DATASET_NAME = OmegaConf.select(config, "data_params.dataset_name", default="sevir")
    DATA_KEY = OmegaConf.select(config, "data_params.data_key", default="vil")
    RAW_SEQ_LEN = OmegaConf.select(config, "data_params.raw_seq_len", default=49)
    STRIDE = OmegaConf.select(config, "data_params.stride", default=12)
    PIXEL_SCALE = OmegaConf.select(config, "evaluation_params.pixel_scale", default=255.0)
    THRESHOLDS = np.array(
        OmegaConf.select(
            config,
            "evaluation_params.thresholds",
            default=[16, 74, 133, 160, 181, 219],
        ),
        dtype=np.float32,
    )

    if (
        PARTIAL_EVALUATION and AUTOENCODER_CHECKPOINT is None and is_main_process
    ):
        raise ValueError(
            "Partial Evaluation is enabled but Autoencoder Checkpoint is not provided"
        )

    DEFAULT_LATENT_DIR = f"datasets/{DATASET_NAME}/data/{DATASET_NAME}_latent_vae"
    DEFAULT_RAW_DIR = f"datasets/{DATASET_NAME}/data/{DATASET_NAME}_full"
    TRAIN_FILE = args.train_file or f"{DEFAULT_LATENT_DIR}/nowcast_training_full.h5"
    TRAIN_META = args.train_meta or f"{DEFAULT_LATENT_DIR}/nowcast_training_full_META.csv"
    VAL_FILE = args.val_file or f"{DEFAULT_LATENT_DIR}/nowcast_validation_full.h5"
    VAL_META = args.val_meta or f"{DEFAULT_LATENT_DIR}/nowcast_validation_full_META.csv"
    PRELOAD_MODEL = config.run_params.preload_model
    # The parent as CONFIGURED, before any crash-resume override below.  The
    # frozen-teacher identity check must compare against this, not against the
    # arm's own latest checkpoint -- otherwise every legitimate resume would
    # look like a teacher/parent mismatch.
    CONFIGURED_PARENT = config.run_params.preload_model
    # crash resilience: a fixed-path "latest" checkpoint saved every N
    # batches takes precedence over preload_model so a supervising
    # relaunch resumes instead of restarting
    RESUME_LATEST_PATH = OmegaConf.select(
        config, "run_params.resume_latest_path", default=None
    )
    SAVE_LATEST_EVERY = int(
        OmegaConf.select(config, "training_params.save_latest_every_batches", default=0)
    )
    # Periodic EMA snapshots.  The early-stopping path writes a SINGLE file
    # that is overwritten on every improvement, so a finished run leaves
    # exactly one selectable checkpoint and its trajectory is unrecoverable.
    # That is fine only if you trust the selection metric -- and on CIKM the
    # validation split is much wetter than test, so `partial_csi_m` is a poor
    # proxy.  Snapshots let the checkpoint be chosen offline, afterwards,
    # under a frozen rule (tools/select_checkpoint.py).
    # Default 0 = off, so existing runs are bit-for-bit unaffected.
    SNAPSHOT_EVERY_EPOCHS = int(
        OmegaConf.select(config, "training_params.snapshot_every_epochs", default=0)
    )
    SNAPSHOT_DIR = OmegaConf.select(
        config, "training_params.snapshot_dir", default=None
    )
    # Carry the evaluation EMA through supervisor restarts.  Without it a
    # restart silently reinitializes the EMA from the raw weights, which makes
    # `partial_csi_m` -- and therefore early stopping -- depend on how many
    # times the job crashed.  Default false so existing runs are unaffected.
    SAVE_EMA_IN_LATEST = bool(
        OmegaConf.select(config, "training_params.save_ema_in_latest", default=False)
    )
    # Declaring a continuation budget declares intent: this run is one arm of a
    # matched comparison, not an ordinary training job.  Every "fall back and
    # keep going" path below then becomes fail-CLOSED, because each of them can
    # silently turn an arm into something else -- a scratch run, a run with a
    # reset optimizer, a run whose cosine schedule restarts at step 0 -- while
    # the log still looks like a healthy continuation.
    STRICT_CONTINUATION = (
        OmegaConf.select(
            config,
            "training_params.continuation_end_epoch_exclusive",
            default=None,
        )
        is not None
    )
    if RESUME_LATEST_PATH and os.path.exists(RESUME_LATEST_PATH):
        if is_main_process:
            print(
                f"{DEBUG_PRINT_PREFIX}Found latest checkpoint at "
                f"{RESUME_LATEST_PATH}; resuming from it (overrides preload_model)."
            )
        PRELOAD_MODEL = RESUME_LATEST_PATH

    # ---- Innovation 2: unbalanced-OT training loss configuration ----
    UOT_ENABLED = OmegaConf.select(config, "uot_params.enabled", default=False)
    uot_loss_module = None
    uot_loss_params = None
    UOT_WARMUP_STEPS = 0
    if UOT_ENABLED:
        uot_loss_module = GridUnbalancedSinkhorn(
            GridUOTConfig(
                blur=float(OmegaConf.select(config, "uot_params.blur", default=3.0)),
                reach=float(OmegaConf.select(config, "uot_params.reach", default=16.0)),
                downsample=int(OmegaConf.select(config, "uot_params.downsample", default=4)),
                n_iters=int(OmegaConf.select(config, "uot_params.n_iters", default=100)),
                self_iters=int(OmegaConf.select(config, "uot_params.self_iters", default=50)),
                debiased=True,
            )
        )
        _zero_point = OmegaConf.select(config, "uot_params.mass_zero_point", default=None)
        uot_loss_params = {
            "weight": float(OmegaConf.select(config, "uot_params.weight", default=0.01)),
            "t_power": float(OmegaConf.select(config, "uot_params.t_power", default=2.0)),
            "normalize_by_mass": bool(
                OmegaConf.select(config, "uot_params.normalize_by_mass", default=False)
            ),
            # fixed climatological value scale (M_ref); calibrate so the
            # logged uot_term/training_loss ratio lands around 5-20%
            "value_scale_ref": float(
                OmegaConf.select(config, "uot_params.value_scale_ref", default=1.0)
            ),
            "dry_frame_mass": float(
                OmegaConf.select(config, "uot_params.dry_frame_mass", default=1e-3)
            ),
            "mass_kwargs": {
                "transform": str(OmegaConf.select(config, "uot_params.mass_transform", default="vil")),
                "low_threshold": float(OmegaConf.select(config, "uot_params.mass_low_threshold", default=0.0)),
                "gamma": float(OmegaConf.select(config, "uot_params.mass_gamma", default=1.0)),
                "mass_scale": float(OmegaConf.select(config, "uot_params.mass_scale", default=1.0)),
                "threshold_mode": str(OmegaConf.select(config, "uot_params.threshold_mode", default="soft")),
                "threshold_softness": float(OmegaConf.select(config, "uot_params.threshold_softness", default=4.0)),
                "zero_point": None if _zero_point is None else float(_zero_point),
            },
        }
        # linear warmup of the UOT weight over the first steps (audit rec):
        # let the flow objective shape the field first, then phase in the
        # transport geometry. In global_step units (+= BATCH_SIZE per batch).
        UOT_WARMUP_STEPS = int(
            OmegaConf.select(config, "uot_params.warmup_steps", default=0)
        )
        if is_main_process:
            print(
                f"{DEBUG_PRINT_PREFIX}UOT LOSS ENABLED: weight={uot_loss_params['weight']} "
                f"transform={uot_loss_params['mass_kwargs']['transform']} "
                f"(blur={uot_loss_module.config.blur}, reach={uot_loss_module.config.reach}, "
                f"ds={uot_loss_module.config.downsample})"
            )

    # ---- Rollout-Matched Lead--Flow Coupling (training only) ----
    # RMLF changes what the LATER autoregressive chunks are conditioned on
    # during training.  It adds nothing to inference: autoregressive_sample and
    # sample_chunk_euler are untouched, and validation loss below stays
    # teacher-forced (no rmlf_controller is passed there).
    _rmlf_node = OmegaConf.select(config, "rmlf_params", default=None)
    _rmlf_mapping = (
        None
        if _rmlf_node is None
        else OmegaConf.to_container(_rmlf_node, resolve=True)
    )
    rmlf_config = rmlf_config_from_mapping(_rmlf_mapping)
    rmlf_config.validate_for_training()
    rmlf_controller = RMLFController(rmlf_config) if rmlf_config.enabled else None
    if is_main_process and rmlf_config.enabled:
        print(
            f"{DEBUG_PRINT_PREFIX}RMLF ENABLED: "
            f"condition={rmlf_config.condition_mode}, "
            f"coupling={rmlf_config.coupling_mode}"
            + (
                f"[{rmlf_config.amplification_key}]"
                if rmlf_config.coupling_mode == "amplification_table"
                else ""
            )
            + f", teacher={rmlf_config.teacher_mode}, "
            f"rollout_p={rmlf_config.rollout_probability}, "
            f"a=[{rmlf_config.corruption_min}, {rmlf_config.corruption_max}], "
            f"bridge_steps={rmlf_config.bridge_euler_steps}"
        )

    BATCH_SIZE = config.training_params.micro_batch_size
    LEARNING_RATE = config.optimizer_params.learning_rate
    NUM_EPOCHS = config.training_params.num_epochs
    NUM_WORKERS = config.training_params.num_workers
    EARLY_STOPPING_PATIENCE = config.training_params.early_stopping_patience
    EARLY_STOPPING_METRIC = config.training_params.early_stopping_metric
    INPUT_LENGTH = OmegaConf.select(
        config, "data_params.input_length", default=config.data_params.lag_time
    )
    OUTPUT_LENGTH = OmegaConf.select(
        config, "data_params.output_length", default=config.data_params.lead_time
    )
    LAG_TIME = config.data_params.lag_time
    LEAD_TIME = config.data_params.lead_time
    TIME_SPACING = config.data_params.time_spacing
    GRAD_CLIP = config.training_params.gradient_clip_val

    if (
        EARLY_STOPPING_METRIC in ["partial_csi_m", "partial_mse"]
        and not PARTIAL_EVALUATION
        and is_main_process
    ):
        raise ValueError(
            f"Early stopping metric {EARLY_STOPPING_METRIC} requires partial evaluation to be enabled"
        )

    OPTIMIZER_TYPE = config.optimizer_params.optimizer_type
    WEIGHT_DECAY = config.optimizer_params.weight_decay

    SCHEDULER_TYPE = config.scheduler_params.scheduler_type
    LR_PLATEAU_FACTOR = config.scheduler_params.lr_plateau_factor
    LR_PLATEAU_PATIENCE = config.scheduler_params.lr_plateau_patience
    LR_COSINE_WARMUP_ITER_PERCENTAGE = (
        config.scheduler_params.lr_cosine_warmup_iter_percentage
    )
    LR_COSINE_MIN_WARMUP_LR_RATIO = (
        config.scheduler_params.lr_cosine_min_warmup_lr_ratio
    )
    LR_COSINE_MIN_LR_RATIO = config.scheduler_params.lr_cosine_min_lr_ratio

    NORMALIZED_AUTOENCODER = config.autoencoder_params.normalized_autoencoder

    USE_FP16 = config.training_params.fp16

    EMA_MODEL_SAVING = config.ema_model_saving_params.ema_model_saving
    EMA_MODEL_SAVING_DECAY = config.ema_model_saving_params.ema_model_saving_decay

    GRAD_ACCUMULATION_STEPS = (
        config.training_params.grad_accumulation_steps
    )
    NUM_TRAIN_TIMESTEPS = config.rflow_params.num_train_timesteps
    EULER_STEPS = config.sampling_params.euler_steps
    if (
        rmlf_config.enabled
        and rmlf_config.bridge_euler_steps != EULER_STEPS
        and not rmlf_config.allow_reduced_bridge_fidelity
    ):
        # A bridge solved on a coarser grid than deployment injects solver
        # error that has nothing to do with rollout conditioning, and it makes
        # R1 strictly harder than the condition the model actually meets at
        # test time.  Reducing bridge fidelity is a legitimate efficiency
        # ablation, but it must be a deliberate, separately reported one.
        raise ValueError(
            "rmlf_params.bridge_euler_steps "
            f"({rmlf_config.bridge_euler_steps}) must equal "
            f"sampling_params.euler_steps ({EULER_STEPS}) so the rollout "
            "bridge uses the deployment solver.  Set them equal, or set "
            "rmlf_params.allow_reduced_bridge_fidelity=true to run the "
            "reduced-fidelity bridge as an explicitly labelled ablation."
        )
    STDIT_HIDDEN_SIZE = config.stdit.hidden_size
    STDIT_DEPTH = config.stdit.depth
    STDIT_NUM_HEADS = config.stdit.num_heads
    STDIT_PATCH_SIZE = tuple(config.stdit.patch_size)
    STDIT_MLP_RATIO = OmegaConf.select(config, "stdit.mlp_ratio", default=4.0)
    STDIT_DROP_PATH = OmegaConf.select(config, "stdit.drop_path", default=0.0)
    STDIT_QK_NORM = OmegaConf.select(config, "stdit.qk_norm", default=True)

    if OUTPUT_LENGTH % INPUT_LENGTH != 0:
        raise ValueError("output_length must be divisible by input_length.")
    if RAW_SEQ_LEN < (INPUT_LENGTH + OUTPUT_LENGTH) * TIME_SPACING:
        raise ValueError("raw_seq_len is too small for input_length/output_length.")
    if LAG_TIME != INPUT_LENGTH:
        raise ValueError("data_params.lag_time must match data_params.input_length.")
    if LEAD_TIME != OUTPUT_LENGTH:
        raise ValueError("data_params.lead_time must match data_params.output_length.")
    if STDIT_DEPTH % 2 != 0:
        raise ValueError("stdit.depth must be even.")

    if is_main_process:
        print(f"--- Distributed Training Config ---")
        print(f"World Size: {world_size}")
        print(f"Batch Size PER GPU: {BATCH_SIZE}")
        print(f"Global Batch Size (before accumulation): {BATCH_SIZE * world_size}")
        print(f"Gradient Accumulation Steps: {GRAD_ACCUMULATION_STEPS}")
        print(
            f"Effective Global Batch Size: {BATCH_SIZE * world_size * GRAD_ACCUMULATION_STEPS}"
        )
        print(f"FP16 Enabled: {USE_FP16}")
        print(f"-----------------------------------")
        print(f"{DEBUG_PRINT_PREFIX}Run ID (Main): {MAIN_RUN_ID}")
        print(f"{DEBUG_PRINT_PREFIX}Run String: {RUN_STRING}")
        print(f"{DEBUG_PRINT_PREFIX}Training File: {TRAIN_FILE}")
        print(f"{DEBUG_PRINT_PREFIX}Training Meta: {TRAIN_META}")
        print(f"{DEBUG_PRINT_PREFIX}Validation File: {VAL_FILE}")
        print(f"{DEBUG_PRINT_PREFIX}Validation Meta: {VAL_META}")
        print(f"{DEBUG_PRINT_PREFIX}Debug Mode: {DEBUG_MODE}")
        print(f"{DEBUG_PRINT_PREFIX}Normalized Autoencoder: {NORMALIZED_AUTOENCODER}")
        print(
            f"{DEBUG_PRINT_PREFIX}Enable Wandb: {config.run_params.enable_wandb}"
        )
        print(f"{DEBUG_PRINT_PREFIX}Partial Evaluation: {PARTIAL_EVALUATION}")
        print(
            f"{DEBUG_PRINT_PREFIX}Partial Evaluation Interval: {PARTIAL_EVALUATION_INTERVAL}"
        )
        print(
            f"{DEBUG_PRINT_PREFIX}Partial Evaluation Batches: {PARTIAL_EVALUATION_BATCHES}"
        )
        print(f"{DEBUG_PRINT_PREFIX}Autoencoder Checkpoint: {AUTOENCODER_CHECKPOINT}")
        print(f"{DEBUG_PRINT_PREFIX}Training File: {TRAIN_FILE}")
        print(f"{DEBUG_PRINT_PREFIX}Training Meta: {TRAIN_META}")
        print(f"{DEBUG_PRINT_PREFIX}Preload Model: {PRELOAD_MODEL}")
        print(f"{DEBUG_PRINT_PREFIX}Learning Rate: {LEARNING_RATE}")
        print(f"{DEBUG_PRINT_PREFIX}Number of Epochs: {NUM_EPOCHS}")
        print(f"{DEBUG_PRINT_PREFIX}Number of Workers: {NUM_WORKERS}")
        print(f"{DEBUG_PRINT_PREFIX}Early Stopping Patience: {EARLY_STOPPING_PATIENCE}")
        print(f"{DEBUG_PRINT_PREFIX}Early Stopping Metric: {EARLY_STOPPING_METRIC}")
        print(f"{DEBUG_PRINT_PREFIX}Input Length: {INPUT_LENGTH}")
        print(f"{DEBUG_PRINT_PREFIX}Output Length: {OUTPUT_LENGTH}")
        print(f"{DEBUG_PRINT_PREFIX}Time Spacing: {TIME_SPACING}")
        print(f"{DEBUG_PRINT_PREFIX}Raw Seq Len: {RAW_SEQ_LEN}")
        print(f"{DEBUG_PRINT_PREFIX}Stride: {STRIDE}")
        print(f"{DEBUG_PRINT_PREFIX}Data Key: {DATA_KEY}")
        print(f"{DEBUG_PRINT_PREFIX}Dataset Name: {DATASET_NAME}")
        print(f"{DEBUG_PRINT_PREFIX}Pixel Scale: {PIXEL_SCALE}")
        print(f"{DEBUG_PRINT_PREFIX}Thresholds: {THRESHOLDS}")
        print(f"{DEBUG_PRINT_PREFIX}Gradient Clip Value: {GRAD_CLIP}")
        print(f"{DEBUG_PRINT_PREFIX}RF Timesteps: {NUM_TRAIN_TIMESTEPS}")
        print(f"{DEBUG_PRINT_PREFIX}Euler Steps: {EULER_STEPS}")
        print(f"{DEBUG_PRINT_PREFIX}Save EMA in latest: {SAVE_EMA_IN_LATEST}")

        print(f"--------- {DEBUG_PRINT_PREFIX}STDiT Config ---------")
        print(f"{DEBUG_PRINT_PREFIX}Hidden Size: {STDIT_HIDDEN_SIZE}")
        print(f"{DEBUG_PRINT_PREFIX}Depth: {STDIT_DEPTH}")
        print(f"{DEBUG_PRINT_PREFIX}Num Heads: {STDIT_NUM_HEADS}")
        print(f"{DEBUG_PRINT_PREFIX}Patch Size: {STDIT_PATCH_SIZE}")
        print(f"{DEBUG_PRINT_PREFIX}MLP Ratio: {STDIT_MLP_RATIO}")
        print(f"{DEBUG_PRINT_PREFIX}Drop Path: {STDIT_DROP_PATH}")
        print(f"{DEBUG_PRINT_PREFIX}QK Norm: {STDIT_QK_NORM}")

        print(f"--------- {DEBUG_PRINT_PREFIX}Optimizer Config ---------")
        print(f"{DEBUG_PRINT_PREFIX}Optimizer Type: {OPTIMIZER_TYPE}")
        print(f"{DEBUG_PRINT_PREFIX}Weight Decay: {WEIGHT_DECAY}")
        print(f"{DEBUG_PRINT_PREFIX}Scheduler Type: {SCHEDULER_TYPE}")
        print(f"{DEBUG_PRINT_PREFIX}LR Plateau Factor: {LR_PLATEAU_FACTOR}")
        print(f"{DEBUG_PRINT_PREFIX}LR Plateau Patience: {LR_PLATEAU_PATIENCE}")
        print(
            f"{DEBUG_PRINT_PREFIX}LR Cosine Warmup Iter Percentage: {LR_COSINE_WARMUP_ITER_PERCENTAGE}"
        )
        print(
            f"{DEBUG_PRINT_PREFIX}LR Cosine Min Warmup LR Ratio: {LR_COSINE_MIN_WARMUP_LR_RATIO}"
        )
        print(f"{DEBUG_PRINT_PREFIX}LR Cosine Min LR Ratio: {LR_COSINE_MIN_LR_RATIO}")

        print(f"--------- {DEBUG_PRINT_PREFIX}EMA Model Saving Config ---------")
        print(f"{DEBUG_PRINT_PREFIX}EMA Model Saving: {EMA_MODEL_SAVING}")
        if EMA_MODEL_SAVING:
            print(
                f"{DEBUG_PRINT_PREFIX}EMA Model Saving Decay: {EMA_MODEL_SAVING_DECAY}"
            )
        print(f"------------------------------------------------------------")

    project_name = f"{DATASET_NAME}-nowcasting-rf-stdit"
    if ENABLE_WANDB:
        config_dict = {
            "learning_rate": LEARNING_RATE,
            "batch_size_per_gpu": BATCH_SIZE,
            "world_size": world_size,
            "grad_accumulation_steps": GRAD_ACCUMULATION_STEPS,
            "effective_batch_size": BATCH_SIZE * world_size * GRAD_ACCUMULATION_STEPS,
            "num_epochs": NUM_EPOCHS,
            "num_workers": NUM_WORKERS,
            "early_stopping_patience": EARLY_STOPPING_PATIENCE,
            "input_length": INPUT_LENGTH,
            "output_length": OUTPUT_LENGTH,
            "time_spacing": TIME_SPACING,
            "grad_clip": GRAD_CLIP,
            "num_train_timesteps": NUM_TRAIN_TIMESTEPS,
            "euler_steps": EULER_STEPS,
            "rmlf_enabled": rmlf_config.enabled,
            "rmlf_condition_mode": rmlf_config.condition_mode,
            "rmlf_coupling_mode": rmlf_config.coupling_mode,
            "rmlf_amplification_key": rmlf_config.amplification_key,
            "rmlf_teacher_mode": rmlf_config.teacher_mode,
            "rmlf_teacher_checkpoint": rmlf_config.teacher_checkpoint,
            "rmlf_rollout_probability": rmlf_config.rollout_probability,
            "rmlf_bridge_euler_steps": rmlf_config.bridge_euler_steps,
            "rmlf_corruption_min": rmlf_config.corruption_min,
            "rmlf_corruption_max": rmlf_config.corruption_max,
            "rmlf_warmup_steps": rmlf_config.warmup_steps,
            "save_ema_in_latest": SAVE_EMA_IN_LATEST,
            "dataset": DATASET_NAME,
            "model": "Flowcast-RF-STDiT",
            "raw_seq_len": RAW_SEQ_LEN,
            "stride": STRIDE,
            "data_key": DATA_KEY,
            "pixel_scale": PIXEL_SCALE,
            "thresholds": THRESHOLDS.tolist(),
            "optimizer_type": OPTIMIZER_TYPE,
            "weight_decay": WEIGHT_DECAY,
            "scheduler_type": SCHEDULER_TYPE,
            "lr_plateau_factor": LR_PLATEAU_FACTOR,
            "lr_plateau_patience": LR_PLATEAU_PATIENCE,
            "lr_cosine_warmup_iter_percentage": LR_COSINE_WARMUP_ITER_PERCENTAGE,
            "lr_cosine_min_warmup_lr_ratio": LR_COSINE_MIN_WARMUP_LR_RATIO,
            "lr_cosine_min_lr_ratio": LR_COSINE_MIN_LR_RATIO,
            "stdit_hidden_size": STDIT_HIDDEN_SIZE,
            "stdit_depth": STDIT_DEPTH,
            "stdit_num_heads": STDIT_NUM_HEADS,
            "stdit_patch_size": list(STDIT_PATCH_SIZE),
            "stdit_mlp_ratio": STDIT_MLP_RATIO,
            "stdit_drop_path": STDIT_DROP_PATH,
            "stdit_qk_norm": STDIT_QK_NORM,
            "fp16": USE_FP16,
            "ema_model_saving": EMA_MODEL_SAVING,
            "ema_model_saving_decay": EMA_MODEL_SAVING_DECAY,
        }
        wandb.init(
            project=project_name,
            name=MAIN_RUN_ID,
            config=config_dict,
        )

    ARTIFACTS_FOLDER = f"artifacts/{DATASET_NAME}/flowcast/{MAIN_RUN_ID}"
    PLOTS_FOLDER = f"{ARTIFACTS_FOLDER}/plots"
    ANIMATIONS_FOLDER = f"{PLOTS_FOLDER}/animations"
    METRICS_FOLDER = f"{PLOTS_FOLDER}/metrics"
    MODEL_SAVE_DIR = f"{ARTIFACTS_FOLDER}/models"
    MODEL_SAVE_PATH = os.path.join(MODEL_SAVE_DIR, "early_stopping_model" + ".pt")
    SNAPSHOT_FOLDER = SNAPSHOT_DIR or f"{MODEL_SAVE_DIR}/snapshots"

    if is_main_process:
        os.makedirs(PLOTS_FOLDER, exist_ok=True)
        os.makedirs(ANIMATIONS_FOLDER, exist_ok=True)
        os.makedirs(METRICS_FOLDER, exist_ok=True)
        os.makedirs(MODEL_SAVE_DIR, exist_ok=True)
        if SNAPSHOT_EVERY_EPOCHS > 0:
            os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)

    if world_size > 1:
        dist.barrier()

    print(f"{DEBUG_PRINT_PREFIX}Using device: {device}")
    if device.type == "cpu" and is_main_process:
        print(DEBUG_PRINT_PREFIX + "Warning: CPU is used for computation!")

    seed = 42
    random.seed(seed)
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    train_dataset = DynamicEncodedSequentialSevirDataset(
        meta_csv=TRAIN_META,
        data_file=TRAIN_FILE,
        data_type=DATA_KEY,
        raw_seq_len=RAW_SEQ_LEN,
        lag_time=INPUT_LENGTH,
        lead_time=OUTPUT_LENGTH,
        time_spacing=TIME_SPACING,
        stride=STRIDE,
        channel_last=True,
        debug_mode=DEBUG_MODE,
        transform=None,
    )
    val_dataset = DynamicEncodedSequentialSevirDataset(
        meta_csv=VAL_META,
        data_file=VAL_FILE,
        data_type=DATA_KEY,
        raw_seq_len=RAW_SEQ_LEN,
        lag_time=INPUT_LENGTH,
        lead_time=OUTPUT_LENGTH,
        time_spacing=TIME_SPACING,
        stride=STRIDE,
        channel_last=True,
        debug_mode=DEBUG_MODE,
        transform=None,
    )

    train_sampler = DistributedSampler(
        train_dataset, num_replicas=world_size, rank=rank, shuffle=True, seed=seed
    )
    val_sampler = DistributedSampler(
        val_dataset, num_replicas=world_size, rank=rank, shuffle=False
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=dynamic_encoded_sequential_collate,
        num_workers=NUM_WORKERS if not DEBUG_MODE else 0,
        pin_memory=True if not DEBUG_MODE else False,
        sampler=train_sampler,
        drop_last=True,
        persistent_workers=True if not DEBUG_MODE else False,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=dynamic_encoded_sequential_collate,
        num_workers=NUM_WORKERS if not DEBUG_MODE else 0,
        pin_memory=True if not DEBUG_MODE else False,
        sampler=val_sampler,
        drop_last=False,
        persistent_workers=True if not DEBUG_MODE else False,
    )

    input_shape = None
    output_shape = None
    if is_main_process:
        temp_loader = (
            DataLoader(
                train_dataset,
                batch_size=BATCH_SIZE,
                shuffle=True,
                collate_fn=dynamic_encoded_sequential_collate,
                num_workers=0,
            )
        )
        for batch in temp_loader:
            inputs_cpu, outputs_cpu, _ = batch
            print(f"Inputs shape (from rank 0): {inputs_cpu.shape}")
            print(f"Outputs shape (from rank 0): {outputs_cpu.shape}")
            input_shape = inputs_cpu.shape
            output_shape = outputs_cpu.shape
            break
        del temp_loader

    shapes_list = [input_shape, output_shape]
    if world_size > 1:
        dist.broadcast_object_list(shapes_list, src=0)
    input_shape, output_shape = shapes_list[0], shapes_list[1]

    if input_shape is None or output_shape is None:
        raise RuntimeError("Could not determine input/output shapes.")

    preload_model_state_dict = None
    preload_global_step = None
    preload_best_val_loss = None
    preload_std = None
    preload_mean = None
    preload_optimizer_state_dict = None
    preload_scheduler_state_dict = None
    preload_ema_model_state_dict = None
    preload_rmlf_state_dict = None
    preload_continuation_end = None
    preload_epoch = None
    mean = None
    std = None

    if PRELOAD_MODEL is not None:
        if is_main_process:
            print(f"{DEBUG_PRINT_PREFIX}Attempting to load checkpoint: {PRELOAD_MODEL}")
            try:
                model_info = torch.load(PRELOAD_MODEL, map_location="cpu")
                preload_model_state_dict = model_info["model_state_dict"]
                # None, not 0: a defaulted 0 is indistinguishable from a
                # genuine 0 and would slip past the strict-continuation check
                # below.  The non-strict path coerces None -> 0 later, so
                # ordinary runs are unaffected.
                preload_global_step = model_info.get("global_step", None)
                preload_best_val_loss = model_info.get("best_metric", None)
                preload_std = model_info.get("std", None)
                preload_mean = model_info.get("mean", None)
                preload_optimizer_state_dict = model_info.get(
                    "optimizer_state_dict", None
                )
                preload_scheduler_state_dict = model_info.get(
                    "scheduler_state_dict", None
                )
                preload_ema_model_state_dict = model_info.get(
                    "ema_model_state_dict", None
                )
                preload_rmlf_state_dict = model_info.get("rmlf_state_dict", None)
                preload_continuation_end = model_info.get(
                    "continuation_end_epoch_exclusive", None
                )
                preload_epoch = model_info.get("epoch", None)
                print(
                    f"{DEBUG_PRINT_PREFIX}Successfully loaded model info from checkpoint"
                )
            except FileNotFoundError:
                if STRICT_CONTINUATION:
                    raise
                print(
                    f"{DEBUG_PRINT_PREFIX}Preload model file not found: {PRELOAD_MODEL}. Starting from scratch."
                )
            except Exception as e:
                if STRICT_CONTINUATION:
                    raise
                print(
                    f"{DEBUG_PRINT_PREFIX}Error loading checkpoint: {e}. Starting from scratch."
                )
        loaded_info = [
            preload_model_state_dict,
            preload_global_step,
            preload_best_val_loss,
            preload_std,
            preload_mean,
            preload_optimizer_state_dict,
            preload_scheduler_state_dict,
            preload_ema_model_state_dict,
            preload_rmlf_state_dict,
            preload_continuation_end,
            preload_epoch,
        ]
        if world_size > 1:
            dist.broadcast_object_list(loaded_info, src=0)
        (
            preload_model_state_dict,
            preload_global_step,
            preload_best_val_loss,
            preload_std,
            preload_mean,
            preload_optimizer_state_dict,
            preload_scheduler_state_dict,
            preload_ema_model_state_dict,
            preload_rmlf_state_dict,
            preload_continuation_end,
            preload_epoch,
        ) = loaded_info
    else:
        if is_main_process:
            print(f"{DEBUG_PRINT_PREFIX}No preload model specified.")

    if STRICT_CONTINUATION:
        # Not just "loading did not raise" -- the fields have to exist.  A
        # weights-only checkpoint loads cleanly and then silently restarts the
        # optimizer, the LR schedule and the epoch counter.
        assert_strict_continuation(
            {
                "preload_model path": CONFIGURED_PARENT,
                "model_state_dict": preload_model_state_dict,
                "optimizer_state_dict": preload_optimizer_state_dict,
                "scheduler_state_dict": preload_scheduler_state_dict,
                "epoch": preload_epoch,
                "global_step": preload_global_step,
                "mean": preload_mean,
                "std": preload_std,
            },
            PRELOAD_MODEL,
        )
        if is_main_process:
            print(
                f"{DEBUG_PRINT_PREFIX}STRICT CONTINUATION: parent="
                f"{PRELOAD_MODEL} epoch={preload_epoch} "
                f"global_step={preload_global_step}"
            )

    if rmlf_controller is not None and preload_rmlf_state_dict is not None:
        rmlf_controller.load_state_dict(preload_rmlf_state_dict)
        if is_main_process:
            print(f"{DEBUG_PRINT_PREFIX}Restored RMLF RNG state.")

    if preload_mean is None or preload_std is None:
        if is_main_process:
            print(f"{DEBUG_PRINT_PREFIX}Computing mean and std...")
            temp_loader = DataLoader(
                train_dataset,
                batch_size=BATCH_SIZE * 4,
                shuffle=False,
                collate_fn=dynamic_encoded_sequential_collate,
                num_workers=NUM_WORKERS // 2 if NUM_WORKERS > 1 else 0,
                pin_memory=False,
            )
            mean, std = compute_mean_std(temp_loader, channel_last=True)
            del temp_loader
            print(f"{DEBUG_PRINT_PREFIX}Computed Mean: {mean}")
            print(f"{DEBUG_PRINT_PREFIX}Computed Std: {std}")
        mean_std_list = [mean, std]
        if world_size > 1:
            dist.broadcast_object_list(mean_std_list, src=0)
        mean, std = mean_std_list[0], mean_std_list[1]
        if mean is None or std is None:
            raise RuntimeError("Mean/Std computation/broadcast failed.")
    else:
        mean = preload_mean
        std = preload_std

    model = FlowCastSTDiTWrapper(
        latent_channels=input_shape[4],
        hidden_size=STDIT_HIDDEN_SIZE,
        depth=STDIT_DEPTH,
        num_heads=STDIT_NUM_HEADS,
        patch_size=STDIT_PATCH_SIZE,
        mlp_ratio=STDIT_MLP_RATIO,
        drop_path=STDIT_DROP_PATH,
        qk_norm=STDIT_QK_NORM,
        mean=mean,
        std=std,
    )

    if preload_model_state_dict is not None:
        try:
            model.load_state_dict(
                preload_model_state_dict, strict=STRICT_CONTINUATION
            )
            if is_main_process:
                print(
                    f"{DEBUG_PRINT_PREFIX}Successfully loaded pre-trained model state dict."
                )
        except Exception as e:
            if STRICT_CONTINUATION:
                raise RuntimeError(
                    "Strict continuation: could not load the parent model "
                    f"state dict: {e}"
                ) from e
            if is_main_process:
                print(
                    f"{DEBUG_PRINT_PREFIX}Error loading pre-trained model state dict: {e}. Model weights might be random."
                )

    model = model.to(device)
    if world_size > 1:
        model = DDP(
            model,
            device_ids=[local_rank],
            output_device=local_rank,
            find_unused_parameters=True,
        )
        if is_main_process:
            print(f"{DEBUG_PRINT_PREFIX}Wrapped model with DDP.")

    eval_ema_model = None
    if EMA_MODEL_SAVING:
        eval_ema_model = copy.deepcopy(
            model.module if world_size > 1 else model
        )
        eval_ema_model = eval_ema_model.to(device)
        if preload_ema_model_state_dict is not None:
            eval_ema_model.load_state_dict(
                preload_ema_model_state_dict, strict=True
            )
            if is_main_process:
                print(f"{DEBUG_PRINT_PREFIX}Restored evaluation EMA state.")
        if is_main_process:
            print(f"{DEBUG_PRINT_PREFIX}Created EMA model.")

    # ---- RMLF rollout teacher ----
    # This is a DIFFERENT object from `eval_ema_model`.  The evaluation EMA
    # tracks the student and exists to pick checkpoints; the rollout teacher
    # defines the condition-error distribution the student is trained against
    # and must not move, or each arm sees a different corruption process and
    # the R1/R2/R3 comparison is confounded.  `ema()` is never called on it.
    rmlf_teacher = None
    if rmlf_config.enabled:
        if rmlf_config.teacher_mode == "frozen":
            teacher_path = str(rmlf_config.teacher_checkpoint)
            # The student must START from the same parameters whose rollout
            # errors the bridge injects.  If the two differ, the arm is
            # trained to be robust to some OTHER model's mistakes, and
            # "match the deployed model's rollout error" is no longer what
            # is being tested.  Set rmlf_params.allow_teacher_parent_mismatch
            # only for a deliberate cross-model ablation.
            if not rmlf_config.allow_teacher_parent_mismatch:
                if CONFIGURED_PARENT is None:
                    raise ValueError(
                        "RMLF frozen teacher requires run_params.preload_model "
                        "to be set to the same parent checkpoint."
                    )
                if os.path.abspath(teacher_path) != os.path.abspath(
                    str(CONFIGURED_PARENT)
                ):
                    raise ValueError(
                        "RMLF teacher_checkpoint and run_params.preload_model "
                        "must be the same file for the matched-continuation "
                        f"probe.\n  teacher: {os.path.abspath(teacher_path)}"
                        f"\n  parent : {os.path.abspath(str(CONFIGURED_PARENT))}"
                    )
            teacher_state = None
            teacher_sha256 = None
            if is_main_process:
                blob = torch.load(teacher_path, map_location="cpu")
                key = (
                    "ema_model_state_dict"
                    if rmlf_config.teacher_checkpoint_type == "ema"
                    else "model_state_dict"
                )
                if key not in blob:
                    raise KeyError(
                        f"RMLF teacher checkpoint {teacher_path} has no {key!r}; "
                        f"available keys: {sorted(blob)}"
                    )
                teacher_state = {
                    (name[7:] if name.startswith("module.") else name): tensor
                    for name, tensor in blob[key].items()
                }
                digest = hashlib.sha256()
                with open(teacher_path, "rb") as handle:
                    for block in iter(lambda: handle.read(1 << 20), b""):
                        digest.update(block)
                teacher_sha256 = digest.hexdigest()
                teacher_global_step = blob.get("global_step")
                print(
                    f"{DEBUG_PRINT_PREFIX}RMLF frozen teacher: {teacher_path}\n"
                    f"{DEBUG_PRINT_PREFIX}  type={rmlf_config.teacher_checkpoint_type} "
                    f"sha256={teacher_sha256} "
                    f"epoch={blob.get('epoch')} global_step={teacher_global_step}"
                )
                if rmlf_config.warmup_steps > 0 and teacher_global_step is None:
                    raise RuntimeError(
                        f"RMLF parent {teacher_path} has no global_step, so "
                        "the continuation-local rollout warmup has no anchor. "
                        "Use a parent that records it, or set "
                        "rmlf_params.warmup_steps: 0 to start at full rollout "
                        "probability deliberately."
                    )
                if (
                    teacher_global_step is not None
                    and rmlf_config.warmup_steps > 0
                    and int(rmlf_config.warmup_start_global_step)
                    != int(teacher_global_step)
                    # teacher_checkpoint IS the parent (asserted above), so its
                    # global_step is the correct ramp origin regardless of
                    # whether this process is a fresh start or a resume.
                ):
                    raise ValueError(
                        "rmlf_params.warmup_start_global_step "
                        f"({rmlf_config.warmup_start_global_step}) must equal the "
                        f"parent's global_step ({int(teacher_global_step)}), or "
                        "the ramp is measured from the wrong origin and is "
                        "already saturated on the first continuation batch."
                    )
                del blob
            teacher_payload = [teacher_state, teacher_sha256]
            if world_size > 1:
                dist.broadcast_object_list(teacher_payload, src=0)
            teacher_state, teacher_sha256 = teacher_payload
            if teacher_state is None:
                raise RuntimeError("RMLF teacher state broadcast failed.")
            if rmlf_controller is not None:
                rmlf_controller.verify_table_provenance(
                    teacher_sha256,
                    num_train_timesteps=NUM_TRAIN_TIMESTEPS,
                    precision_mode=(
                        "fp16_autocast" if USE_FP16 else "fp32"
                    ),
                )
            rmlf_teacher = copy.deepcopy(model.module if world_size > 1 else model)
            rmlf_teacher.load_state_dict(teacher_state, strict=True)
            rmlf_teacher = freeze_module(rmlf_teacher.to(device))
            del teacher_state, teacher_payload
        else:
            # Ablation only: the co-evolving student EMA.  It answers
            # "adapt to a moving early model", not "match the deployed
            # model's rollout error".
            if eval_ema_model is None:
                raise ValueError(
                    "rmlf_params.teacher_mode='ema' requires "
                    "ema_model_saving_params.ema_model_saving=true."
                )
            rmlf_teacher = eval_ema_model
            if is_main_process:
                print(
                    f"{DEBUG_PRINT_PREFIX}WARNING: RMLF teacher_mode='ema' -- the "
                    "rollout teacher drifts with the student and is shared with "
                    "the evaluation EMA."
                )

    num_batches_per_epoch = len(train_loader)
    total_num_steps = int(NUM_EPOCHS * num_batches_per_epoch)
    if is_main_process:
        print(f"{DEBUG_PRINT_PREFIX}Batches per epoch per GPU: {num_batches_per_epoch}")
        print(f"{DEBUG_PRINT_PREFIX}Total training steps: {total_num_steps}")

    if OPTIMIZER_TYPE == "adam":
        optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    elif OPTIMIZER_TYPE == "adamw":
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
        )
    else:
        if is_main_process:
            raise ValueError(f"Invalid optimizer type: {OPTIMIZER_TYPE}")
        else:
            dist.barrier()
            cleanup_ddp()
            sys.exit(1)

    if preload_optimizer_state_dict is not None:
        try:
            optimizer.load_state_dict(preload_optimizer_state_dict)
            for state in optimizer.state.values():
                for k, v in state.items():
                    if isinstance(v, torch.Tensor):
                        state[k] = v.to(device)
            if is_main_process:
                print(
                    f"{DEBUG_PRINT_PREFIX}Successfully loaded pre-trained optimizer state dict."
                )
        except Exception as e:
            if STRICT_CONTINUATION:
                raise RuntimeError(
                    "Strict continuation: could not load the parent optimizer "
                    f"state dict: {e}"
                ) from e
            if is_main_process:
                print(
                    f"{DEBUG_PRINT_PREFIX}Error loading pre-trained optimizer state dict: {e}. Optimizer state reset."
                )

    warmup_iter = int(np.round(LR_COSINE_WARMUP_ITER_PERCENTAGE * total_num_steps))

    if SCHEDULER_TYPE == "plateau":
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer,
            mode="min",
            factor=LR_PLATEAU_FACTOR,
            patience=LR_PLATEAU_PATIENCE,
        )
    elif SCHEDULER_TYPE == "cosine":
        warmup_scheduler = LambdaLR(
            optimizer,
            lr_lambda=warmup_lambda(
                warmup_steps=warmup_iter, min_lr_ratio=LR_COSINE_MIN_WARMUP_LR_RATIO
            ),
        )
        cosine_scheduler = CosineAnnealingLR(
            optimizer,
            T_max=(total_num_steps - warmup_iter),
            eta_min=LR_COSINE_MIN_LR_RATIO * LEARNING_RATE,
        )
        scheduler = SequentialLR(
            optimizer,
            schedulers=[warmup_scheduler, cosine_scheduler],
            milestones=[warmup_iter],
        )
    else:
        if is_main_process:
            raise ValueError(f"Invalid scheduler type: {SCHEDULER_TYPE}")
        else:
            dist.barrier()
            cleanup_ddp()
            sys.exit(1)

    # restore the LR schedule position on resume: without this, a crash
    # relaunch would restart warmup+cosine from step 0 while the weights
    # continue, silently splicing two different LR trajectories together
    if preload_scheduler_state_dict is not None:
        try:
            scheduler.load_state_dict(preload_scheduler_state_dict)
            # Scheduler constructors (especially LambdaLR + SequentialLR)
            # mutate optimizer.param_groups[*]["lr"].  Loading the scheduler
            # state restores its counters and cached _last_lr, but PyTorch does
            # not copy that cached value back into the optimizer.  Without this
            # explicit synchronization, a resumed run can continue at the
            # warmup floor (0.1x here) even though the scheduler position is
            # correct.
            restored_lrs = scheduler.get_last_lr()
            if len(restored_lrs) != len(optimizer.param_groups):
                raise RuntimeError(
                    "Scheduler/optimizer param-group count mismatch while "
                    f"restoring LR: {len(restored_lrs)} vs "
                    f"{len(optimizer.param_groups)}"
                )
            for param_group, restored_lr in zip(
                optimizer.param_groups, restored_lrs
            ):
                param_group["lr"] = float(restored_lr)
            if is_main_process:
                print(
                    f"{DEBUG_PRINT_PREFIX}Restored LR scheduler state "
                    f"(last_epoch={getattr(scheduler, 'last_epoch', '?')}, "
                    f"optimizer_lr={optimizer.param_groups[0]['lr']:.12g})."
                )
        except Exception as e:
            if STRICT_CONTINUATION:
                raise RuntimeError(
                    "Strict continuation: could not restore the parent LR "
                    f"scheduler state: {e}"
                ) from e
            if is_main_process:
                print(
                    f"{DEBUG_PRINT_PREFIX}Could not restore scheduler state: {e}. "
                    "LR schedule restarts from step 0."
                )

    ae_model = None
    val_sample_loader = (
        None
    )
    if is_main_process and PARTIAL_EVALUATION:
        if not os.path.exists(AUTOENCODER_CHECKPOINT):
            raise FileNotFoundError(
                f"[Rank 0] AE Model not found at {AUTOENCODER_CHECKPOINT}"
            )

        print(f"{DEBUG_PRINT_PREFIX}Loading Autoencoder for evaluation...")

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

        checkpoint = torch.load(
            AUTOENCODER_CHECKPOINT, map_location=device
        )
        # Remove 'module.' prefix if it exists (in case the AE was trained with DDP)
        new_state_dict = {}
        for k, v in checkpoint["model_state_dict"].items():
            new_key = k.replace("module.", "") if k.startswith("module.") else k
            new_state_dict[new_key] = v
        ae_model.load_state_dict(new_state_dict)
        ae_model = ae_model.to(device)
        ae_model.eval()
        print(f"{DEBUG_PRINT_PREFIX}Autoencoder loaded successfully.")

        VAL_SAMPLE_FILE = (
            args.partial_evaluation_file
            or f"{DEFAULT_RAW_DIR}/nowcast_validation_full.h5"
        )
        VAL_SAMPLE_META = (
            args.partial_evaluation_meta
            or f"{DEFAULT_RAW_DIR}/nowcast_validation_full_META.csv"
        )

        val_sample_dataset = DynamicSequentialSevirDataset(
            meta_csv=VAL_SAMPLE_META,
            data_file=VAL_SAMPLE_FILE,
            data_type=DATA_KEY,
            raw_seq_len=RAW_SEQ_LEN,
            lag_time=INPUT_LENGTH,
            lead_time=OUTPUT_LENGTH,
            time_spacing=TIME_SPACING,
            stride=STRIDE,
            channel_last=False,
            debug_mode=DEBUG_MODE,
        )

        val_sample_loader = DataLoader(
            val_sample_dataset,
            batch_size=(
                BATCH_SIZE // 4 if BATCH_SIZE > 4 else BATCH_SIZE
            ),
            shuffle=False,
            collate_fn=dynamic_sequential_collate,
            num_workers=NUM_WORKERS if not DEBUG_MODE else 0,
            pin_memory=True if not DEBUG_MODE else False,
        )
        print(f"{DEBUG_PRINT_PREFIX}Test loader created for partial evaluation.")

    early_stopping = None
    best_val_loss_init = None

    if EARLY_STOPPING_METRIC == "val_loss":
        best_val_loss_init = (
            float("inf") if preload_best_val_loss is None else preload_best_val_loss
        )
        metric_direction = "minimize"
    elif EARLY_STOPPING_METRIC in ["partial_csi_m", "partial_mse"]:
        best_val_loss_init = (
            -np.inf if preload_best_val_loss is None else preload_best_val_loss
        )
        metric_direction = (
            "maximize" if EARLY_STOPPING_METRIC == "partial_csi_m" else "minimize"
        )
        if (
            metric_direction == "minimize"
        ):
            best_val_loss_init = (
                float("inf") if preload_best_val_loss is None else preload_best_val_loss
            )
            print(
                f"{DEBUG_PRINT_PREFIX} Early stopping set to MINIMIZE {EARLY_STOPPING_METRIC}"
            )
        else:
            print(
                f"{DEBUG_PRINT_PREFIX} Early stopping set to MAXIMIZE {EARLY_STOPPING_METRIC}"
            )
    else:
        if is_main_process:
            print(
                f"{DEBUG_PRINT_PREFIX} Warning: Unknown early stopping metric '{EARLY_STOPPING_METRIC}'. Defaulting to validation loss."
            )
        best_val_loss_init = (
            float("inf") if preload_best_val_loss is None else preload_best_val_loss
        )
        metric_direction = "minimize"

    initial_metric_tensor = torch.tensor(
        best_val_loss_init if best_val_loss_init is not None else float("inf"),
        device=device,
    )
    if world_size > 1:
        dist.broadcast(initial_metric_tensor, src=0)
    synced_best_val_loss_init = initial_metric_tensor.item()

    if is_main_process:
        early_stopping = EarlyStopping(
            patience=EARLY_STOPPING_PATIENCE,
            verbose=True,
            path=MODEL_SAVE_PATH,
            initial_best_metric=synced_best_val_loss_init,
            metric_direction=metric_direction,
        )
        print(
            f"{DEBUG_PRINT_PREFIX}Initialized EarlyStopping with initial best metric: {synced_best_val_loss_init}, direction: {metric_direction}"
        )

    if is_main_process:
        print(f"{DEBUG_PRINT_PREFIX}Starting training, run id: {MAIN_RUN_ID}")

    global_step = 0 if preload_global_step is None else preload_global_step
    SMOKE_BATCHES = int(args.smoke_batches)
    smoke_batches_done = 0
    smoke_rollout_batches = 0
    if SMOKE_BATCHES > 0 and is_main_process:
        print(
            f"{DEBUG_PRINT_PREFIX}MEMORY SMOKE MODE: {SMOKE_BATCHES} batches, "
            "then report peak memory and exit without checkpointing."
        )

    # decoded-pixel path for the UOT loss: every rank needs the frozen AE
    train_decode_fn = None
    if UOT_ENABLED:
        if AUTOENCODER_CHECKPOINT is None:
            raise ValueError(
                "uot_params.enabled requires autoencoder_params.autoencoder_checkpoint"
            )
        train_ae_model = build_autoencoder(config, device)
        normalizer_module = model.module if world_size > 1 else model
        train_decode_fn = make_decode_fn(
            normalizer_module,
            train_ae_model,
            NORMALIZED_AUTOENCODER,
            PIXEL_SCALE,
            DATASET_NAME,
        )
        if is_main_process:
            print(f"{DEBUG_PRINT_PREFIX}Loaded frozen AE on all ranks for UOT decode path.")

    scaler = torch.amp.GradScaler(device=device.type, enabled=USE_FP16)

    # continue the epoch budget across resumes (see latest_payload): a
    # fresh 0..NUM_EPOCHS loop would re-spend the whole schedule
    start_epoch = int(preload_epoch) + 1 if preload_epoch is not None else 0

    # Absolute stop for a matched continuation.  It must be an ABSOLUTE epoch
    # index, never `start_epoch + budget`: after a supervisor restart
    # `start_epoch` is the arm's own latest epoch, so a relative budget would
    # silently re-grant the full budget on every crash and the arms would end
    # up with different amounts of training.
    #
    # `num_epochs` stays at the original full schedule because
    # `total_num_steps` (and therefore the cosine T_max and warmup length) is
    # derived from it -- shortening it would change the LR trajectory, which
    # is exactly the confound a matched continuation exists to avoid.
    end_epoch = int(
        OmegaConf.select(
            config,
            "training_params.continuation_end_epoch_exclusive",
            default=NUM_EPOCHS,
        )
    )
    end_epoch = min(end_epoch, NUM_EPOCHS)
    if start_epoch >= end_epoch:
        raise RuntimeError(
            "No continuation epochs remain: "
            f"start_epoch={start_epoch}, end_epoch={end_epoch} "
            f"(num_epochs={NUM_EPOCHS}, "
            "training_params.continuation_end_epoch_exclusive="
            f"{OmegaConf.select(config, 'training_params.continuation_end_epoch_exclusive', default=None)}). "
            "Set continuation_end_epoch_exclusive to (parent_epoch + 1 + budget)."
        )
    if preload_continuation_end is not None and int(
        preload_continuation_end
    ) != end_epoch:
        raise RuntimeError(
            "Continuation budget changed across resume: checkpoint recorded "
            f"continuation_end_epoch_exclusive={int(preload_continuation_end)}, "
            f"config says {end_epoch}.  Refusing to silently extend or shorten "
            "an arm's budget mid-run."
        )
    if is_main_process:
        print(
            f"{DEBUG_PRINT_PREFIX}Epoch loop: [{start_epoch}, {end_epoch}) "
            f"= {end_epoch - start_epoch} epochs "
            f"(full schedule num_epochs={NUM_EPOCHS})."
        )

    for epoch in range(start_epoch, end_epoch):
        train_sampler.set_epoch(epoch)
        val_sampler.set_epoch(
            epoch
        )

        model.train()
        train_loss_accum = 0.0
        train_count = 0

        train_bar_desc = f"Training Epoch {epoch} (Rank {rank})"
        train_bar = tqdm(
            train_loader,
            desc=train_bar_desc,
            disable=not is_main_process,
            position=rank,
            leave=False,
        )

        optimizer.zero_grad()

        for batch_idx, batch in enumerate(train_bar):
            inputs, outputs, metadata = batch
            inputs = inputs.to(device, non_blocking=True)
            outputs = outputs.to(device, non_blocking=True)

            current_model = model.module if world_size > 1 else model

            step_uot_params = uot_loss_params
            if uot_loss_params is not None and UOT_WARMUP_STEPS > 0:
                ramp = min(1.0, global_step / float(UOT_WARMUP_STEPS))
                step_uot_params = {
                    **uot_loss_params,
                    "weight": uot_loss_params["weight"] * ramp,
                }

            with torch.amp.autocast(device_type=device.type, enabled=USE_FP16):
                (
                    final_batch_loss,
                    uot_term_stat,
                    rmlf_term_stats,
                ) = compute_chunked_rflow_loss(
                    model_forward=model,
                    normalizer_model=current_model,
                    inputs=inputs,
                    outputs=outputs,
                    input_length=INPUT_LENGTH,
                    output_length=OUTPUT_LENGTH,
                    num_train_timesteps=NUM_TRAIN_TIMESTEPS,
                    decode_fn=train_decode_fn,
                    uot_loss=uot_loss_module,
                    uot_params=step_uot_params,
                    rmlf_controller=rmlf_controller,
                    rmlf_teacher=rmlf_teacher,
                    global_step=global_step,
                    return_rmlf_stats=True,
                )

            if final_batch_loss is None:
                raise ValueError("final_batch_loss is None")

            scaled_loss = final_batch_loss / GRAD_ACCUMULATION_STEPS
            scaler.scale(scaled_loss).backward()

            raw_loss_value = final_batch_loss.item()
            train_loss_accum += raw_loss_value
            train_count += 1

            if (batch_idx + 1) % GRAD_ACCUMULATION_STEPS == 0 or (batch_idx + 1) == len(
                train_loader
            ):
                scaler.unscale_(optimizer)
                # returns the total norm BEFORE clipping: free monitor for
                # whether the UOT term is crowding the base loss out of the
                # clipping budget (plain-run reference ~1.9; a run where UOT
                # dominates the gradient showed 4.7 with GRAD_CLIP=1.0)
                pre_clip_norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), GRAD_CLIP
                )
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()

                if SCHEDULER_TYPE == "cosine":
                    scheduler.step()

                if EMA_MODEL_SAVING and eval_ema_model is not None:
                    ema(
                        (
                            model.module if world_size > 1 else model
                        ),
                        eval_ema_model,
                        EMA_MODEL_SAVING_DECAY,
                    )

                if is_main_process:
                    current_lr = optimizer.param_groups[0]["lr"]

                    log_data = {
                        "training_loss_step": raw_loss_value,
                        "learning_rate": current_lr,
                        "grad_norm_preclip": float(pre_clip_norm),
                    }
                    if uot_term_stat is not None:
                        log_data["uot_term"] = uot_term_stat
                        log_data["uot_ratio"] = uot_term_stat / max(
                            raw_loss_value - uot_term_stat, 1e-8
                        )
                    if rmlf_term_stats is not None:
                        log_data.update(rmlf_term_stats)

                    if ENABLE_WANDB:
                        wandb.log(log_data, step=global_step)

            global_step += BATCH_SIZE
            if is_main_process:
                postfix = {"training_loss": f"{raw_loss_value:.4f}"}
                if uot_term_stat is not None:
                    # surfaces the calibration target (see ~line 403: aim for
                    # 5-20%) in the log file, since wandb is usually disabled
                    postfix["uot_ratio"] = (
                        f"{uot_term_stat / max(raw_loss_value - uot_term_stat, 1e-8):.4f}"
                    )
                if rmlf_term_stats is not None:
                    postfix["rmlf_p"] = f"{rmlf_term_stats['rmlf_rollout_fraction']:.2f}"
                    postfix["rmlf_a"] = f"{rmlf_term_stats['rmlf_corruption']:.2f}"
                train_bar.set_postfix(postfix)

            if SMOKE_BATCHES > 0:
                smoke_batches_done += 1
                if (
                    rmlf_term_stats is not None
                    and rmlf_term_stats.get("rmlf_rollout_fraction", 0.0) > 0.0
                ):
                    smoke_rollout_batches += 1
                if smoke_batches_done >= SMOKE_BATCHES:
                    if device.type == "cuda":
                        torch.cuda.synchronize(device)
                        peak = torch.tensor(
                            [
                                float(torch.cuda.max_memory_allocated(device)),
                                float(torch.cuda.max_memory_reserved(device)),
                            ],
                            device=device,
                        )
                        if world_size > 1:
                            dist.all_reduce(peak, op=dist.ReduceOp.MAX)
                        allocated, reserved = (peak / 2 ** 30).tolist()
                    else:
                        allocated = reserved = float("nan")
                    if is_main_process:
                        total = (
                            torch.cuda.get_device_properties(device).total_memory
                            / 2 ** 30
                            if device.type == "cuda"
                            else float("nan")
                        )
                        print(
                            f"\n{DEBUG_PRINT_PREFIX}MEMORY SMOKE "
                            f"({smoke_batches_done} batches, {world_size} rank(s))\n"
                            f"{DEBUG_PRINT_PREFIX}  peak allocated (max over ranks): "
                            f"{allocated:.2f} GiB\n"
                            f"{DEBUG_PRINT_PREFIX}  peak reserved  (max over ranks): "
                            f"{reserved:.2f} GiB\n"
                            f"{DEBUG_PRINT_PREFIX}  device total                   : "
                            f"{total:.2f} GiB\n"
                            f"{DEBUG_PRINT_PREFIX}  rollout-conditioned batches    : "
                            f"{smoke_rollout_batches}/{smoke_batches_done}\n"
                            f"{DEBUG_PRINT_PREFIX}  uot decode path                : "
                            f"{'on' if train_decode_fn is not None else 'off'}\n"
                            f"{DEBUG_PRINT_PREFIX}  ddp                            : "
                            f"{'on' if world_size > 1 else 'off'}"
                        )
                    if rmlf_config.enabled and smoke_rollout_batches == 0:
                        raise RuntimeError(
                            "Memory smoke saw no rollout-conditioned batch, so "
                            "the teacher bridge never ran and this is not the "
                            "arm's real peak.  Re-run with "
                            "rmlf_params.rollout_probability: 1.0 and "
                            "warmup_steps: 0."
                        )
                    if world_size > 1:
                        dist.barrier()
                    cleanup_ddp()
                    return

            if (
                is_main_process
                and SAVE_LATEST_EVERY > 0
                and RESUME_LATEST_PATH
                and (batch_idx + 1) % SAVE_LATEST_EVERY == 0
            ):
                latest_payload = {
                    "model_state_dict": (
                        model.module if world_size > 1 else model
                    ).state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "scheduler_state_dict": scheduler.state_dict(),
                    "global_step": global_step,
                    # resume must also restore WHERE IN THE EPOCH BUDGET we
                    # are: without it the epoch loop restarts at 0 and the
                    # run trains NUM_EPOCHS *more* epochs, pushing the
                    # cosine schedule past T_max (LR starts rising again)
                    # and compounding with every crash-resume
                    "epoch": epoch,
                    "best_metric": (
                        early_stopping.best_metric
                        if early_stopping is not None
                        else None
                    ),
                    "mean": mean,
                    "std": std,
                }
                # Legacy payloads stay byte-identical unless a config asks for
                # the extra state.  The rollout TEACHER is deliberately absent:
                # it is pinned by rmlf_params.teacher_checkpoint, so a resume
                # cannot silently change it.
                if SAVE_EMA_IN_LATEST and eval_ema_model is not None:
                    latest_payload["ema_model_state_dict"] = (
                        eval_ema_model.state_dict()
                    )
                if rmlf_controller is not None:
                    latest_payload["rmlf_state_dict"] = rmlf_controller.state_dict()
                latest_payload["continuation_end_epoch_exclusive"] = end_epoch
                tmp_path = RESUME_LATEST_PATH + ".tmp"
                torch.save(latest_payload, tmp_path)
                os.replace(tmp_path, RESUME_LATEST_PATH)  # atomic swap
                print(
                    f"{DEBUG_PRINT_PREFIX}Saved latest checkpoint at batch "
                    f"{batch_idx + 1} (global_step {global_step})."
                )

            if DEBUG_MODE and batch_idx >= 2:
                if is_main_process:
                    print(
                        f"{DEBUG_PRINT_PREFIX}Debug break after {batch_idx+1} batches."
                    )
                break
        train_bar.close()

        avg_train_loss_local = (
            train_loss_accum / train_count if train_count > 0 else 0.0
        )
        loss_tensor = torch.tensor(avg_train_loss_local, device=device)
        if world_size > 1:
            loss_tensor = reduce_tensor(
                loss_tensor, world_size
            )
        avg_train_loss_global = loss_tensor.item()

        model.eval()
        if eval_ema_model is not None:
            eval_ema_model.eval()

        val_loss_accum = 0.0
        val_count = 0

        val_bar_desc = f"Validation Epoch {epoch} (Rank {rank})"
        val_bar = tqdm(
            val_loader,
            desc=val_bar_desc,
            disable=not is_main_process,
            position=rank,
            leave=False,
        )

        with torch.no_grad():
            for batch in val_bar:
                inputs, outputs, metadata = batch
                inputs = inputs.to(device, non_blocking=True)
                outputs = outputs.to(device, non_blocking=True)

                current_model = model.module if world_size > 1 else model

                with torch.amp.autocast(device_type=device.type, enabled=USE_FP16):
                    loss, _ = compute_chunked_rflow_loss(
                        model_forward=current_model,
                        normalizer_model=current_model,
                        inputs=inputs,
                        outputs=outputs,
                        input_length=INPUT_LENGTH,
                        output_length=OUTPUT_LENGTH,
                        num_train_timesteps=NUM_TRAIN_TIMESTEPS,
                        decode_fn=train_decode_fn,
                        uot_loss=uot_loss_module,
                        uot_params=uot_loss_params,
                    )

                val_loss_accum += loss.item() * inputs.size(0)
                val_count += inputs.size(0)

                if is_main_process:
                    val_bar.set_postfix(
                        {"validation_loss": "{:.4f}".format(loss.item())}
                    )

                if (
                    DEBUG_MODE and val_count // BATCH_SIZE >= 3
                ):
                    if is_main_process:
                        print(f"{DEBUG_PRINT_PREFIX}Debug break during validation.")
                    break
        val_bar.close()

        val_loss_total_tensor = torch.tensor(val_loss_accum, device=device)
        val_count_total_tensor = torch.tensor(val_count, device=device)

        if world_size > 1:
            dist.all_reduce(val_loss_total_tensor, op=dist.ReduceOp.SUM)
            dist.all_reduce(val_count_total_tensor, op=dist.ReduceOp.SUM)

        avg_val_loss_global = (
            (val_loss_total_tensor / val_count_total_tensor).item()
            if val_count_total_tensor > 0
            else 0.0
        )

        if SCHEDULER_TYPE == "plateau":
            scheduler.step(avg_val_loss_global)

        partial_eval_results = None
        if (
            is_main_process
            and PARTIAL_EVALUATION
            and (epoch % PARTIAL_EVALUATION_INTERVAL == 0)
        ):

            print(
                f"{DEBUG_PRINT_PREFIX}Running Partial Evaluation for Epoch {epoch}..."
            )
            eval_model = (
                eval_ema_model
                if EMA_MODEL_SAVING and eval_ema_model is not None
                else (model.module if world_size > 1 else model)
            )
            eval_model.eval()

            partial_eval_results = partial_evaluate_model(
                model=eval_model,
                device=device,
                val_sample_loader=val_sample_loader,
                dataset_name=DATASET_NAME,
                thresholds=THRESHOLDS,
                global_step=global_step,
                epoch=epoch,
                ae_model=ae_model,
                normalized_autoencoder=NORMALIZED_AUTOENCODER,
                use_fp16=USE_FP16,
                partial_evaluation_batches=PARTIAL_EVALUATION_BATCHES,
                input_length=INPUT_LENGTH,
                output_length=OUTPUT_LENGTH,
                num_train_timesteps=NUM_TRAIN_TIMESTEPS,
                euler_steps=EULER_STEPS,
                enable_wandb=ENABLE_WANDB,
                wandb_instance=wandb if ENABLE_WANDB else None,
                debug_print_prefix=DEBUG_PRINT_PREFIX,
                plots_folder=METRICS_FOLDER,
                cartopy_features=CARTOPY_FEATURES,
                ema_model_evaluated=EMA_MODEL_SAVING
                and eval_ema_model is not None,
                pixel_scale=PIXEL_SCALE,
                batch_size_autoencoder=(
                    None if BATCH_SIZE > 2 else BATCH_SIZE
                ),
            )
            print(f"{DEBUG_PRINT_PREFIX}Partial Evaluation finished.")

        if is_main_process:
            current_lr = optimizer.param_groups[0]["lr"]
            print(
                f"Finished Epoch {epoch} - Train Loss: {avg_train_loss_global:.4f}, Val Loss: {avg_val_loss_global:.4f}, LR: {current_lr:.6f}"
            )
            if ENABLE_WANDB:
                log_data = {
                    "epoch": epoch,
                    "avg_training_loss": avg_train_loss_global,
                    "avg_validation_loss": avg_val_loss_global,
                    "learning_rate": current_lr,
                }
                wandb.log(log_data, step=global_step)

        stop_signal_tensor = torch.tensor(
            0, device=device, dtype=torch.int
        )
        if is_main_process and early_stopping is not None:
            if EARLY_STOPPING_METRIC == "val_loss":
                current_metric = avg_val_loss_global
            elif EARLY_STOPPING_METRIC == "partial_mse":
                current_metric = (
                    partial_eval_results.get("mse_mean", float("inf"))
                    if partial_eval_results
                    else float("inf")
                )
            elif EARLY_STOPPING_METRIC == "partial_csi_m":
                current_metric = (
                    partial_eval_results.get("csi_from_mean_m", -np.inf)
                    if partial_eval_results
                    else -np.inf
                )
            else:
                current_metric = avg_val_loss_global

            model_to_save = (
                eval_ema_model
                if EMA_MODEL_SAVING and eval_ema_model is not None
                else (model.module if world_size > 1 else model)
            )

            if (
                SNAPSHOT_EVERY_EPOCHS > 0
                and (epoch + 1) % SNAPSHOT_EVERY_EPOCHS == 0
            ):
                # Weights only: the optimizer state is ~2x the parameters and
                # a snapshot is never resumed from (resuming uses the raw
                # `*_latest.pt`, which carries optimizer + scheduler + epoch).
                # Keeping them separate is what stops an EMA checkpoint from
                # being mistaken for a resumable one.
                snap_path = os.path.join(
                    SNAPSHOT_FOLDER,
                    f"{'ema' if EMA_MODEL_SAVING and eval_ema_model is not None else 'raw'}"
                    f"_epoch{epoch:04d}_step{global_step}.pt",
                )
                tmp_snap = snap_path + ".tmp"
                torch.save(
                    {
                        "model_state_dict": model_to_save.state_dict(),
                        "global_step": global_step,
                        "epoch": epoch,
                        "mean": getattr(model_to_save, "mean", None),
                        "std": getattr(model_to_save, "std", None),
                        "selection_metric_name": EARLY_STOPPING_METRIC,
                        "selection_metric_value": current_metric,
                        "learning_rate": optimizer.param_groups[0]["lr"],
                        "is_ema": bool(
                            EMA_MODEL_SAVING and eval_ema_model is not None
                        ),
                    },
                    tmp_snap,
                )
                os.replace(tmp_snap, snap_path)
                print(
                    f"{DEBUG_PRINT_PREFIX}Snapshot saved: {snap_path} "
                    f"({EARLY_STOPPING_METRIC}={current_metric:.6f})"
                )

            early_stopping(current_metric, model_to_save, optimizer, epoch, global_step)

            if early_stopping.early_stop:
                print(f"{DEBUG_PRINT_PREFIX}Early stopping triggered.")
                stop_signal_tensor = torch.tensor(1, device=device, dtype=torch.int)

        if world_size > 1:
            dist.broadcast(stop_signal_tensor, src=0)

        if stop_signal_tensor.item() == 1:
            if is_main_process:
                print("Early stopping condition met. Finalizing training.")
            break

        if world_size > 1:
            dist.barrier()

    if is_main_process:
        print(f"{DEBUG_PRINT_PREFIX}Finished training, run id: {MAIN_RUN_ID}")
        if ENABLE_WANDB:
            wandb.finish()

    cleanup_ddp()

# Seed for the partial-evaluation noise stream. Changing this -- or the
# validation set, euler_steps, S, or raw-vs-EMA -- makes partial_csi_m a
# DIFFERENT statistic, whose values must not be compared across the change.
PARTIAL_EVAL_SEED = 20260728


def partial_evaluate_model(
    model,
    device,
    val_sample_loader,
    dataset_name,
    thresholds,
    global_step,
    epoch,
    ae_model,
    normalized_autoencoder,
    use_fp16,
    partial_evaluation_batches,
    input_length,
    output_length,
    num_train_timesteps,
    euler_steps,
    enable_wandb,
    wandb_instance,
    debug_print_prefix,
    plots_folder,
    cartopy_features,
    ema_model_evaluated,
    pixel_scale,
    batch_size_autoencoder=None,
):
    """
    Runs a partial evaluation on a subset of the validation data.

    This is executed periodically on the main process during training. It generates
    predictions using ODE integration, decodes them with the autoencoder, calculates
    nowcasting metrics (CSI, MSE, etc.), and creates animations for visual inspection.

    Note: This function runs only on the main DDP process (rank 0). In the future
    we can parallelize this function across all processes.

    Args:
        model (nn.Module): The unwrapped model (or its EMA version) to be evaluated.
        device (torch.device): The device of the main process.
        val_sample_loader (DataLoader): DataLoader for the validation subset.
        dataset_name (str): Dataset identifier for dataset-specific evaluation handling.
        thresholds (np.ndarray): Array of thresholds for computing categorical metrics.
        global_step (int): The current global training step for logging.
        epoch (int): The current epoch number.
        ae_model (nn.Module): The pre-trained autoencoder for decoding predictions.
        normalized_autoencoder (bool): Flag indicating if the AE expects normalized inputs.
        use_fp16 (bool): Whether to use mixed-precision for inference.
        partial_evaluation_batches (int): The number of batches to evaluate.
        enable_wandb (bool): If True, log results to WandB.
        wandb_instance: The active WandB run instance.
        debug_print_prefix (str): Prefix for print statements.
        plots_folder (str): Directory to save generated plots and animations.
        cartopy_features (list): List of features to draw on cartopy plots.
        ema_model_evaluated (bool): Flag to indicate if the EMA model is being evaluated.
        pixel_scale (float): Dataset-specific evaluation scale.
        batch_size_autoencoder (int, optional): Batch size for the autoencoder's forward pass.

    Returns:
        dict or None: A dictionary containing the computed metrics, or None if evaluation fails.
    """
    results = None
    model.eval()
    if ae_model:
        ae_model.eval()

    with torch.no_grad():
        metrics_accumulators = [
            MetricsAccumulator(
                lead_time=lt,
                thresholds=thresholds,
                pool_size=16,
                compute_mse=True,
                compute_threshold=True,
                compute_crps=True,
                compute_fss=True,
                fss_scales=[1, 4, 16],
                device=device,
            )
            for lt in range(output_length)
        ]
        count = 0
        y_pred_batches = []
        y_true_batches = []
        first_metadata = None

        # Common random numbers: ONE generator per evaluation call, seeded
        # identically every epoch and then consumed continuously across all
        # batches. Unseeded, partial_csi_m is a fresh S=1 draw each epoch and
        # its swing can exceed the effect this run exists to measure (UOT was
        # +0.63% on CIKM) -- early stopping would then freeze weights picked
        # partly by luck. Seeding inside the batch loop is equally wrong: it
        # hands every batch the same noise, collapsing the panel to a single
        # realisation instead of an independent draw per event. Created here,
        # the stream is reproducible across epochs and across the plain/UOT
        # twins while still varying from event to event.
        eval_generator = torch.Generator(device=device)
        eval_generator.manual_seed(PARTIAL_EVAL_SEED)

        eval_bar = tqdm(
            val_sample_loader, desc=f"Partial Eval Epoch {epoch}", leave=False
        )

        for batch in eval_bar:
            x_cond, x_true, metadata = batch
            x_cond = x_cond.to(device, non_blocking=True)
            x_true = x_true.to(device, non_blocking=True)

            B, C, T_in, H, W = x_cond.shape
            x_cond = x_cond.permute(0, 2, 1, 3, 4).reshape(B * T_in, C, H, W)

            if normalized_autoencoder:
                x_cond = x_cond / 255.0

            if ae_model:
                encoded_chunks = []
                bs_ae = (
                    batch_size_autoencoder
                    if batch_size_autoencoder is not None
                    else x_cond.shape[0]
                )
                for i in range(0, x_cond.shape[0], bs_ae):
                    chunk = x_cond[i : i + bs_ae]
                    encoded_chunk = ae_model.encode(chunk)
                    encoded_chunk = encoded_chunk.latent_dist.mode()
                    encoded_chunks.append(encoded_chunk)
                x_cond = torch.cat(encoded_chunks, dim=0)
            else:
                print(
                    f"{debug_print_prefix}Warning: AE model not available for encoding in partial eval."
                )
                latent_channels, latent_H, latent_W = (
                    4,
                    H // 8,
                    W // 8,
                )
                x_cond = torch.randn(
                    B * T_in, latent_channels, latent_H, latent_W, device=device
                )

            latent_channels, latent_H, latent_W = (
                x_cond.shape[1],
                x_cond.shape[2],
                x_cond.shape[3],
            )
            x_cond = x_cond.reshape(B, T_in, latent_channels, latent_H, latent_W)
            x_cond = x_cond.permute(0, 1, 3, 4, 2).contiguous()
            x_cond = model.normalize(x_cond)

            x_true = x_true.squeeze(1)
            if dataset_name == "cikm":
                x_true = x_true[:, :, 13:-14, 13:-14]
            x_true = raw_to_eval_scale(x_true, dataset_name, pixel_scale)
            H_true, W_true = x_true.shape[2], x_true.shape[3]
            with torch.amp.autocast(device_type=device.type, enabled=use_fp16):
                x_pred = autoregressive_sample(
                    model=model,
                    initial_cond=x_cond,
                    input_length=input_length,
                    output_length=output_length,
                    num_train_timesteps=num_train_timesteps,
                    euler_steps=euler_steps,
                    generator=eval_generator,
                ).unsqueeze(1)

            x_true_np = x_true.cpu().numpy()
            x_pred = model.denormalize(x_pred)
            B, S, T, H_latent, W_latent, C_latent = x_pred.shape
            x_pred_tensor = x_pred.reshape(B * S * T, H_latent, W_latent, C_latent)
            x_pred_tensor = x_pred_tensor.permute(0, 3, 1, 2).contiguous()

            if ae_model:
                decoded_chunks = []
                bs_ae = (
                    batch_size_autoencoder
                    if batch_size_autoencoder is not None
                    else x_pred_tensor.shape[0]
                )
                for i in range(0, x_pred_tensor.shape[0], bs_ae):
                    chunk = x_pred_tensor[i : i + bs_ae]
                    decoded_chunk = ae_model.decode(chunk)
                    decoded_chunk = decoded_chunk.sample
                    decoded_chunks.append(decoded_chunk)
                x_pred_tensor = torch.cat(
                    decoded_chunks, dim=0
                )
            else:
                print(
                    f"{debug_print_prefix}Warning: AE model not available for decoding in partial eval."
                )
                x_pred_tensor = (
                    torch.rand(B * S * T, 1, H_true, W_true, device=device)
                    * pixel_scale
                )

            x_pred_tensor = decoded_to_eval_scale(
                x_pred_tensor,
                dataset_name,
                pixel_scale,
                normalized_autoencoder,
            )

            if dataset_name == "cikm":
                x_pred_tensor = x_pred_tensor[:, :, 13:-14, 13:-14]

            if torch.isnan(x_pred_tensor).any():
                print(f"{debug_print_prefix} WARNING: NaN values found in x_pred after decode (likely due to FP16) - Please rerun with fp16: false")

            x_pred_tensor = x_pred_tensor.reshape(B, S, T, 1, H_true, W_true)
            x_pred_tensor = x_pred_tensor.permute(
                0, 1, 2, 4, 5, 3
            )
            if x_pred_tensor.shape[-1] == 1:
                x_pred_tensor = x_pred_tensor.squeeze(-1)

            x_pred_np = x_pred_tensor.cpu().numpy().astype(np.float32)

            y_pred_batches.append(x_pred_np)
            y_true_batches.append(x_true_np)
            if first_metadata is None:
                first_metadata = metadata[0]

            count += B
            if (
                count >= partial_evaluation_batches * val_sample_loader.batch_size
            ):
                break
        eval_bar.close()

        if not y_pred_batches:
            print(
                f"{debug_print_prefix}No batches processed during partial evaluation."
            )
            return None

        y_pred_array = np.concatenate(y_pred_batches, axis=0)
        y_true_array = np.concatenate(y_true_batches, axis=0)

        y_pred_array = post_process_samples(
            y_pred_array, clamp_min=0.0, clamp_max=pixel_scale
        )

        for metrics_accumulator in metrics_accumulators:
            metrics_accumulator.update(y_true_array, y_pred_array)

        results = calculate_metrics(
            num_lead_times=output_length,
            metrics_accumulators=metrics_accumulators,
            thresholds=thresholds,
        )
        EMA_SUFFIX = "(EMA)" if ema_model_evaluated else ""
        print(
            f"{debug_print_prefix}Partial Results {EMA_SUFFIX}: MSE: {results.get('mse_from_mean_mean', 'N/A')}, "
            f"CSI-M: {results.get('csi_from_mean_m', 'N/A')}, CSI (pool)-M: {results.get('csi_pooled_from_mean_m', 'N/A')}, "
            f"HSS-M: {results.get('hss_from_mean_m', 'N/A')}, FAR-M: {results.get('far_from_mean_m', 'N/A')}, "
            f"POD-M: {results.get('pod_from_mean_m', 'N/A')}, FSS-M: {results.get('fss_m_from_mean', 'N/A')}"
        )

        # Per-threshold CSI/FAR: CSI-M is the equal-weight mean over
        # thresholds, so a gain at 40 dBZ contributes only 1/4 of itself
        # and is indistinguishable from a gain at 20 dBZ (or from a 40 dBZ
        # LOSS masked by a 20 dBZ gain). The transport-geometry claim is
        # specifically about the sparse high-threshold cores, so the
        # decomposition - already computed here - must be surfaced.
        per_thr_csi = results.get("csi_from_mean_mean") or {}
        per_thr_far = results.get("far_from_mean_mean") or {}
        if per_thr_csi:
            print(
                f"{debug_print_prefix}Partial CSI per threshold: "
                + ", ".join(
                    f"{float(k):.0f}dBZ={float(v):.4f}"
                    for k, v in sorted(per_thr_csi.items(), key=lambda kv: float(kv[0]))
                )
            )

        EMA_SUFFIX_WANDB = "_EMA" if ema_model_evaluated else ""
        if enable_wandb and wandb_instance:
            log_dict = {
                f"partial_mse{EMA_SUFFIX_WANDB}": results["mse_from_mean_mean"],
                f"partial_csi_m{EMA_SUFFIX_WANDB}": results["csi_from_mean_m"],
                f"partial_csi_pool_m{EMA_SUFFIX_WANDB}": results[
                    "csi_pool_from_mean_m"
                ],
                f"partial_hss_m{EMA_SUFFIX_WANDB}": results["hss_from_mean_m"],
                f"partial_far_m{EMA_SUFFIX_WANDB}": results["far_from_mean_m"],
                f"partial_pod_m{EMA_SUFFIX_WANDB}": results["pod_from_mean_m"],
                f"partial_fss_m{EMA_SUFFIX_WANDB}": results["fss_m_from_mean"],
            }
            for k, v in per_thr_csi.items():
                log_dict[f"partial_csi_t{float(k):.0f}{EMA_SUFFIX_WANDB}"] = float(v)
            for k, v in per_thr_far.items():
                log_dict[f"partial_far_t{float(k):.0f}{EMA_SUFFIX_WANDB}"] = float(v)
            wandb_instance.log(log_dict, step=global_step)

        try:
            sample_pred_plot = y_pred_array[0, 0]
            sample_true_plot = y_true_array[0]

            epoch_anim_folder_suffix = "_ema" if ema_model_evaluated else ""
            epoch_anim_folder = os.path.join(
                plots_folder, f"animations{epoch_anim_folder_suffix}", f"Epoch_{epoch}"
            )
            os.makedirs(epoch_anim_folder, exist_ok=True)

            fig1 = plt.figure()
            anim1 = make_animation(
                sample_pred_plot,
                first_metadata,
                title=f"Output Epoch {epoch}{EMA_SUFFIX}",
                fig=fig1,
                cartopy_features=cartopy_features,
            )
            anim1_path = os.path.join(
                epoch_anim_folder, f"output_test_animation_sample0.gif"
            )
            anim1.save(anim1_path, writer="imagemagick", fps=6)
            plt.close(fig1)

            fig2 = plt.figure()
            anim2 = make_animation(
                sample_true_plot,
                first_metadata,
                title=f"Target Epoch {epoch}",
                fig=fig2,
                cartopy_features=cartopy_features,
            )
            anim2_path = os.path.join(epoch_anim_folder, "target_test_animation.gif")
            anim2.save(anim2_path, writer="imagemagick", fps=6)
            plt.close(fig2)

            if enable_wandb and wandb_instance:
                wandb_instance.log(
                    {
                        f"Prediction Animation{EMA_SUFFIX_WANDB}": wandb.Video(
                            anim1_path, fps=6, format="gif"
                        ),
                        "Target Animation": wandb.Video(
                            anim2_path, fps=6, format="gif"
                        ),
                    },
                    step=global_step,
                )

        except Exception as e:
            print(f"{debug_print_prefix} Error creating or saving animations: {e}")

    return results


if __name__ == "__main__":
    is_distributed = "RANK" in os.environ and "WORLD_SIZE" in os.environ
    if (
        not is_distributed
        and torch.cuda.is_available()
        and torch.cuda.device_count() > 1
    ):
        print("WARNING: Multiple GPUs available but not running in distributed mode.")
        print(
            "Use `torchrun --standalone --nnodes=1 --nproc_per_node=NUM_GPUS your_script_name.py [args]`"
        )

    main()
