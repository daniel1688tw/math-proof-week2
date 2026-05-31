import copy
import itertools
import json
import re

import networkx as nx
import sympy as sp

from config import SOURCE_NODE_TYPES, VAGUE_TERMS
from schemas import PROBLEM_JSON_SCHEMA, PROOF_CONTRACT_SCHEMA, PROOF_GRAPH_STATE_SCHEMA
from verifier_utils import (
    make_error, with_error_ids, verify_json_schema,
    normalize_math_text, allowed_references, is_source_node, has_proof_steps,
    declared_variable_symbols, extract_symbol_names,
    node_declared_symbols, inference_declared_symbols,
    node_symbol_texts, inference_symbol_texts,
    node_map, build_nx_graph, blocking_errors,
    PROOF_DECLARATION_FIELD,
)
from json_utils import parse_json_from_text


# ── Structural Verifier ──────────────────────────────────────────────────────

def verify_variable_declarations(problem_json, graph_state):
    errors = []
    base_declared = declared_variable_symbols(problem_json)
    nodes_by_id = node_map(graph_state)
    inferences = graph_state.get("inferences", [])
    declared_after_node = {node_id: set(base_declared) | node_declared_symbols(node) for node_id, node in nodes_by_id.items()}

    changed = True
    while changed:
        changed = False
        for inference in inferences:
            conclusion = inference.get("conclusion_node")
            if conclusion not in nodes_by_id:
                continue
            available = set(base_declared)
            for dep in list(inference.get("premise_nodes", [])) + list(inference.get("side_condition_nodes", [])):
                available.update(declared_after_node.get(dep, set(base_declared)))
            available.update(inference_declared_symbols(inference))
            available.update(node_declared_symbols(nodes_by_id[conclusion]))
            if not available.issubset(declared_after_node[conclusion]):
                declared_after_node[conclusion].update(available)
                changed = True

    goal = problem_json.get("goal", {})
    goal_symbolic = goal.get("symbolic", "") if isinstance(goal, dict) else ""
    if goal_symbolic:
        missing = sorted(extract_symbol_names(goal_symbolic) - base_declared)
        if missing:
            errors.append(make_error("structural", None, None, "high", goal_symbolic, f"problem_json.goal.symbolic uses undeclared variable/function(s): {', '.join(missing)}.", "Declare the variable/function in problem_json.variables/domain before using it."))

    for node in graph_state.get("nodes", []):
        node_id = node.get("id")
        available = set(declared_after_node.get(node_id, base_declared))
        for label, text in node_symbol_texts(node):
            missing = sorted(extract_symbol_names(text) - available)
            if missing:
                errors.append(make_error("structural", node_id, None, "high", text, f"{label} uses undeclared variable/function(s): {', '.join(missing)}.", "Declare the variable/function earlier in problem_json or in an ancestor proof node/inference."))

    for inference in inferences:
        inf_id = inference.get("id")
        conclusion = inference.get("conclusion_node")
        available = set(base_declared)
        for dep in list(inference.get("premise_nodes", [])) + list(inference.get("side_condition_nodes", [])):
            available.update(declared_after_node.get(dep, set(base_declared)))
        available.update(inference_declared_symbols(inference))
        for label, text in inference_symbol_texts(inference):
            missing = sorted(extract_symbol_names(text) - available)
            if missing:
                errors.append(make_error("structural", conclusion, inf_id, "high", text, f"{label} uses undeclared variable/function(s): {', '.join(missing)}.", "Declare the variable/function earlier in problem_json, an ancestor node, or this inference declaration field."))

    return errors


def verify_obligation_coverage(proof_contract, graph_state):
    errors = []
    obligations = proof_contract.get("obligations", [])
    obligation_ids = [ob.get("id") for ob in obligations if isinstance(ob, dict) and ob.get("id")]
    covered_by = {}
    any_node_has_covers = False
    for node in graph_state.get("nodes", []):
        node_id = node.get("id")
        covers = node.get("covers_obligations", [])
        if covers:
            any_node_has_covers = True
        for ob_id in covers:
            covered_by.setdefault(ob_id, set()).add(node_id)
    severity = "high" if any_node_has_covers else "medium"
    blocking = any_node_has_covers
    for ob_id in obligation_ids:
        if ob_id not in covered_by:
            errors.append(make_error("structural", None, None, severity, f"Obligation {ob_id} must be covered by some node.", f"{ob_id} is not listed in any node.covers_obligations.", "Add this obligation id to covers_obligations of a node that covers it.", blocking))
    return errors


