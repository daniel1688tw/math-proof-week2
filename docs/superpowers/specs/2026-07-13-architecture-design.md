# 架構設計文檔與 README.md 更新設計規格書（2026-07-13）

## 一、 背景與目標
為使專案的其他開發者能夠快速理解 Socratic Calculus Proof Tutor 的框架結構與各個檔案的定位，我們需要建立一個清晰的架構設計文檔 `ARCHITECTURE.md`，並更新專案根目錄的 `README.md`，使其更具導讀性與可維護性。

---

## 二、 ARCHITECTURE.md 的結構設計

預計在專案根目錄建立 `ARCHITECTURE.md`，內容分為以下主要部分：

### 1. 核心教學理念與專案定位
- **蘇格拉底教學法（Socratic Method）**：著重於「引導」而非「灌輸」，透過逐步提問讓學生自己發現證明的關鍵步驟。
- **Grounded SFT**：將標準的 LaTeX 參考解答注入 `system` 提示詞中（學生看不到），讓模型有了「標準答案」的錨定，避免引導時產生數學幻覺或偏離解題路徑。

### 2. 雙層架構（Two-Layer Architecture）
說明系統如何劃分為「確定性決策層」與「LLM 語氣微調層」：
- **TutorDriver (確定性決策層)**：
  - **狀態偵測（Phase Detection）**：基於正則表達式，偵測學生回覆的意圖：
    - `stuck`：卡住偵測（中文 60 字元、英文 120 字元內且包含卡住特徵詞）。
    - `refuse_leak`：防逼問答案偵測（拒絕洩漏參考解答，並重新將主導權交還學生）。
    - `rectify`：邏輯糾錯偵測（學生提出嘗試時，引導其發現漏洞）。
    - `writeup_request`：要求寫完整證明。
    - `review`：審閱學生提交的證明草稿。
  - **分級提示（Hint Laddering）**：
    - `Level 0`（預設）：聚焦提問，禁提定理。
    - `Level 1`（卡住 1 次）：拆解子問題，禁提定理。
    - `Level 2`（卡住 2 次）：注入 `hint_ladders.json` 中的定理或核心想法名稱，並讓學生接手推導。
  - **安全性防護機制（Guards & Fallbacks）**：
    - **單問句截斷**：多問號時截斷至第一個問號，防止複合問句打亂學生節奏。
    - **洩漏 n-gram 檢查**：當提示等級小於 2 時，若回覆與參考解有連續 15 字元重合，將加入警示重新生成。
    - **重複回問保底**：若回覆與前 3 輪重複，將加入警示重新生成。
- **Fine-tuned LLM (大模型微調層 - Qwen3-4B-Instruct)**：
  - **微調技術**：QLoRA 4-bit 量化載入，僅訓練 33M 的 LoRA 參數。
  - **Assistant-only masking**：在 tokenize 後，只對 assistant 的回合計算 loss，其他部分遮蔽（設為 -100），使模型專注於學習引導語氣而非複誦學生。
  - **左截斷滑動窗口（Left-truncated window）**：對超長對話進行窗口截斷，保留多輪對話後半部的上下文，避免直接捨棄後段。

### 3. 雙語部署設計
- **動態語言偵測**：`TutorDriver` 在 `start()` 或首輪 `step()` 藉由 CJK 字元占比判定學生使用語言（< 10% 判為英文）。
- **資源動態載入**：偵測到英文後，自動載入 `BASE_SYSTEM_EN`、`LEVEL_INSTRUCTIONS_EN` 以及 `hint_ladders_en.json` 的內容。

### 4. 檔案目錄對照表 (File Registry)
為開發者詳細說明每個檔案與目錄的作用：
- `dataset/`
  - `src/` 與 `src_en/`：手寫中英文問題與多輪對話代碼。
  - `build.py`：建置資料集腳本。
  - `validate.py`：驗證資料集格式與正確性。
  - `tutor_driver.py`：確定性決策層主程式。
  - `interactive_turn.py`：互動測試介面。
  - `test_driver_unit.py` / `test_driver_integration.py` / `test_driver_phase.py`：各層級測試腳本。
  - `eval_*.py`：三情境完整評估工具。
- `learn_path/socratic_tutor/`
  - `train_qlora.py`：模型微調主控程式.
  - `common.py`：路徑與基準模型名稱共用設定。
- `docs/`：開發 specs 與設計文檔。

---

## 三、 README.md 的更新設計

1. **架構章節更新**：
   - 簡化 README 中關於 `TutorDriver` 的細部參數設定，移至 `ARCHITECTURE.md`。
   - 保留核心架構圖與大原則說明。
2. **新增導讀與連結**：
   - 在「架構」章節最上方，明確提供 `ARCHITECTURE.md` 的 clickable markdown 連結，引導其他開發者深入閱讀。
3. **雙語說明同步**：
   - 在 README 的簡介與快速開始部分，提及中英文雙語微調成果與動態語言偵測。

---

## 四、 驗證與檢查
- 檢查所有產生的 markdown 連結在 Windows 本地環境下是否完全正確且可點擊（即符合 `file:///d:/UserData/claude_project/...` 格式）。
- 確保文字流暢，排版美觀，並使用標準繁體中文。
