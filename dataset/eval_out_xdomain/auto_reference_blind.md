# 備課管線盲測（不給手寫解，管線自證＋自驗）

## H1（verified，615.2s）
> 用 $\varepsilon$-$N$ 定義證明 $\lim_{n\to\infty}\dfrac{3n-1}{n+2}=3$。

### 自動參考解（人工核對正確性）
任取 $\varepsilon > 0$。需證明存在正整數 $N$，使得當 $n > N$ 時，$\left| \dfrac{3n - 1}{n + 2} - 3 \right| < \varepsilon$。

首先計算差值：
$$
\left| \dfrac{3n - 1}{n + 2} - 3 \right| = \left| \dfrac{(3n - 1) - 3(n + 2)}{n + 2} \right| = \left| \dfrac{-7}{n + 2} \right| = \dfrac{7}{n + 2},
$$
此步依據為分式減法運算規則與絕對值性質（因 $n$ 為正整數，故 $n + 2 > 0$）。

由 $\dfrac{7}{n + 2} < \varepsilon$ 得 $n + 2 > \dfrac{7}{\varepsilon}$，即 $n > \dfrac{7}{\varepsilon} - 2$。  
因實數 $\dfrac{7}{\varepsilon} - 2$ 存在，據實數性質（對任意實數 $x$，存在正整數 $N$ 滿足 $N > x$），故存在正整數 $N$ 達到 $N > \dfrac{7}{\varepsilon} - 2$。

當 $n > N$ 時（因 $n$ 為正整數，故 $n \geq N + 1$），有：
$$
n + 2 > N + 2.
$$
又因 $N > \dfrac{7}{\varepsilon} - 2$，故 $N + 2 > \dfrac{7}{\varepsilon}$。因此，
$$
n + 2 > \dfrac{7}{\varepsilon} \quad \Rightarrow \quad \dfrac{7}{n + 2} < \varepsilon.
$$

結論：對任意 $\varepsilon > 0$，存在正整數 $N$ 使得當 $n > N$ 時，$\left| \dfrac{3n - 1}{n + 2} - 3 \right| < \varepsilon$。$\blacksquare$

### 教學步驟（4 步）
1. 任取 $\varepsilon > 0$，需證明存在正整數 $N$ 使得當 $n > N$ 時，$\left| \dfrac{3n - 1}{n + 2} - 3 \right| < \varepsilon$。（確認：存在正整數 N）
2. $\left| \dfrac{3n - 1}{n + 2} - 3 \right|$ 計算：$= \left| \dfrac{(3n - 1) - 3(n + 2)}{n + 2} \right| = \left| \dfrac{-7}{n + 2} \right| = \dfrac{7}{n + 2}$（確認：$\dfrac{7}{n+2}）
3. 由 $\dfrac{7}{n+2} < \varepsilon$ 可得 $n > \dfrac{7}{\varepsilon} - 2$。（確認：$n > \dfrac{7}{\varepsilon} - 2$）
4. 因實數 $x = \dfrac{7}{\varepsilon} - 2$ 存在，存在正整數 $N$ 滿足 $N > x$。當 $n > N$ 時，有 $n + 2 > N + 2 > \dfrac{7}{\varepsilon}$，故 $\dfrac{7}{n+2} < \varepsilon$。（確認：$N + 2 > \dfrac{7}{\varepsilon}$）

## H3（verified，401.6s）
> 設 $f$ 在 $\mathbb{R}$ 連續且對所有有理數 $q$ 有 $f(q)=0$，證明 $f\equiv0$。

### 自動參考解（人工核對正確性）
任取 $ x \in \mathbb{R} $。由有理數集 $\mathbb{Q}$ 在 $\mathbb{R}$ 中的稠密性（對任意 $ x \in \mathbb{R} $ 與 $ \varepsilon > 0 $，存在 $ q \in \mathbb{Q} $ 滿足 $ |x - q| < \varepsilon $）可知，對每個正整數 $ n $，取 $ q_n \in \mathbb{Q} $ 使得 $ |x - q_n| < \frac{1}{n} $。因此序列 $ \{ q_n \} $ 收斂於 $ x $。

由於 $ f $ 在 $\mathbb{R}$ 上連續，故對收斂至 $ x $ 的序列 $ \{ q_n \} $ 有
$$
\lim_{n \to \infty} f(q_n) = f(x).
$$

