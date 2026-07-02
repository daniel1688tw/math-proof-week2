"""compare.py — 產生 base / finetuned 兩個 transformers backend 的「第一輪引導回覆」。

improve.md 問題①修正：
  * 測試題改用 problems.HELDOUT_PROBLEMS（**不在訓練集**）當主測試集，量泛化。
  * 種子題（split="seed"）仍會跑，但**分開報告**，只當「記憶 sanity check」。
本腳本只做 transformers 推理 + 形式評分（零 Ollama，避免搶顯存）；
教學品質（LLM judge）與四方對比交給 score_replies.py（讀本腳本輸出的 JSON）。

輸出：eval_out/replies_base.json、eval_out/replies_finetuned.json

執行：
  conda run -n lora_project --live-stream python compare.py
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

from common import ADAPTER_DIR, MODEL_NAME, SYSTEM_SOCRATIC
from eval_common import save_replies, score_form
from problems import all_eval_problems

# 是否補綴「尚未嘗試」前綴。種子現在有「帶/不帶前綴」兩版訓練，故預設用「純題目」評估
# （更貼近真實使用：學生直接貼題目）。設 WRAP=1 可改回補綴前綴。
WRAP = os.environ.get("WRAP", "0") == "1"
NO_ATTEMPT = "\n\nI have not started yet and I am not sure where to begin."


def load_base():
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
    model.eval()
    return tok, model


@torch.no_grad()
def gen(tok, model, problem: str) -> tuple[str, float]:
    user_content = problem + NO_ATTEMPT if WRAP else problem
    messages = [
        {"role": "system", "content": SYSTEM_SOCRATIC},
        {"role": "user", "content": user_content},
    ]
    enc = tok.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True,
    ).to(model.device)
    t0 = time.time()
    out = model.generate(
        **enc, max_new_tokens=400, do_sample=True, temperature=0.7, top_p=0.9,
        repetition_penalty=1.05, pad_token_id=tok.pad_token_id or tok.eos_token_id,
    )
    elapsed = time.time() - t0
    text = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return text, elapsed


def run_backend(tok, model, label: str) -> list[dict]:
    print("\n" + "=" * 72)
    print(f"  {label}")
    print("=" * 72)
    results: list[dict] = []
    for p in all_eval_problems():
        a, t = gen(tok, model, p["problem"])
        sc = score_form(a)
        results.append({"id": p["id"], "split": p["split"], "problem": p["problem"],
                        "reply": a, "elapsed": t, "form": sc})
        flag = "✓" if sc["total"] >= 4 else ("△" if sc["total"] == 3 else "✗")
        tag = "H" if p["split"] == "held" else "s"
        print(f"\n{flag}[{tag}] [{p['id']}]  form:{sc['total']}/5  字:{sc['word_count']}  ?:{sc['question_count']}  {t:.0f}s")
        print(f"  {a[:200].replace(chr(10),' ')}{'…' if len(a)>200 else ''}")
    return results


def _avg(results: list[dict], split: str) -> float:
    rows = [r for r in results if r["split"] == split]
    return sum(r["form"]["total"] for r in rows) / max(1, len(rows))


def main() -> None:
    tok, model = load_base()
    base_results = run_backend(tok, model, "基底 Qwen3-4B-Instruct（無 adapter）")
    save_replies("base", base_results)

    if not os.path.isdir(ADAPTER_DIR):
        print(f"\n[警告] 找不到 adapter（{ADAPTER_DIR}），只產出 base。")
        return

    print("\n  載入 LoRA adapter…")
    model = PeftModel.from_pretrained(model, ADAPTER_DIR)
    model.eval()
    ft_results = run_backend(tok, model, "微調後（基底 + 蘇格拉底 QLoRA adapter）")
    save_replies("finetuned", ft_results)

    # ── 形式分摘要：held-out（泛化）與 seed（記憶）分開報告 ──────────────────────
    print("\n" + "=" * 72)
    print("  形式分摘要（只量形式，不代表教學品質；品質請跑 score_replies.py）")
    print("=" * 72)
    for split, name in (("held", "held-out（泛化，主指標）"), ("seed", "seed（記憶 sanity）")):
        b, f = _avg(base_results, split), _avg(ft_results, split)
        d = f - b
        sign = "+" if d > 0 else ""
        print(f"  {name:<26} 基底 {b:.2f}  微調 {f:.2f}  Δ {sign}{d:.2f}")

    print("\n  ⚠️ 形式分高 ≠ 會教。請接著跑：")
    print("     python gen_ollama_replies.py   # 產 A-socratic / grounded 回覆")
    print("     python gen_reference_solutions.py  # 產參考解（judge 需要）")
    print("     python score_replies.py        # form + LLM judge 四方對比\n")


if __name__ == "__main__":
    main()
