#!/bin/bash
# Supervise the clean UOT-v4 CIKM run.  The unique v4 checkpoint path means
# attempt 1 starts from random weights; retries resume v4 only.
set -u

PROJECT_DIR=${PROJECT_ROOT}
PY_DIR=${CONDA_ROOT}/envs/torch/bin
CONFIG=experiments/cikm/runner/flowcast/flowcast_config_uot_v4_clean.yaml
SUPERVISOR_LOG=logs/supervisor_uot_v4_clean.log
MASTER_PORT=29618
child_pid=""

cd "$PROJECT_DIR" || exit 1
mkdir -p logs artifacts/cikm/flowcast
echo $$ > logs/uot_v4_clean_supervisor.pid

terminate_child() {
  if [ -n "$child_pid" ] && kill -0 "$child_pid" 2>/dev/null; then
    kill -TERM "$child_pid"
    wait "$child_pid"
  fi
  exit 143
}
trap terminate_child TERM INT

for attempt in $(seq 1 40); do
  if ! nvidia-smi >/dev/null 2>&1; then
    echo "$(date) CUDA driver unresponsive; aborting (reboot needed)" >> "$SUPERVISOR_LOG"
    exit 1
  fi

  run_log="logs/uot_v4_clean_cikm_$(date +%Y%m%d_%H%M%S).log"
  echo "$(date) attempt $attempt starting -> $run_log" >> "$SUPERVISOR_LOG"

  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    "$PY_DIR/torchrun" --nproc_per_node=3 --master_port="$MASTER_PORT" \
    experiments/sevir/runner/flowcast/dist_train_flowcast.py \
    --config "$CONFIG" >"$run_log" 2>&1 &
  child_pid=$!
  wait "$child_pid"
  code=$?
  child_pid=""

  echo "$(date) attempt $attempt exited code=$code" >> "$SUPERVISOR_LOG"
  if [ "$code" -eq 0 ]; then
    echo "$(date) training finished cleanly" >> "$SUPERVISOR_LOG"
    break
  fi
  sleep 120
done
