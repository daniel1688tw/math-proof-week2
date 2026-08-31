# Level 提示機制與資料集完整優化方案

> 文件日期：2026-08-21  
> 適用專案：`math-proof-week2-main`  
> 本文件僅提出方案；本輪不修改程式、資料集、模型或測試。
>
> **狀態更新（2026-08-31）：歷史方案，部分已實作、部分已被後續決策取代。**
> 現行 Level 2 允許一個可執行微支架及必要公式；phase／action／level 的實作審查、
> 尚待修缺口與文件索引見 `docs/code-review-level-phase-2026-08-31.md`。下文的「建議」
> 不應直接當成目前程式行為。

## 一、結論先行

你的方向是對的，但建議補上四個關鍵設計，否則只改 prompt 和增加幾條卡住對話，仍會留下訓練／推論不一致與 level 跳級問題。

1. **Level 0、1、2 的輸出規則改由當輪 prompt 控制**；Driver 仍以確定性狀態選擇 prompt，不能讓模型自己計算目前是第幾級。
2. **Level 2 不再依賴 `core_idea`**；改成要求模型只根據 `<REFERENCE_PROOF>` 與對話歷史，辨認「下一個尚未完成的必要連結」，以文字點出定理、技巧或方向。
3. **資料中的 level 行為自然呈現，不在學生或助教文字中標示 `Level 0/1/2`**；但必須保留一份不送進模型的 sidecar/audit metadata，才能驗證每輪是否真的符合預定狀態。
4. **訓練資料改成「每個 assistant 回合一個目標樣本」並只對最後一個 assistant 回合算 loss**，讓該回合收到與推論時相同的 prompt。否則同一段多輪對話只有一個固定 system prompt，無法同時正確教 Level 0、1、2。

對兩個尚未決定的資料類型，建議如下：

- **逐步教學（walkthrough）**：保留在 `teach_steps` 與端到端情境測試，不混入主要 SFT loss。現在的 walkthrough 是 Driver 確定性輸出且完全繞過生成模型，混入普通 SFT 會教模型在一般引導輪主動講步驟與算式，和部署規則衝突。
- **完整證明審閱（review）**：應放入資料集，但集中訓練「指出第一個重要缺漏並只問一題」及「學生修正後再審」；無缺漏的通過收尾目前可由 Driver 確定性處理，不必占太高比例。

建議在現有 830 筆中英對話上，新增 **400 筆 level-aware canonical dialogues**，總數約 1,230 筆；再展開成約 4,300–5,000 個「單一目標 assistant 回合」的訓練樣本。

## 二、目前實作與資料的盤點結果

### 2.1 現行推論流程

目前 Driver 已有以下結構：

- `stuck_count` 控制 `level = min(stuck_count, 2)`。
- Level 0：只問聚焦問題，不主動點名定理或技巧。
- Level 1：把前一問拆小再問，不點名定理或技巧。
- Level 2：從已驗證 `teach_steps` 取得 `core_idea`，要求模型先透露想法，再問一題，且禁止新增算式。
- 連續卡住 3 次後，進入持久 `walkthrough` phase。
- `walkthrough`、`review`、`closed` 和「拒絕代寫／回應學生嘗試」等 action 會優先於 level。
- walkthrough 由 Driver 用 `explain + check + expected_answer` 確定性組出，不呼叫生成模型。

因此，「用 prompt 控制 Level 0–2」不是從零開始，而是要把現有 prompt 做得更完整，並移除 Level 2 對 `core_idea` 的輸入依賴。

### 2.2 現行資料量

目前 `train.jsonl + val.jsonl` 合計：

| 指標 | 現況 |
| --- | ---: |
| 對話數 | 830 |
| 中文／英文 | 415／415 |
| assistant 回合 | 2,300 |
| user 回合 | 2,300 |
| 每筆 user+assistant 訊息平均數 | 5.54 |
| `dialogues_hint.py` | 中文 12、英文 12 |
| `dialogues_writeup.py` | 中文 8、英文 8 |

用卡住詞彙做保守的靜態掃描後，得到下列近似分布。這不是語意分類器的正式標註，只用來判斷資料缺口：

| 每筆對話最長連續卡住次數 | 對話數 |
| ---: | ---: |
| 0 | 714 |
| 1 | 89 |
| 2 | 13 |
| 3 | 14 |

