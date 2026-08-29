# Verify-Then-Generate paired evaluation

- Generator: Qwen3-4B + /workspace/dataset/qlora_adapter_v9
- Verifier: qwen3-4b-thinking-2507:latest

| condition | hit | targeted | math | guidance | reveal | one question | no leak | latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 1.0 | 0.9714 | 1.0 | 0.9143 | 1.0 | 1.0 | 1.0 | 50.576 |
| verify_then_generate | 1.0 | 1.0 | 1.0 | 0.9429 | 1.0 | 1.0 | 1.0 | 87.531 |

## H1
### baseline
- verifier: disabled / 
- latency: 56.8698 s
- reply: 分子算錯了：$3n-1-3(n+2)=3n-1-3n-6=-7$，絕對值是 $7$ 而非 $5$。修正後，$N$ 與 $\varepsilon$ 的關係要怎麼寫？
- judge: 助教精準指出分子計算錯誤（應為 7 而非 5），數學算式完全正確；且未直接給出修正後的 N 選擇與完整證明，而是透過提問引導學生重新思考修正後的 N 與 \varepsilon 關係。
### verify_then_generate
- verifier: issues / 學生在計算分子 |3n-1 - 3(n+2)| 時錯誤地得到 5，但實際應為 7。
- latency: 59.9518 s
- reply: 分子算錯了。$3n-1-3(n+2)$ 展開後是什麼常數？
- judge: 助教精準指出學生在分子 $3n-1-3(n+2)$ 化簡上的算術錯誤，並以提問方式引導學生自行計算展開後的常數，數學敘述無誤且未直接洩漏正確答案。

## H2
### baseline
- verifier: disabled / 
- latency: 29.8721 s
- reply: 這裡你用的是「一致連續」的定義，但 $\delta$ 依賴 $x$（$\delta=\varepsilon x^2$），這其實是哪種連續性？
- judge: 助教精準指出學生在證明中所採用的 δ 依賴於 x（δ=εx²），成功抓出埋入的根本錯誤。透過反問「這其實是哪種連續性？」，有效引導學生反思逐點連續與一致連續的差異，且未直接洩漏完整解答。
### verify_then_generate
- verifier: issues / In the step where δ is defined as ε x², δ depends on x but uniform continuity requires δ to be independent of x for all x in (0,1).
- latency: 101.6153 s
- reply: 這裡出現了「逐點連續」與「一致連續」的混淆。$\delta=\varepsilon x^2$ 這個 $\delta$ 依賴於 $x$，而一致連續要求 $\delta$ 對所有 $x$ 都相同。若 $x$ 很小，$\delta$ 會變得很小，這行得通嗎？
- judge: 助教精準指出學生選取的 δ 依賴於 x 係屬於逐點連續而非一致連續的根本錯誤，數學觀念敘述完全正確；並透過「當 x 很小時 δ 會變得很小」的反問進行啟發式引導，同時完全避免了直接洩漏否定一致連續的完整證明過程。

## H3
### baseline
- verifier: disabled / 
- latency: 72.7673 s
- reply: 這裡用到「有理數在 $\mathbb{R}$ 稠密」，但你只靠平均兩個有理數得到 $a$，這給出的是什麼樣的點？
- judge: 助教直指學生第一個根本錯誤，透過詢問「平均兩個有理數給出的是什麼樣的點」引導學生發現兩有理數之平均仍為有理數而非無理數；雖然開頭提到稠密性稍有雜訊，但引導與質疑方向相當精準且未洩漏正解。
### verify_then_generate
- verifier: issues / 學生聲稱無理數可以寫成兩個有理數的平均，但這斷言不成立，因為兩個有理數的平均必然是有理數。
- latency: 70.6166 s
- reply: 這裡用了兩個未被假設的命題。首先，$a=\frac{p+q}{2}$ 是有理數的平均，那 $a$ 本身是什麼樣的數？
- judge: 助教精準指出「兩個有理數的平均 $a=\frac{p+q}{2}$ 本身必然是有理數」這一關鍵矛盾，成功命中學生嘗試中的第一個根本錯誤；透過蘇格拉底式提問引導學生思考 $a$ 的數性，且完全沒有洩漏利用稠密性與序列連續性的正確解法。

