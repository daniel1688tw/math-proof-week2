# -*- coding: utf-8 -*-
"""CPU-only contracts for the GPT-OSS 120B level dialogue evaluator."""
from pathlib import Path

from eval_limit_levels_dual_ai import (
    assess_scenario,
    build_limit_problem,
    build_student_prompt,
    choose_student_mode,
    extract_json_object,
    extract_unique_problem_statements,
    merge_dialogues,
    render_markdown,
    student_output_compliant,
    validate_evaluation,
)


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "math-proof-week2-main (main的前一版) - 複製 - 進行修改5.txt"


def test_source_log_contains_one_unique_problem_repeated_three_times():
    statements = extract_unique_problem_statements(SOURCE)

    assert len(statements) == 1
    assert "lim_{x\\to a}" in statements[0]


def test_stuck_scenario_forces_four_stuck_turns_before_learning():
    assert [
        choose_student_mode("stuck_escalation", turn, "guide", "", {})
        for turn in range(1, 5)
    ] == ["force_stuck"] * 4
    assert choose_student_mode("stuck_escalation", 5, "walkthrough", "", {}) == "learn_step"


def test_normal_scenario_declares_readiness_after_several_guided_attempts():
    assert choose_student_mode("normal_progress", 1, "guide", "", {}) == "learn_step"
    assert choose_student_mode("normal_progress", 5, "guide", "", {}) == "declare_ready"


def test_learn_step_prompt_forbids_role_drift_back_to_stuck_or_questions():
    prompt = build_student_prompt(
        build_limit_problem("證明極限為正時函數在去心鄰域為正。"),
        "stuck_escalation",
        "learn_step",
        [],
        "第 1 步：取 ε=L/2。為什麼這是合法的？",
    )

    assert "不得反問" in prompt
    assert "behavior 必須是 ready 或 attempt" in prompt


def test_force_stuck_prompt_requires_driver_detectable_strong_confusion():
    prompt = build_student_prompt(
        build_limit_problem("證明極限為正時函數在去心鄰域為正。"),
        "stuck_escalation",
        "force_stuck",
        [],
        "要讓 f(x) 為正，需要找什麼下界？",
    )

    assert "完整包含「我完全不知道怎麼繼續，完全卡住了，毫無頭緒。」" in prompt
    assert "不得用問句" in prompt


def test_misconception_scenario_routes_wrong_step_and_review_repairs():
    assert [
        choose_student_mode("misconception_repair", turn, "guide", "", {})
        for turn in range(1, 5)
    ] == ["force_stuck"] * 4
    assert choose_student_mode(
        "misconception_repair", 3, "walkthrough", "", {"misconception_used": False}
    ) == "wrong_step"
    assert choose_student_mode(
        "misconception_repair", 7, "review", "請提交完整證明", {"flawed_proof_submitted": False}
    ) == "flawed_full_proof"
    assert choose_student_mode(
        "misconception_repair", 8, "review", "請只提交局部訂正", {"active_issue": "epsilon"}
    ) == "local_repair"
    assert choose_student_mode(
        "misconception_repair", 8, "review", "請只提交這一項的局部訂正", {"active_issue": ""}
    ) == "local_repair"
    assert choose_student_mode(
        "misconception_repair", 9, "review", "請提交乾淨完整證明", {"active_issue": ""}
    ) == "clean_full_proof"


def test_assessment_requires_expected_level_and_completion_coverage():
    stuck_turns = [
        {"level": 0, "phase": "guide", "student_mode": "force_stuck"},
        {"level": 1, "phase": "guide", "student_mode": "force_stuck"},
        {"level": 2, "phase": "guide", "student_mode": "force_stuck"},
        {"level": 0, "phase": "walkthrough", "student_mode": "force_stuck"},
        {"level": 0, "phase": "walkthrough", "student_mode": "learn_step"},
        {"level": 0, "phase": "review", "student_mode": "correct_full_proof"},
        {"level": 0, "phase": "closed", "student_mode": "clean_full_proof"},
    ]
    assessment = assess_scenario("stuck_escalation", stuck_turns, "closed")

    assert assessment["passed"] is True
    assert assessment["checks"]["covered_level_0_1_2"] is True
    assert assessment["checks"]["entered_walkthrough"] is True
    assert assessment["checks"]["submitted_full_proof"] is True


