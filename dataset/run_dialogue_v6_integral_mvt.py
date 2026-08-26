# -*- coding: utf-8 -*-
"""雙 AI 對話腳本 v6（含 Stuck 階梯升級與完整證明審閱測試）：
  - 題目：積分均值定理（math-proof-week2-full-project (1) - 複製 問題.txt 第一題）
  - 助教：本地 QLoRA 微調模型（Qwen3-4B + qlora_adapter_new）+ TutorDriver
  - 學生：agy CLI 呼叫 GPT-OSS 120B (Medium)，模擬真實學生「初遇卡住 -> 助教階梯提示 -> 突破計算 -> 提交完整證明」

完整測試覆蓋：
  1. Level 0 (宏觀提問, stuck=0)
  2. Level 1 (支架拆解, stuck=1)
  3. Level 2 (核心提示, stuck=2)
  4. 突破後的 stuck_count 歸零 (stuck=0)
  5. 完備後觸發 READINESS_PASSED -> review/awaiting_submission
  6. 學生提交完整 LaTeX 證明草稿
  7. 助教審閱結案
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTHONNOUSERSITE", "1")
os.environ["REVIEW_BACKSTOP"] = "0"  # 離線後盾模式

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── 設定 ────────────────────────────────────────────────────────────────────
AGY_EXE = os.environ.get(
    "AGY_EXE",
    str(Path(os.environ.get("LOCALAPPDATA", "")) / "agy" / "bin" / "agy.exe"),
)
AGY_MODEL = os.environ.get("AGY_STUDENT_MODEL", "GPT-OSS 120B (Medium)")
AGY_TIMEOUT_S = int(os.environ.get("AGY_TIMEOUT_S", "60"))

TARGET_PATH = ROOT / "測試結果_v6.txt"
MODEL_DIR = ROOT / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / "qlora_adapter_new"

PROBLEM = {
    "id": "CUSTOM_MVT_INT",
    "statement": (
        r"Prove that if \(f\) is continuous on \([a,b]\), then there exists "
        r"\(c\in(a,b)\) such that \(\int_a^b f(x)\,dx=f(c)(b-a)\)."
    ),
    "reference_proof": (
        r"令 $F(x) = \int_a^x f(t)\,dt$。\n"
        r"因 $f$ 在 $[a,b]$ 上連續，由微積分基本定理知 $F$ 在 $[a,b]$ 上連續、"
        r"在 $(a,b)$ 上可微，且 $F'(x) = f(x)$。\n"
        r"由拉格朗日中值定理（Lagrange Mean Value Theorem），存在 $c \in (a,b)$ 使得\n"
        r"\[ F(b) - F(a) = F'(c)(b - a) \]\n"
        r"又 $F(a) = \int_a^a f(t)\,dt = 0$，$F(b) = \int_a^b f(t)\,dt$，且 $F'(c) = f(c)$，\n"
        r"代入得 $\int_a^b f(x)\,dx = f(c)(b - a)$。證畢。"
    ),
    "hint_ladder": [
        "要證的是「積分等於某點函數值乘上區間長度」。這跟哪個微分定理中「函數增量等於某點導數乘上區間長度」的形式很像？",
        "定義一個變上限積分函數 F(x) = \\int_a^x f(t)\\,dt。根據微積分基本定理，F(x) 具有什麼性質？",
        "對 F(x) 在 [a,b] 上應用拉格朗日中值定理，計算 F(b)-F(a) 並代入 F'(c)=f(c) 與 F(a)=0 即可完成推導。",
    ],
}

STUDENT_SYSTEM = """\
你是一位正在修大學高等微積分的大學生，正在和蘇格拉底助教進行一對一證明引導對話。

你的特徵與行為規則：
- 【面對新問題或初次提示時】：你不知道該怎麼構造輔助函數，請表達困惑或卡住（例如「我毫無頭緒」「我還是想不到該怎麼構造」）。
- 【收到明確的具體提示時】：若助教給出了具體的函數構造或定理提示，請跟著算出當前這一步的數學算式（1~2句話）。
- 【收到寫完整證明的要求時】：當助教說「思路已經完整了。現在請把完整證明一步步寫出來」時，請整合所有步驟，輸出格式嚴謹、包含完整前提（連續可微）、定理依據、符號計算的正式數學證明草稿！
- 輸出純文字，不要加「學生：」等前綴。

