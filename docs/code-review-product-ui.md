# Code Review：商品化介面（`feature/product-ui`）— 第 2 次審查

- 審查日期：2026-07-27（第 2 次；本檔覆蓋前一版評估）
- 審查範圍：本分支相對基底 `training-iter-v11` 的程式碼變更
  - `dataset/app.py`（216 行，已含 F1/F2 修復）
  - `dataset/auto_reference.py`（+15 行：`build_reference` 新增選填 `progress_cb`）
  - `dataset/test_app.py`（新增，純邏輯單元測試）
- 審查方法：逐行人工重審 + 客觀證據（單元測試、`py_compile`、Gradio 行為實證）
- 審查者：Claude（Opus 4.8）

> **與前版差異**：第 1 次審查提出的 **F1（Medium）** 與 **F2（Low）已修復並經本次複驗確認**；
> 本次為修復後的重新全面審查，並補上更深一層的觀察（N1–N3）。

---

## 1. 客觀證據（Evidence）

| 檢查 | 結果 |
|---|---|
| 單元測試 `python dataset/test_app.py` | **全數通過（22 斷言）**：progress_cb×3、向後相容、assemble/opener/check_ollama、`_run_prepare` 正常/例外兩路 |
| `py_compile app.py auto_reference.py test_app.py` | **OK**（無語法錯誤）|
| `import app` 是否載入模型 | **否**（模型只在 `main()` 內載——隔離約束成立，測試不需 GPU）|
| Gradio 6 `build_ui` 建構 + 伺服器服務 | **HTTP 200**（含 F1 的 `[send_btn, msg_tb]` 雙輸出停用鏈，接線有效）|
| `gr.State` 執行期是否 deepcopy 值 | **否**（`preprocess`/`postprocess` 原樣回傳）→ 以參照持有含模型的 driver，不複製 CUDA 模型 |
| `.then(_enable*)` 於 handler 失敗後是否仍執行 | **是**（`trigger_only_on_success` 預設 False）→ 控制項不會卡在停用狀態 |

---

## 2. 修復複驗（F1 / F2）

