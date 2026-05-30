"""
Stage 2 — Contract Builder
Tests: _normalize_proof_contract(), generate_proof_contract()

The contract_builder node takes problem_json and produces a proof_contract
that specifies proof obligations, allowed references, and acceptance criteria.
"""
import pytest


# ── Normalizer unit tests ────────────────────────────────────────────────────

class TestNormalizeProofContract:
    """Test _normalize_proof_contract() in isolation (no LLM needed)."""

    @staticmethod
    def norm(data):
        import generators
        return generators._normalize_proof_contract(data)

    def _base(self, **kwargs):
        d = {
            "goal": {"text": "g", "symbolic": "g"},
            "obligations": [{"id": "O1", "description": "prove it", "status": "pending"}],
            "allowed_references": ["chain_rule"],
        }
        d.update(kwargs)
        return d

    def test_nested_problem_wrapper_unwrapped_to_top_level(self):
        data = {"problem": {"goal": {"text": "g", "symbolic": "g"},
                            "obligations": [{"id": "O1", "description": "d", "status": "pending"}],
                            "allowed_references": ["r1"]}}
        result = self.norm(data)
        assert "goal" in result
        assert "problem" not in result

    def test_obligations_dict_converted_to_single_element_list(self):
        data = {**self._base(), "obligations": {"id": "O1", "description": "d", "status": "pending"}}
        result = self.norm(data)
        assert isinstance(result["obligations"], list)
        assert result["obligations"][0]["id"] == "O1"

    def test_obligation_item_missing_id_gets_auto_id(self):
        data = {**self._base(), "obligations": [{"description": "prove goal", "status": "pending"}]}
        result = self.norm(data)
        assert result["obligations"][0]["id"] == "O1"

    def test_obligation_item_missing_status_defaults_to_pending(self):
        data = {**self._base(), "obligations": [{"id": "O1", "description": "prove goal"}]}
        result = self.norm(data)
        assert result["obligations"][0]["status"] == "pending"

    def test_empty_obligations_replaced_by_default_obligation(self):
        data = {**self._base(), "obligations": []}
        result = self.norm(data)
        assert len(result["obligations"]) == 1
        assert result["obligations"][0]["id"] == "O1"

    def test_allowed_references_with_space_in_key_mapped_to_snake_case(self):
        data = {"goal": {"text": "g", "symbolic": "g"},
                "obligations": [{"id": "O1", "description": "d", "status": "pending"}],
                "allowed references": ["chain_rule"],
                "allowed_references": []}
        result = self.norm(data)
        assert "chain_rule" in result["allowed_references"]

    def test_spaced_dict_keys_stripped_recursively(self):
        data = {" goal": {"text": "g", "symbolic": "g"},
                "obligations": [{"id": "O1", "description": "d", "status": "pending"}],
                "allowed_references": ["r1"]}
        result = self.norm(data)
        assert "goal" in result and " goal" not in result


# ── Schema validation tests ──────────────────────────────────────────────────

class TestContractBuilderSchema:
    """Validate that schema checks catch missing / malformed fields."""

    def _check(self, data):
        from verifier_utils import verify_json_schema
        from schemas import PROOF_CONTRACT_SCHEMA
        return verify_json_schema("proof_contract", data, PROOF_CONTRACT_SCHEMA)

    def test_valid_proof_contract_passes_with_no_errors(self, proof_contract):
        errors = self._check(proof_contract)
        assert errors == [], f"Unexpected errors: {[e['evidence'] for e in errors]}"

    def test_missing_obligations_produces_schema_error(self, proof_contract):
        del proof_contract["obligations"]
        errors = self._check(proof_contract)
        assert any("obligations" in e["evidence"] for e in errors)

    def test_missing_allowed_references_produces_schema_error(self, proof_contract):
        del proof_contract["allowed_references"]
        errors = self._check(proof_contract)
        assert any("allowed_references" in e["evidence"] for e in errors)

    def test_obligation_missing_id_produces_schema_error(self, proof_contract):
        proof_contract["obligations"][0].pop("id")
        errors = self._check(proof_contract)
        assert any("id" in e["evidence"] for e in errors)


# ── Mock-LLM generator tests ─────────────────────────────────────────────────

class TestContractBuilderMockLLM:
    """Test generate_proof_contract() with a fake model."""

    VALID_RESPONSE = """{
        "goal": {"text": "prove it", "symbolic": "x = x"},
        "obligations": [{"id": "O1", "description": "show x=x", "status": "pending"}],
        "allowed_references": ["algebra"],
        "forbidden_moves": ["assuming result"]
    }"""

    def _inject(self, monkeypatch, make_mock_llm, responses):
        import generators
        llm = make_mock_llm(responses)
        monkeypatch.setattr(generators, "ACTIVE_LLM", llm)
        return llm

    def test_valid_response_returns_proof_contract_with_source_metadata(
            self, monkeypatch, make_mock_llm, problem_json):
        self._inject(monkeypatch, make_mock_llm, [self.VALID_RESPONSE])
        import generators
        result = generators.generate_proof_contract(problem_json)
        assert "goal" in result
        assert result["_generation_source"] == "hf"

    def test_result_cached_by_problem_id(self, monkeypatch, make_mock_llm, problem_json):
        llm = self._inject(monkeypatch, make_mock_llm, [self.VALID_RESPONSE])
        import generators
        r1 = generators.generate_proof_contract(problem_json)
        r2 = generators.generate_proof_contract(problem_json)
        assert r1 is r2
        assert llm.call_count == 1

    def test_all_bad_responses_raise_runtime_error(self, monkeypatch, make_mock_llm, problem_json):
        self._inject(monkeypatch, make_mock_llm, ["bad json"] * 6)
        import generators
        with pytest.raises(RuntimeError, match="exceeded.*repair attempts"):
            generators.generate_proof_contract(problem_json)

    def test_nested_wrapper_unwrapped_by_normalizer(self, monkeypatch, make_mock_llm, problem_json):
        wrapped_response = """{
            "problem": {
                "goal": {"text": "prove it", "symbolic": "x = x"},
                "obligations": [{"id": "O1", "description": "d", "status": "pending"}],
                "allowed_references": ["algebra"]
            }
        }"""
        self._inject(monkeypatch, make_mock_llm, [wrapped_response])
        import generators
        result = generators.generate_proof_contract(problem_json)
        assert "goal" in result
        assert "problem" not in result


# ── Live-model integration test ──────────────────────────────────────────────

@pytest.mark.livemodel
class TestContractBuilderLiveModel:
    """Runs against the real loaded model. Skip with: pytest -m 'not livemodel'."""

    def test_live_generate_proof_contract_has_required_fields(
            self, require_live_model, problem_json):
        import generators
        from verifier_utils import verify_json_schema
        from schemas import PROOF_CONTRACT_SCHEMA
        result = generators.generate_proof_contract(problem_json)
        assert "goal" in result
        assert "obligations" in result and len(result["obligations"]) > 0
        assert "allowed_references" in result
        schema_errors = verify_json_schema("proof_contract", result, PROOF_CONTRACT_SCHEMA)
        assert schema_errors == [], f"Schema errors: {[e['evidence'] for e in schema_errors]}"
