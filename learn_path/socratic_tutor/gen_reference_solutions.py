"""gen_reference_solutions.py — 用子系統 A（Ollama 思考型模型）為評估題產生「參考解」。

improve.md 問題③（solution-grounded 引導）的前置步驟：先把每題的完整證明算好、存成快取，
之後 grounded 引導層、LLM judge 都從快取讀，不必每次重算，也避免 transformers 與 Ollama
同時佔用 6GB GPU（本流程純 Ollama）。

輸出：eval_out/reference_solutions.json
  { "<problem_id>": {"problem": ..., "proof": ..., "truncated": bool, "model": ...}, ... }

可重跑（已存在且非空的 id 預設略過；設 FORCE=1 可全部重算）。

執行（需 Ollama 已啟動且已 pull 模型）：
  conda run -n lora_project --live-stream python gen_reference_solutions.py
"""

from __future__ import annotations

import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ollama_client as oc
from eval_common import OUT_DIR  # honors EVAL_SET（eval_out 或 eval_out/v4）
from problems import all_eval_problems

OUT_PATH = os.path.join(OUT_DIR, "reference_solutions.json")
FORCE = os.environ.get("FORCE", "0") == "1"


def _load() -> dict:
    if os.path.exists(OUT_PATH):
        try:
            return json.load(open(OUT_PATH, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    if not oc.health_check():
        print(f"[錯誤] 連不上 Ollama（{oc.OLLAMA_HOST}）。請先啟動 Ollama 並 pull 模型。")
        sys.exit(1)

    model = oc.resolve_model()
    print(f"[參考解] model={model}  輸出={OUT_PATH}  FORCE={FORCE}")
    data = _load()
    problems = all_eval_problems()

    for i, p in enumerate(problems, 1):
        pid = p["id"]
        if not FORCE and data.get(pid, {}).get("proof"):
            print(f"  [{i}/{len(problems)}] {pid} 已有參考解，略過")
            continue
        print(f"  [{i}/{len(problems)}] {pid} 產生中…", flush=True)
        t0 = time.time()
        try:
            r = oc.generate_proof(p["problem"], model=model)
        except Exception as e:
            print(f"     ✗ 失敗：{e}")
            continue
        data[pid] = {
            "problem": p["problem"],
            "proof": r["proof"],
            "truncated": r["truncated"],
            "model": r["model"],
            "split": p["split"],
        }
        _save(data)  # 每題即存，可中斷續跑
        flag = "（截斷續寫）" if r["truncated"] else ""
        print(f"     ✓ {len(r['proof'])} 字 / {time.time()-t0:.0f}s {flag}")

    print(f"\n[完成] 共 {len(data)} 題參考解 → {OUT_PATH}")


if __name__ == "__main__":
    main()
