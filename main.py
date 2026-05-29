import json
from pathlib import Path

from config import ARTIFACT_DIR, REQUIRE_HF_MODEL_FOR_TESTS
from benchmark import BENCHMARK_PROBLEMS
from model_loader import ACTIVE_LLM
from schemas import PROBLEM_JSON_SCHEMA, PROOF_CONTRACT_SCHEMA, PROOF_GRAPH_STATE_SCHEMA
from json_utils import validate_or_raise
from generators import generate_problem_json, generate_proof_contract, generate_graph_skeleton
from verifier_utils import is_source_node
from graph_planner import graph_planner, graph_prover
from langgraph_nodes import WEEK2_APP

print("Week 2 environment ready.")
print("MODEL_NAME:", ACTIVE_LLM.model_name)
print("ACTIVE_LLM.backend:", ACTIVE_LLM.backend)

# ── Demo run ─────────────────────────────────────────────────────────────────

demo_problem = BENCHMARK_PROBLEMS[0]["raw_problem"]
try:
    demo_result = WEEK2_APP.invoke({"raw_problem": demo_problem, "trace": []})
    print("accepted:", demo_result["accepted"])
    print("error_count:", len(demo_result.get("current_errors", [])))
    print("trace:", json.dumps(demo_result["trace"], ensure_ascii=False, indent=2))
    print("problem_json source:", demo_result["problem_json"].get("_generation_source"))
    print("contract source:", demo_result["proof_contract"].get("_generation_source"))
except Exception as exc:
    print(f"Demo failed (continuing to tests): {exc}")
    demo_result = {
        "accepted": False, "current_errors": [], "trace": [],
        "problem_json": {"_generation_source": "error"},
        "proof_contract": {"_generation_source": "error"},
        "proof_graph_state": {}, "aggregator_result": {}, "error": repr(exc),
    }

# ── Tests ─────────────────────────────────────────────────────────────────────

def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_model_loaded_or_declared():
    if REQUIRE_HF_MODEL_FOR_TESTS:
        assert_true(ACTIVE_LLM.backend == "hf", f"Expected hf backend, got {ACTIVE_LLM.backend}: {ACTIVE_LLM.error}")
    else:
        assert_true(ACTIVE_LLM.backend in {"hf", "fallback"}, "Backend should be hf or fallback.")
    return f"test_model_loaded_or_declared passed with backend={ACTIVE_LLM.backend}"


def test_problem_and_contract_generation():
    pass_count = 0
    for item in BENCHMARK_PROBLEMS:
        try:
            problem_json = generate_problem_json(item["raw_problem"])
            proof_contract = generate_proof_contract(problem_json)
            validate_or_raise("problem_json", problem_json, PROBLEM_JSON_SCHEMA)
            validate_or_raise("proof_contract", proof_contract, PROOF_CONTRACT_SCHEMA)
            pass_count += 1
        except Exception as exc:
            print(f"Problem/contract test failed for {item['problem_id']}: {exc}")
    assert_true(pass_count >= len(BENCHMARK_PROBLEMS) - 1, f"Expected at least {len(BENCHMARK_PROBLEMS)-1} valid pairs, got {pass_count}/{len(BENCHMARK_PROBLEMS)}")
    return f"test_problem_and_contract_generation passed with {pass_count}/{len(BENCHMARK_PROBLEMS)}"


def test_graph_generation_schema():
    pass_count = 0
    for item in BENCHMARK_PROBLEMS:
        try:
            problem_json = generate_problem_json(item["raw_problem"])
            proof_contract = generate_proof_contract(problem_json)
            graph_state = generate_graph_skeleton(problem_json, proof_contract)
            validate_or_raise("proof_graph_state", graph_state, PROOF_GRAPH_STATE_SCHEMA)
            pass_count += 1
        except Exception as exc:
            print(f"Schema test failed for {item['problem_id']}: {exc}")
    assert_true(pass_count >= len(BENCHMARK_PROBLEMS) - 1, f"Expected at least {len(BENCHMARK_PROBLEMS)-1} schema-valid graphs, got {pass_count}/{len(BENCHMARK_PROBLEMS)}")
    return f"test_graph_generation_schema passed with {pass_count}/{len(BENCHMARK_PROBLEMS)}"


def test_node_proof_generation():
    item = BENCHMARK_PROBLEMS[1]
    problem_json, proof_contract, graph_state = graph_planner(item["raw_problem"])
    graph_state = graph_prover(problem_json, proof_contract, graph_state)
    required_nodes = [node for node in graph_state["nodes"] if not is_source_node(node, problem_json, proof_contract)]
    assert_true(required_nodes, "Expected at least one non-source node.")
    for node in required_nodes:
        assert_true(bool(node.get("proof_body", {}).get("steps")), f"Node {node['id']} has no proof_body.steps")
    return "test_node_proof_generation passed"


def test_week2_langgraph_pipeline():
    summaries = []
    pass_count = 0
    for item in BENCHMARK_PROBLEMS:
        try:
            result = WEEK2_APP.invoke({"raw_problem": item["raw_problem"], "trace": []})
            assert_true("problem_json" in result, "Missing problem_json.")
            assert_true("proof_contract" in result, "Missing proof_contract.")
            assert_true("proof_graph_state" in result, "Missing proof_graph_state.")
            assert_true("aggregator_result" in result, "Missing aggregator_result.")
            summaries.append({"problem_id": item["problem_id"], "accepted": result["accepted"], "errors": len(result.get("current_errors", [])), "sources": [step for step in result.get("trace", [])]})
            pass_count += 1
        except Exception as exc:
            print(f"Pipeline test failed for {item['problem_id']}: {exc}")
            summaries.append({"problem_id": item["problem_id"], "accepted": False, "error": repr(exc)})
    Path(ARTIFACT_DIR / "week2_pipeline_summaries.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    assert_true(pass_count >= len(BENCHMARK_PROBLEMS) - 1, f"Expected at least {len(BENCHMARK_PROBLEMS)-1} pipeline completions, got {pass_count}/{len(BENCHMARK_PROBLEMS)}")
    return f"test_week2_langgraph_pipeline passed with {pass_count}/{len(BENCHMARK_PROBLEMS)}"


def run_week2_tests():
    tests = [
        test_model_loaded_or_declared,
        test_problem_and_contract_generation,
        test_graph_generation_schema,
        test_node_proof_generation,
        test_week2_langgraph_pipeline,
    ]
    results = []
    for test in tests:
        try:
            result = test()
            print(result)
            results.append(result)
        except Exception as exc:
            msg = f"{test.__name__} FAILED: {exc}"
            print(msg)
            results.append(msg)
    print("All Week 2 tests finished.")
    return results


week2_test_results = run_week2_tests()

# ── Save outputs ──────────────────────────────────────────────────────────────

Path(ARTIFACT_DIR / "week2_test_results.json").write_text(
    json.dumps(week2_test_results, ensure_ascii=False, indent=2), encoding="utf-8"
)
Path(ARTIFACT_DIR / "week2_demo_result.json").write_text(
    json.dumps(demo_result, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("Saved:", ARTIFACT_DIR / "week2_test_results.json")
print("Saved:", ARTIFACT_DIR / "week2_demo_result.json")
print("Saved:", ARTIFACT_DIR / "week2_pipeline_summaries.json")
