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
    PHASE_INSTRUCTIONS, REVIEW_PASS, TutorDriver, detect_lang, enforce_single_question,
    gives_new_equation, grade_walkthrough_answer, is_overpraising, is_spoonfeeding,
    is_stuck, leaks_reference, load_problems_with_ladders,
    _FALLBACK_QS, _FALLBACK_QS_EN, _MAX_WALK_RETRY, _normalize,
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
check("『I know exactly what to do here.』→ 非 stuck（不可誤殺肯定句）",
      not is_stuck("I know exactly what to do here."))
check("『I'm sure the limit is zero.』→ 非 stuck（不可誤殺肯定句）",
      not is_stuck("I'm sure the limit is zero."))

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


probs = load_problems_with_ladders()
check("ladder 已載入（A6 有 2 條）", len(probs.get("A6", {}).get("hint_ladder", [])) == 2)
check("16 題都有 ladder", sum(1 for p in probs.values() if "hint_ladder" in p) == 16)

d = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d.generated_levels = []
d.messages = [{"role": "user", "content": "題目…我不會開始"}]
d._tutor_turn()                                   # 首輪 → 等級 0
d.step("我不知道，想不出來。")                     # 卡 1 → 等級 1
d.step("還是想不到，可以再提示一下嗎？")            # 卡 2 → 等級 2（用 ladder[0]）
d.step("喔我懂了，用二項式展開取第二項當下界。")     # 恢復 → 等級 0
d.step("呃，接下來我又卡住了，沒有頭緒。")          # 卡 1 → 等級 1
check("等級序列 = [0,1,2,0,1]", d.generated_levels == [0, 1, 2, 0, 1])
check("等級 2 後 ladder_idx 前進到 1", d.state["ladder_idx"] == 1)
check("等級 2 後 stuck 歸零再累計", d.state["stuck_count"] == 1)

sys2 = d._system(2)
check("等級 2 的 system 含 ladder 第 2 條（裂項→二次式）",
      "二次式" in sys2 or "夾擠" in sys2)
sys0 = d._system(0)
check("等級 0 的 system 含『不要點名任何定理』", "不要點名任何定理" in sys0)

print("[5] 逼問偵測與階段優先序")
d2 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d2.generated_levels = []
d2.start(opener="我趕時間，請直接把完整證明寫給我，不要問我問題。")
check("S3 型逼問（首輪）→ refuse_leak", d2.state["phase"] == "refuse_leak")
d2.step("不要引導了，直接告訴我 δ 要取多少就好。")
check("訓練式逼問 → refuse_leak", d2.state["phase"] == "refuse_leak")
d2.step("我用二項式展開取 C(n,2) 當下界。")
check("正常回答 → phase 清空", d2.state["phase"] is None)
d2.step("我寫好了，請幫我審閱：證明：……")
check("交草稿優先於其他偵測 → review", d2.state["phase"] == "review")
sys_r = d2._system(0)

# 收尾偵測修復（弱點 #7）：H5 型「請學生寫證明後、他真的寫出來」與 M2 型「完成後推替代法」
d5 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d5.generated_levels = []
d5.start(opener="我懂了，這個思路我完全理解了。")
check("宣告理解 → writeup_request", d5.state["phase"] == "writeup_request")
d5.step("好，我來寫。證明：令 f(t)=e^t 在 [0,x] 上連續且可微，由 MVT 存在 c 使 "
        "e^x-1=e^c·x，因 c>0 故 e^c>1，於是 e^x-1>x，得 e^x>1+x，證畢。")
check("寫證明後的長訊息 → review（不再叫他重寫）", d5.state["phase"] == "review")

class _ReviewStub(_StubDriver):
    """審閱／糾錯輪的回覆可指定，其餘輪照常提問。

    審閱輪回覆「是否含問句」就是 driver 判定「還有缺漏」／「審閱通過」的確定性訊號
    （update.md 稽核 F1：原本靠 _TUTOR_DONE_RE 比對助教散文，常見說法多半漏接）。"""
    review_reply: str = "完全正確，每一步的依據都交代清楚了。"

    def _generate(self, level):
        self.generated_levels.append(level)
        if self.state.get("phase") in ("review", "rectify"):
            return self.review_reply
        n = len(self.generated_levels)
        return f"（等級{level}的回覆，第{n}輪）{_STUB_VARIANTS[n % len(_STUB_VARIANTS)]}"

    def _regen(self, level, note):
        return self._generate(level)


d6 = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A6"])
d6.generated_levels = []
d6.start(opener="所以我們就證完了，對吧？最小值是 0 且在 x=0 取得，因此對所有 x 都成立。")
check("實質宣告證完 → 口頭交稿走 review", d6.state["phase"] == "review")
check("審閱通過（該輪回覆無問句）→ arm done_closed", d6.state.get("done_closed"))
d6.step("嗯，這樣整個就串起來了。不過我發現我剛才對 x≤0 那段講得有點含糊，其實應該更明確說明。")
check("完成後的反思閒聊 → closed（不推替代法）", d6.state["phase"] == "closed")
check("closed 指示禁新問題／替代法",
      "不要再拋出任何新問題" in d6._system(0) and "替代證法" in d6._system(0))
# #11（Fork B，2026-07-23）：完成後帶問句的反思——好奇/範圍/非斷言質疑都進 closed
# （只簡短回答那一個問題、不藉機延伸）；只有斷言式質疑才跳回一般流程重新檢查。
d6.step("這樣是不是對 x<0 也成立呢？")
check("完成後帶問句的範圍好奇 → closed（#11：只答不延伸）", d6.state["phase"] == "closed")
check("closed 新指示：只簡短回答那一個問題",
      "只簡短回答那一個問題" in d6._system(0))
