# -*- coding: utf-8 -*-
"""完整證明兩輪審閱、局部訂正佇列與草稿合併的純邏輯測試。"""
from __future__ import annotations

import os
import json
import os
import subprocess
import re
import sys
from pathlib import Path

os.environ["REVIEW_BACKSTOP"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import review_backstop
import phase_router
from review_backstop import (_issue_from_fallback_text, _parse_gaps,
                             _parse_issue_list, review_full_proof)
from tutor_driver import (LOCAL_JUDGE_UNAVAILABLE, REVIEW_CLEAN_REQUEST,
                          REVIEW_ISSUE_UNACTIONABLE, REVIEW_PASS,
                          REVIEW_REFUSE_WRITE, TutorDriver)


def issue(root: str, desc: str | None = None) -> dict:
    return {"root_cause": root, "location": "草稿中的對應敘述",
            "description": desc or root, "correction": f"{root}的正確版本"}


def test_native_schema_and_review_failure_diagnostics() -> None:
    """原生 schema 會送到 Ollama，且 timeout／length／解析失敗不再全變成 None。"""
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }
    original_urlopen = review_backstop.urllib.request.urlopen
    original_remote = os.environ.pop("REMOTE_REVIEW_SSH", None)
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({
                "done_reason": "length", "message": {"content": ""},
            }).encode("utf-8")

    def fake_length(req, timeout):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    review_backstop.urllib.request.urlopen = fake_length
    try:
        length_diag = {}
        assert review_backstop._chat_content(
            "system", "user", 120, num_predict=8192,
            response_format=schema, diagnostics=length_diag) is None
    finally:
        review_backstop.urllib.request.urlopen = original_urlopen
    assert captured["payload"]["format"] == schema
    assert captured["payload"]["options"]["num_predict"] == 8192
    assert captured["timeout"] == 120
    assert length_diag["failure_reason"] == "length_exhausted"
    assert isinstance(length_diag.get("elapsed_ms"), int)

    review_backstop.urllib.request.urlopen = lambda *_args, **_kwargs: (
        (_ for _ in ()).throw(TimeoutError("timed out")))
    try:
        timeout_diag = {}
        assert review_backstop._chat_content(
            "system", "user", 120, response_format=schema,
            diagnostics=timeout_diag) is None
    finally:
        review_backstop.urllib.request.urlopen = original_urlopen
    assert timeout_diag["failure_reason"] == "timeout"
    if original_remote is not None:
        os.environ["REMOTE_REVIEW_SSH"] = original_remote

    original_chat = review_backstop._chat_content
    outputs = iter(["not json", '{"ok":true}'])

    def fake_chat(system, user, timeout, diagnostics=None, **kwargs):
        if diagnostics is not None:
            diagnostics.update(status="received", failure_reason=None)
        return next(outputs)

    def parse_ok(raw):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value.get("ok"), bool) else None

    review_backstop._chat_content = fake_chat
    try:
        retry_diag = {}
        assert review_backstop._retry_parsed(
            "system", "user", parse_ok, timeout=120, attempts=2,
            per_attempt_timeout=120, response_format=schema,
            diagnostics=retry_diag) == {"ok": True}
    finally:
        review_backstop._chat_content = original_chat
    assert retry_diag["status"] == "parsed"
    assert retry_diag["attempts"][0]["failure_reason"] == "structured_output_invalid"
    assert retry_diag["attempts"][1]["status"] == "parsed"


def test_issue_parser_and_two_pass_root_dedup() -> None:
    many = [f"錯誤 {i}" for i in range(1, 7)]
    assert _parse_gaps(__import__("json").dumps(many, ensure_ascii=False)) == many

    parsed = _parse_issue_list(
        '[{"root_cause":"不等號方向錯誤","description":"第二行方向相反",'
        '"question":"第二行應如何比較？"}]')
    assert parsed and parsed[0]["root_cause"] == "不等號方向錯誤"

    outputs = iter([
        '[{"root_cause":"中值定理的區間差方向錯誤",'
        '"description":"把 b-a 寫成 a-b，後續符號也因此錯誤",'
        '"question":"中值定理中的端點差應如何寫？"}]',
        '[{"root_cause":"中值定理區間差方向錯誤",'
        '"description":"相同根本錯誤造成結論方向錯誤",'
        '"question":"端點差的順序為何？"},'
        '{"root_cause":"遺漏定理前提", "description":"未說明閉區間連續",'
        '"question":"使用定理前還要確認什麼？"}]',
    ])
    original = review_backstop._chat_content
    calls = []

    def fake_chat(system, user, timeout, **kwargs):
        calls.append(user)
        return next(outputs)

    review_backstop._chat_content = fake_chat
    try:
        issues = review_full_proof("題目", "參考解", "學生證明")
    finally:
        review_backstop._chat_content = original
    assert len(calls) == 2
    assert issues is not None and len(issues) == 2
    assert "後續" in issues[0]["description"] or "結論" in issues[0]["description"]


