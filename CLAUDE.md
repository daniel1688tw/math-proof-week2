# week3 — 蘇格拉底式高等數學證明引導助教

本 repo 只保留**一個方法**：手寫 grounded 資料集 QLoRA 微調 Qwen3-4B（`qlora_adapter_v9`，雙語）
＋ 對話驅動程式（`tutor_driver.py`）。這是經過 v2→v6 六輪迭代與三路線正面對決後判定的
最佳部署形態（判定依據：`dataset/eval_out_final/FINAL_VERDICT.md`）。

**現行部署形態 = `qlora_adapter_v9` + 含 #11/#12 修復的 driver**。v10、v11 兩輪整體重訓
皆守門判退（同一個收尾紀律退化重現），adapter 封存於本機供分析，**不要誤以為版號越新越該用**。

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
              │  · 階段偵測（交草稿→審閱、逼問→拒絕、嘗試→糾錯、說懂了→請寫證明、
              │              證明確認完成→closed 收尾：禁新問題/替代法/延伸）
              │  · 等級 2 注入 hint_ladders.json 的預寫提示內容
              │  · 提示梯用盡仍連卡兩次 → walkthrough 逐步教學（一步一確認，教完仍要學生自寫證明）
              │  · 審閱/糾錯輪 ──► 審閱後盾（review_backstop.py，Ollama 思考型找碴）
              │                    缺漏清單注入 system；不在線自動降級（REVIEW_BACKSTOP=0 關）
              ▼
         qlora_adapter_v9 + Qwen3-4B（4-bit nf4）＋ grounded system（含 <REFERENCE_PROOF>）
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
│   ├── app.py / test_app.py          # ★ Gradio 商品化介面（本機單人 Demo）／其純邏輯測試
│   ├── qlora_adapter_v9/             # ★ 部署 adapter（權重不進 git）
│   ├── qlora_adapter_v10/ v11/       # 判退封存（本機、gitignore，供分析）
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
│   ├── regression_suite.py           # ★ 推送前守門（預設 agy/Gemini 當評審+學生；退步即 exit 1）
│   ├── auto_gate.py                  # 守門外圈自動迭代（退件→修 driver→重評）
│   ├── regression_baseline_antigravity.json  # ★ 現行基準（預設評審後端；只升不降）
│   ├── regression_baseline.json / regression_scores/  # Claude 後端基準與各版本計分卡
│   └── eval_out_final/ / eval_out_v6/ / eval_out_hard/ / eval_out_driver/ / eval_out_xdomain/  # 現行報告
├── learn_path/socratic_tutor/        # 訓練引擎（僅 4 檔）
│   ├── common.py                     # 模型與路徑設定（env 覆寫）
│   ├── train_qlora.py                # QLoRA 訓練主程式
│   ├── download_chunked.py           # 分塊下載基底模型（VPN 節流對策）
│   ├── test_4bit_load.py             # 4-bit 載入煙霧測試
│   └── qwen3_4b/                     # 基底權重（~8GB，不進 git）
├── .claude/skills/pre-push-check/    # /pre-push-check skill：推送前守門流程（進版控）
├── docs/
│   ├── code-review-product-ui.md     # 商品化介面 code review（第 2 次，覆蓋前版）
│   ├── notion/                       # Notion 專案空間的內容源（00–09，見下方「專案文件空間」）
│   └── superpowers/                  # 設計 spec 與實作計畫
├── dataset_plan.md / socratic_math_research.md      # 設計文件
├── self_verified_teaching_design.md  # 自我驗證教學設計（備課/同學模式/逐步教學）
├── 專題成果報告.md                     # 論文式完整報告
├── 使用者說明書.md                     # 給使用者的操作說明（商品化介面）
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

