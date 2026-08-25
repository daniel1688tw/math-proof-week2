# -*- coding: utf-8 -*-
"""受控的學生語意分類與持久 phase 事件路由。

Thinking 模型只描述學生當輪的語意事實；持久 phase 只能由
``apply_phase_event`` 依合法事件矩陣更新。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Callable


INTENTS = {
    "full_proof_submission", "local_revision", "show_attempt",
    "demand_full_answer", "request_hint", "understood_whole_proof",
    "understood_single_step", "stuck", "challenge_or_missed_review",
    "post_completion", "ordinary", "uncertain",
}
SCOPES = {"whole_proof", "single_step", "conversation", "unknown"}
REQUESTED_WRITERS = {"tutor", "student", "none", "uncertain"}
LEARNING_STATES = {
    "stuck", "partial_progress", "progressing", "active_clarification",
    "not_applicable", "uncertain",
}
PHASES = {"guide", "walkthrough", "review", "closed"}
PHASE_EVENTS = {
    "STUCK_LIMIT_REACHED", "WALKTHROUGH_COMPLETED", "READINESS_PASSED",
    "FULL_PROOF_SUBMITTED", "REVIEW_PASSED", "REVIEW_REOPEN_REQUESTED",
    "RESET",
}
REVIEW_STATUSES = {
    "awaiting_submission", "checking", "correcting", "awaiting_clean",
    "rechecking", "unavailable",
}
TURN_ACTIONS = {
    "normal_guide", "respond_attempt", "answer_clarification",
    "refuse_tutor_write", "peer_reflect", "post_completion_reply",
    "review_local_revision", "walkthrough_answer",
}
CONFIDENCE_THRESHOLD = 0.75


def _phase_state_snapshot(state: dict) -> dict:
    """擷取事件前後快照，不把整份對話與診斷歷史複製進去。"""
    keys = (
        "phase", "review_status", "stuck_count", "walk_idx", "walk_lang",
        "walk_active", "review_active", "awaiting_clean_proof", "done_closed",
        "writeup_asked",
    )
    return {key: state.get(key) for key in keys}


def _sync_compatibility_flags(state: dict) -> None:
    """第一版保留舊旗標作相容鏡射；邏輯不得再以它們路由。"""
    phase = state.get("phase")
    status = state.get("review_status")
    state["walk_active"] = phase == "walkthrough"
    state["done_closed"] = phase == "closed"
    state["review_active"] = phase == "review" and status == "correcting"
    state["awaiting_clean_proof"] = phase == "review" and status == "awaiting_clean"
    state["writeup_asked"] = bool(
        phase == "review" and status == "awaiting_submission")


def normalize_persisted_state(state: dict) -> dict:
    """將舊快照一次性映射為四種 phase，回傳同一個 dict。"""
    old_phase = state.get("phase")
    if state.get("done_closed") or old_phase == "closed":
        phase = "closed"
        status = None
    elif (state.get("review_active") or state.get("awaiting_clean_proof")
          or old_phase in {"review", "writeup_request"}):
        phase = "review"
        old_status = state.get("review_status")
        status_map = {
            "issues": "correcting", "clear": "checking", "reviewing": "checking",
            "reviewing_merged": "rechecking", "local_judge_unavailable": "unavailable",
            "local_merge_unavailable": "unavailable", "local_correct": "correcting",
            "pass": None, "final_pass": None,
        }
        if str(old_status).startswith("local_") and old_status not in status_map:
            status = "correcting"
        else:
            status = status_map.get(old_status, old_status)
        if old_phase == "writeup_request":
            status = "awaiting_submission"
        elif status not in REVIEW_STATUSES:
            status = ("awaiting_clean" if state.get("awaiting_clean_proof")
                      else "correcting" if state.get("review_active")
                      else "awaiting_submission")
    elif state.get("walk_active") or old_phase == "walkthrough":
        phase = "walkthrough"
        status = None
    else:
        phase = "guide"
        status = None
    state["phase"] = phase
    state["review_status"] = status
    state["mode"] = "peer" if state.get("mode") == "peer" else state.get("mode", "tutor")
    _sync_compatibility_flags(state)
    return state


def apply_phase_event(state: dict, event: str, *, source: str = "controller") -> str:
    """唯一持久 phase 轉移入口。非法事件只記錄拒絕，不改 phase。"""
    normalize_persisted_state(state)
    previous = state["phase"]
    before = _phase_state_snapshot(state)
    accepted = False
    reject_reason = "event_not_allowed_from_current_phase"

    if event not in PHASE_EVENTS:
        reject_reason = "unknown_event"
    elif event == "RESET":
        accepted = True
        state.update(phase="guide", review_status=None, stuck_count=0, walk_idx=0)
        for key in (
            "walk_lang", "walk_feedback", "review_issues", "review_issue_idx",
            "review_base_proof", "current_proof_draft", "review_last_full_proof",
            "review_corrections", "review_had_issues",
        ):
            state.pop(key, None)
    elif previous == "guide" and event == "STUCK_LIMIT_REACHED":
        if int(state.get("stuck_count") or 0) < 3:
            reject_reason = "stuck_limit_not_reached"
        else:
            accepted = True
            state.update(phase="walkthrough", review_status=None, walk_idx=0,
                         stuck_count=0)
    elif previous == "guide" and event == "READINESS_PASSED":
        accepted = True
        state.update(phase="review", review_status="awaiting_submission",
                     stuck_count=0)
    elif previous == "walkthrough" and event == "WALKTHROUGH_COMPLETED":
        accepted = True
        state.update(phase="review", review_status="awaiting_submission",
                     stuck_count=0)
        state.pop("walk_lang", None)
    elif previous == "review" and event == "FULL_PROOF_SUBMITTED":
        accepted = True
        status = ("rechecking" if state.get("review_status") == "awaiting_clean"
                  else "checking")
        state.update(phase="review", review_status=status, stuck_count=0)
    elif previous == "review" and event == "REVIEW_PASSED":
        accepted = True
        state.update(phase="closed", review_status=None, stuck_count=0)
    elif previous == "closed" and event == "REVIEW_REOPEN_REQUESTED":
        if not (state.get("current_proof_draft") or state.get("review_last_full_proof")):
            reject_reason = "no_recent_full_proof"
        else:
            accepted = True
            state.update(phase="review", review_status="rechecking", stuck_count=0)

    _sync_compatibility_flags(state)
    after = _phase_state_snapshot(state)
    state.setdefault("phase_events", []).append({
        "previous_phase": previous,
        "event": event,
        "event_source": source,
        "next_phase": state["phase"],
        "accepted": accepted,
        "reject_reason": "" if accepted else reject_reason,
        "state_before": before,
        "state_after": after,
    })
    return state["phase"]


@dataclass
class StudentStateDecision:
    phase: str | None
    intent: str
    learning_state: str
    turn_action: str = "normal_guide"
    answers_current_question: bool | None = None
    has_actionable_math: bool = False
    advances_solution: bool | None = None
    requested_writer: str = "none"
    phase_confidence: float = 1.0
    stuck_confidence: float = 1.0
    evidence: str = ""
    source: str = "deterministic"

    def to_dict(self) -> dict:
        return asdict(self)


def update_stuck_count(count: int, learning_state: str, *,
                       answers_current_question: bool | None = None,
                       has_actionable_math: bool = False,
                       advances_solution: bool | None = None) -> int:
    """依「能否繼續參與推導」更新連續卡住次數。

    ``advances_solution`` 只描述是否提出新的相關內容，不判數學正誤；錯誤但
    可審閱的嘗試仍會中斷連續卡住。純重複、離題或不確定則保留原計數。
    """
    current = max(0, int(count))
    if has_actionable_math or answers_current_question is True:
        return 0
    if learning_state == "stuck":
        return current + 1
    if learning_state in {
        "partial_progress", "progressing", "active_clarification",
        "not_applicable",
    }:
        return 0
    return current                  # uncertain／中性無進展：不加一，也不抹掉既有計數


def _decision(phase: str | None, intent: str, learning: str, *,
              turn_action: str | None = None,
              source: str = "deterministic", evidence: str = "",
              answers_current_question: bool | None = None,
              has_actionable_math: bool | None = None,
              advances_solution: bool | None = None,
              requested_writer: str = "none",
              phase_confidence: float = 1.0,
              stuck_confidence: float = 1.0) -> StudentStateDecision:
    if has_actionable_math is None:
        has_actionable_math = learning in {
            "partial_progress", "progressing", "active_clarification",
        }
    if answers_current_question is None:
        if learning in {"partial_progress", "progressing"}:
            answers_current_question = True
        elif learning in {"stuck", "active_clarification"}:
            answers_current_question = False
    if advances_solution is None:
        if learning in {"partial_progress", "progressing"}:
            advances_solution = True
        elif learning in {"stuck", "active_clarification"}:
            advances_solution = False
    if turn_action is None:
        turn_action = "normal_guide"
    persistent_phase = phase if phase in PHASES else "guide"
    return StudentStateDecision(
        phase=persistent_phase, intent=intent, learning_state=learning,
        turn_action=(turn_action if turn_action in TURN_ACTIONS else "normal_guide"),
        answers_current_question=answers_current_question,
        has_actionable_math=bool(has_actionable_math),
        advances_solution=advances_solution,
        requested_writer=(requested_writer
                          if requested_writer in REQUESTED_WRITERS else "uncertain"),
        source=source, evidence=evidence,
        phase_confidence=phase_confidence,
        stuck_confidence=stuck_confidence,
    )


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _parse_json_object(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw,
                 flags=re.I | re.S).strip()
    # Thinking 模型可能先輸出推理文字，也可能在 evidence 中逐字引用 LaTeX。
    # 貪婪的 ``\{.*\}`` 會把多個物件黏在一起；而 ``\varepsilon`` 之類若未
    # 依 JSON 規格雙寫反斜線，json.loads 也會整份失敗。用字串感知的括號掃描
    # 逐一擷取物件，並只修補「不是合法 JSON escape」的反斜線。
    candidates = [raw]
    depth = 0
    start = None
    in_string = False
    escaped = False
    for i, ch in enumerate(raw):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(raw[start:i + 1])
                start = None
    fallback_object = None
    for candidate in candidates:
        repaired = re.sub(
            r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', candidate)
        for attempt in (candidate, repaired):
            try:
                value = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                if {"intent", "scope", "learning_state"}.issubset(value):
                    return value
                if fallback_object is None:
                    fallback_object = value
    return fallback_object


def _normalize_evidence_anchor(text: str) -> str:
    """只忽略排版差異，仍要求 evidence 可定位回學生原文。"""
    value = (text or "").casefold()
    value = re.sub(r"\$|`|\\\(|\\\)|\\\[|\\\]", "", value)
    value = re.sub(r"[\s，。、！？；：,.!?;:'\"“”‘’（）()]", "", value)
    return value


def _validate_model_result(raw: dict | None, student_text: str) -> dict | None:
    if not isinstance(raw, dict):
        return None
    intent = str(raw.get("intent") or "").strip()
    scope = str(raw.get("scope") or "").strip()
    learning = str(raw.get("learning_state") or "").strip()
    requested_writer = str(raw.get("requested_writer") or "").strip()
    evidence = str(raw.get("evidence") or "").strip()
    if (intent not in INTENTS or scope not in SCOPES
            or learning not in LEARNING_STATES
            or requested_writer not in REQUESTED_WRITERS):
        return None
    # evidence 是防止模型脫離學生原文猜測的錨點。允許空白、標點、數學定界符
    # 差異，但不接受語意改寫或杜撰內容。
    exact_anchor = bool(
        evidence and evidence.casefold() in (student_text or "").casefold())
    normalized_evidence = _normalize_evidence_anchor(evidence)
    normalized_student = _normalize_evidence_anchor(student_text)
    normalized_anchor = bool(
        normalized_evidence and normalized_evidence in normalized_student)
    if not exact_anchor and not normalized_anchor:
        return None
    phase_confidence = _safe_float(
        raw.get("phase_confidence", raw.get("confidence")))
    stuck_confidence = _safe_float(
        raw.get("stuck_confidence", raw.get("confidence")))
    answers_current_question = raw.get("answers_current_question")
    has_actionable_math = raw.get("has_actionable_math")
    advances_solution = raw.get("advances_solution")
    if (not isinstance(answers_current_question, bool)
            or not isinstance(has_actionable_math, bool)
            or not isinstance(advances_solution, bool)):
        return None
    return {
        "intent": intent,
        "scope": scope,
        "learning_state": learning,
        "phase_confidence": phase_confidence,
        "stuck_confidence": stuck_confidence,
        "answers_current_question": answers_current_question,
        "has_actionable_math": has_actionable_math,
        "advances_solution": advances_solution,
        "requested_writer": requested_writer,
        "evidence": evidence,
    }


CLASSIFIER_SYSTEM = """你是數學助教系統的幕後語意分類器。你只描述學生訊息的語意事實；
最終 phase 與 stuck_count 由 Driver 的固定規則決定。
不要解題、不要評斷答案正確性、不要提供教學回覆。只輸出一個 JSON 物件。

