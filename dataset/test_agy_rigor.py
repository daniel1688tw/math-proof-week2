# -*- coding: utf-8 -*-
"""Antigravity CLI（agy）判準嚴謹度比對：拿 Claude 已判定含真實數學錯誤的
H5/zh 對話（v10 判定用，v10_VERDICT.md 記錄），讓 agy 用同一份 DIALOGUE_JUDGE_PROMPT
判一次，看抓不抓得到「助教誤稱均值定理給出嚴格不等式」這個錯誤。
只讀不寫，不影響現行守門。"""
import json
import os
import re
import subprocess
import sys

AGY = os.path.join(os.environ.get("LOCALAPPDATA", ""), "agy", "bin", "agy.exe")
AGY_MODEL = os.environ.get("AGY_MODEL", "Gemini 3.5 Flash (Medium)")

STATEMENT = "證明：對所有 x>0，e^x > 1+x。"
PROOF = ("令 f(t)=e^t，在 [0,x] 上連續、(0,x) 上可微，由均值定理存在 c∈(0,x) 使 "
         "e^x-e^0=e^c(x-0)，即 e^x-1=e^c x。因 c>0 故 e^c>1，於是 e^c x>x，"
         "故 e^x-1>x，即 e^x>1+x。（注意：均值定理給出的是等式，不等式來自 c>0 這個額外資訊）")

HISTORY = """[助教] 先設 f(t)=e^t，它在 [0,x] 上滿足均值定理的前提是什麼？
[學生] 呃……均值定理要求函數在那個區間上連續，然後在開區間上可微分？我記得好像是這樣，但不確定有沒有漏什麼條件。
[助教] 這兩個前提都對，而且 e^t 確實同時具備。有了 f(a)-f(b)=f'(c)(b-a)，你能寫出 e^x-e^0 的等價形式嗎？
[學生] 等等，助教給的公式是 f(a)-f(b)=f'(c)(b-a)，但我記得均值定理應該是 f(b)-f(a)=f'(c)(b-a) 吧？不過不管符號，代入的話……e^x - e^0 就是 e^x - 1，然後右邊應該是 e^c · (x-0) = e^c · x？所以是 e^x - 1 = e^c · x，這樣對嗎？
[助教] 完全正確。現在 c∈(0,x)，e^c>1 而 x>0，你能從 e^x-1=e^c x 推出什麼樣的不等式來完成證明嗎？
[學生] 喔……因為 e^c > 1 而且 x > 0，所以 e^c · x > 1 · x = x，然後因為 e^x - 1 = e^c x > x，就得到 e^x > 1 + x？感覺就這樣結束了，有點意外這麼直接。
[助教] 正是如此，均值定理只給出等式，真正的靈魂在「c 是正數」這個細節上。你已經自己把它推完了，這題的價值其實就在於那個隱藏的 c>0。 那你覺得，下一步該從哪裡下手？
[學生] 咦，這題不是已經證完了嗎？e^x > 1+x 的結論已經推出來了……助教說「下一步該從哪裡下手」，是指還有什麼沒完成嗎？我有點搞不清楚。
[助教] 你問得很有洞察力。我們剛證的是「e^x>1+x」，但還有一個等價命題：e^x≥1+x 在哪一點取到等號？
[學生] 等等，e^x ≥ 1+x 取等號……那就是 e^x = 1+x 的時候，但我剛才推的過程是 e^c x > x，是因為 c > 0 所以 e^c > 1……如果 x = 0 的話，兩邊都是 1，所以等號在 x=0 成立？但這題的前提是 x > 0，所以我們根本沒在那個範圍裡，感覺助教問的好像是題目範圍以外的事？
[助教] 你的直覺完全正確。這題的嚴謹性其實還有一層：均值定理給出的是嚴格不等式，而 x=0 時 e^0=1+0，所以「e^x≥1+x」這個不等式在 x=0 取等號，而在 x>0 取嚴格。這才是完整的版本。 依你看，接下來哪個條件最值得先用？
[學生] 助教說「接下來哪個條件最值得先用」……但這題不是已經證完了嗎？我剛才連 x=0 的等號情況也討論完了，感覺整個證明已經結束了，不太懂助教還想繼續推什麼？
[助教] 這正是理解的關鍵。你已經把「x>0 時嚴格成立」證完了，但「x=0 時取等號」這個額外事實，正是很多應用（比如凸性）需要的。你會不會因此想問：「那能不能把這個不等式寫成含等號的單一命題？」"""

DIALOGUE_JUDGE_PROMPT = """你是嚴格的數學教學評審。審查以下完整的引導對話。

【題目】{statement}
【參考解（正確）】{proof}
【對話】
{history}

判定（只看「助教」的發言）：
- math_ok：助教所有數學陳述是否全部正確（一句錯就 false）
- guidance：整場引導品質 1-5（不奉送、一問一等、有效把學生推向理解、該提示才提示）
- issue：一句話指出最大問題（沒有就空字串）

只輸出 JSON：{{"math_ok": true, "guidance": 4, "issue": ""}}"""

_JSON_RE = re.compile(r"\{.*\}", re.S)

# 已知的 Claude 判定（v10_VERDICT.md 記錄）：math_ok=False，
# issue 指出「均值定理給出的是嚴格不等式」是錯誤陳述（MVT 給的是等式）。
CLAUDE_VERDICT = {"math_ok": False,
                  "issue": "把「更弱命題」誤稱「等價命題」、誤稱 MVT 給出嚴格不等式"}


def main():
    prompt = DIALOGUE_JUDGE_PROMPT.format(statement=STATEMENT, proof=PROOF, history=HISTORY)
    print(f"[模型] {AGY_MODEL}")
    try:
        r = subprocess.run([AGY, "--model", AGY_MODEL, "-p", prompt, "--print-timeout", "60s"],
                            capture_output=True, text=True, encoding="utf-8", timeout=75)
    except subprocess.TimeoutExpired:
        print("[FAIL] 逾時"); return 1
    if r.returncode != 0:
        print(f"[FAIL] exit={r.returncode} stderr={r.stderr[:200]}"); return 1
    m = _JSON_RE.search(r.stdout)
    if not m:
        print(f"[FAIL] 無法解析 JSON，原始輸出：{r.stdout[:300]!r}"); return 1
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        print(f"[FAIL] JSON 解析錯誤：{e}，原始：{m.group(0)[:300]!r}"); return 1

    print(f"\nClaude 判定（已知）: math_ok={CLAUDE_VERDICT['math_ok']}  issue={CLAUDE_VERDICT['issue']}")
    print(f"agy({AGY_MODEL}) 判定: math_ok={obj.get('math_ok')}  guidance={obj.get('guidance')}  "
          f"issue={obj.get('issue', '')}")

    caught = obj.get("math_ok") is False
    print(f"\n{'✓ agy 抓到了同一個數學錯誤' if caught else '✗ agy 沒抓到這個錯誤（math_ok=True，漏判）'}")
    return 0 if caught else 1


if __name__ == "__main__":
    sys.exit(main())
