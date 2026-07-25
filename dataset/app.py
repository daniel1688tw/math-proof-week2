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


# ── 備課背景執行緒 + 佇列串流（供 UI 逐步顯示階段）─────────────────────────
def _run_prepare(statement: str):
    """generator：逐步 yield ('progress', 字串)，最後 yield ('result', dict) 或 ('error', 訊息)。

    worker 以 try/finally 保證一定送出結束哨兵，備課意外拋例外也不會讓 UI 永久卡死。
    """
    q: "queue.Queue" = queue.Queue()
    holder: dict = {}

    def worker():
        try:
            def cb(stage: str, detail: str = ""):
                q.put(("progress", f"{stage} {detail}".strip()))
            holder["result"] = build_reference(statement, progress_cb=cb)
        except Exception as e:                       # 備課非預期錯誤 → 回報而非卡死
            holder["error"] = repr(e)
        finally:
            q.put(("__done__", None))

    threading.Thread(target=worker, daemon=True).start()
    while True:
        kind, payload = q.get()
        if kind == "__done__":
            break
        yield kind, payload
    if "error" in holder:
        yield "error", holder["error"]
    else:
        yield "result", holder["result"]


# ── Gradio UI ──────────────────────────────────────────────────────────────
def build_ui(tok, model):
    import gradio as gr

    ollama_warn = "" if check_ollama() else \
        "⚠️ 未偵測到 Ollama 服務：備課需要 Ollama，目前所有題目會走同學模式。\n"

    with gr.Blocks(title="蘇格拉底數學證明助教") as demo:
        gr.Markdown("# 蘇格拉底數學證明助教\n"
                    "貼上你的證明題，助教會先自己備課再一步步引導你（不直接給答案）。")
        if ollama_warn:
            gr.Markdown(ollama_warn)

        driver_state = gr.State(None)

        with gr.Group() as input_group:
            statement_tb = gr.Textbox(label="題目敘述（必填）", lines=4,
                                      placeholder="例：證明連續函數在閉區間上有界。")
            proof_tb = gr.Textbox(label="你目前的證明／嘗試（可留空）", lines=6,
                                  placeholder="沒有頭緒可留空，助教會從第一個提示開始引導。")
            prepare_btn = gr.Button("開始備課", variant="primary")

        progress_md = gr.Markdown("")

        with gr.Group(visible=False) as chat_group:
            chatbot = gr.Chatbot(label="對話", height=460)
            with gr.Row():
                msg_tb = gr.Textbox(label="你的回覆", scale=5, lines=2)
                send_btn = gr.Button("送出", scale=1, variant="primary")
            reset_btn = gr.Button("重新開始（換一題）")

        def on_prepare(statement, proof):
            if not (statement or "").strip():
                yield (gr.update(value="請先輸入題目。"),
                       gr.update(visible=True), gr.update(visible=False), [], None)
                return
            lines = []
            result = None
            for kind, payload in _run_prepare(statement):
                if kind == "progress":
                    lines.append("• " + payload)
                    yield ("\n".join(lines), gr.update(visible=True),
                           gr.update(visible=False), [], None)
                elif kind == "error":
                    lines.append(f"⚠️ 備課發生非預期錯誤：{payload}\n請稍後再試或換一題。")
                    yield ("\n".join(lines), gr.update(visible=True),
                           gr.update(visible=False), [], None)
                    return
                elif kind == "result":
                    result = payload
            problem = assemble_problem(statement, result)
            driver = TutorDriver(tok, model, problem)
            reply = driver.start(opener=opener_for(proof))
            if result["status"] == "verified":
                lines.append("✅ 備課完成（grounded），開始引導。")
            else:
                lines.append("⚠️ 這題我沒能自己驗證出可靠解，將以同儕身分陪你探索（同學模式）。")
            first_user = opener_for(proof) or "（請助教給第一個提示）"
            chat = [{"role": "user", "content": first_user},
                    {"role": "assistant", "content": reply}]
            yield ("\n".join(lines), gr.update(visible=False),
                   gr.update(visible=True), chat, driver)

        def on_send(message, chat, driver):
            if driver is None or not (message or "").strip():
                yield "", chat
                return
            # 先即時回顯學生訊息並清空輸入框；生成期間 Chatbot 顯示等待指示
            chat = chat + [{"role": "user", "content": message}]
            yield "", chat
            try:
                reply = driver.step(message)
            except Exception as e:
                reply = f"（抱歉，這一輪出了點狀況：{e!r}，請再說一次。）"
            chat = chat + [{"role": "assistant", "content": reply}]
            yield "", chat

        def on_reset():
            return (gr.update(visible=True), gr.update(visible=False),
                    "", [], None, "", "")

        # 進行中操作期間停用對應按鈕，避免單 GPU 序列化佇列被重複點擊塞爆
        _disable = lambda: gr.update(interactive=False)   # noqa: E731
        _enable = lambda: gr.update(interactive=True)     # noqa: E731

        prepare_btn.click(_disable, None, prepare_btn).then(
            on_prepare, [statement_tb, proof_tb],
            [progress_md, input_group, chat_group, chatbot, driver_state]).then(
            _enable, None, prepare_btn)

        send_btn.click(_disable, None, send_btn).then(
            on_send, [msg_tb, chatbot, driver_state], [msg_tb, chatbot]).then(
            _enable, None, send_btn)
        msg_tb.submit(_disable, None, send_btn).then(
            on_send, [msg_tb, chatbot, driver_state], [msg_tb, chatbot]).then(
            _enable, None, send_btn)
        reset_btn.click(
            on_reset, None,
            [input_group, chat_group, progress_md, chatbot, driver_state,
             statement_tb, proof_tb])

    demo.queue(default_concurrency_limit=1)
    return demo


def main():
    from interactive_turn import load_model
    print("[app] 載入模型中（首次約需 30–60 秒）…", flush=True)
    tok, model = load_model()
    print("[app] 模型就緒，啟動介面 http://localhost:7860", flush=True)
    build_ui(tok, model).launch(server_name="127.0.0.1", server_port=7860)


if __name__ == "__main__":
    main()
