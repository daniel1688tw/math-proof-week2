# -*- coding: utf-8 -*-
"""寫證明→審閱對話（8 條）：內容由 Claude 手寫。

補上目標的「最後一哩路」：引導不以助教總結收尾，而是——
  1. 關鍵步驟走完後，助教請學生**自己寫出完整證明**
  2. 學生交出的草稿帶一個典型缺漏（前提沒驗、特例沒排、量詞順序、嚴格性）
  3. 助教審閱時**用一個問題指出缺漏**（不直接改），學生自行補上
  4. 補完才確認完成
訓練訊號：審閱行為 = 「對照參考解找缺漏 → 問題式指出 → 等學生修」。
"""

DIALOGUES = [
    # 1. A2：缺漏 = 沒說明 |x+2|<5 的來源（預設界）
    {"problem_id": "A2", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "我已經懂整個思路了：分解、壓住 |x+2|、取 min。"},
        {"role": "assistant", "content": "很好，那最後一步：請把完整證明自己寫出來，我幫你審閱。"},
        {"role": "user", "content": "證明：給定 ε>0。因為 |x²−4|=|x−2||x+2|，而 |x+2|<5，所以 |x²−4|<5|x−2|。取 δ=min{1, ε/5}，則 0<|x−2|<δ 時 |x²−4|<5·(ε/5)=ε。得證。"},
        {"role": "assistant", "content": "整體結構正確，但有一個依據沒交代：$|x+2|<5$ 是在什麼前提下才成立的？"},
        {"role": "user", "content": "喔，要先限制 |x−2|<1，那時 1<x<3 所以 |x+2|<5。我補上：「先設 |x−2|<1，得 |x+2|<5」，這也解釋了 min 裡的 1。"},
        {"role": "assistant", "content": "正是，補上這句後每個常數都有出處，這才是完整的證明。"},
    ]},

    # 2. A5：缺漏 = N 寫成非整數 1/ε
    {"problem_id": "A5", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "思路我全懂了，解不等式找 N 就好。"},
        {"role": "assistant", "content": "那請你把完整證明寫出來，我來審閱。"},
        {"role": "user", "content": "證明：給定 ε>0，取 N=1/ε。當 n≥N 時，|1/n−0|=1/n≤1/N=ε…咦，這樣是 ≤ε 不是 <ε，總之差不多。得證。"},
        {"role": "assistant", "content": "有兩個小洞，先看第一個：$N=1/\\varepsilon$ 一定是正整數嗎？"},
        {"role": "user", "content": "不一定…要由阿基米德性質取正整數 N>1/ε。這樣一改，n≥N 時 1/n≤1/N<ε，剛好也把 ≤ 變成 <，第二個洞一起補掉了。"},
        {"role": "assistant", "content": "正確，一個修正同時堵住兩個洞：$N$ 是整數、且嚴格不等式成立。證明完整了。"},
    ]},

    # 3. B1：缺漏 = 沒排除 c 落在端點
    {"problem_id": "B1", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "反證兩個方向我都會了，可以收尾了吧。"},
        {"role": "assistant", "content": "可以，請把完整證明寫出來，我幫你檢查。"},
        {"role": "user", "content": "證明：不妨設 f(a)<0<f(b)。令 S={x∈[a,b]:f(x)<0}，非空有上界，由完備性 c=sup S 存在。若 f(c)>0，連續性使 c 左側附近 f>0，與 c=sup S 矛盾；若 f(c)<0，連續性使 c 右側附近 f<0，S 有比 c 大的元素，矛盾。故 f(c)=0。得證。"},
        {"role": "assistant", "content": "反證寫得很乾淨。但題目要求 $c\\in(a,b)$（開區間），你的 $c$ 為什麼不會是 $a$ 或 $b$？"},
        {"role": "user", "content": "因為 f(a)<0、f(b)>0 都不是零，而 f(c)=0，所以 c≠a 且 c≠b，故 c∈(a,b)。我把這句補進結尾。"},
        {"role": "assistant", "content": "正是，題目的每個要求都要對應到證明裡的一句話，現在完整了。"},
    ]},

    # 4. C2：缺漏 = 常數情形沒討論
    {"problem_id": "C2", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "極值在內部、費馬定理收尾，我懂了。"},
        {"role": "assistant", "content": "那請寫出完整證明，我來審閱。"},
        {"role": "user", "content": "證明：f 在 [a,b] 連續，由最大值定理取得最大值 M 與最小值 m。因為 f(a)=f(b)，最大或最小至少有一個在內部點 c∈(a,b) 取得。由費馬定理 f'(c)=0。得證。"},
        {"role": "assistant", "content": "主線正確，但「至少有一個在內部」有一種情形會失效：如果 $M=m$ 會發生什麼？"},
        {"role": "user", "content": "M=m 時 f 是常數，極值全在端點也沒關係，因為 f'≡0，任取 c∈(a,b) 都有 f'(c)=0。我把這個情形分開寫。"},
        {"role": "assistant", "content": "正確，補上常數情形後，兩種情況都被涵蓋，證明才算完備。"},
    ]},

    # 5. C10：缺漏 = 1/(1+ξ)<1 的依據（ξ>0）沒寫
    {"problem_id": "C10", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "均值定理給 ln(1+x)=x/(1+ξ)，剩下就是夾了。"},
        {"role": "assistant", "content": "對，請把完整證明寫出來讓我看看。"},
        {"role": "user", "content": "證明：對 f(t)=ln(1+t) 在 [0,x] 用均值定理，存在 ξ∈(0,x) 使 ln(1+x)=x/(1+ξ)。因為 1/(1+x)<1/(1+ξ)<1，兩邊乘 x 得 x/(1+x)<ln(1+x)<x。得證。"},
        {"role": "assistant", "content": "骨架對。中間那串不等式 $\\frac1{1+x}<\\frac1{1+\\xi}<1$ 的依據是什麼，你沒有寫出來？"},
        {"role": "user", "content": "依據是 0<ξ<x：所以 1<1+ξ<1+x，取倒數反向得那串不等式。另外乘 x 不變號是因為 x>0。我把這兩句補上。"},
        {"role": "assistant", "content": "正是，不等式的每一步變形都要交代方向的依據，現在無懈可擊了。"},
    ]},

    # 6. D3：缺漏 = μ∈[m,M] 沒建立就用 IVT
    {"problem_id": "D3", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "夾平均值再用介值定理，思路有了。"},
        {"role": "assistant", "content": "很好，請寫出完整證明。"},
        {"role": "user", "content": "證明：f 連續，由最大值定理有最小值 m、最大值 M。令 μ=(1/(b−a))∫f。由介值定理，存在 c∈[a,b] 使 f(c)=μ，即 ∫f=f(c)(b−a)。得證。"},
        {"role": "assistant", "content": "介值定理要求 $\\mu$ 落在 $f$ 的值域範圍內，這一步你還沒建立：為什麼 $\\mu\\in[m,M]$？"},
        {"role": "user", "content": "因為 m≤f(x)≤M 對積分保序：m(b−a)≤∫f≤M(b−a)，除以 (b−a) 得 m≤μ≤M。補在用 IVT 之前。"},
        {"role": "assistant", "content": "正確，定理的前提要先驗證再引用，這是證明寫作最重要的紀律。"},
    ]},

    # 7. E4：缺漏 = 部分和遞增沒說（單調有界缺一半）
    {"problem_id": "E4", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "裂項找上界，最後用單調有界定理，我會了。"},
        {"role": "assistant", "content": "那就寫出完整證明吧，我幫你審。"},
        {"role": "user", "content": "證明：對 k≥2 有 1/k²≤1/(k(k−1))=1/(k−1)−1/k。故 S_n≤1+(1−1/n)<2。由單調有界定理，S_n 收斂，即級數收斂。得證。"},
        {"role": "assistant", "content": "上界估得漂亮。但單調有界定理需要兩個條件，你只寫了一個：$S_n$ 為什麼是遞增的？"},
        {"role": "user", "content": "因為每一項 1/k²>0，S_{n+1}=S_n+1/(n+1)²>S_n。我把「各項為正故部分和遞增」補在開頭。"},
        {"role": "assistant", "content": "正是，「遞增」與「有上界」缺一不可，補上後定理的引用才完整。"},
    ]},

    # 8. E6：缺漏 = 沒固定 r 就用比值<1
    {"problem_id": "E6", "persona": "writeup", "kind": "writeup", "turns": [
        {"role": "user", "content": "遞推壓進幾何級數再比較，思路我有了。"},
        {"role": "assistant", "content": "請把完整證明寫出來，我來審閱。"},
        {"role": "user", "content": "證明：因為 lim|a_{n+1}/a_n|=L<1，從某個 N 起比值都小於 1，所以 |a_n|≤|a_N|·1^{n−N}=|a_N|…咦，這樣上界是常數，加總會發散。可是思路應該對啊。得證？"},
        {"role": "assistant", "content": "你自己撞到了關鍵：比值「小於 1」不夠，因為公比 1 的幾何級數不收斂。該把比值壓在什麼之下才行？"},
        {"role": "user", "content": "要先固定一個 r 使 L<r<1，由極限定義從某 N 起比值<r，遞推得 |a_n|≤|a_N|r^{n−N}，幾何級數 r<1 收斂，比較判別法收工。"},
        {"role": "assistant", "content": "正確，「插入固定的 r」正是這個證明的靈魂，你現在把它寫進去，證明就完整了。"},
    ]},
]
