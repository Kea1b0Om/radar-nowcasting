#!/bin/bash
# qw arms: TEST-set verification + the performance sweep nobody has run yet.
#
# Why this exists.  Every qw number so far came from an experiment designed for
# ATTRIBUTION, not performance: lambda was solved to match the dead tw arms'
# score-gradient magnitude exactly, so that the only thing differing across
# arms was the WEIGHTING AXIS.  That is the right design for the mechanism
# claim and the wrong design for asking how good the method gets -- the tilt
# was deliberately given the same authority as objectives already known to do
# nothing.  Nobody has yet turned the knob up.
#
# Two knobs, pre-registered predictions:
#
#   lambda (authority).  For the tw arms, raising lambda made bias40 WORSE
#     (0.7731 -> 0.7624 at lam0.0200): more weight on a median-seeking term is
#     more median-seeking.  For qw the sign must FLIP -- more weight on a
#     q90-seeking term should push bias40 UP.  A flip is simultaneously a
#     performance gain and a third independent mechanism confirmation; no flip
#     means the tilt is being swallowed and the ceiling is already here.
#   tau0 (tilt level).  tau* = (1+tau0)/2, so tau0=0.95 targets q97.5.  The
#     collapse-quantile precheck peaked at q90 for the students, so t95 is
#     expected to overshoot: it is the arm that finds the top of the curve.
#
# TEST is the gate that outranks all of it: validation-only CIs did not
# survive transfer once already (RMLF).  Test runs first, on the two arms
# already trained, before any new GPU goes to sweeping.
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch
mkdir -p logs
rm -f QW_MAX_DONE QW_MAX_ABORT
echo "test" > QW_MAX_STAGE

CFG=experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml
TEACHER=artifacts/cikm/flowcast/teacher_v4.pt
TEST_H5=datasets/cikm/data/cikm_full/nowcast_testing_full.h5
TEST_META=datasets/cikm/data/cikm_full/nowcast_testing_full_META.csv
T8=audit_outputs/distill/test_s8
mkdir -p ${T8}

# ---------------------------------------------------------------- 1. TEST
# 8-member dumps of the two trained qw arms, matching whatever protocol the
# existing test_s8 arms used.  The teacher/control dumps are reused if present
# (they are frozen artefacts; re-dumping only burns GPU and risks divergence).
test_dump () {
  local gpu=$1 ckpt=$2 steps=$3 tag=$4
  if [ -f ${T8}/${tag}.h5 ]; then echo "reuse ${tag}"; return; fi
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/write_validation_ensemble.py \
    --config ${CFG} --checkpoint ${ckpt} \
    --test-file ${TEST_H5} --test-meta ${TEST_META} \
    --output ${T8}/${tag}.h5 --split-label testing \
    --euler-steps ${steps} --members 8 --dtype float16 \
    > logs/test_s8_${tag}.log 2>&1
  echo "$? ${tag}" >> ${T8}/EXITS_QW
}
rm -f ${T8}/EXITS_QW
test_dump 0 audit_outputs/distill/qw_t80/snapshots/student_final.pt 4 qw_t80 &
test_dump 1 audit_outputs/distill/qw_t50/snapshots/student_final.pt 4 qw_t50 &
test_dump 2 ${TEACHER} 10 teacher_s10 &
test_dump 3 audit_outputs/distill/lam0.0060/snapshots/student_final.pt 4 lam0.0060 &
wait

TEST_ARMS=""
for t in teacher_s10 lam0.0060 lam0.0200 qw_t50 qw_t80; do
  [ -f ${T8}/${t}.h5 ] && TEST_ARMS="${TEST_ARMS} ${t}=${T8}/${t}.h5"
done
echo "=== TEST published protocol ===" > logs/qw_test_scores.log
for C in mean q90; do
  python -u tools/score_test_published.py --collapse ${C} --arms ${TEST_ARMS} \
    --output ${T8}/scores_qw_${C}.json >> logs/qw_test_scores.log 2>&1
done
# Paired CIs on test, same estimator as validation (input-length 5).
python -u tools/score_gate_arms.py --arms ${TEST_ARMS} \
  --reference lam0.0060 --input-length 5 \
  --output-dir ${T8}/scores_ref_qw_ci >> logs/qw_test_scores.log 2>&1

echo "sweep" > QW_MAX_STAGE

# ------------------------------------------------------- 2. PERFORMANCE SWEEP
common_args () {
  echo "--config ${CFG} --checkpoint ${TEACHER} \
    --expect-teacher-digest e654bbfccf2d \
    --train-file datasets/cikm/data/cikm_full/nowcast_validation_full.h5 \
    --train-meta datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv \
    --condition-start 0 --condition-end 1000 \
    --student-steps 4 --group-size 8 --grad-last-k 1 \
    --reward-frames 4 --score-view ste --precision bf16 --seed 42"
}
TARGET=$(python -c "print(0.006*0.79242)")
LAM_T80=0.005034          # solved earlier; the matched-attribution dose

