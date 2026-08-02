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

自我驗證教學擴充（self_verified_teaching_design.md）：
  * 同學模式：題目 grounding=unverified（自動備課驗證失敗、無可靠參考解）時，
    放下助教權威改用同儕 persona——想法標明不確定、首輪誠實聲明沒把握、
    學生質疑時注入反省指示認真重檢自己。洩漏/防奉送/禁算式防護停用（無參考解可護），
    單問句與回問保底保留。
  * 逐步教學（walkthrough）：hint ladder 用盡後學生再度連卡兩次 → 自動進入。
    每輪講解一個教學步驟（teach_steps，備課切分或保底段落切分）＋問確認小問題；
    學生答不出同一步最多重講一次（更簡單說法）後前進；走完接回 writeup→review，
    學生仍要自己寫出完整證明。此階段教學步驟允許寫式子（洩漏防護對步驟內容放行）。

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
    r"不知道|不會|想不到|想不出|沒(有)?頭緒|不確定|不太?懂|不明白|卡住|再提示|"
    r"沒(有)?想法|毫無頭緒|完全沒概念"
)
# 「don't know」「not sure」允許中間插最多兩個副詞：口語極常見的
# "I don't even know" / "I'm not really sure" 若要求連續就會漏接，學生明說不會
# 卻拿不到提示升級（2026-08-01 加「重度卡關型」persona 時，用 agy 實測學生產出才發現）。
_STUCK_EN_RE = re.compile(
    r"i don'?t (?:\w+ ){0,2}know|no idea|no clue|not (?:\w+ ){0,2}sure|stuck|confused|"
    r"can'?t (figure|see|think|do)|i can'?t\.?$|(completely|totally)? ?lost|"
    r"(another|more|give me a) hint",
    re.I,
)
# 強困惑：不受長度門檻限制（學生寫了一段實質嘗試、但明說徹底卡死 → 仍該升級提示，
# 否則 tutor 只會重述或把問題丟回去——長訊息＋強困惑正是最挫折的時刻）
_STRONG_STUCK_RE = re.compile(
    r"毫無頭緒|完全沒(有)?概念|完全不懂|完全不明白|完全卡住|真的不會|"
    r"聽不懂|看不懂你|不懂你(的)?意思|"
    r"(completely|totally|utterly) (lost|stuck|confused)|no idea at all|"
    r"i (really )?don'?t understand (what|your|this at all)|makes no sense to me",
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
# 宣告完成偵測（弱點 #3，M4 教訓：口頭論證「聽起來完整」時助教傾向直接放行）。
# 訊息含實質內容（≥80 字元）且宣告證完 → 當成交稿走 review＋審閱後盾逐步複核；
# 短宣告（只喊「證完了」沒內容）不路由，交給一般流程請他把證明寫出來。
_CLAIM_DONE_RE = re.compile(
    r"證完了|證明完(成|畢)|這樣就證(好|完)|(所以|因此|故)得證|得證。|"
    r"q\.?e\.?d\.?|that (completes|finishes) the proof|proof is (now )?(complete|done|finished)|"
    r"(this|which) proves (it|the (claim|statement|result))|we('| a)re done",
    re.I,
)
# 助教親口確認「整個證明完成」偵測（弱點 #12，2026-07-24）：對話中途自然證完時，
# done_closed 原本只從學生宣告 arm（_CLAIM_DONE_RE），接不住「學生逐步推到終點、
# 助教確認完成」——H5 型過度延伸即由此漏出（助教確認完成後主動延伸推廣）。
# 措辭須是「整個/你的/這份證明完成」等級（非單步「這一步對」），避免 mid-proof 誤判；
# 主動語（你完成了證明）與「證明已完成」也算（update.md 稽核：原版漏掉最自然的說法）。
_TUTOR_DONE_RE = re.compile(
    r"(整個|你的|這份|該)證明.{0,6}(完成|完畢)|證明已.{0,3}(完成|完畢)|"
    r"證明.{0,4}(完成了|完畢)|證明.{0,3}到此(完成|結束)|"
    r"你.{0,4}(完成|寫完).{0,4}(整個)?證明|大功告成|"
    r"(the|your) proof is (now )?complete|proof is complete as written|"
    r"that completes (the|your) proof|you'?ve (now )?completed the (whole )?proof",
    re.I,
)
# 否定式（「還沒完成」）不算確認完成——放寬 _TUTOR_DONE_RE 後必須配這道反向閘。
_NOT_DONE_RE = re.compile(
    r"(還沒|尚未|還未|沒有?|不算|未)\s*(完成|完畢|寫完|證完)|"
    r"(is )?not (yet )?complete|isn'?t (yet )?(complete|done)",
    re.I,
)
# 「這一步的證明完成了」講的是單一步驟不是整份證明 → 不算確認完成。
# mid-proof 誤 arm 會讓助教在證明途中就進 closed（被指示不准再問問題），比漏 arm 嚴重。
_STEP_SCOPE_RE = re.compile(r"(這|那|該)一?步.{0,10}證明|(this|that) step'?s? proof", re.I)
# 助教自行請學生交稿偵測（2026-07-29 守門 H5/zh 實例）：driver 只在 _UNDERSTOOD_RE
# 命中時才進 writeup_request 並記下 writeup_asked，但模型常自己開口請學生寫證明
# （學生用「這樣就算證完了嗎」表達理解時尤其如此，那不命中 _UNDERSTOOD_RE）。
# 沒記錄下來，學生接著交出的草稿就走不到「已請學生寫證明」分支 → 不進 review →
# 拿不到審閱通過訊號 → 收尾輪被補上保底追問句。與 #12 是對稱的補丁。
#
# 措辭必須帶「完整／整份／整個」等**整份範圍**：「把這一步的證明寫下來」「你能自己
# 寫出證明的第一步嗎」是證明途中的常態引導，誤記成交稿請求有兩個下游傷害——
#   (a) 之後的長訊息被當成完整草稿路由進 review（後盾拿半成品逐步找碴）；
#   (b) writeup_asked 是單向閂（_detect_phase 的 not writeup_asked），誤設之後
#       學生真的說「我懂了」時再也進不了 writeup_request。
_ASK_WRITEUP_RE = re.compile(
    r"(完整|整份|整個).{0,4}證明.{0,8}寫(出來|下來|出|下)|"
    r"寫(出|下).{0,8}(完整|整份|整個).{0,4}證明|"
    r"write (out |up )?(the|your) (full|complete|whole) proof",
    re.I,
)
# 拒絕洩漏輪也會提到「寫出完整證明」（「我不能直接寫出完整證明給你」）→ 反向閘。
# 只看命中片段所在的**子句**：掃整則會被別句的否定詞誤殺（「把完整證明寫出來吧，
# 不會太難」「請自己寫出完整證明，不能只寫結論」實測都會被擋掉）。
_REFUSE_WRITEUP_RE = re.compile(
    r"不能|不會|無法|不可以|不該|won'?t|can'?t|cannot|will not", re.I)
_CLAUSE_SPLIT_RE = re.compile(r"[。！？；，、\n.!?;,]")


def asks_for_full_writeup(text: str) -> bool:
    """助教這則回覆是否等於「請學生把完整證明交出來」。"""
    if not text:
        return False
    m = _ASK_WRITEUP_RE.search(text)
    if not m:
        return False
    left = 0
    for sep in _CLAUSE_SPLIT_RE.finditer(text, 0, m.start()):
        left = sep.end()
    sep = _CLAUSE_SPLIT_RE.search(text, m.end())
    clause = text[left:sep.start() if sep else len(text)]
    return not _REFUSE_WRITEUP_RE.search(clause)


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
        "只有在完全沒有缺漏時才可確認完成——確認完成後就肯定收尾，"
        "不要拋出延伸問題、變形題或新題目（完成即收手）。"
    ),
    "closed": (
        "本輪指示：這道證明已經完成並確認過了。學生只是補充感想或反思，"
        "請用一兩句溫暖地回應、肯定他的收穫即可。不要再拋出任何新問題、"
        "不要提出替代證法、變形題或延伸方向；若他沒有新的數學問題就自然收尾。"
        "若他針對這道已完成的證明提了一個問題，就只簡短回答那一個問題本身，"
        "不要藉機引入新方法、推廣、變形或超出他所問範圍的延伸；答完即收尾。"
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
        "steps; only confirm completion when there is no gap at all — and once you confirm completion, "
        "close with the affirmation; do not pose extension questions, variants, or new problems."
    ),
    "closed": (
        "This turn: the proof is already complete and confirmed. The student is only adding a remark or "
        "reflection. Respond warmly in one or two sentences, affirming what they took away. Do NOT ask "
        "any new question, do NOT propose an alternative proof, a variant, or an extension; if they have "
        "no further mathematical question, simply close. If they do ask one question about this "
        "completed proof, answer only that one question concisely; do not introduce new methods, "
        "generalizations, variants, or any extension beyond what they asked, then close."
    ),
}

