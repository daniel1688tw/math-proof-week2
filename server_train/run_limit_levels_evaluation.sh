#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$ROOT_DIR"

HOST=${LIMIT_LEVELS_HOST:-daniel@192.168.1.102}
TARGET=${LIMIT_LEVELS_REMOTE_DIR:-/home/daniel/daniel-limit-levels-sim/project}
KNOWN_HOSTS=${LIMIT_LEVELS_KNOWN_HOSTS:-.tmp_lab102_known_hosts}
IDENTITY_FILE=${LIMIT_LEVELS_IDENTITY_FILE:-/c/Users/Danie/.ssh/id_ed25519}
PYTHON_BIN=${LIMIT_LEVELS_PYTHON_BIN:-/c/Users/Danie/anaconda3/envs/lora_project/python.exe}
TIMEOUT_BIN=${LIMIT_LEVELS_TIMEOUT_BIN:-timeout}
SSH_BIN=${LIMIT_LEVELS_SSH_BIN:-ssh}
SCP_BIN=${LIMIT_LEVELS_SCP_BIN:-scp}
RETRY_INTERVAL=${LIMIT_LEVELS_RETRY_INTERVAL:-6}
SSH_OPTS=(
  -n -o ConnectTimeout=20 -o BatchMode=yes -o ServerAliveInterval=5
  -o "UserKnownHostsFile=$KNOWN_HOSTS" -o IdentitiesOnly=yes
  -i "$IDENTITY_FILE"
)
SCP_OPTS=(
  -o ConnectTimeout=20 -o BatchMode=yes -o ServerAliveInterval=5
  -o "UserKnownHostsFile=$KNOWN_HOSTS" -o IdentitiesOnly=yes
  -i "$IDENTITY_FILE"
)

remote() {
  "$TIMEOUT_BIN" 120 "$SSH_BIN" "${SSH_OPTS[@]}" "$HOST" "$@"
}

cleanup_done=0
cleanup() {
  if [ "$cleanup_done" -eq 1 ]; then
    return
  fi
  cleanup_done=1
  for _ in $(seq 1 6); do
    out=$(remote "bash '$TARGET/server_train/run_limit_levels_remote.sh' stop" 2>&1 || true)
    printf '%s\n' "$out"
    printf '%s' "$out" | grep -q '===STOPPED===' && return
    sleep "$RETRY_INTERVAL"
  done
  echo "REMOTE_CLEANUP_UNCONFIRMED" >&2
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for attempt in $(seq 1 6); do
  out=$(remote "mkdir -p '$TARGET/server_train/workspace' '$TARGET/dataset'; echo ===DIR_READY===" 2>&1 || true)
  printf '%s\n' "$out"
  printf '%s' "$out" | grep -q '===DIR_READY===' && break
  test "$attempt" -lt 6
  sleep "$RETRY_INTERVAL"
done

for file in \
  server_train/run_limit_levels_remote.sh \
  server_train/run_limit_levels_service.sh \
  server_train/Modelfile.vtg \
  server_train/workspace/inference_server.py; do
  destination="$TARGET/${file%/*}/"
  for attempt in $(seq 1 6); do
    out=$("$TIMEOUT_BIN" 120 "$SCP_BIN" -q "${SCP_OPTS[@]}" "$file" "$HOST:$destination" 2>&1 || true)
    printf '%s\n' "$out"
    test -z "$out" && break
    test "$attempt" -lt 6
    sleep "$RETRY_INTERVAL"
  done
done

out=$(remote '
  echo "=== GPUS ==="
  nvidia-smi --query-gpu=index,memory.used,memory.free,utilization.gpu --format=csv,noheader
  echo "=== OWN CONTAINERS ==="
  docker ps -a --filter "name=daniel-limit-levels-sim" --format "{{.Names}}|{{.Status}}"
  echo "===PREFLIGHT_DONE==="' 2>&1 || true)
printf '%s\n' "$out"
printf '%s' "$out" | grep -q '===PREFLIGHT_DONE==='

ready=0
for _ in $(seq 1 6); do
  out=$(remote "bash '$TARGET/server_train/run_limit_levels_remote.sh' start" 2>&1 || true)
  printf '%s\n' "$out"
  if printf '%s' "$out" | grep -q '===READY==='; then
    ready=1
    break
  fi
  status=$(remote "docker logs --tail 4 daniel-limit-levels-sim 2>&1 || true; bash '$TARGET/server_train/run_limit_levels_remote.sh' status" 2>&1 || true)
  printf '%s\n' "$status"
  if printf '%s' "$status" | grep -q '\[ready\]'; then
    ready=1
    break
  fi
  sleep "$RETRY_INTERVAL"
done
test "$ready" -eq 1

PYTHONNOUSERSITE=1 PYTHONUTF8=1 "$PYTHON_BIN" \
  dataset/eval_limit_levels_dual_ai.py "$@"
