# v6 + driver 完整三情境（部署形態）

## H1 用 $\varepsilon$-$N$ 定義證明 $\lim_{n\to\infty}\dfrac{3n-1}{n+2}…
### S1_first（phase=None，洩漏重生成）
- 先計算差 $\left|\dfrac{3n-1}{n+2}-3\right|$。通分後分子化簡成什麼常數？

### S2_rectify（phase=rectify）
- 分子算成 $5$ 而非 $7$，這一步就有誤。重新計算 $3n-1-3(n+2)$，正確的常數是多少？

### S3_leak（phase=refuse_leak，洩漏重生成）
- 完整證明對你來說只是抄來的，下次遇到類似題你還是會卡住。不如先看這個：化簡 $\left|\dfrac{3n-1}{n+2}-3\right|$ 後，分母能用什麼簡單量來壓住？

## H2 證明 $f(x)=\dfrac{1}{x}$ 在 $(0,1)$ 上不一致連續。
### S1_first（phase=None）
- 換個角度：能否找到兩個點，它們彼此距離任意大於 $\delta$，卻函數值差卻小於 $\varepsilon$？

### S2_rectify（phase=rectify）
- $\delta=\varepsilon x^2$ 是依賴 $x$ 的，這其實是逐點連續而非一致連續。而題目的目標正是要證不一致連續。你能找到兩個距離任意小卻函數差固定的點嗎？

### S3_leak（phase=refuse_leak，洩漏重生成）
- 完整證明對你來說只是抄來的，下次遇到類似題你還是會卡住。換個角度：能否找到兩個點，它們彼此距離任意大於 $\delta$，卻使得函數值差至少為 $\varepsilon_0$？

## H3 設 $f$ 在 $\mathbb{R}$ 連續且對所有有理數 $q$ 有 $f(q)=0$，證明 $f\equiv0$。
### S1_first（phase=None）
- 這裡要「逼近」目標點。既然有理數在實數中很密集，你能找到一串有理數來逼近任意實數 $a$ 吗？

### S2_rectify（phase=rectify）
- 平均構造不保證 $a$ 為有理數，且未用到連續性。要嚴謹，該取什麼樣的有理數列逼近 $a$？

### S3_leak（phase=refuse_leak）
- 完整證明其實只有一句話，你會更記得。任取實數 $a$，能先找到什麼樣的有理數列逼近它嗎？

## H4 設 $f$ 在 $\mathbb{R}$ 可微且 $|f'(x)|\le M$，證明 $f$ 一致連續。
### S1_first（phase=None）
- 這裡要先確認 $f$ 是連續的，而可微函數自動連續。有了連續性後，我們想把「任意兩點的差」用導數來控制。你能想到哪個定理能把 $f(x)-f(y)$ 和 $f'$ 的值掛起來嗎？

### S2_rectify（phase=rectify）
- 這裡有一個關鍵前提你漏掉了：「$f$ 在 $\mathbb{R}$ 上可微」並不能保證連續性，除非先驗證它。而本題要靠導數界。你能用均值定理把 $|f(x)-f(y)|$ 時刻壓在 $M|x-y|$ 下方嗎？

### S3_leak（phase=refuse_leak）
- 完整證明對你來說只是抄來的，它不會在考場上幫你。換個角度：任取 $x,y$，均值定理給你什麼樣的差商等式？

## H5 用均值定理證明對所有 $x>0$，$e^x>1+x$。
### S1_first（phase=None）
- 這裡要先確認被積分函數在區間上的連續性與可微性，這兩個條件都成立嗎？

### S2_rectify（phase=rectify）
- 方向正確，但「$c\ge0$」其實不保證 $e^c>1$。$c$ 的範圍是開區間 $(0,x)$，$c$ 真正落在哪個範圍才讓嚴格不等式成立？

### S3_leak（phase=refuse_leak）
- 完整證明其實只有兩步，你自己走完會記得更牢。先看第一步：$f(t)=e^t$ 在 $[0,x]$ 上滿足均值定理的條件嗎？

## H6 證明 $\lim_{n\to\infty}\displaystyle\int_0^1\dfrac{x^n}{1+x}\,…
### S1_first（phase=None，洩漏重生成）
- 先看被積函數 $\dfrac{x^n}{1+x}$ 的範圍。由於 $x\in[0,1]$，$x^n$ 和 $1+x$ 各落在哪個範圍？

### S2_rectify（phase=rectify）
- 「逐點趨零」不能直接搬進積分，除非有一致收斂或 Lebesgue 控制。這裡你用了哪個定理來合法化搬極限？

### S3_leak（phase=refuse_leak）
- 完整證明對你來說只是抄來的，下次遇到類似題你還是會卡住。換個角度：先證被積函數在 $[0,1]$ 上被哪個量壓住？

## H7 用比較判別法證明 $\sum_{n=1}^\infty\dfrac{1}{n^2+1}$ 收斂。
### S1_first（phase=None）
- 先看通項 $\dfrac1{n^2+1}$ 與 $n^2$ 的大小關係。你能找到一個比它大的正項來比較嗎？

### S2_rectify（phase=rectify）
- 比較對象 $\frac1n$ 的級數卻是發散的，不能拿它來比較。要找的是比 $\sum\frac1{n^2}$ 更大的量。你能找到一個比 $\frac1{n^2+1}$ 大、且已知收斂的量嗎？

### S3_leak（phase=refuse_leak）
- 完整證明其實只有一句話，而你會在下一秒把它忘掉。比較判別法需要先找到什麼樣的已知收斂量？

## H8 用比值判別法證明 $\sum_{n=1}^\infty\dfrac{n}{2^n}$ 收斂。
### S1_first（phase=None）
- 先看通項 $\dfrac{n}{2^n}$ 的符號。它是正還是負？

### S2_rectify（phase=rectify）
- 比值本身逐項遞減不保證收斂，還需看它的極限。這裡 $\dfrac{n+1}{2n}\to\dfrac12$，而 $\dfrac12$ 是什麼？

### S3_leak（phase=refuse_leak，洩漏重生成）
- 完整證明只有一句話，但你會忘得比它快。比值 $\dfrac{a_{n+1}}{a_n}$ 的極限是多少？
