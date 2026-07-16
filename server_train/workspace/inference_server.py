# -*- coding: utf-8 -*-
"""極簡推論服務：4-bit 載入 Qwen3-8B + adapter，POST /generate {messages, max_new_tokens} → {text}。
只給 regression suite 遠端評估用（本機 4050 載不動 8B）；容器 port 只綁 127.0.0.1，走 SSH tunnel。
greedy、單執行緒（http.server 序列處理請求，天然符合逐題評估的使用型態）。"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

MODEL = os.environ.get("MODEL_NAME", "Qwen/Qwen3-8B")
ADAPTER = os.environ.get("ADAPTER_DIR", "/workspace/out/qlora8b_adapter_v1")
PORT = int(os.environ.get("PORT", "8899"))

# 預設 bf16（24GB 裝得下 8B，推理 40+ tok/s）；QUANT=4bit 才用 bnb
# （bnb 4-bit 推理在此路徑 <1.2 tok/s，只適合訓練與 Colab T4 部署，不適合評估服務）。
tok = AutoTokenizer.from_pretrained(MODEL)
if os.environ.get("QUANT") == "4bit":
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_use_double_quant=True,
                             bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, quantization_config=bnb, device_map={"": 0}, dtype=torch.bfloat16)
else:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, device_map={"": 0}, dtype=torch.bfloat16)
model = PeftModel.from_pretrained(model, ADAPTER)
model.eval()
print(f"[ready] {MODEL} + {ADAPTER} on {torch.cuda.get_device_name(0)}", flush=True)


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/generate":
            self.send_error(404)
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            msgs = body["messages"]
            max_new = int(body.get("max_new_tokens", 240))
            enc = tok.apply_chat_template(
                msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True
            ).to(model.device)
            with torch.no_grad():
                out = model.generate(
                    **enc, max_new_tokens=max_new, do_sample=False,
                    repetition_penalty=1.05,
                    pad_token_id=tok.pad_token_id or tok.eos_token_id)
            text = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)
            payload = json.dumps({"text": text}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as e:  # noqa: BLE001
            self.send_error(500, str(e)[:200])

    def log_message(self, fmt, *args):  # 安靜一點，只留錯誤
        pass


HTTPServer(("0.0.0.0", PORT), H).serve_forever()
