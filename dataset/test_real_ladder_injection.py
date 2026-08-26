# -*- coding: utf-8 -*-
"""驗證 TutorDriver 真正的提示梯 (Hint Ladder) 與教學步驟 (Teach Steps) 動態注入機制。

此測試不使用任何寫死劇本的 Mock，直接檢驗真實 TutorDriver 類別的 _system(level) 與
_get_ladder_hint(level) 邏輯，確保所有題目在 Level 0/1/2 都有明確的提示深度階梯。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tutor_driver import TutorDriver, load_problems


class _DummyModel:
    device = "cpu"


def test_hint_ladder_loading():
    print("[1] 測試 load_problems() 自動掛載 hint_ladders.json 與 hint_ladders_en.json...")
    problems = load_problems()
    
    # 檢查 H1 是否成功掛載中文與英文 ladder
    assert "H1" in problems, "H1 題必須存在於 problems 中"
    p_h1 = problems["H1"]
    assert "hint_ladder" in p_h1, "H1 必須包含 hint_ladder"
    assert len(p_h1["hint_ladder"]) >= 2, f"H1 hint_ladder 至少有 2 條提示，實際: {len(p_h1['hint_ladder'])}"
    assert "單一分式" in p_h1["hint_ladder"][0], "H1 第 1 條提示必須包含單一分式"
    assert "阿基米德" in p_h1["hint_ladder"][1], "H1 第 2 條提示必須包含阿基米德性質"
    
    # 檢查英文 ladder
    assert "hint_ladder_en" in p_h1, "H1 必須包含 hint_ladder_en"
    assert "Archimedean" in p_h1["hint_ladder_en"][1], "H1 英文第 2 條提示必須包含 Archimedean"
    print("  ✓ load_problems() 成功掛載中英文提示梯！")


def test_tutor_driver_ladder_injection():
    print("\n[2] 測試 TutorDriver 在 Level 0/1/2 的真實 System Prompt 注入深度...")
    problems = load_problems()
    p_h1 = problems["H1"]
    
    driver = TutorDriver(tok=None, model=_DummyModel(), problem=p_h1)
    
    # 測試 Level 0: 宏觀聚焦，不應在指示區塊注入具體梯子內容
    sys_0 = driver._system(0)
    instr_0 = sys_0.split("</REFERENCE_PROOF>")[-1]
    assert "單一分式" not in instr_0, "Level 0 指示不應提前洩漏具體梯子內容"
    assert "阿基米德" not in instr_0, "Level 0 指示不應提前洩漏關鍵定理名稱"
    assert "宏觀聚焦問題" in instr_0 or "只問一個" in instr_0, "Level 0 必須引導宏觀思考"
    print("  ✓ Level 0: 正確維持宏觀聚焦，無梯子內容提前洩漏。")
    
    # 測試 Level 1: 注入第 1 條梯子（局部方向拆解）
    sys_1 = driver._system(1)
    instr_1 = sys_1.split("</REFERENCE_PROOF>")[-1]
    assert "單一分式" in instr_1, "Level 1 必須成功注入第 1 條提示（單一分式）"
    assert "阿基米德" not in instr_1, "Level 1 仍不應洩漏第 2 條關鍵定理（阿基米德性質）"
    assert "請參考以下子問題方向" in instr_1 or "引導學生" in instr_1, "Level 1 必須包含子問題指示"
    print("  ✓ Level 1: 成功注入第 1 條提示方向（單一分式），維持局部支架。")
    
    # 測試 Level 2: 注入第 2 條梯子（關鍵突破口 / 定理點名）
    sys_2 = driver._system(2)
    instr_2 = sys_2.split("</REFERENCE_PROOF>")[-1]
    assert "阿基米德" in instr_2, "Level 2 必須成功注入關鍵破局定理（阿基米德性質）"
    assert "第一句明確點出關鍵方向或構造" in instr_2 or "關鍵方向" in instr_2, "Level 2 必須包含突破口指示"
    print("  ✓ Level 2: 成功注入關鍵破局提示（阿基米德性質）。")


def test_english_ladder_injection():
    print("\n[3] 測試英文 Session 下的提示梯動態注入...")
    problems = load_problems()
    p_h4 = problems["H4"]  # H4: 均值定理 / Lipschitz
    
    driver = TutorDriver(tok=None, model=_DummyModel(), problem=p_h4)
    driver.state["lang"] = "en"  # 切換為英文
    
    # Level 1 EN
    sys_1_en = driver._system(1)
    instr_1_en = sys_1_en.split("</REFERENCE_PROOF>")[-1]
    assert "mean value theorem" in instr_1_en.lower() or "links the difference" in instr_1_en.lower(), "英文 Level 1 必須注入第 1 條提示"
    
    # Level 2 EN
    sys_2_en = driver._system(2)
    instr_2_en = sys_2_en.split("</REFERENCE_PROOF>")[-1]
    assert "lipschitz" in instr_2_en.lower(), "英文 Level 2 必須注入關鍵突破口（Lipschitz）"
    print("  ✓ 英文 Session: 成功注入英文提示梯！")


def test_custom_ladder_injection():
    print("\n[4] 測試新題目／自訂題目自帶 hint_ladder 時的自動注入...")
    custom_prob = {
        "id": "CUSTOM_NEW_1",
        "statement": "證明某個性質...",
        "reference_proof": "參考證明全文...",
        "hint_ladder": [
            "利用柯西不等式將求和項放大",
            "利用夾擠定理取極限並驗證端點"
        ]
    }
    driver = TutorDriver(tok=None, model=_DummyModel(), problem=custom_prob)
    
    # Level 1 提取梯子第 1 階
    sys_1 = driver._system(1)
    instr_1 = sys_1.split("</REFERENCE_PROOF>")[-1]
    assert "柯西不等式" in instr_1, "Level 1 應自動注入 hint_ladder 第 1 階"
    
    # Level 2 提取梯子第 2 階
    sys_2 = driver._system(2)
    instr_2 = sys_2.split("</REFERENCE_PROOF>")[-1]
    assert "夾擠定理" in instr_2, "Level 2 應自動注入 hint_ladder 第 2 階"
    print("  ✓ 自訂 hint_ladder: 成功將題目的分級提示梯注入 Level 1 與 Level 2！")


if __name__ == "__main__":
    print("=" * 70)
    print("開始執行真實提示梯 (Hint Ladder) 動態注入測試")
    print("=" * 70)
    test_hint_ladder_loading()
    test_tutor_driver_ladder_injection()
    test_english_ladder_injection()
    test_custom_ladder_injection()
    print("\n" + "=" * 70)
    print("✓ 全部提示梯真實動態注入測試【100% 通過】！")
    print("=" * 70)
