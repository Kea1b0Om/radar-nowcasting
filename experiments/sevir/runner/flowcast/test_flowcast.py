"""
This script evaluates a pre-trained FlowCast model on standardized nowcasting datasets.

It loads a trained model and its configuration, then iterates through the test set
to generate probabilistic forecasts. For each input sequence, it performs the
following steps:
1. Encodes the input radar frames into a latent space using a pre-trained autoencoder.
2. Generates multiple forecast samples with chunked autoregressive Euler rollout.
3. Decodes the latent predictions back into pixel space using the autoencoder.
4. Accumulates the predictions and ground truth to calculate nowcasting metrics.
5. Saves animations of sample forecasts and plots of the final metrics.
"""

import gc
import sys
import os
import time
import wandb
try:
    import namegenerator
except Exception:  # optional: only used to make a random run name
    namegenerator = None
import datetime

from omegaconf import OmegaConf

sys.path.append(os.getcwd())
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch.utils.data import DataLoader, Subset
try:
    from experiments.sevir.display.cartopy import make_animation
except Exception as _anim_exc:  # cartopy optional: only used for eval animations
    make_animation = None
    print(f"[warn] make_animation unavailable ({_anim_exc}); eval animations disabled.")
import random
from tqdm import tqdm
from common.models.flowcast.rf_stdit import (
    FlowCastSTDiTWrapper,
    autoregressive_sample,
)

from experiments.sevir.dataset.sevirfulldataset import (
    DynamicSequentialSevirDataset,
    dynamic_sequential_collate,
    post_process_samples,
)
from common.metrics.metrics_streaming_probabilistic import (
    MetricsAccumulator,
)
from common.metrics.crft_evaluation import Evaluation as CRFTEvaluation
from common.utils.utils import calculate_metrics
import argparse


parser = argparse.ArgumentParser(description="Script for testing FlowCast model.")

parser.add_argument(
    "--artifacts_folder",
    type=str,
    default=None,
    help="Artifacts folder to load model from",
)
parser.add_argument(
    "--config",
    type=str,
    default="experiments/sevir/runner/flowcast/flowcast_config.yaml",
    help="Path to the configuration file.",
)
parser.add_argument(
    "--test_data_percentage",
    type=float,
    default=1.0,
    help="Percentage of the test data to use (0.0 to 1.0).",
)
parser.add_argument(
    "--test_file",
    type=str,
    default=None,
)
parser.add_argument(
    "--test_meta",
    type=str,
    default=None,
)
parser.add_argument(
    "--crft_eval",
    action="store_true",
    help=(
        "Additionally score predictions with CRFT's own evaluator "
        "(common/metrics/crft_evaluation.py, vendored byte-identical from "
        "RuntimeWarning/CRFT). The published CIKM baseline tables we compare "
        "against were produced by that code, so running it on the same arrays "
        "turns 'equivalent by inspection' into 'equal by measurement'. "
        "Does not affect the FlowCast metrics, which are always reported."
    ),
)
args = parser.parse_args()
if not (0.0 <= args.test_data_percentage <= 1.0):
    raise ValueError("test_data_percentage must be between 0.0 and 1.0")
config = OmegaConf.load(args.config)

DEBUG_MODE = config.run_params.debug_mode
ENABLE_WANDB = config.run_params.enable_wandb
RUN_STRING = config.run_params.run_string
DATASET_NAME = OmegaConf.select(config, "data_params.dataset_name", default="sevir")
DATA_KEY = OmegaConf.select(config, "data_params.data_key", default="vil")
RAW_SEQ_LEN = OmegaConf.select(config, "data_params.raw_seq_len", default=49)
STRIDE = OmegaConf.select(config, "data_params.stride", default=12)
PIXEL_SCALE = OmegaConf.select(config, "evaluation_params.pixel_scale", default=255.0)

