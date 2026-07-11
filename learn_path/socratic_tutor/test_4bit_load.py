"""
test_4bit_load.py — 下載 Qwen3-4B-Instruct-2507 並測試「4-bit nf4 載入 + 一次推論」。

目的：CLAUDE.md 警告 transformers 5.x 在 Windows + bitsandbytes 4-bit 載入 7B 模型時，
新版 core_model_loading 的 ThreadPoolExecutor 會 segfault。4B 未驗證過，所以在投入
完整訓練前，先用這支小腳本確認 4B 能否安全 4-bit 載入並產生一段文字。

若這支會 segfault（Python 直接崩潰、沒有 traceback），代表 4B 也中招，再來想對策；
若能印出 "[OK] 推論成功"，表示 4-bit 訓練路徑可行，且模型權重也已快取好。

執行：
  conda run -n lora_project --live-stream python test_4bit_load.py
"""

from __future__ import annotations

import os
import sys
import time

# 盡量降低觸發 ThreadPoolExecutor segfault 的機率：限制執行緒
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTHONNOUSERSITE", "1")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from common import MODEL_NAME

print(f"transformers 載入 {MODEL_NAME}（4-bit nf4）…", flush=True)
print(f"  torch={torch.__version__} cuda={torch.cuda.is_available()}", flush=True)

t0 = time.time()
tok = AutoTokenizer.from_pretrained(MODEL_NAME)

bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=bnb,
    device_map={"": 0},          # 整顆放 GPU0；避免 auto 切到 CPU
    torch_dtype=torch.bfloat16,
)
model.eval()
print(f"  載入完成，耗時 {time.time()-t0:.1f}s", flush=True)
if torch.cuda.is_available():
    print(f"  VRAM 已用 {torch.cuda.memory_allocated()/1024**3:.2f} GiB", flush=True)

# 一次極短推論，確認 forward/generate 正常
messages = [
    {"role": "system", "content": "你是蘇格拉底式數學助教，每次只問一個引導問題。"},
    {"role": "user", "content": "I need to prove that the function f(x)=x^2 is continuous at x=2. Where do I start?"},
]
enc = tok.apply_chat_template(
    messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
).to(model.device)

with torch.no_grad():
    out = model.generate(**enc, max_new_tokens=80, do_sample=False)
text = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)

print("\n[模型回覆預覽]\n" + text.strip()[:400], flush=True)
print("\n[OK] 4-bit 載入 + 推論成功，可進行訓練。", flush=True)
