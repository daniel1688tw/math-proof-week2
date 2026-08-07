# Code review — 逐步教學可評分化（2026-08-07 整合批次）

**審閱範圍**：`11ab1ae..a2ba4fd`（3 個 commit）
`7efc16f` 逐步教學可評分化（Codex 交接整合）／`8b8b014` repo 清理與文件更新／
`a2ba4fd` build.py 中間產物移出版控。

**逐檔行數**：`tutor_driver.py` +581、`auto_reference.py` +273、`regression_suite.py` +77、
`render_transcripts.py` 新增 214、`test_driver_unit.py` +421（248 → 303 條斷言）、
`app.py` / `review_backstop.py` / `build.py` / `eval_svt_e2e.py` 小幅。

**驗證狀態（本次審閱實跑）**
- `test_driver_unit.py` — 303 條全過（計數用 `grep -cE "^  (✓|✗) "`）
- `test_phase_routing.py` — 全過；階段分佈含 `walkthrough 48 輪`、等級 2 提示輪 32 次、
  `ladder_idx` 最大值 2（多輪升級路徑確實有被回放語料覆蓋）

**總評：4.2 / 5，可維持現狀部署。** 無 Critical。設計取捨（教學輪改確定性模板、
不加第二個 LLM verifier、加重試上限）都有實測依據且在註解裡交代了理由，這批的
註解品質是全 repo 最好的一段。下列 3 項 Important 都是**新加的守衛在特定輸入下
不生效**，不是回歸——但其中兩項打在「最需要幫助的學生」身上，與 #17 同型。

---

---

## 修復狀態（2026-08-07 第二批）

**三項 Important 全部修完，完整守門 exit 0**（計分卡
`regression_scores/2026-08-07T183953_a2ba4fd.json`，25 項硬性指標全 ≥ 基準）。
全程 TDD——6 條斷言先以正確理由失敗才動手；單元測試 303 → **313 條 / 32 組**。

| 項目 | 修法 |
|---|---|
| I-1 | 錯答清單移到答案鍵**之後**比對，並套用 `accepted_answers` 既有的短答保護 |
| I-2 | 比對對象加上 `step["explain"]` 本身，新增 `_strip_walk_template()` 先剝掉 driver 自己加的模板（回饋前綴／步驟標頭／確認問題段）|
| I-3 | `_detect_lang` 直接沿用 `tutor_driver.detect_lang`（函式內延遲 import，同 `validate_ladder` 的既有模式）；`build_reference` 把語言算一次往下傳給 `fallback_steps` / `ensure_checkable_steps` / `teach_steps_lang` |

**唯一可歸因的證據是 walkthrough 探針，不是 judge 分數。**
Tier 1/2 的 104 筆回覆與上輪逐字 **104/104 相同** ⇒ 固定探針零變化 ⇒ 所有 `judge_*`
波動（含上升）都是評審雜訊。真正的證據在 `*_probes.json`：

| | `11ab1ae`（修復前）| `a2ba4fd`（修復後）|
|---|:---:|:---:|
| A6/zh 相鄰逐字重複 | 1 | **0** |
| A6/en 相鄰逐字重複 | 1 | **0** |

> TDD 過程本身的教訓：**I-2 的測試第一版是綠的，但測不到東西**——`expected_answer`
> 被我設成 `explain` 的子字串，於是「回覆含答案」在模型逐字吐回時也成立，斷言恆真。
> 與 `test_phase_routing.py` 的 V4、LADDER 那輪的「48 字 fixture」完全同型：
> **每條斷言都要問一次「什麼樣的生產程式碼改動會讓它失敗」。**

### 這輪守門讀對話新抓到的問題（弱點 #23，未修）

`a2ba4fd_transcripts.md:556`，A6/zh 進 walkthrough 的**前一輪**（等級 2、提示梯已耗盡）：

> 這題需要「取二次項當下界」這個技巧，**你自己查一下**二項式展開就知道了。

與 I-2 同一個失敗模式，但 `_REFUSE_TEACH_RE` 只作用於 walkthrough **重講輪**，蓋不到這裡。
**非本批引進**：與上輪逐字相同，且屬 104/104 相同的固定探針集合——長期存在，只是沒人讀到。
修法方向與注意事項見 `CLAUDE.md` 弱點 #23。

---

## Important（原始診斷，皆已用可執行證據確認）

### I-1 `common_errors` 排在答案鍵之前比對，會把正確答案判成錯

