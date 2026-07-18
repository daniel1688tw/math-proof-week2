# 評審後端遷移計劃：Antigravity CLI（`agy`）作為 Claude Sonnet 的替代/備援

**狀態：計劃書，尚未實作。** 現行部署與守門**繼續使用 `claude` CLI（Sonnet）當評審**。
本文件記錄可行性驗證結果與未來要換時的具體步驟，等真正需要時再照此實作。

---

## 一、為什麼考慮換

- 守門完整跑一輪需 Claude 評審 100+ 次；Claude Pro 額度中斷會打斷整輪
  （已有 `--gen-only`／`--rejudge`／`auto_gate` 續評機制緩解，但仍受限）。
- Antigravity CLI 免費預覽期若額度充足，可作為**備援評審**（Claude 限額時切換）或
  **雙評審交叉驗證**（降低單一評審雜訊，見弱點 #6）。

## 二、可行性驗證結果（2026-07-18，已實測）

| 項目 | 結果 |
|---|---|
| CLI 存在與安裝 | ✅ `agy.exe` v1.1.4，`irm https://antigravity.google/cli/install.ps1 \| iex`，裝到 `%LOCALAPPDATA%\agy\bin`，SHA512 校驗 |
| 無頭模式 | ✅ `agy -p "<prompt>"`（別名 `--print`／`--prompt`）單次非互動、回純文字到 stdout、exit 0 |
| 授權 | ✅ 沿用已安裝並登入的 **Antigravity IDE** 憑證，無需另外登入（實測 `-p` 直接回應） |
| 相關旗標 | `--model`、`--print-timeout`（預設 5m）、`--dangerously-skip-permissions` |

**已知風險（實測觀察）：**
1. **額度非 Gemini Pro 消費訂閱**：綁 Antigravity 帳號（免費預覽自有額度），非
   gemini.google.com 的 Pro 方案。要換帳號＝在 Antigravity IDE 內重新登入。
2. **後端連線時好時壞**：`agy models` 多次呼叫會 hang（限流或網路）。批次連呼 100+ 次
   的穩定性**尚未驗證**，是換用前最大的未知數。
3. **方法論斷點**：現行基準以 Claude Sonnet 建立；換評審＝換尺，reveal/score 拿捏不同，
   **基準須整套重建**，不可與 Claude 基準混比。

## 三、程式面：架構已預留（無需大改）

`regression_suite.py` 已有抽象層：
- `JUDGE_BACKEND` 環境變數（`claude` | `gemini`）。
- `_judge_cmd()` 依後端組命令列。
- 各後端獨立基準檔（如 `regression_baseline_gemini.json`），`record` 記 `judge_backend`。

要接 `agy` 只需在 `_judge_cmd()` 增加一個分支，**不動守門主流程**。

## 四、實作步驟（未來需要時照做）

1. **接後端**：在 `_judge_cmd()` 增 `antigravity` 分支：
   ```
   [agy_path, "-p", prompt, "--print-timeout", "3m"]
   ```
   （必要時加 `--model <gemini-model>`；模型清單待 `agy models` 穩定後確認。）
   `claude_call` 的限流重試正則需增列 agy 的限額/逾時訊息樣式。
2. **穩定性壓測**（**換用前必做**）：寫一支小腳本，連續呼叫 `agy -p` 120 次
   （模擬一輪守門的評審量），量測：JSON 可解析率、平均延遲、hang/限流發生率。
   通不過就不換。
3. **JSON 契約驗證**：用 §五的對照集，確認 agy 對評審 prompt 穩定回**可解析 JSON**
   （無 code fence、無多餘散文）。必要時在 prompt 加更硬的格式約束。
4. **雙評審對照**：同一批已存檔對話（`regression_scores/*_dialogues.json`、`*_replies.json`）
   分別用 `claude` 與 `agy` 評，比對 math_ok/reveal_ok/score 一致率，量化評審尺差異。
5. **重建基準**：`JUDGE_BACKEND=antigravity` 跑一輪完整守門，產出
   `regression_baseline_gemini.json`（或 `_antigravity.json`）作為該後端的獨立地板。
6. **定位角色**：決定 agy 是（a）Claude 限額時的**備援**、（b）**雙評審交叉**、
   還是（c）**主評審**。建議先做 (a)/(b)，主評審維持 Claude 直到穩定性充分驗證。

## 五、對照驗證清單（步驟 2–4 用）

- 輸入：`dataset/regression_scores/` 內既有的 `*_replies.json` / `*_dialogues.json`（已存檔、
  不需重跑 GPU）。
- 指標：JSON 可解析率 ≥99%、連續 120 呼叫零 hang、與 Claude 評分一致率（math_ok/reveal_ok
  逐項、score ±1）。
- 通過門檻：穩定性達標且尺差可量化，才進入 §四步驟 5 重建基準。

---

## 現行決策

**維持 `claude` CLI（Sonnet）當評審。** 本計劃備而不用；未來 Claude 額度成為瓶頸、
或想加雙評審降雜訊時，再依 §四實作。`agy` 已安裝可隨時實測，架構已預留接點。