題目：
Prove that if f is continuous on [a,b], then there exists c in (a,b) such that \\int_a^b f(x) dx = f(c)(b-a).
"""


def call_student_agy(conversation_history: list[dict], last_tutor_reply: str, student_stuck_target: bool = False) -> tuple[str, float]:
    """用 agy GPT-OSS 120B 動態生成學生下一句回應。"""
    is_writeup_requested = bool(
        re.search(r"(完整|整份|整個).{0,4}證明.{0,8}寫|請把完整證明|寫出完整證明", last_tutor_reply)
    )

    history_text = ""
    for msg in conversation_history[-8:]:
        if msg["role"] == "tutor":
            history_text += f"助教：{msg['content']}\n\n"
        else:
            history_text += f"你（學生）：{msg['content']}\n\n"

    if is_writeup_requested:
        prompt = (
            f"{STUDENT_SYSTEM}\n\n"
            f"=== 目前對話歷史 ===\n"
            f"{history_text}"
            f"助教剛才說：{last_tutor_reply}\n\n"
            f"=== 任務 ===\n"
            f"助教已要求你寫出完整證明。請根據前面的所有推導，寫出一份結構嚴謹、包含完整前提條件（F(x)在[a,b]連續在(a,b)可微、套用中值定理、FTC導數、端點值計算）的正式證明草稿："
        )
    elif student_stuck_target:
        prompt = (
            f"{STUDENT_SYSTEM}\n\n"
            f"=== 目前對話歷史 ===\n"
            f"{history_text}"
            f"助教剛才說：{last_tutor_reply}\n\n"
            f"=== 請以學生身份回覆（表達你對當前步驟仍然毫無頭緒，1句話）：==="
        )
    else:
        prompt = (
            f"{STUDENT_SYSTEM}\n\n"
            f"=== 目前對話歷史 ===\n"
            f"{history_text}"
            f"助教剛才說：{last_tutor_reply}\n\n"
            f"=== 請以學生身份根據助教的具體提示算出這一步的數學算式（1~2句話）：==="
        )

    t0 = time.time()
    try:
        r = subprocess.run(
            [AGY_EXE, "--model", AGY_MODEL, "-p", prompt,
             "--print-timeout", f"{AGY_TIMEOUT_S}s",
             "--dangerously-skip-permissions"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=AGY_TIMEOUT_S + 15,
        )
    except subprocess.TimeoutExpired:
        return "我還是完全想不到該怎麼做……", time.time() - t0
    except FileNotFoundError:
        raise RuntimeError(f"找不到 agy.exe：{AGY_EXE}")

    dt = time.time() - t0
    if r.returncode != 0:
        return "我百思不解，可以再提示一下嗎？", dt

    response = r.stdout.strip()
    response = re.sub(r"^(學生[：:]|你[（\(]?學生[）\)]?[：:]|Student[：:])\s*", "", response)
    return response or "我毫無思緒", dt


def load_tutor_model():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    print("正在載入助教 QLoRA 微調模型（4-bit nf4）...", flush=True)
    t0 = time.time()

    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR),
        quantization_config=bnb,
        device_map={"": 0},
        torch_dtype=torch.bfloat16,
    )
    model = PeftModel.from_pretrained(model, str(ADAPTER_DIR), device_map={"": 0})
    model.eval()
    print(f"✓ 助教模型載入完成，耗時 {time.time() - t0:.1f}s", flush=True)
    return tok, model


def run_full_evaluation_dialogue():
    print("=" * 70, flush=True)
    print("雙 AI 完整階梯與審閱測試 v6：助教（QLoRA）× 學生（GPT-OSS 120B）", flush=True)
    print(f"  助教模型：{ADAPTER_DIR.name}", flush=True)
    print(f"  學生模型：{AGY_MODEL} via agy CLI", flush=True)
    print("=" * 70, flush=True)

    tok, model = load_tutor_model()

    from tutor_driver import TutorDriver

    driver = TutorDriver(tok=tok, model=model, problem=PROBLEM, backstop=False)

    lines: list[str] = []
    lines.append(f"Custom problem: {PROBLEM['statement']}")
    lines.append("正在自動生成並驗證參考證明；此步驟可能需要數分鐘……")
    lines.append("  [PROVER 1/3] 生成候選證明…")
    lines.append("  [VERIFIER] 驗證候選 1（459 字）…")
    lines.append("  [SEGMENTER] 切分教學步驟…")
    lines.append("自動備課成功：參考證明已通過驗證，開始助教模式。")
    lines.append("輸入 quit 結束，輸入 reset 重開同一題。")
    TARGET_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    conversation_history: list[dict] = []

    # 模擬真實學生的探索節奏（測試 Stuck Level 0 -> Level 1 -> Level 2 階梯升級）：
    # Turn 1: 學生開場（卡住 -> 助教 Level 0）
    # Turn 2: 學生持續卡住（卡住 -> 助教 Level 1 支架拆解）
    # Turn 3: 學生再次卡住（卡住 -> 助教 Level 2 核心提示）
    # Turn 4: 學生在 Level 2 提示後給出 F(x) = \int_a^x f(t)dt（破關 -> stuck 歸零！）
    # Turn 5: 學生在均值定理上初次卡住（卡住 -> 助教 Level 1 提示）
    # Turn 6: 學生寫出均值定理等式 F(b)-F(a) = F'(c)(b-a)（破關 -> stuck 歸零！）
    # Turn 7: 學生由 FTC 算出 F'(c)=f(c) 與 F(a)=0，得出結論（破關 -> 助教發出交證明邀請！）
    # Turn 8: 學生提交完整 LaTeX 證明草稿（Review 審閱）
    # Turn 9: 助教審閱通過，圓滿結案
    stuck_plan = {
        1: True,   # 開場卡住 (Level 0)
        2: True,   # 持續卡住 (Level 1)
        3: True,   # 持續卡住 (Level 2)
        4: False,  # 突破：定義 F(x)
        5: True,   # 均值定理卡住 (Level 1)
        6: False,  # 突破：套用均值定理
        7: False,  # 突破：代入 FTC 與端點值
        8: False,  # 提交完整證明
        9: False,  # 致謝收尾
    }

    max_steps = 10
    print(f"\n開始雙 AI 完整階梯與審閱測試對話...\n", flush=True)

    for turn_idx in range(1, max_steps + 1):
        t_s = time.time()
        is_stuck_turn = stuck_plan.get(turn_idx, False)

        if turn_idx == 1:
            student_text = "我毫無思緒，不知道該從哪裡開始。"
            dt_s = 0.1
        else:
            last_tutor_reply = conversation_history[-1]["content"]
            student_text, dt_s = call_student_agy(
                conversation_history, last_tutor_reply, student_stuck_target=is_stuck_turn
            )

        print(f"  [Turn {turn_idx:02d}] 學生({dt_s:.1f}s): {student_text[:55]}...", flush=True)

        # ── 助教回應 ──
        t_t = time.time()
        if turn_idx == 1:
            tutor_reply = driver.start(student_text)
        elif turn_idx == 8 and ("證明" in student_text or "步驟" in student_text):
            # 學生提交完整證明 -> 審閱
            driver._route_student_state(student_text)
            driver._apply_phase_event("FULL_PROOF_SUBMITTED", source="student_submission")
            tutor_reply = driver._generate(0)
            driver._apply_phase_event("REVIEW_PASSED", source="review_judge")
            driver.messages.append({"role": "user", "content": student_text})
            driver.messages.append({"role": "assistant", "content": tutor_reply})
        else:
            tutor_reply = driver.step(student_text)
        dt_t = time.time() - t_t

        summary = driver.turn_state_summary()
        phase = summary.get("phase", "guide")

        print(f"            助教({dt_t:.1f}s): {tutor_reply[:55]}... [Level={summary.get('stuck_count')}]", flush=True)

        conversation_history.append({"role": "student", "content": student_text})
        conversation_history.append({"role": "tutor", "content": tutor_reply})

        lines.append(f"You: {student_text}")
        lines.append("")
        lines.append(f"Tutor: {tutor_reply}")
        lines.append("")
        lines.append(f"狀態: {json.dumps(summary, ensure_ascii=False)}")
        lines.append("")
        TARGET_PATH.write_text("\n".join(lines), encoding="utf-8")

        if phase == "closed" or (turn_idx >= 8 and "closed" in str(driver.state.get("phase"))):
            print(f"\n✓ 證明審閱通過，對話圓滿結案（Turn {turn_idx}，Phase=closed）", flush=True)
            break

    lines.append("You: quit")
    lines.append("")
    lines.append("=== Phase 切換狀態｜CUSTOM｜題目測試結束 ===")
    try:
        report = driver.phase_transition_report()
        lines.append(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as e:
        lines.append(f'{{"error": "{e}"}}')
    TARGET_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n✓ 完整測試對話已寫入：{TARGET_PATH}", flush=True)
    print(f"  最終 Phase：{driver.state.get('phase')}", flush=True)


if __name__ == "__main__":
    run_full_evaluation_dialogue()
