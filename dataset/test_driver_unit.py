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
check("『聽不懂這步。』→ stuck（e2e 發現的缺口）", is_stuck("聽不懂這步。"))
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

d6 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d6.generated_levels = []
d6.start(opener="所以我們就證完了，對吧？最小值是 0 且在 x=0 取得，因此對所有 x 都成立。")
check("實質宣告證完 → review 且 arm done_closed",
      d6.state["phase"] == "review" and d6.state.get("done_closed"))
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
d7 = _StubDriver(tok=None, model=_StubModel(), problem=probs["A6"])
d7.generated_levels = []
d7.start(opener="So that completes the proof, right? The minimum value is 0, attained "
                "only at x = 0, so it holds for all x.")
check("EN 實質宣告證完 → review 且 arm done_closed",
      d7.state["phase"] == "review" and d7.state.get("done_closed"))
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
    """生成與重生成都不含問句 → 每輪都走保底附加路徑。"""

    def _generate(self, level):
        return f"Good, that completes the argument (turn {len(self.messages)})."

    def _regen(self, level, note):
        return f"Nice work, the proof is complete (turn {len(self.messages)})."


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

print()
if FAIL:
    print(f"✗ {len(FAIL)} 項失敗：{FAIL}")
    sys.exit(1)
print("全部單元測試通過 ✓")
