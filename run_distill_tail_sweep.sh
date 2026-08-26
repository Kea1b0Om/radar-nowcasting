#!/bin/bash
# Tail-weighted composite arms at MATCHED score-gradient share.
#
# The question is "does putting the gradient on the tail buy extreme
# fidelity", and the only way to ask it cleanly is to hold the amount of
# score gradient fixed and vary only its distribution across thresholds.
# Measured at stage0 (audit_outputs/distill/tail_*, GPU1):
#
#   weights            ||grad score_raw||   plain:t40 contribution
#   equal (1 1 1 1 1)        0.79242              8.8 : 1
#   tiltA (1 1 2 4 8)        0.44112              1.1 : 1   <- equalised
#   tiltB (.5 1 2 6 16)      0.33248              0.28: 1   <- tail-dominant
#
# so lambda is rescaled by the inverse ratio to keep lambda*||grad score||
# constant against the equal-weight arms already run:
#   tiltA @ share(lam=0.006) -> 0.006 * 0.79242/0.44112 = 0.0108
#   tiltB @ share(lam=0.006) -> 0.006 * 0.79242/0.33248 = 0.0143
#
# The equal-weight controls (lam0.0060, lam0.0200) are already trained, so
# these two arms complete a 2x2: {equal, tilted} x {gradient share held}.
# GPUs 2 and 3 only -- run_test_s8.sh wave 2 takes 0 and 1.
#
# usage: ./run_distill_tail_sweep.sh [ITERS]
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch

ITERS=${1:-1000}
mkdir -p logs audit_outputs/distill

launch () {
  local gpu=$1 lam=$2 tag=$3; shift 3
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
    --lr 1e-5 --max-grad-norm 1.0 --precision bf16 --seed 42 "$@" \
    > logs/distill_${tag}.log 2>&1
  echo "$? ${tag}" >> DISTILL_TAIL_SWEEP_EXITS
}

rm -f DISTILL_TAIL_SWEEP_DONE DISTILL_TAIL_SWEEP_EXITS

launch 2 0.0108 tiltA_lam0.0108 --tail-weights 1 1 2 4 8 &
launch 3 0.0143 tiltB_lam0.0143 --tail-weights 0.5 1 2 6 16 &
wait

touch DISTILL_TAIL_SWEEP_DONE
