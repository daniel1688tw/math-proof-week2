# 精簡 PHASE 架構修正提案

適用目錄：

`D:\math-proof-week2-main (main的前一版) - 複製 - 進行修改10 - 最成功版 - 複製`

本文件只提出修正方案，不代表已修改任何 Python、Notebook、資料集或模型檔案。

## 1. 目標

保留 `phase`，但只讓它表示「目前由哪一個持久工作流負責下一輪」，不再拿 phase
表示學生當輪的每一種意圖。目標是：

1. phase 數量少且定義互斥。
2. phase 只能由少數、可驗證的事件切換。
3. Thinking 模型只判學生訊息的語意事實，不直接決定 phase。
4. 學生與 Tutor 說話模型都不能單方面切換 phase。
5. 保留成功版既有的 Level、walkthrough、readiness、審閱佇列、同學模式與防洩漏設計。
6. 不針對特定微積分題、公式或固定學生措辭設計轉移規則。

## 2. 本次不處理的範圍

- 不調整 Level 0～2 的提示深度與問題品質。
- 不重做 teach steps、segmenter、參考證明生成或驗證。
- 不更改訓練資料內容與模型權重。
- 不替特定題目新增關鍵詞名單。
- 不把所有判斷合併成一個大型 Thinking prompt。

## 3. 成功版目前為何容易誤切

目前實際使用的狀態包含：

- `None`：一般引導。
- `rectify`：學生提出數學嘗試。
- `refuse_leak`：學生索取 Tutor 完整解答。
- `peer_reflect`：同學模式中重新檢查上一個想法。
- `walkthrough`：逐步教學。
- `writeup_request`：要求學生交完整證明。
- `review`：完整證明審閱與訂正。
- `closed`：結案。

其中 `rectify`、`refuse_leak`、`peer_reflect` 只描述「這一輪要怎麼回答」，不是需要跨輪
保存的工作流階段。把它們當 phase，會造成 `_detect_phase()` 幾乎每輪都覆寫 phase，
也讓 Thinking 的單輪 intent 分類波動直接變成 phase 波動。

此外，`walk_active`、`review_active`、`awaiting_clean_proof`、`writeup_asked`、
`done_closed` 又與 phase 重複表示工作流狀態。當任一處更新 phase、另一處忘記同步旗標時，
就會出現「文字在某階段、狀態卻在另一階段」的情況。

## 4. 建議只保留四個持久 phase

```text
guide → walkthrough → review → closed
  └───────────────→ review
closed ──明確重審──→ review
```

| phase | 唯一職責 | 保留的局部狀態 |
| --- | --- | --- |
| `guide` | 一般引導、Level 0～2、回應嘗試、釐清與拒絕代寫 | `stuck_count`、目前聚焦問題、累積證明進度 |
| `walkthrough` | 硬鎖的逐步教學 | `walk_idx`、`walk_lang`、已呈現步驟 |
| `review` | 等待完整交稿、全文審閱、局部訂正、等待乾淨全文 | `review_status`、issues、issue index、最近完整草稿 |
| `closed` | 已通過審閱後的確定性結案 | 最近完整草稿、結案紀錄 |

### 為何不另外保留 `writeup_request`

要求學生交稿只是進入審閱工作流的第一個狀態，不需要獨立 phase。沿用現有
`review_status`，新增或統一使用：

```text
review_status = awaiting_submission
```

Controller 判定引導完成後：

1. 將 `phase` 設為 `review`。
2. 將 `review_status` 設為 `awaiting_submission`。
3. 輸出現有的確定性交稿模板。

因此仍能明確知道系統正在等完整證明，又少一個 phase。

## 5. 舊 phase 到新架構的最小差異映射

| 現行值 | 新 phase | 新的當輪行為／局部狀態 |
| --- | --- | --- |
| `None` | `guide` | 一般 Level 引導 |
| `rectify` | `guide` | `turn_action=respond_attempt` |
| `refuse_leak` | `guide` | `turn_action=refuse_tutor_write` |
| `peer_reflect` | `guide` | `mode=peer`，`turn_action=peer_reflect` |
| `walkthrough` | `walkthrough` | 原 walkthrough 狀態原樣保留 |
| `writeup_request` | `review` | `review_status=awaiting_submission` |
| `review` | `review` | 沿用現有 `review_status` 與 review queue |
| `closed` | `closed` | 原結案行為原樣保留 |

這個映射不刪除原有教學能力，只把「當輪回覆方式」移出 phase。

## 6. phase 與當輪語意必須分工

### phase 回答的問題

