# Week 2：小模型 + 圖形證明器完整流程

本專案以 Qwen/Qwen2.5-Math-7B-Instruct（4-bit 量化）為核心 LLM，實作一套**自動微積分證明生成與驗證系統**。輸入一道微積分題目的文字描述，系統會依序生成結構化問題資訊、證明契約、有向無環證明圖（DAG），逐節點填入推導步驟，最後通過多層驗證器評判接受度。整個流程以 LangGraph StateGraph 串接。

---

## 模組總覽

```
week2/
├── config.py              # 全域設定（模型名稱、Token 限制、修復次數）
├── benchmark.py           # 基準測試題庫與定理庫
├── schemas.py             # JSON Schema 定義（三種資料結構）
├── model_loader.py        # LLM 載入（4-bit 量化 HF 模型）
├── json_utils.py          # JSON 解析與自動修復工具
├── prompts.py             # Prompt 模板（一般版 + 緊湊版）
├── generators.py          # 核心生成器（帶正規化 + 驗證的生成迴圈）
├── verifier_utils.py      # 驗證工具函數（共用基礎層）
├── verifiers.py           # 多層驗證器（結構 / 符號 / Critic）
├── graph_planner.py       # 圖規劃器與節點證明填充
├── langgraph_nodes.py     # LangGraph 工作流節點與 StateGraph 定義
└── main.py                # 主程式入口（示例執行 + 測試套件）
```

---

## 系統架構圖

```
原始題目文字
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph StateGraph                      │
│                                                             │
│  problem_parser → contract_builder → graph_planner          │
│       │                │                   │                │
│  problem_json    proof_contract      graph_skeleton         │
│                                            │                │
│                                     graph_prover            │
│                                            │                │
│                                    (逐節點生成)              │
│                                     node proof_body         │
│                                            │                │
│                                    run_verifiers            │
│                                            │                │
│                                    export_trace             │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
 accepted / error_count / trace
```

---

## 資料流與三大結構

系統在生成階段維護三個逐步累積的 JSON 物件：

| 資料結構 | 必填欄位 | 說明 |
|---|---|---|
| `problem_json` | `problem_id`, `raw_problem`, `goal` | 問題的結構化表示，含目標、假設、變數、領域 |
| `proof_contract` | `goal`, `obligations`, `allowed_references` | 證明的合約，規定可用定理、禁止動作與驗收標準 |
| `proof_graph_state` | `proof_id`, `nodes`, `inferences` | 有向無環證明圖，包含節點（假設 / 引理 / 目標）與推導邊 |

---

## 各模組說明

### `config.py` — 全域設定

```python
MODEL_NAME = "Qwen/Qwen2.5-Math-7B-Instruct"
MAX_NEW_TOKENS = 2000
MAX_REPAIR_ATTEMPTS = 3   # 單次生成最多嘗試修復次數
TEMPERATURE = 0.1
```

控制模型名稱、生成 Token 限制、修復次數上限與輸出目錄。`SOURCE_NODE_TYPES` 定義哪些節點類型屬於「來源節點」（不需生成 proof_body）。

---

### `benchmark.py` — 題庫與定理庫

包含三道基準測試題：

1. **鏈式法則** — `d/dx sin(x²) = 2x·cos(x²)`
2. **均值定理（MVT）** — 存在 c ∈ (a,b) 使 f'(c) = (f(b)−f(a))/(b−a)
3. **中間值定理（IVT）** — 連續函數在端點值之間必取到每個中間值

`THEOREM_LIBRARY`：27 條可被 proof_contract 引用的定理／規則名稱清單（如 `chain_rule`, `mean_value_theorem` 等）。

---

### `schemas.py` — JSON Schema

用 JSON Schema（Draft 2020-12）嚴格定義三種資料結構。每次 LLM 輸出後必須通過對應的 Schema 驗證才算成功。

---

### `model_loader.py` — LLM 載入器

```
LLMBackend（dataclass）
├── backend: "hf" | "fallback"
├── generate(prompt, max_new_tokens, json_prefix)
└── load_small_model()  →  4-bit BitsAndBytes 量化載入
```

**重要設計**：
- `json_prefix=True` 在 `<|im_start|>assistant\n` 之後自動附加 `{`，強制模型以 JSON 格式輸出
- 若可用 token 數不足 `MIN_NEW_TOKENS=100`，拋出 `RuntimeError("prompt_too_long: ...")`，觸發緊湊 Prompt 重試機制

