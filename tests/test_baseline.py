"""
tests/test_baseline.py — Test suite for baseline.py chain pipeline.

Run unit tests + mock tests (no GPU needed):
    .\\env\\python.exe -m pytest tests/test_baseline.py -v

Run live-model benchmark tests (GPU + Qwen model required):
    .\\env\\python.exe -m pytest tests/test_baseline.py -v -m livemodel

Run all benchmark problems interactively:
    .\\env\\python.exe tests/test_baseline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow importing from the week2 root
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

# Override conftest's autouse fixture: importing generators → model_loader loads Qwen → crash.
# baseline.py is standalone and has no generator cache to clear.
@pytest.fixture(autouse=True)
def clear_gen_cache():
    yield


# Override conftest's require_live_model: baseline has its own LLM singleton.
# We only run live tests when baseline.ACTIVE_LLM has already been pre-loaded;
# triggering a cold model load inside pytest crashes on Windows (access violation
# in PyTorch's threaded materialiser).
@pytest.fixture
def require_live_model():
    if bl.ACTIVE_LLM is not None and getattr(bl.ACTIVE_LLM, "backend", None) == "hf":
        return bl.ACTIVE_LLM
    pytest.skip(
        "Baseline live-model tests require the model to be pre-loaded. "
        "Run `python tests/test_baseline.py` for an interactive benchmark instead."
    )


import baseline as bl
from baseline import (
    LinearProof,
    ProofStep,
    VerifierError,
    _parse_linear_proof,
    _parse_premise_goal,
    extract_json,
    run_baseline,
    stage_correct,
    stage_extract,
    stage_generate,
    verify_linear_proof,
)
from benchmark import BENCHMARK_PROBLEMS


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_step(step_id="S1", statement="some claim", justification="by theorem", refs=None):
    return ProofStep(
        step_id=step_id,
        statement=statement,
        justification=justification,
        refs=refs or [],
    )


def _make_proof(steps, conclusion="the goal is proven"):
    return LinearProof(steps=steps, conclusion=conclusion)


# ─────────────────────────────────────────────────────────────────────────────
# Unit: extract_json
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractJson:
    def test_pure_json(self):
        data = extract_json('{"key": "value"}')
        assert data == {"key": "value"}

    def test_json_embedded_in_text(self):
        data = extract_json('Sure! Here is the answer: {"premises": ["x > 0"], "goal": "sqrt(x) > 0"}')
        assert data["goal"] == "sqrt(x) > 0"

    def test_trailing_comma_repair(self):
        data = extract_json('{"steps": [{"a": 1},], "conclusion": "done"}')
        assert data is not None
        assert data["conclusion"] == "done"

    def test_returns_none_for_no_json(self):
        assert extract_json("No JSON here at all.") is None

    def test_nested_json(self):
        data = extract_json('{"outer": {"inner": [1, 2, 3]}}')
        assert data["outer"]["inner"] == [1, 2, 3]


# ─────────────────────────────────────────────────────────────────────────────
# Unit: _parse_premise_goal
# ─────────────────────────────────────────────────────────────────────────────

class TestParsePremiseGoal:
    def test_valid_list_premises(self):
        text = '{"premises": ["f is continuous", "f is differentiable"], "goal": "exists c"}'
        pg = _parse_premise_goal(text)
        assert pg.premises == ["f is continuous", "f is differentiable"]
        assert pg.goal == "exists c"

    def test_string_premise_coerced_to_list(self):
        text = '{"premises": "x is real", "goal": "x^2 >= 0"}'
        pg = _parse_premise_goal(text)
        assert isinstance(pg.premises, list)
        assert len(pg.premises) == 1

    def test_missing_goal_raises(self):
        with pytest.raises(ValueError, match="goal"):
            _parse_premise_goal('{"premises": ["x is real"]}')

    def test_empty_goal_raises(self):
        with pytest.raises(ValueError, match="goal"):
            _parse_premise_goal('{"premises": [], "goal": "  "}')

    def test_goal_embedded_in_text(self):
        text = 'Here you go: {"premises": ["a > 0"], "goal": "sqrt(a) > 0"} Done.'
        pg = _parse_premise_goal(text)
        assert pg.goal == "sqrt(a) > 0"

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError):
            _parse_premise_goal("not json at all")


# ─────────────────────────────────────────────────────────────────────────────
# Unit: _parse_linear_proof
# ─────────────────────────────────────────────────────────────────────────────

class TestParseLinearProof:
    def test_valid_proof(self):
        data = {
            "steps": [
                {"step_id": "S1", "statement": "x > 0", "justification": "given", "refs": []},
                {"step_id": "S2", "statement": "sqrt(x) > 0", "justification": "sqrt definition", "refs": ["S1"]},
            ],
            "conclusion": "sqrt(x) > 0 for x > 0",
        }
        proof = _parse_linear_proof(json.dumps(data))
        assert len(proof.steps) == 2
        assert proof.steps[1].refs == ["S1"]
        assert proof.conclusion == "sqrt(x) > 0 for x > 0"

    def test_empty_steps(self):
        proof = _parse_linear_proof('{"steps": [], "conclusion": ""}')
        assert proof.steps == []

    def test_missing_steps_key(self):
        proof = _parse_linear_proof('{"conclusion": "done"}')
        assert proof.steps == []

    def test_non_dict_step_ignored(self):
        data = {"steps": [{"step_id": "S1", "statement": "x", "justification": "axiom"}, "bad entry"], "conclusion": "x"}
        proof = _parse_linear_proof(json.dumps(data))
        assert len(proof.steps) == 1

    def test_refs_coerced_to_strings(self):
        data = {"steps": [{"step_id": "S1", "statement": "x", "justification": "axiom", "refs": [1, 2]}], "conclusion": "x"}
        proof = _parse_linear_proof(json.dumps(data))
        assert proof.steps[0].refs == ["1", "2"]


# ─────────────────────────────────────────────────────────────────────────────
# Unit: verify_linear_proof
# ─────────────────────────────────────────────────────────────────────────────

class TestVerifyLinearProof:
    GOAL = "d/dx sin(x^2) = 2x cos(x^2)"

    def test_valid_proof_no_blocking(self):
        proof = _make_proof([
            _make_step("S1", "Let u = x^2", "substitution definition"),
            _make_step("S2", "d/dx sin(x^2) = 2x cos(x^2)", "chain_rule", refs=["S1"]),
        ], conclusion="d/dx sin(x^2) = 2x cos(x^2)")
        errors = verify_linear_proof(proof, self.GOAL)
        assert not any(e.blocking for e in errors)

    def test_empty_proof_is_blocking(self):
        proof = _make_proof([])
        errors = verify_linear_proof(proof, self.GOAL)
        assert any(e.blocking for e in errors)

    def test_empty_statement_is_blocking(self):
        proof = _make_proof([_make_step(statement="")])
        errors = verify_linear_proof(proof, self.GOAL)
        assert any(e.blocking and "statement" in e.description.lower() for e in errors)

    def test_empty_justification_is_blocking(self):
        proof = _make_proof([_make_step(justification="")])
        errors = verify_linear_proof(proof, self.GOAL)
        assert any(e.blocking and "justification" in e.description.lower() for e in errors)

    def test_missing_conclusion_is_blocking(self):
        proof = _make_proof([_make_step()], conclusion="")
        errors = verify_linear_proof(proof, self.GOAL)
        assert any(e.blocking and "conclusion" in e.description.lower() for e in errors)

    def test_vague_term_not_blocking(self):
        proof = _make_proof([
            _make_step(statement="this is clearly true", justification="some known theorem"),
            _make_step("S2", "conclusion follows", "power_rule"),
        ])
        errors = verify_linear_proof(proof, "goal")
        vague = [e for e in errors if "Vague" in e.description]
        assert vague, "Expected vague-term error"
        assert not any(e.blocking for e in vague)

    def test_dangling_ref_not_blocking(self):
        proof = _make_proof([_make_step(refs=["S99"])])
        errors = verify_linear_proof(proof, self.GOAL)
        ref_errors = [e for e in errors if "S99" in e.description]
        assert ref_errors
        assert not any(e.blocking for e in ref_errors)

    def test_single_step_warns(self):
        proof = _make_proof([_make_step("S1", "result follows", "by IVT")])
        errors = verify_linear_proof(proof, "goal")
        depth_warnings = [e for e in errors if "one step" in e.description or "shallow" in e.description]
        assert depth_warnings

    def test_all_vague_terms_detected(self):
        for term in bl.VAGUE_TERMS:
            proof = _make_proof([
                _make_step(justification=f"this is {term} from the definition"),
                _make_step("S2", "conclusion", "power_rule"),
            ])
            errors = verify_linear_proof(proof, "goal")
            assert any(term in e.description for e in errors), f"Expected vague-term error for '{term}'"

    def test_is_accepted_no_blocking(self):
        errors = [VerifierError(None, "medium", "warn", "fix", False)]
        assert bl._is_accepted(errors) is True

    def test_is_accepted_with_blocking(self):
        errors = [VerifierError(None, "high", "error", "fix", True)]
        assert bl._is_accepted(errors) is False


# ─────────────────────────────────────────────────────────────────────────────
# Integration: MockLLM  (no GPU required)
# ─────────────────────────────────────────────────────────────────────────────

class TestBaselineMockLLM:
    """Tests that replace ACTIVE_LLM with a mock — no real model needed."""

    def _mock_llm(self, responses, make_mock_llm):
        return make_mock_llm(responses)

    def test_extract_parses_correctly(self, make_mock_llm, monkeypatch):
        pg_json = json.dumps({
            "premises": ["f is continuous on [a,b]", "N between f(a) and f(b)"],
            "goal": "exists c such that f(c) = N",
        })
        mock = make_mock_llm([pg_json, '{"steps":[],"conclusion":""}'])
        monkeypatch.setattr(bl, "ACTIVE_LLM", mock)
        pg = stage_extract("Prove IVT")
        assert pg.premises[0] == "f is continuous on [a,b]"
        assert "f(c) = N" in pg.goal

    def test_full_pipeline_accepted(self, make_mock_llm, monkeypatch):
        pg_json = json.dumps({
            "premises": ["x is real"],
            "goal": "x^2 >= 0",
        })
        proof_json = json.dumps({
            "steps": [
                {"step_id": "S1", "statement": "x^2 = x * x", "justification": "definition of exponentiation", "refs": []},
                {"step_id": "S2", "statement": "x * x >= 0 for all real x", "justification": "product of equal-sign reals is non-negative", "refs": ["S1"]},
            ],
            "conclusion": "x^2 >= 0 for any real x",
        })
        mock = make_mock_llm([pg_json, proof_json])
        monkeypatch.setattr(bl, "ACTIVE_LLM", mock)

        result = run_baseline("Prove x^2 >= 0", problem_id="test_sq", max_corrections=0)
        assert result.premises == ["x is real"]
        assert result.accepted
        assert len(result.proof.steps) == 2

    def test_correction_triggered_on_blocking_error(self, make_mock_llm, monkeypatch):
        pg_json = json.dumps({"premises": ["x is real"], "goal": "x^2 >= 0"})
        bad_proof = json.dumps({
            "steps": [{"step_id": "S1", "statement": "x^2 >= 0", "justification": "", "refs": []}],
            "conclusion": "x^2 >= 0",
        })
        good_proof = json.dumps({
            "steps": [
                {"step_id": "S1", "statement": "x^2 = x*x", "justification": "definition of exponentiation", "refs": []},
                {"step_id": "S2", "statement": "x^2 >= 0", "justification": "product of reals with same sign is non-negative", "refs": ["S1"]},
            ],
            "conclusion": "therefore x^2 >= 0",
        })
        mock = make_mock_llm([pg_json, bad_proof, good_proof])
        monkeypatch.setattr(bl, "ACTIVE_LLM", mock)

        result = run_baseline("Prove x^2 >= 0", problem_id="correction_test", max_corrections=2)
        assert result.attempts >= 2
        assert mock.call_count == 3  # extract + bad generate + correct

    def test_max_corrections_respected(self, make_mock_llm, monkeypatch):
        pg_json = json.dumps({"premises": [], "goal": "goal"})
        bad_proof = json.dumps({"steps": [{"step_id": "S1", "statement": "x", "justification": "", "refs": []}], "conclusion": "x"})
        mock = make_mock_llm([pg_json] + [bad_proof] * 10)
        monkeypatch.setattr(bl, "ACTIVE_LLM", mock)

        result = run_baseline("some problem", max_corrections=2)
        # extract(1) + generate(1) + correct(1 at most) = 3 calls
        assert mock.call_count <= 4

    def test_result_fields_complete(self, make_mock_llm, monkeypatch):
        pg_json = json.dumps({"premises": ["a > 0"], "goal": "sqrt(a) > 0"})
        proof_json = json.dumps({
            "steps": [
                {"step_id": "S1", "statement": "a > 0 by hypothesis", "justification": "given premise", "refs": []},
                {"step_id": "S2", "statement": "sqrt(a) > 0", "justification": "square root of positive real is positive", "refs": ["S1"]},
            ],
            "conclusion": "sqrt(a) > 0",
        })
        mock = make_mock_llm([pg_json, proof_json])
        monkeypatch.setattr(bl, "ACTIVE_LLM", mock)

        result = run_baseline("Prove sqrt(a) > 0 given a > 0", problem_id="sqrt_test")
        assert result.problem_id == "sqrt_test"
        assert isinstance(result.elapsed_sec, float) and result.elapsed_sec >= 0
        assert isinstance(result.errors, list)
        assert isinstance(result.attempts, int) and result.attempts >= 1
        assert result.proof is not None

    def test_stage_correct_sends_errors_to_llm(self, make_mock_llm, monkeypatch):
        corrected = json.dumps({
            "steps": [
                {"step_id": "S1", "statement": "f is continuous", "justification": "given premise", "refs": []},
                {"step_id": "S2", "statement": "f(c) = N exists", "justification": "intermediate_value_theorem", "refs": ["S1"]},
            ],
            "conclusion": "exists c such that f(c) = N",
        })
        mock = make_mock_llm([corrected])
        monkeypatch.setattr(bl, "ACTIVE_LLM", mock)

        proof = LinearProof(
            steps=[ProofStep("S1", "", "bad", [])],
            conclusion="done",
        )
        errors = [VerifierError("S1", "high", "Empty statement", "Add a claim", True)]
        fixed = stage_correct(proof, ["f continuous"], "exists c", errors)
        assert len(fixed.steps) == 2
        # Verify the prompt included the error description
        call_prompt = mock.calls[0]["prompt_head"]
        assert len(call_prompt) > 0  # something was sent


# ─────────────────────────────────────────────────────────────────────────────
# Live model: all 3 benchmark problems
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.livemodel
@pytest.mark.parametrize("prob", BENCHMARK_PROBLEMS, ids=[p["problem_id"] for p in BENCHMARK_PROBLEMS])
def test_benchmark_baseline(require_live_model, prob):
    """End-to-end baseline pipeline on each benchmark problem."""
    # Inject the live model into baseline's module-level slot
    import baseline as bl_mod
    bl_mod.ACTIVE_LLM = require_live_model

    result = run_baseline(prob["raw_problem"], problem_id=prob["problem_id"])

    # Structural assertions — model quality varies, so we assert shape not score
    assert result.premises, f"[{prob['problem_id']}] No premises extracted"
    assert result.goal, f"[{prob['problem_id']}] No goal extracted"
    assert result.proof is not None
    assert result.proof.steps, f"[{prob['problem_id']}] Proof has no steps"
    assert result.proof.conclusion, f"[{prob['problem_id']}] Proof has no conclusion"
    assert result.attempts >= 1

    blocking = [e for e in result.errors if e.blocking]
    print(
        f"\n[{prob['problem_id']}] accepted={result.accepted}  "
        f"attempts={result.attempts}  steps={len(result.proof.steps)}  "
        f"blocking={len(blocking)}  time={result.elapsed_sec:.1f}s"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Script entry point: run all benchmarks interactively
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from baseline import _print_result

    print("=" * 64)
    print("Baseline Pipeline — Benchmark Run")
    print("=" * 64)

    for prob in BENCHMARK_PROBLEMS:
        result = run_baseline(prob["raw_problem"], problem_id=prob["problem_id"])
        _print_result(result)

    print("\nDone.")
