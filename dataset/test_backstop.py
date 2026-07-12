# -*- coding: utf-8 -*-
"""test_backstop.py — 審閱後盾找碴準確度測試（需 Ollama，不需 GPU/HF 模型）。

用三個「微調模型審閱曾失手」的真實案例，驗證思考型後盾能否精準找出缺漏：
  案例 1（X2 鴿籠）  ：草稿缺「餘數只有 n 種」前提——微調模型察覺對但解釋錯。
  案例 2（X4 特徵向量）：草稿推 c2=0 缺 v2≠0 依據——微調模型只問出泛泛概念題。
  案例 3（H3 雙重錯誤）：嘗試含兩個錯——微調模型只抓到一個、還背書了錯的那個。
輸出各案例的缺漏清單供人工核對；自動斷言只檢查「有找到 vs 沒找到／降級」。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from review_backstop import available, find_gaps  # noqa: E402

HERE = Path(__file__).resolve().parent

if not available():
    print("Ollama 未在線或後盾模型未安裝，跳過（部署時 driver 會自動降級）")
    sys.exit(0)

xdomain = {p["id"]: p for p in
           json.loads((HERE / "xdomain_problems.json").read_text(encoding="utf-8"))}
heldout = {p["id"]: p for p in
           json.loads((HERE / "held_out.json").read_text(encoding="utf-8"))}
attempts = json.loads((HERE / "held_out_attempts.json").read_text(encoding="utf-8"))

CASES = [
    ("X2 鴿籠：草稿缺類別數前提",
     xdomain["X2"],
     "證明：任取 n+1 個整數。由鴿籠原理，必存在兩個數 a、b（a≠b）除以 n 的餘數相同。"
     "設 a = qn + r、b = pn + r，則 a − b = (q − p)n，故 n 整除 a − b。證畢。",
     "期望：指出套用鴿籠原理前未陳述「餘數共 n 種 vs 數有 n+1 個」"),
    ("X4 特徵向量：推 c2=0 缺 v2≠0",
     xdomain["X4"],
     "證明：設 c1v1 + c2v2 = 0（式 1）。左乘 A 得 c1λ1v1 + c2λ2v2 = 0（式 2）。"
     "式 2 減 λ1 倍式 1 得 c2(λ2−λ1)v2 = 0。因為 λ2 ≠ λ1，所以 c2 = 0。"
     "代回式 1 得 c1v1 = 0，因為 v1 ≠ 0，所以 c1 = 0。故 {v1, v2} 線性獨立。",
     "期望：指出從 c2(λ2−λ1)v2=0 推 c2=0 還需要 v2≠0"),
    ("H3 雙重錯誤：無理數寫成有理數平均＋假設 f 線性",
     heldout["H3"],
     attempts["H3"]["attempt"],
     "期望：兩個錯都抓到——(p+q)/2 仍是有理數；f((p+q)/2)=(f(p)+f(q))/2 無依據"),
]

fails = 0
for name, prob, draft, expect in CASES:
    print(f"\n=== {name} ===")
    print(f"（{expect}）")
    gaps = find_gaps(prob["statement"], prob["reference_proof"], draft)
    if gaps is None:
        print("  ✗ 後盾降級（逾時或輸出不可解析）")
        fails += 1
    elif not gaps:
        print("  ✗ 未找到任何缺漏（應至少找到一項）")
        fails += 1
    else:
        for g in gaps:
            print(f"  → {g}")

print()
if fails:
    print(f"✗ {fails}/3 案例失敗")
    sys.exit(1)
print("3/3 案例後盾均有產出，內容請人工核對上方清單 ✓")