BATCH_SIZE = config.test_params.micro_batch_size
NUM_WORKERS = config.test_params.num_workers
PROBABILISTIC_SAMPLES = config.test_params.probabilistic_samples
BATCH_SIZE_AUTOENCODER = config.test_params.batch_size_autoencoder
CARTOPY_FEATURES = config.test_params.cartopy_features
INPUT_LENGTH = OmegaConf.select(
    config, "data_params.input_length", default=config.data_params.lag_time
)
OUTPUT_LENGTH = OmegaConf.select(
    config, "data_params.output_length", default=config.data_params.lead_time
)
TIME_SPACING = config.data_params.time_spacing
NUM_TRAIN_TIMESTEPS = config.rflow_params.num_train_timesteps
EULER_STEPS = OmegaConf.select(
    config, "sampling_params.euler_steps", default=config.test_params.euler_steps
)

PRELOAD_AE_MODEL = config.autoencoder_params.autoencoder_checkpoint
NORMALIZED_AUTOENCODER = config.autoencoder_params.normalized_autoencoder
LATENT_CHANNELS = config.autoencoder_params.latent_channels
NORM_NUM_GROUPS = config.autoencoder_params.norm_num_groups
LAYERS_PER_BLOCK = config.autoencoder_params.layers_per_block
ACT_FN = config.autoencoder_params.act_fn
BLOCK_OUT_CHANNELS = config.autoencoder_params.block_out_channels
DOWN_BLOCK_TYPES = config.autoencoder_params.down_block_types
UP_BLOCK_TYPES = config.autoencoder_params.up_block_types


RUN_ID = (
    datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    + "_"
    + RUN_STRING
    + "_"
    + (namegenerator.gen() if namegenerator is not None else os.urandom(3).hex())
)
ARTIFACTS_FOLDER = args.artifacts_folder
if ARTIFACTS_FOLDER is None:
    ARTIFACTS_FOLDER = f"saved_models/{DATASET_NAME}/flowcast"

