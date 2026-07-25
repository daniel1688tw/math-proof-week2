# -*- coding: utf-8 -*-
"""test_app.py — 商品化介面純邏輯單元測試（不載模型、不連 Ollama、不需 GPU）。

跑法：python dataset/test_app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import auto_reference

FAIL = []


def check(name, cond):
    print(("  ✓ " if cond else "  ✗ ") + name)
    if not cond:
        FAIL.append(name)


def _fake_chat_pass(system, user, temperature, timeout=600):
    if "標準參考解" in system:            # PROVER_SYSTEM
        return "證明：由假設可得結論。$\\blacksquare$"
    if "驗證員" in system:                # VERIFIER_SYSTEM
        return '{"verdict": "pass", "issues": []}'
    if "教學設計者" in system:            # SEGMENTER_SYSTEM
        return '[{"explain": "步驟一：套用定義", "check": "定義是什麼？"}]'
    return None


# ── Task 1: build_reference progress_cb ────────────────────────────────────
print("[1] build_reference progress_cb 回呼")
_orig_chat = auto_reference._chat
auto_reference._chat = _fake_chat_pass
try:
    events = []
    result = auto_reference.build_reference(
        "證明 1+1=2", k=1, verbose=False,
        progress_cb=lambda stage, detail="": events.append((stage, detail)),
    )
    stages = [s for s, _ in events]
    check("verified 狀態", result["status"] == "verified")
    check("PROVER 階段有觸發", "PROVER" in stages)
    check("VERIFIER 階段有觸發", "VERIFIER" in stages)
    check("SEGMENTER 階段有觸發", "SEGMENTER" in stages)

    result2 = auto_reference.build_reference("證明 1+1=2", k=1, verbose=False)
    check("不傳 progress_cb 仍向後相容", result2["status"] == "verified")
    check("參考解 $blacksquare$ 收尾", result2["reference_proof"].endswith("$\\blacksquare$"))
finally:
    auto_reference._chat = _orig_chat


# ── Task 2: app.py 純邏輯 ──────────────────────────────────────────────────
print("[2] app.py 純邏輯（assemble_problem / opener_for / check_ollama）")
import app  # import 不得載入模型（模型只在 app.main() 內載）
from tutor_driver import TutorDriver

_verified = {"status": "verified", "reference_proof": "P $\\blacksquare$",
             "teach_steps": [{"explain": "a", "check": "b"}], "log": []}
prob_v = app.assemble_problem("  證明 X  ", _verified)
check("verified：statement 有 strip", prob_v["statement"] == "證明 X")
check("verified：grounding=auto_verified", prob_v["grounding"] == "auto_verified")
check("verified：帶 reference_proof", prob_v["reference_proof"] == "P $\\blacksquare$")
check("verified：帶 teach_steps", bool(prob_v["teach_steps"]))

_unverified = {"status": "unverified", "log": []}
prob_u = app.assemble_problem("證明 Y", _unverified)
check("unverified：grounding=unverified", prob_u["grounding"] == "unverified")
check("unverified：無 reference_proof", "reference_proof" not in prob_u)
_d = TutorDriver.__new__(TutorDriver)
_d.problem = prob_u
check("unverified：is_peer() True", _d.is_peer() is True)

check("opener_for(None) → None", app.opener_for(None) is None)
check("opener_for(空白) → None", app.opener_for("   ") is None)
check("opener_for(證明) → strip 字串",
      app.opener_for("  我試著用歸納法  ") == "我試著用歸納法")
check("check_ollama(壞URL) → False（不拋例外）",
      app.check_ollama("http://127.0.0.1:1/nope", timeout=1) is False)

# _run_prepare：正常完成 → 最後 ('result', dict)
_orig_build = app.build_reference
app.build_reference = lambda statement, progress_cb=None: (
    progress_cb and progress_cb("PROVER", "1/1"),
    {"status": "unverified", "log": []})[1]
try:
    outs = list(app._run_prepare("證明 Z"))
    kinds = [k for k, _ in outs]
    check("_run_prepare 有 progress", "progress" in kinds)
    check("_run_prepare 末項為 result", outs[-1][0] == "result")
    check("_run_prepare result 內容正確", outs[-1][1]["status"] == "unverified")
finally:
    app.build_reference = _orig_build

# _run_prepare：worker 拋例外 → 不卡死，末項為 ('error', ...)
def _boom(statement, progress_cb=None):
    raise RuntimeError("備課炸了")
app.build_reference = _boom
try:
    outs = list(app._run_prepare("證明 boom"))
    check("_run_prepare 例外不卡死、末項為 error",
          outs[-1][0] == "error" and "備課炸了" in outs[-1][1])
finally:
    app.build_reference = _orig_build


print()
if FAIL:
    print(f"✗ {len(FAIL)} 項失敗：{FAIL}")
    sys.exit(1)
print("全部單元測試通過 ✓")
