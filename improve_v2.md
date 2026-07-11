# improve_v2.md — 第三輪改進分析

> 分析對象：`baseline_v2.py`（best-of-n + TIR + LLM-judge）的實驗結果，
> 以及新鮮批次的 `baseline.py`(v4) vs `simple.py` 對比。
> 改進建議主要針對 T（TIR）、J（LLM-judge）兩個機制。

---

## §0 TL;DR — 五個核心發現

| # | 發現 | 影響 |
|---|------|------|
| 1 | TIR（工具整合推理）在 10 題中有 9 題失敗 | T 機制完全無效，無法提供可靠的驗證信號 |
| 2 | LLM-judge 對全部 10 題均給出 `judge_score=10, accepted=True` | J 機制失去鑑別力，無法區分好壞 |
| 3 | best-of-n 在兩個信號均為常數時退化成隨機選取 | 2 題 REGRESSED（選到更差的候選）、0 題改善 |
| 4 | v2 平均分 6.0 vs v4 平均分 6.5（無提升） | M/J/T 路線圖的第一次實作落空 |
| 5 | 新鮮批次 simple 均值 6.7 > v4 均值 6.2 | 採樣隨機性（溫度 0.1 + do_sample=True）使批次間差異 ±0.5，pipeline 優勢不穩定 |

---

## §1 v2（baseline_v2.py）實作後驗

### 1.1 每題 v4 → v2 分數變化

| problem_id | v4 分 | v2 分 | Δ | 備註 |
|------------|--------|--------|---|------|
| cauchy_sequence_summable_differences | 7 | 7 | 0 | — |
| iterated_map_converges_to_zero | 8 | 8 | 0 | — |
| periodic_function_two_critical_points | 5 | 3 | **-2** | TIR judge 誤判選到較差候選 |
| nonnegative_continuous_zero_integral | 9 | 9 | 0 | — |
| cauchy_functional_equation_continuous | 9 | 9 | 0 | — |
| recursive_sequence_convergence | 4 | 4 | 0 | — |
| uniform_limit_continuous | 10 | 10 | 0 | — |
| derivative_limit_implies_average_limit | 6 | 4 | **-2** | best-of-n 選到含 f(0)/x 丟棄錯誤的候選 |
| contraction_unique_fixed_point | 3 | 3 | 0 | — |
| gronwall_zero_function | 4 | 3 | -1 | — |

**總結**：7 題持平、2 題 -2、1 題 -1；無任何 +1 或以上改善。
平均分：v4 = 6.5，v2 = 6.0（下降 0.5）。

### 1.2 根本原因

best-of-n 的排序 key `_candidate_rank_key` 依賴（TIR_pass_count, judge_score, attempts）。
由於 TIR 全部失敗（下節細述）且 judge_score 全部 = 10，排序鍵退化為 `(0, 10, attempts)`，
等效於按生成順序隨機選取。對有 n=2 候選的問題，有 50% 機率選到更差的那個。

---

## §2 TIR（工具整合推理）每題診斷

### 2.1 失效類型分類

| 類型 | 描述 | 出現題數 |
|------|------|----------|
| **A** | 格式不符：模型生成的程式碼可執行，但輸出未遵循 `CHECK <label>: PASS/FAIL` 格式 | 7/10 |
| **B** | 擷取 Bug：code fence 未關閉，`_extract_code_block` fallback 抓到散文+截斷程式碼，SyntaxError | 1/10 |
| **C** | 模型生成程式碼本身有 bug（`.format()` 含未跳脫的 `}`） | 1/10 |
| **D** | 驗證內容與證明脫節：`check()` 驗的是瑣碎事實（如「0<1」）或平凡的例子函數，而非證明的實際主張 | 4/10（與A重疊）|
| **E** | 真正驗證了最終數值主張（模型設計正確且執行成功） | 1/10 |

> 唯一屬於 E 的題目：`recursive_sequence_convergence`（驗證極限值 √2-1）。

### 2.2 每題明細

| problem_id | 類型 | 失效具體描述 |
|------------|------|-------------|
| cauchy_sequence | A+D | 輸出 `True` 不附標籤；check 的是「1/2^n>0」這種恆真式 |
| iterated_map | A | 輸出帶 `✓`/`✗` 符號而非 `PASS/FAIL` |
| periodic_function | B | code fence `\`\`\`python` 後無對應 `\`\`\`` 結尾，fallback 擷取截斷字串 → SyntaxError |
| nonneg_integral | A+D | `print(check_ineq)` 印 `True/False`，未有 `CHECK` 前綴；check 的是「ε=0.05>0」 |
| cauchy_functional | A | 輸出格式為 `Step1: PASS` 而非 `CHECK Step1: PASS` |
| recursive_sequence | E | 正確定義 `a_next(a)=1/(2+a)` 並驗 |a_{99}-L|<1e-6；輸出 `CHECK convergence: PASS` ✓ |
| uniform_limit | A+D | check 的是「ε/3 > 0」；輸出為 `verified=True` 非標準格式 |
| derivative_limit | C | `.format(L=L)` 但格式字串含 `{ε}` （ε 非關鍵字）→ KeyError |
| contraction | A+D | check 的是「k=0.5<1」（已知條件，非結論）；輸出 `result=True` |
| gronwall | A | 輸出嵌在 markdown 表格裡，正則擷取失敗，回傳 0 pass 0 fail |

