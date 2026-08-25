# Phase 精準切換解決方案

適用資料夾：`D:\math-proof-week2-main (main的前一版) - 複製 - 進行修改10`

## 1. 結論

建議採用「**狀態機硬規則 + Thinking 模型只判斷模糊意圖 + 轉換白名單**」的混合方案。

不建議讓 Thinking 模型直接決定所有 phase，因為 `walkthrough`、完整證明審閱、局部訂正、
等待乾淨證明與 `closed` 都含有不可隨意跳出的狀態。若全部交給模型，單次分類波動就可能中斷
逐步教學、把局部答案當全文，或在證明尚未通過時提前進入 `closed`。

Thinking 模型應只負責目前正則難以精準區分的語意，例如：

- 學生貼的是完整證明，還是只回答一個小步驟？
- 「我懂了」指理解目前一步，還是已掌握整個證明？
- 學生是在要求提示，還是在要求直接給完整答案？
- 一段包含推導的訊息是嘗試、完整交稿，還是對 Tutor 的質疑？

此方案是執行期路由調整，**不需要重新訓練模型**。

## 2. 現況問題

目前 `_detect_phase()` 主要依靠正則、文字長度及數個 state flag 判斷：

- `_DRAFT_RE`：判斷是否交完整證明。
- `_DEMAND_RE`：判斷是否要求直接給答案。
- `_ATTEMPT_RE`：判斷是否提交自己的嘗試。
- `_UNDERSTOOD_RE`：判斷是否已理解並應要求交稿。
- `_CLAIM_DONE_RE`：判斷是否宣告證完。
- `walk_active`、`writeup_asked`、`done_closed`、`review_active`、
  `awaiting_clean_proof`：限制特殊流程。

主要風險如下：

| 風險 | 例子 | 可能誤判 |
|---|---|---|
| 關鍵詞缺乏上下文 | 「要證明：對任意……」 | 被當成完整交稿，錯進 `review` |
| 文字長度代替語意 | 很長的局部推導 | 被當成完整證明 |
| 同一句有多個意圖 | 「我不會，直接告訴我可以嗎？」 | `stuck` 與 `refuse_leak` 衝突 |
| 理解範圍不清 | 「我懂了」 | 單步理解被當成整題理解 |
| phase 在多處被改寫 | review queue、walkthrough、一般路由各自更新 | 同一輪出現不一致狀態 |
| 完成狀態判斷過早 | 學生說「故得證」但證明仍有錯 | 提前進入 `closed` |

## 3. 建議架構

```text
學生訊息
  │
  ├─ ① 不可猜的狀態鎖（review / walkthrough / closed / peer）
  │      └─ 能確定時直接路由
  │
  ├─ ② 高精度明確規則
  │      └─ 明確交稿、明確要求答案等才直接路由
  │
  ├─ ③ 仍模糊 → Thinking 模型分類「學生意圖」
  │
  └─ ④ 轉換白名單驗證 → 產生 final phase
```

Thinking 模型只分類 `intent`，不要讓它任意發明 phase。程式再把 intent 映射到既有 phase，
可避免模型輸出不存在的狀態或跳過必要流程。

## 4. 第一層：狀態鎖

以下情況不應交給模型自由判斷：

| 目前狀態 | 優先處理 | 允許離開的條件 |
|---|---|---|
| `review_active=True` | 將訊息視為目前問題的局部訂正 | 只有明確且具完整結構的全文重交，才重新做完整審閱 |
| `awaiting_clean_proof=True` | 維持交稿／審閱流程 | 收到乾淨完整證明後進 `review` |
| `walk_active=True` | 預設維持 `walkthrough` | 只有明確完整交稿才進 `review` |
| `done_closed=True` | 預設 `closed` | 學生明確指出證明錯誤或漏審，才觸發重新審閱 |
| peer mode | 只在普通同儕與 `peer_reflect` 間切換 | 學生明確質疑先前想法 |

