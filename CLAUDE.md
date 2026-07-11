# week3 — 蘇格拉底式微積分引導助教

本目錄記錄從「LLM 微積分證明 pipeline」演進至「蘇格拉底式引導助教」的完整實驗過程。
**目前主要成果與活躍開發區是 `dataset/`**：一套手寫的 grounded 蘇格拉底對話資料集，
用於 QLoRA 微調 Qwen3-4B，已透過多輪迭代（v2→v5）驗證微調可穩定超越未微調基底模型。

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

Bash（conda 不在 PATH 上）改用環境內 python 直呼：
```bash
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" your_script.py
```

---

## 目錄結構

```
week3/
├── dataset/                          # ★★★ 主要成果：手寫 grounded 蘇格拉底資料集 + QLoRA 微調
│   ├── src/                          # 手寫內容源碼（problems_*.py、dialogues_*.py）
│   │   ├── problems_A.py ~ E.py      # 50 道題目 + LaTeX 參考解（極限/連續/微分/積分/級數 各10）
│   │   ├── dialogues_A.py ~ E.py     # 150 條核心對話（3 persona × 50 題）
│   │   ├── dialogues_aug_*.py        # 犯錯變體 + 關鍵步驟短對話
│   │   ├── dialogues_resist.py       # 抗洩漏／抗附和對話（v3 新增）
│   │   └── dialogues_hint.py         # 分級提示對話（v4/v5 新增，見下）
│   ├── build.py                      # 組裝 src/ → problems.json + train/val.jsonl（注入 grounded system）
│   ├── validate.py                   # 格式/字數/一問一等/不洩漏 驗證
│   ├── test_dataset.py               # 分佈/引用/grounding 完整性測試
│   ├── problems.json / train.jsonl / val.jsonl   # build.py 產出（382 對話，344/38 切分）
│   ├── held_out.json / held_out_attempts.json    # 8 題訓練集外的評估題 + 埋錯嘗試
│   ├── hard_math_major.json          # 5 題訓練分布外難題（一致收斂/Darboux定理/Chebyshev積分不等式等）
│   ├── eval_heldout.py / eval_heldout_v3.py       # held-out 首問／三情境（首問/糾錯/逼問）評估
│   ├── eval_hard.py                  # 難題評估（含 Darboux 完整多輪對話）
│   ├── eval_full_dialogue.py         # 完整多輪引導對話測試（模型即時生成、學生依參考解手寫）
│   ├── eval_hint_escalation.py       # 分級提示規則驗證（學生連續卡住兩次）
│   ├── qlora_adapter_v2/ ~ v5/       # 各版 LoRA adapter（權重不進 git，見 .gitignore）
│   └── eval_out_v2/ ~ v4/、eval_out_hard/   # 各版評估報告與生成結果
├── learn_path/                       # 舊版蘇格拉底助教實驗（MathDial+GSM8K 行為遷移，歷史對照組）
│   ├── 架構設計.md                   # 子系統 A/B 架構說明（含新舊資料策略對照）
│   └── socratic_tutor/               # QLoRA 訓練腳本本體（train_qlora.py、common.py 等，dataset/ 沿用同一套腳本）
├── socratic_math_research.md         # SocraticMath 研究與資料集設計規劃（已落地為 dataset/）
├── dataset_plan.md                   # dataset/ 的企劃文件
├── PUSH_SCOPE.md                     # git 推送範圍記錄
├── simple_4B_ollama.py               # 4B Ollama 直接推論（歷史 baseline，未做 grounding）
├── archive/                          # 歸檔：舊測試題、舊評估結果、舊腳本
└── gguf/                             # 本機 GGUF 模型（Qwen3-4B-Thinking Q4_K_M，Ollama 用）
```

---

## 模型與路線