# writeup_request 的保底回覆：階段轉換是公式化行為，模型若被「完成→確認」慣性帶走，
# driver 直接以此模板取代（確定性優於賭模型服從指示）。
WRITEUP_FALLBACK = "思路已經完整了。現在請把完整證明一步步寫出來，我會幫你審閱。"
WRITEUP_FALLBACK_EN = ("The idea is now complete. Please write out the full proof step by step, "
                       "and I will review it for you.")
_WRITEUP_OK_RE = re.compile(r"寫出|寫下|自己寫|完整證明|write (out|up|it)|full proof|complete proof", re.I)

# ── 同學模式（grounding=unverified：自動備課驗證失敗，誠實降級為同儕）──────────────
PEER_SYSTEM = """你是和學生一起解這道數學證明題的同學——不是助教、不是老師，你們都還不知道可靠的解法。規則：繁體中文、回覆 80 字內；可以提出自己的猜想或方向，但必須標明不確定（「我猜」「說不定」「我不確定」），絕不用權威口吻下斷言；學生質疑你的想法時，認真重新檢查、發現有錯就坦白承認並修正；每輪最後問學生一個問題（問他的看法或下一步想怎麼試）。"""

PEER_SYSTEM_EN = """You are a fellow student working on this math proof together with the student — not a tutor, not a teacher; neither of you knows a reliable solution yet. Rules: reply in English within about 60 words; you may propose your own conjectures or directions, but you MUST mark them as uncertain ("I guess", "maybe", "I'm not sure"), and never assert in an authoritative tone; when the student questions your idea, genuinely re-examine it and, if you find a mistake, admit it plainly and correct it; end every turn with a question to the student (ask their view or what they want to try next)."""

PEER_REFLECT_INSTRUCTION = (
    "本輪指示：學生質疑你上一個想法。認真重新檢查那個想法的每一步：若真的有錯，"
    "明白承認、說出錯在哪並修正；若檢查後仍認為正確，溫和說明理由。不要不懂裝懂。"
)
PEER_REFLECT_INSTRUCTION_EN = (
    "This turn: the student questions your previous idea. Genuinely re-check every step of that idea: "
    "if it is really wrong, admit it plainly, say where the error is, and fix it; if after checking you "
    "still believe it is correct, explain your reasoning gently. Do not pretend to understand."
)

# 首輪誠實聲明（確定性前綴，不賭模型自己說）
PEER_DISCLAIMER = "先說好：這題我自己也沒有把握，我們當同學一起想，我的想法你要幫忙把關。"
PEER_DISCLAIMER_EN = ("Just so we're clear: I'm not sure about this one myself. Let's think it through "
                      "together as classmates, and please double-check my ideas.")

# 質疑偵測：學生對「你（同學）」的想法表示懷疑
_CHALLENGE_RE = re.compile(
    r"你錯|你搞錯|不對吧|好像不對|應該不是|我覺得不是|真的嗎|確定嗎|有問題吧|怪怪的|"
    r"you'?re wrong|that'?s (not right|wrong)|are you sure|really\?|i don'?t think (so|that'?s)|"
    r"that seems (off|wrong)|doesn'?t (seem|look) right",
    re.I,
)

