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
新題目 ──► auto_reference.py 備課（PROVER×3 → VERIFIER → REPAIR → SEGMENTER，Ollama 思考型）
   ├─ verified   → 下方 grounded 教學（全部防護生效）
   └─ unverified → 同學模式（誠實聲明沒把握、同儕探索、被質疑會反省認錯）

學生訊息 ──► TutorDriver（dataset/tutor_driver.py）
              │  確定性決策層：
              │  · stuck counter（連續卡住 0/1/2 次 → 提示等級 0/1/2）
              │  · 階段偵測（交草稿→審閱、逼問→拒絕、嘗試→糾錯、說懂了→請寫證明）
              │  · 等級 2 注入 hint_ladders.json 的預寫提示內容
              │  · 提示梯用盡仍連卡兩次 → walkthrough 逐步教學（一步一確認，教完仍要學生自寫證明）
              │  · 審閱/糾錯輪 ──► 審閱後盾（review_backstop.py，Ollama 思考型找碴）
              │                    缺漏清單注入 system；不在線自動降級（REVIEW_BACKSTOP=0 關）
              ▼
         qlora_adapter_v6 + Qwen3-4B（4-bit nf4）＋ grounded system（含 <REFERENCE_PROOF>）
              │
              ▼
         後處理：單問句截斷、洩漏 15-gram 檢查、on-track 防奉送、
         等級 2 禁算式、回問保底（命中→加強指示重生成）
```

**設計鐵律**（v4→v6 三次驗證的教訓）：離散決策（何時升級、何時換階段）交給程式碼；
內容拿捏（提示深度、審閱重點）交給預寫內容（參考解、hint ladder）；模型只負責數學與語氣。
**混合架構延伸**（2026-07-12）：即時數學判斷（審閱草稿找缺漏）交給思考型模型
（S2 4.75 的證據），微調模型只把缺漏清單包裝成引導語氣——判斷與說話分工。

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
│   ├── review_backstop.py            # 審閱後盾（Ollama 思考型找碴，可降級）
│   ├── auto_reference.py             # ★ 自動備課管線（生成→驗證→修補→教學步驟切分）
│   ├── interactive_turn.py           # 逐輪互動 CLI（維護 session 狀態檔）
│   ├── qlora_adapter_v6/             # ★ 部署 adapter（權重不進 git）
│   ├── held_out.json / held_out_attempts.json / hard_math_major.json / adv_test_problem.json  # 評估題
│   ├── xdomain_problems.json         # 跨領域評估題（離散×3 + 線代×3，XDOMAIN_ADAPTER 覆寫）
│   ├── eval_heldout_v3.py            # 三情境回歸（裸模型，HELDOUT_ADAPTER 覆寫）
│   ├── eval_hard.py                  # 分布外難題（HARD_ADAPTER 覆寫）
│   ├── eval_final_driver.py          # 部署形態三情境（FINAL_ADAPTER 覆寫）
│   ├── eval_xdomain.py               # 跨領域遷移三情境（部署形態）
│   ├── eval_final_ollama.py          # Ollama 對照（歷史對決用，需 Ollama）
│   ├── test_driver_unit.py / test_driver_integration.py / test_driver_phase.py  # driver 測試
│   ├── test_backstop.py / eval_backstop_e2e.py      # 後盾準確度（需 Ollama）/ 端對端對照
│   ├── test_auto_reference.py / eval_svt_e2e.py     # 備課盲測 / walkthrough+同學模式端對端
│   └── eval_out_final/ / eval_out_v6/ / eval_out_hard/ / eval_out_driver/ / eval_out_xdomain/  # 現行報告
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
python dataset\test_driver_unit.py                                        # 純邏輯，無 GPU（51 項）
conda run -n lora_project --live-stream python dataset\test_driver_integration.py   # 分級提示（GPU）
conda run -n lora_project --live-stream python dataset\test_driver_phase.py         # 階段管理（GPU）
conda run -n lora_project --live-stream python dataset\eval_final_driver.py         # 部署形態三情境
conda run -n lora_project --live-stream python dataset\eval_heldout_v3.py           # 裸模型回歸
python dataset\test_backstop.py                                           # 後盾找碴準確度（需 Ollama）
conda run -n lora_project --live-stream python dataset\eval_backstop_e2e.py         # 後盾端對端（GPU+Ollama）
python dataset\test_auto_reference.py                                     # 備課管線盲測（需 Ollama，~1.5hr）
conda run -n lora_project --live-stream python dataset\eval_svt_e2e.py              # 逐步教學+同學模式端對端
```

### 推送前守門（每次更新必跑；skill：`/pre-push-check`）
```powershell
python dataset\regression_suite.py --quick     # 單元+資料集（~1 分鐘）
python dataset\regression_suite.py             # 完整：Claude 當評審+學生（GPU+claude CLI，~1.5hr）
python dataset\regression_suite.py --update-baseline   # 確認進步後抬高基準
```
任何指標低於 `dataset/regression_baseline.json` → exit 1，**不可推送**。
確定性指標（洩漏/拒絕/單問句/升級/教學收尾）零容忍；judge_* 指標容忍 ε=0.05。
計分卡與對話記錄存 `dataset/regression_scores/`（進 git，留版本歷史）。

### 新題目備課（先自己證對才教）
```powershell
python dataset\auto_reference.py --statement "證明 ..." --id NEW1 --out new_problem.json
# verified → 產出含 reference_proof + teach_steps 的題目檔，TutorDriver 直接可用
# unverified → 該題自動走同學模式（誠實降級，不硬教）
```

