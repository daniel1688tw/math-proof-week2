# -*- coding: utf-8 -*-
"""雙 AI 對話腳本 v5：
  - 助教：本機/實驗室 4090 QLoRA 微調模型（Qwen3-4B + qlora_adapter_new）
  - 學生：agy CLI 呼叫 GPT-OSS 120B，動態依助教回應生成「不太懂微積分的學生」反應

用法：
  # 助教用本機 GPU（預設）
  python dataset/run_dialogue_v5_dual_ai.py

  # 助教用遠端實驗室 4090（透過 SSH + Python 轉發，未來可擴充）
  TUTOR_REMOTE=1 python dataset/run_dialogue_v5_dual_ai.py

學生輪數由 MAX_TURNS 控制（預設 20），對話到助教判定完成後自動結束。
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
AGY_MODEL = os.environ.get("AGY_STUDENT_MODEL", "Gemini 3.7 Flash (Low)")
AGY_TIMEOUT_S = int(os.environ.get("AGY_TIMEOUT_S", "60"))

MAX_TURNS = int(os.environ.get("MAX_TURNS", "20"))
TARGET_PATH = ROOT / "測試結果_v5.txt"

MODEL_DIR = ROOT / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / "qlora_adapter_new"

# ── 題目（含分級提示梯）──────────────────────────────────────────────────────
PROBLEM = {
    "id": "CUSTOM_ROLLE",
    "statement": (
        r"Let \(f\) be continuous on \([0,1]\) and twice differentiable on \((0,1)\). "
        r"Suppose that \(f(0)=f(1)=0\) and \(f(\tfrac12)=1\). "
        r"Prove that there exists \(c\in(0,1)\) such that \(f''(c)=-8\)."
    ),
    "reference_proof": (
        r"令 $g(x) = f(x) - (-4x^2 + 4x) = f(x) + 4x^2 - 4x$。"
        "\n"
        r"則 $g(0) = f(0) = 0$，$g(1) = f(1) = 0$，$g(1/2) = f(1/2) + 4(1/4) - 4(1/2) = 1 + 1 - 2 = 0$。"
        "\n"
        r"因 $g$ 在 $[0, 1/2]$ 和 $[1/2, 1]$ 上連續且在開區間可微，由 Rolle 定理："
        "\n"
        r"存在 $c_1 \in (0, 1/2)$ 使得 $g'(c_1) = 0$，存在 $c_2 \in (1/2, 1)$ 使得 $g'(c_2) = 0$。"
        "\n"
        r"再對 $g'$ 在 $[c_1, c_2]$ 上應用 Rolle 定理："
        "\n"
        r"存在 $c \in (c_1, c_2) \subset (0, 1)$ 使得 $g''(c) = 0$。"
        "\n"
        r"又 $g''(x) = f''(x) + 8$，故 $g''(c) = f''(c) + 8 = 0$，即 $f''(c) = -8$。"
    ),
    "hint_ladder": [
        "題設給了 f 在 0, 1/2, 1 的值，要證 f''=-8。若構造輔助函數減去一個二次式，能讓這三個點的值同時為零嗎？",
        "令輔助函數 g(x) = f(x) - (-4x^2+4x) = f(x) + 4x^2 - 4x，先算出 g 在三個點的值有幾個零點，再分段應用羅爾定理。",
    ],
}

# ── 學生 system prompt（GPT-OSS 120B 扮演不太懂微積分的學生）───────────────────
STUDENT_SYSTEM = """\
你是一位大學微積分課的學生，正在和助教進行一對一蘇格拉底式輔導。

你的特徵：
- 對微積分基礎有一定了解（會求導、知道羅爾定理的名字），但對如何「構造輔助函數」來應用定理感到困惑
- 個性不太積極，容易卡住，但會誠實表達自己的困惑
- 偶爾會猜測或嘗試，但往往差一步或邏輯不完整
- 不會一次就說出完整正確答案，而是逐步被引導才能前進
- 語氣自然、口語，有時用「啊」「嗯」「這樣嗎」等語氣詞
- 不會一直說「我不知道」，而是會根據助教的提示嘗試回答或追問

