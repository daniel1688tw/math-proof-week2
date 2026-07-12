---
name: pre-push-check
description: 推送 GitHub 前的品質守門：跑全自動回歸套件（Claude 當評審與學生）、比對基準、檢查推送範圍，給出「可推 / 不可推」判定。使用者說「推之前先測」「跑回歸」「pre-push」時使用。
---

# 推送前品質守門（week3 蘇格拉底助教專案）

目標：**每個版本只進步不退步**。推送前依序執行以下步驟，任何一步失敗就停下回報，不要推送。

## 步驟 1：快速檢查（~1 分鐘，先擋低級錯誤）

```powershell
$env:PYTHONUTF8 = "1"
& "D:\Danie\anaconda3\envs\lora_project\python.exe" dataset\regression_suite.py --quick
```

exit code ≠ 0 → 單元測試或資料集驗證壞了，直接回報失敗原因並停止。

## 步驟 2：完整回歸（~1.5 小時，背景執行）

前置確認（都不滿足要先回報）：
- `nvidia-smi` 顯存乾淨（≈0 MiB；有孤兒 python 佔用先清）
- `claude --version` 可用（Tier 2/3 評審與學生角色必需）
- Ollama 在線則 Tier 4 一併跑，不在線會自動跳過（不算失敗）

```powershell
$env:PYTHONUTF8 = "1"; $env:PYTHONUNBUFFERED = "1"
& "D:\Danie\anaconda3\envs\lora_project\python.exe" dataset\regression_suite.py
```

用 run_in_background 跑，靠完成通知接續（排程喚醒只當保底，不可靠）。

## 步驟 3：判讀結果

套件會產出 `dataset/regression_scores/<ts>_<sha>.json` 並自動與
`dataset/regression_baseline.json` 比較（確定性指標零容忍、judge_* 容忍 ε=0.05）。

- **exit 0（全過）**：繼續步驟 4。若多項指標明顯上升，建議使用者跑
  `--update-baseline` 抬高基準（基準只升不降）。
- **exit 1（有退步）**：列出退步的指標與對應的失敗案例（計分卡 JSON 裡有），
  讀 `regression_scores/<ts>_<sha>_dialogues.json` 檢視多輪對話哪裡出問題，
  診斷根因後回報。**不要推送**，除非使用者明確說接受此退步。

另外必做的質性抽查（不只看數字）：
- 打開 `*_dialogues.json`，親自讀 3 場 Claude-學生對話全文，確認助教沒有
  「數字上過關但實際誤導」的回覆（評審偶有漏判）。
- `judge_math_ok` < 1.0 時，逐筆看 issue 欄位，判斷是評審誤判還是真錯；
  真錯要回報使用者，這是「不誤導學生」的硬底線。

## 步驟 4：推送範圍檢查（PUSH_SCOPE.md 的檢查清單）

```powershell
git status --short | Select-String -Pattern "qlora_adapter|safetensors|gguf|zip"   # 應無輸出
git status --short | Select-String -Pattern "\.env|credential|secret|token|api_key" # 應無輸出
```

- 權重、>100MB 二進位、log、zip 不推；`regression_scores/` 的計分卡 JSON **要推**（版本歷史）。
- commit 訊息英文、寫「做了什麼＋為什麼」，結尾加 Co-Authored-By。
- `git add` 用明確路徑，不要 `git add -A`。

## 步驟 5：判定回報

以表格回報使用者：各指標 vs 基準、質性抽查發現、推送範圍檢查結果，
最後給明確結論：「✓ 可推送」或「✗ 不可推送＋原因＋建議修法」。
使用者同意後才執行 push。

## 背景知識

- 套件設計說明在 `dataset/regression_suite.py` docstring；指標定義：
  確定性（s1_structural / s3_refusal / escalation / walkthrough / single_question）
  ＋ Claude 評審（judge_math_ok / judge_s2_catch / judge_score /
  judge_dialogue_math_ok / judge_dialogue_guidance / judge_backstop）。
- 評審模型用環境變數 `JUDGE_MODEL` 覆寫（預設 sonnet）。
- 深度題庫：held_out 8 + hard_math_major 5（含 Darboux）+ xdomain 6；
  新增評估題後記得在 regression_suite.py 的 DEEP_IDS / DIALOGUE_CASES 擴充。
