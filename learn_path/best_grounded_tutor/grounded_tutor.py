"""grounded_tutor.py — Solution-grounded 蘇格拉底微積分助教（自包含、可獨立運行）。

這是 learn_path 評估中表現最好且最安全的方法（見 ../socratic_tutor/eval_out/EVAL_REPORT.md）：
held-out 教學品質 4.42/5，在「正確性 + 不洩漏答案」上勝過 base 與單純微調。

核心理念——把「會解」與「會教」解耦：
  1. 先用本機 Ollama 的思考型模型產出完整證明 → 當「參考解 / 答案卡」（學生看不到）。
  2. 引導層把參考解放進 system prompt（隱藏），只問引導問句、絕不洩漏答案。
     老師「知道答案」才問得出指向正確下一步的問題，避免小模型自信給錯提示。

★ 零第三方依賴：只用 Python 標準函式庫（urllib）。唯一需求是本機 Ollama 在跑、且已 pull
  一個思考型模型（預設 qwen3-4b-thinking-2507）。不需要 torch / transformers / 微調權重。

──────────────────────────────────────────────────────────────────────────────
前置：
  1. 安裝並啟動 Ollama（https://ollama.com），服務預設在 http://localhost:11434
  2. 拉一個思考型模型：
       ollama pull qwen3-4b-thinking-2507
     （或任何思考型模型，再把 tag 寫進同資料夾的 ollama_model.txt，或設環境變數 OLLAMA_MODEL）

執行：
  # 互動多輪（輸入題目開始；對話中 quit 離開、reset 換新題）
  python grounded_tutor.py

  # 單題起手（直接給題目，看第一個引導問句）
  python grounded_tutor.py "Prove that lim_{x->2} x^2 = 4 using epsilon-delta."

環境變數（可選）：
  OLLAMA_HOST   Ollama 位址（預設 http://localhost:11434）
  OLLAMA_MODEL  覆寫模型 tag（優先順序：此變數 > ollama_model.txt > 內建預設）
  SHOW_REF=1    在終端印出參考解（debug 用；正常隱藏，避免誤以為要給學生看）
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────────────────────────────────────
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = "qwen3-4b-thinking-2507:latest"
REQUEST_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "1800"))
SHOW_REF = os.environ.get("SHOW_REF", "0") == "1"

_HERE = os.path.dirname(os.path.abspath(__file__))

# 思考型模型會先輸出長 <think> 再給 content，預算須夠大否則 content 被截成空：
PROOF_NUM_PREDICT = 15360   # 完整證明（思考鏈可能很長）
PROOF_NUM_CTX = 16384
GUIDE_NUM_PREDICT = 4096    # 引導問句（思考 + 短問句）
GUIDE_NUM_CTX = 16384

# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_SOCRATIC = (
    "You are a Socratic mathematics tutor specializing in calculus and "
    "mathematical proofs. Your goal is to help the student reach the answer "
    "by themselves, NOT to give the answer directly.\n"
    "Guidelines:\n"
    "- Never state the final answer or a full solution outright. Instead, ask "
    "ONE short, focused, leading question that moves the student one step forward. "
    "Wait for the student's response before asking the next question.\n"
    "- When the student presents a problem they have NOT yet attempted, ask ONE "
    "specific question that targets the key definition, theorem, or technique "
    "the proof requires. Examples: 'What does it mean for a sequence to be "
    "Cauchy?', 'What does the continuity of f at c tell you about f near c?', "
    "'If you apply the Mean Value Theorem on [M, x] rather than [0, x], what "
    "expression do you get?' — never respond with a generic 'Can you walk me "
    "through your approach?' when the student has no attempt yet.\n"
    "- Build on what the student says. If they make a mistake, do not just "
    "correct it — ask a question that helps them notice the error themselves.\n"
    "- Use precise calculus/analysis terminology: ε-δ definitions, Cauchy "
    "sequence, Monotone Convergence Theorem, Mean Value Theorem, Intermediate "
    "Value Theorem, uniform convergence, contraction mapping, etc.\n"
    "- When the student reaches a correct step, confirm it in one sentence and "
    "guide them to the next one.\n"
    "- Keep every reply under 80 words. Do not address the student by name."
)

SYSTEM_SOCRATIC_GROUNDED_SUFFIX = (
    "\n\nIMPORTANT — A correct reference solution to this problem is provided to "
    "you below, delimited by <reference> ... </reference>. The student CANNOT see "
    "it. Use the reference ONLY to make sure your guiding question points toward a "
    "correct next step and does not send the student down a wrong path. "
    "NEVER reveal, quote, restate, or paraphrase the reference solution, and never "
    "give away the final answer. Still ask only ONE short leading question."
)

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

STUDENT_NO_ATTEMPT_PREFIX = (
    "\n\nI have not started yet and I am not sure where to begin."
)


def build_grounded_system(reference_solution: str) -> str:
    return (
        SYSTEM_SOCRATIC
        + SYSTEM_SOCRATIC_GROUNDED_SUFFIX
        + f"\n\n<reference>\n{reference_solution.strip()}\n</reference>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Ollama 客戶端（純 urllib）
# ─────────────────────────────────────────────────────────────────────────────
def resolve_model() -> str:
    if os.environ.get("OLLAMA_MODEL"):
        return os.environ["OLLAMA_MODEL"]
    f = os.path.join(_HERE, "ollama_model.txt")
    if os.path.exists(f):
        try:
            tag = open(f, encoding="utf-8").read().strip()
            if tag:
                return tag
        except Exception:
            pass
    return DEFAULT_MODEL


def health_check() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def _split_think(text: str) -> tuple[str, str]:
    if "</think>" in text:
        head, _, tail = text.partition("</think>")
        return head.replace("<think>", "").strip(), tail.strip()
    return "", text.strip()


def _post_chat(payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat", data=data,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _chat(messages: list[dict], model: str, num_predict: int, num_ctx: int,
          temperature: float = 0.7, top_p: float = 0.9, top_k: int = 20) -> dict:
    options = {"temperature": temperature, "top_p": top_p, "top_k": top_k,
               "num_predict": num_predict, "num_ctx": num_ctx}
    payload = {"model": model, "messages": messages, "stream": False,
               "options": options, "think": True}
    try:
        resp = _post_chat(payload)
    except urllib.error.HTTPError as e:
        if e.code == 400:  # 模型不接受 think 參數
            payload.pop("think", None)
            resp = _post_chat(payload)
        else:
            raise
    msg = resp.get("message", {}) or {}
    content = (msg.get("content") or "").strip()
    thinking = (msg.get("thinking") or "").strip()
    if not thinking:
        thinking, content = _split_think(content)
    return {"content": content, "thinking": thinking,
            "done_reason": resp.get("done_reason"), "_msg": msg}


# ─────────────────────────────────────────────────────────────────────────────
# (1) 產參考解（含截斷自動續寫）
# ─────────────────────────────────────────────────────────────────────────────
def generate_reference(problem: str, model: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROOF},
        {"role": "user", "content":
            f"Prove the following statement rigorously.\n\nProblem: {problem}"},
    ]
    r = _chat(messages, model, PROOF_NUM_PREDICT, PROOF_NUM_CTX,
              temperature=0.6, top_p=0.95)
    answer = r["content"]

    # 截斷續寫：思考鏈吃光預算導致答案空/半截時，關 think 強制收尾
    if r["done_reason"] == "length":
        partial = (r["thinking"] or "") + (r["_msg"].get("content") or "")
        cont = messages + [
            {"role": "assistant", "content": partial},
            {"role": "user", "content":
                "You have reasoned enough. Stop thinking and output ONLY the final, "
                "complete, rigorous step-by-step proof. Do not re-derive from scratch."},
        ]
        parts: list[str] = []
        for _ in range(2):
            payload = {"model": model, "messages": cont, "stream": False,
                       "options": {"temperature": 0.6, "top_p": 0.95, "top_k": 20,
                                   "num_predict": PROOF_NUM_PREDICT,
                                   "num_ctx": PROOF_NUM_CTX},
                       "think": False}
            try:
                resp2 = _post_chat(payload)
            except urllib.error.HTTPError as e:
                if e.code == 400:
                    payload.pop("think", None)
                    resp2 = _post_chat(payload)
                else:
                    raise
            chunk = (resp2.get("message", {}).get("content") or "").strip()
            if not chunk:
                _, chunk = _split_think(resp2.get("message", {}).get("content") or "")
            if chunk:
                parts.append(chunk)
            if resp2.get("done_reason") != "length":
                break
            cont = cont + [
                {"role": "assistant", "content": chunk},
                {"role": "user", "content":
                    "Continue from exactly where you stopped; do not repeat, just finish."},
            ]
        combined = "\n".join(p for p in parts if p).strip()
        if combined:
            answer = combined
    return answer


# ─────────────────────────────────────────────────────────────────────────────
# (2) 引導回合
# ─────────────────────────────────────────────────────────────────────────────
def tutor_turn(system: str, history: list[dict], model: str) -> str:
    msgs = [{"role": "system", "content": system}] + history
    return _chat(msgs, model, GUIDE_NUM_PREDICT, GUIDE_NUM_CTX,
                 temperature=0.7, top_p=0.9)["content"]


# ─────────────────────────────────────────────────────────────────────────────
# 工作階段
# ─────────────────────────────────────────────────────────────────────────────
def _make_reference(problem: str, model: str) -> str:
    print("  [1/2] 產生參考解（答案卡，學生看不到）…", flush=True)
    ref = generate_reference(problem, model)
    if SHOW_REF:
        print("\n----- 參考解（debug）-----\n" + ref + "\n--------------------------\n")
    return ref


def run_session(problem: str, model: str) -> None:
    ref = _make_reference(problem, model)
    system = build_grounded_system(ref)
    print("  [2/2] 進入引導對話。\n")
    history = [{"role": "user", "content": problem + STUDENT_NO_ATTEMPT_PREFIX}]
    first = tutor_turn(system, history, model)
    history.append({"role": "assistant", "content": first})
    print(f"Tutor: {first}\n")
    while True:
        try:
            user = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not user or user.lower() in {"quit", "exit", "q"}:
            break
        if user.lower() == "reset":
            print("（reset：請輸入新題目）\n")
            return
        history.append({"role": "user", "content": user})
        ans = tutor_turn(system, history, model)
        history.append({"role": "assistant", "content": ans})
        print(f"Tutor: {ans}\n")


def main() -> None:
    if not health_check():
        print(f"[錯誤] 連不上 Ollama（{OLLAMA_HOST}）。")
        print("       請先啟動 Ollama，並 `ollama pull qwen3-4b-thinking-2507`。")
        sys.exit(1)
    model = resolve_model()
    print(f"Solution-grounded 蘇格拉底微積分助教  (model={model})\n")

    args = sys.argv[1:]
    if args:  # 單題起手
        problem = " ".join(args)
        ref = _make_reference(problem, model)
        system = build_grounded_system(ref)
        history = [{"role": "user", "content": problem + STUDENT_NO_ATTEMPT_PREFIX}]
        print("\nTutor:", tutor_turn(system, history, model))
        return

    print("（互動模式：輸入題目開始；對話中 quit 離開、reset 換新題）\n")
    while True:
        try:
            problem = input("Enter problem: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not problem or problem.lower() in {"quit", "exit", "q"}:
            break
        run_session(problem, model)
        print("─" * 60 + "\n")


if __name__ == "__main__":
    main()
