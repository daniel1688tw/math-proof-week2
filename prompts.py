from benchmark import THEOREM_LIBRARY
from json_utils import compact_json


def prompt_problem_json(raw_problem):
    _ex1 = (
        '{"problem_id":"exp_derivative","raw_problem":"Prove d/dx exp(x) = exp(x)",'
        '"goal":{"text":"The derivative of exp(x) equals exp(x)","symbolic":"Eq(Derivative(exp(x),x),exp(x))"},'
        '"assumptions":[{"id":"A1","statement":"x is a real number"}],'
        '"variables":[{"symbol":"x","type":"real","role":"independent variable"}],'
        '"domain":{"x":"all real numbers"},"technical_terms":["derivative","exponential"],"hidden_conditions":[]}'
    )
    _ex2 = (
        '{"problem_id":"product_rule","raw_problem":"Prove: d/dx[f(x)g(x)] = f\'(x)g(x) + f(x)g\'(x)",'
        '"goal":{"text":"d/dx[f*g] = f\'*g + f*g\'","symbolic":"Eq(Derivative(f(x)*g(x),x),Derivative(f(x),x)*g(x)+f(x)*Derivative(g(x),x))"},'
        '"assumptions":[{"id":"A1","statement":"f is differentiable at x"},{"id":"A2","statement":"g is differentiable at x"}],'
        '"variables":[{"symbol":"x","type":"real","role":"independent variable"},{"symbol":"f","type":"function","role":"first factor"},{"symbol":"g","type":"function","role":"second factor"}],'
        '"domain":{"x":"all real numbers"},"technical_terms":["derivative","product rule","differentiability"],"hidden_conditions":[]}'
    )
    return f"""Output ONLY a JSON object, no explanation or reasoning text.
Required fields: problem_id(string slug), raw_problem(string), goal(object with text and symbolic keys),
assumptions(array of {{id,statement}}), variables(array of {{symbol,type,role}}),
domain(object), technical_terms(array), hidden_conditions(array).

Example 1: {_ex1}

Example 2: {_ex2}

Problem: {raw_problem}
JSON:"""


def prompt_proof_contract(problem_json):
    _ex = (
        '{"goal":{"text":"The derivative of exp(x) equals exp(x)","symbolic":"Eq(Derivative(exp(x),x),exp(x))"},'
        '"assumptions":[{"id":"A1","statement":"x is a real number"}],'
        '"allowed_references":["limit_definition_of_derivative","exponential_series_definition"],'
        '"forbidden_moves":["assuming the result","circular reasoning"],'
        '"obligations":[{"id":"O1","description":"Show limit definition gives exp(x)","status":"pending"}],'
        '"acceptance_rubric":["Must use limit definition or series","Must not assume d/dx exp(x)=exp(x)"]}'
    )
    clean = {k: v for k, v in problem_json.items() if not k.startswith("_")}
    return f"""You are a proof contract builder for calculus proofs. Return ONLY valid JSON.
Choose allowed_references from this theorem library: {THEOREM_LIBRARY}
Select only the theorems/rules directly relevant to THIS problem.
Required fields:
  goal(object with text and symbolic), assumptions(array),
  allowed_references(array of strings from the library above),
  forbidden_moves(array of strings describing what is NOT allowed),
  obligations(array of {{id, description, status:"pending"}}),
  acceptance_rubric(array of strings describing what a correct proof must show).

Example output: {_ex}

problem_json={compact_json(clean)}
JSON:"""


def prompt_graph_skeleton(problem_json, proof_contract):
    return f"""You are a calculus proof graph planner. Return ONLY valid JSON for proof_graph_state.
Build a directed proof graph where assumption/source nodes flow via inferences to the goal node.
Required top-level keys: proof_id(string), based_on_graph_id(string), current_graph_version(1),
  goal_node_id(string), nodes(array), inferences(array), errors([]), obligation_status([]), graph_patches([]).
Node fields: id(string), node_type(assumption|goal|lemma|subclaim|side_condition|definition_expansion|allowed_reference), claim(string), status("source" for assumption/allowed_reference nodes, "planned" for all others).
Inference fields: id(string), premise_nodes(array of node ids), conclusion_node(string), rule_refs(array from proof_contract.allowed_references), side_condition_nodes([]), relation("implies"), status("planned").
Guidelines:
- Create intermediate lemma/subclaim nodes for each non-trivial proof step.
- A complete proof graph typically has 3–7 nodes (sources + intermediate + goal).
- Every non-source node must be the conclusion_node of at least one inference.
- The goal node must be reachable from assumption/source nodes.
problem_json={compact_json(problem_json)}
proof_contract={compact_json(proof_contract)}
JSON:"""