DEBUG_PRINT_PREFIX = "[DEBUG] " if DEBUG_MODE else ""
DEFAULT_RAW_DIR = f"datasets/{DATASET_NAME}/data/{DATASET_NAME}_full"
TEST_FILE = args.test_file or f"{DEFAULT_RAW_DIR}/nowcast_testing_full.h5"
TEST_META = args.test_meta or f"{DEFAULT_RAW_DIR}/nowcast_testing_full_META.csv"
THRESHOLDS = np.array(
    OmegaConf.select(
        config,
        "evaluation_params.thresholds",
        default=[16, 74, 133, 160, 181, 219],
    ),
    dtype=np.float32,
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
if OmegaConf.select(config, "data_params.lag_time", default=INPUT_LENGTH) != INPUT_LENGTH:
    raise ValueError("data_params.lag_time must match data_params.input_length.")
if OmegaConf.select(config, "data_params.lead_time", default=OUTPUT_LENGTH) != OUTPUT_LENGTH:
    raise ValueError("data_params.lead_time must match data_params.output_length.")
if STDIT_DEPTH % 2 != 0:
    raise ValueError("stdit.depth must be even.")

print(f"{DEBUG_PRINT_PREFIX}Debug Mode: {DEBUG_MODE}")
print(f"{DEBUG_PRINT_PREFIX}Testing File: {TEST_FILE}")
print(f"{DEBUG_PRINT_PREFIX}Testing Meta: {TEST_META}")
print(f"{DEBUG_PRINT_PREFIX}Normalized Autoencoder: {NORMALIZED_AUTOENCODER}")
print(f"{DEBUG_PRINT_PREFIX}Batch Size: {BATCH_SIZE}")
print(f"{DEBUG_PRINT_PREFIX}Euler Steps: {EULER_STEPS}")
print(f"{DEBUG_PRINT_PREFIX}Number of Workers: {NUM_WORKERS}")
print(f"{DEBUG_PRINT_PREFIX}Input Length: {INPUT_LENGTH}")
print(f"{DEBUG_PRINT_PREFIX}Output Length: {OUTPUT_LENGTH}")
print(f"{DEBUG_PRINT_PREFIX}Time Spacing: {TIME_SPACING}")
print(f"{DEBUG_PRINT_PREFIX}Raw Seq Len: {RAW_SEQ_LEN}")
print(f"{DEBUG_PRINT_PREFIX}Stride: {STRIDE}")
print(f"{DEBUG_PRINT_PREFIX}Data Key: {DATA_KEY}")
print(f"{DEBUG_PRINT_PREFIX}Dataset Name: {DATASET_NAME}")
print(f"{DEBUG_PRINT_PREFIX}Pixel Scale: {PIXEL_SCALE}")
print(f"{DEBUG_PRINT_PREFIX}Thresholds: {THRESHOLDS}")
print(f"{DEBUG_PRINT_PREFIX}Probabilistic Samples: {PROBABILISTIC_SAMPLES}")
print(f"{DEBUG_PRINT_PREFIX}Preload AE Model: {PRELOAD_AE_MODEL}")
print(f"{DEBUG_PRINT_PREFIX}Latent Channels: {LATENT_CHANNELS}")
print(f"{DEBUG_PRINT_PREFIX}Norm Num Groups: {NORM_NUM_GROUPS}")
print(f"{DEBUG_PRINT_PREFIX}Layers Per Block: {LAYERS_PER_BLOCK}")
print(f"{DEBUG_PRINT_PREFIX}Activation Function: {ACT_FN}")
print(f"{DEBUG_PRINT_PREFIX}Block Out Channels: {BLOCK_OUT_CHANNELS}")
print(f"{DEBUG_PRINT_PREFIX}Down Block Types: {DOWN_BLOCK_TYPES}")
print(f"{DEBUG_PRINT_PREFIX}Up Block Types: {UP_BLOCK_TYPES}")
print(f"--------- {DEBUG_PRINT_PREFIX}STDiT Config ---------")
print(f"{DEBUG_PRINT_PREFIX}Hidden Size: {STDIT_HIDDEN_SIZE}")
print(f"{DEBUG_PRINT_PREFIX}Depth: {STDIT_DEPTH}")
print(f"{DEBUG_PRINT_PREFIX}Num Heads: {STDIT_NUM_HEADS}")
print(f"{DEBUG_PRINT_PREFIX}Patch Size: {STDIT_PATCH_SIZE}")
print(f"{DEBUG_PRINT_PREFIX}MLP Ratio: {STDIT_MLP_RATIO}")
print(f"{DEBUG_PRINT_PREFIX}Drop Path: {STDIT_DROP_PATH}")
print(f"{DEBUG_PRINT_PREFIX}QK Norm: {STDIT_QK_NORM}")
print(f"{DEBUG_PRINT_PREFIX}Batch Size Autoencoder: {BATCH_SIZE_AUTOENCODER}")

PLOTS_FOLDER = ARTIFACTS_FOLDER + "/plots"
os.makedirs(PLOTS_FOLDER, exist_ok=True)
ANIMATIONS_FOLDER = PLOTS_FOLDER + "/animations"
os.makedirs(ANIMATIONS_FOLDER, exist_ok=True)
METRICS_FOLDER = PLOTS_FOLDER + "/metrics"
os.makedirs(METRICS_FOLDER, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"{DEBUG_PRINT_PREFIX}Using device: {device}")
if device.type == "cpu":
    print(DEBUG_PRINT_PREFIX + "CPU is used")
else:
    print(f"{DEBUG_PRINT_PREFIX}Number of GPUs available: {torch.cuda.device_count()}")
    if torch.cuda.device_count() > 1:
        print(f"{DEBUG_PRINT_PREFIX}Using {torch.cuda.device_count()} GPUs!")

random.seed(42)
torch.manual_seed(42)
np.random.seed(42)

MODEL_SAVE_DIR = ARTIFACTS_FOLDER + "/models"
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)
MODEL_SAVE_PATH = os.path.join(MODEL_SAVE_DIR, "early_stopping_model" + ".pt")

def safe_encode(model, x):
    """
    Safely encode using the model, handling the DataParallel wrapper.
    """
    if isinstance(model, torch.nn.DataParallel):
        return model.module.encode(x)
    return model.encode(x)


def safe_decode(model, x):
    """
    Safely decode using the model, handling the DataParallel wrapper.
    """
    if isinstance(model, torch.nn.DataParallel):
        return model.module.decode(x)
    return model.decode(x)


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


