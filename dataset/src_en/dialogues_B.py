# -*- coding: utf-8 -*-
"""Topic B core dialogues (B1-B10 x 3 personas). English translation of src/dialogues_B.py."""

DIALOGUES = [
    # ===== B1: IVT (f(a)f(b)<0) =====
    {"problem_id": "B1", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Intuitively the graph must cross the x-axis, but I don't know how to prove rigorously that this c exists."},
        {"role": "assistant", "content": "The intuition is right; the key is to capture \"crossing zero\" with a set. Assume WLOG $f(a)<0<f(b)$ — can you define a set collecting the points where $f$ is negative?"},
        {"role": "user", "content": "Let S = {x in [a,b] : f(x)<0}; a is in it, so it's nonempty."},
        {"role": "assistant", "content": "Good — $S$ is nonempty and bounded above by $b$. By completeness of the reals, what does $S$ have? Take that as your candidate $c$."},
        {"role": "user", "content": "It has a supremum; let c = sup S."},
        {"role": "assistant", "content": "Exactly. Now argue by contradiction: if $f(c)>0$, continuity makes $f>0$ just to the left of $c$ too — how does that clash with $c=\\sup S$?"},
        {"role": "user", "content": "Then a whole segment left of c is >0, so some smaller number is also an upper bound of S, contradicting that c is the least upper bound."},
        {"role": "assistant", "content": "Right. After also excluding $f(c)<0$, only $f(c)=0$ remains. Can you explain why $f(c)<0$ is also contradictory?"},
        {"role": "user", "content": "If f(c)<0, continuity makes f<0 just to the right of c as well, so S contains points bigger than c, contradicting that c is an upper bound. Hence f(c)=0."},
        {"role": "assistant", "content": "Completely correct. The core is \"catch the critical point with sup, then squeeze from both sides with continuity\" — the completeness proof of the IVT."},
    ]},
    {"problem_id": "B1", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f is continuous with one negative and one positive value, so by the intermediate value theorem there is c with f(c)=0. Done."},
        {"role": "assistant", "content": "But this problem asks you to prove that very conclusion of the IVT — citing it would be circular. We must fall back on a more basic tool: which axiom of the reals can supply the critical point?"},
        {"role": "user", "content": "Oh right, I can't use the thing being proved. I should use completeness — the existence of the supremum."},
        {"role": "assistant", "content": "Exactly. Assume $f(a)<0<f(b)$, set $S=\\{x:f(x)<0\\}$ and $c=\\sup S$. Can you rule out $f(c)>0$ by contradiction?"},
        {"role": "user", "content": "If f(c)>0, continuity makes f>0 to the left of c too, giving a smaller upper bound, contradicting c=sup S."},
        {"role": "assistant", "content": "Good — and $f(c)<0$ is excluded similarly. Lesson: the theorem being proved cannot be used as a tool; retreat to the completeness axiom."},
    ]},
    {"problem_id": "B1", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "I set S={x:f(x)<0}, c=sup S, then use continuity and contradiction to show f(c) can be neither positive nor negative."},
        {"role": "assistant", "content": "Correct route. How do you ensure the resulting $c$ lies in the open interval $(a,b)$ rather than at an endpoint?"},
        {"role": "user", "content": "Since f(a)<0 and f(b)>0 are both nonzero while f(c)=0, c can equal neither a nor b, so c is in (a,b)."},
        {"role": "assistant", "content": "Correct — the nonzero endpoint values force $c$ into the open interval. Your command of the completeness proof is complete."},
    ]},

    # ===== B2: EVT =====
    {"problem_id": "B2", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "The extreme value theorem... I know the statement but have no idea where the proof even starts."},
        {"role": "assistant", "content": "Splitting the goal into two steps clarifies a lot. What property of $f$ on $[a,b]$ must the first step establish before a \"maximum\" can even be finite?"},
        {"role": "user", "content": "First show f is bounded (above), otherwise the supremum would be infinite."},
        {"role": "assistant", "content": "Exactly. If $f$ were unbounded above, you could pick $f(x_n)>n$. The $x_n$ live in a closed bounded interval — which theorem guarantees a convergent subsequence?"},
        {"role": "user", "content": "Bolzano-Weierstrass; take a subsequence x_{n_k} -> x* in [a,b]."},
        {"role": "assistant", "content": "Good. How does that conflict with $f(x_{n_k})\\to+\\infty$, proving boundedness?"},
        {"role": "user", "content": "Continuity gives f(x_{n_k}) -> f(x*), finite, contradicting the divergence to infinity, so f is bounded."},
        {"role": "assistant", "content": "Right. Step two: let $M=\\sup f$ and take $f(y_n)\\to M$. Using B-W again to extract a subsequence, what does continuity finally deliver?"},
        {"role": "user", "content": "y_{n_k} -> y*, and continuity gives f(y*) = lim f(y_{n_k}) = M, so the maximum M is attained at y*."},
        {"role": "assistant", "content": "Completely correct. Both steps run on \"extract a subsequence via B-W + pass the limit through continuity\" — the skeleton of the EVT."},
    ]},
    {"problem_id": "B2", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Let M=sup f. Since the sup exists, f must attain M at some point."},
        {"role": "assistant", "content": "Existence of $\\sup$ only guarantees you can approach $M$ arbitrarily closely, not that it is attained. Can you give a function whose supremum is not attained?"},
        {"role": "user", "content": "Like f(x)=x on the open interval (0,1): sup=1 but never attained. So we need the closed interval and continuity."},
        {"role": "assistant", "content": "Exactly. So take $f(y_n)\\to M$ with $\\{y_n\\}\\subset[a,b]$ — which theorem extracts a convergent subsequence?"},
        {"role": "user", "content": "Bolzano-Weierstrass: y_{n_k} -> y* in [a,b], and continuity gives f(y*)=M."},
        {"role": "assistant", "content": "Correct. Lesson: $\\sup$ is only the least upper bound and need not be attained; the closed interval plus continuity is what secures attainment."},
    ]},
    {"problem_id": "B2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "First boundedness by contradiction, then take an approximating sequence f(y_n) -> M, extract a subsequence via B-W, and continuity gives f(y*)=M."},
        {"role": "assistant", "content": "Structurally complete. Which two indispensable properties of the closed interval $[a,b]$ did your proof use?"},
        {"role": "user", "content": "One: boundedness, so B-W applies. Two: closedness, so the subsequential limit y* stays inside [a,b]."},
        {"role": "assistant", "content": "Correct — bounded plus closed (compactness), neither dispensable. You know exactly what each hypothesis is for."},
    ]},

    # ===== B3: Heine-Cantor =====
    {"problem_id": "B3", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "I keep mixing up uniform continuity and ordinary continuity, and I don't know how to prove this."},
        {"role": "assistant", "content": "Uniform continuity demands one $\\delta$ that works at every point. Direct proof is hard, so argue by contradiction: what does the negation of uniform continuity look like?"},
        {"role": "user", "content": "There is some eps_0>0 such that for every n we can find x_n, y_n with |x_n-y_n|<1/n but |f(x_n)-f(y_n)|>=eps_0."},
        {"role": "assistant", "content": "Good — that manufactures two sequences. $\\{x_n\\}\\subset[a,b]$: which theorem extracts a convergent subsequence?"},
        {"role": "user", "content": "Bolzano-Weierstrass: x_{n_k} -> x*."},
        {"role": "assistant", "content": "Exactly. Since $|x_{n_k}-y_{n_k}|<1/n_k\\to0$, where must $y_{n_k}$ tend?"},
        {"role": "user", "content": "y_{n_k} -> x* as well, because their distance tends to 0."},
        {"role": "assistant", "content": "Right. By continuity, where do $f(x_{n_k})$ and $f(y_{n_k})$ each tend, and how does that contradict $\\ge\\varepsilon_0$?"},
        {"role": "user", "content": "Both -> f(x*), so their difference -> 0, contradicting |f(x_n)-f(y_n)|>=eps_0. Hence f is uniformly continuous."},
        {"role": "assistant", "content": "Completely correct. Contradiction + B-W + passing limits through continuity — the standard route to Heine-Cantor."},
    ]},
    {"problem_id": "B3", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f is continuous at every point, so every point has its delta — that already makes it uniformly continuous."},
        {"role": "assistant", "content": "That is precisely the issue: the pointwise $\\delta$ may shrink from point to point. \"Uniform\" demands a single $\\delta$ valid at all points. To prove it, how would a contradiction argument begin?"},
        {"role": "user", "content": "Assume not uniformly continuous: there is eps_0, and for every n points x_n, y_n with |x_n-y_n|<1/n but difference >= eps_0."},
        {"role": "assistant", "content": "Exactly. Applying Bolzano-Weierstrass to $\\{x_n\\}$, what subsequence do you get?"},
        {"role": "user", "content": "x_{n_k} -> x*, and since the distance -> 0, y_{n_k} -> x* too. Continuity sends both images to f(x*), difference -> 0, contradiction."},
        {"role": "assistant", "content": "Correct. Lesson: pointwise continuity gives no shared $\\delta$; uniformity needs compactness (B-W) to secure it."},
    ]},
    {"problem_id": "B3", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Contradiction: build sequences with |x_n-y_n|<1/n but difference >= eps_0; B-W gives a subsequence, both sequences share the limit, continuity yields the contradiction."},
        {"role": "assistant", "content": "Very complete. At which step does the proof use, essentially, that the interval is closed and bounded rather than open?"},
        {"role": "user", "content": "The limit x* extracted by B-W must stay inside the interval with f continuous there; on an open interval x* could escape to an endpoint where continuity is unavailable."},
        {"role": "assistant", "content": "Correct — which is exactly why f(x)=1/x is continuous but not uniformly continuous on (0,1). Understood thoroughly."},
    ]},

    # ===== B4: x^2 not uniformly continuous =====
    {"problem_id": "B4", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "To prove NOT uniformly continuous, I don't know how to write the negated statement."},
        {"role": "assistant", "content": "Just negate the definition of uniform continuity. Can you write out the full negation, \"there exists $\\varepsilon_0$ such that for every $\\delta$...\"?"},
        {"role": "user", "content": "There exists eps_0>0 such that for every delta>0 we can find x, y with |x-y|<delta but |x^2-y^2|>=eps_0."},
        {"role": "assistant", "content": "Good. The key is $|x^2-y^2|=|x-y||x+y|$ — which factor blows up out of control far from the origin?"},
        {"role": "user", "content": "|x+y| grows without bound as x and y get large."},
        {"role": "assistant", "content": "Exactly. So fix $|x-y|=\\delta/2$ and place $x,y$ far out, making $|x-y||x+y|$ exceed $\\varepsilon_0$. How would you choose them?"},
        {"role": "user", "content": "Take x=n+delta/2, y=n: |x-y|=delta/2<delta, while |x^2-y^2|=(delta/2)(2n+delta/2)>=delta*n, which is >=1 for large n."},
        {"role": "assistant", "content": "Completely correct — take $\\varepsilon_0=1$ and you're done. The essence: $|x+y|$ unbounded means no single $\\delta$ can serve everywhere."},
    ]},
    {"problem_id": "B4", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "x^2 is continuous at every point, so it's uniformly continuous — is the problem statement wrong?"},
        {"role": "assistant", "content": "Pointwise continuity does not imply uniform continuity. Test it: with $\\delta$ fixed, when $x,y$ move out together, can $|x^2-y^2|$ still be controlled by $\\delta$?"},
        {"role": "user", "content": "|x^2-y^2|=|x-y||x+y|; even with |x-y| held small, the whole thing blows up as |x+y| grows. So it's not uniformly continuous."},
        {"role": "assistant", "content": "Exactly. So take concretely $x=n+\\delta/2,\\ y=n$: $|x-y|<\\delta$, but what about $|x^2-y^2|$?"},
        {"role": "user", "content": ">= delta*n, which is >=1=eps_0 for n large enough, so the negation holds and x^2 is not uniformly continuous."},
        {"role": "assistant", "content": "Correct. Lesson: uniform continuity is a strictly stronger global property than pointwise continuity, and $x^2$ on $\\mathbb{R}$ is the standard counterexample."},
    ]},
    {"problem_id": "B4", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Take eps_0=1, x=n+delta/2, y=n; then |x-y|=delta/2<delta while |x^2-y^2|=delta(n+delta/4)>=delta*n>=1 for n large."},
        {"role": "assistant", "content": "The counterexample is dead on. Why does this phenomenon not occur on the bounded interval $[0,1]$?"},
        {"role": "user", "content": "On [0,1], |x+y|<=2 is bounded, so x^2 is Lipschitz and hence uniformly continuous; only an unbounded domain lets it blow up."},
        {"role": "assistant", "content": "Correct — you've located the root cause in the unboundedness of the domain. Very clear analysis."},
    ]},

    # ===== B5: eps-delta x^2 continuous at a =====
    {"problem_id": "B5", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Proving x^2 continuous at a general point a looks like the x=2 problem but not quite — I'm stuck."},
        {"role": "assistant", "content": "Same method. Write $|x^2-a^2|=|x-a||x+a|$; the varying factor is $|x+a|$. If you first assume $|x-a|<1$, what bound does $|x+a|$ get?"},
        {"role": "user", "content": "|x+a| <= |x-a|+2|a| < 1+2|a|."},
        {"role": "assistant", "content": "Good, so $|x^2-a^2|<(1+2|a|)|x-a|$. To make that $<\\varepsilon$, how do you choose $\\delta$?"},
        {"role": "user", "content": "Take delta = min{1, eps/(1+2|a|)}."},
        {"role": "assistant", "content": "Completely correct. Note this $\\delta$ depends on $a$ — exactly where the difference from uniform continuity lies."},
    ]},
    {"problem_id": "B5", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "I wrote |x+a| <= 2|a| and took delta = eps/(2|a|)."},
        {"role": "assistant", "content": "$|x+a|\\le2|a|$ only holds approximately when $x$ is right at $a$ — but $x$ can exceed $a$. Can you derive a rigorous bound using $|x-a|<1$?"},
        {"role": "user", "content": "|x+a|=|(x-a)+2a|<=|x-a|+2|a|<1+2|a|. My 2|a| missed the |x-a| part."},
        {"role": "assistant", "content": "Exactly. After the fix, what must $\\delta$ be so the preliminary bound $|x-a|<1$ is also preserved?"},
        {"role": "user", "content": "Take delta=min{1, eps/(1+2|a|)}."},
        {"role": "assistant", "content": "Correct. Lesson: when bounding $|x+a|$, account for the offset of $x$ from $a$, and keep the preliminary bound alive with the min."},
    ]},
    {"problem_id": "B5", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Assume |x-a|<1 to get |x+a|<1+2|a|, then take delta=min{1, eps/(1+2|a|)}."},
        {"role": "assistant", "content": "Completely correct. From the fact that this $\\delta$ shrinks as $a$ grows, can you see why $x^2$ is not uniformly continuous on $\\mathbb{R}$?"},
        {"role": "user", "content": "Yes: delta contains 1/(1+2|a|), so bigger a forces smaller delta, and no delta works for all a simultaneously — hence not uniformly continuous."},
        {"role": "assistant", "content": "Correct — you saw straight through the key difference between pointwise and uniform continuity. Excellent."},
    ]},

    # ===== B6: sequential criterion =====
    {"problem_id": "B6", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Deriving \"images of sequences converge\" from eps-delta continuity — I don't know how to connect the two definitions."},
        {"role": "assistant", "content": "Lay the two definitions side by side and it clicks. The goal is $f(x_n)\\to f(x_0)$. Starting from continuity of $f$ at $x_0$, what do you get for a given $\\varepsilon$?"},
        {"role": "user", "content": "There is delta>0 such that |x-x_0|<delta implies |f(x)-f(x_0)|<eps."},
        {"role": "assistant", "content": "Good — $\\delta$ is now in hand. Next use $x_n\\to x_0$: for THIS $\\delta$, what do you get?"},
        {"role": "user", "content": "There is N such that |x_n-x_0|<delta for n>=N."},
        {"role": "assistant", "content": "Exactly — chain them. For $n\\ge N$, what happens to $|f(x_n)-f(x_0)|$?"},
        {"role": "user", "content": "<eps, so f(x_n) -> f(x_0)."},
        {"role": "assistant", "content": "Completely correct. The trick: first extract $\\delta$ from continuity, then feed that $\\delta$ to the convergence of the sequence."},
    ]},
    {"problem_id": "B6", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "First take the N from the sequence to get some delta, then use continuity... hmm, the order feels off."},
        {"role": "assistant", "content": "You've noticed the ordering problem. Which definition must produce $\\delta$ first, so it can be used in the other?"},
        {"role": "user", "content": "Continuity should produce delta first (from eps), and then x_n -> x_0 finds N for that delta. I had it backwards."},
        {"role": "assistant", "content": "Exactly. With the order fixed: $n\\ge N\\Rightarrow|x_n-x_0|<\\delta\\Rightarrow$ what?"},
        {"role": "user", "content": "=> |f(x_n)-f(x_0)|<eps, proving f(x_n) -> f(x_0)."},
        {"role": "assistant", "content": "Correct. Lesson: continuity generates $\\delta$ first, and the sequence's convergence then matches that $\\delta$ — the order cannot be flipped."},
    ]},
    {"problem_id": "B6", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Continuity gives delta(eps); then x_n -> x_0 gives N for that delta; chaining yields |f(x_n)-f(x_0)|<eps."},
        {"role": "assistant", "content": "Completely correct. That's one direction of \"continuity preserves sequential limits\". How does the converse (sequences characterizing continuity) usually go?"},
        {"role": "user", "content": "By contradiction: if f is not continuous there is eps_0, and you build x_n -> x_0 with |f(x_n)-f(x_0)|>=eps_0, a contradiction."},
        {"role": "assistant", "content": "Correct — you command the sequential characterization of continuity in both directions."},
    ]},

    # ===== B7: odd polynomial has real root =====
    {"problem_id": "B7", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Odd-degree polynomials always have a real root — I know the fact but not the proof."},
        {"role": "assistant", "content": "To use the intermediate value theorem you first need one positive and one negative value. Look at $x\\to+\\infty$: with the odd leading term dominating, where does $p(x)$ tend?"},
        {"role": "user", "content": "The leading term is the odd power x^(2k+1), so p(x) -> +infinity as x -> +infinity."},
        {"role": "assistant", "content": "Good. Combining $+\\infty$ at $+\\infty$ and $-\\infty$ at $-\\infty$, can you find points where $p$ is positive and negative respectively?"},
        {"role": "user", "content": "As x -> -infinity, p(x) -> -infinity. So there is b with p(b)>0 and a<b with p(a)<0."},
        {"role": "assistant", "content": "Exactly. $p$ is continuous on $[a,b]$ with endpoints of opposite sign — which theorem finishes?"},
        {"role": "user", "content": "The intermediate value theorem: there is c in (a,b) with p(c)=0."},
        {"role": "assistant", "content": "Completely correct. Oddness is the key: the two tails go to $\\pm\\infty$, manufacturing the sign change the IVT needs."},
    ]},
    {"problem_id": "B7", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Polynomials are continuous, so by the intermediate value theorem there must be a root."},
        {"role": "assistant", "content": "The IVT first needs the premise of \"two function values of opposite sign\", which you haven't supplied. What feature guarantees an odd-degree polynomial takes values of both signs?"},
        {"role": "user", "content": "Oh — look at the tail behavior. p -> +infinity as x -> +infinity and p -> -infinity as x -> -infinity, so it's both positive and negative somewhere."},
        {"role": "assistant", "content": "Exactly. And why does this trick fail for even degree (like $x^2+1$)?"},
        {"role": "user", "content": "Even degree has both tails of the same sign (both -> +infinity); the graph might stay entirely above the x-axis, no sign change, so no real root guaranteed."},
        {"role": "assistant", "content": "Correct. Lesson: verify the opposite-sign premise before invoking the IVT — and \"odd degree\" is precisely what supplies it."},
    ]},
    {"problem_id": "B7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "From the odd leading term, p(+infinity)=+infinity and p(-infinity)=-infinity; pick a,b with opposite signs, IVT gives the root."},
        {"role": "assistant", "content": "Concise and correct. To make \"the leading term dominates as $x\\to\\pm\\infty$\" rigorous, how do you usually handle the lower-order terms?"},
        {"role": "user", "content": "Factor out x^(2k+1): p(x) = x^(2k+1)(1 + c_{2k}/x + ...), the bracket -> 1, so the sign is decided by x^(2k+1)."},
        {"role": "assistant", "content": "Correct — factoring out the leading term and showing the bracket tends to 1 is the standard rigorization. Well done."},
    ]},

    # ===== B8: boundedness =====
    {"problem_id": "B8", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "The boundedness theorem... how do you prove a continuous function on a closed interval can't run off to infinity?"},
        {"role": "assistant", "content": "Contradiction is natural here. If $f$ were unbounded, what kind of point $x_n$ could you produce for each $n$?"},
        {"role": "user", "content": "There is x_n in [a,b] with |f(x_n)|>n."},
        {"role": "assistant", "content": "Good. The $x_n$ lie in a closed bounded interval — which theorem guarantees a convergent subsequence whose limit stays in $[a,b]$?"},
        {"role": "user", "content": "Bolzano-Weierstrass: x_{n_k} -> x*, and since [a,b] is closed, x* is in [a,b]."},
        {"role": "assistant", "content": "Exactly. Continuity makes $f(x_{n_k})$ converge, yet it also satisfies $|f(x_{n_k})|>n_k$ — where is the contradiction?"},
        {"role": "user", "content": "A convergent sequence must be bounded, but |f(x_{n_k})|>n_k -> infinity is unbounded — contradiction. So f is bounded."},
        {"role": "assistant", "content": "Completely correct. Boundedness and the EVT share the same \"B-W + continuity\" skeleton."},
    ]},
    {"problem_id": "B8", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f is continuous so every f(x) is a finite value, hence f is bounded."},
        {"role": "assistant", "content": "Finite at each point (pointwise) is not the same as globally bounded. $f(x)=1/x$ is finite at every point of $(0,1)$ yet unbounded. What property of the domain makes the difference?"},
        {"role": "user", "content": "The interval must be closed and bounded. Use contradiction: if unbounded, produce |f(x_n)|>n."},
        {"role": "assistant", "content": "Exactly. After extracting a convergent subsequence from $\\{x_n\\}$, how do closedness and continuity deliver the contradiction?"},
        {"role": "user", "content": "x_{n_k} -> x* in [a,b], f(x_{n_k}) -> f(x*) is bounded, contradicting >n_k."},
        {"role": "assistant", "content": "Correct. Lesson: pointwise finiteness is not global boundedness; the closed interval (compactness) is the key."},
    ]},
    {"problem_id": "B8", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Contradiction: |f(x_n)|>n, B-W extracts x_{n_k} -> x* in [a,b], continuity gives convergence contradicting unboundedness."},
        {"role": "assistant", "content": "Correct. The proofs of boundedness and the EVT are nearly identical — what is their logical order?"},
        {"role": "user", "content": "Boundedness comes first, so that sup f is finite; only then does step two of the EVT stand."},
        {"role": "assistant", "content": "Correct — boundedness is the preliminary lemma of the EVT. Your logical layering is very clean."},
    ]},

    # ===== B9: composition continuity =====
    {"problem_id": "B9", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Continuity of a composition means chaining two eps-deltas, and I always tangle them up."},
        {"role": "assistant", "content": "First set $y_0=g(x_0)$. From continuity of the outer $f$ at $y_0$, what $\\eta$ do you get for a given $\\varepsilon$?"},
        {"role": "user", "content": "There is eta>0 such that |y-y_0|<eta implies |f(y)-f(y_0)|<eps."},
        {"role": "assistant", "content": "Good — treat this $\\eta$ as the target the inner layer must reach. From continuity of $g$ at $x_0$, what can you get for $\\eta$?"},
        {"role": "user", "content": "There is delta>0 such that |x-x_0|<delta implies |g(x)-y_0|<eta."},
        {"role": "assistant", "content": "Exactly. Link the two chains: what does $|x-x_0|<\\delta$ imply, step by step?"},
        {"role": "user", "content": "=> |g(x)-y_0|<eta => |f(g(x))-f(y_0)|<eps, so the composition is continuous."},
        {"role": "assistant", "content": "Completely correct. The order is: outer layer produces $\\eta$, inner layer uses $\\eta$ to produce $\\delta$ — never the reverse."},
    ]},
    {"problem_id": "B9", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "Take delta from continuity of g to get some eta, then use continuity of f — chain them that way."},
        {"role": "assistant", "content": "The order is reversed. $\\eta$ is the threshold the outer $f$ produces from $\\varepsilon$; it must exist first so the inner $g$ knows how close to aim. Can you rearrange?"},
        {"role": "user", "content": "Right: first take eta from continuity of f (given eps), then take delta from continuity of g (given eta)."},
        {"role": "assistant", "content": "Exactly. Then how does the chain from $|x-x_0|<\\delta$ run all the way to $\\varepsilon$?"},
        {"role": "user", "content": "|x-x_0|<delta => |g(x)-y_0|<eta => |f(g(x))-f(y_0)|<eps."},
        {"role": "assistant", "content": "Correct. Lesson: for compositions, set thresholds from the outside in — $\\eta$ before $\\delta$."},
    ]},
    {"problem_id": "B9", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "From f continuous at y_0=g(x_0) take eta(eps); from g continuous at x_0 take delta(eta); the chain yields eps."},
        {"role": "assistant", "content": "Completely correct. Would the sequential criterion make the composition proof even cleaner?"},
        {"role": "user", "content": "Yes: x_n -> x_0 => g(x_n) -> g(x_0) (g continuous) => f(g(x_n)) -> f(g(x_0)) (f continuous) — just apply it twice."},
        {"role": "assistant", "content": "Correct — the sequential criterion turns composition continuity into two limit passes. Very clean; well mastered."},
    ]},

    # ===== B10: chord theorem =====
    {"problem_id": "B10", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "I need c with f(c)=f(c+1/2), and I have no idea how to relate the values at two different points."},
        {"role": "assistant", "content": "Turning \"two equal values\" into \"some function equals zero\" clarifies everything. Can you define a $g(x)$ so that $g(c)=0$ corresponds exactly to $f(c)=f(c+\\frac12)$?"},
        {"role": "user", "content": "Set g(x)=f(x+1/2)-f(x); then g(c)=0 means f(c)=f(c+1/2)."},
        {"role": "assistant", "content": "Good — $g$ is continuous on $[0,\\frac12]$. What do you get when you compute $g(0)+g(\\frac12)$?"},
        {"role": "user", "content": "g(0)=f(1/2)-f(0), g(1/2)=f(1)-f(1/2), and their sum = f(1)-f(0) = 0."},
        {"role": "assistant", "content": "That's the key! $g(0)+g(\\frac12)=0$ — what does that say about their signs, and which theorem do you then use?"},
        {"role": "user", "content": "g(0) and g(1/2) have opposite signs (or one is 0), so by the intermediate value theorem there is c with g(c)=0."},
        {"role": "assistant", "content": "Completely correct. The core maneuver: build the difference function $g$, show the endpoint sum is zero, apply the IVT."},
    ]},
    {"problem_id": "B10", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "I set g(x)=f(x+1/2)-f(x), claim g(0)=g(1/2), and use Rolle to get g'(c)=0."},
        {"role": "assistant", "content": "Check one thing first: the problem gives only continuity, not differentiability. Can the Rolle's theorem you're invoking even be used here?"},
        {"role": "user", "content": "Computing: g(0)=f(1/2)-f(0) and g(1/2)=f(1)-f(1/2) need not be equal; and with no differentiability, Rolle is unavailable."},
        {"role": "assistant", "content": "Exactly. But what special value does their sum give, steering you to the intermediate value theorem instead?"},
        {"role": "user", "content": "g(0)+g(1/2)=f(1)-f(0)=0, so they have opposite signs, and the IVT gives g(c)=0."},
        {"role": "assistant", "content": "Correct. Lesson: with only continuity, use the IVT — don't misapply Rolle, which needs differentiability; and actually compute the endpoint values."},
    ]},
    {"problem_id": "B10", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Set g(x)=f(x+1/2)-f(x); computing gives g(0)+g(1/2)=f(1)-f(0)=0, so opposite signs, and the IVT yields c."},
        {"role": "assistant", "content": "Very slick. If the boundary case $g(0)=0$ occurs, what one sentence must your argument add?"},
        {"role": "user", "content": "If g(0)=0 take c=0 directly; otherwise g(0) and g(1/2)=-g(0) are strictly opposite in sign and the IVT gives an interior c."},
        {"role": "assistant", "content": "Correct — covering the boundary case makes the proof watertight. Very rigorous work on this one."},
    ]},
]
