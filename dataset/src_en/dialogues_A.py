# -*- coding: utf-8 -*-
"""Topic A core dialogues (A1-A10 x 3 personas). English translation of src/dialogues_A.py.
persona: confused / error / bright. build.py injects the problem statement into the first user turn."""

DIALOGUES = [
    # ===== A1: lim n^(1/n)=1 =====
    {"problem_id": "A1", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "I'm completely lost on this one — there's an n inside the root and an n in the exponent, and I don't know where to start."},
        {"role": "assistant", "content": "First compare sizes: for $n\\ge1$, $\\sqrt[n]{n}$ is always $\\ge1$. Can you use that to define a nonnegative quantity measuring its gap from $1$?"},
        {"role": "user", "content": "Since n>=1, the n-th root of n should be >=1. So I set a_n = n^(1/n) - 1 >= 0."},
        {"role": "assistant", "content": "Good. Since $\\sqrt[n]{n}=1+a_n$, what equation about $n$ do you get by raising both sides to the $n$-th power?"},
        {"role": "user", "content": "Raising both sides to the n gives n = (1+a_n)^n."},
        {"role": "assistant", "content": "Right. Every term in the binomial expansion of $(1+a_n)^n$ is positive. If you keep only the term with $a_n^2$ as a lower bound, what inequality do you get?"},
        {"role": "user", "content": "Keeping the C(n,2)a_n^2 term gives n >= n(n-1)/2 * a_n^2."},
        {"role": "assistant", "content": "Very good. Solve that inequality for an upper bound on $a_n$, then let $n\\to\\infty$ — which theorem finishes the proof?"},
        {"role": "user", "content": "Solving gives a_n^2 <= 2/(n-1), so 0 <= a_n <= sqrt(2/(n-1)) -> 0, and by the squeeze theorem a_n -> 0, so the limit is 1."},
        {"role": "assistant", "content": "Completely correct, and the logic is complete. You've mastered the core trick: use the binomial theorem to produce a lower bound with the $a_n$-squared term, then squeeze."},
    ]},
    {"problem_id": "A1", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Here's my idea: since 1/n -> 0 as n -> infinity, n^(1/n) = n^0 = 1. Is this correct?"},
        {"role": "assistant", "content": "Careful — this is an indeterminate form of type $\\infty^0$; you can't substitute the limits of the base and the exponent separately. Can you give an example $f(n)^{g(n)}$ where the base tends to infinity and the exponent tends to zero, yet the limit is not $1$?"},
        {"role": "user", "content": "Oh... something like (2^n)^(1/n) = 2 — the exponent tends to 0 but the result is 2, not 1. So my substitution was wrong."},
        {"role": "assistant", "content": "Exactly. So let's take the rigorous route: set $a_n=\\sqrt[n]{n}-1\\ge0$ and expand $n=(1+a_n)^n$. Which term can you keep as a lower bound to pin down $a_n$?"},
        {"role": "user", "content": "Take the C(n,2)a_n^2 term of the binomial expansion, getting n >= n(n-1)/2 * a_n^2, so a_n <= sqrt(2/(n-1)) -> 0, and the limit is 1."},
        {"role": "assistant", "content": "Good — that is a valid argument. Key lesson: for exponential-form limits, never substitute the limits of base and power separately."},
    ]},
    {"problem_id": "A1", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "My plan: set a_n = n^(1/n) - 1 >= 0, then use the binomial theorem on n = (1+a_n)^n to bound a_n from above."},
        {"role": "assistant", "content": "Sharp direction. Why is the first-order term $na_n$ not enough as a lower bound — why must you keep the quadratic term?"},
        {"role": "user", "content": "The first-order term only gives n >= 1 + n a_n, which doesn't force a_n -> 0. With C(n,2)a_n^2 you get a_n^2 <= 2/(n-1)."},
        {"role": "assistant", "content": "Correct — only the quadratic term extracts the rate at which $a_n\\to0$. When you invoke the squeeze theorem at the end, what hypothesis must you check?"},
        {"role": "user", "content": "The squeeze theorem needs 0 <= a_n <= sqrt(2/(n-1)) with both ends tending to 0."},
        {"role": "assistant", "content": "Complete and flawless. You caught the most easily skipped point: why nothing less than the quadratic term works."},
    ]},

    # ===== A2: eps-delta lim x^2=4 =====
    {"problem_id": "A2", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "I've memorized the epsilon-delta definition, but I really don't know how to find delta for this one."},
        {"role": "assistant", "content": "Start by writing out the quantity to control: how does $|x^2-4|$ factor?"},
        {"role": "user", "content": "It factors as |x-2||x+2|."},
        {"role": "assistant", "content": "Good — $|x-2|$ is exactly what we control. The other factor $|x+2|$ varies; if you first assume $|x-2|<1$, what range does $x$ lie in?"},
        {"role": "user", "content": "|x-2|<1 means 1<x<3, so |x+2| is less than 5."},
        {"role": "assistant", "content": "Right. So $|x^2-4|<5|x-2|$. To make that $<\\varepsilon$, how should you choose $\\delta$ so both constraints hold at once?"},
        {"role": "user", "content": "Take delta = min{1, eps/5}; then |x-2|<delta gives |x^2-4| < 5*(eps/5) = eps."},
        {"role": "assistant", "content": "Completely correct. You've grasped the essence of $\\varepsilon$-$\\delta$: first pin the varying factor with a preliminary bound, then take the min."},
    ]},
    {"problem_id": "A2", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "I factored |x-2||x+2| and then just set delta = eps/|x+2|, so |x^2-4| = |x+2|*delta = eps."},
        {"role": "assistant", "content": "Check one thing first: in the definition, may $\\delta$ depend on the variable $x$, or only on $\\varepsilon$?"},
        {"role": "user", "content": "In the definition delta can only depend on eps, not on x... because x is chosen arbitrarily afterwards. So my choice is illegal."},
        {"role": "assistant", "content": "Exactly. To remove the dependence on $x$, first assume $|x-2|<1$. Does $|x+2|$ then have a constant upper bound free of $x$?"},
        {"role": "user", "content": "Yes: when 1<x<3, |x+2|<5. So |x^2-4|<5|x-2|."},
        {"role": "assistant", "content": "Right. Combining with the preliminary bound, how should the final $\\delta$ be written so it involves only $\\varepsilon$?"},
        {"role": "user", "content": "Take delta = min{1, eps/5}, which depends only on eps."},
        {"role": "assistant", "content": "Correct. Core lesson: $\\delta$ may depend only on $\\varepsilon$, so you must first trade the varying factor for a constant via a preliminary bound."},
    ]},
    {"problem_id": "A2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "I'd factor |x-2||x+2|, first require |x-2|<1 so |x+2|<5, then take delta=min{1, eps/5}."},
        {"role": "assistant", "content": "Steps are correct. Why must you take the min at the end — why not just write $\\delta=\\varepsilon/5$?"},
        {"role": "user", "content": "Because eps/5 could exceed 1, and then the bound |x+2|<5 would no longer hold; the min protects that bound."},
        {"role": "assistant", "content": "Precise. You see both roles of the min: it preserves the preliminary bound while also forcing the $\\varepsilon$ estimate. You've fully mastered this one."},
    ]},

    # ===== A3: lim(a_n+b_n)=L+M =====
    {"problem_id": "A3", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "This feels very abstract — the limit of a sum of two sequences. I don't know where to begin."},
        {"role": "assistant", "content": "Start by writing the goal: we want $|(a_n+b_n)-(L+M)|$ to be less than $\\varepsilon$. Which inequality splits this quantity into two parts?"},
        {"role": "user", "content": "The triangle inequality: |(a_n+b_n)-(L+M)| <= |a_n-L| + |b_n-M|."},
        {"role": "assistant", "content": "Good. Since $a_n\\to L$, to make the final sum exactly $\\varepsilon$, to what fraction of $\\varepsilon$ would you push $|a_n-L|$?"},
        {"role": "user", "content": "I can make |a_n-L| < eps/2, and likewise |b_n-M| < eps/2, so the sum is exactly eps."},
        {"role": "assistant", "content": "Exactly. Those two conditions give you an $N_1$ and an $N_2$. To have both hold simultaneously, how do you choose the final $N$?"},
        {"role": "user", "content": "Take N = max{N_1, N_2}; for n>=N both hold and the sum is < eps/2+eps/2 = eps."},
        {"role": "assistant", "content": "Completely correct. You've got both classic techniques: splitting by the triangle inequality and the $\\varepsilon/2$ allocation."},
    ]},
    {"problem_id": "A3", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "I let |a_n-L|<eps and |b_n-M|<eps, added them to get <2eps, so the limit is L+M."},
        {"role": "assistant", "content": "The direction is right, but your final bound is $2\\varepsilon$, not $\\varepsilon$. The definition requires strictly less than $\\varepsilon$ — how can you adjust the initial choices?"},
        {"role": "user", "content": "Oh, I should make each one < eps/2 from the start, so the sum is eps."},
        {"role": "assistant", "content": "Correct. (Though $2\\varepsilon$ can be rescued via \"$\\varepsilon$ arbitrary\", $\\varepsilon/2$ is cleaner.) How do you merge the two $N$'s corresponding to those conditions?"},
        {"role": "user", "content": "Take N = max{N_1, N_2}, which guarantees both eps/2 bounds hold for n>=N."},
        {"role": "assistant", "content": "Good. Lesson: budget $\\varepsilon/2$ ahead of time for the later addition, so the bound lands exactly on $\\varepsilon$."},
    ]},
    {"problem_id": "A3", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "I split with the triangle inequality into |a_n-L|+|b_n-M|, push each below eps/2, and take N=max{N_1,N_2}."},
        {"role": "assistant", "content": "Structurally complete. If the problem were about $a_n-b_n$ instead, how would your triangle inequality step change?"},
        {"role": "user", "content": "Write |(a_n-b_n)-(L-M)| <= |a_n-L| + |b_n-M|, split into the same two pieces, and everything after is identical."},
        {"role": "assistant", "content": "Correct — the difference case only rearranges signs; the estimation skeleton is unchanged. You're clearly fluent with these limit laws."},
    ]},

    # ===== A4: lim sin(n)/n = 0 =====
    {"problem_id": "A4", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "sin n keeps oscillating — I don't know how to handle limits with sin in them."},
        {"role": "assistant", "content": "Can you first \"cage\" the oscillating part: whatever $n$ is, what upper bound does the absolute value of $\\sin n$ have?"},
        {"role": "user", "content": "|sin n| <= 1, for every n."},
        {"role": "assistant", "content": "Good. Plugging that into the fraction, what simpler quantity dominates $\\left|\\dfrac{\\sin n}{n}\\right|$?"},
        {"role": "user", "content": "0 <= |sin n / n| <= 1/n."},
        {"role": "assistant", "content": "Exactly. Both ends tend to $0$ as $n\\to\\infty$ — which theorem lets you conclude?"},
        {"role": "user", "content": "Left end 0, right end 1/n -> 0, so by the squeeze theorem |sin n / n| -> 0, hence sin n / n -> 0."},
        {"role": "assistant", "content": "Completely correct. The general method for bounded oscillating factors is: take an absolute-value bound, then squeeze."},
    ]},
    {"problem_id": "A4", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "I think that because sin n has no limit, sin n / n has no limit either."},
        {"role": "assistant", "content": "The numerator having no limit doesn't mean the whole fraction has none. What range confines the size of the numerator $\\sin n$?"},
        {"role": "user", "content": "The numerator is confined to [-1,1] while the denominator grows, so the whole thing gets squeezed small... so actually it tends to 0?"},
        {"role": "assistant", "content": "Right. To make that intuition rigorous, between which expressions can $\\left|\\dfrac{\\sin n}{n}\\right|$ be squeezed?"},
        {"role": "user", "content": "0 <= |sin n/n| <= 1/n, the right side -> 0, so by the squeeze theorem the limit is 0."},
        {"role": "assistant", "content": "Correct. Lesson: a bounded quantity divided by one tending to infinity tends to zero — whether the numerator itself has a limit is irrelevant."},
    ]},
    {"problem_id": "A4", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Using |sin n|<=1 gives 0<=|sin n/n|<=1/n, and squeezing gives 0."},
        {"role": "assistant", "content": "Clean. Why squeeze the absolute value here instead of squeezing $\\sin n/n$ directly?"},
        {"role": "user", "content": "Because sin n/n jumps between positive and negative; squeezing directly needs -1/n <= sin n/n <= 1/n, while the absolute value needs only one upper bound — more concise."},
        {"role": "assistant", "content": "Correct — both write-ups work, and the absolute value saves half the effort. You fully understand the flexibility of the squeeze."},
    ]},

    # ===== A5: eps-N lim 1/n = 0 =====
    {"problem_id": "A5", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "I don't really understand the epsilon-N definition. What exactly are we supposed to prove for 1/n -> 0?"},
        {"role": "assistant", "content": "The definition demands: given any $\\varepsilon>0$, find an $N$ such that $|1/n-0|<\\varepsilon$ whenever $n\\ge N$. Can you first solve that inequality into a condition on $n$?"},
        {"role": "user", "content": "|1/n| = 1/n < eps, which solves to n > 1/eps."},
        {"role": "assistant", "content": "Good. Which property of the real numbers guarantees there exists a positive integer satisfying $N>1/\\varepsilon$?"},
        {"role": "user", "content": "The Archimedean property — it guarantees a positive integer larger than any real number 1/eps."},
        {"role": "assistant", "content": "Correct. Having chosen such an $N$, how does the relation between $1/n$ and $1/N$ for $n\\ge N$ secure the inequality?"},
        {"role": "user", "content": "For n>=N, 1/n <= 1/N < eps, so the definition holds and the limit is 0."},
        {"role": "assistant", "content": "Completely correct. The $\\varepsilon$-$N$ routine is: solve the inequality for $N$, invoke Archimedes for existence, verify monotonicity."},
    ]},
    {"problem_id": "A5", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "I take N = 1/eps, and then for n>=N we have 1/n<eps. Done."},
        {"role": "assistant", "content": "In the definition $N$ is usually required to be a positive integer, but $1/\\varepsilon$ need not be an integer. How do you fix this choice?"},
        {"role": "user", "content": "Oh — take N to be a positive integer greater than 1/eps, either via the ceiling function or by citing the Archimedean property."},
        {"role": "assistant", "content": "Correct. After the fix, $n\\ge N>1/\\varepsilon$ guarantees $1/n<\\varepsilon$. Remember this \"integer $N$\" detail from now on."},
        {"role": "user", "content": "Got it — N must be an integer, and stating it via the Archimedean property is safest."},
        {"role": "assistant", "content": "Good. Lesson: $N$ is an index of a term, hence a positive integer — never write the non-integer $1/\\varepsilon$ itself."},
    ]},
    {"problem_id": "A5", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Solving 1/n<eps gives n>1/eps; by the Archimedean property take a positive integer N>1/eps, and for n>=N, 1/n<=1/N<eps."},
        {"role": "assistant", "content": "Perfectly standard. You used \"$n\\ge N\\Rightarrow 1/n\\le 1/N$\" — which property of the sequence does that step rely on?"},
        {"role": "user", "content": "It relies on 1/n being decreasing, so larger indices give smaller values."},
        {"role": "assistant", "content": "Correct — that monotonicity is what transfers the estimate at $N$ to all $n\\ge N$. The argument is airtight."},
    ]},

    # ===== A6: lim n/2^n = 0 =====
    {"problem_id": "A6", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "The numerator n keeps growing but so does the denominator 2^n — I don't know which one wins."},
        {"role": "assistant", "content": "Exponentials usually outgrow polynomials, but rigor demands a usable lower bound for $2^n$. Expanding $2^n=(1+1)^n$ by the binomial theorem, which term can you extract?"},
        {"role": "user", "content": "You can take the C(n,2) = n(n-1)/2 term as a lower bound."},
        {"role": "assistant", "content": "Good, so $2^n\\ge \\dfrac{n(n-1)}{2}$. Substituting into $\\dfrac{n}{2^n}$, what upper bound do you get?"},
        {"role": "user", "content": "n/2^n <= n / (n(n-1)/2) = 2/(n-1)."},
        {"role": "assistant", "content": "Exactly. $0\\le \\dfrac{n}{2^n}\\le \\dfrac{2}{n-1}$, and the right end tends to zero as $n\\to\\infty$ — which theorem closes the proof?"},
        {"role": "user", "content": "The right end 2/(n-1) -> 0, so by the squeeze theorem n/2^n -> 0."},
        {"role": "assistant", "content": "Completely correct. Taking the quadratic binomial term as a lower bound is the standard trick for taming exponentials."},
    ]},
    {"problem_id": "A6", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Use L'Hopital: the derivative form of n/2^n is 1/(2^n ln2) -> 0, so the limit is 0."},
        {"role": "assistant", "content": "A sequence itself has no derivative — L'Hopital needs a function version plus differentiability, and this course wants an elementary estimate. Can you give $2^n$ a polynomial-order lower bound?"},
        {"role": "user", "content": "Using the binomial theorem, 2^n = (1+1)^n >= C(n,2) = n(n-1)/2."},
        {"role": "assistant", "content": "Good. Substituting that lower bound, what upper bound does $\\dfrac{n}{2^n}$ acquire?"},
        {"role": "user", "content": "<= 2/(n-1) -> 0, and the squeeze theorem gives limit 0."},
        {"role": "assistant", "content": "Correct. Lesson: for sequence limits, prefer binomial/inequality estimates; L'Hopital requires extra functionalization and differentiability hypotheses."},
    ]},
    {"problem_id": "A6", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "I use 2^n >= C(n,2) = n(n-1)/2 to get n/2^n <= 2/(n-1) -> 0, then squeeze."},
        {"role": "assistant", "content": "Slick. Why use the quadratic term rather than the first-order bound $2^n\\ge n$?"},
        {"role": "user", "content": "The first-order bound only gives n/2^n <= 1, which doesn't push to 0; you need the quadratic term so the upper bound tends to 0 with n."},
        {"role": "assistant", "content": "Correct — the key is that the lower bound's order must exceed the numerator's. Your instinct for this order comparison is sharp."},
    ]},

    # ===== A7: convergent implies bounded =====
    {"problem_id": "A7", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Bounded means the whole sequence is fenced in by one number, but convergence only controls the terms near L eventually — what about the early terms?"},
        {"role": "assistant", "content": "You've spotted the key: split into \"tail\" and \"head\". Applying the definition of convergence with $\\varepsilon=1$, what $N$ and what bound for $n\\ge N$ do you get?"},
        {"role": "user", "content": "With eps=1, there is N such that for n>=N, |a_n-L|<1, so |a_n| < |L|+1."},
        {"role": "assistant", "content": "Good — the tail is fenced by $|L|+1$. The head $a_1,\\dots,a_{N-1}$ has only finitely many terms; how do you fence those too?"},
        {"role": "user", "content": "There are only finitely many, so take the maximum of their absolute values."},
        {"role": "assistant", "content": "Exactly. Combining the tail bound with the max over the finitely many head terms, how do you write the final bound $M$?"},
        {"role": "user", "content": "M = max{|a_1|,...,|a_{N-1}|, |L|+1}, and then |a_n| <= M for all n."},
        {"role": "assistant", "content": "Completely correct. The core idea: finitely many terms are automatically bounded, the infinite tail is fenced by convergence, and you take the max of the two."},
    ]},
    {"problem_id": "A7", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Since a_n -> L, we have |a_n| <= |L|+1, so the sequence is bounded."},
        {"role": "assistant", "content": "That bound holds only for \"large enough $n$\". Are the terms with $n<N$ also guaranteed to satisfy $|L|+1$?"},
        {"role": "user", "content": "No — the first N-1 terms could be huge, not necessarily <= |L|+1."},
        {"role": "assistant", "content": "Right. So how do you fold those finitely many head terms into the final bound $M$?"},
        {"role": "user", "content": "Take their maximum absolute value: M = max{|a_1|,...,|a_{N-1}|, |L|+1}."},
        {"role": "assistant", "content": "Correct. Lesson: convergence controls only the tail; the finitely many early terms must be collected separately via a max."},
    ]},
    {"problem_id": "A7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Take eps=1 to get |a_n|<|L|+1 for n>=N, then set M=max{|a_1|,...,|a_{N-1}|,|L|+1}."},
        {"role": "assistant", "content": "Structurally complete. Why may you safely take the maximum over the first $N-1$ terms without worrying it might not exist?"},
        {"role": "user", "content": "Because that's a finite set — finitely many reals always have a maximum; no completeness needed."},
        {"role": "assistant", "content": "Correct — finiteness is the soul of that step. You clearly distinguish the tools needed for finite versus infinite cases."},
    ]},

    # ===== A8: a_n->L => |a_n|->|L| =====
    {"problem_id": "A8", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "I need to prove |a_n| -> |L|, but once the absolute values go on I don't know how to estimate the difference."},
        {"role": "assistant", "content": "There is a tool made exactly for differences of absolute values: the reverse triangle inequality. What can dominate $\\big||a_n|-|L|\\big|$?"},
        {"role": "user", "content": "The reverse triangle inequality: ||a_n|-|L|| <= |a_n-L|."},
        {"role": "assistant", "content": "Good — the right side is exactly what we control. Since $a_n\\to L$, for a given $\\varepsilon$ what can you make $|a_n-L|$ do?"},
        {"role": "user", "content": "There is N such that |a_n-L|<eps for n>=N."},
        {"role": "assistant", "content": "Exactly. Chaining gives $\\big||a_n|-|L|\\big|<\\varepsilon$. As a side thought: does the converse hold — can you find a counterexample?"},
        {"role": "user", "content": "The converse fails: e.g. a_n=(-1)^n, |a_n|=1 -> 1 but a_n does not converge."},
        {"role": "assistant", "content": "Completely correct — you even produced the counterexample. The reverse triangle inequality is the key tool for absolute-value limits."},
    ]},
    {"problem_id": "A8", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Since a_n -> L, |a_n| -> |L| because the absolute value is continuous. That's enough, right?"},
        {"role": "assistant", "content": "Continuity of the absolute value does work, but this problem asks for a direct estimate from the definition. Can you write an upper-bound inequality for $\\big||a_n|-|L|\\big|$?"},
        {"role": "user", "content": "Hmm... is it ||a_n|-|L|| <= |a_n-L|? That's called the reverse triangle inequality."},
        {"role": "assistant", "content": "Exactly. With it, how does $|a_n-L|<\\varepsilon$ from $a_n\\to L$ lead directly to the conclusion?"},
        {"role": "user", "content": "For n>=N, ||a_n|-|L|| <= |a_n-L| < eps, so |a_n| -> |L|."},
        {"role": "assistant", "content": "Correct. Lesson: citing \"continuity\" is quick, but foundational problems often want the reverse triangle inequality written out explicitly."},
    ]},
    {"problem_id": "A8", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "By the reverse triangle inequality ||a_n|-|L||<=|a_n-L|<eps, done. The converse fails, e.g. a_n=(-1)^n."},
        {"role": "assistant", "content": "Complete. How is the reverse triangle inequality itself derived from the standard triangle inequality?"},
        {"role": "user", "content": "From |a_n|=|a_n-L+L|<=|a_n-L|+|L| we get |a_n|-|L|<=|a_n-L|; swap the roles and combine into the absolute value."},
        {"role": "assistant", "content": "Correct — you can even prove the tool's origin. Your grasp of this problem is rock solid."},
    ]},

    # ===== A9: eps-delta lim(2x+1)=3 =====
    {"problem_id": "A9", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "This one is linear, but I'm still not sure how to arrange delta."},
        {"role": "assistant", "content": "First compute the quantity to control: what does $|(2x+1)-3|$ simplify to, in terms of $|x-1|$?"},
        {"role": "user", "content": "= |2x-2| = 2|x-1|."},
        {"role": "assistant", "content": "Good. To make $2|x-1|<\\varepsilon$, what should $\\delta$ be?"},
        {"role": "user", "content": "|x-1| < eps/2, so take delta = eps/2."},
        {"role": "assistant", "content": "Correct. Comparing with the $x^2$ problem, why is no min needed here?"},
        {"role": "user", "content": "Because the coefficient 2 is a constant, unlike |x+2| which varies with x, so no preliminary bound and no min."},
        {"role": "assistant", "content": "Completely correct. A linear function has constant slope, so $\\delta$ is simply $\\varepsilon$ divided by the slope."},
    ]},
    {"problem_id": "A9", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "|(2x+1)-3| = |2x-2|, and I take delta=eps, so when |x-1|<eps it's <eps."},
        {"role": "assistant", "content": "Compute again: $|2x-2|=2|x-1|$. If $|x-1|<\\varepsilon$, how big is this quantity — is it really $<\\varepsilon$?"},
        {"role": "user", "content": "It would be 2|x-1|<2eps, not eps. I dropped the factor 2."},
        {"role": "assistant", "content": "Exactly. To ensure $2|x-1|<\\varepsilon$, how should $\\delta$ be corrected?"},
        {"role": "user", "content": "Take delta=eps/2, so 2|x-1|<2*(eps/2)=eps."},
        {"role": "assistant", "content": "Correct. Lesson: never forget to fold the slope (coefficient) into $\\delta$ — a linear coefficient amplifies the gap."},
    ]},
    {"problem_id": "A9", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "|(2x+1)-3|=2|x-1|, so delta=eps/2 suffices, no min needed."},
        {"role": "assistant", "content": "Correct. If the function were $f(x)=kx+b$ ($k\\ne0$), what is the general formula for $\\delta$?"},
        {"role": "user", "content": "delta = eps/|k|, because |f(x)-f(x_0)| = |k||x-x_0|."},
        {"role": "assistant", "content": "Completely correct — you've extracted the general rule that in the linear case $\\delta$ is determined solely by $|k|$."},
    ]},

    # ===== A10: lim x sin(1/x)=0 =====
    {"problem_id": "A10", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "As x -> 0, sin(1/x) oscillates wildly — I don't know if this limit even exists."},
        {"role": "assistant", "content": "Cage the oscillating factor first: for all $x\\ne0$, what is the upper bound of $\\left|\\sin\\frac1x\\right|$?"},
        {"role": "user", "content": "|sin(1/x)| <= 1."},
        {"role": "assistant", "content": "Good. After multiplying by $x$, what simple quantity dominates $\\left|x\\sin\\frac1x\\right|$?"},
        {"role": "user", "content": "|x sin(1/x)| <= |x|."},
        {"role": "assistant", "content": "Exactly. $0\\le\\left|x\\sin\\frac1x\\right|\\le|x|$, and the right end tends to zero as $x\\to0$ — which theorem concludes?"},
        {"role": "user", "content": "|x| -> 0, so by the squeeze theorem x sin(1/x) -> 0."},
        {"role": "assistant", "content": "Completely correct. Even though the inner oscillation has no limit, multiplying by a bounded factor times something tending to zero still yields a squeeze conclusion."},
    ]},
    {"problem_id": "A10", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Since lim sin(1/x) does not exist, the product rule for limits says the limit does not exist, so this problem has no limit."},
        {"role": "assistant", "content": "The product rule requires both limits to exist before you may use it — it does not apply here. Try another angle: what controls the absolute value of $x\\sin\\frac1x$?"},
        {"role": "user", "content": "It's controlled by |x|, since |sin(1/x)|<=1 gives |x sin(1/x)|<=|x|."},
        {"role": "assistant", "content": "Good. Then as $x\\to0$, what does the squeeze give you?"},
        {"role": "user", "content": "|x| -> 0, so squeezing gives x sin(1/x) -> 0: the limit exists and equals 0."},
        {"role": "assistant", "content": "Correct. Lesson: the product rule presupposes both limits exist; when that fails, the squeeze often rescues the argument."},
    ]},
    {"problem_id": "A10", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Using |sin(1/x)|<=1 gives |x sin(1/x)|<=|x| -> 0, squeeze gives 0."},
        {"role": "assistant", "content": "Correct. If $x$ were replaced by $x^2$ and the inner function by $\\cos\\frac1x$, would the argument need changes?"},
        {"role": "user", "content": "No: likewise |x^2 cos(1/x)| <= x^2 -> 0; only the outer factor changes to x^2 and the squeeze goes through as before."},
        {"role": "assistant", "content": "Correct — you recognize the general pattern of \"factor tending to zero times bounded factor\". Well mastered."},
    ]},
]