> 下一輪由哪一個持久工作流接手？

### `StudentStateDecision` 回答的問題

> 學生這一輪是在作答、釐清、卡住、索取代寫、交全文，還是要求重審？

建議保留現有結構化欄位，例如：

```text
intent
learning_state
answers_current_question
has_actionable_math
advances_solution
requested_writer
confidence
evidence
```

但 Thinking 不再輸出或建議 final phase。phase 由 Controller 根據「目前 phase＋事件」
決定。

### 不應再成為 phase 的當輪行為

```text
normal_guide
respond_attempt
answer_clarification
refuse_tutor_write
peer_reflect
post_completion_reply
```

這些行為只影響本輪 system instruction，不跨輪鎖住工作流。

## 7. phase 只能由事件切換

建議使用少量、題型無關的事件：

```text
STUCK_LIMIT_REACHED
WALKTHROUGH_COMPLETED
READINESS_PASSED
FULL_PROOF_SUBMITTED
REVIEW_PASSED
REVIEW_REOPEN_REQUESTED
RESET
```

事件來源必須可驗證：

| 事件 | 產生者 | 必要條件 |
| --- | --- | --- |
| `STUCK_LIMIT_REACHED` | Controller | 只在 `guide`，且 `stuck_count` 達現行門檻 |
| `WALKTHROUGH_COMPLETED` | walkthrough state machine | `walk_idx` 已完成所有步驟 |
| `READINESS_PASSED` | readiness Thinking judge | 根據累積對話判 true，且通過信心與格式檢查 |
| `FULL_PROOF_SUBMITTED` | turn classifier＋全文結構守門 | 訊息本身具有完整證明外形；walkthrough 硬鎖時不產生此轉移 |
| `REVIEW_PASSED` | review Thinking judge | 完整證明已完成既定審閱流程且無剩餘 issue |
| `REVIEW_REOPEN_REQUESTED` | Controller | `closed` 中明確要求重審，且有最近完整草稿 |
| `RESET` | UI／CLI | 使用者明確重開題目 |

學生說「我懂了」、要求系統「請我交稿」、Tutor 候選稿自行要求交稿，都不是 phase 事件。

## 8. 唯一合法轉移表

| current phase | event | next phase | 同步動作 |
| --- | --- | --- | --- |
| `guide` | `STUCK_LIMIT_REACHED` | `walkthrough` | 初始化 `walk_idx=0`，清空 `stuck_count` |
| `guide` | `READINESS_PASSED` | `review` | `review_status=awaiting_submission`，輸出固定交稿模板 |
| `guide` | `FULL_PROOF_SUBMITTED` | `review` | 保存全文並開始完整審閱 |
| `walkthrough` | `WALKTHROUGH_COMPLETED` | `review` | `review_status=awaiting_submission`，輸出固定交稿模板 |
| `review` | `FULL_PROOF_SUBMITTED` | `review` | 依 status 開始初審或乾淨全文重審 |
| `review` | `REVIEW_PASSED` | `closed` | 設定確定性結案結果 |
| `closed` | `REVIEW_REOPEN_REQUESTED` | `review` | 對最近完整草稿重新審閱 |
| 任意 | `RESET` | `guide` | 清除本題工作流狀態 |

表中沒有列出的轉移一律拒絕，phase 保持不變。

### 明確禁止的轉移

- `walkthrough → review`：不能由學生貼全文、按提交或索取 Tutor 代寫觸發；只能由
  `WALKTHROUGH_COMPLETED` 觸發。
- 任意 phase → `closed`：不能由學生說「得證」「我懂了」或 Tutor 自行稱讚觸發；只能由
  `REVIEW_PASSED` 觸發。
- `guide → review(awaiting_submission)`：不能由學生要求系統請自己交稿觸發；只能由
  `READINESS_PASSED` 或 walkthrough 完成觸發。
- `review → walkthrough`：審閱中卡住不啟動 walkthrough。
- `closed → guide/walkthrough`：一般反思、致謝或延伸問題不重開教學流程。

## 9. 單一轉移入口

目前 phase 會由 router、walkthrough、review workflow 與 Tutor 回覆後處理等多處直接改寫。
建議所有修改集中到一個小函式，仍放在現有 `phase_router.py`，不新增大型模組：

```python
PHASES = {"guide", "walkthrough", "review", "closed"}

def apply_phase_event(state: dict, event: str) -> str:
    """只依 current phase、合法事件與必要 state facts 更新 phase。"""
```

其他程式只能呼叫 `apply_phase_event()`，不得直接寫：

