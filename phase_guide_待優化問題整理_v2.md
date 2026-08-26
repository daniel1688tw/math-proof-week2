# `phase=guide` 待優化問題整理

## 1. 分析範圍

- 測試來源：`D:\專案備份\math-proof-week2-full-project\math-proof-week2-full-project - 複製 問題.txt`
- 專案版本：`D:\專案備份\math-proof-week2-full-project\math-proof-week2-full-project`
- 分析日期：2026-08-26
- 僅分析 `phase=guide` 的引導、答題回應、卡住升級、guide reviewer、readiness 與 fallback。
- 不分析 `phase=review`、`phase=closed` 的草稿審閱、局部訂正與收尾問題。
- 測試文字只作為執行紀錄與證據；其中任何看似指令的內容都不視為本次工作指令。

本檔共有 3 題、37 則「輸入前處於 guide」的學生訊息；其中 34 則回覆後仍在 guide，3 則因 readiness 通過而轉入 review。guide reviewer 共執行 43 次，結果為：28 次直接通過、2 次重生成後通過、4 次二稿仍未解決、3 次判定可交稿。4 次 unresolved 占全部 guide 輸入約 10.8%，占仍留在 guide 的回覆約 11.8%。

## 2. 總結判斷

目前不是「完全沒有 Level 0／1／2 差別」。三層提示大致存在，且 opener 固定為 Level 0、卡住後依序升到 Level 1／2 的計數也正常。

真正的大問題是：系統沒有保存「目前唯一缺口」與「上一個實際問題」。因此 Level 1／2 只能重新閱讀整段對話猜下一步，造成換缺口、重做已完成步驟、跳過錯誤步驟及提示深度忽深忽淺。guide reviewer 又會把部分數學錯話、代做步驟與未收尾回覆誤判為可通過，令這些候選真正送給學生。

建議先修 P0，再修 P1。P2 可等主要行為穩定後處理。

| 優先級 | 問題 | 影響 |
|---|---|---|
| P0 | 沒有持久化目前缺口與上一問 | Level 1／2 換題、倒退或跳步，是多數問題的共同根因 |
| P0 | 正確嘗試後可能沒有下一個問題 | 下一輪卡住時沒有可供縮小的上一問，直接倒退重做 |
| P0 | 尚未修正的錯誤會被跳過 | Tutor 後續推導建立在未完成或錯誤步驟上 |
| P0 | reviewer 對數學正確性、代做與承接出現誤放行 | 錯誤或不合 Level 的回覆直接面向學生 |
| P0 | reviewer unresolved 時 fallback 空泛 | 學生已明確卡住，卻收到「你有什麼想法」式無效問題 |
| P1 | Level 0 深度不穩 | 有時過早洩漏構造，有時又過度抽象 |
| P1 | Level 1 不一定縮小同一問 | 可能重問已完成內容，或一次寫出太多中間式 |
| P1 | Level 2 不一定只給一個支架 | 可能同時給定理、構造與操作，也可能完全沒有可操作支架 |
| P1 | 重複的學生步驟仍被視為新進度 | stuck 歸零，對話形成重複迴圈 |
| P1 | 簡短但明確的錯誤答案可能被路由成 ordinary | 無法穩定使用 respond_attempt 的糾錯規則 |
| P2 | 少數數學措辭不精確 | 可能讓學生形成錯誤定理印象 |
| P2 | guide reviewer 延遲偏高 | 每次審查平均約 32.4 秒，互動等待明顯 |
| P2 | 「最後一次提示」等措辭與真實流程不符 | 同一題可出現多次「最後一次」，降低一致性 |

## 3. P0：最應先修正的問題

### P0-1　沒有保存唯一的 `active_gap` 與上一個實際問題

#### 測試證據

- 三份 phase report 的所有 guide state 都沒有 `active_gap`、`last_guide_question` 或同等狀態。
- 第一題一開始由「構造函數」切到「哪個定理」，尚未沿同一問逐層縮小。
- 第三題學生把 $F(b)-F(a)$ 的順序寫反後，下一輪 Tutor 改問 $F$ 為何可導，未先完成原本的正負號缺口。
- 第二題學生已寫出 $|a_nb_n|\le M|a_n|$，下一輪卡住後 Tutor 又回去要求寫同一個上界。

