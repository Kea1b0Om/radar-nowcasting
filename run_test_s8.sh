#!/bin/bash
# CIKM TEST set, 8-member ensembles -- the probabilistic axis, where this
# method's actual claim lives (CRPS / spread-skill), and where SDIR reports
# nothing at all.
#
# Run AFTER run_test_s1.sh so the two do not contend for GPUs.  The S=1 pass
# answers "does it belong in the published table"; this pass answers "is the
# 4-step student a better probabilistic forecast than the 10-step product".
#
# Two waves.  teacher_s10 at 10 steps over 4000 events is the long pole
# (~2.5h); the 4-step arms are ~2.5x faster.
#
# usage: ./run_test_s8.sh
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch

CFG=experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml
TEACHER=artifacts/cikm/flowcast/teacher_v4.pt
H5=datasets/cikm/data/cikm_full/nowcast_testing_full.h5
META=datasets/cikm/data/cikm_full/nowcast_testing_full_META.csv
OUT=audit_outputs/distill/test_s8
mkdir -p ${OUT} logs

dump () {
  local gpu=$1 ckpt=$2 steps=$3 tag=$4
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/write_validation_ensemble.py \
    --config ${CFG} --checkpoint ${ckpt} \
    --test-file ${H5} --test-meta ${META} \
    --output ${OUT}/${tag}.h5 --split-label testing \
    --euler-steps ${steps} --members 8 --dtype float16 \
    > logs/test_s8_${tag}.log 2>&1
  echo "$? ${tag}" >> ${OUT}/EXITS
}

rm -f ${OUT}/EXITS TEST_S8_DONE

dump 0 ${TEACHER} 10 teacher_s10 &
dump 1 ${TEACHER} 4  teacher_s4 &
dump 2 audit_outputs/distill/lam0.0000/snapshots/student_final.pt 4 lam0.0000 &
dump 3 audit_outputs/distill/lam0.0200/snapshots/student_final.pt 4 lam0.0200 &
wait

dump 0 audit_outputs/distill/lam0.0028/snapshots/student_final.pt 4 lam0.0028 &
dump 1 audit_outputs/distill/lam0.0060/snapshots/student_final.pt 4 lam0.0060 &
wait

# Probabilistic table (CRPS / spread-skill / pooled CSI), paired bootstrap
# against the deployed 10-step product.
python -u tools/score_gate_arms.py --arms \
    teacher_s10=${OUT}/teacher_s10.h5 teacher_s4=${OUT}/teacher_s4.h5 \
    lam0.0000=${OUT}/lam0.0000.h5 lam0.0028=${OUT}/lam0.0028.h5 \
    lam0.0060=${OUT}/lam0.0060.h5 lam0.0200=${OUT}/lam0.0200.h5 \
  --reference teacher_s10 --input-length 5 \
  --output-dir ${OUT}/scores_ref_teacher10 > logs/test_s8_scores.log 2>&1

# Ensemble-mean CSI in the published per-lead reduction.  Reported ONLY
# alongside the S=1 table and explicitly labelled: an 8-member mean is not
# comparable to a single-sample published number.
python -u tools/score_test_published.py --collapse mean \
  --arms \
    teacher_s10=${OUT}/teacher_s10.h5 teacher_s4=${OUT}/teacher_s4.h5 \
    lam0.0000=${OUT}/lam0.0000.h5 lam0.0028=${OUT}/lam0.0028.h5 \
    lam0.0060=${OUT}/lam0.0060.h5 lam0.0200=${OUT}/lam0.0200.h5 \
  --output ${OUT}/scores_ensmean.json >> logs/test_s8_scores.log 2>&1

touch TEST_S8_DONE
