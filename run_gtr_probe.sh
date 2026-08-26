#!/bin/bash
# GTR stage-A probe: zero-training truncated-source arms + scoring, one chain.
#
# Arms: control (production sampler) / oracle_k{3,5,7} (truth-anchored source,
# diagnostic ceiling) / tmean_k{3,5,7} (teacher-mean-anchored source, the
# zero-training GTR proxy).  250 frozen-half validation events, S=8.
#
# Pre-registered readouts (scores_ref_gtr vs control):
#   mechanism works  = tmean ssr moves toward 1 with CRPS improving and MSE
#                      not exploding (k200c off-manifold discriminator);
#   truncation dead  = oracle arms degrade badly even at k=7 (frozen flow
#                      cannot run from interior starts);
#   anchor worthless = tmean ~= control at every k (a trained prior must then
#                      carry everything; pilot stage B decides).
set -u
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch
mkdir -p logs audit_outputs/gtr_probe
rm -f GTR_PROBE_DONE GTR_PROBE_ABORT
echo "run" > GTR_PROBE_STAGE

GPU=""
for g in 3 2 1 0; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $g)
  if [ "$used" -lt 2000 ]; then GPU=$g; break; fi
done
[ -n "$GPU" ] || { echo "no free GPU" | tee GTR_PROBE_ABORT; exit 1; }
echo "using GPU ${GPU}"

CUDA_VISIBLE_DEVICES=${GPU} python -u tools/gtr_probe.py \
  --config experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml \
  --checkpoint artifacts/cikm/flowcast/teacher_v4.pt \
  --test-file datasets/cikm/data/cikm_full/nowcast_validation_full.h5 \
  --test-meta datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv \
  --split-label validation --start-batch 167 --max-events 250 \
  --members 8 --start-indices 3 5 7 --anchor-samples 8 \
  --output-dir audit_outputs/gtr_probe > logs/gtr_probe.log 2>&1
rc=$?
[ $rc -eq 0 ] || { echo "probe failed rc=$rc" | tee GTR_PROBE_ABORT; exit $rc; }
echo "score" > GTR_PROBE_STAGE

OUT=audit_outputs/gtr_probe
ARMS="control=${OUT}/control.h5"
for k in 3 5 7; do
  ARMS="${ARMS} oracle_k${k}=${OUT}/oracle_k${k}.h5 tmean_k${k}=${OUT}/tmean_k${k}.h5"
done
python -u tools/score_gate_arms.py --arms ${ARMS} \
  --reference control --input-length 5 \
  --output-dir ${OUT}/scores_ref_gtr > logs/gtr_probe_scores.log 2>&1

echo "done" > GTR_PROBE_STAGE
touch GTR_PROBE_DONE
