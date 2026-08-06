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
只輸出一個 JSON 物件：{"verdict": "pass" 或 "fail", "issues": ["…", "…"]}。
verdict=pass 表示此證明可以放心作為教學參考解（小瑕疵可列在 issues）；
verdict=fail 表示有實質錯誤或關鍵缺漏。不要輸出 JSON 以外的文字。"""

REPAIR_SYSTEM = """你是嚴謹的數學系助教。下面是一道題、一份大致正確的證明、與審閱者指出的問題清單。
請輸出修正後的完整證明（繁體中文、LaTeX、每步交代依據、$\\blacksquare$ 收束）。
只輸出證明本文。"""

SEGMENTER_SYSTEM = """你是數學教學設計者。把給定的參考證明切成 3 到 6 個循序漸進的教學步驟，
每步是學生一次能吸收的小單位，並為每步設計一個「確認理解」的小問題（答案應該很短）。
只輸出 JSON 陣列：[{"explain": "此步驟要講解的內容（可含式子）", "check": "確認理解的小問題"}, …]。
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


def parse_steps(content: str | None) -> list | None:
    if not content:
        return None
    for span in _balanced_spans(content, "[", "]"):
        arr = _loads_lenient(span)
        if (isinstance(arr, list) and 2 <= len(arr) <= 8 and
                all(isinstance(o, dict) and o.get("explain") and o.get("check")
                    for o in arr)):
            return [{"explain": str(o["explain"]), "check": str(o["check"])}
                    for o in arr[:6]]
    return None


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


def validate_ladder(hints: list, statement: str, proof: str) -> bool:
    """提示梯的五道確定性驗收：條數／長度／不帶新算式／不洩漏參考解／兩條不雷同。

    門檻皆以 hint_ladders.json 的 33 條手寫提示（人工驗過的黃金標準）校準，實測零誤判。
    任一條不過即整份丟棄——寧可退回 driver 既有的通用保底句，
    也不冒「提示本身洩漏答案或給算式」的風險（生成的梯不像參考解有 VERIFIER 獨立審）。

    長度上限刻意比 prompt 要求的 15–45 字寬：prompt 訂目標、驗收訂紅線，
    只差一兩字不該整份丟棄。
    """
    # lazy import：tutor_driver._ensure_teach_steps() 會反向 import 本模組，
    # 模組層互 import 會形成循環。
    from tutor_driver import gives_new_equation, leaks_reference

    if not isinstance(hints, list) or len(hints) != 2:
        return False
    for h in hints:
        if not isinstance(h, str) or not (12 <= len(h.strip()) <= 60):
            return False
        if gives_new_equation(h, statement):      # 保護等級 2 禁算式白名單不被污染
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
    """
    hints = parse_ladder(_chat(
        LADDER_SYSTEM, f"題目：{statement}\n\n參考證明：\n{proof}",
        temperature=0.2, timeout=300))
    if hints and validate_ladder(hints, statement, proof):
        return hints
    return None


def fallback_steps(proof: str) -> list:
    """SEGMENTER 失敗時的確定性保底：以空行段落切分＋通用確認問句。"""
    paras = [p.strip() for p in re.split(r"\n\s*\n", proof) if p.strip()]
    if len(paras) < 2:                       # 只有一段就對半切句子
        sents = [s for s in re.split(r"(?<=[。！？])", proof) if s.strip()]
        mid = max(1, len(sents) // 2)
        paras = ["".join(sents[:mid]), "".join(sents[mid:])]
    return [{"explain": p, "check": "這一步的推理你能自己複述一遍嗎？"}
            for p in paras[:6]]


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
            steps = segment_proof(statement, proof) or fallback_steps(proof)
            if verbose:
                print("  [LADDER] 生成分級提示…")
            _emit("LADDER", "")
            hints = build_ladder(statement, proof)
            if verbose:
                print("  [LADDER] " + ("產出 2 條提示" if hints
                                        else "未通過驗收，改用通用提示"))
            out = {"status": "verified", "reference_proof": proof,
                   "teach_steps": steps, "log": log}
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
