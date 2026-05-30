"""
Stage 1 — Problem Parser
Tests: _normalize_problem_json(), generate_problem_json()

The problem_parser node accepts a raw natural-language problem string and
produces a structured problem_json dict that must satisfy PROBLEM_JSON_SCHEMA.
"""
import pytest


# ── Normalizer unit tests ────────────────────────────────────────────────────

class TestNormalizeProblemJson:
    """Test _normalize_problem_json() in isolation (no LLM needed)."""

    @staticmethod
    def norm(data):
        import generators
        return generators._normalize_problem_json(data)

    def _base(self, **kwargs):
        d = {"problem_id": "p1", "raw_problem": "test", "goal": {"text": "g", "symbolic": "g"}}
        d.update(kwargs)
        return d

    def test_string_assumptions_converted_to_id_statement_objects(self):
        result = self.norm(self._base(assumptions=["x is real", "f is differentiable"]))
        assert result["assumptions"] == [
            {"id": "A1", "statement": "x is real"},
            {"id": "A2", "statement": "f is differentiable"},
        ]

    def test_dict_assumptions_pass_through_unchanged(self):
        assumption = {"id": "A1", "statement": "x is real"}
        result = self.norm(self._base(assumptions=[assumption]))
        assert result["assumptions"][0] == assumption

    def test_string_variables_converted_to_symbol_type_role_objects(self):
        result = self.norm(self._base(variables=["x", "f"]))
        assert result["variables"][0] == {"symbol": "x", "type": "real", "role": "variable"}
        assert result["variables"][1]["symbol"] == "f"

    def test_string_goal_converted_to_text_symbolic_dict(self):
        result = self.norm({"problem_id": "p1", "raw_problem": "test", "goal": "x = 1"})
        assert isinstance(result["goal"], dict)
        assert "text" in result["goal"] and "symbolic" in result["goal"]

    def test_string_hidden_conditions_converted_to_id_statement_objects(self):
        result = self.norm(self._base(hidden_conditions=["domain is closed"]))
        assert result["hidden_conditions"][0] == {"id": "H1", "statement": "domain is closed"}

    def test_leading_space_in_dict_keys_stripped(self):
        data = {" problem_id": "p1", "raw_problem": "test", "goal": {"text": "g", "symbolic": "g"}}
        result = self.norm(data)
        assert "problem_id" in result and " problem_id" not in result

    def test_empty_assumptions_list_not_converted(self):
        result = self.norm(self._base(assumptions=[]))
        assert result["assumptions"] == []


# ── Schema validation tests ──────────────────────────────────────────────────

class TestProblemParserSchema:
    """Validate that schema checks catch missing / malformed fields."""

    def _check(self, data):
        from verifier_utils import verify_json_schema
        from schemas import PROBLEM_JSON_SCHEMA
        return verify_json_schema("problem_json", data, PROBLEM_JSON_SCHEMA)

    def test_valid_problem_json_passes_with_no_errors(self, problem_json):
        errors = self._check(problem_json)
        assert errors == [], f"Unexpected errors: {[e['evidence'] for e in errors]}"

    def test_missing_problem_id_produces_schema_error(self, problem_json):
        del problem_json["problem_id"]
        errors = self._check(problem_json)
        assert any("problem_id" in e["evidence"] for e in errors)

    def test_missing_goal_produces_schema_error(self, problem_json):
        del problem_json["goal"]
        errors = self._check(problem_json)
        assert any("goal" in e["evidence"] for e in errors)

    def test_goal_missing_text_subfield_produces_schema_error(self, problem_json):
        problem_json["goal"] = {"symbolic": "x = 1"}  # 'text' absent
        errors = self._check(problem_json)
        assert any("text" in e["evidence"] for e in errors)


# ── Mock-LLM generator tests ─────────────────────────────────────────────────

