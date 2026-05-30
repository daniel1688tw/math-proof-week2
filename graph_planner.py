import copy

from generators import (
    generate_problem_json, generate_proof_contract,
    generate_graph_skeleton, generate_node_proof,
)
from verifier_utils import is_source_node
from verifiers import run_all_verifiers


def graph_planner(raw_problem):
    problem_json = generate_problem_json(raw_problem)
    proof_contract = generate_proof_contract(problem_json)
    graph_state = generate_graph_skeleton(problem_json, proof_contract)
    return problem_json, proof_contract, graph_state


def graph_prover(problem_json, proof_contract, graph_state):
    graph_state = copy.deepcopy(graph_state)
    for node in graph_state.get("nodes", []):
        if is_source_node(node, problem_json, proof_contract):
            continue
        if not node.get("proof_body", {}).get("steps"):
            try:
                node["proof_body"] = generate_node_proof(
                    problem_json, proof_contract, graph_state, node
                )
                node["status"] = "proven"
            except Exception as exc:
                print(f"  [graph_prover] node {node.get('id')} failed: {exc!r:.120}")
                node["proof_body"] = {"steps": [], "_generation_error": str(exc)}
                node["status"] = "proof_failed"
        else:
            node["status"] = "proven"
    return graph_state


def full_model_pipeline(raw_problem):
    problem_json, proof_contract, graph_state = graph_planner(raw_problem)
    graph_state = graph_prover(problem_json, proof_contract, graph_state)
    result = run_all_verifiers(problem_json, proof_contract, graph_state)
    return {
        "problem_json": problem_json,
        "proof_contract": proof_contract,
        "proof_graph_state": result["annotated_graph_state"],
        "errors": result["errors"],
        "aggregator": result["aggregator"],
    }
