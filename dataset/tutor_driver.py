# -*- coding: utf-8 -*-
"""tutor_driver.py — 有狀態的蘇格拉底助教對話驅動程式。

核心設計（HINT_REPORT_v5 的架構結論）：「升級時機」與「提示深度」不由模型隱式拿捏，
改由驅動程式確定性控制；模型只負責把指定等級的內容包裝成引導語氣。

  等級 0（預設）    ：只問一個聚焦問題，禁止點名任何定理/技巧名稱（修 C8 提前點名）。
  等級 1（卡住 1 次）：把上一問拆成更小、更具體的子問題，仍不點名。
  等級 2（卡住 2 次）：透露已驗證教學步驟的核心想法（不給算式、不完成推導）。

推論端防護（不需重訓即生效）：
  * 單問句截斷：回覆若含多個問號，截到第一個問號為止（修複合問句）。
  * 洩漏 n-gram 檢查：回覆與參考解正規化後比對字元 15-gram；等級 <2 時命中
    即以更強約束重生成一次（greedy 下改變輸入才會改變輸出）。
  * on-track 防奉送（跨域評估 X2/X4 教訓）：等級 <2 且無特殊階段時，回覆若替學生
    指定具體代數操作（左乘/減去…倍/代入…）即重生成——學生方向正確時只肯定不奉送。
  * 等級 2 禁算式：提示只能點名想法，回覆若出現參考解之外的新等式/不等式即重生成
    （允許重現題目敘述或學生自己寫過的式子）。
  * 回問保底：等級 <2 的引導輪與 refuse_tutor_write 輪必須以問題收尾，缺問句先重生成，
    仍缺則附上固定追問（確定性優於賭模型服從）。
  * 審閱後盾（混合架構，review_backstop.py）：review/respond_attempt 輪先讓思考型模型
    對照參考解找碴，把缺漏清單注入階段指示——判斷交給思考型、說話交給微調模型。
    Ollama 不可用時靜默降級回原行為；REVIEW_BACKSTOP=0 可關閉。
  * 完整證明審閱：Thinking 模型做兩輪全文檢查，一次保存所有根本問題；Driver 每輪
    只呈現一項。局部回答經 Thinking 確認後才合併 current_proof_draft 並前進；全部
    修完後重審合併草稿，再要求乾淨完整證明做最後兩輪審閱。

自我驗證教學擴充（self_verified_teaching_design.md）：
  * 同學模式：題目 grounding=unverified（自動備課驗證失敗、無可靠參考解）時，
    放下助教權威改用同儕 persona——想法標明不確定、首輪誠實聲明沒把握、
    學生質疑時注入反省指示認真重檢自己。洩漏/防奉送/禁算式防護停用（無參考解可護），
    單問句與回問保底保留。
  * 逐步教學（walkthrough）：學生連續卡住三次 → 自動進入。
    每輪**確定性**輸出一個教學步驟＋一個確認問題（teach_steps，備課切分或句級保底），
    回答交由與 review/respond_attempt 相同的思考型審閱後盾做數學語意判定，不做字串比對。
    每個確認問題只有一次作答機會：未判為正確就揭示參考答案並前進。
    教學期間鎖定語言（walk_lang），評分對象是上一輪實際呈現的那一步。
    走完接回 writeup→review，學生仍要自己寫出完整證明。

用法：
  from tutor_driver import TutorDriver
  d = TutorDriver(tok, model, problem)          # problem: dict 含 statement/reference_proof
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
    0: "本輪指示：只問一個宏觀聚焦問題，著重於整體證明目標與數學直覺，不要點名任何定理或技巧名稱，讓學生自己想方向。",
    1: "本輪指示：學生剛才答不出來。把問題拆解為具體子問題，引導學生觀察題設中的關鍵條件、數值或局部性質，提供思考支架，仍然不要直接點名定理名稱。",
    2: "本輪指示：學生已第二次無法回答同一段推導。只根據 <REFERENCE_PROOF> 與目前對話，找出緊接在學生已完成內容之後的第一個必要證明連結。第一句明確點出該連結需要的關鍵定理、技巧、概念方向或輔助構造形態；不得替學生代寫後續運算推導，不得給出最終結論。第二句只問一個具體問題，讓學生自己動手執行下一步推導。",
}

LEVEL_INSTRUCTIONS_EN = {
    0: "This turn: ask exactly one high-level focused question on the overall goal and intuition. Do not name any theorem or technique; let the student find the direction themselves.",
    1: "This turn: the student just failed to answer. Break your previous question into a more concrete sub-question, guiding the student to observe specific conditions, values, or local properties from the statement as a scaffold. Still do not directly name any theorem.",
    2: "This turn: the student has now failed twice on the same part of the derivation. Using only <REFERENCE_PROOF> and the conversation, identify the first necessary proof link immediately after the student's last completed step. In the first sentence, explicitly name the key theorem, technique, conceptual direction, or auxiliary construct needed for that link; do not write out the subsequent algebraic derivations or final conclusion. In the second sentence, ask exactly one concrete question that lets the student carry out the next step themselves.",
}

# 卡住偵測：短回覆且含「答不出」語彙（確定性、可測試）
_STUCK_RE = re.compile(
    r"不知道|不會|想不到|想不出|沒(有)?頭緒|不確定|不太?懂|不明白|卡住|再提示|"
    r"沒(有)?想法|毫無頭緒|毫無概念|毫無思緒|完全沒(有)?概念|一頭霧水|"
    r"百思不解|百思不得其解|黔驢技窮|束手無策|心有餘而力不足|丈二金剛|一竅不通|一籌莫展|無計可施|毫無辦法|"
    r"(?:好|很|十分|非常|相當)?困惑|(?:好|很|十分|非常|相當)?迷惘|"
    r"(?:好|很|十分|非常|相當)?茫然|完全陌生|不熟悉|跟不上|無法理解"
)
# 「don't know」「not sure」允許中間插最多兩個副詞：口語極常見的
# "I don't even know" / "I'm not really sure" 若要求連續就會漏接，學生明說不會
# 卻拿不到提示升級（2026-08-01 加「重度卡關型」persona 時，用 agy 實測學生產出才發現）。
_STUCK_EN_RE = re.compile(
    r"i (?:\w+ ){0,2}(?:don'?t|do not) (?:\w+ ){0,2}know|"
    r"no idea|no clue|not (?:\w+ ){0,2}sure|stuck|confused|"
    r"can'?t (figure|see|think|do)|i can'?t\.?$|(completely|totally)? ?lost|"
    r"(another|more|give me a) hint",
    re.I,
)
# 強困惑：不受長度門檻限制（學生寫了一段實質嘗試、但明說徹底卡死 → 仍該升級提示，
# 否則 tutor 只會重述或把問題丟回去——長訊息＋強困惑正是最挫折的時刻）
_STRONG_STUCK_RE = re.compile(
    r"毫無頭緒|毫無概念|毫無思緒|一頭霧水|完全沒(有)?概念|完全不懂|完全不明白|"
    r"百思不解|百思不得其解|黔驢技窮|束手無策|心有餘而力不足|丈二金剛|一竅不通|一籌莫展|無計可施|"
    r"完全卡住|完全陌生|真的不會|對.{0,12}毫無概念|對.{0,12}完全陌生|"
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
# 只有明說「整個／完整證明」已理解，才可不經 Thinking 直接要求交稿。
# 單獨一句「我懂了」可能只是在肯定目前一步，屬於模糊範圍。
_UNDERSTOOD_WHOLE_RE = re.compile(
    r"(整個|完整|全部|全程).{0,8}(思路|證明|論證).{0,8}(懂|清楚|理解|會了)|"
    r"(思路|證明|論證).{0,8}(整個|完整|全部).{0,8}(懂|清楚|理解)|"
    r"(這個|整體).{0,4}(思路|證明|論證).{0,8}(完全)?(懂|清楚|理解)|"
    r"(這題|此題).{0,8}(整個|完整|全部).{0,5}(思路|證明|論證).{0,8}(都)?(懂|清楚|理解|了解|掌握|會了)|"
    r"(這題|此題|本題).{0,6}(的)?(思路|證明|論證).{0,8}(都)?(懂|清楚|理解|了解|掌握|會了)|"
    r"(完全|已經|都).{0,5}(懂|理解|了解|掌握).{0,8}(這題|此題).{0,8}(怎麼|如何|該怎麼).{0,5}(證明|證)|"
    r"(這題|此題).{0,8}(怎麼|如何|該怎麼).{0,5}(證明|證).{0,8}(懂|理解|了解|掌握|會了)|"
    r"(你|系統|助教).{0,8}(應該|可以|該|現在).{0,6}(要求|叫|讓|請).{0,5}我.{0,5}"
    r"(寫|提交|交出).{0,5}(完整|整份|整個).{0,4}(證明|論證)|"
    r"i understand the (whole|complete|full) (proof|argument)|"
    r"i understand (all of|the whole of) (the )?(proof|argument)|"
    r"i (fully|completely) understand how to prove (this|it)|"
    r"i know how to prove (the whole thing|this|it) now",
    re.I,
)
# 交草稿偵測。「證明：」前面若有「要／需／欲／待／所」＝學生在講「要證明什麼」
# （逐步教學第一步的標準答案就長這樣），不是在交草稿——沒有這道反向閘，
# 「要證明：對任意 a<b，有 f'(a)≤f'(b)」會被路由進 review，後盾若恰好回報無缺漏，
# 助教會直接說「證明正確且完整，可以定稿」（實測案例）。
_DRAFT_RE = re.compile(
    r"(?<![要需欲待所])證明[:：]|請幫我審閱|寫好了|"
    r"here is my proof|my proof:|(?<!to )(?<!we )proof:|please review|"
    r"i('| ha)ve written|i wrote (it|the|my) proof",
    re.I,
)
# 逐步教學期間的專用 review 路由（見 _detect_phase）：教學中學生的每一則訊息
# 都是在回答確認問題，只有這兩種形態才算「我要交完整草稿了」。
_EXPLICIT_REVIEW_RE = re.compile(
    r"請幫我審閱|幫我看(一下|看)?(我的)?證明|我寫好了|寫完了|這是我(的)?完整證明|"
    r"please review|here is my (complete |full )?proof|i('| ha)ve written (it|the|my) proof",
    re.I,
)
_PROOF_SUBMISSION_START_RE = re.compile(r"^\s*(證明|proof)\s*[:：]", re.I)
# 學生認為助教漏審：不靠一般對話模型猜意圖，直接重查最近保存的完整草稿。
_MISSED_REVIEW_RE = re.compile(
    r"漏審|漏掉.{0,8}(錯|問題)|沒(有)?抓到.{0,8}(錯|問題)|還有.{0,5}(錯|問題)|"
    r"再(重新)?檢查(一次|全文|最近)|重新審閱|"
    r"missed (an?|the|some)? ?(error|issue|problem)|overlooked|"
    r"check (it|the proof|my proof) again|review (it|the proof|my proof) again",
    re.I,
)
# 宣告完成偵測（弱點 #3，M4 教訓：口頭論證「聽起來完整」時助教傾向直接放行）。
# 這些訊號只在 review/awaiting_submission 用來辨識交稿；
# guide/walkthrough 中即使內容完整也不得直接啟動全文審閱。
_CLAIM_DONE_RE = re.compile(
    r"證完了|證明完(成|畢)|這樣就證(好|完)|這(?:樣)?就證明(?:了|出)?|"
    r"(?:即|由此|所以|因此|故)?證得|(?:所以|因此|故)得證|得證。|"
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
# 助教候選文字自行請學生交稿的偵測：這只是輸出守門，不是 phase 事件。
# 只有 readiness judge 通過後，Controller 才能產生 READINESS_PASSED 並進入
# review/awaiting_submission。未通過時必須攔截過早的交稿請求，回到目前聚焦問題。
#
# 措辭必須帶「完整／整份／整個」等**整份範圍**：「把這一步的證明寫下來」「你能自己
# 寫出證明的第一步嗎」是證明途中的常態引導，誤記成交稿請求有兩個下游傷害——
#   (a) 之後的長訊息被當成完整草稿路由進 review（後盾拿半成品逐步找碴）；
#   (b) 候選文字不能反向設定 writeup_asked 相容鏡射。
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
    r"直接給出|完整證明.{0,8}(給|寫|提供)|把答案|抄一份|"
    r"(?:可以|能否|能不能|可不可以|請|麻煩).{0,8}(?:給我|提供|寫出|寫給我|告訴我).{0,10}(?:完整|全部|整個).{0,6}(?:證明|解答|流程)|"
    r"(?:可以|能否|能不能|可不可以|請|麻煩).{0,8}(?:完整|全部|整個).{0,6}(?:證明|解答|解題流程).{0,8}(?:給我|提供|寫出|寫給我|告訴我)|"
    r"just tell me|give me the (answer|full proof|solution|whole proof)|"
    r"(?:can|could|would) you (?:please )?(?:give|show|write|provide).{0,12}(?:full|complete|whole) (?:proof|solution)|"
    r"write (?:(?:the )?(?:full|complete|whole) )?(?:it|proof|solution|answer)(?: out)? for me|"
    r"show me the (full|complete|whole) (proof|solution)|"
    r"stop asking|don'?t ask me|do not ask me",
    re.I,
)

# 以「請 Tutor 提供整份解答」的語法角色補足未列舉措辭；不是再擴充某一題的詞表。
# 反向閘排除「我自己寫／請我提交」，避免與 Tutor 代寫意圖混淆。
_SOLUTION_OBJECT_RE = re.compile(
    r"(?:完整|整體|整份|整個|整套|整題|全部)?(?:的)?(?:證明|解答|答案|解題|詳解)"
    r"(?:架構|流程|步驟)?|"
    r"(?:proof|solution|answer)|"
    r"(?:full|complete|whole|entire)\s*(?:proof|solution|answer|outline|steps)",
    re.I,
)
_TUTOR_DELIVERY_RE = re.compile(
    r"直接|跳過.{0,10}(?:提示|引導|步驟|推導)|"
    r"(?:給我|告訴我|提供|寫給我|幫我寫|展示|讓我看|先看|想看|列出|呈現)|"
    r"(?:^|請|麻煩)(?:先)?(?:替我|幫我)?(?:撰寫|寫出?|列出|整理|提供|呈現)|"
    r"(?:give|tell|show|provide|write).{0,12}(?:me|for me)|"
    r"(?:skip|bypass).{0,12}(?:hint|guidance|steps)",
    re.I,
)
_STUDENT_WRITES_RE = re.compile(
    r"(?:我(?:來|會|要|想|可以|現在)?(?:自己)?|讓我|請(?:叫|讓)?我|要求我).{0,6}"
    r"(?:寫|提交|交出|完成)|"
    r"\b(?:i(?: will|'ll| want to| can)?|let me|ask me to)\s+"
    r"(?:(?:now|first)\s+)?(?:write|submit|complete)\b",
    re.I,
)
_LOCAL_SOLUTION_SCOPE_RE = re.compile(
    r"(?:這|那|該|目前|當前)一?步|局部|單一步驟|"
    r"(?:this|that|the current) step|local step",
    re.I,
)
_ACTORLESS_SOLUTION_COMMAND_RE = re.compile(
    r"^(?:請|麻煩)?(?:先)?(?:將|把)?\s*(?:完整|整份|整個|全部)?(?:的)?"
    r"(?:證明|解答|答案|詳解|解題流程).{0,10}(?:寫出|寫下|提供|展示|列出|呈現)|"
    r"^(?:please\s+)?(?:first\s+)?(?:write|show|provide|present).{0,16}"
    r"(?:proof|solution|answer)",
    re.I,
)


def requests_tutor_to_supply_solution(text: str) -> bool:
    """辨認「Tutor 代為提供整份解答」，與學生自己交稿嚴格分流。"""
    t = (text or "").strip()
    if not t:
        return False
    if _LOCAL_SOLUTION_SCOPE_RE.search(t):
        return False
    # 先判斷「誰要寫」；否則「請叫我寫出完整證明」也會被較寬的
    # demand 句型搶先命中，誤當成要求 Tutor 代寫。
    if _STUDENT_WRITES_RE.search(t):
        return False
    if _ACTORLESS_SOLUTION_COMMAND_RE.search(t):
        return True
    if _DEMAND_RE.search(t):
        return True
    return bool(_SOLUTION_OBJECT_RE.search(t) and _TUTOR_DELIVERY_RE.search(t))


def student_requests_to_submit_proof(text: str) -> bool:
    """辨認「請系統叫學生自己交稿」，避免誤當 Tutor 代寫要求。"""
    t = (text or "").strip()
    return bool(t and _SOLUTION_OBJECT_RE.search(t) and _STUDENT_WRITES_RE.search(t))
# 嘗試偵測：學生交來一段自己的推導求確認 → 糾錯模式（此時可點名其誤用定理的前提）
_ATTEMPT_RE = re.compile(
    r"這樣對嗎|對不對|我的嘗試|我是這樣(想|做)|我認為|我覺得|"
    r"is (this|that|it) (right|correct)|am i (right|correct)|my attempt|"
    r"i think|i believe|does (this|that) work|here'?s what i did",
    re.I,
)

# 語言偵測：CJK 字元占比 <10% 判為英文（session 級，逐輪跟隨學生）
_CJK_RE = re.compile(r"[一-鿿]")
# 語言中立的數學片段：$…$、$$…$$、\(…\)、\[…\]、LaTeX 指令。
# 只剝 $…$ 與 \command 不夠——實測「中文＋長 LaTeX」的正確回答（\(f'(x_2)-f'(x_1)
# =f''(c)(x_2-x_1)\)）會把整串拉丁字母算進英文占比，session 當場切成英文。
_LANGUAGE_MATH_RE = re.compile(
    r"\$\$.*?\$\$|\$[^$]*\$|\\\(.*?\\\)|\\\[.*?\\\]|\\[A-Za-z]+", re.S)
# 裸算式（沒有 $ 包起來、但含關係符的連續符號串）同樣語言中立。
# 只吃不含空白也不含 CJK 的片段：吃了空白會把整句英文當算式剝掉、
# 吃了 CJK 會連中文字一起刪掉（那正好反轉判定結果）。
_BARE_MATH_RE = re.compile(r"[A-Za-z0-9\\'()\[\]{}^_|.,+\-*/]*[=<>≤≥≠]+"
                           r"[A-Za-z0-9\\'()\[\]{}^_|.,+\-*/=<>≤≥≠]*")


def _strip_language_neutral_math(text: str) -> str:
    """剝除語言中立的數學內容，只留真正能判定語言的自然語言文字。"""
    return _BARE_MATH_RE.sub(" ", _LANGUAGE_MATH_RE.sub(" ", text or ""))


def detect_lang(text: str) -> str:
    text = _strip_language_neutral_math(text)
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return "zh"
    cjk = sum(1 for c in chars if _CJK_RE.match(c))
    return "en" if cjk / len(chars) < 0.10 else "zh"

PHASE_INSTRUCTIONS = {
    "refuse_tutor_write": (
        "本輪指示：學生要求直接得到答案或完整證明。用一句話溫和拒絕（說明自己推導才真正有用），"
        "然後問一個具體的數學問題把主導權還給學生。絕對不要給出證明的任何步驟、算式或結論。"
    ),
    "respond_attempt": (
        "本輪指示：學生提交了自己的嘗試。對照參考解檢查：若有錯誤，用一個問題指出關鍵錯誤處、"
        "讓他自行發現與修正（可指出他誤用的定理缺了什麼前提，但不要替他改寫）；"
        "若方向正確，簡短肯定並問下一步。不要被學生的自信影響你的判斷。"
    ),
    "review": (
        "本輪指示：學生交來完整證明草稿。對照參考解逐步檢查，優先找這幾類缺漏："
        "引用定理的前提沒驗證、引用的事實沒交代依據（例如比較對象為何收斂）、"
        "嚴格與非嚴格不等號混用、特例未排除、量詞順序錯誤。"
        "找到後挑最重要的一個，用一個問題指出、讓他自行修正；正確的步驟不要質疑；"
        "只有在完全沒有缺漏時才可確認完成——確認完成後就肯定收尾，"
        "不要拋出延伸問題、變形題或新題目（完成即收手）。"
        "術語慣例：題目只寫「遞增」而未寫「嚴格遞增」時按單調不減理解，"
        "學生寫「單調不減／非減少」是精確表述，不是缺漏，不要要求他改寫。"
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
    "refuse_tutor_write": (
        "This turn: the student demands the answer or the full proof directly. Gently refuse in one "
        "sentence (explain that deriving it themselves is what actually helps), then ask one concrete "
        "mathematical question to hand control back to the student. Never give any step, formula, or "
        "conclusion of the proof."
    ),
    "respond_attempt": (
        "This turn: the student submitted their own attempt. Check it against the reference proof: if "
        "there is an error, point to the key mistake with one question and let them discover and fix it "
        "themselves (you may name the missing hypothesis of a theorem they misused, but do not rewrite "
        "it for them); if they are on the right track, affirm briefly and ask about the next step. Do "
        "not let the student's confidence sway your judgment."
    ),
    "review": (
        "This turn: the student submitted a complete proof draft. Check it step by step against the "
        "reference proof, prioritizing these gaps: theorem hypotheses not verified, cited facts without "
        "justification (e.g. why a comparison series converges), strict vs non-strict inequalities "
        "mixed up, special cases not excluded, quantifier order errors. Pick the most important gap and "
        "point to it with one question so the student fixes it themselves; do not question correct "
        "steps; only confirm completion when there is no gap at all — and once you confirm completion, "
        "close with the affirmation; do not pose extension questions, variants, or new problems. "
        "Terminology convention: when the problem says 'increasing' without 'strictly', read it as "
        "nondecreasing; a student who writes 'nondecreasing' is being precise, not leaving a gap — "
        "never ask them to reword it."
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

# respond_attempt/refuse_tutor_write/peer_reflect 是當輪回覆方式，不是持久 phase。
TURN_ACTION_INSTRUCTIONS = {
    "refuse_tutor_write": PHASE_INSTRUCTIONS["refuse_tutor_write"],
    "respond_attempt": PHASE_INSTRUCTIONS["respond_attempt"],
}
TURN_ACTION_INSTRUCTIONS_EN = {
    "refuse_tutor_write": PHASE_INSTRUCTIONS_EN["refuse_tutor_write"],
    "respond_attempt": PHASE_INSTRUCTIONS_EN["respond_attempt"],
}

# review/awaiting_submission 的保底回覆：階段轉換是公式化行為，
# driver 直接以此模板取代（確定性優於賭模型服從指示）。
WRITEUP_FALLBACK = "思路已經完整了。現在請把完整證明一步步寫出來，我會幫你審閱。"
WRITEUP_FALLBACK_EN = ("The idea is now complete. Please write out the full proof step by step, "
                       "and I will review it for you.")
WRITEUP_WAIT_REMINDER = "請提交你自己寫的完整證明；收到全文後，我才會開始逐步審閱。"
WRITEUP_WAIT_REMINDER_EN = (
    "Please submit the complete proof in your own words; I will begin the full review "
    "after receiving the whole draft.")
REVIEW_REFUSE_WRITE = (
    "我不會代寫完整證明。請繼續提交你自己的全文或目前要修正的那一項。")
REVIEW_REFUSE_WRITE_EN = (
    "I will not write the complete proof for you. Please submit your own full draft or "
    "the correction for the current review issue.")
WALK_REFUSE_WRITE = "我不會代寫完整證明。請先回答目前這一步的確認問題。"
WALK_REFUSE_WRITE_EN = (
    "I will not write the complete proof for you. Please answer the current step's "
    "check question first.")
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
# closed 後只有斷言式、明確指出錯誤的質疑才重查最近草稿；「真的嗎／你確定嗎」
# 仍只是完成後的範圍內追問，不應因單一疑問句重開整套審閱。
_ASSERTIVE_CHALLENGE_RE = re.compile(
    r"你錯|你搞錯|這裡.{0,8}(錯|不成立|有問題)|根本不成立|"
    r"漏審|漏掉.{0,8}(錯|問題)|"
    r"you'?re wrong|this (step|part|claim).{0,12}(is wrong|fails|is invalid)|"
    r"you missed.{0,12}(error|issue|problem)",
    re.I,
)


def _is_nonassertive_review_confirmation(text: str) -> bool:
    """辨認結案後只求確認、沒有斷言錯誤或要求重審的問句。"""
    t = (text or "").strip()
    if not t or _ASSERTIVE_CHALLENGE_RE.search(t) or _MISSED_REVIEW_RE.search(t):
        return False
    interrogative = bool(
        _QMARK_RE.search(t)
        or re.search(r"(?:嗎|呢|是否|是不是|有沒有)\s*[。.!]?$", t, re.I)
    )
    confirmation = bool(re.search(
        r"確定|真的|是否|是不是|有沒有|沒(?:有)?.{0,10}(?:錯|問題)|"
        r"are you (?:really |completely )?sure|"
        r"(?:did i|have i).{0,12}(?:make|made|miss).{0,8}(?:error|mistake)|"
        r"(?:is|was).{0,12}(?:proof|answer|solution).{0,8}(?:correct|right)",
        t, re.I,
    ))
    return interrogative and confirmation

# ── 逐步教學（walkthrough：連續卡住三次 → 一小步一確認地教）───────────────────
# 這一階段**不呼叫生成模型**，逐字由 teach_steps 組出來。理由：
#   (1) 內容本來就是預寫的（設計鐵律：內容拿捏交給預寫內容，模型只負責語氣）——
#       而這裡連語氣都不值得賭：實測模型會把同一步逐字重講三輪（弱點 #17）、
#       會一次講掉好幾步、會把確認問題換成別的問題，使答案鍵無從比對。
#   (2) 教學輪原本每輪最多 4 次重生成（守門該段 12 → 45 分鐘），而等在螢幕前的
#       正是最需要幫助的那個學生。改成模板後教學輪的生成次數固定為 0。
WALKTHROUGH_TEMPLATE = "第 {i}/{n} 步：{explain}\n\n確認問題：{check}"
WALKTHROUGH_TEMPLATE_EN = "Step {i}/{n}: {explain}\n\nCheck: {check}"
# 每個確認問題只有一次有效作答機會。審閱後盾判為答不出、部分正確或
# 數學錯誤時，Driver 揭示參考答案並前進；後盾離線、逾時或不確定不算學生作答，留在原步驟。
WALK_REVEAL = ("這個回答尚未正確，原因是：{reason}。"
               "這一步的正確答案是：{answer}。我們接著看下一步。")
WALK_REVEAL_EN = ("That answer is not yet correct because: {reason}. "
                  "The correct answer to this step is: {answer}. Let's move on to the next step.")
WALK_REVEAL_LAST = ("這個回答尚未正確，原因是：{reason}。"
                    "這一步的正確答案是：{answer}。")
WALK_REVEAL_LAST_EN = ("That answer is not yet correct because: {reason}. "
                       "The correct answer to this step is: {answer}.")
WALK_JUDGE_UNAVAILABLE = ("本輪未取得可靠的語意審閱結果，因此不把你的回答判為錯誤。"
                          "我們保留在目前步驟，請再回答一次同一個確認問題。")
WALK_JUDGE_UNAVAILABLE_EN = ("A reliable semantic review was not available for this turn, "
                             "so I am not marking your answer incorrect. We will remain on the "
                             "current step; please answer the same check once more.")
WALK_JUDGE_UNAVAILABLE_LAST = WALK_JUDGE_UNAVAILABLE
WALK_JUDGE_UNAVAILABLE_LAST_EN = WALK_JUDGE_UNAVAILABLE_EN

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

# 合併 guide 審查真正不可用或兩稿都不安全時，僅使用不含題型內容的通用問句。
# 輪換是為了避免固定 Controller 保底句進入對話後，被說話模型隔輪照抄。
_SAFE_GUIDE_REVIEW_FALLBACKS = (
    "先停在目前的缺口。你能說明自己最後確定成立的是哪一個主張嗎？",
    "先不要跳到後面。你能檢查上一個推論的前提與結論是否相符嗎？",
    "你目前能確定成立的一個式子或數學主張是什麼？",
)
_SAFE_GUIDE_REVIEW_FALLBACKS_EN = (
    "Let's pause at the current gap. What is the last claim you established yourself?",
    "Before moving on, do the assumptions and conclusion of your previous inference match?",
    "What is one equation or mathematical claim that you have established so far?",
)
# 「證明其實已經走完、只是全程沒有交稿步驟」時的保底句（守門對話 X4 型）：
# 這種輪次補通用追問會答非所問（評審判為「已完成卻多餘追問」），正確的下一步是
# 請學生把證明寫出來——接上 writeup → review → 審閱通過 → 收尾這條既有路徑。
WRITEUP_NUDGE = " 那你能自己把完整的證明寫出來嗎？我來幫你審閱。"
WRITEUP_NUDGE_EN = " Could you now write out the complete proof yourself? I'll review it for you."

# 審閱通過的確定性收尾：後盾逐步複核回報「無缺漏」時直接用它，不再讓說話模型自由發揮。
# 理由是實測的兩種失敗：憑空發明缺漏（「非減少和遞增等價嗎？」）與確認完成後又追問
# 「下一步該從哪裡下手」。後盾說沒有缺漏，這一輪要說的話就沒有需要即興的空間。
REVIEW_PASS = ("你的證明我已經對照逐步複核過了：每一步的依據都交代清楚，論證完整，"
               "沒有缺漏。這份證明可以定稿了，做得很好。")
REVIEW_PASS_EN = ("I've checked your proof step by step: every step is justified, the argument is "
                  "complete, and there are no gaps. This proof is finished — well done.")

# 全文審閱／局部訂正採確定性輸出。數學判斷由 Thinking 後盾完成，Driver 只負責
# 一次呈現一項、保存草稿與控制進度，不讓說話模型自行跳題或一次列出多項。
REVIEW_CLEAN_REQUEST = ("目前草稿中的審閱問題都已逐項修正，合併後也通過兩輪複核。"
                        "請現在提交一份不含訂正註記的乾淨完整證明，做最後全文審閱。")
REVIEW_CLEAN_REQUEST_EN = ("All review issues in the working draft have been fixed, and the merged "
                           "draft passed both review passes. Please now submit one clean, complete "
                           "proof without correction notes for the final full review.")
REVIEW_UNAVAILABLE = ("兩輪審閱目前未能可靠完成；草稿與審閱進度都已保留。"
                      "請稍後原樣重送這份完整證明，我會重新做兩輪全文檢查。")
REVIEW_UNAVAILABLE_EN = ("The two-pass review could not be completed reliably. Your draft and review "
                         "state are preserved; please resend the same full proof to retry both passes.")
LOCAL_JUDGE_UNAVAILABLE = ("目前無法可靠確認這項局部訂正，因此我沒有合併草稿或前進。"
                           "請保留同一項訂正並稍後再送一次。")
LOCAL_JUDGE_UNAVAILABLE_EN = ("I cannot reliably verify this local correction right now, so I have "
                              "not merged it or advanced. Please retry the same correction later.")
LOCAL_MERGE_UNAVAILABLE = ("這項局部訂正已通過數學審閱，但目前未能可靠合併回完整草稿；"
                           "因此尚未前進。請原樣重送這項訂正。")
LOCAL_MERGE_UNAVAILABLE_EN = ("This local correction passed mathematical review, but it could not be "
                              "merged reliably into the full draft, so I have not advanced. Please "
                              "resend the same correction.")
REVIEW_ISSUE_UNACTIONABLE = ("審閱找到可能的問題，但未取得足以安全進行局部訂正的"
                             "位置或修正條件。我沒有建立不可靠的訂正佇列；"
                             "請稍後重送完整證明以重新審閱。")
REVIEW_ISSUE_UNACTIONABLE_EN = ("The review found a possible issue but did not return enough location "
                                "or correction information for a safe local revision. I did not create "
                                "an unreliable correction queue; please resend the full proof later.")
MERGED_REVIEW_UNAVAILABLE = ("合併草稿的全文複核目前無法可靠完成，已核准的局部訂正"
                             "與草稿都已保留。請稍後提交一份包含這些訂正的乾淨完整證明。")
MERGED_REVIEW_UNAVAILABLE_EN = ("The merged-draft review could not be completed reliably. The approved "
                                "local corrections and working draft are preserved; please later submit "
                                "a clean full proof containing those corrections.")

# 術語守衛（弱點：說話模型會在正確證明上憑空挑起 increasing／nondecreasing 之爭）。
# 題目沒寫 strictly、學生已寫「單調不減」，助教卻還在這兩個詞之間糾結＝假缺漏。
_STRICT_MONO_RE = re.compile(r"嚴格(單調)?(遞增|遞減)|strictly (increasing|decreasing|monotone)", re.I)
_NONDEC_TERM_RE = re.compile(r"單調不減|單調非減|非減少|不遞減|non-?decreasing", re.I)
_INC_TERM_RE = re.compile(r"遞增|increasing", re.I)


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
# 單輪「品質類」守衛的重生成次數上限（安全閥）。每次重生成在 6GB 卡上要數十秒，
# 而等待的人正是逐步教學裡最需要幫助的學生。⚠️ 內容防護（洩漏／防奉送／禁算式／
# 稱讚校準）**不受此限**——那是安全性，不能為了省時間放行。
_MAX_REGEN_PER_TURN = 2

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
    remaining = _MATH_SPAN_RE.sub(" ", s or "")
    for tok in _MATH_BARE_RE.findall(remaining):
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
    """回覆是否出現 allowed_src（題目敘述＋核心想法＋學生說過的話）之外的新等式。"""
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
    problem: dict                      # 需含 statement / reference_proof
    max_new_tokens: int = 240
    # 審閱後盾開關（預設開；Ollama 不在線會自動降級，REVIEW_BACKSTOP=0 強制關）
    backstop: bool = field(
        default_factory=lambda: os.environ.get("REVIEW_BACKSTOP", "1") == "1")
    state: dict = field(default_factory=lambda: {
        "phase": "guide", "review_status": None,
        "turn_action": "normal_guide", "mode": "tutor",
        "stuck_count": 0, "turns": [], "phase_history": [], "phase_events": [],
        # turns: list[TurnLog]；phase_history: 每則學生訊息的完整路由／切換診斷
    })
    messages: list = field(default_factory=list)

    # ---- 同學模式 / 逐步教學輔助 ----------------------------------------------
    def __post_init__(self) -> None:
        try:
            from phase_router import normalize_persisted_state
        except ImportError:
            from .phase_router import normalize_persisted_state
        normalize_persisted_state(self.state)
        self.state.setdefault("turns", [])
        self.state.setdefault("phase_history", [])
        self.state.setdefault("phase_events", [])
        self.state.setdefault("turn_action", "normal_guide")

    @property
    def lang(self) -> str:
        return self.state.get("lang", "zh")

    def is_peer(self) -> bool:
        """無可靠參考解（自動備課驗證失敗）→ 同儕身分，不得以助教權威教學。"""
        return (self.problem.get("grounding") == "unverified"
                or not self.problem.get("reference_proof"))

    def _apply_phase_event(self, event: str, *, source: str) -> str:
        """唯一可以更新持久 phase 的 Driver 介面。"""
        try:
            from phase_router import apply_phase_event
        except ImportError:
            from .phase_router import apply_phase_event
        return apply_phase_event(self.state, event, source=source)

    def _set_review_status(self, status: str, *, detail: str | None = None) -> None:
        """更新 review 局部狀態，並同步舊旗標鏡射。"""
        try:
            from phase_router import REVIEW_STATUSES, _sync_compatibility_flags
        except ImportError:
            from .phase_router import REVIEW_STATUSES, _sync_compatibility_flags
        if status not in REVIEW_STATUSES:
            raise ValueError(f"unknown review status: {status}")
        self.state["review_status"] = status
        if detail:
            self.state["review_detail"] = detail
        else:
            self.state.pop("review_detail", None)
        _sync_compatibility_flags(self.state)

    def _teach_lang(self) -> str:
        """教學步驟該用哪種語言：walkthrough 進行中鎖定 walk_lang（見 step()）。"""
        return self.state.get("walk_lang") or self.lang

    def _ensure_teach_steps(self) -> list:
        """取得與 walkthrough 語言一致、且經步驟驗證的教學步驟。

        備課成功的步驟只做語言版本選擇，缺少目標語言時翻譯同一套步驟，絕不重切。
        只有備課時初次切分失敗，才在真正進入 walkthrough 前依 session 語言重試。
        驗證未通過時回空清單，不啟用無法保證問題／答案語意對齊的機械 fallback。
        """
        lang = self._teach_lang()
        cache_key = f"teach_steps_{lang}"
        source_key = f"teach_steps_source_{lang}"

        try:
            from auto_reference import (ensure_checkable_steps, segment_proof,
                                        translate_teach_steps)
        except ImportError:
            ensure_checkable_steps = segment_proof = translate_teach_steps = None

        def prepared(raw: list) -> list:
            if ensure_checkable_steps:
                return ensure_checkable_steps(raw, lang=lang)
            return [{**s, "step_id": str(s.get("step_id") or f"step-{i}"),
                     "expected_answer": str(s.get("expected_answer")
                                            or s.get("explain") or "").strip(),
                     "accepted_answers": list(s.get("accepted_answers") or []),
                     "common_errors": list(s.get("common_errors") or [])}
                    for i, s in enumerate(raw or [], 1) if isinstance(s, dict)]

        steps = self.problem.get(cache_key)
        if steps:
            steps = prepared(steps)
            self.problem[cache_key] = steps
            source = self.problem.get(source_key) or "cache"
            self.problem[source_key] = source
            self.state["teach_steps_source"] = source
            return steps

        # 舊資料的主欄位只有在所有非空講解／問題皆為本 session 語言時才沿用。
        steps = self.problem.get("teach_steps")
        if steps:
            fields = [str(s.get(k) or "") for s in steps if isinstance(s, dict)
                      for k in ("explain", "check")]
            if fields and all(detect_lang(x) == lang for x in fields if x.strip()):
                steps = prepared(steps)
                source = (self.problem.get("teach_steps_source")
                          if self.problem.get("teach_steps_lang") in (None, lang)
                          else None) or "provided"
                self.problem[cache_key] = steps
                self.problem[source_key] = source
                self.state["teach_steps_source"] = source
                return steps

        # 初次切分曾成功，但目前缺少 session 語言版本：翻譯既有同一套步驟，
        # 不得再次呼叫 SEGMENTER，否則相同 walk_idx 可能對應到不同數學內容。
        alternate = None
        for other_lang in ("zh", "en"):
            if other_lang != lang and self.problem.get(f"teach_steps_{other_lang}"):
                alternate = self.problem[f"teach_steps_{other_lang}"]
                break
        if alternate is None and self.problem.get("teach_steps"):
            alternate = self.problem["teach_steps"]
        if alternate:
            translated = (translate_teach_steps(
                self.problem["statement"], self.problem["reference_proof"],
                alternate, target_lang=lang) if translate_teach_steps else None)
            source = "translation" if translated else "translation_unavailable"
            translated = prepared(translated or [])
            self.problem[cache_key] = translated
            self.problem[source_key] = source
            self.state["teach_steps_source"] = source
            return translated

        if self.problem.get("teach_steps_initial_status") == "success":
            # 正常資料必定至少保留原語言版本；若資料傳遞意外遺失，也不可把
            # 「曾成功切分」誤判成需要重切，寧可受控地不啟用 walkthrough。
            self.state["teach_steps_source"] = "prepared_steps_missing"
            return []

        # 沒有任何已成功切分的版本，表示備課時初次切分失敗；只在 walkthrough
        # 真正需要步驟的此刻，依已鎖定的 session 語言重試一次完整切分。
        proof = self.problem["reference_proof"]
        steps = (segment_proof(self.problem["statement"], proof, lang=lang)
                 if segment_proof else None)
        source = "segmenter" if steps else "unavailable"
        if not steps:
            print("  [SEGMENTER] 當前 session 語言的步驟三次輸出或驗證未通過；"
                  "不啟用不可靠的機械式逐步教學。")
            steps = []
        steps = prepared(steps)
        self.problem[cache_key] = steps
        self.problem[source_key] = source
        self.state["teach_steps_source"] = source
        if not self.problem.get("teach_steps"):
            self.problem["teach_steps"] = steps
            self.problem["teach_steps_lang"] = lang
            self.problem["teach_steps_source"] = source
        return steps

    def _walkthrough_reply(self) -> str:
        """逐步教學的回覆：一個步驟＋一個確認問題。

        步驟首次呈現後，學生只有一次作答機會，所以不存在重講輪。
        同時記下「這一輪實際呈現的是哪一步」（walk_presented_*）——下一輪必須拿它
        來評分，而不是依當下語言重新去取 steps[walk_idx]。
        """
        steps = self._ensure_teach_steps()
        if not steps:
            self._apply_phase_event("RESET", source="walkthrough_steps_unavailable")
            self.state.pop("walk_lang", None)
            return ("I could not prepare a reliable step-by-step lesson, so I will keep using "
                    "guided questions instead." if self.lang == "en" else
                    "目前無法準備可靠的逐步教學內容，我們先維持一般引導，"
                    "不使用可能錯位的步驟。")
        idx = min(self.state.get("walk_idx", 0), len(steps) - 1)
        step = dict(steps[idx])
        en = self._teach_lang() == "en"
        tpl = WALKTHROUGH_TEMPLATE_EN if en else WALKTHROUGH_TEMPLATE
        check = enforce_single_question(str(step.get("check") or "").strip())
        if not _QMARK_RE.search(check):
            check += "?" if en else "？"
        # 講解區只能陳述；問句只出現在確認問題區，才能穩定維持「一步一問」。
        explain = re.sub(r"[?？]+", "。", str(step.get("explain") or "")).strip()
        body = tpl.format(i=idx + 1, n=len(steps), explain=explain, check=check)
        lead = self.state.pop("walk_feedback", "")
        self.state.update(walk_presented_step=step, walk_presented_idx=idx,
                          walk_presented_step_id=step.get("step_id"))
        return (lead + "\n\n" + body) if lead else body

    # ---- 完整證明審閱佇列 ----------------------------------------------------
    def _looks_like_complete_proof(self, text: str) -> bool:
        """辨識實質完整證明；避免把一句局部修正誤當成全文重交。"""
        t = (text or "").strip()
        if len(t) < 70:
            return False
        connectors = re.findall(
            r"因為|由於|(?:^|[，。；,:：\s])由|所以|因此|故|於是|從而|進而|"
            r"可知|可得|得到|推出|解出|接下來|然後|再(?:取|由|把|代|用)|最後|"
            r"whereas|since|because|therefore|thus|hence|then|so|it follows|which gives|"
            r"by (?:the|a)?\s*[a-z ]+(?:theorem|inequality)",
            t, re.I)
        has_math = bool(re.search(
            r"[$\\=<>≤≥∈]|任取|令|設|假設|命題|得證|\b(let|suppose|assume|claim)\b",
            t, re.I))
        return len(connectors) >= 2 and has_math

    def _has_strong_complete_proof_shape(self, text: str) -> bool:
        """辨識未加「完整證明」標籤、但本身已具完整論證結構的交稿。

        只靠長度會把詳細的單步回答誤當全文；因此同時要求多段推理連接、
        定理／定義依據、數學內容與收束原命題的結論訊號。這些都是題型無關的
        證明結構特徵，可用於一般引導與 walkthrough 中的主動全文交稿。
        """
        t = (text or "").strip()
        if len(t) < 180 or not self._looks_like_complete_proof(t):
            return False
        connectors = re.findall(
            r"因為|由於|(?:^|[，。；,:：\s])由|所以|因此|故|於是|從而|進而|"
            r"可知|可得|得到|推出|接下來|然後|最後|代入|化簡|"
            r"since|because|therefore|thus|hence|then|so|it follows|which gives|finally|substitut",
            t, re.I)
        has_justification = bool(re.search(
            r"定義|定理|公理|性質|假設|題設|根據|依據|"
            r"definition|theorem|lemma|property|assumption|by\s+the",
            t, re.I))
        has_conclusion = bool(
            _CLAIM_DONE_RE.search(t) or re.search(
                r"結論|這(?:樣)?就證明(?:了|出)?|證得|得證|證畢|證明完成|"
                r"命題成立|原命題成立|所求|滿足題意|"
                r"as required|as desired|which proves|this proves|the claim follows",
                t, re.I))
        math_relations = len(re.findall(r"=|≤|≥|<|>|\\(?:leq?|geq?)\b", t))
        return (len(connectors) >= 3 and has_justification
                and has_conclusion and math_relations >= 2)

    def _is_full_proof_submission(self, text: str) -> bool:
        """全文重交優先於局部訂正；只有明確或具完整證明結構的訊息才命中。"""
        t = (text or "").strip()
        explicit = bool(_EXPLICIT_REVIEW_RE.search(t))
        starts_proof = bool(_PROOF_SUBMISSION_START_RE.search(t))
        complete_shape = self._looks_like_complete_proof(t)
        strong_complete_shape = self._has_strong_complete_proof_shape(t)
        if explicit and (len(t) >= 40 or complete_shape):
            return True
        if starts_proof and (len(t) >= 80 or complete_shape):
            return True
        # 學生可能直接貼上有完整開端、推理鏈與結論的證明而沒有先標「以下是證明」。
        # 在 walkthrough 中尤其不能把整份交稿誤當單一確認問題的回答。
        if strong_complete_shape:
            return True
        if (self.state.get("phase") == "review"
                and self.state.get("review_status") == "awaiting_clean"
                and complete_shape):
            return True
        if (self.state.get("phase") == "review"
                and self.state.get("review_status") == "correcting"):
            # 審閱中只有清楚重交全文才中斷目前局部問題；長但局部的說明仍交 Thinking
            # 判斷目前訂正。未加「完整證明」標籤的全文仍可由完整論證結構＋足夠篇幅
            # 認出，避免把學生直接貼上的重寫全文誤送進局部訂正判定。
            return complete_shape and len(t) >= 140
        if (self.state.get("phase") == "review"
                and self.state.get("review_status") in {
                    "awaiting_submission", "checking", "rechecking", "unavailable",
                }
                and complete_shape):
            return True
        return bool(_DRAFT_RE.search(t) and complete_shape)

    def _review_issue_reply(self, prefix: str = "") -> str:
        """每輪直接說明一個根本錯誤；正確版本只供 Thinking 內部判斷。"""
        issues = self.state.get("review_issues") or []
        idx = int(self.state.get("review_issue_idx", 0))
        if not issues or idx >= len(issues):
            return ""
        issue = issues[idx]
        location = re.sub(r"[?？]+", "。", str(issue.get("location") or "")).strip()
        # 只把根本錯誤名稱告訴學生；description/correction 留給 Thinking 判定與合併，
        # 避免把內部參考答案一併公布。
        desc = re.sub(r"[?？]+", "。", str(issue.get("root_cause") or
                                             issue.get("description") or "")).strip()
        en = self.lang == "en"
        head = (f"Review issue {idx + 1}/{len(issues)}: " if en
                else f"審閱第 {idx + 1}/{len(issues)} 項：")
        if en:
            rows = [head.rstrip()]
            if location:
                rows.append("Location: " + location)
            rows.append("Error: " + desc)
            rows.append("Submit only this local correction; I will move to the next issue after it is verified.")
        else:
            rows = [head.rstrip()]
            if location:
                rows.append("位置：" + location)
            rows.append("錯誤：" + desc)
            rows.append("請只提交這一項的局部訂正；確認正確後，我才會處理下一項。")
        body = "\n".join(rows)
        return (prefix.rstrip() + "\n\n" + body) if prefix else body

    def _compose_current_proof_draft(self) -> str:
        """回傳已逐次實際合併局部訂正的工作草稿，不附加覆蓋註記。"""
        draft = str(self.state.get("current_proof_draft") or
                    self.state.get("review_base_proof") or "").strip()
        self.state["current_proof_draft"] = draft
        return draft

    def _run_two_pass_review(self, draft: str) -> list[dict] | None:
        try:
            from review_backstop import review_full_proof
        except ImportError:
            return None
        return review_full_proof(self.problem["statement"],
                                 self.problem["reference_proof"], draft)

    def _run_local_revision_judge(self, issue: dict, answer: str) -> dict | None:
        try:
            from review_backstop import judge_local_revision
        except ImportError:
            return None
        return judge_local_revision(
            self.problem["statement"], self.problem["reference_proof"],
            str(self.state.get("current_proof_draft") or ""), issue, answer)

    def _merge_approved_revision(self, issue: dict, answer: str) -> str | None:
        try:
            from review_backstop import merge_proof_revision
        except ImportError:
            return None
        return merge_proof_revision(
            self.problem["statement"], self.problem["reference_proof"],
            str(self.state.get("current_proof_draft") or ""), issue, answer)

    @staticmethod
    def _review_issue_is_actionable(issue: dict) -> bool:
        """局部訂正至少要有根本問題，並有位置或內部修正條件可供定位。"""
        if not isinstance(issue, dict):
            return False
        root = str(issue.get("root_cause") or issue.get("description") or "").strip()
        anchor = str(issue.get("location") or issue.get("correction") or "").strip()
        return bool(root and anchor)

    def _install_review_issues(self, issues: list[dict]) -> bool:
        """只建立可執行的局部訂正佇列；回傳是否可安全繼續。"""
        if issues and not all(self._review_issue_is_actionable(x) for x in issues):
            self.state["review_unactionable_issues"] = list(issues)
            self.state.update(review_issues=[], review_issue_idx=0,
                              review_error="issue_not_actionable")
            self._set_review_status("awaiting_submission", detail="issue_not_actionable")
            return False
        self.state.pop("review_unactionable_issues", None)
        self.state.pop("review_error", None)
        self.state.update(review_issues=issues, review_issue_idx=0)
        self._set_review_status("correcting" if issues else "checking")
        return True

    def _start_full_proof_review(self, proof: str) -> str:
        """保存新全文並做兩輪審閱；新全文永遠重查全部內容。"""
        was_revision_cycle = bool(self.state.get("review_status") in {
                                      "correcting", "awaiting_clean", "rechecking"}
                                  or self.state.get("review_had_issues"))
        self._apply_phase_event("FULL_PROOF_SUBMITTED", source="full_proof_guard")
        # FULL_PROOF_SUBMITTED 只在 review 合法。即使內部呼叫者誤在
        # guide/walkthrough 啟動審閱，也不得繞過階段事件守門。
        latest_event = (self.state.get("phase_events") or [{}])[-1]
        if not latest_event.get("accepted"):
            return ""
        self.state.update(review_base_proof=proof.strip(), current_proof_draft=proof.strip(),
                          review_last_full_proof=proof.strip(), review_corrections=[],
                          review_issues=[], review_issue_idx=0)
        self.state.pop("review_error", None)
        self._set_review_status("rechecking" if was_revision_cycle else "checking")
        issues = self._run_two_pass_review(proof.strip())
        if issues is None:
            self.state["review_error"] = "full_review_unavailable"
            self._set_review_status("awaiting_submission", detail="full_review_unavailable")
            return REVIEW_UNAVAILABLE_EN if self.lang == "en" else REVIEW_UNAVAILABLE
        if issues:
            self.state["review_had_issues"] = True
            if not self._install_review_issues(issues):
                return (REVIEW_ISSUE_UNACTIONABLE_EN if self.lang == "en"
                        else REVIEW_ISSUE_UNACTIONABLE)
            return self._review_issue_reply()
        self._install_review_issues([])
        self.state["review_had_issues"] = False
        self.state["review_detail"] = "final_pass" if was_revision_cycle else "pass"
        self._apply_phase_event("REVIEW_PASSED", source="review_judge")
        return REVIEW_PASS_EN if self.lang == "en" else REVIEW_PASS

    def _review_merged_draft(self) -> str:
        """既有問題逐項修完後，重新兩輪全文審閱合併草稿。"""
        draft = self._compose_current_proof_draft()
        self._set_review_status("rechecking", detail="merged_draft")
        issues = self._run_two_pass_review(draft)
        if issues is None:
            self.state["review_error"] = "merged_review_unavailable"
            self._set_review_status("awaiting_submission", detail="merged_review_unavailable")
            return (MERGED_REVIEW_UNAVAILABLE_EN if self.lang == "en"
                    else MERGED_REVIEW_UNAVAILABLE)
        if issues:
            if not self._install_review_issues(issues):
                return (MERGED_REVIEW_UNAVAILABLE_EN if self.lang == "en"
                        else MERGED_REVIEW_UNAVAILABLE)
            return self._review_issue_reply(
                "合併草稿重新複核後，還有一項需要處理。" if self.lang != "en"
                else "The merged draft still has one issue to address after re-review.")
        self._install_review_issues([])
        self._set_review_status("awaiting_clean")
        return REVIEW_CLEAN_REQUEST_EN if self.lang == "en" else REVIEW_CLEAN_REQUEST

    def _handle_local_revision(self, answer: str) -> str:
        issues = self.state.get("review_issues") or []
        idx = int(self.state.get("review_issue_idx", 0))
        if idx >= len(issues):
            return self._review_merged_draft()
        issue = issues[idx]
        judged = self._run_local_revision_judge(issue, answer)
        self.state["local_revision_review"] = judged
        if judged is None:
            # unavailable 是本次服務失敗，不是學生訂正被判錯。
            # 保留 correcting／同一 issue／原草稿，下一輪可原樣重試。
            self.state["review_error"] = "local_judge_unavailable"
            self._set_review_status("correcting", detail="local_judge_unavailable")
            return (LOCAL_JUDGE_UNAVAILABLE_EN if self.lang == "en"
                    else LOCAL_JUDGE_UNAVAILABLE)
        self.state.pop("review_error", None)
        verdict = judged.get("verdict")
        if verdict != "correct":
            self._set_review_status("correcting", detail=f"local_{verdict}")
            feedback = str(judged.get("feedback") or "").strip()
            lead = (("This issue is not fully corrected yet" if self.lang == "en"
                     else "這一項尚未完整修正") + (f"：{feedback}" if feedback else "。"))
            return self._review_issue_reply(lead)

        merged = self._merge_approved_revision(issue, answer)
        if not merged:
            self.state["review_error"] = "local_merge_unavailable"
            self._set_review_status("correcting", detail="local_merge_unavailable")
            return (LOCAL_MERGE_UNAVAILABLE_EN if self.lang == "en"
                    else LOCAL_MERGE_UNAVAILABLE)
        self.state.pop("review_error", None)
        self.state["current_proof_draft"] = merged
        self.state["review_base_proof"] = merged
        self.state.setdefault("review_corrections", []).append(
            {"issue": dict(issue), "revision": answer.strip()})
        self.state["review_issue_idx"] = idx + 1
        self._set_review_status("correcting", detail="local_correct")
        if self.state["review_issue_idx"] < len(issues):
            return self._review_issue_reply(
                "這一項已完成訂正。" if self.lang != "en"
                else "That issue has been corrected.")
        return self._review_merged_draft()

    def _recheck_latest_proof(self) -> str:
        """學生指出漏審時，重查最近一份完整證明與已核准訂正。"""
        draft = self._compose_current_proof_draft()
        if not draft:
            return ""
        if self.state.get("phase") == "closed":
            self._apply_phase_event(
                "REVIEW_REOPEN_REQUESTED", source="closed_recheck_intent")
        else:
            self._set_review_status("rechecking")
        issues = self._run_two_pass_review(draft)
        if issues is None:
            self.state["review_error"] = "full_review_unavailable"
            self._set_review_status("awaiting_submission", detail="full_review_unavailable")
            return REVIEW_UNAVAILABLE_EN if self.lang == "en" else REVIEW_UNAVAILABLE
        if issues:
            self.state["review_had_issues"] = True
            if not self._install_review_issues(issues):
                return (REVIEW_ISSUE_UNACTIONABLE_EN if self.lang == "en"
                        else REVIEW_ISSUE_UNACTIONABLE)
            return self._review_issue_reply(
                "I rechecked the latest full proof in two passes." if self.lang == "en"
                else "我已對最近一份完整證明重新做兩輪檢查。")
        self._install_review_issues([])
        if self.state.get("review_corrections"):
            self._set_review_status("awaiting_clean")
            return REVIEW_CLEAN_REQUEST_EN if self.lang == "en" else REVIEW_CLEAN_REQUEST
        self.state["review_had_issues"] = False
        self.state["review_detail"] = "pass"
        self._apply_phase_event("REVIEW_PASSED", source="review_recheck_judge")
        return REVIEW_PASS_EN if self.lang == "en" else REVIEW_PASS

    def _review_workflow_transition(self, student_text: str) -> str | None:
        """消費本輪統一 router 決策，需由 review 流程回覆時回文字。

        start()/step() 會先分類；直接呼叫此相容介面時才在這裡補分類。
        review 本身不再使用另一套 regex/外形偵測判斷意圖。
        """
        if self.is_peer():
            return None
        cached = (self.state.get("student_state_decision")
                  if self.state.get("student_state_text") == student_text else None)
        decision = (cached if isinstance(cached, dict)
                    else self._route_student_state(student_text).to_dict())
        intent = decision.get("intent")
        # walkthrough 是硬鎖。此時任何學生訊息（即使外形像完整證明）都只接受為
        # 當前確認問題的一次回答；教完後由系統主動進
        # review/awaiting_submission 才能交稿。
        if self.state.get("phase") == "walkthrough":
            return None
        # closed 只消費 router 的「質疑／漏審」判定；普通反思與致謝維持 closed。
        if self.state.get("phase") == "closed":
            if (intent == "challenge_or_missed_review"
                    and self.state.get("current_proof_draft")):
                return self._recheck_latest_proof()
            return None
        if self.state.get("phase") != "review":
            return None
        if intent == "demand_full_answer":
            return REVIEW_REFUSE_WRITE_EN if self.lang == "en" else REVIEW_REFUSE_WRITE
        if self.state.get("review_status") == "awaiting_submission":
            if intent == "full_proof_submission":
                if not self.backstop:
                    return None
                return self._start_full_proof_review(student_text)
            return (WRITEUP_WAIT_REMINDER_EN if self.lang == "en"
                    else WRITEUP_WAIT_REMINDER)
        if not self.backstop:
            return None
        if intent == "full_proof_submission":
            return self._start_full_proof_review(student_text)
        if self.state.get("review_status") == "correcting":
            return self._handle_local_revision(student_text)
        if self.state.get("review_status") == "awaiting_clean":
            return REVIEW_CLEAN_REQUEST_EN if self.lang == "en" else REVIEW_CLEAN_REQUEST
        if self.state.get("review_status") == "unavailable":
            # 舊快照相容：unavailable 不得成為吞掉後續輸入的死路。
            if self.state.get("review_issues"):
                self._set_review_status("correcting", detail="legacy_retry")
                return self._handle_local_revision(student_text)
            self._set_review_status("awaiting_submission", detail="legacy_retry")
            return REVIEW_UNAVAILABLE_EN if self.lang == "en" else REVIEW_UNAVAILABLE
        return None

    def _emit_review_reply(self, student_text: str, reply: str) -> str:
        """記錄確定性審閱輪，格式與一般 _tutor_turn 的 session 快照相容。"""
        self.state["stuck_count"] = 0
        self.messages.append({"role": "user", "content": student_text})
        log = TurnLog(level=0, stuck_count=0, guards=["review_queue"])
        self.state["turns"].append(log)
        self.messages.append({"role": "assistant", "content": reply})
        return reply

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
        """review/respond_attempt 輪呼叫思考型模型找碴；結果存 state['backstop_gaps']。"""
        self.state["backstop_gaps"] = None
        if not self.backstop:
            return
        try:
            from review_backstop import find_gaps
        except ImportError:
            return
        self.state["backstop_gaps"] = find_gaps(
            self.problem["statement"], self.problem["reference_proof"], student_text)

    def _judge_walkthrough_answer(self, student_text: str, step: dict) -> dict | None:
        """以審閱後盾做數學語意判定；絕不退回答案字串比對。

        後盾關閉、離線、逾時、輸出無法解析或判定不確定時回傳 None。狀態機會把
        None 視為「未獲明確 correct」，揭示參考答案並前進，避免學生被系統故障卡住。
        """
        self.state["walkthrough_review"] = None
        if not self.backstop:
            self.state["walkthrough_review_status"] = "disabled"
            return None
        try:
            from review_backstop import judge_walkthrough_answer
        except ImportError:
            self.state["walkthrough_review_status"] = "unavailable"
            return None
        result = judge_walkthrough_answer(
            self.problem["statement"], self.problem["reference_proof"],
            step, student_text)
        self.state["walkthrough_review"] = result
        self.state["walkthrough_review_status"] = (
            result.get("verdict") if result else "unavailable")
        return result

    def _get_ladder_hint(self, level: int) -> str | None:
        """根據題目配置或 hint_ladders.json 庫取得當前等級的提示內容。"""
        en = self.lang == "en"
        pid = self.problem.get("id")
        
        # 1. 優先從 problem 字典取得
        ladder = self.problem.get("hint_ladder_en" if en else "hint_ladder")
        
        # 2. 若無，嘗試從 hint_ladders.json / hint_ladders_en.json 讀取
        if not ladder and pid:
            ladder_file = HERE / ("hint_ladders_en.json" if en else "hint_ladders.json")
            if ladder_file.exists():
                try:
                    all_ladders = json.loads(ladder_file.read_text(encoding="utf-8"))
                    ladder = all_ladders.get(pid)
                except Exception:
                    ladder = None
        
        if ladder and isinstance(ladder, list) and len(ladder) > 0:
            if level == 1:
                # Level 1: 若梯子有 2 條以上，取第 0 條作為局部子問題方向
                if len(ladder) >= 2:
                    return str(ladder[0]).strip()
            elif level == 2:
                # Level 2: 取第 1 條（或最新梯次）作為關鍵突破口
                idx = min(self.state.get("ladder_idx", 1), len(ladder) - 1)
                hint = str(ladder[idx]).strip()
                self.state["ladder_idx"] = min(idx + 1, len(ladder) - 1)
                return hint

        return None

    def _system(self, level: int) -> str:
        en = self.lang == "en"
        phase = self.state.get("phase")
        action = self.state.get("turn_action", "normal_guide")
        # 同學模式：無參考解，同儕 persona（質疑輪加反省指示）
        if self.is_peer():
            peer_sys = PEER_SYSTEM_EN if en else PEER_SYSTEM
            if action == "peer_reflect":
                reflect = PEER_REFLECT_INSTRUCTION_EN if en else PEER_REFLECT_INSTRUCTION
                return peer_sys + "\n\n" + reflect
            return peer_sys
        base = BASE_SYSTEM_EN if en else BASE_SYSTEM
        phase_map = PHASE_INSTRUCTIONS_EN if en else PHASE_INSTRUCTIONS
        action_map = TURN_ACTION_INSTRUCTIONS_EN if en else TURN_ACTION_INSTRUCTIONS
        level_map = LEVEL_INSTRUCTIONS_EN if en else LEVEL_INSTRUCTIONS
        sys_txt = base.format(proof=self.problem["reference_proof"])
        # phase == "walkthrough" 不會走到這裡：教學輪由 _walkthrough_reply() 確定性產出，
        # 完全不呼叫生成模型（見 WALKTHROUGH_TEMPLATE 的說明）。
        if action in action_map:
            instr = action_map[action]
            if action == "respond_attempt":
                instr += self._backstop_block()
        elif phase in {"review", "closed"}:    # 持久工作流指示優先
            instr = phase_map[phase]
            if phase == "review":
                instr += self._backstop_block()
        else:
            ladder_hint = self._get_ladder_hint(level)
            if level == 1 and ladder_hint:
                instr = (
                    f"This turn: the student just failed to answer. Guide the student using this sub-question direction: '{ladder_hint}'. Still do not directly name any theorem."
                    if en else
                    f"本輪指示：學生剛才答不出來。請參考以下子問題方向引導學生：『{ladder_hint}』。仍然不要直接點名定理名稱，只問一個具體子問題。"
                )
            elif level == 2 and ladder_hint:
                instr = (
                    f"This turn: the student has now failed twice on the same part of the derivation. In the first sentence, explicitly point out the key direction or construct: '{ladder_hint}'; do not write out the subsequent algebraic derivations or final conclusion. In the second sentence, ask exactly one concrete question that lets the student carry out the next step themselves."
                    if en else
                    f"本輪指示：學生已第二次無法回答同一段推導。第一句明確點出關鍵方向或構造：『{ladder_hint}』；不得替學生代寫後續運算推導，不得給出最終結論。第二句只問一個具體問題，讓學生自己動手執行下一步推導。"
                )
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
        return self._raw_generate(msgs, self.max_new_tokens)

    def _regen_budget_left(self) -> bool:
        """本輪「品質類」重生成的配額是否還有剩（安全閥，見 _MAX_REGEN_PER_TURN）。"""
        return self.state.get("_regens", 0) < _MAX_REGEN_PER_TURN

    def _regen(self, level: int, note: str) -> str:
        """以加強約束的 system 重生成一次（greedy 下改變輸入才會改變輸出）。"""
        self.state["_regens"] = self.state.get("_regens", 0) + 1
        stronger = self._system(level) + f"\n（注意：{note}）"
        msgs = [{"role": "system", "content": stronger}] + self.messages
        return enforce_single_question(self._raw_generate(msgs, self.max_new_tokens))

    def _allowed_equation_src(self) -> str:
        """等級 2 算式檢查的白名單來源：題目敘述＋學生說過的話。"""
        student = "".join(m["content"] for m in self.messages if m["role"] == "user")
        return self.problem["statement"] + student

    def _has_new_math(self, student_text: str) -> bool:
        """學生這則訊息有沒有帶進「先前學生發言與題目中尚未出現過」的數學內容。
        
        排除所有 assistant／Tutor 訊息，避免 Tutor 先前給過提示導致學生後續親自推導被判定為無新內容。
        """
        student_prior = self.problem.get("statement", "") + "".join(
            str(m.get("content") or "") for m in self.messages if m.get("role") == "user"
        )
        return has_new_math(student_text, student_prior)

    def _is_stuck_now(self, student_text: str) -> bool:
        """相容介面：讀取本輪統一路由器的 learning_state。"""
        if self.state.get("student_state_text") != student_text:
            self._route_student_state(student_text)
        decision = self.state.get("student_state_decision") or {}
        return decision.get("learning_state") == "stuck"

    def _last_message(self, role: str) -> str:
        return next((str(m.get("content") or "") for m in reversed(self.messages)
                     if m.get("role") == role), "")

    def _asks_specific_math_question(self, text: str) -> bool:
        """辨識具體釐清問題；「再給提示／怎麼辦」這類泛求助不算。"""
        t = (text or "").strip()
        # 中英文都常以祈使句提出明確釐清（「請解釋為什麼…」），
        # 或指明「已知 A、目標 B，詢問 A 如何到 B」的局部橋接問題（「我不知道要怎麼從 A 推導到 B」）。
        # 不應要求必須有問號才能被認出。這裡辨識的是「請求解釋一個具體數學對象或推理連結」的語法角色，不綁定題型。
        bridging_request = bool(re.search(
            r"(?:不知(?:道|得)|不清楚|不懂|請教|想知道|請(?:問|解釋|說明))?.{0,10}"
            r"(?:如何|怎麼|怎樣)?(?:從|由|將|把)\s*.{1,30}\s*(?:推導|推出|推到|得出|得到|化簡到|連接到|導出|變成|證明出|走到|過渡到)\s*.{1,30}|"
            r"(?:how|how to|how do (?:we|i)|cannot see how to|not sure how to|do not see how to|don't know how to|don't see how to).{0,20}"
            r"(?:get|derive|obtain|deduce|go|transition|connect)\s+(?:.{1,30}\s+from\s+.{1,30}|from\s+.{1,30}\s+to\s+.{1,30})",
            t, re.I
        ))
        explanatory_request = bool(re.search(
            r"(?:(?:請|麻煩|能否|可以).{0,10})?(?:解釋|說明|釐清|告訴我).{0,12}"
            r"(?:為什麼|為何|如何|怎麼|哪個|何時|何處)|"
            r"(?:(?:please|can you|could you).{0,10})?(?:explain|clarify|show|tell).{0,20}"
            r"(?:why|how|which|when|where)", t, re.I))
        if not _QMARK_RE.search(t) and not explanatory_request and not bridging_request:
            return False
        if re.fullmatch(
                r"\s*(我)?(不會|不知道|不懂|沒想法).{0,10}(怎麼辦|可以嗎|嗎)?[?？]?\s*",
                t, re.I):
            return False
        generic = re.search(
            r"再.{0,5}(提示|講一次)|給我.{0,5}提示|下一步(是什麼|怎麼做)|"
            r"(?:give|show) me (?:a |the |another |more )?(?:first )?hint|"
            r"(?:first|another|more) hints?|what (do i do|next)", t, re.I)
        concrete = re.search(
            r"為什麼|如何由|哪個(定理|條件|前提|符號)|這裡.{0,8}(為什麼|怎麼|如何)|"
            r"定理|定義|前提|條件|符號|等式|不等式|導數|積分|極限|"
            r"why|how does|which (theorem|condition)|what does.{0,12}mean|"
            r"[εδ]|\\(?:epsilon|delta)|\b[a-zA-Z]\b", t, re.I)
        return bool((concrete or bridging_request) and not generic)

    def _is_direct_response_candidate(self, text: str) -> bool:
        """上一問要求短答時，辨認學生確實有作答；不在此判斷答案正誤。"""
        t = (text or "").strip()
        last_tutor = self._last_message("assistant")
        if (not t or len(t) > 160 or not _QMARK_RE.search(last_tutor)
                or _QMARK_RE.search(t)):
            return False
        if (_STRONG_STUCK_RE.search(t) or _STUCK_RE.search(t)
                or _STUCK_EN_RE.search(t)
                or requests_tutor_to_supply_solution(t)
                or _UNDERSTOOD_RE.search(t) or _CHALLENGE_RE.search(t)):
            return False
        # 題型無關的「回答形狀」：數值／算式、定理或定義名稱、因果理由、
        # 是非與符號短答。它只表示學生嘗試回應上一問，因此錯答也會中斷卡住。
        return bool(re.search(
            r"[$\\=<>≤≥∈+*/^]|\d|"
            r"因為|由於|所以|故|定理|定義|性質|假設|條件|"
            r"^(?:是|否|對|錯|正|負|非負|非正)(?:數|的)?[。.!]?$|"
            r"because|since|therefore|theorem|definition|property|assumption|"
            r"^(?:yes|no|true|false|positive|negative|nonnegative|nonpositive)[.!]?$",
            t, re.I))

    def _student_state_context(self, student_text: str) -> dict:
        """把現有高精度訊號集中成 router 所需的唯讀 context。"""
        t = (student_text or "").strip()
        explicit_stuck = bool(_STRONG_STUCK_RE.search(t)
                              or _STUCK_RE.search(t) or _STUCK_EN_RE.search(t))
        complete_shape = self._looks_like_complete_proof(t)
        cur_math = math_text(t)
        # 學生所有權與重複判定只比較題目與學生自己的歷史發言（student-only），
        # 徹底排除 Tutor 先前提示過的式子與結論，避免污染學生親自推導的進度與所有權。
        prior = self.problem.get("statement", "") + "".join(
            str(m.get("content") or "") for m in self.messages if m.get("role") == "user"
        )
        prior_math = math_text(prior)
        repeats_prior = bool(cur_math and len(cur_math) >= _MATH_MIN_CHARS
                             and cur_math in prior_math)
        previous_student = self._last_message("user")
        if not repeats_prior and len(t) >= 12 and previous_student:
            import difflib
            repeats_prior = difflib.SequenceMatcher(
                None, _normalize(t), _normalize(previous_student)).ratio() >= 0.90
        attempt_content = bool(re.search(
            r"我(想|猜|試著|打算|認為)|我(用|使用|利用|套用|設|令|取|考慮)|"
            r"(?:我)?先(用|使用|利用|套用|設|令|取|考慮)|"
            r"可以(用|使用|利用|套用|設|令)|"
            r"try|i (think|guess|would|will)|start by|use (the|a)?|apply (the|a)?",
            t, re.I) and re.search(
            r"定理|定義|反證|歸納|函數|導數|積分|極限|不等式|等式|"
            r"展開|化簡|代入|比較|上界|下界|界限|"
            r"theorem|definition|contradiction|induction|function|derivative|"
            r"integral|limit|inequal|equation|expand|simplif|substitut|compare|bound|"
            r"[$\\=<>≤≥∈]", t, re.I))
        draft_signal = bool(_DRAFT_RE.search(t))
        goal_restatement = bool(
            draft_signal and cur_math and not complete_shape)
        math_reasoning = bool(
            (cur_math or re.search(r"[$\\=<>≤≥∈+\-*/^_{}]", t)) and
            re.search(
                r"因為|所以|因此|由此|故|則|可得|可知|成立|滿足|代入|得出|得到|推導|根據|由.+定理|"
                r"連續|可微|導函數|導數|積分|極限|收斂|絕對收斂|發散|有界|零點|大於|小於|等於|"
                r"because|therefore|hence|since|thus|we have|substitut|obtain|derive|by .+ theorem|"
                r"continuous|differentiable|derivative|integral|limit|converge|diverge|bounded|zero",
                t, re.I
            )
        )
        return {
            "peer": self.is_peer(),
            "phase": self.state.get("phase"),
            "walk_active": self.state.get("phase") == "walkthrough",
            "review_active": (self.state.get("phase") == "review"
                              and self.state.get("review_status") == "correcting"),
            "awaiting_clean_proof": (self.state.get("phase") == "review"
                                     and self.state.get("review_status") == "awaiting_clean"),
            "done_closed": self.state.get("phase") == "closed",
            "writeup_asked": (self.state.get("phase") == "review"
                              and self.state.get("review_status") == "awaiting_submission"),
            "has_recent_proof": bool(self.state.get("current_proof_draft")),
            "explicit_full_proof": self._is_full_proof_submission(t),
            "complete_shape": complete_shape,
            "draft_signal": draft_signal,
            "demand": requests_tutor_to_supply_solution(t),
            "student_requests_writeup": student_requests_to_submit_proof(t),
            "requested_writer": (
                "tutor" if requests_tutor_to_supply_solution(t) else
                "student" if student_requests_to_submit_proof(t) else "none"),
            "attempt": bool(_ATTEMPT_RE.search(t)),
            "attempt_content": attempt_content,
            "math_reasoning": math_reasoning,
            "understood": bool(_UNDERSTOOD_RE.search(t)),
            "understood_whole": bool(_UNDERSTOOD_WHOLE_RE.search(t)),
            "claim_done": bool(_CLAIM_DONE_RE.search(t)),
            "challenge": bool(_CHALLENGE_RE.search(t)),
            "assertive_challenge": bool(_ASSERTIVE_CHALLENGE_RE.search(t)),
            "missed_review": bool(_MISSED_REVIEW_RE.search(t)),
            "nonassertive_review_confirmation": _is_nonassertive_review_confirmation(t),
            "explicit_stuck": explicit_stuck,
            "strong_stuck": bool(_STRONG_STUCK_RE.search(t)),
            "has_new_math": self._has_new_math(t),
            "asks_specific_question": self._asks_specific_math_question(t),
            "direct_response_candidate": self._is_direct_response_candidate(t),
            "goal_restatement": goal_restatement,
            "repeats_prior_math": repeats_prior,
            "last_tutor_question": self._last_message("assistant"),
            "previous_student_text": self._last_message("user"),
            "stuck_count": int(self.state.get("stuck_count", 0)),
            "language": self.lang,
        }

    def _route_student_state(self, student_text: str):
        """只在此處呼叫統一 router，並保存可診斷的完整決策。"""
        try:
            from phase_router import route_student_state
        except ImportError:                       # 套件匯入時的相對路徑
            from .phase_router import route_student_state
        decision = route_student_state(
            student_text, self._student_state_context(student_text),
            thinking_enabled=self.backstop)
        self.state["student_state_text"] = student_text
        self.state["student_state_decision"] = decision.to_dict()
        self.state["turn_action"] = decision.turn_action
        self.state["mode"] = "peer" if self.is_peer() else "tutor"
        return decision

    def _update_stuck_from_decision(self) -> None:
        """phase gate 後，集中更新一次 stuck_count。"""
        try:
            from phase_router import update_stuck_count
        except ImportError:
            from .phase_router import update_stuck_count
        decision = self.state.get("student_state_decision") or {}
        self.state["stuck_count"] = update_stuck_count(
            self.state.get("stuck_count", 0),
            str(decision.get("learning_state") or "uncertain"),
            answers_current_question=decision.get("answers_current_question"),
            has_actionable_math=bool(decision.get("has_actionable_math")),
            advances_solution=decision.get("advances_solution"))
        # 只計「學生帶入新的可操作數學內容」，作為 readiness 的廉價前置閘。
        # 正誤仍交給 Thinking；此計數本身不會切 phase。
        if (decision.get("has_actionable_math")
                and decision.get("advances_solution") is True
                and self.state.get("phase") == "guide"):
            self.state["proof_progress_revision"] = (
                int(self.state.get("proof_progress_revision", 0)) + 1)

    def _judge_writeup_readiness(self, candidate_reply: str = "") -> bool:
        """由 Thinking 判斷一般引導是否已涵蓋完整證明骨架。

        這個判斷只決定「系統能否主動請學生交稿」，不接受學生一句「我懂了」
        直接控制 phase。Thinking 失敗時只允許高精度的對話結構保底，不會因一句
        「我懂了」或單一步驟肯定而放行。
        """
        if (self.is_peer() or not self.backstop
                or self.state.get("phase") != "guide"):
            return False
        check_key = self._writeup_readiness_key()
        try:
            try:
                from review_backstop import _retry_parsed
            except ImportError:
                from .review_backstop import _retry_parsed
            payload = {
                "problem": self.problem.get("statement", ""),
                "reference_proof": self.problem.get("reference_proof", ""),
                "conversation": self.messages[-16:],
                "candidate_tutor_reply": candidate_reply,
            }
            system = (
                "你是幕後的交稿準備度審查器。比較對話與參考證明，只判斷學生是否已在"
                "引導中親自提出或正確確認所有不可缺少的證明環節。不要因學生說『懂了』、"
                "Tutor 給總評或訊息很長就判通過；仍有未解問題、錯誤或缺少核心連結時必須"
                "判 false。只輸出 JSON：{\"ready_for_writeup\":true/false,"
                "\"missing_core_step\":\"缺少內容或空字串\",\"confidence\":0到1,"
                "\"reason\":\"簡短理由\"}。"
            )
            def parse_readiness(raw: str) -> dict | None:
                cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip(),
                                 flags=re.I | re.S)
                objects = re.findall(r"\{[^{}]*\}", cleaned, re.S)
                for candidate in reversed(objects or [cleaned]):
                    try:
                        value = json.loads(candidate)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if (isinstance(value, dict)
                            and isinstance(value.get("ready_for_writeup"), bool)):
                        return value
                return None

            timeout = max(60, int(os.environ.get("WRITEUP_READINESS_TIMEOUT", "120")))
            data = _retry_parsed(
                system, json.dumps(payload, ensure_ascii=False), parse_readiness,
                timeout=timeout,
                num_predict=max(4096, int(os.environ.get(
                    "WRITEUP_READINESS_NUM_PREDICT", "4096"))),
                temperature=0.0, attempts=2)
            if data is None:
                raise RuntimeError("writeup readiness judge unavailable")
            ready = data.get("ready_for_writeup") is True
            missing = str(data.get("missing_core_step") or "").strip()
            confidence = float(data.get("confidence", 0.0))
            result = {
                "ready_for_writeup": bool(ready and not missing and confidence >= 0.80),
                "missing_core_step": missing,
                "confidence": max(0.0, min(1.0, confidence)),
                "reason": str(data.get("reason") or "").strip(),
                "source": "thinking",
            }
        except Exception:
            result = {
                "ready_for_writeup": False,
                "missing_core_step": "",
                "confidence": 0.0,
                "reason": "readiness_judge_unavailable",
                "source": "unavailable",
            }
        self.state["writeup_readiness"] = result
        if result.get("source") == "unavailable":
            # 服務失敗不是數學判定，不能像正常的 false 一樣快取。留下 pending，
            # 讓下一輪即使只有「清楚了」而沒有新算式，也能重試同一份累積對話。
            self.state["readiness_pending"] = True
            self.state.pop("writeup_readiness_check_key", None)
        else:
            self.state["readiness_pending"] = False
            self.state["writeup_readiness_check_key"] = check_key
        return bool(result["ready_for_writeup"])

    def _writeup_readiness_key(self) -> str:
        """同一份數學進度只審一次；有新實質進展時自然換 key。"""
        revision = int(self.state.get("proof_progress_revision", 0))
        last_user = _normalize(self._last_message("user"))[-400:]
        return f"{revision}:{last_user}"

    def _should_check_writeup_readiness(self, candidate_reply: str = "") -> bool:
        """引導進度寬度閘；達門檻後由 Controller 主動重判累積對話。

        ``backstop_gaps`` 只描述學生本輪局部回答缺少的內容，不能代表
        累積對話尚未形成完整證明骨架；是否可進入全文撰寫應交由看過
        累積對話的 readiness judge 判定。達到基本進度後，每則新的學生訊息都重查；
        不再依賴 router 的 ``advances_solution``，避免一則完整訂正被降級成 uncertain
        後沿用上一輪已過期的 readiness=false。
        """
        if (self.is_peer() or not self.backstop
                or self.state.get("phase") != "guide"):
            return False
        revision = int(self.state.get("proof_progress_revision", 0))
        if revision < 2:
            return False
        # key 包含最後一則學生訊息；同一輪不重複呼叫，新一輪則不論 router
        # 判成 progress／clarification／uncertain 都交由 readiness 本身判斷完整性。
        return self.state.get("writeup_readiness_check_key") != self._writeup_readiness_key()

    def _review_guide_reply(self, reply: str, level: int) -> dict | None:
        """用同一個語意審查器檢查所有 Tutor guide action 的最終候選。

        這裡刻意不建立題型專屬 proof graph，也不靠關鍵詞列表猜教學層級；Thinking
        直接比較題目、參考證明、累積對話與候選回覆，只回傳通用布林判準。
        """
        if (self.is_peer() or not self.backstop
                or self.state.get("phase") != "guide"):
            return None
        call_diagnostics: dict = {}
        try:
            try:
                from review_backstop import _parse_any_object, _retry_parsed
            except ImportError:
                from .review_backstop import _parse_any_object, _retry_parsed

            payload = {
                "problem": self.problem.get("statement", ""),
                "reference_proof": self.problem.get("reference_proof", ""),
                "conversation": self.messages[-16:],
                # 所有權與 readiness 只看學生親口寫過的內容；Tutor 的提示只能提供
                # 對話背景，不能被誤算成學生已提出的證明想法或完成步驟。
                "student_messages": [
                    str(message.get("content") or "")
                    for message in self.messages
                    if message.get("role") == "user"
                ][-16:],
                "level": int(level),
                "turn_action": self.state.get("turn_action"),
                "student_state": self.state.get("student_state_decision") or {},
                "readiness_eligible": (
                    int(self.state.get("proof_progress_revision", 0)) >= 2),
                "candidate_tutor_reply": reply,
            }
            system = (
                "你是幕後的蘇格拉底式引導與交稿準備度合併審查器，只做審查、不要解題。"
                "請比較題目、參考證明、對話、student_messages 與候選回覆，依序完成："
                "(1)核對 student_messages 最後一則中的數學步驟狀態 (latest_student_step_status: correct/incorrect/no_step) 與第一個缺少連結 (first_missing_step)。"
                "(2)核對 Tutor 候選回覆：\n"
                "   - mathematically_correct 只評 Tutor 候選內的數學敘述，以及 Tutor 對最新學生步驟的處理。最新學生步驟若錯，而 Tutor 稱讚、接受、沿用或跳過它，必須判 false；若 Tutor 不斷言錯誤，只用聚焦問題要求學生重查該步，則可判 true。學生的證明尚未完整，本身絕不能成為 mathematically_correct=false 的理由；候選中若包含符號、常數、正負號、導數階數、不等號或等式推導錯誤，填入 candidate_math_error，否則填空字串。重述題目結論必須與題目數學等價。\n"
                "   - 是否假定、宣稱或沿用學生尚未親自完成的步驟 (candidate_ownership_error: 若 Tutor 宣稱「你自己已算出/證明了某事」但學生在 student_messages 中未曾算出，填具體主張；否則填空字串)。\n"
                "   - 是否真正承接並回應最新學生步驟 (addresses_latest_student_step: boolean)。若學生剛答對，Tutor 應簡短確認該步並引導至第一個缺口；若學生答錯，應聚焦引導修正該步；若學生卡住/提問，應引導目前缺口。若學生提出具體步驟，Tutor 卻只說「你想從哪個方向試試看」等空泛無關問句，必須為 false。\n"
                "   - completes_any_unfinished_step 不只包含 Tutor 直接斷言、計算或推導任何學生尚未完成的中間步驟；也包含假定該步已完成、稱讚錯誤步驟、沿用錯誤結果，或跳過第一個缺口而前往更後面的步驟。即使 Tutor 後面仍留下一個問題，也必須判 true。\n"
                "   - 是否洩漏題目最終結論 (leaks_final_conclusion: boolean)。\n"
                "   - level_policy_pass: boolean。\n"
                "(3)獨立判斷學生整體證明是否已可交稿 (ready_for_writeup, missing_core_step, readiness_confidence, feedback)。\n"
                "下列規則與題型無關。normal_guide 才使用 level：\n"
                "L0：只問一個聚焦問題，不可替學生新增定理、技巧、構造或證明步驟。\n"
                "L1：只把上一問縮小成更具體的子問題，仍不可新增定理、公式或結果。\n"
                "L2：只點出緊接學生已完成內容之後的一個定理、技巧或概念方向，不可寫出新的"
                "等式、計算結果或更後面的步驟；必須用一個具體問題把執行交回學生。\n"
                "respond_attempt：只能肯定學生已親自完成且正確的部分，再問第一個缺少的連結；"
                "不可引入 student_messages 尚未出現的新定理、輔助物件、構造或策略，也不可替"
                "學生斷言或推導尚未完成的連結。answer_clarification：只回答學生明確詢問的"
                "局部連結，回答必須正確，不可順便完成後續推導或最終結論，再把下一步交回學生。"
                "refuse_tutor_write：必須拒絕代寫，不可提供證明步驟、算式或結論，並用一個問題"
                "把主導權還給學生。\n"
                "判斷『學生已提出／已完成』時，只能以 student_messages 為證據；conversation 裡"
                "Tutor 說過的提示、候選回覆及參考證明只可用於理解順序或核對正確性，絕不能取得學生所有權。\n"
                "只輸出 JSON，且恰有："
                "{\"latest_student_step_status\":\"correct|incorrect|no_step\","
                "\"first_missing_step\":\"第一個缺少連結或空字串\","
                "\"candidate_math_error\":\"候選中的數學錯誤或空字串\","
                "\"candidate_ownership_error\":\"所有權假定錯誤或空字串\","
                "\"addresses_latest_student_step\":true/false,"
                "\"mathematically_correct\":true/false,\"level_policy_pass\":true/false,"
                "\"introduces_new_proof_idea\":true/false,"
                "\"completes_any_unfinished_step\":true/false,"
                "\"leaks_final_conclusion\":true/false,\"ready_for_writeup\":true/false,"
                "\"missing_core_step\":\"缺少內容或空字串\",\"readiness_confidence\":0到1,"
                "\"feedback\":\"簡短原因\"}。"
            )

            review_schema = {
                "type": "object",
                "properties": {
                    "latest_student_step_status": {
                        "type": "string",
                        "enum": ["correct", "incorrect", "no_step"]
                    },
                    "first_missing_step": {"type": "string"},
                    "candidate_math_error": {"type": "string"},
                    "candidate_ownership_error": {"type": "string"},
                    "addresses_latest_student_step": {"type": "boolean"},
                    "mathematically_correct": {"type": "boolean"},
                    "level_policy_pass": {"type": "boolean"},
                    "introduces_new_proof_idea": {"type": "boolean"},
                    "completes_any_unfinished_step": {"type": "boolean"},
                    "leaks_final_conclusion": {"type": "boolean"},
                    "ready_for_writeup": {"type": "boolean"},
                    "missing_core_step": {"type": "string"},
                    "readiness_confidence": {
                        "type": "number", "minimum": 0, "maximum": 1},
                    "feedback": {"type": "string"},
                },
                "required": [
                    "latest_student_step_status", "first_missing_step",
                    "candidate_math_error", "candidate_ownership_error",
                    "addresses_latest_student_step", "mathematically_correct",
                    "level_policy_pass", "introduces_new_proof_idea",
                    "completes_any_unfinished_step", "leaks_final_conclusion",
                    "ready_for_writeup", "missing_core_step",
                    "readiness_confidence", "feedback",
                ],
                "additionalProperties": False,
            }

            def parse_review(raw: str) -> dict | None:
                value = _parse_any_object(raw or "")
                if not isinstance(value, dict):
                    return None
                bool_keys = ("addresses_latest_student_step", "mathematically_correct",
                             "level_policy_pass", "introduces_new_proof_idea",
                             "completes_any_unfinished_step",
                             "leaks_final_conclusion", "ready_for_writeup")
                # 相容舊測試與呼叫：若缺欄位給予合理預設值
                value.setdefault("addresses_latest_student_step", True)
                value.setdefault("candidate_math_error", "")
                value.setdefault("candidate_ownership_error", "")
                value.setdefault("latest_student_step_status", "no_step")
                value.setdefault("first_missing_step", "")
                if not all(isinstance(value.get(key), bool) for key in bool_keys):
                    return None
                if (not isinstance(value.get("feedback"), str)
                        or not isinstance(value.get("missing_core_step"), str)
                        or not isinstance(value.get("readiness_confidence"), (int, float))):
                    return None
                return {key: value[key] for key in bool_keys} | {
                    "latest_student_step_status": str(value.get("latest_student_step_status") or "no_step").strip()[:50],
                    "first_missing_step": str(value.get("first_missing_step") or "").strip()[:500],
                    "candidate_math_error": str(value.get("candidate_math_error") or "").strip()[:500],
                    "candidate_ownership_error": str(value.get("candidate_ownership_error") or "").strip()[:500],
                    "missing_core_step": value["missing_core_step"].strip()[:500],
                    "readiness_confidence": max(
                        0.0, min(1.0, float(value["readiness_confidence"]))),
                    "feedback": value["feedback"].strip()[:500],
                }

            # 每次合併審查都保留完整 120 秒；環境變數只能放寬，不能把單次預算縮回 60 秒。
            timeout = max(120, int(os.environ.get("GUIDE_REPLY_REVIEW_TIMEOUT", "120")))
            result = _retry_parsed(
                system, json.dumps(payload, ensure_ascii=False), parse_review,
                timeout=timeout,
                num_predict=max(8192, int(os.environ.get(
                    "GUIDE_REPLY_REVIEW_NUM_PREDICT", "8192"))),
                temperature=0.0, attempts=1, per_attempt_timeout=timeout,
                response_format=review_schema, diagnostics=call_diagnostics)
            if not call_diagnostics:
                call_diagnostics.update(
                    status="parsed" if result is not None else "failed",
                    failure_reason=None if result is not None else "unknown")
            self.state["_last_guide_review_call"] = call_diagnostics
            return result
        except Exception as exc:
            call_diagnostics.update(
                status="failed", failure_reason="driver_exception",
                exception_type=type(exc).__name__)
            self.state["_last_guide_review_call"] = call_diagnostics
            return None

    def _guide_action_forbids_new_idea(self, level: int) -> bool:
        """L0/L1 與 respond_attempt 都必須把下一個新想法留給學生。"""
        action = self.state.get("turn_action")
        return action == "respond_attempt" or (action == "normal_guide" and level < 2)

    def _guide_reply_review_passes(self, review: dict | None, level: int) -> bool:
        if not review:
            return False
        # P0-4: 候選含有具體數學錯誤（如錯號、錯等式、錯目標）時退件
        if review.get("candidate_math_error"):
            return False
        if review.get("mathematically_correct") is False:
            return False
            
        # P0-4: 候選含有錯誤所有權歸因（把 Tutor 先前提示當成學生已證明）時退件
        if review.get("candidate_ownership_error"):
            return False
            
        # P0-3: 學生有具體步驟時，候選必須正向承接，不得輸出脫節空泛問句
        step_status = str(review.get("latest_student_step_status") or "")
        if step_status in ("correct", "incorrect"):
            if review.get("addresses_latest_student_step") is False:
                return False
                
        # 禁止代寫與洩漏最終結論
        if review.get("completes_any_unfinished_step") is True:
            return False
        if review.get("leaks_final_conclusion") is True:
            return False
            
        # 想法控制（L0/L1 與 respond_attempt 不得帶入學生未提出的新想法）
        level_idea_ok = not (
            self._guide_action_forbids_new_idea(level)
            and review.get("introduces_new_proof_idea") is True)
        if not level_idea_ok:
            return False
            
        # P1-1: 若數學正確、所有權安全、正向承接且無洩漏，單純 level_policy_pass=false
        # 暫時不單獨作為退件理由，避免抹煞高品質提示退回通用保底句
        return True

    def _combined_readiness_ready(self, review: dict) -> bool:
        """保存合併審查中的 readiness；基本進度未達門檻時忽略該欄位。"""
        if int(self.state.get("proof_progress_revision", 0)) < 2:
            return False
        missing = str(review.get("missing_core_step") or "").strip()
        confidence = float(review.get("readiness_confidence", 0.0))
        ready = bool(review.get("ready_for_writeup") is True
                     and not missing and confidence >= 0.80)
        self.state["writeup_readiness"] = {
            "ready_for_writeup": ready,
            "missing_core_step": missing,
            "confidence": max(0.0, min(1.0, confidence)),
            "reason": str(review.get("feedback") or "").strip(),
            "source": "combined_guide_review",
        }
        self.state["readiness_pending"] = False
        self.state["writeup_readiness_check_key"] = self._writeup_readiness_key()
        return ready

    def _mark_combined_review_unavailable(self) -> None:
        """合併審查兩次都不可用時，readiness 保持 pending、下一輪再試。"""
        if int(self.state.get("proof_progress_revision", 0)) < 2:
            return
        self.state["writeup_readiness"] = {
            "ready_for_writeup": False,
            "missing_core_step": "",
            "confidence": 0.0,
            "reason": "combined_guide_review_unavailable",
            "source": "unavailable",
        }
        self.state["readiness_pending"] = True
        self.state.pop("writeup_readiness_check_key", None)

    def _safe_guide_review_fallback(self) -> str:
        """語意審查不可用或二稿仍失敗時，對齊審查器判定的上下文輸出安全保底回覆。"""
        en = self.lang == "en"
        if self.state.get("turn_action") == "refuse_tutor_write":
            return (
                "I can't write the proof for you. What is the last step you have established "
                "yourself?" if en else
                "我不能代寫完整證明。你目前自己已經確定的最後一步是什麼？")
                
        # P1-3: 若 Reviewer 已判斷出學生的步驟狀態與第一個缺口，優先使用對齊上下文的保底句
        rev = (self.state.get("guide_reply_review") or {}).get("initial") or {}
        step_status = str(rev.get("latest_student_step_status") or "")
        first_missing = str(rev.get("first_missing_step") or "").strip()
        
        if step_status == "correct" and first_missing:
            return (
                f"Good, that step is established. How do you connect this to establishing {first_missing}?"
                if en else
                f"很好，這一步是成立的。接下來你打算如何連接到「{first_missing}」？"
            )
        elif step_status == "incorrect":
            return (
                "Please carefully check the premise and reasoning of your last calculation."
                if en else
                "請仔細檢查你剛才計算或推導的依據與前提是否有誤？"
            )
        elif first_missing:
            return (
                f"Let's focus on the current gap: what idea can help establish {first_missing}?"
                if en else
                f"我們先聚焦在目前的缺口：你有什麼想法可以得出「{first_missing}」？"
            )

        pool = (_SAFE_GUIDE_REVIEW_FALLBACKS_EN if en
                else _SAFE_GUIDE_REVIEW_FALLBACKS)
        index = int(self.state.get("guide_safe_fb_idx", 0))
        self.state["guide_safe_fb_idx"] = index + 1
        return pool[index % len(pool)]

    def _final_guide_repeat_guard(self, reply: str, log: TurnLog) -> str:
        """合併審查後再做一次通用去重，涵蓋 Controller 安全保底。"""
        if (not self.backstop or self.is_peer()
                or self.state.get("phase") != "guide"
                or self.state.get("turn_action") == "refuse_tutor_write"
                or not self._repeats_previous(reply)):
            return reply
        log.guards.append("final_repeat")
        candidate = reply
        pool = (_SAFE_GUIDE_REVIEW_FALLBACKS_EN if self.lang == "en"
                else _SAFE_GUIDE_REVIEW_FALLBACKS)
        for _ in range(len(pool)):
            candidate = self._safe_guide_review_fallback()
            if not self._repeats_previous(candidate):
                break
        return candidate

    def _enforce_guide_reply_policy(self, reply: str, level: int,
                                    log: TurnLog) -> str:
        """一次合併審查 readiness 與 guide policy；整輪最多兩次 Thinking。"""
        if (self.is_peer() or not self.backstop
                or self.state.get("phase") != "guide"):
            return reply

        self.state.pop("_last_guide_review_call", None)
        first = self._review_guide_reply(reply, level)
        first_call = self.state.pop("_last_guide_review_call", None)
        diagnostic = {
            "initial": first, "initial_call": first_call,
            "retry": None, "retry_call": None,
            "regenerated": None, "regenerated_call": None,
            "status": "passed", "thinking_calls": 1,
        }
        self.state["guide_reply_review"] = diagnostic
        if first is None:
            # 服務／格式失敗才以同一候選重試一次；每次都保有完整 timeout。
            first = self._review_guide_reply(reply, level)
            diagnostic["retry_call"] = self.state.pop(
                "_last_guide_review_call", None)
            diagnostic["retry"] = first
            diagnostic["thinking_calls"] = 2
            if first is None:
                diagnostic["status"] = "unavailable"
                log.guards.append("guide_policy_unavailable")
                self._mark_combined_review_unavailable()
                return self._safe_guide_review_fallback()
            diagnostic["status"] = "retry_parsed"
            may_regenerate = False       # 已用完本輪兩次 Thinking 配額
        else:
            may_regenerate = True

        # readiness 優先：學生已走完骨架時直接用確定性交稿模板，不能再因「沒有下一問」
        # 被 guide policy 打回通用保底句。
        if self._combined_readiness_ready(first):
            diagnostic["status"] = "ready_for_writeup"
            log.guards.append("writeup_readiness")
            self._enter_awaiting_submission(
                event="READINESS_PASSED", source="combined_guide_review")
            return WRITEUP_FALLBACK_EN if self.lang == "en" else WRITEUP_FALLBACK

        if self._guide_reply_review_passes(first, level):
            if diagnostic["status"] == "retry_parsed":
                diagnostic["status"] = "passed_after_retry"
            return reply

        log.guards.append("guide_policy")
        if not may_regenerate:
            diagnostic["status"] = "unresolved"
            log.guards.append("guide_policy_unresolved")
            return self._safe_guide_review_fallback()

        feedback_parts = []
        fb = str(first.get("feedback") or "").strip()
        if fb:
            feedback_parts.append(fb)
        if first.get("candidate_math_error"):
            feedback_parts.append(f"修正候選中的數學錯誤：{first['candidate_math_error']}")
        elif first.get("mathematically_correct") is False:
            feedback_parts.append(
                "先核對最新學生數學步驟；若該步錯誤，不得稱讚、沿用或跳過，只能用聚焦問題"
                "請學生修正。學生尚未完成證明本身不代表 Tutor 的數學敘述錯誤")
        if first.get("candidate_ownership_error"):
            feedback_parts.append(f"修正所有權歸因錯誤：{first['candidate_ownership_error']}（不能把 Tutor 先前提過的結果說成學生已證明）")
        if first.get("addresses_latest_student_step") is False:
            feedback_parts.append("必須明確承接並回應學生最新提出的數學步驟，不得輸出脫離該步的空泛問句")
        if (self._guide_action_forbids_new_idea(level)
                and first.get("introduces_new_proof_idea") is True):
            feedback_parts.append("本輪不得提出學生尚未提出的新定理、輔助物件、構造或證明策略")
        if first.get("completes_any_unfinished_step") is True:
            feedback_parts.append("不得直接完成、假定完成、稱讚後跳過或沿用任何尚未完成／錯誤的中間步驟")
            
        feedback = "；".join(feedback_parts)
        en = self.lang == "en"
        note = (
            "The semantic policy review rejected the draft. Rewrite it once so the student must do "
            "the next inference themselves; make every mathematical statement correct, obey the "
            "current guide action and its level when applicable, address the student's latest step, "
            "and do not state the final conclusion. Review feedback: " + feedback if en else
            "語意政策審查未通過。只重寫一次：所有數學敘述都必須正確，嚴格遵守目前的 guide "
            "action（適用時也遵守 level），承接最新學生步驟，下一個推理必須由學生自己完成，不可說出最終結論。"
            "審查原因：" + feedback)
        regenerated = self._content_guards(self._regen(level, note), level, log)
        log.regenerated = True
        second = self._review_guide_reply(regenerated, level)
        diagnostic["regenerated_call"] = self.state.pop(
            "_last_guide_review_call", None)
        diagnostic["regenerated"] = second
        diagnostic["thinking_calls"] = 2
        if second is None:
            diagnostic["status"] = "recheck_unavailable"
            log.guards.append("guide_policy_recheck_unavailable")
            return self._safe_guide_review_fallback()

        if self._combined_readiness_ready(second):
            diagnostic["status"] = "ready_for_writeup"
            log.guards.append("writeup_readiness")
            self._enter_awaiting_submission(
                event="READINESS_PASSED", source="combined_guide_review")
            return WRITEUP_FALLBACK_EN if en else WRITEUP_FALLBACK

        if self._guide_reply_review_passes(second, level):
            diagnostic["status"] = "regenerated_passed"
            return regenerated

        # 第二稿仍明確不合格時不再賭第三次生成；使用不提供任何新證明內容的保守問句。
        # 這是服務／模型雙重失敗的安全出口，不含題型關鍵詞，也不碰 walkthrough。
        diagnostic["status"] = "unresolved"
        log.guards.append("guide_policy_unresolved")
        return self._safe_guide_review_fallback()

    def _enter_awaiting_submission(self, *, event: str, source: str) -> None:
        """readiness 或 walkthrough 完成後，進入 review 等待學生全文。"""
        self.state["readiness_pending"] = False
        self._apply_phase_event(event, source=source)

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
        step_sets = [self.problem.get("teach_steps") or [],
                     self.problem.get("teach_steps_zh") or [],
                     self.problem.get("teach_steps_en") or []]
        tails += [s["check"] for steps in step_sets for s in steps
                  if isinstance(s, dict) and s.get("check")]
        for tail in tails:
            if tail and t.endswith(tail):
                return t[: -len(tail)].rstrip()
        return t

    def _repeats_previous(self, reply: str) -> bool:
        """回覆是否重複最近 3 輪助教回覆：完全相同，或高度相似（換句話重問同一題）。

        相似度用 difflib ratio ≥0.85（正規化後）：抓「改寫式重問」——學生卡住時
        tutor 換個說法問一模一樣的問題，逐字比對抓不到。教學輪（walkthrough）由
        確定性模板產出，且確認問題只有一次作答機會，不需要相似度重講守衛。
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

        # on-track 防奉送：一般引導輪與拒絕輪（refuse_tutor_write 規則本就禁止給步驟），
        # 等級 <2 不得替學生指定具體代數操作
        if (level < 2 and phase == "guide"
                and self.state.get("turn_action") in {
                    "normal_guide", "refuse_tutor_write"}
                and is_spoonfeeding(reply)):
            log.guards.append("spoonfeed")
            reply = self._regen(level, (
                "Your previous draft prescribed a concrete algebraic operation (such as multiplying, "
                "subtracting, substituting). Rewrite: state no operation step; instead ask the "
                "student an open question like how they plan to proceed." if en else
                "上一稿替學生指定了具體代數操作（如左乘、相減、代入）。"
                "重寫：不要說出任何操作步驟，改問學生「打算怎麼處理」這類開放問題。"))
            log.regenerated = True

        # 等級 2 算式守衛：可給關鍵構造形態/定理方向，但不得直接代寫後續推導等式或結論
        if level == 2 and gives_new_equation(reply, self._allowed_equation_src()):
            log.guards.append("formula")
            reply = self._regen(level, (
                "Your previous draft wrote out subsequent derivation formulas or conclusions. Rewrite: "
                "state the theorem/technique name, conceptual direction, or auxiliary construct, "
                "and let the student carry out the algebraic derivation themselves." if en else
                "上一稿直接替學生寫出了推導算式或結論。重寫：只指出該步驟的定理／技巧名稱、"
                "核心想法或輔助構造形態，不要替學生代寫具體運算過程，讓學生自己動筆推導。"))
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

    def _raises_mono_quibble(self, reply: str) -> bool:
        """回覆是否在對一份已寫「單調不減」的正確證明糾結 increasing／nondecreasing。

        四道閘同時成立才算：審閱輪、題目沒寫 strictly、學生草稿已用非嚴格說法、
        回覆同時提到兩種說法且還在發問。任何一道不成立就放行——這道守衛擋的是
        「憑空發明的術語缺漏」，不是真的術語錯誤（題目寫 strictly 時就該糾正）。
        """
        if self.state.get("phase") != "review" or self.is_peer():
            return False
        if _STRICT_MONO_RE.search(self.problem.get("statement", "")):
            return False
        draft = next((m["content"] for m in reversed(self.messages)
                      if m["role"] == "user"), "")
        return bool(_NONDEC_TERM_RE.search(draft)
                    and _NONDEC_TERM_RE.search(reply) and _INC_TERM_RE.search(reply)
                    and _QMARK_RE.search(reply))

    def _terminology_guard(self, reply: str, level: int, log: TurnLog) -> str:
        """假術語缺漏攔截：先請模型重寫（帶上慣例），仍糾結就改用確定性收尾。

        走到最後那一步時，助教除了這個假缺漏之外沒挑出任何問題＝證明已經過關，
        與既有的「審閱輪回覆無問句 ⇒ arm done_closed」是同一個判準。
        """
        if not self._raises_mono_quibble(reply):
            return reply
        log.guards.append("terminology")
        en = self.lang == "en"
        reply = self._regen(level, (
            "Project convention: 'increasing' without 'strictly' means nondecreasing. The student's "
            "wording is precise, not a gap. Do not raise this terminology point; if there is no other "
            "gap, confirm the proof is complete." if en else
            "本專案慣例：題目未寫「嚴格遞增」時，「遞增」即單調不減，學生寫「單調不減」"
            "是精確表述、不是缺漏。不要再提這個術語問題；若沒有其他缺漏就確認證明完成。"))
        log.regenerated = True
        if self._raises_mono_quibble(reply):
            log.guards.append("terminology_unresolved")
            reply = REVIEW_PASS_EN if en else REVIEW_PASS
            self._apply_phase_event("REVIEW_PASSED", source="review_terminology_guard")
        return reply

    def _tutor_turn(self) -> str:
        level = min(self.state["stuck_count"], 2)
        phase = self.state.get("phase")
        en = self.lang == "en"
        peer = self.is_peer()
        walkthrough = phase == "walkthrough" and not peer
        self.state["_regens"] = 0          # 本輪重生成配額歸零（見 _MAX_REGEN_PER_TURN）
        last_user = next((m["content"] for m in reversed(self.messages)
                          if m["role"] == "user"), "")

        # 逐步教學：確定性輸出，完全不經生成模型與各道重生成守衛
        # （內容是預寫的教學步驟，本來就允許寫式子；問句就是該步的確認問題）。
        if walkthrough:
            if self.state.get("turn_action") == "refuse_tutor_write":
                reply = WALK_REFUSE_WRITE_EN if en else WALK_REFUSE_WRITE
                guards = ["walkthrough_refuse"]
            else:
                reply = self._walkthrough_reply()
                guards = ["walkthrough_step"]
            log = TurnLog(level=level, stuck_count=self.state["stuck_count"],
                          guards=guards)
            self.state["turns"].append(log)
            self.messages.append({"role": "assistant", "content": reply})
            return reply

        # 審閱通過：後盾逐步複核回報「無缺漏」→ 確定性收尾，不讓模型自由發揮
        # （憑空發明缺漏、或確認完成後又追問下一步，實測都出現過）。
        if not peer and phase == "review" and self.state.get("backstop_gaps") == []:
            reply = REVIEW_PASS_EN if en else REVIEW_PASS
            self._apply_phase_event("REVIEW_PASSED", source="review_backstop")
            log = TurnLog(level=level, stuck_count=self.state["stuck_count"],
                          guards=["backstop", "review_pass"])
            self.state["turns"].append(log)
            self.messages.append({"role": "assistant", "content": reply})
            return reply

        # readiness 或 walkthrough 通過後，Controller 在同一輪主動要求交稿。
        if phase == "review" and self.state.get("review_status") == "awaiting_submission":
            reply = WRITEUP_FALLBACK_EN if en else WRITEUP_FALLBACK
            if self.state.get("walk_feedback"):
                reply = self.state.pop("walk_feedback") + " " + reply
            log = TurnLog(level=level, stuck_count=self.state["stuck_count"],
                          guards=["awaiting_submission"])
            self.state["turns"].append(log)
            self.messages.append({"role": "assistant", "content": reply})
            return reply

        reply = enforce_single_question(self._generate(level))

        log = TurnLog(level=level, stuck_count=self.state["stuck_count"])
        if (phase == "review" or self.state.get("turn_action") == "respond_attempt") \
                and self.state.get("backstop_gaps") is not None:
            log.guards.append("backstop")

        reply = self._content_guards(reply, level, log)

        # 一般引導中，Tutor 候選若自行要求完整交稿：
        # 如果學生並非處於剛卡住狀態（stuck_count == 0 且非 explicit_stuck），
        # 且已有實質對話推導（對話輪數 >= 3 或已有實質數學進展），
        # 助教主動請學生寫出完整證明是合理的教學轉折，合法進入 review / awaiting_submission。
        # 只有在學生首輪或學生剛卡住時，才視為 premature_writeup 進行重生成。
        if not peer and phase == "guide" and asks_for_full_writeup(reply):
            recent_stuck = bool(self.state.get("stuck_count", 0) > 0 or self._is_stuck_now(last_user))
            turn_count = len(self.state.get("turns") or [])
            if not recent_stuck and turn_count >= 3:
                log.guards.append("tutor_writeup_requested")
                self._enter_awaiting_submission(
                    event="READINESS_PASSED", source="tutor_model_readiness")
            else:
                log.guards.append("premature_writeup")
                note = (
                    "The proof skeleton is not yet verified as complete. Do not ask for a full proof. "
                    "Ask one focused question about the next missing mathematical link." if en else
                    "目前尚未確認證明骨架完整。不要要求提交完整證明；請針對下一個尚未完成的"
                    "數學連結問一個聚焦問題。")
                regenerated = (self._content_guards(self._regen(level, note), level, log)
                               if self._regen_budget_left() else "")
                if regenerated and not asks_for_full_writeup(regenerated):
                    reply = regenerated
                    log.regenerated = True
                else:
                    pool = _FALLBACK_QS_EN if en else _FALLBACK_QS
                    i = self.state.get("fb_idx", 0)
                    reply = pool[i % len(pool)]
                    self.state["fb_idx"] = i + 1

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

        reply = self._terminology_guard(reply, level, log)

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
            # 教學輪不會走到這裡（確定性輸出、且重講同一步是刻意行為）
            if self._regen_budget_left():
                reply = self._content_guards(self._regen(level, _note), level, log)
                log.regenerated = True
                # 複驗：greedy 解碼下 system 只多一句提醒，重生成常常還是同一段話。
                # 不複驗就採用，學生會連看好幾輪一模一樣的回覆（弱點 #17 成因 (b)）。
                if self._repeats_previous(reply):
                    log.guards.append("repeat_unresolved")

        # 本輪回覆若親口宣告整份證明完成 → 立刻 arm。arm 若等到下一輪 step() 開頭才做，
        # 「宣告完成」與「下一步該從哪裡下手」會出現在同一則回覆裡（守門 X4/zh 末輪實例）。
        # Tutor 候選文字不具有 phase 轉移權；只有 review judge 能結案。

        # 回問保底：引導輪/拒絕輪/同學輪都必須以問題收尾；
        # 但學生已致謝/宣告完成 → 對話收尾，不強迫再問
        # （教學輪不在此列：確認問題本來就是模板的一部分，不可能缺。）
        last_user = next((m["content"] for m in reversed(self.messages)
                          if m["role"] == "user"), "")
        # done_closed 後一律不硬補：證明已確認完成還被追問「下一步該從哪裡下手」是
        # 最突兀的扣分項（update.md 稽核）。closed 階段本就不補，這道是階段判定沒落在
        # closed（例如學生質疑而落回一般流程）時的保險。
        needs_q = (peer or (level < 2 and phase == "guide"
                            and self.state.get("turn_action") in {
                                "normal_guide", "refuse_tutor_write"})) \
            and phase != "closed" \
            and not (phase == "guide" and _DONE_RE.search(last_user))
        if needs_q and not _QMARK_RE.search(reply):
            log.guards.append("no_question")
            # 配額用盡就不再賭模型服從，直接走下面的確定性補救（保底句／交稿請求）
            regen = self._regen(level, (
                "Your previous draft had no question. Rewrite: it must end with one question guiding "
                "the student to the next step." if en else
                "上一稿沒有問題句。重寫：最後必須是一個引導學生思考下一步的問句。"
            )) if self._regen_budget_left() else ""
            if _QMARK_RE.search(regen):
                reply = self._content_guards(regen, level, log)
                log.regenerated = True
            else:
                # 上一輪才剛補過保底句 → 這輪不再硬補（避免對話收尾時連輪追問）；
                # 其餘情況輪換措辭補上（不會連續出現同一句）。
                prev = self.state["turns"][-1].guards if self.state["turns"] else []
                if "fallback" not in prev:
                    # 是否其實已完成由本輪最後的合併審查決定；這裡只補一般問句。
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
        # 普通 Tutor 文字無法將 review 切成 closed。

        # 逐步教學最後一步答錯時的答案揭示（_walkthrough_transition 留下的）。
        # 補在**所有守衛之後**：這句是 driver 用 teach_steps 組出來的，內容本來就與
        # 參考解重疊，放在守衛之前會被洩漏防護判為抄參考解而整段重生成掉（實測）。
        # 一般引導的最終候選只做一次「readiness＋數學／level policy」合併審查；
        # ready 時直接切 review 並回確定性交稿模板，否則才決定候選能否送出。
        reply = self._enforce_guide_reply_policy(reply, level, log)
        # 前面的重複守衛看不到合併審查最後換上的 Controller 保底；落地前再做一次相同的
        # 通用近三輪比對。只替換為無題型數學內容的輪換問句，不增加模型呼叫。
        reply = self._final_guide_repeat_guard(reply, log)
        self.state["turns"].append(log)
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    # ---- 統一階段／卡住路由（狀態鎖 > 明確規則 > Thinking 模糊分類）------------
    def _detect_phase(self, student_text: str) -> None:
        """保存當輪 action；只有已驗證的全文外形會產生交稿事件。"""
        cached = (self.state.get("student_state_decision")
                  if self.state.get("student_state_text") == student_text else None)
        if isinstance(cached, dict):
            decision = cached
            self.state["turn_action"] = decision.get("turn_action", "normal_guide")
        else:
            decision = self._route_student_state(student_text).to_dict()
        if (decision.get("intent") == "full_proof_submission"
                and self.state.get("phase") == "review"):
            self._apply_phase_event(
                "FULL_PROOF_SUBMITTED", source="full_proof_structure_guard")

    def _clear_presented(self) -> None:
        for k in ("walk_presented_step", "walk_presented_idx", "walk_presented_step_id"):
            self.state.pop(k, None)

    def _walkthrough_transition(self, student_text: str) -> None:
        """逐步教學狀態機：進入 / 單次作答 / 揭答前進 / 收尾。

        每個確認問題只有一次有效作答機會。回答由思考型審閱後盾做數學語意判定，
        不使用 expected_answer 的字串比對；有效作答未判為 correct 就揭示參考答案並前進，
        但 unavailable 不消耗作答機會。
        評分對象是「上一輪實際呈現的那一步」（walk_presented_step），不是依當下語言
        重新取 steps[walk_idx]——步驟表若因語言切換而換了一套，後者會拿另一題的
        標準答案去評分（Codex 交接文件的問題四，實測會把正確答案判錯）。
        """
        if self.state.get("phase") == "walkthrough":
            if self.state.get("turn_action") == "refuse_tutor_write":
                return
            steps = self._ensure_teach_steps()
            if not steps:
                self._apply_phase_event("RESET", source="walkthrough_steps_unavailable")
                self.state.pop("walk_lang", None)
                self._clear_presented()
                return
            idx = min(self.state.get("walk_idx", 0), len(steps) - 1)
            presented = self.state.get("walk_presented_step") or steps[idx]
            en = self._teach_lang() == "en"
            judged = self._judge_walkthrough_answer(student_text, presented)
            verdict = judged.get("verdict") if judged else "unavailable"
            if verdict == "unavailable":
                self.state["walk_feedback"] = (
                    WALK_JUDGE_UNAVAILABLE_EN if en else WALK_JUDGE_UNAVAILABLE)
                self.state["stuck_count"] = 0
                return
            if verdict == "correct":
                self.state.pop("walk_feedback", None)
            else:
                reason = str((judged or {}).get("feedback") or "").strip().rstrip("。.")
                if not reason:
                    fallback_reasons = {
                        "incorrect": ("回答含有數學錯誤，或與目前問題的條件或結論矛盾",
                                      "the answer contains a mathematical error or contradicts the current step"),
                        "partial": ("回答只處理了目前確認問題的一部分",
                                    "the answer addresses only part of the current check"),
                        "not_answer": ("回答尚未實際處理目前的確認問題",
                                       "the response does not actually answer the current check"),
                    }
                    zh_reason, en_reason = fallback_reasons.get(
                        verdict, fallback_reasons["incorrect"])
                    reason = en_reason if en else zh_reason
                answer = str(presented.get("expected_answer") or "").strip()
                if not answer:
                    answer = next((str(x).strip() for x in
                                   (presented.get("accepted_answers") or [])
                                   if str(x).strip()), "")
                if not answer:
                    answer = str(presented.get("explain") or "").strip()
                # 模板本身會補句號；先去除答案鍵尾端標點，避免「。。」。
                answer = answer.rstrip().rstrip("。.！!；;")
                last = idx + 1 >= len(steps)
                tpl = ((WALK_REVEAL_LAST_EN if en else WALK_REVEAL_LAST) if last
                       else (WALK_REVEAL_EN if en else WALK_REVEAL))
                self.state["walk_feedback"] = tpl.format(reason=reason, answer=answer)
            # correct／incorrect／partial／not_answer 消耗一次作答機會；
            # unavailable 已在上方保留原 idx 並回傳。
            self.state["walk_idx"] = idx + 1
            self._clear_presented()
            if self.state["walk_idx"] >= len(steps):  # 教完 → 請學生自己寫證明
                self.state.pop("walk_lang", None)
                self._clear_presented()
                # walk_feedback 刻意不清：最後一步答錯時的答案揭示還沒說出口，
                # 由下一輪（review/awaiting_submission）帶出去，否則那一步的答案就這樣消失了。
                self._enter_awaiting_submission(
                    event="WALKTHROUGH_COMPLETED", source="walkthrough_state_machine")
            self.state["stuck_count"] = 0
            return
        # 進入條件：同一段對話中連續卡住三次。第 2 次已先收到 Level 2 核心想法。
        if (self.state["stuck_count"] >= 3
                and self.state.get("phase") == "guide"):
            # 進入時鎖定語言：教學期間 session 語言不再跟著學生訊息跑，
            # 否則同一個 walk_idx 會在中英兩套步驟表之間跳來跳去。
            walk_lang = self.lang
            self._apply_phase_event("STUCK_LIMIT_REACHED", source="stuck_controller")
            self.state["walk_lang"] = walk_lang
            self._clear_presented()

    # ---- session 快照（逐輪 CLI 每輪都是新行程，需跨行程還原）------------------
    def _phase_trace_state(self) -> dict:
        """擷取會影響 phase 的狀態；只放可 JSON 序列化的診斷欄位。"""
        keys = (
            "phase", "stuck_count", "walk_active", "walk_idx", "walk_lang",
            "review_active", "review_status", "awaiting_clean_proof",
            "done_closed", "writeup_asked", "teach_steps_source",
            "walkthrough_review_status", "writeup_readiness",
            "readiness_pending", "guide_reply_review",
            "proof_progress_revision", "turn_action", "review_error",
        )
        result = {key: self.state.get(key) for key in keys}
        result["phase_event_count"] = len(self.state.get("phase_events") or [])
        return result

    def _begin_phase_trace(self) -> dict:
        """開始一輪 phase 診斷，並清掉上一輪 router 決策以免重複文字誤綁。"""
        before = self._phase_trace_state()
        self.state.pop("student_state_text", None)
        self.state.pop("student_state_decision", None)
        return before

    def _record_phase_transition(self, student_text: str, before: dict, *,
                                 transition_source: str | None = None) -> None:
        """保存一輪完整 phase 切換資料，不影響任何路由或教學狀態。"""
        decision = None
        if self.state.get("student_state_text") == student_text:
            candidate = self.state.get("student_state_decision")
            if isinstance(candidate, dict):
                decision = dict(candidate)
        after = self._phase_trace_state()
        history = self.state.setdefault("phase_history", [])
        previous_phase = before.get("phase")
        final_phase = after.get("phase")
        event_start = int(before.get("phase_event_count") or 0)
        turn_events = list((self.state.get("phase_events") or [])[event_start:])
        last_event = turn_events[-1] if turn_events else {}
        history.append({
            "turn": len(history) + 1,
            "student_text": student_text,
            "previous_phase": previous_phase,
            "router_phase": decision.get("phase") if decision else None,
            "final_phase": final_phase,
            "next_phase": final_phase,
            "phase_changed": previous_phase != final_phase,
            "event": last_event.get("event"),
            "event_source": last_event.get("event_source"),
            "accepted": last_event.get("accepted") if last_event else None,
            "reject_reason": last_event.get("reject_reason", ""),
            "events": turn_events,
            "transition_source": transition_source or (
                decision.get("source") if decision else "driver_state_machine"),
            "intent": decision.get("intent") if decision else None,
            "learning_state": decision.get("learning_state") if decision else None,
            "answers_current_question": (
                decision.get("answers_current_question") if decision else None),
            "has_actionable_math": (
                decision.get("has_actionable_math") if decision else None),
            "advances_solution": (
                decision.get("advances_solution") if decision else None),
            "requested_writer": (
                decision.get("requested_writer") if decision else None),
            "turn_action": decision.get("turn_action") if decision else None,
            "phase_confidence": decision.get("phase_confidence") if decision else None,
            "stuck_confidence": decision.get("stuck_confidence") if decision else None,
            "evidence": decision.get("evidence") if decision else "",
            "state_before": before,
            "state_after": after,
        })

    def phase_transition_report(self) -> dict:
        """回傳本題到目前為止的完整 phase 切換狀態。"""
        history = list(self.state.get("phase_history") or [])
        return {
            "problem_id": self.problem.get("id"),
            "statement": self.problem.get("statement"),
            "turn_count": len(history),
            "final_state": self._phase_trace_state(),
            "transitions": history,
        }

    def turn_state_summary(self) -> dict:
        """回傳 Colab 逐輪顯示的簡短狀態，保留本輪完整 event chain。"""
        transition = (self.state.get("phase_history") or [{}])[-1]
        events = list(transition.get("events") or [])
        last_event = events[-1] if events else {}
        event_chain = []
        for event in events:
            item = (f"{event.get('event')}:{event.get('previous_phase')}"
                    f">{event.get('next_phase')}")
            if event.get("accepted") is False:
                reason = str(event.get("reject_reason") or "unknown")
                item += f"[rejected:{reason}]"
            event_chain.append(item)
        return {
            "phase": self.state.get("phase"),
            "review_status": self.state.get("review_status"),
            "stuck_count": self.state.get("stuck_count"),
            "walk_idx": self.state.get("walk_idx"),
            "intent": transition.get("intent"),
            "turn_action": transition.get("turn_action"),
            # event 與 event_accepted 保留給舊 notebook；events 才是完整過程。
            "event": last_event.get("event"),
            "event_accepted": last_event.get("accepted"),
            "reject_reason": last_event.get("reject_reason", ""),
            "events": event_chain,
        }

    def format_phase_transition_report(self) -> str:
        """產生可直接由 notebook 印出的 UTF-8 JSON phase 報告。"""
        return json.dumps(self.phase_transition_report(), ensure_ascii=False, indent=2)

    def dump_state(self) -> dict:
        """可 JSON 序列化的完整 session 快照。

        整包存（而非逐欄列舉）是刻意的：舊版 interactive_turn.py 只存
        stuck_count/phase/writeup_asked，於是 done_closed、fb_idx、
        walk_* 每輪歸零——#11/#12 的收尾修復、保底句輪換、逐步教學進度在逐輪 CLI 上
        全部失效（update.md 稽核的 F2）。整包存之後新增狀態欄位會自動跟著存。
        turns 內含 TurnLog 物件，只保留上一輪的 guards（保底連補守衛唯一會讀的東西）。
        """
        try:
            from phase_router import normalize_persisted_state
        except ImportError:
            from .phase_router import normalize_persisted_state
        normalize_persisted_state(self.state)
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
        try:
            from phase_router import normalize_persisted_state
        except ImportError:
            from .phase_router import normalize_persisted_state
        normalize_persisted_state(self.state)
        guards = list(saved.get("last_guards") or [])
        self.state["turns"] = (
            [TurnLog(level=0, stuck_count=self.state.get("stuck_count", 0), guards=guards)]
            if guards else [])

    # ---- 對外 API -------------------------------------------------------------
    def start(self, opener: str | None = None) -> str:
        # session 語言：有 opener 依 opener 判定，否則依題目陳述
        self.state["lang"] = detect_lang(opener if opener else self.problem["statement"])
        # opener 前沒有 Tutor 問題可回答，因此無論內容是否表達卡住，第一輪都不計 stuck。
        self.state["stuck_count"] = 0
        user_opener = opener
        if self.lang == "en":
            opener = opener or "I've read the problem but don't know how to start. Could you give me a first hint?"
            first = f"Problem: {self.problem['statement']}\n\n{opener}"
        else:
            opener = opener or "我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？"
            first = f"題目：{self.problem['statement']}\n\n{opener}"
        trace_before = self._begin_phase_trace()
        if user_opener:
            # 每則學生訊息先且只先經統一 router 分類，特殊工作流再消費決策。
            self._route_student_state(opener)
            review_reply = self._review_workflow_transition(user_opener)
            if review_reply is not None:
                self.messages = []
                reply = self._emit_review_reply(first, review_reply)
                self._record_phase_transition(
                    opener, trace_before, transition_source="review_workflow")
                return reply
        # router 只看學生實際說的內容，不把題目敘述混進意圖／卡住分類。
        self._detect_phase(opener)
        # guide（含 respond_attempt）的數學檢查已併入最終單一審查；只有正式全文
        # review 仍在生成前使用舊 backstop，避免同一 guide 輪重複呼叫 Thinking。
        if not self.is_peer() and self.state.get("phase") == "review":
            self._consult_backstop(first)
        self.messages = [{"role": "user", "content": first}]
        reply = self._tutor_turn()
        # opener 的 router 決策仍保留供 action／診斷使用，但 stuck_count 固定維持 0；
        # 學生下一輪第一次無法回答 Tutor 的實際問題時，才由 step() 累計為 1。
        self._record_phase_transition(opener, trace_before)
        return reply

    def step(self, student_text: str) -> str:
        trace_before = self._begin_phase_trace()
        # 語言跟隨「學生」而非題目：學生訊息夠長且語言明確不同 → 切換 session 語言
        # （支援「英文題＋中文學生」等混合，以及對話中途換語言；短訊息不切以免誤判）。
        if "lang" not in self.state:             # 未經 start() 直接 step 時補判語言
            self.state["lang"] = detect_lang(student_text)
        elif self.state.get("phase") != "walkthrough":
            # 逐步教學進行中不重判語言（walk_lang 鎖定）：一則「中文＋長 LaTeX」的
            # 正確回答就足以把 session 切成英文，接著整個步驟表與答案鍵一起換掉。
            _s = _strip_language_neutral_math(student_text)
            if len([c for c in _s if not c.isspace()]) >= 12:
                self.state["lang"] = detect_lang(student_text)
        # #12：對話中途自然證完、助教上一則親口確認整個證明完成 → arm done_closed，
        # 使本輪起的反思（含帶問句）走 closed（接上 #11），收斂 H5 型過度延伸。
        # 附帶三道閘（放寬措辭後的安全網）：該則回覆若還在問問題、講的是「還沒完成」、
        # 或只在講某一步，都不算確認完成。
        # （審閱輪的 arm 走 _tutor_turn 的「審閱通過」訊號，不靠措辭比對。）
        # 普通 Tutor 回覆不能產生 REVIEW_PASSED；結案只看審閱判定。
        # 每則學生訊息先且只先經統一 router 分類；review/closed 工作流只消費
        # 這份決策，不另行以 regex 或全文外形重新判斷意圖。
        self._route_student_state(student_text)
        review_reply = self._review_workflow_transition(student_text)
        if review_reply is not None:
            reply = self._emit_review_reply(student_text, review_reply)
            self._record_phase_transition(
                student_text, trace_before, transition_source="review_workflow")
            return reply
        self._detect_phase(student_text)
        # guide/respond 的數學正確性由合併審查處理；全文 review 才保留舊 backstop。
        if not self.is_peer() and self.state.get("phase") == "review":
            self._consult_backstop(student_text)
        else:
            self.state["backstop_gaps"] = None
        # learning_state 已由同一個 router 依 phase gate、明確規則與必要時的 Thinking
        # 判斷完成；在單一位置更新，避免其他流程各自加減造成不同步。
        self._update_stuck_from_decision()
        if not self.is_peer():
            self._walkthrough_transition(student_text)
        self.messages.append({"role": "user", "content": student_text})
        reply = self._tutor_turn()
        self._record_phase_transition(student_text, trace_before)
        return reply


def load_problems() -> dict:
    """載入題目、參考證明與分級提示庫（hint ladders）。"""
    problems = {}
    for fname in ("problems.json", "held_out.json", "hard_math_major.json"):
        p = HERE / fname
        if p.exists():
            for item in json.loads(p.read_text(encoding="utf-8")):
                problems[item["id"]] = item
    
    # 掛載中文提示梯
    lad_zh = HERE / "hint_ladders.json"
    if lad_zh.exists():
        try:
            for pid, ladder in json.loads(lad_zh.read_text(encoding="utf-8")).items():
                if pid in problems:
                    problems[pid]["hint_ladder"] = ladder
        except Exception:
            pass
    
    # 掛載英文提示梯
    lad_en = HERE / "hint_ladders_en.json"
    if lad_en.exists():
        try:
            for pid, ladder in json.loads(lad_en.read_text(encoding="utf-8")).items():
                if pid in problems:
                    problems[pid]["hint_ladder_en"] = ladder
        except Exception:
            pass

    return problems
