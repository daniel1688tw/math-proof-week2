# 設計文件：自我驗證備課 + 同學模式 + 逐步教學（2026-07-12）

> 分支：`self-verified-teaching`（自 `hybrid-review-backstop` 分出）
> 目標：(1) 助教面對沒有手寫參考解的困難證明題時，先「自己證對」（自動生成＋驗證參考解）
> 才教學，驗證不過就誠實降級為「同學模式」，杜絕誤導；(2) 學生連續卡住三次時，
> 自動進入「逐步教學」，一小步一確認地把證明教完，最後仍由學生自己寫出完整證明。
> 純推論端改動，不重訓模型。

## 決策記錄（與使用者確認）

1. **驗證失敗行為**：降級為「同學模式」——放下助教權威、以同儕身分一起想、
   想法標明不確定；學生質疑時認真反省檢查自己、有錯就承認（使用者自定義方案）。
2. **逐步教學觸發**：`stuck_count` 依 0→1→2→3 升級；第三次連續卡住時自動進入。

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
  **每步的 schema**：
  `{step_id, explain, check, expected_answer, accepted_answers, common_errors}`。
  `expected_answer` 不拿來做字串比對，而是提供語意審閱後盾核對與答不出時揭示。
- **兩層步驟驗收**：先由 `validate_teach_steps()` 做確定性結構檢查（步數 3–6／
  explain＋check＋expected_answer 皆非空／check 只含一個問號（問兩件事就無法用單一
  答案鍵評分）／答案 ≤60 字／不得有「問題與答案都雷同」的兩步；再由獨立
  `TEACH_STEPS_VERIFIER_SYSTEM` 對照已驗證參考解，檢查定理前提、量詞、不等號方向、
  問答對齊、重複與語言。最多產生三次，任何一層未通過就不啟用這套步驟。
- **不再自動採用句級 fallback**：機械切分只能保證欄位完整，不能保證問題、答案鍵與講解
  在數學語意上對齊。`fallback_steps()` 僅保留作歷史資料相容／離線診斷工具，不在可靠
  walkthrough 的執行路徑；SEGMENTER 失敗時回到一般引導。
- `build_reference()` 另回傳 `teach_steps_lang`（步驟語言）與 `teach_steps_source`
  （`segmenter` / `unavailable`），供 driver 與 UI 使用。
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

觸發（自動）：一般引導階段的 `stuck_count` 連續達 3；一旦學生提出實質嘗試便歸零。

進入前的三層支援：Level 0 只問一個聚焦問題；Level 1 把問題拆得更小；Level 2
揭露已驗證教學步驟的定理／技巧／核心想法（不新增公式）並再問一個問題。第三次仍卡住才切換。

狀態機（目前規格：每題只作答一次）：
```
walkthrough 進入 → walk_idx=0、walk_lang=當下 session 語言（鎖定）
每輪：確定性輸出「第 i/n 步：{explain}\n\n確認問題：{check}」（不呼叫生成模型），
      並記下本輪實際呈現的步驟 walk_presented_step/idx/step_id
  下一輪 judge_walkthrough_answer(...)：
    使用 Review／Rectify 的同一思考型審閱後盾，依數學語意判定
    correct／incorrect／partial／not_answer；不做答案字串或子字串比對。
    correct → 直接前進
    其他 verdict → 揭示 expected_answer，然後前進
    後盾離線、逾時、格式無法解析或 uncertain → 不猜答案是否正確；揭示參考答案後前進
walk_idx 走完 → 接回既有 writeup_request（請學生自己寫完整證明）→ review 審閱
中途學生**明確**交草稿（請幫我審閱／整則以「證明：」開頭）→ 進 review
```

- **首次呈現完全不經生成模型**。內容本來就是預寫的，而讓模型「用自己的話包裝」實測換來：
  同一步逐字重講三輪（弱點 #17）、一次講掉好幾步、把確認問題換成別的問題（答案鍵
  就此無從比對）。改成模板後首次呈現的生成次數為 0（原本每輪最多 4 次重生成），
  學生每輪等待也從數十秒降到即時。
- **不再有重講輪或 retry 計數**。這是「學生只有一次作答機會」的直接結果，也刪除了
  舊的重講生成、相似度判定、推託文字正則與重試上限；這些機制已不在執行路徑上。
- **逐步回答審閱後盾**：`review_backstop.judge_walkthrough_answer()` 與草稿審閱的
  `find_gaps()` 使用同一個思考型模型與結構化輸出策略。它會接受等價公式、LaTeX 差異、
  同義詞和「比標準答案更完整但仍正確」的回答；含矛盾、方向錯誤或只答一部分則不通過。
  Driver 只信任明確的 `correct`，不設任何字串比對 fallback。
- **語言鎖定 `walk_lang`**：教學期間 `step()` 不再重判 session 語言。一則「中文＋長
  LaTeX」的正確回答就足以把 session 切成英文，接著同一個 `walk_idx` 指向另一套排序
  不同的英文步驟，正確答案被拿另一題的 `expected_answer` 評分。兩層防護缺一不可：
  語言判定先剝除 `$…$`／`$$…$$`／`\(…\)`／`\[…\]`／LaTeX 指令／裸算式
  （`_strip_language_neutral_math`），**且**評分對象是上一輪實際呈現的那一步。
- **後盾故障採 fail-open 教學流程**：若審閱服務不可用，不把學生困住，也不以字串猜測；
  顯示該步參考答案並直接前進。判定狀態記在 `walkthrough_review_status` 供除錯。
- `teach_steps` 來源：題目自帶且語言相符（備課時產生）→ 否則臨場呼叫 SEGMENTER，
  並通過確定性結構檢查與獨立 Math Judge → 再否則不啟用 walkthrough、回到一般引導。
  取用時過 `ensure_checkable_steps()` 補齊舊資料欄位，但不以補欄位取代數學驗證。
- 交草稿的判定在教學期間收窄：第 1 步的標準答案常常長成「要證明：對任意 a<b…」，
  走一般 `_DRAFT_RE`（含 `證明[:：]`）會被當成交稿而中斷教學，後盾若恰好回報無缺漏，
  助教會直接說「可以定稿」。`_DRAFT_RE` 另加反向閘：「要／需／欲／待／所」＋「證明：」不算交稿。

## 四、驗證計畫

| 層 | 內容 | 需求 |
|---|---|---|
| 單元 | walkthrough 狀態機（進入/單次作答/揭答前進/收尾）、語意後盾 stub、peer 切換、保底切分 | 無 GPU |
| 管線盲測 | ≥10 題已知解盲測：verified 率、verified 正確率（人工核對）| Ollama |
| 端對端 | 全程卡住學生走完 walkthrough→writeup→review；unverified 題同學模式含質疑反省 | GPU+Ollama |
| 回歸 | 既有三情境評估逐字不變（新階段僅新條件觸發）、單元測試全過 | GPU |

## 落選方案（記錄）

- 重訓 v7 加教學對話：不解決「自己證對」、會再稀釋抗洩漏（v6 的教訓）。
- 更重的驗證（更大模型/形式化）：6GB VRAM 本機不可行；多樣本＋獨立審閱是現實上限。