def test_full_review_retries_and_keeps_first_pass() -> None:
    valid_first = ('[{"root_cause":"定理用錯","location":"第三行",'
                   '"description":"該定理不能推出導數為零",'
                   '"correction":"應改用符合前提的定理"}]')
    outputs = iter(["格式錯誤", valid_first, "仍非 JSON", "仍非 JSON", "仍非 JSON"])
    original = review_backstop._chat_content
    calls = []

    def fake_chat(system, user, timeout, **kwargs):
        calls.append(user)
        return next(outputs)

    review_backstop._chat_content = fake_chat
    try:
        issues = review_full_proof("題目", "參考解", "學生證明")
    finally:
        review_backstop._chat_content = original
    assert len(calls) == 5
    assert issues and len(issues) == 1
    assert issues[0]["root_cause"] == "定理用錯"


def test_full_review_second_pass_explicitly_audits_conclusion_scope() -> None:
    original = review_backstop._retry_parsed
    calls = []

    def fake_retry(system, user, parser, **kwargs):
        calls.append(user)
        return []

    review_backstop._retry_parsed = fake_retry
    try:
        assert review_full_proof("題目", "參考解", "學生證明") == []
    finally:
        review_backstop._retry_parsed = original
    assert len(calls) == 2
    assert "末句結論" in calls[1]
    assert "定義域或量詞範圍" in calls[1]
    assert "不能由前文自動補回" in calls[1]


def test_review_backend_can_use_remote_ssh_transport() -> None:
    original_run = subprocess.run
    original_remote = os.environ.get("REMOTE_REVIEW_SSH")
    original_port = os.environ.get("REMOTE_REVIEW_PORT")
    calls = []

    class Result:
        returncode = 0
        stdout = '{"message":{"content":"CLEAR"},"done_reason":"stop"}'
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Result()

    subprocess.run = fake_run
    os.environ["REMOTE_REVIEW_SSH"] = "daniel@example.invalid"
    os.environ["REMOTE_REVIEW_PORT"] = "11435"
    try:
        result = review_backstop._chat_content("system", "user", 60, num_predict=128)
    finally:
        subprocess.run = original_run
        if original_remote is None:
            os.environ.pop("REMOTE_REVIEW_SSH", None)
        else:
            os.environ["REMOTE_REVIEW_SSH"] = original_remote
        if original_port is None:
            os.environ.pop("REMOTE_REVIEW_PORT", None)
        else:
            os.environ["REMOTE_REVIEW_PORT"] = original_port
    assert result == "CLEAR"
    assert calls and calls[0][0][:2] == ["ssh", "daniel@example.invalid"]
    assert "localhost:11435/api/chat" in calls[0][0][2]
    assert calls[0][1]["input"].startswith("{")


def test_text_fallback_recovers_actionable_issue_fields() -> None:
    parsed = _issue_from_fallback_text(
        "位置：第一行；錯誤：epsilon 被錯誤地描述為存在性陳述", 1)
    assert parsed["location"] == "第一行"
    assert parsed["root_cause"] == "epsilon 被錯誤地描述為存在性陳述"
    assert parsed["description"] == parsed["root_cause"]


def test_contextual_local_revision_accepts_minimal_valid_replacement() -> None:
    original = review_backstop._chat_content
    calls = []
    outputs = iter([
        '{"verdict":"uncertain","feedback":"需再檢查上下文"}',
        '{"verdict":"correct","feedback":"正確定理名稱已足以替換原錯字"}',
        '{"verdict":"correct","feedback":"以題設連續性取代多餘單調性即可"}',
    ])

    def fake_chat(system, user, timeout, **kwargs):
        calls.append((system, user, timeout))
        return next(outputs)

    review_backstop._chat_content = fake_chat
    try:
        theorem_fix = review_backstop.judge_local_revision(
            "題目", "參考解",
            "根據均值定理，存在 x0,y0 取得最小值與最大值。",
            {"root_cause": "誤用均值定理找極值",
             "correction": "根據極值定理"},
            "根據極值定理")
        assumption_fix = review_backstop.judge_local_revision(
            "題目", "參考解",
            "因 A 位於 m,M 之間且 f 單調遞增，根據 IVT 可得結論。",
            {"root_cause": "加入題目未給的單調遞增假設",
             "correction": "f 在區間上連續"},
            "因為 A 落在 m 和 M 之間，且 f 在 [a,b] 上連續")
    finally:
        review_backstop._chat_content = original
    assert theorem_fix and theorem_fix["verdict"] == "correct"
    assert assumption_fix and assumption_fix["verdict"] == "correct"
    assert len(calls) == 3  # uncertain 會自動重試；下一個正確判定一次完成
    assert all(timeout == 300 for _, _, timeout in calls)
    assert "局部文字" in calls[0][0] and "定理名稱寫錯" in calls[0][0]


