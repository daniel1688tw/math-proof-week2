# -*- coding: utf-8 -*-
"""measure_stuck_detection.py — 量測 is_stuck() 對「真實學生訊息」的準確度。

動機（2026-08-02）：確定性層大量依賴詞表比對，而詞表只認得列舉過的說法。
手工造句實測 is_stuck 命中率僅 zh 27% / en 20%，但手工造句不能代表真實分佈——
要決定「值不值得改寫成結構訊號」，得先有真實語料上的 precision / recall。

做法：
  1. 從 regression_scores/*_dialogues.json 取出所有學生訊息（去重）。
  2. 分層抽樣：is_stuck=True 的全取（測 precision）＋ False 的隨機抽樣（測 recall）。
  3. 用評審後端批次標註 ground truth（一次 10 則，回 JSON 陣列）。
  4. 標註存檔（stuck_labels.json），之後重算不必再呼叫 API。
  5. 印出混淆矩陣與漏接／誤判實例。

用法：
  python dataset/measure_stuck_detection.py            # 有標註存檔就直接重算
  python dataset/measure_stuck_detection.py --relabel  # 強制重新標註
  python dataset/measure_stuck_detection.py --sample 240
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("REVIEW_BACKSTOP", "0")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tutor_driver import is_stuck  # noqa: E402

LABELS_PATH = HERE / "stuck_labels.json"

LABEL_PROMPT = """你在標註數學助教對話的語料。下面是學生（人類）對助教說的話，每則獨立。

對每一則判定：這位學生是不是在表達「我answer不出來 / 我卡住了 / 我需要更多幫助才能前進」？

判定準則：
- true：明確表示不會、沒想法、看不懂、跟不上、想放棄、要求更多提示——**不論用什麼措辭**。
- false：提出了自己的推導或猜想（即使不確定、即使錯）、回答了助教的問題、提出具體疑問、
  表達理解、道謝收尾、或談論與「卡住」無關的事。
- 重點：帶著實質嘗試但語氣不確定（例如「我覺得應該是 X，但不太確定」）算 **false**，
  因為他有內容可以往下接；完全交不出內容才算 true。

【待標註訊息】
{items}

只輸出一個 JSON 陣列，長度與訊息數相同，元素為 true/false，順序對應。
例如：[true, false, false, true]"""


def load_student_messages() -> list[dict]:
    seen, out = set(), []
    for f in sorted(glob.glob(str(HERE / "regression_scores" / "*_dialogues.json"))):
        for rec in json.loads(Path(f).read_text(encoding="utf-8")):
            for who, txt in rec.get("history", []):
                if who != "學生":
                    continue
                t = (txt or "").strip()
                if not t or t in seen:
                    continue
                seen.add(t)
                out.append({"text": t, "lang": rec.get("lang", "zh"),
                            "persona": rec.get("persona", "")[:3]})
    return out


def stratified_sample(msgs: list[dict], n: int, seed: int = 20260802) -> list[dict]:
    """is_stuck=True 全取（precision 分母小，全測）；False 隨機抽 n 則（測 recall）。"""
    rng = random.Random(seed)
    pos = [m for m in msgs if is_stuck(m["text"])]
    neg = [m for m in msgs if not is_stuck(m["text"])]
    rng.shuffle(neg)
    return pos + neg[:n]


def label_batch(batch: list[dict]) -> list[bool] | None:
    from regression_suite import claude_call, _balanced, _loads_lenient
    items = "\n".join(f"{i + 1}. {m['text']}" for i, m in enumerate(batch))
    raw = claude_call(LABEL_PROMPT.format(items=items), timeout=300)
    if not raw:
        return None
    for span in _balanced(raw, "[", "]"):
        obj = _loads_lenient(span)
        if isinstance(obj, list) and len(obj) == len(batch):
            return [bool(x) for x in obj]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=200, help="抽樣的 is_stuck=False 則數")
    ap.add_argument("--relabel", action="store_true")
    ap.add_argument("--batch", type=int, default=10)
    args = ap.parse_args()

    msgs = load_student_messages()
    print(f"[語料] 去重後的真實學生訊息 {len(msgs)} 則"
          f"（is_stuck 判為卡住 {sum(1 for m in msgs if is_stuck(m['text']))} 則）")

    sample = stratified_sample(msgs, args.sample)
    cached = {}
    if LABELS_PATH.exists() and not args.relabel:
        cached = {d["text"]: d["label"] for d in
                  json.loads(LABELS_PATH.read_text(encoding="utf-8"))}
        print(f"[標註] 讀到既有標註 {len(cached)} 則")

    todo = [m for m in sample if m["text"] not in cached]
    if todo:
        print(f"[標註] 需新標註 {len(todo)} 則，每批 {args.batch} 則")
        for i in range(0, len(todo), args.batch):
            batch = todo[i:i + args.batch]
            labels = label_batch(batch)
            if labels is None:
                print(f"  批次 {i // args.batch + 1} 標註失敗（跳過，不計入）")
                continue
            for m, lb in zip(batch, labels):
                cached[m["text"]] = lb
            print(f"  批次 {i // args.batch + 1}/{(len(todo) - 1) // args.batch + 1} 完成")
        LABELS_PATH.write_text(json.dumps(
            [{"text": t, "label": v} for t, v in cached.items()],
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[標註] 已存檔 {LABELS_PATH.name}（{len(cached)} 則）")

    graded = [m for m in sample if m["text"] in cached]
    tp = fp = fn = tn = 0
    misses, falses = [], []
    for m in graded:
        pred, truth = is_stuck(m["text"]), cached[m["text"]]
        if pred and truth:
            tp += 1
        elif pred and not truth:
            fp += 1
            falses.append(m)
        elif not pred and truth:
            fn += 1
            misses.append(m)
        else:
            tn += 1

    print(f"\n[混淆矩陣] 已標註 {len(graded)} 則")
    print(f"    真陽 {tp:3d}   假陽 {fp:3d}")
    print(f"    假陰 {fn:3d}   真陰 {tn:3d}")
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    print(f"    precision {prec:.3f}｜recall {rec:.3f}｜F1 {f1:.3f}")
    print("    （recall 是重點：漏接＝學生明說不會卻拿不到提示升級）")

    print(f"\n[漏接實例] 該判卡住卻沒判，共 {fn} 則：")
    for m in misses[:15]:
        print(f"    [{m['lang']}] {m['text'][:78]}")
    print(f"\n[誤判實例] 判成卡住但其實不是，共 {fp} 則：")
    for m in falses[:8]:
        print(f"    [{m['lang']}] {m['text'][:78]}")


if __name__ == "__main__":
    main()
