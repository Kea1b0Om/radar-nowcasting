#!/bin/bash
# Launch one Shanghai arm (plain | uot | uot_probe).
#
#   ./run_shanghai.sh uot       0,1,2 29721   # 3-GPU DDP, after probe
#   ./run_shanghai.sh plain     0,1,2 29721   # afterwards, same 3 cards
#   ./run_shanghai.sh uot_probe 0     29723   # 1-GPU throwaway calibration
#
# Same twin rules as run_sevirlr.sh: both real arms MUST use the same GPU
# count (DistributedSampler partitions by world_size), run sequentially on
# the same cards. The probe is exempt -- it never produces a comparable model.
#
# Prerequisites (in order):
#   1. Shanghai AE trained (run_shanghai_ae.sh) and copied to
#      saved_models/shanghai/autoencoder/models/early_stopping_model.pt
#   2. Latents extracted into $LATENT (generate_static_dataset.py)
#   3. Probe run -> weight calibrated in flowcast_config_shanghai_uot.yaml
set -u

ARM=$1
GPU=$2
PORT=$3
NPROC=$(( $(echo "$GPU" | tr -cd ',' | wc -c) + 1 ))

PROJECT_DIR=${PROJECT_ROOT}
PY=${CONDA_ROOT}/envs/torch/bin/torchrun
LATENT=${DATA_ROOT}/datasets/shanghai/data/shanghai_latent_vae
RAW=${DATA_ROOT}/datasets/shanghai/data/shanghai_full
CONFIG=experiments/shanghai/runner/flowcast/flowcast_config_shanghai_${ARM}.yaml

cd "$PROJECT_DIR" || exit 1
mkdir -p logs artifacts/shanghai/flowcast

CUDA_VISIBLE_DEVICES="$GPU" PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  "$PY" --nproc_per_node="$NPROC" --master_port="$PORT" \
  experiments/sevir/runner/flowcast/dist_train_flowcast.py \
  --config "$CONFIG" \
  --train_file "$LATENT/nowcast_training_full.h5" \
  --train_meta "$LATENT/nowcast_training_full_META.csv" \
  --val_file "$LATENT/nowcast_validation_full.h5" \
  --val_meta "$LATENT/nowcast_validation_full_META.csv" \
  --partial_evaluation_file "$RAW/nowcast_validation_full.h5" \
  --partial_evaluation_meta "$RAW/nowcast_validation_full_META.csv"