d6.step("你確定這樣就對了嗎？")
check("完成後非斷言的『你確定…嗎』→ closed（簡答，非重驗；Fork B）",
      d6.state["phase"] == "closed")
d6.step("你錯了吧，這一步根本不成立。")
check("完成後斷言式質疑（_CHALLENGE_RE 命中）→ 不走 closed",
      d6.state["phase"] != "closed")

# 英文平行：完成後帶問句的好奇 → closed（雙語一致）
d7 = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A6"])
d7.generated_levels = []
d7.review_reply = "Completely correct — every step is justified."
d7.start(opener="So that completes the proof, right? The minimum value is 0, attained "
                "only at x = 0, so it holds for all x.")
check("EN 實質宣告證完 → review", d7.state["phase"] == "review")
check("EN 審閱通過（回覆無問句）→ arm done_closed", d7.state.get("done_closed"))
d7.step("So does this also hold for x < 0?")
check("EN 完成後帶問句好奇 → closed（#11）", d7.state["phase"] == "closed")
check("EN closed 新指示：只答那一個問題、不延伸",
      "answer only that one question" in d7._system(0).lower())
d2.state["phase"] = "refuse_leak"
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
check("助教親口確認整個證明完成 → arm done_closed（#12）", d8.state.get("done_closed"))
check("助教確認完成後、學生帶問句反思 → closed（#12＋#11）", d8.state["phase"] == "closed")

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
check("EN 助教確認完成 → arm done_closed（#12）", d10.state.get("done_closed"))
check("EN 助教確認完成後反思 → closed（#12＋#11）", d10.state["phase"] == "closed")

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
g1b.state["phase"] = "refuse_leak"
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
from review_backstop import _parse_gaps  # noqa: E402

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
b.state["phase"] = "rectify"
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
check("teach_steps 缺欄位 → None", parse_steps('[{"explain": "只有講解"}]') is None)
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
    "hint_ladder": ["提示一", "提示二"],
    "teach_steps": [{"explain": "教步驟甲", "check": "甲的關鍵定理是什麼？",
                     "expected_answer": "中值定理"},
                    {"explain": "教步驟乙", "check": "乙得到什麼結論？",
                     "expected_answer": "有界"}],
}
w = _StubDriver(tok=None, model=_StubModel(), problem=dict(_walk_prob))
w.generated_levels = []
w.messages = [{"role": "user", "content": "題目…開始"}]
w.state["ladder_idx"] = 2                      # 模擬提示梯已用盡
w.step("我不知道，想不出來。")                  # 卡 1
check("卡 1 尚未進入教學", not w.state.get("walk_active"))
r_w = w.step("還是不會。")                      # 卡 2 → 進入 walkthrough
check("提示梯用盡＋連卡兩次 → 進入 walkthrough",
      w.state.get("walk_active") and w.state["phase"] == "walkthrough"
      and w.state["walk_idx"] == 0)
check("教學輪確定性輸出「一個步驟＋一個確認問題」（不經生成模型）",
      "教步驟甲" in r_w and "甲的關鍵定理是什麼？" in r_w and "第 1/2 步" in r_w)
check("教學輪記下本輪實際呈現的步驟（下一輪據此評分）",
      w.state["walk_presented_idx"] == 0
      and w.state["walk_presented_step"]["expected_answer"] == "中值定理")
w.step("聽不懂，不明白。")                       # 卡住 → 同一步重講
check("卡住 → 同一步重講（walk_idx 不動、retry=1）",
      w.state["walk_idx"] == 0 and w.state["walk_retry"] == 1)
r_wrong = w.step("應該是夾擠定理吧。")           # 答錯 → 仍留在同一步
check("答錯 → 留在同一步（不因為有回答就前進）", w.state["walk_idx"] == 0)
check("答錯後的下一輪帶上修正提示、重講同一步",
      "還不是這一步要的答案" in r_wrong and "第 1/2 步" in r_wrong)
w.step("是中值定理。")                           # 答對 → 前進
check("答對才前進到步驟 2", w.state["walk_idx"] == 1 and w.state["walk_retry"] == 0)
w.step("這一步得到的是有界。")                    # 答對 → 步驟用盡 → 請寫證明
check("步驟教完 → 轉 writeup_request 且教學結束",
      not w.state.get("walk_active") and w.state["phase"] == "writeup_request")

# 安全閥：答案鍵是自動生成的，寫壞時不能讓學生永遠卡在同一步
wS = _StubDriver(tok=None, model=_StubModel(), problem=dict(_walk_prob))
wS.generated_levels = []
wS.messages = [{"role": "user", "content": "題目…開始"}]
wS.state.update(walk_active=True, walk_idx=0, walk_retry=0, phase="walkthrough",
                walk_lang="zh", ladder_idx=2)
wS._tutor_turn()
for _ in range(_MAX_WALK_RETRY):
    wS.step("我覺得是別的東西。")
check(f"同一步連錯 {_MAX_WALK_RETRY} 次仍留在原步（重試上限內）", wS.state["walk_idx"] == 0)
r_rev = wS.step("還是不知道。")
check("超過重試上限 → 揭示答案並強制前進（答案鍵寫壞不得困住學生）",
      wS.state["walk_idx"] == 1 and "中值定理" in r_rev)
for _ in range(_MAX_WALK_RETRY + 1):          # 最後一步也連續答不出來 → 教完轉交稿
    r_last = wS.step("還是不知道。")
