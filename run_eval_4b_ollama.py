"""完整驗證：用 Ollama 上的 Qwen3-4B-Thinking-2507 跑 test_problems_v3.json 全 10 題。

每題存 reasoning + answer，輸出：
  - eval_4b_results.json（結構化，供評分）
  - eval_4b_outputs.txt（純文字，便於人工閱讀）
進度即時印出，方便背景監看。
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

    model = _resolve_model()
    print(f"模型: {model}　題數: {len(problems)}\n", flush=True)

    results = {}
    txt_chunks = []
    t_all = time.time()

    for i, p in enumerate(problems, 1):
        pid = p["problem_id"]
        raw = p["raw_problem"]
        print(f"[{i}/{len(problems)}] {pid} … 推理中", flush=True)
        t0 = time.time()
        r = run_simple_4b_ollama(raw, return_thinking=True)
        elapsed = time.time() - t0
        print(f"    完成 {elapsed:.0f}s　reasoning={len(r['reasoning'])} ans={len(r['answer'])}", flush=True)

        results[pid] = {
            "problem_id": pid,
            "topic": p.get("topic"),
            "difficulty": p.get("difficulty"),
            "raw_problem": raw,
            "model": r["model"],
            "elapsed_sec": round(elapsed, 1),
            "reasoning_chars": len(r["reasoning"]),
            "answer_chars": len(r["answer"]),
            "answer": r["answer"],
        }
        txt_chunks.append(
            f"{'='*78}\n[{i}] {pid}  ({p.get('topic')}, {p.get('difficulty')})  "
            f"{elapsed:.0f}s\n{'='*78}\n題目: {raw}\n\n--- 最終證明 ---\n{r['answer']}\n"
        )

        # 每題寫一次，避免中途中斷丟失
        with open(os.path.join(_HERE, "eval_4b_results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        with open(os.path.join(_HERE, "eval_4b_outputs.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(txt_chunks))

    print(f"\n全部完成，總耗時 {time.time()-t_all:.0f}s", flush=True)
    print("結果：eval_4b_results.json / eval_4b_outputs.txt", flush=True)


if __name__ == "__main__":
    main()
