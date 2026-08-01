# -*- coding: utf-8 -*-
"""test_phase_routing.py — 用**真實模型輸出**回放驗證確定性階段路由（無 GPU、無 Ollama）。

為什麼需要這支（與 test_driver_unit.py 的分工）：
  test_driver_unit.py 的每一句助教／學生台詞都是人寫的。它能證明「狀態機邏輯正確」，
  但證明不了「真模型實際講出來的話會不會踩中這些正則」——收尾偵測、交稿請求偵測、
  完成宣告偵測全都是在比對散文，而散文正是最容易估錯的東西
  （update.md 稽核 F1 就是實測 8 種自然措辭只命中 2 種）。

做法：把 dataset/regression_scores/*_dialogues.json 裡歷次守門留下的真實對話
（學生由 Gemini/Claude 即興扮演、助教由 v9 生成）逐則回放進 TutorDriver 的確定性層，
本輪助教回覆改由存檔指定（重生成亦回同一則），於是狀態轉移就是「真實措辭下的轉移」。
接著檢查一組不變式。存檔隨每輪守門累積，語料只會愈來愈多。

⚠️ 已知語料偏差（2026-08-01 量測，243 場 / 1582 輪）：
    phase=None 1210、review 134、rectify 134、closed 83、writeup_request 18、refuse_leak 3，
    **hint ladder 從未被消耗（max ladder_idx = 0）**。Tier 3 的「學生」太會答，
    不會用 is_stuck 認得出的方式卡住，所以分級提示→逐步教學那整條升級路徑
    這份語料完全沒有覆蓋——那部分只能靠 test_driver_unit.py 的構造式案例守。
    本檔末會印出覆蓋報告，別把「這裡全綠」誤讀成「全部路徑都測過了」。
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys
from pathlib import Path

os.environ["REVIEW_BACKSTOP"] = "0"      # 純邏輯回放不打審閱後盾

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tutor_driver import (  # noqa: E402
    TutorDriver, confirms_whole_proof_done, load_problems_with_ladders,
    _NOT_DONE_RE, _QMARK_RE, _STEP_SCOPE_RE, _TUTOR_DONE_RE,
)


def _declares_completion(text: str) -> bool:
    """回覆是否宣告了整份證明完成（不含 confirms_whole_proof_done 的『無問句』那道閘）。

    要單獨定義，是因為 confirms_whole_proof_done 本身就排除帶問句的回覆——拿它去檢查
    「宣告完成卻又帶問句」會是一條永遠不可能觸發的空不變式。"""
    return bool(text and _TUTOR_DONE_RE.search(text)
                and not _NOT_DONE_RE.search(text)
                and not _STEP_SCOPE_RE.search(text))

FAIL: list = []


def check(name, cond):
    print(("  ✓ " if cond else "  ✗ ") + name)
    if not cond:
        FAIL.append(name)


# ── 題庫（對話題號含 xdomain 的 X 系列）──────────────────────────────────────
PROBLEMS = load_problems_with_ladders()
for _fn in ("xdomain_problems.json", "adv_test_problem.json"):
    _p = HERE / _fn
    if _p.exists():
        _data = json.loads(_p.read_text(encoding="utf-8"))
        for _it in (_data if isinstance(_data, list) else [_data]):
            PROBLEMS.setdefault(_it["id"], _it)


class _StubModel:
    device = "cpu"


class _ReplayDriver(TutorDriver):
    """回放：本輪助教回覆由存檔指定；重生成也回同一則。

    重生成回同一則是刻意的——我們要重現的是「當時那句話造成的狀態轉移」，
    不是去猜模型被加強約束後會改講什麼。"""

    def _raw_generate(self, msgs, max_new):
        self.sys_seen.append(msgs[0]["content"])
        return self.cur


def _hint_injected(sys_txt: str) -> bool:
    """該輪 system 是否真的把等級 2 的提示內容送進去了。"""
    return "提示內容：" in sys_txt or "\nHint:" in sys_txt


def replay(rec: dict):
    """回放一場對話，回傳 (driver, 每輪快照)。history = [["助教"|"學生", 內容], …]。"""
    d = _ReplayDriver(tok=None, model=_StubModel(), problem=PROBLEMS[rec["id"]])
    d.sys_seen, d.cur = [], ""
    hist = rec["history"]
    snaps = []

    def snap(student: str | None):
        log = d.state["turns"][-1]
        snaps.append(dict(
            student=student,
            reply=d.messages[-1]["content"] if d.messages else "",
            phase=d.state.get("phase"),
            hint=any(_hint_injected(s) for s in d.sys_seen),
            ladder=d.state["ladder_idx"],
            guards=list(log.guards),
            level=log.level,
            done=bool(d.state.get("done_closed")),
            writeup_asked=bool(d.state.get("writeup_asked")),
        ))

    d.cur = hist[0][1]
    d.sys_seen.clear()
    d.start()
    snap(None)
    i = 1
    while i < len(hist):
        who, content = hist[i]
        if who != "學生":
            i += 1
            continue
        d.cur = hist[i + 1][1] if i + 1 < len(hist) else "（存檔在此結束）"
        d.sys_seen.clear()
        d.step(content)
        snap(content)
        i += 2
    return d, snaps


def load_corpus():
    out = []
    for f in sorted(glob.glob(str(HERE / "regression_scores" / "*_dialogues.json"))):
        for rec in json.loads(Path(f).read_text(encoding="utf-8")):
            if rec.get("id") in PROBLEMS and rec.get("history"):
                out.append((Path(f).name, rec))
    return out


CORPUS = load_corpus()
print(f"[回放語料] {len(CORPUS)} 場真實守門對話"
      f"（{len({f for f, _ in CORPUS})} 輪守門存檔）")

# ── 不變式 ────────────────────────────────────────────────────────────────
# 每條都是「契約」而非「重述實作」：違反代表使用者真的會看到壞行為。
V1: list = []   # 提示梯守恆
V2: list = []   # 收尾後仍補通用追問句
V3: list = []   # done_closed 沒有可指認的來源
V4: list = []   # 助教還在提問卻宣告收尾
V5: list = []   # 已請學生交稿後，長草稿反而被要求重寫

for fname, rec in CORPUS:
    d, snaps = replay(rec)
    tag = f"{fname[:24]} {rec['id']}/{rec.get('lang', 'zh')}"

    # V1：ladder_idx 的總增量必須等於「真的把提示送出去」的輪數。
    #     階段指示優先於等級指示，phase 有值時 system 裡沒有提示內容——此時推進
    #     ladder_idx 等於把沒給出去的提示記為已用，還會讓 walkthrough 提早觸發。
    shown = sum(1 for s in snaps if s["hint"])
    if d.state["ladder_idx"] != shown:
        V1.append(f"{tag}: ladder_idx={d.state['ladder_idx']} 但實際給出提示 {shown} 次")

    armed_at = None
    for idx, s in enumerate(snaps):
        reply = s["reply"]
        # V2：證明已確認完成後還被追問「下一步該從哪裡下手」是最突兀的扣分項。
        if armed_at is not None and "fallback" in s["guards"]:
            V2.append(f"{tag}: 第 {armed_at} 輪收尾，第 {idx} 輪仍補追問句")
        # V4：driver 不得在「已宣告整份完成」的回覆後面自己再補上問句（#17 時序缺口：
        #     arm 發生在補句之前，補句若照樣加上去，學生看到的就是
        #     「證明到此完成。…那你覺得，下一步該從哪裡下手？」）。
        #     只追究 driver 補的（fallback／writeup_nudge）——存檔裡模型當年自己多講
        #     的那一句是模型行為，不是這一層的契約，不該由本檔判定。
        if ("fallback" in s["guards"] or "writeup_nudge" in s["guards"]) \
                and _declares_completion(reply):
            V4.append(f"{tag}: 第 {idx} 輪宣告完成，driver 仍補問句 → {reply[-40:]}")
        if s["done"] and armed_at is None:
            armed_at = idx
            # V3：arm 必須來自可指認的來源——審閱通過（review 輪且回覆無問句）
            #     或助教親口宣告完成。兩者皆非就是誤判收尾（會中斷糾錯，稽核 F3）。
            by_review = s["phase"] == "review" and not _QMARK_RE.search(reply)
            if not (by_review or confirms_whole_proof_done(reply)):
                V3.append(f"{tag}: 第 {idx} 輪 arm done_closed 但"
                          f"phase={s['phase']}、回覆未宣告完成 → {reply[:60]}")

    # V5：已請學生交稿後，他交出的長草稿必須進審閱，不可被 writeup 保底叫他重寫
    #     剛寫完的證明（弱點 #7 的 H5 型 bug）。
    asked = False
    for s in snaps:
        if asked and s["student"] and len(s["student"].strip()) >= 120 \
                and s["phase"] == "writeup_request":
            V5.append(f"{tag}: 交稿後的 {len(s['student'])} 字草稿又被要求重寫")
        asked = asked or s["writeup_asked"]

print("\n[不變式] 真實對話回放")
check(f"V1 提示梯守恆（提示沒送出去就不得計為已用）：違反 {len(V1)}", not V1)
check(f"V2 收尾後不再補通用追問句：違反 {len(V2)}", not V2)
check(f"V3 done_closed 皆有可指認來源（審閱通過／親口宣告）：違反 {len(V3)}", not V3)
check(f"V4 宣告完成後 driver 不得自己再補問句：違反 {len(V4)}", not V4)
check(f"V5 交稿後的長草稿不得被要求重寫：違反 {len(V5)}", not V5)
for lst in (V1, V2, V3, V4, V5):
    for line in lst[:5]:
        print("      · " + line)

# ── 覆蓋報告（避免把「全綠」誤讀成「全部路徑都測過」）──────────────────────
cov = collections.Counter()
max_ladder = 0
for _, rec in CORPUS:
    d, snaps = replay(rec)
    for s in snaps:
        cov[str(s["phase"])] += 1
        cov["_等級2提示輪"] += 1 if s["hint"] else 0
    max_ladder = max(max_ladder, d.state["ladder_idx"])

print("\n[覆蓋報告] 這份語料實際走到的階段（總輪數 "
      f"{sum(v for k, v in cov.items() if not k.startswith('_'))}）")
for k, v in sorted(cov.items(), key=lambda kv: -kv[1]):
    if not k.startswith("_"):
        print(f"    phase={k:16s} {v:5d} 輪")
print(f"    等級 2 提示輪 {cov['_等級2提示輪']} 次；ladder_idx 最大值 {max_ladder}")
if max_ladder == 0:
    print("    ⚠️ 本語料未覆蓋分級提示／逐步教學升級路徑"
          "（Tier 3 的學生太會答，不會用 is_stuck 認得出的方式卡住）。"
          "該路徑由 test_driver_unit.py 的構造式案例把關。")

print()
if FAIL:
    print(f"✗ {len(FAIL)} 項失敗：{FAIL}")
    sys.exit(1)
print("全部階段路由回放測試通過 ✓")
