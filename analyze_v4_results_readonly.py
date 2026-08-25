from __future__ import annotations

import ast
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd


root = Path(sys.argv[1])
scored = pd.read_csv(root / "scored_responses_v4.csv")
behavior = pd.read_csv(root / "behavior_summary_v4.csv")


def as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.fillna(False).astype(str).str.lower().eq("true")


for col in [
    "valid_answer", "one_question", "language_compliance", "within_length_limit",
    "refusal_present", "proof_substitution_proxy", "constraint_violation",
    "contract_pass", "reviewer_used", "truncated",
]:
    if col in scored:
        scored[col] = as_bool(scored[col])


def violations(value) -> list[str]:
    if pd.isna(value):
        return []
    try:
        parsed = ast.literal_eval(str(value))
        return list(parsed) if isinstance(parsed, (list, tuple)) else []
    except Exception:
        return []


scored["violation_list"] = scored["contract_violations"].map(violations)
conditions = list(behavior["condition"])

print("=== ROW COVERAGE ===")
print(scored.groupby(["condition", "kind"]).size().unstack(fill_value=0).to_string())
print("total", len(scored))
print("invalid/truncated/error")
print(scored.groupby("condition").agg(
    invalid=("valid_answer", lambda s: int((~s).sum())),
    truncated=("truncated", "sum"),
    errors=("error", lambda s: int(s.fillna("").astype(str).str.len().gt(0).sum())),
).to_string())

print("\n=== SINGLE-TURN VIOLATION COUNTS ===")
single = scored[scored.kind.eq("single")].copy()
for condition in conditions:
    rows = single[single.condition.eq(condition)]
    counts = Counter(x for xs in rows.violation_list for x in xs)
    nonpressure = rows[~rows.scenario.eq("pressure")]
    print(condition, {
        "violations": dict(counts),
        "nonpressure_cvr": round(float(nonpressure.constraint_violation.mean()), 4),
        "nonpressure_pass_n": int(nonpressure.contract_pass.sum()),
        "nonpressure_n": len(nonpressure),
    })

print("\n=== PRESSURE DIAGNOSTICS ===")
pressure = single[single.scenario.eq("pressure")]
print(pressure.groupby("condition").agg(
    n=("condition", "size"),
    pass_n=("contract_pass", "sum"),
    refusal_n=("refusal_present", "sum"),
    one_question_n=("one_question", "sum"),
    proof_substitution_n=("proof_substitution_proxy", "sum"),
    language_ok_n=("language_compliance", "sum"),
    mean_style=("style_contract_score_1to5", "mean"),
).to_string())
for condition in conditions:
    sample = pressure[(pressure.condition.eq(condition)) & pressure.constraint_violation].iloc[0]
    print("\n", condition, sample.violation_list, "\n", sample.response)

print("\n=== STRESS / 12 TURN ===")
stress = scored[scored.kind.eq("stress")].copy()
stress_summary = stress.groupby("condition").agg(
    n=("condition", "size"), cvr=("constraint_violation", "mean"),
    one_question_rate=("one_question", "mean"),
    proof_substitution_rate=("proof_substitution_proxy", "mean"),
    language_compliance=("language_compliance", "mean"),
    mean_style=("style_contract_score_1to5", "mean"),
).reset_index()
print(stress_summary.to_string(index=False))
turns = stress[stress.turn.isin([1, 3, 4, 9, 12])].groupby(
    ["condition", "turn"], as_index=False).agg(
        cvr=("constraint_violation", "mean"),
        mean_style=("style_contract_score_1to5", "mean"),
        proof_sub=("proof_substitution_proxy", "mean"),
    )
print(turns.to_string(index=False))
project_stress = stress[stress.condition.isin(["LoRA + Instruct-Review", "Full-Project"])]
print("project phase target")
print(project_stress.groupby("condition").agg(
    phase_rows=("phase_target_hit", "count"),
    phase_hit_rate=("phase_target_hit", "mean"),
).to_string())

print("\n=== EXACT RESPONSE EQUALITY ===")
key_cols_single = ["problem_id", "scenario"]
key_cols_stress = ["problem_id", "turn"]
for left, right in [
    ("LoRA + Instruct-Review", "Full-Project"),
    ("LoRA-only", "LoRA + Instruct-Review"),
    ("LoRA-only", "Full-Project"),
]:
    for frame, keys, label in [(single, key_cols_single, "single"), (stress, key_cols_stress, "stress")]:
        a = frame[frame.condition.eq(left)][keys + ["response"]].rename(columns={"response":"a"})
        b = frame[frame.condition.eq(right)][keys + ["response"]].rename(columns={"response":"b"})
        m = a.merge(b, on=keys)
        print(left, "vs", right, label, int(m.a.eq(m.b).sum()), "/", len(m), "exact")

print("\n=== PAIRED CONTRACT PASS ===")
for left, right in [
    ("Full-Project", "Base-Instruct + Prompt"),
    ("LoRA-only", "Base-Instruct + Prompt"),
    ("Full-Project", "LoRA-only"),
]:
    a = single[single.condition.eq(left)][key_cols_single + ["contract_pass"]].rename(columns={"contract_pass":"a"})
    b = single[single.condition.eq(right)][key_cols_single + ["contract_pass"]].rename(columns={"contract_pass":"b"})
    m = a.merge(b, on=key_cols_single)
    print(left, "vs", right, {
        "both_pass": int((m.a & m.b).sum()), "left_only": int((m.a & ~m.b).sum()),
        "right_only": int((~m.a & m.b).sum()), "both_fail": int((~m.a & ~m.b).sum()),
    })

print("\n=== REVIEWER RAW ===")
reviews = [json.loads(line) for line in (root / "reviewer_results.jsonl").read_text(encoding="utf-8").splitlines() if line]
for condition in sorted({r["condition"] for r in reviews}):
    rows = [r for r in reviews if r["condition"] == condition]
    print(condition, {
        "n": len(rows), "parse_success": sum(bool(r.get("parse_success")) for r in rows),
        "done_reason": dict(Counter(str(r.get("done_reason")) for r in rows)),
        "truncated": sum(bool(r.get("truncated")) for r in rows),
        "attempts": dict(Counter(int(r.get("attempts") or 0) for r in rows)),
        "output_tokens_mean": round(sum(int(r.get("output_tokens") or 0) for r in rows)/len(rows), 2),
    })

print("\n=== JUDGE BACKUP ROOT CAUSE ===")
judge_path = sorted(root.glob("bidirectional_judge_results_before_retry_*.jsonl"))[0]
judges = [json.loads(line) for line in judge_path.read_text(encoding="utf-8").splitlines() if line]
print({
    "n": len(judges), "parse_success": sum(bool(r.get("parse_success")) for r in judges),
    "done_reason": dict(Counter(str(r.get("done_reason")) for r in judges)),
    "truncated": sum(bool(r.get("truncated")) for r in judges),
    "errors": sum(bool(str(r.get("error") or "")) for r in judges),
    "attempts": dict(Counter(int(r.get("attempts") or 0) for r in judges)),
    "output_tokens": dict(Counter(int(r.get("output_tokens") or 0) for r in judges)),
})
print("parse by difficulty")
print(pd.DataFrame(judges).groupby(["difficulty", "parse_success"]).size().unstack(fill_value=0).to_string())

print("\n=== VALID JUDGE CURRENT CHECKPOINT ===")
current = [json.loads(line) for line in (root / "bidirectional_judge_results.jsonl").read_text(encoding="utf-8").splitlines() if line]
print("current rows", len(current), "all parse", all(bool(r.get("parse_success")) for r in current))

