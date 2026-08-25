# 備課管線自動生成 hint ladder — 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `auto_reference.py` 備課管線加入第五階段 LADDER，為已驗證的參考解自動生成 2 條分級提示，讓使用者自帶題目也能走完整的分級引導路徑；同時補上空梯路徑目前完全缺席的 Tier 0 測試覆蓋。

**Architecture:** 新增 `LADDER_SYSTEM` / `parse_ladder` / `validate_ladder` / `build_ladder` 四個單元，形狀完全照既有的 SEGMENTER 階段。五道確定性驗收（條數／長度／不帶新算式／不洩漏參考解／兩條不雷同）任一不過即整份丟棄回 `None`，題目就沒有 `hint_ladder` 欄位、行為等同今日。`tutor_driver.py` 零改動——`_ladder()` 早已會讀該欄位。

**Tech Stack:** Python 3.11（conda env `lora_project`）、Ollama `qwen3-4b-thinking-2507`（備課用思考型模型）、無測試框架（專案慣例是 `check(name, cond)` 平鋪腳本 + `sys.exit(1)`）。

## Global Constraints

- 語言：所有程式碼註解、docstring、測試名稱、commit message **一律繁體中文**（week3/CLAUDE.md 語言慣例）。
- 執行環境：`PYTHONNOUSERSITE=1`、`PYTHONUTF8=1`，Python 為 `D:\Danie\anaconda3\envs\lora_project\python.exe`。
- 測試慣例：**不使用 pytest**。新增斷言用既有的 `check(name, cond)`，區段以 `print("[N] 標題")` 開頭，插在檔尾 `print()` + `if FAIL:` 區塊**之前**。
- 現行基準：`test_driver_unit.py` = **215 條斷言 / 25 組**，全數通過。任何改動後這 215 條都必須維持通過。
  （⚠️ 計數方式：`grep -cE "^  (✓|✗) "`。不要用 `grep -c "✓\|✗"`——那會把結尾的
  「全部單元測試通過 ✓」也算進去，本計畫初版所有絕對數字因此都多了 1，已於 Task 3 修正。）
- 梯長固定 **2 條**：`validate_ladder` 只接受 2 條。手寫梯中有 2 題是 3 條（`hint_ladders.json` 的 17 題裡 15 題為 2 條），那 2 題是人工驗過的既有資產，**不受此驗收管轄、不修改**。
- 只生**繁體中文**梯（`hint_ladder`），不生 `hint_ladder_en`。⚠️ **實情修正**：`_ladder()`（`tutor_driver.py:583-584`）的回退是 `hint_ladder_en → hint_ladder`，也就是**回退到中文梯**，不是回退到英文通用句。因此「英文 session 由既有回退機制處理」的結果是：英文學生＋自動備課題目，會拿到「英文階段指示＋中文提示內容」的混語提示。這是已知取捨（混語在 4B 上實際傷害可控），不是回退到英文通用句。
- **不得留下任何對 `tutor_driver.py` 的修改**。唯一例外是 Task 1 Step 3 的靈敏度驗證——那是刻意改壞一行、確認測試會響、然後 `git checkout` 還原，Step 4 會驗證檔案已乾淨。若實作過程發現非**永久**改不可，停下來回報——那代表設計有誤。
- **不得修改 `_allowed_equation_src()` 的白名單邏輯**（ADV1 手寫提示刻意帶算式並依賴白名單放行）。

**設計 spec：** `docs/superpowers/specs/2026-08-05-hint-ladder-generation-design.md`

---

## 檔案結構

| 檔案 | 責任 | 本計畫的改動 |
|---|---|---|
| `dataset/auto_reference.py` | 備課管線（生成→驗證→修補→切分教學步驟）。237 行。 | 新增 LADDER 階段的 4 個單元 + 接進 `build_reference()` 與 `main()` |
| `dataset/app.py` | Gradio 介面。`assemble_problem` 把備課結果組成 driver 要的 problem dict。 | 一行 passthrough |
| `dataset/test_driver_unit.py` | driver 與 auto_reference 純函式的單元測試（無 GPU、不打 Ollama）。1197 行。 | 追加 `[26]` 空梯路徑、`[27]` LADDER 生成端 |
| `dataset/test_app.py` | app.py 純邏輯測試。 | 追加 `assemble_problem` 的 `hint_ladder` passthrough 斷言 |
| `dataset/tutor_driver.py` | **零改動** | — |

任務順序有意義：**Task 1 先鎖住現況行為**（空梯路徑的升級軌跡），之後的改動若意外影響 driver 會立刻響。Task 2→4 由內而外建生成端，Task 5 接線並驗收。

---

### Task 1: 空梯路徑的 Tier 0 測試（鎖住現況，不改產品碼）

