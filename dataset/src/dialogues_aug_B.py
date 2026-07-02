# -*- coding: utf-8 -*-
"""主題 B 擴充對話：每題 1 條第二類錯誤變體 + 3 條關鍵步驟短對話。內容由 Claude 手寫。"""

DIALOGUES = [
    # ---- B1 ----
    {"problem_id": "B1", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我令 S={x:f(x)<0}，取 c=inf S 當候選零點。"},
        {"role": "assistant", "content": "由 $f(a)<0$，$a\\in S$，取 $\\inf S$ 恐怕就是 $a$；要抓到「由負轉正」的臨界點，該改取 $\\sup$ 還是 $\\inf$？"},
        {"role": "user", "content": "應該取 sup S，因為那是負值區的右邊界，剛好在轉正處。"},
        {"role": "assistant", "content": "正是。取 $c=\\sup S$ 後，用連續性反證 $f(c)$ 不能為正也不能為負，得什麼？"},
        {"role": "user", "content": "得 f(c)=0。"},
        {"role": "assistant", "content": "正確。教訓：臨界零點是負值集的上確界，不是下確界。"},
    ]},
    {"problem_id": "B1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼要用上確界，而不是直接找零點？"},
        {"role": "assistant", "content": "因為我們還沒有 IVT 可用（正要證它），得靠完備性提供臨界點。$\\sup S$ 存在依賴什麼？"},
        {"role": "user", "content": "依賴實數完備性（最小上界公理）。"},
        {"role": "assistant", "content": "正確，完備性是這個證法的基石。"},
    ]},
    {"problem_id": "B1", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "如何確保得到的 c 在開區間 (a,b) 內？"},
        {"role": "assistant", "content": "由端點值的符號。$f(a),f(b)$ 都非零，而 $f(c)=0$，這逼出 $c$ 不等於誰？"},
        {"role": "user", "content": "不等於 a、也不等於 b，故 c∈(a,b)。"},
        {"role": "assistant", "content": "正確，端點非零把 $c$ 逼進開區間。"},
    ]},
    {"problem_id": "B1", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "反證 f(c)>0 時為什麼會矛盾？"},
        {"role": "assistant", "content": "由連續性，$f(c)>0$ 會使 $c$ 左側附近也 $>0$。那比 $c$ 小的數會變成 $S$ 的什麼，與 $c=\\sup S$ 衝突？"},
        {"role": "user", "content": "變成 S 的上界，比 c 小卻是上界，跟 c 是最小上界矛盾。"},
        {"role": "assistant", "content": "正確，這就排除了 $f(c)>0$。"},
    ]},

    # ---- B2 ----
    {"problem_id": "B2", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "f 連續在有限區間，值域也是有限區間，所以有最大值。"},
        {"role": "assistant", "content": "「值域是有限區間」本身要證，且開區間如 $(0,1)$ 就取不到端點。要嚴謹，第一步該先證 $f$ 具備什麼？"},
        {"role": "user", "content": "先證 f 有界（有上界），才能談有限的 sup。"},
        {"role": "assistant", "content": "正是。接著取 $f(y_n)\\to M=\\sup f$，用哪個定理抽子列並靠連續性達到 $M$？"},
        {"role": "user", "content": "Bolzano-Weierstrass 抽 y_{n_k}→y*，連續性給 f(y*)=M。"},
        {"role": "assistant", "content": "正確。教訓：不能空言值域有界，要用 B-W + 連續性建構取到 $M$ 的點。"},
    ]},
    {"problem_id": "B2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 sup 存在還不夠，要證「取到」？"},
        {"role": "assistant", "content": "$\\sup$ 只保證可任意逼近。想想 $f(x)=x$ 於 $(0,1)$，$\\sup=1$ 卻取不到。要取到得靠什麼組合？"},
        {"role": "user", "content": "靠閉區間＋連續性（B-W 抽子列）。"},
        {"role": "assistant", "content": "正確，這正是最大值定理的核心。"},
    ]},
    {"problem_id": "B2", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼子列極限 y* 一定落在 [a,b]？"},
        {"role": "assistant", "content": "因為 $[a,b]$ 具有什麼拓撲性質，使收斂子列的極限不會跑出去？"},
        {"role": "user", "content": "閉性，閉集包含其所有極限點。"},
        {"role": "assistant", "content": "正確，閉性保住了 y* 在區間內。"},
    ]},
    {"problem_id": "B2", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "第一步「證有界」的反證怎麼開始？"},
        {"role": "assistant", "content": "假設無上界，則能對每個 $n$ 取到 $f(x_n)>n$。接著對 $\\{x_n\\}$ 用哪個定理？"},
        {"role": "user", "content": "Bolzano-Weierstrass，抽收斂子列後連續性導出矛盾。"},
        {"role": "assistant", "content": "正確，無界假設會與連續極限有限相衝突。"},
    ]},

    # ---- B3 ----
    {"problem_id": "B3", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我直接對每個 ε 找一個 δ(x)，然後取所有 δ(x) 的最小值當通用 δ。"},
        {"role": "assistant", "content": "$\\{\\delta(x)\\}$ 有無限多個，其下確界可能是 $0$，不能當 $\\delta$。要證一致連續，改用什麼策略較保險？"},
        {"role": "user", "content": "用反證法，假設不一致連續，造出反例序列。"},
        {"role": "assistant", "content": "正是。造出 $|x_n-y_n|<1/n$ 但差 $\\ge\\varepsilon_0$ 後，用哪個定理與連續性導矛盾？"},
        {"role": "user", "content": "Bolzano-Weierstrass 抽子列，兩序列同極限，連續性使差→0，矛盾。"},
        {"role": "assistant", "content": "正確。教訓：無限多 $\\delta(x)$ 取 inf 可能為 0，故用反證 + 緊緻性。"},
    ]},
    {"problem_id": "B3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "一致連續和逐點連續差在哪？"},
        {"role": "assistant", "content": "差在 $\\delta$ 能否對「所有點」通用。逐點連續的 $\\delta$ 可以隨誰而變？"},
        {"role": "user", "content": "隨點 x 而變；一致連續要求同一個 δ 對所有 x 都行。"},
        {"role": "assistant", "content": "正確，這是兩者的本質分野。"},
    ]},
    {"problem_id": "B3", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 y_{n_k} 也會收斂到 x*？"},
        {"role": "assistant", "content": "因為 $|x_{n_k}-y_{n_k}|<1/n_k\\to0$。既然 $x_{n_k}\\to x^*$，兩者距離趨零推出 $y_{n_k}$ 如何？"},
        {"role": "user", "content": "y_{n_k} 也→x*。"},
        {"role": "assistant", "content": "正確，這讓兩序列的像都趨 f(x*)。"},
    ]},
    {"problem_id": "B3", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼開區間 (0,1) 上 1/x 不一致連續？"},
        {"role": "assistant", "content": "因為區間不閉，逼近 $0$ 時斜率爆炸，找不到通用 $\\delta$。這說明一致連續需要區間具備什麼？"},
        {"role": "user", "content": "需要閉且有界（緊緻），Heine-Cantor 才適用。"},
        {"role": "assistant", "content": "正確，緊緻性是關鍵前提。"},
    ]},

    # ---- B4 ----
    {"problem_id": "B4", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我固定 x=y+1 這種相距 1 的點，但 |x−y|=1 不小於 δ 啊。"},
        {"role": "assistant", "content": "距離要 $<\\delta$，取固定的 $1$ 不行。改讓距離依 $\\delta$ 縮小、卻把點推到遠處，例如 $x-y=\\delta/2$。這樣 $|x^2-y^2|$ 如何？"},
        {"role": "user", "content": "取 x=n+δ/2、y=n，|x−y|=δ/2<δ，而 |x²−y²|=(δ/2)(2n+δ/2)≥δn。"},
        {"role": "assistant", "content": "正是，取 $n$ 大就 $\\ge\\varepsilon_0$。關鍵是同時「距離小」與「位置遠」。"},
        {"role": "user", "content": "懂了，距離用 δ/2 縮小，位置用 n 推遠。"},
        {"role": "assistant", "content": "正確。教訓：反例要讓 $|x-y|<\\delta$ 但利用 $|x+y|$ 無界。"},
    ]},
    {"problem_id": "B4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼關鍵在 |x+y| 這個因子？"},
        {"role": "assistant", "content": "因為 $|x^2-y^2|=|x-y||x+y|$。$|x-y|$ 可壓小，但 $|x+y|$ 在遠處會怎樣？"},
        {"role": "user", "content": "無界地變大，讓乘積失控。"},
        {"role": "assistant", "content": "正確，無界因子是不一致連續的根源。"},
    ]},
    {"problem_id": "B4", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 x² 在 [0,1] 反而一致連續？"},
        {"role": "assistant", "content": "因為有界區間上 $|x+y|$ 被壓住。$|x+y|\\le2$ 使 $x^2$ 成為什麼樣的函數？"},
        {"role": "user", "content": "Lipschitz（常數 2），故一致連續。"},
        {"role": "assistant", "content": "正確，有界域讓因子受控。"},
    ]},
    {"problem_id": "B4", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "「不一致連續」的定義否定句怎麼寫？"},
        {"role": "assistant", "content": "就是把定義反過來：存在 $\\varepsilon_0>0$，對任意 $\\delta>0$ 都能找到什麼？"},
        {"role": "user", "content": "找到 x,y 使 |x−y|<δ 但 |f(x)−f(y)|≥ε_0。"},
        {"role": "assistant", "content": "正確，這是我們要建構的反例目標。"},
    ]},

    # ---- B5 ----
    {"problem_id": "B5", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "在 a 點我取 δ=ε/(1+2|a|)，不加 min。"},
        {"role": "assistant", "content": "若 $\\varepsilon$ 很大，這個 $\\delta$ 可能超過 $1$，使預設界 $|x-a|<1$（進而 $|x+a|<1+2|a|$）失效。該補什麼？"},
        {"role": "user", "content": "要取 min{1, ε/(1+2|a|)} 保住預設界。"},
        {"role": "assistant", "content": "正是。這樣兩個條件才同時成立。"},
        {"role": "user", "content": "懂了，沒有 min 時大 ε 會破壞估計。"},
        {"role": "assistant", "content": "正確。教訓：只要用了預設界，就得靠 min 保護它。"},
    ]},
    {"problem_id": "B5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "|x+a| 的上界 1+2|a| 怎麼來的？"},
        {"role": "assistant", "content": "由 $|x+a|=|(x-a)+2a|\\le|x-a|+2|a|$。在預設界 $|x-a|<1$ 下，這變成什麼？"},
        {"role": "user", "content": "<1+2|a|。"},
        {"role": "assistant", "content": "正確，三角不等式加預設界即得。"},
    ]},
    {"problem_id": "B5", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "從 δ 依賴 a 能看出什麼？"},
        {"role": "assistant", "content": "$\\delta=\\min\\{1,\\varepsilon/(1+2|a|)\\}$ 隨 $|a|$ 變大而變小。這對「一致」連續意味什麼？"},
        {"role": "user", "content": "找不到對所有 a 通用的 δ，所以 x² 在 ℝ 上不一致連續。"},
        {"role": "assistant", "content": "正確，逐點 δ 隨點退化正是不一致的徵兆。"},
    ]},
    {"problem_id": "B5", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "這題和在 x=2 那題本質一樣嗎？"},
        {"role": "assistant", "content": "一樣，只是把具體的 $2$ 換成一般的 $a$。變動因子 $|x+a|$ 一樣要用什麼壓住？"},
        {"role": "user", "content": "用預設界 |x−a|<1 壓成常數上界。"},
        {"role": "assistant", "content": "正確，方法完全平行。"},
    ]},

    # ---- B6 ----
    {"problem_id": "B6", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我想先固定 δ，再對序列找 N，再回頭用連續取這個 δ。"},
        {"role": "assistant", "content": "$\\delta$ 應由連續性（依 $\\varepsilon$）先產生，還是由序列收斂先產生才合理？"},
        {"role": "user", "content": "由連續性先產生 δ，再拿去給序列找 N。"},
        {"role": "assistant", "content": "正是。順序對了後，$n\\ge N\\Rightarrow|x_n-x_0|<\\delta\\Rightarrow$ 什麼？"},
        {"role": "user", "content": "⇒|f(x_n)−f(x_0)|<ε。"},
        {"role": "assistant", "content": "正確。教訓：$\\delta$ 由連續性先生成，序列再匹配。"},
    ]},
    {"problem_id": "B6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "這題要把哪兩個定義接起來？"},
        {"role": "assistant", "content": "連續的 $\\varepsilon$-$\\delta$ 和序列收斂的 $\\varepsilon$-$N$。橋樑是誰把兩者連起來？"},
        {"role": "user", "content": "是 δ：連續給 δ，序列用 δ 找 N。"},
        {"role": "assistant", "content": "正確，$\\delta$ 是接點。"},
    ]},
    {"problem_id": "B6", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "反方向（序列刻畫連續）怎麼證？"},
        {"role": "assistant", "content": "用反證：若不連續就有 $\\varepsilon_0$，能造出什麼樣的序列導出矛盾？"},
        {"role": "user", "content": "造 x_n→x_0 但 |f(x_n)−f(x_0)|≥ε_0，與假設 f(x_n)→f(x_0) 矛盾。"},
        {"role": "assistant", "content": "正確，這給出連續的序列等價刻畫。"},
    ]},
    {"problem_id": "B6", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼這叫「連續的序列準則」？"},
        {"role": "assistant", "content": "因為它用「序列的像收斂」來刻畫連續。本題證的是哪個方向？"},
        {"role": "user", "content": "連續 ⇒ 保序列極限（x_n→x_0 則 f(x_n)→f(x_0)）。"},
        {"role": "assistant", "content": "正確，這是其中一個方向。"},
    ]},

    # ---- B7 ----
    {"problem_id": "B7", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "偶次多項式應該也有實根吧，都連續啊。"},
        {"role": "assistant", "content": "連續不保證有根，還需異號值。偶次時兩端行為如何，能保證異號嗎？"},
        {"role": "user", "content": "偶次兩端同號（都→+∞ 或都→−∞），未必異號，如 x²+1 無實根。"},
        {"role": "assistant", "content": "正是。奇次的特別之處在哪，使 IVT 可用？"},
        {"role": "user", "content": "奇次兩端異號（+∞ 與 −∞），保證有正有負。"},
        {"role": "assistant", "content": "正確。教訓：IVT 需異號前提，只有奇次自動提供。"},
    ]},
    {"problem_id": "B7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 x→+∞ 時 p(x)→+∞？"},
        {"role": "assistant", "content": "提出最高次項 $x^{2k+1}$，括號內趨 $1$。因指數為奇、$x\\to+\\infty$，主項符號為何？"},
        {"role": "user", "content": "正的，所以 p(x)→+∞。"},
        {"role": "assistant", "content": "正確，首項主宰決定趨向。"},
    ]},
    {"problem_id": "B7", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "怎麼嚴謹說明「首項主宰」？"},
        {"role": "assistant", "content": "把 $p(x)=x^{2k+1}(1+c_{2k}/x+\\cdots)$。括號當 $x\\to\\infty$ 趨向什麼，故符號由誰定？"},
        {"role": "user", "content": "括號→1，符號由 x^{2k+1} 定。"},
        {"role": "assistant", "content": "正確，提出首項是嚴謹化的標準手法。"},
    ]},
    {"problem_id": "B7", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "找到一正一負的點後，下一步是什麼？"},
        {"role": "assistant", "content": "在這兩點構成的閉區間上，$p$ 連續且端點異號，套哪個定理？"},
        {"role": "user", "content": "介值定理，得存在 c 使 p(c)=0。"},
        {"role": "assistant", "content": "正確，IVT 收尾。"},
    ]},

    # ---- B8 ----
    {"problem_id": "B8", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "f 在開區間 (0,1) 連續也應該有界吧？"},
        {"role": "assistant", "content": "$f(x)=1/x$ 在 $(0,1)$ 連續卻無界。有界性定理需要區間具備什麼，開區間缺了哪點？"},
        {"role": "user", "content": "需要閉且有界；開區間不閉，子列極限可能跑到端點外。"},
        {"role": "assistant", "content": "正是。閉性讓 B-W 的子列極限留在區間內。少了它反證就失效。"},
        {"role": "user", "content": "懂了，所以定理限定閉區間 [a,b]。"},
        {"role": "assistant", "content": "正確。教訓：有界性定理的「閉」不可省。"},
    ]},
    {"problem_id": "B8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "反證假設「無界」具體是什麼？"},
        {"role": "assistant", "content": "無上界（或下界）意味對每個 $n$ 能取到什麼樣的點？"},
        {"role": "user", "content": "取 x_n 使 |f(x_n)|>n。"},
        {"role": "assistant", "content": "正確，這是矛盾的起點。"},
    ]},
    {"problem_id": "B8", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "矛盾具體出在哪一步？"},
        {"role": "assistant", "content": "$f(x_{n_k})$ 因連續而收斂（有界），卻又滿足什麼，兩者衝突？"},
        {"role": "user", "content": "滿足 |f(x_{n_k})|>n_k→∞，無界，與收斂矛盾。"},
        {"role": "assistant", "content": "正確，收斂序列必有界正是矛盾核心。"},
    ]},
    {"problem_id": "B8", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "有界性定理和最大值定理有關係嗎？"},
        {"role": "assistant", "content": "有，前者是後者的前置引理。要談 $\\sup f$ 是有限的，得先知道 $f$ 什麼？"},
        {"role": "user", "content": "先知道 f 有界，sup 才有限。"},
        {"role": "assistant", "content": "正確，邏輯上有界性先行。"},
    ]},

    # ---- B9 ----
    {"problem_id": "B9", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我用同一個 δ 同時處理 f 和 g，反正都連續。"},
        {"role": "assistant", "content": "外層 $f$ 的門檻是 $\\eta$、內層 $g$ 的是 $\\delta$，兩者不同層級。應先由誰產生 $\\eta$，再由誰產生 $\\delta$？"},
        {"role": "user", "content": "先由 f 連續（依 ε）產生 η，再由 g 連續（依 η）產生 δ。"},
        {"role": "assistant", "content": "正是。鏈式推理 $|x-x_0|<\\delta\\Rightarrow|g(x)-y_0|<\\eta\\Rightarrow$ 什麼？"},
        {"role": "user", "content": "⇒|f(g(x))−f(y_0)|<ε。"},
        {"role": "assistant", "content": "正確。教訓：合成連續要分兩層門檻、由外而內。"},
    ]},
    {"problem_id": "B9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "y_0 是什麼？"},
        {"role": "assistant", "content": "$y_0=g(x_0)$，是外層函數 $f$ 要連續的那個點。$f$ 在 $y_0$ 連續給出什麼門檻？"},
        {"role": "user", "content": "給出 η，使 |y−y_0|<η 時 |f(y)−f(y_0)|<ε。"},
        {"role": "assistant", "content": "正確，$y_0$ 是內外層的銜接點。"},
    ]},
    {"problem_id": "B9", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "用序列準則證合成連續會更快嗎？"},
        {"role": "assistant", "content": "會。$x_n\\to x_0$ 經 $g$ 連續得 $g(x_n)\\to g(x_0)$，再經 $f$ 連續得什麼？"},
        {"role": "user", "content": "f(g(x_n))→f(g(x_0))，兩次極限傳遞即可。"},
        {"role": "assistant", "content": "正確，序列準則讓證明更簡潔。"},
    ]},
    {"problem_id": "B9", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼順序不能顛倒？"},
        {"role": "assistant", "content": "因為內層 $g$ 要「逼多近」是由外層需求 $\\eta$ 決定的。$\\eta$ 沒先出來，$\\delta$ 就無標準可循。所以誰先？"},
        {"role": "user", "content": "η 先、δ 後。"},
        {"role": "assistant", "content": "正確，由外而內設門檻。"},
    ]},

    # ---- B10 ----
    {"problem_id": "B10", "persona": "error", "kind": "augmented", "turns": [
        {"role": "user", "content": "我設 g(x)=f(x)−f(x+1/2)，然後說 g(0)=g(1/2) 用 IVT。"},
        {"role": "assistant", "content": "符號方向不影響，但要算端點和而非設相等。$g(0)+g(1/2)$ 等於什麼？"},
        {"role": "user", "content": "=[f(0)−f(1/2)]+[f(1/2)−f(1)]=f(0)−f(1)=0。"},
        {"role": "assistant", "content": "正是，和為零故異號，用 IVT。這裡用的是 IVT 還是 Rolle，為什麼？"},
        {"role": "user", "content": "用 IVT，因為只給連續、沒給可微。"},
        {"role": "assistant", "content": "正確。教訓：靠端點和為零 + IVT，別誤用 Rolle。"},
    ]},
    {"problem_id": "B10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼要造 g(x)=f(x+1/2)−f(x)？"},
        {"role": "assistant", "content": "因為 $g(c)=0$ 恰好等價於我們要的 $f(c)=f(c+\\frac12)$。所以把「兩值相等」轉成什麼？"},
        {"role": "user", "content": "轉成「g 有零點」，好用 IVT。"},
        {"role": "assistant", "content": "正確，造差函數是關鍵一步。"},
    ]},
    {"problem_id": "B10", "persona": "bright", "kind": "short", "turns": [
        {"role": "user", "content": "為什麼 g(0)+g(1/2)=0 就能保證有零點？"},
        {"role": "assistant", "content": "因為兩者相加為零，代表它們異號（或其一為零），據此該套哪個定理得零點？"},
        {"role": "user", "content": "異號（或有一為 0），異號時用 IVT 得零點。"},
        {"role": "assistant", "content": "正確，和為零逼出異號。"},
    ]},
    {"problem_id": "B10", "persona": "confused", "kind": "short", "turns": [
        {"role": "user", "content": "g 定義在哪個區間？"},
        {"role": "assistant", "content": "因為要用到 $f(x+\\frac12)$，$x+\\frac12$ 不能超過 $1$，故 $x$ 的範圍是什麼？"},
        {"role": "user", "content": "x∈[0,1/2]。"},
        {"role": "assistant", "content": "正確，定義域限制來自 $f$ 的自變數範圍。"},
    ]},
]
