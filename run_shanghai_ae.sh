#!/bin/bash
# Train the Shanghai AutoencoderKL.
#
#   ./run_shanghai_ae.sh 0,1,2 29711    # 3-GPU DDP
#   ./run_shanghai_ae.sh 2     29711    # single (shared-card) fallback
#
# GPU is a comma-separated CUDA_VISIBLE_DEVICES list; nproc is derived. The
# VAE has no twin-pairing constraint, so world_size is free to change --
# only the nowcast arms must match each other. Saves to
# artifacts/shanghai/autoencoder_kl/<RUN_ID>/models/early_stopping_model.pt
set -u

GPU=$1
PORT=$2
NPROC=$(( $(echo "$GPU" | tr -cd ',' | wc -c) + 1 ))

PROJECT_DIR=${PROJECT_ROOT}
PY=${CONDA_ROOT}/envs/torch/bin/torchrun
RAW=${DATA_ROOT}/datasets/shanghai/data/shanghai_full

cd "$PROJECT_DIR" || exit 1
mkdir -p logs artifacts/shanghai/autoencoder_kl

CUDA_VISIBLE_DEVICES="$GPU" PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  "$PY" --nproc_per_node="$NPROC" --master_port="$PORT" \
  experiments/sevir/autoencoder/dist_train_autoencoder_kl.py \
  --config experiments/shanghai/autoencoder/autoencoder_kl_config.yaml \
  --train_file "$RAW/nowcast_training_full.h5" \
  --train_meta "$RAW/nowcast_training_full_META.csv" \
  --val_file "$RAW/nowcast_validation_full.h5" \
  --val_meta "$RAW/nowcast_validation_full_META.csv"