補上目前**零覆蓋**的路徑：`test_driver_unit.py:355` 是用 `state["ladder_idx"] = 2` 手動模擬梯用盡，從未真的跑過 `hint_ladder` 不存在的題目——而 `app.py` 的每個使用者都走這條。

**Files:**
- Modify: `dataset/test_driver_unit.py`（插在檔尾 `print()` + `if FAIL:` 區塊之前）

**Interfaces:**
- Consumes: 既有的 `_StubDriver`（`test_driver_unit.py:83`）、`_StubModel`（`:75`）、`check()`（`:25`）
- Produces: `_CapturingStub`、`_run_stuck(ladder)` — Task 2–5 不依賴，僅本任務內用

- [ ] **Step 1: 寫失敗測試**

在 `test_driver_unit.py` 檔尾 `print()` / `if FAIL:` 區塊**之前**插入：

```python
print("[26] 空梯路徑：使用者自帶題目沒有 hint_ladder 時的升級軌跡")


class _CapturingStub(_StubDriver):
    """在「生成當下」擷取 system。

    ⚠️ 不可在 step() 回傳後才讀 _system()：ladder_idx 在該輪結尾才遞增
    （tutor_driver.py 的 level==2 分支），事後讀會看到遞增後的狀態，
    誤判「卡 2 注入的是提示二」。
    """
    captured: list

    def _generate(self, level):
        self.captured.append((level, self.state.get("phase"), self._system(level)))
        return super()._generate(level)


_LAD_PROB = {
    "id": "L1", "statement": "測試題：證明某序列收斂。",
    "reference_proof": "步驟甲。\n\n步驟乙。",
    "teach_steps": [{"explain": "教步驟甲", "check": "甲懂了嗎？"},
                    {"explain": "教步驟乙", "check": "乙懂了嗎？"}],
}
_STUCK_MSGS = ["我不知道，想不出來。", "還是不會。", "完全沒有頭緒。",
               "還是想不到，可以再提示一下嗎？"]


def _run_stuck(ladder):
    """連卡四輪，回傳跑完的 driver（captured 逐輪記錄 (等級, phase, system)）。"""
    prob = dict(_LAD_PROB)
    if ladder is not None:
        prob["hint_ladder"] = ladder
    d = _CapturingStub(tok=None, model=_StubModel(), problem=prob)
    d.generated_levels = []
    d.captured = []
    d.messages = [{"role": "user", "content": "題目…開始"}]
    for m in _STUCK_MSGS:
        d.step(m)
    return d


_nl = _run_stuck(None)                      # 無梯＝使用者自帶題目的現況
check("無梯：卡 1 → 等級 1", _nl.captured[0][0] == 1)
check("無梯：卡 2 → 等級 2 且注入的是通用保底句（非題目專屬提示）",
      _nl.captured[1][0] == 2 and "關鍵定理或想法名稱" in _nl.captured[1][2])
check("無梯：ladder_idx 仍推進到 1（該輪確實把提示送出去了）",
      _nl.state["ladder_idx"] == 1)
check("無梯：卡 3 → 進入逐步教學（max(梯長,1) 讓空梯不死鎖）",
      _nl.captured[2][1] == "walkthrough" and _nl.state["walk_active"])

_yl = _run_stuck(["提示一：關鍵是均值定理。", "提示二：導數有界給出 Lipschitz。"])
check("有梯：卡 2 → 注入 ladder[0]",
      _yl.captured[1][0] == 2 and "提示一" in _yl.captured[1][2])
check("有梯：卡 3 → 注入 ladder[1]",
      _yl.captured[2][0] == 2 and "提示二" in _yl.captured[2][2])
check("有梯：卡 4 → 提示梯用盡才進入逐步教學",
      _yl.captured[3][1] == "walkthrough")
check("空梯的實質退化：比有梯早一輪掉進逐步教學",
      _nl.captured[2][1] == "walkthrough" and _yl.captured[2][1] != "walkthrough")
```

- [ ] **Step 2: 執行確認測試通過**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3/dataset"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_driver_unit.py
```

預期：**全部通過**（223 條）。這一組是**行為快照**，測的是既有邏輯，本來就該過。

⚠️ 若有任何一條失敗，**不要改測試去迎合**——那代表你對現況的理解或 `_CapturingStub` 的擷取時機有誤。先把 `_nl.captured` / `_yl.captured` 印出來對照，確認擷取到的是生成當下的狀態。

- [ ] **Step 3: 驗證測試有靈敏度（還原一次 bug 確認會響）**

暫時把 `tutor_driver.py:1090` 的 `ladder_len = max(len(self._ladder()), 1)` 改成 `ladder_len = max(len(self._ladder()), 2)`，重跑測試。

預期：「無梯：卡 3 → 進入逐步教學」**失敗**（空梯要卡到第 4 次才進教學）。

確認會響之後 **`git checkout dataset/tutor_driver.py` 還原**。

> 這一步不可略過。`test_phase_routing.py` 的教訓：V4 不變式初版是空的、永遠不可能觸發，看起來全綠其實什麼都沒測。每條不變式都要實際還原一次 bug 驗證會響。

- [ ] **Step 4: 確認 tutor_driver.py 已還原**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3"
git status --short dataset/tutor_driver.py
```

