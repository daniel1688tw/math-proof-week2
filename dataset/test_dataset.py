# -*- coding: utf-8 -*-
"""test_dataset.py — 資料集完整性與統計測試（validate.py 之外的補充檢查）。

檢查項目：
  1. 來源統計：題目/對話 依 主題、persona、kind 的分佈
  2. 引用完整性：每條對話的 problem_id 皆存在於 problems.json
  3. grounding：抽樣確認 train/val 每筆 system 都含正確題目的參考解片段
  4. 題目注入：第一個 user 回合確實以「題目：」開頭
  5. 訓練信號：統計 assistant 回合總數（真正的訓練 token 來源）
  6. JSONL 可解析、messages 結構正確
"""
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"


def load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    fails = []

    # ---- 來源 ----
    problems = {}
    topic_counter = Counter()
    for p in sorted(SRC.glob("problems_*.py")):
        for prob in load_module(p).PROBLEMS:
            problems[prob["id"]] = prob
            topic_counter[prob["topic"]] += 1

    dialogues = []
    for p in sorted(SRC.glob("dialogues_*.py")):
        for d in load_module(p).DIALOGUES:
            dialogues.append(d)

    persona_counter = Counter(d["persona"] for d in dialogues)
    kind_counter = Counter(d["kind"] for d in dialogues)
    topic_dlg_counter = Counter(problems[d["problem_id"]]["topic"] for d in dialogues
                                if d["problem_id"] in problems)

    print("題目主題分佈 :", dict(topic_counter))
    print("對話 persona :", dict(persona_counter))
    print("對話 kind    :", dict(kind_counter))
    print("對話主題分佈 :", dict(topic_dlg_counter))
    print(f"題目數 {len(problems)}，對話數 {len(dialogues)}")

    # 2. 引用完整性
    for d in dialogues:
        if d["problem_id"] not in problems:
            fails.append(f"對話引用不存在題目 {d['problem_id']}")

    # 5. 訓練信號（來源端）
    n_assistant = sum(sum(1 for t in d["turns"] if t["role"] == "assistant") for d in dialogues)
    n_user = sum(sum(1 for t in d["turns"] if t["role"] == "user") for d in dialogues)
    print(f"assistant 訓練信號 {n_assistant}，user 回合 {n_user}")

    # 每題至少該有的對話數（3 核心 + 4 擴充 = 7）
    per_problem = Counter(d["problem_id"] for d in dialogues)
    short_problems = [pid for pid in problems if per_problem[pid] < 7]
    if short_problems:
        fails.append(f"下列題目對話數 < 7：{short_problems}")

    # ---- 產出端 ----
    def load_jsonl(name):
        with open(HERE / name, encoding="utf-8") as f:
            return [json.loads(x) for x in f if x.strip()]

    train = load_jsonl("train.jsonl")
    val = load_jsonl("val.jsonl")
    print(f"train {len(train)}，val {len(val)}，合計 {len(train)+len(val)}")

    # 3 + 4 + 6：逐筆結構、grounding、題目注入
    for name, recs in (("train", train), ("val", val)):
        for i, r in enumerate(recs):
            msgs = r.get("messages", [])
            if not msgs or msgs[0]["role"] != "system":
                fails.append(f"{name}#{i} 首非 system")
                continue
            if "<REFERENCE_PROOF>" not in msgs[0]["content"] or "</REFERENCE_PROOF>" not in msgs[0]["content"]:
                fails.append(f"{name}#{i} system 缺參考解標籤")
            if len(msgs) < 2 or msgs[1]["role"] != "user":
                fails.append(f"{name}#{i} 第二則非 user")
            elif not msgs[1]["content"].startswith("題目："):
                fails.append(f"{name}#{i} user 未注入題目陳述")

    # grounding 抽樣：確認 system 內的參考解確實來自某題（比對片段）
    proof_snippets = [(pid, p["reference_proof"][:20]) for pid, p in problems.items()]
    matched = 0
    for r in train + val:
        sys_c = r["messages"][0]["content"]
        if any(snip in sys_c for _, snip in proof_snippets):
            matched += 1
    print(f"grounding 命中（system 含某題參考解片段）：{matched}/{len(train)+len(val)}")
    if matched != len(train) + len(val):
        fails.append("有記錄的 system 未含任何題目參考解片段")

    print("=" * 56)
    if fails:
        print(f"[FAIL] {len(fails)} 項：")
        for f in fails:
            print("  -", f)
        return 1
    print("所有完整性測試通過 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