### 重新訓練（產出新版 adapter，不覆蓋現役 v9）
```powershell
$env:ADAPTER_DIR = "week3\dataset\qlora_adapter_v12"  # 預設是 qlora_adapter_new
$env:MAX_LEN = "1024"; $env:EPOCHS = "3"; $env:GRAD_ACCUM = "8"; $env:EVAL_STEPS = "20"
$env:OPTIM = "adamw_8bit"          # ★ 不要用 paged_adamw_8bit（abrupt kill 後 init error）
$env:NEFTUNE_ALPHA = "5"
conda run -n lora_project --live-stream python learn_path\socratic_tutor\train_qlora.py
```

### 測試與評估
```powershell
python dataset\test_driver_unit.py                                        # 純邏輯，無 GPU（127 條斷言 / 13 組）
python dataset\test_app.py                                                # 介面純邏輯，無 GPU、不連 Ollama
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
python dataset\regression_suite.py             # 完整：agy/Gemini 當評審+學生（GPU+agy CLI，~1.5hr）
python dataset\regression_suite.py --gen-only  # 只生成存檔不評審（省額度，之後 --rejudge 補評）
python dataset\regression_suite.py --rejudge   # 讀存檔重新評審（不重跑 GPU；含 S4）
python dataset\regression_suite.py --update-baseline   # 確認進步後抬高基準
python dataset\auto_gate.py --max-iters 3      # 外圈自動迭代：退件→修 driver→重評，直到全過或上限
```
退出碼：0=通過、1=退步、**2=評審不完整（限額打斷）**——生成已存檔，額度恢復後
`--rejudge` 補評即可（auto_gate 會自動記進度接續，Claude Pro 額度中斷不會賠掉整輪）。
任何指標低於基準（預設後端＝`dataset/regression_baseline_antigravity.json`）→ exit 1，**不可推送**。
**硬性守門 = 確定性 + 單輪評審（n≈13）+ altmethod（含 ε）+ Tier 4 後盾**：
確定性指標（洩漏/拒絕/單問句/升級/教學收尾）零容忍；judge_* 指標容忍 ε=0.05（小樣本逐項覆寫）。
**Tier 3 多輪對話（`judge_dialogue_*`，n=3）已降 advisory**（`ADVISORY_METRICS`）：照算照印、
不進 pass/fail——四輪實測全幅擺動、連現役 v9 都會被自己的基準判退（依據見 V11_VERDICT.md）。
計分卡與對話記錄存 `dataset/regression_scores/`（進 git，留版本歷史）。

### 新題目備課（先自己證對才教）
```powershell
python dataset\auto_reference.py --statement "證明 ..." --id NEW1 --out new_problem.json
# verified → 產出含 reference_proof + teach_steps 的題目檔，TutorDriver 直接可用
# unverified → 該題自動走同學模式（誠實降級，不硬教）
```

