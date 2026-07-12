# -*- coding: utf-8 -*-
"""review_backstop.py — 審閱後盾：思考型模型對學生草稿/嘗試做參考解對照複核。

混合架構定位（FINAL_VERDICT 的教訓）：思考型模型 S2 糾錯 4.75 全場最強（解剖銳利），
但無訓練約束、對抗情境不可靠 → 不讓它面對學生，只讓它在幕後「找碴」。
判斷交給思考型模型、說話仍由微調模型包裝成引導語氣：

  學生交草稿/嘗試 → find_gaps()（本模組，Ollama 思考型） → 缺漏清單
                  → 注入 TutorDriver 的 review/rectify 階段指示 → 微調模型引導式說出

Ollama 不可用或逾時 → 回傳 None，driver 靜默降級回原行為（部署不因後盾死掉而中斷）。

環境變數：
  REVIEW_MODEL    後盾模型（預設 qwen3-4b-thinking-2507:latest）
  OLLAMA_URL      chat API（預設 http://localhost:11434/api/chat）
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

MODEL = os.environ.get("REVIEW_MODEL", "qwen3-4b-thinking-2507:latest")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

# 找碴員 system：只做判斷、只輸出結構化清單（不需引導語氣——那是微調模型的事）
CRITIC_SYSTEM = """你是數學系課程的證明審閱助教。使用者會給你：題目、正確的參考解、學生寫的草稿或嘗試。

任務：對照參考解，以**嚴格的教學標準**（不是數學家的「顯然可略」標準）找出草稿的缺漏或錯誤：
1. 數學錯誤：斷言不成立、計算錯、包含關係或不等號方向反了、量詞順序錯誤。
2. 依據缺漏：某一步結論依賴的事實沒有明說——即使該事實顯然成立也算缺漏。
   例：由 $cv=0$ 推 $c=0$ 卻沒說 $v\\ne0$；套用鴿籠原理卻沒陳述「幾個物件、幾個類別」；
   引用定理卻沒驗證其前提。教學上這些都必須讓學生補上。
3. 嚴格與非嚴格不等號、特例未排除。

規則：
- 草稿正確且依據完整的步驟不要質疑；風格與詳略不算問題。
- 每項用一句話精確說明：在哪一步、缺了什麼或錯在哪，並給正確版本。
- 最多列 3 項，按嚴重程度排序；完全沒有問題就輸出空陣列。
- 只輸出 JSON 字串陣列（如 ["…","…"]），不要輸出任何其他文字。"""

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
                return [g.strip()[:200] for g in arr[:3] if g.strip()]
            break
    return None


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
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": CRITIC_SYSTEM},
                     {"role": "user", "content": user}],
        "stream": False,
        "think": True,
        # num_predict 必須留給思考鏈足夠空間：3072 在真實證明案例會被思考吃光
        # （done_reason=length、正文空白）。8192 實測 X4/H3 案例思考 4-6k token。
        "options": {"temperature": 0.2, "top_p": 0.95, "top_k": 20,
                    "num_predict": 8192, "num_ctx": 12288},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    return _parse_gaps((data.get("message", {}).get("content") or "").strip())
