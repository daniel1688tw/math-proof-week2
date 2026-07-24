# 蘇格拉底助教 商品化介面（Gradio 本機 Demo）— 設計文件

- 日期：2026-07-24
- 分支：`feature/product-ui`（自 `training-iter-v11` 分出）
- 基底部署形態：`qlora_adapter_v9` + Qwen3-4B（4-bit nf4）+ `tutor_driver.py`

## 目標

把現有的蘇格拉底式高等數學證明引導助教包成一個**簡單、本機、單人**的圖形介面，
讓使用者**貼上自己的題目**（可含也可不含目前的證明嘗試），由助教慢慢引導。
定位是展示／自用 Demo，不是雲端多人服務。

## 使用者情境（皆須支援）

1. **只有題目、沒有方向**：使用者只貼題目、不給證明 → 助教從第一個提示開始，
   靠 driver 既有的 stuck counter／提示梯／walkthrough 逐級慢慢引導。
2. **貼上寫到一半／完整的證明**：助教審閱、逐點回饋。
3. **給的證明是錯的**：助教不直接給答案，路由到審閱 → 審閱後盾找碴 → 引導改正（rectify）。
4. **助教自己也沒把握的題目**（備課驗證失敗）：誠實降級為同儕（同學模式），坦白沒把握、陪同探索。

## 非目標（YAGNI，本次明確排除）

- 無帳號、登入、多人並發（單 GPU、單人 Demo）。
- 無跨程序重啟的歷史保存。
- 無 adapter 版本切換 UI、無題庫瀏覽器、無 driver 內部狀態除錯面板。
- 無雲端部署、無打包成 .exe。
- 無 token 級串流（見下方理由）。

## 架構總覽

新增單一入口 `dataset/app.py`（Gradio 單體 App）。啟動時**載入模型一次並常駐**於程序記憶體
（沿用 `interactive_turn.py` 的 `load_model()` 邏輯）。使用者以瀏覽器連 `localhost` 操作。

- 單 GPU → Gradio 佇列設 `concurrency_limit=1`，所有生成序列化，不會同時觸發兩次推理。
- **不改動** `tutor_driver.py`、評估腳本、守門資產（`regression_suite.py` 等）。
  driver 對「使用者自帶題目」已能優雅處理，無須改。

### driver 既有能力（本設計所倚賴、不需修改的事實）

- `TutorDriver(tok, model, problem)`；`problem` 為 dict，含 `statement`、選填 `reference_proof`／
  `teach_steps`／`hint_ladder`／`grounding`。
- `d.start(opener=None)`：`opener` 即「學生開場白」。留空時預設請求第一個提示。
- `d.step(student_text)`：推進一輪，回傳完整助教回覆（已含所有後處理防護）。
- `is_peer()`：`grounding == "unverified"` 或無 `reference_proof` → 自動同學模式。
- 缺 `hint_ladder` 時 `_ladder()` 回 `[]`、`_ensure_teach_steps()` 保底切分 —— 不會壞。
  （使用者自帶題目沒有預寫提示梯，等級 2 改用模型生成提示＋`teach_steps` walkthrough。）

## 使用流程（單頁、分階段顯示）

1. **輸入區**：
   - 題目敘述文字框（必填）。
   - 選填「你目前的證明／嘗試（可留空）」文字框。
   - 「開始備課」按鈕。
2. **備課中進度**：按下後呼叫 `auto_reference.build_reference(statement, progress_cb=…)`，
   以回呼把階段（`PROVER i/k → VERIFIER → REPAIR → SEGMENTER`）即時推到進度區。
3. **備課完成分流**：
   - `verified` → 組出 `problem` dict（`grounding="auto_verified"` + `reference_proof` + `teach_steps`），
     建 `TutorDriver`；`opener` = 使用者貼的證明（無則 `None`＝預設請求提示）→ `d.start(opener)`。
     顯示「已備課完成（grounded）」，展開對話區並顯示助教開場回覆。
   - `unverified` → 組 `problem`（`grounding="unverified"`）建 driver（同學模式）；
     `d.start(opener)` 首輪由 driver 確定性補上誠實聲明。展開對話區。
4. **對話輪**：使用者輸入 → `d.step()` → 追加到對話。driver 後處理需要完整文本
   （洩漏 15-gram 檢查、單問句截斷、回問保底重生成），**故不做 token 級串流**，
   改在生成期間顯示「思考中…」狀態。既有防護（洩漏檢查、單問句、審閱後盾等）照常生效。

## 元件與狀態

- `gr.State` 持有該 session 的 `TutorDriver` 實例（模型物件全域共享唯一份；driver 各 session 獨立）。
- Session 語言由 driver 既有的逐輪自判邏輯處理，介面不干預。
- 「重新開始」按鈕：清空 `gr.State` 與對話，回到輸入區。

## 需要的最小改動

| 動作 | 檔案 | 說明 |
| --- | --- | --- |
| 新增 | `dataset/app.py` | Gradio 入口；載模型、備課、對話串接 |
| 修改 | `dataset/auto_reference.py` | `build_reference` 加**選填** `progress_cb(stage: str, detail: str)` 回呼；不傳則行為與現在完全一致（向後相容） |
| 依賴 | 環境 | `pip install gradio`（lora_project env）；README 補一行啟動說明 |

`build_reference` 內既有的 `verbose` print 點（PROVER/VERIFIER/REPAIR/SEGMENTER）改為
「若有 `progress_cb` 則呼叫之」，print 行為保留。

## 錯誤處理

- **Ollama 離線 / 備課全數失敗** → `build_reference` 回 `unverified` → 同學模式（誠實降級）。
  啟動時偵測 Ollama 未在線則於介面頂端預警「備課功能需要 Ollama，未偵測到服務」。
- **模型載入失敗**（啟動時）→ 於終端印明確錯誤並結束，不啟動 Web 服務。
- **備課耗時**（每題數分鐘）→ 進度回呼持續更新維持 UI 存活；`_chat` 既有 timeout 沿用。
- **VRAM 注意（寫入說明，非程式處理）**：常駐 4-bit 4B（約 3.5GB）＋ 備課時 Ollama 會被擠到 CPU
  而變慢，是 6GB 卡的固有限制，Demo 可接受。

## 測試

- **Smoke 單元測試** `dataset/test_app.py`：mock `auto_reference._chat`，驗證
  (a) `progress_cb` 有被觸發且階段字串正確、
  (b) verified 路徑組出的 `problem` dict 欄位齊全（statement/grounding/reference_proof/teach_steps）、
  (c) unverified 路徑 `grounding="unverified"` 且觸發 `is_peer()`、
  (d) `opener` 空／非空分別對應「請求提示」與「送審閱」。
  不載入真模型（driver 生成以輕量 stub 或只驗證組裝邏輯）。
- **手動驗收**：啟動 app，(1) 貼已知可證題、不給證明 → 逐級引導；
  (2) 貼含錯誤的證明 → 審閱找錯並引導改正；(3) 貼無法驗證內容 → 同學模式誠實聲明。
- 既有 driver／評估測試不受影響（未改 driver）。

## 交付與範圍

- 產出：`dataset/app.py`、`auto_reference.py` 一處回呼改動、`test_app.py`、README 啟動段落。
- 全部落在 `feature/product-ui` 分支；不動守門基準、不動部署 adapter。
