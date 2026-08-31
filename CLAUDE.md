# week3 — 蘇格拉底式高等數學證明引導助教

本 repo 只保留**一個方法**：手寫 grounded 資料集 QLoRA 微調 Qwen3-4B（`qlora_adapter_v9`，雙語）
＋ 對話驅動程式（`tutor_driver.py`）。這是經過 v2→v6 六輪迭代與三路線正面對決後判定的
最佳部署形態（判定依據：`dataset/eval_out_final/FINAL_VERDICT.md`）。

**現行部署形態 = `qlora_adapter_v9` + 含 #11/#12 修復的 driver**。v10、v11 兩輪整體重訓
皆守門判退（同一個收尾紀律退化重現），**不要誤以為版號越新越該用**。
v10／v11 的 adapter 權重已於 2026-08-07 清理時刪除（本機只留現役 v9），判退依據與行為紀錄保留在 `eval_out_xdomain/V10_VERDICT.md`／`V11_VERDICT.md`。

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
              │  · 三條正交控制線：phase（guide/walkthrough/review/closed）＞ turn_action ＞ level
              │  · stuck counter（0/1/2 → Level 0/1/2；第三次連續卡住進 walkthrough）
              │  · Level 2 只給一個可執行微支架，可含必要公式但不代寫後續推導
              │  · walkthrough 逐步教學（確定性模板：一步一確認、教完仍要學生自寫證明；
              │    答對前進，答錯揭答前進，審閱不可用則保留原步；此階段不呼叫生成模型）
              │  · 審閱/糾錯輪 ──► 審閱後盾（review_backstop.py，Ollama 思考型找碴）
              │                    缺漏清單注入 system；不可用時保守停留、不假裝通過（REVIEW_BACKSTOP=0 關）
              ▼
         qlora_adapter_v9 + Qwen3-4B（4-bit nf4）＋ grounded system（含 <REFERENCE_PROOF>）
              │
              ▼
         後處理：單問句截斷、洩漏 15-gram 檢查、on-track 防奉送、
         Level 2 單一微支架限制、回問保底（命中→加強指示重生成）
