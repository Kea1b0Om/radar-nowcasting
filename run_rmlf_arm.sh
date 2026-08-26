#!/bin/bash
# Supervise one RMLF arm.  Usage:
#
#   bash run_rmlf_arm.sh r0        # teacher forcing control
#   bash run_rmlf_arm.sh r1        # detached self forcing
#   bash run_rmlf_arm.sh r2        # anchored rollout bridge
#   bash run_rmlf_arm.sh r2g       # grid control: r3's grid + marginals,
#                                  # independent -- the arm r3 must beat
#   bash run_rmlf_arm.sh r3        # interaction-coupled bridge
#
# Run them in that order.  R3 must not be launched before the estimator's
# interaction heat map has been inspected, and its claim is R3 > R2G, not
# R3 > R2 (see docs/RMLF_IMPLEMENTATION.md).
#
# Every arm continues from the SAME parent checkpoint for the SAME budget, so
# each one gets its own resume path and its own master port; nothing else
# differs.  This script deliberately does not overwrite run_uot_v4_clean.sh.
#
# MAX_ATTEMPTS defaults to 1 ON PURPOSE.  The latest checkpoint does not carry
# the GradScaler, the Python/NumPy/Torch/CUDA RNG, the intra-epoch batch index
# or the DataLoader worker state, and resume restarts at `checkpoint_epoch+1`.
# So a mid-epoch crash silently drops the rest of that epoch and resets the
# base RF noise stream -- the four RMLF streams still match, but the ARM no
# longer saw the same data or the same randomness as its siblings, and the
# paired comparison is void.  If an arm dies, discard that round's four-arm
# comparison and re-run all of them from the same parent.
#
#   MAX_ATTEMPTS=40 bash run_rmlf_arm.sh r2    # exploratory only, NOT for
#                                              # a reported paired result
set -u

ARM=${1:?usage: run_rmlf_arm.sh ARM, where ARM is r0, r1, r2, r2g or r3}
case "$ARM" in
  r0|r1|r2|r2g|r3) ;;
  *) echo "unknown arm: $ARM (expected r0, r1, r2, r2g or r3)" >&2; exit 2 ;;
esac

PROJECT_DIR=${PROJECT_DIR:-${PROJECT_ROOT}}
PY_DIR=${PY_DIR:-${CONDA_ROOT}/envs/torch/bin}
CONFIG=experiments/cikm/runner/flowcast/flowcast_config_rmlf_${ARM}.yaml
SUPERVISOR_LOG=logs/supervisor_rmlf_${ARM}.log
NPROC=${NPROC:-3}
# 1 = a reported paired run must be a single uninterrupted process.
MAX_ATTEMPTS=${MAX_ATTEMPTS:-1}
# Distinct port per arm so two arms can be queued without colliding.
case "$ARM" in
  r0) DEFAULT_PORT=29640 ;;
  r1) DEFAULT_PORT=29641 ;;
  r2) DEFAULT_PORT=29642 ;;
  r2g) DEFAULT_PORT=29644 ;;
  r3) DEFAULT_PORT=29643 ;;
esac
MASTER_PORT=${MASTER_PORT:-$DEFAULT_PORT}
child_pid=""

cd "$PROJECT_DIR" || exit 1

# Every PARENT_* placeholder must be resolved.  Leaving even one behind means
# either the arm points at the wrong parent, trains zero epochs, or ramps its
# warmup from the wrong origin -- all silent, all fatal to the comparison.
if grep -nE 'PARENT_(CHECKPOINT_ABSOLUTE_PATH|EPOCH_PLUS_14|GLOBAL_STEP)' "$CONFIG" \
     | grep -v '^[0-9]*:#' >/dev/null; then
  echo "ERROR: $CONFIG still has unresolved PARENT_* placeholders:" >&2
  grep -nE 'PARENT_(CHECKPOINT_ABSOLUTE_PATH|EPOCH_PLUS_14|GLOBAL_STEP)' "$CONFIG" \
    | grep -v '^[0-9]*:#' >&2
  echo >&2
  echo "Set them in ALL four arm configs from the same parent checkpoint:" >&2
  echo "  PARENT_CHECKPOINT_ABSOLUTE_PATH -> the shared parent .pt" >&2
  echo "  PARENT_EPOCH_PLUS_14            -> parent['epoch'] + 1 + 13" >&2
  echo "  PARENT_GLOBAL_STEP              -> parent['global_step']" >&2
  echo "and record the parent's sha256." >&2
  exit 3
