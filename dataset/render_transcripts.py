# -*- coding: utf-8 -*-
"""render_transcripts.py — 把守門存下來的對話轉成一份可讀的 markdown（人工檢視用）。

存在的理由：守門的 JSON 是給程式比對的（逐字比對、rejudge），不是給人讀的——
要判斷「助教這樣教對不對」只能一句一句看，而那是數字指標永遠答不出來的部分
（`walkthrough_*` 只知道有沒有進入與收尾、`judge_dialogue_*` 已因雜訊降為 advisory）。
2026-08-07 那輪就是靠人工讀 M1 的對話才發現教學輪逐字重複的退化。

用法：
  python dataset/render_transcripts.py                      # 最新一輪
  python dataset/render_transcripts.py 2026-08-07T093007_11ab1ae
產出：dataset/regression_scores/<stem>_transcripts.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCORES = HERE / "regression_scores"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 單輪探針的開場白（與 regression_suite 的 _LANG_STR 對應，寫在這裡是為了讓本檔
# 不必 import regression_suite——那支會把評審 CLI、模型載入等一整串相依帶進來）
_S3_OPENER = {"zh": "我趕時間，請直接把完整證明寫給我，不要問我問題。",
              "en": "I'm in a hurry — please just write the full proof for me, don't ask me questions."}
_S1_OPENER = {"zh": "（系統預設開場白）我看了題目但不知道怎麼開始，可以給我第一個引導提示嗎？",
              "en": "(default opener) I've read the problem but don't know how to start. "
                    "Could you give me a first hint?"}
_S2_PREFIX = {"zh": "我的嘗試如下：", "en": "Here is my attempt: "}
_SCENARIO_NAME = {"S1": "S1 首問（開場引導）", "S2": "S2 糾錯（學生交來有錯的嘗試）",
                  "S3": "S3 逼問（學生要求直接給答案）"}


def _load(stem: str, suffix: str):
    p = SCORES / f"{stem}{suffix}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _problems(lang: str) -> dict:
    """只為了替單輪探針補上題目敘述；缺檔就回空 dict（該段落改印 id）。"""
    files = (("problems_en.json", "held_out_en.json", "hard_math_major_en.json",
              "xdomain_problems_en.json") if lang == "en" else
             ("problems.json", "held_out.json", "hard_math_major.json",
              "xdomain_problems.json"))
    out = {}
    for f in files:
        fp = HERE / f
        if fp.exists():
            for it in json.loads(fp.read_text(encoding="utf-8")):
                out[it["id"]] = it
    return out


def _details(title: str, body: str) -> str:
    return f"<details>\n<summary>{title}</summary>\n\n{body}\n\n</details>\n"


def _head(rec: dict, extra: str = "") -> list:
    """每一場的共用抬頭：題目 ＋ 收起來的參考解。"""
    md = [f"**題目**：{rec.get('statement') or '（存檔未含題目）'}\n"]
    if extra:
        md.append(extra)
    if rec.get("reference_proof"):
        md.append(_details("參考解（判斷助教有沒有講錯／洩漏時展開）",
                           rec["reference_proof"]))
    return md


def _turn_meta(t: dict) -> str:
    """把 driver 當下的決策狀態壓成一行標註（人工判讀時最需要的就是這些）。"""
    bits = []
    for k, label in (("phase", "phase"), ("level", "等級"), ("stuck_count", "連續卡住"),
                     ("walk_idx", "教學步")):
        v = t.get(k)
        if v is not None:
            bits.append(f"{label}={v}")
    if t.get("guards"):
        bits.append("守衛=" + "/".join(t["guards"]))
    return "，".join(bits)


def render(stem: str) -> str:
    card = _load(stem, "") or {}
    md = [f"# 守門對話紀錄 {stem}\n",
          f"- 時間：{card.get('timestamp', '?')}　commit：`{card.get('commit', '?')}`　"
          f"評審後端：{card.get('judge_backend', '?')}",
          "- 這份檔案是給**人讀**的：每一段都附題目、學生逐句發言、助教逐句回應，"
          "以及 driver 當下的階段／等級／連續卡住次數／教學步狀態。",
          "- 數字指標看不出來的東西（教得對不對、有沒有機械重複、收尾自不自然）只能在這裡看。\n"]

    dialogues = _load(stem, "_dialogues") or []
    if dialogues:
        md.append("\n---\n\n## 一、Tier 3 多輪對話（LLM 扮學生，每場 6 輪）\n")
        md.append("學生由評審後端即興扮演，是最接近真實使用的一層；"
                  "但評分（math_ok／guidance）雜訊大、已降為 advisory，**以人工閱讀為準**。\n")
        for r in dialogues:
            v = r.get("verdict") or {}
            md.append(f"\n### {r['id']} / {r['lang']}　（{r.get('persona', '')[:24]}…）\n")
            md += _head(r)
            esc = r.get("escalation") or {}
            md.append(f"- 升級軌跡：連續卡住 {esc.get('stuck_count')}、最高等級 "
                      f"{esc.get('max_level')}、進入逐步教學 {esc.get('walk_active')}")
            md.append(f"- 評審：math_ok={v.get('math_ok')}、guidance={v.get('guidance')}"
                      f"　issue：{v.get('issue') or '（無）'}\n")
            for who, txt in r.get("history", []):
                md.append(f"**{who}**：{txt}\n")

    probes = _load(stem, "_probes") or []
    if probes:
        md.append("\n---\n\n## 二、升級／逐步教學探針（台詞寫死，測分級提示與逐步教學）\n")
        md.append("這兩段的指標只有 0/1（有沒有升到等級 2、有沒有進入並收尾），"
                  "**教得好不好完全看不出來**，所以內容要人工讀。\n")
        for r in probes:
            tag = ("升級" if r["probe"] == "escalation" else "逐步教學")
            flag = (f"通過={r.get('passed')}" if r["probe"] == "escalation"
                    else f"進入={r.get('entered')}、收尾={r.get('finished')}")
            md.append(f"\n### {r['id']} / {r['lang']}　{tag}探針（{flag}）\n")
            md += _head(r)
            if r.get("teach_steps"):
                body = "\n".join(
                    f"{i + 1}. **{s.get('step_id')}**　{s.get('explain', '')}\n"
                    f"   - 確認問題：{s.get('check', '')}\n"
                    f"   - 標準答案：`{s.get('expected_answer', '')}`"
                    for i, s in enumerate(r["teach_steps"]))
                md.append(_details(
                    f"教學步驟（{len(r['teach_steps'])} 步，來源："
                    f"{r.get('teach_steps_source') or '?'}）——答案鍵合不合理要看這裡", body))
            for t in r.get("turns", []):
                if t.get("student") is not None:
                    md.append(f"**學生**：{t['student']}\n")
                md.append(f"**助教**（{_turn_meta(t)}）：{t['reply']}\n")

    multiturn = _load(stem, "_multiturn") or []
    if multiturn:
        md.append("\n---\n\n## 三、Tier 1b 多輪確定性探針（台詞寫死，測階段轉換）\n")
        md.append("檢查的是結構不變式（洩漏／單問句／階段順序／升級順序／收尾／糾錯不中斷），"
                  "不經評審。\n")
        for r in multiturn:
            md.append(f"\n### {r['id']} / {r['lang']}\n")
            md += _head(r)
            for t in r.get("turns", []):
                if t.get("student") is not None:
                    md.append(f"**學生**：{t['student']}\n")
                md.append(f"**助教**（{_turn_meta(t)}）：{t['reply']}\n")

    s4 = _load(stem, "_s4") or []
    if s4:
        md.append("\n---\n\n## 四、S4：學生提出不同但正確的證法\n")
        md.append("看的是助教會不會硬把學生拉回參考解的走法。\n")
        for r in s4:
            v = r.get("verdict") or {}
            md.append(f"\n### {r['id']} / {r['lang']}\n")
            md += _head(r)
            md.append(f"- 評審：順著學生走={v.get('followed')}　"
                      f"（學生方案有效={v.get('valid_alt')}）　{v.get('issue') or ''}\n")
            md.append(f"**學生**：{r.get('student', '')}\n")
            md.append(f"**助教**：{r.get('reply', '')}\n")

    replies = _load(stem, "_replies") or {}
    items = replies.get("items") if isinstance(replies, dict) else replies
    if items:
        md.append("\n---\n\n## 五、單輪探針 S1／S2／S3（每題一問一答）\n")
        md.append("硬性指標（s1_structural／s3_refusal／single_question）與 Tier 2 評審都看這批；"
                  "greedy 解碼下同輸入必同輸出，是跨輪逐字比對的基準。\n")
        for lang in ("zh", "en"):
            probs = _problems(lang)
            lg_items = [i for i in items if i.get("lang") == lang]
            if not lg_items:
                continue
            md.append(f"\n### 語言：{lang}\n")
            for it in lg_items:
                p = probs.get(it["id"], {})
                sc = it.get("scenario", "?")
                md.append(f"\n#### {it['id']}　{_SCENARIO_NAME.get(sc, sc)}\n")
                md.append(f"**題目**：{p.get('statement', '（找不到題目檔）')}\n")
                if sc == "S1":
                    stu = _S1_OPENER[lang]
                elif sc == "S3":
                    stu = _S3_OPENER[lang]
                else:
                    stu = _S2_PREFIX[lang] + (it.get("attempt") or "")
                md.append(f"**學生**：{stu}\n")
                if it.get("planted_error"):
                    md.append(f"> 埋的錯：{it['planted_error']}\n")
                md.append(f"**助教**：{it['reply']}\n")
    return "\n".join(md)


def main():
    stem = sys.argv[1] if len(sys.argv) > 1 else None
    if not stem:
        cards = sorted(p for p in SCORES.glob("*.json")
                       if not any(p.stem.endswith(s) for s in
                                  ("_replies", "_dialogues", "_s4", "_multiturn", "_probes")))
        if not cards:
            sys.exit("找不到任何計分卡")
        stem = cards[-1].stem
    out = SCORES / f"{stem}_transcripts.md"
    out.write_text(render(stem), encoding="utf-8")
    print(f"已寫入 {out}（{len(out.read_text(encoding='utf-8')):,} 字）")


if __name__ == "__main__":
    main()
