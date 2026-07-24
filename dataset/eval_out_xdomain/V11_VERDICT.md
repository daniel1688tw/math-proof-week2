# v11 判定（2026-07-24）：v11 判退（≈v10），#11 driver 修復乾淨可上線；Tier 3 對話守門待重校

## 背景

延續 v10 迭代方向，本輪同時做了兩件**可分離**的事：

1. **#11 driver 修復**（純確定性層，TDD）：擴充 `tutor_driver.py` 的 `closed` 收尾階段——
   學生在證明完成後提出「帶問句的反思」（好奇/範圍/非斷言質疑）時，路由進 `closed`
   並只簡短回答那一個問題、不藉機延伸；只有斷言式質疑（`_CHALLENGE_RE` 命中，如
   「你錯了」）才落回一般流程重新檢查。詳見 [tutor_driver.py](../tutor_driver.py) 第
   ~758 行 gate 與 `PHASE_INSTRUCTIONS[closed]` 中英指示；單元測試 `test_driver_unit.py`
   新增 7 條（好奇問句→closed、非斷言質疑→closed、斷言質疑→非closed、closed 新指示子句中英、
   英文平行）。**設計岔路 Fork B**（使用者定案）：完成後帶問句一律進 closed 簡答，
   只有斷言式質疑跳出；因已完成證明必經 review+後盾複核，非斷言「你確定嗎」由 closed 簡答即可。

2. **v11 adapter**：用 v10 的 830 例資料集（含 `dialogues_journey.py`）在 4090（192.168.1.222
   GPU0）重訓，超參同 v9/v10（4B-2507、MAX_LEN=1024）。假設：讓 v10 守門掛掉的 H5
   「完成後未經請求延伸」現已被 #11 driver 的 closed 階段兜住，這回可能過關。
   - 13 分鐘完成，eval_loss **1.044**（≈v10 1.042、優於 v9 1.052）。雙語煙霧測試通過。
   - adapter 6/6 檔分塊拷回、逐檔 SHA256 與遠端完全一致（這次零損毀）。

## 守門結果（Antigravity / Gemini 3.6 Flash Medium 學生＋評審，對 `regression_baseline_antigravity.json`）

跑了三次獨立評審：v11+driver 完整、v9+driver 完整、v9+driver rejudge（同文字重評）。

### 確定性層：#11 零退步（決定性證據）
三輪守門，所有確定性指標維持基準：`s1_structural`／`s3_refusal`／`escalation`／
`walkthrough`／`single_question`（中英）在 v9+driver 皆 1.0。單元測試 123/123。
**#11 driver 修復不造成任何確定性回歸。**（v11 那輪 `s1_structural_zh` 掉到 0.9474
是 X4/zh 開場「先寫出要證的線性組合等式」被判奉送——**v11 模型行為**，非 driver。）

### 單輪評審層（Tier 2，n≈13）：穩定通過
`judge_math_ok`／`judge_score`／`judge_reveal_ok`／`judge_altmethod` 通過或改善。
唯一「退步」`judge_s2_catch_zh` 0.7692 一經 rejudge 即回到基準 0.8571 = 評審雜訊。

### 多輪對話層（Tier 3，n=3）：雜訊主導，兩配置皆「退步」

| 計分卡 | 配置 | dmo_zh | dmo_en | dg_zh | dg_en |
|---|---|:---:|:---:|:---:|:---:|
| 基準 | v9（min of 2 runs） | 0.6667 | 0.6667 | 0.6 | 0.7333 |
| 004814 | v11+driver | **1.0** | 0.6667 | 0.8667 | 0.5333 |
| 015412 | v9+driver | **0.0** | **0.0** | 0.5333 | 0.5333 |
| 021354 | v9+driver **rejudge（同文字）** | 0.0 | **0.3333** | 0.5333 | 0.6 |

（dmo=dialogue_math_ok，dg=dialogue_guidance）

**關鍵事實**：
- `dialogue_math_ok_zh` 在 v11 抽到 **1.0**、在 v9（更穩定的部署模型）抽到 **0.0**——
  同指標相鄰兩輪暴擺全幅。
