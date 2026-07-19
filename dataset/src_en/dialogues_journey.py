# -*- coding: utf-8 -*-
"""English mirror of dialogues_journey.py (weakness #7 cross-topic stuck-prone journeys,
#1 on-track affirm-only, #9 outline-refusal). Authored by Claude, verified against
reference proofs."""

DIALOGUES = [
    # ===== A3 limit of a sum (fragile) =====
    {"problem_id": "A3", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "I just finished learning the definition of limits, but I have no idea where to start on this one."},
        {"role": "assistant", "content": "That's fine — let's step back. For a single sequence $a_n\\to L$, what does the $\\varepsilon$-$N$ definition say?"},
        {"role": "user", "content": "For any ε>0 there exists N such that n≥N implies |a_n−L|<ε."},
        {"role": "assistant", "content": "Good, you know the definition. Written in the same format, which absolute value does this problem ask you to control?"},
        {"role": "user", "content": "It should be |(a_n+b_n)−(L+M)| < ε. But I only know |a_n−L| and |b_n−M| each get small — how these three quantities connect, I'm completely lost."},
        {"role": "assistant", "content": "You've named the difficulty precisely. After regrouping the sum as $(a_n-L)+(b_n-M)$, how does the absolute value of the whole relate to the two separate ones?"},
        {"role": "user", "content": "Hmm... I still can't see it. No clue on this step."},
        {"role": "assistant", "content": "The tool for this step is the triangle inequality. Using it to split that absolute value, what upper bound do you get?"},
        {"role": "user", "content": "Oh! |(a_n−L)+(b_n−M)| ≤ |a_n−L|+|b_n−M|."},
        {"role": "assistant", "content": "Exactly. To make the right side less than $\\varepsilon$, how much would you naturally allocate to each piece?"},
        {"role": "user", "content": "ε/2 each. So I need N₁ with |a_n−L|<ε/2 and N₂ with |b_n−M|<ε/2."},
        {"role": "assistant", "content": "Right. One thing remains: how do you merge the two thresholds $N_1,N_2$ into the single $N$ the definition requires?"},
        {"role": "user", "content": "Take N = max{N₁, N₂}; for n≥N both hold, and the sum is less than ε."},
        {"role": "assistant", "content": "You walked the whole path yourself. Please write the full proof starting from \"given $\\varepsilon>0$\", and I will review it."},
        {"role": "user", "content": "Proof: Given ε>0. Since a_n→L there is N₁ with |a_n−L|<ε/2 for n≥N₁; since b_n→M there is N₂ with |b_n−M|<ε/2 for n≥N₂. Let N=max{N₁,N₂}. For n≥N, |(a_n+b_n)−(L+M)|≤|a_n−L|+|b_n−M|<ε."},
        {"role": "assistant", "content": "Complete structure, correct quantifier order, and the triangle inequality is applied properly. This one is done."},
    ]},

    # ===== B2 extreme value theorem (fragile) =====
    {"problem_id": "B2", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "I know the conclusion — a continuous function on a closed interval attains a maximum — but I have no idea how to *prove* it. It feels like it should just be true."},
        {"role": "assistant", "content": "The intuitive facts are often the hardest to prove. Split it in two: before $f$ can attain a maximum, what more basic property must it have?"},
        {"role": "user", "content": "Uh... it needs an upper bound first? Otherwise there's no sup at all."},
        {"role": "assistant", "content": "Correct — step one is boundedness. Try contradiction: if $f$ were unbounded, what kind of point $x_n$ could you find for each $n$?"},
        {"role": "user", "content": "Points x_n with f(x_n)>n. But these points are scattered in [a,b] and I don't know what they do. I'm stuck."},
        {"role": "assistant", "content": "Key observation: all the $x_n$ are squeezed into the bounded set $[a,b]$. What theorem applies to bounded sequences?"},
        {"role": "user", "content": "I still can't remember... could I have a hint?"},
        {"role": "assistant", "content": "This step uses the Bolzano-Weierstrass theorem. What does it give you for $\\{x_n\\}$?"},
        {"role": "user", "content": "Oh, a convergent subsequence! x_{n_k}→x*, and x* stays in [a,b]."},
        {"role": "assistant", "content": "Good. Now continuity enters: what does $f(x_{n_k})$ tend to, and where does that clash with $f(x_{n_k})>n_k$?"},
        {"role": "user", "content": "By continuity f(x_{n_k})→f(x*), a finite value; but f(x_{n_k})>n_k goes to infinity. Contradiction, so f is bounded above."},
        {"role": "assistant", "content": "Part one done. Part two: let $M=\\sup f$. To show some point actually attains $M$, how would you pick a sequence approaching $M$?"},
        {"role": "user", "content": "Take y_n with f(y_n)→M... and then it's the same trick again? Extract y_{n_k}→y*, and continuity gives f(y*)=M."},
        {"role": "assistant", "content": "The very same trick — and you recognized it yourself. Please combine both parts into a full written proof."},
        {"role": "user", "content": "Proof: (1) If f were unbounded, pick x_n∈[a,b] with f(x_n)>n. By B-W a subsequence x_{n_k}→x*∈[a,b]; continuity gives f(x_{n_k})→f(x*) finite, contradicting f(x_{n_k})>n_k→∞. So f is bounded above. (2) Let M=sup f. Pick y_n with f(y_n)→M; by B-W take y_{n_k}→y*∈[a,b]; continuity gives f(y*)=lim f(y_{n_k})=M. So f attains its maximum at y*."},
        {"role": "assistant", "content": "Both parts are rigorous: the contradiction is explicit, and you justified that the subsequential limit stays in $[a,b]$. Done."},
    ]},

    # ===== C4 Cauchy MVT (fragile, classic two-c error) =====
    {"problem_id": "C4", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "I just learned the mean value theorem. My idea: apply MVT to f and g separately, getting f(b)−f(a)=f'(c)(b−a) and g(b)−g(a)=g'(c)(b−a), then divide. Is that right?"},
        {"role": "assistant", "content": "A natural idea — but check one detail: are the two points produced by the two applications of the MVT the same $c$?"},
        {"role": "user", "content": "Ah... not necessarily. One is c₁ and the other c₂, so dividing doesn't give f'(c)/g'(c) at a single point. Now I'm completely stuck."},
        {"role": "assistant", "content": "A valuable place to be stuck — that IS the core difficulty. Recall Rolle's theorem gives \"some point with zero derivative\". If you want the conclusion at one shared point, what would you construct so Rolle applies?"},
        {"role": "user", "content": "A new function? But I really can't figure out what it should look like."},
        {"role": "assistant", "content": "The technique is called an auxiliary function: combine $f,g$ with the endpoint differences so the two endpoint values coincide. Using $f(b)-f(a)$ and $g(b)-g(a)$ as coefficients, can you propose a candidate?"},
        {"role": "user", "content": "Maybe h(x) = (f(b)−f(a))·g(x) − (g(b)−g(a))·f(x)?"},
        {"role": "assistant", "content": "A fine candidate. Verify Rolle's hypothesis: what are $h(a)$ and $h(b)$?"},
        {"role": "user", "content": "h(a)=f(b)g(a)−g(b)f(a), and h(b)=−g(b)f(a)+f(b)g(a)... they're equal after expanding! So h(a)=h(b)."},
        {"role": "assistant", "content": "Hypothesis holds. After applying Rolle, what equation does $h'(c)=0$ expand to?"},
        {"role": "user", "content": "(f(b)−f(a))g'(c) = (g(b)−g(a))f'(c), and dividing gives the desired identity."},
        {"role": "assistant", "content": "Pause before dividing: the denominator has two factors, $g'(c)$ and $g(b)-g(a)$ — which one still needs a justification that it is nonzero?"},
        {"role": "user", "content": "g'(c)≠0 is given, but g(b)−g(a)≠0 needs an argument — if they were equal, Rolle applied to g would give a point with g'=0, contradicting the hypothesis."},
        {"role": "assistant", "content": "Every piece is in place. Please write the full proof, putting $g(b)\\ne g(a)$ at the start."},
        {"role": "user", "content": "Proof: First g(b)≠g(a): otherwise Rolle gives a point with g'=0, contradiction. Define h(x)=(f(b)−f(a))g(x)−(g(b)−g(a))f(x); h is continuous and differentiable, and h(a)=f(b)g(a)−g(b)f(a)=h(b). By Rolle there is c with h'(c)=0, i.e. (f(b)−f(a))g'(c)=(g(b)−g(a))f'(c). Dividing by g'(c)(g(b)−g(a)) gives f'(c)/g'(c)=(f(b)−f(a))/(g(b)−g(a))."},
        {"role": "assistant", "content": "Rigorous and complete: hypothesis check, construction, Rolle, and the legality of the division are all addressed. You've also learned the classic trap — the two MVT points need not coincide."},
    ]},

    # ===== D5 |∫f|≤∫|f| (fragile, long attempt + strong confusion) =====
    {"problem_id": "D5", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "I tried viewing the integral as a sum of small rectangles and using the triangle inequality on each piece — the direction feels right but I can't make it rigorous. I also tried manipulating the integrand directly, but how the absolute value outside ∫f becomes the |f| inside, I'm totally lost."},
        {"role": "assistant", "content": "Your intuition is actually correct, and the rigorous version is simpler than you think. Forget the integral for a moment: at each point $x$, what squeeze relates $f(x)$ and $|f(x)|$?"},
        {"role": "user", "content": "Just −|f(x)| ≤ f(x) ≤ |f(x)|."},
        {"role": "assistant", "content": "Right. Integration has an order-preserving property: if $u\\le v$ pointwise, what happens after integrating?"},
        {"role": "user", "content": "The inequality survives: ∫u ≤ ∫v. So integrating all three sides: −∫|f| ≤ ∫f ≤ ∫|f|."},
        {"role": "assistant", "content": "Good. The last step is pure algebra: a real number $t$ satisfying $-A\\le t\\le A$ with $A\\ge0$ is equivalent to what statement about $|t|$?"},
        {"role": "user", "content": "Equivalent to |t| ≤ A. So |∫f| ≤ ∫|f| — done!"},
        {"role": "assistant", "content": "Yes, and you walked the whole route. Please combine the three steps into a written proof."},
        {"role": "user", "content": "Proof: For all x, −|f(x)|≤f(x)≤|f(x)|. By order-preservation of the integral, −∫|f|≤∫f≤∫|f|. Let A=∫|f|≥0; then ∫f lies in [−A,A], which is equivalent to |∫f|≤A=∫|f|."},
        {"role": "assistant", "content": "Concise and correct, each step justified. By the way, your original \"small rectangles plus triangle inequality\" intuition is exactly this proof's shadow at the level of Riemann sums."},
    ]},

    # ===== E2 convergent implies Cauchy (fragile) =====
    {"problem_id": "E2", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "I keep forgetting the definition of a Cauchy sequence — it looks similar to convergence but not quite. I don't even know what this problem wants me to prove."},
        {"role": "assistant", "content": "Put the two definitions side by side. Convergence says terms get close to a limit $L$; in the Cauchy definition, what do the terms get close to?"},
        {"role": "user", "content": "To each other: for any ε>0 there is N such that m,n≥N implies |a_n−a_m|<ε."},
        {"role": "assistant", "content": "Definition correct. So we must show: knowing every term is close to $L$, deduce any two terms are close to each other. You have $|a_n-L|$ and $|a_m-L|$, and the target is $|a_n-a_m|$ — how do you connect them?"},
        {"role": "user", "content": "Hmm... intuitively if both are near L they're near each other, but writing it as an inequality — I really can't do it."},
        {"role": "assistant", "content": "The bridge is the triangle inequality: view $a_n-a_m$ as going to $L$ and back. What upper bound does splitting give?"},
        {"role": "user", "content": "|a_n−a_m| ≤ |a_n−L| + |L−a_m|. Oh, so each piece under ε/2 suffices."},
        {"role": "assistant", "content": "Right. And where does the threshold $N$ for \"each under $\\varepsilon/2$\" come from?"},
        {"role": "user", "content": "From convergence: for ε/2 there is N with |a_n−L|<ε/2 for n≥N. The same N works for both m and n."},
        {"role": "assistant", "content": "Everything is in place. Please write the full proof, starting with \"given $\\varepsilon>0$\"."},
        {"role": "user", "content": "Proof: Let a_n→L. Given ε>0, there is N with |a_n−L|<ε/2 for n≥N. For any m,n≥N, |a_n−a_m|≤|a_n−L|+|L−a_m|<ε/2+ε/2=ε. Hence {a_n} is Cauchy."},
        {"role": "assistant", "content": "Quantifiers, threshold, and the bridge are all correct. You can now also see the real difference between the two definitions: one is external (a limit), the other internal (term to term)."},
    ]},

    # ===== A7 convergent implies bounded (bright on-track, affirm-only) =====
    {"problem_id": "A7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "My idea: take ε=1, so there is N with |a_n−L|<1 for n≥N, and the whole tail is covered by |L|+1."},
        {"role": "assistant", "content": "Exactly the right direction — the tail is handled. Which terms are not yet covered?"},
        {"role": "user", "content": "The finitely many a_1 through a_{N−1}. Since there are only finitely many, they have a largest absolute value themselves."},
        {"role": "assistant", "content": "Yes — \"finitely many\" is precisely the reason it works. How do you plan to merge the two bounds into one for the whole sequence?"},
        {"role": "user", "content": "Take M = max{|a_1|,…,|a_{N−1}|, |L|+1}; then |a_n| ≤ M for every n."},
        {"role": "assistant", "content": "Good — the argument is complete. Please write it as a formal proof."},
        {"role": "user", "content": "Proof: Let a_n→L. Take ε=1: there is N with |a_n−L|<1 for n≥N, hence |a_n|≤|L|+1. Let M=max{|a_1|,…,|a_{N−1}|,|L|+1}; then |a_n|≤M for all n, so the sequence is bounded."},
        {"role": "assistant", "content": "Correct and tight. Especially good that you said \"because there are only finitely many\" unprompted — that is the true reason this proof works."},
    ]},

    # ===== C2 Rolle (bright on-track, hypothesis-checking questions only) =====
    {"problem_id": "C2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "My plan: use the extreme value theorem to get the max M and min m, then split into cases, and at an interior extremum apply Fermat's theorem to get f'(c)=0."},
        {"role": "assistant", "content": "The skeleton is exactly right. First the degenerate case: if $M=m$, what does the function look like, and how does the conclusion hold?"},
        {"role": "user", "content": "M=m means f is constant, so the derivative is 0 everywhere; any c works."},
        {"role": "assistant", "content": "Right. Now for $M>m$: why must at least one extremum land in the open interior rather than both at the endpoints?"},
        {"role": "user", "content": "Because f(a)=f(b). If both the max and min were attained at endpoints, then M and m would both equal f(a), forcing M=m — contradiction."},
        {"role": "assistant", "content": "Beautifully argued — that is exactly what the hypothesis $f(a)=f(b)$ is for. When you finally cite Fermat's theorem, which premises does it need to yield $f'(c)=0$?"},
        {"role": "user", "content": "It needs c to be an interior point and f differentiable at c — interiority was just shown, differentiability is given on (a,b)."},
        {"role": "assistant", "content": "All premises accounted for. Please write out the complete proof."},
        {"role": "user", "content": "Proof: f is continuous on [a,b], so by the extreme value theorem it attains a maximum M and minimum m. If M=m, f is constant and f'≡0 on (a,b); take any c. If M>m, since f(a)=f(b), the max or the min is attained at an interior point c∈(a,b); c is an interior extremum where f is differentiable, so by Fermat's theorem f'(c)=0."},
        {"role": "assistant", "content": "Complete with nothing missing: both cases, the interiority argument, and Fermat's premises. This could serve as a model write-up."},
    ]},

    # ===== E5 harmonic series diverges (outline-refusal) =====
    {"problem_id": "E5", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "Could you first walk me through the entire idea of the proof? I'll write it myself afterwards — that would be faster for me."},
        {"role": "assistant", "content": "If you listen first, what you remember will be my path, not yours. Step by step instead: divergence of the series is equivalent to what behavior of the partial sums $S_n$?"},
        {"role": "user", "content": "S_n doesn't converge. But 1/n keeps shrinking — why wouldn't the sum settle down? I have no clue at all."},
        {"role": "assistant", "content": "\"Terms vanish yet the sum diverges\" is exactly what makes this problem interesting. Try comparing $S_{2n}$ with $S_n$: which terms are added in between?"},
        {"role": "user", "content": "The terms 1/(n+1) + 1/(n+2) + … + 1/(2n), which is n terms."},
        {"role": "assistant", "content": "Good. Which of these $n$ terms is the smallest, and what lower bound does that give the whole block?"},
        {"role": "user", "content": "The smallest is 1/(2n), so the block is ≥ n·(1/(2n)) = 1/2. So S_{2n} − S_n ≥ 1/2, always half a step apart."},
        {"role": "assistant", "content": "And that \"always half a step apart\" contradicts which property of convergent sequences?"},
        {"role": "user", "content": "Convergent sequences are Cauchy, so S_{2n}−S_n should tend to 0, but it stays ≥ 1/2. Contradiction — S_n doesn't converge, the series diverges!"},
        {"role": "assistant", "content": "The entire proof came out of you — that's the payoff of not hearing the outline first. Please write it out in full."},
        {"role": "user", "content": "Proof: Let S_n be the partial sums. S_{2n}−S_n = Σ_{k=n+1}^{2n} 1/k has n terms, each ≥1/(2n), so S_{2n}−S_n ≥ 1/2. If S_n converged it would be Cauchy, forcing S_{2n}−S_n→0, contradicting ≥1/2. Hence the series diverges."},
        {"role": "assistant", "content": "Rigorous and elegant. And what you own now is your proof, not a transcript of mine."},
    ]},
]
