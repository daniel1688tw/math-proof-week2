from config import MAX_NEW_TOKENS, MAX_REPAIR_ATTEMPTS
from schemas import PROBLEM_JSON_SCHEMA, PROOF_CONTRACT_SCHEMA, PROOF_GRAPH_STATE_SCHEMA
from json_utils import parse_json_from_text, validate_or_raise
from prompts import (
    prompt_problem_json, prompt_proof_contract,
    prompt_graph_skeleton, prompt_node_proof, prompt_repair_json,
    prompt_problem_json_compact, prompt_proof_contract_compact,
    prompt_graph_skeleton_compact, prompt_node_proof_compact,
    THEOREM_LIBRARY,
)
from model_loader import ACTIVE_LLM


def require_real_model():
    active_model = ACTIVE_LLM
    if active_model is None:
        raise RuntimeError("ACTIVE_LLM is not initialized.")
    if getattr(active_model, "backend", None) != "hf":
        raise RuntimeError(
            f"ACTIVE_LLM is not a real HF model: backend={getattr(active_model, 'backend', None)}, "
            f"error={getattr(active_model, 'error', None)}"
        )
    if not hasattr(active_model, "generate"):
        raise RuntimeError("ACTIVE_LLM does not provide generate().")
    return active_model


def generate_json_until_valid(prompt, schema, name, max_new_tokens=MAX_NEW_TOKENS, compact_prompt=None, normalizer=None):
    model = require_real_model()
    attempt = 0
    current_prompt = prompt
    compact_tried = False

    while True:
        attempt += 1
        try:
            raw = model.generate(current_prompt, max_new_tokens=max_new_tokens, json_prefix=True)
        except RuntimeError as gen_err:
            if "prompt_too_long" in str(gen_err) and compact_prompt and not compact_tried:
                print(f"  [{name}] prompt too long — retrying with compact prompt")
                current_prompt = compact_prompt
                compact_tried = True
                attempt -= 1
                continue
            raise RuntimeError(f"{name} generation error: {gen_err}") from gen_err

        print(f"  [{name}] raw[:600]: {raw[:600]!r}")
        try:
            data = parse_json_from_text(raw)
            if normalizer:
                data = normalizer(data)
            validate_or_raise(name, data, schema)
            data["_generation_source"] = model.backend
            data["_generation_attempts"] = attempt
            return data
        except Exception as exc:
            last_error = repr(exc)
            print(f"  [{name}] attempt {attempt} failed: {last_error[:150]}")
            # On first failure, try compact prompt before repair (if not already tried)
            if attempt == 1 and compact_prompt and not compact_tried:
                print(f"  [{name}] attempt 1 failed — retrying with compact prompt")
                current_prompt = compact_prompt
                compact_tried = True
                attempt -= 1
                continue
            if attempt >= MAX_REPAIR_ATTEMPTS:
                raise RuntimeError(
                    f"{name}: exceeded {MAX_REPAIR_ATTEMPTS} repair attempts. Last error: {last_error}"
                )
            # Extract partial JSON from CoT output to avoid sending verbose reasoning to repair
            try:
                from json_utils import extract_json_object
                repair_input = extract_json_object(raw)
            except Exception:
                repair_input = raw
            current_prompt = prompt_repair_json(repair_input, last_error)


_gen_cache = {}


def _normalize_problem_json(data):
    """Convert string items in assumptions/variables/hidden_conditions to required object format."""
    data = _strip_dict_keys(data)
    goal = data.get("goal")
    if isinstance(goal, str):
        data["goal"] = {"text": goal, "symbolic": goal}
    assumptions = data.get("assumptions", [])
    if assumptions and isinstance(assumptions[0], str):
        data["assumptions"] = [{"id": f"A{i+1}", "statement": a} for i, a in enumerate(assumptions)]
    variables = data.get("variables", [])
    if variables and isinstance(variables[0], str):
        data["variables"] = [{"symbol": v, "type": "real", "role": "variable"} for v in variables]
    hidden = data.get("hidden_conditions", [])
    if hidden and isinstance(hidden[0], str):
        data["hidden_conditions"] = [{"id": f"H{i+1}", "statement": h} for i, h in enumerate(hidden)]
    return data


