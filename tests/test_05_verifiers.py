"""
Stage 5 — Run Verifiers
Tests: each verifier function individually, plus the aggregator and run_all_verifiers().

Verifier functions are pure (no LLM) unless they call the critic model.
Critic-model verifiers (case_coverage, theorem_applicability) return pass=True
when no model is available, so they are effectively skipped in unit tests.
"""
import copy
import pytest


# ── JSON schema verifier ─────────────────────────────────────────────────────

class TestVerifyJsonSchema:

    def _check(self, name, data, schema_name):
        from verifier_utils import verify_json_schema
        from schemas import PROBLEM_JSON_SCHEMA, PROOF_CONTRACT_SCHEMA, PROOF_GRAPH_STATE_SCHEMA
        schemas = {
            "problem_json": PROBLEM_JSON_SCHEMA,
            "proof_contract": PROOF_CONTRACT_SCHEMA,
            "proof_graph_state": PROOF_GRAPH_STATE_SCHEMA,
        }
        return verify_json_schema(name, data, schemas[schema_name])

    def test_valid_problem_json_produces_no_errors(self, problem_json):
        assert self._check("problem_json", problem_json, "problem_json") == []

    def test_valid_proof_contract_produces_no_errors(self, proof_contract):
        assert self._check("proof_contract", proof_contract, "proof_contract") == []

    def test_valid_graph_state_produces_no_errors(self, graph_state):
        assert self._check("proof_graph_state", graph_state, "proof_graph_state") == []

    def test_schema_error_has_expected_structure(self, problem_json):
        del problem_json["problem_id"]
        errors = self._check("problem_json", problem_json, "problem_json")
        assert len(errors) > 0
        e = errors[0]
        assert e["source"] == "json_schema"
        assert "severity" in e and "evidence" in e and "required_fix" in e


# ── verify_graph_structure ───────────────────────────────────────────────────

class TestVerifyGraphStructure:

    def _run(self, problem_json, proof_contract, graph_state):
        from verifiers import verify_graph_structure
        return verify_graph_structure(problem_json, proof_contract, graph_state)

    def test_valid_graph_produces_no_blocking_errors(
            self, problem_json, proof_contract, graph_state):
        from verifier_utils import blocking_errors
        errors = self._run(problem_json, proof_contract, graph_state)
        blocking = blocking_errors(errors)
        assert blocking == [], f"Unexpected blocking errors: {[e['evidence'] for e in blocking]}"

    def test_missing_goal_node_id_produces_high_severity_error(
            self, problem_json, proof_contract, graph_state):
        del graph_state["goal_node_id"]
        errors = self._run(problem_json, proof_contract, graph_state)
        assert any(e["severity"] == "high" and "goal" in e["claim"].lower() for e in errors)

    def test_goal_node_missing_from_nodes_produces_high_severity_error(
            self, problem_json, proof_contract, graph_state):
        graph_state["nodes"] = [n for n in graph_state["nodes"] if n["id"] != "G1"]
        errors = self._run(problem_json, proof_contract, graph_state)
        assert any(e["severity"] == "high" and "goal" in e["claim"].lower() for e in errors)

    def test_duplicate_node_ids_produce_high_severity_error(
            self, problem_json, proof_contract, graph_state):
        graph_state["nodes"].append(copy.deepcopy(graph_state["nodes"][0]))  # duplicate A1
        errors = self._run(problem_json, proof_contract, graph_state)
        assert any("unique" in e["claim"].lower() for e in errors)

    def test_cycle_in_inference_graph_produces_high_severity_error(
            self, problem_json, proof_contract, graph_state):
        # Add an inference that creates a cycle: G1 → L1
        graph_state["inferences"].append({
            "id": "ICycle", "premise_nodes": ["G1"], "side_condition_nodes": [],
            "conclusion_node": "L1", "rule_refs": ["chain_rule"],
            "relation": "implies", "status": "planned",
        })
        errors = self._run(problem_json, proof_contract, graph_state)
        assert any("dag" in e["claim"].lower() or "cycle" in e["evidence"].lower() for e in errors)

    def test_unknown_rule_ref_in_inference_produces_high_severity_error(
            self, problem_json, proof_contract, graph_state):
        graph_state["inferences"][0]["rule_refs"] = ["forbidden_magic_rule"]
        errors = self._run(problem_json, proof_contract, graph_state)
        assert any("allowed_references" in e["evidence"] for e in errors)

    def test_vague_justification_in_proof_body_produces_medium_error(
            self, problem_json, proof_contract, graph_state):
        graph_state["nodes"][1]["proof_body"] = {
            "steps": [{"statement": "This is clearly true", "reason": "obvious", "refs": []}]
        }
        errors = self._run(problem_json, proof_contract, graph_state)
        vague_errors = [e for e in errors if e["severity"] == "medium" and "vague" in e.get("evidence", "").lower()]
        assert len(vague_errors) > 0


