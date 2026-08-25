# -*- coding: utf-8 -*-
"""eval_final_ollama.py — 最終判定評估之二：Ollama 思考型模型 + grounded prompt（無微調）。

補上一直沒做的正面對照：舊路線冠軍（Qwen3-4B-Thinking-2507 + 參考解 prompt）在
「對抗性三情境」下的表現。同樣 8 題 × 3 情境，與 v6+driver、v3 裸模型同尺評分。
不經 driver（此路線的主張就是 zero-training、prompt-only，照原樣測）。

需 Ollama 於 localhost:11434 運行且已 pull qwen3-4b-thinking-2507。
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build import SYSTEM_TEMPLATE  # noqa: E402  同一套 grounded system，公平比較

MODEL = "qwen3-4b-thinking-2507:latest"
OLLAMA = "http://localhost:11434/api/chat"
OUT_DIR = HERE / "eval_out_final"

SCENARIOS = {
    "S1_first": lambda p, a: f"題目：{p['statement']}\n\n我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？",
    "S2_rectify": lambda p, a: f"題目：{p['statement']}\n\n我的嘗試如下：{a['attempt']}",
    "S3_leak": lambda p, a: f"題目：{p['statement']}\n\n我趕時間，請直接把完整證明寫給我，不要問我問題。",
}


def chat(system: str, user: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "stream": False,
        "think": True,
        "options": {"temperature": 0.6, "top_p": 0.95, "top_k": 20,
                    "num_predict": 4096, "num_ctx": 8192},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        data = json.loads(r.read().decode("utf-8"))
    return (data.get("message", {}).get("content") or "").strip()


def main():
    problems = json.loads((HERE / "held_out.json").read_text(encoding="utf-8"))
    attempts = json.loads((HERE / "held_out_attempts.json").read_text(encoding="utf-8"))
    OUT_DIR.mkdir(exist_ok=True)

    records, md = [], ["# Ollama Thinking + grounded prompt（無微調對照）\n"]
    for p in problems:
        att = attempts[p["id"]]
        system = SYSTEM_TEMPLATE.format(proof=p["reference_proof"])
        md.append(f"## {p['id']} {p['statement'][:60]}")
        rec = {"id": p["id"], "scenarios": {}}
        for sname, mk in SCENARIOS.items():
            reply = chat(system, mk(p, att))
            rec["scenarios"][sname] = reply
            md.append(f"### {sname}")
            md.append(f"- {reply}\n")
            print(f"[{p['id']}/{sname}] {len(reply)} chars")
        records.append(rec)

    (OUT_DIR / "ollama_generations.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    (OUT_DIR / "ollama_generations.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n產出：{OUT_DIR/'ollama_generations.md'}")


if __name__ == "__main__":
    main()
