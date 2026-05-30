# Pipeline 人工檢查指南

## 3. 在 Colab 中設定環境

### 步驟 3-1：開啟 Colab 並切換為 GPU Runtime

```
選單 → 執行階段 → 變更執行階段類型 → T4 GPU（或 A100）
```

免費版 T4 即可執行 7B 4-bit 量化模型。

### 步驟 3-2：Clone 你的 GitHub repo

```python
# Colab cell 1
!git clone https://github.com/<你的帳號>/<repo名稱>.git
%cd <repo名稱>   # 或 %cd <repo名稱>/week2（看你 push 的層級）
```

### 步驟 3-3：安裝依賴套件

```python
# Colab cell 2
!pip install -q \
    jsonschema \
    networkx \
    sympy \
    langgraph \
    transformers \
    accelerate \
    "bitsandbytes>=0.46.1"
```

> Colab 是 Linux 環境，bitsandbytes 可直接用 pip 安裝（不需要 Windows wheel）。

### 步驟 3-4：確認 GPU 與套件正常

```python
# Colab cell 3
import torch
print("CUDA available:", torch.cuda.is_available())
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None")
```

預期輸出：
```
CUDA available: True
GPU: Tesla T4
```

### 步驟 3-5：確認工作目錄

```python
# Colab cell 4
import os
os.listdir(".")
# 應該看到：benchmark.py, config.py, generators.py, tests/, ...
```

如果看到的是上層目錄，補一行：
```python
os.chdir("week2")
```

---

## 4. 逐步執行 inspect_pipeline.py

> **第一次執行 Stage 1 會下載 Qwen/Qwen2.5-Math-7B-Instruct（約 14 GB），請耐心等待。**
> 後續 stage 執行時模型已在記憶體中，速度較快。

### 推薦流程：一次跑一個 stage，逐步確認

#### Stage 1：問題解析

```python
# Colab cell
!python tests/inspect_pipeline.py --stop-after 1
```

執行時間：模型載入 5~10 分鐘 + 推理約 30~60 秒

---

#### Stage 2：合約建立（需 Stage 1 完成）

```python
!python tests/inspect_pipeline.py --start-from 2 --stop-after 2
```

---

#### Stage 3：圖骨架規劃（需 Stage 1~2 完成）

```python
!python tests/inspect_pipeline.py --start-from 3 --stop-after 3
```

---

#### Stage 4：逐節點證明（需 Stage 1~3 完成）

```python
!python tests/inspect_pipeline.py --start-from 4 --stop-after 4
```

---

#### Stage 5：驗證器（需 Stage 1~4 完成）

```python
!python tests/inspect_pipeline.py --start-from 5 --stop-after 5
```

---

#### Stage 6：輸出追蹤（需 Stage 5 完成）

```python
!python tests/inspect_pipeline.py --start-from 6 --stop-after 6
```

---

### 也可以一次全跑（6 個 stage）

```python
!python tests/inspect_pipeline.py
```

---

### 切換題目

```python
# 0 = chain rule（d/dx sin(x^2) = 2x·cos(x^2)）  ← 預設
# 1 = 均值定理（Mean Value Theorem）
# 2 = 中間值定理（Intermediate Value Theorem）
!python tests/inspect_pipeline.py --problem 1 --stop-after 3
```

---

### 查看輸出結果

```python
# 查看 Markdown 報告（每個 stage 的人工可讀摘要）
!cat week2_outputs/inspect/report.md

# 查看某個 stage 的完整 JSON
!cat week2_outputs/inspect/stage1_problem_json.json
!cat week2_outputs/inspect/stage2_proof_contract.json
!cat week2_outputs/inspect/stage3_graph_skeleton.json
!cat week2_outputs/inspect/stage4_proven_graph.json
!cat week2_outputs/inspect/stage5_verifier_result.json
!cat week2_outputs/inspect/stage6_trace.json
```

---

## 5. inspect_pipeline.py 各部分說明

### 檔案結構概覽

```
tests/inspect_pipeline.py
│
├── setup()              ← 建立輸出目錄 week2_outputs/inspect/
├── save_stage(name, data) ← 將結果存為 JSON
├── load_stage(name)     ← 讀取之前存的 JSON（--start-from 用）
├── append_report(text)  ← 追加到 report.md
├── init_report()        ← 初始化 report.md 標頭
│
├── run_stage1()   ← Stage 1: Problem Parser
├── run_stage2()   ← Stage 2: Contract Builder
├── run_stage3()   ← Stage 3: Graph Planner
├── run_stage4()   ← Stage 4: Graph Prover
├── run_stage5()   ← Stage 5: Run Verifiers
├── run_stage6()   ← Stage 6: Export Trace
│
└── main()         ← 解析 --problem / --stop-after / --start-from 參數
```

### 各 Stage 函式說明

