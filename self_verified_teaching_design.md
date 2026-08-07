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

- `teach_steps`：由 SEGMENTER（同模型）把驗證過的參考解切成 3–6 個教學步驟，供逐步教學使用。
  **每步的 schema（2026-08-07 擴充成可評分）**：
  `{step_id, explain, check, expected_answer, accepted_answers, common_errors}`。
  沒有 `expected_answer`，driver 只能「有回答就當答對」——實測學生答錯照樣被推到下一步。
- **確定性驗收 `validate_teach_steps()`**（與 LADDER 同型，五道閘）：步數 3–6／
  explain＋check＋expected_answer 皆非空／check 只含一個問號（問兩件事就無法用單一
  答案鍵評分）／答案 ≤60 字／不得有「問題與答案都雷同」的兩步。任一不過即整份丟棄。
  刻意**不**再叫一個 LLM 當 teach-step verifier：多一次思考型呼叫要多等最長 300 秒，
  而它擋不掉的錯（答案鍵與問題語意不合）正是它最容易誤判的地方；真正的安全網是
  driver 端的重試上限（見第三節）。
- **句級保底 `fallback_steps()`**（驗收不過／Ollama 離線時走）：舊版只按空行切段，
  參考解常常只有一段 ⇒ 第一步幾乎是整份證明、確認問題是無法驗證的「你能複述嗎」。
  改為：句級切分（`_proof_units`）→ 合併／再切到 3–6 步（`_balanced_units`）→
  每步擷取最後一個關係式或結論子句當答案鍵（`_fallback_expected`）。
  **它是語法式保底不是第二個 LLM**：保證步數、欄位與可評分性，保證不了數學語意對齊。
- `build_reference()` 另回傳 `teach_steps_lang`（步驟語言）與 `teach_steps_source`
  （`segmenter` / `fallback`），供 driver 與 UI 使用。
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

狀態機（2026-08-07 改為「答對才前進」）：
```
walkthrough 進入 → walk_idx=0、walk_lang=當下 session 語言（鎖定）
每輪：確定性輸出「第 i/n 步：{explain}\n\n確認問題：{check}」（不呼叫生成模型），
      並記下本輪實際呈現的步驟 walk_presented_step/idx/step_id
  下一輪 grade_walkthrough_answer(學生訊息, walk_presented_step)：
    比對順序＝先答案鍵（expected_answer／accepted_answers）、再錯答清單（common_errors）、
    最後才看卡住。錯答清單**必須排在答案鍵之後**：它是無長度下限的子字串比對，排在前面時
    只要生成的錯答是正確答案的子字串（如 expected="非負" ＋ common_errors=["負"]），
    答對就永遠先命中 incorrect（2026-08-07 實測）。
    correct   → walk_idx += 1、walk_retry=0
    incorrect → 留在同一步，walk_retry += 1，下一輪帶「還不是這一步要的答案」重講
    stuck     → 留在同一步，walk_retry += 1，下一輪帶「這一步我再講一次」重講
  walk_retry > 2（安全閥）→ 揭示 expected_answer 後強制前進
walk_idx 走完 → 接回既有 writeup_request（請學生自己寫完整證明）→ review 審閱
中途學生**明確**交草稿（請幫我審閱／整則以「證明：」開頭）→ 進 review
```

- **首次呈現完全不經生成模型**。內容本來就是預寫的，而讓模型「用自己的話包裝」實測換來：
  同一步逐字重講三輪（弱點 #17）、一次講掉好幾步、把確認問題換成別的問題（答案鍵
  就此無從比對）。改成模板後首次呈現的生成次數為 0（原本每輪最多 4 次重生成），
  學生每輪等待也從數十秒降到即時。
- **重講輪是唯一還會叫模型的地方**（2026-08-07 補）。純模板化的第一版把「重講」做成
  把同一段原封不動再貼一次，M1 中英兩場守門的 `guidance` 都被評 1 分，學生本人在對話裡
  寫「Repeating it doesn't make it any clearer」。現在重講輪帶 `WALK_RETRY_INSTRUCTION`
  請模型**換完全不同的說法**（確認問題仍由程式附上，答案鍵才比得到），並在三種情況下
  退回模板＋揭示該步答案：模型不在線、講出來的東西與原步驟／上一則回覆相似度 ≥0.9、
  或推託「你自己去查」（`_REFUSE_TEACH_RE`）。
  > 相似度那道閘要比對 `step["explain"]` **本身**，不能只比上一則完整回覆——後者含
  > 「第 i/n 步：」前綴與確認問題，會把相似度稀釋到門檻以下（實測 96 字步驟逐字吐回
  > 只算 0.845 < 0.9）。剝除模板的工具是 `_strip_walk_template()`。
- **語言鎖定 `walk_lang`**：教學期間 `step()` 不再重判 session 語言。一則「中文＋長
  LaTeX」的正確回答就足以把 session 切成英文，接著同一個 `walk_idx` 指向另一套排序
  不同的英文步驟，正確答案被拿另一題的 `expected_answer` 評分。兩層防護缺一不可：
  語言判定先剝除 `$…$`／`$$…$$`／`\(…\)`／`\[…\]`／LaTeX 指令／裸算式
  （`_strip_language_neutral_math`），**且**評分對象是上一輪實際呈現的那一步。
- **重試上限是必要的**：答案鍵由模型或語法保底自動生成、沒有人工審過，寫壞時
  「只有答對才前進」會把學生永遠困在同一步。上限之後揭示答案並帶他往下走。
- `teach_steps` 來源：題目自帶（備課時產生）→ 否則臨場呼叫 SEGMENTER（Ollama 在線，
  仍過 `validate_teach_steps`）→ 再否則句級保底。取用時一律過 `ensure_checkable_steps()`
  補齊 `step_id`／`expected_answer`（舊資料相容，冪等，不改寫既有內容）。
- 交草稿的判定在教學期間收窄：第 1 步的標準答案常常長成「要證明：對任意 a<b…」，
  走一般 `_DRAFT_RE`（含 `證明[:：]`）會被當成交稿而中斷教學，後盾若恰好回報無缺漏，
  助教會直接說「可以定稿」。`_DRAFT_RE` 另加反向閘：「要／需／欲／待／所」＋「證明：」不算交稿。

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
