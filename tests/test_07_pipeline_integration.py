"""
Full pipeline integration tests
Tests: WEEK2_APP.invoke() end-to-end, and full_model_pipeline()

These tests verify that all 6 stages chain together correctly.
Mock-LLM tests run without a GPU. Live-model tests require the real HF model.
"""
import pytest


# ── Mock-LLM integration tests ───────────────────────────────────────────────

class TestPipelineWithMockLLM:
    """Run the full LangGraph pipeline with pre-baked LLM responses."""

    PROBLEM_JSON_RESP = """{
        "problem_id": "integ_test",
        "raw_problem": "Prove d/dx sin(x) = cos(x)",
        "goal": {"text": "d/dx sin(x) = cos(x)", "symbolic": "d/dx sin(x) = cos(x)"},
        "assumptions": [{"id": "A1", "statement": "x is real"}],
        "variables": [{"symbol": "x", "type": "real", "role": "variable"}],
        "domain": {"x": "real"}, "technical_terms": [], "hidden_conditions": []
    }"""

    PROOF_CONTRACT_RESP = """{
        "goal": {"text": "d/dx sin(x) = cos(x)", "symbolic": "d/dx sin(x) = cos(x)"},
        "obligations": [{"id": "O1", "description": "Show derivative", "status": "pending"}],
        "allowed_references": ["derivative_rule", "limit_rule"],
        "forbidden_moves": []
    }"""

    GRAPH_SKELETON_RESP = """{
        "proof_id": "integ_test",
        "goal_node_id": "G1",
        "nodes": [
            {"id": "A1", "node_type": "assumption", "claim": "x is real", "status": "source"},
            {"id": "G1", "node_type": "goal", "claim": "d/dx sin(x) = cos(x)", "status": "planned"}
        ],
        "inferences": [
            {"id": "I1", "premise_nodes": ["A1"], "side_condition_nodes": [],
             "conclusion_node": "G1", "rule_refs": ["derivative_rule"],
             "relation": "implies", "status": "planned"}
        ]
    }"""

    NODE_PROOF_RESP = """{
        "format": "structured_derivation",
        "steps": [
            {"statement": "By derivative rule, d/dx sin(x) = cos(x)", "reason": "derivative_rule", "refs": []}
        ]
    }"""

    def _inject(self, monkeypatch, make_mock_llm):
        """Inject a mock LLM with enough responses to cover all generator calls."""
        import generators
        responses = [
            self.PROBLEM_JSON_RESP,
            self.PROOF_CONTRACT_RESP,
            self.GRAPH_SKELETON_RESP,
            self.NODE_PROOF_RESP,  # for G1
        ]
        llm = make_mock_llm(responses)
        monkeypatch.setattr(generators, "ACTIVE_LLM", llm)
        return llm

    def test_pipeline_invoke_returns_state_with_all_required_keys(
            self, monkeypatch, make_mock_llm):
        import verifiers
        self._inject(monkeypatch, make_mock_llm)
        monkeypatch.setattr(verifiers, "_get_active_llm", lambda: None)
        from langgraph_nodes import WEEK2_APP
        state = WEEK2_APP.invoke({"raw_problem": "Prove d/dx sin(x) = cos(x)"})
        for key in ["problem_json", "proof_contract", "proof_graph_state",
                    "current_errors", "aggregator_result", "accepted", "trace"]:
            assert key in state, f"Key '{key}' missing from final state"

    def test_pipeline_trace_has_entry_for_each_of_six_nodes(
            self, monkeypatch, make_mock_llm):
        import verifiers
        self._inject(monkeypatch, make_mock_llm)
        monkeypatch.setattr(verifiers, "_get_active_llm", lambda: None)
        from langgraph_nodes import WEEK2_APP
        state = WEEK2_APP.invoke({"raw_problem": "Prove d/dx sin(x) = cos(x)"})
        node_names = {entry["node"] for entry in state["trace"]}
        expected = {"problem_parser", "contract_builder", "graph_planner",
                    "graph_prover", "run_verifiers", "export_trace"}
        assert node_names == expected

    def test_pipeline_accepted_is_bool(self, monkeypatch, make_mock_llm):
        import verifiers
        self._inject(monkeypatch, make_mock_llm)
        monkeypatch.setattr(verifiers, "_get_active_llm", lambda: None)
        from langgraph_nodes import WEEK2_APP
        state = WEEK2_APP.invoke({"raw_problem": "Prove d/dx sin(x) = cos(x)"})
        assert isinstance(state["accepted"], bool)

    def test_full_model_pipeline_function_returns_expected_keys(
            self, monkeypatch, make_mock_llm):
        import verifiers
        self._inject(monkeypatch, make_mock_llm)
        monkeypatch.setattr(verifiers, "_get_active_llm", lambda: None)
        from graph_planner import full_model_pipeline
        result = full_model_pipeline("Prove d/dx sin(x) = cos(x)")
        for key in ["problem_json", "proof_contract", "proof_graph_state",
                    "errors", "aggregator"]:
            assert key in result, f"Key '{key}' missing from full_model_pipeline result"


# ── Live-model integration tests ─────────────────────────────────────────────

@pytest.mark.livemodel
class TestPipelineLiveModel:
    """Runs the full pipeline against the real HF model.
    Skip with: pytest -m 'not livemodel'
    These tests are slow (~30-120 s) because the model must run inference for each stage.
    """

    def test_live_pipeline_produces_valid_problem_json_and_proof_contract(
            self, require_live_model):
        from langgraph_nodes import WEEK2_APP
        state = WEEK2_APP.invoke(
            {"raw_problem": "Prove that d/dx sin(x) = cos(x) using the limit definition."}
        )
        pj = state.get("problem_json", {})
        pc = state.get("proof_contract", {})
        assert "problem_id" in pj, "problem_json missing problem_id"
        assert "goal" in pj, "problem_json missing goal"
        assert "obligations" in pc, "proof_contract missing obligations"
        assert "allowed_references" in pc, "proof_contract missing allowed_references"

    def test_live_pipeline_all_six_trace_nodes_present(self, require_live_model):
        from langgraph_nodes import WEEK2_APP
        state = WEEK2_APP.invoke({"raw_problem": "Prove d/dx x^2 = 2*x using the power rule."})
        node_names = {entry["node"] for entry in state.get("trace", [])}
        for expected_node in ["problem_parser", "contract_builder", "graph_planner",
                               "graph_prover", "run_verifiers", "export_trace"]:
            assert expected_node in node_names, f"Trace missing node '{expected_node}'"

    def test_live_pipeline_proof_graph_state_has_nodes(self, require_live_model):
        from langgraph_nodes import WEEK2_APP
        state = WEEK2_APP.invoke({"raw_problem": "Prove d/dx x^2 = 2*x."})
        gs = state.get("proof_graph_state", {})
        assert "nodes" in gs and len(gs["nodes"]) > 0, "proof_graph_state has no nodes"

    def test_live_pipeline_aggregator_result_has_all_required_pass_key(
            self, require_live_model):
        from langgraph_nodes import WEEK2_APP
        state = WEEK2_APP.invoke({"raw_problem": "Prove d/dx x^2 = 2*x."})
        agg = state.get("aggregator_result", {})
        assert "all_required_pass" in agg, "aggregator_result missing all_required_pass"
        assert isinstance(agg["all_required_pass"], bool)
