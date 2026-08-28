#!/usr/bin/env bash
set -euo pipefail

GGUF=/assets/Qwen3-4B-Thinking-2507-Q4_K_M.gguf
ADAPTER_CONFIG=/workspace/dataset/qlora_adapter_v9/adapter_config.json
ADAPTER_MODEL=/workspace/dataset/qlora_adapter_v9/adapter_model.safetensors
MODEL_CONFIG=/workspace/learn_path/socratic_tutor/qwen3_4b/config.json
VTG_OUTPUT=${VTG_OUTPUT:-/workspace/dataset/eval_out_xdomain/verify_then_generate_remote.json}

check_hash() {
  local expected=$1
  local path=$2
  local actual
  actual=$(sha256sum "$path" | cut -d' ' -f1)
  if [[ "$actual" != "$expected" ]]; then
    echo "SHA256 mismatch: $path" >&2
    exit 1
  fi
}

test -f "$MODEL_CONFIG"
test -f "$ADAPTER_CONFIG"
test -f "$ADAPTER_MODEL"
test -f "$GGUF"
check_hash 7f731777c0d903ea8539d2eca6e622a487cd8abcc9471716aaa070e8ad37b90f "$ADAPTER_CONFIG"
check_hash 7004e21a3d9fb61ca7c0e6acc4cad116f7e59edf2dad4ead43299aa78c61405c "$ADAPTER_MODEL"
check_hash ddd52e18200baab281c5c46f70d544ce4d4fe4846eab1608f2fff48a64554212 "$GGUF"

mkdir -p "$OLLAMA_MODELS" "$(dirname "$VTG_OUTPUT")"
ollama serve >/tmp/daniel-vtg-ollama.log 2>&1 &
ollama_pid=$!
cleanup() {
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
if [[ "$ready" != "1" ]]; then
  tail -100 /tmp/daniel-vtg-ollama.log >&2 || true
  exit 1
fi

ollama create "$REVIEW_MODEL" -f /workspace/server_train/Modelfile.vtg
ollama show "$REVIEW_MODEL" >/dev/null

python /workspace/dataset/eval_verify_then_generate.py \
  --generate-only \
  --output "$VTG_OUTPUT"
