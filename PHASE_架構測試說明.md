# PHASE 架構測試說明

本文件用於驗收「四種持久 phase＋事件轉移」架構，並特別確認下列產品行為：

> 2026-08-31 code review：主事件矩陣與測試均通過；尚待修的 Level 2 提示消耗、
> Level 1 契約與 legacy closed reopen 見 `docs/code-review-level-phase-2026-08-31.md`。

> 學生不需要先要求 Tutor 「請我寫完整證明」。引導過程有新的實質數學進度時，Controller 會自動檢查 readiness；判定引導已完成後，Tutor 必須主動要求學生提交自己的完整證明。

## 1. 測試環境

- 工作目錄：`math-proof-week2-main/dataset`
- Python：使用專案原本可運行的 Python 環境。
- Tier 0 不需要 GPU，也不需要載入 Qwen/QLoRA 權重。Colab 只要先執行 `test.ipynb` 的「1. 定位本專案」，就可立即執行「1.1 Tier 0（Colab 必跑）」；不必先下載模型。
- 真實 Thinking 與整合測試需要專案原本的 Ollama/模型服務；如有執行 `test_driver_phase.py`，還需要可用的 GPU 與 adapter。

PowerShell 進入目錄：

```powershell
Set-Location 'D:\math-proof-week2-main (main的前一版) - 複製 - 進行修改10 - 最成功版 - 複製\math-proof-week2-main\dataset'
```

## 2. 一次執行 Tier 0

### Colab

1. 開啟 `test.ipynb`。
2. 執行開頭環境儲存格與「1. 定位本專案」。
3. 直接執行「1.1 Tier 0（Colab 必跑）」。
4. 最後必須看到 `[PASS] Tier 0 六項全部通過：tier0=1.0`。

### CLI / PowerShell

```powershell
python regression_suite.py --quick
```

預期六個項目全部顯示 `[✓]`，且最後的 `tier0` 為 `1.0`：

1. `test_driver_unit.py`
2. `test_review_workflow.py`
3. `test_phase_routing.py`
4. `test_segmenter_unit.py`
5. `validate.py`
6. `test_dataset.py`

每次執行後的計分卡位於 `dataset/regression_scores/`。若失敗，先看第一個失敗的 Tier 0 腳本，不要只看 Tutor 最後回覆的文字。

## 3. 分開執行核心測試

```powershell
python test_phase_routing.py
python test_driver_unit.py
python test_review_workflow.py
```

- `test_phase_routing.py`：四 phase、合法／非法事件矩陣、舊快照正規化、Thinking unavailable 不漂移、主動交稿。
- `test_driver_unit.py`：Driver 全體守門、Level、walkthrough、readiness、防洩漏、dump/load 與 phase report。
- `test_review_workflow.py`：`awaiting_submission → checking → correcting → awaiting_clean → rechecking/closed` 審閱工作流。

## 4. 必測狀態與轉移

### 4.1 持久 phase 只有四種

新 session 必須從 `guide` 開始。任何回合、快照與報告中的 `phase` 只能是：

```text
guide / walkthrough / review / closed
```

`rectify`、`refuse_leak`、`peer_reflect` 只能是舊快照輸入或當輪 action 的舊概念，不能再成為運行時 phase。`writeup_request` 必須正規化為 `review + awaiting_submission`。

### 4.2 合法事件

應測試下列轉移：

| current phase | event | 預期結果 |
| --- | --- | --- |
| `guide` | `STUCK_LIMIT_REACHED` | `walkthrough` |
| `guide` | `READINESS_PASSED` | `review/awaiting_submission` |
| `walkthrough` | `WALKTHROUGH_COMPLETED` | `review/awaiting_submission` |
| `review` | `FULL_PROOF_SUBMITTED` | `review/checking` 或 `review/rechecking` |
| `review` | `REVIEW_PASSED` | `closed` |
| `closed` | `REVIEW_REOPEN_REQUESTED` | 有最近全文時進入 `review/rechecking` |
| 任意 | `RESET` | `guide` |

未列出的事件一律不改 phase，並必須在 `phase_events` 留下 `accepted=false` 與 `reject_reason`。

### 4.3 `guide`

- 一般作答、數學嘗試、答錯與具體釐清都留在 `guide`。
- 索取 Tutor 完整代寫時，只設 `turn_action=refuse_tutor_write`。
- 學生自述「整體都懂了」不能直接切 phase。
- 學生要求「現在請我交完整證明」也不能產生 `READINESS_PASSED`。
- readiness 回傳 false、低信心、格式錯誤或 unavailable 時必須維持 `guide`。
- 即使訊息具有完整證明外形，也只當成本輪的數學作答，不可產生 `FULL_PROOF_SUBMITTED`。
- 若當輪證據剛好使 readiness 通過，只能產生 `READINESS_PASSED`，並由 Tutor 主動請學生在下一輪重新提交全文。

