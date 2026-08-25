# -*- coding: utf-8 -*-
"""Topic C augmented dialogues: per problem 1 second-error variant + 3 short key-step
dialogues. English translation of src/dialogues_aug_C.py."""

DIALOGUES = [
    # ---- C1 ----
    {"problem_id": "C1", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "I just write lim f(x) = f(x_0) — f is defined there, so it's continuous."},
        {"role": "assistant", "content": "\"Defined\" is not the same as \"the limit equals the function value\". To prove the latter, can $f(x)-f(x_0)$ be massaged into a product involving the difference quotient?"},
        {"role": "user", "content": "Yes: [f(x)-f(x_0)]/(x-x_0) * (x-x_0)."},
        {"role": "assistant", "content": "Exactly. As $x\\to x_0$, where does each factor tend, and what is the product?"},
        {"role": "user", "content": "-> f'(x_0)*0 = 0, so f(x) -> f(x_0): continuous."},
        {"role": "assistant", "content": "Correct. Lesson: continuity means limit = value, proved via the difference-quotient product — not via \"being defined\"."},
    ]},
    {"problem_id": "C1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why may we multiply and divide by (x-x_0)?"},
        {"role": "assistant", "content": "Because in the limit $x\\to x_0$ we have $x\\ne x_0$. What does that guarantee about the denominator, legalizing the operation?"},
        {"role": "user", "content": "The denominator x-x_0 != 0, so multiplying and dividing is fine."},
        {"role": "assistant", "content": "Correct — the limit process excludes the point of equality."},
    ]},
    {"problem_id": "C1", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "What does the continuous-but-not-differentiable example show?"},
        {"role": "assistant", "content": "$|x|$ is continuous at $0$ but not differentiable — what does that say about the relative strength of differentiability and continuity?"},
        {"role": "user", "content": "Differentiability is stronger: differentiable => continuous but not conversely."},
        {"role": "assistant", "content": "Correct — the implication is one-way."},
    ]},
    {"problem_id": "C1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is the limit of the difference-quotient factor f'(x_0)?"},
        {"role": "assistant", "content": "Because the limit of $\\frac{f(x)-f(x_0)}{x-x_0}$ is precisely the definition of the derivative. What does the differentiability hypothesis guarantee about that limit?"},
        {"role": "user", "content": "It exists and is finite, equal to f'(x_0)."},
        {"role": "assistant", "content": "Correct — finiteness makes the product vanish."},
    ]},

    # ---- C2 ----
    {"problem_id": "C2", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "I say f(a)=f(b), so somewhere in between there must be a horizontal tangent — take that point as c."},
        {"role": "assistant", "content": "That's a picture, not a proof. $c$ must come from theorems. What does continuity of $f$ on $[a,b]$ guarantee is attained, as the source of $c$?"},
        {"role": "user", "content": "A maximum and a minimum (extreme value theorem)."},
        {"role": "assistant", "content": "Exactly. If $f$ is not constant, an extremum falls in the interior — which theorem gives $f'(c)=0$?"},
        {"role": "user", "content": "Fermat's theorem."},
        {"role": "assistant", "content": "Correct. Lesson: Rolle's $c$ comes from EVT + Fermat, not from geometric intuition."},
    ]},
    {"problem_id": "C2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why does the constant case need separate treatment?"},
        {"role": "assistant", "content": "If $M=m$ (max equals min), $f$ is constant — what is $f'$ everywhere then?"},
        {"role": "user", "content": "Zero everywhere; any c works."},
        {"role": "assistant", "content": "Correct — in the constant case the extrema may all sit at the endpoints, so it's stated separately."},
    ]},
    {"problem_id": "C2", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Why must an extremum be interior in the non-constant case?"},
        {"role": "assistant", "content": "By $f(a)=f(b)$: if both the max and the min sat at the endpoints, the equal endpoint values would force $f$ constant. So for non-constant $f$, at least one extremum lies where?"},
        {"role": "user", "content": "In the interior (a,b)."},
        {"role": "assistant", "content": "Correct — which is what lets Fermat's theorem act."},
    ]},
    {"problem_id": "C2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Which hypotheses does Rolle use?"},
        {"role": "assistant", "content": "Continuity (on $[a,b]$), differentiability (on $(a,b)$), and equal endpoint values. Continuity feeds the EVT — where does differentiability act?"},
        {"role": "user", "content": "In Fermat's theorem, guaranteeing f'(c) exists and equals 0."},
        {"role": "assistant", "content": "Correct — each hypothesis has its own job."},
    ]},

    # ---- C3 ----
    {"problem_id": "C3", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "For the MVT I apply Rolle directly to f and say f'(c) = the secant slope."},
        {"role": "assistant", "content": "Rolle requires $f(a)=f(b)$, which needn't hold here. You must first build a function with equal endpoints — how do you subtract the secant from $f$?"},
        {"role": "user", "content": "g(x) = f(x) - f(a) - [(f(b)-f(a))/(b-a)](x-a), making g(a)=g(b)=0."},
        {"role": "assistant", "content": "Exactly. Applying Rolle to $g$, what does expanding $g'(c)=0$ give?"},
        {"role": "user", "content": "f'(c) = (f(b)-f(a))/(b-a)."},
        {"role": "assistant", "content": "Correct. Lesson: $f$ fails Rolle's premise — subtract the secant to build the auxiliary function."},
    ]},
    {"problem_id": "C3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "What is the geometric meaning of g(x)?"},
        {"role": "assistant", "content": "It's the vertical gap at $x$ between the graph of $f$ and the secant line. Why is that gap $0$ at the endpoints?"},
        {"role": "user", "content": "Because the secant equals f exactly at a and b, so the gap vanishes."},
        {"role": "assistant", "content": "Correct — that's what secures Rolle's premise."},
    ]},
    {"problem_id": "C3", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Why is g'(x) = f'(x) minus the slope?"},
        {"role": "assistant", "content": "Differentiate $g$ term by term: what constant is the derivative of the secant part $\\frac{f(b)-f(a)}{b-a}(x-a)$?"},
        {"role": "user", "content": "It's (f(b)-f(a))/(b-a), so g' = f' minus that slope."},
        {"role": "assistant", "content": "Correct — the secant slope is a constant."},
    ]},
    {"problem_id": "C3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "How do you verify g(b)=0?"},
        {"role": "assistant", "content": "Substitute $x=b$: $g(b)=f(b)-f(a)-\\frac{f(b)-f(a)}{b-a}(b-a)$. Why do the last terms cancel?"},
        {"role": "user", "content": "The last term equals f(b)-f(a), which cancels the front, giving 0."},
        {"role": "assistant", "content": "Correct — the endpoint value vanishes."},
    ]},

    # ---- C4 ----
    {"problem_id": "C4", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "I apply Lagrange to f/g and directly get (f/g)'(c) = ..."},
        {"role": "assistant", "content": "The derivative of $f/g$ follows the quotient rule and won't produce the target ratio. To force a single shared $c$, which linear combination should you build?"},
        {"role": "user", "content": "h = (f(b)-f(a))g - (g(b)-g(a))f, and apply Rolle to it."},
        {"role": "assistant", "content": "Exactly. After $h(a)=h(b)$, Rolle gives $h'(c)=0$ — rearranged into what?"},
        {"role": "user", "content": "f'(c)/g'(c) = (f(b)-f(a))/(g(b)-g(a))."},
        {"role": "assistant", "content": "Correct. Lesson: build the linear combination $h$; don't force Lagrange onto the quotient $f/g$."},
    ]},
    {"problem_id": "C4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why must we ensure g(b) != g(a)?"},
        {"role": "assistant", "content": "Because the conclusion divides by $g(b)-g(a)$. If it were zero, Rolle would give a point with $g'=0$ — contradicting which hypothesis?"},
        {"role": "user", "content": "Contradicting g' != 0, so g(b) != g(a)."},
        {"role": "assistant", "content": "Correct — divisibility is thereby secured."},
    ]},
    {"problem_id": "C4", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "What does the Cauchy MVT degenerate to with g(x)=x?"},
        {"role": "assistant", "content": "Then $g(b)-g(a)=b-a$ and $g'=1$ — the ratio becomes which familiar theorem?"},
        {"role": "user", "content": "The Lagrange mean value theorem."},
        {"role": "assistant", "content": "Correct — Lagrange is the special case of Cauchy."},
    ]},
    {"problem_id": "C4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why doesn't applying Lagrange twice separately work?"},
        {"role": "assistant", "content": "Because two applications give two different intermediate points $c_1,c_2$. Division requires the SAME $c$ — guaranteed by what?"},
        {"role": "user", "content": "By a single Rolle application to the one auxiliary function h."},
        {"role": "assistant", "content": "Correct — the shared c is the crux."},
    ]},

    # ---- C5 ----
    {"problem_id": "C5", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "f'=0 on the whole domain — even if the domain has two pieces, f is still one constant, right?"},
        {"role": "assistant", "content": "If the domain is two disjoint intervals, each piece can take a different constant. For the mean value theorem, where must everything between $x_1$ and $x_2$ lie?"},
        {"role": "user", "content": "Inside one interval (connected), or the MVT can't be applied."},
        {"role": "assistant", "content": "Exactly. So the conclusion \"constant\" must be restricted to what?"},
        {"role": "user", "content": "To an interval; if disconnected, each piece is separately constant."},
        {"role": "assistant", "content": "Correct. Lesson: \"zero derivative implies constant\" needs the domain to be an interval (connected)."},
    ]},
    {"problem_id": "C5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "How do you turn \"constant\" into something provable?"},
        {"role": "assistant", "content": "Into \"any two values agree\". For any $x_1<x_2$, which theorem links the difference of values to the derivative?"},
        {"role": "user", "content": "The mean value theorem: f(x_2)-f(x_1) = f'(c)(x_2-x_1)."},
        {"role": "assistant", "content": "Correct — that is the central bridge."},
    ]},
    {"problem_id": "C5", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Does this imply antiderivatives differ by a constant?"},
        {"role": "assistant", "content": "Yes. If $f'=g'$, applying this result to $f-g$ shows $f-g$ is what?"},
        {"role": "user", "content": "(f-g)'=0 so f-g is constant, i.e. f=g+C."},
        {"role": "assistant", "content": "Correct — exactly the basis for uniqueness of antiderivatives up to a constant."},
    ]},
    {"problem_id": "C5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why does f'(c)=0 give f(x_2)=f(x_1)?"},
        {"role": "assistant", "content": "Substitute into the MVT identity $f(x_2)-f(x_1)=f'(c)(x_2-x_1)$: with $f'(c)=0$, what is the right side?"},
        {"role": "user", "content": "The right side is 0, so f(x_2)=f(x_1)."},
        {"role": "assistant", "content": "Correct — the two values agree."},
    ]},

    # ---- C6 ----
    {"problem_id": "C6", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "f' >= 0 gives strictly increasing, right?"},
        {"role": "assistant", "content": "$f'\\ge0$ gives only non-strict increase. $f(x)=x^3$ has $f'(0)=0$ yet is strictly increasing — but does $f'\\ge0$ in general guarantee strictness?"},
        {"role": "user", "content": "No — a constant function has f'=0>=0 but isn't strictly increasing. Strictness needs f'>0."},
        {"role": "assistant", "content": "Exactly. This problem assumes $f'>0$ — what sign does the MVT give $f(x_2)-f(x_1)$?"},
        {"role": "user", "content": "> 0, hence strictly increasing."},
        {"role": "assistant", "content": "Correct. Lesson: $f'>0$ guarantees strict increase; $f'\\ge0$ only the non-strict version."},
    ]},
    {"problem_id": "C6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why the MVT, rather than just saying \"the slope is positive\"?"},
        {"role": "assistant", "content": "\"Positive slope\" is local information; the MVT is what reaches \"comparison of any two points\". As what does it write $f(x_2)-f(x_1)$?"},
        {"role": "user", "content": "As f'(c)(x_2-x_1), converting a local derivative into a global difference."},
        {"role": "assistant", "content": "Correct — the bridge from local to global."},
    ]},
    {"problem_id": "C6", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Is the converse \"strictly increasing => f'>0\" true?"},
        {"role": "assistant", "content": "No. Which strictly increasing function has a zero derivative somewhere, serving as the counterexample?"},
        {"role": "user", "content": "x^3, with f'(0)=0 — so only f'>=0 can be concluded."},
        {"role": "assistant", "content": "Correct — monotonicity and derivative sign are not equivalent."},
    ]},
    {"problem_id": "C6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Does c always exist?"},
        {"role": "assistant", "content": "On the closed interval between $x_1<x_2$, $f$ is continuous and differentiable inside — the MVT guarantees $c$ lies where?"},
        {"role": "user", "content": "Inside (x_1, x_2); it exists."},
        {"role": "assistant", "content": "Correct — once the hypotheses hold, existence is guaranteed."},
    ]},

    # ---- C7 ----
    {"problem_id": "C7", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "If the maximum is at an endpoint, f'=0 there too, right?"},
        {"role": "assistant", "content": "An endpoint has only one side, so only the sign of a one-sided derivative follows. What kind of point does Fermat's theorem require the extremum to be?"},
        {"role": "user", "content": "An interior point — only there do the two sides squeeze out f'=0."},
        {"role": "assistant", "content": "Exactly. At an interior point the left derivative is $\\ge0$ and the right $\\le0$ — differentiability equates them, giving what?"},
        {"role": "user", "content": "f'(c) = 0."},
        {"role": "assistant", "content": "Correct. Lesson: Fermat is restricted to interior points; endpoint extrema needn't have zero derivative."},
    ]},
    {"problem_id": "C7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is the right derivative <= 0?"},
        {"role": "assistant", "content": "From $f(c+h)\\le f(c)$: as $h\\to0^+$ the quotient has numerator $\\le0$ and denominator $>0$ — so what is its sign?"},
        {"role": "user", "content": "<= 0, hence the right derivative <= 0."},
        {"role": "assistant", "content": "Correct — numerator and denominator decide the sign."},
    ]},
    {"problem_id": "C7", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Is f'(c)=0 sufficient for an extremum?"},
        {"role": "assistant", "content": "No. $x^3$ has $f'(0)=0$ without an extremum at $0$ — so $f'(c)=0$ is only what kind of condition?"},
        {"role": "user", "content": "Necessary but not sufficient."},
        {"role": "assistant", "content": "Correct — a critical point need not be an extremum."},
    ]},
    {"problem_id": "C7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why look at both one-sided derivatives?"},
        {"role": "assistant", "content": "Because the right gives $\\le0$ and the left gives $\\ge0$. Differentiability makes them equal — what is the only value satisfying both?"},
        {"role": "user", "content": "0."},
        {"role": "assistant", "content": "Correct — the two sides squeeze out zero."},
    ]},

    # ---- C8 ----
    {"problem_id": "C8", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "I use |f(x)-f(y)| = |∫_y^x f'| <= M|x-y| — but the problem only says differentiable."},
        {"role": "assistant", "content": "The integral route needs the extra premise that $f'$ is integrable (e.g. continuous). Using differentiability alone, which theorem gives the same conclusion directly?"},
        {"role": "user", "content": "The mean value theorem: f(x)-f(y) = f'(c)(x-y)."},
        {"role": "assistant", "content": "Exactly. Taking absolute values with $|f'(c)|\\le M$ gives what?"},
        {"role": "user", "content": "|f(x)-f(y)| <= M|x-y|."},
        {"role": "assistant", "content": "Correct. Lesson: with only differentiability, the MVT has the fewest premises and is safest."},
    ]},
    {"problem_id": "C8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Is the Lipschitz constant exactly M?"},
        {"role": "assistant", "content": "Yes — in $|f(x)-f(y)|\\le M|x-y|$ the $M$ is precisely the derivative bound. What weaker form of continuity does it also guarantee?"},
        {"role": "user", "content": "Uniform continuity (take delta = eps/M)."},
        {"role": "assistant", "content": "Correct — Lipschitz implies uniform continuity."},
    ]},
    {"problem_id": "C8", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "How do Lipschitz and uniform continuity compare in strength?"},
        {"role": "assistant", "content": "Lipschitz $\\Rightarrow$ uniformly continuous, while $\\sqrt{x}$ is uniformly continuous but not Lipschitz — what does that say?"},
        {"role": "user", "content": "Lipschitz is strictly stronger."},
        {"role": "assistant", "content": "Correct — the implication is one-way."},
    ]},
    {"problem_id": "C8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Does the case x=y need handling?"},
        {"role": "assistant", "content": "One sentence suffices. For $x=y$, what are the two sides of the inequality — does it hold?"},
        {"role": "user", "content": "Both sides are 0, so it holds."},
        {"role": "assistant", "content": "Correct — the boundary case is covered."},
    ]},

    # ---- C9 ----
    {"problem_id": "C9", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "I use |sin x - sin y| <= |x|+|y| since each |sin| <= 1... no wait, that seems too loose."},
        {"role": "assistant", "content": "That bound is both too loose and aimed wrong. Instead view $\\sin$ as a function evaluated at two points and apply the MVT — what is its derivative bound?"},
        {"role": "user", "content": "Use the MVT with f=sin, f'=cos, |cos| <= 1."},
        {"role": "assistant", "content": "Exactly. $\\sin x-\\sin y=\\cos c(x-y)$ — what do absolute values give?"},
        {"role": "user", "content": "|sin x - sin y| <= |x-y|."},
        {"role": "assistant", "content": "Correct. Lesson: the MVT with the derivative bound gives the tight Lipschitz constant 1."},
    ]},
    {"problem_id": "C9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Is this problem related to the Lipschitz one?"},
        {"role": "assistant", "content": "Yes — it's the special case of $|f'|\\le M$. What is $\\sin$'s derivative bound $M$, hence its Lipschitz constant?"},
        {"role": "user", "content": "M=1, so the constant is 1."},
        {"role": "assistant", "content": "Correct — apply C8's conclusion directly."},
    ]},
    {"problem_id": "C9", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Is the constant 1 optimal?"},
        {"role": "assistant", "content": "Consider $x,y\\to0$: $\\frac{|\\sin x-\\sin y|}{|x-y|}$ approaches $|\\cos0|$ — which is?"},
        {"role": "user", "content": "It approaches 1, so the constant 1 is optimal and can't be lowered."},
        {"role": "assistant", "content": "Correct — the derivative's value at 0 decides the optimal constant."},
    ]},
    {"problem_id": "C9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Where does c come from?"},
        {"role": "assistant", "content": "From the MVT — $c$ is some point between $x$ and $y$. Do we need to know its exact location?"},
        {"role": "user", "content": "No — |cos c| <= 1 is all we need."},
        {"role": "assistant", "content": "Correct — the bound doesn't depend on where c is."},
    ]},

    # ---- C10 ----
    {"problem_id": "C10", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "I use ln(1+x) ~ x (first-order Taylor), so ln(1+x) < x."},
        {"role": "assistant", "content": "An approximation is not a strict inequality, and it gives no lower bound. The MVT yields both strict bounds at once — what identity does it give for $\\ln(1+t)$ on $[0,x]$?"},
        {"role": "user", "content": "ln(1+x) = x/(1+xi), with xi in (0,x)."},
        {"role": "assistant", "content": "Exactly. Squeezing $\\frac1{1+\\xi}$ from $0<\\xi<x$ and multiplying by $x$ gives what?"},
        {"role": "user", "content": "x/(1+x) < ln(1+x) < x."},
        {"role": "assistant", "content": "Correct. Lesson: the MVT identity yields strict two-sided bounds — better than approximation."},
    ]},
    {"problem_id": "C10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "How can one identity give both bounds?"},
        {"role": "assistant", "content": "Because in $\\ln(1+x)=\\frac{x}{1+\\xi}$ the $\\xi$ has range $(0,x)$. Between which two values does $\\frac1{1+\\xi}$ then lie?"},
        {"role": "user", "content": "Between 1/(1+x) and 1; multiplying by x gives the two-sided bound."},
        {"role": "assistant", "content": "Correct — the range of $\\xi$ converts into upper and lower bounds."},
    ]},
    {"problem_id": "C10", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "What needs care for x in (-1,0)?"},
        {"role": "assistant", "content": "For $x<0$, multiplying by a negative flips inequalities, and the interval becomes $[x,0]$. Which two expressions swap their order?"},
        {"role": "user", "content": "x/(1+x) and x swap order and must be rearranged."},
        {"role": "assistant", "content": "Correct — the sign flip on negative intervals is the trap."},
    ]},
    {"problem_id": "C10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why does ln(1+x) - ln 1 equal ln(1+x)?"},
        {"role": "assistant", "content": "Because $\\ln1=0$. Applying the MVT on $[0,x]$, what is the left endpoint value $f(0)=\\ln(1+0)$?"},
        {"role": "user", "content": "= ln 1 = 0, so the difference is just ln(1+x)."},
        {"role": "assistant", "content": "Correct — the left endpoint vanishes."},
    ]},
]