- **連 v9 部署模型都會被自己的基準判退**（基準 0.6667，v9 這輪新對話抽到 0.0）。
- 015412 與 021354 是**同一批對話文字、只換一次評審**：`dialogue_math_ok_en`
  從 0.0 跳到 0.3333、`s2_catch_zh` 從退步變通過——**光評審變異就 ≥0.33**。

## 判定

### v11 → 判退，維持部署 v9（與 v10 同命）
- v11≈v10，**重現 v10 的收尾過度延伸**：H5/en 逐輪可見助教在學生證完後主動延伸 6 輪、
  把學生拖進 x<0 推廣（transcript 見 004814_dialogues.json）；X4 有模型級數學錯誤
  （誤稱單位矩陣為反例、重根特徵向量獨立性錯誤），driver 蓋不住。
- **#11 修復為何沒接住 H5**：根因是「對話中途自然證完、助教自己確認完成」時
  `done_closed` 從未 arm（`_CLAIM_DONE_RE` 只認學生明確宣告如 QED，不認
  「which proves e^x>1+x」）；#11 修的是「done_closed 已 arm 後、帶問句反思」，
  這條路徑根本沒觸發。這是**真實但獨立的 driver 缺口**（見下方「下輪方向」）。

### #11 driver 修復 → 乾淨，建議上線於 v9
- 確定性零退步、單輪評審通過、且**不惡化對話層**（v9 與 v11 對話同樣受雜訊影響，
  #11 無關）。zh 對話在 v11 那輪反而大幅改善（dmo_zh 1.0、dg_zh 0.8667）。
- 本修復不需要 v11——它跑在既有 v9 adapter 之上即生效。

### Tier 3 對話守門 → 基準建在幸運高點，需方法層修正（治理決定，待授權）
- `dialogue_math_ok` 是**二元×3、每翻一場 0.333**，且光評審變異 ≥0.33（實測同文字
  0.0↔0.333）、加上學生路徑變異達全幅（0.0↔1.0）。**沒有任何 ε 能同時容忍此雜訊
  又抓得到真退步**；現行 `judge_dialogue` ε=0.07 是為 5 分制 guidance 設計的、對
  二元 math_ok 無效。
- 基準 note 稱「min of two v9 runs（conservative floor）」，但第三次 v9 抽樣即跌到 0.0
  ——兩輪取樣不足以覆蓋 n=3 的真實範圍。這正是 CLAUDE.md 弱點 #7
  「輸入隨機的指標基準不可棘輪到幸運最大值」的老問題，尚未套用到對話類指標。
- **不擅自改**：降基準違反「只升不降」、放大 ε 會掩蓋真實對話瑕疵，兩者皆屬治理決定，
  留給人工定奪。可選方向：(a) 對話改多輪聚合（中位數/多次 rejudge 平均）再對基準；
  (b) `dialogue_math_ok` 降為 advisory（保留計算與質性審閱、不進硬性 pass/fail），
  guidance 保留但 ε 依實測放寬；(c) 維持現狀，接受 Tier 3 在 n=3 下只能質性判讀。

## 下輪方向（driver 缺口 #12）
擴充完成偵測：當**助教自己的回覆確認證明完成**（如「Completely correct / 完全正確 /
the proof is complete」）時 arm `done_closed`，使後續反思輪走 closed；或放寬學生完成
偵測涵蓋「which proves <目標式>」式宣告，以在 turn 6 就攔下初次過度延伸。此缺口敏感
（易誤判 mid-proof），需 TDD 謹慎設計，未在本輪無人監督時貿然改動。

## 現場狀態
- 遠端 4090 容器已 `docker compose down`、GPU0 已釋放；本機無殘留進程、Ollama 無駐留。
- v11 adapter 保留於 `dataset/qlora_adapter_v11/`（本機、gitignore）供分析；830 例資料集
  與 journey 對話仍在 `training-iter-v10` 分支。
- 計分卡進 git 留證。**未 push、未切換部署預設、未動基準**。

---

## 追加（2026-07-24）：#12 driver 修復 + advisory + 第三輪守門 → 守門校準問題確立