預期：**無輸出**（檔案乾淨）。若有輸出代表 Step 3 的還原沒做完。

- [ ] **Step 5: 重跑測試 + 階段路由測試**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3/dataset"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_driver_unit.py
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_phase_routing.py
```

預期：兩支都全數通過。

- [ ] **Step 6: Commit**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3"
git add dataset/test_driver_unit.py
git commit -m "test: 補空梯路徑的升級軌跡覆蓋（Tier 0）

app.py 的使用者自帶題目一律沒有 hint_ladder，但這條路徑此前零自動測試
（既有測試是手動設 ladder_idx=2 模擬梯用盡，從未跑過梯不存在的題目）。

新增有梯／無梯對照：無梯在卡 2 注入通用保底句、卡 3 即進逐步教學；
有梯依序用完兩條提示、卡 4 才進。靈敏度已驗證（把 max(梯長,1) 改成
max(梯長,2) 會讓無梯那條失敗）。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `parse_ladder` — 模型輸出的結構解析

**Files:**
- Modify: `dataset/auto_reference.py`（新增函式，放在 `parse_steps` 之後、`segment_proof` 之前）
- Modify: `dataset/test_driver_unit.py`（新增 `[27]` 區段）

**Interfaces:**
- Consumes: 既有的 `_balanced_spans(content, open_ch, close_ch)`、`_loads_lenient(s)`
- Produces: `parse_ladder(content: str | None) -> list | None` — 成功時回**恰 2 個非空字串**的 list（已 strip），否則 `None`。Task 3 的 `validate_ladder` 與 Task 4 的 `build_ladder` 依賴此簽章。

- [ ] **Step 1: 寫失敗測試**

在 `test_driver_unit.py` 的 `[26]` 區段之後、檔尾 `print()` 區塊之前插入：

```python
print("[27] LADDER：提示梯自動生成的解析與驗收")
from auto_reference import parse_ladder  # noqa: E402

check("parse_ladder：正常 2 條 → 通過",
      parse_ladder('["先想想均值定理能給你什麼。", "再看導數有界推出什麼性質。"]')
      == ["先想想均值定理能給你什麼。", "再看導數有界推出什麼性質。"])
check("parse_ladder：3 條 → None（梯長固定 2）",
      parse_ladder('["提示一夠長的內容。", "提示二夠長的內容。", "提示三夠長的內容。"]') is None)
check("parse_ladder：1 條 → None", parse_ladder('["只有一條提示的內容。"]') is None)
check("parse_ladder：非字串元素 → None", parse_ladder('[{"a": 1}, {"b": 2}]') is None)
check("parse_ladder：空白字串元素 → None", parse_ladder('["有內容的提示。", "   "]') is None)
check("parse_ladder：垃圾輸出 → None", parse_ladder("我覺得可以先想想均值定理。") is None)
check("parse_ladder：思考鏈包夾仍可取出",
      parse_ladder('思考中…最後給出：["提示甲的內容夠長。", "提示乙的內容也夠長。"] 完畢')
      == ["提示甲的內容夠長。", "提示乙的內容也夠長。"])
check("parse_ladder：LaTeX escape 降級解析（\\{ 是非法 JSON escape）",
      parse_ladder(r'["用 \{x_n\} 的單調性想想看吧。", "再用有界性收束到結論。"]') is not None)
check("parse_ladder：None 輸入 → None", parse_ladder(None) is None)
```

- [ ] **Step 2: 執行確認測試失敗**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3/dataset"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_driver_unit.py
```

預期：**ImportError: cannot import name 'parse_ladder' from 'auto_reference'**（整支腳本中斷）。

- [ ] **Step 3: 最小實作**

在 `dataset/auto_reference.py` 的 `parse_steps` 函式之後、`segment_proof` 之前插入：

```python
def parse_ladder(content: str | None) -> list | None:
    """把模型輸出解析成恰 2 條非空提示；結構不合回 None。

    梯長固定 2（手寫 hint_ladders.json 的 17 題裡 15 題為 2 條，取眾數）。
    照 parse_steps 的作法：括號平衡取出候選 JSON 陣列，逐段寬鬆解析
    （LaTeX 的 \\{ \\dots 是非法 JSON escape，需反斜線加倍重試）。
    """
    if not content:
        return None
    for span in _balanced_spans(content, "[", "]"):
        arr = _loads_lenient(span)
        if (isinstance(arr, list) and len(arr) == 2
                and all(isinstance(s, str) and s.strip() for s in arr)):
            return [s.strip() for s in arr]
    return None
```