題設條件指出：對所有 $ q \in \mathbb{Q} $，$ f(q) = 0 $。因此 $ f(q_n) = 0 $ 對所有 $ n \in \mathbb{N} $ 成立。

故
$$
\lim_{n \to \infty} f(q_n) = \lim_{n \to \infty} 0 = 0.
$$

由上述兩式可得 $ f(x) = 0 $。因 $ x \in \mathbb{R} $ 為任意，故對所有 $ x \in \mathbb{R} $，$ f(x) = 0 $。

$\blacksquare$

### 教學步驟（5 步）
1. 對任意 $ x \in \mathbb{R} $ 與 $ \varepsilon > 0 $，存在有理數 $ q $ 滿足 $ |x - q| < \varepsilon $（有理數在實數中稠密）。（確認：若 $ x = \sqrt{2} $、$ \varepsilon = 0.1 $，是否存在有理數 $ q $？）
2. 對每個正整數 $ n $，取 $ q_n \in \mathbb{Q} $ 滿足 $ |x - q_n| < \frac{1}{n} $。則序列 $ \{q_n\} $ 收斂於 $ x $。（確認：序列 $ \{q_n\} $ 收斂到哪個數？）
3. 由於 $ f $ 在 $ \mathbb{R} $ 上連續，對收斂至 $ x $ 的序列 $ \{q_n\} $ 有 $ \lim_{n \to \infty} f(q_n) = f(x) $。（確認：$ \lim_{n \to \infty} f(q_n) $ 等於什麼？）
4. 題設條件指出對所有有理數 $ q $ 有 $ f(q) = 0 $，因此 $ f(q_n) = 0 $ 對所有 $ n $ 成立。（確認：因為 $ q_n $ 是有理數，$ f(q_n) $ 等於什麼？）
5. 故 $ \lim_{n \to \infty} f(q_n) = \lim_{n \to \infty} 0 = 0 $。（確認：$ \lim_{n \to \infty} 0 $ 等於什麼？）

## H5（verified，288.1s）
> 用均值定理證明對所有 $x>0$，$e^x>1+x$。

### 自動參考解（人工核對正確性）
設函數 $ f(t) = e^t $。因 $ e^t $ 在實數域上連續且可導，故於區間 $[0, x]$ 上連續，在開區間 $(0, x)$ 內可導（$x > 0$）。由拉格朗日均值定理，存在某點 $ c \in (0, x) $ 使得

$$
\frac{f(x) - f(0)}{x - 0} = f'(c).
$$

代入計算得：

$$
\frac{e^x - e^0}{x} = e^c,
$$

即

$$
\frac{e^x - 1}{x} = e^c.
$$

因 $ c \in (0, x) $ 且 $ x > 0 $，故 $ c > 0 $。又因指數函數 $ e^t $ 在實數域上嚴格遞增，且 $ e^0 = 1 $，故有 $ e^c > e^0 = 1 $。因此，

$$
\frac{e^x - 1}{x} > 1.
$$

由於 $ x > 0 $，兩邊同乘以 $ x $ 得不等式：

$$
e^x - 1 > x,
$$

即對所有 $ x > 0 $，有 $ e^x > 1 + x $。

$\blacksquare$

### 教學步驟（6 步）
1. 設函數 $ f(t) = e^t $。它在實數域上連續且可導。（確認：e^t 可導嗎？）
2. 在區間 [0, x]（$x > 0$）上，由拉格朗日均值定理，存在 $ c \in (0, x) $ 使得 $ \frac{f(x) - f(0)}{x} = f'(c) $。（確認：均值定理給出的等式是什麼？）
3. 代入 $ f(t) = e^t $，得 $ \frac{e^x - 1}{x} = e^c $。（確認：代入後的等式是什麼？）
4. 因 $ c \in (0, x) $ 且 $ x > 0 $，故 $ c > 0 $。（確認：c 的範圍是什麼？）
5. 指數函數 $ e^t $ 嚴格遞增，且 $ e^0 = 1 $，故 $ e^c > 1 $。（確認：若 c > 0 則 $ e^c $ 與 1 的大小？）
6. 由 $ \frac{e^x - 1}{x} > 1 $ 和 $ x > 0 $，兩邊同乘以 $ x $ 得 $ e^x > 1 + x $。（確認：最終不等式是什麼？）

