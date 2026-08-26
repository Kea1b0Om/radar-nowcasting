#!/bin/bash
# CIKM TEST replication of the qw arms.  Within-split CIs prove nothing about
# transfer, so a frozen-half result only counts if it reappears here.
#
# Reuses the existing test dumps for every reference arm (teacher_s10/s4,
# lambda dose arms) -- they are bitwise the same checkpoints -- and adds only
# the two qw arms, S=1 (published-comparable) and S=8 (probabilistic axis).
#
# Chain gate: teacher_s10 S=1 must still reproduce the logged CSI-M
# (export GATE_VALUE).
#
# Pre-registered readout, mirroring the frozen-half criteria:
#   transfers  if S=8 chunk2 bias40/csi CIs vs lam0.0060 stay positive and
#              exclude zero, with MSE flat (not the k200c signature);
#   fails      if the deltas shrink into the CI or flip sign (the RMLF
#              outcome), regardless of how good validation looked.
set -u
GATE_VALUE=${GATE_VALUE:?export GATE_VALUE=<CSI-M logged for this checkpoint>}
cd ~/FlowCast_uot
source ~/miniconda3/etc/profile.d/conda.sh
conda activate torch

CFG=experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml
H5=datasets/cikm/data/cikm_full/nowcast_testing_full.h5
META=datasets/cikm/data/cikm_full/nowcast_testing_full_META.csv
S1=audit_outputs/distill/test_s1
S8=audit_outputs/distill/test_s8
mkdir -p logs
rm -f QW_TEST_DONE QW_TEST_ABORT ${S1}/EXITS_QW ${S8}/EXITS_QW
echo "precheck" > QW_TEST_STAGE

# ---- reference dumps must already exist; this script never re-dumps them
for f in ${S1}/teacher_s10.h5 ${S1}/teacher_s4.h5 ${S1}/lam0.0060.h5 ${S1}/lam0.0200.h5 \
         ${S8}/teacher_s10.h5 ${S8}/lam0.0000.h5 ${S8}/lam0.0060.h5 ${S8}/lam0.0200.h5; do
  [ -f "$f" ] || { echo "missing reference dump: $f" | tee QW_TEST_ABORT; exit 1; }
done

# ---- GPU guard
for g in 0 1 2 3; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $g)
  if [ "$used" -gt 2000 ]; then
    echo "GPU $g busy (${used} MiB) - abort" | tee QW_TEST_ABORT; exit 1
  fi
done
echo "dump" > QW_TEST_STAGE

dump () {  # $1 gpu  $2 ckpt  $3 members  $4 outdir  $5 tag
  CUDA_VISIBLE_DEVICES=$1 python -u tools/write_validation_ensemble.py \
    --config ${CFG} --checkpoint $2 \
    --test-file ${H5} --test-meta ${META} \
    --output $4/$5.h5 --split-label testing \
    --euler-steps 4 --members $3 --dtype float16 \
    > logs/qw_test_$5_m$3.log 2>&1
  echo "$? $5 m$3" >> $4/EXITS_QW
}

QW50=audit_outputs/distill/qw_t50/snapshots/student_final.pt
QW80=audit_outputs/distill/qw_t80/snapshots/student_final.pt
dump 0 ${QW50} 1 ${S1} qw_t50 &
dump 1 ${QW80} 1 ${S1} qw_t80 &
dump 2 ${QW50} 8 ${S8} qw_t50 &
dump 3 ${QW80} 8 ${S8} qw_t80 &
wait
echo "score_s1" > QW_TEST_STAGE

# ---- S=1: the published-comparable table, chain gate re-checked
python -u tools/score_test_published.py --collapse member0 \
  --arms \
    teacher_s10=${S1}/teacher_s10.h5 teacher_s4=${S1}/teacher_s4.h5 \
    lam0.0060=${S1}/lam0.0060.h5 lam0.0200=${S1}/lam0.0200.h5 \
    qw_t50=${S1}/qw_t50.h5 qw_t80=${S1}/qw_t80.h5 \
  --gate-arm teacher_s10 --gate-value ${GATE_VALUE} --gate-tol 0.002 \
  --output ${S1}/scores_s1_qw.json > logs/qw_test_scores.log 2>&1
echo "score_s8" > QW_TEST_STAGE

# ---- S=8: probabilistic axis + the ratio CIs, reference = matched control
python -u tools/score_gate_arms.py --arms \
    teacher_s10=${S8}/teacher_s10.h5 lam0.0000=${S8}/lam0.0000.h5 \
    lam0.0060=${S8}/lam0.0060.h5 lam0.0200=${S8}/lam0.0200.h5 \
    qw_t50=${S8}/qw_t50.h5 qw_t80=${S8}/qw_t80.h5 \
  --reference lam0.0060 --input-length 5 \
  --output-dir ${S8}/scores_ref_control_qw >> logs/qw_test_scores.log 2>&1

for C in mean q90; do
  python -u tools/score_test_published.py --collapse ${C} \
    --arms \
      teacher_s10=${S8}/teacher_s10.h5 lam0.0000=${S8}/lam0.0000.h5 \
      lam0.0060=${S8}/lam0.0060.h5 lam0.0200=${S8}/lam0.0200.h5 \
      qw_t50=${S8}/qw_t50.h5 qw_t80=${S8}/qw_t80.h5 \
    --output ${S8}/scores_qw_${C}.json >> logs/qw_test_scores.log 2>&1
done
echo "done" > QW_TEST_STAGE
touch QW_TEST_DONE
