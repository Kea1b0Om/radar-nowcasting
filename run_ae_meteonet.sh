#!/bin/bash
# Supervise the MeteoNet autoencoder-KL run.  This is the latent-space stage the
# MeteoNet FlowCast/UOT-v4 run will later load its frozen encoder from.
set -u

PROJECT_DIR=${PROJECT_ROOT}
PY_DIR=${CONDA_ROOT}/envs/torch/bin
CONFIG=experiments/meteonet/autoencoder/autoencoder_kl_config.yaml
SUPERVISOR_LOG=logs/supervisor_ae_meteonet.log
MASTER_PORT=29619
child_pid=""

cd "$PROJECT_DIR" || exit 1
mkdir -p logs artifacts/meteonet/autoencoder_kl
echo $$ > logs/ae_meteonet_supervisor.pid

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

  run_log="logs/ae_meteonet_$(date +%Y%m%d_%H%M%S).log"
  echo "$(date) attempt $attempt starting -> $run_log" >> "$SUPERVISOR_LOG"

  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    "$PY_DIR/torchrun" --nproc_per_node=3 --master_port="$MASTER_PORT" \
    experiments/sevir/autoencoder/dist_train_autoencoder_kl.py \
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
