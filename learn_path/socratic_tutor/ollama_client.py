"""ollama_client.py — 可重用的本機 Ollama HTTP 客戶端。

把 simple_4B_ollama 裡分散的 Ollama 呼叫邏輯收斂成乾淨、可 import 的模組，供
評估流程（產參考解、A-socratic 基準、LLM judge、模擬學生、solution-grounded 引導）共用。

設計重點：
  * chat()           — 通用對話呼叫，自動處理「模型拒絕 think 參數回 HTTP 400 → 移除重送」、
                       以及舊版 Ollama 把 <think> 內嵌在 content 的切割。
  * generate_proof() — 用「完整證明」system prompt 產出參考解，含截斷自動續寫（最多 2 輪）。
  * resolve_model()  — 從 learn_path/ollama_model.txt 讀 tag，預設 qwen3:4b。

所有函式都是純 HTTP（urllib），不依賴 transformers，因此不與 GPU 上的 4-bit 模型搶顯存
（Ollama 自管 llama.cpp）。但請注意：同時讓 transformers 模型常駐 + Ollama 推理仍會搶 6GB，
故評估流程採「生成 → 存 JSON → 評分」分階段，避免兩者同時佔用。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = "qwen3:4b"
REQUEST_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "1800"))

# learn_path 目錄（socratic_tutor 的上一層），ollama_model.txt 放在那
_HERE = os.path.dirname(os.path.abspath(__file__))
_LEARN_PATH = os.path.dirname(_HERE)


def resolve_model() -> str:
    """讀 learn_path/ollama_model.txt 的 tag；不存在則回 DEFAULT_MODEL。"""
    for cand in (os.path.join(_LEARN_PATH, "ollama_model.txt"),
                 os.path.join(_HERE, "ollama_model.txt")):
        if os.path.exists(cand):
            try:
                tag = open(cand, encoding="utf-8").read().strip()
                if tag:
                    return tag
            except Exception:
                pass
    return os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)


def _split_think(text: str) -> tuple[str, str]:
    """舊版 Ollama 沒回結構化 thinking 欄位時，從 </think> 切割。"""
    if "</think>" in text:
        head, _, tail = text.partition("</think>")
        return head.replace("<think>", "").strip(), tail.strip()
    return "", text.strip()


def _post_chat(payload: dict, timeout: int = REQUEST_TIMEOUT) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat(
    messages: list[dict],
    model: Optional[str] = None,
    *,
    num_predict: int = 2048,
    num_ctx: int = 8192,
    temperature: float = 0.6,
    top_p: float = 0.95,
    top_k: int = 20,
    think: bool = True,
    timeout: int = REQUEST_TIMEOUT,
) -> dict:
    """通用 Ollama 對話。回傳 {content, thinking, done_reason, model}。

    自動處理：think 參數被模型拒絕（HTTP 400）→ 移除後重送；舊版內嵌 <think> → 切割。
    """
    model = model or resolve_model()
    options = {
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "num_predict": num_predict,
        "num_ctx": num_ctx,
    }
    payload = {"model": model, "messages": messages, "stream": False,
               "options": options, "think": think}
    try:
        resp = _post_chat(payload, timeout)
    except urllib.error.HTTPError as e:
        if e.code == 400:
            payload.pop("think", None)
            resp = _post_chat(payload, timeout)
        else:
            raise

    msg = resp.get("message", {}) or {}
    content = (msg.get("content") or "").strip()
    thinking = (msg.get("thinking") or "").strip()
    if not thinking:  # 舊版：思考內嵌在 content
        thinking, content = _split_think(content)
    return {
        "content": content,
        "thinking": thinking,
        "done_reason": resp.get("done_reason"),
        "model": model,
        "_raw_message": msg,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 參考解（完整證明）— 給 solution-grounded 引導當「答案卡」
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROOF = (
    "You are a careful mathematics assistant. Provide a rigorous, complete, "
    "step-by-step proof as your final answer, using precise definitions and "
    "theorem names. Do not use vague justifications such as 'obvious' or "
    "'clearly'.\n"
    "Decide the single best proof strategy in one short sentence, then execute "
    "it directly. Do NOT explore multiple alternative approaches or restart your "
    "reasoning. Keep your thinking focused and concise, and make sure you finish "
    "writing the complete final proof rather than over-thinking."
)


def generate_proof(
    raw_problem: str,
    model: Optional[str] = None,
    *,
    num_predict: int = 15360,
    num_ctx: int = 16384,
    temperature: float = 0.6,
    top_p: float = 0.95,
    top_k: int = 20,
) -> dict:
    """用思考型模型產出完整證明，含截斷偵測 + 最多 2 輪自動續寫。

    回傳 {proof, reasoning, model, truncated}。proof 即可當參考解（答案卡）。
    """
    model = model or resolve_model()
    messages = [
        {"role": "system", "content": SYSTEM_PROOF},
        {"role": "user", "content":
            f"Prove the following statement rigorously.\n\nProblem: {raw_problem}"},
    ]
    options = {"temperature": temperature, "top_p": top_p, "top_k": top_k,
               "num_predict": num_predict, "num_ctx": num_ctx}
    payload = {"model": model, "messages": messages, "stream": False,
               "options": options, "think": True}
    try:
        resp = _post_chat(payload)
    except urllib.error.HTTPError as e:
        if e.code == 400:
            payload.pop("think", None)
            resp = _post_chat(payload)
        else:
            raise

    msg = resp.get("message", {}) or {}
    answer = (msg.get("content") or "").strip()
    reasoning = (msg.get("thinking") or "").strip()
    if not reasoning:
        reasoning, answer = _split_think(answer)

    truncated = False
    if resp.get("done_reason") == "length":
        truncated = True
        partial = (msg.get("thinking") or "") + (msg.get("content") or "")
        cont_messages = messages + [
            {"role": "assistant", "content": partial},
            {"role": "user", "content": (
                "You have already reasoned enough above. Stop thinking now and output "
                "ONLY the final, complete, rigorous step-by-step proof. Do not continue "
                "the scratch work or re-derive from scratch."
            )},
        ]
        parts: list[str] = []
        for _ in range(2):
            cont_payload = {"model": model, "messages": cont_messages,
                            "stream": False, "options": options, "think": False}
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
            if not chunk:
                _, chunk = _split_think(msg2.get("content") or "")
            if chunk:
                parts.append(chunk)
            if resp2.get("done_reason") != "length":
                break
            cont_messages = cont_messages + [
                {"role": "assistant", "content": chunk},
                {"role": "user", "content": (
                    "Continue the proof from exactly where you stopped. Do not repeat "
                    "what you already wrote; just continue and finish it."
                )},
            ]
        combined = "\n".join(p for p in parts if p).strip()
        if combined:
            answer = combined

    return {"proof": answer, "reasoning": reasoning, "model": model,
            "truncated": truncated}


def health_check() -> bool:
    """確認 Ollama 服務在跑。"""
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False
