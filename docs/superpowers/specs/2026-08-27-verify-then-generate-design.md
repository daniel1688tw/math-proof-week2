# 高等數學證明 Verify-Then-Generate 設計規格

## 目標

在不更換既有部署生成模型的前提下，把參考專案「先驗證學生推理，再依診斷生成回覆」的方法整合進 `TutorDriver`。整合後仍由 `qlora_adapter_v9 + Qwen3-4B` 產生助教回覆，幕後證明驗證則沿用 `review_backstop.py` 的 Qwen3-4B Thinking／Ollama。

本變更只處理高等數學證明。驗證標準是題目隨附的 `reference_proof`，而不是參考專案的 MathDial、小學文字題答案或數值步驟對齊。

## 範圍

### 納入

- `guide` 階段中，router 已判為 `respond_attempt` 的學生數學嘗試。
- 在助教生成前，以 Thinking verifier 對照 `reference_proof` 找出錯誤與缺漏。
- 把幕後診斷注入既有 grounded system prompt，再由 v9 微調模型生成蘇格拉底式回覆。
- 保留目前所有生成後防護與候選語意審查。
- 提供可切換旗標，以相同題目、相同 adapter 做成對 A/B 評估。
- 保存足以稽核呼叫順序、診斷狀態與降級情形的 session diagnostics。

### 不納入

- 不匯入參考專案的 OpenAI API wrapper、MathDial dataset、SimCSE／ROSCOE step alignment 或其小學題 prompts。
- 不重新訓練或更換 `qlora_adapter_v9`。
- 不改變 phase router、Level 0/1/2、walkthrough、全文 review、closed 或 peer mode 的設計語意。
- 不讓 Thinking verifier 直接面對學生或撰寫最終助教回覆。

## 架構

```text
學生提出證明步驟
  -> 既有 router 判為 guide/respond_attempt
  -> Qwen3-4B Thinking 對照 reference_proof 驗證
  -> 保存第一個缺口與完整缺漏清單
  -> 注入 TutorDriver 的 grounded system prompt
  -> qlora_adapter_v9 生成蘇格拉底式候選回覆
  -> 現有內容守衛與候選語意審查
  -> 合格回覆送給學生
```

這是現有混合架構的窄幅延伸：Thinking 負責數學判斷，微調模型負責教學語氣，Controller 負責離散行為與安全規則。

## 元件與責任

### `dataset/review_backstop.py`

沿用既有 `find_gaps(statement, reference_proof, draft)`。如實作時需要統一 diagnostics，可增加薄包裝函式，但不得另建 verifier 模型、另增外部套件或改變現有全文審閱語意。

驗證結果分為三種：

- `issues`：回傳一個或多個證明錯誤／缺漏；第一項是本輪優先引導目標。
- `clear`：回傳空清單，代表 verifier 未在目前嘗試中找到問題；這不等同全文證明已通過 review，也不得直接切換到 `closed`。
- `unavailable`：服務離線、逾時或無法解析；不得假裝已驗證，也不得中斷對話。

### `dataset/tutor_driver.py`

新增 `VERIFY_THEN_GENERATE` 環境旗標，預設為 `1`。只有同時符合下列條件時執行生成前驗證：

- `REVIEW_BACKSTOP=1`；
- `VERIFY_THEN_GENERATE=1`；
- 非 peer mode；
- `phase == "guide"`；
- `turn_action == "respond_attempt"`。

驗證必須發生在 `_generate()` 之前。結果寫入獨立的 `pre_generation_verification` state，至少包含 `status`、`issues`、`first_issue`，並讓既有 `_backstop_block()` 可把診斷注入 system prompt。

`clear` 只能告訴生成模型「目前嘗試未找到缺漏」，不可視為全文 review 通過。`unavailable` 時不注入虛構診斷，後續仍走原有生成與候選審查；因此服務失敗是安全降級，不是錯誤放行。

現有生成後審查必須保留，因為它還負責候選數學錯誤、學生／Tutor 所有權歸因、active gap、Level 深度、洩漏與 writeup readiness。前置驗證不能取代這些職責。

### 成對評估腳本

新增一個獨立評估入口，使用固定的高等數學證明題與帶錯學生嘗試，分別在 `VERIFY_THEN_GENERATE=0` 與 `1` 下執行。兩組必須使用相同的 `qlora_adapter_v9`、解碼設定、題目與學生輸入。

每筆結果保存：

- 題目與案例識別碼；
- 學生嘗試及預期第一錯誤；
- 是否啟用前置驗證；
- verifier diagnostics；
- 最終助教回覆；
- 第一錯誤是否命中、針對性、數學正確性、洩漏、單問句及行為規範判定；
- verifier 與整輪延遲。

輸出同時提供逐案例紀錄與彙總，避免平均分掩蓋特定題型退化。評估不更新既有 regression baseline。

## 行為不變量

- 助教不得代寫完整證明，也不得洩漏 `reference_proof`。
- 一般引導維持單一問題，Level 0/1/2 的提示深度規則不變。
- `respond_attempt` 應聚焦學生最新證明步驟的第一個關鍵錯誤或缺漏。
- verifier 的完整診斷只供幕後使用；學生只看見經微調模型包裝的引導語。
- walkthrough 仍使用已驗證的預寫教學步驟，不加入此前置驗證。
- 全文證明仍走現有 two-pass review workflow；局部嘗試的 `clear` 不得提前結案。
- peer mode 沒有可靠參考解時維持誠實降級，不啟用此流程。
- verifier 不可用時不得製造通過結論、改變 phase 或遺失 session 進度。

## 錯誤處理與可觀測性

- verifier 回傳 `None`、逾時、解析失敗或服務不可達時，記錄 `status="unavailable"`。
- 每輪 diagnostics 必須能分辨功能關閉、條件不適用、成功找到問題、未找到問題及服務不可用。
- 不把 verifier 的原始思考鏈存入學生對話，也不輸出給學生。
- `VERIFY_THEN_GENERATE=0` 應精確恢復目前分支的既有行為，供 A/B 基準比較。

## 測試與驗證

採 TDD 實作，最低測試集合如下：

1. `respond_attempt` 的呼叫順序為 verify 再 generate。
2. verifier 找到的第一個缺口確實出現在生成時的幕後 prompt。
3. 純卡住、澄清、拒絕代寫、peer、walkthrough、review 與 closed 不誤觸此流程。
4. `clear` 不會把 guide 直接切到 review 或 closed。
5. `unavailable` 不會中斷對話或虛構驗證通過。
6. `VERIFY_THEN_GENERATE=0` 不執行前置驗證。
7. 既有 Level、防洩漏、單問句、候選審查與 phase 測試全部通過。
8. 執行 `python dataset/regression_suite.py --quick`。
9. 執行成對 A/B 評估，人工檢查所有退化案例，而非只比較平均分。
10. 本機模型、Ollama 與評審後端可用時執行完整 `python dataset/regression_suite.py`；若外部條件不允許，交付時明列未完成項與原因。

## 成功判準

- 既有確定性測試與 quick regression 無回歸。
- B 組不降低數學正確性、防洩漏、單問句與行為規範指標。
- B 組在帶錯學生證明嘗試上的第一錯誤命中率或回覆針對性優於 A 組；若沒有可辨識改善，則不宣稱 verify-then-generate 有效。
- 最終報告列出品質差異與額外延遲，據此給出採用、條件式採用或不採用判定。
