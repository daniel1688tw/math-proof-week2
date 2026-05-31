# GitHub 推送指南：math-proof-week2

Repository URL：`https://github.com/daniel1688tw/math-proof-week2.git`

---

## 排除的檔案（.gitignore）

以下項目**不會**被推上 GitHub：

| 排除項目 | 原因 |
|---|---|
| `env/` | Windows 本地虛擬環境，體積大且不跨平台 |
| `.claude/` | Claude Code 本機設定，個人專屬 |
| `.pytest_cache/` | pytest 執行快取，可本地重新產生 |
| `CLAUDE.md` | 本機 AI 開發指令，不屬於公開文件 |
| `week2_graph_model_pipeline_cells(3).ipynb` | 原始開發 Notebook，已重構為模組 |
| `__pycache__/` | Python 編譯快取 |

---

## 日常更新推送

修改程式後，執行以下指令更新 repo：

```powershell
cd "d:\UserData\claude_project\霓的資料\引導式數學專案\week2"

git add generators.py json_utils.py tests/inspect_pipeline.py   # 或 git add .
git status          # 確認即將 commit 的內容
git commit -m "fix: 描述這次修改了什麼"
git push
```

---

## 首次設定（已完成）

Repository 已建立並連結，不需重複執行：

```powershell
git remote add origin https://github.com/daniel1688tw/math-proof-week2.git
git branch -M main
git push -u origin main
```

---

## 常見錯誤處理

**錯誤：`failed to push some refs`（遠端有衝突）**
```powershell
git pull origin main --rebase
git push
```

**錯誤：需要 Token 認證**

GitHub 已停用密碼認證，需使用 Personal Access Token：
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 建立新 token，勾選 `repo` 權限
3. Push 時「密碼」欄填入 token（不是 GitHub 密碼）
或使用 GitHub CLI：
```powershell
gh auth login
```
