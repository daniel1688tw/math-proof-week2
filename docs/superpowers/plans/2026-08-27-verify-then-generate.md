# Advanced Proof Verify-Then-Generate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add proof-attempt verification before tutor response generation while preserving the `full-project` TutorDriver behavior and the deployed `qlora_adapter_v9` generator.

**Architecture:** The existing router remains authoritative. Only `guide/respond_attempt` turns call the existing Qwen3-4B Thinking `find_gaps()` backstop before `_generate()`, then reuse `_backstop_block()` to ground the v9 response; the existing post-generation semantic review remains intact. A paired evaluator runs the same advanced-proof attempts with the feature off and on, records diagnostics and latency, and judges quality without changing regression baselines.

**Tech Stack:** Python 3.11, existing `TutorDriver`, Ollama/Qwen3-4B Thinking backstop, Transformers/PEFT 4-bit Qwen3-4B with `qlora_adapter_v9`, existing Antigravity judge wrapper.

**Spec:** `docs/superpowers/specs/2026-08-27-verify-then-generate-design.md`

## Global Constraints

- Implement on branch `explore/verify-then-generate`; do not modify `full-project`.
- Treat commit `f2f26bb` on `full-project` as the tutor-style and behavior source of truth.
- Keep `qlora_adapter_v9` as the response generator; do not retrain or replace it.
- Use the existing `review_backstop.py` Qwen3-4B Thinking/Ollama path as verifier.
- Do not import MathDial, SimCSE/ROSCOE, OpenAI wrappers, elementary-math prompts, or dependencies from `reference_repos/verify-then-generate`.
- Preserve Level 0/1/2, refusal, anti-leakage, single-question, walkthrough, review, closed, peer-mode, and readiness behavior.
- Do not update either regression baseline file.
- Preserve all unrelated untracked files in the working tree.

---

## File Structure

- Modify `dataset/tutor_driver.py`: feature flag, pre-generation verification diagnostics, routing integration, and prompt grounding.
- Modify `dataset/test_driver_unit.py`: deterministic call-order, gating, prompt-injection, clear-result, unavailable-result, and disabled-feature tests.
- Create `dataset/eval_verify_then_generate.py`: paired v9 generation, judging, metrics, latency accounting, and JSON/Markdown output.
- Create `dataset/test_verify_then_generate_eval.py`: CPU-only tests for evaluator prompt construction and summary calculations.
- Modify `dataset/regression_suite.py`: include the new CPU-only evaluator test in Tier 0.
- Modify `README.md`: document the feature flag, exact trigger, model roles, fallback, and paired evaluation command.
- Modify `專案架構設計.md`: show the proof-attempt verify-before-generate path without changing the existing phase contract.
- Create `dataset/eval_out_xdomain/VERIFY_THEN_GENERATE_VERDICT.md`: final evidence and adopt/conditional/reject decision after evaluation.

### Task 1: Add pre-generation proof-attempt verification

**Files:**
- Modify: `dataset/test_driver_unit.py`
- Modify: `dataset/tutor_driver.py:45-55, 792-825, 1343-1378, 2992-3067`

**Interfaces:**
- Consumes: `review_backstop.find_gaps(statement: str, reference_proof: str, draft: str) -> list[str] | None`.
- Produces: `TutorDriver.verify_then_generate: bool` and `TutorDriver._prepare_backstop_context(student_text: str) -> None`.
- Produces state: `pre_generation_verification = {"status": str, "issues": list[str], "first_issue": str, "latency_seconds": float}`.
- Status values: `issues`, `clear`, `unavailable`, `disabled`, `not_applicable`.

- [ ] **Step 1: Write failing unit tests for trigger gating and call order**

Add a test section to `dataset/test_driver_unit.py` with a stub that records the actual controller order:

