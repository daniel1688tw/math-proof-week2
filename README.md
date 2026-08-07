# Socratic Calculus Proof Tutor — QLoRA 微調 + 對話驅動架構

把 **Qwen3-4B-Instruct** 微調成蘇格拉底式的大學微積分／數學分析證明助教：

- **不直接給答案**——每次只問一個聚焦問題，引導學生自己完成證明
- **分級提示**——學生連續卡住兩次，才透漏該步的關鍵定理或想法（不給算式）
- **自我驗證備課**——面對沒見過的題目，先自己證一遍並獨立驗證，證對了才教；證不出來誠實說沒把握
- **寫證明與審閱**——學生走完關鍵步驟後，請他自己寫出完整證明，再對草稿做問題式審閱
- **抗壓**——被逼問答案時拒絕並把主導權還給學生；學生自信斷言錯誤時不附和
- **懂得收手**——證明確認完成後進入收尾狀態，不再拋新問題、不主動延伸

訓練資料**全部人工撰寫並驗證數學正確性**（50 道題目 + 中英平行多輪對話），
在單張 6GB VRAM 的筆電 GPU（RTX 4050）上即可完成訓練與推論。

現行部署形態 = **`qlora_adapter_v9` + TutorDriver（含全部確定性防護）+ 審閱後盾**。
v10／v11 兩輪整體重訓皆經守門判退，**版號越新不代表越該用**。

## 架構：模型只管數學與語氣，決策交給程式碼

```
新題目 → auto_reference.py 備課（Ollama 思考型模型，五階段）
          PROVER×3 → VERIFIER → REPAIR → SEGMENTER → LADDER
          verified → 產出 reference_proof + teach_steps + hint_ladder，進入下方 grounded 教學
          unverified → 同學模式（誠實聲明沒把握、同儕一起探索、被質疑會反省認錯）

學生訊息 → TutorDriver（確定性決策層）
             · stuck counter：連續卡住次數 → 提示等級 0/1/2（持續卡住時單調遞增，不回退）
             · 階段偵測：交草稿→review / 逼問→refuse_leak / 嘗試→rectify /
                         說懂了→writeup_request / 證明確認完成→closed 收尾
             · 等級 2 注入提示梯內容（內建題來自 hint_ladders.json，
               使用者自帶題目來自備課的 LADDER 階段）
             · 提示梯用盡仍連卡兩次 → walkthrough 逐步教學（一步一確認，教完仍要學生自寫證明）
             · review/rectify 輪：審閱後盾（Ollama 思考型模型對照參考解找碴，
               缺漏清單注入 system；未裝 Ollama 自動降級，REVIEW_BACKSTOP=0 關閉）
           → QLoRA 微調模型（4-bit nf4）+ grounded system prompt（內含該題參考解）
           → 內容防護（每次重生成後重跑）：參考解洩漏 n-gram 檢查、on-track 防奉送、
             等級 2 禁算式、稱讚校準；其後單問句截斷、重複偵測、回問保底
```

核心設計原則（六輪迭代的教訓）：**離散決策交給程式碼、內容拿捏交給預寫內容、
模型只負責數學與語氣**。「透漏多少提示」這類連續量，純 SFT 校準不準；
把提示內容預先寫好、由驅動程式決定何時注入，行為即完全受控。

混合架構延伸：審閱學生草稿需要的「即時數學判斷」超出 4B 微調模型的可靠範圍
（會出現「察覺對但解釋錯」與錯誤背書），故由思考型模型在幕後找碴、微調模型
只負責把缺漏清單包裝成引導問題（`review_backstop.py`，選配，需本機 Ollama +
`qwen3-4b-thinking-2507`；未安裝時自動降級回單模型行為）。

完整設計文件見 [專案架構設計.md](專案架構設計.md)。

## 成效（8 道訓練集外題目 × 3 對抗情境，LLM-as-judge /5）

