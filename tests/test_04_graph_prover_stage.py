"""
Stage 4 — Graph Prover
Tests: graph_prover() from graph_planner.py

The graph_prover node iterates over every non-source node in the graph and
calls generate_node_proof() to fill in proof_body.steps, then sets status='proven'.
"""
import copy
import pytest


# ── Unit tests (mock LLM) ────────────────────────────────────────────────────

class TestGraphProver:
    """Test graph_prover() behavior using a mock LLM."""

    VALID_NODE_PROOF = """{
        "format": "structured_derivation",
        "steps": [
            {"statement": "By power rule, d/dx x^2 = 2*x", "reason": "power_rule", "refs": []},
            {"statement": "Therefore, d/dx sin(x^2) = 2*x*cos(x^2)", "reason": "chain_rule", "refs": []}
        ]
    }"""

    def _inject(self, monkeypatch, make_mock_llm, responses):
        import generators
        llm = make_mock_llm(responses)
        monkeypatch.setattr(generators, "ACTIVE_LLM", llm)
        return llm

    def test_source_nodes_are_skipped_and_unchanged(
            self, monkeypatch, make_mock_llm, problem_json, proof_contract, graph_state):
        # Provide enough responses for non-source nodes (L1, G1) only.
        self._inject(monkeypatch, make_mock_llm, [self.VALID_NODE_PROOF] * 2)
        from graph_planner import graph_prover
        result = graph_prover(problem_json, proof_contract, graph_state)
        assumption_node = next(n for n in result["nodes"] if n["id"] == "A1")
        assert "proof_body" not in assumption_node or not assumption_node.get("proof_body", {}).get("steps")

    def test_non_source_nodes_receive_proof_body_with_steps(
            self, monkeypatch, make_mock_llm, problem_json, proof_contract, graph_state):
        self._inject(monkeypatch, make_mock_llm, [self.VALID_NODE_PROOF] * 2)
        from graph_planner import graph_prover
        result = graph_prover(problem_json, proof_contract, graph_state)
        for node in result["nodes"]:
            if node.get("node_type") not in {"assumption", "allowed_reference"}:
                assert "proof_body" in node
                assert "steps" in node["proof_body"]
                assert len(node["proof_body"]["steps"]) > 0

    def test_non_source_nodes_status_set_to_proven(
            self, monkeypatch, make_mock_llm, problem_json, proof_contract, graph_state):
        self._inject(monkeypatch, make_mock_llm, [self.VALID_NODE_PROOF] * 2)
        from graph_planner import graph_prover
        result = graph_prover(problem_json, proof_contract, graph_state)
        for node in result["nodes"]:
            if node.get("node_type") not in {"assumption", "allowed_reference"}:
                assert node["status"] == "proven", f"Node {node['id']} not marked proven"

    def test_existing_proof_body_with_steps_not_overwritten(
            self, monkeypatch, make_mock_llm, problem_json, proof_contract, graph_state):
        # Pre-fill L1 with steps so the prover should skip it.
        existing_step = {"statement": "existing proof", "reason": "manual", "refs": []}
        graph_state["nodes"][1]["proof_body"] = {"steps": [existing_step]}
        # Provide one response only — if prover calls model for L1 it would exhaust responses.
        llm = self._inject(monkeypatch, make_mock_llm, [self.VALID_NODE_PROOF])
        from graph_planner import graph_prover
        result = graph_prover(problem_json, proof_contract, graph_state)
        l1 = next(n for n in result["nodes"] if n["id"] == "L1")
        # Existing steps should be preserved.
        assert l1["proof_body"]["steps"][0]["statement"] == "existing proof"

    def test_original_graph_state_not_mutated(
            self, monkeypatch, make_mock_llm, problem_json, proof_contract, graph_state):
        self._inject(monkeypatch, make_mock_llm, [self.VALID_NODE_PROOF] * 2)
        original = copy.deepcopy(graph_state)
        from graph_planner import graph_prover
        graph_prover(problem_json, proof_contract, graph_state)
        # graph_prover does deepcopy internally — original should be unchanged.
        assert graph_state["nodes"][1]["proof_body"] == original["nodes"][1]["proof_body"]

    def test_node_proof_generation_failure_raises_runtime_error(
            self, monkeypatch, make_mock_llm, problem_json, proof_contract, graph_state):
        self._inject(monkeypatch, make_mock_llm, ["bad json"] * 10)
        from graph_planner import graph_prover
        with pytest.raises(RuntimeError, match="exceeded.*repair attempts"):
            graph_prover(problem_json, proof_contract, graph_state)


# ── Live-model integration test ──────────────────────────────────────────────

@pytest.mark.livemodel
class TestGraphProverLiveModel:
    """Runs against the real loaded model. Skip with: pytest -m 'not livemodel'."""

    def test_live_graph_prover_fills_all_non_source_nodes(
            self, require_live_model, problem_json, proof_contract, graph_state):
        from graph_planner import graph_prover
        result = graph_prover(problem_json, proof_contract, graph_state)
        for node in result["nodes"]:
            if node.get("node_type") not in {"assumption", "allowed_reference"}:
                pb = node.get("proof_body", {})
                assert isinstance(pb, dict), f"Node {node['id']} has no proof_body dict"
                assert "steps" in pb, f"Node {node['id']} proof_body has no steps"
