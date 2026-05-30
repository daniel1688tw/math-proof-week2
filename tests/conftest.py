"""
Shared fixtures and helpers for the week2 pipeline test suite.

Run the full suite from the week2/ directory:
    .\\env\\python.exe -m pytest tests/ -v

Install pytest first if needed:
    .\\env\\Scripts\\pip.exe install pytest
"""
import sys
import copy
from pathlib import Path

# Add the week2 root to sys.path so all project modules are importable.
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class MockLLM:
    """Fake LLM (backend='hf') that returns a pre-baked sequence of strings.

    Passes the require_real_model() check in generators.py.
    After exhausting the response list, returns a fallback JSON stub.
    """
    backend = "hf"
    model_name = "mock-model"
    error = None

    def __init__(self, responses=None):
        self._responses = list(responses or [])
        self._idx = 0
        self.calls = []

    def generate(self, prompt, max_new_tokens=None, json_prefix=False):
        self.calls.append({"prompt_head": prompt[:80], "max_new_tokens": max_new_tokens})
        if self._idx < len(self._responses):
            response = self._responses[self._idx]
            self._idx += 1
            return response
        return '{"_fallback": true}'

    @property
    def call_count(self):
        return len(self.calls)


@pytest.fixture
def make_mock_llm():
    """Return the MockLLM class so tests can instantiate it with custom responses."""
    return MockLLM


@pytest.fixture(autouse=True)
def clear_gen_cache():
    """Clear the in-memory generator cache before and after every test."""
    import generators
    generators._gen_cache.clear()
    yield
    generators._gen_cache.clear()


# ── Shared valid fixture data ────────────────────────────────────────────────

_PROBLEM_JSON = {
    "problem_id": "test_chain",
    "raw_problem": "Prove d/dx sin(x^2) = 2*x*cos(x^2)",
    "goal": {
        "text": "The derivative of sin(x^2) equals 2*x*cos(x^2)",
        "symbolic": "d/dx sin(x**2) = 2*x*cos(x**2)",
    },
    "assumptions": [{"id": "A1", "statement": "x is a real number"}],
    "variables": [{"symbol": "x", "type": "real", "role": "variable"}],
    "domain": {"x": "all real numbers"},
    "technical_terms": ["derivative", "chain rule"],
    "hidden_conditions": [],
}

_PROOF_CONTRACT = {
    "goal": {
        "text": "Prove d/dx sin(x^2) = 2*x*cos(x^2)",
        "symbolic": "d/dx sin(x**2) = 2*x*cos(x**2)",
    },
    "obligations": [
        {"id": "O1", "description": "Apply chain rule to sin(x^2)", "status": "pending"},
        {"id": "O2", "description": "Show derivative equals 2*x*cos(x^2)", "status": "pending"},
    ],
    "allowed_references": ["chain_rule", "derivative_rule", "power_rule"],
    "forbidden_moves": ["assuming the result"],
}

# Minimal skeleton (no proof bodies yet).
_GRAPH_STATE = {
    "proof_id": "test_chain",
    "goal_node_id": "G1",
    "nodes": [
        {"id": "A1", "node_type": "assumption", "claim": "x is a real number", "status": "source"},
        {"id": "L1", "node_type": "lemma",      "claim": "d/dx x^2 = 2*x",              "status": "planned", "proof_body": {}},
        {"id": "G1", "node_type": "goal",       "claim": "d/dx sin(x^2) = 2*x*cos(x^2)", "status": "planned", "proof_body": {}},
    ],
    "inferences": [
        {"id": "I1", "premise_nodes": ["A1"],       "side_condition_nodes": [], "conclusion_node": "L1", "rule_refs": ["power_rule"],  "relation": "implies", "status": "planned"},
        {"id": "I2", "premise_nodes": ["A1", "L1"], "side_condition_nodes": [], "conclusion_node": "G1", "rule_refs": ["chain_rule"],  "relation": "implies", "status": "planned"},
    ],
}

# Graph with complete proof bodies — designed to pass all verifiers when critics are skipped.
# Last step of each node explicitly restates the node's claim so proof_concludes_node_claim passes.
_PROVEN_GRAPH_STATE = {
    "proof_id": "test_chain",
    "goal_node_id": "G1",
    "nodes": [
        {"id": "A1", "node_type": "assumption", "claim": "x is a real number", "status": "source"},
        {
            "id": "L1", "node_type": "lemma", "claim": "d/dx x^2 = 2*x", "status": "proven",
            "proof_body": {"format": "structured_derivation", "steps": [
                {"statement": "By power rule, d/dx x^2 = 2*x", "reason": "power_rule", "refs": []},
            ]},
        },
        {
            "id": "G1", "node_type": "goal",
            "claim": "d/dx sin(x^2) = 2*x*cos(x^2)", "status": "proven",
            "covers_obligations": ["O1", "O2"],
            "proof_body": {"format": "structured_derivation", "steps": [
                {"statement": "Let u = x^2, so f(u) = sin(u)", "reason": "substitution", "refs": []},
                {"statement": "Therefore, d/dx sin(x^2) = 2*x*cos(x^2)", "reason": "chain_rule", "refs": ["L1"]},
            ]},
        },
    ],
    "inferences": [
        {"id": "I1", "premise_nodes": ["A1"],       "side_condition_nodes": [], "conclusion_node": "L1", "rule_refs": ["power_rule"],  "relation": "implies", "status": "planned"},
        {"id": "I2", "premise_nodes": ["A1", "L1"], "side_condition_nodes": [], "conclusion_node": "G1", "rule_refs": ["chain_rule"],  "relation": "implies", "status": "planned"},
    ],
}


@pytest.fixture
def problem_json():
    return copy.deepcopy(_PROBLEM_JSON)


@pytest.fixture
def proof_contract():
    return copy.deepcopy(_PROOF_CONTRACT)


@pytest.fixture
def graph_state():
    return copy.deepcopy(_GRAPH_STATE)


@pytest.fixture
def proven_graph_state():
    return copy.deepcopy(_PROVEN_GRAPH_STATE)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "livemodel: requires a real loaded HF model (ACTIVE_LLM with backend='hf').",
    )


@pytest.fixture
def require_live_model():
    """Skip a test if no real HF model is loaded into ACTIVE_LLM."""
    from model_loader import ACTIVE_LLM
    if ACTIVE_LLM is None or getattr(ACTIVE_LLM, "backend", None) != "hf":
        pytest.skip("Live HF model not loaded — run with LOAD_HF_MODEL=True in config.py")
    return ACTIVE_LLM
