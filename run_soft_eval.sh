#!/bin/bash
# Frozen-half evaluation of the soft-chaining arms, against the arms that
# isolate each factor:
#
#   lam0.0060        equal weights, hard chain   <- the matched-share control
#   tiltA_lam0.0108  weighted, hard chain        <- weight without gradient (failed)
#   soft2/soft5_equal  soft chain, equal weights <- gradient without weight
#   soft5_tiltA      soft chain + weighted       <- both (the arm that matters)
#
# All at the same absolute score-gradient magnitude, so the only thing that
# varies across the four is where the gradient can reach and how much of it
# lands on the tail.
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
  echo "$? ${tag}" >> ${OUT}/EXITS_SOFT
}
rm -f ${OUT}/EXITS_SOFT SOFT_EVAL_DONE
dump 0 soft2_equal & dump 1 soft5_equal & dump 2 soft5_tiltA & wait

ARMS="teacher_s10=${OUT}/teacher_s10.h5 lam0.0000=${OUT}/lam0.0000.h5 \
lam0.0060=${OUT}/lam0.0060.h5 lam0.0200=${OUT}/lam0.0200.h5 \
tiltA_lam0.0108=${OUT}/tiltA_lam0.0108.h5 \
soft2_equal=${OUT}/soft2_equal.h5 soft5_equal=${OUT}/soft5_equal.h5 \
soft5_tiltA=${OUT}/soft5_tiltA.h5"

python -u tools/score_gate_arms.py --arms ${ARMS} \
  --reference lam0.0060 --input-length 5 \
  --output-dir ${OUT}/scores_ref_soft > logs/soft_eval_scores.log 2>&1
for C in mean q90; do
  python -u tools/score_test_published.py --collapse ${C} --arms ${ARMS} \
    --output ${OUT}/scores_soft_${C}.json >> logs/soft_eval_scores.log 2>&1
done
touch SOFT_EVAL_DONE