```python
print("[VTG] 高等證明嘗試：先驗證再生成")

class _VerifyThenGenerateStub(_StubDriver):
    call_order: list
    generated_system: str
    verifier_result: list | None

    def _run_pre_generation_verifier(self, student_text):
        self.call_order.append(("verify", student_text))
        return self.verifier_result

    def _generate(self, level):
        self.call_order.append(("generate", level))
        self.generated_system = self._system(level)
        return "先聚焦你剛才那一步。哪一個前提需要先核對？"

    def _enforce_guide_reply_policy(self, reply, level, log):
        return reply

vtg = _VerifyThenGenerateStub(
    tok=None, model=_StubModel(), problem=probs["H4"],
    backstop=True, verify_then_generate=True)
vtg.call_order = []
vtg.verifier_result = ["Heine-Cantor 定理只適用於緊緻集合，不能直接套用在 ℝ"]
vtg.start(opener="我的證明使用 Heine-Cantor 定理，所以 ℝ 上連續就一致連續。這樣對嗎？")
check("respond_attempt 先 verify 再 generate",
      [item[0] for item in vtg.call_order[:2]] == ["verify", "generate"])
check("前置診斷注入 v9 的幕後 prompt",
      "Heine-Cantor" in vtg.generated_system
      and vtg.state["pre_generation_verification"]["status"] == "issues")

for label, phase, action, peer, backstop, enabled in (
    ("normal guide", "guide", "normal_guide", False, True, True),
    ("clarification", "guide", "answer_clarification", False, True, True),
    ("refusal", "guide", "refuse_tutor_write", False, True, True),
    ("walkthrough", "walkthrough", "normal_guide", False, True, True),
    ("closed", "closed", "post_completion_reply", False, True, True),
    ("peer", "guide", "respond_attempt", True, True, True),
    ("backstop off", "guide", "respond_attempt", False, False, True),
    ("feature off", "guide", "respond_attempt", False, True, False),
):
    problem = dict(probs["H4"])
    if peer:
        problem["grounding"] = "unverified"
    probe = _VerifyThenGenerateStub(
        tok=None, model=_StubModel(), problem=problem,
        backstop=backstop, verify_then_generate=enabled)
    probe.call_order, probe.verifier_result = [], ["不應呼叫"]
    probe.state.update(phase=phase, turn_action=action)
    probe._prepare_backstop_context("學生文字")
    check(f"{label} 不觸發前置 verifier",
          not any(item[0] == "verify" for item in probe.call_order))
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```powershell
python dataset\test_driver_unit.py
```

Expected: failure because `verify_then_generate`, `_run_pre_generation_verifier()`, and `_prepare_backstop_context()` do not exist and `respond_attempt` does not verify before `_generate()`.

- [ ] **Step 3: Add the feature flag and diagnostic defaults**

In `dataset/tutor_driver.py`, import `time` and add this dataclass field next to `backstop`:

```python
verify_then_generate: bool = field(
    default_factory=lambda: os.environ.get("VERIFY_THEN_GENERATE", "1") == "1")
```

In `__post_init__`, initialize a serializable diagnostic without changing phase state:

```python
self.state.setdefault("pre_generation_verification", {
    "status": "not_applicable", "issues": [], "first_issue": "",
    "latency_seconds": 0.0,
})
```

- [ ] **Step 4: Implement one shared preparation path**

Add these focused helpers next to `_consult_backstop()`:

```python
def _record_pre_generation_verification(self, status, issues=None, latency=0.0):
    clean = [str(item).strip() for item in (issues or []) if str(item).strip()]
    self.state["pre_generation_verification"] = {
        "status": status,
        "issues": clean,
        "first_issue": clean[0] if clean else "",
        "latency_seconds": round(max(0.0, float(latency)), 4),
    }

def _run_pre_generation_verifier(self, student_text):
    try:
        from review_backstop import find_gaps
    except ImportError:
        return None
    return find_gaps(
        self.problem["statement"], self.problem["reference_proof"], student_text)

def _prepare_backstop_context(self, student_text):
    self.state["backstop_gaps"] = None
    phase = self.state.get("phase")
    action = self.state.get("turn_action")
    if not self.is_peer() and phase == "review":
        self._record_pre_generation_verification("not_applicable")
        self._consult_backstop(student_text)
        return
    if self.is_peer() or phase != "guide" or action != "respond_attempt":
        self._record_pre_generation_verification("not_applicable")
        return
    if not self.backstop or not self.verify_then_generate:
        self._record_pre_generation_verification("disabled")
        return
    started = time.perf_counter()
    issues = self._run_pre_generation_verifier(student_text)
    elapsed = time.perf_counter() - started
    if issues is None:
        self._record_pre_generation_verification("unavailable", latency=elapsed)
        return
    self.state["backstop_gaps"] = list(issues)
    self._record_pre_generation_verification(
        "issues" if issues else "clear", issues, elapsed)
