# dataset/ — 手寫 grounded 蘇格拉底資料集 + 驅動程式 + 評估

本目錄是整個專案的核心：**內容全部由人工撰寫並驗證數學正確性**（非模型生成），
腳本只負責組裝、驗證、訓練與評估。

## 產出檔案

| 檔案 | 內容 |
| --- | --- |
| `problems.json` / `problems_en.json` | 50 道題目 + 手寫 LaTeX 參考解（極限/連續/微分/積分/級數 各 10），中英平行 |
| `train.jsonl` / `val.jsonl` | 中英平行對話 9:1 切分（747/83 = 830 例），messages 格式，與 `train_qlora.py` 相容 |
| `hint_ladders.json` / `_en.json` | **17 題**的分級提示內容（driver 等級 2 注入用）|
| `qlora_adapter_v9/` | 部署用 LoRA adapter（權重不進 git，見根目錄 README 訓練步驟）|

> ⚠️ 提示梯只涵蓋 17 題，不是全部 50 題。其餘內建題與**所有使用者自帶題目**改由
> `auto_reference.py` 的 LADDER 階段自動生成；生成或驗收失敗則退回通用保底句。

> ⚠️ 現行部署的 `qlora_adapter_v9` 是用 **814 例**（733/81，不含 `dialogues_journey.py`）訓練的。
> 目前 `build.py` 產出的 830 例含 journey 對話，是 v10／v11 的訓練資料——這兩輪重訓
> **皆經守門判退**，資料保留供下次迭代參考，詳見根目錄 `CLAUDE.md`。

## Grounded SFT 格式

每筆 `messages`：`system`（引導規則 + `<REFERENCE_PROOF>` 該題參考解，學生看不到）→
`user`（`題目：<LaTeX>` + 學生初始狀態）→ 多輪交替，末回合 assistant。

## 重建與驗證

```powershell
conda run -n lora_project --live-stream python dataset\build.py          # src/ + src_en/ → jsonl
conda run -n lora_project --live-stream python dataset\validate.py       # 格式/字數/一問一等/不洩漏
conda run -n lora_project --live-stream python dataset\test_dataset.py   # 分佈/引用/grounding
```

## 品質標準（validate.py 全數強制）

結構交替、system 含參考解、assistant 中文 ≤100 字、至多一個問號（一問一等）、
無「答案是/故得證/證畢」等洩漏字樣、對話 4–20 回合。

## 驅動程式與備課

- `tutor_driver.py`：**部署核心**。stuck counter→提示等級、階段偵測
  （review／rectify／refuse_leak／writeup_request／closed／walkthrough）、
  逐步教學的答案評分與語言鎖定，以及全部內容防護（洩漏 n-gram、on-track 防奉送、
  等級 2 禁算式、稱讚校準；每次重生成後重跑）＋單問句截斷、重複偵測、回問保底。
- `auto_reference.py`：**自動備課管線**（新題目先自己證對才教）。五階段
  PROVER×3 → VERIFIER → REPAIR → SEGMENTER → **LADDER**，產出 `reference_proof`
  ＋可評分的 `teach_steps` ＋ `hint_ladder`；驗證不過標 unverified、driver 走同學模式。
- `review_backstop.py`：審閱後盾（選配）。review／rectify 輪讓 Ollama 思考型模型對照
  參考解找碴、缺漏清單注入 system；Ollama 不在線自動降級，`REVIEW_BACKSTOP=0` 關閉。
- `interactive_turn.py`：逐輪互動 CLI（`dump_state()` / `load_state()` 整包狀態快照）。
- `app.py`：Gradio 本機單人 Demo，使用者自帶題目。

## 測試與評估

| 檔案 | 需要 | 內容 |
|---|---|---|
| `test_driver_unit.py` | — | **313 條斷言**，driver 全部確定性邏輯 + LADDER 生成端 |
| `test_phase_routing.py` | — | 回放 `regression_scores/*_dialogues.json` 的 299 場真實對話，驗 5 條階段路由不變式 |
| `test_dataset.py` / `validate.py` | — | 資料集分佈與品質標準 |
| `test_app.py` | — | 介面純邏輯 |
| `test_driver_integration.py` / `test_driver_phase.py` | GPU | 分級提示／階段管理 |
| `test_backstop.py` / `eval_backstop_e2e.py` | Ollama（+GPU） | 後盾找碴準確度／端對端有無對照 |
| `test_auto_reference.py` / `eval_svt_e2e.py` | Ollama（+GPU） | 備課盲測／逐步教學＋同學模式端對端 |
| `eval_final_driver.py` / `eval_heldout_v3.py` / `eval_hard.py` / `eval_xdomain.py` | GPU | 部署形態／裸模型／難題／跨領域 |
| `regression_suite.py` | GPU + agy | **推送前守門**（見根目錄 README）|
| `render_transcripts.py` | — | 把守門對話轉成可讀 markdown 供人工檢視 |

現行報告在 `eval_out_final/`（最終判定）、`eval_out_v6/`、`eval_out_hard/`、
`eval_out_driver/`、`eval_out_xdomain/`；歷次守門計分卡與對話存檔在 `regression_scores/`
（**不可刪**——`test_phase_routing.py` 以它為回放語料）。

修改內容只需編輯 `src/`／`src_en/` 下對應檔案，再重跑 `build.py`。
被淘汰的歷史版本（v2–v5）見 git tag `experiments-v2-v6`。
