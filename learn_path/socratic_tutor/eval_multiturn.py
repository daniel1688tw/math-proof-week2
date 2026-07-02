"""eval_multiturn.py — 模擬學生的多輪引導評估（improve.md 問題④）。

原本所有評估都只測「第一輪」，但目標是「一步步引導到解出」。本腳本用一個 LLM 扮演學生
（會嘗試、會犯典型錯誤、一次只回應老師問的那一步），與「助教 backend」對話數輪，
再用 LLM judge 評整段對話：是否引導到正確完成、引導是否正確、有沒有過早給答案、
是否能因應學生回應調整。

助教 backend（皆走 Ollama，避免與 transformers 搶顯存）：
  * socratic — SYSTEM_SOCRATIC（純 prompt 基準）
  * grounded — 隱藏參考解（需 eval_out/reference_solutions.json）

> 微調後的 transformers 模型要做多輪評估，請改用 inference.py 互動，或自行把它包成 backend；
> 但那會與「Ollama 學生」搶顯存，需分階段（先快取學生回應較難，故此處統一用 Ollama）。

輸出：eval_out/multiturn_<backend>.json

執行（需 Ollama）：
  conda run -n lora_project --live-stream python eval_multiturn.py            # grounded
  python eval_multiturn.py socratic
"""

from __future__ import annotations

import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ollama_client as oc
from common import SYSTEM_SOCRATIC, build_grounded_system
from eval_common import OUT_DIR, load_reference_solutions
from problems import HELDOUT_PROBLEMS

MAX_TURNS = int(os.environ.get("MT_TURNS", "6"))     # 老師問句數上限
N_PROBLEMS = int(os.environ.get("MT_N", "4"))        # 評估題數（held-out 前 N 題）

STUDENT_SYSTEM = (
    "You are a university student learning calculus and real analysis. You are working "
    "through a proof problem WITH a tutor who asks you one guiding question at a time. "
    "Rules:\n"
    "- Respond ONLY to the tutor's latest question. Do NOT solve the whole problem at once.\n"
    "- Attempt the step honestly in 1-3 sentences. It is fine (and realistic) to be "
    "unsure or to make a plausible mistake sometimes.\n"
    "- Do not look up or state the full final proof. Work it out step by step.\n"
    "- When you genuinely believe the proof is finished, end your message with the exact "
    "tag [DONE]."
)

JUDGE_SYSTEM = (
    "You grade a multi-turn Socratic tutoring transcript for a calculus proof. You are "
    "given the PROBLEM, a correct REFERENCE SOLUTION, and the TRANSCRIPT (tutor=T, "
    "student=S). Grade the TUTOR's performance on five criteria, each integer 0/1/2:\n"
    "  reached_completion: by the end, was the student guided to a essentially correct, "
    "complete proof? 2=yes, 1=partial, 0=no.\n"
    "  guidance_correct: were the tutor's hints/claims mathematically correct throughout "
    "(per reference)? 2=all correct, 1=minor slip, 0=a wrong/misleading hint.\n"
    "  no_premature_answer: did the tutor avoid just handing over the solution? "
    "2=never, 1=once leaned too far, 0=gave it away.\n"
    "  adaptivity: did the tutor build on / correct the student's actual responses "
    "(not ignore them)? 2=clearly, 1=somewhat, 0=ignored student.\n"
    "  progress: did each tutor turn move one concrete step forward? 2=steady, "
    "1=some stalling, 0=circular/stuck.\n"
    "Respond with ONLY JSON: "
    '{\"reached_completion\":N,\"guidance_correct\":N,\"no_premature_answer\":N,'
    '\"adaptivity\":N,\"progress\":N,\"rationale\":\"one sentence\"}'
)


def _tutor_system(backend: str, problem_id: str, refs: dict) -> str:
    if backend == "grounded":
        ref = refs.get(problem_id, {}).get("proof", "")
        if ref:
            return build_grounded_system(ref)
    return SYSTEM_SOCRATIC


def _student_reply(problem: str, transcript: list[dict], model: str) -> tuple[str, bool]:
    # transcript: [{role: tutor/student, content}]；轉成學生視角的 messages
    msgs = [{"role": "system", "content": STUDENT_SYSTEM},
            {"role": "user", "content": f"Here is the problem:\n{problem}"}]
    for t in transcript:
        role = "user" if t["role"] == "tutor" else "assistant"
        msgs.append({"role": role, "content": t["content"]})
    # qwen3-thinking 會先思考再答；預算須含思考量，否則 content 空
    r = oc.chat(msgs, model=model, num_predict=3072, num_ctx=8192,
                temperature=0.7, top_p=0.9, think=True)
    txt = r["content"]
    done = "[DONE]" in txt
    return txt.replace("[DONE]", "").strip(), done