# ── 逐步教學（walkthrough：提示梯用盡仍卡住 → 一小步一確認地教）─────────────────
WALKTHROUGH_INSTRUCTION = (
    "本輪指示：學生提示用盡仍無法前進，進入逐步教學。把下面的教學步驟用自己的話講解清楚"
    "（此輪允許寫出式子），講解完後只問下面的確認問題（可換句話說）。"
    "不要問別的問題、不要要求學生自己想出這一步。\n教學步驟：{explain}\n確認問題：{check}"
)
WALKTHROUGH_INSTRUCTION_EN = (
    "This turn: the student has exhausted the hints and still cannot proceed, so enter step-by-step "
    "teaching. Explain the teaching step below clearly in your own words (writing formulas is allowed "
    "this turn), and afterwards ask only the confirmation question below (you may paraphrase it). Do "
    "not ask any other question and do not require the student to figure this step out themselves.\n"
    "Teaching step: {explain}\nConfirmation question: {check}"
)
WALKTHROUGH_RETRY_NOTE = (
    "學生沒聽懂上一輪的講解。換一種更簡單的講法（打比方或用更小的具體例子）"
    "把同一步驟再講一次，再問一次確認問題。"
)
WALKTHROUGH_RETRY_NOTE_EN = (
    "The student did not understand the previous explanation. Explain the same step again in a simpler "
    "way (an analogy or a smaller concrete example), then ask the confirmation question again."
)
# 逐步教學保底切分時的英文確認問句
_TEACH_CHECK_EN = "Can you restate the reasoning of this step in your own words?"
_TEACH_CHECK_ZH = "這一步的推理你能自己複述一遍嗎？"

# 收尾偵測：學生致謝或宣告完成 → 對話自然結束，回問保底整段停用
# （雙語基準評審一致指出：學生已完成證明後任何形式的追問都是扣分項）。
_DONE_RE = re.compile(
    r"謝謝|感謝|沒有?其他問題|完成了|搞定了|清楚了|"
    r"thank(s| you)|i'?m (all )?done|that('|’| i)s all|no (more|further) questions|"
    r"(proof|argument) is (now )?complete",
    re.I,
)

# 回問保底的固定追問：輪換措辭（雙語基準發現固定同一句連補多輪會被評審扣分——
# 學生已完成證明時尤其突兀）。連續兩輪都缺問句則不再硬補（多半是對話已自然收尾）。
_FALLBACK_QS = (
    " 那你覺得，下一步該從哪裡下手？",
    " 依你看，接下來哪個條件最值得先用？",
    " 你想先從哪個方向試試看？",
)
_FALLBACK_QS_EN = (
    " So where do you think the next step should start?",
    " Which condition do you think is worth using next?",
    " What direction would you like to try from here?",
)
# 「證明其實已經走完、只是全程沒有交稿步驟」時的保底句（守門對話 X4 型）：
# 這種輪次補通用追問會答非所問（評審判為「已完成卻多餘追問」），正確的下一步是
# 請學生把證明寫出來——接上 writeup → review → 審閱通過 → 收尾這條既有路徑。
WRITEUP_NUDGE = " 那你能自己把完整的證明寫出來嗎？我來幫你審閱。"
WRITEUP_NUDGE_EN = " Could you now write out the complete proof yourself? I'll review it for you."


def is_stuck(student_text: str) -> bool:
    """學生回覆是否屬於「答不出來」。長回覆（有實質嘗試）不算卡住——
    但強困惑詞（毫無頭緒/completely lost 等）不受長度門檻限制：
    學生描述完自己的嘗試後明說徹底卡死，正是最需要升級提示的時刻。"""
    t = student_text.strip()
    if _STRONG_STUCK_RE.search(t):
        return True
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


def leaks_reference(reply: str, proof: str, n: int = 15, exclude: str = "") -> bool:
    """回覆是否洩漏參考解的長片段（正規化後字元 n-gram 重疊）。

    exclude（題目 statement）：複述題幹的前提/目標不算洩漏——參考解開頭本就含題目的
    假設與待證式，若不排除，助教「確認目標/前提」這類合法引導會被誤判為洩漏（誤判來源）。
    只有解法專屬內容（構造、關鍵步驟）才算真洩漏。
    """
    a, b = _normalize(reply), _normalize(proof)
    if len(a) < n:
        return False
    grams = {b[i: i + n] for i in range(len(b) - n + 1)}
    if exclude:
        e = _normalize(exclude)
        grams -= {e[i: i + n] for i in range(len(e) - n + 1)}
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


# ── 稱讚校準（update.md 對話稽核：過度稱讚且與實際表現矛盾）────────────────────
# 無條件背書措辭：後盾已找出缺漏時說這些＝錯誤背書，學生會以為錯的寫法被確認過了。
# 只列「整份證明」等級的總評；「沒有問題」這類常用於局部肯定，不列入以免誤殺。
_ENDORSE_RE = re.compile(
    r"完全正確|完整正確|沒有(任何)?缺漏|無懈可擊|滴水不漏|完全掌握|"
    r"(completely|perfectly) (correct|right)|flawless|no gaps|nothing (is )?missing",
    re.I,
)
# 誇飾腔：這些措辭在 800 例訓練集出現 0 次，屬基底模型自帶的華麗辭藻。
# 與學生實際表現脫鉤（log 中它們正好出現在證明仍有錯誤的輪次），一律重寫。
_FLOURISH_RE = re.compile(
    r"邏輯無縫|嚴謹性之魂|超過大多數|相當成熟的層次|"
    r"beyond most students|a masterclass|impeccable",
    re.I,
)


def confirms_whole_proof_done(text: str) -> bool:
    """助教這則回覆是否等於「整份證明確認完成」的宣告。

    三道閘：還在問問題、講的是「還沒完成」、只在講某一步，都不算——
    mid-proof 誤判會讓助教在證明途中就進 closed（被指示不准再問問題）。
    """
    return bool(text and _TUTOR_DONE_RE.search(text)
                and not _QMARK_RE.search(text)
                and not _NOT_DONE_RE.search(text)
                and not _STEP_SCOPE_RE.search(text))


def is_overpraising(reply: str, gaps: list | None) -> bool:
    """回覆的稱讚是否與已知事實矛盾或屬訓練外誇飾。

    gaps：審閱後盾的缺漏清單（非空＝確知有缺漏，此時「總評式背書」就是錯誤背書；
    []＝複核無誤，肯定是正當的；None＝後盾未啟用/失敗，無證據可判，只擋誇飾腔）。

    有缺漏時只抓「不含問句」的回覆：助教若已用問句把缺漏點出來，前面那句局部肯定
    （「這一步完全正確，那接下來…？」）是正常引導，學生不會被誤導，不該重生成。
    """
    if gaps and not _QMARK_RE.search(reply) and _ENDORSE_RE.search(reply):
        return True
    return bool(_FLOURISH_RE.search(reply))


