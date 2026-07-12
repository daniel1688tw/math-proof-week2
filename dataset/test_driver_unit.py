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
        return f"（等級{level}的回覆）這一步該怎麼想？"


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

print("[8] 自我驗證教學：備課解析 / walkthrough 狀態機 / 同學模式")
from auto_reference import fallback_steps, parse_steps, parse_verdict  # noqa: E402
from tutor_driver import PEER_DISCLAIMER  # noqa: E402

check("verdict pass 可解析",
      parse_verdict('{"verdict": "pass", "issues": []}') == {"verdict": "pass", "issues": []})
check("verdict fail 含 LaTeX escape 降級解析",
      (parse_verdict(r'思考後：{"verdict": "fail", "issues": ["$\frac{p+q}{2}$ 是有理數"]}')
       or {}).get("verdict") == "fail")
check("verdict 垃圾輸出 → None", parse_verdict("我覺得這證明還行。") is None)
s_ok = parse_steps('[{"explain": "先建立包含關係", "check": "Tv 在哪個集合？"},'
                   '{"explain": "套秩零度定理", "check": "兩維度和是多少？"}]')
check("teach_steps 可解析", s_ok is not None and len(s_ok) == 2 and s_ok[0]["check"])
check("teach_steps 缺欄位 → None", parse_steps('[{"explain": "只有講解"}]') is None)
fb = fallback_steps("第一段。\n\n第二段。\n\n第三段。")
check("保底切分：三段 → 3 步且含通用確認問句",
      len(fb) == 3 and "複述" in fb[0]["check"])

_walk_prob = {
    "id": "W1", "statement": "測試題", "reference_proof": "步驟甲。\n\n步驟乙。",
    "hint_ladder": ["提示一", "提示二"],
    "teach_steps": [{"explain": "教步驟甲", "check": "甲懂了嗎？"},
                    {"explain": "教步驟乙", "check": "乙懂了嗎？"}],
}
w = _StubDriver(tok=None, model=_StubModel(), problem=dict(_walk_prob))
w.generated_levels = []
w.messages = [{"role": "user", "content": "題目…開始"}]
w.state["ladder_idx"] = 2                      # 模擬提示梯已用盡
w.step("我不知道，想不出來。")                  # 卡 1
check("卡 1 尚未進入教學", not w.state.get("walk_active"))
w.step("還是不會。")                            # 卡 2 → 進入 walkthrough
check("提示梯用盡＋連卡兩次 → 進入 walkthrough",
      w.state.get("walk_active") and w.state["phase"] == "walkthrough"
      and w.state["walk_idx"] == 0)
check("walkthrough system 注入步驟與確認問題",
      "教步驟甲" in w._system(0) and "甲懂了嗎" in w._system(0))
w.step("聽不懂，不明白。")                       # 同步驟卡住 → 重講一次
check("卡住 → 同一步重講（walk_idx 不動、retry=1）",
      w.state["walk_idx"] == 0 and w.state["walk_retry"] == 1
      and "更簡單的講法" in w._system(0))
w.step("還是不太懂。")                           # 重講過仍卡 → 前進
check("重講過仍卡 → 前進到步驟 2", w.state["walk_idx"] == 1)
w.step("喔，甲我懂了！")                         # 答得出 → 前進；步驟用盡 → 請寫證明
check("步驟教完 → 轉 writeup_request 且教學結束",
      not w.state.get("walk_active") and w.state["phase"] == "writeup_request")

w2 = _StubDriver(tok=None, model=_StubModel(), problem=dict(_walk_prob))
w2.generated_levels = []
w2.messages = [{"role": "user", "content": "題目…開始"}]
w2.state.update(walk_active=True, walk_idx=0, walk_retry=0, phase="walkthrough",
                ladder_idx=2)
w2.step("證明：如下……請幫我審閱。")
check("教學中交草稿 → 打斷進 review", w2.state["phase"] == "review"
      and not w2.state.get("walk_active"))

class _PeerStub(_StubDriver):
    def _generate(self, level):
        self.generated_levels.append(level)
        return "說不定可以從定義下手。你覺得呢？"

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

print()
if FAIL:
    print(f"✗ {len(FAIL)} 項失敗：{FAIL}")
    sys.exit(1)
print("全部單元測試通過 ✓")