### 互動使用
```powershell
# 圖形介面（商品化 Demo，使用者自帶題目；需 Ollama 在線才有 grounded 備課）
conda run -n lora_project --live-stream python dataset\app.py          # http://localhost:7860

# 命令列逐輪互動（內建 50 題）
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

## 雙語化與守門重設計（2026-07-14~15，v7 adapter，計分卡 `regression_scores/`）

- **v7 = 中英平行資料重訓**（`src/`＋`src_en/` 共 800 例）；英文評估資產齊備
  （`held_out_en.json`、`hard_math_major_en.json`、`xdomain_problems_en.json`、`hint_ladders_en.json`）。
- **語言跟隨學生**：session 語言逐輪依學生訊息重判（≥12 非空白字元才切，防短訊息誤判），
  支援「英文題＋中文學生」與對話中途換語言。
- **收尾偵測 `_DONE_RE`**：學生致謝/宣告完成 → 回問保底停用，不再追問
  （guidance zh/en 皆升至 0.7333）；保底句三種措辭輪換、連輪不硬補。
- **守門容忍度校正 `JUDGE_EPSILON_OVERRIDE`**：小樣本 judge 指標須蓋過單題改判雜訊
  （s2_catch 14 題 ε=0.08、altmethod 3 題 ε=0.34），實測同輸入逐字相同仍會被評審翻面。
- **基準逐指標取高**：更新基準時保留較高舊地板，貫徹只升不降。
- **限流防呆**：`claude_call` 把「You've hit your limit」等限額訊息當可重試失敗——
  曾整場 Tier 3 的「學生」全是限額錯誤訊息。⚠️ **此「本 session 必須閒置」規則只在
  `JUDGE_BACKEND=claude` 才成立**（2026-07-22 起預設後端改為 `antigravity`＝agy／
  Gemini 3.6 Flash Medium，學生與評審皆走 Gemini、不碰 Claude 額度，本 session 可照常工作，
  見 v11 迭代 2026-07-24）。若手動切回 `JUDGE_BACKEND=claude` 則舊規則恢復（同帳號搶額度）。
- 修掉的雙語路徑 bug：`_STUCK_EN_RE` 漏 "can't do/completely lost"（walkthrough_en 0→1.0）、
  提示梯三處取用不一致（`_ladder()` 統一）、教學輪 `_regen` 誤截多問句結構。

## v9 部署（2026-07-18，4090 訓練，MAX_LEN=1024，計分卡 `2026-07-18T192050_22c38a7.json`）

- **v9 = 資料集不變、序列長度 640→1024 重訓**（Qwen3-4B-Instruct-2507，其餘超參同 v8）。
  動機：量測發現 MAX_LEN=640 截掉 26% 訓練樣本的**尾端**（對話收尾/審閱輪）——正是弱點 #7
  「完成後仍多講」的訓練面根因。在實驗室 4090（bf16，docker `server_train/docker-compose.v9.yml`）
  訓練 12.5 分鐘，eval_loss 1.052；adapter 分塊拷回本機、SHA256 一致。
- **最終守門本機 4-bit（部署精度）25/25 全綠 → 升 v9**。相對 v8 基準：英文單輪全面提升
  （altmethod_en 0.833→1.0＝弱點 #5 英文殘留根治、s2_catch_en 0.857→0.929、score_en 0.943→0.962、
  s1_structural_en 0.947→1.0），中英對話引導同升（guidance_zh 0.8→0.933、dialogue_math_ok 雙語 1.0）。
- **弱點 #7 收尾 bug 由 driver 根治**（非模型）：兩個確定性修復＋4 單元測試——
  (a) 已請學生寫證明後、他送出長訊息（≥120 字）→ 路由 `review`，不再被 writeup 保底叫他重寫剛寫的證明；
  (b) 實質宣告證完 → arm `done_closed`，之後非質疑/非提問的反思輪走新 `closed` 階段
  （禁新問題/替代法/延伸）。修復後 dialogue_guidance_en 由五輪穩定 0.7333 回升、guidance_zh 反超基準。
- **reveal_ok_zh 加雜訊容忍 ε=0.08**（與 s2_catch 同型：確定性生成、Claude 評審、n≈13）：
  同批 S2 文本五輪判分 0.833–0.942 從未再現基準 1.0（分母隨評審漏填 reveal 鍵浮動）＝純評審雜訊，
  基準 1.0 是幸運高點（弱點 #6）。**保守作法：只加容忍、不降基準 1.0**。
- 部署預設 adapter 已全面切 v9（各 runner env default），v8 目錄保留可 env 覆寫回退。
- 本機 6GB 卡教訓：連跑兩輪 suite 之間必須 `ollama stop`（Tier 4 後盾的 Ollama 模型駐留 3.2GB
  會使下一輪載入 4-bit 基底 segfault，兩次撞同一進度點才查出）。
- **本機 6GB 卡教訓 2（2026-07-22）**：裝了 Antigravity CLI（`agy`）後，**Antigravity IDE
  桌面應用**會啟一堆背景進程（實測 16 個，GPU 加速 UI 渲染）搶這張卡，導致 4-bit 載入
  在 30-40% segfault（連撞四次同位置才鎖定）。跑本機守門前先關 IDE：
  `taskkill /F /IM "Antigravity.exe"` + `"Antigravity IDE.exe"`。`agy` CLI 憑證存磁碟，
  IDE 關掉不影響評審呼叫。

## 評審後端：改用 agy / Gemini 3.6 Flash Medium 為預設（2026-07-22，`dataset/JUDGE_BACKEND_MIGRATION_PLAN.md`）

- Antigravity CLI（`agy`）已完整接入 `regression_suite.py` 抽象層並成為**預設評審**
  （`JUDGE_BACKEND=antigravity` + `AGY_MODEL="Gemini 3.6 Flash (Medium)"`）；
  Claude 保留為 `JUDGE_BACKEND=claude` 備援。達成脫離 Claude 額度依賴。
- **選型（四檔位、25 次壓測皆 100% 可解析）**：3.5 Flash Medium 判準對照憑空捏造誤殺、
  3.1 Pro 對話層 dialogue_math_ok_zh 兩輪 **0.333↔0.0 崩潰**且把引導誤判成數學錯 → 皆淘汰；
  **3.6 Flash Medium** 判準對照 2/2、zh 對話數學兩輪 **0.667↔0.667 逐字一致**、
  正確區分引導/數學、最快（6.5s）→ 採用。教訓：**模型層級高 ≠ 當裁判可靠**（Pro 反而崩）。
- 基準 `regression_baseline_antigravity.json` = 兩輪保守 **min**（吸收 en 對話/後盾 ±1 案
  的 n=3 本質雜訊，Claude 亦有）。不同裁判的尺不可互比，故獨立基準檔。
- 選型腳本留存：`test_agy_stability.py`（壓測）、`test_agy_rigor.py`/`test_agy_rigor2.py`
  （判準對照，一錯一對），未來換模型可快速重評。

## Driver hardening（2026-07-19，計分卡 `2026-07-19T154401_f4c1ee4.json`，25/25 全綠）

- **強困惑不受長度門檻限制**（`_STRONG_STUCK_RE`）：原本學生寫一段實質嘗試（>60 字）
  後才說「毫無頭緒/completely lost」不會被判定卡住、拿不到提示升級——這正是最挫折的
  時刻卻沒被接住。新增強困惑詞清單，不受長度限制直接判定 `is_stuck`。
- **改寫式重問偵測**（`_repeats_previous` 加 difflib 相似度 ≥0.85）：舊版只抓「逐字
  相同」，抓不到「換句話問同一題」。教學輪（`walkthrough`）除外——重講同一步是刻意
  行為，仍只用完全相同判定。
- 兩項為 driver 共用層修復，v9/v10 皆受益；新增 5 條單元測試（含修正兩個測試 stub
  因固定字串觸發新相似度守衛而誤判的問題）。
- 守門結果：英文對話與抓錯指標同步提升（dialogue_guidance_en 0.8667→1.0、
  s2_catch_en→1.0、altmethod_en→1.0），無退步。

## v10 資料集擴充與訓練實驗（2026-07-19~21，判定不採用，`eval_out_xdomain/V10_VERDICT.md`）

- **新增 `dialogues_journey.py`**（中英各 8 段，共 16 段，資料集 800→830 例）針對三項
  driver 蓋不住的訓練面弱點：
  - **#7 跨題型「剛學完但易卡住」旅程**（5 題，涵蓋極限/連續/微分/積分/級數）：
    fragile persona 多次卡住（含長訊息＋強困惑），助教逐級加深、連卡兩次才點名定理
    （不給算式），全程不代寫。
  - **#1 on-track 只肯定不奉送**（2 題）：學生方向正確時助教只肯定＋開放式提問，
    不指定任何具體代數操作。
  - **#9 拒絕大綱式洩漏**（1 題）：學生要求「先講完整思路」，助教一句婉拒＋
    一個問題還主導權，不順從。
- 訓練環境改用 **192.168.1.222**（.102 金鑰被拒，見 `COMMANDS.md`），GPU0（較空的那張，
  用前務必 `nvidia-smi` 確認即時用量，不能沿用 .102 的固定 GPU1 慣例）。
  13 分鐘訓練完成，eval_loss 1.042（略優於 v9 的 1.052），煙霧測試雙語通過。
- **adapter 傳輸教訓**：13 塊分塊中發現 1 塊（`chunk_am`）在這條 VPN 上損毀，
  逐塊 SHA256 比對定位、只重下壞塊即可，不必整批重傳；目錄裡也曾發現大小相符但
  SHA 不符的舊檔殘留，**絕不可只信任檔案大小，一律以 SHA256 為準**。
- **守門判定：不通過，v10 不升版，部署維持 v9。** 跑了 2 輪完整 suite + 3 次
  `--rejudge`（共 4 次獨立 Tier 2/3 評審）：確定性指標與單題評審（Tier 0/1/2）全數
  通過或優於基準；Tier 3 對話類分數本身雜訊很大、四輪間大幅擺動，但**質性內容跨四輪
  一致**——H5 案例（e^x>1+x，均值定理）在全部 4 次獨立生成中都出現「學生完成證明後，
  助教未經請求主動延伸到題目範圍外內容（x<0 推廣／替代證法）」，其中一輪這種即興延伸
  還**產生了新的數學錯誤**（誤稱「更弱命題」為「等價命題」）。判定為真實、可重現的
  收尾紀律退化，非評審雜訊。
- 830 例資料集本身內容經人工撰寫並對照參考解驗證，問題出在訓練後的模型行為交互作用
  （疑似 journey 資料「連續多輪深入追問」的訓練訊號讓模型收尾後更傾向順勢多教），
  非訓練資料有誤，保留在 `training-iter-v10` 分支供下次迭代參考；v10 adapter 保留於
  `dataset/qlora_adapter_v10/`（本機、gitignore）供後續分析。
  **後續**：v11 以同資料集重訓再試一次，同樣判退（見下節）。

## v11 迭代（2026-07-24，`eval_out_xdomain/V11_VERDICT.md`）：driver 修復上線、v11 adapter 判退

這一輪同時做了**兩件可分離的事**，結論相反，不要混為一談：

- **#11/#12 driver 修復（純確定性層，TDD）→ 乾淨通過、已上線**
  - **#11**：學生在證明完成後提出「帶問句的反思」時路由進 `closed` 並只簡短回答那一個問題，
    不藉機延伸；只有**斷言式質疑**（`_CHALLENGE_RE`，如「你錯了」）才落回一般流程重查。
    設計岔路 **Fork B**（使用者定案）：非斷言的「你確定嗎」由 closed 簡答即可，
    因為已完成的證明必經 review＋後盾複核。
  - **#12**：新增 `_TUTOR_DONE_RE`——**助教親口確認整個證明完成**時也 arm `done_closed`
    （原本只從學生宣告 arm，接不住此路徑）。措辭限「整個證明完成」等級以免 mid-proof 誤判。
  - 單元測試由 123 → **127 條 / 13 組**全過；三輪守門確定性指標零退步。
- **v11 adapter（830 例資料集重訓，eval_loss 1.044）→ 判退，部署維持 v9**
  假設「#11 能兜住 v10 的 H5 過度延伸」不成立：同問題重現（H5 延伸 6 輪、把學生拖進
  x<0 推廣），X4 另有模型級數學錯誤（誤稱單位矩陣為反例）。adapter 封存本機供分析。

### 守門校準（本輪最重要的產出，人工授權後實施）

四輪獨立守門顯示：確定性與單輪指標**全數穩定通過**，每輪的「退步」都落在**不同的**
輸入隨機雜訊指標——因為 Gemini 學生每輪把同一個 v9 帶進不同對話、surfacing 不同既有小瑕疵。

1. `judge_altmethod_zh` 基準 1.0 → **0.8333**（與 en 既有「容一案」一致，補上遺漏）。
2. `judge_dialogue_*` **全降 advisory**（math_ok 與 guidance、zh+en）：二元 × n=3，
   同一批文字光換評審就變動 ≥0.33、跨路徑 0.0↔1.0 全幅擺動，**沒有任何 ε 擋得住**。
   對話數學正確性改由 Tier 4 後盾把關，引導品質改由質性審閱。
3. 此設定下第四輪守門硬性全綠 PASS（計分卡 `2026-07-24T135954_868764f.json`）。

> 教訓延伸自弱點 #7：**把守門從「會誤殺的儀式」修成「可辯護的判準」，比追高分數重要**；
> 只在能可靠量測的層面棘輪。

## 商品化介面（2026-07-27，分支 `feature/product-ui`，`docs/code-review-product-ui.md`）

- `dataset/app.py`：Gradio **本機單人 Demo**，使用者自帶題目（題目 id 固定 `USER`，
  完全不查題庫）。流程＝貼題目（＋可選的證明嘗試）→ 逐階段串流顯示備課
  （PROVER 1/3 → VERIFIER → REPAIR → SEGMENTER）→ verified 走 grounded 教學、
  unverified 走同學模式 → 對話區逐輪引導。**Ollama 離線時所有題目都走同學模式**。
- 三層結構：純邏輯（`check_ollama` / `assemble_problem` / `opener_for`，`test_app.py` 可測）、
  備課串流（`_run_prepare`：背景執行緒＋佇列，worker `try/finally` 保證送出結束哨兵，
  備課例外不會讓 UI 永久卡死）、`build_ui`。
- 健壯性：進行中同時停用 `send_btn` 與 `msg_tb`（防 Enter 重送把單 GPU 佇列塞爆）、
  開場生成包 try/except。
- **Code review 第 2 次判定：可作為本機單人 Demo 上線，無 High/Medium 缺陷，總評 4.4/5**
  （F1/F2 已修）。尚存 F3–F6、N1–N3 皆 Low/Info，多與「未來對外多人產品化」相關；
  建議下次觸碰 `app.py` 時順手處理 F3（`check_ollama` 未關連線）與 N2。
- 未跑完整守門（未動 driver 與模型）；UI 互動層仍需真模型＋瀏覽器手動驗收四情境。

## 專案文件空間（Notion，2026-07-28）

專案架構與決策紀錄已整理進 Notion，入口頁「蘇格拉底式高等數學證明引導助教」
（`https://app.notion.com/p/3ab7ea3c6f3881329872ead09bf41b47`），底下 01–09 子頁：
系統架構／核心檔案地圖／資料集與訓練／品質守門／決策與判定紀錄／商品化介面／
分支地圖／已知弱點與下一步／常用指令。

