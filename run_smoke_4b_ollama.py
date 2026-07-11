"""冒煙測試：用 Ollama 上的 Qwen3-4B-Thinking-2507 跑 test_problems_v3.json 第 1 題。

確認：(a) 模型能載入/推理、(b) <think> 切除正常、(c) 證明品質。
結果（reasoning + answer）存成 smoke_4b_ollama_p1.json，方便後續評分對比。
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from simple_4B_ollama import run_simple_4b_ollama, _resolve_model  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    with open(os.path.join(_HERE, "test_problems_v3.json"), encoding="utf-8") as f:
        problems = json.load(f)

    p = problems[0]  # 第 1 題：cauchy_sequence_summable_differences
    raw = p["raw_problem"]
    model = _resolve_model()
    print(f"模型: {model}", flush=True)
    print(f"題目[{p['problem_id']}]: {raw}\n", flush=True)

    t0 = time.time()
    r = run_simple_4b_ollama(raw, return_thinking=True)
    elapsed = time.time() - t0

    out = {
        "problem_id": p["problem_id"],
        "raw_problem": raw,
        "model": r["model"],
        "elapsed_sec": round(elapsed, 1),
        "reasoning_chars": len(r["reasoning"]),
        "answer_chars": len(r["answer"]),
        "reasoning": r["reasoning"],
        "answer": r["answer"],
    }
    out_path = os.path.join(_HERE, "smoke_4b_ollama_p1.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("=" * 72, flush=True)
    print(f"(a) 推理完成：耗時 {elapsed:.1f}s", flush=True)
    print(f"(b) <think> 切除：reasoning={len(r['reasoning'])} chars，"
          f"answer 開頭是否殘留 <think>？ "
          f"{'是(異常)' if '<think>' in r['answer'] else '否(正常)'}", flush=True)
    print(f"(c) 證明（最終答案，{len(r['answer'])} chars）:\n", flush=True)
    print(r["answer"], flush=True)
    print("\n" + "=" * 72, flush=True)
    print(f"已存到 {out_path}", flush=True)


if __name__ == "__main__":
    main()
