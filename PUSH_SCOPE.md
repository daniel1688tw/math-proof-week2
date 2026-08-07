# Git 推送範圍記錄

> 記錄 `week3/` repo 推送 GitHub 時「該推什麼、不該推什麼」，供未來對照。

- Repo：https://github.com/daniel1688tw/math-proof-week2
- 最終版分支：**`feature/product-ui`**（部署形態 = `qlora_adapter_v9` + TutorDriver + 審閱後盾 + Gradio 介面）
- **版本策略（2026-07-11 起）**：工作目錄只保留目前最佳方法。被淘汰的方法
  （MathDial 行為遷移、Ollama 無微調路線、adapter v2–v5 評估）保存在
  git tag **`experiments-v2-v6`**，不要再把舊版本加回工作目錄。
- **v10／v11 兩輪整體重訓皆守門判退**，adapter 封存本機（gitignore）供分析；
  版號越新不代表越該用。

---

## 會推送的範圍

| 路徑 | 內容 |
|---|---|
| `README.md`、`CLAUDE.md`、`PUSH_SCOPE.md`、`update.md`、`專案架構設計.md` | 對外說明、迭代紀錄、版本差異、架構權威來源 |
| `專題成果報告.md`、`使用者說明書.md` | 論文式報告與使用者操作說明 |
| `專題簡報.pptx` | 專題簡報（19 張，16:9）。**二進位但只有 ~100KB**，遠低於 GitHub 限制；<br>由 scratchpad 的產生腳本輸出，要改內容請改腳本重跑而非手改投影片 |
| `模擬對答過程.md` | 守門對話紀錄的根目錄閱讀版（8/7 那輪的定格快照）|
| `dataset_plan.md`、`socratic_math_research.md`、`self_verified_teaching_design.md` | 設計文件 |
| `dataset/`（除權重與 `__pycache__`）| 資料集源碼、建置/驗證/測試/評估腳本、driver、備課管線、介面、評估報告 |
| `dataset/regression_scores/` | 歷次守門計分卡與**對話存檔**——`test_phase_routing.py` 以它為回放語料，**不可刪** |
| `learn_path/socratic_tutor/` 的 4 個檔案 | `common.py`、`train_qlora.py`、`download_chunked.py`、`test_4bit_load.py` |
| `server_train/` | 伺服器端訓練管線（Dockerfile、compose、workspace）|
| `docs/` | code review、Notion 內容源、superpowers spec 與實作計畫 |
| `.claude/skills/pre-push-check/` | 推送前守門流程 skill |

**判斷原則**：程式碼、設定、資料集（json/jsonl）、Markdown 報告 → 推送。

## 不推送（`.gitignore` 已設定）

| 模式 | 原因 |
|---|---|
| `learn_path/socratic_tutor/qwen3_4b/` | 基底模型 ~8GB，公開 HF 模型不該進 repo |
| `qlora_adapter/`、`qlora_adapter_v*/`、`*.safetensors` | adapter 權重 132MB 超過 GitHub 100MB 限制 |
| `gguf/`、`*.gguf` | 舊 Ollama 路線的本機量化模型（方法已淘汰，檔案留本機以免重新下載之苦）|
| `COMMANDS.md` | **含伺服器存取資訊**，絕不進版控 |
| `*/_checkpoints/` | 訓練中途 checkpoint |
| `*.log`、`*.zip`、`*.ipynb` 草稿、`__pycache__/`、`.claude/settings.local.json`、`.superpowers/` | 過程產物與本機設定 |

**判斷原則**：權重、>100MB 二進位、訓練中途產物、log、機密 → 不推。

> ⚠️ 教訓存檔：`.gitignore` 曾把 adapter 版本寫死（v2/v3），新版本（v4/v5）沒被涵蓋，
> 已改萬用字元 `qlora_adapter_v*/`。每次訓練出新 adapter 後跑
> `git status --short | grep qlora_adapter` 確認被排除。

---

## 若要發佈 adapter 權重

GitHub 檔案上限 100MB，二選一：
1. **Hugging Face Hub**（推薦）：`huggingface-cli upload <帳號>/socratic-tutor-lora dataset/qlora_adapter_v9 .`
2. **Git LFS**：`git lfs track "*.safetensors"` 後只加最終 adapter（勿含 `_checkpoints/`）。

## 推送前檢查清單

1. 跑守門：`python dataset\regression_suite.py`（或 skill `/pre-push-check`），**exit 0 才可推**
2. `git status --short | grep -E "qlora_adapter|safetensors|gguf|zip"` → 應無輸出
3. `git add <明確路徑>`，不要 `git add -A` 摸黑全加（快照 commit 除外）
4. `git status --short | grep -iE "\.env|credential|secret|token|api_key|COMMANDS"` → 應無輸出
5. Commit 訊息寫「做了什麼＋為什麼」

---

*2026-07-02 建立；2026-07-11 工作目錄縮減為單一方法，歷史入 tag `experiments-v2-v6`；
2026-08-07 更新——最終版分支改為 `feature/product-ui`，補上守門存檔與機密檔案條目。*
