# -*- coding: utf-8 -*-
"""主題 C 擴充對話：每題 1 條第二類錯誤變體 + 3 條關鍵步驟短對話。內容由 Claude 手寫。"""

DIALOGUES = [
    # ---- C1 ----
    {"problem_id": "C1", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我直接寫 lim f(x)=f(x_0) 因為 f 有定義，所以連續。"},
        {"role": "assistant", "content": "「有定義」不等於「極限等於函數值」。要證後者，$f(x)-f(x_0)$ 能否湊成含差商的乘積？"},
        {"role": "user", "content": "可以：[f(x)−f(x_0)]/(x−x_0)·(x−x_0)。"},
        {"role": "assistant", "content": "正是。取 $x\\to x_0$，兩因子各趨向什麼，乘積為何？"},
        {"role": "user", "content": "→f'(x_0)·0=0，所以 f(x)→f(x_0)，連續。"},
        {"role": "assistant", "content": "正確。教訓：連續要證極限＝函數值，靠差商乘積，而非「有定義」。"},
    ]},
    {"problem_id": "C1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼可以乘再除 (x−x_0)？"},
        {"role": "assistant", "content": "因為取極限 $x\\to x_0$ 時 $x\\ne x_0$。這保證分母怎樣，故可合法乘除？"},
        {"role": "user", "content": "分母 x−x_0≠0，所以能乘除。"},
        {"role": "assistant", "content": "正確，極限過程排除了等於的那點。"},
    ]},
    {"problem_id": "C1", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "連續但不可微的例子說明什麼？"},
        {"role": "assistant", "content": "$|x|$ 在 $0$ 連續卻不可微，說明可微與連續的強弱關係如何？"},
        {"role": "user", "content": "可微比連續強，可微⇒連續但反之不然。"},
        {"role": "assistant", "content": "正確，蘊含是單向的。"},
    ]},
    {"problem_id": "C1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "差商那個因子的極限為什麼是 f'(x_0)？"},
        {"role": "assistant", "content": "因為差商 $\\frac{f(x)-f(x_0)}{x-x_0}$ 的極限正是導數的定義。可微假設保證這個極限如何？"},
        {"role": "user", "content": "存在且有限，等於 f'(x_0)。"},
        {"role": "assistant", "content": "正確，有限性讓乘積趨零。"},
    ]},

    # ---- C2 ----
    {"problem_id": "C2", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我說 f(a)=f(b) 所以中間一定有水平切線，取那點就是 c。"},
        {"role": "assistant", "content": "這是圖形直覺。$c$ 須由定理導出。$f$ 連續於 $[a,b]$ 保證取得什麼，作為 $c$ 的來源？"},
        {"role": "user", "content": "取得最大值和最小值（最大值定理）。"},
        {"role": "assistant", "content": "正是。若非常數，極值落在內部，用哪個定理得 $f'(c)=0$？"},
        {"role": "user", "content": "費馬定理。"},
        {"role": "assistant", "content": "正確。教訓：Rolle 的 $c$ 靠最大值定理 + 費馬定理，而非圖形直覺。"},
    ]},
    {"problem_id": "C2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "常數情形為什麼要單獨討論？"},
        {"role": "assistant", "content": "若 $M=m$（最大等於最小），$f$ 是常數，此時 $f'$ 處處為何？"},
        {"role": "user", "content": "處處為 0，任取 c 都行。"},
        {"role": "assistant", "content": "正確，常數情形極值可能都在端點，需另述。"},
    ]},
    {"problem_id": "C2", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼非常數時極值必在內部？"},
        {"role": "assistant", "content": "由 $f(a)=f(b)$，若最大與最小都在端點則兩端值相等使 $f$ 為常數。非常數則至少一個極值在哪？"},
        {"role": "user", "content": "在內部 (a,b)。"},
        {"role": "assistant", "content": "正確，這保證能用費馬定理。"},
    ]},
    {"problem_id": "C2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Rolle 用到哪些假設？"},
        {"role": "assistant", "content": "連續（$[a,b]$）、可微（$(a,b)$）、端點值相等。連續用在最大值定理，可微用在哪？"},
        {"role": "user", "content": "用在費馬定理，保證 f'(c) 存在為 0。"},
        {"role": "assistant", "content": "正確，各假設各司其職。"},
    ]},

    # ---- C3 ----
    {"problem_id": "C3", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "均值定理我直接對 f 用 Rolle，說 f'(c)=割線斜率。"},
        {"role": "assistant", "content": "Rolle 要 $f(a)=f(b)$，但本題未必。要先造一個兩端相等的函數，怎麼從 $f$ 減去割線？"},
        {"role": "user", "content": "g(x)=f(x)−f(a)−[(f(b)−f(a))/(b−a)](x−a)，使 g(a)=g(b)=0。"},
        {"role": "assistant", "content": "正是。對 $g$ 用 Rolle，$g'(c)=0$ 展開後得什麼？"},
        {"role": "user", "content": "f'(c)=(f(b)−f(a))/(b−a)。"},
        {"role": "assistant", "content": "正確。教訓：$f$ 不滿足 Rolle 前提，須減割線造輔助函數。"},
    ]},
    {"problem_id": "C3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "g(x) 的幾何意義是什麼？"},
        {"role": "assistant", "content": "它是 $f$ 的圖形與割線在 $x$ 處的鉛直差。端點處這個差為何是 $0$？"},
        {"role": "user", "content": "因為割線在 a、b 恰好等於 f，所以差為 0。"},
        {"role": "assistant", "content": "正確，這保證了 Rolle 前提。"},
    ]},
    {"problem_id": "C3", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "g'(x) 為什麼是 f'(x)−斜率？"},
        {"role": "assistant", "content": "對 $g$ 逐項微分，割線部分 $\\frac{f(b)-f(a)}{b-a}(x-a)$ 的導數是什麼常數？"},
        {"role": "user", "content": "是 (f(b)−f(a))/(b−a)，所以 g'=f'−該斜率。"},
        {"role": "assistant", "content": "正確，割線斜率為常數。"},
    ]},
    {"problem_id": "C3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "驗證 g(b)=0 怎麼算？"},
        {"role": "assistant", "content": "代入 $x=b$：$g(b)=f(b)-f(a)-\\frac{f(b)-f(a)}{b-a}(b-a)$，後兩項相消為何？"},
        {"role": "user", "content": "後項=f(b)−f(a)，與前面相減得 0。"},
        {"role": "assistant", "content": "正確，端點值歸零。"},
    ]},

    # ---- C4 ----
    {"problem_id": "C4", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我對 f/g 用 Lagrange，直接得 (f/g)'(c)=……"},
        {"role": "assistant", "content": "$f/g$ 的導數是商法則，不會直接給出目標比值。要讓「同一個 $c$」出現，該造哪個線性組合函數？"},
        {"role": "user", "content": "h=(f(b)−f(a))g−(g(b)−g(a))f，對它用 Rolle。"},
        {"role": "assistant", "content": "正是。$h(a)=h(b)$ 後 Rolle 給 $h'(c)=0$，整理得什麼？"},
        {"role": "user", "content": "f'(c)/g'(c)=(f(b)−f(a))/(g(b)−g(a))。"},
        {"role": "assistant", "content": "正確。教訓：造線性組合 $h$，別對商 $f/g$ 硬套 Lagrange。"},
    ]},
    {"problem_id": "C4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼要保證 g(b)≠g(a)？"},
        {"role": "assistant", "content": "因為結論要除以 $g(b)-g(a)$。若它為零，Rolle 會給某點 $g'=0$，這與什麼假設矛盾？"},
        {"role": "user", "content": "與 g'≠0 矛盾，所以 g(b)≠g(a)。"},
        {"role": "assistant", "content": "正確，可除性由此保證。"},
    ]},
    {"problem_id": "C4", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Cauchy MVT 取 g(x)=x 會退化成什麼？"},
        {"role": "assistant", "content": "此時 $g(b)-g(a)=b-a$、$g'=1$，比值變成什麼熟悉的定理？"},
        {"role": "user", "content": "變成 Lagrange 均值定理。"},
        {"role": "assistant", "content": "正確，Lagrange 是 Cauchy 的特例。"},
    ]},
    {"problem_id": "C4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼分開用兩次 Lagrange 不行？"},
        {"role": "assistant", "content": "因為兩次會給出兩個不同的中間點 $c_1,c_2$。要相除必須是同一個 $c$，靠什麼保證？"},
        {"role": "user", "content": "靠單一輔助函數 h 的一次 Rolle。"},
        {"role": "assistant", "content": "正確，共用 c 是關鍵。"},
    ]},

    # ---- C5 ----
    {"problem_id": "C5", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "f'=0 在整個定義域，就算定義域分兩段，f 還是同一個常數吧？"},
        {"role": "assistant", "content": "若定義域是兩個分離區間，各段可取不同常數。均值定理要求 $x_1,x_2$ 之間都在哪裡才行？"},
        {"role": "user", "content": "要在同一個區間（連通）內，均值定理才能套。"},
        {"role": "assistant", "content": "正是。所以結論「常數」要限定在什麼上？"},
        {"role": "user", "content": "限定在區間上；不連通時各段各自為常數。"},
        {"role": "assistant", "content": "正確。教訓：「導數恆零⇒常數」需定義域為區間（連通）。"},
    ]},
    {"problem_id": "C5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "怎麼把「常數」轉成可證的東西？"},
        {"role": "assistant", "content": "轉成「任兩點函數值相等」。任取 $x_1<x_2$，用哪個定理連結函數差與導數？"},
        {"role": "user", "content": "均值定理，f(x_2)−f(x_1)=f'(c)(x_2−x_1)。"},
        {"role": "assistant", "content": "正確，這是核心橋樑。"},
    ]},
    {"problem_id": "C5", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "由此能推出不定積分「差一常數」嗎？"},
        {"role": "assistant", "content": "能。若 $f'=g'$，對 $f-g$ 用此結論，$f-g$ 是什麼？"},
        {"role": "user", "content": "(f−g)'=0 故 f−g 為常數，即 f=g+C。"},
        {"role": "assistant", "content": "正確，這正是反導數唯一性到常數的根據。"},
    ]},
    {"problem_id": "C5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 f'(c)=0 就給 f(x_2)=f(x_1)？"},
        {"role": "assistant", "content": "代入均值定理式 $f(x_2)-f(x_1)=f'(c)(x_2-x_1)$，$f'(c)=0$ 使右邊為何？"},
        {"role": "user", "content": "右邊=0，所以 f(x_2)=f(x_1)。"},
        {"role": "assistant", "content": "正確，兩點值相等。"},
    ]},

    # ---- C6 ----
    {"problem_id": "C6", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "f'≥0 就嚴格遞增吧？"},
        {"role": "assistant", "content": "$f'\\ge0$ 只給非嚴格遞增。$f(x)=x^3$ 有 $f'(0)=0$ 卻仍嚴格遞增，但一般 $f'\\ge0$ 能保證嚴格嗎？"},
        {"role": "user", "content": "不能，常數函數 f'=0≥0 但不嚴格遞增。要嚴格需 f'>0。"},
        {"role": "assistant", "content": "正是。本題假設 $f'>0$，均值定理給 $f(x_2)-f(x_1)$ 的符號為何？"},
        {"role": "user", "content": ">0，所以嚴格遞增。"},
        {"role": "assistant", "content": "正確。教訓：$f'>0$ 才保證嚴格，$f'\\ge0$ 只給非嚴格。"},
    ]},
    {"problem_id": "C6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼要用均值定理而不是直接說「斜率正」？"},
        {"role": "assistant", "content": "「斜率正」是局部資訊，均值定理才能連到「任兩點大小」。它把 $f(x_2)-f(x_1)$ 寫成什麼？"},
        {"role": "user", "content": "寫成 f'(c)(x_2−x_1)，把局部導數轉成整體差。"},
        {"role": "assistant", "content": "正確，這是局部到整體的橋樑。"},
    ]},
    {"problem_id": "C6", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "逆命題「嚴格遞增⇒f'>0」對嗎？"},
        {"role": "assistant", "content": "不對。哪個嚴格遞增函數在某點導數為零，作為反例？"},
        {"role": "user", "content": "x³，f'(0)=0，所以只能得 f'≥0。"},
        {"role": "assistant", "content": "正確，單調與導數正負非等價。"},
    ]},
    {"problem_id": "C6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "c 一定存在嗎？"},
        {"role": "assistant", "content": "在 $x_1<x_2$ 的閉區間上 $f$ 連續、開區間可微，均值定理保證 $c$ 落在哪？"},
        {"role": "user", "content": "落在 (x_1,x_2) 內，存在。"},
        {"role": "assistant", "content": "正確，前提滿足即保證存在。"},
    ]},

    # ---- C7 ----
    {"problem_id": "C7", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "端點取極大時也一定 f'=0 吧？"},
        {"role": "assistant", "content": "端點只有單側，只能得單側導數的符號。費馬定理要求極值點是什麼樣的點？"},
        {"role": "user", "content": "內部點，才有左右兩側夾出 f'=0。"},
        {"role": "assistant", "content": "正是。內部點時左導數 $\\ge0$、右導數 $\\le0$，可微使兩者相等給什麼？"},
        {"role": "user", "content": "f'(c)=0。"},
        {"role": "assistant", "content": "正確。教訓：費馬定理限「內部點」，端點極值未必導數為零。"},
    ]},
    {"problem_id": "C7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "右導數為什麼 ≤0？"},
        {"role": "assistant", "content": "由 $f(c+h)\\le f(c)$，$h\\to0^+$ 時差商分子 $\\le0$、分母 $>0$，故差商符號為何？"},
        {"role": "user", "content": "≤0，所以右導數 ≤0。"},
        {"role": "assistant", "content": "正確，符號由分子分母決定。"},
    ]},
    {"problem_id": "C7", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "f'(c)=0 是極值的充分條件嗎？"},
        {"role": "assistant", "content": "不是。$x^3$ 在 $0$ 的 $f'(0)=0$ 卻非極值，說明 $f'(c)=0$ 只是什麼條件？"},
        {"role": "user", "content": "必要非充分條件。"},
        {"role": "assistant", "content": "正確，臨界點未必是極值。"},
    ]},
    {"problem_id": "C7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼要同時看左右導數？"},
        {"role": "assistant", "content": "因為右導數給 $\\le0$、左導數給 $\\ge0$。可微使兩者相等，唯一同時滿足的值是什麼？"},
        {"role": "user", "content": "0。"},
        {"role": "assistant", "content": "正確，左右夾出零。"},
    ]},

    # ---- C8 ----
    {"problem_id": "C8", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我用 |f(x)−f(y)|=|∫_y^x f'|≤M|x−y|，但題目只說可微。"},
        {"role": "assistant", "content": "積分路線需 $f'$ 可積（如連續）這個額外前提。只靠可微，用哪個定理直接得同結論？"},
        {"role": "user", "content": "均值定理，f(x)−f(y)=f'(c)(x−y)。"},
        {"role": "assistant", "content": "正是。取絕對值並用 $|f'(c)|\\le M$ 得什麼？"},
        {"role": "user", "content": "|f(x)−f(y)|≤M|x−y|。"},
        {"role": "assistant", "content": "正確。教訓：只有可微時，均值定理前提最少、最穩。"},
    ]},
    {"problem_id": "C8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "Lipschitz 常數就是 M 嗎？"},
        {"role": "assistant", "content": "是。由 $|f(x)-f(y)|\\le M|x-y|$，這裡的 $M$ 正是導數界。它同時保證什麼較弱的連續性？"},
        {"role": "user", "content": "保證一致連續（取 δ=ε/M）。"},
        {"role": "assistant", "content": "正確，Lipschitz⇒一致連續。"},
    ]},
    {"problem_id": "C8", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Lipschitz 與一致連續的強弱關係？"},
        {"role": "assistant", "content": "已知 Lipschitz $\\Rightarrow$ 一致連續；而 $\\sqrt{x}$ 一致連續卻非 Lipschitz，這說明兩者的強弱關係為何？"},
        {"role": "user", "content": "說明 Lipschitz 嚴格更強。"},
        {"role": "assistant", "content": "正確，蘊含單向。"},
    ]},
    {"problem_id": "C8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "x=y 的情形要處理嗎？"},
        {"role": "assistant", "content": "要提一句。$x=y$ 時不等式兩邊各為多少，是否成立？"},
        {"role": "user", "content": "兩邊都 0，成立。"},
        {"role": "assistant", "content": "正確，邊界情形也涵蓋。"},
    ]},

    # ---- C9 ----
    {"problem_id": "C9", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我用 |sin x−sin y|≤|x|+|y|，因為各自 |sin|≤1……不對好像太鬆。"},
        {"role": "assistant", "content": "那個界太鬆且方向不對。改把 $\\sin$ 看成某函數在兩點的差、套用均值定理，其導數界是多少？"},
        {"role": "user", "content": "用均值定理，f=sin，f'=cos，|cos|≤1。"},
        {"role": "assistant", "content": "正是。$\\sin x-\\sin y=\\cos c(x-y)$，取絕對值得什麼？"},
        {"role": "user", "content": "|sin x−sin y|≤|x−y|。"},
        {"role": "assistant", "content": "正確。教訓：用均值定理與導數界，得到緊的 Lipschitz 常數 1。"},
    ]},
    {"problem_id": "C9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "這題和 Lipschitz 那題有關嗎？"},
        {"role": "assistant", "content": "有，這是 $|f'|\\le M$ 的特例。$\\sin$ 的導數界 $M$ 是多少，故 Lipschitz 常數為何？"},
        {"role": "user", "content": "M=1，常數為 1。"},
        {"role": "assistant", "content": "正確，直接套 C8 的結論。"},
    ]},
    {"problem_id": "C9", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "常數 1 是最佳的嗎？"},
        {"role": "assistant", "content": "考慮 $x,y\\to0$ 時 $\\frac{|\\sin x-\\sin y|}{|x-y|}$ 逼近 $|\\cos0|$，也就是多少？"},
        {"role": "user", "content": "逼近 1，所以常數 1 是最佳、不能更小。"},
        {"role": "assistant", "content": "正確，導數在 0 的值決定最佳常數。"},
    ]},
    {"problem_id": "C9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "c 是哪裡來的？"},
        {"role": "assistant", "content": "由均值定理，$c$ 是介於 $x,y$ 之間的某點。我們需要知道 $c$ 的確切位置嗎？"},
        {"role": "user", "content": "不需要，只要 |cos c|≤1 就夠。"},
        {"role": "assistant", "content": "正確，界不依賴 c 的位置。"},
    ]},

    # ---- C10 ----
    {"problem_id": "C10", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我用 ln(1+x)≈x（泰勒一階），所以 ln(1+x)<x。"},
        {"role": "assistant", "content": "近似不是嚴格不等式，且沒給下界。用均值定理可一次得到嚴格的上下界。$\\ln(1+t)$ 在 $[0,x]$ 給什麼等式？"},
        {"role": "user", "content": "ln(1+x)=x/(1+ξ)，ξ∈(0,x)。"},
        {"role": "assistant", "content": "正是。由 $0<\\xi<x$ 夾出 $\\frac1{1+\\xi}$ 的範圍，乘 $x$ 得什麼？"},
        {"role": "user", "content": "x/(1+x)<ln(1+x)<x。"},
        {"role": "assistant", "content": "正確。教訓：用均值定理等式可得嚴格上下界，勝過近似。"},
    ]},
    {"problem_id": "C10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼一個等式能同時給上下界？"},
        {"role": "assistant", "content": "因為 $\\ln(1+x)=\\frac{x}{1+\\xi}$ 中 $\\xi$ 有範圍 $(0,x)$。$\\frac1{1+\\xi}$ 因此落在哪兩個值之間？"},
        {"role": "user", "content": "介於 1/(1+x) 與 1 之間，乘 x 就給雙邊界。"},
        {"role": "assistant", "content": "正確，$\\xi$ 的範圍轉成上下界。"},
    ]},
    {"problem_id": "C10", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "對 x∈(−1,0) 論證要注意什麼？"},
        {"role": "assistant", "content": "$x<0$ 時乘以負數不等號要反向，且區間變 $[x,0]$。這會使哪兩式的大小順序調換？"},
        {"role": "user", "content": "x/(1+x) 與 x 的順序調換，要重新排。"},
        {"role": "assistant", "content": "正確，負區間乘法變號是陷阱。"},
    ]},
    {"problem_id": "C10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "ln(1+x)−ln1 為什麼等於 ln(1+x)？"},
        {"role": "assistant", "content": "因為 $\\ln1=0$。均值定理用在 $[0,x]$，左端點值 $f(0)=\\ln(1+0)$ 是多少？"},
        {"role": "user", "content": "=ln1=0，所以差就是 ln(1+x)。"},
        {"role": "assistant", "content": "正確，左端點歸零。"},
    ]},
]
