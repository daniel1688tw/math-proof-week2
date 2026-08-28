# Verify-Then-Generate 高等證明評估判定

## Tested configuration

- 分支與受測 commit：`explore/verify-then-generate`，`a074659`
- 預定 generator：本機 Qwen3-4B 基底模型 + 鎖定的 `dataset/qlora_adapter_v9`
- 預定 verifier：`qwen3-4b-thinking-2507:latest`，本機 Ollama chat API（預設 `http://localhost:11434/api/chat`）
- 預定案例：H1–H8，每題 `baseline` 與 `verify_then_generate` 各一筆，共 16 records
- 預定 judge：`antigravity` / `Gemini 3.6 Flash (Medium)`；本機 `agy 1.1.21` CLI 存在，但本輪在 judging 前即中止
- 實際 runtime：NVIDIA GeForce GTX 1650 4 GiB；Ollama API 可連線，但只有 `mistral:latest`、`llama3.2:1b`
- 阻塞先決條件：`dataset/qlora_adapter_v9` 不存在；Ollama 缺指定 verifier tag；`lora_project` 缺 `accelerate` 與 `peft`

## Deterministic verification

| 命令 | 測試總數／可觀測通過數 | Exit code | 結果 |
|---|---:|---:|---|
| `python dataset\test_driver_unit.py` | 362 個 `✓` checks | 0 | 通過 |
| `python dataset\test_review_workflow.py` | 19 個 test functions | 0 | 通過 |
| `python dataset\test_phase_routing.py` | 57 個 `OK` checks | 0 | 通過 |
| `python dataset\test_verify_then_generate_eval.py` | 1 個 helper suite pass marker | 0 | 通過 |
| `python dataset\regression_suite.py --quick` | Tier 0：7/7 子套件 | 0 | 通過 |

為取得數值總數，另重跑 driver、phase 與 evaluator-helper 測試做唯讀計數；三者仍為 exit 0。Review workflow 的 19 是 source 中的 `test_*` function 數，原始 runtime 為 exit 0。Quick gate 產生 `dataset/regression_scores/2026-08-28T213353_a074659.json`，其中 `tier0=1.0`，未更新 baseline。

## Paired results

正式命令以本機可用的 Conda 絕對路徑執行：

```powershell
$env:PYTHONNOUSERSITE = "1"
& "C:\Users\Danie\anaconda3\Scripts\conda.exe" run -n lora_project --live-stream python dataset\eval_verify_then_generate.py
```

命令 exit 1；`AutoModelForCausalLM.from_pretrained` 在載入 generator 時因缺 `accelerate` 中止。Evaluator 尚未生成任何 reply、record、JSON 或 Markdown，故沒有合法的 `--rejudge` 輸入。

| 指標 | baseline | verify-then-generate | 差值 |
|---|---:|---:|---:|
| records | 0/8 | 0/8 | N/A |
| `first_error_hit` | N/A | N/A | N/A |
| `targetedness` | N/A | N/A | N/A |
| `math_correct` | N/A | N/A | N/A |
| `guidance` | N/A | N/A | N/A |
| `reveal_safe` | N/A | N/A | N/A |
| single-question | N/A | N/A | N/A |
| no-reference-leak | N/A | N/A | N/A |
| latency | N/A | N/A | N/A |

「0 records」表示評估未開始，不表示零退化。Latency delta 亦不可估計。

## Case-level regressions

H1–H8 均沒有 baseline/treatment reply，因此無從逐案比較，也不能把任何案例宣告為「無退化」。本輪沒有可依 `first_error_hit`、`math_correct`、`guidance`、`reveal_safe`、single-question 或 no-leak 篩出的 losing/ambiguous pair；原因是 generator 載入前的環境失敗，而非 verifier error、prompt-grounding error、v9 wording error、post-guard interaction 或 judge ambiguity。

## Existing regression gate

- Quick suite：exit 0；Tier 0 的 7/7 子套件通過，`tier0=1.0` 與基準相等。
- Full suite：以相同 Conda 環境執行 `dataset\regression_suite.py`，Tier 0 的 7/7 子套件先通過，接著在 `load_model()` 匯入 `peft` 時 exit 1。
- 精確 incomplete tier：Tier 1（zh，GPU 生成）尚未開始；Tier 1 zh/en、Tier 1b zh/en、Tier 2 zh/en、Tier 3 zh/en、S4 zh/en 與 Tier 4 均未執行。這不是 full-suite pass，也不是 judge-incomplete exit 2。
- 本輪未使用 `--update-baseline`，亦未修改 regression baseline。

## Decision

**BLOCKED / INCONCLUSIVE（評估受阻、暫不採用；待 runtime/model prerequisites 修復後重評）。**

採用條件要求 deterministic tests 與 regression gates 均通過、安全／數學指標不下降，且 first-error targeting 或 targetedness 有可量測改善。本輪只有 deterministic gate 與 quick suite 通過；paired quality、latency、逐案退化及 full regression 都沒有完成，所以目前無法判斷方法品質，也沒有證據支持 adopt 或 conditional adopt。這是評估受阻後的暫不採用，不是對 verify-then-generate 方法的品質否決。

重跑前至少需：恢復鎖定的 `qlora_adapter_v9`、補齊 `lora_project` 的 `accelerate`／`peft`、提供指定 Ollama verifier tag，並確認硬體可載入部署精度模型。功能 rollback／保持停用方式：`VERIFY_THEN_GENERATE=0`。
