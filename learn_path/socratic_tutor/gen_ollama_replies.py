"""gen_ollama_replies.py — 用 Ollama 產生兩個基準 backend 的第一輪引導回覆。

improve.md 問題⑨：compare.py 從未把「子系統 A 的思考型模型 + 好 prompt」當基準線比較。
improve.md 問題③：solution-grounded（參考解在手）引導。

本腳本產出兩個 backend 的回覆 JSON（純 Ollama，不碰 transformers）：
  * ollama_socratic — 思考型模型 + SYSTEM_SOCRATIC（零訓練成本的強基準）。
  * grounded        — 思考型模型 + 隱藏參考解（build_grounded_system）；需先跑
                      gen_reference_solutions.py 產出 eval_out/reference_solutions.json。

輸出：eval_out/replies_ollama_socratic.json、eval_out/replies_grounded.json

執行（需 Ollama 已啟動）：
  conda run -n lora_project --live-stream python gen_ollama_replies.py
  # 只產其中一個：
  python gen_ollama_replies.py socratic
  python gen_ollama_replies.py grounded
"""

from __future__ import annotations

import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ollama_client as oc
from common import STUDENT_NO_ATTEMPT_PREFIX, SYSTEM_SOCRATIC, build_grounded_system
from eval_common import load_reference_solutions, save_replies, score_form
from problems import all_eval_problems

# 與訓練分佈對齊：第一輪附「尚未嘗試」前綴（種子也含此版本）。設 WRAP=0 可改純題目。
WRAP = os.environ.get("WRAP", "1") == "1"
# 引導預算：qwen3-thinking 會先輸出長 <think>，須留足空間否則 content 空（done=length）
SOCRATIC_NUM_PREDICT = 3072
SOCRATIC_NUM_CTX = 8192


def _user_content(problem: str) -> str:
    return problem + STUDENT_NO_ATTEMPT_PREFIX if WRAP else problem


def gen_socratic(problems: list[dict], model: str) -> list[dict]:
    results = []
    print("\n=== ollama_socratic（思考型 + SYSTEM_SOCRATIC）===")
    for i, p in enumerate(problems, 1):
        messages = [
            {"role": "system", "content": SYSTEM_SOCRATIC},
            {"role": "user", "content": _user_content(p["problem"])},
        ]
        t0 = time.time()
        r = oc.chat(messages, model=model, num_predict=SOCRATIC_NUM_PREDICT,
                    num_ctx=SOCRATIC_NUM_CTX, temperature=0.7, top_p=0.9, think=True)
        a = r["content"]
        sc = score_form(a)
        results.append({"id": p["id"], "split": p["split"], "problem": p["problem"],
                        "reply": a, "elapsed": time.time() - t0, "form": sc})
        print(f"  [{i}/{len(problems)}] {p['id']}  form:{sc['total']}/5  {a[:90].replace(chr(10),' ')}…")
    return results


def gen_grounded(problems: list[dict], model: str) -> list[dict]:
    refs = load_reference_solutions()
    if not refs:
        print("[警告] 找不到 reference_solutions.json，請先跑 gen_reference_solutions.py。"
              " 略過 grounded。")
        return []
    results = []
    print("\n=== grounded（思考型 + 隱藏參考解）===")
    for i, p in enumerate(problems, 1):
        ref = refs.get(p["id"], {}).get("proof", "")
        if not ref:
            print(f"  [{i}/{len(problems)}] {p['id']} 無參考解，略過")
            continue
        messages = [
            {"role": "system", "content": build_grounded_system(ref)},
            {"role": "user", "content": _user_content(p["problem"])},
        ]
        t0 = time.time()
        r = oc.chat(messages, model=model, num_predict=SOCRATIC_NUM_PREDICT,
                    num_ctx=16384, temperature=0.7, top_p=0.9, think=True)
        a = r["content"]
        sc = score_form(a)
        results.append({"id": p["id"], "split": p["split"], "problem": p["problem"],
                        "reply": a, "elapsed": time.time() - t0, "form": sc})
        print(f"  [{i}/{len(problems)}] {p['id']}  form:{sc['total']}/5  {a[:90].replace(chr(10),' ')}…")
    return results


def main() -> None:
    if not oc.health_check():
        print(f"[錯誤] 連不上 Ollama（{oc.OLLAMA_HOST}）。請先啟動 Ollama。")
        sys.exit(1)
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    model = oc.resolve_model()
    print(f"[Ollama backends] model={model}  which={which}  WRAP={WRAP}")
    problems = all_eval_problems()

    if which in ("both", "socratic"):
        save_replies("ollama_socratic", gen_socratic(problems, model))
    if which in ("both", "grounded"):
        res = gen_grounded(problems, model)
        if res:
            save_replies("grounded", res)
    print("\n[完成] 回覆已存到 eval_out/。接著跑 score_replies.py 做 form + judge 對比。")


if __name__ == "__main__":
    main()
