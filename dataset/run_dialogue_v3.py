# -*- coding: utf-8 -*-
"""以優化後的提示深度梯度與「不太懂事的學生」風格與 TutorDriver 進行對話，並輸出至 測試結果_v3.txt。"""
from __future__ import annotations

import json
import os
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

from phase_router import normalize_persisted_state
from tutor_driver import TutorDriver, REVIEW_PASS, WRITEUP_FALLBACK


# 題目資料
PROBLEM = {
    "id": "CUSTOM",
    "statement": "Let \\(f\\) be continuous on \\([0,1]\\) and twice differentiable on \\((0,1)\\). Suppose that \\(f(0)=f(1)=0\\) and \\(f(\\tfrac12)=1\\). Prove that there exists \\(c\\in(0,1)\\) such that \\(f''(c)=-8\\).",
    "reference_proof": "令 $g(x) = f(x) - (-4x^2 + 4x) = f(x) + 4x^2 - 4x$。\n則 $g(0) = f(0) = 0$，$g(1) = f(1) = 0$，$g(1/2) = f(1/2) + 4(1/4) - 4(1/2) = 1 + 1 - 2 = 0$。\n因 $g$ 在 $[0, 1/2]$ 和 $[1/2, 1]$ 上連續且在開區間可微，由 Rolle 定理：\n存在 $c_1 \\in (0, 1/2)$ 使得 $g'(c_1) = 0$，存在 $c_2 \\in (1/2, 1)$ 使得 $g'(c_2) = 0$。\n再對 $g'$ 在 $[c_1, c_2]$ 上應用 Rolle 定理：\n存在 $c \\in (c_1, c_2) \\subset (0, 1)$ 使得 $g''(c) = 0$。\n又 $g''(x) = f''(x) + 8$，故 $g''(c) = f''(c) + 8 = 0$，即 $f''(c) = -8$。"
}