- [ ] **Step 4: 執行確認測試通過**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3/dataset"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_driver_unit.py
```

預期：全數通過（232 條）。

- [ ] **Step 5: Commit**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3"
git add dataset/auto_reference.py dataset/test_driver_unit.py
git commit -m "feat: auto_reference 新增 parse_ladder（提示梯結構解析）

照 parse_steps 的形狀：括號平衡取候選 JSON 陣列 + 反斜線加倍降級解析。
只接受恰 2 條非空字串（手寫梯 17 題中 15 題為 2 條，取眾數）。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `validate_ladder` — 五道確定性驗收

這是整個功能的安全核心。五道閘全部已對 `hint_ladders.json` 的 33 條手寫提示（人工驗過的黃金標準）校準，實測零誤判。

**Files:**
- Modify: `dataset/auto_reference.py`（新增 `import difflib` + `validate_ladder`）
- Modify: `dataset/test_driver_unit.py`（`[27]` 區段追加）

**Interfaces:**
- Consumes: `tutor_driver.gives_new_equation(reply, allowed_src) -> bool`、`tutor_driver.leaks_reference(reply, proof, n=15, exclude="") -> bool`（**lazy import 於函式內**，避免與 `tutor_driver._ensure_teach_steps()` 的反向 import 形成循環）
- Produces: `validate_ladder(hints: list, statement: str, proof: str) -> bool` — Task 4 的 `build_ladder` 依賴此簽章

- [ ] **Step 1: 寫失敗測試**

在 `[27]` 區段的 `parse_ladder` 斷言之後追加：

```python
from auto_reference import validate_ladder  # noqa: E402

# 驗收用的固定素材：參考解刻意寫成「無算式但有可洩漏的長句」，
# 才能把「洩漏」與「帶算式」兩道閘分開測（含 = 的句子會先被算式閘攔下）。
_VS = "設 $f$ 在 $[a,b]$ 上可微且 $|f'(x)| \\le M$，證明 $f$ 一致連續。"
_VP = ("由均值定理，存在介於兩點之間的 $c$ 使得函數差等於導數乘上距離。"
       "再由導數有界，可推出 Lipschitz 條件，於是取與位置無關的 δ 即完成證明。$\\blacksquare$")
_OK = ["這一步的關鍵是均值定理，它連起函數差與導數。",
       "導數有界會給出與位置無關的 δ 選取。"]

check("validate_ladder：合格的兩條 → 通過", validate_ladder(_OK, _VS, _VP))
check("validate_ladder：3 條 → 退",
      not validate_ladder(_OK + ["第三條提示的內容也夠長。"], _VS, _VP))
check("validate_ladder：非 list → 退", not validate_ladder("不是清單", _VS, _VP))
check("validate_ladder：過短（<12 字）→ 退",
      not validate_ladder(["太短了", _OK[1]], _VS, _VP))
check("validate_ladder：過長（>60 字）→ 退",
      not validate_ladder([_OK[0] + "而且我還要再補上非常非常非常非常非常非常多餘的冗長說明文字，硬是要拉得更長更長。",
                           _OK[1]], _VS, _VP))
check("validate_ladder：帶題目以外的新算式 → 退",
      not validate_ladder(["關鍵是均值定理，會得到 f(x)-f(y)=f'(c)(x-y)。", _OK[1]],
                          _VS, _VP))
check("validate_ladder：洩漏參考解長片段（15-gram）→ 退",
      not validate_ladder(["再由導數有界，可推出 Lipschitz 條件，於是取與位置無關的 δ。",
                           _OK[1]], _VS, _VP))
check("validate_ladder：兩條雷同 → 退",
      not validate_ladder([_OK[0], _OK[0] + "。"], _VS, _VP))

# 回歸鎖：手寫梯是人工驗過的黃金標準，被自己的驗收擋掉＝門檻訂錯。
_gold = [(pid, p) for pid, p in probs.items()
         if len(p.get("hint_ladder") or []) == 2 and p.get("reference_proof")]
_gold_fail = [pid for pid, p in _gold
              if not validate_ladder(p["hint_ladder"], p.get("statement", ""),
                                     p["reference_proof"])]
check(f"回歸鎖：{len(_gold)} 題手寫 2 條梯全部通過 validate_ladder（失敗：{_gold_fail}）",
      len(_gold) >= 14 and not _gold_fail)
```

> `probs` 是 `test_driver_unit.py:94` 已載入的 `load_problems_with_ladders()` 結果，直接沿用。
> 3 條梯的 2 題不在此鎖的管轄範圍（`len(...) == 2` 已濾掉）——它們是人工資產，
> 不受「生成的梯必須是 2 條」這條規則約束。

- [ ] **Step 2: 執行確認測試失敗**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3/dataset"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_driver_unit.py
```