約 116 筆含卡住片段，但只有約 4 筆看得到不只一段分離的卡住 episode。這支持你的觀察：目前資料確實不足以穩定學到「在同一筆對話中，卡住、恢復、之後再次卡住」的節奏。

### 2.3 三個必須先解決的結構問題

#### 問題 A：訓練與推論的 prompt 不一致

目前 `build.py` 對整段對話只放一份固定 system prompt，內容僅概括說「連續兩次答不出來可點名技巧」。推論時，Driver 卻會為當輪動態追加 Level 0、1 或 2 指示。

如果仍以整段對話一筆 SFT 訓練，模型看不到「這一個 assistant 回合究竟應服從哪一種當輪指示」。資料雖然在文字上呈現逐級加深，卻沒有建立 prompt compliance 的直接訓練訊號。

#### 問題 B：明確卡住的開場可能跳過 Level 1

目前使用者自帶 opener 若明說卡住，第一輪仍先用 Level 0 生成，之後把 `stuck_count` 設為 1。學生下一輪再次卡住時，計數先加到 2，回覆便直接走 Level 2。

也就是可能出現：

```text
開場說不會 → Level 0
再次說不會 → Level 2
```

這與資料中預期的 `Level 0 → Level 1 → Level 2 → walkthrough` 不一致。

#### 問題 C：一旦連續卡住 3 次，就不能再回到普通 level episode

目前 `walkthrough` 是持久 phase。進入後會一路教完，再進 `review`，不會回到 `guide`。因此一筆對話可以先發生多次 0／1／2 卡住 episode，但 **3 次卡住的 episode 必須是 guide 階段的最後一段**。

合法例子：`[1, 2, 1, 3]`。  
不符合現行狀態機的例子：`[3, 1, 2]`。

若希望 `[3, 1]` 也成立，就必須另行設計「退出 walkthrough 回到 guide」；目前不建議增加這種循環，因為會使 phase、教學步驟索引與 review 入口更難驗證。

## 三、建議的狀態定義

### 3.1 Level 只處理普通引導強度

Level 不應同時表示教學 phase、學生答案正誤或 review 狀態。建議維持三條正交控制線：

| 控制線 | 可能值 | 用途 |
| --- | --- | --- |
| `phase` | `guide / walkthrough / review / closed` | 決定目前工作流 |
| `turn_action` | `normal_guide / respond_attempt / answer_clarification / refuse_tutor_write / ...` | 決定當輪特殊任務 |
| `hint_level` | `0 / 1 / 2` | 只決定 `normal_guide` 的提示強度 |

建議優先序：

```text
持久 phase > 當輪 action > hint_level
```

因此學生交來錯誤嘗試時，應走 `respond_attempt`，而不是因為之前卡住兩次就硬套 Level 2。學生要求完整答案時，也應先走拒絕代寫規則。

### 3.2 「卡住」的正式定義

計數對象應改成：**學生對 Tutor 已提出的問題，連續幾次沒有提供可繼續處理的數學內容。**

| 學生當輪狀態 | 計數更新 |
| --- | ---: |
| 明確答不出、無可操作數學內容 | `+1` |
| 正確作答 | 歸零 |
| 錯誤但具體且相關的嘗試 | 歸零，改走糾錯 action |
| 提出具體澄清問題 | 歸零或結束本 episode |
| 純重複／離題／語意不確定 | 保持，不加也不歸零 |
| phase 非 `guide` | 不使用 level 計數 |

「錯誤嘗試」不應等同卡住。學生願意提出可審閱的數學內容，助教應針對錯誤提問，而不是因答錯便一路升級到奉送技巧。

### 3.3 Level 與卡住次數的唯一映射

建議以「本輪學生訊息處理完成後」的連續失敗次數決定回覆：

| 連續未能回答 Tutor 問題的次數 | 下一則回覆 |
| ---: | --- |
| 0 | Level 0 |
| 1 | Level 1 |
| 2 | Level 2 |
| 3 | 進入 walkthrough，不再呼叫普通 level prompt |

開場白沒有上一個 Tutor 問題可回答，因此無論學生說「我完全不會」，首輪都使用 Level 0，且 **不把 opener 當成一次答題失敗**。之後若他第一次答不出 Tutor 的實際問題，才進 Level 1。