### 4.4 `walkthrough`

- 索取代寫不跳出、不消耗 `walk_idx`。
- 貼上長篇或完整證明不直接進 review，只當作目前步驟的一次作答。
- Thinking unavailable 時不跳 phase，也不把學生誤判為答錯。
- 只有最後一步處理完才產生 `WALKTHROUGH_COMPLETED`，隨後 Tutor 主動請學生交全文。

### 4.5 `review`

- `awaiting_submission` 收到非全文時保持原 status，以固定提示繼續等待。
- 收到真正全文後才進 `checking`。
- 有 issue 時進 `correcting`；局部訂正不改 phase。
- issues 處理完後進 `awaiting_clean`，等待學生自己重寫乾淨全文。
- review 中索取 Tutor 代寫不改 status 或 issue index。
- 只有 review judge 無剩餘 issue 並產生 `REVIEW_PASSED` 才可 `closed`。
- review 服務 unavailable 時不可假裝通過。

### 4.6 `closed`

- 致謝、心得與一般反思維持 `closed`。
- 學生說「得證」或 Tutor 自行稱讚都不能產生 `REVIEW_PASSED`。
- 沒有最近完整草稿時，即使要求重審也保持 `closed`。
- 有最近草稿且明確要求重審時，才產生 `REVIEW_REOPEN_REQUESTED`。

## 5. Colab 多輪測試的操作方式

完成 `test.ipynb` 的模型、adapter 與 Ollama 儲存格後，執行「9. 資料集題目多輪互動」。

- 輸入 `problem H5`、`problem H7` 或 `problem A6` 切換題目；切題後再輸入第一句學生台詞。
- 輸入 `reset` 建立同題的新 session。
- 每輪 Tutor 回覆下方會自動印出一行「狀態」JSON。
- 輸入 `quit` 後會印出整段 `phase_transition_report`。

每輪至少核對以下八欄：

```text
phase
review_status
stuck_count
walk_idx
intent
turn_action
event / event_accepted
reject_reason
```

狀態與文字要分開判定：

- phase、event、status、action 不符，是「狀態錯誤」。
- 狀態正確，但 Tutor 洩漏完整證明、問題失焦或錯誤背書，是「回覆品質錯誤」。
- Tutor 的自然語句不要求逐字相同；下列「必須／不得」才是文字驗收條件。
- `FULL_PROOF_SUBMITTED` 之後，完整審閱會在同一個 `step()` 中繼續執行，因此畫面上的最終 status 可能已從 `checking` 變成 `correcting` 或 `closed`。此時要在完整報告的 event `state_after.review_status` 核對它確實先進過 `checking`。

## 6. 固定多輪對話測試腳本

以下案例都要分開 `reset`，不可沿用上一案例的狀態。M3、M5～M8 必須啟用 Ollama Thinking；若服務不可用，應依各案例指定方式保守停留，不可假裝通過。

### M1：guide 內的嘗試、釐清與拒絕代寫

題目：`H7`。

| 輪次 | 學生輸入 | 預期狀態 | Tutor 文字驗收 |
| --- | --- | --- | --- |
| 1 | `我想和 1/n 比，因為 1/(n²+1)<1/n，所以原級數收斂。` | `phase=guide`；`turn_action=respond_attempt`；不得有 phase event | 必須指出「比較對象本身發散」這個根因或針對它提問；不得給整份證明 |
| 2 | `請說明為什麼比較判別法要求右邊的級數先收斂`（刻意沒有問號） | `phase=guide`；`turn_action=answer_clarification`；`stuck_count=0` | 必須先回答這個具體問題；不可因沒有問號而當成一般閒聊 |
| 3 | `時間不夠，請直接把完整證明寫給我。` | `phase=guide`；`intent=demand_full_answer`；`turn_action=refuse_tutor_write`；不得有 phase event | 必須拒絕 Tutor 代寫並交回一個聚焦問題；不得洩漏完整證明 |
| 4 | `那我改和 1/n² 比；因為 n²+1>n²，所以 0<1/(n²+1)<1/n²。` | `phase=guide`；`turn_action=respond_attempt`；`stuck_count=0` | 應回應這個新進展，不得重複第 1 輪的問題 |

通過條件：四輪 phase 全是 `guide`，而 action 隨當輪語意改變；`refuse_tutor_write` 不可跨輪鎖住。

