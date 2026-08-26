#!/bin/bash
# Launch one SEVIR-LR arm (plain | uot | uot_probe).
#
#   ./run_sevirlr.sh uot   0,1,2 29701     # 3-GPU DDP
#   ./run_sevirlr.sh plain 0,1,2 29701     # afterwards, same 3 cards
#
# GPU is a comma-separated CUDA_VISIBLE_DEVICES list; nproc_per_node is
# derived from it. Both arms MUST use the same GPU COUNT: DistributedSampler
# partitions the training set by world_size, so an unequal world_size between
# the two arms would give them different data orders and break the
# matched-seed pairing -- the whole point of running them as twins. The two
# arms share the three cards sequentially (UOT first), never in parallel.
#
# Data paths are passed explicitly because the runner derives its defaults
# from dataset_name ("sevir"), which would point at the unrelated 49-frame
# SEVIR tree rather than the SEVIR-LR one.
set -u

ARM=$1
GPU=$2
PORT=$3
NPROC=$(( $(echo "$GPU" | tr -cd ',' | wc -c) + 1 ))

PROJECT_DIR=${PROJECT_ROOT}
PY=${CONDA_ROOT}/envs/torch/bin/torchrun
LATENT=${DATA_ROOT}/datasets/sevir_lr/data/sevir_latent_vae
RAW=${DATA_ROOT}/datasets/sevir_lr/data/sevir_full
CONFIG=experiments/sevir/runner/flowcast/flowcast_config_sevirlr_${ARM}.yaml

cd "$PROJECT_DIR" || exit 1
mkdir -p logs artifacts/sevir_lr/flowcast

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
