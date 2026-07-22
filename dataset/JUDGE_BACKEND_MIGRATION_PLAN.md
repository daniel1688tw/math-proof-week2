# 評審後端遷移：Antigravity CLI（`agy` / Gemini 3.1 Pro Low）

**狀態：已完整接入並雙輪實測（2026-07-22）。最終結論：預設維持 `claude`，
`agy` 保留為可選後端（`JUDGE_BACKEND=antigravity`）。** 見 §七選型結論。

> **§七 最終選型結論（2026-07-22，兩輪對同一 v9 模型實測）**
>
> | 面向 | 結果 |
> |---|---|
> | 穩定性 | ✅ 三檔位各 25 次壓測 100% 可解析、零逾時 |
> | 單題評審（math_ok/score/s2_catch/reveal/altmethod） | ✅ 兩輪穩定（math_ok_zh 0.90/0.94、score_zh 0.76/0.75、s2_catch 相同、reveal 相近） |
> | **多輪對話層（n=3）** | ❌ **兩輪劇烈擺動**：dialogue_math_ok_zh **0.333↔0.0**、en **0.667↔1.0**、guidance_zh 0.533↔0.333 |
> | 判準可靠性 | ⚠️ 會把「引導問題（罐頭式追問）」誤判成「數學錯誤」（M2 案例，math_ok=False 但理由是引導） |
>
> **判斷**：Gemini 3.1 Pro (Low) 單題評審可用，但對話層不可靠。對話層正是抓
> v9 收尾退步、v10 延伸退步最關鍵的閘——這裡不能可靠守門，就不該讓 Gemini 當唯一預設。
> 且對話層 n=3 + LLM 即興學生的本質雜訊，Claude 也有（歷史 1.0/0.333 擺動），Gemini 更甚。
>
> **決策**：**預設維持 `claude`**（已驗證能抓對話退步）。`agy` 後端程式與基準檔完整保留，
> 適用場景：(a) 單題指標的**交叉驗證**、(b) Claude 限額時的**備援**。整套壓測/對照/
> 基準腳本留存，未來若 Antigravity 出更強模型或修正對話層判準，可快速重新評估。
>
> `regression_baseline_antigravity.json` 為 run1 建立的**臨時**基準；因對話層雙輪不穩，
> 若要正式用 agy 守門，對話/後盾指標需多輪校準（取保守 floor）後才可信。

---

## 一、換的原因

- 守門完整跑一輪需評審 100+ 次；Claude Pro 額度中斷會打斷整輪
  （`--gen-only`／`--rejudge`／`auto_gate` 續評機制仍保留，換後端後同樣適用）。
- Antigravity CLI 額度與 Claude Code session 完全解耦，可分散依賴、降低同帳號搶額度污染評審的風險。

## 二、選型過程（2026-07-21，實測數據）

### 穩定性壓測（`test_agy_stability.py`，25 次連續呼叫，貼近 Tier2 評審格式）

| 模型檔位 | 可解析率 | 平均延遲 | 最大延遲 | hang/逾時 |
|---|---|---|---|---|
| Gemini 3.5 Flash (Medium) | 25/25 100% | 7.9s | 11.8s | 0 |
| Gemini 3.1 Pro (High) | 25/25 100% | 14.1s | 19.1s | 0 |
| Gemini 3.1 Pro (Low) | 25/25 100% | 13.3s | 17.9s | 0 |

三個檔位穩定性全數通過（門檻：可解析率 ≥99%、零 hang）。

### 判準嚴謹度對照（`test_agy_rigor.py` / `test_agy_rigor2.py`，2 個已知案例）

用 v10 判定時 Claude 已標注過的兩筆真實對話（H5/zh 含真實數學錯誤、X4/en 乾淨無誤）
讓三個檔位重判：

| 模型檔位 | 錯誤案例（應 False） | 乾淨案例（應 True） |
|---|---|---|
| Gemini 3.5 Flash (Medium) | ✓ 抓到 | ✗ 誤殺（**憑空捏造**：把題目核心正確命題判為錯誤陳述） |
| Gemini 3.1 Pro (High) | ✓ 抓到 | ✗ 誤殺（嚴格但有文本依據：抓到原文一處用詞疑似口誤） |
| Gemini 3.1 Pro (Low) | ✓ 抓到 | ✗ 誤殺（同上，理由相近） |

