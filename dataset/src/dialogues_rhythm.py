# -*- coding: utf-8 -*-
"""節奏錯位對話（10 條）：內容由 Claude 手寫。

M4 完整對話測試發現的缺陷：學生沒按預期順序回答（跳步/只答一半/答非所問）時，
模型不會察覺邏輯鏈被跳過，反而自己搶先講結論、過早宣告完成。
本模組的訓練訊號：助教必須「對照目前這一步」檢查學生回答——
  * 學生跳到後面的步驟 → 肯定其方向，但拉回還沒建立的那一步
  * 學生只答了一半 → 追問缺的那一半，不往前走
  * 學生答非所問 → 指出所答屬於哪一步，重新聚焦當前問題
  * 中間步驟未補完前，絕不宣告「證完了」
"""

DIALOGUES = [
    # 1. A2：學生跳到結論（δ=ε/5），但 |x+2| 的界還沒建立
    {"problem_id": "A2", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "我分解成 |x−2||x+2| 了，接下來怎麼辦？"},
        {"role": "assistant", "content": "很好。兩個因子中，哪一個是你能用 δ 直接控制的？"},
        {"role": "user", "content": "我知道答案了：取 δ=min{1, ε/5} 就證完了！"},
        {"role": "assistant", "content": "結論正確，但你跳過了一步：$\\varepsilon/5$ 裡的 $5$ 是哪裡來的？這需要先建立 $|x+2|$ 的上界。"},
        {"role": "user", "content": "喔對，要先設 |x−2|<1，那時 1<x<3，所以 |x+2|<5。"},
        {"role": "assistant", "content": "正是，現在 $\\delta=\\min\\{1,\\varepsilon/5\\}$ 的每個成分都有了依據，證明才算完整。"},
    ]},

    # 2. A3：學生答非所問（回答了後面「合併門檻」的步驟）
    {"problem_id": "A3", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "要證和的極限，我該從哪裡下手？"},
        {"role": "assistant", "content": "先想：$|(a_n+b_n)-(L+M)|$ 能用哪個不等式拆成兩塊？"},
        {"role": "user", "content": "取 N=max{N_1,N_2} 就可以了。"},
        {"role": "assistant", "content": "那是最後合併門檻的步驟，你先跳過了拆項。回到眼前：這個絕對值被什麼不等式壓住？"},
        {"role": "user", "content": "喔，三角不等式：≤|a_n−L|+|b_n−M|。"},
        {"role": "assistant", "content": "對，先拆項、再各壓 $\\varepsilon/2$、最後才輪到你剛說的 $N=\\max\\{N_1,N_2\\}$。順序清楚了嗎？"},
        {"role": "user", "content": "清楚了，我剛剛把第三步當成第一步了。"},
        {"role": "assistant", "content": "很好，證明的每一步都有它的位置，依序建立才不會漏掉依據。"},
    ]},

    # 3. B1：學生答錯依據（把連續性當成上確界存在的理由）
    {"problem_id": "B1", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "我設了 S={x∈[a,b]:f(x)<0}，然後呢？"},
        {"role": "assistant", "content": "$S$ 非空且有上界，它的上確界為什麼存在？"},
        {"role": "user", "content": "因為 f 是連續的。"},
        {"role": "assistant", "content": "連續性是稍後排除 $f(c)\\ne0$ 時才登場的。上確界的存在靠的是實數的哪個公理？"},
        {"role": "user", "content": "喔，是完備性（最小上界公理），跟 f 連不連續無關。"},
        {"role": "assistant", "content": "正是，先由完備性拿到 $c=\\sup S$，連續性留給下一步的反證使用。"},
    ]},

    # 4. B10：學生過早宣告完成（異號還沒證就要用 IVT）
    {"problem_id": "B10", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "我設 g(x)=f(x+1/2)−f(x)，所以由介值定理存在 c 使 g(c)=0，證完了！"},
        {"role": "assistant", "content": "還沒完：介值定理需要「端點異號」這個前提，你還沒建立它。$g(0)+g(\\tfrac12)$ 等於多少？"},
        {"role": "user", "content": "算一下：g(0)+g(1/2)=f(1)−f(0)=0，所以兩者異號或其一為零。"},
        {"role": "assistant", "content": "對，這一步補上了 IVT 的前提，現在引用它才是合法的。整個論證的順序你能重述一次嗎？"},
        {"role": "user", "content": "先造 g、再算端點和為零得異號、最後才用 IVT 取得 c。"},
        {"role": "assistant", "content": "完全正確，前提先行、定理後用，這才是完整的證明。"},
    ]},

    # 5. C3：學生答非所問（端點條件問題答成 Rolle 結論）
    {"problem_id": "C3", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "我造了 g(x)=f(x)−f(a)−[(f(b)−f(a))/(b−a)](x−a)。"},
        {"role": "assistant", "content": "很好。要對 $g$ 用 Rolle，先驗證它的端點條件：$g(a)$ 和 $g(b)$ 各是多少？"},
        {"role": "user", "content": "Rolle 給我們 g'(c)=0。"},
        {"role": "assistant", "content": "那是驗完端點之後的結論。先回到驗證本身：把 $x=a$ 代入 $g$，得到什麼？"},
        {"role": "user", "content": "g(a)=0，然後 g(b)=f(b)−f(a)−(f(b)−f(a))=0，兩端相等。"},
        {"role": "assistant", "content": "正是，端點條件成立後，你剛才說的 $g'(c)=0$ 才站得住腳。"},
    ]},

    # 6. C7：學生只答一半（只給了右側，左側沒答）
    {"problem_id": "C7", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "局部極大給 f(c+h)≤f(c)，接下來看差商對吧？"},
        {"role": "assistant", "content": "對。先看 $h>0$ 的那一側，差商的符號是什麼？"},
        {"role": "user", "content": "分子≤0、分母>0，所以差商≤0，右導數≤0。左側應該也差不多吧，反正結論就是 0。"},
        {"role": "assistant", "content": "「差不多」不能當論證。左側分母是負的，差商的符號會相同還是相反？"},
        {"role": "user", "content": "會相反：分子≤0、分母<0，差商≥0，所以左導數≥0。"},
        {"role": "assistant", "content": "對，兩側夾出 $f'(c)=0$——每一側都要各自寫清楚，符號論證不能用「差不多」帶過。"},
    ]},

    # 7. D1：學生過早宣告完成（矛盾的量化下界還沒給）
    {"problem_id": "D1", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "反證：若某點 f(x_0)>0，連續性讓附近一段都是正的，跟積分為 0 矛盾，證完了！"},
        {"role": "assistant", "content": "方向全對，但「矛盾」還差一個量化步驟：那一段上的積分到底至少是多少？"},
        {"role": "user", "content": "那段上 f>f(x_0)/2，長度是 d−c，所以積分至少 (f(x_0)/2)(d−c)>0。"},
        {"role": "assistant", "content": "還有一小步：這個正下界怎麼傳給整個 $\\int_a^b f$？"},
        {"role": "user", "content": "因為 f≥0，整體積分不小於那一段的積分，所以 ∫f>0，跟 =0 矛盾。"},
        {"role": "assistant", "content": "現在才是完整的矛盾：正下界、非負性傳遞，缺一不可。"},
    ]},

    # 8. D6：學生跳到最後代入（常數還沒定就代 b）
    {"problem_id": "D6", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "設 G(x)=∫_a^x f，由 FTC-1 得 G'=f=F'，所以 ∫f=F(b)−F(a)，完成！"},
        {"role": "assistant", "content": "中間跳了一步：從 $G'=F'$ 到最後的等式之間，你用了什麼還沒說出口的事實？"},
        {"role": "user", "content": "嗯…G'=F' 所以 G−F 是常數。"},
        {"role": "assistant", "content": "對，而那個常數是多少，你要用哪個點定出來？"},
        {"role": "user", "content": "用 x=a：G(a)=0，所以常數是 −F(a)，於是 G(b)=F(b)−F(a)。"},
        {"role": "assistant", "content": "正是，「差常數＋端點定常數」補上後，你的結論才真正成立。"},
    ]},

    # 9. E1：學生過早宣告完成（sup 是極限還沒證）
    {"problem_id": "E1", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "數列遞增有上界，令 L=sup{a_n}，L 就是極限，證完了！"},
        {"role": "assistant", "content": "「sup 就是極限」正是要證的部分。給定 $\\varepsilon>0$，你要先找到什麼？"},
        {"role": "user", "content": "找一個 N 使 a_N>L−ε，因為 L−ε 不是上界。"},
        {"role": "assistant", "content": "對。接著哪個性質讓這個下界傳給所有 $n\\ge N$？"},
        {"role": "user", "content": "遞增性：n≥N 時 a_n≥a_N>L−ε，加上 a_n≤L，就有 |a_n−L|<ε。"},
        {"role": "assistant", "content": "這才是完整的證明——sup 給逼近、遞增給傳遞，兩者都要明說。"},
    ]},

    # 10. E8：學生答非所問（問偶子列，答成餘項估計）
    {"problem_id": "E8", "persona": "rhythm", "kind": "rhythm", "turns": [
        {"role": "user", "content": "交錯級數，我要從哪裡看起？"},
        {"role": "assistant", "content": "先看偶數部分和：$S_{2n+2}-S_{2n}$ 等於什麼？"},
        {"role": "user", "content": "誤差不超過第一個被捨去的項，|S−S_n|≤b_{n+1}。"},
        {"role": "assistant", "content": "那是收斂證完之後的餘項估計，現在還用不上。回到偶數子列：那個差等於哪兩項相減？"},
        {"role": "user", "content": "=b_{2n+1}−b_{2n+2}≥0（遞減），所以偶數子列遞增。"},
        {"role": "assistant", "content": "對，先把兩個子列的單調性與同極限建立好，你剛才的餘項估計才有立足點。"},
    ]},
]