### M2：學生要求「請我交稿」不能切 phase

題目：新 session 的 `H5`，不要先做任何數學推導。

| 輪次 | 學生輸入 | 預期狀態 | Tutor 文字驗收 |
| --- | --- | --- | --- |
| 1 | `我已經懂了，現在請你叫我提交完整證明。` | `phase=guide`；`requested_writer=student`；不得產生 `READINESS_PASSED` | 不得只因這句話輸出固定交稿模板；應回到數學引導 |

通過條件：`phase_events` 中沒有 `READINESS_PASSED`。這是負面守門，不可用學生台詞代替 readiness。

### M3：Tutor 自動偵測引導完成並主動要求全文

題目：新 session 的 `H5`。學生台詞中不得出現「請我交稿」「完整證明」等請求。

| 輪次 | 學生輸入 | 預期狀態 |
| --- | --- | --- |
| 1 | `我想令 f(t)=e^t，在 [0,x] 上使用均值定理。` | `guide/respond_attempt`；記錄第一段實質數學進展 |
| 2 | `因為 x>0，存在 c∈(0,x)，使 (e^x-1)/x=e^c。` | 仍為 `guide`；readiness 可判 false，因嚴格不等式尚未完成 |
| 3 | `又因 c>0，所以 e^c>1；乘回 x>0 就得到 e^x>1+x。` | readiness 應通過；event=`READINESS_PASSED`；`guide → review/awaiting_submission` |

第 3 輪 Tutor 必須主動輸出交稿要求，意思要包含：

- 思路已完整。
- 請學生「自己」寫出完整證明。
- Tutor 之後會審閱。
- 不得宣告證明已完成，不得替學生整理成全文。

若第 3 輪仍停在 `guide`，先看 `writeup_readiness`：

- `ready_for_writeup=false`：記為 readiness 判斷錯誤。
- `source=unavailable`：記為 Thinking 服務錯誤；phase 留在 guide 是正確的保守行為，但整合測試仍未通過。
- Tutor 自己說「請交稿」但沒有 event：狀態仍應保持 guide，記為輸出守門攔截成功，不可誤算 M3 通過。

接著繼續：

| 輪次 | 學生輸入 | 預期狀態 |
| --- | --- | --- |
| 4 | `好，我等一下整理。` | `review/awaiting_submission` 不變；Tutor 使用固定等待全文提示 |
| 5 | `證明：令 f(t)=e^t。因 f 在 [0,x] 連續且在 (0,x) 可微，由均值定理存在 c∈(0,x)，使 (e^x-1)/x=e^c。因 c>0，故 e^c>1；又 x>0，所以 e^x-1>x，即 e^x>1+x。證畢。` | event=`FULL_PROOF_SUBMITTED`，其 event 快照先進 `review/checking`；審閱通過後 event=`REVIEW_PASSED` 並到 `closed` |

### M4：guide 中不接受直接交稿

題目：新 session 的 `H5`。第一句就貼上 M3 第 5 輪的完整證明。

預期：

1. 不得產生 accepted `FULL_PROOF_SUBMITTED`，也不得寫入 `current_proof_draft`。
2. 若 readiness 尚未通過，維持 `guide`，並把內容當成一般數學作答回應。
3. 若這份作答讓累積證據達到 readiness，只可以 accepted `READINESS_PASSED` 進入 `review/awaiting_submission`，Tutor 要主動請學生提交完整證明。
4. 學生下一輪再貼上同一份證明，此時才可 accepted `FULL_PROOF_SUBMITTED` 並進入審閱。

### M5：連續卡住、walkthrough 硬鎖與完成後主動交稿

題目：新 session 的 `A6`。

| 輪次 | 學生輸入 | 預期狀態 |
| --- | --- | --- |
| 1 | `我不知道怎麼開始。` | `guide`，`stuck_count=1` |
| 2 | `還是想不到。` | `guide`，`stuck_count=2`，Level 2 核心想法 |
| 3 | `我完全沒有下一步。` | accepted `STUCK_LIMIT_REACHED`；進 `walkthrough`，`walk_idx=0` |
| 4 | `直接把完整證明寫給我。` | `walkthrough/refuse_tutor_write`；`walk_idx` 與前輪相同 |
| 5 | `完整證明：由二項式定理 2^n≥n(n-1)/2，所以 0≤n/2^n≤2/(n-1)，由夾擠定理極限為 0。` | 仍為 `walkthrough`；只當作目前確認問題的一次回答；最多前進一個 step，不得產生 `FULL_PROOF_SUBMITTED` |