預期：**ImportError: cannot import name 'validate_ladder' from 'auto_reference'**。

- [ ] **Step 3: 最小實作**

先在 `dataset/auto_reference.py` 的 import 區（`import argparse` 之後）加一行：

```python
import difflib
```

然後在 `parse_ladder` 之後插入：

```python
def validate_ladder(hints: list, statement: str, proof: str) -> bool:
    """提示梯的五道確定性驗收：條數／長度／不帶新算式／不洩漏參考解／兩條不雷同。

    門檻皆以 hint_ladders.json 的 33 條手寫提示（人工驗過的黃金標準）校準，實測零誤判。
    任一條不過即整份丟棄——寧可退回 driver 既有的通用保底句，
    也不冒「提示本身洩漏答案或給算式」的風險（生成的梯不像參考解有 VERIFIER 獨立審）。

    長度上限刻意比 prompt 要求的 15–45 字寬：prompt 訂目標、驗收訂紅線，
    只差一兩字不該整份丟棄。
    """
    # lazy import：tutor_driver._ensure_teach_steps() 會反向 import 本模組，
    # 模組層互 import 會形成循環。
    from tutor_driver import gives_new_equation, leaks_reference

    if not isinstance(hints, list) or len(hints) != 2:
        return False
    for h in hints:
        if not isinstance(h, str) or not (12 <= len(h.strip()) <= 60):
            return False
        if gives_new_equation(h, statement):      # 保護等級 2 禁算式白名單不被污染
            return False
        if leaks_reference(h, proof, exclude=statement):
            return False
    return difflib.SequenceMatcher(None, hints[0], hints[1]).ratio() < 0.85
```

- [ ] **Step 4: 執行確認測試通過**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3/dataset"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_driver_unit.py
```

預期：全數通過（241 條）。

⚠️ 若「回歸鎖」那條失敗，**不要放寬門檻了事**。先把 `_gold_fail` 裡的題目印出來，逐條看是哪一道閘擋的：

```bash
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" -c "
import sys; sys.path.insert(0, '.')
from auto_reference import validate_ladder
from tutor_driver import gives_new_equation, leaks_reference, load_problems_with_ladders
for pid, p in load_problems_with_ladders().items():
    lad = p.get('hint_ladder') or []
    if len(lad) != 2 or not p.get('reference_proof'):
        continue
    if validate_ladder(lad, p.get('statement',''), p['reference_proof']):
        continue
    for h in lad:
        print(pid, '長度', len(h), '算式', gives_new_equation(h, p.get('statement','')),
              '洩漏', leaks_reference(h, p['reference_proof'], exclude=p.get('statement','')),
              repr(h[:40]))
"
```

真的是門檻訂太緊才調整，並把調整理由寫進 commit message。

- [ ] **Step 5: Commit**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3"
git add dataset/auto_reference.py dataset/test_driver_unit.py
git commit -m "feat: auto_reference 新增 validate_ladder（提示梯五道確定性驗收）

條數／長度／不帶新算式（gives_new_equation）／不洩漏參考解（leaks_reference
15-gram）／兩條不雷同（difflib < 0.85）。五道閘全部對 33 條手寫提示校準，
零誤判；並加回歸鎖確保黃金標準不被自己的驗收擋掉。

不帶新算式那道特別重要：等級 2 的禁算式白名單包含當前提示文字
（_allowed_equation_src），提示若帶算式會讓該守衛對那些算式失效。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `build_ladder` + LADDER_SYSTEM + 接進備課管線

**Files:**
- Modify: `dataset/auto_reference.py`（新增 `LADDER_SYSTEM`、`build_ladder`；改 `build_reference()` 的 verified 分支與 `main()`）
- Modify: `dataset/test_driver_unit.py`（`[27]` 區段追加）

**Interfaces:**
- Consumes: `parse_ladder`（Task 2）、`validate_ladder`（Task 3）、既有的 `_chat(system, user, temperature, timeout=600)`
- Produces: `build_ladder(statement: str, proof: str) -> list | None`；`build_reference()` 的回傳 dict 在 verified 且驗收通過時**多一個 `"hint_ladder"` 鍵**（不通過時該鍵**不存在**，不是 `None`）。Task 5 的 `app.py` 依賴這個「鍵可能不存在」的約定。

- [ ] **Step 1: 寫失敗測試**

在 `[27]` 區段末尾追加：

```python
import auto_reference as _ar  # noqa: E402

_LADDER_JSON = ('["這一步的關鍵是均值定理，它連起函數差與導數。", '
                '"導數有界會給出與位置無關的 δ 選取。"]')
