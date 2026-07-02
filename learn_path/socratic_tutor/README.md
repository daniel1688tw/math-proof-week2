# 蘇格拉底引導式微積分證明助教（QLoRA 微調）

把 **Qwen3-4B-Instruct-2507** 微調成「蘇格拉底引導式」數學證明助教：不直接給答案，
而是用一連串引導問題，陪學生一步步完成微積分證明。

## 設計取捨（重要）

公開資源上**不存在**「微積分證明 × 蘇格拉底多輪引導」的現成資料集。因此本專案採
**行為遷移（behaviour transfer）** 策略：

- **引導行為**用最真實的公開蘇格拉底數學教學對話訓練：
  - [`eth-nlped/mathdial`](https://huggingface.co/datasets/eth-nlped/mathdial)：2.3K 真人師生輔導對話（老師用 probing 提問引導）。
  - [`openai/gsm8k`](https://huggingface.co/datasets/openai/gsm8k)（`socratic` config）：引導性子問題逐步分解。
  - 兩者皆為「文字應用題」，但「問引導問題、不給答案、回應迷思」的**教學行為可遷移**到微積分。
- **微積分證明的內容知識**由 Qwen3-4B 基底本身提供（已具備微積分能力），
  推論時 `common.py` 的 `SYSTEM_SOCRATIC` 把行為錨定到「微積分與證明」。

> 若日後要更貼合微積分證明，可走「合成擴增」或「人工黃金種子」路線（見對話紀錄），
> 但本版刻意只用公開資料、零生成步驟。

## 硬體與環境

- GPU：RTX 4050 Laptop **6 GiB**（4-bit nf4 量化下 4B 可訓練）。
- 環境：conda `lora_project`（transformers 5.8.1 / bitsandbytes 0.49.2 / peft 0.19.1）。
- 網路：本機封鎖 HF 舊 CDN `cdn-lfs`，但新 Xet 後端（`cas-bridge.xethub.hf.co`）暢通，
  資料集與 Qwen3-4B 權重皆可下載。

## 檔案

| 檔案 | 說明 |
| --- | --- |
| `common.py` | 共用設定：基底模型名、路徑、`SYSTEM_SOCRATIC`（訓練/推論共用的引導 system prompt）。 |
| `prepare_data.py` | 下載 MathDial + GSM8K-socratic，轉成 `messages` 對話格式 → `data/train.jsonl`、`data/val.jsonl`。 |
| `test_4bit_load.py` | 下載 Qwen3-4B 並測試 4-bit 載入是否 segfault（投入訓練前的煙霧測試）。 |
| `train_qlora.py` | QLoRA 訓練：4-bit + LoRA，只對 assistant 回合算 loss，輸出 `qlora_adapter/`。 |
| `inference.py` | 載入基底 + adapter 做多輪引導對話；`USE_ADAPTER=0` 可對照微調前。 |

## 執行步驟

```powershell
# 0) 啟用環境變數（避免 user site-packages 干擾）
$env:Path = "D:\Danie\anaconda3;D:\Danie\anaconda3\Scripts;D:\Danie\anaconda3\Library\bin;" + $env:Path
$env:PYTHONNOUSERSITE = "1"
Set-Location "...\week3\learn_path\socratic_tutor"

# 1) 準備資料（小檔，快）
conda run -n lora_project --live-stream python prepare_data.py

# 2) 煙霧測試：4-bit 載入（首次會下載 ~8GB 權重）
conda run -n lora_project --live-stream python test_4bit_load.py

# 3) QLoRA 訓練（產出 qlora_adapter/）
conda run -n lora_project --live-stream python train_qlora.py

# 4) 推論（微調後引導對話）
conda run -n lora_project --live-stream python inference.py
#    對照微調前：
$env:USE_ADAPTER = "0"; conda run -n lora_project --live-stream python inference.py
```

## 訓練超參數（可用環境變數覆寫）

`EPOCHS=2`、`MAX_LEN=512`、`BATCH=1`、`GRAD_ACCUM=16`、`LR=2e-4`、`LORA_R=16`、`LORA_ALPHA=32`。
6 GiB VRAM 下若 OOM，先把 `MAX_LEN` 降到 384，或 `LORA_R` 降到 8。
（已啟用 `load_best_model_at_end` + EarlyStopping：存 eval_loss 最佳的 checkpoint，並在停滯時提早停。）

## 評估流程（improve.md 修正後）

評估刻意分成「生成回覆 → 存 JSON → 評分」三階段，避免 transformers 與 Ollama 同時搶 6GB。
測試題用 `problems.HELDOUT_PROBLEMS`（**不在訓練集**）量泛化；種子題只當記憶 sanity check。

```powershell
# A) transformers：base / finetuned 第一輪回覆（零 Ollama）
conda run -n lora_project --live-stream python compare.py

# B) Ollama：參考解（grounded/judge 需要）＋ A-socratic / grounded 第一輪回覆
conda run -n lora_project --live-stream python gen_reference_solutions.py
conda run -n lora_project --live-stream python gen_ollama_replies.py

# C) 彙整四方做 form + LLM judge（教學品質）對比
conda run -n lora_project --live-stream python score_replies.py

# D) 模擬學生多輪評估（是否能一步步引導到正確完成）
conda run -n lora_project --live-stream python eval_multiturn.py grounded

# 互動用 solution-grounded 助教（純 Ollama，先產參考解再引導）
conda run -n lora_project --live-stream python guided_tutor.py
```

| 新檔案 | 說明 |
| --- | --- |
| `problems.py` | 題目單一來源：`CALCULUS_SEEDS`（只訓練）、`HELDOUT_PROBLEMS`（只評估）。 |
| `ollama_client.py` | 可重用的 Ollama 客戶端（chat / generate_proof / resolve_model）。 |
| `gen_reference_solutions.py` | 用子系統 A 為評估題產「參考解」快取（grounded / judge 用）。 |
| `eval_judge.py` | LLM-as-judge：評引導回覆的教學品質（正確/相關/推進/不洩漏/聚焦）。 |
| `eval_common.py` | 共用：form 評分、回覆 JSON 讀寫。 |
| `compare.py` | 產 base / finetuned 第一輪回覆（held-out vs seed 分開報告）。 |
| `gen_ollama_replies.py` | 產 A-socratic / grounded 第一輪回覆。 |
| `score_replies.py` | 彙整四方回覆做 form + judge 對比表。 |
| `eval_multiturn.py` | 模擬學生多輪評估 + judge 整段對話。 |
| `guided_tutor.py` | solution-grounded 互動助教（參考解在手，引導不洩漏）。 |
