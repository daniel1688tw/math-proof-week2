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


print()
if FAIL:
    print(f"✗ {len(FAIL)} 項失敗：{FAIL}")
    sys.exit(1)
print("全部單元測試通過 ✓")
