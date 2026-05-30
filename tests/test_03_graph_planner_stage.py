"""
Stage 3 — Graph Planner
Tests: _normalize_graph_state(), _strip_dict_keys(), generate_graph_skeleton()

The graph_planner node takes problem_json + proof_contract and produces a
proof_graph_state describing the tree of nodes and inferences to be proven.
"""
import pytest


# ── _strip_dict_keys unit tests ──────────────────────────────────────────────

class TestStripDictKeys:
    """Test _strip_dict_keys() — the function that fixes spaced JSON keys from the model."""

    @staticmethod
    def strip(data):
        import generators
        return generators._strip_dict_keys(data)

    def test_leading_space_in_key_removed(self):
        result = self.strip({" nodes": [], "proof_id": "p"})
        assert "nodes" in result and " nodes" not in result

    def test_trailing_space_in_key_removed(self):
        result = self.strip({"nodes ": [], "proof_id": "p"})
        assert "nodes" in result and "nodes " not in result

    def test_clean_keys_unchanged(self):
        result = self.strip({"proof_id": "p", "nodes": []})
        assert result == {"proof_id": "p", "nodes": []}

    def test_nested_dict_keys_also_stripped(self):
        result = self.strip({" outer": {" inner": "v"}})
        assert "outer" in result
        assert "inner" in result["outer"]

    def test_list_items_processed_recursively(self):
        result = self.strip([{" id": "n1"}])
        assert result[0]["id"] == "n1"


# ── Normalizer unit tests ────────────────────────────────────────────────────

class TestNormalizeGraphState:
    """Test _normalize_graph_state() in isolation (no LLM needed)."""

    @staticmethod
    def norm(data):
        import generators
        return generators._normalize_graph_state(data)

    def _base(self, **kwargs):
        d = {"proof_id": "p1", "nodes": [], "inferences": []}
        d.update(kwargs)
        return d

    def test_spaced_proof_id_key_restored(self):
        result = self.norm({" proof_id": "p1", "nodes": [], "inferences": []})
        assert result["proof_id"] == "p1"

    def test_missing_proof_id_extracted_from_id_field(self):
        result = self.norm({"id": "p1", "nodes": [], "inferences": []})
        assert result["proof_id"] == "p1"

    def test_spaced_node_type_status_stripped(self):
        node = {"id": "N1", "node_type": " assumption", "claim": "c", "status": " source"}
        result = self.norm(self._base(nodes=[node]))
        assert result["nodes"][0]["node_type"] == "assumption"
        assert result["nodes"][0]["status"] == "source"

    def test_inference_like_objects_separated_from_nodes(self):
        node = {"id": "N1", "node_type": "assumption", "claim": "c", "status": "source"}
        inf_like = {"id": "I1", "premise_nodes": ["N1"], "conclusion_node": "G1"}
        result = self.norm(self._base(nodes=[node, inf_like]))
        # inf-like object should be moved out of nodes
        assert all("premise_nodes" not in n for n in result["nodes"])
        assert any("premise_nodes" in i for i in result["inferences"])

    def test_inference_missing_required_fields_filled_with_defaults(self):
        result = self.norm(self._base(inferences=[{"id": "I1", "conclusion_node": "G1"}]))
        inf = result["inferences"][0]
        assert "premise_nodes" in inf
        assert "side_condition_nodes" in inf
        assert "rule_refs" in inf
        assert "relation" in inf
        assert "status" in inf

    def test_inference_missing_id_gets_auto_id(self):
        result = self.norm(self._base(inferences=[{"conclusion_node": "G1"}]))
        assert result["inferences"][0]["id"] == "I1"

    def test_empty_inferences_list_preserved(self):
        result = self.norm(self._base(inferences=[]))
        assert result["inferences"] == []


# ── Schema validation tests ──────────────────────────────────────────────────

class TestGraphPlannerSchema:
    """Validate that schema checks catch missing / malformed graph state fields."""

    def _check(self, data):
        from verifier_utils import verify_json_schema
        from schemas import PROOF_GRAPH_STATE_SCHEMA
        return verify_json_schema("proof_graph_state", data, PROOF_GRAPH_STATE_SCHEMA)

    def test_valid_graph_state_passes_with_no_errors(self, graph_state):
        errors = self._check(graph_state)
        assert errors == [], f"Unexpected errors: {[e['evidence'] for e in errors]}"

    def test_missing_proof_id_produces_schema_error(self, graph_state):
        del graph_state["proof_id"]
        errors = self._check(graph_state)
        assert any("proof_id" in e["evidence"] for e in errors)

    def test_node_missing_required_id_produces_schema_error(self, graph_state):
        del graph_state["nodes"][0]["id"]
        errors = self._check(graph_state)
        assert any("id" in e["evidence"] for e in errors)

    def test_node_invalid_status_value_produces_schema_error(self, graph_state):
        graph_state["nodes"][0]["status"] = "unknown_status"
        errors = self._check(graph_state)
        assert any("status" in e["evidence"] or "unknown_status" in e["evidence"] for e in errors)