# ── verify_obligation_coverage ───────────────────────────────────────────────

class TestVerifyObligationCoverage:

    def _run(self, proof_contract, graph_state):
        from verifiers import verify_obligation_coverage
        return verify_obligation_coverage(proof_contract, graph_state)

    def test_no_node_has_covers_obligations_errors_are_medium_and_non_blocking(
            self, proof_contract, graph_state):
        # Default graph_state has no covers_obligations on any node.
        errors = self._run(proof_contract, graph_state)
        for e in errors:
            assert e["severity"] == "medium", "Expected medium when model never sets covers_obligations"
            assert e["blocking_acceptance"] is False

    def test_some_nodes_have_covers_obligations_uncovered_is_high_blocking(
            self, proof_contract, graph_state):
        # Mark G1 as covering O1 only; O2 becomes a blocking gap.
        graph_state["nodes"][2]["covers_obligations"] = ["O1"]
        errors = self._run(proof_contract, graph_state)
        o2_errors = [e for e in errors if "O2" in e["claim"]]
        assert len(o2_errors) > 0
        assert all(e["severity"] == "high" and e["blocking_acceptance"] for e in o2_errors)

    def test_all_obligations_covered_produces_no_errors(
            self, proof_contract, graph_state):
        graph_state["nodes"][2]["covers_obligations"] = ["O1", "O2"]
        errors = self._run(proof_contract, graph_state)
        assert errors == []

    def test_empty_obligations_list_produces_no_errors(
            self, proof_contract, graph_state):
        proof_contract["obligations"] = []
        errors = self._run(proof_contract, graph_state)
        assert errors == []


# ── verify_node_proofs ───────────────────────────────────────────────────────

class TestVerifyNodeProofs:

    def _run(self, problem_json, proof_contract, graph_state):
        from verifiers import verify_node_proofs
        return verify_node_proofs(problem_json, proof_contract, graph_state)

    def test_source_nodes_skipped_no_error_for_empty_proof_body(
            self, problem_json, proof_contract, graph_state):
        errors = self._run(problem_json, proof_contract, graph_state)
        source_errors = [e for e in errors if e.get("node_id") == "A1"]
        assert source_errors == []

    def test_non_source_node_with_empty_proof_body_produces_high_severity_error(
            self, problem_json, proof_contract, graph_state):
        errors = self._run(problem_json, proof_contract, graph_state)
        non_source_errors = [e for e in errors if e.get("node_id") in ("L1", "G1")]
        assert len(non_source_errors) > 0
        assert all(e["severity"] == "high" for e in non_source_errors)

    def test_proof_body_steps_empty_list_produces_error(
            self, problem_json, proof_contract, proven_graph_state):
        proven_graph_state["nodes"][1]["proof_body"]["steps"] = []
        errors = self._run(problem_json, proof_contract, proven_graph_state)
        l1_errors = [e for e in errors if e.get("node_id") == "L1"]
        assert len(l1_errors) > 0

    def test_final_step_contains_node_claim_passes(
            self, problem_json, proof_contract, proven_graph_state):
        errors = self._run(problem_json, proof_contract, proven_graph_state)
        # proven_graph_state has correct proofs with claim in final step.
        non_source_errors = [e for e in errors if e.get("node_id") in ("L1", "G1")]
        assert non_source_errors == [], f"Unexpected errors: {non_source_errors}"

    def test_final_step_does_not_contain_claim_produces_error(
            self, problem_json, proof_contract, proven_graph_state):
        proven_graph_state["nodes"][2]["proof_body"]["steps"][-1]["statement"] = "unrelated conclusion"
        errors = self._run(problem_json, proof_contract, proven_graph_state)
        g1_errors = [e for e in errors if e.get("node_id") == "G1"]
        assert len(g1_errors) > 0


# ── verify_symbolic ──────────────────────────────────────────────────────────

