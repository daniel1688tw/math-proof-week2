# -*- coding: utf-8 -*-
"""test_driver_unit.py — tutor_driver 的純邏輯單元測試（不載模型、不需 GPU、不打 Ollama）。"""
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
    PHASE_INSTRUCTIONS, TutorDriver, enforce_single_question, gives_new_equation,
    is_spoonfeeding, is_stuck, leaks_reference, load_problems_with_ladders,
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
check("實質嘗試（含定理）→ 非 stuck", not is_stuck("我想用均值定理，f(x)-f(y)=f'(c)(x-y)，然後取絕對值。"))
check("長回覆含『不確定』但有嘗試 → 非 stuck（長度>60）",
      not is_stuck("我不確定對不對，但我試著設 g(x)=f(x)-kx，然後算它的導數 g'(x)=f'(x)-k，接著看端點的符號，g'(a)<0 而 g'(b)>0。"))
check("正確回答 → 非 stuck", not is_stuck("部分和是遞增的，因為每一項都是正的。"))

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


class _StubDriver(TutorDriver):
    """繞過真實生成，只驗證狀態轉移與 system 組裝。"""
    generated_levels: list

    def _generate(self, level):
        self.generated_levels.append(level)
        return f"（等級{level}的回覆，第{len(self.generated_levels)}輪）這一步該怎麼想？"


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
d2.state["phase"] = "refuse_leak"
sys_leak = d2._system(0)
check("refuse_leak 指示含『拒絕』與『問一個』", "拒絕" in sys_leak and "問一個" in sys_leak)

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

print("[8] 英文偵測（雙語支援）")
from tutor_driver import detect_lang, is_spoonfeeding as _is_spoon

check("純英文 → en", detect_lang("I have no idea how to start this problem.") == "en")
check("繁中 → zh", detect_lang("我不知道怎麼開始。") == "zh")
check("英文夾 LaTeX → en", detect_lang(r"Prove that $\lim_{x\to 2}x^2=4$ using epsilon-delta.") == "en")
check("en stuck: I don't know", is_stuck("I don't know how to continue."))
check("en stuck: still stuck", is_stuck("I'm still stuck, can I get another hint?"))
check("en 實質嘗試不算 stuck",
      not is_stuck("I am not sure, but I tried setting g(x)=f(x)-kx and computing g'(x)=f'(x)-k, then checked the signs at both endpoints of the interval."))
check("en 奉送：left-multiply", _is_spoon("Next, left-multiply both sides by A to get a new equation."))
check("en 奉送：subtract ... times", _is_spoon("Subtract lambda_1 times the original equation."))
check("en 引導注意力不算奉送", not _is_spoon("First look at what dividing by n gives you. What remainders can appear?"))

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

print("[9] 重複回覆保底")


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
r1 = d5.step("I checked continuity on [a,b]. What value are we trying to get?")
check("重複命中後重生成出新句", r1.startswith("What value"))
check("重複輪標記 repeat 守衛", "repeat" in d5.state["turns"][-1].guards)

print()
if FAIL:
    print(f"✗ {len(FAIL)} 項失敗：{FAIL}")
    sys.exit(1)
print("全部單元測試通過 ✓")
