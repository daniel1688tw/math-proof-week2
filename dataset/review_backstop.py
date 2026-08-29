# -*- coding: utf-8 -*-
"""review_backstop.py — 審閱後盾：思考型模型對學生草稿/嘗試做參考解對照複核。

混合架構定位（FINAL_VERDICT 的教訓）：思考型模型 S2 糾錯 4.75 全場最強（解剖銳利），
但無訓練約束、對抗情境不可靠 → 不讓它面對學生，只讓它在幕後「找碴」。
判斷交給思考型模型；一般嘗試仍可由微調模型包裝成引導語氣。完整證明則使用
確定性的問題佇列，避免說話模型跳題：

  學生交草稿/嘗試 → find_gaps()（本模組，Ollama 思考型） → 缺漏清單
                  → 注入 TutorDriver 的 review/rectify 階段指示 → 微調模型引導式說出
  學生交完整證明 → review_full_proof() 兩輪全文複核 → 根本問題佇列
  學生局部訂正   → judge_local_revision() 語意確認 → 核准後才合併草稿與前進

Ollama 不可用或逾時 → 回傳 None；完整證明不得因此誤判通過，Driver 保留進度供重試。

環境變數：
  REVIEW_MODEL    後盾模型（預設 qwen3-4b-thinking-2507:latest）
  OLLAMA_URL      chat API（預設 http://localhost:11434/api/chat）
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from difflib import SequenceMatcher

MODEL = os.environ.get("REVIEW_MODEL", "qwen3-4b-thinking-2507:latest")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")


def _ollama_think_enabled() -> bool:
    """Allow GGUF imports that reason internally but lack Ollama's think capability."""
    return os.environ.get("OLLAMA_THINK", "1").strip().lower() not in {
        "0", "false", "no", "off",
    }

# 找碴員 system：只做判斷、只輸出結構化清單（不需引導語氣——那是微調模型的事）
CRITIC_SYSTEM = """你是數學系課程的證明審閱助教。使用者會給你：題目、正確的參考解、學生寫的草稿或嘗試。

任務：對照參考解，以**嚴格的教學標準**（不是數學家的「顯然可略」標準）找出草稿的缺漏或錯誤：
1. 數學錯誤：斷言不成立、計算錯、包含關係或不等號方向反了、量詞順序錯誤。
2. 依據缺漏：某一步結論依賴的事實沒有明說——即使該事實顯然成立也算缺漏。
   例：由 $cv=0$ 推 $c=0$ 卻沒說 $v\\ne0$；套用鴿籠原理卻沒陳述「幾個物件、幾個類別」；
   引用定理卻沒驗證其前提。教學上這些都必須讓學生補上。
3. 嚴格與非嚴格不等號、特例未排除。

術語慣例（本專案規格，三處一致：備課驗證員、教學步驟、審閱）：
題目只寫「遞增／increasing」而未寫「嚴格／strictly」時，一律按**單調不減**理解。
學生寫「單調不減／非減少／nondecreasing」是精確表述，**不是缺漏**，不可列為問題。

規則：
- 草稿正確且依據完整的步驟不要質疑；風格與詳略不算問題。
- 每項用一句話精確說明：在哪一步、缺了什麼或錯在哪。
- 必須列出所有彼此獨立的根本問題，不設數量上限；完全沒有問題就輸出空陣列。
- 只輸出 JSON 字串陣列（如 ["…","…"]），不要輸出任何其他文字。"""

CRITIC_TEXT_FALLBACK_SYSTEM = """你是數學系課程的證明審閱助教。使用者會給你：題目、
正確的參考解、學生寫的草稿或嘗試。前面的 JSON 輸出已重複失敗，現在請從頭獨立審閱。

仍須採嚴格教學標準：找出數學錯誤、未明說的必要依據、未驗證的定理前提、量詞或
不等號問題；列出所有彼此獨立的根本問題。題目只寫遞增／increasing 時按單調不減理解。

輸出只能是以下兩種形式之一：
CLEAR
或每個問題各佔一行：
ISSUE: 在哪一步、缺了什麼或錯在哪
不可輸出標題、編號、JSON、Markdown 或其他文字。"""

