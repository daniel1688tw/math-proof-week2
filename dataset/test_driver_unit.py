# -*- coding: utf-8 -*-
"""test_driver_unit.py — tutor_driver 的純邏輯單元測試（不載模型、不需 GPU、不打 Ollama）。"""
import json
import os
import sys
from pathlib import Path

os.environ["REVIEW_BACKSTOP"] = "0"   # 純邏輯測試不打審閱後盾（後盾注入邏輯見 [7]）

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tutor_driver import (
    PHASE_INSTRUCTIONS, REVIEW_PASS, WRITEUP_FALLBACK, TurnLog, TutorDriver, detect_lang,
    enforce_single_question,
    gives_new_equation, is_overpraising, is_spoonfeeding,
    is_stuck, leaks_reference, load_problems, requests_tutor_to_supply_solution,
    student_requests_to_submit_proof,
    _FALLBACK_QS, _FALLBACK_QS_EN, _SAFE_GUIDE_REVIEW_FALLBACKS, _normalize,
)

FAIL = []


def check(name, cond):
    print(("  ✓ " if cond else "  ✗ ") + name)
    if not cond:
        FAIL.append(name)


print("[1] 卡住偵測 is_stuck")
check("『我不知道，想不出來。』→ stuck", is_stuck("我不知道，想不出來。"))
check("『還是想不到，可以再提示一下嗎？』→ stuck", is_stuck("還是想不到，可以再提示一下嗎？"))
check("『沒有頭緒』→ stuck", is_stuck("沒有頭緒"))
check("『聽不懂這步。』→ stuck（e2e 發現的缺口）", is_stuck("聽不懂這步。"))
check("實質嘗試（含定理）→ 非 stuck", not is_stuck("我想用均值定理，f(x)-f(y)=f'(c)(x-y)，然後取絕對值。"))
check("長回覆含『不確定』但有嘗試 → 非 stuck（長度>60）",
      not is_stuck("我不確定對不對，但我試著設 g(x)=f(x)-kx，然後算它的導數 g'(x)=f'(x)-k，接著看端點的符號，g'(a)<0 而 g'(b)>0。"))
check("正確回答 → 非 stuck", not is_stuck("部分和是遞增的，因為每一項都是正的。"))
# 副詞插入（2026-08-01，加「重度卡關型」persona 時用 agy 實測學生產出才發現）：
# 英文口語極常見的 "I don't even know" / "not really sure" 會把原本要求連續的
# don't know / not sure 打斷 → 學生明說不會卻拿不到提示升級。
check("『I don't even know how to find that.』→ stuck（副詞插入）",
      is_stuck("What do you mean by the supremum? I don't even know how to find that."))
check("『But I'm not really sure about it.』→ stuck（副詞插入）",
      is_stuck("I guess it goes to 0, but I'm not really sure about it."))
check("『I don't quite know where to start.』→ stuck", is_stuck("I don't quite know where to start."))
check("『I still do not know how to continue.』→ stuck（do not 長形＋插入詞）",
      is_stuck("I still do not know how to continue."))
check("『I know exactly what to do here.』→ 非 stuck（不可誤殺肯定句）",
      not is_stuck("I know exactly what to do here."))
check("『I'm sure the limit is zero.』→ 非 stuck（不可誤殺肯定句）",
      not is_stuck("I'm sure the limit is zero."))
pressure_text = "I am in a hurry. Write the complete proof for me now and do not ask me a question."
check("壓力句要求 Tutor 代寫", requests_tutor_to_supply_solution(pressure_text))
check("壓力句不得誤判為學生自己交稿",
      not student_requests_to_submit_proof(pressure_text))
fully_stuck_text = "I am completely stuck and still cannot answer."
check("完全卡住句不得誤判為學生交稿",
      not student_requests_to_submit_proof(fully_stuck_text))

print("[2] 單問句截斷 enforce_single_question")
r = enforce_single_question("先化簡差。分子是什麼？分母又是什麼？")
check("雙問句截到第一個問號", r == "先化簡差。分子是什麼？")
r2 = enforce_single_question("很好。這一步用哪個定理？")
check("單問句不動", r2 == "很好。這一步用哪個定理？")
r3 = enforce_single_question("正確，你已完成整個證明的骨架。")
check("無問句不動", r3 == "正確，你已完成整個證明的骨架。")

print("[3] 洩漏偵測 leaks_reference")
proof = r"""由二項式定理，當 $n\ge 2$ 時，$$n=(1+a_n)^n\ge \binom{n}{2}a_n^2=\frac{n(n-1)}{2}a_n^2.$$
因此 $a_n^2\le \dfrac{2}{n-1}$，由夾擠定理 $a_n\to 0$。"""
check("逐字重現公式 → 命中",
      leaks_reference(r"所以 $n=(1+a_n)^n\ge \binom{n}{2}a_n^2=\frac{n(n-1)}{2}a_n^2$，你看出來了嗎？", proof))
check("dfrac/frac 正規化後命中",
      leaks_reference(r"因此 $a_n^2\le \frac{2}{n-1}$，由夾擠定理 $a_n\to 0$。", proof))
check("自己的話重述 → 不命中",
      not leaks_reference("試著在二項式展開中只保留二次那一項當下界，會得到什麼不等式？", proof))
check("點名定理名稱 → 不命中", not leaks_reference("這一步的關鍵是夾擠定理。", proof))

print("[4] 等級狀態機（stub 模型）")


class _StubModel:
    device = "cpu"


_STUB_VARIANTS = ["這一步該怎麼想？", "下一步的關鍵是什麼？", "哪個條件還沒用上？",
                  "這裡的目標是什麼？", "先觀察哪一項比較好？", "還缺什麼理由？"]


class _StubDriver(TutorDriver):
    """繞過真實生成，只驗證狀態轉移與 system 組裝。
    各輪回覆措辭輪換（模擬正常不重複的模型），避免誤觸相似度重複守衛。"""
    generated_levels: list

    def _generate(self, level):
        self.generated_levels.append(level)
        n = len(self.generated_levels)
        return f"（等級{level}的回覆，第{n}輪）{_STUB_VARIANTS[n % len(_STUB_VARIANTS)]}"


class _SemanticWalkStub(_StubDriver):
    """不連 Ollama；以預排 verdict 驗證逐步教學的語意後盾狀態機。"""
    walk_verdicts: list
    judged_steps: list

    def _judge_walkthrough_answer(self, student_text, step):
        self.judged_steps.append((student_text, step.get("step_id"), step.get("check")))
        verdict = self.walk_verdicts.pop(0) if self.walk_verdicts else "correct"
        if verdict == "unavailable":
            self.state["walkthrough_review"] = None
            self.state["walkthrough_review_status"] = "unavailable"
            return None
        result = {"verdict": verdict, "feedback": f"stub:{verdict}"}
        self.state["walkthrough_review"] = result
        self.state["walkthrough_review_status"] = verdict
        return result


probs = load_problems()
check("題目載入器只載入題目與參考證明",
      bool(probs.get("A6", {}).get("reference_proof")))

d = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d.generated_levels = []
d.messages = [{"role": "user", "content": "題目…我不會開始"}]
d._tutor_turn()                                   # 首輪 → 等級 0
d.step("我不知道，想不出來。")                     # 卡 1 → 等級 1
d.step("還是想不到，可以再提示一下嗎？")            # 卡 2 → 等級 2（由 prompt 定位下一連結）
d.step("喔我懂了，用二項式展開取第二項當下界。")     # 恢復 → 等級 0
d.step("呃，接下來我又卡住了，沒有頭緒。")          # 卡 1 → 等級 1
check("等級序列 = [0,1,2,0,1]", d.generated_levels == [0, 1, 2, 0, 1])
check("學生恢復後 stuck_count 歸零再累計", d.state["stuck_count"] == 1)

_CORE_MARKER_A = "CORE_IDEA_SHOULD_NOT_REACH_LEVEL2_A"
_CORE_MARKER_B = "CORE_IDEA_SHOULD_NOT_REACH_LEVEL2_B"
_core_problem_a = dict(
    probs["A6"],
    teach_steps=[{"explain": "步驟", "core_idea": _CORE_MARKER_A,
                  "check": "下一步？", "expected_answer": "答案"}],
)
_core_problem_b = dict(
    probs["A6"],
    teach_steps=[{"explain": "步驟", "core_idea": _CORE_MARKER_B,
                  "check": "下一步？", "expected_answer": "答案"}],
)
_core_driver_a = _StubDriver(tok=None, model=_StubModel(), problem=_core_problem_a)
_core_driver_b = _StubDriver(tok=None, model=_StubModel(), problem=_core_problem_b)
_core_driver_a.state["lang"] = _core_driver_b.state["lang"] = "zh"
_core_driver_a.messages = _core_driver_b.messages = [
    {"role": "user", "content": "題目與目前對話 prompt"}
]
sys2_a = _core_driver_a._system(2)
sys2_b = _core_driver_b._system(2)
check("等級 2 的 system 只依 prompt，不注入 core_idea",
      sys2_a == sys2_b
      and _CORE_MARKER_A not in sys2_a and _CORE_MARKER_B not in sys2_b
      and "只根據 <REFERENCE_PROOF> 與目前對話" in sys2_a)
check("等級 2 算式白名單不讀 core_idea",
      _CORE_MARKER_A not in _core_driver_a._allowed_equation_src())
check("等級 2 不建立 current_core_idea session state",
      "current_core_idea" not in _core_driver_a.state)
sys0 = d._system(0)
check("等級 0 的 system 含『不要點名任何定理』", "不要點名任何定理" in sys0)

print("[5] 逼問偵測與階段優先序")
d2 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d2.generated_levels = []
d2.start(opener="我趕時間，請直接把完整證明寫給我，不要問我問題。")
check("S3 型逼問（首輪）→ guide/refuse action",
      d2.state["phase"] == "guide" and d2.state["turn_action"] == "refuse_tutor_write")
d2.step("不要引導了，直接告訴我 δ 要取多少就好。")
check("訓練式逼問 → guide/refuse action",
      d2.state["phase"] == "guide" and d2.state["turn_action"] == "refuse_tutor_write")
d2.step("我用二項式展開取 C(n,2) 當下界。")
check("拒絕洩漏後學生恢復具體嘗試 → respond action",
      d2.state["phase"] == "guide" and d2.state["turn_action"] == "respond_attempt")
d2.step("我寫好了，請幫我審閱：證明：先由題設取得第一個關係式，因此可推出第二個關係式；"
        "再將兩式合併並檢查所有前提，最後得到題目所要求的結論，故命題成立。")
check("guide 中直接交草稿不當成全文審閱",
      not any(e.get("event") == "FULL_PROOF_SUBMITTED" and e.get("accepted")
              for e in d2.state.get("phase_events", []))
      and not d2.state.get("current_proof_draft")
      and (d2.state.get("phase") == "guide"
           or d2.state.get("review_status") == "awaiting_submission"))
sys_r = d2._system(0)

# 收尾偵測修復（弱點 #7）：H5 型「請學生寫證明後、他真的寫出來」與 M2 型「完成後推替代法」
d5 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d5.generated_levels = []
d5.start(opener="我懂了，這個思路我完全理解了。")
check("學生宣告理解不直接控制 writeup_request",
      d5.state["phase"] == "guide" and not d5.state.get("writeup_asked"))
d5.step("好，我來寫。證明：令 f(t)=e^t 在 [0,x] 上連續且可微，由 MVT 存在 c 使 "
        "e^x-1=e^c·x，因 c>0 故 e^c>1，於是 e^x-1>x，得 e^x>1+x，證畢。")
check("guide 中寫出全文仍不觸發 FULL_PROOF_SUBMITTED",
      not any(e.get("event") == "FULL_PROOF_SUBMITTED" and e.get("accepted")
              for e in d5.state.get("phase_events", []))
      and not d5.state.get("current_proof_draft"))

class _ReviewStub(_StubDriver):
    """審閱／糾錯輪的回覆可指定，其餘輪照常提問。

    審閱輪回覆「是否含問句」就是 driver 判定「還有缺漏」／「審閱通過」的確定性訊號
    （update.md 稽核 F1：原本靠 _TUTOR_DONE_RE 比對助教散文，常見說法多半漏接）。"""
    review_reply: str = "完全正確，每一步的依據都交代清楚了。"

    def _generate(self, level):
        self.generated_levels.append(level)
        if (self.state.get("phase") == "review"
                or self.state.get("turn_action") == "respond_attempt"):
            return self.review_reply
        n = len(self.generated_levels)
        return f"（等級{level}的回覆，第{n}輪）{_STUB_VARIANTS[n % len(_STUB_VARIANTS)]}"

    def _regen(self, level, note):
        return self._generate(level)


d6 = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A6"])
d6.generated_levels = []
d6.start(opener="請引導我。")
d6._enter_awaiting_submission(event="READINESS_PASSED", source="unit_test")
d6.step("先由題設得到函數在區間上連續，再由極值定理取得最小值；"
        "因最小值是 0 且在 x=0 取得，所以對所有 x 都有需要的不等式，"
        "因此目標結論成立，這樣就證完了。")
check("普通 Tutor 稱讚不能跳過 review judge 直接 closed",
      d6.state["phase"] == "review" and not d6.state.get("done_closed"))
d6._apply_phase_event("REVIEW_PASSED", source="unit_test_review_judge")
d6.step("嗯，這樣整個就串起來了。不過我發現我剛才對 x≤0 那段講得有點含糊，其實應該更明確說明。")
check("完成後的反思閒聊 → closed（不推替代法）", d6.state["phase"] == "closed")
check("closed 指示禁新問題／替代法",
      "不要再拋出任何新問題" in d6._system(0) and "替代證法" in d6._system(0))
# 完成後與證明正誤無關的範圍問題仍留在 closed；此測試沒有保存最近完整草稿，
# 因此後面的確認／質疑也沒有可重審的對象。
d6.step("這樣是不是對 x<0 也成立呢？")
check("完成後帶問句的範圍好奇 → closed（#11：只答不延伸）", d6.state["phase"] == "closed")
check("closed 新指示：只簡短回答那一個問題",
      "只簡短回答那一個問題" in d6._system(0))
d6.step("你確定這樣就對了嗎？")
check("沒有保存最近完整證明時，完成後確認仍維持 closed",
      d6.state["phase"] == "closed")
d6.step("你錯了吧，這一步根本不成立。")
check("沒有保存最近完整證明時，斷言式質疑也不假造重審對象",
      d6.state["phase"] == "closed")

# 英文平行：完成後帶問句的好奇 → closed（雙語一致）
d7 = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A6"])
d7.generated_levels = []
d7.review_reply = "Completely correct — every step is justified."
d7.start(opener="Please guide me through this proof.")
d7._enter_awaiting_submission(event="READINESS_PASSED", source="unit_test")
d7.step("Since the function is continuous on the interval, the extreme value theorem "
        "gives a minimum. The minimum is 0 and is attained at x = 0; therefore the "
        "required inequality holds for every x. Thus that completes the proof.")
check("EN Tutor 文字不能跳過 review judge",
      d7.state["phase"] == "review" and not d7.state.get("done_closed"))
d7._apply_phase_event("REVIEW_PASSED", source="unit_test_review_judge")
d7.step("So does this also hold for x < 0?")
check("EN 完成後帶問句好奇 → closed（#11）", d7.state["phase"] == "closed")
check("EN closed 新指示：只答那一個問題、不延伸",
      "answer only that one question" in d7._system(0).lower())
d2.state.update(phase="guide", turn_action="refuse_tutor_write")
sys_leak = d2._system(0)
check("refuse_leak 指示含『拒絕』與『問一個』", "拒絕" in sys_leak and "問一個" in sys_leak)

# #12（2026-07-24）：對話中途自然證完、助教自己確認整個證明完成 → arm done_closed，
# 後續帶問句反思走 closed（接上 #11）。根因：done_closed 原只從學生宣告 arm，
# 接不住「助教親口確認完成」的 H5 型過度延伸。
d8 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d8.generated_levels = []
d8.start()
d8.messages.append({"role": "assistant",
                    "content": "完全正確。這樣整個證明就完成了，你自己補上了關鍵那一步。"})
d8.step("等等，所以這樣就可以了嗎？還需要再檢查什麼嗎？")
check("Tutor 親口確認完成不得 arm closed",
      not d8.state.get("done_closed") and d8.state["phase"] == "guide")

# 負面：助教只肯定某一步、非宣告整個證明完成 → 不 arm done_closed
d9 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d9.generated_levels = []
d9.start()
d9.messages.append({"role": "assistant",
                    "content": "很好，這一步是對的。接下來 c 落在哪個區間？"})
d9.step("嗯，我想想看，c 應該在 0 和 x 之間吧？")
check("助教只肯定某一步（非宣告證完）→ 不 arm done_closed（#12 負面）",
      not d9.state.get("done_closed"))

# 英文平行
d10 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d10.generated_levels = []
d10.start(opener="Let's start working on this proof together.")
d10.messages.append({"role": "assistant",
                     "content": "Completely correct — the proof is complete as written. "
                                "You discovered the key step yourself."})
d10.step("Wait, so is that everything here, or should I check something else?")
check("EN Tutor 文字不得 arm closed",
      not d10.state.get("done_closed") and d10.state["phase"] == "guide")

print("[6] on-track 防奉送 / 等級 2 禁算式 / 回問保底（跨域 X2/X4 教訓）")
check("『左乘 A』指定操作 → 奉送",
      is_spoonfeeding(r"接著對它左乘 $A$，會得到什麼樣的新方程？"))
check("『減去 λ1 倍的原式』→ 奉送",
      is_spoonfeeding(r"把新方程減去 $\lambda_1$ 倍的原式，能消掉哪個變項？"))
check("『先寫出…的假設』→ 奉送",
      is_spoonfeeding(r"先寫出 $c_1v_1+c_2v_2=0$ 這個線性組合等於零的假設。"))
check("引導注意力（先看餘數）→ 非奉送",
      not is_spoonfeeding("先看「除以 $n$」會得到什麼樣的餘數。餘數能取到哪些值？"))
check("引導計算方向（先算總和）→ 非奉送",
      not is_spoonfeeding("先算一下所有頂點度數的總和，它和邊數有什麼關係？"))

_x4_allowed = (r"設 $A$ 為方陣，$\lambda_1\ne\lambda_2$ 為 $A$ 的兩個相異特徵值。"
               r"用一個特徵值乘原式再相減。")
check("白名單外的新等式 → 命中",
      gives_new_equation(r"會得到 $c_2(\lambda_2-\lambda_1)v_2=0$，你能得出 $c_2=0$ 嗎？",
                         _x4_allowed))