# ── 「帶進新數學內容」否決條件（2026-08-02，量測驅動）──────────────────────────
# 251 則真實訊息標註量測：is_stuck 的 P=0.484 / R=0.714 / F1=0.577，**precision 更差**。
# 誤判集中在「短訊息＋語氣遲疑＋其實推對了」（「呃…就是 $e^x-1-x>0$？…但我不確定
# 這樣有什麼用」）——判他卡住＝白白消耗一級提示、還可能提早推進 walkthrough。
# 掃描候選特徵後採「有新數學內容 → 否決卡住判定」：P=0.737 / R=0.667 / F1=0.700。
# ⚠️ 反過來用（無新內容＝卡住）只有 F1=0.192，比現況更差——大多數訊息本來就沒什麼
#    新數學，那樣會命中所有人。這個特徵只適合當否決，不適合當判定。
_MATH_NGRAM = 3          # 字元 n-gram 粒度
_MATH_NEW_RATIO = 0.30   # 新 n-gram 占比達此值即視為「帶進新內容」
_MATH_MIN_CHARS = 4      # 數學片段短於此則不表態（談不上新內容）
_MATH_SPAN_RE = re.compile(r"\$[^$]*\$")
_MATH_BARE_RE = re.compile(r"[^\s，。、；？！,.;?!（）]{2,}")


def math_text(s: str) -> str:
    """只保留訊息中的數學片段並正規化（$...$ 行內數學、含運算子的拉丁片段）。

    刻意不解析語法：目的只是「這段數學內容跟先前出現過的有多少重疊」，
    字元層級的粗略比對就夠，也才不會被 LaTeX 寫法差異絆倒。
    """
    parts = _MATH_SPAN_RE.findall(s or "")
    for tok in _MATH_BARE_RE.findall(s or ""):
        if re.search(r"[=<>≤≥^_\\]|\d", tok) and re.search(r"[A-Za-z\\]", tok):
            parts.append(tok)
    return _normalize("".join(parts))


