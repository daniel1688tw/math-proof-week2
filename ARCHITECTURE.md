# 架構設計文件 (ARCHITECTURE.md)

本文件詳細記錄了「高等數學證明引導助教系統」的系統架構、核心設計原理、雙層控制機制、雙語部署邏輯以及專案檔案目錄對照表。

---

## 1. 專案核心定位

本專案旨在將 **Qwen3-4B-Instruct** 微調成一個專業的大學微積分／數學分析證明引導助教（Socratic Math Tutor）。其核心定位為：**結合確定性決策層與 LLM 語氣微調層的高等數學證明引導助教系統**。

在高等數學證明的教學中，傳統 LLM 常有以下痛點：
1. **答案洩漏（Answer Leaking）**：容易在學生稍微施壓或逼問時，直接給出完整證明或關鍵推導步驟，失去引導教學的意義。
2. **提示深度的模糊性**：難以精確拿捏何時該給學生多少提示（例如：學生連續卡住幾次後才給定理名稱）。
3. **複合提問混淆**：LLM 傾向在一輪回覆中問多個問題，導致學生無所適從。

本系統採用「**離散決策交給程式碼、提示內容交給預寫資源、模型僅負責數學語境與語氣**」的設計哲學。透過雙層架構的有機結合，實現百分之百受控的引導教學行為。

---

## 2. 雙層架構設計

本系統由 **TutorDriver (確定性決策層)** 與 **Fine-tuned LLM (微調層)** 兩層組成。

### 2.1 TutorDriver (確定性決策層)
`TutorDriver` 作為整個對話系統的狀態機與控制中樞，負責有狀態的流程控制與安全防禦。其主要職責如下：

#### A. 對話階段偵測 (Phase Detection)
`TutorDriver` 會在每輪對話開始時，以正則表達式（Regex）對學生的最新回覆進行確定性判定，藉此跳脫模型的盲目慣性，切換至對應的教學階段：
*   **卡住偵測 (`stuck`)**：若學生回覆較短且包含「不知道、不會、卡住、求提示」等語意，則判定為卡住狀態，遞增卡住計數器（`stuck_count`），用於觸發提示升級機制。
*   **拒絕洩漏 (`refuse_leak`)**：若偵測到學生強烈要求「直接給我答案/完整證明」，則強行將系統指令切換為 refusal 模式，指示模型用一句話溫和拒絕並反問一個聚焦問題。
*   **邏輯糾錯 (`rectify`)**：若學生提交了自己的推導嘗試（如「我覺得...這樣對嗎？」），則進入糾錯模式，指示模型對照參考解，精確指出其邏輯漏洞，但不要代為寫出正確算式。
*   **寫證明要求 (`writeup_request`)**：當學生表示自己已完全理解思路後，觸發此階段，要求學生寫出完整證明草稿。
*   **審閱草稿 (`review`)**：當學生交出完整證明後，對照參考解進行查漏（例如：定理前提未驗證、極限存在性未說明等），挑出最重要的一個漏洞用問題指出。

#### B. 分級提示 (Hint Laddering)
系統根據 `stuck_count` 來動態調整提示的深度，確保提示符合蘇格拉底式的漸進原則：
*   **L0（預設引導）**：只提一個聚焦問題，禁止點名任何定理或技巧名稱，引導學生自己思考方向。
*   **L1（拆解子問題）**：若學生卡住 1 次，將上一個問題拆解成更小、更具體的子問題，仍然不透漏定理名稱。
*   **L2（定理注入）**：若學生連續卡住 2 次，TutorDriver 會從預寫的 [hint_ladders.json](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/hint_ladders.json)（或 [hint_ladders_en.json](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/hint_ladders_en.json)）中提取對應題目的關鍵定理名稱或核心想法注入 System Prompt 中，指示模型第一句必須明確說出該定理/核心想法，第二句提出讓學生接手推導的問題。給予提示後重置計數。

