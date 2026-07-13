# -*- coding: utf-8 -*-
"""Topic E: sequences and series (monotone convergence / Cauchy / necessary condition
for convergence / convergence tests / absolute convergence / e).
English translation of src/problems_E.py."""

PROBLEMS = [
    {
        "id": "E1",
        "topic": "series",
        "difficulty": "medium",
        "statement": r"Prove the monotone convergence theorem: if the sequence $\{a_n\}$ is increasing and bounded above, then $\{a_n\}$ converges.",
        "reference_proof": r"""The set $\{a_n\}$ is nonempty and bounded above, so by completeness of the reals (least upper bound axiom) $L=\sup\{a_n\}$ exists.
Claim: $a_n\to L$. Given $\varepsilon>0$, since $L-\varepsilon$ is not an upper bound, there exists $N$ with $a_N>L-\varepsilon$.
Since $\{a_n\}$ is increasing, $a_n\ge a_N>L-\varepsilon$ for $n\ge N$; also $a_n\le L<L+\varepsilon$.
Hence $|a_n-L|<\varepsilon$ for $n\ge N$, i.e. $a_n\to L$. $\blacksquare$""",
    },
    {
        "id": "E2",
        "topic": "series",
        "difficulty": "basic",
        "statement": r"Prove that every convergent sequence is a Cauchy sequence.",
        "reference_proof": r"""Suppose $a_n\to L$. Given $\varepsilon>0$, there exists $N$ such that $n\ge N \Rightarrow |a_n-L|<\dfrac{\varepsilon}{2}$.
For any $m,n\ge N$, by the triangle inequality
$$|a_n-a_m|\le |a_n-L|+|L-a_m|<\frac{\varepsilon}{2}+\frac{\varepsilon}{2}=\varepsilon.$$
Hence $\{a_n\}$ is a Cauchy sequence. $\blacksquare$""",
    },
    {
        "id": "E3",
        "topic": "series",
        "difficulty": "basic",
        "statement": r"Prove: if the series $\sum a_n$ converges, then $a_n\to 0$.",
        "reference_proof": r"""Let the partial sums be $S_n=\sum_{k=1}^n a_k$; since $\sum a_n$ converges, $S_n\to S$ (some finite value).
Then $S_{n-1}\to S$ as well. Hence
$$a_n=S_n-S_{n-1}\to S-S=0.$$
(Note the converse fails, e.g. the harmonic series: $a_n=1/n\to0$ but $\sum 1/n$ diverges.) $\blacksquare$""",
    },
    {
        "id": "E4",
        "topic": "series",
        "difficulty": "medium",
        "statement": r"Prove that $\sum_{n=1}^\infty \dfrac{1}{n^2}$ converges.",
        "reference_proof": r"""The partial sums $S_n=\sum_{k=1}^n \dfrac{1}{k^2}$ form an increasing sequence (all terms positive).
For $k\ge 2$, use the telescoping bound $\dfrac{1}{k^2}\le \dfrac{1}{k(k-1)}=\dfrac{1}{k-1}-\dfrac{1}{k}$. Hence
$$S_n\le 1+\sum_{k=2}^n\Big(\frac{1}{k-1}-\frac1k\Big)=1+\Big(1-\frac1n\Big)<2.$$
$\{S_n\}$ is increasing and bounded above by $2$, so it converges by the monotone convergence theorem. $\blacksquare$""",
    },
    {
        "id": "E5",
        "topic": "series",
        "difficulty": "medium",
        "statement": r"Prove that the harmonic series $\sum_{n=1}^\infty \dfrac{1}{n}$ diverges.",
        "reference_proof": r"""Let $S_n$ be the partial sums. Consider
$$S_{2n}-S_n=\sum_{k=n+1}^{2n}\frac1k.$$
This sum has $n$ terms, each $\ge \dfrac{1}{2n}$, so $S_{2n}-S_n\ge n\cdot\dfrac{1}{2n}=\dfrac12$.
If $\{S_n\}$ converged it would be Cauchy, forcing $S_{2n}-S_n\to 0$, contradicting $\ge\frac12$.
Hence $\{S_n\}$ does not converge, i.e. $\sum \frac1n$ diverges. $\blacksquare$""",
    },
    {
        "id": "E6",
        "topic": "series",
        "difficulty": "advanced",
        "statement": r"Prove the ratio test: if $a_n\ne0$ and $\lim_{n\to\infty}\left|\dfrac{a_{n+1}}{a_n}\right|=L<1$, then $\sum a_n$ converges absolutely.",
        "reference_proof": r"""Pick $r$ with $L<r<1$. By the definition of the limit, there exists $N$ such that $n\ge N \Rightarrow \left|\dfrac{a_{n+1}}{a_n}\right|<r$.
By induction, $|a_n|\le |a_N|\,r^{\,n-N}$ for $n\ge N$.
Compare with the geometric series: $\sum_{n\ge N}|a_N|r^{n-N}=|a_N|\cdot\dfrac{1}{1-r}<\infty$ (since $0<r<1$).
By the comparison test, $\sum |a_n|$ converges, i.e. $\sum a_n$ converges absolutely. $\blacksquare$""",
    },
    {
        "id": "E7",
        "topic": "series",
        "difficulty": "medium",
        "statement": r"Prove: an absolutely convergent series converges ($\sum|a_n|$ converges $\Rightarrow \sum a_n$ converges).",
        "reference_proof": r"""Let $b_n=a_n+|a_n|$; then $0\le b_n\le 2|a_n|$.
Since $\sum 2|a_n|$ converges, the comparison test gives that $\sum b_n$ converges (a series of nonnegative terms).
Since $a_n=b_n-|a_n|$ is the difference of two convergent series, $\sum a_n=\sum b_n-\sum|a_n|$ converges. $\blacksquare$""",
    },
    {
        "id": "E8",
        "topic": "series",
        "difficulty": "advanced",
        "statement": r"Prove the Leibniz alternating series test: if $b_n\ge0$ is decreasing and $b_n\to0$, then $\sum(-1)^{n+1}b_n$ converges.",
        "reference_proof": r"""Let $S_n$ be the partial sums. Consider the even- and odd-indexed subsequences.
$S_{2n+2}-S_{2n}=b_{2n+1}-b_{2n+2}\ge0$ (decreasing), so $\{S_{2n}\}$ is increasing;
$S_{2n+1}-S_{2n-1}=-b_{2n}+b_{2n+1}\le0$, so $\{S_{2n+1}\}$ is decreasing.
Also $S_{2n+1}-S_{2n}=b_{2n+1}\ge0$, so $S_{2n}\le S_{2n+1}\le S_1$ and $S_{2n}\ge S_2$; both subsequences are monotone and bounded, hence convergent.
Since $S_{2n+1}-S_{2n}=b_{2n+1}\to0$, both subsequences have the same limit $S$, so $S_n\to S$ and the series converges. $\blacksquare$""",
    },
    {
        "id": "E9",
        "topic": "series",
        "difficulty": "advanced",
        "statement": r"Prove that the sequence $a_n=\left(1+\dfrac1n\right)^n$ converges (i.e. the limit $e$ exists).",
        "reference_proof": r"""By the binomial theorem,
$$a_n=\sum_{k=0}^n\binom{n}{k}\frac{1}{n^k}=\sum_{k=0}^n\frac{1}{k!}\prod_{j=0}^{k-1}\Big(1-\frac{j}{n}\Big).$$
(Increasing) As $n$ grows, each factor $1-\frac{j}{n}$ increases and there are more terms, so $a_{n+1}\ge a_n$.
(Bounded above) Each product is $\le1$, so $a_n\le\sum_{k=0}^n\dfrac{1}{k!}\le 1+\sum_{k=1}^n\dfrac{1}{2^{k-1}}<1+2=3$.
$\{a_n\}$ is increasing and bounded above by $3$, so it converges by the monotone convergence theorem. $\blacksquare$""",
    },
    {
        "id": "E10",
        "topic": "series",
        "difficulty": "basic",
        "statement": r"Prove the comparison test: if $0\le a_n\le b_n$ and $\sum b_n$ converges, then $\sum a_n$ converges.",
        "reference_proof": r"""Let $A_n=\sum_{k=1}^n a_k$ and $B_n=\sum_{k=1}^n b_k$. Since all terms are nonnegative, both are increasing.
Since $\sum b_n$ converges, $B_n\to B$ and $B_n\le B$. From $a_k\le b_k$ we get $A_n\le B_n\le B$.
Hence $\{A_n\}$ is increasing and bounded above by $B$, so it converges by the monotone convergence theorem, i.e. $\sum a_n$ converges. $\blacksquare$""",
    },
]
