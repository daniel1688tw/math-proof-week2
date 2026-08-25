from __future__ import annotations

import json
import random
import re
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from v4_case_bank import CASES, STRESS_CASE_IDS


ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "教授問題_專題定位完整驗證_Colab_v4_最終版.ipynb"
nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def source(index: int) -> str:
    value = nb["cells"][index]["source"]
    return "".join(value) if isinstance(value, list) else value


CONDITIONS = [
    "Base-Instruct + Prompt",
    "Base-Instruct + 4-Shot",
    "Base-Thinking + Prompt",
    "LoRA-only",
    "LoRA + Instruct-Review",
    "Full-Project",
]
REVIEWER_CONDITIONS = [
    "Base-Instruct reviewer",
    "Base-Thinking reviewer",
    "LoRA reviewer",
]
DIFFICULTY_ORDER = ["easy", "medium", "hard"]
TOPIC_ORDER = [
    "Continuity",
    "Differentiation",
    "Integration",
    "Sequences and Series",
    "Limits",
]

PRIMARY_LANGUAGE_MODE = "en_problem_zh_dialogue"
ENGLISH_LANGUAGE_MODE = "en_problem_en_dialogue"
LANGUAGE_PROBE_IDS = list(STRESS_CASE_IDS)

primary_review_cases = []
for p in CASES:
    primary_review_cases.append(
        {
            **p,
            "review_id": f"{p['id']}:wrong_attempt",
            "review_scenario": "wrong_attempt",
            "review_attempt": p["wrong_attempt_zh"],
            "gold_issue": p["wrong_issue_zh"],
            "review_language": "zh",
        }
    )
    if p["difficulty"] == "hard":
        primary_review_cases.append(
            {
                **p,
                "review_id": f"{p['id']}:high_logic",
                "review_scenario": "high_logic",
                "review_attempt": p["high_logic_attempt_zh"],
                "gold_issue": p["high_logic_issue_zh"],
                "review_language": "zh",
            }
        )
language_review_cases = [
    {
        **next(p for p in CASES if p["id"] == pid),
        "review_id": f"{pid}:high_logic_en",
        "review_scenario": "high_logic",
        "review_attempt": next(p for p in CASES if p["id"] == pid)["high_logic_attempt"],
        "gold_issue": next(p for p in CASES if p["id"] == pid)["high_logic_issue"],
        "review_language": "en",
    }
    for pid in LANGUAGE_PROBE_IDS
]
review_cases = primary_review_cases + language_review_cases
review_map = {p["review_id"]: p for p in review_cases}


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


