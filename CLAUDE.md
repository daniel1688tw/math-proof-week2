# week3 — 蘇格拉底式高等數學證明引導助教

本 repo 只保留**一個方法**：手寫 grounded 資料集 QLoRA 微調 Qwen3-4B（`qlora_adapter_v6`）
＋ 對話驅動程式（`tutor_driver.py`）。這是經過 v2→v6 六輪迭代與三路線正面對決後判定的
最佳部署形態（判定依據：`dataset/eval_out_final/FINAL_VERDICT.md`）。

**歷史版本不在工作目錄**：所有被淘汰的方法（MathDial 行為遷移、Ollama 無微調路線、
v2–v5 adapter 與其評估）完整保存在 git tag **`experiments-v2-v6`**，
需要時 `git checkout experiments-v2-v6` 即可回看。

## 語言慣例

與此目錄相關的對話、說明、註解與回覆，請一律使用**繁體中文**。

---

## Python 環境

Anaconda 虛擬環境 **`lora_project`**（Python 3.11，路徑 `D:\Danie\anaconda3\envs\lora_project`）。

```powershell
$env:PYTHONNOUSERSITE = "1"
conda run -n lora_project --live-stream python your_script.py
```

Bash（conda 不在 PATH）：
```bash
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" your_script.py
```

關鍵套件：torch 2.5.1+cu121、transformers 5.8.1、peft 0.19.1、bitsandbytes 0.49.2。
硬體：RTX 4050 Laptop 6GiB VRAM。
⚠️ transformers 5.x + bitsandbytes 在 Windows 載入 **7B** 會 segfault；本專案全程用 4B，安全。

---

## 架構（部署形態 = 模型 + 驅動程式）

```
學生訊息 ──► TutorDriver（dataset/tutor_driver.py）
              │  確定性決策層：
              │  · stuck counter（連續卡住 0/1/2 次 → 提示等級 0/1/2）
              │  · 階段偵測（交草稿→審閱、逼問→拒絕、嘗試→糾錯、說懂了→請寫證明）
              │  · 等級 2 注入 hint_ladders.json 的預寫提示內容
              ▼
         qlora_adapter_v6 + Qwen3-4B（4-bit nf4）＋ grounded system（含 <REFERENCE_PROOF>）
              │
              ▼
         後處理：單問句截斷、洩漏 15-gram 檢查（命中→加強指示重生成）
```

**設計鐵律**（v4→v6 三次驗證的教訓）：離散決策（何時升級、何時換階段）交給程式碼；
內容拿捏（提示深度、審閱重點）交給預寫內容（參考解、hint ladder）；模型只負責數學與語氣。

---

## 目錄結構

```
week3/
├── dataset/                          # ★ 一切核心
│   ├── src/                          # 手寫內容源碼（50 題 + 400 對話，Claude 撰寫並驗證）
│   ├── build.py / validate.py / test_dataset.py     # 建置與驗證
│   ├── problems.json / train.jsonl / val.jsonl       # 建置產出（360/40）
│   ├── hint_ladders.json             # 分級提示內容（driver 等級 2 用）
│   ├── tutor_driver.py               # ★ 對話驅動程式
│   ├── interactive_turn.py           # 逐輪互動 CLI（維護 session 狀態檔）
│   ├── qlora_adapter_v6/             # ★ 部署 adapter（權重不進 git）
│   ├── held_out.json / held_out_attempts.json / hard_math_major.json / adv_test_problem.json  # 評估題
│   ├── eval_heldout_v3.py            # 三情境回歸（裸模型，HELDOUT_ADAPTER 覆寫）
│   ├── eval_hard.py                  # 分布外難題（HARD_ADAPTER 覆寫）
│   ├── eval_final_driver.py          # 部署形態三情境（FINAL_ADAPTER 覆寫）
│   ├── eval_final_ollama.py          # Ollama 對照（歷史對決用，需 Ollama）
│   ├── test_driver_unit.py / test_driver_integration.py / test_driver_phase.py  # driver 測試
│   └── eval_out_final/ / eval_out_v6/ / eval_out_hard/ / eval_out_driver/       # 現行報告
├── learn_path/socratic_tutor/        # 訓練引擎（僅 4 檔）
│   ├── common.py                     # 模型與路徑設定（env 覆寫）
│   ├── train_qlora.py                # QLoRA 訓練主程式
│   ├── download_chunked.py           # 分塊下載基底模型（VPN 節流對策）
│   ├── test_4bit_load.py             # 4-bit 載入煙霧測試
│   └── qwen3_4b/                     # 基底權重（~8GB，不進 git）
├── dataset_plan.md / socratic_math_research.md      # 設計文件
├── PUSH_SCOPE.md                     # git 推送範圍
└── README.md                         # GitHub 對外說明
```

