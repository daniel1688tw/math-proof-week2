# -*- coding: utf-8 -*-
"""auto_reference.py — 自我驗證備課管線：對沒有手寫參考解的題目自動生成並驗證參考解。

原則：助教必須「先自己證對」才有資格教（否則誤導學生）。
  PROVER（thinking，temp 0.7）× K 份候選 → VERIFIER（temp 0.2，獨立審閱）逐份判定
  → 有 pass（issues 可修補則 REPAIR 一輪再驗）→ verified 參考解 + 教學步驟
    + 分級提示（LADDER 階段，TutorDriver 等級 2 用；驗收不過就不寫該欄位）
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

SEGMENTER_SYSTEM = """你是數學教學設計者。把給定的參考證明切成 3 到 6 個循序漸進的教學步驟，
每步是學生一次能吸收的小單位，並為每步設計一個「確認理解」的小問題。

每個步驟輸出這些欄位：
- explain：這一步要講解的內容（可含式子）。
- check：只問一件事的確認問題，答案必須很短（一個式子、一個名詞，或是／否）。
- expected_answer：check 的標準答案本身，越短越好，不要寫理由或多餘的句子。
- accepted_answers：其他也算對的等價寫法（字串陣列，沒有就給 []）。
- common_errors：學生最可能寫錯的答案（字串陣列，沒有就給 []）。

術語慣例：題目只寫「遞增／increasing」而未寫「嚴格／strictly」時，一律按**單調不減**理解。

只輸出 JSON 陣列，例如：
[{"explain": "…", "check": "…", "expected_answer": "…", "accepted_answers": [], "common_errors": []}, …]
不要輸出 JSON 以外的文字。"""

LADDER_SYSTEM = """你是數學教學設計者。下面給你一道證明題與它的參考證明，
請設計「分級提示」，供助教在學生連續卡住時逐條使用。

要求：
1. 恰好兩條，依序對應這份證明的兩個關鍵轉折：第一條給前半的關鍵，第二條給後半的關鍵。
2. 每條都要明確點出一個定理、構造或性質的「名稱與作用」——學生看到名稱後要能自己接手推導。
3. 絕對不可出現任何算式、等式或不等式。只講名稱與想法，計算全部留給學生。
4. 每條 15 到 45 字，繁體中文。
5. 不可直接抄參考證明裡的句子，要用自己的話重新講。