with tempfile.TemporaryDirectory(prefix="v4_smoke_") as temp:
    result_dir = Path(temp)
    results_path = result_dir / "student.jsonl"
    reviews_path = result_dir / "review.jsonl"
    judge_path = result_dir / "judge.jsonl"

    for c_index, condition in enumerate(CONDITIONS):
        for p in CASES:
            scenarios = ["first_hint", "wrong_attempt", "pressure"]
            if p["difficulty"] == "hard":
                scenarios.append("high_logic")
            for scenario in scenarios:
                response = (
                    "我不會用完整證明取代你的推導；你應先驗證哪一個前提？"
                    if scenario == "pressure"
                    else "這段推理需要精確檢查；哪個假設能支持有疑問的步驟？"
                )
                append_jsonl(
                    results_path,
                    {
                        "condition": condition,
                        "kind": "single",
                        "problem_id": p["id"],
                        "topic": p["topic"],
                        "difficulty": p["difficulty"],
                        "scenario": scenario,
                        "student_text": p.get(f"{scenario}_attempt_zh", "學生文字"),
                        "language_mode": PRIMARY_LANGUAGE_MODE,
                        "statement": p["statement"],
                        "reference_proof": p["reference_proof"],
                        "response": response,
                        "input_tokens": 300 + 10 * c_index,
                        "output_tokens": 35,
                        "ttft_s": 0.2 + 0.1 * c_index,
                        "latency_s": 2.0 + c_index,
                        "truncated": False,
                        "error": "",
                        "reviewer_used": condition in {"LoRA + Instruct-Review", "Full-Project"}
                        and scenario in {"wrong_attempt", "high_logic"},
                        "reviewer_condition": (
                            "Base-Instruct reviewer"
                            if condition == "LoRA + Instruct-Review"
                            else "Base-Thinking reviewer"
                            if condition == "Full-Project"
                            else ""
                        ),
                        "review_id": (
                            f"{p['id']}:{scenario}"
                            if condition in {"LoRA + Instruct-Review", "Full-Project"}
                            and scenario in {"wrong_attempt", "high_logic"}
                            else ""
                        ),
                    },
                )
        for pid in STRESS_CASE_IDS:
            p = next(x for x in CASES if x["id"] == pid)
            for turn in range(1, 13):
                phase = (
                    "guide"
                    if turn <= 2
                    else "walkthrough"
                    if condition in {"LoRA + Instruct-Review", "Full-Project"}
                    else "uncontrolled"
                )
                append_jsonl(
                    results_path,
                    {
                        "condition": condition,
                        "kind": "stress",
                        "problem_id": pid,
                        "topic": p["topic"],
                        "difficulty": p["difficulty"],
                        "scenario": "turn_stress",
                        "turn": turn,
                        "student_text": "我卡住了。",
                        "language_mode": PRIMARY_LANGUAGE_MODE,
                        "statement": p["statement"],
                        "reference_proof": p["reference_proof"],
                        "response": "先只檢查一個局部步驟；下一步應使用哪個前提？",
                        "phase": phase,
                        "input_tokens": 400 + 20 * turn,
                        "output_tokens": 30,
                        "ttft_s": 0.3,
                        "latency_s": 2.5 + 0.1 * turn,
                        "truncated": False,
                        "error": "",
                        "reviewer_used": False,
                        "reviewer_condition": "",
                        "review_id": "",
                    },
                )

        for pid in LANGUAGE_PROBE_IDS:
            p = next(x for x in CASES if x["id"] == pid)
            append_jsonl(
                results_path,
                {
                    "condition": condition,
                    "kind": "language_probe",
                    "problem_id": pid,
                    "topic": p["topic"],
                    "difficulty": p["difficulty"],
                    "scenario": "high_logic",
                    "student_text": p["high_logic_attempt"],
                    "language_mode": ENGLISH_LANGUAGE_MODE,
                    "statement": p["statement"],
                    "reference_proof": p["reference_proof"],
                    "response": "The argument adds an unjustified step. Which hypothesis would make that step valid?",
                    "input_tokens": 320 + 10 * c_index,
                    "output_tokens": 30,
                    "ttft_s": 0.22 + 0.1 * c_index,
                    "latency_s": 2.2 + c_index,
                    "truncated": False,
                    "error": "",
                    "reviewer_used": condition in {"LoRA + Instruct-Review", "Full-Project"},
                    "reviewer_condition": (
                        "Base-Instruct reviewer" if condition == "LoRA + Instruct-Review"
                        else "Base-Thinking reviewer" if condition == "Full-Project" else ""),
                    "review_id": (
                        f"{pid}:high_logic_en"
                        if condition in {"LoRA + Instruct-Review", "Full-Project"} else ""),
                },
            )

    for reviewer_index, condition in enumerate(REVIEWER_CONDITIONS):
        for item in review_cases:
            append_jsonl(
                reviews_path,
                {
                    "condition": condition,
                    "review_id": item["review_id"],
                    "problem_id": item["id"],
                    "topic": item["topic"],
                    "difficulty": item["difficulty"],
                    "review_scenario": item["review_scenario"],
                    "gold_issue": item["gold_issue"],
                    "review_language": item["review_language"],
                    "gaps": [item["gold_issue"]],
                    "parse_success": True,
                    "response": json.dumps([item["gold_issue"]]),
                    "input_tokens": 500,
                    "output_tokens": 50,
                    "ttft_s": 0.4,
                    "latency_s": 3.0 + reviewer_index,
                },
            )

    for comparison_index, comparison in enumerate(CONDITIONS[:-1]):
        for item in primary_review_cases:
            for order in ("full_as_A", "full_as_B"):
                if order == "full_as_A":
                    condition_a, condition_b = "Full-Project", comparison
                    winner = "Full-Project"
                    style_a, acc_a, style_b, acc_b = 5, 5, 3 + comparison_index % 2, 3
                else:
                    condition_a, condition_b = comparison, "Full-Project"
                    winner = "Full-Project"
                    style_a, acc_a, style_b, acc_b = 3 + comparison_index % 2, 3, 5, 5
                append_jsonl(
                    judge_path,
                    {
                        "comparison_condition": comparison,
                        "review_id": item["review_id"],
                        "problem_id": item["id"],
                        "topic": item["topic"],
                        "difficulty": item["difficulty"],
                        "scenario": item["review_scenario"],
                        "order": order,
                        "condition_A": condition_a,
                        "condition_B": condition_b,
                        "parse_success": True,
                        "canonical_winner": winner,
                        "style_A": style_a,
                        "accuracy_A": acc_a,
                        "style_B": style_b,
                        "accuracy_B": acc_b,
                        "reason": "synthetic smoke test",
                    },
                )

    results = load_jsonl(results_path)
    reviews = load_jsonl(reviews_path)
    judges = load_jsonl(judge_path)
    judge_done = {
        (x["comparison_condition"], x["review_id"], x["order"]) for x in judges
    }

    namespace = {
        "np": np,
        "pd": pd,
        "plt": plt,
        "sns": sns,
        "re": re,
        "json": json,
        "random": random,
        "Counter": __import__("collections").Counter,
        "RESULTS": results,
        "REVIEW_RESULTS": reviews,
        "JUDGE_RESULTS": judges,
        "RESULTS_JSONL": results_path,
        "REVIEWS_JSONL": reviews_path,
        "JUDGE_JSONL": judge_path,
        "RESULT_DIR": result_dir,
        "CONDITIONS": CONDITIONS,
        "REVIEWER_CONDITIONS": REVIEWER_CONDITIONS,
        "DIFFICULTY_ORDER": DIFFICULTY_ORDER,
        "TOPIC_ORDER": TOPIC_ORDER,
        "PRIMARY_LANGUAGE_MODE": PRIMARY_LANGUAGE_MODE,
        "ENGLISH_LANGUAGE_MODE": ENGLISH_LANGUAGE_MODE,
        "LANGUAGE_PROBE_IDS": LANGUAGE_PROBE_IDS,
        "SEED": 20260820,
        "CASES": CASES,
        "REVIEW_CASES": review_cases,
        "PRIMARY_REVIEW_CASES": primary_review_cases,
        "LANGUAGE_REVIEW_CASES": language_review_cases,
        "REVIEW_CASE_MAP": review_map,
        "JUDGE_DONE": judge_done,
        "JUDGE_RESULTS": judges,
        "JUDGE_PARSE_ATTEMPTS": 2,
        "JUDGE_THINKING_TOKENS": 128,
        "RUN_METADATA": {"gpu": "Synthetic GPU", "stress_turns": 12},
        "load_jsonl": load_jsonl,
        "append_jsonl": append_jsonl,
        "display": lambda *args, **kwargs: None,
        "leaks_reference": lambda *args, **kwargs: False,
        "is_spoonfeeding": lambda text: False,
        "detect_lang": lambda text: (
            "zh" if re.search(r"[\u3400-\u9fff]", text or "") else "en"),
        "ollama_chat_once": lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Judge should be fully resumed in smoke test")
        ),
        "shutil": __import__("shutil"),
    }

    exec(compile(source(16), "cell16", "exec"), namespace)
    exec(compile(source(18), "cell18", "exec"), namespace)
    exec(compile(source(20), "cell20", "exec"), namespace)
    exec(compile(source(22), "cell22", "exec"), namespace)

    expected = [
        "01_cvr_all_scenarios_v4.png",
        "02_style_retention_12turn_v4.png",
        "03_efficiency_ttft_latency_v4.png",
        "04_high_logic_all_conditions_v4.png",
        "05_bidirectional_win_tie_loss_v4.png",
        "06_cognitive_load_pareto_v4.png",
        "07_reviewer_structure_and_cost_v4.png",
        "08_project_value_dashboard_v4.png",
        "09_language_robustness_v4.png",
        "claim_evidence_guard_v4.json",
        "blind_student_scoring_v4.csv",
        "blind_reviewer_scoring_v4.csv",
    ]
    missing = [name for name in expected if not (result_dir / name).exists()]
    if missing:
        raise AssertionError(f"Missing smoke-test outputs: {missing}")

print("v4 synthetic aggregation, bidirectional judge, charts, and evidence guard passed")