def prompt_node_proof(problem_json, proof_contract, graph_state, node):
    nodes_by_id = {n["id"]: n for n in graph_state.get("nodes", [])}
    node_id = node.get("id", "")
    parent_ids = set()
    for inf in graph_state.get("inferences", []):
        if inf.get("conclusion_node") == node_id:
            parent_ids.update(inf.get("premise_nodes", []))
            parent_ids.update(inf.get("side_condition_nodes", []))
    parent_nodes = [nodes_by_id[pid] for pid in parent_ids if pid in nodes_by_id]
    return f"""You are a calculus proof writer. Return ONLY valid JSON for proof_body.
Write a step-by-step derivation that proves the node claim from its parent nodes.
Format: {{"format":"structured_derivation","steps":[{{"statement":"...","reason":"...","refs":["..."]}}]}}
Rules:
- Each step must have statement(the math fact), reason(why it holds), refs(theorem/rule names used).
- The final step statement must match or directly conclude the node claim.
- Use refs from proof_contract.allowed_references only.
- Write at least 2 steps. Be mathematically precise.
problem_json={compact_json(problem_json)}
proof_contract={compact_json(proof_contract)}
node={compact_json(node)}
parent_nodes={compact_json(parent_nodes)}
JSON:"""


def prompt_repair_json(bad_text, error_message):
    return f"""The following output is not valid JSON. Fix it and return ONLY the corrected JSON.
Do not explain. Do not add text outside the JSON object.
Error: {error_message}
Bad output:
{bad_text}
JSON:"""


# ── Compact (short-prompt) versions ────────────────────────────────────────────

def prompt_problem_json_compact(raw_problem):
    return f"""JSON only. No explanation.
Fields: problem_id(slug), raw_problem, goal(text,symbolic), assumptions([{{id,statement}}]), variables([{{symbol,type,role}}]), domain, technical_terms, hidden_conditions.
Problem: {raw_problem}
JSON:"""


def prompt_proof_contract_compact(problem_json):
    relevant = [t for t in THEOREM_LIBRARY if any(
        term.lower() in t.lower() for term in problem_json.get("technical_terms", [])
    )] or THEOREM_LIBRARY[:8]
    summary = compact_json({
        "problem_id": problem_json.get("problem_id"),
        "goal": problem_json.get("goal"),
        "technical_terms": problem_json.get("technical_terms", []),
    })
    return f"""JSON only. Build proof_contract.
Fields: goal, assumptions, allowed_references(choose from: {relevant}), forbidden_moves, obligations([{{id,description,status:"pending"}}]), acceptance_rubric.
problem={summary}
JSON:"""


def prompt_graph_skeleton_compact(problem_json, proof_contract):
    summary = compact_json({
        "goal": problem_json.get("goal"),
        "allowed_references": proof_contract.get("allowed_references", [])[:6],
        "obligations": [o["id"] for o in proof_contract.get("obligations", [])],
    })
    return f"""JSON only. Build proof_graph_state (DAG from assumptions to goal).
Fields: proof_id, based_on_graph_id, current_graph_version(1), goal_node_id, nodes, inferences, errors([]), obligation_status([]), graph_patches([]).
Node: id, node_type(assumption|goal|subclaim|lemma), claim, status("source" or "planned").
Inference: id, premise_nodes, conclusion_node, rule_refs, side_condition_nodes([]), relation("implies"), status("planned").
context={summary}
JSON:"""


def prompt_node_proof_compact(problem_json, proof_contract, graph_state, node):
    return f"""JSON only. Write proof_body for this node claim.
Format: {{"format":"structured_derivation","steps":[{{"statement":"...","reason":"...","refs":["..."]}}]}}
At least 2 steps. Final step must establish the claim.
claim: {node.get("claim")}
refs_allowed: {proof_contract.get("allowed_references", [])[:6]}
JSON:"""
