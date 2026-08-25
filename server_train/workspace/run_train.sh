#!/bin/bash
# 容器入口：訓練 → 煙霧測試。所有輸出寫 /workspace/out/。
set -e
mkdir -p /workspace/out
echo "=== 環境 ==="
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
echo "=== 訓練 Qwen3-8B QLoRA ==="
python train_qlora.py 2>&1 | tee /workspace/out/train.log
echo "=== 煙霧測試 ==="
python smoke_test.py 2>&1 | tee /workspace/out/smoke.log
echo "=== 全部完成 ==="
