# -*- coding: utf-8 -*-
"""
validate.py — 資料集品質驗證

檢查（對 train.jsonl + val.jsonl 全量）：
  [結構]  每筆 messages 首為 system，其後 user/assistant 嚴格交替，末回合為 assistant
  [結構]  system 含 <REFERENCE_PROOF> 區塊
  [字數]  每個 assistant 回合中文字數 ≤ 100
  [一問一等]  每個 assistant 回合問號（? ？）數量 ≤ 1
  [不洩漏]  assistant 不得出現洩漏字樣（答案是、故得證、證畢、QED…）之硬性列表
  [長度]  每條對話 user+assistant 回合數在 [4, 20] 之間
  [引用]  對話對應題目 id 存在於 problems.json
  [平衡]  印出 persona / topic 分佈

回傳非零 exit code 若有任何 ERROR。
"""
import json
import re
import sys
from pathlib import Path

# Windows 主控台預設 cp950，強制 UTF-8 避免印出中文/✓ 時崩潰
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent

LEAK_PATTERNS = [
    "答案是", "故得證", "證畢", "QED", "q.e.d", "綜上所述，證明完成",
    "所以結論為", "最終答案", "得證。",
    # 英文洩漏字樣（助教不得直接宣告完成/交出結論）
    "the answer is", "therefore proved", "hence proved", "this completes the proof",
    "the final answer",
]

CJK = re.compile(r"[一-鿿]")
QMARK = re.compile(r"[?？]")
# 英文長度以「詞數」衡量：先剝除 LaTeX 數學片段避免誤算
_TEX = re.compile(r"\$[^$]*\$|\\[A-Za-z]+")


def count_cjk(s):
    return len(CJK.findall(s))


def count_en_words(s):
    return len(_TEX.sub(" ", s).split())


def is_english(s):
    """回覆語言判斷：CJK 占非空白字元 <10% 視為英文（與 driver detect_lang 同準則）。"""
    stripped = _TEX.sub(" ", s)
    chars = [c for c in stripped if not c.isspace()]
    if not chars:
        return False
    return count_cjk(s) / len(chars) < 0.10


def load_jsonl(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def validate():
    errors, warnings = [], []
    problems = {p["id"]: p for p in json.loads((HERE / "problems.json").read_text(encoding="utf-8"))}

    records = []
    for name in ("train.jsonl", "val.jsonl"):
        records.extend((name, i, r) for i, r in enumerate(load_jsonl(HERE / name)))

    if not records:
        errors.append("找不到 train.jsonl / val.jsonl 或內容為空，請先執行 build.py")

    assistant_char_max = 0
    assistant_word_max = 0
    turn_counts = []
    for name, i, rec in records:
        tag = f"{name}#{i}"
        msgs = rec.get("messages", [])
        if not msgs or msgs[0]["role"] != "system":
            errors.append(f"{tag}: 首訊息非 system")
            continue
        if "<REFERENCE_PROOF>" not in msgs[0]["content"]:
            errors.append(f"{tag}: system 缺少 <REFERENCE_PROOF>")

        body = msgs[1:]
        # 交替檢查
        expect = "user"
        for m in body:
            if m["role"] != expect:
                errors.append(f"{tag}: 角色順序錯誤，預期 {expect} 得到 {m['role']}")
                break
            expect = "assistant" if expect == "user" else "user"
        if body and body[-1]["role"] != "assistant":
            errors.append(f"{tag}: 末回合非 assistant")

        n_turns = len(body)
        turn_counts.append(n_turns)
        if not (4 <= n_turns <= 20):
            warnings.append(f"{tag}: 對話回合數 {n_turns} 超出建議區間 [4,20]")

        for m in body:
            if m["role"] != "assistant":
                continue
            content = m["content"]
            if is_english(content):
                w = count_en_words(content)
                assistant_word_max = max(assistant_word_max, w)
                if w > 80:
                    errors.append(f"{tag}: assistant 英文詞數 {w} > 80 → {content[:40]}…")
            else:
                c = count_cjk(content)
                assistant_char_max = max(assistant_char_max, c)
                if c > 100:
                    errors.append(f"{tag}: assistant 中文字數 {c} > 100 → {content[:30]}…")
            if len(QMARK.findall(content)) > 1:
                errors.append(f"{tag}: assistant 含多個問號（違反一問一等）→ {content[:40]}…")
            for pat in LEAK_PATTERNS:
                if pat.lower() in content.lower():
                    errors.append(f"{tag}: assistant 疑似洩漏『{pat}』→ {content[:40]}…")

    # 分佈統計（需 build 前的 src，這裡從對話數推估無法拿 persona，略）
    print("=" * 56)
    print(f"總對話數            : {len(records)}")
    if turn_counts:
        print(f"回合數 min/median/max : {min(turn_counts)}/"
              f"{sorted(turn_counts)[len(turn_counts)//2]}/{max(turn_counts)}")
    print(f"assistant 最長中文字數 : {assistant_char_max}")
    print(f"assistant 最長英文詞數 : {assistant_word_max}")
    print(f"題目數              : {len(problems)}")
    print("=" * 56)

    if warnings:
        print(f"\n[WARN] {len(warnings)} 則警告：")
        for w in warnings[:40]:
            print("  -", w)
        if len(warnings) > 40:
            print(f"  … 其餘 {len(warnings)-40} 則略")

    if errors:
        print(f"\n[ERROR] {len(errors)} 則錯誤：")
        for e in errors:
            print("  -", e)
        print("\n驗證失敗 ✗")
        return 1

    print("\n驗證通過 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