- **內容源在 repo**：`docs/notion/00-09*.md`（Notion 頁面由此建立）。
- **權威來源仍是各分支的 `CLAUDE.md`**；Notion 是快照，同步節奏見入口頁「維護節奏」。
- 更新 Notion 時用 MCP 的 `notion-update-page` 改既有頁面，**不要重建新頁**（連結會失效）。
- Notion **teamspace 無法用 API/MCP 建立**，此「空間」是工作區頂層頁面。

## BoN＋驗證器（2026-07-18，判定不採用，`eval_out_xdomain/BON_VERIFIER_VERDICT.md`）

- 單張 4090 生成器（4B-2507+v8）＋驗證器（4B-Thinking-2507）共存，選擇性驗證含式子的回覆。
- 校準後 v2 prompt 抓錯 3/4、誤殺 0/3；但**實戰 273 輪僅 1 輪真的抓錯重生成（0.4%）**——
  微調＋driver＋後盾已把可驗證的數學錯誤壓到極低，驗證器邊際效益無法量測，卻多 8GB 顯存與延遲。
  程式碼與校準 harness 保留（`VERIFY=0`＝現行部署），未來換非同源強驗證器可重啟。

## 已知弱點（下輪迭代方向）

1. ~~細膩雙重錯誤解剖、審閱「察覺對但解釋錯」~~ → 已由審閱後盾解決（2026-07-12，
   e2e 驗證 H3/X2/X4 全改善）；殘餘依賴：Ollama 需在線，離線時降級回原行為。
