"""
simple_4B_ollama.py — Qwen3-4B-Thinking via local Ollama (no HuggingFace download)

為什麼有這支：這台筆電的網路擋掉了 HF 的檔案 CDN（DNS + 傳輸層），抓不動
transformers 用的 safetensors 權重。Ollama 走自己的 registry（暢通），且用
llama.cpp 推理，徹底繞開 transformers 5.x + bitsandbytes 的 segfault 問題。

與 simple_4B.py（transformers 版）對應，但改呼叫本機 Ollama HTTP API：
  - 模型 tag 從 ollama_model.txt 讀取（pull 時寫入），預設 qwen3:4b。
  - 採樣用 Qwen 思考模型建議：temperature=0.6, top_p=0.95, top_k=20。
  - num_predict=15360（思考鏈長）、num_ctx=16384（實測 20480 會 offload 到 CPU）。
  - 截斷自動續寫：最難題的思考鏈會吃光生成預算、最終答案變空（done_reason
    ="length"）。偵測到後關閉 think、把思考接回，強制模型輸出最終證明。
  - 優先用 Ollama 的結構化 thinking 欄位分離推理/答案；舊版則退回 </think> 切割。

前置：Ollama 已安裝且服務在跑（http://localhost:11434），且已
    ollama pull qwen3:4b   （或 qwen3:4b-thinking-2507）

Usage:
    python simple_4B_ollama.py                          # interactive
    python simple_4B_ollama.py "Prove that 2+2=4."      # single problem
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_HOST    = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL  = "qwen3:4b"
NUM_PREDICT    = 15360      # max new tokens (thinking + answer); 最難題思考鏈可達 ~2 萬字元
NUM_CTX        = 16384      # context window；實測 20480 會讓 KV+權重達 6.0GB 致 30% offload 到 CPU
                            # （ollama ps 顯示 30%/70% CPU/GPU、速度大降）。16384 全程留在 GPU。
                            # 若仍截斷，交由下方「截斷續寫」補完，不靠加大 ctx。
TEMPERATURE    = 0.6
TOP_P          = 0.95
TOP_K          = 20
REQUEST_TIMEOUT = 1800      # seconds; long thinking on a 4050 can take minutes

SYSTEM_PROMPT = (
    "You are a careful mathematics assistant. Provide a rigorous, complete, "
    "step-by-step proof as your final answer, using precise definitions and "
    "theorem names. Do not use vague justifications such as 'obvious' or "
    "'clearly'.\n"
    # 從源頭抑制「思考鏈爆量 → 被截斷」：先定策略、直接執行、勿窮舉多法、
    # 思考精簡。對思考型模型，這能在不傷正確性下大幅縮短 <think> 長度。
    "Decide the single best proof strategy in one short sentence, then execute "
    "it directly. Do NOT explore multiple alternative approaches or restart your "
    "reasoning. Keep your thinking focused and concise, and make sure you finish "
    "writing the complete final proof rather than over-thinking."
)

_HERE = os.path.dirname(os.path.abspath(__file__))


def _resolve_model() -> str:
    """Read the model tag written by the pull step; fall back to DEFAULT_MODEL."""
    f = os.path.join(_HERE, "ollama_model.txt")
    if os.path.exists(f):
        try:
            tag = open(f, encoding="utf-8").read().strip()
            if tag:
                return tag
        except Exception:
            pass
    return DEFAULT_MODEL


def _split_think(text: str) -> tuple[str, str]:
    """Fallback splitter when Ollama doesn't return a structured 'thinking' field."""
    if "</think>" in text:
        head, _, tail = text.partition("</think>")
        return head.replace("<think>", "").strip(), tail.strip()
    return "", text.strip()


