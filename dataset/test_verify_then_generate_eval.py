# -*- coding: utf-8 -*-
"""CPU-only contract tests for the verify-then-generate evaluator helpers."""
import os
import sys
import types
import review_backstop

from eval_verify_then_generate import (
    CASE_IDS,
    _v9_adapter_dir,
    build_judge_prompt,
    evaluation_exit_code,
    judge_record,
    prepare_rejudge_metadata,
    render_markdown,
    successful_treatment_n,
    summarize,
)


def test_case_manifest_contains_only_feature_eligible_routes():
    """H6 routes to the existing review backstop, not guide/respond_attempt."""
    assert CASE_IDS == ("H1", "H2", "H3", "H4", "H5", "H7", "H8")


def test_find_gaps_retries_once_when_structured_output_is_invalid():
    """A single malformed verifier sample must not invalidate the whole A/B run."""
    replies = iter(["not JSON", '["first issue"]'])
    original = review_backstop._chat_content
    review_backstop._chat_content = lambda *args, **kwargs: next(replies)
    try:
        assert review_backstop.find_gaps("statement", "reference", "draft", timeout=10) == [
            "first issue",
        ]
    finally:
        review_backstop._chat_content = original


def test_find_gaps_falls_back_to_strict_issue_lines_after_json_failures():
    """Repeated malformed JSON should trigger a separately parsed low-temperature review."""
    replies = iter(["not JSON", "still not JSON", "ISSUE: missing theorem premise"])
    calls = []
    original = review_backstop._chat_content

    def fake_chat(*args, **kwargs):
        calls.append((args, kwargs))
        return next(replies)

    review_backstop._chat_content = fake_chat
    try:
        assert review_backstop.find_gaps("statement", "reference", "draft", timeout=10) == [
            "missing theorem premise",
        ]
    finally:
        review_backstop._chat_content = original
    assert calls[-1][0][0] == review_backstop.CRITIC_TEXT_FALLBACK_SYSTEM
    assert calls[-1][1]["temperature"] == 0.05


def test_find_gaps_fallback_accepts_only_explicit_clear():
    """An explicit CLEAR may produce [], while arbitrary prose must never do so."""
    replies = iter(["bad", "bad again", "CLEAR"])
    original = review_backstop._chat_content
    review_backstop._chat_content = lambda *args, **kwargs: next(replies)
    try:
        assert review_backstop.find_gaps("statement", "reference", "draft", timeout=10) == []
    finally:
        review_backstop._chat_content = original
    assert review_backstop._parse_gap_lines("No issues found") is None


def test_render_markdown_omits_empty_verifier_detail_without_trailing_space():
    """Disabled baseline verification should still produce diff-clean Markdown."""
    metric = {
        "first_error_hit_rate": None, "targetedness_mean": None,
        "math_correct_rate": None, "guidance_mean": None,
        "reveal_safe_rate": None, "single_question_rate": 1.0,
        "no_reference_leak_rate": 1.0, "mean_latency_seconds": 1.0,
    }
    records = [{
        "id": "H1", "condition": "baseline", "latency_seconds": 1.0,
        "reply": "question?", "judge": None,
        "verification": {"status": "disabled", "first_issue": ""},
    }]
    rendered = render_markdown(
        records, {"baseline": metric, "verify_then_generate": metric},
        {"generator": "v9", "verifier": "thinking"})

    assert "- verifier: disabled\n" in rendered
    assert all(line == line.rstrip() for line in rendered.splitlines())


