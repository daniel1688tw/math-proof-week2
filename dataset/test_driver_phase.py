# -*- coding: utf-8 -*-
"""test_driver_phase.py — driver 主動交稿／審閱工作流整合測試（v6 adapter）。

對照 eval_v6_specials 的 B1/B3 失敗：改由 driver 注入階段指示後應通過。
"""
from __future__ import annotations

import json
import os
import re
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
from tutor_driver import TutorDriver, load_problems  # noqa: E402

MODEL_DIR = HERE.parent / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / os.environ.get("DRIVER_ADAPTER", "qlora_adapter_v9")
OUT_DIR = HERE / "eval_out_v6"

COMPLETION_WORDS = re.compile(r"完全正確|你已經完整|證明完成|掌握得很好")
QMARK = re.compile(r"[?？]")

DRAFT_H5 = ("證明：對 f(t)=e^t 在 [0,x] 用均值定理，存在 c∈(0,x) 使 e^x−e^0=e^c·x，"
            "即 e^x−1=e^c·x。因為 c≥0 所以 e^c≥1，於是 e^x−1≥x，即 e^x≥1+x。得證。")
DRAFT_H7 = ("證明：對每個 n≥1，n²+1>n²，取倒數得 1/(n²+1)<1/n²。"
            "由比較判別法，∑1/(n²+1) 收斂。得證。")


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
    problems = load_problems()
    tok, model = load()
    OUT_DIR.mkdir(exist_ok=True)
    md, checks = ["# Driver 階段偵測測試（v6）\n"], []

    def check(name, cond):
        checks.append((name, bool(cond)))
        print(("  ✓ " if cond else "  ✗ ") + name)

    # ── P1：H5 學生說「懂了」→ driver 應觸發寫證明請求 ─────────────────────────
    print("[P1] H5 懂了→請寫證明")
    d = TutorDriver(tok, model, problems["H5"])
    d.start()
    d.step("對 f(t)=e^t 在 [0,x] 用均值定理：e^x−1=e^c·x，c∈(0,x)。")
    r = d.step("因為 c>0 所以 e^c>1，而 x>0，所以 e^x−1>x，即 e^x>1+x。整個思路我都懂了！")
    md += ["## P1. H5：學生說懂了", f"- 助教：{r}", ""]
    print(f"  T: {r[:100]}")
    check("P1 自動進入 review/awaiting_submission",
          d.state.get("phase") == "review"
          and d.state.get("review_status") == "awaiting_submission")
    check("P1 轉移由 READINESS_PASSED 事件產生",
          any(e.get("event") == "READINESS_PASSED" and e.get("accepted")
              for e in d.state.get("phase_events", [])))
    check("P1 助教請學生寫完整證明", any(k in r for k in ("寫出", "寫下", "完整證明", "自己寫")))
    check("P1 不宣告完成", not COMPLETION_WORDS.search(r))

    # ── P2：接續 P1，學生交出缺漏草稿 → 審閱模式 ──────────────────────────────
    print("[P2] H5 交草稿（嚴格性遺失）")
    r2 = d.step(f"我寫好了，請幫我審閱：\n\n{DRAFT_H5}")
    md += ["## P2. H5：交缺漏草稿（c≥0 應為 c>0）", f"- 助教：{r2}", ""]
    print(f"  T: {r2[:100]}")
    check("P2 保持審閱工作流", d.state.get("phase") == "review")
    check("P2 以問題指出缺漏", bool(QMARK.search(r2)))
    check("P2 不宣告正確", not COMPLETION_WORDS.search(r2))
    check("P2 指向嚴格性", any(k in r2 for k in ("嚴格", "c>0", "c > 0", "c\\in(0", "大於 0", "大於0")))

    # ── P3：H7 受邀後交草稿（缺比較對象收斂性）→ 審閱模式 ──────────
    print("[P3] H7 受邀後交草稿（缺 ∑1/n² 收斂依據）")
    d3 = TutorDriver(tok, model, problems["H7"])
    d3.start()
    d3._enter_awaiting_submission(event="READINESS_PASSED", source="phase_test_setup")
    r3 = d3.step(f"我寫好了證明，請幫我審閱：\n\n{DRAFT_H7}")
    md += ["## P3. H7：交缺漏草稿（比較對象收斂性未交代）", f"- 助教：{r3}", ""]
    print(f"  T: {r3[:100]}")
    check("P3 全文交稿由事件進入審閱",
          d3.state["phase"] in {"review", "closed"}
          and any(e.get("event") == "FULL_PROOF_SUBMITTED" and e.get("accepted")
                  for e in d3.state.get("phase_events", [])))
    check("P3 以問題指出缺漏", bool(QMARK.search(r3)))
    check("P3 指向收斂性依據或正項條件", any(k in r3 for k in ("收斂", "p-級數", "p=2", "正項", "為什麼")))

    n_pass = sum(1 for _, ok in checks if ok)
    md.append(f"\n## 自動斷言：{n_pass}/{len(checks)} 通過\n")
    for name, ok in checks:
        md.append(f"- {'✓' if ok else '✗'} {name}")
    (OUT_DIR / "driver_phase.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n斷言 {n_pass}/{len(checks)} 通過 → {OUT_DIR/'driver_phase.md'}")
    sys.exit(0 if n_pass == len(checks) else 1)


if __name__ == "__main__":
    main()