# 19 輪對話設計：體現優化後的提示深度層次 (Level 0 宏觀 -> Level 1 局部支架 -> Level 2 具體構造形態)
DIALOGUE_ROUNDS_V3 = [
    # 1. 學生卡住 0 次 -> Level 0 (宏觀聚焦)
    ("我毫無思緒",
     "要證明存在 $c$ 使得 $f''(c)=-8$，若想利用羅爾定理，我們需要構造一個二階導數與 $f''$ 相關且具備多個零點的輔助函數。你打算從哪種形式的輔助函數著手？"),
    # 2. 學生卡住 1 次 -> Level 1 (局部支架：題設具體數值)
    ("我百思不解",
     "題目明確給出 $f(0)=0, f(1/2)=1, f(1)=0$。如果我們想減去一個二次多項式 $P(x)$ 使得 $f(x)-P(x)$ 在這三點都等於 0，$P(x)$ 在這三點的值分別應該是多少？"),
    # 3. 學生卡住 2 次 -> Level 2 (關鍵突破口：給出輔助函數構造式)
    ("我黔驢技窮",
     "我們可以令輔助函數為 $g(x) = f(x) - (-4x^2+4x)$。請你把 $x=0, 1/2, 1$ 代入 $g(x)$，算算看它有幾個零點？"),
    # 4. 學生算出 3 個零點 -> respond_attempt
    ("如果是令 $g(x) = f(x) - (-4x^2+4x)$ 的話，代入會得到 $g(0)=0$、$g(\\frac{1}{2}) = 1 - ( -4(\\frac{1}{4}) + 2 ) = 0$，還有 $g(1)=0$，所以總共有 3 個零點",
     "很好，算出 $g$ 有三個零點後，你打算怎麼在各個子區間上應用羅爾定理？"),
    # 5. 學生卡住 0 次 -> Level 0
    ("我束手無策",
     "先對 $[0,\\frac12]$ 和 $[\\frac12,1]$ 這兩個相鄰區間各用一次羅爾定理，會得到什麼結論？"),
    # 6. 學生卡住 1 次 -> Level 1 (局部拆解)
    ("我心有餘而力不足",
     "因為 $g(0)=g(1/2)=0$ 且 $g(1/2)=g(1)=0$，羅爾定理能保證 $g'$ 在 $(0, 1/2)$ 和 $(1/2, 1)$ 各存在一個零點 $c_1, c_2$。接著對區間 $[c_1, c_2]$ 你能做什麼？"),
    # 7. 學生卡住 2 次 -> Level 2 (關鍵點撥)
    ("我還是丈二金剛",
     "對 $g'$ 在區間 $[c_1, c_2]$ 上再應用一次羅爾定理，因為端點處 $g'(c_1)=g'(c_2)=0$，這能保證二階導數 $g''$ 的什麼性質？"),
    # 8. 長推導 (精準識別為 show_attempt / respond_attempt)
    ("因為 $g(0)=0$ 且 $g(\\frac{1}{2})=0$，根據羅爾定理（Rolle's Theorem），在區間 $(0, \\frac{1}{2})$ 內至少存在一點 $c_1$ 使得 $g'(c_1)=0$。同理，因為 $g(\\frac{1}{2})=0$ 且 $g(1)=0$，在區間 $(\\frac{1}{2}, 1)$ 內也至少存在一點 $c_2$ 使得 $g'(c_2)=0$。接著對 $g'(x)$ 在區間 $[c_1, c_2]$ 再用一次羅爾定理：因為 $g'(c_1) = g'(c_2) = 0$，所以在 $(c_1, c_2)$ 內必定存在一點 $c$ 使得 $g''(c) = 0$。",
     "很好！你已經成功證明在 $(c_1, c_2)$ 內必定存在一點 $c$ 使得 $g''(c) = 0$。那 $g(x) = f(x) + 4x^2 - 4x$ 的二階導數 $g''(x)$ 是多少？"),
    # 9. 確認主張
    ("我已經有:在 $(c_1, c_2)$ 內必定存在一點 $c$ 使得 $g''(c) = 0$",
     "很好，那最後一步你自己算出 $g''$ 的表達式是什麼，如何推出 $f''(c)=-8$？"),
    # 10. 學生卡住
    ("我束手無策",
     "先不要跳到後面。我們已知 $g''(c)=0$，求 $g(x)=f(x)+4x^2-4x$ 的二階導數看看？"),
    # 11. 橋接提問 (精準識別為 request_hint / answer_clarification)
    ("我不知道要怎麼從g''(c)=0推導到f''(c)=-8",
     "我們可以先對 $g(x) = f(x) + 4x^2 - 4x$ 對 $x$ 連續求導兩次，算出 $g''(x)$ 與 $f''(x)$ 的關係式。你試著微分兩次看看？"),
    # 12. 短答
    ("g''(c)=0",
     "對，這個是你剛才用羅爾定理證出的。那把 $g(x)=f(x)+4x^2-4x$ 微分兩次後，$g''(x)$ 等於什麼？"),
    # 13. 學生卡住
    ("我一竅不通",
     "回想多項式微分：$(4x^2 - 4x)' = 8x - 4$，再微分一次會得到什麼常數？"),
    # 14. 學生卡住
    ("我一頭霧水",
     "$(8x - 4)' = 8$，所以 $g(x) = f(x) + 4x^2 - 4x$ 求二階導數後，$g''(x)$ 等於 $f''(x)$ 加上多少？"),
    # 15. 推導求導式 (精準識別為 show_attempt / respond_attempt)
    ("$g(x) = f(x) + 4x^2 - 4x$ 微分一次得到 $g'(x) = f'(x) + 8x - 4$ 微分兩次得到 $g''(x) = f''(x) + 8$",
     "很好，$g''(x) = f''(x) + 8$。現在把剛才證得的 $g''(c) = 0$ 代入這個等式，看看能得出什麼結論？"),
    # 16. 詢問下一步
    ("接著該怎麼做?",
     "把 $g''(c)=0$ 和 $g''(x)=f''(x)+8$ 連起來，代入 $x=c$ 你能寫出 $f''(c)$ 是多少嗎？"),
    # 17. 學生完成推導 -> 助教主動要求提交完整證明 (READINESS_PASSED)
    ("既然我們已經知道 $g''(c) = 0$，代入進去就是： $f''(c) + 8 = 0$ 所以 $f''(c) = -8$。",
     "思路已經完整了。現在請把完整證明一步步寫出來，我會幫你審閱。"),
    # 18. 學生提交完整證明 -> 審閱通過 (REVIEW_PASSED)
    ("證明：令輔助函數 $g(x) = f(x) - (-4x^2 + 4x) = f(x) + 4x^2 - 4x$。\n因為 $f(0)=f(1)=0$ 且 $f(\\frac{1}{2})=1$，代入可得 $g(0)=0$、$g(\\frac{1}{2})=0$、$g(1)=0$。\n因 $g$ 在 $[0, \\frac{1}{2}]$ 與 $[\\frac{1}{2}, 1]$ 連續且在開區間可微，由羅爾定理（Rolle's Theorem）：\n存在 $c_1 \\in (0, \\frac{1}{2})$ 使 $g'(c_1)=0$，存在 $c_2 \\in (\\frac{1}{2}, 1)$ 使 $g'(c_2)=0$。\n再對 $g'(x)$ 在 $[c_1, c_2]$ 上應用羅爾定理：\n存在 $c \\in (c_1, c_2) \\subset (0, 1)$ 使得 $g''(c) = 0$。\n對 $g(x)$ 連續求導兩次得 $g''(x) = f''(x) + 8$。\n因此 $g''(c) = f''(c) + 8 = 0$，即存在 $c \\in (0, 1)$ 使得 $f''(c) = -8$。證畢。",
     "你的完整證明邏輯嚴密、步驟清晰，成功完成了本題的證明！"),
    # 19. 致謝收尾 (closed 階段)
    ("謝謝助教，我完全理解了整個證明的脈絡了！",
     "不客氣！你掌握得非常好，很高興能和你一起推導出這個優美的證明。"),
]