#### 根因

Level 1／2 prompt 只收到整段對話與參考證明，沒有一個確定性的「本輪只能處理這個缺口」狀態。reviewer 也沒有 `stays_on_active_gap` 判準，所以每輪都可能重新選證明步驟。

#### 簡單且通用的修法

只增加兩段文字狀態，不建立 proof graph，也不擴增題型關鍵詞：

- `active_gap`：目前唯一尚未完成的第一個數學連結。
- `last_guide_question`：上一輪實際送給學生的問題。

學生只是說不會、沒有提出新步驟時，保留原 `active_gap`。學生答對、答錯、提出可審閱的具體數學內容或明確局部問題時，才允許 reviewer 更新缺口。Level 1／2 的 system prompt 與 reviewer 都必須收到這兩欄。

#### 驗收條件

- 同一缺口連續卡住時，Level 0／1／2 的主題必須相同。
- Level 1 只能縮小上一問；Level 2 只能替同一問多加一個支架。
- 學生未修正錯誤前，不得改問後面的證明步驟。

### P0-2　`respond_attempt` 正確回應後可能沒有下一問

#### 測試證據

第二題學生第一次推出

```text
|a_n b_n| = |a_n||b_n| ≤ M|a_n|
```

Tutor 只回覆：

```text
很好，比較判別法就能收尾了。
```

回覆沒有問題，phase 仍是 guide。學生下一輪說不會後，Tutor 只好倒退重問剛才已完成的上界。

#### 根因

目前確定性 `needs_q` 只涵蓋 Level 小於 2 的 `normal_guide`／拒絕代寫，不涵蓋 `respond_attempt`、`answer_clarification` 與 Level 2。

#### 簡單且通用的修法

只要最後仍是 guide，以下所有 guide action 都必須留下恰好一個聚焦問題：

- `normal_guide`
- `respond_attempt`
- `answer_clarification`
- `refuse_tutor_write`

唯一例外是 readiness 已通過，同一輪由 Controller 改成「請寫完整證明」。

#### 驗收條件

- 學生完成一個正確中間步驟後，Tutor 必須簡短確認並問第一個尚未完成的連結。
- 下一輪學生卡住時，Level 1 必須縮小這個新問題，不得回到前一個已完成步驟。

### P0-3　錯誤步驟尚未修正，Tutor 卻切換到其他缺口

#### 測試證據

第三題學生寫成

```text
∫_a^b f(x)dx = F(a)-F(b)
```

Tutor 正確指出順序應為 $F(b)-F(a)$。但學生接著說「我束手無策」後，Tutor 改問「$F$ 是由哪個定理保證可導」，沒有先要求學生修正原本的符號錯誤。下一輪又繼續問 $F'(x)$，使未修正的錯誤被暫時跳過。

#### 根因

reviewer 只在最新學生訊息本身被分類為 `correct`／`incorrect` 時強制檢查 `addresses_latest_student_step`。當下一則訊息只是 stuck、被判為 `no_step`，上一輪尚未完成的錯誤就失去約束力。

#### 簡單且通用的修法

把「目前尚未修正的錯誤」直接視為 `active_gap`。學生接著只說不會時仍保留它。`addresses_latest_student_step` 應對 correct、incorrect、no_step 全部生效；no_step 時要檢查候選是否承接目前 active gap，而不是只看這句「我不會」。

#### 驗收條件

- 學生答錯後連續說不會，Level 1／2 都必須協助修正同一錯誤。
- 未修正前，Tutor 不得使用該錯誤結果，也不得前往另一個證明步驟。

### P0-4　guide reviewer 仍會誤放行數學錯話、代做與錯誤所有權

#### 測試證據

1. 第二題學生回答「比值判別法」後，Tutor 說：

   ```text
   比值判別法用在通項的比值趨零，這裡的條件不適用。
   ```

   這個敘述不正確。比值判別法的一般條件是相鄰項絕對值比的極限或上極限小於 1，不是「通項的比值趨零」。reviewer 卻標為 `mathematically_correct=true`。

