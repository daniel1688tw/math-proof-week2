# week3 — 蘇格拉底式微積分引導助教

本目錄記錄從「LLM 微積分證明 pipeline」演進至「蘇格拉底式引導助教」的完整實驗過程，
以及下一階段的資料集設計規劃。

## 語言慣例

與此目錄相關的對話、說明、註解與回覆，請一律使用**繁體中文**。

---

## Python 環境

本專案使用 Anaconda 虛擬環境 **`lora_project`**。

| 項目 | 值 |
| --- | --- |
| 環境名稱 | `lora_project` |
| 環境路徑 | `D:\Danie\anaconda3\envs\lora_project` |
| Python | 3.11.15 |
| Anaconda root | `D:\Danie\anaconda3` |

### 在環境中執行命令

```powershell
$env:PYTHONNOUSERSITE = "1"
conda run -n lora_project --live-stream python your_script.py
```

---

## 目錄結構

```
week3/
├── socratic_math_research.md        # ★ 新方向：客製化微積分引導資料集設計規劃
├── simple_4B_ollama.py              # 4B Ollama 直接推論（當前 baseline）
├── 架構.md                          # simple_4B_ollama.py 架構說明
├── improve_v2.md                    # TIR/Judge/best-of-n 改進分析報告
├── run_eval_4b_ollama.py            # 全 10 題評估（4B Ollama）
├── run_smoke_4b_ollama.py           # 單題冒煙測試
├── run_compare_simple.py            # pipeline vs simple 對比
├── ollama_model.txt                 # Ollama 模型 tag（qwen3-4b-thinking-2507:latest）
├── Modelfile.qwen3-4b-thinking      # Ollama Modelfile
├── gguf/                            # 本機 GGUF 模型（Qwen3-4B-Thinking Q4_K_M）
├── baseline.py                      # [歷史] 7B transformers 4-stage pipeline
├── simple.py                        # [歷史] 7B transformers 直接回覆對照組
├── archive/                         # 歸檔：舊測試題、舊評估結果、舊腳本
└── learn_path/                      # 蘇格拉底助教實驗（見下）
```

```
learn_path/
├── 架構設計.md                      # 子系統 A/B 架構說明
├── improve.md                       # 評估方法問題與改進建議
├── best_grounded_tutor/             # ★ 推薦路線：grounded_tutor.py
└── socratic_tutor/
    ├── problems.py                  # 題目集（CALCULUS_SEEDS / HELDOUT 12 題）
    ├── guided_tutor.py              # Ollama grounded 引導助教（最佳路線）
    ├── gen_reference_solutions.py   # 產出參考解（答案卡）
    ├── gen_ollama_replies.py        # Ollama 批次生成（socratic/grounded 兩模式）
    ├── eval_judge.py                # LLM-as-judge 教學品質評分
    ├── eval_multiturn.py            # 多輪模擬學生評估
    ├── score_replies.py             # 統一評分入口
    ├── train_qlora.py               # QLoRA 微調（可用，但見★注意）
    ├── inference.py                 # LoRA adapter 推論
    ├── prepare_data.py              # 訓練資料準備
    ├── qwen3_4b/                    # 本機模型權重（~8 GB）
    ├── qlora_adapter/               # 訓練產出 LoRA adapter（checkpoint-364）
    ├── data/                        # train.jsonl / val.jsonl
    └── eval_out/                    # 評估結果（held-out 12 題 + v4 難題）
```

---

## 模型

| 路線 | 模型 | Backend |
| --- | --- | --- |
| **推薦（最佳）** | Qwen3-4B-Thinking-2507 | Ollama（本機 GGUF） |
| LoRA 微調 | Qwen3-4B-Instruct | transformers + bitsandbytes |
| 歷史對照 | Qwen2.5-Math-7B-Instruct | transformers（⚠️ segfault 風險） |

> ⚠️ `transformers 5.x + bitsandbytes` 在 Windows 載入 7B 模型時會 segfault；
> 4B 模型實測 OK。7B 路線請改用 Ollama 或降版至 `transformers==4.46.3`。

---

## 執行方式

### 當前主要路線（Ollama grounded 助教）

```powershell
# 前置：Ollama 已啟動，模型已 pull
# 1. 產出參考解（答案卡）
conda run -n lora_project --live-stream python learn_path\socratic_tutor\gen_reference_solutions.py

# 2. 互動式 grounded 助教
conda run -n lora_project --live-stream python learn_path\best_grounded_tutor\grounded_tutor.py

# 3. 批次評估（held-out 或 v4 難題）
conda run -n lora_project --live-stream python learn_path\socratic_tutor\gen_ollama_replies.py
conda run -n lora_project --live-stream python learn_path\socratic_tutor\score_replies.py
```

### 4B Ollama baseline（無 grounding）

```powershell
conda run -n lora_project --live-stream python simple_4B_ollama.py
conda run -n lora_project --live-stream python run_eval_4b_ollama.py
```

### LoRA 微調（歷史，★單獨使用不安全）

```powershell
conda run -n lora_project --live-stream python learn_path\socratic_tutor\prepare_data.py
conda run -n lora_project --live-stream python learn_path\socratic_tutor\train_qlora.py
conda run -n lora_project --live-stream python learn_path\socratic_tutor\inference.py
```

---

## 實驗結論（評估報告：eval_out/EVAL_REPORT.md）

| 路線 | held-out 12 題（/5） | v4 難題 10 題（/5） |
| --- | :---: | :---: |
| **grounded（思考型 + 參考解）** | **4.42** | **4.55** ★ |
| 微調 + grounded | 4.54 | 4.10 |
| 微調（純） | 4.04 | 2.90（最差）|
| base（無微調） | 3.63 | 3.30 |

**核心發現**：
- grounded（參考解在手）是關鍵，題目越難越重要
- 純微調在難題上反而有害（自信給錯方向）
- 思考型模型（Ollama）+ grounded = 最簡單且最安全的路線

---

## 下一步：socratic_math_research.md

規劃一套針對微積分證明的客製化蘇格拉底對話資料集：
- 五階段引導策略（契約確認 → 架構規劃 → 逐步推導 → 邏輯糾錯 → 嚴謹總結）
- 三種學生人格（優秀 / 迷茫 / 犯錯）的合成對話
- Grounded SFT 格式（system 帶參考解，保證內容正確性）
