# -*- coding: utf-8 -*-
"""Write-proof -> review dialogues (8). English translation of src/dialogues_writeup.py.

Completes the goal's "last mile": guidance does not end with the tutor summarizing — instead:
  1. after the key steps are walked, the tutor asks the student to WRITE the full proof
  2. the submitted draft carries one typical gap (unverified premise, unexcluded special
     case, quantifier order, strictness)
  3. in review, the tutor points at the gap WITH ONE QUESTION (no rewriting); the student
     patches it themselves
  4. completion is confirmed only after the patch
Training signal: review behavior = "check against reference proof -> point via question ->
wait for the student's fix"."""

DIALOGUES = [
    # 1. A2: gap = source of |x+2|<5 (preliminary bound) unstated
    {"problem_id": "A2", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "I understand the whole idea now: factor, pin |x+2|, take the min."},
        {"role": "assistant", "content": "Good — the final step, then: please write out the complete proof yourself, and I'll review it."},
        {"role": "user", "content": "Proof: Given eps>0. Since |x^2-4|=|x-2||x+2| and |x+2|<5, we have |x^2-4|<5|x-2|. Take delta=min{1, eps/5}; then 0<|x-2|<delta gives |x^2-4|<5*(eps/5)=eps. QED."},
        {"role": "assistant", "content": "The overall structure is right, but one justification is missing: under what premise does $|x+2|<5$ actually hold?"},
        {"role": "user", "content": "Oh — first restrict |x-2|<1, then 1<x<3 so |x+2|<5. I'll add: \"first assume |x-2|<1, giving |x+2|<5\" — which also explains the 1 inside the min."},
        {"role": "assistant", "content": "Exactly — with that sentence every constant has its origin, and only then is the proof complete."},
    ]},

    # 2. A5: gap = N written as the non-integer 1/eps
    {"problem_id": "A5", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "I've fully got the idea — solve the inequality and find N."},
        {"role": "assistant", "content": "Then please write out the complete proof and I'll review it."},
        {"role": "user", "content": "Proof: Given eps>0, take N=1/eps. For n>=N, |1/n-0|=1/n<=1/N=eps... hmm, that's <=eps not <eps, close enough anyway. QED."},
        {"role": "assistant", "content": "There are two small holes; the first one first: is $N=1/\\varepsilon$ necessarily a positive integer?"},
        {"role": "user", "content": "Not necessarily... take a positive integer N>1/eps by the Archimedean property. With that fix, for n>=N, 1/n<=1/N<eps — which also turns the <= into <, patching the second hole at the same time."},
        {"role": "assistant", "content": "Correct — one fix seals both holes: $N$ is an integer AND the strict inequality holds. The proof is complete."},
    ]},

    # 3. B1: gap = c at an endpoint not excluded
    {"problem_id": "B1", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "I can do both contradiction directions now — time to wrap up, right?"},
        {"role": "assistant", "content": "Yes — please write out the complete proof and I'll check it."},
        {"role": "user", "content": "Proof: WLOG f(a)<0<f(b). Let S={x in [a,b]: f(x)<0}, nonempty and bounded above, so by completeness c=sup S exists. If f(c)>0, continuity makes f>0 just left of c, contradicting c=sup S; if f(c)<0, continuity makes f<0 just right of c, so S has elements greater than c, contradiction. Hence f(c)=0. QED."},
        {"role": "assistant", "content": "The contradictions are written cleanly. But the problem requires $c\\in(a,b)$ (open interval) — why can your $c$ be neither $a$ nor $b$?"},
        {"role": "user", "content": "Because f(a)<0 and f(b)>0 are both nonzero while f(c)=0, so c != a and c != b, hence c in (a,b). I'll add that sentence to the end."},
        {"role": "assistant", "content": "Exactly — every requirement of the problem must map to a sentence in the proof. Now it's complete."},
    ]},

    # 4. C2: gap = constant case undiscussed
    {"problem_id": "C2", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "Extremum interior, Fermat finishes — I've got it."},
        {"role": "assistant", "content": "Then write out the complete proof and I'll review."},
        {"role": "user", "content": "Proof: f is continuous on [a,b]; by the EVT it attains maximum M and minimum m. Since f(a)=f(b), at least one of the max or min is attained at an interior point c in (a,b). By Fermat's theorem f'(c)=0. QED."},
        {"role": "assistant", "content": "The main line is right, but \"at least one interior\" fails in one situation: what happens if $M=m$?"},
        {"role": "user", "content": "If M=m then f is constant, and it doesn't matter that the extrema sit at endpoints, since f'==0 and any c in (a,b) has f'(c)=0. I'll write that case separately."},
        {"role": "assistant", "content": "Correct — with the constant case added, both situations are covered and the proof is complete."},
    ]},

    # 5. C10: gap = justification of 1/(1+xi)<1 (xi>0) unwritten
    {"problem_id": "C10", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "The MVT gives ln(1+x)=x/(1+xi); the rest is squeezing."},
        {"role": "assistant", "content": "Right — write out the complete proof and let me see it."},
        {"role": "user", "content": "Proof: Apply the MVT to f(t)=ln(1+t) on [0,x]: there is xi in (0,x) with ln(1+x)=x/(1+xi). Since 1/(1+x)<1/(1+xi)<1, multiplying by x gives x/(1+x)<ln(1+x)<x. QED."},
        {"role": "assistant", "content": "The skeleton is right. But what justifies the chain $\\frac1{1+x}<\\frac1{1+\\xi}<1$ — you never wrote it?"},
        {"role": "user", "content": "The basis is 0<xi<x: so 1<1+xi<1+x, and taking reciprocals reverses into that chain. Also multiplying by x preserves signs because x>0. I'll add both sentences."},
        {"role": "assistant", "content": "Exactly — every inequality manipulation must state its directional justification. Airtight now."},
    ]},

    # 6. D3: gap = mu in [m,M] not established before the IVT
    {"problem_id": "D3", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "Trap the average, then the IVT — I have the idea."},
        {"role": "assistant", "content": "Good — please write the complete proof."},
        {"role": "user", "content": "Proof: f is continuous; by the EVT it has minimum m and maximum M. Let mu=(1/(b-a))∫f. By the IVT there is c in [a,b] with f(c)=mu, i.e. ∫f=f(c)(b-a). QED."},
        {"role": "assistant", "content": "The IVT requires $\\mu$ to lie within $f$'s attained range — a step you haven't established: why is $\\mu\\in[m,M]$?"},
        {"role": "user", "content": "Because m<=f(x)<=M integrates (monotonicity) to m(b-a)<=∫f<=M(b-a); dividing by (b-a) gives m<=mu<=M. I'll insert that before using the IVT."},
        {"role": "assistant", "content": "Correct — verify a theorem's premises before citing it; that is the most important discipline of proof writing."},
    ]},

    # 7. E4: gap = increase of partial sums unstated (half of monotone-bounded missing)
    {"problem_id": "E4", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "Telescoping for the bound, then the monotone convergence theorem — I've got it."},
        {"role": "assistant", "content": "Then write out the complete proof and I'll review."},
        {"role": "user", "content": "Proof: For k>=2, 1/k^2 <= 1/(k(k-1)) = 1/(k-1)-1/k. Hence S_n <= 1+(1-1/n) < 2. By the monotone convergence theorem S_n converges, i.e. the series converges. QED."},
        {"role": "assistant", "content": "The bound is estimated beautifully. But the monotone convergence theorem needs two conditions and you wrote only one: why is $S_n$ increasing?"},
        {"role": "user", "content": "Because every term 1/k^2 > 0: S_{n+1} = S_n + 1/(n+1)^2 > S_n. I'll add \"positive terms, hence increasing partial sums\" at the start."},
        {"role": "assistant", "content": "Exactly — \"increasing\" and \"bounded above\" are both indispensable; with that added, the theorem is cited completely."},
    ]},

    # 8. E6: gap = using ratio<1 without fixing r
    {"problem_id": "E6", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "Iterate into a geometric series and compare — I have the idea."},
        {"role": "assistant", "content": "Please write out the complete proof and I'll review it."},
        {"role": "user", "content": "Proof: Since lim|a_{n+1}/a_n| = L < 1, from some N on the ratios are below 1, so |a_n| <= |a_N| * 1^{n-N} = |a_N|... wait, that bound is a constant, and summing constants diverges. But the idea should be right. QED?"},
        {"role": "assistant", "content": "You've hit the crux yourself: \"ratio below 1\" is not enough, because a geometric series with ratio 1 doesn't converge. Below WHAT must the ratios be pinned?"},
        {"role": "user", "content": "First fix r with L<r<1; by the limit definition the ratios are <r from some N on; iterating gives |a_n| <= |a_N| r^{n-N}; the geometric series with r<1 converges, and comparison finishes."},
        {"role": "assistant", "content": "Correct — \"inserting the fixed r\" is the soul of this proof. Write it in and the proof is complete."},
    ]},
]
