# 2026-08-11：改用 stuck_count 控制引導深度

## 要解決的問題

原本的教學深度同時依賴題目外掛資料、索引與連續卡住次數，造成內建題／自訂題行為不一致，
而且特殊階段可能錯誤推進索引。這也讓逐步教學的真正觸發條件不容易理解與測試。

## 解決方式

1. 移除外掛提示資料、生成階段、索引欄位、讀取器與 app 傳遞邏輯。
2. 所有題目統一採 `stuck_count`：
   - 0：Level 0，單一聚焦問題。
   - 1：Level 1，拆成更小的子問題。
   - 2：Level 2，揭露經驗證步驟的定理／技巧／核心想法，不新增公式。
   - 3：切換到逐步教學。
3. 學生提出實質數學嘗試時，把 `stuck_count` 重設為 0。
4. review、rectify、refuse_leak、writeup_request、closed 等特殊階段優先，不消耗一般引導進度。
5. 自動備課的教學步驟新增 `core_idea`，並由結構檢查和獨立數學審閱共同驗證。
6. SEGMENTER 最多嘗試三次，以提高逐步教學資料的成功率。
7. 逐步教學每步只給一次作答機會；錯誤、不完整、答不出來或審閱不可用時，揭示參考答案並前進。
8. 逐步回答沿用 Review／Rectify 的思考型審閱後盾，不使用字串比對。

## Notebook 相容性

- `train.ipynb` 與 `test.ipynb` 預設專案根目錄改為
  `/content/drive/MyDrive/math-proof-week2-main (main的前一版) - 複製`。
- 兩份 notebook 仍允許用環境變數 `PROJECT_DIR` 覆寫路徑。
- `test.ipynb` 會在專案外層尋找 `gguf/`，因此外層資料夾名稱不同於內層 Python 專案也能運作。
- Notebook 及 CLI 改用只載入題目資料的 `load_problems()`。

## 驗證

- `dataset/test_driver_unit.py`：通過。
- `dataset/test_phase_routing.py`：通過。
- `dataset/test_app.py`：通過。
- Python 語法編譯與 notebook JSON 解析：需在同步前全部通過。

## 是否需要重新訓練

不需要。本次沒有變更 `train.jsonl`、`val.jsonl` 或既有 adapter 權重；修改位於推論時狀態機、
prompt、自動備課、測試與 notebook 路徑。只有未來改動 SFT 對話資料或希望訓練新 adapter 時，
才需要重新執行 `train.ipynb`。

---

# 2026-08-15：完整證明兩輪審閱與局部訂正佇列

## 要解決的問題

原本每一輪 review／rectify 都重新審查學生當輪文字，沒有保存可合併的證明草稿，也沒有
穩定的問題佇列。因此可能漏審、重複處理同一錯誤、一次談多項問題，或把學生重交的完整
證明誤當局部回答。只說「不知道」或只說定理名稱，也可能被一般 Tutor 誤認為完成訂正。

## 解決方式

1. 完整證明交由 `qwen3-4b-thinking-2507` 做兩輪獨立全文審閱；第一輪找出所有根本問題，
   第二輪專門補抓遺漏，再合併明顯重複的根本原因。
2. Driver 將全部問題保存為 `review_issues`，但每次只呈現 `review_issue_idx` 指向的一項。
3. 保存 `review_base_proof`、`current_proof_draft` 與已核准的 `review_corrections`；局部訂正
   以「取代原稿衝突敘述」的覆蓋層合併，問題全部處理後再做兩輪全文複核。
4. 每個局部回答先由 Thinking 模型語意審閱；接受精簡但等價的正確修法，拒絕空答、
   「不知道」、只說定理名稱、部分訂正及含矛盾的回答。只有 verdict=`correct` 才合併及前進。
5. 同一根本錯誤造成的後續錯式／錯結論由審閱 prompt 要求合併為一項，並在兩輪結果間
   做輕量根本原因去重。
6. 學生重交具完整證明結構的全文時，會清空舊局部覆蓋並重新做兩輪全文審閱。
7. 學生指出「漏審／重新檢查」時，自動重查最近保存的完整／合併草稿。
8. 工作草稿確認無誤後，要求學生提交不含訂正註記的乾淨完整證明，再做最後兩輪審閱。
9. Thinking 審閱暫時不可用時不會誤判通過，也不會丟失草稿或推進問題索引。

## Notebook 與驗證

- `train.ipynb`、`test.ipynb` 預設路徑同步為
  `/content/drive/MyDrive/math-proof-week2-main (main的前一版) - 複製 - 進行修改5`。
- `test.ipynb` 新增執行 `dataset/test_review_workflow.py`，並檢查 `review_backstop.py` 語法。
- `auto_gate.py` 與 `regression_suite.py` 的基礎測試也納入新審閱流程測試。

## 是否需要重新訓練

不需要。本次只修改推論時的審閱後盾、狀態機、測試與 notebook 路徑；沒有改動
`train.jsonl`、`val.jsonl` 或 adapter 權重。
