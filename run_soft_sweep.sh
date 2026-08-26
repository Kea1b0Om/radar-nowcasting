#!/bin/bash
# Soft chaining x tail weighting, at matched score-gradient magnitude.
#
# The stage0 calibration changed the design.  Softness revives the tail term
# (t40 grows 4.4x at s=5, and the plain term is bitwise unchanged, so the
# effect is attributable), but the *total* score gradient moves only +1.7%,
# because a revived term still carries only 1/5 of an equal-weight composite.
#
#   weight only  -> gradient moved onto a term that had none      (measured: worse)
#   soften only  -> term is alive but under-weighted              (this: +1.7% signal)
#   both         -> alive AND weighted                            <- the arm that matters
#
# Arms (1000 iters each), all at the same absolute score-gradient magnitude
# as the equal-weight lambda=0.006 arm already trained, so the comparison
# isolates *where* the gradient points, never how much there is:
#
#   soft2_equal   s=2, equal weights, lambda=0.006
#   soft5_equal   s=5, equal weights, lambda=0.006
#   soft5_tiltA   s=5, weights 1 1 2 4 8, lambda solved from a fresh stage0
#
# lambda for the combined arm cannot be guessed: tilting puts 0.5 of the mass
# on a term that softness just grew 4.4x, so the scale moves twice.  It is
# measured here and solved for, the same discipline that caught the original
# grid being 3x too hot.
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch
mkdir -p logs audit_outputs/distill
TARGET=$(python -c "print(0.006*0.79242)")   # lambda * ||grad score_raw|| of the reference arm

common_args () {
  echo "--config experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml \
    --checkpoint artifacts/cikm/flowcast/teacher_v4.pt \
    --expect-teacher-digest e654bbfccf2d \
    --train-file datasets/cikm/data/cikm_full/nowcast_validation_full.h5 \
    --train-meta datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv \
    --condition-start 0 --condition-end 1000 \
    --student-steps 4 --group-size 8 --grad-last-k 1 \
    --reward-frames 4 --score-view ste --precision bf16 --seed 42"
}

# --- measure the combined arm's score-gradient scale, then solve for lambda
CUDA_VISIBLE_DEVICES=2 python -u tools/train_distill_reward.py --stage0 --stage0-batches 3 \
  $(common_args) --output-dir audit_outputs/distill/soft5_tiltA_cal \
  --reward-weight 0.05 --chaining-softness 5.0 --tail-weights 1 1 2 4 8 \
  > logs/soft5_tiltA_cal.log 2>&1
LAM_C=$(python - <<PY
import json
d=json.load(open("audit_outputs/distill/soft5_tiltA_cal/stage0.json"))
import statistics
gs=[r["grad_norm_score"] for r in d["history"]]
raw=statistics.median(gs)/0.05
print(f"{$TARGET/raw:.6f}")
PY
)
echo "solved lambda for soft5_tiltA = ${LAM_C}" | tee logs/soft_sweep_lambda.txt

launch () {
  local gpu=$1 tag=$2 lam=$3; shift 3
  rm -rf audit_outputs/distill/${tag}
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/train_distill_reward.py \
    $(common_args) --output-dir audit_outputs/distill/${tag} \
    --iters 1000 --snapshot-every 200 --log-every 25 \
    --reward-weight ${lam} --lr 1e-5 --max-grad-norm 1.0 "$@" \
    > logs/distill_${tag}.log 2>&1
  echo "$? ${tag}" >> DISTILL_SOFT_SWEEP_EXITS
}

rm -f DISTILL_SOFT_SWEEP_DONE DISTILL_SOFT_SWEEP_EXITS
launch 0 soft2_equal 0.006  --chaining-softness 2.0 &
launch 1 soft5_equal 0.006  --chaining-softness 5.0 &
launch 2 soft5_tiltA ${LAM_C} --chaining-softness 5.0 --tail-weights 1 1 2 4 8 &
wait
touch DISTILL_SOFT_SWEEP_DONE