def verify_graph_structure(problem_json, proof_contract, graph_state):
    errors = []
    nodes = graph_state.get("nodes", [])
    inferences = graph_state.get("inferences", [])
    nodes_by_id = node_map(graph_state)
    node_ids = [node.get("id") for node in nodes]
    inference_ids = [inf.get("id") for inf in inferences]
    allowed = allowed_references(proof_contract)
    forbidden = " ".join(proof_contract.get("forbidden_moves", [])).lower()

    if len(node_ids) != len(set(node_ids)):
        errors.append(make_error("structural", None, None, "high", "Node ids must be unique.", str(node_ids), "Give each node a unique id."))

    if len(inference_ids) != len(set(inference_ids)):
        errors.append(make_error("structural", None, None, "high", "Inference ids must be unique.", str(inference_ids), "Give each inference a unique id."))

    for node in nodes:
        if node.get("status") == "source" and not is_source_node(node, problem_json, proof_contract):
            errors.append(make_error("structural", node.get("id"), None, "high", node.get("claim", ""), "Source graph node must be assumption or allowed_reference.", "Use node_type=assumption or node_type=allowed_reference."))

    errors += verify_variable_declarations(problem_json, graph_state)
    errors += verify_obligation_coverage(proof_contract, graph_state)

    for inf in inferences:
        inf_id = inf.get("id")
        conclusion = inf.get("conclusion_node")

        if conclusion not in nodes_by_id:
            errors.append(make_error("structural", conclusion, inf_id, "high", "Conclusion node must exist.", f"conclusion_node={conclusion} is referenced by {inf_id} but missing.", "Create the conclusion node or fix inference.conclusion_node."))

        refs = list(inf.get("premise_nodes", [])) + list(inf.get("side_condition_nodes", []))
        for ref in refs:
            if ref not in nodes_by_id:
                errors.append(make_error("structural", ref, inf_id, "high", "Referenced premise/side-condition node must exist.", f"{ref} is referenced by {inf_id} but missing.", "Create the missing premise/side-condition node or fix the inference reference."))

        for rule in inf.get("rule_refs", []):
            if allowed and rule.strip() not in allowed:
                errors.append(make_error("structural", conclusion, inf_id, "high", nodes_by_id.get(conclusion, {}).get("claim", ""), f"{rule} is not in allowed_references.", "Use only references listed in proof_contract.allowed_references."))
            if rule.lower() in forbidden:
                errors.append(make_error("structural", conclusion, inf_id, "high", nodes_by_id.get(conclusion, {}).get("claim", ""), f"{rule} appears in forbidden_moves.", "Remove forbidden move."))

    graph = build_nx_graph(graph_state)

    if not nx.is_directed_acyclic_graph(graph):
        errors.append(make_error("structural", None, None, "high", "Proof graph must be DAG.", f"Cycle detected: {list(nx.find_cycle(graph))}", "Remove cycle."))

    goal_id = graph_state.get("goal_node_id")
    if not goal_id or goal_id not in nodes_by_id:
        missing_id = goal_id or "(goal_node_id not set)"
        errors.append(make_error("structural", goal_id, None, "high", "Goal node must exist.", f"{missing_id} missing.", "Create goal node."))
    else:
        goal_claim = nodes_by_id[goal_id].get("claim", "")
        goal_obj = problem_json.get("goal", {})
        goal_text = (goal_obj.get("text", "") or goal_obj.get("symbolic", "")) if isinstance(goal_obj, dict) else str(goal_obj)
        if goal_text and normalize_math_text(goal_text) not in normalize_math_text(goal_claim):
            errors.append(make_error("structural", goal_id, None, "high", goal_claim, f"Goal node does not align with {goal_text}.", "Align goal node with problem_json.goal."))

    incoming_counts = {node_id: 0 for node_id in node_ids}
    for inference in inferences:
        conclusion = inference.get("conclusion_node")
        if conclusion in incoming_counts:
            incoming_counts[conclusion] += 1

    for node in nodes:
        node_id = node.get("id")
        node_type = node.get("node_type")
        if node_type not in SOURCE_NODE_TYPES and incoming_counts.get(node_id, 0) == 0 and node_id != graph_state.get("goal_node_id"):
            errors.append(make_error("structural", node_id, None, "medium", node.get("claim", ""), "Non-source node has no incoming inference.", "Add an inference proving this node.", False))

        proof_text = json.dumps(node.get("proof_body", {}), ensure_ascii=False).lower()
        for vague_term in VAGUE_TERMS:
            if vague_term.lower() in proof_text:
                errors.append(make_error("structural", node_id, None, "medium", node.get("claim", ""), f"Vague justification detected: {vague_term}", "Replace vague wording with named references.", False))

    return errors


# ── Node Proof Verifier ──────────────────────────────────────────────────────

def proof_body_steps(node):
    proof_body = node.get("proof_body", {})
    if not isinstance(proof_body, dict):
        return []
    steps = proof_body.get("steps", [])
    return steps if isinstance(steps, list) else []


def proof_step_statement(step):
    if not isinstance(step, dict):
        return ""
    return str(step.get("statement", "")).strip()


def proof_concludes_node_claim(node):
    steps = proof_body_steps(node)
    if not steps:
        return False, "proof_body.steps is empty."
    for index, step in enumerate(steps, start=1):
        if not proof_step_statement(step):
            return False, f"proof_body.steps[{index}] has no statement."
    targets = [node.get("claim_formal", ""), node.get("claim", "")]
    target_norms = [normalize_math_text(t) for t in targets if t]
    # Check last step first (preferred), then any step
    all_step_norms = [(i, proof_step_statement(s), normalize_math_text(proof_step_statement(s))) for i, s in enumerate(steps)]
    for tn in target_norms:
        if not tn:
            continue
        # Prefer last step
        last_stmt, last_norm = all_step_norms[-1][1], all_step_norms[-1][2]
        if tn in last_norm:
            return True, f"final statement proves node claim: {last_stmt}"
        # Accept any step that contains the claim
        for i, stmt, snorm in all_step_norms:
            if tn in snorm:
                return True, f"step {i+1} proves node claim: {stmt}"
    final_statement = proof_step_statement(steps[-1])
    return False, f"final proof step does not conclude node claim. final_statement={final_statement}"


