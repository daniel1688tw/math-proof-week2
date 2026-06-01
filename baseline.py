"""
baseline.py — Standalone Chain Pipeline for Math Proof Generation

Completely self-contained: no imports from other project files.

Chain (4 stages):
  raw_problem
    [1] Extract   → identify premises[] and goal
    [2] Generate  → produce a flat list of proof steps
    [3] Verify    → structural checks (empty fields, vague terms, bad refs)
    [4] Correct   → if blocking errors exist, ask LLM to fix  (retry loop)
  → BaselineResult

Usage:
    python baseline.py                          # run all 3 benchmark problems
    python baseline.py "Prove that 2+2=4."      # run a custom problem
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field

# Force UTF-8 output so Unicode chars (arrows, bullets, math) don't crash on
# Windows consoles / PowerShell redirection that default to cp950/cp932.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from typing import Any, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Configuration  (edit here to tune behaviour)
# ─────────────────────────────────────────────────────────────────────────────

MODEL_NAME          = "Qwen/Qwen2.5-Math-7B-Instruct"
USE_4BIT            = True          # BitsAndBytes nf4 quantisation when GPU available
MAX_NEW_TOKENS      = 1500
EXTRACT_MAX_TOKENS  = 1024
TEMPERATURE         = 0.1
MAX_CORRECTIONS     = 3             # correction retry budget

VAGUE_TERMS = [
    "obvious", "clearly", "some theorem", "it follows trivially",
    "顯然", "容易看出", "trivially", "trivial",
]


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PremiseGoal:
    premises: List[str]
    goal: str


@dataclass
class ProofStep:
    step_id: str
    statement: str
    justification: str
    refs: List[str] = field(default_factory=list)


@dataclass
class LinearProof:
    steps: List[ProofStep]
    conclusion: str


@dataclass
class VerifierError:
    step_id: Optional[str]
    severity: str   # "high" | "medium" | "low"
    description: str
    required_fix: str
    blocking: bool  # True → must fix before acceptance


@dataclass
class BaselineResult:
    problem_id: str
    raw_problem: str
    premises: List[str]
    goal: str
    proof: Optional[LinearProof]
    errors: List[VerifierError]
    accepted: bool
    attempts: int
    elapsed_sec: float


# ─────────────────────────────────────────────────────────────────────────────
# LLM Backend  (lazy-loaded; replace ACTIVE_LLM for testing)
# ─────────────────────────────────────────────────────────────────────────────

class _LLMBackend:
    """Loads Qwen2.5-Math with 4-bit quantisation when a GPU is present."""

    def __init__(self) -> None:
        self.backend: str = "fallback"
        self.error: Optional[str] = None
        self._tokenizer: Any = None
        self._model: Any = None
        self._torch: Any = None
        self._load()

    def _load(self) -> None:
        try:
            import torch
        except ImportError as exc:
            self.error = f"import error: {exc}"
            return

        self._torch = torch

        if torch.cuda.is_available():
            try:
                import bitsandbytes as _bnb
                _dummy = _bnb.nn.Linear4bit(16, 16, bias=False).to("cuda")
                _x = torch.zeros(1, 16, device="cuda", dtype=torch.float16)
                with torch.no_grad():
                    _dummy(_x)
                del _dummy, _x
                torch.cuda.synchronize()
                print("[baseline] bitsandbytes 4-bit warm-up OK", flush=True)
            except Exception as e:
                print(f"[baseline] bnb warm-up failed (will try anyway): {e}", flush=True)

        try:
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                BitsAndBytesConfig,
            )
        except ImportError as exc:
            self.error = f"import error: {exc}"
            return

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                MODEL_NAME, trust_remote_code=True
            )
            kw: dict = {"trust_remote_code": True}

            if torch.cuda.is_available() and USE_4BIT:
                kw["device_map"] = {"": 0}
                kw["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
            elif torch.cuda.is_available():
                kw["device_map"] = "auto"
                kw["torch_dtype"] = torch.float16

            print(f"[baseline] Loading {MODEL_NAME} ...", flush=True)
            self._model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, **kw)
            self._model.eval()
            self.backend = "hf"
            print(f"[baseline] Model loaded: {MODEL_NAME}", flush=True)
        except Exception as exc:
            self.error = repr(exc)
            print(f"[baseline] Model load failed: {exc}", flush=True)

    # Public interface expected by the pipeline
    def generate(self, prompt: str, max_new_tokens: int = MAX_NEW_TOKENS) -> str:
        if self.backend != "hf":
            raise RuntimeError(
                f"[baseline] No HF model available — {self.error}"
            )
        torch = self._torch
        messages = [
            {
                "role": "system",
                "content": (
                    "You output ONLY valid JSON objects. "
                    "No explanation, no markdown, no text outside the JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        if hasattr(self._tokenizer, "apply_chat_template"):
            text = self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            text = prompt
        # Nudge the model to begin its response with `{` so the output is JSON.
        text = text + "{"

        inputs = self._tokenizer(text, return_tensors="pt")
        prompt_len = inputs["input_ids"].shape[-1]
        model_max = getattr(self._model.config, "max_position_embeddings", 4096)
        available = model_max - prompt_len
        actual_max = min(max_new_tokens, available)
        if actual_max < 20:
            raise RuntimeError(
                f"[baseline] Prompt too long ({prompt_len} tokens). "
                "Shorten the prompt or increase max_position_embeddings."
            )

        device = next(self._model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        print(
            f"  [generate] prompt={prompt_len}tok, max_new={actual_max}tok",
            flush=True,
        )
        with torch.no_grad():
            out_ids = self._model.generate(
                **inputs,
                max_new_tokens=actual_max,
                do_sample=TEMPERATURE > 0,
                temperature=TEMPERATURE if TEMPERATURE > 0 else None,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        new_tokens = out_ids[0][inputs["input_ids"].shape[-1] :]
        return "{" + self._tokenizer.decode(new_tokens, skip_special_tokens=True)


# Module-level singleton — replace for testing, e.g. baseline.ACTIVE_LLM = mock
ACTIVE_LLM: Any = None


def _get_llm() -> Any:
    """Return ACTIVE_LLM, loading it lazily on first real call."""
    global ACTIVE_LLM
    if ACTIVE_LLM is None:
        ACTIVE_LLM = _LLMBackend()
    return ACTIVE_LLM


def _llm_call(prompt: str, max_new_tokens: int = MAX_NEW_TOKENS) -> str:
    return _get_llm().generate(prompt, max_new_tokens=max_new_tokens)


# ─────────────────────────────────────────────────────────────────────────────
# JSON Extractor  (no dependency on json_utils.py)
# ─────────────────────────────────────────────────────────────────────────────

def _find_json_object(text: str) -> Optional[str]:
    """Return the first balanced {...} substring from text, or None."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _repair_json(raw: str) -> str:
    """Apply light heuristic repairs to a truncated / malformed JSON string."""
    # Fix ) used as array-close instead of ] (common Qwen output artifact).
    repaired = re.sub(r'(["\}])\s*\)', lambda m: m.group(1) + ']', raw)
    # Strip trailing commas before ] or }
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    # Scan to find unmatched { / [ and whether we ended inside an unclosed
    # string — all while ignoring brace characters inside string values
    # (e.g. LaTeX \frac{1}{n} must not skew the depth count).
    depth_c = depth_s = 0
    in_str = esc = False
    for ch in repaired:
        if esc:
            esc = False; continue
        if ch == '\\' and in_str:
            esc = True; continue
        if ch == '"':
            in_str = not in_str; continue
        if in_str:
            continue
        if ch == '{':
            depth_c += 1
        elif ch == '}':
            depth_c -= 1
        elif ch == '[':
            depth_s += 1
        elif ch == ']':
            depth_s -= 1
    # Close an unclosed string value *before* appending structural tokens,
    # otherwise the closing } / ] would land inside the string.
    if in_str:
        repaired += '"'
    if depth_c > 0:
        repaired += '}' * depth_c
    if depth_s > 0:
        repaired += ']' * depth_s
    return repaired


