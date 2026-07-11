# Git 推送範圍記錄

> 記錄 `week3/` repo 推送 GitHub 時「該推什麼、不該推什麼」，供未來對照。

- Repo：https://github.com/daniel1688tw/math-proof-week2
- 分支：`lora-finetune`
- **版本策略（2026-07-11 起）**：工作目錄只保留目前最佳方法（v6 + driver）。
  所有歷史方法（MathDial 行為遷移、Ollama 路線、adapter v2–v5 評估）保存在
  git tag **`experiments-v2-v6`**，不要再把舊版本加回工作目錄。

---

## 會推送的範圍

| 路徑 | 內容 |
|---|---|
| `README.md`、`CLAUDE.md`、`PUSH_SCOPE.md`、`dataset_plan.md`、`socratic_math_research.md` | 說明與設計文件 |
| `dataset/`（除權重與 log） | 資料集源碼、建置/驗證/測試/評估腳本、driver、現行評估報告（eval_out_final/v6/hard/driver）|
| `learn_path/socratic_tutor/` 的 4 個檔案 | `common.py`、`train_qlora.py`、`download_chunked.py`、`test_4bit_load.py` |

**判斷原則**：程式碼、設定、資料集（json/jsonl）、Markdown 報告 → 推送。

## 不推送（`.gitignore` 已設定）

| 模式 | 原因 |
|---|---|
| `learn_path/socratic_tutor/qwen3_4b/` | 基底模型 7.6GB，公開 HF 模型不該進 repo |
| `qlora_adapter/`、`qlora_adapter_v*/`、`*.safetensors` | adapter 權重 132MB 超過 GitHub 100MB 限制（本機只留 v6）|
| `gguf/`、`*.gguf` | 舊 Ollama 路線的本機量化模型（方法已淘汰，檔案留本機以免重新下載之苦）|
| `*/_checkpoints/` | 訓練中途 checkpoint |
| `*.log`、`*.zip`、`__pycache__/`、`.claude/` | 過程產物與本機設定；zip 用 `git archive -o pkg.zip HEAD` 隨時可重生 |

**判斷原則**：權重、>100MB 二進位、訓練中途產物、log → 不推。

> ⚠️ 教訓存檔：`.gitignore` 曾把 adapter 版本寫死（v2/v3），新版本（v4/v5）沒被涵蓋，
> 已改萬用字元 `qlora_adapter_v*/`。每次訓練出新 adapter 後跑
> `git status --short | grep qlora_adapter` 確認被排除。

---

## 若要發佈 adapter 權重

GitHub 檔案上限 100MB，二選一：
1. **Hugging Face Hub**（推薦）：`huggingface-cli upload <帳號>/socratic-tutor-lora dataset/qlora_adapter_v6 .`
2. **Git LFS**：`git lfs track "*.safetensors"` 後只加最終 adapter（勿含 `_checkpoints/`）。

## 推送前檢查清單

1. `git status --short | grep -E "qlora_adapter|safetensors|gguf|zip"` → 應無輸出
2. `git add <明確路徑>`，不要 `git add -A` 摸黑全加（快照 commit 除外）
3. `git status --short | grep -iE "\.env|credential|secret|token|api_key"` → 應無輸出
4. Commit 訊息英文、寫「做了什麼＋為什麼」

---

*2026-07-02 建立；2026-07-11 更新——工作目錄縮減為單一方法，歷史入 tag `experiments-v2-v6`。*
