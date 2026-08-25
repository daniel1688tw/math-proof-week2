# -*- coding: utf-8 -*-
"""主題 A 核心對話（A1-A10 × 3 Persona）。內容由 Claude 手寫。
persona: confused（迷茫）/ error（犯錯）/ bright（優秀）。build.py 會把題目陳述注入第一個 user 回合。"""

DIALOGUES = [
    # ===== A1: lim n^(1/n)=1 =====
    {"problem_id": "A1", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "老師，這題我完全沒頭緒，根號裡是 n、次方也是 n，我不知道怎麼下手。"},
        {"role": "assistant", "content": "先觀察大小：對 $n\\ge1$，$\\sqrt[n]{n}$ 恆 $\\ge1$，你能否據此設一個非負的量來代表它跟 $1$ 的差距？"},
        {"role": "user", "content": "因為 n≥1，所以 n 開 n 次方應該 ≥1。那我設 a_n = n^(1/n) − 1 ≥ 0。"},
        {"role": "assistant", "content": "很好。既然 $\\sqrt[n]{n}=1+a_n$，把等式兩邊同取 $n$ 次方，會得到關於 $n$ 的什麼式子？"},
        {"role": "user", "content": "兩邊 n 次方就是 n = (1+a_n)^n。"},
        {"role": "assistant", "content": "對。$(1+a_n)^n$ 二項式展開全是正項。若只保留含 $a_n^2$ 的那一項當下界，你能寫出哪個不等式？"},
        {"role": "user", "content": "保留 C(n,2)a_n² 這項，就是 n ≥ n(n−1)/2 · a_n²。"},
        {"role": "assistant", "content": "非常好。從這個不等式解出 $a_n$ 的上界，再讓 $n\\to\\infty$，該用哪個定理收尾？"},
        {"role": "user", "content": "解出 a_n² ≤ 2/(n−1)，所以 0 ≤ a_n ≤ √(2/(n−1))→0，用夾擠定理得 a_n→0，極限是 1。"},
        {"role": "assistant", "content": "完全正確，邏輯完整。你已掌握「用二項式製造 $a_n$ 平方項的下界、再夾擠」這個核心手法。"},
    ]},
    {"problem_id": "A1", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "我想這樣做：因為 n→∞ 時 1/n→0，所以 n^(1/n) = n^0 = 1。這樣對嗎？"},
        {"role": "assistant", "content": "留意這是 $\\infty^0$ 型不定式，不能把底數與指數的極限分開代入。你能舉一個 $f(n)^{g(n)}$、底數趨無窮而指數趨零卻不等於 $1$ 的例子嗎？"},
        {"role": "user", "content": "喔…好像 (2^n)^(1/n) = 2，指數趨 0 但結果是 2 不是 1。所以我的代入是錯的。"},
        {"role": "assistant", "content": "正是如此。那我們回到嚴謹路線：設 $a_n=\\sqrt[n]{n}-1\\ge0$，把 $n=(1+a_n)^n$ 展開，你能取哪一項當下界來壓住 $a_n$？"},
        {"role": "user", "content": "取二項式的 C(n,2)a_n² 項，得到 n ≥ n(n−1)/2 · a_n²，所以 a_n ≤ √(2/(n−1))→0，極限是 1。"},
        {"role": "assistant", "content": "很好，這才是有效的論證。關鍵教訓：指數形式的極限不可把底、冪的極限各自代入。"},
    ]},
    {"problem_id": "A1", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "我打算設 a_n = n^(1/n) − 1 ≥ 0，然後用二項式從 n=(1+a_n)^n 壓 a_n 的上界。"},
        {"role": "assistant", "content": "方向很準。為何一次項 $na_n$ 當下界不夠，必須保留到二次項？"},
        {"role": "user", "content": "一次項只給 n ≥ 1+n a_n，推不出 a_n→0。用 C(n,2)a_n² 才有 a_n² ≤ 2/(n−1)。"},
        {"role": "assistant", "content": "正確，二次項才能壓出 $a_n\\to0$ 的速率。最後收尾引用夾擠定理時，需要驗證什麼前提？"},
        {"role": "user", "content": "夾擠定理，前提是 0 ≤ a_n ≤ √(2/(n−1)) 且兩端極限都是 0。"},
        {"role": "assistant", "content": "完整無誤。你抓到了「為何非二次項不可」這個最容易被略過的關鍵。"},
    ]},

    # ===== A2: ε-δ lim x²=4 =====
    {"problem_id": "A2", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "ε-δ 證明我背過定義，但這題真的不知道 δ 要怎麼找。"},
        {"role": "assistant", "content": "先把要控制的量寫清楚：$|x^2-4|$ 能因式分解成什麼形式？"},
        {"role": "user", "content": "可以分解成 |x−2||x+2|。"},
        {"role": "assistant", "content": "很好，其中 $|x-2|$ 正是我們能控制的。剩下的 $|x+2|$ 是變動的，若先假設 $|x-2|<1$，$x$ 會落在哪個範圍？"},
        {"role": "user", "content": "|x−2|<1 表示 1<x<3，那 |x+2| 就小於 5。"},
        {"role": "assistant", "content": "對。於是 $|x^2-4|<5|x-2|$。要讓它 $<\\varepsilon$，$\\delta$ 該怎麼取才能同時滿足這兩個限制？"},
        {"role": "user", "content": "取 δ = min{1, ε/5}，這樣 |x−2|<δ 時 |x²−4| < 5·(ε/5) = ε。"},
        {"role": "assistant", "content": "完全正確。你抓到 $\\varepsilon$-$\\delta$ 的精髓：先用一個預設界固定變動因子，再取 min。"},
    ]},
    {"problem_id": "A2", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "我因式分解成 |x−2||x+2|，然後直接令 δ = ε/|x+2|，這樣 |x²−4| = |x+2|·δ = ε。"},
        {"role": "assistant", "content": "先檢查一件事：回顧定義，$\\delta$ 的選取可以依賴於變數 $x$，還是只能依賴 $\\varepsilon$？"},
        {"role": "user", "content": "定義裡 δ 只能依賴 ε，不能含 x…因為 x 是後面才任意取的。那我這樣寫不合法。"},
        {"role": "assistant", "content": "正是。要擺脫對 $x$ 的依賴，可先假設 $|x-2|<1$。這時 $|x+2|$ 有沒有一個不含 $x$ 的常數上界？"},
        {"role": "user", "content": "有，1<x<3 時 |x+2|<5。所以 |x²−4|<5|x−2|。"},
        {"role": "assistant", "content": "對。那麼結合這個預設界，最後的 $\\delta$ 該怎麼寫成只含 $\\varepsilon$ 的形式？"},
        {"role": "user", "content": "取 δ = min{1, ε/5}，就只依賴 ε 了。"},
        {"role": "assistant", "content": "正確。核心教訓：$\\delta$ 只能依賴 $\\varepsilon$，故必須先用預設界把變動因子換成常數。"},
    ]},
    {"problem_id": "A2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "我會分解 |x−2||x+2|，先設 |x−2|<1 讓 |x+2|<5，再取 δ=min{1, ε/5}。"},
        {"role": "assistant", "content": "步驟正確。為何最後一定要取 min，而不能只寫 $\\delta=\\varepsilon/5$？"},
        {"role": "user", "content": "因為 ε/5 可能大於 1，那時 |x+2|<5 的預設界就不成立了，所以要 min 保住那個界。"},
        {"role": "assistant", "content": "精準。你清楚 min 的兩個角色：保住預設界、同時壓下 $\\varepsilon$。這題你已完全掌握。"},
    ]},

    # ===== A3: lim(a_n+b_n)=L+M =====
    {"problem_id": "A3", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "這題感覺很抽象，兩個數列相加的極限，我不知道從哪裡開始。"},
        {"role": "assistant", "content": "先寫出目標：我們要讓 $|(a_n+b_n)-(L+M)|$ 小於 $\\varepsilon$。這個量能用什麼不等式拆成兩部分？"},
        {"role": "user", "content": "用三角不等式，|(a_n+b_n)−(L+M)| ≤ |a_n−L| + |b_n−M|。"},
        {"role": "assistant", "content": "很好。既然 $a_n\\to L$，為了讓最後相加剛好得 $\\varepsilon$，你會把 $|a_n-L|$ 壓到 $\\varepsilon$ 的幾分之幾？"},
        {"role": "user", "content": "我可以讓 |a_n−L| < ε/2，同樣 |b_n−M| < ε/2，這樣加起來剛好 ε。"},
        {"role": "assistant", "content": "正是。這兩個條件各自給出一個 $N_1$、$N_2$，要同時成立，最終的 $N$ 該怎麼取？"},
        {"role": "user", "content": "取 N = max{N_1, N_2}，n≥N 時兩式都成立，和就 < ε/2+ε/2 = ε。"},
        {"role": "assistant", "content": "完全正確。你掌握了兩個經典技巧：三角不等式拆項、以及 $\\varepsilon/2$ 分配。"},
    ]},
    {"problem_id": "A3", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "我讓 |a_n−L|<ε 且 |b_n−M|<ε，相加得 <2ε，所以極限是 L+M。"},
        {"role": "assistant", "content": "邏輯方向對，但結論的上界是 $2\\varepsilon$ 而非 $\\varepsilon$。定義要求的是恰好小於 $\\varepsilon$，你能怎麼調整一開始的選取？"},
        {"role": "user", "content": "喔，我應該一開始就讓每個 < ε/2，這樣相加才是 ε。"},
        {"role": "assistant", "content": "正確。雖然 $2\\varepsilon$ 也能藉「$\\varepsilon$ 任意」補救，但 $\\varepsilon/2$ 更乾淨。那兩個條件對應的 $N$ 要如何合併？"},
        {"role": "user", "content": "取 N = max{N_1, N_2}，就能保證 n≥N 時兩個 ε/2 同時成立。"},
        {"role": "assistant", "content": "很好。教訓：預留 $\\varepsilon/2$ 給後續相加，能讓上界剛好落在 $\\varepsilon$。"},
    ]},
    {"problem_id": "A3", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "我用三角不等式拆成 |a_n−L|+|b_n−M|，各壓到 ε/2，取 N=max{N_1,N_2}。"},
        {"role": "assistant", "content": "結構完整。若題目改成 $a_n-b_n$，你的三角不等式那一步要怎麼改寫？"},
        {"role": "user", "content": "寫成 |(a_n−b_n)−(L−M)| ≤ |a_n−L| + |b_n−M|，一樣拆成兩塊，後面完全相同。"},
        {"role": "assistant", "content": "正確，差的情形只是符號安排，估計骨架不變。你對這類極限運算律已經很熟練。"},
    ]},

    # ===== A4: lim sin(n)/n = 0 =====
    {"problem_id": "A4", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "sin n 一直在振盪，我不知道這種有 sin 的極限怎麼算。"},
        {"role": "assistant", "content": "振盪的部分能否先「圈住」：$\\sin n$ 不論 $n$ 為何，它的絕對值有什麼上界？"},
        {"role": "user", "content": "|sin n| ≤ 1，這個對所有 n 都成立。"},
        {"role": "assistant", "content": "很好。把它套進分式，$\\left|\\dfrac{\\sin n}{n}\\right|$ 會被什麼較簡單的量壓住？"},
        {"role": "user", "content": "0 ≤ |sin n / n| ≤ 1/n。"},
        {"role": "assistant", "content": "正是。左右兩端當 $n\\to\\infty$ 都趨向 $0$，此時該用哪個定理下結論？"},
        {"role": "user", "content": "左端 0、右端 1/n→0，用夾擠定理得 |sin n / n|→0，所以 sin n / n→0。"},
        {"role": "assistant", "content": "完全正確。處理有界振盪因子的通法就是「取絕對值上界 + 夾擠」。"},
    ]},
    {"problem_id": "A4", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "我覺得因為 sin n 沒有極限，所以 sin n / n 也沒有極限。"},
        {"role": "assistant", "content": "分子沒有極限，不代表整個分式沒有。這裡分子 $\\sin n$ 的大小被限制在哪個範圍？"},
        {"role": "user", "content": "分子被限制在 [−1,1]，分母越來越大，所以整體會被壓小…那其實會趨近 0？"},
        {"role": "assistant", "content": "對。要嚴謹表達這個直覺，$\\left|\\dfrac{\\sin n}{n}\\right|$ 可以被哪個式子夾住？"},
        {"role": "user", "content": "0 ≤ |sin n/n| ≤ 1/n，右邊→0，用夾擠定理得極限 0。"},
        {"role": "assistant", "content": "正確。教訓：有界量除以趨無窮的量會趨零，分子本身有無極限並不影響。"},
    ]},
    {"problem_id": "A4", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "用 |sin n|≤1 得 0≤|sin n/n|≤1/n，夾擠得 0。"},
        {"role": "assistant", "content": "乾淨俐落。這裡為何要對絕對值做夾擠，而不直接夾 $\\sin n/n$ 本身？"},
        {"role": "user", "content": "因為 sin n/n 會正負跳動，直接夾要用 −1/n ≤ sin n/n ≤ 1/n；取絕對值只需一個上界，更簡潔。"},
        {"role": "assistant", "content": "正確，兩種寫法都對，取絕對值省一半功夫。你完全理解夾擠的彈性。"},
    ]},

    # ===== A5: ε-N lim 1/n = 0 =====
    {"problem_id": "A5", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "ε-N 定義我看不太懂，這題 1/n→0 到底要證明什麼？"},
        {"role": "assistant", "content": "定義要求：給任意 $\\varepsilon>0$，找到一個 $N$，使得 $n\\ge N$ 時 $|1/n-0|<\\varepsilon$。你能先把這個不等式解成對 $n$ 的條件嗎？"},
        {"role": "user", "content": "|1/n| = 1/n < ε，解出來是 n > 1/ε。"},
        {"role": "assistant", "content": "很好。那麼要保證存在一個滿足 $N>1/\\varepsilon$ 的正整數，靠的是實數的哪個性質？"},
        {"role": "user", "content": "阿基米德性質，保證存在正整數大於任何實數 1/ε。"},
        {"role": "assistant", "content": "正確。取這樣的 $N$ 後，$n\\ge N$ 時 $1/n$ 與 $1/N$ 的大小關係如何確保不等式成立？"},
        {"role": "user", "content": "n≥N 時 1/n ≤ 1/N < ε，所以定義成立，極限是 0。"},
        {"role": "assistant", "content": "完全正確。ε-N 的流程就是「解不等式求 N、用阿基米德保證存在、驗證單調性」。"},
    ]},
    {"problem_id": "A5", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "我取 N = 1/ε，然後 n≥N 時 1/n<ε，證完。"},
        {"role": "assistant", "content": "$N$ 在定義裡通常要是正整數，但 $1/\\varepsilon$ 未必是整數。該怎麼修正這個取法？"},
        {"role": "user", "content": "喔，要取 N 是大於 1/ε 的正整數，可以用天花板函數 ⌈1/ε⌉ 或直接說由阿基米德性質存在這樣的 N。"},
        {"role": "assistant", "content": "正確。修正後 $n\\ge N>1/\\varepsilon$ 就能保證 $1/n<\\varepsilon$。這個「取整數 N」的細節你以後要記得。"},
        {"role": "user", "content": "懂了，N 一定要是整數，用阿基米德性質敘述最保險。"},
        {"role": "assistant", "content": "很好。教訓：$N$ 是「項的序號」故須為正整數，別直接寫成非整數的 $1/\\varepsilon$。"},
    ]},
    {"problem_id": "A5", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "解 1/n<ε 得 n>1/ε，由阿基米德性質取正整數 N>1/ε，n≥N 時 1/n≤1/N<ε。"},
        {"role": "assistant", "content": "完全標準。你用到「$n\\ge N\\Rightarrow 1/n\\le 1/N$」，這一步依賴數列的什麼性質？"},
        {"role": "user", "content": "依賴 1/n 是遞減的，所以序號越大值越小。"},
        {"role": "assistant", "content": "正確，這個單調性是把 $N$ 的估計傳遞到所有 $n\\ge N$ 的關鍵。論證無懈可擊。"},
    ]},

    # ===== A6: lim n/2^n = 0 =====
    {"problem_id": "A6", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "分子 n 越來越大，分母 2^n 也越來越大，我不知道誰贏。"},
        {"role": "assistant", "content": "指數通常比多項式長得快，但要嚴謹得給 $2^n$ 一個好用的下界。$2^n=(1+1)^n$ 用二項式展開，能取出哪一項?"},
        {"role": "user", "content": "可以取 C(n,2) = n(n−1)/2 這一項當下界。"},
        {"role": "assistant", "content": "很好，所以 $2^n\\ge \\dfrac{n(n-1)}{2}$。把它代進 $\\dfrac{n}{2^n}$ 會得到什麼上界？"},
        {"role": "user", "content": "n/2^n ≤ n / (n(n−1)/2) = 2/(n−1)。"},
        {"role": "assistant", "content": "正是。$0\\le \\dfrac{n}{2^n}\\le \\dfrac{2}{n-1}$，右端 $n\\to\\infty$ 時趨零，該引用哪個定理收尾？"},
        {"role": "user", "content": "右端 2/(n−1)→0，用夾擠定理得 n/2^n→0。"},
        {"role": "assistant", "content": "完全正確。取二項式的二次項當下界，是壓制指數的常用技巧。"},
    ]},
    {"problem_id": "A6", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "用羅必達：n/2^n 的導數是 1/(2^n ln2)→0，所以極限 0。"},
        {"role": "assistant", "content": "數列本身沒有導數，羅必達要先轉成函數版本並確認可微；本課想要初等估計。你能給 $2^n$ 一個多項式量級的下界嗎？"},
        {"role": "user", "content": "用二項式，2^n = (1+1)^n ≥ C(n,2) = n(n−1)/2。"},
        {"role": "assistant", "content": "很好。用這個下界代入，$\\dfrac{n}{2^n}$ 會得到什麼樣的上界？"},
        {"role": "user", "content": "≤ 2/(n−1)→0，夾擠定理得極限 0。"},
        {"role": "assistant", "content": "正確。教訓：數列極限優先用二項式/不等式估計，羅必達需額外的函數化與可微前提。"},
    ]},
    {"problem_id": "A6", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "我用 2^n ≥ C(n,2) = n(n−1)/2 得 n/2^n ≤ 2/(n−1)→0，夾擠。"},
        {"role": "assistant", "content": "俐落。這裡用二次項而非一次項 $2^n\\ge n$，是為了什麼？"},
        {"role": "user", "content": "一次項只給 n/2^n ≤ 1，壓不到 0；要二次項才能讓上界隨 n 趨 0。"},
        {"role": "assistant", "content": "正確，關鍵是下界的階數要高於分子。你對這個「階數比較」的直覺很清楚。"},
    ]},

    # ===== A7: 收斂數列必有界 =====
    {"problem_id": "A7", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "有界是說整個數列被一個數框住，但收斂只保證後面靠近 L，前面怎麼辦？"},
        {"role": "assistant", "content": "你抓到重點了：要分「後面」與「前面」。先用收斂定義取 $\\varepsilon=1$，能得到什麼樣的 $N$ 以及對 $n\\ge N$ 的界？"},
        {"role": "user", "content": "取 ε=1，存在 N 使 n≥N 時 |a_n−L|<1，所以 |a_n| < |L|+1。"},
        {"role": "assistant", "content": "很好，尾巴被 $|L|+1$ 框住了。那前面的 $a_1,\\dots,a_{N-1}$ 只有有限個，該如何把它們也一併框住？"},
        {"role": "user", "content": "只有有限個，可以取它們絕對值的最大值。"},
        {"role": "assistant", "content": "正是。把「尾巴的界」與「前面有限項的最大值」合起來，最終的界 $M$ 怎麼寫？"},
        {"role": "user", "content": "M = max{|a_1|,…,|a_{N−1}|, |L|+1}，這樣所有 |a_n| ≤ M。"},
        {"role": "assistant", "content": "完全正確。核心是「有限項必有界、無限尾巴用收斂框住」，兩者取 max。"},
    ]},
    {"problem_id": "A7", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "因為 a_n→L，所以 |a_n|≤|L|+1，數列有界。"},
        {"role": "assistant", "content": "這個界只對「夠大的 $n$」成立。$n<N$ 的那些項也被 $|L|+1$ 保證了嗎？"},
        {"role": "user", "content": "沒有，前面 N−1 項可能很大，不一定 ≤|L|+1。"},
        {"role": "assistant", "content": "對。那前面這有限個項要怎麼納入最終的界 $M$？"},
        {"role": "user", "content": "取它們的最大絕對值，令 M = max{|a_1|,…,|a_{N−1}|, |L|+1}。"},
        {"role": "assistant", "content": "正確。教訓：收斂只控制尾巴，前面的有限項要另外用 max 收進來。"},
    ]},
    {"problem_id": "A7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "取 ε=1 得 n≥N 時 |a_n|<|L|+1，再令 M=max{|a_1|,…,|a_{N−1}|,|L|+1}。"},
        {"role": "assistant", "content": "結構完整。為何這裡可以放心對前 $N-1$ 項取最大值，而不怕取不到？"},
        {"role": "user", "content": "因為那是有限集合，有限個實數必有最大值，不需要完備性。"},
        {"role": "assistant", "content": "正確，有限性是這步的靈魂。你清楚區分了有限與無限情形所需的工具。"},
    ]},

    # ===== A8: a_n→L ⇒ |a_n|→|L| =====
    {"problem_id": "A8", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "要證 |a_n|→|L|，可是絕對值套上去我不知道怎麼估計差。"},
        {"role": "assistant", "content": "有一個專門處理絕對值之差的工具：反向三角不等式。$\\big||a_n|-|L|\\big|$ 可以被誰壓住？"},
        {"role": "user", "content": "反向三角不等式：||a_n|−|L|| ≤ |a_n−L|。"},
        {"role": "assistant", "content": "很好，右邊正是我們能控制的。由 $a_n\\to L$，對給定的 $\\varepsilon$ 你能讓 $|a_n-L|$ 如何？"},
        {"role": "user", "content": "存在 N 使 n≥N 時 |a_n−L|<ε。"},
        {"role": "assistant", "content": "正是。串起來後 $\\big||a_n|-|L|\\big|$ 就 $<\\varepsilon$。順帶想想：逆命題成立嗎，能否舉反例?"},
        {"role": "user", "content": "逆不成立，例如 a_n=(−1)^n，|a_n|=1→1 但 a_n 不收斂。"},
        {"role": "assistant", "content": "完全正確，連反例都想到了。反向三角不等式是絕對值極限的關鍵工具。"},
    ]},
    {"problem_id": "A8", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "因為 a_n→L，所以 |a_n|→|L|，因為絕對值連續，這樣就好了吧？"},
        {"role": "assistant", "content": "用絕對值函數連續確實可以，但本題要求從定義直接估計。你能寫出 $\\big||a_n|-|L|\\big|$ 的一個上界不等式嗎？"},
        {"role": "user", "content": "嗯…是不是 ||a_n|−|L|| ≤ |a_n−L|？這叫反向三角不等式。"},
        {"role": "assistant", "content": "正是。有了它，$a_n\\to L$ 給出的 $|a_n-L|<\\varepsilon$ 如何直接導出結論？"},
        {"role": "user", "content": "n≥N 時 ||a_n|−|L|| ≤ |a_n−L| < ε，所以 |a_n|→|L|。"},
        {"role": "assistant", "content": "正確。教訓：引用「連續」很快，但基礎題常要求你把反向三角不等式明確寫出。"},
    ]},
    {"problem_id": "A8", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "用反向三角不等式 ||a_n|−|L||≤|a_n−L|<ε 即得。逆命題不成立，a_n=(−1)^n 為例。"},
        {"role": "assistant", "content": "完整。反向三角不等式本身怎麼從標準三角不等式推得？"},
        {"role": "user", "content": "由 |a_n|=|a_n−L+L|≤|a_n−L|+|L| 得 |a_n|−|L|≤|a_n−L|，對調再合併絕對值即可。"},
        {"role": "assistant", "content": "正確，你連工具的來源都能自證。這題掌握得非常扎實。"},
    ]},

    # ===== A9: ε-δ lim(2x+1)=3 =====
    {"problem_id": "A9", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "這題是線性的，但我還是不太會安排 δ。"},
        {"role": "assistant", "content": "先算要控制的量：$|(2x+1)-3|$ 化簡後等於什麼含 $|x-1|$ 的式子？"},
        {"role": "user", "content": "= |2x−2| = 2|x−1|。"},
        {"role": "assistant", "content": "很好。要讓 $2|x-1|<\\varepsilon$，據此 $\\delta$ 該取成什麼？"},
        {"role": "user", "content": "|x−1| < ε/2，所以取 δ = ε/2。"},
        {"role": "assistant", "content": "正確。對照 $x^2$ 那題，為何這裡不必取 min？"},
        {"role": "user", "content": "因為係數 2 是常數，不像 |x+2| 會隨 x 變，所以不用預設界、不用 min。"},
        {"role": "assistant", "content": "完全正確。線性函數的斜率是常數，$\\delta$ 直接由 $\\varepsilon$ 除以斜率即可。"},
    ]},
    {"problem_id": "A9", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "|(2x+1)−3| = |2x−2|，我取 δ=ε，這樣 |x−1|<ε 時就 <ε。"},
        {"role": "assistant", "content": "再算一次：$|2x-2|=2|x-1|$，若 $|x-1|<\\varepsilon$，這個量會是多少，真的 $<\\varepsilon$ 嗎？"},
        {"role": "user", "content": "會是 2|x−1|<2ε，不是 ε。我漏掉了係數 2。"},
        {"role": "assistant", "content": "正是。要讓 $2|x-1|<\\varepsilon$，$\\delta$ 該修正成什麼？"},
        {"role": "user", "content": "取 δ=ε/2，這樣 2|x−1|<2·(ε/2)=ε。"},
        {"role": "assistant", "content": "正確。教訓：別忘了把斜率（係數）算進 $\\delta$，線性項的係數會放大差距。"},
    ]},
    {"problem_id": "A9", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "|(2x+1)−3|=2|x−1|，取 δ=ε/2 即可，不需 min。"},
        {"role": "assistant", "content": "正確。若函數改成 $f(x)=kx+b$（$k\\ne0$），$\\delta$ 的通式會是什麼？"},
        {"role": "user", "content": "δ = ε/|k|，因為 |f(x)−f(x_0)| = |k||x−x_0|。"},
        {"role": "assistant", "content": "完全正確，你抓到線性情形 $\\delta$ 只由 $|k|$ 決定的一般規律。"},
    ]},

    # ===== A10: lim x sin(1/x)=0 =====
    {"problem_id": "A10", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "x→0 時 sin(1/x) 瘋狂振盪，這個極限我不知道存不存在。"},
        {"role": "assistant", "content": "振盪因子先圈住：對所有 $x\\ne0$，$\\left|\\sin\\frac1x\\right|$ 的上界是多少?"},
        {"role": "user", "content": "|sin(1/x)| ≤ 1。"},
        {"role": "assistant", "content": "很好。乘上 $x$ 後，$\\left|x\\sin\\frac1x\\right|$ 被什麼簡單的量壓住?"},
        {"role": "user", "content": "|x sin(1/x)| ≤ |x|。"},
        {"role": "assistant", "content": "正是。$0\\le\\left|x\\sin\\frac1x\\right|\\le|x|$，$x\\to0$ 時右端趨零，該用哪個定理下結論？"},
        {"role": "user", "content": "|x|→0，用夾擠定理，所以 x sin(1/x)→0。"},
        {"role": "assistant", "content": "完全正確。即使內層振盪不存在極限，乘上趨零的有界外因子仍可用夾擠定論。"},
    ]},
    {"problem_id": "A10", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "因為 lim sin(1/x) 不存在，乘積極限律說極限不存在，所以這題無極限。"},
        {"role": "assistant", "content": "乘積極限律要求「兩個極限都存在」才能用，這裡不適用。換個角度：$x\\sin\\frac1x$ 的絕對值被誰控制住?"},
        {"role": "user", "content": "被 |x| 控制，因為 |sin(1/x)|≤1，所以 |x sin(1/x)|≤|x|。"},
        {"role": "assistant", "content": "很好。那麼當 $x\\to0$，用夾擠能得到什麼結論?"},
        {"role": "user", "content": "|x|→0，夾擠得 x sin(1/x)→0，極限存在且為 0。"},
        {"role": "assistant", "content": "正確。教訓：乘積律的前提是兩極限皆存在；不成立時改用夾擠常能救回。"},
    ]},
    {"problem_id": "A10", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "用 |sin(1/x)|≤1 得 |x sin(1/x)|≤|x|→0，夾擠得 0。"},
        {"role": "assistant", "content": "正確。這裡若把 $x$ 換成 $x^2$、內層改 $\\cos\\frac1x$，論證需要改動嗎？"},
        {"role": "user", "content": "不用，一樣 |x² cos(1/x)|≤x²→0，只是外因子換成 x²，夾擠照舊。"},
        {"role": "assistant", "content": "正確，你看出這是「趨零因子 × 有界因子」的通用模式。掌握得很好。"},
    ]},
]
