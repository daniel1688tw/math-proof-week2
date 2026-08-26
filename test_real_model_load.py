# -*- coding: utf-8 -*-
"""驗證本地真實 GPU 載入 Qwen3-4B + QLoRA adapter 進行即時推論。"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTHONNOUSERSITE", "1")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / "dataset" / "qlora_adapter_new"

print(f"Base model dir: {MODEL_DIR} (exists: {MODEL_DIR.exists()})")
print(f"Adapter dir: {ADAPTER_DIR} (exists: {ADAPTER_DIR.exists()})")

print("正在載入 Tokenizer...")
tok = AutoTokenizer.from_pretrained(str(MODEL_DIR))
if tok.pad_token_id is None:
    tok.pad_token = tok.eos_token

print("正在載入 4-bit 基底模型到 GPU (device_map={'': 0})...")
bnb = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

t0 = time.time()
model = AutoModelForCausalLM.from_pretrained(
    str(MODEL_DIR),
    quantization_config=bnb,
    device_map={"": 0},
    torch_dtype=torch.bfloat16,
)
print(f"✓ 4-bit 基底模型載入完成，耗時 {time.time()-t0:.1f}s")
if torch.cuda.is_available():
    print(f"  VRAM 已用: {torch.cuda.memory_allocated()/1024**3:.2f} GiB")

print("正在掛載 QLoRA adapter 權重 (device_map={'': 0})...")
model = PeftModel.from_pretrained(model, str(ADAPTER_DIR), device_map={"": 0})
model.eval()
print("✓ QLoRA adapter 掛載成功！")

# 煙霧測試生成
msgs = [
    {"role": "system", "content": "你是蘇格拉底助教。請只問一個聚焦問題。"},
    {"role": "user", "content": "我不知道怎麼開始。"}
]
enc = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True).to(model.device)
with torch.no_grad():
    out = model.generate(**enc, max_new_tokens=60, do_sample=False)
reply = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
print(f"\n模型煙霧測試即時生成結果:\n{reply}\n")