def extract_json(text: str) -> Optional[dict]:
    """Try to extract and parse a JSON object from model output."""
    # 1. Try raw text first (model might output pure JSON)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 2. Find balanced {...} block.
    #    If the output is truncated (no closing }), _find_json_object returns
    #    None — fall back to everything from the first { onward so the repair
    #    step can still close the object.
    candidate = _find_json_object(text)
    if candidate is None:
        start = text.find("{")
        if start != -1:
            candidate = text[start:]

    if candidate:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        # 3. Light structural repairs (trailing commas, unbalanced brackets)
        repaired = _repair_json(candidate)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        # 4. Fix LaTeX escape sequences that collide with JSON escape chars.
        #    \right, \rho  → \r is valid JSON (CR) but wrong here
        #    \nabla, \nu   → \n is valid JSON (LF) but wrong here
        #    \theta, \tau  → \t is valid JSON (tab) but wrong here
        #    \beta         → \b is valid JSON (backspace) but wrong here
        #    \frac, \forall → \f is valid JSON (form-feed) but wrong here
        #    Rule: if \x is followed by more letters it's a LaTeX command.
        pre = re.sub(r'\\([nrtbf])(?=[a-zA-Z])', r'\\\\\1', repaired)
        # 5. Fix all remaining invalid JSON escape sequences
        #    (\( \) \cdot \sin \cos etc.)
        escaped = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', pre)
        try:
            return json.loads(escaped)
        except json.JSONDecodeError:
            pass

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