intent 只能是：full_proof_submission, local_revision, show_attempt,
demand_full_answer, request_hint, understood_whole_proof,
understood_single_step, stuck, challenge_or_missed_review, post_completion,
ordinary, uncertain。
scope 只能是：whole_proof, single_step, conversation, unknown。
requested_writer 只能是：tutor, student, none, uncertain。
learning_state 只能是：stuck, partial_progress, progressing,
active_clarification, not_applicable, uncertain。

判準：
1. 「要證明……」通常只是重述目標，不是完整交稿。完整證明須有多個相連推理、依據與結論。
2. 「我懂了」若未明說整個證明，預設只表示理解目前一步。
3. 要提示不等於要求完整答案；只有明確索取完整解答才是 demand_full_answer。
4. 答錯但有與上一問相關的實質推理，是 partial_progress，不是 stuck。
5. 說不確定但提出具體下一步，也是 partial_progress。
6. 明確詢問某個符號、前提、定理或推理理由，是 active_clarification。
7. 新公式若只是抄寫、重複或無關，不能因此判為 progressing。
8. 只回答「是／否／正／負」時要依上一問判斷；若上一問正好只問此事，視為 progressing。
9. 不得因學生說「得證」而判定系統已 closed。
10. evidence 必須逐字引用學生訊息中的短片段；資訊不足就輸出 uncertain。
11. 卡住判斷必須依整句語意與上一個 Tutor 問題，不得只搜尋固定關鍵詞。
    只要學生以任何說法清楚表達無法回答、無法繼續或沒有可延續想法，且未提出
    相關下一步，就判 intent=stuck、learning_state=stuck。