check("最後一步的答案揭示不得被守衛吃掉（要出現在轉交稿那一輪）",
      wS.state["phase"] == "writeup_request" and "有界" in r_last)

w2 = _StubDriver(tok=None, model=_StubModel(), problem=dict(_walk_prob))
w2.generated_levels = []
w2.messages = [{"role": "user", "content": "題目…開始"}]
w2.state.update(walk_active=True, walk_idx=0, walk_retry=0, phase="walkthrough",
                ladder_idx=2)
w2.step("證明：如下……請幫我審閱。")
check("教學中交草稿 → 打斷進 review", w2.state["phase"] == "review"
      and not w2.state.get("walk_active"))

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
      p.state["phase"] == "peer_reflect" and "重新檢查" in p._system(0))
r3 = p.step("好，那我們換個方向？")
check("非質疑輪 → phase 清空", p.state["phase"] is None)
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
check("en 逼問 → refuse_leak", d3.state["phase"] == "refuse_leak")
d3.step("I think we keep only the quadratic term as a lower bound. Is this correct?")
check("en 嘗試 → rectify", d3.state["phase"] == "rectify")
d3.step("Here is my proof: by the binomial theorem ... please review it.")
check("en 交草稿 → review", d3.state["phase"] == "review")
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
d5b.state["phase"] = None
check("換句話重問（僅一詞之差）→ 判定重複",
      d5b._repeats_previous("Which hypothesis in the problem verifies one condition of that theorem?"))
check("真正的新問題 → 不判重複",
      not d5b._repeats_previous("What does the sign of g'(x) tell you about monotonicity?"))
