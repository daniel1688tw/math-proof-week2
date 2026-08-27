# -*- coding: utf-8 -*-
"""CPU-only contract tests for the verify-then-generate evaluator helpers."""
from eval_verify_then_generate import build_judge_prompt, summarize


def test_summarize_compares_the_paired_conditions():
    """A false first-error hit must not be counted as a successful hit."""
    sample = [{
        "id": "H4", "condition": "verify_then_generate",
        "reply": "你能先檢查這個定理的假設是否足夠嗎？",
        "verification": {"latency_seconds": 2.0},
        "single_question": True, "leaks_reference": False,
        "latency_seconds": 3.0,
        "judge": {"first_error_hit": True, "targetedness": 5,
                  "math_correct": True, "guidance": 5,
                  "reveal_safe": True, "rationale": "指出定理適用條件。"},
    }, {
        "id": "H4", "condition": "baseline",
        "reply": "請再想想證明還缺少什麼。",
        "verification": {"latency_seconds": 0.0},
        "single_question": True, "leaks_reference": False,
        "latency_seconds": 1.0,
        "judge": {"first_error_hit": False, "targetedness": 2,
                  "math_correct": True, "guidance": 3,
                  "reveal_safe": True, "rationale": "只泛稱有缺漏。"},
    }]

    summary = summarize(sample)

    assert summary["verify_then_generate"]["first_error_hit_rate"] == 1.0
    assert summary["baseline"]["first_error_hit_rate"] == 0.0
    assert summary["verify_then_generate"]["mean_latency_seconds"] == 3.0
    assert summary["verify_then_generate"]["mean_verifier_latency_seconds"] == 2.0


def test_judge_prompt_requires_the_first_error_and_safe_socratic_rubric():
    """The judge prompt must distinguish root-error correction from solution leakage."""
    prompt = build_judge_prompt(
        "證明題目", "錯把連續當作可微", "學生嘗試", "助教回覆")

    for key in ("first_error_hit", "targetedness", "math_correct", "guidance",
                "reveal_safe", "rationale"):
        assert key in prompt
    assert "最早／根本錯誤" in prompt
    assert "不要因蘇格拉底式回覆未給出完整解答而扣分" in prompt
    assert "不要因完整洩漏解答而加分" in prompt


if __name__ == "__main__":
    test_summarize_compares_the_paired_conditions()
    test_judge_prompt_requires_the_first_error_and_safe_socratic_rubric()
    print("PASS: verify-then-generate evaluator helpers")
