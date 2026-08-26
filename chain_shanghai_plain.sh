#!/bin/bash
# Wait for the Shanghai UOT arm to finish, then start its plain twin.
#
#   setsid nohup ./chain_shanghai_plain.sh > logs/chain_shanghai_plain.log 2>&1 < /dev/null &
#
# Why chained rather than concurrent: the two arms must run on the SAME three
# GPUs with the same world_size (DistributedSampler partitions by world_size,
# and randn shapes follow the micro batch), so a matched-seed twin cannot
# share cards with its sibling -- and at ~30 GB (UOT) + ~20 GB (plain) they
# would not fit on one 48 GB card anyway.
#
# Why wait for natural early stopping rather than killing the UOT arm: both
# arms must be governed by the identical stopping rule (patience 50 on
# partial_csi_m). Truncating one by hand would make the pair incomparable
# even though its best checkpoint is already frozen.
set -u

cd ${PROJECT_ROOT} || exit 1

echo "[$(date +%F_%T)] waiting for the UOT arm to exit..."
while pgrep -f "dist_train_flowcast[.]py" > /dev/null; do
    sleep 60
done
echo "[$(date +%F_%T)] UOT arm has exited."

# Record how the UOT arm ended, so the twin's stopping condition is auditable.
grep -a "Early stopping triggered\|Finished training\|Early Stopping counter" \
    logs/shanghai_uot.log | tail -3

# The plain arm must start from scratch: a stale checkpoint would resume it
# mid-trajectory with a different RNG stream and break the pairing.
rm -f artifacts/shanghai/flowcast/shanghai_plain_latest.pt

sleep 30  # let the cards release their memory

echo "[$(date +%F_%T)] launching the plain twin on GPUs 0,1,2"
./run_shanghai.sh plain 0,1,2 29731 > logs/shanghai_plain.log 2>&1
echo "[$(date +%F_%T)] plain arm exited."
