# Git 推送範圍記錄

> 本檔記錄 `week3/` 這個 git repo 推送到 GitHub 時「該推什麼、不該推什麼」，
> 供未來新增檔案或再次推送時對照，避免又要重新判斷一次。

- Repo：https://github.com/daniel1688tw/math-proof-week2
- 目前分支：`lora-finetune`（從空白建立，不基於遠端既有分支）
- `week3/` 是本地 git repo 根目錄（原本不是 git repo，2026-07-02 才 `git init`）

---

## 會推送的範圍

| 路徑 | 內容 | 為什麼推 |
|---|---|---|
| `CLAUDE.md`、`dataset_plan.md`、`socratic_math_research.md`、`PUSH_SCOPE.md` | 專案說明文件 | 提供上下文，不含機密 |
| `learn_path/架構設計.md`、`learn_path/improve.md`、`learn_path/_probe_env.py` | 子系統 A/B 架構說明、環境健檢腳本 | 文字/小型腳本，說明 LoRA 訓練架構的設計脈絡 |
| `learn_path/socratic_tutor/*.py`、`*.md`、`*.json` | QLoRA 訓練/推論/評估腳本 | 程式碼與設定，體積小 |
| `learn_path/socratic_tutor/data/` | 舊版訓練資料（MathDial+GSM8K，5.8MB） | 純文字 jsonl，可重現訓練 |
| `learn_path/socratic_tutor/eval_out/` | 評估報告與生成結果 | 純文字/JSON |
| `dataset/` 整個目錄（除 `qlora_adapter_v*/`） | 手寫 grounded 資料集 + build/validate/test/eval 腳本 + 各版評估報告（`eval_out_v2`～`v4`、`eval_out_hard`）+ 訓練/評估 log | 這是本專案的核心產出，全是文字檔（.py/.json/.jsonl/.md/.log） |

**判斷原則**：程式碼、設定檔、資料集（jsonl/json）、Markdown 報告、log → 一律推送，這些都小且是可重現訓練的必要材料。

**明確排除在「LoRA 相關」範圍之外、不推的東西**（屬於 Ollama 無微調 baseline 路線或本機設定，
與本分支主題無關，不要不小心用 `git add -A` 撈進去）：
`simple_4B_ollama.py`、`run_compare_simple.py`、`run_eval_4b_ollama.py`、`run_smoke_4b_ollama.py`、
`架構.md`、`ollama_model.txt`、`Modelfile.qwen3-4b-thinking`、`archive/`、
`learn_path/best_grounded_tutor/`、`learn_path/ollama_model.txt`、`.claude/`（本機 Claude Code 設定）。

---

## 不會推送的範圍（`.gitignore` 已設定）

| 路徑/模式 | 內容 | 為什麼不推 |
|---|---|---|
| `learn_path/socratic_tutor/qwen3_4b/` | 基底模型權重 | **7.6GB**，且是公開 HF 模型（`Qwen/Qwen3-4B-Instruct-2507`），不該存進 repo |
| `gguf/`、`*.gguf` | GGUF 量化模型 | 大型二進位檔，屬於本機推論用途 |
| `qlora_adapter/`、`qlora_adapter_v*/`（萬用字元，涵蓋 v2/v3/v4/v5…所有未來版本） | LoRA adapter 權重目錄 | 內含 `adapter_model.safetensors`（**132MB**），**超過 GitHub 單檔 100MB 硬限制**，一般 push 會被拒絕 |
| `*.safetensors` | 任何權重檔 | 同上，全域排除 |
| `__pycache__/`、`*.pyc` | Python 快取 | 無意義的產物 |
| `*/_checkpoints/` | 訓練中途 checkpoint | 與最終 adapter 重複，且同樣是大型權重 |

**判斷原則**：任何模型權重（`.safetensors`、`.gguf`）、超過 100MB 的二進位檔、訓練中途產物 → 一律不推。

> ⚠️ **曾發生的問題**：`.gitignore` 一開始把 `qlora_adapter_v2/`、`qlora_adapter_v3/` 寫死成
> 明確路徑，後來新增 `qlora_adapter_v4/`、`v5/` 時沒被排除到（`git status` 顯示為未追蹤）。
> 已改成萬用字元 `qlora_adapter_v*/`，之後新版號會自動涵蓋，不用每次手動補規則。
> **每次訓練出新版 adapter 後，務必先 `git status --short | grep qlora_adapter` 確認被排除。**

---

## 若之後想推送 adapter 權重本身

目前 132MB 的 `adapter_model.safetensors` 超過 GitHub 100MB 硬限制，若未來需要把權重也放上去，二選一：

1. **Git LFS**（推薦）：
   ```powershell
   git lfs install
   git lfs track "*.safetensors"
   git add .gitattributes
   git add qlora_adapter_v3/adapter_model.safetensors qlora_adapter_v3/adapter_config.json `
           qlora_adapter_v3/tokenizer.json qlora_adapter_v3/tokenizer_config.json `
           qlora_adapter_v3/chat_template.jinja
   git commit -m "Track adapter weights via Git LFS"
   git push
   ```
   注意：不要連 `_checkpoints/` 一起加，只加最終 adapter。

2. **改放 Hugging Face Hub**（更適合權重檔案，無 100MB 限制、有版本管理）：
   ```powershell
   huggingface-cli upload <你的帳號>/socratic-tutor-lora qlora_adapter_v3/ .
   ```

---

## 下次要推送新內容時的檢查清單

1. `git status --short` 看有沒有新檔案跑進不該進的目錄（尤其是新產生的 `qlora_adapter_v*` 或新的模型資料夾）。
2. 若新增了模型/adapter 目錄，記得在 `.gitignore` 補一行，或確認舊規則的萬用字元（如 `*.safetensors`）已涵蓋。
3. `git add <明確路徑>`，不要用 `git add -A`（避免不小心撈進大檔或機密檔）。
4. `git diff --cached --stat | tail -1` 檢查變更檔案數與行數是否合理。
5. `git status --short | grep -iE "\.env|credential|secret|token|api_key"` 確認沒有機密檔混入。
6. Commit 訊息用英文、說明「做了什麼＋為什麼」，不用 `--no-verify`。

---

*建立日期：2026-07-02，對應 commit `71a40cc`（89 檔案、18,362 行，分支 `lora-finetune`）。*
*更新日期：2026-07-03——補 v4/v5 adapter 的 `.gitignore` 萬用字元修正、`.claude/` 排除、
新增分級提示相關檔案（`dataset/src/dialogues_hint.py`、`eval_hint_escalation.py` 等）；
尚未推送這批新內容，見上方「下次要推送新內容時的檢查清單」。*
