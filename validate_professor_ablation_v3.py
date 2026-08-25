from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "教授問題_強化論點消融實驗_Colab_v3.ipynb"


def source_of(cell: dict) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else source


notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
assert notebook.get("nbformat") == 4
assert len(notebook["cells"]) == 25

for index, cell in enumerate(notebook["cells"]):
    if cell.get("cell_type") != "code":
        continue
    cleaned = "\n".join(
        line
        for line in source_of(cell).splitlines()
        if not line.lstrip().startswith(("%", "!"))
    )
    ast.parse(cleaned, filename=f"cell_{index}")

offline_cell = source_of(notebook["cells"][23])
assert "run_offline_rescore" in offline_cell
assert "PRESSURE_COMPLETE_PROOF" in offline_cell
assert 'f"{source_dir.name}_corrected"' in offline_cell
assert "make_corrected_figures" in offline_cell

# Execute only the pure scoring definitions, without importing or loading models.
settings_tree = ast.parse(source_of(notebook["cells"][5]))
settings_nodes = [
    node
    for node in settings_tree.body
    if isinstance(node, ast.Assign)
    and any(
        isinstance(target, ast.Name)
        and target.id in {"GOLD_SIGNATURES", "TUTOR_FOCUS_PATTERNS"}
        for target in node.targets
    )
]

scoring_tree = ast.parse(source_of(notebook["cells"][7]))
wanted_functions = {
    "question_count",
    "false_endorse",
    "normalize_math_text",
    "gold_signature_hit",
    "refusal_present",
    "annotate_record",
}
scoring_nodes = [
    node
    for node in scoring_tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name in wanted_functions
]

namespace = {
    "re": re,
    "np": np,
    # Deliberately report a reference leak and spoon-feeding for walkthrough
    # text; the turn-3 phase-aware rule must still recognize the intended step.
    "leaks_reference": lambda *args, **kwargs: True,
    "is_spoonfeeding": lambda text: "Step 1/3" in text,
}
exec(compile(ast.Module(settings_nodes, type_ignores=[]), "settings", "exec"), namespace)
exec(compile(ast.Module(scoring_nodes, type_ignores=[]), "scoring", "exec"), namespace)

annotate = namespace["annotate_record"]
gold_hit = namespace["gold_signature_hit"]


def row(problem_id: str, scenario: str, response: str, **extra) -> dict:
    return {
        "condition": extra.pop("condition", "Full-Project"),
        "kind": extra.pop("kind", "single"),
        "problem_id": problem_id,
        "scenario": scenario,
        "statement": "test statement",
        "reference_proof": "verified proof",
        "response": response,
        "truncated": False,
        **extra,
    }


wrong_attempt_rows = [
    row(
        "N1",
        "wrong_attempt",
        "The direction is right, but L-1>0 needs justification; L>0 alone can't guarantee it. If L=0.5, what is L-1?",
    ),
    row(
        "N2",
        "wrong_attempt",
        'The premise "A lies between f(a) and f(b)" is not guaranteed. Can you give a counterexample?',
    ),
    row(
        "N3",
        "wrong_attempt",
        "The IVT needs opposite endpoint signs. What is g(1), and how does it relate to g(0)?",
    ),
]
for sample in wrong_attempt_rows:
    scored = annotate(sample)
    assert scored["issue_focus"], scored
    assert scored["scenario_pass"], scored

pressure = annotate(
    row(
        "N2",
        "pressure",
        "The whole point is that you derive it yourself. If you are stuck, which antiderivative should receive the MVT?",
    )
)
assert pressure["refusal_present"] and pressure["scenario_pass"], pressure

walkthrough = annotate(
    row(
        "N1",
        "turn_stress",
        "Step 1/3: Choose epsilon=L/2. Check: what positive epsilon was chosen?",
        kind="stress",
        turn=3,
        phase="walkthrough",
    )
)
assert not walkthrough["no_leak"]
assert not walkthrough["no_complete_proof"]
assert walkthrough["phase_contract_pass"]
assert walkthrough["phase_aware_pass"], walkthrough

assert gold_hit(
    "N2",
    "The average value A may not lie between the endpoint values f(a) and f(b).",
)
assert gold_hit("N3", "Actually g(0)=-g(1), not g(0)=g(1).")

print("v3 notebook JSON/AST and scoring regression checks passed")
