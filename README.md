# 引導式數學專案 Week 2：小模型 + 圖形證明器

以 **Qwen/Qwen2.5-Math-7B-Instruct**（4-bit 量化）為核心 LLM，實作一套自動微積分證明生成與驗證系統。輸入一道微積分題目的文字描述，系統依序生成結構化問題資訊、證明契約、有向無環證明圖（DAG），逐節點填入推導步驟，最後通過多層驗證器評判接受度，整個流程以 **LangGraph StateGraph** 串接。

---

## 系統流程

```
原始題目文字
     ↓
problem_parser   → problem_json（問題結構化）
     ↓
contract_builder → proof_contract（可用定理、義務清單）
     ↓
graph_planner    → proof_graph_state（DAG 骨架）
     ↓
graph_prover     → 逐節點生成 proof_body
     ↓
run_verifiers    → 多層驗證（結構 / 符號 / Critic）
     ↓
accepted: true / false
```

---

## 環境需求

| 項目 | 規格 |
|---|---|
| Python | 3.11 |
| GPU | NVIDIA，建議 ≥ 6 GB VRAM（RTX 4050 可執行） |
| CUDA | 12.x |
| 模型 | Qwen/Qwen2.5-Math-7B-Instruct（自動從 HuggingFace 下載） |

### 安裝依賴

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate bitsandbytes peft
pip install jsonschema networkx sympy langgraph
pip install sentencepiece huggingface_hub safetensors
```

---

## 快速開始

```bash
# 執行完整流程（Demo + 五項測試）
python main.py

# 逐 Stage 檢查特定題目（支援 --problem 0/1/2）
python tests/inspect_pipeline.py --problem 2
```

執行完後會在 `week2_outputs/` 產生：

```
week2_outputs/
├── week2_demo_result.json          # Demo 題目的完整 trace
├── week2_test_results.json         # 五項測試通過/失敗
├── week2_pipeline_summaries.json   # 三道基準題的管線摘要
└── inspect/                        # inspect_pipeline.py 逐 Stage 輸出
    ├── stage1_problem_json.json
    ├── stage2_proof_contract.json
    ├── stage3_graph_skeleton.json
    ├── stage4_proven_graph.json
    ├── stage5_verifier_result.json
    ├── stage6_trace.json
    └── report.md
```

---

## 專案結構

```
week2/
├── main.py              # 主程式入口（Demo + 測試套件）
├── config.py            # 全域設定（模型、Token 限制、修復次數）
├── benchmark.py         # 基準測試題庫（3 道微積分題）與定理庫
├── schemas.py           # JSON Schema（三種資料結構）
├── model_loader.py      # HF 模型載入（4-bit BitsAndBytes 量化）
├── json_utils.py        # JSON 解析與自動修復（處理 Qwen 輸出特性）
├── prompts.py           # Prompt 模板（一般版 + 緊湊版）
├── generators.py        # 核心生成迴圈（生成 → 正規化 → 驗證）
├── graph_planner.py     # 圖規劃器與節點證明填充
├── langgraph_nodes.py   # LangGraph StateGraph 定義
├── verifiers.py         # 多層驗證器
├── verifier_utils.py    # 驗證工具函數
└── tests/
    ├── inspect_pipeline.py          # 逐 Stage 互動式檢查工具
    ├── test_01_problem_parser.py
    ├── test_02_contract_builder.py
    ├── test_03_graph_planner_stage.py
    ├── test_04_graph_prover_stage.py
    ├── test_05_verifiers.py
    ├── test_06_export_trace.py
    └── test_07_pipeline_integration.py
```

---

## 基準測試題目

| 題目 | 類型 |
|---|---|
| 鏈式法則：`d/dx sin(x²) = 2x·cos(x²)` | chain_rule |
| 均值定理（MVT）：存在 c 使 f'(c) = (f(b)−f(a))/(b−a) | mean_value_theorem |
| 中間值定理（IVT）：連續函數必取到端點值之間的每個值 | intermediate_value_theorem |

測試標準：五項自動測試，三道題至少通過兩題視為整體通過。

---

## 多層驗證架構

```
run_all_verifiers
├── JSON Schema 驗證
├── 圖結構驗證（DAG、節點唯一性、推導邊參照）
├── 節點推導驗證（proof_body 最後一步是否結論節點 claim）
├── 符號計算驗證（SymPy：微分、極限、積分）
├── LLM Critic 驗證（案例覆蓋、假設使用、定理適用條件）
├── 推導邊驗證（rule_refs 非空、前提節點存在）
└── 傳播閉包驗證（從來源節點能否推導至目標節點）
```

---

## JSON 自動修復機制（json_utils.py）

Qwen2.5-Math 模型的輸出常帶有特殊格式問題，`json_utils.py` 實作了一套修復流水線：

| 修復函數 | 處理的問題 |
|---|---|
| `_fix_invalid_json_escapes` | 修復 LaTeX 反斜線（`\frac`、`\[` 等） |
| `_fix_quoted_object_start` | 修復 `"{ key"` → `{ "key"`（引號錯位） |
| `_fix_unclosed_strings_with_parens` | 修復未閉合字串（以括號深度判斷 `)` 是否為結構符號） |
| `_fix_unclosed_simple_strings` | 修復 `"word)` → `"word")`（簡單單詞未閉合） |
| `_fix_close_parens` | 將 `)` 替換為對應的 `}` 或 `]`；丟棄多餘的 `}` / `]` |
| `_auto_close` + `_try_parse_closed` | 截斷輸出的自動補全與啟發式修復 |

---

## 確定性 Fallback 機制

當 LLM 所有修復嘗試均失敗時，各 Stage 使用 `_make_fallback_*` 函數產生高品質預設值：

- **Stage 1**：從 benchmark hint 取得正確的 `goal.symbolic`（如 `Eq(f(c), N)`）、變數清單與 `problem_id`，確保後續 Stage 能正常解析
- **Stage 3**（Graph Planner）：從 `proof_contract.obligations` 直接生成節點，不依賴 LLM

---

## 關鍵設計

- **正規化器在 Schema 驗證前執行**：修補模型常見輸出偏差（包裝層、obligations 格式、節點 status 空格）
- **禁止確定性備用輸出**：`REQUIRE_HF_MODEL_FOR_TESTS = True`，測試必須反映真實模型能力
- **緊湊 Prompt 備用機制**：Token 不足或首次失敗時自動切換，最多修復 3 次
- **`json_prefix=True`**：強制模型從 `{` 開始輸出，提高 JSON 生成成功率

---

## 設定參數

| 參數 | 預設值 | 說明 |
|---|---|---|
| `MODEL_NAME` | `Qwen/Qwen2.5-Math-7B-Instruct` | HuggingFace 模型 ID |
| `USE_4BIT_IF_AVAILABLE` | `True` | 是否啟用 4-bit 量化 |
| `MAX_NEW_TOKENS` | `2000` | 單次生成最大 Token 數 |
| `MAX_REPAIR_ATTEMPTS` | `3` | JSON 修復最大嘗試次數 |
| `TEMPERATURE` | `0.1` | 生成溫度 |

修改 `config.py` 即可調整所有參數。
