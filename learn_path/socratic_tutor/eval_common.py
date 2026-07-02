"""eval_common.py — 評估流程共用工具：形式評分 + 回覆 JSON 讀寫。

評估流程刻意分成「生成回覆 → 存 JSON → 評分」三階段，避免 transformers 模型常駐時
與 Ollama（form 無關，但 judge 用）同時搶 6GB GPU。各 backend 的第一輪回覆都存成
eval_out/replies_<backend>.json，再由 score_replies.py 統一做 form + judge 評分。

回覆 JSON 格式：
  { "backend": "<name>",
    "results": [ {"id":..., "split":"held"|"seed", "problem":..., "reply":...,
                  "elapsed": float}, ... ] }
"""

from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
# EVAL_SET 子資料夾隔離不同題集的產物（預設 eval_out/；EVAL_SET=v4 → eval_out/v4/）。
OUT_DIR = os.path.join(HERE, "eval_out", os.environ.get("EVAL_SET", "").strip())

# ── 形式評分（保留舊 score_socratic 的 5 項，當「快速、零成本」的 sanity 指標）──────
CALCULUS_TERMS = [
    "limit", "continuous", "continuity", "differentiable", "derivative",
    "integral", "sequence", "convergent", "converges", "cauchy",
    "mean value", "mvt", "intermediate value", "ivt", "epsilon", "delta",
    "bounded", "monotone", "uniform", "fixed point", "contraction", "periodic",
    "supremum", "infimum", "sup", "closed", "open interval", "induction",
    "series", "rolle", "lipschitz",
]
PROOF_DONE_PATTERNS = [
    r"therefore.{0,60}(proved|proven|complete|done|qed|follows)",
    r"we have (shown|proved|proven|demonstrated)",
    r"this (completes|concludes) the proof",
    r"q\.?\s*e\.?\s*d",
    r"\bproof\.?\s*\n",
    r"(?:step\s*1|step1).*\n.*(?:step\s*2|step2).*\n.*(?:step\s*3|step3)",
    r"since.*therefore.*converges",
]


def score_form(response: str) -> dict:
    """形式評分（0–5）。注意：只量形式，不代表教學品質（品質見 eval_judge）。"""
    text = response.strip()
    text_lower = text.lower()
    word_count = len(text.split())
    question_count = text.count("?")

    is_proof = any(
        re.search(p, text_lower, re.IGNORECASE | re.DOTALL)
        for p in PROOF_DONE_PATTERNS
    ) or word_count > 400

    scores = {
        "has_question":     1 if question_count >= 1 else 0,
        "no_direct_answer": 0 if is_proof else 1,
        "focused_question": 1 if 1 <= question_count <= 3 else 0,
        "uses_math_terms":  1 if any(t in text_lower for t in CALCULUS_TERMS) else 0,
        "concise":          1 if 30 <= word_count <= 300 else 0,
    }
    scores["total"] = sum(scores.values())
    scores["word_count"] = word_count
    scores["question_count"] = question_count
    return scores


# ── 回覆 JSON 讀寫 ──────────────────────────────────────────────────────────────
def replies_path(backend: str) -> str:
    return os.path.join(OUT_DIR, f"replies_{backend}.json")


def save_replies(backend: str, results: list[dict]) -> str:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = replies_path(backend)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"backend": backend, "results": results}, f,
                  ensure_ascii=False, indent=2)
    return path


def load_replies(backend: str) -> list[dict]:
    path = replies_path(backend)
    if not os.path.exists(path):
        return []
    return json.load(open(path, encoding="utf-8")).get("results", [])


def load_reference_solutions() -> dict:
    path = os.path.join(OUT_DIR, "reference_solutions.json")
    if not os.path.exists(path):
        return {}
    return json.load(open(path, encoding="utf-8"))