def test_local_revision_scope_recheck_ignores_unqueued_draft_error() -> None:
    """第一輪越界檢查全文時，範圍複核應只評目前 issue。"""
    original = review_backstop._chat_content
    calls = []
    outputs = iter([
        '{"verdict":"partial","feedback":"草稿中另一個不等式仍有錯"}',
        '{"verdict":"correct","feedback":"目前 epsilon 正負號問題已完成訂正"}',
    ])

    def fake_chat(system, user, timeout, **kwargs):
        calls.append((system, user, timeout))
        return next(outputs)

    review_backstop._chat_content = fake_chat
    try:
        result = review_backstop.judge_local_revision(
            "證明一般命題", "參考證明",
            "取 epsilon=-L/2。後面另有一個尚未排入佇列的不等式錯誤。",
            {"root_cause": "epsilon 被取為負數", "location": "取 epsilon=-L/2",
             "description": "極限定義要求 epsilon>0", "correction": "epsilon=L/2"},
            "epsilon=L/2", timeout=300)
    finally:
        review_backstop._chat_content = original
    assert result and result["verdict"] == "correct"
    assert len(calls) == 2
    assert calls[1][0] == review_backstop.LOCAL_REVISION_SCOPE_SYSTEM
    assert all(timeout == 300 for _, _, timeout in calls)
    assert "未寫在目前 issue description" in calls[1][0]


def test_walkthrough_judge_accepts_concise_reason_after_retry() -> None:
    """正確的精簡依據不得因一次 uncertain 被降成 unavailable。"""
    original = review_backstop._chat_content
    calls = []
    outputs = iter([
        '{"verdict":"uncertain","feedback":"需要再確認"}',
        '{"verdict":"correct","feedback":"學生正確指出直接適用的定義"}',
        '{"verdict":"correct","feedback":"第二輪確認理由與結論皆成立"}',
    ])

    def fake_chat(system, user, timeout, **kwargs):
        calls.append((system, timeout, kwargs.get("num_predict")))
        return next(outputs)

    review_backstop._chat_content = fake_chat
    try:
        result = review_backstop.judge_walkthrough_answer(
            "證明一般命題", "參考證明",
            {"explain": "由絕對值定義得到 -e<y<e",
             "check": "為什麼 |y|<e 可推出 -e<y<e？",
             "expected_answer": "因為絕對值的定義", "accepted_answers": []},
            "絕對值的基本定義", timeout=300)
    finally:
        review_backstop._chat_content = original
    assert result and result["verdict"] == "correct"
    assert len(calls) == 3
    assert all(timeout == 300 and tokens == 8192 for _, timeout, tokens in calls)
    assert calls[-1][0] == review_backstop.ANSWER_CORRECT_AUDIT_SYSTEM
    assert "正確點出直接適用的定義" in review_backstop.ANSWER_JUDGE_SYSTEM


def test_walkthrough_judge_compact_fallback_requires_specific_reason() -> None:
    """完整語境失敗後仍應取得具體錯因，不可落到通用 unavailable 理由。"""
    original = review_backstop._chat_content
    calls = []
    outputs = iter([
        "非 JSON", "仍非 JSON", "第三次也失敗",
        '{"verdict":"incorrect","root_error":"回答沒有處理確認問題",'
        '"correct_basis":"delta 應控制函數值差",'
        '"feedback":"目前無法可靠確認這個回答為正確"}',
    ])

    def fake_chat(system, user, timeout, **kwargs):
        calls.append((system, timeout))
        return next(outputs)

    review_backstop._chat_content = fake_chat
    try:
        result = review_backstop.judge_walkthrough_answer(
            "證明一般命題", "參考證明",
            {"explain": "選 delta 使接近 a 時 |f(x)-L|<epsilon",
             "check": "delta 用來確保什麼？", "expected_answer": "|f(x)-L|<epsilon",
             "accepted_answers": []},
            "|x-a|<=delta", timeout=300)
    finally:
        review_backstop._chat_content = original
    assert result and result["verdict"] == "incorrect"
    assert result["feedback"] == "回答沒有處理確認問題"
    assert "delta 應控制函數值差" not in result["feedback"]
    assert "無法可靠確認" not in result["feedback"]
    assert len(calls) == 4
    assert calls[-1][0] == review_backstop.ANSWER_JUDGE_COMPACT_SYSTEM
    assert all(timeout == 300 for _, timeout in calls)