# tau0=0.95 needs its own solve: the window integrates only 5% of tau-mass, so
# its raw score scale is ~4x smaller than t80's and a guessed lambda would be
# a dose experiment pretending to be a tilt experiment.
rm -rf audit_outputs/distill/qw_t95_cal
CUDA_VISIBLE_DEVICES=0 python -u tools/train_distill_reward.py --stage0 --stage0-batches 3 \
  $(common_args) --output-dir audit_outputs/distill/qw_t95_cal \
  --reward-weight 0.05 --qw-tau0 0.95 > logs/qw_t95_cal.log 2>&1
LAM_T95=$(python - <<PY
import json, statistics
d = json.load(open("audit_outputs/distill/qw_t95_cal/stage0.json"))
raw = statistics.median([r["grad_norm_score"] for r in d["history"]]) / 0.05
print(f"{${TARGET}/raw:.6f}")
PY
)
LAM_X2=$(python -c "print(f'{2*${LAM_T80}:.6f}')")
LAM_X4=$(python -c "print(f'{4*${LAM_T80}:.6f}')")
echo "lambda: t80x2=${LAM_X2} t80x4=${LAM_X4} t95=${LAM_T95}" | tee logs/qw_max_lambda.txt

launch () {
  local gpu=$1 tag=$2 lam=$3 tau=$4 iters=$5
  rm -rf audit_outputs/distill/${tag}
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/train_distill_reward.py \
    $(common_args) --output-dir audit_outputs/distill/${tag} \
    --iters ${iters} --snapshot-every 500 --log-every 25 \
    --reward-weight ${lam} --lr 1e-5 --max-grad-norm 1.0 --qw-tau0 ${tau} \
    > logs/distill_${tag}.log 2>&1
  echo "$? ${tag}" >> DISTILL_QW_MAX_EXITS
}
rm -f DISTILL_QW_MAX_EXITS
# t80_long doubles the schedule at the matched dose: separates "the tilt is
# saturated" from "1000 iters was simply not enough", which no arm has tested.
launch 0 qw_t80_x2   ${LAM_X2}  0.8  1000 &
launch 1 qw_t80_x4   ${LAM_X4}  0.8  1000 &
launch 2 qw_t95      ${LAM_T95} 0.95 1000 &
launch 3 qw_t80_long ${LAM_T80} 0.8  2000 &
wait
echo "eval" > QW_MAX_STAGE

# ------------------------------------------------------------- 3. VALIDATION EVAL
VH5=datasets/cikm/data/cikm_full/nowcast_validation_full.h5
VMETA=datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv
OUT=audit_outputs/distill/frozen_half
rm -f ${OUT}/EXITS_QWMAX
dump () {
  local gpu=$1 tag=$2
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/write_validation_ensemble.py \
    --config ${CFG} --checkpoint audit_outputs/distill/${tag}/snapshots/student_final.pt \
    --test-file ${VH5} --test-meta ${VMETA} --output ${OUT}/${tag}.h5 \
    --split-label validation --start-batch 167 --end-batch 334 \
    --euler-steps 4 --members 8 --dtype float16 > logs/dump_${tag}.log 2>&1
  echo "$? ${tag}" >> ${OUT}/EXITS_QWMAX
}
dump 0 qw_t80_x2 & dump 1 qw_t80_x4 & dump 2 qw_t95 & dump 3 qw_t80_long & wait

ARMS="teacher_s10=${OUT}/teacher_s10.h5 lam0.0060=${OUT}/lam0.0060.h5 \
lam0.0200=${OUT}/lam0.0200.h5 soft5_tiltA=${OUT}/soft5_tiltA.h5 \
qw_t50=${OUT}/qw_t50.h5 qw_t80=${OUT}/qw_t80.h5 \
qw_t80_x2=${OUT}/qw_t80_x2.h5 qw_t80_x4=${OUT}/qw_t80_x4.h5 \
qw_t95=${OUT}/qw_t95.h5 qw_t80_long=${OUT}/qw_t80_long.h5"
python -u tools/score_gate_arms.py --arms ${ARMS} \
  --reference lam0.0060 --input-length 5 \
  --output-dir ${OUT}/scores_qwmax_ci > logs/qw_max_scores.log 2>&1
for C in mean q90; do
  python -u tools/score_test_published.py --collapse ${C} --arms ${ARMS} \
    --output ${OUT}/scores_qwmax_${C}.json >> logs/qw_max_scores.log 2>&1
done
echo "done" > QW_MAX_STAGE
touch QW_MAX_DONE