```python
state["phase"] = ...
```

每次轉移至少記錄：

```text
previous_phase
event
event_source
next_phase
accepted
reject_reason
state_before
state_after
```

這能直接定位「分類錯」與「轉移規則錯」，不必只從 Tutor 文字猜測。

## 10. 四個 phase 的詳細行為

### 10.1 `guide`

保留目前一般引導與 Level 0～2。

- `show_attempt`：仍使用目前 `rectify` 的提示內容，但 phase 保持 `guide`。
- `clarification`：先回答學生最新的具體問題，phase 保持 `guide`。
- `demand_full_answer`：固定拒絕 Tutor 代寫，再回到目前聚焦問題；phase 保持 `guide`。
- `stuck`：依現行政策更新 `stuck_count`。
- `understood_whole_proof`：只記錄學生語意，不切 phase。
- 有新的實質數學進度：更新現有 `proof_progress_revision`，必要時呼叫 readiness。

Level 不是 phase；Level 只決定 `guide` 內提示深度。

### 10.2 `walkthrough`

保留目前確定性步驟模板、語言鎖與 `walk_idx`。

- walkthrough 是硬鎖。
- 學生索取完整證明：拒絕，但不消耗或跳過步驟。
- 學生貼整份證明或按全文提交：只判目前確認問題，不進全文審閱。
- 每步數學判定仍由 Thinking 負責；參考答案只供參考，不做字串裁決。
- Thinking 技術性不可用時留在當步，不把 unavailable 當成學生錯誤。
- 所有步驟完成後，由 Controller 產生 `WALKTHROUGH_COMPLETED`。

### 10.3 `review`

沿用現有 review queue，不重做審閱架構。`review_status` 建議限定為：

```text
awaiting_submission
checking
correcting
awaiting_clean
rechecking
unavailable
```

- `awaiting_submission`：等待學生自己的完整證明。
- 收到真正全文後開始 `checking`。
- 有 issue 時進 `correcting`，一次處理一項。
- issues 修完後要求乾淨全文，進 `awaiting_clean`。
- 全文審閱通過才產生 `REVIEW_PASSED`。
- 學生在 review 中要求 Tutor 代寫：固定拒絕，status 與 issue index 不變。
- readiness 不在 review 中重跑。

### 10.4 `closed`

- 一般致謝、心得、反思：確定性收尾，phase 不變。
- 有關已完成證明的具體小問題：只回答該問題，不啟動新教學流程。
- 明確要求重審最近證明：有最近全文才產生 `REVIEW_REOPEN_REQUESTED`。
- 沒有最近全文或 Thinking 不確定：保持 `closed`。

## 11. readiness 的責任邊界

readiness 只負責判斷：

> 學生是否已在累積對話中親自提出或正確確認完整證明不可缺少的環節？

建議保留 `true/false`，不要讓 readiness 輸出 phase。

- `true`：Controller 產生 `READINESS_PASSED`。
- `false`：留在 `guide`，依原 Level 繼續。
- unavailable／格式錯誤／低信心：phase 不變。
- `missing_core_step` 只作診斷參考；本次不拿它生成新問題。
- readiness 必須看累積對話，不能因「目前這一則只是局部步驟」就阻止重新判斷整體進度。
- 學生自己要求進入交稿不會觸發或替代 readiness。

## 12. Thinking 模型的使用方式

為保持通用且不依賴固定措辭，Thinking 可繼續判斷語意，但權限要縮小：

| Thinking 工作 | 可以影響什麼 | 不可以影響什麼 |
| --- | --- | --- |
| turn intent／role | 當輪 action、`stuck_count` 輸入 | 直接寫 phase |
| walkthrough verdict | 當步是否前進 | 跳出 walkthrough |
| readiness | 是否產生 `READINESS_PASSED` | 接受學生自我宣告為完成 |
| review judge | issues 與 `REVIEW_PASSED` | 未經全文審閱直接 closed |
| closed recheck intent | 是否提出重審事件 | 沒有最近全文時憑空重審 |

### Thinking 失敗時的統一規則

```text
phase 不變
```

然後依目前 phase 使用安全回覆：

- `guide`：沿用目前 Level 與聚焦問題。
- `walkthrough`：留在目前步驟。
- `review`：保留 status／issue，不假裝通過。
- `closed`：保持結案，不擅自重開。

不應因 Thinking 一次失敗而猜測另一個 phase，也不需要無限重試。

## 13. Tutor 說話模型的權限

Tutor 說話模型只能生成目前 phase 允許的文字，不能建立 phase 事件。