| 路線 | 模型 | Backend | 現況 |
| --- | --- | --- | --- |
| **推薦（互動場景）** | Qwen3-4B-Instruct + QLoRA（`dataset/qlora_adapter_v3` 起） | transformers + bitsandbytes | ★ 已證實超越未微調基底，見下方結論 |
| Ollama grounded（無微調） | Qwen3-4B-Thinking-2507 | Ollama（本機 GGUF） | 仍是「零訓練成本」的可靠備案 |
| 歷史對照 | Qwen2.5-Math-7B-Instruct | transformers（⚠️ segfault 風險） | 不用，7B 在 Windows 會 segfault |

> ⚠️ `transformers 5.x + bitsandbytes` 在 Windows 載入 7B 模型時會 segfault；4B 模型實測 OK。

---

## 執行方式

### 資料集重建與驗證（`dataset/`）

```powershell
$env:PYTHONNOUSERSITE = "1"
conda run -n lora_project --live-stream python dataset\build.py          # src/ → problems.json + train/val.jsonl
conda run -n lora_project --live-stream python dataset\validate.py       # 格式/字數/一問一等/不洩漏
conda run -n lora_project --live-stream python dataset\test_dataset.py   # 分佈/引用/grounding 完整性
```

### QLoRA 微調（用 `learn_path/socratic_tutor/train_qlora.py`，但指向 `dataset/` 的資料）

`common.py` 支援環境變數覆寫路徑，訓練 `dataset/` 資料集、輸出到新版 adapter 目錄，
不動到舊的 `learn_path/socratic_tutor/qlora_adapter/`：

```powershell
$env:TRAIN_JSONL = "week3\dataset\train.jsonl"
$env:VAL_JSONL   = "week3\dataset\val.jsonl"
$env:ADAPTER_DIR = "week3\dataset\qlora_adapter_v6"     # 每次遞增版號
$env:MAX_LEN = "640"; $env:EPOCHS = "3"; $env:GRAD_ACCUM = "8"; $env:EVAL_STEPS = "20"
$env:OPTIM = "adamw_8bit"          # ★ 不要用 paged_adamw_8bit，遇 abrupt kill 後會 init error
$env:NEFTUNE_ALPHA = "5"           # embedding 噪音正則化，小資料 SFT 有感提升
conda run -n lora_project --live-stream python learn_path\socratic_tutor\train_qlora.py
```

### 評估（`dataset/eval_*.py`，皆走 transformers 4-bit + PeftModel，不需 Ollama）

```powershell
conda run -n lora_project --live-stream python dataset\eval_heldout_v3.py     # 3情境：首問/糾錯/逼問答案
conda run -n lora_project --live-stream python dataset\eval_full_dialogue.py  # 完整多輪對話（人工檢視用）
conda run -n lora_project --live-stream python dataset\eval_hard.py           # 訓練分布外難題
conda run -n lora_project --live-stream python dataset\eval_hint_escalation.py # 分級提示規則驗證
```

### 舊版 Ollama grounded 助教（無微調，仍可用）

```powershell
conda run -n lora_project --live-stream python learn_path\socratic_tutor\gen_reference_solutions.py
conda run -n lora_project --live-stream python learn_path\best_grounded_tutor\grounded_tutor.py
```

---

## 資料集設計（`dataset/`）

- **Grounded SFT**：每筆 `system` 含 `<REFERENCE_PROOF>`（該題參考解，學生看不到），
  確保引導方向永遠正確，不會像早期跨域微調那樣「自信給錯方向」。
- **五階段引導策略**：契約確認 → 架構規劃 → 逐步推導 → 邏輯糾錯 → 嚴謹總結。
- **3 種學生人格**：confused（迷茫）/ error（犯錯）/ bright（優秀）。
- **分級提示規則**（v4 起）：學生對同一步連續兩次答不出來，助教可點出關鍵定理/技巧
  名稱或簡短想法，但不解釋如何套用、不給算式——避免無限鬼打牆問句，同時保留學生自己
  完成推導的空間。
