from typing import Any, TypedDict

from langgraph.graph import StateGraph, START, END

from generators import (
    generate_problem_json, generate_proof_contract, generate_graph_skeleton,
)
from graph_planner import graph_prover
from verifiers import run_all_verifiers


class ProofAgentState(TypedDict, total=False):
    raw_problem: str
    problem_json: dict
    proof_contract: dict
    proof_graph_state: dict
    current_errors: list
    aggregator_result: dict
    accepted: bool
    trace: list


def problem_parser_node(state: ProofAgentState):
    problem_json = generate_problem_json(state["raw_problem"])
    trace = list(state.get("trace", [])) + [{"node": "problem_parser", "source": problem_json.get("_generation_source")}]
    return {"problem_json": problem_json, "trace": trace}


def contract_builder_node(state: ProofAgentState):
    proof_contract = generate_proof_contract(state["problem_json"])
    trace = list(state.get("trace", [])) + [{"node": "contract_builder", "source": proof_contract.get("_generation_source")}]
    return {"proof_contract": proof_contract, "trace": trace}


def graph_planner_node(state: ProofAgentState):
    graph_state = generate_graph_skeleton(state["problem_json"], state["proof_contract"])
    trace = list(state.get("trace", [])) + [{"node": "graph_planner", "source": graph_state.get("_generation_source")}]
    return {"proof_graph_state": graph_state, "trace": trace}


def graph_prover_node(state: ProofAgentState):
    graph_state = graph_prover(state["problem_json"], state["proof_contract"], state["proof_graph_state"])
    trace = list(state.get("trace", [])) + [{"node": "graph_prover"}]
    return {"proof_graph_state": graph_state, "trace": trace}


def run_verifiers_node(state: ProofAgentState):
    result = run_all_verifiers(state["problem_json"], state["proof_contract"], state["proof_graph_state"])
    trace = list(state.get("trace", [])) + [{"node": "run_verifiers", "accepted": result["aggregator"]["all_required_pass"], "error_count": len(result["errors"])}]
    return {
        "proof_graph_state": result["annotated_graph_state"],
        "current_errors": result["errors"],
        "aggregator_result": result["aggregator"],
        "accepted": result["aggregator"]["all_required_pass"],
        "trace": trace,
    }


def export_trace_node(state: ProofAgentState):
    trace = list(state.get("trace", [])) + [{"node": "export_trace", "accepted": state.get("accepted", False)}]
    return {"trace": trace}


def build_week2_langgraph_app():
    builder = StateGraph(ProofAgentState)

    builder.add_node("problem_parser", problem_parser_node)
    builder.add_node("contract_builder", contract_builder_node)
    builder.add_node("graph_planner", graph_planner_node)
    builder.add_node("graph_prover", graph_prover_node)
    builder.add_node("run_verifiers", run_verifiers_node)
    builder.add_node("export_trace", export_trace_node)

    builder.add_edge(START, "problem_parser")
    builder.add_edge("problem_parser", "contract_builder")
    builder.add_edge("contract_builder", "graph_planner")
    builder.add_edge("graph_planner", "graph_prover")
    builder.add_edge("graph_prover", "run_verifiers")
    builder.add_edge("run_verifiers", "export_trace")
    builder.add_edge("export_trace", END)

    return builder.compile()


WEEK2_APP = build_week2_langgraph_app()
