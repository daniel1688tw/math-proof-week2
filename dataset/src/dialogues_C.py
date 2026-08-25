# -*- coding: utf-8 -*-
"""主題 C 核心對話（C1-C10 × 3 Persona）。內容由 Claude 手寫。"""

DIALOGUES = [
    # ===== C1: differentiable ⇒ continuous =====
    {"problem_id": "C1", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "可微就連續，感覺很顯然，可是要我證我又不知道從哪下手。"},
        {"role": "assistant", "content": "連續的目標是證 $\\lim_{x\\to x_0}(f(x)-f(x_0))=0$。能不能把 $f(x)-f(x_0)$ 湊出一個差商的形式?"},
        {"role": "user", "content": "可以寫成 f(x)−f(x_0) = [f(x)−f(x_0)]/(x−x_0) · (x−x_0)。"},
        {"role": "assistant", "content": "很好。當 $x\\to x_0$，這個乘積的兩個因子各自趨向什麼?"},
        {"role": "user", "content": "第一個因子→f'(x_0)（可微），第二個 (x−x_0)→0。"},
        {"role": "assistant", "content": "正是。用極限乘積律，整個乘積趨向什麼，從而得到連續?"},
        {"role": "user", "content": "→f'(x_0)·0=0，所以 f(x)→f(x_0)，f 在 x_0 連續。"},
        {"role": "assistant", "content": "完全正確。關鍵是「乘一個又除一個 $(x-x_0)$」湊出差商，可微保證因子有限。"},
    ]},
    {"problem_id": "C1", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "因為 f 可微，導數存在，所以 f 連續，這不是定義嗎?"},
        {"role": "assistant", "content": "這是要證的定理、不是定義，需要推導。你能把 $f(x)-f(x_0)$ 改寫成含差商的乘積來著手嗎?"},
        {"role": "user", "content": "喔，寫成 [f(x)−f(x_0)]/(x−x_0)·(x−x_0)。"},
        {"role": "assistant", "content": "很好。這裡為什麼可以乘除 $(x-x_0)$，需要什麼前提?"},
        {"role": "user", "content": "因為取極限是 x→x_0 但 x≠x_0，所以 x−x_0≠0，可以除。兩因子極限相乘得 f'(x_0)·0=0。"},
        {"role": "assistant", "content": "正確。教訓：可微⇒連續是需要證明的命題，靠差商乘積與極限律，而非直接當定義。"},
    ]},
    {"problem_id": "C1", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "把 f(x)−f(x_0) 寫成差商乘 (x−x_0)，取極限得 f'(x_0)·0=0，故連續。"},
        {"role": "assistant", "content": "正確。反過來，連續卻不可微的經典例子是什麼，說明兩者不等價?"},
        {"role": "user", "content": "f(x)=|x| 在 0 連續但不可微，左右導數不同。所以可微是比連續強的條件。"},
        {"role": "assistant", "content": "正確，你清楚兩者的嚴格強弱關係。掌握得很好。"},
    ]},

    # ===== C2: Rolle =====
    {"problem_id": "C2", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Rolle 定理的證明我背不起來，不知道 c 是怎麼冒出來的。"},
        {"role": "assistant", "content": "$c$ 來自極值。$f$ 在閉區間 $[a,b]$ 連續，哪個定理保證它取得最大與最小值?"},
        {"role": "user", "content": "最大值定理，f 會達到最大值 M 和最小值 m。"},
        {"role": "assistant", "content": "很好。若 $M=m$，$f$ 是什麼，導數如何?"},
        {"role": "user", "content": "M=m 時 f 是常數，導數處處為 0，隨便取 c 都行。"},
        {"role": "assistant", "content": "正是。若 $M>m$，由 $f(a)=f(b)$，最大或最小至少有一個發生在哪裡?"},
        {"role": "user", "content": "至少一個在內部點 c∈(a,b)，因為端點值相等不可能同時是嚴格的最大和最小。"},
        {"role": "assistant", "content": "對。在內部極值點用哪個定理得到 $f'(c)=0$?"},
        {"role": "user", "content": "費馬定理，內部極值且可微則 f'(c)=0。"},
        {"role": "assistant", "content": "完全正確。Rolle 的靈魂是「最大值定理找極值點 + 費馬定理得零導數」。"},
    ]},
    {"problem_id": "C2", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "因為 f(a)=f(b)，圖形一定會有水平切線，所以 f'(c)=0。"},
        {"role": "assistant", "content": "這是直覺不是證明。要嚴謹得指出 $c$ 從何而來。$f$ 在 $[a,b]$ 連續能保證取得什麼?"},
        {"role": "user", "content": "最大值和最小值（最大值定理）。"},
        {"role": "assistant", "content": "很好。當最大或最小落在內部點，再靠哪個定理把它變成 $f'(c)=0$?"},
        {"role": "user", "content": "費馬定理。但要先排除 M=m 的常數情形，那時任一點都行。"},
        {"role": "assistant", "content": "正確。教訓：Rolle 的 $c$ 必須經由「最大值定理 + 費馬定理」導出，不能只憑圖形直覺。"},
    ]},
    {"problem_id": "C2", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "用最大值定理取 M、m，M=m 則常數；否則極值在內部，費馬給 f'(c)=0。"},
        {"role": "assistant", "content": "完整。你的證明用到了 $[a,b]$ 連續與 $(a,b)$ 可微，這兩個假設分別在哪一步起作用?"},
        {"role": "user", "content": "連續用在最大值定理（保證極值存在），可微用在費馬定理（保證 f'(c) 存在且為 0）。"},
        {"role": "assistant", "content": "正確，你精準對應了每個假設的角色。理解非常到位。"},
    ]},

    # ===== C3: Lagrange MVT =====
    {"problem_id": "C3", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "均值定理我知道結論是斜率等於割線，但證明要怎麼從 Rolle 過來?"},
        {"role": "assistant", "content": "想法是造一個輔助函數把割線減掉，使兩端值相等好套 Rolle。你能寫出這個 $g(x)$ 嗎?"},
        {"role": "user", "content": "設 g(x)=f(x)−f(a)−[(f(b)−f(a))/(b−a)]·(x−a)?"},
        {"role": "assistant", "content": "很好。驗證看看：$g(a)$ 和 $g(b)$ 各是多少?"},
        {"role": "user", "content": "g(a)=0；g(b)=f(b)−f(a)−(f(b)−f(a))=0。兩端都是 0。"},
        {"role": "assistant", "content": "正是，滿足 Rolle 前提。套用後得到 $g'(c)=0$，而 $g'(x)$ 等於什麼?"},
        {"role": "user", "content": "g'(x)=f'(x)−(f(b)−f(a))/(b−a)，所以 f'(c)=(f(b)−f(a))/(b−a)。"},
        {"role": "assistant", "content": "完全正確。均值定理的核心技巧是「減去割線造出滿足 Rolle 的輔助函數」。"},
    ]},
    {"problem_id": "C3", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "我直接對 f 用 Rolle，得到 f'(c)=0，再說它等於割線斜率。"},
        {"role": "assistant", "content": "Rolle 需要 $f(a)=f(b)$，但本題沒有這個條件。要先「造」出兩端相等的函數，你會怎麼修改 $f$?"},
        {"role": "user", "content": "減掉割線：g(x)=f(x)−[割線]，讓 g(a)=g(b)=0。"},
        {"role": "assistant", "content": "正是。對 $g$ 用 Rolle 得 $g'(c)=0$，展開 $g'$ 後會得到什麼?"},
        {"role": "user", "content": "f'(c)−(f(b)−f(a))/(b−a)=0，即 f'(c)=割線斜率。"},
        {"role": "assistant", "content": "正確。教訓：$f$ 一般不滿足 $f(a)=f(b)$，須先減割線造輔助函數才能用 Rolle。"},
    ]},
    {"problem_id": "C3", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "造 g(x)=f(x)−f(a)−(f(b)−f(a))/(b−a)·(x−a)，g(a)=g(b)=0，Rolle 給 g'(c)=0。"},
        {"role": "assistant", "content": "完全正確。這個輔助函數在幾何上代表什麼量，讓你更容易記住構造?"},
        {"role": "user", "content": "g(x) 是 f 的圖形與割線在 x 處的鉛直差（縱向距離），端點差自然為 0。"},
        {"role": "assistant", "content": "正確，幾何意義是「函數到割線的垂直差」。你把構造的動機理解得很透。"},
    ]},

    # ===== C4: Cauchy MVT =====
    {"problem_id": "C4", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "Cauchy 均值定理有兩個函數，我不知道輔助函數要怎麼設。"},
        {"role": "assistant", "content": "想法和 Lagrange 一樣，用組合把兩端湊相等。試著造 $h(x)=(f(b)-f(a))g(x)-(g(b)-g(a))f(x)$，先算 $h(a)$ 與 $h(b)$?"},
        {"role": "user", "content": "h(a)=(f(b)−f(a))g(a)−(g(b)−g(a))f(a)，h(b) 展開後…好像會相等?"},
        {"role": "assistant", "content": "動手展開兩者，你會發現交叉項抵消。確認 $h(a)=h(b)$ 後，能用哪個定理?"},
        {"role": "user", "content": "展開後 h(a)=f(b)g(a)−g(b)f(a)=h(b)。相等，就能用 Rolle。"},
        {"role": "assistant", "content": "正是。Rolle 給 $h'(c)=0$，把 $h'$ 展開能得到什麼關係式?"},
        {"role": "user", "content": "(f(b)−f(a))g'(c)−(g(b)−g(a))f'(c)=0，整理成 f'(c)/g'(c)=(f(b)−f(a))/(g(b)−g(a))。"},
        {"role": "assistant", "content": "完全正確。還記得要先說明 $g(b)\\ne g(a)$，否則不能除，這靠什麼保證?"},
    ]},
    {"problem_id": "C4", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "分別對 f、g 用 Lagrange，得 f'(c)=…、g'(c)=…，相除就好。"},
        {"role": "assistant", "content": "兩次 Lagrange 給的中間點 $c$ 未必是同一個，不能直接相除。要讓「同一個 $c$」出現，該造一個怎樣的輔助函數?"},
        {"role": "user", "content": "對，兩個 c 不同。要造一個組合函數 h，一次 Rolle 給同一個 c。"},
        {"role": "assistant", "content": "正是。取 $h=(f(b)-f(a))g-(g(b)-g(a))f$，驗 $h(a)=h(b)$ 後用 Rolle，$h'(c)=0$ 給出什麼?"},
        {"role": "user", "content": "(f(b)−f(a))g'(c)=(g(b)−g(a))f'(c)，同一個 c，除得結論。"},
        {"role": "assistant", "content": "正確。教訓：要保證「共用同一 $c$」必須用單一輔助函數，分開用兩次均值定理會出兩個點。"},
    ]},
    {"problem_id": "C4", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "造 h=(f(b)−f(a))g−(g(b)−g(a))f，h(a)=h(b)，Rolle 給 h'(c)=0 即結論。"},
        {"role": "assistant", "content": "正確。你如何確保能除以 $g'(c)$ 與 $g(b)-g(a)$，兩者都非零?"},
        {"role": "user", "content": "g'≠0 是假設；g(b)≠g(a) 因為若相等，Rolle 會給某點 g'=0，跟假設矛盾。"},
        {"role": "assistant", "content": "正確，你把「可除性」的兩個前提都論證了。這題掌握得很完整。"},
    ]},

    # ===== C5: f'≡0 ⇒ const =====
    {"problem_id": "C5", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "導數恆為 0 就是常數，這也要證?我不知道怎麼下筆。"},
        {"role": "assistant", "content": "要證常數，等價於證任兩點的函數值相等。任取 $x_1<x_2$，哪個定理能把 $f(x_2)-f(x_1)$ 和導數連起來?"},
        {"role": "user", "content": "均值定理，f(x_2)−f(x_1)=f'(c)(x_2−x_1)。"},
        {"role": "assistant", "content": "很好。既然 $f'\\equiv0$，$f'(c)$ 是多少，$f(x_2)-f(x_1)$ 因此如何?"},
        {"role": "user", "content": "f'(c)=0，所以 f(x_2)−f(x_1)=0，即 f(x_2)=f(x_1)。"},
        {"role": "assistant", "content": "正是。因為 $x_1,x_2$ 是任取的，這說明了什麼?"},
        {"role": "user", "content": "任兩點值都相等，所以 f 是常數。"},
        {"role": "assistant", "content": "完全正確。「導數恆零⇒常數」的橋樑正是均值定理。"},
    ]},
    {"problem_id": "C5", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f'=0 表示不變化，積分回去 f=C，所以是常數。"},
        {"role": "assistant", "content": "「積分回去」其實正是要證的結論之一，容易循環。這門課要用均值定理。任取 $x_1<x_2$，它給出什麼等式?"},
        {"role": "user", "content": "f(x_2)−f(x_1)=f'(c)(x_2−x_1)=0，所以兩點值相等。"},
        {"role": "assistant", "content": "正是。這裡有個常被忽略的前提：$f$ 必須定義在什麼樣的集合上，結論才成立?"},
        {"role": "user", "content": "要在區間（連通）上。若定義域分兩段，各段可以是不同常數。"},
        {"role": "assistant", "content": "正確。教訓：用均值定理而非「積分回去」，且「區間」這個連通性前提不可少。"},
    ]},
    {"problem_id": "C5", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "任取 x_1<x_2，MVT 給 f(x_2)−f(x_1)=f'(c)(x_2−x_1)=0，故 f 為常數。"},
        {"role": "assistant", "content": "正確。由此可推一個推論：若 $f'=g'$ 於區間上，$f$ 與 $g$ 差什麼?"},
        {"role": "user", "content": "對 f−g 用此結論，(f−g)'=0，所以 f−g 是常數，即 f=g+C。"},
        {"role": "assistant", "content": "正確，這正是不定積分「差一個常數」的嚴謹根據。很好。"},
    ]},

    # ===== C6: f'>0 ⇒ strictly increasing =====
    {"problem_id": "C6", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "導數為正就遞增，直覺懂但證明卡住。"},
        {"role": "assistant", "content": "遞增的定義是 $x_1<x_2\\Rightarrow f(x_1)<f(x_2)$。任取這樣兩點，用哪個定理連結函數差與導數?"},
        {"role": "user", "content": "均值定理，f(x_2)−f(x_1)=f'(c)(x_2−x_1)。"},
        {"role": "assistant", "content": "很好。右邊兩個因子的符號各是什麼，乘積因此如何?"},
        {"role": "user", "content": "f'(c)>0、x_2−x_1>0，乘積 >0，所以 f(x_2)>f(x_1)。"},
        {"role": "assistant", "content": "正是，因 $x_1<x_2$ 任取，$f$ 嚴格遞增。若把假設放寬成 $f'\\ge0$，結論會怎麼變?"},
        {"role": "user", "content": "只能得 f(x_2)≥f(x_1)，是遞增（非嚴格）。"},
        {"role": "assistant", "content": "完全正確。你連嚴格與非嚴格的分界都掌握了。"},
    ]},
    {"problem_id": "C6", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "f'(x)>0 表示每點都往上，所以整體遞增，這樣就夠了吧?"},
        {"role": "assistant", "content": "「每點斜率為正」是局部資訊，要嚴謹連到「任兩點大小」需要工具。任取 $x_1<x_2$，均值定理給什麼?"},
        {"role": "user", "content": "f(x_2)−f(x_1)=f'(c)(x_2−x_1)>0，所以 f(x_2)>f(x_1)。"},
        {"role": "assistant", "content": "正是，這才把局部的正斜率轉成整體的大小比較。這一步為何非用均值定理不可?"},
        {"role": "user", "content": "因為它是唯一把「兩點函數差」精確等於「某點導數×間距」的工具。"},
        {"role": "assistant", "content": "正確。教訓：局部導數符號要靠均值定理才能過渡到整體單調性。"},
    ]},
    {"problem_id": "C6", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "任取 x_1<x_2，MVT 給 f(x_2)−f(x_1)=f'(c)(x_2−x_1)>0，故嚴格遞增。"},
        {"role": "assistant", "content": "正確。逆命題「嚴格遞增可微函數必有 $f'>0$」成立嗎，能舉例說明?"},
        {"role": "user", "content": "不成立，f(x)=x³ 嚴格遞增但 f'(0)=0，所以只能得 f'≥0。"},
        {"role": "assistant", "content": "正確，你精準指出單調與導數正負之間並非等價。很好。"},
    ]},

    # ===== C7: Fermat =====
    {"problem_id": "C7", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "費馬定理說極值點導數為 0，我不知道怎麼證。"},
        {"role": "assistant", "content": "從局部極大的定義出發：附近 $f(c+h)\\le f(c)$。先看右導數（$h\\to0^+$），差商 $\\frac{f(c+h)-f(c)}{h}$ 的符號如何?"},
        {"role": "user", "content": "分子 ≤0、分母 h>0，所以差商 ≤0，右導數 f'(c)≤0。"},
        {"role": "assistant", "content": "很好。再看左導數（$h\\to0^-$），這時分母符號變了，差商符號如何?"},
        {"role": "user", "content": "分子 ≤0、分母 h<0，差商 ≥0，所以左導數 f'(c)≥0。"},
        {"role": "assistant", "content": "正是。可微保證左右導數相等，$f'(c)$ 同時 $\\le0$ 又 $\\ge0$，結論是什麼?"},
        {"role": "user", "content": "只能是 f'(c)=0。"},
        {"role": "assistant", "content": "完全正確。費馬定理靠「左右差商夾出 $f'(c)=0$」，可微是黏合左右的關鍵。"},
    ]},
    {"problem_id": "C7", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "極大值點切線水平，所以 f'(c)=0，這不是顯然嗎?"},
        {"role": "assistant", "content": "圖形直覺要化成不等式。用 $f(c+h)\\le f(c)$，先算右導數（$h\\to0^+$）的符號會是什麼?"},
        {"role": "user", "content": "差商 ≤0，右導數 ≤0。"},
        {"role": "assistant", "content": "很好，左導數（$h\\to0^-$）呢，兩者合起來逼出什麼?"},
        {"role": "user", "content": "左導數 ≥0，兩者相等只能是 0。"},
        {"role": "assistant", "content": "正確。另外，這裡為何強調「內部點」，端點極值時結論會失效嗎?"},
        {"role": "user", "content": "端點只有單側，只能得單側導數的符號，未必為 0。所以要內部點。"},
        {"role": "assistant", "content": "正確。教訓：費馬定理需「內部點 + 可微」，靠左右差商而非圖形直覺。"},
    ]},
    {"problem_id": "C7", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "由 f(c+h)≤f(c)，右導數 ≤0、左導數 ≥0，可微使兩者相等故 f'(c)=0。"},
        {"role": "assistant", "content": "完全正確。逆命題「$f'(c)=0$ 則 $c$ 是極值」對嗎，反例?"},
        {"role": "user", "content": "不對，f(x)=x³ 在 0 有 f'(0)=0 卻非極值。所以 f'(c)=0 只是極值的必要條件。"},
        {"role": "assistant", "content": "正確，你清楚費馬定理只給必要而非充分條件。掌握得很好。"},
    ]},

    # ===== C8: |f'|≤M ⇒ Lipschitz =====
    {"problem_id": "C8", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "導數有界要推 Lipschitz，我不知道怎麼把 |f(x)−f(y)| 和 M 連起來。"},
        {"role": "assistant", "content": "$|f(x)-f(y)|$ 是兩點函數差，哪個定理能把它精確寫成導數乘間距?"},
        {"role": "user", "content": "均值定理，f(x)−f(y)=f'(c)(x−y)。"},
        {"role": "assistant", "content": "很好。取絕對值後，用假設 $|f'(c)|\\le M$ 能得到什麼不等式?"},
        {"role": "user", "content": "|f(x)−f(y)|=|f'(c)||x−y|≤M|x−y|。"},
        {"role": "assistant", "content": "正是。這對 $x=y$ 的情形也成立嗎，需不需要另外說明?"},
        {"role": "user", "content": "x=y 時兩邊都 0，也成立。所以對所有 x,y 都有 Lipschitz。"},
        {"role": "assistant", "content": "完全正確。導數有界透過均值定理直接給出 Lipschitz 常數 $M$。"},
    ]},
    {"problem_id": "C8", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "因為 |f'|≤M，積分得 |f(x)−f(y)|=|∫f'|≤M|x−y|。"},
        {"role": "assistant", "content": "用積分可以，但題目只說可微、未必 $f'$ 可積或連續。有沒有只靠可微的工具能得同一結論?"},
        {"role": "user", "content": "均值定理只要可微就行：f(x)−f(y)=f'(c)(x−y)。"},
        {"role": "assistant", "content": "正是，更基本。取絕對值後如何得到 Lipschitz?"},
        {"role": "user", "content": "|f(x)−f(y)|=|f'(c)||x−y|≤M|x−y|。"},
        {"role": "assistant", "content": "正確。教訓：只有可微假設時，均值定理比積分路線更穩妥、前提更少。"},
    ]},
    {"problem_id": "C8", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "由 MVT，f(x)−f(y)=f'(c)(x−y)，取絕對值得 |f(x)−f(y)|≤M|x−y|。"},
        {"role": "assistant", "content": "正確。Lipschitz 連續與一致連續之間有什麼蘊含關係?"},
        {"role": "user", "content": "Lipschitz ⇒ 一致連續（取 δ=ε/M 即可），但反之不然，如 √x 一致連續卻非 Lipschitz。"},
        {"role": "assistant", "content": "正確，你把三種連續強弱層次都理清了。非常好。"},
    ]},

    # ===== C9: |sin x - sin y| ≤ |x-y| =====
    {"problem_id": "C9", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "這題有 sin，我不知道怎麼估計 |sin x − sin y|。"},
        {"role": "assistant", "content": "把它看成某函數在兩點的差，就能用均值定理。取 $f(t)=\\sin t$，$f'(t)$ 是什麼，有何界?"},
        {"role": "user", "content": "f'(t)=cos t，|cos t|≤1。"},
        {"role": "assistant", "content": "很好。對 $x\\ne y$ 用均值定理，$\\sin x-\\sin y$ 等於什麼?"},
        {"role": "user", "content": "=cos c·(x−y)，某個 c 介於 x,y 之間。"},
        {"role": "assistant", "content": "正是。取絕對值並用 $|\\cos c|\\le1$，會得到什麼?"},
        {"role": "user", "content": "|sin x−sin y|=|cos c||x−y|≤|x−y|。"},
        {"role": "assistant", "content": "完全正確。這其實是 C8 的特例：$\\sin$ 的導數有界 $1$，故 Lipschitz 常數為 $1$。"},
    ]},
    {"problem_id": "C9", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "用和差化積 sin x−sin y=2cos((x+y)/2)sin((x−y)/2)，然後 |sin x−sin y|≤2|sin((x−y)/2)|≤2·(x−y)/2=|x−y|，但我不確定 |sin t|≤|t| 能不能用。"},
        {"role": "assistant", "content": "你的路線可行，但依賴 $|\\sin t|\\le|t|$ 這個要另證的引理。有沒有更直接、只用一個定理的方法?"},
        {"role": "user", "content": "可以對 f(t)=sin t 用均值定理，f'=cos，|cos|≤1。"},
        {"role": "assistant", "content": "正是。這樣 $\\sin x-\\sin y=\\cos c(x-y)$，取絕對值直接得結論。你看出兩法的取捨了嗎?"},
        {"role": "user", "content": "看出來了，均值定理一步到位，不用額外證 |sin t|≤|t|。"},
        {"role": "assistant", "content": "正確。教訓：均值定理把「導數有界」直接轉成 Lipschitz，省去輔助引理。"},
    ]},
    {"problem_id": "C9", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "對 sin 用 MVT：sin x−sin y=cos c(x−y)，|cos c|≤1，故 |sin x−sin y|≤|x−y|。"},
        {"role": "assistant", "content": "正確。這個 Lipschitz 常數 $1$ 是最佳（不能更小）的嗎，如何說明?"},
        {"role": "user", "content": "是最佳，因為在 x,y→0 時 |sin x−sin y|/|x−y|→|cos 0|=1，逼近 1。"},
        {"role": "assistant", "content": "正確，你指出常數 $1$ 的最佳性由導數在 $0$ 的值達到。分析很深入。"},
    ]},

    # ===== C10: x/(1+x) < ln(1+x) < x =====
    {"problem_id": "C10", "persona": "confused", "kind": "core", "turns": [
        {"role": "user", "content": "這個雙邊不等式含 ln，我不知道怎麼一次證出上下界。"},
        {"role": "assistant", "content": "對 $f(t)=\\ln(1+t)$ 在 $[0,x]$ 用均值定理會很有用。$f'(t)$ 是什麼?"},
        {"role": "user", "content": "f'(t)=1/(1+t)。"},
        {"role": "assistant", "content": "很好。均值定理給 $\\ln(1+x)-\\ln1=f'(\\xi)\\cdot x$，即 $\\ln(1+x)=\\frac{x}{1+\\xi}$，其中 $\\xi$ 在哪個範圍?"},
        {"role": "user", "content": "ξ∈(0,x)。"},
        {"role": "assistant", "content": "正是。由 $0<\\xi<x$ 推 $\\frac{1}{1+\\xi}$ 的範圍，再乘上 $x>0$，會得到什麼雙邊不等式?"},
        {"role": "user", "content": "1<1+ξ<1+x，所以 1/(1+x)<1/(1+ξ)<1，乘 x 得 x/(1+x)<ln(1+x)<x。"},
        {"role": "assistant", "content": "完全正確。一個均值定理等式配上 $\\xi$ 的範圍，就同時擠出上下界。"},
    ]},
    {"problem_id": "C10", "persona": "error", "kind": "core", "turns": [
        {"role": "user", "content": "我對 ln(1+x)<x，設 g(x)=x−ln(1+x)，g'(x)=1−1/(1+x)>0，g(0)=0 所以 g>0。左邊我不會。"},
        {"role": "assistant", "content": "右半你用單調性做得很好。左邊其實可用同一招，或用均值定理一次搞定。試對 $\\ln(1+t)$ 在 $[0,x]$ 用均值定理，得到什麼等式?"},
        {"role": "user", "content": "ln(1+x)=x/(1+ξ)，ξ∈(0,x)。"},
        {"role": "assistant", "content": "正是。由 $\\xi<x$ 得 $\\frac{1}{1+\\xi}>\\frac{1}{1+x}$，乘 $x$ 後左界就出來了。是哪個不等式?"},
        {"role": "user", "content": "ln(1+x)=x/(1+ξ)>x/(1+x)，左界得證。"},
        {"role": "assistant", "content": "正確。教訓：均值定理的單一等式配 $\\xi$ 範圍，能同時給上下界，比分開造兩個輔助函數更省。"},
    ]},
    {"problem_id": "C10", "persona": "bright", "kind": "core", "turns": [
        {"role": "user", "content": "對 ln(1+t) 在 [0,x] 用 MVT：ln(1+x)=x/(1+ξ)，由 0<ξ<x 得 x/(1+x)<ln(1+x)<x。"},
        {"role": "assistant", "content": "非常俐落。若要對 $x\\in(-1,0)$ 也建立類似不等式，論證需注意什麼?"},
        {"role": "user", "content": "x<0 時乘負數不等號要反向，且區間變成 [x,0]，得小心 x/(1+x) 與 x 的大小順序會調換。"},
        {"role": "assistant", "content": "正確，你敏銳注意到負區間乘法變號的陷阱。理解非常紮實。"},
    ]},
]