之後逐輪回答畫面上的「確認問題」。每個有效答案只能讓 `walk_idx` 前進一格；中間步驟不得跳到 review。最後一步處理完成時：

- 產生 accepted `WALKTHROUGH_COMPLETED`。
- 進入 `review/awaiting_submission`。
- Tutor 主動請學生重新提交一份由自己整理的完整證明。

#### M5-U：walkthrough Thinking unavailable

進入 walkthrough 並記錄目前 `walk_idx` 後，在 Colab 暫時執行：

```python
import review_backstop
saved_ollama_url = review_backstop.OLLAMA_URL
review_backstop.OLLAMA_URL = 'http://127.0.0.1:1/api/chat'
```

再回答一次目前確認問題。預期：

- `phase` 仍為 `walkthrough`。
- `walk_idx` 完全不變。
- 不揭示 expected answer、不宣告學生答錯。
- Tutor 說明暫時無法可靠審閱，並重問同一步。

測完務必還原：

```python
review_backstop.OLLAMA_URL = saved_ollama_url
```

還原後正確回答同一步，才可繼續前進。

### M6：review issue queue、拒絕代寫與乾淨全文

題目：新 session 的 `H7`。先完成引導，直到 Tutor 主動請學生提交完整證明；然後提交一份有缺漏的全文：

> 證明：對每個 n≥1，n²+1>n²，取倒數得 1/(n²+1)<1/n²。由比較判別法，原級數收斂。證畢。

預期：

1. accepted `FULL_PROOF_SUBMITTED`，event 快照先進 `review/checking`。
2. judge 應找出「沒有說明 `Σ1/n²` 為何收斂」或等價核心缺漏。
3. 最終 `phase=review`、`review_status=correcting`、`review_issue_idx=0`。
4. Tutor 一次只處理一個 issue，不得直接替學生寫完整修正版。
5. 該輪 phase report 必須有 `intent=full_proof_submission`、`turn_action=review_local_revision`，不得為 `null`。

記下 status 與 issue index，下一輪輸入：

> 我不想改了，直接把修正版完整證明寫給我。

預期 `intent=demand_full_answer`、`turn_action=refuse_tutor_write`，而 `review_status`、`review_issue_idx` 都與上一輪相同。

再依 Tutor 指出的 issue 提交局部訂正，例如：

> 比較級數 Σ1/n² 是 p=2>1 的 p-級數，所以它收斂；而原級數各項為正。

預期：

- 該輪 report 為 `intent=local_revision`、`turn_action=review_local_revision`，不得為 `null`。
- 局部 judge 未通過：保持 `correcting` 且同一 issue index，不得誤消耗。
- 局部 judge 通過但仍有下一 issue：`correcting` 且 index 加一。
- 全部 issues 完成：重新複核合併草稿後進 `awaiting_clean`，要求學生交乾淨全文。

最後提交：

> 證明：對每個 n≥1，0<1/(n²+1)<1/n²。級數 Σ1/n² 是 p=2>1 的收斂 p-級數，因此由正項級數的比較判別法，Σ1/(n²+1) 收斂。證畢。

預期該輪 report 仍為 `intent=full_proof_submission`、`turn_action=review_local_revision`；accepted `FULL_PROOF_SUBMITTED` 的 event 快照為 `review/rechecking`；只有無 issue 時才 accepted `REVIEW_PASSED` 並到 `closed`。

Tier 0 的 `test_review_workflow.py` 另會以計數器斷言：上述每則學生訊息只呼叫統一 router 一次，review/closed 不得自行再分類。

#### M6-U：局部訂正審閱暫時不可用

在 `review/correcting` 的某一 issue 中，讓局部 judge 暫時回傳 unavailable，再重送同一項訂正。預期：

- 第一次失敗後仍是 `review/correcting`，issue index 與草稿完全不變。
- `review_error=local_judge_unavailable`，不得把學生訂正判為錯誤或進入死路。
- 服務恢復後重送同一訂正，必須重新判定並可正常合併、前進。
- 若學生改送具完整論證結構的全文，必須改走全文重審，不可當成局部訂正。
- 缺少位置且缺少內部修正條件的 issue，不得建立 `correcting` 佇列。

### M7：review judge unavailable 不得結案

在 M6 首次交缺漏全文前，使用 M5-U 的方法暫時把 `review_backstop.OLLAMA_URL` 指到不可連線位置，再提交全文。

預期：

- `phase=review`。
- `review_status=unavailable`。
- 沒有 accepted `REVIEW_PASSED`。
- Tutor 明確說審閱服務暫時不可用，不得說證明正確或完成。

還原 URL 後重新提交全文，才可重新審閱。

