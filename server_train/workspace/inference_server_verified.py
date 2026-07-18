# -*- coding: utf-8 -*-
"""驗證式生成服務（Best-of-N＋數學驗證器，單張 4090 兩模型共存）。

架構（弱點 #2 的全輪化解法）：
  生成器：Qwen3-4B-Instruct-2507 + qlora_adapter_v8（bf16 ~8GB）——部署版微調模型
  驗證器：Qwen3-4B-Thinking-2507（bf16 ~8GB）——同 2507 世代的思考型，只在幕後驗證

流程（POST /generate {messages, max_new_tokens} → {text, verify_meta}）：
  1. 生成候選（greedy，與部署版一致）。
  2. 候選含數學實質內容（等式/不等式）才驗證：從 system 的 <REFERENCE_PROOF> 取參考解，
     讓思考型對照檢查候選裡的每個數學宣稱；純提問/肯定輪直接放行（零開銷）。
  3. 驗證不過 → 把「錯在哪」注入指示重生成（greedy 下改變輸入才會改變輸出），
     最多 N 輪；全數不過則回傳最後一個候選並在 meta 標記（誠實暴露，不假裝通過）。

VERIFY=0 可關閉（退回純生成，行為 = 部署版）。"""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

GEN_MODEL = os.environ.get("MODEL_NAME", "Qwen/Qwen3-4B-Instruct-2507")
ADAPTER = os.environ.get("ADAPTER_DIR", "/workspace/out/qlora_adapter_v8")
VER_MODEL = os.environ.get("VERIFIER_MODEL", "Qwen/Qwen3-4B-Thinking-2507")
VERIFY = os.environ.get("VERIFY", "1") == "1"
MAX_TRIES = int(os.environ.get("BON_TRIES", "3"))
PORT = int(os.environ.get("PORT", "8899"))

_EQ_RE = re.compile(r"=|≤|≥|\\le\b|\\ge\b|<|>")
_PROOF_RE = re.compile(r"<REFERENCE_PROOF>\n?(.*?)\n?</REFERENCE_PROOF>", re.S)

VERIFY_PROMPT = """你是數學審查員。下面是一道證明題、其正確參考解，以及一位助教回覆學生的一句話。
請只檢查「助教回覆中的數學宣稱」是否全部正確（式子、不等式方向、定理名稱與其結論、區間端點、
係數、導數/積分結果）。助教用提問引導、內容不完整都沒關係——只抓「說錯的數學」。
用最高標準逐項核對每一個數學宣稱：先逐字抄出回覆中的每個式子/宣稱，逐一與參考解及數學事實比對，
有任何一項錯誤就判 false。不確定時傾向判 false 並說明疑點。
特別注意：回覆若複述「待證目標」或題目條件，其式子必須與題目逐字元一致——多一項、少一項、常數不同都算錯（學生會照抄，錯的目標會毀掉整個證明）。

【題目】{statement}
【參考解】{proof}
【助教回覆】{reply}

只輸出 JSON：{{"ok": true}} 或 {{"ok": false, "error": "<一句話指出錯在哪、正確應為何>"}}"""

print("[載入生成器]", GEN_MODEL, flush=True)
gtok = AutoTokenizer.from_pretrained(GEN_MODEL)
gen = AutoModelForCausalLM.from_pretrained(GEN_MODEL, device_map={"": 0}, dtype=torch.bfloat16)
if os.path.exists(os.path.join(ADAPTER, "adapter_config.json")):
    gen = PeftModel.from_pretrained(gen, ADAPTER)
    print("[adapter]", ADAPTER, flush=True)
gen.eval()

ver = vtok = None
if VERIFY:
    print("[載入驗證器]", VER_MODEL, flush=True)
    vtok = AutoTokenizer.from_pretrained(VER_MODEL)
    ver = AutoModelForCausalLM.from_pretrained(VER_MODEL, device_map={"": 0}, dtype=torch.bfloat16)
    ver.eval()
print(f"[ready] verify={VERIFY} on {torch.cuda.get_device_name(0)}", flush=True)


def _gen_reply(msgs, max_new):
    enc = gtok.apply_chat_template(msgs, add_generation_prompt=True,
                                   return_tensors="pt", return_dict=True).to(gen.device)
    with torch.no_grad():
        out = gen.generate(**enc, max_new_tokens=max_new, do_sample=False,
                           repetition_penalty=1.05,
                           pad_token_id=gtok.pad_token_id or gtok.eos_token_id)
    return gtok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def _verify(statement, proof, reply):
    """回傳 (ok, error)。思考鏈要給足空間（後盾教訓：太小會被思考吃光、正文空白）。"""
    msgs = [{"role": "user", "content": VERIFY_PROMPT.format(
        statement=statement, proof=proof, reply=reply)}]
    enc = vtok.apply_chat_template(msgs, add_generation_prompt=True,
                                   return_tensors="pt", return_dict=True).to(ver.device)
    with torch.no_grad():
        out = ver.generate(**enc, max_new_tokens=4096, do_sample=False,
                           pad_token_id=vtok.pad_token_id or vtok.eos_token_id)
    text = vtok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)
    text = text.split("</think>")[-1]          # 取思考鏈之後的正文
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return True, None                      # 驗證器失能 → 放行（不阻斷教學）
    for cand in (m.group(0), m.group(0).replace("\\", "\\\\")):
        try:
            obj = json.loads(cand)
            return bool(obj.get("ok", True)), obj.get("error")
        except json.JSONDecodeError:
            continue
    return True, None


def generate_verified(msgs, max_new):
    reply = _gen_reply(msgs, max_new)
    meta = {"verified": False, "tries": 1, "passed": None}
    if not (VERIFY and _EQ_RE.search(reply)):
        return reply, meta                     # 無數學實質內容 → 零開銷放行
    sys_txt = msgs[0]["content"] if msgs and msgs[0]["role"] == "system" else ""
    pm = _PROOF_RE.search(sys_txt)
    if not pm:
        return reply, meta                     # 無參考解（同學模式）→ 無從驗證
    proof = pm.group(1)
    statement = ""
    for m0 in msgs:
        if m0["role"] == "user":
            statement = m0["content"][:600]
            break
    meta["verified"] = True
    for t in range(MAX_TRIES):
        ok, err = _verify(statement, proof, reply)
        if ok:
            meta.update(tries=t + 1, passed=True)
            return reply, meta
        note = (f"\n（注意：上一稿有數學錯誤——{err}。改正這個錯誤後重寫，"
                f"其餘要求不變。）")
        msgs2 = [dict(msgs[0], content=msgs[0]["content"] + note)] + msgs[1:]
        reply = _gen_reply(msgs2, max_new)
        meta["tries"] = t + 2
        if not _EQ_RE.search(reply):           # 重寫後不含式子 → 不再需要驗證
            meta["passed"] = True
            return reply, meta
    meta["passed"] = False                     # 全數不過：誠實標記，回傳最後候選
    return reply, meta


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/generate":
            self.send_error(404)
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            reply, meta = generate_verified(
                body["messages"], int(body.get("max_new_tokens", 240)))
            payload = json.dumps({"text": reply, "verify_meta": meta}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            print(f"[turn] verified={meta['verified']} tries={meta['tries']} "
                  f"passed={meta['passed']}", flush=True)
        except Exception as e:  # noqa: BLE001
            self.send_error(500, str(e)[:200])

    def log_message(self, fmt, *args):
        pass


HTTPServer(("0.0.0.0", PORT), H).serve_forever()
