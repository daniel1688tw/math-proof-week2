# -*- coding: utf-8 -*-
"""auto_reference.py — 自我驗證備課管線：對沒有手寫參考解的題目自動生成並驗證參考解。

原則：助教必須「先自己證對」才有資格教（否則誤導學生）。
  PROVER（thinking，temp 0.7）× K 份候選 → VERIFIER（temp 0.2，獨立審閱）逐份判定
  → 有 pass（issues 可修補則 REPAIR 一輪再驗）→ verified 參考解 + 教學步驟
  → 全部 fail → unverified（TutorDriver 據此進入同學模式，誠實降級）。

教訓沿用 review_backstop：num_predict=8192（思考鏈空間）、JSON 解析括號平衡＋反斜線加倍。

CLI：
  python auto_reference.py --statement "證明 ..." --id NEW1 --out new_problem.json
  python auto_reference.py --problems xdomain_problems.json --id X2 --blind   # 已知解盲測
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = os.environ.get("REVIEW_MODEL", "qwen3-4b-thinking-2507:latest")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
K_CANDIDATES = int(os.environ.get("PROVER_K", "3"))

PROVER_SYSTEM = """你是嚴謹的數學系助教，要為一道證明題寫出「標準參考解」。
要求：繁體中文、LaTeX 記號、每一步都交代依據（引用定理要驗證前提、用到「某量非零」
「某集合非空」這類事實要明說）、量詞與不等號嚴格精確、結尾以 $\\blacksquare$ 收束。
只輸出證明本文，不要輸出任何其他說明。"""

VERIFIER_SYSTEM = """你是獨立的數學證明驗證員，用最嚴格的標準審查一份「將作為教學參考解」的證明。
逐步檢查：每一步推理是否成立、引用定理的前提是否驗證、依據是否明說、量詞與不等號方向、
計算是否正確、是否真的證出了題目要求的結論（不多不少）。
你沒有其他資料可對照，必須自己獨立推導驗證。
術語慣例：題目只寫「遞增／increasing」而未寫「嚴格／strictly」時，一律按**單調不減**理解；
證明寫成「單調不減／非減少」是精確表述，不算缺漏。
只輸出一個 JSON 物件：{"verdict": "pass" 或 "fail", "issues": ["…", "…"]}。
verdict=pass 表示此證明可以放心作為教學參考解（小瑕疵可列在 issues）；
verdict=fail 表示有實質錯誤或關鍵缺漏。不要輸出 JSON 以外的文字。"""

REPAIR_SYSTEM = """你是嚴謹的數學系助教。下面是一道題、一份大致正確的證明、與審閱者指出的問題清單。
請輸出修正後的完整證明（繁體中文、LaTeX、每步交代依據、$\\blacksquare$ 收束）。
只輸出證明本文。"""

SEGMENTER_SYSTEM = """你是數學教學設計者。把給定的、已驗證正確的參考證明切成 3 到 6 個
循序漸進的教學步驟。每步必須是學生一次能吸收的小單位，explain 要直接講清楚該步推理，
check 只問一個真正檢查本步推理連結的問題，而非抄錄結果、問顯然的是非題或要求逐字複誦。
問題必須完全可由本步 explain 作答：不得要求學生使用本步尚未講解的新運算、新定理或下一步
結論。若本步包含策略性選擇，優先問「為何這樣選能推進目標」，不要只問該選擇是否合法；
若本步核心是套用定義或定理，應檢查相關定義內容、適用前提或由此前提得到的推論。
若 explain 同時寫出「依據某個界或性質得到中間關係」與「計算中間量」，並以兩者
合成主要新結論，check 必須詢問這個主要推論如何成立；不可只問鏈尾的單一代數或計算等式。
確認問題可以問「如何推得目標結論」，但不得在問句中同時把關鍵中間不等式／關係與
目標結論完整寫出，令問句本身已包含答案。此時應只問「如何得到目標結論？」，讓學生
從 explain 中取回中間關係與理由。
expected_answer 是精簡但完整的評分判準，不是唯一字串答案。若 check 問「為什麼／如何」，
答案必須明說所用前提或已知條件、依據的定義／定理／性質，以及它如何導出所問結論；不得
只把問題中的結論換句話說，也不得只寫「由定義」「由某定理」而不說明相關內容。
accepted_answers 只列真正等價且同樣充分的說法。
嚴格保留量詞與不等號方向，不得把非嚴格結論改成嚴格結論；相鄰步驟不得重複同一問題。
證畢符號 $\\blacksquare$、$\\square$、QED 不是教學步驟，必須從步驟中省略。
只輸出符合指定 JSON Schema 的物件：
{"steps": [{"explain": "此步驟的完整講解（可含式子）",
  "core_idea": "本步最關鍵的定理、構造或性質；不含算式，最多 60 字",
  "check": "一個確認問題",
  "expected_answer": "精簡但包含推理依據的標準答案",
  "accepted_answers": ["可接受的等價短答"],
  "common_errors": ["常見但錯誤的短答"]}, …]}。