def feed_crft_evaluator(crft_eval, y_true_array, y_pred_array, pixel_scale):
    """Score one chunk with CRFT's own evaluator.

    Our arrays are (B, T, H, W) / (B, S, T, H, W) on the dBZ metric scale.
    CRFT's Evaluation.update wants (seq_len, batch, H, W) in [0, 1] and applies
    value_scale itself, so we collapse the ensemble the same way FlowCast's
    "from mean" metrics do, rescale, and move the time axis to the front.
    """
    pred = np.mean(y_pred_array.astype(np.float32), axis=1) / pixel_scale
    gt = y_true_array.astype(np.float32) / pixel_scale
    crft_eval.update(
        np.ascontiguousarray(gt.transpose(1, 0, 2, 3)),
        np.ascontiguousarray(pred.transpose(1, 0, 2, 3)),
    )


def report_crft_metrics(crft_eval, thresholds):
    """Print CRFT-evaluator results in the same shape as the FlowCast block."""
    pod, far, csi, hss, gss, mse, mae, precision, f1, bias, ssim, accuracy, psnr = (
        crft_eval.calculate_stat()
    )
    csi_per_thresh = {float(t): float(csi[:, i].mean()) for i, t in enumerate(thresholds)}
    hss_per_thresh = {float(t): float(hss[:, i].mean()) for i, t in enumerate(thresholds)}
    print("--- CRFT evaluator (vendored byte-identical from RuntimeWarning/CRFT) ---")
    print(f"[CRFT] CSI-M : {float(np.mean([csi[:, i].mean() for i in range(len(thresholds))]))}")
    print(f"[CRFT] HSS-M : {float(np.mean([hss[:, i].mean() for i in range(len(thresholds))]))}")
    print(f"[CRFT] POD-M : {float(np.mean([pod[:, i].mean() for i in range(len(thresholds))]))}")
    print(f"[CRFT] FAR-M : {float(np.mean([far[:, i].mean() for i in range(len(thresholds))]))}")
    print(f"[CRFT] CSI per threshold: {csi_per_thresh}")
    print(f"[CRFT] HSS per threshold: {hss_per_thresh}")
    print(f"[CRFT] CSI-M by lead time: {[float(csi[t].mean()) for t in range(csi.shape[0])]}")
    print(f"[CRFT] SSIM: {float(ssim.mean())}  PSNR: {float(psnr.mean())}")
    # CRFT sums MSE/MAE over the spatial axes instead of averaging, so these are
    # NOT comparable to the FlowCast per-pixel numbers above or across papers.
    print(f"[CRFT] MSE (spatial-sum convention): {float(mse.mean())}")
    print(f"[CRFT] MAE (spatial-sum convention): {float(mae.mean())}")


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


if ENABLE_WANDB:
    wandb.init(
        project=f"{DATASET_NAME}-nowcasting-testing-rf-stdit",
        name=RUN_ID,
        config={
            "batch_size": BATCH_SIZE,
            "num_workers": NUM_WORKERS,
            "input_length": INPUT_LENGTH,
            "output_length": OUTPUT_LENGTH,
            "time_spacing": TIME_SPACING,
            "raw_seq_len": RAW_SEQ_LEN,
            "stride": STRIDE,
            "data_key": DATA_KEY,
            "dataset": DATASET_NAME,
            "pixel_scale": PIXEL_SCALE,
            "thresholds": THRESHOLDS.tolist(),
            "probabilistic_samples": PROBABILISTIC_SAMPLES,
            "num_train_timesteps": NUM_TRAIN_TIMESTEPS,
            "euler_steps": EULER_STEPS,
            "model": "flowcast-rf-stdit",
            "model_save_path": MODEL_SAVE_PATH,
        },
    )

PRELOAD_MODEL = MODEL_SAVE_PATH if os.path.exists(MODEL_SAVE_PATH) else None
if PRELOAD_MODEL is None:
    raise FileNotFoundError(f"Model not found at {MODEL_SAVE_PATH}")
