"""
eval_socratic_v3.py — 蘇格拉底引導回覆品質評估

對 test_problems_v3.json 的 10 題，分別跑：
  - 基底模型（Qwen3-4B-Instruct，無 adapter）
  - 微調模型（同基底 + QLoRA qlora_adapter/）

每題取第一輪回覆，用 5 個蘇格拉底準則評分（0-5）：
  1. has_question     — 回覆含至少一個問句
  2. no_direct_answer — 未給出完整證明/答案
  3. focused_question — 問題數量 1-3（不轟炸）
  4. uses_math_terms  — 含相關微積分術語
  5. concise          — 回覆字數在合理範圍（30-300）

執行：
  conda run -n lora_project --live-stream python eval_socratic_v3.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

os.environ.setdefault("PYTHONNOUSERSITE", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pyarrow          # noqa: F401  — Windows: 先預載 Arrow DLL
import datasets         # noqa: F401
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

# ── 路徑設定 ─────────────────────────────────────────────────────────────────
HERE          = os.path.dirname(os.path.abspath(__file__))
SOCRATIC_DIR  = os.path.join(HERE, "learn_path", "socratic_tutor")
MODEL_DIR     = os.path.join(SOCRATIC_DIR, "qwen3_4b")
ADAPTER_DIR   = os.path.join(SOCRATIC_DIR, "qlora_adapter")
TEST_FILE     = os.path.join(HERE, "test_problems_v3.json")
OUTPUT_CSV    = os.path.join(HERE, "eval_socratic_v3.csv")

# 把 socratic_tutor/ 加入 path 以便取用 common.py 的 SYSTEM_SOCRATIC
sys.path.insert(0, SOCRATIC_DIR)
from common import MODEL_NAME as COMMON_MODEL_NAME, SYSTEM_SOCRATIC  # noqa: E402

# 本機有完整模型就優先用本機路徑
MODEL_NAME = MODEL_DIR if os.path.exists(os.path.join(MODEL_DIR, "config.json")) else COMMON_MODEL_NAME

# ── 評分準則 ──────────────────────────────────────────────────────────────────
CALCULUS_TERMS = [
    "limit", "continuous", "continuity", "differentiable", "derivative",
    "integral", "integrable", "sequence", "convergent", "converges", "cauchy",
    "mean value", "mvt", "intermediate value", "ivt", "epsilon", "delta",
    "bounded", "monotone", "uniform", "fixed point", "contraction", "periodic",
    "compact", "closed", "open interval", "sup", "infimum", "supremum",
]

# 這些 pattern 出現代表模型直接給完整答案
PROOF_DONE_PATTERNS = [
    r"therefore.{0,60}(proved|proven|complete|done|qed|follows)",
    r"we have (shown|proved|proven|demonstrated)",
    r"this (completes|concludes) the proof",
    r"q\.?\s*e\.?\s*d",
    r"\bproof\.?\s*\n",
    r"(?:step\s*1|step1).*\n.*(?:step\s*2|step2).*\n.*(?:step\s*3|step3)",  # full proof steps
    r"since.*therefore.*converges",
    r"by induction.*we (get|obtain|have)",
]


def score_socratic(response: str) -> dict:
    """給一個蘇格拉底引導回覆打分，回傳各項分數與摘要資訊。"""
    text = response.strip()
    text_lower = text.lower()
    words = text.split()
    word_count = len(words)
    question_count = text.count("?")

    # 1. 含問句
    s_question = 1 if question_count >= 1 else 0

    # 2. 未直接給答案
    is_proof = any(
        re.search(p, text_lower, re.IGNORECASE | re.DOTALL)
        for p in PROOF_DONE_PATTERNS
    )
    if word_count > 400:   # 超過 400 字大概是在寫完整證明
        is_proof = True
    s_no_answer = 0 if is_proof else 1

    # 3. 問題數量合理（1-3 個）
    s_focused = 1 if 1 <= question_count <= 3 else 0

    # 4. 有微積分術語
    term_hits = sum(1 for t in CALCULUS_TERMS if t in text_lower)
    s_terms = 1 if term_hits >= 1 else 0

    # 5. 簡潔（30-300 字）
    s_concise = 1 if 30 <= word_count <= 300 else 0

    total = s_question + s_no_answer + s_focused + s_terms + s_concise
    return {
        "has_question"     : s_question,
        "no_direct_answer" : s_no_answer,
        "focused_question" : s_focused,
        "uses_math_terms"  : s_terms,
        "concise"          : s_concise,
        "total"            : total,
        "word_count"       : word_count,
        "question_count"   : question_count,
        "term_hits"        : term_hits,
        "snippet"          : text[:220].replace("\n", " ") + ("…" if len(text) > 220 else ""),
    }


# ── 模型載入 ──────────────────────────────────────────────────────────────────
def load_model(use_adapter: bool):
    label = "微調後（+ LoRA）" if use_adapter else "基底模型（無 adapter）"
    print(f"\n{'='*64}")
    print(f"  載入 {label}")
    print(f"  model : {MODEL_NAME}")
    print(f"{'='*64}")

    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb,
        device_map={"": 0},
        torch_dtype=torch.bfloat16,
    )
    if use_adapter:
        if not os.path.isdir(ADAPTER_DIR):
            print(f"  [警告] 找不到 adapter 目錄：{ADAPTER_DIR}")
        else:
            model = PeftModel.from_pretrained(model, ADAPTER_DIR)
            print(f"  ✓ LoRA adapter 已載入")
    model.eval()
    return tok, model, label


@torch.no_grad()
def gen_reply(tok, model, problem: str) -> tuple[str, float]:
    messages = [
        {"role": "system", "content": SYSTEM_SOCRATIC},
        {"role": "user",   "content": problem},
    ]
    enc = tok.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    ).to(model.device)

    t0 = time.time()
    out = model.generate(
        **enc,
        max_new_tokens=320,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.05,
        pad_token_id=tok.pad_token_id or tok.eos_token_id,
    )
    elapsed = time.time() - t0
    reply = tok.decode(
        out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True
    ).strip()
    return reply, elapsed


# ── 主程式 ────────────────────────────────────────────────────────────────────
def main() -> None:
    with open(TEST_FILE, encoding="utf-8") as f:
        problems = json.load(f)

    all_rows = []   # 最終 CSV 行

    for use_adapter in [False, True]:
        tok, model, label = load_model(use_adapter)
        model_tag = "finetuned" if use_adapter else "base"
        print()

        for idx, prob in enumerate(problems, 1):
            pid   = prob["problem_id"]
            topic = prob["topic"]
            diff  = prob["difficulty"]
            raw   = prob["raw_problem"]

            print(f"  [{idx:02d}/10] {pid}")
            reply, elapsed = gen_reply(tok, model, raw)
            sc = score_socratic(reply)

            row = {
                "model"            : model_tag,
                "problem_id"       : pid,
                "topic"            : topic,
                "difficulty"       : diff,
                "total_score"      : sc["total"],
                "has_question"     : sc["has_question"],
                "no_direct_answer" : sc["no_direct_answer"],
                "focused_question" : sc["focused_question"],
                "uses_math_terms"  : sc["uses_math_terms"],
                "concise"          : sc["concise"],
                "word_count"       : sc["word_count"],
                "question_count"   : sc["question_count"],
                "elapsed_s"        : round(elapsed, 1),
                "snippet"          : sc["snippet"],
                "full_response"    : reply,
            }
            all_rows.append(row)

            flag = "✓" if sc["total"] >= 4 else ("△" if sc["total"] == 3 else "✗")
            print(f"         {flag} 總分 {sc['total']}/5  "
                  f"（問句:{sc['has_question']} 不給答:{sc['no_direct_answer']} "
                  f"集中:{sc['focused_question']} 術語:{sc['uses_math_terms']} "
                  f"簡潔:{sc['concise']}）  {sc['word_count']}字 {elapsed:.0f}s")
            print(f"         回覆摘要：{sc['snippet'][:120]}")

        del model
        torch.cuda.empty_cache()

    # ── 輸出 CSV ──────────────────────────────────────────────────────────────
    import csv
    fieldnames = [
        "model", "problem_id", "topic", "difficulty",
        "total_score", "has_question", "no_direct_answer",
        "focused_question", "uses_math_terms", "concise",
        "word_count", "question_count", "elapsed_s", "snippet", "full_response",
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n✓ 詳細結果已寫入：{OUTPUT_CSV}")

    # ── 彙總報告 ──────────────────────────────────────────────────────────────
    def avg(rows, key):
        vals = [r[key] for r in rows]
        return sum(vals) / len(vals) if vals else 0

    base_rows = [r for r in all_rows if r["model"] == "base"]
    ft_rows   = [r for r in all_rows if r["model"] == "finetuned"]

    print("\n" + "=" * 64)
    print("  評估彙總（/5 為各項平均）")
    print("=" * 64)
    print(f"{'指標':<22}{'基底模型':>10}{'微調模型':>10}{'差異':>8}")
    print("-" * 50)

    for key, label in [
        ("total_score",      "總分（/5）"),
        ("has_question",     "含問句"),
        ("no_direct_answer", "不直接給答案"),
        ("focused_question", "問題集中（1-3）"),
        ("uses_math_terms",  "微積分術語"),
        ("concise",          "回覆簡潔"),
    ]:
        b = avg(base_rows, key)
        f = avg(ft_rows,   key)
        d = f - b
        sign = "+" if d > 0 else ""
        print(f"  {label:<20}{b:>10.2f}{f:>10.2f}{sign+f'{d:.2f}':>8}")

    print("\n  逐題比較（基底 → 微調）：")
    print(f"  {'problem_id':<45}{'基底':>4}{'微調':>4}{'Δ':>4}")
    print("  " + "-" * 57)
    base_map = {r["problem_id"]: r for r in base_rows}
    ft_map   = {r["problem_id"]: r for r in ft_rows}
    for prob in problems:
        pid = prob["problem_id"]
        b = base_map[pid]["total_score"]
        f = ft_map[pid]["total_score"]
        d = f - b
        sign = "+" if d > 0 else ""
        bar = "▲" if d > 0 else ("▼" if d < 0 else "=")
        print(f"  {pid:<45}{b:>4}{f:>4}{bar+sign+str(abs(d)):>5}")

    b_avg = avg(base_rows, "total_score")
    f_avg = avg(ft_rows,   "total_score")
    d_avg = f_avg - b_avg
    sign  = "+" if d_avg > 0 else ""
    print(f"  {'平均':<45}{b_avg:>4.1f}{f_avg:>4.1f}{sign+f'{d_avg:.1f}':>5}")

    verdict = (
        "✓ 微調模型蘇格拉底引導行為明顯優於基底"
        if d_avg >= 0.5 else
        "△ 微調模型有部分改善，但差異未達顯著"
        if d_avg > 0 else
        "✗ 微調模型未表現出明顯的蘇格拉底引導改善"
        if d_avg == 0 else
        "✗ 微調模型退步（需檢查 adapter 或 system prompt）"
    )
    print(f"\n  {verdict}\n")


if __name__ == "__main__":
    main()