def _normalize_proof_contract(data):
    """Unwrap nested wrapper, fix obligations format, ensure required fields exist."""
    data = _strip_dict_keys(data)
    for wrapper in ["problem", "proof_contract", "contract"]:
        if wrapper in data and isinstance(data[wrapper], dict):
            nested = data[wrapper]
            if any(k in nested for k in ["goal", "obligations", "allowed_references"]):
                for k, v in nested.items():
                    if k not in data:
                        data[k] = v
                del data[wrapper]
                break
    # Ensure goal exists at top level (may have been nested)
    if "goal" not in data:
        for wrapper in ["problem", "proof_contract", "contract"]:
            if wrapper in data and isinstance(data[wrapper], dict):
                nested = data[wrapper]
                for k, v in nested.items():
                    if k not in data:
                        data[k] = v
                del data[wrapper]
                break
    # obligations: dict → list
    obligations = data.get("obligations")
    if isinstance(obligations, dict):
        obligations = [obligations]
        data["obligations"] = obligations
    # Fix obligations items: ensure id, description, status
    if isinstance(obligations, list):
        for i, ob in enumerate(obligations):
            if not isinstance(ob, dict):
                obligations[i] = {"id": f"O{i+1}", "description": str(ob), "status": "pending"}
                continue
            if "id" not in ob:
                ob["id"] = f"O{i+1}"
            if "description" not in ob:
                ob["description"] = ob.get("text", ob.get("statement", f"obligation {i+1}"))
            if "status" not in ob:
                ob["status"] = "pending"
    # Ensure obligations exists
    if not data.get("obligations"):
        data["obligations"] = [{"id": "O1", "description": "Prove the stated goal", "status": "pending"}]
    # Ensure allowed_references exists (also handle "allowed references" with space from model output,
    # and the case where the model wraps the contract body inside a "fields" key).
    if not data.get("allowed_references"):
        fields = data.get("fields") if isinstance(data.get("fields"), dict) else {}
        data["allowed_references"] = (
            data.get("allowed references")          # key with space
            or data.get("allowed_theorems")
            or fields.get("allowed_references")     # nested under "fields"
            or fields.get("allowed_theorems")
            or []
        )
    return data