def test_assessment_rejects_readiness_transition_after_latest_step_was_incorrect():
    turns = [
        {
            "level": 0,
            "phase_before": "guide",
            "phase": "review",
            "student_mode": "learn_step",
            "pre_generation_verification": {
                "status": "clear",
                "issues": [],
            },
            "guide_review": {
                "initial": {
                    "latest_student_step_status": "incorrect",
                    "ready_for_writeup": True,
                },
            },
        },
        {
            "level": 0,
            "phase_before": "review",
            "phase": "closed",
            "student_mode": "correct_full_proof",
            "pre_generation_verification": {"status": "not_applicable", "issues": []},
        },
    ]

    assessment = assess_scenario("normal_progress", turns, "closed")

    assert assessment["checks"]["incorrect_steps_never_triggered_readiness"] is False
    assert assessment["passed"] is False


def test_assessment_uses_effective_retry_or_regenerated_guide_review():
    base_turn = {
        "level": 0,
        "phase_before": "guide",
        "phase": "review",
        "student_mode": "correct_full_proof",
        "pre_generation_verification": {"status": "clear", "issues": []},
    }
    retry_incorrect = dict(base_turn, guide_review={
        "initial": None,
        "retry": {"latest_student_step_status": "incorrect"},
        "regenerated": None,
    })
    regenerated_correct = dict(base_turn, guide_review={
        "initial": {"latest_student_step_status": "incorrect"},
        "retry": None,
        "regenerated": {"latest_student_step_status": "correct"},
    })

    retry_result = assess_scenario("normal_progress", [retry_incorrect], "review")
    regenerated_result = assess_scenario(
        "normal_progress", [regenerated_correct], "review")

    assert retry_result["checks"]["incorrect_steps_never_triggered_readiness"] is False
    assert regenerated_result["checks"]["incorrect_steps_never_triggered_readiness"] is True


def test_problem_is_grounded_with_verified_steps_for_the_source_statement():
    statement = extract_unique_problem_statements(SOURCE)[0]
    problem = build_limit_problem(statement)

    assert problem["statement"] == statement
    assert "ε=L/2" in problem["reference_proof"]
    assert len(problem["hint_ladder"]) >= 2
    assert len(problem["teach_steps_en"]) >= 3
    assert problem["teach_steps_initial_status"] == "success"
    display_texts = [
        problem["reference_proof"], *problem["hint_ladder"],
        *(step["explain"] for step in problem["teach_steps_zh"]),
    ]
    assert not any(
        ord(char) < 32 and char not in "\n\r\t"
        for text in display_texts for char in text
    )
    assert "$δ>0$" in problem["teach_steps_zh"][1]["explain"]


def test_student_prompt_controls_behavior_without_exposing_reference_proof():
    problem = build_limit_problem(extract_unique_problem_statements(SOURCE)[0])
    prompt = build_student_prompt(
        problem, "misconception_repair", "wrong_step", [],
        "What lower bound do you obtain?")

    assert "GPT-OSS" in prompt
    assert "wrong_step" in prompt
    assert "student_message" in prompt
    assert problem["reference_proof"] not in prompt


def test_evaluation_requires_all_three_scenarios_and_combined_level_coverage():
    dialogues = [
        {"scenario": "normal_progress", "assessment": {"passed": True, "levels": [0]}},
        {"scenario": "stuck_escalation", "assessment": {"passed": True, "levels": [0, 1, 2]}},
        {"scenario": "misconception_repair", "assessment": {"passed": True, "levels": [0]}},
    ]

    validity = validate_evaluation(dialogues)

    assert validity["valid"] is True
    assert validity["scenario_count"] == 3
    assert validity["covered_levels"] == [0, 1, 2]


def test_json_parser_accepts_fenced_agy_output():
    parsed = extract_json_object(
        '```json\n{"student_message":"我還不會。","behavior":"stuck"}\n```')

    assert parsed == {"student_message": "我還不會。", "behavior": "stuck"}