## H7（verified，357.3s）
> 用比較判別法證明 $\sum_{n=1}^\infty\dfrac{1}{n^2+1}$ 收斂。

### 自動參考解（人工核對正確性）
考慮 $ a_n = \dfrac{1}{n^2 + 1} $ 與 $ b_n = \dfrac{1}{n^2} $。對任意正整數 $ n \geq 1 $，有  
$$
n^2 + 1 > n^2 \quad (\text{因 } 1 > 0)
\implies a_n < b_n.
$$  
此不等式成立的依據為：若 $ x, y > 0 $ 且 $ x > y $ 則 $ \dfrac{1}{x} < \dfrac{1}{y} $（實數倒數函數單調性）。  

設 $ b_n = \dfrac{1}{n^2} $，已知級數 $ \sum_{n=1}^\infty b_n $ 收斂（因係 $ p $-級數，$ p = 2 > 1 $；此結論依賴於 $ p $-級數收斂定理：當 $ p > 1 $ 時，$ \sum_{n=1}^\infty \dfrac{1}{n^p} $ 收斂）。  

由比較判別法（直接比較形式）：因對所有 $ n \geq 1 $ 有 $ a_n > 0 $（分母為正整數）且 $ a_n < b_n $，而 $ \sum_{n=1}^\infty b_n $ 收斂，故原級數 $ \sum_{n=1}^\infty a_n $ 收斂。  

$\blacksquare$

### 教學步驟（4 步）
1. 考慮級數 $\sum_{n=1}^\infty \dfrac{1}{n^2 + 1}$，並選擇比較序列 $ b_n = \dfrac{1}{n^2} $（確認：b_n 是什麼？）
2. 對任意正整數 $ n \geq 1 $，有 $ n^2 + 1 > n^2 $（因 $ 1 > 0 $）（確認：n²+1 與 n² 哪個大？）
3. 由 $ n^2 + 1 > n^2 $ 和實數倒數函數單調性，得 $ \dfrac{1}{n^2 + 1} < \dfrac{1}{n^2} $（確認：若 x > y > 0，則 1/x 與 1/y 的大小關係？）
4. 級數 $\sum_{n=1}^\infty b_n = \sum_{n=1}^\infty \dfrac{1}{n^2}$ 是收斂的 p-級數（p=2>1），且 $ a_n > 0 $，故由比較判別法得原級數收斂（確認：原級數收斂的依據是什麼？）

## M1（verified，463.8s）
> 設 $f_n(x)=\dfrac{nx}{1+n^2x^2}$，$x\in[0,1]$。證明 $\{f_n\}$ 在 $[0,1]$ 上逐點收斂於 $0$，但不一致收斂。

### 自動參考解（人工核對正確性）
設 $f_n(x)=\dfrac{nx}{1+n^2x^2}$，$x\in[0,1]$。證明 $\{f_n\}$ 在 $[0,1]$ 上逐點收斂於 $0$，但不一致收斂。

首先證明 $\{f_n\}$ 在 $[0,1]$ 上逐點收斂於 $0$。  
對任意固定 $x \in [0,1]$，分兩種情況討論：  
1. 若 $x = 0$，則 $f_n(0) = \dfrac{n \cdot 0}{1 + n^2 \cdot 0^2} = 0$，故 $\lim_{n \to \infty} f_n(x) = 0$。  
2. 若 $x > 0$，對任意 $\varepsilon > 0$，取正整數 $N = \left\lceil \dfrac{1}{x \varepsilon} \right\rceil + 1$。則當 $n \geq N$ 時，有  
$$
|f_n(x)| = \dfrac{nx}{1 + n^2 x^2} < \dfrac{nx}{n^2 x^2} = \dfrac{1}{n x},
$$  
此處利用了 $1 > 0$ 故分母 $1 + n^2 x^2 > n^2 x^2$（因 $x > 0$ 且 $n \geq 1$）。又因 $n \geq N = \left\lceil \dfrac{1}{x \varepsilon} \right\rceil + 1$，故 $\dfrac{1}{n x} < \varepsilon$。因此，$\lim_{n \to \infty} f_n(x) = 0$。

