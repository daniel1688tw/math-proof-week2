# -*- coding: utf-8 -*-
"""eval_hard.py — 數學系等級難題測試：一致收斂、二階導數鏈式單調性、一致連續乘積、
Darboux 定理、Chebyshev 積分不等式。這些技巧**都不在 50 道訓練題的範圍**，用來測試
微調模型（預設 qlora_adapter_v9，可用 HARD_ADAPTER 覆寫）是否能把訓練學到的「引導行為」類推到陌生的證明技巧上，
而非僅是記住訓練題的具體套路。

跑兩件事：
  1. 5 題 S1 首問比較：base_grounded vs ft_grounded
  2. M4（Darboux 定理，最刁鑽）：ft_grounded 完整多輪引導對話（學生回覆依參考解手寫）
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
ADAPTER_DIR = HERE / os.environ.get("HARD_ADAPTER", "qlora_adapter_v9")
OUT_DIR = HERE / "eval_out_hard"

OPENER = "我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？"

M4_STUDENT_TURNS = [
    "可以定義 g(x)=f(x)-kx，這樣 g'(x)=f'(x)-k。",
    "g'(a)=f'(a)-k<0，g'(b)=f'(b)-k>0。",
    "g 可微所以連續，在 [a,b] 由最大值定理會有最小值。",
    "因為 g'(a)<0，g 在 a 附近是遞減的，所以 a 右邊有點的值比 g(a) 小，a 不會是最小值點。",
    "同理 g'(b)>0，b 左邊有點的值比 g(b) 小，所以最小值點也不在 b。",
    "所以最小值點 c 在開區間 (a,b) 內，由費馬定理 g'(c)=0，也就是 f'(c)=k。這樣就證完了！",
]


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
def gen(tok, model, messages, max_new=260):
    enc = tok.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
    ).to(model.device)
    out = model.generate(
        **enc, max_new_tokens=max_new, do_sample=False,
        repetition_penalty=1.05, pad_token_id=tok.pad_token_id or tok.eos_token_id,
    )
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def run_s1(tok, model, problems):
    records = []
    md = ["# 數學系難題 S1 首問比較（base_grounded vs ft_grounded）\n"]
    for p in problems:
        grounded_sys = SYSTEM_TEMPLATE.format(proof=p["reference_proof"])
        user = f"題目：{p['statement']}\n\n{OPENER}"
        msgs = [{"role": "system", "content": grounded_sys}, {"role": "user", "content": user}]
        out_ft = gen(tok, model, msgs)
        with model.disable_adapter():
            out_base = gen(tok, model, msgs)
        records.append({"id": p["id"], "topic": p["topic"], "statement": p["statement"],
                         "base_grounded": out_base, "ft_grounded": out_ft})
        md.append(f"## {p['id']}（{p['topic']}）")
        md.append(f"**題目**：{p['statement']}\n")
        md.append(f"- **base_grounded**：{out_base}")
        md.append(f"- **ft_grounded**：{out_ft}\n")
        print(f"[S1/{p['id']}] done")
    return records, md


def run_m4_dialogue(tok, model, problems):
    p = next(x for x in problems if x["id"] == "M4")
    system = SYSTEM_TEMPLATE.format(proof=p["reference_proof"])
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": f"題目：{p['statement']}\n\n{OPENER}"}]
    transcript = [{"role": "user", "content": messages[-1]["content"]}]
    reply = gen(tok, model, messages)
    messages.append({"role": "assistant", "content": reply})
    transcript.append({"role": "assistant", "content": reply})
    print(f"\n[M4] T1: {reply}")
    for s in M4_STUDENT_TURNS:
        messages.append({"role": "user", "content": s})
        transcript.append({"role": "user", "content": s})
        print(f"  S: {s}")
        reply = gen(tok, model, messages)
        messages.append({"role": "assistant", "content": reply})
        transcript.append({"role": "assistant", "content": reply})
        print(f"  T: {reply}")
    return transcript


def main():
    problems = json.loads((HERE / "hard_math_major.json").read_text(encoding="utf-8"))
    tok, model = load()
    OUT_DIR.mkdir(exist_ok=True)

    s1_records, md = run_s1(tok, model, problems)
    m4_transcript = run_m4_dialogue(tok, model, problems)

    md.append("# M4（Darboux 定理）完整多輪對話（ft_grounded）\n")
    p4 = next(x for x in problems if x["id"] == "M4")
    md.append(f"**題目**：{p4['statement']}\n")
    for t in m4_transcript:
        tag = "**學生**" if t["role"] == "user" else "**助教**"
        md.append(f"- {tag}：{t['content']}")

    (OUT_DIR / "s1_comparison.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in s1_records), encoding="utf-8")
    (OUT_DIR / "m4_dialogue.jsonl").write_text(
        json.dumps({"id": "M4", "transcript": m4_transcript}, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "results.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n產出：{OUT_DIR/'results.md'}")


if __name__ == "__main__":
    main()
