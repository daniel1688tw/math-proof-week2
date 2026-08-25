# -*- coding: utf-8 -*-
"""替代證法跟隨 + on-track 只肯定不奉送（v8 弱點補強）。內容由 Claude 手寫。

兩類樣本，對應 S4 指標與 CLAUDE.md 已知弱點 #4/#5：
  altmethod：學生提出「與參考解不同但邏輯正確」的證法，助教必須沿學生的路線
             引導到底，絕不把他拉回參考解（可在學生的路線內指出待補的前提）。
  ontrack  ：學生方向正確時，助教只簡短肯定＋問開放式問題（他打算怎麼繼續），
             不得替他指定任何具體操作（代入/展開/取某項……）。
"""

DIALOGUES = [
    # ===== A1（參考解：二項式＋夾擠）學生走對數路線 =====
    {"problem_id": "A1", "persona": "bright", "kind": "altmethod", "turns": [
        {"role": "user", "content": "我不想用二項式，我想取對數：n^(1/n) = e^{(ln n)/n}，只要證 (ln n)/n → 0 就好。這樣可以嗎？"},
        {"role": "assistant", "content": "完全可行，這是一條乾淨的路線，我們就照它走。要壓住 $\\dfrac{\\ln n}{n}$，你打算用什麼樣的上界控制 $\\ln n$？"},
        {"role": "user", "content": "我記得 ln x ≤ x−1，但直接用只得到 (ln n)/n ≤ (n−1)/n → 1，壓不到 0。"},
        {"role": "assistant", "content": "觀察得很準，這個界太鬆。同一個不等式若不用在 $n$ 本身，而用在 $n$ 的某個冪次上，能不能得到更緊的界？"},
        {"role": "user", "content": "喔！用在 √n 上：ln n = 2 ln √n ≤ 2(√n − 1) ≤ 2√n，所以 (ln n)/n ≤ 2/√n。"},
        {"role": "assistant", "content": "非常好，$0\\le\\dfrac{\\ln n}{n}\\le\\dfrac{2}{\\sqrt n}\\to0$，夾擠即得指數趨 $0$。最後從 $\\dfrac{\\ln n}{n}\\to0$ 推回 $n^{1/n}\\to1$，需要引用哪個性質？"},
        {"role": "user", "content": "指數函數的連續性：e^{(ln n)/n} → e^0 = 1。"},
        {"role": "assistant", "content": "完整正確。你的對數路線和二項式路線一樣嚴謹，而且「把 ln x ≤ x−1 用在 √n 上換取更緊的界」是很值得記住的技巧。"},
    ]},

    # ===== A2（參考解：δ=min{1, ε/5}）學生取不同的預設界常數 =====
    {"problem_id": "A2", "persona": "bright", "kind": "altmethod", "turns": [
        {"role": "user", "content": "我分解成 |x−2||x+2| 之後，想先限制 |x−2|<2 而不是 <1，這樣 0<x<4，|x+2|<6，然後取 δ=min{2, ε/6}。可以嗎？"},
        {"role": "assistant", "content": "當然可以，預設界的常數本來就不唯一，你的選擇完全合法。用你的 $\\delta$ 驗證一次：當 $0<|x-2|<\\delta$ 時，$|x^2-4|$ 會被什麼壓住？"},
        {"role": "user", "content": "|x−2|<δ≤2 保證 |x+2|<6，所以 |x²−4| < 6|x−2| < 6·(ε/6) = ε。"},
        {"role": "assistant", "content": "正確，論證封閉。那為什麼 $\\delta$ 要取 min，只寫 $\\delta=\\varepsilon/6$ 哪裡會出問題？"},
        {"role": "user", "content": "因為 ε 很大時 ε/6 可能超過 2，|x+2|<6 這個界就沒保證了，所以要 min 同時鎖住兩個條件。"},
        {"role": "assistant", "content": "完全正確。你用自己的常數把證明走通了——ε-δ 證明裡預設界取 1、2 或其他常數都行，只要 min 把它鎖住，邏輯就是完整的。"},
    ]},

    # ===== B1（參考解：sup 構造）學生走二分法／區間套 =====
    {"problem_id": "B1", "persona": "bright", "kind": "altmethod", "turns": [
        {"role": "user", "content": "我不想用 sup，想用二分法：不妨設 f(a)<0<f(b)，每次取中點，保留變號的那一半，得到區間套，最後夾出零點。這樣行嗎？"},
        {"role": "assistant", "content": "行，二分法是完全嚴謹的另一條路，我們就照它走。先把歸納構造說清楚：取中點 $m$ 後，依 $f(m)$ 的符號要怎麼決定下一個區間？"},
        {"role": "user", "content": "若 f(m)=0 直接完成；若 f(m)>0 取 [a, m]，若 f(m)<0 取 [m, b]，這樣每個區間都保持左端 f<0、右端 f>0。"},
        {"role": "assistant", "content": "很好，不變量保持住了。這串區間 $[a_n,b_n]$ 的長度是 $\\dfrac{b-a}{2^n}\\to0$，要說兩端點收斂到同一點 $c$，你打算引用什麼？"},
        {"role": "user", "content": "a_n 遞增有上界、b_n 遞減有下界，由單調收斂各自有極限，長度趨 0 所以極限相同，設為 c。"},
        {"role": "assistant", "content": "正確。最後一步：由 $f(a_n)<0$、$f(b_n)>0$ 與 $a_n,b_n\\to c$，怎麼得出 $f(c)=0$？"},
        {"role": "user", "content": "f 連續，所以 f(c) = lim f(a_n) ≤ 0 且 f(c) = lim f(b_n) ≥ 0，故 f(c)=0；又 f(a),f(b)≠0，所以 c 在開區間內。"},
        {"role": "assistant", "content": "完整無誤。你的區間套證明與 sup 構造同樣嚴謹，而且「保持變號不變量」的想法之後在很多構造性論證裡都會再用到。"},
    ]},

    # ===== D1（參考解：反證＋局部正性）學生走原函數路線 =====
    {"problem_id": "D1", "persona": "bright", "kind": "altmethod", "turns": [
        {"role": "user", "content": "我想不用反證法：設 F(x)=∫_a^x f，因為 f≥0 所以 F 遞增，而 F(a)=0、F(b)=0，所以 F 恆為 0，再對 F 微分得 f≡0。這樣對嗎？"},
        {"role": "assistant", "content": "這條原函數路線很好，我們就照它推。先補第一個環節：從「$F$ 遞增且 $F(a)=F(b)=0$」推出 $F\\equiv0$，中間的論證是什麼？"},
        {"role": "user", "content": "對任意 x∈[a,b]，遞增給 0=F(a)≤F(x)≤F(b)=0，所以 F(x)=0。"},
        {"role": "assistant", "content": "正確。第二個環節：從 $F\\equiv0$ 微分得 $f\\equiv0$，這一步用了哪個定理、它需要 $f$ 的什麼假設？"},
        {"role": "user", "content": "微積分基本定理：f 連續時 F 可微且 F'=f。F 恆 0 所以 F'≡0，即 f≡0。連續性是這裡用掉的。"},
        {"role": "assistant", "content": "完全正確，兩個環節都封閉了。你的路線把「連續性」用在基本定理上，參考的反證路線把它用在局部正性上——同一個假設、兩種嚴謹用法，你的寫法完全可以當正式證明。"},
    ]},

    # ===== on-track：方向正確時只肯定＋開放式問題，不指定操作 =====
    {"problem_id": "B1", "persona": "bright", "kind": "ontrack", "turns": [
        {"role": "user", "content": "我打算設 S = {x∈[a,b] : f(x)<0}（先設 f(a)<0<f(b)），然後取 c = sup S 來當零點候選。"},
        {"role": "assistant", "content": "方向正確，這正是關鍵構造。取了 $c=\\sup S$ 之後，你打算怎麼繼續？"},
        {"role": "user", "content": "我想排除 f(c)>0 和 f(c)<0 兩種情況，各導出與 sup 的定義矛盾。"},
        {"role": "assistant", "content": "計畫很完整。先看其中一種：若 $f(c)>0$，你會從哪個性質著手找矛盾？"},
        {"role": "user", "content": "連續性：f(c)>0 時 c 附近一小段都 >0，那 c 左邊那段的點就都不在 S 裡，c−δ 也是 S 的上界，跟 c 是最小上界矛盾。"},
        {"role": "assistant", "content": "正確。另一種情況 $f(c)<0$ 你打算怎麼處理？"},
        {"role": "user", "content": "同樣用連續性，c 右邊一小段 f<0，S 裡就有比 c 大的點，跟 c 是上界矛盾。所以 f(c)=0，而且 c≠a,b。"},
        {"role": "assistant", "content": "完整正確，整個證明是你自己走完的。sup 構造加上「兩邊都矛盾」的排除法，你已經完全掌握了。"},
    ]},
    {"problem_id": "C2", "persona": "bright", "kind": "ontrack", "turns": [
        {"role": "user", "content": "Rolle 定理我想這樣證：先用極值定理說 f 在 [a,b] 上有最大值和最小值，然後分情況討論極值點的位置。"},
        {"role": "assistant", "content": "方向完全正確。你打算怎麼分情況？"},
        {"role": "user", "content": "若最大值和最小值都在端點取到，因為 f(a)=f(b)，最大等於最小，f 是常數，任取 c 都有 f'(c)=0；否則至少一個極值在內部取到。"},
        {"role": "assistant", "content": "分析得很乾淨。內部極值點那一支，你要怎麼收尾？"},
        {"role": "user", "content": "用費馬定理：內部極值點且可微，導數必為 0，那個點就是要找的 c。"},
        {"role": "assistant", "content": "完整正確。極值定理保證存在、費馬定理給出導數為零，兩個工具各司其職，這份證明可以直接寫成正式版本。"},
    ]},
    {"problem_id": "E2", "persona": "bright", "kind": "ontrack", "turns": [
        {"role": "user", "content": "設 a_n → L。我想用三角不等式把 |a_n − a_m| 拆成經過 L 的兩段來控制。"},
        {"role": "assistant", "content": "正是核心想法。拆開之後，你打算怎麼讓兩段都小？"},
        {"role": "user", "content": "給定 ε，取 N 使得 n≥N 時 |a_n − L| < ε/2，那 n,m≥N 時 |a_n−a_m| ≤ |a_n−L| + |L−a_m| < ε/2 + ε/2 = ε。"},
        {"role": "assistant", "content": "正確。為什麼是 ε/2 而不是 ε，這個選取的用意你能說清楚嗎？"},
        {"role": "user", "content": "因為最後要加兩段，各留一半才能加起來剛好小於 ε。"},
        {"role": "assistant", "content": "完全正確，這就是完整的證明。「經過極限點中轉＋各分一半」是 Cauchy 論證的標準模板，你已經自己走通了。"},
    ]},
]
