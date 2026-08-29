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
from collections import Counter
from pathlib import Path

from tutor_driver import TutorDriver, leaks_reference, load_problems


HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "eval_out_xdomain"

CONDITIONS = (("baseline", False), ("verify_then_generate", True))
CASE_IDS = ("H1", "H2", "H3", "H4", "H5", "H7", "H8")
EXCLUDED_CASES = {
    "H6": "deployment routes this draft to review, not guide/respond_attempt",
}
JUDGE_KEYS = (
    "first_error_hit", "targetedness", "math_correct", "guidance", "reveal_safe", "rationale",
)
V9_ADAPTER_DIR = (HERE / "qlora_adapter_v9").resolve()
SUCCESSFUL_VERIFIER_STATUSES = frozenset(("issues", "clear"))


def _v9_adapter_dir() -> Path:
    """Reject any adapter override that would invalidate the v9 comparison."""
    configured = os.environ.get("FINAL_ADAPTER")
    if configured:
        candidate = Path(configured)
        candidate = candidate if candidate.is_absolute() else HERE / candidate
        if candidate.resolve() != V9_ADAPTER_DIR:
            raise ValueError(
                "verify-then-generate 評估必須使用 qlora_adapter_v9；"
                f"拒絕 FINAL_ADAPTER={configured!r}"
            )
    return V9_ADAPTER_DIR


def load_v9_model():
    """Load only the locked v9 adapter and return its resolved provenance path."""
    expected = _v9_adapter_dir()
    from eval_final_driver import ADAPTER_DIR, load

    actual = Path(ADAPTER_DIR).resolve()
    if actual != expected:
        raise RuntimeError(
            f"eval_final_driver adapter 為 {actual}，預期 {expected}；拒絕非 v9 評估。"
        )
    tok, model = load()
    return tok, model, actual


def judge_provenance() -> dict:
    """Describe the configured judge so mixed backends cannot be hidden."""
    backend = os.environ.get("JUDGE_BACKEND", "antigravity")
    if backend == "antigravity":
        model = os.environ.get("AGY_MODEL", "Gemini 3.6 Flash (Medium)")
    elif backend == "gemini":
        model = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")
    else:
        model = os.environ.get("JUDGE_MODEL", "sonnet")
    return {"backend": backend, "model": model}


def successful_treatment_n(records: list[dict]) -> int:
    """Count treatment replies whose pre-generation verifier actually answered."""
    return sum(
        row.get("condition") == "verify_then_generate"
        and row.get("verification", {}).get("status") in SUCCESSFUL_VERIFIER_STATUSES
        for row in records
    )


def evaluation_validity(records: list[dict]) -> tuple[bool, str | None]:
    """Require a complete paired comparison with successful treatment verification."""
    case_ids = {row.get("id") for row in records if row.get("id") is not None}
    if not case_ids:
        return False, "no selected cases"
    for case_id in case_ids:
        baseline = [row for row in records
                    if row.get("id") == case_id and row.get("condition") == "baseline"]
        treatment = [row for row in records
                     if row.get("id") == case_id
                     and row.get("condition") == "verify_then_generate"]
        if len(baseline) != 1 or len(treatment) != 1:
            return False, f"incomplete pair for {case_id}"
        if treatment[0].get("verification", {}).get("status") not in SUCCESSFUL_VERIFIER_STATUSES:
            return False, f"unsuccessful treatment verifier for {case_id}"
    return True, None


def evaluation_exit_code(records: list[dict], judge_requested: bool) -> int:
    """Return the documented nonzero result for invalid or incomplete evaluations."""
    valid, _ = evaluation_validity(records)
    if not valid:
        return 1
    if judge_requested and any(record.get("judge") is None for record in records):
        return 2
    return 0


