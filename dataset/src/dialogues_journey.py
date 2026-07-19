# -*- coding: utf-8 -*-
"""跨題型「剛學完微積分但容易卡住」旅程對話（弱點 #7）＋ on-track 只肯定不奉送（弱點 #1 殘餘）
＋ 拒絕大綱式洩漏（弱點 #9 殘餘）。內容由 Claude 手寫並逐題對照參考解驗證。

設計要點：
- fragile persona：多次卡住（含長訊息＋強困惑），助教逐級加深——先聚焦問題、
  再縮小範圍、連卡兩次才點名定理/技巧名稱（不給算式），全程不代寫。
- bright on-track：學生方向正確時只肯定與開放式推進，不指定任何具體代數操作。
- outline-refusal：學生要求先講完整思路時，一句婉拒＋一個問題還主導權。"""

DIALOGUES = [
    # ===== A3 極限和的極限（fragile：開場全無頭緒 → 逐級加深 → 點名三角不等式）=====
    {"problem_id": "A3", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "老師，我剛學完極限的定義，但這題完全不知道從哪裡開始。"},
        {"role": "assistant", "content": "沒關係，先退一步：對單一數列 $a_n\\to L$，$\\varepsilon$-$N$ 定義說的是什麼？"},
        {"role": "user", "content": "就是對任意 ε>0，存在 N，n≥N 時 |a_n−L|<ε。"},
        {"role": "assistant", "content": "很好，定義你是會的。那這題要證的結論，照同樣格式寫出來，要控制的量是哪個絕對值？"},
        {"role": "user", "content": "應該是 |(a_n+b_n)−(L+M)| 要小於 ε。可是我只知道 |a_n−L| 和 |b_n−M| 各自會變小，這三個量要怎麼連起來我毫無頭緒。"},
        {"role": "assistant", "content": "你已經把難點說得很準了。把和重排成 $(a_n-L)+(b_n-M)$ 之後，兩項合在一起的絕對值和分開的絕對值之間有什麼關係？"},
        {"role": "user", "content": "嗯……我還是想不出來，這步真的沒概念。"},
        {"role": "assistant", "content": "這一步的工具是三角不等式。用它把那個絕對值拆開，你會得到什麼樣的上界？"},
        {"role": "user", "content": "喔！|(a_n−L)+(b_n−M)| ≤ |a_n−L|+|b_n−M|。"},
        {"role": "assistant", "content": "正是。現在要讓右邊總和小於 $\\varepsilon$，兩塊各分配多少比較自然？"},
        {"role": "user", "content": "各分 ε/2，那就要有 N₁ 讓 |a_n−L|<ε/2，還有 N₂ 讓 |b_n−M|<ε/2。"},
        {"role": "assistant", "content": "對。最後只剩一件事：兩個門檻 $N_1,N_2$ 要怎麼合成定義裡的那一個 $N$？"},
        {"role": "user", "content": "取 N = max{N₁, N₂}，n≥N 時兩條同時成立，加起來就小於 ε 了。"},
        {"role": "assistant", "content": "完整走完了，而且每一步都是你自己推的。請把整份證明從「給定 $\\varepsilon>0$」開始寫出來，我幫你審閱。"},
        {"role": "user", "content": "證明：給定 ε>0。由 a_n→L 存在 N₁ 使 n≥N₁ 時 |a_n−L|<ε/2；由 b_n→M 存在 N₂ 使 n≥N₂ 時 |b_n−M|<ε/2。取 N=max{N₁,N₂}，則 n≥N 時 |(a_n+b_n)−(L+M)|≤|a_n−L|+|b_n−M|<ε。"},
        {"role": "assistant", "content": "結構完整、量詞順序正確、三角不等式引用得當，沒有缺漏。這題完成了。"},
    ]},

    # ===== B2 最大值定理（fragile：兩段式證明，各卡一次 → 點名 B-W）=====
    {"problem_id": "B2", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "這題我知道結論是連續函數在閉區間會有最大值，但要怎麼「證明」它我完全沒概念，感覺它本來就該對。"},
        {"role": "assistant", "content": "直覺對的事往往最難證。先拆成兩件事：$f$ 要達到最大值之前，得先保證什麼更基本的性質？"},
        {"role": "user", "content": "呃……要先有上界？不然連 sup 都沒有。"},
        {"role": "assistant", "content": "正確，第一步就證有上界。試試反證：若 $f$ 無上界，對每個 $n$ 你能找到什麼樣的點 $x_n$？"},
        {"role": "user", "content": "可以找到 x_n 使 f(x_n)>n。可是這些點散在 [a,b] 裡，我不知道它們會怎樣，卡住了。"},
        {"role": "assistant", "content": "關鍵觀察：這些 $x_n$ 全擠在有界的 $[a,b]$ 裡。有界數列有什麼定理可用？"},
        {"role": "user", "content": "還是想不起來……提示一下好嗎？"},
        {"role": "assistant", "content": "這一步該用 Bolzano-Weierstrass 定理。它對 $\\{x_n\\}$ 給出什麼？"},
        {"role": "user", "content": "喔，有收斂子列！x_{n_k}→x*，而且 x* 還在 [a,b] 裡。"},
        {"role": "assistant", "content": "很好。現在讓 $f$ 的連續性上場：$f(x_{n_k})$ 會趨向什麼，這跟 $f(x_{n_k})>n_k$ 衝突在哪？"},
        {"role": "user", "content": "連續所以 f(x_{n_k})→f(x*)，是個有限值；但 f(x_{n_k})>n_k 會趨向無窮，矛盾。所以 f 有上界。"},
        {"role": "assistant", "content": "第一段完成。第二段：令 $M=\\sup f$，要證有點真的達到 $M$，你會怎麼選一列點靠近 $M$？"},
        {"role": "user", "content": "取 y_n 使 f(y_n)→M……然後應該又是同一招？對 y_n 取收斂子列 y_{n_k}→y*，連續性給 f(y*)=M。"},
        {"role": "assistant", "content": "正是同一招，你自己認出來了。請把兩段合成完整證明寫出來。"},
        {"role": "user", "content": "證明：（一）若 f 無上界，取 x_n∈[a,b] 使 f(x_n)>n，由 B-W 有子列 x_{n_k}→x*∈[a,b]，連續性給 f(x_{n_k})→f(x*) 有限，與 f(x_{n_k})>n_k→∞ 矛盾，故 f 有上界。（二）令 M=sup f，取 y_n 使 f(y_n)→M，由 B-W 取 y_{n_k}→y*∈[a,b]，連續性給 f(y*)=lim f(y_{n_k})=M。故 f 在 y* 達到最大值。"},
        {"role": "assistant", "content": "兩段都嚴謹：反證的矛盾點明確，第二段的子列極限落在 $[a,b]$ 也交代了。完成。"},
    ]},

    # ===== C4 Cauchy 均值定理（fragile：先犯「分開套 MVT」經典錯 → 卡構造 → 點名輔助函數）=====
    {"problem_id": "C4", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "我剛學完均值定理。這題我想對 f 和 g 各用一次均值定理，得到 f(b)−f(a)=f'(c)(b−a) 和 g(b)−g(a)=g'(c)(b−a)，相除就是答案了，對嗎？"},
        {"role": "assistant", "content": "想法自然，但檢查一個細節：兩次均值定理各自給出的那個點，是同一個 $c$ 嗎？"},
        {"role": "user", "content": "啊……不一定，一個是 c₁ 一個是 c₂，相除後湊不成同一點的 f'(c)/g'(c)。那怎麼辦，我完全卡住了。"},
        {"role": "assistant", "content": "卡得很有價值——這正是這題的核心困難。回想 Rolle 定理只給「某一點導數為零」，若想讓結論在同一點發生，你會想構造什麼樣的東西來套 Rolle？"},
        {"role": "user", "content": "構造一個新函數？可是要長什麼樣子我真的想不出來。"},
        {"role": "assistant", "content": "這一步的技巧叫「輔助函數構造」：把 $f,g$ 與端點差值組合成一個函數，讓兩端點取值相等。用 $f(b)-f(a)$ 和 $g(b)-g(a)$ 當係數，你能組出一個候選嗎？"},
        {"role": "user", "content": "試試 h(x) = (f(b)−f(a))·g(x) − (g(b)−g(a))·f(x)？"},
        {"role": "assistant", "content": "很好的候選。驗證 Rolle 的前提：$h(a)$ 和 $h(b)$ 算出來各是什麼？"},
        {"role": "user", "content": "h(a)=f(b)g(a)−g(b)f(a)，h(b)=−g(b)f(a)+f(b)g(a)……展開後一樣！所以 h(a)=h(b)。"},
        {"role": "assistant", "content": "前提成立。套用 Rolle 之後，$h'(c)=0$ 展開成什麼等式？"},
        {"role": "user", "content": "(f(b)−f(a))g'(c) = (g(b)−g(a))f'(c)，除過去就是要證的式子。"},
        {"role": "assistant", "content": "除之前停一下：分母有兩個因子 $g'(c)$ 與 $g(b)-g(a)$，哪一個需要另外論證不為零？"},
        {"role": "user", "content": "g'(c)≠0 是題目給的，但 g(b)−g(a)≠0 要說明——如果相等，Rolle 用在 g 上會有一點 g'=0，跟假設矛盾。"},
        {"role": "assistant", "content": "所有環節都齊了。請把完整證明寫出來，記得把 $g(b)\\ne g(a)$ 放在開頭。"},
        {"role": "user", "content": "證明：先證 g(b)≠g(a)：否則由 Rolle 存在點使 g'=0，與 g'≠0 矛盾。構造 h(x)=(f(b)−f(a))g(x)−(g(b)−g(a))f(x)，h 連續可微且 h(a)=f(b)g(a)−g(b)f(a)=h(b)。由 Rolle 存在 c 使 h'(c)=0，即 (f(b)−f(a))g'(c)=(g(b)−g(a))f'(c)，兩邊除以 g'(c)(g(b)−g(a)) 得 f'(c)/g'(c)=(f(b)−f(a))/(g(b)−g(a))。"},
        {"role": "assistant", "content": "嚴謹完整：前提檢查、構造、Rolle、除法的合法性全都交代了。你也記住了那個經典陷阱——兩次均值定理的點不是同一個。"},
    ]},

    # ===== D5 積分絕對值不等式（fragile：長訊息描述嘗試後強困惑 → 從夾擠事實引導）=====
    {"problem_id": "D5", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "我試過把積分想成很多小矩形的和，每個小塊用三角不等式，感覺方向對但寫不出嚴謹的版本；也想過直接對被積函數操作，但 |∫f| 外面的絕對值和裡面的 |f| 到底怎麼換過去，我毫無頭緒。"},
        {"role": "assistant", "content": "你的直覺其實已經對了，嚴謹版比想像簡單。先不看積分：對每個點 $x$，$f(x)$ 和 $|f(x)|$ 之間有什麼夾擠關係？"},
        {"role": "user", "content": "就是 −|f(x)| ≤ f(x) ≤ |f(x)|。"},
        {"role": "assistant", "content": "對。積分有一個保序性質：若 $u\\le v$ 逐點成立，積分後大小關係如何？"},
        {"role": "user", "content": "積分保持不等號，∫u ≤ ∫v。所以把三邊都積分：−∫|f| ≤ ∫f ≤ ∫|f|。"},
        {"role": "assistant", "content": "很好。最後一步是純代數：一個實數 $t$ 同時滿足 $-A\\le t\\le A$（$A\\ge0$），等價於關於 $|t|$ 的什麼敘述？"},
        {"role": "user", "content": "等價於 |t| ≤ A。所以 |∫f| ≤ ∫|f|，證完了！"},
        {"role": "assistant", "content": "對，整條路你自己走完的。請把三步合成完整證明寫下來。"},
        {"role": "user", "content": "證明：對所有 x 有 −|f(x)|≤f(x)≤|f(x)|。由積分保序，−∫|f|≤∫f≤∫|f|。令 A=∫|f|≥0，則 ∫f 落在 [−A,A]，等價於 |∫f|≤A=∫|f|。"},
        {"role": "assistant", "content": "簡潔正確，三步各有依據。順帶一提，你一開始的「小矩形＋三角不等式」直覺，正是這個證明在 Riemann 和層次的影子。"},
    ]},

    # ===== E2 收斂必 Cauchy（fragile：定義混淆 → 卡橋接 → 點名三角不等式）=====
    {"problem_id": "E2", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "Cauchy 數列的定義我老是記不清楚，跟收斂的定義好像又不太一樣，這題我不知道要證什麼。"},
        {"role": "assistant", "content": "先把兩個定義並排。收斂是「項與極限 $L$ 靠近」，那 Cauchy 的定義是項與什麼靠近？"},
        {"role": "user", "content": "是項跟項互相靠近：對任意 ε>0 存在 N，m,n≥N 時 |a_n−a_m|<ε。"},
        {"role": "assistant", "content": "定義寫對了。所以要證的是：已知每項都靠近 $L$，推出任兩項互相靠近。你手上有 $|a_n-L|$ 和 $|a_m-L|$，目標是 $|a_n-a_m|$，怎麼把它們接起來？"},
        {"role": "user", "content": "嗯……我知道兩項都離 L 很近，直覺上它們就互相很近，但要寫成不等式我完全不會。"},
        {"role": "assistant", "content": "這座橋就是三角不等式：把 $a_n-a_m$ 看成先走到 $L$ 再走出來。拆開後得到什麼上界？"},
        {"role": "user", "content": "|a_n−a_m| ≤ |a_n−L| + |L−a_m|。喔，那兩塊各小於 ε/2 就好了。"},
        {"role": "assistant", "content": "對。那個「各小於 $\\varepsilon/2$」的門檻 $N$ 從哪裡來？"},
        {"role": "user", "content": "從收斂的定義來：對 ε/2 存在 N，n≥N 時 |a_n−L|<ε/2。m,n 都用同一個 N 就行。"},
        {"role": "assistant", "content": "全部到位。請寫出完整證明，注意開頭要「給定 $\\varepsilon>0$」。"},
        {"role": "user", "content": "證明：設 a_n→L。給定 ε>0，存在 N 使 n≥N 時 |a_n−L|<ε/2。對任意 m,n≥N，|a_n−a_m|≤|a_n−L|+|L−a_m|<ε/2+ε/2=ε。故 {a_n} 是 Cauchy 數列。"},
        {"role": "assistant", "content": "量詞、門檻、橋接全都正確。你現在應該也看清了兩個定義的差別：一個對外（極限），一個對內（項與項）。"},
    ]},

    # ===== A7 收斂必有界（bright on-track：只肯定與開放推進，不指定操作）=====
    {"problem_id": "A7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "我的想法：取 ε=1，存在 N 使 n≥N 時 |a_n−L|<1，這樣尾巴的所有項都被 |L|+1 蓋住。"},
        {"role": "assistant", "content": "方向完全正確，尾段已經處理好了。剩下沒被蓋住的是哪些項？"},
        {"role": "user", "content": "前面 a_1 到 a_{N−1} 這有限多項。因為只有有限個，它們自己一定有個最大絕對值。"},
        {"role": "assistant", "content": "對，「有限」正是關鍵理由。那你打算怎麼把兩塊的界合成整個數列的界？"},
        {"role": "user", "content": "取 M = max{|a_1|,…,|a_{N−1}|, |L|+1}，那所有 n 都有 |a_n| ≤ M。"},
        {"role": "assistant", "content": "很好，論證已經完整。請把它寫成正式證明。"},
        {"role": "user", "content": "證明：設 a_n→L。取 ε=1，存在 N 使 n≥N 時 |a_n−L|<1，故 |a_n|≤|L|+1。令 M=max{|a_1|,…,|a_{N−1}|,|L|+1}，則對所有 n 有 |a_n|≤M，數列有界。"},
        {"role": "assistant", "content": "正確且精煉。特別好的是你主動說出「因為只有有限個」——這是這個證明成立的真正理由。"},
    ]},

    # ===== C2 Rolle 定理（bright on-track：肯定＋前提檢查式提問，不代寫任何步驟）=====
    {"problem_id": "C2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "我的計畫：先用最大值定理拿到最大值 M 和最小值 m，然後分情況討論，內部極值點用費馬定理得 f'(c)=0。"},
        {"role": "assistant", "content": "骨架完全正確。先看退化情形：若 $M=m$，函數是什麼樣子，結論怎麼成立？"},
        {"role": "user", "content": "M=m 表示 f 是常數，導數處處為 0，任取 c 都行。"},
        {"role": "assistant", "content": "對。那 $M>m$ 時，為什麼極值點一定至少有一個落在開區間內部，而不是兩個都在端點？"},
        {"role": "user", "content": "因為 f(a)=f(b)。如果最大值和最小值都在端點取，那 M 和 m 都等於 f(a)，就變成 M=m 了，矛盾。"},
        {"role": "assistant", "content": "推理漂亮，這正是 $f(a)=f(b)$ 這個假設的用途。最後引用費馬定理時，它需要哪個前提才能給出 $f'(c)=0$？"},
        {"role": "user", "content": "需要 c 是內部點而且 f 在 c 可微——內部性剛剛證了，可微性是題目在 (a,b) 給的。"},
        {"role": "assistant", "content": "所有前提都對上了。請寫出完整證明。"},
        {"role": "user", "content": "證明：f 在 [a,b] 連續，由最大值定理達到最大值 M 與最小值 m。若 M=m，f 為常數，(a,b) 上 f'≡0，任取 c。若 M>m，由 f(a)=f(b)，最大或最小值至少一個在內部點 c∈(a,b) 取得；c 為內部極值點且 f 在 c 可微，由費馬定理 f'(c)=0。"},
        {"role": "assistant", "content": "完整無缺：兩個情形、內部性的論證、費馬定理的前提都交代了。這份可以當範本。"},
    ]},

    # ===== E5 調和級數發散（outline-refusal：學生要求先講完整思路 → 婉拒＋還主導權）=====
    {"problem_id": "E5", "persona": "fragile", "kind": "core", "turns": [
        {"role": "user", "content": "老師，這題可以先把完整的證明思路講一遍給我聽嗎？我聽完再自己寫，這樣比較快。"},
        {"role": "assistant", "content": "先聽完再寫，記住的會是我的路而不是你的。我們一步步來：級數發散等價於部分和數列 $S_n$ 怎麼樣？"},
        {"role": "user", "content": "S_n 不收斂。可是 1/n 明明越來越小，加起來為什麼會不收斂，我完全沒概念。"},
        {"role": "assistant", "content": "「項趨零但和發散」正是這題有趣的地方。試試看比較 $S_{2n}$ 和 $S_n$：中間多加的是哪些項？"},
        {"role": "user", "content": "多了 1/(n+1) + 1/(n+2) + … + 1/(2n)，共 n 項。"},
        {"role": "assistant", "content": "很好。這 $n$ 項裡最小的是哪一項，據此整段和至少是多少？"},
        {"role": "user", "content": "最小是 1/(2n)，所以整段 ≥ n·(1/(2n)) = 1/2。也就是 S_{2n} − S_n ≥ 1/2，永遠差半格。"},
        {"role": "assistant", "content": "這個「永遠差半格」跟收斂數列的哪個性質互相矛盾？"},
        {"role": "user", "content": "收斂數列是 Cauchy 的，S_{2n}−S_n 應該要趨於 0，但它 ≥ 1/2，矛盾。所以 S_n 不收斂，級數發散！"},
        {"role": "assistant", "content": "整條證明是你自己推出來的——這就是不先聽思路的好處。請把它完整寫下來。"},
        {"role": "user", "content": "證明：設部分和 S_n。S_{2n}−S_n = Σ_{k=n+1}^{2n} 1/k，共 n 項且每項 ≥1/(2n)，故 S_{2n}−S_n ≥ 1/2。若 S_n 收斂則為 Cauchy 數列，須有 S_{2n}−S_n→0，與 ≥1/2 矛盾。故級數發散。"},
        {"role": "assistant", "content": "嚴謹漂亮。而且你現在擁有的是自己的證明，不是我的轉述。"},
    ]},
]
