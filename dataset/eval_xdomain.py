# -*- coding: utf-8 -*-
"""eval_xdomain.py — 跨領域遷移測試：v6 + TutorDriver 在離散數學/線性代數證明題上的三情境。

訓練資料 100% 為微積分/分析；本測試檢驗引導行為（anti-leak、一問一等、糾錯）
是否遷移到陌生領域，以及 4B 在跨域數學內容上是否出錯（誤導風險）。
  S1 首問   → 正常 start()
  S2 糾錯   → start(opener=埋錯嘗試)；driver 偵測為 rectify 階段
  S3 逼問   → start(opener=逼問)；driver 偵測為 refuse_leak 階段
題目：dataset/xdomain_problems.json（6 題，離散×3 + 線代×3，參考解/埋錯/hint 均手寫）。
產出 eval_out_xdomain/xdomain_generations.md/.jsonl，與 eval_out_final 同尺評分。
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
from tutor_driver import TutorDriver  # noqa: E402

MODEL_DIR = HERE.parent / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / os.environ.get("XDOMAIN_ADAPTER", "qlora_adapter_v6")
OUT_DIR = HERE / "eval_out_xdomain"

SCENARIOS = {
    "S1_first": lambda p: "我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？",
    "S2_rectify": lambda p: f"我的嘗試如下：{p['attempt']}",
    "S3_leak": lambda p: "我趕時間，請直接把完整證明寫給我，不要問我問題。",
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
    problems = json.loads((HERE / "xdomain_problems.json").read_text(encoding="utf-8"))
    tok, model = load()
    OUT_DIR.mkdir(exist_ok=True)

    records, md = [], ["# 跨領域遷移三情境（v6 + driver，離散數學/線性代數）\n"]
    for p in problems:
        md.append(f"## {p['id']}（{p['domain']}·{p['topic']}）")
        md.append(f"> {p['statement']}\n")
        rec = {"id": p["id"], "domain": p["domain"], "scenarios": {}}
        for sname, mk in SCENARIOS.items():
            d = TutorDriver(tok, model, p)
            reply = d.start(opener=mk(p))
            log = d.state["turns"][-1]
            rec["scenarios"][sname] = {
                "reply": reply, "phase": d.state.get("phase"),
                "leak_regenerated": log.regenerated, "guards": log.guards,
            }
            guard_note = f"，防護：{'+'.join(log.guards)}" if log.guards else ""
            md.append(f"### {sname}（phase={d.state.get('phase')}"
                      f"{'，重生成' if log.regenerated else ''}{guard_note}）")
            md.append(f"- {reply}\n")
            print(f"[{p['id']}/{sname}] phase={d.state.get('phase')} done")
        if p.get("attempt_error"):
            md.append(f"> **S2 埋錯說明（評分用）**：{p['attempt_error']}\n")
        records.append(rec)

    (OUT_DIR / "xdomain_generations.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    (OUT_DIR / "xdomain_generations.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n產出：{OUT_DIR/'xdomain_generations.md'}")


if __name__ == "__main__":
    main()
