# -*- coding: utf-8 -*-
"""Topic E augmented dialogues: per problem 1 second-error variant + 3 short key-step
dialogues. English translation of src/dialogues_aug_E.py."""

DIALOGUES = [
    # ---- E1 ----
    {"problem_id": "E1", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "An increasing sequence must converge — it keeps growing, so it has to stop somewhere."},
        {"role": "assistant", "content": "Increasing without an upper bound diverges (e.g. $a_n=n$). What extra condition is needed for convergence?"},
        {"role": "user", "content": "An upper bound. Increasing + bounded above gives convergence."},
        {"role": "assistant", "content": "Exactly. What of $\\{a_n\\}$ is the limit then, and which axiom guarantees its existence?"},
        {"role": "user", "content": "The sup, guaranteed by completeness (the least upper bound axiom)."},
        {"role": "assistant", "content": "Correct. Lesson: increasing alone is not enough — an upper bound is required; the limit is the sup."},
    ]},
    {"problem_id": "E1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is the limit exactly the sup?"},
        {"role": "assistant", "content": "Because $\\sup$ is the least upper bound and the increasing sequence approaches it indefinitely. Given $\\varepsilon$, some $a_N$ can be found exceeding what value?"},
        {"role": "user", "content": "Exceeding L-eps (with L=sup), since L-eps is not an upper bound."},
        {"role": "assistant", "content": "Correct — the approach property comes from the definition of sup."},
    ]},
    {"problem_id": "E1", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "At which step is the increasing hypothesis used?"},
        {"role": "assistant", "content": "In passing $a_N>L-\\varepsilon$ to all $n\\ge N$. What relation between $a_n$ and $a_N$ does monotonicity give?"},
        {"role": "user", "content": "For n>=N, a_n >= a_N > L-eps."},
        {"role": "assistant", "content": "Correct — monotonicity propagates the lower bound."},
    ]},
    {"problem_id": "E1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is a_n <= L?"},
        {"role": "assistant", "content": "Because $L=\\sup\\{a_n\\}$ is an upper bound. So every term stays below what?"},
        {"role": "user", "content": "Below L, hence a_n <= L."},
        {"role": "assistant", "content": "Correct — the upper-bound property supplies the ceiling."},
    ]},

    # ---- E2 ----
    {"problem_id": "E2", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "I prove |a_{n+1}-a_n| -> 0 — that makes it Cauchy, right?"},
        {"role": "assistant", "content": "Vanishing consecutive differences is not Cauchy (e.g. $a_n=\\sqrt n$). Cauchy controls $|a_n-a_m|$ for ALL large $m,n$. With whom as intermediary do you estimate?"},
        {"role": "user", "content": "With the limit L: |a_n-a_m| <= |a_n-L| + |L-a_m|."},
        {"role": "assistant", "content": "Exactly — push each below $\\varepsilon/2$. Why are vanishing consecutive differences insufficient?"},
        {"role": "user", "content": "Because they can still accumulate to divergence — sqrt(n) is the example."},
        {"role": "assistant", "content": "Correct. Lesson: Cauchy controls arbitrary pairs of terms, not merely consecutive ones."},
    ]},
    {"problem_id": "E2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why use the limit L as intermediary?"},
        {"role": "assistant", "content": "Because $a_n\\to L$ is known — every term is near $L$. Into which two pieces does the triangle inequality split $|a_n-a_m|$?"},
        {"role": "user", "content": "Into |a_n-L| + |L-a_m|."},
        {"role": "assistant", "content": "Correct — L is the shared reference point."},
    ]},
    {"problem_id": "E2", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Why does the converse fail in Q?"},
        {"role": "assistant", "content": "Because $\\mathbb{Q}$ is not complete. For a rational Cauchy sequence approaching $\\sqrt2$, where does the limit lie — does it converge within $\\mathbb{Q}$?"},
        {"role": "user", "content": "The limit is irrational, outside Q, so it doesn't converge there."},
        {"role": "assistant", "content": "Correct — Cauchy convergence is equivalent to completeness."},
    ]},
    {"problem_id": "E2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why take eps/2?"},
        {"role": "assistant", "content": "Because two error pieces get added. With each below $\\varepsilon/2$, the total is exactly what?"},
        {"role": "user", "content": "Exactly eps."},
        {"role": "assistant", "content": "Correct — half is budgeted for the addition."},
    ]},

    # ---- E3 ----
    {"problem_id": "E3", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "a_n -> 0 means sum a_n converges — the terms keep shrinking after all."},
        {"role": "assistant", "content": "A common misconception. Which series has vanishing terms yet diverges, as the counterexample?"},
        {"role": "user", "content": "Sum 1/n: 1/n -> 0 but it diverges. So the converse fails."},
        {"role": "assistant", "content": "Exactly. And how is the forward statement proved with partial sums?"},
        {"role": "user", "content": "a_n = S_n - S_{n-1}, both -> S, so the difference -> 0."},
        {"role": "assistant", "content": "Correct. Lesson: $a_n\\to0$ is merely necessary — the harmonic series is the counterexample."},
    ]},
    {"problem_id": "E3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is a_n = S_n - S_{n-1}?"},
        {"role": "assistant", "content": "$S_n$ sums the first $n$ terms and $S_{n-1}$ the first $n-1$ — what remains after subtracting?"},
        {"role": "user", "content": "The n-th term a_n."},
        {"role": "assistant", "content": "Correct — the basic relation of partial sums."},
    ]},
    {"problem_id": "E3", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "How is the contrapositive of this necessary condition used?"},
        {"role": "assistant", "content": "The contrapositive says: if $a_n\\not\\to0$ the series diverges. As which test is that commonly known?"},
        {"role": "user", "content": "The term test (divergence test)."},
        {"role": "assistant", "content": "Correct — that's its practical value."},
    ]},
    {"problem_id": "E3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why does S_{n-1} also tend to S?"},
        {"role": "assistant", "content": "It's just a shifted copy of $S_n$, and subsequences of a convergent sequence share the limit. So $S_{n-1}$ tends to what?"},
        {"role": "user", "content": "To the same S."},
        {"role": "assistant", "content": "Correct — shifting doesn't change the limit."},
    ]},

    # ---- E4 ----
    {"problem_id": "E4", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "I compared with 1/k^2 <= 1/k, but sum 1/k diverges, so my comparison proves nothing."},
        {"role": "assistant", "content": "The comparison target must be a CONVERGENT upper bound. By which telescoping quantity should $\\frac1{k^2}$ be replaced so its series converges?"},
        {"role": "user", "content": "1/k^2 <= 1/(k(k-1)) = 1/(k-1) - 1/k, whose telescoping sum converges."},
        {"role": "assistant", "content": "Exactly. After telescoping, what constant bounds $S_n$?"},
        {"role": "user", "content": "< 2; increasing and bounded, hence convergent."},
        {"role": "assistant", "content": "Correct. Lesson: the comparison series itself must converge — sum 1/k won't do."},
    ]},
    {"problem_id": "E4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is summing 1/(k-1) - 1/k easy?"},
        {"role": "assistant", "content": "It's a telescoping sum — adjacent terms cancel. Summing from $k=2$ to $n$, which two terms survive?"},
        {"role": "user", "content": "1 - 1/n."},
        {"role": "assistant", "content": "Correct — everything in between cancels."},
    ]},
    {"problem_id": "E4", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Besides telescoping, what other proofs exist?"},
        {"role": "assistant", "content": "The integral test or Cauchy condensation. Against which integral does the integral test compare $\\sum1/n^2$?"},
        {"role": "user", "content": "Against ∫_1^∞ x^{-2} dx, which converges, so the series converges."},
        {"role": "assistant", "content": "Correct — several tools apply."},
    ]},
    {"problem_id": "E4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is bounding the partial sums enough?"},
        {"role": "assistant", "content": "With positive terms, $S_n$ increases. Increasing and bounded above — which theorem gives convergence?"},
        {"role": "user", "content": "The monotone convergence theorem."},
        {"role": "assistant", "content": "Correct — boundedness is the key."},
    ]},

    # ---- E5 ----
    {"problem_id": "E5", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "I use the ratio test: a_{n+1}/a_n = n/(n+1) -> 1 < 1? So it converges."},
        {"role": "assistant", "content": "The ratio limit is exactly $1$ (not $<1$), so the ratio test is inconclusive. Instead, what is the lower bound of $S_{2n}-S_n$?"},
        {"role": "user", "content": ">= n * 1/(2n) = 1/2, breaking Cauchy, so it diverges."},
        {"role": "assistant", "content": "Exactly. Why can't a ratio limit equal to $1$ decide?"},
        {"role": "user", "content": "Because at L=1 the ratio test fails and another method is needed."},
        {"role": "assistant", "content": "Correct. Lesson: ratio limit 1 is inconclusive — use the block lower bound to break Cauchy."},
    ]},
    {"problem_id": "E5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Which terms does S_{2n}-S_n sum?"},
        {"role": "assistant", "content": "The terms from index $n+1$ to $2n$: $\\sum_{k=n+1}^{2n}\\frac1k$. How many terms is that?"},
        {"role": "user", "content": "n terms."},
        {"role": "assistant", "content": "Correct — the term count is key to the lower bound."},
    ]},
    {"problem_id": "E5", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "What does the block (2^m) grouping proof conclude?"},
        {"role": "assistant", "content": "Group by $2^{m-1}<k\\le2^m$: each block sums to $\\ge\\frac12$. What lower bound does $S_{2^m}$ get?"},
        {"role": "user", "content": "S_{2^m} >= 1 + m/2 -> infinity: divergent."},
        {"role": "assistant", "content": "Correct — the other classic proof."},
    ]},
    {"problem_id": "E5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is each term >= 1/(2n)?"},
        {"role": "assistant", "content": "$k$ runs from $n+1$ to $2n$, maximal at $2n$. The minimum of $\\frac1k$ occurs at $k=2n$ and equals what?"},
        {"role": "user", "content": "1/(2n), so each term >= 1/(2n)."},
        {"role": "assistant", "content": "Correct — the largest denominator gives the smallest term."},
    ]},

    # ---- E6 ----
    {"problem_id": "E6", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "Ratio < 1, so I compare directly with sum (ratio)^n."},
        {"role": "assistant", "content": "The ratios may creep toward $1$ with $n$, so no fixed common ratio emerges. What fixed number must you choose first to compare?"},
        {"role": "user", "content": "Fix L < r < 1; beyond some term the ratio is < r."},
        {"role": "assistant", "content": "Exactly. Iterating gives $|a_n|\\le|a_N|r^{n-N}$ — comparison with which series yields convergence?"},
        {"role": "user", "content": "The geometric series sum r^n, convergent."},
        {"role": "assistant", "content": "Correct. Lesson: fix $L<r<1$ — never use the drifting ratios themselves."},
    ]},
    {"problem_id": "E6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why insert an r between L and 1?"},
        {"role": "assistant", "content": "Because a FIXED common ratio strictly below 1 is needed to pin the tail. Choosing $r$ between $L$ and $1$ guarantees what?"},
        {"role": "user", "content": "Beyond some term the ratio < r < 1, allowing geometric comparison."},
        {"role": "assistant", "content": "Correct — the fixed ratio is the precondition for comparison."},
    ]},
    {"problem_id": "E6", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "At L=1, one convergent and one divergent example?"},
        {"role": "assistant", "content": "Both have ratio limit $1$. Which converges and which diverges?"},
        {"role": "user", "content": "Sum 1/n^2 converges; sum 1/n diverges."},
        {"role": "assistant", "content": "Correct — hence L=1 decides nothing."},
    ]},
    {"problem_id": "E6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Where does |a_n| <= |a_N| r^{n-N} come from?"},
        {"role": "assistant", "content": "From each step's ratio being $<r$ for $n\\ge N$, multiplied out. Going from $a_N$ to $a_n$, how many factors of $r$?"},
        {"role": "user", "content": "n-N of them, so |a_n| <= |a_N| r^{n-N}."},
        {"role": "assistant", "content": "Correct — iterated multiplication."},
    ]},

    # ---- E7 ----
    {"problem_id": "E7", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "Sum |a_n| converges; dropping the absolute values makes the sum smaller, so sum a_n converges."},
        {"role": "assistant", "content": "With negative terms, \"smaller\" is not rigorous. Build the nonnegative auxiliary $b_n=a_n+|a_n|$ — in what range does it lie?"},
        {"role": "user", "content": "0 <= b_n <= 2|a_n|."},
        {"role": "assistant", "content": "Exactly. Comparison gives $\\sum b_n$ convergent — what follows via $a_n=b_n-|a_n|$?"},
        {"role": "user", "content": "Sum a_n = sum b_n - sum |a_n| converges."},
        {"role": "assistant", "content": "Correct. Lesson: construct the nonnegative term rather than vaguely saying \"smaller\"."},
    ]},
    {"problem_id": "E7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "What's the benefit of b_n = a_n + |a_n|?"},
        {"role": "assistant", "content": "It is nonnegative, so the comparison test applies. Does the series of its bound $2|a_n|$ converge?"},
        {"role": "user", "content": "Yes (since sum |a_n| converges), so sum b_n converges."},
        {"role": "assistant", "content": "Correct — converting to nonnegative terms is the key."},
    ]},
    {"problem_id": "E7", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "An example of conditional convergence?"},
        {"role": "assistant", "content": "Convergent but not absolutely so. Which alternating series converges while its absolute series diverges?"},
        {"role": "user", "content": "Sum (-1)^{n+1}/n converges but sum 1/n diverges — conditionally convergent."},
        {"role": "assistant", "content": "Correct — the absolute/conditional distinction."},
    ]},
    {"problem_id": "E7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Where does the left side of 0 <= b_n <= 2|a_n| come from?"},
        {"role": "assistant", "content": "From $a_n\\ge-|a_n|$, giving $b_n=a_n+|a_n|\\ge0$. And the right side $\\le2|a_n|$ from $a_n\\le|a_n|$ — right?"},
        {"role": "user", "content": "Right — both sides come from the absolute value inequalities."},
        {"role": "assistant", "content": "Correct — that pins down b_n's range."},
    ]},

    # ---- E8 ----
    {"problem_id": "E8", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "For alternating series, b_n -> 0 alone suffices for convergence, right?"},
        {"role": "assistant", "content": "Vanishing alone is not enough: if $b_n$ isn't decreasing, the even/odd subsequences may fail to be monotone and the series can diverge. What extra property of $b_n$ is needed?"},
        {"role": "user", "content": "Decreasing — that's what makes the even sums increase and the odd sums decrease."},
        {"role": "assistant", "content": "Exactly. With both subsequences monotone and bounded, what does $S_{2n+1}-S_{2n}=b_{2n+1}\\to0$ deliver?"},
        {"role": "user", "content": "Both subsequences share the limit, so S_n converges."},
        {"role": "assistant", "content": "Correct. Lesson: Leibniz needs BOTH \"decreasing\" and \"tending to zero\"."},
    ]},
    {"problem_id": "E8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is S_{2n} increasing?"},
        {"role": "assistant", "content": "Look at $S_{2n+2}-S_{2n}=b_{2n+1}-b_{2n+2}$. What sign does the decrease of $b_n$ give this difference?"},
        {"role": "user", "content": ">= 0, so S_{2n} increases."},
        {"role": "assistant", "content": "Correct — monotonicity of b_n supplies the sign."},
    ]},
    {"problem_id": "E8", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "What is Leibniz's remainder estimate?"},
        {"role": "assistant", "content": "The error $|S-S_n|$ is at most the first omitted term — that is, $\\le$ which term?"},
        {"role": "user", "content": "<= b_{n+1}."},
        {"role": "assistant", "content": "Correct — a practical error bound."},
    ]},
    {"problem_id": "E8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why do the two subsequences share one limit?"},
        {"role": "assistant", "content": "Because $S_{2n+1}-S_{2n}=b_{2n+1}\\to0$. When the gap between two convergent monotone subsequences vanishes, what happens to their limits?"},
        {"role": "user", "content": "They are equal — one common limit S."},
        {"role": "assistant", "content": "Correct — the vanishing gap forces the same limit."},
    ]},

    # ---- E9 ----
    {"problem_id": "E9", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "(1+1/n)^n: base -> 1, power -> infinity, so 1^infinity = 1."},
        {"role": "assistant", "content": "$1^\\infty$ is an indeterminate form — the limits can't be taken separately. After the binomial expansion, is $a_n$ increasing or decreasing?"},
        {"role": "user", "content": "Expanded as sum (1/k!) prod(1-j/n): factors and term count both grow, so increasing."},
        {"role": "assistant", "content": "Exactly. Now the bound: with $1/k!\\le1/2^{k-1}$, what constant bound emerges?"},
        {"role": "user", "content": "a_n < 3; increasing and bounded, so it converges to e."},
        {"role": "assistant", "content": "Correct. Lesson: $1^\\infty$ is indeterminate — prove monotone boundedness of the sequence itself."},
    ]},
    {"problem_id": "E9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why does the expansion show the increase?"},
        {"role": "assistant", "content": "As $n$ grows, each factor $(1-j/n)$ increases and an extra positive term appears. What relation does that give $a_{n+1}$ versus $a_n$?"},
        {"role": "user", "content": "a_{n+1} >= a_n: increasing."},
        {"role": "assistant", "content": "Correct — term-by-term comparison does it."},
    ]},
    {"problem_id": "E9", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "For which k does 1/k! <= 1/2^{k-1} hold?"},
        {"role": "assistant", "content": "For $k\\ge1$, $k!\\ge2^{k-1}$. How is the $k=0$ term handled?"},
        {"role": "user", "content": "The k=0 term is 1, counted separately: write 1 + sum_{k>=1}."},
        {"role": "assistant", "content": "Correct — mind the summation start."},
    ]},
    {"problem_id": "E9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why is the upper bound 3?"},
        {"role": "assistant", "content": "From $a_n\\le1+\\sum_{k\\ge1}\\frac1{2^{k-1}}$: what is that geometric sum, and the total?"},
        {"role": "user", "content": "The geometric sum is 2, so a_n < 1+2 = 3."},
        {"role": "assistant", "content": "Correct — hence the bound 3."},
    ]},

    # ---- E10 ----
    {"problem_id": "E10", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "a_n <= b_n and b_n -> 0, so a_n -> 0, hence sum a_n converges."},
        {"role": "assistant", "content": "The comparison test compares partial sums, not vanishing terms. What is the relation between $A_n$ and $B_n$, and $B_n$'s bound?"},
        {"role": "user", "content": "A_n <= B_n <= B (the total of sum b_n)."},
        {"role": "assistant", "content": "Exactly. $A_n$ increases and is $\\le B$ — which theorem gives convergence?"},
        {"role": "user", "content": "The monotone convergence theorem."},
        {"role": "assistant", "content": "Correct. Lesson: compare boundedness of partial sums, not vanishing of terms."},
    ]},
    {"problem_id": "E10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Why does A_n increase?"},
        {"role": "assistant", "content": "Because each $a_k\\ge0$: adding a term never decreases the partial sum. So how do $A_{n+1}$ and $A_n$ compare?"},
        {"role": "user", "content": "A_{n+1} >= A_n: increasing."},
        {"role": "assistant", "content": "Correct — nonnegative terms give the increase."},
    ]},
    {"problem_id": "E10", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "How is the divergence version of the comparison test stated?"},
        {"role": "assistant", "content": "The contrapositive: if $0\\le a_n\\le b_n$ and $\\sum a_n$ diverges, then $\\sum b_n$ does what?"},
        {"role": "user", "content": "Also diverges (the bigger one diverges even more)."},
        {"role": "assistant", "content": "Correct — both directions in hand."},
    ]},
    {"problem_id": "E10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Where does B_n <= B come from?"},
        {"role": "assistant", "content": "Because $\\sum b_n$ converges to $B$ with nonnegative terms, the increasing partial sums never exceed the total. So how do $B_n$ and $B$ relate?"},
        {"role": "user", "content": "B_n <= B."},
        {"role": "assistant", "content": "Correct — a convergent positive series pins its partial sums by the total."},
    ]},
]
