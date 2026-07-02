"""
inference.py — 載入微調後的蘇格拉底助教（基底 4-bit + LoRA adapter）做多輪引導對話。

與 simple_4B_ollama.py 的差異：那支是「直接給完整證明」的對照組；這支是微調後的
「引導式」助教——一次只問一個引導問題、不直接給答案，陪學生一步步完成微積分證明。

用法：
  # 互動多輪對話（輸入 quit 離開；輸入 reset 清空對話重開）
  conda run -n lora_project --live-stream python inference.py

  # 單題起手（給一個問題，看模型的第一個引導提問）
  conda run -n lora_project --live-stream python inference.py "Prove that f(x)=x^2 is continuous at x=2."

  # 不載入 adapter、只看基底模型（對照微調前後差異）
  set USE_ADAPTER=0 && conda run -n lora_project --live-stream python inference.py
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTHONNOUSERSITE", "1")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from common import (
    ADAPTER_DIR,
    MODEL_NAME,
    STUDENT_NO_ATTEMPT_PREFIX,
    SYSTEM_SOCRATIC,
    build_grounded_system,
)

USE_ADAPTER = os.environ.get("USE_ADAPTER", "1") != "0"

# improve.md 問題⑦：種子已含「帶/不帶前綴」兩版，模型對純題目本身也能引導，
# 故自動補綴預設「關閉」（降低對前綴的脆弱依賴）。需要時設 WRAP=1 開啟。
_AUTO_WRAP = os.environ.get("WRAP", "0") == "1"

# improve.md 問題③：solution-grounded。設 REF_FILE=<參考解 .txt 路徑> 即可把參考解
# 當「答案卡」放進 system（學生看不到），讓引導指向正確下一步。
# （純 transformers 流程，不在程序內呼叫 Ollama，避免與 4-bit 模型搶 6GB；
#   參考解可先用 guided_tutor.py / gen_reference_solutions.py 產出後存成檔。）
_REF_FILE = os.environ.get("REF_FILE", "").strip()


def _system_prompt() -> str:
    if _REF_FILE and os.path.exists(_REF_FILE):
        ref = open(_REF_FILE, encoding="utf-8").read()
        print(f"  已載入參考解（grounded）：{_REF_FILE}")
        return build_grounded_system(ref)
    return SYSTEM_SOCRATIC

# 「純題目」的開頭關鍵字——若 user 第一輪輸入符合此模式，視為「尚未嘗試」並補綴
_PROBLEM_STARTS = re.compile(
    r"^\s*(prove|show|let|define|suppose|assume|consider|given|find|"
    r"determine|evaluate|compute|if\s+f|if\s+g|if\s+\()",
    re.IGNORECASE,
)
# 「已有嘗試」的標誌詞——出現任一個就不補綴
_HAS_ATTEMPT_MARKERS = re.compile(
    r"(my attempt|i tried|i think|i got|here is|here's|i have|"
    r"is this correct|my work|my solution|my approach)",
    re.IGNORECASE,
)


def _should_wrap(text: str) -> bool:
    """判斷是否需要補綴 STUDENT_NO_ATTEMPT_PREFIX。

    邏輯：以題目語句開頭 AND 沒有任何「我已嘗試」的字樣。
    """
    return bool(_PROBLEM_STARTS.match(text)) and not bool(
        _HAS_ATTEMPT_MARKERS.search(text)
    )


def _wrap_if_needed(text: str) -> tuple[str, bool]:
    """若需要，在 user 訊息後附加「尚未嘗試」前綴，回傳 (包裝後的文字, 是否做了包裝)。"""
    if _AUTO_WRAP and _should_wrap(text):
        return text + STUDENT_NO_ATTEMPT_PREFIX, True
    return text, False


def load_model():
    tok = AutoTokenizer.from_pretrained(MODEL_NAME)
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, quantization_config=bnb, device_map={"": 0},
        torch_dtype=torch.bfloat16,
    )
    if USE_ADAPTER and os.path.isdir(ADAPTER_DIR):
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, ADAPTER_DIR)
        print(f"  已載入 LoRA adapter：{ADAPTER_DIR}")
    else:
        print("  使用基底模型（未載入 adapter）")
    model.eval()
    return tok, model


@torch.no_grad()
def reply(tok, model, messages: list[dict]) -> str:
    enc = tok.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
    ).to(model.device)
    out = model.generate(
        **enc,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.05,
        pad_token_id=tok.pad_token_id or tok.eos_token_id,
    )
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def main() -> None:
    tok, model = load_model()
    args = sys.argv[1:]

    base = [{"role": "system", "content": _system_prompt()}]

    if args:  # 單題起手模式
        raw = " ".join(args)
        wrapped, did_wrap = _wrap_if_needed(raw)
        if did_wrap:
            print("（偵測到純題目輸入，已補綴「尚未嘗試」情境）")
        messages = base + [{"role": "user", "content": wrapped}]
        print("\nTutor:", reply(tok, model, messages))
        return

    print("\n蘇格拉底微積分助教（quit 離開、reset 重開）\n")
    messages = list(base)
    is_first_turn = True
    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user or user.lower() in {"quit", "exit", "q"}:
            break
        if user.lower() == "reset":
            messages = list(base)
            is_first_turn = True
            print("（已重置對話）\n")
            continue
        # 第一輪且無嘗試：自動補綴情境前綴
        if is_first_turn:
            wrapped, did_wrap = _wrap_if_needed(user)
            if did_wrap:
                print("（補綴「尚未嘗試」情境，如需關閉請設 NO_WRAP=1）")
            user = wrapped
            is_first_turn = False
        messages.append({"role": "user", "content": user})
        ans = reply(tok, model, messages)
        messages.append({"role": "assistant", "content": ans})
        print(f"Tutor: {ans}\n")


if __name__ == "__main__":
    main()