ANSWER_JUDGE_SYSTEM = """你是數學證明課程的逐步回答審閱員。使用者會給你題目、
已驗證的參考解、目前教學步驟、確認問題、參考答案，以及學生這一次的回答。

請像審閱證明草稿一樣先獨立核對數學內容，再判斷學生是否完整回答了目前的確認問題：
- 不做字串比對。LaTeX 包裝、等價式、變數命名、同義詞及較完整但正確的回答都要接受。
- 回答若含錯誤或互相矛盾的敘述，判 incorrect。
- 只答對一部分，判 partial。
- 表示不會、要求答案、空白或沒有實際回答，判 not_answer。
- 只有完整且數學正確地回答目前問題才能判 correct；無法確定時判 uncertain。
- 若學生提供理由或推導，必須同時審查其中每個斷言是否成立。即使最後結論碰巧
  與參考答案一致，只要理由中有錯誤等式、誤用性質或無效推理，仍判 incorrect。
- 「完整回答」按確認問題實際要求判斷，不等於逐字重述講解。若問題問某一步為什麼
  成立，學生正確點出直接適用的定義、性質或定理，而該名稱已足以唯一支持這一步，
  應判 correct；除非問題明確要求展開推導，否則不可因回答精簡而拒絕。
- 若判 incorrect 或 partial，feedback 必須指出學生回答中哪個具體量、關係、方向、
  前提或結論與目前問題不符；不可只寫「無法確認」「答案不正確」等通用句。
- 若學生回答含多個式子或推理，先獨立推導正確論證，再按學生的書寫順序找出第一個錯誤
  等式、不成立的理由或關鍵缺口。root_error 必須指出這個最早根本錯誤，correct_basis
  必須寫出該處的正確關係或依據；不可只把錯誤前提所導致的後續結果當成錯因。
- root_error 只負責診斷學生寫錯或漏掉的第一處，必須寫成「將 A 誤寫為 B」、
  「誤用某性質」或「漏掉某條件」這類完整診斷，不可只輸出一個沒有主詞動詞的式子。
  correct_basis 只供程式確認診斷有正確依據，不要把它重複寫進 root_error。
- root_error、correct_basis 與 feedback 必須全部使用使用者指定的輸出語言；數學符號不影響語言判定。
- 判 correct 時不可因交換等式兩邊、等價不等式、LaTeX 寫法或回答比參考答案更完整
  而拒絕。

只輸出 JSON：
{"verdict":"correct|incorrect|partial|not_answer|uncertain",
 "root_error":"incorrect/partial 時填最早根本錯誤；其他判定可留空",
 "correct_basis":"incorrect/partial 時填該處正確關係或依據；其他判定可留空",
 "feedback":"一句簡短而具體的數學判定理由"}
不要輸出 JSON 以外的文字。"""

ANSWER_JUDGE_COMPACT_SYSTEM = """你是數學證明課程的確認問題審閱員。前一次完整語境
審閱未得到可用結果；請只依目前步驟、確認問題、參考答案與學生回答，重新做數學語意
判定。不得做字串比對；等價式、同義敘述、不同 LaTeX 包裝及更完整的正確回答均應判
correct。若問題只問理由，正確點出能唯一支持該步的定義、性質或定理就是充分回答，
除非題目明確要求推導。若判 incorrect 或 partial，feedback 必須明確指出學生寫出的
哪個量、符號、方向、條件或結論不符合問題，不能寫「無法確認」或「答案錯誤」等通用
理由。學生的理由若無效，即使結論碰巧正確也要判 incorrect。若回答有多個式子，root_error
必須指出按書寫順序出現的第一個錯式或錯誤理由，correct_basis 填該處的正確關係；不可只寫
後續結果。root_error 要寫成「將 A 誤寫為 B」、「誤用某性質」或「漏掉某條件」的完整診斷，
不可只輸出一個孤立式子。所有文字欄位必須使用使用者指定的輸出語言。只有資料本身互相矛盾、
確實無法判斷時才可判 uncertain。

只輸出 JSON：
{"verdict":"correct|incorrect|partial|not_answer|uncertain",
 "root_error":"incorrect/partial 時必填；其他判定可留空",
 "correct_basis":"incorrect/partial 時必填；其他判定可留空",
 "feedback":"一句簡短而具體的數學判定理由"}
不要輸出 JSON 以外的文字。"""

ANSWER_CORRECT_AUDIT_SYSTEM = """你是數學證明課程的第二輪獨立審閱員。第一輪暫時將學生的
逐步回答判為 correct，但你不可信任該結果，必須從頭獨立檢查。

規則：
- 分開檢查「結論是否正確」與「學生寫的理由是否真的能推出該結論」。
- 即使最後式子與參考答案相同，只要學生中間用了錯誤等式、無效相消、誤用定理或虛假前提，
  就必須判 incorrect。
- 按學生書寫順序找第一個錯誤或缺口。root_error 寫成「將 A 誤寫為 B」、「誤用某性質」或
  「漏掉某條件」的完整診斷；correct_basis 填該處的正確關係或依據。
- 不做字串比對；數學上等價且理由成立的回答仍判 correct。
- 所有文字欄位必須使用使用者指定的輸出語言。

只輸出 JSON：
{"verdict":"correct|incorrect|partial|not_answer|uncertain",
 "root_error":"incorrect/partial 時必填；其他判定可留空",
 "correct_basis":"incorrect/partial 時必填；其他判定可留空",
 "feedback":"一句簡短而具體的判定理由"}
不要輸出 JSON 以外的文字。"""