2. 第一題 Level 1 直接告訴學生把兩個端點式「相加」，並把兩條式子完整重述後才問結果；reviewer 仍標為未完成步驟 `false`。

3. 第三題 Level 1 已完整寫出

   ```text
   F'(c)=[F(b)-F(a)]/(b-a)
   ```

   再要求學生代入；這已替學生完成當前關鍵定理的套用，但 reviewer 仍放行。

4. 第二題 Tutor 主動引入「比較判別法」後沒有下一問，reviewer 雖回報 `level_policy_pass=false`，最終仍放行。

#### 根因

- `level_policy_pass=false` 單獨不會退件。
- `completes_any_unfinished_step` 的判準仍容易把「Tutor 直接寫出中間結果」誤當成「只是問學生證明該結果」。
- 數學正確性欄位沒有穩定抓住錯誤的定理敘述。
- 缺少「是否留在 active gap」的獨立欄位。

#### 簡單且通用的修法

不需要新增多個 reviewer，只修正現有單一 reviewer：

- 新增 `stays_on_active_gap`，Level 1／2 為 false 時退件。
- 明確規定：Tutor 只問學生如何證明某缺口，不算完成；Tutor 自己寫出等式、套用定理或運算結果，才算完成未完成步驟。
- 數學正確性必須逐一核對候選中的定理敘述、正負號、導數階數、等式與不等式。
- `addresses_latest_student_step` 對所有 step status 都是硬條件。
- 不建議只把模糊的 `level_policy_pass` 全面改成硬閘；應使用上述具體欄位退件，避免高品質提示因籠統判分被誤殺。

#### 驗收條件

- 錯誤的定理敘述一定退件。
- Tutor 自己完成當前中間式，即使句尾仍有問題，也一定退件。
- 只把缺口當成提問目標、不直接給結果的候選應可通過。

### P0-5　reviewer 二稿仍失敗時，fallback 幾乎沒有教學作用

#### 測試證據

4 次 `guide_policy_unresolved` 最後出現同型句子，例如：

```text
我們先聚焦在目前的缺口：你有什麼想法可以得出「利用 f(0)=f(2) 來證明 g(1)=-g(0)」？
```

```text
我們先聚焦在目前的缺口：你有什麼想法可以得出「應用中間值定理」？
```

```text
我們先聚焦在目前的缺口：你有什麼想法可以得出「應用中值定理以得到 F'(c)=...」？
```

學生已連續明說不會，fallback 卻仍問「有什麼想法」，只把 reviewer 的缺口文字直接塞入模板，沒有比上一問多一層支架。

#### 簡單且通用的修法

fallback 直接依 Level 與 `active_gap` 使用三種通用模板，不再額外呼叫模型：

- Level 0：問題目哪個已知條件與缺口最直接相關。
- Level 1：問要先建立哪個更小的等式、界、前提或局部性質。
- Level 2：點出 reviewer 已確認的唯一方向，要求學生檢查其前提並做一個明確數學動作。

同一層準備兩種措辭輪換，避免 fallback 連續重複。

#### 驗收條件

- unresolved 後的回覆仍要符合當前 Level 深度。
- 不得再出現只把缺口包進「你有什麼想法」的同義反問。

## 4. P1：Level 與進度品質問題

### P1-1　Level 0 深度不一致

#### 證據

- 第一題第一輪直接說「先造一個新函數」，已透露參考證明的核心構造。
- 第二題第一輪「要證絕對收斂，要控制哪個級數」深度合理。
- 第三題第一輪問「怎麼造出這個某點對應的量」，較抽象且不容易直接作答。

#### 通用修法

Level 0 只能使用題目明示條件、目標與學生已寫內容，問一個宏觀但有明確思考對象的問題；不得引入參考證明才有的定理、技巧、輔助函數或構造，也不得只問空泛方向。

### P1-2　Level 1 未穩定縮小上一問

#### 證據

- 第一題由「構造函數」切到「聯想到哪個定理」。
- 第二題在學生已完成上界後，又要求重新寫同一個上界。
- 第三題直接提供完整中值定理等式，或同時提供兩個代入式，只留下最後抄寫工作。

#### 通用修法

Level 1 必須收到 `last_guide_question`，並被明確要求只把這一問縮小一次；可指向題設或學生已有的一個條件、數值、式子或局部性質，但不得換缺口、新增定理、提供新公式或重做已完成內容。

