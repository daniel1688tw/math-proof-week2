# 推送到 GitHub：math-proof-week2

本文說明如何將此專案推送到 GitHub repository `math-proof-week2`。

---

## 推送前確認：排除的檔案

以下項目已寫入 `.gitignore`，**不會**被推上去：

| 排除項目 | 原因 |
|---|---|
| `env/` | Windows 本地虛擬環境，體積大且不跨平台 |
| `.claude/` | Claude Code 本機設定，個人專屬 |
| `.pytest_cache/` | pytest 執行快取，可本地重新產生 |
| `CLAUDE.md` | 本機 AI 開發指令，不屬於公開文件 |
| `week2_graph_model_pipeline_cells(3).ipynb` | 原始開發 Notebook，已重構為模組 |
| `__pycache__/` | Python 編譯快取 |

---

## 推送步驟

### 步驟 1：在 GitHub 建立 repository

前往 [github.com/new](https://github.com/new)，建立一個新的 repository：

- **Repository name**：`math-proof-week2`
- **Visibility**：Public 或 Private（依個人需求）
- **不要**勾選 "Initialize this repository with a README"（本地已有 README.md）

建立後複製 HTTPS URL，格式如下：
```
https://github.com/<你的帳號>/math-proof-week2.git
```

---

### 步驟 2：在 PowerShell 執行推送指令

```powershell
# 切換到 week2 目錄
cd "d:\UserData\claude_project\霓的資料\引導式數學專案\week2"

# 初始化 git（如果還沒有 .git 資料夾）
git init

# 設定預設分支為 main
git branch -M main

# 確認 .gitignore 有效——確保下列項目「不在」列表中
git status
# 應看不到：env/、.claude/、.pytest_cache/、CLAUDE.md、*.ipynb
```

確認 `git status` 輸出正常後，繼續：

```powershell
# 加入所有未排除的檔案
git add .

# 再次確認即將 commit 的檔案清單
git status
```

**應包含的檔案**（確認這些都在列表中）：
```
benchmark.py
config.py
generators.py
graph_planner.py
json_utils.py
langgraph_nodes.py
main.py
model_loader.py
prompts.py
schemas.py
verifier_utils.py
verifiers.py
README.md
TESTING_GUIDE.md
.gitignore
tests/conftest.py
tests/inspect_pipeline.py
tests/test_01_problem_parser.py
tests/test_02_contract_builder.py
tests/test_03_graph_planner_stage.py
tests/test_04_graph_prover_stage.py
tests/test_05_verifiers.py
tests/test_06_export_trace.py
tests/test_07_pipeline_integration.py
week2_outputs/week2_demo_result.json
week2_outputs/week2_pipeline_summaries.json
week2_outputs/week2_test_results.json
```

```powershell
# 建立第一個 commit
git commit -m "feat: week2 math proof pipeline with LangGraph + 7-stage test suite"

# 連結到你的 GitHub repo（替換為你的帳號）
git remote add origin https://github.com/<你的帳號>/math-proof-week2.git

# 推上去
git push -u origin main
```

---

### 步驟 3：確認推送結果

推送完成後前往：
```
https://github.com/<你的帳號>/math-proof-week2
```

確認以下項目：
- [ ] `README.md` 顯示在 repo 首頁
- [ ] `tests/` 資料夾存在
- [ ] `env/`、`.claude/`、`.pytest_cache/`、`CLAUDE.md`、`.ipynb` 都**不在**repo 中

---

## 後續更新推送

之後修改程式後，用以下指令更新 repo：

```powershell
cd "d:\UserData\claude_project\霓的資料\引導式數學專案\week2"

git add .
git status          # 確認變更內容
git commit -m "fix: 描述這次修改了什麼"
git push
```

---

## 如果 push 遇到錯誤

**錯誤：`remote: Repository not found`**
```powershell
# 確認 remote URL 設定正確
git remote -v
# 若 URL 錯誤，重新設定：
git remote set-url origin https://github.com/<你的帳號>/math-proof-week2.git
```

**錯誤：`failed to push some refs`（遠端有衝突）**
```powershell
# 只有在剛建立空 repo 且 GitHub 幫你建了 README 時才會發生
git pull origin main --allow-unrelated-histories
git push
```

**錯誤：需要 token 認證**

GitHub 已停用密碼認證，需要使用 Personal Access Token：
1. 前往 GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 建立新 token，勾選 `repo` 權限
3. Push 時「密碼」欄位填入 token（不是 GitHub 密碼）
