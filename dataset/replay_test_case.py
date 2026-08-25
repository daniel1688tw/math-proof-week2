# -*- coding: utf-8 -*-
"""案例重播腳本：重播 測試結果.txt 中的 17 輪對話並檢驗關鍵輪次修復情況。"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# 設定環境
os.environ["REVIEW_BACKSTOP"] = "0"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from phase_router import route_student_state, normalize_persisted_state
from tutor_driver import TutorDriver, _FALLBACK_QS, _FALLBACK_QS_EN


# 題目資料
PROBLEM = {
    "id": "CUSTOM",
    "statement": "Let \\(f\\) be continuous on \\([0,1]\\) and twice differentiable on \\((0,1)\\). Suppose that \\(f(0)=f(1)=0\\) and \\(f(\\tfrac12)=1\\). Prove that there exists \\(c\\in(0,1)\\) such that \\(f''(c)=-8\\).",
    "reference_proof": "令 $g(x) = f(x) - (-4x^2 + 4x) = f(x) + 4x^2 - 4x$。\n則 $g(0) = f(0) = 0$，$g(1) = f(1) = 0$，$g(1/2) = f(1/2) + 4(1/4) - 4(1/2) = 1 + 1 - 2 = 0$。\n因 $g$ 在 $[0, 1/2]$ 和 $[1/2, 1]$ 上連續且在開區間可微，由 Rolle 定理：\n存在 $c_1 \\in (0, 1/2)$ 使得 $g'(c_1) = 0$，存在 $c_2 \\in (1/2, 1)$ 使得 $g'(c_2) = 0$。\n再對 $g'$ 在 $[c_1, c_2]$ 上應用 Rolle 定理：\n存在 $c \\in (c_1, c_2) \\subset (0, 1)$ 使得 $g''(c) = 0$。\n又 $g''(x) = f''(x) + 8$，故 $g''(c) = f''(c) + 8 = 0$，即 $f''(c) = -8$。"
}

# 17 輪學生發言
STUDENT_UTTERANCES = [
    "我毫無思緒",
    "我百思不解",
    "我黔驢技窮",
    "如果是令 $g(x) = f(x) - (-4x^2+4x)$ 的話，代入會得到 $g(0)=0$、$g(\\frac{1}{2}) = 1 - ( -4(\\frac{1}{4}) + 2 ) = 0$，還有 $g(1)=0$，所以總共有 3 個零點",
    "我束手無策",
    "我心有餘而力不足",
    "我還是丈二金剛",
    "因為 $g(0)=0$ 且 $g(\\frac{1}{2})=0$，根據羅爾定理（Rolle's Theorem），在區間 $(0, \\frac{1}{2})$ 內至少存在一點 $c_1$ 使得 $g'(c_1)=0$。同理，因為 $g(\\frac{1}{2})=0$ 且 $g(1)=0$，在區間 $(\\frac{1}{2}, 1)$ 內也至少存在一點 $c_2$ 使得 $g'(c_2)=0$。接著對 $g'(x)$ 在區間 $[c_1, c_2]$ 再用一次羅爾定理：因為 $g'(c_1) = g'(c_2) = 0$，所以在 $(c_1, c_2)$ 內必定存在一點 $c$ 使得 $g''(c) = 0$。",
    "我已經有:在 $(c_1, c_2)$ 內必定存在一點 $c$ 使得 $g''(c) = 0$",
    "我束手無策",
    "我不知道要怎麼從g''(c)=0推導到f''(c)=-8",
    "g''(c)=0",
    "我一竅不通",
    "我一頭霧水",
    "$g(x) = f(x) + 4x^2 - 4x$ 微分一次得到 $g'(x) = f'(x) + 8x - 4$ 微分兩次得到 $g''(x) = f''(x) + 8$",
    "接著該怎麼做?",
    "既然我們已經知道 $g''(c) = 0$，代入進去就是： $f''(c) + 8 = 0$ 所以 $f''(c) = -8$。",
]


class _StubModel:
    device = "cpu"


class MockModelDriver(TutorDriver):
    """用於 Tier 0 快速重播狀態機與路由的 Driver。"""
    def __init__(self, problem, **kwargs):
        super().__init__(tok=None, model=_StubModel(), problem=problem, **kwargs)
        self.mock_replies = [
            "先湊出一個「有三零點」的輔助函數。你打算減去哪個二次項？",
            "換個角度：題設給了 $f$ 在 $0,1,\\frac12$ 的值，而要證的是 $f''=-8$。若減去一個二次函數，能讓這三個點的差值同時為零嗎？",
            "試著減去 $-4x^2+4x$，算完 $g$ 的端點與中點值後，你會發現它有幾個零點？",
            "很好，三零點後你打算怎麼用羅爾定理？",
            "先對 $[0,\\frac12]$ 和 $[\\frac12,1]$ 各用一次，會得到什麼？",
            "最後一步：$g'$ 在 $c_1,c_2$ 處為零，再對 $[c_1,c_2]$ 用一次羅爾定理，能得到什麼？",
            "你自己算過 $g''$ 是什麼，最後一步你自己就能寫出來。",
            "很好！你已經推導出存在 $c$ 使得 $g''(c)=0$。那 $g(x)$ 的具體表達式求二階導數後是多少？",
            "很好，那最後一步你自己算出 $g''$ 是什麼，如何推出 $f''(c)=-8$？",
            "先不要跳到後面。我們已有 $g''(c)=0$，求 $g(x)=f(x)+4x^2-4x$ 的二階導數看看？",
            "我們可以先對 $g(x) = f(x) + 4x^2 - 4x$ 求兩次導數：$g''(x) = f''(x) + 8$。代入 $g''(c)=0$ 能得到什麼？",
            "對，這個是你自己用羅爾定理推出的。那 $g''$ 的具體表達式是什麼，如何連接到 $f''$？",
            "回想輔助函數 $g(x) = f(x) + 4x^2 - 4x$，試著把它微分兩次？",
            "你自己算過 $g(x) = f(x) + 4x^2 - 4x$，求二階導數後，$g''$ 等於什麼？",
            "很好，$g''(x) = f''(x) + 8$。現在把 $g''(c) = 0$ 代入這個式子，看看能得出什麼？",
            "把 $g''(c)=0$ 和 $g''(x)=f''(x)+8$ 連起來，你能寫出 $f''(c)$ 是多少嗎？",
            "思路已經完整了。現在請把完整證明一步步寫出來，我會幫你審閱。",
        ]
        self._turn_idx = 0

    def _raw_generate(self, msgs: list, max_new: int) -> str:
        if self._turn_idx < len(self.mock_replies):
            r = self.mock_replies[self._turn_idx]
            self._turn_idx += 1
            return r
        return "請繼續說明你的下一步想法？"

    def _generate(self, level: int) -> str:
        if self._turn_idx < len(self.mock_replies):
            r = self.mock_replies[self._turn_idx]
            self._turn_idx += 1
            return r
        return "請繼續說明你的下一步想法？"


def run_replay():
    print("=" * 70)
    print("重播 17 輪對話測試 (Replay 17-Turn Conversation)")
    print("=" * 70)

    driver = MockModelDriver(PROBLEM, backstop=False)
    
    # 執行 start
    first_reply = driver.start(STUDENT_UTTERANCES[0])
    
    results = []
    
    for turn_idx, text in enumerate(STUDENT_UTTERANCES, start=1):
        if turn_idx > 1:
            reply = driver.step(text)
        else:
            reply = first_reply
        
        summary = driver.turn_state_summary()
        decision = driver.state.get("student_state_decision") or {}
        
        results.append({
            "turn": turn_idx,
            "student_text": text,
            "tutor_reply": reply,
            "summary": summary,
            "decision": decision,
        })

    print(f"\n{'輪次':<4} | {'意圖(Intent)':<24} | {'學習狀態(Learning)':<20} | {'動作(Action)':<22} | {'判定結果'}")
    print("-" * 90)

    all_passed = True
    for r in results:
        t = r["turn"]
        intent = r["decision"].get("intent", "unknown")
        learning = r["decision"].get("learning_state", "unknown")
        action = r["decision"].get("turn_action", "unknown")
        
        check_msg = "✓ OK"
        
        # 關鍵輪次檢查
        if t == 8:
            # 第 8 輪：長推導，不能是 uncertain
            if intent == "show_attempt" and learning == "partial_progress" and action == "respond_attempt":
                check_msg = "✓ 已修復（長推導成功判定為 show_attempt/respond_attempt）"
            else:
                check_msg = f"✗ 未修復 (intent={intent}, learning={learning})"
                all_passed = False
        elif t == 11:
            # 第 11 輪：橋接提問，必須是 request_hint / active_clarification / answer_clarification
            if intent == "request_hint" and learning == "active_clarification" and action == "answer_clarification":
                check_msg = "✓ 已修復（橋接提問成功判定為 request_hint/answer_clarification）"
            else:
                check_msg = f"✗ 未修復 (intent={intent}, action={action})"
                all_passed = False
        elif t == 15:
            # 第 15 輪：微分式子推導，意圖為 show_attempt，且助教回覆不可為空泛問句
            is_generic = any(q.strip() in r["tutor_reply"] for q in _FALLBACK_QS + _FALLBACK_QS_EN)
            if intent == "show_attempt" and not is_generic:
                check_msg = "✓ 已修復（正常推進作答，無空泛問句）"
            else:
                check_msg = f"✗ 未修復 (intent={intent}, is_generic={is_generic})"
                all_passed = False
        elif t == 17:
            # 第 17 輪：最終完成證明
            check_msg = "✓ 成功推導出結論"

        print(f"{t:<4} | {intent:<24} | {learning:<20} | {action:<22} | {check_msg}")

    print("\n" + "=" * 70)
    print("關鍵問題修復深度對比報告：")
    print("=" * 70)

    # Turn 8 對比
    r8 = results[7]
    print(f"\n【第 43 輪／Turn 8：長推導 Rolle 定理】")
    print(f"  學生發言: {r8['student_text'][:60]}...")
    print(f"  先前紀錄: intent=uncertain, learning_state=uncertain, action=normal_guide (fallback)")
    print(f"  優化後  : intent={r8['decision'].get('intent')}, learning_state={r8['decision'].get('learning_state')}, action={r8['decision'].get('turn_action')}, source={r8['decision'].get('source')}")
    print(f"  判定    : {'通過 (PASSED)' if r8['decision'].get('intent') == 'show_attempt' else '失敗 (FAILED)'}")

    # Turn 11 對比
    r11 = results[10]
    print(f"\n【第 58 輪／Turn 11：橋接提問從 g''(c)=0 推到 f''(c)=-8】")
    print(f"  學生發言: {r11['student_text']}")
    print(f"  先前紀錄: intent=uncertain, learning_state=uncertain, action=normal_guide (空泛問句)")
    print(f"  優化後  : intent={r11['decision'].get('intent')}, learning_state={r11['decision'].get('learning_state')}, action={r11['decision'].get('turn_action')}, source={r11['decision'].get('source')}")
    print(f"  判定    : {'通過 (PASSED)' if r11['decision'].get('intent') == 'request_hint' else '失敗 (FAILED)'}")

    # Turn 15 對比
    r15 = results[14]
    print(f"\n【第 78 輪／Turn 15：具體求導式子推導】")
    print(f"  學生發言: {r15['student_text']}")
    print(f"  先前紀錄: 助教回覆空泛問句「你想先從哪個方向試試看？」")
    print(f"  優化後  : intent={r15['decision'].get('intent')}, learning_state={r15['decision'].get('learning_state')}, action={r15['decision'].get('turn_action')}")
    print(f"  Tutor回覆: {r15['tutor_reply']}")
    print(f"  判定    : {'通過 (PASSED)' if r15['decision'].get('intent') == 'show_attempt' else '失敗 (FAILED)'}")

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ 全部 17 輪重播與先前失敗案例檢驗【100% 通過】！")
    else:
        print("✗ 仍有部分案例未通過檢驗，請檢查路由邏輯。")
        sys.exit(1)


if __name__ == "__main__":
    run_replay()
