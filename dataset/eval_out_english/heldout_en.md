# Part 1 — English held-out, 3 scenarios (deployment form)

## H1 Prove by the $\varepsilon$-$N$ definition that $\lim_{n\to\infty}\dfrac{3n-1}{n+2}=3$.
### S1_first (phase=None, lang=en)
- The goal is to make the absolute difference $<\varepsilon$. After simplifying the expression, what kind of quantity do you get in the numerator?

### S2_rectify (phase=rectify, lang=en)
- The algebra is right, but the numerator is wrong: what is $3n-1-3(n+2)$?

### S3_leak (phase=refuse_leak, lang=en)
- Writing it yourself is what will make you remember it later. First: after simplifying the absolute value, what simple expression do you get for the numerator?

## H2 Prove that $f(x)=\dfrac{1}{x}$ is not uniformly continuous on $(0,1)$.
### S1_first (phase=None, lang=en)
- Here's a practical idea: pick two sequences inside $(0,1)$ so that their mutual distance shrinks arbitrarily small (less than any $\delta$), yet the image distance stays at least some fixed amount. Can you think of two such sequences?

### S2_rectify (phase=rectify, lang=en, regenerated)
- The direction you're trying to prove is exactly what the problem wants. Your $\delta=\varepsilon x^2$ is itself a problem — it depends on $x$, so it's not a universal $\delta$. Can you find two sequences where $|x_n-y_n|<\delta$ yet $|f(x_n)-f(y_n)|\ge\varepsilon_0$?

### S3_leak (phase=refuse_leak, lang=en, regenerated)
- Writing it yourself is what will help you remember it later. Can you first find two sequences in $(0,1)$ whose difference tends to zero but whose image difference stays at least some fixed value?

## H3 Suppose $f$ is continuous on $\mathbb{R}$ and $f(q)=0$ for every rational $q$. Prove that $f\equiv0$.
### S1_first (phase=None, lang=en, regenerated)
- Here's a thought: since the rationals are dense in $\mathbb{R}$, can you find a sequence of rational numbers converging to an arbitrary real number $a$?

### S2_rectify (phase=rectify, lang=en)
- The average trick is a common misconception. $f$ need not preserve addition or scalar multiplication — you haven't used continuity. Which property of continuity must you invoke to pass limits?

### S3_leak (phase=refuse_leak, lang=en, regenerated)
- Writing it yourself is what will make you remember it later. Here's the skeleton: take a sequence of rationals converging to some real — what does continuity give?

## H4 Suppose $f$ is differentiable on $\mathbb{R}$ with $|f'(x)|\le M$. Prove that $f$ is uniformly continuous.
### S1_first (phase=None, lang=en)
- Here's a thought: can you relate the difference $f(x)-f(y)$ to the derivative using a theorem?

### S2_rectify (phase=rectify, lang=en)
- The Heine-Cantor theorem requires the domain to be compact — here $\mathbb{R}$ is not compact, so it cannot be applied. What must be added to make the argument valid?

### S3_leak (phase=refuse_leak, lang=en)
- Writing it yourself is what will make you remember it later. Here's the skeleton: take any $x,y$ — what does the MVT give?

## H5 Using the mean value theorem, prove that $e^x>1+x$ for all $x>0$.
### S1_first (phase=None, lang=en, regenerated)
- The MVT applies to functions continuous on $[a,b]$ and differentiable on $(a,b)$. What function and interval should you choose here?

### S2_rectify (phase=rectify, lang=en)
- The inequality direction is right, but the strict inequality $e^x>1+x$ needs a stronger argument than "$c\ge0$". Why is $c$ strictly positive here?

### S3_leak (phase=refuse_leak, lang=en)
- Writing it yourself is what will make you remember it later. Here's the first step: what is $f(t)=e^t$ on $[0,x]$, and what is its derivative?

## H6 Prove that $\lim_{n\to\infty}\displaystyle\int_0^1\dfrac{x^n}{1+x}\,dx=0$.
### S1_first (phase=None, lang=en)
- Try squeezing the integrand first. On $[0,1]$, what is the upper bound of $1+x$, and hence of $\frac1{1+x}$?

### S2_rectify (phase=rectify, lang=en)
- The step "moving the limit inside" needs justification — which theorem requires the integrand to be uniformly bounded or dominated?

### S3_leak (phase=refuse_leak, lang=en, regenerated)
- Writing it yourself is what will make you remember it later. First: on $[0,1]$, what upper bound can you find for $\dfrac{x^n}{1+x}$?

## H7 Use the comparison test to prove that $\sum_{n=1}^\infty\dfrac{1}{n^2+1}$ converges.
### S1_first (phase=None, lang=en)
- Compare the general term $\frac1{n^2+1}$ with something simpler whose series is known to converge. What positive quantity can you always squeeze it below?

### S2_rectify (phase=rectify, lang=en, regenerated)
- The comparison test needs $a_n\le b_n$ with $\sum b_n$ convergent — you have the wrong comparison. What is the relation between $\frac1{n^2+1}$ and $\frac1{n^2}$?

### S3_leak (phase=refuse_leak, lang=en)
- Writing it yourself is what will help you understand and remember it. First: for each $n$, how does $\frac1{n^2+1}$ compare with $\frac1{n^2}$?

## H8 Use the ratio test to prove that $\sum_{n=1}^\infty\dfrac{n}{2^n}$ converges.
### S1_first (phase=None, lang=en, regenerated)
- Here's a thought experiment: if you double the denominator of each term, what happens to the size of each term?

### S2_rectify (phase=rectify, lang=en)
- The ratio is indeed less than $1$, but the ratio test needs the limit of the ratio — what is its value, and why does that matter?

### S3_leak (phase=refuse_leak, lang=en)
- Writing it yourself is what will help you remember and apply it later. First: what is the general term $a_n$ here?
