PROBLEM_JSON_SCHEMA = {
    "type": "object",
    "required": ["problem_id", "raw_problem", "goal"],
    "properties": {
        "problem_id": {"type": "string"},
        "raw_problem": {"type": "string"},
        "goal": {"type": "object", "required": ["text", "symbolic"], "properties": {"text": {"type": "string"}, "symbolic": {"type": "string"}}},
        "assumptions": {"type": "array"},
        "variables": {"type": "array"},
        "domain": {"type": "object"},
        "technical_terms": {"type": "array", "items": {"type": "string"}},
        "hidden_conditions": {"type": "array"},
    },
}

PROOF_CONTRACT_SCHEMA = {
    "type": "object",
    "required": ["goal", "obligations", "allowed_references"],
    "properties": {
        "goal": {"type": "object"},
        "assumptions": {"type": "array"},
        "allowed_references": {"type": "array", "items": {"type": "string"}},
        "allowed_theorems": {"type": "array", "items": {"type": "string"}},
        "forbidden_moves": {"type": "array", "items": {"type": "string"}},
        "obligations": {"type": "array", "items": {"type": "object", "required": ["id", "description", "status"], "properties": {"id": {"type": "string"}, "description": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "pass", "fail"]}}}},
        "acceptance_rubric": {"type": "array", "items": {"type": "string"}},
    },
}

PROOF_GRAPH_STATE_SCHEMA = {
    "type": "object",
    "required": ["proof_id", "nodes", "inferences"],
    "properties": {
        "proof_id": {"type": "string"},
        "based_on_graph_id": {"type": "string"},
        "current_graph_version": {"type": "integer"},
        "goal_node_id": {"type": "string"},
        "nodes": {"type": "array", "items": {"type": "object", "required": ["id", "node_type", "claim", "status"], "properties": {"id": {"type": "string"}, "node_type": {"type": "string"}, "claim": {"type": "string"}, "claim_formal": {"type": "string"}, "proof_flow": {"type": "array", "items": {"type": "string"}}, "proof_body": {"type": "object"}, "planned_rule_refs": {"type": "array", "items": {"type": "string"}}, "covers_obligations": {"type": "array", "items": {"type": "string"}}, "errors": {"type": "array"}, "status": {"type": "string", "enum": ["planned", "proven", "verified", "failed", "patched", "source"]}}}},
        "inferences": {"type": "array", "items": {"type": "object", "required": ["id", "premise_nodes", "conclusion_node", "rule_refs", "side_condition_nodes", "relation", "status"], "properties": {"id": {"type": "string"}, "premise_nodes": {"type": "array", "items": {"type": "string"}}, "conclusion_node": {"type": "string"}, "rule_refs": {"type": "array", "items": {"type": "string"}}, "side_condition_nodes": {"type": "array", "items": {"type": "string"}}, "instantiation": {"type": "object"}, "relation": {"type": "string"}, "status": {"type": "string", "enum": ["planned", "proven", "verified", "failed", "patched"]}, "verifier_notes": {"type": "array"}}}},
        "errors": {"type": "array"},
        "obligation_status": {"type": "array"},
        "graph_patches": {"type": "array"},
    },
    "additionalProperties": True,
}