這層可直接沿用目前 review workflow 與 walkthrough 的優先處理，只需統一由一個路由函式回傳，
不要再由多處各自改寫 `state["phase"]`。

## 5. 第二層：保留少量高精度規則

正則只保留「幾乎不可能誤解」的情況：

| 明確訊號 | intent | phase |
|---|---|---|
| 「請幫我審閱以下完整證明」「以下是完整證明：……」且具有證明結構 | `full_proof_submission` | `review` |
| 「直接給我答案／完整證明」 | `demand_full_answer` | `refuse_leak` |
| Tutor 已要求交完整證明，學生提交具完整結構的長論證 | `full_proof_submission` | `review` |
| 已完成且通過審閱，學生只道謝或反思 | `post_completion` | `closed` |
| 明確要求重查最近證明或指出漏審 | `missed_review` | 重新審閱最近草稿 |

不要再用「只要出現 `證明：`」「只要超過固定字數」作為單一充分條件。文字長度只能當輔助特徵，
不能直接決定 phase。

## 6. 第三層：Thinking 模型分類模糊意圖

使用現有的 `qwen3-4b-thinking-2507`，只在前兩層無法確定時呼叫。建議輸出：

```json
{
  "intent": "show_attempt",
  "scope": "single_step",
  "confidence": 0.86,
  "evidence": "我試著先對 f' 使用中值定理，這樣對嗎"
}
```

固定 enum：

```text
full_proof_submission
local_revision
show_attempt
demand_full_answer
request_hint
understood_whole_proof
understood_single_step
stuck
challenge_or_missed_review
post_completion
ordinary
uncertain
```

`scope` 只允許：

```text
whole_proof | single_step | conversation | unknown
```

### Thinking prompt 必須強調

1. 只判斷學生意圖，不解題、不評證明正確性。
2. 「要證明……」通常只是重述目標，不等於交稿。
3. 完整證明須包含多個相連推理、依據與結論；只有一個等式或一步理由不是完整證明。
4. 「我懂了」若未明說整體且仍在 walkthrough，預設是理解單步。
5. 要提示不等於要求直接答案。
6. 學生說「得證」不代表證明已通過，只能判為可能交稿，不能判 `closed`。
7. `evidence` 必須引用學生訊息中的短片段；不得自行杜撰。
8. 只輸出 JSON Schema，不得輸出解釋文字。

## 7. 第四層：白名單映射

Thinking 只提供意圖，最後 phase 由程式決定：

| intent | 必要 state 條件 | final phase／動作 |
|---|---|---|
| `full_proof_submission` | 通過完整結構檢查 | `review` |
| `local_revision` | `review_active=True` | 留在 review workflow，處理目前一項 |
| `show_attempt` | 非 walkthrough/review lock | `rectify` |
| `demand_full_answer` | 非 review lock | `refuse_leak` |
| `understood_whole_proof` | 尚未要求交稿 | `writeup_request` |
| `understood_single_step` | `walk_active=True` | `walkthrough` |
| `challenge_or_missed_review` | 有最近完整草稿 | 重新審閱最近草稿 |
| `post_completion` | `done_closed=True` | `closed` |
| `stuck` / `request_hint` / `ordinary` | 一般教學中 | `None`，由 stuck_count 決定提示深度 |
| `uncertain` | 任意 | 使用安全 fallback，不切換關鍵 phase |

### 關鍵不變量

- Thinking 不得直接產生 `closed`；只有 `done_closed=True` 才能進入。
- 未經完整證明審閱，不得把 `done_closed` 設為 True。
- `review_active=True` 時，普通訊息不得跳到 `rectify`、`refuse_leak` 或 walkthrough。
- `walk_active=True` 時，除完整交稿外不得跳離 walkthrough。
- `writeup_request` 只代表要求學生交完整證明，不代表證明已完成。

## 8. 信心門檻與失敗處理

建議規則：