完整軌跡應是：

```text
開場無頭緒 → Level 0 聚焦第一問
第一次答不出這一問 → Level 1 拆小
第二次仍答不出 → Level 2 透露方向
第三次仍無法接續 → walkthrough
```

這會同時修正目前的 opener 跳級問題，也使資料標註與程式語意一致。

## 四、Level 0／1／2 Prompt 設計

Prompt 內不必寫出「Level 0／1／2」字樣。程式可以用數字當 key，但送進模型的文字只描述本輪行為，避免模型在回覆中複誦等級名稱。

### 4.1 共通 base prompt

共通規則保留：參考證明只作 grounding、不洩漏完整解、一次一個問題、用精確數學術語、根據學生實際進度推進。

另外建議明文加入：

- 先找學生已完成的最後一個正確連結，再找下一個尚缺連結。
- 不得跳到參考證明後段。
- 不得因學生語氣自信而肯定錯誤內容。
- 只問一個可以由學生在下一輪實際回答的問題。

### 4.2 Level 0 prompt 草案

```text
本輪是一般引導。先判斷學生已經完成到哪一個正確步驟；若他帶來正確內容，只肯定那個具體部分。接著針對下一個尚未完成的必要連結問一個聚焦問題。不要主動引入學生尚未提到的定理名稱、技巧名稱、證明步驟或解法公式；可以沿用題目與學生已說過的符號和概念。只問一個問題。
```

重點是「不要主動引入新名稱」，而不是機械地禁止所有定理名稱。若學生自己已說要用 Rolle 定理，Tutor 可以沿用這個名稱詢問前提。

### 4.3 Level 1 prompt 草案

```text
學生第一次無法回答上一個問題。維持同一個數學目標，但不要原句重問；把上一問拆成一個更小、只需完成一項判斷、回憶一個定義或辨認一個關係的具體子問題。不要主動點出新的定理或技巧名稱，不要提供下一步的計算結果，也不要引入參考證明中的新等式。可以重用題目與既有對話中的式子。只問一個問題。
```

Level 1 的品質不能只用字面相似度判定。真正的合格條件是：回答這個新問題所需的認知步驟，比上一問少且更明確。

### 4.4 Level 2 prompt 草案（不使用 `core_idea`）

```text
學生已第二次無法回答同一段推導。只根據 <REFERENCE_PROOF> 與目前對話，找出緊接在學生已完成內容之後、尚未完成的第一個必要證明連結。第一句明確點出該連結需要的定理、技巧或概念方向；若沒有公認名稱，就用純文字描述一個方向。不得引用或改寫整段參考證明，不得跳到更後面的步驟，不得新增任何等式、不等式或計算結果。第二句只問一個具體問題，讓學生自己執行下一步。
```

Level 2 的固定輸出契約是：

```text
一句方向提示 + 一個接手問題
```

合格例：

> 這裡需要用三角不等式把兩個誤差接起來。你能把目標的絕對值拆成哪兩個已知會變小的量？

不合格例：

- 只再問一次「你想到什麼定理嗎？」——沒有實際透露方向。
- 直接寫出完整關鍵不等式——超出 Level 2 的揭露範圍。
- 點名參考證明後段才用到的定理——跳步。
- 複製 `reference_proof` 的句子——洩漏。

### 4.5 英文 prompt

英文版必須語義平行，不宜只靠機械翻譯。核心契約可寫成：

```text
The student has now failed twice on the same part of the derivation. Using only <REFERENCE_PROOF> and the conversation, identify the first necessary proof link immediately after the student's last completed step. In the first sentence, explicitly name the theorem, technique, or conceptual direction needed for that link; if it has no standard name, describe one direction in words. Do not quote or paraphrase a stretch of the reference proof, jump ahead, or introduce any new equation, inequality, or computed result. In the second sentence, ask exactly one concrete question that lets the student carry out the next step.
```

## 五、移除 Level 2 的 `core_idea` 依賴

### 5.1 建議移除的範圍

第一階段只移除「Level 2 生成路徑」對 `core_idea` 的依賴：

- Level 2 prompt 不再 `.format(core_idea=...)`。
- Level 2 前不再呼叫 `_prepare_core_idea()`。
- `_allowed_equation_src()` 不再把 `core_idea` 放入白名單，只允許題目與學生已寫過的式子。
- `current_core_idea` 不再成為 session state。

