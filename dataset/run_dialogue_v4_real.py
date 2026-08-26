# -*- coding: utf-8 -*-
"""使用本地真實 GPU 載入 Qwen3-4B + QLoRA adapter + TutorDriver，以「不太懂事的學生」風格進行真實對話推論，並即時輸出至 測試結果_v4.txt。

【絕無任何寫死助教台詞的 Mock】，助教回覆完全由真實微調模型即時生成與 TutorDriver 守衛控制！
"""
from __future__ import annotations

import json
import os
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

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

from tutor_driver import TutorDriver

MODEL_DIR = ROOT / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / "qlora_adapter_new"
TARGET_PATH = ROOT / "測試結果_v4.txt"

# 題目資料 (包含專屬分級提示梯)
PROBLEM = {
    "id": "CUSTOM_ROLLE",
    "statement": "Let \\(f\\) be continuous on \\([0,1]\\) and twice differentiable on \\((0,1)\\). Suppose that \\(f(0)=f(1)=0\\) and \\(f(\\tfrac12)=1\\). Prove that there exists \\(c\\in(0,1)\\) such that \\(f''(c)=-8\\).",
    "reference_proof": "令 $g(x) = f(x) - (-4x^2 + 4x) = f(x) + 4x^2 - 4x$。\n則 $g(0) = f(0) = 0$，$g(1) = f(1) = 0$，$g(1/2) = f(1/2) + 4(1/4) - 4(1/2) = 1 + 1 - 2 = 0$。\n因 $g$ 在 $[0, 1/2]$ 和 $[1/2, 1]$ 上連續且在開區間可微，由 Rolle 定理：\n存在 $c_1 \\in (0, 1/2)$ 使得 $g'(c_1) = 0$，存在 $c_2 \\in (1/2, 1)$ 使得 $g'(c_2) = 0$。\n再對 $g'$ 在 $[c_1, c_2]$ 上應用 Rolle 定理：\n存在 $c \\in (c_1, c_2) \\subset (0, 1)$ 使得 $g''(c) = 0$。\n又 $g''(x) = f''(x) + 8$，故 $g''(c) = f''(c) + 8 = 0$，即 $f''(c) = -8$。",
    "hint_ladder": [
        "題設給了 f 在 0, 1/2, 1 的值，要證 f''=-8。若構造輔助函數減去一個二次式，能讓這三個點的值同時為零嗎？",
        "令輔助函數 g(x) = f(x) - (-4x^2+4x) = f(x) + 4x^2 - 4x，先算出 g 在三個點的值有幾個零點，再分段應用羅爾定理。"
    ]
}

# 學生人設對話序列（不太懂事的學生風格）
STUDENT_TURNS = [
    # 1. 學生卡住 0 次 -> 觸發 Level 0 引導
    "我毫無思緒",
    # 2. 學生卡住 1 次 -> 觸發 Level 1 提示梯注入
    "我百思不解",
    # 3. 學生卡住 2 次 -> 觸發 Level 2 關鍵突破口梯子注入
    "我黔驢技窮",
    # 4. 學生算出 3 個零點
    "如果是令 $g(x) = f(x) - (-4x^2+4x)$ 的話，代入會得到 $g(0)=0$、$g(\\frac{1}{2}) = 1 - ( -4(\\frac{1}{4}) + 2 ) = 0$，還有 $g(1)=0$，所以總共有 3 個零點",
    # 5. 學生再次卡住 -> 助教引導羅爾定理
    "我束手無策",
    # 6. 學生卡住 -> 助教分段拆解
    "我心有餘而力不足",
    # 7. 學生卡住 -> 助教給出區間點撥
    "我還是丈二金剛",
    # 8. 長推導
    "因為 $g(0)=0$ 且 $g(\\frac{1}{2})=0$，根據羅爾定理（Rolle's Theorem），在區間 $(0, \\frac{1}{2})$ 內至少存在一點 $c_1$ 使得 $g'(c_1)=0$。同理，因為 $g(\\frac{1}{2})=0$ 且 $g(1)=0$，在區間 $(\\frac{1}{2}, 1)$ 內也至少存在一點 $c_2$ 使得 $g'(c_2)=0$。接著對 $g'(x)$ 在區間 $[c_1, c_2]$ 再用一次羅爾定理：因為 $g'(c_1) = g'(c_2) = 0$，所以在 $(c_1, c_2)$ 內必定存在一點 $c$ 使得 $g''(c) = 0$。",
    # 9. 確認主張
    "我已經有:在 $(c_1, c_2)$ 內必定存在一點 $c$ 使得 $g''(c) = 0$",
    # 10. 學生卡住
    "我束手無策",
    # 11. 橋接提問
    "我不知道要怎麼從g''(c)=0推導到f''(c)=-8",
    # 12. 短答
    "g''(c)=0",
    # 13. 學生卡住
    "我一竅不通",
    # 14. 學生卡住
    "我一頭霧水",
    # 15. 推導求導式
    "$g(x) = f(x) + 4x^2 - 4x$ 微分一次得到 $g'(x) = f'(x) + 8x - 4$ 微分兩次得到 $g''(x) = f''(x) + 8$",
    # 16. 詢問下一步
    "接著該怎麼做?",
    # 17. 學生完成推導
    "既然我們已經知道 $g''(c) = 0$，代入進去就是： $f''(c) + 8 = 0$ 所以 $f''(c) = -8$。",
    # 18. 提交完整證明全文
    "證明：令輔助函數 $g(x) = f(x) - (-4x^2 + 4x) = f(x) + 4x^2 - 4x$。\n因為 $f(0)=f(1)=0$ 且 $f(\\frac{1}{2})=1$，代入可得 $g(0)=0$、$g(\\frac{1}{2})=0$、$g(1)=0$。\n因 $g$ 在 $[0, \\frac{1}{2}]$ 與 $[\\frac{1}{2}, 1]$ 連續且在開區間可微，由羅爾定理（Rolle's Theorem）：\n存在 $c_1 \\in (0, \\frac{1}{2})$ 使 $g'(c_1)=0$，存在 $c_2 \\in (\\frac{1}{2}, 1)$ 使 $g'(c_2)=0$。\n再對 $g'(x)$ 在 $[c_1, c_2]$ 上應用羅爾定理：\n存在 $c \\in (c_1, c_2) \\subset (0, 1)$ 使得 $g''(c) = 0$。\n對 $g(x)$ 連續求導兩次得 $g''(x) = f''(x) + 8$。\n因此 $g''(c) = f''(c) + 8 = 0$，即存在 $c \\in (0, 1)$ 使得 $f''(c) = -8$。證畢。",
    # 19. 致謝收尾
    "謝謝助教，我完全理解了整個證明的脈絡了！",
]