| # | 修復內容 | 複驗結果 |
|---|---|---|
| **F1（Medium）** 生成中 Enter 重送 | 送出鏈改為以 `_disable_send`/`_enable_send`（各回 2 個 update）**同時停用 `send_btn` 與 `msg_tb`**（[app.py:191-196](../dataset/app.py#L191-L196)）| ✅ 停用 update 不帶 value，`msg_tb` 內容保留供 `on_send` 讀取；生成中 Enter 被擋。建構服務 HTTP 200 |
| **F2（Low）** 開場生成無例外處理 | `on_prepare` 的 `TutorDriver(...)`＋`driver.start()` 包 try/except（[app.py:143-150](../dataset/app.py#L143-L150)），失敗保留輸入態並友善回報 | ✅ 與 `on_send` 對稱；py_compile OK |

---

## 3. 尚存發現（本次全面審查）

嚴重度：**High**＝正確性/資料損毀；**Medium**＝特定情境錯誤或明顯 UX 缺陷；
**Low**＝邊角/資源/風格；**Info**＝觀察，未必需改。**本次無 High/Medium。**

| # | 位置 | 類別 | 嚴重度 | 摘要 | 狀態 |
|---|---|---|:---:|---|---|
| F3 | [app.py:37](../dataset/app.py#L37) | resource | **Low** | `check_ollama` 未關閉 response（無 context manager）| 待處理 |
| F4 | [app.py:96](../dataset/app.py#L96) | UX | **Low** | `ollama_warn` 僅啟動時判一次（狀態改變不更新；啟動阻塞至多 3 秒）| 待處理 |
| F5 | [app.py:80](../dataset/app.py#L80) | design | **Low** | 備課背景執行緒無法取消（關分頁後仍跑到 Ollama timeout）| 待處理（產品化）|
| F6 | [app.py:197](../dataset/app.py#L197) | UX | **Info** | `reset_btn` 於進行中未停用，備課/生成中按重置可能與佇列中的 handler 競態 | 觀察 |
| N1 | [app.py:147](../dataset/app.py#L147), [171](../dataset/app.py#L171) | security/UX | **Low** | 直接把 `{e!r}`（例外 repr）顯示給使用者，可能洩漏內部路徑/細節 | 新增（產品化）|
| N2 | [app.py:123-159](../dataset/app.py#L123-L159) | readability | **Info** | 三處「錯誤/提示 yield」樣板重複；`opener_for(proof)` 算兩次 | 新增 |
| N3 | [app.py:211](../dataset/app.py#L211) | config | **Info** | host/port（`127.0.0.1`/`7860`）寫死，未支援 env 覆寫 | 新增 |

### F3（Low）`check_ollama` 未關閉連線
`urllib.request.urlopen(url)` 回傳的 response 未讀取或關閉，連線可能延遲釋放。
**建議**：`with urllib.request.urlopen(url, timeout=timeout): return True`。

### F4（Low）`ollama_warn` 僅啟動時計算
警告在 `build_ui` 時判定；使用者啟動後才開/關 Ollama 不會更新，且啟動阻塞至多 3 秒。
**建議**（可選）：改為每次備課前即時判定，或縮短啟動 timeout。

### F5（Low，設計取捨）備課執行緒不可取消
`worker` 為 daemon 執行緒，關分頁/重置時 `build_reference`（Ollama 至多 600 秒）仍在背景跑完。
單人 Demo 影響有限（daemon 隨程序退出清理）。**建議**（未來產品化）：加協作式取消旗標。

### F6（Info）`reset_btn` 進行中未停用
因 `concurrency_limit=1`，reset 會排在目前 handler 之後，順序大致安全；但若目前 handler 為
generator 之後仍 yield，可能覆蓋 reset 的輸出、狀態短暫不一致。單人情境影響極小。

### N1（Low，新增）例外 repr 直接顯示給使用者
[app.py:147](../dataset/app.py#L147)（建立助教失敗）、[app.py:171](../dataset/app.py#L171)
（`driver.step` 失敗）將 `{e!r}` 直接呈現於 UI。本機單人 Demo（使用者即操作者）可接受，
但若對外開放，例外 repr 可能洩漏檔案路徑或內部結構。
**建議**（產品化）：對外顯示通用訊息、細節寫入伺服器日誌（`print`/`logging`）。

### N2（Info，新增）錯誤 yield 樣板重複、`opener_for` 重算
`on_prepare` 有三處幾乎相同的「回到輸入態＋顯示訊息」yield（空題、備課錯誤、建立助教錯誤），
且 `opener_for(proof)` 於 [app.py:145](../dataset/app.py#L145) 與 [155](../dataset/app.py#L155)
各算一次。
**建議**（可選）：抽一個 `_input_state(msg)` 小工具回傳該 5-tuple；`opener` 先算一次存變數。
純可讀性，無行為影響。

### N3（Info，新增）host/port 寫死
[app.py:211](../dataset/app.py#L211) 的 `server_name`/`server_port` 未支援環境變數覆寫。
**建議**（可選）：`os.environ.get("APP_PORT", "7860")` 等，方便換埠或區網分享。

---

## 4. 正面評價（Strengths）

- **關注點分離**：純函式（`check_ollama`/`assemble_problem`/`opener_for`/`_run_prepare`）可單元
  測試且 `import app` 不載模型——測試不需 GPU（已實證）。
- **向後相容的最小改動**：`build_reference` 僅新增選填 `progress_cb`，不傳則行為逐字不變。
- **健壯性到位**：`_run_prepare` worker `try/finally` 保證送結束哨兵（有專門測試）；
  `on_send`、`on_prepare` 兩處模型呼叫皆有例外防護（F2 修復後對稱）。
- **執行緒同步正確**：`holder` 的寫入在 `queue.put` 之前，主執行緒於收到哨兵後才讀取，
  queue 提供 happens-before 記憶體屏障——無資料競態。
- **資源安全**：`gr.State` 以參照持有 driver（實證 Gradio 6 執行期不 deepcopy）。
- **並發正確**：`concurrency_limit=1` 序列化單 GPU；進行中停用控制項且 `.then` 於成敗皆恢復
  （已實證），F1 修復後連 Enter 重送亦擋住。
- **測試設計**：`_run_prepare` 正常與例外兩路皆有斷言，鎖住健壯性契約。

---

## 5. 判定

**可作為本機單人 Demo 上線。** 本次全面審查**無 High/Medium 缺陷**；F1/F2 已修復複驗。
尚存 F3–F6 與新增 N1–N3 皆為 **Low/Info**，主要與「未來真正產品化（對外多人）」相關，
本機 Demo 情境下可延後處理。建議下次觸碰此檔時順手處理 F3（context manager）與 N2
（可讀性小重構）。

| 面向 | 前版（修復前）| 本版（F1/F2 修復後）|
|---|:---:|:---:|
| 正確性 | 4.5 | 4.5 |
| 健壯性 | 4.0 | **4.5** |
| 可讀性/結構 | 4.5 | 4.5 |
| 測試涵蓋 | 4.0（純邏輯佳；UI 互動仰賴手動驗收）| 4.0 |
| **總評** | 4.25 / 5 | **4.4 / 5** |

> 仍待部署端手動驗收：真模型＋Ollama＋瀏覽器下的四情境（只有題目逐級引導／錯誤證明糾正／
> Ollama 離線同學模式／重新開始換題）。此為 UI 互動層，非自動測試可涵蓋。