- 交稿提示使用現有固定模板，由 Controller 輸出。
- review 通過與 closed 收尾使用固定模板。
- 拒絕 Tutor 代寫可沿用現有固定拒絕流程。
- 普通 `guide` 候選稿即使自行說「請交完整證明」，也不能改變 phase 或
  `review_status`；只有 readiness 通過後的 Controller 事件有效。

若保留 Tutor 候選稿的語意 action 守門，它只能是輸出防護，不得成為 phase router。
分類不可用時應保持 phase，且回到「目前聚焦問題」；不要讓全系統每輪都退回同一組
題型無關的通用問句。

## 14. 同學模式不再使用 phase

成功版的同學模式由 `grounding=unverified` 或缺少可靠參考解決定，這是執行模式，不是
教學工作流 phase。

建議：

```text
mode = tutor | peer
phase = guide | walkthrough | review | closed
```

peer mode 固定停留在 `guide`；學生質疑上一個想法時，只設定
`turn_action=peer_reflect`，不切換 phase。原 `PEER_SYSTEM` 與反思指示可原樣保留。

## 15. 狀態的單一真實來源

實作完成後，以下關係應由 phase／review status 推導：

| 舊旗標 | 建議來源 |
| --- | --- |
| `walk_active` | `phase == "walkthrough"` |
| `done_closed` | `phase == "closed"` |
| `review_active` | `phase == "review" and review_status == "correcting"` |
| `awaiting_clean_proof` | `phase == "review" and review_status == "awaiting_clean"` |
| `writeup_asked` | phase 已進 `review`，且曾由 readiness／walk completion 進入 `awaiting_submission` |

為降低一次修改風險，第一版可暫時保留這些舊欄位作相容鏡像，但：

1. 邏輯判斷只能讀 `phase` 與 `review_status`。
2. 舊旗標只能由 `apply_phase_event()` 同步更新。
3. Tier 0 穩定後再移除鏡像欄位。

不可讓 phase 與舊旗標同時成為權威來源。

## 16. 舊快照載入規則

舊 session 快照可在 `load_state()` 一次性正規化：

```text
done_closed=True                         → closed
review_active=True / awaiting_clean=True → review
walk_active=True                         → walkthrough
phase=writeup_request                    → review + awaiting_submission
phase=review                             → review + 保留 review_status
phase=walkthrough                        → walkthrough
phase=closed                             → closed
phase=None/rectify/refuse_leak/peer_reflect → guide
```

正規化後只保存四種新 phase；不要在每一輪繼續兼容舊 phase 名稱。

## 17. 預計修改範圍（實作階段）

### 必須修改

| 檔案 | 最小修改內容 |
| --- | --- |
| `dataset/phase_router.py` | phase enum 改成四種；保留語意分類；新增唯一事件轉移函式 |
| `dataset/tutor_driver.py` | 將 `rectify/refuse_leak/peer_reflect` 改為當輪 action；writeup 併入 review status；禁止其他位置直接寫 phase |
| `dataset/test_phase_routing.py` | 改測四 phase、合法事件矩陣、非法轉移與 Thinking unavailable 不變性 |
| `dataset/test_driver_unit.py` | 更新 phase 名稱與整段流程斷言 |
| `dataset/test_review_workflow.py` | 更新 `awaiting_submission → checking → correcting → awaiting_clean → closed` 流程 |
| `dataset/regression_suite.py` | 保留並執行新的 phase routing 測試 |
| `train.ipynb`、`test.ipynb` | 同步 phase 名稱、報告欄位與 Tier 0 測試入口 |

### 原則上不修改

```text
reference_builder.py
segmenter.py
dataset 內容
模型權重
一般教學提示內容
walkthrough 步驟資料
review_backstop.py 的數學審閱核心
```

若實作時發現上述檔案必須大改，應先停止並重新評估，因為那已偏離「差異最小」。

## 18. Tier 0 必測流程

### A. phase 集合與轉移入口

1. 新 session 一律從 `guide` 開始。
2. 快照與報告中的 phase 只允許四種值。
3. 所有 phase 修改都經過 `apply_phase_event()`。
4. 未列入合法矩陣的事件不改 phase，並留下 reject 診斷。
5. Thinking unavailable、低信心、格式錯誤時 phase 不變。

### B. `guide`

