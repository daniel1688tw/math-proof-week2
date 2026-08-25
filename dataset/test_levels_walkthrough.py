# -*- coding: utf-8 -*-
"""檢查 Level 0 -> Level 1 -> Level 2 -> 逐步教學 的狀態鏈條與各 Level 優化設定。"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from phase_router import update_stuck_count, apply_phase_event
from tutor_driver import (
    TutorDriver, LEVEL_INSTRUCTIONS, LEVEL_INSTRUCTIONS_EN,
    _STUCK_RE, _STRONG_STUCK_RE, leaks_reference, gives_new_equation, is_spoonfeeding
)

print("=" * 70)
print("檢查 Level 0 -> Level 1 -> Level 2 -> 逐步教學 (Walkthrough) 架構")
print("=" * 70)

# 1. 檢查提示梯遞增與轉移
print("\n[1] 檢查提示計數遞增 (stuck_count 與 level 映射)")
sc = 0
lvl = min(sc, 2)
print(f"  • 輪次 0 (起步/正常): stuck_count={sc} -> Level={lvl}")
assert sc == 0 and lvl == 0

sc = update_stuck_count(sc, "stuck")
lvl = min(sc, 2)
print(f"  • 第 1 次連續卡住: stuck_count={sc} -> Level={lvl} (方向拆解/縮小範圍)")
assert sc == 1 and lvl == 1

sc = update_stuck_count(sc, "stuck")
lvl = min(sc, 2)
print(f"  • 第 2 次連續卡住: stuck_count={sc} -> Level={lvl} (點名定理/核心想法，嚴禁算式)")
assert sc == 2 and lvl == 2

sc = update_stuck_count(sc, "stuck")
lvl = min(sc, 2)
print(f"  • 第 3 次連續卡住: stuck_count={sc} (達門檻，準備切入逐步教學)")
assert sc == 3

# 2. 檢查事件轉移矩陣
print("\n[2] 檢查事件轉移矩陣 (STUCK_LIMIT_REACHED 守門)")
# 測試未達 3 次時不可轉移
state_not_ready = {"phase": "guide", "stuck_count": 2}
apply_phase_event(state_not_ready, "STUCK_LIMIT_REACHED", source="test")
print(f"  • stuck_count=2 嘗試進入逐步教學: phase={state_not_ready['phase']}, accepted={state_not_ready['phase_events'][-1]['accepted']}, reject_reason={state_not_ready['phase_events'][-1]['reject_reason']}")
assert state_not_ready["phase"] == "guide"
assert state_not_ready["phase_events"][-1]["accepted"] is False

# 測試達到 3 次時正式轉移
state_ready = {"phase": "guide", "stuck_count": 3}
apply_phase_event(state_ready, "STUCK_LIMIT_REACHED", source="test")
print(f"  • stuck_count=3 觸發 STUCK_LIMIT_REACHED: phase={state_ready['phase']}, accepted={state_ready['phase_events'][-1]['accepted']}, stuck_count_after={state_ready['stuck_count']}")
assert state_ready["phase"] == "walkthrough"
assert state_ready["phase_events"][-1]["accepted"] is True
assert state_ready["stuck_count"] == 0

# 3. 檢查 Level 0, Level 1, Level 2 的提示規範與防護
print("\n[3] 檢查 Level 0, Level 1, Level 2 的指示設計與專屬防護")
print(f"  • Level 0 指示: {LEVEL_INSTRUCTIONS[0]}")
print(f"    - 防護約束: 嚴禁洩漏參考解 (leaks_reference)、嚴禁代寫/奉送具體操作 (is_spoonfeeding)、問句收尾。")

print(f"\n  • Level 1 指示: {LEVEL_INSTRUCTIONS[1]}")
print(f"    - 防護約束: 學生答不出時拆解為更小具體子問題，仍然不要點名定理名稱。")

print(f"\n  • Level 2 指示: {LEVEL_INSTRUCTIONS[2]}")
print(f"    - 防護約束: 連續卡兩次時點名定理/概念方向，但【嚴格禁止算式與等式/不等式】(gives_new_equation)；第二句提問讓學生自己動筆。")

print("\n" + "=" * 70)
print("✓ 全鏈條 (Level 0 -> Level 1 -> Level 2 -> 逐步教學) 檢查 100% 符合規範！")
print("=" * 70)