def test_summarize_compares_the_paired_conditions():
    """A false first-error hit must not be counted as a successful hit."""
    sample = [{
        "id": "H4", "condition": "verify_then_generate",
        "reply": "你能先檢查這個定理的假設是否足夠嗎？",
        "verification": {"status": "clear", "latency_seconds": 2.0},
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


def test_summary_counts_successful_treatment_verifier_calls():
    """Unavailable verification must leave the treatment evaluation invalid."""
    records = [{
        "id": "H4", "condition": "verify_then_generate",
        "verification": {"status": "unavailable", "latency_seconds": 1.0},
        "single_question": True, "leaks_reference": False, "latency_seconds": 2.0,
        "judge": None,
    }, {
        "id": "H5", "condition": "verify_then_generate",
        "verification": {"status": "not_applicable", "latency_seconds": 0.0},
        "single_question": True, "leaks_reference": False, "latency_seconds": 2.0,
        "judge": None,
    }]

    summary = summarize(records)

    assert summary["verify_then_generate"]["verification_status_counts"] == {
        "unavailable": 1, "not_applicable": 1,
    }
    assert summary["verify_then_generate"]["valid_treatment_n"] == 0
    assert successful_treatment_n(records) == 0
    assert evaluation_exit_code(records, judge_requested=False) == 1


def test_incomplete_treatment_verification_cannot_be_reported_as_a_valid_evaluation():
    """One verified pair cannot validate an eight-pair treatment comparison."""
    records = []
    for index in range(1, 9):
        case_id = f"H{index}"
        records.append({
            "id": case_id, "condition": "baseline",
            "verification": {"status": "not_applicable", "latency_seconds": 0.0},
            "single_question": True, "leaks_reference": False, "latency_seconds": 1.0,
            "judge": {"first_error_hit": False, "targetedness": 1,
                      "math_correct": True, "guidance": 1,
                      "reveal_safe": True, "rationale": "baseline"},
        })
        verified = index == 1
        records.append({
            "id": case_id, "condition": "verify_then_generate",
            "verification": {
                "status": "clear" if verified else "unavailable",
                "latency_seconds": 1.0,
            },
            "single_question": True, "leaks_reference": False, "latency_seconds": 2.0,
            "judge": {"first_error_hit": verified, "targetedness": 5 if verified else 1,
                      "math_correct": True, "guidance": 5 if verified else 1,
                      "reveal_safe": True, "rationale": "treatment"},
        })

    summary = summarize(records)

    assert summary["verify_then_generate"]["first_error_hit_rate"] == 1.0
    assert evaluation_exit_code(records, judge_requested=True) == 1


def test_v9_adapter_guard_rejects_a_non_v9_override():
    """A FINAL_ADAPTER override must not silently change this v9 experiment."""
    previous = os.environ.get("FINAL_ADAPTER")
    os.environ["FINAL_ADAPTER"] = "qlora_adapter_v10"
    try:
        try:
            _v9_adapter_dir()
        except ValueError as error:
            assert "qlora_adapter_v9" in str(error)
        else:
            raise AssertionError("non-v9 FINAL_ADAPTER was accepted")
    finally:
        if previous is None:
            os.environ.pop("FINAL_ADAPTER", None)
        else:
            os.environ["FINAL_ADAPTER"] = previous


def test_judge_record_rejects_boolean_scores():
    """Boolean values are not valid 1-to-5 targetedness or guidance scores."""
    fake_module = types.SimpleNamespace(
        claude_call=lambda prompt: "ignored",
        parse_json_obj=lambda raw: {
            "first_error_hit": True, "targetedness": True,
            "math_correct": True, "guidance": 5,
            "reveal_safe": True, "rationale": "bad score type",
        },
    )
    original = sys.modules.get("regression_suite")
    sys.modules["regression_suite"] = fake_module
    try:
        assert judge_record({
            "statement": "題目", "planted_error": "錯誤", "attempt": "嘗試", "reply": "回覆",
        }) is None
    finally:
        if original is None:
            del sys.modules["regression_suite"]
        else:
            sys.modules["regression_suite"] = original


def test_rejudge_preserves_generation_provenance_and_rejects_mixed_judges():
    """Rejudging cannot hide a pre-existing judgement from another backend."""
    saved_metadata = {
        "generator": "Qwen3-4B + qlora_adapter_v9",
        "adapter_dir": "C:/models/qlora_adapter_v9",
        "verifier": "qwen3-thinking",
    }
    current = {"backend": "antigravity", "model": "Gemini 3.6 Flash (Medium)"}
    preserved = prepare_rejudge_metadata(saved_metadata, [], current)
    assert preserved["adapter_dir"] == "C:/models/qlora_adapter_v9"
    assert preserved["verifier"] == "qwen3-thinking"

    prior = [{"judge": {"provenance": {"backend": "claude", "model": "sonnet"}}}]
    try:
        prepare_rejudge_metadata(saved_metadata, prior, current)
    except ValueError as error:
        assert "跨 backend" in str(error)
    else:
        raise AssertionError("mixed judge provenance was accepted")


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
    test_case_manifest_contains_only_feature_eligible_routes()
    test_find_gaps_retries_once_when_structured_output_is_invalid()
    test_find_gaps_falls_back_to_strict_issue_lines_after_json_failures()
    test_find_gaps_fallback_accepts_only_explicit_clear()
    test_render_markdown_omits_empty_verifier_detail_without_trailing_space()
    test_summarize_compares_the_paired_conditions()
    test_summary_counts_successful_treatment_verifier_calls()
    test_incomplete_treatment_verification_cannot_be_reported_as_a_valid_evaluation()
    test_v9_adapter_guard_rejects_a_non_v9_override()
    test_judge_record_rejects_boolean_scores()
    test_rejudge_preserves_generation_provenance_and_rejects_mixed_judges()
    test_judge_prompt_requires_the_first_error_and_safe_socratic_rubric()
    print("PASS: verify-then-generate evaluator helpers")
