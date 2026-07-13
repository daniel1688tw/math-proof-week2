# Socratic Calculus Proof Tutor — QLoRA 微調 + 對話驅動架構

把 **Qwen3-4B-Instruct** 微調成蘇格拉底式的大學微積分／數學分析證明助教：

- **不直接給答案**——每次只問一個聚焦問題，引導學生自己完成證明
- **分級提示**——學生連續卡住兩次，才透漏該步的關鍵定理或想法（不給算式）
- **寫證明與審閱**——學生走完關鍵步驟後，請他自己寫出完整證明，再對草稿做問題式審閱
- **抗壓**——被逼問答案時拒絕並把主導權還給學生；學生自信斷言錯誤時不附和

訓練資料**全部人工撰寫並驗證數學正確性**（50 道題目 + 400 條繁體中文多輪對話），
在單張 6GB VRAM 的筆電 GPU（RTX 4050）上即可完成訓練與推論。

> [!NOTE]
> 關於本專案的完整混合式設計框架、每個模組檔案的具體功用以及核心機制的詳細技術細節，請參閱專為開發者撰寫的：[**架構設計文件 (architecture_design.md)**](architecture_design.md)。

## 架構：模型只管數學與語氣，決策交給程式碼


```
學生訊息 → TutorDriver（確定性決策層）
             · stuck counter：連續卡住次數 → 提示等級 0/1/2
             · 階段偵測：交草稿→審閱 / 逼問→拒絕 / 嘗試→糾錯 / 說懂了→請寫證明
             · 等級 2 注入 hint_ladders.json 的人工預寫提示
             · 審閱/糾錯輪：審閱後盾（Ollama 思考型模型對照參考解找碴，
               缺漏清單注入 system；未裝 Ollama 自動降級，REVIEW_BACKSTOP=0 關閉）
           → QLoRA 微調模型（4-bit）+ grounded system prompt（內含該題參考解）
           → 後處理：單問句截斷、參考解洩漏 n-gram 檢查、on-track 防奉送
             （不替學生指定代數操作）、等級 2 禁算式、回問保底（命中即重生成）
```

核心設計原則（六輪迭代的教訓）：**離散決策交給程式碼、內容拿捏交給預寫內容、
模型只負責數學與語氣**。「透漏多少提示」這類連續量，純 SFT 校準不準；
把提示內容預先寫進 `hint_ladders.json`、由驅動程式決定何時注入，行為即完全受控。

混合架構延伸：審閱學生草稿需要的「即時數學判斷」超出 4B 微調模型的可靠範圍
（會出現「察覺對但解釋錯」與錯誤背書），故由思考型模型在幕後找碴、微調模型
只負責把缺漏清單包裝成引導問題（`review_backstop.py`，選配，需本機 Ollama +
`qwen3-4b-thinking-2507`；未安裝時自動降級回單模型行為）。

## 成效（8 道訓練集外題目 × 3 對抗情境，LLM-as-judge /5）

| 路線 | 首問 | 糾錯 | 逼問答案 | 總平均 |
|---|:---:|:---:|:---:|:---:|
| **本方法（微調 + driver + 審閱後盾）** | 4.31 | 4.50 | 4.31 | **4.37** |
| 微調 + driver（後盾離線時的降級形態） | 4.31 | 4.19 | 4.31 | 4.27 |
| 未微調基底 + 同樣 prompt | 3.88 | 4.06 | 3.00 | 3.65 |
| Ollama 思考型 + 同樣 prompt（無微調） | 3.63 | 4.75 | 3.63 | 4.00 |

微調的價值集中在互動壓力情境：被逼問時未微調模型只會政策式拒絕（零教學前進），
思考型模型甚至曾把完整證明整段交出；微調 + driver 則穩定做到「一句拒絕 + 一個引導問題」。
完整判定過程見 [dataset/eval_out_final/FINAL_VERDICT.md](dataset/eval_out_final/FINAL_VERDICT.md)。

## 專案結構與模組導覽

本專案主要包含以下模組與檔案（詳細設計請參考 [architecture_design.md](architecture_design.md)）：