- `confidence >= 0.75`，且 `evidence` 確實出現在學生訊息中：採用分類結果。
- `confidence < 0.75`、JSON 無法解析、逾時或 evidence 不存在：視為 `uncertain`。
- `uncertain` 時不得中斷程式，也不得猜測高風險 phase：
  - walkthrough lock：維持 `walkthrough`。
  - review lock：維持 review workflow。
  - `done_closed=True` 且無明確數學質疑：維持 `closed`。
  - 其他情況：phase 設為 `None`，繼續一般引導。

不建議無限重試 Thinking。單次重試一次即可；仍失敗就使用上述安全 fallback，避免學生等待過久。

## 9. 建議的程式介面

新增一個小型模組 `dataset/phase_router.py`，避免把更多分類邏輯塞進 `tutor_driver.py`：

```python
def route_phase(student_text: str, state: dict, context: dict) -> PhaseDecision:
    """先套狀態鎖與高精度規則；仍模糊時才呼叫 Thinking。"""


@dataclass
class PhaseDecision:
    phase: str | None
    intent: str
    source: str       # state_lock | deterministic | thinking | fallback
    confidence: float
    evidence: str
```

`TutorDriver._detect_phase()` 最後只做一件事：

```python
decision = route_phase(student_text, self.state, context)
self.state["phase"] = decision.phase
self.state["phase_decision"] = asdict(decision)
```

review queue 與 walkthrough transition 仍保留原本專用處理，但都要在呼叫一般 phase router 前完成。

## 10. 測試方式

### 單句分類測試

至少涵蓋：

- 「要證明：對任意 a<b……」→ 不是 `review`。
- 「以下是完整證明：……」且有完整推理鏈 → `review`。
- 「我懂這一步了，但後面不會」→ 不是 `writeup_request`。
- 「整個思路我懂了，可以寫證明」→ `writeup_request`。
- 「可以再提示一點嗎」→ 不是 `refuse_leak`。
- 「直接把完整證明給我」→ `refuse_leak`。
- 「我試著用中值定理，這樣對嗎」→ `rectify`。
- 已完成後「你是不是漏看一個符號錯誤」→ 重新審閱，不是普通 `closed`。

### 對話序列測試

phase 精準度不能只測單句，至少測以下完整序列：

1. 一般引導 → 卡住三次 → walkthrough → 回答單步 → 完整交稿 → review。
2. review 找錯 → 局部訂正數輪 → 等待乾淨證明 → 完整重交 → closed。
3. Tutor 要求交稿 → 學生提交未標「完整證明」但具完整結構的全文 → review。
4. closed → 學生一般反思 → closed；closed → 明確指出漏審 → 重新審閱。
5. walkthrough 中回答「要證明：……」→ 仍留在 walkthrough。

### 建議指標

- 整體 final phase accuracy ≥ 95%。
- `review`、`closed`、`writeup_request` 的 false positive 應特別接近 0。
- 所有狀態不變量測試必須 100% 通過。
- Thinking 不可用時，整個測試流程仍不得拋出例外或中斷。

## 11. 導入順序

1. 先建立 `phase_router.py`、JSON Schema 與純函式測試，不接管正式 phase。
2. 開啟 shadow mode：同時記錄現行判定與新判定，但仍使用現行結果。
3. 收集誤判案例，建立固定 regression cases。
4. 只讓新 router 接管「原規則無法確定」的案例。
5. 指標穩定後，再逐步縮減低精度正則；不要一次全部刪除。

建議記錄下列診斷欄位，方便定位誤切換原因：

```text
previous_phase
state_locks
deterministic_match
thinking_intent
thinking_confidence
final_phase
decision_source
```

## 12. 預計需要修改的檔案（實作時）

本文件目前只提出方案，尚未修改程式。實作時建議最小範圍為：

- 新增 `math-proof-week2-main/dataset/phase_router.py`
- 局部調整 `math-proof-week2-main/dataset/tutor_driver.py`
- 擴充 `math-proof-week2-main/dataset/test_phase_routing.py`
- 補充少量 `math-proof-week2-main/dataset/test_driver_unit.py` 序列測試
- 若 `test.ipynb` 會直接複製指定檔案到 Colab，再把 `phase_router.py` 加入其檔案檢查／上傳清單