def prepare_rejudge_metadata(saved_metadata: dict, records: list[dict], current_judge: dict) -> dict:
    """Preserve generation provenance and reject a rejudge that would mix judges."""
    metadata = dict(saved_metadata)
    old_requested_backend = metadata.pop("judge_backend", None)
    if old_requested_backend is not None:
        metadata["generation_requested_judge_backend"] = old_requested_backend

    prior_judges = [row.get("judge") for row in records if isinstance(row.get("judge"), dict)]
    for judge in prior_judges:
        provenance = judge.get("provenance")
        if not isinstance(provenance, dict) or provenance != current_judge:
            raise ValueError("不允許跨 backend 或未知 provenance 的 --rejudge 接續。")
    if prior_judges:
        metadata["judge"] = dict(current_judge)
    return metadata


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
    if not all(isinstance(value.get(key), (int, float)) and not isinstance(value.get(key), bool)
               and 1 <= value[key] <= 5
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
        evidence_rows = rows if condition == "baseline" else [
            row for row in rows
            if row.get("verification", {}).get("status") in SUCCESSFUL_VERIFIER_STATUSES
        ]
        judged = [row for row in evidence_rows if isinstance(row.get("judge"), dict)]
        status_counts = Counter(
            row.get("verification", {}).get("status", "missing") for row in rows)
        mean = lambda values: round(statistics.fmean(values), 4) if values else None
        result[condition] = {
            "n": len(rows),
            "evidence_n": len(evidence_rows),
            "judged_n": len(judged),
            "verification_status_counts": dict(status_counts),
            "valid_treatment_n": sum(
                row.get("verification", {}).get("status") in SUCCESSFUL_VERIFIER_STATUSES
                for row in rows
            ) if condition == "verify_then_generate" else 0,
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
            "single_question_rate": mean([row["single_question"] for row in evidence_rows]),
            "no_reference_leak_rate": mean([not row["leaks_reference"] for row in evidence_rows]),
            "mean_latency_seconds": mean([row["latency_seconds"] for row in evidence_rows]),
            "mean_verifier_latency_seconds": mean(
                [row["verification"]["latency_seconds"] for row in evidence_rows]),
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
            verifier_line = f"- verifier: {verification['status']}"
            if verification["first_issue"]:
                verifier_line += f" / {verification['first_issue']}"
            lines.extend([
                f"### {row['condition']}",
                verifier_line,
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

    current_judge = judge_provenance()
    if args.rejudge:
        saved = json.loads(args.rejudge.read_text(encoding="utf-8"))
        records = saved["records"]
        metadata = prepare_rejudge_metadata(saved.get("metadata", {}), records, current_judge)
    else:
        # Tier 0 imports only the CPU-only helpers above; this initializes
        # Transformers only for real generation and locks the v9 adapter.
        tok, model, adapter_dir = load_v9_model()
        records = generate_records(tok, model, args.limit)
        metadata = {
            "generator": f"Qwen3-4B + {adapter_dir}",
            "adapter_dir": str(adapter_dir),
            "verifier": os.environ.get("REVIEW_MODEL", "qwen3-4b-thinking-2507:latest"),
            "excluded_cases": dict(EXCLUDED_CASES),
        }

    if not args.generate_only:
        for record in records:
            if record.get("judge") is None:
                judgement = judge_record(record)
                if judgement is not None:
                    judgement["provenance"] = dict(current_judge)
                    record["judge"] = judgement
    if any(isinstance(record.get("judge"), dict) for record in records):
        metadata["judge"] = dict(current_judge)

    valid, invalid_reason = evaluation_validity(records)
    payload = {
        "metadata": metadata,
        "valid": valid,
        "verdict": "EVALUATED" if valid else "INCONCLUSIVE",
        "invalid_reason": invalid_reason,
        "summary": summarize(records),
        "records": records,
    }
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    json_path = args.output or OUT_DIR / f"verify_then_generate_{stamp}.json"
    md_path = json_path.with_suffix(".md")
    OUT_DIR.mkdir(exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(records, payload["summary"], metadata), encoding="utf-8")
    print(json_path)
    exit_code = evaluation_exit_code(records, judge_requested=not args.generate_only)
    if exit_code == 1:
        print("實驗組沒有 successful verifier call；本次 A/B 評估無效。")
        sys.exit(1)
    if exit_code == 2:
        print("評審不完整；已保存輸出，可用 --rejudge 接續。")
        sys.exit(2)


if __name__ == "__main__":
    main()
