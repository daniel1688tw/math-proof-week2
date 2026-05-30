"""
逐 stage 執行 pipeline 並顯示 LLM 生成結果供人工檢查。

用法：
    # 執行全部 6 個 stage（預設使用第一個 benchmark 題目）
    .\\env\\python.exe tests\\inspect_pipeline.py

    # 指定題目（0=chain_rule, 1=MVT, 2=IVT）
    .\\env\\python.exe tests\\inspect_pipeline.py --problem 1

    # 只跑到 Stage N 就停，之後的不跑
    .\\env\\python.exe tests\\inspect_pipeline.py --stop-after 3

    # 從 Stage N 繼續（讀取上次存的中間結果）
    .\\env\\python.exe tests\\inspect_pipeline.py --start-from 4

結果存到：
    week2_outputs/inspect/stageN_*.json   ← 各 stage 的原始輸出
    week2_outputs/inspect/report.md       ← 完整人工可讀報告（Markdown）
"""
import sys
import json
import argparse
from pathlib import Path

# Force UTF-8 stdout/stderr so all Unicode (Chinese, math symbols) prints correctly
# on Windows terminals that default to cp950/cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add week2 root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

INSPECT_DIR = Path("week2_outputs/inspect")
REPORT_FILE = INSPECT_DIR / "report.md"


def setup():
    INSPECT_DIR.mkdir(parents=True, exist_ok=True)


def banner(text, char="═"):
    line = char * 60
    print(f"\n{line}")
    print(f"  {text}")
    print(line)


def section(title):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")


def save_stage(name, data):
    path = INSPECT_DIR / f"{name}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → 已存：{path}")
    return path


def load_stage(name):
    path = INSPECT_DIR / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def append_report(text):
    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def init_report(problem_id):
    REPORT_FILE.write_text(
        f"# Pipeline 檢查報告\n\n題目：{problem_id}\n\n", encoding="utf-8")


# ── Stage 1: Problem Parser ──────────────────────────────────────────────────

def run_stage1(raw_problem):
    banner("Stage 1 — Problem Parser（問題解析）")
    print("  正在呼叫 LLM 解析題目結構...")

    import generators
    result = generators.generate_problem_json(raw_problem)

    section("LLM 生成的 problem_json")
    goal = result.get("goal", {})
    print(f"  problem_id : {result.get('problem_id')}")
    print(f"  目標(text) : {goal.get('text')}")
    print(f"  目標(symbolic): {goal.get('symbolic')}")

    assumptions = result.get("assumptions", [])
    print(f"\n  假設（共 {len(assumptions)} 條）：")
    for a in assumptions:
        stmt = a.get("statement", a) if isinstance(a, dict) else a
        aid  = a.get("id", "?")   if isinstance(a, dict) else "?"
        print(f"    [{aid}] {stmt}")

    variables = result.get("variables", [])
    print(f"\n  變數（共 {len(variables)} 個）：", end=" ")
    syms = [v.get("symbol", v) if isinstance(v, dict) else v for v in variables]
    print(", ".join(str(s) for s in syms))

    hidden = result.get("hidden_conditions", [])
    if hidden:
        print(f"\n  隱藏條件（共 {len(hidden)} 條）：")
        for h in hidden:
            stmt = h.get("statement", h) if isinstance(h, dict) else h
            print(f"    {stmt}")

    print(f"\n  來源：{result.get('_generation_source')}  "
          f"嘗試次數：{result.get('_generation_attempts')}")

    save_stage("stage1_problem_json", result)

    append_report(
        f"## Stage 1 — Problem Parser\n\n"
        f"- **problem_id**: {result.get('problem_id')}\n"
        f"- **目標 (text)**: {goal.get('text')}\n"
        f"- **目標 (symbolic)**: `{goal.get('symbolic')}`\n"
        f"- **假設**: {[a.get('statement', a) if isinstance(a, dict) else a for a in assumptions]}\n"
        f"- **變數**: {syms}\n\n"
    )

    print("\n  [OK] Stage 1 完成。請檢查以上內容是否正確解析了題意。\n")
    return result


# ── Stage 2: Contract Builder ────────────────────────────────────────────────