FULL_REVIEW_SYSTEM = """你是數學證明課程的嚴格審閱員。請對照題目與已驗證參考解，
完整檢查學生證明的前提、量詞、定理適用條件、等式、不等號方向及結論強度。

規則：
- 一次找出所有實質數學問題，不要只找第一項；風格或可省略的贅詞不算問題。
- 同一個根本錯誤造成的後續錯式或錯誤結論，必須合併成同一項，後果寫入 description，
  不得拆成多項重複要求學生修正。
- correction 要直接寫出這一處數學上正確的版本，但只修該根本錯誤，不代寫整份證明。
- root_cause 與 description 只說明學生哪個斷言錯、錯因及後果，不得包含正確版本；
  正確內容只能放在 correction，供內部判定使用。
- 題目只寫 increasing／遞增而沒有 strictly／嚴格時，本專案按單調不減理解。
- 若草稿末尾有「已核准的局部訂正」，那些訂正取代原稿中相衝突的舊敘述。

只輸出 JSON 物件陣列，不要輸出其他文字：
[{"root_cause":"簡短且可去重的根本錯誤", "location":"草稿中的位置或原句",
  "description":"錯誤理由與連帶後果", "correction":"這一處的正確版本"}]
完全正確時輸出 []。"""

FULL_REVIEW_TEXT_FALLBACK_SYSTEM = """你是數學證明課程的嚴格審閱員。請對照題目與
已驗證參考解，從頭到尾找出學生完整證明的所有根本數學錯誤。相同根本錯誤造成的後果
合併成一項；每個字串只寫明位置與錯因。完全正確時輸出 []。
只輸出 JSON 字串陣列，例如 ["位置：第二行；錯誤：..."]，不要輸出其他文字。"""

LOCAL_REVISION_SYSTEM = """你是數學證明課程的局部訂正審閱員。使用者會提供題目、參考解、
目前合併草稿、現在唯一要修的問題，以及學生的局部回答。

請獨立核對數學內容，判斷這個回答是否真的修正了目前問題：
- 必須先把學生回答視為「只替換目前錯誤位置的局部文字」，在目前完整草稿的上下文中
  重新閱讀；不要要求學生重複前後已存在且正確的句子、公式或定理應用。
- 接受精簡但數學正確的等價說法、等價式、不同變數名稱，不做字串比對。
- 問題中的 correction 只是內部參考，不是唯一標準答案；必須依數學內容獨立判斷，
  不得要求學生逐字相同。
- 回答必須含足以取代錯誤敘述的實質訂正。通常只說定理名稱不足；但若目前唯一錯誤
  正是「定理名稱寫錯」，而草稿中該定理的其餘敘述與應用已完整，正確定理名稱本身
  就是充分的局部替換，應判 correct。
- 若目前唯一錯誤是多加了題目未給的假設，學生用題設真正給定、且足以支撐原稿後續
  定理應用的條件取代它，即使沒有重抄後續定理名稱或結論，也應判 correct。
- 只說「不知道／不會」、只表示同意，或沒有處理目前根本錯誤，判 not_answer 或 partial。
- 本輪不是重新審閱全文。判定範圍只包含「目前唯一要修的問題」明列的 root_cause、
  location 與 description；草稿中未列入 description 的其他獨立錯誤，不得拿來拒絕
  這次局部訂正，它們會在合併後的全文重審中另行排入佇列。
- 若 description 明確列出同一根本錯誤造成的連帶後果，才要求學生一併修正；不得自行
  從草稿擴張新的連帶後果。
- 若回答本身仍含錯誤、矛盾，或未修好目前明列的問題，判 incorrect 或 partial。
- 只要這段回答能在目前位置取代錯誤文字，並使目前明列的問題數學上成立，就判 correct，
  即使全文仍有其他尚未審閱的錯誤。

只輸出 JSON：
{"verdict":"correct|incorrect|partial|not_answer|uncertain",
 "feedback":"一句精簡理由"}
不要輸出 JSON 以外的文字。"""

LOCAL_REVISION_SCOPE_SYSTEM = """你是數學證明局部訂正的範圍複核員。前一位審閱員
可能把完整草稿中的其他錯誤誤算到本輪。請只判斷：學生局部回答能否取代指定 location
附近的錯誤文字，並修好目前 issue 的 root_cause 與 description。

規則：
- 這不是全文審閱；未寫在目前 issue description 裡的其他錯誤一律忽略，留給合併後重審。
- correction 只供參考；接受精簡、等價且數學正確的替換，不做字串比對。
- 只有 description 明列的連帶後果才屬本輪範圍，不得自行擴張範圍。
- 回答若足以作為該位置的正確局部替換，判 correct；若仍未修到當前問題才判
  incorrect／partial／not_answer。無法確定判 uncertain。

只輸出 JSON：
{"verdict":"correct|incorrect|partial|not_answer|uncertain",
 "feedback":"一句精簡且只針對目前 issue 的理由"}
不要輸出 JSON 以外的文字。"""

MERGE_REVISION_SYSTEM = """你是數學證明草稿編輯器。使用者會給你目前完整草稿、
正在處理的單一問題，以及已由數學審閱員確認正確的學生局部訂正。請把學生訂正實際
替換或補入完整草稿的對應位置；不得只在文末附加註記，也不得自行修補其他尚未處理的錯誤。
未被此次訂正影響的內容原樣保留。只輸出 JSON：{"merged_draft":"合併後的完整草稿"}。"""