```

Replace the duplicated review-only branches in both `start()` and `step()` with `_prepare_backstop_context()`. In `start()`, pass the original `user_opener` when supplied so the verifier sees only the student's attempt rather than the driver-added `Problem:` prefix:

```python
self._prepare_backstop_context(user_opener or first)
```

In `step()` pass `student_text`.

- [ ] **Step 5: Add clear, unavailable, serialization, and invariant tests**

Extend the same test section:

```python
vtg_clear = _VerifyThenGenerateStub(
    tok=None, model=_StubModel(), problem=probs["H4"],
    backstop=True, verify_then_generate=True)
vtg_clear.call_order, vtg_clear.verifier_result = [], []
vtg_clear.start(opener="我先核對目前這一步：定理的定義域條件已滿足。")
check("局部 clear 不會提前結案",
      vtg_clear.state["pre_generation_verification"]["status"] == "clear"
      and vtg_clear.state["phase"] == "guide"
      and not vtg_clear.state.get("done_closed"))

vtg_down = _VerifyThenGenerateStub(
    tok=None, model=_StubModel(), problem=probs["H4"],
    backstop=True, verify_then_generate=True)
vtg_down.call_order, vtg_down.verifier_result = [], None
reply_down = vtg_down.start(opener="我的證明先套用 Heine-Cantor，這樣對嗎？")
check("verifier unavailable 安全降級且仍有助教回覆",
      bool(reply_down)
      and vtg_down.state["pre_generation_verification"]["status"] == "unavailable"
      and vtg_down.state.get("backstop_gaps") is None)
check("前置診斷隨 session 保存",
      vtg_down.dump_state()["state"]["pre_generation_verification"]["status"] == "unavailable")
check("前置診斷不洩漏完整參考解且保留單問句",
      not leaks_reference(vtg.messages[-1]["content"], probs["H4"]["reference_proof"])
      and len(re.findall(r"[?？]", vtg.messages[-1]["content"])) == 1)
```

- [ ] **Step 6: Run all deterministic tests**

Run:

```powershell
python dataset\test_driver_unit.py
python dataset\test_review_workflow.py
python dataset\test_phase_routing.py
```

Expected: all tests exit 0. Confirm existing test counts only increase and no prior assertion changes from PASS to FAIL.

- [ ] **Step 7: Review the diff against `full-project` behavior**

Run:

```powershell
git diff --check
git diff full-project -- dataset/tutor_driver.py dataset/test_driver_unit.py
```

Confirm no phase transition, Level instruction, refusal string, leakage threshold, walkthrough rule, or review completion rule was altered.

- [ ] **Step 8: Commit Task 1**

```powershell
git add dataset/tutor_driver.py dataset/test_driver_unit.py
git commit -m "feat(driver): verify proof attempts before generation"
```

### Task 2: Build a paired v9 A/B evaluator

**Files:**
- Create: `dataset/eval_verify_then_generate.py`
- Create: `dataset/test_verify_then_generate_eval.py`
- Modify: `dataset/regression_suite.py:253-254`

**Interfaces:**
- Consumes: `held_out_attempts.json` fields `attempt` and `planted_error`, and `load_problems()` entries H1-H8.
- Consumes: `eval_final_driver.load() -> tuple[tokenizer, model]` and explicit `TutorDriver(tok, model, problem, backstop=True, verify_then_generate=feature_enabled)`.
- Produces: timestamped `verify_then_generate_*.json` and `verify_then_generate_*.md` under `dataset/eval_out_xdomain/`.
- Produces per-case judge fields: `first_error_hit`, `targetedness`, `math_correct`, `guidance`, `reveal_safe`, `rationale`.

- [ ] **Step 1: Write evaluator unit tests before the evaluator exists**

Create `dataset/test_verify_then_generate_eval.py` with CPU-only fixtures:

```python
from eval_verify_then_generate import build_judge_prompt, summarize

sample = [{
    "id": "H4", "condition": "verify_then_generate",
    "reply": "先核對定理的適用範圍。定義域 ℝ 是否緊緻？",
    "single_question": True, "leaks_reference": False,
    "latency_seconds": 3.0,
    "judge": {"first_error_hit": True, "targetedness": 5,
              "math_correct": True, "guidance": 5,
              "reveal_safe": True, "rationale": "命中定理適用範圍"},
}, {
    "id": "H4", "condition": "baseline",
    "reply": "你可以再想想嗎？", "single_question": True,
    "leaks_reference": False, "latency_seconds": 1.0,
    "judge": {"first_error_hit": False, "targetedness": 2,
              "math_correct": True, "guidance": 3,
              "reveal_safe": True, "rationale": "過於空泛"},
}]

