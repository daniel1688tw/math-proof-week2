# -*- coding: utf-8 -*-
"""主題 A：數列與函數極限（ε-N / ε-δ / 夾擠 / 極限運算 / 有界性）。
所有參考解由 Claude 手寫並驗證數學正確性。"""

PROBLEMS = [
    {
        "id": "A1",
        "topic": "極限",
        "difficulty": "中等",
        "statement": r"證明 $\lim_{n\to\infty}\sqrt[n]{n}=1$。",
        "reference_proof": r"""令 $a_n=\sqrt[n]{n}-1\ge 0$（因 $n\ge 1$ 時 $\sqrt[n]{n}\ge 1$）。則 $n=(1+a_n)^n$。
由二項式定理，當 $n\ge 2$ 時，
$$n=(1+a_n)^n\ge \binom{n}{2}a_n^2=\frac{n(n-1)}{2}a_n^2.$$
因此 $a_n^2\le \dfrac{2}{n-1}$，即 $0\le a_n\le \sqrt{\dfrac{2}{n-1}}$。
當 $n\to\infty$ 時右端 $\to 0$，由夾擠定理 $a_n\to 0$，故 $\sqrt[n]{n}=1+a_n\to 1$。$\blacksquare$""",
    },
    {
        "id": "A2",
        "topic": "極限",
        "difficulty": "中等",
        "statement": r"用 $\varepsilon$-$\delta$ 定義證明 $\lim_{x\to 2}x^2=4$。",
        "reference_proof": r"""要證：對任意 $\varepsilon>0$，存在 $\delta>0$，使得 $0<|x-2|<\delta \Rightarrow |x^2-4|<\varepsilon$。
先做因式分解：$|x^2-4|=|x-2|\,|x+2|$。
先限制 $|x-2|<1$，則 $1<x<3$，於是 $|x+2|<5$。
故當 $|x-2|<1$ 時 $|x^2-4|<5|x-2|$。
取 $\delta=\min\{1,\varepsilon/5\}$。則 $0<|x-2|<\delta$ 時 $|x^2-4|<5\cdot\frac{\varepsilon}{5}=\varepsilon$。$\blacksquare$""",
    },
    {
        "id": "A3",
        "topic": "極限",
        "difficulty": "中等",
        "statement": r"設 $\lim_{n\to\infty}a_n=L$、$\lim_{n\to\infty}b_n=M$，證明 $\lim_{n\to\infty}(a_n+b_n)=L+M$。",
        "reference_proof": r"""要證：對任意 $\varepsilon>0$，存在 $N$，使得 $n\ge N \Rightarrow |(a_n+b_n)-(L+M)|<\varepsilon$。
關鍵不等式（三角不等式）：$|(a_n+b_n)-(L+M)|\le |a_n-L|+|b_n-M|$。
由 $a_n\to L$：存在 $N_1$ 使 $n\ge N_1 \Rightarrow |a_n-L|<\varepsilon/2$。
由 $b_n\to M$：存在 $N_2$ 使 $n\ge N_2 \Rightarrow |b_n-M|<\varepsilon/2$。
取 $N=\max\{N_1,N_2\}$，則 $n\ge N$ 時兩式同時成立，故和 $<\varepsilon/2+\varepsilon/2=\varepsilon$。$\blacksquare$""",
    },
    {
        "id": "A4",
        "topic": "極限",
        "difficulty": "基礎",
        "statement": r"證明 $\lim_{n\to\infty}\dfrac{\sin n}{n}=0$。",
        "reference_proof": r"""對所有 $n$，$|\sin n|\le 1$，故 $0\le \left|\dfrac{\sin n}{n}\right|\le \dfrac{1}{n}$。
當 $n\to\infty$ 時 $\dfrac{1}{n}\to 0$。由夾擠定理，$\left|\dfrac{\sin n}{n}\right|\to 0$，因此 $\dfrac{\sin n}{n}\to 0$。$\blacksquare$""",
    },
    {
        "id": "A5",
        "topic": "極限",
        "difficulty": "基礎",
        "statement": r"用 $\varepsilon$-$N$ 定義證明 $\lim_{n\to\infty}\dfrac{1}{n}=0$。",
        "reference_proof": r"""要證：對任意 $\varepsilon>0$，存在 $N$，使得 $n\ge N \Rightarrow \left|\dfrac{1}{n}-0\right|<\varepsilon$。
$\left|\dfrac1n\right|=\dfrac1n<\varepsilon \iff n>\dfrac1\varepsilon$。
由阿基米德性質，存在正整數 $N>\dfrac1\varepsilon$。則 $n\ge N$ 時 $\dfrac1n\le\dfrac1N<\varepsilon$。$\blacksquare$""",
    },
    {
        "id": "A6",
        "topic": "極限",
        "difficulty": "中等",
        "statement": r"證明 $\lim_{n\to\infty}\dfrac{n}{2^n}=0$。",
        "reference_proof": r"""對 $n\ge 1$，由二項式定理 $2^n=(1+1)^n\ge \binom{n}{2}=\dfrac{n(n-1)}{2}$（$n\ge 2$）。
故 $0\le \dfrac{n}{2^n}\le \dfrac{n}{n(n-1)/2}=\dfrac{2}{n-1}$。
當 $n\to\infty$ 時 $\dfrac{2}{n-1}\to 0$，由夾擠定理得 $\dfrac{n}{2^n}\to 0$。$\blacksquare$""",
    },
    {
        "id": "A7",
        "topic": "極限",
        "difficulty": "中等",
        "statement": r"證明：收斂數列必有界。",
        "reference_proof": r"""設 $a_n\to L$。取 $\varepsilon=1$，存在 $N$ 使 $n\ge N \Rightarrow |a_n-L|<1$，
故 $n\ge N$ 時 $|a_n|\le |L|+1$。
其餘有限項 $a_1,\dots,a_{N-1}$ 只有有限個，令 $M=\max\{|a_1|,\dots,|a_{N-1}|,\,|L|+1\}$。
則對所有 $n$，$|a_n|\le M$，故數列有界。$\blacksquare$""",
    },
    {
        "id": "A8",
        "topic": "極限",
        "difficulty": "基礎",
        "statement": r"設 $\lim_{n\to\infty}a_n=L$，證明 $\lim_{n\to\infty}|a_n|=|L|$。",
        "reference_proof": r"""由反向三角不等式 $\big||a_n|-|L|\big|\le |a_n-L|$。
給定 $\varepsilon>0$，由 $a_n\to L$ 存在 $N$ 使 $n\ge N \Rightarrow |a_n-L|<\varepsilon$。
則 $n\ge N$ 時 $\big||a_n|-|L|\big|\le|a_n-L|<\varepsilon$，故 $|a_n|\to|L|$。
（注意逆命題不成立，例如 $a_n=(-1)^n$。）$\blacksquare$""",
    },
    {
        "id": "A9",
        "topic": "極限",
        "difficulty": "基礎",
        "statement": r"用 $\varepsilon$-$\delta$ 定義證明 $\lim_{x\to 1}(2x+1)=3$。",
        "reference_proof": r"""$|(2x+1)-3|=|2x-2|=2|x-1|$。
給定 $\varepsilon>0$，要 $2|x-1|<\varepsilon$，即 $|x-1|<\varepsilon/2$。
取 $\delta=\varepsilon/2$。則 $0<|x-1|<\delta \Rightarrow |(2x+1)-3|=2|x-1|<2\cdot\frac{\varepsilon}{2}=\varepsilon$。$\blacksquare$""",
    },
    {
        "id": "A10",
        "topic": "極限",
        "difficulty": "中等",
        "statement": r"證明 $\lim_{x\to 0}x\sin\dfrac{1}{x}=0$。",
        "reference_proof": r"""對 $x\ne 0$，$\left|\sin\dfrac1x\right|\le 1$，故 $0\le\left|x\sin\dfrac1x\right|\le |x|$。
給定 $\varepsilon>0$，取 $\delta=\varepsilon$。則 $0<|x|<\delta$ 時 $\left|x\sin\dfrac1x-0\right|\le|x|<\varepsilon$。
（等價地由夾擠定理，因 $-|x|\le x\sin\frac1x\le|x|$ 且兩端 $\to 0$。）$\blacksquare$""",
    },
]