### P1-3　Level 2 的「一個支架」不穩定

#### 證據

- 第一題早期 Level 2 同時提供「中間值定理」「端點異號條件」及「先造函數」，一次給了多個支架。
- 第二題 Level 2 重複學生已完成的分解與上界，而不是推進到比較判別法的使用條件。
- 第三題一次能給出合理方向，但 reviewer unresolved 時又退化成沒有實質支架的反問。

#### 通用修法

Level 2 仍只處理 active gap，恰好提供一個定理、技巧、概念方向或輔助構造。若輔助構造必須用公式定義，最多允許一個定義式；不得同時代做定理套用、運算過程與結果，句尾仍要留一個有意義的數學動作給學生。

### P1-4　學生重複舊步驟仍被算成新進度

#### 證據

第二題學生已寫過一次 $|a_nb_n|\le M|a_n|$。Tutor 倒退重問後，學生逐字再寫一次，router 仍判為 `show_attempt / partial_progress`，`stuck_count` 歸零。

#### 通用修法

判斷進度時只比較學生自己的數學內容，不把 Tutor 提示算成學生所有權；若學生只是重述自己已完成的相同關係，且沒有回答目前的新問題，就標為 no new step，保留 active gap 與既有 stuck 計數。使用語意比較或數學關係正規化，不擴增題目關鍵詞列表。

### P1-5　明確但簡短的錯誤答案被路由成 `ordinary`

#### 證據

第二題 Tutor 問應使用哪個判別法，學生回答「比值判別法」。這明確回答了當前數學問題，但 router 給出 `intent=ordinary`、`learning_state=uncertain`、`turn_action=normal_guide`，不是 `respond_attempt`。

#### 通用修法

只要學生訊息直接回答上一個問題，即使很短或答案錯誤，也應視為可審閱的 attempt。router 只判「是否在回答／是否有可審閱數學內容」，正誤交給 guide reviewer，不用列舉定理名稱。

### P1-6　Tutor 偶爾把應由學生完成的中間理由先說掉

#### 證據

- 第一題學生剛定義 $g$，Tutor 直接宣告「$g$ 是連續的」。
- 第一題學生尚未連結兩個端點式時，Tutor 直接提出「兩者相加」。
- 第三題 Level 1 直接寫出完整中值定理等式與最後代入材料。

#### 通用修法

reviewer 的學生所有權只能以 `student_messages` 為證據。Tutor 已說過的提示、參考證明與候選本身只能用來理解順序與核對正確性，不得算成學生已完成。若候選把新中間結果陳述成事實，就以 `completes_any_unfinished_step=true` 退件。

### P1-7　readiness 診斷欄位偶有互相矛盾

#### 證據

第一題轉入 review 時，reviewer 同時回傳：

- `ready_for_writeup=true`
- `first_missing_step="g is continuous on [0,1]"`
- feedback 又說 proof is complete

最後切換不一定錯，因為學生可能已掌握骨架、可在完整證明補寫形式細節；但診斷語意不一致，之後很難判斷究竟是「核心步驟已完成」還是「仍缺一步」。

#### 通用修法

不增加 schema：直接規定若骨架已完整、`ready_for_writeup=true`，`first_missing_step` 應為空字串；只有真正尚未完成的第一個核心連結才填入。形式化細節可放在 feedback，但不要同時標成 first missing step。

## 5. P2：次要但仍值得記錄的問題

### P2-1　「符號相反」的措辭不夠精確

第一題 Tutor 說 $g(0)$ 與 $g(1)$「符號相反」。若兩者都為零，嚴格來說不是一正一負。較精確且通用的說法是 $g(0)g(1)\le 0$，或分成「某端點為零」與「兩端異號」兩種情況。

### P2-2　guide reviewer 延遲偏高

43 次可量測的 reviewer 呼叫，單次耗時約 22.8–48.1 秒，平均約 32.4 秒。每個 guide 輸入平均承擔約 37.7 秒 reviewer 時間，尚未計入 Tutor 生成本身。

