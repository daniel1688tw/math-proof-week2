# -*- coding: utf-8 -*-
"""分級提示對話（10 條，A-E 各 2 題）：內容由 Claude 手寫。

示範新規則：學生對同一步連續兩次答不出來/方向錯誤時，助教才可點出關鍵定理或技巧「名稱」
（不解釋如何套用、不給算式），再問一個問題讓學生自己接著推導。
持久卡兩次前一律只用問題重新引導，不得提早給名稱——避免「透漏」被濫用成走捷徑。
"""

DIALOGUES = [
    # ===== A4：夾擠定理 =====
    {"problem_id": "A4", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "老師我完全不知道怎麼處理 sin n 這種振盪的東西。"},
        {"role": "assistant", "content": "先想想 $\\sin n$ 雖然振盪，但它的絕對值有沒有一個固定的上界？"},
        {"role": "user", "content": "不知道，我沒學過怎麼處理振盪函數的極限。"},
        {"role": "assistant", "content": "沒關係，換個角度：$|\\sin n|$ 對任何 $n$ 都不會超過哪個數？"},
        {"role": "user", "content": "還是想不到，對不起。"},
        {"role": "assistant", "content": "這一步的關鍵是夾擠定理。你能自己找出 $\\left|\\frac{\\sin n}{n}\\right|$ 的一個上界嗎？"},
        {"role": "user", "content": "喔！$\\left|\\frac{\\sin n}{n}\\right|\\le\\frac1n$，因為 $|\\sin n|\\le1$。"},
        {"role": "assistant", "content": "對，$0\\le\\left|\\frac{\\sin n}{n}\\right|\\le\\frac1n\\to0$，接下來你知道怎麼收尾了嗎？"},
        {"role": "user", "content": "兩端都趨 0，用夾擠定理得極限是 0。"},
        {"role": "assistant", "content": "完全正確。有了定理名稱後你自己補完了整個論證，這就是重點。"},
    ]},

    # ===== A1：二項式定理 =====
    {"problem_id": "A1", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "n 開 n 次方這種東西我完全沒有頭緒。"},
        {"role": "assistant", "content": "先設 $a_n=\\sqrt[n]{n}-1\\ge0$，把等式兩邊同取 $n$ 次方會得到什麼？"},
        {"role": "user", "content": "我不知道要怎麼展開 (1+a_n)^n。"},
        {"role": "assistant", "content": "沒關係，換個問法：$(1+a_n)^n$ 有沒有一種標準方式可以把它寫成一串加總？"},
        {"role": "user", "content": "還是沒有頭緒，抱歉。"},
        {"role": "assistant", "content": "這裡要用二項式定理展開。展開後，如果只保留含 $a_n^2$ 的那一項當下界，你能寫出什麼不等式？"},
        {"role": "user", "content": "喔，$n\\ge\\binom{n}{2}a_n^2=\\frac{n(n-1)}{2}a_n^2$。"},
        {"role": "assistant", "content": "很好。解出 $a_n$ 的上界後，讓 $n\\to\\infty$，你會用哪個定理收尾？"},
        {"role": "user", "content": "$a_n^2\\le\\frac{2}{n-1}$，用夾擠定理得 $a_n\\to0$，極限是 1。"},
        {"role": "assistant", "content": "完全正確，你把二項式定理套進去後自己完成了整個估計。"},
    ]},

    # ===== B2：Bolzano-Weierstrass 定理 =====
    {"problem_id": "B2", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "要證明有界性我完全不知道從哪裡切入。"},
        {"role": "assistant", "content": "用反證法：若 $f$ 無上界，能對每個 $n$ 取到 $f(x_n)>n$ 的點 $x_n$。$\\{x_n\\}$ 是不是也在 $[a,b]$ 裡？"},
        {"role": "user", "content": "是啊，但接下來我不知道能做什麼。"},
        {"role": "assistant", "content": "$\\{x_n\\}$ 是有界數列，有沒有辦法從裡面抓出一個收斂的子列？"},
        {"role": "user", "content": "我想不出來要用什麼工具。"},
        {"role": "assistant", "content": "這裡要用 Bolzano-Weierstrass 定理。它能給你 $\\{x_n\\}$ 的一個收斂子列，這對後面的矛盾有什麼幫助？"},
        {"role": "user", "content": "子列 $x_{n_k}\\to x^*\\in[a,b]$，由連續性 $f(x_{n_k})\\to f(x^*)$ 有限，跟 $f(x_{n_k})>n_k\\to\\infty$ 矛盾！"},
        {"role": "assistant", "content": "完全正確，你自己把矛盾接起來了，這就是完整的證明骨架。"},
    ]},

    # ===== B7：介值定理 =====
    {"problem_id": "B7", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "奇次多項式有實根，我不知道要怎麼證。"},
        {"role": "assistant", "content": "先看 $x\\to+\\infty$ 和 $x\\to-\\infty$ 時，這個多項式的值會怎麼變化？"},
        {"role": "user", "content": "我不確定，多項式的極限我不太會分析。"},
        {"role": "assistant", "content": "換個角度：最高次項是奇次，當 $x$ 很大或很小時，函數值的正負號會是什麼？"},
        {"role": "user", "content": "還是不太確定，可以再提示一下嗎？"},
        {"role": "assistant", "content": "有了一正一負的兩個函數值後，這裡要用介值定理。你能說出它怎麼幫你找到根嗎？"},
        {"role": "user", "content": "p 在 [a,b] 連續，且 p(a)<0<p(b)，介值定理給存在 c 使 p(c)=0！"},
        {"role": "assistant", "content": "完全正確，你只差「兩端異號」這個前提，現在你自己補上了。"},
    ]},

    # ===== C2：費馬定理 =====
    {"problem_id": "C2", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "Rolle 定理的證明我不知道要從哪裡開始。"},
        {"role": "assistant", "content": "$f$ 在 $[a,b]$ 連續，這保證它會取得什麼樣的值？"},
        {"role": "user", "content": "我不知道連續能保證什麼。"},
        {"role": "assistant", "content": "換個問法：閉區間上的連續函數，一定會有最大值和最小值嗎？"},
        {"role": "user", "content": "應該有吧，但我不知道怎麼用這個。"},
        {"role": "assistant", "content": "若最大或最小落在內部點，這裡要用費馬定理。它能告訴你該點的導數是多少？"},
        {"role": "user", "content": "費馬定理說內部極值點的導數是 0，所以 $f'(c)=0$！"},
        {"role": "assistant", "content": "正確。你還記得要先排除「$f$ 是常數」這個特殊情形嗎？"},
        {"role": "user", "content": "記得，那時 f' 處處為 0，隨便取 c 都行。"},
        {"role": "assistant", "content": "完全正確，兩種情形你都覆蓋到了。"},
    ]},

    # ===== C3：Rolle 定理 =====
    {"problem_id": "C3", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "均值定理要怎麼從 Rolle 定理推過來，我沒有頭緒。"},
        {"role": "assistant", "content": "Rolle 定理需要兩端點函數值相等，但這題的 $f(a)$ 不一定等於 $f(b)$。你會怎麼處理？"},
        {"role": "user", "content": "我不知道要怎麼讓兩端相等。"},
        {"role": "assistant", "content": "換個想法：能不能造一個新函數，把 $f$ 減去某條直線，讓端點差歸零？"},
        {"role": "user", "content": "還是想不出來要減哪條線。"},
        {"role": "assistant", "content": "這裡要用 Rolle 定理，減去的正是連接 $(a,f(a))$ 與 $(b,f(b))$ 的割線。你能寫出這個輔助函數嗎？"},
        {"role": "user", "content": "$g(x)=f(x)-f(a)-\\frac{f(b)-f(a)}{b-a}(x-a)$，這樣 $g(a)=g(b)=0$！"},
        {"role": "assistant", "content": "很好，對 $g$ 用 Rolle 定理後，$g'(c)=0$ 能推出什麼？"},
        {"role": "user", "content": "$g'(x)=f'(x)-\\frac{f(b)-f(a)}{b-a}$，所以 $f'(c)=\\frac{f(b)-f(a)}{b-a}$。"},
        {"role": "assistant", "content": "完全正確，你自己把輔助函數與 Rolle 定理接了起來。"},
    ]},

    # ===== D3：介值定理（積分中值） =====
    {"problem_id": "D3", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "積分中值定理要怎麼證，我完全不知道 c 從哪裡冒出來。"},
        {"role": "assistant", "content": "$f$ 在 $[a,b]$ 連續，能取得最小值 $m$ 和最大值 $M$。積分 $\\int_a^b f$ 會落在什麼範圍？"},
        {"role": "user", "content": "我不太確定要怎麼把積分跟 m、M 連起來。"},
        {"role": "assistant", "content": "換個角度：若 $m\\le f(x)\\le M$ 對所有 $x$ 成立，對這個不等式積分會得到什麼？"},
        {"role": "user", "content": "還是不太會，抱歉。"},
        {"role": "assistant", "content": "這裡要用介值定理。積分後的不等式會把平均值夾在 $m$ 與 $M$ 之間，你能自己寫出這個不等式嗎？"},
        {"role": "user", "content": "平均值 $\\mu=\\frac1{b-a}\\int_a^b f$ 落在 $[m,M]$ 內，介值定理給存在 c 使 f(c)=μ！"},
        {"role": "assistant", "content": "完全正確，你自己把「夾出平均值」和「介值定理取到它」兩步接起來了。"},
    ]},

    # ===== D7：Heine-Cantor 定理（一致連續） =====
    {"problem_id": "D7", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "連續函數可積的證明我不知道怎麼控制上下和的差。"},
        {"role": "assistant", "content": "逐點連續給的 $\\delta$ 會隨點變動。要讓所有子區間同時被壓住，你需要哪種更強的連續性？"},
        {"role": "user", "content": "我不知道除了連續還有什麼更強的版本。"},
        {"role": "assistant", "content": "換個問法：有沒有一種連續性，能保證同一個 $\\delta$ 對整個區間的所有點都通用？"},
        {"role": "user", "content": "還是想不起來，可以直接提示嗎？"},
        {"role": "assistant", "content": "這裡要用 Heine-Cantor 定理（一致連續）。有了通用的 $\\delta$，你能說出 $U-L$ 的上界會是什麼嗎？"},
        {"role": "user", "content": "取分割 mesh<δ，每段 $M_i-m_i\\le\\varepsilon/(b-a)$，所以 $U-L\\le\\varepsilon$！"},
        {"role": "assistant", "content": "完全正確，通用 $\\delta$ 正是你需要的那把鑰匙。"},
    ]},

    # ===== E9：單調有界定理 =====
    {"problem_id": "E9", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "(1+1/n)^n 收斂，這個我完全不知道怎麼下手。"},
        {"role": "assistant", "content": "這是 $1^\\infty$ 型不定式，不能直接代極限。你會怎麼證明這個數列本身收斂？"},
        {"role": "user", "content": "我不知道要怎麼證明一個數列收斂。"},
        {"role": "assistant", "content": "換個問法：如果一個數列能證明遞增又有上界，會有什麼結論？"},
        {"role": "user", "content": "還是不太確定要怎麼證遞增和有界。"},
        {"role": "assistant", "content": "這裡要用單調有界定理。展開 $(1+1/n)^n$ 後，你能看出它為何遞增、又為何有上界嗎？"},
        {"role": "user", "content": "二項式展開後每項隨 n 增大都變大，且 1/k!≤1/2^(k-1) 給出上界 3。"},
        {"role": "assistant", "content": "完全正確，你自己把遞增和有上界都證出來了。"},
    ]},

    # ===== C4：無正式定理名稱，純構造想法 =====
    {"problem_id": "C4", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "Cauchy 均值定理要用兩個函數 f,g，我完全不知道怎麼下手。"},
        {"role": "assistant", "content": "分開對 $f,g$ 各用一次均值定理會得到兩個不同的 $c$。你會怎麼讓兩者共用同一個 $c$？"},
        {"role": "user", "content": "我不知道要怎麼讓它們共用同一個點。"},
        {"role": "assistant", "content": "換個角度：能不能把 $f,g$ 組合成單一一個函數，只需要對它用一次 Rolle 定理？"},
        {"role": "user", "content": "還是想不出來要怎麼組合。"},
        {"role": "assistant", "content": "試著把 $f,g$ 加權相減，湊出一個在 $a,b$ 兩端函數值相等的組合函數。你會怎麼寫？"},
        {"role": "user", "content": "$h(x)=(f(b)-f(a))g(x)-(g(b)-g(a))f(x)$，這樣端點值應該會相等。"},
        {"role": "assistant", "content": "很好，驗證 $h(a)=h(b)$ 後，對 $h$ 用 Rolle 定理，$h'(c)=0$ 能給你什麼？"},
        {"role": "user", "content": "展開得 $(f(b)-f(a))g'(c)=(g(b)-g(a))f'(c)$，除一下就是要證的等式！"},
        {"role": "assistant", "content": "完全正確，你自己找到了這個組合函數。"},
    ]},

    # ===== D1：無正式定理名稱，純反證想法 =====
    {"problem_id": "D1", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "積分是 0 就要證函數恆為 0，我不知道怎麼從積分推回逐點的性質。"},
        {"role": "assistant", "content": "試試反證法：若某點 $f(x_0)>0$，你能不能用連續性，把這個單點的正值變成一整段都是正的？"},
        {"role": "user", "content": "我不知道連續性要怎麼用在這裡。"},
        {"role": "assistant", "content": "換個角度：連續函數在一點附近的值，會不會突然從正變成離很遠的數？"},
        {"role": "user", "content": "還是想不出來要怎麼具體操作。"},
        {"role": "assistant", "content": "試著用連續性的定義：取 $\\varepsilon=f(x_0)/2$，看看 $x_0$ 附近一整段的函數值會被限制在什麼範圍。"},
        {"role": "user", "content": "附近一段會有 $f(x)>f(x_0)/2>0$，因為 $f\\ge0$，這段的積分會是正的！"},
        {"role": "assistant", "content": "很好，這跟 $\\int_a^b f=0$ 有什麼衝突？"},
        {"role": "user", "content": "$\\int_a^b f$ 至少大於這一段的正積分，跟等於 0 矛盾，所以沒有這種 $x_0$，$f\\equiv0$。"},
        {"role": "assistant", "content": "完全正確，你自己把連續性轉成了「一段都是正的」這個關鍵想法。"},
    ]},

    # ===== E2：三角不等式 =====
    {"problem_id": "E2", "persona": "confused", "kind": "hint", "turns": [
        {"role": "user", "content": "收斂數列是 Cauchy 數列，這兩個定義我搞不清楚要怎麼接。"},
        {"role": "assistant", "content": "已知 $a_n\\to L$，目標是估計 $|a_n-a_m|$。你能不能先把它跟 $L$ 扯上關係？"},
        {"role": "user", "content": "我不知道要怎麼把 a_n 和 a_m 一起跟 L 連起來。"},
        {"role": "assistant", "content": "換個想法：$a_n-a_m$ 能不能先加上再減去 $L$，湊出兩個你已知會變小的量？"},
        {"role": "user", "content": "還是想不出來怎麼湊。"},
        {"role": "assistant", "content": "這裡要用三角不等式。你能寫出 $|a_n-a_m|$ 被 $|a_n-L|$ 和 $|a_m-L|$ 夾住的式子嗎？"},
        {"role": "user", "content": "$|a_n-a_m|\\le|a_n-L|+|L-a_m|$，各壓到 $\\varepsilon/2$ 就得 $<\\varepsilon$！"},
        {"role": "assistant", "content": "完全正確，三角不等式正是連接兩個定義的橋樑。"},
    ]},
]
