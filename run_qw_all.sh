#!/bin/bash
# Quantile-axis (qwCRPS) dose arms, end to end: precheck -> stage0 -> sweep -> eval.
#
# The z-vs-tau dichotomy: every refuted arm weighted the OUTCOME axis of the
# score (tw chaining), whose collapsed-ensemble optimum is the conditional
# median for ANY weighting.  These arms weight the QUANTILE-LEVEL axis
# (Gneiting & Ranjan 2011's other half): pure window w(a) = 1{a >= tau0},
# whose collapsed optimum is the conditional quantile (1 + tau0)/2.
#
#   qw_t50  tau0=0.5  -> collapse point q75
#   qw_t80  tau0=0.8  -> collapse point q90
#
# Both at the same absolute score-gradient magnitude as every previous arm
# (TARGET = lambda * ||grad score_raw|| of the lam0.0060 reference), so the
# only thing that varies vs the dead tw/soft arms is the AXIS of the weight.
#
# Pre-registered readout (frozen half, scores_ref_qw + published tables):
#   dies    if bias40 stays at the control's ~0.773 (tilt swallowed), or moves
#           only with csi40/CSI-M degrading beyond the lam0.0200 trade-off;
#   lives   if bias40 rises with csi40 (q90 and mean collapse both reported).
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch
mkdir -p logs audit_outputs/distill
OUT=audit_outputs/distill/frozen_half
rm -f QW_ALL_DONE QW_ABORT ${OUT}/EXITS_QW DISTILL_QW_SWEEP_EXITS
echo "precheck" > QW_STAGE_MARK

# ---- GPU guard: refuse to stomp on someone else's run
for g in 0 1; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $g)
  if [ "$used" -gt 2000 ]; then
    echo "GPU $g busy (${used} MiB) - abort" | tee QW_ABORT; exit 1
  fi
done

# ---- 0. zero-GPU precheck: collapse-quantile monotonicity on frozen dumps.
# If CSI gain is not monotone toward upper quantiles, tau* being the right
# target loses its prior (informative either way; not a hard gate).
ARMS_PRE="teacher_s10=${OUT}/teacher_s10.h5 lam0.0060=${OUT}/lam0.0060.h5 lam0.0200=${OUT}/lam0.0200.h5"
for C in q50 q75 q95; do
  python -u tools/score_test_published.py --collapse ${C} --arms ${ARMS_PRE} \
    --output ${OUT}/scores_precheck_${C}.json >> logs/qw_precheck.log 2>&1
done
echo "stage0" > QW_STAGE_MARK

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
TARGET=$(python -c "print(0.006*0.79242)")

# ---- 1. per-arm lambda: the window integrates over (1-tau0) of tau-mass, so
# the raw score scale shrinks with tau0 and each arm must be solved, not
# guessed -- the discipline that caught the original grid being 3x too hot.
solve_lambda () {  # $1 gpu  $2 tag  $3 tau0
  rm -rf audit_outputs/distill/$2_cal
  CUDA_VISIBLE_DEVICES=$1 python -u tools/train_distill_reward.py --stage0 --stage0-batches 3 \
    $(common_args) --output-dir audit_outputs/distill/$2_cal \
    --reward-weight 0.05 --qw-tau0 $3 > logs/$2_cal.log 2>&1
  python - <<PY
import json, statistics
d = json.load(open("audit_outputs/distill/$2_cal/stage0.json"))
raw = statistics.median([r["grad_norm_score"] for r in d["history"]]) / 0.05
print(f"{${TARGET}/raw:.6f}")
PY
}
LAM_T50=$(solve_lambda 0 qw_t50 0.5)
LAM_T80=$(solve_lambda 1 qw_t80 0.8)
echo "lambda qw_t50=${LAM_T50} qw_t80=${LAM_T80}" | tee logs/qw_sweep_lambda.txt
echo "sweep" > QW_STAGE_MARK

# ---- 2. the dose arms
launch () {
  local gpu=$1 tag=$2 lam=$3 tau=$4
  rm -rf audit_outputs/distill/${tag}
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/train_distill_reward.py \
    $(common_args) --output-dir audit_outputs/distill/${tag} \
    --iters 1000 --snapshot-every 200 --log-every 25 \
    --reward-weight ${lam} --lr 1e-5 --max-grad-norm 1.0 --qw-tau0 ${tau} \
    > logs/distill_${tag}.log 2>&1
  echo "$? ${tag}" >> DISTILL_QW_SWEEP_EXITS
}
launch 0 qw_t50 ${LAM_T50} 0.5 &
launch 1 qw_t80 ${LAM_T80} 0.8 &
wait
echo "eval" > QW_STAGE_MARK

# ---- 3. frozen-half dumps + the same two scoreboards as every prior arm
CFG=experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml
H5=datasets/cikm/data/cikm_full/nowcast_validation_full.h5
META=datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv
dump () {
  local gpu=$1 tag=$2
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/write_validation_ensemble.py \
    --config ${CFG} --checkpoint audit_outputs/distill/${tag}/snapshots/student_final.pt \
    --test-file ${H5} --test-meta ${META} --output ${OUT}/${tag}.h5 \
    --split-label validation --start-batch 167 --end-batch 334 \
    --euler-steps 4 --members 8 --dtype float16 > logs/dump_${tag}.log 2>&1
  echo "$? ${tag}" >> ${OUT}/EXITS_QW
}
dump 0 qw_t50 & dump 1 qw_t80 & wait

ARMS="teacher_s10=${OUT}/teacher_s10.h5 lam0.0000=${OUT}/lam0.0000.h5 \
lam0.0060=${OUT}/lam0.0060.h5 lam0.0200=${OUT}/lam0.0200.h5 \
tiltA_lam0.0108=${OUT}/tiltA_lam0.0108.h5 soft5_tiltA=${OUT}/soft5_tiltA.h5 \
qw_t50=${OUT}/qw_t50.h5 qw_t80=${OUT}/qw_t80.h5"
python -u tools/score_gate_arms.py --arms ${ARMS} \
  --reference lam0.0060 --input-length 5 \
  --output-dir ${OUT}/scores_ref_qw > logs/qw_eval_scores.log 2>&1
for C in mean q90; do
  python -u tools/score_test_published.py --collapse ${C} --arms ${ARMS} \
    --output ${OUT}/scores_qw_${C}.json >> logs/qw_eval_scores.log 2>&1
done
echo "done" > QW_STAGE_MARK
touch QW_ALL_DONE