`auto_reference.py` 的舊 schema 可以先保留一版做相容讀取，但不再是 Level 2 的必要欄位。確認 walkthrough、舊快取與測試都不需要後，再移除：

- SEGMENTER prompt 中的 `core_idea`。
- `required` schema 中的 `core_idea`。
- `_fallback_core_idea()` 與相關驗證。

這種兩階段退場比一次刪除安全，也能清楚做消融實驗。

### 5.2 Prompt-only Level 2 的風險

移除 `core_idea` 後，4B 模型必須自行從完整參考證明定位下一個缺口，可能發生：

- 點錯定理或點到太後面的定理。
- 把參考證明改寫成提示，造成洩漏。
- 為了具體而輸出公式。
- 對沒有標準定理名稱的構造題給出空泛提示。

因此不能只靠 prompt 宣稱完成，必須保留三道守門：

1. 既有 Level 2 新算式 guard。
2. 參考證明片段洩漏 guard。
3. 新增語意 judge：檢查所點方向是否真的是「下一個尚缺必要連結」，而非任意正確但過早／過晚的概念。

## 六、資料集改造方案

### 6.1 Canonical dialogue 與訓練樣本分離

建議把「完整自然對話」當作 canonical source，再由 builder 展開成真正送入 SFT 的 target samples。

Canonical dialogue 負責：

- 呈現完整學習歷程。
- 容納同一筆對話中多次卡住與恢復。
- 供人工閱讀、狀態回放、端到端評估。

Target sample 負責：

- 只訓練某一個 assistant 回合。
- 注入該回合實際應使用的 prompt。
- 只對最後一個 assistant 回合算 loss。

這樣才能同時滿足「對話內不標 level」和「每一輪真的由 prompt 控制」兩個目標。

### 6.2 對話文字不標 level，但保留 sidecar audit trace

模型可見的 `messages` 內不得出現：

- `[LEVEL 1]`、`Level 2`、`目前等級`。
- `stuck_count=2`。
- `phase=guide` 等控制欄位。

但來源端必須有不送入模型的稽核資料，例如：

```json
{
  "dialogue_id": "zh_A3_levelmix_01",
  "episode_plan": [1, 2],
  "turn_audit": [
    {"turn_id": 1, "learning_state": "progressing", "expected_hint_level": 0},
    {"turn_id": 2, "learning_state": "stuck", "expected_hint_level": 1},
    {"turn_id": 3, "learning_state": "progressing", "expected_hint_level": 0},
    {"turn_id": 4, "learning_state": "stuck", "expected_hint_level": 1},
    {"turn_id": 5, "learning_state": "stuck", "expected_hint_level": 2}
  ]
}
```

這份資料可放在獨立 `dialogue_manifest.jsonl`，或放在 source dict 的 `_audit` 欄位並由 `build.py` 完全剝除。較推薦獨立 sidecar，最不容易誤送入模型。

### 6.3 每題新增四種卡住節奏

現有 50 題、中文與英文各一套。建議每題每語言新增四筆，共：

```text
50 題 × 2 語言 × 4 筆 = 400 筆新 canonical dialogues
```

四種固定配額、隨機安插位置的 schedule：

| Schedule | 卡住 episode 設計 | 目的 | 每語言數量 |
| --- | --- | --- | ---: |
| S0 | 全程 0 次卡住 | 防止模型無條件升級提示 | 50 |
| S1 | 一段 `[1]` | 學一次拆小後恢復 | 50 |
| S2 | `[1,2]` 或 `[2,1]` | 同對話多次卡住與正確 reset | 50 |
| S3 | `[1,3]` 或 `[2,3]` | 多 episode，最後進 walkthrough | 50 |

雙語合計後：

| 每筆最長卡住 run | 新增對話數 |
| ---: | ---: |
| 0 | 100 |
| 1 | 100 |
| 2 | 100 |
| 3 | 100 |

其中 S2、S3 共 200 筆，也就是 50% 新資料含不只一次卡住 episode。這比完全隨機抽樣更可靠；「不定時」由 episode 落在證明哪一步、學生措辭與 `[1,2] / [2,1]` 的次序來實現，而不是讓最終分布碰運氣。

