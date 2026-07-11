"""
common.py — QLoRA 訓練引擎的共用設定（基底模型與路徑）。

train_qlora.py 與 test_4bit_load.py 從這裡讀設定；所有路徑都可用同名環境變數覆寫。
訓練資料與 system prompt 的實際內容由 week3/dataset/build.py 產生（grounded 格式，
含 <REFERENCE_PROOF>），推論端請用 week3/dataset/tutor_driver.py。
"""

from __future__ import annotations

import os

# ─────────────────────────────────────────────────────────────────────────────
# 基底模型
# ─────────────────────────────────────────────────────────────────────────────
# Qwen3-4B-Instruct-2507（Qwen3 架構需 transformers>=4.51）。
# 若本機 ./qwen3_4b/ 已有完整權重（config.json 存在）則優先使用，避免重複下載。
_REPO = "Qwen/Qwen3-4B-Instruct-2507"

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOCAL_MODEL_DIR = os.path.join(_HERE, "qwen3_4b")
if os.path.exists(os.path.join(_LOCAL_MODEL_DIR, "config.json")):
    MODEL_NAME = _LOCAL_MODEL_DIR
else:
    MODEL_NAME = _REPO

# ─────────────────────────────────────────────────────────────────────────────
# 路徑（皆可用同名環境變數覆寫）
# ─────────────────────────────────────────────────────────────────────────────
HERE = _HERE
# 預設指向 week3/dataset 的 grounded 資料集。
_DATASET_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "dataset"))
TRAIN_JSONL = os.environ.get("TRAIN_JSONL", os.path.join(_DATASET_DIR, "train.jsonl"))
VAL_JSONL = os.environ.get("VAL_JSONL", os.path.join(_DATASET_DIR, "val.jsonl"))
# 訓練輸出：預設寫到新目錄，避免覆蓋現行部署中的 qlora_adapter_v6
ADAPTER_DIR = os.environ.get("ADAPTER_DIR", os.path.join(_DATASET_DIR, "qlora_adapter_new"))
