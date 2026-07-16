# -*- coding: utf-8 -*-
"""煙霧測試：4-bit 載入 Qwen3-8B + 新練 adapter，各跑一輪中/英 grounded 教學回覆。
驗證三件事：載得起、會用引導語氣（單問句、不奉送）、雙語都能回。"""
import os
import sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

MODEL = os.environ.get("MODEL_NAME", "Qwen/Qwen3-8B")
ADAPTER = os.environ.get("ADAPTER_DIR", "/workspace/out/qlora8b_adapter_v1")

SYSTEM_ZH = """你是蘇格拉底式高等數學引導助教。下面 <REFERENCE_PROOF> 內是參考解（學生看不到），僅供你確保提問指向正確的下一步，切勿洩漏其內容或最終結論。規則：每次只問一個聚焦問題、用精確數學術語、回覆 80 字內；學生方向正確就肯定並繼續推進，有邏輯漏洞就用問題引導其自行發現。學生走完所有關鍵步驟後，請他把完整證明寫出來；審閱他寫的證明時，若有缺漏就用一個問題指出、讓他自行補上。

<REFERENCE_PROOF>
先限制 |x-2|<1 得 |x+2|<5，故 |x^2-4|<5|x-2|；取 δ=min{1, ε/5}。
</REFERENCE_PROOF>"""

CASES = [
    ("zh", SYSTEM_ZH, "題目：用 ε-δ 定義證明 lim_{x→2} x² = 4。\n\n我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？"),
    ("en", SYSTEM_ZH, "Problem: Prove using the ε-δ definition that lim_{x→2} x² = 4.\n\nI've read the problem but don't know how to start. Could you give me a first hint?"),
]

bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                         bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(
    MODEL, quantization_config=bnb, device_map={"": 0}, dtype=torch.bfloat16)
model = PeftModel.from_pretrained(model, ADAPTER)
model.eval()
print(f"[載入成功] {MODEL} + {ADAPTER}")

fails = 0
for lang, system, user in CASES:
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    enc = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                  return_tensors="pt", return_dict=True).to(model.device)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=200, do_sample=False,
                             repetition_penalty=1.05,
                             pad_token_id=tok.pad_token_id or tok.eos_token_id)
    reply = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    q_ok = ("?" in reply) or ("？" in reply)
    leak = "min{1" in reply.replace(" ", "") or "δ=min" in reply.replace(" ", "")
    print(f"\n[{lang}] 回覆：{reply[:300]}")
    print(f"[{lang}] 含問句: {q_ok} | 疑似洩漏參考解: {leak}")
    fails += (not q_ok) + leak

print(f"\n煙霧測試{'通過 ✓' if fails == 0 else f'失敗 ✗（{fails} 項）'}")
sys.exit(1 if fails else 0)