2. ~~學生明確困惑（長訊息＋強困惑詞）被長度門檻擋掉、拿不到提示升級~~ → 已由
   `_STRONG_STUCK_RE` 根治（2026-07-19，driver hardening，不受長度限制）。
3. ~~學生卡住時 tutor 換句話重問同一題（逐字比對抓不到）~~ → 已由 difflib 相似度
   ≥0.85 偵測根治（2026-07-19，教學輪重講除外）。
4. M4 型細膩跳步（宣告聽起來完整時不驗證）→ 可考慮把「宣告完成」也路由給後盾複核。
5. on-track 奉送、等級 2 附算式 → 已由 driver 三項防護緩解（2026-07-11）；
   訓練面補強樣本已寫入 `dialogues_journey.py`（2 題），但 v10、v11 兩次整體重訓守門
   皆未通過（見上方 v10／v11 判定），此弱點的訓練面根治尚未達成，資料保留供下次迭代。
   **下輪建議**：只取 on-track 與 outline-refusal 樣本做小幅增量訓練，先不放 journey
   旅程對話（兩次判退共同指向它的「連續多輪深入追問」訓練訊號）。
6. ~~不順學生的替代證法（英文殘留）~~ → v9（MAX_LEN=1024 重訓）**英文亦根治**
   （altmethod_en 0.833→1.0，守門通過，2026-07-18）。中文自 v8 已穩定 6/6。
