# dataset/ — 手寫 grounded 蘇格拉底資料集 + 驅動程式 + 評估

本目錄是整個專案的核心：**內容全部由人工撰寫並驗證數學正確性**（非模型生成），
腳本只負責組裝、驗證、訓練與評估。

## 產出檔案

| 檔案 | 內容 |
| --- | --- |
| `problems.json` | 50 道題目 + 手寫 LaTeX 參考解（極限/連續/微分/積分/級數 各 10）|
| `train.jsonl` / `val.jsonl` | 400 條對話 9:1 切分（360/40），messages 格式，與 `train_qlora.py` 相容 |
| `hint_ladders.json` | 每題的分級提示內容（driver 等級 2 注入用，17 題含進階題）|
| `qlora_adapter_v6/` | 部署用 LoRA adapter（權重不進 git，見根目錄 README 訓練步驟）|

## 資料統計（`test_dataset.py`）

- 對話 **400** 條，assistant 訓練信號 **1076**，五大主題完全平衡
- 對話類型：核心 150（confused/error/bright 三人格）＋ 犯錯變體與短對話 ＋
  抗洩漏/抗附和 20 ＋ 分級提示 12 ＋ 節奏錯位 10 ＋ 寫證明審閱 8

## Grounded SFT 格式

每筆 `messages`：`system`（引導規則 + `<REFERENCE_PROOF>` 該題參考解，學生看不到）→
`user`（`題目：<LaTeX>` + 學生初始狀態）→ 多輪交替，末回合 assistant。

## 重建與驗證

```powershell
conda run -n lora_project --live-stream python dataset\build.py          # src/ → jsonl
conda run -n lora_project --live-stream python dataset\validate.py       # 格式/字數/一問一等/不洩漏
conda run -n lora_project --live-stream python dataset\test_dataset.py   # 分佈/引用/grounding
```

## 品質標準（validate.py 全數強制）

結構交替、system 含參考解、assistant 中文 ≤100 字、至多一個問號（一問一等）、
無「答案是/故得證/證畢」等洩漏字樣、對話 4–20 回合。

## 驅動程式與測試

- `tutor_driver.py`：部署核心。stuck counter→提示等級、階段偵測（審閱/拒絕/糾錯/寫證明）、
  單問句截斷、洩漏 n-gram 防護、on-track 防奉送、等級 2 禁算式、回問保底。
- `review_backstop.py`：審閱後盾（選配）。review/rectify 輪讓 Ollama 思考型模型對照
  參考解找碴、缺漏清單注入 system；`test_backstop.py`（準確度）與 `eval_backstop_e2e.py`
  （端對端對照）可重跑驗證。
- `auto_reference.py`：自動備課管線（新題目先自己證對才教）。生成→獨立驗證→修補→
  教學步驟切分；驗證不過標 unverified、driver 走同學模式。盲測 `test_auto_reference.py`
  （9/10 verified、正確率 100%）、端對端 `eval_svt_e2e.py`（逐步教學＋同學模式）。
- `interactive_turn.py`：逐輪互動 CLI（session 狀態存檔）。
- `test_driver_unit.py`（無 GPU）/ `test_driver_integration.py` / `test_driver_phase.py`：
  三套可重跑測試。
- `eval_final_driver.py` / `eval_heldout_v3.py` / `eval_hard.py` / `eval_final_ollama.py`：
  評估腳本；現行報告在 `eval_out_final/`（最終判定）、`eval_out_v6/`、`eval_out_hard/`。

修改內容只需編輯 `src/` 下對應檔案，再重跑 `build.py`。歷史版本（v2–v5）見 git tag
`experiments-v2-v6`。
