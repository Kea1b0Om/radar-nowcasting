#!/bin/bash
# Frozen-half ensemble dump for the calibrated few-step distillation lane.
#
# Conditions: --start-batch 167 --end-batch 334 with micro_batch_size 6, i.e.
# events [1002, 2000) -- 998 events strictly inside the frozen half [1000, 2000)
# that no arm was trained on.  (1000 is not a multiple of 6, so the range starts
# two events late; every arm uses the identical range, so pairing is exact.)
#
# Six arms.  The two teacher arms are what make the student arms readable:
#
#   teacher_s10  the deployed product, 10 steps.  Upper reference.
#   teacher_s4   the SAME weights run at 4 steps, no distillation at all.
#                Without this arm, "lam0.0000 is close to the teacher" cannot
#                be attributed to distillation -- few-step degradation might
#                simply be small on this model.  This is the no-op control for
#                the entire distillation half of the method.
#   lam0.0000    pure endpoint distillation, 4 steps
#   lam0.0028    +reward at ~10% gradient share
#   lam0.0060    +reward at ~20% share
#   lam0.0200    +reward at ~39% share (deliberately over the calibrated band)
#
# Everything else is byte-identical across arms: same events, same member
# count, same seeds (seeded per GLOBAL batch index, so the shard range does not
# change the noise), same deterministic sampler (kappa=0).
#
# usage: ./run_distill_eval.sh
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch

CFG=experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml
TEACHER=artifacts/cikm/flowcast/teacher_v4.pt
H5=datasets/cikm/data/cikm_full/nowcast_validation_full.h5
META=datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv
OUT=audit_outputs/distill/frozen_half
mkdir -p ${OUT} logs

dump () {
  local gpu=$1 ckpt=$2 steps=$3 tag=$4
  CUDA_VISIBLE_DEVICES=${gpu} python -u tools/write_validation_ensemble.py \
    --config ${CFG} --checkpoint ${ckpt} \
    --test-file ${H5} --test-meta ${META} \
    --output ${OUT}/${tag}.h5 \
    --split-label validation \
    --start-batch 167 --end-batch 334 \
    --euler-steps ${steps} --members 8 --dtype float16 \
    > logs/dump_${tag}.log 2>&1
  echo "$? ${tag}" >> ${OUT}/EXITS
}

rm -f ${OUT}/EXITS DISTILL_EVAL_DONE

# Wave 1: the long teacher run plus three 4-step arms.
dump 0 ${TEACHER} 10 teacher_s10 &
dump 1 ${TEACHER} 4  teacher_s4 &
dump 2 audit_outputs/distill/lam0.0000/snapshots/student_final.pt 4 lam0.0000 &
dump 3 audit_outputs/distill/lam0.0028/snapshots/student_final.pt 4 lam0.0028 &
wait

# Wave 2: the remaining two arms.
dump 0 audit_outputs/distill/lam0.0060/snapshots/student_final.pt 4 lam0.0060 &
dump 1 audit_outputs/distill/lam0.0200/snapshots/student_final.pt 4 lam0.0200 &
wait

touch DISTILL_EVAL_DONE