*   **對話驅動層 (`dataset/`)**
    *   [tutor_driver.py](dataset/tutor_driver.py)：核心有狀態驅動程式，控制 stuck 狀態與階段判定，並施加 6 大推論端防護。
    *   [review_backstop.py](dataset/review_backstop.py)：後台審閱後盾，調用本地 Ollama 思考型模型進行草稿找碴。
    *   [interactive_turn.py](dataset/interactive_turn.py)：學生/開發者逐輪互動 CLI。
*   **資料集建置與驗證 (`dataset/`)**
    *   `src/` & `src_en/`：收錄人工手寫之 50 道大學微積分/數學分析題目與 400 條多輪對話。
    *   [build.py](dataset/build.py)：將手寫內容組裝成 grounded SFT 格式並切分 train/val 資料。
    *   [validate.py](dataset/validate.py)：嚴格的 SFT 資料集品質驗證器。
*   **QLoRA 微調訓練 (`learn_path/socratic_tutor/`)**
    *   [train_qlora.py](learn_path/socratic_tutor/train_qlora.py)：微調主程式，實作 Assistant-only loss masking 與左截斷保留視窗。
    *   [common.py](learn_path/socratic_tutor/common.py)：共用路徑設定檔。

## 快速開始


### 1. 環境（Python 3.11，CUDA 12.x，≥6GB VRAM）

```bash
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121
pip install "transformers==5.8.1" "accelerate==1.13.0" "peft==0.19.1" \
            "bitsandbytes==0.49.2" "datasets==4.8.5" "huggingface_hub==1.14.0"
```

> Windows 注意：transformers 5.x + bitsandbytes 載入 7B 模型會 segfault；本專案用 4B，實測安全。

### 2. 下載基底模型

```bash
huggingface-cli download Qwen/Qwen3-4B-Instruct-2507 --local-dir learn_path/socratic_tutor/qwen3_4b
```

### 3. 訓練（~1 小時 @ RTX 4050）

```bash
cd learn_path/socratic_tutor
MAX_LEN=640 EPOCHS=3 GRAD_ACCUM=8 EVAL_STEPS=20 OPTIM=adamw_8bit NEFTUNE_ALPHA=5 \
python train_qlora.py
# 產出 dataset/qlora_adapter_new/（訓練資料 dataset/train.jsonl 已內附，路徑均可用環境變數覆寫）
```

### 4. 測試

```bash
cd dataset
python test_driver_unit.py            # 驅動程式邏輯（無 GPU，51 項斷言）
python test_driver_integration.py     # 分級提示行為（GPU）
python test_driver_phase.py           # 階段管理行為（GPU）
python eval_final_driver.py           # 三情境完整評估
```

### 5. 互動使用

```bash
cd dataset
python interactive_turn.py --problem A2 --state session.json --reset      # 開場
python interactive_turn.py --problem A2 --state session.json --student "我把 |x²-4| 分解成 |x-2||x+2| 了"
```

或在自己的程式中：

```python
from tutor_driver import TutorDriver, load_problems_with_ladders
problems = load_problems_with_ladders()
driver = TutorDriver(tok, model, problems["A2"])
print(driver.start())                 # 助教第一問
print(driver.step("學生的回覆"))       # 逐輪推進
```

## 資料集

| 項目 | 數量 |
|---|---:|
| 題目（含手寫 LaTeX 參考解） | 50（極限/連續/微分/積分/級數 各 10）|
| 對話（360 train / 40 val） | 400 |
| 對話類型 | 核心引導（3 種學生人格）、犯錯變體、抗洩漏/抗附和、分級提示、節奏錯位、寫證明審閱 |
| 評估題（全部不在訓練集） | 8 held-out + 5 分布外難題 + 1 進階題（L'Hôpital 嚴格證明）|

修改 `dataset/src/` 後執行 `python build.py && python validate.py && python test_dataset.py` 重建。

## 開發歷史

本 repo 的工作目錄只保留最終方法。六輪迭代的完整歷史（MathDial 行為遷移、Ollama
無微調路線、adapter v2–v5 及其評估報告）保存在 git tag：

```bash
git checkout experiments-v2-v6
```

## 內容聲明

`dataset/src/` 的所有題目、參考解與對話由人工撰寫並驗證數學正確性，非模型生成。
基底模型 Qwen3-4B-Instruct-2507 遵循其原始授權（Apache 2.0）。
