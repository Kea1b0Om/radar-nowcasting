#!/bin/bash
# Pre-registered lambda dose-response for calibrated few-step distillation.
#
# Four arms, one per GPU, byte-identical except --reward-weight:
#
#   lam0.0000  GPU0  pure endpoint distillation.  The control that separates
#                    "what few-step costs" from "what the reward buys".
#   lam0.0028  GPU1  ~10% score share of the gradient (measured, see below)
#   lam0.0060  GPU2  ~20% share -- top of the calibrated band
#   lam0.0200  GPU3  ~39% share -- deliberately over the band, so that
#                    "too much reward goes off-manifold" becomes a measured
#                    curve in this run instead of an assumption carried over
#                    from the k200c / band-gate arms
#
# The grid comes from stage0 (audit_outputs/distill/stage0_rw0.05): at
# lambda=0.05 the score term carried 66% of the gradient, and
# ||grad distill|| / ||grad score_raw|| has median 0.0233, so
# lambda(t) = t/(1-t) * 0.0233.  Calibrating an auxiliary term by gradient
# norm rather than loss magnitude is the UOT lesson: that arm sat at 31.7%
# of the loss while carrying 213% of the gradient, and under grad clipping
# an over-weighted auxiliary term steals the main term's effective lr.
#
# Read-out is NOT taken from these logs: they are subsampled-frame training
# diagnostics.  The verdict runs on the frozen half [1000, 2000) through the
# evaluation pipeline, against the pre-registered conjunctive criteria.
#
# usage: ./run_distill_sweep.sh [ITERS]
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch

ITERS=${1:-1000}
mkdir -p logs audit_outputs/distill

launch () {
  local gpu=$1 lam=$2 tag=$3
  rm -rf audit_outputs/distill/${tag}
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/train_distill_reward.py \
    --config experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml \
    --checkpoint artifacts/cikm/flowcast/teacher_v4.pt \
    --expect-teacher-digest e654bbfccf2d \
    --train-file datasets/cikm/data/cikm_full/nowcast_validation_full.h5 \
    --train-meta datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv \
    --output-dir audit_outputs/distill/${tag} \
    --condition-start 0 --condition-end 1000 \
    --iters ${ITERS} --snapshot-every 200 --log-every 25 \
    --student-steps 4 --group-size 8 --grad-last-k 1 \
    --reward-weight ${lam} --reward-frames 4 --score-view ste \
    --lr 1e-5 --max-grad-norm 1.0 --precision bf16 --seed 42 \
    > logs/distill_${tag}.log 2>&1
  echo "$? ${tag}" >> DISTILL_SWEEP_EXITS
}

rm -f DISTILL_SWEEP_DONE DISTILL_SWEEP_EXITS

launch 0 0.0     lam0.0000 &
launch 1 0.0028  lam0.0028 &
launch 2 0.0060  lam0.0060 &
launch 3 0.02    lam0.0200 &
wait

touch DISTILL_SWEEP_DONE
