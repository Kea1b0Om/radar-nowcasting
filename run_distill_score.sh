#!/bin/bash
# Score the frozen-half ensembles against the pre-registered criteria.
#
# Reference = lam0.0000 (pure endpoint distillation); the criteria are stated
# relative to that arm.  The teacher arms are scored in the same table so the
# cost of few-step sampling is answered by the same numbers.
#
# CPU only, no model load.  usage: ./run_distill_score.sh
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch

OUT=audit_outputs/distill/frozen_half
python -u tools/score_gate_arms.py \
  --arms \
    teacher_s10=${OUT}/teacher_s10.h5 \
    teacher_s4=${OUT}/teacher_s4.h5 \
    lam0.0000=${OUT}/lam0.0000.h5 \
    lam0.0028=${OUT}/lam0.0028.h5 \
    lam0.0060=${OUT}/lam0.0060.h5 \
    lam0.0200=${OUT}/lam0.0200.h5 \
  --reference lam0.0000 \
  --input-length 5 \
  --output-dir ${OUT}/scores_ref_lam0 \
  > logs/distill_scores.log 2>&1
echo "score exit: $?"
touch DISTILL_SCORE_DONE