def test_walkthrough_judge_checks_reason_and_reports_first_error() -> None:
    """理由錯誤不能因結論相同而放行；錯誤鏈必須指出第一個錯式。"""
    original = review_backstop._chat_content
    calls = []
    outputs = iter([
        '{"verdict":"incorrect",'
        '"root_error":"你在第一個等式就把 g\' 的多項式導數寫成 +4-8x",'
        '"correct_basis":"由 g=f-4x(1-x)=f-4x+4x^2，應有 g\'=f\'-4+8x，所以 g\'\'=f\'\'+8",'
        '"feedback":"後續會得到錯誤結果"}',
        '{"verdict":"correct","feedback":"最後等式形式正確"}',
        '{"verdict":"incorrect",'
        '"root_error":"把共同積分下限說成可以像代數項直接相消，這不是有效的積分推理",'
        '"correct_basis":"應用定積分的可加性：積分 0 到 x 等於積分 0 到 y 加上積分 y 到 x",'
        '"feedback":"結論雖對但理由無效"}',
    ])

    def fake_chat(system, user, timeout, **kwargs):
        calls.append(system)
        return next(outputs)

    review_backstop._chat_content = fake_chat
    try:
        derivative = review_backstop.judge_walkthrough_answer(
            "證明存在 c 使 f''(c)=-8", "已驗證參考證明",
            {"explain": "g'=f'-4+8x，所以 g''=f''+8。",
             "check": "為什麼 g''(c)=0 可推出 f''(c)=-8？",
             "expected_answer": "因為 g''=f''+8。"},
            "g'=f'+4-8x，所以 g''=f''-8。", timeout=300)
        integral = review_backstop.judge_walkthrough_answer(
            "證明積分估計", "已驗證參考證明",
            {"explain": "F(x)-F(y)=積分 y 到 x。",
             "check": "為什麼這個等式成立？",
             "expected_answer": "由定積分可加性。"},
            "因為相同下限 0 可以直接相消。", timeout=300)
    finally:
        review_backstop._chat_content = original
    assert derivative and derivative["verdict"] == "incorrect"
    assert derivative["feedback"].startswith("你在第一個等式")
    assert "應有 g'=f'-4+8x" not in derivative["feedback"]
    assert integral and integral["verdict"] == "incorrect"
    assert "不是有效的積分推理" in integral["feedback"]
    assert "可加性" not in integral["feedback"]
    assert calls[-1] == review_backstop.ANSWER_CORRECT_AUDIT_SYSTEM
    assert "即使最後結論碰巧" in review_backstop.ANSWER_JUDGE_SYSTEM
    assert "第一個錯誤" in review_backstop.ANSWER_JUDGE_SYSTEM


def test_walkthrough_judge_retries_non_chinese_feedback_in_chinese_session() -> None:
    """中文步驟的對外錯因不得偶爾退化成英文。"""
    original = review_backstop._chat_content
    calls = []
    outputs = iter([
        '{"verdict":"incorrect","root_error":"student used the wrong theorem",'
        '"correct_basis":"use the intermediate value theorem"}',
        '{"verdict":"incorrect","root_error":"學生誤用了均值定理",'
        '"correct_basis":"此處應使用中間值定理"}',
    ])

    def fake_chat(system, user, timeout, **kwargs):
        calls.append(system)
        return next(outputs)

    review_backstop._chat_content = fake_chat
    try:
        result = review_backstop.judge_walkthrough_answer(
            "證明存在零點", "參考證明",
            {"explain": "由中間值定理得到零點。",
             "check": "此處使用哪個定理？", "expected_answer": "中間值定理"},
            "均值定理", timeout=300)
    finally:
        review_backstop._chat_content = original
    assert result and result["verdict"] == "incorrect"
    assert result["feedback"] == "學生誤用了均值定理"
    assert not re.search(r"student|wrong|theorem", result["feedback"], re.I)
    assert len(calls) == 2


def test_merge_uses_full_timeout_and_exact_patch_fallback() -> None:
    """長篇完整合併失敗時，應以唯一精確 patch 完成，不要求學生重送訂正。"""
    original = review_backstop._chat_content
    calls = []
    outputs = iter([
        "不是 JSON", "仍不是 JSON", "第三次仍無法解析",
        '{"old_text":"F 在 (a,b) 上連續且在 [a,b] 上可微",'
        '"new_text":"F 在 [a,b] 上連續且在 (a,b) 上可微"}',
    ])

    def fake_chat(system, user, timeout, **kwargs):
        calls.append((system, timeout))
        return next(outputs)

    review_backstop._chat_content = fake_chat
    try:
        draft = "由基本定理，F 在 (a,b) 上連續且在 [a,b] 上可微，因此可用中值定理。"
        merged = review_backstop.merge_proof_revision(
            "題目", "參考解", draft,
            issue("閉開區間條件顛倒"),
            "F 在 [a,b] 上連續且在 (a,b) 上可微", timeout=300)
    finally:
        review_backstop._chat_content = original
    assert merged == "由基本定理，F 在 [a,b] 上連續且在 (a,b) 上可微，因此可用中值定理。"
    assert len(calls) == 4
    assert all(timeout == 300 for _, timeout in calls)
    assert calls[-1][0] == review_backstop.PATCH_REVISION_SYSTEM


