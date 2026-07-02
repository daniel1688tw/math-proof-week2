# -*- coding: utf-8 -*-
"""主題 D 擴充對話：每題 1 條第二類錯誤變體 + 3 條關鍵步驟短對話。內容由 Claude 手寫。"""

DIALOGUES = [
    # ---- D1 ----
    {"problem_id": "D1", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "∫f=0 且 f≥0，那 f 的最大值一定是 0，所以 f≡0。"},
        {"role": "assistant", "content": "「最大值是 0」正是要證的部分，不能先假設。改用反證：若某點 $f(x_0)>0$，連續性讓附近如何？"},
        {"role": "user", "content": "附近一段 f>f(x_0)/2>0。"},
        {"role": "assistant", "content": "正是。因 $f\\ge0$，這段積分給 $\\int f$ 什麼正下界，導致矛盾？"},
        {"role": "user", "content": "≥(f(x_0)/2)(d−c)>0，與 ∫f=0 矛盾。"},
        {"role": "assistant", "content": "正確。教訓：用連續性把單點正值放大成一段，才推出正積分。"},
    ]},
    {"problem_id": "D1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼可以找到一整段 f>f(x_0)/2？"},
        {"role": "assistant", "content": "由連續性，取 $\\varepsilon=f(x_0)/2$，在 $x_0$ 附近 $f$ 與 $f(x_0)$ 的差小於它。故該段 $f$ 大於什麼？"},
        {"role": "user", "content": "大於 f(x_0)−ε=f(x_0)/2。"},
        {"role": "assistant", "content": "正確，連續性提供這一整段。"},
    ]},
    {"problem_id": "D1", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "拿掉「連續」會怎樣？"},
        {"role": "assistant", "content": "會有反例。哪種 $f\\ge0$、$\\int=0$ 卻不恆零，只在零測集非零？"},
        {"role": "user", "content": "單點取 1、其餘為 0，積分仍 0 但不恆 0。"},
        {"role": "assistant", "content": "正確，連續性排除這種情形。"},
    ]},
    {"problem_id": "D1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "f≥0 這個條件用在哪？"},
        {"role": "assistant", "content": "用在把整段的正積分下界推到整個 $\\int_a^b f$。因為其餘部分 $f\\ge0$，整體積分至少多少？"},
        {"role": "user", "content": "至少不小於那一段的積分，所以 >0。"},
        {"role": "assistant", "content": "正確，非負性保證不會被別處抵消。"},
    ]},

    # ---- D2 ----
    {"problem_id": "D2", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "F(x)=∫f，我說 F'(x)=f(x) 因為積分與微分互逆。"},
        {"role": "assistant", "content": "「互逆」正是這條定理要建立的。要從導數定義出發，$\\frac{F(x+h)-F(x)}{h}$ 等於什麼積分？"},
        {"role": "user", "content": "(1/h)∫_x^{x+h} f。"},
        {"role": "assistant", "content": "正是。減去 $f(x)$ 後用連續性，差被什麼上界壓住並趨零？"},
        {"role": "user", "content": "被 sup_{|t−x|≤|h|}|f(t)−f(x)| 壓住，h→0 趨 0。"},
        {"role": "assistant", "content": "正確。教訓：互逆性須證，靠差商 + 連續性估計。"},
    ]},
    {"problem_id": "D2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼把 f(x) 寫成 (1/h)∫_x^{x+h} f(x) dt？"},
        {"role": "assistant", "content": "因為 $f(x)$ 是常數，對 $t$ 積分後除以 $h$ 剛好還原。這樣才能和差商合併成什麼形式？"},
        {"role": "user", "content": "合併成 (1/h)∫(f(t)−f(x))dt。"},
        {"role": "assistant", "content": "正確，湊出同一積分好估計。"},
    ]},
    {"problem_id": "D2", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "這裡只需要 f 在該點連續嗎？"},
        {"role": "assistant", "content": "是。若 $f$ 僅可積但在 $x$ 不連續，$F$ 在該點還一定可微且 $F'=f$ 嗎？"},
        {"role": "user", "content": "不一定，FTC-1 的逐點可微需要該點連續。"},
        {"role": "assistant", "content": "正確，連續性是逐點必要條件。"},
    ]},
    {"problem_id": "D2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼那個 sup 會趨於 0？"},
        {"role": "assistant", "content": "當 $h\\to0$，$t$ 被限制在 $x$ 的 $|h|$ 鄰域內。由連續性，$|f(t)-f(x)|$ 的上確界趨向什麼？"},
        {"role": "user", "content": "趨向 0。"},
        {"role": "assistant", "content": "正確，這逼出 F'(x)=f(x)。"},
    ]},

    # ---- D3 ----
    {"problem_id": "D3", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "積分中值定理的 c 我取端點 a，f(a)(b−a) 就是積分吧？"},
        {"role": "assistant", "content": "端點值未必等於平均值。$c$ 要由論證得出。先問：$\\frac1{b-a}\\int f$ 落在 $f$ 的哪個值域範圍？"},
        {"role": "user", "content": "落在 [m,M]（最小到最大值）內。"},
        {"role": "assistant", "content": "正是。連續函數取遍 $[m,M]$，用哪個定理保證有 $c$ 使 $f(c)$ 等於平均值？"},
        {"role": "user", "content": "介值定理。c 存在但位置未定。"},
        {"role": "assistant", "content": "正確。教訓：$c$ 由 IVT 保證存在，不能指定為端點或中點。"},
    ]},
    {"problem_id": "D3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 m(b−a)≤∫f≤M(b−a)？"},
        {"role": "assistant", "content": "由 $m\\le f\\le M$ 逐點成立，對其積分（保序）在長度 $b-a$ 上得到什麼？"},
        {"role": "user", "content": "得 m(b−a)≤∫f≤M(b−a)。"},
        {"role": "assistant", "content": "正確，常數的積分就是常數乘長度。"},
    ]},
    {"problem_id": "D3", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "此定理用到 f 連續幾次？"},
        {"role": "assistant", "content": "兩次。一次取得 $m,M$（最大值定理），一次取遍中間值。後者是哪個定理？"},
        {"role": "user", "content": "介值定理。"},
        {"role": "assistant", "content": "正確，連續性雙重角色。"},
    ]},
    {"problem_id": "D3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "平均值 μ 是什麼？"},
        {"role": "assistant", "content": "$\\mu=\\frac1{b-a}\\int_a^b f$。它必落在哪個閉區間，才能用 IVT 取到？"},
        {"role": "user", "content": "落在 [m,M]。"},
        {"role": "assistant", "content": "正確，這保證 f(c)=μ 有解。"},
    ]},

    # ---- D4 ----
    {"problem_id": "D4", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "f≤g，兩邊積分不等號自動保持，這是積分的性質嘛。"},
        {"role": "assistant", "content": "這正是要證的性質。回到定義：令 $h=g-f\\ge0$，它的下和有什麼符號，故 $\\int h$ 如何？"},
        {"role": "user", "content": "下和≥0（每個 inf h≥0），所以 ∫h≥0。"},
        {"role": "assistant", "content": "正是。由線性 $\\int g-\\int f=\\int h$，得什麼？"},
        {"role": "user", "content": "≥0，即 ∫f≤∫g。"},
        {"role": "assistant", "content": "正確。教訓：保序性要由「非負積分＋線性」推出。"},
    ]},
    {"problem_id": "D4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼非負函數的積分非負？"},
        {"role": "assistant", "content": "因為每個子區間的 $m_i=\\inf h\\ge0$，故任一下和 $\\sum m_i\\Delta x_i\\ge0$。積分是下和的什麼？"},
        {"role": "user", "content": "是下和的上確界，故也≥0。"},
        {"role": "assistant", "content": "正確，非負性由下和傳到積分。"},
    ]},
    {"problem_id": "D4", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "f<g 嚴格時 ∫f<∫g 嚴格成立嗎？"},
        {"role": "assistant", "content": "不一定，除非 $g-f$ 在某段連續且為正。單點嚴格不夠，為什麼？"},
        {"role": "user", "content": "單點不影響積分，要一整段正才使積分嚴格。"},
        {"role": "assistant", "content": "正確，這與 D1 的道理相通。"},
    ]},
    {"problem_id": "D4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼要令 h=g−f？"},
        {"role": "assistant", "content": "因為把兩函數比較轉成「單一非負函數的積分符號」較好處理。$h\\ge0$ 是由什麼給的？"},
        {"role": "user", "content": "由 f≤g 給的。"},
        {"role": "assistant", "content": "正確，移項化簡是關鍵一步。"},
    ]},

    # ---- D5 ----
    {"problem_id": "D5", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "|∫f|≤∫|f|，因為絕對值加起來一定更大，直接寫。"},
        {"role": "assistant", "content": "直覺對，但要嚴謹。從哪個逐點不等式出發，再用積分保序？"},
        {"role": "user", "content": "−|f|≤f≤|f|，積分得 −∫|f|≤∫f≤∫|f|。"},
        {"role": "assistant", "content": "正是。$-A\\le\\int f\\le A$ 等價於什麼絕對值不等式？"},
        {"role": "user", "content": "|∫f|≤A=∫|f|。"},
        {"role": "assistant", "content": "正確。教訓：逐點夾 + 保序，比含糊的直覺嚴謹。"},
    ]},
    {"problem_id": "D5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "−|f|≤f≤|f| 為什麼成立？"},
        {"role": "assistant", "content": "這是實數絕對值的基本性質，對每個 $x$ 都成立。$f(x)$ 一定介於 $\\pm|f(x)|$ 之間嗎？"},
        {"role": "user", "content": "是，任何實數都介於它的正負絕對值之間。"},
        {"role": "assistant", "content": "正確，逐點成立才能積分。"},
    ]},
    {"problem_id": "D5", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "f 可積能保證 |f| 可積嗎？"},
        {"role": "assistant", "content": "能。因為取絕對值不會增大子區間的振幅 $M_i-m_i$。故 $\\int|f|$ 如何？"},
        {"role": "user", "content": "有定義（可積），所以右邊成立。"},
        {"role": "assistant", "content": "正確，你補上了可積性前提。"},
    ]},
    {"problem_id": "D5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "這題和三角不等式有關嗎？"},
        {"role": "assistant", "content": "有，這是三角不等式的積分版。離散的 $|\\sum a_i|\\le\\sum|a_i|$ 對應連續的什麼？"},
        {"role": "user", "content": "對應 |∫f|≤∫|f|。"},
        {"role": "assistant", "content": "正確，離散到連續的類比。"},
    ]},

    # ---- D6 ----
    {"problem_id": "D6", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "∫_a^b f=F(b)−F(a)，因為 F 是反導數，代入就好。"},
        {"role": "assistant", "content": "這是要證的公式。先用 FTC-1 造 $G(x)=\\int_a^x f$，它與 $F$ 的導數關係如何？"},
        {"role": "user", "content": "G'=f=F'，所以 G−F 是常數。"},
        {"role": "assistant", "content": "正是。由 $G(a)=0$ 定常數，代 $x=b$ 得什麼？"},
        {"role": "user", "content": "∫_a^b f=G(b)=F(b)−F(a)。"},
        {"role": "assistant", "content": "正確。教訓：用「導數相等差常數」把積分定義的反導數與 F 連起來。"},
    ]},
    {"problem_id": "D6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "常數 C 怎麼定出來？"},
        {"role": "assistant", "content": "代入 $x=a$：$G(a)-F(a)=C$。$G(a)=\\int_a^a f$ 等於多少，故 $C$ 是什麼？"},
        {"role": "user", "content": "G(a)=0，所以 C=−F(a)。"},
        {"role": "assistant", "content": "正確，端點定常數。"},
    ]},
    {"problem_id": "D6", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "f 僅可積（不連續）時第二部分怎麼證？"},
        {"role": "assistant", "content": "改用分割，對每個子區間對 $F$ 用均值定理，得 $\\sum f(c_i)\\Delta x_i=F(b)-F(a)$，再取極限。這個和趨向什麼？"},
        {"role": "user", "content": "趨向 ∫_a^b f，故公式成立。"},
        {"role": "assistant", "content": "正確，這是不依賴 FTC-1 的一般證法。"},
    ]},
    {"problem_id": "D6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 G−F 是常數？"},
        {"role": "assistant", "content": "因為 $(G-F)'=G'-F'=f-f=0$。導數恆零的函數在區間上是什麼？"},
        {"role": "user", "content": "是常數。"},
        {"role": "assistant", "content": "正確，這用到 C5 的結論。"},
    ]},

    # ---- D7 ----
    {"problem_id": "D7", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "連續函數逐點連續，每段波動小，所以上下和差小、可積。"},
        {"role": "assistant", "content": "逐點連續給的 $\\delta$ 隨點變，無法讓所有子區間同時小。要升級成什麼連續性？"},
        {"role": "user", "content": "一致連續（Heine-Cantor），提供通用 δ。"},
        {"role": "assistant", "content": "正是。取分割細於 $\\delta$，$U-L=\\sum(M_i-m_i)\\Delta x_i$ 被壓到多少？"},
        {"role": "user", "content": "≤ε，故可積。"},
        {"role": "assistant", "content": "正確。教訓：可積性需一致連續給通用 $\\delta$。"},
    ]},
    {"problem_id": "D7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "可積的判準是什麼？"},
        {"role": "assistant", "content": "黎曼可積準則：存在分割使上下和之差任意小。本題要證 $U-L$ 能小於什麼？"},
        {"role": "user", "content": "小於任意 ε。"},
        {"role": "assistant", "content": "正確，這就是可積的充要條件之一。"},
    ]},
    {"problem_id": "D7", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "M_i、m_i 為何一定被取到？"},
        {"role": "assistant", "content": "因為每個閉子區間上 $f$ 連續，用哪個定理保證最大最小被達到？"},
        {"role": "user", "content": "最大值定理。"},
        {"role": "assistant", "content": "正確，這讓 M_i−m_i 有意義。"},
    ]},
    {"problem_id": "D7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼每段 M_i−m_i≤ε/(b−a)？"},
        {"role": "assistant", "content": "因為子區間長 $<\\delta$，區間內任兩點距離 $<\\delta$。由一致連續，函數值差小於什麼？"},
        {"role": "user", "content": "小於 ε/(b−a)，故最大最小之差也被這壓住。"},
        {"role": "assistant", "content": "正確，通用 δ 讓每段同時受控。"},
    ]},

    # ---- D8 ----
    {"problem_id": "D8", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我算出 ∫_0^1 1/(1+x²)=arctan1=π/4，但題目只要界，我不確定要不要算出來。"},
        {"role": "assistant", "content": "算出精確值當然也對，但題目想練「估計」。若不積分，先夾被積函數：$\\frac1{1+x^2}$ 在 $[0,1]$ 落在哪個範圍？"},
        {"role": "user", "content": "1/2≤1/(1+x²)≤1，積分得 1/2≤∫≤1。"},
        {"role": "assistant", "content": "正是，且 $\\pi/4\\approx0.785$ 確實落在其中。"},
        {"role": "user", "content": "懂了，估計法不必算出積分本身。"},
        {"role": "assistant", "content": "正確。教訓：估界只需夾被積函數再乘區間長。"},
    ]},
    {"problem_id": "D8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "1≤1+x²≤2 取倒數為什麼變 1/2≤…≤1？"},
        {"role": "assistant", "content": "同號取倒數時不等號反向。分母越大，倒數越小，故 $1+x^2$ 最大 $2$ 對應倒數的什麼？"},
        {"role": "user", "content": "對應最小值 1/2。"},
        {"role": "assistant", "content": "正確，方向必須反轉。"},
    ]},
    {"problem_id": "D8", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "怎麼把上界收得更接近 π/4？"},
        {"role": "assistant", "content": "把 $[0,1]$ 細分多段、各段用該段的 max/min 估。分越細，上下界如何？"},
        {"role": "user", "content": "越接近真值 π/4。"},
        {"role": "assistant", "content": "正確，這正是上下和加細的精神。"},
    ]},
    {"problem_id": "D8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼乘的是 1（區間長）？"},
        {"role": "assistant", "content": "因為積分區間 $[0,1]$ 的長度是 $1$。常數界對長度 $L$ 的區間積分得常數乘 $L$，這裡 $L$ 是多少？"},
        {"role": "user", "content": "L=1。"},
        {"role": "assistant", "content": "正確，故界直接是常數本身。"},
    ]},

    # ---- D9 ----
    {"problem_id": "D9", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "p=2 時收斂，所以我猜所有 p 都收斂。"},
        {"role": "assistant", "content": "單一個例不能推及全部。關鍵看 $R^{1-p}$ 的極限。$p<1$ 時 $1-p>0$，$R^{1-p}$ 趨向什麼？"},
        {"role": "user", "content": "→∞，所以 p<1 發散。加上 p=1 是 ln R 也發散。"},
        {"role": "assistant", "content": "正是。故收斂條件是什麼？"},
        {"role": "user", "content": "p>1。"},
        {"role": "assistant", "content": "正確。教訓：要對指數 $1-p$ 的正負全面討論，勿以單例概全。"},
    ]},
    {"problem_id": "D9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "廣義積分收斂的定義是什麼？"},
        {"role": "assistant", "content": "先算到有限上限 $R$，再取 $R\\to\\infty$。極限存在且有限就叫什麼？"},
        {"role": "user", "content": "叫收斂。"},
        {"role": "assistant", "content": "正確，這是判斷的出發點。"},
    ]},
    {"problem_id": "D9", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 p=1 要單獨算？"},
        {"role": "assistant", "content": "因為一般反導數 $\\frac{x^{1-p}}{1-p}$ 在 $p=1$ 分母為零失效。$p=1$ 時反導數改成什麼？"},
        {"role": "user", "content": "ln x，∫_1^R dx/x=ln R→∞。"},
        {"role": "assistant", "content": "正確，對數情形必須單列。"},
    ]},
    {"problem_id": "D9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "這跟 ∑1/n^p 的收斂門檻一樣是巧合嗎？"},
        {"role": "assistant", "content": "不是巧合。哪個判別法把正遞減函數的級數與其積分綁在一起？"},
        {"role": "user", "content": "積分判別法，所以門檻都是 p>1。"},
        {"role": "assistant", "content": "正確，兩者本質相連。"},
    ]},

    # ---- D10 ----
    {"problem_id": "D10", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我對 ∫fg 直接用 |fg|≤(f²+g²)/2 積分，得 ∫fg≤(∫f²+∫g²)/2，這是 Cauchy-Schwarz 嗎？"},
        {"role": "assistant", "content": "那是 AM-GM，給的是不同（較弱）的界。Cauchy-Schwarz 要造哪個含參數 $\\lambda$ 的非負量？"},
        {"role": "user", "content": "∫(f−λg)²≥0，展開成 λ 的二次式。"},
        {"role": "assistant", "content": "正是。恆非負二次式的判別式該滿足什麼，整理得目標？"},
        {"role": "user", "content": "判別式≤0，得 (∫fg)²≤∫f²·∫g²。"},
        {"role": "assistant", "content": "正確。教訓：Cauchy-Schwarz 靠參數化非負二次式 + 判別式，而非 AM-GM。"},
    ]},
    {"problem_id": "D10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 ∫(f−λg)²≥0？"},
        {"role": "assistant", "content": "因為被積分的是平方，逐點非負。非負函數的積分是什麼符號？"},
        {"role": "user", "content": "非負，所以整個積分≥0。"},
        {"role": "assistant", "content": "正確，這是整個證法的起點。"},
    ]},
    {"problem_id": "D10", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "判別式該用 <0 還是 ≤0？"},
        {"role": "assistant", "content": "二次式是恆「$\\ge0$」而非「無實根」，可能有重根（等號）。故判別式用哪個？"},
        {"role": "user", "content": "用 ≤0，才涵蓋 f、g 成比例的等號情形。"},
        {"role": "assistant", "content": "正確，$<0$ 會漏掉等號。"},
    ]},
    {"problem_id": "D10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "∫g²=0 這個特殊情形怎麼辦？"},
        {"role": "assistant", "content": "此時二次項消失、不再是二次式。由 D1，$g^2\\ge0$ 連續且積分為 0 推出 $g$ 是什麼？"},
        {"role": "user", "content": "g≡0，於是兩邊都 0，不等式仍成立。"},
        {"role": "assistant", "content": "正確，退化情形另外處理。"},
    ]},
]
