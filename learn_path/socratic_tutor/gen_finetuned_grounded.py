"""gen_finetuned_grounded.py — 第五個 backend：微調模型 + grounded（參考解在手）。

回答「grounded + 微調模型，是否比只有 grounded（思考型）更好」：
  * 載入 base(4-bit) + 微調 LoRA adapter（transformers）。
  * system prompt 用 build_grounded_system(參考解)，把快取的完整證明（學生看不到）放進去。
  * user 用「純題目」（WRAP=0，與 replies_finetuned.json 一致）→ 與「未 grounded 的微調」
    唯一差別就是「有沒有餵參考解」，乾淨地隔離出 grounding 的效果。

參考解讀自 eval_out/reference_solutions.json（已由 gen_reference_solutions.py 產出），
故本步純 transformers、不呼叫 Ollama、無 GPU 競爭。

輸出：eval_out/replies_finetuned_grounded.json

執行：
  conda run -n lora_project --live-stream python gen_finetuned_grounded.py
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("PYTHONNOUSERSITE", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pyarrow, datasets  # noqa: F401  (Windows: 先預載 Arrow DLL)
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

from common import ADAPTER_DIR, MODEL_NAME, build_grounded_system
from eval_common import load_reference_solutions, save_replies, score_form
from problems import all_eval_problems

WRAP = os.environ.get("WRAP", "0") == "1"
NO_ATTEMPT = "\n\nI have not started yet and I am not sure where to begin."


def load_finetuned():
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, quantization_config=bnb, device_map={"": 0},
        torch_dtype=torch.bfloat16,
    )
    model = PeftModel.from_pretrained(model, ADAPTER_DIR)
    model.eval()
    return tok, model


@torch.no_grad()
def gen(tok, model, system: str, problem: str) -> tuple[str, float]:
    user = problem + NO_ATTEMPT if WRAP else problem
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    enc = tok.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True,
    ).to(model.device)
    t0 = time.time()
    out = model.generate(
        **enc, max_new_tokens=400, do_sample=True, temperature=0.7, top_p=0.9,
        repetition_penalty=1.05, pad_token_id=tok.pad_token_id or tok.eos_token_id,
    )
    text = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return text, time.time() - t0


def main() -> None:
    refs = load_reference_solutions()
    if not refs:
        print("[錯誤] 找不到 reference_solutions.json，請先跑 gen_reference_solutions.py。")
        sys.exit(1)

    tok, model = load_finetuned()
    print("\n" + "=" * 72)
    print("  微調模型 + grounded（參考解在手）")
    print("=" * 72)
    results = []
    for p in all_eval_problems():
        ref = refs.get(p["id"], {}).get("proof", "")
        if not ref:
            print(f"  {p['id']} 無參考解，略過"); continue
        system = build_grounded_system(ref)
        a, t = gen(tok, model, system, p["problem"])
        sc = score_form(a)
        results.append({"id": p["id"], "split": p["split"], "problem": p["problem"],
                        "reply": a, "elapsed": t, "form": sc})
        tag = "H" if p["split"] == "held" else "s"
        flag = "✓" if sc["total"] >= 4 else ("△" if sc["total"] == 3 else "✗")
        print(f"\n{flag}[{tag}] [{p['id']}]  form:{sc['total']}/5  字:{sc['word_count']}  {t:.0f}s")
        print(f"  {a[:200].replace(chr(10),' ')}{'…' if len(a)>200 else ''}")

    save_replies("finetuned_grounded", results)
    print(f"\n[完成] {len(results)} 題 → eval_out/replies_finetuned_grounded.json")


if __name__ == "__main__":
    main()
