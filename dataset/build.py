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
SRC_EN = HERE / "src_en"

# 精簡版 grounded system（~80 token）：完整規則版約 130 token，會讓多數 grounded 樣本
# （system 已含完整 LaTeX 參考解）超過 MAX_LEN=512 而被截斷/丟棄。精簡後多能塞進 512~640。
SYSTEM_TEMPLATE = """你是蘇格拉底式高等數學引導助教。下面 <REFERENCE_PROOF> 內是參考解（學生看不到），僅供你確保提問指向正確的下一步，切勿洩漏其內容或最終結論。規則：每次只問一個聚焦問題、用精確數學術語、回覆 80 字內；學生方向正確就肯定並推進，有邏輯漏洞就用問題引導其自行發現。若學生對同一步連續兩次答不出來或方向錯誤，可點出該步該用的關鍵定理或技巧名稱（不解釋如何套用、不給算式），再問一個問題讓學生自己接著推導。學生走完所有關鍵步驟後，請他把完整證明寫出來；審閱他寫的證明時，若有缺漏就用一個問題指出、讓他自行補上。

<REFERENCE_PROOF>
{proof}
</REFERENCE_PROOF>"""

# 英文版 grounded system（與中文版語義等價；與 tutor_driver.BASE_SYSTEM_EN 同源）。
SYSTEM_TEMPLATE_EN = """You are a Socratic tutor for advanced mathematics proofs. The <REFERENCE_PROOF> below is a reference solution (invisible to the student); use it only to ensure your questions point toward the correct next step, and never leak its content or final conclusion. Rules: ask only one focused question per turn, use precise mathematical terminology, keep replies within about 60 words; if the student is on the right track, affirm and push forward; if there is a logical gap, guide them to discover it themselves through a question. If the student fails the same step or goes the wrong direction twice in a row, you may name the key theorem or technique that step needs (without explaining how to apply it and without formulas), then ask one question for the student to continue the derivation. Once the student has walked through all key steps, ask them to write out the complete proof; when reviewing their written proof, point out any gap with a single question and let them fix it themselves.

<REFERENCE_PROOF>
{proof}
</REFERENCE_PROOF>"""

# 語言設定：目錄、system 模板、題目前綴、problems.json 輸出檔名
LANGS = [
    {"src": SRC, "template": SYSTEM_TEMPLATE, "prefix": "題目：", "problems_out": "problems.json"},
    {"src": SRC_EN, "template": SYSTEM_TEMPLATE_EN, "prefix": "Problem: ", "problems_out": "problems_en.json"},
]


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_problems(src: Path):
    problems = {}
    order = []
    for path in sorted(src.glob("problems_*.py")):
        mod = _load_module(path)
        for p in mod.PROBLEMS:
            if p["id"] in problems:
                raise ValueError(f"重複題目 id: {p['id']} ({path.name})")
            problems[p["id"]] = p
            order.append(p["id"])
    return problems, order


def load_dialogues(src: Path):
    dialogues = []
    for path in sorted(src.glob("dialogues_*.py")):
        mod = _load_module(path)
        for d in mod.DIALOGUES:
            d["_src"] = path.name
            dialogues.append(d)
    return dialogues


def build_record(dialogue, problems, template, prefix):
    pid = dialogue["problem_id"]
    if pid not in problems:
        raise ValueError(f"對話引用不存在的題目 id: {pid} ({dialogue.get('_src')})")
    prob = problems[pid]
    messages = [{"role": "system", "content": template.format(proof=prob["reference_proof"])}]
    turns = dialogue["turns"]
    if not turns or turns[0]["role"] != "user":
        raise ValueError(f"對話首回合須為 user: {pid} ({dialogue.get('_src')})")
    # 將題目陳述注入第一個 user 回合，避免每條對話重複抄寫 LaTeX
    first = f"{prefix}{prob['statement']}\n\n{turns[0]['content']}"
    messages.append({"role": "user", "content": first})
    messages.extend({"role": t["role"], "content": t["content"]} for t in turns[1:])
    return {"messages": messages}


def main():
    core, aug = [], []
    lang_stats = []
    for lang in LANGS:
        problems, order = load_problems(lang["src"])
        dialogues = load_dialogues(lang["src"])

        # problems.json / problems_en.json（供 driver 與評估使用）
        problems_out = [problems[pid] for pid in order]
        (HERE / lang["problems_out"]).write_text(
            json.dumps(problems_out, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        n_core = n_aug = 0
        for d in dialogues:
            rec = build_record(d, problems, lang["template"], lang["prefix"])
            if d["kind"] == "core":
                core.append(rec); n_core += 1
            else:
                aug.append(rec); n_aug += 1
        lang_stats.append((lang["src"].name, len(problems_out), n_core, n_aug))

    def dump_jsonl(path, records):
        with open(path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump_jsonl(HERE / "dialogues_core.jsonl", core)
    dump_jsonl(HERE / "dialogues_augmented.jsonl", aug)

    # 合併雙語 + 固定種子 shuffle + 9:1 切分
    allrec = core + aug
    rng = random.Random(20260702)
    rng.shuffle(allrec)
    n_val = max(1, round(len(allrec) * 0.1))
    val, train = allrec[:n_val], allrec[n_val:]
    dump_jsonl(HERE / "train.jsonl", train)
    dump_jsonl(HERE / "val.jsonl", val)

    for name, n_prob, n_core, n_aug in lang_stats:
        print(f"[{name:8}] 題目 {n_prob}，核心 {n_core}，擴充 {n_aug}")
    print(f"核心對話      : {len(core)}")
    print(f"擴充對話      : {len(aug)}")
    print(f"對話總數      : {len(allrec)}")
    print(f"train / val   : {len(train)} / {len(val)}")


if __name__ == "__main__":
    main()
