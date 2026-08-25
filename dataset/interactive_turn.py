# -*- coding: utf-8 -*-
"""interactive_turn.py — 單輪呼叫版 TutorDriver，供人類（或 Claude）真實逐輪對話。

每次呼叫載入模型一次、還原上次存的對話狀態、推進一輪、存回狀態。
第一次呼叫（無 --student）觸發 d.start()；之後每次帶 --student "文字" 觸發 d.step()。

用法：
  python interactive_turn.py --problem ADV1 --state session.json                 # 開場
  python interactive_turn.py --problem ADV1 --state session.json --student "..."  # 之後每輪
  python interactive_turn.py --problem ADV1 --state session.json --reset          # 重來
"""
from __future__ import annotations

import argparse
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
from tutor_driver import TurnLog, TutorDriver, load_problems  # noqa: E402

MODEL_DIR = HERE.parent / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / os.environ.get("ADAPTER", "qlora_adapter_v9")


def load_model():
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


def load_extra_problem(pid: str, problems: dict):
    """允許測試不在 problems.json/held_out.json/hard_math_major.json 裡的一次性題目。"""
    if pid in problems:
        return
    xdomain = HERE / "xdomain_problems.json"
    if xdomain.exists():
        for p in json.loads(xdomain.read_text(encoding="utf-8")):
            if p["id"] == pid:
                problems[pid] = p
                return
    extra = HERE / "adv_test_problem.json"
    if extra.exists():
        p = json.loads(extra.read_text(encoding="utf-8"))
        if p["id"] == pid:
            problems[pid] = p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--student", default=None)
    ap.add_argument("--opener", default=None)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    state_path = Path(args.state)
    if args.reset and state_path.exists():
        state_path.unlink()

    problems = load_problems()
    load_extra_problem(args.problem, problems)
    problem = problems[args.problem]

    tok, model = load_model()
    d = TutorDriver(tok, model, problem)

    if state_path.exists():
        # 整包還原（TutorDriver.load_state）。舊版只挑 4 個欄位還原，done_closed、
        # fb_idx、walk_* 每輪歸零：收尾修復失效（完成後仍被追問同一句）、保底句無法
        # 輪換、逐步教學卡在第一步。詳見 update.md 稽核 F2。
        d.load_state(json.loads(state_path.read_text(encoding="utf-8")))

    if args.student is None and not state_path.exists():
        reply = d.start(opener=args.opener) if args.opener else d.start()
    elif args.student is not None:
        reply = d.step(args.student)
    else:
        print("[狀態已存在但未提供 --student；若要開場請先 --reset]")
        sys.exit(1)

    turn_info = d.state["turns"][-1] if d.state["turns"] else TurnLog(level=0, stuck_count=0)
    state_path.write_text(json.dumps(d.dump_state(), ensure_ascii=False, indent=2),
                          encoding="utf-8")

    print(f"[等級={turn_info.level} phase={d.state.get('phase')} "
          f"stuck_count={d.state['stuck_count']} "
          f"done_closed={bool(d.state.get('done_closed'))} "
          f"guards={turn_info.guards}]")
    print("助教：" + reply)


if __name__ == "__main__":
    main()
