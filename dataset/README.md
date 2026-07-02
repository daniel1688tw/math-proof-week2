# 高等數學蘇格拉底引導資料集

依 [`../dataset_plan.md`](../dataset_plan.md) 建置的 **域內、grounded、繁體中文** 蘇格拉底式對話訓練集，
用於 QLoRA 微調 Qwen3-4B 成高等數學證明引導助教。**全部內容由 Claude 手寫**（見 memory: dataset-content-authored-by-claude），
腳本只負責組裝，不生成任何數學內容。

## 產出檔案

| 檔案 | 內容 |
| --- | --- |
| `problems.json` | 50 道題目 + 手寫 LaTeX 參考解（A 極限 / B 連續 / C 微分 / D 積分 / E 級數，各 10） |
| `dialogues_core.jsonl` | 150 條核心對話（3 Persona × 50 題） |
| `dialogues_augmented.jsonl` | 200 條擴充對話（50 犯錯變體 + 150 關鍵步驟短對話） |
| `train.jsonl` / `val.jsonl` | 合併後 9:1 切分（315 / 35），**messages 格式，與 `train_qlora.py` 相容** |

## 資料統計（`test_dataset.py`）

- 對話總數 **350**，assistant 訓練信號 **907**
- persona：confused 150 / error 100 / bright 100
- kind：core 150 / augmented 50 / short 150
- 主題分佈：五大主題各 70 條對話（完全平衡）

## Grounded SFT 格式

每筆 `messages`：
1. `system`：引導規則 + `<REFERENCE_PROOF>…</REFERENCE_PROOF>`（該題參考解，學生看不到）
2. `user`：`題目：<LaTeX 題目>` + 該 Persona 的初始狀態
3. `assistant` / `user` 交替：五階段蘇格拉底引導，末回合為 assistant

## 重建與驗證

```powershell
$env:PYTHONNOUSERSITE = "1"
conda run -n lora_project --live-stream python dataset\build.py          # src/ → 各 jsonl
conda run -n lora_project --live-stream python dataset\validate.py       # 格式/字數/一問一等/不洩漏
conda run -n lora_project --live-stream python dataset\test_dataset.py   # 分佈/引用/grounding 完整性
```

## 品質保證（validate.py 全部通過）

- 結構：system 首、user/assistant 嚴格交替、末回合 assistant、system 含參考解
- 字數：每個 assistant 回合中文 ≤ 100（實測最長 55）
- 一問一等：每個 assistant 回合至多一個問號
- 不洩漏：無「答案是 / 故得證 / 證畢 / QED」等洩漏字樣
- 對話長度：4–20 回合

## 來源結構（手寫內容）

```
src/
├── problems_A.py … problems_E.py          # 50 題 + 參考解
├── dialogues_A.py … dialogues_E.py        # 150 核心對話
└── dialogues_aug_A.py … dialogues_aug_E.py # 200 擴充對話
```

修改內容只需編輯 `src/` 下對應檔案，再重跑 `build.py`。
