import json
import re

import networkx as nx
import sympy as sp
from jsonschema import Draft202012Validator

from config import SOURCE_NODE_TYPES, VAGUE_TERMS


def make_error(source, node_id, inference_id, severity, claim, evidence, required_fix, blocking_acceptance=True):
    return {"source": source, "node_id": node_id, "inference_id": inference_id, "step_id": None, "severity": severity, "claim": claim, "evidence": evidence, "required_fix": required_fix, "blocking_acceptance": bool(blocking_acceptance)}


def with_error_ids(errors):
    output = []
    for index, error in enumerate(errors, start=1):
        copied = dict(error)
        copied["error_id"] = f"E{index}"
        output.append(copied)
    return output


def verify_json_schema(name, data, schema):
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        path = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(make_error("json_schema", None, None, "high", f"{name} must match schema", f"{path}: {error.message}", "Fix JSON format before later verifiers."))
    return errors


def normalize_math_text(text):
    s = str(text).lower()
    s = s.replace(" ", "").replace("*", "").replace("'", "prime").replace("′", "prime").replace("∘", "o")
    return re.sub(r"[^a-z0-9_=()+/\\-]", "", s)


def allowed_references(contract):
    refs = contract.get("allowed_references", [])
    return {r.strip() for r in refs if isinstance(r, str) and r.strip()}


def is_source_node(node, problem_json=None, proof_contract=None):
    return node.get("node_type") in SOURCE_NODE_TYPES


def has_proof_steps(node):
    proof_body = node.get("proof_body", {})
    return isinstance(proof_body, dict) and bool(proof_body.get("steps"))


def declared_variable_symbols(problem_json):
    declared = set()
    for variable in problem_json.get("variables", []):
        symbol = variable.get("symbol") if isinstance(variable, dict) else variable
        if symbol:
            declared.add(str(symbol))
    domain = problem_json.get("domain", {})
    if isinstance(domain, dict):
        declared.update(str(symbol) for symbol in domain.keys())
    return declared


_MATH_BUILTINS = {
    # Conventional single-letter function/sequence names
    "f", "g", "h",
    # Calculus shorthand notation
    "d", "dx", "dy", "dz", "dt", "df",
    # Trig and elementary functions
    "sin", "cos", "tan", "sec", "csc", "cot",
    "arcsin", "arccos", "arctan", "asin", "acos", "atan",
    "sinh", "cosh", "tanh",
    "exp", "log", "ln", "sqrt", "abs",
    # SymPy names
    "Eq", "Ne", "Lt", "Le", "Gt", "Ge",
    "Derivative", "Integral", "Limit", "Sum", "Product",
    "Function", "Symbol", "Integer", "Float", "Rational",
    "diff", "integrate", "limit", "simplify",
    # Common math keywords
    "lim", "sup", "inf", "max", "min",
    "forall", "exists",
    # Logic keywords
    "true", "false", "implies", "iff",
}


def extract_symbol_names(text):
    raw = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", str(text)))
    return raw - _MATH_BUILTINS


PROOF_DECLARATION_FIELD = "declarations"


def declaration_symbols(items):
    symbols = set()
    for item in items or []:
        if isinstance(item, dict):
            symbol = item.get("symbol")
        elif isinstance(item, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item.strip()):
            symbol = item.strip()
        else:
            symbol = None
        if symbol:
            symbols.add(str(symbol))
    return symbols


def node_declared_symbols(node):
    return declaration_symbols(node.get(PROOF_DECLARATION_FIELD, []))


def inference_declared_symbols(inference):
    return declaration_symbols(inference.get(PROOF_DECLARATION_FIELD, []))


def node_symbol_texts(node):
    texts = []
    if node.get("claim_formal"):
        texts.append(("claim_formal", node.get("claim_formal")))
    return texts


def inference_symbol_texts(inference):
    texts = []
    instantiation = inference.get("instantiation", {})
    if isinstance(instantiation, dict):
        for key, value in instantiation.items():
            if value is not None:
                texts.append((f"instantiation.{key}", str(value)))
    return texts


def node_map(graph_state):
    return {node["id"]: node for node in graph_state.get("nodes", [])}


def build_nx_graph(graph_state):
    graph = nx.DiGraph()
    for node in graph_state.get("nodes", []):
        graph.add_node(node["id"])
    for inference in graph_state.get("inferences", []):
        conclusion = inference.get("conclusion_node")
        for premise in inference.get("premise_nodes", []):
            graph.add_edge(premise, conclusion, inference_id=inference.get("id"))
        for side in inference.get("side_condition_nodes", []):
            graph.add_edge(side, conclusion, inference_id=inference.get("id"))
    return graph


def blocking_errors(errors):
    return [error for error in errors if error.get("blocking_acceptance") or error.get("severity") == "high"]
