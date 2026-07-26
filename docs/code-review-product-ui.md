# Code Review：商品化介面（`feature/product-ui`）

- 審查日期：2026-07-27
- 審查範圍：本分支相對基底 `training-iter-v11` 的程式碼變更
  - `dataset/app.py`（新增，206 行）
  - `dataset/auto_reference.py`（+15 行：`build_reference` 新增選填 `progress_cb`）
  - `dataset/test_app.py`（新增，117 行）
- 審查方法：逐行人工審查 + 客觀證據（單元測試、`py_compile`、Gradio 行為實證）
- 審查者：Claude（Opus 4.8）

---

## 1. 客觀證據（Evidence）

| 檢查 | 結果 |
|---|---|
| 單元測試 `python dataset/test_app.py` | **全數通過**（progress_cb×3、向後相容、assemble/opener/check_ollama、`_run_prepare` 正常/例外兩路）|
| `py_compile app.py auto_reference.py test_app.py` | **OK**（無語法錯誤）|
| `import app` 是否載入模型 | **否**（模型只在 `main()` 內載，測試不需 GPU——隔離約束成立）|
| Gradio 6 `build_ui` 建構 + 伺服器服務 | **HTTP 200**（煙霧測試）|
| `gr.State` 執行期是否 deepcopy 值 | **否**（`preprocess`/`postprocess` 原樣回傳；deepcopy 僅作用於 `__init__` 的預設值 `None`）→ 以參照持有 driver，**不會 deepcopy CUDA 模型**|
| `.then(_enable)` 於 handler 失敗後是否仍執行 | **是**（Gradio `trigger_only_on_success` 預設 False；`.then` 無論成敗都跑）→ 按鈕不會卡在停用狀態 |

---

## 2. 整體評價

程式品質**良好、可上線為本機 Demo**。純邏輯與 UI/模型清楚分離、可單元測試；`auto_reference`
變更純為新增、向後相容；已針對前一輪自審主動加了健壯性防護（worker `try/finally`、
`on_send` 例外處理、進行中停用按鈕）。以下發現多為**邊角健壯性/UX**，無阻斷性缺陷。

嚴重度定義：**High**＝正確性/資料損毀；**Medium**＝特定情境下的錯誤行為或明顯 UX 缺陷；
**Low**＝邊角/資源/風格；**Info**＝觀察，未必需改。

| # | 位置 | 類別 | 嚴重度 | 摘要 | 狀態 |
|---|---|---|:---:|---|---|
| F1 | `app.py` 送出鏈 | correctness/UX | **Medium** | 生成中按 Enter 仍可重複送出（只停用了 `send_btn`，`msg_tb.submit` 未擋）| ✅ **已修復（2026-07-27）** |
| F2 | `on_prepare` | robustness | **Low** | `on_prepare` 的 `driver.start()` 未包 try/except（與 `on_send` 不對稱）| ✅ **已修復（2026-07-27）** |
| F3 | `app.py:37` | resource | **Low** | `check_ollama` 未關閉 response（無 context manager）| 待處理 |
| F4 | `app.py:96` | UX | **Low** | `ollama_warn` 只在啟動時判一次（狀態改變不更新；且啟動阻塞至多 3 秒）| 待處理 |
| F5 | `app.py:80` | design | **Low** | 備課背景執行緒無法取消（關分頁後仍跑到 Ollama timeout）| 待處理（產品化）|
| F6 | `app.py` 重置鏈 | UX | **Info** | `reset_btn` 於進行中未停用，備課/生成中按重置可能與佇列中的 handler 競態 | 觀察 |

> **修復記錄（2026-07-27）**：F1 — 送出鏈改為同時停用 `send_btn` 與 `msg_tb`
> （`_disable_send`/`_enable_send` 各回傳 2 個 update），生成中按 Enter 亦被擋。
> F2 — `on_prepare` 的 `TutorDriver(...)`＋`driver.start()` 已包 try/except，開場生成失敗時
> 保留在輸入態並友善回報。測試全綠、UI 建構 HTTP 200。

---

## 3. 個別發現