d5b.state["phase"] = "walkthrough"
check("教學輪重講同一步（刻意相似）→ 不判重複",
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
check("repeat 重生成宣告完成 → arm done_closed", rd.state.get("done_closed") is True)
check("→ 該輪不得再補保底追問句",
      rd.messages[-1]["content"] == "是的，整個證明完成了。"
      and "fallback" not in rd.state["turns"][-1].guards)

print("[13] 宣告完成 → 口頭交稿路由審閱（弱點 #3）")
dc = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
dc.generated_levels = []
dc.start(opener="請引導我。")
dc.step("設 a_n = n^(1/n) − 1，由二項式定理 n ≥ C(n,2)a_n²，解出 a_n ≤ √(2/(n−1))，夾擠得 a_n→0，"
        "所以極限是 1，這樣就證完了。")
check("長論證＋宣告證完 → review", dc.state.get("phase") == "review")
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
check("英文長論證＋宣告 → review", dc4.state.get("phase") == "review")

print("[14] 收尾 arm 時機、追問抑制與稱讚校準（update.md 對話稽核）")


# 口頭宣告式交稿（不以「證明：」開頭 → 走 _CLAIM_DONE_RE 分支），且 δ 取法有缺漏
_CLAIM = ("我把式子拆成 |x-2||x+2|，先限制 |x-2|<1 得到 |x+2|<5，"
          "再取 δ = ε/5，這樣 |x^2-4| < 5·(ε/5) = ε，因此得證。")

rv = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A2"])
rv.generated_levels = []
rv.review_reply = "你取 δ 的時候，前面 |x-2|<1 的限制還保得住嗎？"
rv.start(opener=_CLAIM)
check("宣告式交稿 → review", rv.state.get("phase") == "review")
check("審閱結果未知時不得 arm done_closed（F3：arm 早於審閱＝糾錯會被吞）",
      not rv.state.get("done_closed"))
rv.step("你是說 δ 的取法有問題嗎？")
check("審閱指出缺漏後、學生帶問句追問 → 不進 closed，糾錯續行（F3 回歸）",
      rv.state.get("phase") != "closed")

rv2 = _ReviewStub(tok=None, model=_StubModel(), problem=probs["A2"])
rv2.generated_levels = []
rv2.review_reply = "完全正確，每一步都有依據，這份證明可以了。"
rv2.start(opener=_CLAIM)
check("審閱通過（該輪回覆無問句）→ arm done_closed（F1：不靠措辭正則）",
      rv2.state.get("done_closed"))
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
nq2.state["done_closed"] = True
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
    _should = _why == "確實宣告整份完成"
    check(f"助教說「{_txt[:12]}…」（{_why}）→ {'arm' if _should else '不 arm'} done_closed",
          bool(_d.state.get("done_closed")) is _should)

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
op2.state["phase"] = "rectify"
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
op4.state["phase"] = "rectify"            # review＋gaps==[] 改走確定性收尾（見 [28]）
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
check("助教自行要求交稿 → 記錄 writeup_asked", wa.state.get("writeup_asked") is True)
check("→ 學生交出的長草稿路由 review（而非落回一般引導輪）",
      wa.state.get("phase") == "review")
check("→ 審閱通過後 arm done_closed，收尾不再補追問句",
      wa.state.get("done_closed") is True
      and "fallback" not in wa.state["turns"][-1].guards)

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
x4 = _GuardStub(tok=None, model=_StubModel(), problem=probs["A6"])
x4.first = ("完全正確。核心是把「相異特徵值」這個條件用上，逼出係數只能是零。"
            "你自己的推導比任何提示都清楚。")
x4.regen = x4.first                      # 重生成仍無問句 → 走保底路徑
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
x4._tutor_turn()
_out = x4.messages[-1]["content"]
check("深度對話＋實質推導＋總評式肯定且無問句 → 補的是交稿請求",
      "寫出來" in _out and "下一步該從哪裡下手" not in _out)
check("→ 同時記下 writeup_asked（下一則草稿才進得了 review）",
      x4.state.get("writeup_asked") is True)
check("log.guards 記為 writeup_nudge", "writeup_nudge" in x4.state["turns"][-1].guards)

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
check("本輪宣告整份證明完成 → 立即 arm done_closed", tw.state.get("done_closed") is True)
check("→ 同一則回覆不得再被補上追問句",
      tw.messages[-1]["content"] == tw.first
      and "fallback" not in tw.state["turns"][-1].guards)

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
    check(f"真正的交稿請求要記下 writeup_asked：「{_r[:14]}…」",
          _tutor_says(_r, _MID_SHORT).state.get("writeup_asked") is True)

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
check("→ 誤設的下游：不得吃掉真正的 writeup_request 時機",
      _d18.state.get("phase") == "writeup_request")

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

print("[20] 特殊 phase 不得消耗提示梯")
# 階段指示優先於等級指示：phase 有值時 system 注入的是階段指示、根本沒有提示內容，
# 卻仍把 ladder_idx 記為已用 → 提示被「用掉」但學生從未看到。


def _ladder_after(phase):
    d = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
    d.generated_levels = []
    d.messages = [{"role": "user", "content": "題目…"}]
    d.state["stuck_count"] = 2                   # 等級 2
    d.state["phase"] = phase
    d._tutor_turn()
    return d.state["ladder_idx"]


for _ph in ("refuse_leak", "rectify", "review", "writeup_request", "closed"):
    check(f"{_ph} 輪不得推進 ladder_idx", _ladder_after(_ph) == 0)
check("一般引導輪（phase=None）等級 2 仍要推進 ladder_idx", _ladder_after(None) == 1)

# 危害重現：一串糾錯輪把提示梯吃光 → 學生一條提示都沒拿到就被推進逐步教學
ep = _StubDriver(tok=None, model=_StubModel(),
                 problem=dict(probs["A6"],
                              teach_steps=[{"explain": "步驟一", "check": "懂嗎？"}]))
ep.generated_levels = []
ep.start(opener="我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？")
for _m in ("我覺得可以用二項式，但我不確定。", "這樣對嗎？我還是不太懂。",
           "我認為要取平方，可是不知道怎麼做。", "我覺得是這樣，但想不出下一步。",
           "還是不知道。", "真的想不到。"):
    ep.step(_m)
check("糾錯輪不得把學生推進逐步教學（提示梯並未真正用過）",
      not ep.state.get("walk_active"))

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
check("教學輪不再受重複偵測影響（內容確定性、重講同一步是刻意行為）",
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
      esc.state["turns"][-1].level == 2 and esc.state["ladder_idx"] == 1)

esc_en = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
esc_en.generated_levels = []
esc_en.start(opener="I have no idea how to start. Could you give me a first hint?")
check("明說卡住的 opener 計為第一次卡住（自帶題目才不會白卡一輪）",
      esc_en.state["stuck_count"] == 1)
esc_en.step("I don't know, I can't figure it out.")
check("英文純困惑 → 仍計為卡住（opener 已卡 1，這是第 2 次）",
      esc_en.state["stuck_count"] == 2 and esc_en.state["turns"][-1].level == 2)
esc_auto = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
esc_auto.generated_levels = []
esc_auto.start()                                  # 系統自動填的預設開場白
check("自動預設 opener 不計為卡住（否則每場都從等級 1 起跳）",
      esc_auto.state["stuck_count"] == 0)

print("[24] 持續卡關時支援等級必須單調遞增（弱點 #17 的根因）")
# 2026-08-02 守門 M1 回放診斷：等級序列是 0→1→2→1→2→1→walkthrough。
# 給完等級 2 提示後 stuck_count 被歸零，於是下一輪掉回等級 1——而等級 1 的指示是
# 「拆成更小的子問題，仍然不要點名定理」＝比上一輪給得更少。學生越卡，助教給的
# 幫助反而在 2 和 1 之間震盪，walkthrough 因此拖到第 6 輪才觸發。
# 那個歸零是多餘的：學生真的恢復時 step() 本來就會把 stuck_count 設回 0。
# 預先供給 teach_steps：修復生效後 walkthrough 真的會觸發，而 A6 題目沒自帶步驟，
# _ensure_teach_steps() 會去打 Ollama——純邏輯測試不得有外部相依。
_MONO_PROB = dict(probs["A6"], teach_steps=[
    {"explain": "步驟一", "check": "這步懂嗎？"},
    {"explain": "步驟二", "check": "那這步呢？"}])
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
      all(b >= a for a, b in zip(_lv[1:3], _lv[2:4])) and 1 not in _lv[3:])
check("提示梯兩條都送出去（ladder_idx 到 2）", mono.state["ladder_idx"] == 2)
check(f"提示梯用盡後盡快進入逐步教學（第 {_walk_at} 次卡住時）",
      _walk_at is not None and _walk_at <= 4)

# 既有行為不得破壞：學生恢復後 stuck_count 要歸零、等級回到 0
rec2 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
rec2.generated_levels = []
rec2.start()
rec2.step("我不知道。")
rec2.step("還是不會。")
check("連卡兩次 → 等級 2 且 ladder_idx=1（罐頭升級路徑不變）",
      rec2.generated_levels[-1] == 2 and rec2.state["ladder_idx"] == 1)
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

print("[26] 空梯路徑：使用者自帶題目沒有 hint_ladder 時的升級軌跡")


