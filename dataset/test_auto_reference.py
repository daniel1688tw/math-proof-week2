# -*- coding: utf-8 -*-
"""test_auto_reference.py — 備課管線盲測（需 Ollama，不需 GPU/HF 模型）。

對 10 題「已有手寫參考解」的題目盲跑管線（不給手寫解），量測：
  1. verified 率：管線敢背書的比例（低不是壞事，代表誠實）
  2. verified 正確率：敢背書的裡面有多少真的對（安全關鍵，人工核對用）
產出 eval_out_xdomain/auto_reference_blind.md/.jsonl（逐題含完整自動解供人工核對）。
每題完成即增量寫檔，中斷不丟進度。
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from auto_reference import build_reference  # noqa: E402
from review_backstop import available  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT_MD = HERE / "eval_out_xdomain" / "auto_reference_blind.md"
OUT_JL = HERE / "eval_out_xdomain" / "auto_reference_blind.jsonl"

if not available():
    print("Ollama 未在線，無法盲測")
    sys.exit(0)

pools = {}
for fname in ("held_out.json", "hard_math_major.json", "xdomain_problems.json"):
    for p in json.loads((HERE / fname).read_text(encoding="utf-8")):
        pools[p["id"]] = p

# 10 題：簡單→難、分析→離散/線代都覆蓋（M4 Darboux 是已知最難）
PICKS = ["H1", "H3", "H5", "H7", "M1", "M2", "M4", "M5", "X4", "X6"]

records = []
md = ["# 備課管線盲測（不給手寫解，管線自證＋自驗）\n"]
for pid in PICKS:
    p = pools[pid]
    print(f"\n===== {pid}：{p['statement'][:50]}… =====")
    t0 = time.time()
    result = build_reference(p["statement"])
    elapsed = round(time.time() - t0, 1)
    rec = {"id": pid, "status": result["status"], "elapsed_s": elapsed,
           "log": result["log"]}
    md.append(f"## {pid}（{result['status']}，{elapsed}s）")
    md.append(f"> {p['statement']}\n")
    if result["status"] == "verified":
        rec["auto_proof"] = result["reference_proof"]
        rec["teach_steps"] = result["teach_steps"]
        md.append("### 自動參考解（人工核對正確性）")
        md.append(result["reference_proof"])
        md.append(f"\n### 教學步驟（{len(result['teach_steps'])} 步）")
        for i, s in enumerate(result["teach_steps"], 1):
            md.append(f"{i}. {s['explain']}（確認：{s['check']}）")
    else:
        md.append("（管線拒絕背書 → 部署時走同學模式）")
    md.append("")
    records.append(rec)
    OUT_JL.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records),
                      encoding="utf-8")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"[{pid}] {result['status']}（{elapsed}s）已增量寫檔")

n_ver = sum(1 for r in records if r["status"] == "verified")
md.append(f"\n---\n**verified 率：{n_ver}/{len(records)}**；verified 正確率待人工核對。")
OUT_MD.write_text("\n".join(md), encoding="utf-8")
print(f"\n完成：verified {n_ver}/{len(records)}，報告 {OUT_MD}")
