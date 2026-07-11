"""
run_smoke_4b.py — 冒煙測試 Qwen3-4B-Thinking-2507（本機 lora_project）

只跑 test_problems_v3.json 的第 1 題，確認：
  (a) transformers 5.x 能否在 Windows + bnb 4-bit 順利載入 4B（不 segfault）
  (b) <think> 區塊切除是否正常
  (c) 證明品質長怎樣

執行：
    conda run -n lora_project --live-stream python run_smoke_4b.py
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import simple_4B  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "test_problems_v3.json"), "r", encoding="utf-8") as f:
    problems = json.load(f)

prob = problems[0]
print(f"[smoke] problem_id = {prob['problem_id']}", flush=True)
print(f"[smoke] raw_problem = {prob['raw_problem']}", flush=True)
print("[smoke] loading + generating (first run downloads ~8GB) ...", flush=True)

t0 = time.time()
try:
    result = simple_4B.run_simple_4b(prob["raw_problem"], return_thinking=True)
except Exception as exc:
    print(f"[smoke] FAILED: {exc!r}", flush=True)
    raise
elapsed = time.time() - t0

reasoning = result["reasoning"]
answer = result["answer"]

print("\n" + "=" * 70, flush=True)
print(f"[smoke] OK — loaded and generated in {elapsed:.1f}s", flush=True)
print(f"[smoke] thinking length : {len(reasoning)} chars", flush=True)
print(f"[smoke] answer length   : {len(answer)} chars", flush=True)
print(f"[smoke] think-strip OK  : {'yes' if reasoning else 'NO (no </think> split)'}", flush=True)
print("=" * 70, flush=True)
print("\n---------------- THINKING (first 800 chars) ----------------", flush=True)
print(reasoning[:800], flush=True)
print("\n---------------- FINAL ANSWER (proof) ----------------", flush=True)
print(answer, flush=True)

# Persist for inspection
with open(os.path.join(HERE, "smoke_4b_output.txt"), "w", encoding="utf-8") as f:
    f.write(f"problem_id: {prob['problem_id']}\nelapsed: {elapsed:.1f}s\n")
    f.write(f"thinking_chars: {len(reasoning)}\nanswer_chars: {len(answer)}\n")
    f.write("\n==== THINKING ====\n")
    f.write(reasoning)
    f.write("\n\n==== FINAL ANSWER ====\n")
    f.write(answer)
print("\n[smoke] wrote smoke_4b_output.txt", flush=True)