def run_stage2(problem_json):
    banner("Stage 2 — Contract Builder（合約建立）")
    print("  正在呼叫 LLM 生成 proof_contract...")

    import generators
    result = generators.generate_proof_contract(problem_json)

    section("LLM 生成的 proof_contract")
    obligations = result.get("obligations", [])
    print(f"  義務（共 {len(obligations)} 條）：")
    for ob in obligations:
        print(f"    [{ob.get('id')}] {ob.get('description')}  [{ob.get('status')}]")

    allowed = result.get("allowed_references", [])
    print(f"\n  允許引用（共 {len(allowed)} 個）：")
    print(f"    {', '.join(allowed)}")

    forbidden = result.get("forbidden_moves", [])
    if forbidden:
        print(f"\n  禁止動作：{', '.join(forbidden)}")

    rubric = result.get("acceptance_rubric", [])
    if rubric:
        print(f"\n  驗收標準：")
        for r in rubric:
            print(f"    • {r}")

    print(f"\n  來源：{result.get('_generation_source')}  "
          f"嘗試次數：{result.get('_generation_attempts')}")

    save_stage("stage2_proof_contract", result)

    append_report(
        f"## Stage 2 — Contract Builder\n\n"
        f"**義務 (obligations)**:\n" +
        "".join(f"- [{ob.get('id')}] {ob.get('description')}\n" for ob in obligations) +
        f"\n**允許引用**: {', '.join(allowed)}\n\n"
    )

    print("\n  [OK] Stage 2 完成。請檢查義務是否完整涵蓋了證明所需步驟。\n")
    return result


# ── Stage 3: Graph Planner ───────────────────────────────────────────────────

def run_stage3(problem_json, proof_contract):
    banner("Stage 3 — Graph Planner（圖骨架規劃）")
    print("  正在呼叫 LLM 生成 proof_graph_state 骨架...")

    import generators
    result = generators.generate_graph_skeleton(problem_json, proof_contract)

    section("LLM 生成的 proof_graph_state")
    nodes = result.get("nodes", [])
    goal_id = result.get("goal_node_id", "(未設定)")
    print(f"  goal_node_id：{goal_id}")
    print(f"\n  節點（共 {len(nodes)} 個）：")
    for node in nodes:
        marker = " ← GOAL" if node.get("id") == goal_id else ""
        covers = node.get("covers_obligations", [])
        covers_str = f"  覆蓋: {covers}" if covers else ""
        print(f"    [{node.get('id')}] ({node.get('node_type')}) "
              f"\"{node.get('claim')}\"{marker}{covers_str}")

    inferences = result.get("inferences", [])
    print(f"\n  推理（共 {len(inferences)} 條）：")
    for inf in inferences:
        premises = " + ".join(inf.get("premise_nodes", []))
        sides    = inf.get("side_condition_nodes", [])
        side_str = f" [{', '.join(sides)}]" if sides else ""
        rules    = ", ".join(inf.get("rule_refs", []))
        print(f"    {inf.get('id')}: {premises}{side_str} → {inf.get('conclusion_node')}  "
              f"(rule: {rules})")

    print(f"\n  來源：{result.get('_generation_source')}  "
          f"嘗試次數：{result.get('_generation_attempts')}")

    save_stage("stage3_graph_skeleton", result)

    node_lines = "".join(
        f"- [{n.get('id')}] ({n.get('node_type')}) {n.get('claim')}"
        + (" ← GOAL\n" if n.get("id") == goal_id else "\n")
        for n in nodes
    )
    inf_lines = "".join(
        f"- {i.get('id')}: {' + '.join(i.get('premise_nodes',[]))} → "
        f"{i.get('conclusion_node')} (rule: {', '.join(i.get('rule_refs',[]))})\n"
        for i in inferences
    )
    append_report(
        f"## Stage 3 — Graph Planner\n\n"
        f"**goal_node_id**: {goal_id}\n\n"
        f"**節點**:\n{node_lines}\n"
        f"**推理**:\n{inf_lines}\n"
    )

    print("\n  [OK] Stage 3 完成。請檢查：\n"
          "    • 節點數量是否合理？\n"
          "    • 推理鏈能否從假設節點到達 goal 節點？\n"
          "    • goal_node_id 是否正確指向終點？\n")
    return result


# ── Stage 4: Graph Prover ────────────────────────────────────────────────────

