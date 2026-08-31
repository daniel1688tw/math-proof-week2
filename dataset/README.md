# dataset/ — grounded 蘇格拉底資料集、驅動程式與評估

本目錄包含人工撰寫並驗證的題目／參考解、SFT 對話、助教狀態機、自動備課與測試。

## 主要資料

| 檔案 | 內容 |
| --- | --- |
| `problems.json` / `problems_en.json` | 50 道中英平行題目與參考解 |
| `train.jsonl` / `val.jsonl` | 中英平行、messages 格式的 SFT 對話 |
| `qlora_adapter_v9/` | 部署用 LoRA adapter（權重不進 git） |

提示時機由同一套 `stuck_count` 狀態機控制；提示內容可由題目內的 `hint_ladder*`
或 `hint_ladders*.json` 提供。`phase`、`turn_action` 與 level 分開管理。

## 引導與逐步教學

`tutor_driver.py` 的一般引導路徑：

| 連續卡住次數 | 行為 |
| --- | --- |
| 0 | Level 0：只問一個聚焦問題，不點名定理或技巧 |
| 1 | Level 1：把前一個問題拆成更小、更具體的子問題 |
| 2 | Level 2：給一個可執行微支架；可含一個必要公式，但不可繼續代寫後續推導或結論 |
| 3 | 切換到 `walkthrough` 逐步教學 |

學生提出新的可操作數學內容時，`stuck_count` 歸零；純重貼舊步驟則保留計數。
持久 phase 只有 `guide / walkthrough / review / closed`；`respond_attempt`、
`answer_clarification`、`refuse_tutor_write` 等是當輪 action，不是 phase。

逐步教學每輪固定呈現「一個教學步驟＋一個確認問題」。學生只有一次作答機會：

- 回答交給與 Review／Rectify 相同的思考型審閱後盾做語意判定，不做字串比對。
- 回答正確就前進；回答錯誤、不完整或未回答目前問題時，顯示參考答案後前進。
- 審閱服務不可用時停在同一步，不判學生錯、不揭答，也不虛構已完成的學習進度。
- 全部步驟完成後，要求學生自行寫出完整證明，再進入既有 review 審閱。

## 自動備課

`auto_reference.py` 依序執行：

```text
PROVER × 3 → VERIFIER → 必要時 REPAIR／再驗證 → SEGMENTER
```

輸出包含 `reference_proof` 與 3–6 個 `teach_steps`。每個步驟包含：

```text
step_id, explain, check, expected_answer,
accepted_answers, common_errors
```

SEGMENTER 最多嘗試三次；每次都需通過確定性結構檢查及獨立數學審閱。驗證失敗的題目
標為 `unverified`，Driver 進入誠實的同學模式。

## 主要測試

| 檔案 | 用途 |
| --- | --- |
| `test_driver_unit.py` | 狀態機、守衛、逐步教學與自動備課單元測試 |
| `test_phase_routing.py` | 四 phase、合法 event、0→1→2→3 與 action 路由 |
| `test_review_workflow.py` | 全文審閱、局部訂正、乾淨全文與 closed 重審 |
| `test_app.py` | app 與自動備課整合 |
| `test_dataset.py` / `validate.py` | 訓練資料分布與格式驗證 |
| `regression_suite.py` | GPU／評審後端的部署前守門 |

## 是否需要重新訓練

目前部署 adapter 仍為 v9。Driver／phase 文件同步不會改動 `train.jsonl`、`val.jsonl`
或 adapter 權重；只有修改 SFT 資料或重新訓練 adapter 時才需要執行訓練流程。

完整審查見 `docs/code-review-level-phase-2026-08-31.md`。
