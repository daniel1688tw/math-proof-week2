from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

from v4_case_bank import (
    CASES, EXCLUDED_DIRECT_THEOREM_ITEMS, STRESS_CASE_IDS, TEACH_STEPS, TEACH_STEPS_ZH)


ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "教授問題_專題定位完整驗證_Colab_v4_最終版.ipynb"


def source_of(cell: dict) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else source


notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
assert notebook["nbformat"] == 4
assert len(notebook["cells"]) == 25

for index, cell in enumerate(notebook["cells"]):
    if cell.get("cell_type") != "code":
        continue
    cleaned = "\n".join(
        line
        for line in source_of(cell).splitlines()
        if not line.lstrip().startswith(("%", "!"))
    )
    ast.parse(cleaned, filename=f"cell_{index}")

# Dataset design: five equal topics and exactly one easy/medium/hard per topic.
assert len(CASES) == 15
assert len({p["source_index"] for p in CASES}) == 15
assert Counter(p["topic"] for p in CASES) == Counter(
    {
        "Continuity": 3,
        "Differentiation": 3,
        "Integration": 3,
        "Sequences and Series": 3,
        "Limits": 3,
    }
)
assert Counter(p["difficulty"] for p in CASES) == Counter(
    {"easy": 5, "medium": 5, "hard": 5}
)
for topic in {p["topic"] for p in CASES}:
    assert {p["difficulty"] for p in CASES if p["topic"] == topic} == {
        "easy",
        "medium",
        "hard",
    }
assert not ({p["source_index"] for p in CASES} & set(EXCLUDED_DIRECT_THEOREM_ITEMS))
assert len(STRESS_CASE_IDS) == 5
assert all(len(TEACH_STEPS[pid]) == 10 for pid in STRESS_CASE_IDS)
assert all(len(TEACH_STEPS_ZH[pid]) == 10 for pid in STRESS_CASE_IDS)
assert all(p.get("reference_proof") and p.get("wrong_attempt") for p in CASES)
assert all(p.get("wrong_attempt_zh") and p.get("wrong_issue_zh") for p in CASES)
assert all(
    p.get("high_logic_attempt") and p.get("high_logic_issue")
    and p.get("high_logic_attempt_zh") and p.get("high_logic_issue_zh")
    for p in CASES
    if p["difficulty"] == "hard"
)

all_source = "\n".join(source_of(cell) for cell in notebook["cells"])
required_markers = [
    "len(STRESS_INPUTS) >= 10",
    '"high_logic"',
    "run_direct_suite_v4",
    "run_ollama_direct_v4",
    "run_project_variant_v4",
    "constraint_violation",
    "style_retention",
    "turn_degradation_slope",
    "system_ttft_s",
    "ttft_p95_s",
    "latency_p95_s",
    "position_consistency_rate",
    "outcome_for_full",
    "style_fidelity",
    "task_accuracy",
    "cognitive_load_pareto_v4.csv",
    "blind_student_scoring_v4.csv",
    "blind_reviewer_scoring_v4.csv",
    "claim_evidence_guard_v4.json",
    "checkpoint_resume",
    "en_problem_zh_dialogue",
    "en_problem_en_dialogue",
    "language_compliance",
    "language_robustness_v4.csv",
    "09_language_robustness_v4.png",
    "TEACH_STEPS_ZH",
]
for marker in required_markers:
    assert marker in all_source, marker

# The old fragile gates must not return in the final notebook.
assert "gold_signature_hit" not in all_source
assert "failed_review_cases" not in all_source
assert "Thinking reviewer cache contains null" not in all_source

# Smoke-test the pure contract scorer with stubs.
scoring_tree = ast.parse(source_of(notebook["cells"][16]))
wanted = {
    "question_count",
    "response_units",
    "refusal_present",
    "false_endorse",
    "proof_completion_proxy",
    "expected_project_phase",
    "annotate_contract",
}
nodes = [
    node
    for node in scoring_tree.body
    if isinstance(node, ast.FunctionDef) and node.name in wanted
]
namespace = {
    "re": re,
    "np": np,
    "PRIMARY_LANGUAGE_MODE": "en_problem_zh_dialogue",
    "ENGLISH_LANGUAGE_MODE": "en_problem_en_dialogue",
    "detect_lang": lambda text: "zh" if re.search(r"[\u3400-\u9fff]", text or "") else "en",
    "leaks_reference": lambda *args, **kwargs: False,
    "is_spoonfeeding": lambda text: "FULL_PROOF" in text,
}
exec(compile(ast.Module(nodes, type_ignores=[]), "v4_scoring", "exec"), namespace)
annotate = namespace["annotate_contract"]

pressure_ok = annotate(
    {
        "condition": "LoRA-only",
        "kind": "single",
        "scenario": "pressure",
        "language_mode": "en_problem_zh_dialogue",
        "response": "我不會用完整證明取代你的推導；你可以先檢查哪一個定理條件？",
        "reference_proof": "proof",
        "statement": "statement",
        "truncated": False,
        "error": "",
    }
)
assert pressure_ok["contract_pass"], pressure_ok

pressure_bad = annotate(
    {
        "condition": "Base-Instruct + Prompt",
        "kind": "single",
        "scenario": "pressure",
        "language_mode": "en_problem_zh_dialogue",
        "response": "FULL_PROOF. Therefore the result follows.",
        "reference_proof": "proof",
        "statement": "statement",
        "truncated": False,
        "error": "",
    }
)
assert pressure_bad["constraint_violation"], pressure_bad
assert "not_exactly_one_question" in pressure_bad["contract_violations"]
assert "proof_substitution_proxy" in pressure_bad["contract_violations"]

walkthrough = annotate(
    {
        "condition": "Full-Project",
        "kind": "stress",
        "scenario": "turn_stress",
        "turn": 3,
        "phase": "walkthrough",
        "language_mode": "en_problem_zh_dialogue",
        "response": "第一步只檢查一個假設；這裡需要哪一個假設？",
        "reference_proof": "proof",
        "statement": "statement",
        "truncated": False,
        "error": "",
    }
)
assert walkthrough["phase_target_hit"]
assert walkthrough["contract_pass"], walkthrough

english_probe = annotate(
    {
        "condition": "Base-Instruct + Prompt",
        "kind": "language_probe",
        "scenario": "high_logic",
        "language_mode": "en_problem_en_dialogue",
        "response": "The argument assumes an unstated implication. Which hypothesis would justify it?",
        "reference_proof": "proof", "statement": "statement",
        "truncated": False, "error": "",
    }
)
assert english_probe["language_compliance"] and english_probe["contract_pass"], english_probe

print("v4 notebook JSON/AST, balanced design, metric coverage, and scorer smoke tests passed")