_orig_chat = _ar._chat
try:
    _ar._chat = lambda *a, **k: _LADDER_JSON
    check("build_ladder：模型輸出合格 → 回傳兩條", _ar.build_ladder(_VS, _VP) == _OK)

    _ar._chat = lambda *a, **k: '["太短", "也太短"]'
    check("build_ladder：驗收不過 → None（退回通用保底句）",
          _ar.build_ladder(_VS, _VP) is None)

    _ar._chat = lambda *a, **k: "我想想…均值定理應該可以。"
    check("build_ladder：輸出無法解析 → None", _ar.build_ladder(_VS, _VP) is None)

    _ar._chat = lambda *a, **k: None
    check("build_ladder：Ollama 離線 → None", _ar.build_ladder(_VS, _VP) is None)

    # 管線整合：LADDER 通過時 build_reference 的結果要帶 hint_ladder
    def _fake_chat(system, user, temperature, timeout=600):
        if system is _ar.PROVER_SYSTEM:
            return "由均值定理可得結論。$\\blacksquare$"
        if system is _ar.VERIFIER_SYSTEM:
            return '{"verdict": "pass", "issues": []}'
        if system is _ar.SEGMENTER_SYSTEM:
            return ('[{"explain": "先建立不等式", "check": "左邊是什麼？"}, '
                    '{"explain": "再取極限", "check": "極限是多少？"}]')
        if system is _ar.LADDER_SYSTEM:
            return _LADDER_JSON
        return None

    _ar._chat = _fake_chat
    _res = _ar.build_reference("測試題敘述", k=1, verbose=False)
    check("build_reference：verified 且 LADDER 通過 → 結果帶 hint_ladder",
          _res["status"] == "verified" and _res.get("hint_ladder") == _OK)
    check("build_reference：teach_steps 不受影響", len(_res["teach_steps"]) == 2)

    def _fake_chat_bad_ladder(system, user, temperature, timeout=600):
        if system is _ar.LADDER_SYSTEM:
            return '["太短", "也太短"]'
        return _fake_chat(system, user, temperature, timeout)

    _ar._chat = _fake_chat_bad_ladder
    _res2 = _ar.build_reference("測試題敘述", k=1, verbose=False)
    check("build_reference：LADDER 驗收不過 → 結果不含 hint_ladder 鍵（非 None）",
          _res2["status"] == "verified" and "hint_ladder" not in _res2)
finally:
    _ar._chat = _orig_chat
```

- [ ] **Step 2: 執行確認測試失敗**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3/dataset"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_driver_unit.py
```

預期：**AttributeError: module 'auto_reference' has no attribute 'build_ladder'**。

- [ ] **Step 3: 加 LADDER_SYSTEM 常數**

在 `dataset/auto_reference.py` 的 `SEGMENTER_SYSTEM` 之後插入：

```python
LADDER_SYSTEM = """你是數學教學設計者。下面給你一道證明題與它的參考證明，
請設計「分級提示」，供助教在學生連續卡住時逐條使用。

要求：
1. 恰好兩條，依序對應這份證明的兩個關鍵轉折：第一條給前半的關鍵，第二條給後半的關鍵。
2. 每條都要明確點出一個定理、構造或性質的「名稱與作用」——學生看到名稱後要能自己接手推導。
3. 絕對不可出現任何算式、等式或不等式。只講名稱與想法，計算全部留給學生。
4. 每條 15 到 45 字，繁體中文。
5. 不可直接抄參考證明裡的句子，要用自己的話重新講。

只輸出 JSON 陣列：["第一條提示", "第二條提示"]。不要輸出 JSON 以外的文字。"""
```

- [ ] **Step 4: 加 build_ladder**

在 `dataset/auto_reference.py` 的 `segment_proof` 之後、`fallback_steps` 之前插入：

```python
def build_ladder(statement: str, proof: str) -> list | None:
    """為已驗證的參考解生成分級提示梯（TutorDriver 等級 2 用）；失敗回 None。

    失敗即現況：呼叫端不寫 hint_ladder 欄位，_ladder() 回 []，
    driver 走既有的通用保底句路徑。不做確定性保底切分——
    從參考解機械切出來的片段當提示有洩漏風險，寧可退回通用句。
    """
    hints = parse_ladder(_chat(
        LADDER_SYSTEM, f"題目：{statement}\n\n參考證明：\n{proof}",
        temperature=0.2, timeout=300))
    if hints and validate_ladder(hints, statement, proof):
        return hints
    return None
```

- [ ] **Step 5: 接進 build_reference**

在 `dataset/auto_reference.py` 的 `build_reference()` 中，把這一段：

```python
            if verbose:
                print("  [SEGMENTER] 切分教學步驟…")
            _emit("SEGMENTER", "")
            steps = segment_proof(statement, proof) or fallback_steps(proof)
            return {"status": "verified", "reference_proof": proof,
                    "teach_steps": steps, "log": log}
```

替換為：