PATCH_REVISION_SYSTEM = """你是數學證明草稿的精確局部編輯器。學生的局部訂正已由
數學審閱員確認正確；你的工作只是在目前完整草稿中定位這一處，產生一個可由程式安全
套用的單次替換。old_text 必須逐字複製目前草稿中恰好出現一次的連續原文，範圍只要
足以唯一定位；new_text 是套用學生訂正後要取代它的文字。不得修改其他內容，也不得
把訂正附加在文末。只輸出 JSON：{"old_text":"原文","new_text":"替換文字"}。"""

def _parse_gaps(content: str) -> list | None:
    """從模型輸出中撈出 JSON 字串陣列；撈不出視為失敗（None）。

    用括號平衡掃描抓頂層 [...]（字串元素內含 [a,b] 這類方括號時，
    單純的非貪婪正則會抓錯片段——實測 X2 案例踩過）。
    """
    if not content:
        return None
    candidates, depth, start = [], 0, None
    for i, ch in enumerate(content):
        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(content[start:i + 1])
    for cand in candidates:
        # 模型輸出常含 LaTeX 跳脫（\{ \dots \leq），對 JSON 是非法 escape；
        # 先照原樣試，失敗再把反斜線全部加倍（視為字面反斜線）重試。
        for attempt in (cand, cand.replace("\\", "\\\\")):
            try:
                arr = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if isinstance(arr, list) and all(isinstance(g, str) for g in arr):
                return [g.strip()[:200] for g in arr if g.strip()]
            break
    return None


def _parse_gap_lines(content: str) -> list | None:
    """解析 JSON 重試失敗後的保守純文字協定；其他內容一律視為失敗。"""
    stripped = (content or "").strip()
    if stripped == "CLEAR":
        return []
    lines = stripped.splitlines()
    if not lines or any(not line.strip().startswith("ISSUE:") for line in lines):
        return None
    issues = [line.strip()[len("ISSUE:"):].strip()[:200] for line in lines]
    return issues if all(issues) else None


def _balanced_objects(content: str) -> list[str]:
    """擷取模型輸出中的頂層 JSON 物件；正確處理字串內的大括號與跳脫。"""
    spans, depth, start, in_string, escaped = [], 0, None, False, False
    for i, ch in enumerate(content or ""):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                spans.append(content[start:i + 1])
    return spans


def _parse_object(content: str, verdicts: set[str]) -> dict | None:
    """寬鬆解析含 LaTeX 反斜線的結構化判定。"""
    for span in _balanced_objects(content):
        for attempt in (span, span.replace("\\", "\\\\")):
            try:
                obj = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and obj.get("verdict") in verdicts:
                return obj
            break
    return None


def _parse_any_object(content: str) -> dict | None:
    """解析第一個 JSON 物件，供已核准局部訂正的草稿合併使用。"""
    for span in _balanced_objects(content):
        for attempt in (span, span.replace("\\", "\\\\")):
            try:
                obj = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                return obj
            break
    return None


def _balanced_arrays(content: str) -> list[str]:
    """擷取頂層 JSON 陣列；忽略字串內的中括號。"""
    spans, depth, start, in_string, escaped = [], 0, None, False, False
    for i, ch in enumerate(content or ""):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                spans.append(content[start:i + 1])
    return spans


def _parse_issue_list(content: str) -> list[dict] | None:
    """解析全文審閱問題；兼容模型偶爾使用的舊欄位或純字串項目。"""
    for span in _balanced_arrays(content):
        for attempt in (span, span.replace("\\", "\\\\")):
            try:
                arr = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if not isinstance(arr, list):
                break
            issues = []
            for i, raw in enumerate(arr, 1):
                if isinstance(raw, str) and raw.strip():
                    raw = {"root_cause": raw.strip(), "description": raw.strip()}
                if not isinstance(raw, dict):
                    return None
                root = str(raw.get("root_cause") or raw.get("summary")
                           or raw.get("problem") or "").strip()
                desc = str(raw.get("description") or raw.get("problem")
                           or raw.get("summary") or root).strip()
                if not root or not desc:
                    return None
                issues.append({
                    "issue_id": str(raw.get("issue_id") or f"issue-{i}"),
                    "root_cause": root[:300],
                    "location": str(raw.get("location") or "").strip()[:500],
                    "description": desc[:1000],
                    "correction": str(raw.get("correction") or "").strip()[:1000],
                })
            return issues
    return None


