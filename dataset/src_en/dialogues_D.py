# -*- coding: utf-8 -*-
"""Topic D core dialogues (D1-D10 x 3 personas). English translation of src/dialogues_D.py."""

DIALOGUES = [
    # ===== D1: f>=0 continuous, integral 0 => f==0 =====
    {"problem_id": "D1", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Integral zero implies f is identically zero? Lots of functions seem to have zero integral — how do you prove this?"},
        {"role": "assistant", "content": "The key is $f\\ge0$ and continuity. Argue by contradiction: suppose $f(x_0)>0$ at some point — what does continuity force $f$ to do near $x_0$?"},
        {"role": "user", "content": "Continuity makes f exceed some positive number on a small piece around x_0, say > f(x_0)/2."},
        {"role": "assistant", "content": "Good — call that piece $[c,d]$. Since $f\\ge0$, $\\int_a^b f$ is at least the integral over $[c,d]$ — can you give a lower bound?"},
        {"role": "user", "content": "∫_a^b f >= ∫_c^d f >= (f(x_0)/2)(d-c) > 0."},
        {"role": "assistant", "content": "Exactly — how does that clash with $\\int_a^b f=0$?"},
        {"role": "user", "content": "We get a positive number that should equal 0 — contradiction. So no such x_0 exists and f is identically 0."},
        {"role": "assistant", "content": "Completely correct. The core: continuity amplifies a single positive value into a whole positive segment, and nonnegativity then forces a positive integral."},
    ]},
    {"problem_id": "D1", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "∫f=0 means the average of f is 0, and zero average means f=0."},
        {"role": "assistant", "content": "Zero average generally only forces \"some positive and some negative\". Which extra hypothesis here rules out negative values?"},
        {"role": "user", "content": "The problem gives f>=0, so no negative values can cancel. Then if some point is >0..."},
        {"role": "assistant", "content": "That's the key. If $f(x_0)>0$, use continuity to produce a segment where $f>\\frac{f(x_0)}2$ — what lower bound for the integral follows?"},
        {"role": "user", "content": ">= (f(x_0)/2)(d-c) > 0, contradicting ∫f=0, so f == 0."},
        {"role": "assistant", "content": "Correct. Lesson: nonnegativity and continuity are both indispensable — drop either and you can build examples with zero integral that aren't identically zero."},
    ]},
    {"problem_id": "D1", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Contradiction: f(x_0)>0, continuity gives f>f(x_0)/2 on a neighborhood [c,d], so ∫ >= (f(x_0)/2)(d-c) > 0, contradiction."},
        {"role": "assistant", "content": "Complete. If \"continuous\" is dropped, can you produce a counterexample with $f\\ge0$, $\\int=0$, yet $f$ not identically zero?"},
        {"role": "user", "content": "Yes: let f be 1 at a single point and 0 elsewhere — the integral is still 0 but f is not identically 0. So continuity is essential."},
        {"role": "assistant", "content": "Correct — continuity is exactly what excludes \"nonzero on a measure-zero set\". Sharp analysis."},
    ]},

    # ===== D2: FTC part 1 =====
    {"problem_id": "D2", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "FTC part 1 — the derivative of F(x)=∫f is f — I don't know how to prove it from the definition."},
        {"role": "assistant", "content": "Start from the definition of the derivative. Using additivity of the integral, what does $\\frac{F(x+h)-F(x)}{h}$ become?"},
        {"role": "user", "content": "= (1/h) ∫_x^{x+h} f(t) dt."},
        {"role": "assistant", "content": "Good. We want this to approach $f(x)$. Writing $f(x)$ as $\\frac1h\\int_x^{x+h}f(x)\\,dt$ too, what integral is their difference?"},
        {"role": "user", "content": "Difference = (1/h) ∫_x^{x+h} (f(t)-f(x)) dt."},
        {"role": "assistant", "content": "Exactly. After taking absolute values, what quantity — courtesy of continuity of $f$ at $x$ — dominates this difference and tends to 0?"},
        {"role": "user", "content": "It's dominated by sup_{|t-x|<=|h|}|f(t)-f(x)|, which tends to 0 as h->0 by continuity, so F'(x)=f(x)."},
        {"role": "assistant", "content": "Completely correct. The trick: smuggle the constant $f(x)$ into the integral and control the integrand's oscillation with continuity."},
    ]},
    {"problem_id": "D2", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "F(x)=∫f is just the antiderivative of f, so F'=f — isn't that the definition?"},
        {"role": "assistant", "content": "\"Antiderivative\" is exactly what this theorem establishes, so it can't serve as a definition. Start from the derivative limit: what integral does $\\frac{F(x+h)-F(x)}h$ equal?"},
        {"role": "user", "content": "(1/h) ∫_x^{x+h} f dt."},
        {"role": "assistant", "content": "Good. Subtracting $f(x)$ and using continuity, how do you show it approaches $f(x)$?"},
        {"role": "user", "content": "Difference = (1/h)∫(f(t)-f(x))dt, absolute value <= the sup of |f(t)-f(x)| nearby, which tends to 0 as h->0 by continuity."},
        {"role": "assistant", "content": "Correct. Lesson: the FTC must PROVE that integration and differentiation invert each other — the conclusion can't be assumed as a definition."},
    ]},
    {"problem_id": "D2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "The quotient is (1/h)∫_x^{x+h}(f(t)-f(x))dt, whose absolute value <= sup|f(t)-f(x)| -> 0 (continuity), so F'=f."},
        {"role": "assistant", "content": "Completely correct. Only continuity of $f$ at the point was used — what happens if $f$ is merely integrable but discontinuous at $x$?"},
        {"role": "user", "content": "Then F need not be differentiable at x, or F'(x) != f(x); the differentiability in FTC-1 genuinely requires continuity at the point."},
        {"role": "assistant", "content": "Correct — continuity is the pointwise necessary ingredient. Deep understanding."},
    ]},

    # ===== D3: integral mean value =====
    {"problem_id": "D3", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "The mean value theorem for integrals wants c with ∫f = f(c)(b-a), and I don't see where c comes from."},
        {"role": "assistant", "content": "First squeeze the integral. $f$ is continuous on $[a,b]$, attaining minimum $m$ and maximum $M$ — in what range does $\\int_a^b f$ lie?"},
        {"role": "user", "content": "m(b-a) <= ∫f <= M(b-a)."},
        {"role": "assistant", "content": "Good. Dividing by $(b-a)$ gives the average $\\mu=\\frac1{b-a}\\int f$ — in what interval does it lie?"},
        {"role": "user", "content": "mu in [m,M]."},
        {"role": "assistant", "content": "Exactly. A continuous function attains every value between $m$ and $M$ — which theorem guarantees a $c$ with $f(c)=\\mu$?"},
        {"role": "user", "content": "The intermediate value theorem: there is c with f(c)=mu, i.e. ∫f=f(c)(b-a)."},
        {"role": "assistant", "content": "Completely correct. The integral MVT = squeeze the average between m and M, then hit it with the IVT."},
    ]},
    {"problem_id": "D3", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Take c to be the midpoint of [a,b]; then f(c) is the average and ∫f=f(c)(b-a)."},
        {"role": "assistant", "content": "The value at the midpoint need not equal the average. $c$'s existence must be argued, not decreed. First: within what range of $f$'s values must $\\frac1{b-a}\\int f$ lie?"},
        {"role": "user", "content": "In [m,M] (min to max), since integrating m<=f<=M gives that."},
        {"role": "assistant", "content": "Exactly. Since the average lies in $[m,M]$, which theorem guarantees a $c$ where $f(c)$ equals it exactly?"},
        {"role": "user", "content": "The intermediate value theorem. So c exists but isn't necessarily the midpoint."},
        {"role": "assistant", "content": "Correct. Lesson: $c$ is guaranteed by the IVT with unknown location — it may not be chosen as the midpoint."},
    ]},
    {"problem_id": "D3", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "From m<=f<=M, integration gives mu = ∫f/(b-a) in [m,M], and the IVT supplies c with f(c)=mu."},
        {"role": "assistant", "content": "Correct. The proof uses continuity of $f$ twice — where exactly?"},
        {"role": "user", "content": "Once to attain m and M (extreme value theorem), once to attain intermediate values (IVT); both need continuity."},
        {"role": "assistant", "content": "Correct — you see continuity's double role. Very complete."},
    ]},

    # ===== D4: monotonicity of integral =====
    {"problem_id": "D4", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "f<=g gives ∫f<=∫g — intuitively right, but I don't know how to write the proof."},
        {"role": "assistant", "content": "Moving the difference to one side simplifies it. Let $h=g-f$: from $f\\le g$, what is the sign of $h$?"},
        {"role": "user", "content": "h = g-f >= 0."},
        {"role": "assistant", "content": "Good. For the nonnegative function $h$, what is the sign of any lower sum $L(h,P)=\\sum m_i\\Delta x_i$ — because each $m_i$ is what?"},
        {"role": "user", "content": "Each m_i = inf h >= 0, so every lower sum >= 0, hence ∫h = sup of lower sums >= 0."},
        {"role": "assistant", "content": "Exactly. Now split $\\int h$ by linearity — what relation between $\\int f$ and $\\int g$ falls out?"},
        {"role": "user", "content": "∫g - ∫f = ∫h >= 0, so ∫f <= ∫g."},
        {"role": "assistant", "content": "Completely correct. Monotonicity is rooted in \"nonnegative functions have nonnegative integrals\" plus linearity."},
    ]},
    {"problem_id": "D4", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f<=g holds at every point, so integrating both sides preserves the inequality. Done."},
        {"role": "assistant", "content": "The conclusion is right, but \"integrating preserves inequalities\" is precisely the property being proved. Back to definitions: with $h=g-f\\ge0$, why is its integral nonnegative?"},
        {"role": "user", "content": "Because inf h >= 0 on every subinterval, all lower sums are >= 0, so ∫h >= 0."},
        {"role": "assistant", "content": "Exactly — that is the real basis of monotonicity. What does linearity then give?"},
        {"role": "user", "content": "∫g - ∫f = ∫h >= 0, hence ∫f <= ∫g."},
        {"role": "assistant", "content": "Correct. Lesson: \"integration preserves order\" isn't free — it's derived from nonnegative integrals plus linearity."},
    ]},
    {"problem_id": "D4", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Let h=g-f>=0; its lower sums are all >=0 so ∫h>=0, and linearity gives ∫f<=∫g."},
        {"role": "assistant", "content": "Correct. If $f\\le g$ with strict inequality $f<g$ at some points, is $\\int f<\\int g$ guaranteed strictly?"},
        {"role": "user", "content": "Not necessarily; unless h=g-f is continuous and positive on some segment (as in the D1 argument), strictness at isolated points can't force a strict integral inequality."},
        {"role": "assistant", "content": "Correct — you've drawn the strict/non-strict boundary precisely. Well done."},
    ]},

    # ===== D5: |∫f| <= ∫|f| =====
    {"problem_id": "D5", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "|∫f| <= ∫|f| — with the absolute value inside, I don't know how to begin."},
        {"role": "assistant", "content": "Start from a pointwise inequality valid for all $x$: how is $f(x)$ squeezed by $\\pm|f(x)|$?"},
        {"role": "user", "content": "-|f(x)| <= f(x) <= |f(x)|."},
        {"role": "assistant", "content": "Good. Applying monotonicity of the integral (D4) to this two-sided inequality, what do you learn about $\\int f$?"},
        {"role": "user", "content": "-∫|f| <= ∫f <= ∫|f|."},
        {"role": "assistant", "content": "Exactly. A real number that is both $\\ge -A$ and $\\le A$ — what does that say about its absolute value?"},
        {"role": "user", "content": "It's equivalent to |∫f| <= A = ∫|f|."},
        {"role": "assistant", "content": "Completely correct. This is the continuous triangle inequality: pointwise squeeze plus monotonicity of the integral."},
    ]},
    {"problem_id": "D5", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "By the triangle inequality, |∫f| = |Σ f Δx| <= Σ|f|Δx = ∫|f| — write it directly."},
        {"role": "assistant", "content": "The Riemann-sum-limit idea is right, but you'd need to rigorously argue that limits preserve the inequality. Is there a more direct route using only monotonicity?"},
        {"role": "user", "content": "Yes — use -|f| <= f <= |f| and integrate."},
        {"role": "assistant", "content": "Exactly. Integration gives $-\\int|f|\\le\\int f\\le\\int|f|$ — why is that equivalent to $|\\int f|\\le\\int|f|$?"},
        {"role": "user", "content": "Because -A <= y <= A is the definition of |y| <= A, with A = ∫|f|."},
        {"role": "assistant", "content": "Correct. Lesson: pointwise squeeze + monotonicity is a cleaner rigorous route than taking limits of Riemann sums."},
    ]},
    {"problem_id": "D5", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "From -|f| <= f <= |f|, integrating gives -∫|f| <= ∫f <= ∫|f|, i.e. |∫f| <= ∫|f|."},
        {"role": "assistant", "content": "Correct. The proof needs $|f|$ integrable — does integrability of $f$ guarantee that of $|f|$?"},
        {"role": "user", "content": "Yes: the absolute value of an integrable function is integrable (the oscillation M_i - m_i doesn't increase), so ∫|f| is well defined."},
        {"role": "assistant", "content": "Correct — you checked the integrability premise. Very rigorous."},
    ]},

    # ===== D6: FTC part 2 =====
    {"problem_id": "D6", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "The Newton-Leibniz formula ∫f = F(b)-F(a): I know how to use it but not how to prove it."},
        {"role": "assistant", "content": "Hook it to FTC part 1. Define $G(x)=\\int_a^x f$; by FTC-1, what is $G'$?"},
        {"role": "user", "content": "G'=f. And the problem gives F'=f, so G'=F'."},
        {"role": "assistant", "content": "Good, $G'=F'$. By \"functions with equal derivatives differ by a constant\", what is $G-F$?"},
        {"role": "user", "content": "G-F = C (a constant)."},
        {"role": "assistant", "content": "Exactly. Pin down $C$ with $x=a$, then substitute $x=b$ — what do you get?"},
        {"role": "user", "content": "G(a)=0 gives C=-F(a), so G(x)=F(x)-F(a); at b, ∫f = G(b) = F(b)-F(a)."},
        {"role": "assistant", "content": "Completely correct. Part 2 is: build G via FTC-1, then trade it for an arbitrary antiderivative F using the constant difference."},
    ]},
    {"problem_id": "D6", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "F is an antiderivative of f, so ∫f = F(b)-F(a) — that's the definition."},
        {"role": "assistant", "content": "That is exactly the formula to be proved. For rigor, first build a concrete antiderivative $G(x)=\\int_a^x f$ via FTC-1 — how does it relate to the given $F$?"},
        {"role": "user", "content": "G'=f=F', so G-F is a constant."},
        {"role": "assistant", "content": "Exactly. How do you determine that constant and derive the formula?"},
        {"role": "user", "content": "G(a)=0 gives the constant = -F(a); substituting x=b gives ∫f = F(b)-F(a)."},
        {"role": "assistant", "content": "Correct. Lesson: connect the integral-defined antiderivative to an arbitrary $F$ via \"equal derivatives differ by a constant\" — don't just declare the formula."},
    ]},
    {"problem_id": "D6", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Set G(x)=∫_a^x f; FTC-1 gives G'=f=F', so G-F=C, and G(a)=0 yields ∫f=F(b)-F(a)."},
        {"role": "assistant", "content": "Completely correct. If part 2 is to hold with $f$ merely Riemann integrable (not necessarily continuous), how must the proof change?"},
        {"role": "user", "content": "Use a partition and apply the MVT to F on each subinterval, getting Σ f(c_i)Δx_i = F(b)-F(a), then refine the partition and take the limit."},
        {"role": "assistant", "content": "Correct — that's the more general proof independent of FTC-1. Broad perspective."},
    ]},

    # ===== D7: continuous => Riemann integrable =====
    {"problem_id": "D7", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Continuous implies integrable — this needs upper and lower sums and I don't know how to control their difference."},
        {"role": "assistant", "content": "The integrability criterion is \"the upper-lower gap can be made arbitrarily small\". $f$ is continuous on $[a,b]$ — to what stronger form of continuity can you upgrade, to control oscillation uniformly?"},
        {"role": "user", "content": "By Heine-Cantor, f is uniformly continuous on [a,b]."},
        {"role": "assistant", "content": "Good. Given $\\varepsilon$, uniform continuity provides $\\delta$ with $|s-t|<\\delta \\Rightarrow |f(s)-f(t)|<\\frac{\\varepsilon}{b-a}$. If every piece of the partition is shorter than $\\delta$, what bounds each $M_i-m_i$?"},
        {"role": "user", "content": "M_i - m_i <= eps/(b-a), since any two points of the subinterval are within delta."},
        {"role": "assistant", "content": "Exactly. Now estimate $U-L=\\sum(M_i-m_i)\\Delta x_i$ — what do you get?"},
        {"role": "user", "content": "<= (eps/(b-a)) * Σ Δx_i = (eps/(b-a))(b-a) = eps, so f is integrable."},
        {"role": "assistant", "content": "Completely correct. The key: uniform continuity makes every piece's oscillation simultaneously $<\\varepsilon/(b-a)$, so the total stays controlled."},
    ]},
    {"problem_id": "D7", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f is continuous at each point, so each piece oscillates little, the upper-lower gap is small, integrable."},
        {"role": "assistant", "content": "Pointwise continuity gives a $\\delta$ that varies with the point — it can't make ALL subintervals small at once. What upgrade provides one universal $\\delta$?"},
        {"role": "user", "content": "Uniform continuity (Heine-Cantor), so a single delta works across the whole interval."},
        {"role": "assistant", "content": "Exactly. With the universal $\\delta$ and a partition finer than $\\delta$, how does the $U-L$ estimate finish?"},
        {"role": "user", "content": "Each M_i-m_i <= eps/(b-a), so the total U-L <= eps, hence integrable."},
        {"role": "assistant", "content": "Correct. Lesson: integrability needs the universal $\\delta$ of UNIFORM continuity; pointwise continuity is not enough."},
    ]},
    {"problem_id": "D7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Heine-Cantor gives uniform continuity; take a partition with mesh<delta, then U-L = Σ(M_i-m_i)Δx_i <= eps, integrable."},
        {"role": "assistant", "content": "Completely correct. You used \"$f$ attains $M_i, m_i$ on each closed subinterval\" — which theorem does that step rely on?"},
        {"role": "user", "content": "The extreme value theorem, guaranteeing the max and min are actually attained on each closed subinterval, so M_i and m_i make sense."},
        {"role": "assistant", "content": "Correct — you've surfaced every hidden lemma. A very complete argument."},
    ]},

    # ===== D8: bounds for ∫_0^1 1/(1+x^2) =====
    {"problem_id": "D8", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "I need to trap this integral between 1/2 and 1 and don't know where to start estimating."},
        {"role": "assistant", "content": "No need to evaluate the integral — estimate the integrand first. On $[0,1]$, in what range does $1+x^2$ lie?"},
        {"role": "user", "content": "0<=x^2<=1, so 1<=1+x^2<=2."},
        {"role": "assistant", "content": "Good. Taking reciprocals (mind the direction), what is the range of $\\frac1{1+x^2}$?"},
        {"role": "user", "content": "Reciprocals flip the inequalities: 1/2 <= 1/(1+x^2) <= 1."},
        {"role": "assistant", "content": "Exactly. Integrating this inequality over an interval of length 1 (monotonicity), what results?"},
        {"role": "user", "content": "(1/2)*1 <= ∫ <= 1*1, i.e. 1/2 <= ∫ <= 1."},
        {"role": "assistant", "content": "Completely correct. The general method for estimating integrals: squeeze the integrand first, then multiply by the interval length."},
    ]},
    {"problem_id": "D8", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "1<=1+x^2<=2, so taking reciprocals gives 1 <= 1/(1+x^2) <= 1/2."},
        {"role": "assistant", "content": "Taking reciprocals must reverse the inequality direction. After inverting $1\\le 1+x^2\\le2$: does a larger denominator give a smaller or larger value?"},
        {"role": "user", "content": "A larger denominator gives a smaller value, so it's 1/2 <= 1/(1+x^2) <= 1 — I wrote the direction backwards."},
        {"role": "assistant", "content": "Exactly. After the fix, integrating over $[0,1]$ gives what bounds?"},
        {"role": "user", "content": "1/2 <= ∫ <= 1."},
        {"role": "assistant", "content": "Correct. Lesson: taking reciprocals of both sides of an inequality (same sign) must reverse its direction."},
    ]},
    {"problem_id": "D8", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "On [0,1], 1<=1+x^2<=2 => 1/2<=1/(1+x^2)<=1; integrating gives 1/2<=∫<=1."},
        {"role": "assistant", "content": "Correct. The true value is $\\pi/4\\approx0.785$. To tighten the bounds toward the true value, how would you refine the strategy?"},
        {"role": "user", "content": "Subdivide [0,1] into pieces, estimate each piece with its own max/min — finer subdivision gives tighter bounds approaching pi/4."},
        {"role": "assistant", "content": "Correct — that is precisely the spirit of refining upper and lower sums toward the integral. Clear thinking."},
    ]},

    # ===== D9: ∫_1^∞ dx/x^p convergence =====
    {"problem_id": "D9", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Whether this improper integral converges depends on p, and I don't know how to decide."},
        {"role": "assistant", "content": "By definition, an improper integral is computed up to $R$ first, then $R\\to\\infty$. Compute $\\int_1^R x^{-p}\\,dx$ (for $p\\ne1$) — what do you get?"},
        {"role": "user", "content": "= (R^{1-p} - 1)/(1-p)."},
        {"role": "assistant", "content": "Good. As $R\\to\\infty$, the limit of $R^{1-p}$ hinges on the sign of $1-p$. For $p>1$, where does it tend?"},
        {"role": "user", "content": "For p>1, 1-p<0, so R^{1-p} -> 0 and the limit is 1/(p-1): convergent."},
        {"role": "assistant", "content": "Exactly. And why do the remaining cases $p\\le1$ (hint: watch $R^{1-p}$ for $p<1$; the integral is $\\ln R$ for $p=1$) both diverge?"},
        {"role": "user", "content": "For p<1, R^{1-p} -> infinity: divergent. For p=1, ∫ = ln R -> infinity: also divergent. So convergence <=> p>1."},
        {"role": "assistant", "content": "Completely correct. The recipe: integrate to R, discuss the limit of $R^{1-p}$, and treat the logarithmic case $p=1$ separately."},
    ]},
    {"problem_id": "D9", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "The antiderivative of x^{-p} is x^{1-p}/(1-p) for every p — just plug in infinity."},
        {"role": "assistant", "content": "That antiderivative breaks at $p=1$ (zero denominator). What is the antiderivative of $\\int\\frac{dx}{x}$ when $p=1$?"},
        {"role": "user", "content": "It's ln x — I missed that special case. ∫_1^R dx/x = ln R -> infinity, divergent."},
        {"role": "assistant", "content": "Exactly. And for $p\\ne1$, by the limit of $R^{1-p}$, when does it converge?"},
        {"role": "user", "content": "For p>1, R^{1-p} -> 0: convergent; for p<1 it -> infinity: divergent. So convergence <=> p>1."},
        {"role": "assistant", "content": "Correct. Lesson: for power integrals, always treat the logarithmic case $p=1$ separately — the general formula does not apply."},
    ]},
    {"problem_id": "D9", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "For p!=1, ∫_1^R = (R^{1-p}-1)/(1-p): converges to 1/(p-1) for p>1; diverges for p<1 and for p=1 (ln R)."},
        {"role": "assistant", "content": "Completely correct. Compared with the series $\\sum 1/n^p$, the identical convergence threshold is no coincidence — which test underlies it?"},
        {"role": "user", "content": "The integral test: for a positive decreasing function, the series and its integral converge or diverge together, so both thresholds are p>1."},
        {"role": "assistant", "content": "Correct — you've unified the convergence of the integral and the series via the integral test. Well done."},
    ]},

    # ===== D10: integral Cauchy-Schwarz =====
    {"problem_id": "D10", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "The integral version of Cauchy-Schwarz — I have absolutely no idea how to start."},
        {"role": "assistant", "content": "There's a classic trick: build a quantity that is always nonnegative. For an arbitrary real $\\lambda$, what is the sign of $\\int(f-\\lambda g)^2$?"},
        {"role": "user", "content": "The integrand is a square, >=0, so ∫(f-λg)^2 >= 0 for every λ."},
        {"role": "assistant", "content": "Good. Expand it as a quadratic in $\\lambda$: $\\int f^2-2\\lambda\\int fg+\\lambda^2\\int g^2\\ge0$. Since this quadratic is always nonnegative, what must its discriminant satisfy?"},
        {"role": "user", "content": "Discriminant <= 0: (2∫fg)^2 - 4(∫g^2)(∫f^2) <= 0."},
        {"role": "assistant", "content": "Exactly. Rearranging that discriminant inequality gives the goal — which is?"},
        {"role": "user", "content": "(∫fg)^2 <= (∫f^2)(∫g^2)."},
        {"role": "assistant", "content": "Completely correct. The core maneuver: build the nonnegative quadratic $\\int(f-\\lambda g)^2$ and use discriminant $\\le0$."},
    ]},
    {"problem_id": "D10", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "I set the quadratic to have no real roots, so the discriminant is < 0, giving the strict inequality."},
        {"role": "assistant", "content": "Careful: the quadratic is \"always $\\ge0$\", not \"without real roots\" — it may have a double root (the equality case). So should the discriminant be $<0$ or $\\le0$?"},
        {"role": "user", "content": "It should be <=0, since some λ can make ∫(f-λg)^2 = 0 (when f and g are proportional), where the discriminant equals 0."},
        {"role": "assistant", "content": "Exactly — $\\le0$ covers the equality case. Rearranging the discriminant yields what conclusion?"},
        {"role": "user", "content": "(∫fg)^2 <= (∫f^2)(∫g^2), equality included."},
        {"role": "assistant", "content": "Correct. Lesson: an everywhere-nonnegative quadratic corresponds to discriminant $\\le0$; using $<0$ would drop the proportional (equality) case."},
    ]},
    {"problem_id": "D10", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "From ∫(f-λg)^2>=0, the quadratic in λ is always nonnegative, so the discriminant <=0, i.e. (∫fg)^2 <= ∫f^2 * ∫g^2."},
        {"role": "assistant", "content": "Completely correct. When $\\int g^2=0$ the quadratic term vanishes and it's no longer a quadratic — how do you patch this boundary case?"},
        {"role": "user", "content": "If ∫g^2=0, then by D1 g==0, so ∫fg=0 and both sides are 0 — the inequality still holds; just handle it separately."},
        {"role": "assistant", "content": "Correct — you covered the degenerate case. This argument is airtight."},
    ]},
]
