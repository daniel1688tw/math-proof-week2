# -*- coding: utf-8 -*-
"""eval_english.py — 英文部署形態評估（v7 雙語 adapter 專用）。

兩部分：
  Part 1  英文 held-out 三情境（泛化）：held_out_en.json 8 題 × {S1 首問 / S2 糾錯 / S3 逼問}，
          走 TutorDriver（會偵測 session 語言 = en），輸出 eval_out_english/heldout_en.md。
  Part 2  多輪 IVT 重現（使用者原始 bug）：用英文 B1（介值定理）逐輪餵入使用者 transcript 的
          學生訊息，檢查助教是否重複問句、是否回應學生當下困惑。輸出 eval_out_english/ivt_multiturn.md。

用法：
  $env:FINAL_ADAPTER="qlora_adapter_v7"
  conda run -n lora_project --live-stream python dataset\\eval_english.py
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
ADAPTER_DIR = HERE / os.environ.get("FINAL_ADAPTER", "qlora_adapter_v7")
OUT_DIR = HERE / "eval_out_english"

# 英文三情境 opener（對應中文 eval_final_driver 的 S1/S2/S3）
SCENARIOS = {
    "S1_first": lambda att: "I've read the problem but don't know how to start. Could you give me a first hint?",
    "S2_rectify": lambda att: f"Here is my attempt: {att['attempt']}",
    "S3_leak": lambda att: "I'm in a hurry — please just write the full proof for me, don't ask me questions.",
}

# Part 2：使用者原始 transcript 的英文學生訊息（IVT 題），逐輪餵入。
IVT_STATEMENT = (r"Suppose $f$ is continuous on $[a,b]$ and $f(a)<0<f(b)$. "
                 r"Prove that the equation $f(x)=0$ has a solution in $(a,b)$.")
IVT_PROOF = (
    r"Without loss of generality $f(a)<0<f(b)$. Let $S=\{x\in[a,b]:f(x)<0\}$. "
    r"$S$ is nonempty (contains $a$) and bounded above by $b$, so $c=\sup S$ exists in $[a,b]$. "
    r"If $f(c)>0$, continuity gives $f>0$ on $(c-\delta,c]$, making $c-\delta$ an upper bound of $S$, "
    r"contradicting $c=\sup S$. If $f(c)<0$ then $c<b$ and continuity gives $f<0$ on $[c,c+\delta)$, "
    r"so $S$ has points beyond $c$, a contradiction. Hence $f(c)=0$; since $f(a),f(b)\ne0$, $c\in(a,b)$."
)
IVT_STUDENT_TURNS = [
    "I have not started yet. I am very confused, so please guide me one tiny step at a time.",
    "I think IVT requires the function to be continuous on a closed interval like [a,b]. Here f is continuous on [a,b], but I am not sure what value we are trying to get.",
    "The hypothesis is that f is continuous on [a,b]. I think that checks the continuity condition for IVT, but I still do not understand what value IVT is supposed to find.",
    "We already checked that f is continuous on [a,b], so the continuity condition is satisfied. My remaining confusion is: what intermediate value should IVT give us? Is it 0 because f(a)<0<f(b)?",
    "So 0 lies between f(a) and f(b). Then IVT gives some c in [a,b] with f(c)=0, right? But why must c be in the open interval (a,b), not at an endpoint?",
    "If c=a then f(c)=f(a), but f(c)=0 while f(a)<0, so that is impossible. Similarly c cannot be b since f(b)>0. So c is not an endpoint.",
    "Since f is continuous on [a,b] and f(a)<0<f(b), by IVT there is c in [a,b] with f(c)=0; c cannot be a or b because f(a),f(b) are nonzero, so c is in (a,b). Is the proof complete now?",
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


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def part1_heldout(tok, model, md):
    problems = json.loads((HERE / "held_out_en.json").read_text(encoding="utf-8"))
    ladders = json.loads((HERE / "hint_ladders_en.json").read_text(encoding="utf-8"))
    attempts = json.loads((HERE / "held_out_attempts_en.json").read_text(encoding="utf-8"))
    md.append("# Part 1 — English held-out, 3 scenarios (deployment form)\n")
    records = []
    for p in problems:
        pid = p["id"]
        prob = dict(p)
        if pid in ladders:
            prob["hint_ladder_en"] = ladders[pid]
        md.append(f"## {pid} {p['statement']}")
        rec = {"id": pid, "scenarios": {}}
        for sname, mk in SCENARIOS.items():
            d = TutorDriver(tok, model, prob)
            reply = d.start(opener=mk(attempts[pid]))
            log = d.state["turns"][-1]
            rec["scenarios"][sname] = {
                "reply": reply, "phase": d.state.get("phase"),
                "lang": d.state.get("lang"), "regenerated": log.regenerated,
            }
            md.append(f"### {sname} (phase={d.state.get('phase')}, lang={d.state.get('lang')}"
                      f"{', regenerated' if log.regenerated else ''})")
            md.append(f"- {reply}\n")
            print(f"[H/{pid}/{sname}] phase={d.state.get('phase')} lang={d.state.get('lang')} done")
        records.append(rec)
    return records


def part2_ivt_multiturn(tok, model, md):
    md.append("\n# Part 2 — Multi-turn IVT (reproduces the original English repeat bug)\n")
    prob = {"id": "IVT", "statement": IVT_STATEMENT, "reference_proof": IVT_PROOF}
    d = TutorDriver(tok, model, prob)
    first = d.start(opener=IVT_STUDENT_TURNS[0])
    md.append(f"**Student:** {IVT_STUDENT_TURNS[0]}")
    md.append(f"**Tutor:** {first}\n")
    print(f"[IVT/t0] lang={d.state.get('lang')} :: {first}")
    tutor_replies = [first]
    repeats = 0
    for i, s in enumerate(IVT_STUDENT_TURNS[1:], 1):
        reply = d.step(s)
        md.append(f"**Student:** {s}")
        md.append(f"**Tutor:** {reply}\n")
        # 重複偵測：與先前任一助教回覆正規化後相同
        if any(_norm(reply) == _norm(prev) for prev in tutor_replies):
            repeats += 1
            md.append(f"> ⚠️ REPEAT of an earlier tutor question (turn {i})\n")
        tutor_replies.append(reply)
        print(f"[IVT/t{i}] phase={d.state.get('phase')} :: {reply}")
    md.append(f"\n**Repeat count across {len(tutor_replies)} tutor turns: {repeats}**")
    return repeats


def main():
    OUT_DIR.mkdir(exist_ok=True)
    tok, model = load()
    print(f"adapter = {ADAPTER_DIR.name}")
    md1 = []
    part1_heldout(tok, model, md1)
    (OUT_DIR / "heldout_en.md").write_text("\n".join(md1), encoding="utf-8")
    md2 = []
    repeats = part2_ivt_multiturn(tok, model, md2)
    (OUT_DIR / "ivt_multiturn.md").write_text("\n".join(md2), encoding="utf-8")
    print(f"\n產出：{OUT_DIR/'heldout_en.md'}")
    print(f"產出：{OUT_DIR/'ivt_multiturn.md'}")
    print(f"IVT 多輪重複問句次數：{repeats}（期望 0）")


if __name__ == "__main__":
    main()