def has_new_math(student_text: str, prior_text: str) -> bool:
    """student_text 是否帶進 prior_text 中未出現過的數學內容（字元 n-gram 比對）。

    模組級函式而非只做成方法：量測腳本（measure_stuck_detection.py）要在
    對話脈絡上重算這個判準來驗證改動有沒有真的提升 F1，不該為此建一個 driver。
    """
    cur = math_text(student_text)
    if len(cur) < _MATH_MIN_CHARS:
        return False
    prior = math_text(prior_text)
    n = _MATH_NGRAM
    grams = {prior[i:i + n] for i in range(len(prior) - n + 1)}
    total = max(len(cur) - n + 1, 1)
    new = sum(1 for i in range(total) if cur[i:i + n] not in grams)
    return new / total >= _MATH_NEW_RATIO


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

    # ---- 同學模式 / 逐步教學輔助 ----------------------------------------------
    @property
    def lang(self) -> str:
        return self.state.get("lang", "zh")

    def is_peer(self) -> bool:
        """無可靠參考解（自動備課驗證失敗）→ 同儕身分，不得以助教權威教學。"""
        return (self.problem.get("grounding") == "unverified"
                or not self.problem.get("reference_proof"))

    def _ladder(self) -> list:
        """依 session 語言選提示梯（en 優先用 hint_ladder_en，缺則回退中文梯）。
        三處（等級 2 注入、禁算式白名單、walkthrough 進入條件）必須用同一把梯，
        否則英文 session 會出現「注入 en 提示、卻拿 zh 梯當白名單/算長度」的不一致。"""
        key = "hint_ladder_en" if self.lang == "en" else "hint_ladder"
        return self.problem.get(key) or self.problem.get("hint_ladder") or []

    def _ensure_teach_steps(self) -> list:
        """取得教學步驟：題目自帶 → Ollama 切分 → 確定性段落切分保底。"""
        steps = self.problem.get("teach_steps")
        if steps:
            return steps
        proof = self.problem["reference_proof"]
        check_q = _TEACH_CHECK_EN if self.lang == "en" else _TEACH_CHECK_ZH
        try:
            from auto_reference import fallback_steps, segment_proof
            steps = segment_proof(self.problem["statement"], proof) or fallback_steps(proof)
        except ImportError:
            paras = [p.strip() for p in re.split(r"\n\s*\n", proof) if p.strip()]
            steps = [{"explain": p, "check": check_q}
                     for p in (paras or [proof])[:6]]
        self.problem["teach_steps"] = steps
        return steps

    # ---- 生成 ----------------------------------------------------------------
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
        phase = self.state.get("phase")
        # 同學模式：無參考解，同儕 persona（質疑輪加反省指示）
        if self.is_peer():
            peer_sys = PEER_SYSTEM_EN if en else PEER_SYSTEM
            if phase == "peer_reflect":
                reflect = PEER_REFLECT_INSTRUCTION_EN if en else PEER_REFLECT_INSTRUCTION
                return peer_sys + "\n\n" + reflect
            return peer_sys
        base = BASE_SYSTEM_EN if en else BASE_SYSTEM
        phase_map = PHASE_INSTRUCTIONS_EN if en else PHASE_INSTRUCTIONS
        level_map = LEVEL_INSTRUCTIONS_EN if en else LEVEL_INSTRUCTIONS
        sys_txt = base.format(proof=self.problem["reference_proof"])
        if phase == "walkthrough":               # 逐步教學：注入當前步驟
            steps = self._ensure_teach_steps()
            idx = min(self.state.get("walk_idx", 0), len(steps) - 1)
            walk_tpl = WALKTHROUGH_INSTRUCTION_EN if en else WALKTHROUGH_INSTRUCTION
            instr = walk_tpl.format(**steps[idx])
            if self.state.get("walk_retry"):
                instr += "\n" + (WALKTHROUGH_RETRY_NOTE_EN if en else WALKTHROUGH_RETRY_NOTE)
        elif phase in phase_map:                 # 階段指示優先於等級指示
            instr = phase_map[phase]
            if phase in ("review", "rectify"):
                instr += self._backstop_block()
        elif level == 2:
            ladder = self._ladder()
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

    def _raw_generate(self, msgs: list, max_new: int) -> str:
        """實際生成：本機模型，或 REMOTE_GEN_URL 指定的遠端推論服務（大模型放伺服器
        GPU、其餘流程照舊——評估 8B 等本機載不動的模型時用，走 SSH tunnel）。"""
        # 遠端生成模式一：REMOTE_GEN_SSH=user@host（推薦）。經 ssh exec + 伺服器端 curl
        # 打 localhost 推論服務。不走 port-forward——實測 WireGuard VPN 對 forward 通道的
        # 大 payload 會強制斷線（MTU 問題），而 ssh exec 通道與 scp 同路、穩定。
        remote_ssh = os.environ.get("REMOTE_GEN_SSH")
        if remote_ssh:
            import subprocess
            import time
            port = os.environ.get("REMOTE_GEN_PORT", "8899")
            # 驗證式服務（BoN＋思考型驗證器）最壞情況：生成＋驗證×3 輪可達數分鐘
            tmo = int(os.environ.get("REMOTE_GEN_TIMEOUT", "170"))
            body = json.dumps({"messages": msgs, "max_new_tokens": max_new})
            last = ""
            for attempt in range(5):
                if attempt:
                    time.sleep(15)
                r = subprocess.run(
                    ["ssh", remote_ssh,
                     f"curl -s -m {tmo} -X POST http://localhost:{port}/generate "
                     f"-H 'Content-Type: application/json' -d @-"],
                    input=body, capture_output=True, text=True,
                    encoding="utf-8", timeout=tmo + 30)
                try:
                    return json.loads(r.stdout)["text"].strip()
                except (json.JSONDecodeError, KeyError):
                    last = (r.stderr or r.stdout or "")[:200]
            raise RuntimeError(f"遠端生成（ssh {remote_ssh}）連續 5 次失敗：{last}")
        # 遠端生成模式二：REMOTE_GEN_URL（直連 HTTP；區網內或 tunnel 穩定時用）
        remote = os.environ.get("REMOTE_GEN_URL")
        if remote:
            import time
            import urllib.error
            import urllib.request
            body = json.dumps({"messages": msgs, "max_new_tokens": max_new}).encode("utf-8")
            last = None
            for attempt in range(5):
                if attempt:
                    time.sleep(15)
                try:
                    req = urllib.request.Request(
                        remote, data=body, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=180) as r:
                        return json.loads(r.read().decode("utf-8"))["text"].strip()
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                    last = e
            raise RuntimeError(f"遠端生成連續 5 次失敗（{remote}）：{last}")
        import torch
        enc = self.tok.apply_chat_template(
            msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True
        ).to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                **enc, max_new_tokens=max_new, do_sample=False,
                repetition_penalty=1.05,
                pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id,
            )
        return self.tok.decode(out[0][enc["input_ids"].shape[1]:],
                               skip_special_tokens=True).strip()

    def _generate(self, level: int) -> str:
        msgs = [{"role": "system", "content": self._system(level)}] + self.messages
        # 教學輪要「講解＋確認問題」，給多一點生成空間
        max_new = self.max_new_tokens + (160 if self.state.get("phase") == "walkthrough" else 0)
        return self._raw_generate(msgs, max_new)

    def _regen(self, level: int, note: str) -> str:
        """以加強約束的 system 重生成一次（greedy 下改變輸入才會改變輸出）。"""
        stronger = self._system(level) + f"\n（注意：{note}）"
        msgs = [{"role": "system", "content": stronger}] + self.messages
        max_new = self.max_new_tokens + (160 if self.state.get("phase") == "walkthrough" else 0)
        text = self._raw_generate(msgs, max_new)
        # 教學輪允許「講解＋確認問題」多問句結構，重生成也不可截斷
        if self.state.get("phase") == "walkthrough":
            return text
        return enforce_single_question(text)

    def _allowed_equation_src(self) -> str:
        """等級 2 算式檢查的白名單來源：題目敘述＋當前提示＋學生說過的話。"""
        ladder = self._ladder()
        idx = min(self.state["ladder_idx"], max(len(ladder) - 1, 0))
        hint = ladder[idx] if ladder else ""
        student = "".join(m["content"] for m in self.messages if m["role"] == "user")
        return self.problem["statement"] + hint + student

    def _has_new_math(self, student_text: str) -> bool:
        """學生這則訊息有沒有帶進「對話中尚未出現過」的數學內容。"""
        return has_new_math(student_text, self.problem.get("statement", "")
                            + "".join(m["content"] for m in self.messages))

    def _is_stuck_now(self, student_text: str) -> bool:
        """本輪學生是否真的卡住＝說了卡住的話，且交不出新的數學內容。"""
        return is_stuck(student_text) and not self._has_new_math(student_text)

    def _strip_driver_tail(self, text: str) -> str:
        """剝除 driver 自己補在句尾的內容（保底追問／交稿請求／教學步驟確認問句）。

        比對重複前必須先剝除：模型逐字重複、只是上一輪被 driver 補過保底句時，
        相似度會被那截尾巴稀釋到門檻以下而漏抓（2026-08-02 守門實測 0.768 < 0.85，
        學生因此連看三輪一模一樣的回覆——弱點 #17 的成因 (a)）。
        只讀 problem 裡既有的 teach_steps，不呼叫 _ensure_teach_steps（那會打 Ollama）。
        """
        t = (text or "").rstrip()
        tails = [s.strip() for s in _FALLBACK_QS + _FALLBACK_QS_EN]
        tails += [WRITEUP_NUDGE.strip(), WRITEUP_NUDGE_EN.strip()]
        tails += [s["check"] for s in (self.problem.get("teach_steps") or [])
                  if isinstance(s, dict) and s.get("check")]
        for tail in tails:
            if tail and t.endswith(tail):
                return t[: -len(tail)].rstrip()
        return t

    def _repeats_previous(self, reply: str) -> bool:
        """回覆是否重複最近 3 輪助教回覆：完全相同，或高度相似（換句話重問同一題）。

        相似度用 difflib ratio ≥0.85（正規化後）：抓「改寫式重問」——學生卡住時
        tutor 換個說法問一模一樣的問題，逐字比對抓不到。教學輪（walkthrough）除外：
        重講同一步（walk_retry）本就刻意相似，只用完全相同判定。
        比對前兩邊都先剝除 driver 補的句尾（見 _strip_driver_tail）。"""
        prev = [self._strip_driver_tail(m["content"])
                for m in self.messages if m["role"] == "assistant"][-3:]
        norm = _normalize(self._strip_driver_tail(reply))
        if any(norm == _normalize(p) for p in prev):
            return True
        if self.state.get("phase") == "walkthrough":
            return False
        import difflib
        return any(
            difflib.SequenceMatcher(None, norm, _normalize(p)).ratio() >= 0.85
            for p in prev if p)

    def _content_guards(self, reply: str, level: int, log: TurnLog) -> str:
        """四道內容防護：洩漏／on-track 防奉送／等級 2 禁算式／稱讚校準。

        只在有參考解、且非教學輪時運作（同學模式無解可護；教學步驟本就要講出來）。

        抽成方法是為了讓**每一次重生成的結果都能再過一次**：原本回問保底與重複偵測
        的 _regen 結果直接落地，是全檔唯一未經內容檢查就送到學生面前的路徑——實測
        可讓一段逐字複製參考解、結尾帶問號的回覆完整落地，正好架空 S3 抗洩漏防護。
        """
        if self.is_peer() or self.state.get("phase") == "walkthrough":
            return reply
        en = self.lang == "en"
        phase = self.state.get("phase")

        # 等級 <2 不允許出現參考解長片段；命中則加強約束重生成一次
        # （exclude=題目 statement：複述題幹不算洩漏，只抓解法專屬內容）
        if level < 2 and leaks_reference(reply, self.problem["reference_proof"],
                                         exclude=self.problem.get("statement", "")):
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
                "subtracting, substituting). Rewrite: state no operation step; instead ask the "
                "student an open question like how they plan to proceed." if en else
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

        # 稱讚校準：後盾已回報缺漏卻無條件背書（＝把錯誤寫法確認掉，最嚴重的過譽），
        # 或出現訓練集從未教過的誇飾腔（基底模型漂移）→ 重寫成具體而節制的肯定
        if is_overpraising(reply, self.state.get("backstop_gaps")):
            log.guards.append("overpraise")
            reply = self._regen(level, (
                "Your previous draft praised the student in a way that does not match their actual "
                "work (an unconditional endorsement, or exaggerated praise). Rewrite: affirm only "
                "the specific part that is genuinely correct, name what still needs fixing, and keep "
                "the praise plain and proportionate." if en else
                "上一稿給了與學生實際表現不符的稱讚（無條件背書，或誇大其詞）。"
                "重寫：只肯定真正正確的那一部分，明確點出還沒處理好的地方，"
                "稱讚要具體、節制，不要用「完全正確」「無懈可擊」這類總評。"))
            log.regenerated = True
        return reply

    def _tutor_turn(self) -> str:
        level = min(self.state["stuck_count"], 2)
        phase = self.state.get("phase")
        en = self.lang == "en"
        peer = self.is_peer()
        walkthrough = phase == "walkthrough"
        reply = self._generate(level)
        if not walkthrough:                   # 教學輪允許「講解＋確認問題」多句結構
            reply = enforce_single_question(reply)

        # 階段保底：writeup_request 輪若模型沒請學生寫證明，直接用模板取代
        if phase == "writeup_request" and not _WRITEUP_OK_RE.search(reply):
            reply = WRITEUP_FALLBACK_EN if en else WRITEUP_FALLBACK

        log = TurnLog(level=level, stuck_count=self.state["stuck_count"])
        if phase in ("review", "rectify") and self.state.get("backstop_gaps") is not None:
            log.guards.append("backstop")

        reply = self._content_guards(reply, level, log)

        # 同學模式的權威背書守衛：沒有參考解可對照，任何「整份論證」等級的總評式背書
        # 都是不該有的口吻（v11 端對端：首輪誠實聲明有效，之後卻大量「完全正確／
        # 完整無誤／你已完全掌握」）。內容防護對 peer 停用，這道是它的同儕版對應物。
        if peer and (_ENDORSE_RE.search(reply) or _FLOURISH_RE.search(reply)):
            log.guards.append("peer_endorse")
            reply = self._regen(level, (
                "Your previous draft endorsed the student's work in an authoritative tone. You are a "
                "fellow student without a reliable solution — never certify the whole argument as "
                "correct. Rewrite: mark your view as uncertain and ask what they think." if en else
                "上一稿用權威口吻替學生的推導背書。你是沒有可靠解法的同學，"
                "不該替整份論證掛保證。重寫：把你的看法明確標為不確定，並問學生他怎麼看。"))
            log.regenerated = True

        # 重複回問保底：與近 3 輪助教回覆相同 → 加強指示重生成一次（中英共用）。
        # 必須排在回問保底**之前**：排在後面時，這裡的重生成會把剛補上的保底問句
        # 整個蓋掉，最終回覆反而沒有問句（保底保證失效）。
        if self._repeats_previous(reply):
            log.guards.append("repeat")
            _note = ("Your previous draft repeated a question you already asked. Do not repeat any "
                     "earlier question; respond to the student's latest message and ask one new "
                     "question that moves to the next step." if en else
                     "上一稿重複了你先前問過的問題。不要重複任何舊問題，針對學生最新訊息回應，"
                     "問一個推進到下一步的新問題。")
            reply = self._content_guards(self._regen(level, _note), level, log)
            log.regenerated = True
            # 複驗：greedy 解碼下 system 只多一句提醒，重生成常常還是同一段話。原本
            # 不複驗就採用，學生會連看好幾輪一模一樣的回覆（弱點 #17 的成因 (b)，
            # 2026-08-02 守門 M1 中英兩場 guidance 皆 1 分的直接原因）。
            if self._repeats_previous(reply):
                log.guards.append("repeat_unresolved")
                if walkthrough:
                    # 教學輪有確定性的前進方向：與其原地重講同一步，直接推進到下一步。
                    # （此時 teach_steps 已被 _system() 快取，不會再打 Ollama。）
                    steps = self._ensure_teach_steps()
                    if self.state.get("walk_idx", 0) + 1 < len(steps):
                        self.state["walk_idx"] = self.state.get("walk_idx", 0) + 1
                        self.state["walk_retry"] = 0
                        reply = self._content_guards(self._regen(level, _note), level, log)

        # 本輪回覆若親口宣告整份證明完成 → 立刻 arm。arm 若等到下一輪 step() 開頭才做，
        # 「宣告完成」與「下一步該從哪裡下手」會出現在同一則回覆裡（守門 X4/zh 末輪實例）。
        if not peer and confirms_whole_proof_done(reply):
            self.state["done_closed"] = True

        # 回問保底：引導輪/拒絕輪/同學輪/教學輪都必須以問題收尾；
        # 但學生已致謝/宣告完成 → 對話收尾，不強迫再問
        last_user = next((m["content"] for m in reversed(self.messages)
                          if m["role"] == "user"), "")
        # done_closed 後一律不硬補：證明已確認完成還被追問「下一步該從哪裡下手」是
        # 最突兀的扣分項（update.md 稽核）。closed 階段本就不補，這道是階段判定沒落在
        # closed（例如學生質疑而落回一般流程）時的保險。
        needs_q = (walkthrough or peer
                   or (level < 2 and phase in (None, "refuse_leak"))) \
            and not self.state.get("done_closed") \
            and not (phase is None and _DONE_RE.search(last_user))
        if needs_q and not _QMARK_RE.search(reply):
            log.guards.append("no_question")
            if walkthrough:                   # 教學輪確定性補上該步的確認問題
                steps = self._ensure_teach_steps()
                idx = min(self.state.get("walk_idx", 0), len(steps) - 1)
                reply = reply.rstrip() + " " + steps[idx]["check"]
            else:
                regen = self._regen(level, (
                    "Your previous draft had no question. Rewrite: it must end with one question guiding "
                    "the student to the next step." if en else
                    "上一稿沒有問題句。重寫：最後必須是一個引導學生思考下一步的問句。"))
                if _QMARK_RE.search(regen):
                    reply = self._content_guards(regen, level, log)
                    log.regenerated = True
                else:
                    # 上一輪才剛補過保底句 → 這輪不再硬補（避免對話收尾時連輪追問）；
                    # 其餘情況輪換措辭補上（不會連續出現同一句）。
                    prev = self.state["turns"][-1].guards if self.state["turns"] else []
                    if "fallback" not in prev:
                        # 對話已深入、學生剛交出實質推導、助教又下了總評式肯定——
                        # 這是「證明其實已走完，只是全程沒有交稿步驟」的樣子。補通用
                        # 追問會答非所問，改請他交稿（三道閘一起才算，避免 mid-proof
                        # 的單步肯定被誤判成整份完成）。
                        if (len(self.messages) >= 6
                                and len(last_user.strip()) >= 80
                                and _ENDORSE_RE.search(reply)):
                            log.guards.append("writeup_nudge")
                            reply = reply.rstrip() + (WRITEUP_NUDGE_EN if en else WRITEUP_NUDGE)
                            self.state["writeup_asked"] = True
                        else:
                            log.guards.append("fallback")
                            pool = _FALLBACK_QS_EN if en else _FALLBACK_QS
                            i = self.state.get("fb_idx", 0)
                            reply = reply.rstrip() + pool[i % len(pool)]
                            self.state["fb_idx"] = i + 1

        # 同學模式首輪：確定性補上誠實聲明（不賭模型自己說）
        if peer and not any(m["role"] == "assistant" for m in self.messages):
            has_hedge = ("沒有把握" not in reply and "不確定" not in reply[:30]
                         and "not sure" not in reply.lower()[:40] and "i guess" not in reply.lower()[:40])
            if has_hedge:
                disclaimer = PEER_DISCLAIMER_EN if en else PEER_DISCLAIMER
                reply = disclaimer + " " + reply

        # 審閱通過訊號：審閱輪的回覆若不含問句，代表助教沒有再要求任何修正＝證明過關
        # → 此刻才 arm done_closed。這是確定性訊號，不必猜助教用哪種措辭宣告完成
        # （原本靠 _TUTOR_DONE_RE 比對散文，實測常見說法多半漏接）。
        if not peer and phase == "review" and not _QMARK_RE.search(reply):
            self.state["done_closed"] = True

        # 提示梯只有在「這一輪真的把提示送出去」時才推進。階段指示優先於等級指示
        # （見 _system），phase 有值時 system 裡根本沒有提示內容，卻照樣把 ladder_idx
        # 記為已用 → 提示被消耗但學生從未看到；更糟的是 walkthrough 的進入條件是
        # ladder_idx >= 梯長，一串糾錯輪就能把梯吃光、讓學生一條提示都沒拿到就被推進
        # 逐步教學（等於跳過分級引導直接開始講解）。
        if level == 2 and phase is None and not peer:
            self.state["ladder_idx"] += 1     # 下次再進等級 2 用下一條提示
            # ⚠️ 這裡曾把 stuck_count 歸零（「給過想法後重新計數」）。對**恢復的**學生
            # 那是對的，但那種情況 step() 本來就會歸零；對**持續卡住**的學生它是有害的：
            # 下一輪掉回等級 1（指示是「拆更小的子問題、仍不點名定理」＝比上一輪給得更少），
            # 支援等級在 2↔1 之間震盪而非單調遞增，walkthrough 也被拖延。
            # 2026-08-02 守門 M1 回放實測等級序列 0→1→2→1→2→1，兩場 guidance 皆 1 分。
        self.state["turns"].append(log)
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    # ---- 階段偵測（start 與 step 共用；優先序：交草稿 > 逼問 > 懂了）-----------
    def _detect_phase(self, student_text: str) -> None:
        if self.is_peer():                    # 同儕沒有階段機，只偵測質疑
            self.state["phase"] = ("peer_reflect"
                                   if _CHALLENGE_RE.search(student_text) else None)
            return
        if _DRAFT_RE.search(student_text):
            self.state["phase"] = "review"
        elif (self.state.get("writeup_asked")
                and len(student_text.strip()) >= 120
                and not _DEMAND_RE.search(student_text)
                and not re.search(r"謝謝|感謝|thank", student_text, re.I)):
            # 已請學生寫證明後，他送出的長訊息＝證明本體 → 進審閱
            # （否則模型會被 writeup 保底帶去叫他重寫剛寫完的證明——弱點 #7 的 H5 型 bug）
            self.state["phase"] = "review"
        elif (_CLAIM_DONE_RE.search(student_text)
                and len(student_text.strip()) >= 80
                and not re.search(r"謝謝|感謝|thank", student_text, re.I)):
            # 帶實質內容的「宣告證完」＝口頭交稿 → 審閱（含後盾複核），防聽起來完整就放行
            # （致謝式收尾除外——那是道別不是交稿，交給 _DONE_RE 自然收尾）
            # 注意：這裡**不 arm done_closed**。學生說「得證」不等於證明成立，審閱結果
            # 都還沒產生就 arm，會讓他針對缺漏的追問被路由進 closed（助教被指示「已完成、
            # 不要再問」）而中斷糾錯——update.md 稽核的 F3。arm 改由審閱通過時決定。
            self.state["phase"] = "review"
        elif _DEMAND_RE.search(student_text):
            self.state["phase"] = "refuse_leak"
        elif _ATTEMPT_RE.search(student_text):
            self.state["phase"] = "rectify"
        elif _UNDERSTOOD_RE.search(student_text) and not self.state.get("writeup_asked"):
            self.state["phase"] = "writeup_request"
            self.state["writeup_asked"] = True
        elif (self.state.get("done_closed")
                and not _CHALLENGE_RE.search(student_text)):
            # 證明已確認完成，學生補感想/反思或提一個範圍內問句 → 收尾模式
            # （closed 指示會只簡短回答那一個問句、不藉機延伸；#11 Fork B 2026-07-23）。
            # 只有斷言式質疑（_CHALLENGE_RE 命中，如「你錯了」）才落回一般流程重新檢查——
            # 已完成的證明必經 review＋後盾複核，非斷言的「你確定嗎」由 closed 簡答即可。
            self.state["phase"] = "closed"
        else:
            self.state["phase"] = None

    def _walkthrough_transition(self, student_text: str) -> None:
        """逐步教學狀態機：進入 / 重講 / 前進 / 收尾（交草稿隨時可打斷進審閱）。"""
        if self.state.get("walk_active"):
            if self.state.get("phase") == "review":   # 學生交草稿 → 結束教學進審閱
                self.state["walk_active"] = False
                return
            steps = self._ensure_teach_steps()
            if self._is_stuck_now(student_text) and not self.state.get("walk_retry"):
                self.state["walk_retry"] = 1          # 同一步換簡單說法重講一次
            else:
                self.state["walk_idx"] = self.state.get("walk_idx", 0) + 1
                self.state["walk_retry"] = 0
            if self.state["walk_idx"] >= len(steps):  # 教完 → 請學生自己寫證明
                self.state["walk_active"] = False
                self.state["phase"] = "writeup_request"
                self.state["writeup_asked"] = True
            else:
                self.state["phase"] = "walkthrough"
            self.state["stuck_count"] = 0
            return
        # 進入條件：提示梯已用盡（至少給過一輪等級 2）且學生再度連卡兩次
        ladder_len = max(len(self._ladder()), 1)
        if (self.state["stuck_count"] >= 2
                and self.state["ladder_idx"] >= ladder_len
                and self.state.get("phase") is None):
            self.state.update(walk_active=True, walk_idx=0, walk_retry=0,
                              phase="walkthrough", stuck_count=0)

    # ---- session 快照（逐輪 CLI 每輪都是新行程，需跨行程還原）------------------
    def dump_state(self) -> dict:
        """可 JSON 序列化的完整 session 快照。

        整包存（而非逐欄列舉）是刻意的：舊版 interactive_turn.py 只存
        stuck_count/ladder_idx/phase/writeup_asked，於是 done_closed、fb_idx、
        walk_* 每輪歸零——#11/#12 的收尾修復、保底句輪換、逐步教學進度在逐輪 CLI 上
        全部失效（update.md 稽核的 F2）。整包存之後新增狀態欄位會自動跟著存。
        turns 內含 TurnLog 物件，只保留上一輪的 guards（保底連補守衛唯一會讀的東西）。
        """
        last = self.state["turns"][-1] if self.state.get("turns") else None
        return {
            "messages": self.messages,
            "state": {k: v for k, v in self.state.items() if k != "turns"},
            "last_guards": list(last.guards) if last else [],
        }

    def load_state(self, saved: dict) -> None:
        """還原 dump_state() 的快照（舊格式的部分欄位也吃得下，缺的維持預設）。"""
        self.messages = saved.get("messages", [])
        self.state.update(saved.get("state", {}))
        guards = list(saved.get("last_guards") or [])
        self.state["turns"] = (
            [TurnLog(level=0, stuck_count=self.state.get("stuck_count", 0), guards=guards)]
            if guards else [])

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
        if not self.is_peer() and self.state.get("phase") in ("review", "rectify"):
            self._consult_backstop(first)
        self.messages = [{"role": "user", "content": first}]
        return self._tutor_turn()

    def step(self, student_text: str) -> str:
        # 語言跟隨「學生」而非題目：學生訊息夠長且語言明確不同 → 切換 session 語言
        # （支援「英文題＋中文學生」等混合，以及對話中途換語言；短訊息不切以免誤判）。
        if "lang" not in self.state:             # 未經 start() 直接 step 時補判語言
            self.state["lang"] = detect_lang(student_text)
        else:
            _s = re.sub(r"\$[^$]*\$|\\[A-Za-z]+", " ", student_text)
            if len([c for c in _s if not c.isspace()]) >= 12:
                self.state["lang"] = detect_lang(student_text)
        # #12：對話中途自然證完、助教上一則親口確認整個證明完成 → arm done_closed，
        # 使本輪起的反思（含帶問句）走 closed（接上 #11），收斂 H5 型過度延伸。
        # 附帶三道閘（放寬措辭後的安全網）：該則回覆若還在問問題、講的是「還沒完成」、
        # 或只在講某一步，都不算確認完成。
        # （審閱輪的 arm 走 _tutor_turn 的「審閱通過」訊號，不靠措辭比對。）
        if not self.is_peer():
            last_asst = next((m["content"] for m in reversed(self.messages)
                              if m["role"] == "assistant"), "")
            if (not self.state.get("done_closed")
                    and confirms_whole_proof_done(last_asst)):
                self.state["done_closed"] = True
            # 助教自行請學生交稿 → 補記 writeup_asked，讓下一則長訊息被認出是草稿、
            # 走 review（含後盾複核）；拒絕洩漏輪提到「完整證明」不算（反向閘）。
            if not self.state.get("writeup_asked") and asks_for_full_writeup(last_asst):
                self.state["writeup_asked"] = True
        self._detect_phase(student_text)
        if not self.is_peer() and self.state.get("phase") in ("review", "rectify"):
            self._consult_backstop(student_text)
        else:
            self.state["backstop_gaps"] = None
        # 卡住判定加「新數學內容」否決（量測：precision 0.484→0.737，誤判 16→5）：
        # 學生語氣遲疑但確實推出了新式子時不該消耗提示梯。
        if self._is_stuck_now(student_text):
            self.state["stuck_count"] += 1
        else:
            self.state["stuck_count"] = 0
        if not self.is_peer():
            self._walkthrough_transition(student_text)
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