else:
    print(f"{DEBUG_PRINT_PREFIX}Model found at {MODEL_SAVE_PATH}")

    full_test_dataset = DynamicSequentialSevirDataset(
        meta_csv=TEST_META,
        data_file=TEST_FILE,
        data_type=DATA_KEY,
        raw_seq_len=RAW_SEQ_LEN,
        lag_time=INPUT_LENGTH,
        lead_time=OUTPUT_LENGTH,
        time_spacing=TIME_SPACING,
        stride=STRIDE,
        channel_last=False,
        debug_mode=DEBUG_MODE,
    )

    if args.test_data_percentage < 1.0:
        num_samples = int(len(full_test_dataset) * args.test_data_percentage)
        test_dataset = Subset(full_test_dataset, range(num_samples))
    else:
        test_dataset = full_test_dataset

    test_loader = DataLoader(
        test_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=dynamic_sequential_collate,
        num_workers=NUM_WORKERS if not DEBUG_MODE else 0,
        pin_memory=True if not DEBUG_MODE else False,
    )

    if not os.path.exists(PRELOAD_AE_MODEL):
        raise FileNotFoundError(f"Model not found at {PRELOAD_AE_MODEL}")

    from diffusers.models.autoencoders import AutoencoderKL

    ae_model = AutoencoderKL(
        in_channels=1,
        out_channels=1,
        down_block_types=DOWN_BLOCK_TYPES,
        up_block_types=UP_BLOCK_TYPES,
        block_out_channels=BLOCK_OUT_CHANNELS,
        act_fn=ACT_FN,
        latent_channels=LATENT_CHANNELS,
        norm_num_groups=NORM_NUM_GROUPS,
        layers_per_block=LAYERS_PER_BLOCK,
    )

    checkpoint = torch.load(PRELOAD_AE_MODEL, map_location=device)
    # Remove 'module.' prefix if it exists (in case the AE was trained with DDP)
    new_state_dict = {}
    for k, v in checkpoint["model_state_dict"].items():
        new_key = k.replace("module.", "") if k.startswith("module.") else k
        new_state_dict[new_key] = v
    ae_model.load_state_dict(new_state_dict)
    ae_model = ae_model.to(device)
    if torch.cuda.device_count() > 1:
        ae_model = torch.nn.DataParallel(ae_model)
    ae_model.eval()

    input_shape = None
    output_shape = None
    for batch in test_loader:
        inputs, outputs, metadata = batch
        inputs_decoded = inputs[:, :, 0, :, :].to(device)
        encoded_obj = safe_encode(ae_model, inputs_decoded)
        inputs_decoded = encoded_obj.latent_dist.mode()

        print(f"Inputs shape: {inputs.shape}")
        print(f"Inputs Decoded shape: {inputs_decoded.shape}")
        print(f"Outputs shape: {outputs.shape}")
        input_shape = inputs.shape
        inputs_decoded_shape = inputs_decoded.shape
        output_shape = outputs.shape
        break
    checkpoint = torch.load(MODEL_SAVE_PATH, weights_only=False, map_location="cpu")
    checkpoint_model_state_dict = checkpoint["model_state_dict"]
    checkpoint_mean = checkpoint.get("mean", 0.0)
    checkpoint_std = checkpoint.get("std", 1.0)

    loaded_model = FlowCastSTDiTWrapper(
        latent_channels=inputs_decoded_shape[1],
        hidden_size=STDIT_HIDDEN_SIZE,
        depth=STDIT_DEPTH,
        num_heads=STDIT_NUM_HEADS,
        patch_size=STDIT_PATCH_SIZE,
        mlp_ratio=STDIT_MLP_RATIO,
        drop_path=STDIT_DROP_PATH,
        qk_norm=STDIT_QK_NORM,
        mean=checkpoint_mean,
        std=checkpoint_std,
    )
    loaded_model.load_state_dict(checkpoint_model_state_dict)
    loaded_model = loaded_model.to(device)
    if torch.cuda.device_count() > 1:
        loaded_model = torch.nn.DataParallel(loaded_model)
    loaded_model.eval()

    metrics_accumulators = [
        MetricsAccumulator(
            lead_time=lead_time,
            thresholds=THRESHOLDS,
            pool_size=16,
            compute_mse=True,
            compute_threshold=True,
            compute_crps=True,
            compute_fss=True,
            fss_scales=[1, 4, 16],
            device=device,
        )
        for lead_time in range(OUTPUT_LENGTH)
    ]

    crft_eval = (
        CRFTEvaluation(
            seq_len=OUTPUT_LENGTH,
            value_scale=PIXEL_SCALE,
            thresholds=list(THRESHOLDS),
        )
        if args.crft_eval
        else None
    )
    if crft_eval is not None:
        print(
            f"{DEBUG_PRINT_PREFIX}CRFT evaluator enabled "
            f"(value_scale={PIXEL_SCALE}, thresholds={list(THRESHOLDS)})"
        )

    test_bar = tqdm(test_loader, desc="Testing Model")
    count = 0
    y_pred = []
    y_true = []
    total_prediction_time = 0.0
    total_samples_processed = 0
    for idx, batch in enumerate(test_bar):
        x_cond, x_true, metadata = batch
        current_model = (
            loaded_model.module
            if isinstance(loaded_model, torch.nn.DataParallel)
            else loaded_model
        )

        B, C, T_in, H, W = x_cond.shape
        x_cond = x_cond.permute(0, 2, 1, 3, 4).reshape(B * T_in, C, H, W)

        with torch.no_grad():
            x_cond = x_cond.to(device)
            if NORMALIZED_AUTOENCODER:
                x_cond = x_cond / 255.0
            encoded_obj = safe_encode(ae_model, x_cond)
            x_cond = encoded_obj.latent_dist.mode()

        latent_channels, latent_H, latent_W = (
            x_cond.shape[1],
            x_cond.shape[2],
            x_cond.shape[3],
        )
        x_cond = x_cond.reshape(B, T_in, latent_channels, latent_H, latent_W)
        x_cond = x_cond.permute(0, 1, 3, 4, 2).contiguous()
        x_cond = current_model.normalize(x_cond)

        x_true = x_true.squeeze(1)
        if DATASET_NAME == "cikm":
            x_true = x_true[:, :, 13:-14, 13:-14]
        x_true = raw_to_eval_scale(x_true, DATASET_NAME, PIXEL_SCALE)
        sample_predictions = []

        start_time = time.time()
        for sample_idx in range(PROBABILISTIC_SAMPLES):
            seed = idx * PROBABILISTIC_SAMPLES + sample_idx
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)

            with torch.no_grad():
                x_pred_sample = autoregressive_sample(
                    model=current_model,
                    initial_cond=x_cond,
                    input_length=INPUT_LENGTH,
                    output_length=OUTPUT_LENGTH,
                    num_train_timesteps=NUM_TRAIN_TIMESTEPS,
                    euler_steps=EULER_STEPS,
                )
                x_pred_sample = current_model.denormalize(x_pred_sample)
            sample_predictions.append(x_pred_sample.unsqueeze(1))

        x_pred = torch.cat(sample_predictions, dim=1)

        end_time = time.time()
        total_prediction_time += end_time - start_time
        total_samples_processed += B

        x_true_np = x_true.cpu().numpy()
        B, S, T, H_latent, W_latent, C_latent = x_pred.shape
        x_pred = x_pred.reshape(B * S * T, H_latent, W_latent, C_latent)
        x_pred = x_pred.permute(0, 3, 1, 2).contiguous()

        with torch.no_grad():
            if BATCH_SIZE_AUTOENCODER is not None:
                decoded_chunks = []
                for i in range(0, x_pred.shape[0], BATCH_SIZE_AUTOENCODER):
                    chunk = x_pred[i : i + BATCH_SIZE_AUTOENCODER]
                    decoded_chunk_obj = safe_decode(ae_model, chunk)
                    decoded_chunks.append(decoded_chunk_obj.sample)
                x_pred = torch.cat(decoded_chunks, dim=0)
            else:
                decoded_obj_fallback = safe_decode(ae_model, x_pred)
                x_pred = decoded_obj_fallback.sample

        if torch.isnan(x_pred).any():
            print(
                f"{DEBUG_PRINT_PREFIX}WARNING: NaNs detected in inference batch! If you are running this script with FP16, try running with FP32."
            )

        x_pred = decoded_to_eval_scale(
            x_pred,
            DATASET_NAME,
            PIXEL_SCALE,
            NORMALIZED_AUTOENCODER,
        )
        if DATASET_NAME == "cikm":
            x_pred = x_pred[:, :, 13:-14, 13:-14]
        new_channels, new_H, new_W = x_pred.shape[1], x_pred.shape[2], x_pred.shape[3]

        x_pred = x_pred.reshape(B, S, T, new_channels, new_H, new_W)
        x_pred = x_pred.permute(0, 1, 2, 4, 5, 3)

        if x_pred.shape[-1] == 1:
            x_pred = x_pred.squeeze(-1)

        x_pred = x_pred.cpu().detach().numpy().astype(np.float16)

        y_pred.append(x_pred)
        y_true.append(x_true_np)

        flush_interval = max(1, int((400 / BATCH_SIZE) / PROBABILISTIC_SAMPLES))
        if idx % flush_interval == 0 and idx > 0:
            y_pred_array = np.concatenate(y_pred, axis=0)
            y_pred_array = post_process_samples(
                y_pred_array, clamp_min=0.0, clamp_max=PIXEL_SCALE
            )
            y_true_array = np.concatenate(y_true, axis=0)

            for lead_time, metrics_accumulator in enumerate(metrics_accumulators):
                metrics_accumulator.update(y_true_array, y_pred_array)
            if crft_eval is not None:
                feed_crft_evaluator(
                    crft_eval, y_true_array, y_pred_array, PIXEL_SCALE
                )

            batch_size_y_true = y_pred_array.shape[0]
            y_pred = []
            y_true = []

            results = calculate_metrics(
                num_lead_times=OUTPUT_LENGTH,
                metrics_accumulators=metrics_accumulators,
                thresholds=THRESHOLDS,
            )

            if ENABLE_WANDB:
                global_step = idx * batch_size_y_true
                wandb.log(
                    {
                        "partial_mse": results["mse_from_mean_mean"],
                        "partial_crps": results["crps_mean"],
                        "partial_csi_m": results["csi_from_mean_m"],
                        "partial_csi_pool_m": results["csi_pool_from_mean_m"],
                        "partial_hss_m": results["hss_from_mean_m"],
                        "partial_far_m": results["far_from_mean_m"],
                        "partial_pod_m": results["pod_from_mean_m"],
                        "partial_fss_m": results["fss_m_from_mean"],
                    },
                    step=global_step,
                )

        if idx == 0 and make_animation is not None:
            sample_pred = x_pred[0]
            sample_pred = post_process_samples(
                sample_pred, clamp_min=0.0, clamp_max=PIXEL_SCALE
            )
            for i in range(sample_pred.shape[0]):
                sample_pred_plot = sample_pred[i]
                fig1 = plt.figure()
                anim = make_animation(
                    sample_pred_plot,
                    metadata[0],
                    title="Outputs",
                    fig=fig1,
                    cartopy_features=CARTOPY_FEATURES,
                )
                anim.save(
                    os.path.join(
                        PLOTS_FOLDER, "animations", f"output_test_animation{i}.gif"
                    ),
                    writer="imagemagick",
                    fps=6,
                )
                plt.close(fig1)

            fig2 = plt.figure()
            anim = make_animation(
                x_true_np[0],
                metadata[0],
                title="Target",
                fig=fig2,
                cartopy_features=CARTOPY_FEATURES,
            )
            anim.save(
                os.path.join(PLOTS_FOLDER, "animations", "target_test_animation.gif"),
                writer="imagemagick",
                fps=6,
            )
            plt.close(fig2)

        count += 1
        if DEBUG_MODE and count > 10:
            print(f"{DEBUG_PRINT_PREFIX}Breaking early due to DEBUG_MODE")
            break

    if len(y_pred) > 0:
        y_pred_array = np.concatenate(y_pred, axis=0)
        y_pred_array = post_process_samples(
            y_pred_array, clamp_min=0.0, clamp_max=PIXEL_SCALE
        )
        y_true_array = np.concatenate(y_true, axis=0)
        for lead_time, metrics_accumulator in enumerate(metrics_accumulators):
            metrics_accumulator.update(y_true_array, y_pred_array)
        if crft_eval is not None:
            feed_crft_evaluator(crft_eval, y_true_array, y_pred_array, PIXEL_SCALE)

    del y_pred
    del y_true
    gc.collect()

    results = calculate_metrics(
        num_lead_times=OUTPUT_LENGTH,
        metrics_accumulators=metrics_accumulators,
        thresholds=THRESHOLDS,
    )

    crps_mean = results["crps_mean"]

    if total_samples_processed > 0:
        average_time_per_prediction = total_prediction_time / total_samples_processed
        print(
            f"Average time per ensemble prediction: {average_time_per_prediction:.4f} seconds"
        )

    print(f"CRPS: {crps_mean}")
    # Scaled CRPS
    print(f"CRPS (scaled by maximum dataset value): {crps_mean / PIXEL_SCALE}")

    mse_from_mean_mean = results["mse_from_mean_mean"]
    csi_from_mean_m = results["csi_from_mean_m"]
    csi_pool_from_mean_m = results["csi_pool_from_mean_m"]
    hss_from_mean_m = results["hss_from_mean_m"]
    far_from_mean_m = results["far_from_mean_m"]
    pod_from_mean_m = results["pod_from_mean_m"]
    csi_from_mean_mean_dict = results["csi_from_mean_mean"]
    far_from_mean_mean_dict = results["far_from_mean_mean"]
    hss_from_mean_mean_dict = results["hss_from_mean_mean"]
    pod_from_mean_mean_dict = results["pod_from_mean_mean"]
    csi_pool_from_mean_mean_dict = results["csi_pool_from_mean_mean"]

    print("--- Metrics from Ensemble Mean ---")
    print(f"Mean MSE : {mse_from_mean_mean}")
    print(f"CSI-M : {csi_from_mean_m}")
    print(f"CSI (16-pooled)-M : {csi_pool_from_mean_m}")
    print(f"HSS-M : {hss_from_mean_m}")
    print(f"FAR-M : {far_from_mean_m}")
    print(f"POD-M : {pod_from_mean_m}")
    print("CSI per threshold:", csi_from_mean_mean_dict)
    print("FAR per threshold:", far_from_mean_mean_dict)
    print("HSS per threshold:", hss_from_mean_mean_dict)
    print("POD per threshold:", pod_from_mean_mean_dict)
    print(f"CSI (16-pooled) mean per threshold: {csi_pool_from_mean_mean_dict}")
    csi_m_from_mean_lead_time = results["csi_m_from_mean_lead_time"]
    csi_last_thresh_from_mean_lead_time = results["csi_last_thresh_from_mean_lead_time"]
    csi_pool_m_from_mean_lead_time = results["csi_pool_m_from_mean_lead_time"]
    csi_pool_last_thresh_from_mean_lead_time = results[
        "csi_pool_last_thresh_from_mean_lead_time"
    ]
    hss_m_from_mean_lead_time = results["hss_m_from_mean_lead_time"]
    far_m_from_mean_lead_time = results["far_m_from_mean_lead_time"]
    pod_m_from_mean_lead_time = results["pod_m_from_mean_lead_time"]
    print("--- Lead Time Metrics ---")
    print(f"CSI-M by lead time: {csi_m_from_mean_lead_time}")
    print(f"CSI-M (219) by lead time: {csi_last_thresh_from_mean_lead_time}")
    print(f"CSI (16-pooled)-M by lead time: {csi_pool_m_from_mean_lead_time}")
    print(
        f"CSI (16-pooled) (219) by lead time: {csi_pool_last_thresh_from_mean_lead_time}"
    )
    print(f"HSS-M by lead time: {hss_m_from_mean_lead_time}")
    print(f"FAR-M by lead time: {far_m_from_mean_lead_time}")
    print(f"POD-M by lead time: {pod_m_from_mean_lead_time}")

    if crft_eval is not None:
        report_crft_metrics(crft_eval, THRESHOLDS)

    print(DEBUG_PRINT_PREFIX + "Finished testing the model")
