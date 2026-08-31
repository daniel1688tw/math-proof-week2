# Level／Phase Code Review（2026-08-31）

## 結論

目前四 phase 狀態機的主幹是對齊的：運行時持久 phase 只有 `guide / walkthrough / review / closed`，Thinking 只分類當輪語意，真正的 phase 只能由 Controller 接受合法事件後改變。`stuck_count` 的主路徑也符合 `0 → Level 0`、第一次卡住 `1 → Level 1`、第二次卡住 `2 → Level 2`、第三次卡住進 `walkthrough`；opener 不計卡住，實質新數學內容會中斷連續卡住。

本次無 GPU 驗證全部通過：

- `python dataset/test_phase_routing.py`
- `python dataset/test_driver_unit.py`
- `python dataset/test_review_workflow.py`

但「測試全綠」不等於 level／phase 契約已完全封閉。本次找到 1 項高優先、2 項中優先實作缺口，以及 1 項必須同步說清楚的可用性取捨。

## 現行權威契約

| 控制線 | 值 | 職責 |
| --- | --- | --- |
| `phase` | `guide / walkthrough / review / closed` | 持久工作流；只能由合法 event 改變 |
| `turn_action` | `normal_guide / respond_attempt / answer_clarification / refuse_tutor_write / peer_reflect / post_completion_reply / review_local_revision / walkthrough_answer` | 當輪任務；不能自行改 phase |
| `hint_level` | `0 / 1 / 2`，目前由 `min(stuck_count, 2)` 取得 | 只控制 `guide + normal_guide` 的提示深度 |

優先序是「持久 phase 鎖定工作流，再由 action 決定當輪任務，最後才套用 level」。`review`、`closed`、`walkthrough` 不應被卡住計數或一般 level prompt 改寫。

合法 phase event：

| 當前 phase | event | 下一狀態 |
| --- | --- | --- |
| `guide` | `STUCK_LIMIT_REACHED` | `walkthrough` |
| `guide` | `READINESS_PASSED` | `review/awaiting_submission` |
| `walkthrough` | `WALKTHROUGH_COMPLETED` | `review/awaiting_submission` |
| `review` | `FULL_PROOF_SUBMITTED` | `review/checking` 或 `review/rechecking` |
| `review` | `REVIEW_PASSED` | `closed` |
| `closed` | `REVIEW_REOPEN_REQUESTED` | `review/rechecking` |
| 任意 | `RESET` | `guide` |

## Findings

### P1：Level 2 提示梯在組 prompt 時就被消耗

位置：`dataset/tutor_driver.py::_get_ladder_hint()`、`_system()`、`_regen()`。

`_get_ladder_hint(2)` 會立即更新 `state["ladder_idx"]`。初稿、內容守衛重生成及 guide semantic review 重生成都會再次呼叫 `_system(level)`，因此一次學生回合可能消耗多條提示，而且重寫稿收到的已不是初稿的同一個 scaffold。

這在現有資料可重現：`M4`、`ADV1` 的中英 `hint_ladders*.json` 都有 3 條。對 3 條梯連續呼叫兩次 `_system(2)`，第一次注入第 2 條，第二次已改注入第 3 條。這違反：

- 同一回合只處理一個 active gap。
- Level 2 只給一個 micro-scaffold。
- 提示只有真正送到學生面前才可視為已消耗。

建議修改：把本輪選定的 hint 存成 turn-local cache，所有重生成重用同一條；只有最終候選落地後才更新索引。若產品其實只需要「L1 一條、L2 一條」，更簡單的做法是移除遞增索引，固定以 level 映射到對應提示。修正前先加一條 3-item ladder 測試，斷言初稿與重生成的 system 使用同一條提示。

### P2：Level 1 的文字契約互相矛盾

位置：`LEVEL_INSTRUCTIONS[1]`、`_get_ladder_hint(1)`、`_guide_action_forbids_new_idea()`、`hint_ladders*.json`。