# ── Mock-LLM generator tests ─────────────────────────────────────────────────

class TestGraphPlannerMockLLM:
    """Test generate_graph_skeleton() with a fake model."""

    VALID_RESPONSE = """{
        "proof_id": "test_chain",
        "goal_node_id": "G1",
        "nodes": [
            {"id": "A1", "node_type": "assumption", "claim": "x is a real number", "status": "source"},
            {"id": "G1", "node_type": "goal", "claim": "d/dx sin(x^2) = 2*x*cos(x^2)", "status": "planned"}
        ],
        "inferences": [
            {"id": "I1", "premise_nodes": ["A1"], "side_condition_nodes": [],
             "conclusion_node": "G1", "rule_refs": ["chain_rule"],
             "relation": "implies", "status": "planned"}
        ]
    }"""

    def _inject(self, monkeypatch, make_mock_llm, responses):
        import generators
        llm = make_mock_llm(responses)
        monkeypatch.setattr(generators, "ACTIVE_LLM", llm)
        return llm

    def test_valid_response_returns_graph_state_with_source_metadata(
            self, monkeypatch, make_mock_llm, problem_json, proof_contract):
        self._inject(monkeypatch, make_mock_llm, [self.VALID_RESPONSE])
        import generators
        result = generators.generate_graph_skeleton(problem_json, proof_contract)
        assert "nodes" in result and "inferences" in result
        assert result["_generation_source"] == "hf"

    def test_result_cached_by_problem_id(
            self, monkeypatch, make_mock_llm, problem_json, proof_contract):
        llm = self._inject(monkeypatch, make_mock_llm, [self.VALID_RESPONSE])
        import generators
        r1 = generators.generate_graph_skeleton(problem_json, proof_contract)
        r2 = generators.generate_graph_skeleton(problem_json, proof_contract)
        assert r1 is r2
        assert llm.call_count == 1

    def test_spaced_keys_in_model_output_stripped_by_normalizer(
            self, monkeypatch, make_mock_llm, problem_json, proof_contract):
        spaced_response = """{
            " proof_id": "test_chain",
            " goal_node_id": "G1",
            " nodes": [
                {"id": "A1", " node_type": "assumption", "claim": "x is a real number", " status": "source"},
                {"id": "G1", " node_type": "goal", "claim": "the goal", " status": "planned"}
            ],
            "inferences": [
                {"id": "I1", "premise_nodes": ["A1"], "side_condition_nodes": [],
                 "conclusion_node": "G1", "rule_refs": ["chain_rule"],
                 "relation": "implies", "status": "planned"}
            ]
        }"""
        self._inject(monkeypatch, make_mock_llm, [spaced_response])
        import generators
        result = generators.generate_graph_skeleton(problem_json, proof_contract)
        # proof_id and nodes should be accessible without leading spaces
        assert result["proof_id"] == "test_chain"
        assert len(result["nodes"]) == 2
        assert result["nodes"][0]["node_type"] == "assumption"

    def test_all_bad_responses_raise_runtime_error(
            self, monkeypatch, make_mock_llm, problem_json, proof_contract):
        self._inject(monkeypatch, make_mock_llm, ["bad json"] * 6)
        import generators
        with pytest.raises(RuntimeError, match="exceeded.*repair attempts"):
            generators.generate_graph_skeleton(problem_json, proof_contract)


# ── Live-model integration test ──────────────────────────────────────────────

@pytest.mark.livemodel
class TestGraphPlannerLiveModel:
    """Runs against the real loaded model. Skip with: pytest -m 'not livemodel'."""

    def test_live_generate_graph_skeleton_has_nodes_and_inferences(
            self, require_live_model, problem_json, proof_contract):
        import generators
        from verifier_utils import verify_json_schema
        from schemas import PROOF_GRAPH_STATE_SCHEMA
        result = generators.generate_graph_skeleton(problem_json, proof_contract)
        assert "nodes" in result and isinstance(result["nodes"], list)
        assert len(result["nodes"]) > 0
        assert "inferences" in result
        schema_errors = verify_json_schema("proof_graph_state", result, PROOF_GRAPH_STATE_SCHEMA)
        assert schema_errors == [], f"Schema errors: {[e['evidence'] for e in schema_errors]}"
