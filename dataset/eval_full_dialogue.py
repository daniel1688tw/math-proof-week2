# -*- coding: utf-8 -*-
"""eval_full_dialogue.py — 對微調模型（qlora_adapter_v3）跑 3 題完整多輪引導對話。

與先前 eval_heldout*.py 不同：這裡不只看第一個問句，而是讓對話真正進行到「證明完成」。
助教（tutor）每一輪都由模型即時生成（非事先寫好）；學生（student）的回覆由 Claude
根據對應的參考解**事先寫好**（模擬一個認真、逐步跟上的學生），確保每輪學生回應在數學上
正確且對應到證明的下一個邏輯步驟，讓對話能自然走完整個五階段引導。

三題選自 held_out.json（訓練集之外的題目），涵蓋連續性/微分/級數三個主題。

執行：
  PYTHONNOUSERSITE=1 PYTHONUTF8=1 conda run -n lora_project --live-stream python eval_full_dialogue.py
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
ADAPTER_DIR = HERE / "qlora_adapter_v3"
OUT_DIR = HERE / "eval_out_v3"

OPENER = "我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？"

# 每題事先寫好的「學生」逐輪回覆（依對應參考解的邏輯步驟撰寫），
# 助教每輪的問句由模型即時生成，學生依內容自然回應。
CASES = [
    {
        "id": "H3",
        "student_turns": [
            "喔，有理數在實數中是稠密的，所以任何實數附近都有有理數。",
            "那我可以取一串有理數 q_n，讓它收斂到 a。",
            "連續的序列準則：如果 q_n→a 且 f 在 a 連續，那 f(q_n) 會收斂到 f(a)。",
            "因為每個 q_n 都是有理數，所以 f(q_n)=0 對所有 n 成立。",
            "所以 f(a)=lim f(q_n)=lim 0=0。因為 a 是任意實數，所以 f 恆等於 0。這樣就證完了嗎？",
        ],
    },
    {
        "id": "H5",
        "student_turns": [
            "f(t)=e^t 在 [0,x] 上連續、可微，滿足均值定理的條件，f'(t)=e^t。",
            "存在 c 介於 0 和 x 之間，使得 e^x − e^0 = e^c·(x−0)，也就是 e^x − 1 = e^c·x。",
            "因為 c>0，所以 e^c > e^0 = 1。",
            "所以 e^x−1 = e^c·x > 1·x = x（因為 x>0），也就是 e^x > 1+x。證完了！",
        ],
    },
    {
        "id": "H7",
        "student_turns": [
            "應該要找一個已知收斂的級數來比較，我猜是 ∑1/n²？",
            "因為 n²+1 > n²，兩邊取倒數不等號要反向，所以 0 < 1/(n²+1) < 1/n²。",
            "∑1/n² 是 p=2>1 的 p-級數，已知收斂。由比較判別法，∑1/(n²+1) 也收斂。這樣就完成了吧？",
        ],
    },
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
def tutor_reply(tok, model, messages):
    enc = tok.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
    ).to(model.device)
    out = model.generate(
        **enc, max_new_tokens=260, do_sample=False,
        repetition_penalty=1.05, pad_token_id=tok.pad_token_id or tok.eos_token_id,
    )
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def run_case(tok, model, problems, case):
    p = next(x for x in problems if x["id"] == case["id"])
    system = SYSTEM_TEMPLATE.format(proof=p["reference_proof"])
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"題目：{p['statement']}\n\n{OPENER}"},
    ]
    transcript = [{"role": "user", "content": messages[-1]["content"]}]

    reply = tutor_reply(tok, model, messages)
    messages.append({"role": "assistant", "content": reply})
    transcript.append({"role": "assistant", "content": reply})
    print(f"\n[{case['id']}] T1: {reply}")

    for s in case["student_turns"]:
        messages.append({"role": "user", "content": s})
        transcript.append({"role": "user", "content": s})
        print(f"  S: {s}")
        reply = tutor_reply(tok, model, messages)
        messages.append({"role": "assistant", "content": reply})
        transcript.append({"role": "assistant", "content": reply})
        print(f"  T: {reply}")

    return {"id": p["id"], "topic": p["topic"], "statement": p["statement"],
            "reference_proof": p["reference_proof"], "transcript": transcript}


def main():
    problems = json.loads((HERE / "held_out.json").read_text(encoding="utf-8"))
    tok, model = load()
    OUT_DIR.mkdir(exist_ok=True)

    results = [run_case(tok, model, problems, c) for c in CASES]

    md = ["# 微調模型（qlora_adapter_v3）完整引導對話測試（3 題）\n"]
    for r in results:
        md.append(f"## {r['id']}（{r['topic']}）")
        md.append(f"**題目**：{r['statement']}\n")
        md.append(f"<details><summary>參考解（學生看不到）</summary>\n\n{r['reference_proof']}\n\n</details>\n")
        for t in r["transcript"]:
            tag = "**學生**" if t["role"] == "user" else "**助教**"
            md.append(f"- {tag}：{t['content']}")
        md.append("")

    (OUT_DIR / "full_dialogues.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results), encoding="utf-8")
    (OUT_DIR / "full_dialogues.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n產出：{OUT_DIR/'full_dialogues.md'}")


if __name__ == "__main__":
    main()
