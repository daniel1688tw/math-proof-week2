"""Balanced 15-problem bank selected from pasted-text.txt for the v4 notebook.

The attachment is treated only as a candidate problem source.  Problem wording is
kept, while topics are rebalanced to five equal groups.  Direct restatements of a
named theorem (IVT, Rolle, Fermat, integral MVT) are not selected.
"""

from __future__ import annotations


CASES = [
    {
        "id": "C1",
        "source_index": 1,
        "topic": "Continuity",
        "difficulty": "easy",
        "statement": r"Prove that if \(f\) is continuous on \([0,1]\) and \(f(x)>0\) for every \(x\in[0,1]\), then there exists \(c>0\) such that \(f(x)\ge c\) for all \(x\in[0,1]\).",
        "reference_proof": r"By the Extreme Value Theorem, f attains a minimum m=f(x_0) on [0,1]. The hypothesis gives m=f(x_0)>0. Taking c=m yields f(x)>=c for every x in [0,1].",
        "wrong_attempt": r"Because f(x)>0 at every point, let c=inf_{x in [0,1]} f(x). Then c>0 automatically, so the result follows.",
        "wrong_issue": "Pointwise positivity alone does not make an infimum positive; compactness and attainment of the minimum must be used.",
    },
    {
        "id": "C2",
        "source_index": 4,
        "topic": "Continuity",
        "difficulty": "medium",
        "statement": r"Prove that if \(f\) is continuous on \([a,b]\) and \(f(x)\neq 0\) for all \(x\in[a,b]\), then \(f\) has the same sign on all of \([a,b]\).",
        "reference_proof": r"Choose x_0 in [a,b]. If f(x_0)>0 and there were y with f(y)<0, continuity on the interval between x_0 and y and the Intermediate Value Theorem would give z with f(z)=0, a contradiction. Hence f is positive everywhere. The case f(x_0)<0 is analogous, so f has one sign on the whole interval.",
        "wrong_attempt": r"The function never equals zero, so it cannot change sign. Therefore it has the same sign everywhere.",
        "wrong_issue": "The claim that a sign change forces a zero requires continuity and an explicit Intermediate Value Theorem argument.",
    },
    {
        "id": "C3",
        "source_index": 3,
        "topic": "Continuity",
        "difficulty": "hard",
        "statement": r"Prove that if \(f\) is continuous on \([a,b]\) and takes only rational values, then \(f\) is constant.",
        "reference_proof": r"Suppose f is not constant. Then there are u,v in [a,b] with f(u)<f(v), after interchanging them if needed. Choose an irrational number alpha strictly between f(u) and f(v). By continuity on the interval between u and v, the Intermediate Value Theorem gives t with f(t)=alpha. This contradicts that every value of f is rational. Therefore f is constant.",
        "wrong_attempt": r"The rationals are closed under limits. Since f is continuous and all its values are rational, its image is closed and therefore must be a single point.",
        "wrong_issue": "The rationals are not closed in R, and rational-valuedness alone does not show that the image is a singleton.",
        "high_logic_attempt": r"Because [a,b] is uncountable but the rational numbers are countable, two inputs must have the same f-value. Therefore f is constant.",
        "high_logic_issue": "Pigeonhole gives only one repeated value, not equality of f at every pair; the proof needs an irrational intermediate value contradiction.",
    },
    {
        "id": "D1",
        "source_index": 5,
        "topic": "Differentiation",
        "difficulty": "easy",
        "statement": r"Prove that if \(f\) is differentiable on \(\mathbb{R}\) and \(f'(x)>0\) for all \(x\in\mathbb{R}\), then \(f\) is one-to-one.",
        "reference_proof": r"Let x<y. By the Mean Value Theorem, for some c in (x,y), f(y)-f(x)=f'(c)(y-x)>0. Thus f(y)>f(x), so f is strictly increasing and hence one-to-one.",
        "wrong_attempt": r"Since f'(x)>0, f(x)>0 for every x. A positive function cannot take the same value twice, so f is one-to-one.",
        "wrong_issue": "A positive derivative implies increasing behavior, not pointwise positivity; a positive function may repeat values.",
    },
    {
        "id": "D2",
        "source_index": 8,
        "topic": "Differentiation",
        "difficulty": "medium",
        "statement": r"Prove that if \(f\) is differentiable on \(\mathbb{R}\) and \(|f'(x)|\le M\) for all \(x\), then \(|f(x)-f(y)|\le M|x-y|\) for all real \(x,y\).",
        "reference_proof": r"If x=y the result is immediate. Otherwise apply the Mean Value Theorem on the interval with endpoints x and y. For some c between them, f(x)-f(y)=f'(c)(x-y). Taking absolute values gives |f(x)-f(y)|=|f'(c)||x-y|<=M|x-y|.",
        "wrong_attempt": r"Integrating the inequality |f'|<=M from y to x immediately gives |f(x)-f(y)|<=M|x-y|.",
        "wrong_issue": "Differentiability alone does not justify invoking the Fundamental Theorem of Calculus for f'; the Mean Value Theorem supplies the valid argument.",
    },
    {
        "id": "D3",
        "source_index": 29,
        "topic": "Differentiation",
        "difficulty": "hard",
        "statement": r"Prove that if \(f\) is continuous on \([a,b]\) and differentiable on \((a,b)\), and if \(f'(x)\neq 0\) for all \(x\in(a,b)\), then \(f\) has at most one zero in \([a,b]\).",
        "reference_proof": r"Suppose f had two distinct zeros x_1<x_2 in [a,b]. The restriction of f to [x_1,x_2] is continuous and is differentiable on (x_1,x_2). Since f(x_1)=f(x_2)=0, Rolle's theorem gives c in (x_1,x_2) with f'(c)=0, contradicting the hypothesis. Hence f has at most one zero.",
        "wrong_attempt": r"If f had two zeros, the Mean Value Theorem would give a point c between them with f(c)=0, which contradicts the assumption on f'.",
        "wrong_issue": "The Mean Value/Rolle conclusion concerns f'(c), not f(c); the contradiction must be f'(c)=0.",
        "high_logic_attempt": r"Since f'(x) is never zero and derivatives are continuous, f' has one sign. Thus f is monotone and has at most one zero.",
        "high_logic_issue": "A derivative need not be continuous; the conclusion is true, but this proof inserts an unstated continuity assumption instead of using Rolle's theorem directly.",
    },
    {
        "id": "I1",
        "source_index": 18,
        "topic": "Integration",
        "difficulty": "easy",
        "statement": r"Prove that if \(f\) is continuous on \([0,1]\), then \(\int_0^1 f(x)\,dx=\int_0^1 f(1-x)\,dx\).",
        "reference_proof": r"In the right-hand integral set u=1-x, so du=-dx. As x goes from 0 to 1, u goes from 1 to 0. Therefore integral_0^1 f(1-x) dx = integral_1^0 f(u)(-du)=integral_0^1 f(u)du, which is the left-hand integral after renaming u.",
        "wrong_attempt": r"Replace x by 1-x in the integrand. Since the interval is still [0,1], the two integrals are automatically equal.",
        "wrong_issue": "A substitution must also transform the differential and reverse the bounds; equality is not automatic from replacing the symbol.",
    },
    {
        "id": "I2",
        "source_index": 15,
        "topic": "Integration",
        "difficulty": "medium",
        "statement": r"Prove that if \(f\) is continuous on \([a,b]\), \(\int_a^b f(x)\,dx=0\), and \(f(x)\ge 0\) for all \(x\), then \(f(x)=0\) for all \(x\in[a,b]\).",
        "reference_proof": r"Suppose f(x_0)>0 for some x_0. By continuity, f(x)>=f(x_0)/2 on a nondegenerate one-sided or two-sided interval around x_0 contained in [a,b]. Since f is nonnegative elsewhere, the integral over [a,b] is then strictly positive, contradicting that it is zero. Hence no such x_0 exists and f is identically zero.",
        "wrong_attempt": r"The integral average is zero, so the integral mean value theorem gives one c with f(c)=0. By continuity, f(x)=0 for every x.",
        "wrong_issue": "One zero of a continuous nonnegative function does not make the function identically zero; a positive point must be ruled out using a positive neighborhood.",
    },
    {
        "id": "I3",
        "source_index": 20,
        "topic": "Integration",
        "difficulty": "hard",
        "statement": r"Prove that if \(f\) is continuous on \([a,b]\) and \(\int_a^b f(x)g(x)\,dx=0\) for every continuous function \(g\), then \(f(x)=0\) for all \(x\in[a,b]\).",
        "reference_proof": r"The hypothesis holds for every continuous g, so choose g=f. Then integral_a^b f(x)^2 dx=0. The function f^2 is continuous and nonnegative. If f(x_0) were nonzero, continuity would make f^2 bounded below by a positive number on a nondegenerate neighborhood of x_0, forcing the integral to be positive. Thus f(x)=0 everywhere.",
        "wrong_attempt": r"Take g(x)=1. Then integral_a^b f(x) dx=0, and therefore f(x)=0 for every x.",
        "wrong_issue": "A continuous function can have integral zero without being identically zero; the universal quantifier should be used with g=f.",
        "high_logic_attempt": r"Choose g(x)=sign(f(x)). Then the hypothesis gives integral_a^b |f(x)| dx=0, so f=0.",
        "high_logic_issue": "sign(f) need not be continuous at zeros and therefore may not be an admissible test function; g=f is the valid continuous choice.",
    },
    {
        "id": "S1",
        "source_index": 27,
        "topic": "Sequences and Series",
        "difficulty": "easy",
        "statement": r"Prove that if \(\sum a_n\) converges absolutely and \((b_n)\) is bounded, then \(\sum a_nb_n\) converges absolutely.",
        "reference_proof": r"Because (b_n) is bounded, there is M>=0 such that |b_n|<=M for all n. Hence |a_n b_n|<=M|a_n|. Since sum |a_n| converges, the comparison test gives convergence of sum |a_n b_n|. Thus sum a_n b_n converges absolutely.",
        "wrong_attempt": r"A bounded sequence b_n must converge to some B. Hence a_n b_n behaves like B a_n, so the series converges absolutely.",
        "wrong_issue": "Boundedness does not imply convergence; the proof should use a uniform bound and comparison of absolute values.",
    },
    {
        "id": "S2",
        "source_index": 24,
        "topic": "Sequences and Series",
        "difficulty": "medium",
        "statement": r"Prove that if a sequence \((x_n)\) is increasing and bounded above, then the sequence \((\sin x_n)\) need not be increasing, but it must have a convergent subsequence.",
        "reference_proof": r"By monotone convergence, x_n converges to some ell. Continuity of sine gives sin(x_n)->sin(ell), so the entire sine sequence converges and therefore has a convergent subsequence. It need not be increasing: x_n=pi-1/n is increasing and bounded above by pi, while sin(x_n)=sin(1/n) is decreasing for n>=1.",
        "wrong_attempt": r"Since x_n is increasing and sine is continuous, sin(x_n) is increasing. It is bounded, so it has a convergent subsequence.",
        "wrong_issue": "Continuity does not preserve monotonicity; sine is not increasing on all of R, although convergence follows from x_n converging.",
    },
    {
        "id": "S3",
        "source_index": 28,
        "topic": "Sequences and Series",
        "difficulty": "hard",
        "statement": r"Prove that if a power series \(\sum c_nx^n\) converges at \(x=r>0\), then it converges absolutely for every \(x\) with \(|x|<r\).",
        "reference_proof": r"Convergence of sum c_n r^n implies the sequence c_n r^n is bounded, say |c_n r^n|<=M. Fix |x|<r and put q=|x|/r<1. Then |c_n x^n|=|c_n r^n|q^n<=M q^n. The geometric series sum M q^n converges, so comparison proves that sum |c_n x^n| converges.",
        "wrong_attempt": r"Since c_n r^n tends to zero, the series sum |c_n r^n| converges. Because |x|<r, absolute convergence at x follows immediately.",
        "wrong_issue": "Terms tending to zero do not imply absolute convergence at r; only boundedness of c_n r^n is needed for comparison inside the radius.",
        "high_logic_attempt": r"Apply the ratio test: |c_{n+1}x^{n+1}/(c_nx^n)|=|x|/r<1 because the series converges at r.",
        "high_logic_issue": "Convergence at r gives no limit for c_{n+1}/c_n, so the displayed ratio equality is unjustified; bounded terms at r and geometric comparison are required.",
    },
    {
        "id": "L1",
        "source_index": 26,
        "topic": "Limits",
        "difficulty": "easy",
        "statement": r"Prove that if \(a_n\to 0\) and \((b_n)\) is bounded, then \(a_nb_n\to 0\).",
        "reference_proof": r"Choose M>=0 with |b_n|<=M for every n. If M=0 the result is immediate. Otherwise, given epsilon>0, choose N so that n>=N implies |a_n|<epsilon/M. Then |a_n b_n|<=M|a_n|<epsilon. Therefore a_n b_n tends to zero.",
        "wrong_attempt": r"By the product law for limits, lim(a_n b_n)=(lim a_n)(lim b_n)=0, so the product tends to zero.",
        "wrong_issue": "The bounded sequence b_n need not have a limit, so the product law cannot be invoked in that form.",
    },
    {
        "id": "L2",
        "source_index": 25,
        "topic": "Limits",
        "difficulty": "medium",
        "statement": r"Prove that if \(a_n\to L\) and \(f\) is continuous at \(L\), then \(f(a_n)\to f(L)\).",
        "reference_proof": r"Let epsilon>0. Continuity of f at L gives delta>0 such that |x-L|<delta implies |f(x)-f(L)|<epsilon. Since a_n->L, there is N such that n>=N implies |a_n-L|<delta. Hence n>=N implies |f(a_n)-f(L)|<epsilon, proving the desired convergence.",
        "wrong_attempt": r"Because a_n tends to L, eventually a_n=L. Therefore eventually f(a_n)=f(L), which proves convergence.",
        "wrong_issue": "Convergence does not imply eventual equality; the delta from continuity must be combined with the tail estimate for a_n.",
    },
    {
        "id": "L3",
        "source_index": 19,
        "topic": "Limits",
        "difficulty": "hard",
        "statement": r"Prove that if \(f\) is continuous on \([0,1]\), then \(\lim_{n\to\infty}\int_0^1 f(x)x^n\,dx=0\).",
        "reference_proof": r"Continuity on [0,1] makes f bounded: |f(x)|<=M. Therefore |integral_0^1 f(x)x^n dx|<=integral_0^1 |f(x)|x^n dx<=M integral_0^1 x^n dx=M/(n+1). The last quantity tends to zero, so the squeeze theorem gives the result.",
        "wrong_attempt": r"The functions x^n converge uniformly to zero on [0,1]. Therefore f(x)x^n also converges uniformly to zero, and the limit may be moved through the integral.",
        "wrong_issue": "x^n does not converge uniformly to zero on [0,1] (indeed x^n=1 at x=1); a direct M/(n+1) bound is needed.",
        "high_logic_attempt": r"For every x in [0,1], x^n tends to zero, so f(x)x^n tends pointwise to zero. Pointwise convergence always permits exchanging limit and integral.",
        "high_logic_issue": "At x=1 the pointwise limit is not zero, and pointwise convergence alone does not justify interchanging limit and integral; boundedness gives an elementary integral estimate.",
    },
]


