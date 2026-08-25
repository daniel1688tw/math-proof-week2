# -*- coding: utf-8 -*-
"""主題 D：積分學（FTC / 積分中值定理 / 可積性 / 保序 / 估計 / 廣義積分 / Cauchy-Schwarz）。
所有參考解由 Claude 手寫並驗證數學正確性。"""

PROBLEMS = [
    {
        "id": "D1",
        "topic": "積分",
        "difficulty": "中等",
        "statement": r"設 $f$ 在 $[a,b]$ 連續、$f\ge 0$ 且 $\int_a^b f(x)\,dx=0$，證明 $f\equiv 0$。",
        "reference_proof": r"""反證法。假設存在 $x_0\in[a,b]$ 使 $f(x_0)>0$。
由連續性，取 $\varepsilon=\dfrac{f(x_0)}{2}>0$，存在子區間 $[c,d]\subset[a,b]$（含 $x_0$，長度 $d-c>0$）使其上 $f(x)>\dfrac{f(x_0)}{2}$。
因 $f\ge 0$，
$$\int_a^b f\ge \int_c^d f\ge \frac{f(x_0)}{2}(d-c)>0,$$
與 $\int_a^b f=0$ 矛盾。故對所有 $x$，$f(x)=0$。$\blacksquare$""",
    },
    {
        "id": "D2",
        "topic": "積分",
        "difficulty": "進階",
        "statement": r"證明微積分基本定理（第一部分）：$f$ 在 $[a,b]$ 連續，$F(x)=\int_a^x f(t)\,dt$，則 $F'(x)=f(x)$。",
        "reference_proof": r"""固定 $x\in[a,b]$。對 $h\ne 0$，
$$\frac{F(x+h)-F(x)}{h}=\frac{1}{h}\int_x^{x+h}f(t)\,dt.$$
與 $f(x)$ 作差並利用 $\frac1h\int_x^{x+h}f(x)\,dt=f(x)$：
$$\left|\frac{F(x+h)-F(x)}{h}-f(x)\right|=\left|\frac1h\int_x^{x+h}\big(f(t)-f(x)\big)\,dt\right|\le \sup_{|t-x|\le|h|}|f(t)-f(x)|.$$
由 $f$ 在 $x$ 連續，當 $h\to 0$ 時右端 $\to 0$。故 $F'(x)=f(x)$。$\blacksquare$""",
    },
    {
        "id": "D3",
        "topic": "積分",
        "difficulty": "中等",
        "statement": r"證明積分第一中值定理：$f$ 在 $[a,b]$ 連續，則存在 $c\in[a,b]$ 使 $\int_a^b f(x)\,dx=f(c)(b-a)$。",
        "reference_proof": r"""$f$ 在 $[a,b]$ 連續，由最大值定理達到最小值 $m$ 與最大值 $M$，即 $m\le f(x)\le M$。
積分保序得 $m(b-a)\le\int_a^b f\le M(b-a)$，故平均值
$$\mu=\frac{1}{b-a}\int_a^b f\in[m,M].$$
由介值定理（連續函數取遍 $[m,M]$），存在 $c\in[a,b]$ 使 $f(c)=\mu$，即 $\int_a^b f=f(c)(b-a)$。$\blacksquare$""",
    },
    {
        "id": "D4",
        "topic": "積分",
        "difficulty": "基礎",
        "statement": r"設 $f,g$ 在 $[a,b]$ 可積且 $f(x)\le g(x)$，證明 $\int_a^b f\le \int_a^b g$（積分保序）。",
        "reference_proof": r"""令 $h=g-f\ge 0$，$h$ 在 $[a,b]$ 可積。
對任意分割 $P$，因 $h\ge 0$，其下和 $L(h,P)=\sum m_i\Delta x_i\ge 0$（每個 $m_i=\inf h\ge 0$）。
故 $\int_a^b h=\sup_P L(h,P)\ge 0$。
由積分線性，$\int_a^b g-\int_a^b f=\int_a^b h\ge 0$，即 $\int_a^b f\le\int_a^b g$。$\blacksquare$""",
    },
    {
        "id": "D5",
        "topic": "積分",
        "difficulty": "基礎",
        "statement": r"設 $f$ 在 $[a,b]$ 可積，證明 $\left|\int_a^b f\right|\le \int_a^b |f|$。",
        "reference_proof": r"""對所有 $x$ 有 $-|f(x)|\le f(x)\le |f(x)|$。
由積分保序分別積分：
$$-\int_a^b|f|\le \int_a^b f\le \int_a^b|f|.$$
一個實數同時 $\le A$ 且 $\ge -A$（其中 $A=\int_a^b|f|\ge0$），等價於 $\left|\int_a^b f\right|\le A=\int_a^b|f|$。$\blacksquare$""",
    },
    {
        "id": "D6",
        "topic": "積分",
        "difficulty": "中等",
        "statement": r"證明微積分基本定理（第二部分／Newton-Leibniz）：$f$ 在 $[a,b]$ 連續、$F'=f$，則 $\int_a^b f=F(b)-F(a)$。",
        "reference_proof": r"""令 $G(x)=\int_a^x f(t)\,dt$。由 FTC 第一部分，$G'=f=F'$ 於 $[a,b]$。
故 $(G-F)'\equiv 0$，由「導數恆零則為常數」得 $G-F\equiv C$（常數）。
代入 $x=a$：$G(a)=0$，故 $C=-F(a)$，即 $G(x)=F(x)-F(a)$。
代入 $x=b$：$\int_a^b f=G(b)=F(b)-F(a)$。$\blacksquare$""",
    },
    {
        "id": "D7",
        "topic": "積分",
        "difficulty": "進階",
        "statement": r"證明 $[a,b]$ 上的連續函數 $f$ 為黎曼可積。",
        "reference_proof": r"""由 Heine-Cantor，$f$ 在 $[a,b]$ 一致連續。給定 $\varepsilon>0$，存在 $\delta>0$ 使
$|s-t|<\delta \Rightarrow |f(s)-f(t)|<\dfrac{\varepsilon}{b-a}$。
取分割 $P$ 使每個子區間長 $\Delta x_i<\delta$。在閉子區間上 $f$ 達到最大 $M_i$、最小 $m_i$（最大值定理），
且對應點距離 $<\delta$，故 $M_i-m_i\le \dfrac{\varepsilon}{b-a}$。於是
$$U(f,P)-L(f,P)=\sum_i (M_i-m_i)\Delta x_i\le \frac{\varepsilon}{b-a}\sum_i \Delta x_i=\varepsilon.$$
由黎曼可積準則（上下和之差可任意小），$f$ 可積。$\blacksquare$""",
    },
    {
        "id": "D8",
        "topic": "積分",
        "difficulty": "基礎",
        "statement": r"證明 $\dfrac{1}{2}\le \int_0^1 \dfrac{dx}{1+x^2}\le 1$。",
        "reference_proof": r"""對 $x\in[0,1]$，$0\le x^2\le 1$，故 $1\le 1+x^2\le 2$，取倒數得
$$\frac{1}{2}\le \frac{1}{1+x^2}\le 1.$$
在 $[0,1]$（長度 $1$）上對此不等式積分（積分保序）：
$$\frac12\cdot 1\le \int_0^1\frac{dx}{1+x^2}\le 1\cdot 1,$$
即 $\dfrac12\le\int_0^1\dfrac{dx}{1+x^2}\le 1$。（實際值 $\pi/4\approx 0.785$，落在區間內。）$\blacksquare$""",
    },
    {
        "id": "D9",
        "topic": "積分",
        "difficulty": "中等",
        "statement": r"證明廣義積分 $\int_1^\infty \dfrac{dx}{x^p}$ 收斂當且僅當 $p>1$。",
        "reference_proof": r"""考慮 $\int_1^R x^{-p}\,dx$，令 $R\to\infty$。
情形 $p\ne 1$：$\int_1^R x^{-p}\,dx=\dfrac{R^{1-p}-1}{1-p}$。
  - 若 $p>1$，則 $1-p<0$，$R^{1-p}\to 0$，極限為 $\dfrac{1}{p-1}$（有限），收斂。
  - 若 $p<1$，則 $1-p>0$，$R^{1-p}\to\infty$，發散。
情形 $p=1$：$\int_1^R \dfrac{dx}{x}=\ln R\to\infty$，發散。
綜合：收斂 $\iff p>1$。$\blacksquare$""",
    },
    {
        "id": "D10",
        "topic": "積分",
        "difficulty": "進階",
        "statement": r"證明積分型 Cauchy-Schwarz 不等式：$f,g$ 在 $[a,b]$ 連續，則 $\left(\int_a^b fg\right)^2\le \left(\int_a^b f^2\right)\left(\int_a^b g^2\right)$。",
        "reference_proof": r"""若 $\int_a^b g^2=0$，由 D1（$g^2\ge0$ 連續積分為 $0$）得 $g\equiv 0$，兩端皆 $0$，成立。
否則令 $A=\int g^2>0$。對任意實數 $\lambda$，$(f-\lambda g)^2\ge 0$，積分得
$$0\le \int_a^b (f-\lambda g)^2=\int f^2-2\lambda\int fg+\lambda^2\int g^2.$$
這是關於 $\lambda$ 的二次式且恆非負，故判別式 $\le 0$：
$$\Big(2\int fg\Big)^2-4\Big(\int g^2\Big)\Big(\int f^2\Big)\le 0,$$
整理即 $\left(\int fg\right)^2\le \left(\int f^2\right)\left(\int g^2\right)$。$\blacksquare$""",
    },
]