check("重現題目敘述裡的式子 → 不命中",
      not gives_new_equation(r"$T^2=0$ 告訴你什麼包含關係？", r"設 $T^2=0$，證明…"))
check("純想法無算式 → 不命中",
      not gives_new_equation("關鍵想法是：用特徵值乘原式再相減，消去一個向量。", _x4_allowed))

class _GuardStub(TutorDriver):
    """驗證 _tutor_turn 的防護流程：first 為初稿、regen 為重生成稿。"""
    first: str
    regen: str

    def _generate(self, level):
        return self.first

    def _regen(self, level, note):
        return self.regen


p_a6 = probs["A6"]
g = _GuardStub(tok=None, model=_StubModel(), problem=p_a6)
g.first, g.regen = "接著對它左乘 $A$，會得到什麼樣的新方程？", "你打算怎麼處理這兩條式子？"
g.messages = [{"role": "user", "content": "題目…我不會開始"}]
g._tutor_turn()
check("等級 0 奉送 → 觸發重生成", g.messages[-1]["content"] == g.regen)
check("log.guards 記錄 spoonfeed", "spoonfeed" in g.state["turns"][-1].guards)

g1b = _GuardStub(tok=None, model=_StubModel(), problem=p_a6)
g1b.first = r"我不能直接給證明。先把 $c_1v_1+c_2v_2=0$ 左乘 $A$，會得到什麼？"
g1b.regen = "自己推導才有用。你打算怎麼利用特徵向量的定義？"
g1b.messages = [{"role": "user", "content": "直接把完整證明寫給我"}]
g1b.state.update(phase="guide", turn_action="refuse_tutor_write")
g1b._tutor_turn()
check("refuse_leak 輪奉送操作 → 也觸發重生成", g1b.messages[-1]["content"] == g1b.regen)

g2 = _GuardStub(tok=None, model=_StubModel(), problem=p_a6)
g2.first, g2.regen = "完全正確。這句話本身就在說鴿籠原理。", "還是沒有問句的重生成稿。"
g2.messages = [{"role": "user", "content": "題目…我的想法是這樣"}]
g2._tutor_turn()
check("無問句且重生成仍無 → 附上固定追問",
      g2.messages[-1]["content"].endswith("那你覺得，下一步該從哪裡下手？"))

g3 = _GuardStub(tok=None, model=_StubModel(), problem=p_a6)
g3.first = r"那我直接告訴你：會得到 $c_2(\lambda_2-\lambda_1)v_2=0$，你能得出 $c_2=0$ 嗎？"
g3.regen = "這一步的關鍵想法是用特徵值乘原式再相減。你能自己動筆推出係數嗎？"
g3.messages = [{"role": "user", "content": "題目…我不會"}]
g3.state["stuck_count"] = 2
g3._tutor_turn()
check("等級 2 出現新算式 → 觸發重生成", g3.messages[-1]["content"] == g3.regen)
check("log.guards 記錄 formula", "formula" in g3.state["turns"][-1].guards)

print("[7] 審閱後盾注入（混合架構）")
from review_backstop import _parse_gaps, _parse_object  # noqa: E402

check("純 JSON 陣列可解析",
      _parse_gaps('["缺 v2≠0 的依據", "區間寫錯"]') == ["缺 v2≠0 的依據", "區間寫錯"])
check("夾雜思考文字仍撈得到陣列",
      _parse_gaps('好的，我檢查完了。\n["鴿籠原理套用前未陳述類別數"]\n以上。')
      == ["鴿籠原理套用前未陳述類別數"])
check("空陣列 = 複核無誤", _parse_gaps("[]") == [])
check("字串元素內含方括號（區間 [0,1]）仍正確解析",
      _parse_gaps('["套用定理前未陳述區間 [0,1] 上的前提"]')
      == ["套用定理前未陳述區間 [0,1] 上的前提"])
check("LaTeX 非法 JSON escape（\\{ \\dots \\leq）降級解析成功",
      _parse_gaps(r'["餘數範圍應為 $\{0,1,\dots,n-1\}$ 且 $0 \leq r < n$"]') is not None)
check("無陣列輸出 → None（降級）", _parse_gaps("我覺得這個證明沒什麼問題。") is None)
check("非字串元素 → 略過該候選", _parse_gaps('[1, 2]') is None)
check("逐步回答後盾的結構化 verdict 可從夾雜文字中解析",
      (_parse_object('分析完畢。 {"verdict":"partial","feedback":"少一項"}',
                     {"correct", "incorrect", "partial", "not_answer", "uncertain"}) or {})
      .get("verdict") == "partial")

# TutorDriver 必須呼叫語意後盾，而不是在本地拿 expected_answer 做字串比較。
import review_backstop as _review_module  # noqa: E402
_judge_original = _review_module.judge_walkthrough_answer
_judge_call = {}


def _fake_judge(statement, reference_proof, step, student_answer, timeout=300):
    _judge_call.update(statement=statement, proof=reference_proof,
                       step=step, answer=student_answer)
    return {"verdict": "correct", "feedback": "數學上等價"}


_review_module.judge_walkthrough_answer = _fake_judge
try:
    _judge_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"],
                                backstop=True)
    _judge_result = _judge_driver._judge_walkthrough_answer(
        "較完整但等價的回答", {"explain": "某步", "check": "得到什麼？",
                              "expected_answer": "短答案"})
finally:
    _review_module.judge_walkthrough_answer = _judge_original
check("walkthrough 評分確實委派給 Review／Rectify 同一後盾模組",
      _judge_result["verdict"] == "correct"
      and _judge_call.get("answer") == "較完整但等價的回答"
      and _judge_driver.state["walkthrough_review_status"] == "correct")

b = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
b.generated_levels = []
b.state["phase"] = "review"
b.state["backstop_gaps"] = ["從 c2(λ2−λ1)v2=0 推 c2=0 缺 v2≠0 的依據"]
sys_gap = b._system(0)
check("有缺漏 → 清單注入 review 指示",
      "v2≠0" in sys_gap and "只依據這份清單" in sys_gap)
b.state["backstop_gaps"] = []
check("空清單 → 注入『未發現缺漏，不要憑空發明問題』",
      "未發現缺漏" in b._system(0))
b.state["backstop_gaps"] = None
check("後盾失敗(None) → 指示與原版一致（降級）",
      b._system(0).endswith(PHASE_INSTRUCTIONS["review"]))
b.state.update(phase="guide", turn_action="respond_attempt")
b.state["backstop_gaps"] = ["度數總和應為 2|E| 而非 |E|"]
check("rectify 階段同樣注入", "2|E|" in b._system(0))
check("REVIEW_BACKSTOP=0 → driver 預設不啟用後盾", b.backstop is False)

print("[8] 自我驗證教學：備課解析 / walkthrough 狀態機 / 同學模式")
from auto_reference import fallback_steps, parse_steps, parse_verdict  # noqa: E402
from tutor_driver import PEER_DISCLAIMER  # noqa: E402

check("verdict pass 可解析",
      parse_verdict('{"verdict": "pass", "issues": []}') == {"verdict": "pass", "issues": []})
check("verdict fail 含 LaTeX escape 降級解析",
      (parse_verdict(r'思考後：{"verdict": "fail", "issues": ["$\frac{p+q}{2}$ 是有理數"]}')
       or {}).get("verdict") == "fail")
check("verdict 垃圾輸出 → None", parse_verdict("我覺得這證明還行。") is None)
s_ok = parse_steps('[{"explain": "先建立包含關係", "check": "Tv 在哪個集合？",'
                   ' "expected_answer": "ker T", "common_errors": ["im T"]},'
                   '{"explain": "套秩零度定理", "check": "兩維度和是多少？",'
                   ' "expected_answer": "n"}]')
check("teach_steps 可解析", s_ok is not None and len(s_ok) == 2 and s_ok[0]["check"])
check("teach_steps 保留答案鍵與 step_id",
      s_ok[0]["expected_answer"] == "ker T" and s_ok[0]["common_errors"] == ["im T"]
      and s_ok[0]["step_id"] != s_ok[1]["step_id"])
_missing_step = parse_steps('[{"explain": "只有講解"}]')
check("teach_steps 缺欄位 → 保留候選供定向修補",
      _missing_step is not None and not _missing_step[0]["expected_answer"])
fb = fallback_steps("第一段的推理由此開始。\n\n第二段接著推出關鍵不等式 a<b。\n\n第三段收束結論。")
check("保底切分：3–6 步、每步都有 step_id 與 expected_answer",
      3 <= len(fb) <= 6 and all(s["step_id"] and s["expected_answer"] for s in fb))
_ONE_PARA = ("因為 f 在區間上連續且可微，由中值定理存在 c 使得 f(b)-f(a)=f'(c)(b-a)，"
             "又 f'(c)>=0，所以 f(b)>=f(a)，故 f 單調不減。$\\blacksquare$")
fb2 = fallback_steps(_ONE_PARA)
check("單段完整證明仍切成 3–6 個小步驟（第一步不含整份證明）",
      3 <= len(fb2) <= 6 and len(fb2[0]["explain"]) < len(_ONE_PARA) * 0.6)
check("保底切分移除 QED 記號，不產生空答案鍵的最後一步",
      "blacksquare" not in fb2[-1]["explain"] and fb2[-1]["expected_answer"])
_TAILCOND = fallback_steps(
    "對 $n\\ge 1$，由二項式定理 $2^n=(1+1)^n\\ge \\binom{n}{2}=\\dfrac{n(n-1)}{2}$（$n\\ge 2$）。"
    "\n\n故 $0\\le \\dfrac{n}{2^n}\\le \\dfrac{2}{n-1}$。\n\n由夾擠定理得 $\\dfrac{n}{2^n}\\to 0$。")
check("答案鍵取主關係式而非句尾括號裡的附帶條件（守門 A6/zh 實測踩過）",
      _TAILCOND[0]["expected_answer"] != "$n\\ge 2$"
      and "binom" in _TAILCOND[0]["expected_answer"])

_walk_prob = {
    "id": "W1", "statement": "測試題", "reference_proof": "步驟甲。\n\n步驟乙。",
    "teach_steps": [{"explain": "教步驟甲", "core_idea": "中值定理",
                      "check": "甲的關鍵定理是什麼？",
                      "expected_answer": "中值定理"},
                    {"explain": "教步驟乙", "core_idea": "有界性",
                     "check": "乙得到什麼結論？",
                      "expected_answer": "有界"}],
}
w = _SemanticWalkStub(tok=None, model=_StubModel(), problem=dict(_walk_prob))
w.generated_levels = []
w.walk_verdicts = ["not_answer", "correct"]
w.judged_steps = []
w.messages = [{"role": "user", "content": "題目…開始"}]
w.step("我不知道，想不出來。")                  # 卡 1
check("卡 1 尚未進入教學", not w.state.get("walk_active"))
w.step("還是不會。")                            # 卡 2 → Level 2 核心想法
r_w = w.step("我仍然不知道。")                  # 卡 3 → 進入 walkthrough
check("連續卡住三次 → 進入 walkthrough",
      w.state.get("walk_active") and w.state["phase"] == "walkthrough"
      and w.state["walk_idx"] == 0)
check("教學輪確定性輸出「一個步驟＋一個確認問題」（不經生成模型）",
      "教步驟甲" in r_w and "甲的關鍵定理是什麼？" in r_w and "第 1/2 步" in r_w)
check("教學輪記下本輪實際呈現的步驟（下一輪據此評分）",
      w.state["walk_presented_idx"] == 0
      and w.state["walk_presented_step"]["expected_answer"] == "中值定理")
r_next = w.step("聽不懂，不明白。")               # 唯一一次機會：揭答並前進
check("答不出來 → 揭示參考答案並直接前進到步驟 2",
      w.state["walk_idx"] == 1 and "中值定理" in r_next and "第 2/2 步" in r_next)
check("逐步回答交給語意後盾，且審閱的是上一輪實際呈現的步驟",
      len(w.judged_steps) == 1 and w.judged_steps[0][2] == "甲的關鍵定理是什麼？")
r_done = w.step("這一步得到的是有界。")             # 後盾判對 → 步驟用盡
check("步驟教完 → review/awaiting_submission 且教學結束",
      not w.state.get("walk_active") and w.state["phase"] == "review"
      and w.state["review_status"] == "awaiting_submission"
      and "參考答案" not in r_done)

# incorrect／partial 不得退回字串比對；後盾不可用時留在原步驟。
wS = _SemanticWalkStub(tok=None, model=_StubModel(), problem=dict(_walk_prob))
wS.generated_levels = []
wS.walk_verdicts = ["incorrect", "unavailable", "correct"]
wS.judged_steps = []
wS.messages = [{"role": "user", "content": "題目…開始"}]
wS.state.update(walk_active=True, walk_idx=0, phase="walkthrough",
                walk_lang="zh")
wS._tutor_turn()
r_rev = wS.step("我覺得是夾擠定理。")
check("答錯只有一次機會 → 當輪揭答並前進", wS.state["walk_idx"] == 1
      and "中值定理" in r_rev and len(wS.judged_steps) == 1)
check("逐步教學答錯時先說明原因，再提供正確答案",
      "stub:incorrect" in r_rev and "正確答案" in r_rev
      and r_rev.index("stub:incorrect") < r_rev.index("正確答案")
      and "正確依據" not in r_rev and "。。" not in r_rev)
r_unavailable = wS.step("還是不知道。")
check("後盾不可用時不消耗步驟、不揭答、不切 phase",
      wS.state["phase"] == "walkthrough" and wS.state["walk_idx"] == 1
      and "保留在目前步驟" in r_unavailable and "正確答案" not in r_unavailable)
check("後盾不可用時不把學生回答誤宣告為錯誤",
      "不把你的回答判為錯誤" in r_unavailable
      and "這個回答尚未正確" not in r_unavailable)
r_last = wS.step("這一步得到有界。")
check("服務恢復且同步回答正確後才轉交稿",
      wS.state["phase"] == "review"
      and wS.state["review_status"] == "awaiting_submission")

# 最後一題答錯時，不可讓自由生成模型在「錯因＋正解」後又說「完全正確」。
w_last = _SemanticWalkStub(tok=None, model=_StubModel(), problem=dict(_walk_prob))
w_last.generated_levels = []
w_last.walk_verdicts = ["incorrect"]
w_last.judged_steps = []
w_last.messages = [{"role": "user", "content": "題目…開始"}]
w_last.state.update(walk_active=True, walk_idx=1, phase="walkthrough",
                    walk_lang="zh")
w_last._tutor_turn()
r_last_wrong = w_last.step("錯誤回答")
check("最後一步答錯 → 確定性揭答後中性請交稿，不生成矛盾稱讚",
      "stub:incorrect" in r_last_wrong and "正確答案" in r_last_wrong
      and "現在請把完整證明" in r_last_wrong
      and "完全正確" not in r_last_wrong and not w_last.generated_levels)

w2 = _SemanticWalkStub(tok=None, model=_StubModel(), problem=dict(_walk_prob))
w2.generated_levels = []
w2.walk_verdicts = []
w2.judged_steps = []
w2.messages = [{"role": "user", "content": "題目…開始"}]
w2.state.update(walk_active=True, walk_idx=0, phase="walkthrough")
w2.step("證明：先由題設得到第一個關係式，因此推出第二個關係式；再把兩個關係式合併，"
        "並逐一驗證所用定理的前提，最後得到題目要求的結論。請幫我審閱。")
check("教學中交草稿仍只算當前確認問題的一次回答",
      w2.state["phase"] == "walkthrough" and w2.state.get("walk_active"))

_PEER_VARIANTS = ["說不定可以從定義下手。你覺得呢？", "或許先試個特例看看？",
                  "要不要從反面假設想想？", "感覺關鍵在那個極限，你怎麼看？"]


class _PeerStub(_StubDriver):
    def _generate(self, level):
        self.generated_levels.append(level)
        return _PEER_VARIANTS[len(self.generated_levels) % len(_PEER_VARIANTS)]

_peer_prob = {"id": "P1", "statement": "未驗證難題", "grounding": "unverified"}
p = _PeerStub(tok=None, model=_StubModel(), problem=dict(_peer_prob))
p.generated_levels = []
check("無參考解 → 同學模式", p.is_peer())
r1 = p.start()
check("同學首輪：確定性加上誠實聲明", r1.startswith(PEER_DISCLAIMER))
check("同學 system 是同儕 persona 非助教",
      "同學" in p._system(0) and "不是助教" in p._system(0)
      and "REFERENCE_PROOF" not in p._system(0))
p.step("你錯了吧，這方向好像不對。")
check("學生質疑 → peer_reflect 反省指示",
      p.state["phase"] == "guide" and p.state["turn_action"] == "peer_reflect"
      and "重新檢查" in p._system(0))
r3 = p.step("好，那我們換個方向？")
check("非質疑輪 → guide/normal action",
      p.state["phase"] == "guide" and p.state["turn_action"] == "normal_guide")
check("同學模式第二輪起不再重複聲明", not r3.startswith(PEER_DISCLAIMER))

print("[9] 英文偵測（雙語支援）")
from tutor_driver import detect_lang, PEER_DISCLAIMER_EN  # noqa: E402

check("純英文 → en", detect_lang("I have no idea how to start this problem.") == "en")
check("繁中 → zh", detect_lang("我不知道怎麼開始。") == "zh")
check("英文夾 LaTeX → en", detect_lang(r"Prove that $\lim_{x\to 2}x^2=4$ using epsilon-delta.") == "en")
check("en stuck: I don't know", is_stuck("I don't know how to continue."))
check("en 實質嘗試不算 stuck",
      not is_stuck("I am not sure, but I tried setting g(x)=f(x)-kx and computing g'(x)=f'(x)-k, then checked the signs at both endpoints of the interval."))
check("en 奉送：left-multiply", is_spoonfeeding("Next, left-multiply both sides by A to get a new equation."))
check("en 引導注意力不算奉送", not is_spoonfeeding("First look at what dividing by n gives you. What remainders can appear?"))

d3 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d3.generated_levels = []
d3.start(opener="I have not started yet. I am very confused, please guide me one tiny step at a time.")
check("英文 session 語言 = en", d3.state.get("lang") == "en")
check("英文首則含 Problem: 前綴", d3.messages[0]["content"].startswith("Problem:"))
d3.step("Just tell me the full proof, stop asking me questions.")
check("en 逼問 → guide/refuse action",
      d3.state["phase"] == "guide" and d3.state["turn_action"] == "refuse_tutor_write")
d3.step("I think we keep only the quadratic term as a lower bound. Is this correct?")
check("en 嘗試 → guide/respond action",
      d3.state["phase"] == "guide" and d3.state["turn_action"] == "respond_attempt")