def test_markdown_report_shows_scenario_checks_and_each_turn_level():
    payload = {
        "validity": {"valid": True, "covered_levels": [0, 1, 2]},
        "dialogues": [{
            "scenario": "stuck_escalation", "assessment": {
                "passed": True, "checks": {"entered_walkthrough": True}},
            "turns": [{"turn": 1, "level": 0, "phase": "guide",
                       "student_mode": "force_stuck", "student": "我不會",
                       "tutor": "先想想 L 的符號？"}],
        }],
    }

    report = render_markdown(payload)

    assert "valid: True" in report
    assert "Level 0" in report
    assert "stuck_escalation" in report
    assert "entered_walkthrough" in report


def test_controlled_student_outputs_must_match_the_requested_mode():
    assert student_output_compliant(
        "force_stuck", {"student_message": "我還是不知道怎麼繼續。", "behavior": "stuck"})
    assert student_output_compliant(
        "force_stuck", {
            "student_message": "我卡住了，不知道該怎麼用極限的定義開始證明…",
            "behavior": "stuck",
        })
    assert student_output_compliant(
        "force_stuck", {
            "student_message": "我真的不知道該怎麼把 ε = L/2 帶進去，完全卡住了，沒頭緒該怎麼展開。",
            "behavior": "stuck",
        })
    assert student_output_compliant(
        "wrong_step", {"student_message": "我算成 L/3。", "behavior": "wrong"})
    assert student_output_compliant(
        "flawed_full_proof", {
            "student_message": "這是完整證明：取 epsilon=-L/2，使用 <= delta，最後得到 5L/2。" * 3,
            "behavior": "full_proof",
        })
    assert student_output_compliant(
        "flawed_full_proof", {
            "student_message": (
                r"完整證明：取 \(\varepsilon=-\frac{L}{2}\)，令 "
                r"\(0<|x-a|\le\delta\)，最後推出 \(f(x)>\frac{5L}{2}\)。" * 3),
            "behavior": "full_proof",
        })
    assert not student_output_compliant(
        "force_stuck", {"student_message": "取 epsilon=L/2。", "behavior": "attempt"})
    assert student_output_compliant(
        "declare_ready", {"student_message": "我懂了，整個思路已經清楚。", "behavior": "ready"})
    assert student_output_compliant(
        "declare_ready", {"student_message": "我已掌握整個思路，現在可以寫完整證明。", "behavior": "ready"})
    assert student_output_compliant(
        "learn_step", {"student_message": "所以得到 f(x)>L/2>0，我理解這一步了。", "behavior": "ready"})


def test_resume_merge_preserves_passed_scenarios_and_replaces_retried_one():
    existing = [
        {"scenario": "normal_progress", "assessment": {"passed": True}},
        {"scenario": "misconception_repair", "assessment": {"passed": False}},
    ]
    retried = [{"scenario": "misconception_repair", "assessment": {"passed": True}}]

    merged = merge_dialogues(existing, retried)

    assert [row["scenario"] for row in merged] == [
        "normal_progress", "misconception_repair"]
    assert merged[-1]["assessment"]["passed"] is True


if __name__ == "__main__":
    test_source_log_contains_one_unique_problem_repeated_three_times()
    test_stuck_scenario_forces_four_stuck_turns_before_learning()
    test_normal_scenario_declares_readiness_after_several_guided_attempts()
    test_learn_step_prompt_forbids_role_drift_back_to_stuck_or_questions()
    test_force_stuck_prompt_requires_driver_detectable_strong_confusion()
    test_misconception_scenario_routes_wrong_step_and_review_repairs()
    test_assessment_requires_expected_level_and_completion_coverage()
    test_assessment_rejects_readiness_transition_after_latest_step_was_incorrect()
    test_assessment_uses_effective_retry_or_regenerated_guide_review()
    test_problem_is_grounded_with_verified_steps_for_the_source_statement()
    test_student_prompt_controls_behavior_without_exposing_reference_proof()
    test_evaluation_requires_all_three_scenarios_and_combined_level_coverage()
    test_json_parser_accepts_fenced_agy_output()
    test_markdown_report_shows_scenario_checks_and_each_turn_level()
    test_controlled_student_outputs_must_match_the_requested_mode()
    test_resume_merge_preserves_passed_scenarios_and_replaces_retried_one()
    print("PASS: GPT-OSS level dialogue evaluator contracts")
