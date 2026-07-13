# -*- coding: utf-8 -*-
"""tutor_driver.py — 有狀態的蘇格拉底助教對話驅動程式。

核心設計（HINT_REPORT_v5 的架構結論）：「升級時機」與「提示深度」不由模型隱式拿捏，
改由驅動程式確定性控制；模型只負責把指定等級的內容包裝成引導語氣。

  等級 0（預設）    ：只問一個聚焦問題，禁止點名任何定理/技巧名稱（修 C8 提前點名）。
  等級 1（卡住 1 次）：把上一問拆成更小、更具體的子問題，仍不點名。
  等級 2（卡住 2 次）：可透漏 hint ladder 中對應的一條想法（不給算式、不完成推導）。

推論端防護（不需重訓即生效）：
  * 單問句截斷：回覆若含多個問號，截到第一個問號為止（修複合問句）。
  * 洩漏 n-gram 檢查：回覆與參考解正規化後比對字元 15-gram；等級 <2 時命中
    即以更強約束重生成一次（greedy 下改變輸入才會改變輸出）。
  * on-track 防奉送（跨域評估 X2/X4 教訓）：等級 <2 且無特殊階段時，回覆若替學生
    指定具體代數操作（左乘/減去…倍/代入…）即重生成——學生方向正確時只肯定不奉送。
  * 等級 2 禁算式：提示只能點名想法，回覆若出現參考解之外的新等式/不等式即重生成
    （允許重現題目敘述或學生自己寫過的式子）。
  * 回問保底：等級 <2 的引導輪與 refuse_leak 輪必須以問題收尾，缺問句先重生成，
    仍缺則附上固定追問（確定性優於賭模型服從）。
  * 審閱後盾（混合架構，review_backstop.py）：review/rectify 輪先讓思考型模型
    對照參考解找碴，把缺漏清單注入階段指示——判斷交給思考型、說話交給微調模型。
    Ollama 不可用時靜默降級回原行為；REVIEW_BACKSTOP=0 可關閉。

用法：
  from tutor_driver import TutorDriver
  d = TutorDriver(tok, model, problem)          # problem: dict 含 statement/reference_proof/(hint_ladder)
  first = d.start()                              # 學生首則訊息由 d.start(opener=...) 帶入
  reply = d.step("學生回覆")                     # 逐輪推進；d.state 可檢視 stuck/level 記錄
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ── grounded system（與 build.py 的訓練模板同源；驅動程式逐輪追加等級指示）────────
BASE_SYSTEM = """你是蘇格拉底式高等數學引導助教。下面 <REFERENCE_PROOF> 內是參考解（學生看不到），僅供你確保提問指向正確的下一步，切勿洩漏其內容或最終結論。規則：每次只問一個聚焦問題、用精確數學術語、回覆 80 字內；學生方向正確就肯定並繼續推進，有邏輯漏洞就用問題引導其自行發現。學生走完所有關鍵步驟後，請他把完整證明寫出來；審閱他寫的證明時，若有缺漏就用一個問題指出、讓他自行補上。

<REFERENCE_PROOF>
{proof}
</REFERENCE_PROOF>"""

# 英文版 grounded system（與 BASE_SYSTEM 語義等價；session 語言為英文時採用）。
BASE_SYSTEM_EN = """You are a Socratic tutor for advanced mathematics proofs. The <REFERENCE_PROOF> below is a reference solution (invisible to the student); use it only to ensure your questions point toward the correct next step, and never leak its content or final conclusion. Rules: ask only one focused question per turn, use precise mathematical terminology, keep replies within about 60 words; if the student is on the right track, affirm and push forward; if there is a logical gap, guide them to discover it themselves through a question. Once the student has walked through all key steps, ask them to write out the complete proof; when reviewing their written proof, point out any gap with a single question and let them fix it themselves.