7. ~~S4 僅 3 案例~~ → 已擴到 6 案例（2026-07-16）。**教訓：輸入隨機的指標（S4 學生方案、
   Tier 3 對話由 Claude 即興生成）基準不可棘輪到幸運最大值**，應設在可辯護的真實水準
   （altmethod_en 基準 0.8333 = 容一案），否則正常跑分必然誤判退步。
8. ~~學生說「懂了」後助教多講一段延伸講解（`_DONE_RE` 只擋追問型、蓋不住講解型）~~ →
   v9 由 driver 兩修復根治（2026-07-18）：寫完證明→review、宣告證完→`closed` 收尾階段
   （禁新問題/替代法/延伸）。dialogue_guidance_en 0.7333→回升、guidance_zh 反超基準。
9. 缺「剛學完微積分但容易卡住」跨題型多輪對話 → 訓練樣本已寫入 `dialogues_journey.py`
   （5 題跨主題旅程對話），但 v10／v11 整體重訓守門皆未通過，根治尚未達成，資料保留供下次迭代。
10. 拒絕大綱式洩漏（學生要求先講完整思路）→ 訓練樣本已寫入 `dialogues_journey.py`
    （1 題婉拒＋還主導權），同上，隨 v10／v11 整體未通過，待下次迭代。