class TestVerifySymbolic:

    def _run(self, problem_json, graph_state):
        from verifiers import verify_symbolic
        return verify_symbolic(problem_json, graph_state)

    def test_correct_derivative_in_goal_symbolic_passes(
            self, problem_json, graph_state):
        # problem_json goal.symbolic = "d/dx sin(x**2) = 2*x*cos(x**2)" — should be correct.
        errors = self._run(problem_json, graph_state)
        assert errors == [], f"Unexpected symbolic errors: {[e['evidence'] for e in errors]}"

    def test_wrong_derivative_in_goal_symbolic_fails(
            self, problem_json, graph_state):
        problem_json["goal"]["symbolic"] = "d/dx sin(x**2) = 2*x*sin(x**2)"  # wrong: should be cos
        errors = self._run(problem_json, graph_state)
        assert len(errors) > 0

    def test_correct_equation_in_node_claim_formal_passes(
            self, problem_json, graph_state):
        graph_state["nodes"][1]["claim_formal"] = "2*x + 0 = 2*x"
        errors = self._run(problem_json, graph_state)
        assert errors == []

    def test_wrong_equation_in_node_claim_formal_fails(
            self, problem_json, graph_state):
        graph_state["nodes"][1]["claim_formal"] = "x + 1 = x + 2"
        errors = self._run(problem_json, graph_state)
        assert len(errors) > 0

    def test_non_parseable_symbolic_text_skipped_gracefully(
            self, problem_json, graph_state):
        # A prose claim with no '=' sign → no symbolic item → no error.
        graph_state["nodes"][1]["claim_formal"] = "f is continuous on the interval"
        errors = self._run(problem_json, graph_state)
        assert errors == []


# ── verify_inferences ────────────────────────────────────────────────────────

class TestVerifyInferences:

    def _run(self, problem_json, proof_contract, graph_state):
        from verifiers import verify_inferences
        return verify_inferences(problem_json, proof_contract, graph_state)

    def test_valid_inferences_produce_no_errors(
            self, problem_json, proof_contract, graph_state):
        errors = self._run(problem_json, proof_contract, graph_state)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_missing_premise_node_produces_high_severity_error(
            self, problem_json, proof_contract, graph_state):
        graph_state["inferences"][0]["premise_nodes"] = ["NONEXISTENT"]
        errors = self._run(problem_json, proof_contract, graph_state)
        assert any(e["severity"] == "high" and "missing" in e["evidence"].lower() for e in errors)

    def test_empty_rule_refs_produces_high_severity_error(
            self, problem_json, proof_contract, graph_state):
        graph_state["inferences"][0]["rule_refs"] = []
        errors = self._run(problem_json, proof_contract, graph_state)
        assert any("rule_refs" in e["evidence"].lower() for e in errors)

    def test_missing_conclusion_node_produces_high_severity_error(
            self, problem_json, proof_contract, graph_state):
        graph_state["inferences"][0]["conclusion_node"] = "NONEXISTENT"
        errors = self._run(problem_json, proof_contract, graph_state)
        assert any(e["severity"] == "high" for e in errors)


# ── verify_inference_closure ─────────────────────────────────────────────────

class TestVerifyInferenceClosure:

    def _run(self, problem_json, proof_contract, graph_state, prior_errors=None):
        from verifiers import verify_inference_closure
        return verify_inference_closure(
            problem_json, proof_contract, graph_state, prior_errors or [])

    def test_valid_chain_of_inferences_produces_no_closure_errors(
            self, problem_json, proof_contract, proven_graph_state):
        errors = self._run(problem_json, proof_contract, proven_graph_state)
        assert errors == [], f"Unexpected closure errors: {errors}"

    def test_non_source_node_with_no_incoming_inference_produces_closure_error(
            self, problem_json, proof_contract, graph_state):
        # Remove all inferences so no non-source node can be reached.
        graph_state["inferences"] = []
        errors = self._run(problem_json, proof_contract, graph_state)
        # L1 and G1 should both fail closure.
        node_ids = {e["node_id"] for e in errors}
        assert "L1" in node_ids or "G1" in node_ids

    def test_goal_node_not_reachable_via_inference_produces_closure_error(
            self, problem_json, proof_contract, proven_graph_state):
        # Remove I2 so G1 cannot be reached.
        proven_graph_state["inferences"] = [
            i for i in proven_graph_state["inferences"] if i["id"] != "I2"
        ]
        errors = self._run(problem_json, proof_contract, proven_graph_state)
        g1_errors = [e for e in errors if e.get("node_id") == "G1"]
        assert len(g1_errors) > 0