不需修改訓練資料，也不需重新 train。核心目標是讓 Thinking 補足語意判斷，而不是取代既有狀態機。

---

# 學生卡住狀態精準判斷方案

## 13. 結論

卡住判斷也建議採「**明確規則 + Thinking 判斷模糊案例 + 保守更新 stuck_count**」，並與前述
phase router 共用同一次 Thinking 呼叫，不必再增加第二個模型服務。

Thinking 不應只看學生訊息；至少要同時看到：

- Tutor 上一個實際問題。
- 學生最新回答。
- 前一輪學生回答與目前 `stuck_count`。
- 目前 phase。
- 本地計算出的 `explicit_stuck`、`strong_stuck`、`has_new_math` 等特徵。

判斷重點不是「答案正不正確」，而是學生是否仍能提出與當前問題相關的下一步。學生答錯但有
實質嘗試，應交給 `rectify`，不應算卡住；學生寫了一個無關或重複算式，也不應只因出現數學
符號就被判為有進展。

## 14. 現況限制

目前實作是：

```python
is_stuck(student_text) and not has_new_math(student_text, prior_text)
```

其中 `is_stuck()` 依關鍵詞與長度判定，`has_new_math()` 發現新算式就否決卡住。這個設計簡單，
但有以下邊界：

| 學生回答 | 真實狀況 | 現有機制的風險 |
|---|---|---|
|「我不確定，但我想先令 (g(x)=f(x)-x)」| 有實質嘗試 | 可能因「不確定」誤判卡住 |
|「我試了中值定理，但後面完全不知道怎麼接」| 已在目前位置卡住 | 新算式可能一票否決卡住 |
| 很長地描述自己仍完全不懂 | 確實卡住 | 可能受長度上限漏判 |
| 寫出一個與當前問題無關的新公式 | 沒有有效進展 | `has_new_math=True` 可能誤判有進展 |
|「這裡的 (c) 是怎麼來的？」| 主動釐清 | 不應算卡住，但可能含困惑詞 |
|「由絕對值定義」| 精簡但有效回答 | 短文字不應因內容少被判卡住 |

因此 `has_new_math` 應保留為特徵，但不再擁有一票否決權。

## 15. 建議的 learning_state

Thinking 不直接輸出布林值，改輸出下列有限狀態：

```text
stuck
partial_progress
progressing
active_clarification
not_applicable
uncertain
```

定義：

| learning_state | 判準 | stuck_count 更新 |
|---|---|---|
| `stuck` | 明確無法回答目前問題，且沒有可延續的相關步驟 | `+1` |
| `partial_progress` | 有相關但不完整的想法、式子或定理 | 歸零 |
| `progressing` | 已實際回答或提出可延續的下一步，不要求一定正確 | 歸零 |
| `active_clarification` | 主動詢問某個具體概念、符號或前提 | 歸零 |
| `not_applicable` | review、closed、walkthrough 評分等不應累計一般卡住次數的階段 | 歸零 |
| `uncertain` | 模型或規則無法可靠判斷 | 維持原值，不加也不歸零 |

`partial_progress` 歸零是因為目前的 `stuck_count` 定義是「連續卡住次數」；學生只要重新開始做出
實質嘗試，連續卡住便已中斷。數學正確性另由 Tutor／Thinking 審閱處理。

## 16. 三層判斷流程

### 第一層：phase gate

只有一般引導階段才更新一般 `stuck_count`：

| phase／狀態 | 處理方式 |
|---|---|
| `review_active`、`awaiting_clean_proof`、`review` | 不累計；由審閱流程判斷局部訂正 |
| `walk_active` / `walkthrough` | 不累計一般卡住次數；每一步已有一次作答與揭答機制 |
| `writeup_request` | 不因「我不會寫完整證明」立即切 walkthrough，先維持交稿引導 |
| `closed` | 不累計 |
| peer mode | 不使用 Tutor 的 stuck 升級機制 |
| `None` 或一般引導 | 才執行卡住分類 |

