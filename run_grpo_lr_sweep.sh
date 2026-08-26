#!/bin/bash
# Pre-registered final dose test for lane 1 (Flow-GRPO).
#
# The previous run used a learning rate far below the reference setting, so its
# result could not distinguish "method fails" from "step size too small".
# Batch scale was already aligned to the reference; the learning rate was the
# one knob held back, and this sweeps it.
#
# EVERYTHING except --lr and --iters is byte-identical to run_grpo_rl2.sh.
# Read-out is the pre-registered verdict() already coded in the pilot:
# Read-out uses the verdict() already coded in the pilot; thresholds are set
# there.  Fix them before running.
#
# Arms run concurrently on separate GPUs (all four were idle at launch).
# usage: ./run_grpo_lr_sweep.sh [ITERS]
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch

ITERS=${1:-60}

launch () {
  local gpu=$1 lr=$2 tag=$3
  rm -f GRPO_${tag}_DONE
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/train_grpo_pilot.py \
    --config experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml \
    --checkpoint artifacts/cikm/flowcast/teacher_v4.pt \
    --train-file datasets/cikm/data/cikm_full/nowcast_validation_full.h5 \
    --train-meta datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv \
    --output-dir audit_outputs/grpo_pilot/${tag} \
    --iters ${ITERS} --conditions-per-iter 16 --num-minibatches 4 --num-inner-epochs 1 \
    --condition-start 0 --condition-end 1000 \
    --group-size 16 --kappa 1.0 --lr ${lr} --clip-range 1e-3 \
    --transitions-per-update 2 --adv-mode global_std --log-every 5 \
    > logs/grpo_${tag}.log 2>&1
  echo "exit=$?" > GRPO_${tag}_DONE
}

launch 0 1e-5 rl_lr1e5 &
P1=$!
launch 1 1e-4 rl_lr1e4 &
P2=$!
wait $P1 $P2
echo "sweep finished" > GRPO_LR_SWEEP_DONE