def _strip_dict_keys(data):
    """Recursively strip leading/trailing whitespace from all dict keys."""
    if isinstance(data, dict):
        return {k.strip(): _strip_dict_keys(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_strip_dict_keys(item) for item in data]
    return data


def _normalize_graph_state(data):
    """Fix graph state: strip status spaces, extract inferences from nodes, add required fields."""
    data = _strip_dict_keys(data)

    # Ensure proof_id exists
    if "proof_id" not in data:
        data["proof_id"] = data.get("id", "generated_proof")

    # Separate inference-like objects mixed into nodes array
    raw_nodes = data.get("nodes", [])
    real_nodes, extracted_infs = [], []
    for item in raw_nodes:
        if not isinstance(item, dict):
            continue
        if "premise_nodes" in item or "conclusion_node" in item:
            extracted_infs.append(item)
        else:
            real_nodes.append(item)
    data["nodes"] = real_nodes
    if not data.get("inferences"):
        data["inferences"] = extracted_infs
    if "inferences" not in data:
        data["inferences"] = []

    # Detect when the LLM returned a single node object instead of a graph_state.
    # Symptoms: top-level has node_type (node field) but nodes array is empty.
    if data.get("node_type") and not data.get("nodes"):
        raise ValueError(
            f"LLM returned a node object (node_type={data.get('node_type')!r}) "
            "instead of a proof_graph_state; retrying"
        )

    # Strip status spaces in nodes
    for node in data["nodes"]:
        if isinstance(node.get("status"), str):
            node["status"] = node["status"].strip()
        if isinstance(node.get("node_type"), str):
            node["node_type"] = node["node_type"].strip()

    # Fix inference required fields and strip status spaces
    for i, inf in enumerate(data["inferences"]):
        if not isinstance(inf, dict):
            data["inferences"][i] = {}
            inf = data["inferences"][i]
        if "id" not in inf:
            inf["id"] = f"I{i+1}"
        if "premise_nodes" not in inf:
            inf["premise_nodes"] = []
        if "side_condition_nodes" not in inf:
            inf["side_condition_nodes"] = []
        if "rule_refs" not in inf:
            inf["rule_refs"] = []
        if "conclusion_node" not in inf:
            inf["conclusion_node"] = ""
        if "relation" not in inf:
            inf["relation"] = "implies"
        if "status" not in inf:
            inf["status"] = "planned"
        elif isinstance(inf["status"], str):
            inf["status"] = inf["status"].strip()

    if not data.get("nodes"):
        raise ValueError("proof_graph_state has empty nodes array; retrying")

    # Remove dangling inference references to nodes that don't exist in the graph.
    # The LLM sometimes lists side_condition_nodes or premise_nodes it never created.
    node_ids = {n.get("id") for n in data["nodes"]}
    for inf in data["inferences"]:
        inf["premise_nodes"] = [p for p in inf.get("premise_nodes", []) if p in node_ids]
        inf["side_condition_nodes"] = [s for s in inf.get("side_condition_nodes", []) if s in node_ids]
        if inf.get("conclusion_node") not in node_ids:
            goal_id = data.get("goal_node_id")
            if goal_id and goal_id in node_ids:
                inf["conclusion_node"] = goal_id

    # Remove inferences where conclusion_node appears in its own dependencies (self-loop → cycle).
    clean_inferences = []
    for inf in data["inferences"]:
        conclusion = inf.get("conclusion_node", "")
        deps = set(inf.get("premise_nodes", [])) | set(inf.get("side_condition_nodes", []))
        if conclusion and conclusion in deps:
            inf["side_condition_nodes"] = [s for s in inf.get("side_condition_nodes", []) if s != conclusion]
            inf["premise_nodes"] = [p for p in inf.get("premise_nodes", []) if p != conclusion]
        clean_inferences.append(inf)
    data["inferences"] = clean_inferences

    return data


_KIND_SYMBOLIC = {
    "intermediate_value_theorem": "Eq(f(c), N)",
    "mean_value_theorem": "Eq(Derivative(f(x), x).subs(x, c), (f(b) - f(a)) / (b - a))",
    "chain_rule": "Eq(Derivative(f(g(x)), x), Derivative(f(u), u).subs(u, g(x)) * Derivative(g(x), x))",
}


def _make_fallback_problem_json(raw_problem, hint=None):
    """Minimal valid problem_json built from raw_problem string when LLM fails."""
    hint = hint or {}
    goal_text = hint.get("expected", raw_problem)
    # Prefer a known sympy-parseable expression over the English goal_symbolic
    goal_symbolic = _KIND_SYMBOLIC.get(hint.get("kind", ""), hint.get("goal_symbolic", goal_text))
    # Build variables from hint interval and expr
    variables = []
    for sym in hint.get("interval", []):
        variables.append({"symbol": str(sym), "type": "real", "role": "interval_endpoint"})
    expr = hint.get("expr", "")
    if expr and expr not in {v["symbol"] for v in variables}:
        variables.append({"symbol": str(expr), "type": "function", "role": "function"})
    return {
        "problem_id": hint.get("problem_id", "fallback_problem"),
        "raw_problem": raw_problem,
        "goal": {"text": goal_text, "symbolic": goal_symbolic},
        "assumptions": [],
        "variables": variables,
        "hidden_conditions": [],
        "technical_terms": [],
        "_generation_source": "fallback",
        "_generation_attempts": 0,
    }


def generate_problem_json(raw_problem, hint=None):
    if raw_problem not in _gen_cache:
        try:
            result = generate_json_until_valid(
                prompt_problem_json(raw_problem),
                PROBLEM_JSON_SCHEMA,
                "problem_json",
                compact_prompt=prompt_problem_json_compact(raw_problem),
            )
            result = _normalize_problem_json(result)
        except RuntimeError as exc:
            print(f"  [problem_json] all LLM attempts failed ({exc}); using fallback")
            result = _make_fallback_problem_json(raw_problem, hint)
        _gen_cache[raw_problem] = result
    return _gen_cache[raw_problem]


def generate_proof_contract(problem_json):
    cache_key = f"pc:{problem_json.get('problem_id', problem_json.get('raw_problem', '')[:30])}"
    if cache_key not in _gen_cache:
        result = generate_json_until_valid(
            prompt_proof_contract(problem_json),
            PROOF_CONTRACT_SCHEMA,
            "proof_contract",
            compact_prompt=prompt_proof_contract_compact(problem_json),
            normalizer=_normalize_proof_contract,
        )
        _gen_cache[cache_key] = result
    return _gen_cache[cache_key]


def _make_fallback_graph_state(problem_json, proof_contract):
    """Minimal valid graph state built deterministically from problem_json."""
    assumptions = problem_json.get("assumptions", [])
    nodes = []
    for a in assumptions:
        aid = a.get("id", f"A{len(nodes)+1}") if isinstance(a, dict) else f"A{len(nodes)+1}"
        stmt = a.get("statement", str(a)) if isinstance(a, dict) else str(a)
        nodes.append({"id": aid, "node_type": "assumption", "claim": stmt, "status": "source"})
    goal = problem_json.get("goal", {})
    goal_text = goal.get("text", "Prove the goal") if isinstance(goal, dict) else str(goal)
    nodes.append({"id": "G1", "node_type": "goal", "claim": goal_text, "status": "planned"})
    premise_ids = [n["id"] for n in nodes if n["node_type"] == "assumption"]
    # Build rule_refs: prefer proof_contract's allowed_references; fall back to
    # theorems in THEOREM_LIBRARY that match the problem's technical_terms.
    refs = proof_contract.get("allowed_references", [])
    if not refs:
        terms = problem_json.get("technical_terms", [])
        refs = [t for t in THEOREM_LIBRARY
                if any(term.lower() in t.lower() for term in terms)][:4]
    inferences = [{
        "id": "I1", "premise_nodes": premise_ids, "conclusion_node": "G1",
        "rule_refs": refs[:2] if refs else [],
        "side_condition_nodes": [], "relation": "implies", "status": "planned",
    }]
    return {
        "proof_id": problem_json.get("problem_id", "fallback_proof"),
        "based_on_graph_id": "fallback",
        "current_graph_version": 1,
        "goal_node_id": "G1",
        "nodes": nodes,
        "inferences": inferences,
        "errors": [],
        "obligation_status": [],
        "graph_patches": [],
        "_generation_source": "fallback",
        "_generation_attempts": 0,
    }


def generate_graph_skeleton(problem_json, proof_contract):
    cache_key = f"gs:{problem_json.get('problem_id', problem_json.get('raw_problem', '')[:30])}"
    if cache_key not in _gen_cache:
        try:
            result = generate_json_until_valid(
                prompt_graph_skeleton(problem_json, proof_contract),
                PROOF_GRAPH_STATE_SCHEMA,
                "proof_graph_state",
                max_new_tokens=3000,
                compact_prompt=prompt_graph_skeleton_compact(problem_json, proof_contract),
                normalizer=_normalize_graph_state,
            )
        except RuntimeError as exc:
            print(f"  [graph_skeleton] all LLM attempts failed ({exc}); using deterministic fallback")
            result = _make_fallback_graph_state(problem_json, proof_contract)
        _gen_cache[cache_key] = result
    return _gen_cache[cache_key]


def generate_node_proof(problem_json, proof_contract, graph_state, node):
    model = require_real_model()
    attempt = 0
    compact_tried = False
    current_prompt = prompt_node_proof(problem_json, proof_contract, graph_state, node)

    while True:
        attempt += 1
        try:
            raw = model.generate(current_prompt, max_new_tokens=1024, json_prefix=True)
        except RuntimeError as gen_err:
            if "prompt_too_long" in str(gen_err) and not compact_tried:
                print(f"  [node_proof {node.get('id')}] prompt too long — retrying with compact prompt")
                current_prompt = prompt_node_proof_compact(problem_json, proof_contract, graph_state, node)
                compact_tried = True
                attempt -= 1
                continue
            raise RuntimeError(f"node_proof {node.get('id')} generation error: {gen_err}") from gen_err

        print(f"  [node_proof {node.get('id')}] raw[:600]: {raw[:600]!r}")
        try:
            proof_body = parse_json_from_text(raw)
            if not isinstance(proof_body, dict) or not proof_body.get("steps"):
                raise ValueError("proof_body has no steps")
            proof_body["_generation_source"] = model.backend
            proof_body["_generation_attempts"] = attempt
            return proof_body
        except Exception as exc:
            last_error = repr(exc)
            print(f"  [node_proof {node.get('id')}] attempt {attempt} failed: {last_error[:150]}")
            if attempt >= MAX_REPAIR_ATTEMPTS:
                raise RuntimeError(
                    f"node_proof {node.get('id')}: exceeded {MAX_REPAIR_ATTEMPTS} repair attempts. "
                    f"Last error: {last_error}"
                )
            try:
                from json_utils import extract_json_object
                repair_input = extract_json_object(raw)
            except Exception:
                repair_input = raw
            current_prompt = prompt_repair_json(repair_input, last_error)