def test_review_queue_local_merge_clean_final_and_missed_recheck() -> None:
    problem = {"statement": "證明一般命題。", "reference_proof": "已驗證參考證明。"}
    driver = TutorDriver(tok=None, model=None, problem=problem, backstop=True)
    driver._enter_awaiting_submission(event="READINESS_PASSED", source="unit_test")
    first, second = issue("第一個根本錯誤"), issue("第二個根本錯誤")
    review_results = iter([[first, second], [], [], [issue("重新檢查發現的漏項")]])
    local_calls = []
    merge_calls = []
    reviewed_drafts = []
    original_review = review_backstop.review_full_proof
    original_local = review_backstop.judge_local_revision
    original_merge = review_backstop.merge_proof_revision

    def fake_review(statement, reference, draft, timeout=600):
        reviewed_drafts.append(draft)
        return next(review_results)

    def fake_local(statement, reference, draft, current_issue, answer, timeout=300):
        local_calls.append((current_issue["root_cause"], answer, draft))
        if "不知道" in answer:
            return {"verdict": "not_answer", "feedback": "沒有實質訂正"}
        return {"verdict": "correct", "feedback": "等價且完整"}

    def fake_merge(statement, reference, draft, current_issue, answer, timeout=300):
        merge_calls.append((current_issue["root_cause"], answer, draft))
        return draft + "\n已實際合併：" + answer

    review_backstop.review_full_proof = fake_review
    review_backstop.judge_local_revision = fake_local
    review_backstop.merge_proof_revision = fake_merge
    try:
        full = ("這是我的完整證明：令 x 為任意元素。因為條件甲成立，所以可使用定理乙；"
                "因此得到中間結論，又因條件丙成立，故最後命題成立。")
        reply = driver.step(full)
        trace = driver.phase_transition_report()["transitions"][-1]
        assert driver.state["review_active"]
        assert driver.state["phase"] == "review"
        assert driver.state["review_status"] == "correcting"
        assert driver.state["phase_events"][-1]["event"] == "FULL_PROOF_SUBMITTED"
        assert len(driver.state["review_issues"]) == 2
        assert "第一個根本錯誤" in reply and "第二個根本錯誤" not in reply
        assert "錯誤：" in reply and "正確版本：" not in reply
        assert first["correction"] not in reply
        assert "？" not in reply and "?" not in reply
        assert trace["intent"] == "full_proof_submission"
        assert trace["turn_action"] == "review_local_revision"

        reply = driver.step("我不知道")
        trace = driver.phase_transition_report()["transitions"][-1]
        assert driver.state["review_issue_idx"] == 0
        assert driver.state["review_status"] == "correcting"
        assert not driver.state.get("review_corrections")
        assert "尚未完整修正" in reply
        assert trace["intent"] == "local_revision"
        assert trace["turn_action"] == "review_local_revision"

        reply = driver.step("精簡但數學正確的第一項等價訂正。")
        assert driver.state["review_issue_idx"] == 1
        assert len(driver.state["review_corrections"]) == 1
        assert "第二個根本錯誤" in reply

        reply = driver.step("第二項的完整局部訂正。")
        assert reply == REVIEW_CLEAN_REQUEST
        assert driver.state["awaiting_clean_proof"]
        assert driver.state["phase"] == "review"
        assert driver.state["review_status"] == "awaiting_clean"
        assert "已核准的局部訂正" not in driver.state["current_proof_draft"]
        assert "已實際合併：精簡但數學正確的第一項等價訂正。" in driver.state["current_proof_draft"]
        assert "已實際合併：第二項的完整局部訂正。" in driver.state["current_proof_draft"]
        assert len(merge_calls) == 2
        assert reviewed_drafts[1] == driver.state["current_proof_draft"]

        clean = ("這是我的完整證明：令 x 為任意元素。因為已修正的條件成立，所以正確套用定理；"
                 "因此得到中間結論，又因其餘前提皆成立，故命題成立。")
        reply = driver.step(clean)
        assert reply == REVIEW_PASS and driver.state["done_closed"]
        assert driver.state["phase"] == "closed"
        assert driver.state["review_status"] is None
        assert driver.state["phase_events"][-1]["event"] == "REVIEW_PASSED"
        assert driver.state["review_last_full_proof"] == clean

        reply = driver.step("你漏審了一個錯誤，請重新檢查最近的完整證明。")
        trace = driver.phase_transition_report()["transitions"][-1]
        assert driver.state["review_active"] and not driver.state["done_closed"]
        assert driver.state["phase"] == "review"
        assert driver.state["review_status"] == "correcting"
        assert "重新檢查發現的漏項" in reply
        assert local_calls[0][1] == "我不知道"  # not_answer 也確實先交 Thinking 判斷
        assert trace["intent"] == "challenge_or_missed_review"
        assert trace["turn_action"] == "post_completion_reply"
    finally:
        review_backstop.review_full_proof = original_review
        review_backstop.judge_local_revision = original_local
        review_backstop.merge_proof_revision = original_merge


