"""gen_seed_references.py — 為 10 題訓練種子產出「簡短參考解」（grounded 訓練範例用）。

修正「訓練沒在 grounding 下做」的分佈不一致：要讓微調模型學會「讀 <reference> → 問引導
問句、不洩漏」，訓練資料就得包含 grounded 範例。但 MAX_LEN=512 下參考解必須夠短，否則
連同精簡 system + 對話會超出 512。故這裡請思考型模型產出 ≤90 字的精簡解題綱要。

輸出：seed_references.json  { "<seed_id>": "<concise outline>", ... }

執行（需 Ollama）：
  conda run -n lora_project --live-stream python gen_seed_references.py
"""

from __future__ import annotations

import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ollama_client as oc
from problems import CALCULUS_SEEDS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "seed_references.json")

_PROMPT = (
    "Give a CONCISE solution outline for the following problem: state the key idea "
    "and the main steps in at most 90 words. Be mathematically correct and specific "
    "(name the theorem/technique). Do NOT write a full formal proof; just the outline."
)


def main() -> None:
    if not oc.health_check():
        print(f"[錯誤] 連不上 Ollama（{oc.OLLAMA_HOST}）。"); sys.exit(1)
    model = oc.resolve_model()
    print(f"[種子參考解] model={model}")
    out: dict = {}
    if os.path.exists(OUT_PATH):
        out = json.load(open(OUT_PATH, encoding="utf-8"))
    for i, (pid, problem, _ideal) in enumerate(CALCULUS_SEEDS, 1):
        if out.get(pid):
            print(f"  [{i}/10] {pid} 已有，略過"); continue
        r = oc.chat(
            [{"role": "system", "content": _PROMPT},
             {"role": "user", "content": f"Problem: {problem}"}],
            model=model, num_predict=6144, num_ctx=8192, temperature=0.3, think=True)
        ref = r["content"].strip()
        out[pid] = ref
        json.dump(out, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"  [{i}/10] {pid}: {len(ref.split())} 字  {ref[:80]}…")
    print(f"\n[完成] {len(out)} 題 → {OUT_PATH}")


if __name__ == "__main__":
    main()
