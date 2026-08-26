# -*- coding: utf-8 -*-
"""來源問題紀錄所揭露的 phase=guide 回歸案例。"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from tutor_driver import TutorDriver  # noqa: E402


PROBLEM = {
    "id": "GUIDE-V2",
    "statement": "證明一個一般數學命題。",
    "reference_proof": "先完成缺口 A，再完成缺口 B。",
}


def driver() -> TutorDriver:
    return TutorDriver(object(), object(), PROBLEM, backstop=True)


def safe_review(**overrides) -> dict:
    value = {
        "latest_student_step_status": "no_step",
        "first_missing_step": "",
        "candidate_math_error": "",
        "candidate_ownership_error": "",
        "addresses_latest_student_step": True,
        "stays_on_active_gap": True,
        "mathematically_correct": True,
        "level_policy_pass": True,
        "introduces_new_proof_idea": False,
        "completes_any_unfinished_step": False,
        "leaks_final_conclusion": False,
        "ready_for_writeup": False,
        "missing_core_step": "",
        "readiness_confidence": 0.0,
        "feedback": "",
    }
    value.update(overrides)
    return value


def test_gap_and_last_question_survive_session_snapshot() -> None:
    original = driver()
    original.state.update(
        active_gap="修正 F(a)-F(b) 的符號順序",
        last_guide_question="牛頓—萊布尼茲公式的積分順序是什麼？",
    )
    restored = driver()
    restored.load_state(original.dump_state())
    assert restored.state["active_gap"] == "修正 F(a)-F(b) 的符號順序"
    assert restored.state["last_guide_question"].endswith("？")


def test_stuck_no_step_keeps_unresolved_error_gap() -> None:
    d = driver()
    d.state["active_gap"] = "修正 F(a)-F(b) 的符號順序"
    d._update_guide_context_from_review(safe_review(
        latest_student_step_status="no_step",
        first_missing_step="說明 F 為何可導",
    ))
    assert d.state["active_gap"] == "修正 F(a)-F(b) 的符號順序"


def test_correct_step_advances_to_first_new_gap() -> None:
    d = driver()
    d.state["active_gap"] = "建立 |a_n b_n| 的上界"
    d._update_guide_context_from_review(safe_review(
        latest_student_step_status="correct",
        first_missing_step="使用比較判別法收尾",
    ))
    assert d.state["active_gap"] == "使用比較判別法收尾"


def test_level_one_and_two_must_stay_on_active_gap() -> None:
    d = driver()
    off_gap = safe_review(stays_on_active_gap=False)
    assert not d._guide_reply_review_passes(off_gap, 1)
    assert not d._guide_reply_review_passes(off_gap, 2)


def test_no_step_candidate_must_still_address_current_gap() -> None:
    d = driver()
    unaddressed = safe_review(
        latest_student_step_status="no_step",
        addresses_latest_student_step=False,
    )
    assert not d._guide_reply_review_passes(unaddressed, 0)


def test_all_guide_actions_require_exactly_one_question() -> None:
    d = driver()
    for action in ("normal_guide", "respond_attempt", "answer_clarification",
                   "refuse_tutor_write"):
        d.state.update(phase="guide", turn_action=action)
        assert d._guide_turn_requires_question()
    d.state.update(phase="review", turn_action="respond_attempt")
    assert not d._guide_turn_requires_question()


def test_level_fallback_is_actionable_and_uses_active_gap() -> None:
    d = driver()
    d.state.update(active_gap="修正 F(a)-F(b) 的符號順序",
                   turn_action="normal_guide")
    replies = [d._safe_guide_review_fallback(level) for level in (0, 1, 2)]
    assert all("修正 F(a)-F(b) 的符號順序" in reply for reply in replies)
    assert all(reply.rstrip().endswith("？") for reply in replies)
    assert all("你有什麼想法" not in reply for reply in replies)
    assert len(set(replies)) == 3


def test_same_level_fallback_rotates_without_losing_active_gap() -> None:
    d = driver()
    gap = "establish the current bound"
    d.state.update(active_gap=gap, turn_action="normal_guide", lang="en")
    first = d._safe_guide_review_fallback(1)
    second = d._safe_guide_review_fallback(1)
    assert first != second
    assert gap in first and gap in second
    assert first.rstrip().endswith("?") and second.rstrip().endswith("?")


def test_incorrect_step_fallback_names_same_error_gap() -> None:
    d = driver()
    d.state.update(active_gap="修正 F(a)-F(b) 的符號順序",
                   turn_action="respond_attempt")
    d.state["guide_reply_review"] = {
        "initial": safe_review(latest_student_step_status="incorrect")
    }
    reply = d._safe_guide_review_fallback(1)
    assert "修正 F(a)-F(b) 的符號順序" in reply
    assert reply.rstrip().endswith("？")


def test_repeated_incorrect_fallback_rotates_on_same_error() -> None:
    d = driver()
    gap = "correct the reversed endpoint difference"
    d.state.update(active_gap=gap, turn_action="respond_attempt", lang="en")
    d.state["guide_reply_review"] = {
        "initial": safe_review(latest_student_step_status="incorrect")
    }
    first = d._safe_guide_review_fallback(1)
    second = d._safe_guide_review_fallback(1)
    assert first != second
    assert gap in first and gap in second


def test_level_one_and_two_prompt_receive_same_gap_and_last_question() -> None:
    d = driver()
    d.state.update(
        phase="guide", turn_action="normal_guide",
        active_gap="修正 F(a)-F(b) 的符號順序",
        last_guide_question="積分端點的順序應如何排列？",
    )
    for level in (1, 2):
        prompt = d._system(level)
        assert "修正 F(a)-F(b) 的符號順序" in prompt
        assert "積分端點的順序應如何排列？" in prompt


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
    print(f"phase guide v2: {len(tests)}/{len(tests)} passed")