def test_full_resubmission_is_not_local_revision() -> None:
    problem = {"statement": "證明一般命題。", "reference_proof": "參考證明。"}
    driver = TutorDriver(tok=None, model=None, problem=problem, backstop=True)
    driver._enter_awaiting_submission(event="READINESS_PASSED", source="unit_test")
    calls = []
    original_review = review_backstop.review_full_proof
    original_local = review_backstop.judge_local_revision

    def fake_review(statement, reference, draft, timeout=600):
        calls.append(draft)
        return [issue("初稿問題")] if len(calls) == 1 else []

    def fail_local(*args, **kwargs):
        raise AssertionError("完整證明不可送進局部訂正判定")

    review_backstop.review_full_proof = fake_review
    review_backstop.judge_local_revision = fail_local
    try:
        driver.step("這是我的完整證明：因為前提成立，所以套用定理，因此結論成立，故得證。" * 2)
        # 不加「完整證明」標籤，仍應由全文結構辨認為重交，不可誤當局部訂正。
        rewritten = ("任取一個符合題設的元素。因為前提已修正，所以可正確套用定理，"
                     "因此得到所需的中間結論；又因其餘條件成立，故原命題成立。" * 3)
        reply = driver.step(rewritten)
        assert reply == REVIEW_PASS
        assert calls[-1] == rewritten
        assert driver.state["review_corrections"] == []
    finally:
        review_backstop.review_full_proof = original_review
        review_backstop.judge_local_revision = original_local


def test_local_judge_unavailable_preserves_issue_and_allows_retry() -> None:
    """一次服務失敗不得把局部訂正流程變成死路。"""
    problem = {"statement": "證明一般命題。", "reference_proof": "已驗證參考證明。"}
    driver = TutorDriver(tok=None, model=None, problem=problem, backstop=True)
    current_issue = issue("量詞順序錯誤")
    original_draft = "給定任意 epsilon，存在 epsilon 使性質成立。"
    driver.state.update(
        phase="review", review_status="correcting", review_active=True,
        review_issues=[current_issue], review_issue_idx=0,
        current_proof_draft=original_draft, review_base_proof=original_draft)
    local_results = iter([None, {"verdict": "correct", "feedback": "量詞已修正"}])
    local_calls = []
    original_local = review_backstop.judge_local_revision
    original_merge = review_backstop.merge_proof_revision
    original_review = review_backstop.review_full_proof

    def fake_local(statement, reference, draft, pending_issue, answer, timeout=300):
        local_calls.append((draft, pending_issue, answer))
        return next(local_results)

    review_backstop.judge_local_revision = fake_local
    review_backstop.merge_proof_revision = lambda *args, **kwargs: "給定任意 epsilon，存在 delta 使性質成立。"
    review_backstop.review_full_proof = lambda *args, **kwargs: []
    try:
        correction = "存在一個相對應的 delta > 0"
        reply = driver.step(correction)
        assert reply == LOCAL_JUDGE_UNAVAILABLE
        assert driver.state["phase"] == "review"
        assert driver.state["review_status"] == "correcting"
        assert driver.state["review_issue_idx"] == 0
        assert driver.state["current_proof_draft"] == original_draft
        assert driver.state["review_error"] == "local_judge_unavailable"

        reply = driver.step(correction)
        assert reply == REVIEW_CLEAN_REQUEST
        assert driver.state["review_status"] == "awaiting_clean"
        assert len(driver.state["review_corrections"]) == 1
        assert "review_error" not in driver.state
        assert len(local_calls) == 2
    finally:
        review_backstop.judge_local_revision = original_local
        review_backstop.merge_proof_revision = original_merge
        review_backstop.review_full_proof = original_review


