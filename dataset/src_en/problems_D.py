# -*- coding: utf-8 -*-
"""Topic D: integration (FTC / mean value theorem for integrals / integrability /
monotonicity of the integral / estimates / improper integrals / Cauchy-Schwarz).
English translation of src/problems_D.py."""

PROBLEMS = [
    {
        "id": "D1",
        "topic": "integration",
        "difficulty": "medium",
        "statement": r"Suppose $f$ is continuous on $[a,b]$, $f\ge 0$, and $\int_a^b f(x)\,dx=0$. Prove that $f\equiv 0$.",
        "reference_proof": r"""By contradiction. Suppose there is $x_0\in[a,b]$ with $f(x_0)>0$.
By continuity, taking $\varepsilon=\dfrac{f(x_0)}{2}>0$, there is a subinterval $[c,d]\subset[a,b]$ (containing $x_0$, of length $d-c>0$) on which $f(x)>\dfrac{f(x_0)}{2}$.
Since $f\ge 0$,
$$\int_a^b f\ge \int_c^d f\ge \frac{f(x_0)}{2}(d-c)>0,$$
contradicting $\int_a^b f=0$. Hence $f(x)=0$ for all $x$. $\blacksquare$""",
    },
    {
        "id": "D2",
        "topic": "integration",
        "difficulty": "advanced",
        "statement": r"Prove the fundamental theorem of calculus (part 1): if $f$ is continuous on $[a,b]$ and $F(x)=\int_a^x f(t)\,dt$, then $F'(x)=f(x)$.",
        "reference_proof": r"""Fix $x\in[a,b]$. For $h\ne 0$,
$$\frac{F(x+h)-F(x)}{h}=\frac{1}{h}\int_x^{x+h}f(t)\,dt.$$
Subtract $f(x)$ using $\frac1h\int_x^{x+h}f(x)\,dt=f(x)$:
$$\left|\frac{F(x+h)-F(x)}{h}-f(x)\right|=\left|\frac1h\int_x^{x+h}\big(f(t)-f(x)\big)\,dt\right|\le \sup_{|t-x|\le|h|}|f(t)-f(x)|.$$
By continuity of $f$ at $x$, the right-hand side $\to 0$ as $h\to 0$. Hence $F'(x)=f(x)$. $\blacksquare$""",
    },
    {
        "id": "D3",
        "topic": "integration",
        "difficulty": "medium",
        "statement": r"Prove the first mean value theorem for integrals: if $f$ is continuous on $[a,b]$, then there exists $c\in[a,b]$ with $\int_a^b f(x)\,dx=f(c)(b-a)$.",
        "reference_proof": r"""$f$ is continuous on $[a,b]$, so by the extreme value theorem it attains a minimum $m$ and maximum $M$, i.e. $m\le f(x)\le M$.
Monotonicity of the integral gives $m(b-a)\le\int_a^b f\le M(b-a)$, so the average value
$$\mu=\frac{1}{b-a}\int_a^b f\in[m,M].$$
By the intermediate value theorem (a continuous function attains every value in $[m,M]$), there exists $c\in[a,b]$ with $f(c)=\mu$, i.e. $\int_a^b f=f(c)(b-a)$. $\blacksquare$""",
    },
    {
        "id": "D4",
        "topic": "integration",
        "difficulty": "basic",
        "statement": r"Suppose $f,g$ are integrable on $[a,b]$ and $f(x)\le g(x)$. Prove $\int_a^b f\le \int_a^b g$ (monotonicity of the integral).",
        "reference_proof": r"""Let $h=g-f\ge 0$; $h$ is integrable on $[a,b]$.
For any partition $P$, since $h\ge 0$, its lower sum $L(h,P)=\sum m_i\Delta x_i\ge 0$ (each $m_i=\inf h\ge 0$).
Hence $\int_a^b h=\sup_P L(h,P)\ge 0$.
By linearity of the integral, $\int_a^b g-\int_a^b f=\int_a^b h\ge 0$, i.e. $\int_a^b f\le\int_a^b g$. $\blacksquare$""",
    },
    {
        "id": "D5",
        "topic": "integration",
        "difficulty": "basic",
        "statement": r"Suppose $f$ is integrable on $[a,b]$. Prove $\left|\int_a^b f\right|\le \int_a^b |f|$.",
        "reference_proof": r"""For all $x$, $-|f(x)|\le f(x)\le |f(x)|$.
Integrating each part (monotonicity of the integral):
$$-\int_a^b|f|\le \int_a^b f\le \int_a^b|f|.$$
A real number that is both $\le A$ and $\ge -A$ (with $A=\int_a^b|f|\ge0$) satisfies $\left|\int_a^b f\right|\le A=\int_a^b|f|$. $\blacksquare$""",
    },
    {
        "id": "D6",
        "topic": "integration",
        "difficulty": "medium",
        "statement": r"Prove the fundamental theorem of calculus (part 2 / Newton-Leibniz): if $f$ is continuous on $[a,b]$ and $F'=f$, then $\int_a^b f=F(b)-F(a)$.",
        "reference_proof": r"""Let $G(x)=\int_a^x f(t)\,dt$. By FTC part 1, $G'=f=F'$ on $[a,b]$.
Hence $(G-F)'\equiv 0$, and by "zero derivative implies constant", $G-F\equiv C$ (a constant).
Substituting $x=a$: $G(a)=0$, so $C=-F(a)$, i.e. $G(x)=F(x)-F(a)$.
Substituting $x=b$: $\int_a^b f=G(b)=F(b)-F(a)$. $\blacksquare$""",
    },
    {
        "id": "D7",
        "topic": "integration",
        "difficulty": "advanced",
        "statement": r"Prove that a continuous function $f$ on $[a,b]$ is Riemann integrable.",
        "reference_proof": r"""By Heine-Cantor, $f$ is uniformly continuous on $[a,b]$. Given $\varepsilon>0$, there exists $\delta>0$ such that
$|s-t|<\delta \Rightarrow |f(s)-f(t)|<\dfrac{\varepsilon}{b-a}$.
Take a partition $P$ with every subinterval of length $\Delta x_i<\delta$. On each closed subinterval $f$ attains a maximum $M_i$ and minimum $m_i$ (extreme value theorem),
and the corresponding points are within $\delta$, so $M_i-m_i\le \dfrac{\varepsilon}{b-a}$. Then
$$U(f,P)-L(f,P)=\sum_i (M_i-m_i)\Delta x_i\le \frac{\varepsilon}{b-a}\sum_i \Delta x_i=\varepsilon.$$
By the Riemann integrability criterion (upper and lower sums can be made arbitrarily close), $f$ is integrable. $\blacksquare$""",
    },
    {
        "id": "D8",
        "topic": "integration",
        "difficulty": "basic",
        "statement": r"Prove that $\dfrac{1}{2}\le \int_0^1 \dfrac{dx}{1+x^2}\le 1$.",
        "reference_proof": r"""For $x\in[0,1]$, $0\le x^2\le 1$, so $1\le 1+x^2\le 2$, and taking reciprocals,
$$\frac{1}{2}\le \frac{1}{1+x^2}\le 1.$$
Integrating this inequality over $[0,1]$ (length $1$; monotonicity of the integral):
$$\frac12\cdot 1\le \int_0^1\frac{dx}{1+x^2}\le 1\cdot 1,$$
i.e. $\dfrac12\le\int_0^1\dfrac{dx}{1+x^2}\le 1$. (The actual value is $\pi/4\approx 0.785$, inside the interval.) $\blacksquare$""",
    },
    {
        "id": "D9",
        "topic": "integration",
        "difficulty": "medium",
        "statement": r"Prove that the improper integral $\int_1^\infty \dfrac{dx}{x^p}$ converges if and only if $p>1$.",
        "reference_proof": r"""Consider $\int_1^R x^{-p}\,dx$ and let $R\to\infty$.
Case $p\ne 1$: $\int_1^R x^{-p}\,dx=\dfrac{R^{1-p}-1}{1-p}$.
  - If $p>1$, then $1-p<0$, $R^{1-p}\to 0$, and the limit is $\dfrac{1}{p-1}$ (finite): convergent.
  - If $p<1$, then $1-p>0$, $R^{1-p}\to\infty$: divergent.
Case $p=1$: $\int_1^R \dfrac{dx}{x}=\ln R\to\infty$: divergent.
Combining: convergence $\iff p>1$. $\blacksquare$""",
    },
    {
        "id": "D10",
        "topic": "integration",
        "difficulty": "advanced",
        "statement": r"Prove the integral Cauchy-Schwarz inequality: if $f,g$ are continuous on $[a,b]$, then $\left(\int_a^b fg\right)^2\le \left(\int_a^b f^2\right)\left(\int_a^b g^2\right)$.",
        "reference_proof": r"""If $\int_a^b g^2=0$, then by D1 ($g^2\ge0$ continuous with zero integral) $g\equiv 0$, and both sides are $0$: done.
Otherwise let $A=\int g^2>0$. For every real $\lambda$, $(f-\lambda g)^2\ge 0$, and integrating,
$$0\le \int_a^b (f-\lambda g)^2=\int f^2-2\lambda\int fg+\lambda^2\int g^2.$$
This quadratic in $\lambda$ is nonnegative for all $\lambda$, so its discriminant is $\le 0$:
$$\Big(2\int fg\Big)^2-4\Big(\int g^2\Big)\Big(\int f^2\Big)\le 0,$$
which rearranges to $\left(\int fg\right)^2\le \left(\int f^2\right)\left(\int g^2\right)$. $\blacksquare$""",
    },
]