| Stage | 函式 | 呼叫的核心模組 | 輸入 | 輸出 |
|-------|------|----------------|------|------|
| 1 | `run_stage1(raw_problem)` | `generators.generate_problem_json()` | 原始題目字串 | `problem_json` dict |
| 2 | `run_stage2(problem_json)` | `generators.generate_proof_contract()` | stage1 結果 | `proof_contract` dict |
| 3 | `run_stage3(problem_json, proof_contract)` | `generators.generate_graph_skeleton()` | stage1+2 結果 | `graph_state` dict |
| 4 | `run_stage4(problem_json, proof_contract, graph_state)` | `graph_planner.graph_prover()` | stage1+2+3 結果 | `proven_graph` dict（各節點含 proof_body） |
| 5 | `run_stage5(problem_json, proof_contract, proven_graph)` | `verifiers.run_all_verifiers()` | stage1+2+4 結果 | `{errors, aggregator, obligation_status}` |
| 6 | `run_stage6(state_so_far)` | `langgraph_nodes.export_trace_node()` | stage5 的 accepted 結果 | `{trace}` |

### 關鍵設計：`--start-from` 的中間結果載入

Stage N 執行後結果存為 JSON。下次執行 `--start-from N+1` 時，腳本會從 JSON 讀回之前的結果，不需重新呼叫 LLM。這讓你可以：

- 先看 stage3 的節點結構是否合理，再決定要不要繼續跑 stage4
- 如果 stage4 有問題，只重跑 stage4（`--start-from 4 --stop-after 4`）而不用重跑 stage1~3

---

## 6. 各 Stage 完成後可人工檢查的項目

### Stage 1 — Problem Parser（問題解析）

**LLM 做了什麼**：把原始題目字串轉成結構化 JSON，包含目標、假設、變數。

**人工檢查清單**：

| 項目 | 正確的樣子 | 常見問題 |
|------|-----------|----------|
| `goal.text` | 用自然語言描述題目要證明的東西 | 描述不完整、包含原題目以外的內容 |
| `goal.symbolic` | 數學符號式，如 `d/dx sin(x^2) = 2*x*cos(x^2)` | 符號錯誤、漏掉 `=` |
| `assumptions` | 列出題目中明確說的前提條件（如「x 是實數」） | 假設遺漏、或把目標誤當成假設 |
| `variables` | 所有出現的變數及其型別 | 遺漏變數、型別錯誤（如 `integer` vs `real`） |
| `hidden_conditions` | 隱含但未明說的條件（如可微性） | 應該有但為空、或捏造不存在的條件 |
| `_generation_attempts` | 通常為 1 或 2 | 3 表示需要修復才通過 JSON 驗證 |

---

### Stage 2 — Contract Builder（證明合約）

**LLM 做了什麼**：規劃這個證明需要完成哪些「義務（obligation）」，以及允許/禁止引用哪些定理。

**人工檢查清單**：

| 項目 | 正確的樣子 | 常見問題 |
|------|-----------|----------|
| `obligations` | 把完整證明分解成幾個必須完成的子目標 | 義務太籠統（只有一條「prove the result」）、或義務之間重疊 |
| 義務的覆蓋性 | 所有義務合在一起足以構成完整的證明 | 遺漏關鍵步驟（如 chain rule 的例子應該包含「先建立 lemma」） |
| `allowed_references` | 列出合法引用的定理名稱（如 `chain_rule`, `power_rule`） | 允許的定理太少（後面 stage4 會引用到但這裡沒列）、或引用了不存在的定理名稱 |
| `forbidden_moves` | 若有，應是明確禁止的捷徑（如「不能直接引用結論」） | 通常為空，但若有，確認是否合理 |

---

### Stage 3 — Graph Planner（證明圖骨架）

**LLM 做了什麼**：把證明組織成有向圖，每個節點是一個命題，推理邊表示「由 A 可推出 B（使用定理 X）」。

**人工檢查清單**：

| 項目 | 正確的樣子 | 常見問題 |
|------|-----------|----------|
| `goal_node_id` | 指向最終要證明的節點 | 指向中間節點、或不存在的 ID |
| 節點數量 | 合理範圍（一般 3~8 個），assumption + lemma + goal | 節點太少（整個證明只有 2 個節點，缺乏中間步驟）、或節點太多（每一個代數步驟都列成節點） |
| 推理鏈的連通性 | 從所有 source（assumption）節點出發，能透過推理邊到達 goal 節點 | 有孤立節點、或 goal 節點沒有入邊（沒有推理指向它） |
| 推理使用的定理 | `rule_refs` 中的定理名稱應在 stage2 的 `allowed_references` 中 | 引用了 contract 沒有允許的定理 |
| assumption 節點 | `node_type=assumption`，claim 對應 stage1 的假設 | 假設節點 claim 和 stage1 不一致 |

---

### Stage 4 — Graph Prover（逐節點證明）

**LLM 做了什麼**：為每個非 source 節點（lemma、goal）生成具體的推導步驟（`proof_body.steps`）。

**人工檢查清單**：

