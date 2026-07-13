# -*- coding: utf-8 -*-
"""Topic C core dialogues (C1-C10 x 3 personas). English translation of src/dialogues_C.py."""

DIALOGUES = [
    # ===== C1: differentiable => continuous =====
    {"problem_id": "C1", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Differentiable implies continuous feels obvious, but when asked to prove it I don't know where to start."},
        {"role": "assistant", "content": "The goal for continuity is $\\lim_{x\\to x_0}(f(x)-f(x_0))=0$. Can you massage $f(x)-f(x_0)$ into something involving a difference quotient?"},
        {"role": "user", "content": "I can write f(x)-f(x_0) = [f(x)-f(x_0)]/(x-x_0) * (x-x_0)."},
        {"role": "assistant", "content": "Good. As $x\\to x_0$, where does each of the two factors in this product tend?"},
        {"role": "user", "content": "The first factor -> f'(x_0) (differentiability), and the second (x-x_0) -> 0."},
        {"role": "assistant", "content": "Exactly. By the product rule for limits, where does the whole product tend, giving continuity?"},
        {"role": "user", "content": "-> f'(x_0)*0 = 0, so f(x) -> f(x_0) and f is continuous at x_0."},
        {"role": "assistant", "content": "Completely correct. The key is multiplying and dividing by $(x-x_0)$ to conjure the difference quotient; differentiability keeps that factor finite."},
    ]},
    {"problem_id": "C1", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Since f is differentiable, the derivative exists, so f is continuous — isn't that the definition?"},
        {"role": "assistant", "content": "It's a theorem to be proved, not a definition — a derivation is required. Can you rewrite $f(x)-f(x_0)$ as a product involving the difference quotient to get started?"},
        {"role": "user", "content": "Oh — write it as [f(x)-f(x_0)]/(x-x_0) * (x-x_0)."},
        {"role": "assistant", "content": "Good. Why is multiplying and dividing by $(x-x_0)$ allowed here — what premise does it need?"},
        {"role": "user", "content": "Because the limit is taken as x -> x_0 with x != x_0, so x-x_0 != 0 and we may divide. The product of the limits is f'(x_0)*0 = 0."},
        {"role": "assistant", "content": "Correct. Lesson: differentiable => continuous is a proposition requiring proof — via the difference-quotient product and limit laws, not by fiat."},
    ]},
    {"problem_id": "C1", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Write f(x)-f(x_0) as the difference quotient times (x-x_0); taking limits gives f'(x_0)*0=0, hence continuity."},
        {"role": "assistant", "content": "Correct. Conversely, what is the classic example of a continuous but non-differentiable function, showing the two are not equivalent?"},
        {"role": "user", "content": "f(x)=|x| is continuous at 0 but not differentiable there — the one-sided derivatives differ. So differentiability is strictly stronger than continuity."},
        {"role": "assistant", "content": "Correct — you have the strict hierarchy clear. Well mastered."},
    ]},

    # ===== C2: Rolle =====
    {"problem_id": "C2", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "I can't memorize the proof of Rolle's theorem — I don't see where the point c comes from."},
        {"role": "assistant", "content": "$c$ comes from an extremum. $f$ is continuous on the closed interval $[a,b]$ — which theorem guarantees it attains a maximum and a minimum?"},
        {"role": "user", "content": "The extreme value theorem: f attains a maximum M and a minimum m."},
        {"role": "assistant", "content": "Good. If $M=m$, what is $f$, and what about its derivative?"},
        {"role": "user", "content": "If M=m then f is constant, the derivative is 0 everywhere, and any c works."},
        {"role": "assistant", "content": "Exactly. If $M>m$, then since $f(a)=f(b)$, where must at least one of the maximum or minimum occur?"},
        {"role": "user", "content": "At least one occurs at an interior point c in (a,b), because with equal endpoint values they can't both be strict extremes at the endpoints."},
        {"role": "assistant", "content": "Right. At that interior extremum, which theorem gives $f'(c)=0$?"},
        {"role": "user", "content": "Fermat's theorem: at an interior extremum where the derivative exists, f'(c)=0."},
        {"role": "assistant", "content": "Completely correct. The soul of Rolle is: EVT locates the extremum, Fermat turns it into a zero derivative."},
    ]},
    {"problem_id": "C2", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Since f(a)=f(b), the graph must have a horizontal tangent somewhere, so f'(c)=0."},
        {"role": "assistant", "content": "That is intuition, not proof. Rigor requires saying where $c$ comes from. What does continuity of $f$ on $[a,b]$ guarantee it attains?"},
        {"role": "user", "content": "A maximum and a minimum (extreme value theorem)."},
        {"role": "assistant", "content": "Good. When the maximum or minimum falls at an interior point, which theorem converts it into $f'(c)=0$?"},
        {"role": "user", "content": "Fermat's theorem. But first handle the constant case M=m, where any point works."},
        {"role": "assistant", "content": "Correct. Lesson: Rolle's $c$ must be derived via \"EVT + Fermat\", not read off a picture."},
    ]},
    {"problem_id": "C2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Use the EVT to get M, m; if M=m it's constant; otherwise an extremum is interior and Fermat gives f'(c)=0."},
        {"role": "assistant", "content": "Complete. Your proof used continuity on $[a,b]$ and differentiability on $(a,b)$ — at which step does each hypothesis act?"},
        {"role": "user", "content": "Continuity feeds the EVT (existence of extrema); differentiability feeds Fermat (existence of f'(c), equal to 0)."},
        {"role": "assistant", "content": "Correct — you've matched each hypothesis precisely to its role. Spot-on understanding."},
    ]},

    # ===== C3: Lagrange MVT =====
    {"problem_id": "C3", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "I know the MVT's conclusion — slope equals the secant — but how does the proof come from Rolle?"},
        {"role": "assistant", "content": "The idea is to build an auxiliary function that subtracts the secant line, making the endpoint values equal so Rolle applies. Can you write that $g(x)$?"},
        {"role": "user", "content": "Set g(x) = f(x) - f(a) - [(f(b)-f(a))/(b-a)]*(x-a)?"},
        {"role": "assistant", "content": "Good. Verify: what are $g(a)$ and $g(b)$?"},
        {"role": "user", "content": "g(a)=0; g(b)=f(b)-f(a)-(f(b)-f(a))=0. Both endpoints are 0."},
        {"role": "assistant", "content": "Exactly — Rolle's hypotheses hold. Applying it gives $g'(c)=0$; what is $g'(x)$?"},
        {"role": "user", "content": "g'(x)=f'(x)-(f(b)-f(a))/(b-a), so f'(c)=(f(b)-f(a))/(b-a)."},
        {"role": "assistant", "content": "Completely correct. The MVT's core trick: subtract the secant to build an auxiliary function satisfying Rolle."},
    ]},
    {"problem_id": "C3", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "I apply Rolle directly to f, get f'(c)=0, and then say it equals the secant slope."},
        {"role": "assistant", "content": "Rolle needs $f(a)=f(b)$, which this problem doesn't provide. You must first manufacture a function with equal endpoints — how would you modify $f$?"},
        {"role": "user", "content": "Subtract the secant: g(x)=f(x)-[secant], making g(a)=g(b)=0."},
        {"role": "assistant", "content": "Exactly. Applying Rolle to $g$ gives $g'(c)=0$; what does expanding $g'$ yield?"},
        {"role": "user", "content": "f'(c)-(f(b)-f(a))/(b-a)=0, i.e. f'(c) = secant slope."},
        {"role": "assistant", "content": "Correct. Lesson: $f$ generally fails $f(a)=f(b)$; you must subtract the secant to build the auxiliary function before Rolle can act."},
    ]},
    {"problem_id": "C3", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Build g(x)=f(x)-f(a)-(f(b)-f(a))/(b-a)*(x-a); g(a)=g(b)=0, and Rolle gives g'(c)=0."},
        {"role": "assistant", "content": "Completely correct. Geometrically, what quantity does this auxiliary function represent — a way to remember the construction?"},
        {"role": "user", "content": "g(x) is the vertical gap at x between the graph of f and the secant line, so the endpoint gaps are naturally 0."},
        {"role": "assistant", "content": "Correct — the geometric meaning is the vertical deviation from the secant. You understand the construction's motivation thoroughly."},
    ]},

    # ===== C4: Cauchy MVT =====
    {"problem_id": "C4", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "The Cauchy MVT has two functions and I don't know how to set up the auxiliary function."},
        {"role": "assistant", "content": "Same idea as Lagrange: combine them so the endpoints agree. Try $h(x)=(f(b)-f(a))g(x)-(g(b)-g(a))f(x)$ — first compute $h(a)$ and $h(b)$?"},
        {"role": "user", "content": "h(a)=(f(b)-f(a))g(a)-(g(b)-g(a))f(a), and expanding h(b)... they seem to come out equal?"},
        {"role": "assistant", "content": "Expand both and you'll see the cross terms cancel. Once $h(a)=h(b)$ is confirmed, which theorem applies?"},
        {"role": "user", "content": "Expanding gives h(a)=f(b)g(a)-g(b)f(a)=h(b). Equal, so Rolle applies."},
        {"role": "assistant", "content": "Exactly. Rolle gives $h'(c)=0$; what relation does expanding $h'$ produce?"},
        {"role": "user", "content": "(f(b)-f(a))g'(c)-(g(b)-g(a))f'(c)=0, which rearranges to f'(c)/g'(c)=(f(b)-f(a))/(g(b)-g(a))."},
        {"role": "assistant", "content": "Completely correct. And remember to first justify $g(b)\\ne g(a)$, or the division is illegal — what guarantees it?"},
    ]},
    {"problem_id": "C4", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Apply Lagrange to f and g separately, get f'(c)=... and g'(c)=..., then divide."},
        {"role": "assistant", "content": "The two applications of Lagrange give intermediate points that need not coincide, so you can't just divide. To force a single shared $c$, what kind of auxiliary function should you build?"},
        {"role": "user", "content": "Right, the two c's differ. Build one combined function h so a single Rolle gives the same c."},
        {"role": "assistant", "content": "Exactly. Take $h=(f(b)-f(a))g-(g(b)-g(a))f$, check $h(a)=h(b)$, apply Rolle — what does $h'(c)=0$ give?"},
        {"role": "user", "content": "(f(b)-f(a))g'(c)=(g(b)-g(a))f'(c), same c, and dividing gives the conclusion."},
        {"role": "assistant", "content": "Correct. Lesson: a shared $c$ requires a single auxiliary function; two separate MVT applications produce two different points."},
    ]},
    {"problem_id": "C4", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Build h=(f(b)-f(a))g-(g(b)-g(a))f; h(a)=h(b), and Rolle gives h'(c)=0, i.e. the conclusion."},
        {"role": "assistant", "content": "Correct. How do you ensure you may divide by $g'(c)$ and by $g(b)-g(a)$ — that both are nonzero?"},
        {"role": "user", "content": "g' != 0 is a hypothesis; and g(b) != g(a) because otherwise Rolle would give a point with g'=0, contradicting that hypothesis."},
        {"role": "assistant", "content": "Correct — you justified both divisibility premises. Complete command of this one."},
    ]},

    # ===== C5: f'==0 => const =====
    {"problem_id": "C5", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Derivative identically 0 means constant — does that even need proof? I don't know how to write it."},
        {"role": "assistant", "content": "Proving constancy is equivalent to proving any two values agree. Take any $x_1<x_2$: which theorem connects $f(x_2)-f(x_1)$ to the derivative?"},
        {"role": "user", "content": "The mean value theorem: f(x_2)-f(x_1)=f'(c)(x_2-x_1)."},
        {"role": "assistant", "content": "Good. Since $f'\\equiv0$, what is $f'(c)$, and hence what is $f(x_2)-f(x_1)$?"},
        {"role": "user", "content": "f'(c)=0, so f(x_2)-f(x_1)=0, i.e. f(x_2)=f(x_1)."},
        {"role": "assistant", "content": "Exactly. Since $x_1,x_2$ were arbitrary, what does that show?"},
        {"role": "user", "content": "Any two values agree, so f is constant."},
        {"role": "assistant", "content": "Completely correct. The bridge from \"derivative identically zero\" to \"constant\" is precisely the mean value theorem."},
    ]},
    {"problem_id": "C5", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f'=0 means no change; integrating back gives f=C, so it's constant."},
        {"role": "assistant", "content": "\"Integrating back\" is essentially part of what's being proved — that's circular. This course uses the mean value theorem. For any $x_1<x_2$, what equation does it give?"},
        {"role": "user", "content": "f(x_2)-f(x_1)=f'(c)(x_2-x_1)=0, so the two values agree."},
        {"role": "assistant", "content": "Exactly. There's an often-missed premise here: on what kind of set must $f$ be defined for the conclusion to hold?"},
        {"role": "user", "content": "On an interval (connected). If the domain has two pieces, each piece can be a different constant."},
        {"role": "assistant", "content": "Correct. Lesson: use the MVT rather than \"integrating back\", and the connectedness premise \"interval\" is indispensable."},
    ]},
    {"problem_id": "C5", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Take any x_1<x_2; the MVT gives f(x_2)-f(x_1)=f'(c)(x_2-x_1)=0, so f is constant."},
        {"role": "assistant", "content": "Correct. A corollary follows: if $f'=g'$ on an interval, how do $f$ and $g$ differ?"},
        {"role": "user", "content": "Apply this result to f-g: (f-g)'=0, so f-g is constant, i.e. f=g+C."},
        {"role": "assistant", "content": "Correct — that is exactly the rigorous basis for antiderivatives differing by a constant. Well done."},
    ]},

    # ===== C6: f'>0 => strictly increasing =====
    {"problem_id": "C6", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Positive derivative means increasing — I get it intuitively but the proof stalls."},
        {"role": "assistant", "content": "Increasing means $x_1<x_2\\Rightarrow f(x_1)<f(x_2)$. Taking two such points, which theorem links the difference of values to the derivative?"},
        {"role": "user", "content": "The mean value theorem: f(x_2)-f(x_1)=f'(c)(x_2-x_1)."},
        {"role": "assistant", "content": "Good. What are the signs of the two factors on the right, and hence of the product?"},
        {"role": "user", "content": "f'(c)>0 and x_2-x_1>0, so the product is >0, giving f(x_2)>f(x_1)."},
        {"role": "assistant", "content": "Exactly — and since $x_1<x_2$ were arbitrary, $f$ is strictly increasing. If the hypothesis were relaxed to $f'\\ge0$, how does the conclusion change?"},
        {"role": "user", "content": "You only get f(x_2)>=f(x_1) — increasing but not strictly."},
        {"role": "assistant", "content": "Completely correct. You even have the strict/non-strict boundary down."},
    ]},
    {"problem_id": "C6", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f'(x)>0 means it goes up at every point, so it's increasing overall — surely that's enough?"},
        {"role": "assistant", "content": "\"Positive slope at each point\" is local information; connecting it rigorously to a comparison of two arbitrary points needs a tool. For $x_1<x_2$, what does the MVT give?"},
        {"role": "user", "content": "f(x_2)-f(x_1)=f'(c)(x_2-x_1)>0, so f(x_2)>f(x_1)."},
        {"role": "assistant", "content": "Exactly — that converts local positivity of slope into a global comparison. Why is the MVT indispensable at this step?"},
        {"role": "user", "content": "Because it's the only tool that writes a two-point difference exactly as some derivative times the gap."},
        {"role": "assistant", "content": "Correct. Lesson: the sign of the derivative passes to global monotonicity only through the mean value theorem."},
    ]},
    {"problem_id": "C6", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "For any x_1<x_2, MVT gives f(x_2)-f(x_1)=f'(c)(x_2-x_1)>0, so strictly increasing."},
        {"role": "assistant", "content": "Correct. Does the converse hold — must a strictly increasing differentiable function have $f'>0$, and can you give an example?"},
        {"role": "user", "content": "No: f(x)=x^3 is strictly increasing but f'(0)=0, so you can only conclude f'>=0."},
        {"role": "assistant", "content": "Correct — you pinpointed that monotonicity and derivative sign are not equivalent. Well done."},
    ]},

    # ===== C7: Fermat =====
    {"problem_id": "C7", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Fermat's theorem says the derivative vanishes at an extremum, and I don't know how to prove it."},
        {"role": "assistant", "content": "Start from the definition of a local maximum: nearby, $f(c+h)\\le f(c)$. Looking first at the right derivative ($h\\to0^+$), what is the sign of the difference quotient $\\frac{f(c+h)-f(c)}{h}$?"},
        {"role": "user", "content": "Numerator <=0, denominator h>0, so the quotient <=0 and the right derivative f'(c)<=0."},
        {"role": "assistant", "content": "Good. Now the left derivative ($h\\to0^-$): the denominator's sign flips — what is the quotient's sign?"},
        {"role": "user", "content": "Numerator <=0, denominator h<0, quotient >=0, so the left derivative f'(c)>=0."},
        {"role": "assistant", "content": "Exactly. Differentiability makes the one-sided derivatives equal; $f'(c)$ is both $\\le0$ and $\\ge0$ — conclusion?"},
        {"role": "user", "content": "It can only be f'(c)=0."},
        {"role": "assistant", "content": "Completely correct. Fermat squeezes $f'(c)=0$ from the two one-sided quotients; differentiability is the glue joining them."},
    ]},
    {"problem_id": "C7", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "The tangent is horizontal at a maximum, so f'(c)=0 — isn't that obvious?"},
        {"role": "assistant", "content": "The picture must become inequalities. Using $f(c+h)\\le f(c)$, what sign does the right derivative ($h\\to0^+$) get?"},
        {"role": "user", "content": "The quotient <=0, so the right derivative <=0."},
        {"role": "assistant", "content": "Good. Now the left derivative ($h\\to0^-$): what do the two sides force together?"},
        {"role": "user", "content": "Left derivative >=0; since they're equal, it must be 0."},
        {"role": "assistant", "content": "Correct. Also: why insist on an interior point — does the conclusion fail for an endpoint extremum?"},
        {"role": "user", "content": "An endpoint has only one side, so you only get the sign of a one-sided derivative, not necessarily 0. Hence interior."},
        {"role": "assistant", "content": "Correct. Lesson: Fermat needs \"interior point + differentiable\", and runs on one-sided quotients, not pictures."},
    ]},
    {"problem_id": "C7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "From f(c+h)<=f(c): right derivative <=0, left derivative >=0; differentiability equates them so f'(c)=0."},
        {"role": "assistant", "content": "Completely correct. Is the converse true — does $f'(c)=0$ make $c$ an extremum, and what is a counterexample?"},
        {"role": "user", "content": "No: f(x)=x^3 has f'(0)=0 but 0 is not an extremum. So f'(c)=0 is only necessary, not sufficient."},
        {"role": "assistant", "content": "Correct — Fermat gives a necessary condition only. Well mastered."},
    ]},

    # ===== C8: |f'|<=M => Lipschitz =====
    {"problem_id": "C8", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Bounded derivative should give Lipschitz, but I don't see how to connect |f(x)-f(y)| with M."},
        {"role": "assistant", "content": "$|f(x)-f(y)|$ is a two-point difference of values — which theorem writes it exactly as a derivative times the gap?"},
        {"role": "user", "content": "The mean value theorem: f(x)-f(y)=f'(c)(x-y)."},
        {"role": "assistant", "content": "Good. Taking absolute values and using the hypothesis $|f'(c)|\\le M$, what inequality follows?"},
        {"role": "user", "content": "|f(x)-f(y)|=|f'(c)||x-y|<=M|x-y|."},
        {"role": "assistant", "content": "Exactly. Does that also hold when $x=y$ — does it need a separate remark?"},
        {"role": "user", "content": "For x=y both sides are 0, so it holds. Hence Lipschitz for all x, y."},
        {"role": "assistant", "content": "Completely correct. A bounded derivative hands you the Lipschitz constant $M$ straight through the MVT."},
    ]},
    {"problem_id": "C8", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Since |f'|<=M, integrating gives |f(x)-f(y)|=|∫f'|<=M|x-y|."},
        {"role": "assistant", "content": "Integration can work, but the problem only assumes differentiability — $f'$ need not be integrable or continuous. Is there a tool using differentiability alone that yields the same conclusion?"},
        {"role": "user", "content": "The mean value theorem needs only differentiability: f(x)-f(y)=f'(c)(x-y)."},
        {"role": "assistant", "content": "Exactly, and it's more basic. After taking absolute values, how does Lipschitz follow?"},
        {"role": "user", "content": "|f(x)-f(y)|=|f'(c)||x-y|<=M|x-y|."},
        {"role": "assistant", "content": "Correct. Lesson: with only differentiability assumed, the MVT route is safer and needs fewer hypotheses than integration."},
    ]},
    {"problem_id": "C8", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "By the MVT, f(x)-f(y)=f'(c)(x-y); absolute values give |f(x)-f(y)|<=M|x-y|."},
        {"role": "assistant", "content": "Correct. What implication holds between Lipschitz continuity and uniform continuity?"},
        {"role": "user", "content": "Lipschitz => uniformly continuous (take delta=eps/M), but not conversely — e.g. sqrt(x) is uniformly continuous but not Lipschitz."},
        {"role": "assistant", "content": "Correct — you've sorted the whole hierarchy of continuity strengths. Excellent."},
    ]},

    # ===== C9: |sin x - sin y| <= |x-y| =====
    {"problem_id": "C9", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "This one has sin in it and I don't know how to estimate |sin x - sin y|."},
        {"role": "assistant", "content": "View it as a two-point difference of some function, so the MVT applies. Take $f(t)=\\sin t$: what is $f'(t)$, and what bound does it obey?"},
        {"role": "user", "content": "f'(t)=cos t, and |cos t|<=1."},
        {"role": "assistant", "content": "Good. Applying the MVT for $x\\ne y$, what does $\\sin x-\\sin y$ equal?"},
        {"role": "user", "content": "= cos c * (x-y) for some c between x and y."},
        {"role": "assistant", "content": "Exactly. Taking absolute values and using $|\\cos c|\\le1$, what do you get?"},
        {"role": "user", "content": "|sin x-sin y|=|cos c||x-y|<=|x-y|."},
        {"role": "assistant", "content": "Completely correct. This is a special case of C8: $\\sin$ has derivative bounded by $1$, so its Lipschitz constant is $1$."},
    ]},
    {"problem_id": "C9", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Using sum-to-product, sin x - sin y = 2cos((x+y)/2)sin((x-y)/2), so |sin x-sin y| <= 2|sin((x-y)/2)| <= 2*(x-y)/2 = |x-y| — but I'm not sure I may use |sin t|<=|t|."},
        {"role": "assistant", "content": "Your route works but leans on the lemma $|\\sin t|\\le|t|$, which itself needs proof. Is there a more direct method using just one theorem?"},
        {"role": "user", "content": "Apply the MVT to f(t)=sin t, with f'=cos and |cos|<=1."},
        {"role": "assistant", "content": "Exactly: $\\sin x-\\sin y=\\cos c(x-y)$, and absolute values finish it. Do you see the trade-off between the two methods?"},
        {"role": "user", "content": "Yes — the MVT gets there in one step without separately proving |sin t|<=|t|."},
        {"role": "assistant", "content": "Correct. Lesson: the MVT converts \"bounded derivative\" into Lipschitz directly, sparing the auxiliary lemma."},
    ]},
    {"problem_id": "C9", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "MVT on sin: sin x - sin y = cos c (x-y), |cos c|<=1, so |sin x-sin y|<=|x-y|."},
        {"role": "assistant", "content": "Correct. Is the Lipschitz constant $1$ optimal (impossible to lower), and how would you show it?"},
        {"role": "user", "content": "It's optimal: as x,y -> 0, |sin x-sin y|/|x-y| -> |cos 0| = 1, approaching 1."},
        {"role": "assistant", "content": "Correct — optimality of the constant $1$ is attained through the derivative's value at $0$. Deep analysis."},
    ]},

    # ===== C10: x/(1+x) < ln(1+x) < x =====
    {"problem_id": "C10", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "This two-sided inequality involves ln, and I don't see how to prove both bounds at once."},
        {"role": "assistant", "content": "Applying the MVT to $f(t)=\\ln(1+t)$ on $[0,x]$ is very effective here. What is $f'(t)$?"},
        {"role": "user", "content": "f'(t)=1/(1+t)."},
        {"role": "assistant", "content": "Good. The MVT gives $\\ln(1+x)-\\ln1=f'(\\xi)\\cdot x$, i.e. $\\ln(1+x)=\\frac{x}{1+\\xi}$ — in what range does $\\xi$ lie?"},
        {"role": "user", "content": "xi in (0,x)."},
        {"role": "assistant", "content": "Exactly. From $0<\\xi<x$, deduce the range of $\\frac{1}{1+\\xi}$, then multiply by $x>0$ — what two-sided inequality results?"},
        {"role": "user", "content": "1<1+xi<1+x, so 1/(1+x)<1/(1+xi)<1; multiplying by x gives x/(1+x)<ln(1+x)<x."},
        {"role": "assistant", "content": "Completely correct. One MVT identity plus the range of $\\xi$ squeezes out both bounds simultaneously."},
    ]},
    {"problem_id": "C10", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "For ln(1+x)<x I set g(x)=x-ln(1+x), g'(x)=1-1/(1+x)>0, g(0)=0 so g>0. But I can't do the left half."},
        {"role": "assistant", "content": "Your monotonicity argument for the right half is fine. The left half can use the same trick — or the MVT can nail both at once. Applying the MVT to $\\ln(1+t)$ on $[0,x]$, what identity do you get?"},
        {"role": "user", "content": "ln(1+x)=x/(1+xi), with xi in (0,x)."},
        {"role": "assistant", "content": "Exactly. From $\\xi<x$ we get $\\frac{1}{1+\\xi}>\\frac{1}{1+x}$; multiplying by $x$ — which inequality drops out?"},
        {"role": "user", "content": "ln(1+x)=x/(1+xi)>x/(1+x): the left bound is proved."},
        {"role": "assistant", "content": "Correct. Lesson: a single MVT identity plus the range of $\\xi$ gives both bounds at once — cheaper than building two auxiliary functions."},
    ]},
    {"problem_id": "C10", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "MVT on ln(1+t) over [0,x]: ln(1+x)=x/(1+xi), and 0<xi<x gives x/(1+x)<ln(1+x)<x."},
        {"role": "assistant", "content": "Very slick. To establish an analogous inequality for $x\\in(-1,0)$, what must the argument watch out for?"},
        {"role": "user", "content": "For x<0, multiplying by a negative flips the inequalities, and the interval becomes [x,0]; the ordering of x/(1+x) and x swaps, so care is needed."},
        {"role": "assistant", "content": "Correct — you spotted the sign-flip trap on the negative interval. Very solid understanding."},
    ]},
]
