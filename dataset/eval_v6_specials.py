# -*- coding: utf-8 -*-
"""eval_v6_specials.py — v6 兩項新能力的專項測試（測試題皆不在對應訓練對話中）。

A. 節奏錯位（rhythm）：
   A1. M4（Darboux）重跑當初暴露缺陷的腳本——學生在中間步驟未補完前宣告「證完了」，
       助教必須「不宣告完成、用問題拉回缺的那一步」（v3 當時搶先講結論並說「你已經完整了」）。
   A2. H7：學生跳步宣告完成（比較不等式沒建立就說證完），助教應拉回。
B. 寫證明→審閱（writeup）：
   B1. H5：學生說「思路都懂了」→ 助教應請學生寫出完整證明。
   B2. H5：學生交出帶缺漏的證明草稿（≥ 沒有處理成嚴格 >）→ 助教應以問題指出缺漏，
       不得宣告正確、不得自己重寫證明。
   B3. H7：草稿缺「比較對象為何收斂」的依據 → 助教應以問題指出。

自動斷言 + markdown 逐字稿輸出 eval_out_v6/specials.md。
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
from build import SYSTEM_TEMPLATE  # noqa: E402

MODEL_DIR = HERE.parent / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / os.environ.get("SPECIAL_ADAPTER", "qlora_adapter_v6")
OUT_DIR = HERE / "eval_out_v6"

COMPLETION_WORDS = re.compile(r"完全正確|你已經完整|證明完成|完成了|非常嚴謹|掌握得很好")
QMARK = re.compile(r"[?？]")


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


@torch.no_grad()
def gen(tok, model, messages, max_new=260):
    enc = tok.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
    ).to(model.device)
    out = model.generate(
        **enc, max_new_tokens=max_new, do_sample=False,
        repetition_penalty=1.05, pad_token_id=tok.pad_token_id or tok.eos_token_id,
    )
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def run_script(tok, model, problem, user_turns, md, title):
    """依序送 user 回合、收集助教回覆；回傳所有回覆。"""
    system = SYSTEM_TEMPLATE.format(proof=problem["reference_proof"])
    messages = [{"role": "system", "content": system}]
    replies = []
    md.append(f"## {title}")
    md.append(f"**題目**：{problem['statement']}\n")
    for u in user_turns:
        messages.append({"role": "user", "content": u})
        md.append(f"- **學生**：{u}")
        r = gen(tok, model, messages)
        messages.append({"role": "assistant", "content": r})
        md.append(f"- **助教**：{r}")
        replies.append(r)
        print(f"  S: {u[:60]}")
        print(f"  T: {r[:80]}")
    md.append("")
    return replies


def main():
    def P(fname):
        return {p["id"]: p for p in json.loads((HERE / fname).read_text(encoding="utf-8"))}

    hard = P("hard_math_major.json")
    held = P("held_out.json")
    tok, model = load()
    OUT_DIR.mkdir(exist_ok=True)
    md, checks = [f"# v6 專項測試（adapter={ADAPTER_DIR.name}）\n"], []

    def check(name, cond):
        checks.append((name, bool(cond)))
        print(("  ✓ " if cond else "  ✗ ") + name)

    # ── A1. M4 節奏錯位重測（重演當初 v3 失敗的關鍵時刻）───────────────────────
    print("\n[A1] M4 節奏錯位")
    m4 = hard["M4"]
    replies = run_script(tok, model, m4, [
        f"題目：{m4['statement']}\n\n我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？",
        "可以定義 g(x)=f(x)-kx，這樣 g'(x)=f'(x)-k。",
        # 學生跳步：端點導數符號還沒算、端點排除還沒論證，直接宣告完成
        "所以 g 有最小值點 c，由費馬定理 g'(c)=0，f'(c)=k，證完了！",
    ], md, "A1. M4：學生跳步宣告完成")
    last = replies[-1]
    check("A1 助教不宣告完成", not COMPLETION_WORDS.search(last))
    check("A1 助教以問題拉回缺漏步驟", bool(QMARK.search(last)))
    check("A1 拉回的內容指向缺的步驟（端點/內部/符號）",
          any(k in last for k in ("端點", "內部", "符號", "最小值點", "為什麼")))

    # ── A2. H7 節奏錯位───────────────────────────────────────────────────────
    print("\n[A2] H7 節奏錯位")
    h7 = held["H7"]
    replies = run_script(tok, model, h7, [
        f"題目：{h7['statement']}\n\n我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？",
        # 跳步：比較不等式還沒建立就宣告完成
        "跟 ∑1/n² 比就好了，由比較判別法收斂，證完了！",
    ], md, "A2. H7：比較不等式未建立就宣告完成")
    last = replies[-1]
    check("A2 助教不宣告完成", not COMPLETION_WORDS.search(last))
    check("A2 助教要求補不等式（含 不等式/大小/上界/≤ 等字眼）",
          any(k in last for k in ("不等式", "大小", "上界", "比較", "\\le", "≤")))

    # ── B1. H5 請學生寫證明────────────────────────────────────────────────────
    print("\n[B1] H5 寫證明請求")
    h5 = held["H5"]
    b1_replies = run_script(tok, model, h5, [
        f"題目：{h5['statement']}\n\n我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？",
        "對 f(t)=e^t 在 [0,x] 用均值定理：e^x−1=e^c·x，c∈(0,x)。",
        "因為 c>0 所以 e^c>1，而 x>0，所以 e^x−1>x，即 e^x>1+x。整個思路我都懂了！",
    ], md, "B1. H5：學生表示思路已懂")
    last = b1_replies[-1]
    check("B1 助教請學生寫出完整證明", any(k in last for k in ("寫出", "寫下", "把完整證明", "自己寫")))

    # ── B2. H5 審閱帶缺漏草稿（≥ 未處理成嚴格 >）──────────────────────────────
    print("\n[B2] H5 審閱缺漏草稿")
    draft_h5 = ("證明：對 f(t)=e^t 在 [0,x] 用均值定理，存在 c∈(0,x) 使 e^x−e^0=e^c·x，"
                "即 e^x−1=e^c·x。因為 c≥0 所以 e^c≥1，於是 e^x−1≥x，即 e^x≥1+x。得證。")
    b2_replies = run_script(tok, model, h5, [
        f"題目：{h5['statement']}\n\n我把完整證明寫好了，請幫我審閱：\n\n{draft_h5}",
    ], md, "B2. H5：審閱缺漏草稿（嚴格性遺失）")
    last = b2_replies[-1]
    check("B2 不宣告正確", not COMPLETION_WORDS.search(last))
    check("B2 以問題指出缺漏", bool(QMARK.search(last)))
    check("B2 指向嚴格性（>/嚴格/c>0）", any(k in last for k in ("嚴格", "c>0", "c > 0", ">")))

    # ── B3. H7 審閱帶缺漏草稿（比較對象收斂性沒交代）─────────────────────────
    print("\n[B3] H7 審閱缺漏草稿")
    draft_h7 = ("證明：對每個 n≥1，n²+1>n²，取倒數得 1/(n²+1)<1/n²。"
                "由比較判別法，∑1/(n²+1) 收斂。得證。")
    b3_replies = run_script(tok, model, h7, [
        f"題目：{h7['statement']}\n\n我把完整證明寫好了，請幫我審閱：\n\n{draft_h7}",
    ], md, "B3. H7：審閱缺漏草稿（比較對象收斂性未交代）")
    last = b3_replies[-1]
    check("B3 以問題指出缺漏", bool(QMARK.search(last)))
    check("B3 指向『∑1/n² 為何收斂』或正項條件",
          any(k in last for k in ("收斂", "p-級數", "p=2", "正")))

    # ── 總結 ──────────────────────────────────────────────────────────────────
    n_pass = sum(1 for _, ok in checks if ok)
    md.append(f"\n## 自動斷言：{n_pass}/{len(checks)} 通過\n")
    for name, ok in checks:
        md.append(f"- {'✓' if ok else '✗'} {name}")
    (OUT_DIR / "specials.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n斷言 {n_pass}/{len(checks)} 通過 → {OUT_DIR/'specials.md'}")
    sys.exit(0 if n_pass == len(checks) else 1)


if __name__ == "__main__":
    main()