d3.step("Here is my proof: by the binomial theorem ... please review it.")
check("en guide 中交草稿不當成全文審閱",
      not any(e.get("event") == "FULL_PROOF_SUBMITTED" and e.get("accepted")
              for e in d3.state.get("phase_events", []))
      and not d3.state.get("current_proof_draft")
      and (d3.state.get("phase") == "guide"
           or d3.state.get("review_status") == "awaiting_submission"))
check("en session 的 system 是英文", "Socratic" in d3._system(0))

d4 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d4.generated_levels = []
d4.start()
check("中文 session 語言 = zh", d4.state.get("lang") == "zh")
check("zh system 不變", "蘇格拉底" in d4._system(0))

# 英文同學模式：誠實聲明用英文
pe = _PeerStub(tok=None, model=_StubModel(), problem={"id": "P2", "statement": "An unverified hard problem", "grounding": "unverified"})
pe.generated_levels = []

def _en_gen(level, _p=pe):
    _p.generated_levels.append(level)
    return "Maybe we can start from the definition. What do you think?"
pe._generate = _en_gen
r_en = pe.start(opener="I really am not certain how to attack this, can we think together?")
check("英文同學首輪：加英文誠實聲明", r_en.startswith(PEER_DISCLAIMER_EN))
check("英文同學 system 是英文 peer", "fellow student" in pe._system(0))

print("[10] 重複回覆保底")


class _RepeatStub(TutorDriver):
    calls: int = 0

    def _generate(self, level):
        self.calls += 1
        return "Which hypothesis in the problem verifies one condition of that theorem?"

    def _regen(self, level, note):
        return "What value does the theorem guarantee for f somewhere in the interval?"


d5 = _RepeatStub(tok=None, model=_StubModel(), problem=probs["A6"])
d5.calls = 0
d5.start(opener="I am confused, please guide me step by step.")
r1r = d5.step("I checked continuity on [a,b]. What value are we trying to get?")
check("重複命中後重生成出新句", r1r.startswith("What value"))
check("重複輪標記 repeat 守衛", "repeat" in d5.state["turns"][-1].guards)

# 改寫式重問（換句話問同一題）也要命中：相似度 ≥0.85
d5b = _RepeatStub(tok=None, model=_StubModel(), problem=probs["A6"])
d5b.messages = [{"role": "assistant",
                 "content": "Which hypothesis in the problem verifies one condition of the theorem?"}]
d5b.state["phase"] = "guide"
check("換句話重問（僅一詞之差）→ 判定重複",
      d5b._repeats_previous("Which hypothesis in the problem verifies one condition of that theorem?"))
check("真正的新問題 → 不判重複",
      not d5b._repeats_previous("What does the sign of g'(x) tell you about monotonicity?"))
d5b.state["phase"] = "walkthrough"
check("教學輪使用確定性模板 → 不套用一般回覆的相似度判定",
      not d5b._repeats_previous("Which hypothesis in the problem verifies one condition of that theorem?"))

# 強困惑不受長度門檻限制（長訊息＋明說徹底卡死 → 仍升級）
check("長嘗試＋『毫無頭緒』→ stuck",
      is_stuck("我試著設 g(x)=f(x)-x，然後看它在端點的符號，也想過用中間值定理，"
               "但接下來怎麼把兩個條件連起來我毫無頭緒。"))
check("長嘗試＋completely lost → stuck",
      is_stuck("I tried defining g(x)=f(x)-x and checked the endpoint signs, and I also thought "
               "about the intermediate value theorem, but how to connect the two conditions "
               "I'm completely lost."))

print("[11] 語言跟隨學生（英文題＋中文學生等混合）")
_en_prob = {"id": "B1", "statement": "Prove that a continuous function on [a,b] with f(a)<0<f(b) has a root in (a,b).",
            "reference_proof": "Let S={x:f(x)<0}, c=sup S. ..."}
# 英文題 + 學生中文開場 → session 跟隨學生＝中文
dm = _StubDriver(tok=None, model=_StubModel(), problem=dict(_en_prob))
dm.generated_levels = []
dm.start(opener="老師我完全不知道怎麼開始，可以給我第一個引導提示嗎？")
check("英文題＋中文開場 → lang=zh（跟學生）", dm.state.get("lang") == "zh")
check("英文題＋中文開場 → 前綴用中文『題目：』", dm.messages[0]["content"].startswith("題目："))
# 英文題 + 自動開場（鎖英文）→ 學生改中文（夠長）→ 切回中文
dm2 = _StubDriver(tok=None, model=_StubModel(), problem=dict(_en_prob))
dm2.generated_levels = []
dm2.start()
check("英文題自動開場 → 初始 lang=en", dm2.state.get("lang") == "en")
dm2.step("我還是看不懂這一步，可以換個方式解釋嗎？")
check("學生改講中文（夠長）→ 切換 lang=zh", dm2.state.get("lang") == "zh")
# 短訊息／純數學不誤切
dm2.step("ok")
check("短訊息不觸發誤切（維持 zh）", dm2.state.get("lang") == "zh")

print("[12] 回問保底：措辭輪換＋連續缺問句不硬補")


class _NoQStub(TutorDriver):
    """生成與重生成都不含問句 → 每輪都走保底附加路徑。

    重生成稿刻意**不**宣告整份證明完成：否則會命中 _TUTOR_DONE_RE 而 arm
    done_closed，保底句整段停用，就測不到本組要測的「措辭輪換」了
    （該互動另由 [12b] 專門驗證）。"""

    def _generate(self, level):
        return f"Good, that completes the argument (turn {len(self.messages)})."

    def _regen(self, level, note):
        return f"Nice work, that part holds up (turn {len(self.messages)})."


nq = _NoQStub(tok=None, model=_StubModel(), problem=dict(_en_prob))
r1 = nq.start(opener="Please guide me on this problem, I want to try it myself.")
check("首輪保底附上追問（第 1 種措辭）", r1.rstrip().endswith("should start?"))
r2 = nq.step("Here is my full attempt with all steps written out, please take a look at the whole thing and tell me.")
check("上一輪已補過 → 連續缺問句不再硬補", not r2.rstrip().endswith("?"))
r3 = nq.step("I double-checked the boundary case works too, and here is the cleaned-up version of that part.")
check("隔一輪再缺問句 → 換第 2 種措辭", r3.rstrip().endswith("next?"))
check("fb_idx 已輪轉到 2", nq.state.get("fb_idx") == 2)
r4 = nq.step("Thanks, that's all — my proof is now complete and I have no further questions.")
check("學生致謝宣告完成 → 不再追問", not r4.rstrip().endswith("?"))
nqz = _NoQStub(tok=None, model=_StubModel(), problem=probs["A6"])
nqz.start(opener="請引導我，我想自己試試看。")
rz = nqz.step("謝謝，我都清楚了，沒有其他問題。")
check("中文致謝收尾 → 不再追問", not rz.rstrip().endswith("？") and not rz.rstrip().endswith("?"))

print("[12b] repeat 的重生成若宣告整份證明完成 → arm done_closed，不得再補保底句")
# repeat 守衛排在回問保底之前，因此它的重生成稿會成為本輪最終回覆。若那一稿親口
# 宣告整份證明完成，補上「下一步該從哪裡下手？」正是弱點 #7／X4 型的扣分行為。


class _RepeatDoneStub(TutorDriver):
    """初稿與上一則助教回覆逐字相同（觸發 repeat），重生成稿宣告整份證明完成。"""
    SAME = "這個方向是對的，你已經把關鍵的不等式建立起來了，接下來只要收尾就好。"

    def _generate(self, level):
        return self.SAME

    def _regen(self, level, note):
        return "是的，整個證明完成了。"


rd = _RepeatDoneStub(tok=None, model=_StubModel(), problem=probs["A6"])
rd.messages = [{"role": "user", "content": "題目…"},
               {"role": "assistant", "content": _RepeatDoneStub.SAME},
               {"role": "user", "content": "所以就這樣結束了嗎？"}]
rd._tutor_turn()
check("repeat 重生成的 Tutor 宣告不得 arm closed",
      not rd.state.get("done_closed") and rd.state["phase"] == "guide")

print("[13] guide 中宣告完成仍不接受交稿")
dc = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
dc.generated_levels = []
dc.start(opener="請引導我。")
dc.step("設 a_n = n^(1/n) − 1，由二項式定理 n ≥ C(n,2)a_n²，解出 a_n ≤ √(2/(n−1))，夾擠得 a_n→0，"
        "所以極限是 1，這樣就證完了。")
check("長論證＋宣告證完 → 不啟動全文審閱",
      not any(e.get("event") == "FULL_PROOF_SUBMITTED" and e.get("accepted")
              for e in dc.state.get("phase_events", []))
      and not dc.state.get("current_proof_draft"))
dc2 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
dc2.generated_levels = []
dc2.start(opener="請引導我。")
dc2.step("證完了！")
check("短宣告無內容 → 不路由 review", dc2.state.get("phase") != "review")
dc3 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
dc3.generated_levels = []
dc3.start(opener="Please guide me through this one.")
dc3.step("Thanks so much for your help today — my proof is now complete and I have no further questions at all.")
check("致謝式收尾（含 thanks）→ 不當交稿", dc3.state.get("phase") != "review")
dc4 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
dc4.generated_levels = []
dc4.start(opener="Please guide me through this one.")
dc4.step("Setting a_n = n^(1/n) − 1, the binomial theorem gives n ≥ C(n,2)a_n², hence a_n ≤ √(2/(n−1)) → 0 "
         "by squeezing, so the limit equals 1, and that completes the proof.")
check("英文長論證＋宣告 → 不啟動全文審閱",
      not any(e.get("event") == "FULL_PROOF_SUBMITTED" and e.get("accepted")
              for e in dc4.state.get("phase_events", []))
      and not dc4.state.get("current_proof_draft"))

print("[14] 收尾 arm 時機、追問抑制與稱讚校準（update.md 對話稽核）")


# 口頭宣告式交稿（不以「證明：」開頭 → 走 _CLAIM_DONE_RE 分支），且 δ 取法有缺漏
_CLAIM = ("我把式子拆成 |x-2||x+2|，先限制 |x-2|<1 得到 |x+2|<5，"
          "再取 δ = ε/5，這樣 |x^2-4| < 5·(ε/5) = ε，因此得證。")

rv = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A2"])
rv.generated_levels = []
rv.review_reply = "你取 δ 的時候，前面 |x-2|<1 的限制還保得住嗎？"
rv.start(opener="請引導我。")
rv._enter_awaiting_submission(event="READINESS_PASSED", source="unit_test")
rv.step(_CLAIM)
check("受邀後的宣告式交稿 → review", rv.state.get("phase") == "review")
check("審閱結果未知時不得 arm done_closed（F3：arm 早於審閱＝糾錯會被吞）",
      not rv.state.get("done_closed"))
rv.step("你是說 δ 的取法有問題嗎？")
check("審閱指出缺漏後、學生帶問句追問 → 不進 closed，糾錯續行（F3 回歸）",
      rv.state.get("phase") != "closed")

rv2 = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A2"])
rv2.generated_levels = []
rv2.review_reply = "完全正確，每一步都有依據，這份證明可以了。"
rv2.start(opener="請引導我。")
rv2._enter_awaiting_submission(event="READINESS_PASSED", source="unit_test")
rv2.step(_CLAIM)
check("審閱通過（該輪回覆無問句）→ arm done_closed（F1：不靠措辭正則）",
      not rv2.state.get("done_closed") and rv2.state["phase"] == "review")
rv2._apply_phase_event("REVIEW_PASSED", source="unit_test_review_judge")
rv2.step("原來取 min 是為了同時控制兩個因子。")
check("審閱通過後的反思（無謝謝、無問號）→ closed", rv2.state.get("phase") == "closed")


class _NoQ2Stub(TutorDriver):
    """首輪帶問句（不觸發保底），之後每輪都不含問句 → 測追問保底是否被抑制。"""

    def _generate(self, level):
        if len(self.messages) <= 1:
            return "先想想 |x^2-4| 可以怎麼分解？"
        return f"這一點你說得有道理，我再想一下（第{len(self.messages)}輪）。"

    def _regen(self, level, note):
        return f"確實值得再檢查一次（第{len(self.messages)}輪）。"


nq2 = _NoQ2Stub(tok=None, model=_StubModel(), problem=probs["A2"])
nq2.start(opener="請引導我，我想自己試試看。")
check("首輪有問句 → 未動用保底", "fallback" not in nq2.state["turns"][-1].guards)
nq2.state.update(phase="review", review_status="checking")
nq2._apply_phase_event("REVIEW_PASSED", source="unit_test_review_judge")
r_ch = nq2.step("你錯了吧，這一步根本不成立。")
check("證明已確認完成後 → 即使落回一般流程也不再硬補追問句",
      not r_ch.rstrip().endswith("？") and "fallback" not in nq2.state["turns"][-1].guards)

# 放寬 _TUTOR_DONE_RE 後的邊界守衛：mid-proof 誤 arm 會讓助教在證明中途就進收尾模式
# （被指示「不要再拋出任何新問題」）＝比漏 arm 嚴重得多，兩種近似措辭都必須擋掉
for _txt, _why in (("很好，這一步的證明完成了。", "只講某一步完成"),
                   ("你的證明還沒完成，中間少了一個條件。", "否定式"),
                   ("這樣整個證明就完成了，你自己補上了關鍵那一步。", "確實宣告整份完成")):
    _d = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
    _d.generated_levels = []
    _d.start()
    _d.messages.append({"role": "assistant", "content": _txt})
    _d.step("嗯，我想想看。")
    check(f"Tutor 說「{_txt[:12]}…」（{_why}）不得 arm done_closed",
          not _d.state.get("done_closed"))

# F2：逐輪 CLI 跨行程還原——done_closed / fb_idx / lang / 上輪 guards 都要活下來
snap = json.loads(json.dumps(rv2.dump_state()))
rv3 = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A2"])
rv3.load_state(snap)
check("dump/load 保住 done_closed（F2：CLI 每輪重建 driver）",
      rv3.state.get("done_closed") is True)
check("dump/load 保住 messages 與 lang",
      rv3.messages == rv2.messages and rv3.state.get("lang") == rv2.state.get("lang"))
nq_snap = json.loads(json.dumps(nq2.dump_state()))
nq3 = _NoQ2Stub(tok=None, model=_StubModel(), problem=probs["A2"])
nq3.load_state(nq_snap)
check("dump/load 保住 fb_idx（否則保底句永遠是同一句）",
      nq3.state.get("fb_idx") == nq2.state.get("fb_idx"))
check("dump/load 保住上一輪 guards（連兩輪不硬補的守衛才有效）",
      (nq3.state["turns"][-1].guards if nq3.state["turns"] else [])
      == (nq2.state["turns"][-1].guards if nq2.state["turns"] else []))

# F6：稱讚校準——後盾已回報缺漏卻無條件背書 → 重生成（錯誤背書是最嚴重的一種過譽）
op = _GuardStub(tok=None, model=_StubModel(), problem=probs["A2"])
op.first = "完全正確，你的證明沒有任何缺漏，可以收工了。"
op.regen = "主要方向正確，但取 δ 那一行還有一個條件沒顧到，你看得出是哪個嗎？"
op.messages = [{"role": "user", "content": "證明：我先把 |x^2-4| 拆開……"}]
op.state["phase"] = "review"
op.state["backstop_gaps"] = ["取 δ 時未保留 |x-2|<1 的限制"]
op._tutor_turn()
check("後盾已回報缺漏卻說『完全正確』→ 重生成（F6 錯誤背書）",
      op.messages[-1]["content"] == op.regen)
check("log.guards 記錄 overpraise", "overpraise" in op.state["turns"][-1].guards)

op2 = _GuardStub(tok=None, model=_StubModel(), problem=probs["A2"])
op2.first = "很好，你的論證邏輯無縫，已經超過大多數學生的水準了。"
op2.regen = "這一步的依據交代得清楚。接下來 |x+2| 你打算怎麼估？"
op2.messages = [{"role": "user", "content": "我覺得這樣拆應該就可以了"}]
op2.state.update(phase="guide", turn_action="respond_attempt")
op2._tutor_turn()
check("訓練集 0 次的誇飾腔（邏輯無縫／超過大多數）→ 重生成（F6 基底模型漂移）",
      op2.messages[-1]["content"] == op2.regen)

op2b = _GuardStub(tok=None, model=_StubModel(), problem=probs["A2"])
op2b.first = "拆成兩個絕對值這一步完全正確。那取 δ 的時候，|x-2|<1 這個限制還在嗎？"
op2b.regen = "（不該被觸發的重生成稿）"
op2b.messages = [{"role": "user", "content": "證明：我先把 |x^2-4| 拆開……"}]
op2b.state["phase"] = "review"
op2b.state["backstop_gaps"] = ["取 δ 時未保留 |x-2|<1 的限制"]
op2b._tutor_turn()
check("有缺漏但已用問句點出（局部肯定＋引導）→ 不算錯誤背書，不重生成",
      op2b.messages[-1]["content"] == op2b.first)

op3 = _GuardStub(tok=None, model=_StubModel(), problem=probs["A2"])
op3.first = "很好，這一步是對的。接下來 |x+2| 怎麼估？"
op3.regen = "（不該被觸發的重生成稿）"
op3.messages = [{"role": "user", "content": "我先把它拆成兩個絕對值相乘"}]
op3._tutor_turn()
check("正常肯定（很好／這一步是對的）→ 不觸發 overpraise",
      op3.messages[-1]["content"] == op3.first)

check("後盾複核無誤時的『完全正確』→ is_overpraising 不成立（肯定是正當的）",
      not is_overpraising("完全正確，每一步的依據都交代了。", []))
op4 = _GuardStub(tok=None, model=_StubModel(), problem=probs["A2"])
op4.first = "完全正確，每一步的依據都交代了。"
op4.regen = "（不該被觸發的重生成稿）"
op4.messages = [{"role": "user", "content": "證明：……（完整草稿）"}]
op4.state.update(phase="guide", turn_action="respond_attempt")
op4.state["backstop_gaps"] = []          # 後盾複核無誤 → 肯定是正當的
op4._tutor_turn()
check("後盾複核無誤時的『完全正確』→ 不觸發 overpraise",
      op4.messages[-1]["content"] == op4.first)