# ── annotate_and_aggregate ───────────────────────────────────────────────────

class TestAnnotateAndAggregate:

    def _run(self, problem_json, proof_contract, graph_state, errors=None):
        from verifiers import annotate_and_aggregate
        return annotate_and_aggregate(problem_json, proof_contract, graph_state, errors or [])

    def test_output_has_expected_aggregator_keys(
            self, problem_json, proof_contract, graph_state):
        _, agg = self._run(problem_json, proof_contract, graph_state)
        assert "all_required_pass" in agg
        assert "blocking_errors" in agg
        assert "failed_nodes" in agg
        assert "failed_obligations" in agg

    def test_proven_graph_with_no_blocking_errors_is_accepted(
            self, monkeypatch, problem_json, proof_contract, proven_graph_state):
        import verifiers
        # Disable critic-model calls so they don't add unexpected errors.
        monkeypatch.setattr(verifiers, "_get_active_llm", lambda: None)
        result = verifiers.run_all_verifiers(problem_json, proof_contract, proven_graph_state)
        assert result["aggregator"]["all_required_pass"] is True

    def test_high_severity_error_makes_accepted_false(
            self, problem_json, proof_contract, proven_graph_state):
        from verifier_utils import make_error
        blocking_error = make_error(
            "structural", "G1", None, "high", "test claim", "test evidence", "fix it")
        _, agg = self._run(problem_json, proof_contract, proven_graph_state, [blocking_error])
        assert agg["all_required_pass"] is False

    def test_annotated_graph_nodes_get_verified_or_failed_status(
            self, problem_json, proof_contract, proven_graph_state):
        annotated, _ = self._run(problem_json, proof_contract, proven_graph_state)
        valid_statuses = {"verified", "failed", "source"}
        for node in annotated["nodes"]:
            assert node["status"] in valid_statuses or node["node_type"] in {"assumption", "allowed_reference"}, \
                f"Node {node['id']} has unexpected status {node['status']}"

    def test_obligation_status_present_in_annotated_graph(
            self, problem_json, proof_contract, proven_graph_state):
        annotated, _ = self._run(problem_json, proof_contract, proven_graph_state)
        assert "obligation_status" in annotated
        assert isinstance(annotated["obligation_status"], list)


# ── run_all_verifiers integration ────────────────────────────────────────────

class TestRunAllVerifiers:

    def test_output_has_required_keys(
            self, monkeypatch, problem_json, proof_contract, graph_state):
        import verifiers
        monkeypatch.setattr(verifiers, "_get_active_llm", lambda: None)
        result = verifiers.run_all_verifiers(problem_json, proof_contract, graph_state)
        assert "errors" in result
        assert "annotated_graph_state" in result
        assert "aggregator" in result

    def test_each_error_has_error_id_assigned(
            self, monkeypatch, problem_json, proof_contract, graph_state):
        import verifiers
        monkeypatch.setattr(verifiers, "_get_active_llm", lambda: None)
        result = verifiers.run_all_verifiers(problem_json, proof_contract, graph_state)
        for err in result["errors"]:
            assert "error_id" in err and err["error_id"].startswith("E")

    def test_invalid_schema_stops_later_verifiers(
            self, monkeypatch, problem_json, proof_contract, graph_state):
        import verifiers
        monkeypatch.setattr(verifiers, "_get_active_llm", lambda: None)
        del problem_json["problem_id"]  # break schema
        result = verifiers.run_all_verifiers(problem_json, proof_contract, graph_state)
        # Should have schema errors and accepted=False.
        schema_errs = [e for e in result["errors"] if e["source"] == "json_schema"]
        assert len(schema_errs) > 0
        assert result["aggregator"]["all_required_pass"] is False

    def test_unproven_graph_is_not_accepted(
            self, monkeypatch, problem_json, proof_contract, graph_state):
        import verifiers
        monkeypatch.setattr(verifiers, "_get_active_llm", lambda: None)
        # graph_state has no proof bodies → should not be accepted.
        result = verifiers.run_all_verifiers(problem_json, proof_contract, graph_state)
        assert result["aggregator"]["all_required_pass"] is False
