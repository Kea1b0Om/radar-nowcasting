#!/bin/bash
# Frozen-half ensembles for the two tail-weighted arms, same protocol as the
# equal-weight arms already dumped (events [1002,2000), S=8, 4 steps, kappa=0,
# per-global-batch seeds) so all six arms are exactly paired.
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch
CFG=experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml
H5=datasets/cikm/data/cikm_full/nowcast_validation_full.h5
META=datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv
OUT=audit_outputs/distill/frozen_half
dump () {
  local gpu=$1 tag=$2
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/write_validation_ensemble.py \
    --config ${CFG} --checkpoint audit_outputs/distill/${tag}/snapshots/student_final.pt \
    --test-file ${H5} --test-meta ${META} --output ${OUT}/${tag}.h5 \
    --split-label validation --start-batch 167 --end-batch 334 \
    --euler-steps 4 --members 8 --dtype float16 > logs/dump_${tag}.log 2>&1
  echo "$? ${tag}" >> ${OUT}/EXITS_TAIL
}
rm -f ${OUT}/EXITS_TAIL TAIL_EVAL_DONE
dump 2 tiltA_lam0.0108 &
dump 3 tiltB_lam0.0143 &
wait
python -u tools/score_gate_arms.py --arms \
    teacher_s10=${OUT}/teacher_s10.h5 lam0.0000=${OUT}/lam0.0000.h5 \
    lam0.0060=${OUT}/lam0.0060.h5 lam0.0200=${OUT}/lam0.0200.h5 \
    tiltA_lam0.0108=${OUT}/tiltA_lam0.0108.h5 tiltB_lam0.0143=${OUT}/tiltB_lam0.0143.h5 \
  --reference lam0.0060 --input-length 5 \
  --output-dir ${OUT}/scores_ref_lam0060 > logs/tail_scores.log 2>&1
for C in mean q90; do
  python -u tools/score_test_published.py --collapse ${C} --arms \
    teacher_s10=${OUT}/teacher_s10.h5 lam0.0000=${OUT}/lam0.0000.h5 \
    lam0.0060=${OUT}/lam0.0060.h5 lam0.0200=${OUT}/lam0.0200.h5 \
    tiltA_lam0.0108=${OUT}/tiltA_lam0.0108.h5 tiltB_lam0.0143=${OUT}/tiltB_lam0.0143.h5 \
    --output ${OUT}/scores_tail_${C}.json >> logs/tail_scores.log 2>&1
done
touch TAIL_EVAL_DONE
