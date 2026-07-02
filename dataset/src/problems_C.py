# -*- coding: utf-8 -*-
"""主題 C：微分學（可微⇒連續 / 均值定理 Rolle-Lagrange-Cauchy / 費馬 / 單調 / Lipschitz）。
所有參考解由 Claude 手寫並驗證數學正確性。"""

PROBLEMS = [
    {
        "id": "C1",
        "topic": "微分",
        "difficulty": "基礎",
        "statement": r"證明：若 $f$ 在 $x_0$ 可微，則 $f$ 在 $x_0$ 連續。",
        "reference_proof": r"""要證 $\lim_{x\to x_0}f(x)=f(x_0)$，即 $\lim_{x\to x_0}\big(f(x)-f(x_0)\big)=0$。
對 $x\ne x_0$ 恆等變形：
$$f(x)-f(x_0)=\frac{f(x)-f(x_0)}{x-x_0}\cdot (x-x_0).$$
當 $x\to x_0$，第一因子 $\to f'(x_0)$（可微假設，有限），第二因子 $\to 0$。
由極限乘積律，$\lim_{x\to x_0}\big(f(x)-f(x_0)\big)=f'(x_0)\cdot 0=0$。故 $f$ 在 $x_0$ 連續。$\blacksquare$""",
    },
    {
        "id": "C2",
        "topic": "微分",
        "difficulty": "中等",
        "statement": r"證明 Rolle 定理：$f$ 在 $[a,b]$ 連續、$(a,b)$ 可微且 $f(a)=f(b)$，則存在 $c\in(a,b)$ 使 $f'(c)=0$。",
        "reference_proof": r"""$f$ 在 $[a,b]$ 連續，由最大值定理達到最大值 $M$ 與最小值 $m$。
情形一：$M=m$，則 $f$ 為常數，$(a,b)$ 上 $f'\equiv 0$，任取 $c$ 即可。
情形二：$M>m$。由 $f(a)=f(b)$，最大或最小值至少有一個在內部點 $c\in(a,b)$ 取得。
在該內部極值點，由費馬定理 $f'(c)=0$。$\blacksquare$""",
    },
    {
        "id": "C3",
        "topic": "微分",
        "difficulty": "中等",
        "statement": r"證明 Lagrange 均值定理：$f$ 在 $[a,b]$ 連續、$(a,b)$ 可微，則存在 $c$ 使 $f'(c)=\dfrac{f(b)-f(a)}{b-a}$。",
        "reference_proof": r"""構造輔助函數，消去端點差以套用 Rolle：
$$g(x)=f(x)-f(a)-\frac{f(b)-f(a)}{b-a}(x-a).$$
$g$ 在 $[a,b]$ 連續、$(a,b)$ 可微。驗證端點：$g(a)=0$，且
$g(b)=f(b)-f(a)-\dfrac{f(b)-f(a)}{b-a}(b-a)=0$。
由 Rolle 定理存在 $c\in(a,b)$ 使 $g'(c)=0$。而 $g'(x)=f'(x)-\dfrac{f(b)-f(a)}{b-a}$，
故 $f'(c)=\dfrac{f(b)-f(a)}{b-a}$。$\blacksquare$""",
    },
    {
        "id": "C4",
        "topic": "微分",
        "difficulty": "進階",
        "statement": r"證明 Cauchy 均值定理：$f,g$ 在 $[a,b]$ 連續、$(a,b)$ 可微且 $g'\ne 0$，則存在 $c$ 使 $\dfrac{f'(c)}{g'(c)}=\dfrac{f(b)-f(a)}{g(b)-g(a)}$。",
        "reference_proof": r"""先注意 $g(b)\ne g(a)$：否則由 Rolle 存在點使 $g'=0$，與假設矛盾。
構造輔助函數
$$h(x)=\big(f(b)-f(a)\big)\,g(x)-\big(g(b)-g(a)\big)\,f(x).$$
$h$ 在 $[a,b]$ 連續、$(a,b)$ 可微。計算 $h(a)=f(b)g(a)-g(b)f(a)=h(b)$（展開可驗證相等）。
由 Rolle 存在 $c$ 使 $h'(c)=0$，即 $\big(f(b)-f(a)\big)g'(c)=\big(g(b)-g(a)\big)f'(c)$。
除以 $g'(c)\big(g(b)-g(a)\big)\ne 0$ 得結論。$\blacksquare$""",
    },
    {
        "id": "C5",
        "topic": "微分",
        "difficulty": "中等",
        "statement": r"證明：若 $f$ 在區間 $I$ 上可微且 $f'\equiv 0$，則 $f$ 在 $I$ 上為常數。",
        "reference_proof": r"""任取 $x_1<x_2\in I$。$f$ 在 $[x_1,x_2]$ 連續、$(x_1,x_2)$ 可微，由 Lagrange 均值定理
存在 $c\in(x_1,x_2)$ 使
$$f(x_2)-f(x_1)=f'(c)(x_2-x_1).$$
由 $f'(c)=0$ 得 $f(x_2)=f(x_1)$。因 $x_1,x_2$ 任取，$f$ 在 $I$ 上取同一值，即為常數。$\blacksquare$""",
    },
    {
        "id": "C6",
        "topic": "微分",
        "difficulty": "中等",
        "statement": r"證明：若 $f$ 在區間 $I$ 上可微且 $f'>0$，則 $f$ 在 $I$ 上嚴格遞增。",
        "reference_proof": r"""任取 $x_1<x_2\in I$。由 Lagrange 均值定理，存在 $c\in(x_1,x_2)$ 使
$$f(x_2)-f(x_1)=f'(c)(x_2-x_1).$$
因 $f'(c)>0$ 且 $x_2-x_1>0$，右端 $>0$，故 $f(x_2)>f(x_1)$。
因 $x_1<x_2$ 任取，$f$ 嚴格遞增。$\blacksquare$""",
    },
    {
        "id": "C7",
        "topic": "微分",
        "difficulty": "中等",
        "statement": r"證明費馬定理：若 $f$ 在內部點 $c$ 取得局部極大且 $f'(c)$ 存在，則 $f'(c)=0$。",
        "reference_proof": r"""設 $c$ 為局部極大，則存在 $\delta>0$，$|h|<\delta$ 時 $f(c+h)\le f(c)$。
右導數（$h\to 0^+$）：差商 $\dfrac{f(c+h)-f(c)}{h}\le 0$，故 $f'(c)=\lim_{h\to0^+}\le 0$。
左導數（$h\to 0^-$）：分子 $\le 0$、分母 $<0$，差商 $\ge 0$，故 $f'(c)\ge 0$。
因 $f'(c)$ 存在（左右導數相等），同時 $\le 0$ 與 $\ge 0$，故 $f'(c)=0$。$\blacksquare$""",
    },
    {
        "id": "C8",
        "topic": "微分",
        "difficulty": "中等",
        "statement": r"設 $f$ 在區間 $I$ 可微且 $|f'(x)|\le M$，證明 $|f(x)-f(y)|\le M|x-y|$（$f$ 為 Lipschitz）。",
        "reference_proof": r"""任取 $x,y\in I$，不妨 $x\ne y$。由 Lagrange 均值定理，存在介於 $x,y$ 之間的 $c$ 使
$$f(x)-f(y)=f'(c)(x-y).$$
取絕對值並用 $|f'(c)|\le M$：
$$|f(x)-f(y)|=|f'(c)|\,|x-y|\le M|x-y|.$$
$x=y$ 時兩端皆為 $0$，不等式亦成立。$\blacksquare$""",
    },
    {
        "id": "C9",
        "topic": "微分",
        "difficulty": "中等",
        "statement": r"證明對所有實數 $x,y$，$|\sin x-\sin y|\le |x-y|$。",
        "reference_proof": r"""令 $f(t)=\sin t$，則 $f'(t)=\cos t$，$|f'(t)|\le 1$。
對 $x\ne y$，由 Lagrange 均值定理存在 $c$ 使
$$\sin x-\sin y=\cos c\,(x-y).$$
取絕對值：$|\sin x-\sin y|=|\cos c|\,|x-y|\le |x-y|$。$x=y$ 時等式顯然成立。$\blacksquare$""",
    },
    {
        "id": "C10",
        "topic": "微分",
        "difficulty": "進階",
        "statement": r"證明對所有 $x>0$，$\dfrac{x}{1+x}<\ln(1+x)<x$。",
        "reference_proof": r"""令 $f(t)=\ln(1+t)$，在 $[0,x]$ 連續、$(0,x)$ 可微，$f'(t)=\dfrac{1}{1+t}$。
由 Lagrange 均值定理存在 $\xi\in(0,x)$ 使
$$\ln(1+x)-\ln 1=\frac{1}{1+\xi}\,x,\qquad\text{即 } \ln(1+x)=\frac{x}{1+\xi}.$$
因 $0<\xi<x$，有 $1<1+\xi<1+x$，故 $\dfrac{1}{1+x}<\dfrac{1}{1+\xi}<1$。
乘以 $x>0$：$\dfrac{x}{1+x}<\dfrac{x}{1+\xi}=\ln(1+x)<x$。$\blacksquare$""",
    },
]