#### C. 推論端防護機制 (Guards)
為了彌補 LLM 在長對話中可能出現的指令退化或失控，`TutorDriver` 實作了三道防護網：
1.  **單問句截斷**：助教生成的回覆若包含多個問號（？/ ?），`TutorDriver` 會自動將回覆截斷至第一個問號為止，以避免複合提問。
2.  **洩漏 n-gram 檢查**：在提示等級低於 L2 時，`TutorDriver` 會將模型生成的回覆與 `reference_proof` 進行正規化（移除空白、LaTeX 特殊符號等），並進行 15-gram 比對。一旦發現重疊，即判定有洩漏嫌疑，追加 System Note 並在 greedy decoding 下變更輸入促使模型重新生成。
3.  **重複回問保底**：比對模型生成的回覆與最近三輪的助教回覆，若發現語義或字元高度重複，則追加提示要求其針對學生最新狀況提問，重新生成回覆。
4.  **writeup_request 保底模板**：當系統進入 `writeup_request` 階段，若模型產生的回覆未包含請學生寫下證明的相關字眼，`TutorDriver` 會直接使用預設的保底回覆覆蓋，確保對話狀態正確移轉。

---

### 2.2 Fine-tuned LLM (微調層)
微調層基於 Qwen3-4B-Instruct，主要目標在於微調模型的**教學語氣**、**抗洩漏的抗壓性**以及**對數學公式的掌握度**。

#### A. QLoRA 4-bit 量化載入
為了能在一般筆記型電腦 GPU（VRAM >= 6GB，如 RTX 4050）上順利進行微調與推論，模型採用：
*   **4-bit NormalFloat (nf4) 量化**載入。
*   開啟雙重量化（Double Quantization）。
*   以 `bfloat16` 作為計算精度。
*   啟用 Gradient Checkpointing 與 Paged AdamW 8bit 優化器，以極大化降低顯存碎片與使用量。
*   微調模組涵蓋 Attention 與 MLP 層的多個投影矩陣：`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`。

#### B. Assistant-only Loss Masking
本專案的微調核心在於「教導模型如何回應」，而非學習學生的輸入。因此在進行 Chat Template 渲染後：
*   僅針對 `messages` 中角色為 `assistant` 的 Token 計算交叉熵損失（Cross-Entropy Loss）。
*   所有 `system` 與 `user` 回合的 Token 在 Label 中一律被覆蓋為 `-100`（Masking），不參與梯度更新。

#### C. 左截斷滑動窗口 (Left-truncated Window)
在處理長對話數據時（限制 `MAX_LEN = 512`）：
*   **傳統做法（右側截斷）**：只保留對話前 512 個 token，會導致長多輪對話的後半段（特別是結尾的「寫證明」與「審閱草稿」階段）被完全砍掉，甚至因為沒有 assistant token 而被丟棄。
*   **左截斷滑動窗口**：本系統設計了 `_fit_window` 機制。若對話超長，它會保留 System Prompt，並「捨棄最舊的輪次，保留包含最新 assistant 回合的後半部對話窗口」，且窗口必定以 `user` 訊息作為開頭。這使模型能學習多輪對話中後半段的高階教學行為。

---

## 3. 雙語部署設計

本系統支援繁體中文（Traditional Chinese）與英文（English）的雙語流暢切換：

1.  **動態語言判定**：
    在 `TutorDriver` 的 [tutor_driver.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/tutor_driver.py) 中，`detect_lang` 會先利用正則表達式剝除 LaTeX 數學公式與指令（因為 LaTeX 公式在語意上是語言中立的），然後計算 CJK 字元佔所有非空白字元的比例。
    *   若 **CJK 占比 < 10%**，則判定此對話 Session 的語言為**英文 (en)**。
    *   否則，判定此 Session 的語言為**繁體中文 (zh)**。
2.  **資源與提示動態載入**：
    根據判定的語言結果，`TutorDriver` 會動態切換：
    *   **System Template**：`BASE_SYSTEM`（中文）對照 `BASE_SYSTEM_EN`（英文）。
    *   **分級提示指令**：`LEVEL_INSTRUCTIONS` 對照 `LEVEL_INSTRUCTIONS_EN`。
    *   **階段引導指令**：`PHASE_INSTRUCTIONS` 對照 `PHASE_INSTRUCTIONS_EN`。
    *   **定理提示內容**：優先從 [hint_ladders_en.json](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/hint_ladders_en.json) 讀取英文提示，若無則降級使用 [hint_ladders.json](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/hint_ladders.json)。

