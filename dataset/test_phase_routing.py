# -*- coding: utf-8 -*-
"""四種持久 phase、事件矩陣與 Controller 主動交稿的 Tier 0 測試。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ["REVIEW_BACKSTOP"] = "0"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from phase_router import (  # noqa: E402
    PHASES,
    PHASE_EVENTS,
    apply_phase_event,
    normalize_persisted_state,
    route_student_state,
    update_stuck_count,
)
from tutor_driver import TutorDriver, WRITEUP_FALLBACK  # noqa: E402


FAIL: list[str] = []


def check(name: str, condition: bool) -> None:
    print(("  OK " if condition else "  FAIL ") + name)
    if not condition:
        FAIL.append(name)


def state(phase: str = "guide", status: str | None = None, **extra) -> dict:
    value = {"phase": phase, "review_status": status, "stuck_count": 0}
    value.update(extra)
    normalize_persisted_state(value)
    return value


print("[1] 四 phase 與合法事件矩陣")
cases = (
    (state("guide", stuck_count=3), "STUCK_LIMIT_REACHED", "walkthrough", None),
    (state("guide"), "READINESS_PASSED", "review", "awaiting_submission"),
    (state("walkthrough"), "WALKTHROUGH_COMPLETED", "review", "awaiting_submission"),
    (state("review", "awaiting_submission"), "FULL_PROOF_SUBMITTED", "review", "checking"),
    (state("review", "awaiting_clean"), "FULL_PROOF_SUBMITTED", "review", "rechecking"),
    (state("review", "checking"), "REVIEW_PASSED", "closed", None),
    (state("closed", current_proof_draft="proof"), "REVIEW_REOPEN_REQUESTED", "review", "rechecking"),
)
for initial, event, expected_phase, expected_status in cases:
    apply_phase_event(initial, event, source="test")
    check(f"{event}: {expected_phase}/{expected_status}",
          initial["phase"] == expected_phase
          and initial.get("review_status") == expected_status
          and initial["phase_events"][-1]["accepted"] is True)

reset = state("closed", current_proof_draft="proof", review_issues=[{"x": 1}])
apply_phase_event(reset, "RESET", source="test")
check("RESET 回 guide 並清除工作流狀態",
      reset["phase"] == "guide" and "current_proof_draft" not in reset)


print("[2] 非法轉移與不足條件一律拒絕")
for phase in sorted(PHASES):
    for event in sorted(PHASE_EVENTS - {"RESET"}):
        legal = {
            ("guide", "STUCK_LIMIT_REACHED"), ("guide", "READINESS_PASSED"),
            ("walkthrough", "WALKTHROUGH_COMPLETED"),
            ("review", "FULL_PROOF_SUBMITTED"), ("review", "REVIEW_PASSED"),
            ("closed", "REVIEW_REOPEN_REQUESTED"),
        }
        if (phase, event) in legal:
            continue
        initial = state(
            phase,
            "checking" if phase == "review" else None,
            current_proof_draft="proof" if phase == "closed" else None,
            stuck_count=3)
        before = initial["phase"]
        apply_phase_event(initial, event, source="illegal-matrix-test")
        check(f"拒絕 {phase} + {event}",
              initial["phase"] == before
              and initial["phase_events"][-1]["accepted"] is False)

not_stuck = state("guide", stuck_count=2)
apply_phase_event(not_stuck, "STUCK_LIMIT_REACHED", source="test")
check("卡住未達門檻不進 walkthrough",
      not_stuck["phase"] == "guide"
      and not_stuck["phase_events"][-1]["reject_reason"] == "stuck_limit_not_reached")

no_proof = state("closed")
apply_phase_event(no_proof, "REVIEW_REOPEN_REQUESTED", source="test")
check("沒有最近全文不得重開審閱", no_proof["phase"] == "closed")


print("[3] 舊快照一次性正規化")
legacy = (
    ({"phase": None}, "guide", None),
    ({"phase": "rectify"}, "guide", None),
    ({"phase": "refuse_leak"}, "guide", None),
    ({"phase": "peer_reflect"}, "guide", None),
    ({"phase": "walkthrough"}, "walkthrough", None),
    ({"phase": "writeup_request"}, "review", "awaiting_submission"),
    ({"phase": "review", "review_active": True}, "review", "correcting"),
    ({"phase": "closed"}, "closed", None),
)
for snapshot, expected_phase, expected_status in legacy:
    old = snapshot.get("phase")
    normalize_persisted_state(snapshot)
    check(f"legacy {old} -> {expected_phase}",
          snapshot["phase"] == expected_phase
          and snapshot.get("review_status") == expected_status)


print("[4] Thinking 只決定當輪 action，不切 phase")


def context(**changes) -> dict:
    base = {
        "phase": "guide", "peer": False, "explicit_full_proof": False,
        "complete_shape": False, "claim_done": False, "demand": False,
        "student_requests_writeup": False, "requested_writer": "none",
        "attempt": False, "attempt_content": False, "has_new_math": False,
        "direct_response_candidate": False, "understood": False,
        "understood_whole": False, "asks_specific_question": False,
        "strong_stuck": False, "explicit_stuck": False,
        "challenge": False, "assertive_challenge": False,
        "missed_review": False, "nonassertive_review_confirmation": False,
        "has_recent_proof": False, "draft_signal": False,
        "repeats_prior_math": False, "goal_restatement": False,
        "last_tutor_question": "下一步？", "previous_student_text": "",
        "stuck_count": 0,
    }
    base.update(changes)
    return base


demand = route_student_state(
    "請直接寫完整證明。", context(demand=True), thinking_enabled=False)
check("索取代寫留在 guide，只設 refuse action",
      demand.phase == "guide" and demand.turn_action == "refuse_tutor_write")

attempt = route_student_state(
    "我想用中值定理。", context(attempt_content=True), thinking_enabled=False)
check("數學嘗試留在 guide，只設 respond action",
      attempt.phase == "guide" and attempt.turn_action == "respond_attempt")

attempt_question = route_student_state(
    "I used the Intermediate Value Theorem. Is this correct?",
    context(attempt=True, has_new_math=True, asks_specific_question=True),
    thinking_enabled=False)
check("帶問號的新數學嘗試優先進 respond_attempt",
      attempt_question.phase == "guide"
      and attempt_question.turn_action == "respond_attempt")

student_request = route_student_state(
    "你應該要求我提交完整證明。",
    context(student_requests_writeup=True, requested_writer="student"),
    thinking_enabled=False)
check("學生要求進交稿不是 phase 事件",
      student_request.phase == "guide"
      and student_request.intent == "understood_whole_proof")

walk_demand = route_student_state(
    "直接給我完整證明。",
    context(phase="walkthrough", demand=True), thinking_enabled=False)
check("walkthrough 中拒絕代寫但不跳出",
      walk_demand.phase == "walkthrough"
      and walk_demand.turn_action == "refuse_tutor_write")

closed_challenge = route_student_state(
    "請重新審閱剛才的證明。",
    context(phase="closed", missed_review=True, has_recent_proof=True),
    thinking_enabled=False)
check("closed 分類器只回報重審意圖，不自行改 phase",
      closed_challenge.phase == "closed"
      and closed_challenge.intent == "challenge_or_missed_review")

unknown = route_student_state("我再想想。", context(), thinking_enabled=False)
check("Thinking unavailable 時 phase 不漂移",
      unknown.phase == "guide" and unknown.learning_state == "uncertain")
check("不確定語意不清掉卡住次數",
      update_stuck_count(2, unknown.learning_state) == 2)


print("[5] Controller 自動偵測引導完畢並主動要求全文")


class _StubModel:
    device = "cpu"


class _ReadyDriver(TutorDriver):
    def _raw_generate(self, msgs, max_new):
        return "這一步有新進展。你能接著處理下一個關鍵連結嗎？"

    def _review_guide_reply(self, reply, level):
        # 此檔只測 phase 路由；避免純邏輯測試連外呼叫引導語意審查服務。
        return {
            "mathematically_correct": True,
            "level_policy_pass": True,
            "introduces_new_proof_idea": False,
            "completes_any_unfinished_step": False,
            "leaks_final_conclusion": False,
            "ready_for_writeup": True,
            "missing_core_step": "",
            "readiness_confidence": 0.99,
            "feedback": "",
        }

    def _judge_walkthrough_answer(self, student_text, step):
        return {"verdict": "correct", "feedback": ""}


STEPS = [
    {"step_id": f"s{i}", "explain": f"第 {i} 步。", "core_idea": f"性質 {i}",
     "check": f"第 {i} 步得到什麼？", "expected_answer": f"結論 {i}"}
    for i in range(1, 4)
]
PROBLEM = {
    "id": "PHASE4", "statement": "證明測試命題。",
    "reference_proof": "依序推得三個結論，故命題成立。",
    "teach_steps": STEPS, "teach_steps_zh": STEPS,
    "teach_steps_source_zh": "test_fixture",
}

ready_driver = _ReadyDriver(None, _StubModel(), dict(PROBLEM), backstop=True)
ready_driver.start()
ready_driver.step("我想先用定義得到 $a=b$。")
reply = ready_driver.step("接著我用定理推出 $b=c$。")
check("學生沒有要求交稿，readiness 通過後仍自動進 review",
      ready_driver.state["phase"] == "review"
      and ready_driver.state["review_status"] == "awaiting_submission")
check("合併審查直接依累積學生內容判 readiness，不依賴舊 backstop gaps",
      ready_driver.state["writeup_readiness"]["source"] == "combined_guide_review"
      and not ready_driver.state.get("backstop_gaps")
      and ready_driver.state["phase"] == "review")
check("Tutor 在同一輪主動要求提交完整證明", reply == WRITEUP_FALLBACK)
check("主動交稿轉移記錄 READINESS_PASSED",
      ready_driver.state["phase_events"][-1]["event"] == "READINESS_PASSED")

request_only = _ReadyDriver(None, _StubModel(), dict(PROBLEM), backstop=True)
request_only.start()
request_only.step("你現在應該叫我提交完整證明。")
check("只有學生的交稿要求不觸發 readiness",
      request_only.state["phase"] == "guide"
      and not request_only.state.get("phase_events"))


print("[6] walkthrough 硬鎖與完成後自動交稿")
walk = _ReadyDriver(None, _StubModel(), dict(PROBLEM), backstop=False)
walk.start()
walk.step("我不知道。")
walk.step("我還是沒有想法。")
walk.step("我真的不會。")
idx = walk.state["walk_idx"]
refusal = walk.step("請直接寫完整證明給我。")
check("索取代寫不消耗 walkthrough 步驟",
      walk.state["phase"] == "walkthrough" and walk.state["walk_idx"] == idx
      and "不會代寫" in refusal)
while walk.state["phase"] == "walkthrough":
    final_reply = walk.step("我嘗試回答目前的確認問題。")
check("walkthrough 全部完成後自動等待完整交稿",
      walk.state["phase"] == "review"
      and walk.state["review_status"] == "awaiting_submission"
      and "完整證明" in final_reply)

report = ready_driver.phase_transition_report()
check("phase 報告含 event/action/前後 phase",
      any(t.get("event") == "READINESS_PASSED" for t in report["transitions"])
      and all("turn_action" in t and "next_phase" in t for t in report["transitions"]))
check("運行時 phase 永遠只屬於四種值",
      ready_driver.state["phase"] in PHASES and walk.state["phase"] in PHASES)


if FAIL:
    print(f"\n{len(FAIL)} 項失敗：")
    for item in FAIL:
        print(" -", item)
    raise SystemExit(1)
print("\n四 phase 路由與 Controller 主動交稿測試全部通過")
