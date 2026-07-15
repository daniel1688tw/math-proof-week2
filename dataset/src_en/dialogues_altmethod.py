# -*- coding: utf-8 -*-
"""Alternative-method following + on-track affirm-only (v8 weakness fix).
English parallel of src/dialogues_altmethod.py; authored by Claude.

Two sample kinds, targeting the S4 metric and known weaknesses #4/#5:
  altmethod: the student proposes a proof route that differs from the reference
             but is logically valid; the tutor MUST follow the student's route
             to the end and never pull them back to the reference (missing
             hypotheses may be pointed out within the student's route).
  ontrack:   when the student is on the right track, the tutor only affirms
             briefly and asks an open question (how they plan to continue),
             never prescribing any concrete operation.
"""

DIALOGUES = [
    # ===== A1 (reference: binomial + squeeze) — student takes the log route =====
    {"problem_id": "A1", "persona": "bright", "kind": "altmethod", "turns": [
        {"role": "user", "content": "I'd rather not use the binomial theorem. I want to take logs: n^(1/n) = e^{(ln n)/n}, so it suffices to show (ln n)/n → 0. Is that okay?"},
        {"role": "assistant", "content": "Perfectly valid — it's a clean route, so let's follow it. To control $\\dfrac{\\ln n}{n}$, what kind of upper bound on $\\ln n$ do you plan to use?"},
        {"role": "user", "content": "I remember ln x ≤ x−1, but using it directly only gives (ln n)/n ≤ (n−1)/n → 1, which doesn't push it to 0."},
        {"role": "assistant", "content": "Sharp observation — that bound is too loose. If you apply the same inequality not to $n$ itself but to some power of $n$, can you get a tighter bound?"},
        {"role": "user", "content": "Oh! Apply it to √n: ln n = 2 ln √n ≤ 2(√n − 1) ≤ 2√n, so (ln n)/n ≤ 2/√n."},
        {"role": "assistant", "content": "Excellent: $0\\le\\dfrac{\\ln n}{n}\\le\\dfrac{2}{\\sqrt n}\\to0$, so the exponent tends to $0$ by squeezing. To go from $\\dfrac{\\ln n}{n}\\to0$ back to $n^{1/n}\\to1$, which property do you need to cite?"},
        {"role": "user", "content": "Continuity of the exponential function: e^{(ln n)/n} → e^0 = 1."},
        {"role": "assistant", "content": "Complete and correct. Your log route is just as rigorous as the binomial one, and \"apply ln x ≤ x−1 to √n for a tighter bound\" is a trick worth remembering."},
    ]},

    # ===== A2 (reference: δ=min{1, ε/5}) — student picks different constants =====
    {"problem_id": "A2", "persona": "bright", "kind": "altmethod", "turns": [
        {"role": "user", "content": "After factoring |x−2||x+2|, I want to first restrict |x−2|<2 instead of <1, so 0<x<4 and |x+2|<6, then take δ=min{2, ε/6}. Is that allowed?"},
        {"role": "assistant", "content": "Absolutely — the constant in the preliminary bound is not unique, and your choice is perfectly legal. Verify it once with your $\\delta$: when $0<|x-2|<\\delta$, what bounds $|x^2-4|$?"},
        {"role": "user", "content": "|x−2|<δ≤2 guarantees |x+2|<6, so |x²−4| < 6|x−2| < 6·(ε/6) = ε."},
        {"role": "assistant", "content": "Correct — the argument closes. Now, what would go wrong if $\\delta$ were not a min but simply $\\delta=\\varepsilon/6$?"},
        {"role": "user", "content": "For large ε, ε/6 could exceed 2, and then the bound |x+2|<6 is no longer guaranteed, so the min locks in both conditions."},
        {"role": "assistant", "content": "Exactly right. You carried the proof through with your own constants — in ε-δ proofs the preliminary bound can be 1, 2, or anything else, as long as the min locks it in, the logic is complete."},
    ]},

    # ===== B1 (reference: sup construction) — student uses bisection / nested intervals =====
    {"problem_id": "B1", "persona": "bright", "kind": "altmethod", "turns": [
        {"role": "user", "content": "I don't want to use sup. I'd use bisection: assume f(a)<0<f(b), repeatedly take the midpoint and keep the half where the sign changes, getting nested intervals that squeeze out a root. Does that work?"},
        {"role": "assistant", "content": "It works — bisection is a fully rigorous alternative, so let's follow it. First make the inductive construction precise: after taking the midpoint $m$, how do you choose the next interval based on the sign of $f(m)$?"},
        {"role": "user", "content": "If f(m)=0 we're done; if f(m)>0 take [a, m], if f(m)<0 take [m, b]. Every interval keeps f<0 at the left end and f>0 at the right end."},
        {"role": "assistant", "content": "Good — the invariant is preserved. The lengths of $[a_n,b_n]$ are $\\dfrac{b-a}{2^n}\\to0$; to argue both endpoints converge to one common point $c$, what do you plan to invoke?"},
        {"role": "user", "content": "a_n is increasing and bounded above, b_n decreasing and bounded below, so both converge by monotone convergence; the lengths tend to 0, so the limits coincide — call it c."},
        {"role": "assistant", "content": "Correct. Final step: from $f(a_n)<0$, $f(b_n)>0$ and $a_n,b_n\\to c$, how do you conclude $f(c)=0$?"},
        {"role": "user", "content": "By continuity, f(c) = lim f(a_n) ≤ 0 and f(c) = lim f(b_n) ≥ 0, so f(c)=0; and since f(a),f(b)≠0, c lies in the open interval."},
        {"role": "assistant", "content": "Complete and correct. Your nested-interval proof is as rigorous as the sup construction, and the \"preserve the sign-change invariant\" idea will reappear in many constructive arguments."},
    ]},

    # ===== D1 (reference: contradiction + local positivity) — student uses the antiderivative =====
    {"problem_id": "D1", "persona": "bright", "kind": "altmethod", "turns": [
        {"role": "user", "content": "I'd like to avoid contradiction: set F(x)=∫_a^x f. Since f≥0, F is nondecreasing, and F(a)=0, F(b)=0, so F is identically 0; differentiating F gives f≡0. Is that right?"},
        {"role": "assistant", "content": "The antiderivative route is a good one — let's push it through. First link: from \"$F$ nondecreasing and $F(a)=F(b)=0$\" to $F\\equiv0$, what is the argument in between?"},
        {"role": "user", "content": "For any x∈[a,b], monotonicity gives 0=F(a)≤F(x)≤F(b)=0, so F(x)=0."},
        {"role": "assistant", "content": "Correct. Second link: differentiating $F\\equiv0$ to get $f\\equiv0$ — which theorem does that step use, and what assumption on $f$ does it need?"},
        {"role": "user", "content": "The fundamental theorem of calculus: since f is continuous, F is differentiable with F'=f. F is identically 0 so F'≡0, i.e. f≡0. That's where continuity gets used."},
        {"role": "assistant", "content": "Exactly right — both links close. Your route spends continuity on the fundamental theorem, while the reference contradiction route spends it on local positivity — same hypothesis, two rigorous uses. Your version can stand as a formal proof as-is."},
    ]},

    # ===== on-track: affirm + open question only, never prescribe operations =====
    {"problem_id": "B1", "persona": "bright", "kind": "ontrack", "turns": [
        {"role": "user", "content": "I plan to set S = {x∈[a,b] : f(x)<0} (assuming f(a)<0<f(b)) and take c = sup S as the candidate root."},
        {"role": "assistant", "content": "Right direction — that is exactly the key construction. Having taken $c=\\sup S$, how do you plan to continue?"},
        {"role": "user", "content": "I want to rule out both f(c)>0 and f(c)<0, deriving a contradiction with the definition of sup in each case."},
        {"role": "assistant", "content": "A complete plan. Take one of them: if $f(c)>0$, which property will you start from to find the contradiction?"},
        {"role": "user", "content": "Continuity: if f(c)>0 then f>0 on a small interval around c, so the points just left of c are not in S, making c−δ an upper bound of S — contradicting that c is the least upper bound."},
        {"role": "assistant", "content": "Correct. And how do you plan to handle the case $f(c)<0$?"},
        {"role": "user", "content": "Same idea: continuity gives f<0 slightly to the right of c, so S contains points bigger than c, contradicting that c is an upper bound. Hence f(c)=0, and c≠a,b."},
        {"role": "assistant", "content": "Complete and correct — you walked the whole proof yourself. The sup construction plus ruling out both signs: you have fully mastered it."},
    ]},
    {"problem_id": "C2", "persona": "bright", "kind": "ontrack", "turns": [
        {"role": "user", "content": "For Rolle's theorem I'd argue: by the extreme value theorem f attains a maximum and a minimum on [a,b], then split into cases by where the extrema are attained."},
        {"role": "assistant", "content": "Exactly the right direction. How do you plan to split the cases?"},
        {"role": "user", "content": "If both the max and the min are attained at endpoints, then since f(a)=f(b) the max equals the min, so f is constant and any c gives f'(c)=0; otherwise at least one extremum is attained in the interior."},
        {"role": "assistant", "content": "Very clean analysis. For the interior-extremum branch, how will you finish?"},
        {"role": "user", "content": "By Fermat's theorem: at an interior extremum of a differentiable function the derivative vanishes, and that point is the c we need."},
        {"role": "assistant", "content": "Complete and correct. The extreme value theorem provides existence, Fermat's theorem gives the zero derivative — each tool doing its own job. This can be written up as a formal proof directly."},
    ]},
    {"problem_id": "E2", "persona": "bright", "kind": "ontrack", "turns": [
        {"role": "user", "content": "Let a_n → L. I want to use the triangle inequality to split |a_n − a_m| into two legs passing through L."},
        {"role": "assistant", "content": "That is precisely the core idea. After splitting, how do you plan to make both legs small?"},
        {"role": "user", "content": "Given ε, choose N so that n≥N implies |a_n − L| < ε/2; then for n,m≥N, |a_n−a_m| ≤ |a_n−L| + |L−a_m| < ε/2 + ε/2 = ε."},
        {"role": "assistant", "content": "Correct. Why ε/2 rather than ε — can you spell out the purpose of that choice?"},
        {"role": "user", "content": "Because two legs get added at the end, so each must be given half for the sum to come out strictly less than ε."},
        {"role": "assistant", "content": "Exactly right — that is the complete proof. \"Route through the limit point and give each leg half\" is the standard template for Cauchy arguments, and you walked it through on your own."},
    ]},
]
