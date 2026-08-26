#!/bin/bash
# Stage 0 wiring gate for the calibrated few-step distillation lane.
#
# No optimizer step is taken.  It answers four questions that a training
# curve cannot, and one that decides the dose:
#
#   1. identity arm exactly 0.0 on the real backbone (student==teacher at
#      the teacher's step count, shared noises)
#   2. the K-step distill loss is strictly positive
#   3. BOTH loss terms reach the student with finite, non-zero gradients
#      (back-propagated separately -- a combined backward would pass on the
#      distill term alone and hide a severed score path)
#   4. the teacher is bit-identical before and after
#   5. score_grad_share = ||grad(lambda*score)|| / (||grad distill|| +
#      ||grad(lambda*score)||), which is what --reward-weight must be
#      calibrated on.  Loss ratio is not a substitute: the UOT arm sat at
#      31.7% of the loss while carrying 213% of the gradient.
#
# The share is monotone in lambda and the raw norms are logged, so one run
# inverts to the lambda that hits any target share -- no sweep needed here.
#
# usage: ./run_distill_stage0.sh [GPU] [REWARD_WEIGHT] [BATCHES]
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch

GPU=${1:-1}
RW=${2:-0.05}
BATCHES=${3:-3}
TAG=stage0_rw${RW}

mkdir -p logs audit_outputs/distill
rm -f DISTILL_STAGE0_DONE
LOG=logs/distill_${TAG}.log

{
  echo "=== host/env ==="
  hostname; date -Is
  python -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda)"
  nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv

  echo
  echo "=== server test parity (house rule: local green is not enough) ==="
  python -m pytest tests/test_distill.py -q 2>&1 | tail -5

  echo
  echo "=== stage0 (GPU ${GPU}, reward_weight=${RW}, batches=${BATCHES}) ==="
  CUDA_VISIBLE_DEVICES=${GPU} python -u tools/train_distill_reward.py \
    --stage0 --stage0-batches ${BATCHES} \
    --config experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml \
    --checkpoint artifacts/cikm/flowcast/teacher_v4.pt \
    --train-file datasets/cikm/data/cikm_full/nowcast_validation_full.h5 \
    --train-meta datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv \
    --output-dir audit_outputs/distill/${TAG} \
    --condition-start 0 --condition-end 1000 \
    --student-steps 4 --group-size 8 --grad-last-k 1 \
    --reward-weight ${RW} --reward-frames 4 --score-view ste \
    --precision bf16 --seed 42
  echo "stage0 exit: $?"
  date -Is
} > ${LOG} 2>&1

touch DISTILL_STAGE0_DONE
