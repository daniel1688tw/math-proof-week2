# -*- coding: utf-8 -*-
"""主題 E：數列與級數（單調有界 / Cauchy / 收斂必要條件 / 判別法 / 絕對收斂 / e）。
所有參考解由 Claude 手寫並驗證數學正確性。"""

PROBLEMS = [
    {
        "id": "E1",
        "topic": "級數",
        "difficulty": "中等",
        "statement": r"證明單調有界定理：若數列 $\{a_n\}$ 遞增且有上界，則 $\{a_n\}$ 收斂。",
        "reference_proof": r"""集合 $\{a_n\}$ 非空且有上界，由實數完備性（最小上界公理）$L=\sup\{a_n\}$ 存在。
斷言 $a_n\to L$。給定 $\varepsilon>0$，因 $L-\varepsilon$ 不是上界，存在 $N$ 使 $a_N>L-\varepsilon$。
由 $\{a_n\}$ 遞增，$n\ge N$ 時 $a_n\ge a_N>L-\varepsilon$；又 $a_n\le L<L+\varepsilon$。
故 $n\ge N$ 時 $|a_n-L|<\varepsilon$，即 $a_n\to L$。$\blacksquare$""",
    },
    {
        "id": "E2",
        "topic": "級數",
        "difficulty": "基礎",
        "statement": r"證明：收斂數列必為 Cauchy 數列。",
        "reference_proof": r"""設 $a_n\to L$。給定 $\varepsilon>0$，存在 $N$ 使 $n\ge N \Rightarrow |a_n-L|<\dfrac{\varepsilon}{2}$。
對任意 $m,n\ge N$，由三角不等式
$$|a_n-a_m|\le |a_n-L|+|L-a_m|<\frac{\varepsilon}{2}+\frac{\varepsilon}{2}=\varepsilon.$$
故 $\{a_n\}$ 為 Cauchy 數列。$\blacksquare$""",
    },
    {
        "id": "E3",
        "topic": "級數",
        "difficulty": "基礎",
        "statement": r"證明：若級數 $\sum a_n$ 收斂，則 $a_n\to 0$。",
        "reference_proof": r"""設部分和 $S_n=\sum_{k=1}^n a_k$，由 $\sum a_n$ 收斂知 $S_n\to S$（某有限值）。
則 $S_{n-1}\to S$ 亦成立。於是
$$a_n=S_n-S_{n-1}\to S-S=0.$$
（注意逆命題不成立，如調和級數 $a_n=1/n\to0$ 但 $\sum 1/n$ 發散。）$\blacksquare$""",
    },
    {
        "id": "E4",
        "topic": "級數",
        "difficulty": "中等",
        "statement": r"證明 $\sum_{n=1}^\infty \dfrac{1}{n^2}$ 收斂。",
        "reference_proof": r"""部分和 $S_n=\sum_{k=1}^n \dfrac{1}{k^2}$ 為遞增數列（每項為正）。
對 $k\ge 2$，用裂項上界 $\dfrac{1}{k^2}\le \dfrac{1}{k(k-1)}=\dfrac{1}{k-1}-\dfrac{1}{k}$。故
$$S_n\le 1+\sum_{k=2}^n\Big(\frac{1}{k-1}-\frac1k\Big)=1+\Big(1-\frac1n\Big)<2.$$
$\{S_n\}$ 遞增且有上界 $2$，由單調有界定理收斂。$\blacksquare$""",
    },
    {
        "id": "E5",
        "topic": "級數",
        "difficulty": "中等",
        "statement": r"證明調和級數 $\sum_{n=1}^\infty \dfrac{1}{n}$ 發散。",
        "reference_proof": r"""設部分和 $S_n$。考慮
$$S_{2n}-S_n=\sum_{k=n+1}^{2n}\frac1k.$$
此和共 $n$ 項，每項 $\ge \dfrac{1}{2n}$，故 $S_{2n}-S_n\ge n\cdot\dfrac{1}{2n}=\dfrac12$。
若 $\{S_n\}$ 收斂則為 Cauchy 數列，$S_{2n}-S_n\to 0$，與 $\ge\frac12$ 矛盾。
故 $\{S_n\}$ 不收斂，即 $\sum \frac1n$ 發散。$\blacksquare$""",
    },
    {
        "id": "E6",
        "topic": "級數",
        "difficulty": "進階",
        "statement": r"證明比值判別法：若 $a_n\ne0$ 且 $\lim_{n\to\infty}\left|\dfrac{a_{n+1}}{a_n}\right|=L<1$，則 $\sum a_n$ 絕對收斂。",
        "reference_proof": r"""取 $r$ 使 $L<r<1$。由極限定義，存在 $N$ 使 $n\ge N \Rightarrow \left|\dfrac{a_{n+1}}{a_n}\right|<r$。
遞推得對 $n\ge N$，$|a_n|\le |a_N|\,r^{\,n-N}$。
比較幾何級數：$\sum_{n\ge N}|a_N|r^{n-N}=|a_N|\cdot\dfrac{1}{1-r}<\infty$（因 $0<r<1$）。
由比較判別法，$\sum |a_n|$ 收斂，即 $\sum a_n$ 絕對收斂。$\blacksquare$""",
    },
    {
        "id": "E7",
        "topic": "級數",
        "difficulty": "中等",
        "statement": r"證明：絕對收斂的級數必收斂（$\sum|a_n|$ 收斂 $\Rightarrow \sum a_n$ 收斂）。",
        "reference_proof": r"""令 $b_n=a_n+|a_n|$，則 $0\le b_n\le 2|a_n|$。
因 $\sum 2|a_n|$ 收斂，由比較判別法 $\sum b_n$ 收斂（非負項級數）。
而 $a_n=b_n-|a_n|$，為兩個收斂級數之差，故 $\sum a_n=\sum b_n-\sum|a_n|$ 收斂。$\blacksquare$""",
    },
    {
        "id": "E8",
        "topic": "級數",
        "difficulty": "進階",
        "statement": r"證明 Leibniz 交錯級數判別法：若 $b_n\ge0$ 遞減且 $b_n\to0$，則 $\sum(-1)^{n+1}b_n$ 收斂。",
        "reference_proof": r"""設部分和 $S_n$。考慮偶數項與奇數項子列。
$S_{2n+2}-S_{2n}=b_{2n+1}-b_{2n+2}\ge0$（遞減），故 $\{S_{2n}\}$ 遞增；
$S_{2n+1}-S_{2n-1}=-b_{2n}+b_{2n+1}\le0$，故 $\{S_{2n+1}\}$ 遞減。
又 $S_{2n+1}-S_{2n}=b_{2n+1}\ge0$，故 $S_{2n}\le S_{2n+1}\le S_1$、$S_{2n}\ge S_2$，兩子列皆單調有界故收斂。
因 $S_{2n+1}-S_{2n}=b_{2n+1}\to0$，兩子列同極限 $S$，故 $S_n\to S$，級數收斂。$\blacksquare$""",
    },
    {
        "id": "E9",
        "topic": "級數",
        "difficulty": "進階",
        "statement": r"證明數列 $a_n=\left(1+\dfrac1n\right)^n$ 收斂（即極限 $e$ 存在）。",
        "reference_proof": r"""由二項式定理，
$$a_n=\sum_{k=0}^n\binom{n}{k}\frac{1}{n^k}=\sum_{k=0}^n\frac{1}{k!}\prod_{j=0}^{k-1}\Big(1-\frac{j}{n}\Big).$$
（遞增）由 $n$ 增大時每個因子 $1-\frac{j}{n}$ 增大、且項數增多，故 $a_{n+1}\ge a_n$。
（有上界）每個乘積 $\le1$，故 $a_n\le\sum_{k=0}^n\dfrac{1}{k!}\le 1+\sum_{k=1}^n\dfrac{1}{2^{k-1}}<1+2=3$。
$\{a_n\}$ 遞增且有上界 $3$，由單調有界定理收斂。$\blacksquare$""",
    },
    {
        "id": "E10",
        "topic": "級數",
        "difficulty": "基礎",
        "statement": r"證明比較判別法：若 $0\le a_n\le b_n$ 且 $\sum b_n$ 收斂，則 $\sum a_n$ 收斂。",
        "reference_proof": r"""設 $A_n=\sum_{k=1}^n a_k$、$B_n=\sum_{k=1}^n b_k$。因各項非負，兩者皆遞增。
由 $\sum b_n$ 收斂，$B_n\to B$ 且 $B_n\le B$。由 $a_k\le b_k$ 得 $A_n\le B_n\le B$。
故 $\{A_n\}$ 遞增且有上界 $B$，由單調有界定理收斂，即 $\sum a_n$ 收斂。$\blacksquare$""",
    },
]
