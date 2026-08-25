# -*- coding: utf-8 -*-
"""主題 B 核心對話（B1-B10 × 3 Persona）。內容由 Claude 手寫。"""

DIALOGUES = [
    # ===== B1: IVT (f(a)f(b)<0) =====
    {"problem_id": "B1", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "這題直覺上圖形會穿過 x 軸，但我不知道怎麼嚴謹證明有這個 c。"},
        {"role": "assistant", "content": "直覺沒錯，關鍵是把「穿過零點」用一個集合刻畫出來。不妨設 $f(a)<0<f(b)$，你能定義一個蒐集「$f$ 為負的點」的集合嗎？"},
        {"role": "user", "content": "可以設 S = {x∈[a,b] : f(x)<0}，a 在裡面所以非空。"},
        {"role": "assistant", "content": "很好，$S$ 非空又有上界 $b$。由實數完備性，$S$ 有什麼？把它取為候選的 $c$。"},
        {"role": "user", "content": "有上確界，令 c = sup S。"},
        {"role": "assistant", "content": "正是。接著用反證：若 $f(c)>0$，由連續性 $c$ 左側附近 $f$ 也 $>0$，這會和 $c=\\sup S$ 起什麼衝突？"},
        {"role": "user", "content": "那 c 左邊有一段都 >0，表示更小的數也是 S 的上界，跟 c 是最小上界矛盾。"},
        {"role": "assistant", "content": "對。再排除 $f(c)<0$ 的情形後就剩 $f(c)=0$。你能說說 $f(c)<0$ 為何也矛盾嗎？"},
        {"role": "user", "content": "若 f(c)<0，連續性使 c 右邊也 <0，那 S 裡有比 c 大的點，跟 c 是上界矛盾。所以 f(c)=0。"},
        {"role": "assistant", "content": "完全正確。核心是「用 sup 抓臨界點、再用連續性兩面夾殺」，這是 IVT 的完備性證法。"},
    ]},
    {"problem_id": "B1", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f 連續、一負一正，直接由介值定理就有 c 使 f(c)=0，證完。"},
        {"role": "assistant", "content": "但本題要求「證明」介值定理這個結論本身，不能直接引用它，否則是循環論證。我們得回到更基本的工具：實數的哪個公理能提供臨界點?"},
        {"role": "user", "content": "喔對，不能用要證的東西。應該用完備性——上確界存在。"},
        {"role": "assistant", "content": "正是。設 $f(a)<0<f(b)$，令 $S=\\{x:f(x)<0\\}$，$c=\\sup S$。你能用反證排除 $f(c)>0$ 嗎?"},
        {"role": "user", "content": "若 f(c)>0，連續性讓 c 左邊也 >0，那有更小的上界，跟 c=sup S 矛盾。"},
        {"role": "assistant", "content": "很好，同理排除 $f(c)<0$。教訓：要證的定理不能拿來當工具，須退回完備性公理。"},
    ]},
    {"problem_id": "B1", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "我設 S={x:f(x)<0}，c=sup S，再用連續性反證 f(c) 不能為正也不能為負。"},
        {"role": "assistant", "content": "路線正確。你如何確保最終得到的 $c$ 落在開區間 $(a,b)$ 而非端點?"},
        {"role": "user", "content": "因為 f(a)<0、f(b)>0 都非零，而 f(c)=0，所以 c 不等於 a 也不等於 b，故 c∈(a,b)。"},
        {"role": "assistant", "content": "正確，端點值非零就把 $c$ 逼進開區間。你對完備性證法掌握得很完整。"},
    ]},

    # ===== B2: EVT =====
    {"problem_id": "B2", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "最大值定理…我知道結論，但證明要從哪裡開始都不知道。"},
        {"role": "assistant", "content": "把目標拆成兩步會清楚很多。第一步通常要先證 $f$ 在 $[a,b]$ 上具有什麼性質，才談得上「最大值」是有限的?"},
        {"role": "user", "content": "要先證 f 有界（有上界），不然上確界會是無窮大。"},
        {"role": "assistant", "content": "正是。若 $f$ 無上界，就能取到 $f(x_n)>n$。$\\{x_n\\}$ 在有界閉區間裡，哪個定理保證它有收斂子列?"},
        {"role": "user", "content": "Bolzano-Weierstrass 定理，取到子列 x_{n_k}→x*∈[a,b]。"},
        {"role": "assistant", "content": "很好，這和 $f(x_{n_k})\\to+\\infty$ 有何衝突，從而證得有界?"},
        {"role": "user", "content": "連續性給 f(x_{n_k})→f(x*) 有限，跟趨無窮矛盾，所以 f 有界。"},
        {"role": "assistant", "content": "對。第二步令 $M=\\sup f$，取 $f(y_n)\\to M$。同樣用 B-W 抽子列，最後靠連續性能得到什麼?"},
        {"role": "user", "content": "y_{n_k}→y*，連續性給 f(y*)=lim f(y_{n_k})=M，所以在 y* 達到最大值 M。"},
        {"role": "assistant", "content": "完全正確。兩步都靠「B-W 抽子列 + 連續性傳遞極限」，這是最大值定理的骨架。"},
    ]},
    {"problem_id": "B2", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "令 M=sup f，因為 sup 存在，所以一定有某點 f 取到 M。"},
        {"role": "assistant", "content": "$\\sup$ 存在只保證「可任意逼近 $M$」，未必真被取到。你能舉一個上確界取不到的函數例子嗎?"},
        {"role": "user", "content": "像 f(x)=x 在開區間 (0,1)，sup=1 但取不到。所以要用到閉區間和連續性。"},
        {"role": "assistant", "content": "正是。那就取 $f(y_n)\\to M$，$\\{y_n\\}\\subset[a,b]$ 用哪個定理抽收斂子列?"},
        {"role": "user", "content": "Bolzano-Weierstrass，y_{n_k}→y*∈[a,b]，連續性給 f(y*)=M。"},
        {"role": "assistant", "content": "正確。教訓：$\\sup$ 只是最小上界、未必被達到；閉區間 + 連續性才保證取到。"},
    ]},
    {"problem_id": "B2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "先反證有界，再取逼近序列 f(y_n)→M，用 B-W 抽子列加連續性得 f(y*)=M。"},
        {"role": "assistant", "content": "結構完整。你的證明用到了哪兩個「閉區間 [a,b]」不可或缺的性質?"},
        {"role": "user", "content": "一是有界，讓 B-W 能用；二是閉，讓子列極限 y* 仍留在 [a,b] 裡。"},
        {"role": "assistant", "content": "正確，正是有界＋閉（緊緻）缺一不可。你清楚每個假設的用途。"},
    ]},

    # ===== B3: Heine-Cantor =====
    {"problem_id": "B3", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "一致連續和普通連續的差別我常搞混，這題不知怎麼證。"},
        {"role": "assistant", "content": "一致連續要求同一個 $\\delta$ 對所有點通用。直接證很難，改用反證：若「不」一致連續，否定命題長什麼樣?"},
        {"role": "user", "content": "存在某個 ε_0>0，對每個 n 都能找到 x_n,y_n 使 |x_n−y_n|<1/n 但 |f(x_n)−f(y_n)|≥ε_0。"},
        {"role": "assistant", "content": "很好，這就造出兩個序列。$\\{x_n\\}\\subset[a,b]$，哪個定理能抽出收斂子列?"},
        {"role": "user", "content": "Bolzano-Weierstrass，x_{n_k}→x*。"},
        {"role": "assistant", "content": "正是。因 $|x_{n_k}-y_{n_k}|<1/n_k\\to0$，$y_{n_k}$ 會趨向哪裡?"},
        {"role": "user", "content": "y_{n_k} 也→x*，因為兩者距離趨 0。"},
        {"role": "assistant", "content": "對。那 $f(x_{n_k})$ 與 $f(y_{n_k})$ 由連續性各趨向什麼，如何和 $\\ge\\varepsilon_0$ 矛盾?"},
        {"role": "user", "content": "兩者都→f(x*)，差→0，跟 |f(x_n)−f(y_n)|≥ε_0 矛盾，所以一致連續。"},
        {"role": "assistant", "content": "完全正確。反證 + B-W + 連續性傳遞，這是 Heine-Cantor 的標準路線。"},
    ]},
    {"problem_id": "B3", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f 在每個點連續，所以對每個點都有 δ，這樣就是一致連續了。"},
        {"role": "assistant", "content": "問題正在這裡：逐點的 $\\delta$ 可能隨點越變越小。「一致」要求存在一個對所有點都行的 $\\delta$。要證這點，用反證會如何開頭?"},
        {"role": "user", "content": "假設不一致連續，就有 ε_0，對每個 n 有 x_n,y_n，|x_n−y_n|<1/n 但差≥ε_0。"},
        {"role": "assistant", "content": "正是。接著對 $\\{x_n\\}$ 用 Bolzano-Weierstrass，會得到什麼樣的子列?"},
        {"role": "user", "content": "x_{n_k}→x*，且因距離→0，y_{n_k} 也→x*。連續性讓兩者的像都→f(x*)，差→0，矛盾。"},
        {"role": "assistant", "content": "正確。教訓：逐點連續的 $\\delta$ 不必通用，「一致」要靠緊緻性（B-W）才能保證。"},
    ]},
    {"problem_id": "B3", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "反證：造出 |x_n−y_n|<1/n 但差≥ε_0 的序列，B-W 抽子列後兩序列同極限，連續性導出矛盾。"},
        {"role": "assistant", "content": "非常完整。這個證明在哪一步「本質地」用到了區間是閉且有界，而非開區間?"},
        {"role": "user", "content": "B-W 抽出的極限 x* 要留在區間內、且 f 在該點連續；開區間的話 x* 可能跑到端點外，連續性用不上。"},
        {"role": "assistant", "content": "正確，這正解釋了為何 f(x)=1/x 在 (0,1) 連續卻不一致連續。理解到位。"},
    ]},

    # ===== B4: x² not uniformly continuous =====
    {"problem_id": "B4", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "要證「不」一致連續，我不知道否定命題該怎麼寫。"},
        {"role": "assistant", "content": "把一致連續的定義取否定即可。你能寫出「存在 $\\varepsilon_0$，對任意 $\\delta$…」的完整否定句嗎?"},
        {"role": "user", "content": "存在 ε_0>0，對任意 δ>0，都能找到 x,y 使 |x−y|<δ 但 |x²−y²|≥ε_0。"},
        {"role": "assistant", "content": "很好。關鍵在 $|x^2-y^2|=|x-y||x+y|$，其中哪個因子在遠處會失控變大?"},
        {"role": "user", "content": "|x+y| 會隨著 x,y 變大而無界。"},
        {"role": "assistant", "content": "正是。那就固定 $|x-y|=\\delta/2$，把 $x,y$ 取在很大的地方，讓 $|x-y||x+y|$ 大過 $\\varepsilon_0$。你會怎麼取?"},
        {"role": "user", "content": "取 x=n+δ/2、y=n，|x−y|=δ/2<δ，而 |x²−y²|=(δ/2)(2n+δ/2)≥δn，取 n 大就 ≥1。"},
        {"role": "assistant", "content": "完全正確，取 $\\varepsilon_0=1$ 即成。本質是 $|x+y|$ 無界使同一 $\\delta$ 無法通用。"},
    ]},
    {"problem_id": "B4", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "x² 在每點連續，所以它一致連續，這題是不是寫錯了?"},
        {"role": "assistant", "content": "逐點連續不等於一致連續。試著檢驗：固定 $\\delta$，當 $x,y$ 一起變大，$|x^2-y^2|$ 還能被 $\\delta$ 控制住嗎?"},
        {"role": "user", "content": "|x²−y²|=|x−y||x+y|，就算 |x−y| 固定小，|x+y| 變大時整體會爆掉。所以不一致連續。"},
        {"role": "assistant", "content": "正是。那就具體取 $x=n+\\delta/2,\\ y=n$，$|x-y|<\\delta$ 但 $|x^2-y^2|$ 如何?"},
        {"role": "user", "content": "≥δn，取 n 夠大就 ≥1=ε_0，所以否定命題成立，x² 不一致連續。"},
        {"role": "assistant", "content": "正確。教訓：一致連續是比逐點連續更強的整體性質，$\\mathbb{R}$ 上的 $x^2$ 就是反例。"},
    ]},
    {"problem_id": "B4", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "取 ε_0=1，x=n+δ/2、y=n，則 |x−y|=δ/2<δ 而 |x²−y²|=δ(n+δ/4)≥δn≥1（n 夠大）。"},
        {"role": "assistant", "content": "反例造得很準。為何這個現象在有界區間 $[0,1]$ 上就不會發生?"},
        {"role": "user", "content": "因為 [0,1] 上 |x+y|≤2 有界，$x²$ 是 Lipschitz，自然一致連續；無界域才會失控。"},
        {"role": "assistant", "content": "正確，你點出了問題的根源在定義域無界。分析得非常清楚。"},
    ]},

    # ===== B5: ε-δ x² continuous at a =====
    {"problem_id": "B5", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "在一般點 a 證 x² 連續，跟在 x=2 那題好像但又不一樣，我卡住了。"},
        {"role": "assistant", "content": "做法一致。先寫 $|x^2-a^2|=|x-a||x+a|$，其中變動因子是 $|x+a|$。若先假設 $|x-a|<1$，$|x+a|$ 有什麼上界?"},
        {"role": "user", "content": "|x+a| ≤ |x−a|+2|a| < 1+2|a|。"},
        {"role": "assistant", "content": "很好，所以 $|x^2-a^2|<(1+2|a|)|x-a|$。要它 $<\\varepsilon$，$\\delta$ 該怎麼取?"},
        {"role": "user", "content": "取 δ = min{1, ε/(1+2|a|)}。"},
        {"role": "assistant", "content": "完全正確。注意這裡的 $\\delta$ 依賴 $a$，這與一致連續的差別正在於此。"},
    ]},
    {"problem_id": "B5", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "我寫 |x+a| ≤ 2|a|，然後取 δ=ε/(2|a|)。"},
        {"role": "assistant", "content": "$|x+a|\\le2|a|$ 只在 $x$ 恰好等於 $a$ 附近才近似成立，但 $x$ 可比 $a$ 大。你能用 $|x-a|<1$ 給出嚴謹的上界嗎?"},
        {"role": "user", "content": "|x+a|=|(x−a)+2a|≤|x−a|+2|a|<1+2|a|。原本的 2|a| 少算了 |x−a| 那塊。"},
        {"role": "assistant", "content": "正是。修正後 $\\delta$ 該取什麼才能同時保住 $|x-a|<1$ 這個預設界?"},
        {"role": "user", "content": "取 δ=min{1, ε/(1+2|a|)}。"},
        {"role": "assistant", "content": "正確。教訓：估 $|x+a|$ 要把 $x$ 對 $a$ 的偏移算進去，並用 min 保住預設界。"},
    ]},
    {"problem_id": "B5", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "設 |x−a|<1 得 |x+a|<1+2|a|，取 δ=min{1, ε/(1+2|a|)}。"},
        {"role": "assistant", "content": "完全正確。從這個 $\\delta$ 隨 $a$ 變大而變小，你能看出 $x^2$ 為何在 $\\mathbb{R}$ 上不一致連續嗎?"},
        {"role": "user", "content": "能，δ 含 1/(1+2|a|)，a 越大 δ 越小，找不到對所有 a 通用的 δ，所以不一致連續。"},
        {"role": "assistant", "content": "正確，你把逐點與一致連續的關鍵差異一眼看穿。非常好。"},
    ]},

    # ===== B6: sequential criterion =====
    {"problem_id": "B6", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "要從 ε-δ 連續推出「序列的像收斂」，我不知道怎麼把兩個定義接起來。"},
        {"role": "assistant", "content": "把兩個定義並排就會通。目標是 $f(x_n)\\to f(x_0)$，先由 $f$ 在 $x_0$ 連續，對給定 $\\varepsilon$ 你會得到什麼?"},
        {"role": "user", "content": "存在 δ>0，使 |x−x_0|<δ 時 |f(x)−f(x_0)|<ε。"},
        {"role": "assistant", "content": "很好，$\\delta$ 現在是已知的。再用 $x_n\\to x_0$，對「這個」$\\delta$ 你能得到什麼?"},
        {"role": "user", "content": "存在 N，使 n≥N 時 |x_n−x_0|<δ。"},
        {"role": "assistant", "content": "正是，把兩者串起來。$n\\ge N$ 時 $|f(x_n)-f(x_0)|$ 會如何?"},
        {"role": "user", "content": "<ε，所以 f(x_n)→f(x_0)。"},
        {"role": "assistant", "content": "完全正確。訣竅是「先由連續取出 $\\delta$，再拿 $\\delta$ 去餵序列收斂」。"},
    ]},
    {"problem_id": "B6", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "先取序列給的 N 得到某個 δ，再用連續性…咦順序怪怪的。"},
        {"role": "assistant", "content": "你察覺到順序問題了。$\\delta$ 是哪個定義先產生的，才能拿去用在另一個?"},
        {"role": "user", "content": "應該先由連續性產生 δ（依 ε），再用 x_n→x_0 對這個 δ 找 N。我剛剛倒過來了。"},
        {"role": "assistant", "content": "正是。修正順序後，$n\\ge N\\Rightarrow|x_n-x_0|<\\delta\\Rightarrow$ 什麼?"},
        {"role": "user", "content": "⇒ |f(x_n)−f(x_0)|<ε，得證 f(x_n)→f(x_0)。"},
        {"role": "assistant", "content": "正確。教訓：$\\delta$ 由連續性先生成，序列收斂再去匹配這個 $\\delta$，順序不可顛倒。"},
    ]},
    {"problem_id": "B6", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "由連續取 δ(ε)，再由 x_n→x_0 對此 δ 取 N，串起來得 |f(x_n)−f(x_0)|<ε。"},
        {"role": "assistant", "content": "完全正確。這是「連續⇒保序列極限」的一個方向；反方向（用序列刻畫連續）通常怎麼證?"},
        {"role": "user", "content": "反方向用反證：若不連續就有 ε_0，造出 x_n→x_0 但 |f(x_n)−f(x_0)|≥ε_0 的序列，矛盾。"},
        {"role": "assistant", "content": "正確，你完整掌握了連續性的序列刻畫（兩個方向）。"},
    ]},

    # ===== B7: odd polynomial has real root =====
    {"problem_id": "B7", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "奇次多項式一定有實根，我知道結論但不知怎麼證。"},
        {"role": "assistant", "content": "想用介值定理，就得先找到一正一負的函數值。先看 $x\\to+\\infty$，奇次首項主宰時 $p(x)$ 趨向什麼?"},
        {"role": "user", "content": "首項是奇次 x^(2k+1)，x→+∞ 時 p(x)→+∞。"},
        {"role": "assistant", "content": "很好。那麼綜合 $x\\to+\\infty$ 趨正、$x\\to-\\infty$ 趨負，能否各找到一個使 $p$ 為正、為負的點？"},
        {"role": "user", "content": "x→−∞ 時 p(x)→−∞。所以存在 b 使 p(b)>0、a<b 使 p(a)<0。"},
        {"role": "assistant", "content": "正是。$p$ 在 $[a,b]$ 連續且端點異號，用哪個定理收尾?"},
        {"role": "user", "content": "介值定理，存在 c∈(a,b) 使 p(c)=0。"},
        {"role": "assistant", "content": "完全正確。奇次的關鍵就在兩端趨向 $\\pm\\infty$，製造出介值定理所需的異號。"},
    ]},
    {"problem_id": "B7", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "多項式連續，所以由介值定理一定有根。"},
        {"role": "assistant", "content": "介值定理要先有「一正一負的兩個函數值」當前提，你還沒提供。哪個特徵保證奇次多項式能取到異號值?"},
        {"role": "user", "content": "喔，要看兩端行為。x→+∞ 時 p→+∞，x→−∞ 時 p→−∞，所以有正有負。"},
        {"role": "assistant", "content": "正是。那偶次多項式（如 $x^2+1$）為何這招會失效?"},
        {"role": "user", "content": "偶次兩端同號（都→+∞），可能整條都在 x 軸上方，沒有異號，就未必有實根。"},
        {"role": "assistant", "content": "正確。教訓：介值定理需先驗證異號前提，而「奇次」正是提供此前提的關鍵。"},
    ]},
    {"problem_id": "B7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "由奇次首項知 p(+∞)=+∞、p(−∞)=−∞，取 a,b 使異號，IVT 給根。"},
        {"role": "assistant", "content": "簡潔正確。要把「$x\\to\\pm\\infty$ 時首項主宰」寫嚴謹，通常怎麼處理低次項?"},
        {"role": "user", "content": "提出 x^(2k+1)，寫成 x^(2k+1)(1+c_{2k}/x+…)，括號→1，故符號由 x^(2k+1) 決定。"},
        {"role": "assistant", "content": "正確，提出首項再論證括號趨 1，是嚴謹化極限行為的標準手法。很好。"},
    ]},

    # ===== B8: boundedness =====
    {"problem_id": "B8", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "有界性定理…要怎麼證閉區間上連續函數一定不會跑到無窮?"},
        {"role": "assistant", "content": "用反證會很自然。若 $f$ 無界，你能對每個 $n$ 造出什麼樣的點 $x_n$?"},
        {"role": "user", "content": "存在 x_n∈[a,b] 使 |f(x_n)|>n。"},
        {"role": "assistant", "content": "很好。$\\{x_n\\}$ 在有界閉區間裡，哪個定理保證存在極限仍落在 $[a,b]$ 內的收斂子列?"},
        {"role": "user", "content": "Bolzano-Weierstrass，x_{n_k}→x*，因為 [a,b] 是閉的，x*∈[a,b]。"},
        {"role": "assistant", "content": "正是。連續性讓 $f(x_{n_k})$ 收斂，但它同時滿足 $|f(x_{n_k})|>n_k$，矛盾在哪?"},
        {"role": "user", "content": "收斂序列必有界，但 |f(x_{n_k})|>n_k→∞ 無界，矛盾。所以 f 有界。"},
        {"role": "assistant", "content": "完全正確。有界性與最大值定理共用同一套「B-W + 連續性」骨架。"},
    ]},
    {"problem_id": "B8", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f 連續所以每個 f(x) 都是有限值，因此 f 有界。"},
        {"role": "assistant", "content": "每點有限（逐點）不等於整體有界。$f(x)=1/x$ 在 $(0,1)$ 每點都有限，卻無界。差別在定義域的什麼性質?"},
        {"role": "user", "content": "差在區間要閉且有界。用反證：無界的話造 |f(x_n)|>n。"},
        {"role": "assistant", "content": "正是。$\\{x_n\\}$ 抽收斂子列後，靠閉性與連續性如何導出矛盾?"},
        {"role": "user", "content": "x_{n_k}→x*∈[a,b]，f(x_{n_k})→f(x*) 有界，跟 >n_k 矛盾。"},
        {"role": "assistant", "content": "正確。教訓：逐點有限 ≠ 整體有界；閉區間（緊緻）才是關鍵。"},
    ]},
    {"problem_id": "B8", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "反證：|f(x_n)|>n，B-W 抽 x_{n_k}→x*∈[a,b]，連續性給收斂矛盾無界。"},
        {"role": "assistant", "content": "正確。有界性定理和最大值定理的證明幾乎相同，兩者的邏輯先後關係是什麼?"},
        {"role": "user", "content": "先證有界，才能談 sup f 是有限的，最大值定理的第二步才站得住。"},
        {"role": "assistant", "content": "正確，有界性是最大值定理的前置引理。你把邏輯層次理得很清楚。"},
    ]},

    # ===== B9: composition continuity =====
    {"problem_id": "B9", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "合成函數連續，要串兩個 ε-δ，我每次都會弄亂。"},
        {"role": "assistant", "content": "先設 $y_0=g(x_0)$，由外層 $f$ 在 $y_0$ 連續，對給定 $\\varepsilon$ 你會得到怎樣的 $\\eta$?"},
        {"role": "user", "content": "存在 η>0，使 |y−y_0|<η 時 |f(y)−f(y_0)|<ε。"},
        {"role": "assistant", "content": "很好，把這個 $\\eta$ 當成內層要達到的目標。由 $g$ 在 $x_0$ 連續，對 $\\eta$ 你能取到什麼?"},
        {"role": "user", "content": "存在 δ>0，使 |x−x_0|<δ 時 |g(x)−y_0|<η。"},
        {"role": "assistant", "content": "正是。把兩條鎖鏈接起來：$|x-x_0|<\\delta$ 會依序推出什麼?"},
        {"role": "user", "content": "⇒ |g(x)−y_0|<η ⇒ |f(g(x))−f(y_0)|<ε，所以合成連續。"},
        {"role": "assistant", "content": "完全正確。順序是「外層產生 $\\eta$、內層用 $\\eta$ 產生 $\\delta$」，方向不能顛倒。"},
    ]},
    {"problem_id": "B9", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "由 g 連續取 δ 得到某個 η，再用 f 連續，這樣接起來。"},
        {"role": "assistant", "content": "順序反了。$\\eta$ 是外層 $f$ 對 $\\varepsilon$ 產生的門檻，應該先有它，內層 $g$ 才知道要逼近多近。你能重排嗎?"},
        {"role": "user", "content": "對，先由 f 連續（依 ε）取 η，再由 g 連續（依 η）取 δ。"},
        {"role": "assistant", "content": "正是。這樣 $|x-x_0|<\\delta$ 的推理鏈如何一路推到 $\\varepsilon$?"},
        {"role": "user", "content": "|x−x_0|<δ ⇒ |g(x)−y_0|<η ⇒ |f(g(x))−f(y_0)|<ε。"},
        {"role": "assistant", "content": "正確。教訓：合成連續要「由外而內」設門檻，$\\eta$ 先於 $\\delta$。"},
    ]},
    {"problem_id": "B9", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "由 f 在 y_0=g(x_0) 連續取 η(ε)，再由 g 在 x_0 連續取 δ(η)，鏈式推得 ε。"},
        {"role": "assistant", "content": "完全正確。若改用序列準則來證合成連續，會不會更簡潔?"},
        {"role": "user", "content": "會，x_n→x_0 ⇒ g(x_n)→g(x_0)（g 連續）⇒ f(g(x_n))→f(g(x_0))（f 連續），兩次套用即可。"},
        {"role": "assistant", "content": "正確，序列準則讓合成連續變成兩次極限傳遞，非常乾淨。掌握得很好。"},
    ]},

    # ===== B10: chord theorem =====
    {"problem_id": "B10", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "要找 c 使 f(c)=f(c+1/2)，我完全不知道怎麼把兩個點的值扯上關係。"},
        {"role": "assistant", "content": "把「兩點值相等」轉成「某函數為零」會清楚許多。你能定義一個 $g(x)$ 使 $g(c)=0$ 恰好對應 $f(c)=f(c+\\frac12)$ 嗎?"},
        {"role": "user", "content": "設 g(x)=f(x+1/2)−f(x)，那 g(c)=0 就是 f(c)=f(c+1/2)。"},
        {"role": "assistant", "content": "很好，$g$ 定義在 $[0,\\frac12]$ 上連續。算算 $g(0)+g(\\frac12)$ 會得到什麼?"},
        {"role": "user", "content": "g(0)=f(1/2)−f(0)，g(1/2)=f(1)−f(1/2)，相加=f(1)−f(0)=0。"},
        {"role": "assistant", "content": "正是關鍵！$g(0)+g(\\frac12)=0$ 意味兩者的符號有什麼關係，接著用哪個定理?"},
        {"role": "user", "content": "g(0) 和 g(1/2) 異號（或其一為 0），用介值定理得存在 c 使 g(c)=0。"},
        {"role": "assistant", "content": "完全正確。核心手法是「造差函數 $g$、算端點和為零、用 IVT」。"},
    ]},
    {"problem_id": "B10", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "我設 g(x)=f(x+1/2)−f(x)，然後說 g(0)=g(1/2)，用 Rolle 得 g'(c)=0。"},
        {"role": "assistant", "content": "先檢查一件事：題目只給連續、沒給可微，你打算套用的 Rolle 定理在這裡能用嗎？"},
        {"role": "user", "content": "算一下 g(0)=f(1/2)−f(0)、g(1/2)=f(1)−f(1/2)，不一定相等；而且沒可微，不能用 Rolle。"},
        {"role": "assistant", "content": "正是。但這兩者相加會得到什麼特別的值，讓你改用介值定理?"},
        {"role": "user", "content": "g(0)+g(1/2)=f(1)−f(0)=0，所以異號，用 IVT 得 g(c)=0。"},
        {"role": "assistant", "content": "正確。教訓：只有連續性時該用 IVT，別誤用需要可微的 Rolle；且端點值要實際算。"},
    ]},
    {"problem_id": "B10", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "設 g(x)=f(x+1/2)−f(x)，算得 g(0)+g(1/2)=f(1)−f(0)=0，故異號，IVT 給 c。"},
        {"role": "assistant", "content": "非常俐落。若 $g(0)=0$ 這個邊界情形出現，你的論證要如何補一句?"},
        {"role": "user", "content": "若 g(0)=0 直接取 c=0；否則 g(0) 與 g(1/2)=−g(0) 嚴格異號，IVT 給內部的 c。"},
        {"role": "assistant", "content": "正確，補上邊界情形讓證明滴水不漏。這題你處理得很嚴謹。"},
    ]},
]
