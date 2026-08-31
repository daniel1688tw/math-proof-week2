# Level／Phase Code Review 與文件同步計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 驗證目前 TutorDriver 的提示等級、持久階段與當輪動作是否符合專案設計，提出有證據的修改建議，並同步所有仍具維護效力的 Markdown 文件。

**Architecture:** 以 `phase_router.py` 作為 phase／action 的唯一分類與事件轉移入口，以 `tutor_driver.py` 作為 level 選擇、內容守衛與工作流執行層。審查會把 `phase`、`turn_action`、`hint_level` 視為三條正交控制線，逐一核對事件表、路由優先序、失敗降級與狀態持久化。

**Tech Stack:** Python 3.11、PowerShell、專案自有無 GPU 單元測試、Markdown。

**Spec:** `LEVEL_優化完整方案.md`、`精簡_PHASE_架構修正提案.md`、`phase_routing_solution.md`

## Global Constraints

- 與專案相關的說明、註解與回覆一律使用繁體中文。
- 不覆寫工作樹中既有的 `dataset/tutor_driver.py` 與 `dataset/test_driver_unit.py` 未提交修改。
- 歷史評估報告、逐字生成紀錄、既有 superpowers 計畫／規格與技能說明保留原貌，不改寫實驗證據。
- 只有 Controller 接受的 phase event 能改變持久 phase；模型候選文字沒有 phase 轉移權。
- `phase > turn_action > hint_level`；hint level 只控制 `guide + normal_guide` 的提示深度。

---

### Task 1: 建立狀態機對照表

**Files:**
- Review: `dataset/phase_router.py`
- Review: `dataset/tutor_driver.py`
- Review: `LEVEL_優化完整方案.md`
- Review: `精簡_PHASE_架構修正提案.md`

**Interfaces:**
- Consumes: `route_student_state(student_text, context)`、`update_stuck_count(...)`、`apply_phase_event(...)`
- Produces: phase／action／level 的期望值與實際值對照表，以及可定位到函式與行號的 findings。

- [ ] **Step 1: 列出四個持久 phase 與所有合法事件轉移**
- [ ] **Step 2: 列出 turn action 對 phase gate 的優先序**
- [ ] **Step 3: 核對 opener、一般 step、walkthrough、review、closed 的 stuck 計數語意**
- [ ] **Step 4: 核對模型候選、readiness judge 與 review judge 的 phase 權限邊界**

### Task 2: 驗證測試覆蓋與現況

**Files:**
- Test: `dataset/test_phase_routing.py`
- Test: `dataset/test_driver_unit.py`
- Test: `dataset/test_review_workflow.py`
- Test: `dataset/test_driver_phase.py`

**Interfaces:**
- Consumes: Task 1 的狀態機對照表。
- Produces: 每個關鍵 transition／failure mode 的測試證據與缺口清單。

- [ ] **Step 1: 執行 phase routing、driver unit、review workflow 無 GPU 測試**
- [ ] **Step 2: 對失敗案例做最小重現並定位根因**
- [ ] **Step 3: 搜尋未被測試鎖定的 event rejection、unavailable 與 state restore 路徑**
- [ ] **Step 4: 依嚴重度整理 findings；沒有證據的推測不得列為缺陷**

### Task 3: 同步維護中文件

**Files:**
- Create: `docs/code-review-level-phase-2026-08-31.md`
- Modify: 所有目前仍具維護效力、且描述 level／phase 現況的根目錄與 `docs/notion/` Markdown。
- Preserve: `dataset/eval_out_*/`、`dataset/regression_scores/`、`docs/superpowers/specs/`、既有 `docs/superpowers/plans/`、技能說明與第三方參考 repo。

**Interfaces:**
- Consumes: Task 1 findings 與 Task 2 測試結果。
- Produces: 單一權威 code review 報告、同步後的架構／操作／待辦文件，以及明確的歷史文件標示。

- [ ] **Step 1: 寫入結論、狀態機表、findings、建議與測試證據**
- [ ] **Step 2: 修正維護中文件中的舊 level／phase 敘述**
- [ ] **Step 3: 對仍有參考價值但不代表現況的提案加上狀態標示**
- [ ] **Step 4: 搜尋互相矛盾的關鍵句並逐項消除**

### Task 4: 最終驗證

**Files:**
- Verify: 所有本輪修改的 Markdown。
- Verify: `dataset/test_phase_routing.py`、`dataset/test_driver_unit.py`、`dataset/test_review_workflow.py`

**Interfaces:**
- Consumes: Task 3 文件更新。
- Produces: 可重現的測試結果、乾淨的 Markdown 差異與保留項目清單。

- [ ] **Step 1: 重新執行所有無 GPU 相關測試**
- [ ] **Step 2: 檢查 Markdown 連結、UTF-8 與關鍵術語一致性**
- [ ] **Step 3: 檢查 git diff，確認未覆寫使用者程式修改或歷史證據**
- [ ] **Step 4: 交付按嚴重度排序的 findings、已更新文件與仍待決策事項**