def run_stage4(problem_json, proof_contract, graph_state):
    banner("Stage 4 — Graph Prover（逐節點證明）")
    print("  正在呼叫 LLM 為每個非 source 節點生成 proof_body...")

    from graph_planner import graph_prover
    result = graph_prover(problem_json, proof_contract, graph_state)

    section("各節點的 proof_body")
    for node in result.get("nodes", []):
        ntype = node.get("node_type")
        if ntype in {"assumption", "allowed_reference"}:
            print(f"\n  [{node['id']}] ({ntype}) — source 節點，無需證明")
            continue
        steps = node.get("proof_body", {}).get("steps", [])
        print(f"\n  [{node['id']}] ({ntype}) claim: \"{node.get('claim')}\"")
        if not steps:
            print("    [!] 無 steps（生成失敗或為空）")
        else:
            for i, step in enumerate(steps, 1):
                stmt   = step.get("statement", "")
                reason = step.get("reason", "")
                refs   = step.get("refs", [])
                ref_str = f"  (refs: {refs})" if refs else ""
                print(f"    步驟 {i}: {stmt}")
                print(f"           理由: {reason}{ref_str}")

    save_stage("stage4_proven_graph", result)

    # Build report section
    node_sections = []
    for node in result.get("nodes", []):
        if node.get("node_type") in {"assumption", "allowed_reference"}:
            continue
        steps = node.get("proof_body", {}).get("steps", [])
        step_lines = "".join(
            f"  {i}. {s.get('statement')} _(reason: {s.get('reason')})_\n"
            for i, s in enumerate(steps, 1)
        )
        fallback = "  (無 steps)\n"
        node_sections.append(
            f"**[{node['id']}]** {node.get('claim')}\n\n{step_lines or fallback}"
        )
    append_report(
        f"## Stage 4 — Graph Prover\n\n" + "\n".join(node_sections) + "\n"
    )

    print("\n  [OK] Stage 4 完成。請檢查：\n"
          "    • 每個步驟的邏輯是否正確？\n"
          "    • 理由（reason）是否引用了合法的定理？\n"
          "    • 最後一步是否確實推出了該節點的 claim？\n")
    return result


# ── Stage 5: Run Verifiers ───────────────────────────────────────────────────

def run_stage5(problem_json, proof_contract, proven_graph):
    banner("Stage 5 — Run Verifiers（驗證器）")
    print("  正在執行所有 verifier...")

    from verifiers import run_all_verifiers
    result = run_all_verifiers(problem_json, proof_contract, proven_graph)

    errors = result["errors"]
    agg    = result["aggregator"]

    section("Verifier 結果")
    accepted = agg.get("all_required_pass", False)
    print(f"  最終判定：{'[PASS] 通過 (accepted=True)' if accepted else '[FAIL] 未通過 (accepted=False)'}")
    print(f"  錯誤總數：{len(errors)}")

    # Group by severity
    for sev in ["high", "medium", "low"]:
        sev_errors = [e for e in errors if e.get("severity") == sev]
        if not sev_errors:
            continue
        label = {"high": "[HIGH] HIGH（阻斷）", "medium": "[MED] MEDIUM（非阻斷）", "low": "[ - ] LOW"}.get(sev, sev)
        print(f"\n  {label} — {len(sev_errors)} 個：")
        for e in sev_errors:
            nid = e.get("node_id", "—")
            src = e.get("source", "")
            print(f"    [{e['error_id']}] node={nid}  source={src}")
            print(f"      claim   : {e.get('claim', '')[:80]}")
            print(f"      evidence: {e.get('evidence', '')[:100]}")
            print(f"      fix     : {e.get('required_fix', '')[:80]}")

    section("Obligation 狀態")
    obs = result["annotated_graph_state"].get("obligation_status", [])
    for ob in obs:
        status_icon = "[pass]" if ob.get("status") == "pass" else "[FAIL]"
        print(f"  {status_icon} [{ob.get('id')}] {ob.get('description')}  → {ob.get('status')}")

    save_stage("stage5_verifier_result", {
        "errors": errors,
        "aggregator": agg,
        "obligation_status": obs,
    })

    # Build report
    err_lines = "".join(
        f"- [{e['error_id']}] **{e.get('severity').upper()}** ({e.get('source')}) "
        f"node={e.get('node_id','—')}: {e.get('evidence','')[:100]}\n"
        for e in errors
    )
    ob_lines = "".join(
        f"- {'✅' if o.get('status')=='pass' else '❌'} [{o.get('id')}] {o.get('description')} → {o.get('status')}\n"
        for o in obs
    )
    append_report(
        f"## Stage 5 — Verifiers\n\n"
        f"**結果**: {'ACCEPTED' if accepted else 'REJECTED'}  |  "
        f"錯誤數: {len(errors)}\n\n"
        f"**錯誤列表**:\n{err_lines or '(無錯誤)'}\n\n"
        f"**Obligation 狀態**:\n{ob_lines}\n"
    )

    print(f"\n  [OK] Stage 5 完成。請檢查：\n"
          f"    • HIGH 錯誤是否是真正的邏輯問題？還是 verifier 誤判？\n"
          f"    • Obligation 是否都被對應節點的 proof_body 覆蓋？\n")
    return result


