# 評估報告 v2（方法修正後，Claude 親自評分）

> 日期：2026-06-27　評分者：Claude（非 4B judge）
> 本輪修正：精簡 system prompt（~70 token，省 ~310 token）、grounded 訓練範例（種子參考解由
> Claude 手寫）、截斷改「保留含 assistant 的左截斷窗口」、優化器改 adamw_8bit。
> 訓練資料：可用 **2900 / 跳過 0**（修正前 1956 / 丟 804）。
> 核心新增對照組：**base_grounded**（基底+grounding，未微調）→ 與 finetuned_grounded
> 同基底、同 grounding，**只差有沒有微調**，乾淨隔離微調效果。

## 一、總分（教學品質 /5）

| 路線 | v4（難，10題） | held-out（中，12題） |
|---|:---:|:---:|
| **base_grounded**（基底+grounding） | **4.40** 🏆 | 4.33 |
| finetuned_grounded（微調+grounding） | 3.85 | 4.29 |
| base（基底+prompt） | 3.20 | 3.83 |
| finetuned（微調，純） | 3.00 | **4.42** 🏆 |

## 二、核心結論：微調在 grounding 下「沒有加分，難題還扣分」

apples-to-apples（同基底、同 grounding，只差微調）：

| 題集 | base_grounded | finetuned_grounded | 微調的效果 |
|---|:---:|:---:|:---:|
| v4（難） | 4.40 | 3.85 | **−0.55（變差）** |
| held-out（中） | 4.33 | 4.29 | −0.04（持平） |

**即使做完所有方法修正**（grounded 訓練、手寫參考解、精簡 prompt、救回資料），在 grounding 下
微調仍**沒有勝過不微調**；難題上甚至明顯更差。原因：微調模型被小學數學資料訓出固定習慣
（動不動套「輔助函數 / Squeeze / 反證模板 / 終止式 "Does that help?"」），在難題上**會無視參考解、
退回這些習慣**而給錯方向。base 模型沒有這些習慣，反而更忠實地照參考解引導。

典型案例（v4）：
- 級數 ∑√aₙ/n：base_grounded 指向 Cauchy-Schwarz（5 分）；finetuned_grounded 卻說「用極限比較審斂法」(2 分，錯工具)。
- Landau |f'|≤√2：base_grounded 直指兩側 Taylor 相減（5 分）；finetuned_grounded 從「假設 f 為常數」這個無用特例開場（2.5 分）。

## 三、但方法修正確實有效（與舊版對比）

- **資料救回**：丟棄樣本 804 → **0**（精簡 prompt + 左截斷窗口，多輪 MathDial 全數保留）。
- **修掉崩潰**：舊版 finetuned_grounded 在 Landau 題回「Hi. Can you explain your idea?」整個放棄；
  新版（grounded 訓練 + 精簡 prompt 對齊訓練/評估分佈）不再崩潰，每題都給出合理問句。
- **微調本身在中等題仍有用**：held-out 上 finetuned(4.42) > base(3.83)；但一旦加 grounding 就被抹平。

## 四、難 vs 中 的不同樣貌

- **難題（v4）**：base 自身知識不夠 → **grounding 價值最大**（base_grounded 4.40 遙遙領先）；
  微調的固定習慣在難題上是負擔（finetuned 3.00 最差）。
- **中等題（held-out）**：base 已會內容 → 微調的「簡潔對題風格」幫得上（finetuned 4.42 最高）；
  grounding 的正確性加成有限，微調與否在 grounded 下幾乎一樣。

## 五、最終建議（與先前一致、且更穩固）

1. **部署用 grounding，不需要微調**：base_grounded 在難題最佳、中等題與微調並列，且
   **不必訓練、不必維護 adapter、行為最可預測**。→ best_grounded_tutor（思考型模型）即可。
2. **微調不值得進產線**：對 grounding 沒有淨加分，難題上還會因固定習慣無視參考解而退步。
3. **真正的關鍵是 grounding（參考解在手）**，題目越難越重要——這點在兩個題集、apples-to-apples
   對照下都成立。

## 附：逐題分數

### v4（難）
| # | 題 | base | finetuned | base_grounded | ft_grounded |
|---|---|:--:|:--:|:--:|:--:|
|1|f'增⇒f/x單調|3.5|4.5|4|4|
|2|Landau|3.5|3.5|5|2.5|
|3|UC+積分⇒f→0|2.5|3.5|4.5|3.5|
|4|矩消失⇒f≡0|3|2|4.5|5|
|5|n∫xⁿf→f(1)|4|2.5|4|4.5|
|6|Poincaré|3|2|4.5|3.5|
|7|∑√aₙ/n|2.5|2|5|2|
|8|f+f'→L|3.5|3.5|4.5|5|
|9|∫\|f''\|≥4max|2.5|2.5|4|4.5|
|10|∑f(k/n²)→0|4|4|4|4|
|**平均**||**3.20**|**3.00**|**4.40**|**3.85**|

### held-out（中）
| 平均 | base 3.83 | finetuned 4.42 | base_grounded 4.33 | ft_grounded 4.29 |
|---|---|---|---|---|
