"""score_replies.py — 彙整所有 backend 的回覆，做 form + LLM judge 評分與對比。

improve.md 問題①②⑨：
  * 讀 eval_out/replies_*.json（base / finetuned / ollama_socratic / grounded，存在哪些就比哪些）。
  * form 分（零成本，已在回覆裡）＋ LLM judge 分（教學品質，問題②）。
  * held-out（泛化，主指標）與 seed（記憶 sanity）**分開報告**（問題①）。

judge 需要 Ollama 與參考解（eval_out/reference_solutions.json）。
請在 transformers 不常駐時跑（避免搶顯存）。

執行：
  conda run -n lora_project --live-stream python score_replies.py
"""

from __future__ import annotations

import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import eval_judge
import ollama_client as oc
from eval_common import OUT_DIR, load_reference_solutions, load_replies

BACKENDS = ["base", "finetuned", "ollama_socratic", "grounded"]
SCORES_PATH = os.path.join(OUT_DIR, "scores.json")


def _present_backends() -> list[str]:
    return [b for b in BACKENDS if load_replies(b)]


def main() -> None:
    backends = _present_backends()
    if not backends:
        print("[錯誤] eval_out/ 沒有任何 replies_*.json。請先跑 compare.py / gen_ollama_replies.py。")
        sys.exit(1)

    refs = load_reference_solutions()
    do_judge = oc.health_check()
    if not do_judge:
        print("[警告] Ollama 未啟動 → 只算 form 分，跳過 LLM judge（教學品質）。")
    elif not refs:
        print("[警告] 無 reference_solutions.json → judge 缺參考解，正確性判斷會較弱。")

    all_scores: dict = {}
    print(f"\n要評分的 backends：{backends}")
    for b in backends:
        rows = load_replies(b)
        print(f"\n── judge backend: {b}（{len(rows)} 題）──")
        scored = []
        for i, r in enumerate(rows, 1):
            entry = {"id": r["id"], "split": r["split"], "form": r["form"]["total"]}
            if do_judge:
                ref = refs.get(r["id"], {}).get("proof", "")
                j = eval_judge.judge_reply(r["problem"], ref, r["reply"])
                entry["judge"] = j["total"]
                entry["judge_detail"] = j
                print(f"  [{i}/{len(rows)}] {r['id']:<34} form {r['form']['total']}/5  judge {j['total']}/10")
            else:
                entry["judge"] = None
            scored.append(entry)
        all_scores[b] = scored

    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump(all_scores, open(SCORES_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # ── 對比表 ──────────────────────────────────────────────────────────────────
    def avg(b, split, key):
        rows = [r for r in all_scores[b] if r["split"] == split and r.get(key) is not None]
        return (sum(r[key] for r in rows) / len(rows)) if rows else float("nan")

    print("\n" + "=" * 78)
    print("  對比（held-out = 泛化主指標；seed = 記憶 sanity）")
    print("=" * 78)
    header = f"  {'backend':<18}{'form(H)':>9}{'judge(H)':>10}{'form(s)':>9}{'judge(s)':>10}"
    print(header)
    print("  " + "-" * 74)
    for b in backends:
        fh, jh = avg(b, "held", "form"), avg(b, "held", "judge")
        fs, js = avg(b, "seed", "form"), avg(b, "seed", "judge")
        def fmt(x):
            return f"{x:.2f}" if x == x else "  -"
        print(f"  {b:<18}{fmt(fh):>9}{fmt(jh):>10}{fmt(fs):>9}{fmt(js):>10}")

    print(f"\n  詳細分數 → {SCORES_PATH}")
    print("  解讀：看 held-out 的 judge 分（教學品質+正確性）；form 只是 sanity。")
    print("        若 grounded > finetuned > ollama_socratic > base，代表方向正確；")
    print("        若 finetuned 在 seed 高、held-out 沒贏 base，代表只是背了種子。\n")


if __name__ == "__main__":
    main()