fi

# The parent must exist as a file.  Without this the trainer would go through
# its checkpoint-load path, and although strict continuation now fails closed,
# catching it here costs nothing and gives a clearer message.
PARENT=$(grep -E '^\s*preload_model:' "$CONFIG" | head -1 | sed -E 's/.*preload_model:[[:space:]]*"?([^"#]*)"?.*/\1/' | xargs)
if [ -z "$PARENT" ] || [ "$PARENT" = "null" ]; then
  echo "ERROR: $CONFIG has no run_params.preload_model" >&2
  exit 4
fi
if [ ! -f "$PARENT" ]; then
  echo "ERROR: parent checkpoint not found: $PARENT" >&2
  exit 4
fi

# A stale arm-latest silently overrides preload_model, so the run would resume
# a PREVIOUS attempt instead of starting this arm from the shared parent.  For
# a reported paired run that must be an explicit decision.
LATEST=$(grep -E '^\s*resume_latest_path:' "$CONFIG" | head -1 | sed -E 's/.*resume_latest_path:[[:space:]]*"?([^"#]*)"?.*/\1/' | xargs)
if [ -n "$LATEST" ] && [ -f "$LATEST" ] && [ "${ALLOW_RESUME:-0}" != "1" ]; then
  echo "ERROR: $LATEST already exists." >&2
  echo "It would override preload_model and resume a previous attempt of this" >&2
  echo "arm rather than starting from the shared parent.  Either archive it," >&2
  echo "or set ALLOW_RESUME=1 if resuming really is what you want (and accept" >&2
  echo "that this arm is then no longer a clean matched continuation)." >&2
  exit 5
fi

mkdir -p logs artifacts/cikm/flowcast
echo $$ > "logs/rmlf_${ARM}_supervisor.pid"

terminate_child() {
  if [ -n "$child_pid" ] && kill -0 "$child_pid" 2>/dev/null; then
    kill -TERM "$child_pid"
    wait "$child_pid"
  fi
  exit 143
}
trap terminate_child TERM INT

finished=0
last_code=1
for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  if ! nvidia-smi >/dev/null 2>&1; then
    echo "$(date) CUDA driver unresponsive; aborting (reboot needed)" >> "$SUPERVISOR_LOG"
    exit 1
  fi

  run_log="logs/rmlf_${ARM}_cikm_$(date +%Y%m%d_%H%M%S).log"
  echo "$(date) attempt $attempt/$MAX_ATTEMPTS arm=$ARM config=$CONFIG -> $run_log" >> "$SUPERVISOR_LOG"

  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    "$PY_DIR/torchrun" --nproc_per_node="$NPROC" --master_port="$MASTER_PORT" \
    experiments/sevir/runner/flowcast/dist_train_flowcast.py \
    --config "$CONFIG" >"$run_log" 2>&1 &
  child_pid=$!
  wait "$child_pid"
  code=$?
  child_pid=""
  last_code=$code

  echo "$(date) attempt $attempt exited code=$code" >> "$SUPERVISOR_LOG"
  if [ "$code" -eq 0 ]; then
    echo "$(date) arm $ARM finished cleanly" >> "$SUPERVISOR_LOG"
    finished=1
    break
  fi
  if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
    echo "$(date) WARNING: restarting arm $ARM after a crash.  This arm is no" >> "$SUPERVISOR_LOG"
    echo "$(date) longer a valid matched continuation; exploratory use only." >> "$SUPERVISOR_LOG"
    sleep 120
  fi
done

if [ "$finished" -ne 1 ]; then
  echo "$(date) arm $ARM FAILED after $MAX_ATTEMPTS attempt(s), code=$last_code" >> "$SUPERVISOR_LOG"
  echo "arm $ARM failed (last exit code $last_code); see $SUPERVISOR_LOG" >&2
  exit "$last_code"
fi
