"""guided_tutor.py — Solution-grounded 蘇格拉底助教（improve.md 問題③的互動實作）。

把「會解」與「會教」解耦：
  1. 先用子系統 A（Ollama 思考型模型）產出完整證明 → 當「參考解 / 答案卡」（學生看不到）。
  2. 引導層用 build_grounded_system(參考解) 當 system prompt，多輪只問引導問句、不洩漏答案。
     老師「知道答案」才問得出指向正確下一步的問題，避免 4B 自信給錯提示。

全程走 Ollama（純 HTTP，不碰 transformers），單一模型常駐即可，無 GPU 競爭。

用法（需 Ollama 已啟動）：
  # 互動多輪（quit 離開、reset 換題）
  conda run -n lora_project --live-stream python guided_tutor.py
  # 單題起手（直接給題目，看第一個引導問句）
  python guided_tutor.py "Prove that lim_{x->2} x^2 = 4 using epsilon-delta."

環境變數：
  SHOW_REF=1  在終端印出參考解（debug 用；正常不顯示，避免誤以為要給學生看）
"""

from __future__ import annotations

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ollama_client as oc
from common import STUDENT_NO_ATTEMPT_PREFIX, build_grounded_system

SHOW_REF = os.environ.get("SHOW_REF", "0") == "1"


def make_reference(problem: str, model: str) -> str:
    print("  [1/2] 產生參考解（答案卡，學生看不到）…", flush=True)
    r = oc.generate_proof(problem, model=model)
    if SHOW_REF:
        print("\n----- 參考解（debug）-----\n" + r["proof"] + "\n--------------------------\n")
    elif r["truncated"]:
        print("  （參考解曾截斷、已自動續寫）")
    return r["proof"]


def tutor_turn(system: str, history: list[dict], model: str) -> str:
    """history：[{role: user/assistant, content}]（已含本輪學生 user）。回老師引導問句。"""
    msgs = [{"role": "system", "content": system}] + history
    r = oc.chat(msgs, model=model, num_predict=4096, num_ctx=16384,
                temperature=0.7, top_p=0.9, think=True)
    return r["content"]


def _run_session(problem: str, model: str) -> None:
    ref = make_reference(problem, model)
    system = build_grounded_system(ref)
    print("  [2/2] 進入引導對話。\n")
    # 首輪：學生剛收到題目、尚未嘗試
    history = [{"role": "user", "content": problem + STUDENT_NO_ATTEMPT_PREFIX}]
    first = tutor_turn(system, history, model)
    history.append({"role": "assistant", "content": first})
    print(f"Tutor: {first}\n")
    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not user or user.lower() in {"quit", "exit", "q"}:
            break
        history.append({"role": "user", "content": user})
        ans = tutor_turn(system, history, model)
        history.append({"role": "assistant", "content": ans})
        print(f"Tutor: {ans}\n")


def main() -> None:
    if not oc.health_check():
        print(f"[錯誤] 連不上 Ollama（{oc.OLLAMA_HOST}）。請先啟動 Ollama。")
        sys.exit(1)
    model = oc.resolve_model()
    args = sys.argv[1:]
    print(f"Solution-grounded 蘇格拉底助教  (model={model})\n")

    if args:  # 單題起手
        problem = " ".join(args)
        ref = make_reference(problem, model)
        system = build_grounded_system(ref)
        history = [{"role": "user", "content": problem + STUDENT_NO_ATTEMPT_PREFIX}]
        print("\nTutor:", tutor_turn(system, history, model))
        return

    print("（互動模式：輸入題目開始；對話中 quit 離開、reset 換新題）\n")
    while True:
        try:
            problem = input("Enter problem: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not problem or problem.lower() in {"quit", "exit", "q"}:
            break
        _run_session(problem, model)
        print("─" * 60 + "\n")


if __name__ == "__main__":
    main()
