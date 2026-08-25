# -*- coding: utf-8 -*-
"""主題 E 擴充對話：每題 1 條第二類錯誤變體 + 3 條關鍵步驟短對話。內容由 Claude 手寫。"""

DIALOGUES = [
    # ---- E1 ----
    {"problem_id": "E1", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "遞增數列一定收斂吧，越來越大總會停在某處。"},
        {"role": "assistant", "content": "遞增卻無上界會發散（如 $a_n=n$）。要收斂還需加什麼條件？"},
        {"role": "user", "content": "還要有上界。遞增＋有上界才收斂。"},
        {"role": "assistant", "content": "正是。此時極限取 $\\{a_n\\}$ 的什麼，靠哪個公理保證存在？"},
        {"role": "user", "content": "取 sup，靠完備性（最小上界公理）。"},
        {"role": "assistant", "content": "正確。教訓：遞增不夠，必須有上界；極限是 sup。"},
    ]},
    {"problem_id": "E1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼極限剛好是 sup？"},
        {"role": "assistant", "content": "因為 $\\sup$ 是最小上界，數列遞增會無限逼近它。給 $\\varepsilon$，能找到 $a_N$ 超過什麼值？"},
        {"role": "user", "content": "超過 L−ε（L=sup），因為 L−ε 不是上界。"},
        {"role": "assistant", "content": "正確，逼近性由 sup 的定義來。"},
    ]},
    {"problem_id": "E1", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "遞增性用在證明的哪一步？"},
        {"role": "assistant", "content": "用在把 $a_N>L-\\varepsilon$ 傳給所有 $n\\ge N$。遞增使 $a_n$ 與 $a_N$ 的大小關係如何？"},
        {"role": "user", "content": "n≥N 時 a_n≥a_N>L−ε。"},
        {"role": "assistant", "content": "正確，單調性傳遞下界。"},
    ]},
    {"problem_id": "E1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 a_n≤L？"},
        {"role": "assistant", "content": "因為 $L=\\sup\\{a_n\\}$ 是上界。所以每一項都不超過什麼？"},
        {"role": "user", "content": "不超過 L，故 a_n≤L。"},
        {"role": "assistant", "content": "正確，上界性給出上方界。"},
    ]},

    # ---- E2 ----
    {"problem_id": "E2", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我證 |a_{n+1}−a_n|→0，這樣就是 Cauchy 了吧。"},
        {"role": "assistant", "content": "相鄰項差趨零不等於 Cauchy（如 $a_n=\\sqrt n$）。Cauchy 要控制任意 $m,n$ 大時的 $|a_n-a_m|$。以誰為中介來估？"},
        {"role": "user", "content": "以極限 L 為中介：|a_n−a_m|≤|a_n−L|+|L−a_m|。"},
        {"role": "assistant", "content": "正是，各壓到 $\\varepsilon/2$。相鄰差趨零為何不夠？"},
        {"role": "user", "content": "因為累積起來仍可能發散，√n 就是例子。"},
        {"role": "assistant", "content": "正確。教訓：Cauchy 要控制任意兩項，非僅相鄰項。"},
    ]},
    {"problem_id": "E2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼用極限 L 當中介？"},
        {"role": "assistant", "content": "因為已知 $a_n\\to L$，每項都靠近 $L$。用三角不等式把 $|a_n-a_m|$ 拆成哪兩段？"},
        {"role": "user", "content": "拆成 |a_n−L|+|L−a_m|。"},
        {"role": "assistant", "content": "正確，L 是共同的參考點。"},
    ]},
    {"problem_id": "E2", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "逆命題在 ℚ 上為什麼失敗？"},
        {"role": "assistant", "content": "因為 $\\mathbb{Q}$ 不完備。逼近 $\\sqrt2$ 的有理 Cauchy 列，其極限落在哪裡，故在 $\\mathbb{Q}$ 內收斂嗎？"},
        {"role": "user", "content": "極限是無理數，不在 ℚ，所以不收斂。"},
        {"role": "assistant", "content": "正確，Cauchy 收斂性等價於完備性。"},
    ]},
    {"problem_id": "E2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼取 ε/2？"},
        {"role": "assistant", "content": "因為兩段誤差相加。各壓到 $\\varepsilon/2$，總和才恰為多少？"},
        {"role": "user", "content": "恰為 ε。"},
        {"role": "assistant", "content": "正確，預留一半給相加。"},
    ]},

    # ---- E3 ----
    {"problem_id": "E3", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "a_n→0 就代表 ∑a_n 收斂，反正每項越來越小。"},
        {"role": "assistant", "content": "這是常見誤解。哪個級數通項趨零卻發散，作反例？"},
        {"role": "user", "content": "∑1/n，1/n→0 但發散。所以逆不成立。"},
        {"role": "assistant", "content": "正是。本題的正向命題該怎麼用部分和證？"},
        {"role": "user", "content": "a_n=S_n−S_{n−1}，兩者都→S，差→0。"},
        {"role": "assistant", "content": "正確。教訓：$a_n\\to0$ 只是必要條件，調和級數即反例。"},
    ]},
    {"problem_id": "E3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 a_n=S_n−S_{n−1}？"},
        {"role": "assistant", "content": "因為 $S_n$ 是前 $n$ 項和、$S_{n-1}$ 是前 $n-1$ 項和，兩者相減剩下什麼？"},
        {"role": "user", "content": "剩下第 n 項 a_n。"},
        {"role": "assistant", "content": "正確，這是部分和的基本關係。"},
    ]},
    {"problem_id": "E3", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "這個必要條件的逆否怎麼用？"},
        {"role": "assistant", "content": "逆否是「若 $a_n\\not\\to0$ 則級數發散」。這常被當成什麼判別法？"},
        {"role": "user", "content": "通項判別法（發散測試）。"},
        {"role": "assistant", "content": "正確，實用價值在此。"},
    ]},
    {"problem_id": "E3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 S_{n−1} 也→S？"},
        {"role": "assistant", "content": "因為它只是 $S_n$ 的平移子列，收斂數列的子列與原列同極限。故 $S_{n-1}$ 趨向什麼？"},
        {"role": "user", "content": "趨向同一個 S。"},
        {"role": "assistant", "content": "正確，平移不改變極限。"},
    ]},

    # ---- E4 ----
    {"problem_id": "E4", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我用 1/k²≤1/k 比較，但 ∑1/k 發散，所以我這樣證不出收斂。"},
        {"role": "assistant", "content": "比較對象要選「收斂」的上界。$\\frac1{k^2}$ 換成哪個可裂項的量，其級數才收斂？"},
        {"role": "user", "content": "1/k²≤1/(k(k−1))=1/(k−1)−1/k，這個裂項和收斂。"},
        {"role": "assistant", "content": "正是。裂項求和後 $S_n$ 的上界是什麼常數？"},
        {"role": "user", "content": "<2，遞增有界故收斂。"},
        {"role": "assistant", "content": "正確。教訓：比較的上界級數本身必須收斂，$\\sum1/k$ 不行。"},
    ]},
    {"problem_id": "E4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "裂項 1/(k−1)−1/k 求和為什麼簡單？"},
        {"role": "assistant", "content": "因為它是望遠鏡（telescoping）和，相鄰項相消。從 $k=2$ 加到 $n$ 只剩哪兩項？"},
        {"role": "user", "content": "剩 1−1/n。"},
        {"role": "assistant", "content": "正確，中間全消。"},
    ]},
    {"problem_id": "E4", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "除了裂項還有什麼證法？"},
        {"role": "assistant", "content": "積分判別法或柯西凝聚判別法。積分判別法比較 $\\sum1/n^2$ 與哪個積分？"},
        {"role": "user", "content": "與 ∫_1^∞ x^{−2}dx，收斂故級數收斂。"},
        {"role": "assistant", "content": "正確，多種工具皆可。"},
    ]},
    {"problem_id": "E4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼證部分和有界就夠？"},
        {"role": "assistant", "content": "因為各項為正，$S_n$ 遞增。遞增又有上界，用哪個定理保證收斂？"},
        {"role": "user", "content": "單調有界定理。"},
        {"role": "assistant", "content": "正確，有界性是關鍵。"},
    ]},

    # ---- E5 ----
    {"problem_id": "E5", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我用比值判別法：a_{n+1}/a_n=n/(n+1)→1<1？所以收斂。"},
        {"role": "assistant", "content": "比值極限是 $1$（非 $<1$），比值判別法此時無結論。改看 $S_{2n}-S_n$ 的下界是多少？"},
        {"role": "user", "content": "≥n·1/(2n)=1/2，破壞 Cauchy，所以發散。"},
        {"role": "assistant", "content": "正是。比值極限等於 $1$ 為何不能判定？"},
        {"role": "user", "content": "因為 L=1 時比值判別法失效，需另法。"},
        {"role": "assistant", "content": "正確。教訓：比值極限為 1 時無效，改用分段下界破壞 Cauchy。"},
    ]},
    {"problem_id": "E5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "S_{2n}−S_n 是哪些項的和？"},
        {"role": "assistant", "content": "是第 $n+1$ 到第 $2n$ 項的和 $\\sum_{k=n+1}^{2n}\\frac1k$。這共有幾項？"},
        {"role": "user", "content": "n 項。"},
        {"role": "assistant", "content": "正確，項數是估下界的關鍵。"},
    ]},
    {"problem_id": "E5", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "分組（2^m 塊）證法的結論是什麼？"},
        {"role": "assistant", "content": "按 $2^{m-1}<k\\le2^m$ 分組，每組和 $\\ge\\frac12$。故 $S_{2^m}$ 有什麼下界？"},
        {"role": "user", "content": "S_{2^m}≥1+m/2→∞，發散。"},
        {"role": "assistant", "content": "正確，另一經典證法。"},
    ]},
    {"problem_id": "E5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼每項≥1/(2n)？"},
        {"role": "assistant", "content": "因為 $k$ 從 $n+1$ 到 $2n$，最大是 $2n$。$\\frac1k$ 的最小值出現在 $k=2n$，等於多少？"},
        {"role": "user", "content": "1/(2n)，所以每項≥1/(2n)。"},
        {"role": "assistant", "content": "正確，用最大的分母得最小的項。"},
    ]},

    # ---- E6 ----
    {"problem_id": "E6", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "比值<1 我就直接跟 ∑(比值)^n 比較。"},
        {"role": "assistant", "content": "比值可能隨 $n$ 趨近 $1$，湊不出固定公比。要先取一個固定的什麼數才能比較？"},
        {"role": "user", "content": "取 L<r<1 固定，之後比值<r。"},
        {"role": "assistant", "content": "正是。遞推得 $|a_n|\\le|a_N|r^{n-N}$，比較哪種級數得收斂？"},
        {"role": "user", "content": "比較幾何級數 ∑r^n，收斂。"},
        {"role": "assistant", "content": "正確。教訓：須固定 $L<r<1$，不能用會逼近 1 的比值本身。"},
    ]},
    {"problem_id": "E6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼要插一個 r 在 L 和 1 之間？"},
        {"role": "assistant", "content": "因為要一個「嚴格小於 1 的固定公比」來壓住尾巴。$r$ 取在 $L$ 與 $1$ 之間就能保證什麼？"},
        {"role": "user", "content": "從某項後比值<r<1，可比幾何級數。"},
        {"role": "assistant", "content": "正確，固定公比是比較的前提。"},
    ]},
    {"problem_id": "E6", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "L=1 時各舉一收斂與發散例？"},
        {"role": "assistant", "content": "兩者比值極限都是 $1$。哪個收斂、哪個發散？"},
        {"role": "user", "content": "∑1/n² 收斂、∑1/n 發散。"},
        {"role": "assistant", "content": "正確，故 L=1 無法判定。"},
    ]},
    {"problem_id": "E6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "|a_n|≤|a_N|r^{n−N} 怎麼來的？"},
        {"role": "assistant", "content": "由 $n\\ge N$ 時每步比值 $<r$，逐次相乘。從 $a_N$ 乘到 $a_n$ 共乘幾個 $r$？"},
        {"role": "user", "content": "n−N 個，所以 |a_n|≤|a_N|r^{n−N}。"},
        {"role": "assistant", "content": "正確，遞推累乘。"},
    ]},

    # ---- E7 ----
    {"problem_id": "E7", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "∑|a_n| 收斂，去掉絕對值和更小，所以 ∑a_n 收斂。"},
        {"role": "assistant", "content": "有負項時「更小」不嚴謹。造非負輔助項 $b_n=a_n+|a_n|$，它落在哪個範圍？"},
        {"role": "user", "content": "0≤b_n≤2|a_n|。"},
        {"role": "assistant", "content": "正是。比較得 $\\sum b_n$ 收斂，再用 $a_n=b_n-|a_n|$ 推出什麼？"},
        {"role": "user", "content": "∑a_n=∑b_n−∑|a_n| 收斂。"},
        {"role": "assistant", "content": "正確。教訓：造非負項而非含糊地說「更小」。"},
    ]},
    {"problem_id": "E7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "b_n=a_n+|a_n| 有什麼好處？"},
        {"role": "assistant", "content": "它非負，可用比較判別法。它的上界 $2|a_n|$ 對應的級數收斂嗎？"},
        {"role": "user", "content": "收斂（因 ∑|a_n| 收斂），所以 ∑b_n 收斂。"},
        {"role": "assistant", "content": "正確，轉成非負項是關鍵。"},
    ]},
    {"problem_id": "E7", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "條件收斂的例子？"},
        {"role": "assistant", "content": "收斂但非絕對收斂者。哪個交錯級數收斂、其絕對值級數卻發散？"},
        {"role": "user", "content": "∑(−1)^{n+1}/n 收斂但 ∑1/n 發散，屬條件收斂。"},
        {"role": "assistant", "content": "正確，區分絕對與條件收斂。"},
    ]},
    {"problem_id": "E7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "0≤b_n≤2|a_n| 的左邊怎麼來？"},
        {"role": "assistant", "content": "因為 $a_n\\ge-|a_n|$，故 $b_n=a_n+|a_n|\\ge0$。右邊 $\\le2|a_n|$ 又因 $a_n\\le|a_n|$，對嗎？"},
        {"role": "user", "content": "對，兩邊都由絕對值不等式得到。"},
        {"role": "assistant", "content": "正確，夾出 b_n 的範圍。"},
    ]},

    # ---- E8 ----
    {"problem_id": "E8", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "交錯級數只要 b_n→0 就收斂吧。"},
        {"role": "assistant", "content": "光趨零不夠。若 $b_n$ 不遞減，偶奇子列可能不單調而發散。還需要 $b_n$ 什麼性質？"},
        {"role": "user", "content": "還要遞減，才能讓偶項遞增、奇項遞減。"},
        {"role": "assistant", "content": "正是。兩子列單調有界後，靠 $S_{2n+1}-S_{2n}=b_{2n+1}\\to0$ 得什麼？"},
        {"role": "user", "content": "兩子列同極限，S_n 收斂。"},
        {"role": "assistant", "content": "正確。教訓：Leibniz 需「遞減 + 趨零」兩者。"},
    ]},
    {"problem_id": "E8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 S_{2n} 遞增？"},
        {"role": "assistant", "content": "看 $S_{2n+2}-S_{2n}=b_{2n+1}-b_{2n+2}$。$b_n$ 遞減使這個差是什麼符號？"},
        {"role": "user", "content": "≥0，所以 S_{2n} 遞增。"},
        {"role": "assistant", "content": "正確，遞減性給出符號。"},
    ]},
    {"problem_id": "E8", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "Leibniz 的餘項估計是什麼？"},
        {"role": "assistant", "content": "誤差 $|S-S_n|$ 不超過第一個被捨去項。也就是 $\\le$ 哪一項？"},
        {"role": "user", "content": "≤b_{n+1}。"},
        {"role": "assistant", "content": "正確，實用的誤差界。"},
    ]},
    {"problem_id": "E8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "兩子列為什麼有同一極限？"},
        {"role": "assistant", "content": "因為 $S_{2n+1}-S_{2n}=b_{2n+1}\\to0$。兩單調有界子列的極限之差趨零，故它們如何？"},
        {"role": "user", "content": "相等，同一極限 S。"},
        {"role": "assistant", "content": "正確，差趨零逼出同極限。"},
    ]},

    # ---- E9 ----
    {"problem_id": "E9", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "(1+1/n)^n，底趨 1、冪趨無窮，1^∞=1。"},
        {"role": "assistant", "content": "$1^\\infty$ 是不定式，不能分開取極限。用二項式展開後，$a_n$ 是遞增還遞減？"},
        {"role": "user", "content": "展開成 ∑(1/k!)∏(1−j/n)，因子與項數都增，故遞增。"},
        {"role": "assistant", "content": "正是。再證上界，用 $1/k!\\le1/2^{k-1}$ 得什麼常數界？"},
        {"role": "user", "content": "a_n<3，遞增有界故收斂到 e。"},
        {"role": "assistant", "content": "正確。教訓：$1^\\infty$ 不定式，須證數列單調有界。"},
    ]},
    {"problem_id": "E9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼展開後看得出遞增？"},
        {"role": "assistant", "content": "因為 $n$ 增大時每個因子 $(1-j/n)$ 增大、且多出一項正項。這使 $a_{n+1}$ 與 $a_n$ 的關係如何？"},
        {"role": "user", "content": "a_{n+1}≥a_n，遞增。"},
        {"role": "assistant", "content": "正確，逐項比較即得。"},
    ]},
    {"problem_id": "E9", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "1/k!≤1/2^{k−1} 對哪些 k 成立？"},
        {"role": "assistant", "content": "$k\\ge1$ 時 $k!\\ge2^{k-1}$。$k=0$ 那項要怎麼處理？"},
        {"role": "user", "content": "k=0 項是 1，單獨算，寫成 1+∑_{k≥1}。"},
        {"role": "assistant", "content": "正確，注意求和起點。"},
    ]},
    {"problem_id": "E9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "上界為什麼是 3？"},
        {"role": "assistant", "content": "由 $a_n\\le1+\\sum_{k\\ge1}\\frac1{2^{k-1}}$，那個幾何級數和是多少，總計得什麼？"},
        {"role": "user", "content": "幾何和=2，所以 a_n<1+2=3。"},
        {"role": "assistant", "content": "正確，故有上界 3。"},
    ]},

    # ---- E10 ----
    {"problem_id": "E10", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "a_n≤b_n 且 b_n→0，所以 a_n→0，因此 ∑a_n 收斂。"},
        {"role": "assistant", "content": "比較判別法比較的是部分和而非通項趨零。$A_n$ 與 $B_n$ 的關係、$B_n$ 的界是什麼？"},
        {"role": "user", "content": "A_n≤B_n≤B（∑b_n 之和）。"},
        {"role": "assistant", "content": "正是。$A_n$ 遞增且 $\\le B$，用哪個定理得收斂？"},
        {"role": "user", "content": "單調有界定理。"},
        {"role": "assistant", "content": "正確。教訓：比較部分和的有界性，不是比較通項趨零。"},
    ]},
    {"problem_id": "E10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 A_n 遞增？"},
        {"role": "assistant", "content": "因為各項 $a_k\\ge0$，每加一項部分和只增不減。故 $A_{n+1}$ 與 $A_n$ 的關係？"},
        {"role": "user", "content": "A_{n+1}≥A_n，遞增。"},
        {"role": "assistant", "content": "正確，非負項給遞增。"},
    ]},
    {"problem_id": "E10", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "比較判別法的發散版怎麼敘述？"},
        {"role": "assistant", "content": "逆否形式：若 $0\\le a_n\\le b_n$ 且 $\\sum a_n$ 發散，則 $\\sum b_n$ 如何？"},
        {"role": "user", "content": "也發散（大的更發散）。"},
        {"role": "assistant", "content": "正確，兩個方向都掌握。"},
    ]},
    {"problem_id": "E10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "B_n≤B 是怎麼來的？"},
        {"role": "assistant", "content": "因為 $\\sum b_n$ 收斂到 $B$ 且各項非負，部分和遞增不超過總和。故 $B_n$ 與 $B$ 的關係？"},
        {"role": "user", "content": "B_n≤B。"},
        {"role": "assistant", "content": "正確，收斂的正項級數部分和被總和壓住。"},
    ]},
]