def _chat_content(system: str, user: str, timeout: int, *, num_predict: int = 8192,
                  temperature: float = 0.15, response_format=None,
                  diagnostics: dict | None = None) -> str | None:
    """呼叫既有 Thinking 模型；可選用原生 schema 並回報失敗原因。"""
    request_data = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "stream": False,
        "think": _ollama_think_enabled(),
        "options": {"temperature": temperature, "top_p": 0.95, "top_k": 20,
                    "num_predict": num_predict, "num_ctx": 16384},
    }
    if response_format is not None:
        # Ollama 的 format 可直接接受 JSON Schema；只對有指定的呼叫生效，
        # 不改變既有全文審閱與 walkthrough 的輸出格式。
        request_data["format"] = response_format
    payload = json.dumps(request_data).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    started = time.monotonic()

    def finish(**fields) -> None:
        if diagnostics is not None:
            diagnostics.update(fields)
            diagnostics["elapsed_ms"] = int((time.monotonic() - started) * 1000)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw_response = r.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        text = str(exc).lower()
        reason = ("timeout" if isinstance(exc, TimeoutError) or "timed out" in text
                  else "service_error")
        finish(status="failed", failure_reason=reason,
               exception_type=type(exc).__name__)
        return None
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        finish(status="failed", failure_reason="response_json_invalid")
        return None
    content = (data.get("message", {}).get("content") or "").strip()
    done_reason = str(data.get("done_reason") or "").strip()
    if not content:
        finish(status="failed",
               failure_reason=("length_exhausted" if done_reason == "length"
                               else "empty_content"),
               done_reason=done_reason, content_length=0)
        return None
    finish(status="received", failure_reason=None, done_reason=done_reason,
           content_length=len(content))
    return content


