# 備課管線自動生成 hint ladder — 設計 spec

日期：2026-08-05　分支：`fix/driver-guard-hardening`

## 背景：現況的缺口

`TutorDriver` 的分級引導機制以 `hint_ladder` 為軸心：

- 學生連續卡住兩次 → 等級 2，`LEVEL_INSTRUCTIONS[2]` 注入 `ladder[ladder_idx]` 的內容，
  要求助教第一句明確說出提示裡的定理／技巧名稱。
- `ladder_idx` 記錄「下次要用第幾條提示」，且只在**提示真的送到學生面前**時推進
  （`level == 2 and phase is None and not peer`）。
- 進入逐步教學（walkthrough）的條件是 `ladder_idx >= len(ladder)`，即**提示梯用盡**。

問題在於：備課管線 `auto_reference.py` 的四個階段（PROVER → VERIFIER → REPAIR →
SEGMENTER）**只產出 `reference_proof` 與 `teach_steps`，不產出 `hint_ladder`**。
全 repo 的 `.py` 檔中 `hint_ladder` 只有「從 JSON 讀出」與「讀出後賦值」兩種用法，
沒有任何一處生成它。`hint_ladders.json`（17 題）是手寫的，只涵蓋內建題。

因此 `app.py` 的使用者自帶題目一律走空梯路徑。實測（`_StubDriver` 模擬連卡 5 輪）：

| 卡住次數 | 有梯（2 條，內建題） | 無梯（自帶題） |
|---|---|---|
| 1 | level 1 | level 1 |
| 2 | level 2，注入 `ladder[0]` | level 2，注入通用保底句 |
| 3 | level 2，注入 `ladder[1]` | **進 walkthrough** |
| 4 | **進 walkthrough** | — |

空梯不會死鎖（`ladder_len = max(len(ladder), 1)` 把空梯視為長度 1），但有兩個後果：

1. **等級 2 的透漏內容退化成一句通用 meta 指示**
   （`"點出此步驟所需的關鍵定理或想法名稱（不給算式）。"`），
   提示深度改由 4B 微調模型在 80 字回覆限制下當場即興拿捏——
   這正是設計鐵律要避免的「內容拿捏交給模型」。
2. **提早一輪掉進 walkthrough**。該被第二條提示救起來的學生直接被講答案，
   而 walkthrough 每輪最多 4 次重生成，延遲成本也提早付。

影響面是「連續卡住兩次以上的使用者自帶題」——觸發面窄，但打在最需要幫助的學生身上。

## 目標

在備課管線加入第五階段 LADDER，對已驗證的參考解自動生成 2 條分級提示，
並以確定性驗收把關安全性；驗收不過就整份丟棄，行為退回今日現況。

同時補上空梯路徑的 Tier 0 測試覆蓋——該路徑目前**零自動測試**
（`test_driver_unit.py:355` 是用 `state["ladder_idx"] = 2` 手動模擬梯用盡，
從未真的跑過 `hint_ladder` 不存在的題目）。

### 非目標

- 不為內建 17 題重新生成提示梯（已有人工驗過的手寫梯，不動）。
- 不做雙語備課（見「已定案的取捨」第 2 點）。
- 不改 `tutor_driver.py`。
- 不加 CRITIC 複核輪（見「方案取捨」）。

## 方案取捨

| 方案 | 說明 | 判定 |
|---|---|---|
| **A. LADDER 階段 ＋ 確定性驗收** | 備課時生成，五道確定性閘把關，不過就丟棄 | **採用** |
| B. A ＋ CRITIC 複核輪 | 再叫思考型模型審「這條提示是否等於給答案」 | 不採用：多 2–4 分鐘，判準本身有雜訊（`judge_backstop` 同型輸入實測 0.0/0.33/0.67），而確定性檢查在 33 條黃金標準上已零誤判 |
| C. 不生成，只補測試 | 成本最低 | 不採用：問題原封不動 |

方案 A 的關鍵性質是**失敗即現況**：驗收不過就不寫 `hint_ladder` 欄位，
`_ladder()` 回 `[]`，走今天既有的通用保底句路徑。不需要新的保底邏輯，
最壞情況零退步，也不引進新的失敗模式。這與 `unverified → 同學模式` 是同一種誠實降級。

### 生成時機：備課時一併生成（已定案）

備選是執行期 lazy（第一次進等級 2 才生成，照 `_ensure_teach_steps()` 模式）。
不採用的理由：Ollama 思考型每次呼叫 2–4 分鐘，卡住的學生要在最挫折的時刻乾等。
備課時生成則使用者本來就在看串流進度，多等一段可接受，代價是沒卡住的題目也付這個成本。

## 已定案的取捨（有依據，非預設值）

