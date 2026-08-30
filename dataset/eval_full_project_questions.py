# -*- coding: utf-8 -*-
"""以 agy GPT-OSS 120B 模擬學生，評估 full-project 三題的助教品質。"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

from eval_limit_levels_dual_ai import (
    REVIEW_MODEL,
    STUDENT_MODEL,
    RemoteTutorDriverMixin,
    call_agy,
    extract_json_object,
    fresh_turn_diagnostic,
    install_agy_review_backend,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_SOURCE = ROOT / "math-proof-week2-full-project (1) - 複製 問題.txt"
DEFAULT_OUTPUT = HERE / "eval_out_xdomain" / "full_project_all_questions_2026-08-30.json"
SCENARIOS = ("normal_progress", "stuck_escalation", "misconception_repair")


_PROBLEM_TEMPLATES = (
    {
        "id": "CUSTOM_INTEGRAL_MVT",
        "match": "int_a^b f(x)",
        "reference_proof": (
            "Assume a<b. Define F(x)=integral_a^x f(t)dt. By the Fundamental Theorem "
            "of Calculus, F is continuous on [a,b], differentiable on (a,b), and "
            "F'(x)=f(x). The Mean Value Theorem gives c in (a,b) such that "
            "F(b)-F(a)=F'(c)(b-a). Since F(a)=0 and F(b)=integral_a^b f(t)dt, "
            "integral_a^b f(x)dx=f(c)(b-a)."
        ),
        "hint_ladder": [
            "Represent the integral as the endpoint difference of an auxiliary function.",
            "Define F(x)=integral_a^x f(t)dt and apply the Mean Value Theorem to F.",
        ],
        "misconception_instruction": (
            "Submit a plausible full proof using this route: continuity of f is enough to "
            "'apply the MVT directly to f', which produces the required integral average value. "
            "Present every claim confidently as valid and never evaluate or qualify the route."
        ),
        "misconception_marker": "apply the mvt directly to f",
        "teach_steps_en": [
            {
                "step_id": "s1", "core_idea": "Build an antiderivative-like auxiliary function",
                "explain": ("Define F(x)=integral_a^x f(t)dt. Continuity of f and the "
                            "Fundamental Theorem of Calculus give F'(x)=f(x)."),
                "check": "What is F'(x)?", "expected_answer": "F'(x)=f(x)",
                "accepted_answers": ["f(x)", "F'(x)=f(x)"], "common_errors": [],
            },
            {
                "step_id": "s2", "core_idea": "Apply the Mean Value Theorem to F",
                "explain": ("The Mean Value Theorem gives c in (a,b) with "
                            "F(b)-F(a)=F'(c)(b-a)."),
                "check": "What equation does the Mean Value Theorem give?",
                "expected_answer": "F(b)-F(a)=F'(c)(b-a)",
                "accepted_answers": ["F(b)-F(a)=F'(c)(b-a)"], "common_errors": [],
            },
            {
                "step_id": "s3", "core_idea": "Translate back to the integral",
                "explain": ("Use F(a)=0, F(b)=integral_a^b f(t)dt, and F'(c)=f(c) "
                            "in the Mean Value Theorem identity."),
                "check": "What equality follows after substitution?",
                "expected_answer": "integral_a^b f(t)dt=f(c)(b-a)",
                "accepted_answers": ["integral_a^b f(t)dt=f(c)(b-a)"],
                "common_errors": [],
            },
        ],
    },
    {
        "id": "CUSTOM_ABSOLUTE_PRODUCT",
        "match": "a_nb_n",
        "reference_proof": (
            "Since (b_n) is bounded, there is M>=0 such that |b_n|<=M for all n. "
            "Thus |a_n b_n|=|a_n||b_n|<=M|a_n|. Since sum |a_n| converges, "
            "sum M|a_n| converges. By comparison sum |a_n b_n| converges, so "
            "sum a_n b_n converges absolutely."
        ),
        "hint_ladder": [
            "Express boundedness using one constant valid for every index.",
            "Use |b_n|<=M to bound |a_n b_n| and apply comparison.",
        ],
        "misconception_instruction": (
            "Submit a plausible full proof using this route: boundedness of (b_n) implies "
            "'sum |b_n| converges', and this yields convergence of the product series. "
            "Present every claim confidently as valid and never evaluate or qualify the route."
        ),
        "misconception_markers": [
            "sum |b_n| converges",
            "sum |b_n|=b<infty",
        ],
        "teach_steps_en": [
            {
                "step_id": "s1", "core_idea": "Convert boundedness to a uniform bound",
                "explain": "There is M>=0 such that |b_n|<=M for every n.",
                "check": "What uniform inequality does boundedness give?",
                "expected_answer": "|b_n|<=M for every n",
                "accepted_answers": ["|b_n|<=M", "|b_n|<=M for every n"],
                "common_errors": [],
            },
            {
                "step_id": "s2", "core_idea": "Bound the product term",
                "explain": "Multiply by |a_n| to get |a_n b_n|<=M|a_n|.",
                "check": "What inequality controls |a_n b_n|?",
                "expected_answer": "|a_n b_n|<=M|a_n|",
                "accepted_answers": ["|a_n b_n|<=M|a_n|"], "common_errors": [],
            },
            {
                "step_id": "s3", "core_idea": "Use the comparison test",
                "explain": ("The comparison test gives convergence of sum |a_n b_n| "
                            "from convergence of sum M|a_n|."),
                "check": "What does convergence of sum |a_n b_n| prove?",
                "expected_answer": "sum a_n b_n converges absolutely",
                "accepted_answers": ["it converges absolutely",
                                     "sum a_n b_n converges absolutely"],
                "common_errors": [],
            },
        ],
    },
    {
        "id": "CUSTOM_SHIFT_ZERO",
        "match": "f(c)=f(c+1)",
        "reference_proof": (
            "Define g(x)=f(x+1)-f(x) on [0,1]. It is continuous. We have "
            "g(1)=f(2)-f(1)=f(0)-f(1)=-g(0). If g(0)=0, take c=0. "
            "Otherwise g(0) and g(1) have opposite signs, so the Intermediate Value "
            "Theorem gives c in (0,1) with g(c)=0, hence f(c)=f(c+1)."
        ),
        "hint_ladder": [
            "Rewrite the desired equality as a continuous function being zero.",
            "Use g(x)=f(x+1)-f(x) on [0,1] and compare g(0) with g(1).",
        ],
        "misconception_instruction": (
            "Submit a plausible full proof defining g(x)=f(x+1)-f(x) on [0,2], evaluating "
            "g(2)=f(3)-f(2), and using that endpoint comparison; include the exact expression "
            "'f(3)'. Present every claim confidently as valid and never evaluate or qualify the route."
        ),
        "misconception_marker": "f(3)",
        "teach_steps_en": [
            {
                "step_id": "s1", "core_idea": "Encode the target as a zero",
                "explain": ("Define g(x)=f(x+1)-f(x) on [0,1]. It is continuous as a "
                            "difference of continuous functions."),
                "check": "What auxiliary function are we using?",
                "expected_answer": "g(x)=f(x+1)-f(x)",
                "accepted_answers": ["g(x)=f(x+1)-f(x)"], "common_errors": [],
            },
            {
                "step_id": "s2", "core_idea": "Relate endpoint values",
                "explain": ("g(0)=f(1)-f(0), g(1)=f(2)-f(1), and f(2)=f(0), "
                            "so g(1)=-g(0)."),
                "check": "What relation holds between g(1) and g(0)?",
                "expected_answer": "g(1)=-g(0)",
                "accepted_answers": ["g(1)=-g(0)"], "common_errors": [],
            },
            {
                "step_id": "s3", "core_idea": "Handle the endpoint and apply IVT",
                "explain": ("If g(0)=0 take c=0; otherwise g(0),g(1) have opposite signs, "
                            "so IVT gives g(c)=0."),
                "check": "What does g(c)=0 say about f(c) and f(c+1)?",
                "expected_answer": "f(c)=f(c+1)",
                "accepted_answers": ["f(c)=f(c+1)"], "common_errors": [],
            },
        ],
    },
)


def extract_unique_statements(path: Path) -> list[str]:
    prefix = "Custom problem:"
    values: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith(prefix):
            statement = line[len(prefix):].strip()
            if statement and statement not in values:
                values.append(statement)
    return values


def _compact_math(text: str) -> str:
    return re.sub(r"[\s\\(){}]", "", text).lower()


def problem_specs_for_source(path: Path) -> list[dict]:
    statements = extract_unique_statements(path)
    problems: list[dict] = []
    for statement in statements:
        compact = _compact_math(statement)
        template = next(
            (row for row in _PROBLEM_TEMPLATES
             if _compact_math(str(row["match"])) in compact), None)
        if template is None:
            raise RuntimeError(f"題目缺少已驗證評估規格：{statement}")
        problem = {key: value for key, value in template.items() if key != "match"}
        problem.update(
            statement=statement,
            teach_steps_initial_status="success",
            teach_steps_source_en="manual_verified_reference",
        )
        problems.append(problem)
    if len(problems) != len(_PROBLEM_TEMPLATES):
        raise RuntimeError(f"預期 3 個唯一題目，實得 {len(problems)} 個")
    return problems


def choose_student_mode(scenario: str, turn_index: int, phase: str,
                        state: dict) -> str:
    if phase == "closed":
        return "done"
    if phase == "review":
        if state.get("active_issue"):
            return "local_repair"
        if state.get("awaiting_clean_proof"):
            return "clean_full_proof"
        if scenario == "misconception_repair" and not state.get("flawed_proof_submitted"):
            return "flawed_full_proof"
        return "correct_full_proof"
    if phase == "walkthrough":
        return "learn_step"
    if scenario == "stuck_escalation" and turn_index <= 4:
        return "force_stuck"
    return "learn_step"


def build_student_prompt(problem: dict, scenario: str, mode: str,
                         transcript: list[dict], tutor_reply: str,
                         active_issue: str = "") -> str:
    history = "\n".join(
        ("Tutor: " if row["role"] == "tutor" else "Student: ") + row["text"]
        for row in transcript[-18:])
    instructions = {
        "force_stuck": (
            "Set student_message exactly to 'I still do not know how to continue.' and behavior "
            "to stuck. Do not include any mathematical idea, theorem, formula, or symbol."
        ),
        "learn_step": (
            "Respond only to the tutor's latest question with the smallest relevant step. Do not "
            "write a complete proof unless explicitly requested. If unclear, ask one local question."
        ),
        "correct_full_proof": (
            "The tutor requested a full proof. Write a self-contained mathematically correct proof "
            "using only the ideas learned in the conversation. Set behavior to full_proof."
        ),
        "flawed_full_proof": problem["misconception_instruction"] +
            " Set behavior to full_proof.",
        "local_repair": (
            f"The tutor identified this current issue: {active_issue}. Submit only a mathematically "
            "correct local replacement for that issue, not a full proof. Preserve and use the "
            "current draft's definitions exactly; do not switch back to a different convention "
            "from an earlier guide turn. Set behavior to local_repair."
        ),
        "clean_full_proof": (
            "Submit a clean, self-contained, corrected full proof without correction notes. "
            "Set behavior to full_proof."
        ),
        "done": "Briefly acknowledge completion. Set behavior to done.",
    }[mode]
    return f"""You are a realistic beginning student in an advanced mathematics proof course.