```python
            if verbose:
                print("  [SEGMENTER] 切分教學步驟…")
            _emit("SEGMENTER", "")
            steps = segment_proof(statement, proof) or fallback_steps(proof)
            if verbose:
                print("  [LADDER] 生成分級提示…")
            _emit("LADDER", "")
            hints = build_ladder(statement, proof)
            if verbose:
                print("  [LADDER] " + ("產出 2 條提示" if hints
                                        else "未通過驗收，改用通用提示"))
            out = {"status": "verified", "reference_proof": proof,
                   "teach_steps": steps, "log": log}
            if hints:                       # 驗收不過就不寫這個鍵（等同今日行為）
                out["hint_ladder"] = hints
            return out
```

- [ ] **Step 6: 接進 main()**

在 `dataset/auto_reference.py` 的 `main()` 中，把這一段：

```python
    if result["status"] == "verified":
        out["reference_proof"] = result["reference_proof"]
        out["teach_steps"] = result["teach_steps"]
        print(f"  參考解 {len(result['reference_proof'])} 字、教學步驟 {len(result['teach_steps'])} 步")
```

替換為：

```python
    if result["status"] == "verified":
        out["reference_proof"] = result["reference_proof"]
        out["teach_steps"] = result["teach_steps"]
        if result.get("hint_ladder"):
            out["hint_ladder"] = result["hint_ladder"]
        print(f"  參考解 {len(result['reference_proof'])} 字、"
              f"教學步驟 {len(result['teach_steps'])} 步、"
              f"分級提示 {len(result.get('hint_ladder') or [])} 條")
```

- [ ] **Step 7: 執行確認測試通過**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3/dataset"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_driver_unit.py
```

預期：全數通過（248 條）。

- [ ] **Step 8: Commit**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3"
git add dataset/auto_reference.py dataset/test_driver_unit.py
git commit -m "feat: 備課管線加入 LADDER 階段，自動生成分級提示梯

PROVER → VERIFIER → REPAIR → SEGMENTER → LADDER。prompt 規格由 33 條手寫
提示反推：恰兩條、依序對應證明的兩個關鍵轉折、每條點名一個定理/構造/性質的
名稱與作用、不得出現任何算式。

失敗即現況：生成或驗收不過就不寫 hint_ladder 鍵，driver 走既有通用保底句，
最壞情況零退步。不做確定性保底切分（從參考解機械切片段有洩漏風險）。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `app.py` passthrough + 端對端驗收

**Files:**
- Modify: `dataset/app.py:43-53`（`assemble_problem`）
- Modify: `dataset/test_app.py`（`[2]` 區段追加）

**Interfaces:**
- Consumes: `build_reference()` 的回傳 dict（Task 4），約定是 `"hint_ladder"` 鍵**可能不存在**
- Produces: `assemble_problem()` 回傳的 problem dict 在有梯時帶 `hint_ladder`，供 `TutorDriver._ladder()` 讀取

- [ ] **Step 1: 寫失敗測試**

在 `dataset/test_app.py` 的 `[2]` 區段中、`_unverified` 那組之前追加：

```python
_verified_lad = {"status": "verified", "reference_proof": "P $\\blacksquare$",
                 "teach_steps": [{"explain": "a", "check": "b"}],
                 "hint_ladder": ["這一步的關鍵是均值定理，它連起函數差與導數。",
                                 "導數有界會給出與位置無關的 δ 選取。"],
                 "log": []}
prob_l = app.assemble_problem("證明 Z", _verified_lad)
check("verified：hint_ladder 有傳遞給 driver", len(prob_l["hint_ladder"]) == 2)
check("verified：LADDER 未通過驗收時不帶 hint_ladder 鍵",
      "hint_ladder" not in prob_v)
```

- [ ] **Step 2: 執行確認測試失敗**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3/dataset"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_app.py
```

預期：`KeyError: 'hint_ladder'`（`assemble_problem` 沒有傳遞該欄位）。

- [ ] **Step 3: 最小實作**

在 `dataset/app.py` 的 `assemble_problem` 中，把：

```python
    if result["status"] == "verified":
        prob["reference_proof"] = result["reference_proof"]
        prob["teach_steps"] = result["teach_steps"]
    return prob
```

替換為：

```python
    if result["status"] == "verified":
        prob["reference_proof"] = result["reference_proof"]
        prob["teach_steps"] = result["teach_steps"]
        if result.get("hint_ladder"):      # LADDER 驗收不過時不存在，driver 走通用保底句
            prob["hint_ladder"] = result["hint_ladder"]
    return prob
```