這可避免學生在 review、逐步教學或收尾時說「不知道」，卻污染一般教學的連續卡住計數。

### 第二層：高精度確定性判斷

以下案例不必呼叫 Thinking：

- 明確強卡住，且沒有任何具體嘗試，例如「我真的完全不知道」「毫無頭緒」→ `stuck`。
- 學生提供與上一問題直接相關的等式、定理應用或文字下一步，且沒有表示已無法繼續
  → `partial_progress` 或 `progressing`。
- 學生提出具體釐清問題，例如「為什麼這裡可以用羅爾定理？」→ `active_clarification`。
- 特殊 phase 被第一層攔截 → `not_applicable`。

只有同時含「困惑訊號」與「某種嘗試」，或回覆過短而無法確定是否有進展時，才交給 Thinking。

### 第三層：Thinking 判斷模糊案例

可把前一份 phase classifier 的 JSON Schema 擴充為：

```json
{
  "intent": "show_attempt",
  "scope": "single_step",
  "learning_state": "partial_progress",
  "phase_confidence": 0.84,
  "stuck_confidence": 0.91,
  "evidence": "我試著用中值定理，但不知道後面怎麼整理"
}
```

如此 phase 與 stuck 只需一次 `qwen3-4b-thinking-2507` 呼叫，也能避免兩個模型判定互相矛盾。

## 17. Thinking 模型的卡住判斷規則

建議 system prompt 明確寫入：

1. 判斷學生是否能對 Tutor「上一個實際問題」提出相關下一步，而不是只看自信語氣。
2. 答案錯誤但有相關推理，判 `partial_progress`，不要判 `stuck`。
3. 說「不確定」不等於卡住；若後面有具體想法，視為進展。
4. 即使出現新公式，若公式只是抄題目、重複 Tutor 已給內容或與問題無關，仍可判 `stuck`。
5. 學生明說「做到這裡後完全不知道下一步」，即使前面描述過嘗試，也可判 `stuck`。
6. 詢問明確概念、符號、定理前提或某步理由，是 `active_clarification`，不是卡住。
7. 只回答「是」「不是」「正」「負」時，須依上一個問題判斷；若上一題正好只問此內容，
   這就是有效進展。
8. 不評完整證明正確性、不提供解法，只分類學習狀態。
9. `evidence` 必須引用學生原文；不得杜撰。
10. 資訊不足時輸出 `uncertain`，不可硬猜。

## 18. 本地特徵如何使用

保留既有函式，但改變角色：

| 現有特徵 | 新角色 |
|---|---|
| `_STUCK_RE` / `_STUCK_EN_RE` | `explicit_stuck` 特徵，不直接等於最終結果 |
| `_STRONG_STUCK_RE` | 高權重卡住訊號；仍要檢查是否有明確可延續步驟 |
| `has_new_math()` | `new_math` 特徵，不再一票否決 |
| 訊息長度 | 只作為資訊量特徵，不作為硬門檻 |
| 上一輪 Tutor 問題 | 判斷回答是否相關的必要輸入 |
| 最近學生訊息 | 判斷是否只是重複、是否連續卡住 |

可以增加兩個簡單特徵，不需複雜 NLP：

- `asks_specific_question`：是否提出具體數學問句，而非只說「我不懂」。
- `repeats_prior_math`：數學內容是否只是重複題目或 Tutor 上一輪已公布的式子。

## 19. 建議程式介面

可直接放在前述 `phase_router.py`，避免新增另一個模型模組：

```python
@dataclass
class StudentStateDecision:
    phase: str | None
    intent: str
    learning_state: str
    phase_confidence: float
    stuck_confidence: float
    evidence: str
    source: str


def classify_student_state(student_text, last_tutor_question, state, features):
    """明確案例走規則；模糊案例才呼叫 Thinking。"""
```

更新計數集中在單一函式：