def _post_chat(payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_simple_4b_ollama(
    raw_problem: str,
    model: Optional[str] = None,
    return_thinking: bool = False,
):
    """Send the problem to a local Ollama thinking model; return the final proof.

    With return_thinking=True, returns {"reasoning": ..., "answer": ..., "model": ...}.
    """
    model = model or _resolve_model()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Prove the following statement rigorously.\n\nProblem: {raw_problem}"},
    ]
    options = {
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "top_k": TOP_K,
        "num_predict": NUM_PREDICT,
        "num_ctx": NUM_CTX,
    }
    payload = {"model": model, "messages": messages, "stream": False, "options": options, "think": True}

    print(f"  [ollama] model={model} num_ctx={NUM_CTX} num_predict={NUM_PREDICT}", flush=True)
    try:
        resp = _post_chat(payload)
    except urllib.error.HTTPError as e:
        # Some models/versions reject "think": retry without it and split manually.
        if e.code == 400:
            payload.pop("think", None)
            resp = _post_chat(payload)
        else:
            raise

    msg = resp.get("message", {}) or {}
    answer = (msg.get("content") or "").strip()
    reasoning = (msg.get("thinking") or "").strip()
    if not reasoning:  # older Ollama: thinking is inline in content
        reasoning, answer = _split_think(answer)

    # ── 截斷偵測 + 自動續寫（最多 2 輪，可拼接）──────────────────────────
    # 思考型模型在最難題上會把整個 num_predict 預算耗在思考鏈，導致最終答案
    # 為空（done_reason="length" 且 content 空）或寫到一半被截斷（content 半截）。
    # done_reason=="length" 幾乎必然代表輸出不完整（正常收尾是 "stop"），故只要
    # 偵測到 length 就續寫：把已生成內容接回、關閉 think（整個預算留給答案）。
    #   第 1 輪：要求「停止思考、直接輸出完整最終證明」。think=False 下證明通常
    #            一輪就寫完（~1000 token << 15360 預算）。
    #   第 2 輪：保險——若連答案本身都太長又被截，要求「從中斷處接著寫完」並拼接。
    # 不必無限加大 num_ctx，省 VRAM；半截答案會被完整版取代。
    if resp.get("done_reason") == "length":
        partial = (msg.get("thinking") or "") + (msg.get("content") or "")
        cont_messages = messages + [
            {"role": "assistant", "content": partial},
            {"role": "user", "content": (
                "You have already reasoned enough above. Stop thinking now and output ONLY "
                "the final, complete, rigorous step-by-step proof. Do not continue the "
                "scratch work or re-derive from scratch."
            )},
        ]
        answer_parts: list[str] = []
        for attempt in range(1, 3):  # 最多 2 輪續寫
            print(f"  [ollama] done_reason=length → 續寫第 {attempt} 輪（強制收尾）", flush=True)
            cont_payload = {
                "model": model, "messages": cont_messages,
                "stream": False, "options": options, "think": False,
            }
            try:
                resp2 = _post_chat(cont_payload)
            except urllib.error.HTTPError as e:
                if e.code == 400:
                    cont_payload.pop("think", None)
                    resp2 = _post_chat(cont_payload)
                else:
                    raise
            msg2 = resp2.get("message", {}) or {}
            chunk = (msg2.get("content") or "").strip()
            if not chunk:  # 極少數情況答案仍夾在 <think> 裡
                _, chunk = _split_think(msg2.get("content") or "")
            if chunk:
                answer_parts.append(chunk)
            if resp2.get("done_reason") != "length":
                break  # 已完整收尾
            # 連答案都被截斷：要求從中斷處接著寫，下一輪拼接
            cont_messages = cont_messages + [
                {"role": "assistant", "content": chunk},
                {"role": "user", "content": (
                    "Continue the proof from exactly where you stopped. Do not repeat what "
                    "you already wrote; just continue and finish it."
                )},
            ]
        combined = "\n".join(p for p in answer_parts if p).strip()
        if combined:
            answer = combined
            reasoning = (reasoning + "\n\n[思考被截斷，已強制收尾並續寫補完]").strip()

    if return_thinking:
        return {"reasoning": reasoning, "answer": answer, "model": model}
    return answer


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _print_answer(raw_problem: str, answer: str, reasoning: str, elapsed: float) -> None:
    sep = "─" * 64
    print(f"\n{sep}")
    print(f"Problem: {raw_problem}")
    if reasoning:
        print(f"\n(thinking: ~{len(reasoning)} chars — hidden)")
    print(f"\nAnswer (final proof):\n{answer}")
    print(f"\n(elapsed {elapsed:.1f}s)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "-f" and args[1].endswith(".json"):
        args = []

    if args:
        raw = " ".join(args)
        t0 = time.time()
        r = run_simple_4b_ollama(raw, return_thinking=True)
        _print_answer(raw, r["answer"], r["reasoning"], time.time() - t0)
        print(f"\n{'─'*64}\nDone. (model={r['model']})")
    else:
        print("Qwen3-4B-Thinking via Ollama  (type 'quit' or leave blank to exit)\n")
        while True:
            try:
                raw = input("Enter problem: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not raw or raw.lower() in {"quit", "exit", "q"}:
                break
            t0 = time.time()
            r = run_simple_4b_ollama(raw, return_thinking=True)
            _print_answer(raw, r["answer"], r["reasoning"], time.time() - t0)
            print()
        print(f"{'─'*64}\nDone.")
