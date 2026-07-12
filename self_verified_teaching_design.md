# 設計文件：自我驗證備課 + 同學模式 + 逐步教學（2026-07-12）

> 分支：`self-verified-teaching`（自 `hybrid-review-backstop` 分出）
> 目標：(1) 助教面對沒有手寫參考解的困難證明題時，先「自己證對」（自動生成＋驗證參考解）
> 才教學，驗證不過就誠實降級為「同學模式」，杜絕誤導；(2) 學生提示梯用盡仍完全不會時，
> 自動進入「逐步教學」，一小步一確認地把證明教完，最後仍由學生自己寫出完整證明。
> 純推論端改動，不重訓模型。

## 決策記錄（與使用者確認）

1. **驗證失敗行為**：降級為「同學模式」——放下助教權威、以同儕身分一起想、
   想法標明不確定；學生質疑時認真反省檢查自己、有錯就承認（使用者自定義方案）。
2. **逐步教學觸發**：hint ladder 用盡後學生再度連卡兩次 → 自動進入（推薦方案）。

## 一、自動參考解管線 `dataset/auto_reference.py`

備課階段（教學前離線執行；此時 GPU 空閒供思考型模型使用）：

```
題目 statement
  → PROVER（qwen3-4b-thinking，temp 0.7）生成 K=3 份候選證明
  → VERIFIER（同模型，temp 0.2，獨立審閱員 prompt）逐份判定 pass/fail + issues
  → 有 pass：取第一份 pass 的候選；若有小 issues 先 REPAIR 修補一輪 → 再驗證
  → 產出 {status: "verified", reference_proof, teach_steps} 或 {status: "unverified", best_attempt}
```

- `teach_steps`：由 SEGMENTER（同模型）把驗證過的參考解切成 3–6 個教學步驟，
  每步 `{explain, check}`（講解內容＋確認理解的小問題），供逐步教學使用。
  切分失敗時退回確定性段落切分＋通用確認問句。
- CLI：`python auto_reference.py --statement "..." [--id NEW1] [--out file.json]`；
  也可 `--problems xdomain_problems.json --id X4 --blind` 對已知解題目盲測（忽略現有解）。
- 所有 Ollama 呼叫沿用 review_backstop 的教訓：`num_predict=8192`（思考鏈空間）、
  JSON 解析用括號平衡＋反斜線加倍兩段式。

**驗收標準（安全關鍵）**：對 ≥10 題已有手寫解的題目盲測，回報 verified 率；
**verified 的自動解人工核對正確率須 ≥90%**——「錯誤卻通過驗證」是最危險情形，必須量化。

## 二、同學模式（`tutor_driver.py` peer persona）

觸發：題目標記 `grounding: "unverified"`（或無 reference_proof 且管線失敗）。

- system 換為 PEER_SYSTEM：「你是和學生一起解這題的同學，不是助教。可以提出自己的
  想法但要標明不確定（『我猜』『說不定』）；不下權威斷言；學生質疑你時，認真重新檢查
  自己的想法，發現錯就明白承認。」
- 質疑偵測 `_CHALLENGE_RE`（你錯了/不對吧/我覺得不是/好像不對…）→ 該輪注入反省指示。
- 防護調整：洩漏/防奉送/禁算式停用（無參考解、同儕本可分享想法）；
  單問句截斷與回問保底保留（對話仍要有來有往）。
- 誠實聲明：進入同學模式的第一輪必須告知學生「這題我沒有把握，我們一起想，
  我的想法你要幫忙檢查」。

## 三、逐步教學（driver 新階段 `walkthrough`）

觸發（自動）：`ladder_idx >= len(hint_ladder)` 且 stuck_count 再次達 2。

狀態機：
```
walkthrough 進入 → walk_idx=0
每輪：講解 teach_steps[walk_idx].explain（微調模型用自己的話包裝）＋ 問 check 小問題
  學生答得出（非 stuck）→ walk_idx += 1
  學生答不出（stuck）→ 換更簡單說法重講一次（每步最多重講 1 次）→ 前進
walk_idx 走完 → 接回既有 writeup_request（請學生自己寫完整證明）→ review 審閱
中途學生交草稿 → 直接進 review（草稿優先權不變）
```

- 教學步驟內容加入洩漏白名單（教學步允許寫式子）；spoonfeed/formula 防護在此階段停用。
- `teach_steps` 來源：題目自帶（備課時產生）→ 否則臨場呼叫 SEGMENTER（Ollama 在線）
  → 再否則確定性段落切分（保底，不依賴 Ollama）。

## 四、驗證計畫

| 層 | 內容 | 需求 |
|---|---|---|
| 單元 | walkthrough 狀態機（進入/重講/前進/收尾）、peer 切換、質疑偵測、保底切分 | 無 GPU |
| 管線盲測 | ≥10 題已知解盲測：verified 率、verified 正確率（人工核對）| Ollama |
| 端對端 | 全程卡住學生走完 walkthrough→writeup→review；unverified 題同學模式含質疑反省 | GPU+Ollama |
| 回歸 | 既有三情境評估逐字不變（新階段僅新條件觸發）、單元測試全過 | GPU |

## 落選方案（記錄）

- 重訓 v7 加教學對話：不解決「自己證對」、會再稀釋抗洩漏（v6 的教訓）。
- 更重的驗證（更大模型/形式化）：6GB VRAM 本機不可行；多樣本＋獨立審閱是現實上限。