def verify_node_proofs(problem_json, proof_contract, graph_state):
    errors = []
    for node in graph_state.get("nodes", []):
        node_id = node.get("id")
        if is_source_node(node, problem_json, proof_contract):
            continue
        ok, evidence = proof_concludes_node_claim(node)
        if not ok:
            errors.append(make_error("node_proof", node_id, None, "high", node.get("claim", ""), evidence, "Make the final proof_body.steps statement conclude this node's claim."))
    return errors


# ── Inference Verifier ───────────────────────────────────────────────────────

def inference_verifier_errors(inference, proof_contract, nodes_by_id):
    errors = []
    inference_id = inference.get("id")
    conclusion_id = inference.get("conclusion_node")
    conclusion_node = nodes_by_id.get(conclusion_id)

    if conclusion_node is None:
        errors.append(make_error("inference_verifier", conclusion_id, inference_id, "high", "Conclusion node must exist.", f"conclusion_node={conclusion_id} is missing.", "Create the conclusion node or fix inference.conclusion_node."))
        return errors

    dependency_ids = list(inference.get("premise_nodes", [])) + list(inference.get("side_condition_nodes", []))
    for dep_id in dependency_ids:
        if dep_id not in nodes_by_id:
            errors.append(make_error("inference_verifier", conclusion_id, inference_id, "high", conclusion_node.get("claim", ""), f"dependency node {dep_id} is missing.", "Create the missing premise/side-condition node or fix the inference reference."))

    if errors:
        return errors

    rule_refs = list(inference.get("rule_refs", []))
    if not rule_refs:
        errors.append(make_error("inference_verifier", conclusion_id, inference_id, "high", conclusion_node.get("claim", ""), "inference.rule_refs is empty.", "Add the theorem/definition/rule used by this inference to rule_refs."))

    return errors


def verify_inferences(problem_json, proof_contract, graph_state):
    errors = []
    nodes_by_id = node_map(graph_state)
    for inference in graph_state.get("inferences", []):
        errors += inference_verifier_errors(inference, proof_contract, nodes_by_id)
    return errors


def inference_passes_verifier(inference, proof_contract, nodes_by_id, blocked_infs):
    inference_id = inference.get("id")
    if inference_id in blocked_infs:
        return False
    return len(inference_verifier_errors(inference, proof_contract, nodes_by_id)) == 0


def compute_inference_closure(problem_json, proof_contract, graph_state, errors):
    nodes_by_id = node_map(graph_state)
    blocked_nodes = {error.get("node_id") for error in blocking_errors(errors) if error.get("node_id")}
    blocked_infs = {error.get("inference_id") for error in blocking_errors(errors) if error.get("inference_id")}
    verified_nodes = {node_id for node_id, node in nodes_by_id.items() if is_source_node(node, problem_json, proof_contract) and node_id not in blocked_nodes}
    verified_infs = set()
    changed = True

    while changed:
        changed = False
        for inference in graph_state.get("inferences", []):
            inference_id = inference.get("id")
            if inference_id in verified_infs:
                continue
            if not inference_passes_verifier(inference, proof_contract, nodes_by_id, blocked_infs):
                continue
            dependency_nodes = list(inference.get("premise_nodes", [])) + list(inference.get("side_condition_nodes", []))
            if not all(dep in verified_nodes for dep in dependency_nodes):
                continue
            verified_infs.add(inference_id)
            changed = True
            conclusion = inference.get("conclusion_node")
            if conclusion in nodes_by_id and not is_source_node(nodes_by_id[conclusion], problem_json, proof_contract) and conclusion not in blocked_nodes:
                if conclusion not in verified_nodes:
                    verified_nodes.add(conclusion)

    return verified_nodes, verified_infs


def verify_inference_closure(problem_json, proof_contract, graph_state, errors):
    closure_errors = []
    verified_nodes, verified_infs = compute_inference_closure(problem_json, proof_contract, graph_state, errors)
    blocked_nodes = {error.get("node_id") for error in blocking_errors(errors) if error.get("node_id")}

    for node in graph_state.get("nodes", []):
        node_id = node.get("id")
        if is_source_node(node, problem_json, proof_contract):
            continue
        if node_id in blocked_nodes:
            continue
        if node_id not in verified_nodes:
            closure_errors.append(make_error("inference_closure", node_id, None, "high", node.get("claim", ""), "No verified inference proves this non-source node.", "Add a verified inference whose conclusion_node is this node, whose premise_nodes and side_condition_nodes are source or verified nodes, whose rule_refs are in allowed_references, and whose inference verifier passes."))

    return closure_errors


# ── Symbolic Verifier ────────────────────────────────────────────────────────