### 6.4 Episode 安插規則

為避免模型學到「只會在開頭卡住」，卡住位置應分層輪替：

- 25% 在辨認定義／前提時發生。
- 35% 在選定理或證明策略時發生。
- 30% 在關鍵構造、不等式或量詞連接時發生。
- 10% 在收尾合法性、特例或定理前提檢查時發生。

每兩個 episode 之間至少要有一個可操作的數學回覆，明確觸發 reset。不能只插一句「我懂了」，因為那不足以證明學生真的恢復推導。

### 6.5 學生卡住措辭要多樣化

應同時涵蓋：

- 明確短句：「我不知道」、「還是想不到」。
- 委婉表達：「這裡我接不起來」、「我看得到目標，但不知道怎麼把兩邊連起來」。
- 長訊息後卡住：「我試過 A、B，但兩條路都卡在同一個地方」。
- 要求再縮小：「可以把剛才那一問再拆小一點嗎？」
- 中英口語變體、拼字與標點變體。
- 負例：學生說「我不確定，但我想先取……」且已提出具體步驟，應算可操作嘗試，不應累加卡住。
- 負例：學生問某個定理前提的具體問題，應走 clarification，而不是卡住升級。

不建議用少量固定句型複製到 400 筆，否則 classifier 只會記關鍵詞。

### 6.6 一筆不標 level 的示意對話

下面只示範自然文字；括號中的說明不會進入正式資料：

```text
學生：我知道要控制 |a_n-a_m|，但不知道要從哪裡接。（普通開場）
助教：收斂的假設目前直接讓你控制的是哪一種距離？（Level 0 行為）

學生：我還是看不出它和兩項之間距離的關係。（第一次卡住）
助教：先只看 a_n 與極限 L：你知道哪個量會在 n 夠大時變小？（Level 1 行為）

學生：是 |a_n-L|，另一項也有 |a_m-L|。（恢復，計數歸零）
助教：很好，現在這兩個量要如何共同控制目標？（Level 0 行為）

學生：我不知道怎麼把它們合起來。（第一次卡住）
助教：若在 a_n-a_m 中間加入同一個中介量，哪個量最自然？（Level 1 行為）

學生：還是想不到要用什麼關係。（第二次卡住）
助教：這裡需要用三角不等式把兩段距離接起來。你能把路徑拆成先到 L、再從 L 到另一項嗎？（Level 2 行為）
```

正式 `messages` 中沒有任何 level 標籤；level 只存在 builder 的稽核 trace 與當輪 system prompt 選擇中。

## 七、逐步教學與完整證明審閱是否放入資料集

### 7.1 逐步教學：不放入主要 SFT loss

目前 walkthrough 的產品契約是：

- 第三次連續卡住後進入。
- 由已驗證 `teach_steps` 確定性呈現 `explain + check`。
- 允許講解與算式。
- 不呼叫生成模型。
- 每步答案由後盾判定，錯誤時揭示參考答案後前進。

這與普通 Level 0–2 的「不能代做、Level 2 不給新算式」是不同模式。若把 walkthrough assistant 文字與普通引導混在同一個 LoRA loss，模型可能在 guide phase 提早模仿 walkthrough。

建議分三層保存：

1. `teach_steps`：真正部署使用的逐步內容。
2. `runtime_scenarios`：含三次卡住、進入 walkthrough、答對／答錯、教完進 review 的完整情境，用於端到端回放。
3. 主要 SFT：walkthrough assistant 回合設為 loss mask，不訓練生成。

若未來決定改成「模型生成 walkthrough」，應另建 mode-specific dataset 或獨立 adapter，不應直接混進這一版。

### 7.2 完整證明審閱：應放入 SFT

Review 仍有模型生成的核心行為：根據參考證明與後盾缺漏清單，用一個問題指出最重要缺口，讓學生自行修正。因此建議保留並擴充。

在 400 筆新增對話中，至少 120 筆延伸到「學生自行提交完整證明」；分配如下：

| Review 情境 | 建議數量 | 是否主要 SFT target |
| --- | ---: | --- |
| 草稿有一個重要缺漏 | 45 | 是 |
| 草稿有多個缺漏，助教只挑第一個 | 30 | 是 |
| 學生局部修正後再審 | 25 | 是 |
| 草稿正確，確認完成 | 15 | 少量；主要由 Driver 確定性處理 |
| 學生質疑是否漏審／要求重開 | 5 | 可放端到端評估 |