1. **梯長固定 2 條** — 手寫梯 17 題中 15 題為 2 條、2 題為 3 條。取眾數，驗收條件也單純。
2. **只生繁體中文梯** — 整條備課管線（PROVER/VERIFIER/REPAIR/SEGMENTER）本來就是中文單語，
   參考解本身也是中文。英文 session 時 `_ladder()` 已會回退中文梯
   （`self.problem.get("hint_ladder_en") or self.problem.get("hint_ladder") or []`），
   模型自行翻譯——這與「英文學生拿到中文參考解」是同一個既有性質，不為此擴充雙語備課。
3. **不動 `_allowed_equation_src()` 白名單** — 曾考慮把 `hint` 從等級 2 禁算式白名單移除
   當作更根本的防線，但 `adv_test_problem.json` 的 ADV1 手寫提示**刻意**帶算式
   （`f(x)g'(c)=g(x)f'(c)`）並依賴白名單放行，移除會打壞既有題目。
   改為「讓生成的梯保證無算式」，白名單原樣。

## 架構

### 生成端：`auto_reference.py`

新增四個單元，形狀照既有的 SEGMENTER：

```
LADDER_SYSTEM                                    # system prompt 常數
parse_ladder(content)              -> list[str] | None    # 結構解析
validate_ladder(hints, statement, proof) -> bool          # 五道確定性驗收
build_ladder(statement, proof)     -> list[str] | None    # _chat → parse → validate
```

**`LADDER_SYSTEM` 的內容規格**（從 33 條手寫提示反推）：手寫梯不是「同一提示的兩種深度」，
而是**對應證明的兩個關鍵轉折、依序給出**。例（H4）：

> 1. 這一步的關鍵是均值定理，它能把兩點的函數差和某一點的導數連起來。
> 2. 導數有界會給出 Lipschitz 性質，而 Lipschitz 的 δ 選取與位置無關。

因此 prompt 要求：恰兩條、依序對應證明的兩個關鍵轉折、每條**點名一個定理／構造／性質的
名稱與作用**（`LEVEL_INSTRUCTIONS[2]` 規定助教第一句必須說出提示裡的定理名，提示裡沒有
可點名的東西就無法履行）、**不得出現任何算式或等式**、每條 15–45 字、只輸出 JSON 陣列。

**`parse_ladder`** 照 `parse_steps` 的作法：`_balanced_spans(content, "[", "]")`
逐段 `_loads_lenient`（LaTeX 反斜線加倍重試），取第一個結構合格者。

**`validate_ladder` 的五道閘**（全部確定性，全部已對 33 條手寫提示校準）：

| 檢查 | 門檻 | 校準依據 |
|---|---|---|
| 恰 2 條非空字串 | `len(hints) == 2` | 手寫眾數 15/17 |
| 每條長度 | 12 ≤ len ≤ 60 字 | 手寫實測 16–46 字（平均 33）。刻意比 prompt 要求的 15–45 字寬：prompt 訂目標、驗收訂紅線，只差一兩字不該整份丟棄 |
| 不得帶新算式 | `gives_new_equation(h, statement)` 為 False | 33 條零誤判；語意正是「不得帶入題目以外的算式」，保護等級 2 禁算式白名單不被污染 |
| 不得洩漏參考解 | `leaks_reference(h, proof, exclude=statement)` 為 False | 33 條零誤判 |
| 兩條不得雷同 | `difflib.SequenceMatcher` 相似度 < 0.85 | 33 題零雷同；防退化成同一句 |

任一條不過 → `build_ladder` 回 `None`。

**匯入方向**：`validate_ladder` 內部 lazy import
`from tutor_driver import gives_new_equation, leaks_reference`，
與 `tutor_driver._ensure_teach_steps()` 反向 lazy import `auto_reference` 同一慣例，
避免循環匯入。

**接線**：`build_reference()` 的 verified 分支，SEGMENTER 之後：

```
_emit("LADDER", "")
hints = build_ladder(statement, proof)
out = {"status": "verified", "reference_proof": proof, "teach_steps": steps, "log": log}
if hints:
    out["hint_ladder"] = hints
```

`_chat` timeout 取 300 秒（同 `segment_proof`）。Ollama 離線或逾時 → `_chat` 回 `None`
→ `build_ladder` 回 `None` → 同一條降級路徑。`main()` 的 `--out` 一併寫出該欄位。

### 消費端

| 檔案 | 改動 |
|---|---|
| `app.py` `assemble_problem` | 一行：`if result.get("hint_ladder"): prob["hint_ladder"] = result["hint_ladder"]` |
| `tutor_driver.py` | **零改動**（`_ladder()` 早已會讀 `hint_ladder`） |
| `interactive_turn.py` | 零改動（走內建題庫，本來就有梯） |

`app.py` 的 `progress_cb` 是直接把 stage 字串丟進佇列（`f"{stage} {detail}".strip()`），
新階段會自動出現在備課串流進度裡，顯示邏輯不需修改。

## 資料流