1. 一般回答、數學嘗試、答錯、具體釐清都留在 `guide`。
2. 索取 Tutor 完整答案只觸發當輪拒絕，仍留在 `guide`。
3. 未知同義改寫可由 Thinking 判斷 intent，但不直接輸出 phase。
4. 學生說整體理解或要求系統請自己交稿，不切 review。
5. 連續卡住達門檻才由 Controller 切 `walkthrough`。
6. readiness false／unavailable 留在 `guide`。
7. readiness true 才切 `review + awaiting_submission`。
8. walkthrough 外真正完整交稿可直接切 `review + checking`。

### C. `walkthrough`

1. 索取 Tutor 代寫不跳出、不消耗步驟。
2. 貼完整證明不跳出，只判當前確認問題。
3. 全文提交按鈕不跳出。
4. Thinking 不可用時留在當步。
5. 中間步驟完成仍為 `walkthrough`。
6. 最後步驟完成才切 `review + awaiting_submission`。

### D. `review`

1. `awaiting_submission` 中收到非全文，保持 status。
2. 真正全文使 status 進入 `checking`。
3. 有 issue 時留在 `review` 並進 `correcting`。
4. 局部訂正不改 phase，也不消耗錯誤的 issue。
5. 要求 Tutor 代寫不改 status／issue index。
6. 修正完成後進 `awaiting_clean`，仍為 `review`。
7. 乾淨全文審閱通過才切 `closed`。
8. 審閱服務 unavailable 不可切 `closed`。

### E. `closed`

1. 一般反思與致謝保持 `closed`。
2. 歷史性的「以前卡住」不重啟 Level 或 walkthrough。
3. 沒有最近全文時，即使要求重審也不憑空進 review。
4. 有最近全文且明確要求重審，才切 `review + rechecking`。
5. 重審未通過時保持 review；重審再次通過才回 closed。

### F. 舊快照相容

1. 七種舊 phase／`None` 全部依映射正規化。
2. 矛盾舊狀態使用固定優先序正規化，不交給 Thinking 猜測。
3. dump 後不再出現 `rectify/refuse_leak/peer_reflect/writeup_request`。

## 19. 真實 Thinking 測試原則

不需要把每一句可能措辭列成關鍵詞測試。應按語意家族測試，每個家族使用少量不同改寫：

1. 數學嘗試與答錯。
2. 無問號的具體釐清。
3. 索取 Tutor 完整代寫。
4. 要求系統請學生自己交稿。
5. 整體理解宣告但沒有數學內容。
6. 真正完整證明與長篇局部回答。
7. closed 後的一般反思與明確重審。

每輪同時核對：

```text
intent／turn role
event
previous_phase
next_phase
review_status
Tutor 最終文字
```

只看 Tutor 文字不足以判斷 phase 是否正確。

## 20. 驗收標準

1. phase 永遠只屬於 `{guide, walkthrough, review, closed}`。
2. 所有非法轉移測試 100% 通過。
3. walkthrough 硬鎖與 review queue 既有測試不得退步。
4. 學生與 Tutor 的普通文字不能直接改 phase。
5. Thinking unavailable 不造成 phase 漂移。
6. Tier 0 全部通過，且既有基準分數不下降。
7. 真實 Thinking 測試中，狀態錯誤與提示品質問題分開記錄。
8. `train.ipynb`、`test.ipynb` 與 CLI 使用相同 phase enum 與測試入口。

## 21. 建議實作順序

1. 先備份成功版並記錄目前 Tier 0 基準。
2. 在 `phase_router.py` 加入四 phase enum、事件 enum 與合法轉移表，先寫純單元測試。
3. 加入舊快照正規化，但尚未接管正式 Driver。
4. 將 `tutor_driver.py` 的直接 phase 寫入逐一改成事件呼叫。
5. 將 `rectify/refuse_leak/peer_reflect` 改成當輪 action。
6. 將 `writeup_request` 映射為 `review_status=awaiting_submission`。
7. 更新 phase report、Tier 0 與回歸測試。
8. 同步 `train.ipynb`、`test.ipynb`。
9. 最後才執行真實 Thinking 流程測試；不先調整提示品質。

每一步都應保持可回退，不要一次重寫整個 `TutorDriver`。

## 22. 最終建議

採用四個持久 phase：

```text
guide / walkthrough / review / closed
```

保留現有 `phase_router.py`、Level、walkthrough、readiness 與 review queue；只把
`rectify`、`refuse_leak`、`peer_reflect` 移成當輪 action，並把 `writeup_request`
併入 `review_status=awaiting_submission`。

這個方案的核心不是讓 Thinking 更努力猜 phase，而是讓 phase 只在少數可驗證事件發生時
切換。如此才能同時達到「保留 phase」、「差異最小」與「切換精準」。