### #12 driver 修復（弱點 #12，TDD）
- 新增 `_TUTOR_DONE_RE`：對話中途自然證完、**助教親口確認整個證明完成**時 arm
  `done_closed`（原本只從學生 `_CLAIM_DONE_RE` 宣告 arm，接不住此路徑）。後續反思輪
  即走 closed（接上 #11），收斂 H5 型過度延伸。措辭限「整個證明完成」等級避免 mid-proof
  誤判；新增 5 條單元測試（含負面「只肯定某步不誤 arm」），全套 128/128 通過。

### `dialogue_math_ok` 降為 advisory
- `regression_suite.py` 新增 `ADVISORY_METRICS`：計算＋印出但不進硬性 pass/fail。
  依據：二元×n=3，同一批文字光評審變異 ≥0.33、跨路徑全幅 0.0↔1.0，無 ε 可用（見上）。

### 第三輪守門（v9 + #11 + #12，計分卡 2026-07-24T123309）
- **確定性 + 單輪指標全過或改善**；**#12 讓 `dialogue_guidance_zh` 0.5333→0.6 回到基準**；
  `dialogue_math_ok` 正確標為 `[advisory]` 不擋門。
- 仍「退步」兩項，皆為**輸入隨機雜訊指標、與 #11/#12 無關**：
  - `judge_altmethod_zh` 1.0→0.8：S4 替代證法（Gemini 即興），基準 1.0 是幸運高點——
    專案早對 **en 版設 0.8333「容一案」**卻漏設 zh。
  - `judge_dialogue_guidance_en` 0.7333→0.5333：**本輪 en 對話低分源於 v9 中途數學錯誤**
    （H5 錯誤建議對 e^t 再用 MVT、M2 奇偶函數混淆），**證明未完成、closed 不觸發、與
    #11/#12 無涉**。三次 v9 量測皆 0.53–0.6，從未接近基準 0.7333 = 基準本身幸運高點。

### 結論：守門校準問題（非程式回歸）
三輪守門的確定性與單輪指標**全數穩定通過**；每輪的「退步」都落在不同的輸入隨機
雜訊指標（dialogue / altmethod / s2_catch），因 Gemini 學生每輪把 v9 帶進不同對話、
surfacing 不同既有小瑕疵。這是 CLAUDE.md 弱點 #7「輸入隨機指標基準不可棘輪到幸運
最大值」的老問題，尚未套用到 dialogue_guidance / altmethod_zh。**#11+#12 driver 修復
本身乾淨、可上線。**

### 最終守門校準（2026-07-24，已實施並經人工授權）

第四輪（獨立確認）守門再證：`judge_altmethod_zh` 回升 1.0（確認降 0.8333 是對的、原
1.0 為雜訊）；但 `dialogue_guidance` **這輪換 zh 掉（0.6→0.4667）、en 反而過**——與上輪
恰相反，證實 **guidance 兩語言皆 n=3 全幅雜訊（四輪 0.4667↔0.8667）、任何固定門檻擋不住**。

最終決策（人工授權「降 advisory」）：
1. **gate 重校**：`judge_altmethod_zh` 1.0 → **0.8333**（與 en 既有「容一案」一致，補漏）。
2. **`judge_dialogue_*` 全降 advisory**（math_ok 與 guidance、zh+en）：`ADVISORY_METRICS =
   ("judge_dialogue",)`，計算＋印出但不進 pass/fail；dialogue 基準值還原原始、僅供顯示。
   對話數學正確性由 Tier 4 後盾把關，引導品質改由質性審閱。
3. **硬性守門 = 確定性 + 單輪評審（n≈13 穩定）+ altmethod（含 ε）+ 後盾**——四輪全數穩定通過。

確定性重比對確認：此設定下第四輪守門（計分卡 135954）**硬性守門全綠 PASS**。

### 淨結果
- **#11 + #12 driver 修復乾淨、可上線**（部署形態 = v9 + 新 driver）。
- 守門改為只在「能可靠量測」的層面棘輪；n=3 對話類降 advisory，避免正常跑分被雜訊誤殺。
- v11 adapter 判退封存（≈v10）；下輪 driver 缺口與對話守門方法（多輪聚合）見上文與「下輪方向」。