Review 樣本不可都放在容易題，也不可總是缺相同的「定理前提」。應涵蓋：

- 定理前提未驗證。
- 量詞順序。
- 嚴格／非嚴格不等號。
- 除法分母未證非零。
- 特例未排除。
- 引用比較對象收斂但未說理由。
- 結論正確但中間有循環論證。

## 八、訓練資料建置方式

### 8.1 每個 assistant 回合展開成一筆 target sample

假設 canonical dialogue 有 6 個 assistant 回合，builder 產生 6 筆訓練目標。第 4 筆概念上是：

```json
{
  "messages": [
    {"role": "system", "content": "base prompt + 本輪行為 prompt + reference proof"},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "...過去回覆..."},
    {"role": "user", "content": "...本輪學生訊息..."},
    {"role": "assistant", "content": "...本輪唯一訓練目標..."}
  ],
  "target_assistant_index": 4
}
```

關鍵要求：

- system prompt 使用該回合在推論時真正會收到的規則。
- 之前的 assistant 回合只作 context，labels 全為 `-100`。
- 只對最後一個 assistant 回合算 loss。
- prompt 文字不寫 level 數字，只寫行為契約。

若仍對前面所有 assistant 回合算 loss，前面原本的 Level 0 回覆會被放在「本輪是 Level 2」的 system prompt 下再次訓練，形成自相矛盾的 supervision。

### 8.2 512 token 限制下的 context window

目前訓練預設 `MAX_LEN=512`，且完整參考證明已占不少 token。不建議只為新資料直接提高上限，因為現有訓練說明已記錄 6 GB GPU 的記憶體限制。

建議：

- canonical dialogue 保存完整歷程。
- target sample 只保留最近足以理解當輪的 2–4 組 user/assistant 互動。
- Level 1 至少保留上一個 Tutor 問題與學生第一次卡住訊息。
- Level 2 至少保留上一問、前一次縮小提示，以及學生第二次卡住訊息。
- 當輪 prompt 已告知提示強度，模型不需要靠超長歷史自行重算次數。
- builder 輸出 token 長度分布與被截斷比例；若 system + reference proof 本身已太長，應先精簡 base prompt，而非截掉最後目標。

### 8.3 資料切分改為按題目分組

目前是把所有對話 shuffle 後做 9:1，容易讓同一題、同一參考證明，甚至中英翻譯對出現在 train 與 val 兩側。

建議按 `problem_id` 分組並跨語言綁定：

```text
每個主題 10 題：8 train / 1 validation / 1 test
總計：40 train / 5 validation / 5 test
```

同一題的所有 persona、schedule、中文與英文必須在同一 split。這樣才測得到模型是否學會 level 行為，而不是記住該題的參考證明。

另外保留現有 held-out、hard-math、cross-domain 評估，不拿來調 prompt。

### 8.4 目標回合分布

不應只看 canonical dialogue 數量，還要看真正算 loss 的 assistant targets。建議最終有效 target 比例約為：

| Target 類型 | 建議比例 |
| --- | ---: |
| 一般 Level 0 推進 | 40–45% |
| Level 1 拆小 | 15–20% |
| Level 2 透露方向 | 15–20% |
| 回應具體嘗試／糾錯 | 10–15% |
| Review 缺漏提問 | 10–15% |

walkthrough、確定性 writeup request、確定性 review pass 不納入或只占極少量。

## 九、資料品質守門

### 9.1 靜態檢查

新增資料應至少檢查：

- `messages` 中 level marker 為 0 次。
- episode schedule 與 sidecar trace 一致。
- 每兩個 episode 間確實有 actionable math reset。
- 三次卡住只在最後一個 guide episode 出現。
- Level 0 不主動新增定理／技巧或解法步驟。
- Level 1 是實質拆小，而非換句話重複。
- Level 2 第一部分確實透露一個方向，且沒有新等式或不等式。
- 每個普通引導回合最多一個問號。
- review 只處理一個最重要缺漏。
- 中英文語義平行，但措辭自然。

### 9.2 語意 judge

純 regex 無法判斷「拆得更小」或「是否點到下一個缺口」。應使用獨立 judge，輸出固定 JSON：