def _prompt_extract(raw_problem: str) -> str:
    return f"""\
Extract the mathematical structure from this problem.
Output ONLY a JSON object. No explanation, no markdown, no surrounding text.

Required fields:
  "premises" : list of strings — each given assumption or condition
  "goal"     : string — the exact statement that must be proven

Example output:
{{"premises": ["f is continuous on [a,b]", "N is between f(a) and f(b)"], "goal": "there exists c in [a,b] such that f(c)=N"}}

Problem: {raw_problem}

JSON:"""


def _prompt_generate(premises: List[str], goal: str) -> str:
    p_block = "\n".join(f"  - {p}" for p in premises)
    return f"""\
Write a rigorous step-by-step mathematical proof.
Output ONLY a JSON object. No explanation, no markdown, no surrounding text.

Given premises:
{p_block}

Goal to prove: {goal}

Each element in "steps" must have:
  "step_id"      : "S1", "S2", ... (sequential)
  "statement"    : precise mathematical claim for this step
  "justification": cite a specific theorem, definition, or axiom by name
                   (never use vague words like "obvious", "clearly", "trivial")
  "refs"         : list of earlier step_ids this step depends on  ([] for first steps)

Also include at the top level:
  "conclusion"   : a sentence restating what was proven (must match the goal)

JSON:"""


def _prompt_correct(
    premises: List[str],
    goal: str,
    proof_json: str,
    errors: List[VerifierError],
) -> str:
    p_block = "\n".join(f"  - {p}" for p in premises)
    err_block = "\n".join(
        f"  [{e.severity.upper()}] step {e.step_id or 'global'}: "
        f"{e.description}  →  Fix: {e.required_fix}"
        for e in errors
    )
    return f"""\
The proof below contains errors. Fix ALL of them and return the corrected proof.
Output ONLY a JSON object. No explanation, no markdown, no surrounding text.

Given premises:
{p_block}

Goal: {goal}

Current (flawed) proof:
{proof_json}

Errors to fix:
{err_block}

Return corrected proof JSON with the same structure (steps[], conclusion):
JSON:"""


