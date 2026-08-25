# v9-deployment 分支：與 `self-verified-teaching` 的差異

本分支（`v9-deployment`，接續自 `bon-verifier`）在 `self-verified-teaching`
的基礎上完成 **v9 部署升版**，並附帶伺服器訓練管線與一個判定「不採用」的驗證器實驗。
以下按「影響部署的核心變更」→「新增基建（不影響部署行為）」→「文件與評估產物」分層說明。

分支血緣：
```
self-verified-teaching  ──►  bon-verifier  ──►  v9-deployment
   (v8 部署基準)              (8B 實驗+守門基建+           (本分支＝v9 升版收束)
                              BoN 驗證器+v9 升版)
```

---

## 一、影響部署的核心變更（相對 self-verified-teaching）

### 1. 部署模型 v8 → **v9**（重訓，非資料變更）
- **訓練資料完全相同**（中英平行 800 例，`src/`＋`src_en/`），唯一差別是
  **序列長度 `MAX_LEN` 640 → 1024**。
- 動機：量測發現 `MAX_LEN=640` 會截掉 **26% 訓練樣本的尾端**（對話收尾／審閱輪），
  這正是弱點 #7「學生說懂了後助教仍多講一段」的**訓練面根因**。1024 達成零截斷。
- 訓練環境：實驗室 4090（bf16，`server_train/docker-compose.v9.yml`），12.5 分鐘、
  eval_loss 1.052；adapter 分塊拷回本機、SHA256 校驗一致。
- **部署預設 adapter 已從 `qlora_adapter_v8` 切到 `qlora_adapter_v9`**
  （各 runner 的 env 預設值；`qlora_adapter_v8/` 目錄保留，可用環境變數回退）。

### 2. `tutor_driver.py`：收尾偵測兩個確定性修復（根治弱點 #7）
self-verified-teaching 的 `_DONE_RE` 只能擋「追問型」延伸，擋不住「講解型」延伸。
本分支新增兩條確定性路由：
- **(a) 寫完證明 → review**：學生被請去寫證明後（`writeup_asked`），若送出長訊息
  （≥120 字）＝證明本體，路由到 `review`，**不再被 writeup 保底叫他重寫剛寫完的證明**。
- **(b) 完成後 → `closed` 新階段**：實質宣告證完時 arm `done_closed`；之後非質疑、
  非提問的反思輪走新增的 `closed` 階段，指示「溫暖收尾、禁新問題／替代法／延伸」。
- 新增 4 條單元測試（`test_driver_unit.py`），全數通過。
- 效果：`dialogue_guidance_en` 由五輪穩定 0.7333 回升、`dialogue_guidance_zh` 反超基準。
- **此修復同時惠及 v8**（driver 為共用層）。

### 3. `regression_suite.py`：`reveal_ok` 加入雜訊容忍
- `JUDGE_EPSILON_OVERRIDE` 新增 `"judge_reveal_ok": 0.08`，與既有的 `judge_s2_catch`
  同型（確定性 greedy 生成、Claude 評審、n≈13，單題翻面 = 0.077）。
- 依據：同一批 S2 文本五輪判分 0.833–0.942、**從未再現基準 1.0**，分母亦隨評審漏填
  reveal 鍵浮動 → 純評審雜訊；基準 1.0 是幸運高點（弱點 #6 教訓）。
- **保守作法：只加容忍、不降基準 1.0。** 仍能擋下 2 題以上的系統性洩漏退步。

### 守門結果（本機 4-bit，部署精度）
**25/25 全綠 → v9 上任。** 相對 v8 基準的實質提升：
| 指標 | v8 基準 | v9 |
|---|---|---|
| altmethod_en（弱點 #5 英文殘留） | 0.833 | **1.0** |
| s2_catch_en | 0.857 | 0.929 |
| score_en | 0.943 | 0.962 |
| s1_structural_en | 0.947 | 1.0 |
| dialogue_guidance_zh | 0.8 | 0.933 |

---

## 二、新增基建（不改變部署行為）

### 4. 伺服器訓練管線 `server_train/`（全新目錄）
- 一份 Docker image（`daniel-qlora-train`）＋多份 compose：`docker-compose.yml`（8B 訓練）、
  `docker-compose.v9.yml`（v9 4B 訓練）、`docker-compose.infer.yml`（bf16 推論）、
  `docker-compose.verified.yml`（BoN 驗證式服務）；程式碼以 volume 掛載、免重 build。
- `workspace/`：訓練腳本、資料副本（SHA 與本機一致）、推論服務、驗證器校準 harness。
- 遵守共用伺服器規範（`daniel-` 前綴、埠綁 127.0.0.1、資源上限、用完 `compose down`）。
- **跨 VPN 大檔傳輸對策**：SSH exec ＋伺服器端 curl（WireGuard 會重置 port-forward 大封包）、
  adapter 走 10MB 分塊＋逐塊重試＋SHA256 校驗。

### 5. BoN＋驗證器實驗 → **判定不採用**
- `inference_server_verified.py`＋`test_verifier.py`：生成器（4B-2507+adapter）與
  驗證器（4B-Thinking-2507）單張 4090 共存，選擇性驗證含式子的回覆。
- 校準後 v2 prompt 抓錯 3/4、誤殺 0/3；但**實戰 273 輪僅 1 輪真的抓錯重生成（0.4%）**——
  微調＋driver＋審閱後盾已把可驗證的數學錯誤壓到極低，驗證器邊際效益無法量測、
  卻多 8GB 顯存與延遲。判定 **VERIFY=0（＝現行部署行為）**，程式碼保留供未來換強驗證器。
- 詳見 `dataset/eval_out_xdomain/BON_VERIFIER_VERDICT.md`。

### 6. 守門基建（承自 bon-verifier 對 8B 實驗的合併）
- `--gen-only` / `--rejudge` 生成與評審分離、`incomplete`（exit 2）偵測、`auto_gate.py`
  外圈自動迭代——讓 Claude Pro 額度中斷可續評、不賠掉整輪。

### 7. `learn_path/socratic_tutor/common.py`
- 加入 `MODEL_NAME` 環境變數覆寫（伺服器端訓練不同基底模型用），**不影響本機預設行為**。

---

## 三、文件與評估產物
- `CLAUDE.md`：新增「v9 部署」「BoN＋驗證器」兩節，弱點 #5／#7 標記為已解決。
- `dataset/regression_scores/`：v9 各輪計分卡與對話存檔（含守門通過的
  `2026-07-18T192050_22c38a7.json`）。

---

## 四、若要回退到 self-verified-teaching 的行為
- **只回退模型**：設 `FINAL_ADAPTER=qlora_adapter_v8`（driver 修復仍生效，仍受益）。
- **完全回退**：checkout `self-verified-teaching`（v8 + 舊 driver + 無 server_train）。
- BoN 驗證器預設關閉（`VERIFY=0`），不影響部署。
