#!/bin/bash
# SCD / VE-Loss premise audits -- the pre-registered gate battery that decides
#   * Radar-SCD (weather-state encoder + future renderer) prototype: GO/NO-GO
#   * VE-Loss / robust-tokenizer route: premise present/absent/kill
# before any training run is budgeted.  Each stage is a read-only diagnostic
# on frozen checkpoints (~<= 1 GPU-hour per stage on the memo's budget).
#
# Order is load-bearing:
#   0. unit tests (house rule: local green first)
#   A. SCD separability -- 4-step grid (student if given, else teacher) and
#      10-step grid (teacher); gates G1-G4 live in the tool
#   B. AE posterior variance (VE diagnostic A); gates V1/V2
#   C. decoder endpoint robustness (VE diagnostic B) -- identity arm MUST
#      pass before the real arm is interpretable; gates K1/K2
#
# Usage:
#   CKPT=artifacts/cikm/flowcast/.../early_stopping_model.pt \
#   [STUDENT_CKPT=.../snapshots/student_iterNNNNNN.pt] \
#   [AE_CKPT=.../autoencoder_kl/.../early_stopping_model.pt] \
#   bash run_scd_ve_audits.sh [gpu]
#
# AE_CKPT is required with the default (v4) config outside production: its
# autoencoder_checkpoint hides behind an OmegaConf ${DATA_ROOT} interpolation
# that resolves only there; the tools fail with guidance if it is missing.
set -uo pipefail

GPU=${1:-0}
CFG=${CFG:-experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml}
CKPT=${CKPT:?set CKPT to the 10-step teacher FlowCast .pt}
STUDENT_CKPT=${STUDENT_CKPT:-}
AE_CKPT=${AE_CKPT:-}
VAL_FILE=${VAL_FILE:-datasets/cikm/data/cikm_full/nowcast_validation_full.h5}
VAL_META=${VAL_META:-datasets/cikm/data/cikm_full/nowcast_validation_full_META.csv}
OUT=${OUT:-audit_outputs/scd_ve}
MAX_EVENTS_SCD=${MAX_EVENTS_SCD:-32}
MAX_EVENTS_VAR=${MAX_EVENTS_VAR:-400}
MAX_EVENTS_END=${MAX_EVENTS_END:-32}

mkdir -p "$OUT"

echo "== 0. unit tests =="
python -m pytest tests/test_audit_scd_separability.py \
                 tests/test_audit_ae_posterior_variance.py \
                 tests/test_audit_decoder_endpoint_robustness.py -q 2>&1 | tail -3 || exit 1

echo "== A. SCD separability (4-step grid) =="
SCD4_CKPT=${STUDENT_CKPT:-$CKPT}
CUDA_VISIBLE_DEVICES=${GPU} python -u tools/audit_scd_separability.py \
  --config "$CFG" --checkpoint "$SCD4_CKPT" \
  ${AE_CKPT:+--ae-checkpoint "$AE_CKPT"} \
  --data-file "$VAL_FILE" --data-meta "$VAL_META" \
  --euler-steps 4 --max-events "$MAX_EVENTS_SCD" \
  --out "$OUT/scd_separability_s4.json" || exit 1

echo "== A'. SCD separability (10-step grid, teacher) =="
CUDA_VISIBLE_DEVICES=${GPU} python -u tools/audit_scd_separability.py \
  --config "$CFG" --checkpoint "$CKPT" \
  ${AE_CKPT:+--ae-checkpoint "$AE_CKPT"} \
  --data-file "$VAL_FILE" --data-meta "$VAL_META" \
  --euler-steps 10 --max-events "$MAX_EVENTS_SCD" \
  --out "$OUT/scd_separability_s10.json" || exit 1

echo "== B. AE posterior variance =="
CUDA_VISIBLE_DEVICES=${GPU} python -u tools/audit_ae_posterior_variance.py \
  --config "$CFG" \
  ${AE_CKPT:+--ae-checkpoint "$AE_CKPT"} \
  --data-file "$VAL_FILE" --data-meta "$VAL_META" \
  --max-events "$MAX_EVENTS_VAR" \
  --out "$OUT/ae_posterior_variance.json" || exit 1

echo "== C. decoder endpoint robustness: identity arm =="
CUDA_VISIBLE_DEVICES=${GPU} python -u tools/audit_decoder_endpoint_robustness.py \
  --config "$CFG" --checkpoint "$CKPT" \
  ${STUDENT_CKPT:+--student-checkpoint "$STUDENT_CKPT"} \
  ${AE_CKPT:+--ae-checkpoint "$AE_CKPT"} \
  --data-file "$VAL_FILE" --data-meta "$VAL_META" \
  --identity --max-events 4 \
  --out "$OUT/endpoint_identity.json" || exit 1

echo "== C'. decoder endpoint robustness: real arm =="
CUDA_VISIBLE_DEVICES=${GPU} python -u tools/audit_decoder_endpoint_robustness.py \
  --config "$CFG" --checkpoint "$CKPT" \
  ${STUDENT_CKPT:+--student-checkpoint "$STUDENT_CKPT"} \
  ${AE_CKPT:+--ae-checkpoint "$AE_CKPT"} \
  --data-file "$VAL_FILE" --data-meta "$VAL_META" \
  --max-events "$MAX_EVENTS_END" \
  --out "$OUT/endpoint_robustness.json" || exit 1

echo "== combined verdict =="
python - "$OUT" <<'PY'
import json
import sys

out = sys.argv[1]
scd4 = json.load(open(f"{out}/scd_separability_s4.json"))
scd10 = json.load(open(f"{out}/scd_separability_s10.json"))
var = json.load(open(f"{out}/ae_posterior_variance.json"))
end = json.load(open(f"{out}/endpoint_robustness.json"))

print("SCD (4-step grid, the pre-registered gate arm):")
for name, ok in scd4["verdict"]["gates"].items():
    print(f"  {name:28s} {'PASS' if ok else 'FAIL'}")
print(f"  -> Radar-SCD prototype: "
      f"{'GO' if scd4['verdict']['go_prototype'] else 'NO-GO'}"
      f"  (p={scd4['verdict']['p_separable_compute']:.3f}, "
      f"projected speedup {scd4['verdict']['projected_speedup']:.2f}x; "
      f"10-step grid agrees: {scd10['verdict']['go_prototype']})")

v = var["verdict"]
print("\nVE diagnostic A (posterior variance):")
print(f"  median sigma^2 = {v['median_sigma2']:.3e}")
if v["gates"]["V1_variance_collapse_premise_present"]:
    print("  -> collapse premise PRESENT (VE premise half-met; needs B too)")
elif v["gates"]["V2_premise_absent_VE_NOGO"]:
    print("  -> collapse premise ABSENT: VE-Loss as-is NO-GO")
else:
    print("  -> inconclusive band")

k = end["verdict"]
print("\nVE diagnostic B (endpoint amplification):")
print(f"  A_D(d4)/A_D(d10)   = {k['amp_ratio_s4_over_s10']:.3f} "
      f"(kill if < {k['constants']['kill_amp_ratio']})")
print(f"  A_D(d4)/A_D(gauss) = {k['amp_ratio_s4_over_gauss']:.3f} "
      f"(structure if >= {k['constants']['structure_min_ratio']})")
print(f"  -> tokenizer route: "
      f"{'conditional GO' if k['tokenizer_route_go'] else 'NO-GO / KILL'}")

both = (v["gates"]["V1_variance_collapse_premise_present"]
        and k["tokenizer_route_go"])
print("\nVE combined (memo rule: BOTH premises must hold):",
      "conditional GO" if both else "NO-GO")
PY