# The production use case is code-switched: English problem statements with
# Traditional-Chinese tutoring dialogue.  Keep the English originals above for
# the matched language probe, and attach verified Chinese dialogue fixtures for
# the primary experiment.
CASE_DIALOGUE_ZH = {
    "C1": {
        "wrong_attempt_zh": r"因為每一點都有 f(x)>0，所以令 c=inf_{x in [0,1]} f(x)。那麼 c 自動大於 0，因此結論成立。",
        "wrong_issue_zh": "逐點為正不保證下確界大於零；必須利用緊緻性以及最小值確實能取到。",
    },
    "C2": {
        "wrong_attempt_zh": r"函數從不等於零，所以它不可能變號，因此在整個區間上同號。",
        "wrong_issue_zh": "變號必經零需要連續性，必須明確使用中間值定理論證。",
    },
    "C3": {
        "wrong_attempt_zh": r"有理數對極限封閉。因為 f 連續而且所有函數值都是有理數，所以像集是閉集，因而只能是單點集。",
        "wrong_issue_zh": "有理數在實數中不是閉集，而且值域只含有理數並不能直接推出像集只有一點。",
        "high_logic_attempt_zh": r"因為 [a,b] 不可數而有理數可數，所以必有兩個輸入具有相同的 f 值，因此 f 是常數函數。",
        "high_logic_issue_zh": "鴿籠原理最多得到某個值重複，不能推出任意兩點函數值相等；需要以無理中間值導出矛盾。",
    },
    "D1": {
        "wrong_attempt_zh": r"因為 f'(x)>0，所以每個 x 都有 f(x)>0。正函數不可能取兩次相同的值，因此 f 是一對一。",
        "wrong_issue_zh": "導數為正表示函數嚴格遞增，不表示函數值逐點為正；正函數仍可能重複取值。",
    },
    "D2": {
        "wrong_attempt_zh": r"直接把不等式 |f'|<=M 從 y 積分到 x，就立即得到 |f(x)-f(y)|<=M|x-y|。",
        "wrong_issue_zh": "只有可微不足以直接對 f' 使用微積分基本定理；應由中值定理取得合法論證。",
    },
    "D3": {
        "wrong_attempt_zh": r"如果 f 有兩個零點，中值定理會給出兩點之間某個 c 使 f(c)=0，這與 f' 的假設矛盾。",
        "wrong_issue_zh": "中值定理或 Rolle 定理的結論是 f'(c)=0，不是 f(c)=0；真正的矛盾必須落在導數。",
        "high_logic_attempt_zh": r"因為 f'(x) 永不為零，而且導數是連續的，所以 f' 同號，故 f 單調並且至多有一個零點。",
        "high_logic_issue_zh": "導數不一定連續；結論雖正確，但此論證加入了未給定的連續性，應直接使用 Rolle 定理。",
    },
    "I1": {
        "wrong_attempt_zh": r"在被積函數中把 x 換成 1-x。因為積分區間仍是 [0,1]，兩個積分自動相等。",
        "wrong_issue_zh": "代換時還必須處理微分與上下限反向，不能只靠更換符號就宣稱相等。",
    },
    "I2": {
        "wrong_attempt_zh": r"積分平均值是零，所以積分中值定理給出某個 c 使 f(c)=0。再由連續性可得所有 x 都有 f(x)=0。",
        "wrong_issue_zh": "連續非負函數只有一個零點並不能推出恆為零；必須假設存在正值點，再用其正值鄰域導出積分為正。",
    },
    "I3": {
        "wrong_attempt_zh": r"取 g(x)=1，就有 integral_a^b f(x) dx=0，因此每個 x 都有 f(x)=0。",
        "wrong_issue_zh": "連續函數的積分可以為零而函數不恆為零；應利用『每個 g』這個量詞選取 g=f。",
        "high_logic_attempt_zh": r"取 g(x)=sign(f(x))，則假設給出 integral_a^b |f(x)| dx=0，所以 f=0。",
        "high_logic_issue_zh": "sign(f) 在零點可能不連續，因此未必是允許的測試函數；合法的連續選擇是 g=f。",
    },
    "S1": {
        "wrong_attempt_zh": r"有界數列 b_n 必收斂到某個 B，因此 a_n b_n 的行為像 B a_n，所以級數絕對收斂。",
        "wrong_issue_zh": "有界不代表收斂；應使用一致上界並比較 |a_n b_n| 與 |a_n|。",
    },
    "S2": {
        "wrong_attempt_zh": r"因為 x_n 遞增且 sine 連續，所以 sin(x_n) 也遞增。它又有界，因此有收斂子數列。",
        "wrong_issue_zh": "連續性不保持單調性，而且 sine 並非在整條實數軸上遞增；收斂性應由 x_n 本身收斂推出。",
    },
    "S3": {
        "wrong_attempt_zh": r"因為 c_n r^n 趨近零，所以級數 sum |c_n r^n| 收斂。又因 |x|<r，可立即得到 x 處的絕對收斂。",
        "wrong_issue_zh": "項趨近零不代表在 r 處絕對收斂；內部比較只需要 c_n r^n 有界。",
        "high_logic_attempt_zh": r"使用比值判別法：|c_{n+1}x^{n+1}/(c_nx^n)|=|x|/r<1，因為級數在 r 收斂。",
        "high_logic_issue_zh": "在 r 收斂不會給出 c_{n+1}/c_n 的極限，所寫的比值等式沒有依據；應使用 r 處項的有界性與幾何級數比較。",
    },
    "L1": {
        "wrong_attempt_zh": r"由極限的乘法法則，lim(a_n b_n)=(lim a_n)(lim b_n)=0，所以乘積趨近零。",
        "wrong_issue_zh": "有界數列 b_n 未必有極限，因此不能用這種形式的乘法法則。",
    },
    "L2": {
        "wrong_attempt_zh": r"因為 a_n 趨近 L，所以最後 a_n 會等於 L，因此最後 f(a_n)=f(L)，這就證明了收斂。",
        "wrong_issue_zh": "收斂不表示最終相等；必須把連續性給出的 delta 與數列尾端估計結合。",
    },
    "L3": {
        "wrong_attempt_zh": r"函數 x^n 在 [0,1] 上一致收斂到零，所以 f(x)x^n 也一致收斂到零，並可把極限移入積分。",
        "wrong_issue_zh": "x^n 在 [0,1] 上不一致收斂到零，因為 x=1 時始終為 1；需要直接估計 M/(n+1)。",
        "high_logic_attempt_zh": r"對每個 x in [0,1]，x^n 都趨近零，所以 f(x)x^n 逐點趨近零；逐點收斂一定允許交換極限與積分。",
        "high_logic_issue_zh": "x=1 時逐點極限不是零，而且逐點收斂本身不足以交換極限與積分；有界性可給出初等積分估計。",
    },
}

