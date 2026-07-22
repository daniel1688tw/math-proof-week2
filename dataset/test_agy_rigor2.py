# -*- coding: utf-8 -*-
"""第二筆判準比對：乾淨（無數學錯誤）案例，確認 agy 不會誤殺（false positive）。
X4/en，Claude 判定 math_ok=True guidance=4。"""
import json
import os
import re
import subprocess
import sys

AGY = os.path.join(os.environ.get("LOCALAPPDATA", ""), "agy", "bin", "agy.exe")
AGY_MODEL = os.environ.get("AGY_MODEL", "Gemini 3.5 Flash (Medium)")

STATEMENT = "設 Av1=λ1v1、Av2=λ2v2，λ1≠λ2，證明 v1、v2 線性獨立。"
PROOF = ("設 c1v1+c2v2=0，左乘 A 得 c1λ1v1+c2λ2v2=0；前式乘 λ1 相減得 "
         "c2(λ2-λ1)v2=0，因 λ2≠λ1 且 v2≠0 得 c2=0，代回得 c1=0。")

HISTORY = """[助教] Start from the definition of linear dependence: if $c_1v_1+c_2v_2=0$, what do you want to prove?
[學生] I want to prove that $c_1 = c_2 = 0$ is the only solution. But wait — isn't that kind of obvious? Like, $v_1$ and $v_2$ are eigenvectors, so they're nonzero by definition, and nonzero vectors are always linearly independent, right?
[助教] That's the trap. "Nonzero vectors" doesn't guarantee linear independence — $v_2$ could equal $2v_1$. So which property of the eigenvalues must you use instead?
[學生] Oh right, that makes sense — two nonzero vectors can still be parallel. So I need to use the fact that $\\lambda_1 \\ne \\lambda_2$... but I'm not sure exactly how. Do I multiply the equation $c_1v_1 + c_2v_2 = 0$ by $A$ somehow?
[助教] Exactly. After left-multiplying by $A$, you'll get another linear combination involving $\\lambda_1,\\lambda_2$. How would you combine it with the original equation to eliminate one vector?
[學生] Okay so if I multiply $c_1v_1 + c_2v_2 = 0$ by $A$, I get $c_1\\lambda_1 v_1 + c_2\\lambda_2 v_2 = 0$. And the original is $c_1v_1 + c_2v_2 = 0$, so if I multiply that by $\\lambda_1$ and subtract... I'd get $c_2(\\lambda_2 - \\lambda_1)v_2 = 0$. Since $v_2$ is nonzero and $\\lambda_1 \\ne \\lambda_2$, that forces $c_2 = 0$!
[助教] Completely correct. The key is: distinct eigenvalues plus the definition of eigenvectors (nonzero) together force the linear independence — you can't rely on "nonzero vectors are independent". So where do you think the next step should start?
[學生] Right, so with $c_2 = 0$ plugged back into the original equation, we just get $c_1 v_1 = 0$, and since $v_1$ is nonzero that means $c_1 = 0$ too. So both coefficients are zero, which is exactly what we needed — I think that wraps up the proof?
[助教] Yes, and you yourself pointed out the trap: "nonzero vectors are linearly independent" is false. You used the distinct eigenvalues hypothesis precisely where it was needed — that's the hallmark of a rigorous proof. Well done.
[學生] Yeah, that actually clicks now — I was confusing "nonzero" with "independent," which is totally wrong. The real work was using $\\lambda_1 \\ne \\lambda_2$ to create that telescoping elimination. Thanks, I think I could write this up cleanly on my own now.
[助教] You're welcome. Remember: in linear algebra, "nonzero" and "linearly independent" are two different things — and the latter needs a hypothesis (distinct eigenvalues) to hold.
[學生] Got it — "linearly independent" is strictly stronger than just "nonzero," and the whole proof hinges on $\\lambda_1 \\ne \\lambda_2$ giving us that $(\\lambda_2 - \\lambda_1) \\ne 0$ factor to squeeze out $c_2$. I'll remember that next time I'm tempted to shortcut with "they're eigenvectors so they must be independent.
[助教] Exactly — and you caught it yourself. That's the essence of understanding. Keep going. Which condition do you think is worth using next?"""

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
CLAUDE_VERDICT = {"math_ok": True, "guidance": 4}


def main():
    prompt = DIALOGUE_JUDGE_PROMPT.format(statement=STATEMENT, proof=PROOF, history=HISTORY)
    print(f"[模型] {AGY_MODEL}")
    r = subprocess.run([AGY, "--model", AGY_MODEL, "-p", prompt, "--print-timeout", "60s"],
                        capture_output=True, text=True, encoding="utf-8", timeout=75)
    if r.returncode != 0:
        print(f"[FAIL] exit={r.returncode}"); return 1
    m = _JSON_RE.search(r.stdout)
    if not m:
        print(f"[FAIL] 無法解析：{r.stdout[:300]!r}"); return 1
    obj = json.loads(m.group(0))
    print(f"\nClaude 判定（已知）: math_ok={CLAUDE_VERDICT['math_ok']}  guidance={CLAUDE_VERDICT['guidance']}")
    print(f"agy({AGY_MODEL}) 判定: math_ok={obj.get('math_ok')}  guidance={obj.get('guidance')}  "
          f"issue={obj.get('issue', '')}")
    ok = obj.get("math_ok") is True
    print(f"\n{'✓ agy 正確判過（無誤殺）' if ok else '✗ agy 誤殺了乾淨案例（false positive）'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
