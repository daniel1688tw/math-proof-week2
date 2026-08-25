# -*- coding: utf-8 -*-
"""主題 D 核心對話（D1-D10 × 3 Persona）。內容由 Claude 手寫。"""

DIALOGUES = [
    # ===== D1: f≥0 continuous, ∫=0 ⇒ f≡0 =====
    {"problem_id": "D1", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "積分是 0 就說 f 恆為 0，可是積分為 0 感覺很多函數都行，怎麼證?"},
        {"role": "assistant", "content": "關鍵是 $f\\ge0$ 且連續。用反證：假設某點 $f(x_0)>0$，連續性會讓 $f$ 在 $x_0$ 附近怎麼樣?"},
        {"role": "user", "content": "連續性讓 x_0 附近一小段 f 都大於某個正數，比如 >f(x_0)/2。"},
        {"role": "assistant", "content": "很好，設那段是 $[c,d]$。因 $f\\ge0$，$\\int_a^b f$ 至少大於在 $[c,d]$ 上的積分，能給個下界嗎?"},
        {"role": "user", "content": "∫_a^b f ≥ ∫_c^d f ≥ (f(x_0)/2)(d−c)>0。"},
        {"role": "assistant", "content": "正是，這和 $\\int_a^b f=0$ 起了什麼衝突?"},
        {"role": "user", "content": "得到正數卻應等於 0，矛盾。所以沒有這種 x_0，f 恆為 0。"},
        {"role": "assistant", "content": "完全正確。核心是「連續性把單點正值放大成一整段正值，再用非負性壓出正積分」。"},
    ]},
    {"problem_id": "D1", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "∫f=0 所以 f 的平均是 0，平均 0 就代表 f=0。"},
        {"role": "assistant", "content": "平均為 0 一般只逼出「有正有負」，這裡靠哪個額外假設排除負值的可能?"},
        {"role": "user", "content": "題目給 f≥0，所以不會有負值抵消。那如果某點 >0…"},
        {"role": "assistant", "content": "正是關鍵。若某點 $f(x_0)>0$，用連續性在附近造一段 $f>\\frac{f(x_0)}2$，積分下界會是什麼?"},
        {"role": "user", "content": "≥(f(x_0)/2)(d−c)>0，跟 ∫f=0 矛盾，所以 f≡0。"},
        {"role": "assistant", "content": "正確。教訓：非負 + 連續缺一不可，少了任一個都能找到 $\\int=0$ 卻非零的例子。"},
    ]},
    {"problem_id": "D1", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "反證：f(x_0)>0，連續性給鄰域 [c,d] 上 f>f(x_0)/2，故 ∫≥(f(x_0)/2)(d−c)>0 矛盾。"},
        {"role": "assistant", "content": "完整。若把「連續」拿掉，能否舉出 $f\\ge0$、$\\int=0$ 卻不恆為零的反例?"},
        {"role": "user", "content": "可以，f 在單點取 1、其餘為 0，積分仍是 0 但不恆為 0。所以連續性不可少。"},
        {"role": "assistant", "content": "正確，你點出連續性正是排除「零測集上非零」的關鍵。分析到位。"},
    ]},

    # ===== D2: FTC part 1 =====
    {"problem_id": "D2", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "微積分基本定理第一部分，F(x)=∫f 的導數是 f，我不知道怎麼從定義證。"},
        {"role": "assistant", "content": "從導數定義出發。$\\frac{F(x+h)-F(x)}{h}$ 用積分可加性可寫成什麼形式?"},
        {"role": "user", "content": "= (1/h)∫_x^{x+h} f(t) dt。"},
        {"role": "assistant", "content": "很好。我們想證它趨近 $f(x)$。把 $f(x)$ 也寫成 $\\frac1h\\int_x^{x+h}f(x)\\,dt$，兩者相減得到什麼積分?"},
        {"role": "user", "content": "差 = (1/h)∫_x^{x+h} (f(t)−f(x)) dt。"},
        {"role": "assistant", "content": "正是。取絕對值後，用 $f$ 在 $x$ 的連續性，這個差能被什麼量壓住並趨於 0?"},
        {"role": "user", "content": "被 sup_{|t−x|≤|h|}|f(t)−f(x)| 壓住，h→0 時因連續性趨 0，所以 F'(x)=f(x)。"},
        {"role": "assistant", "content": "完全正確。訣竅是「把常數 $f(x)$ 塞進積分、用連續性控制被積函數的波動」。"},
    ]},
    {"problem_id": "D2", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "F(x)=∫f 就是 f 的反導數，所以 F'=f，這不是定義嗎?"},
        {"role": "assistant", "content": "「反導數」正是這條定理要建立的結論，不能當定義用。要從導數極限著手：$\\frac{F(x+h)-F(x)}h$ 等於什麼積分?"},
        {"role": "user", "content": "(1/h)∫_x^{x+h} f dt。"},
        {"role": "assistant", "content": "很好。減去 $f(x)$ 並用連續性，如何說明它趨近 $f(x)$?"},
        {"role": "user", "content": "差=(1/h)∫(f(t)−f(x))dt，絕對值≤附近 |f(t)−f(x)| 的上確界，h→0 因連續趨 0。"},
        {"role": "assistant", "content": "正確。教訓：FTC 是要「證明」積分與微分互逆，不能把結論當定義。"},
    ]},
    {"problem_id": "D2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "差商 (1/h)∫_x^{x+h}(f(t)−f(x))dt，絕對值≤sup|f(t)−f(x)|→0（連續），故 F'=f。"},
        {"role": "assistant", "content": "完全正確。這裡只用到 $f$ 在該點連續；若 $f$ 僅可積但在 $x$ 不連續，結論會怎樣?"},
        {"role": "user", "content": "則 F 在 x 未必可微，或 F'(x)≠f(x)；FTC-1 的可微性正需要該點連續。"},
        {"role": "assistant", "content": "正確，你精準指出連續性是逐點成立的必要條件。理解很深。"},
    ]},

    # ===== D3: integral mean value =====
    {"problem_id": "D3", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "積分中值定理要找 c 使 ∫f=f(c)(b−a)，我不知道 c 怎麼來。"},
        {"role": "assistant", "content": "先把積分夾住。$f$ 在 $[a,b]$ 連續，取得最小 $m$、最大 $M$，則 $\\int_a^b f$ 落在哪個範圍?"},
        {"role": "user", "content": "m(b−a) ≤ ∫f ≤ M(b−a)。"},
        {"role": "assistant", "content": "很好。除以 $(b-a)$ 得平均值 $\\mu=\\frac1{b-a}\\int f$，它落在哪個區間?"},
        {"role": "user", "content": "μ∈[m,M]。"},
        {"role": "assistant", "content": "正是。連續函數能取遍 $[m,M]$ 之間的值，靠哪個定理保證存在 $c$ 使 $f(c)=\\mu$?"},
        {"role": "user", "content": "介值定理，存在 c 使 f(c)=μ，即 ∫f=f(c)(b−a)。"},
        {"role": "assistant", "content": "完全正確。積分中值定理＝「用 m,M 夾住平均值 + 介值定理取到它」。"},
    ]},
    {"problem_id": "D3", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "取 c 是 [a,b] 中點，f(c) 就是平均值，∫f=f(c)(b−a)。"},
        {"role": "assistant", "content": "中點的值未必等於平均值。$c$ 的存在要靠論證而非指定。先問：$\\frac1{b-a}\\int f$ 一定落在 $f$ 的哪個值域範圍內?"},
        {"role": "user", "content": "落在 [m,M]（最小到最大值）之間，因為 m≤f≤M 積分後得到。"},
        {"role": "assistant", "content": "正是。既然平均值在 $[m,M]$ 內，用哪個定理保證有 $c$ 使 $f(c)$ 恰等於它?"},
        {"role": "user", "content": "介值定理。所以 c 是存在但不一定是中點。"},
        {"role": "assistant", "content": "正確。教訓：$c$ 由介值定理保證存在、位置未知，不能隨意指定為中點。"},
    ]},
    {"problem_id": "D3", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "由 m≤f≤M 積分得 μ=∫f/(b−a)∈[m,M]，IVT 給 c 使 f(c)=μ。"},
        {"role": "assistant", "content": "正確。這個定理的證明用到 $f$ 連續兩次，分別在哪兩處?"},
        {"role": "user", "content": "一是取得 m、M（最大值定理），二是取遍中間值（介值定理），兩者都要連續。"},
        {"role": "assistant", "content": "正確，你清楚連續性的雙重角色。掌握得很完整。"},
    ]},

    # ===== D4: monotonicity of integral =====
    {"problem_id": "D4", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "f≤g 就 ∫f≤∫g，直覺對，但要證我不知道怎麼寫。"},
        {"role": "assistant", "content": "把差移到一邊會簡單。令 $h=g-f$，由 $f\\le g$ 知 $h$ 有什麼符號?"},
        {"role": "user", "content": "h=g−f≥0。"},
        {"role": "assistant", "content": "很好。對非負函數 $h$，任一分割的下和 $L(h,P)=\\sum m_i\\Delta x_i$ 的符號如何，因為每個 $m_i$ 是什麼?"},
        {"role": "user", "content": "每個 m_i=inf h≥0，所以下和≥0，因此 ∫h=sup 下和 ≥0。"},
        {"role": "assistant", "content": "正是。再用積分的線性把 $\\int h$ 拆開，就得到 $\\int f$ 與 $\\int g$ 的關係?"},
        {"role": "user", "content": "∫g−∫f=∫h≥0，所以 ∫f≤∫g。"},
        {"role": "assistant", "content": "完全正確。保序性的根源是「非負函數的積分非負 + 線性」。"},
    ]},
    {"problem_id": "D4", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f≤g 每點都成立，直接兩邊積分不等號不變，就好了。"},
        {"role": "assistant", "content": "結論對，但「兩邊積分不變號」正是要證的性質本身。要回到定義：令 $h=g-f\\ge0$，它的積分為何非負?"},
        {"role": "user", "content": "因為每個子區間 inf h≥0，下和都≥0，所以 ∫h≥0。"},
        {"role": "assistant", "content": "正是，這才是保序性的根據。再用線性得到什麼?"},
        {"role": "user", "content": "∫g−∫f=∫h≥0，故 ∫f≤∫g。"},
        {"role": "assistant", "content": "正確。教訓：「積分保序」不是免費的，要由非負積分＋線性推出。"},
    ]},
    {"problem_id": "D4", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "令 h=g−f≥0，其下和皆≥0 故 ∫h≥0，由線性得 ∫f≤∫g。"},
        {"role": "assistant", "content": "正確。若 $f\\le g$ 但在某些點嚴格 $f<g$，能保證 $\\int f<\\int g$ 嚴格成立嗎?"},
        {"role": "user", "content": "不一定；除非 h=g−f 在某段連續且為正（如 D1 的論證），單點嚴格不足以讓積分嚴格。"},
        {"role": "assistant", "content": "正確，你把嚴格與非嚴格的界線分析得很清楚。很好。"},
    ]},

    # ===== D5: |∫f| ≤ ∫|f| =====
    {"problem_id": "D5", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "|∫f|≤∫|f| 這個絕對值放進去，我不知道怎麼開始。"},
        {"role": "assistant", "content": "先從一個對所有 $x$ 都成立的逐點不等式出發：$f(x)$ 被 $\\pm|f(x)|$ 怎麼夾住?"},
        {"role": "user", "content": "−|f(x)| ≤ f(x) ≤ |f(x)|。"},
        {"role": "assistant", "content": "很好。對這個雙邊不等式用積分保序（D4），會得到關於 $\\int f$ 的什麼?"},
        {"role": "user", "content": "−∫|f| ≤ ∫f ≤ ∫|f|。"},
        {"role": "assistant", "content": "正是。一個實數同時 $\\ge -A$ 且 $\\le A$，等價於它的絕對值滿足什麼?"},
        {"role": "user", "content": "等價於 |∫f|≤A=∫|f|。"},
        {"role": "assistant", "content": "完全正確。這就是連續版的三角不等式：逐點夾 + 積分保序。"},
    ]},
    {"problem_id": "D5", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "由三角不等式 |∫f|=|Σf Δx|≤Σ|f|Δx=∫|f|，直接寫。"},
        {"role": "assistant", "content": "用黎曼和取極限的想法對，但要嚴謹地說極限保持不等號。有沒有更直接、只靠保序性的做法?"},
        {"role": "user", "content": "有，用 −|f|≤f≤|f| 再積分。"},
        {"role": "assistant", "content": "正是。積分後得到 $-\\int|f|\\le\\int f\\le\\int|f|$，這與 $|\\int f|\\le\\int|f|$ 為何等價?"},
        {"role": "user", "content": "因為 −A≤y≤A 就是 |y|≤A 的定義，取 A=∫|f|。"},
        {"role": "assistant", "content": "正確。教訓：逐點夾 + 保序，是比「黎曼和取極限」更乾淨的嚴謹路線。"},
    ]},
    {"problem_id": "D5", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "由 −|f|≤f≤|f| 積分得 −∫|f|≤∫f≤∫|f|，即 |∫f|≤∫|f|。"},
        {"role": "assistant", "content": "正確。這個證明需要 $|f|$ 可積，$f$ 可積能保證 $|f|$ 也可積嗎?"},
        {"role": "user", "content": "能，可積函數的絕對值仍可積（振幅 M_i−m_i 不會增大），所以 ∫|f| 有定義。"},
        {"role": "assistant", "content": "正確，你補上了可積性的前提檢查。非常嚴謹。"},
    ]},

    # ===== D6: FTC part 2 =====
    {"problem_id": "D6", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Newton-Leibniz 公式 ∫f=F(b)−F(a)，我知道怎麼用但不會證。"},
        {"role": "assistant", "content": "把它接到 FTC 第一部分。定義 $G(x)=\\int_a^x f$，由 FTC-1，$G'$ 等於什麼?"},
        {"role": "user", "content": "G'=f。而題目給 F'=f，所以 G'=F'。"},
        {"role": "assistant", "content": "很好，$G'=F'$。由「導數相等的函數相差常數」，$G-F$ 是什麼?"},
        {"role": "user", "content": "G−F=C（常數）。"},
        {"role": "assistant", "content": "正是。用 $x=a$ 定出 $C$，再代 $x=b$，會得到什麼?"},
        {"role": "user", "content": "G(a)=0 給 C=−F(a)，所以 G(x)=F(x)−F(a)，代 b 得 ∫f=G(b)=F(b)−F(a)。"},
        {"role": "assistant", "content": "完全正確。第二部分是「用 FTC-1 造 G，再靠常數差把它換成任意反導數 F」。"},
    ]},
    {"problem_id": "D6", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "F 是 f 的反導數，所以 ∫f=F(b)−F(a)，這是定義。"},
        {"role": "assistant", "content": "這正是要證的公式。要嚴謹，先用 FTC-1 造一個具體的反導數 $G(x)=\\int_a^x f$，它與題目的 $F$ 有何關係?"},
        {"role": "user", "content": "G'=f=F'，所以 G−F 是常數。"},
        {"role": "assistant", "content": "正是。怎麼定出那個常數，最後導出公式?"},
        {"role": "user", "content": "由 G(a)=0 得常數=−F(a)，代 x=b 得 ∫f=F(b)−F(a)。"},
        {"role": "assistant", "content": "正確。教訓：要用「$G'=F'$ 差常數」把積分定義的反導數與任意 $F$ 連起來，而非直接當公式。"},
    ]},
    {"problem_id": "D6", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "設 G(x)=∫_a^x f，FTC-1 給 G'=f=F'，故 G−F=C，由 G(a)=0 得 ∫f=F(b)−F(a)。"},
        {"role": "assistant", "content": "完全正確。第二部分若要在「$f$ 僅黎曼可積、未必連續」下成立，證法需怎麼改?"},
        {"role": "user", "content": "改用分割 + 對每子區間用 MVT 於 F，得 Σ f(c_i)Δx_i=F(b)−F(a)，再令分割加細取極限。"},
        {"role": "assistant", "content": "正確，你給出了不依賴 FTC-1 的更一般版本證法。視野很廣。"},
    ]},

    # ===== D7: continuous ⇒ Riemann integrable =====
    {"problem_id": "D7", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "連續函數可積，這要用上下和，我不知道怎麼控制它們的差。"},
        {"role": "assistant", "content": "可積準則是「上下和之差可任意小」。$f$ 在 $[a,b]$ 連續，能升級成哪個更強的連續性來統一控制波動?"},
        {"role": "user", "content": "由 Heine-Cantor，f 在 [a,b] 一致連續。"},
        {"role": "assistant", "content": "很好。給定 $\\varepsilon$，一致連續給出 $\\delta$，使 $|s-t|<\\delta$ 時 $|f(s)-f(t)|<\\frac{\\varepsilon}{b-a}$。若分割每段長 $<\\delta$，每段的 $M_i-m_i$ 被什麼壓住?"},
        {"role": "user", "content": "M_i−m_i ≤ ε/(b−a)，因為子區間內任兩點距離<δ。"},
        {"role": "assistant", "content": "正是。把 $U-L=\\sum(M_i-m_i)\\Delta x_i$ 估一下，會得到什麼?"},
        {"role": "user", "content": "≤ (ε/(b−a))·Σ Δx_i = (ε/(b−a))(b−a)=ε，所以可積。"},
        {"role": "assistant", "content": "完全正確。關鍵是「一致連續讓每段波動同時 $<\\varepsilon/(b-a)$」，總和才被控制。"},
    ]},
    {"problem_id": "D7", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f 在每點連續，所以每段波動小，上下和差就小，可積。"},
        {"role": "assistant", "content": "逐點連續給的 $\\delta$ 隨點而異，無法讓「所有子區間」同時小。要一個通用的 $\\delta$，該升級成什麼?"},
        {"role": "user", "content": "一致連續（Heine-Cantor），這樣同一個 δ 對整個區間都有效。"},
        {"role": "assistant", "content": "正是。有了通用 $\\delta$，取分割細於 $\\delta$，$U-L$ 的估計如何收尾?"},
        {"role": "user", "content": "每段 M_i−m_i≤ε/(b−a)，總和 U−L≤ε，故可積。"},
        {"role": "assistant", "content": "正確。教訓：可積性要靠「一致」連續提供通用 $\\delta$，逐點連續不夠。"},
    ]},
    {"problem_id": "D7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "Heine-Cantor 給一致連續，取分割 mesh<δ，則 U−L=Σ(M_i−m_i)Δx_i≤ε，可積。"},
        {"role": "assistant", "content": "完全正確。你用到「閉子區間上 $f$ 取得 $M_i,m_i$」，這一步依賴什麼定理?"},
        {"role": "user", "content": "最大值定理，保證閉子區間上最大最小值真的被取到，M_i、m_i 才有意義。"},
        {"role": "assistant", "content": "正確，你把每個隱含引理都點出來了。論證非常完整。"},
    ]},

    # ===== D8: bounds for ∫_0^1 1/(1+x²) =====
    {"problem_id": "D8", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "要估計這個積分在 1/2 和 1 之間，我不知道從哪裡估。"},
        {"role": "assistant", "content": "不必算出積分，先估被積函數。在 $[0,1]$ 上，$1+x^2$ 落在哪個範圍?"},
        {"role": "user", "content": "0≤x²≤1，所以 1≤1+x²≤2。"},
        {"role": "assistant", "content": "很好，取倒數（注意方向）得 $\\frac1{1+x^2}$ 的範圍是什麼?"},
        {"role": "user", "content": "取倒數要反向：1/2 ≤ 1/(1+x²) ≤ 1。"},
        {"role": "assistant", "content": "正是。在長度為 1 的區間上對此不等式積分（保序），會得到什麼?"},
        {"role": "user", "content": "(1/2)·1 ≤ ∫ ≤ 1·1，即 1/2 ≤ ∫ ≤ 1。"},
        {"role": "assistant", "content": "完全正確。估積分的通法就是「先夾被積函數，再乘區間長度」。"},
    ]},
    {"problem_id": "D8", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "1≤1+x²≤2，取倒數得 1≤1/(1+x²)≤1/2。"},
        {"role": "assistant", "content": "取倒數時不等號方向要反轉。$1\\le 1+x^2\\le2$ 取倒數後，較大的分母給較小或較大的值?"},
        {"role": "user", "content": "分母越大值越小，所以是 1/2 ≤ 1/(1+x²) ≤ 1，我方向寫反了。"},
        {"role": "assistant", "content": "正是。修正後在 $[0,1]$ 積分得到什麼上下界?"},
        {"role": "user", "content": "1/2 ≤ ∫ ≤ 1。"},
        {"role": "assistant", "content": "正確。教訓：不等式兩邊同時取倒數（同號時）必須反轉不等號方向。"},
    ]},
    {"problem_id": "D8", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "在 [0,1] 上 1≤1+x²≤2 ⇒ 1/2≤1/(1+x²)≤1，積分得 1/2≤∫≤1。"},
        {"role": "assistant", "content": "正確。實際值是 $\\pi/4\\approx0.785$。若想把上界收緊到接近真值，估計策略要怎麼改進?"},
        {"role": "user", "content": "可把 [0,1] 細分成多段、各段用該段的 max/min 估，分越細界越緊，逼近 π/4。"},
        {"role": "assistant", "content": "正確，這正是上下和加細逼近積分的精神。想法很清楚。"},
    ]},

    # ===== D9: ∫_1^∞ dx/x^p convergence =====
    {"problem_id": "D9", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "這個瑕積分收斂與否跟 p 有關，我不知道怎麼判斷。"},
        {"role": "assistant", "content": "廣義積分的定義就是先算到 $R$、再取 $R\\to\\infty$。先算 $\\int_1^R x^{-p}\\,dx$（設 $p\\ne1$）得到什麼?"},
        {"role": "user", "content": "= (R^{1−p}−1)/(1−p)。"},
        {"role": "assistant", "content": "很好。$R\\to\\infty$ 時 $R^{1-p}$ 的極限取決於指數 $1-p$ 的正負。$p>1$ 時它趨向什麼?"},
        {"role": "user", "content": "p>1 時 1−p<0，R^{1−p}→0，極限=1/(p−1)，收斂。"},
        {"role": "assistant", "content": "正是。那剩下的 $p\\le1$ 情形（提示：$p<1$ 看 $R^{1-p}$、$p=1$ 積分是 $\\ln R$）為何都發散？"},
        {"role": "user", "content": "p<1 時 R^{1−p}→∞ 發散；p=1 時 ∫=ln R→∞ 也發散。所以收斂⟺p>1。"},
        {"role": "assistant", "content": "完全正確。訣竅是「先積到 R、討論 $R^{1-p}$ 的極限，且 $p=1$ 對數情形單獨處理」。"},
    ]},
    {"problem_id": "D9", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "∫x^{−p} 的反導數是 x^{1−p}/(1−p)，對所有 p 都適用，代入無窮就好。"},
        {"role": "assistant", "content": "這個反導數在 $p=1$ 會出問題（分母為零）。$p=1$ 時 $\\int\\frac{dx}{x}$ 的反導數其實是什麼?"},
        {"role": "user", "content": "是 ln x，我漏了這個特例。∫_1^R dx/x=ln R→∞，發散。"},
        {"role": "assistant", "content": "正是。至於 $p\\ne1$，由 $R^{1-p}$ 的極限，何時收斂?"},
        {"role": "user", "content": "p>1 時 R^{1−p}→0 收斂，p<1 時→∞ 發散。所以收斂⟺p>1。"},
        {"role": "assistant", "content": "正確。教訓：冪函數積分務必單獨處理 $p=1$ 的對數情形，別套一般公式。"},
    ]},
    {"problem_id": "D9", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "p≠1 時 ∫_1^R=(R^{1−p}−1)/(1−p)，p>1 收斂到 1/(p−1)；p<1 及 p=1（ln R）發散。"},
        {"role": "assistant", "content": "完全正確。對照級數 $\\sum 1/n^p$，兩者的收斂門檻一致並非巧合，背後是哪個判別法?"},
        {"role": "user", "content": "積分判別法：正遞減函數的級數與其積分同時收斂或發散，所以門檻都是 p>1。"},
        {"role": "assistant", "content": "正確，你把積分與級數的收斂性用積分判別法統一起來了。很好。"},
    ]},

    # ===== D10: integral Cauchy-Schwarz =====
    {"problem_id": "D10", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "積分版的 Cauchy-Schwarz，我完全不知道怎麼起手。"},
        {"role": "assistant", "content": "有個經典技巧：造一個「恆非負」的量。考慮對任意實數 $\\lambda$，$\\int(f-\\lambda g)^2$ 的符號是什麼?"},
        {"role": "user", "content": "被積分的是平方，≥0，所以 ∫(f−λg)²≥0，對所有 λ 都成立。"},
        {"role": "assistant", "content": "很好。把它展開成 $\\lambda$ 的二次式：$\\int f^2-2\\lambda\\int fg+\\lambda^2\\int g^2\\ge0$。這個二次式恆非負，判別式該滿足什麼?"},
        {"role": "user", "content": "判別式 ≤0：(2∫fg)²−4(∫g²)(∫f²)≤0。"},
        {"role": "assistant", "content": "正是。整理這個判別式不等式，就得到目標。是什麼?"},
        {"role": "user", "content": "(∫fg)²≤(∫f²)(∫g²)。"},
        {"role": "assistant", "content": "完全正確。核心手法是「造非負二次式 $\\int(f-\\lambda g)^2$、用判別式 $\\le0$」。"},
    ]},
    {"problem_id": "D10", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "我把判別式設為二次式無實根，所以判別式<0，得到嚴格不等式。"},
        {"role": "assistant", "content": "留意：二次式是「恆 $\\ge0$」而非「無實根」，它可能有重根（等號情形）。因此判別式該是 $<0$ 還是 $\\le0$?"},
        {"role": "user", "content": "應該是 ≤0，因為可以有 λ 使 ∫(f−λg)²=0（f 與 g 成比例時），此時判別式=0。"},
        {"role": "assistant", "content": "正是。用 $\\le0$ 才涵蓋等號。整理判別式得到什麼結論?"},
        {"role": "user", "content": "(∫fg)²≤(∫f²)(∫g²)，含等號。"},
        {"role": "assistant", "content": "正確。教訓：恆非負二次式對應判別式 $\\le0$，$<0$ 會漏掉等號（成比例）情形。"},
    ]},
    {"problem_id": "D10", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "由 ∫(f−λg)²≥0 得 λ 的二次式恆非負，判別式≤0 即 (∫fg)²≤∫f²·∫g²。"},
        {"role": "assistant", "content": "完全正確。這招在 $\\int g^2=0$ 時二次項消失、不再是二次式，該怎麼補這個邊界情形?"},
        {"role": "user", "content": "∫g²=0 時由 D1 得 g≡0，於是 ∫fg=0，不等式兩邊都 0，仍成立，另外處理即可。"},
        {"role": "assistant", "content": "正確，你補上了退化情形。這題論證滴水不漏。"},
    ]},
]
