# -*- coding: utf-8 -*-
"""app.py — 蘇格拉底助教商品化介面（Gradio 本機單人 Demo）。

使用者貼上自己的題目（可含目前的證明嘗試），系統先自我驗證備課（auto_reference），
再由 TutorDriver 進行 grounded 引導；備課驗證失敗則走同學模式（誠實降級）。

啟動：
  conda run -n lora_project --live-stream python dataset/app.py
瀏覽器開 http://localhost:7860
"""
from __future__ import annotations

import os
import queue
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

os.environ.setdefault("PYTHONNOUSERSITE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("BITSANDBYTES_NOWELCOME", "1")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from auto_reference import build_reference  # noqa: E402
from tutor_driver import TutorDriver        # noqa: E402


# ── 純邏輯（可單元測試，不載模型、不連 Ollama）─────────────────────────────
def check_ollama(url: str | None = None, timeout: int = 3) -> bool:
    """偵測 Ollama 是否在線（備課功能依賴；離線時備課會降級為同學模式）。"""
    url = url or os.environ.get("OLLAMA_TAGS_URL", "http://localhost:11434/api/tags")
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except (urllib.error.URLError, OSError):
        return False


def assemble_problem(statement: str, result: dict, pid: str = "USER") -> dict:
    """把 build_reference 的結果組成 TutorDriver 需要的 problem dict。"""
    prob = {
        "id": pid,
        "statement": statement.strip(),
        "grounding": "auto_verified" if result["status"] == "verified" else "unverified",
    }
    if result["status"] == "verified":
        prob["reference_proof"] = result["reference_proof"]
        prob["teach_steps"] = result["teach_steps"]
    return prob


def opener_for(proof: str | None) -> str | None:
    """使用者貼的證明 → driver 的學生開場白；空則 None（driver 預設請求提示）。"""
    return (proof or "").strip() or None
