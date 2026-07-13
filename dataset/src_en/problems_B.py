# -*- coding: utf-8 -*-
"""Topic B: continuity (IVT / extreme value theorem / uniform continuity /
definition of continuity / composition). English translation of src/problems_B.py."""

PROBLEMS = [
    {
        "id": "B1",
        "topic": "continuity",
        "difficulty": "medium",
        "statement": r"Suppose $f$ is continuous on $[a,b]$ and $f(a)f(b)<0$. Prove that there exists $c\in(a,b)$ with $f(c)=0$.",
        "reference_proof": r"""Without loss of generality assume $f(a)<0<f(b)$. Let $S=\{x\in[a,b]:f(x)<0\}$.
$S$ is nonempty (it contains $a$) and bounded above by $b$, so by completeness of the reals $c=\sup S$ exists and $c\in[a,b]$.
Claim: $f(c)=0$.
(i) If $f(c)>0$, then by continuity there is $\delta>0$ with $f>0$ on $(c-\delta,c]$, so $c-\delta$ is also an upper bound of $S$, contradicting $c=\sup S$.
(ii) If $f(c)<0$, then $c<b$, and by continuity there is $\delta>0$ with $f<0$ on $[c,c+\delta)$, so $S$ contains points greater than $c$, a contradiction.
Hence $f(c)=0$, and since $f(a),f(b)\ne 0$ we get $c\in(a,b)$. $\blacksquare$""",
    },
    {
        "id": "B2",
        "topic": "continuity",
        "difficulty": "advanced",
        "statement": r"Prove that a continuous function $f$ on $[a,b]$ attains a maximum value (extreme value theorem).",
        "reference_proof": r"""Step 1 (boundedness): if $f$ were unbounded above, there would exist $x_n\in[a,b]$ with $f(x_n)>n$. By Bolzano-Weierstrass, $\{x_n\}$ has a convergent subsequence $x_{n_k}\to x^*\in[a,b]$. By continuity $f(x_{n_k})\to f(x^*)$ (finite), contradicting $f(x_{n_k})>n_k\to\infty$. So $f$ is bounded above.
Step 2 (attainment): let $M=\sup_{[a,b]}f$ (exists and is finite). Choose $y_n\in[a,b]$ with $f(y_n)\to M$. By B-W take a convergent subsequence $y_{n_k}\to y^*\in[a,b]$; by continuity $f(y^*)=\lim f(y_{n_k})=M$.
Hence $f$ attains its maximum $M$ at $y^*$. $\blacksquare$""",
    },
    {
        "id": "B3",
        "topic": "continuity",
        "difficulty": "advanced",
        "statement": r"Prove that a continuous function $f$ on $[a,b]$ is uniformly continuous (Heine-Cantor theorem).",
        "reference_proof": r"""By contradiction. Suppose $f$ is not uniformly continuous. Then there exists $\varepsilon_0>0$ such that for every $n$ there are $x_n,y_n\in[a,b]$ with
$$|x_n-y_n|<\tfrac1n \quad\text{but}\quad |f(x_n)-f(y_n)|\ge \varepsilon_0.$$
By Bolzano-Weierstrass, $\{x_n\}$ has a convergent subsequence $x_{n_k}\to x^*\in[a,b]$.
Since $|x_{n_k}-y_{n_k}|<\frac{1}{n_k}\to 0$, we also have $y_{n_k}\to x^*$.
By continuity of $f$ at $x^*$, $f(x_{n_k})\to f(x^*)$ and $f(y_{n_k})\to f(x^*)$,
so $|f(x_{n_k})-f(y_{n_k})|\to 0$, contradicting $\ge\varepsilon_0$. $\blacksquare$""",
    },
    {
        "id": "B4",
        "topic": "continuity",
        "difficulty": "medium",
        "statement": r"Prove that $f(x)=x^2$ is not uniformly continuous on $\mathbb{R}$.",
        "reference_proof": r"""To show: there exists $\varepsilon_0>0$ such that for every $\delta>0$ we can find $x,y$ with $|x-y|<\delta$ but $|f(x)-f(y)|\ge\varepsilon_0$.
Take $\varepsilon_0=1$. For any $\delta>0$, let $x=n+\dfrac{\delta}{2}$ and $y=n$ ($n$ a large integer to be chosen).
Then $|x-y|=\dfrac{\delta}{2}<\delta$, while
$$|x^2-y^2|=|x-y|\,|x+y|=\frac{\delta}{2}\Big(2n+\frac{\delta}{2}\Big)\ge \delta n.$$
Choosing $n$ large enough that $\delta n\ge 1$ gives $|f(x)-f(y)|\ge 1$. Hence $f$ is not uniformly continuous.
(The essential reason: $|x+y|$ is unbounded, so no single $\delta$ can work everywhere.) $\blacksquare$""",
    },
    {
        "id": "B5",
        "topic": "continuity",
        "difficulty": "basic",
        "statement": r"Prove by the $\varepsilon$-$\delta$ definition that $f(x)=x^2$ is continuous at an arbitrary point $x=a$.",
        "reference_proof": r"""To show: for every $\varepsilon>0$ there exists $\delta>0$ such that $|x-a|<\delta \Rightarrow |x^2-a^2|<\varepsilon$.
$|x^2-a^2|=|x-a|\,|x+a|$. Restrict $|x-a|<1$ first; then $|x+a|\le |x-a|+2|a|<1+2|a|$.
Hence $|x^2-a^2|<(1+2|a|)|x-a|$.
Take $\delta=\min\Big\{1,\dfrac{\varepsilon}{1+2|a|}\Big\}$; then $|x-a|<\delta$ implies $|x^2-a^2|<\varepsilon$. $\blacksquare$""",
    },
    {
        "id": "B6",
        "topic": "continuity",
        "difficulty": "medium",
        "statement": r"Suppose $f$ is continuous at $x_0$. Prove that for every sequence $x_n\to x_0$ we have $f(x_n)\to f(x_0)$ (sequential criterion for continuity).",
        "reference_proof": r"""Given $\varepsilon>0$. Since $f$ is continuous at $x_0$, there exists $\delta>0$ such that $|x-x_0|<\delta \Rightarrow |f(x)-f(x_0)|<\varepsilon$.
Since $x_n\to x_0$, for this $\delta$ there exists $N$ such that $n\ge N \Rightarrow |x_n-x_0|<\delta$.
Then for $n\ge N$, $|f(x_n)-f(x_0)|<\varepsilon$, i.e. $f(x_n)\to f(x_0)$. $\blacksquare$""",
    },
    {
        "id": "B7",
        "topic": "continuity",
        "difficulty": "medium",
        "statement": r"Prove that every real polynomial of odd degree $p(x)=x^{2k+1}+c_{2k}x^{2k}+\cdots+c_0$ has at least one real root.",
        "reference_proof": r"""$p$ is a polynomial, hence continuous on $\mathbb{R}$. Consider its behavior as $x\to\pm\infty$:
since the leading term is the odd power $x^{2k+1}$, $\lim_{x\to+\infty}p(x)=+\infty$ and $\lim_{x\to-\infty}p(x)=-\infty$.
So there exists $b$ with $p(b)>0$ and $a<b$ with $p(a)<0$.
$p$ is continuous on $[a,b]$ with $p(a)<0<p(b)$, so by the intermediate value theorem there is $c\in(a,b)$ with $p(c)=0$. $\blacksquare$""",
    },
    {
        "id": "B8",
        "topic": "continuity",
        "difficulty": "advanced",
        "statement": r"Prove that a continuous function on $[a,b]$ is bounded (boundedness theorem).",
        "reference_proof": r"""By contradiction. Suppose $f$ is unbounded; then for each $n$ there exists $x_n\in[a,b]$ with $|f(x_n)|>n$.
$\{x_n\}\subset[a,b]$ is bounded, so by Bolzano-Weierstrass it has a convergent subsequence $x_{n_k}\to x^*$,
and since $[a,b]$ is closed, $x^*\in[a,b]$.
By continuity of $f$ at $x^*$, $f(x_{n_k})\to f(x^*)$, so $\{f(x_{n_k})\}$ converges and is therefore bounded;
but $|f(x_{n_k})|>n_k\to\infty$ is unbounded, a contradiction. Hence $f$ is bounded. $\blacksquare$""",
    },
    {
        "id": "B9",
        "topic": "continuity",
        "difficulty": "medium",
        "statement": r"Suppose $g$ is continuous at $x_0$ and $f$ is continuous at $g(x_0)$. Prove that $f\circ g$ is continuous at $x_0$.",
        "reference_proof": r"""Let $y_0=g(x_0)$. Given $\varepsilon>0$.
Since $f$ is continuous at $y_0$, there exists $\eta>0$ such that $|y-y_0|<\eta \Rightarrow |f(y)-f(y_0)|<\varepsilon$.
Since $g$ is continuous at $x_0$, for this $\eta$ there exists $\delta>0$ such that $|x-x_0|<\delta \Rightarrow |g(x)-y_0|<\eta$.
Then $|x-x_0|<\delta \Rightarrow |g(x)-y_0|<\eta \Rightarrow |f(g(x))-f(y_0)|<\varepsilon$, i.e. $f\circ g$ is continuous at $x_0$. $\blacksquare$""",
    },
    {
        "id": "B10",
        "topic": "continuity",
        "difficulty": "advanced",
        "statement": r"Suppose $f$ is continuous on $[0,1]$ with $f(0)=f(1)$. Prove that there exists $c\in[0,\tfrac12]$ such that $f(c)=f(c+\tfrac12)$.",
        "reference_proof": r"""Define $g(x)=f(x+\tfrac12)-f(x)$; $g$ is continuous on $[0,\tfrac12]$.
Evaluate the endpoints: $g(0)=f(\tfrac12)-f(0)$ and $g(\tfrac12)=f(1)-f(\tfrac12)$.
Adding: $g(0)+g(\tfrac12)=f(1)-f(0)=0$, so $g(\tfrac12)=-g(0)$.
If $g(0)=0$, take $c=0$. Otherwise $g(0)$ and $g(\tfrac12)$ have opposite signs, and by the intermediate value theorem there is $c\in(0,\tfrac12)$ with $g(c)=0$,
i.e. $f(c)=f(c+\tfrac12)$. $\blacksquare$""",
    },
]
