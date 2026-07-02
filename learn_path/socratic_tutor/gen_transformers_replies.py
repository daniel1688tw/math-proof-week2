"""gen_transformers_replies.py — 統一產生 transformers 四個 backend 的第一輪引導回覆。

backend：
  base               基底 Instruct + 完整 SYSTEM_SOCRATIC（基底的最佳 prompt）
  finetuned          基底 + LoRA + 精簡 SYSTEM_SOCRATIC_COMPACT（與訓練一致）
  base_grounded      基底 + 完整 grounded prompt（apples-to-apples 對照組）
  finetuned_grounded 基底 + LoRA + 精簡 grounded prompt（與訓練一致）

設計重點（回應「微調在 grounding 下到底有沒有加分」）：
  * base_grounded vs finetuned_grounded = 同基底、同 grounding，只差「有沒有微調」→ 隔離微調效果。
  * 微調相關 backend 用精簡 prompt（與訓練分佈一致，修掉先前 off-distribution 的崩潰）。
  * grounded backend 從快取讀參考解（eval_common，honors EVAL_SET）→ 純 transformers、不碰 Ollama。

用法（先確保對應題集的 reference_solutions.json 已存在）：
  EVAL_SET=v4 python gen_transformers_replies.py base finetuned base_grounded finetuned_grounded
  python gen_transformers_replies.py base finetuned base_grounded finetuned_grounded   # held-out
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

import pyarrow, datasets  # noqa: F401
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

from common import (
    ADAPTER_DIR, MODEL_NAME, SYSTEM_SOCRATIC, SYSTEM_SOCRATIC_COMPACT,
    build_grounded_system, build_grounded_system_compact,
)
from eval_common import load_reference_solutions, save_replies, score_form
from problems import all_eval_problems

ALL = ["base", "finetuned", "base_grounded", "finetuned_grounded"]


def _system_for(backend: str, ref: str) -> str:
    if backend == "base":
        return SYSTEM_SOCRATIC
    if backend == "finetuned":
        return SYSTEM_SOCRATIC_COMPACT
    if backend == "base_grounded":
        return build_grounded_system(ref)
    if backend == "finetuned_grounded":
        return build_grounded_system_compact(ref)
    raise ValueError(backend)


def load(adapter: bool):
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, quantization_config=bnb, device_map={"": 0}, torch_dtype=torch.bfloat16)
    if adapter:
        model = PeftModel.from_pretrained(model, ADAPTER_DIR)
    model.eval()
    return tok, model


@torch.no_grad()
def gen(tok, model, system: str, problem: str) -> tuple[str, float]:
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": problem}]
    enc = tok.apply_chat_template(messages, add_generation_prompt=True,
                                  return_tensors="pt", return_dict=True).to(model.device)
    t0 = time.time()
    out = model.generate(**enc, max_new_tokens=400, do_sample=True, temperature=0.7,
                         top_p=0.9, repetition_penalty=1.05,
                         pad_token_id=tok.pad_token_id or tok.eos_token_id)
    text = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return text, time.time() - t0


def run_backend(backend: str, refs: dict) -> None:
    grounded = "grounded" in backend
    adapter = "finetuned" in backend
    if grounded and not refs:
        print(f"[{backend}] 無參考解，略過"); return
    tok, model = load(adapter)
    print("\n" + "=" * 72 + f"\n  {backend}\n" + "=" * 72)
    results = []
    for p in all_eval_problems():
        ref = refs.get(p["id"], {}).get("proof", "") if grounded else ""
        if grounded and not ref:
            continue
        a, t = gen(tok, model, _system_for(backend, ref), p["problem"])
        sc = score_form(a)
        results.append({"id": p["id"], "split": p["split"], "problem": p["problem"],
                        "reply": a, "elapsed": t, "form": sc})
        print(f"  [{p['split']}] {p['id']:<34} form {sc['total']}/5  {a[:90].replace(chr(10),' ')}…")
    save_replies(backend, results)
    print(f"  → {len(results)} 題已存")
    del model
    torch.cuda.empty_cache()


def main() -> None:
    backends = sys.argv[1:] or ALL
    refs = load_reference_solutions()
    print(f"[transformers replies] EVAL_SET={os.environ.get('EVAL_SET','(held)')}  backends={backends}")
    for b in backends:
        run_backend(b, refs)
    print("\n[完成] 接著用 score_replies.py 或人工評分。")


if __name__ == "__main__":
    main()
