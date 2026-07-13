# -*- coding: utf-8 -*-
"""Topic D augmented dialogues: per problem 1 second-error variant + 3 short key-step
dialogues. English translation of src/dialogues_aug_D.py."""

DIALOGUES = [
    # ---- D1 ----
    {"problem_id": "D1", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "∫f=0 and f>=0, so the maximum of f must be 0, hence f == 0."},
        {"role": "assistant", "content": "\"The maximum is 0\" is part of what must be proved — it can't be assumed. Argue by contradiction instead: if $f(x_0)>0$ at some point, what does continuity do nearby?"},
        {"role": "user", "content": "On a nearby segment, f > f(x_0)/2 > 0."},
        {"role": "assistant", "content": "Exactly. Since $f\\ge0$, what positive lower bound does that segment give $\\int f$, producing the contradiction?"},
        {"role": "user", "content": ">= (f(x_0)/2)(d-c) > 0, contradicting ∫f=0."},
        {"role": "assistant", "content": "Correct. Lesson: continuity amplifies a single positive value into a segment — that's what yields the positive integral."},
    ]},
    {"problem_id": "D1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why can a whole segment with f > f(x_0)/2 be found?"},
        {"role": "assistant", "content": "By continuity with $\\varepsilon=f(x_0)/2$: near $x_0$ the difference between $f$ and $f(x_0)$ stays below it. So on that segment $f$ exceeds what?"},
        {"role": "user", "content": "Exceeds f(x_0)-eps = f(x_0)/2."},
        {"role": "assistant", "content": "Correct — continuity supplies the whole segment."},
    ]},
    {"problem_id": "D1", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "What happens if \"continuous\" is removed?"},
        {"role": "assistant", "content": "Counterexamples appear. Which $f\\ge0$ with $\\int=0$ is not identically zero, being nonzero only on a measure-zero set?"},
        {"role": "user", "content": "f equal to 1 at a single point and 0 elsewhere — the integral is still 0 but f is not identically 0."},
        {"role": "assistant", "content": "Correct — continuity rules that case out."},
    ]},
    {"problem_id": "D1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Where is the hypothesis f >= 0 used?"},
        {"role": "assistant", "content": "In extending the segment's positive integral to a bound for the whole $\\int_a^b f$. Since $f\\ge0$ elsewhere, the total integral is at least what?"},
        {"role": "user", "content": "At least the integral over that segment, hence > 0."},
        {"role": "assistant", "content": "Correct — nonnegativity prevents cancellation elsewhere."},
    ]},

    # ---- D2 ----
    {"problem_id": "D2", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "F(x)=∫f, and I say F'(x)=f(x) because integration and differentiation are inverse."},
        {"role": "assistant", "content": "\"Inverse\" is exactly what this theorem establishes. Starting from the derivative's definition, what integral does $\\frac{F(x+h)-F(x)}{h}$ equal?"},
        {"role": "user", "content": "(1/h) ∫_x^{x+h} f."},
        {"role": "assistant", "content": "Exactly. After subtracting $f(x)$, what bound — via continuity — dominates the difference and tends to zero?"},
        {"role": "user", "content": "It's dominated by sup_{|t-x|<=|h|}|f(t)-f(x)|, which tends to 0 as h->0."},
        {"role": "assistant", "content": "Correct. Lesson: the inverse relation must be proved, via the difference quotient plus a continuity estimate."},
    ]},
    {"problem_id": "D2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why write f(x) as (1/h) ∫_x^{x+h} f(x) dt?"},
        {"role": "assistant", "content": "Because $f(x)$ is a constant: integrating over $t$ and dividing by $h$ recovers it exactly. Into what form can it then merge with the quotient?"},
        {"role": "user", "content": "Into (1/h) ∫ (f(t)-f(x)) dt."},
        {"role": "assistant", "content": "Correct — one integral, ready to estimate."},
    ]},
    {"problem_id": "D2", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Do we only need continuity of f at that single point?"},
        {"role": "assistant", "content": "Yes. If $f$ is merely integrable but discontinuous at $x$, is $F$ still guaranteed differentiable there with $F'=f$?"},
        {"role": "user", "content": "Not necessarily — the pointwise differentiability of FTC-1 needs continuity at the point."},
        {"role": "assistant", "content": "Correct — continuity is the pointwise necessary condition."},
    ]},
    {"problem_id": "D2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why does that sup tend to 0?"},
        {"role": "assistant", "content": "As $h\\to0$, $t$ is confined to the $|h|$-neighborhood of $x$. By continuity, where does the sup of $|f(t)-f(x)|$ tend?"},
        {"role": "user", "content": "To 0."},
        {"role": "assistant", "content": "Correct — that squeezes out F'(x)=f(x)."},
    ]},

    # ---- D3 ----
    {"problem_id": "D3", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "For the integral MVT I take c to be the endpoint a — then f(a)(b-a) is the integral, right?"},
        {"role": "assistant", "content": "The endpoint value need not equal the average. $c$ must come from an argument. First: within what range of $f$'s values does $\\frac1{b-a}\\int f$ lie?"},
        {"role": "user", "content": "Within [m, M] (min to max)."},
        {"role": "assistant", "content": "Exactly. A continuous function attains everything in $[m,M]$ — which theorem guarantees a $c$ with $f(c)$ equal to the average?"},
        {"role": "user", "content": "The intermediate value theorem. c exists but its location is undetermined."},
        {"role": "assistant", "content": "Correct. Lesson: $c$ exists by the IVT — it can't be decreed to be an endpoint or midpoint."},
    ]},
    {"problem_id": "D3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is m(b-a) <= ∫f <= M(b-a)?"},
        {"role": "assistant", "content": "From $m\\le f\\le M$ holding pointwise, what does integrating (monotonicity) over a length $b-a$ give?"},
        {"role": "user", "content": "It gives m(b-a) <= ∫f <= M(b-a)."},
        {"role": "assistant", "content": "Correct — a constant integrates to the constant times the length."},
    ]},
    {"problem_id": "D3", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "How many times does this theorem use continuity of f?"},
        {"role": "assistant", "content": "Twice: once to attain $m,M$ (extreme value theorem), once to attain intermediate values. Which theorem is the latter?"},
        {"role": "user", "content": "The intermediate value theorem."},
        {"role": "assistant", "content": "Correct — continuity plays a double role."},
    ]},
    {"problem_id": "D3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "What is the average value mu?"},
        {"role": "assistant", "content": "$\\mu=\\frac1{b-a}\\int_a^b f$. In which closed interval must it lie so the IVT can attain it?"},
        {"role": "user", "content": "In [m, M]."},
        {"role": "assistant", "content": "Correct — that guarantees f(c)=mu has a solution."},
    ]},

    # ---- D4 ----
    {"problem_id": "D4", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "f<=g, and integrating both sides automatically preserves the inequality — that's a property of integrals."},
        {"role": "assistant", "content": "That property is exactly what's being proved. Back to definitions: with $h=g-f\\ge0$, what sign do its lower sums have, and hence $\\int h$?"},
        {"role": "user", "content": "Lower sums >= 0 (each inf h >= 0), so ∫h >= 0."},
        {"role": "assistant", "content": "Exactly. By linearity $\\int g-\\int f=\\int h$ — giving what?"},
        {"role": "user", "content": ">= 0, i.e. ∫f <= ∫g."},
        {"role": "assistant", "content": "Correct. Lesson: monotonicity is derived from \"nonnegative integrals + linearity\"."},
    ]},
    {"problem_id": "D4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is the integral of a nonnegative function nonnegative?"},
        {"role": "assistant", "content": "Because on each subinterval $m_i=\\inf h\\ge0$, so every lower sum $\\sum m_i\\Delta x_i\\ge0$. What is the integral relative to lower sums?"},
        {"role": "user", "content": "It's their supremum, hence also >= 0."},
        {"role": "assistant", "content": "Correct — nonnegativity passes from lower sums to the integral."},
    ]},
    {"problem_id": "D4", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "If f<g strictly, does ∫f<∫g hold strictly?"},
        {"role": "assistant", "content": "Not necessarily — unless $g-f$ is continuous and positive on some segment. Why is strictness at single points insufficient?"},
        {"role": "user", "content": "Single points don't affect the integral; a whole positive segment is needed for strictness."},
        {"role": "assistant", "content": "Correct — the same principle as in D1."},
    ]},
    {"problem_id": "D4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why set h = g-f?"},
        {"role": "assistant", "content": "Because comparing two functions becomes the easier question of \"the sign of one nonnegative function's integral\". What gives $h\\ge0$?"},
        {"role": "user", "content": "The hypothesis f <= g."},
        {"role": "assistant", "content": "Correct — moving terms to one side is the pivotal simplification."},
    ]},

    # ---- D5 ----
    {"problem_id": "D5", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "|∫f| <= ∫|f| because absolute values always add up bigger — just write it down."},
        {"role": "assistant", "content": "The intuition is fine, but rigor is needed. From which pointwise inequality do you start, then apply monotonicity of the integral?"},
        {"role": "user", "content": "-|f| <= f <= |f|; integrating gives -∫|f| <= ∫f <= ∫|f|."},
        {"role": "assistant", "content": "Exactly. $-A\\le\\int f\\le A$ is equivalent to which absolute-value inequality?"},
        {"role": "user", "content": "|∫f| <= A = ∫|f|."},
        {"role": "assistant", "content": "Correct. Lesson: pointwise squeeze plus monotonicity beats vague intuition."},
    ]},
    {"problem_id": "D5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why does -|f| <= f <= |f| hold?"},
        {"role": "assistant", "content": "It's the basic property of real absolute values, holding for each $x$. Does $f(x)$ always lie between $\\pm|f(x)|$?"},
        {"role": "user", "content": "Yes — every real number lies between plus and minus its absolute value."},
        {"role": "assistant", "content": "Correct — pointwise validity is what allows integration."},
    ]},
    {"problem_id": "D5", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Does integrability of f guarantee that of |f|?"},
        {"role": "assistant", "content": "Yes — taking absolute values doesn't increase the oscillation $M_i-m_i$ on subintervals. So what about $\\int|f|$?"},
        {"role": "user", "content": "It is well defined (integrable), so the right side makes sense."},
        {"role": "assistant", "content": "Correct — you've patched the integrability premise."},
    ]},
    {"problem_id": "D5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Is this related to the triangle inequality?"},
        {"role": "assistant", "content": "Yes — it's the integral version. The discrete $|\\sum a_i|\\le\\sum|a_i|$ corresponds to what in the continuous setting?"},
        {"role": "user", "content": "To |∫f| <= ∫|f|."},
        {"role": "assistant", "content": "Correct — the discrete-to-continuous analogy."},
    ]},

    # ---- D6 ----
    {"problem_id": "D6", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "∫_a^b f = F(b)-F(a) because F is an antiderivative — just substitute."},
        {"role": "assistant", "content": "That's the formula to be proved. First build $G(x)=\\int_a^x f$ via FTC-1 — how do its and $F$'s derivatives relate?"},
        {"role": "user", "content": "G'=f=F', so G-F is a constant."},
        {"role": "assistant", "content": "Exactly. Fix the constant via $G(a)=0$, then substitute $x=b$ — what results?"},
        {"role": "user", "content": "∫_a^b f = G(b) = F(b)-F(a)."},
        {"role": "assistant", "content": "Correct. Lesson: connect the integral-defined antiderivative to F via \"equal derivatives differ by a constant\"."},
    ]},
    {"problem_id": "D6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "How is the constant C pinned down?"},
        {"role": "assistant", "content": "Substitute $x=a$: $G(a)-F(a)=C$. What is $G(a)=\\int_a^a f$, and hence $C$?"},
        {"role": "user", "content": "G(a)=0, so C = -F(a)."},
        {"role": "assistant", "content": "Correct — the endpoint fixes the constant."},
    ]},
    {"problem_id": "D6", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "How is part 2 proved when f is merely integrable (not continuous)?"},
        {"role": "assistant", "content": "Use a partition and apply the MVT to $F$ on each subinterval: $\\sum f(c_i)\\Delta x_i=F(b)-F(a)$, then take the limit. Where does this sum tend?"},
        {"role": "user", "content": "To ∫_a^b f, so the formula holds."},
        {"role": "assistant", "content": "Correct — the general proof independent of FTC-1."},
    ]},
    {"problem_id": "D6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is G-F a constant?"},
        {"role": "assistant", "content": "Because $(G-F)'=G'-F'=f-f=0$. What is a function with identically zero derivative on an interval?"},
        {"role": "user", "content": "A constant."},
        {"role": "assistant", "content": "Correct — that uses the result of C5."},
    ]},

    # ---- D7 ----
    {"problem_id": "D7", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "A continuous function is continuous at each point, so each piece oscillates little, hence U-L is small and it's integrable."},
        {"role": "assistant", "content": "The pointwise $\\delta$ varies with the point and can't shrink all subintervals at once. To which form of continuity must you upgrade?"},
        {"role": "user", "content": "Uniform continuity (Heine-Cantor), supplying a universal delta."},
        {"role": "assistant", "content": "Exactly. With a partition finer than $\\delta$, to what is $U-L=\\sum(M_i-m_i)\\Delta x_i$ pinned?"},
        {"role": "user", "content": "<= eps, hence integrable."},
        {"role": "assistant", "content": "Correct. Lesson: integrability needs uniform continuity's universal $\\delta$."},
    ]},
    {"problem_id": "D7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "What is the criterion for integrability?"},
        {"role": "assistant", "content": "The Riemann criterion: some partition makes the upper-lower gap arbitrarily small. What must $U-L$ be shown smaller than here?"},
        {"role": "user", "content": "Smaller than any eps."},
        {"role": "assistant", "content": "Correct — one of the equivalent characterizations of integrability."},
    ]},
    {"problem_id": "D7", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Why are M_i and m_i necessarily attained?"},
        {"role": "assistant", "content": "Because $f$ is continuous on each closed subinterval — which theorem guarantees the max and min are reached?"},
        {"role": "user", "content": "The extreme value theorem."},
        {"role": "assistant", "content": "Correct — that's what makes M_i - m_i meaningful."},
    ]},
    {"problem_id": "D7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is each M_i - m_i <= eps/(b-a)?"},
        {"role": "assistant", "content": "Each subinterval is shorter than $\\delta$, so any two of its points are within $\\delta$. By uniform continuity, their function values differ by less than what?"},
        {"role": "user", "content": "Less than eps/(b-a), so the max-min gap is pinned by it too."},
        {"role": "assistant", "content": "Correct — the universal delta controls every piece simultaneously."},
    ]},

    # ---- D8 ----
    {"problem_id": "D8", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "I computed ∫_0^1 1/(1+x^2) = arctan 1 = pi/4, but the problem only asks for bounds — should I even compute it?"},
        {"role": "assistant", "content": "The exact value is of course correct, but the problem trains ESTIMATION. Without integrating, first squeeze the integrand: where does $\\frac1{1+x^2}$ lie on $[0,1]$?"},
        {"role": "user", "content": "1/2 <= 1/(1+x^2) <= 1; integrating gives 1/2 <= ∫ <= 1."},
        {"role": "assistant", "content": "Exactly — and $\\pi/4\\approx0.785$ indeed falls inside."},
        {"role": "user", "content": "Got it — estimation doesn't require evaluating the integral itself."},
        {"role": "assistant", "content": "Correct. Lesson: for bounds, squeeze the integrand and multiply by the interval length."},
    ]},
    {"problem_id": "D8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why does taking reciprocals of 1<=1+x^2<=2 give 1/2<=...<=1?"},
        {"role": "assistant", "content": "Reciprocals of same-sign quantities reverse the inequality. A larger denominator gives a smaller reciprocal — so the maximum $2$ of $1+x^2$ corresponds to what?"},
        {"role": "user", "content": "To the minimum value 1/2."},
        {"role": "assistant", "content": "Correct — the direction must flip."},
    ]},
    {"problem_id": "D8", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "How can the bounds be tightened toward pi/4?"},
        {"role": "assistant", "content": "Subdivide $[0,1]$ into pieces, estimating each with its own max/min. As the subdivision refines, what do the bounds do?"},
        {"role": "user", "content": "They approach the true value pi/4."},
        {"role": "assistant", "content": "Correct — exactly the spirit of refining upper and lower sums."},
    ]},
    {"problem_id": "D8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why multiply by 1 (the interval length)?"},
        {"role": "assistant", "content": "Because $[0,1]$ has length $1$. A constant bound integrated over length $L$ gives the constant times $L$ — what is $L$ here?"},
        {"role": "user", "content": "L = 1."},
        {"role": "assistant", "content": "Correct — so the bounds are the constants themselves."},
    ]},

    # ---- D9 ----
    {"problem_id": "D9", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "It converges for p=2, so I guess it converges for every p."},
        {"role": "assistant", "content": "A single case can't extend to all. The key is the limit of $R^{1-p}$. For $p<1$, $1-p>0$ — where does $R^{1-p}$ tend?"},
        {"role": "user", "content": "-> infinity, so p<1 diverges. And p=1 gives ln R, also divergent."},
        {"role": "assistant", "content": "Exactly. So what is the convergence condition?"},
        {"role": "user", "content": "p > 1."},
        {"role": "assistant", "content": "Correct. Lesson: discuss the sign of the exponent $1-p$ in full — never generalize from one example."},
    ]},
    {"problem_id": "D9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "What is the definition of convergence for an improper integral?"},
        {"role": "assistant", "content": "Integrate up to a finite bound $R$, then let $R\\to\\infty$. When the limit exists and is finite, it's called what?"},
        {"role": "user", "content": "Convergent."},
        {"role": "assistant", "content": "Correct — that's the starting point of the analysis."},
    ]},
    {"problem_id": "D9", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Why must p=1 be computed separately?"},
        {"role": "assistant", "content": "Because the general antiderivative $\\frac{x^{1-p}}{1-p}$ fails at $p=1$ (zero denominator). What does the antiderivative become at $p=1$?"},
        {"role": "user", "content": "ln x, and ∫_1^R dx/x = ln R -> infinity."},
        {"role": "assistant", "content": "Correct — the logarithmic case must be listed separately."},
    ]},
    {"problem_id": "D9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Is it coincidence that the threshold matches sum 1/n^p?"},
        {"role": "assistant", "content": "No. Which test binds the series of a positive decreasing function to its integral?"},
        {"role": "user", "content": "The integral test — so both thresholds are p>1."},
        {"role": "assistant", "content": "Correct — they are intrinsically linked."},
    ]},

    # ---- D10 ----
    {"problem_id": "D10", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "For ∫fg I use |fg| <= (f^2+g^2)/2 and integrate, getting ∫fg <= (∫f^2+∫g^2)/2 — is that Cauchy-Schwarz?"},
        {"role": "assistant", "content": "That's AM-GM, which gives a different (weaker) bound. For Cauchy-Schwarz, which nonnegative quantity with parameter $\\lambda$ should you build?"},
        {"role": "user", "content": "∫(f-λg)^2 >= 0, expanded as a quadratic in λ."},
        {"role": "assistant", "content": "Exactly. What must the discriminant of an everywhere-nonnegative quadratic satisfy, rearranging into the goal?"},
        {"role": "user", "content": "Discriminant <= 0, giving (∫fg)^2 <= ∫f^2 * ∫g^2."},
        {"role": "assistant", "content": "Correct. Lesson: Cauchy-Schwarz runs on the parametrized nonnegative quadratic + discriminant — not on AM-GM."},
    ]},
    {"problem_id": "D10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is ∫(f-λg)^2 >= 0?"},
        {"role": "assistant", "content": "The integrand is a square, pointwise nonnegative. What is the sign of the integral of a nonnegative function?"},
        {"role": "user", "content": "Nonnegative, so the whole integral >= 0."},
        {"role": "assistant", "content": "Correct — that's the launching point of the proof."},
    ]},
    {"problem_id": "D10", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Should the discriminant be < 0 or <= 0?"},
        {"role": "assistant", "content": "The quadratic is everywhere \"$\\ge0$\", not \"without real roots\" — a double root (equality) is possible. So which discriminant condition?"},
        {"role": "user", "content": "<= 0, to cover the equality case where f and g are proportional."},
        {"role": "assistant", "content": "Correct — \"< 0\" would drop the equality case."},
    ]},
    {"problem_id": "D10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "What about the special case ∫g^2 = 0?"},
        {"role": "assistant", "content": "Then the quadratic term vanishes and it's no longer a quadratic. By D1, $g^2\\ge0$ continuous with zero integral implies $g$ is what?"},
        {"role": "user", "content": "g == 0, so both sides are 0 and the inequality still holds."},
        {"role": "assistant", "content": "Correct — the degenerate case is handled separately."},
    ]},
]