<REFERENCE_PROOF>
{proof}
</REFERENCE_PROOF>"""

LEVEL_INSTRUCTIONS = {
    0: "本輪指示：只問一個聚焦問題，不要點名任何定理或技巧名稱，讓學生自己想方向。",
    1: "本輪指示：學生剛才答不出來。把上一個問題拆成更小、更具體的子問題再問一次，仍然不要點名定理或技巧名稱。",
    2: "本輪指示：學生已連續兩次答不出來，本輪必須透漏想法。回覆的第一句要明確說出下面提示裡的定理／技巧名稱或核心想法（這是此輪允許且必要的透漏，不要再用反問代替），第二句問一個讓學生自己接手推導的問題。不要給任何算式、不要替學生完成任何一步計算。\n提示內容：{hint}",
}

LEVEL_INSTRUCTIONS_EN = {
    0: "This turn: ask exactly one focused question. Do not name any theorem or technique; let the student find the direction themselves.",
    1: "This turn: the student just failed to answer. Break your previous question into a smaller, more concrete sub-question and ask again. Still do not name any theorem or technique.",
    2: "This turn: the student has failed twice in a row, so you must reveal an idea now. Your first sentence must explicitly state the theorem/technique name or core idea from the hint below (this reveal is required this turn - do not replace it with another counter-question); your second sentence asks one question that lets the student take over the derivation. Do not give any formula and do not carry out any computation for the student.\nHint: {hint}",
}

# 卡住偵測：短回覆且含「答不出」語彙（確定性、可測試）
_STUCK_RE = re.compile(
    r"不知道|不會|想不到|想不出|沒(有)?頭緒|不確定|不太懂|不明白|卡住|再提示|"
    r"沒(有)?想法|毫無頭緒|完全沒概念"
)
_STUCK_EN_RE = re.compile(
    r"i don'?t know|no idea|no clue|not sure|stuck|confused|"
    r"can'?t (figure|see|think)|i'?m lost|(another|more|give me a) hint",
    re.I,
)
_QMARK_RE = re.compile(r"[?？]")

# 階段偵測（v6 專項測試發現：階段轉換也不能賭模型慣性，由驅動程式判定）
_UNDERSTOOD_RE = re.compile(
    r"思路.{0,6}(懂|有了|清楚)|都懂了|我懂了|我會了|理解了|"
    r"i understand now|now i understand|i (got|get) it( now)?|makes sense now|i see it now",
    re.I,
)
_DRAFT_RE = re.compile(
    r"證明[:：]|請幫我審閱|寫好了|"
    r"here is my proof|my proof:|proof:|please review|i('| ha)ve written|i wrote (it|the|my) proof",
    re.I,
)
# 逼問偵測（v6 回歸發現 S3 抗洩漏被 hint/writeup 資料稀釋，改由 driver 確定性防護）
_DEMAND_RE = re.compile(
    r"直接.{0,14}(告訴我|給我|寫給我|說出來|貼給我|抄給我)|給我答案|不要問我|"
    r"直接給出|完整證明.{0,6}(給|寫)|把答案|抄一份|"
    r"just tell me|give me the (answer|full proof|solution|whole proof)|"
    r"write (it|the proof)( out)? for me|show me the (full|complete|whole) (proof|solution)|"
    r"stop asking|don'?t ask me",
    re.I,
)
# 嘗試偵測：學生交來一段自己的推導求確認 → 糾錯模式（此時可點名其誤用定理的前提）
_ATTEMPT_RE = re.compile(
    r"這樣對嗎|對不對|我的嘗試|我是這樣(想|做)|我認為|我覺得|"
    r"is (this|that|it) (right|correct)|am i (right|correct)|my attempt|"
    r"i think|i believe|does (this|that) work|here'?s what i did",
    re.I,
)

# 語言偵測：CJK 字元占比 <10% 判為英文（session 級，首則訊息決定）
_CJK_RE = re.compile(r"[一-鿿]")


def detect_lang(text: str) -> str:
    # LaTeX 數學片段與指令語言中立，先剝除再算 CJK 占比
    text = re.sub(r"\$[^$]*\$|\\[A-Za-z]+", " ", text)
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return "zh"
    cjk = sum(1 for c in chars if _CJK_RE.match(c))
    return "en" if cjk / len(chars) < 0.10 else "zh"

PHASE_INSTRUCTIONS = {
    "refuse_leak": (
        "本輪指示：學生要求直接得到答案或完整證明。用一句話溫和拒絕（說明自己推導才真正有用），"
        "然後問一個具體的數學問題把主導權還給學生。絕對不要給出證明的任何步驟、算式或結論。"
    ),
    "rectify": (
        "本輪指示：學生提交了自己的嘗試。對照參考解檢查：若有錯誤，用一個問題指出關鍵錯誤處、"
        "讓他自行發現與修正（可指出他誤用的定理缺了什麼前提，但不要替他改寫）；"
        "若方向正確，簡短肯定並問下一步。不要被學生的自信影響你的判斷。"
    ),
    "writeup_request": (
        "本輪指示：學生表示已理解整個思路。請他把完整證明自己寫出來（你將負責審閱），"
        "不要再問步驟問題、不要總結、不要宣告完成。"
    ),
    "review": (
        "本輪指示：學生交來完整證明草稿。對照參考解逐步檢查，優先找這幾類缺漏："
        "引用定理的前提沒驗證、引用的事實沒交代依據（例如比較對象為何收斂）、"
        "嚴格與非嚴格不等號混用、特例未排除、量詞順序錯誤。"
        "找到後挑最重要的一個，用一個問題指出、讓他自行修正；正確的步驟不要質疑；"
        "只有在完全沒有缺漏時才可確認完成。"
    ),
}

PHASE_INSTRUCTIONS_EN = {
    "refuse_leak": (
        "This turn: the student demands the answer or the full proof directly. Gently refuse in one "
        "sentence (explain that deriving it themselves is what actually helps), then ask one concrete "
        "mathematical question to hand control back to the student. Never give any step, formula, or "
        "conclusion of the proof."
    ),
    "rectify": (
        "This turn: the student submitted their own attempt. Check it against the reference proof: if "
        "there is an error, point to the key mistake with one question and let them discover and fix it "
        "themselves (you may name the missing hypothesis of a theorem they misused, but do not rewrite "
        "it for them); if they are on the right track, affirm briefly and ask about the next step. Do "
        "not let the student's confidence sway your judgment."
    ),
    "writeup_request": (
        "This turn: the student says they understand the whole idea. Ask them to write out the complete "
        "proof themselves (you will review it). Do not ask further step-by-step questions, do not "
        "summarize, and do not declare completion."
    ),
    "review": (
        "This turn: the student submitted a complete proof draft. Check it step by step against the "
        "reference proof, prioritizing these gaps: theorem hypotheses not verified, cited facts without "
        "justification (e.g. why a comparison series converges), strict vs non-strict inequalities "
        "mixed up, special cases not excluded, quantifier order errors. Pick the most important gap and "
        "point to it with one question so the student fixes it themselves; do not question correct "
        "steps; only confirm completion when there is no gap at all."
    ),
}

# writeup_request 的保底回覆：階段轉換是公式化行為，模型若被「完成→確認」慣性帶走，
# driver 直接以此模板取代（確定性優於賭模型服從指示）。
WRITEUP_FALLBACK = "思路已經完整了。現在請把完整證明一步步寫出來，我會幫你審閱。"
WRITEUP_FALLBACK_EN = ("The idea is now complete. Please write out the full proof step by step, "
                       "and I will review it for you.")
_WRITEUP_OK_RE = re.compile(r"寫出|寫下|自己寫|完整證明|write (out|up|it)|full proof|complete proof", re.I)


def is_stuck(student_text: str) -> bool:
    """學生回覆是否屬於「答不出來」。長回覆（有實質嘗試）不算卡住。
    英文回覆詞長較長，長度門檻放寬到 120 字元。"""
    t = student_text.strip()
    if detect_lang(t) == "en":
        return bool(_STUCK_EN_RE.search(t)) and len(t) <= 120
    return bool(_STUCK_RE.search(t)) and len(t) <= 60


def enforce_single_question(reply: str) -> str:
    """複合問句防護：截到第一個問號為止（保留其前的陳述句）。"""
    m = _QMARK_RE.search(reply)
    if not m:
        return reply
    rest = reply[m.end():]
    if not _QMARK_RE.search(rest):
        return reply  # 只有一個問號，不動
    return reply[: m.end()].strip()


def _normalize(s: str) -> str:
    """洩漏比對前的正規化：移除空白、$、LaTeX 反斜線與常見裝飾。"""
    s = re.sub(r"[\s$]", "", s)
    s = s.replace("\\dfrac", "\\frac").replace("\\left", "").replace("\\right", "")
    return s


def leaks_reference(reply: str, proof: str, n: int = 15) -> bool:
    """回覆是否含參考解的長片段（正規化後字元 n-gram 重疊）。"""
    a, b = _normalize(reply), _normalize(proof)
    if len(a) < n:
        return False
    grams = {b[i: i + n] for i in range(len(b) - n + 1)}
    return any(a[i: i + n] in grams for i in range(len(a) - n + 1))


# on-track 防奉送：等級 0/1 不得替學生「指定具體代數操作」（引導注意力的動詞如
# 看/想/回想不算；替他做步驟的操作動詞才算）。窄匹配以避免誤殺正常引導問句。
_SPOONFEED_RE = re.compile(
    r"左乘|右乘|同乘|兩邊(?:乘|除|加|減)|減去[^，。？]{0,18}倍|代入|移項|"
    r"先寫出|寫出[^，。？]{0,12}(?:假設|方程|等式|式子)"
)
# 英文奉送模式：替學生指定具體代數操作（引導注意力的 look/recall 不算）。
_SPOONFEED_EN_RE = re.compile(
    r"(left|right)-?multiply|multiply (both sides|through)|subtract [^.?!]{0,24}times|"
    r"substitute [^.?!]{0,20}into|move [^.?!]{0,16}to the other side|"
    r"first write (out|down) [^.?!]{0,20}(assumption|equation|identity)",
    re.I,
)


def is_spoonfeeding(reply: str) -> bool:
    """回覆是否替學生指定了具體代數操作（on-track 洩漏模式；中英雙語）。"""
    return bool(_SPOONFEED_RE.search(reply) or _SPOONFEED_EN_RE.search(reply))


# 等級 2 禁算式：抓「含 = / ≤ / ≥ / \le / \ge 的連續數學片段」
_EQ_TOKEN_RE = re.compile(r"[^\s，。？！；、]*(?:=|≤|≥|\\le\b|\\ge\b)[^\s，。？！；、]*")


def gives_new_equation(reply: str, allowed_src: str) -> bool:
    """回覆是否出現 allowed_src（題目敘述＋提示＋學生說過的話）之外的新等式。"""
    allowed = _normalize(allowed_src)
    for tok in _EQ_TOKEN_RE.findall(reply):
        t = _normalize(tok)
        if len(t) < 3:
            continue
        if t not in allowed:
            return True
    return False


@dataclass
class TurnLog:
    level: int
    stuck_count: int
    leak_flag: bool = False
    regenerated: bool = False
    guards: list = field(default_factory=list)   # 本輪觸發過的防護名稱（spoonfeed/formula/no_question）


@dataclass
class TutorDriver:
    tok: object
    model: object
    problem: dict                      # 需含 statement / reference_proof；可選 hint_ladder(list[str])
    max_new_tokens: int = 240
    # 審閱後盾開關（預設開；Ollama 不在線會自動降級，REVIEW_BACKSTOP=0 強制關）
    backstop: bool = field(
        default_factory=lambda: os.environ.get("REVIEW_BACKSTOP", "1") == "1")
    state: dict = field(default_factory=lambda: {
        "stuck_count": 0, "ladder_idx": 0, "turns": [],   # turns: list[TurnLog]
    })
    messages: list = field(default_factory=list)

    # ---- 生成 ----------------------------------------------------------------
    @property
    def lang(self) -> str:
        return self.state.get("lang", "zh")

    def _backstop_block(self) -> str:
        """把後盾複核結果組成注入 system 的指示段；後盾未啟用/失敗時為空字串。"""
        gaps = self.state.get("backstop_gaps")
        if gaps is None:
            return ""
        if self.lang == "en":
            if not gaps:
                return ("\n[REVIEW CHECK] The review backstop has checked the draft step by step "
                        "against the reference proof: no gaps found. If you agree, affirm the student "
                        "directly and do not invent problems out of thin air.")
            lines = "\n".join(f"- {g}" for g in gaps)
            return ("\n[REVIEW CHECK] The review backstop checked step by step against the reference "
                    "proof and found these gaps (reliable, ordered by severity):\n" + lines +
                    "\nUse only this list: take the first item and guide the student with one question "
                    "to discover and fix it themselves; do not raise questions outside the list, and do "
                    "not state the correct version of the gap outright.")
        if not gaps:
            return ("\n【複核結果】審閱後盾已對照參考解逐步複核：未發現缺漏。"
                    "若你也同意，直接肯定學生，不要憑空發明問題。")
        lines = "\n".join(f"- {g}" for g in gaps)
        return ("\n【複核結果】審閱後盾已對照參考解逐步複核，找出以下缺漏"
                "（可信，按嚴重程度排序）：\n" + lines +
                "\n請只依據這份清單：挑第一項，用一個問題引導學生自行發現並修正；"
                "不要提清單以外的問題，也不要把缺漏的正確版本直接講完。")

    def _consult_backstop(self, student_text: str) -> None:
        """review/rectify 輪呼叫思考型模型找碴；結果存 state['backstop_gaps']。"""
        self.state["backstop_gaps"] = None
        if not self.backstop:
            return
        try:
            from review_backstop import find_gaps
        except ImportError:
            return
        self.state["backstop_gaps"] = find_gaps(
            self.problem["statement"], self.problem["reference_proof"], student_text)

    def _system(self, level: int) -> str:
        en = self.lang == "en"
        base = BASE_SYSTEM_EN if en else BASE_SYSTEM
        phase_map = PHASE_INSTRUCTIONS_EN if en else PHASE_INSTRUCTIONS
        level_map = LEVEL_INSTRUCTIONS_EN if en else LEVEL_INSTRUCTIONS
        sys_txt = base.format(proof=self.problem["reference_proof"])
        phase = self.state.get("phase")
        if phase in phase_map:                   # 階段指示優先於等級指示
            instr = phase_map[phase]
            if phase in ("review", "rectify"):
                instr += self._backstop_block()
        elif level == 2:
            key = "hint_ladder_en" if en else "hint_ladder"
            ladder = self.problem.get(key) or self.problem.get("hint_ladder") or []
            idx = min(self.state["ladder_idx"], max(len(ladder) - 1, 0))
            if ladder:
                hint = ladder[idx]
            elif en:
                hint = "Name the key theorem or idea this step needs (no formulas)."
            else:
                hint = "點出此步驟所需的關鍵定理或想法名稱（不給算式）。"
            instr = level_map[2].format(hint=hint)
        else:
            instr = level_map[level]
        return sys_txt + "\n\n" + instr

    def _generate(self, level: int) -> str:
        import torch
        msgs = [{"role": "system", "content": self._system(level)}] + self.messages
        enc = self.tok.apply_chat_template(
            msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                **enc, max_new_tokens=self.max_new_tokens, do_sample=False,
                repetition_penalty=1.05,
                pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id,
            )
        return self.tok.decode(out[0][enc["input_ids"].shape[1]:],
                               skip_special_tokens=True).strip()

    def _regen(self, level: int, note: str) -> str:
        """以加強約束的 system 重生成一次（greedy 下改變輸入才會改變輸出）。"""
        import torch
        stronger = self._system(level) + f"\n（注意：{note}）"
        msgs = [{"role": "system", "content": stronger}] + self.messages
        enc = self.tok.apply_chat_template(
            msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                **enc, max_new_tokens=self.max_new_tokens, do_sample=False,
                repetition_penalty=1.05,
                pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id,
            )
        return enforce_single_question(
            self.tok.decode(out[0][enc["input_ids"].shape[1]:],
                            skip_special_tokens=True).strip())

    def _allowed_equation_src(self) -> str:
        """等級 2 算式檢查的白名單來源：題目敘述＋當前提示＋學生說過的話。"""
        ladder = self.problem.get("hint_ladder") or []
        idx = min(self.state["ladder_idx"], max(len(ladder) - 1, 0))
        hint = ladder[idx] if ladder else ""
        student = "".join(m["content"] for m in self.messages if m["role"] == "user")
        return self.problem["statement"] + hint + student

    def _repeats_previous(self, reply: str) -> bool:
        """回覆是否與最近 3 輪助教回覆（正規化後）完全相同。"""
        prev = [m["content"] for m in self.messages if m["role"] == "assistant"][-3:]
        norm = _normalize(reply)
        return any(norm == _normalize(p) for p in prev)

    def _tutor_turn(self) -> str:
        level = min(self.state["stuck_count"], 2)
        phase = self.state.get("phase")
        reply = self._generate(level)
        reply = enforce_single_question(reply)

        en = self.lang == "en"
        # 階段保底：writeup_request 輪若模型沒請學生寫證明，直接用模板取代
        if phase == "writeup_request" and not _WRITEUP_OK_RE.search(reply):
            reply = WRITEUP_FALLBACK_EN if en else WRITEUP_FALLBACK

        log = TurnLog(level=level, stuck_count=self.state["stuck_count"])
        if phase in ("review", "rectify") and self.state.get("backstop_gaps") is not None:
            log.guards.append("backstop")
        # 等級 <2 不允許出現參考解長片段；命中則加強約束重生成一次
        if level < 2 and leaks_reference(reply, self.problem["reference_proof"]):
            log.leak_flag = True
            reply = self._regen(level, (
                "Your previous draft quoted the reference proof verbatim. Rewrite it and avoid "
                "reproducing any formula word-for-word." if en else
                "上一稿引用了參考解的原文片段，重寫並避免逐字重現任何式子。"))
            log.regenerated = True

        # on-track 防奉送：一般引導輪與拒絕輪（refuse_leak 規則本就禁止給步驟），
        # 等級 <2 不得替學生指定具體代數操作
        if level < 2 and phase in (None, "refuse_leak") and is_spoonfeeding(reply):
            log.guards.append("spoonfeed")
            reply = self._regen(level, (
                "Your previous draft prescribed a concrete algebraic operation (such as multiplying, "
                "subtracting, substituting). Rewrite: state no operation step; instead ask the student "
                "an open question like how they plan to proceed." if en else
                "上一稿替學生指定了具體代數操作（如左乘、相減、代入）。"
                "重寫：不要說出任何操作步驟，改問學生「打算怎麼處理」這類開放問題。"))
            log.regenerated = True

        # 等級 2 禁算式：提示只能點名想法/名稱，不得出現白名單外的新等式
        if level == 2 and gives_new_equation(reply, self._allowed_equation_src()):
            log.guards.append("formula")
            reply = self._regen(level, (
                "Your previous draft contained a formula. Rewrite: state only the theorem/technique "
                "name or idea from the hint, and never write any equation or inequality; let the "
                "student derive it themselves." if en else
                "上一稿包含了算式。重寫：只說出提示裡的定理／技巧名稱或想法，"
                "絕對不要寫出任何等式或不等式，讓學生自己動筆推。"))
            log.regenerated = True

        # 回問保底：引導輪與 refuse_leak 輪必須以問題收尾
        if level < 2 and phase in (None, "refuse_leak") and not _QMARK_RE.search(reply):
            log.guards.append("no_question")
            regen = self._regen(level, (
                "Your previous draft had no question. Rewrite: it must end with one question guiding "
                "the student to the next step." if en else
                "上一稿沒有問題句。重寫：最後必須是一個引導學生思考下一步的問句。"))
            if _QMARK_RE.search(regen):
                reply = regen
                log.regenerated = True
            else:
                reply = reply.rstrip() + (" So where do you think the next step should start?"
                                          if en else " 那你覺得，下一步該從哪裡下手？")

        # 重複回問保底：與近 3 輪助教回覆相同 → 加強指示重生成一次（中英共用）
        if self._repeats_previous(reply):
            log.guards.append("repeat")
            reply = self._regen(level, (
                "Your previous draft repeated a question you already asked. Do not repeat any earlier "
                "question; respond to the student's latest message and ask one new question that moves "
                "to the next step." if en else
                "上一稿重複了你先前問過的問題。不要重複任何舊問題，針對學生最新訊息回應，"
                "問一個推進到下一步的新問題。"))
            log.regenerated = True

        if level == 2:
            self.state["ladder_idx"] += 1     # 下次再進等級 2 用下一條提示
            self.state["stuck_count"] = 0     # 給過想法後重新計數
        self.state["turns"].append(log)
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    # ---- 階段偵測（start 與 step 共用；優先序：交草稿 > 逼問 > 懂了）-----------
    def _detect_phase(self, student_text: str) -> None:
        if _DRAFT_RE.search(student_text):
            self.state["phase"] = "review"
        elif _DEMAND_RE.search(student_text):
            self.state["phase"] = "refuse_leak"
        elif _ATTEMPT_RE.search(student_text):
            self.state["phase"] = "rectify"
        elif _UNDERSTOOD_RE.search(student_text) and not self.state.get("writeup_asked"):
            self.state["phase"] = "writeup_request"
            self.state["writeup_asked"] = True
        else:
            self.state["phase"] = None

    # ---- 對外 API -------------------------------------------------------------
    def start(self, opener: str | None = None) -> str:
        # session 語言：有 opener 依 opener 判定，否則依題目陳述
        self.state["lang"] = detect_lang(opener if opener else self.problem["statement"])
        if self.lang == "en":
            opener = opener or "I've read the problem but don't know how to start. Could you give me a first hint?"
            first = f"Problem: {self.problem['statement']}\n\n{opener}"
        else:
            opener = opener or "我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？"
            first = f"題目：{self.problem['statement']}\n\n{opener}"
        self._detect_phase(first)
        if self.state.get("phase") in ("review", "rectify"):
            self._consult_backstop(first)
        self.messages = [{"role": "user", "content": first}]
        return self._tutor_turn()

    def step(self, student_text: str) -> str:
        if "lang" not in self.state:             # 未經 start() 直接 step 時補判語言
            self.state["lang"] = detect_lang(student_text)
        self._detect_phase(student_text)
        if self.state.get("phase") in ("review", "rectify"):
            self._consult_backstop(student_text)
        else:
            self.state["backstop_gaps"] = None
        if is_stuck(student_text):
            self.state["stuck_count"] += 1
        else:
            self.state["stuck_count"] = 0
        self.messages.append({"role": "user", "content": student_text})
        return self._tutor_turn()


def load_problems_with_ladders() -> dict:
    """合併 problems.json / held_out.json / hard_math_major.json 與 hint_ladders.json。"""
    problems = {}
    for fname in ("problems.json", "held_out.json", "hard_math_major.json"):
        p = HERE / fname
        if p.exists():
            for item in json.loads(p.read_text(encoding="utf-8")):
                problems[item["id"]] = item
    for fname, key in (("hint_ladders.json", "hint_ladder"),
                       ("hint_ladders_en.json", "hint_ladder_en")):
        lad = HERE / fname
        if lad.exists():
            for pid, ladder in json.loads(lad.read_text(encoding="utf-8")).items():
                if pid in problems:
                    problems[pid][key] = ladder
    return problems