Problem: {problem['statement']}
Scenario: {scenario}
Current conversation:
{history or '(no earlier turns)'}
Latest tutor reply: {tutor_reply or '(none yet)'}

You cannot see any reference proof. Do not use tools or external sources. Follow the controlled
instruction exactly, do not evaluate the tutor, and do not mention role-playing. Prefer plain English
and ASCII mathematical notation. Return JSON only:
{{"student_message":"next student message","behavior":"stuck|attempt|question|full_proof|local_repair|done"}}

Controlled instruction: {instructions}"""


def assess_scenario(scenario: str, turns: list[dict], final_phase: str) -> dict:
    levels = [row.get("level") for row in turns]
    phases = [row.get("phase") for row in turns]
    modes = [row.get("student_mode") for row in turns]
    checks = {
        "finished_closed": final_phase == "closed",
        "entered_review": "review" in phases or "closed" in phases,
    }
    if scenario == "stuck_escalation":
        checks.update(
            covered_level_0_1_2=all(level in levels for level in (0, 1, 2)),
            entered_walkthrough="walkthrough" in phases,
            forced_stuck_prefix=modes[:4] == ["force_stuck"] * 4,
        )
    elif scenario == "misconception_repair":
        checks.update(
            flawed_proof_submitted="flawed_full_proof" in modes,
            attempted_local_repair="local_repair" in modes,
        )
    else:
        checks["normal_progress_without_forced_stuck"] = "force_stuck" not in modes
    return {"passed": all(checks.values()), "checks": checks,
            "levels": levels, "phases": phases, "modes": modes}


_SCORE_NAMES = (
    "mathematical_correctness", "pedagogical_guidance", "level_adaptation",
    "student_ownership", "review_quality", "closing_quality",
)


def parse_quality_result(value: object) -> dict | None:
    if not isinstance(value, dict) or value.get("verdict") not in {"pass", "warn", "fail"}:
        return None
    scores = value.get("scores")
    if not isinstance(scores, dict) or any(
            not isinstance(scores.get(name), (int, float))
            or not 1 <= float(scores[name]) <= 5 for name in _SCORE_NAMES):
        return None
    if not isinstance(value.get("misleading"), bool) or not isinstance(
            value.get("answer_leakage"), bool):
        return None
    return {
        "verdict": value["verdict"],
        "misleading": value["misleading"],
        "answer_leakage": value["answer_leakage"],
        "scores": {name: float(scores[name]) for name in _SCORE_NAMES},
        "strengths": [str(item) for item in value.get("strengths") or []][:8],
        "issues": [str(item) for item in value.get("issues") or []][:8],
        "evidence": [str(item) for item in value.get("evidence") or []][:12],
    }


def evaluation_jobs(problems: list[dict], problem_id: str | None = None,
                    scenario: str | None = None) -> list[dict]:
    return [
        {"problem": problem, "scenario": scenario_name}
        for problem in problems
        if not problem_id or problem["id"] == problem_id
        for scenario_name in SCENARIOS
        if not scenario or scenario_name == scenario
    ]


def parse_student_result(raw: str, mode: str, problem: dict | None = None) -> dict | None:
    value = extract_json_object(raw)
    if not isinstance(value, dict):
        return None
    message = str(value.get("student_message") or "").strip()
    behavior = str(value.get("behavior") or "").strip()
    if not message:
        return None
    expected = {
        "force_stuck": "stuck", "correct_full_proof": "full_proof",
        "flawed_full_proof": "full_proof", "clean_full_proof": "full_proof",
        "local_repair": "local_repair", "done": "done",
    }.get(mode)
    if expected and behavior != expected:
        return None
    if mode == "force_stuck" and message != "I still do not know how to continue.":
        return None
    if mode == "flawed_full_proof" and problem:
        # 單句錯誤斷言不是「完整草稿」，不能算已真正測到審閱工作流。
        if len(message) < 120:
            return None
        raw_markers = problem.get("misconception_markers") or [
            problem.get("misconception_marker") or ""
        ]
        markers = [_compact_math(str(marker)) for marker in raw_markers if marker]
        compact_message = _compact_math(message)
        if markers and not any(marker in compact_message for marker in markers):
            return None
        if re.search(r"\b(?:incorrect|incorrectly|wrong|mistake|error)\b|錯誤|不正確|刻意|故意",
                     message, flags=re.I):
            return None
    return {"student_message": message, "behavior": behavior, "mode": mode}


def build_quality_judge_prompt(problem: dict, scenario: str, turns: list[dict]) -> str:
    transcript = "\n\n".join(
        f"Turn {row.get('turn')} | Level {row.get('level')} | "
        f"{row.get('phase_before')}->{row.get('phase')}\n"
        f"Student: {row.get('student', '')}\nTutor: {row.get('tutor', '')}"
        for row in turns)
    return f"""You are an independent evaluator of an advanced-mathematics proof tutor.

