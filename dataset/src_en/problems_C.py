# -*- coding: utf-8 -*-
"""Topic C: differentiation (differentiable => continuous / mean value theorems
Rolle-Lagrange-Cauchy / Fermat / monotonicity / Lipschitz). English translation of src/problems_C.py."""

PROBLEMS = [
    {
        "id": "C1",
        "topic": "differentiation",
        "difficulty": "basic",
        "statement": r"Prove: if $f$ is differentiable at $x_0$, then $f$ is continuous at $x_0$.",
        "reference_proof": r"""We must show $\lim_{x\to x_0}f(x)=f(x_0)$, i.e. $\lim_{x\to x_0}\big(f(x)-f(x_0)\big)=0$.
For $x\ne x_0$ rewrite identically:
$$f(x)-f(x_0)=\frac{f(x)-f(x_0)}{x-x_0}\cdot (x-x_0).$$
As $x\to x_0$, the first factor $\to f'(x_0)$ (finite, by differentiability) and the second factor $\to 0$.
By the product rule for limits, $\lim_{x\to x_0}\big(f(x)-f(x_0)\big)=f'(x_0)\cdot 0=0$. Hence $f$ is continuous at $x_0$. $\blacksquare$""",
    },
    {
        "id": "C2",
        "topic": "differentiation",
        "difficulty": "medium",
        "statement": r"Prove Rolle's theorem: if $f$ is continuous on $[a,b]$, differentiable on $(a,b)$, and $f(a)=f(b)$, then there exists $c\in(a,b)$ with $f'(c)=0$.",
        "reference_proof": r"""$f$ is continuous on $[a,b]$, so by the extreme value theorem it attains a maximum $M$ and a minimum $m$.
Case 1: $M=m$. Then $f$ is constant, $f'\equiv 0$ on $(a,b)$, and any $c$ works.
Case 2: $M>m$. Since $f(a)=f(b)$, at least one of the maximum or minimum is attained at an interior point $c\in(a,b)$.
At that interior extremum, Fermat's theorem gives $f'(c)=0$. $\blacksquare$""",
    },
    {
        "id": "C3",
        "topic": "differentiation",
        "difficulty": "medium",
        "statement": r"Prove the Lagrange mean value theorem: if $f$ is continuous on $[a,b]$ and differentiable on $(a,b)$, then there exists $c$ with $f'(c)=\dfrac{f(b)-f(a)}{b-a}$.",
        "reference_proof": r"""Construct an auxiliary function that cancels the endpoint difference so Rolle applies:
$$g(x)=f(x)-f(a)-\frac{f(b)-f(a)}{b-a}(x-a).$$
$g$ is continuous on $[a,b]$ and differentiable on $(a,b)$. Check the endpoints: $g(a)=0$, and
$g(b)=f(b)-f(a)-\dfrac{f(b)-f(a)}{b-a}(b-a)=0$.
By Rolle's theorem there exists $c\in(a,b)$ with $g'(c)=0$. Since $g'(x)=f'(x)-\dfrac{f(b)-f(a)}{b-a}$,
we get $f'(c)=\dfrac{f(b)-f(a)}{b-a}$. $\blacksquare$""",
    },
    {
        "id": "C4",
        "topic": "differentiation",
        "difficulty": "advanced",
        "statement": r"Prove the Cauchy mean value theorem: if $f,g$ are continuous on $[a,b]$, differentiable on $(a,b)$, and $g'\ne 0$, then there exists $c$ with $\dfrac{f'(c)}{g'(c)}=\dfrac{f(b)-f(a)}{g(b)-g(a)}$.",
        "reference_proof": r"""First note $g(b)\ne g(a)$: otherwise Rolle would give a point where $g'=0$, contradicting the hypothesis.
Construct the auxiliary function
$$h(x)=\big(f(b)-f(a)\big)\,g(x)-\big(g(b)-g(a)\big)\,f(x).$$
$h$ is continuous on $[a,b]$ and differentiable on $(a,b)$. Compute $h(a)=f(b)g(a)-g(b)f(a)=h(b)$ (expand to verify equality).
By Rolle there exists $c$ with $h'(c)=0$, i.e. $\big(f(b)-f(a)\big)g'(c)=\big(g(b)-g(a)\big)f'(c)$.
Dividing by $g'(c)\big(g(b)-g(a)\big)\ne 0$ gives the conclusion. $\blacksquare$""",
    },
    {
        "id": "C5",
        "topic": "differentiation",
        "difficulty": "medium",
        "statement": r"Prove: if $f$ is differentiable on an interval $I$ and $f'\equiv 0$, then $f$ is constant on $I$.",
        "reference_proof": r"""Take any $x_1<x_2\in I$. $f$ is continuous on $[x_1,x_2]$ and differentiable on $(x_1,x_2)$, so by the Lagrange mean value theorem
there exists $c\in(x_1,x_2)$ with
$$f(x_2)-f(x_1)=f'(c)(x_2-x_1).$$
Since $f'(c)=0$, $f(x_2)=f(x_1)$. As $x_1,x_2$ were arbitrary, $f$ takes the same value throughout $I$, i.e. it is constant. $\blacksquare$""",
    },
    {
        "id": "C6",
        "topic": "differentiation",
        "difficulty": "medium",
        "statement": r"Prove: if $f$ is differentiable on an interval $I$ and $f'>0$, then $f$ is strictly increasing on $I$.",
        "reference_proof": r"""Take any $x_1<x_2\in I$. By the Lagrange mean value theorem there exists $c\in(x_1,x_2)$ with
$$f(x_2)-f(x_1)=f'(c)(x_2-x_1).$$
Since $f'(c)>0$ and $x_2-x_1>0$, the right-hand side is $>0$, so $f(x_2)>f(x_1)$.
As $x_1<x_2$ were arbitrary, $f$ is strictly increasing. $\blacksquare$""",
    },
    {
        "id": "C7",
        "topic": "differentiation",
        "difficulty": "medium",
        "statement": r"Prove Fermat's theorem: if $f$ attains a local maximum at an interior point $c$ and $f'(c)$ exists, then $f'(c)=0$.",
        "reference_proof": r"""Let $c$ be a local maximum: there exists $\delta>0$ such that $f(c+h)\le f(c)$ whenever $|h|<\delta$.
Right derivative ($h\to 0^+$): the difference quotient $\dfrac{f(c+h)-f(c)}{h}\le 0$, so $f'(c)=\lim_{h\to0^+}\le 0$.
Left derivative ($h\to 0^-$): numerator $\le 0$, denominator $<0$, so the quotient is $\ge 0$, giving $f'(c)\ge 0$.
Since $f'(c)$ exists (left and right derivatives agree), it is both $\le 0$ and $\ge 0$, hence $f'(c)=0$. $\blacksquare$""",
    },
    {
        "id": "C8",
        "topic": "differentiation",
        "difficulty": "medium",
        "statement": r"Suppose $f$ is differentiable on an interval $I$ with $|f'(x)|\le M$. Prove $|f(x)-f(y)|\le M|x-y|$ ($f$ is Lipschitz).",
        "reference_proof": r"""Take any $x,y\in I$, say $x\ne y$. By the Lagrange mean value theorem there is $c$ between $x$ and $y$ with
$$f(x)-f(y)=f'(c)(x-y).$$
Take absolute values and use $|f'(c)|\le M$:
$$|f(x)-f(y)|=|f'(c)|\,|x-y|\le M|x-y|.$$
For $x=y$ both sides are $0$, so the inequality also holds. $\blacksquare$""",
    },
    {
        "id": "C9",
        "topic": "differentiation",
        "difficulty": "medium",
        "statement": r"Prove that for all real $x,y$, $|\sin x-\sin y|\le |x-y|$.",
        "reference_proof": r"""Let $f(t)=\sin t$; then $f'(t)=\cos t$ and $|f'(t)|\le 1$.
For $x\ne y$, the Lagrange mean value theorem gives some $c$ with
$$\sin x-\sin y=\cos c\,(x-y).$$
Taking absolute values: $|\sin x-\sin y|=|\cos c|\,|x-y|\le |x-y|$. For $x=y$ the inequality is trivial. $\blacksquare$""",
    },
    {
        "id": "C10",
        "topic": "differentiation",
        "difficulty": "advanced",
        "statement": r"Prove that for all $x>0$, $\dfrac{x}{1+x}<\ln(1+x)<x$.",
        "reference_proof": r"""Let $f(t)=\ln(1+t)$, continuous on $[0,x]$ and differentiable on $(0,x)$, with $f'(t)=\dfrac{1}{1+t}$.
By the Lagrange mean value theorem there exists $\xi\in(0,x)$ with
$$\ln(1+x)-\ln 1=\frac{1}{1+\xi}\,x,\qquad\text{i.e. } \ln(1+x)=\frac{x}{1+\xi}.$$
Since $0<\xi<x$, we have $1<1+\xi<1+x$, hence $\dfrac{1}{1+x}<\dfrac{1}{1+\xi}<1$.
Multiplying by $x>0$: $\dfrac{x}{1+x}<\dfrac{x}{1+\xi}=\ln(1+x)<x$. $\blacksquare$""",
    },
]