12. 沒有命中本地詞表不代表學生正在進展。只有實際回答上一問、提出相關下一步，
    或提出具體釐清問題，才能判 progressing、partial_progress 或 active_clarification。
13. 錯誤但相關的作答是 partial_progress；單純換句話表達困惑、逃避作答或表示
    腦中無法接續，則是 stuck。不要依答案正確與否判斷卡住。
14. 必須結合 last_tutor_question。若上一問只要求一個符號、數值、式子或簡短結論，
    學生用一個詞或一個公式直接回答，也可判 progressing；不能因回答很短就判 uncertain。
15. 學生表示整體推理已掌握，或明確要求 Tutor 現在請自己提交完整證明，判為
    understood_whole_proof，而不是 demand_full_answer。後者只指要求 Tutor 代寫答案。
16. 學生在多輪推導後說「這就證明了目標」時，若語意是在收束整體思路，判為
    understood_whole_proof；只有目前這一則訊息本身具完整論證，才判 full_proof_submission。
17. evidence 優先引用不含 LaTeX 的原文短片段；若必須引用 LaTeX，反斜線必須依
    JSON 規格正確跳脫。不可省略 evidence。
18. 判斷完整證明相關意圖時，必須辨認「誰要寫」：要求 Tutor 給、寫、展示答案或
    證明架構是 demand_full_answer；要求 Tutor 請學生自己提交，才是
    understood_whole_proof。學生說想先看證明「再理解」，不表示目前已理解。
