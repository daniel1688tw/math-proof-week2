# -*- coding: utf-8 -*-
"""主題 E 核心對話（E1-E10 × 3 Persona）。內容由 Claude 手寫。"""

DIALOGUES = [
    # ===== E1: monotone bounded ⇒ convergent =====
    {"problem_id": "E1", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "單調有界定理，我知道會收斂，但不知道極限是誰、怎麼證。"},
        {"role": "assistant", "content": "極限的候選人來自完備性。$\\{a_n\\}$ 遞增且有上界，這個集合有什麼存在?把它當成極限 $L$。"},
        {"role": "user", "content": "有上確界，令 L=sup{a_n}。"},
        {"role": "assistant", "content": "很好。要證 $a_n\\to L$，給定 $\\varepsilon$，因 $L-\\varepsilon$ 不是上界，能找到什麼樣的 $a_N$?"},
        {"role": "user", "content": "存在 N 使 a_N > L−ε。"},
        {"role": "assistant", "content": "正是。用「遞增」這個條件，$n\\ge N$ 時 $a_n$ 被夾在哪兩個值之間?"},
        {"role": "user", "content": "L−ε<a_N≤a_n≤L<L+ε，所以 |a_n−L|<ε，收斂到 L。"},
        {"role": "assistant", "content": "完全正確。核心是「$\\sup$ 當極限、遞增性把 $a_N$ 的下界傳遞給所有 $n\\ge N$」。"},
    ]},
    {"problem_id": "E1", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "數列有界所以收斂，這不是有界就收斂嗎?"},
        {"role": "assistant", "content": "光有界不保證收斂，$a_n=(-1)^n$ 有界卻不收斂。這裡多了哪個條件才使收斂成立?"},
        {"role": "user", "content": "多了單調（遞增）。所以是單調＋有界才收斂。"},
        {"role": "assistant", "content": "正是。那極限應該取 $\\{a_n\\}$ 的什麼，並靠實數的哪個性質保證它存在?"},
        {"role": "user", "content": "取 sup{a_n}，靠完備性（最小上界公理）保證存在。"},
        {"role": "assistant", "content": "正確。教訓：有界≠收斂，必須加單調；極限是 $\\sup$，存在性靠完備性。"},
    ]},
    {"problem_id": "E1", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "令 L=sup{a_n}，給 ε 取 a_N>L−ε，遞增使 n≥N 時 L−ε<a_n≤L，故 a_n→L。"},
        {"role": "assistant", "content": "完全正確。這個定理和 Bolzano-Weierstrass 在邏輯上是什麼關係?"},
        {"role": "user", "content": "單調有界定理較弱但可直接由完備性證；B-W 更強，通常用單調有界或區間套來證。"},
        {"role": "assistant", "content": "正確，你清楚幾個完備性等價命題間的層次。理解很到位。"},
    ]},

    # ===== E2: convergent ⇒ Cauchy =====
    {"problem_id": "E2", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "收斂數列是 Cauchy 數列，這兩個定義我常混，不知道怎麼接。"},
        {"role": "assistant", "content": "Cauchy 是說「任兩個夠後面的項互相靠近」。既然 $a_n\\to L$，把每一項都跟 $L$ 比，先取到什麼?"},
        {"role": "user", "content": "存在 N，使 n≥N 時 |a_n−L|<ε/2。"},
        {"role": "assistant", "content": "很好。以 $L$ 為中介，你打算用三角不等式把 $|a_n-a_m|$ 拆成哪兩項？"},
        {"role": "user", "content": "因為要用三角不等式 |a_n−a_m|≤|a_n−L|+|L−a_m|，兩個 ε/2 加起來才是 ε。"},
        {"role": "assistant", "content": "正是。所以對 $m,n\\ge N$，$|a_n-a_m|$ 的上界是什麼?"},
        {"role": "user", "content": "<ε/2+ε/2=ε，所以是 Cauchy 數列。"},
        {"role": "assistant", "content": "完全正確。訣竅是「以極限 $L$ 為中介、用三角不等式、預留 $\\varepsilon/2$」。"},
    ]},
    {"problem_id": "E2", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "|a_n−a_m|=|a_n−L+L−a_m|≤|a_n−L|+|a_m−L|<ε+ε=2ε，所以是 Cauchy。"},
        {"role": "assistant", "content": "邏輯對，但上界成了 $2\\varepsilon$。要讓它剛好 $<\\varepsilon$，一開始每項該壓到多少?"},
        {"role": "user", "content": "一開始就取 |a_n−L|<ε/2，這樣相加是 ε。"},
        {"role": "assistant", "content": "正是。那兩個條件對應的門檻，取哪個 $N$ 讓 $m,n$ 同時滿足?"},
        {"role": "user", "content": "同一個 N 就好，因為 m,n≥N 時各自都 <ε/2。"},
        {"role": "assistant", "content": "正確。教訓：中介式估計要預留 $\\varepsilon/2$，讓最終上界落在 $\\varepsilon$。"},
    ]},
    {"problem_id": "E2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "取 N 使 n≥N 時 |a_n−L|<ε/2，則 m,n≥N 時 |a_n−a_m|≤|a_n−L|+|L−a_m|<ε。"},
        {"role": "assistant", "content": "完全正確。逆命題「Cauchy⇒收斂」在 $\\mathbb{R}$ 成立、在 $\\mathbb{Q}$ 卻不成立，差別在哪?"},
        {"role": "user", "content": "差在完備性；ℝ 完備使 Cauchy 必收斂，ℚ 不完備（如逼近 √2 的有理 Cauchy 列極限不在 ℚ）。"},
        {"role": "assistant", "content": "正確，你點出 Cauchy 收斂性等價於完備性。視野很好。"},
    ]},

    # ===== E3: ∑a_n converges ⇒ a_n→0 =====
    {"problem_id": "E3", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "級數收斂就 a_n→0，我知道結論但不會證。"},
        {"role": "assistant", "content": "把通項用部分和表示是關鍵。$a_n$ 可以寫成哪兩個部分和的差?"},
        {"role": "user", "content": "a_n=S_n−S_{n−1}，其中 S_n 是前 n 項和。"},
        {"role": "assistant", "content": "很好。級數收斂表示 $S_n\\to S$，那 $S_{n-1}$ 趨向什麼?"},
        {"role": "user", "content": "S_{n−1} 也→S。"},
        {"role": "assistant", "content": "正是。於是 $a_n=S_n-S_{n-1}$ 的極限是什麼?"},
        {"role": "user", "content": "→S−S=0，所以 a_n→0。"},
        {"role": "assistant", "content": "完全正確。這是收斂的必要條件；記得逆命題不成立，你能舉個反例嗎?"},
    ]},
    {"problem_id": "E3", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "反過來也對吧?a_n→0 就代表 ∑a_n 收斂。"},
        {"role": "assistant", "content": "這是常見誤解。有沒有一個 $a_n\\to0$ 但級數卻發散的著名例子?"},
        {"role": "user", "content": "調和級數 ∑1/n，通項→0 但級數發散。所以逆命題錯。"},
        {"role": "assistant", "content": "正是。那正向命題「$\\sum a_n$ 收斂 ⇒ $a_n\\to0$」該怎麼用部分和證?"},
        {"role": "user", "content": "a_n=S_n−S_{n−1}，兩者都→S，差→0。"},
        {"role": "assistant", "content": "正確。教訓：$a_n\\to0$ 只是收斂的必要非充分條件，調和級數即反例。"},
    ]},
    {"problem_id": "E3", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "a_n=S_n−S_{n−1}，S_n,S_{n−1} 皆→S，故 a_n→0；逆不真，∑1/n 為例。"},
        {"role": "assistant", "content": "完全正確。這個必要條件的「逆否」形式常拿來做什麼用途?"},
        {"role": "user", "content": "當作發散判別法：若 a_n 不趨於 0（或極限非 0），則 ∑a_n 必發散。"},
        {"role": "assistant", "content": "正確，這正是「通項判別法」的實用價值。掌握得很好。"},
    ]},

    # ===== E4: ∑1/n² converges =====
    {"problem_id": "E4", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "∑1/n² 收斂，我不會算它的和，那要怎麼證收斂?"},
        {"role": "assistant", "content": "證收斂不必算出和。部分和 $S_n$ 因每項為正是遞增的，只要再證它什麼，就能用單調有界定理?"},
        {"role": "user", "content": "只要證 S_n 有上界。"},
        {"role": "assistant", "content": "很好。找上界的技巧是裂項。對 $k\\ge2$，$\\frac1{k^2}$ 能被哪個可裂項的量壓住?"},
        {"role": "user", "content": "1/k² ≤ 1/(k(k−1)) = 1/(k−1) − 1/k。"},
        {"role": "assistant", "content": "正是。把這個上界從 $k=2$ 加到 $n$，望遠鏡求和後 $S_n$ 的上界是多少?"},
        {"role": "user", "content": "S_n ≤ 1+(1−1/n)<2，遞增又有上界 2，由單調有界定理收斂。"},
        {"role": "assistant", "content": "完全正確。訣竅是「裂項製造望遠鏡和，得到常數上界」。"},
    ]},
    {"problem_id": "E4", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "因為 1/n²→0，所以 ∑1/n² 收斂。"},
        {"role": "assistant", "content": "通項趨零是必要非充分（$\\sum1/n$ 就反例）。要證收斂，可證部分和有界。$\\frac1{k^2}$ 有什麼可裂項的上界?"},
        {"role": "user", "content": "1/k²≤1/(k−1)−1/k（k≥2）。"},
        {"role": "assistant", "content": "正是。求和後 $S_n$ 被壓在什麼常數之下，用哪個定理下結論?"},
        {"role": "user", "content": "S_n<2，遞增有界，用單調有界定理收斂。"},
        {"role": "assistant", "content": "正確。教訓：不能只憑通項趨零判收斂，要證部分和有界（此處靠裂項）。"},
    ]},
    {"problem_id": "E4", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "用 1/k²≤1/(k−1)−1/k 裂項得 S_n≤1+(1−1/n)<2，遞增有界故收斂。"},
        {"role": "assistant", "content": "完全正確。除了裂項，還有哪個標準判別法能證 $\\sum1/n^p$（$p>1$）收斂?"},
        {"role": "user", "content": "積分判別法：∫_1^∞ x^{−p}dx 在 p>1 收斂，故級數收斂；或柯西凝聚判別法。"},
        {"role": "assistant", "content": "正確，你熟悉多種判別工具並知其適用。很好。"},
    ]},

    # ===== E5: harmonic diverges =====
    {"problem_id": "E5", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "∑1/n 每項都趨 0，為什麼還會發散?我不知道怎麼證發散。"},
        {"role": "assistant", "content": "證發散可證部分和不是 Cauchy。看差 $S_{2n}-S_n=\\sum_{k=n+1}^{2n}\\frac1k$，這個和共有幾項?"},
        {"role": "user", "content": "從 n+1 到 2n，共 n 項。"},
        {"role": "assistant", "content": "很好。這 $n$ 項中每一項都 $\\ge$ 最小的 $\\frac1{2n}$，由此整個和有什麼下界？"},
        {"role": "user", "content": "每項≥1/(2n)，所以和≥n·(1/(2n))=1/2。"},
        {"role": "assistant", "content": "正是。若 $\\{S_n\\}$ 收斂它就該是 Cauchy 而使 $S_{2n}-S_n\\to0$，這與剛得到的 $\\ge\\frac12$ 如何矛盾？"},
        {"role": "user", "content": "Cauchy 要求 S_{2n}−S_n→0，但它≥1/2 不趨 0，矛盾，所以發散。"},
        {"role": "assistant", "content": "完全正確。關鍵是「取一段 $n$ 項、每項用最小值估下界得 $\\frac12$，破壞 Cauchy 條件」。"},
    ]},
    {"problem_id": "E5", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "1/n→0，所以 ∑1/n 收斂到某個有限值。"},
        {"role": "assistant", "content": "通項趨零不保證收斂。試看 $S_{2n}-S_n=\\sum_{k=n+1}^{2n}\\frac1k$ 的下界，能給出什麼?"},
        {"role": "user", "content": "有 n 項、每項≥1/(2n)，和≥1/2。這樣就不會趨 0。"},
        {"role": "assistant", "content": "正是。這如何否定「收斂」，用的是哪個必要性質?"},
        {"role": "user", "content": "收斂必為 Cauchy，但 S_{2n}−S_n≥1/2 不→0，違反 Cauchy，故發散。"},
        {"role": "assistant", "content": "正確。教訓：$\\sum1/n$ 是「通項趨零卻發散」的標準反例，判發散可破壞 Cauchy。"},
    ]},
    {"problem_id": "E5", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "S_{2n}−S_n=∑_{k=n+1}^{2n}1/k≥n·1/(2n)=1/2，違反 Cauchy，故發散。"},
        {"role": "assistant", "content": "完全正確。另一種經典證法是分組（$2^m$ 塊）估下界，能簡述其結果嗎?"},
        {"role": "user", "content": "把項按 2^{m−1}<k≤2^m 分組，每組和≥1/2，故 S_{2^m}≥1+m/2→∞，發散。"},
        {"role": "assistant", "content": "正確，你掌握了兩種證法。理解很全面。"},
    ]},

    # ===== E6: ratio test =====
    {"problem_id": "E6", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "比值判別法我會用，但要證它為什麼成立，我不知道。"},
        {"role": "assistant", "content": "既然比值極限 $L<1$，先在 $L$ 與 $1$ 之間插一個數 $r$。為何要取這個 $r$ 而不直接用 $L$?"},
        {"role": "user", "content": "取 L<r<1，這樣從某項後比值 <r，可以跟公比 r 的幾何級數比。"},
        {"role": "assistant", "content": "正是。由極限定義，存在 $N$ 使 $n\\ge N$ 時 $|a_{n+1}/a_n|<r$。遞推後 $|a_n|$ 被什麼壓住?"},
        {"role": "user", "content": "|a_n|≤|a_N|·r^{n−N}（對 n≥N）。"},
        {"role": "assistant", "content": "很好。右邊是收斂的幾何級數，用哪個判別法得到 $\\sum|a_n|$ 收斂?"},
        {"role": "user", "content": "比較判別法，∑|a_N|r^{n−N} 收斂所以 ∑|a_n| 收斂，即絕對收斂。"},
        {"role": "assistant", "content": "完全正確。精髓是「插入 $r$、遞推成幾何上界、再比較」。"},
    ]},
    {"problem_id": "E6", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "比值 <1 就跟公比 <1 的幾何級數比，所以收斂。"},
        {"role": "assistant", "content": "有個陷阱：比值可能一路趨近 $1$（如 $\\sum1/n^2$ 的比值 $\\to1$）。若直接用「比值<1」而非固定的 $r<1$，比較會失效嗎?"},
        {"role": "user", "content": "會，因為比值可能無限逼近 1，湊不出固定公比。要先取 L<r<1 固定住。"},
        {"role": "assistant", "content": "正是。固定 $r$ 後遞推得 $|a_n|\\le|a_N|r^{n-N}$，再比較幾何級數。這裡若 $L=1$ 呢?"},
        {"role": "user", "content": "L=1 時插不進 r<1，判別法失效，需另尋方法。"},
        {"role": "assistant", "content": "正確。教訓：必須固定一個 $L<r<1$ 才能比較；$L=1$ 時比值判別法無效。"},
    ]},
    {"problem_id": "E6", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "取 L<r<1，∃N 使 n≥N 時比值<r，遞推 |a_n|≤|a_N|r^{n−N}，比較幾何級數得絕對收斂。"},
        {"role": "assistant", "content": "完全正確。比值判別法在 $L=1$ 時無結論，能各舉一個此時收斂與發散的例子嗎?"},
        {"role": "user", "content": "∑1/n² 收斂、∑1/n 發散，兩者比值極限都是 1，說明 L=1 無法判定。"},
        {"role": "assistant", "content": "正確，你精準界定了判別法的失效邊界。很好。"},
    ]},

    # ===== E7: absolute convergence ⇒ convergence =====
    {"problem_id": "E7", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "絕對收斂就收斂，但 a_n 可能有正有負，我不知道怎麼處理符號。"},
        {"role": "assistant", "content": "把帶符號的項轉成非負項是關鍵。令 $b_n=a_n+|a_n|$，它的範圍是什麼?"},
        {"role": "user", "content": "0≤b_n≤2|a_n|（因為 a_n≥−|a_n|）。"},
        {"role": "assistant", "content": "很好。既然 $\\sum|a_n|$ 收斂，$\\sum2|a_n|$ 也收斂，用比較判別法對 $\\sum b_n$ 得到什麼?"},
        {"role": "user", "content": "∑b_n 收斂（非負項被收斂級數壓住）。"},
        {"role": "assistant", "content": "正是。最後把 $a_n=b_n-|a_n|$，$\\sum a_n$ 因此如何?"},
        {"role": "user", "content": "∑a_n=∑b_n−∑|a_n|，兩收斂級數之差，所以收斂。"},
        {"role": "assistant", "content": "完全正確。訣竅是「用 $b_n=a_n+|a_n|$ 轉非負、比較、再相減」。"},
    ]},
    {"problem_id": "E7", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "∑|a_n| 收斂，把絕對值拿掉只會更小，所以 ∑a_n 收斂。"},
        {"role": "assistant", "content": "「拿掉絕對值更小」不嚴謹，$a_n$ 有負項時和未必更小。要嚴謹得造非負輔助項，$b_n=a_n+|a_n|$ 有何好處?"},
        {"role": "user", "content": "b_n≥0 且≤2|a_n|，可以用比較判別法證 ∑b_n 收斂。"},
        {"role": "assistant", "content": "正是。有了 $\\sum b_n$ 收斂，怎麼回推 $\\sum a_n$?"},
        {"role": "user", "content": "a_n=b_n−|a_n|，兩收斂級數相減，故 ∑a_n 收斂。"},
        {"role": "assistant", "content": "正確。教訓：處理帶符號級數要造非負項 $a_n+|a_n|$，而非含糊地說「更小」。"},
    ]},
    {"problem_id": "E7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "令 b_n=a_n+|a_n|∈[0,2|a_n|]，比較得 ∑b_n 收斂，故 ∑a_n=∑b_n−∑|a_n| 收斂。"},
        {"role": "assistant", "content": "完全正確。條件收斂（收斂但非絕對收斂）的級數存在嗎，舉例?"},
        {"role": "user", "content": "存在，∑(−1)^{n+1}/n 收斂（Leibniz）但 ∑1/n 發散，故為條件收斂。"},
        {"role": "assistant", "content": "正確，你清楚絕對收斂與條件收斂的區別。掌握得很好。"},
    ]},

    # ===== E8: Leibniz alternating series =====
    {"problem_id": "E8", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "交錯級數判別法的證明，我不知道怎麼用單調有界。"},
        {"role": "assistant", "content": "訣竅是分別看偶數與奇數部分和。先看偶數項 $S_{2n}$，$S_{2n+2}-S_{2n}=b_{2n+1}-b_{2n+2}$ 的符號如何（$b_n$ 遞減）?"},
        {"role": "user", "content": "b_{2n+1}−b_{2n+2}≥0，所以 S_{2n} 遞增。"},
        {"role": "assistant", "content": "很好。同理奇數項 $S_{2n+1}$ 是遞減的。再看 $S_{2n+1}-S_{2n}=b_{2n+1}$，這說明兩子列的相對位置與有界性如何?"},
        {"role": "user", "content": "S_{2n}≤S_{2n+1}，所以 S_{2n} 有上界 S_1、S_{2n+1} 有下界 S_2，兩者都單調有界故收斂。"},
        {"role": "assistant", "content": "正是。最後由 $S_{2n+1}-S_{2n}=b_{2n+1}\\to0$，兩子列的極限有何關係，整個 $S_n$ 如何?"},
        {"role": "user", "content": "兩子列同極限 S，所以 S_n→S，級數收斂。"},
        {"role": "assistant", "content": "完全正確。核心是「偶、奇子列各單調有界、差 $b_{2n+1}\\to0$ 逼出同一極限」。"},
    ]},
    {"problem_id": "E8", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "b_n→0 所以交錯級數收斂，通項趨零就夠了。"},
        {"role": "assistant", "content": "光 $b_n\\to0$ 不夠，還需要 $b_n$ 的哪個性質，才能保證兩子列夾出同一極限?"},
        {"role": "user", "content": "還要 b_n 遞減。少了遞減，偶/奇子列不一定單調，會出問題。"},
        {"role": "assistant", "content": "正是。有了遞減，$S_{2n}$ 遞增、$S_{2n+1}$ 遞減，再靠什麼讓兩者極限相同?"},
        {"role": "user", "content": "靠 S_{2n+1}−S_{2n}=b_{2n+1}→0，兩子列同極限，故 S_n 收斂。"},
        {"role": "assistant", "content": "正確。教訓：Leibniz 需「遞減 + 趨零」兩條件，缺遞減可能發散。"},
    ]},
    {"problem_id": "E8", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "S_{2n} 遞增、S_{2n+1} 遞減、S_{2n}≤S_{2n+1}，兩子列單調有界；差 b_{2n+1}→0 給同極限。"},
        {"role": "assistant", "content": "完全正確。Leibniz 判別法還附帶一個好用的誤差估計，是什麼?"},
        {"role": "user", "content": "餘項 |S−S_n|≤b_{n+1}，即誤差不超過第一個被捨去項的絕對值。"},
        {"role": "assistant", "content": "正確，你連實用的餘項估計都掌握了。很好。"},
    ]},

    # ===== E9: (1+1/n)^n converges =====
    {"problem_id": "E9", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "要證 (1+1/n)^n 收斂（就是 e），我完全不知道怎麼下手。"},
        {"role": "assistant", "content": "用單調有界定理，需證兩件事。先把 $a_n=(1+\\frac1n)^n$ 用二項式展開成含 $\\frac1{k!}$ 的和，你能寫出通項嗎?"},
        {"role": "user", "content": "a_n=∑_{k=0}^n (1/k!)·∏_{j=0}^{k−1}(1−j/n)。"},
        {"role": "assistant", "content": "很好。當 $n$ 增大時每個因子 $(1-j/n)$ 變大、項數也變多，由此 $a_n$ 的單調性為何？"},
        {"role": "user", "content": "每個因子變大、項數變多，所以 a_{n+1}≥a_n，遞增。"},
        {"role": "assistant", "content": "正是。再證有界：每個乘積 $\\le1$，故 $a_n\\le\\sum_{k=0}^n\\frac1{k!}$，這個和能被哪個幾何級數壓到常數?"},
        {"role": "user", "content": "1/k!≤1/2^{k−1}，所以 a_n≤1+∑1/2^{k−1}<3，遞增有界故收斂。"},
        {"role": "assistant", "content": "完全正確。關鍵是「二項式展開看出遞增、$1/k!\\le1/2^{k-1}$ 壓出上界 3」。"},
    ]},
    {"problem_id": "E9", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "因為 1/n→0，所以 (1+1/n)^n→1^∞=1。"},
        {"role": "assistant", "content": "這是 $1^\\infty$ 不定式，不能把底與冪的極限分開。要嚴謹得證數列本身收斂。先用二項式展開後，$a_n$ 是遞增還遞減?"},
        {"role": "user", "content": "展開成 ∑(1/k!)∏(1−j/n)，因子與項數都隨 n 增，所以遞增，不是趨於 1。"},
        {"role": "assistant", "content": "正是。再證有上界，用 $1/k!\\le1/2^{k-1}$ 得到什麼常數界?"},
        {"role": "user", "content": "a_n<3，遞增有界故收斂到某個介於 2 和 3 的數（就是 e）。"},
        {"role": "assistant", "content": "正確。教訓：$1^\\infty$ 是不定式，不可分開取極限；此列實際遞增趨於 $e\\approx2.718$。"},
    ]},
    {"problem_id": "E9", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "二項式展開見 a_n 遞增，且 a_n≤∑1/k!≤1+∑1/2^{k−1}<3，單調有界故收斂。"},
        {"role": "assistant", "content": "完全正確。你用 $1/k!\\le1/2^{k-1}$ 得上界，這個不等式對哪些 $k$ 成立，$k=0,1$ 要注意嗎?"},
        {"role": "user", "content": "k≥1 時 k!≥2^{k−1} 成立；k=0 那項是 1，單獨算，所以寫成 1+∑_{k≥1}。"},
        {"role": "assistant", "content": "正確，你注意到求和起點的細節。論證很嚴謹。"},
    ]},

    # ===== E10: comparison test =====
    {"problem_id": "E10", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "比較判別法：0≤a_n≤b_n 且 ∑b_n 收斂就 ∑a_n 收斂，這要怎麼證?"},
        {"role": "assistant", "content": "看部分和。$A_n=\\sum a_k$、$B_n=\\sum b_k$，因各項非負，這兩個部分和數列有什麼單調性?"},
        {"role": "user", "content": "都是遞增的。"},
        {"role": "assistant", "content": "很好。由 $a_k\\le b_k$ 知 $A_n\\le B_n$，而收斂的 $B_n$ 又被什麼上界壓住？"},
        {"role": "user", "content": "A_n≤B_n，而 ∑b_n 收斂所以 B_n≤B（總和）。所以 A_n≤B。"},
        {"role": "assistant", "content": "正是。$A_n$ 遞增又有上界 $B$，用哪個定理下結論?"},
        {"role": "user", "content": "單調有界定理，A_n 收斂，即 ∑a_n 收斂。"},
        {"role": "assistant", "content": "完全正確。比較判別法的骨架就是「部分和遞增 + 被 $B$ 壓住 + 單調有界」。"},
    ]},
    {"problem_id": "E10", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "a_n≤b_n 且 b_n→0，所以 a_n→0，因此 ∑a_n 收斂。"},
        {"role": "assistant", "content": "通項趨零不保證級數收斂。比較判別法比較的是「部分和」還是「通項」?"},
        {"role": "user", "content": "是部分和。應該說 A_n≤B_n≤B，而不是只看通項。"},
        {"role": "assistant", "content": "正是。$A_n$ 遞增且 $\\le B$，再用哪個定理得收斂?"},
        {"role": "user", "content": "單調有界定理，A_n 收斂。"},
        {"role": "assistant", "content": "正確。教訓：比較判別法靠「部分和有界 + 單調」，不是比較通項趨零。"},
    ]},
    {"problem_id": "E10", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "A_n、B_n 皆遞增，A_n≤B_n≤B，故 A_n 遞增有界，單調有界定理給 ∑a_n 收斂。"},
        {"role": "assistant", "content": "完全正確。它的逆否形式（比較判別法的發散版）怎麼敘述?"},
        {"role": "user", "content": "若 0≤a_n≤b_n 且 ∑a_n 發散，則 ∑b_n 發散（大的更發散）。"},
        {"role": "assistant", "content": "正確，你掌握了比較判別法的兩個方向。很好。"},
    ]},
]