- [ ] **Step 4: 執行確認測試通過**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3/dataset"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_app.py
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_driver_unit.py
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" test_phase_routing.py
```

預期：三支全數通過。

- [ ] **Step 5: Commit**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3"
git add dataset/app.py dataset/test_app.py
git commit -m "feat: app.py 把備課產出的 hint_ladder 傳給 driver

assemble_problem 多一個 passthrough。LADDER 驗收不過時該鍵不存在，
_ladder() 回 [] 走既有通用保底句路徑。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: 端對端人工驗收（需 Ollama 在線）**

先確認 Ollama 在線，再對 2 題實跑備課：

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3"
OUT="${TEMP:-/tmp}"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" \
  dataset/auto_reference.py --statement "證明：若數列 {a_n} 收斂，則它有界。" \
  --id E2E1 --out "$OUT/e2e1.json"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" \
  dataset/auto_reference.py --statement "證明：連續函數在閉區間上必有最大值。" \
  --id E2E2 --out "$OUT/e2e2.json"
```

產出檔寫在 repo 之外（暫存目錄），**不要 commit 進版控**。

每題約 10–20 分鐘（PROVER×3 各 2–4 分鐘 + VERIFIER + SEGMENTER + LADDER）。

人工檢視產出的 `hint_ladder`，逐項確認：

1. 兩條**依序**對應證明的前半與後半，不是同一件事講兩次
2. 每條都**點名了**一個定理／構造／性質（等級 2 的指示要求助教第一句說出這個名稱，沒有可點名的東西就履行不了）
3. 完全沒有算式
4. 不是抄參考解的句子

若某題產出 `分級提示 0 條`，看 log 判斷是哪一道閘擋的——那不算失敗（設計上就會退回通用句），但若兩題都是 0 條，代表 prompt 需要調整，回報後再議。

- [ ] **Step 7: 完整守門**

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" \
  dataset/regression_suite.py --quick
```

`--quick` 通過後跑完整守門（GPU + agy CLI，約 1.5 小時）：

```bash
# 跑之前先關 Antigravity IDE（它的背景進程會搶 6GB 卡導致 4-bit 載入 segfault）
taskkill /F /IM "Antigravity.exe"
taskkill /F /IM "Antigravity IDE.exe"
PYTHONNOUSERSITE=1 PYTHONUTF8=1 "/d/Danie/anaconda3/envs/lora_project/python.exe" \
  dataset/regression_suite.py
```

預期 exit 0。**判讀重點**：本批改動不碰 `tutor_driver.py`，內建題的生成行為在數學上不可能改變，所以應該逐字比對 `dataset/regression_scores/` 最新兩輪的 `*_replies.json`，預期 **104/104 相同**。若相同，所有 `judge_*` 的上下波動都是評審雜訊，不可解讀成本批改動的效果。

⚠️ 若在 walkthrough 探針處卡住（log 停在 `[E4/zh] 升級 ✓` 之後），這是 2026-08-04 兩次重現、**尚未解決**的已知問題。判斷方法是看 CPU 時間增量：40 秒內 <0.5 秒＝卡死，>5 秒＝還在算。確認卡死就 `Stop-Process -Force` 殺掉主進程釋放顯存，讓機器休息後再跑，不要立刻重試。若無法完成完整守門，以 `--quick` 通過 + Tier 0 全綠交付，並在回報中明確說明完整守門未跑完。

- [ ] **Step 8: 更新 CLAUDE.md 並 commit**

在 `week3/CLAUDE.md` 的「已知弱點」章節，於第 5 項之後插入新的一節記錄本次改動（節點放在「守衛鏈五項缺陷修復」那節之後），內容涵蓋：

- 缺口：備課管線只產 `reference_proof` + `teach_steps`，不產 `hint_ladder`；使用者自帶題目一律空梯
- 實測的退化：等級 2 退化成通用 meta 指示、提早一輪進 walkthrough（附有梯／無梯對照表）
- 修法：LADDER 階段 + 五道確定性驗收，失敗即現況
- 五道閘對 33 條手寫提示零誤判的校準數據
- 已知限制：驗收只保證安全性不保證品質；守門照不到這條路徑（Tier 1/2/3 全走內建題）
- 測試數：216 → 實際數字

同時把「常用指令」的測試數註記由 `186 條斷言 / 22 組` 更新為實際值。

```bash
cd "d:/UserData/claude_project/霓的資料/引導式數學專案/week3"
git add CLAUDE.md
git commit -m "docs: CLAUDE.md 記錄 LADDER 階段與空梯路徑的量測

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## 完成條件

- [ ] `test_driver_unit.py` 全數通過（215 → 約 248 條）
- [ ] `test_app.py`、`test_phase_routing.py` 全數通過
- [ ] 33 條手寫提示的回歸鎖通過
- [ ] Task 1 Step 3 的靈敏度驗證做過，且 `tutor_driver.py` 已還原乾淨
- [ ] 端對端 2 題人工檢視過生成的梯
- [ ] `regression_suite.py --quick` 通過；完整守門 exit 0（或明確說明未跑完的原因）
- [ ] `git status` 顯示 `tutor_driver.py` 未被修改
