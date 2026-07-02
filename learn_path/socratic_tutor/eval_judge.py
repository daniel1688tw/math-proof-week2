"""eval_judge.py — LLM-as-judge：評「引導回覆」的教學品質（improve.md 問題②）。

原本 compare.py 的 score_socratic 只量形式（有問號 / 字數 / 含術語 / 非完整證明），
一個「形式漂亮但內容空泛或錯誤」的問句也能拿滿分 → 形式分高 ≠ 助教好。

本模組用一個 LLM（預設本機 Ollama，可用 JUDGE_MODEL 覆寫）依 rubric 評 5 個維度，
並把**參考解**一併提供給 judge，讓它能判斷「引導是否在數學上正確、指向正確下一步」。

  rubric（每項 0–2，總分 0–10）：
    correct        — 引導中的數學陳述/暗示對「這道題」是否正確（最重要）
    relevant       — 是否針對這題的關鍵定義/定理/技巧（而非泛泛）
    advances       — 是否推進「具體一步」（而非空泛的 "describe your approach"）
    no_leak        — 是否沒有洩漏完整解法/最終答案
    single_focused — 是否大致只問一個聚焦的問題（不轟炸）

⚠️ judge 品質受限於 judge 模型。4B 評 4B 偏弱但仍優於純形式分；建議用較強模型當 judge：
   設環境變數 JUDGE_MODEL=qwen3:8b（或更強），或改接 API。
"""

from __future__ import annotations

import json
import os
import re

import ollama_client as oc

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "")  # 空 → 用 resolve_model()

_RUBRIC = (
    "You are a strict grader of Socratic math tutoring. You are given a PROBLEM, a "
    "correct REFERENCE SOLUTION (ground truth), and a TUTOR REPLY (the tutor's first "
    "guiding message to a student who just received the problem). The tutor is SUPPOSED "
    "to ask a short leading question that nudges the student one step forward WITHOUT "
    "giving away the solution.\n\n"
    "Grade the TUTOR REPLY on five criteria, each an integer 0, 1, or 2:\n"
    "  correct: Are the mathematical claims/hints in the reply correct FOR THIS PROBLEM "
    "(consistent with the reference solution)? 2=fully correct, 1=minor imprecision, "
    "0=wrong or misleading.\n"
    "  relevant: Does it target the key definition/theorem/technique this problem needs "
    "(per the reference)? 2=spot on, 1=loosely related, 0=off-target or generic.\n"
    "  advances: Does it push one concrete next step? 2=concrete & actionable, "
    "1=somewhat vague, 0=empty/generic (e.g. 'walk me through your approach').\n"
    "  no_leak: Does it withhold the full solution and final answer? 2=no leak, "
    "1=hints a bit too much, 0=basically gives the solution/answer.\n"
    "  single_focused: Is it essentially ONE focused question (not a barrage)? "
    "2=one focused question, 1=two questions, 0=many or none.\n\n"
    "Respond with ONLY a JSON object, no prose, exactly:\n"
    '{\"correct\":N,\"relevant\":N,\"advances\":N,\"no_leak\":N,\"single_focused\":N,'
    '\"rationale\":\"one short sentence\"}'
)


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        # 容錯：抓出各鍵的數字
        out = {}
        for k in ("correct", "relevant", "advances", "no_leak", "single_focused"):
            mk = re.search(rf'"{k}"\s*:\s*([0-2])', text)
            if mk:
                out[k] = int(mk.group(1))
        return out or None


def judge_reply(problem: str, reference: str, reply: str,
                model: str | None = None) -> dict:
    """回傳 {correct, relevant, advances, no_leak, single_focused, total, rationale}。"""
    model = model or (JUDGE_MODEL or oc.resolve_model())
    ref = reference.strip() or "(no reference solution available)"
    user = (
        f"PROBLEM:\n{problem}\n\n"
        f"REFERENCE SOLUTION (ground truth, the student cannot see this):\n{ref}\n\n"
        f"TUTOR REPLY:\n{reply}\n\n"
        "Now grade the TUTOR REPLY as instructed."
    )
    messages = [{"role": "system", "content": _RUBRIC},
                {"role": "user", "content": user}]
    # ⚠️ qwen3-thinking 永遠先輸出長 <think> 再給 content；預算須夠大否則 JSON 被截成空。
    resp = oc.chat(messages, model=model, num_predict=4096, num_ctx=8192,
                   temperature=0.0, top_p=0.9, think=True)
    parsed = _extract_json(resp["content"]) or {}
    keys = ("correct", "relevant", "advances", "no_leak", "single_focused")
    scores = {k: int(parsed.get(k, 0)) for k in keys}
    scores["total"] = sum(scores[k] for k in keys)
    scores["rationale"] = str(parsed.get("rationale", ""))[:200]
    scores["judge_model"] = model
    return scores


if __name__ == "__main__":
    # 小型自測：給一個明顯好/壞的回覆，看 judge 是否區分
    prob = "Prove that lim_{x->2} x^2 = 4 using the epsilon-delta definition."
    ref = ("Given eps>0, choose delta=min(1, eps/5). For |x-2|<delta, |x+2|<5 and "
           "|x^2-4|=|x-2||x+2|<5*delta<=eps.")
    good = ("To start an epsilon-delta proof, can you factor |x^2 - 4| as "
            "|x-2|*|x+2|, and then think about how to bound |x+2| when x is near 2?")
    bad = "Sure! The answer is that the limit equals 4. Here is the full proof: ..."
    if not oc.health_check():
        print("Ollama 未啟動，略過自測。")
    else:
        print("GOOD:", judge_reply(prob, ref, good))
        print("BAD :", judge_reply(prob, ref, bad))
