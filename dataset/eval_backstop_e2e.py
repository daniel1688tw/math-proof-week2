# -*- coding: utf-8 -*-
"""eval_backstop_e2e.py — 審閱後盾端對端驗證（需 GPU + Ollama）。

完整部署鏈路：學生草稿 → driver 偵測 review/rectify → 後盾（思考型）找碴
→ 缺漏清單注入 system → 微調模型包裝成引導問題。
用三個「微調模型單獨審閱曾失手」的案例，對照有/無後盾的回覆。
產出 eval_out_xdomain/backstop_e2e.md。
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
ADAPTER_DIR = HERE / os.environ.get("FINAL_ADAPTER", "qlora_adapter_v6")
OUT = HERE / "eval_out_xdomain" / "backstop_e2e.md"

xd = {p["id"]: p for p in json.loads((HERE / "xdomain_problems.json").read_text(encoding="utf-8"))}
ho = {p["id"]: p for p in json.loads((HERE / "held_out.json").read_text(encoding="utf-8"))}
att = json.loads((HERE / "held_out_attempts.json").read_text(encoding="utf-8"))

CASES = [
    ("X2 審閱：草稿缺鴿籠前提（先前失手：解釋成『它就是要證的命題』）",
     xd["X2"],
     "證明：任取 n+1 個整數。由鴿籠原理，必存在兩個數 a、b（a≠b）除以 n 的餘數相同。"
     "設 a = qn + r、b = pn + r，則 a − b = (q − p)n，故 n 整除 a − b。證畢。請幫我審閱。"),
    ("X4 審閱：草稿缺 v2≠0（先前失手：只問泛泛概念題）",
     xd["X4"],
     "證明：設 c1v1 + c2v2 = 0（式 1）。左乘 A 得 c1λ1v1 + c2λ2v2 = 0（式 2）。"
     "式 2 減 λ1 倍式 1 得 c2(λ2−λ1)v2 = 0。因為 λ2 ≠ λ1，所以 c2 = 0。"
     "代回式 1 得 c1v1 = 0，因為 v1 ≠ 0，所以 c1 = 0。故 {v1, v2} 線性獨立。請幫我審閱。"),
    ("H3 糾錯：雙重錯誤嘗試（先前失手：背書了錯的平均式）",
     ho["H3"],
     f"我的嘗試如下：{att['H3']['attempt']}"),
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


def main():
    tok, model = load()
    md = ["# 審閱後盾端對端驗證（有/無後盾對照）\n"]
    for name, prob, opener in CASES:
        md.append(f"## {name}")
        for use_backstop, tag in ((False, "無後盾（原行為）"), (True, "有後盾")):
            d = TutorDriver(tok, model, prob, backstop=use_backstop)
            reply = d.start(opener=opener)
            gaps = d.state.get("backstop_gaps")
            md.append(f"### {tag}（phase={d.state.get('phase')}"
                      f"{'，後盾缺漏 ' + str(len(gaps)) + ' 項' if gaps else ''}）")
            if use_backstop and gaps:
                for g in gaps:
                    md.append(f"> 後盾：{g}")
            elif use_backstop and gaps is None:
                md.append("> 後盾降級（Ollama 失敗）")
            md.append(f"- {reply}\n")
            print(f"[{prob['id']}/{tag}] done")
    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"\n產出：{OUT}")


if __name__ == "__main__":
    main()
