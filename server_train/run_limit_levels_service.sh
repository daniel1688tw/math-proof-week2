#!/usr/bin/env bash
set -euo pipefail

OLLAMA_LOG=/tmp/daniel-limit-levels-ollama.log
INFERENCE_LOG=/tmp/daniel-limit-levels-inference.log

ollama serve >"$OLLAMA_LOG" 2>&1 &
ollama_pid=$!
inference_pid=""

cleanup() {
  if [ -n "$inference_pid" ]; then
    kill "$inference_pid" 2>/dev/null || true
    wait "$inference_pid" 2>/dev/null || true
  fi
  kill "$ollama_pid" 2>/dev/null || true
  wait "$ollama_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

ready=0
for _ in $(seq 1 60); do
  if ollama list >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  tail -100 "$OLLAMA_LOG" >&2 || true
  exit 10
fi

if ! ollama show "$REVIEW_MODEL" >/dev/null 2>&1; then
  ollama create "$REVIEW_MODEL" -f /workspace/server_train/Modelfile.vtg
fi

python /workspace/inference_server.py >"$INFERENCE_LOG" 2>&1 &
inference_pid=$!
ready=0
for _ in $(seq 1 120); do
  if grep -q '\[ready\]' "$INFERENCE_LOG"; then
    ready=1
    break
  fi
  if ! kill -0 "$inference_pid" 2>/dev/null; then
    cat "$INFERENCE_LOG" >&2 || true
    exit 11
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  tail -100 "$INFERENCE_LOG" >&2 || true
  exit 12
fi

echo "[ready] 4-bit tutor + thinking reviewer"
wait "$inference_pid"