---

## 4. 檔案目錄對照表

本專案結構緊湊，各模組職責清晰，具體對照如下：

### 4.1 資料建置與驗證模組
*   [dataset/build.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/build.py)：將 `src/` 中的題目與 dialogues 對話原始碼組裝，注入 grounded system prompt（包含參考解答），輸出為 `dialogues_core.jsonl` 與 `dialogues_augmented.jsonl`，最後以 9:1 的比例切分並隨機打亂產生 `train.jsonl` 與 `val.jsonl`。
*   [dataset/validate.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/validate.py)：對建置完成的 `train.jsonl` 與 `val.jsonl` 進行全量品質檢查，包含角色交替順序、問號數量、字數長度限制、拒絕洩漏詞彙比對等，確保訓練數據品質。
*   [dataset/test_dataset.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/test_dataset.py)：針對資料集格式、完整性與基礎欄位進行單元測試。

### 4.2 對話控制與推論核心 (TutorDriver)
*   [dataset/tutor_driver.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/tutor_driver.py)：本專案的確定性控制中樞。包含對話階段偵測、分級提示控制、動態雙語判定，以及後處理防禦機制。
*   [dataset/interactive_turn.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/interactive_turn.py)：供開發者或評估人員在終端機與助教進行多輪互動的命令列腳本。
*   [dataset/problems.json](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/problems.json) 與 [dataset/problems_en.json](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/problems_en.json)：存放 50 道大學數學題目的陳述與 LaTeX 參考解。
*   [dataset/hint_ladders.json](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/hint_ladders.json) 與 [dataset/hint_ladders_en.json](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/hint_ladders_en.json)：存放每道題目的分級提示（L2 定理名稱或核心想法）。

### 4.3 測試與評估腳本
*   [dataset/test_driver_unit.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/test_driver_unit.py)：無須 GPU，針對 `TutorDriver` 的狀態轉移、問句截斷、n-gram 洩漏判定、雙語判定等核心純 Python 邏輯進行 25 項斷言測試。
*   [dataset/test_driver_phase.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/test_driver_phase.py)：需要 GPU，測試在多輪對話中各種對話階段（如 refuse_leak、rectify、review）的實際狀態轉換與提示注入。
*   [dataset/test_driver_integration.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/test_driver_integration.py)：需要 GPU，測試在學生連續卡住時，`TutorDriver` 是否正確進行 L0 -> L1 -> L2 的提示升級並注入定理名稱。
*   [dataset/eval_final_driver.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/eval_final_driver.py)：本專案的最終評估主程式，在 8 道未見題（held-out）與對抗情境下執行評估。
*   [dataset/eval_final_ollama.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/eval_final_ollama.py)：評估對照組（使用 Ollama 思考型模型與 baseline 提示詞）的評估腳本。
*   [dataset/eval_english.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/eval_english.py) 與 [dataset/eval_hard.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/eval_hard.py)：分別對英文情境與高難度分布外題目進行引導成效評估。
*   [dataset/eval_heldout_v3.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/dataset/eval_heldout_v3.py)：針對 held-out 測試集的早期評估對比腳本。

### 4.4 QLoRA 訓練引擎
*   [learn_path/socratic_tutor/train_qlora.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/learn_path/socratic_tutor/train_qlora.py)：微調主程式，配置 4-bit 量化、LoRA 參數、左截斷滑動窗口、Assistant-only loss masking，並整合 EarlyStopping 與最佳模型儲存。
*   [learn_path/socratic_tutor/common.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/learn_path/socratic_tutor/common.py)：共用設定檔，定義微調時預設使用的基底模型名稱（Qwen3-4B）與資料路徑。
*   [learn_path/socratic_tutor/test_4bit_load.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/learn_path/socratic_tutor/test_4bit_load.py)：用於測試本機環境是否能成功以 4-bit/8-bit 量化載入基底模型的冒煙測試腳本。
*   [learn_path/socratic_tutor/download_chunked.py](file:///d:/UserData/claude_project/霓資料/math-proof-week2/learn_path/socratic_tutor/download_chunked.py)：預載/分塊下載基底模型權重之工具腳本。