| 路線 | 首問 | 糾錯 | 逼問答案 | 總平均 |
|---|:---:|:---:|:---:|:---:|
| **本方法（微調 + driver + 審閱後盾）** | 4.31 | 4.50 | 4.31 | **4.37** |
| 微調 + driver（後盾離線時的降級形態） | 4.31 | 4.19 | 4.31 | 4.27 |
| 未微調基底 + 同樣 prompt | 3.88 | 4.06 | 3.00 | 3.65 |
| Ollama 思考型 + 同樣 prompt（無微調） | 3.63 | 4.75 | 3.63 | 4.00 |

微調的價值集中在互動壓力情境：被逼問時未微調模型只會政策式拒絕（零教學前進），
思考型模型甚至曾把完整證明整段交出；微調 + driver 則穩定做到「一句拒絕 + 一個引導問題」。
完整判定過程見 [dataset/eval_out_final/FINAL_VERDICT.md](dataset/eval_out_final/FINAL_VERDICT.md)。

跨領域遷移（離散數學／線性代數 6 題）三情境總平均 4.25 ≈ 域內，引導行為無衰減遷移，
18 筆生成零數學錯誤——**grounded 參考解是跨域的關鍵錨，不可拿掉**。

---

## 快速開始

### 1. 環境（Python 3.11，CUDA 12.x，≥6GB VRAM）

```bash
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121
pip install "transformers==5.8.1" "accelerate==1.13.0" "peft==0.19.1" \
            "bitsandbytes==0.49.2" "datasets==4.8.5" "huggingface_hub==1.14.0"
```

> Windows 注意：transformers 5.x + bitsandbytes 載入 7B 模型會 segfault；本專案用 4B，實測安全。

本機開發用 Anaconda 環境 `lora_project`：

```powershell
$env:PYTHONNOUSERSITE = "1"
conda run -n lora_project --live-stream python dataset\app.py
```

### 2. 下載基底模型

```bash
huggingface-cli download Qwen/Qwen3-4B-Instruct-2507 --local-dir learn_path/socratic_tutor/qwen3_4b
```

### 3.（選配但強烈建議）安裝 Ollama 思考型模型

備課與審閱後盾都依賴它。**沒有它，助教無法為新題目備課，所有自帶題目都會走同學模式。**

```bash
# 安裝 Ollama 後
ollama pull qwen3-4b-thinking-2507
ollama serve            # 預設 http://localhost:11434
```

### 4. 訓練（~1 小時 @ RTX 4050；v9 是在 4090 上 12.5 分鐘）

```bash
cd learn_path/socratic_tutor
MAX_LEN=1024 EPOCHS=3 GRAD_ACCUM=8 EVAL_STEPS=20 OPTIM=adamw_8bit NEFTUNE_ALPHA=5 \
python train_qlora.py
# 產出 dataset/qlora_adapter_new/（路徑可用 ADAPTER_DIR 覆寫，不會蓋掉現役 v9）
```

> `MAX_LEN=1024` 是 v9 的關鍵改動：640 會截掉 26% 訓練樣本的**尾端**，正是對話收尾／
> 審閱輪所在的位置。`OPTIM` 不要用 `paged_adamw_8bit`（abrupt kill 後會留下 init error）。

### 5. 測試與品質守門

```bash
cd dataset
python test_driver_unit.py            # 驅動程式邏輯（無 GPU，250 條斷言 / 28 組）
python test_phase_routing.py          # 真實對話回放驗階段路由不變式（無 GPU，299 場存檔）
python test_app.py                    # 介面純邏輯（無 GPU、不連 Ollama）
python test_dataset.py                # 資料集結構與內容檢查

conda run -n lora_project python test_driver_integration.py   # 分級提示行為（GPU）
conda run -n lora_project python test_driver_phase.py         # 階段管理行為（GPU）
conda run -n lora_project python eval_final_driver.py         # 部署形態三情境評估

# 推送前守門（版本只進不退）：
python regression_suite.py --quick    # 單元＋資料集（~1 分鐘）
python regression_suite.py            # 完整回歸（GPU＋評審 CLI，~1.5–2 小時）
python regression_suite.py --rejudge  # 讀存檔重新評審（不重跑 GPU）
```

完整回歸預設由 **Antigravity CLI（`agy`／Gemini 3.6 Flash Medium）擔任評審與學生**
（`JUDGE_BACKEND=claude` 可切回 Claude 備援）。分成五層：

