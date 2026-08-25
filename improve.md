# 蘇格拉底式高等數學證明引導助教 — 優化與改進分析 (improve.md)

這份文件對比前一版的專案內容

---

## 1. 核心改進：混合式審閱後盾架構 (Hybrid Review Backstop Architecture)

*   **架構升級**：在原本微調 (LoRA) 4B 模型的基礎上，針對需要嚴格數學判斷的 `review`（草稿審閱）和 `rectify`（邏輯糾錯）階段，引入了**後台思考型模型 (Reasoning Model)**（預設為本地 Ollama 運行的 `qwen3-4b-thinking-2507:latest`）作為「審閱後盾」。
*   **判斷與對話分工**：
    *   **思考型大模型（幕後找碴助教）**：負責對照正確參考解，對學生的證明進行極度嚴格的邏輯審查，挑出 1~3 個嚴格教學標準下的數學錯誤或依據缺漏（例如：引用定理前提未驗證、等號/不等號方向反了、特例未排除等），並輸出為結構化的 JSON 陣列。
    *   **微調 4B 模型（台前親和助教）**：接收注入 system 指示中的缺漏清單，再以其微調所獲得的親和、引導性語氣去詢問學生，引導其自行修正，解決了小型微調模型在判斷複雜數學邏輯時容易出現的「錯誤背書」或「看懂但解釋錯」的局限性。
*   **解析容錯與 LaTeX 支持**：在 [review_backstop.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/review_backstop.py) 中實現了**平衡括號掃描演算法**，當模型輸出的 LaTeX 公式含有非法 JSON 轉義反斜線（如 `\leq` 或 `\dots`）時，能自動進行雙反斜線轉義重試，確保 JSON 解析的穩定性。
*   **靜默降級機制 (Graceful Degradation)**：當本地 Ollama 離線、逾時或無法解析時，系統能自動捕獲異常並回傳 `None`，讓 Driver 靜默退回微調模型自體審查，避免因後盾掛掉而導致整個系統運行中斷，極大提升了部署的穩健性。

---

## 2. 確定性推論防護 (Guardrails) 的系統化與重構

在 [tutor_driver.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/tutor_driver.py) 中，將防護機制由原本零散的過濾與簡單警告，重構為具有**系統化重生成（Systematic Regeneration）**的 6 大安全防護機制：

*   **新增：on-track 防奉送 (Spoonfeed Prevention)**：
    *   **痛點**：當學生方向正確時，模型常急於幫學生做代數計算（例如同乘、相減、代入、移項等），直接把步驟奉送給學生。
    *   **改進**：新增 `is_spoonfeeding` 檢測，若模型在等級 <2 且非特殊階段時給出具體代數操作指令，將觸發 `spoonfeed` 防護，要求模型重生成，只給予肯定，而不奉送具體步驟。
*   **新增：等級 2 禁算式 (Level 2 Equation Ban)**：
    *   **痛點**：學生卡住多次時，等級 2 提示雖然允許給出定理/技巧名稱或想法，但容易順便把推導式子一併奉上。
    *   **改進**：新增 `gives_new_equation` 檢測，提取模型回覆中包含 `=`、`≤`、`≥` 等算式片段，若該公式不屬於白名單（題目、當前提示、學生歷史訊息）則判定違規並要求重生成，強迫學生必須自己動筆推導。
*   **優化：回問保底與確定性回覆 (Ending with Question Guard)**：
    *   **痛點**：在普通引導輪或拒絕洩漏輪 (`refuse_leak`) 中，模型有時會忘記以問句結尾，導致對話斷流。
    *   **改進**：若 `level < 2` 且回覆不含問號，先嘗試重生成；若仍缺問句，則**強制附上預設問句**（中文為「那你覺得，下一步該從哪裡下手？」，英文為「So where do you think the next step should start?」）。這種確定性的程式碼保底，優於單純賭模型的指令服從。
*   **優化：重複問句防護 (Repeat Prevention)**：
    *   比對當前生成與最近 3 輪助教的回覆，若相同則追加「不要重複問過的問題，試著換個方向提問」的指示並強迫重生成，防範模型在學生不斷回答「我不知道」時陷入循環死結。
*   **重生成機制化 (Regeneration Refactoring)**：
    *   統一實作 `_regen` 方法，將 temperature 設為 0 (`do_sample=False`, `repetition_penalty=1.05`)，並在 system prompt 後綴加上特定的加強約束，確保 greedy 解碼下改變輸入能確實改變輸出。

---

## 3. 語言適應與跟隨優化 (Dynamic Language Adaptation)

*   **動態語言檢測**：以往系統語言是根據題目的語言決定。現在的 `step` 中，如果學生的訊息扣除 LaTeX 公式後字元數 $\ge 12$ 且語言明確不同，會動態重新偵測並切換當前 session 的語言 (`lang`)。這完美支持了「英文題目、中文對話」或是中途切換語言的複雜教學情境，更貼近學生的真實使用習慣。
*   **英文版 Grounded System 修正**：修正了 `BASE_SYSTEM_EN` 中的部分細微語義，以防英文提示中包含數學式子時被誤判為洩漏。

---

## 4. 評估與驗證體系的建立 (Evaluation & Testing Harness)

*   **單元測試擴展 (`test_driver_unit.py`)**：擴充了無 GPU 狀態下的單元測試，涵蓋新增的卡住正則表達式、防奉送（Spoonfeed）、等級 2 白名單算式檢測、重複問句檢測、重複回問保底等 74 個斷言，確保所有確定性防護的行為完全符合預期。
*   **後盾精準度測試 (`test_backstop.py`)**：新增專門測試，評估審閱後盾對學生證明草稿中邏輯漏洞的分析可信度。
*   **端到端對話評估 (`eval_backstop_e2e.py` / `eval_xdomain.py`)**：
    *   新增對話跨領域評估，導入了 `xdomain_problems.json`（包含線性代數、離散數學等題目）。
    *   對比有無 backstop 機制下，系統在面對全新數學領域題目時的表現，結果證明：混合審閱後盾大幅降低了 4B 裸模型跨領域引導時的幻覺與邏輯錯誤，大幅擴展了系統的泛化能力。