簡單改善方式是先做無問句、重複、Level 2 算式數量等確定性守衛，再把較穩定的候選交給 reviewer；維持正常一審、只有失敗才重生成複審，不再增加新的模型或審查層。

### P2-3　「最後一次提示」與實際流程不一致

同一題在不同缺口可多次出現「最後一次提示／最後一步」。這不影響數學，但可能令學生誤以為之後不會再得到協助。可改成「再給一層提示」或直接陳述支架，不把內部 Level 狀態說給學生。

## 6. 三題逐題問題索引

### 題目一：連續函數與平移差函數

- Level 0 過早給出「構造新函數」。
- Level 1 從構造缺口切到定理缺口。
- 三次 reviewer unresolved 後出現空泛 fallback。
- Level 1 曾直接給出端點式相加操作。
- 「符號相反」未處理兩端皆零的精確語意。
- readiness 的 `first_missing_step` 與 `ready_for_writeup` 不一致。

### 題目二：絕對收斂級數乘有界數列

- 正確上界後 Tutor 沒有留下下一問。
- 後續 Level 1／2 重問已完成上界，形成重複迴圈。
- 學生重複同一式子仍被算成新進度。
- 「比值判別法用在通項比值趨零」是數學錯話，reviewer 未攔截。
- 簡短錯誤答案被路由成 ordinary，而不是 respond_attempt。

### 題目三：積分中值定理

- 學生的 $F(a)-F(b)$ 符號錯誤尚未修正，Tutor 就切到 $F'$ 缺口。
- Level 1 曾直接提供完整中值定理等式。
- Level 1 最後直接提供全部代入材料，提示過深。
- reviewer unresolved 時 fallback 只把缺口包進「有什麼想法」。

## 7. 建議修正順序

1. 新增 `active_gap` 與 `last_guide_question`，並把它們送進 Level 1／2 prompt 與 reviewer。
2. 所有仍留在 guide 的 action 強制以一個聚焦問題收尾；readiness 通過除外。
3. reviewer 新增 `stays_on_active_gap`，並修正數學正確性、學生所有權與 `completes_any_unfinished_step` 判準。
4. fallback 改成依 Level 與 active gap 的三層確定性模板。
5. router 將直接回答上一問的簡短數學內容一律視為 attempt；重複舊步驟不得算新進度。
6. 最後再處理延遲、措辭與細微數學表述。

這個順序不需要 proof graph、題型分類器、額外 reviewer 或關鍵詞擴增，對微積分、級數及一般證明題都能共用。

## 8. 修正後最低限度驗收案例

至少要測以下情況：

1. opener 明說不會：仍為 Level 0、`stuck_count=0`。
2. 同一問題連續卡兩次：依序 Level 1、Level 2，而且三輪 `active_gap` 相同。
3. 學生答對一個中間步驟：Tutor 問新的第一缺口；下一輪卡住不得倒退。
4. 學生答錯後再說不會：Tutor 必須持續修正同一錯誤，不得換題。
5. 學生逐字重複已完成步驟：不得當成新進度或清除目前缺口。
6. 學生只回答一個錯誤定理名稱：必須走 respond_attempt，並正確說明錯在哪裡。
7. Level 1 候選直接寫出新中間等式：reviewer 應退件。
8. Level 2 候選同時給定理、運算與結果：reviewer 或確定性守衛應退件。
9. reviewer 二稿仍失敗：fallback 仍須符合當前 Level 且指向 active gap，不得只問「有什麼想法」。
10. 學生完成整體證明骨架：同一輪轉入 `review/awaiting_submission`，不再硬補 guide 問題。

## 9. 本次測試中已正常、暫不需要改動的部分

- 三題 opener 即使明說卡住，仍固定從 Level 0、`stuck_count=0` 開始。
- 明確卡住後的計數大致遵守 0→1→2。
- 學生提出新的具體數學內容時，stuck 通常能歸零。
- 三題最後都能在學生自行推出核心結論後主動要求完整證明。
- 本次沒有出現 guide reviewer 大量 `null`／`unavailable`；主要問題是 4 次 unresolved 及多次「解析成功但判斷錯誤」。
- 本次沒有真正進入 walkthrough，因此不能用這份紀錄判定 walkthrough 品質，也不應據此修改 walkthrough。