```json
{
  "level_policy_pass": true,
  "next_link_grounded": true,
  "single_question": true,
  "new_formula": false,
  "premature_reveal": false,
  "feedback": ""
}
```

Level 2 judge 必須同時看到題目、參考證明、對話歷史與助教回覆；只看助教單句無法知道它是否跳步。

### 9.3 人工抽查

每批新增 50 筆，至少人工抽查：

- 全部 Level 2 回合。
- 全部三次卡住進 walkthrough 的邊界。
- 全部 review 多缺漏案例。
- 20% Level 1 回合。
- 所有 validator/judge 意見不一致的樣本。

數學內容不可只由同一個生成模型自產自審；至少保留一層獨立 verifier 或人工複核。

## 十、評估與消融實驗

### 10.1 四層評估

#### A. 單輪 prompt compliance

固定同一題與同一段對話，分別注入三種 prompt，檢查：

- Level 0 是否保持開放而不奉送。
- Level 1 是否真的拆小。
- Level 2 是否明確透露方向但不給算式。

#### B. 多輪狀態機回放

至少涵蓋：

```text
[0]
[1]
[2]
[3]
[1,2]
[2,1]
[1,2,3]
卡住 → 錯誤但具體嘗試 → reset
卡住 → 具體澄清問題 → reset
卡住中要求完整答案 → refuse action 優先
review 中說卡住 → review phase 優先，不得進 walkthrough
```

#### C. 數學正確性與洩漏

檢查 Level 2 點名是否與參考證明下一連結一致、是否洩漏完整步驟、是否新增公式、是否把錯誤學生嘗試誤判為正確。

#### D. 端到端產品流程

測完整鏈：

```text
guide → 多次卡住／恢復 → 最後三次卡住 → walkthrough
→ 教完 → 學生自行寫證明 → review → 局部修正 → closed
```

### 10.2 建議門檻

| 指標 | 建議門檻 |
| --- | ---: |
| Level prompt 遵從率 | ≥ 95% |
| 普通引導一輪一問 | ≥ 98% |
| Level 1 實質拆小率 | ≥ 92% |
| Level 2 下一連結正確率 | ≥ 92% |
| Level 2 新公式率 | ≤ 2% |
| Level 0/1 提前透露率 | ≤ 3% |
| actionable attempt reset 正確率 | ≥ 97% |
| 第三次卡住進 walkthrough | 100% |
| 特殊 phase/action 優先序 | 100% |
| 多 episode 完整路徑通過率 | ≥ 90% |
| Review 第一重要缺漏命中率 | ≥ 90% |

### 10.3 2×2 消融

為確認移除 `core_idea` 是否真的值得，建議保留四組：

| 組別 | 訓練資料 | Level 2 輸入 |
| --- | --- | --- |
| A | 舊資料／舊 adapter | 注入 `core_idea`（現況基線） |
| B | 舊資料／舊 adapter | prompt-only，不注入 `core_idea` |
| C | 新 level-aware 資料／新 adapter | prompt-only（預定部署組） |
| D | 新 level-aware 資料／新 adapter | 注入 `core_idea`（只作診斷） |

重點比較 B 與 C，可看出資料改造的增益；比較 C 與 D，可判斷 `core_idea` 對正確率、延遲、洩漏率究竟是幫助還是負擔。

## 十一、預計修改的檔案與責任邊界

以下只是之後的實作地圖，本輪不動檔案：

| 檔案 | 預計工作 |
| --- | --- |
| `dataset/tutor_driver.py` | 改 Level prompt、移除 Level 2 的 `core_idea` 注入、修 opener 計數、保留公式與洩漏 guard |
| `dataset/phase_router.py` | 明確化 stuck/reset 契約，補 episode 與特殊 phase 測試 |
| `dataset/auto_reference.py` | 先停止 Level 2 消費 `core_idea`，之後再分階段移除 schema 與 fallback |
| `dataset/src/dialogues_level_mixed.py` | 新增中文 level-aware canonical dialogues |
| `dataset/src_en/dialogues_level_mixed.py` | 新增自然英文平行對話 |
| `dataset/build.py` | 產生 sidecar、按 assistant 回合展開、注入當輪 prompt、按 problem split |
| `dataset/validate.py` | 新增 schedule、marker、level policy、split leakage 檢查 |
| `dataset/test_dataset.py` | 新增 target 分布、episode 分布、last-assistant-only 統計 |
| `learn_path/socratic_tutor/train_qlora.py` | 只對指定的最後 assistant 回合算 loss |
| `server_train/workspace/train_qlora.py` | 與上列訓練邏輯同步 |
| `dataset/test_driver_unit.py` | opener 0→1→2、不跳級、reset、Level 2 無 core_idea |
| `dataset/test_phase_routing.py` | 多 episode、三次卡住最後進 walkthrough、phase/action 優先 |
| 新增 `dataset/eval_level_policy.py` | 單輪三 prompt 與多輪 schedule 評估 |