def test_unavailable_accepts_unlabelled_full_proof_recovery() -> None:
    """舊 unavailable 快照中的重寫全文不得被當成局部訂正。"""
    problem = {"statement": "以定義證明正性。", "reference_proof": "已驗證參考證明。"}
    driver = TutorDriver(tok=None, model=None, problem=problem, backstop=True)
    driver.state.update(
        phase="review", review_status="unavailable",
        review_issues=[issue("量詞順序錯誤")], review_issue_idx=0,
        current_proof_draft="舊草稿。", review_base_proof="舊草稿。")
    reviewed = []
    original_review = review_backstop.review_full_proof
    original_local = review_backstop.judge_local_revision

    def fake_review(statement, reference, draft, timeout=600):
        reviewed.append(draft)
        return []

    def fail_local(*args, **kwargs):
        raise AssertionError("重寫完整證明不可送進局部訂正判定")

    review_backstop.review_full_proof = fake_review
    review_backstop.judge_local_revision = fail_local
    try:
        full = ("因為題設的極限存在且 L>0，根據極限的定義，對於給定的 epsilon=L/2>0，"
                "存在相應的 delta>0，使得當 0<|x-a|<delta 時，|f(x)-L|<epsilon。"
                "將 epsilon=L/2 代入並根據絕對值的性質拆開，可得 L/2<f(x)<3L/2。"
                "因為 L>0，所以 L/2>0，因此當 x 充分靠近 a 時必定有 f(x)>L/2>0。")
        reply = driver.step(full)
        trace = driver.phase_transition_report()["transitions"][-1]
        assert reply == REVIEW_PASS
        assert reviewed == [full]
        assert driver.state["phase"] == "closed"
        assert trace["intent"] == "full_proof_submission"
    finally:
        review_backstop.review_full_proof = original_review
        review_backstop.judge_local_revision = original_local


def test_unactionable_issue_never_enters_local_revision_queue() -> None:
    problem = {"statement": "證明一般命題。", "reference_proof": "已驗證參考證明。"}
    driver = TutorDriver(tok=None, model=None, problem=problem, backstop=True)
    driver._enter_awaiting_submission(event="READINESS_PASSED", source="unit_test")
    original_review = review_backstop.review_full_proof
    review_backstop.review_full_proof = lambda *args, **kwargs: [{
        "root_cause": "量詞順序錯誤", "location": "", "description": "", "correction": "",
    }]
    try:
        reply = driver.step("這是我的完整證明：因為前提成立，所以套用定理，因此結論成立，故得證。" * 2)
        assert reply == REVIEW_ISSUE_UNACTIONABLE
        assert driver.state["review_status"] == "awaiting_submission"
        assert not driver.state.get("review_issues")
        assert driver.state["review_error"] == "issue_not_actionable"
        assert driver.state.get("review_unactionable_issues")
    finally:
        review_backstop.review_full_proof = original_review


def test_review_workflow_consumes_one_router_decision_per_turn() -> None:
    """review/closed 不重新偵測意圖，且診斷欄位不為空。"""
    problem = {"statement": "證明一般命題。", "reference_proof": "已驗證參考證明。"}
    driver = TutorDriver(tok=None, model=None, problem=problem, backstop=True)
    driver._enter_awaiting_submission(event="READINESS_PASSED", source="unit_test")
    route_calls = []
    original_route = phase_router.route_student_state
    original_review = review_backstop.review_full_proof

    def counting_route(student_text, context, **kwargs):
        route_calls.append(student_text)
        return original_route(student_text, context, **kwargs)

    phase_router.route_student_state = counting_route
    review_backstop.review_full_proof = lambda *args, **kwargs: []
    try:
        demand = "請你直接寫出完整證明給我。"
        status_before = driver.state.get("review_status")
        index_before = driver.state.get("review_issue_idx")
        reply = driver.step(demand)
        trace = driver.phase_transition_report()["transitions"][-1]
        assert reply == REVIEW_REFUSE_WRITE
        assert driver.state.get("review_status") == status_before
        assert driver.state.get("review_issue_idx") == index_before
        assert route_calls == [demand]
        assert trace["intent"] == "demand_full_answer"
        assert trace["turn_action"] == "refuse_tutor_write"

        full = ("這是我的完整證明：任取符合題設的元素。因為所有前提都成立，"
                "所以可以套用相應定理，因此得到所需的中間結論；"
                "再由元素的任意性，故原命題成立，證畢。")
        reply = driver.step(full)
        trace = driver.phase_transition_report()["transitions"][-1]
        assert reply == REVIEW_PASS
        assert route_calls == [demand, full]
        assert trace["intent"] == "full_proof_submission"
        assert trace["turn_action"] == "review_local_revision"

        challenge = "你真的確定最近的完整證明沒有漏審嗎？"
        reply = driver.step(challenge)
        trace = driver.phase_transition_report()["transitions"][-1]
        assert reply == REVIEW_PASS
        assert route_calls == [demand, full, challenge]
        assert trace["intent"] == "challenge_or_missed_review"
        assert trace["turn_action"] == "post_completion_reply"
    finally:
        phase_router.route_student_state = original_route
        review_backstop.review_full_proof = original_review


