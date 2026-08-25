"""
download_chunked.py — 分塊 Range 下載 Qwen3-4B 權重，專剋本機 VPN 對長連線的節流。

為什麼需要這支：本機網路會把 HF 大檔的「單一長連線」節流到接近零（但不完全斷，
所以 snapshot_download 的逾時都被騙過、永遠 hang）。但「短連線爆發」是可以的。
本下載器因此把每個大檔切成許多 8MB 的獨立 Range 請求，各自短連線、各自逾時；
某塊卡住就只重抓那一塊，逐塊磨完整個 8GB。

每個請求都打 huggingface.co 的 resolve URL 並讓 requests 自動跟隨重導到 cas-bridge
（每次重發一個新的簽章 URL，連簽章過期都不用處理），並在重導中保留 Range header。

下載目標：本機資料夾 ./qwen3_4b/。common.py 偵測到此資料夾齊全後自動改用本機路徑。

執行（可重複跑，會從已下載位元組續傳）：
  conda run -n lora_project --live-stream python download_chunked.py
"""

from __future__ import annotations

import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests

REPO = "Qwen/Qwen3-4B-Instruct-2507"
BASE = f"https://huggingface.co/{REPO}/resolve/main/"
API = f"https://huggingface.co/api/models/{REPO}"
DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qwen3_4b")

CHUNK = 8 * 1024 * 1024     # 每塊 8MB
TIMEOUT = 25               # 單塊逾時（秒）；卡住就重抓該塊
PROGRESS_EVERY = 64 * 1024 * 1024

sess = requests.Session()


def list_files() -> list[str]:
    r = sess.get(API, timeout=30)
    r.raise_for_status()
    return [s["rfilename"] for s in r.json()["siblings"]]


def get_total(url: str):
    """回傳檔案總大小；若 HEAD 無 Content-Length（小檔 inline 服務）回 None。"""
    r = sess.head(url, allow_redirects=True, timeout=30)
    r.raise_for_status()
    cl = r.headers.get("Content-Length")
    return int(cl) if cl else None


def _download_whole(url: str, dest: str) -> None:
    """小檔/未知大小：整檔一次抓（短連線，沒問題）。"""
    for _ in range(10):
        try:
            r = sess.get(url, allow_redirects=True, timeout=120)
            r.raise_for_status()
            with open(dest, "wb") as f:
                f.write(r.content)
            return
        except Exception as e:  # noqa: BLE001
            print(f"    整檔重抓（{type(e).__name__}）", flush=True)
            time.sleep(1)
    raise RuntimeError(f"無法下載 {dest}")


def download_file(fname: str) -> None:
    url = BASE + fname
    dest = os.path.join(DEST, fname)
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    total = get_total(url)
    if total is None:
        print(f"  [get*] {fname}  (整檔)", flush=True)
        _download_whole(url, dest)
        print(f"  [done] {fname}", flush=True)
        return
    have = os.path.getsize(dest) if os.path.exists(dest) else 0
    if have >= total:
        print(f"  [skip] {fname}  已完整 ({total/1024**2:.1f} MB)")
        return

    print(f"  [get ] {fname}  {have/1024**2:.0f}/{total/1024**2:.0f} MB", flush=True)
    last_print = have
    with open(dest, "ab") as f:
        while have < total:
            end = min(have + CHUNK - 1, total - 1)
            try:
                r = sess.get(
                    url, headers={"Range": f"bytes={have}-{end}"},
                    allow_redirects=True, timeout=TIMEOUT,
                )
                r.raise_for_status()
                data = r.content
            except Exception as e:  # noqa: BLE001
                print(f"    塊 @{have/1024**2:.0f}MB 卡住（{type(e).__name__}）→ 重抓", flush=True)
                time.sleep(1)
                continue
            if not data:
                continue
            f.write(data)
            have += len(data)
            if have - last_print >= PROGRESS_EVERY or have >= total:
                print(f"    {fname}: {have/1024**2:.0f}/{total/1024**2:.0f} MB "
                      f"({100*have/total:.0f}%)", flush=True)
                last_print = have
    print(f"  [done] {fname}", flush=True)


def main() -> None:
    os.makedirs(DEST, exist_ok=True)
    files = list_files()
    files.sort(key=lambda n: (n.endswith(".safetensors"), n))  # 小檔先、大 safetensors 後
    print(f"目標：{REPO} → {DEST}")
    print(f"檔案數：{len(files)}（CHUNK={CHUNK//1024//1024}MB, TIMEOUT={TIMEOUT}s）\n")
    t0 = time.time()
    for fn in files:
        download_file(fn)
    print(f"\n[完成] 全部檔案已下載到 {DEST}（耗時 {time.time()-t0:.0f}s）")


if __name__ == "__main__":
    main()
