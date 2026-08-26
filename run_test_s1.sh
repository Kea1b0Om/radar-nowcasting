#!/bin/bash
# CIKM TEST set, single-sample protocol -- the setting whose numbers are
# comparable to the published CIKM tables.
#
# The validation split has a different wet-pixel distribution from test, so
# validation numbers do not share a scale with published results.
#
# Chain gate: teacher_s10 at S=1 must reproduce the CSI-M that the training
# pipeline logged for this checkpoint (export GATE_VALUE).  If it does not,
# the dump or the scorer is wrong and no arm comparison may be read.
#
# usage: ./run_test_s1.sh
set -u
GATE_VALUE=${GATE_VALUE:?export GATE_VALUE=<CSI-M logged for this checkpoint>}
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch

CFG=experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml
TEACHER=artifacts/cikm/flowcast/teacher_v4.pt
H5=datasets/cikm/data/cikm_full/nowcast_testing_full.h5
META=datasets/cikm/data/cikm_full/nowcast_testing_full_META.csv
OUT=audit_outputs/distill/test_s1
mkdir -p ${OUT} logs

dump () {
  local gpu=$1 ckpt=$2 steps=$3 tag=$4
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/write_validation_ensemble.py \
    --config ${CFG} --checkpoint ${ckpt} \
    --test-file ${H5} --test-meta ${META} \
    --output ${OUT}/${tag}.h5 --split-label testing \
    --euler-steps ${steps} --members 1 --dtype float16 \
    > logs/test_s1_${tag}.log 2>&1
  echo "$? ${tag}" >> ${OUT}/EXITS
}

rm -f ${OUT}/EXITS TEST_S1_DONE

# Wave 1: the 10-step teacher (slowest, and the gate) plus three 4-step arms.
dump 0 ${TEACHER} 10 teacher_s10 &
dump 1 ${TEACHER} 4  teacher_s4 &
dump 2 audit_outputs/distill/lam0.0000/snapshots/student_final.pt 4 lam0.0000 &
dump 3 audit_outputs/distill/lam0.0200/snapshots/student_final.pt 4 lam0.0200 &
wait

# Wave 2: the two intermediate doses.
dump 0 audit_outputs/distill/lam0.0028/snapshots/student_final.pt 4 lam0.0028 &
dump 1 audit_outputs/distill/lam0.0060/snapshots/student_final.pt 4 lam0.0060 &
wait

python -u tools/score_test_published.py --collapse member0 \
  --arms \
    teacher_s10=${OUT}/teacher_s10.h5 \
    teacher_s4=${OUT}/teacher_s4.h5 \
    lam0.0000=${OUT}/lam0.0000.h5 \
    lam0.0028=${OUT}/lam0.0028.h5 \
    lam0.0060=${OUT}/lam0.0060.h5 \
    lam0.0200=${OUT}/lam0.0200.h5 \
  --gate-arm teacher_s10 --gate-value ${GATE_VALUE} --gate-tol 0.002 \
  --output ${OUT}/scores_s1.json > logs/test_s1_scores.log 2>&1

touch TEST_S1_DONE