Problem:
{problem['statement']}

Verified reference proof (hidden from the simulated student):
{problem['reference_proof']}

Scenario: {scenario}
Dialogue:
{transcript}

Evaluate the tutor, not the student. Check every mathematical assertion independently. A walkthrough
may reveal exactly one verified step only after repeated stuck turns; that is permitted. Mark
answer_leakage=true only for premature disclosure of the overall proof or later steps. Mark
misleading=true for any false, materially ambiguous, or unjustified mathematical claim by the tutor.
For misconception_repair, verify that the planted error was identified and not endorsed. Scores use
1 (unacceptable) through 5 (excellent): mathematical_correctness, pedagogical_guidance,
level_adaptation, student_ownership, review_quality, closing_quality.

Return JSON only:
{{"verdict":"pass|warn|fail","misleading":false,"answer_leakage":false,
"scores":{{"mathematical_correctness":1,"pedagogical_guidance":1,
"level_adaptation":1,"student_ownership":1,"review_quality":1,"closing_quality":1}},
"strengths":["..."],"issues":["..."],"evidence":["cite turn numbers and exact behavior"]}}"""


def student_attempt_limit(mode: str) -> int:
    """錯誤植入較容易被強模型自行修正，因此容許更多受控重試。"""
    return 6 if mode == "flawed_full_proof" else 3


def call_student(problem: dict, scenario: str, mode: str,
                 transcript: list[dict], tutor_reply: str,
                 active_issue: str = "") -> dict:
    prompt = build_student_prompt(
        problem, scenario, mode, transcript, tutor_reply, active_issue)
    raw = ""
    attempt_limit = student_attempt_limit(mode)
    for attempt in range(attempt_limit):
        print(f"[student] {problem['id']} scenario={scenario} mode={mode} "
              f"attempt={attempt + 1}", flush=True)
        raw = call_agy(STUDENT_MODEL, prompt)
        parsed = parse_student_result(raw, mode, problem)
        if parsed is not None:
            return parsed
        prompt += ("\nYour previous output violated the controlled instruction. Return one valid "
                   "JSON object and obey the required behavior exactly.")
        if mode == "flawed_full_proof":
            marker = (problem.get("misconception_marker")
                      or (problem.get("misconception_markers") or [""])[0])
            prompt += (
                " This is a robustness test of the tutor, not a request for you to correct the "
                "argument. The student_message must confidently contain this exact claim: "
                f"{marker!r}. Do not replace it with a valid proof route and do not label it as "
                "an error.")
    raise RuntimeError(f"GPT-OSS student output invalid for {mode}: {raw[-500:]}")


def judge_quality(problem: dict, scenario: str, turns: list[dict]) -> dict | None:
    prompt = build_quality_judge_prompt(problem, scenario, turns)
    for attempt in range(3):
        print(f"[quality-judge] {problem['id']} scenario={scenario} attempt={attempt + 1}",
              flush=True)
        raw = call_agy(REVIEW_MODEL, prompt)
        parsed = parse_quality_result(extract_json_object(raw))
        if parsed is not None:
            return parsed
        prompt += "\nThe previous response was invalid. Return the exact JSON schema only."
    return None


def _default_driver_factory(problem: dict):
    from tutor_driver import TutorDriver

    class RemoteTutorDriver(RemoteTutorDriverMixin, TutorDriver):
        pass

    return RemoteTutorDriver(
        tok=object(), model=object(), problem=dict(problem),
        backstop=True, verify_then_generate=True)


def run_scenario(problem: dict, scenario: str, max_turns: int = 24,
                 driver_factory=None, student_caller=None,
                 quality_judge=None) -> dict:
    driver = (driver_factory or _default_driver_factory)(problem)
    student_fn = student_caller or call_student
    quality_fn = quality_judge or judge_quality
    transcript: list[dict] = []
    turns: list[dict] = []
    control = {"flawed_proof_submitted": False}
    tutor_reply = ""
    for turn_index in range(1, max_turns + 1):
        phase_before = str(driver.state.get("phase") or "guide")
        if phase_before == "closed":
            break
        review_issues = driver.state.get("review_issues") or []
        review_idx = int(driver.state.get("review_issue_idx") or 0)
        active_issue = ""
        if review_idx < len(review_issues):
            issue = review_issues[review_idx]
            active_issue = str(
                issue.get("description") if isinstance(issue, dict) else issue)
        mode_state = dict(control)
        mode_state.update(
            active_issue=active_issue,
            awaiting_clean_proof=driver.state.get("awaiting_clean_proof"),
            tutor_reply=tutor_reply,
        )
        mode = choose_student_mode(scenario, turn_index, phase_before, mode_state)
        student = student_fn(
            problem, scenario, mode, transcript, tutor_reply, active_issue=active_issue)
        if mode == "flawed_full_proof":
            control["flawed_proof_submitted"] = True
        previous_pre = driver.state.get("pre_generation_verification")
        previous_guide = driver.state.get("guide_reply_review")
        previous_walk = driver.state.get("walkthrough_review")
        started = time.time()
        tutor_reply = (driver.start(opener=student["student_message"])
                       if turn_index == 1 else driver.step(student["student_message"]))
        state = driver.turn_state_summary()
        log = driver.state["turns"][-1] if driver.state.get("turns") else None
        row = {
            "turn": turn_index, "level": log.level if log else None,
            "phase_before": phase_before, "phase": state.get("phase"),
            "student_mode": mode, "student_behavior": student.get("behavior"),
            "student": student["student_message"], "tutor": tutor_reply,
            "tutor_latency_seconds": round(time.time() - started, 3), "state": state,
            "pre_generation_verification": fresh_turn_diagnostic(
                previous_pre, driver.state.get("pre_generation_verification")),
            "guide_review": fresh_turn_diagnostic(
                previous_guide, driver.state.get("guide_reply_review")),
            "walkthrough_review": fresh_turn_diagnostic(
                previous_walk, driver.state.get("walkthrough_review")),
        }
        turns.append(row)
        transcript.extend((
            {"role": "student", "text": student["student_message"]},
            {"role": "tutor", "text": tutor_reply},
        ))
        print(f"[{problem['id']} {scenario} turn {turn_index}] level={row['level']} "
              f"phase={phase_before}->{row['phase']} mode={mode}\n"
              f"Student: {row['student']}\nTutor: {row['tutor']}", flush=True)
    final_phase = str(driver.state.get("phase") or "")
    assessment = assess_scenario(scenario, turns, final_phase)
    quality = quality_fn(problem, scenario, turns)
    return {
        "problem_id": problem["id"], "statement": problem["statement"],
        "scenario": scenario, "turns": turns, "final_phase": final_phase,
        "phase_report": driver.phase_transition_report(),
        "assessment": assessment, "quality": quality,
    }


def merge_dialogues(existing: list[dict], updates: list[dict]) -> list[dict]:
    merged = {
        (row.get("problem_id"), row.get("scenario")): row
        for row in existing
    }
    for row in updates:
        merged[(row.get("problem_id"), row.get("scenario"))] = row
    return [merged[key] for key in sorted(merged)]


def dialogue_complete_for_resume(row: dict) -> bool:
    """只有結構與品質都正式通過才略過；warn 必須允許定向重跑。"""
    return (row.get("assessment", {}).get("passed") is True
            and row.get("quality", {}).get("verdict") == "pass")


def validate_batch(dialogues: list[dict], problems: list[dict],
                   expected_pairs: set[tuple[str, str]] | None = None) -> dict:
    expected = expected_pairs or {
        (problem["id"], scenario) for problem in problems for scenario in SCENARIOS}
    actual = {(row.get("problem_id"), row.get("scenario")) for row in dialogues}
    relevant = [row for row in dialogues
                if (row.get("problem_id"), row.get("scenario")) in expected]
    structural_pass = all(row.get("assessment", {}).get("passed") is True
                          for row in relevant)
    judges_complete = all(isinstance(row.get("quality"), dict) for row in relevant)
    quality_pass = all(row.get("quality", {}).get("verdict") != "fail" for row in relevant)
    return {
        "valid": actual.issuperset(expected) and structural_pass and judges_complete and quality_pass,
        "expected_dialogues": len(expected),
        "completed_dialogues": len(actual & expected),
        "missing": [f"{problem_id}/{scenario}" for problem_id, scenario in sorted(expected - actual)],
        "structural_pass": structural_pass,
        "judges_complete": judges_complete,
        "quality_pass": quality_pass,
    }


def summarize_quality(dialogues: list[dict]) -> dict:
    available = [row for row in dialogues if isinstance(row.get("quality"), dict)]
    averages = {}
    for name in _SCORE_NAMES:
        values = [float(row["quality"].get("scores", {}).get(name)) for row in available
                  if isinstance(row["quality"].get("scores", {}).get(name), (int, float))]
        averages[name] = round(sum(values) / len(values), 3) if values else None
    return {
        "dialogue_count": len(dialogues),
        "pass_count": sum(row.get("quality", {}).get("verdict") == "pass" for row in available),
        "warn_count": sum(row.get("quality", {}).get("verdict") == "warn" for row in available),
        "fail_count": sum(row.get("quality", {}).get("verdict") == "fail" for row in available),
        "judge_unavailable_count": len(dialogues) - len(available),
        "misleading_count": sum(bool(row.get("quality", {}).get("misleading")) for row in available),
        "answer_leakage_count": sum(bool(row.get("quality", {}).get("answer_leakage"))
                                    for row in available),
        "average_scores": averages,
    }


def render_report(payload: dict) -> str:
    summary = payload.get("quality_summary") or summarize_quality(payload.get("dialogues") or [])
    lines = ["# full-project 全題助教品質評估", "", "## 助教品質總結", "",
             f"- 對話數：{summary.get('dialogue_count', 0)}",
             f"- 通過／警告／失敗：{summary.get('pass_count', 0)}／"
             f"{summary.get('warn_count', 0)}／{summary.get('fail_count', 0)}",
             f"- 誤導：{summary.get('misleading_count', 0)}",
             f"- 提前答案洩漏：{summary.get('answer_leakage_count', 0)}", "",
             "### 平均分（1–5）", ""]
    for name, score in (summary.get("average_scores") or {}).items():
        lines.append(f"- {name}: {score if score is not None else 'N/A'}")
    for dialogue in payload.get("dialogues") or []:
        quality = dialogue.get("quality") or {}
        lines.extend(["", f"## {dialogue.get('problem_id')}／{dialogue.get('scenario')}", "",
                      f"- 結構檢查：{dialogue.get('assessment', {}).get('passed')}",
                      f"- 品質判定：{quality.get('verdict', 'unavailable')}"])
        for evidence in quality.get("evidence") or []:
            lines.append(f"- 證據：{evidence}")
        for issue in quality.get("issues") or []:
            lines.append(f"- 問題：{issue}")
        for turn in dialogue.get("turns") or []:
            lines.extend(["", f"### Turn {turn.get('turn')}｜Level {turn.get('level')}｜"
                          f"{turn.get('phase_before')}→{turn.get('phase')}", "",
                          f"- Student: {turn.get('student')}",
                          f"- Tutor: {turn.get('tutor')}"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--problem")
    parser.add_argument("--scenario", choices=SCENARIOS)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    problems = problem_specs_for_source(args.source)
    jobs = evaluation_jobs(problems, args.problem, args.scenario)
    if not jobs:
        raise RuntimeError("篩選後沒有可執行的題目／情境")
    install_agy_review_backend()
    dialogues: list[dict] = []
    if args.resume and args.output.exists():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        dialogues = list(previous.get("dialogues") or [])
    expected_pairs = {
        (job["problem"]["id"], job["scenario"]) for job in jobs
    }
    completed = {
        (row.get("problem_id"), row.get("scenario"))
        for row in dialogues
        if dialogue_complete_for_resume(row)
    }
    for job in jobs:
        key = (job["problem"]["id"], job["scenario"])
        if args.resume and key in completed:
            print(f"[resume-skip] {key[0]} {key[1]}", flush=True)
            continue
        row = run_scenario(job["problem"], job["scenario"])
        dialogues = merge_dialogues(dialogues, [row])
        relevant = [item for item in dialogues
                    if (item.get("problem_id"), item.get("scenario")) in expected_pairs]
        report_dialogues = dialogues if args.resume else relevant
        payload = {
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "source_file": args.source.name,
            "assistant": "Qwen3-4B-Instruct-2507 + qlora_adapter_v9 on lab RTX 4090 GPU1",
            "student": f"agy {STUDENT_MODEL}",
            "quality_reviewer": f"agy {REVIEW_MODEL}",
            "dialogues": dialogues,
            "quality_summary": summarize_quality(report_dialogues),
        }
        payload["validity"] = validate_batch(
            dialogues, problems, None if args.resume else expected_pairs)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        args.output.with_suffix(".md").write_text(
            render_report(payload), encoding="utf-8")
    validity = validate_batch(dialogues, problems, expected_pairs)
    print(f"RESULT_FILE={args.output}", flush=True)
    if not validity["judges_complete"]:
        return 2
    return 0 if validity["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