Level 1 prompt 明寫「仍然不要直接點名定理名稱」，但現有中文與英文第一階提示至少各 9 題直接含均值定理、比較判別法、比值判別法、二項式定理、單調有界定理或 Cauchy 均值定理。實際組出的同一份 system 會同時出現「關鍵是均值定理」與「不要直接點名定理名稱」。

此外，最新未提交修改允許 Level 1 在 semantic review 明確判定 `level_policy_pass=true` 時引入同一缺口的子問題方向。這個方向合理，但目前沒有把「可指出子目標」與「不可直接命名關鍵定理／完成步驟」切成單一、可測試的規則。

建議先做產品決策並統一四處：

1. 若要維持 Level 1 不點名定理，builder／validator 必須禁止 `ladder[0]` 含定理名稱或完成式，現有 9 組提示需重寫。
2. 若允許 Level 1 點出一個方向，則更新 `LEVEL_INSTRUCTIONS` 與文件，明定仍不得完成任何中間步驟；Level 2 的差異必須是「直接給一個可執行 micro-scaffold」。

在決策前，不建議只調 reviewer prompt，因為輸入本身已互相矛盾。

### P2：closed 重審的「最近全文」來源不一致

位置：`phase_router.apply_phase_event()`、`TutorDriver._student_state_context()`、`TutorDriver._review_workflow_transition()`。

event 層接受 `current_proof_draft` 或 `review_last_full_proof` 任一存在即可執行 `REVIEW_REOPEN_REQUESTED`；但 router 的 `has_recent_proof` 與 closed workflow 只檢查 `current_proof_draft`。舊快照若只保留 `review_last_full_proof`，event 本身可合法重開，實際路由卻永遠不會發出該 event。

建議讓三層共用同一個 `has_recent_proof()` 判準，或至少都檢查這兩個欄位。測試需建立「只有 `review_last_full_proof`」的 closed 快照，確認明確漏審質疑可重開。

### P3：後盾不可用時目前採 fail-closed，不是所有路徑都會「自動降級繼續」

這是安全取捨，不一定是程式缺陷：

- walkthrough answer judge unavailable：停留原步、不揭答、不前進。
- full review judge unavailable：停在 `review/unavailable`，不得 `closed`。
- guide semantic review 連續不可用：輸出不含題型內容的安全 fallback。

因此「Ollama 不在線自動降級回原行為」已不準確。現況是「不崩潰、保留狀態、拒絕假裝判對；需要可靠審閱的 phase 會等待服務恢復」。若產品不接受 walkthrough 無限等待，應另設明確的人工重試／退出政策，而不是把服務失敗當成學生答錯或已完成。

## 已確認對齊的部分

- opener 明說不會仍從 Level 0 開始，`stuck_count=0`。
- 第一次、第二次、第三次連續卡住依序得到 Level 1、Level 2、`walkthrough`。
- `respond_attempt`、`answer_clarification`、`refuse_tutor_write` 是 action，不是 phase。
- guide 中的完整證明外形不會直接產生 `FULL_PROOF_SUBMITTED`；必須先由 readiness 進 `review/awaiting_submission`。
- Tutor 候選文字不能自行產生 `READINESS_PASSED` 或 `REVIEW_PASSED`。
- walkthrough 是持久硬鎖；只有完成最後一步才進 review。
- review issue queue、局部訂正、乾淨全文複核與 closed reopen 的 event 骨架正確。
- phase history／event history／dump-load 的核心欄位已有測試。

## 文件更新範圍

本輪把仍具維護效力的架構、操作與待辦文件同步到上述契約。歷史評估報告、逐字對話、舊 superpowers 計畫／規格、技能說明與第三方參考 repo 不改寫；它們是當時版本的證據，會在相關入口標明「歷史快照」。

## 建議實作順序

1. 先修 Level 2 hint 的 turn-local 消耗時機，這是可重現的狀態錯誤。
2. 決定 Level 1 是否可命名定理，再一次同步 prompt、hint 資料、validator 與測試。
3. 統一 closed reopen 的最近全文判準。
4. 增加服務不可用的產品提示或人工重試入口；維持 fail-closed 數學安全。