### 互動使用
```powershell
conda run -n lora_project --live-stream python dataset\interactive_turn.py --problem A2 --state session.json --reset
conda run -n lora_project --live-stream python dataset\interactive_turn.py --problem A2 --state session.json --student "學生回覆"
```

---

## 最終判定數據（8 held-out 題 × 3 情境，同尺評分；2026-07-12 更新）

| 路線 | S1 首問 | S2 糾錯 | S3 逼問 | 總平均 |
|---|:---:|:---:|:---:|:---:|
| **v6 + TutorDriver + 審閱後盾（採用）** | 4.31 | 4.50 | 4.31 | **4.37** |
| v6 + TutorDriver（後盾離線時的降級形態） | 4.31 | 4.19 | 4.31 | 4.27 |
| v3 裸模型 | 4.38 | 4.31 | 4.38 | 4.35 |
| Ollama Thinking + grounded | 3.63 | 4.75 | 3.63 | 4.00 |
| base + grounded | 3.88 | 4.06 | 3.00 | 3.65 |

- 審閱後盾把思考型的糾錯銳利度（4.75）移植進部署形態：S2 4.19→4.50（跨域 4.67→4.92），
  S1/S3 逐字不變；H3-S2 錯誤背書消除。域內 4.37 已超過 v3 裸模型 4.35。
- Ollama 思考型單獨用不可靠（S3 曾把完整證明整段交出、有空輸出）——混合架構讓它
  只在幕後找碴、永不直接面對學生，致命傷被隔離。
- driver 防護直接證據：S3 裸 4.06 → 4.31（洩漏重生成 24 筆中觸發 6 次全數成功）。
- 對決明細與備份基準：`eval_out_final/FINAL_VERDICT.md` 追加節、`*_nobackstop.md`。

## 跨領域遷移（2026-07-11，離散數學/線性代數 6 題，`eval_out_xdomain/EVAL_REPORT_xdomain.md`）

- 三情境總平均 4.25 ≈ 域內 4.27：引導行為無衰減遷移；S2 糾錯 4.67 反超域內（6 個埋錯全中）；
  18 筆生成零數學錯誤（grounded 參考解是關鍵錨，跨域**不可**拿掉）。
- 跨域放大三個域內已知弱點 → 當日在 driver 加了三項防護（on-track 防奉送／等級 2 禁算式／
  回問保底，皆為重生成機制，單元測試 39/39），**跨域升至 4.44、域內無回歸**。
- 審閱解釋精確度（X2「察覺對但解釋錯」）是唯一出現數學錯話的環節，driver 蓋不住，需訓練面解法。

## 審閱後盾（2026-07-12，混合架構落地，`eval_out_xdomain/backstop_e2e.md`）

- `review_backstop.py`：review/rectify 輪先讓 Ollama 思考型（qwen3-4b-thinking）對照參考解
  找碴，缺漏清單注入微調模型的階段指示。Ollama 不在線自動降級；`REVIEW_BACKSTOP=0` 關閉。
- 端對端驗證（3 個微調模型曾失手的案例，有/無後盾對照）：H3 雙重錯誤的錯誤背書
  「平均式子沒問題」**消失**、X4 從問錯目標變精準指出缺 v₂≠0、X2 無回歸。
- 工程教訓：思考鏈需 `num_predict=8192`（3072 會被思考吃光、正文空白）；模型輸出的
  LaTeX（`\{` `\dots`）是非法 JSON escape，解析需反斜線加倍重試；每次找碴 2–4 分鐘
  （GPU 被 HF 佔用時後盾走 CPU）。
- 找碴準確度（`test_backstop.py`）：X2 缺前提／X4 缺 v₂≠0／H3 雙錯 3/3 精準，
  關鍵是 CRITIC_SYSTEM 要求「教學標準」（未明說的依據也算缺漏，數學家標準會放行）。

## 自我驗證教學（2026-07-12，`eval_out_xdomain/SVT_REPORT.md`，設計 `self_verified_teaching_design.md`）

- **備課管線盲測（10 題已知解盲跑）：verified 9/10、verified 正確率 9/9 = 100%**（零錯誤背書）；
  唯一 unverified 是 M4 Darboux（歷來最難）——「知之為知之」正是設計目標。
- 逐步教學端對端：提示梯耗盡→自動進入→一步一確認→教完轉回學生自寫證明，全程正確；
  修復 `_STUCK_RE` 缺「不懂」的缺口。
- 同學模式端對端：首輪誠實聲明、被質疑坦白認錯並修正；同儕閒聊偶有混亂陳述（已聲明沒把握，可接受）。
- 已知限制：證明者與驗證員同一個 4B 思考模型（獨立取樣非獨立模型），新領域建議先抽查 verified 解。

## 已知弱點（下輪迭代方向）

1. ~~細膩雙重錯誤解剖、審閱「察覺對但解釋錯」~~ → 已由審閱後盾解決（2026-07-12，
   e2e 驗證 H3/X2/X4 全改善）；殘餘依賴：Ollama 需在線，離線時降級回原行為。
2. 偶發式子細節錯誤（H5-S3 均值定理區間寫錯）——發生在引導輪，後盾只蓋 review/rectify。
3. M4 型細膩跳步（宣告聽起來完整時不驗證）→ 可考慮把「宣告完成」也路由給後盾複核。
4. ~~on-track 奉送、等級 2 附算式~~ → 已由 driver 三項防護緩解（2026-07-11）；
   根治仍需下次重訓補「on-track 只肯定不奉送」訓練樣本。