### F1（Medium，✅ 已修復）生成中 Enter 鍵可重複送出
**位置**：[app.py:182-187](../dataset/app.py#L182-L187)
**問題**：`send_btn.click` 與 `msg_tb.submit` 是**兩個獨立觸發源**。停用 `send_btn` 只擋滑鼠點按，
生成期間使用者在輸入框按 Enter 仍會觸發 `msg_tb.submit` → 排入第二次 `on_send`。單 GPU
`concurrency_limit=1` 會序列化執行，不致崩潰，但會多跑一輪、且第二次的 `message` 此時輸入框
可能已被前一次清空（送出空字串→被 `on_send` 開頭擋掉）或送出殘留字，行為不直覺。
**失敗情境**：使用者送出訊息後、助教生成中，再次按 Enter → 佇列多一筆 on_send。
**建議**：一併停用 `msg_tb`（或改用一個 `gr.State`「生成中」旗標在 `on_send` 開頭短路），例如
`msg_tb.submit(_disable_both, ...).then(on_send, ...).then(_enable_both, ...)`，`_disable_both`
回傳 `[gr.update(interactive=False)]*2` 同時停用 `send_btn` 與 `msg_tb`。

### F2（Low，✅ 已修復）`on_prepare` 的 `driver.start()` 未做例外處理
**位置**：[app.py:142-144](../dataset/app.py#L142-L144)
**問題**：`on_send` 的 `driver.step()` 已包 try/except（[app.py:162-165](../dataset/app.py#L162-L165)），
但 `on_prepare` 的 `driver.start(opener=...)` 沒有。若模型在開場生成時拋例外，`on_prepare`
會向上拋、對話區不會展開、進度停在最後一行。**按鈕仍會被 `.then(_enable)` 恢復**（已實證），
故非卡死，但使用者看到的是「備課完成卻無下文」。
**建議**：與 `on_send` 對稱地包住 `driver.start()`，失敗時在進度區顯示友善訊息並保留在輸入態。

### F3（Low）`check_ollama` 未關閉連線
**位置**：[app.py:36-40](../dataset/app.py#L36-L40)
**問題**：`urllib.request.urlopen(url)` 回傳的 response 未被讀取或關閉，連線可能延遲釋放。
**建議**：`with urllib.request.urlopen(url, timeout=timeout): return True`。

### F4（Low）`ollama_warn` 僅啟動時計算一次
**位置**：[app.py:96-97](../dataset/app.py#L96-L97)
**問題**：警告訊息在 `build_ui` 時判定；若使用者啟動後才開/關 Ollama，警告不會更新。且
`check_ollama` 預設 timeout 3 秒會阻塞啟動。
**影響**：Demo 可接受；若在意可改為每次備課前即時判定、或縮短啟動 timeout。

### F5（Low，設計取捨）備課執行緒不可取消
**位置**：[app.py:70-80](../dataset/app.py#L70-L80)
**問題**：`worker` 為 daemon 執行緒，使用者關分頁/重置時，`build_reference`（Ollama 呼叫，
至多 600 秒 timeout）仍會在背景跑到結束。單人 Demo 影響有限（daemon 隨程序退出清理）。
**建議**（未來產品化）：加入取消旗標與 `build_reference` 的協作式中止點。

### F6（Info）`reset_btn` 進行中未停用
**位置**：[app.py:188-191](../dataset/app.py#L188-L191)
**問題**：備課/生成進行中，`reset_btn` 仍可點；由於 `concurrency_limit=1`，reset 會排在目前
handler 之後執行，順序大致安全，但若目前 handler 之後又 yield（generator）可能覆蓋 reset 的
輸出，狀態顯示短暫不一致。單人情境影響極小。

---

## 4. 正面評價（Strengths）

- **關注點分離**：`check_ollama`/`assemble_problem`/`opener_for`/`_run_prepare` 為純函式，
  可單元測試且 `import app` 不載模型——測試不需 GPU（已實證）。
- **向後相容的最小改動**：`build_reference` 僅新增選填 `progress_cb` 與 `_emit`，不傳則行為
  逐字不變，且既有 `verbose` print 保留（已測 backward-compat）。
- **健壯性**：`_run_prepare` 的 worker 以 `try/finally` 保證送出結束哨兵，備課例外不會讓 UI
  永久卡死（有專門單元測試覆蓋）；`on_send` 對 `driver.step()` 例外亦有防護。
- **資源安全**：`gr.State` 以參照持有含模型的 driver，經實證 Gradio 6 執行期不 deepcopy，
  無 CUDA 模型被複製之虞。
- **並發正確**：`concurrency_limit=1` 序列化單 GPU 推理；進行中停用按鈕（`.then` 於成敗皆
  恢復，已實證）避免佇列被連點塞爆。
- **測試設計**：`_run_prepare` 的正常與例外兩條路徑都有斷言，鎖住健壯性契約。

---

## 5. 判定

**可作為本機單人 Demo 上線。** 無 High/阻斷性缺陷。**F1（Medium）與 F2（Low）已於 2026-07-27
修復**；F3–F6 屬邊角，待真正產品化時一併處理。

| 面向 | 修復前 | 修復後（F1/F2）|
|---|:---:|:---:|
| 正確性 | 4.5 | 4.5 |
| 健壯性 | 4.0 | 4.5 |
| 可讀性/結構 | 4.5 | 4.5 |
| 測試涵蓋 | 4.0（純邏輯佳；UI 互動仰賴手動驗收）| 4.0 |
| **總評** | **4.25 / 5** | **4.4 / 5** |
