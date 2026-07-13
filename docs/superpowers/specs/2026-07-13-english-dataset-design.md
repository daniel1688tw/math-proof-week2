# 英文化訓練資料與雙語部署設計（2026-07-13）

## 背景與問題

實測（Colab 英文對話）發現部署形態對英文學生完全失效：
1. 訓練集 360/40 筆全為繁中 → 英文輸入是分布外，模型退化成重複同一句罐頭問句。
2. `tutor_driver.py` 的卡住／階段／逼問偵測 regex 只認中文 → 英文學生永遠 level 0、交草稿不會進 review 階段。
3. driver 沒有「重複回覆」保底。

使用者需求：**大多時候用英文**，故以英文為主、保留中文能力。

## 決策（使用者已確認）

1. **雙語 720 筆**：原繁中 360 筆 + 英文翻譯版 360 筆一起訓練。
2. **英文為主介面、driver 雙語偵測**：system prompt 與 hint ladder 出英文版；driver 依學生語言自動選用，偵測 regex 中英都支援。
3. **翻完直接重訓（qlora_adapter_v7，不覆蓋 v6）＋ 跑英文版三情境評估**。
4. 完成後檢查 `hybrid-review-backstop`、`self-verified-teaching` 兩分支是否有同樣問題。

## 架構

### 資料層
- 新增 `dataset/src_en/`，鏡像 `dataset/src/` 全部 19 檔（problems_A–E、dialogues 14 檔），
  內容由 Claude 逐句翻譯（非機器翻譯；數學 LaTeX 不變，語氣與教學意圖保留）。
  題目 id 沿用（A1…E10），模組內以 `lang: "en"` 欄位標示或由目錄區分。
- `build.py`：
  - 新增 `SYSTEM_TEMPLATE_EN`（與中文版語義等價的精簡 grounded system）。
  - 分別載入 `src/`（中文模板、「題目：」前綴）與 `src_en/`（英文模板、`Problem:` 前綴），
    合併後同一種子 shuffle、9:1 切分 → train ≈ 648 / val ≈ 72。
- `hint_ladders_en.json`：50 題 hint ladder 英文版。
- `problems.json` 維持中文；新增 `problems_en.json`（driver 依語言取用 statement/proof）。
  參考解（reference_proof）英文版翻譯連接詞、保留全部數學式。

### Driver 層（`tutor_driver.py`）
- 語言偵測：學生首則訊息 CJK 字元比例 < 10% → session 語言 = en（session 級，不逐輪切換）。
- `BASE_SYSTEM` / `LEVEL_INSTRUCTIONS` / `PHASE_INSTRUCTIONS` / `WRITEUP_FALLBACK` 出英文版，依 session 語言選用。
- 偵測 regex 全部加英文 alternation：
  - stuck：`i don't know|no idea|not sure|stuck|confused|can't figure|lost` 等（維持短回覆長度門檻，英文放寬至 ~120 chars）。
  - draft/review：`proof:|here is my proof|please review|i wrote`。
  - demand：`just tell me|give me the answer|write it for me|show me the full proof`。
  - attempt：`is this right|is this correct|my attempt|i think|i believe`。
  - understood：`i understand now|i got it|makes sense now|i see it now`。
- 新增**重複回覆保底**（中英共用）：本輪回覆正規化後與最近 3 輪任一助教回覆相同或幾乎相同
  （normalized 完全相等即可，先不做模糊比對）→ 注入「不要重複之前問過的問題，針對學生最新訊息回應」重生成一次。

### 訓練
- `ADAPTER_DIR=qlora_adapter_v7`、MAX_LEN=640、EPOCHS=3、GRAD_ACCUM=8、OPTIM=adamw_8bit、NEFTUNE_ALPHA=5。

### 驗證
- `validate.py` / `test_dataset.py` 通過（如有語言假設需同步更新）。
- driver 單元測試新增英文偵測與重複保底案例（純邏輯、無 GPU）。
- 評估：held_out 題翻英文版跑 `eval_final_driver.py` 三情境（英文學生模擬），
  另跑原中文評估確認無回歸。
- IVT 情境（使用者實測失敗的那段英文對話）作為手動煙霧測試。

## 不做的事
- 不做模糊相似度重複偵測（先用精確比對，不夠再加）。
- 不動 hybrid-review-backstop 的後盾邏輯（本分支 lora-finetune 沒有該檔）；
  分支檢查為獨立後續步驟。

## 風險
- 720 筆訓練時間約加倍（6GB VRAM 可行，時長數小時）。
- 雙語混訓可能輕微稀釋中文表現 → 以中文回歸評估把關。