[dataset/tutor_driver.py:518](../dataset/tutor_driver.py#L518)

```python
for err in (step.get("common_errors") or []):
    e = _answer_normalize(str(err))
    if e and e in norm:
        return "incorrect"
```

`common_errors` 用的是**無長度下限的子字串**比對，且排在 `expected_answer` 之前。
只要生成的錯誤答案是正確答案的子字串，正確答案永遠先命中 `incorrect`。

實測（本次審閱）：

| `expected_answer` | `common_errors` | 學生輸入 | 判定 |
|---|---|---|---|
| `非負` | `["負"]` | `非負` | **incorrect** |
| `$x_2-x_1>0$` | `["0"]` | `$x_2-x_1>0$` | **incorrect** |

兩組 `common_errors` 都是 SEGMENTER 很可能真的生成的內容（「負」「0」正是這兩題
最典型的錯答）。下游行為：學生答對 → 判 incorrect → 留在同一步重講，最多兩輪後
被 `_MAX_WALK_RETRY` 揭示答案帶過。安全閥有效（不會死鎖），但學生會被告知
「剛才的回答還不是這一步要的答案」兩次，而他答的就是標準答案。

**修法**：`accepted_answers` 那裡已有的短答保護（`len(cand) <= 2 and len(norm) > 12`
就跳過）沒有套用到 `common_errors`；且順序應改成「先看是否命中答案鍵，
沒命中才查 common_errors」。註解裡寫的排序理由（先看錯誤答案）針對的是
「答案裡混了錯誤說法」，但目前的實作連完全相同的答案都會被攔下。

### I-2 重講輪的防重複比對，抓不到「逐字重講同一段 explain」

[dataset/tutor_driver.py:809](../dataset/tutor_driver.py#L809)

```python
prev = next((m["content"] for m in reversed(self.messages) if m["role"] == "assistant"), "")
if difflib.SequenceMatcher(None, _normalize(text), _normalize(prev)).ratio() >= 0.9:
    return None
```

`prev` 是**上一則完整的助教回覆**，也就是 `WALKTHROUGH_TEMPLATE` 組出來的
`第 i/n 步：{explain}\n\n確認問題：{check}`；而 `text` 只有 explain 本體（問句已被
系統剝掉）。兩者長度天生不對等，模板的前綴與確認問題直接稀釋掉相似度。

實測（本次審閱，用 96 字的真實步驟文字）：模型把 explain **逐字原樣吐回**時，
相似度 = **0.845 < 0.90 → 判定為「新說法」而被採用**。

也就是說，這道守衛正是為了擋 2026-08-07 守門 M1 中英兩場的「同一段原封不動再貼
一次」而加的，卻擋不住最乾淨的那個版本。這與弱點 #17 的第一批修復同型
（保底句稀釋相似度到 0.768 < 0.85 使 `repeat` 不觸發）——**同一個錯誤重犯了一次**。

**修法**：比對對象改成 `step["explain"]`（重講的基準本來就是它），或比對前先把
`prev` 裡的模板前綴與 `check` 剝掉。門檻 0.9 本身沒問題。

### I-3 `auto_reference._detect_lang` 沒跟上 `tutor_driver.detect_lang` 的強化

[dataset/auto_reference.py:428](../dataset/auto_reference.py#L428)

這批的核心修復之一，是把語言判定前的剝除從「只剝 `$…$` 與 `\command`」擴成
`_strip_language_neutral_math()`（另含 `\(…\)`、`\[…\]`、裸算式）。
`tutor_driver.detect_lang` 改了，`auto_reference._detect_lang` **維持舊寫法**：

```python
chars = [c for c in re.sub(r"\$[^$]*\$|\\[A-Za-z]+", " ", text or "") if not c.isspace()]
```

實測（本次審閱）兩者對同一段中文的判定不一致：

| 輸入 | `tutor_driver.detect_lang` | `auto_reference._detect_lang` |
|---|---|---|
| `故 \(\left\|\dfrac{3n-1}{n+2}-3\right\|=\dfrac{7}{n+2}<\varepsilon\) 成立。` | zh | **en** |
| `所以 f(x_2)-f(x_1)=f'(c)(x_2-x_1)>=0` | zh | **en** |

被誤判成 en 的兩個下游：
- `build_reference()` 寫出的 `teach_steps_lang`（[auto_reference.py:538](../dataset/auto_reference.py#L538)），
  `app.py` 會原樣存進題目、driver 拿它當 `src_lang`。
- `ensure_checkable_steps(steps)`（[auto_reference.py:529](../dataset/auto_reference.py#L529)）
  **沒帶 lang**，於是逐步驟自行判定——一個以算式為主的中文步驟很容易被判成 en，
  結果是中文講解配上 `What key relation does this step establish?` 的確認問題。

這正是這批要修的「混語」問題的另一面，只是發生在備課端而不是 driver 端。

**修法**：`auto_reference` 直接沿用 `tutor_driver._strip_language_neutral_math`
（或把它抽到共用模組），並在 `build_reference` 裡把語言算一次、往下傳
（現在 `fallback_steps(proof)`、`ensure_checkable_steps(steps)`、`_detect_lang(proof)`
是三個各自為政的判定）。

---

## Minor

| # | 位置 | 說明 |
|---|---|---|
| M-1 | [tutor_driver.py:1284-1295](../dataset/tutor_driver.py#L1284) | 新加的 `walk_feedback` 補句被插進「提示梯只在真的送出提示時才推進」那段註解與它所描述的 `if level == 2` 之間，註解與程式碼被拆開了。純可讀性，移到 `if level == 2` 之前或之後即可。 |
| M-2 | [tutor_driver.py:833](../dataset/tutor_driver.py#L833) | `expected_answer` 為空時 `WALK_ANSWER_HINT` 會輸出「這一步要的答案是：。」。`ensure_checkable_steps` 幾乎保證非空，但 `_fallback_expected` 理論上可回空字串，加一道 `if answer` 較穩。 |
| M-3 | [tutor_driver.py:31](../dataset/tutor_driver.py#L31) | `_DRAFT_RE` 的反向閘只列了「要需欲待所」：「我**想**證明：…」「我要 證明：…」（中間有空白）仍會被當成交草稿。教學期間有專用路由擋著，一般輪仍會誤判。 |
| M-4 | [tutor_driver.py:756-767](../dataset/tutor_driver.py#L756) | 英文 session 生成出來的步驟被寫回 `self.problem["teach_steps"]`（zh 鍵）；反向路徑（en session 取不到 `teach_steps_en` 而借用 zh 步驟）則會把中文步驟快取進 `teach_steps_en`。內建題目前都沒有 `teach_steps`，實務上不會咬到，但這個快取鍵的語意目前是錯的。 |
| M-5 | [auto_reference.py:529](../dataset/auto_reference.py#L529) | `validate_teach_steps` 驗收的是 SEGMENTER 的原始輸出，但真正送出去的是 `ensure_checkable_steps()` 補齊後的版本——補進去的 `check`／`expected_answer` 不受那五道閘檢查（長度、單一問句、重複）。目前補的是常數字串所以安全，日後若補值邏輯變複雜，驗收應改成對最終產物做。 |

---

## 做得好的部分（值得保留的判斷）

1. **教學輪改成完全確定性、不呼叫生成模型**——這是設計鐵律（「內容拿捏交給預寫內容」）
   的正確延伸。附帶效果是把該階段每輪最多 4 次的重生成降為 0，守門那段 45 → 12 分鐘，
   而等在螢幕前的正是最需要幫助的那個學生。以語氣固定換可預測性，取捨交代得很清楚。
2. **刻意偏離交接文件的兩處都有理由且都對**：不加第二個 LLM verifier（成本 300 秒
   ／它擋不掉的錯正是它最會誤判的地方）、加 `_MAX_WALK_RETRY=2`（答案鍵無人工審過，
   寫壞時不能讓學生永遠困在同一步）。I-1 的存在恰好證明了第二點的必要性。
3. **語言鎖定做了兩層**（`walk_lang` ＋ 以 `walk_presented_step` 而非
   `steps[walk_idx]` 評分）——只做前者，語言在教學中途被切換時仍會拿錯答案鍵。
4. **`_fallback_expected` 取最長關係式而非最後一個**，並在註解裡留下 A6/zh 的實測案例。
5. **探針一起改**（`regression_suite` 的 walkthrough 探針、`eval_svt_e2e` 的 `None` 台詞）
   ——「答對才前進」若不同步改探針，兩個硬性指標會從 1.0 掉到 0.5 而看起來像退步。
6. **`render_transcripts.py`**：把「人工讀對話」變成低成本可重複的動作，是這批
   真正抓到三個退化（逐字重講／答案鍵挑錯／推託你自己查）的工具。硬性指標當時全綠。

---

## 對守門的提醒

這批改動**會改變生成行為**，不像前幾批可以用「Tier 1/2 逐字 104/104 相同」證明零影響：
`PHASE_INSTRUCTIONS["review"]` 加了術語慣例、審閱無缺漏改確定性收尾。
`2026-08-07T093007_11ab1ae.json` 那輪是**修復前**的守門（103/104 相同，唯一差異已查明），
之後的三項修復（教學重講逐字重複／句級保底答案鍵／重講推託）只單獨重跑了 walkthrough 探針
（`regression_scores/2026-08-07_walkthrough_recheck.json`）。

**推送前仍需重跑一次完整守門**（GPU + agy，約 1.5hr）。
上述 I-1～I-3 若要修，一併修完再跑一次即可，不必分兩輪。
