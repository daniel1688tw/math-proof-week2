# -*- coding: utf-8 -*-
"""eval_hint_escalation.py — 測試「學生連續卡住兩次才透漏定理名稱」規則是否生效。

3 題（皆不在 dialogues_hint.py 訓練過的題目）：學生連續兩輪回覆「不知道/想不出來」，
觀察助教是否 (a) 前兩次仍只用問題引導、不提前給名稱，(b) 第二次卡住後才點出關鍵定理/技巧
名稱、且不解釋如何套用、不給算式。
"""
from __future__ import annotations

import json
import os
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
from build import SYSTEM_TEMPLATE  # noqa: E402

MODEL_DIR = HERE.parent / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / os.environ.get("HINT_ADAPTER", "qlora_adapter_v5")
OUT_DIR = HERE / os.environ.get("HINT_OUT", "eval_out_v5")

OPENER = "我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？"
STUCK_1 = "我不知道，想不出來。"
STUCK_2 = "還是想不到，可以再提示一下嗎？"

# 3 題不在 dialogues_hint.py 訓練過（訓練用了 A4/A1/B2/B7/C2/C3/D3/D7/E9/E2）
CASES = ["A6", "C8", "E4"]


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


@torch.no_grad()
def gen(tok, model, messages):
    enc = tok.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
    ).to(model.device)
    out = model.generate(
        **enc, max_new_tokens=220, do_sample=False,
        repetition_penalty=1.05, pad_token_id=tok.pad_token_id or tok.eos_token_id,
    )
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def load_problem(pid):
    for fname in ("problems.json",):
        data = json.loads((HERE / fname).read_text(encoding="utf-8"))
        for p in data:
            if p["id"] == pid:
                return p
    raise KeyError(pid)


def run_case(tok, model, pid):
    p = load_problem(pid)
    system = SYSTEM_TEMPLATE.format(proof=p["reference_proof"])
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": f"題目：{p['statement']}\n\n{OPENER}"}]
    transcript = [{"role": "user", "content": messages[-1]["content"]}]
    for i, next_user in enumerate([None, STUCK_1, STUCK_2]):
        if next_user is not None:
            messages.append({"role": "user", "content": next_user})
            transcript.append({"role": "user", "content": next_user})
            print(f"  S: {next_user}")
        reply = gen(tok, model, messages)
        messages.append({"role": "assistant", "content": reply})
        transcript.append({"role": "assistant", "content": reply})
        print(f"  T{i+1}: {reply}")
    return {"id": pid, "statement": p["statement"], "transcript": transcript}


def main():
    tok, model = load()
    OUT_DIR.mkdir(exist_ok=True)
    results = [run_case(tok, model, pid) for pid in CASES]

    md = ["# 分級提示規則測試：學生連續卡住兩次\n"]
    for r in results:
        md.append(f"## {r['id']}")
        md.append(f"**題目**：{r['statement']}\n")
        for t in r["transcript"]:
            tag = "**學生**" if t["role"] == "user" else "**助教**"
            md.append(f"- {tag}：{t['content']}")
        md.append("")

    (OUT_DIR / "hint_escalation.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results), encoding="utf-8")
    (OUT_DIR / "hint_escalation.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n產出：{OUT_DIR/'hint_escalation.md'}")


if __name__ == "__main__":
    main()