## 十二、建議執行順序

### Phase 0：凍結基線

- 保存目前 adapter、prompt、eval 結果與隨機種子。
- 跑一次現有 regression suite，記錄 Level 0／1／2、walkthrough、review 指標。

### Phase 1：先修狀態契約，不重訓

- 統一 opener 不計為「回答失敗」。
- 固定 0→1→2→walkthrough 映射。
- 加入多 episode 與 reset 單元測試。
- 只用 prompt-only Level 2 做 B 組評估，量化移除 `core_idea` 的直接影響。

### Phase 2：建立 400 筆 canonical dialogues

- 每批 50 筆，先中文後自然英文對應。
- 每批通過靜態 validator、語意 judge 與人工抽查才合併。
- 先完成 50 筆 pilot，確認 schedule 與 prompt 契約，再全量擴寫。

### Phase 3：改 builder 與 loss masking

- canonical dialogue 展開成 per-assistant target。
- sidecar 不進模型。
- 只訓練最後 assistant。
- 按 problem ID 分組切 train／validation／test。
- 輸出 token、target 類型與截斷統計。

### Phase 4：重新訓練與消融

- 跑 A/B/C/D 四組或至少 A/B/C。
- 先看 level policy 與洩漏，再看一般數學引導與 review，避免只用 eval loss 選模型。

### Phase 5：部署前端到端守門

- 使用真實 Driver 跑多 episode 對話。
- 驗證第三次卡住只進一次 walkthrough。
- 驗證 walkthrough 結束後只進 writeup/review，不回到 level prompt。
- 驗證 review、closed、拒絕代寫等既有能力沒有退化。

## 十三、驗收條件

只有同時滿足以下條件才建議替換現有版本：

1. 開場卡住不再跳過 Level 1。
2. 同一筆對話可正確處理兩段以上 0／1／2 episode，且中間 reset 正確。
3. Level 2 完全不讀 `core_idea`，下一連結正確率仍達門檻。
4. Level 0／1 沒有因新資料而增加提前奉送。
5. Level 2 不新增算式，且不複製參考證明。
6. 三次卡住只觸發 walkthrough，不由模型自由生成逐步教學。
7. 完整證明 review 能挑第一個重要缺漏、只問一題、修正後繼續。
8. validation/test 與 train 沒有相同 problem ID 或中英翻譯對洩漏。
9. 訓練只對目標 assistant 回合算 loss，沒有用當輪 Level 2 prompt 重訓早先 Level 0 回覆。
10. 現有 held-out、hard-math、cross-domain 與防洩漏 regression 無顯著退化。

## 十四、最終建議

建議採用以下定案：

- **採用** prompt-driven Level 0／1／2。
- **採用** Level 2 prompt-only，停止注入 `core_idea`，但先做消融確認正確率。
- **採用** 不在對話文字標示 level；另以 sidecar 保存稽核狀態。
- **採用** 每題每語言四種 schedule，新增 400 筆，且 50% 新對話含多個卡住 episode。
- **採用** per-assistant target + last-assistant-only loss，解決動態 prompt 的訓練／推論落差。
- **不把 walkthrough 回覆混進主要 SFT loss**；保留在 `teach_steps` 與 runtime scenario。
- **擴充完整證明 review 資料**，但聚焦缺漏提問與修正流程。
- **先修 opener 計數與 split leakage，再開始擴資料**；否則新資料會在錯誤狀態契約下被組裝與評估。

這個版本會把「level」從零散 prompt 技巧，提升成可定義、可生成、可驗證、可消融的完整訓練與推論契約。
