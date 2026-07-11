# -*- coding: utf-8 -*-
"""
build.py — 高等數學蘇格拉底引導資料集建置腳本

流程：
  1. 從 src/problems_*.py 收集 50 道題目 + LaTeX 參考解 → dataset/problems.json
  2. 從 src/dialogues_*.py 收集所有對話原始碼（不含 system）
  3. 為每條對話注入 grounded system（帶對應題目的 <REFERENCE_PROOF>）
  4. 依 kind 分流輸出：
       - core      → dialogues_core.jsonl
       - augmented / short → dialogues_augmented.jsonl
  5. 合併全部，固定亂數種子 shuffle，9:1 切 train.jsonl / val.jsonl

所有題目與對話內容皆由 Claude 手寫（見 memory: dataset-content-authored-by-claude），
本腳本只負責組裝，不生成任何數學內容。
"""
import importlib.util
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"

# 精簡版 grounded system（~80 token）：完整規則版約 130 token，會讓多數 grounded 樣本
# （system 已含完整 LaTeX 參考解）超過 MAX_LEN=512 而被截斷/丟棄。精簡後多能塞進 512~640。
SYSTEM_TEMPLATE = """你是蘇格拉底式高等數學引導助教。下面 <REFERENCE_PROOF> 內是參考解（學生看不到），僅供你確保提問指向正確的下一步，切勿洩漏其內容或最終結論。規則：每次只問一個聚焦問題、用精確數學術語、回覆 80 字內；學生方向正確就肯定並推進，有邏輯漏洞就用問題引導其自行發現。若學生對同一步連續兩次答不出來或方向錯誤，可點出該步該用的關鍵定理或技巧名稱（不解釋如何套用、不給算式），再問一個問題讓學生自己接著推導。學生走完所有關鍵步驟後，請他把完整證明寫出來；審閱他寫的證明時，若有缺漏就用一個問題指出、讓他自行補上。

<REFERENCE_PROOF>
{proof}
</REFERENCE_PROOF>"""


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_problems():
    problems = {}
    order = []
    for path in sorted(SRC.glob("problems_*.py")):
        mod = _load_module(path)
        for p in mod.PROBLEMS:
            if p["id"] in problems:
                raise ValueError(f"重複題目 id: {p['id']} ({path.name})")
            problems[p["id"]] = p
            order.append(p["id"])
    return problems, order


def load_dialogues():
    dialogues = []
    for path in sorted(SRC.glob("dialogues_*.py")):
        mod = _load_module(path)
        for d in mod.DIALOGUES:
            d["_src"] = path.name
            dialogues.append(d)
    return dialogues


def build_record(dialogue, problems):
    pid = dialogue["problem_id"]
    if pid not in problems:
        raise ValueError(f"對話引用不存在的題目 id: {pid} ({dialogue.get('_src')})")
    prob = problems[pid]
    messages = [{"role": "system", "content": SYSTEM_TEMPLATE.format(proof=prob["reference_proof"])}]
    turns = dialogue["turns"]
    if not turns or turns[0]["role"] != "user":
        raise ValueError(f"對話首回合須為 user: {pid} ({dialogue.get('_src')})")
    # 將題目陳述注入第一個 user 回合，避免每條對話重複抄寫 LaTeX
    first = f"題目：{prob['statement']}\n\n{turns[0]['content']}"
    messages.append({"role": "user", "content": first})
    messages.extend({"role": t["role"], "content": t["content"]} for t in turns[1:])
    return {"messages": messages}


def main():
    problems, order = load_problems()
    dialogues = load_dialogues()

    # 1. problems.json
    problems_out = [problems[pid] for pid in order]
    (HERE / "problems.json").write_text(
        json.dumps(problems_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 2. 分流
    core, aug = [], []
    for d in dialogues:
        rec = build_record(d, problems)
        (core if d["kind"] == "core" else aug).append(rec)

    def dump_jsonl(path, records):
        with open(path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump_jsonl(HERE / "dialogues_core.jsonl", core)
    dump_jsonl(HERE / "dialogues_augmented.jsonl", aug)

    # 3. 合併 + 切分
    allrec = core + aug
    rng = random.Random(20260702)
    rng.shuffle(allrec)
    n_val = max(1, round(len(allrec) * 0.1))
    val, train = allrec[:n_val], allrec[n_val:]
    dump_jsonl(HERE / "train.jsonl", train)
    dump_jsonl(HERE / "val.jsonl", val)

    print(f"題目數        : {len(problems_out)}")
    print(f"核心對話      : {len(core)}")
    print(f"擴充對話      : {len(aug)}")
    print(f"對話總數      : {len(allrec)}")
    print(f"train / val   : {len(train)} / {len(val)}")


if __name__ == "__main__":
    main()
