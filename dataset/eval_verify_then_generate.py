# -*- coding: utf-8 -*-
"""Paired v9 evaluation for proof verification before tutor generation."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

from tutor_driver import TutorDriver, leaks_reference, load_problems


HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "eval_out_xdomain"

CONDITIONS = (("baseline", False), ("verify_then_generate", True))
CASE_IDS = tuple(f"H{i}" for i in range(1, 9))
JUDGE_KEYS = (
    "first_error_hit", "targetedness", "math_correct", "guidance", "reveal_safe", "rationale",
)


def build_judge_prompt(statement: str, planted_error: str, attempt: str, reply: str) -> str:
    """Build the strict, solution-safe rubric used for one generated reply."""
    return f"""你是高等數學證明教學的嚴格評審。請根據題目、埋入的錯誤、學生嘗試與助教回覆評分。

題目：{statement}
埋入的錯誤：{planted_error}
學生嘗試：{attempt}
助教回覆：{reply}

first_error_hit：助教是否處理了埋入的最早／根本錯誤，而非只籠統地說證明不完整。
targetedness：助教針對該錯誤的精準程度，1 到 5 分。
math_correct：助教的數學敘述是否正確。
guidance：助教引導學生自行修正的品質，1 到 5 分。
reveal_safe：助教是否避免直接洩漏完整參考解。