19. walkthrough 中的長訊息必須依目前訊息本身判斷：若已從前提連續推到題目結論，
    可判 full_proof_submission/whole_proof；若只詳細回答當前一步，仍是 single_step。
20. 「證明：」「proof:」後面若只是重述題目結論，這是學生的作答內容，
    不是要求 Tutor 代寫；只有訊息真正要求 Tutor 提供答案才判 demand_full_answer。
21. 完成後，只要學生詢問、質疑或陳述最近完整證明是否仍有錯誤或漏審，
    不論疑問、肯定、否定或委婉語氣，都判 challenge_or_missed_review；
    純致謝、心得或與證明正誤無關的延伸探索才判 post_completion。
22. 純社交、自我感受或與他人比較，若沒有回答上一個數學問題也沒有新的
    數學推理，不得因「我覺得」這類句型就判 show_attempt。
23. answers_current_question 表示學生是否實際回應 last_tutor_question。
24. has_actionable_math 表示是否包含可繼續審閱、計算或推導的具體數學內容；
    即使內容可能算錯，只要具體且與當前工作相關仍為 true。
25. advances_solution 表示是否提出新的、與解題相關的步驟或關係；只重複舊內容、
    離題或純社交為 false。這個欄位不判定數學正誤。
26. 「沒進展」不等於「卡住」：純重複或離題但沒有表示無法繼續時，使用 uncertain；
    只有明確無法回答／繼續，且沒有可操作內容或具體澄清問題時才是 stuck。