---

## §3 LLM-judge 問題診斷

### 3.1 現象

v2 批次 10 題 judge_score 分布：**全部 10/10，全部 accepted=True**。
分數方差為 0，完全失去鑑別力。

### 3.2 根本原因

| # | 原因 | 說明 |
|---|------|------|
| 1 | **認知過載** | 要求 7B 模型「從頭驗證整個微積分證明的邏輯正確性」超出其推理容量；模型退化成表面掃描 |
| 2 | **格式即正確的啟發式** | 完整、有步驟編號的 LaTeX 格式讓模型誤判為「高品質」；錯誤隱藏在邏輯深處而非表面格式 |
| 3 | **無「先假設有錯」的先驗** | judge prompt 未預設「這個證明很可能有問題」；模型預設正面評分 |

---

## §4 新鮮批次：baseline.py(v4) vs simple.py 對比

> 資料來源：`run_v4_simple_batch.py` 批次輸出（`v4_simple_results.json`），共 10 題，總耗時 3368.7s。
> 詳細評分與評語：`compare_v4.csv`。

### 4.1 逐題分數

| problem_id | v4_fresh | simple_fresh | Δ(fresh v4 - hist v4) | Δ(fresh simple - hist simple) |
|------------|----------|--------------|----------------------|-------------------------------|
| cauchy_sequence_summable_differences | 7 | 7 | 0 | 0 |
| iterated_map_converges_to_zero | 8 | 9 | 0 | 0 |
| periodic_function_two_critical_points | 5 | 5 | 0 | 0 |
| nonnegative_continuous_zero_integral | 9 | 9 | 0 | 0 |
| cauchy_functional_equation_continuous | 9 | 9 | 0 | **+5** |
| recursive_sequence_convergence | 4 | 3 | 0 | 0 |
| uniform_limit_continuous | 10 | 10 | 0 | 0 |
| derivative_limit_implies_average_limit | 4 | 9 | **-2** | 0 |
| contraction_unique_fixed_point | 3 | 3 | 0 | 0 |
| gronwall_zero_function | 3 | 3 | -1 | +1 |
| **平均** | **6.2** | **6.7** | -0.3 | +0.6 |

### 4.2 主要觀察

**1. 本輪 simple 反超 v4**（+0.5）——與歷史 v4(6.5) > simple(6.1) 方向相反。

主要驅動因素是兩個高差異題目：

- **`derivative_limit_implies_average_limit`**（v4 4 vs simple 9）：
  fresh v4 在 [0,x] 套 MVT 後同時犯了兩個錯——`c∈(0,x)` 且 x>M 不保證 c>M（歷史 v4 唯一缺口）＋把 f(0)/x 項憑空丟棄（歷史 v4 正確保留）。
  本輪模型採樣到了更差的推導路徑。fresh simple 則正確使用「先固定 M，再對 [M,x] 套 MVT」策略。

- **`cauchy_functional_equation_continuous`**（simple 從 4→9）：
  歷史 simple 有循環歸納錯誤（→ 4 分）；fresh simple 採樣到非循環路徑（`f(qx)=qf(x)` 取 x=p/q 直接得 f(p/q)=p/q·f(1)）→ 9 分。單一採樣隨機性造成 +5 分跳躍。

**2. 採樣方差大**（temperature=0.1，do_sample=True）：

即使在低溫下，10 題中有 2 題出現 ≥2 分的批次間差異。
pipeline（v4）對 baseline（simple）的優勢在 ±2 分的採樣噪聲下難以穩定體現。

**3. 7 題分數完全相同**，證明主要瓶頸在模型本身的能力而非 pipeline 結構。

| 差異來源 | 題數 |
|----------|------|
| v4 > simple | 0 |
| v4 < simple | 2（cauchy_functional fresh simple +5，derivative_limit fresh v4 -2 vs hist）|
| v4 = simple | 7 |
| 有回合異常（accepted=False）| 1（periodic，attempts=2）|

### 4.3 小結

新鮮批次結果的核心訊息是：**pipeline 的額外複雜度（Extract/Generate/Verify/Correct 四階段）在本資料集上的邊際增益不穩定**。歷史 v4 優勢（6.5 vs 6.1）在本輪反轉為 simple 優勢（6.2 vs 6.7），主因是單題的採樣運氣。

要讓 pipeline 有穩定且可解釋的優勢，需要把「驗證信號」的品質從「啟發式 LLM 評分」提升到「可執行的形式化檢查」，也就是第三輪改進的核心目標。

---

## §5 改進提案（第三輪）

