#!/bin/bash
# Dose + reach calibration for the SOFT chaining transform.
#
# Two things must be read before any training arm is launched:
#   1. score_grad_share  -- softness changes the score's scale (a soft chain
#      lifts every sub-threshold pixel off the floor), so it moves lambda
#      implicitly, exactly as the tail weights did.  Re-solve, do not assume.
#   2. the t35/t40 component values -- with the hard chain these were
#      0.0099-0.111; if soft chaining works they must rise, because pixels
#      that were pinned at the threshold now contribute.
#
# Softness is in dBZ and sets how far below the threshold the score can see
# (gradient = sigmoid(-d/s) at distance d below): s=1 reaches ~2 dBZ, s=2
# ~5 dBZ, s=5 ~15 dBZ.  Larger s reaches further but blends the tail term
# back into the bulk, which is the whole tension being swept here.
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch
GPU=${1:-0}
mkdir -p logs audit_outputs/distill
run () {
  local tag=$1; shift
  echo "########## ${tag} ##########"
  CUDA_VISIBLE_DEVICES=${GPU} python -u tools/train_distill_reward.py \
    --stage0 --stage0-batches 3 \
    --config experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml \
    --checkpoint artifacts/cikm/flowcast/teacher_v4.pt \
    --expect-teacher-digest e654bbfccf2d \
    --train-file datasets/cikm/data/cikm_full/nowcast_validation_full.h5 \
    --train-meta datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv \
    --output-dir audit_outputs/distill/soft_${tag} \
    --condition-start 0 --condition-end 1000 \
    --student-steps 4 --group-size 8 --grad-last-k 1 \
    --reward-weight 0.05 --reward-frames 4 --score-view ste \
    --precision bf16 --seed 42 "$@" 2>&1 | \
    grep -E "score grad share|grad distill|grad lambda|VERDICT|identity arm|score_t35|score_t40|score_plain" | head -20
}
{
  run hard0
  run soft1 --chaining-softness 1.0
  run soft2 --chaining-softness 2.0
  run soft5 --chaining-softness 5.0
} > logs/distill_soft_stage0.log 2>&1
touch DISTILL_SOFT_STAGE0_DONE
cat logs/distill_soft_stage0.log