其次證明 $\{f_n\}$ 在 $[0,1]$ 上不一致收斂於 $0$。  
計算 $f_n(x)$ 的極值點：導數為  
$$
f_n'(x) = \dfrac{n - n^3 x^2}{(1 + n^2 x^2)^2}.
$$  
令 $f_n'(x) = 0$，得臨界點 $x = \dfrac{1}{n}$（因 $x \geq 0$）。此點在區間 $[0,1]$ 內（因 $n \geq 1$ 時 $\dfrac{1}{n} \leq 1$）。計算得  
$$
f_n\left(\dfrac{1}{n}\right) = \dfrac{n \cdot \dfrac{1}{n}}{1 + n^2 \cdot \left(\dfrac{1}{n}\right)^2} = \dfrac{1}{1 + 1} = \dfrac{1}{2}.
$$  
取 $\varepsilon_0 = \dfrac{1}{4}$，對任意正整數 $N$，令 $n = N$、$x_N = \dfrac{1}{N} \in [0,1]$（因 $N \geq 1$），則  
$$
|f_N(x_N)| = f_N\left(\dfrac{1}{N}\right) = \dfrac{1}{2} > \varepsilon_0.
$$  
故 $\{f_n\}$ 在 $[0,1]$ 上不一致收斂於 $0$。

$\blacksquare$

### 教學步驟（5 步）
1. 當 $x=0$ 時，$f_n(0) = \dfrac{n \cdot 0}{1 + n^2 \cdot 0^2} = 0$（確認：f_n(0) 是多少？）
2. 對於 $x > 0$，有 $1 + n^2 x^2 > n^2 x^2$（因 $1 > 0$），故 $|f_n(x)| < \dfrac{nx}{n^2 x^2} = \dfrac{1}{n x}$（確認：|f_n(x)| 與 $\dfrac{1}{n x}$ 的關係？）
3. 對於固定 $x > 0$，$\lim_{n \to \infty} \dfrac{1}{n x} = 0$（確認：$\lim_{n \to \infty} \dfrac{1}{n x}$ 等於多少？（$x$ 固定 $>0$））
4. $f_n'(x) = \dfrac{n(1 - n^2 x^2)}{(1 + n^2 x^2)^2}$，令其為零得臨界點 $x=\dfrac{1}{n}$（確認：f_n 的臨界點是什麼？）
5. 在 $x=\dfrac{1}{n}$ 時，$f_n(\dfrac{1}{n}) = \dfrac{1}{2}$。取 $\varepsilon_0 = \dfrac{1}{4}$，則對於任意正整數 $N$，有 $f_N(\dfrac{1}{N}) > \varepsilon_0$（確認：$f_n(1/n)$ 等於多少？）

## M2（verified，427.2s）
> 證明對所有實數 $x$，$\cos x\ge1-\dfrac{x^2}{2}$。

### 自動參考解（人工核對正確性）
定義函數 $f(x) = \cos x - 1 + \dfrac{x^2}{2}$。需證 $\forall x \in \mathbb{R},\ f(x) \geq 0$。

首先，驗證 $x=0$ 時等號成立：$f(0) = \cos 0 - 1 + \dfrac{0^2}{2} = 1 - 1 + 0 = 0$。

其次，計算一階導數：$f'(x) = -\sin x + x$。

證明 $f'(x)$ 在 $x \geq 0$ 時非負，在 $x \leq 0$ 時非正：

- 對於 $x \geq 0$，令 $h(x) = x - \sin x$。則 $h(0) = 0$，且 $h'(x) = 1 - \cos x \geq 0$（因 $\forall x,\ \cos x \leq 1$）。又因 $h'(x) = 0$ 當且僅當 $\cos x = 1$（即 $x = 2k\pi$, $k \in \mathbb{Z}$），但 $h(x)$ 在 $[0, +\infty)$ 上嚴格遞增（因 $h'(x) > 0$ 除離散點外）。故 $\forall x \geq 0$, $h(x) \geq h(0) = 0$，即 $f'(x) \geq 0$。

- 對於 $x \leq 0$，令 $t = -x \geq 0$，則 $f'(x) = f'(-t) = -t + \sin t = -(t - \sin t)$。由上可知 $\forall t \geq 0$, $t - \sin t \geq 0$，故 $f'(x) \leq 0$。

由此可知，$f(x)$ 在 $(-\infty, 0]$ 上嚴格遞減，在 $[0, +\infty)$ 上嚴格遞增。因此，$x = 0$ 為 $f(x)$ 唯一臨界點且為全局最小值點。又因 $f(0) = 0$，故 $\forall x \in \mathbb{R}$, $f(x) \geq 0$。