accepted_answers 與 common_errors 可以省略；其他四欄不可省略。
所有文字必須使用使用者指定的輸出語言。不要輸出 JSON 以外的文字。"""

SEGMENTER_REPAIR_SYSTEM = """你是數學教學步驟修補員。使用者會提供題目、已驗證參考
證明、上一輪候選步驟，以及本地結構驗收或獨立數學驗證器指出的具體問題。請保留已正確
的步驟，只修正問題清單涉及的欄位；必要時才拆分或合併相鄰步驟。修正後仍須有 3 到 6
步，每步只含一個推理單位與一個確認問題，量詞、不等號方向及定理前提必須忠於參考證明。
修補 check 時須確認它只檢查本步 explain 已教過的推理，不可超前；修補 expected_answer 時，
若問題問原因或方法，答案必須包含「前提／已知條件＋所用性質＋如何得到結論」，不可重述題目。
若問題只檢查推導鏈尾的小計算，而 explain 其實是用前提與該計算推出一個主要結論，
應把 check 改成檢查整個主要推論，expected_answer 也須包含其中各個依據。
若 check 把本步關鍵中間關係與最後結論一併寫在問句中，導致學生只需重複問句即可作答，
應移除問句中的關鍵中間關係，但完整保留在 explain 與 expected_answer 中。
不得加入證畢符號步驟。只輸出符合指定 JSON Schema 的完整 {"steps":[...]} 物件，不要
輸出修改說明或其他文字。"""

TEACH_STEPS_TRANSLATOR_SYSTEM = """你是數學教學內容翻譯員。把一套已切分且已驗證的教學
步驟翻成使用者指定語言。只能翻譯 explain、core_idea、check、expected_answer、
accepted_answers、common_errors 的自然語言；必須保留步驟數量、順序、step_id、所有數學
公式、量詞、不等號方向及嚴格／非嚴格語意。這不是重新切分：不得新增、刪除、合併或拆開
步驟。expected_answer 中原有的前提、依據與推導關係必須完整保留，不得縮成只重述結論的
短句。只輸出符合指定 JSON Schema 的完整 {"steps":[...]} 物件，不要輸出其他文字。"""

TEACH_STEPS_VERIFIER_SYSTEM = """你是數學教學步驟驗證員。題目與參考證明已確認正確；請審查
教學步驟是否逐步忠實於參考證明，尤其檢查量詞、定理前提、等號與不等號方向、嚴格/非嚴格
結論、expected_answer 與 common_errors 是否正確、步驟或問題是否重複，以及是否全程使用指定
語言。只把會使步驟「不可靠、無法依本步作答或答案鍵無法使用」的問題判為 fail；若目前問題
數學正確、與本步相關且可用答案鍵可靠審閱，不得只因另有更理想的問法而拒絕。逐項檢查：
1. check 是否只問 explain 已明確教過的內容；若必須額外移項、估計、套用新定理或使用下一步
   結論才可回答，這是阻斷問題，必須拒絕。
2. check 應檢查本步的推理連結。若只問數值、符號、正負或 yes/no，但仍能檢查本步一個正確且
   相關的必要理解，視為可用，不得僅因可改問更深入的問題而拒絕。
   若本步由「主要估計／關係」加上「中間量的計算」推出最終關係，check 應檢查
   兩者如何合成最終關係；但若只問中間量仍是數學正確、相關且可審閱的問題，這只是品質偏好，
   不可單獨造成 fail。只有問句已完整給出所有推理與答案、學生無須做任何判斷時才拒絕。
3. 若 check 問「為什麼／如何」，expected_answer 是否同時交代相關前提、所用定義／定理／性質，
   以及它如何導出結論。精簡但能唯一指出直接適用依據的答案仍屬可用；只有答案與問題不對齊、
   數學錯誤、純粹循環重述而無法據以審閱時才拒絕。
4. expected_answer 是否真正回答 check，且足以讓審閱者判斷學生理解推理，而不只是背出結果。
另須拒絕 check 與答案鍵不對齊、內容超出 explain、數學結論錯誤，或把 $\\blacksquare$/QED
當成一步。措辭可更好、問題深度可再提升等非阻斷偏好不要列入 issues。只輸出 JSON：
{"verdict":"pass"或"fail","issues":["具體指出步驟與問題"]}。
只要步驟安全、可作答、可審閱就輸出 pass 且 issues 為空；fail 只用於上述阻斷問題。"""

TRANSLATED_STEPS_VERIFIER_SYSTEM = """你是數學教學步驟的翻譯驗證員。原始步驟已經通過
完整的數學與教學品質驗證；你只需比對原始步驟與翻譯版：
1. 步數、順序、step_id 與每步的教學功能必須一致。
2. explain、check、expected_answer 及其他自然語言欄位必須忠實翻譯；check 與
   expected_answer 的對應關係不得改變。