class _CapturingStub(_StubDriver):
    """在「生成當下」擷取 system；教學輪不生成，改記 (level, 'walkthrough', 模板回覆)。

    ⚠️ 不可在 step() 回傳後才讀 _system()：ladder_idx 在該輪結尾才遞增
    （tutor_driver.py 的 level==2 分支），事後讀會看到遞增後的狀態，
    誤判「卡 2 注入的是提示二」。
    """
    captured: list

    def _generate(self, level):
        self.captured.append((level, self.state.get("phase"), self._system(level)))
        return super()._generate(level)

    def _walkthrough_reply(self):
        reply = super()._walkthrough_reply()
        self.captured.append((min(self.state["stuck_count"], 2), "walkthrough", reply))
        return reply


_LAD_PROB = {
    "id": "L1", "statement": "測試題：證明某序列收斂。",
    "reference_proof": "步驟甲。\n\n步驟乙。",
    "teach_steps": [{"explain": "教步驟甲", "check": "甲的定理是什麼？",
                     "expected_answer": "夾擠定理"},
                    {"explain": "教步驟乙", "check": "乙的結論是什麼？",
                     "expected_answer": "收斂"}],
}
_STUCK_MSGS = ["我不知道，想不出來。", "還是不會。", "完全沒有頭緒。",
               "還是想不到，可以再提示一下嗎？"]


def _run_stuck(ladder):
    """連卡四輪，回傳跑完的 driver（captured 逐輪記錄 (等級, phase, system)）。"""
    prob = dict(_LAD_PROB)
    if ladder is not None:
        prob["hint_ladder"] = ladder
    d = _CapturingStub(tok=None, model=_StubModel(), problem=prob)
    d.generated_levels = []
    d.captured = []
    d.messages = [{"role": "user", "content": "題目…開始"}]
    for m in _STUCK_MSGS:
        d.step(m)
    return d


_nl = _run_stuck(None)                      # 無梯＝使用者自帶題目的現況
check("無梯：卡 1 → 等級 1", _nl.captured[0][0] == 1)
check("無梯：卡 2 → 等級 2 且注入的是通用保底句（非題目專屬提示）",
      _nl.captured[1][0] == 2 and "關鍵定理或想法名稱" in _nl.captured[1][2])
check("無梯：ladder_idx 仍推進到 1（該輪確實把提示送出去了）",
      _nl.state["ladder_idx"] == 1)
check("無梯：卡 3 → 進入逐步教學（max(梯長,1) 讓空梯不死鎖）",
      _nl.captured[2][1] == "walkthrough" and _nl.state["walk_active"])

_yl = _run_stuck(["提示一：關鍵是均值定理。", "提示二：導數有界給出 Lipschitz。"])
check("有梯：卡 2 → 注入 ladder[0]",
      _yl.captured[1][0] == 2 and "提示一" in _yl.captured[1][2])
check("有梯：卡 3 → 注入 ladder[1]",
      _yl.captured[2][0] == 2 and "提示二" in _yl.captured[2][2])
check("有梯：卡 4 → 提示梯用盡才進入逐步教學",
      _yl.captured[3][1] == "walkthrough")
check("空梯的實質退化：比有梯早一輪掉進逐步教學",
      _nl.captured[2][1] == "walkthrough" and _yl.captured[2][1] != "walkthrough")

print("[27] LADDER：提示梯自動生成的解析與驗收")
from auto_reference import parse_ladder  # noqa: E402

check("parse_ladder：正常 2 條 → 通過",
      parse_ladder('["先想想均值定理能給你什麼。", "再看導數有界推出什麼性質。"]')
      == ["先想想均值定理能給你什麼。", "再看導數有界推出什麼性質。"])
check("parse_ladder：3 條 → None（梯長固定 2）",
      parse_ladder('["提示一夠長的內容。", "提示二夠長的內容。", "提示三夠長的內容。"]') is None)
check("parse_ladder：1 條 → None", parse_ladder('["只有一條提示的內容。"]') is None)
check("parse_ladder：非字串元素 → None", parse_ladder('[{"a": 1}, {"b": 2}]') is None)
check("parse_ladder：空白字串元素 → None", parse_ladder('["有內容的提示。", "   "]') is None)
check("parse_ladder：垃圾輸出 → None", parse_ladder("我覺得可以先想想均值定理。") is None)
check("parse_ladder：思考鏈包夾仍可取出",
      parse_ladder('思考中…最後給出：["提示甲的內容夠長。", "提示乙的內容也夠長。"] 完畢')
      == ["提示甲的內容夠長。", "提示乙的內容也夠長。"])
check("parse_ladder：LaTeX escape 降級解析（\\{ 是非法 JSON escape）",
      parse_ladder(r'["用 \{x_n\} 的單調性想想看吧。", "再用有界性收束到結論。"]')
      == [r"用 \{x_n\} 的單調性想想看吧。", "再用有界性收束到結論。"])
check("parse_ladder：None 輸入 → None", parse_ladder(None) is None)

from auto_reference import validate_ladder  # noqa: E402

# 驗收用的固定素材：參考解刻意寫成「無算式但有可洩漏的長句」，
# 才能把「洩漏」與「帶算式」兩道閘分開測（含 = 的句子會先被算式閘攔下）。
_VS = "設 $f$ 在 $[a,b]$ 上可微且 $|f'(x)| \\le M$，證明 $f$ 一致連續。"
_VP = ("由均值定理，存在介於兩點之間的 $c$ 使得函數差等於導數乘上距離。"
       "再由導數有界，可推出 Lipschitz 條件，於是取與位置無關的 δ 即完成證明。$\\blacksquare$")
_OK = ["這一步的關鍵是均值定理，它連起函數差與導數。",
       "導數有界會給出與位置無關的 δ 選取。"]

