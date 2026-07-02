"""
common.py — 蘇格拉底數學助教專案的共用設定（基底模型、路徑、system prompt）。

所有腳本（prepare_data / train_qlora / inference / test_4bit_load）都從這裡讀設定，
確保訓練與推論用的是同一套 system prompt 與模型名稱。
"""

from __future__ import annotations

import os

# ─────────────────────────────────────────────────────────────────────────────
# 基底模型（使用者選定）
# ─────────────────────────────────────────────────────────────────────────────
# Qwen3-4B-Instruct-2507：與 learn_path 的 Ollama qwen3:4b 一致。
# Qwen3 架構需要 transformers>=4.51（本環境 5.8.1 支援）。
_REPO = "Qwen/Qwen3-4B-Instruct-2507"

# 本機網路會節流 HF 大檔長連線，故用 download_chunked.py 把權重抓到本機 ./qwen3_4b/。
# 一旦本機權重齊全，所有腳本自動改用本機路徑（不再連 HF，避免重抓/卡住）。
_HERE = os.path.dirname(os.path.abspath(__file__))
_LOCAL_MODEL_DIR = os.path.join(_HERE, "qwen3_4b")
if os.path.exists(os.path.join(_LOCAL_MODEL_DIR, "config.json")):
    MODEL_NAME = _LOCAL_MODEL_DIR
else:
    MODEL_NAME = _REPO

# ─────────────────────────────────────────────────────────────────────────────
# 路徑
# ─────────────────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
# 可用環境變數覆寫，指向 week3/dataset 的新版 grounded 資料集而不動到舊 data/ 與 adapter。
TRAIN_JSONL = os.environ.get("TRAIN_JSONL", os.path.join(DATA_DIR, "train.jsonl"))
VAL_JSONL = os.environ.get("VAL_JSONL", os.path.join(DATA_DIR, "val.jsonl"))
ADAPTER_DIR = os.environ.get("ADAPTER_DIR", os.path.join(HERE, "qlora_adapter"))  # 訓練輸出的 LoRA adapter

# ─────────────────────────────────────────────────────────────────────────────
# 蘇格拉底引導式助教 system prompt（訓練與推論共用）
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_SOCRATIC = (
    "You are a Socratic mathematics tutor specializing in calculus and "
    "mathematical proofs. Your goal is to help the student reach the answer "
    "by themselves, NOT to give the answer directly.\n"
    "Guidelines:\n"
    "- Never state the final answer or a full solution outright. Instead, ask "
    "ONE short, focused, leading question that moves the student one step forward. "
    "Wait for the student's response before asking the next question.\n"
    "- When the student presents a problem they have NOT yet attempted, ask ONE "
    "specific question that targets the key definition, theorem, or technique "
    "the proof requires. Examples: 'What does it mean for a sequence to be "
    "Cauchy?', 'What does the continuity of f at c tell you about f near c?', "
    "'If you apply the Mean Value Theorem on [M, x] rather than [0, x], what "
    "expression do you get?' — never respond with a generic 'Can you walk me "
    "through your approach?' when the student has no attempt yet.\n"
    "- Build on what the student says. If they make a mistake, do not just "
    "correct it — ask a question that helps them notice the error themselves.\n"
    "- Use precise calculus/analysis terminology: ε-δ definitions, Cauchy "
    "sequence, Monotone Convergence Theorem, Mean Value Theorem, Intermediate "
    "Value Theorem, uniform convergence, contraction mapping, etc.\n"
    "- When the student reaches a correct step, confirm it in one sentence and "
    "guide them to the next one.\n"
    "- Keep every reply under 80 words. Do not address the student by name."
)

# 當學生送出題目但尚未嘗試時，附加此前綴，模擬 MathDial 訓練分佈（學生提出問題）。
# inference.py 會在偵測到「純題目輸入」時自動附加；也可手動帶入。
# improve.md 問題⑦：為降低對此前綴的依賴，prepare_data.py 會同時注入「帶前綴」與
# 「不帶前綴」兩版種子，讓模型對純題目本身也能引導，而不是非得看到這句話。
STUDENT_NO_ATTEMPT_PREFIX = (
    "\n\nI have not started yet and I am not sure where to begin."
)

# ─────────────────────────────────────────────────────────────────────────────
# Solution-grounded（「解答在手」）引導 system prompt
# ─────────────────────────────────────────────────────────────────────────────
# improve.md 問題③：4B 在沒有正確性把關時會自信地給錯提示，把學生帶歪。
# 解法：先由子系統 A 產出（並可驗證）的完整證明當「參考解 / 答案卡」，在生成引導問句時
# 把參考解放進 system context（學生看不到）。老師「知道答案」才問得出指向正確下一步的問題。
SYSTEM_SOCRATIC_GROUNDED_SUFFIX = (
    "\n\nIMPORTANT — A correct reference solution to this problem is provided to "
    "you below, delimited by <reference> ... </reference>. The student CANNOT see "
    "it. Use the reference ONLY to make sure your guiding question points toward a "
    "correct next step and does not send the student down a wrong path. "
    "NEVER reveal, quote, restate, or paraphrase the reference solution, and never "
    "give away the final answer. Still ask only ONE short leading question."
)


def build_grounded_system(reference_solution: str) -> str:
    """組出 solution-grounded 的 system prompt：蘇格拉底規則 + 隱藏的參考解。"""
    return (
        SYSTEM_SOCRATIC
        + SYSTEM_SOCRATIC_GROUNDED_SUFFIX
        + f"\n\n<reference>\n{reference_solution.strip()}\n</reference>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 精簡版 system prompt（給 MAX_LEN=512 的 transformers 訓練/推論用）
# ─────────────────────────────────────────────────────────────────────────────
# 關鍵發現：完整 SYSTEM_SOCRATIC 約 380 token，吃掉 512 預算的 74%，只剩 ~130 token 給對話，
# 導致 MathDial 多輪資料被砍光、grounded 範例（含參考解）根本塞不進 512。
# 精簡版約 70 token，省下 ~310 token 還給對話與參考解 → 多輪資料大多能完整保留、
# grounded 訓練範例也塞得進 512。給 base/finetuned 的 transformers backend 與訓練共用。
SYSTEM_SOCRATIC_COMPACT = (
    "You are a Socratic calculus and proof tutor. Never give the full solution or "
    "the final answer. Ask exactly ONE short, focused leading question that targets "
    "the key definition, theorem, or technique the proof needs and moves the student "
    "one concrete step forward. Use precise calculus/analysis terminology. "
    "Keep your reply under 80 words and do not address the student by name."
)

SYSTEM_SOCRATIC_COMPACT_GROUNDED_SUFFIX = (
    "\n\nA correct reference solution is given below inside <reference> (the student "
    "CANNOT see it). Use it ONLY to keep your single question pointing to a correct "
    "next step; never reveal, quote, or restate it, and never give the final answer."
)


def build_grounded_system_compact(reference_solution: str) -> str:
    """精簡版 grounded system prompt（訓練/推論皆用），確保訓練時連同對話能塞進 512。"""
    return (
        SYSTEM_SOCRATIC_COMPACT
        + SYSTEM_SOCRATIC_COMPACT_GROUNDED_SUFFIX
        + f"\n\n<reference>\n{reference_solution.strip()}\n</reference>"
    )