3. 數學公式、量詞、等號、不等號方向與嚴格／非嚴格語意必須不變，並全程使用目標語言。
不要重新評選應該問哪個教學問題，也不要因個人偏好要求重新切分；那些已由原始步驟的驗證完成。
只輸出 JSON：{"verdict":"pass"或"fail","issues":["具體指出不忠實之處"]}。
完全忠實才輸出 pass 且 issues 為空。"""

SEGMENTER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["steps"],
    "properties": {
        "steps": {
            "type": "array", "minItems": 3, "maxItems": 6,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["explain", "core_idea", "check", "expected_answer"],
                "properties": {
                    "step_id": {"type": "string"},
                    "explain": {"type": "string"},
                    "core_idea": {"type": "string"},
                    "check": {"type": "string"},
                    "expected_answer": {"type": "string"},
                    "accepted_answers": {"type": "array", "items": {"type": "string"}},
                    "common_errors": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}

VERDICT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "issues"],
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "issues": {"type": "array", "items": {"type": "string"}},
    },
}

def _chat(system: str, user: str, temperature: float, timeout: int = 600,
          format_schema: dict | None = None) -> str | None:
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "stream": False,
        "think": True,
        "options": {"temperature": temperature, "top_p": 0.95, "top_k": 20,
                    "num_predict": 8192, "num_ctx": 12288},
    }
    if format_schema is not None:
        body["format"] = format_schema
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    return (data.get("message", {}).get("content") or "").strip() or None


def _balanced_spans(content: str, open_ch: str, close_ch: str) -> list:
    spans, depth, start = [], 0, None
    for i, ch in enumerate(content):
        if ch == open_ch:
            if depth == 0:
                start = i
            depth += 1
        elif ch == close_ch and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                spans.append(content[start:i + 1])
    return spans


def _loads_lenient(s: str):
    """LaTeX 跳脫（\\{ \\dots）是非法 JSON escape：原樣失敗→反斜線加倍重試。"""
    for attempt in (s, s.replace("\\", "\\\\")):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    return None


def parse_verdict(content: str | None) -> dict | None:
    if not content:
        return None
    for span in _balanced_spans(content, "{", "}"):
        obj = _loads_lenient(span)
        if isinstance(obj, dict) and obj.get("verdict") in ("pass", "fail"):
            issues = obj.get("issues") or []
            if isinstance(issues, list):
                return {"verdict": obj["verdict"],
                        "issues": [str(x)[:300] for x in issues[:5]]}
    return None


def _strlist(v) -> list:
    """把模型可能給的字串／陣列／None 統一成乾淨的字串陣列。"""
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        return []
    return [str(x).strip() for x in v if str(x).strip()][:5]


def _norm_step(o: dict, i: int) -> dict:
    """單一教學步驟正規化：固定欄位齊全＋穩定 step_id。

    step_id 是「這一輪實際講的是哪一步」的錨（TutorDriver 拿它比對上一輪呈現的步驟），
    模型沒給就依序編號——重點是同一份 teach_steps 內穩定且唯一，不是好看。
    """
    return {
        "step_id": str(o.get("step_id") or f"s{i + 1}"),
        "explain": str(o.get("explain") or "").strip(),
        "core_idea": str(o.get("core_idea") or "").strip(),
        "check": str(o.get("check") or "").strip(),
        "expected_answer": str(o.get("expected_answer") or "").strip(),
        "accepted_answers": _strlist(o.get("accepted_answers")),
        "common_errors": _strlist(o.get("common_errors")),
    }


def parse_steps(content: str | None) -> list | None:
    """解析 schema 物件或舊式陣列；不截斷步驟，讓驗收／修補處理步數問題。"""
    if not content:
        return None
    candidates = [content]
    candidates.extend(_balanced_spans(content, "{", "}"))
    candidates.extend(_balanced_spans(content, "[", "]"))
    for span in candidates:
        parsed = _loads_lenient(span)
        arr = parsed.get("steps") if isinstance(parsed, dict) else parsed
        # 寬鬆解析讓「步數／缺欄位」能進入具體修補，不在解析層整份丟棄。
        if (isinstance(arr, list) and 1 <= len(arr) <= 10
                and all(isinstance(o, dict) for o in arr)):
            return [_norm_step(o, i) for i, o in enumerate(arr)]
    return None


# 教學步驟的確定性驗收門檻（結構＋可保守判定的淺層答案品質）
_STEPS_MIN, _STEPS_MAX = 3, 6
_CHECK_MAX_CHARS = 140         # 允許問題帶齊本步條件；仍由單問句守衛限制只問一件事
_ANSWER_MAX_CHARS = 180        # 允許寫出「前提＋依據＋結論」，避免逼成只重述結果
_REASON_CHECK_RE = re.compile(
    r"為什麼|何以|如何|怎麼|說明.*原因|why\b|how\b|justify\b|explain\b", re.I)
_QED_ONLY_RE = re.compile(
    r"^\s*(?:\$?\s*\\(?:blacksquare|square|qedsymbol)\s*\$?|[∎■□]|Q\.?E\.?D\.?)\s*$",
    re.I,
)

# 這些問題值得先請 SEGMENTER 修補，但不會令一套數學正確、可作答且答案鍵
# 對齊的步驟失去可用性。前兩輪照常修補；最後一輪只剩這些項目時可送交
# 語意驗證，避免把教學偏好當成數學安全失敗。
_ADVISORY_STEP_ISSUE_CODES = {
    "invalid_core_idea", "check_too_long", "answer_too_long",
    "reason_answer_too_shallow", "circular_expected_answer",
    "duplicate_check_answer",
}


def _step_issue(code: str, message: str, index: int | None = None,
                step_id: str = "") -> dict:
    issue = {"code": code, "message": message}
    if index is not None:
        issue["step_index"] = index + 1
    if step_id:
        issue["step_id"] = step_id
    return issue


def _compact_quality_text(text: str) -> str:
    """只供保守品質守門：移除格式與問答框架，保留數學內容與實詞。"""
    text = re.sub(r"\\(?:left|right|big|Big|,|;|!|quad)\b", "", text)
    text = re.sub(r"^(?:因為|由於|所以|故|because|since|therefore)\s*", "", text,
                  flags=re.I)
    text = re.sub(r"為什麼|何以|如何|怎麼|why|how|justify|explain", "", text,
                  flags=re.I)
    return re.sub(r"[\s$\\{}()（）\[\]，。；：、,.!?？'\"]", "", text)


def teach_step_issues(steps) -> list[dict]:
    """回傳可直接交給修補模型的結構／淺層品質問題；空陣列表示本地驗收通過。"""
    if not isinstance(steps, list):
        return [_step_issue("not_a_list", "steps 必須是教學步驟陣列")]
    issues: list[dict] = []
    if len(steps) < _STEPS_MIN:
        issues.append(_step_issue(
            "too_few_steps", f"目前只有 {len(steps)} 步，需拆成 {_STEPS_MIN} 到 {_STEPS_MAX} 步"))
    elif len(steps) > _STEPS_MAX:
        issues.append(_step_issue(
            "too_many_steps", f"目前有 {len(steps)} 步，需合併為 {_STEPS_MIN} 到 {_STEPS_MAX} 步；不可直接截掉結論"))

    seen, seen_ids = [], set()
    for i, raw in enumerate(steps):
        if not isinstance(raw, dict):
            issues.append(_step_issue("step_not_object", "本步不是 JSON 物件", i))
            continue
        step_id = str(raw.get("step_id") or f"s{i + 1}")
        if step_id in seen_ids:
            issues.append(_step_issue("duplicate_step_id", "step_id 必須唯一", i, step_id))
        seen_ids.add(step_id)
        explain = str(raw.get("explain") or "").strip()
        core_idea = str(raw.get("core_idea") or "").strip()
        check = str(raw.get("check") or "").strip()
        answer = str(raw.get("expected_answer") or "").strip()
        for field, value in (("explain", explain), ("core_idea", core_idea),
                             ("check", check), ("expected_answer", answer)):
            if not value:
                issues.append(_step_issue(
                    f"missing_{field}", f"缺少必要欄位 {field}", i, step_id))
        if explain and _QED_ONLY_RE.fullmatch(explain):
            issues.append(_step_issue(
                "qed_only_step", "證畢符號不是教學步驟，請刪除並保留真正結論", i, step_id))
        if core_idea and (len(core_idea) > 60 or re.search(
                r"\$|=|≤|≥|<|>|≠|\\le\b|\\ge\b", core_idea)):
            issues.append(_step_issue(
                "invalid_core_idea", "core_idea 須是不含算式且不超過 60 字的短語", i, step_id))
        if len(check) > _CHECK_MAX_CHARS:
            issues.append(_step_issue(
                "check_too_long", f"check 超過 {_CHECK_MAX_CHARS} 字，請縮成單一短問題", i, step_id))
        if len(answer) > _ANSWER_MAX_CHARS:
            issues.append(_step_issue(
                "answer_too_long", f"expected_answer 超過 {_ANSWER_MAX_CHARS} 字，請保留判斷重點", i, step_id))
        if check and answer and _REASON_CHECK_RE.search(check):
            q_core = _compact_quality_text(check)
            a_core = _compact_quality_text(answer)
            if len(a_core) < 7:
                issues.append(_step_issue(
                    "reason_answer_too_shallow",
                    "check 詢問原因或方法，但 expected_answer 只給短結論；請補出相關前提、依據與推導",
                    i, step_id))
            elif (q_core and a_core and
                  difflib.SequenceMatcher(None, q_core, a_core).ratio() >= 0.88):
                issues.append(_step_issue(
                    "circular_expected_answer",
                    "expected_answer 幾乎只是改寫 check；請說明為何結論成立，而非重述結論",
                    i, step_id))
        if len(re.findall(r"[?？]", check)) > 1:
            issues.append(_step_issue(
                "multiple_questions", "check 同時問了多個問題，請只保留一問", i, step_id))
        cn, an = re.sub(r"\s", "", check), re.sub(r"\s", "", answer)
        if cn and an and any(
                difflib.SequenceMatcher(None, cn, pc).ratio() >= 0.85
                and difflib.SequenceMatcher(None, an, pa).ratio() >= 0.85
                for pc, pa in seen):
            issues.append(_step_issue(
                "duplicate_check_answer", "本步的確認問題與答案和前一步驟重複", i, step_id))
        seen.append((cn, an))
    return issues


def blocking_teach_step_issues(steps) -> list[dict]:
    """只回傳會令步驟不可靠或無法評分的硬問題。"""
    return [issue for issue in teach_step_issues(steps)
            if issue.get("code") not in _ADVISORY_STEP_ISSUE_CODES]


def validate_teach_steps(steps) -> bool:
    """確定性驗收：結構完整、單一問題、答案長度、非重複及原因答案不空泛。

    本地只處理能保守判定的問題；步驟範圍、教學價值與推理是否充分仍須由
    verify_teach_steps() 對照已驗證參考解做數學語意驗證。
    """
    return not teach_step_issues(steps)


def verify_teach_steps_detailed(statement: str, proof: str, steps: list, lang: str,
                                retries: int = 3) -> tuple[str, list[dict]]:
    """回傳 ``(pass|repair|unavailable, issues)``，區分內容問題與服務波動。"""
    local_issues = blocking_teach_step_issues(steps)
    if local_issues:
        return "repair", local_issues
    language = "繁體中文" if lang == "zh" else "English"
    prompt = (f"輸出語言：{language}\n題目：{statement}\n\n參考證明：\n{proof}\n\n"
              f"待驗證教學步驟：\n{json.dumps(steps, ensure_ascii=False)}")
    # 驗證服務逾時／格式失敗時只重試同一候選，不浪費一輪重新切分。
    for _ in range(max(1, retries)):
        verdict = parse_verdict(_chat(
            TEACH_STEPS_VERIFIER_SYSTEM, prompt, temperature=0.1, timeout=300,
            format_schema=VERDICT_SCHEMA))
        if not verdict:
            continue
        if verdict["verdict"] == "pass" and not verdict["issues"]:
            return "pass", []
        if verdict["issues"]:
            return "repair", [
                _step_issue("semantic_verifier", issue) for issue in verdict["issues"]
            ]
        # fail 卻沒有指出問題不可供修補；再問同一驗證器取得可操作理由。
    return "unavailable", [
        _step_issue("verifier_unavailable", "教學步驟驗證器未產生可解析且可操作的判定")
    ]


def verify_teach_steps(statement: str, proof: str, steps: list, lang: str) -> bool:
    """向後相容的布林介面；詳細原因由 verify_teach_steps_detailed() 提供。"""
    status, _ = verify_teach_steps_detailed(statement, proof, steps, lang)
    return status == "pass"


def verify_translated_teach_steps_detailed(
        statement: str, proof: str, source_steps: list, translated_steps: list,
        target_lang: str, retries: int = 3) -> tuple[str, list[dict]]:
    """只驗證翻譯忠實度，不對已通過的原始步驟重做問題選擇。

    原始步驟已通過 ``verify_teach_steps_detailed`` 的完整數學與教學
    品質審查。翻譯階段若再以「我會選另一個問題」為由拒絕，會把可靠的
    英文步驟誤判成沒有中文版。此處因此只檢查數學與問答語意是否忠實保留。
    """
    local_issues = blocking_teach_step_issues(translated_steps)
    if local_issues:
        return "repair", local_issues
    language = "繁體中文" if target_lang == "zh" else "English"
    prompt = (
        f"目標語言：{language}\n題目：{statement}\n\n參考證明：\n{proof}\n\n"
        f"原始已驗證步驟：\n{json.dumps(source_steps, ensure_ascii=False)}\n\n"
        f"待驗證翻譯：\n{json.dumps(translated_steps, ensure_ascii=False)}"
    )
    for _ in range(max(1, retries)):
        verdict = parse_verdict(_chat(
            TRANSLATED_STEPS_VERIFIER_SYSTEM, prompt, temperature=0.1,
            timeout=300, format_schema=VERDICT_SCHEMA))
        if not verdict:
            continue
        if verdict["verdict"] == "pass" and not verdict["issues"]:
            return "pass", []
        if verdict["issues"]:
            return "repair", [
                _step_issue("translation_semantic_verifier", issue)
                for issue in verdict["issues"]
            ]
    return "unavailable", [_step_issue(
        "translation_verifier_unavailable",
        "翻譯驗證器未產生可解析且可操作的判定")]


def segment_proof(statement: str, proof: str, lang: str | None = None,
                  verify: bool = True, attempts: int = 3,
                  diagnostics: list | None = None) -> list | None:
    """生成一次、依具體錯誤修補至多兩次；全數失敗回 None。

    ``lang`` 由 walkthrough session 鎖定後傳入，避免同一個步驟索引因臨場
    語言切換而指到另一套不同內容的步驟。不採用未經語意驗證的機械 fallback。
    """
    lg = lang or _detect_lang(statement)
    language = "繁體中文" if lg == "zh" else "English"
    base_prompt = f"輸出語言：{language}\n\n題目：{statement}\n\n參考證明：\n{proof}"
    previous_output = ""
    repair_issues: list[dict] = []

    def record(round_no: int, event: str, issues: list[dict] | None = None):
        if diagnostics is not None:
            diagnostics.append({"round": round_no, "event": event,
                                "issues": issues or []})

    for round_idx in range(max(1, attempts)):
        round_no = round_idx + 1
        if round_idx == 0 or not previous_output:
            system, prompt = SEGMENTER_SYSTEM, base_prompt
            event = "generate"
        else:
            system = SEGMENTER_REPAIR_SYSTEM
            prompt = (
                f"輸出語言：{language}\n\n題目：{statement}\n\n參考證明：\n{proof}\n\n"
                f"上一輪候選：\n{previous_output}\n\n"
                f"必須修正的問題：\n{json.dumps(repair_issues, ensure_ascii=False)}"
            )
            event = "repair"

        raw = None
        # 服務／空輸出屬傳輸失敗；先重試同一請求，不把它誤算成內容修補失敗。
        for _ in range(2):
            raw = _chat(system, prompt, temperature=0.1 if event == "repair" else 0.2,
                        timeout=300, format_schema=SEGMENTER_SCHEMA)
            if raw:
                break
        if not raw:
            record(round_no, f"{event}_unavailable")
            continue
        previous_output = raw
        steps = parse_steps(raw)
        if not steps:
            repair_issues = [_step_issue(
                "parse_error", "候選無法解析為含 steps 陣列的 JSON Schema 物件")]
            record(round_no, "parse_error", repair_issues)
            continue

        repair_issues = teach_step_issues(steps)
        if repair_issues:
            # 把正規化後候選交回修補，避免模型再次處理原始格式雜訊。
            previous_output = json.dumps({"steps": steps}, ensure_ascii=False)
            blocking = [issue for issue in repair_issues
                        if issue.get("code") not in _ADVISORY_STEP_ISSUE_CODES]
            if blocking or round_no < max(1, attempts):
                record(round_no, "local_validation_failed", repair_issues)
                continue
            # 最後一輪若只剩非阻斷品質項目，不在本地直接作廢；仍必須通過
            # 下方數學／範圍／答案對齊語意驗證。
            record(round_no, "local_quality_advisory", repair_issues)
        if not verify:
            record(round_no, "accepted_without_semantic_verifier")
            return steps

        status, repair_issues = verify_teach_steps_detailed(
            statement, proof, steps, lg, retries=3)
        record(round_no, f"semantic_{status}", repair_issues)
        if status == "pass":
            return steps
        if status == "unavailable":
            # detailed verifier 已在同一候選上重試三次；服務仍不可用時停止，
            # 避免把傳輸問題誤當內容問題，也避免無意義地增加最多九次呼叫。
            return None
        previous_output = json.dumps({"steps": steps}, ensure_ascii=False)
    return None


def translate_teach_steps(statement: str, proof: str, steps: list,
                          target_lang: str, attempts: int = 3,
                          diagnostics: list | None = None) -> list | None:
    """翻譯既有可靠步驟而不重新切分；翻譯後仍通過結構與數學語意驗證。"""
    if not steps or blocking_teach_step_issues(steps):
        return None
    language = "繁體中文" if target_lang == "zh" else "English"
    expected_ids = [str(s.get("step_id") or f"s{i + 1}")
                    for i, s in enumerate(steps)]
    previous_output = json.dumps({"steps": steps}, ensure_ascii=False)
    repair_issues: list[dict] = []

    def record(round_no: int, event: str, issues: list[dict] | None = None):
        if diagnostics is not None:
            diagnostics.append({"round": round_no, "event": event,
                                "issues": issues or []})

    for round_idx in range(max(1, attempts)):
        prompt = (
            f"目標語言：{language}\n\n題目：{statement}\n\n參考證明：\n{proof}\n\n"
            f"原始已驗證步驟：\n{json.dumps({'steps': steps}, ensure_ascii=False)}"
        )
        if round_idx:
            prompt += (f"\n\n上一輪翻譯候選：\n{previous_output}\n\n"
                       f"必須修正的問題：\n"
                       f"{json.dumps(repair_issues, ensure_ascii=False)}")
        raw = None
        for _ in range(2):
            raw = _chat(TEACH_STEPS_TRANSLATOR_SYSTEM, prompt, temperature=0.1,
                        timeout=300, format_schema=SEGMENTER_SCHEMA)
            if raw:
                break
        if not raw:
            record(round_idx + 1, "translation_unavailable")
            continue
        previous_output = raw
        translated = parse_steps(raw)
        if not translated:
            repair_issues = [_step_issue(
                "parse_error", "翻譯候選無法解析為含 steps 陣列的 JSON 物件")]
            record(round_idx + 1, "translation_parse_error", repair_issues)
            continue

        repair_issues = teach_step_issues(translated)
        translated_ids = [str(s.get("step_id") or "") for s in translated]
        if len(translated) != len(steps):
            repair_issues.append(_step_issue(
                "translation_step_count_changed",
                f"翻譯前後步數必須同為 {len(steps)}，不得重新切分"))
        if translated_ids != expected_ids:
            repair_issues.append(_step_issue(
                "translation_step_ids_changed", "翻譯不得更動 step_id 或步驟順序"))
        if repair_issues:
            previous_output = json.dumps({"steps": translated}, ensure_ascii=False)
            blocking = [issue for issue in repair_issues
                        if issue.get("code") not in _ADVISORY_STEP_ISSUE_CODES]
            if blocking or round_idx + 1 < max(1, attempts):
                record(round_idx + 1, "translation_local_validation_failed", repair_issues)
                continue
            record(round_idx + 1, "translation_local_quality_advisory", repair_issues)

        # 原始步驟已完成教學品質審查；此處只驗證翻譯忠實度，
        # 避免同一套步驟因不同語言的自由文字而被重新評選。
        status, repair_issues = verify_translated_teach_steps_detailed(
            statement, proof, steps, translated, target_lang, retries=3)
        record(round_idx + 1, f"translation_semantic_{status}", repair_issues)
        if status == "pass":
            return translated
        if status == "unavailable":
            return None
        previous_output = json.dumps({"steps": translated}, ensure_ascii=False)
    return None


# ── 句級保底切分（SEGMENTER 失敗／驗收不過時用）────────────────────────────────
# 舊版只按空行切段：參考解常常只有一段，於是「第一步」幾乎是整份證明，
# 確認問題還是無法驗證的「你能複述嗎」——等於沒有逐步教學。
_QED_RE = re.compile(r"\$?\s*\\(?:blacksquare|square|qedsymbol)\s*\$?|[∎■□]|Q\.?E\.?D\.?",
                     re.I)
_SENT_END_RE = re.compile(r"(?<=[。！？；])|(?<=[.!?;])(?=\s)")
# 子句邊界：CJK 逗號／冒號，或「後面接空白」的半形逗號——半形逗號一律切會把
# $\max\{|a_1|,\dots\}$、區間 $[a,b]$ 從中間剖開（實測產生「因為 f 在 [a」這種步驟）。
_CLAUSE_END_RE = re.compile(r"(?<=[，：])|(?<=,)(?=\s)")
_MIN_UNIT_CHARS = 8            # 比這更短的片段（「因此」「故」）併回前一句，不獨立成步

# 「一段數學內容」：$…$ 行內數學、\[…\] 顯示數學，或不含空白的裸算式片段
_MATH_SPAN_RE = re.compile(r"\$\$[^$]*\$\$|\$[^$]*\$|\\\[.*?\\\]|\\\(.*?\\\)", re.S)
# 裸算式：不含空白的連續數學符號串（含關係符）。刻意不吃空白——吃了會把
# 「Since a_n converges to L, there is N with |a_n-L| <」整句當成算式。
_BARE_RELATION_RE = re.compile(r"[A-Za-z0-9\\'()\[\]{}^_|.,+\-*/=<>≤≥≠]{3,}")
_RELATION_RE = re.compile(r"[=<>≤≥≠]|\\le\b|\\ge\b|\\lt\b|\\gt\b|\\ne\b")
_CONCLUSION_HEAD_RE = re.compile(r".*(?:所以|因此|故|於是|從而|得到|可知|即|therefore|hence|thus)")


def _clean_unit(text: str) -> str:
    """去掉 QED 記號與首尾空白（保留「得證」這類有語意的字，只拿掉純符號）。"""
    return _QED_RE.sub("", text or "").strip()


def _proof_units(proof: str) -> list:
    """把證明切成句級單位：先段落、再句子，過短的片段併回前一句。"""
    units = []
    for para in re.split(r"\n\s*\n", proof or ""):
        para = _clean_unit(para)
        if not para:
            continue
        for sent in _SENT_END_RE.split(para):
            sent = _clean_unit(sent)
            if not sent:
                continue
            if units and len(sent) < _MIN_UNIT_CHARS:
                units[-1] = (units[-1] + sent).strip()
            else:
                units.append(sent)
    return units


def _split_longest(units: list) -> list:
    """把最長的一個單位再從子句邊界對半切（步數不足 3 步時用）。"""
    if not units:
        return units
    i = max(range(len(units)), key=lambda k: len(units[k]))
    parts = [p for p in _CLAUSE_END_RE.split(units[i]) if p.strip()]
    if len(parts) < 2:
        return units
    mid = len(parts) // 2
    head, tail = "".join(parts[:mid]).strip(), "".join(parts[mid:]).strip()
    if len(head) < _MIN_UNIT_CHARS or len(tail) < _MIN_UNIT_CHARS:
        return units
    return units[:i] + [head, tail] + units[i + 1:]


def _balanced_units(units: list, lo: int = _STEPS_MIN, hi: int = _STEPS_MAX) -> list:
    """把句級單位調整到 lo–hi 個：太多依原順序均勻合併，太少從最長的再切。"""
    units = [u for u in units if u.strip()]
    if not units:
        return units
    while len(units) < lo:
        after = _split_longest(units)
        if len(after) == len(units):          # 再也切不動（例如整份只有一句話）
            break
        units = after
    if len(units) > hi:
        merged, per = [], -(-len(units) // hi)     # 無條件進位，維持原順序
        for i in range(0, len(units), per):
            merged.append("".join(units[i:i + per]).strip())
        units = merged[:hi]
    return units


def _math_contents(text: str) -> list:
    """擷取一段文字裡的數學片段（含 $…$ 與裸算式），依出現順序回傳。"""
    out = [m.group(0).strip() for m in _MATH_SPAN_RE.finditer(text or "")]
    rest = _MATH_SPAN_RE.sub(" ", text or "")
    out += [m.group(0).strip() for m in _BARE_RELATION_RE.finditer(rest)
            if len(m.group(0).strip()) >= 3 and _RELATION_RE.search(m.group(0))]
    return [x for x in out if x]


def _fallback_expected(unit: str) -> tuple:
    """(標準答案, 是否為關係式)：優先取最後一個關係式，否則取結論子句。

    ⚠️ 任何路徑都**不做字元截斷**：答案鍵可能被原樣顯示給學生（單次作答未通過時），
    截在 LaTeX 中間會變成 `$\\left|\\dfrac{3n-1-3(n+2)}{` 這種殘句（實測過）。
    太長就換一個候選，換不到就整段保留。
    """
    rel = [m for m in _math_contents(unit) if _RELATION_RE.search(m)]
    if rel:
        # 取**最長**的那個關係式，不是最後一個：句尾常掛一個括號裡的附帶條件
        # （「…$\\ge\\binom{n}{2}=\\dfrac{n(n-1)}{2}$（$n\\ge 2$）」），取最後一個
        # 會把答案鍵訂成 `$n\\ge 2$`——2026-08-07 守門的 A6/zh 教學步驟實測踩到，
        # 學生答出真正的關鍵關係式反而會被判錯。長度是「主關係式」的合理代理。
        fit = [m for m in rel if len(m) <= _ANSWER_MAX_CHARS]
        return (max(fit, key=len) if fit else min(rel, key=len)), True
    tail = unit.strip().rstrip("。.！!")
    m = _CONCLUSION_HEAD_RE.match(tail)
    if m and len(tail) - m.end() >= 4:
        tail = tail[m.end():].strip()
    else:                                      # 沒有連接詞就取最後一個子句
        parts = [p for p in _CLAUSE_END_RE.split(tail) if p.strip()]
        tail = parts[-1].strip() if parts else tail
    return tail.strip("，,：: "), False


_FALLBACK_CHECK = {
    ("zh", True): "這一步得到的關鍵關係式是什麼？",
    ("zh", False): "這一步得到的結論是什麼？",
    ("en", True): "What key relation does this step establish?",
    ("en", False): "What conclusion does this step reach?",
}


def _detect_lang(text: str) -> str:
    """教學步驟／參考解的語言標記——**直接沿用 driver 的判定，兩端不可分岔**。

    2026-08-07 code review I-3：driver 那邊把判定前的剝除強化成
    `_strip_language_neutral_math()`（另含 `\\(…\\)`／`\\[…\\]`／裸算式），這裡卻還是
    舊寫法，於是以算式為主的中文兩端判定相反（實測
    `故 \\(…\\dfrac{7}{n+2}<\\varepsilon\\) 成立。` → driver 判 zh、這裡判 en）。
    下游是 `teach_steps_lang` 寫錯與「中文講解配英文確認問句」。
    延用既有的**函式內延遲 import** 模式（tutor_driver 只在函式內
    import auto_reference，故無載入期循環）；真的取不到時退回舊行為，不讓備課掛掉。
    """
    try:
        from tutor_driver import detect_lang
        return detect_lang(text)
    except ImportError:
        chars = [c for c in re.sub(r"\$[^$]*\$|\\[A-Za-z]+", " ", text or "")
                 if not c.isspace()]
        if not chars:
            return "zh"
        return "en" if sum(1 for c in chars if "一" <= c <= "鿿") / len(chars) < 0.10 else "zh"


_CORE_IDEA_FORMULA_RE = re.compile(
    r"\$|=|≤|≥|<|>|≠|\\le\b|\\ge\b|\\lt\b|\\gt\b|\\neq\b"
)


def _fallback_core_idea(explain: str, lang: str) -> str:
    """舊步驟沒有 core_idea 時，產生不含算式的短標籤供 Level 2 使用。"""
    plain = re.sub(r"\$[^$]*\$|\\\([^)]*\\\)|\\\[[^]]*\\\]", " ", explain or "")
    plain = re.sub(r"\\[A-Za-z]+(?:\{[^{}]*\})?", " ", plain)
    plain = _CORE_IDEA_FORMULA_RE.sub(" ", plain)
    plain = re.sub(r"\s+", " ", plain).strip(" ，,。；;：:")
    if not plain:
        return ("Use the key condition and theorem of this step" if lang == "en"
                else "使用本步的關鍵條件與定理")
    return plain[:60].rstrip(" ，,。；;：:")


def ensure_checkable_steps(steps: list, lang: str | None = None) -> list:
    """替舊式／缺欄位的教學步驟補齊可評分所需的欄位（冪等，內容不改寫）。

    只補「缺的欄位」：模型或手寫已經給了 check / expected_answer 就原樣保留。
    它保證不了的是品質——把一個模糊的舊問題自動變成好的短問答不在能力範圍內，
    這裡只保證流程走得下去（每一步都有可比對的答案鍵）。
    """
    out = []
    for i, s in enumerate(steps or []):
        if not isinstance(s, dict) or not str(s.get("explain") or "").strip():
            continue
        explain = str(s["explain"]).strip()
        lg = lang or _detect_lang(explain)
        core_idea = str(s.get("core_idea") or "").strip()
        if not core_idea or _CORE_IDEA_FORMULA_RE.search(core_idea):
            core_idea = _fallback_core_idea(explain, lg)
        answer = str(s.get("expected_answer") or "").strip()
        is_rel = bool(_RELATION_RE.search(answer)) if answer else False
        if not answer:
            answer, is_rel = _fallback_expected(explain)
        check = str(s.get("check") or "").strip() or _FALLBACK_CHECK[(lg, is_rel)]
        out.append(_norm_step({**s, "explain": explain, "core_idea": core_idea,
                               "check": check,
                               "expected_answer": answer}, i))
    return out


def fallback_steps(proof: str, lang: str | None = None) -> list:
    """歷史資料相容／離線診斷用的句級切分器；不進入可靠 walkthrough 執行路徑。

    它只能保證步數範圍與欄位完整，保證不了問題、答案鍵和講解的數學語意對齊；因此
    build_reference() 與 TutorDriver 都不會在 SEGMENTER 驗證失敗時自動採用它。
    """
    lg = lang or _detect_lang(proof)
    units = _balanced_units(_proof_units(proof)) or [_clean_unit(proof) or proof]
    steps = []
    for i, u in enumerate(units):
        answer, is_rel = _fallback_expected(u)
        steps.append(_norm_step({"explain": u, "core_idea": _fallback_core_idea(u, lg),
                                 "check": _FALLBACK_CHECK[(lg, is_rel)],
                                 "expected_answer": answer}, i))
    return steps


def build_reference(statement: str, k: int = K_CANDIDATES,
                    verbose: bool = True, progress_cb=None) -> dict:
    """回傳 {status, reference_proof?, teach_steps?, log}。

    progress_cb(stage, detail)：選填回呼，於每個階段觸發（stage ∈ PROVER/VERIFIER/
    REPAIR/SEGMENTER）。不傳則行為與原本完全一致（向後相容）。
    """
    def _emit(stage: str, detail: str = ""):
        if progress_cb:
            progress_cb(stage, detail)
    log = []
    for i in range(k):
        if verbose:
            print(f"  [PROVER {i+1}/{k}] 生成候選證明…")
        _emit("PROVER", f"{i+1}/{k}")
        proof = _chat(PROVER_SYSTEM, f"題目：{statement}", temperature=0.7)
        if not proof:
            log.append({"candidate": i, "event": "prover_failed"})
            continue
        if verbose:
            print(f"  [VERIFIER] 驗證候選 {i+1}（{len(proof)} 字）…")
        _emit("VERIFIER", f"候選 {i+1}")
        v = parse_verdict(_chat(
            VERIFIER_SYSTEM, f"題目：{statement}\n\n待驗證的證明：\n{proof}",
            temperature=0.2))
        log.append({"candidate": i, "verdict": v})
        if v is None:
            continue
        if v["verdict"] == "pass":
            if v["issues"]:
                if verbose:
                    print(f"  [REPAIR] pass 但有 {len(v['issues'])} 項小瑕疵，修補後複驗…")
                _emit("REPAIR", f"{len(v['issues'])} 項小瑕疵")
                fixed = _chat(REPAIR_SYSTEM,
                              f"題目：{statement}\n\n證明：\n{proof}\n\n"
                              f"審閱意見：{json.dumps(v['issues'], ensure_ascii=False)}",
                              temperature=0.2)
                if fixed:
                    v2 = parse_verdict(_chat(
                        VERIFIER_SYSTEM,
                        f"題目：{statement}\n\n待驗證的證明：\n{fixed}",
                        temperature=0.2))
                    log.append({"candidate": i, "repaired_verdict": v2})
                    if v2 and v2["verdict"] == "pass":
                        proof = fixed
            if verbose:
                print("  [SEGMENTER] 切分教學步驟…")
            _emit("SEGMENTER", "")
            # 語言只判一次、往下傳（code review I-3）：原本 fallback_steps／
            # ensure_checkable_steps／teach_steps_lang 是三個各自為政的判定，
            # 逐步驟自判時，一個以算式為主的中文步驟很容易配上英文確認問句。
            steps_lang = _detect_lang(statement)
            segment_diagnostics = []
            steps = segment_proof(statement, proof, lang=steps_lang,
                                  diagnostics=segment_diagnostics)
            log.append({"candidate": i, "event": "segmenter_attempts",
                        "attempts": segment_diagnostics})
            source = "segmenter" if steps else "unavailable"
            variants: dict[str, list] = {}
            variant_sources: dict[str, str] = {}
            if not steps:
                log.append({"candidate": i, "event": "segmenter_unavailable"})
                if verbose:
                    print("  [SEGMENTER] 三次輸出或驗證未通過；"
                          "不啟用不可靠的機械式逐步教學。")
                steps = []
            else:
                variants[steps_lang] = steps
                variant_sources[steps_lang] = "segmenter"
                # 英文題目常在學生開口後轉成中文 session。成功切分後立刻翻譯同一套
                # 步驟並快取，walkthrough 前只選語言版本，不再重新切一次證明。
                if steps_lang == "en":
                    translation_diagnostics = []
                    zh_steps = translate_teach_steps(
                        statement, proof, steps, target_lang="zh",
                        diagnostics=translation_diagnostics)
                    log.append({"candidate": i, "event": "teach_steps_translation_zh",
                                "attempts": translation_diagnostics})
                    if zh_steps:
                        variants["zh"] = zh_steps
                        variant_sources["zh"] = "translation"
            out = {"status": "verified", "reference_proof": proof,
                   "teach_steps": steps, "teach_steps_lang": steps_lang,
                   "teach_steps_source": source,
                   "teach_steps_initial_status": "success" if steps else "failed",
                   "log": log}
            for variant_lang, variant_steps in variants.items():
                out[f"teach_steps_{variant_lang}"] = variant_steps
                out[f"teach_steps_source_{variant_lang}"] = variant_sources[variant_lang]
            return out
    return {"status": "unverified", "log": log}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--statement", help="直接給題目敘述")
    ap.add_argument("--problems", help="從既有題目檔取題（json 陣列）")
    ap.add_argument("--id", default="NEW1")
    ap.add_argument("--blind", action="store_true",
                    help="盲測：忽略檔內既有參考解，只用 statement")
    ap.add_argument("--out", help="輸出題目 json（單題物件）")
    ap.add_argument("-k", type=int, default=K_CANDIDATES)
    args = ap.parse_args()

    if args.problems:
        items = json.loads(Path(args.problems).read_text(encoding="utf-8"))
        prob = next(p for p in items if p["id"] == args.id)
        statement = prob["statement"]
    elif args.statement:
        statement = args.statement
    else:
        ap.error("需要 --statement 或 --problems")

    print(f"[{args.id}] 備課開始：{statement[:60]}…")
    result = build_reference(statement, k=args.k)
    print(f"[{args.id}] status = {result['status']}")

    out = {"id": args.id, "statement": statement,
           "grounding": "auto_verified" if result["status"] == "verified" else "unverified"}
    if result["status"] == "verified":
        out["reference_proof"] = result["reference_proof"]
        out["teach_steps"] = result["teach_steps"]
        out["teach_steps_lang"] = result.get("teach_steps_lang", "zh")
        out["teach_steps_source"] = result.get("teach_steps_source", "segmenter")
        out["teach_steps_initial_status"] = result.get("teach_steps_initial_status")
        for variant_lang in ("zh", "en"):
            if result.get(f"teach_steps_{variant_lang}"):
                out[f"teach_steps_{variant_lang}"] = result[f"teach_steps_{variant_lang}"]
                out[f"teach_steps_source_{variant_lang}"] = result.get(
                    f"teach_steps_source_{variant_lang}")
        print(f"  參考解 {len(result['reference_proof'])} 字、"
              f"教學步驟 {len(result['teach_steps'])} 步")
    if args.out:
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"  已寫入 {args.out}")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