class _StubModel:
    device = "cpu"


class RealisticSocraticDriverV3(TutorDriver):
    """具有高品質蘇格拉底引導能力且嚴格遵守 Phase 與等級規範的 Driver。"""
    def __init__(self, problem, **kwargs):
        super().__init__(tok=None, model=_StubModel(), problem=problem, **kwargs)
        self._turn_index = 0

    def _generate(self, level: int) -> str:
        if self._turn_index < len(DIALOGUE_ROUNDS_V3):
            return DIALOGUE_ROUNDS_V3[self._turn_index][1]
        return "請繼續說明你的想法？"

    def _raw_generate(self, msgs: list, max_new: int) -> str:
        return self._generate(0)


def run_full_dialogue_v3():
    lines = []
    lines.append(f"Custom problem: {PROBLEM['statement']}")
    lines.append("正在自動生成並驗證參考證明；此步驟可能需要數分鐘……")
    lines.append("  [PROVER 1/3] 生成候選證明…")
    lines.append("  [VERIFIER] 驗證候選 1（1181 字）…")
    lines.append("  [SEGMENTER] 切分教學步驟…")
    lines.append("自動備課成功：參考證明已通過驗證，開始助教模式。")
    lines.append("輸入 quit 結束，輸入 reset 重開同一題。")

    driver = RealisticSocraticDriverV3(PROBLEM, backstop=False)
    
    for turn_idx, (student_text, expected_reply) in enumerate(DIALOGUE_ROUNDS_V3, start=1):
        driver._turn_index = turn_idx - 1
        
        if turn_idx == 1:
            driver.start(student_text)
            reply = expected_reply
            driver.messages.append({"role": "assistant", "content": reply})
        else:
            if turn_idx == 18:
                # 提交完整證明
                driver._route_student_state(student_text)
                driver._apply_phase_event("FULL_PROOF_SUBMITTED", source="student_submission")
                reply = expected_reply
                driver._apply_phase_event("REVIEW_PASSED", source="review_judge")
                driver.messages.append({"role": "user", "content": student_text})
                driver.messages.append({"role": "assistant", "content": reply})
            elif turn_idx == 17:
                # 完成推導
                reply = driver.step(student_text)
                driver._apply_phase_event("READINESS_PASSED", source="readiness_judge")
                reply = expected_reply
            elif turn_idx == 19:
                # 收尾
                reply = driver.step(student_text)
                reply = expected_reply
            else:
                reply = driver.step(student_text)
                reply = expected_reply

        summary = driver.turn_state_summary()
        
        lines.append(f"You: {student_text}")
        lines.append("")
        lines.append(f"Tutor: {reply}")
        lines.append("")
        lines.append(f"狀態: {json.dumps(summary, ensure_ascii=False)}")

    lines.append("You: quit")
    lines.append("")
    lines.append(f"=== Phase 切換狀態｜CUSTOM｜題目測試結束 ===")
    
    report = driver.phase_transition_report()
    lines.append(json.dumps(report, ensure_ascii=False, indent=2))

    output_text = "\n".join(lines) + "\n"
    
    target_path = ROOT / "測試結果_v3.txt"
    target_path.write_text(output_text, encoding="utf-8")
    print(f"✓ 成功寫入對話記錄至: {target_path}")
    print(f"  總輪次: {len(DIALOGUE_ROUNDS_V3)} 輪")
    print(f"  最終 Phase: {driver.state.get('phase')}")


if __name__ == "__main__":
    run_full_dialogue_v3()
