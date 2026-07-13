# -*- coding: utf-8 -*-
"""Rhythm-mismatch dialogues (10). English translation of src/dialogues_rhythm.py.

Defect found in M4 full-dialogue tests: when the student answers out of order (skipping
steps / answering half / answering the wrong question), the model fails to notice the
broken logical chain and instead rushes ahead to conclusions or declares completion early.
Training signal: the tutor must check the student's answer AGAINST THE CURRENT STEP —
  * student jumps ahead -> affirm the direction but pull back to the unestablished step
  * student answers half -> press for the missing half, don't move on
  * student answers the wrong question -> name which step that answer belongs to, refocus
  * never declare "proof complete" before intermediate steps are filled in"""

DIALOGUES = [
    # 1. A2: student jumps to the conclusion (delta=eps/5) before bounding |x+2|
    {"problem_id": "A2", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "I've factored it into |x-2||x+2|. What now?"},
        {"role": "assistant", "content": "Good. Of the two factors, which one can you control directly with δ?"},
        {"role": "user", "content": "I know the answer: take delta = min{1, eps/5} and the proof is done!"},
        {"role": "assistant", "content": "The conclusion is right, but you skipped a step: where does the $5$ in $\\varepsilon/5$ come from? That requires first establishing the bound on $|x+2|$."},
        {"role": "user", "content": "Oh right — first assume |x-2|<1, then 1<x<3, so |x+2|<5."},
        {"role": "assistant", "content": "Exactly — now every component of $\\delta=\\min\\{1,\\varepsilon/5\\}$ has its justification, and only now is the proof complete."},
    ]},

    # 2. A3: student answers the wrong question (the later "merge thresholds" step)
    {"problem_id": "A3", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "To prove the limit of the sum, where do I start?"},
        {"role": "assistant", "content": "First think: by which inequality can $|(a_n+b_n)-(L+M)|$ be split into two pieces?"},
        {"role": "user", "content": "Take N = max{N_1, N_2} and it works."},
        {"role": "assistant", "content": "That's the final step of merging thresholds — you skipped the splitting. Back to the present: what inequality pins this absolute value?"},
        {"role": "user", "content": "Oh, the triangle inequality: <= |a_n-L| + |b_n-M|."},
        {"role": "assistant", "content": "Right: split first, then push each below $\\varepsilon/2$, and only then comes your $N=\\max\\{N_1,N_2\\}$. Is the order clear now?"},
        {"role": "user", "content": "Clear — I had treated step three as step one."},
        {"role": "assistant", "content": "Good. Every step of a proof has its place; building them in order is what keeps the justifications intact."},
    ]},

    # 3. B1: student gives the wrong justification (continuity for sup's existence)
    {"problem_id": "B1", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "I've set S = {x in [a,b] : f(x)<0}. What next?"},
        {"role": "assistant", "content": "$S$ is nonempty and bounded above — why does its supremum exist?"},
        {"role": "user", "content": "Because f is continuous."},
        {"role": "assistant", "content": "Continuity enters later, when ruling out $f(c)\\ne0$. On which axiom of the reals does the supremum's existence rest?"},
        {"role": "user", "content": "Oh — completeness (the least upper bound axiom), independent of whether f is continuous."},
        {"role": "assistant", "content": "Exactly: completeness first hands you $c=\\sup S$; continuity is saved for the contradiction in the next step."},
    ]},

    # 4. B10: student declares completion early (IVT before opposite signs shown)
    {"problem_id": "B10", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "I set g(x)=f(x+1/2)-f(x), so by the IVT there is c with g(c)=0. Done!"},
        {"role": "assistant", "content": "Not yet: the IVT needs the premise of endpoints with opposite signs, which you haven't established. What does $g(0)+g(\\tfrac12)$ equal?"},
        {"role": "user", "content": "Computing: g(0)+g(1/2) = f(1)-f(0) = 0, so the two have opposite signs or one is zero."},
        {"role": "assistant", "content": "Right — that step fills in the IVT's premise, and only now is invoking it legitimate. Can you restate the order of the whole argument?"},
        {"role": "user", "content": "First build g, then compute the endpoint sum to get opposite signs, and only then use the IVT to obtain c."},
        {"role": "assistant", "content": "Completely correct — premises first, theorem afterwards. That is a complete proof."},
    ]},

    # 5. C3: student answers wrong question (endpoint check answered with Rolle's conclusion)
    {"problem_id": "C3", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "I've built g(x) = f(x) - f(a) - [(f(b)-f(a))/(b-a)](x-a)."},
        {"role": "assistant", "content": "Good. To apply Rolle to $g$, first verify its endpoint condition: what are $g(a)$ and $g(b)$?"},
        {"role": "user", "content": "Rolle gives us g'(c)=0."},
        {"role": "assistant", "content": "That's the conclusion AFTER the endpoints check. Back to the verification itself: substituting $x=a$ into $g$, what do you get?"},
        {"role": "user", "content": "g(a)=0, and then g(b)=f(b)-f(a)-(f(b)-f(a))=0 — both endpoints equal."},
        {"role": "assistant", "content": "Exactly — with the endpoint condition established, the $g'(c)=0$ you cited now stands."},
    ]},

    # 6. C7: student answers half (right side only, left side skipped)
    {"problem_id": "C7", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "The local maximum gives f(c+h) <= f(c); next we look at difference quotients, right?"},
        {"role": "assistant", "content": "Right. Take the $h>0$ side first: what is the sign of the difference quotient?"},
        {"role": "user", "content": "Numerator <=0, denominator >0, quotient <=0, so the right derivative <=0. The left side is probably similar — anyway the conclusion is 0."},
        {"role": "assistant", "content": "\"Probably similar\" is not an argument. On the left side the denominator is negative — will the quotient's sign be the same or opposite?"},
        {"role": "user", "content": "Opposite: numerator <=0, denominator <0, quotient >=0, so the left derivative >=0."},
        {"role": "assistant", "content": "Right — the two sides squeeze out $f'(c)=0$. Each side must be written out on its own; sign arguments can't be waved through with \"probably\"."},
    ]},

    # 7. D1: student declares completion early (quantified lower bound missing)
    {"problem_id": "D1", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "Contradiction: if f(x_0)>0 somewhere, continuity makes a whole nearby segment positive, contradicting zero integral. Done!"},
        {"role": "assistant", "content": "The direction is entirely right, but the \"contradiction\" still lacks one quantitative step: how much, at least, is the integral over that segment?"},
        {"role": "user", "content": "On that segment f > f(x_0)/2 with length d-c, so the integral is at least (f(x_0)/2)(d-c) > 0."},
        {"role": "assistant", "content": "One small step left: how does this positive lower bound pass to the whole $\\int_a^b f$?"},
        {"role": "user", "content": "Since f >= 0, the total integral is no less than that segment's integral, so ∫f > 0, contradicting = 0."},
        {"role": "assistant", "content": "NOW the contradiction is complete: the positive lower bound plus the nonnegativity transfer — neither can be skipped."},
    ]},

    # 8. D6: student jumps to the final substitution (constant not yet determined)
    {"problem_id": "D6", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "Set G(x)=∫_a^x f; FTC-1 gives G'=f=F', so ∫f=F(b)-F(a). Finished!"},
        {"role": "assistant", "content": "A step was skipped in the middle: between $G'=F'$ and the final identity, what unstated fact did you use?"},
        {"role": "user", "content": "Hmm... G'=F' means G-F is a constant."},
        {"role": "assistant", "content": "Right — and what is that constant? Which point do you use to determine it?"},
        {"role": "user", "content": "Use x=a: G(a)=0, so the constant is -F(a), hence G(b)=F(b)-F(a)."},
        {"role": "assistant", "content": "Exactly — with \"differ by a constant + fix it at the endpoint\" filled in, your conclusion truly holds."},
    ]},

    # 9. E1: student declares completion early (sup being the limit unproved)
    {"problem_id": "E1", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "The sequence is increasing and bounded above; let L=sup{a_n}; L is the limit. Done!"},
        {"role": "assistant", "content": "\"The sup is the limit\" is exactly the part that needs proof. Given $\\varepsilon>0$, what must you find first?"},
        {"role": "user", "content": "Find an N with a_N > L-eps, since L-eps is not an upper bound."},
        {"role": "assistant", "content": "Right. And which property then passes this lower bound to all $n\\ge N$?"},
        {"role": "user", "content": "Monotonicity: for n>=N, a_n >= a_N > L-eps, and with a_n <= L we get |a_n-L| < eps."},
        {"role": "assistant", "content": "That is the complete proof — sup gives the approach, monotonicity the propagation, and both must be said explicitly."},
    ]},

    # 10. E8: student answers wrong question (asked about even subsequence, answers remainder)
    {"problem_id": "E8", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "Alternating series — where do I start looking?"},
        {"role": "assistant", "content": "Start with the even partial sums: what does $S_{2n+2}-S_{2n}$ equal?"},
        {"role": "user", "content": "The error is at most the first omitted term: |S-S_n| <= b_{n+1}."},
        {"role": "assistant", "content": "That is the remainder estimate AFTER convergence is proved — it isn't usable yet. Back to the even subsequence: that difference equals which two terms subtracted?"},
        {"role": "user", "content": "= b_{2n+1} - b_{2n+2} >= 0 (decreasing), so the even subsequence increases."},
        {"role": "assistant", "content": "Right — first establish the two subsequences' monotonicity and common limit; only then does your remainder estimate have ground to stand on."},
    ]},
]