```

2026-08-31 的 level／phase 審查與待修項目見 `docs/code-review-level-phase-2026-08-31.md`。

**設計鐵律**（v4→v6 三次驗證的教訓）：離散決策（何時升級、何時換階段）交給程式碼；
內容拿捏（提示深度、審閱重點）交給預寫內容（參考解、hint ladder）；模型只負責數學與語氣。
**混合架構延伸**（2026-07-12）：即時數學判斷（審閱草稿找缺漏）交給思考型模型
（S2 4.75 的證據），微調模型只把缺漏清單包裝成引導語氣——判斷與說話分工。

---

## 目錄結構

```
week3/
├── dataset/                          # ★ 一切核心
│   ├── src/ + src_en/                # 手寫內容源碼（50 題 + 中英平行對話，Claude 撰寫並驗證）
│   ├── build.py / validate.py / test_dataset.py     # 建置與驗證
│   ├── problems.json / train.jsonl / val.jsonl       # 建置產出（747/83＝830 例；v9 訓練用的是不含 journey 的 814）
│   ├── hint_ladders.json             # 分級提示內容（driver 等級 2 用；只 17 題，其餘靠備課 LADDER 生成）
│   ├── tutor_driver.py               # ★ 對話驅動程式
│   ├── review_backstop.py            # 審閱後盾（Ollama 思考型找碴，可降級）
│   ├── auto_reference.py             # ★ 自動備課管線（PROVER→VERIFIER→REPAIR→SEGMENTER→LADDER）
│   ├── interactive_turn.py           # 逐輪互動 CLI（維護 session 狀態檔）
│   ├── app.py / test_app.py          # ★ Gradio 商品化介面（本機單人 Demo）／其純邏輯測試
│   ├── qlora_adapter_v9/             # ★ 部署 adapter（權重不進 git）
│   ├── held_out.json / held_out_attempts.json / hard_math_major.json / adv_test_problem.json  # 評估題
│   ├── xdomain_problems.json         # 跨領域評估題（離散×3 + 線代×3，XDOMAIN_ADAPTER 覆寫）
│   ├── eval_heldout_v3.py            # 三情境回歸（裸模型，HELDOUT_ADAPTER 覆寫）
│   ├── eval_hard.py                  # 分布外難題（HARD_ADAPTER 覆寫）
│   ├── eval_final_driver.py          # 部署形態三情境（FINAL_ADAPTER 覆寫）
│   ├── eval_xdomain.py               # 跨領域遷移三情境（部署形態）
│   ├── eval_final_ollama.py          # Ollama 對照（歷史對決用，需 Ollama）
│   ├── test_driver_unit.py / test_driver_integration.py / test_driver_phase.py  # driver 測試
│   ├── test_phase_routing.py         # ★ 真實對話回放驗階段路由不變式（Tier 0，無 GPU）
│   ├── test_backstop.py / eval_backstop_e2e.py      # 後盾準確度（需 Ollama）/ 端對端對照
│   ├── test_auto_reference.py / eval_svt_e2e.py     # 備課盲測 / walkthrough+同學模式端對端
│   ├── regression_suite.py           # ★ 推送前守門（預設 agy/Gemini 當評審+學生；退步即 exit 1）
│   ├── auto_gate.py                  # 守門外圈自動迭代（退件→修 driver→重評）
│   ├── measure_gate_noise.py         # ★ 量守門指標的純評審雜訊 vs ε（判退時先跑這支）
│   ├── measure_stuck_detection.py / stuck_labels.json  # is_stuck 準確度量表 + 251 則標註
│   ├── regression_baseline_antigravity.json  # ★ 現行基準（預設評審後端；只升不降）
│   ├── render_transcripts.py         # 把守門對話轉成可讀 md（人工檢視用）
│   ├── regression_baseline.json / regression_scores/  # Claude 後端基準與各版本計分卡
│   │                                 #   ⚠️ regression_scores/*_dialogues.json 是
│   │                                 #      test_phase_routing.py 的回放語料，不可刪
│   └── eval_out_final/ / eval_out_v6/ / eval_out_hard/ / eval_out_driver/ / eval_out_xdomain/  # 現行報告
├── learn_path/socratic_tutor/        # 訓練引擎（僅 4 檔）
│   ├── common.py                     # 模型與路徑設定（env 覆寫）
│   ├── train_qlora.py                # QLoRA 訓練主程式
│   ├── download_chunked.py           # 分塊下載基底模型（VPN 節流對策）
│   ├── test_4bit_load.py             # 4-bit 載入煙霧測試
│   └── qwen3_4b/                     # 基底權重（~8GB，不進 git）
├── server_train/                     # 伺服器端訓練管線（Dockerfile / compose / workspace）
├── .claude/skills/pre-push-check/    # /pre-push-check skill：推送前守門流程（進版控）
├── docs/
│   ├── code-review-product-ui.md     # 商品化介面 code review（第 2 次，覆蓋前版）
│   ├── code-review-walkthrough-gradable.md  # 逐步教學可評分化批次 code review（2026-08-07）
│   ├── notion/                       # Notion 專案空間的內容源（00–09，見下方「專案文件空間」）
│   └── superpowers/                  # 設計 spec 與實作計畫
├── 專案架構設計.md                     # ★ 架構的權威來源（設計問題/鐵律/各層職責/取捨）
├── update.md                         # 與 training-iter-v11 的行為差異對照
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
python dataset\test_driver_unit.py                                        # 純邏輯，無 GPU（313 條斷言 / 32 組）
#   ⚠️ 斷言計數用 grep -cE "^  (✓|✗) "；用 grep -c "✓\|✗" 會多算結尾的總結行
python dataset\test_phase_routing.py                                      # 真實對話回放驗階段路由（無 GPU，299 場存檔）
python dataset\render_transcripts.py                                      # ★ 把最新一輪守門的對話轉成可讀 md（人工檢視用）
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
python dataset\measure_gate_noise.py           # ★ 判退時先跑：量各指標的純評審雜訊 vs ε
python dataset\measure_stuck_detection.py      # is_stuck 準確度（251 則真實訊息標註，可重跑）
```
退出碼：0=通過、1=退步、**2=評審不完整（限額打斷）**——生成已存檔，額度恢復後
`--rejudge` 補評即可（auto_gate 會自動記進度接續，Claude Pro 額度中斷不會賠掉整輪）。
任何指標低於基準（預設後端＝`dataset/regression_baseline_antigravity.json`）→ exit 1，**不可推送**。
**硬性守門 = 確定性 + 單輪評審（n≈13）+ altmethod（含 ε）**：
確定性指標（洩漏/拒絕/單問句/升級/教學收尾）零容忍；judge_* 指標容忍 ε=0.05（小樣本逐項覆寫）。
**advisory（照算照印、不進 pass/fail）＝ `judge_dialogue_*`、`judge_backstop`、
`dialogue_ladder_used_*`**（見 `ADVISORY_METRICS`）。
計分卡與對話記錄存 `dataset/regression_scores/`（進 git，留版本歷史）。

⚠️ **守門本身的已知限制（2026-08-02 量測，`measure_gate_noise.py`）**——判讀結果前必讀：
- **9 個硬性 judge 指標中有 8 個的「純評審雜訊」≥ 自己的 ε**，亦即沒有任何真實退步時
  也可能判退。量法：取 14 輪同後端、Tier 1/2 回覆**逐字全同**的守門（生成端零變化），
  差異即評審自身的不確定性。實測 `s2_catch_zh` 0.159、`score_zh` 0.135、`reveal_ok` 0.115…
  只有 `math_ok_zh`（0.0385）低於 ε。**判退時先跑 `measure_gate_noise.py` 對照，
  再決定是真退步還是抽到雜訊低點。**
- ⚠️ **放寬 ε 不是解法**：`s2_catch_zh` 共 14 題，真實「多錯 2 題」= 0.143 比雜訊 0.159 還小，
  任何蓋得住雜訊的 ε 都會同時放行真實退步。
- **Tier 1/2 是單輪探針**（S1/S2/S3 只呼叫 `start()`），測不到多輪行為：連續 6 輪守門、
  期間改了守衛鏈順序／`is_stuck`／`stuck_count` 語意，104 筆回覆**始終 104/104 逐字相同**。
  多輪路徑目前只由 Tier 0（`test_driver_unit.py` + `test_phase_routing.py`）把關。
- 承上，判退時的第一個動作應該是**逐字比對本輪與上輪的 `*_replies.json`**：全同 ⇒
  生成端沒變 ⇒ 所有 judge_* 波動都是評審雜訊。

### ⚠️ 未解：長時間連跑後守門會在 walkthrough 探針卡死（2026-08-04，兩次重現）
連續跑多輪 2 小時守門後，Tier 1 的 walkthrough 探針處出現**進程層死結**，兩次重現、
同一位置（log 停在 `[E4/zh] 升級 ✓` 之後）。判定依據與排除項：
- **CPU 時間 40–45 秒內增加 0.0–0.1 秒** ← 決定性證據（在算的話會明顯增加）
- GPU 使用率連續 8 次取樣 0%，但仍佔著 4231 MiB；顯卡本身健康（45°C、無 Xid、
  throttle 原因為 `GpuIdle`）
- 進程**零網路連線** ⇒ 排除卡在 Ollama（`segment_proof` 的 300s timeout 也早該觸發）
- 該段程式碼近期未修改（`ff828c5` 只新增 `tier1_multiturn`，沒動 `tier1()`）
- 49 個執行緒全部靜止 ⇒ 疑似 CUDA/PyTorch 層死結

**排除方式**：`Stop-Process -Force` 殺掉主進程即可釋放顯存（會回到 0 MiB、無殘留
compute app），之後重跑。但第二次重跑仍卡在同一處，所以殺進程只是清場、不是根治。
**尚未確認的假設**：這台機器連續跑了多輪 2 小時守門，疑似長時間 GPU 負載後的
驅動／執行期不穩。建議讓機器休息後再跑，而不是立刻重試。

**判斷卡死 vs 只是慢的正確方法**（本 session 學到的）：不要只看 log 行數或單次
GPU 取樣——walkthrough 探針約 16 次生成 × 每次約 4 分鐘，整段 60 分鐘完全不輸出，
單次取樣很容易抓到空檔而誤判。**用 CPU 時間增量**：40 秒內 <0.5 秒＝卡死，
>5 秒＝在算。

### Tier 2 多次評審取共識（2026-08-02）
`_judge_item_consensus()`：每則探針評審 `JUDGE_SAMPLES=3` 次，布林多數決、數值中位數。
成本 38 → 114 次評審呼叫（約 +8 分鐘）。`JUDGE_SAMPLES=1` 還原舊行為。
**動機是降低變異本身，而不是加大容忍**（見上一則的「放寬 ε 不是解法」）。
⚠️ **效果尚未證實**：兩輪共識實測的平均兩兩差距 0.0411 → 0.0390，僅降 5%，
n=2 完全落在雜訊內，且 `s2_catch_en`／`altmethod_zh` 反而變大。保留它的理由是
「多數決降低布林指標變異屬二項分佈性質（理論無爭議）＋ 成本低 ＋ 實測零壞處」，
**不是「已驗證有效」**。需再累積 3–5 輪共識資料才能定論，隨日後開發自然累積即可。
教訓：初版比較用「單次 14 輪的極差」對「共識 2 輪的單一對差」，極差隨樣本數增大，
必然偏向共識、得出「7 項明顯收斂」的假成果；**比較不同樣本數時必須用平均兩兩差距**。

### `judge_backstop` 降 advisory 的依據（2026-08-02，人工授權）
Tier 4 拿**寫死的草稿字串**直接呼叫 `find_gaps()`，完全不經過 `TutorDriver`，輸入固定；
即使如此，同一組輸入連跑三次得 **0.3333 / 0.6667 / 0.0**——涵蓋整個值域。
不確定性有兩層（Ollama 思考型生成缺漏清單、評審判定是否命中埋錯）× n=3，
一案翻面 = 0.333，無 ε 可擋。與 `judge_dialogue_*` 同型，處置一致。
後盾品質改由 `test_backstop.py`（人工檢視）與 `eval_backstop_e2e.py` 把關；
要恢復硬性把關需先加大 n（多寫埋錯案例）。

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

- **v7 = 中英平行資料重訓**（`src/`＋`src_en/` 共 814 例＝733/81）；英文評估資產齊備
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
- 部署預設 adapter 已全面切 v9（各 runner env default）。
  ⚠️ v8 目錄原本保留作 env 覆寫回退，已於 2026-08-07 清理時刪除；現在本機只有 v9，`FINAL_ADAPTER` 等環境變數仍可覆寫但沒有其他版本可指。
- 本機 6GB 卡教訓：連跑兩輪 suite 之間必須 `ollama stop`（Tier 4 後盾的 Ollama 模型駐留 3.2GB
  會使下一輪載入 4-bit 基底 segfault，兩次撞同一進度點才查出）。
- **本機 6GB 卡教訓 2（2026-07-22）**：裝了 Antigravity CLI（`agy`）後，**Antigravity IDE
  桌面應用**會啟一堆背景進程（實測 16 個，GPU 加速 UI 渲染）搶這張卡，導致 4-bit 載入
  在 30-40% segfault（連撞四次同位置才鎖定）。跑本機守門前先關 IDE：
  `taskkill /F /IM "Antigravity.exe"` + `"Antigravity IDE.exe"`。`agy` CLI 憑證存磁碟，
  IDE 關掉不影響評審呼叫。

## 評審後端：改用 agy / Gemini 3.6 Flash Medium 為預設（2026-07-22）

- Antigravity CLI（`agy`）已完整接入 `regression_suite.py` 抽象層並成為**預設評審**
  （`JUDGE_BACKEND=antigravity` + `AGY_MODEL="Gemini 3.6 Flash (Medium)"`）；
  Claude 保留為 `JUDGE_BACKEND=claude` 備援。達成脫離 Claude 額度依賴。
- **選型（四檔位、25 次壓測皆 100% 可解析）**：3.5 Flash Medium 判準對照憑空捏造誤殺、
  3.1 Pro 對話層 dialogue_math_ok_zh 兩輪 **0.333↔0.0 崩潰**且把引導誤判成數學錯 → 皆淘汰；
  **3.6 Flash Medium** 判準對照 2/2、zh 對話數學兩輪 **0.667↔0.667 逐字一致**、
  正確區分引導/數學、最快（6.5s）→ 採用。教訓：**模型層級高 ≠ 當裁判可靠**（Pro 反而崩）。
- 基準 `regression_baseline_antigravity.json` = 兩輪保守 **min**（吸收 en 對話/後盾 ±1 案
  的 n=3 本質雜訊，Claude 亦有）。不同裁判的尺不可互比，故獨立基準檔。
- 選型當時的一次性腳本（壓測 `test_agy_stability.py`、判準對照 `test_agy_rigor*.py`）與
  遷移計畫文件已於 2026-08-07 清理時刪除；**選型結論保留在本節與 `regression_suite.py`
  開頭的註解**。未來要換評審模型時，依該註解記的方法重寫壓測即可
  （25 次連續呼叫測可解析率 ＋ 拿一錯一對的已知案例測判準）。

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

- **新增 `dialogues_journey.py`**（中英各 8 段，展開後資料集 814→830 例）針對三項
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
  `dataset/qlora_adapter_v10/`——adapter 權重已於 2026-08-07 清理時刪除（本機只留現役 v9）——判退依據與行為紀錄留在文件裡，要重現需依 CLAUDE.md 的超參重訓。
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
  x<0 推廣），X4 另有模型級數學錯誤（誤稱單位矩陣為反例）。adapter 權重已於 2026-08-07 清理時刪除（本機只留現役 v9）——判退依據與行為紀錄留在文件裡，要重現需依 CLAUDE.md 的超參重訓。

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

## 真實對話稽核與收尾修復（2026-07-29，`update.md` 的四項觀察）

一次 A2/A3 真實對話留下四項問題，逐項追到程式碼後**兩項已修、兩項確認是架構缺口未修**：

- **F3（本分支引進的回歸，已修）**：`_CLAIM_DONE_RE` 分支在「審閱結果還沒產生」時就
  arm `done_closed`，而 #11 又拿掉了 `_QMARK_RE` 例外 → 學生針對缺漏的追問被路由進
  `closed`（助教被指示「已完成、不要再問」），**糾錯就此中斷**。改為交稿當輪不 arm。
- **F1（已修）**：`done_closed` 改由**審閱通過訊號**決定——審閱輪的回覆不含問句＝助教
  沒再要求修正＝過關。原本靠 `_TUTOR_DONE_RE` 比對助教散文，實測 8 種自然措辭只命中 2 種
  （「邏輯無縫，你已經完全掌握」「證明已經完成」皆漏接），漏接就會落回一般引導輪、
  補上 `_FALLBACK_QS[0]`「那你覺得，下一步該從哪裡下手？」——log 裡那句逐字就是它。
  措辭正則仍保留給「對話中途自然證完」的路徑，並補三道閘（含問句／否定式／只講某一步不算）。
- **F2（已修）**：`interactive_turn.py` 舊版只存 4 個欄位，`done_closed`／`fb_idx`／
  `walk_*` 每輪歸零 → **#11/#12 的收尾修復在逐輪 CLI 上等於沒上線**，保底句永遠是同一句、
  「連兩輪不硬補」守衛永遠失效、逐步教學卡在第一步。改為 `TutorDriver.dump_state()/
  load_state()` 整包快照（新增狀態欄位自動跟著存）。`app.py` 因 driver 常駐不受此影響。
- **F6（已修）**：新增 `is_overpraising()` 稱讚校準守衛——(a) 後盾已回報缺漏、回覆又不含
  問句地說「完全正確／無懈可擊」＝錯誤背書；(b) 訓練集出現 0 次的誇飾腔（邏輯無縫／
  嚴謹性之魂／超過大多數）＝基底模型漂移。命中即重生成。局部肯定＋問句點缺漏不誤殺。
- **F4／F5（未修，架構缺口）**：見已知弱點 #15／#16。這才是「Tutor 沒抓到學生錯誤、
  自己講錯」的根因，driver 補丁蓋不住。

單元測試 127 → **150 條 / 14 組**全過。**完整守門通過**（計分卡
`regression_scores/2026-07-29T092207_05640eb.json`，exit 0）：確定性指標中英共 44 項全綠，
且 Tier 1/2 回覆與基準輪 `868764f` **逐字比對 104/104 相同**（greedy 解碼，同輸入同輸出）
＝本批改動對固定輸入的生成行為零影響，所有 judge_* 上下波動皆為評審雜訊。

## 收尾三個路徑補完（2026-07-29 第二批，源自守門對話實例）

上批修好的是「有明確訊號」的兩條路徑；完整守門的 6 場對話顯示 4 場仍出現
「證明完成後助教多餘追問」（基準輪同樣存在，非新引進）。逐場追出三個獨立缺口：

- **H5 型（助教自行要求交稿）**：driver 只在 `_UNDERSTOOD_RE` 命中時才記 `writeup_asked`，
  但模型常自己開口請學生寫證明（學生用「這樣就算證完了嗎」表達理解時尤其如此）。
  沒記下來 → 151 字草稿走不到交稿分支 → 不進 review → 拿不到審閱通過訊號。
  修法與 #12 對稱：掃助教上一則回覆命中 `_TUTOR_ASK_WRITEUP_RE` 即補記，
  並以 `_REFUSE_WRITEUP_RE` 反向閘擋掉拒絕洩漏輪的「不能寫出完整證明」。
- **X4 型（全程沒有交稿步驟）**：證明在一問一答中走完，助教下總評式肯定卻無問句 →
  舊行為補通用追問。改為三道閘同時成立時（對話 ≥6 則、學生上一則 ≥80 字、
  回覆命中 `_ENDORSE_RE`）補 `WRITEUP_NUDGE` 請他交稿，接回 review→收尾這條既有路徑；
  閘沒過就維持通用追問，避免 mid-proof 的單步肯定被誤判成整份完成。
- **時序缺口**：`_TUTOR_DONE_RE` 的偵測放在 `step()` 開頭（掃上一則），而保底句是本輪
  結尾補的 → 助教「宣告完成」與「追問下一步」出現在同一則回覆。抽出
  `confirms_whole_proof_done()` 供兩處共用，本輪生成後立即 arm，補句前就生效。

真實對話重放驗證（剝除原文中上一輪附加的保底句後重跑確定性層）：H5/X4/M2 三場
**末輪 guards 全部清空**，X4 的通用追問由 2 次降為 0 次。單元測試 150 → **162 條 / 17 組**。
⚠️ 這批改動會改變階段路由（system 指示隨之不同），**不像上批可證明對生成零影響**，
推送前需重跑一次完整守門。

## 守衛鏈五項缺陷修復＋守門覆蓋補強（2026-08-01，分支 `fix/driver-guard-hardening`）

對 `feature/product-ui` 做 code review，逐項以可執行證據確認後修復（全程 TDD，先看
24 條新斷言以正確理由失敗才實作）。單元測試 162 → **186 條 / 22 組**。

- **重生成繞過內容防護（最嚴重）**：回問保底與重複偵測的 `_regen` 結果**直接落地**，
  不再經洩漏／防奉送／禁算式／稱讚校準——全檔唯一未經內容檢查就送到學生面前的路徑。
  實測可讓一段逐字複製參考解、結尾帶問號的回覆完整落地（`guards` 只記到 `no_question`），
  正好架空招牌的 S3 抗洩漏。修法：四道防護抽成 `_content_guards()`，每次重生成後再跑一次。
  併修順序缺陷：`repeat` 原排在回問保底之後，其重生成會把剛補上的保底問句整個蓋掉。
- **`_TUTOR_ASK_WRITEUP_RE` mid-proof 誤命中（`a9b3abc` 引進的回歸）**：「你能自己試著
  寫出這個證明的第一步嗎」等常態引導都會誤記 `writeup_asked`，兩個下游傷害實測皆重現——
  推導途中的長訊息被當完整草稿送 review（後盾拿半成品找碴）；`writeup_asked` 是單向閂，
  誤設後真正該交稿時再也進不了 `writeup_request`。改用 `asks_for_full_writeup()`，
  措辭須帶「完整／整份／整個」整份範圍。
- **`_REFUSE_WRITEUP_RE` 過寬**：回覆任何位置出現 `不能/不會/無法` 就整條否決，
  實測 4 句合理交稿請求誤殺 2 句。改為只看命中片段所在的**子句**。
- **特殊 phase 消耗提示梯**：`phase` 有值時 system 注入的是階段指示、根本沒有提示內容，
  卻照樣推進 `ladder_idx`；更糟的是 walkthrough 進入條件為 `ladder_idx >= 梯長`，實測
  一串糾錯輪就能把梯吃光，**學生一條提示都沒拿到就被推進逐步教學**。改為只在
  `phase is None` 時推進。（同一份 code review 另提兩點——walkthrough／peer 也會
  消耗——**實測不成立**，早已由 `not walkthrough and not peer` 擋掉。）
- **同學模式沒有背書守衛**：`is_overpraising` 被關在 `if not peer` 內，同儕模式完全不生效
  ——正是 v11 人工實測記下的「首輪誠實聲明有效、之後大量『完全正確／你已完全掌握』」
  的根因。新增 `peer_endorse` 守衛（`_ENDORSE_RE`／`_FLOURISH_RE`）。

**完整守門 exit 0**（計分卡 `2026-08-01T193728_8be3255.json`）：25 項硬性指標全 ≥ 基準，
10 項確定性指標維持 1.0。⚠️ 但 Tier 1/2 的 **104 筆回覆與上輪逐字比對 104/104 相同**
＝本批對固定探針零影響，所有 `judge_*` 波動皆評審雜訊，**不可當成修復有效的證據**。

### `test_phase_routing.py`：用真實對話回放補守門覆蓋（本輪最重要的產出）

`test_driver_unit.py` 的每句台詞都是人寫的——能證明狀態機邏輯正確，證明不了**真模型
講出來的話會不會踩中那些正則**（收尾／交稿／完成宣告偵測全在比對散文，稽核 F1 就是
實測 8 種自然措辭只命中 2 種）。新測試把 `regression_scores/*_dialogues.json` 累積的
**243 場真實守門對話**（42 輪存檔）回放進確定性層，檢查 5 條不變式，納入 Tier 0（無 GPU）。

靈敏度已驗證（還原修復即觸發）：還原 F3 → V3 抓到 **14 筆**；拿掉 `done_closed` 閘 →
V3/V4 各抓到 2 筆，證據逐字重現當年的 bug（「證明到此完成。…那你覺得，下一步該從哪裡下手？」）。
> 教訓：**V4 初版是空的**——它用 `confirms_whole_proof_done` 判斷，而該函式本身就排除
> 帶問句的回覆，永遠不可能觸發。每條不變式都必須實際還原一次 bug 驗證會響，否則只是裝飾。

**⚠️ 量測到的守門盲區（比修復本身更值得記）**：這 243 場對話的階段分佈為
`None 1210 / review 134 / rectify 134 / closed 83 / writeup_request 18 / refuse_leak 3`，
而 **`ladder_idx` 最大值 = 0——多輪對話中提示梯從未被消耗過一次**。
（更正：升級路徑本身 **Tier 1 有測**——`escalation_*` 用罐頭的連兩則卡住訊息斷言
`level==2 且 ladder_idx==1`，`walkthrough_*` 也測進入與收尾，兩者都是硬門。
真正沒被覆蓋的是**真實多輪對話流**：Tier 3 的三個 persona 太會答，`is_stuck` 在
1339 則真實學生訊息中只命中 22 則（1.6%）且從未連續兩輪，所以升級機制在
realistic 情境下從未啟動過。`a9b3abc` 與提示梯誤耗都活在這個交錯地帶。）

### 補強：重度卡關型 persona（2026-08-01）

`DIALOGUE_CASES` 加入第 4 個 persona（題目 M1，逐點/一致收斂）。措辭經 agy 實測校準
至中英各 3/3 觸發 `is_stuck`——關鍵是那句「**除非助教講出定理名稱，否則答不出來**」，
少了它 LLM 學生會自己推出答案而跳出卡住狀態（實測 en 只有 1/3、且不連續）。

**刻意不做成硬性指標**：學生由 LLM 即興扮演＝輸入隨機，連學生生成失敗都會讓指標歸零，
正是弱點 #7「輸入隨機的指標不可棘輪」。改為 advisory 的 `dialogue_ladder_used_*`
＋每場印出升級軌跡；真正的把關留給 `test_phase_routing.py`——這些對話會寫進存檔，
之後由 Tier 0 的確定性不變式永久複查。

**守門結果（`2026-08-02T004147_e2c7b52.json`，exit 0）**：硬性指標零退步，
Tier 1/2 回覆再次 **104/104 逐字相同**（`is_stuck` 改動對固定探針零影響）。
新 persona 中英皆 `ladder_idx=2 / max_level=2 / walkthrough=True`
——**真實多輪對話首度走完整條升級路徑**，`test_phase_routing.py` 的語料因此首度出現
walkthrough 輪與等級 2 提示輪，V1 提示梯守恆不再是空跑的不變式。

### ⚠️ 新弱點 #17：學生持續卡關時助教退化成重複迴圈（新 persona 首跑即抓到）

M1 中英兩場 `guidance` 皆被評為 **1 分**（`math_ok=True`，純教學失敗非數學錯誤），
兩份獨立評審指向同一件事。原始對話（`M1/zh`）第 8/10/12 輪**逐字相同**：

> 也許你該先查查這個序列的圖形長什麼樣子，再試著猜它的逐點極限。 那你覺得，下一步該從哪裡下手？

學生連說「毫無頭緒」，助教卻叫他「自己去查圖形」並反問「下一步該從哪裡下手」。
回放逐輪 guards 查出機制，**正是 code review 列為 M2、當時刻意未修的兩項**：

1. **保底句稀釋相似度**：上一輪被補了 `_FALLBACK_QS` 後，本輪逐字相同的回覆與它的
   difflib 相似度掉到 **0.768 < 0.85 門檻** → `repeat` 根本沒觸發（snap 5）。
2. **重生成不複驗**：`repeat` 真的觸發時（snap 6），`_regen` 回傳的仍是同一段文字，
   而程式碼**無條件採用**、不再檢查是否仍在重複。

影響面：這正好打在**最需要幫助的學生**身上（提示梯用盡、進入逐步教學者）。
修法方向（下輪）：比對前先剝除 driver 自己補的保底句／nudge；重生成後複驗，
仍重複就換保底措辭或推進 `walk_idx`。

**副產品：修掉一個英文 driver bug。** 校準 persona 時實測發現 `_STUCK_EN_RE` 要求
`don't know` / `not sure` **連續**，而口語極常見的 "I don't **even** know" /
"I'm not **really** sure" 會被副詞插斷 → 學生明說不會卻拿不到提示升級。改為容許中間
插最多兩個詞（`i don'?t (?:\w+ ){0,2}know`），並補 5 條測試含兩條「不可誤殺肯定句」
（`I know exactly…` / `I'm sure…`）。註：此缺口在既有 243 場存檔中**從未發生**
（修復前後命中數同為 22），是新 persona 探測才逼出來的。

## 備課管線自動生成提示梯：LADDER 階段（2026-08-06，`docs/superpowers/specs/2026-08-05-hint-ladder-generation-design.md`）

**缺口**：`auto_reference.py` 的四階段（PROVER → VERIFIER → REPAIR → SEGMENTER）
**只產 `reference_proof` 與 `teach_steps`，不產 `hint_ladder`**——全 repo 的 `.py` 檔中
`hint_ladder` 只有「從 JSON 讀出」與「讀出後賦值」兩種用法，沒有一處生成它。
`hint_ladders.json`（17 題）是手寫的，只涵蓋內建題。因此 **`app.py` 的使用者自帶題目
一律走空梯路徑**。

**量測到的退化**（`_StubDriver` 模擬連卡 5 輪，Task 1 已固化為 Tier 0 測試）：

| 連續卡住 | 有梯（2 條，內建題） | 無梯（自帶題） |
|---|---|---|
| 1 | 等級 1 | 等級 1 |
| 2 | 等級 2，注入 `ladder[0]` | 等級 2，注入**通用保底句** |
| 3 | 等級 2，注入 `ladder[1]` | **進 walkthrough** |
| 4 | **進 walkthrough** | — |

空梯不死鎖（`ladder_len = max(len(ladder), 1)`），但**等級 2 的透漏內容退化成一句通用
meta 指示**（提示深度改由 4B 模型當場即興拿捏，正是設計鐵律要避免的），且**提早一輪
掉進 walkthrough**——該被第二條提示救起來的學生直接被講答案。

**修法**：加第五階段 LADDER（`LADDER_SYSTEM` + `parse_ladder` + `validate_ladder`
+ `build_ladder`），prompt 規格由 33 條手寫提示反推（恰兩條、依序對應證明的兩個關鍵
轉折、每條點名一個定理／構造／性質的名稱與作用、不得出現任何算式）。
**`tutor_driver.py` 零改動**——`_ladder()` 早就會讀 `hint_ladder`，只是沒人給它。

**五道確定性驗收**（`validate_ladder`，全部對 33 條手寫提示校準，實測零誤判）：
恰 2 條非空字串／每條 12–60 字／`gives_new_equation(h, statement)` 為 False／
`leaks_reference(h, proof, exclude=statement)` 為 False／兩條 difflib 相似度 < 0.85。
**任一不過即整份丟棄回 `None`，不寫 `hint_ladder` 鍵**（不是寫 `None`）→ 行為等於今日。
所有失敗路徑（Ollama 離線、無法解析、驗收不過）收斂到同一結果，**最壞情況零退步**。
> 「不得帶新算式」那道特別重要：等級 2 的禁算式白名單 `_allowed_equation_src()`
> **包含當前提示文字**，提示若帶算式會讓該守衛對那些算式失效。
> （曾考慮把 hint 移出白名單當更根本的防線，但 ADV1 的手寫提示**刻意**帶算式並依賴
> 白名單放行，移除會打壞既有題目——故改為「讓生成的梯保證無算式」。）

**端對端實測**（2 題，Ollama 思考型）：兩題皆 verified 且產出 2 條通過驗收的提示。
E2E1「數列收斂則有界」＝「收斂定義＋三角不等式取尾端的界」→「前綴有限集取最大值」；
E2E2「連續函數在閉區間有最大值」＝「波爾查諾-魏爾斯特拉斯定理推有界」→「序列準則使
上確界被達到」。**兩條確實依序對應該題真正的兩個關鍵轉折**，長度 22–39 字（手寫梯為 16–46）。

單元測試 **215 → 248 條**（Task 1 補空梯路徑覆蓋 8 條 + LADDER 生成端 25 條）。

**完整守門 exit 0**（計分卡 `2026-08-06T194135_5426de5.json`）：25 項硬性指標全 ≥ 基準。
⚠️ 但 Tier 1/2 的 **104 筆回覆與上輪逐字比對 104/104 相同**＝本批對固定探針零影響，
所有 `judge_*` 波動皆評審雜訊，**不可當成修復有效的證據**（本批的真實驗證是 Tier 0
斷言 ＋ 端對端人工檢視）。同輪副產品：Tier 1b 多輪探針首度跑完，抓到弱點 #19。

### 這一輪的三個教訓（比功能本身更值得記）

1. **`test_driver_unit.py` 的斷言計數要用 `grep -cE "^  (✓|✗) "`。** 用
   `grep -c "✓\|✗"` 會把結尾的「全部單元測試通過 ✓」也算進去——實作計畫初版所有
   絕對數字因此都多了 1（CLAUDE.md 舊記的「186 條 / 22 組」亦屬此類，實為 185）。
2. **測試素材必須實測它是否真的觸得到它宣稱要測的那道閘。** 計畫裡一條標榜
   「過長 >60 字 → 退」的 fixture 實測只有 **48 字**，落在門檻內、根本不會被長度閘攔下。
   修正後實測 62 字，並確認另兩道閘（算式、洩漏）對它皆回 False，才證明是長度閘在作用。
   這與 `test_phase_routing.py` 的 V4 教訓同型：**看起來全綠不等於測到東西**。
3. **長時間任務不要丟進 subagent 自己 session 的背景。** 端對端第一次「執行」時
   subagent 把它背景化後即結束 session，進程隨之死亡——GPU 0 MiB、產出檔不存在才發現。

### 已知限制

- **驗收只保證安全性，不保證品質。** 五道閘擋的是「洩漏／給算式／退化重複／格式錯」，
  擋不掉「提示講得爛但無害」。品質只能靠人工抽查。
- **守門照不到這條路徑。** Tier 1/2 是單輪探針、Tier 3 對話，全部走內建題（有手寫梯），
  這次改動在守門指標上是隱形的。驗證只能靠 Tier 0 斷言 ＋ 人工檢視。
- **生成的梯未經人工審閱即用於教學**（不像 `reference_proof` 有 VERIFIER 獨立審）。
  緩解：提示保證不含算式、不洩漏參考解，且等級 2 的既有守衛在生成回覆時仍全數生效。
- 證明者與提示生成者是同一個 4B 思考模型（獨立取樣非獨立模型），新領域建議先抽查。
- **提示梯不再跨語言回退**：英文 session 沒有 `hint_ladder_en` 時使用英文通用提示，
  不把中文 `hint_ladder` 混入英文 system。自動備課仍只產生主語言提示梯；另一語言缺梯
  時品質退化為通用提示，但不再出現混語內容。

## 逐步教學可評分化＋語言鎖定＋審閱收尾（2026-08-07，整合 Codex 交接）

> **2026-08-09 現行規格（以下 2026-08-07 內容保留作歷史紀錄）：**
> `grade_walkthrough_answer`、答案／錯答子字串比對、`walk_retry`、
> `_MAX_WALK_RETRY` 與重講生成守衛均已移除。每個確認問題只作答一次；回答由與
> Review／Rectify 相同的思考型後盾依題目、已驗證參考解與實際呈現步驟做數學語意審閱。
> 明確 `correct` 直接前進；`incorrect`／`partial`／`not_answer` 或後盾不可用時，揭示該步
> 參考答案後前進。SEGMENTER 產物另經 `TEACH_STEPS_VERIFIER_SYSTEM` 獨立驗證，失敗時
> 不採用語意未驗證的句級 fallback，而是回到一般引導。中英文步驟分開快取，且 walkthrough
> 全程鎖定語言、依上一輪實際呈現的 step 審閱。現行細節以
> `self_verified_teaching_design.md` 與 `update.md` 的 2026-08-09 節為準。

Codex 在另一端（`math-proof-week2-training-iter-v11`）做的七項修改，逐項對照本 repo 後
**七項全部尚未存在**（現況只有兩處部分緩解：空梯 `max(len(ladder),1)` 已在、
`detect_lang` 已剝 `$…$`）。逐區塊合併並在本 repo 的架構下重做，單元測試 248 → **303 條**。

- **教學步驟變成可評分的**（`auto_reference.py`）：SEGMENTER schema 擴為
  `{step_id, explain, check, expected_answer, accepted_answers, common_errors}`，
  加 `validate_teach_steps()` 五道確定性驗收；**驗收不過就整份丟棄改走句級保底**
  （`_proof_units`／`_balanced_units`／`_fallback_expected`，3–6 步、每步都有答案鍵、
  移除 QED 記號）。舊資料由 `ensure_checkable_steps()` 冪等補齊。
  `build_reference()` 另回 `teach_steps_lang` / `teach_steps_source`。
- **只有答對才前進**（`tutor_driver.grade_walkthrough_answer`）：先看 `common_errors`、
  再看答案鍵、最後才看卡住（語氣遲疑但答對要算對）。是／否題只看開頭表態
  （「不是，x₂-x₁<0」不因含「是」而算對；「是，因為…」的完整解釋也不因比不到單字而算錯）；
  `\ge`/`\geq`/`≥`/`>=` 與正／負／非負／非正、遞增／單調不減統一正規化。
- **教學輪改為確定性模板、完全不呼叫生成模型**（本輪最大的行為改變）：
  「第 i/n 步：{explain}\n\n確認問題：{check}」。內容本來就是預寫的，讓模型包裝實測換來
  同一步逐字重講、一次講掉好幾步、把確認問題換掉（答案鍵無從比對）。
  副作用是**弱點 #17 的殘留成本一併消失**：教學輪原本每輪最多 4 次重生成
  （守門該段 12 → 45 分鐘），現在是 0 次。
- **語言鎖定 `walk_lang` ＋ presented-step 評分**：`_strip_language_neutral_math()`
  在語言判定前剝除 `$…$`／`$$…$$`／`\(…\)`／`\[…\]`／LaTeX 指令／裸算式；教學期間
  `step()` 不再重判語言；評分對象是 `walk_presented_step`（上一輪實際呈現那一步），
  不是依當下語言重新取 `steps[walk_idx]`。**兩層缺一不可**。
- **「要證明：…」不再被當成交稿**：`_DRAFT_RE` 加反向閘（要／需／欲／待／所），
  教學期間另走專用路由（只有 `_EXPLICIT_REVIEW_RE` 或整則以「證明：」開頭才進 review）。
- **審閱無缺漏 → 確定性收尾**：後盾回報 `gaps == []` 時直接用 `REVIEW_PASS` 模板並
  `done_closed=True`，不再讓說話模型自由發揮（實測會憑空發明缺漏、或確認完成後又追問
  「下一步該從哪裡下手」）。另加 `terminology` 守衛：題目沒寫 strictly、學生已寫
  「單調不減」，助教卻還在 increasing／nondecreasing 之間糾結 → 先帶慣例重生成一次，
  仍糾結就走確定性收尾。**術語慣例（未寫 strictly 的 increasing ＝ 單調不減）四處一致**：
  答案正規化、`PHASE_INSTRUCTIONS["review"]`（中英）、`auto_reference.VERIFIER_SYSTEM`
  ／`SEGMENTER_SYSTEM`、`review_backstop.CRITIC_SYSTEM`——只改一處會讓學生寫對卻被判缺漏。
- **明說卡住的 opener 計為第一次卡住**（自動預設開場白不計），且記在**生成之後**——
  首輪沒有「上一個問題」可拆，等級 1 的指示在那裡是空話，影響的是下一輪的等級。

### 兩處刻意偏離交接文件（已驗證的取捨）

1. **不加 `TEACH_STEPS_VERIFIER_SYSTEM`（第二個 LLM verifier）**：沿用 LADDER 的取捨——
   多一次思考型呼叫要多等最長 300 秒，而它擋不掉的錯（答案鍵與問題語意不合）正是它
   最容易誤判的地方；交接文件自己也寫「列出任何 issue 就安全拒絕」，那會把品質較好的
   SEGMENTER 輸出換成語法保底。改由確定性驗收 ＋ 下面的重試上限把關。
2. **加了重試上限 `_MAX_WALK_RETRY=2`**：交接文件的「答錯或卡住都留在同一步」在
   答案鍵寫壞時會把學生**永遠**困在那一步（答案鍵是自動生成、無人工審閱）。
   超過上限即揭示 `expected_answer` 並前進。第一次答錯仍然留在原步，驗收清單不受影響。

### 完整守門結果（`2026-08-07T093007_11ab1ae.json`，exit 0）與它抓到的三件事

25 項硬性指標全 ≥ 基準，多項上升（`judge_math_ok_zh` 0.9038→0.9423、`judge_score_zh`
0.8192→0.8577、`judge_s2_catch_en` 0.7857→0.8571、`judge_altmethod` 中英雙雙 0.8333→1.0）。
Tier 1/2 逐字比對 **103/104 相同**——唯一差異 `X1/S2/zh` 已查明：該題學生嘗試以
「…由數學歸納法得證。」結尾，命中 `_CLAIM_DONE_RE` 走 **review**，正好吃到新加的術語慣例句
（兩版指的是同一個缺漏）。**所以 judge_* 的上升是評審雜訊，不可當成修復有效的證據。**

真正的收穫來自**人工讀對話**（`render_transcripts.py` 產出的 markdown），數字全綠但內容有問題：

1. **教學輪重講逐字重複（我自己引進的退化，中英兩場重現，已修）**：改成確定性模板時
   順手拿掉了舊的 `WALKTHROUGH_RETRY_NOTE`，於是「重講」＝把同一段原封不動再貼一次。
   M1 中英兩場 `guidance` 都被評 1 分，英文那場學生本人寫「Repeating it doesn't make it
   any clearer」。修法：**首次呈現維持模板、重講輪才叫模型換說法**，確認問題仍由程式附上
   （答案鍵才比得到）；換不出新說法（difflib ≥0.9）或不在線就退回模板並補上該步答案——
   保證「連續兩則教學回覆不逐字相同」。
2. **句級保底的答案鍵挑到句尾括號裡的附帶條件（已修）**：A6/zh 的第一步標準答案被訂成
   `$n\ge 2$` 而非關鍵式 $2^n\ge\binom{n}{2}$，學生答對主關係式反而判錯。
   `_fallback_expected` 改取**最長**的關係式（句尾常掛括號補充條件）。
3. **重講時推託「你自己去查」（已修）**：探針重跑實測抓到「這題的關鍵是…你自己查一下
   二項式展開就知道了」。逐步教學是提示梯用盡後的最後手段，這時推託等於放棄教學 →
   `_REFUSE_TEACH_RE` 命中即視為重講失敗，退回模板＋答案。只作用於教學重講輪。

修復後單獨重跑 walkthrough 探針（真模型，中英）：**相鄰逐字重複對 2 → 0**、
`walkthrough_*` 進入／收尾仍為 True。紀錄在 `regression_scores/2026-08-07_walkthrough_recheck.json`。
> 教訓（延續 `test_phase_routing.py` 的 V4 與 LADDER 那輪）：**硬性指標全綠不等於教得好。**
> `walkthrough_*` 只知道「有沒有進入、有沒有收尾」，`judge_dialogue_*` 早已因雜訊降為
> advisory——這三件事沒有任何自動指標抓得到，全靠讀對話。故新增 `render_transcripts.py`，
> 把每輪守門的對話轉成可讀 markdown，讓「人工讀」變成低成本可重複的動作。

### 守門與驗證狀態

- Tier 0 全過：`test_driver_unit.py` **303 條**、`test_phase_routing.py`（299 場回放、
  5 條不變式違反 0）、`validate.py`、`test_dataset.py`；`regression_suite.py --quick` exit 0。
- **`regression_suite.py` 的 walkthrough 探針必須跟著改**：固定回「我懂了」在新規則下
  是**答錯**（留在同一步），`walkthrough_zh/en` 這兩個硬性指標會從 1.0 掉到 0.5。
  已改為回「上一輪實際呈現那一步的 `expected_answer`」；`eval_svt_e2e.py` 同步
  （台詞用 `None` 表示「回答當前步驟的標準答案」）。
- ⚠️ **本批改動會改變生成行為，不像前幾批可證明對固定探針零影響**：`PHASE_INSTRUCTIONS
  ["review"]` 加了術語慣例（Tier 1/2 的 S1/S2/S3 不走 review，但 Tier 1b 多輪探針會走）、
  審閱無缺漏改確定性收尾（Tier 1 全程 `backstop=False`，故只影響 Tier 3 與實際使用）。
  **推送前需重跑一次完整守門**（GPU + agy，約 1.5hr）。
- 未跑：`test_driver_phase.py`／`test_driver_integration.py`（需 GPU）、
  `test_auto_reference.py`／`eval_svt_e2e.py`（需 Ollama）。

### Code review（2026-08-07，`docs/code-review-walkthrough-gradable.md`）

對 `11ab1ae..a2ba4fd` 做 code review，總評 **4.2/5、無 Critical、可維持現狀部署**。
三項 Important **全部是「新加的守衛在特定輸入下不生效」**，逐項以可執行證據確認
（見弱點 #20/#21/#22），不是回歸；Minor 5 項（註解被拆開、空答案鍵的句尾、
`_DRAFT_RE` 反向閘只列五個字、`teach_steps` 快取鍵語意、驗收對象是補齊前的版本）。

**這輪 review 最值得記的一件事**：I-2（重講防重複抓不到逐字重講）與弱點 #17 第一批
修復踩的是**同一個錯誤**——拿「模型這次講的內容」去比對「上一則完整回覆」，而後者
還包含 driver 自己加的模板前綴與確認問題，稀釋掉相似度。#17 那次是保底句把 0.85
門檻稀釋到 0.768，這次是模板把 0.9 門檻稀釋到 0.845。
**凡是用 difflib 比對「模型輸出」與「上一則回覆」的地方，都要先剝掉 driver 自己
加的部分**，否則門檻等於形同虛設。全檔目前還有第三處同型比對
（`_repeats_previous`）已經有 `_strip_driver_tail`，是唯一做對的那個。

## Code review 三項 Important 修復（2026-08-07 第二批，計分卡 `2026-08-07T183953_a2ba4fd.json`）

全程 TDD（6 條斷言先以正確理由失敗才實作），單元測試 303 → **313 條 / 32 組**。
**完整守門 exit 0**：25 項硬性指標全 ≥ 基準。

- **#20 修法**：`common_errors` 移到答案鍵**之後**比對，並套用 `accepted_answers` 既有的
  短答保護。代價自覺：答案裡同時混了正確答案與某個錯誤說法時判 correct——對教學系統
  而言這個方向的誤判遠比反過來安全。
- **#21 修法**：比對對象加上 `step["explain"]` 本身，並新增 `_strip_walk_template()`
  在比對前剝掉 driver 自己加的模板（回饋前綴／`第 i/n 步：` 標頭／確認問題段）。
- **#22 修法**：`auto_reference._detect_lang` 改成**直接沿用 `tutor_driver.detect_lang`**
  （函式內延遲 import，沿用 `validate_ladder` 既有模式；取不到時退回舊行為），
  兩端從此不可能分岔；`build_reference` 另把語言算一次往下傳給 `fallback_steps` /
  `ensure_checkable_steps` / `teach_steps_lang`（原本是三個各自為政的判定）。

### 這輪唯一的真實證據來自 `_probes.json`，不是 judge 分數

Tier 1/2 的 104 筆回覆與上輪**逐字 104/104 相同** ⇒ 固定探針的生成端零變化 ⇒
**所有 `judge_*` 波動（含上升）都是評審雜訊，不可當成修復有效的證據**。
真正可歸因的證據是 walkthrough 探針的逐輪存檔：

| | `11ab1ae`（修復前） | `a2ba4fd`（修復後） |
|---|:---:|:---:|
| A6/zh 相鄰逐字重複 | 1 | **0** |
| A6/en 相鄰逐字重複 | 1 | **0** |
| 進入／收尾 | True／True | True／True |

（註：本輪 `teach_steps_source` 為 `segmenter`、上輪為 `fallback`——Ollama 在線與否
不同，故非完全受控對照；但兩輪的重講輪都實際發生過，重複數 1→0 是可歸因的。）

### advisory 指標的中文下滑與本批無關（已查證，不要誤記為退步）

`judge_dialogue_math_ok_zh` 0.6667→0.25、`judge_dialogue_guidance_zh` 0.6→0.45
看起來很嚇人，但 Tier 3 的 8 場對話中**只有 M1 中英兩場進入 walkthrough**
（其餘 6 場 `walkthrough=False`、`ladder_idx=0`），亦即 H5/M2/X4 三場**根本沒碰到
本批改動的任何一行**，其分數變動只可能來自 Gemini 學生每輪走不同路徑（輸入隨機）。
英文同期反而上升（`dialogue_math_ok_en` 0.6667→1.0）也印證這點。
M1 中英兩場則是 guidance **兩輪都是 1 分**，維持不變＝弱點 K 未動。
> 方法教訓：advisory 指標波動時，先查「這一場有沒有走到你改的那條路徑」，
> 再決定要不要當回事。`escalation.walk_active` 就是這個問題的直接答案。

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
13. **判分類守門的可靠度普遍不足（2026-08-02 量化後範圍比原本認定的大很多）**：
    原本只知道 `judge_dialogue_*`（n=3）不可靠而降 advisory；`measure_gate_noise.py`
    量測後發現 **9 個硬性 judge 指標中有 8 個的純評審雜訊 ≥ 自己的 ε**
    （`s2_catch_zh` 0.159、`score_zh` 0.135、`reveal_ok` 0.115…，只有 `math_ok_zh` 達標），
    亦即沒有真實退步時也可能判退。`judge_backstop` 已因此降 advisory（實測 0.0/0.33/0.67）。
    ⚠️ **放寬 ε 是死路**：`s2_catch_zh` 真實「多錯 2 題」= 0.143 比雜訊 0.159 還小。
    已做：Tier 2 多次評審取共識（效果未證實，見「Tier 2 多次評審取共識」節）。
    可選方向：加大 n（每指標的題數）、多輪聚合取中位數、或改用更穩定的判準設計。
    **在此之前，任何採用/判退決策都不可只用 judge 分數當依據**（v10 判退是靠
    「質性內容跨四輪一致」認定的），且判退時應先跑 `measure_gate_noise.py` 對照。
    另有結構性盲區：Tier 1/2 為單輪探針，測不到多輪行為（連 6 輪回覆 104/104 逐字相同），
    多輪路徑僅由 Tier 0 的 `test_driver_unit.py` + `test_phase_routing.py` 把關。
14. **商品化介面的 Low/Info 項未清**：F3（`check_ollama` 未關連線）、N2（錯誤 yield 樣板
    重複、`opener_for` 重算）等；且 UI 互動層四情境仍需真模型＋瀏覽器手動驗收
    （自動測試只涵蓋純邏輯）。詳見 `docs/code-review-product-ui.md`。
15. **對話中途的錯誤步驟完全沒有檢查**（update 稽核 F4，最高優先）：審閱後盾只在
    `phase in ("review","rectify")` 觸發，學生在推導途中寫錯一步（不帶「這樣對嗎／我覺得」
    等 `_ATTEMPT_RE` 觸發詞）時 phase=None，driver 只注入「等級 0：問一個聚焦問題」，
    模型手上沒有任何「這步錯了」的訊號 → 照 `BASE_SYSTEM` 的「方向正確就肯定」去肯定。
    這是「Tutor 沒抓到學生數學錯誤」的根因，**不是偶發**。可選解法：學生訊息含算式
    （`_EQ_TOKEN_RE` 命中）即呼叫後盾複核；代價是該輪多 2–4 分鐘，需先量延遲可接受度。
16. **助教自己的數學錯誤沒有任何攔截點**（update 稽核 F5）：`_tutor_turn` 的防護
    （洩漏／防奉送／禁算式／回問保底／重複／稱讚校準）沒有一道檢查內容正確性。
    BoN＋驗證器已判定不採用（邊際效益無法量測）。守門面亦有缺口：`judge_math_ok_*`
    基準 0.9038（容許約 10% 輪次講錯），而最貼近此情境的多輪指標
    `judge_dialogue_math_ok_*` 基準僅 0.667 且已降 advisory ＝ 不進 pass/fail。
17. ~~學生持續卡關時助教退化成重複迴圈~~ → **根因已修**（2026-08-02，三批）。
    「重度卡關型」persona 首跑抓到中英 `guidance` 皆 1 分、`math_ok=True`（純教學失敗）。
    **本項最大的教訓是：我連續兩批都在修症狀，而診斷只花了一次回放。**
    - **第 1、2 批（症狀）**：(a) driver 補的保底句把 difflib 相似度稀釋到門檻以下
      （實測 0.768 < 0.85）→ `repeat` 不觸發，修法為比對前剝除 driver 自己補的句尾
      （`_strip_driver_tail`）；(b) `_regen` 回傳同一段文字卻不複驗就採用，修法為
      重生成後複驗、教學輪推進 `walk_idx`。→ 逐字重複確實消失，**但 `guidance` 仍是 1 分**，
      失敗模式只是換出口：改成直接洩漏答案（「我直接告訴你…極限是 0」）後宣告放棄。
    - **第 3 批（根因）**：回放逐輪查狀態才看到等級序列是 `0→1→2→1→2→1`。
      `_tutor_turn` 在送出等級 2 提示後把 `stuck_count` 歸零（「給過想法後重新計數」）——
      對**恢復的**學生是對的（但 `step()` 本來就會歸零，該行多餘），對**持續卡住**的
      學生有害：下一輪掉回等級 1（指示是「拆更小的子問題、仍不點名定理」＝給得更少），
      支援強度在 2↔1 震盪而非單調遞增，walkthrough 也被反覆重置拖延。刪掉該行即可。
    - **結果**：等級序列 → `0→1→2→2→walkthrough`，第 4 次卡住即進入逐步教學；
      實測對話變成單調遞增的降階梯（抽象提問→簡化→具體操作→點名策略→給關鍵點→
      寫出代入計算），無重複、無放棄。中英 `guidance` **1 → 2**（守門
      `2026-08-02T190427_f85c48e`，exit 0，硬性指標零退步）。
    - **殘留**：分數仍偏低（2/5）。新的評語指向不同問題——「未完成逐點收斂的引導即
      跳轉至不一致收斂」（助教在子目標間跳躍，沒把一個走完）。另有延遲成本未解：
      walkthrough 每輪最多 4 次重生成，守門該段由 12 分鐘漲到 45 分鐘，
      **學生每輪等待同步變成 3–4 倍**，下輪應加每輪重生成次數上限。
17b. ~~逐步教學「有回答就前進」：學生答錯照樣被推到下一步；中文＋長 LaTeX 的正確答案
    會把 session 切成英文而被另一套步驟的答案鍵判錯；「要證明：…」被當成交完整草稿~~
    → 已由 2026-08-07 的整合根治（見上方專節）。**殘留**：`expected_answer` 只有
    確定性驗收（保證可評分、不保證數學語意對得準），品質需人工抽查；句級保底的問題
    仍是「這一步得到的關鍵關係式是什麼？」這種語法式問法，教學價值低於通過驗收的
    SEGMENTER 輸出。另外教學輪改成模板後**語氣固定**，這是拿語氣換可預測性的取捨。
18. ~~備課管線不生成 `hint_ladder`，使用者自帶題目的等級 2 退化成通用指示、
    提早一輪掉進 walkthrough~~ → 已由 **LADDER 階段**根治（2026-08-06，見上方專節）。
    殘留：生成的梯只有確定性驗收（保證安全性，不保證品質），且守門照不到這條路徑；
    品質需人工抽查。備課因此每題多一次 Ollama 呼叫（最長 300 秒）。
19. **英文多輪對話會洩漏參考解（4 題中 3 題）** ← Tier 1b 首度跑完即抓到，**尚未修**。
    2026-08-06 的守門是 `tier1_multiturn`（`ff828c5`）**第一次真正完成**的一輪
    （在此之前 walkthrough 探針卡死，所有 `mt_*` 指標都是 `None`，先前計分卡皆無此欄）。
    首跑結果：中文 4 題 6 項全綠；**英文 `mt_no_leak_en = 0.25`**——A6/en、E4/en、H5/en
    在等級 <2 的輪次命中 `leaks_reference`（等級 2 本來就允許點名想法，不計）。
    另 `mt_phase_flow_en = 0.75`：H5/en 全程沒出現 `writeup_request`
    （phases = None>None>None>rectify>rectify>**None**>review>closed>closed）。
    **與 LADDER 無關**：多輪探針跑的是內建題（有手寫梯），不經過備課管線；
    同輪 Tier 1/2 的 104 筆固定探針與上輪**逐字 104/104 相同**。
    這正是弱點 #13 說的「Tier 1/2 是單輪探針，測不到多輪行為」那塊盲區——
    補上探針後第一次量就見底。**下輪優先處理**；注意單輪的 `s3_refusal_en` 長期 1.0，
    可見「單輪不洩漏」完全推不出「多輪不洩漏」。
20. ~~`common_errors` 排在答案鍵之前比對，會把正確答案判成錯~~ → **已修**（2026-08-07 第二批，守門 exit 0，見上方專節）。原始診斷（code review I-1，`tutor_driver.py:518`）：錯誤答案用**無長度下限的子字串**比對，且排在
    `expected_answer` 之前，只要生成的錯答是正確答案的子字串就永遠先命中。
    實測：`expected_answer="非負"` ＋ `common_errors=["負"]`，學生答「非負」判 incorrect；
    `expected_answer="$x_2-x_1>0$"` ＋ `common_errors=["0"]`，答對同樣判 incorrect
    ——兩組都是 SEGMENTER 很可能真的生成的內容。`_MAX_WALK_RETRY` 擋住了死鎖
    （最多兩輪就被帶過），但學生會被連說兩次「這還不是這一步要的答案」，而他答的
    就是標準答案。**修法**：先比對答案鍵、沒命中才查 `common_errors`，並套用
    `accepted_answers` 那裡已有的短答保護（`len(cand) <= 2 and len(norm) > 12` 跳過）。
21. ~~教學重講的防重複比對抓不到「逐字重講」~~ → **已修**（2026-08-07 第二批，守門 exit 0，見上方專節）。原始診斷（code review I-2，`tutor_driver.py:809`）：
    比對對象是**上一則完整助教回覆**（含 `第 i/n 步：` 前綴與確認問題），而受測文字
    只有 explain 本體，長度天生不對等。實測 96 字的真實步驟：模型把 explain 逐字原樣
    吐回，相似度 **0.845 < 0.9 → 判定為「新說法」而採用**。這道守衛正是為了擋
    M1 那兩場「原封不動再貼一次」而加的，卻擋不住最乾淨的那個版本。
    **修法**：改成比對 `step["explain"]`，或比對前剝掉模板前綴與 `check`（門檻 0.9 沒問題）。
    ⚠️ 與弱點 #17 第一批修復同型，見上方「Code review」節記的通則。
22. ~~`auto_reference._detect_lang` 沒跟上 `tutor_driver.detect_lang` 的強化~~ → **已修**（2026-08-07 第二批，守門 exit 0，見上方專節）。原始診斷（code review I-3，`auto_reference.py:428`）：這批把語言判定前的剝除擴成
    `_strip_language_neutral_math()`（含 `\(…\)`／`\[…\]`／裸算式），但 `auto_reference`
    仍是舊寫法。實測同一段中文兩者判定相反（`故 \(…\dfrac{7}{n+2}<\varepsilon\) 成立。`
    → driver 判 zh、備課判 **en**）。下游兩處：`build_reference()` 寫出的
    `teach_steps_lang`（`app.py` 存進題目、driver 當 `src_lang`），以及
    `ensure_checkable_steps(steps)` **沒帶 lang** 而逐步驟自行判定——算式為主的中文步驟
    很容易配上英文確認問句。**修法**：共用同一個剝除函式，並在 `build_reference`
    把語言算一次往下傳（現在 `fallback_steps` / `ensure_checkable_steps` / `_detect_lang`
    是三個各自為政的判定）。
23. **等級 2 提示梯用盡時，助教會推託「你自己去查」** ← 2026-08-07 第二批守門
    **讀對話**抓到（`a2ba4fd_transcripts.md:556`），**尚未修**。A6/zh 逐步教學探針的
    倒數第二輪（等級 2、`ladder_idx=2`＝提示梯已耗盡）逐字輸出：

    > 這題需要「取二次項當下界」這個技巧，你自己查一下二項式展開就知道了。

    這正是 `_REFUSE_TEACH_RE` 要擋的失敗模式，但那道守衛**只作用於 walkthrough 重講輪**
    （2026-08-07 第一批刻意限定範圍），而這句出現在進 walkthrough 的**前一輪**——
    學生此刻已經把整條提示梯用完，推託等於在最需要幫助的時間點放棄教學。
    **非本批引進**：與上一輪計分卡（`11ab1ae_transcripts.md:553`）**逐字相同**，
    且該筆屬 104/104 相同的固定探針集合，是長期存在、只是沒人讀到。
    **修法方向**：把 `_REFUSE_TEACH_RE` 的作用域從「教學重講輪」擴大到
    「等級 2 且 `ladder_idx >= 梯長`」，命中即重生成。
    ⚠️ 不可無條件全域套用——一般引導輪的「你自己試著寫出…」是正當的蘇格拉底問法
    （同一份 transcript 裡有 6 處），擴太寬會把它們一起誤殺。
