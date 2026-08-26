#!/bin/bash
# Re-calibrate the dose for a TAIL-WEIGHTED composite.
#
# Why this cannot reuse the previous lambda: ``twcrps_composite`` normalises
# the threshold weights to sum to 1, so tilting weight onto the small tail
# terms lowers the total score magnitude and changes the gradient scale.
# Re-weighting therefore moves lambda implicitly.  Reading score_grad_share
# again and re-solving for lambda is the same discipline that caught the
# original grid being 3x too hot -- it is not optional bookkeeping.
#
# Two candidate tilts, both run at the previous lambda so the share is
# directly comparable to the equal-weight measurement (0.66 at lambda=0.05):
#
#   tiltA  1 1 2 4 8    moderate; tail terms lifted about one order
#   tiltB  0.5 1 2 6 16 aggressive; approximately equalises the *contribution*
#                       of each threshold given the stage0 magnitudes
#                       (plain ~0.5, t20 ~0.35, t30 ~0.2, t35 ~0.1, t40 ~0.03)
#
# usage: ./run_distill_tail_stage0.sh [GPU]
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
    --output-dir audit_outputs/distill/tail_${tag} \
    --condition-start 0 --condition-end 1000 \
    --student-steps 4 --group-size 8 --grad-last-k 1 \
    --reward-weight 0.05 --reward-frames 4 --score-view ste \
    --precision bf16 --seed 42 "$@" 2>&1 | \
    grep -E "score grad share|grad distill|grad lambda|VERDICT|identity arm|score_t40|score_plain|threshold_weights" | head -20
}

{
  run equal
  run tiltA --tail-weights 1 1 2 4 8
  run tiltB --tail-weights 0.5 1 2 6 16
} > logs/distill_tail_stage0.log 2>&1

touch DISTILL_TAIL_STAGE0_DONE
cat logs/distill_tail_stage0.log
