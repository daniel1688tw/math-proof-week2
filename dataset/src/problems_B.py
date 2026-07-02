# -*- coding: utf-8 -*-
"""主題 B：連續性（IVT / 最大值定理 / 一致連續 / 連續定義 / 合成）。
所有參考解由 Claude 手寫並驗證數學正確性。"""

PROBLEMS = [
    {
        "id": "B1",
        "topic": "連續性",
        "difficulty": "中等",
        "statement": r"設 $f$ 在 $[a,b]$ 連續且 $f(a)f(b)<0$，證明存在 $c\in(a,b)$ 使 $f(c)=0$。",
        "reference_proof": r"""不妨設 $f(a)<0<f(b)$。令 $S=\{x\in[a,b]:f(x)<0\}$。
$S$ 非空（含 $a$）且有上界 $b$，由實數完備性 $c=\sup S$ 存在，且 $c\in[a,b]$。
斷言 $f(c)=0$：
（i）若 $f(c)>0$，由連續性存在 $\delta>0$ 使 $(c-\delta,c]$ 上 $f>0$，則 $c-\delta$ 亦為 $S$ 上界，與 $c=\sup S$ 矛盾。
（ii）若 $f(c)<0$，則 $c<b$，由連續性存在 $\delta>0$ 使 $[c,c+\delta)$ 上 $f<0$，則 $S$ 中有大於 $c$ 的點，矛盾。
故 $f(c)=0$，且因 $f(a),f(b)\ne 0$ 得 $c\in(a,b)$。$\blacksquare$""",
    },
    {
        "id": "B2",
        "topic": "連續性",
        "difficulty": "進階",
        "statement": r"證明 $[a,b]$ 上的連續函數 $f$ 必達到最大值（最大值定理）。",
        "reference_proof": r"""第一步（有界）：若 $f$ 無上界，則存在 $x_n\in[a,b]$ 使 $f(x_n)>n$。由 Bolzano-Weierstrass，$\{x_n\}$ 有收斂子列 $x_{n_k}\to x^*\in[a,b]$。由連續性 $f(x_{n_k})\to f(x^*)$（有限），與 $f(x_{n_k})>n_k\to\infty$ 矛盾。故 $f$ 有上界。
第二步（達到）：令 $M=\sup_{[a,b]}f$（存在且有限）。取 $y_n\in[a,b]$ 使 $f(y_n)\to M$。由 B-W 取收斂子列 $y_{n_k}\to y^*\in[a,b]$，由連續性 $f(y^*)=\lim f(y_{n_k})=M$。
故 $f$ 在 $y^*$ 達到最大值 $M$。$\blacksquare$""",
    },
    {
        "id": "B3",
        "topic": "連續性",
        "difficulty": "進階",
        "statement": r"證明 $[a,b]$ 上的連續函數 $f$ 為一致連續（Heine-Cantor 定理）。",
        "reference_proof": r"""反證法。假設 $f$ 不一致連續，則存在 $\varepsilon_0>0$，對每個 $n$ 存在 $x_n,y_n\in[a,b]$ 使
$$|x_n-y_n|<\tfrac1n \quad\text{但}\quad |f(x_n)-f(y_n)|\ge \varepsilon_0.$$
由 Bolzano-Weierstrass，$\{x_n\}$ 有收斂子列 $x_{n_k}\to x^*\in[a,b]$。
因 $|x_{n_k}-y_{n_k}|<\frac{1}{n_k}\to 0$，故 $y_{n_k}\to x^*$ 亦成立。
由 $f$ 在 $x^*$ 連續，$f(x_{n_k})\to f(x^*)$ 且 $f(y_{n_k})\to f(x^*)$，
於是 $|f(x_{n_k})-f(y_{n_k})|\to 0$，與 $\ge\varepsilon_0$ 矛盾。$\blacksquare$""",
    },
    {
        "id": "B4",
        "topic": "連續性",
        "difficulty": "中等",
        "statement": r"證明 $f(x)=x^2$ 在 $\mathbb{R}$ 上不一致連續。",
        "reference_proof": r"""要證：存在 $\varepsilon_0>0$，對任意 $\delta>0$ 都能找到 $x,y$ 使 $|x-y|<\delta$ 但 $|f(x)-f(y)|\ge\varepsilon_0$。
取 $\varepsilon_0=1$。對任意 $\delta>0$，令 $x=n+\dfrac{\delta}{2}$、$y=n$（$n$ 為待定大整數）。
則 $|x-y|=\dfrac{\delta}{2}<\delta$，而
$$|x^2-y^2|=|x-y|\,|x+y|=\frac{\delta}{2}\Big(2n+\frac{\delta}{2}\Big)\ge \delta n.$$
取 $n$ 足夠大使 $\delta n\ge 1$，即得 $|f(x)-f(y)|\ge 1$。故不一致連續。
（本質原因：$|x+y|$ 無界，使同樣的 $\delta$ 無法通用。）$\blacksquare$""",
    },
    {
        "id": "B5",
        "topic": "連續性",
        "difficulty": "基礎",
        "statement": r"用 $\varepsilon$-$\delta$ 定義證明 $f(x)=x^2$ 在任一點 $x=a$ 連續。",
        "reference_proof": r"""要證：對任意 $\varepsilon>0$，存在 $\delta>0$，使 $|x-a|<\delta \Rightarrow |x^2-a^2|<\varepsilon$。
$|x^2-a^2|=|x-a|\,|x+a|$。先限制 $|x-a|<1$，則 $|x+a|\le |x-a|+2|a|<1+2|a|$。
故 $|x^2-a^2|<(1+2|a|)|x-a|$。
取 $\delta=\min\Big\{1,\dfrac{\varepsilon}{1+2|a|}\Big\}$，則 $|x-a|<\delta$ 時 $|x^2-a^2|<\varepsilon$。$\blacksquare$""",
    },
    {
        "id": "B6",
        "topic": "連續性",
        "difficulty": "中等",
        "statement": r"設 $f$ 在 $x_0$ 連續。證明：對任意數列 $x_n\to x_0$，皆有 $f(x_n)\to f(x_0)$（連續的序列準則）。",
        "reference_proof": r"""給定 $\varepsilon>0$。由 $f$ 在 $x_0$ 連續，存在 $\delta>0$ 使 $|x-x_0|<\delta \Rightarrow |f(x)-f(x_0)|<\varepsilon$。
由 $x_n\to x_0$，對此 $\delta$ 存在 $N$ 使 $n\ge N \Rightarrow |x_n-x_0|<\delta$。
於是 $n\ge N$ 時 $|f(x_n)-f(x_0)|<\varepsilon$，即 $f(x_n)\to f(x_0)$。$\blacksquare$""",
    },
    {
        "id": "B7",
        "topic": "連續性",
        "difficulty": "中等",
        "statement": r"證明任一奇次實係數多項式 $p(x)=x^{2k+1}+c_{2k}x^{2k}+\cdots+c_0$ 至少有一實根。",
        "reference_proof": r"""$p$ 為多項式，在 $\mathbb{R}$ 上連續。考慮 $x\to\pm\infty$ 的行為：
因最高次項為奇次 $x^{2k+1}$，$\lim_{x\to+\infty}p(x)=+\infty$，$\lim_{x\to-\infty}p(x)=-\infty$。
故存在 $b$ 使 $p(b)>0$，存在 $a<b$ 使 $p(a)<0$。
$p$ 在 $[a,b]$ 連續且 $p(a)<0<p(b)$，由介值定理存在 $c\in(a,b)$ 使 $p(c)=0$。$\blacksquare$""",
    },
    {
        "id": "B8",
        "topic": "連續性",
        "difficulty": "進階",
        "statement": r"證明 $[a,b]$ 上的連續函數必有界（有界性定理）。",
        "reference_proof": r"""反證法。假設 $f$ 無界，則對每個 $n$ 存在 $x_n\in[a,b]$ 使 $|f(x_n)|>n$。
$\{x_n\}\subset[a,b]$ 有界，由 Bolzano-Weierstrass 有收斂子列 $x_{n_k}\to x^*$，
且因 $[a,b]$ 為閉集，$x^*\in[a,b]$。
由 $f$ 在 $x^*$ 連續，$f(x_{n_k})\to f(x^*)$，故 $\{f(x_{n_k})\}$ 收斂因而有界；
但 $|f(x_{n_k})|>n_k\to\infty$ 無界，矛盾。故 $f$ 有界。$\blacksquare$""",
    },
    {
        "id": "B9",
        "topic": "連續性",
        "difficulty": "中等",
        "statement": r"設 $g$ 在 $x_0$ 連續、$f$ 在 $g(x_0)$ 連續，證明 $f\circ g$ 在 $x_0$ 連續。",
        "reference_proof": r"""令 $y_0=g(x_0)$。給定 $\varepsilon>0$。
由 $f$ 在 $y_0$ 連續，存在 $\eta>0$ 使 $|y-y_0|<\eta \Rightarrow |f(y)-f(y_0)|<\varepsilon$。
由 $g$ 在 $x_0$ 連續，對此 $\eta$ 存在 $\delta>0$ 使 $|x-x_0|<\delta \Rightarrow |g(x)-y_0|<\eta$。
於是 $|x-x_0|<\delta \Rightarrow |g(x)-y_0|<\eta \Rightarrow |f(g(x))-f(y_0)|<\varepsilon$，即 $f\circ g$ 在 $x_0$ 連續。$\blacksquare$""",
    },
    {
        "id": "B10",
        "topic": "連續性",
        "difficulty": "進階",
        "statement": r"設 $f$ 在 $[0,1]$ 連續且 $f(0)=f(1)$，證明存在 $c\in[0,\tfrac12]$ 使 $f(c)=f(c+\tfrac12)$。",
        "reference_proof": r"""定義 $g(x)=f(x+\tfrac12)-f(x)$，$g$ 在 $[0,\tfrac12]$ 連續。
計算端點：$g(0)=f(\tfrac12)-f(0)$，$g(\tfrac12)=f(1)-f(\tfrac12)$。
兩者相加：$g(0)+g(\tfrac12)=f(1)-f(0)=0$，故 $g(\tfrac12)=-g(0)$。
若 $g(0)=0$，取 $c=0$。否則 $g(0)$ 與 $g(\tfrac12)$ 異號，由介值定理存在 $c\in(0,\tfrac12)$ 使 $g(c)=0$，
即 $f(c)=f(c+\tfrac12)$。$\blacksquare$""",
    },
]