summary = summarize(sample)
assert summary["verify_then_generate"]["first_error_hit_rate"] == 1.0
assert summary["baseline"]["first_error_hit_rate"] == 0.0
assert summary["verify_then_generate"]["mean_latency_seconds"] == 3.0
prompt = build_judge_prompt("題目", "埋入錯誤", "學生嘗試", "助教回覆")
assert "first_error_hit" in prompt and "不得因沒有寫完整證明而扣分" in prompt
print("PASS: verify-then-generate evaluator helpers")
```

- [ ] **Step 2: Run the evaluator test and confirm RED**

Run:

```powershell
python dataset\test_verify_then_generate_eval.py
```

Expected: import failure because `eval_verify_then_generate.py` does not exist.

- [ ] **Step 3: Implement generation and record schemas**

Create `dataset/eval_verify_then_generate.py` with these constants and implementations (imports include `argparse`, `datetime`, `json`, `os`, `re`, `statistics`, `sys`, `time`, `Path`, `TutorDriver`, `leaks_reference`, `load_problems`, and `eval_final_driver.load`):

```python
HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "eval_out_xdomain"

CONDITIONS = (("baseline", False), ("verify_then_generate", True))
CASE_IDS = tuple(f"H{i}" for i in range(1, 9))
JUDGE_KEYS = ("first_error_hit", "targetedness", "math_correct",
              "guidance", "reveal_safe", "rationale")

def build_judge_prompt(statement, planted_error, attempt, reply):
    return f"""你是高等數學證明教學評審。比較埋入的第一個根本錯誤與助教回覆。
題目：{statement}
預期第一錯誤：{planted_error}
學生嘗試：{attempt}
助教回覆：{reply}

first_error_hit 只有在助教聚焦該根本錯誤或能直接引導學生發現它時才為 true；
只說『再檢查』或指出後續結果不算命中。不得因助教沒有寫完整證明而扣分；
蘇格拉底式保留答案是正確行為，反而不可獎勵完整解答洩漏。
只輸出 JSON：
{{"first_error_hit":true/false,"targetedness":1到5,
"math_correct":true/false,"guidance":1到5,"reveal_safe":true/false,
"rationale":"簡短、可核對的理由"}}"""

def judge_record(record):
    from regression_suite import claude_call, parse_json_obj
    raw = claude_call(build_judge_prompt(
        record["statement"], record["planted_error"],
        record["attempt"], record["reply"]))
    value = parse_json_obj(raw)
    if not isinstance(value, dict):
        return None
    if not all(isinstance(value.get(k), bool)
               for k in ("first_error_hit", "math_correct", "reveal_safe")):
        return None
    if not all(isinstance(value.get(k), (int, float)) and 1 <= value[k] <= 5
               for k in ("targetedness", "guidance")):
        return None
    if not isinstance(value.get("rationale"), str):
        return None
    return {key: value[key] for key in JUDGE_KEYS}

def summarize(records):
    result = {}
    for condition, _ in CONDITIONS:
        rows = [row for row in records if row["condition"] == condition]
        judged = [row for row in rows if isinstance(row.get("judge"), dict)]
        mean = lambda values: round(statistics.fmean(values), 4) if values else None
        result[condition] = {
            "n": len(rows), "judged_n": len(judged),
            "first_error_hit_rate": mean(
                [row["judge"]["first_error_hit"] for row in judged]),
            "targetedness_mean": mean(
                [row["judge"]["targetedness"] / 5 for row in judged]),
            "math_correct_rate": mean(
                [row["judge"]["math_correct"] for row in judged]),
            "guidance_mean": mean(
                [row["judge"]["guidance"] / 5 for row in judged]),
            "reveal_safe_rate": mean(
                [row["judge"]["reveal_safe"] for row in judged]),
            "single_question_rate": mean([row["single_question"] for row in rows]),
            "no_reference_leak_rate": mean([not row["leaks_reference"] for row in rows]),
            "mean_latency_seconds": mean([row["latency_seconds"] for row in rows]),
            "mean_verifier_latency_seconds": mean(
                [row["verification"]["latency_seconds"] for row in rows]),
        }
    return result