for _case in CASES:
    _case.update(CASE_DIALOGUE_ZH[_case["id"]])


EXCLUDED_DIRECT_THEOREM_ITEMS = {
    2: "Direct Intermediate Value Theorem statement",
    6: "Rolle's theorem statement",
    11: "Fermat's theorem statement",
    16: "Integral mean value theorem statement",
}


STRESS_CASE_IDS = ["C3", "D3", "I3", "S3", "L3"]


TEACH_STEPS = {
    "C3": [
        ("Assume for contradiction that f is not constant.", "What assumption starts the contradiction proof?"),
        ("Choose u and v with f(u) different from f(v).", "Which two inputs witness nonconstancy?"),
        ("Relabel them so that f(u)<f(v).", "What order may we impose on their function values?"),
        ("Both endpoint values are rational by hypothesis.", "What number type are f(u) and f(v)?"),
        ("Choose an irrational alpha strictly between f(u) and f(v).", "What kind of number should be chosen between the values?"),
        ("Restrict f to the closed interval with endpoints u and v.", "On which interval will continuity be used?"),
        ("The Intermediate Value Theorem gives t with f(t)=alpha.", "Which theorem produces t?"),
        ("But f(t) must be rational by the range hypothesis.", "What does the range hypothesis say about f(t)?"),
        ("This contradicts the irrationality of alpha.", "What are the two incompatible conclusions about f(t)?"),
        ("Therefore the nonconstant assumption is false and f is constant.", "What final conclusion follows from the contradiction?"),
    ],
    "D3": [
        ("Assume f has two distinct zeros x_1 and x_2.", "What contradiction assumption should be made?"),
        ("Order them so that x_1<x_2.", "How should the two zeros be ordered?"),
        ("Consider the restriction of f to [x_1,x_2].", "Which subinterval is relevant?"),
        ("It is continuous on that closed interval.", "Which continuity hypothesis is inherited?"),
        ("It is differentiable on the corresponding open interval.", "Which differentiability hypothesis is inherited?"),
        ("The endpoint values are equal because both are zero.", "What equality holds at the endpoints?"),
        ("Rolle's theorem therefore gives c in (x_1,x_2).", "Which theorem now applies?"),
        ("Its conclusion is f'(c)=0.", "What derivative conclusion does Rolle's theorem give?"),
        ("That contradicts f'(x) being nonzero everywhere in (a,b).", "Which hypothesis is contradicted?"),
        ("Hence f has at most one zero in [a,b].", "What uniqueness conclusion follows?"),
    ],
    "I3": [
        ("Use the phrase 'for every continuous g' to choose a useful test function.", "Which quantifier gives us freedom to choose g?"),
        ("Choose g=f.", "What admissible test function should be selected?"),
        ("This choice is allowed because f is continuous.", "Why is g=f admissible?"),
        ("The hypothesis becomes integral f(x)^2 dx=0.", "What integral identity results?"),
        ("The function h=f^2 is continuous and nonnegative.", "What two properties does h have?"),
        ("Assume f(x_0) is nonzero at some point.", "What contradiction assumption tests whether f vanishes?"),
        ("Then h(x_0)>0.", "What follows for h at that point?"),
        ("Continuity makes h positive on a nondegenerate neighborhood.", "What local lower bound does continuity provide?"),
        ("That neighborhood forces the integral of h to be positive, a contradiction.", "Why would the integral then be positive?"),
        ("Therefore f is zero at every point of [a,b].", "What final conclusion follows?"),
    ],
    "S3": [
        ("Convergence at r implies c_n r^n tends to zero.", "What must the terms at r do?"),
        ("Every convergent sequence is bounded, so |c_n r^n|<=M.", "What uniform bound follows?"),
        ("Fix x with |x|<r.", "Which x values are under consideration?"),
        ("Set q=|x|/r, so 0<=q<1.", "What comparison ratio should be defined?"),
        ("Rewrite |c_n x^n| as |c_n r^n|q^n.", "How can the nth term be factored?"),
        ("Use the bound to obtain |c_n x^n|<=M q^n.", "What termwise inequality follows?"),
        ("The geometric series sum Mq^n converges.", "Which comparison series converges?"),
        ("The comparison test yields convergence of sum |c_n x^n|.", "Which test now applies?"),
        ("Thus the original power series converges absolutely at this x.", "What kind of convergence has been proved?"),
        ("Because x was arbitrary with |x|<r, the claim holds throughout the interior.", "How is the universal conclusion obtained?"),
    ],
    "L3": [
        ("Continuity on [0,1] implies f is bounded.", "Which compactness consequence should be used first?"),
        ("Choose M with |f(x)|<=M for all x.", "What uniform bound may be fixed?"),
        ("Take the absolute value of the integral.", "What quantity should be estimated?"),
        ("Use |integral h|<=integral |h|.", "Which integral inequality applies?"),
        ("Since x^n>=0, the bound is at most M integral_0^1 x^n dx.", "How does the bound on f enter?"),
        ("Compute integral_0^1 x^n dx=1/(n+1).", "What is the elementary integral?"),
        ("Hence the absolute value is at most M/(n+1).", "What numerical upper bound results?"),
        ("The upper bound tends to zero.", "What is the limit of M/(n+1)?"),
        ("The squeeze theorem forces the integral to tend to zero.", "Which theorem completes the limit step?"),
        ("This proves the required limit without claiming uniform convergence of x^n.", "What false uniform-convergence shortcut was avoided?"),
    ],
}


