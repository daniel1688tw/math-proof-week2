"""
run_compare_simple.py — 在 test_problems_v3.json 上對照 simple.py vs simple_v2.py

於同一次執行中，用「共用的單一模型後端」分別跑：
  - simple.run_simple        （單次直答，對照組）
  - simple_v2.run_simple_v2  （draft → review 的最小 self-refine）

兩者共用同一個 _LLMBackend 物件，避免在 6 GiB VRAM 上重複載入 7B 模型。
（simple.SYSTEM_PROMPT 與 simple_v2.DRAFT_SYSTEM_PROMPT 文字相同，故 simple
 透過共用後端的預設 system_prompt 行為不變。）

輸出：
  - compare_simple_results.json   兩者每題完整輸出（增量寫入、可續跑）
  - compare_simple_outputs.txt    可讀對照，供人工 0-10 評分

執行：
    conda run -n lora_project --live-stream python run_compare_simple.py
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import simple          # noqa: E402
import simple_v2       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROBLEMS_PATH = os.path.join(HERE, "test_problems_v3.json")
RESULTS_PATH = os.path.join(HERE, "compare_simple_results.json")
OUTPUTS_PATH = os.path.join(HERE, "compare_simple_outputs.txt")


def _load_done() -> dict:
    if os.path.exists(RESULTS_PATH):
        try:
            with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save(results: dict) -> None:
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def _dump_readable(results: dict, problems: list) -> None:
    sep = "=" * 80
    rule = "-" * 40
    lines = []
    for prob in problems:
        pid = prob["problem_id"]
        r = results.get(pid)
        if not r:
            continue
        lines.append(sep)
        lines.append(f"PID: {pid}")
        lines.append(f"raw_problem: {prob['raw_problem']}")
        lines.append(
            f"simple    elapsed={r.get('simple_elapsed',0):.1f}s | "
            f"simple_v2 elapsed={r.get('simple_v2_elapsed',0):.1f}s"
        )
        lines.append(f"{rule} SIMPLE (one-shot) {rule}")
        lines.append(r.get("simple_output") or "(none)")
        lines.append(f"{rule} SIMPLE_V2 (draft->review) {rule}")
        lines.append(r.get("simple_v2_output") or "(none)")
        lines.append("")
    with open(OUTPUTS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    with open(PROBLEMS_PATH, "r", encoding="utf-8") as f:
        problems = json.load(f)

    # Load the model ONCE and share the backend across both modules.
    backend = simple_v2._LLMBackend()
    simple.ACTIVE_LLM = backend
    simple_v2.ACTIVE_LLM = backend

    results = _load_done()
    print(f"[compare] {len(problems)} problems; {len(results)} already done.", flush=True)

    t_start = time.time()
    for i, prob in enumerate(problems, 1):
        pid = prob["problem_id"]
        if pid in results:
            print(f"[compare] ({i}/{len(problems)}) skip {pid} (done)", flush=True)
            continue
        raw = prob["raw_problem"]
        print(f"\n[compare] ({i}/{len(problems)}) {pid} :: simple ...", flush=True)
        t0 = time.time()
        simple_out = simple.run_simple(raw)
        t_simple = time.time() - t0

        print(f"[compare] ({i}/{len(problems)}) {pid} :: simple_v2 ...", flush=True)
        t1 = time.time()
        simple_v2_out = simple_v2.run_simple_v2(raw)
        t_v2 = time.time() - t1

        results[pid] = {
            "problem_id": pid,
            "topic": prob.get("topic", ""),
            "difficulty": prob.get("difficulty", ""),
            "raw_problem": raw,
            "simple_output": simple_out,
            "simple_v2_output": simple_v2_out,
            "simple_elapsed": t_simple,
            "simple_v2_elapsed": t_v2,
        }
        _save(results)
        _dump_readable(results, problems)
        print(
            f"[compare] done {pid}: simple={t_simple:.1f}s simple_v2={t_v2:.1f}s",
            flush=True,
        )

    print(
        f"\n[compare] ALL DONE in {time.time()-t_start:.1f}s. "
        f"Wrote {RESULTS_PATH} and {OUTPUTS_PATH}",
        flush=True,
    )


if __name__ == "__main__":
    main()