# ─────────────────────────────────────────────────────────────────────────────
# Parsers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_premise_goal(text: str) -> PremiseGoal:
    data = extract_json(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object for premise-goal, got: {type(data).__name__}")
    premises = data.get("premises", [])
    if isinstance(premises, str):
        premises = [premises]
    goal = str(data.get("goal", "")).strip()
    if not goal:
        raise ValueError("Field 'goal' is missing or empty in LLM response")
    return PremiseGoal(premises=[str(p) for p in premises if str(p).strip()], goal=goal)


def _parse_linear_proof(text: str) -> LinearProof:
    data = extract_json(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object for proof, got: {type(data).__name__}")
    steps: List[ProofStep] = []
    for raw in data.get("steps", []):
        if not isinstance(raw, dict):
            continue
        steps.append(
            ProofStep(
                step_id=str(raw.get("step_id", "")).strip(),
                statement=str(raw.get("statement", "")).strip(),
                justification=str(raw.get("justification", "")).strip(),
                refs=[str(r) for r in raw.get("refs", []) if r],
            )
        )
    conclusion = str(data.get("conclusion", "")).strip()
    return LinearProof(steps=steps, conclusion=conclusion)


# ─────────────────────────────────────────────────────────────────────────────
# Verifier
# ─────────────────────────────────────────────────────────────────────────────

def verify_linear_proof(
    proof: LinearProof,
    goal: str,
    raw_problem: str = "",
) -> List[VerifierError]:
    """Structural verifier.

    Blocking (high-severity) errors prevent acceptance.
    Non-blocking (medium/low) errors are reported but do not block.
    """
    errors: List[VerifierError] = []

    # ── Extract named theorems the problem is asking to PROVE ─────────────────
    # Matches capitalized multi-word names like "Mean Value Theorem",
    # "Intermediate Value Theorem". Lowercased "chain rule" is intentionally
    # excluded — it appears as a premise, not the theorem being proved.
    _theorems_to_prove: set = set()
    if raw_problem:
        _theorems_to_prove = {
            m.lower()
            for m in re.findall(
                r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\s+(?:Theorem|Lemma|Corollary|Law)",
                raw_problem,
            )
        }

    # ── Guard: empty proof ────────────────────────────────────────────────────
    if not proof.steps:
        errors.append(
            VerifierError(
                step_id=None, severity="high",
                description="Proof contains no steps",
                required_fix="Provide at least two proof steps leading to the goal",
                blocking=True,
            )
        )
        return errors

    known_ids = {s.step_id for s in proof.steps}

    # ── Per-step checks ───────────────────────────────────────────────────────
    for step in proof.steps:
        sid = step.step_id or "?"

        if not step.statement:
            errors.append(VerifierError(
                step_id=sid, severity="high",
                description="Empty statement",
                required_fix="Provide a precise mathematical claim for this step",
                blocking=True,
            ))

        if not step.justification:
            errors.append(VerifierError(
                step_id=sid, severity="high",
                description="Missing justification",
                required_fix="Cite a specific theorem, definition, or axiom by name",
                blocking=True,
            ))

        combined = (step.statement + " " + step.justification).lower()
        for term in VAGUE_TERMS:
            if term.lower() in combined:
                errors.append(VerifierError(
                    step_id=sid, severity="medium",
                    description=f"Vague justification: '{term}'",
                    required_fix=f"Replace '{term}' with a precise mathematical reason",
                    blocking=False,
                ))

        # ── Circular-reasoning check ──────────────────────────────────────────
        # A step that justifies itself by citing the theorem being proved is
        # circular: the theorem cannot serve as evidence for its own proof.
        just_lower = step.justification.lower()
        for thm in _theorems_to_prove:
            if thm in just_lower:
                errors.append(VerifierError(
                    step_id=sid, severity="high",
                    description=(
                        f"Circular reasoning: justification directly cites "
                        f"'{thm}', which is the theorem being proved"
                    ),
                    required_fix=(
                        f"Do not cite '{thm}' — prove it from first principles. "
                        "For MVT: define h(x)=f(x)-[slope]*(x-a), apply Rolle's Theorem. "
                        "For IVT: use the least-upper-bound (completeness) axiom on "
                        "S={x in [a,b]: f(x)<N}."
                    ),
                    blocking=True,
                ))

        for ref in step.refs:
            if ref and ref not in known_ids:
                errors.append(VerifierError(
                    step_id=sid, severity="medium",
                    description=f"Reference to unknown step '{ref}'",
                    required_fix="Only reference step_ids defined earlier in the proof",
                    blocking=False,
                ))

    # ── Conclusion check ──────────────────────────────────────────────────────
    if not proof.conclusion:
        errors.append(VerifierError(
            step_id=None, severity="high",
            description="Missing conclusion",
            required_fix="Add a 'conclusion' field restating what was proven",
            blocking=True,
        ))

    # ── Soft depth check ─────────────────────────────────────────────────────
    if len(proof.steps) == 1:
        errors.append(VerifierError(
            step_id=None, severity="medium",
            description="Proof has only one step — likely too shallow",
            required_fix="Break the argument into at least two distinct logical steps",
            blocking=False,
        ))

    # ── Soft conclusion–goal alignment check ─────────────────────────────────
    if proof.conclusion and goal:
        goal_words = set(re.findall(r"[a-z0-9]+", goal.lower())) - {
            "a", "an", "the", "of", "in", "is", "and", "to", "that",
            "we", "have", "let", "for", "be", "with",
        }
        concl_text = proof.conclusion.lower()
        if goal_words:
            overlap = sum(1 for w in goal_words if w in concl_text)
            if overlap / len(goal_words) < 0.30:
                errors.append(VerifierError(
                    step_id=None, severity="low",
                    description="Conclusion does not clearly reflect the stated goal",
                    required_fix="Rewrite conclusion so it explicitly restates the goal",
                    blocking=False,
                ))

    return errors


def _is_accepted(errors: List[VerifierError]) -> bool:
    return not any(e.blocking and e.severity == "high" for e in errors)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Stages
# ─────────────────────────────────────────────────────────────────────────────

def stage_extract(raw_problem: str) -> PremiseGoal:
    """Stage 1 — Extract premises and goal from the problem statement."""
    out = _llm_call(_prompt_extract(raw_problem), max_new_tokens=EXTRACT_MAX_TOKENS)
    return _parse_premise_goal(out)


def stage_generate(pg: PremiseGoal) -> LinearProof:
    """Stage 2 — Generate an initial flat proof."""
    out = _llm_call(_prompt_generate(pg.premises, pg.goal))
    return _parse_linear_proof(out)


def stage_correct(
    proof: LinearProof,
    premises: List[str],
    goal: str,
    errors: List[VerifierError],
) -> LinearProof:
    """Stage 4 — Ask LLM to fix blocking errors in the current proof."""
    proof_json = json.dumps(
        {"steps": [asdict(s) for s in proof.steps], "conclusion": proof.conclusion},
        ensure_ascii=False, indent=2,
    )
    out = _llm_call(_prompt_correct(premises, goal, proof_json, errors))
    return _parse_linear_proof(out)


# ─────────────────────────────────────────────────────────────────────────────
# Main Chain Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_baseline(
    raw_problem: str,
    problem_id: str = "baseline",
    max_corrections: int = MAX_CORRECTIONS,
) -> BaselineResult:
    """Run the 4-stage chain pipeline.

    Chain: Extract → Generate → Verify → Correct (retry up to max_corrections).
    Returns a BaselineResult. Never raises — internal errors captured in .errors.
    """
    t0 = time.time()

    try:
        # Stage 1: extract
        pg = stage_extract(raw_problem)
    except Exception as exc:
        return BaselineResult(
            problem_id=problem_id, raw_problem=raw_problem,
            premises=[], goal="",
            proof=None,
            errors=[VerifierError(step_id=None, severity="high",
                                  description=f"stage_extract failed: {exc}",
                                  required_fix="", blocking=True)],
            accepted=False, attempts=0, elapsed_sec=time.time() - t0,
        )

    try:
        # Stage 2: generate
        proof = stage_generate(pg)
    except Exception as exc:
        return BaselineResult(
            problem_id=problem_id, raw_problem=raw_problem,
            premises=pg.premises, goal=pg.goal,
            proof=None,
            errors=[VerifierError(step_id=None, severity="high",
                                  description=f"stage_generate failed: {exc}",
                                  required_fix="", blocking=True)],
            accepted=False, attempts=0, elapsed_sec=time.time() - t0,
        )

    attempts = 1

    # Stage 3 + 4 loop: verify → correct
    errors = verify_linear_proof(proof, pg.goal, raw_problem=raw_problem)
    blocking = [e for e in errors if e.blocking]

    while blocking and attempts < max_corrections:
        try:
            proof = stage_correct(proof, pg.premises, pg.goal, errors)
        except Exception as exc:
            errors.append(VerifierError(step_id=None, severity="high",
                                        description=f"stage_correct failed: {exc}",
                                        required_fix="", blocking=True))
            break
        errors = verify_linear_proof(proof, pg.goal, raw_problem=raw_problem)
        blocking = [e for e in errors if e.blocking]
        attempts += 1

    return BaselineResult(
        problem_id=problem_id,
        raw_problem=raw_problem,
        premises=pg.premises,
        goal=pg.goal,
        proof=proof,
        errors=errors,
        accepted=_is_accepted(errors),
        attempts=attempts,
        elapsed_sec=time.time() - t0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def _safe(s: str) -> str:
    """Strip control characters that corrupt terminal output (e.g. CR from \\r in LaTeX)."""
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', s).replace('\r', '')


def _print_result(result: BaselineResult) -> None:
    sep = "─" * 64
    print(f"\n{sep}")
    print(f"Problem : {result.problem_id}")
    print(f"Accepted: {result.accepted}  |  Attempts: {result.attempts}  |  Time: {result.elapsed_sec:.1f}s")
    print(f"\nPremises ({len(result.premises)}):")
    for p in result.premises:
        print(f"  • {_safe(p)}")
    print(f"\nGoal: {_safe(result.goal)}")
    if result.proof:
        print(f"\nProof ({len(result.proof.steps)} steps):")
        for s in result.proof.steps:
            refs = f"  [refs: {', '.join(s.refs)}]" if s.refs else ""
            print(f"  {s.step_id}: {_safe(s.statement)}")
            print(f"       ↳ {_safe(s.justification)}{refs}")
        print(f"\nConclusion: {_safe(result.proof.conclusion)}")
    blocking = [e for e in result.errors if e.blocking]
    nonblocking = [e for e in result.errors if not e.blocking]
    if blocking:
        print(f"\nBlocking errors ({len(blocking)}):")
        for e in blocking:
            print(f"  [HIGH] {e.step_id or 'global'}: {e.description}")
    if nonblocking:
        print(f"\nNon-blocking warnings ({len(nonblocking)}):")
        for e in nonblocking:
            print(f"  [{e.severity.upper()}] {e.step_id or 'global'}: {e.description}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Non-interactive: problem passed as CLI arguments
        result = run_baseline(" ".join(sys.argv[1:]), problem_id="custom")
        _print_result(result)
        print(f"\n{'─'*64}")
        print("Done.")
    else:
        # Interactive mode: prompt the user repeatedly
        print("Math Proof Generator  (type 'quit' or leave blank to exit)\n")
        counter = 0
        while True:
            try:
                raw = input("Enter problem: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not raw or raw.lower() in {"quit", "exit", "q"}:
                break
            counter += 1
            result = run_baseline(raw, problem_id=f"problem_{counter}")
            _print_result(result)
            print()
        print(f"{'─'*64}")
        print("Done.")
