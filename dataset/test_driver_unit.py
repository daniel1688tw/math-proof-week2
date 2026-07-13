# -*- coding: utf-8 -*-
"""test_driver_unit.py — tutor_driver 的純邏輯單元測試（不載模型、不需 GPU）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tutor_driver import (
    TutorDriver, enforce_single_question, is_stuck, leaks_reference,
    load_problems_with_ladders,
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

print("[6] 英文偵測（雙語支援）")
from tutor_driver import detect_lang

check("純英文 → en", detect_lang("I have no idea how to start this problem.") == "en")
check("繁中 → zh", detect_lang("我不知道怎麼開始。") == "zh")
check("英文夾 LaTeX → en", detect_lang(r"Prove that $\lim_{x\to 2}x^2=4$ using epsilon-delta.") == "en")

check("en stuck: I don't know", is_stuck("I don't know how to continue."))
check("en stuck: no idea", is_stuck("Sorry, I have no idea."))
check("en stuck: still stuck, hint", is_stuck("I'm still stuck, can I get another hint?"))
check("en 實質嘗試不算 stuck",
      not is_stuck("I am not sure, but I tried setting g(x)=f(x)-kx and computing g'(x)=f'(x)-k, then I checked the signs of g'(a) and g'(b) at both endpoints of the interval."))

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
d3.step("I don't know.")
check("en 卡住累計", d3.state["stuck_count"] == 1)
sys_en = d3._system(0)
check("en session 的 system 是英文", "Socratic" in sys_en)

d4 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d4.generated_levels = []
d4.start()
check("中文 session 語言 = zh", d4.state.get("lang") == "zh")
check("zh system 不變", "蘇格拉底" in d4._system(0))

print("[7] 重複回覆保底")


class _RepeatDriver(TutorDriver):
    """前兩次生成回傳同一句，第三次（重生成）回傳新句。"""
    calls: int = 0

    def _generate_text(self, sys_txt):
        self.calls += 1
        if self.calls <= 2:
            return "Which hypothesis in the problem verifies one condition of that theorem?"
        return "What value does the theorem guarantee for f somewhere in the interval?"


d5 = _RepeatDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d5.calls = 0
d5.start(opener="I am confused, please guide me step by step.")
r1 = d5.step("I checked continuity on [a,b]. What value are we trying to get?")
check("重複命中後重生成出新句", r1.startswith("What value"))
check("重複輪有標記 regenerated", d5.state["turns"][-1].regenerated)
check("重生成共呼叫 3 次", d5.calls == 3)

print()
if FAIL:
    print(f"✗ {len(FAIL)} 項失敗：{FAIL}")
    sys.exit(1)
print("全部單元測試通過 ✓")