# ── Stage 6: Export Trace ────────────────────────────────────────────────────

def run_stage6(state_so_far):
    banner("Stage 6 — Export Trace（輸出追蹤記錄）")

    from langgraph_nodes import export_trace_node
    partial_state = {
        "trace": state_so_far.get("trace", []),
        "accepted": state_so_far.get("accepted", False),
    }
    result = export_trace_node(partial_state)

    section("完整 trace")
    for entry in result.get("trace", []):
        node = entry.get("node", "?")
        extra = {k: v for k, v in entry.items() if k != "node"}
        extra_str = "  " + str(extra) if extra else ""
        print(f"  → {node}{extra_str}")

    accepted = partial_state.get("accepted", False)
    print(f"\n  最終 accepted：{'[PASS] True' if accepted else '[FAIL] False'}")

    save_stage("stage6_trace", result)
    append_report(
        f"## Stage 6 — Export Trace\n\n"
        f"**accepted**: {accepted}\n\n"
        f"**trace entries**: {len(result.get('trace', []))}\n\n"
    )

    print("\n  [OK] Stage 6 完成。\n")
    return result


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="逐 stage 執行 pipeline 並顯示 LLM 輸出")
    parser.add_argument("--problem", type=int, default=0,
                        help="benchmark 題目索引：0=chain_rule, 1=MVT, 2=IVT（預設 0）")
    parser.add_argument("--stop-after", type=int, default=6,
                        help="跑到 stage N 後停止（預設 6，全跑）")
    parser.add_argument("--start-from", type=int, default=1,
                        help="從 stage N 開始（讀取之前存的中間結果）（預設 1）")
    args = parser.parse_args()

    setup()

    from benchmark import BENCHMARK_PROBLEMS
    prob = BENCHMARK_PROBLEMS[args.problem]
    raw_problem = prob["raw_problem"]
    problem_id  = prob["problem_id"]

    banner(f"Pipeline 檢查 — {problem_id}", "═")
    print(f"  題目：{raw_problem}")
    print(f"  執行 Stage {args.start_from} → {args.stop_after}")
    print(f"  結果存至：{INSPECT_DIR}/  |  報告：{REPORT_FILE}")

    if args.start_from == 1:
        init_report(problem_id)

    # 載入或生成各 stage 結果
    problem_json  = load_stage("stage1_problem_json")
    proof_contract = load_stage("stage2_proof_contract")
    graph_skeleton = load_stage("stage3_graph_skeleton")
    proven_graph   = load_stage("stage4_proven_graph")
    verifier_result = load_stage("stage5_verifier_result")

    # 執行選定的 stage 範圍
    if args.start_from <= 1 <= args.stop_after:
        problem_json = run_stage1(raw_problem)

    if args.start_from <= 2 <= args.stop_after:
        if problem_json is None:
            print("⚠ 缺少 stage1 結果，請先執行 --stop-after 1")
            sys.exit(1)
        proof_contract = run_stage2(problem_json)

    if args.start_from <= 3 <= args.stop_after:
        if problem_json is None or proof_contract is None:
            print("⚠ 缺少 stage1/2 結果，請先執行 --stop-after 2")
            sys.exit(1)
        graph_skeleton = run_stage3(problem_json, proof_contract)

    if args.start_from <= 4 <= args.stop_after:
        if graph_skeleton is None:
            print("⚠ 缺少 stage3 結果，請先執行 --stop-after 3")
            sys.exit(1)
        proven_graph = run_stage4(problem_json, proof_contract, graph_skeleton)

    if args.start_from <= 5 <= args.stop_after:
        if proven_graph is None:
            print("⚠ 缺少 stage4 結果，請先執行 --stop-after 4")
            sys.exit(1)
        verifier_result = run_stage5(problem_json, proof_contract, proven_graph)

    if args.start_from <= 6 <= args.stop_after:
        agg = verifier_result.get("aggregator", {}) if verifier_result else {}
        state = {"trace": [], "accepted": agg.get("all_required_pass", False)}
        run_stage6(state)

    banner("完成", "─")
    print(f"  人工可讀報告：{REPORT_FILE}")
    print(f"  各 stage JSON：{INSPECT_DIR}/\n")


if __name__ == "__main__":
    main()