27. requested_writer 只描述目前訊息要求「誰」寫完整證明／解答：要求 Tutor 提供是
    tutor；要求系統叫學生自己提交是 student；沒有這個要求是 none；無法判定才是
    uncertain。這與學生是否已經準備好交稿是兩回事。

JSON 欄位固定為 intent, scope, learning_state, answers_current_question,
has_actionable_math, advances_solution, requested_writer, phase_confidence, stuck_confidence,
evidence；三個語意欄位必須是 true 或 false，兩個 confidence 都是 0 到 1。"""


def _model_classify(student_text: str, context: dict,
                    classifier: Callable[[dict], dict | None] | None = None) -> dict | None:
    payload = {
        "last_tutor_question": str(context.get("last_tutor_question") or "")[-1200:],
        "previous_student_message": str(context.get("previous_student_text") or "")[-800:],
        "student_message": student_text,
        "current_phase": context.get("phase"),
        "requested_writer_hint": context.get("requested_writer", "none"),
        "stuck_count": int(context.get("stuck_count") or 0),
        "features": {
            key: bool(context.get(key)) for key in (
                "explicit_stuck", "strong_stuck", "has_new_math",
                "asks_specific_question", "repeats_prior_math", "demand",
                "attempt", "attempt_content", "understood", "draft_signal",
                "challenge", "assertive_challenge",
                "direct_response_candidate", "goal_restatement",
                "missed_review", "nonassertive_review_confirmation",
            )
        },
    }
    if classifier is not None:
        try:
            raw = classifier(payload)
            # 測試或外部注入的舊分類器可逐步遷移；正式 Thinking 呼叫仍必須輸出
            # 三個結構化語意欄位，否則會觸發下面的格式重試／保守 fallback。
            if isinstance(raw, dict):
                learning = str(raw.get("learning_state") or "")
                raw.setdefault(
                    "answers_current_question",
                    learning in {"partial_progress", "progressing"})
                raw.setdefault(
                    "has_actionable_math",
                    learning in {"partial_progress", "progressing",
                                 "active_clarification"})
                raw.setdefault(
                    "advances_solution",
                    learning in {"partial_progress", "progressing"})
                raw.setdefault(
                    "requested_writer",
                    str(context.get("requested_writer") or "none"))
            parsed = _validate_model_result(raw, student_text)
            return _normalize_writer_intent(parsed)
        except Exception:
            return None

    try:
        try:
            from .review_backstop import _chat_content
        except ImportError:
            from review_backstop import _chat_content
    except ImportError:
        return None

    prompt = json.dumps(payload, ensure_ascii=False, indent=2)
    timeout = max(15, int(os.environ.get("PHASE_ROUTER_TIMEOUT", "90")))
    best = None
    for attempt in range(2):              # 一次呼叫＋最多一次格式／低信心重試
        user = prompt if attempt == 0 else (
            prompt + "\n\n請重新核對上一個 Tutor 問題、誰要提供完整證明，以及學生訊息的範圍。"
            "只輸出指定 JSON；三個布林語意欄位不可省略，evidence 必須逐字取自 "
            "student_message；不確定就明確輸出 uncertain。")
        content = _chat_content(CLASSIFIER_SYSTEM, user, timeout,
                                num_predict=3072, temperature=0.05)
        parsed = _normalize_writer_intent(
            _validate_model_result(_parse_json_object(content or ""), student_text))
        if parsed is not None:
            if (best is None
                    or max(parsed["phase_confidence"], parsed["stuck_confidence"])
                    > max(best["phase_confidence"], best["stuck_confidence"])):
                best = parsed
            phase_changing = parsed["intent"] in {
                "full_proof_submission", "demand_full_answer",
                "understood_whole_proof", "challenge_or_missed_review",
            }
            if not (attempt == 0 and phase_changing
                    and parsed["phase_confidence"] < CONFIDENCE_THRESHOLD):
                return parsed
    return best


def _normalize_writer_intent(parsed: dict | None) -> dict | None:
    """用「誰要寫」校正高風險意圖，不靠措辭列舉。

    Thinking 若把「請要求我自己寫」誤標成索取答案，不能讓它選到 refuse_tutor_write；
    反過來，要求 Tutor 提供整份解答也不能被 local_revision 等標籤放過。
    """
    if parsed is None:
        return None
    result = dict(parsed)
    writer = result.get("requested_writer")
    if writer == "student" and result.get("intent") == "demand_full_answer":
        result["intent"] = "understood_whole_proof"
    elif (writer == "tutor" and result.get("scope") == "whole_proof"
          and result.get("intent") in {
              "local_revision", "understood_whole_proof", "ordinary", "uncertain",
          }):
        result["intent"] = "demand_full_answer"
    return result


def _context_phase(context: dict) -> str:
    """只讀正規化當前工作流；舊旗標僅用於舊呼叫者相容。"""
    current = context.get("phase")
    if current in PHASES:
        return current
    if context.get("done_closed") or current == "closed":
        return "closed"
    if (context.get("review_active") or context.get("awaiting_clean_proof")
            or current in {"review", "writeup_request"}):
        return "review"
    if context.get("walk_active") or current == "walkthrough":
        return "walkthrough"
    return "guide"


def _action_for_intent(intent: str, phase: str) -> str:
    if phase == "closed":
        return "post_completion_reply"
    if phase == "walkthrough":
        return "walkthrough_answer"
    if intent == "demand_full_answer":
        return "refuse_tutor_write"
    if intent in {"show_attempt", "local_revision", "full_proof_submission"}:
        return "review_local_revision" if phase == "review" else "respond_attempt"
    if intent == "request_hint":
        return "answer_clarification"
    return "normal_guide"


def route_student_state(student_text: str, context: dict, *,
                        thinking_enabled: bool = True,
                        classifier: Callable[[dict], dict | None] | None = None
                        ) -> StudentStateDecision:
    """只分類當輪語意與 action，絕不用學生文字直接切換 phase。"""
    text = (student_text or "").strip()
    phase = _context_phase(context)

    # 持久工作流鎖：分類器可以說明當輪語意，但回傳的
    # phase 始終是目前 phase，事件由 Controller 另行驗證。
    if context.get("peer"):
        intent = "challenge_or_missed_review" if context.get("challenge") else "ordinary"
        action = "peer_reflect" if context.get("challenge") else "normal_guide"
        return _decision("guide", intent, "not_applicable", turn_action=action,
                         source="state_lock", evidence=text)

    if phase == "walkthrough":
        if context.get("explicit_full_proof"):
            return _decision(
                phase, "understood_single_step", "not_applicable",
                turn_action="walkthrough_answer", source="state_lock", evidence=text)
        if context.get("demand"):
            return _decision(
                phase, "demand_full_answer", "not_applicable",
                turn_action="refuse_tutor_write", requested_writer="tutor",
                source="state_lock", evidence=text)
        return _decision(
            phase, "understood_single_step", "not_applicable",
            turn_action="walkthrough_answer", source="state_lock", evidence=text)

    if phase == "review":
        if context.get("demand"):
            return _decision(
                phase, "demand_full_answer", "not_applicable",
                turn_action="refuse_tutor_write", requested_writer="tutor",
                source="state_lock", evidence=text)
        if (context.get("explicit_full_proof")
                or (context.get("claim_done") and context.get("complete_shape"))):
            return _decision(
                phase, "full_proof_submission", "not_applicable",
                turn_action="review_local_revision", source="state_lock", evidence=text)
        return _decision(
            phase, "local_revision", "not_applicable",
            turn_action="review_local_revision", source="state_lock", evidence=text)

    if phase == "closed":
        direct_reopen = bool(
            context.get("assertive_challenge") or context.get("missed_review")
            or context.get("nonassertive_review_confirmation") or context.get("challenge"))
        if direct_reopen and context.get("has_recent_proof"):
            return _decision(
                phase, "challenge_or_missed_review", "not_applicable",
                turn_action="post_completion_reply", source="state_lock", evidence=text)
        if thinking_enabled or classifier:
            judged = _model_classify(text, context, classifier)
            if (judged is not None
                    and judged["intent"] == "challenge_or_missed_review"
                    and judged["phase_confidence"] >= CONFIDENCE_THRESHOLD
                    and context.get("has_recent_proof")):
                return _decision(
                    phase, judged["intent"], "not_applicable",
                    turn_action="post_completion_reply", source="thinking",
                    evidence=judged["evidence"],
                    answers_current_question=judged.get("answers_current_question"),
                    has_actionable_math=judged.get("has_actionable_math"),
                    advances_solution=judged.get("advances_solution"),
                    phase_confidence=judged["phase_confidence"],
                    stuck_confidence=judged["stuck_confidence"])
        return _decision(
            phase, "post_completion", "not_applicable",
            turn_action="post_completion_reply", source="state_lock", evidence=text)

    # guide 只處理引導與作答；完整交稿必須等 Controller 先以
    # READINESS_PASSED 進入 review/awaiting_submission。
    if context.get("explicit_full_proof"):
        return _decision(
            phase, "show_attempt", "partial_progress",
            turn_action="respond_attempt", source="deterministic",
            answers_current_question=True, has_actionable_math=True,
            advances_solution=True, evidence=text)
    if context.get("student_requests_writeup"):
        return _decision(
            phase, "understood_whole_proof", "progressing",
            turn_action="normal_guide", requested_writer="student",
            answers_current_question=False, has_actionable_math=False,
            advances_solution=False, evidence=text)
    if context.get("demand"):
        return _decision(
            phase, "demand_full_answer", "not_applicable",
            turn_action="refuse_tutor_write", requested_writer="tutor", evidence=text)
    if context.get("claim_done") and context.get("complete_shape"):
        return _decision(
            phase, "show_attempt", "partial_progress",
            turn_action="respond_attempt", answers_current_question=True,
            has_actionable_math=True, advances_solution=True, evidence=text)
    if context.get("understood_whole"):
        return _decision(
            phase, "understood_whole_proof", "progressing",
            turn_action="normal_guide", advances_solution=False,
            requested_writer=str(context.get("requested_writer") or "none"), evidence=text)
    if (context.get("asks_specific_question")
            and not context.get("attempt_content")
            and not context.get("strong_stuck")
            and not (context.get("attempt") and context.get("has_new_math"))):
        return _decision(
            phase, "request_hint", "active_clarification",
            turn_action="answer_clarification", evidence=text)
    if (context.get("attempt_content")
            or (context.get("attempt") and context.get("has_new_math")
                and not context.get("explicit_stuck"))
            or (context.get("direct_response_candidate")
                and not context.get("explicit_stuck"))):
        return _decision(
            phase, "show_attempt", "partial_progress",
            turn_action="respond_attempt", evidence=text)
    mixed_attempt_and_stuck = bool(
        context.get("attempt") and context.get("explicit_stuck")
        and not context.get("attempt_content") and not context.get("has_new_math"))
    if (context.get("strong_stuck") or context.get("explicit_stuck")) \
            and not mixed_attempt_and_stuck \
            and not context.get("has_new_math") and not context.get("attempt_content"):
        return _decision(
            phase, "stuck", "stuck", turn_action="normal_guide", evidence=text)

    if mixed_attempt_and_stuck:
        base = _decision(
            phase, "uncertain", "uncertain", turn_action="normal_guide",
            source="fallback", evidence=text, phase_confidence=0.0,
            stuck_confidence=0.0)
    elif context.get("understood") and not context.get("explicit_stuck"):
        base = _decision(
            phase, "understood_single_step", "progressing",
            turn_action="normal_guide", evidence=text)
    elif context.get("has_new_math") and not context.get("explicit_stuck"):
        base = _decision(
            phase, "show_attempt", "partial_progress",
            turn_action="respond_attempt", evidence=text)
    else:
        base = _decision(
            phase, "uncertain", "uncertain", turn_action="normal_guide",
            source="fallback", evidence=text, phase_confidence=0.0,
            stuck_confidence=0.0)

    ambiguous = bool(
        (context.get("explicit_stuck")
         and (context.get("has_new_math") or context.get("attempt_content")))
        or mixed_attempt_and_stuck
        or (context.get("understood") and not context.get("understood_whole"))
        or (context.get("draft_signal") and not context.get("explicit_full_proof"))
        or context.get("repeats_prior_math") or context.get("goal_restatement")
        or base.intent == "uncertain")
    if not ambiguous or (not thinking_enabled and classifier is None):
        if ambiguous:
            base.source = "fallback"
            if context.get("goal_restatement"):
                base.intent = "uncertain"
                base.learning_state = "uncertain"
                base.answers_current_question = None
                base.has_actionable_math = False
                base.advances_solution = False
            if (context.get("explicit_stuck")
                    and (context.get("has_new_math") or context.get("attempt_content"))):
                base.learning_state = "uncertain"
        return base

    judged = _model_classify(text, context, classifier)
    if judged is None:
        base.source = "fallback"
        base.phase_confidence = 0.0
        base.stuck_confidence = 0.0
        return base

    intent = base.intent
    if judged["phase_confidence"] >= CONFIDENCE_THRESHOLD:
        intent = judged["intent"]
    # Thinking 只描述訊息外形；guide 的產品政策仍不接受交稿事件。
    if intent == "full_proof_submission":
        intent = "show_attempt"
    learning = base.learning_state
    if judged["stuck_confidence"] >= CONFIDENCE_THRESHOLD:
        learning = judged["learning_state"]
    if learning == "not_applicable":
        learning = base.learning_state
    return _decision(
        phase, intent, learning, turn_action=_action_for_intent(intent, phase),
        source="thinking", evidence=judged["evidence"],
        answers_current_question=judged.get("answers_current_question"),
        has_actionable_math=judged.get("has_actionable_math"),
        advances_solution=judged.get("advances_solution"),
        requested_writer=judged.get("requested_writer", "none"),
        phase_confidence=judged["phase_confidence"],
        stuck_confidence=judged["stuck_confidence"])
