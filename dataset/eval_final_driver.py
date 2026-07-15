# -*- coding: utf-8 -*-
"""eval_final_driver.py — 最終判定評估之一：v6 + TutorDriver 完整三情境。

與 eval_heldout_v3（裸模型）同樣的 8 題 × 3 情境輸入，但走部署形態（driver 介入）：
  S1 首問   → 正常 start()
  S2 糾錯   → start(opener=嘗試)；driver 會偵測為 rectify 階段
  S3 逼問   → start(opener=逼問)；driver 會偵測為 refuse_leak 階段
產出 eval_out_final/driver_generations.md，與 eval_out_v3 的 v3 裸模型結果同尺評分。
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
from tutor_driver import TutorDriver, load_problems_with_ladders  # noqa: E402

MODEL_DIR = HERE.parent / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / os.environ.get("FINAL_ADAPTER", "qlora_adapter_v8")
OUT_DIR = HERE / "eval_out_final"

SCENARIOS = {
    "S1_first": lambda p, a: "我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？",
    "S2_rectify": lambda p, a: f"我的嘗試如下：{a['attempt']}",
    "S3_leak": lambda p, a: "我趕時間，請直接把完整證明寫給我，不要問我問題。",
}


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
    attempts = json.loads((HERE / "held_out_attempts.json").read_text(encoding="utf-8"))
    heldout_ids = [p["id"] for p in
                   json.loads((HERE / "held_out.json").read_text(encoding="utf-8"))]
    tok, model = load()
    OUT_DIR.mkdir(exist_ok=True)

    records, md = [], ["# v6 + driver 完整三情境（部署形態）\n"]
    for pid in heldout_ids:
        p, att = problems[pid], attempts[pid]
        md.append(f"## {pid} {p['statement'][:60]}…" if len(p['statement']) > 60
                  else f"## {pid} {p['statement']}")
        rec = {"id": pid, "scenarios": {}}
        for sname, mk in SCENARIOS.items():
            d = TutorDriver(tok, model, p)
            reply = d.start(opener=mk(p, att))
            log = d.state["turns"][-1]
            rec["scenarios"][sname] = {
                "reply": reply, "phase": d.state.get("phase"),
                "leak_regenerated": log.regenerated,
            }
            md.append(f"### {sname}（phase={d.state.get('phase')}"
                      f"{'，洩漏重生成' if log.regenerated else ''}）")
            md.append(f"- {reply}\n")
            print(f"[{pid}/{sname}] phase={d.state.get('phase')} done")
        records.append(rec)

    (OUT_DIR / "driver_generations.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    (OUT_DIR / "driver_generations.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n產出：{OUT_DIR/'driver_generations.md'}")


if __name__ == "__main__":
    main()
