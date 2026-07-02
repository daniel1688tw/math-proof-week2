# -*- coding: utf-8 -*-
"""eval_heldout.py — 在 8 道 held-out 題（不在訓練集）上比較三種路線的第一個引導問句。

路線：
  base_grounded  基底模型（停用 adapter）+ grounded system（含參考解）
  ft_grounded    微調模型（qlora_adapter_v2）+ grounded system
  ft_plain       微調模型 + 無參考解的精簡蘇格拉底 system（測「純微調」在難題的表現）

一次載入基底 4-bit + PeftModel，用 disable_adapter() 切換 base/finetuned，避免重複載入。
產出：eval_out_v2/generations.md（供 Claude 評分）與 generations.jsonl。
生成用 greedy（do_sample=False）確保可重現、對三路線公平。
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
from build import SYSTEM_TEMPLATE  # noqa: E402  複用訓練時的 grounded 模板

MODEL_DIR = HERE.parent / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / "qlora_adapter_v2"
OUT_DIR = HERE / "eval_out_v2"

# 無 grounding 的精簡蘇格拉底 system（純微調路線用）
SYSTEM_PLAIN = (
    "你是蘇格拉底式高等數學引導助教。不要直接給出完整證明或最終答案，"
    "每次只問一個聚焦的引導問題，用精確數學術語，回覆 80 字內。"
)

STUDENT_OPENER = "\n\n我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？"


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
def gen(tok, model, system, user):
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    enc = tok.apply_chat_template(
        msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True
    ).to(model.device)
    out = model.generate(
        **enc, max_new_tokens=220, do_sample=False,
        repetition_penalty=1.05, pad_token_id=tok.pad_token_id or tok.eos_token_id,
    )
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def main():
    problems = json.loads((HERE / "held_out.json").read_text(encoding="utf-8"))
    tok, model = load()
    OUT_DIR.mkdir(exist_ok=True)

    records = []
    md = ["# Held-out 生成結果（8 題 × 3 路線，供評分）\n"]
    for p in problems:
        grounded_sys = SYSTEM_TEMPLATE.format(proof=p["reference_proof"])
        user = f"題目：{p['statement']}{STUDENT_OPENER}"

        conditions = {}
        # 微調 + grounded / 微調 + plain：adapter 啟用
        conditions["ft_grounded"] = gen(tok, model, grounded_sys, user)
        conditions["ft_plain"] = gen(tok, model, SYSTEM_PLAIN, user)
        # 基底 + grounded：停用 adapter
        with model.disable_adapter():
            conditions["base_grounded"] = gen(tok, model, grounded_sys, user)

        rec = {"id": p["id"], "topic": p["topic"], "statement": p["statement"],
               "outputs": conditions}
        records.append(rec)

        md.append(f"## {p['id']}（{p['topic']}）")
        md.append(f"**題目**：{p['statement']}\n")
        for key in ("base_grounded", "ft_grounded", "ft_plain"):
            md.append(f"- **{key}**：{conditions[key]}")
        md.append("")
        print(f"[{p['id']}] done")

    (OUT_DIR / "generations.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    (OUT_DIR / "generations.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n產出：{OUT_DIR/'generations.md'}")


if __name__ == "__main__":
    main()