11. ~~學生完成證明後提出帶問句的反思會跳出 `closed`，完全依賴模型自律~~ → 已由
    **#11 driver 修復**根治（2026-07-24，Fork B：一律進 closed 簡答，只有斷言式質疑跳出）。
12. ~~助教自己確認證明完成時 `done_closed` 沒 arm（只從學生宣告 arm）~~ → 已由
    **#12 `_TUTOR_DONE_RE`** 根治（2026-07-24，措辭限「整個證明完成」等級防 mid-proof 誤判）。
13. **多輪引導品質目前沒有可靠的量化守門**：`judge_dialogue_*` 已降 advisory（n=3 雜訊
    無 ε 可擋），現階段靠 Tier 4 後盾（數學正確性）＋人工質性審閱。方法層可選方向：
    多輪聚合（中位數／多次 rejudge 平均）再對基準，或加大 n。**在此之前，任何採用/判退
    決策都不可用對話類分數當依據**（v10 判退是靠「質性內容跨四輪一致」認定的）。
14. **商品化介面的 Low/Info 項未清**：F3（`check_ollama` 未關連線）、N2（錯誤 yield 樣板
    重複、`opener_for` 重算）等；且 UI 互動層四情境仍需真模型＋瀏覽器手動驗收
    （自動測試只涵蓋純邏輯）。詳見 `docs/code-review-product-ui.md`。
