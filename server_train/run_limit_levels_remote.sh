#!/usr/bin/env bash
set -euo pipefail

ACTION=${1:-status}
NAME=daniel-limit-levels-sim
PROJECT_DIR=${LIMIT_LEVELS_PROJECT_DIR:-/home/daniel/daniel-limit-levels-sim/project}
MODEL_REPO=${LIMIT_LEVELS_MODEL_REPO:-/home/daniel/qlora_8b/workspace/hf_cache/hub/models--Qwen--Qwen3-4B-Instruct-2507}
ADAPTER_DIR=${LIMIT_LEVELS_ADAPTER_DIR:-/home/daniel/qlora_8b/workspace/out/qlora_adapter_v9}
VTG_ROOT=${LIMIT_LEVELS_VTG_ROOT:-/home/daniel/daniel-vtg-eval-4ffa543}
GGUF_DIR=${LIMIT_LEVELS_GGUF_DIR:-$VTG_ROOT/gguf}
OLLAMA_MODELS_DIR=${LIMIT_LEVELS_OLLAMA_MODELS_DIR:-$VTG_ROOT/ollama_models}
READY_ATTEMPTS=${LIMIT_LEVELS_READY_ATTEMPTS:-60}
READY_INTERVAL=${LIMIT_LEVELS_READY_INTERVAL:-5}

gpu_status() {
  nvidia-smi --id=1 --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader
}

stop_owned_container() {
  if docker ps -a --filter "name=^${NAME}$" --format '{{.Names}}' | grep -qx "$NAME"; then
    docker stop -t 20 "$NAME" >/dev/null || true
  fi
}

case "$ACTION" in
  start)
    used=$(nvidia-smi --id=1 --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')
    util=$(nvidia-smi --id=1 --query-gpu=utilization.gpu --format=csv,noheader,nounits | tr -d ' ')
    printf 'GPU1_BEFORE='; gpu_status
    if [ "$used" -gt 500 ] || [ "$util" -gt 10 ]; then
      echo "GPU1_BUSY"
      exit 3
    fi
    if docker ps -a --filter "name=^${NAME}$" --format '{{.Names}}' | grep -qx "$NAME"; then
      echo "OWN_CONTAINER_EXISTS"
      exit 4
    fi
    test -f "$GGUF_DIR/Qwen3-4B-Thinking-2507-Q4_K_M.gguf"
    test -d "$OLLAMA_MODELS_DIR"
    trap stop_owned_container EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    docker run -d --rm --name "$NAME" \
      --gpus '"device=1"' --cpus 8 --memory 32g --shm-size 4g \
      -p 127.0.0.1:8899:8899 \
      -p 127.0.0.1:11435:11434 \
      -e MODEL_NAME=/modelrepo/snapshots/cdbee75f17c01a7cc42f958dc650907174af0554 \
      -e ADAPTER_DIR=/adapter -e PORT=8899 -e QUANT=4bit \
      -e REVIEW_MODEL=qwen3-4b-thinking-2507:latest \
      -e OLLAMA_HOST=0.0.0.0:11434 -e OLLAMA_MODELS=/workspace/.ollama_models \
      -e OLLAMA_NUM_PARALLEL=1 -e OLLAMA_MAX_LOADED_MODELS=1 -e OLLAMA_THINK=1 \
      -v "$MODEL_REPO:/modelrepo:ro" \
      -v "$ADAPTER_DIR:/adapter:ro" \
      -v "$GGUF_DIR:/assets:ro" \
      -v "$OLLAMA_MODELS_DIR:/workspace/.ollama_models" \
      -v /usr/local/bin/ollama:/usr/local/bin/ollama:ro \
      -v /usr/local/lib/ollama:/usr/local/lib/ollama:ro \
      -v "$PROJECT_DIR/server_train/workspace/inference_server.py:/workspace/inference_server.py:ro" \
      -v "$PROJECT_DIR/server_train/run_limit_levels_service.sh:/workspace/server_train/run_limit_levels_service.sh:ro" \
      -v "$PROJECT_DIR/server_train/Modelfile.vtg:/workspace/server_train/Modelfile.vtg:ro" \
      -w /workspace daniel-qlora-train:latest \
      bash /workspace/server_train/run_limit_levels_service.sh >/dev/null
    for _ in $(seq 1 "$READY_ATTEMPTS"); do
      if docker logs "$NAME" 2>&1 | grep -q '\[ready\]'; then
        printf 'GPU1_READY='; gpu_status
        echo "===READY==="
        trap - EXIT INT TERM
        exit 0
      fi
      if ! docker ps --filter "name=^${NAME}$" --format '{{.Names}}' | grep -qx "$NAME"; then
        docker logs "$NAME" 2>&1 || true
        exit 5
      fi
      sleep "$READY_INTERVAL"
    done
    echo "MODEL_SERVER_TIMEOUT"
    exit 6
    ;;
  status)
    docker ps -a --filter "name=^${NAME}$" --format '{{.Names}}|{{.Status}}'
    printf 'GPU1='; gpu_status
    echo "===STATUS==="
    ;;
  stop)
    stop_owned_container
    printf 'GPU1_AFTER='; gpu_status
    docker ps -a --filter "name=^${NAME}$" --format '{{.Names}}|{{.Status}}'
    echo "===STOPPED==="
    ;;
  *)
    echo "usage: $0 start|status|stop" >&2
    exit 2
    ;;
esac
