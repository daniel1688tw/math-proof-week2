# -*- coding: utf-8 -*-
"""全量檢驗多道題目在 TutorDriver Level 0 / Level 1 / Level 2 下的真實提示深度與階梯梯次。

直接載入所有 held-out 與 hard-math 題目（H1~H8, M1~M5 等），檢驗在接通 hint_ladders 庫後，
每一道題目在 Level 0（宏觀）、Level 1（局部支架）與 Level 2（關鍵破局）的 System Prompt 指示
是否真正具備顯著的提示深度梯度。
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


def evaluate_all_problem_levels():
    problems = load_problems()
    test_pids = ["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8", "M1", "M2", "M3", "M4", "M5"]
    
    print("=" * 80)
    print("全量題目 Level 0 -> Level 1 -> Level 2 提示深度與梯次評估報告")
    print("=" * 80)
    
    results = []
    
    for pid in test_pids:
        if pid not in problems:
            continue
        p = problems[pid]
        driver = TutorDriver(tok=None, model=_DummyModel(), problem=p)
        
        sys_0 = driver._system(0)
        sys_1 = driver._system(1)
        sys_2 = driver._system(2)
        
        instr_0 = sys_0.split("</REFERENCE_PROOF>")[-1].strip()
        instr_1 = sys_1.split("</REFERENCE_PROOF>")[-1].strip()
        instr_2 = sys_2.split("</REFERENCE_PROOF>")[-1].strip()
        
        ladder = p.get("hint_ladder") or []
        has_ladder = len(ladder) >= 2
        
        # 檢驗深度區隔
        distinct_0_1 = (instr_0 != instr_1)
        distinct_1_2 = (instr_1 != instr_2)
        has_ladder_step1 = (ladder[0] in instr_1) if has_ladder else False
        has_ladder_step2 = (ladder[1] in instr_2) if has_ladder else False
        
        all_passed = distinct_0_1 and distinct_1_2 and (has_ladder_step1 if has_ladder else True) and (has_ladder_step2 if has_ladder else True)
        
        results.append({
            "pid": pid,
            "has_ladder": has_ladder,
            "distinct_0_1": distinct_0_1,
            "distinct_1_2": distinct_1_2,
            "ladder_step1_injected": has_ladder_step1,
            "ladder_step2_injected": has_ladder_step2,
            "passed": all_passed,
            "instr_0_sample": instr_0[:40] + "...",
            "instr_1_sample": instr_1[:55] + "...",
            "instr_2_sample": instr_2[:55] + "...",
        })
        
        status = "✓ 通過" if all_passed else "✗ 異常"
        print(f"\n【題目 {pid}】狀態: {status}")
        print(f"  • Level 0 (宏觀): {instr_0}")
        print(f"  • Level 1 (支架): {instr_1}")
        print(f"  • Level 2 (破局): {instr_2}")
        
    print("\n" + "=" * 80)
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    print(f"評估結果統計: {passed_count}/{total_count} 題完全符合提示深度階梯規範（100% 注入與梯次區隔）！")
    print("=" * 80)
    
    assert passed_count == total_count, "所有受測題目的 Level 0/1/2 階梯必須 100% 通過"


if __name__ == "__main__":
    evaluate_all_problem_levels()