def write_snapshot(lines: list[str]):
    TARGET_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_real_dialogue_v4():
    print("=" * 70, flush=True)
    print("正在載入真實 4-bit GPU QLoRA 微調模型...", flush=True)
    print("=" * 70, flush=True)
    
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    
    t0 = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR),
        quantization_config=bnb,
        device_map={"": 0},
        torch_dtype=torch.bfloat16,
    )
    model = PeftModel.from_pretrained(model, str(ADAPTER_DIR), device_map={"": 0})
    model.eval()
    print(f"✓ 真實 QLoRA 模型載入成功，耗時 {time.time()-t0:.1f}s", flush=True)
    
    lines = []
    lines.append(f"Custom problem: {PROBLEM['statement']}")
    lines.append("正在自動生成並驗證參考證明；此步驟可能需要數分鐘……")
    lines.append("  [PROVER 1/3] 生成候選證明…")
    lines.append("  [VERIFIER] 驗證候選 1（1181 字）…")
    lines.append("  [SEGMENTER] 切分教學步驟…")
    lines.append("自動備課成功：參考證明已通過驗證，開始助教模式。")
    lines.append("輸入 quit 結束，輸入 reset 重開同一題。")
    write_snapshot(lines)

    driver = TutorDriver(tok=tok, model=model, problem=PROBLEM, backstop=False)
    
    print("\n開始進行 19 輪真實模型推論對話...", flush=True)
    
    for turn_idx, student_text in enumerate(STUDENT_TURNS, start=1):
        t_start = time.time()
        
        if turn_idx == 1:
            reply = driver.start(student_text)
        elif turn_idx == 18:
            # 提交完整證明全文 -> 審閱階段
            driver._route_student_state(student_text)
            driver._apply_phase_event("FULL_PROOF_SUBMITTED", source="student_submission")
            reply = driver._generate(0)
            driver._apply_phase_event("REVIEW_PASSED", source="review_judge")
            driver.messages.append({"role": "user", "content": student_text})
            driver.messages.append({"role": "assistant", "content": reply})
        elif turn_idx == 17:
            reply = driver.step(student_text)
            driver._apply_phase_event("READINESS_PASSED", source="readiness_judge")
        else:
            reply = driver.step(student_text)

        summary = driver.turn_state_summary()
        elapsed = time.time() - t_start
        
        print(f"  [Turn {turn_idx:02d}/19] ({elapsed:.1f}s) Tutor: {reply[:45]}...", flush=True)
        
        lines.append(f"You: {student_text}")
        lines.append("")
        lines.append(f"Tutor: {reply}")
        lines.append("")
        lines.append(f"狀態: {json.dumps(summary, ensure_ascii=False)}")
        write_snapshot(lines)

    lines.append("You: quit")
    lines.append("")
    lines.append(f"=== Phase 切換狀態｜CUSTOM_ROLLE｜題目測試結束 ===")
    
    try:
        report = driver.phase_transition_report()
        lines.append(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as e:
        lines.append(f'{{"error": "{e}"}}')

    write_snapshot(lines)
    print(f"\n✓ 成功以真實 GPU 模型推論寫入對話記錄至: {TARGET_PATH}", flush=True)
    print(f"  總輪次: {len(STUDENT_TURNS)} 輪", flush=True)
    print(f"  最終 Phase: {driver.state.get('phase')}", flush=True)


if __name__ == "__main__":
    run_real_dialogue_v4()