```
使用者貼題目
   └─ build_reference()
        PROVER×3 → VERIFIER → (REPAIR) → SEGMENTER → LADDER   ← 新增
                                            │           │
                                       teach_steps   hint_ladder（或 None）
        └─ assemble_problem() → problem dict
             └─ TutorDriver
                  · 連卡 2 次 → 等級 2 → _ladder()[ladder_idx]
                       有梯 → 生成的提示；無梯 → 通用保底句（現況）
                  · ladder_idx >= len → walkthrough（用 teach_steps）
```

## 錯誤處理

| 情境 | 行為 |
|---|---|
| Ollama 離線／逾時 | `_chat` 回 `None` → 無 `hint_ladder` → 現況行為 |
| 模型輸出無法解析成 JSON 陣列 | `parse_ladder` 回 `None` → 同上 |
| 條數不對 / 長度不對 / 帶算式 / 洩漏 / 兩條雷同 | `validate_ladder` 回 False → 同上 |
| 題目 `unverified` | 根本不進 LADDER 階段（走同學模式，無參考解可依據） |

所有失敗路徑收斂到同一個結果：**題目沒有 `hint_ladder`，行為等於今日**。
不做確定性保底切分（不同於 `fallback_steps`）——從參考解機械切出來的片段當提示
有洩漏風險，寧可退回通用句。

## 測試策略

### A. 空梯路徑 Tier 0（補既有覆蓋缺口，無 GPU）

加進 `test_driver_unit.py`，用既有 `_StubDriver` 跑「連卡 5 輪」的有梯／無梯對照，
斷言上表的升級軌跡：無梯在卡 2 注入通用保底句、卡 3 進 walkthrough；
有梯在卡 2/3 依序注入 `ladder[0]`/`ladder[1]`、卡 4 才進 walkthrough。

⚠️ **實作要點**：斷言必須擷取**生成當下**的 system，不可在 `step()` 回傳後才讀
`_system(2)`——`ladder_idx` 在該輪結尾才遞增，事後讀會看到遞增後的狀態，
誤判「卡 2 注入的是提示二」。作法是覆寫 `_generate` 於呼叫當下存下 `self._system(level)`。
（本 spec 撰寫過程中首次寫探針即踩到此坑。）

### B. LADDER 生成端純函式（無 GPU、不連 Ollama）

同樣放 `test_driver_unit.py`——`auto_reference` 的解析函式
（`parse_verdict` / `parse_steps` / `fallback_steps`）已經在該檔測試，慣例一致。

- `parse_ladder`：正常 2 條通過；3 條／1 條／非字串／空字串 → `None`；LaTeX escape 降級解析
- `validate_ladder`：五道閘各一條反例（含算式、洩漏 15-gram、過長、過短、兩條雷同）
- **回歸鎖**：33 條手寫提示必須全數通過 `validate_ladder`。
  黃金標準被自己的驗收擋掉＝門檻訂錯，這條會立刻響。

### C. 端對端（需 Ollama，人工跑，不進自動測試）

`python dataset\auto_reference.py --statement "…" --out tmp.json` 實跑 2–3 題，
人工檢視生成的梯是否分級合理、是否真的點名了定理。有 Ollama 依賴與生成隨機性，
不做成硬性指標——定位同 `test_auto_reference.py`。

### 守門

改動不碰 `tutor_driver.py`，內建題的生成行為在數學上不可能改變。
推送前跑完整守門，並用 `regression_scores/*_replies.json` 與上輪逐字比對
（預期 104/104 相同）來證明對固定探針零影響。
若再撞到 walkthrough 探針卡死（2026-08-04 兩次重現、未解），
先以 `--quick` 過關，完整守門待機器狀況再補。

## 已知限制（必須誠實記錄）

1. **驗收只保證安全性，不保證品質。** 五道閘擋的是「洩漏／給算式／退化重複／格式錯」，
   擋不掉「提示講得爛但無害」。品質只能靠測試 C 人工抽查。
2. **守門照不到這條路徑。** Tier 1/2 是單輪探針、Tier 3 對話，全部走內建題（有手寫梯），
   這次改動在守門指標上是隱形的。驗證只能靠 Tier 0 斷言 ＋ 人工檢視。
3. **生成的梯未經人工審閱即用於教學。** 與 `reference_proof` 不同（那個有 VERIFIER 獨立審），
   提示只有確定性檢查。緩解：提示不含算式、不洩漏參考解，
   且等級 2 的既有守衛（禁算式、防奉送、洩漏 15-gram）在生成回覆時仍全數生效。
4. **證明者與提示生成者是同一個 4B 思考模型。** 沿用 `self_verified_teaching_design.md`
   已記錄的限制：獨立取樣非獨立模型，新領域建議先抽查。

## 驗收條件

- `test_driver_unit.py` 全數通過（186 條 → 預計 210 條上下）
- `test_phase_routing.py` 不受影響、全數通過
- 33 條手寫提示全部通過 `validate_ladder`（回歸鎖）
- 人工跑 2–3 題端對端，生成的梯符合「兩個關鍵轉折、點名定理、無算式」
- 完整守門 exit 0，且 Tier 1/2 回覆與上輪逐字比對相同