| 項目 | 正確的樣子 | 常見問題 |
|------|-----------|----------|
| 步驟邏輯連貫性 | 每一步的 `statement` 都能從前一步合理推出 | 步驟之間有跳躍、無法推出中間結果 |
| `reason` 欄位 | 每步說明用了什麼定理或規則 | `reason` 是空字串、或是模糊描述（如「by calculation」） |
| 最後一步 | 最後一個步驟的 `statement` 應等於或包含該節點的 `claim` | 最後一步的結論和節點 claim 不一致（表示證明沒有真的推到目標） |
| 對每個節點 | 有 `steps` 且不為空 | `steps` 為空（LLM 生成失敗） |
| 定理引用合法性 | `reason` 中引用的定理應是 stage2 合約中允許的 | 引用了 chain rule 但 chain rule 不在 allowed_references 中 |

---

### Stage 5 — Run Verifiers（自動驗證）

**Verifier 做了什麼**：執行 8 種自動檢查器，每個檢查一個面向（邏輯嚴謹性、義務覆蓋、循環推理等）。

**人工檢查清單**：

| 項目 | 正確的樣子 | 需要注意的情況 |
|------|-----------|---------------|
| `HIGH` 錯誤 | 沒有 HIGH 錯誤才會 accepted | 有 HIGH 錯誤時：確認錯誤是真實的邏輯問題？還是 verifier 的誤判？ |
| `MEDIUM` 錯誤 | 允許有但不阻斷 | 看 `evidence` 欄位：錯誤描述是否指出真正的問題？ |
| Obligation 狀態 | 所有 obligation 都是 `pass` | 哪條 obligation 沒通過？是因為對應的節點 claim 不夠明確？ |
| `source` 欄位 | 顯示是哪個 verifier 觸發（如 `graph_connectivity`、`obligation_coverage`） | 可以追回到特定 verifier 來判斷誤判率 |
| `all_required_pass` | `True` = 整個證明通過 | 若是 `False` 但人工看 stage4 覺得邏輯正確，表示 verifier 過嚴或 LLM 輸出格式問題 |

**8 個 Verifier 的功能**：

| Verifier | 檢查什麼 | 錯誤等級 |
|----------|----------|----------|
| `graph_connectivity` | 推理圖能否從假設連通到 goal | HIGH |
| `obligation_coverage` | 每條義務是否有節點的 claim 覆蓋 | HIGH |
| `proof_step_validity` | 每個步驟是否有 reason、claim 是否合理 | HIGH / MEDIUM |
| `theorem_applicability` | 引用的定理是否適用（LLM 判斷，需模型） | MEDIUM |
| `circular_reasoning` | 是否有推理環路 | HIGH |
| `assumption_use` | assumption 是否有被引用到 | MEDIUM |
| `vague_justification` | evidence 中是否出現模糊詞（obvious、clearly 等） | MEDIUM |
| `case_coverage` | 若有多種情況是否都涵蓋（LLM 判斷） | MEDIUM |

---

### Stage 6 — Export Trace（輸出追蹤）

**做了什麼**：把整個 pipeline 的執行記錄（trace）收集起來，加上最終的 `accepted` 結論。

**人工檢查清單**：

| 項目 | 正確的樣子 |
|------|-----------|
| trace 中的節點名稱 | 應包含 6 個：`problem_parser`, `contract_builder`, `graph_planner`, `graph_prover`, `run_verifiers`, `export_trace` |
| `accepted` 值 | 和 stage5 的 `all_required_pass` 一致 |

---

## 快速參考：輸出檔案位置

```
week2_outputs/inspect/
├── report.md                ← 人工可讀的 Markdown 報告（所有 stage 的摘要）
├── stage1_problem_json.json ← Stage 1 完整 JSON 輸出
├── stage2_proof_contract.json
├── stage3_graph_skeleton.json
├── stage4_proven_graph.json ← 最大的一個，包含所有節點的 proof_body
├── stage5_verifier_result.json
└── stage6_trace.json
```

---

## 常見問題

**Q: Colab session 斷線，重新連線後怎麼繼續？**

A: 模型需要重新載入（重新執行安裝 cell 和 `python tests/inspect_pipeline.py --start-from N`）。
但中間結果的 JSON 檔存在 Colab 的暫時儲存空間中，通常 session 重連後還在（若沒被清除）。
建議把 `week2_outputs/inspect/` 資料夾下載或 mount Google Drive：

```python
from google.colab import drive
drive.mount('/content/drive')
# 然後修改 inspect_pipeline.py 中的 INSPECT_DIR 指向 Drive 路徑
```

**Q: 模型下載速度太慢？**

A: Qwen2.5-Math-7B-Instruct 約 14 GB，在 Colab 上通常 5~10 分鐘。
若已下載過，HF 會快取在 `~/.cache/huggingface/hub/`，同一 session 不會重複下載。

**Q: 執行 stage4 時有某個節點顯示「⚠ 無 steps」？**

A: 表示該節點的 LLM 生成失敗（超過 `MAX_REPAIR_ATTEMPTS=3` 次仍無法生成有效 JSON）。
可以查看 terminal 中該節點的 `raw[:600]` 輸出，了解 LLM 實際輸出了什麼。

**Q: Stage 5 顯示 `accepted=False` 但 stage4 看起來邏輯正確？**

A: 最常見的原因是 `obligation_coverage` 驗證失敗——義務描述和節點 claim 的文字不夠相似。
可以對照 stage2 的義務描述和 stage3 的節點 claim，看是否需要調整 prompts。
