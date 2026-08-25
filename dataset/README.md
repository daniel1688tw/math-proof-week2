# dataset/ — grounded 蘇格拉底資料集、驅動程式與評估

本目錄包含人工撰寫並驗證的題目／參考解、SFT 對話、助教狀態機、自動備課與測試。

## 主要資料

| 檔案 | 內容 |
| --- | --- |
| `problems.json` / `problems_en.json` | 50 道中英平行題目與參考解 |
| `train.jsonl` / `val.jsonl` | 中英平行、messages 格式的 SFT 對話 |
| `qlora_adapter_v9/` | 部署用 LoRA adapter（權重不進 git） |

教學深度不再依賴額外的提示資料檔。所有題目都由同一套 `stuck_count` 狀態機控制。

## 引導與逐步教學

`tutor_driver.py` 的一般引導路徑：

| 連續卡住次數 | 行為 |
| --- | --- |
| 0 | Level 0：只問一個聚焦問題，不點名定理或技巧 |
| 1 | Level 1：把前一個問題拆成更小、更具體的子問題 |
| 2 | Level 2：揭露已驗證步驟的定理／技巧／核心想法，不新增公式，再問一個問題 |
| 3 | 切換到 `walkthrough` 逐步教學 |

學生只要提出實質數學嘗試，`stuck_count` 就歸零。review、rectify、refuse_leak、
writeup_request、closed 等特殊階段優先，不會因卡住計數被誤切到逐步教學。

逐步教學每輪固定呈現「一個教學步驟＋一個確認問題」。學生只有一次作答機會：

- 回答交給與 Review／Rectify 相同的思考型審閱後盾做語意判定，不做字串比對。
- 回答正確就前進；回答錯誤、不完整、答不出來，或審閱服務不可用時，顯示參考答案後前進。
- 全部步驟完成後，要求學生自行寫出完整證明，再進入既有 review 審閱。

## 自動備課

`auto_reference.py` 依序執行：

```text
PROVER × 3 → VERIFIER → 必要時 REPAIR／再驗證 → SEGMENTER
```

輸出包含 `reference_proof` 與 3–6 個 `teach_steps`。每個步驟包含：

```text
step_id, explain, core_idea, check, expected_answer,
accepted_answers, common_errors
```

SEGMENTER 最多嘗試三次；每次都需通過確定性結構檢查及獨立數學審閱。驗證失敗的題目
標為 `unverified`，Driver 進入誠實的同學模式。

## 主要測試

| 檔案 | 用途 |
| --- | --- |
| `test_driver_unit.py` | 狀態機、守衛、逐步教學與自動備課單元測試 |
| `test_phase_routing.py` | 0→1→2→3、特殊階段優先與單次作答路由 |
| `test_app.py` | app 與自動備課整合 |
| `test_dataset.py` / `validate.py` | 訓練資料分布與格式驗證 |
| `regression_suite.py` | GPU／評審後端的部署前守門 |

## 是否需要重新訓練

本次修改只調整 Driver 狀態、prompt、自動備課 schema、測試與 notebook 路徑；沒有改動
`train.jsonl` 或 `val.jsonl` 的訓練樣本，因此不需要重新訓練。重新執行 `train.ipynb` 只在
之後另行修改 SFT 資料或想產生新 adapter 時才需要。