---

### `json_utils.py` — JSON 解析與修復

針對 Qwen2.5-Math 特有的輸出問題設計四層修復流程：

```
原始輸出文字
     │
     ├─1─► _fix_unclosed_simple_strings  ← "word) → "word")
     │       （模型在 SymPy 括號前省略閉合引號）
     │
     ├─2─► _fix_close_parens             ← ) → } 或 ]
     │       （模型混用 ) 當 } 或 ] 使用）
     │
     ├─3─► _find_best_complete_json      ← 找第一個平衡的 {...} 區塊
     │
     └─4─► _auto_close + _try_parse_closed  ← 自動補上缺少的 }]/"] 並解析
```

`normalize_json_keys`：去除鍵名前導空格、轉小寫、空格改底線（解決 `" proof_id"` → `"proof_id"` 問題）。

---

### `prompts.py` — Prompt 模板

每個生成步驟提供**兩個版本**的 Prompt：

| 函數 | 用途 |
|---|---|
| `prompt_problem_json` | 附兩個詳細例子，引導生成完整 problem_json |
| `prompt_problem_json_compact` | 簡短版，在 Token 不足時使用 |
| `prompt_proof_contract` | 引導生成 proof_contract，含定理庫清單 |
| `prompt_proof_contract_compact` | 自動篩選相關定理，縮短 Prompt |
| `prompt_graph_skeleton` | 引導生成完整 DAG 結構 |
| `prompt_graph_skeleton_compact` | 只傳入 goal + 前 6 條 references |
| `prompt_node_proof` | 引導為單一節點寫推導步驟 |
| `prompt_node_proof_compact` | 只傳入 claim + refs |
| `prompt_repair_json` | 修復錯誤 JSON，傳入錯誤訊息 |

---

### `generators.py` — 核心生成迴圈

**`generate_json_until_valid`** 是最關鍵的函數，實作「生成→正規化→驗證→修復」迴圈：

```
while True:
    attempt += 1
    raw = model.generate(prompt)           ← 呼叫 LLM
    
    if prompt_too_long:                    ← Token 不足
        retry with compact_prompt          ← 改用緊湊 Prompt
    
    data = parse_json_from_text(raw)       ← JSON 解析與修復
    if normalizer:
        data = normalizer(data)            ← 結構正規化（驗證前）
    validate_or_raise(data, schema)        ← Schema 驗證
    return data                            ← 成功
    
    if attempt >= MAX_REPAIR_ATTEMPTS:     ← 超過上限，拋出例外
        raise RuntimeError
    
    current_prompt = prompt_repair_json(raw, error)  ← 修復 Prompt
```

**三個正規化器**（在驗證前執行，修補模型常見輸出偏差）：

| 正規化器 | 修補內容 |
|---|---|
| `_normalize_problem_json` | 字串版 goal/assumptions/variables/hidden_conditions → 物件格式 |
| `_normalize_proof_contract` | 解包 `{"problem": {...}}` 包裝層；obligations dict→list；補齊必填欄位 |
| `_normalize_graph_state` | 從 nodes 陣列中萃取混入的 inference 物件；補 `proof_id`；修復節點 status 前導空格 |

---

### `verifier_utils.py` — 驗證工具層

提供所有驗證器共用的基礎函數：

- `make_error(...)` — 建立標準錯誤物件
- `is_source_node(node)` — 判斷節點是否為來源節點（assumption/allowed_reference）
- `build_nx_graph(graph_state)` — 將證明圖轉為 NetworkX DiGraph
- `blocking_errors(errors)` — 篩選出阻斷接受的錯誤（high severity 或 blocking_acceptance=True）
- `normalize_math_text(text)` — 標準化數學文字（去空格、轉小寫）用於比對

---

### `verifiers.py` — 多層驗證器

`run_all_verifiers` 依序執行四個驗證層：

