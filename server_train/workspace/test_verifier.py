# -*- coding: utf-8 -*-
"""驗證器校準測試：歷史真實錯誤 4 例＋正確回覆 3 例，量測抓錯率與誤殺率。
只載驗證器（跑前先 down 掉驗證式服務，避免同卡爆顯存）。"""
import json
import re
import sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

VER_MODEL = "Qwen/Qwen3-4B-Thinking-2507"

VERIFY_PROMPT = """你是數學審查員。下面是一道證明題、其正確參考解，以及一位助教回覆學生的一句話。
請只檢查「助教回覆中的數學宣稱」是否全部正確（式子、不等式方向、定理名稱與其結論、區間端點、
係數、導數/積分結果）。助教用提問引導、內容不完整都沒關係——只抓「說錯的數學」。
用最高標準逐項核對每一個數學宣稱：先逐字抄出回覆中的每個式子/宣稱，逐一與參考解及數學事實比對，
有任何一項錯誤就判 false。不確定時傾向判 false 並說明疑點。
特別注意：回覆若複述「待證目標」或題目條件，其式子必須與題目逐字元一致——多一項、少一項、常數不同都算錯（學生會照抄，錯的目標會毀掉整個證明）。
以問句形式出現的式子同樣要驗證：「乘以 A 之後會得到 X 嗎？」中的 X 若在數學上不是正確結果，就算錯（誘導學生接受錯誤式子比直接寫錯更隱蔽）。

【題目】{statement}
【參考解】{proof}
【助教回覆】{reply}

只輸出 JSON：{{"ok": true}} 或 {{"ok": false, "error": "<一句話指出錯在哪、正確應為何>"}}"""

STMT_H5 = "證明：對所有 x≠0，e^x > 1 + x。"
PROOF_H5 = "令 g(x)=e^x-1-x，g'(x)=e^x-1。x>0 時 g'>0、x<0 時 g'<0，故 g 在 0 取唯一最小值 g(0)=0，x≠0 時 g(x)>0。"
STMT_M2 = "證明 cos x ≥ 1 - x²/2 對所有實數 x。"
PROOF_M2 = "令 g(x)=cos x-1+x²/2，g'(x)=-sin x+x，g''(x)=1-cos x≥0，故 g' 遞增且 g'(0)=0，g 在 0 取最小值 0。"
STMT_X4 = "設 Av₁=λ₁v₁、Av₂=λ₂v₂，λ₁≠λ₂，證明 v₁、v₂ 線性獨立。"
PROOF_X4 = "設 c₁v₁+c₂v₂=0，左乘 A 得 c₁λ₁v₁+c₂λ₂v₂=0；前式乘 λ₁ 相減得 c₂(λ₂-λ₁)v₂=0，因 λ₂≠λ₁ 且 v₂≠0 得 c₂=0，代回得 c₁=0。"

CASES = [
    # (id, statement, proof, reply, 應判 ok?)
    ("錯1-不等號反向", STMT_H5, PROOF_H5,
     "注意 x<0 時不等式會反向：e^x < 1+x。那 x>0 的情形你怎麼處理？", False),
    ("錯2-待證式寫錯", STMT_H5, PROOF_H5,
     "我們要證的是 e^x - 1 > 1 + x。先觀察 x=0 時兩邊相等，接著呢？", False),
    ("錯3-四階導數", STMT_M2, PROOF_M2,
     "Note that the fourth derivative of cos x is -cos x, which keeps the sign pattern. What does that give you?", False),
    ("錯4-係數錯誤", STMT_X4, PROOF_X4,
     "把 c₁v₁+c₂v₂=0 乘以 λ₁ 之後，你會得到 c₁λ₁²v₁+c₂λ₁v₂=0 嗎？", False),
    ("對1-正確引導", STMT_H5, PROOF_H5,
     "先看要證的不等式 e^x>1+x。若構造 g(x)=e^x-1-x，g 在 x=0 的值是多少？", True),
    ("對2-正確糾錯", STMT_M2, PROOF_M2,
     "邏輯很接近，但 g''(x)=1-cos x≥0 只給出 g' 遞增；為什麼還需要 g'(0)=0 才能定位最小值？", True),
    ("對3-正確英文", STMT_X4, PROOF_X4,
     "Left-multiplying by A gives c₁λ₁v₁+c₂λ₂v₂=0. What can you subtract to isolate one coefficient?", True),
]

print("[載入驗證器]", VER_MODEL, flush=True)
vtok = AutoTokenizer.from_pretrained(VER_MODEL)
ver = AutoModelForCausalLM.from_pretrained(VER_MODEL, device_map={"": 0}, dtype=torch.bfloat16)
ver.eval()

catch = miss = fp = 0
for cid, st, pf, reply, expect_ok in CASES:
    msgs = [{"role": "user", "content": VERIFY_PROMPT.format(statement=st, proof=pf, reply=reply)}]
    enc = vtok.apply_chat_template(msgs, add_generation_prompt=True,
                                   return_tensors="pt", return_dict=True).to(ver.device)
    with torch.no_grad():
        out = ver.generate(**enc, max_new_tokens=4096, do_sample=False,
                           pad_token_id=vtok.pad_token_id or vtok.eos_token_id)
    text = vtok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)
    text = text.split("</think>")[-1]
    m = re.search(r"\{.*\}", text, re.S)
    got_ok, err = True, None
    if m:
        for cand in (m.group(0), m.group(0).replace("\\", "\\\\")):
            try:
                obj = json.loads(cand)
                got_ok, err = bool(obj.get("ok", True)), obj.get("error")
                break
            except json.JSONDecodeError:
                continue
    verdict = "✓" if got_ok == expect_ok else "✗"
    print(f"{verdict} [{cid}] 預期 ok={expect_ok} → 判 ok={got_ok} {('| '+str(err)[:80]) if err else ''}",
          flush=True)
    if not expect_ok:
        catch += (not got_ok)
        miss += got_ok
    else:
        fp += (not got_ok)

print(f"\n抓錯 {catch}/4，漏抓 {miss}，誤殺 {fp}/3")
sys.exit(0 if (miss == 0 and fp == 0) else 1)