| 層級 | 內容 | 判定性質 |
|---|---|---|
| Tier 0 | 資料集驗證、driver 單元測試、真實對話回放不變式 | 零容忍 |
| Tier 1 | 單輪確定性探針（洩漏／拒絕／單問句／提示升級／教學收尾） | 零容忍 |
| Tier 1b | **多輪確定性探針**（`mt_*`：多輪不洩漏、階段流、提示梯守恆、乾淨收尾） | 零容忍 |
| Tier 2 | 單輪評審（`judge_math_ok`／`score`／`s2_catch`／`reveal_ok`／`altmethod`，n≈13） | 容忍 ε（預設 0.05，逐項覆寫） |
| Tier 3／4 | 多輪對話評審、審閱後盾找碴準確度 | **advisory**（照算照印，不進 pass/fail） |

計分卡與對話記錄存 `dataset/regression_scores/`（進 git），逐指標與
`regression_baseline_antigravity.json` 比較，**任何硬性指標退步即 exit 1**。
搭配 Claude Code 可用 `/pre-push-check` skill 執行完整守門流程。

> ⚠️ **判退時先跑 `python measure_gate_noise.py`**：實測 9 個硬性 judge 指標中有 8 個的
> 「純評審雜訊」≥ 自己的 ε，沒有真實退步時也可能判退。任何採用／判退決策都不可
> 只用 judge 分數當依據。細節見 `CLAUDE.md`。

### 6. 命令列互動（內建 50 題）

```bash
cd dataset
python interactive_turn.py --problem A2 --state session.json --reset      # 開場
python interactive_turn.py --problem A2 --state session.json --student "我把 |x²-4| 分解成 |x-2||x+2| 了"
```

或在自己的程式中：

```python
from tutor_driver import TutorDriver, load_problems_with_ladders
problems = load_problems_with_ladders()
driver = TutorDriver(tok, model, problems["A2"])
print(driver.start())                 # 助教第一問
print(driver.step("學生的回覆"))       # 逐輪推進
```

---

## 圖形介面（本機單人 Demo）

貼上**自己的**證明題（不查題庫），助教先自我驗證備課，再蘇格拉底式逐步引導；
備課驗證失敗則走同學模式（誠實降級）。

### 開啟

```powershell
# 前置：已完成上方步驟 1–2（模型），步驟 3（Ollama）建議一併完成
pip install "gradio>=4.44"

conda run -n lora_project --live-stream python dataset\app.py
```

終端出現 `[app] 模型就緒，啟動介面 http://localhost:7860` 後（首次載入模型約 30–60 秒），
用瀏覽器開 **http://localhost:7860**。

介面綁定 `127.0.0.1`，**只接受本機連線**；`demo.queue(default_concurrency_limit=1)`
表示同一時間只處理一個請求——這是單張 6GB 卡的 Demo，不是多人服務。

### 使用流程

| 步驟 | 操作 | 說明 |
|---|---|---|
| 1 | **題目敘述（必填）** | 貼上要證明的題目，例：`證明：連續函數在閉區間上必有界。` |
| 2 | **你目前的證明／嘗試（可留空）** | 有寫一部分就貼上（助教會從那裡接手）；完全沒頭緒留空即可 |
| 3 | 按 **開始備課** | 畫面逐階段串流顯示 `PROVER 1/3 → VERIFIER → REPAIR → SEGMENTER → LADDER` |
| 4 | 備課完成 | ✅ `備課完成（grounded）` → 進入完整引導教學<br>⚠️ `沒能自己驗證出可靠解` → 同學模式 |
| 5 | 對話 | 在下方輸入框回覆，按 **送出** 或 Enter；助教每輪只問一個問題 |
| 6 | 換題 | 按 **重新開始（換一題）** 清空對話回到輸入畫面 |

生成期間「送出」鈕與輸入框會一起變灰——這是刻意的，避免按 Enter 重送把單 GPU 佇列塞爆。

### 常見狀況