check("validate_ladder：合格的兩條 → 通過", validate_ladder(_OK, _VS, _VP))
check("validate_ladder：3 條 → 退",
      not validate_ladder(_OK + ["第三條提示的內容也夠長。"], _VS, _VP))
check("validate_ladder：非 list → 退", not validate_ladder("不是清單", _VS, _VP))
check("validate_ladder：過短（<12 字）→ 退",
      not validate_ladder(["太短了", _OK[1]], _VS, _VP))
check("validate_ladder：過長（>60 字）→ 退",
      not validate_ladder([_OK[0] + "而且我還要再補上非常非常非常非常非常非常多餘的冗長說明文字，硬是要拉得更長更長。",
                           _OK[1]], _VS, _VP))
check("validate_ladder：帶題目以外的新算式 → 退",
      not validate_ladder(["關鍵是均值定理，會得到 f(x)-f(y)=f'(c)(x-y)。", _OK[1]],
                          _VS, _VP))
check("validate_ladder：等號兩側有空白的 LaTeX 寫法（舊版 gives_new_equation 會漏接）→ 退",
      not validate_ladder(
          ["關鍵在於取 $\\delta = \\varepsilon / M$ 這個構造，想想為什麼可行。", _OK[1]],
          _VS, _VP))
check("validate_ladder：洩漏參考解長片段（15-gram）→ 退",
      not validate_ladder(["再由導數有界，可推出 Lipschitz 條件，於是取與位置無關的 δ。",
                           _OK[1]], _VS, _VP))
check("validate_ladder：兩條雷同 → 退",
      not validate_ladder([_OK[0], _OK[0] + "。"], _VS, _VP))

# 回歸鎖：手寫梯是人工驗過的黃金標準，被自己的驗收擋掉＝門檻訂錯。
_gold = [(pid, p) for pid, p in probs.items()
         if len(p.get("hint_ladder") or []) == 2 and p.get("reference_proof")]
_gold_fail = [pid for pid, p in _gold
              if not validate_ladder(p["hint_ladder"], p.get("statement", ""),
                                     p["reference_proof"])]
check(f"回歸鎖：{len(_gold)} 題手寫 2 條梯全部通過 validate_ladder（失敗：{_gold_fail}）",
      len(_gold) >= 14 and not _gold_fail)

# 逐條回歸鎖：上面的 _gold 用 len(...)==2 篩題，把 M4 的 3 條梯整題排除
# （load_problems_with_ladders() 有 hint_ladder + reference_proof 的共 16 題 / 33 條，
# 扣掉 M4 只鎖住 15 題 / 30 條）。這裡把「逐條閘」（長度／算式／洩漏）與「條數閘」
# （validate_ladder 硬性要求恰 2 條）拆開驗，讓 M4 的 3 條梯也進回歸鎖覆蓋。
from auto_reference import _LADDER_FORMULA_RE  # noqa: E402
_all_hints = [(pid, h, p) for pid, p in probs.items()
              if p.get("hint_ladder") and p.get("reference_proof")
              for h in p["hint_ladder"]]
_all_hint_fail = [pid for pid, h, p in _all_hints
                  if not (12 <= len(h.strip()) <= 60
                          and not _LADDER_FORMULA_RE.search(h)
                          and not leaks_reference(h, p["reference_proof"],
                                                  exclude=p.get("statement", "")))]
check(f"逐條回歸鎖：{len(_all_hints)} 條手寫提示（含 M4 的 3 條梯）"
      f"全數通過長度／算式／洩漏三道閘（失敗：{_all_hint_fail}）",
      len(_all_hints) >= 33 and not _all_hint_fail)

import auto_reference as _ar  # noqa: E402

_LADDER_JSON = ('["這一步的關鍵是均值定理，它連起函數差與導數。", '
                '"導數有界會給出與位置無關的 δ 選取。"]')
_orig_chat = _ar._chat
try:
    _ar._chat = lambda *a, **k: _LADDER_JSON
    check("build_ladder：模型輸出合格 → 回傳兩條", _ar.build_ladder(_VS, _VP) == _OK)

    _ar._chat = lambda *a, **k: '["太短", "也太短"]'
    check("build_ladder：驗收不過 → None（退回通用保底句）",
          _ar.build_ladder(_VS, _VP) is None)

    _ar._chat = lambda *a, **k: "我想想…均值定理應該可以。"
    check("build_ladder：輸出無法解析 → None", _ar.build_ladder(_VS, _VP) is None)

    _ar._chat = lambda *a, **k: None
    check("build_ladder：Ollama 離線 → None", _ar.build_ladder(_VS, _VP) is None)

    # 管線整合：LADDER 通過時 build_reference 的結果要帶 hint_ladder
    def _fake_chat(system, user, temperature, timeout=600):
        if system is _ar.PROVER_SYSTEM:
            return "由均值定理可得結論。$\\blacksquare$"
        if system is _ar.VERIFIER_SYSTEM:
            return '{"verdict": "pass", "issues": []}'
        if system is _ar.SEGMENTER_SYSTEM:
            return ('[{"explain": "先建立不等式", "check": "左邊是什麼？",'
                    ' "expected_answer": "|a_n-L|"}, '
                    '{"explain": "再取極限", "check": "極限是多少？",'
                    ' "expected_answer": "0"}, '
                    '{"explain": "收束結論", "check": "結論是什麼？",'
                    ' "expected_answer": "數列收斂"}]')
        if system is _ar.LADDER_SYSTEM:
            return _LADDER_JSON
        return None

    _ar._chat = _fake_chat
    _res = _ar.build_reference("測試題敘述", k=1, verbose=False)
    check("build_reference：verified 且 LADDER 通過 → 結果帶 hint_ladder",
          _res["status"] == "verified" and _res.get("hint_ladder") == _OK)
    check("build_reference：合格的 SEGMENTER 輸出直接採用（3 步、標記 segmenter）",
          len(_res["teach_steps"]) == 3 and _res["teach_steps_source"] == "segmenter"
          and _res["teach_steps_lang"] == "zh")

    def _fake_chat_bad_steps(system, user, temperature, timeout=600):
        if system is _ar.SEGMENTER_SYSTEM:      # 只有 2 步、沒有答案鍵 → 驗收不過
            return ('[{"explain": "先建立不等式", "check": "左邊是什麼？"}, '
                    '{"explain": "再取極限", "check": "極限是多少？"}]')
        return _fake_chat(system, user, temperature, timeout)

    _ar._chat = _fake_chat_bad_steps
    _res_fb = _ar.build_reference("測試題敘述", k=1, verbose=False)
    check("build_reference：SEGMENTER 驗收不過 → 改走句級保底且標記 fallback",
          _res_fb["teach_steps_source"] == "fallback"
          and all(s["expected_answer"] for s in _res_fb["teach_steps"]))

    def _fake_chat_bad_ladder(system, user, temperature, timeout=600):
        if system is _ar.LADDER_SYSTEM:
            return '["太短", "也太短"]'
        return _fake_chat(system, user, temperature, timeout)

    _ar._chat = _fake_chat_bad_ladder
    _res2 = _ar.build_reference("測試題敘述", k=1, verbose=False)
    check("build_reference：LADDER 驗收不過 → 結果不含 hint_ladder 鍵（非 None）",
          _res2["status"] == "verified" and "hint_ladder" not in _res2)