print("[15] 助教自行要求交稿也要記錄（守門對話 H5 型）")
# driver 只在 _UNDERSTOOD_RE 命中時才進 writeup_request；但模型常自己開口要求交稿，
# 沒記下來的話，學生接著交出的草稿不會被判定為交稿 → 不進 review → 拿不到審閱通過
# 訊號 → 收尾時被補上保底追問句（2026-07-29 守門 H5/zh 實例）。
_H5_DRAFT = ("好啊，我試試看！是不是要先設 $f(t) = e^t$，然後說明它在 $[0, x]$ 連續、"
             "在 $(0, x)$ 可微，所以存在 $c \\in (0, x)$ 使得 $\\frac{e^x - 1}{x} = e^c$？"
             "接下來再把 $c > 0$ 推出 $e^c > 1$ 寫上去，這樣邏輯就完整了嗎？")

wa = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A6"])
wa.generated_levels = []
wa.review_reply = "完全正確，你甚至把均值定理可用的前提都補上了。"
wa.start()
wa.messages.append({"role": "assistant",
                    "content": "對，你已經自己看出「正式證明」需要把前提明確寫出來。"
                               "那你能把完整的證明寫出來，我來幫你審閱嗎？"})
wa.step(_H5_DRAFT)
check("只有文字看似要求交稿，不會反向設定 writeup_asked",
      not wa.state.get("writeup_asked"))
check("→ 未經系統確認交稿準備度的問句式推導不誤送全文審閱",
      wa.state.get("phase") != "closed" and not wa.state.get("done_closed"))
check("→ 未完成全文審閱時不得 arm done_closed",
      not wa.state.get("done_closed"))

wn = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A6"])
wn.generated_levels = []
wn.start()
wn.messages.append({"role": "assistant",
                    "content": "我不能直接寫出完整證明給你，自己推導才真的有用。"
                               "你打算先用題目的哪個條件？"})
wn.step("好吧，那我自己試試看，先從二項式定理下手。")
check("拒絕洩漏時提到「寫出完整證明」→ 不得誤設 writeup_asked（反向閘）",
      not wn.state.get("writeup_asked"))

print("[16] 對話中自然證完（全程沒有交稿步驟）→ 保底改請交稿（守門對話 X4 型）")
# X4/zh：學生一問一答把推導走完，助教回「完全正確…」不含問句 → 舊行為補上通用
# 追問「那你覺得，下一步該從哪裡下手？」，評審判為「已完成卻多餘追問」。
# 這種情境正確的下一步是請他把證明寫出來（→ review → 審閱通過 → 收尾）。
_COMBINED_READY = {
    "mathematically_correct": True,
    "level_policy_pass": True,
    "introduces_new_proof_idea": False,
    "completes_any_unfinished_step": False,
    "leaks_final_conclusion": False,
    "ready_for_writeup": True,
    "missing_core_step": "",
    "readiness_confidence": 0.99,
    "feedback": "學生已親自走完所有必要連結",
}
x4 = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
x4.first = ("完全正確。核心是把「相異特徵值」這個條件用上，逼出係數只能是零。"
            "你自己的推導比任何提示都清楚。")
x4.regen = x4.first                      # 重生成仍無問句 → 走保底路徑
x4._review_guide_reply = lambda _reply, _level: dict(_COMBINED_READY)
x4.messages = [
    {"role": "user", "content": "題目…我不知道怎麼開始。"},
    {"role": "assistant", "content": "先看看那個線性組合等於零的假設能怎麼用？"},
    {"role": "user", "content": "我想把 c1v1+c2v2=0 兩邊左乘 A 試試看。"},
    {"role": "assistant", "content": "很好，那左乘之後的新式子要怎麼跟原式配合？"},
    {"role": "user", "content": "應該是相減吧？可是兩項好像都還在。"},
    {"role": "assistant", "content": "再想想，相減前要不要先讓其中一項的係數一致？"},
    {"role": "user", "content": "原式同乘 λ1 再相減，就得到 c2(λ2−λ1)v2=0；"
                                "因為 v2≠0 且特徵值相異，所以只能是 c2=0，"
                                "再代回原本的式子就得到 c1 也必須是 0 了！"},
]
x4.state["student_state_decision"] = {
    "phase": "guide", "turn_action": "respond_attempt",
    "has_actionable_math": True, "advances_solution": True,
    "requested_writer": "none",
}
x4.state["proof_progress_revision"] = 3
x4._tutor_turn()
_out = x4.messages[-1]["content"]
check("深度對話＋實質推導＋總評式肯定且無問句 → 補的是交稿請求",
      "寫出來" in _out and "下一步該從哪裡下手" not in _out)
check("→ 同時記下 writeup_asked（下一則草稿才進得了 review）",
      x4.state.get("writeup_asked") is True)
check("log.guards 記為 writeup_readiness",
      "writeup_readiness" in x4.state["turns"][-1].guards)

# 一般引導的完成偵測不能藏在「沒有問句」保底裡：即使 Tutor 候選本身已有問句，
# 只要學生本輪帶入的新數學內容已讓 Thinking 判定骨架完整，也要由系統主動請交稿。
auto = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
auto.first = "完全正確，你已把核心步驟接起來了。你還想檢查哪一個步驟？"
auto.regen = "思路已完整。現在請整理一份完整證明。"
auto.messages = list(x4.messages)
auto.state["student_state_decision"] = {
    "phase": "guide", "turn_action": "respond_attempt",
    "has_actionable_math": True, "advances_solution": True,
    "requested_writer": "none",
}
auto.state["proof_progress_revision"] = 3
auto._review_guide_reply = lambda _reply, _level: dict(_COMBINED_READY)
auto._tutor_turn()
check("一般引導有新進展時主動檢查 readiness，不依賴 Tutor 缺問句",
      auto.state.get("phase") == "review"
      and auto.state.get("review_status") == "awaiting_submission"
      and auto.state.get("writeup_asked") is True
      and "完整證明" in auto.messages[-1]["content"])

# 「請要求我寫」的書寫者是學生，不是 Tutor；本地角色訊號須在 Thinking 前就可用。
role_probe = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"])
role_context = role_probe._student_state_context("請要求我寫完整證明")
check("要求學生自己交稿不被當成 Tutor 代寫",
      role_context["student_requests_writeup"]
      and role_context["requested_writer"] == "student"
      and not role_context["demand"])

# 合併審查每次 Thinking 有完整 timeout；整輪的第二次呼叫由 Controller 統一管理。
import review_backstop as _readiness_backstop
_old_retry_parsed = _readiness_backstop._retry_parsed
_readiness_call = {}
_old_guide_timeout = os.environ.get("GUIDE_REPLY_REVIEW_TIMEOUT")


def _fake_readiness_retry(system, user, parser, **kwargs):
    _readiness_call.update(kwargs)
    return dict(_COMBINED_READY)


try:
    # 即使舊環境仍設為 60，也不得縮短這次要求的完整單次預算。
    os.environ["GUIDE_REPLY_REVIEW_TIMEOUT"] = "60"
    _readiness_backstop._retry_parsed = _fake_readiness_retry
    budget = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
    budget.messages = list(x4.messages)
    budget.state["proof_progress_revision"] = 3
    budget.state["student_state_decision"] = {
        "phase": "guide", "has_actionable_math": True, "advances_solution": True,
        "requested_writer": "none",
    }
    _budget_review = budget._review_guide_reply("完全正確，整個骨架已完成。", 0)
finally:
    _readiness_backstop._retry_parsed = _old_retry_parsed
    if _old_guide_timeout is None:
        os.environ.pop("GUIDE_REPLY_REVIEW_TIMEOUT", None)
    else:
        os.environ["GUIDE_REPLY_REVIEW_TIMEOUT"] = _old_guide_timeout
check("合併審查使用足夠輸出預算，且每次嘗試保有完整 timeout",
      _budget_review and _readiness_call.get("num_predict", 0) >= 8192
      and _readiness_call.get("attempts") == 1
      and _readiness_call.get("per_attempt_timeout", 0) >= 120
      and isinstance(_readiness_call.get("response_format"), dict)
      and "completes_any_unfinished_step" in
          _readiness_call["response_format"]["properties"]
      and isinstance(_readiness_call.get("diagnostics"), dict))

print("[16a] 通用引導語意審查＋readiness unavailable 下一輪重試")

# 審查器只看題目、參考證明、累積對話、level/action 與候選回覆；不使用題型關鍵詞表。
_guide_review_calls = []


def _fake_guide_retry(system, user, parser, **kwargs):
    _guide_review_calls.append({
        "system": system, "payload": json.loads(user), "kwargs": kwargs,
    })
    return parser(json.dumps({
        "mathematically_correct": True,
        "level_policy_pass": True,
        "introduces_new_proof_idea": False,
        "completes_any_unfinished_step": False,
        "leaks_final_conclusion": False,
        "ready_for_writeup": False,
        "missing_core_step": "尚未完成",
        "readiness_confidence": 0.95,
        "feedback": "",
    }, ensure_ascii=False))


_old_retry_parsed = _readiness_backstop._retry_parsed
try:
    _readiness_backstop._retry_parsed = _fake_guide_retry
    guide_probe = TutorDriver(tok=None, model=_StubModel(), problem=probs["A6"],
                              backstop=True)
    guide_probe.messages = [
        {"role": "user", "content": "我先完成了目前這一步。"},
        {"role": "assistant", "content": "Tutor 曾提出一個新構造。"},
        {"role": "user", "content": "我只確認自己剛才寫的內容。"},
    ]
    _guide_probe_results = []
    for _guide_action in ("normal_guide", "respond_attempt",
                          "answer_clarification", "refuse_tutor_write"):
        guide_probe.state.update(phase="guide", turn_action=_guide_action,
                                 student_state_decision={"advances_solution": True})
        _guide_probe_results.append(
            guide_probe._review_guide_reply("那下一個理由是什麼？", 2))
finally:
    _readiness_backstop._retry_parsed = _old_retry_parsed
check("所有 tutor guide action 共用同一個 Thinking 語意審查器",
      all(result is not None for result in _guide_probe_results)
      and {call["payload"]["turn_action"] for call in _guide_review_calls} == {
          "normal_guide", "respond_attempt", "answer_clarification",
          "refuse_tutor_write"}
      and all(call["payload"]["student_messages"] == [
                  "我先完成了目前這一步。", "我只確認自己剛才寫的內容。"]
              and all("Tutor 曾提出" not in item
                      for item in call["payload"]["student_messages"])
              and "最新學生步驟若錯" in call["system"]
              and "尚未完整，本身絕不能成為 mathematically_correct=false" in
                  call["system"]
              and "假定該步已完成" in call["system"]
              and "絕不能取得學生所有權" in call["system"]
              and call["kwargs"].get("num_predict", 0) >= 8192
              and call["kwargs"].get("attempts") == 1
              and call["kwargs"].get("per_attempt_timeout", 0) >= 120
              and isinstance(call["kwargs"].get("response_format"), dict)
              for call in _guide_review_calls))


class _GuidePolicyStub(TutorDriver):
    """以預排審查結果驗證：政策不合格只重生成一次。"""
    first: str
    reviews: list
    regen_reply: str
    regen_calls: int

    def _generate(self, level):
        return self.first

    def _review_guide_reply(self, reply, level):
        return self.reviews.pop(0)

    def _regen(self, level, note):
        self.regen_calls += 1
        return self.regen_reply


_review_fail = {
    "mathematically_correct": False,
    "level_policy_pass": False,
    "introduces_new_proof_idea": True,
    "completes_any_unfinished_step": True,
    "leaks_final_conclusion": True,
    "ready_for_writeup": False,
    "missing_core_step": "學生尚未完成下一個連結",
    "readiness_confidence": 0.95,
    "feedback": "Tutor 已替學生完成缺少的推導並說出結論",
}
_review_pass = {
    "mathematically_correct": True,
    "level_policy_pass": True,
    "introduces_new_proof_idea": False,
    "completes_any_unfinished_step": False,
    "leaks_final_conclusion": False,
    "ready_for_writeup": False,
    "missing_core_step": "學生尚未完成下一個連結",
    "readiness_confidence": 0.95,
    "feedback": "",
}
policy = _GuidePolicyStub(tok=None, model=_StubModel(), problem=probs["A6"],
                          backstop=True)
policy.state.update(phase="guide", turn_action="respond_attempt", _regens=0)
policy.reviews = [dict(_review_fail), dict(_review_pass)]
policy.regen_reply = "先只處理尚未銜接的理由。你認為下一個推理依據是什麼？"
policy.regen_calls = 0
policy_log = TurnLog(level=2, stuck_count=2)
policy_reply = policy._enforce_guide_reply_policy("因此答案已經成立。", 2, policy_log)
check("語意審查失敗後重生成一次，複審通過才送出",
      policy_reply == policy.regen_reply and policy.regen_calls == 1
      and policy.state["guide_reply_review"]["status"] == "regenerated_passed"
      and policy.state["guide_reply_review"]["thinking_calls"] == 2
      and "guide_policy" in policy_log.guards)

idea_only_fail = dict(_review_pass)
idea_only_fail.update(
    level_policy_pass=True, introduces_new_proof_idea=True,
    feedback="Tutor 提出了學生尚未提出的新構造")