def test_closed_proof_correctness_messages_always_recheck() -> None:
    """疑問、肯定、否定或委婉語氣都重審；純致謝不重審。"""
    problem = {"statement": "證明一般命題。", "reference_proof": "參考證明。"}
    original_review = review_backstop.review_full_proof
    calls = []

    def fake_review(statement, reference, draft, timeout=600):
        calls.append(draft)
        return []

    review_backstop.review_full_proof = fake_review
    try:
        for text in (
                "你真的確定嗎？",
                "我的證明是不是還有錯？",
                "我認為剛才可能漏審了一處。",
                "可以再確認最近的完整證明是否正確嗎？"):
            driver = TutorDriver(tok=None, model=None, problem=problem, backstop=True)
            driver.state.update(
                phase="closed", current_proof_draft="最近一份完整證明。",
                review_status=None)
            before = len(calls)
            reply = driver.step(text)
            assert len(calls) == before + 1, text
            assert reply == REVIEW_PASS and driver.state["done_closed"], text

        driver = TutorDriver(tok=None, model=None, problem=problem, backstop=True)
        driver.state.update(
            phase="closed", current_proof_draft="最近一份完整證明。",
            review_status=None)
        before = len(calls)
        # 純致謝不屬於證明正確性重審；直接測 transition，避免單元測試
        # 因一般 Tutor 生成流程而需要載入模型。
        assert driver._review_workflow_transition("謝謝，我會把這個方法記下來。") is None
        assert len(calls) == before
        assert driver.state["phase"] == "closed"
    finally:
        review_backstop.review_full_proof = original_review


def test_guide_reply_reviewer_schema_and_separation() -> None:
    """測試引導回覆審查器之最新 Schema 解析與錯誤欄位分離 (P0-3, P0-4, P1-1)。"""
    driver = TutorDriver(tok=None, model=None, problem={"id": "T1", "statement": "Test", "reference_proof": "Proof"}, backstop=True)
    driver.state.update(phase="guide", turn_action="respond_attempt")

    raw_json = json.dumps({
        "latest_student_step_status": "correct",
        "first_missing_step": "建立不等式下界",
        "candidate_math_error": "",
        "candidate_ownership_error": "",
        "addresses_latest_student_step": True,
        "mathematically_correct": True,
        "level_policy_pass": True,
        "introduces_new_proof_idea": False,
        "completes_any_unfinished_step": False,
        "leaks_final_conclusion": False,
        "ready_for_writeup": False,
        "missing_core_step": "建立不等式下界",
        "readiness_confidence": 0.75,
        "feedback": "學生已正確求出導數",
    })

    original_retry_parsed = review_backstop._retry_parsed

    def fake_retry_parsed(system, user, parser, **kwargs):
        return parser(raw_json)

    review_backstop._retry_parsed = fake_retry_parsed
    try:
        parsed = driver._review_guide_reply("做得好，求出導數後下一步是什麼？", 1)
        assert parsed is not None
        assert parsed["latest_student_step_status"] == "correct"
        assert parsed["first_missing_step"] == "建立不等式下界"
        assert parsed["candidate_math_error"] == ""
        assert parsed["candidate_ownership_error"] == ""
        assert parsed["addresses_latest_student_step"] is True
        assert driver._guide_reply_review_passes(parsed, 1) is True
    finally:
        review_backstop._retry_parsed = original_retry_parsed


if __name__ == "__main__":
    test_native_schema_and_review_failure_diagnostics()
    test_issue_parser_and_two_pass_root_dedup()
    test_full_review_retries_and_keeps_first_pass()
    test_full_review_second_pass_explicitly_audits_conclusion_scope()
    test_review_backend_can_use_remote_ssh_transport()
    test_text_fallback_recovers_actionable_issue_fields()
    test_contextual_local_revision_accepts_minimal_valid_replacement()
    test_local_revision_scope_recheck_ignores_unqueued_draft_error()
    test_walkthrough_judge_accepts_concise_reason_after_retry()
    test_walkthrough_judge_compact_fallback_requires_specific_reason()
    test_walkthrough_judge_checks_reason_and_reports_first_error()
    test_walkthrough_judge_retries_non_chinese_feedback_in_chinese_session()
    test_merge_uses_full_timeout_and_exact_patch_fallback()
    test_review_queue_local_merge_clean_final_and_missed_recheck()
    test_full_resubmission_is_not_local_revision()
    test_local_judge_unavailable_preserves_issue_and_allows_retry()
    test_unavailable_accepts_unlabelled_full_proof_recovery()
    test_unactionable_issue_never_enters_local_revision_queue()
    test_review_workflow_consumes_one_router_decision_per_turn()
    test_closed_proof_correctness_messages_always_recheck()
    test_guide_reply_reviewer_schema_and_separation()
    print("test_review_workflow: all passed")