def _retry_parsed(system: str, user: str, parser, *, timeout: int,
                  num_predict: int = 8192, temperature: float = 0.15,
                  attempts: int = 3, per_attempt_timeout: int | None = None,
                  response_format=None, diagnostics: dict | None = None,
                  retry_instruction: str | None = None):
    """只針對完整證明審閱的服務／JSON 格式失敗重試，不改變數學判準。"""
    attempts = max(1, attempts)
    call_timeout = per_attempt_timeout or max(30, timeout // attempts)
    prompt = user
    attempt_records = []
    for attempt in range(attempts):
        attempt_diagnostic = {"attempt": attempt + 1}
        content = _chat_content(system, prompt, call_timeout,
                                num_predict=num_predict, temperature=temperature,
                                response_format=response_format,
                                diagnostics=attempt_diagnostic)
        parsed = parser(content or "")
        if parsed is not None:
            attempt_diagnostic["status"] = "parsed"
            attempt_diagnostic["failure_reason"] = None
            attempt_records.append(attempt_diagnostic)
            if diagnostics is not None:
                diagnostics.update(status="parsed", failure_reason=None,
                                   attempts=attempt_records)
            return parsed
        if content:
            attempt_diagnostic["status"] = "failed"
            attempt_diagnostic["failure_reason"] = "structured_output_invalid"
        elif not attempt_diagnostic.get("failure_reason"):
            # 兼容測試 stub 或其他未提供底層診斷的呼叫者。
            attempt_diagnostic["status"] = "failed"
            attempt_diagnostic["failure_reason"] = "empty_content"
        attempt_records.append(attempt_diagnostic)
        if attempt + 1 < attempts:
            instruction = retry_instruction or (
                "上一次回覆未能解析。請重新獨立檢查，並嚴格只輸出 system 指定的 "
                "JSON 結構；LaTeX 反斜線須符合 JSON 字串格式。")
            prompt = user + "\n\n" + instruction
    if diagnostics is not None:
        diagnostics.update(
            status="failed",
            failure_reason=attempt_records[-1].get("failure_reason"),
            attempts=attempt_records)
    return None


def _issue_key(text: str) -> str:
    """保留中英文字母數字的輕量正規化，僅用於合併兩輪的明顯重複項。"""
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", (text or "").lower())


def _same_root_issue(left: dict, right: dict) -> bool:
    a = _issue_key(left.get("root_cause", ""))
    b = _issue_key(right.get("root_cause", ""))
    if not a or not b:
        return False
    if min(len(a), len(b)) >= 8 and (a in b or b in a):
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.72


def _merge_root_issues(*groups: list[dict]) -> list[dict]:
    """兩輪問題依根本原因去重；同根後果併入 description。"""
    merged: list[dict] = []
    for issue in (x for group in groups for x in group):
        prior = next((x for x in merged if _same_root_issue(x, issue)), None)
        if prior is None:
            merged.append(dict(issue))
            continue
        extra = issue.get("description", "").strip()
        if extra and _issue_key(extra) not in _issue_key(prior.get("description", "")):
            prior["description"] = (prior["description"].rstrip("。.") + "；" + extra)[:600]
        if not prior.get("location") and issue.get("location"):
            prior["location"] = issue["location"]
        if not prior.get("correction") and issue.get("correction"):
            prior["correction"] = issue["correction"]
    return merged


def _issue_from_fallback_text(text: str, index: int) -> dict:
    """將簡化審閱的「位置／錯誤」標籤回復為可操作 issue。

    這只解析審閱輸出的通用欄位，不根據題型或數學關鍵詞猜測內容。
    """
    raw = str(text or "").strip()
    fields = re.findall(
        r"(?:^|[\n；;])\s*(位置|錯誤|問題|缺漏|location|error|issue|gap)"
        r"\s*[:：]\s*([^\n；;]+)", raw, re.I)
    location = ""
    root = ""
    for label, value in fields:
        key = label.lower()
        value = value.strip()
        if key in {"位置", "location"} and not location:
            location = value
        elif key in {"錯誤", "問題", "缺漏", "error", "issue", "gap"} and not root:
            root = value
    root = root or raw
    return {"issue_id": f"issue-{index}", "root_cause": root,
            "location": location, "description": root, "correction": ""}


def available(timeout: int = 3) -> bool:
    """Ollama 是否在線且已載入後盾模型。"""
    try:
        url = OLLAMA_URL.rsplit("/api/", 1)[0] + "/api/tags"
        with urllib.request.urlopen(url, timeout=timeout) as r:
            names = [m.get("name", "") for m in json.loads(r.read()).get("models", [])]
        return MODEL in names
    except Exception:
        return False


def find_gaps(statement: str, reference_proof: str, draft: str,
              timeout: int = 600) -> list | None:
    """回傳缺漏清單（[] = 複核無誤）；Ollama 失敗/逾時/輸出不可解析 → None（降級）。"""
    user = (f"【題目】\n{statement}\n\n【參考解（正確）】\n{reference_proof}\n\n"
            f"【學生草稿】\n{draft}")
    # num_predict 必須留給思考鏈足夠空間：3072 在真實證明案例會被思考吃光。
    # 數學判斷正確但 JSON 格式偶發失敗時重取一次，仍不把不可解析輸出當成「無缺漏」。
    parsed = _retry_parsed(
        CRITIC_SYSTEM, user, _parse_gaps,
        timeout=timeout, num_predict=8192, temperature=0.2, attempts=2)
    if parsed is not None:
        return parsed
    # Ollama Thinking 搭配 JSON Schema 可能回空 content；改以嚴格逐行協定低溫重審。
    # 只有明確 CLEAR 才回空清單，任何非協定輸出仍回 None，避免把服務失敗當成無缺漏。
    return _retry_parsed(
        CRITIC_TEXT_FALLBACK_SYSTEM, user, _parse_gap_lines,
        timeout=timeout, num_predict=8192, temperature=0.05, attempts=2,
        retry_instruction=(
            "上一次回覆未能解析。請重新獨立檢查，只輸出一行 CLEAR，或每個問題各輸出"
            "一行 ISSUE: 在哪一步、缺了什麼或錯在哪；不可輸出其他文字。"))


def review_full_proof(statement: str, reference_proof: str, draft: str,
                      timeout: int = 600) -> list[dict] | None:
    """以 Thinking 模型做兩輪全文審閱並回傳根本問題佇列。

    第一輪最多重試三次；第二輪若三次皆因服務／格式失敗，仍保留第一輪已可靠解析的
    問題，不讓覆蓋率補查的偶發失敗吞掉整份審閱。只有第一輪完全無法取得可靠結果才
    回 ``None``，呼叫端不得因此宣告證明通過。
    """
    base = (f"【題目】\n{statement}\n\n【已驗證參考解】\n{reference_proof}\n\n"
            f"【學生完整證明／目前合併草稿】\n{draft}")
    first = _retry_parsed(
        FULL_REVIEW_SYSTEM,
        base + "\n\n【第一輪任務】從頭到尾檢查，列出所有不同根本原因的問題。",
        _parse_issue_list, timeout=timeout, num_predict=8192, temperature=0.15)
    if first is None:
        # 結構化物件連續失敗時，改要求較簡單的 JSON 字串陣列；仍由同一 Thinking
        # 模型審閱，不使用本地規則猜測數學正誤。
        simple = _retry_parsed(
            FULL_REVIEW_TEXT_FALLBACK_SYSTEM, base, _parse_gaps,
            timeout=timeout, num_predict=8192, temperature=0.1, attempts=2)
        if simple is None:
            return None
        first = [_issue_from_fallback_text(item, i)
                 for i, item in enumerate(simple, 1)]

    first_json = json.dumps(first, ensure_ascii=False)
    second = _retry_parsed(
        FULL_REVIEW_SYSTEM,
        base + ("\n\n【第一輪已找到的問題】\n" + first_json +
                "\n\n【第二輪任務】重新從頭獨立複核，特別檢查第一輪可能漏掉的問題。"
                "不要重複第一輪同一根本原因；若只有其後果也不要另列。只輸出新問題。"),
        _parse_issue_list, timeout=timeout, num_predict=8192, temperature=0.1)
    if second is None:
        return first
    return _merge_root_issues(first, second)


def judge_local_revision(statement: str, reference_proof: str, current_draft: str,
                         issue: dict, student_revision: str,
                         timeout: int = 300) -> dict | None:
    """判斷學生局部回答是否修好目前唯一問題；不做字串比對或全文越界審閱。"""
    user = (
        f"【題目】\n{statement}\n\n"
        f"【已驗證參考解】\n{reference_proof}\n\n"
        f"【目前合併草稿】\n{current_draft}\n\n"
        f"【目前唯一要修的問題】\n"
        f"根本原因：{issue.get('root_cause', '')}\n"
        f"位置：{issue.get('location', '')}\n"
        f"說明：{issue.get('description', '')}\n"
        f"正確版本：{issue.get('correction', '')}\n\n"
        f"【學生局部回答】\n{student_revision}"
    )
    def parser(content):
        parsed = _parse_object(
            content, {"correct", "incorrect", "partial", "not_answer", "uncertain"})
        return None if parsed and parsed.get("verdict") == "uncertain" else parsed

    obj = _retry_parsed(
        LOCAL_REVISION_SYSTEM, user, parser, timeout=timeout,
        num_predict=4096, temperature=0.1, attempts=3,
        # 局部判定雖然短，但 Thinking 可能把 token 用在推理；每次都保留原本完整 timeout。
        per_attempt_timeout=timeout)
    if not obj:
        return None
    # 完整草稿只用來提供局部上下文。若第一輪判 partial／incorrect，再做一次明確
    # 限定 issue 範圍的複核，避免把尚未排入本輪的獨立錯誤誤當成學生沒有修好。
    # not_answer 不需重審；它沒有可供局部替換的實質內容。
    if obj.get("verdict") in {"partial", "incorrect"}:
        scoped = _retry_parsed(
            LOCAL_REVISION_SCOPE_SYSTEM, user, parser, timeout=timeout,
            num_predict=4096, temperature=0.05, attempts=3,
            per_attempt_timeout=timeout)
        if scoped:
            obj = scoped
    return {"verdict": obj["verdict"],
            "feedback": str(obj.get("feedback") or "").strip()[:300]}


def merge_proof_revision(statement: str, reference_proof: str, current_draft: str,
                         issue: dict, student_revision: str,
                         timeout: int = 300) -> str | None:
    """將已通過 Thinking 數學審閱的局部訂正實際合併回草稿。

    優先要求 Thinking 輸出完整合併稿；若長輸出逾時或 JSON 格式失敗，改要求較短的
    唯一 ``old_text/new_text`` patch，再由程式做精確替換。兩條路徑都只負責編輯，
    不會重新推翻上一階段已完成的數學判定。
    """
    user = (
        f"【題目】\n{statement}\n\n"
        f"【參考解（只供定位，不可替學生修其他錯誤）】\n{reference_proof}\n\n"
        f"【目前完整草稿】\n{current_draft}\n\n"
        f"【目前問題（內部資料）】\n{json.dumps(issue, ensure_ascii=False)}\n\n"
        f"【已確認正確的學生局部訂正】\n{student_revision}"
    )
    obj = _retry_parsed(MERGE_REVISION_SYSTEM, user, _parse_any_object,
                        timeout=timeout, num_predict=8192,
                        temperature=0.1, attempts=3,
                        # 完整草稿較長；不可把總時限除以三而讓每次 Thinking
                        # 還沒完成推理與輸出就被中止。
                        per_attempt_timeout=timeout)
    merged = str((obj or {}).get("merged_draft") or "").strip()
    if merged and merged != current_draft:
        return merged

    patch_obj = _retry_parsed(
        PATCH_REVISION_SYSTEM, user, _parse_any_object,
        timeout=timeout, num_predict=4096, temperature=0.05, attempts=3,
        per_attempt_timeout=timeout)
    old_text = str((patch_obj or {}).get("old_text") or "")
    new_text = str((patch_obj or {}).get("new_text") or "")
    # 只接受唯一且確切的定位，避免含糊位置（如「第二行」）造成誤改。
    if (old_text and new_text and old_text != new_text
            and current_draft.count(old_text) == 1):
        patched = current_draft.replace(old_text, new_text, 1).strip()
        if patched and patched != current_draft:
            return patched
    return None


def _walkthrough_output_lang(step: dict, student_answer: str) -> str:
    """以已呈現的步驟為主判定審閱輸出語言；數學符號不會覆蓋中文。"""
    step_text = " ".join(str(step.get(k) or "")
                         for k in ("explain", "check", "expected_answer"))
    if re.search(r"[\u3400-\u9fff]", step_text):
        return "zh"
    if re.search(r"[A-Za-z]{3,}", step_text):
        return "en"
    return "zh" if re.search(r"[\u3400-\u9fff]", student_answer or "") else "en"


def _walkthrough_answer_mentions_expected(step: dict, student_answer: str) -> bool:
    """只判斷 not_answer 是否值得複審，不以字串命中直接判定數學正確。"""
    compact_answer = re.sub(r"[\s$\\{}]", "", student_answer or "").lower()
    candidates = [step.get("expected_answer")]
    candidates.extend(step.get("accepted_answers") or [])
    return any(
        len(compact) >= 3 and compact in compact_answer
        for candidate in candidates
        if (compact := re.sub(r"[\s$\\{}]", "", str(candidate or "")).lower())
    )


def judge_walkthrough_answer(statement: str, reference_proof: str, step: dict,
                             student_answer: str, timeout: int = 300) -> dict | None:
    """以與 review/rectify 相同的思考型後盾，兩輪語意審閱 walkthrough 回答。

    回傳 ``{"verdict": ..., "feedback": ...}``；後盾離線、逾時、格式錯誤或
    verdict=uncertain 時回傳 None。呼叫端不得退回字串比對。
    """
    output_lang = _walkthrough_output_lang(step, student_answer)
    language = "繁體中文" if output_lang == "zh" else "English"
    user = (
        f"【輸出語言】\n{language}；所有文字欄位必須使用此語言。\n\n"
        f"【題目】\n{statement}\n\n"
        f"【已驗證參考解】\n{reference_proof}\n\n"
        f"【目前教學步驟】\n{step.get('explain', '')}\n\n"
        f"【確認問題】\n{step.get('check', '')}\n\n"
        f"【參考答案】\n{step.get('expected_answer', '')}\n"
        f"【其他可接受說法】\n"
        f"{json.dumps(step.get('accepted_answers') or [], ensure_ascii=False)}\n"
        f"【已知常見錯誤】\n"
        f"{json.dumps(step.get('common_errors') or [], ensure_ascii=False)}\n\n"
        f"【學生回答（只有這一次作答機會）】\n{student_answer}"
    )
    verdicts = {"correct", "incorrect", "partial", "not_answer", "uncertain"}

    def parser(content):
        parsed = _parse_object(content, verdicts)
        if not parsed or parsed.get("verdict") == "uncertain":
            return None
        # 沒有具體數學理由的非正確判定不可直接面向學生，應重新審閱。
        if parsed.get("verdict") in {"incorrect", "partial"}:
            root_error = str(parsed.get("root_error") or "").strip()
            correct_basis = str(parsed.get("correct_basis") or "").strip()
            if not root_error or not correct_basis:
                return None
            compact_root = re.sub(r"\s+", "", root_error.lower())
            if compact_root in {"答案錯誤", "回答錯誤", "答案不正確", "回答不正確",
                                "incorrect", "wronganswer"}:
                return None
            if output_lang == "zh":
                # 中文 session 的對外錯因至少要有中文診斷動詞；
                # 防止裸式子或英文審閱文字流到中文 Tutor。
                if (not re.search(r"[\u3400-\u9fff]", root_error + correct_basis)
                        or not re.search(r"誤|錯|漏|未|沒|只|將|把|混|聲稱|寫|用|缺",
                                         root_error)):
                    return None
            elif re.search(r"[\u3400-\u9fff]", root_error):
                return None
            # 錯因只診斷學生的第一個錯誤；正確依據僅供內部確認。
            # Driver 會另以 expected_answer 呈現完整正確答案，不在這裡重複。
            parsed["feedback"] = root_error
        return parsed

    # Thinking 的一次性輸出可能因 token 用盡、uncertain 或 JSON 格式波動而失敗；
    # 這些服務／格式問題不能被當成學生答錯。每次保留完整 timeout 與推理額度重試。
    obj = _retry_parsed(
        ANSWER_JUDGE_SYSTEM, user, parser, timeout=timeout,
        num_predict=8192, temperature=0.05, attempts=3,
        per_attempt_timeout=timeout)
    # not_answer 不需具體錯因，偶爾會把「含參考答案且另附正確推導」誤當沒作答。
    # 字串命中只觸發另一個語意審查，不直接宣告正確；額外推導仍由模型完整核對。
    if (obj and obj.get("verdict") == "not_answer"
            and _walkthrough_answer_mentions_expected(step, student_answer)):
        obj = None
    if not obj:
        # 完整參考證明可能過長；仍失敗時縮成判定所需的最小充分語境，仍交給同一
        # Thinking 模型做語意審閱，不退回 expected_answer 字串比對。
        compact_user = (
            f"【輸出語言】\n{language}；所有文字欄位必須使用此語言。\n\n"
            f"【題目】\n{statement}\n\n"
            f"【目前教學步驟】\n{step.get('explain', '')}\n\n"
            f"【確認問題】\n{step.get('check', '')}\n\n"
            f"【參考答案】\n{step.get('expected_answer', '')}\n"
            f"【其他可接受說法】\n"
            f"{json.dumps(step.get('accepted_answers') or [], ensure_ascii=False)}\n\n"
            f"【學生回答】\n{student_answer}"
        )
        obj = _retry_parsed(
            ANSWER_JUDGE_COMPACT_SYSTEM, compact_user, parser, timeout=timeout,
            num_predict=8192, temperature=0.05, attempts=3,
            per_attempt_timeout=timeout)
    if not obj:
        return None
    if obj.get("verdict") == "correct":
        # 第一輪若判對，仍由同一思考型模型以獨立 system 再審一輪。
        # 這一輪特別把「結論對」與「理由真的成立」分開，避免無效
        # 相消、錯誤等式等理由因結論碰巧正確而放行。
        audited = _retry_parsed(
            ANSWER_CORRECT_AUDIT_SYSTEM, user, parser, timeout=timeout,
            num_predict=8192, temperature=0.05, attempts=3,
            per_attempt_timeout=timeout)
        if not audited:
            return None
        obj = audited
    return {"verdict": obj["verdict"],
            "feedback": str(obj.get("feedback") or "").strip()[:300],
            "correct_basis": str(obj.get("correct_basis") or "").strip()[:500]}