class TestProblemParserMockLLM:
    """Test generate_problem_json() with a fake model — fast, no GPU required."""

    VALID_RESPONSE = """{
        "problem_id": "mock_p",
        "raw_problem": "Prove x = x",
        "goal": {"text": "x equals x", "symbolic": "x = x"},
        "assumptions": [{"id": "A1", "statement": "x is real"}],
        "variables": [{"symbol": "x", "type": "real", "role": "variable"}],
        "domain": {"x": "real"},
        "technical_terms": ["algebra"],
        "hidden_conditions": []
    }"""

    def _inject(self, monkeypatch, make_mock_llm, responses):
        import generators
        llm = make_mock_llm(responses)
        monkeypatch.setattr(generators, "ACTIVE_LLM", llm)
        return llm

    def test_valid_response_returns_parsed_dict_with_source_metadata(self, monkeypatch, make_mock_llm):
        self._inject(monkeypatch, make_mock_llm, [self.VALID_RESPONSE])
        import generators
        result = generators.generate_problem_json("Prove x = x")
        assert result["problem_id"] == "mock_p"
        assert result["_generation_source"] == "hf"
        assert result["_generation_attempts"] == 1

    def test_same_input_returns_cached_result_and_calls_model_once(self, monkeypatch, make_mock_llm):
        llm = self._inject(monkeypatch, make_mock_llm, [self.VALID_RESPONSE])
        import generators
        r1 = generators.generate_problem_json("Prove x = x")
        r2 = generators.generate_problem_json("Prove x = x")
        assert r1 is r2
        assert llm.call_count == 1

    def test_invalid_then_valid_response_succeeds_via_repair(self, monkeypatch, make_mock_llm):
        bad = '{"broken"'
        # original → bad, compact → bad, repair → valid
        self._inject(monkeypatch, make_mock_llm, [bad, bad, self.VALID_RESPONSE])
        import generators
        result = generators.generate_problem_json("Prove x = x")
        assert result["problem_id"] == "mock_p"

    def test_all_bad_responses_raise_runtime_error_with_exceeded_message(self, monkeypatch, make_mock_llm):
        self._inject(monkeypatch, make_mock_llm, ["bad json"] * 6)
        import generators
        with pytest.raises(RuntimeError, match="exceeded.*repair attempts"):
            generators.generate_problem_json("Some problem")

    def test_string_assumptions_in_model_output_normalized_to_objects(self, monkeypatch, make_mock_llm):
        response = """{
            "problem_id": "p2", "raw_problem": "test",
            "goal": {"text": "g", "symbolic": "g"},
            "assumptions": ["x is real"],
            "variables": [], "domain": {}, "technical_terms": [], "hidden_conditions": []
        }"""
        self._inject(monkeypatch, make_mock_llm, [response])
        import generators
        result = generators.generate_problem_json("test problem 2")
        assert isinstance(result["assumptions"][0], dict)
        assert result["assumptions"][0]["id"] == "A1"

    def test_spaced_keys_in_model_output_stripped_before_schema_check(self, monkeypatch, make_mock_llm):
        response = """{
            " problem_id": "p3", "raw_problem": "test",
            "goal": {"text": "g", "symbolic": "g"},
            "assumptions": [], "variables": [], "domain": {},
            "technical_terms": [], "hidden_conditions": []
        }"""
        self._inject(monkeypatch, make_mock_llm, [response])
        import generators
        result = generators.generate_problem_json("test problem 3")
        assert result["problem_id"] == "p3"


# ── Live-model integration test ──────────────────────────────────────────────

@pytest.mark.livemodel
class TestProblemParserLiveModel:
    """Runs against the real loaded model. Skip with: pytest -m 'not livemodel'."""

    def test_live_generate_returns_valid_problem_json_schema(self, require_live_model):
        import generators
        from verifier_utils import verify_json_schema
        from schemas import PROBLEM_JSON_SCHEMA
        result = generators.generate_problem_json("Prove that d/dx sin(x) = cos(x).")
        assert "problem_id" in result
        assert isinstance(result.get("goal"), dict)
        schema_errors = verify_json_schema("problem_json", result, PROBLEM_JSON_SCHEMA)
        assert schema_errors == [], f"Schema errors: {[e['evidence'] for e in schema_errors]}"