def build_sympy_locals(problem_json=None, graph_state=None):
    local_symbols = {}
    for name in ["x", "h", "t", "a", "b", "c", "n"]:
        local_symbols[name] = sp.symbols(name)
    for name, func in {"sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt}.items():
        local_symbols[name] = func
    if problem_json is None:
        return local_symbols
    for variable in problem_json.get("variables", []):
        symbol = variable.get("symbol") if isinstance(variable, dict) else variable
        role_text = json.dumps(variable, ensure_ascii=False).lower() if isinstance(variable, dict) else ""
        if not symbol:
            continue
        if "function" in role_text or "函數" in role_text:
            local_symbols[str(symbol)] = sp.Function(str(symbol))
        else:
            local_symbols[str(symbol)] = sp.symbols(str(symbol))
    for symbol, description in (problem_json.get("domain", {}).items() if isinstance(problem_json.get("domain", {}), dict) else []):
        if str(symbol) not in local_symbols:
            local_symbols[str(symbol)] = sp.symbols(str(symbol))
    return local_symbols


def parse_sympy_expr(expr, local_symbols=None):
    cleaned = str(expr).replace("^", "**").strip()
    return sp.sympify(cleaned, locals=local_symbols or {})


def sympy_is_zero(expr):
    return bool(sp.simplify(expr) == 0)


def split_equation_text(text):
    parts = str(text).split("=", 1)
    if len(parts) != 2:
        return None
    return parts[0].strip(), parts[1].strip()


def integral_check_from_text(text):
    equation = split_equation_text(text)
    if not equation:
        return None
    lhs, rhs = equation
    lhs = lhs.strip()
    patterns = [
        r"(?i)^(?:integral|integrate)\s*\((.+),\s*([A-Za-z_][A-Za-z0-9_]*)\)$",
        r"(?i)^(?:integral|int)\s+(.+)\s+d([A-Za-z_][A-Za-z0-9_]*)$",
        r"^∫\s*(.+)\s*d([A-Za-z_][A-Za-z0-9_]*)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, lhs)
        if match:
            return {"type": "integral", "expr": match.group(1).strip(), "var": match.group(2).strip(), "expected": rhs}
    definite = re.match(r"(?i)^(?:integral|integrate)\s*\((.+),\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*(.+)\s*,\s*(.+)\s*\)\s*\)$", lhs)
    if definite:
        return {"type": "integral", "expr": definite.group(1).strip(), "var": definite.group(2).strip(), "lower": definite.group(3).strip(), "upper": definite.group(4).strip(), "expected": rhs}
    return None


def derivative_check_from_text(text):
    equation = split_equation_text(text)
    if not equation:
        return None
    lhs, rhs = equation
    match = re.match(r"(?i)^d/d([A-Za-z_][A-Za-z0-9_]*)\s+(.+)$", lhs.strip())
    if not match:
        return None
    return {"type": "derivative", "expr": match.group(2).strip(), "var": match.group(1).strip(), "expected": rhs.strip()}


def limit_check_from_text(text):
    equation = split_equation_text(text)
    if not equation:
        return None
    lhs, rhs = equation
    match = re.match(r"(?i)^lim\s+([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([^ ]+)\s+(.+)$", lhs.strip())
    if not match:
        return None
    return {"type": "limit", "expr": match.group(3).strip(), "var": match.group(1).strip(), "point": match.group(2).strip(), "expected": rhs.strip()}


def equation_check_from_text(text):
    if any(marker in str(text).lower() for marker in ["lim", "d/d", "integral", "integrate", "∫"]):
        return None
    equation = split_equation_text(text)
    if not equation:
        return None
    lhs, rhs = equation
    return {"type": "equation", "lhs": lhs, "rhs": rhs}


def symbolic_items_from_text(text):
    checks = []
    for builder in [integral_check_from_text, derivative_check_from_text, limit_check_from_text, equation_check_from_text]:
        check = builder(text)
        if check:
            checks.append(check)
            break
    return checks


def run_symbolic_item(check, problem_json=None):
    locals_map = build_sympy_locals(problem_json)
    check_type = check.get("type")
    if check_type == "equation":
        lhs = parse_sympy_expr(check["lhs"], locals_map)
        rhs = parse_sympy_expr(check["rhs"], locals_map)
        return sympy_is_zero(lhs - rhs), f"simplify(({lhs}) - ({rhs})) == 0"
    if check_type == "limit":
        var = locals_map.get(check.get("var", "x"), sp.symbols(check.get("var", "x")))
        expr = parse_sympy_expr(check["expr"], locals_map)
        point = parse_sympy_expr(str(check["point"]), locals_map)
        expected = parse_sympy_expr(str(check["expected"]), locals_map)
        computed = sp.limit(expr, var, point)
        return sympy_is_zero(computed - expected), f"computed={computed}, expected={expected}"
    if check_type == "derivative":
        var = locals_map.get(check.get("var", "x"), sp.symbols(check.get("var", "x")))
        expr = parse_sympy_expr(check["expr"], locals_map)
        expected = parse_sympy_expr(check["expected"], locals_map)
        computed = sp.diff(expr, var)
        return sympy_is_zero(computed - expected), f"computed={computed}, expected={expected}"
    if check_type == "integral":
        var = locals_map.get(check.get("var", "x"), sp.symbols(check.get("var", "x")))
        expr = parse_sympy_expr(check["expr"], locals_map)
        expected = parse_sympy_expr(check["expected"], locals_map)
        if "lower" in check and "upper" in check:
            lower = parse_sympy_expr(str(check["lower"]), locals_map)
            upper = parse_sympy_expr(str(check["upper"]), locals_map)
            computed = sp.integrate(expr, (var, lower, upper))
            return sympy_is_zero(computed - expected), f"computed={computed}, expected={expected}"
        derivative_back = sp.diff(expected, var)
        return sympy_is_zero(derivative_back - expr), f"d/d{var}({expected})={derivative_back}, integrand={expr}"
    return False, f"Unknown symbolic item type: {check_type}"


def collect_symbolic_items(problem_json, graph_state):
    checks = []
    goal_symbolic = problem_json.get("goal", {}).get("symbolic", "") if isinstance(problem_json.get("goal", {}), dict) else ""
    for check in symbolic_items_from_text(goal_symbolic):
        checks.append(("problem_goal", None, check))
    for node in graph_state.get("nodes", []):
        node_id = node.get("id")
        for text in [node.get("claim_formal", "")]:
            for check in symbolic_items_from_text(text):
                checks.append(("node_claim", node_id, check))
    return checks


def sample_points_from_domain(problem_json):
    domain_text = json.dumps(problem_json.get("domain", {}), ensure_ascii=False).lower()
    if "positive" in domain_text or "> 0" in domain_text or "正" in domain_text:
        return [sp.Integer(1), sp.Integer(2), sp.Integer(3)]
    if "nonzero" in domain_text or "not zero" in domain_text or "不為0" in domain_text or "不等於0" in domain_text:
        return [sp.Integer(-2), sp.Integer(-1), sp.Integer(1), sp.Integer(2)]
    return [sp.Integer(-2), sp.Integer(-1), sp.Integer(0), sp.Integer(1), sp.Integer(2)]


def function_names_in_expression(text):
    known = {"sin", "cos", "tan", "exp", "log", "sqrt", "Integral", "integral", "limit", "lim"}
    return sorted(set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", str(text))) - known)


def substitute_sample_functions(text, function_map):
    output = str(text)
    for name, expr_text in function_map.items():
        output = re.sub(rf"\b{name}\s*\(\s*x\s*\)", f"({expr_text})", output)
    return output


def sample_function_candidates(problem_json):
    text = json.dumps({"assumptions": problem_json.get("assumptions", []), "domain": problem_json.get("domain", {})}, ensure_ascii=False).lower()
    if "positive" in text or "正" in text:
        return ["x**2 + 1", "exp(x)"]
    if "nonzero" in text or "不為0" in text or "不等於0" in text:
        return ["x**2 + 1", "exp(x)"]
    return ["x", "x + 1", "x**2 + 1", "sin(x)", "exp(x)"]


def sample_counterexample_for_equation(check, problem_json):
    lhs_text = str(check.get("lhs", ""))
    rhs_text = str(check.get("rhs", ""))
    function_names = sorted(set(function_names_in_expression(lhs_text + " " + rhs_text)))
    candidates = sample_function_candidates(problem_json)
    points = sample_points_from_domain(problem_json)
    maps = [dict(zip(function_names, combo)) for combo in itertools.product(candidates[:3], repeat=min(len(function_names), 2))] if function_names else [{}]
    if len(function_names) > 2:
        maps = [dict(zip(function_names, candidates[:1] * len(function_names)))]
    locals_map = build_sympy_locals(problem_json)
    for function_map in maps:
        lhs_sub = substitute_sample_functions(lhs_text, function_map)
        rhs_sub = substitute_sample_functions(rhs_text, function_map)
        try:
            lhs = parse_sympy_expr(lhs_sub, locals_map)
            rhs = parse_sympy_expr(rhs_sub, locals_map)
        except Exception as exc:
            return False, f"sample substitution parse failed: {repr(exc)}"
        free_symbols = sorted((lhs - rhs).free_symbols, key=lambda item: str(item))
        sample_symbol = free_symbols[0] if free_symbols else locals_map.get("x", sp.symbols("x"))
        for point in points:
            try:
                value = sp.N((lhs - rhs).subs(sample_symbol, point))
                if value.is_finite and abs(float(value)) > 1e-8:
                    return False, f"counterexample: {sample_symbol}={point}, functions={function_map}, lhs-rhs={value}"
            except Exception:
                continue
    return True, "no sample counterexample found"


def verify_symbolic(problem_json, graph_state):
    errors = []
    for source, node_id, check in collect_symbolic_items(problem_json, graph_state):
        try:
            ok, evidence = run_symbolic_item(check, problem_json)
        except Exception as exc:
            ok, evidence = False, f"symbolic item raised {repr(exc)}"
        if not ok:
            errors.append(make_error("symbolic", node_id, None, "high", str(check), evidence, "Fix the symbolic claim or computation."))
        if check.get("type") == "equation":
            sample_ok, sample_evidence = sample_counterexample_for_equation(check, problem_json)
            if not sample_ok:
                errors.append(make_error("symbolic", node_id, None, "high", str(check), sample_evidence, "Fix the claim; a sample satisfying assumptions/domain produced a counterexample."))
    return errors


# ── Critic Verifier ──────────────────────────────────────────────────────────

def graph_proof_text(problem_json, proof_contract, graph_state):
    payload = {"problem_json": problem_json, "proof_contract": proof_contract, "graph_state": graph_state}
    return json.dumps(payload, ensure_ascii=False).lower()


def text_mentions_any(text, keywords):
    return any(keyword.lower() in text for keyword in keywords)


def case_coverage_payload(problem_json, graph_state):
    return {
        "problem_json": problem_json,
        "nodes": graph_state.get("nodes", []),
        "inferences": graph_state.get("inferences", []),
        "goal_node_id": graph_state.get("goal_node_id"),
    }


def prompt_case_coverage_critic(problem_json, graph_state):
    payload = case_coverage_payload(problem_json, graph_state)
    payload_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    prompt_lines = [
        "你是 proof critic verifier。",
        "請檢查這份證明是否忽略必要 case。",
        "你只能根據輸入中的 problem_json、nodes、inferences、proof_body 判斷。",
        "不要新增題目沒有的定義、條件、reference 或欄位。",
        "請判斷 assumptions、hidden_conditions、domain 或 goal 是否造成必須分 case。",
        "請判斷 proof_body 與 inferences 是否真的覆蓋所有必要 case。",
        "若沒有缺漏，請回傳 pass=true 且 issues=[]。",
        "若有缺漏，請回傳 pass=false 並在 issues 說明缺漏 case 與證據。",
        "請只輸出 JSON，格式如下：",
        '{"pass":true,"issues":[{"message":"...","evidence":"...","node_id":null,"inference_id":null,"severity":"medium"}]}',
        "輸入資料：",
        payload_text,
    ]
    return "\n".join(prompt_lines)


def _get_active_llm():
    from model_loader import ACTIVE_LLM
    return ACTIVE_LLM


def resolve_case_coverage_model(model_client=None):
    if model_client is not None:
        return model_client
    active_model = _get_active_llm()
    if active_model is None:
        return None
    if getattr(active_model, "backend", None) == "fallback":
        return None
    if not hasattr(active_model, "generate") and not hasattr(active_model, "check_case_coverage"):
        return None
    return active_model


def parse_case_coverage_result(raw_result):
    if isinstance(raw_result, dict):
        result = raw_result
    else:
        result = parse_json_from_text(str(raw_result))
    if not isinstance(result, dict):
        raise ValueError("case coverage critic must return a JSON object")
    issues = result.get("issues", [])
    if issues is None:
        issues = []
    if not isinstance(issues, list):
        raise ValueError("case coverage critic issues must be a list")
    result["issues"] = issues
    result["pass"] = bool(result.get("pass", len(issues) == 0))
    return result


def run_case_coverage_critic(problem_json, graph_state, model_client=None):
    critic_model = resolve_case_coverage_model(model_client)
    if critic_model is None:
        return {"pass": True, "issues": [], "skipped": "no_model"}
    payload = case_coverage_payload(problem_json, graph_state)
    if hasattr(critic_model, "check_case_coverage"):
        raw_result = critic_model.check_case_coverage(payload)
    else:
        prompt = prompt_case_coverage_critic(problem_json, graph_state)
        raw_result = critic_model.generate(prompt, max_new_tokens=700)
    return parse_case_coverage_result(raw_result)


def verify_case_coverage(problem_json, graph_state, model_client=None):
    errors = []
    try:
        critic_result = run_case_coverage_critic(problem_json, graph_state, model_client)
    except Exception as exc:
        errors.append(make_error("critic", None, None, "low", "Case coverage critic could not be parsed.", repr(exc), "Return valid JSON with pass and issues fields from the case critic model.", False))
        return errors
    if critic_result.get("pass", True):
        return errors
    issues = critic_result.get("issues", [])
    if not issues:
        issues = [{"message": "Case analysis may be missing.", "evidence": "The case coverage critic returned pass=false without detailed issues.", "node_id": None, "inference_id": None, "severity": "medium"}]
    for issue in issues:
        issue = issue if isinstance(issue, dict) else {"message": str(issue)}
        severity = issue.get("severity", "medium")
        if severity not in {"low", "medium", "high"}:
            severity = "medium"
        errors.append(make_error("critic", issue.get("node_id"), issue.get("inference_id"), severity, issue.get("message", "Case analysis may be missing."), issue.get("evidence", ""), "Add explicit case split nodes or proof steps covering every required case.", False))
    return errors


def verify_context_requirements(problem_json, graph_state):
    errors = []
    proof_text = json.dumps(graph_state, ensure_ascii=False).lower()

    for assumption in problem_json.get("assumptions", []):
        assumption_id = str(assumption.get("id", "")).lower() if isinstance(assumption, dict) else ""
        statement = str(assumption.get("statement", "")).lower() if isinstance(assumption, dict) else str(assumption).lower()
        if assumption_id and assumption_id in proof_text:
            continue
        if statement and normalize_math_text(statement) and normalize_math_text(statement) in normalize_math_text(proof_text):
            continue
        errors.append(make_error("critic", None, None, "medium", "Assumption may be unused.", f"assumption {assumption_id or statement} is not cited or reflected in proof.", "Cite the assumption in a source node, premise_nodes, or proof_body.", False))

    for hidden in problem_json.get("hidden_conditions", []):
        hidden_id = str(hidden.get("id", "")).lower() if isinstance(hidden, dict) else ""
        statement = str(hidden.get("statement", "")).lower() if isinstance(hidden, dict) else str(hidden).lower()
        keywords = [word for word in re.findall(r"[A-Za-z_]+|[一-鿿]+", statement) if len(word) >= 2]
        if hidden_id and hidden_id in proof_text:
            continue
        if keywords and any(keyword.lower() in proof_text for keyword in keywords[:4]):
            continue
        errors.append(make_error("critic", None, None, "medium", "Hidden condition may be unchecked.", f"hidden condition {hidden_id or statement} is not addressed in proof.", "Add proof steps or side_condition_nodes checking this hidden condition.", False))

    for symbol, constraint in (problem_json.get("domain", {}).items() if isinstance(problem_json.get("domain", {}), dict) else []):
        symbol_text = str(symbol).lower()
        constraint_text = str(constraint).lower()
        if symbol_text in proof_text and any(word in proof_text for word in re.findall(r"[A-Za-z_]+|[一-鿿]+", constraint_text)[:4]):
            continue
        errors.append(make_error("critic", None, None, "medium", "Domain constraint may be unchecked.", f"domain constraint for {symbol}: {constraint} is not clearly addressed.", "Mention or cite the domain constraint in source nodes, side_condition_nodes, or proof_body.", False))

    return errors


def theorem_applicability_payload(problem_json, proof_contract, graph_state, inference):
    nodes_by_id = node_map(graph_state)
    premise_nodes = [nodes_by_id[node_id] for node_id in inference.get("premise_nodes", []) if node_id in nodes_by_id]
    side_condition_nodes = [nodes_by_id[node_id] for node_id in inference.get("side_condition_nodes", []) if node_id in nodes_by_id]
    conclusion_node = nodes_by_id.get(inference.get("conclusion_node"))
    return {
        "problem_json": problem_json,
        "proof_contract": proof_contract,
        "inference": inference,
        "premise_nodes": premise_nodes,
        "side_condition_nodes": side_condition_nodes,
        "conclusion_node": conclusion_node,
    }


def prompt_theorem_applicability_critic(payload):
    payload_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    prompt_lines = [
        "你是 proof critic verifier。",
        "請檢查此 inference 使用的 theorem、definition 或 rule 是否滿足所有適用條件。",
        "你只能根據輸入中的 problem_json、proof_contract、inference、premise_nodes、side_condition_nodes、conclusion_node 判斷。",
        "不要新增題目沒有的 reference、node、欄位或宣告。",
        "不要用關鍵字是否出現作為唯一理由；請做語意判斷。",
        "請檢查每個 rule_ref 的適用條件是否已由 assumptions、domain、hidden_conditions、premise_nodes、side_condition_nodes 或 proof_body 支撐。",
        "如果缺少適用條件，請回傳 pass=false 並在 issues 說明 缺少哪個條件、影響哪個 rule_ref、以及證據。",
        "如果沒有缺漏，請回傳 pass=true 且 issues=[]。",
        "請只輸出 JSON，格式如下：",
        '{"pass":true,"issues":[{"message":"...","evidence":"...","rule_ref":"...","node_id":null,"inference_id":null,"severity":"high"}]}',
        "輸入資料：",
        payload_text,
    ]
    return "\n".join(prompt_lines)


def resolve_theorem_applicability_model(model_client=None):
    if model_client is not None:
        return model_client
    active_model = _get_active_llm()
    if active_model is None:
        return None
    if getattr(active_model, "backend", None) == "fallback":
        return None
    if not hasattr(active_model, "generate") and not hasattr(active_model, "check_theorem_applicability"):
        return None
    return active_model


def parse_theorem_applicability_result(raw_result):
    if isinstance(raw_result, dict):
        result = raw_result
    else:
        result = parse_json_from_text(str(raw_result))
    if not isinstance(result, dict):
        raise ValueError("theorem applicability critic must return a JSON object")
    issues = result.get("issues", [])
    if issues is None:
        issues = []
    if not isinstance(issues, list):
        raise ValueError("theorem applicability critic issues must be a list")
    result["issues"] = issues
    result["pass"] = bool(result.get("pass", len(issues) == 0))
    return result


def run_theorem_applicability_critic(problem_json, proof_contract, graph_state, inference, model_client=None):
    critic_model = resolve_theorem_applicability_model(model_client)
    if critic_model is None:
        return {"pass": True, "issues": [], "skipped": "no_model"}
    payload = theorem_applicability_payload(problem_json, proof_contract, graph_state, inference)
    if hasattr(critic_model, "check_theorem_applicability"):
        raw_result = critic_model.check_theorem_applicability(payload)
    else:
        prompt = prompt_theorem_applicability_critic(payload)
        raw_result = critic_model.generate(prompt, max_new_tokens=700)
    return parse_theorem_applicability_result(raw_result)


def verify_theorem_applicability(problem_json, proof_contract, graph_state, model_client=None):
    errors = []
    for inference in graph_state.get("inferences", []):
        inference_id = inference.get("id")
        conclusion_id = inference.get("conclusion_node")
        try:
            critic_result = run_theorem_applicability_critic(problem_json, proof_contract, graph_state, inference, model_client)
        except Exception as exc:
            errors.append(make_error("critic", conclusion_id, inference_id, "low", "Theorem applicability critic could not be parsed.", repr(exc), "Return valid JSON with pass and issues fields from the theorem applicability critic model.", False))
            continue
        if critic_result.get("pass", True):
            continue
        issues = critic_result.get("issues", [])
        if not issues:
            issues = [{"message": "Theorem applicability may be missing.", "evidence": "The theorem applicability critic returned pass=false without detailed issues.", "rule_ref": "", "node_id": conclusion_id, "inference_id": inference_id, "severity": "high"}]
        for issue in issues:
            issue = issue if isinstance(issue, dict) else {"message": str(issue)}
            severity = issue.get("severity", "high")
            if severity not in {"low", "medium", "high"}:
                severity = "high"
            rule_ref = issue.get("rule_ref", "")
            claim = f"Theorem applicability for {rule_ref}" if rule_ref else issue.get("message", "Theorem applicability may be missing.")
            evidence = issue.get("evidence", "")
            node_id = issue.get("node_id", conclusion_id)
            checked_inference_id = issue.get("inference_id", inference_id)
            errors.append(make_error("critic", node_id, checked_inference_id, severity, claim, evidence, "Add side_condition_nodes or proof_body steps showing every applicability condition for the cited theorem/definition/rule.", True))
    return errors


def verify_critic(problem_json, proof_contract, graph_state):
    errors = []
    errors += verify_case_coverage(problem_json, graph_state)
    errors += verify_context_requirements(problem_json, graph_state)
    errors += verify_theorem_applicability(problem_json, proof_contract, graph_state)
    return errors


# ── Aggregator ───────────────────────────────────────────────────────────────

def annotate_and_aggregate(problem_json, proof_contract, graph_state, errors):
    annotated = copy.deepcopy(graph_state)
    blocked_nodes = {error.get("node_id") for error in blocking_errors(errors) if error.get("node_id")}
    blocked_infs = {error.get("inference_id") for error in blocking_errors(errors) if error.get("inference_id")}
    verified_nodes, verified_infs = compute_inference_closure(problem_json, proof_contract, graph_state, errors)

    for node in annotated.get("nodes", []):
        node_id = node.get("id")
        if node_id in blocked_nodes:
            node["status"] = "failed"
        elif node_id in verified_nodes:
            node["status"] = "verified"
        else:
            node["status"] = "failed"

    for inf in annotated.get("inferences", []):
        inf_id = inf.get("id")
        if inf_id in blocked_infs:
            inf["status"] = "failed"
        elif inf_id in verified_infs:
            inf["status"] = "verified"
        else:
            inf["status"] = "failed"

    goal_node_id = annotated.get("goal_node_id")
    covered = set()
    for node in annotated.get("nodes", []):
        node_id = node.get("id")
        if node.get("status") == "verified":
            covered.update(node.get("covers_obligations", []))
            if node_id == goal_node_id:
                covered.update(ob.get("id", "") for ob in proof_contract.get("obligations", []) if isinstance(ob, dict))

    annotated["obligation_status"] = []
    for ob in proof_contract.get("obligations", []):
        item = dict(ob)
        item["status"] = "pass" if item.get("id") in covered else "fail"
        annotated["obligation_status"].append(item)

    annotated["errors"] = errors

    failed_obs = [o for o in annotated["obligation_status"] if o["status"] != "pass"]
    all_nodes_verified = all(node.get("status") == "verified" for node in annotated.get("nodes", []))
    all_inferences_verified = all(inf.get("status") == "verified" for inf in annotated.get("inferences", []))
    blocking_acceptance_errors = blocking_errors(errors)

    accepted = len(blocking_acceptance_errors) == 0 and len(failed_obs) == 0 and all_nodes_verified and all_inferences_verified

    failed_infs = blocked_infs | {inf.get("id") for inf in annotated.get("inferences", []) if inf.get("status") == "failed"}
    result = {"all_required_pass": accepted, "blocking_errors": blocking_acceptance_errors, "failed_nodes": sorted(blocked_nodes), "failed_inferences": sorted(failed_infs), "failed_obligations": failed_obs, "accepted_proof": annotated if accepted else None}
    return annotated, result


# ── Main entry point ─────────────────────────────────────────────────────────

def run_all_verifiers(problem_json, proof_contract, graph_state):
    errors = []
    errors += verify_json_schema("problem_json", problem_json, PROBLEM_JSON_SCHEMA)
    errors += verify_json_schema("proof_contract", proof_contract, PROOF_CONTRACT_SCHEMA)
    errors += verify_json_schema("proof_graph_state", graph_state, PROOF_GRAPH_STATE_SCHEMA)

    if not blocking_errors(errors):
        errors += verify_graph_structure(problem_json, proof_contract, graph_state)
        errors += verify_node_proofs(problem_json, proof_contract, graph_state)
        errors += verify_symbolic(problem_json, graph_state)
        errors += verify_critic(problem_json, proof_contract, graph_state)
        errors += verify_inferences(problem_json, proof_contract, graph_state)
        errors += verify_inference_closure(problem_json, proof_contract, graph_state, errors)

    errors = with_error_ids(errors)
    annotated, agg = annotate_and_aggregate(problem_json, proof_contract, graph_state, errors)
    return {"errors": errors, "annotated_graph_state": annotated, "aggregator": agg}