finally:
    _ar._chat = _orig_chat

print("[28] 逐步教學的答案評分、語言鎖定與審閱收尾（Codex 交接整合）")
from auto_reference import ensure_checkable_steps, validate_teach_steps  # noqa: E402

# ── 教學步驟驗收（確定性五道閘）────────────────────────────────────────────
_GOOD_STEPS = [{"explain": "由中值定理", "check": "用哪個定理？", "expected_answer": "中值定理"},
               {"explain": "差的符號", "check": "差是正是負？", "expected_answer": "非負"},
               {"explain": "收束結論", "check": "結論是什麼？", "expected_answer": "f 單調不減"}]
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

# ── 答案評分 grade_walkthrough_answer ─────────────────────────────────────
_YN = {"expected_answer": "是", "accepted_answers": [], "common_errors": []}
check("正確的 yes/no 長答可通過",
      grade_walkthrough_answer("是，因為 x_2>x_1，所以 x_2-x_1>0，是正數。", _YN) == "correct")
check("反向不等式的否定答仍判錯",
      grade_walkthrough_answer("不是，x_2-x_1<0。", _YN) == "incorrect")
check("『正』不能通過『非負』（前者比後者強）",
      grade_walkthrough_answer("正", {"expected_answer": "非負"}) == "incorrect")
check("『非負』本身可通過『非負』",
      grade_walkthrough_answer("應該是非負的", {"expected_answer": "非負"}) == "correct")
check("函數單調非減題答『遞減』→ 判錯",
      grade_walkthrough_answer("遞減", {"expected_answer": "單調不減"}) == "incorrect")
check("術語慣例：未寫 strictly 的『遞增』等同『單調不減』",
      grade_walkthrough_answer("f' 遞增", {"expected_answer": "單調不減"}) == "correct")
_EQ = {"expected_answer": r"f'(x_2)-f'(x_1)=f''(c)(x_2-x_1)"}
check("學生多寫等價式與理由仍通過（\\ge0／\\geq 0 等寫法統一）",
      grade_walkthrough_answer(
          r"存在 $c$，使得 $f'(x_2)-f'(x_1)=f''(c)(x_2-x_1)$，而 $f''(c)\geq 0$。", _EQ)
      == "correct")
check("答不出來 → stuck（不算答錯）",
      grade_walkthrough_answer("完全不知道", _EQ) == "stuck")
check("common_errors 命中 → incorrect（優先於其他判定）",
      grade_walkthrough_answer("是夾擠定理", {"expected_answer": "中值定理",
                                            "common_errors": ["夾擠定理"]}) == "incorrect")
check("步驟沒有答案鍵 → 退回舊行為（非卡住即算過），不讓學生死鎖",
      grade_walkthrough_answer("我想想", {"explain": "只有講解"}) == "correct")

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
bl = _StubDriver(tok=None, model=_StubModel(), problem=dict(_BI_PROB))
bl.generated_levels = []
bl.messages = [{"role": "user", "content": "題目…開始"}]
bl.state.update(ladder_idx=2, lang="zh")
bl.step("我不知道，想不出來。")
bl.step("還是不會。")
check("進入 walkthrough 時鎖定語言 walk_lang", bl.state.get("walk_lang") == "zh")
bl.step(_ZH_LATEX)
check("中文＋長 LaTeX 的正確答案：語言不跳動、依中文步驟評分而前進",
      bl.state.get("walk_lang") == "zh" and bl.lang == "zh"
      and bl.state["walk_idx"] == 1)

# 上一輪呈現的步驟才是評分對象：步驟表中途被換掉也不能拿新表的答案鍵評舊問題
ps = _StubDriver(tok=None, model=_StubModel(), problem=dict(_BI_PROB))
ps.generated_levels = []
ps.messages = [{"role": "user", "content": "題目…開始"}]
ps.state.update(walk_active=True, walk_idx=0, walk_retry=0, phase="walkthrough",
                walk_lang="zh", ladder_idx=2)