**結論**：三檔位皆能抓到真實數學錯誤，但都比 Claude 對同一乾淨案例判得更嚴格
（guidance 評分明顯偏低，1-3 分 vs Claude 同案例 ~4 分）。Flash 的誤殺屬於憑空捏造、
不可信賴；Pro 系列的誤殺至少有文本依據，屬於**判準尺度差異**而非推理錯誤。
**Low 與 High 表現幾乎相同（延遲也相近），故選延遲較低的 Low。**

## 三、決策

**採用 `Gemini 3.1 Pro (Low)`，獨立重建基準，不與 Claude 舊基準比較。**
Gemini 系列的評審尺度整體比 Claude 嚴格，這代表「通過 antigravity 守門」與
「通過 Claude 守門」是兩把不同的尺——按遷移原則，**只能同尺比較**（新模型 vs
antigravity 基準），不可直接拿新模型的 antigravity 分數去比 Claude 舊基準。

## 四、實作內容（`regression_suite.py`）

- `JUDGE_BACKEND` 預設值：**維持 `claude`**（§七雙輪實測後的最終決定）；
  `JUDGE_BACKEND=antigravity` 可切到 agy。以下抽象層對三個後端皆可用。
- 新增 `AGY_PATH`（固定裝在 `%LOCALAPPDATA%\agy\bin\agy.exe`）、`AGY_MODEL`
  （預設 `"Gemini 3.1 Pro (Low)"`，可用 `AGY_MODEL` 環境變數覆寫）。
- **`_judge_cmd()` 改為吃 `prompt` 參數**：claude/gemini 走 stdin 餵 prompt（沿用原邏輯）；
  agy 的 `-p` 吃**命令列參數**、不吃 stdin，故 antigravity 分支把 prompt 直接組進
  argv 清單（`[AGY_PATH, "--model", AGY_MODEL, "-p", prompt, "--print-timeout", "180s"]`）。
  `claude_call()` 對應改為依後端決定 `stdin_input` 是否為 `None`，重試迴圈中
  antigravity 每次都要重組命令（prompt 在 argv 裡，跟 claude/gemini 的 cmd 固定不同）。
- `claude_available()` 對 antigravity 改用 `os.path.exists(AGY_PATH)` 而非
  `shutil.which()`（agy 不在 PATH 上）。
- 基準檔：`regression_baseline_antigravity.json`（獨立於 `regression_baseline.json`）。
- 現有 JSON 解析（`parse_json_obj` + `_balanced` + `_loads_lenient`）本身就容錯，
  未特別為 agy 輸出格式調整，實測相容。

## 五、壓測與判準對照腳本（保留，供未來重新校準用）

- `test_agy_stability.py`：`AGY_MODEL=<檔位> python test_agy_stability.py`，25 次
  連續呼叫量測可解析率/延遲/hang。
- `test_agy_rigor.py` / `test_agy_rigor2.py`：拿已知 Claude 判定的真實案例（一錯一對）
  給 agy 重判，量化判準差異。未來若懷疑某次判定失準，可用同一組腳本快速複測。

## 六、殘餘風險（換用後仍需留意）

1. **額度**：Antigravity 免費預覽帳號，非 Gemini Pro 消費訂閱涵蓋範圍，額度上限未知，
   長時間大量評審呼叫若觸頂，`claude_call` 現有的限流偵測正則（`hit your limit` 等）
   未必涵蓋 agy 特有的錯誤字串，需在實際跑大量評審後觀察並補上樣式。
2. **判準嚴格度＋對話層不可靠**（§七）：Gemini 單題比 Claude 嚴（尺度差異，可接受），
   但對話層 n=3 兩輪劇烈擺動且會把引導問題誤判成數學錯誤——這是不採用為預設的主因。
3. **對照樣本量小**（僅 2 判準案例、2 輪守門）：若未來要重新評估 agy，應先用 §五腳本
   擴大對照樣本、並對對話/後盾指標做多輪校準取保守 floor，再決定是否升為預設。