不要因蘇格拉底式回覆未給出完整解答而扣分；不要因完整洩漏解答而加分。
只輸出一個 JSON 物件，且必須完全符合此 schema：
{{
  "first_error_hit": true,
  "targetedness": 1,
  "math_correct": true,
  "guidance": 1,
  "reveal_safe": true,
  "rationale": "brief evidence"
}}
"""


def judge_record(record: dict) -> dict | None:
    """Return a schema-valid external judgement, or None if judging was unavailable."""
    from regression_suite import claude_call, parse_json_obj

    raw = claude_call(build_judge_prompt(
        record["statement"], record["planted_error"], record["attempt"], record["reply"],
    ))
    value = parse_json_obj(raw)
    if not isinstance(value, dict):
        return None
    if not all(isinstance(value.get(key), bool)
               for key in ("first_error_hit", "math_correct", "reveal_safe")):
        return None
    if not all(isinstance(value.get(key), (int, float)) and 1 <= value[key] <= 5
               for key in ("targetedness", "guidance")):
        return None
    if not isinstance(value.get("rationale"), str):
        return None
    return {key: value[key] for key in JUDGE_KEYS}


def summarize(records: list[dict]) -> dict:
    """Summarize the paired conditions without treating unjudged rows as successes."""
    result = {}
    for condition, _ in CONDITIONS:
        rows = [row for row in records if row["condition"] == condition]
        judged = [row for row in rows if isinstance(row.get("judge"), dict)]
        mean = lambda values: round(statistics.fmean(values), 4) if values else None
        result[condition] = {
            "n": len(rows),
            "judged_n": len(judged),
            "first_error_hit_rate": mean(
                [row["judge"]["first_error_hit"] for row in judged]),
            "targetedness_mean": mean(
                [row["judge"]["targetedness"] / 5 for row in judged]),
            "math_correct_rate": mean(
                [row["judge"]["math_correct"] for row in judged]),
            "guidance_mean": mean(
                [row["judge"]["guidance"] / 5 for row in judged]),
            "reveal_safe_rate": mean(
                [row["judge"]["reveal_safe"] for row in judged]),
            "single_question_rate": mean([row["single_question"] for row in rows]),
            "no_reference_leak_rate": mean([not row["leaks_reference"] for row in rows]),
            "mean_latency_seconds": mean([row["latency_seconds"] for row in rows]),
            "mean_verifier_latency_seconds": mean(
                [row["verification"]["latency_seconds"] for row in rows]),
        }
    return result


def render_markdown(records: list[dict], summary: dict, metadata: dict) -> str:
    """Render a side-by-side result table and paired case-level evidence."""
    lines = [
        "# Verify-Then-Generate paired evaluation", "",
        f"- Generator: {metadata['generator']}",
        f"- Verifier: {metadata['verifier']}", "",
        "| condition | hit | targeted | math | guidance | reveal | one question | no leak | latency |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for condition, _ in CONDITIONS:
        item = summary[condition]
        lines.append(
            f"| {condition} | {item['first_error_hit_rate']} | {item['targetedness_mean']} | "
            f"{item['math_correct_rate']} | {item['guidance_mean']} | {item['reveal_safe_rate']} | "
            f"{item['single_question_rate']} | {item['no_reference_leak_rate']} | "
            f"{item['mean_latency_seconds']} |"
        )
    for case_id in CASE_IDS:
        case_rows = [row for row in records if row["id"] == case_id]
        if not case_rows:
            continue
        lines.extend(["", f"## {case_id}"])
        for row in case_rows:
            verification = row["verification"]
            rationale = (row.get("judge") or {}).get("rationale", "未完成評審")
            lines.extend([
                f"### {row['condition']}",
                f"- verifier: {verification['status']} / {verification['first_issue']}",
                f"- latency: {row['latency_seconds']} s",
                f"- reply: {row['reply']}",
                f"- judge: {rationale}",
            ])
    return "\n".join(lines) + "\n"


def generate_records(tok, model, limit: int | None = None) -> list[dict]:
    """Generate each H1-H8 reply under identical v9 decoding except for verification."""
    problems = load_problems()
    attempts = json.loads((HERE / "held_out_attempts.json").read_text(encoding="utf-8"))
    selected = CASE_IDS[:limit] if limit else CASE_IDS
    records = []
    for case_id in selected:
        problem, attempt = problems[case_id], attempts[case_id]
        for condition, feature_enabled in CONDITIONS:
            driver = TutorDriver(
                tok, model, dict(problem), backstop=True,
                verify_then_generate=feature_enabled,
            )
            started = time.perf_counter()
            reply = driver.start(opener=attempt["attempt"])
            elapsed = time.perf_counter() - started
            records.append({
                "id": case_id,
                "condition": condition,
                "statement": problem["statement"],
                "reference_proof": problem["reference_proof"],
                "attempt": attempt["attempt"],
                "planted_error": attempt["planted_error"],
                "reply": reply,
                "verification": dict(driver.state["pre_generation_verification"]),
                "single_question": len(re.findall(r"[?？]", reply)) == 1,
                "leaks_reference": leaks_reference(reply, problem["reference_proof"]),
                "latency_seconds": round(elapsed, 4),
                "judge": None,
            })
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--rejudge", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.rejudge:
        saved = json.loads(args.rejudge.read_text(encoding="utf-8"))
        records = saved["records"]
    else:
        # Tier 0 imports only the CPU-only helpers above; loading this module
        # initializes Transformers and is needed solely for real generation.
        from eval_final_driver import load as load_model
        tok, model = load_model()
        records = generate_records(tok, model, args.limit)

    if not args.generate_only:
        for record in records:
            if record.get("judge") is None:
                record["judge"] = judge_record(record)

    metadata = {
        "generator": "Qwen3-4B + qlora_adapter_v9",
        "verifier": os.environ.get("REVIEW_MODEL", "qwen3-4b-thinking-2507:latest"),
        "judge_backend": os.environ.get("JUDGE_BACKEND", "antigravity"),
    }
    payload = {"metadata": metadata, "summary": summarize(records), "records": records}
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    json_path = args.output or OUT_DIR / f"verify_then_generate_{stamp}.json"
    md_path = json_path.with_suffix(".md")
    OUT_DIR.mkdir(exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(records, payload["summary"], metadata), encoding="utf-8")
    print(json_path)
    if not args.generate_only and any(record["judge"] is None for record in records):
        print("評審不完整；已保存輸出，可用 --rejudge 接續。")
        sys.exit(2)


if __name__ == "__main__":
    main()
