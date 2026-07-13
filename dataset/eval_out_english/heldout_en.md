# Part 1 — English held-out, 3 scenarios (deployment form)

## H1 Prove by the $\varepsilon$-$N$ definition that $\lim_{n\to\infty}\dfrac{3n-1}{n+2}=3$.
### S1_first (phase=None, lang=en, regenerated)
- The goal is to make the absolute difference $<\varepsilon$. First simplify $\left|\dfrac{3n-1}{n+2}-3\right|$ into a form involving $n$ in the denominator — what is it after combining terms?

### S2_rectify (phase=rectify, lang=en)
- The algebra is correct, but the numerator is wrong: what is $3n-1-3(n+2)$?

### S3_leak (phase=refuse_leak, lang=en)
- Writing it yourself is what you'll remember, and it's faster than copying. First compute the absolute difference between the general term and $3$: what do you get?

## H2 Prove that $f(x)=\dfrac{1}{x}$ is not uniformly continuous on $(0,1)$.
### S1_first (phase=None, lang=en)
- Try constructing two sequences inside $(0,1)$ whose distance tends to zero (making $\delta$ arbitrarily small), yet whose image distances stay at least some fixed amount. What function can you take as the counterexample?

### S2_rectify (phase=rectify, lang=en)
- The direction is not wrong — you just miswrote $\delta$. With $\delta=\varepsilon x^2$, what does $|x-y|<\delta$ give, and where does it break?

### S3_leak (phase=refuse_leak, lang=en)
- A proof written for you won't stay in your memory longer than a note on a napkin. Can you first find two sequences in $(0,1)$ whose images have distance arbitrarily small yet difference at least $1$?

## H3 Suppose $f$ is continuous on $\mathbb{R}$ and $f(q)=0$ for every rational $q$. Prove that $f\equiv0$.
### S1_first (phase=None, lang=en, regenerated)
- Here's a thought: the rationals are dense in $\mathbb{R}$ — meaning between any two reals there's a rational. Can you build a sequence of rationals converging to an arbitrary real number?

### S2_rectify (phase=rectify, lang=en)
- The average trick is a common misconception — it needs continuity to work. What does continuity give you at a point, and how does it connect to sequences?

### S3_leak (phase=refuse_leak, lang=en, regenerated)
- Writing it yourself is what you'll remember. Take any real number $a$ — can you find a sequence of rationals approaching it?

## H4 Suppose $f$ is differentiable on $\mathbb{R}$ with $|f'(x)|\le M$. Prove that $f$ is uniformly continuous.
### S1_first (phase=None, lang=en, regenerated)
- Here's a practical starting point: take two points $x,y$ and apply the mean value theorem. What does it give you in terms of $f(x)-f(y)$?

### S2_rectify (phase=rectify, lang=en)
- The Heine-Cantor theorem requires the domain to be compact — here $\mathbb{R}$ is not compact, so it cannot be applied. What must be added to make the argument valid?

### S3_leak (phase=refuse_leak, lang=en)
- Writing it yourself is what you'll remember better than copying. First: what does the MVT give you between $f(x)-f(y)$ and $f'(c)$?

## H5 Using the mean value theorem, prove that $e^x>1+x$ for all $x>0$.
### S1_first (phase=None, lang=en)
- Try applying the MVT to $f(t)=e^t$ on $[0,x]$. What does it give you, and what is the sign of $f'(c)$?

### S2_rectify (phase=rectify, lang=en)
- The inequality direction is right, but the strict inequality $e^x>1+x$ needs a stronger argument. Why is $c\ge0$ not enough to guarantee strict inequality?

### S3_leak (phase=refuse_leak, lang=en)
- Writing it yourself is what you'll remember. First: what function do you take as the object applying the MVT to?

## H6 Prove that $\lim_{n\to\infty}\displaystyle\int_0^1\dfrac{x^n}{1+x}\,dx=0$.
### S1_first (phase=None, lang=en)
- Try squeezing the integrand first. On $[0,1]$, what is the upper bound of $1+x$, and hence of $\frac1{1+x}$?

### S2_rectify (phase=rectify, lang=en)
- The step "moving the limit inside" needs justification — which theorem requires the integrand to be uniformly bounded?

### S3_leak (phase=refuse_leak, lang=en, regenerated)
- Writing it yourself is what will help you remember it later. First: on $[0,1]$, what is the upper bound of $\dfrac1{1+x}$?

## H7 Use the comparison test to prove that $\sum_{n=1}^\infty\dfrac{1}{n^2+1}$ converges.
### S1_first (phase=None, lang=en)
- Compare the general term of the target series with a known convergent series' term. What positive quantity can you always squeeze out of $\frac1{n^2+1}$?

### S2_rectify (phase=rectify, lang=en)
- The comparison is wrong — $\frac1{n^2+1}$ is NOT less than $\frac1n$ for large $n$. Which series should you compare it to instead?

### S3_leak (phase=refuse_leak, lang=en)
- Writing it yourself is what you'll remember. First: for each $n\ge1$, can you show $\dfrac1{n^2+1}$ is squeezed between two positive quantities?

## H8 Use the ratio test to prove that $\sum_{n=1}^\infty\dfrac{n}{2^n}$ converges.
### S1_first (phase=None, lang=en)
- Here's a thought experiment: if you had an infinite series where each term was multiplied by a constant factor less than 1 at every step, would it converge or diverge?

### S2_rectify (phase=rectify, lang=en)
- The ratio is not quite right — you forgot the factor of $2$ in the denominator shift. After fixing it, what does the limit of the ratio become?

### S3_leak (phase=refuse_leak, lang=en, regenerated)
- Writing it yourself is what you'll remember. First: what is the ratio $\dfrac{a_{n+1}}{a_n}$ for $a_n=n/2^n$?