### 5.1 T（TIR）改進

#### T2-a：模板式 harness（**優先實作**）

**問題根源**：模型需要自己判斷輸出格式，9/10 格式不符。
**解法**：由 harness 注入 `check()` 函式的 Python 定義，要求模型**只呼叫**而非定義它：

```python
# harness 注入
def check(label: str, value: bool) -> None:
    print(f"CHECK {label}: {'PASS' if value else 'FAIL'}")
```

prompt 指示：「使用 `check(label, bool)` 來驗證，不要重新定義函式。」
這把格式合規問題從「模型的語言生成任務」轉成「套模板」，大幅降低格式失敗率（類型 A）。

**預計效果**：A 類（7/10）→ 0，整體 TIR 通過率從 1/10 → 4/10 以上（排除 B/C/D）。

#### T2-b：先引用後驗證（Claim-First）

**問題根源**：驗證內容（check）與證明實際主張脫節（類型 D）。
**解法**：在 TIR prompt 加入強制步驟：
1. 「先逐字抄寫證明中所有具體的數值結論/不等式（例：'|a_m - a_n| ≤ 1/2^n'）。」
2. 「為上方每一條具體結論寫一個 `check()` 呼叫，驗證它在範例參數下成立。」

強迫模型的 check 錨定在證明文字中出現的實際斷言，而非隨意挑容易成立的等式。

**預計效果**：D 類（4/10）→ 1~2，有效驗證覆蓋率顯著提升。

#### T2-c：讓 judge 知道 TIR 失敗的意義

告知 judge：「`0 PASS / 0 FAIL` 代表驗證工具未能執行，屬於**中立**（不是正面）信號，評分時應忽略。」
防止 judge 把 TIR 靜默（無輸出）解釋成「沒有問題被發現」。

---

### 5.2 J（LLM-judge）改進

#### J2-a：逐步二元判斷（**優先實作**）

**問題根源**：整體 0-10 評分對 7B 模型要求過高（認知過載）。
**解法**：把 judge 任務拆成「逐步二元判斷」：

```
For each numbered proof step:
  Step N: [quote the step text]
  - Is the logical inference valid? (YES / NO)
  - If NO, briefly state the specific error (1 sentence).
```

最後統計 NO 數量作為缺陷指標，替代 0-10 整體分。
**預計效果**：強迫 judge 逐步處理邏輯結構，而非靠格式啟發式；系統性 10/10 問題消失。

#### J2-b：已知錯誤模式清單

在 judge prompt 加入針對本資料集觀察到的錯誤類型清單：

```
Common errors to check for in calculus proofs:
□ Applying MVT on [0,x] without ensuring c > M (where f' is bounded)
□ Using Banach Fixed-Point Theorem to prove itself (circular)
□ Claiming sequence is monotone without handling the oscillation case
□ Claiming |sum| < 1/2^n when correct bound is 1/2^{n-1} (off-by-2 error)
□ Dropping f(0)/x term when writing f(x)/x = f'(c)
□ Concluding f≡0 from "g continuous and g(0)=0" without further argument
```

強制 judge 執行結構化 checklist，不給它「表面流暢即正確」的逃脫路線。

#### J2-c：跨模型 judge（**受 VRAM 限制，暫緩**）

根本問題：7B judge 評 7B response 缺乏相對優勢。
理想解：用更強的模型（如 Qwen-72B 或 Claude API）作為 judge。
在 6 GiB VRAM 限制下不可行；若未來有 API 存取可優先考慮。

---

### 5.3 P（best-of-n）改進

#### P2：暫緩 best-of-n，等 J/T 信號修復後重評

現狀：J 輸出常數（所有候選均 10 分）+ T 全部 0 pass → `_candidate_rank_key` 退化為隨機排序 → 2 題回歸。
決策：**在 T2-a + J2-a 實作並驗證信號品質前，不啟用多候選選取**。
理由：隨機排序比「只用第一候選」更差（expected score = avg，而非 max）；
等信號修復後，best-of-n 才能提供 expected score → max 的改善。

---

## §6 實作路線圖

| 優先級 | 項目 | 預計收益 |
|--------|------|---------|
| **P0** | T2-a（模板式 harness）+ J2-a（逐步二元判斷） | TIR 通過率 1/10 → 4+/10；judge 鑑別力恢復 |
| **P1** | T2-b（claim-first TIR）+ J2-b（已知錯誤清單）+ T2-c（教 judge 讀 TIR） | 有效驗證覆蓋率提升；judge 系統性偏差降低 |
| **P2** | 重新評估 best-of-n（P1 後驗證 J/T 信號品質） | 信號有效時 best-of-n 才有期望改善 |
| **P3** | J2-c 跨模型 judge（需 API 或更大 GPU） | 根本解決 judge 能力天花板 |

---

*本文件對應 `compare_v4.csv`（新鮮批次評分）與 `compare_v3.csv`（v3/v4/simple/v5 歷史評分）。*