idea_policy = _GuidePolicyStub(
    tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
idea_policy.state.update(phase="guide", turn_action="normal_guide", _regens=0)
idea_policy.reviews = [idea_only_fail, dict(_review_pass)]
idea_policy.regen_reply = "先只看題目已給的條件。你注意到哪些關係？"
idea_policy.regen_calls = 0
idea_log = TurnLog(level=0, stuck_count=0)
idea_reply = idea_policy._enforce_guide_reply_policy(
    "先構造一個新的輔助函數，你會怎麼選？", 0, idea_log)
check("L0/L1 即使 level_policy_pass 誤判 true，新證明構造欄位仍會攔截",
      idea_reply == idea_policy.regen_reply and idea_policy.regen_calls == 1
      and "guide_policy" in idea_log.guards)

respond_idea_policy = _GuidePolicyStub(
    tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
respond_idea_policy.state.update(
    phase="guide", turn_action="respond_attempt", _regens=0)
respond_idea_policy.reviews = [dict(idea_only_fail), dict(_review_pass)]
respond_idea_policy.regen_reply = "先只核對你剛才完成的部分。下一個缺少的主張是什麼？"
respond_idea_policy.regen_calls = 0
respond_idea_log = TurnLog(level=2, stuck_count=0)
respond_idea_reply = respond_idea_policy._enforce_guide_reply_policy(
    "接著構造一個新輔助函數，你會怎麼選？", 2, respond_idea_log)
check("respond_attempt 不因 level=2 而取得學生尚未提出的新想法",
      respond_idea_reply == respond_idea_policy.regen_reply
      and respond_idea_policy.regen_calls == 1
      and "guide_policy" in respond_idea_log.guards)

wrong_step_review = dict(_review_pass)
wrong_step_review.update(
    mathematically_correct=False, level_policy_pass=False,
    completes_any_unfinished_step=True,
    feedback="學生最新一步錯誤，Tutor 卻稱讚並跳到後續步驟")
wrong_step_policy = _GuidePolicyStub(
    tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
wrong_step_policy.state.update(
    phase="guide", turn_action="respond_attempt", _regens=0)
wrong_step_policy.reviews = [wrong_step_review, dict(_review_pass)]
wrong_step_policy.regen_reply = "先檢查你剛才套用定理後，結論涉及哪一階導數？"
wrong_step_policy.regen_calls = 0
wrong_step_log = TurnLog(level=0, stuck_count=0)
wrong_step_reply = wrong_step_policy._enforce_guide_reply_policy(
    "非常好。現在直接進入最後一步。", 0, wrong_step_log)
check("錯誤學生步驟被稱讚或跳過時，既有數學／未完成步驟欄位會攔截",
      wrong_step_reply == wrong_step_policy.regen_reply
      and wrong_step_policy.regen_calls == 1
      and "guide_policy" in wrong_step_log.guards)

unfinished_only_fail = dict(_review_pass)
unfinished_only_fail.update(
    completes_any_unfinished_step=True,
    feedback="Tutor 雖留下更後面的問題，仍先替學生完成了一個中間推論")
unfinished_policy = _GuidePolicyStub(
    tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
unfinished_policy.state.update(
    phase="guide", turn_action="respond_attempt", _regens=0)
unfinished_policy.reviews = [unfinished_only_fail, dict(_review_pass)]
unfinished_policy.regen_reply = "你目前只確認了端點條件；能自己推出緊接著的結論嗎？"
unfinished_policy.regen_calls = 0
unfinished_log = TurnLog(level=0, stuck_count=0)
unfinished_reply = unfinished_policy._enforce_guide_reply_policy(
    "所以導數在兩段各有一個零點；接著你會怎麼做？", 0, unfinished_log)
check("即使仍留下一個更後面的問題，Tutor 完成任何未完成中間步驟仍會被攔截",
      unfinished_reply == unfinished_policy.regen_reply
      and unfinished_policy.regen_calls == 1
      and "guide_policy" in unfinished_log.guards)

turn_policy = _GuidePolicyStub(tok=None, model=_StubModel(), problem=probs["A6"],
                               backstop=True)
turn_policy.state.update(phase="guide", turn_action="normal_guide")
turn_policy.messages = [{"role": "user", "content": "我目前只完成第一個步驟。"}]
turn_policy.first = "所以最終結論已經成立，你看懂了嗎？"
turn_policy.regen_reply = "先停在目前的缺口。你認為下一個推理依據是什麼？"
turn_policy.reviews = [dict(_review_fail), dict(_review_pass)]
turn_policy.regen_calls = 0
turn_policy_reply = turn_policy._tutor_turn()
check("_tutor_turn 送出前確實套用通用語意審查",
      turn_policy_reply == turn_policy.regen_reply
      and turn_policy.regen_calls == 1
      and "guide_policy" in turn_policy.state["turns"][-1].guards)

clarification_policy = _GuidePolicyStub(
    tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
clarification_policy.state.update(
    phase="guide", turn_action="answer_clarification", _regens=0)
clarification_policy.reviews = [dict(_review_fail), dict(_review_pass)]
clarification_policy.regen_reply = "先只處理你問的局部連結。你能檢查這一步的依據嗎？"
clarification_policy.regen_calls = 0
clarification_log = TurnLog(level=0, stuck_count=0)
clarification_reply = clarification_policy._enforce_guide_reply_policy(
    "兩函數在一點值相等，所以二階導數也相等。", 0, clarification_log)
check("answer_clarification 的錯誤數學敘述也會被攔截",
      clarification_reply == clarification_policy.regen_reply
      and clarification_policy.regen_calls == 1
      and "guide_policy" in clarification_log.guards)

policy_fail2 = _GuidePolicyStub(tok=None, model=_StubModel(), problem=probs["A6"],
                                backstop=True)
policy_fail2.state.update(phase="guide", turn_action="normal_guide", _regens=0)
policy_fail2.reviews = [dict(_review_fail), dict(_review_fail)]
policy_fail2.regen_reply = "仍然直接給出最終結論。"
policy_fail2.regen_calls = 0
policy_fail2_log = TurnLog(level=0, stuck_count=0)
policy_fail2_reply = policy_fail2._enforce_guide_reply_policy(
    "直接給出最終結論。", 0, policy_fail2_log)
check("第二稿仍不合格時不做第三次生成，改用無解題內容的安全問句",
      policy_fail2.regen_calls == 1
      and "最終結論" not in policy_fail2_reply
      and "？" in policy_fail2_reply
      and "guide_policy_unresolved" in policy_fail2_log.guards)

policy_unavailable = _GuidePolicyStub(
    tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
policy_unavailable.state.update(
    phase="guide", turn_action="answer_clarification", _regens=0)
policy_unavailable.reviews = [None, None]
policy_unavailable.regen_calls = 0
policy_unavailable_log = TurnLog(level=0, stuck_count=0)
policy_unavailable_reply = policy_unavailable._enforce_guide_reply_policy(
    "兩函數值相等，所以導數相等。", 0, policy_unavailable_log)
check("guide 審查 unavailable 時不再放行未驗證的數學內容",
      "導數相等" not in policy_unavailable_reply
      and "guide_policy_unavailable" in policy_unavailable_log.guards
      and policy_unavailable.state["guide_reply_review"]["thinking_calls"] == 2)

final_repeat_policy = _GuidePolicyStub(
    tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
final_repeat_policy.state.update(
    phase="guide", turn_action="normal_guide", guide_safe_fb_idx=0)
final_repeat_policy.messages = [
    {"role": "assistant", "content": _SAFE_GUIDE_REVIEW_FALLBACKS[0]},
    {"role": "user", "content": "我還是不知道。"},
    {"role": "assistant", "content": "先只看目前已知條件。你注意到什麼？"},
    {"role": "user", "content": "仍然沒想法。"},
]
final_repeat_log = TurnLog(level=0, stuck_count=0)
final_repeat_reply = final_repeat_policy._final_guide_repeat_guard(
    _SAFE_GUIDE_REVIEW_FALLBACKS[0], final_repeat_log)
check("合併審查後的 Controller 保底也受近三輪通用去重守衛",
      final_repeat_reply != _SAFE_GUIDE_REVIEW_FALLBACKS[0]
      and final_repeat_reply.endswith("？")
      and "final_repeat" in final_repeat_log.guards)

final_turn_policy = _GuidePolicyStub(
    tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
final_turn_policy.state.update(
    phase="guide", turn_action="normal_guide", guide_safe_fb_idx=0)
final_turn_policy.messages = [
    {"role": "assistant", "content": _SAFE_GUIDE_REVIEW_FALLBACKS[0]},
    {"role": "user", "content": "我仍然不知道。"},
]
final_turn_policy.first = _SAFE_GUIDE_REVIEW_FALLBACKS[0]
final_turn_policy.regen_reply = _SAFE_GUIDE_REVIEW_FALLBACKS[0]
final_turn_policy.regen_calls = 0
final_turn_policy.reviews = [dict(_review_pass)]
final_turn_reply = final_turn_policy._tutor_turn()
check("_tutor_turn 的最終落地順序確實是先合併審查、再通用去重",
      final_turn_reply != _SAFE_GUIDE_REVIEW_FALLBACKS[0]
      and "final_repeat" in final_turn_policy.state["turns"][-1].guards)

ready_priority = _GuidePolicyStub(
    tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
ready_priority.state.update(
    phase="guide", turn_action="respond_attempt", proof_progress_revision=3,
    _regens=0)
_ready_even_without_question = dict(_COMBINED_READY)
_ready_even_without_question.update(
    level_policy_pass=False,
    feedback="學生已完成證明，因此不需要下一個引導問題")
ready_priority.reviews = [_ready_even_without_question]
ready_priority.regen_calls = 0
ready_priority_log = TurnLog(level=0, stuck_count=0)
ready_priority_reply = ready_priority._enforce_guide_reply_policy(
    "完全正確。", 0, ready_priority_log)
check("合併審查 ready 時優先切 review，不因候選沒有下一問而落入安全保底",
      ready_priority_reply == WRITEUP_FALLBACK
      and ready_priority.state.get("phase") == "review"
      and ready_priority.regen_calls == 0
      and ready_priority.state["guide_reply_review"]["thinking_calls"] == 1)

# unavailable 不是數學上的 false：第一輪不快取，下一輪即使只有「清楚了」仍重試。
_readiness_results = [None, {
    "ready_for_writeup": True, "missing_core_step": "",
    "confidence": 0.95, "reason": "累積骨架完整",
}]


def _fake_pending_retry(system, user, parser, **kwargs):
    return _readiness_results.pop(0)


_old_retry_parsed = _readiness_backstop._retry_parsed
try:
    _readiness_backstop._retry_parsed = _fake_pending_retry
    pending = TutorDriver(tok=None, model=_StubModel(), problem=probs["A6"],
                          backstop=True)
    pending.messages = [{"role": "user", "content": "我已經把必要步驟逐一接起來。"}]
    pending.state.update(
        phase="guide", proof_progress_revision=3,
        student_state_decision={"has_actionable_math": True,
                                "advances_solution": True})
    _pending_first = pending._judge_writeup_readiness("請檢查累積證明骨架。")
    _pending_uncached = (pending.state.get("readiness_pending") is True
                         and "writeup_readiness_check_key" not in pending.state)
    pending.messages.append({"role": "user", "content": "清楚了。"})
    pending.state["student_state_decision"] = {
        "has_actionable_math": False, "advances_solution": False,
    }
    _pending_should_retry = pending._should_check_writeup_readiness()
    _pending_second = pending._judge_writeup_readiness("再檢查同一份累積骨架。")
finally:
    _readiness_backstop._retry_parsed = _old_retry_parsed
check("readiness unavailable 不快取，下一輪無新數學內容也會重試",
      not _pending_first and _pending_uncached and _pending_should_retry
      and _pending_second and pending.state.get("readiness_pending") is False
      and bool(pending.state.get("writeup_readiness_check_key")))

# 前一次是有效的 readiness=false 也一樣：只要學生送來新訊息就重查，
# 不受 router 將完整訂正降級為 uncertain／advances_solution=None 影響。
stale_ready = TutorDriver(tok=None, model=_StubModel(), problem=probs["A6"],
                          backstop=True)
stale_ready.messages = [{"role": "user", "content": "目前還缺最後一個證明連結。"}]
stale_ready.state.update(
    phase="guide", proof_progress_revision=3,
    student_state_decision={"has_actionable_math": True,
                            "advances_solution": True})
stale_ready.state["writeup_readiness_check_key"] = stale_ready._writeup_readiness_key()
_same_message_cached = not stale_ready._should_check_writeup_readiness()
stale_ready.messages.append({
    "role": "user", "content": "我已補完最後連結並自行推出題目的結論。",
})
stale_ready.state["student_state_decision"] = {
    "has_actionable_math": False, "advances_solution": None,
    "learning_state": "uncertain",
}
check("基本進度後每則新學生訊息都重查 readiness，不依賴 advances_solution",
      _same_message_cached and stale_ready._should_check_writeup_readiness())

# Thinking 暫時不可用時，只在深度對話、已有完整外形且 Tutor 給整體完成訊號時保底。
fallback = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"], backstop=True)
fallback.messages = list(x4.messages)
fallback.state["proof_progress_revision"] = 3
fallback.state["student_state_decision"] = {
    "phase": "guide", "has_actionable_math": True, "advances_solution": True,
    "requested_writer": "none",
}
check("Thinking 不可用時不使用文字保底切 phase",
      fallback.state["phase"] == "guide")

# 反向：說話模型提早要求交稿時，readiness 未通過就不得送出該要求或改 phase。
pr = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"])
pr.first = "很好，現在請把完整證明寫出來，我來審閱。"
pr.regen = "目前還少一個連結：哪個條件能推出下一個不等式？"
pr.messages = [{"role": "user", "content": "我只完成了第一步。"}]
pr._judge_writeup_readiness = lambda _reply="": False
pr._tutor_turn()
check("readiness 未通過時攔截過早交稿請求",
      pr.state.get("phase") == "guide"
      and not pr.state.get("writeup_asked")
      and "完整證明寫出來" not in pr.messages[-1]["content"])
check("過早交稿請求的守衛可在 phase 報告外被診斷",
      "premature_writeup" in pr.state["turns"][-1].guards)

# 負面 1：對話才第一輪、學生訊息很短 → 維持既有通用追問，不可誤把 mid-proof 推去交稿
sh = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"])
sh.first = "完全正確。這句話本身就在說鴿籠原理。"
sh.regen = "還是沒有問句的重生成稿。"
sh.messages = [{"role": "user", "content": "題目…我的想法是這樣"}]
sh._tutor_turn()
check("對話才第一輪（mid-proof）→ 仍用通用追問，不誤請交稿",
      sh.messages[-1]["content"].endswith("那你覺得，下一步該從哪裡下手？")
      and "writeup_nudge" not in sh.state["turns"][-1].guards)

# 負面 2：深度對話但助教沒有下總評（只是普通肯定）→ 仍用通用追問
nd = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"])
nd.first = "嗯，這個方向可以，係數的部分再想想。"
nd.regen = nd.first
nd.messages = list(x4.messages[:7])
nd._tutor_turn()
check("深度對話但非總評式肯定 → 仍用通用追問",
      "writeup_nudge" not in nd.state["turns"][-1].guards)

print("[17] 助教本輪親口宣告完成 → 本輪就不補保底句（時序缺口）")
# 守門 X4/zh 末輪實例：助教說「是的，證明到此完成。…」——命中 _TUTOR_DONE_RE，
# 但該偵測放在 step() 開頭（掃上一則助教訊息），而保底句是本輪結尾補的，
# 於是「宣告完成」與「被追問下一步」出現在同一則回覆裡。arm 必須在補句之前發生。
tw = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"])
tw.first = "是的，證明到此完成。你清楚知道那個條件是什麼時候才真正起作用，這比背公式重要得多。"
tw.regen = tw.first                       # 重生成仍無問句
tw.messages = [{"role": "user", "content": "所以整個論證就是這樣串起來的，我懂了。"}]
tw._tutor_turn()
check("Tutor 本輪宣告整份完成不得 arm closed",
      not tw.state.get("done_closed") and tw.state["phase"] == "guide")

# 負面：本輪只肯定某一步 → 不 arm、保底句照補（維持推進對話的既有行為）
tstep = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"])
tstep.first = "對，這一步的證明完成了。"
tstep.regen = "換句話說也一樣成立。"
tstep.messages = [{"role": "user", "content": "我想這一段應該可以了。"}]
tstep._tutor_turn()
check("只宣告某一步完成 → 不 arm、仍補追問句",
      not tstep.state.get("done_closed")
      and "fallback" in tstep.state["turns"][-1].guards)

class _SeqStub(TutorDriver):
    """first 為初稿，regens 依序供應每一次重生成（用完重複最後一則）。

    _GuardStub 每次重生成都回同一稿，測不出「重生成結果要再過一次防護」；
    這個 stub 讓每道守衛拿到不同的重生成稿，才能驗證守衛鏈的串接。"""
    first: str
    regens: list

    def _generate(self, level):
        return self.first

    def _regen(self, level, note):
        i = getattr(self, "_ri", 0)
        self._ri = i + 1
        return self.regens[min(i, len(self.regens) - 1)]


print("[18] 交稿請求偵測必須限定「整份證明」範圍（mid-proof 誤判會反噬收尾流程）")
# 助教在證明途中說「把這一步寫下來」「你能自己寫出證明的第一步嗎」是常態引導，
# 誤記成 writeup_asked 有兩個下游傷害：(a) 之後的長訊息被當成完整草稿送審（後盾
# 會拿半成品逐步找碴）；(b) writeup_asked 是單向閂，真正該請他交稿時再也進不去。


def _tutor_says(reply: str, student: str, problem=None):
    """助教說了 reply、學生接著說 student → 回傳該輪結束後的 driver。"""
    d = _ReviewStub(tok=None, model=_StubModel(), problem=problem or probs["A6"])
    d.generated_levels = []
    d.start()
    d.messages.append({"role": "assistant", "content": reply})
    d.step(student)
    return d


_MID_SHORT = "嗯，好，我再想想。"
for _r in ("很好。你能自己試著寫出這個證明的第一步嗎？",
           "那就把這一步的證明寫下來，我們再看下一步。",
           "關鍵是均值定理。你能用它自己寫出證明的關鍵等式嗎？"):
    check(f"mid-proof 局部要求不得誤設 writeup_asked：「{_r[:14]}…」",
          not _tutor_says(_r, _MID_SHORT).state.get("writeup_asked"))

for _r in ("思路已經完整了。現在請把完整證明一步步寫出來，我會幫你審閱。",
           "很好，關鍵都有了。把完整證明寫出來吧，不會太難。",
           "你已經掌握主線。請自己寫出完整證明，不能只寫結論。"):
    check(f"外加的 Tutor 文字不能反向控制 writeup_asked：「{_r[:14]}…」",
          not _tutor_says(_r, _MID_SHORT).state.get("writeup_asked"))

check("真正的拒絕洩漏仍不得設 writeup_asked（反向閘只看同一子句）",
      not _tutor_says("我不能直接把完整證明寫出來給你，你先試試第一步？",
                      _MID_SHORT).state.get("writeup_asked"))

_MID_LONG = ("我試著往下推：因為 a_n > 0 且 (1+a_n)^n = n，我想先把兩邊取對數，"
             "得到 n·ln(1+a_n) = ln n，然後因為 ln(1+x) 在 x 小的時候接近 x，"
             "所以大概是 n·a_n ≈ ln n，這樣 a_n 大概是 (ln n)/n。不過我還沒處理"
             "ln(1+x) ≤ x 的方向問題，這裡卡住了。")
check("→ 誤設的下游：推導途中的長訊息不得被路由進 review",
      _tutor_says("很好。你能自己試著寫出這個證明的第一步嗎？",
                  _MID_LONG).state.get("phase") != "review")

_d18 = _tutor_says("很好。你能自己試著寫出這個證明的第一步嗎？", "好。")
_d18.step("喔我懂了，整個思路我都清楚了！")
check("學生自述理解仍不得自行打開 writeup_request",
      _d18.state.get("phase") != "writeup_request")

print("[19] 收尾兩道守衛的重生成仍須經過內容防護")
# 回問保底與重複偵測的 _regen 結果原本直接落地，不再經洩漏／防奉送／禁算式／
# 稱讚校準——是全檔唯一讓未經檢查的生成落地的路徑，正好架空 S3 抗洩漏防護。
_LEAK_Q = (r"由二項式定理，$n=(1+a_n)^n\ge \binom{n}{2}a_n^2=\frac{n(n-1)}{2}a_n^2$，"
           r"你看出來了嗎？")
lk = _SeqStub(tok=None, model=_StubModel(), problem=probs["A6"])
lk.first = "這一步是對的。"                      # 無問句 → 觸發回問保底
lk.regens = [_LEAK_Q,                            # 有問號但洩漏參考解
             "那你打算怎麼替 a_n 找一個夠好的上界？"]
lk.messages = [{"role": "user", "content": "題目…"},
               {"role": "user", "content": "我算到這裡。"}]
lk._tutor_turn()
check("回問保底的重生成若洩漏參考解 → 不得直接落地",
      not leaks_reference(lk.messages[-1]["content"], probs["A6"]["reference_proof"],
                          exclude=probs["A6"].get("statement", "")))
check("→ 洩漏被攔下後仍要留下問句", "？" in lk.messages[-1]["content"])

_LONG_REPLY = ("這個方向是對的。你已經注意到 a_n 是正的，而且 (1+a_n)^n 剛好等於 n，"
               "接下來的關鍵是要找到一個夠好的下界，把 a_n 的大小控制住，"
               "這樣才能說明它會趨近於零，而不是停在某個正數上。")
rp = _SeqStub(tok=None, model=_StubModel(), problem=probs["A6"])
rp.first = _LONG_REPLY                           # 與上一則助教回覆逐字相同
rp.regens = ["先想想二項式展開。"]                # 重生成稿沒有問句
rp.messages = [{"role": "user", "content": "題目…"},
               {"role": "assistant", "content": _LONG_REPLY},
               {"role": "user", "content": "嗯，我在想。"}]
rp._tutor_turn()
check("repeat 的重生成不得蓋掉保底問句（最終回覆仍須帶問句）",
      "？" in rp.messages[-1]["content"] or "?" in rp.messages[-1]["content"])

print("[20] 特殊 phase 不得誤觸逐步教學")


def _walk_after(phase):
    d = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
    d.generated_levels = []
    d.messages = [{"role": "user", "content": "題目…"}]
    d.state["stuck_count"] = 3
    d.state["phase"] = phase or "guide"
    d._walkthrough_transition("仍然卡住")
    return bool(d.state.get("walk_active"))


for _ph in ("review", "closed"):
    check(f"{_ph} 輪不得進入 walkthrough", not _walk_after(_ph))
check("一般 guide 連續卡住三次會進入 walkthrough", _walk_after("guide"))

# 一串糾錯輪不得把學生誤推進逐步教學。
ep = _StubDriver(tok=None, model=_StubModel(),
                 problem=dict(probs["A6"],
                              teach_steps=[{"explain": "步驟一", "core_idea": "核心性質",
                                            "check": "關鍵是什麼？",
                                            "expected_answer": "核心性質"}]))
ep.generated_levels = []
ep.start(opener="我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？")
for _m in ("我覺得可以用二項式，但我不確定。", "這樣對嗎？我還是不太懂。",
           "我認為要取平方，可是不知道怎麼做。", "我覺得是這樣，但想不出下一步。"):
    ep.step(_m)
check("opener 與後續模糊困惑輪都不臆測成連續卡住",
      not ep.state.get("walk_active") and ep.state.get("stuck_count") == 0)
ep.step("我先使用二項式定理，取其中的二次項作為下界。")
ep.step("還是不知道。")
ep.step("真的想不到。")
check("出現明確相關進展後重新計算；之後只卡兩次不提前進逐步教學",
      not ep.state.get("walk_active") and ep.state.get("stuck_count") == 2)

print("[21] 同學模式的權威背書守衛")
# 無可靠參考解時，任何「整份證明」等級的總評式背書都是不該有的權威口吻
# （實測 v11 端對端：同儕首輪誠實聲明有效，之後卻大量「完全正確／你已完全掌握」）。
_PEER_P = {"id": "P2", "statement": "未驗證難題", "grounding": "unverified"}
# first 一律自帶問句：否則無問句會先觸發回問保底重生成，測不出背書守衛本身
pe = _SeqStub(tok=None, model=_StubModel(), problem=dict(_PEER_P))
pe.first = "你的推導完全正確，完整無誤，你已完全掌握這題了，要不要換下一題？"
pe.regens = ["我猜這樣可能可以，但我不太確定第二步，你覺得呢？"]
pe.messages = [{"role": "user", "content": "題目…"},
               {"role": "assistant", "content": "我猜可以先試試看，你說呢？"},
               {"role": "user", "content": "我覺得這樣就對了。"}]
pe._tutor_turn()
check("同學模式的總評式背書 → 重生成", pe.messages[-1]["content"] == pe.regens[0])
check("log.guards 記錄 peer_endorse", "peer_endorse" in pe.state["turns"][-1].guards)

pf = _SeqStub(tok=None, model=_StubModel(), problem=dict(_PEER_P))
pf.first = "你的論證邏輯無縫，超過大多數同學，下一步想做什麼？"
pf.regens = ["我不太確定這一步，你要不要再檢查一次？"]
pf.messages = [{"role": "user", "content": "題目…"},
               {"role": "assistant", "content": "我猜可以先試試看，你說呢？"},
               {"role": "user", "content": "我寫好了。"}]
pf._tutor_turn()
check("同學模式的誇飾腔 → 重生成", "peer_endorse" in pf.state["turns"][-1].guards)

pk = _SeqStub(tok=None, model=_StubModel(), problem=dict(_PEER_P))
pk.first = "我猜這一步應該可以，不過我不太確定收斂的理由，你怎麼看？"
pk.regens = ["（不該被呼叫）"]
pk.messages = [{"role": "user", "content": "題目…"},
               {"role": "assistant", "content": "先試試看？"},
               {"role": "user", "content": "我覺得這樣就對了。"}]
pk._tutor_turn()
check("同儕正常的不確定語氣 → 不誤殺",
      "peer_endorse" not in pk.state["turns"][-1].guards)

print("[22] 重複偵測：保底句不得稀釋相似度、重生成後必須複驗（弱點 #17）")
# 2026-08-02 守門實證：「重度卡關型」學生連說毫無頭緒，助教第 8/10/12 輪逐字相同。
# 成因 (a)：上一輪被 driver 補了保底句，本輪逐字相同的回覆與它的 difflib 相似度掉到
# 0.768 < 0.85 → repeat 根本沒觸發。成因 (b)：真觸發時 _regen 回同一段文字，不複驗就採用。
_LOOP = "也許你該先查查這個序列的圖形長什麼樣子，再試著猜它的逐點極限。"

rl = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
rl.generated_levels = []
rl.state["lang"] = "zh"
# 上一輪助教回覆＝同一句 ＋ driver 補的保底句（真實 log 就長這樣）
rl.messages = [{"role": "user", "content": "題目…"},
               {"role": "assistant", "content": _LOOP + _FALLBACK_QS[0]},
               {"role": "user", "content": "不知道，我毫無頭緒。"}]
check("上一輪帶保底句時，逐字相同的回覆仍要判為重複",
      rl._repeats_previous(_LOOP))
rl_en = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
rl_en.generated_levels = []
rl_en.state["lang"] = "en"
_LOOP_EN = "Maybe look at the graph of this sequence first, then guess the pointwise limit."
rl_en.messages = [{"role": "user", "content": "problem…"},
                  {"role": "assistant", "content": _LOOP_EN + _FALLBACK_QS_EN[1]},
                  {"role": "user", "content": "No idea."}]
check("英文同上（保底句不得稀釋相似度）", rl_en._repeats_previous(_LOOP_EN))

nd2 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
nd2.generated_levels = []
nd2.state["lang"] = "zh"
nd2.messages = [{"role": "user", "content": "題目…"},
                {"role": "assistant", "content": _LOOP + _FALLBACK_QS[0]},
                {"role": "user", "content": "嗯。"}]
check("內容真的不同 → 不得誤判為重複",
      not nd2._repeats_previous("那你先算算 $n=1,2,3$ 時的值，看得出什麼趨勢嗎？"))


class _AlwaysRepeatStub(TutorDriver):
    """初稿與重生成都回同一句 → 模擬「重生成沒解決重複」。"""
    LOOP = _LOOP

    def _generate(self, level):
        return self.LOOP

    def _regen(self, level, note):
        return self.LOOP


rr = _AlwaysRepeatStub(tok=None, model=_StubModel(),
                       problem=dict(probs["A6"], teach_steps=[
                           {"explain": "步驟一", "check": "這步的定理是？",
                            "expected_answer": "夾擠定理"},
                           {"explain": "步驟二", "check": "那這步得到什麼？",
                            "expected_answer": "有界"},
                           {"explain": "步驟三", "check": "結論是什麼？",
                            "expected_answer": "收斂"}]))
rr.state["lang"] = "zh"
rr.state.update(phase="walkthrough", walk_active=True, walk_idx=0, walk_lang="zh")
rr.messages = [{"role": "user", "content": "題目…"},
               {"role": "assistant", "content": _LOOP},
               {"role": "user", "content": "還是不懂。"}]
r_walk = rr._tutor_turn()
check("教學輪不受一般回覆的重複偵測影響（內容由確定性模板產出）",
      "步驟一" in r_walk and rr.state.get("walk_idx") == 0)

rr2 = _AlwaysRepeatStub(tok=None, model=_StubModel(), problem=probs["A6"])
rr2.state["lang"] = "zh"
rr2.messages = [{"role": "user", "content": "題目…"},
                {"role": "assistant", "content": _LOOP},
                {"role": "user", "content": "還是不懂。"}]
rr2._tutor_turn()
check("一般輪重生成後仍重複 → 記錄 repeat_unresolved（讓失敗可被量測）",
      "repeat_unresolved" in rr2.state["turns"][-1].guards)

print("[23] 「帶進新數學內容」否決卡住判定（弱點 #17 的量測驅動解法）")
# 251 則真實訊息標註量測：is_stuck 的 P=0.484 / R=0.714 / F1=0.577，**precision 更差**。
# 誤判集中在「短訊息＋語氣遲疑＋其實推對了」，例如
#   「呃…就是 $e^x-1-x>0$？感覺就是移項而已，但我不確定這樣有什麼用。」
# 判他卡住＝白白消耗一級提示、還可能提早推進 walkthrough（與弱點 #17 同源的傷害）。
# 掃描候選特徵（scratchpad/probe_feature.py）：把「有帶進新數學內容」當**否決條件**
# 得 P=0.737 / R=0.667 / F1=0.700；反過來當「無新內容＝卡住」只有 F1=0.192（更差）。
# 閾值在 n=2–3、ratio=0.2–0.3、minlen=4–6 皆同分＝非過擬合。
nc = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
nc.generated_levels = []
nc.messages = [{"role": "user", "content": "題目：證明 $\\lim n/2^n = 0$。"},
               {"role": "assistant", "content": "試著用二項式定理把 $2^n$ 展開找下界。"}]
check("推出新的式子 → 有新內容",
      nc._has_new_math("那我取 $\\binom{n}{2}$ 當下界，得到 $2^n \\ge n(n-1)/2$。"))
check("引進新的輔助函數 → 有新內容",
      nc._has_new_math("我想設 $g(x)=x/2^x$ 然後對它微分看看。"))
check("完全沒有數學內容 → 無新內容（否決不生效，卡住判定照舊）",
      not nc._has_new_math("嗯……我再想想。"))
check("只複述助教剛給的片段 → 無新內容",
      not nc._has_new_math("嗯，你是說 $2^n$ 那個嗎？"))

# 真實誤判案例：語氣遲疑但確實推出了新形式 → 否決，不得判為卡住
fp1 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
fp1.generated_levels = []
fp1.start()
fp1.step("呃…就是 $e^x - 1 - x > 0$？感覺就是移項而已，但我不確定這樣有什麼用。")
check("真實誤判案例（遲疑但推對了）→ 不計為卡住", fp1.state["stuck_count"] == 0)

# 罐頭升級路徑必須不受影響（守門硬性指標 escalation_* 走這條）
esc = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
esc.generated_levels = []
esc.start()
esc.step("我不知道，想不出來。")
check("純困惑、無數學內容 → 仍計為卡住（否決不誤傷）", esc.state["stuck_count"] == 1)
esc.step("還是想不到，再提示一下。")
check("連卡兩次 → 仍升到等級 2（罐頭升級路徑不受影響）",
      esc.state["turns"][-1].level == 2 and esc.state["stuck_count"] == 2)

esc_en = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
esc_en.generated_levels = []
esc_en.start(opener="I have no idea how to start. Could you give me a first hint?")
check("明說卡住的 opener 仍不計 stuck，首輪固定為 Level 0",
      esc_en.state["stuck_count"] == 0 and esc_en.state["turns"][-1].level == 0)
esc_en.step("I don't know, I can't figure it out.")
check("opener 後第一次答不出 Tutor 問題 → Level 1",
      esc_en.state["stuck_count"] == 1 and esc_en.state["turns"][-1].level == 1)
esc_en.step("I still do not know how to continue.")
check("opener 後第二次答不出 Tutor 問題 → Level 2",
      esc_en.state["stuck_count"] == 2 and esc_en.state["turns"][-1].level == 2)
esc_auto = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
esc_auto.generated_levels = []
esc_auto.start()                                  # 系統自動填的預設開場白
check("自動預設 opener 不計為卡住（否則每場都從等級 1 起跳）",
      esc_auto.state["stuck_count"] == 0)

print("[24] 持續卡關時依 0→1→2→3 進入逐步教學")
# 預先供給 teach_steps：修復生效後 walkthrough 真的會觸發，而 A6 題目沒自帶步驟，
# _ensure_teach_steps() 會去打 Ollama——純邏輯測試不得有外部相依。
_MONO_PROB = dict(probs["A6"], teach_steps=[
    {"explain": "步驟一", "core_idea": "核心定理", "check": "關鍵定理？",
     "expected_answer": "核心定理"},
    {"explain": "步驟二", "core_idea": "收束性質", "check": "最後性質？",
     "expected_answer": "收束性質"}])
mono = _StubDriver(tok=None, model=_StubModel(), problem=_MONO_PROB)
mono.generated_levels = []
mono.start()
_STUCKS = ["我不知道。", "還是不會。", "完全沒頭緒。", "真的不知道。", "還是毫無頭緒。"]
_walk_at = None
for _i, _m in enumerate(_STUCKS):
    mono.step(_m)
    if _walk_at is None and mono.state.get("walk_active"):
        _walk_at = _i + 1
_lv = mono.generated_levels
check(f"連續卡住時等級不得下降（實得 {_lv}）",
      _lv[:3] == [0, 1, 2])
check(f"第三次連續卡住進入逐步教學（第 {_walk_at} 次卡住時）", _walk_at == 3)

# 既有行為不得破壞：學生恢復後 stuck_count 要歸零、等級回到 0
rec2 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
rec2.generated_levels = []
rec2.start()
rec2.step("我不知道。")
rec2.step("還是不會。")
check("連卡兩次 → 等級 2 且尚未進入 walkthrough",
      rec2.generated_levels[-1] == 2 and not rec2.state.get("walk_active"))
rec2.step("喔我懂了，用二項式展開取第二項當下界。")
check("學生恢復 → stuck_count 歸零、等級回到 0",
      rec2.state["stuck_count"] == 0 and rec2.generated_levels[-1] == 0)

print("[25] 重生成成本控制（教學輪延遲：學生每輪等待）")
# 計數 stub 曾實測：walkthrough 探針整段 22 次生成、7200 tokens（repeat 每輪都觸發）。
# 教學輪改成確定性模板後，這一段的生成次數固定為 0——內容本來就是預寫的教學步驟，
# 讓模型改寫只換來重複迴圈與每輪多等數十秒（弱點 #17 的殘留成本）。


class _CountingStub(TutorDriver):
    """計生成次數；回傳固定句以逼出 repeat（最壞情況）。"""
    n = 0

    def _raw_generate(self, msgs, max_new):
        self.n += 1
        return "先觀察這個序列的行為。"


_TS = dict(probs["A6"], teach_steps=[
    {"explain": f"步驟{i + 1}", "check": f"第 {i + 1} 步的重點是什麼？",
     "expected_answer": f"重點{i + 1}"} for i in range(6)])
cw = _CountingStub(tok=None, model=_StubModel(), problem=_TS)
cw.n = 0
cw.state["lang"] = "zh"
cw.state.update(phase="walkthrough", walk_active=True, walk_idx=0, walk_lang="zh")
cw.messages = [{"role": "user", "content": "題目…"},
               {"role": "assistant", "content": "先觀察這個序列的行為。"},
               {"role": "user", "content": "還是不懂。"}]
r_cw = cw._tutor_turn()
check(f"教學輪完全不呼叫生成模型（實得生成 {cw.n} 次）", cw.n == 0)
check("→ 仍輸出該步的講解與確認問題", "步驟1" in r_cw and "第 1 步的重點是什麼？" in r_cw)

# 一般輪（非教學輪）保留「勸他別重複」的重生成——那裡換措辭是有意義的
cg = _CountingStub(tok=None, model=_StubModel(), problem=probs["A6"])
cg.n = 0
cg.state["lang"] = "zh"
cg.messages = [{"role": "user", "content": "題目…"},
               {"role": "assistant", "content": "先觀察這個序列的行為。"},
               {"role": "user", "content": "然後呢？"}]
cg._tutor_turn()
check("一般輪仍會嘗試重生成（不誤傷既有行為）",
      "repeat" in cg.state["turns"][-1].guards and cg.n >= 2)

# 每輪重生成次數硬上限（安全閥：任何守衛組合都不得無上限消耗）
from tutor_driver import _MAX_REGEN_PER_TURN  # noqa: E402
cap = _CountingStub(tok=None, model=_StubModel(), problem=probs["A6"])
cap.n = 0
cap.state["lang"] = "zh"
cap.messages = [{"role": "user", "content": "題目…"},
                {"role": "assistant", "content": "先觀察這個序列的行為。"},
                {"role": "user", "content": "然後呢？"}]
cap._tutor_turn()
check(f"單輪生成次數不得超過 1+上限（{1 + _MAX_REGEN_PER_TURN}，實得 {cap.n}）",
      cap.n <= 1 + _MAX_REGEN_PER_TURN)


print("[26] 統一的 stuck_count 0→1→2→3 路徑")


class _Stuck3Capture(_StubDriver):
    captured: list

    def _generate(self, level):
        self.captured.append((level, self.state.get("phase"), self._system(level)))
        return super()._generate(level)


_STUCK3_PROB = {
    "id": "S3", "statement": "證明一般命題。", "reference_proof": "先用核心定理，再收束。",
    "teach_steps": [
        {"explain": "先使用核心定理。", "core_idea": "核心定理",
         "check": "先使用什麼？", "expected_answer": "核心定理"},
        {"explain": "再收束結論。", "core_idea": "收束性質",
         "check": "最後使用什麼？", "expected_answer": "收束性質"},
    ],
}
_stuck3 = _Stuck3Capture(tok=None, model=_StubModel(), problem=dict(_STUCK3_PROB))
_stuck3.generated_levels = []
_stuck3.captured = []
_stuck3.messages = [{"role": "user", "content": "題目…開始"}]
_stuck3.step("我不知道。")
_stuck3.step("還是不會。")
_third_reply = _stuck3.step("仍然沒有頭緒。")
check("第一次卡住是 Level 1", _stuck3.captured[0][0] == 1)
check("第二次卡住是 prompt-only Level 2，system 不注入 core_idea",
      _stuck3.captured[1][0] == 2
      and "只根據 <REFERENCE_PROOF> 與目前對話" in _stuck3.captured[1][2]
      and "current_core_idea" not in _stuck3.state)
check("第三次連續卡住直接進 walkthrough",
      _stuck3.state.get("walk_active") and _stuck3.state.get("phase") == "walkthrough"
      and "第 1/2 步" in _third_reply)
check("狀態只以 stuck_count 控制一般引導深度",
      _stuck3.state["stuck_count"] == 0)

print("[27] 自動備課只產參考證明與教學步驟")
import auto_reference as _ar  # noqa: E402
_orig_chat = _ar._chat
try:
    def _fake_reference_pipeline(system, user, temperature, timeout=600, **kwargs):
        if system is _ar.PROVER_SYSTEM:
            return "由核心定理可得結論。$\\blacksquare$"
        if system is _ar.VERIFIER_SYSTEM:
            return '{"verdict":"pass","issues":[]}'
        if system is _ar.SEGMENTER_SYSTEM:
            return ('[{"explain":"步驟一","core_idea":"定理甲","check":"使用什麼？",'
                    '"expected_answer":"定理甲"},'
                    '{"explain":"步驟二","core_idea":"性質乙","check":"得到什麼？",'
                    '"expected_answer":"性質乙"},'
                    '{"explain":"步驟三","core_idea":"收束結論","check":"結論是什麼？",'
                    '"expected_answer":"命題成立"}]')
        if system is _ar.TEACH_STEPS_VERIFIER_SYSTEM:
            return '{"verdict":"pass","issues":[]}'
        return None
    _ar._chat = _fake_reference_pipeline
    _built = _ar.build_reference("證明一般命題。", k=1, verbose=False)
    check("build_reference 只回傳參考證明與教學步驟",
          _built["status"] == "verified" and len(_built["teach_steps"]) == 3
          and "reference_proof" in _built)
finally:
    _ar._chat = _orig_chat

print("[28] 逐步教學的答案評分、語言鎖定與審閱收尾（Codex 交接整合）")
from auto_reference import ensure_checkable_steps, validate_teach_steps  # noqa: E402

# ── 教學步驟驗收（確定性五道閘）────────────────────────────────────────────
_GOOD_STEPS = [{"explain": "由中值定理", "core_idea": "中值定理",
                "check": "用哪個定理？", "expected_answer": "中值定理"},
               {"explain": "差的符號", "core_idea": "判斷差的符號",
                "check": "差是正是負？", "expected_answer": "非負"},
               {"explain": "收束結論", "core_idea": "單調性定義",
                "check": "結論是什麼？", "expected_answer": "f 單調不減"}]
check("驗收：3 步、欄位齊全 → 通過", validate_teach_steps(_GOOD_STEPS))
check("驗收：只有 2 步 → 退（相容解析，但不合教學規格）",
      not validate_teach_steps(_GOOD_STEPS[:2]))
check("驗收：缺 expected_answer → 退",
      not validate_teach_steps([dict(s, expected_answer="") for s in _GOOD_STEPS]))
check("驗收：一個 check 問兩件事 → 退（無法用單一答案鍵評分）",
      not validate_teach_steps([dict(_GOOD_STEPS[0], check="用哪個定理？前提是什麼？")]
                               + _GOOD_STEPS[1:]))
check("驗收：問題與答案都雷同 → 退",
      not validate_teach_steps([_GOOD_STEPS[0], dict(_GOOD_STEPS[0]), _GOOD_STEPS[2]]))
_legacy = ensure_checkable_steps([{"explain": "由中值定理得 f(b)-f(a)=f'(c)(b-a)。",
                                   "check": "用了哪個定理？"}])
check("舊式步驟補齊：step_id／expected_answer 都補上，既有 check 不被改寫",
      _legacy[0]["step_id"] and _legacy[0]["expected_answer"]
      and _legacy[0]["check"] == "用了哪個定理？")

# ── 語言：LaTeX 不得把中文回答判成英文；教學期間語言鎖定 ────────────────────
_ZH_LATEX = r"存在 \(c\in(x_1,x_2)\)，使得 \(f'(x_2)-f'(x_1)=f''(c)(x_2-x_1)\)。"
check("中文＋\\(...\\) 公式 → 仍判為中文", detect_lang(_ZH_LATEX) == "zh")
check("中文＋\\[...\\] 顯示公式 → 仍判為中文",
      detect_lang(r"我得到 \[a_n \le M\] 這個結果，所以有界。") == "zh")
check("中文＋裸算式 → 仍判為中文",
      detect_lang("那就是 f(x_2)-f(x_1)=f'(c)(x_2-x_1) 這個式子。") == "zh")
check("真正的英文訊息不受影響", detect_lang("I think the mean value theorem applies here.") == "en")

_BI_PROB = {
    "id": "B1", "statement": "測試題", "reference_proof": "步驟甲。\n\n步驟乙。",
    "teach_steps": [{"explain": "中文步驟一", "check": "關鍵等式是什麼？",
                     "expected_answer": r"f'(x_2)-f'(x_1)=f''(c)(x_2-x_1)"},
                    {"explain": "中文步驟二", "check": "結論是什麼？",
                     "expected_answer": "單調不減"}],
    # 英文步驟刻意換一套順序：語言若在教學途中跳動，walk_idx 就會指到別題的答案鍵
    "teach_steps_en": [{"explain": "EN step one", "check": "Is the difference positive?",
                        "expected_answer": "Positive"},
                       {"explain": "EN step two", "check": "What is the conclusion?",
                        "expected_answer": "nondecreasing"}],
}
bl = _SemanticWalkStub(tok=None, model=_StubModel(), problem=dict(_BI_PROB))
bl.generated_levels = []
bl.walk_verdicts = ["correct"]
bl.judged_steps = []
bl.messages = [{"role": "user", "content": "題目…開始"}]
bl.state.update(lang="zh")
bl.step("我不知道，想不出來。")
bl.step("還是不會。")
bl.step("仍然沒有頭緒。")
check("進入 walkthrough 時鎖定語言 walk_lang", bl.state.get("walk_lang") == "zh")
bl.step(_ZH_LATEX)
check("中文＋長 LaTeX 的正確答案：語言不跳動、依中文步驟評分而前進",
      bl.state.get("walk_lang") == "zh" and bl.lang == "zh"
      and bl.state["walk_idx"] == 1)

# 上一輪呈現的步驟才是評分對象：步驟表中途被換掉也不能拿新表的答案鍵評舊問題
ps = _SemanticWalkStub(tok=None, model=_StubModel(), problem=dict(_BI_PROB))
ps.generated_levels = []
ps.walk_verdicts = ["correct"]
ps.judged_steps = []
ps.messages = [{"role": "user", "content": "題目…開始"}]
ps.state.update(walk_active=True, walk_idx=0, phase="walkthrough",
                walk_lang="zh")
ps._tutor_turn()                                   # 呈現中文第 1 步
_replaced_steps = [{"explain": "被換掉的步驟", "check": "？",
                    "expected_answer": "完全不同的答案"}] * 2
ps.problem["teach_steps"] = _replaced_steps
ps.problem["teach_steps_zh"] = _replaced_steps
ps.step(r"$f'(x_2)-f'(x_1)=f''(c)(x_2-x_1)$")
check("依上一輪實際呈現的 step 評分（步驟表被換掉仍判對）", ps.state["walk_idx"] == 1)
check("後盾收到的是上一輪呈現的確認問題，不是被換掉的新步驟",
      ps.judged_steps[0][2] == "關鍵等式是什麼？")

# ── 「要證明：…」不得被當成交完整草稿 ──────────────────────────────────────
tp = _SemanticWalkStub(tok=None, model=_StubModel(), problem=dict(_BI_PROB))
tp.generated_levels = []
tp.walk_verdicts = ["correct"]
tp.judged_steps = []
tp.messages = [{"role": "user", "content": "題目…開始"}]
tp.state.update(walk_active=True, walk_idx=0, phase="walkthrough",
                walk_lang="zh")
tp._tutor_turn()
tp.step("要證明：對任意 a<b，有 f'(a)≤f'(b)。")
check("教學中「要證明：…」→ 維持 walkthrough，由當前步驟評分",
      tp.state["phase"] == "walkthrough" and tp.state.get("walk_active"))
tp.step("證明：任取兩點並由題設得到第一個關係式，因此可推出第二個關係式；"
        "再比較兩邊並檢查所有量詞，最後得到題目要求的結論。請幫我審閱。")
check("教學中「證明：…請幫我審閱」仍由當前步驟評分",
      tp.state["phase"] == "review"
      and tp.state["review_status"] == "awaiting_submission"
      and not tp.state.get("walk_active"))
check("只有步驟完成後才解除語言鎖定", tp.state.get("walk_lang") is None)

d_tp = _StubDriver(tok=None, model=_StubModel(), problem=dict(_BI_PROB))
d_tp.generated_levels = []
d_tp.messages = [{"role": "user", "content": "題目…開始"}]
d_tp.step("要證明：對任意 a<b，有 f'(a)≤f'(b)，這樣理解對嗎？")
check("一般輪的「要證明：…」也不再被 _DRAFT_RE 當成交稿",
      d_tp.state["phase"] != "review")

# ── 審閱無缺漏 → 確定性收尾；術語守衛 ─────────────────────────────────────
rp = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A2"])
rp.generated_levels = []
rp.review_reply = "（不該被使用的生成稿）"
rp.messages = [{"role": "user", "content": "證明：……（完整草稿）"}]
rp.state["phase"] = "review"
rp.state["backstop_gaps"] = []
r_rp = rp._tutor_turn()
check("後盾回報無缺漏 → 直接用確定性收尾模板（不呼叫說話模型）", r_rp == REVIEW_PASS)
check("收尾模板不帶任何問題", "？" not in r_rp and "?" not in r_rp)
check("收尾即 arm done_closed（後續反思不再開新題）", rp.state.get("done_closed"))

rg = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A2"])
rg.generated_levels = []
rg.review_reply = "你寫的是有缺漏的，δ 的取法還要再想想，對嗎？"
rg.messages = [{"role": "user", "content": "證明：……（完整草稿）"}]
rg.state["phase"] = "review"
rg.state["backstop_gaps"] = ["δ 的取法沒有同時控制兩個因子"]
rg._tutor_turn()
check("後盾找到缺漏 → 仍走說話模型引導修正（不誤觸收尾）",
      rg.messages[-1]["content"] == rg.review_reply and not rg.state.get("done_closed"))


class _MonoStub(_StubDriver):
    """審閱輪憑空挑起 increasing／nondecreasing 之爭（重生成也照樣糾結）。"""
    QUIBBLE = "你寫「單調不減」，但題目說的是遞增，這兩者一樣嗎？"

    def _generate(self, level):
        return self.QUIBBLE

    def _regen(self, level, note):
        return self.QUIBBLE


_MONO_PROB = {"id": "MONO", "statement": "設 f 二階可微且 f''(x)≥0，證明 f' 遞增。",
              "reference_proof": "由中值定理即得。"}
mq = _MonoStub(tok=None, model=_StubModel(), problem=dict(_MONO_PROB))
mq.generated_levels = []
mq.messages = [{"role": "user", "content": "證明：由中值定理，f'(x_2)≥f'(x_1)，故 f' 單調不減。"}]
mq.state["phase"] = "review"
r_mq = mq._tutor_turn()
check("題目沒寫嚴格遞增、學生已寫單調不減 → 攔截假術語缺漏",
      "terminology" in mq.state["turns"][-1].guards and r_mq == REVIEW_PASS
      and mq.state.get("done_closed"))

ms = _MonoStub(tok=None, model=_StubModel(),
               problem=dict(_MONO_PROB, statement="證明 f' 嚴格遞增。"))
ms.generated_levels = []
ms.messages = [{"role": "user", "content": "證明：…故 f' 單調不減。"}]
ms.state["phase"] = "review"
r_ms = ms._tutor_turn()
check("題目寫了嚴格遞增 → 不攔截（那是真的術語缺漏）",
      "terminology" not in ms.state["turns"][-1].guards and r_ms == _MonoStub.QUIBBLE)

print("[29] 逐步教學單次作答與語意後盾")
_ONE_TRY_PROB = {
    "id": "OT", "statement": "測試題", "reference_proof": "步驟甲。\n\n步驟乙。",
    "teach_steps": [{"explain": "教步驟甲", "check": "甲的關係式是什麼？",
                     "expected_answer": "a=b"},
                    {"explain": "教步驟乙", "check": "乙的結論是什麼？",
                     "expected_answer": "有界"}],
    "teach_steps_lang": "zh",
}
ot = _SemanticWalkStub(tok=None, model=_StubModel(), problem=dict(_ONE_TRY_PROB))
ot.generated_levels = []
ot.walk_verdicts = ["partial"]
ot.judged_steps = []
ot.state.update(lang="zh", walk_lang="zh", walk_active=True, walk_idx=0,
                phase="walkthrough")
ot.messages = [{"role": "user", "content": "題目…"}]
first = ot._tutor_turn()
second = ot.step("我只知道左邊可能和右邊有關。")
check("確認問題首次呈現使用確定性的一步一問模板",
      "第 1/2 步" in first and "甲的關係式是什麼？" in first)
check("partial 也只作答一次：揭答、前進、沒有重講狀態",
      ot.state["walk_idx"] == 1 and "a=b" in second
      and "第 2/2 步" in second and "walk_retry" not in ot.state)
check("狀態保存後盾 verdict，便於記錄與除錯",
      ot.state["walkthrough_review_status"] == "partial")

print()
print("[30] 備課與 driver 的通用一致性守衛")

# ── I-3：備課端與 driver 端的語言判定必須一致 ─────────────────────────────
# auto_reference._detect_lang 沒跟上 _strip_language_neutral_math 的強化：
# 以算式為主的中文被判成 en → teach_steps_lang 寫錯、中文講解配英文確認問句。
import auto_reference as _ar  # noqa: E402

for _txt in ("故 \\(\\left|\\dfrac{3n-1}{n+2}-3\\right|=\\dfrac{7}{n+2}<\\varepsilon\\) 成立。",
             "所以 f(x_2)-f(x_1)=f'(c)(x_2-x_1)>=0"):
    check(f"I-3 備課端語言判定與 driver 一致（{_txt[:12]}…）",
          _ar._detect_lang(_txt) == detect_lang(_txt) == "zh")
check("I-3 真正的英文仍判 en（修復不可把所有東西都判成中文）",
      _ar._detect_lang("Since the sequence converges to $L$, choose $N$ with $|a_n-L|<1$.")
      == detect_lang("Since the sequence converges to $L$, choose $N$ with $|a_n-L|<1$.")
      == "en")
_ZH_PROOF = "取 $N$ 使 $n>N$ 時 $|a_n-L|<1$。\n\n故 $|a_n|<|L|+1$，數列有界。"
check("I-3 句級保底的確認問句跟著參考解語言走（中文證明不得配英文問句）",
      all("這一步" in s["check"] for s in _ar.fallback_steps(_ZH_PROOF)))

print()
print("[31] 備課步驟依 session 選語言，不在 walkthrough 前重新切分")
_CACHE_EN = [
    {"step_id": f"s{i}", "explain": f"English step {i}.",
     "core_idea": f"idea {i}", "check": f"What follows in step {i}?",
     "expected_answer": f"result {i}"}
    for i in range(1, 4)
]
_CACHE_ZH = [
    {"step_id": f"s{i}", "explain": f"中文第 {i} 步。",
     "core_idea": f"想法 {i}", "check": f"第 {i} 步得到什麼？",
     "expected_answer": f"結論 {i}"}
    for i in range(1, 4)
]
_orig_segment = _ar.segment_proof
_orig_translate = _ar.translate_teach_steps
_routing_calls = {"segment": 0, "translate": 0}

def _count_segment(statement, proof, lang=None, **kwargs):
    _routing_calls["segment"] += 1
    return [dict(s) for s in _CACHE_ZH]

def _count_translate(statement, proof, steps, target_lang, **kwargs):
    _routing_calls["translate"] += 1
    return [dict(s) for s in (_CACHE_ZH if target_lang == "zh" else _CACHE_EN)]

_ar.segment_proof = _count_segment
_ar.translate_teach_steps = _count_translate
try:
    _cached_problem = {
        "statement": "Prove P.", "reference_proof": "Verified proof.",
        "grounding": "auto_verified", "teach_steps": _CACHE_EN,
        "teach_steps_lang": "en", "teach_steps_en": _CACHE_EN,
        "teach_steps_zh": _CACHE_ZH, "teach_steps_initial_status": "success",
    }
    _cached_driver = TutorDriver(tok=None, model=_StubModel(), problem=_cached_problem)
    _cached_driver.state.update(lang="zh", walk_lang="zh")
    _selected = _cached_driver._ensure_teach_steps()
    check("初次切分成功且已有中文快取 → 直接選中文版",
          _selected[0]["explain"].startswith("中文") and
          _routing_calls == {"segment": 0, "translate": 0})

    _translation_problem = {
        "statement": "Prove P.", "reference_proof": "Verified proof.",
        "grounding": "auto_verified", "teach_steps": _CACHE_EN,
        "teach_steps_lang": "en", "teach_steps_en": _CACHE_EN,
        "teach_steps_initial_status": "success",
    }
    _translation_driver = TutorDriver(
        tok=None, model=_StubModel(), problem=_translation_problem)
    _translation_driver.state.update(lang="zh", walk_lang="zh")
    _translated = _translation_driver._ensure_teach_steps()
    check("成功切分只有英文版 → 翻譯同一套步驟、不重新切分",
          _translated[0]["step_id"] == _CACHE_EN[0]["step_id"] and
          _routing_calls == {"segment": 0, "translate": 1})

    _failed_problem = {
        "statement": "Prove P.", "reference_proof": "Verified proof.",
        "grounding": "auto_verified", "teach_steps": [],
        "teach_steps_lang": "en", "teach_steps_source": "unavailable",
        "teach_steps_initial_status": "failed",
    }
    _failed_driver = TutorDriver(tok=None, model=_StubModel(), problem=_failed_problem)
    _failed_driver.state["lang"] = "zh"
    _failed_driver._system(2)
    check("初次切分失敗 → prompt-only Level 2 不讀步驟也不提前重切",
          _routing_calls["segment"] == 0
          and "current_core_idea" not in _failed_driver.state)
    _failed_driver.state["walk_lang"] = "zh"
    _retry_steps = _failed_driver._ensure_teach_steps()
    check("真正進入 walkthrough 前才依 session 語言重試切分",
          bool(_retry_steps) and _routing_calls["segment"] == 1)
finally:
    _ar.segment_proof = _orig_segment
    _ar.translate_teach_steps = _orig_translate

print()
print("[32] 每題完整 phase 切換報告")
_trace_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
_trace_driver.generated_levels = []
_trace_driver.start("我不會")
_trace_driver.step("我的嘗試是先使用反證法，假設結論不成立。")
_trace_report = _trace_driver.phase_transition_report()
check("phase 報告逐輪保存學生訊息", _trace_report["turn_count"] == 2
      and [x["turn"] for x in _trace_report["transitions"]] == [1, 2])
check("phase 報告同時保存切換前、router 與實際結束 phase",
      _trace_report["transitions"][1]["previous_phase"] == "guide"
      and _trace_report["transitions"][1]["router_phase"] == "guide"
      and _trace_report["transitions"][1]["final_phase"] == "guide"
      and _trace_report["transitions"][1]["turn_action"] == "respond_attempt")
check("phase 報告包含意圖、學習狀態、來源、信心與前後 state",
      all(key in _trace_report["transitions"][1] for key in (
          "intent", "learning_state", "answers_current_question",
          "has_actionable_math", "advances_solution", "transition_source",
          "phase_confidence", "stuck_confidence", "state_before", "state_after")))
_formatted_trace = json.loads(_trace_driver.format_phase_transition_report())
check("格式化 phase 報告是完整可解析 JSON",
      _formatted_trace["transitions"] == _trace_report["transitions"])
_trace_saved = _trace_driver.dump_state()
_trace_restored = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
_trace_restored.generated_levels = []
_trace_restored.load_state(_trace_saved)
check("dump/load 保留跨行程 phase 歷史",
      _trace_restored.phase_transition_report()["transitions"]
      == _trace_report["transitions"])

print()
print("[33] 附檔回歸：phase 精準切換與卡住精準判斷")
_stuck_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
_stuck_driver.generated_levels = []
_stuck_driver.start("我沒有頭緒")
_stuck_driver.step("我一頭霧水")
_stuck_driver._detect_phase("我對此毫無概念")
_stuck_driver._update_stuck_from_decision()
_stuck_driver._walkthrough_transition("我對此毫無概念")
_stuck_driver._detect_phase("我仍然不知道")
_stuck_driver._update_stuck_from_decision()
_stuck_driver._walkthrough_transition("我仍然不知道")
check("opener 後三次明確卡住仍維持連續計數並進 walkthrough",
      _stuck_driver.state.get("phase") == "walkthrough"
      and _stuck_driver.state.get("walk_active") is True)
for _stuck_text in ("我對這部分完全陌生", "我好困惑", "我很茫然"):
    _sd = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
    _sd.generated_levels = []
    _decision = _sd._route_student_state(_stuck_text)
    check(f"明確困惑『{_stuck_text}』判為 stuck",
          _decision.learning_state == "stuck")

_demand_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
_demand_driver.generated_levels = []
_demand_driver._detect_phase("可以給我完整且正確的證明嗎？")
check("禮貌索取完整證明仍進 refuse_leak",
      _demand_driver.state.get("phase") == "guide"
      and _demand_driver.state.get("turn_action") == "refuse_tutor_write")
for _supply_text in (
        "我不想一步一步推導了，麻煩直接給這題解答",
        "請問能跳過提示環節，給我整題的解答嗎？",
        "我想先看過整體的證明架構再來理解，請給我證明。",
        "請直接把整體的證明架構與步驟寫出來。",
        "請把整套證明的邏輯和式子列出來。",
        "先將解答寫出來，再解釋。",
        "先將證明寫出來，如果我有問題再問你。"):
    _dd = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
    _dd.generated_levels = []
    _dd._detect_phase(_supply_text)
    check("要求 Tutor 代寫／展示整份解答進 refuse_leak",
          _dd.state.get("phase") == "guide"
          and _dd.state.get("turn_action") == "refuse_tutor_write")
_local_hint_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
_local_hint_driver.generated_levels = []
_local_hint_driver._detect_phase("可以直接告訴我目前這一步該怎麼整理嗎？")
check("只要求目前一步的說明不是索取整份解答",
      _local_hint_driver.state.get("phase") != "refuse_leak")

_explain_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
_explain_driver.generated_levels = []
_explain_decision = _explain_driver._route_student_state(
    "請你用定理解釋一下為什麼 $F(x)$ 在 $(a,b)$ 上可導")
check("無問號的具體解釋請求仍是 active_clarification",
      _explain_decision.intent == "request_hint"
      and _explain_decision.learning_state == "active_clarification")

_goal_problem = dict(probs["A6"])
_goal_problem["statement"] = (
    r"Prove that there exists \(c\in(a,b)\) such that "
    r"\(\int_a^b f(x)\,dx=f(c)(b-a)\).")
_goal_driver = _StubDriver(tok=None, model=_StubModel(), problem=_goal_problem)
_goal_driver.generated_levels = []
_goal_driver._detect_phase(
    r"證明: 存在c屬於(a,b)使得\(\int_a^b f(x)\,dx=f(c)(b-a)\)")
_goal_decision = _goal_driver.state.get("student_state_decision") or {}
check("「證明：待證結論」不再誤切 refuse_leak",
      _goal_driver.state.get("phase") != "refuse_leak"
      and _goal_decision.get("intent") == "uncertain")

_social_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
_social_driver.generated_levels = []
_social_driver.state.update(phase="guide", turn_action="refuse_tutor_write")
_social_driver._detect_phase("我覺得其他同學都好厲害呢！")
_social_decision = _social_driver.state.get("student_state_decision") or {}
check("純社交比較不誤當數學嘗試進 rectify",
      _social_driver.state.get("phase") == "guide"
      and _social_decision.get("intent") != "show_attempt")

for _understood_text in ("這題的整個證明我都掌握了",
                         "我完全了解這題該怎麼證明了",
                         "這題證明我掌握了",
                         "你應該要要求我寫完整證明"):
    _ud = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
    _ud.generated_levels = []
    _ud.state.update(phase="guide", turn_action="respond_attempt")
    _ud._detect_phase(_understood_text)
    check(f"整體理解『{_understood_text}』不直接控制 writeup_request",
          _ud.state.get("phase") != "writeup_request"
          and not _ud.state.get("writeup_asked"))

_attempt_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
_attempt_driver.generated_levels = []
_attempt_text = ("我想要利用 $m \\le f(x) \\le M$ 對整個區間積分，"
                 "但我不確定具體的不等式這樣列對不對。")
_attempt_driver._detect_phase(_attempt_text)
_attempt_decision = _attempt_driver.state.get("student_state_decision") or {}
check("具體數學嘗試不因『不確定』被降成 uncertain",
      _attempt_driver.state.get("phase") == "guide"
      and _attempt_driver.state.get("turn_action") == "respond_attempt"
      and _attempt_decision.get("learning_state") == "partial_progress")

for _short_answer in (r"$L/2$", r"因為$\varepsilon$須為正"):
    _short_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
    _short_driver.generated_levels = []
    _short_driver.messages = [{
        "role": "assistant",
        "content": "要讓下界為正，這裡應取什麼值？",
    }]
    _short_driver.state["stuck_count"] = 2
    _short_driver._detect_phase(_short_answer)
    _short_driver._update_stuck_from_decision()
    _short_decision = _short_driver.state.get("student_state_decision") or {}
    check("簡短數學回答視為作答嘗試並重設連續卡住",
          _short_decision.get("learning_state") == "partial_progress"
          and _short_driver.state.get("stuck_count") == 0)

_unlabelled_proof = (
    "先設 $g(x)=u(x)-v(x)$，並任取區間中的兩點 $x_1<x_2$。"
    "因為題設保證所需的連續性，所以根據定義，$g$ 在閉區間上連續。"
    "接著由題設的可微性可知 $g$ 在開區間內可微，因此可以套用相應定理，"
    "得到存在 $c$ 使 $g(x_2)-g(x_1)=g'(c)(x_2-x_1)$。"
    r"再代入前面得到的符號條件，可得 $g(x_2)-g(x_1)\ge 0$。"
    "最後由任意性推出原命題對所有允許的兩點皆成立，因此這就證明了命題成立。")
_proof_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
_proof_driver.generated_levels = []
check("未標『完整證明』但具完整結構的全文仍被辨識",
      _proof_driver._is_full_proof_submission(_unlabelled_proof))
_proof_driver.state.update(walk_active=True, phase="walkthrough", lang="zh")
_proof_driver._detect_phase(_unlabelled_proof)
check("walkthrough 中主動提交完整證明仍受硬鎖保護",
      _proof_driver.state.get("phase") == "walkthrough")
_proved_wording = _unlabelled_proof.replace(
    "因此這就證明了命題成立。", "因此即證得原命題成立。")
check("不同的通用證明收束措辭仍被辨識為完整交稿",
      _proof_driver._is_full_proof_submission(_proved_wording))
_long_local_step = (
    "我只針對目前這一步說明：由定義可以先把左式改寫，然後比較其中兩項。"
    "這裡我反覆檢查了符號與區間，並補充每個符號的來源，"
    "但我尚未處理後續定理、其他步驟或整體結論。" * 2)
check("很長但沒有整體收束的單步回答不誤判為完整證明",
      not _proof_driver._has_strong_complete_proof_shape(_long_local_step))

_pass_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
_pass_driver.generated_levels = []
_pass_driver._run_two_pass_review = lambda _proof: []
_pass_driver._enter_awaiting_submission(event="READINESS_PASSED", source="unit_test")
_pass_driver._start_full_proof_review(_unlabelled_proof)
check("完整證明審閱通過的同一輪即切到 closed",
      _pass_driver.state.get("phase") == "closed"
      and _pass_driver.state.get("done_closed") is True)

_pass_driver.backstop = True
_reflection = (
    "這題帶給我的啟發是應先檢查定義與量詞，因為證明過程中的每個條件都有作用。"
    "因此之後遇到其他題目，我也會先整理假設，再思考有哪些定理可以使用。")
check("closed 後的長篇反思不會被全文外形檢查重新打開 review",
      _pass_driver._review_workflow_transition(_reflection) is None)
_pass_driver._detect_phase(_reflection)
check("closed 後反思維持 closed",
      _pass_driver.state.get("phase") == "closed")

# 無「以下是完整證明／得證」標籤但已從前提推到結論；walkthrough 仍是硬鎖，
# 不允許語意分類器直接跳過剩餘教學步驟。
import phase_router as _phase_router
_orig_model_classify = _phase_router._model_classify
try:
    _phase_router._model_classify = lambda text, context, classifier=None: {
        "intent": "full_proof_submission", "scope": "whole_proof",
        "learning_state": "not_applicable", "phase_confidence": 0.98,
        "stuck_confidence": 0.98, "evidence": text,
    }
    _walk_full = (
        "先由題設選定所需參數，因為假設保證它符合定義，所以存在對應的控制量。"
        "接著把定義給出的不等式完整展開，分別記錄左側與右側的限制，並說明控制量只依賴已選參數。"
        "再代入先前選定的參數，可知下界嚴格大於零；而任取的點只要符合前述鄰近條件，就落在同一個估計範圍。"
        "由於這個點是任意選取的，故對每一個充分靠近指定位置的點，題目要求的量皆大於零。")
    _walk_proof_driver = _SemanticWalkStub(
        tok=None, model=_StubModel(), problem=dict(_BI_PROB))
    _walk_proof_driver.generated_levels = []
    _walk_proof_driver.walk_verdicts = ["correct"]
    _walk_proof_driver.judged_steps = []
    _walk_proof_driver.backstop = True
    _walk_proof_driver.state.update(
        walk_active=True, walk_idx=1, walk_lang="zh", phase="walkthrough",
        lang="zh", stuck_count=0)
    _walk_proof_driver.messages = [{
        "role": "assistant", "content": "目前這一步可以推出什麼？",
    }]
    _walk_proof_driver.step(_walk_full)
    check("walkthrough 中未標籤的整份論證也只完成目前一步",
          _walk_proof_driver.state.get("phase") == "review"
          and _walk_proof_driver.state.get("review_status") == "awaiting_submission"
          and _walk_proof_driver.state.get("walk_active") is False
          and len(_walk_proof_driver.judged_steps) == 1)
finally:
    _phase_router._model_classify = _orig_model_classify

# guide 中即使學生貼上真正的完整證明，也只當成本輪數學作答。
# Tutor 必須先以 READINESS_PASSED 邀請交稿；學生之後再提交才能審閱。
_plain_full_proof = (
    r"證明：因為極限值 $L>0$，取 $\varepsilon=L/2>0$，則存在 $\delta>0$，"
    r"當 $0<|x-a|<\delta$ 時有 $|f(x)-L|<L/2$。"
    r"因此 $f(x)>L-L/2=L/2>0$，所以充分接近 $a$ 時 $f(x)>0$，證畢。")
_direct_guide_driver = _StubDriver(
    tok=None, model=_StubModel(), problem=dict(probs["A6"]))
_direct_guide_driver.generated_levels = []
_direct_guide_driver.backstop = True
_direct_guide_driver._run_two_pass_review = lambda _proof: []
_direct_guide_driver.step(_plain_full_proof)
check("guide 中的完整證明不觸發全文審閱",
      not any(e.get("event") == "FULL_PROOF_SUBMITTED" and e.get("accepted")
              for e in _direct_guide_driver.state.get("phase_events", []))
      and not _direct_guide_driver.state.get("current_proof_draft")
      and (_direct_guide_driver.state.get("phase") == "guide"
           or _direct_guide_driver.state.get("review_status") == "awaiting_submission"))

if _direct_guide_driver.state.get("phase") == "guide":
    _direct_guide_driver._enter_awaiting_submission(
        event="READINESS_PASSED", source="unit_test")
_direct_guide_driver.step(_plain_full_proof)
check("Tutor 邀請後再提交才觸發全文審閱",
      any(e.get("event") == "FULL_PROOF_SUBMITTED" and e.get("accepted")
          for e in _direct_guide_driver.state.get("phase_events", []))
      and _direct_guide_driver.state.get("current_proof_draft") == _plain_full_proof
      and _direct_guide_driver.state.get("phase") == "closed")

# closed 後不靠窮舉「有錯／漏審」句型：Thinking 只要高信心判定
# 學生在斷言最近證明有錯，就重查已保存的完整草稿。
_closed_recheck_calls = []
try:
    def _semantic_closed_error(text, context, classifier=None):
        return {
            "intent": "challenge_or_missed_review", "scope": "whole_proof",
            "learning_state": "not_applicable", "phase_confidence": 0.98,
            "stuck_confidence": 0.96, "evidence": text,
        }

    _phase_router._model_classify = _semantic_closed_error
    _closed_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
    _closed_driver.generated_levels = []
    _closed_driver.backstop = True
    _closed_driver.state.update(
        phase="closed", current_proof_draft=_unlabelled_proof, review_status=None)
    _closed_driver._run_two_pass_review = lambda proof: (
        _closed_recheck_calls.append(proof) or [])
    _closed_driver.step("我剛剛的證明其實有一處錯誤。")
    _closed_trace = _closed_driver.phase_transition_report()["transitions"][-1]
    _closed_summary = _closed_driver.turn_state_summary()
    check("closed 後斷言證明有錯會自動重查最近全文",
          len(_closed_recheck_calls) == 1
          and _closed_driver.state.get("phase") == "closed"
          and _closed_driver.state.get("review_status") is None
          and _closed_trace.get("transition_source") == "review_workflow")
    check("單輪簡短狀態顯示 reopen 到 pass 的完整 event chain",
          _closed_summary.get("events") == [
              "REVIEW_REOPEN_REQUESTED:closed>review",
              "REVIEW_PASSED:review>closed",
          ]
          and _closed_summary.get("event") == "REVIEW_PASSED")
finally:
    _phase_router._model_classify = _orig_model_classify

print("[34] 核心優化：學生所有權隔離、無問號橋接問題、正向承接審查與上下文對齊保底")
# 1. P0-1: 學生所有權隔離（Tutor 曾提示過，學生後續親自推導不被剝奪所有權）
p01_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
p01_driver.messages = [
    {"role": "user", "content": "題目：證明極限為 0。"},
    {"role": "assistant", "content": "試著考慮輔助函數 $g(x) = f(x) + 4x^2$。"},
]
check("P0-1: 學生推導 Tutor 曾提過的式子仍視為新進度",
      p01_driver._has_new_math("那我令 $g(x) = f(x) + 4x^2$ 並計算 $g''(x) = f''(x) + 8$。"))
ctx01 = p01_driver._student_state_context("那我令 $g(x) = f(x) + 4x^2$。")
check("P0-1: context 中 repeats_prior_math 不受 assistant 訊息污染",
      not ctx01.get("repeats_prior_math"))

# 2. P0-2: 無問號局部橋接釐清（「我不知道要怎麼從 A 推導到 B」）
check("P0-2: 無問號中文兩點橋接請求識別為具體問題",
      p01_driver._asks_specific_math_question("我不知道要怎麼從 $g''(c)=0$ 推導到 $f''(c)=-8$"))
check("P0-2: 無問號英文兩點橋接請求識別為具體問題",
      p01_driver._asks_specific_math_question("I cannot see how to derive f''(c)=-8 from g''(c)=0"))

# 3. P0-3 & P0-4: 審查器正向承接與錯誤類型分離
p03_driver = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
# 學生有步驟，但 Tutor 給予空泛問句（addresses_latest_student_step=False）
review_unaddressed = {
    "latest_student_step_status": "correct",
    "first_missing_step": "由 g''(c)=0 推出 f''(c)=-8",
    "candidate_math_error": "",
    "candidate_ownership_error": "",
    "addresses_latest_student_step": False,
    "mathematically_correct": True,
    "level_policy_pass": True,
    "introduces_new_proof_idea": False,
    "completes_any_unfinished_step": False,
    "leaks_final_conclusion": False,
    "ready_for_writeup": False,
    "missing_core_step": "由 g''(c)=0 推出 f''(c)=-8",
    "readiness_confidence": 0.5,
    "feedback": "候選未承接學生最新步驟",
}
check("P0-3: 學生有步驟時，候選未承接學生最新步驟（addresses_latest_student_step=False）退件",
      not p03_driver._guide_reply_review_passes(review_unaddressed, 1))

# Tutor 含有明確數學錯誤（candidate_math_error）
review_math_err = {
    "latest_student_step_status": "correct",
    "first_missing_step": "",
    "candidate_math_error": "目標常數應為 -8，但候選寫成 8",
    "candidate_ownership_error": "",
    "addresses_latest_student_step": True,
    "mathematically_correct": True,
    "level_policy_pass": True,
    "introduces_new_proof_idea": False,
    "completes_any_unfinished_step": False,
    "leaks_final_conclusion": False,
    "ready_for_writeup": False,
    "missing_core_step": "",
    "readiness_confidence": 0.5,
    "feedback": "候選包含常數符號錯誤",
}
check("P0-4: 候選包含具體數學錯誤（candidate_math_error）退件",
      not p03_driver._guide_reply_review_passes(review_math_err, 1))

# Tutor 含有所有權假定錯誤（candidate_ownership_error）
review_owner_err = {
    "latest_student_step_status": "correct",
    "first_missing_step": "",
    "candidate_math_error": "",
    "candidate_ownership_error": "學生尚未計算 Rolle 定理，Tutor 宣稱學生已得出 g''(c)=0",
    "addresses_latest_student_step": True,
    "mathematically_correct": True,
    "level_policy_pass": True,
    "introduces_new_proof_idea": False,
    "completes_any_unfinished_step": False,
    "leaks_final_conclusion": False,
    "ready_for_writeup": False,
    "missing_core_step": "",
    "readiness_confidence": 0.5,
    "feedback": "候選把 Tutor 先前步驟當作學生完成",
}
check("P0-4: 候選包含虛假所有權歸因（candidate_ownership_error）退件",
      not p03_driver._guide_reply_review_passes(review_owner_err, 1))

# 4. P1-1: Level Policy 與 Readiness 解耦（數學正確、所有權安全、正向承接時放行）
review_level_soft = {
    "latest_student_step_status": "correct",
    "first_missing_step": "利用 Rolle 定理",
    "candidate_math_error": "",
    "candidate_ownership_error": "",
    "addresses_latest_student_step": True,
    "mathematically_correct": True,
    "level_policy_pass": False,
    "introduces_new_proof_idea": False,
    "completes_any_unfinished_step": False,
    "leaks_final_conclusion": False,
    "ready_for_writeup": False,
    "missing_core_step": "利用 Rolle 定理",
    "readiness_confidence": 0.5,
    "feedback": "提示深度略深但數學正確且正向承接",
}
check("P1-1: 數學正確且無洩漏時，level_policy 不單獨作為退件理由",
      p03_driver._guide_reply_review_passes(review_level_soft, 2))

# 5. P1-3: 上下文對齊的保底回覆
p03_driver.state["guide_reply_review"] = {
    "initial": {
        "latest_student_step_status": "correct",
        "first_missing_step": "利用 Rolle 定理找 g''(c)=0",
    }
}
fb_zh = p03_driver._safe_guide_review_fallback()
check("P1-3: 中文保底回覆對齊第一缺口",
      "利用 Rolle 定理找 g''(c)=0" in fb_zh and "很好，這一步是成立的" in fb_zh)

p03_driver.state["lang"] = "en"
fb_en = p03_driver._safe_guide_review_fallback()
check("P1-3: 英文保底回覆對齊第一缺口",
      "利用 Rolle 定理找 g''(c)=0" in fb_en and "Good, that step is established" in fb_en)
p03_driver.state["lang"] = "zh"

print()
if FAIL:
    print(f"✗ {len(FAIL)} 項失敗：{FAIL}")
    sys.exit(1)
print("全部單元測試通過 ✓")