```python
def update_stuck_count(count: int, learning_state: str) -> int:
    if learning_state == "stuck":
        return count + 1
    if learning_state in {"partial_progress", "progressing",
                          "active_clarification", "not_applicable"}:
        return 0
    return count  # uncertain
```

不要讓 `_detect_phase()`、`step()`、walkthrough 與 review queue 分別自行加減 `stuck_count`；它們只
提供 state gate，最後由 `update_stuck_count()` 集中更新。

## 20. Thinking 不可用時

不應拋出錯誤或中斷對話。建議最多重試一次，之後使用保守 fallback：

- 明確強卡住且無相關嘗試 → `stuck`。
- 明確有相關新步驟或具體釐清問題 → `partial_progress` / `active_clarification`。
- 其他模糊案例 → `uncertain`，維持原 `stuck_count`。

這比一律判「不卡住」或一律重設為 0 更穩定，也不會因服務短暫失敗突然進入 walkthrough。

## 21. 測試案例

### 必須判卡住

- 「我不知道。」
- 「我試著令 (g(x)=f(x)-x)，但做到這裡後完全不知道下一步。」
- 「你剛才的問題我還是答不出來，可以再拆小一點嗎？」
- 長篇重述題目後說「所以我仍完全沒有想法」。

### 不應判卡住

- 「我不確定，但我想先對 (f') 使用中值定理。」
- 「因為 (x_2>x_1)，所以 (x_2-x_1>0)。 」
- 「為什麼這裡需要驗證閉區間連續？」
- 「我猜可以用反證法，先假設不存在這個 (c)。」
- 上一題只問正負，而學生回答「非負」。

### 不應影響一般 stuck_count

- review 中回答目前局部訂正。
- walkthrough 中回答確認問題。
- `closed` 後詢問已完成證明中的一個細節。
- `writeup_request` 後說「我不知道完整證明格式怎麼寫」。

### 對話序列

1. `stuck → stuck → partial_progress`：計數應為 `1 → 2 → 0`。
2. `stuck → uncertain → stuck`：計數應為 `1 → 1 → 2`，不因模型不確定而虛構連續次數。
3. `partial_progress → stuck → stuck → stuck`：第三次真正連續卡住才進 walkthrough。
4. 學生連續三次用不同說法重複同一無效內容：Thinking 應能判定沒有新進展。
5. 學生答錯但每輪都提出新的相關嘗試：不因答錯而進 walkthrough，應走糾錯引導。

## 22. 評估指標與導入方式

建立一份人工標註的小型卡住資料集，先收集目前測試對話與真實誤判案例。每筆至少包含：

```text
last_tutor_question
student_answer
phase
previous_stuck_count
gold_learning_state
```

建議至少 100–200 筆，特別增加「語氣不確定但有進展」與「有公式但實際沒進展」兩類困難案例。

驗收目標：

- `stuck` precision 優先，建議 ≥ 90%，避免過早升級提示。
- `stuck` recall 建議 ≥ 90%，避免學生真的卡住卻一直被反問。
- walkthrough 提前觸發率接近 0。
- Thinking 不可用時，所有狀態序列測試仍能完成且不拋例外。

導入仍採 shadow mode：先只記錄新舊判定，不改實際 `stuck_count`；累積誤判案例後，再讓新分類器
只接管舊規則判斷不一致或模糊的案例。確認穩定後，才移除目前的固定文字長度硬門檻。

## 23. 實作範圍

若同時實作 phase 與 stuck 精準判斷，建議仍只需：

- 新增一個 `dataset/phase_router.py`，同時輸出 phase intent 與 learning state。
- 在 `tutor_driver.py` 集中呼叫 router 與更新 `stuck_count`。
- 擴充 `test_phase_routing.py` 的序列測試。
- 新增或擴充 `measure_stuck_detection.py`，比較 precision、recall 與提前 walkthrough 次數。
- 視 `test.ipynb` 的檔案載入方式加入新模組。

不需要修改訓練資料，也不需要重新 train。Thinking 模型只負責執行期的模糊語意判斷。