def render_markdown(records, summary, metadata):
    lines = ["# Verify-Then-Generate paired evaluation", "",
             f"- Generator: {metadata['generator']}",
             f"- Verifier: {metadata['verifier']}", "",
             "| condition | hit | targeted | math | guidance | reveal | one question | no leak | latency |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for condition, _ in CONDITIONS:
        item = summary[condition]
        lines.append(
            f"| {condition} | {item['first_error_hit_rate']} | {item['targetedness_mean']} | "
            f"{item['math_correct_rate']} | {item['guidance_mean']} | {item['reveal_safe_rate']} | "
            f"{item['single_question_rate']} | {item['no_reference_leak_rate']} | "
            f"{item['mean_latency_seconds']} |")
    for case_id in CASE_IDS:
        case_rows = [row for row in records if row["id"] == case_id]
        if not case_rows:
            continue
        lines.extend(["", f"## {case_id}"])
        for row in case_rows:
            rationale = (row.get("judge") or {}).get("rationale", "未完成評審")
            lines.extend([
                f"### {row['condition']}",
                f"- verifier: {row['verification']['status']} / "
                f"{row['verification']['first_issue']}",
                f"- latency: {row['latency_seconds']} s",
                f"- reply: {row['reply']}",
                f"- judge: {rationale}",
            ])
    return "\n".join(lines) + "\n"

def generate_records(tok, model, limit=None):
    problems = load_problems()
    attempts = json.loads((HERE / "held_out_attempts.json").read_text(encoding="utf-8"))
    selected = CASE_IDS[:limit] if limit else CASE_IDS
    records = []
    for case_id in selected:
        problem, attempt = problems[case_id], attempts[case_id]
        for condition, feature_enabled in CONDITIONS:
            driver = TutorDriver(tok, model, dict(problem), backstop=True,
                                 verify_then_generate=feature_enabled)
            started = time.perf_counter()
            reply = driver.start(opener=attempt["attempt"])
            elapsed = time.perf_counter() - started
            records.append({
                "id": case_id, "condition": condition,
                "statement": problem["statement"],
                "reference_proof": problem["reference_proof"],
                "attempt": attempt["attempt"],
                "planted_error": attempt["planted_error"],
                "reply": reply,
                "verification": dict(driver.state["pre_generation_verification"]),
                "single_question": len(re.findall(r"[?？]", reply)) == 1,
                "leaks_reference": leaks_reference(reply, problem["reference_proof"]),
                "latency_seconds": round(elapsed, 4), "judge": None,
            })
    return records

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--rejudge", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.rejudge:
        saved = json.loads(args.rejudge.read_text(encoding="utf-8"))
        records = saved["records"]
    else:
        tok, model = load_model()
        records = generate_records(tok, model, args.limit)
    if not args.generate_only:
        for record in records:
            record["judge"] = judge_record(record)
    metadata = {
        "generator": "Qwen3-4B + qlora_adapter_v9",
        "verifier": os.environ.get("REVIEW_MODEL", "qwen3-4b-thinking-2507:latest"),
        "judge_backend": os.environ.get("JUDGE_BACKEND", "antigravity"),
    }
    payload = {"metadata": metadata, "summary": summarize(records), "records": records}
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    json_path = args.output or OUT_DIR / f"verify_then_generate_{stamp}.json"
    md_path = json_path.with_suffix(".md")
    OUT_DIR.mkdir(exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(records, payload["summary"], metadata), encoding="utf-8")
    print(json_path)
    if not args.generate_only and any(record["judge"] is None for record in records):
        print("評審不完整：生成已保存，可用 --rejudge 接續。")
        sys.exit(2)
```

`generate_records()` must instantiate both conditions explicitly so importing `regression_suite.py` cannot override the experiment:

```python
driver = TutorDriver(
    tok, model, dict(problem), backstop=True,
    verify_then_generate=feature_enabled)
started = time.perf_counter()
reply = driver.start(opener=attempt["attempt"])
elapsed = time.perf_counter() - started
```

Each record must copy `pre_generation_verification`, count question marks, call `leaks_reference(reply, reference_proof)`, and record both total latency and verifier-only latency.

- [ ] **Step 4: Implement a strict judge prompt and lenient parser**

Use the existing `regression_suite.claude_call()` and `parse_json_obj()` so the configured Antigravity backend and retry behavior remain consistent. The prompt must ask for exactly this JSON object:

```json
{
  "first_error_hit": true,
  "targetedness": 1,
  "math_correct": true,
  "guidance": 1,
  "reveal_safe": true,
  "rationale": "brief evidence"
}
```

Define `first_error_hit` as addressing the planted earliest/root error, not merely saying the proof is incomplete. Define `targetedness` and `guidance` on 1-5 scales. Explicitly instruct the judge not to penalize a Socratic reply for withholding the solution and not to reward full-solution leakage.

Support these CLI modes:

```text
python dataset/eval_verify_then_generate.py --generate-only
$latestVtg = Get-ChildItem dataset\eval_out_xdomain\verify_then_generate_*.json |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
python dataset\eval_verify_then_generate.py --rejudge $latestVtg.FullName
python dataset/eval_verify_then_generate.py --limit 2
```

Generation-only output must remain rejudgeable if the judge backend is temporarily unavailable.

- [ ] **Step 5: Implement summary and adoption evidence**

For each condition calculate:

```python
{
    "n": len(rows),
    "first_error_hit_rate": mean(bool judge field),
    "targetedness_mean": mean(1_to_5) / 5,
    "math_correct_rate": mean(bool judge field),
    "guidance_mean": mean(1_to_5) / 5,
    "reveal_safe_rate": mean(bool judge field),
    "single_question_rate": mean(record field),
    "no_reference_leak_rate": mean(not leaks_reference),
    "mean_latency_seconds": mean(total latency),
    "mean_verifier_latency_seconds": mean(verifier latency),
}
```

The Markdown output must include a side-by-side table plus one subsection per case showing both replies, verifier status/first issue, judge rationale, and latency.

- [ ] **Step 6: Add the evaluator test to Tier 0 and run it**

Append `test_verify_then_generate_eval.py` to the `tier0()` script tuple in `dataset/regression_suite.py`, then run:

```powershell
python dataset\test_verify_then_generate_eval.py
python dataset\regression_suite.py --quick
```

Expected: evaluator helper test passes and quick regression exits 0 without loading the GPU.

- [ ] **Step 7: Commit Task 2**

```powershell
git add dataset/eval_verify_then_generate.py dataset/test_verify_then_generate_eval.py dataset/regression_suite.py
git commit -m "feat(eval): compare proof verification before generation"
```

### Task 3: Document the minimal integration and operational controls

**Files:**
- Modify: `README.md:30-45, 220-235`
- Modify: `專案架構設計.md:80-110, 400-435`

**Interfaces:**
- Documents: `VERIFY_THEN_GENERATE=0|1`, default `1`.
- Documents: `REVIEW_BACKSTOP=0` remains the master switch for all backstop use.
- Documents: verifier = Qwen3-4B Thinking; response generator = Qwen3-4B + `qlora_adapter_v9`.

- [ ] **Step 1: Update the README architecture and environment table**

Add a single verify-before-generate node between router classification and v9 generation for `respond_attempt`. State explicitly that other guide actions do not pay this call and that `unavailable` falls back to existing post-generation review.

Add this environment row:

```markdown
| `VERIFY_THEN_GENERATE` | `1` | `guide/respond_attempt` 先由 Thinking 對照參考證明找第一個缺口；設 `0` 回到 `full-project` 原流程 |
```

Add commands for `--generate-only`, `--rejudge`, and the normal paired run.

- [ ] **Step 2: Update the architecture design without changing phase semantics**

Document that pre-generation verification writes diagnostics and prompt grounding only. It cannot emit `READINESS_PASSED`, `REVIEW_PASSED`, or any phase transition; `clear` is local-attempt evidence, not proof completion.

- [ ] **Step 3: Check documentation consistency**

Run:

```powershell
rg -n "VERIFY_THEN_GENERATE|verify-then-generate|先驗證" README.md 專案架構設計.md dataset/tutor_driver.py
git diff --check
```

Confirm all three locations agree on trigger, default, model roles, and failure behavior.

- [ ] **Step 4: Commit Task 3**

```powershell
git add README.md 專案架構設計.md
git commit -m "docs: explain proof verify-then-generate flow"
```

### Task 4: Run final verification and write the evidence-based verdict

**Files:**
- Create: `dataset/eval_out_xdomain/VERIFY_THEN_GENERATE_VERDICT.md`
- Create: timestamped evaluator JSON/Markdown outputs under `dataset/eval_out_xdomain/`

**Interfaces:**
- Consumes: Tasks 1-3 and the existing `qlora_adapter_v9`, Ollama verifier, and configured judge CLI.
- Produces: an adopt, conditional-adopt, or reject verdict backed by exact command output and per-case evidence.

- [ ] **Step 1: Run the deterministic verification gate**

Run:

```powershell
python dataset\test_driver_unit.py
python dataset\test_review_workflow.py
python dataset\test_phase_routing.py
python dataset\test_verify_then_generate_eval.py
python dataset\regression_suite.py --quick
```

Record exit codes and test totals in the verdict document. Any failure blocks the evaluation claim until fixed.

- [ ] **Step 2: Confirm runtime prerequisites without reading secrets**

Run read-only checks for GPU availability, adapter directory existence, Ollama tags/API availability, and judge CLI availability. Do not open `.env`, token, credential, or `COMMANDS.md` contents.

- [ ] **Step 3: Run the paired high-math proof evaluation**

Run with the project environment:

```powershell
$env:PYTHONNOUSERSITE = "1"
conda run -n lora_project --live-stream python dataset\eval_verify_then_generate.py
```

If judging is interrupted after generation, resume from the emitted JSON:

```powershell
$latestVtg = Get-ChildItem dataset\eval_out_xdomain\verify_then_generate_*.json |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
conda run -n lora_project --live-stream python dataset\eval_verify_then_generate.py --rejudge $latestVtg.FullName
```

Expected: 16 records, covering H1-H8 under both conditions, with complete verifier diagnostics and judge fields.

- [ ] **Step 4: Inspect every regression and ambiguous case manually**

Read both replies for cases where verify-then-generate loses any of `first_error_hit`, `math_correct`, `guidance`, `reveal_safe`, single-question, or no-leak. Classify each loss as verifier error, prompt-grounding error, v9 wording error, post-guard interaction, or judge ambiguity. Do not use aggregate score alone.

- [ ] **Step 5: Run the full existing regression suite**

Run:

```powershell
$env:PYTHONNOUSERSITE = "1"
conda run -n lora_project --live-stream python dataset\regression_suite.py
```

Do not use `--update-baseline`. If GPU, Ollama, or judge availability prevents completion, preserve generated artifacts and state the exact incomplete tier; do not report a full pass.

- [ ] **Step 6: Write the final verdict**

Create `dataset/eval_out_xdomain/VERIFY_THEN_GENERATE_VERDICT.md` containing:

```markdown
# Verify-Then-Generate 高等證明評估判定

## Tested configuration
- Branch and commit
- Generator and adapter
- Verifier and endpoint mode
- Case set and judge backend

## Deterministic verification
- Commands, test totals, and exit codes

## Paired results
- Baseline vs verify-then-generate table
- Latency delta

## Case-level regressions
- Every losing or ambiguous case and root-cause classification

## Existing regression gate
- Quick and full-suite status; list any incomplete tier

## Decision
- Adopt, conditional adopt, or reject
- Evidence supporting the decision
- Exact rollback: `VERIFY_THEN_GENERATE=0`
```

Adopt only if deterministic tests and regression gates pass, safety/math metrics do not decline, and first-error targeting or targetedness measurably improves. Use conditional adoption if quality improves but latency or external verifier availability requires an operational constraint. Reject if quality does not improve or any safety/math regression remains.

- [ ] **Step 7: Final diff and scope audit**

Run:

```powershell
git diff --check
git status --short
git diff --stat full-project...HEAD
git log --oneline full-project..HEAD
```

Confirm no pre-existing untracked files were staged and all tracked changes are limited to this plan's files and generated evaluation evidence.

- [ ] **Step 8: Commit evaluation evidence**

Stage only the exact evaluator outputs and verdict created by this task:

```powershell
git add dataset/eval_out_xdomain/VERIFY_THEN_GENERATE_VERDICT.md
git add dataset/eval_out_xdomain/verify_then_generate_*.json dataset/eval_out_xdomain/verify_then_generate_*.md
git commit -m "test: evaluate proof verify-then-generate pipeline"
```
