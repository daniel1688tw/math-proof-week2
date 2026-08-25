# 撰寫架構文件與更新 README.md 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 撰寫詳細的 `ARCHITECTURE.md` 開發者說明文檔，並更新根目錄的 `README.md`，以清晰引導開發者理解專案架構。

**Architecture:** 創建根目錄 `ARCHITECTURE.md` 並更新 `README.md` 中對應的導讀段落與連結。

**Tech Stack:** Markdown / Git / Python (用於驗證測試)

## Global Constraints
- 所有文件回覆與說明文字必須使用繁體中文（Traditional Chinese）。
- Markdown 檔案中的檔案連結必須為 clickable link（在 Windows 下為 `file:///d:/UserData/claude_project/霓資料/math-proof-week2/` 格式的絕對路徑，且不加反引號 ` `）。

---

### Task 1: 撰寫 ARCHITECTURE.md

**Files:**
- Create: `d:/UserData/claude_project/霓資料/math-proof-week2/ARCHITECTURE.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-07-13-architecture-design.md` 規定的架構設計。

- [ ] **Step 1: 建立並撰寫 ARCHITECTURE.md 的前段（理念與決策層）**
  - 建立檔案 `d:/UserData/claude_project/霓資料/math-proof-week2/ARCHITECTURE.md`。
  - 寫入專案概述、蘇格拉底教學法核心理念、Grounded SFT。
  - 詳細說明確定性決策層 `TutorDriver` 的狀態機（stuck、refuse_leak、rectify、writeup_request、review）以及分級提示（L0/L1/L2）的運作邏輯。
  - 詳細說明防護機制（單問句截斷、洩漏比對、重複回問保底）。

- [ ] **Step 2: 撰寫 ARCHITECTURE.md 的後段（微調層、雙語與檔案對照）**
  - 寫入 QLoRA 微調層（4-bit, assistant-only masking, left-truncated window）。
  - 寫入雙語部署設計（語言偵測、資源載入）。
  - 寫入檔案目錄說明表（File Registry），列明每個 python 程式與 json 配置檔的職責。

- [ ] **Step 3: 自我檢查連結與排版**
  - 檢查所有在 `ARCHITECTURE.md` 中引用的檔案連結是否為正確的 Windows 絕對路徑 `file:///d:/UserData/...` 格式，且不包含 markdown 反引號。

- [ ] **Step 4: Git 提交 Task 1 成果**
  - 執行命令：`git add ARCHITECTURE.md`
  - 執行命令：`git commit -m "docs: add ARCHITECTURE.md explaining codebase architecture"`

---

### Task 2: 更新 README.md

**Files:**
- Modify: `d:/UserData/claude_project/霓資料/math-proof-week2/README.md:13-27` (修改架構段落)

**Interfaces:**
- Consumes: `ARCHITECTURE.md` 的導讀連結。

- [ ] **Step 1: 修改 README.md 的架構章節**
  - 編輯 `d:/UserData/claude_project/霓資料/math-proof-week2/README.md`。
  - 在第 13 行的 `## 架構：模型只管數學與語氣，決策交給程式碼` 段落上方或開頭，加入 `ARCHITECTURE.md` 的 clickable 連結與導讀，如「對於專案的詳細雙層架構、狀態機控制流、QLoRA 微調細節與檔案對照表，請參閱 [ARCHITECTURE.md](file:///d:/UserData/claude_project/霓資料/math-proof-week2/ARCHITECTURE.md)。」
  - 簡化 README 中原本對於 `TutorDriver` 與 micro-step 等微觀設計的過度描述，使其更為乾淨。
  - 在簡介中更新該專案支持中英雙語的說明。

- [ ] **Step 2: 自我檢查 README.md 連結**
  - 檢查 README.md 中新增的連結是否正確。

- [ ] **Step 3: Git 提交 Task 2 成果**
  - 執行命令：`git add README.md`
  - 執行命令：`git commit -m "docs: update README.md with architecture link and bilingual info"`

---

### Task 3: 驗證與測試

**Files:**
- Test: `d:/UserData/claude_project/霓資料/math-proof-week2/dataset/validate.py`
- Test: `d:/UserData/claude_project/霓資料/math-proof-week2/dataset/test_dataset.py`
- Test: `d:/UserData/claude_project/霓資料/math-proof-week2/dataset/test_driver_unit.py`

- [ ] **Step 1: 執行資料集格式驗證**
  - 執行命令：`python dataset/validate.py`
  - 預期輸出：無錯誤，順利通過。

- [ ] **Step 2: 執行資料集測試**
  - 執行命令：`python dataset/test_dataset.py`
  - 預期輸出：測試全部 PASS。

- [ ] **Step 3: 執行 driver 單元測試**
  - 執行命令：`python dataset/test_driver_unit.py`
  - 預期輸出：25 項斷言（或當前測試案例）全部 PASS。

- [ ] **Step 4: 建立 Walkthrough**
  - 建立 walkthrough artifact 總結變更。
