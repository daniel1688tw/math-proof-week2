# -*- coding: utf-8 -*-
"""Topic A: limits of sequences and functions (epsilon-N / epsilon-delta / squeeze /
limit laws / boundedness). English translation of src/problems_A.py; all reference
proofs hand-written and verified by Claude."""

PROBLEMS = [
    {
        "id": "A1",
        "topic": "limits",
        "difficulty": "medium",
        "statement": r"Prove that $\lim_{n\to\infty}\sqrt[n]{n}=1$.",
        "reference_proof": r"""Let $a_n=\sqrt[n]{n}-1\ge 0$ (since $\sqrt[n]{n}\ge 1$ for $n\ge 1$). Then $n=(1+a_n)^n$.
By the binomial theorem, for $n\ge 2$,
$$n=(1+a_n)^n\ge \binom{n}{2}a_n^2=\frac{n(n-1)}{2}a_n^2.$$
Hence $a_n^2\le \dfrac{2}{n-1}$, i.e. $0\le a_n\le \sqrt{\dfrac{2}{n-1}}$.
The right-hand side tends to $0$ as $n\to\infty$, so by the squeeze theorem $a_n\to 0$, and therefore $\sqrt[n]{n}=1+a_n\to 1$. $\blacksquare$""",
    },
    {
        "id": "A2",
        "topic": "limits",
        "difficulty": "medium",
        "statement": r"Prove by the $\varepsilon$-$\delta$ definition that $\lim_{x\to 2}x^2=4$.",
        "reference_proof": r"""To show: for every $\varepsilon>0$ there exists $\delta>0$ such that $0<|x-2|<\delta \Rightarrow |x^2-4|<\varepsilon$.
First factor: $|x^2-4|=|x-2|\,|x+2|$.
Restrict $|x-2|<1$ first, so $1<x<3$ and hence $|x+2|<5$.
Thus $|x^2-4|<5|x-2|$ whenever $|x-2|<1$.
Take $\delta=\min\{1,\varepsilon/5\}$. Then $0<|x-2|<\delta$ implies $|x^2-4|<5\cdot\frac{\varepsilon}{5}=\varepsilon$. $\blacksquare$""",
    },
    {
        "id": "A3",
        "topic": "limits",
        "difficulty": "medium",
        "statement": r"Suppose $\lim_{n\to\infty}a_n=L$ and $\lim_{n\to\infty}b_n=M$. Prove that $\lim_{n\to\infty}(a_n+b_n)=L+M$.",
        "reference_proof": r"""To show: for every $\varepsilon>0$ there exists $N$ such that $n\ge N \Rightarrow |(a_n+b_n)-(L+M)|<\varepsilon$.
Key inequality (triangle inequality): $|(a_n+b_n)-(L+M)|\le |a_n-L|+|b_n-M|$.
Since $a_n\to L$: there exists $N_1$ with $n\ge N_1 \Rightarrow |a_n-L|<\varepsilon/2$.
Since $b_n\to M$: there exists $N_2$ with $n\ge N_2 \Rightarrow |b_n-M|<\varepsilon/2$.
Take $N=\max\{N_1,N_2\}$; for $n\ge N$ both hold, so the sum is $<\varepsilon/2+\varepsilon/2=\varepsilon$. $\blacksquare$""",
    },
    {
        "id": "A4",
        "topic": "limits",
        "difficulty": "basic",
        "statement": r"Prove that $\lim_{n\to\infty}\dfrac{\sin n}{n}=0$.",
        "reference_proof": r"""For all $n$, $|\sin n|\le 1$, so $0\le \left|\dfrac{\sin n}{n}\right|\le \dfrac{1}{n}$.
As $n\to\infty$, $\dfrac{1}{n}\to 0$. By the squeeze theorem $\left|\dfrac{\sin n}{n}\right|\to 0$, hence $\dfrac{\sin n}{n}\to 0$. $\blacksquare$""",
    },
    {
        "id": "A5",
        "topic": "limits",
        "difficulty": "basic",
        "statement": r"Prove by the $\varepsilon$-$N$ definition that $\lim_{n\to\infty}\dfrac{1}{n}=0$.",
        "reference_proof": r"""To show: for every $\varepsilon>0$ there exists $N$ such that $n\ge N \Rightarrow \left|\dfrac{1}{n}-0\right|<\varepsilon$.
$\left|\dfrac1n\right|=\dfrac1n<\varepsilon \iff n>\dfrac1\varepsilon$.
By the Archimedean property there is a positive integer $N>\dfrac1\varepsilon$. Then for $n\ge N$, $\dfrac1n\le\dfrac1N<\varepsilon$. $\blacksquare$""",
    },
    {
        "id": "A6",
        "topic": "limits",
        "difficulty": "medium",
        "statement": r"Prove that $\lim_{n\to\infty}\dfrac{n}{2^n}=0$.",
        "reference_proof": r"""For $n\ge 1$, by the binomial theorem $2^n=(1+1)^n\ge \binom{n}{2}=\dfrac{n(n-1)}{2}$ (for $n\ge 2$).
Hence $0\le \dfrac{n}{2^n}\le \dfrac{n}{n(n-1)/2}=\dfrac{2}{n-1}$.
As $n\to\infty$, $\dfrac{2}{n-1}\to 0$, so by the squeeze theorem $\dfrac{n}{2^n}\to 0$. $\blacksquare$""",
    },
    {
        "id": "A7",
        "topic": "limits",
        "difficulty": "medium",
        "statement": r"Prove that every convergent sequence is bounded.",
        "reference_proof": r"""Suppose $a_n\to L$. Take $\varepsilon=1$: there exists $N$ such that $n\ge N \Rightarrow |a_n-L|<1$,
so $|a_n|\le |L|+1$ for $n\ge N$.
The remaining terms $a_1,\dots,a_{N-1}$ are finitely many; let $M=\max\{|a_1|,\dots,|a_{N-1}|,\,|L|+1\}$.
Then $|a_n|\le M$ for all $n$, so the sequence is bounded. $\blacksquare$""",
    },
    {
        "id": "A8",
        "topic": "limits",
        "difficulty": "basic",
        "statement": r"Suppose $\lim_{n\to\infty}a_n=L$. Prove that $\lim_{n\to\infty}|a_n|=|L|$.",
        "reference_proof": r"""By the reverse triangle inequality, $\big||a_n|-|L|\big|\le |a_n-L|$.
Given $\varepsilon>0$, since $a_n\to L$ there exists $N$ such that $n\ge N \Rightarrow |a_n-L|<\varepsilon$.
Then for $n\ge N$, $\big||a_n|-|L|\big|\le|a_n-L|<\varepsilon$, so $|a_n|\to|L|$.
(Note the converse fails, e.g. $a_n=(-1)^n$.) $\blacksquare$""",
    },
    {
        "id": "A9",
        "topic": "limits",
        "difficulty": "basic",
        "statement": r"Prove by the $\varepsilon$-$\delta$ definition that $\lim_{x\to 1}(2x+1)=3$.",
        "reference_proof": r"""$|(2x+1)-3|=|2x-2|=2|x-1|$.
Given $\varepsilon>0$, we need $2|x-1|<\varepsilon$, i.e. $|x-1|<\varepsilon/2$.
Take $\delta=\varepsilon/2$. Then $0<|x-1|<\delta \Rightarrow |(2x+1)-3|=2|x-1|<2\cdot\frac{\varepsilon}{2}=\varepsilon$. $\blacksquare$""",
    },
    {
        "id": "A10",
        "topic": "limits",
        "difficulty": "medium",
        "statement": r"Prove that $\lim_{x\to 0}x\sin\dfrac{1}{x}=0$.",
        "reference_proof": r"""For $x\ne 0$, $\left|\sin\dfrac1x\right|\le 1$, so $0\le\left|x\sin\dfrac1x\right|\le |x|$.
Given $\varepsilon>0$, take $\delta=\varepsilon$. Then for $0<|x|<\delta$, $\left|x\sin\dfrac1x-0\right|\le|x|<\varepsilon$.
(Equivalently by the squeeze theorem, since $-|x|\le x\sin\frac1x\le|x|$ and both sides $\to 0$.) $\blacksquare$""",
    },
]