- **頂端出現「未偵測到 Ollama 服務」**：備課需要 Ollama 在線。沒有它所有題目都走同學模式，
  助教會誠實聲明沒把握，但**引導品質與可靠度都會下降**。啟動 `ollama serve` 後重開介面。
- **備課要等數分鐘**：五階段各需一次思考型模型呼叫（PROVER 跑 3 次，LADDER 最長 300 秒）。
  RTX 4050 6GB 上微調模型常駐約 3.5GB，備課時 Ollama 會被擠到 CPU 而更慢——
  屬 Demo 的固有限制。
- **備課失敗**：畫面會顯示錯誤訊息並留在輸入畫面，不會卡死（背景執行緒以 `try/finally`
  保證送出結束哨兵）。
- **同學模式下的說法不保證正確**：助教已聲明沒把握，內容僅供參考。

使用者導向的完整說明見 [使用者說明書.md](使用者說明書.md)。

### 環境變數

| 變數 | 預設 | 作用 |
|---|---|---|
| `FINAL_ADAPTER` | `qlora_adapter_v9` | 切換 adapter（評估腳本另有 `HELDOUT_/HARD_/XDOMAIN_ADAPTER`） |
| `REVIEW_BACKSTOP` | `1` | 設 `0` 關閉審閱後盾 |
| `REVIEW_MODEL` | `qwen3-4b-thinking-2507:latest` | 備課／後盾用的 Ollama 模型 |
| `OLLAMA_URL` | `http://localhost:11434/api/chat` | Ollama 端點 |
| `PROVER_K` | `3` | 備課生成幾份候選參考解 |
| `JUDGE_BACKEND` | `antigravity` | 守門評審後端（`antigravity` / `claude`） |

---

## 為新題目備課（不透過 UI）

```bash
python dataset/auto_reference.py --statement "證明 ..." --id NEW1 --out new_problem.json
# verified   → 產出含 reference_proof + teach_steps (+ hint_ladder) 的題目檔，TutorDriver 直接可用
# unverified → 該題自動走同學模式（誠實降級，不硬教）
```

備課盲測（10 題已知解盲跑）：**verified 9/10，且這 9 題的參考解正確率 9/9＝零錯誤背書**。
唯一沒過的是歷來最難的 Darboux 題——「知之為知之」正是設計目標。

## 資料集

| 項目 | 數量 |
|---|---:|
| 題目（含手寫 LaTeX 參考解） | 50（極限/連續/微分/積分/級數 各 10）|
| 對話（中英平行；`train.jsonl` 747 / `val.jsonl` 83） | 830 |
| 對話類型 | 核心引導（3 種學生人格）、犯錯變體、抗洩漏/抗附和、分級提示、節奏錯位、寫證明審閱、跨題型旅程 |
| 手寫提示梯 `hint_ladders.json`（推論時讀取） | 17 題（中英各一份）|
| 評估題（全部不在訓練集） | 8 held-out + 5 分布外難題 + 6 跨域（離散/線代）+ 1 進階題 |

> 資料集是**訓練集，不是題庫**：推論時模型不查資料集、不做檢索，面對新題目靠的是
> 現場備課產出的參考解。唯一在推論時被讀取的資料資產是 `hint_ladders.json`。
>
> 現役 **v9 adapter 訓練於 814 例的版本**（733/81）；目前 `build.py` 產出的 830 例含後來加入的
> `dialogues_journey.py`（v10／v11 用，兩次整體重訓皆判退，資料保留供下次迭代）。

修改 `dataset/src/`（或 `src_en/`）後執行 `python build.py && python validate.py && python test_dataset.py` 重建。

## 開發歷史

本 repo 的工作目錄只保留最終方法。六輪迭代的完整歷史（MathDial 行為遷移、Ollama
無微調路線、adapter v2–v5 及其評估報告）保存在 git tag：

```bash
git checkout experiments-v2-v6
```

近期分支演進與逐項優化見 [update.md](update.md)；已知弱點與下一輪方向見 `CLAUDE.md`。

## 內容聲明

`dataset/src/` 的所有題目、參考解與對話由人工撰寫並驗證數學正確性，非模型生成。
基底模型 Qwen3-4B-Instruct-2507 遵循其原始授權（Apache 2.0）。
