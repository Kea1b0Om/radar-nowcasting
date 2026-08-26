#!/usr/bin/env bash
# External arm: NFE sweep on a frozen StormScope.
# Run the whole thing inside ONE ssh session (connection-count discipline).
set -euo pipefail

VARIANT="${VARIANT:-6km_1hr}"
DEVICE="${DEVICE:-cuda:0}"
OUT="${OUT:-audit_outputs/stormscope}"
TIMES="${TIMES:-tools/stormscope_times_2024.txt}"
MEMBERS="${MEMBERS:-8}"
FRAMES="${FRAMES:-4}"

echo "=== gate 0: NATTEN ==="
# HAS_LIBNATTEN does not exist in natten 0.17.5 -- probe the backend functions,
# and actually run a kernel: import succeeding proves nothing about sm_89.
python - <<'PY' || { echo "NATTEN unusable -> NO-GO, stop here."; exit 1; }
import sys, torch, natten
from natten.functional import na2d
print("natten", natten.__version__,
      {f: getattr(natten, f)() for f in ("has_cuda", "has_half", "has_fna")})
q, k, v = (torch.randn(1, 64, 64, 4, 32, device="cuda", dtype=torch.float16)
           for _ in range(3))
out = na2d(q, k, v, kernel_size=7)
torch.cuda.synchronize()
assert torch.isfinite(out).all(), "na2d produced non-finite output"
print("na2d OK", tuple(out.shape))
PY

echo
echo "=== gate 1: load + one forward, peak VRAM ==="
python tools/stormscope_probe.py \
  --variants "$VARIANT" --device "$DEVICE" --out "$OUT/probe.json"

echo
echo "=== arm A: deployment sampler (S_churn=10) ==="
python tools/stormscope_nfe_dump.py \
  --variant "$VARIANT" --device "$DEVICE" \
  --times-file "$TIMES" --members "$MEMBERS" --frames "$FRAMES" \
  --s-churn 10 --out-dir "$OUT/nfe_churn10"

echo
echo "=== arm B: deterministic ODE (S_churn=0, exactly pairable) ==="
python tools/stormscope_nfe_dump.py \
  --variant "$VARIANT" --device "$DEVICE" \
  --times-file "$TIMES" --members "$MEMBERS" --frames "$FRAMES" \
  --s-churn 0 --out-dir "$OUT/nfe_churn0"

echo
echo "=== scoring ==="
for D in "$OUT/nfe_churn10" "$OUT/nfe_churn0"; do
  ARMS=$(python - "$D" <<'PY'
import json, sys
m = json.load(open(f"{sys.argv[1]}/manifest.json"))
print(" ".join(f"{k}={v['h5']}" for k, v in m["arms"].items()))
PY
)
  REF=$(python - "$D" <<'PY'
import json, sys
m = json.load(open(f"{sys.argv[1]}/manifest.json"))
print(f"nfe{max(m['nfe']):03d}")
PY
)
  python tools/score_gate_arms.py --arms $ARMS \
    --reference "$REF" --input-length $((FRAMES / 2)) \
    --output-dir "$D/scores"
done

echo
echo "done. The claim to read off:"
echo "  CSI@30/35/40 across NFE arms  -> should barely move"
echo "  spread_fair / ssr across arms -> should collapse as NFE drops"
echo "  rankhist_nfe*.npz             -> should get more U-shaped as NFE drops"
