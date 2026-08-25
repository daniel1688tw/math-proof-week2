# -*- coding: utf-8 -*-
"""SEGMENTER 的確定性單元測試；不連線 Ollama、不需要 GPU。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_reference as ar


def step(i: int, *, answer: str | None = None) -> dict:
    concepts = ["選取任意元素", "驗證定理前提", "套用核心定理",
                "整理所得等式", "利用符號條件", "收束全稱量詞",
                "排除退化情形"]
    concept = concepts[i - 1]
    return {
        "step_id": f"s{i}",
        "explain": f"第 {i} 步使用「{concept}」完成對應的推理。",
        "core_idea": concept,
        "check": f"這裡為什麼需要{concept}？",
        "expected_answer": answer or f"因為本步必須{concept}",
    }


def payload(count: int, *, answer3: str | None = None) -> str:
    steps = [step(i, answer=answer3 if i == 3 else None)
             for i in range(1, count + 1)]
    return json.dumps({"steps": steps}, ensure_ascii=False)


def check(name: str, condition: bool):
    if not condition:
        raise AssertionError(name)
    print(f"  OK {name}")


print("[1] schema 解析不截斷")
seven = ar.parse_steps(payload(7))
check("保留七步供修補，而不是靜默截成六步", len(seven or []) == 7)
check("回報 too_many_steps", any(
    issue["code"] == "too_many_steps" for issue in ar.teach_step_issues(seven)))
three = ar.parse_steps(payload(3))
check("選填陣列省略時仍可解析", bool(three) and
      three[0]["accepted_answers"] == [] and three[0]["common_errors"] == [])

print("[1b] 原因題的答案不能只重述結論")
shallow = [dict(s) for s in three]
shallow[0].update(check="為什麼 $L>0$ 時 $L/2>0$？",
                  expected_answer="$L/2>0$")
shallow_issues = ar.teach_step_issues(shallow)
check("短結論會被標成 reason_answer_too_shallow", any(
    issue["code"] == "reason_answer_too_shallow" for issue in shallow_issues))
explained = [dict(s) for s in three]
explained[0].update(check="為什麼 $L>0$ 時 $L/2>0$？",
                    expected_answer="因為正數除以正數仍為正，而 $2>0$，所以 $L/2>0$")
check("包含前提、性質與結論的原因答案可通過本地守門",
      not ar.teach_step_issues(explained))
long_but_useful = [dict(s) for s in explained]
long_but_useful[0]["expected_answer"] += (
    "；這個正下界之後可用來把函數值限制在零的上方，並完成題目要求的正性結論")
check("完整理由不再受舊版 60 字上限排斥",
      not any(i["code"] == "answer_too_long"
              for i in ar.teach_step_issues(long_but_useful)))


def run_with_fake(responses: list[str | None], **kwargs):
    calls = []
    old = ar._chat

    def fake(system, user, temperature, timeout=600, format_schema=None):
        calls.append({"system": system, "schema": format_schema, "user": user})
        if not responses:
            raise AssertionError("模型呼叫次數超出測試預期")
        return responses.pop(0)

    ar._chat = fake
    try:
        result = ar.segment_proof("題目", "參考證明", lang="zh", **kwargs)
    finally:
        ar._chat = old
    return result, calls


PASS = '{"verdict":"pass","issues":[]}'

print("[2] 本地問題會帶著原因修補")
result, calls = run_with_fake([payload(2), payload(3), PASS])
check("兩步候選修補後成功", len(result or []) == 3)
check("第二個內容呼叫使用 repair prompt", calls[1]["system"] is ar.SEGMENTER_REPAIR_SYSTEM)
check("repair prompt 收到 too_few_steps", "too_few_steps" in calls[1]["user"])
check("生成與驗證皆要求 JSON Schema", calls[0]["schema"] is ar.SEGMENTER_SCHEMA and
      calls[-1]["schema"] is ar.VERDICT_SCHEMA)

print("[3] 數學驗證意見會修補同一候選")
semantic_issue = json.dumps({
    "verdict": "fail", "issues": [
        "第 3 步的答案只重述結論，沒有交代前提、所用性質與推導",
        "第 3 步只問鏈尾的中間量計算，沒有檢查主要推論如何成立",
        "第 3 步 check 把關鍵中間關係與目標結論一起寫在問題中，問題本身已包含答案",
    ]
}, ensure_ascii=False)
result, calls = run_with_fake([
    payload(3, answer3="錯誤答案"), semantic_issue,
    payload(3, answer3="因為本步必須套用核心定理"), PASS,
])
check("語意修補後成功", len(result or []) == 3)
check("修補提示包含問題／答案品質的具體意見",
      "沒有交代前提" in calls[2]["user"] and
      "沒有檢查主要推論" in calls[2]["user"] and
      "問題本身已包含答案" in calls[2]["user"])
check("語意驗證器被要求檢查步驟範圍與非循環答案",
      "只問 explain 已明確教過的內容" in ar.TEACH_STEPS_VERIFIER_SYSTEM and
      "純粹循環重述" in ar.TEACH_STEPS_VERIFIER_SYSTEM and
      "只問中間量" in ar.TEACH_STEPS_VERIFIER_SYSTEM and
      "不可單獨造成 fail" in ar.TEACH_STEPS_VERIFIER_SYSTEM)

print("[3b] 非阻斷品質問題不再讓第三輪整份作廢")
shallow_payload = json.dumps({"steps": shallow}, ensure_ascii=False)
diagnostics = []
result, calls = run_with_fake(
    [shallow_payload, shallow_payload, shallow_payload, PASS],
    attempts=3, diagnostics=diagnostics)
check("前兩輪仍嘗試修補品質問題", sum(
    c["system"] is ar.SEGMENTER_REPAIR_SYSTEM for c in calls) == 2)
check("第三輪只剩答案過短時仍送交數學語意驗證並可接受", len(result or []) == 3)
check("診斷保留 local_quality_advisory，沒有靜默忽略品質問題", any(
    item["event"] == "local_quality_advisory" for item in diagnostics))

hard_diagnostics = []
result, calls = run_with_fake(
    [payload(2), payload(2), payload(2)], attempts=3,
    diagnostics=hard_diagnostics)
check("步數不足等阻斷問題第三輪仍拒絕", result is None)
check("阻斷問題不會繞過本地驗收送給語意驗證器", all(
    c["system"] is not ar.TEACH_STEPS_VERIFIER_SYSTEM for c in calls))

print("[4] 驗證服務波動不觸發重新切分")
result, calls = run_with_fake([payload(3), "非 JSON", PASS])
content_calls = [c for c in calls if c["system"] in
                 (ar.SEGMENTER_SYSTEM, ar.SEGMENTER_REPAIR_SYSTEM)]
verifier_calls = [c for c in calls if c["system"] is ar.TEACH_STEPS_VERIFIER_SYSTEM]
check("同一候選在驗證器重試後成功", len(result or []) == 3)
check("內容只生成一次", len(content_calls) == 1)
check("驗證器重試兩次", len(verifier_calls) == 2)

print("[5] 翻譯保留同一套步驟而不重新切分")
source_steps = ar.parse_steps(payload(3))
responses = [payload(3), PASS]
calls = []
old = ar._chat

def fake_translate(system, user, temperature, timeout=600, format_schema=None):
    calls.append({"system": system, "schema": format_schema})
    return responses.pop(0)

ar._chat = fake_translate
try:
    translated = ar.translate_teach_steps(
        "Problem", "Verified proof", source_steps, target_lang="zh")
finally:
    ar._chat = old
check("翻譯後步數與 step_id 不變",
      [s["step_id"] for s in translated or []] ==
      [s["step_id"] for s in source_steps or []])
check("翻譯只呼叫 translator 與忠實度 verifier",
      calls[0]["system"] is ar.TEACH_STEPS_TRANSLATOR_SYSTEM and
      calls[1]["system"] is ar.TRANSLATED_STEPS_VERIFIER_SYSTEM and
      all(c["system"] is not ar.SEGMENTER_SYSTEM for c in calls))
check("翻譯驗證不重新評選原始教學問題",
      "不要重新評選" in ar.TRANSLATED_STEPS_VERIFIER_SYSTEM)

print("test_segmenter_unit: all passed")
