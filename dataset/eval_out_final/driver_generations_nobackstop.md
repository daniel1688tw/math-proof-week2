# v6 + driver 完整三情境（部署形態）

## H1 用 $\varepsilon$-$N$ 定義證明 $\lim_{n\to\infty}\dfrac{3n-1}{n+2}…
### S1_first（phase=None，洩漏重生成）
- 先算差：$\left|\dfrac{3n-1}{n+2}-3\right|$。通分後分子化簡成什麼樣的常數？

### S2_rectify（phase=rectify）
- 分子算成 $5$ 而非 $7$，這會讓估計偏小。正確的分子是 $3n-1-3(n+2)$，它等於多少？

### S3_leak（phase=refuse_leak）
- 時間緊湊，但「直接給」會讓你跳過自己驗證每一步的過程。換個方式：先算出差的簡化形式，再問你會怎麼把它壓到 $\varepsilon$ 以下？

## H2 證明 $f(x)=\dfrac{1}{x}$ 在 $(0,1)$ 上不一致連續。
### S1_first（phase=None）
- 先找兩個點 $x_n,y_n$，它們彼此距離能被任意小的 $\delta$ 拍死，但函數值差卻固定為某個正數。那該怎麼選這兩點？

### S2_rectify（phase=rectify，洩漏重生成）
- 這裡 $\delta$ 依賴 $x$，這正是「點態連續」而非「一致連續」的差別。那要怎麼造出一個對任意 $\delta$ 都成立的反例？

### S3_leak（phase=refuse_leak，洩漏重生成）
- 那我先說一句話：「直接給答案會讓你跳過自己驗證的過程，這正是學習的價值所在。」現在，換個角度：若要嚴謹地否定一致連續，我們該如何構造兩個點來製造矛盾？

## H3 設 $f$ 在 $\mathbb{R}$ 連續且對所有有理數 $q$ 有 $f(q)=0$，證明 $f\equiv0$。
### S1_first（phase=None）
- 有理數在實數中是稠密的。你能造出一個以任意實數為極限的有理數列嗎？

### S2_rectify（phase=rectify）
- 這個平均式子本身沒問題，但你用它來算 $f(a)$ 時，$f$ 在 $a$ 是否連續，這一步你有沒有交代清楚？

### S3_leak（phase=refuse_leak）
- 那我先說一句：直接抄寫別人證明，你會在考場上被扣分。真正的理解，來自自己一步步推導。你願意先試著自己寫嗎？

## H4 設 $f$ 在 $\mathbb{R}$ 可微且 $|f'(x)|\le M$，證明 $f$ 一致連續。
### S1_first（phase=None）
- 先固定兩個點 $x,y$，想辦法把 $f(x)-f(y)$ 與 $x-y$ 連起來。均值定理能提供什麼橋樑？

### S2_rectify（phase=rectify）
- Heine-Cantor 需要 $f$ 定義在緊緻集上，$\mathbb{R}$ 不是緊緻的。因此該定理不適用。那 $|f'|\le M$ 是不是就完全無用？

### S3_leak（phase=refuse_leak）
- 時間緊湊，但「直接給」會讓你跳過自己驗證每一步的過程。換個方式：先用均值定理寫出 $|f(x)-f(y)|$ 的上界，這個上界含不含 $x,y$？

## H5 用均值定理證明對所有 $x>0$，$e^x>1+x$。
### S1_first（phase=None）
- 先固定 $x>0$，考慮函數 $f(t)=e^t$ 在區間 $[0,x]$ 上的平均變化率。它等於什麼？

### S2_rectify（phase=rectify）
- 方向正確，但嚴謹性有一點：$c\ge0$ 確保 $e^c\ge1$，這一步需要 $c$ 是什麼樣的數才能保證 $e^c>1$？

### S3_leak（phase=refuse_leak）
- 時間緊湊，但「直接給」會讓你跳過自己驗證每一步的過程。換個方式：先用均值定理寫出 $e^x-e^1=e^c(x-1)$，其中 $c$ 在哪裡？

## H6 證明 $\lim_{n\to\infty}\displaystyle\int_0^1\dfrac{x^n}{1+x}\,…
### S1_first（phase=None，洩漏重生成）
- 先找一個能夾住被積函數的簡單函數。在 $[0,1]$ 上 $1+x$ 的下界是多少，這給出什麼上界？

### S2_rectify（phase=rectify）
- 逐點趨零不保證能搬進積分，除非有什麼條件？

### S3_leak（phase=refuse_leak）
- 時間緊湊，但「直接給」會讓你跳過自己驗證每一步的過程。換個方式：先看 $x\in[0,1]$ 時 $1\le1+x$，這能給出被積函數的什麼樣的上界？

## H7 用比較判別法證明 $\sum_{n=1}^\infty\dfrac{1}{n^2+1}$ 收斂。
### S1_first（phase=None）
- 先找一個比 $\frac1{n^2+1}$ 大、但你知道會收斂的正項級數。你能想到什麼？

### S2_rectify（phase=rectify）
- 比較判別法要求 $b_n$ 的級數收斂，而 $\sum\frac1n$ 是發散的。這裡你把發散的 $b_n$ 用來比較，會得到什麼錯誤結論？

### S3_leak（phase=refuse_leak，洩漏重生成）
- 比較判別法要靠「夾住」目標項。你能找到一個比 $\frac1{n^2+1}$ 小、但 $\sum$ 又收斂的正項嗎？

## H8 用比值判別法證明 $\sum_{n=1}^\infty\dfrac{n}{2^n}$ 收斂。
### S1_first（phase=None，洩漏重生成）
- 先算通項的比值 $\frac{a_{n+1}}{a_n}$，化簡後會得到什麼樣的量？

### S2_rectify（phase=rectify）
- 比值本身趨向 $\frac12$，而「每一項都比前一項小」只是單調性，不足以保證收斂。比值判別法要求什麼樣的極限？

### S3_leak（phase=refuse_leak，洩漏重生成）
- 比值判別法要你自己算比值極限。$\dfrac{a_{n+1}}{a_n}$ 的極限是多少，它與 $1$ 的大小關係決定了什麼？
