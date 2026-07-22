# -*- coding: utf-8 -*-
"""Antigravity CLI（agy）評審穩定性壓測（JUDGE_BACKEND_MIGRATION_PLAN.md §四步驟2）。
連續呼叫貼近實際 Tier2/Tier3 評審格式的 prompt，量測 JSON 可解析率與逾時/hang 發生率。
只讀寫本機，不影響現行 Claude 評審流程；不通過就不接進 regression_suite.py。"""
import json
import os
import re
import subprocess
import time

AGY = os.path.join(os.environ.get("LOCALAPPDATA", ""), "agy", "bin", "agy.exe")
AGY_MODEL = os.environ.get("AGY_MODEL", "Gemini 3.1 Pro (High)")
TIMEOUT_S = 60
N_CALLS = 25

# 貼近 JUDGE_ITEM_PROMPT 的實際格式（單題 S1/S2/S3 評審）
PROMPT_TMPL = """你是嚴格的數學教學評審。

【題目】證明 lim_{{n→∞}} n^(1/n) = 1。
【參考解（正確）】設 a_n = n^(1/n) - 1 ≥ 0，展開 n=(1+a_n)^n 取二項式第二項當下界，
得 a_n² ≤ 2/(n-1)，由夾擠定理 a_n→0，故極限為 1。

【S1 情境】學生請求第一個提示
【S1 助教回覆】案例編號 {i}：先觀察 n^(1/n) 和 1 的大小關係，你能設一個非負的量代表它們的差距嗎？

對這則回覆判定：
- math_ok：回覆中所有數學陳述是否全部正確
- reveal_ok：透露拿捏是否恰當
- score：引導品質 1-5
- issue：一句話說明扣分或錯誤處（沒有就空字串）

只輸出一個 JSON 物件，格式：
{{"S1": {{"math_ok": true, "reveal_ok": true, "score": 4, "issue": ""}}}}
不要輸出任何其他文字。"""

_JSON_RE = re.compile(r"\{.*\}", re.S)


def call_agy(prompt: str):
    t0 = time.time()
    try:
        r = subprocess.run([AGY, "--model", AGY_MODEL, "-p", prompt,
                            "--print-timeout", f"{TIMEOUT_S}s"],
                            capture_output=True, text=True, encoding="utf-8",
                            timeout=TIMEOUT_S + 15)
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT", time.time() - t0
    dt = time.time() - t0
    if r.returncode != 0:
        return None, f"EXIT{r.returncode}:{r.stderr[:120]}", dt
    m = _JSON_RE.search(r.stdout)
    if not m:
        return None, f"NO_JSON:{r.stdout[:120]!r}", dt
    try:
        obj = json.loads(m.group(0))
        return obj, None, dt
    except json.JSONDecodeError as e:
        return None, f"BAD_JSON:{e}", dt


def main():
    if not os.path.exists(AGY):
        print(f"[FATAL] agy.exe 不存在：{AGY}")
        return 1
    ok = 0
    fails = []
    times = []
    for i in range(1, N_CALLS + 1):
        obj, err, dt = call_agy(PROMPT_TMPL.format(i=i))
        times.append(dt)
        if obj and isinstance(obj.get("S1"), dict) and "math_ok" in obj["S1"]:
            ok += 1
            print(f"  [{i:2d}] OK  {dt:5.1f}s")
        else:
            fails.append((i, err))
            print(f"  [{i:2d}] FAIL {dt:5.1f}s  {err}")
    print(f"\n可解析率: {ok}/{N_CALLS} = {ok/N_CALLS:.1%}")
    print(f"平均延遲: {sum(times)/len(times):.1f}s  最大延遲: {max(times):.1f}s")
    if fails:
        print(f"失敗案例: {fails}")
    print(f"\n判定門檻：可解析率 ≥99%、零 hang/timeout → 通過")
    timeouts = sum(1 for _, e in fails if e == "TIMEOUT")
    passed = (ok / N_CALLS) >= 0.99 and timeouts == 0
    print("✓ 通過，可考慮接入" if passed else "✗ 未通過，暫不接入")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
