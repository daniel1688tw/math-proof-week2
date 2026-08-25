# -*- coding: utf-8 -*-
"""auto_gate.py — 守門外圈：「產出 → 獨立評審 → 退件 → 自動修正 → 重評」迭代迴圈。

設計（2026-07-17，使用者規格）：
  * Rubric = regression_baseline.json ＋各評審 prompt 的逐項標準（既有）。
  * Grader = regression_suite.py（Claude headless，每次呼叫都是全新 context，
    看不到修正者的思路）——本腳本不改變評審，只把「退件 → 修正 → 重評」自動化。
  * 修正者 = claude CLI 一次呼叫：收到失敗指標＋評審 evidence，只准對
    dataset/tutor_driver.py 提出最小 old/new 文字替換；套用後必須通過
    test_driver_unit.py 與 --quick，否則整批還原、該輪作廢。
  * 配額韌性（Claude Pro 現實）：suite exit 2 = 評審不完整（限額打斷）→ 不算迭代、
    不觸發修正，存進度後退出；額度恢復後重跑本腳本 → 自動從 --rejudge 接續
    （生成已存檔，補評很便宜）。修正者呼叫失敗同樣存進度退出。

用法：
  python auto_gate.py --max-iters 3          # 迭代上限 3 輪
  python auto_gate.py                        # 續跑（讀 auto_gate_state.json）
  python auto_gate.py --reset                # 清除進度重來

退出碼：0=全過；1=迭代上限仍未過（或修正無法套用）；2=額度中斷（稍後續跑）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from regression_suite import (  # noqa: E402
    BASELINE, SCORE_DIR, claude_call, parse_json_obj)

STATE = HERE / "auto_gate_state.json"
EDITABLE = ["tutor_driver.py"]        # 修正者只准動的檔案（防護/指示層；訓練面修不了）
PY = sys.executable

FIX_PROMPT = """你是資深工程師，負責修一個蘇格拉底數學助教的推論端驅動程式。守門評估退件了，\
你要提出**最小**修正。只能修改 dataset/tutor_driver.py（防護規則、階段指示、regex、保底邏輯）；\
不能改評分標準、不能放寬守門、不能動訓練資料。

【退件的指標】
{failing}

【評審的具體 evidence（沒過的原因）】
{evidence}

【tutor_driver.py 現行完整內容】
{driver_src}

