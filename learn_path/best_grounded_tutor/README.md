# best_grounded_tutor — 最佳方法（Solution-grounded 蘇格拉底助教）

這是 `learn_path` 完整評估中**表現最好且最安全**的方法，獨立打包成一個可單獨運行的資料夾。

- held-out 教學品質 **4.42/5**（與「思考型+純prompt」並列第一，勝過微調 4.04、base 3.63）
- 在「**數學正確 + 不洩漏答案**」上最穩：難題與正確性敏感題勝出（詳見
  [`../socratic_tutor/eval_out/EVAL_REPORT.md`](../socratic_tutor/eval_out/EVAL_REPORT.md)）

## 核心理念：把「會解」與「會教」解耦

```
題目 ──► (1) 思考型模型先產出完整證明 ──► 參考解（答案卡，學生看不到）
                                              │
學生對話 ─────────────────────────────────────► (2) 引導層把參考解放進 system（隱藏），
                                                  只問引導問句、絕不洩漏答案
```

老師「知道答案」才問得出指向**正確**下一步的問題，藉此擋住小模型「自信給錯提示」的風險
（評估中微調模型曾把 ε-δ 題誤導成「配方」、把均勻連續題直接洩漏 Heine-Cantor）。

## 為什麼這個資料夾可以獨立運行

- **零第三方依賴**：`grounded_tutor.py` 只用 Python 標準函式庫（`urllib`）。
- **不需要** torch / transformers / bitsandbytes / 微調權重 / 訓練。
- 唯一外部需求：本機 **Ollama** 在跑，且已 pull 一個**思考型**模型。

## 安裝與執行

```powershell
# 1) 安裝並啟動 Ollama（https://ollama.com），服務預設 http://localhost:11434
# 2) 拉一個思考型模型（預設用這顆）
ollama pull qwen3-4b-thinking-2507

# 3) 執行（任何有 Python 3.8+ 的環境都行，不必用 conda lora_project）
#    互動多輪：輸入題目開始，對話中 quit 離開、reset 換新題
python grounded_tutor.py

#    單題起手：直接看第一個引導問句
python grounded_tutor.py "Prove that lim_{x->2} x^2 = 4 using epsilon-delta."
```

> 用本專案的 conda 環境也可以：
> `conda run -n lora_project --live-stream python grounded_tutor.py`

## 設定

| 項目 | 方式 | 預設 |
| --- | --- | --- |
| 模型 tag | `ollama_model.txt`（本資料夾）或環境變數 `OLLAMA_MODEL` | `qwen3-4b-thinking-2507:latest` |
| Ollama 位址 | 環境變數 `OLLAMA_HOST` | `http://localhost:11434` |
| 顯示參考解(debug) | 環境變數 `SHOW_REF=1` | 隱藏 |

換模型：把任何思考型模型的 tag 寫進 `ollama_model.txt` 即可（例如更強的 `qwen3:8b` 之類，
會讓參考解與引導品質更好）。

## 檔案

| 檔案 | 說明 |
| --- | --- |
| `grounded_tutor.py` | 自包含主程式：Ollama 客戶端 + 參考解生成（含截斷續寫）+ grounded 引導 + CLI |
| `ollama_model.txt` | 要使用的 Ollama 模型 tag |
| `README.md` | 本說明 |

## 運作流程（grounded_tutor.py）

1. `generate_reference()`：用 `SYSTEM_PROOF` 讓思考型模型產出完整證明；若思考鏈吃光預算
   導致答案被截斷（`done_reason=="length"`），自動關閉思考、最多續寫 2 輪補完。
2. `build_grounded_system(參考解)`：組出引導層 system prompt = 蘇格拉底規則 + 隱藏參考解。
3. `tutor_turn()`：多輪引導，每輪只回一個引導問句（思考型模型預算 4096，留足思考空間）。

## 注意

- 第一次對某題回應前會先花數十秒～數分鐘產生參考解（思考型模型的證明較慢），之後同一題的
  後續引導就快了。
- 助教輸出為**英文**（與訓練/評估一致）。要中文化可改 `SYSTEM_SOCRATIC` 文字。