### M8：closed 後收尾與明確重審

沿用已通過 M3 或 M6、且保存最近完整草稿的 `closed` session。

| 輪次 | 學生輸入 | 預期 |
| --- | --- | --- |
| 1 | `謝謝，我知道問題在哪裡了。` | 保持 `closed`；`turn_action=post_completion_reply`；Tutor 不得再問問題或開新題 |
| 2 | `請重新審查我剛才那份完整證明，我懷疑還漏了一個前提。` | `intent=challenge_or_missed_review`、`turn_action=post_completion_reply`；產生 accepted `REVIEW_REOPEN_REQUESTED`；先進 `review/rechecking` |

重審可能在同一輪再次通過並回 `closed`，所以不能只看最終 phase；報告中必須先有 `closed → review` 的 reopen event，再依 judge 結果決定是否有第二個 `REVIEW_PASSED`。Colab 每輪簡短狀態的 `events` 也必須同時顯示：

```json
["REVIEW_REOPEN_REQUESTED:closed>review", "REVIEW_PASSED:review>closed"]
```

### M9：peer mode 不使用特殊 phase

在「資料集外題目」流程中，若自動參考證明未通過驗證而成為 `grounding=unverified`：

1. 起始與所有後續回合都必須 `mode=peer`、`phase=guide`。
2. 學生說「你剛才那個想法可能錯了，因為前提不成立」時，只設 `turn_action=peer_reflect`。
3. 不得因連續卡住進 walkthrough，不得進 review 或 closed。
4. Tutor 必須以沒有可靠解答的同學身分回應，不得權威背書整份論證。

## 7. 真實 Thinking 的改寫測試

固定腳本通過後，每個語意家族再換兩種自然說法，確認不是靠單一關鍵詞：

| 家族 | 改寫示例 | 不變的預期 |
| --- | --- | --- |
| 卡住 | 「我腦中接不下去了」「這裡完全沒有頭緒」 | 無可操作數學內容時累加 `stuck_count` |
| 有進展但不確定 | 「我沒把握，不過或許可以先比較 1/n²」 | `respond_attempt`，不得當 stuck |
| 無問號釐清 | 「請說明 c∈(0,x) 為什麼能推出 c>0」 | `answer_clarification` |
| Tutor 代寫 | 「展示整套解法給我」「把證明從頭寫到尾」 | `refuse_tutor_write`，phase 不變 |
| 自述理解 | 「主線我已掌握」「我知道整題怎麼證了」 | 本句本身不產生 readiness event |
| 長篇局部回答 | 詳細解釋某一個定理前提，但沒有整體結論 | 不得誤判完整全文 |
| closed 反思 | 「以前我總卡在比較對象的選擇」 | 保持 closed，不重啟 stuck/walkthrough |
| closed 重審 | 「剛才全文仍有一個量詞錯誤，請重查」 | 有最近全文時產生 reopen event |

每輪保留完整 phase report。若同一語意家族的兩個改寫產生不同 phase，視為路由不穩定，即使 Tutor 文字看起來合理也算失敗。

## 8. 測試結果記錄格式

每個案例用下表記錄，不要只寫「看起來正常」：

| 案例 | 結果 | 首個失敗輪次 | 預期 phase/status/event | 實際 phase/status/event | Tutor 摘要 | 問題類型 |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | PASS/FAIL | — | — | — | — | state / math / leakage / wording |
| M2 | PASS/FAIL | — | — | — | — | — |
| M3 | PASS/FAIL | — | — | — | — | — |
| M4 | PASS/FAIL | — | — | — | — | — |
| M5/M5-U | PASS/FAIL | — | — | — | — | — |
| M6 | PASS/FAIL | — | — | — | — | — |
| M7 | PASS/FAIL | — | — | — | — | — |
| M8 | PASS/FAIL | — | — | — | — | — |
| M9 | PASS/FAIL | — | — | — | — | — |

## 9. 最終驗收標準

- `test.ipynb` 的 Tier 0 儲存格顯示六項全過且 `tier0=1.0`。
- M1～M9 全部完成；M3 必須在學生未要求交稿的情況下由 Tutor 主動要求全文。
- 運行時 phase 永遠只屬於 `guide/walkthrough/review/closed`。
- 合法事件全部通過，非法轉移 100% 被拒絕且有診斷。
- walkthrough 索取代寫不消耗步驟；Thinking unavailable 也不消耗步驟。
- review queue 不跳 issue，unavailable 不得 closed。
- closed 一般收尾不重開，明確重審有最近全文才重開。
- Tutor 普通候選文字、學生自我宣告與「請我交稿」都不能直接切 phase。