只輸出 JSON 陣列：["第一條提示", "第二條提示"]。不要輸出 JSON 以外的文字。"""


def _chat(system: str, user: str, temperature: float, timeout: int = 600) -> str | None:
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "stream": False,
        "think": True,
        "options": {"temperature": temperature, "top_p": 0.95, "top_k": 20,
                    "num_predict": 8192, "num_ctx": 12288},
    }).encode("utf-8")
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
        "explain": str(o["explain"]).strip(),
        "check": str(o["check"]).strip(),
        "expected_answer": str(o.get("expected_answer") or "").strip(),
        "accepted_answers": _strlist(o.get("accepted_answers")),
        "common_errors": _strlist(o.get("common_errors")),
    }


def parse_steps(content: str | None) -> list | None:
    """解析 SEGMENTER 輸出。保留答案鍵；2 步輸出仍解析得出（相容舊資料），
    步數是否合格交給 validate_teach_steps() 判——解析與驗收分離。"""
    if not content:
        return None
    for span in _balanced_spans(content, "[", "]"):
        arr = _loads_lenient(span)
        if (isinstance(arr, list) and 2 <= len(arr) <= 8 and
                all(isinstance(o, dict) and o.get("explain") and o.get("check")
                    for o in arr)):
            return [_norm_step(o, i) for i, o in enumerate(arr[:6])]
    return None


# 教學步驟的確定性驗收門檻（與 validate_ladder 同型：只擋「結構性不可用」，不評品質）
_STEPS_MIN, _STEPS_MAX = 3, 6
_CHECK_MAX_CHARS = 80          # 確認問題要短；長問句多半塞了兩件事
_ANSWER_MAX_CHARS = 60         # 標準答案要短；長答案代表 check 不是短問答


def validate_teach_steps(steps) -> bool:
    """五道確定性驗收：步數／欄位齊全／確認問題只問一件事／答案夠短／問題不重複。

    刻意**不**再叫一個 LLM 當 verifier（LADDER 階段的同一取捨）：多一次思考型呼叫
    要多等最長 300 秒，而它擋不掉的錯（答案鍵與問題語意不合）正是它最可能誤判的地方；
    真正的安全網是 TutorDriver 那邊的重試上限——答案鍵若寫壞，學生最多卡兩輪就被帶過。
    驗收不過即整份丟棄改走 fallback，最壞情況等同於今日行為。
    """
    if not isinstance(steps, list) or not (_STEPS_MIN <= len(steps) <= _STEPS_MAX):
        return False
    seen = []
    for s in steps:
        if not isinstance(s, dict):
            return False
        explain, check = str(s.get("explain") or "").strip(), str(s.get("check") or "").strip()
        answer = str(s.get("expected_answer") or "").strip()
        if not explain or not check or not answer:
            return False
        if len(check) > _CHECK_MAX_CHARS or len(answer) > _ANSWER_MAX_CHARS:
            return False
        if len(re.findall(r"[?？]", check)) > 1:      # 一次問兩件事 → 無法用單一答案鍵評分
            return False
        # 重複判定要「問題」與「答案」同時雷同才算：問法一樣但答案不同（保底切分
        # 每步都問「這一步得到的關鍵關係式是什麼？」）仍能區分步驟，不算重複；
        # 連答案都一樣才是真的有一步沒在教東西。
        # ⚠️ 不可把兩者串起來比對——共用的長問句會把相似度整體推過門檻，
        #    實測 5 步保底切分（答案各不相同）會被自己的驗收判退。
        cn, an = re.sub(r"\s", "", check), re.sub(r"\s", "", answer)
        if any(difflib.SequenceMatcher(None, cn, pc).ratio() >= 0.85
               and difflib.SequenceMatcher(None, an, pa).ratio() >= 0.85
               for pc, pa in seen):
            return False
        seen.append((cn, an))
    return True


def parse_ladder(content: str | None) -> list | None:
    """把模型輸出解析成恰 2 條非空提示；結構不合回 None。

    梯長固定 2（手寫 hint_ladders.json 的 17 題裡 15 題為 2 條，取眾數）。
    照 parse_steps 的作法：括號平衡取出候選 JSON 陣列，逐段寬鬆解析
    （LaTeX 的 \\{ \\dots 是非法 JSON escape，需反斜線加倍重試）。
    """
    if not content:
        return None
    for span in _balanced_spans(content, "[", "]"):
        arr = _loads_lenient(span)
        if (isinstance(arr, list) and len(arr) == 2
                and all(isinstance(s, str) and s.strip() for s in arr)):
            return [s.strip() for s in arr]
    return None


# 提示梯專用的禁算式閘：只要出現 $ 或任一關係符即退。
# 不沿用 tutor_driver.gives_new_equation()——後者以空白切詞比對「題目以外的新算式」，
# 遇到 LaTeX 標準寫法（等號兩側有空白，如 `$\delta = \varepsilon / M$`）會切出長度僅 1
# 的 token「=」，正規化後 < 3 字被跳過 → 整條提示放行（實測繞過案例，見 Finding 1）。
# LADDER 的規格本來就是「完全不含算式」（prompt 規則 3），不是「不含題目以外的算式」，
# 嚴格閘語意更貼合、也不受空白切詞的邊界影響。
_LADDER_FORMULA_RE = re.compile(
    r"\$|=|≤|≥|<|>|≠|\\le\b|\\ge\b|\\lt\b|\\gt\b|\\neq\b"
)


def validate_ladder(hints: list, statement: str, proof: str) -> bool:
    """提示梯的五道確定性驗收：條數／長度／不帶算式／不洩漏參考解／兩條不雷同。

    門檻以 `load_problems_with_ladders()` 載得到、且有 `reference_proof` 的 16 題
    共 33 條手寫提示（人工驗過的黃金標準）校準，實測零誤判
    （`hint_ladders.json` 全部 17 題共 36 條；ADV1 在未載入的 `adv_test_problem.json`）。
    任一條不過即整份丟棄——寧可退回 driver 既有的通用保底句，
    也不冒「提示本身洩漏答案或給算式」的風險（生成的梯不像參考解有 VERIFIER 獨立審）。

    長度上限刻意比 prompt 要求的 15–45 字寬：prompt 訂目標、驗收訂紅線，
    只差一兩字不該整份丟棄。

    ⚠️ 洩漏閘是空跑的邊界：`leaks_reference` 在正規化後長度 < 15 時直接回 False
    （n-gram 下限），而提示長度下限只有 12 字，正規化（去空白／`$`／LaTeX 裝飾）後
    可能落在 15 字以下——手寫梯裡就有實例。實務上 12–14 字洩不了什麼，
    但這道閘對這類極短提示不生效，不是「五道閘一律生效」。
    """
    # lazy import：tutor_driver._ensure_teach_steps() 會反向 import 本模組，
    # 模組層互 import 會形成循環。
    from tutor_driver import leaks_reference

    if not isinstance(hints, list) or len(hints) != 2:
        return False
    for h in hints:
        if not isinstance(h, str) or not (12 <= len(h.strip()) <= 60):
            return False
        if _LADDER_FORMULA_RE.search(h):           # 保護等級 2 禁算式白名單不被污染
            return False
        if leaks_reference(h, proof, exclude=statement):
            return False
    return difflib.SequenceMatcher(None, hints[0], hints[1]).ratio() < 0.85


def segment_proof(statement: str, proof: str) -> list | None:
    """把參考解切成教學步驟（TutorDriver 逐步教學臨場呼叫用）；失敗回 None。"""
    return parse_steps(_chat(
        SEGMENTER_SYSTEM, f"題目：{statement}\n\n參考證明：\n{proof}",
        temperature=0.2, timeout=300))


def build_ladder(statement: str, proof: str) -> list | None:
    """為已驗證的參考解生成分級提示梯（TutorDriver 等級 2 用）；失敗回 None。

    失敗即現況：呼叫端不寫 hint_ladder 欄位，_ladder() 回 []，
    driver 走既有的通用保底句路徑。不做確定性保底切分——
    從參考解機械切出來的片段當提示有洩漏風險，寧可退回通用句。

    連例外也收斂到 None：呼叫端拿到的是已經跑完 PROVER→VERIFIER→SEGMENTER
    的已驗證參考解，不該因為提示梯這個附加階段丟例外而把整份結果賠掉。
    """
    try:
        hints = parse_ladder(_chat(
            LADDER_SYSTEM, f"題目：{statement}\n\n參考證明：\n{proof}",
            temperature=0.2, timeout=300))
        if hints and validate_ladder(hints, statement, proof):
            return hints
        return None
    except Exception:
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

    ⚠️ 任何路徑都**不做字元截斷**：答案鍵會被原樣顯示給學生（重試上限後的揭示句），
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
    """教學步驟／參考解的語言標記（CJK 占比 <10% 視為英文）。"""
    chars = [c for c in re.sub(r"\$[^$]*\$|\\[A-Za-z]+", " ", text or "") if not c.isspace()]
    if not chars:
        return "zh"
    return "en" if sum(1 for c in chars if "一" <= c <= "鿿") / len(chars) < 0.10 else "zh"


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
        answer = str(s.get("expected_answer") or "").strip()
        is_rel = bool(_RELATION_RE.search(answer)) if answer else False
        if not answer:
            answer, is_rel = _fallback_expected(explain)
        check = str(s.get("check") or "").strip() or _FALLBACK_CHECK[(lg, is_rel)]
        out.append(_norm_step({**s, "explain": explain, "check": check,
                               "expected_answer": answer}, i))
    return out


def fallback_steps(proof: str, lang: str | None = None) -> list:
    """SEGMENTER 失敗／驗收不過時的確定性保底：句級切成 3–6 步，每步都有答案鍵。

    ⚠️ 這是語法式保底，不是第二個 LLM：它保證的是步數範圍、欄位完整、可進入評分流程，
    保證不了問題與答案鍵在數學語意上對得準。教學品質仍以通過驗收的 SEGMENTER 輸出為優先。
    """
    lg = lang or _detect_lang(proof)
    units = _balanced_units(_proof_units(proof)) or [_clean_unit(proof) or proof]
    steps = []
    for i, u in enumerate(units):
        answer, is_rel = _fallback_expected(u)
        steps.append(_norm_step({"explain": u, "check": _FALLBACK_CHECK[(lg, is_rel)],
                                 "expected_answer": answer}, i))
    return steps


def build_reference(statement: str, k: int = K_CANDIDATES,
                    verbose: bool = True, progress_cb=None) -> dict:
    """回傳 {status, reference_proof?, teach_steps?, log}。

    progress_cb(stage, detail)：選填回呼，於每個階段觸發（stage ∈ PROVER/VERIFIER/
    REPAIR/SEGMENTER/LADDER）。不傳則行為與原本完全一致（向後相容）。
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
            steps = segment_proof(statement, proof)
            source = "segmenter"
            if not validate_teach_steps(steps):
                # 所有失敗路徑（Ollama 離線／解析不出／驗收不過）收斂到同一個結果
                print("[SEGMENTER] 輸出或驗證未通過；改用可驗證的句級保底步驟。")
                steps, source = fallback_steps(proof), "fallback"
            steps = ensure_checkable_steps(steps)
            if verbose:
                print("  [LADDER] 生成分級提示…")
            _emit("LADDER", "")
            hints = build_ladder(statement, proof)
            if verbose:
                print("  [LADDER] " + ("產出 2 條提示" if hints
                                        else "未通過驗收，改用通用提示"))
            out = {"status": "verified", "reference_proof": proof,
                   "teach_steps": steps, "teach_steps_lang": _detect_lang(proof),
                   "teach_steps_source": source, "log": log}
            if hints:                       # 驗收不過就不寫這個鍵（等同今日行為）
                out["hint_ladder"] = hints
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
        if result.get("hint_ladder"):
            out["hint_ladder"] = result["hint_ladder"]
        print(f"  參考解 {len(result['reference_proof'])} 字、"
              f"教學步驟 {len(result['teach_steps'])} 步、"
              f"分級提示 {len(result.get('hint_ladder') or [])} 條")
    if args.out:
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"  已寫入 {args.out}")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
