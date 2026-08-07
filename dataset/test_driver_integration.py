# -*- coding: utf-8 -*-
"""test_driver_integration.py — driver + v5 adapter 的整合測試（需 GPU）。

情境：
  1. A6/C8/E4 卡住兩次腳本（與 eval_hint_escalation 相同輸入，可與「無 driver」直接對比）
     斷言：T1/T2（等級 0/1）不點名定理；T3（等級 2）含 ladder 想法且不含長算式；全程單問句。
  2. E4 正常學生腳本：全程等級 0，行為不受 driver 干擾。
產出 eval_out_driver/driver_test.md 供人工檢視 + 自動斷言結果。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("PYTHONNOUSERSITE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("BITSANDBYTES_NOWELCOME", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tutor_driver import TutorDriver, load_problems_with_ladders, _QMARK_RE  # noqa: E402

MODEL_DIR = HERE.parent / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / os.environ.get("DRIVER_ADAPTER", "qlora_adapter_v9")
OUT_DIR = HERE / "eval_out_driver"

STUCK_SCRIPT = ["我不知道，想不出來。", "還是想不到，可以再提示一下嗎？"]
NORMAL_SCRIPT_E4 = [
    "部分和是遞增的，因為每一項都是正數。",
    "還需要證明有上界，才能用單調有界定理。",
    "用裂項：1/k² ≤ 1/(k(k-1)) = 1/(k-1) − 1/k，求和後 S_n ≤ 1+(1−1/n) < 2。",
]

# 等級 0/1 不得出現的定理名稱（點名 = 提早透漏）
THEOREM_NAMES = ["夾擠", "二項式定理", "均值定理", "單調有界", "裂項", "Bolzano", "介值定理"]
# 等級 2 應傳達的想法（每題的可接受關鍵詞：定理名或等價的符號/描述）
LEVEL2_EXPECT = {
    "A6": ["二項式", "binom", "展開"],
    "C8": ["均值定理"],
    "E4": ["單調有界"],
}
# 完成式算式：帶等號/不等號接分式或數值（單提 \binom{n}{2} 是「指出對象」，不算完成計算）
FORMULA_RE = re.compile(r"=\s*\\?d?frac|=\s*\d|\\[lg]e\s*\\?d?frac")


def load():
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), quantization_config=bnb, device_map={"": 0}, dtype=torch.bfloat16,
    )
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, str(ADAPTER_DIR))
    model.eval()
    return tok, model


def main():
    problems = load_problems_with_ladders()
    tok, model = load()
    OUT_DIR.mkdir(exist_ok=True)
    md, checks = ["# Driver 整合測試（v5 adapter）\n"], []

    def check(name, cond):
        checks.append((name, bool(cond)))
        print(("  ✓ " if cond else "  ✗ ") + name)

    # ---- 情境 1：卡住兩次（A6/C8/E4）----
    for pid in ("A6", "C8", "E4"):
        d = TutorDriver(tok, model, problems[pid])
        replies = [d.start()]
        for s in STUCK_SCRIPT:
            replies.append(d.step(s))
        md.append(f"## {pid}（卡住兩次腳本）")
        md.append(f"**題目**：{problems[pid]['statement']}\n")
        for i, r in enumerate(replies):
            lvl = d.state["turns"][i].level
            md.append(f"- **T{i+1}（等級{lvl}）**：{r}")
        md.append("")
        print(f"\n[{pid}]")
        for i, r in enumerate(replies):
            print(f"  T{i+1}(L{d.state['turns'][i].level}): {r[:80]}")

        levels = [t.level for t in d.state["turns"]]
        check(f"{pid} 等級序列 [0,1,2]", levels == [0, 1, 2])
        early = replies[0] + replies[1]
        check(f"{pid} 等級0/1 不點名定理", not any(n in early for n in THEOREM_NAMES))
        check(f"{pid} 等級2 有透漏想法（含該題可接受關鍵詞）",
              any(k in replies[2] for k in LEVEL2_EXPECT[pid]))
        check(f"{pid} 等級2 不含完成式算式", not FORMULA_RE.search(replies[2]))
        check(f"{pid} 全程單問句", all(len(_QMARK_RE.findall(r)) <= 1 for r in replies))
        check(f"{pid} 無未解決洩漏", not any(t.leak_flag and not t.regenerated
                                            for t in d.state["turns"]))

    # ---- 情境 2：正常學生（E4）----
    d = TutorDriver(tok, model, problems["E4"])
    replies = [d.start()]
    for s in NORMAL_SCRIPT_E4:
        replies.append(d.step(s))
    md.append("## E4（正常學生腳本）")
    for i, r in enumerate(replies):
        lvl = d.state["turns"][i].level
        md.append(f"- **T{i+1}（等級{lvl}）**：{r}")
    print("\n[E4 正常學生]")
    for i, r in enumerate(replies):
        print(f"  T{i+1}(L{d.state['turns'][i].level}): {r[:80]}")
    check("正常學生全程等級 0", all(t.level == 0 for t in d.state["turns"]))
    check("正常學生全程單問句", all(len(_QMARK_RE.findall(r)) <= 1 for r in replies))

    # ---- 總結 ----
    n_pass = sum(1 for _, ok in checks if ok)
    md.append(f"\n## 自動斷言：{n_pass}/{len(checks)} 通過\n")
    for name, ok in checks:
        md.append(f"- {'✓' if ok else '✗'} {name}")
    (OUT_DIR / "driver_test.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n斷言 {n_pass}/{len(checks)} 通過 → {OUT_DIR/'driver_test.md'}")
    sys.exit(0 if n_pass == len(checks) else 1)


if __name__ == "__main__":
    main()