TEACH_STEPS_ZH = {
    "C3": [
        ("反設 f 不是常數函數。", "反證法一開始應作什麼假設？"),
        ("選取 u、v，使 f(u) 與 f(v) 不同。", "哪兩個輸入可以見證 f 不是常數？"),
        ("必要時交換兩點，使 f(u)<f(v)。", "可以如何排列這兩個函數值？"),
        ("依題設，兩個端點函數值都是有理數。", "f(u) 與 f(v) 屬於哪一類數？"),
        ("在 f(u) 與 f(v) 之間選一個無理數 alpha。", "應在兩值之間選哪一類數？"),
        ("把 f 限制在以 u、v 為端點的閉區間。", "要在哪個區間使用連續性？"),
        ("由中間值定理，存在 t 使 f(t)=alpha。", "哪個定理能產生這個 t？"),
        ("但由值域假設，f(t) 必須是有理數。", "題設對 f(t) 的數類有何要求？"),
        ("這與 alpha 是無理數矛盾。", "對 f(t) 得到了哪兩個互不相容的結論？"),
        ("因此反設不成立，f 必為常數函數。", "由矛盾可得到什麼最終結論？"),
    ],
    "D3": [
        ("反設 f 有兩個相異零點 x_1、x_2。", "反證時應先假設什麼？"),
        ("不妨令 x_1<x_2。", "應如何排列兩個零點？"),
        ("考慮 f 在 [x_1,x_2] 上的限制。", "應選取哪個子區間？"),
        ("f 在這個閉區間上連續。", "哪個連續性條件會被繼承？"),
        ("f 在對應開區間內可微。", "哪個可微條件會被繼承？"),
        ("兩個端點都是零點，所以端點函數值相等。", "端點函數值滿足什麼等式？"),
        ("因此可在 [x_1,x_2] 上使用 Rolle 定理。", "現在可套用哪個定理？"),
        ("Rolle 定理給出某個 c 使 f'(c)=0。", "該定理對導數給出什麼結論？"),
        ("這與 (a,b) 內處處 f'(x) 不為零矛盾。", "矛盾了題目的哪個假設？"),
        ("所以 f 在 [a,b] 至多只有一個零點。", "最後得到什麼唯一性結論？"),
    ],
    "I3": [
        ("利用『對每個連續 g』來選擇適當的測試函數。", "哪一個量詞讓我們能自由選擇 g？"),
        ("選取 g=f。", "最合適的測試函數是什麼？"),
        ("因為 f 連續，所以 g=f 是允許的。", "為什麼這個 g 符合題設？"),
        ("題設因此變成 integral_a^b f(x)^2 dx=0。", "代入後得到哪個積分等式？"),
        ("函數 h=f^2 連續且非負。", "h 同時具有哪兩個性質？"),
        ("反設某一點 x_0 有 f(x_0) 不等於零。", "要檢驗 f 是否恆零，應作什麼反設？"),
        ("於是 h(x_0)>0。", "這對 h(x_0) 有何影響？"),
        ("由連續性，h 在 x_0 附近的一段非退化區間保持正的下界。", "連續性提供了什麼局部下界？"),
        ("這段區間使 h 的積分嚴格為正，形成矛盾。", "為什麼積分會變成正值？"),
        ("因此 [a,b] 上每一點都有 f(x)=0。", "最後可得到什麼結論？"),
    ],
    "S3": [
        ("級數在 r 收斂，所以其項 c_n r^n 趨近零。", "r 處的各項必須滿足什麼條件？"),
        ("收斂數列必有界，因此存在 M 使 |c_n r^n|<=M。", "可得到什麼一致上界？"),
        ("固定一個滿足 |x|<r 的 x。", "現在考慮哪些 x？"),
        ("令 q=|x|/r，則 0<=q<1。", "應定義哪個比較比率？"),
        ("把 |c_n x^n| 改寫成 |c_n r^n|q^n。", "第 n 項可以如何分解？"),
        ("利用上界得到 |c_n x^n|<=Mq^n。", "可推出哪個逐項不等式？"),
        ("幾何級數 sum Mq^n 收斂。", "哪一個比較級數是收斂的？"),
        ("由比較判別法，sum |c_n x^n| 收斂。", "現在可使用哪個判別法？"),
        ("所以原冪級數在此 x 絕對收斂。", "已證明哪一種收斂？"),
        ("因為 x 是任意的，結論對所有 |x|<r 成立。", "如何得到對整個內部的全稱結論？"),
    ],
    "L3": [
        ("f 在緊緻區間 [0,1] 上連續，因此有界。", "首先要使用連續函數的哪個緊緻性結果？"),
        ("選取 M，使所有 x 都有 |f(x)|<=M。", "可以固定什麼一致上界？"),
        ("先估計該積分的絕對值。", "應對哪個量作估計？"),
        ("使用 |integral h|<=integral |h|。", "應套用哪個積分不等式？"),
        ("因 x^n 非負，可將上界化為 M integral_0^1 x^n dx。", "f 的上界如何進入估計？"),
        ("計算 integral_0^1 x^n dx=1/(n+1)。", "這個初等積分等於多少？"),
        ("因此原積分絕對值不超過 M/(n+1)。", "得到哪個數值上界？"),
        ("當 n 趨近無限時，M/(n+1) 趨近零。", "這個上界的極限為何？"),
        ("由夾擠定理，原積分趨近零。", "哪個定理完成最後的極限步驟？"),
        ("這個證明不需要錯誤地宣稱 x^n 一致收斂到零。", "我們避開了哪個錯誤捷徑？"),
    ],
}