即對所有實數 $x$，$\cos x \geq 1 - \dfrac{x^2}{2}$。

$\blacksquare$

### 教學步驟（6 步）
1. 定義函數 $f(x) = \cos x - 1 + \dfrac{x^2}{2}$。需證 $\forall x \in \mathbb{R},\ f(x) \geq 0$。（確認：這一步的推理你能自己複述一遍嗎？）
2. 首先，驗證 $x=0$ 時等號成立：$f(0) = \cos 0 - 1 + \dfrac{0^2}{2} = 1 - 1 + 0 = 0$。（確認：這一步的推理你能自己複述一遍嗎？）
3. 其次，計算一階導數：$f'(x) = -\sin x + x$。（確認：這一步的推理你能自己複述一遍嗎？）
4. 證明 $f'(x)$ 在 $x \geq 0$ 時非負，在 $x \leq 0$ 時非正：（確認：這一步的推理你能自己複述一遍嗎？）
5. - 對於 $x \geq 0$，令 $h(x) = x - \sin x$。則 $h(0) = 0$，且 $h'(x) = 1 - \cos x \geq 0$（因 $\forall x,\ \cos x \leq 1$）。又因 $h'(x) = 0$ 當且僅當 $\cos x = 1$（即 $x = 2k\pi$, $k \in \mathbb{Z}$），但 $h(x)$ 在 $[0, +\infty)$ 上嚴格遞增（因 $h'(x) > 0$ 除離散點外）。故 $\forall x \geq 0$, $h(x) \geq h(0) = 0$，即 $f'(x) \geq 0$。（確認：這一步的推理你能自己複述一遍嗎？）
6. - 對於 $x \leq 0$，令 $t = -x \geq 0$，則 $f'(x) = f'(-t) = -t + \sin t = -(t - \sin t)$。由上可知 $\forall t \geq 0$, $t - \sin t \geq 0$，故 $f'(x) \leq 0$。（確認：這一步的推理你能自己複述一遍嗎？）

## M4（unverified，602.1s）
> 設 $f$ 在 $[a,b]$ 上可微（不假設 $f'$ 連續），且 $f'(a)<k<f'(b)$。證明存在 $c\in(a,b)$ 使 $f'(c)=k$。（此為 Darboux 定理：導函數即使不連續，仍具介值性質。）

（管線拒絕背書 → 部署時走同學模式）

## M5（verified，941.8s）
> 設 $f$ 在 $[0,1]$ 連續且遞增，證明 $\displaystyle\int_0^1 xf(x)\,dx\ge\frac12\int_0^1 f(x)\,dx$。

### 自動參考解（人工核對正確性）
考慮差值 $\displaystyle \int_0^1 x f(x) \, dx - \frac{1}{2} \int_0^1 f(x) \, dx = \int_0^1 \left( x - \frac{1}{2} \right) f(x) \, dx$。  
由於 $f$ 在 $[0,1]$ 上連續且遞增（即對任意 $x < y$ 有 $f(x) \leq f(y)$），將積分區間拆分為 $\left[0, \frac{1}{2}\right]$ 與 $\left[\frac{1}{2}, 1\right]$。  
令  
$$
I = \int_0^{\frac{1}{2}} \left( x - \frac{1}{2} \right) f(x) \, dx + \int_{\frac{1}{2}}^1 \left( x - \frac{1}{2} \right) f(x) \, dx.
$$  
對第一個積分，作變數替換 $t = 1 - x$。當 $x = 0$ 時 $t = 1$；當 $x = \frac{1}{2}$ 時 $t = \frac{1}{2}$，且 $dx = -dt$。代入得：  
$$
\int_0^{\frac{1}{2}} \left( x - \frac{1}{2} \right) f(x) \, dx = \int_{\frac{1}{2}}^1 \left( \frac{1}{2} - t \right) f(1 - t) \, dt.
$$  
因此，$I$ 可表示為：  
$$
I = \int_{\frac{1}{2}}^1 \left( \frac{1}{2} - t \right) f(1 - t) \, dt + \int_{\frac{1}{2}}^1 \left( t - \frac{1}{2} \right) f(t) \, dt = \int_{\frac{1}{2}}^1 \left( t - \frac{1}{2} \right) \left[ f(t) - f(1 - t) \right] dt.
$$  
由於 $f$ 遞增，且對任意 $t \in [\frac{1}{2}, 1]$ 有 $1 - t < t$（因 $t > \frac{1}{2}$），故 $f(1 - t) \leq f(t)$。因此 $f(t) - f(1 - t) \geq 0$ 對所有 $t \in [\frac{1}{2}, 1]$ 成立；又因 $t - \frac{1}{2} \geq 0$ 在此區間內成立，故被積函數非負。  
由積分的性質（若被積函數非負則積分非負），得 $I \geq 0$。因此，原不等式成立。  

