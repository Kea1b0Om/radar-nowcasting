#!/usr/bin/env bash
# E0: per-threshold AE ceiling + frequency bias.  ONE ssh session, ~0.4 GPU-h.
#
# Gate order is mandatory: the identity arm must PASS before the real arm is
# believed.  If identity does not return CSI=1.000000 and FBI=1.000000 at all
# four thresholds, the eval view is mis-wired and the real numbers mean nothing.
set -euo pipefail

CFG=experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml
CKPT=${CKPT:?set CKPT to the v4 UOT checkpoint .pt}
TEST_FILE=datasets/cikm/data/cikm_full/nowcast_testing_full.h5
TEST_META=datasets/cikm/data/cikm_full/nowcast_testing_full_META.csv
OUT=audit_outputs/ae_fbi

mkdir -p "$OUT"

echo "=== ARM 0: identity (no codec) -- must be exactly 1.0 ==="
python tools/audit_ae_fbi.py --config "$CFG" --checkpoint "$CKPT" \
  --test-file "$TEST_FILE" --test-meta "$TEST_META" \
  --identity --max-events 400 --out "$OUT/identity.json"

# The authoritative identity check lives in audit_ae_fbi.py (it skips cells with
# no truth exceedance and exits 1 on a real mismatch).  set -e already aborts on
# that.  This block only surfaces the diagnostics.
python - "$OUT/identity.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print("  identity diagnostics:")
for t in ("20","30","35","40"):
    print(f"    @{t:<4} csi={d['csi_ae_per_threshold'][t]:.6f}"
          f"  truth_exceedance={d['truth_exceedance_per_threshold'][t]:.1f}"
          f"  empty_leads={d['empty_cells_per_threshold'][t]}")
PY

echo
echo "=== ARM 1: pilot, 400 events (sanity + rough magnitude) ==="
python tools/audit_ae_fbi.py --config "$CFG" --checkpoint "$CKPT" \
  --test-file "$TEST_FILE" --test-meta "$TEST_META" \
  --max-events 400 --out "$OUT/pilot400.json"

echo
echo "=== ARM 2: full test (4000 events) ==="
python tools/audit_ae_fbi.py --config "$CFG" --checkpoint "$CKPT" \
  --test-file "$TEST_FILE" --test-meta "$TEST_META" \
  --out "$OUT/full.json"

echo
echo "=== VERDICT ==="
python - "$OUT/full.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
csi=d["csi_ae_per_threshold"]; fbi=d["fbi_ae_per_threshold"]
print(f"  n_events = {d['n_events']}")
print("  thr    CSI_AE     FBI_AE")
for t in ("20","30","35","40"):
    print(f"  @{t:<4} {csi[t]:.5f}   {fbi[t]:.5f}")
v=d["verdict"]; f30=fbi["30"]
print()
if v["R1_ceiling_not_binding"]:
    print("  R1 HIT : CSI_AE(30) >= 0.60 -> raising the ceiling (f=4 / more latent")
    print("           channels) is permanently closed.  Do not spend GPU there.")
if v["R3_decoder_eating_area_lever_E_GO"]:
    print(f"  R3 HIT : FBI_AE(30) = {f30:.4f} <= 0.92 -> the DECODER eats >=8% of the")
    print("           30 dBZ area.  Lever E is GO; worth ~+0.0247 CSI@30 (+0.0062 CSI-M),")
    print("           which clears SDIR when stacked on the q90 readout.")
elif v["R2_decoder_NOT_eating_area_lever_E_NOGO"]:
    print(f"  R2 HIT : FBI_AE(30) = {f30:.4f} >= 0.97 -> the decoder is NOT eating area.")
    print("           The decoder is not eating area at this threshold.")
else:
    print(f"  INCONCLUSIVE: FBI_AE(30) = {f30:.4f} in (0.92, 0.97).  Arm stays unfunded;")
    print("           break the tie with the @35 column before spending anything.")
PY
