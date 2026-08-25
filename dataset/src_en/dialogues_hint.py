# -*- coding: utf-8 -*-
"""Graded-hint dialogues (10, 2 per topic A-E). English translation of src/dialogues_hint.py.

Demonstrates the rule: only after the student fails the SAME step twice in a row may the
tutor name the key theorem/technique (without explaining how to apply it and without
formulas), then ask one question so the student continues on their own.
Before two consecutive failures, only re-guiding questions are allowed — no early names."""

DIALOGUES = [
    # ===== A4: squeeze theorem =====
    {"problem_id": "A4", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "I have absolutely no idea how to handle an oscillating thing like sin n."},
        {"role": "assistant", "content": "Think first: $\\sin n$ oscillates, but does its absolute value have a fixed upper bound?"},
        {"role": "user", "content": "I don't know — I never learned how to handle limits of oscillating functions."},
        {"role": "assistant", "content": "No worry, another angle: what number does $|\\sin n|$ never exceed, for any $n$?"},
        {"role": "user", "content": "I still can't think of it, sorry."},
        {"role": "assistant", "content": "The key to this step is the squeeze theorem. Can you find an upper bound for $\\left|\\frac{\\sin n}{n}\\right|$ yourself?"},
        {"role": "user", "content": "Oh! |sin n / n| <= 1/n, because |sin n| <= 1."},
        {"role": "assistant", "content": "Right — $0\\le\\left|\\frac{\\sin n}{n}\\right|\\le\\frac1n\\to0$. Do you know how to finish now?"},
        {"role": "user", "content": "Both ends tend to 0, so the squeeze theorem gives limit 0."},
        {"role": "assistant", "content": "Completely correct. Once you had the theorem's name you completed the whole argument yourself — that's the point."},
    ]},

    # ===== A1: binomial theorem =====
    {"problem_id": "A1", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "The n-th root of n — I have no clue at all."},
        {"role": "assistant", "content": "First set $a_n=\\sqrt[n]{n}-1\\ge0$. What do you get by raising both sides to the $n$-th power?"},
        {"role": "user", "content": "I don't know how to expand (1+a_n)^n."},
        {"role": "assistant", "content": "That's fine — another way to ask: is there a standard way to write $(1+a_n)^n$ as a sum of terms?"},
        {"role": "user", "content": "Still no idea, sorry."},
        {"role": "assistant", "content": "Here you need the binomial theorem. After expanding, if you keep only the term with $a_n^2$ as a lower bound, what inequality can you write?"},
        {"role": "user", "content": "Oh: n >= C(n,2) a_n^2 = n(n-1)/2 * a_n^2."},
        {"role": "assistant", "content": "Good. After solving for an upper bound on $a_n$ and letting $n\\to\\infty$, which theorem finishes?"},
        {"role": "user", "content": "a_n^2 <= 2/(n-1); the squeeze theorem gives a_n -> 0, so the limit is 1."},
        {"role": "assistant", "content": "Completely correct — once the binomial theorem was in place you finished the whole estimate yourself."},
    ]},

    # ===== B2: Bolzano-Weierstrass =====
    {"problem_id": "B2", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "I have no idea where to cut into the proof of boundedness."},
        {"role": "assistant", "content": "By contradiction: if $f$ has no upper bound, you can pick points $x_n$ with $f(x_n)>n$. Are those $x_n$ still inside $[a,b]$?"},
        {"role": "user", "content": "Yes, but I don't know what to do next."},
        {"role": "assistant", "content": "$\\{x_n\\}$ is a bounded sequence — is there any way to pull a convergent subsequence out of it?"},
        {"role": "user", "content": "I can't think of what tool to use."},
        {"role": "assistant", "content": "Here you need the Bolzano-Weierstrass theorem. It hands you a convergent subsequence of $\\{x_n\\}$ — how does that help toward the contradiction?"},
        {"role": "user", "content": "The subsequence x_{n_k} -> x* in [a,b]; by continuity f(x_{n_k}) -> f(x*) is finite, contradicting f(x_{n_k}) > n_k -> infinity!"},
        {"role": "assistant", "content": "Completely correct — you wired up the contradiction yourself; that's the whole proof skeleton."},
    ]},

    # ===== B7: intermediate value theorem =====
    {"problem_id": "B7", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "Odd-degree polynomials have real roots — I don't know how to prove it."},
        {"role": "assistant", "content": "First look at what the polynomial's values do as $x\\to+\\infty$ and $x\\to-\\infty$."},
        {"role": "user", "content": "I'm not sure — I'm not good at analyzing limits of polynomials."},
        {"role": "assistant", "content": "Another angle: the leading term has odd degree — what sign does the function take for very large and very small (negative) $x$?"},
        {"role": "user", "content": "Still not sure — could I get another hint?"},
        {"role": "assistant", "content": "Once you have one positive and one negative value, this step needs the intermediate value theorem. Can you say how it locates the root for you?"},
        {"role": "user", "content": "p is continuous on [a,b] with p(a)<0<p(b), so the IVT gives some c with p(c)=0!"},
        {"role": "assistant", "content": "Completely correct — the only missing premise was the sign change at the endpoints, and you just supplied it yourself."},
    ]},

    # ===== C2: Fermat's theorem =====
    {"problem_id": "C2", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "I don't know where to begin the proof of Rolle's theorem."},
        {"role": "assistant", "content": "$f$ is continuous on $[a,b]$ — what values does that guarantee it attains?"},
        {"role": "user", "content": "I don't know what continuity guarantees."},
        {"role": "assistant", "content": "Another way to ask: must a continuous function on a closed interval have a maximum and a minimum?"},
        {"role": "user", "content": "I guess so, but I don't know how to use that."},
        {"role": "assistant", "content": "When the maximum or minimum falls at an interior point, this step needs Fermat's theorem. What does it tell you the derivative is at that point?"},
        {"role": "user", "content": "Fermat's theorem says the derivative at an interior extremum is 0, so f'(c)=0!"},
        {"role": "assistant", "content": "Correct. Do you remember to first exclude the special case that $f$ is constant?"},
        {"role": "user", "content": "Yes — then f' is 0 everywhere, so any c works."},
        {"role": "assistant", "content": "Completely correct — both cases covered."},
    ]},

    # ===== C3: Rolle's theorem =====
    {"problem_id": "C3", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "How the MVT follows from Rolle's theorem — I have no clue."},
        {"role": "assistant", "content": "Rolle needs equal function values at the endpoints, but here $f(a)$ needn't equal $f(b)$. How would you handle that?"},
        {"role": "user", "content": "I don't know how to make the endpoints equal."},
        {"role": "assistant", "content": "Another thought: can you build a new function — $f$ minus some straight line — so the endpoint difference vanishes?"},
        {"role": "user", "content": "I still can't figure out which line to subtract."},
        {"role": "assistant", "content": "Here you need Rolle's theorem, and the line to subtract is exactly the secant joining $(a,f(a))$ and $(b,f(b))$. Can you write this auxiliary function?"},
        {"role": "user", "content": "g(x) = f(x) - f(a) - (f(b)-f(a))/(b-a) * (x-a), so g(a)=g(b)=0!"},
        {"role": "assistant", "content": "Good — after applying Rolle to $g$, what does $g'(c)=0$ yield?"},
        {"role": "user", "content": "g'(x) = f'(x) - (f(b)-f(a))/(b-a), so f'(c) = (f(b)-f(a))/(b-a)."},
        {"role": "assistant", "content": "Completely correct — you connected the auxiliary function and Rolle's theorem yourself."},
    ]},

    # ===== D3: intermediate value theorem (integral MVT) =====
    {"problem_id": "D3", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "How is the integral mean value theorem proved? I have no idea where c comes from."},
        {"role": "assistant", "content": "$f$ is continuous on $[a,b]$, attaining minimum $m$ and maximum $M$. In what range must $\\int_a^b f$ lie?"},
        {"role": "user", "content": "I'm not sure how to relate the integral to m and M."},
        {"role": "assistant", "content": "Another angle: if $m\\le f(x)\\le M$ holds for all $x$, what do you get by integrating this inequality?"},
        {"role": "user", "content": "I still can't do it, sorry."},
        {"role": "assistant", "content": "Here you need the intermediate value theorem. The integrated inequality traps the average value between $m$ and $M$ — can you write that inequality yourself?"},
        {"role": "user", "content": "The average mu = (1/(b-a)) ∫_a^b f lies in [m,M], and the IVT gives c with f(c)=mu!"},
        {"role": "assistant", "content": "Completely correct — you chained \"trap the average\" and \"attain it by the IVT\" yourself."},
    ]},

    # ===== D7: Heine-Cantor (uniform continuity) =====
    {"problem_id": "D7", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "In proving continuous functions are integrable, I don't know how to control the gap between upper and lower sums."},
        {"role": "assistant", "content": "The pointwise $\\delta$ varies from point to point. To pin down ALL subintervals at once, what stronger kind of continuity do you need?"},
        {"role": "user", "content": "I don't know of any stronger version of continuity."},
        {"role": "assistant", "content": "Another way to ask: is there a kind of continuity guaranteeing the SAME $\\delta$ works at every point of the interval?"},
        {"role": "user", "content": "I still can't recall — could you just hint it?"},
        {"role": "assistant", "content": "Here you need the Heine-Cantor theorem (uniform continuity). With the universal $\\delta$, can you say what bounds $U-L$?"},
        {"role": "user", "content": "Take a partition with mesh<delta: each M_i-m_i <= eps/(b-a), so U-L <= eps!"},
        {"role": "assistant", "content": "Completely correct — the universal $\\delta$ was exactly the key you needed."},
    ]},

    # ===== E9: monotone convergence theorem =====
    {"problem_id": "E9", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "(1+1/n)^n converges — I have absolutely no idea how to start."},
        {"role": "assistant", "content": "This is a $1^\\infty$ indeterminate form, so limits can't be substituted directly. How would you prove the sequence itself converges?"},
        {"role": "user", "content": "I don't know how to prove a sequence converges."},
        {"role": "assistant", "content": "Another way to ask: if a sequence can be shown increasing AND bounded above, what conclusion follows?"},
        {"role": "user", "content": "I'm still not sure how to prove increasing and bounded."},
        {"role": "assistant", "content": "Here you need the monotone convergence theorem. After expanding $(1+1/n)^n$, can you see why it increases and why it is bounded above?"},
        {"role": "user", "content": "After the binomial expansion every term grows with n, and 1/k! <= 1/2^(k-1) gives the upper bound 3."},
        {"role": "assistant", "content": "Completely correct — you proved both the increase and the bound yourself."},
    ]},

    # ===== C4: no formal theorem name, pure construction idea =====
    {"problem_id": "C4", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "The Cauchy MVT involves two functions f and g — I have no idea how to start."},
        {"role": "assistant", "content": "Applying the MVT to $f$ and $g$ separately gives two different $c$'s. How would you make them share a single $c$?"},
        {"role": "user", "content": "I don't know how to make them share one point."},
        {"role": "assistant", "content": "Another angle: can you combine $f$ and $g$ into one single function needing only one application of Rolle's theorem?"},
        {"role": "user", "content": "I still can't figure out how to combine them."},
        {"role": "assistant", "content": "Try a weighted difference of $f$ and $g$, arranged so the combination has equal values at $a$ and $b$. How would you write it?"},
        {"role": "user", "content": "h(x) = (f(b)-f(a))g(x) - (g(b)-g(a))f(x) — the endpoint values should come out equal."},
        {"role": "assistant", "content": "Good. After verifying $h(a)=h(b)$ and applying Rolle to $h$, what does $h'(c)=0$ give you?"},
        {"role": "user", "content": "Expanding: (f(b)-f(a))g'(c) = (g(b)-g(a))f'(c) — divide and that's the identity to prove!"},
        {"role": "assistant", "content": "Completely correct — you found the combination function yourself."},
    ]},

    # ===== D1: no formal theorem name, pure contradiction idea =====
    {"problem_id": "D1", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "Zero integral should force the function to be identically zero, but I don't know how to go from the integral back to pointwise properties."},
        {"role": "assistant", "content": "Try contradiction: if $f(x_0)>0$ at some point, can you use continuity to turn that single positive value into a whole positive segment?"},
        {"role": "user", "content": "I don't know how continuity is used here."},
        {"role": "assistant", "content": "Another angle: can a continuous function's values near a point suddenly jump far away from the value at that point?"},
        {"role": "user", "content": "I still can't see how to do it concretely."},
        {"role": "assistant", "content": "Try the definition of continuity: take $\\varepsilon=f(x_0)/2$ and see what range confines the function values on a whole segment near $x_0$."},
        {"role": "user", "content": "On a nearby segment f(x) > f(x_0)/2 > 0, and since f >= 0, the integral over that segment is positive!"},
        {"role": "assistant", "content": "Good — how does that clash with $\\int_a^b f=0$?"},
        {"role": "user", "content": "∫_a^b f is at least that segment's positive integral, contradicting zero. So no such x_0 exists and f == 0."},
        {"role": "assistant", "content": "Completely correct — you converted continuity into the key idea of \"a whole positive segment\" yourself."},
    ]},

    # ===== E2: triangle inequality =====
    {"problem_id": "E2", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "Convergent sequences are Cauchy — I can't figure out how to connect the two definitions."},
        {"role": "assistant", "content": "Given $a_n\\to L$, the goal is to estimate $|a_n-a_m|$. Can you first relate it to $L$?"},
        {"role": "user", "content": "I don't know how to connect a_n and a_m to L at the same time."},
        {"role": "assistant", "content": "Another thought: can you add and subtract $L$ inside $a_n-a_m$, producing two quantities you already know become small?"},
        {"role": "user", "content": "I still can't see how to arrange it."},
        {"role": "assistant", "content": "Here you need the triangle inequality. Can you write $|a_n-a_m|$ pinned by $|a_n-L|$ and $|a_m-L|$?"},
        {"role": "user", "content": "|a_n-a_m| <= |a_n-L| + |L-a_m|; push each below eps/2 and it's < eps!"},
        {"role": "assistant", "content": "Completely correct — the triangle inequality is precisely the bridge between the two definitions."},
    ]},
]