---

## 常用指令

### 資料集重建與驗證
```powershell
conda run -n lora_project --live-stream python dataset\build.py
conda run -n lora_project --live-stream python dataset\validate.py
conda run -n lora_project --live-stream python dataset\test_dataset.py
```

### 重新訓練（產出新版 adapter，不覆蓋 v6）
```powershell
$env:ADAPTER_DIR = "week3\dataset\qlora_adapter_v7"   # 預設是 qlora_adapter_new
$env:MAX_LEN = "640"; $env:EPOCHS = "3"; $env:GRAD_ACCUM = "8"; $env:EVAL_STEPS = "20"
$env:OPTIM = "adamw_8bit"          # ★ 不要用 paged_adamw_8bit（abrupt kill 後 init error）
$env:NEFTUNE_ALPHA = "5"
conda run -n lora_project --live-stream python learn_path\socratic_tutor\train_qlora.py
```

### 測試與評估
```powershell
python dataset\test_driver_unit.py                                        # 純邏輯，無 GPU
conda run -n lora_project --live-stream python dataset\test_driver_integration.py   # 分級提示（GPU）
conda run -n lora_project --live-stream python dataset\test_driver_phase.py         # 階段管理（GPU）
conda run -n lora_project --live-stream python dataset\eval_final_driver.py         # 部署形態三情境
conda run -n lora_project --live-stream python dataset\eval_heldout_v3.py           # 裸模型回歸
```

### 互動使用
```powershell
conda run -n lora_project --live-stream python dataset\interactive_turn.py --problem A2 --state session.json --reset
conda run -n lora_project --live-stream python dataset\interactive_turn.py --problem A2 --state session.json --student "學生回覆"
```

---

## 最終判定數據（2026-07-11，8 held-out 題 × 3 情境，同尺評分）

| 路線 | S1 首問 | S2 糾錯 | S3 逼問 | 總平均 |
|---|:---:|:---:|:---:|:---:|
| **v6 + TutorDriver（採用）** | 4.31 | 4.19 | 4.31 | **4.27** |
| v3 裸模型 | 4.38 | 4.31 | 4.38 | 4.35 |
| Ollama Thinking + grounded | 3.63 | 4.75 | 3.63 | 4.00 |
| base + grounded | 3.88 | 4.06 | 3.00 | 3.65 |

- 與 v3 差 0.08（8 題雜訊內），但 v3 無分級提示/審閱/階段管理能力 → 功能完整性定勝負。
- Ollama 思考型 S2 糾錯全場最強（4.75）但 S3 曾把完整證明整段交出、且有空輸出——
  無訓練約束＋無防護的路線在對抗情境不可靠。未來可考慮「思考型當審閱後盾」混合架構。
- driver 防護直接證據：S3 裸 4.06 → 4.31（洩漏重生成 24 筆中觸發 6 次全數成功）。

## 已知弱點（下輪迭代方向）

1. 細膩雙重錯誤解剖力不足（H3-S2 誤說「平均式子沒問題」）→ rejection-sampling SFT 或混合架構。
2. 偶發式子細節錯誤（H5-S3 均值定理區間寫錯）。
3. M4 型細膩跳步（宣告聽起來完整時不驗證）→ driver 端步驟清單核對。
