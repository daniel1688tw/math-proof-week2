# -*- coding: utf-8 -*-
"""三題 × 三情境批次評估器的純邏輯契約。"""
from pathlib import Path
from types import SimpleNamespace

try:
    import eval_full_project_questions as batch
except ModuleNotFoundError as exc:  # RED：正式評估器尚未建立
    raise AssertionError("缺少 eval_full_project_questions 批次評估器") from exc


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "math-proof-week2-full-project (1) - 複製 問題.txt"


def main() -> None:
    problems = batch.problem_specs_for_source(SOURCE)
    assert len(problems) == 3
    assert len({row["statement"] for row in problems}) == 3
    assert {row["id"] for row in problems} == {
        "CUSTOM_INTEGRAL_MVT", "CUSTOM_ABSOLUTE_PRODUCT", "CUSTOM_SHIFT_ZERO",
    }
    assert all(row["reference_proof"].strip() for row in problems)
    assert all(len(row["teach_steps_en"]) >= 3 for row in problems)
    assert all(row["misconception_instruction"].strip() for row in problems)
    assert all(not any(label in row["misconception_instruction"].lower()
                       for label in ("incorrect", "wrong", "mistake", "error", "錯誤"))
               for row in problems)

    assert batch.SCENARIOS == (
        "normal_progress", "stuck_escalation", "misconception_repair")
    assert [batch.choose_student_mode("stuck_escalation", turn, "guide", {})
            for turn in range(1, 5)] == ["force_stuck"] * 4
    assert batch.choose_student_mode(
        "normal_progress", 1, "guide", {}) == "learn_step"
    assert batch.choose_student_mode(
        "misconception_repair", 8, "review",
        {"flawed_proof_submitted": False}) == "flawed_full_proof"
    assert batch.choose_student_mode(
        "misconception_repair", 9, "review",
        {"flawed_proof_submitted": True, "active_issue": "符號錯誤"}) == "local_repair"
    assert batch.choose_student_mode(
        "normal_progress", 9, "review",
        {"active_issue": "", "flawed_proof_submitted": False,
         "tutor_reply": "沒有建立不可靠的局部訂正佇列；請重送完整證明。"}
    ) == "correct_full_proof"

    prompt = batch.build_student_prompt(
        problems[0], "normal_progress", "learn_step", [], "先找一個輔助函數。")
    assert problems[0]["reference_proof"] not in prompt
    assert "REFERENCE_PROOF" not in prompt
    repair_prompt = batch.build_student_prompt(
        problems[2], "misconception_repair", "local_repair", [],
        "請修正端點函數值。", active_issue="端點函數值計算錯誤")
    assert "current draft's definitions" in repair_prompt

    stuck_turns = [
        {"level": 0, "phase": "guide", "student_mode": "force_stuck"},
        {"level": 1, "phase": "guide", "student_mode": "force_stuck"},
        {"level": 2, "phase": "guide", "student_mode": "force_stuck"},
        {"level": 0, "phase": "walkthrough", "student_mode": "force_stuck"},
        {"level": 0, "phase": "review", "student_mode": "learn_step"},
        {"level": 0, "phase": "closed", "student_mode": "correct_full_proof"},
    ]
    assessment = batch.assess_scenario("stuck_escalation", stuck_turns, "closed")
    assert assessment["passed"]
    assert assessment["checks"]["covered_level_0_1_2"]
    assert assessment["checks"]["entered_walkthrough"]

    quality = batch.parse_quality_result({
        "verdict": "pass", "misleading": False, "answer_leakage": False,
        "scores": {
            "mathematical_correctness": 5, "pedagogical_guidance": 4,
            "level_adaptation": 5, "student_ownership": 4,
            "review_quality": 5, "closing_quality": 5,
        },
        "strengths": ["good"], "issues": [], "evidence": ["turn 2"],
    })
    assert quality and quality["scores"]["level_adaptation"] == 5
    assert batch.parse_quality_result({"verdict": "pass", "scores": {
        "mathematical_correctness": 6}}) is None

    jobs = batch.evaluation_jobs(problems)
    assert len(jobs) == 9
    assert len({(row["problem"]["id"], row["scenario"]) for row in jobs}) == 9
    assert len(batch.evaluation_jobs(
        problems, problem_id="CUSTOM_SHIFT_ZERO", scenario="stuck_escalation")) == 1
    assert batch.parse_student_result(
        '{"student_message":"I still do not know how to continue.","behavior":"stuck"}',
        "force_stuck") is not None
    assert batch.parse_student_result(
        '{"student_message":"Use M.","behavior":"attempt"}',
        "force_stuck") is None
    assert batch.parse_student_result(
        '{"student_message":"Define F and apply MVT correctly.","behavior":"full_proof"}',
        "flawed_full_proof", problems[0]) is None
    assert batch.parse_student_result(
        '{"student_message":"Apply the MVT directly to f.","behavior":"full_proof"}',
        "flawed_full_proof", problems[0]) is None
    assert batch.parse_student_result(
        '{"student_message":"Apply the MVT directly to f and claim f prime of c exists. '
        'Continuity is asserted to justify this direct application, and the resulting point c '
        'is then claimed to equal the integral average without an auxiliary function.",'
        '"behavior":"full_proof"}', "flawed_full_proof", problems[0]) is not None
    assert batch.parse_student_result(
        '{"student_message":"We incorrectly claim sum |b_n| converges.",'
        '"behavior":"full_proof"}', "flawed_full_proof", problems[1]) is None
    assert batch.parse_student_result(
        r'{"student_message":"Assume \\sum|b_n| converges from boundedness. Then combine '
        r'this alleged convergence with absolute convergence of \\sum a_n and claim that the '
        r'product series converges absolutely by multiplying the two convergent sums.",'
        r'"behavior":"full_proof"}', "flawed_full_proof", problems[1]) is not None
    assert batch.parse_student_result(
        r'{"student_message":"Since (b_n) is bounded, \\sum|b_n|=B<\\infty. Also let '
        r'\\sum|a_n|=A<\\infty; hence the absolute product series is bounded by AB and '
        r'therefore converges absolutely, which proves the required conclusion.",'
        r'"behavior":"full_proof"}', "flawed_full_proof", problems[1]) is not None
    assert batch.student_attempt_limit("flawed_full_proof") == 6
    assert batch.student_attempt_limit("learn_step") == 3
    assert batch.dialogue_complete_for_resume({
        "assessment": {"passed": True}, "quality": {"verdict": "pass"}})
    assert not batch.dialogue_complete_for_resume({
        "assessment": {"passed": True}, "quality": {"verdict": "warn"}})
    judge_prompt = batch.build_quality_judge_prompt(
        problems[0], "stuck_escalation", stuck_turns)
    assert problems[0]["reference_proof"] in judge_prompt
    assert "mathematical_correctness" in judge_prompt
    assert "answer_leakage" in judge_prompt

    class FakeDriver:
        def __init__(self):
            self.index = 0
            self.state = {"phase": "guide", "turns": [], "active_issue": "",
                          "awaiting_clean_proof": False}

        def _advance(self):
            phases = ["guide", "guide", "guide", "walkthrough", "review", "closed"]
            levels = [0, 1, 2, 0, 0, 0]
            self.state["phase"] = phases[self.index]
            self.state["turns"].append(SimpleNamespace(level=levels[self.index]))
            self.index += 1
            return "Tutor reply"

        def start(self, opener=None):
            return self._advance()

        def step(self, message):
            return self._advance()

        def turn_state_summary(self):
            return {"phase": self.state["phase"], "stuck_count": min(self.index, 2)}

        def phase_transition_report(self):
            return {"transitions": []}

    def fake_student(problem, scenario, mode, transcript, tutor_reply, active_issue=""):
        return {"student_message": "I still do not know how to continue."
                if mode == "force_stuck" else "small step",
                "behavior": "stuck" if mode == "force_stuck" else "attempt", "mode": mode}

    runtime_row = batch.run_scenario(
        problems[0], "stuck_escalation", max_turns=8,
        driver_factory=lambda problem: FakeDriver(), student_caller=fake_student,
        quality_judge=lambda problem, scenario, turns: quality)
    assert runtime_row["final_phase"] == "closed"
    assert runtime_row["assessment"]["passed"]
    assert runtime_row["quality"]["verdict"] == "pass"
    merged = batch.merge_dialogues(
        [dict(runtime_row, quality=None)], [runtime_row])
    assert len(merged) == 1 and merged[0]["quality"]["verdict"] == "pass"
    validity = batch.validate_batch([
        {"problem_id": problem["id"], "scenario": scenario,
         "assessment": {"passed": True}, "quality": quality}
        for problem in problems for scenario in batch.SCENARIOS
    ], problems)
    assert validity["valid"]
    assert validity["expected_dialogues"] == 9

    sample = [{
        "problem_id": problems[0]["id"],
        "scenario": "stuck_escalation",
        "assessment": {"passed": True},
        "quality": {
            "verdict": "pass", "misleading": False, "answer_leakage": False,
            "scores": {
                "mathematical_correctness": 5,
                "pedagogical_guidance": 4,
                "level_adaptation": 5,
                "student_ownership": 4,
                "review_quality": 5,
                "closing_quality": 5,
            },
            "strengths": ["分級清楚"], "issues": [], "evidence": ["Level 0→1→2"],
        },
        "turns": [],
    }]
    summary = batch.summarize_quality(sample)
    assert summary["dialogue_count"] == 1
    assert summary["pass_count"] == 1
    assert summary["misleading_count"] == 0
    assert summary["answer_leakage_count"] == 0
    assert summary["average_scores"]["mathematical_correctness"] == 5.0
    report = batch.render_report({"dialogues": sample, "quality_summary": summary})
    assert "助教品質總結" in report
    assert "CUSTOM_INTEGRAL_MVT" in report
    assert "Level 0→1→2" in report
    print("PASS: full-project 三題批次評估器契約")


if __name__ == "__main__":
    main()
