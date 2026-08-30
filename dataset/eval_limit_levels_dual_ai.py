# -*- coding: utf-8 -*-
"""以 agy GPT-OSS 120B 學生測試 v9 助教的多層提示完整對話。"""
from __future__ import annotations

import argparse
import base64
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


SCENARIOS = ("normal_progress", "stuck_escalation", "misconception_repair")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_SOURCE = ROOT / "math-proof-week2-main (main的前一版) - 複製 - 進行修改5.txt"
DEFAULT_OUTPUT = HERE / "eval_out_xdomain" / "limit_levels_gpt_oss_120b.json"
AGY_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"
AGY_WRAPPER = ROOT / "server_train" / "agy_utf8.ps1"
STUDENT_MODEL = os.environ.get("AGY_STUDENT_MODEL", "gpt-oss-120b-medium")
REVIEW_MODEL = os.environ.get("AGY_REVIEW_MODEL", "gemini-3.6-flash-medium")


def extract_json_object(text: str) -> dict | None:
    """從 agy 可能帶 code fence 的輸出擷取第一個 JSON 物件。"""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(),
                     flags=re.I | re.S)
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", cleaned):
        try:
            value, _ = decoder.raw_decode(cleaned[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def build_limit_problem(statement: str) -> dict:
    """把來源紀錄中的題目轉為具參考解、提示梯與可驗證步驟的 grounded 題目。"""
    reference = (
        r"因為 $L>0$，取 $ε=L/2>0$。由 "
        r"$\lim_{x\to a}f(x)=L$ 的定義，存在 $δ>0$，使得當 "
        r"$0<|x-a|<δ$ 時，$|f(x)-L|<L/2$。因此 "
        r"$-L/2<f(x)-L<L/2$，所以 $L/2<f(x)<3L/2$。又 "
        r"$L/2>0$，故 $f(x)>0$。"
    )
    steps_zh = [
        {
            "step_id": "s1", "core_idea": "選擇正的 epsilon",
            "explain": r"由 $L>0$，取 $ε=L/2>0$。",
            "check": r"為什麼 $ε=L/2$ 是合法的？",
            "expected_answer": r"因為 $L>0$，所以 $L/2>0$。",
            "accepted_answers": ["L/2>0", "因為 L>0，所以 L/2>0"],
            "common_errors": ["把 epsilon 取成負數"],
        },
        {
            "step_id": "s2", "core_idea": "套用極限定義",
            "explain": (r"由極限定義，存在 $δ>0$，使 $0<|x-a|<δ$ 時，"
                        r"$|f(x)-L|<L/2$。"),
            "check": r"此時 $|f(x)-L|$ 小於多少？",
            "expected_answer": r"$L/2$",
            "accepted_answers": ["L/2", "小於 L/2"],
            "common_errors": [],
        },
        {
            "step_id": "s3", "core_idea": "展開絕對值不等式",
            "explain": (r"展開得 $-L/2<f(x)-L<L/2$，各項加 $L$ 後得到 "
                        r"$L/2<f(x)<3L/2$。"),
            "check": r"由此得到 $f(x)$ 的下界是多少？",
            "expected_answer": r"$L/2$",
            "accepted_answers": ["L/2", "f(x)>L/2"],
            "common_errors": ["把 L-L/2 算成 L/3", "回答成上界 3L/2"],
        },
        {
            "step_id": "s4", "core_idea": "推出正性",
            "explain": r"因 $f(x)>L/2$ 且 $L/2>0$，所以 $f(x)>0$。",
            "check": r"為什麼 $f(x)>0$？",
            "expected_answer": r"因為 $f(x)>L/2>0$。",
            "accepted_answers": ["f(x)>L/2>0", "因為 f(x)>L/2 且 L/2>0"],
            "common_errors": [],
        },
    ]
    steps_en = [
        {
            "step_id": step["step_id"], "core_idea": step["core_idea"],
            "explain": step["explain"], "check": step["check"],
            "expected_answer": step["expected_answer"],
            "accepted_answers": step["accepted_answers"],
            "common_errors": step["common_errors"],
        }
        for step in steps_zh
    ]
    return {
        "id": "CUSTOM_LIMIT_POSITIVITY",
        "statement": statement,
        "reference_proof": reference,
        "hint_ladder": [
            r"先不要處理 $δ$。由 $L>0$，可以選哪個與 $L$ 有關的正數作為 $ε$？",
            r"取 $ε=L/2$，再把 $|f(x)-L|<L/2$ 展開；$f(x)$ 的下界是多少？",
        ],
        "hint_ladder_en": [
            "Before choosing delta, what positive epsilon built from L can you use?",
            "Take epsilon=L/2 and expand |f(x)-L|<L/2. What lower bound for f(x) follows?",
        ],
        "teach_steps_initial_status": "success",
        "teach_steps_source_zh": "manual_verified_reference",
        "teach_steps_source_en": "manual_verified_reference",
        "teach_steps_zh": steps_zh,
        "teach_steps_en": steps_en,
    }


def extract_unique_problem_statements(path: Path) -> list[str]:
    """依首次出現順序擷取舊對話紀錄中的唯一題目。"""
    prefix = "Custom problem:"
    unique: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith(prefix):
            continue
        statement = line[len(prefix):].strip()
        if statement and statement not in unique:
            unique.append(statement)
    return unique


def choose_student_mode(scenario: str, turn_index: int, phase: str,
                        tutor_reply: str, state: dict) -> str:
    """根據受控情境與真實 driver 狀態選擇下一輪學生行為。"""
    if phase == "closed":
        return "done"
    if phase == "review":
        if (state.get("active_issue")
                or "局部訂正" in tutor_reply
                or "local correction" in tutor_reply.lower()):
            return "local_repair"
        if "乾淨完整證明" in tutor_reply or "clean full proof" in tutor_reply.lower():
            return "clean_full_proof"
        if scenario == "misconception_repair" and not state.get("flawed_proof_submitted"):
            return "flawed_full_proof"
        return "correct_full_proof"
    if phase == "walkthrough":
        if scenario == "misconception_repair" and not state.get("misconception_used"):
            return "wrong_step"
        return "learn_step"
    if scenario in {"stuck_escalation", "misconception_repair"} and turn_index <= 4:
        return "force_stuck"
    if scenario == "normal_progress" and turn_index >= 5:
        return "declare_ready"
    return "learn_step"


def build_student_prompt(problem: dict, scenario: str, mode: str,
                         transcript: list[dict], tutor_reply: str) -> str:
    """建立不含參考解、但具可重現行為控制的 GPT-OSS 學生提示。"""
    history = "\n".join(
        ("助教：" if row.get("role") == "tutor" else "學生：") + str(row.get("text") or "")
        for row in transcript[-16:]
    )
    instructions = {
        "force_stuck": ("你仍完全不知道下一步。學生訊息必須完整包含「我完全不知道怎麼繼續，"
                         "完全卡住了，毫無頭緒。」；可以在前後加少量自然語氣，但不得用問句，"
                         "不得提出公式、定理或可能方向。behavior 必須是 stuck。"),
        "learn_step": ("只回答助教目前問的最小一步；即使前面曾卡住，現在也要依助教提示完成或確認"
                       "這一步，不得反問、不得再次表示卡住，也不要提前寫完整證明。"
                       "輸出 JSON 的 behavior 必須是 ready 或 attempt。"),
        "declare_ready": "你已理解前面討論的整體思路；自然表示已經懂了並準備寫完整證明。",
        "wrong_step": ("刻意給出一個常見且局部的初學者錯誤：把 L-L/2 算成 L/3，"
                       "但不要說這是刻意測試。"),
        "flawed_full_proof": ("助教要求完整證明。提交一份看似完整但含三個錯誤的證明："
                              "取 epsilon=-L/2、把條件寫成 |x-a|<=delta、把下界寫成 5L/2。"),
        "local_repair": "只修正助教目前指出的那一項，不重寫全文，也不要自行修其他項。",
        "correct_full_proof": "提交一份自足、嚴謹且正確的完整證明。",
        "clean_full_proof": "重新提交不含訂正註記、完整且正確的乾淨證明。",
    }[mode]
    return f"""你是透過 agy CLI 執行的 GPT-OSS 120B (Medium)，扮演剛開始學高等數學證明的學生。

題目：{problem['statement']}
測試情境：{scenario}
目前對話：
{history or '（尚未開始）'}
助教最新回覆：{tutor_reply or '（尚無）'}

規則：
- 你看不到參考證明，不得使用工具或外部資料。
- 使用繁體中文，以真實學生口吻回覆，不得評論測試或角色扮演。
- 除非助教明確要求完整證明，否則只處理當前一步。
- 受控模式名稱是 {mode}；行為要求：{instructions}

只輸出 JSON：{{"student_message":"學生下一句話","behavior":"stuck|attempt|wrong|ready|full_proof|repair"}}"""


def student_output_compliant(mode: str, data: dict | None) -> bool:
    """避免 agy 偏離受控 persona，讓 level 路徑具可重現性。"""
    message = str((data or {}).get("student_message") or "").strip()
    behavior = str((data or {}).get("behavior") or "").strip()
    if not message:
        return False
    if mode == "force_stuck":
        if behavior != "stuck":
            return False
        mentions_math = re.search(
            r"epsilon|varepsilon|ε|delta|δ|L/2|定理", message, re.I)
        if not mentions_math:
            return True
        # 學生可能只是重述助教剛給的式子並明確表示不會操作；這不是
        # 自己提出公式或方向。真正採取證明步驟（「取／令／因此…」）仍拒收。
        explicit_inability = re.search(
            r"不知道(?:該)?怎麼|不會(?:把|用|展開)|完全卡住|沒(?:有)?頭緒", message)
        asserts_progress = re.search(
            r"(?:^|[，。；])\s*(?:我)?(?:取|令|設|由|因此|所以|得到|推出|可知)", message)
        return bool(explicit_inability) and not bool(asserts_progress)
    if mode == "wrong_step":
        return behavior == "wrong" and "L/3" in message.replace(" ", "")
    if mode == "flawed_full_proof":
        compact = message.replace(" ", "")
        normalized = (compact
                      .replace(r"\frac{5L}{2}", "5L/2")
                      .replace(r"\frac{L}{2}", "L/2")
                      .replace(r"\varepsilon", "epsilon")
                      .replace(r"\delta", "delta")
                      .replace(r"\le", "<="))
        return (behavior == "full_proof" and len(message) >= 120
                and "-L/2" in normalized and "5L/2" in normalized
                and ("<=delta" in normalized.lower() or "≤δ" in normalized))
    if mode in {"correct_full_proof", "clean_full_proof"}:
        return behavior == "full_proof" and len(message) >= 180
    if mode == "local_repair":
        return behavior == "repair" and len(message) <= 240
    if mode == "declare_ready":
        return behavior == "ready" and bool(re.search(r"懂|清楚|理解|掌握|可以寫", message))
    return behavior in {"attempt", "wrong", "ready"} and len(message) <= 240


def assess_scenario(scenario: str, turns: list[dict], final_phase: str) -> dict:
    """檢查單一情境是否真的覆蓋預定路徑，而非只看程序退出碼。"""
    levels = [row.get("level") for row in turns]
    phases = [str(row.get("phase") or "") for row in turns]
    modes = [str(row.get("student_mode") or "") for row in turns]
    full_proof_modes = {"correct_full_proof", "flawed_full_proof", "clean_full_proof"}

    def effective_guide_review(row: dict) -> dict:
        review = row.get("guide_review") or {}
        return (review.get("regenerated") or review.get("retry")
                or review.get("initial") or {})

    incorrect_step_transitions = [
        row for row in turns
        if row.get("phase_before") == "guide"
        and str(row.get("phase") or "") in {"review", "closed"}
        and effective_guide_review(row).get("latest_student_step_status") == "incorrect"
    ]
    checks = {
        "finished_closed": final_phase == "closed",
        "submitted_full_proof": any(mode in full_proof_modes for mode in modes),
        "covered_level_0": 0 in levels,
        "incorrect_steps_never_triggered_readiness": not incorrect_step_transitions,
    }
    if scenario == "stuck_escalation":
        checks.update({
            "covered_level_0_1_2": all(level in levels for level in (0, 1, 2)),
            "entered_walkthrough": "walkthrough" in phases,
        })
    elif scenario == "misconception_repair":
        checks.update({
            "produced_misconception": any(
                mode in {"wrong_step", "flawed_full_proof"} for mode in modes),
            "attempted_repair": "local_repair" in modes,
            "entered_review": "review" in phases,
        })
    else:
        checks["entered_review"] = "review" in phases
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "levels": levels,
        "phases": phases,
        "student_modes": modes,
    }


def validate_evaluation(dialogues: list[dict]) -> dict:
    """只有三情境全數通過且合併覆蓋 0/1/2 才視為有效評估。"""
    by_name = {row.get("scenario"): row for row in dialogues}
    covered = sorted({
        level for row in dialogues for level in row.get("assessment", {}).get("levels", [])
        if isinstance(level, int)
    })
    valid = (
        set(by_name) == set(SCENARIOS)
        and all(bool(by_name[name].get("assessment", {}).get("passed")) for name in SCENARIOS)
        and all(level in covered for level in (0, 1, 2))
    )
    return {
        "valid": valid,
        "scenario_count": len(by_name),
        "covered_levels": covered,
        "passed_scenarios": [
            name for name in SCENARIOS
            if bool(by_name.get(name, {}).get("assessment", {}).get("passed"))
        ],
    }


def merge_dialogues(existing: list[dict], updates: list[dict]) -> list[dict]:
    """依情境合併斷點紀錄；重跑結果取代舊結果並維持固定順序。"""
    by_name = {
        row.get("scenario"): row
        for row in [*existing, *updates]
        if row.get("scenario") in SCENARIOS
    }
    return [by_name[name] for name in SCENARIOS if name in by_name]


def render_markdown(payload: dict) -> str:
    """將完整逐輪證據整理成可人工複核的 Markdown。"""
    validity = payload.get("validity", {})
    lines = [
        "# GPT-OSS 120B 學生 × v9 助教：Level 完整對話評估", "",
        f"- valid: {validity.get('valid')}",
        f"- covered levels: {validity.get('covered_levels', [])}", "",
    ]
    for dialogue in payload.get("dialogues", []):
        assessment = dialogue.get("assessment", {})
        lines.extend([
            f"## {dialogue.get('scenario')}", "",
            f"- passed: {assessment.get('passed')}",
        ])
        for name, value in assessment.get("checks", {}).items():
            lines.append(f"- {name}: {value}")
        for turn in dialogue.get("turns", []):
            lines.extend([
                "", f"### Turn {turn.get('turn')} — Level {turn.get('level')} / "
                f"{turn.get('phase')} / {turn.get('student_mode')}", "",
                f"- Student: {turn.get('student')}",
                f"- Tutor: {turn.get('tutor')}",
            ])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _decode_cli_output(raw: bytes) -> str:
    for encoding in ("utf-8", "cp950"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def call_agy(model: str, prompt: str, timeout: int = 180) -> str:
    """以 Base64/UTF-8 包裝呼叫 agy，避免 Windows argv 長度與編碼污染。"""
    if not AGY_EXE.exists():
        raise RuntimeError(f"找不到 agy CLI：{AGY_EXE}")
    student_cwd = Path(tempfile.gettempdir()) / "daniel-agy-limit-level-student"
    student_cwd.mkdir(parents=True, exist_ok=True)
    cmd = [
        "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-File", str(AGY_WRAPPER), model, str(timeout),
    ]
    encoded_prompt = base64.b64encode(prompt.encode("utf-8"))
    last_error = ""
    for attempt in range(4):
        result = subprocess.run(
            cmd, cwd=student_cwd if model == STUDENT_MODEL else ROOT,
            input=encoded_prompt, capture_output=True, text=False, timeout=timeout + 30)
        encoded_stdout = _decode_cli_output(result.stdout).strip()
        try:
            stdout = base64.b64decode(encoded_stdout).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            stdout = encoded_stdout
        stderr = _decode_cli_output(result.stderr)
        detail = (stderr + stdout).strip()
        transient = bool(re.search(
            r"high traffic|try again|temporarily unavailable|rate limit|too many requests|429",
            detail, re.I))
        if result.returncode == 0 and stdout.strip() and not transient:
            return stdout.strip()
        last_error = detail[-800:] or f"exit={result.returncode} empty output"
        if attempt < 3:
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"agy {model} 連續失敗：{last_error}")


def install_agy_review_backend() -> None:
    """讓 driver 的幕後數學判斷走本機 agy Gemini；學生仍固定 GPT-OSS 120B。"""
    import review_backstop

    def retry_parsed(system: str, user: str, parser, *, timeout: int,
                     num_predict: int = 8192, temperature: float = 0.15,
                     attempts: int = 3, per_attempt_timeout: int | None = None,
                     response_format=None, diagnostics: dict | None = None,
                     retry_instruction: str | None = None):
        del num_predict, temperature, per_attempt_timeout, response_format
        attempt_records = []
        prompt = user
        for index in range(max(1, attempts)):
            started = time.time()
            try:
                raw = call_agy(
                    REVIEW_MODEL,
                    system + "\n\n" + prompt
                    + "\n\n你是幕後數學審查器，不得使用工具；嚴格遵守 system 的輸出協定。",
                    timeout=min(180, max(60, timeout)))
                parsed = parser(raw)
            except Exception as exc:
                parsed = None
                failure = f"{type(exc).__name__}: {exc}"[-500:]
            else:
                failure = "structured_output_invalid" if parsed is None else None
            record = {
                "attempt": index + 1,
                "status": "parsed" if parsed is not None else "failed",
                "failure_reason": failure,
                "elapsed_seconds": round(time.time() - started, 3),
            }
            attempt_records.append(record)
            if parsed is not None:
                if diagnostics is not None:
                    diagnostics.update(status="parsed", failure_reason=None,
                                       attempts=attempt_records)
                return parsed
            if index + 1 < attempts:
                prompt = user + "\n\n" + (retry_instruction or (
                    "上一次輸出無法解析。請重新獨立檢查，只輸出 system 指定的 JSON。"))
        if diagnostics is not None:
            diagnostics.update(status="failed", failure_reason=attempt_records[-1]["failure_reason"],
                               attempts=attempt_records)
        return None

    review_backstop._retry_parsed = retry_parsed


class RemoteTutorDriverMixin:
    """經 Git SSH exec 呼叫只綁遠端 localhost 的 v9 推論服務。"""

    def _raw_generate(self, msgs: list, max_new: int) -> str:
        git_ssh = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "usr" / "bin" / "ssh.exe"
        ssh_exe = str(git_ssh if git_ssh.exists() else "ssh")
        known_hosts = ROOT / ".tmp_lab102_known_hosts"
        identity = Path(os.environ.get("USERPROFILE", "")) / ".ssh" / "id_ed25519"
        body = json.dumps({"messages": msgs, "max_new_tokens": max_new}, ensure_ascii=False)
        encoded = base64.b64encode(body.encode("utf-8")).decode("ascii")
        command = (
            f"printf '%s' '{encoded}' | base64 -d | "
            "curl -sS -m 170 -X POST http://localhost:8899/generate "
            "-H 'Content-Type: application/json' -d @-"
        )
        ssh_cmd = [
            ssh_exe, "-n", "-o", "ConnectTimeout=20", "-o", "BatchMode=yes",
            "-o", "ServerAliveInterval=5", "-o", f"UserKnownHostsFile={known_hosts}",
            "-o", "IdentitiesOnly=yes", "-i", str(identity),
            "daniel@192.168.1.102", command,
        ]
        last = ""
        for attempt in range(5):
            result = subprocess.run(
                ssh_cmd, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=210)
            data = extract_json_object(result.stdout)
            text = str((data or {}).get("text") or "").strip()
            if text:
                return text
            last = (result.stderr or result.stdout)[-500:]
            if attempt < 4:
                time.sleep(6)
        raise RuntimeError(f"遠端 v9 生成連續失敗：{last}")


def call_student(problem: dict, scenario: str, mode: str,
                 transcript: list[dict], tutor_reply: str) -> dict:
    """取得符合本輪受控模式的 GPT-OSS 120B 學生回覆。"""
    prompt = build_student_prompt(problem, scenario, mode, transcript, tutor_reply)
    raw = ""
    for attempt in range(3):
        print(f"[student] scenario={scenario} mode={mode} attempt={attempt + 1}", flush=True)
        raw = call_agy(STUDENT_MODEL, prompt)
        data = extract_json_object(raw)
        if student_output_compliant(mode, data):
            return {
                "student_message": str(data["student_message"]).strip(),
                "behavior": str(data["behavior"]).strip(),
            }
        prompt += "\n上一次輸出不符合受控模式，請修正並只輸出合法 JSON。"
    raise RuntimeError(f"GPT-OSS 學生未遵守 {mode}：{raw[-500:]}")


def fresh_turn_diagnostic(previous: object, current: object):
    """只回傳本輪新建的診斷物件；沿用舊 state 的同一物件視為不適用。"""
    return None if current is previous else current


def run_scenario(problem: dict, scenario: str, max_turns: int = 24) -> dict:
    """執行一段從提示到全文審閱結案的完整真實 driver 對話。"""
    from tutor_driver import TutorDriver

    class RemoteTutorDriver(RemoteTutorDriverMixin, TutorDriver):
        pass

    driver = RemoteTutorDriver(
        tok=object(), model=object(), problem=dict(problem),
        backstop=True, verify_then_generate=True)
    transcript: list[dict] = []
    turns: list[dict] = []
    control = {"misconception_used": False, "flawed_proof_submitted": False}
    tutor_reply = ""

    for turn_index in range(1, max_turns + 1):
        phase_before = str(driver.state.get("phase") or "guide")
        if phase_before == "closed":
            break
        mode_state = dict(control)
        mode_state["active_issue"] = driver.state.get("active_issue") or ""
        mode = choose_student_mode(
            scenario, turn_index, phase_before, tutor_reply, mode_state)
        student = call_student(problem, scenario, mode, transcript, tutor_reply)
        if mode == "wrong_step":
            control["misconception_used"] = True
        if mode == "flawed_full_proof":
            control["flawed_proof_submitted"] = True

        previous_pre_verification = driver.state.get("pre_generation_verification")
        previous_guide_review = driver.state.get("guide_reply_review")
        previous_walkthrough_review = driver.state.get("walkthrough_review")
        started = time.time()
        if turn_index == 1:
            tutor_reply = driver.start(opener=student["student_message"])
        else:
            tutor_reply = driver.step(student["student_message"])
        tutor_latency = round(time.time() - started, 3)
        state = driver.turn_state_summary()
        last_log = driver.state["turns"][-1] if driver.state.get("turns") else None
        row = {
            "turn": turn_index,
            "level": last_log.level if last_log else None,
            "phase_before": phase_before,
            "phase": state.get("phase"),
            "student_mode": mode,
            "student_behavior": student["behavior"],
            "student": student["student_message"],
            "tutor": tutor_reply,
            "tutor_latency_seconds": tutor_latency,
            "state": state,
            "pre_generation_verification": fresh_turn_diagnostic(
                previous_pre_verification,
                driver.state.get("pre_generation_verification")),
            "guide_review": fresh_turn_diagnostic(
                previous_guide_review, driver.state.get("guide_reply_review")),
            "walkthrough_review": fresh_turn_diagnostic(
                previous_walkthrough_review,
                driver.state.get("walkthrough_review")),
        }
        turns.append(row)
        transcript.extend([
            {"role": "student", "text": student["student_message"]},
            {"role": "tutor", "text": tutor_reply},
        ])
        print(
            f"[{scenario} turn {turn_index}] level={row['level']} "
            f"phase={phase_before}->{row['phase']} mode={mode}\n"
            f"Student: {row['student']}\nTutor: {row['tutor']}", flush=True)

    final_phase = str(driver.state.get("phase") or "")
    assessment = assess_scenario(scenario, turns, final_phase)
    return {
        "scenario": scenario,
        "turns": turns,
        "final_phase": final_phase,
        "phase_report": driver.phase_transition_report(),
        "assessment": assessment,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--scenario", choices=SCENARIOS)
    parser.add_argument(
        "--resume", action="store_true",
        help="保留輸出檔中已通過的情境，只重跑缺少或未通過的情境")
    args = parser.parse_args(argv)

    statements = extract_unique_problem_statements(args.source)
    if not statements:
        raise RuntimeError(f"來源檔沒有 Custom problem：{args.source}")
    if len(statements) != 1:
        raise RuntimeError(f"預期一個唯一題目，實得 {len(statements)} 個")
    install_agy_review_backend()
    problem = build_limit_problem(statements[0])
    dialogues: list[dict] = []
    if args.resume and args.output.exists():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        dialogues = list(previous.get("dialogues") or [])
    if args.scenario:
        selected = (args.scenario,)
    elif args.resume:
        passed = {
            row.get("scenario")
            for row in dialogues
            if row.get("assessment", {}).get("passed") is True
        }
        selected = tuple(name for name in SCENARIOS if name not in passed)
    else:
        selected = SCENARIOS
    for scenario in selected:
        dialogues = merge_dialogues(dialogues, [run_scenario(problem, scenario)])
        partial = {
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "source_file": args.source.name,
            "source_occurrences": 3,
            "unique_problem_count": len(statements),
            "assistant": "Qwen3-4B-Instruct-2507 + qlora_adapter_v9 on lab RTX 4090 GPU1",
            "student": f"agy {STUDENT_MODEL}",
            "math_reviewer": f"agy {REVIEW_MODEL}",
            "dialogues": dialogues,
        }
        partial["validity"] = validate_evaluation(dialogues)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8")
        args.output.with_suffix(".md").write_text(render_markdown(partial), encoding="utf-8")
    print(f"RESULT_FILE={args.output}", flush=True)
    validity = validate_evaluation(dialogues)
    return 0 if (args.scenario or validity["valid"]) and all(
        item["assessment"]["passed"] for item in dialogues) else 1


if __name__ == "__main__":
    raise SystemExit(main())