ps._tutor_turn()                                   # 呈現中文第 1 步
ps.problem["teach_steps"] = [{"explain": "被換掉的步驟", "check": "？",
                              "expected_answer": "完全不同的答案"}] * 2
ps.step(r"$f'(x_2)-f'(x_1)=f''(c)(x_2-x_1)$")
check("依上一輪實際呈現的 step 評分（步驟表被換掉仍判對）", ps.state["walk_idx"] == 1)

# ── 「要證明：…」不得被當成交完整草稿 ──────────────────────────────────────
tp = _StubDriver(tok=None, model=_StubModel(), problem=dict(_BI_PROB))
tp.generated_levels = []
tp.messages = [{"role": "user", "content": "題目…開始"}]
tp.state.update(walk_active=True, walk_idx=0, walk_retry=0, phase="walkthrough",
                walk_lang="zh", ladder_idx=2)
tp._tutor_turn()
tp.step("要證明：對任意 a<b，有 f'(a)≤f'(b)。")
check("教學中「要證明：…」→ 維持 walkthrough，由當前步驟評分",
      tp.state["phase"] == "walkthrough" and tp.state.get("walk_active"))
tp.step("證明：如下……請幫我審閱。")
check("教學中「證明：…請幫我審閱」→ 仍可中斷進 review",
      tp.state["phase"] == "review" and not tp.state.get("walk_active"))
check("離開教學時解除語言鎖定", tp.state.get("walk_lang") is None)

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

print("[29] 教學輪重講不得逐字重複（2026-08-07 守門 M1 中英兩場實測退化）")
# 原始症狀：學生連說看不懂，助教把同一段教學文字原封不動再貼兩次，
# 評審 guidance 給 1 分，學生本人在對話裡寫「Repeating it doesn't make it any clearer」。
_RT_PROB = {
    "id": "RT", "statement": "測試題", "reference_proof": "步驟甲。\n\n步驟乙。",
    "teach_steps": [{"explain": "教步驟甲", "check": "甲的定理是什麼？",
                     "expected_answer": "中值定理"},
                    {"explain": "教步驟乙", "check": "乙的結論是什麼？",
                     "expected_answer": "有界"}],
}


class _RetryStub(TutorDriver):
    """重講時模型給得出新說法。"""
    n = 0

    def _raw_generate(self, msgs, max_new):
        self.n += 1
        return f"換個說法：想像把甲拆成很小的一步（第 {self.n} 次講）。"


rt = _RetryStub(tok=None, model=_StubModel(), problem=dict(_RT_PROB))
rt.n = 0
rt.state.update(lang="zh", walk_lang="zh", walk_active=True, walk_idx=0,
                walk_retry=0, phase="walkthrough", ladder_idx=2)
rt.messages = [{"role": "user", "content": "題目…"}]
first = rt._tutor_turn()
check("首次呈現仍是確定性模板（0 次生成）", rt.n == 0 and "教步驟甲" in first)
rt.step("完全看不懂。")
second = rt.messages[-1]["content"]
check("重講輪叫模型換個說法（1 次生成）", rt.n == 1 and "換個說法" in second)
check("重講與上一則不逐字相同", _normalize(second) != _normalize(first))
check("重講仍附上同一個確認問題（答案鍵才比得到）", "甲的定理是什麼？" in second)
check("重講不推進步驟", rt.state["walk_idx"] == 0 and rt.state["walk_retry"] == 1)


class _SameStub(TutorDriver):
    """最壞情況：模型換不出新說法（或不在線）。"""
    n = 0

    def _raw_generate(self, msgs, max_new):
        self.n += 1
        return "教步驟甲"


sm = _SameStub(tok=None, model=_StubModel(), problem=dict(_RT_PROB))
sm.n = 0
sm.state.update(lang="zh", walk_lang="zh", walk_active=True, walk_idx=0,
                walk_retry=0, phase="walkthrough", ladder_idx=2)
sm.messages = [{"role": "user", "content": "題目…"}]
f1 = sm._tutor_turn()
sm.step("完全看不懂。")
f2 = sm.messages[-1]["content"]
check("模型換不出新說法 → 退回模板但補上該步答案（仍不逐字相同）",
      _normalize(f2) != _normalize(f1) and "中值定理" in f2)


class _RefuseTeachStub(TutorDriver):
    """重講時推託「你自己去查」——探針重跑實測抓到的模型失敗模式。"""

    def _raw_generate(self, msgs, max_new):
        return "這題的關鍵是「取二次項當下界」，你自己查一下二項式展開就知道了。"


rf = _RefuseTeachStub(tok=None, model=_StubModel(), problem=dict(_RT_PROB))
rf.state.update(lang="zh", walk_lang="zh", walk_active=True, walk_idx=0,
                walk_retry=0, phase="walkthrough", ladder_idx=2)
rf.messages = [{"role": "user", "content": "題目…"}]
rf._tutor_turn()
rf.step("完全看不懂。")
r_rf = rf.messages[-1]["content"]
check("重講推託「你自己去查」→ 不採用（提示梯早已用盡，這時推託等於放棄教學）",
      "自己查" not in r_rf and "中值定理" in r_rf)
check("一般引導輪不受這道守衛影響（只管教學重講輪）",
      "自己查" in _RefuseTeachStub(tok=None, model=_StubModel(),
                                  problem=dict(_RT_PROB))._generate(0))

print()
if FAIL:
    print(f"✗ {len(FAIL)} 項失敗：{FAIL}")
    sys.exit(1)
print("全部單元測試通過 ✓")