$\blacksquare$

### 教學步驟（2 步）
1. 考慮差值 $\displaystyle \int_0^1 x f(x) \, dx - \frac{1}{2} \int_0^1 f(x) \, dx = \int_0^1 \left( x - \frac{1}{2} \right) f(x) \, dx$。  
由於 $f$ 在 $[0,1]$ 上連續且遞增（即對任意 $x < y$ 有 $f(x) \leq f(y)$），將積分區間拆分為 $\left[0, \frac{1}{2}\right]$ 與 $\left[\frac{1}{2}, 1\right]$。  
令  
$$
I = \int_0^{\frac{1}{2}} \left( x - \frac{1}{2} \right) f(x) \, dx + \int_{\frac{1}{2}}^1 \left( x - \frac{1}{2} \right) f(x) \, dx.
$$  
對第一個積分，作變數替換 $t = 1 - x$。當 $x = 0$ 時 $t = 1$；當 $x = \frac{1}{2}$ 時 $t = \frac{1}{2}$，且 $dx = -dt$。代入得：  
$$
\int_0^{\frac{1}{2}} \left( x - \frac{1}{2} \right) f(x) \, dx = \int_{\frac{1}{2}}^1 \left( \frac{1}{2} - t \right) f(1 - t) \, dt.
$$  
因此，$I$ 可表示為：  
$$
I = \int_{\frac{1}{2}}^1 \left( \frac{1}{2} - t \right) f(1 - t) \, dt + \int_{\frac{1}{2}}^1 \left( t - \frac{1}{2} \right) f(t) \, dt = \int_{\frac{1}{2}}^1 \left( t - \frac{1}{2} \right) \left[ f(t) - f(1 - t) \right] dt.
$$  
由於 $f$ 遞增，且對任意 $t \in [\frac{1}{2}, 1]$ 有 $1 - t < t$（因 $t > \frac{1}{2}$），故 $f(1 - t) \leq f(t)$。因此 $f(t) - f(1 - t) \geq 0$ 對所有 $t \in [\frac{1}{2}, 1]$ 成立；又因 $t - \frac{1}{2} \geq 0$ 在此區間內成立，故被積函數非負。  
由積分的性質（若被積函數非負則積分非負），得 $I \geq 0$。因此，原不等式成立。（確認：這一步的推理你能自己複述一遍嗎？）
2. $\blacksquare$（確認：這一步的推理你能自己複述一遍嗎？）

## X4（verified，344.8s）
> 設 $A$ 為方陣，$\lambda_1\ne\lambda_2$ 為 $A$ 的兩個相異特徵值，$v_1,v_2$ 為對應的特徵向量。證明 $\{v_1,v_2\}$ 線性獨立。

### 自動參考解（人工核對正確性）
設 $A$ 為方陣，$\lambda_1\neq \lambda_2$ 為 $A$ 的兩個相異特徵值，$v_1,v_2$ 為對應的特徵向量。由特徵向量之定義可知 $v_1 \neq \mathbf{0}$ 且 $v_2 \neq \mathbf{0}$。

假設存在標量 $a,b$ 使得  
$$
a v_1 + b v_2 = \mathbf{0}. \tag{1}
$$

將等式 $(1)$ 左乘矩陣 $A$ 得：  
$$
a A v_1 + b A v_2 = A (\mathbf{0}) \implies a \lambda_1 v_1 + b \lambda_2 v_2 = \mathbf{0}. \tag{2}
$$

將等式 $(1)$ 乘以 $\lambda_2$ 得：  
$$
a \lambda_2 v_1 + b \lambda_2 v_2 = \mathbf{0}. \tag{3}
$$

由 $(2) - (3)$ 結果為：  
$$
a (\lambda_1 - \lambda_2) v_1 = \mathbf{0}. \tag{4}
$$

