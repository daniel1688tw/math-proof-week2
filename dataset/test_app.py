# -*- coding: utf-8 -*-
"""不需要 Ollama/GPU 的 app 與自動備課整合測試。"""
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
    print(("  OK " if cond else "  FAIL ") + name)
    if not cond:
        FAIL.append(name)


_STEPS = [
    {"step_id": "test-1", "explain": "先選取任意元素。",
     "core_idea": "選取任意元素", "check": "這裡要選取哪一類元素？",
     "expected_answer": "題目指定集合中的任意元素"},
    {"step_id": "test-2", "explain": "接著逐項確認定理前提。",
     "core_idea": "驗證定理前提", "check": "套用定理前必須先確認什麼？",
     "expected_answer": "定理的所有前提"},
    {"step_id": "test-3", "explain": "最後利用全稱量詞收束。",
     "core_idea": "收束全稱量詞", "check": "任意性如何導出最終結論？",
     "expected_answer": "結論對所有指定元素成立"},
]


def _fake_chat_pass(system, user, temperature, timeout=600, **kwargs):
    if system is auto_reference.PROVER_SYSTEM:
        return "證明：依定義即可得到結論。$\\blacksquare$"
    if system is auto_reference.VERIFIER_SYSTEM:
        return '{"verdict": "pass", "issues": []}'
    if system is auto_reference.SEGMENTER_SYSTEM:
        import json
        return json.dumps(_STEPS, ensure_ascii=False)
    if system is auto_reference.TEACH_STEPS_TRANSLATOR_SYSTEM:
        import json
        return json.dumps({"steps": _STEPS}, ensure_ascii=False)
    if system in (auto_reference.TEACH_STEPS_VERIFIER_SYSTEM,
                  auto_reference.TRANSLATED_STEPS_VERIFIER_SYSTEM):
        return '{"verdict": "pass", "issues": []}'
    return None


print("[1] build_reference progress_cb")
_orig_chat = auto_reference._chat
auto_reference._chat = _fake_chat_pass
try:
    events = []
    result = auto_reference.build_reference(
        "證明 1+1=2", k=1, verbose=False,
        progress_cb=lambda stage, detail="": events.append((stage, detail)),
    )
    stages = [s for s, _ in events]
    check("verified 成功", result["status"] == "verified")
    check("有 PROVER 事件", "PROVER" in stages)
    check("有 VERIFIER 事件", "VERIFIER" in stages)
    check("有 SEGMENTER 事件", "SEGMENTER" in stages)
    check("備課流程只產參考證明與逐步教學資料", set(stages) <= {"PROVER", "VERIFIER", "REPAIR", "SEGMENTER"})
    check("產出含 core_idea 的教學步驟", all(s.get("core_idea") for s in result["teach_steps"]))

    result2 = auto_reference.build_reference("證明 1+1=2", k=1, verbose=False)
    check("未提供 progress_cb 仍正常", result2["status"] == "verified")
    check("補上結尾證明符號", result2["reference_proof"].endswith("$\\blacksquare$"))
    result_en = auto_reference.build_reference("Prove that 1+1=2.", k=1, verbose=False)
    check("英文初次切分成功後立即建立中英文版本",
          bool(result_en.get("teach_steps_en")) and bool(result_en.get("teach_steps_zh")))
finally:
    auto_reference._chat = _orig_chat


print("[2] app.py 組裝")
import app
from tutor_driver import TutorDriver

_verified = {
    "status": "verified",
    "reference_proof": "P $\\blacksquare$",
    "teach_steps": _STEPS,
    "teach_steps_lang": "en",
    "teach_steps_en": _STEPS,
    "teach_steps_zh": _STEPS,
    "teach_steps_initial_status": "success",
    "log": [],
}
prob_v = app.assemble_problem("  證明 X  ", _verified)
check("statement 會 strip", prob_v["statement"] == "證明 X")
check("grounding=auto_verified", prob_v["grounding"] == "auto_verified")
check("保留 reference_proof", prob_v["reference_proof"] == "P $\\blacksquare$")
check("保留 teach_steps", bool(prob_v["teach_steps"]))
check("assemble_problem 保留中英文步驟快取",
      bool(prob_v["teach_steps_en"]) and bool(prob_v["teach_steps_zh"]))

_unverified = {"status": "unverified", "log": []}
prob_u = app.assemble_problem("證明 Y", _unverified)
check("unverified grounding", prob_u["grounding"] == "unverified")
check("unverified 不帶 reference_proof", "reference_proof" not in prob_u)
_d = TutorDriver.__new__(TutorDriver)
_d.problem = prob_u
check("unverified 進同學模式", _d.is_peer() is True)

check("opener_for(None)", app.opener_for(None) is None)
check("opener_for 空白", app.opener_for("   ") is None)
check("opener_for 會 strip", app.opener_for("  我不知道怎麼開始 ") == "我不知道怎麼開始")
check("check_ollama 錯誤 URL", app.check_ollama("http://127.0.0.1:1/nope", timeout=1) is False)

_orig_build = app.build_reference
app.build_reference = lambda statement, progress_cb=None: (
    progress_cb and progress_cb("PROVER", "1/1"),
    {"status": "unverified", "log": []},
)[1]
try:
    outs = list(app._run_prepare("證明 Z"))
    kinds = [k for k, _ in outs]
    check("_run_prepare 有 progress", "progress" in kinds)
    check("_run_prepare 最後是 result", outs[-1][0] == "result")
finally:
    app.build_reference = _orig_build


def _boom(statement, progress_cb=None):
    raise RuntimeError("測試錯誤")


app.build_reference = _boom
try:
    outs = list(app._run_prepare("證明 boom"))
    check("worker 例外回傳 error", outs[-1][0] == "error" and "測試錯誤" in outs[-1][1])
finally:
    app.build_reference = _orig_build

print()
if FAIL:
    print(f"FAIL: {len(FAIL)} 項：{FAIL}")
    sys.exit(1)
print("所有 app 整合測試通過")