## H4
### baseline
- verifier: disabled / 
- latency: 80.4484 s
- reply: Heine-Cantor 需要 $f$ 定義在緊緻空間（如閉區間），$\mathbb{R}$ 不緊緻，不適用。這裡 $|f'|\le M$ 是什麼用處？
- judge: 助教精準指出 Heine-Cantor 定理需在緊緻空間才成立且 ℝ 不緊緻，直接擊中學生的根本錯誤；同時透過反問引導學生思考 $|f'|\le M$ 的用途，數學敘述完全正確且未洩漏解答。
### verify_then_generate
- verifier: issues / 學生在應用 Heine-Cantor 定理時，未明確指出定義域 $\mathbb{R}$ 不是緊緻集，因此該定理不適用於 $\mathbb{R}$
- latency: 63.2849 s
- reply: Heine-Cantor 要求定義域是緊緻的，$\mathbb{R}$ 是緊緻的嗎？
- judge: 助教精確點出 Heine-Cantor 定理需緊緻定義域的前提錯誤，透過反問引導學生反思實數集的緊緻性，且完全未洩漏均值定理等參考解法。

## H5
### baseline
- verifier: disabled / 
- latency: 38.3072 s
- reply: 方向正確，但「$c\ge0$」給出的是 $\ge$ 而非嚴格 $>1$。要嚴格不等號，$c$ 的範圍該怎麼更精準？
- judge: 助教精準指出學生將 c 的範圍寫成「c>=0」導致無法得到嚴格不等號的關鍵錯誤，數學敘述完全正確，且透過反問引導學生重新思考均值定理給出的精準範圍（c>0），並未直接給出完整解答。
### verify_then_generate
- verifier: issues / 學生聲稱 $c \ge 0$，但均值定理中 $c \in (0,x)$ 意味著 $c > 0$，故 $e^c > 1$ 而非 $e^c \ge 1$
- latency: 167.067 s
- reply: 邏輯骨架對，但「$c\ge0$」這個估計太鬆。均值定理給的是開區間 $(0,x)$，所以 $c$ 的符號是什麼，$e^c$ 因此大於還是等於 $1$？
- judge: 助教精準點出學生將開區間 (0,x) 放鬆為 c>=0 的核心錯誤，數學敘述正確，並以提示性提問引導學生思考 c>0 對 e^c 大小關係的影響，未洩漏完整解答。

## H7
### baseline
- verifier: disabled / 
- latency: 46.645 s
- reply: 比較對象選錯了。$\sum\dfrac1n$ 是發散的調和級數，不能當收斂的比較項。要找什麼樣的收斂項？
- judge: 助教精準指出學生誤用發散調和級數作為比較項的核心錯誤，數學敘述完全正確；並透過提問引導學生思考適當的收斂比較項，同時未洩漏具體參考解答（如 1/n²）。
### verify_then_generate
- verifier: issues / 應用比較判別法時，未明確陳述比較對象 $\sum_{n=1}^{\infty} \dfrac{1}{n}$ 收斂
- latency: 70.0697 s
- reply: 比較對象 $\sum\frac1n$ 是發散的調和級數，不能當收斂的 $b_n$ 用。該用哪個已知收斂的級數來比較？
- judge: 助教精準指出學生誤用發散的調和級數 ∑(1/n) 作為比較判別法的上界，數學敘述完全正確且切中根本錯誤；同時以反問引導學生思考尋找已知收斂的級數，未直接洩漏 1/n² 的解答。

## H8
### baseline
- verifier: disabled / 
- latency: 29.1223 s
- reply: 比值判別法要求「比值的極限」而非「每一項都小於 $1$」。這裡 $\dfrac{n+1}{2n}\to\dfrac12$，極限是多少？
- judge: 助教精準指出學生誤用「每一項比值小於 1」而非「比值極限小於 1」的根本錯誤。數學敘述正確，未直接洩漏完整證明，並透過提問引導學生確認極限與比值判別法條件的連結。
### verify_then_generate
- verifier: issues / 學生未計算比值 $\dfrac{a_{n+1}}{a_n}$ 的極限，而比值判別法要求極限小於 1。
- latency: 80.1117 s
- reply: 比值判別法要求「比值的極限」小於 1，而不是「每一項都小於前一項」。這裡 $\dfrac{n+1}{2n}\to\dfrac12$，極限是多少？
- judge: 助教精準指出學生將「單調遞減/比值小於1」誤認為比值判別法條件的根本錯誤；數學述詞完全正確，且未替學生寫出完整的證明結論。唯引導時在敘述中已寫出趨近於 1/2 才詢問極限，提示略多，但整體引導品質仍相當良好。