因 $\lambda_1 \neq \lambda_2$，故 $\lambda_1 - \lambda_2 \neq 0$。又因 $v_1 \neq \mathbf{0}$（特徵向量非零），由 $(4)$ 可知 $a = 0$。

將 $a = 0$ 代入等式 $(1)$ 得 $b v_2 = \mathbf{0}$，因 $v_2 \neq \mathbf{0}$，故 $b = 0$。

因此，唯一解為 $a = b = 0$，即 $\{v_1, v_2\}$ 線性獨立。$\blacksquare$

### 教學步驟（5 步）
1. 特徵向量 $v_1$ 和 $v_2$ 都是非零向量（由特徵值定義）（確認：否）
2. 假設存在標量 $a, b$ 使得 $a v_1 + b v_2 = \mathbf{0}$（確認：存在不全為零的 $a,b$）
3. 將等式左乘矩陣 $A$，得到 $a \lambda_1 v_1 + b \lambda_2 v_2 = \mathbf{0}$（確認：$\lambda_1 v_1$ 和 $\lambda_2 v_2$）
4. 將原等式乘以 $\lambda_2$，得到 $a \lambda_2 v_1 + b \lambda_2 v_2 = \mathbf{0}$（確認：$a \lambda_2 v_1 + b \lambda_2 v_2 = \mathbf{0}$）
5. 相減後得 $a (\lambda_1 - \lambda_2) v_1 = \mathbf{0}$。因 $\lambda_1 \neq \lambda_2$ 且 $v_1 \neq \mathbf{0}$，故 $a = 0$；代入原式得 $b = 0$（確認：0）

## X6（verified，851.8s）
> 設 $A$ 為 $n\times n$ 實對稱矩陣。證明 $A$ 的每個特徵值都是實數。

### 自動參考解（人工核對正確性）
設 $ A $ 為 $ n \times n $ 實對稱矩陣，即 $ A^T = A $（由實對稱矩陣定義）。  
假設存在非零向量 $ v \in \mathbb{C}^n $ 使得 $ A v = \lambda v $，其中 $ \lambda \in \mathbb{C} $ 為某個特徵值。此步驟依賴於特徵值的定義：存在非零向量 $ v $ 滿足方程。  

對兩邊取共軛轉置得 $ (A v)^* = \overline{\lambda} v^* $，即 $ v^* A^* = \overline{\lambda} v^* $。由於 $ A $ 為實矩陣，故 $ A^* = A^T $；又因 $ A $ 對稱，故 $ A^T = A $，因此 $ A^* = A $。由此得：  
$$
v^* A = \overline{\lambda} v^*. \tag{1}
$$  

將原方程 $ A v = \lambda v $ 代入內積形式 $ v^*(A v) $ 得：  
$$
v^* A v = \lambda v^* v. \tag{2}
$$  

由 $(1)$ 兩邊右乘以 $ v $，得：  
$$
(v^* A) v = \overline{\lambda} v^* v, \quad \text{即} \quad v^* A v = \overline{\lambda} v^* v. \tag{3}
$$  

比較 $(2)$ 與 $(3)$ 兩式，得：  
$$
\lambda v^* v = \overline{\lambda} v^* v.
$$  

因 $ v \neq 0 $，故 $ v^* v > 0 $（複數向量的內積模平方為正實數）。因此可除以 $ v^* v $ 得：  
$$
\lambda = \overline{\lambda}.
$$  

即 $ \lambda $ 為實數。此結論對任意特徵值成立，故 $ A $ 的每個特徵值皆為實數。  
$\blacksquare$

### 教學步驟（4 步）
1. 實對稱矩陣定義為 $ A^T = A $（確認：條件是什麼？）
2. 假設存在非零向量 $ v $ 滿足 $ A v = \lambda v $（確認：$ v $ 是什麼？）
3. 對 $ A v = \lambda v $ 取共軛轉置，並利用 $ A $ 實對稱得 $ v^* A = \overline{\lambda} v^* $（確認：共軛轉置結果？）
4. 計算內積：$ v^*(A v) = \lambda v^* v $；由上步得 $ v^* A v = \overline{\lambda} v^* v $。因 $ v \neq 0 $，故 $ v^* v > 0 $，所以 $ \lambda = \overline{\lambda} $（確認：特徵值為實數？）


---
**verified 率：9/10**；verified 正確率待人工核對。