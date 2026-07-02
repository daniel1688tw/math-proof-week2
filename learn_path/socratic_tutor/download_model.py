"""
download_model.py — 韌性下載 Qwen3-4B 權重，對抗本機網路「傳輸層」對大檔的中斷。

背景：這台筆電的網路（疑似 Pulse Secure VPN）會在傳輸層中斷 HF 檔案 CDN 的大型下載，
表現為「衝一波 1~2GB 後無錯誤地 hang 住」。這也是 simple_4B_ollama.py 改用 Ollama 的原因。

對策：
  * HF_HUB_DISABLE_XET=1  → 走純 HTTP resolve（cas-bridge，本機可通），而非 hf_xet 原生協定。
  * HF_HUB_DOWNLOAD_TIMEOUT 短 → 一旦資料流停滯就拋逾時例外，而不是永遠 hang。
  * 外層 retry 迴圈 → snapshot_download 會從 .incomplete 續傳，反覆重試直到全部抓完。

抓完後權重會快取在 HF 預設位置，train_qlora.py / test_4bit_load.py 直接用，不會重抓。

執行：
  conda run -n lora_project --live-stream python download_model.py
"""

from __future__ import annotations

import os
import sys
import time

os.environ["HF_HUB_DISABLE_XET"] = "1"            # 不用 hf_xet 原生協定
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "20")  # 20s 沒資料就視為停滯→重試

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from huggingface_hub import snapshot_download
from huggingface_hub.utils import HfHubHTTPError

from common import MODEL_NAME

MAX_ATTEMPTS = 200          # 大檔可能要很多次續傳
ALLOW = ["*.safetensors", "*.json", "*.txt", "tokenizer*", "*.model", "merges*", "vocab*"]


def main() -> None:
    print(f"韌性下載：{MODEL_NAME}")
    print(f"  HF_HUB_DOWNLOAD_TIMEOUT={os.environ['HF_HUB_DOWNLOAD_TIMEOUT']}s, 最多重試 {MAX_ATTEMPTS} 次")
    t0 = time.time()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            path = snapshot_download(
                MODEL_NAME,
                allow_patterns=ALLOW,
                max_workers=1,                 # 單線、降低被 VPN 中斷機率
                resume_download=True,
            )
            print(f"\n[完成] 全部權重已下載：{path}（耗時 {time.time()-t0:.0f}s，共 {attempt} 次嘗試）")
            return
        except (HfHubHTTPError, TimeoutError, OSError, Exception) as e:  # noqa: BLE001
            msg = str(e).splitlines()[0][:160] if str(e) else type(e).__name__
            print(f"  第 {attempt} 次中斷（{type(e).__name__}: {msg}）→ 5s 後續傳…", flush=True)
            time.sleep(5)
    print("[失敗] 超過重試上限仍未完成下載。")
    sys.exit(1)


if __name__ == "__main__":
    main()