def _tutor_reply(system: str, problem: str, transcript: list[dict], model: str) -> str:
    msgs = [{"role": "system", "content": system},
            {"role": "user", "content": problem
             + "\n\nI have not started yet and I am not sure where to begin."}]
    # 把已發生的對話接上：學生=user、老師=assistant（從第二輪起）
    for t in transcript[1:]:  # transcript[0] 是首輪老師問句，已在歷史外
        role = "assistant" if t["role"] == "tutor" else "user"
        msgs.append({"role": role, "content": t["content"]})
    r = oc.chat(msgs, model=model, num_predict=4096, num_ctx=16384,
                temperature=0.7, top_p=0.9, think=True)
    return r["content"]


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def _judge(problem: str, ref: str, transcript: list[dict], model: str) -> dict:
    lines = []
    for t in transcript:
        tag = "T" if t["role"] == "tutor" else "S"
        lines.append(f"{tag}: {t['content']}")
    user = (f"PROBLEM:\n{problem}\n\nREFERENCE SOLUTION:\n{ref or '(none)'}\n\n"
            f"TRANSCRIPT:\n" + "\n".join(lines) + "\n\nGrade the tutor.")
    r = oc.chat([{"role": "system", "content": JUDGE_SYSTEM},
                 {"role": "user", "content": user}],
                model=model, num_predict=4096, num_ctx=16384,
                temperature=0.0, top_p=0.9, think=True)
    p = _extract_json(r["content"])
    keys = ("reached_completion", "guidance_correct", "no_premature_answer",
            "adaptivity", "progress")
    sc = {k: int(p.get(k, 0)) for k in keys}
    sc["total"] = sum(sc.values())
    sc["rationale"] = str(p.get("rationale", ""))[:200]
    return sc


def run_problem(p: dict, backend: str, refs: dict, model: str) -> dict:
    system = _tutor_system(backend, p["id"], refs)
    transcript: list[dict] = []
    # 首輪老師問句
    first = _tutor_reply(system, p["problem"], transcript, model)
    transcript.append({"role": "tutor", "content": first})
    print(f"\n  [{p['id']}] T1: {first[:110].replace(chr(10),' ')}…")
    for turn in range(MAX_TURNS):
        s_txt, done = _student_reply(p["problem"], transcript, model)
        transcript.append({"role": "student", "content": s_txt})
        print(f"     S: {s_txt[:90].replace(chr(10),' ')}…")
        if done:
            print("     （學生宣告完成）")
            break
        t_txt = _tutor_reply(system, p["problem"], transcript, model)
        transcript.append({"role": "tutor", "content": t_txt})
        print(f"     T: {t_txt[:90].replace(chr(10),' ')}…")
    ref = refs.get(p["id"], {}).get("proof", "")
    judge = _judge(p["problem"], ref, transcript, model)
    print(f"     → judge {judge['total']}/10  {judge['rationale']}")
    return {"id": p["id"], "problem": p["problem"], "backend": backend,
            "transcript": transcript, "judge": judge}


def main() -> None:
    if not oc.health_check():
        print(f"[錯誤] 連不上 Ollama（{oc.OLLAMA_HOST}）。"); sys.exit(1)
    backend = sys.argv[1] if len(sys.argv) > 1 else "grounded"
    model = oc.resolve_model()
    refs = load_reference_solutions()
    if backend == "grounded" and not refs:
        print("[警告] grounded 需要參考解但找不到；退回 socratic。")
        backend = "socratic"
    problems = HELDOUT_PROBLEMS[:N_PROBLEMS]
    print(f"[多輪評估] backend={backend} model={model} 題數={len(problems)} 上限{MAX_TURNS}輪")

    results = [run_problem(p, backend, refs, model) for p in problems]
    avg = sum(r["judge"]["total"] for r in results) / max(1, len(results))

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"multiturn_{backend}.json")
    json.dump({"backend": backend, "avg_judge": avg, "results": results},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n[完成] 平均 judge {avg:.2f}/10 → {out}")


if __name__ == "__main__":
    main()
