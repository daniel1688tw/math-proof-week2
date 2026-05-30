"""
Stage 6 — Export Trace
Tests: export_trace_node() from langgraph_nodes.py

The export_trace node appends a final entry to the trace list recording
whether the proof was accepted, and passes the state through unchanged otherwise.
"""
import pytest


class TestExportTraceNode:
    """Test the export_trace_node LangGraph node function."""

    def _run(self, state):
        from langgraph_nodes import export_trace_node
        return export_trace_node(state)

    def test_trace_receives_new_entry_with_export_trace_node_name(self):
        state = {"trace": [], "accepted": False}
        result = self._run(state)
        assert len(result["trace"]) == 1
        assert result["trace"][-1]["node"] == "export_trace"

    def test_accepted_true_reflected_in_trace_entry(self):
        state = {"trace": [], "accepted": True}
        result = self._run(state)
        assert result["trace"][-1]["accepted"] is True

    def test_accepted_false_reflected_in_trace_entry(self):
        state = {"trace": [], "accepted": False}
        result = self._run(state)
        assert result["trace"][-1]["accepted"] is False

    def test_existing_trace_entries_preserved(self):
        prior_entries = [
            {"node": "problem_parser", "source": "hf"},
            {"node": "run_verifiers", "accepted": False, "error_count": 5},
        ]
        state = {"trace": prior_entries.copy(), "accepted": False}
        result = self._run(state)
        # Prior entries must still be present.
        assert result["trace"][0] == prior_entries[0]
        assert result["trace"][1] == prior_entries[1]
        assert len(result["trace"]) == 3

    def test_empty_initial_trace_works(self):
        state = {"trace": [], "accepted": True}
        result = self._run(state)
        assert len(result["trace"]) == 1

    def test_missing_accepted_key_defaults_to_false_in_entry(self):
        # accepted is not in state (total=False TypedDict allows this).
        state = {"trace": []}
        result = self._run(state)
        assert result["trace"][-1]["accepted"] is False

    def test_original_state_trace_not_mutated(self):
        original_trace = [{"node": "problem_parser", "source": "hf"}]
        state = {"trace": original_trace, "accepted": False}
        self._run(state)
        # export_trace_node uses list() copy internally — original must be unchanged.
        assert len(original_trace) == 1


# ── LangGraph state flow tests ───────────────────────────────────────────────

class TestProofAgentStateShape:
    """Test that the ProofAgentState TypedDict shape is correct."""

    def test_state_typeddict_allows_all_pipeline_fields(self):
        from langgraph_nodes import ProofAgentState
        # All expected keys should be defined in the TypedDict.
        hints = ProofAgentState.__annotations__
        for field in ["raw_problem", "problem_json", "proof_contract",
                      "proof_graph_state", "current_errors", "aggregator_result",
                      "accepted", "trace"]:
            assert field in hints, f"Field '{field}' missing from ProofAgentState"

    def test_week2_app_is_compiled_and_has_invoke(self):
        from langgraph_nodes import WEEK2_APP
        assert hasattr(WEEK2_APP, "invoke"), "WEEK2_APP must be a compiled LangGraph app"
