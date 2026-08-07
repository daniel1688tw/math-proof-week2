# 蘇格拉底式高等數學證明引導助教 — 精簡執行版

> **這個分支只放「從 0 跑起來」需要的東西**（62 個檔）。
> 評估腳本、守門系統、設計文件、歷次實驗紀錄、code review、簡報等，
> **全部在 `main` 分支**——需要看完整脈絡請 `git checkout main`。

面對高等數學證明題，助教**不直接給答案**，而以逐步提問引導學生自己完成證明。
部署形態 = QLoRA 微調的 Qwen3-4B ＋ 確定性驅動程式 ＋ 思考型模型當審閱後盾。

---

## 這個分支有什麼

```
dataset/
  src/ src_en/          中英平行的資料集源碼（50 題 + 對話，全人工撰寫）
  build.py validate.py  由 src/ 建出 train/val.jsonl 並驗證
  tutor_driver.py       ★ 對話驅動程式（確定性決策層，全部教學行為在這裡）
  auto_reference.py     ★ 自動備課（PROVER→VERIFIER→REPAIR→SEGMENTER→LADDER）
  review_backstop.py    審閱後盾（Ollama 思考型模型對照參考解找碴）
  app.py                Gradio 介面（使用者自帶題目）
  interactive_turn.py   命令列逐輪互動（內建題庫）
  problems.json         題庫（50 題 + 參考解）
  held_out.json / hard_math_major.json   額外題庫（13 題，含手寫提示梯的題目）
  hint_ladders.json / _en.json           手寫分級提示梯（16 題）
  train.jsonl val.jsonl 訓練資料（build.py 產出，已附上可直接訓練）
learn_path/socratic_tutor/
  common.py train_qlora.py               QLoRA 訓練
  download_chunked.py test_4bit_load.py  基底模型下載與 4-bit 載入煙霧測試
```

**不在 git 裡**（`.gitignore`）：基底模型權重（~8GB）、adapter 權重（132MB）。

---

## 從 0 開始

### 0. 環境

Anaconda 環境 `lora_project`（Python 3.11）。關鍵套件：
`torch 2.5.1+cu121`、`transformers`、`peft`、`bitsandbytes`、`gradio`。

```powershell
$env:PYTHONNOUSERSITE = "1"
conda run -n lora_project --live-stream python <script>
```

硬體：本專案全程在單張 **RTX 4050 Laptop（6 GiB VRAM）** 上以 4-bit nf4 執行。
⚠️ `transformers 5.x` + `bitsandbytes` 在 Windows 載入 **7B** 會 segfault；本專案用 4B，安全。

### 1. 下載基底模型

```powershell
conda run -n lora_project --live-stream python learn_path\socratic_tutor\download_chunked.py
conda run -n lora_project --live-stream python learn_path\socratic_tutor\test_4bit_load.py   # 煙霧測試
```

### 2. 建置資料集（可選——`train.jsonl` / `val.jsonl` 已附）

```powershell
conda run -n lora_project --live-stream python dataset\build.py      # src/ → 830 例，747/83
conda run -n lora_project --live-stream python dataset\validate.py   # 字數、單問句、不洩漏
```

### 3. 訓練

```powershell
$env:ADAPTER_DIR = "week3\dataset\qlora_adapter_v9"
$env:MAX_LEN = "1024"; $env:EPOCHS = "3"; $env:GRAD_ACCUM = "8"; $env:EVAL_STEPS = "20"
$env:OPTIM = "adamw_8bit"        # ★ 不要用 paged_adamw_8bit（中途中斷後會 init error）
$env:NEFTUNE_ALPHA = "5"
conda run -n lora_project --live-stream python learn_path\socratic_tutor\train_qlora.py
```

產出目錄名要是 `qlora_adapter_v9`，否則各執行腳本要用環境變數覆寫
（`ADAPTER` / `FINAL_ADAPTER` / `DRIVER_ADAPTER`…）。

### 4. 跑起來

```powershell
# 圖形介面：自己貼題目（需 Ollama 在線才有 grounded 備課，離線則走同學模式）
conda run -n lora_project --live-stream python dataset\app.py        # http://localhost:7860

# 命令列：用內建題庫
conda run -n lora_project --live-stream python dataset\interactive_turn.py --problem A2 --state s.json --reset
conda run -n lora_project --live-stream python dataset\interactive_turn.py --problem A2 --state s.json --student "我不知道怎麼開始"
```

**Ollama（可選但建議）**：`review_backstop.py` 與 `auto_reference.py` 需要
`qwen3-4b-thinking-2507`。沒有它系統仍可運作，只是審閱後盾與自動備課自動降級。

---

## 架構一句話

```
學生訊息 → TutorDriver（確定性）：連續卡住 → 提示等級 0/1/2；階段偵測；
           等級 2 注入預寫提示梯；梯用盡再卡 → 逐步教學（模板，答對才前進）
         → QLoRA 微調模型（4-bit）＋ 內含參考解的 grounded system prompt
         → 內容防護：洩漏檢查／防奉送／等級 2 禁算式／稱讚校準／單問句／回問保底
```

設計鐵律：**離散決策交給程式碼、內容拿捏交給預寫內容、模型只負責數學與語氣。**

---

## 完整版在 `main`

`main` 分支另有：評估腳本與報告（路線對決、跨領域、備課盲測）、回歸守門系統
（`regression_suite.py` ＋ 歷次計分卡與對話存檔）、單元測試 313 條、真實對話回放測試、
架構設計文件、專題成果報告與簡報、code review、已知弱點清單。
