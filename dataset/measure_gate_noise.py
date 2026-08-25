# -*- coding: utf-8 -*-
"""measure_gate_noise.py — 量測守門指標自身的雜訊，判斷 ε 是否夠寬、基準是否設在幸運高點。

動機（2026-08-02）：judge_backstop 在同一組**寫死的輸入**下連跑三次得到
0.3333 / 0.6667 / 0.0，卻是硬性指標且 ε=0.05——守門因此誤判退步。事後才發現
judge_s2_catch_zh 的實測極差 0.0824 也已超過它的 ε 0.08，只是還沒被抽中。
與其等下次誤殺，不如把「這個指標的雜訊有多大」變成可以隨時重跑的量測。

核心方法：找出 **Tier 1/2 回覆逐字相同** 的幾輪守門。回覆相同 ⇒ 生成端沒有變化，
於是 judge_* 的差異**全部**來自評審自身的不確定性。在這組輪次上算極差，就是該指標
的雜訊下界；ε 必須大於它，否則守門會在沒有任何真實退步時判退。

用法：
  python dataset/measure_gate_noise.py            # 自動挑最近一組回覆相同的輪次
  python dataset/measure_gate_noise.py --all      # 不篩選，用全部有計分卡的輪次
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _load_cfg():
    """從 regression_suite 取現行的 ε 設定與 advisory 清單（避免兩邊各寫一份而走樣）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("rs", HERE / "regression_suite.py")
    rs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rs)
    return rs.JUDGE_EPSILON, rs.JUDGE_EPSILON_OVERRIDE, rs.ADVISORY_METRICS, rs.BASELINE


def eps_for(metric: str, default: float, override: dict) -> float:
    return next((v for pre, v in override.items() if metric.startswith(pre)), default)


def scorecards() -> list[tuple[str, dict, list | None]]:
    """(stem, metrics, replies) 依時間排序；replies 為 None 表示該輪沒有回覆存檔。"""
    out = []
    for f in sorted(glob.glob(str(HERE / "regression_scores" / "*.json"))):
        p = Path(f)
        if any(s in p.stem for s in ("_dialogues", "_replies", "_s4")):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        mets = data.get("metrics")
        if not mets or "judge_math_ok_zh" not in mets:
            continue          # 只看完整輪（--quick 的計分卡只有 tier0）
        rp = p.with_name(p.stem + "_replies.json")
        replies = None
        if rp.exists():
            items = json.loads(rp.read_text(encoding="utf-8")).get("items", [])
            replies = {(i["id"], i.get("lang", "zh"), i["scenario"]): i["reply"] for i in items}
        # 後端（裁判）必須一致才能比：不同裁判的尺不可互比，所以基準檔本身也是分開的。
        # 2026-07-22 前的計分卡沒有 judge_backend 欄位，那時只有 claude 一種。
        backend = data.get("judge_backend", "claude")
        out.append((p.stem, mets, replies, backend))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="不篩選回覆相同的輪次")
    args = ap.parse_args()

    default_eps, override, advisory, baseline_path = _load_cfg()
    cards = scorecards()
    if len(cards) < 2:
        print("完整輪計分卡不足 2 份，無法量測雜訊。")
        return

    newest = next((c for c in reversed(cards) if c[2]), None)
    if not newest:
        print("找不到帶回覆存檔的輪次。")
        return
    backend = newest[3]
    if args.all:
        group = [c for c in cards if c[3] == backend]
        note = f"後端 {backend} 的全部完整輪（含生成端變化，雜訊會被高估）"
    else:
        # 「回覆逐字相同」⇒ 生成端沒變；「同一後端」⇒ 裁判的尺沒變。
        # 兩者同時成立，指標的差異才是純粹的評審不確定性。
        group = [c for c in cards if c[2] and c[2] == newest[2] and c[3] == backend]
        note = (f"Tier 1/2 回覆與 {newest[0][-7:]} 逐字相同、且同為 {backend} 後端"
                f"（隔離純評審雜訊）")

    print(f"[樣本] {len(group)} 輪：{note}")
    for s, _, _, _ in group:
        print(f"    {s}")
    if len(group) < 2:
        print("\n同輸入輪次不足 2 份，無法算極差。先累積更多守門輪次。")
        return

    base = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    base = base.get("metrics", base)

    vals: dict[str, list] = {}
    for _, mets, _, _ in group:
        for k, v in mets.items():
            if isinstance(v, (int, float)):
                vals.setdefault(k, []).append(v)

    print(f"\n{'指標':32s} {'極差':>7s} {'ε':>6s}  {'基準':>7s} {'分位':>6s}  判定")
    problems = []
    for k in sorted(vals):
        vs = vals[k]
        if len(vs) < 2 or not k.startswith("judge_"):
            continue
        lo, hi = min(vs), max(vs)
        rng = hi - lo
        adv = any(k.startswith(p) for p in advisory)
        e = eps_for(k, default_eps, override)
        b = base.get(k)
        pos = "-" if b is None or hi == lo else f"{(b - lo) / (hi - lo):5.0%}"
        if adv:
            verdict = "advisory"
        elif rng >= e:
            verdict = "⚠️ 雜訊 ≥ ε：會誤殺"
            problems.append((k, rng, e))
        elif rng > e * 0.8:
            verdict = "⚠ 雜訊已達 ε 的 80%"
        else:
            verdict = "ok"
        bs = f"{b:7.4f}" if b is not None else "      -"
        print(f"{k:32s} {rng:7.4f} {e:6.2f}  {bs} {pos:>6s}  {verdict}")

    print("\n[基準位置] 分位＝基準落在實測分佈的哪裡。>70% 代表基準設在幸運高點，"
          "正常跑分就會低於它（弱點 #7）。")
    if problems:
        print("\n[需處置] 以下指標的純評審雜訊已達或超過容忍度：")
        for k, rng, e in problems:
            print(f"    {k}：極差 {rng:.4f} ≥ ε {e:.2f} → 放寬 ε 至 >{rng:.2f}，或降 advisory")
    else:
        print("\n[結論] 所有硬性 judge 指標的 ε 目前都大於實測雜訊。")


if __name__ == "__main__":
    main()