規則：
- 每次只回應一個短回覆（1~3 句話），不要一次把完整證明說出來
- 根據助教的問題做出符合你能力的回應：如果助教已給了很明確的提示，你應該能跟著做
- 如果你真的完全不懂，可以誠實說，但要說清楚哪裡不懂
- 不要重複助教說過的話，而是提出自己的想法或疑問
- 當你逐漸理解後，嘗試用自己的話表達
- 只輸出學生的純文字回覆，不要加任何前綴（如「學生：」）

當前題目：
Let f be continuous on [0,1] and twice differentiable on (0,1).
Suppose that f(0)=f(1)=0 and f(1/2)=1.
Prove that there exists c in (0,1) such that f''(c)=-8.
"""


# ── agy 學生回應生成 ──────────────────────────────────────────────────────────
def call_student_agy(conversation_history: list[dict]) -> tuple[str, float]:
    """用 agy GPT-OSS 120B 動態生成學生下一句回應。

    conversation_history: [{"role": "tutor"/"student", "content": "..."}]
    回傳 (學生回應文字, 耗時秒數)
    """
    # 把對話歷史組成 prompt
    history_text = ""
    for msg in conversation_history[-10:]:  # 只取最近 10 輪，避免 prompt 過長
        if msg["role"] == "tutor":
            history_text += f"助教：{msg['content']}\n\n"
        else:
            history_text += f"你（學生）：{msg['content']}\n\n"

    prompt = (
        f"{STUDENT_SYSTEM}\n\n"
        f"=== 目前對話記錄 ===\n"
        f"{history_text}"
        f"=== 請輸出你（學生）的下一句回應 ==="
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
        return "（學生逾時無回應）", time.time() - t0
    except FileNotFoundError:
        raise RuntimeError(
            f"找不到 agy.exe：{AGY_EXE}\n"
            "請先安裝：irm https://antigravity.google/cli/install.ps1 | iex"
        )

    dt = time.time() - t0

    if r.returncode != 0:
        stderr = r.stderr.strip()
        return f"（agy 錯誤 exit={r.returncode}: {stderr[:80]}）", dt

    response = r.stdout.strip()
    # 移除可能的前綴（如「學生：」「你：」）
    response = re.sub(r"^(學生[：:]|你[（\(]?學生[）\)]?[：:]|Student[：:])\s*", "", response)
    return response or "（無回應）", dt


# ── 判斷對話是否完成 ──────────────────────────────────────────────────────────
_DONE_RE = re.compile(
    r"(謝謝|感謝|懂了|理解了|完全明白|搞懂|學會|我會了|明白了|太棒了|收穫良多"
    r"|thank|got it|understand|makes sense|clear now)",
    re.I,
)


def is_dialogue_done(phase: str, student_text: str) -> bool:
    """判定對話是否應該結束（助教判定 closed 或學生致謝）"""
    if phase in ("closed",):
        return True
    if phase == "guide" and _DONE_RE.search(student_text):
        return True
    return False


# ── 助教模型載入 ──────────────────────────────────────────────────────────────
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


# ── 主程式 ────────────────────────────────────────────────────────────────────
def run_dual_ai_dialogue():
    # 驗證 agy 存在
    if not Path(AGY_EXE).exists():
        print(f"[ERROR] 找不到 agy.exe：{AGY_EXE}", flush=True)
        print("請先執行：irm https://antigravity.google/cli/install.ps1 | iex", flush=True)
        sys.exit(1)

    print("=" * 70, flush=True)
    print("雙 AI 對話 v5：助教（QLoRA 微調）× 學生（GPT-OSS 120B）", flush=True)
    print(f"  助教模型：{ADAPTER_DIR.name}", flush=True)
    print(f"  學生模型：{AGY_MODEL} via agy CLI", flush=True)
    print("=" * 70, flush=True)

    # 載入助教
    tok, model = load_tutor_model()

    from tutor_driver import TutorDriver

    driver = TutorDriver(tok=tok, model=model, problem=PROBLEM, backstop=False)

    lines: list[str] = []
    lines.append(f"題目：{PROBLEM['statement']}")
    lines.append(f"助教模型：{ADAPTER_DIR.name}（4-bit nf4 QLoRA）")
    lines.append(f"學生模型：{AGY_MODEL}（via agy CLI）")
    lines.append("")
    TARGET_PATH.write_text("\n".join(lines), encoding="utf-8")

    conversation_history: list[dict] = []  # [{"role": "tutor"/"student", "content": ...}]

    print(f"\n開始雙 AI 對話（最多 {MAX_TURNS} 輪）...\n", flush=True)

    for turn_idx in range(1, MAX_TURNS + 1):
        # ── 學生回應（GPT-OSS 120B）──
        t_s = time.time()
        if turn_idx == 1:
            # 第一輪：學生主動開口（對題目感到困惑）
            student_prompt = (
                f"{STUDENT_SYSTEM}\n\n"
                f"這是你第一次看到這道題目，請說出你的第一個反應或困惑（1~2句話）：\n"
                f"題目：{PROBLEM['statement']}"
            )
            r = subprocess.run(
                [AGY_EXE, "--model", AGY_MODEL, "-p", student_prompt,
                 "--print-timeout", f"{AGY_TIMEOUT_S}s",
                 "--dangerously-skip-permissions"],
                capture_output=True, text=True, encoding="utf-8",
                timeout=AGY_TIMEOUT_S + 15,
            )
            student_text = r.stdout.strip() if r.returncode == 0 else "我完全不知道從哪裡開始..."
            student_text = re.sub(r"^(學生[：:]|你[（\(]?學生[）\)]?[：:])\s*", "", student_text)
            dt_s = time.time() - t_s
        else:
            student_text, dt_s = call_student_agy(conversation_history)

        print(f"  [Turn {turn_idx:02d}] 學生({dt_s:.1f}s): {student_text[:60]}...", flush=True)

        # ── 助教回應（QLoRA 微調模型）──
        t_t = time.time()
        if turn_idx == 1:
            tutor_reply = driver.start(student_text)
        else:
            tutor_reply = driver.step(student_text)
        dt_t = time.time() - t_t

        summary = driver.turn_state_summary()
        phase = summary.get("phase", "guide")

        print(f"            助教({dt_t:.1f}s): {tutor_reply[:60]}...", flush=True)

        # 寫入記錄
        conversation_history.append({"role": "student", "content": student_text})
        conversation_history.append({"role": "tutor", "content": tutor_reply})

        lines.append(f"[Turn {turn_idx:02d}] 學生：{student_text}")
        lines.append("")
        lines.append(f"[Turn {turn_idx:02d}] 助教：{tutor_reply}")
        lines.append("")
        lines.append(f"         狀態：{json.dumps(summary, ensure_ascii=False)}")
        lines.append("")
        TARGET_PATH.write_text("\n".join(lines), encoding="utf-8")

        # 判斷是否結束
        if is_dialogue_done(phase, student_text) and turn_idx >= 5:
            print(f"\n✓ 對話自然結束（Turn {turn_idx}，Phase={phase}）", flush=True)
            break
    else:
        print(f"\n✓ 已達最大輪次 {MAX_TURNS} 輪", flush=True)

    lines.append("=== 對話結束 ===")
    try:
        report = driver.phase_transition_report()
        lines.append(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as e:
        lines.append(f'{{"error": "{e}"}}')
    TARGET_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n✓ 完整對話已寫入：{TARGET_PATH}", flush=True)
    print(f"  最終 Phase：{driver.state.get('phase')}", flush=True)


if __name__ == "__main__":
    run_dual_ai_dialogue()
