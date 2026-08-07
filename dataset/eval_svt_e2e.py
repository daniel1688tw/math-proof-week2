# -*- coding: utf-8 -*-
"""eval_svt_e2e.py — 自我驗證教學端對端驗證（需 GPU；教學步驟切分需 Ollama，離線走保底）。

情境 A（逐步教學）：學生把 A6 的提示梯全部耗盡仍卡住 → 應自動進入 walkthrough，
  一步步教到完，最後轉 writeup 請學生自己寫證明。
情境 B（同學模式）：unverified 難題 → 首輪誠實聲明；學生質疑 → 反省檢查。
產出 eval_out_xdomain/svt_e2e.md（完整對話記錄）。
"""
from __future__ import annotations

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
ADAPTER_DIR = HERE / os.environ.get("FINAL_ADAPTER", "qlora_adapter_v9")
OUT = HERE / "eval_out_xdomain" / "svt_e2e.md"


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


def run_dialogue(d: TutorDriver, student_turns: list, md: list):
    """student_turns 的元素可以是字串，或 None＝「回答當前教學步驟的標準答案」。

    逐步教學改成「答對才前進」後，寫死的「我懂了」會被判成答錯而停在同一步——
    端對端要驗的是教完整條路徑，所以那幾輪改成逐步讀取當前 expected_answer。
    """
    reply = d.start()
    md.append(f"**助教**（phase={d.state.get('phase')}）：{reply}\n")
    for msg in student_turns:
        if msg is None:
            presented = d.state.get("walk_presented_step") or {}
            msg = presented.get("expected_answer") or "這一步我懂了。"
        md.append(f"**學生**：{msg}\n")
        reply = d.step(msg)
        info = (f"phase={d.state.get('phase')} walk_idx={d.state.get('walk_idx')} "
                f"walk_active={d.state.get('walk_active')}")
        md.append(f"**助教**（{info}）：{reply}\n")
        print(f"  [{info}] {reply[:60]}…")


def main():
    tok, model = load()
    md = ["# 自我驗證教學端對端\n"]

    # ── 情境 A：耗盡提示梯 → walkthrough → 教完 → writeup ─────────────────────
    md.append("## A. 逐步教學（A6，提示梯 2 條全數耗盡）\n")
    probs = load_problems_with_ladders()
    d = TutorDriver(tok, model, dict(probs["A6"]), backstop=False)
    stuck_then_learn = [
        "我不知道怎麼開始。",          # 卡1 → 等級1
        "還是想不出來。",              # 卡2 → 等級2（ladder[0]）
        "嗯…還是不會。",              # 卡1
        "真的想不到，再提示我。",       # 卡2 → 等級2（ladder[1]，梯用盡）
        "我還是不會。",                # 卡1
        "完全沒頭緒，我真的不會。",     # 卡2 → 應進 walkthrough
        None,                          # 答對當前步驟 → 下一步
        "聽不懂這步。",                # 卡 → 重講同一步
        None, None, None, None, None,  # 逐步答對 → 教完 → writeup_request
    ]
    run_dialogue(d, stuck_then_learn, md)

    # ── 情境 B：unverified 難題 → 同學模式 ────────────────────────────────────
    md.append("\n## B. 同學模式（unverified，含質疑反省）\n")
    peer_prob = {
        "id": "PEER1", "grounding": "unverified",
        "statement": r"證明：若 $f:[0,1]\to[0,1]$ 為連續函數，且 $f\circ f=f$，"
                     r"則 $f$ 的不動點集合是非空閉區間。",
    }
    d2 = TutorDriver(tok, model, peer_prob, backstop=False)
    peer_turns = [
        "我猜不動點集合就是 f 的值域，對嗎？",
        "你錯了吧，值域不一定是區間吧？",
        "嗯，那我們先證非空好了，你覺得從哪裡下手？",
    ]
    run_dialogue(d2, peer_turns, md)

    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"\n產出：{OUT}")


if __name__ == "__main__":
    main()