- 全部內容（題目、參考解、對話）由 Claude 手寫並驗證數學正確性，非模型生成。

## 微調版本迭代歷史

| 版本 | 改動 | 結果（held-out，/5） |
| --- | --- | :---: |
| v2 | 首版重訓（50題/315對話，grounded 但無抗壓/分級提示訓練） | ft_grounded 4.26 ≈ base_grounded 4.44（未見優勢） |
| **v3** | +20 條抗洩漏/抗附和對話、修複合問句、NEFTune | **ft 4.35 vs base 3.65（+0.70，全情境領先）** |
| v4 | +10 條分級提示對話（學生連續卡住兩次才透漏定理名稱） | 觸發時機/深度未完全守住（過早透漏、給出完整算式） |
| **v5** | 修正 v4 過度洩漏的範例、補充無正式定理名稱的純想法提示（12 條 hint，eval_loss 1.065） | 最嚴重的「把算式算給學生」在 2/3 題修復；C8 提前點名未修（根因是主題級聯想）；E4 轉為輕微保守。**結論：純 SFT 對「提示深度」的校準已到極限**，見 `eval_out_v5/HINT_REPORT_v5.md` |
| **v6 + driver（★ 部署形態）** | 架構改造：`tutor_driver.py`（stuck counter→提示等級、階段偵測、單問句截斷、洩漏 n-gram 檢查）＋ `hint_ladders.json`（16 題）＋ 節奏錯位/寫證明審閱對話 +18 條（400 對話，eval_loss 1.176） | driver 測試 20/20＋9/9：分級提示完全受控、C8 提前點名修復、**審閱能力（新）**能抓嚴格性遺失與缺依據；裸模型回歸 4.13（vs v3 4.35，−0.22 換三項新能力，S3 抗洩漏稀釋為主因）。見 `eval_out_v6/EVAL_REPORT_v6.md` |

**關鍵發現**：
1. **v2→v3 的轉折點是資料組成，不是超參數**：v2 的僵局根因是評估只測「標準題首問」（base
   已近天花板）、且訓練集零筆「拒答洩漏/抗附和」訊號。補上針對性訓練資料後才反超。
2. **難題測試（`hard_math_major.json`）證實遷移能力**：即使在完全不在訓練範圍的技巧
   （一致收斂、Darboux 定理、Chebyshev 積分不等式）上，ft_grounded 仍平均領先 base +0.46。
3. **完整多輪對話測試發現真實缺陷**：模型有時會把兩個子問題捆成複合問句，且學生沒按
   預期順序回答時不會回頭確認，會自己搶先講出結論——這是下一步訓練資料可以補的方向。

詳細報告見 `dataset/eval_out_v2/EVAL_REPORT_v2.md`、`eval_out_v3/EVAL_REPORT_v3.md`、
`eval_out_hard/EVAL_REPORT_hard.md`。

---

## 舊版實驗結論（歷史對照，`learn_path/socratic_tutor/eval_out/EVAL_REPORT.md`）

在 `dataset/` 出現以前，用 MathDial+GSM8K 行為遷移訓練、無 grounding 訓練資料時的結論：

| 路線 | held-out 12 題（/5） | v4 難題 10 題（/5） |
| --- | :---: | :---: |
| grounded（思考型 + 參考解，無微調） | 4.42 | 4.55 |
| 微調 + grounded | 4.54 | 4.10 |
| 微調（純，跨域訓練） | 4.04 | **2.90（危險，自信給錯方向）**|
| base（無微調） | 3.63 | 3.30 |

當時的結論「純微調在難題上反而有害」**已被 `dataset/` 的域內訓練推翻**——v3 之後的純微調
（`ft_plain`）在同類難題上達 4.25/5，不再出現自信給錯方向的失敗模式（見 CLAUDE.md 上方
「微調版本迭代歷史」與 `dataset/eval_out_v2/EVAL_REPORT_v2.md` 第二節）。