```
run_all_verifiers(problem_json, proof_contract, graph_state)
│
├─1─► verify_json_schema         ← 三個結構的 JSON Schema 驗證
│
├─2─► verify_graph_structure     ← 圖結構驗證
│       ├─ 節點／推導 ID 唯一性
│       ├─ 來源節點類型正確性
│       ├─ verify_variable_declarations  ← 符號宣告完整性
│       ├─ verify_obligation_coverage    ← 義務覆蓋率
│       ├─ 推導邊參照節點存在性
│       ├─ rule_refs 在 allowed_references 內
│       ├─ DAG 無環檢查（NetworkX）
│       └─ 目標節點對齊 problem_json.goal
│
├─3─► verify_node_proofs         ← 節點推導驗證
│       └─ proof_body 最後一步是否結論本節點的 claim
│
├─4─► verify_symbolic            ← 符號計算驗證（SymPy）
│       ├─ 解析 d/dx、lim、integral、equation 格式
│       └─ 用 SymPy 驗算數學正確性
│
├─5─► verify_critic              ← LLM Critic 驗證
│       ├─ verify_case_coverage          ← 案例分析是否完整
│       ├─ verify_context_requirements   ← 假設與隱藏條件是否被用到
│       └─ verify_theorem_applicability  ← 定理適用條件是否滿足
│
├─6─► verify_inferences          ← 推導邊驗證
│       └─ rule_refs 非空、前提節點存在
│
└─7─► verify_inference_closure   ← 傳播閉包驗證
        └─ 從來源節點出發能否推導至目標節點
```

**aggregator** 最終判定：無 blocking 錯誤 + 所有 obligations pass + 所有節點與推導邊 verified → `accepted: true`。

---

### `graph_planner.py` — 圖規劃器

提供兩個主要函數：

- **`graph_planner(raw_problem)`**：串接 `generate_problem_json → generate_proof_contract → generate_graph_skeleton`，返回三元組 `(problem_json, proof_contract, graph_state)`
- **`graph_prover(problem_json, proof_contract, graph_state)`**：遍歷所有非來源節點，為尚未有 `proof_body.steps` 的節點呼叫 `generate_node_proof`，填入推導步驟並將節點狀態設為 `"proven"`

---

### `langgraph_nodes.py` — LangGraph 工作流

定義 `ProofAgentState`（TypedDict）與六個節點函數，並用 `StateGraph` 串成線性管線：

```
START
  → problem_parser     (generate_problem_json)
  → contract_builder   (generate_proof_contract)
  → graph_planner      (generate_graph_skeleton)
  → graph_prover       (graph_prover)
  → run_verifiers      (run_all_verifiers)
  → export_trace
  → END
```

每個節點執行後，將本次執行資訊附加到 `trace` 清單，最終可追蹤整個流程的來源與結果。

---

### `main.py` — 主程式入口

1. **Demo 執行**：以 `BENCHMARK_PROBLEMS[0]`（鏈式法則）跑完整管線，印出 `accepted`、`error_count` 與 `trace`
2. **五項測試**（`run_week2_tests`）：

| 測試名稱 | 通過條件 |
|---|---|
| `test_model_loaded_or_declared` | backend == "hf" |
| `test_problem_and_contract_generation` | 3 題至少 2 題通過 Schema 驗證 |
| `test_graph_generation_schema` | 3 題至少 2 題圖 Schema 通過 |
| `test_node_proof_generation` | MVT 所有非來源節點有 proof_body.steps |
| `test_week2_langgraph_pipeline` | 3 題至少 2 題完整管線執行成功 |

測試結果與 Demo 結果儲存到 `week2_outputs/` 目錄。

---

## 執行方式

```powershell
# 使用專案虛擬環境直接執行
& "d:\UserData\claude_project\霓的資料\引導式數學專案\week2\env\python.exe" -u main.py
```

模型第一次執行時會從 Hugging Face 下載 Qwen2.5-Math-7B-Instruct 權重（約 4 GB，4-bit 量化後）。需要 NVIDIA GPU 且支援 CUDA 12.x。

---

## 關鍵設計決策

| 決策 | 原因 |
|---|---|
| **正規化器在驗證前執行** | 若先驗證再正規化，模型輸出永遠無法通過驗證循環 |
| **禁止確定性備用輸出替代 LLM** | 測試必須反映真實模型能力，不允許靜默降級 |
| **緊湊 Prompt 僅在 Token 不足或第一次失敗時觸發** | 保留詳細 Prompt 做為首選，減少資訊損失 |
| **修復 Prompt 使用萃取後的 JSON 片段** | 避免將冗長 CoT 推理文字送入修復 Prompt，減少 Token 浪費 |
| **LangGraph 線性管線** | 清晰的狀態追蹤與 trace 記錄，便於除錯與擴充 |