輸出格式：只輸出一個 JSON 物件，不要其他文字：
{{"edits": [{{"file": "tutor_driver.py", "old": "<被替換的原文字，必須逐字存在且唯一>",
"new": "<替換後文字>", "reason": "<一句話>"}}], "summary": "<這輪修了什麼，一句話>"}}
若你判斷這些失敗無法靠驅動程式層修復（例如需要重訓），輸出 {{"edits": [], "summary": "需要訓練面修復：<原因>"}}"""


def _load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"iteration": 0, "mode": "full", "history": []}


def _save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_suite(mode: str) -> int:
    cmd = [PY, str(HERE / "regression_suite.py")]
    if mode == "rejudge":
        cmd.append("--rejudge")
    print(f"\n━━ 執行守門（{mode}）━━")
    return subprocess.run(cmd, cwd=str(HERE.parent)).returncode


def _latest_scorecard() -> dict | None:
    cards = [p for p in SCORE_DIR.glob("*.json")
             if not p.stem.endswith(("_replies", "_dialogues", "_s4"))]
    if not cards:
        return None
    return json.loads(max(cards, key=lambda p: p.stat().st_mtime).read_text(encoding="utf-8"))


def _failing_and_evidence() -> tuple[str, str]:
    """從最新計分卡與基準找出退件指標，並蒐集評審 evidence（issue 評語）。"""
    from regression_suite import JUDGE_EPSILON, JUDGE_EPSILON_OVERRIDE
    base = json.loads(BASELINE.read_text(encoding="utf-8"))["metrics"]
    card = _latest_scorecard()
    metrics = card["metrics"] if card else {}
    failing = []
    for k, v in metrics.items():
        if k not in base:
            continue
        eps = 0.0
        if k.startswith("judge_"):
            eps = next((e for pre, e in JUDGE_EPSILON_OVERRIDE.items()
                        if k.startswith(pre)), JUDGE_EPSILON)
        if v < base[k] - eps:
            failing.append(f"{k}: 基準 {base[k]} → 本次 {v}")
    ev = []
    for pattern in ("*_dialogues.json", "*_s4.json"):
        files = sorted(SCORE_DIR.glob(pattern), key=lambda p: p.stat().st_mtime)
        if not files:
            continue
        for r in json.loads(files[-1].read_text(encoding="utf-8")):
            v = r.get("verdict") or {}
            issue = v.get("issue") or v.get("comment") or ""
            if issue:
                ev.append(f"[{r.get('id')}/{r.get('lang')}] {issue}")
    return "\n".join(failing) or "（無——可能是缺失型失敗）", "\n".join(ev) or "（無評語）"


def _apply_fix() -> str:
    """呼叫修正者並套用編輯。回傳 'fixed' / 'unfixable' / 'quota' / 'failed'。"""
    failing, evidence = _failing_and_evidence()
    print(f"\n━━ 退件內容 ━━\n{failing}\n\n━━ evidence ━━\n{evidence[:2000]}")
    driver = (HERE / "tutor_driver.py").read_text(encoding="utf-8")
    out = claude_call(FIX_PROMPT.format(
        failing=failing, evidence=evidence[:6000], driver_src=driver), timeout=600)
    if out is None:
        return "quota"
    plan = parse_json_obj(out)
    if not plan:
        print("（修正者輸出無法解析）")
        return "failed"
    edits = plan.get("edits", [])
    print(f"\n━━ 修正方案：{plan.get('summary', '')} ━━")
    if not edits:
        return "unfixable"
    backup = driver
    text = driver
    for e in edits:
        if e.get("file") not in EDITABLE:
            print(f"（拒絕：不准修改 {e.get('file')}）")
            return "failed"
        old = e.get("old", "")
        if text.count(old) != 1:
            print(f"（編輯定位失敗：old 出現 {text.count(old)} 次）")
            return "failed"
        text = text.replace(old, e["new"])
        print(f"  · {e.get('reason', '')}")
    (HERE / "tutor_driver.py").write_text(text, encoding="utf-8")
    # 驗證：單元測試 + quick 必須全過，否則還原
    for check in (["test_driver_unit.py"], ["test_review_workflow.py"],
                  ["regression_suite.py", "--quick"]):
        r = subprocess.run([PY, str(HERE / check[0])] + check[1:],
                           cwd=str(HERE.parent), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print(f"（{check[0]} 未過，整批還原）")
            (HERE / "tutor_driver.py").write_text(backup, encoding="utf-8")
            return "failed"
    subprocess.run(["git", "add", "dataset/tutor_driver.py"], cwd=str(HERE.parent))
    subprocess.run(["git", "commit", "-m",
                    f"auto-gate fix: {plan.get('summary', '')[:70]}"], cwd=str(HERE.parent))
    return "fixed"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-iters", type=int, default=3)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    if args.reset and STATE.exists():
        STATE.unlink()
    st = _load_state()

    while st["iteration"] < args.max_iters:
        rc = _run_suite(st["mode"])
        if rc == 0:
            print(f"\n✓ auto-gate 通過（第 {st['iteration'] + 1} 輪）")
            if STATE.exists():
                STATE.unlink()
            sys.exit(0)
        if rc == 2:                       # 評審不完整（限額）→ 不算迭代，存進度退出
            st["mode"] = "rejudge"
            _save_state(st)
            print("\n△ 額度中斷：進度已存，額度恢復後重跑 auto_gate.py 會從 --rejudge 接續")
            sys.exit(2)
        # rc == 1：真退件 → 修正
        st["history"].append({"iteration": st["iteration"], "result": "fail"})
        outcome = _apply_fix()
        if outcome == "quota":
            _save_state(st)
            print("\n△ 修正者呼叫因額度中斷：進度已存，稍後重跑接續")
            sys.exit(2)
        if outcome == "unfixable":
            _save_state(st)
            print("\n✗ 修正者判定需訓練面修復，停止自動迭代（交還人工）")
            sys.exit(1)
        if outcome == "failed":
            _save_state(st)
            print("\n✗ 修正無法安全套用，停止自動迭代（交還人工）")
            sys.exit(1)
        st["iteration"] += 1
        st["mode"] = "full"               # 修了 driver → 生成會變，必須完整重跑
        _save_state(st)
        print(f"\n（第 {st['iteration']} 輪修正完成，重新評估）")

    print(f"\n✗ 達迭代上限 {args.max_iters} 仍未通過")
    sys.exit(1)


if __name__ == "__main__":
    main()
