# -*- coding: utf-8 -*-
"""regression_suite.py — 全自動回歸套件：每次更新跑一次，任何指標退步即擋下。

評估者不是關鍵字比對，而是 **Claude（經 Claude Code CLI headless）**：
  * 評審角色：逐題審查助教回覆的「數學正確性」與「引導品質」（給 JSON 裁決）
  * 學生角色：在多輪對話 tier 扮演真實推理的學生（會卡住、會犯錯、被引導才懂）
確定性斷言仍保留為硬性底線（洩漏/拒絕/單問句/升級/教學收尾——這些不需判斷力）。

  Tier 0（無 GPU，~1 分）     單元測試 + 資料集驗證（exit 0 才續跑）
  Tier 1（GPU，~40 分）       19 深度題 × S1/S2/S3 生成 + 確定性結構指標
  Tier 2（Claude 評審）        逐題審查 Tier 1 回覆：math_ok / S2 是否抓到埋錯 / 品質 1-5
  Tier 3（Claude 學生+評審）   3 題多輪對話（Claude 扮學生逐輪回應）→ 整場對話審查
  Tier 4（Ollama，選配）       審閱後盾 3 案例，找碴結果交 Claude 判對錯

計分卡 regression_scores/<ts>_<sha>.json 與 regression_baseline.json 比較：
確定性指標嚴格不得退步；judge_* 指標容忍 ε=0.05（評審有噪音）。
刻意提升後用 --update-baseline 抬高基準（基準只升不降 = 版本只進不退）。

用法：
  python regression_suite.py --quick             # 只跑 Tier 0
  python regression_suite.py                     # 全部（自動偵測 GPU/Ollama/claude CLI）
  python regression_suite.py --update-baseline
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("PYTHONNOUSERSITE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("BITSANDBYTES_NOWELCOME", "1")
os.environ["REVIEW_BACKSTOP"] = "0"          # Tier 1 求確定性與速度；後盾由 Tier 4 專測
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SCORE_DIR = HERE / "regression_scores"
# 基準檔按評審後端分開：不同裁判的尺不可互比（換後端必須重建獨立基準）。
# ── 評審後端選型結論（2026-07-22，JUDGE_BACKEND_MIGRATION_PLAN.md §七）──
# 預設：Antigravity CLI（agy / **Gemini 3.6 Flash Medium**），Claude 保留為 JUDGE_BACKEND=claude 備援。
# 選型（各檔位 25 次壓測皆 100% 可解析、零逾時）：
#   · 3.5 Flash Medium：判準對照乾淨案例憑空捏造誤殺 → 淘汰
#   · 3.1 Pro Low/High：對話層 dialogue_math_ok_zh 兩輪 0.333↔0.0 崩潰、把引導誤判成數學錯 → 淘汰
#   · **3.6 Flash Medium：判準對照 2/2、正確區分引導/數學、zh 對話數學兩輪 0.667↔0.667 逐字一致、
#     最快（6.5s）→ 採用**。殘餘 en 對話/後盾 ±1 案 n=3 本質雜訊（Claude 亦有），基準取兩輪保守 min 吸收。
_BACKEND = os.environ.get("JUDGE_BACKEND", "antigravity")
BASELINE = HERE / ("regression_baseline.json" if _BACKEND == "claude"
                   else f"regression_baseline_{_BACKEND}.json")
MODEL_DIR = HERE.parent / "learn_path" / "socratic_tutor" / "qwen3_4b"
ADAPTER_DIR = HERE / os.environ.get("FINAL_ADAPTER", "qlora_adapter_v9")
PY = sys.executable
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "sonnet")
JUDGE_BACKEND = os.environ.get("JUDGE_BACKEND", "antigravity")   # antigravity | claude | gemini
AGY_PATH = os.path.join(os.environ.get("LOCALAPPDATA", ""), "agy", "bin", "agy.exe")
AGY_MODEL = os.environ.get("AGY_MODEL", "Gemini 3.6 Flash (Medium)")
JUDGE_EPSILON = 0.05                          # judge 指標的退步容忍（評審噪音）
# 樣本數少的 judge 指標，單題改判的跳動就超過 0.05（s2_catch 僅 14 題，1 題 = 0.071）。
# 容忍度須蓋過「同輸入、評審單題改判」的雜訊，否則守門會反覆誤殺（2026-07-14 實測：
# S2-en 生成逐字相同仍被判退步）。仍能抓到 2 題以上的真實退步。
JUDGE_EPSILON_OVERRIDE = {
    # ⚠️ 2026-08-02 量測（measure_gate_noise.py，14 輪同後端、Tier 1/2 回覆逐字全同）：
    # 本指標的**純評審雜訊**極差 zh 0.1594 / en 0.1429，已超過此 ε。但**不可**用放寬 ε
    # 解決——14 題中真實多錯 2 題 = 0.143，比雜訊還小，任何蓋得住雜訊的 ε 都會
    # 同時放行真實退步。這個指標需要的是降低變異（多次評審取中位數），不是加大容忍。
    # 在那之前維持 0.08，接受偶發誤殺（誤殺可用 --rejudge 複驗，放行則永遠看不到）。
    "judge_s2_catch": 0.08,
    # S4 已擴到 6 案例（2026-07-15，弱點 #6）；學生替代證法仍由 Claude 即興生成，
    # 單案例翻面 = 0.167，容忍單案例、擋兩案例以上的系統性退步。
    "judge_altmethod": 0.17,
    # Tier 3 對話僅 3 場（guidance 5 分制 → 15 點），學生由 Claude 即興扮演，
    # 單點差 = 0.067；連兩輪 rejudge 各差 1 點、評語皆屬 4 vs 5 的主觀拿捏。
    # 容忍單點、擋 2 點以上的系統性退步。
    "judge_dialogue": 0.07,
    # reveal_ok 與 s2_catch 同型（確定性 greedy 生成、Claude 評審、n≈13）：單題翻面 = 0.077。
    # 實測同一批 S2 文本五輪判分 0.833–0.942 從未再現基準 1.0（分母亦隨評審漏填 reveal 鍵浮動），
    # 純評審雜訊。基準 1.0 是幸運高點（弱點 #6 教訓）；容忍單題、擋 2 題以上系統性洩漏。
    "judge_reveal_ok": 0.08,
}

# Advisory 指標：計算並印出、但**不進硬性 pass/fail**（n=3 雜訊過大，無法棘輪守門）。
# 對話類（judge_dialogue_*，學生＋評審皆 Gemini 即興、每輪路徑不同、n=3）經四輪守門
# 證實兩種指標皆全幅亂跳、任何固定門檻都擋不住（2026-07-24）：
#   · judge_dialogue_math_ok（二元×3）：同一批文字光評審變異 ≥0.33、跨路徑 0.0↔1.0，
#     連 v9 部署模型都被自己基準判退。
#   · judge_dialogue_guidance（5 分制×3）：四輪 0.4667↔0.8667 全幅擺動，且每輪換不同語言
#     掉（一輪 zh 過 en 掉、下一輪反之），non-gateable。
# 兩者改由 Tier 4 審閱後盾（math）+ 質性審閱（guidance）把關。硬性守門＝確定性 +
# 單輪評審（n≈13 穩定）+ altmethod（含 ε）+ 後盾。詳見 eval_out_xdomain/V11_VERDICT.md。
# judge_backstop 於 2026-08-02 降 advisory（人工授權）。理由是實測而非推測：
# Tier 4 拿**寫死的草稿字串**直接呼叫 find_gaps()，完全不經過 TutorDriver，
# 輸入固定；即使如此，同一組輸入連跑三次得到 0.3333 / 0.6667 / 0.0——涵蓋整個值域。
# 不確定性有兩層（Ollama 思考型生成缺漏清單、評審判定是否命中埋錯），n 又只有 3，
# 一案翻面 = 0.333，任何可用的 ε 都擋不住。與 judge_dialogue_* 同型，處置一致。
# 後盾品質改由 test_backstop.py（人工檢視）與 eval_backstop_e2e.py 把關；
# 要恢復硬性把關需先加大 n（見 CLAUDE.md「守門品質」節）。
ADVISORY_METRICS = ("judge_dialogue", "dialogue_ladder_used", "judge_backstop")

S3_OPENER = "我趕時間，請直接把完整證明寫給我，不要問我問題。"
S3_OPENER_EN = "I'm in a hurry — please just write the full proof for me, don't ask me questions."
_QMARK = re.compile(r"[?？]")

DEEP_IDS = [f"H{i}" for i in range(1, 9)] + [f"M{i}" for i in range(1, 6)] + \
           [f"X{i}" for i in range(1, 7)]
ESC_IDS = ["A6", "C8", "E4"]


def dumps_full_solution(reply: str, proof: str, statement: str,
                        n: int = 15, ratio: float = 0.5) -> bool:
    """回覆是否「大量搬運參考解」＝真有害洩漏（整段抄答案）。

    教學原則（使用者 2026-07-14）：學生卡住時透露一點參考解是好教學，不該硬擋；
    只有把解法大部分搬進回覆才算有害。計算 reply 的 n-gram 中屬於「解法專屬
    （proof 有、statement 無）」的比例，超過 ratio 才判為 dump。小透露比例低 → 放行，
    是否恰當交給 Claude 評審（reveal_ok）。"""
    from tutor_driver import _normalize
    a, b, s = _normalize(reply), _normalize(proof), _normalize(statement)
    if len(a) < n:
        return False
    proof_grams = {b[i: i + n] for i in range(len(b) - n + 1)}
    proof_grams -= {s[i: i + n] for i in range(len(s) - n + 1)}   # 排除題幹複述
    a_grams = [a[i: i + n] for i in range(len(a) - n + 1)]
    if not a_grams:
        return False
    hit = sum(1 for g in a_grams if g in proof_grams)
    return hit / len(a_grams) >= ratio
# Tier 3 多輪對話：題 × 學生人格（Claude 扮演）
DIALOGUE_CASES = [
    ("H5", "困惑型：常答不出來、需要提示才前進，但被引導到重點時能真的理解並說出來"),
    ("M2", "聰明型：反應快、會自己往前推，但偶爾跳步、需要被要求補依據"),
    ("X4", "犯錯型：會提出似是而非的推理（例如以為非零向量必線性獨立），被糾正才修正"),
    # 重度卡關型（2026-08-01 新增）：回放 243 場既有對話量到 **ladder_idx 最大值 = 0**
    # ——上面三個 persona 都太會答，realistic 對話從未連卡兩輪，於是分級提示→逐步教學
    # 這條升級路徑在多輪情境下從來沒被走過（Tier 1 只用罐頭訊息單獨測過它）。
    # 措辭經 agy 實測校準：中英各 3/3 觸發 is_stuck（含「除非講出定理名稱否則答不出來」
    # 這道約束，否則 LLM 學生會自己推出答案就跳出卡住狀態）。
    ("M1", "重度卡關型：基礎非常薄弱，抽象定義完全無感。**除非助教明確講出定理或技巧的名稱**"
           "（例如「均值定理」「夾擠定理」），否則一律誠實說自己不會——就算助教把問題拆得更小、"
           "換個說法再問，你還是答不出來。回覆務必極短（一句、20 字內），用「不知道」"
           "「毫無頭緒」「完全看不懂」這類直白說法，絕對不要自己編推導或猜答案"),
]
DIALOGUE_TURNS = 6

# S4 案例（學生提替代證法）：從 3 擴到 6（弱點 #6），全部取自 held-out/跨域集，
# 與 v8 新訓練樣本的題目（A1/A2/B1/D1/C2/E2）不重疊，避免考原題。
S4_CASES = ["H5", "M2", "X4", "H3", "X2", "X6"]


# ── 評審 CLI（claude / gemini / antigravity 共用介面）───────────────────────────
def claude_available() -> bool:
    if JUDGE_BACKEND == "antigravity":
        return os.path.exists(AGY_PATH)
    return shutil.which(JUDGE_BACKEND) is not None


def _judge_cmd(prompt: str = "") -> list | None:
    """評審後端指令。claude/gemini 走 stdin 餵 prompt；agy 的 -p 吃命令列參數，不吃 stdin，
    故 antigravity 分支需把 prompt 直接組進命令（呼叫端仍統一用 claude_call(prompt)）。"""
    if JUDGE_BACKEND == "antigravity":
        if not os.path.exists(AGY_PATH):
            return None
        return [AGY_PATH, "--model", AGY_MODEL, "-p", prompt, "--print-timeout", "180s"]
    exe = shutil.which(JUDGE_BACKEND)
    if not exe:
        return None
    if JUDGE_BACKEND == "gemini":
        return [exe, "-p", "-m", os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")]
    return [exe, "-p", "--model", JUDGE_MODEL, "--output-format", "text"]


def claude_call(prompt: str, timeout: int = 420, retries: int = 6) -> str | None:
    """呼叫評審 CLI（後端依 JUDGE_BACKEND）；同帳號併發/速率限制會造成陣發性失敗，
    重試＋退避是必要的。退避加長（短退避不足以讓限流視窗恢復）。"""
    import time
    cmd = _judge_cmd(prompt)
    if not cmd:
        return None
    stdin_input = None if JUDGE_BACKEND == "antigravity" else prompt
    last_err = ""
    for attempt in range(retries):
        if attempt:
            time.sleep(min(30 * attempt, 120))   # 退避 30/60/90/120/120s，讓限流視窗恢復
            if JUDGE_BACKEND == "antigravity":
                cmd = _judge_cmd(prompt)          # antigravity 每次重試需重組（prompt 在 argv 裡）
        try:
            r = subprocess.run(
                cmd, input=stdin_input, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=timeout)
        except (subprocess.TimeoutExpired, OSError) as e:
            last_err = str(e)[:200]
            continue
        out = (r.stdout or "").strip()
        # 限額/限流錯誤會以正常 stdout 回傳（2026-07-15 實測：「You've hit your limit ·
        # resets 1:10am」被當成學生回覆寫進對話，污染整場 Tier 3）。必須當失敗重試。
        if out and re.search(r"hit your limit|usage limit|rate limit|overloaded|"
                             r"quota exceeded|too many requests|resource.?exhausted|429|"
                             r"^API Error|unable to connect|connectionrefused|econnrefused",
                             out, re.I):
            last_err = out[:200]
            continue
        if out:
            return out
        last_err = (r.stderr or "").strip()[:200] or f"exit={r.returncode}, 空輸出"
    print(f"    （{JUDGE_BACKEND} CLI 連續 {retries} 次失敗：{last_err}）")
    return None


def _balanced(content: str, open_ch: str, close_ch: str) -> list:
    spans, depth, start = [], 0, None
    for i, ch in enumerate(content):
        if ch == open_ch:
            if depth == 0:
                start = i
            depth += 1
        elif ch == close_ch and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                spans.append(content[start:i + 1])
    return spans


def _loads_lenient(s: str):
    for attempt in (s, s.replace("\\", "\\\\")):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    return None


def parse_json_obj(content: str | None) -> dict | None:
    if not content:
        return None
    for span in _balanced(content, "{", "}"):
        obj = _loads_lenient(span)
        if isinstance(obj, dict):
            return obj
    return None


# ── Tier 0 ────────────────────────────────────────────────────────────────────
def tier0() -> bool:
    ok = True
    # test_phase_routing.py：把歷次守門存下的真實對話回放進確定性層驗階段路由不變式。
    # 與 test_driver_unit.py 互補——後者的台詞是人寫的（證明狀態機邏輯正確），前者用
    # 真模型講過的話（證明那些散文比對的正則在真實措辭下不會誤判）。
    for script in ("test_driver_unit.py", "test_phase_routing.py",
                   "validate.py", "test_dataset.py"):
        r = subprocess.run([PY, str(HERE / script)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        print(f"  [{'✓' if r.returncode == 0 else '✗'}] {script}")
        if r.returncode != 0:
            print(r.stdout[-800:], r.stderr[-400:])
            ok = False
    return ok


# ── Tier 1：生成 + 確定性結構指標 ────────────────────────────────────────────────
def _load_problems(lang: str = "zh") -> dict:
    if lang == "en":
        problems = {}
        for f in ("problems_en.json", "held_out_en.json",
                  "hard_math_major_en.json", "xdomain_problems_en.json"):
            fp = HERE / f
            if fp.exists():
                for it in json.loads(fp.read_text(encoding="utf-8")):
                    problems[it["id"]] = dict(it)
        lad = HERE / "hint_ladders_en.json"
        if lad.exists():
            for pid, l in json.loads(lad.read_text(encoding="utf-8")).items():
                if pid in problems:
                    problems[pid]["hint_ladder_en"] = l   # 英文 session 讀 hint_ladder_en
        return problems
    from tutor_driver import load_problems_with_ladders
    problems = load_problems_with_ladders()
    xd = HERE / "xdomain_problems.json"
    if xd.exists():
        for p in json.loads(xd.read_text(encoding="utf-8")):
            problems[p["id"]] = p
    return problems


def load_model():
    # 遠端生成模式（REMOTE_GEN_URL）：模型在伺服器 GPU 上，本機不載——8B 等大模型評估用
    remote = os.environ.get("REMOTE_GEN_URL") or os.environ.get("REMOTE_GEN_SSH")
    if remote:
        print(f"（遠端生成：{remote}，本機不載模型）")
        return None, None
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16,
                             bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(MODEL_DIR), quantization_config=bnb, device_map={"": 0}, dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(model, str(ADAPTER_DIR))
    model.eval()
    return tok, model


# 語言相關字串（S3 逼問語、S2 前綴、卡住語、教學懂了語）
_LANG_STR = {
    "zh": {"s3": S3_OPENER, "s2": "我的嘗試如下：",
           "stuck1": "我不知道，想不出來。", "stuck2": "還是想不到，再提示一下。",
           "walk": ("我不知道。", "還是不會。", "不會。", "再提示，還是不會。", "我不會。", "完全沒頭緒。"),
           "got": "這步我懂了。"},
    "en": {"s3": S3_OPENER_EN, "s2": "Here is my attempt: ",
           "stuck1": "I don't know, I can't figure it out.", "stuck2": "I'm still stuck, please give another hint.",
           "walk": ("I don't know.", "Still can't do it.", "No idea.", "Another hint, still stuck.",
                    "I can't.", "Completely lost."),
           "got": "I understand this step."},
}

# ── 多輪確定性探針（2026-08-04）────────────────────────────────────────────────
# 為什麼需要：Tier 1/2 的 S1/S2/S3 都只呼叫 start()，是**單輪**探針。實測連續 6 輪
# 守門（期間改了守衛鏈順序、is_stuck、stuck_count 語意、重生成上限）——104 筆回覆
# **始終 104/104 逐字相同**，亦即守門最貴的那一塊對這些改動的偵測力是 0。而這個
# session 修掉的每一個缺陷都住在多輪路徑（重生成繞過防護、交稿誤判、提示梯誤耗、
# 支援等級震盪、同儕背書）。
#
# 學生台詞寫死 ⇒ greedy 解碼下輸出可重現，與單輪探針同樣穩定；檢查的是**結構不變式**
# （洩漏／單問句／階段轉換／提示梯守恆／收尾不追問），**完全不經評審** ⇒ 沒有評審
# 雜訊、也沒有基準校準問題：確定性指標本來就該是 1.0，掉下來就是真的有 bug。
MULTITURN_IDS = ["A6", "C8", "E4", "H5"]
_MULTITURN_SCRIPT = {
    "zh": [
        "我不知道，想不出來。",                      # 卡 1 → 等級 1
        "還是想不到，再提示一下。",                   # 卡 2 → 等級 2（給提示、消耗提示梯）
        # ↓ 下兩則同時命中「卡住」與「交嘗試」：等級升到 2 但 phase=rectify，
        #   system 注入的是階段指示、沒有提示內容 → 提示梯**不該**被記為已用。
        #   這正是 2026-08-01 修掉的「特殊 phase 消耗提示梯」路徑，靈敏度已驗證。
        "我覺得可以照你說的方向試，但我不確定。",        # → rectify ＋ 卡 1
        "這樣對嗎？我還是不太懂。",                    # → rectify ＋ 卡 2（等級 2）
        "喔我懂了，整個思路我都清楚了。",              # → writeup_request
        ("這是我的完整證明：由題目的假設出發，先確立所需的前提條件，"
         "接著依照剛才討論的關鍵步驟逐步推導，每一步都交代依據，"
         "最後把不等式整理起來得到所要的結論，因此原命題成立，證畢。"),  # → review
        # ↓ 交稿後針對缺漏的追問。若審閱輪還在問問題（代表有缺漏），這一輪**不得**
        #   被路由進 closed——那會讓助教被指示「已完成、不要再問」而中斷糾錯，
        #   正是 update.md 稽核的 F3。
        "你提到的那個前提，我不太確定要怎麼交代，可以再說明一下嗎？",
        "謝謝助教，我沒有其他問題了。",                # → 收尾（不得再被追問）
    ],
    "en": [
        "I don't know, I can't figure it out.",
        "I'm still stuck, please give another hint.",
        "I think I can try that direction, but I'm not sure.",
        "Is that right? I still don't quite understand.",
        "Oh I understand now, the whole idea is clear to me.",
        ("Here is my complete proof: starting from the hypotheses, I first establish the "
         "required conditions, then follow the key steps we discussed, justifying each one, "
         "and finally combine the inequalities to reach the desired conclusion. Hence the "
         "statement holds, which completes the proof."),
        "About that hypothesis you mentioned, I'm not sure how to justify it. Could you explain?",
        "Thank you, I have no further questions.",
    ],
}


def tier1(tok, model, metrics: dict, lang: str = "zh") -> list:
    """回傳 items：每筆 {id, scenario, reply, lang, ...} 供 Tier 2 評審。lang 決定語言與指標後綴。"""
    from tutor_driver import TutorDriver, is_spoonfeeding
    problems = _load_problems(lang)
    att = json.loads((HERE / f"held_out_attempts{'_en' if lang == 'en' else ''}.json"
                      ).read_text(encoding="utf-8"))
    L = _LANG_STR[lang]
    sfx = f"_{lang}"
    items, all_replies = [], []

    # 結構檢查用軟化的「整段搬答案」判定取代硬性 leaks_reference（教學原則：小透露不算退步，
    # 恰當與否交給 Claude 評審 reveal_ok）。
    s1_ok = s3_ok = 0
    for pid in DEEP_IDS:
        p = problems[pid]
        stmt = p.get("statement", "")
        d = TutorDriver(tok, model, dict(p), backstop=False)
        r1 = d.start()
        all_replies.append(r1)
        ok1 = bool(_QMARK.search(r1)) and not is_spoonfeeding(r1) \
            and not dumps_full_solution(r1, p["reference_proof"], stmt)
        s1_ok += ok1
        items.append({"id": pid, "scenario": "S1", "reply": r1, "lang": lang})

        d3 = TutorDriver(tok, model, dict(p), backstop=False)
        r3 = d3.start(opener=L["s3"])
        all_replies.append(r3)
        ok3 = d3.state.get("phase") == "refuse_leak" and bool(_QMARK.search(r3)) \
            and not dumps_full_solution(r3, p["reference_proof"], stmt)
        s3_ok += ok3
        items.append({"id": pid, "scenario": "S3", "reply": r3, "lang": lang})

        attempt = att[pid]["attempt"] if pid in att else p.get("attempt")
        if attempt:
            d2 = TutorDriver(tok, model, dict(p), backstop=False)
            r2 = d2.start(opener=f"{L['s2']}{attempt}")
            all_replies.append(r2)
            items.append({"id": pid, "scenario": "S2", "reply": r2, "lang": lang,
                          "attempt": attempt,
                          "planted_error": (att.get(pid) or p).get("planted_error")
                          or p.get("attempt_error", "")})
        print(f"  [{pid}/{lang}] S1 {'✓' if ok1 else '✗'}  S3 {'✓' if ok3 else '✗'}")
    metrics["s1_structural" + sfx] = round(s1_ok / len(DEEP_IDS), 4)
    metrics["s3_refusal" + sfx] = round(s3_ok / len(DEEP_IDS), 4)

    esc_ok = 0
    from tutor_driver import TutorDriver as TD
    for pid in ESC_IDS:
        d = TD(tok, model, dict(problems[pid]), backstop=False)
        d.start()
        d.step(L["stuck1"])
        r = d.step(L["stuck2"])
        all_replies.append(r)
        ok = d.state["turns"][-1].level == 2 and bool(_QMARK.search(r)) \
            and d.state["ladder_idx"] == 1
        esc_ok += ok
        print(f"  [{pid}/{lang}] 升級 {'✓' if ok else '✗'}")
    metrics["escalation" + sfx] = round(esc_ok / len(ESC_IDS), 4)

    d = TD(tok, model, dict(problems["A6"]), backstop=False)
    d.start()
    for msg in L["walk"]:
        d.step(msg)
    entered = bool(d.state.get("walk_active"))
    for _ in range(12):
        if not d.state.get("walk_active"):
            break
        d.step(L["got"])
    finished = not d.state.get("walk_active") and d.state.get("phase") == "writeup_request"
    metrics["walkthrough" + sfx] = round((entered + finished) / 2, 4)
    print(f"  [A6/{lang}] walkthrough 進入 {'✓' if entered else '✗'} 收尾 {'✓' if finished else '✗'}")

    sq = sum(1 for r in all_replies if len(_QMARK.findall(r)) <= 1)
    metrics["single_question" + sfx] = round(sq / len(all_replies), 4)
    return items


# ── Tier 2：Claude 逐題評審 ──────────────────────────────────────────────────────
JUDGE_ITEM_PROMPT = """你是嚴格的數學教學評審。以下是一道證明題、正確參考解，以及蘇格拉底式助教在三種情境下的回覆（回覆可能是中文或英文，兩者同標準審查）。請逐則審查。

【題目】{statement}

【參考解（正確）】{proof}

{blocks}

對每一則回覆判定：
- math_ok：回覆中所有數學陳述是否**全部正確**（一句錯就 false；引導問題本身沒有數學斷言則為 true）
- caught（僅 S2）：助教是否指到了學生嘗試中「真正的錯誤」（見埋錯說明；只點到皮毛或指錯地方算 false）
- reveal_ok：透露拿捏是否恰當。好教學原則：學生真的卡住時透露一點想法/方向是好的；但**不該把整份解法或最終結論直接奉送**，也不該在學生還沒卡住時就過早爆雷。沒有不當透露＝true；奉送答案或過早爆太多＝false。
- score：引導品質 1-5（蘇格拉底原則：適時而不過度的引導、一問一等、指向正確下一步、尊重學生自己的思路）
- issue：一句話說明扣分或錯誤處（沒有就空字串）

只輸出一個 JSON 物件，格式：
{{"S1": {{"math_ok": true, "reveal_ok": true, "score": 4, "issue": ""}}, "S2": {{"math_ok": true, "caught": true, "reveal_ok": true, "score": 4, "issue": ""}}, "S3": {{"math_ok": true, "reveal_ok": true, "score": 4, "issue": ""}}}}
（缺某情境就省略該鍵）不要輸出任何其他文字。"""


def tier1_multiturn(tok, model, metrics: dict, lang: str = "zh") -> list:
    """多輪確定性探針：固定學生台詞跑完整條路徑，檢查結構不變式（不經評審）。

    回傳每場對話的存檔（供人工檢視與日後回放）。指標皆為確定性、零容忍。
    """
    from tutor_driver import TutorDriver, leaks_reference
    problems = _load_problems(lang)
    script = _MULTITURN_SCRIPT[lang]
    sfx = f"_{lang}"
    records = []
    ok_leak = ok_single = ok_phase = ok_ladder = ok_close = ok_rectify = 0
    for pid in MULTITURN_IDS:
        p = problems[pid]
        d = TutorDriver(tok, model, dict(p), backstop=False)
        turns = []
        reply = d.start()
        turns.append({"student": None, "reply": reply, "phase": d.state.get("phase"),
                      "level": d.state["turns"][-1].level, "ladder": d.state["ladder_idx"],
                      "guards": list(d.state["turns"][-1].guards)})
        for msg in script:
            reply = d.step(msg)
            turns.append({"student": msg, "reply": reply, "phase": d.state.get("phase"),
                          "level": d.state["turns"][-1].level, "ladder": d.state["ladder_idx"],
                          "guards": list(d.state["turns"][-1].guards),
                          "done_closed": bool(d.state.get("done_closed"))})

        # ① 全程不得洩漏參考解（等級 <2 的輪次；等級 2 本來就允許點名想法）
        leak = any(t["level"] < 2 and leaks_reference(
            t["reply"], p["reference_proof"], exclude=p.get("statement", "")) for t in turns)
        ok_leak += not leak
        # ② 每輪至多一個問號
        single = all(len(_QMARK.findall(t["reply"])) <= 1 for t in turns)
        ok_single += single
        # ③ 階段轉換：說「我懂了」後要請他交稿，交出長草稿後要進審閱
        phases = [t["phase"] for t in turns]
        phase_ok = "writeup_request" in phases and "review" in phases \
            and phases.index("writeup_request") < phases.index("review")
        ok_phase += phase_ok
        # ④ 提示梯守恆：消耗量不得超過真正發出等級 2 提示的輪數
        lvl2 = sum(1 for t in turns if t["level"] == 2 and t["phase"] is None)
        ladder_ok = d.state["ladder_idx"] <= lvl2
        ok_ladder += ladder_ok
        # ⑤ 收尾：學生道謝那一輪不得再被補上通用追問句
        close_ok = "fallback" not in turns[-1]["guards"]
        ok_close += close_ok
        # ⑥ 糾錯不得被收尾中斷：審閱輪若還在問問題（＝仍有缺漏），學生針對缺漏的
        #    追問就不該落進 closed（助教會被指示「已完成、不要再問」）——稽核 F3。
        #    審閱一次就通過（回覆無問句）時本項不適用，記為通過。
        ri = phases.index("review") if "review" in phases else None
        if ri is not None and ri + 1 < len(turns) and _QMARK.search(turns[ri]["reply"]):
            rectify_ok = turns[ri + 1]["phase"] != "closed"
        else:
            rectify_ok = True
        ok_rectify += rectify_ok

        flags = "".join("✓" if x else "✗" for x in
                        (not leak, single, phase_ok, ladder_ok, close_ok, rectify_ok))
        print(f"  [{pid}/{lang}] 多輪 洩漏/單問句/階段/提示梯/收尾/糾錯不中斷 = {flags}"
              f"（phases={'>'.join(str(x) for x in phases)}）")
        records.append({"id": pid, "lang": lang, "turns": turns})

    n = len(MULTITURN_IDS)
    metrics["mt_no_leak" + sfx] = round(ok_leak / n, 4)
    metrics["mt_single_question" + sfx] = round(ok_single / n, 4)
    metrics["mt_phase_flow" + sfx] = round(ok_phase / n, 4)
    metrics["mt_ladder_conserved" + sfx] = round(ok_ladder / n, 4)
    metrics["mt_clean_close" + sfx] = round(ok_close / n, 4)
    metrics["mt_rectify_uninterrupted" + sfx] = round(ok_rectify / n, 4)
    return records


JUDGE_SAMPLES = int(os.environ.get("JUDGE_SAMPLES", "3"))


def _judge_item_consensus(prompt: str, samples: int = 0) -> dict | None:
    """同一則探針評審多次取共識，降低評審自身的變異。

    為什麼要這樣做（2026-08-02 量測，measure_gate_noise.py）：取 14 輪同後端、
    Tier 1/2 回覆**逐字全同**的守門——生成端毫無變化，judge_* 卻仍擺動
    s2_catch 0.159、score 0.135、reveal_ok 0.115，全部超過各自的 ε。
    ⚠️ 這**不能**靠放寬 ε 解決：14 題中真實多錯 2 題只有 0.143，比雜訊還小，
    任何蓋得住雜訊的容忍度都會同時放行真實退步。唯一的出路是降低變異本身。

    布林欄位取多數決、數值欄位取中位數；解析失敗的樣本直接略過。
    成本：Tier 2 由 38 次評審呼叫增為 114 次，約 +8 分鐘（整輪守門約 2 小時）。
    JUDGE_SAMPLES=1 可還原舊行為（除錯或省額度時用）。
    """
    import statistics
    n = samples or JUDGE_SAMPLES
    votes = [v for v in (parse_json_obj(claude_call(prompt)) for _ in range(n)) if v]
    if not votes:
        return None
    if len(votes) == 1:
        return votes[0]
    merged: dict = {}
    for sname in {k for v in votes for k in v if isinstance(v.get(k), dict)}:
        cells = [v[sname] for v in votes if isinstance(v.get(sname), dict)]
        out: dict = {}
        for field in {k for c in cells for k in c}:
            vals = [c[field] for c in cells if field in c]
            if not vals:
                continue
            if all(isinstance(x, bool) for x in vals):
                out[field] = sum(vals) > len(vals) / 2          # 多數決
            elif all(isinstance(x, (int, float)) for x in vals):
                out[field] = statistics.median(vals)            # 中位數
            else:
                # issue 這類文字：取「與多數決一致」的那一則，避免評語與判定矛盾
                out[field] = next((c.get(field) for c in cells if c.get(field)), vals[0])
        merged[sname] = out
    return merged or votes[0]


def tier2_judge(items: list, metrics: dict, lang: str = "zh") -> None:
    problems = _load_problems(lang)
    sfx = f"_{lang}"
    by_pid: dict = {}
    for it in items:
        by_pid.setdefault(it["id"], {})[it["scenario"]] = it

    math_ok = catch_ok = catch_n = reveal_ok = reveal_n = 0
    scores, judged = [], 0
    for pid, scen in by_pid.items():
        p = problems[pid]
        blocks = []
        for sname in ("S1", "S2", "S3"):
            if sname not in scen:
                continue
            it = scen[sname]
            if sname == "S2":
                blocks.append(f"【S2 學生嘗試（埋錯）】{it['attempt']}\n"
                              f"【S2 埋錯說明】{it['planted_error']}\n"
                              f"【S2 助教回覆】{it['reply']}")
            else:
                ctx = "學生請求第一個提示" if sname == "S1" else "學生逼問直接給完整證明"
                blocks.append(f"【{sname} 情境】{ctx}\n【{sname} 助教回覆】{it['reply']}")
        verdict = _judge_item_consensus(JUDGE_ITEM_PROMPT.format(
            statement=p["statement"], proof=p["reference_proof"], blocks="\n\n".join(blocks)))
        if not verdict:
            print(f"  [{pid}/{lang}] 評審失敗（跳過，不計入）")
            continue
        for sname, v in verdict.items():
            if not isinstance(v, dict):
                continue
            judged += 1
            math_ok += bool(v.get("math_ok"))
            if isinstance(v.get("score"), (int, float)):
                scores.append(float(v["score"]))
            if "reveal_ok" in v:
                reveal_n += 1
                reveal_ok += bool(v.get("reveal_ok"))
            if sname == "S2":
                catch_n += 1
                catch_ok += bool(v.get("caught"))
            if not v.get("math_ok") or (sname == "S2" and not v.get("caught")):
                print(f"  [{pid}/{lang}/{sname}] ✗ {v.get('issue', '')[:80]}")
        print(f"  [{pid}/{lang}] 評審完成")
    if judged:
        metrics["judge_math_ok" + sfx] = round(math_ok / judged, 4)
        metrics["judge_score" + sfx] = round(sum(scores) / len(scores) / 5, 4) if scores else 0.0
    if catch_n:
        metrics["judge_s2_catch" + sfx] = round(catch_ok / catch_n, 4)
    if reveal_n:
        metrics["judge_reveal_ok" + sfx] = round(reveal_ok / reveal_n, 4)


# ── Tier 3：Claude 扮學生的多輪對話 + 整場評審 ───────────────────────────────────
STUDENT_PROMPT = """你在測試一個蘇格拉底式數學助教。你扮演一位真實推理的大學生，人格設定：{persona}

題目：{statement}

以下是到目前為止的對話（「助教」是被測系統、「學生」是你）：
{history}

請產生學生的下一句回覆（1-3 句、口語、符合人格；真的被引導到理解才說懂，不要無腦附和；
若助教的話有數學問題，你可以提出疑問）。{lang_note}只輸出學生要說的話，不要任何其他文字。"""

DIALOGUE_JUDGE_PROMPT = """你是嚴格的數學教學評審。審查以下完整的引導對話。

【題目】{statement}
【參考解（正確）】{proof}
【對話】
{history}

判定（只看「助教」的發言）：
- math_ok：助教所有數學陳述是否全部正確（一句錯就 false）
- guidance：整場引導品質 1-5（不奉送、一問一等、有效把學生推向理解、該提示才提示）
- issue：一句話指出最大問題（沒有就空字串）

只輸出 JSON：{{"math_ok": true, "guidance": 4, "issue": ""}}"""


def tier3_generate(tok, model, lang: str = "zh") -> list:
    """Claude 扮學生跑多輪對話，只生成不評（評分在 tier3_judge，支援 --rejudge）。"""
    from tutor_driver import TutorDriver
    problems = _load_problems(lang)
    lang_note = ("Reply in English (the student speaks English)." if lang == "en"
                 else "用繁體中文回覆。")
    records = []
    for pid, persona in DIALOGUE_CASES:
        p = problems[pid]
        d = TutorDriver(tok, model, dict(p), backstop=False)
        reply = d.start()
        history = [("助教", reply)]
        print(f"  [{pid}/{lang}] 對話開始（{persona[:4]}…）")
        for _ in range(DIALOGUE_TURNS):
            h_txt = "\n".join(f"{who}：{txt}" for who, txt in history)
            stu = claude_call(STUDENT_PROMPT.format(
                persona=persona, statement=p["statement"], history=h_txt,
                lang_note=lang_note), timeout=300)
            if not stu:
                print(f"  [{pid}/{lang}] 學生生成失敗，提前結束")
                break
            history.append(("學生", stu.strip().strip('"')))
            reply = d.step(history[-1][1])
            history.append(("助教", reply))
        # 升級軌跡（供覆蓋度追蹤，不進 pass/fail）：多輪情境下提示梯到底有沒有被用到。
        # 這幾個欄位也讓 --rejudge 讀存檔時不必重跑 GPU 就能算覆蓋度。
        esc = {"ladder_idx": d.state["ladder_idx"],
               "walk_active": bool(d.state.get("walk_active")),
               "max_level": max((t.level for t in d.state["turns"]), default=0)}
        print(f"  [{pid}/{lang}] 升級軌跡 ladder_idx={esc['ladder_idx']} "
              f"max_level={esc['max_level']} walkthrough={esc['walk_active']}")
        records.append({"id": pid, "persona": persona, "history": history,
                        "lang": lang, "verdict": None, "escalation": esc})
    return records


def tier3_judge(records: list, metrics: dict, lang: str = "zh") -> None:
    problems = _load_problems(lang)
    sfx = f"_{lang}"
    math_ok_n, guidance, judged = 0, [], 0
    for rec in records:
        p = problems[rec["id"]]
        h_txt = "\n".join(f"{who}：{txt}" for who, txt in rec["history"])
        verdict = parse_json_obj(claude_call(DIALOGUE_JUDGE_PROMPT.format(
            statement=p["statement"], proof=p["reference_proof"], history=h_txt)))
        rec["verdict"] = verdict
        if verdict:
            judged += 1
            math_ok_n += bool(verdict.get("math_ok"))
            if isinstance(verdict.get("guidance"), (int, float)):
                guidance.append(float(verdict["guidance"]))
            print(f"  [{rec['id']}/{lang}] math_ok={verdict.get('math_ok')} "
                  f"guidance={verdict.get('guidance')} {str(verdict.get('issue', ''))[:60]}")
        else:
            print(f"  [{rec['id']}/{lang}] 評審失敗（跳過，不計入）")
    if judged:
        metrics["judge_dialogue_math_ok" + sfx] = round(math_ok_n / judged, 4)
    if guidance:
        metrics["judge_dialogue_guidance" + sfx] = round(sum(guidance) / len(guidance) / 5, 4)
    # 覆蓋度指標（advisory，不進 pass/fail）：多輪情境下提示梯有沒有真的被用到。
    # 刻意不做成硬門——學生由 LLM 即興扮演＝輸入隨機，連學生生成失敗都會讓它歸零，
    # 正是 CLAUDE.md 弱點 #7 說的「輸入隨機的指標不可棘輪」。它的價值在於把
    # 「有走過升級路徑」的對話寫進存檔，之後由 test_phase_routing.py 的確定性
    # 不變式（Tier 0）永久把關。
    esc = [r.get("escalation") for r in records if r.get("escalation")]
    if esc:
        metrics["dialogue_ladder_used" + sfx] = round(
            sum(1 for e in esc if e["ladder_idx"] >= 1) / len(esc), 4)
        print(f"  [覆蓋/{lang}] 用到提示梯的對話 "
              f"{sum(1 for e in esc if e['ladder_idx'] >= 1)}/{len(esc)}；"
              f"進到逐步教學 {sum(1 for e in esc if e['walk_active'])}")


# ── S4：學生用不同但正確的證法 → 助教是否順著學生邏輯（不硬拉回參考解）─────────────
S4_STUDENT_PROMPT = """你在測試一個數學助教。針對下面題目，請你扮演學生，提出一個「與下面參考解不同、但邏輯正確」的證明方向（只講你的方法思路與你打算怎麼進行，2-4 句），並請助教幫你依你的方向繼續。{lang_note}

【題目】{statement}
【參考解（這是助教手上的版本，但你的方法和它不同）】{proof}

只輸出你（學生）要說的話，不要其他文字。"""

S4_JUDGE_PROMPT = """你是數學教學評審。學生提出了一個與助教參考解不同、但正確的證明方向，看助教如何回應。

【題目】{statement}
【助教的參考解（僅供你對照，非唯一正解）】{proof}
【學生提出的另一種方向】{student}
【助教的回覆】{reply}

判定：
- valid_alt：學生提出的方向是否確實是一條有效（正確可行）的證法（若學生方向本身就錯，此題不計，回 null）
- followed：助教是否**順著學生自己的方向**引導（true）；還是無視/否定學生的正確方向、硬把他拉回參考解的方法（false）
- math_ok：助教回覆的數學陳述是否正確
- issue：一句話說明

只輸出 JSON：{{"valid_alt": true, "followed": true, "math_ok": true, "issue": ""}}"""


def tier_s4_generate(tok, model, lang: str = "zh") -> list:
    """S4 生成：Claude 出替代證法起手、助教回應；只存材料不評分（評分在 tier_s4_judge）。"""
    from tutor_driver import TutorDriver
    problems = _load_problems(lang)
    lang_note = ("Speak English." if lang == "en" else "用繁體中文。")
    records = []
    for pid in S4_CASES:
        p = problems[pid]
        stu = claude_call(S4_STUDENT_PROMPT.format(
            statement=p["statement"], proof=p["reference_proof"], lang_note=lang_note), timeout=300)
        if not stu:
            print(f"  [{pid}/{lang}] S4 學生生成失敗（跳過）")
            continue
        stu = stu.strip().strip('"')
        d = TutorDriver(tok, model, dict(p), backstop=False)
        reply = d.step(stu)          # 直接以學生的方法陳述起手
        records.append({"id": pid, "lang": lang, "student": stu, "reply": reply, "verdict": None})
        print(f"  [{pid}/{lang}] S4 生成完成")
    return records


def tier_s4_judge(records: list, metrics: dict, lang: str = "zh") -> None:
    """S4 評分：可對既存記錄重評（--rejudge 也涵蓋 S4）。"""
    problems = _load_problems(lang)
    sfx = f"_{lang}"
    followed_ok = followed_n = 0
    for r in records:
        if r.get("lang", "zh") != lang:
            continue
        p = problems[r["id"]]
        verdict = parse_json_obj(claude_call(S4_JUDGE_PROMPT.format(
            statement=p["statement"], proof=p["reference_proof"],
            student=r["student"], reply=r["reply"])))
        r["verdict"] = verdict
        if verdict and verdict.get("valid_alt") and verdict.get("followed") is not None:
            followed_n += 1
            followed_ok += bool(verdict.get("followed"))
            print(f"  [{r['id']}/{lang}] S4 followed={verdict.get('followed')} {str(verdict.get('issue',''))[:50]}")
        else:
            print(f"  [{r['id']}/{lang}] S4 評審跳過（valid_alt={verdict and verdict.get('valid_alt')}）")
    if followed_n:
        metrics["judge_altmethod" + sfx] = round(followed_ok / followed_n, 4)


# ── Tier 4：後盾（找碴結果交 Claude 判對錯）─────────────────────────────────────
BACKSTOP_JUDGE_PROMPT = """你是數學評審。學生草稿有已知缺漏，審閱後盾找出了缺漏清單。判定後盾找得對不對。

【題目】{statement}
【已知的真實缺漏】{truth}
【後盾找出的清單】{gaps}

只輸出 JSON：{{"correct": true}}（清單有指到真實缺漏、且沒有錯誤指控）或 {{"correct": false}}"""


def tier4_backstop(metrics: dict) -> None:
    try:
        from review_backstop import available, find_gaps
    except ImportError:
        return
    if not available():
        print("  Ollama 不在線，跳過（不計入比較）")
        return
    problems = _load_problems()
    att = json.loads((HERE / "held_out_attempts.json").read_text(encoding="utf-8"))
    cases = [
        ("X2", "證明：任取 n+1 個整數。由鴿籠原理，必存在兩數 a、b 除以 n 的餘數相同。"
               "設 a=qn+r、b=pn+r，則 a−b=(q−p)n。證畢。",
         "套用鴿籠原理前未陳述「餘數只有 n 種（0 到 n-1）、數卻有 n+1 個」這個前提"),
        ("X4", "證明：設 c1v1+c2v2=0。左乘 A 得 c1λ1v1+c2λ2v2=0。相減得 c2(λ2−λ1)v2=0。"
               "因 λ2≠λ1 故 c2=0；代回得 c1=0。",
         "從 c2(λ2−λ1)v2=0 推 c2=0 缺少 v2≠0（特徵向量非零）這個依據"),
        ("H3", att["H3"]["attempt"], att["H3"]["planted_error"]),
    ]
    ok = n = 0
    for pid, draft, truth in cases:
        gaps = find_gaps(problems[pid]["statement"], problems[pid]["reference_proof"], draft)
        if gaps is None:
            print(f"  [{pid}] 後盾降級（不計入）")
            continue
        verdict = parse_json_obj(claude_call(BACKSTOP_JUDGE_PROMPT.format(
            statement=problems[pid]["statement"], truth=truth,
            gaps=json.dumps(gaps, ensure_ascii=False))))
        n += 1
        hit = bool(verdict and verdict.get("correct"))
        ok += hit
        print(f"  [{pid}] 後盾 {'✓' if hit else '✗'}")
    if n:
        metrics["judge_backstop"] = round(ok / n, 4)


# ── 基準比較 ──────────────────────────────────────────────────────────────────
def compare_with_baseline(metrics: dict, check_missing: bool = True) -> str:
    """回傳 'pass' / 'fail' / 'incomplete'。

    incomplete：基準有、本次卻缺的指標（限額打斷評審會整批缺失）——缺失不是通過，
    也不是退步，是「評審沒做完」，可用 --rejudge 補評後再判。judge_backstop 例外
    （Ollama 不在線時本來就不計入）。"""
    if not BASELINE.exists():
        print("\n（無基準檔——完整跑通過後本次成績將寫入為初始基準）")
        return "pass"
    base = json.loads(BASELINE.read_text(encoding="utf-8"))["metrics"]
    missing = ([k for k in base if k not in metrics and k != "judge_backstop"]
               if check_missing else [])
    ok = True
    print("\n=== 與基準比較（確定性指標零容忍；judge_* 容忍 ε=%.2f）===" % JUDGE_EPSILON)
    for k, v in metrics.items():
        if k not in base:
            print(f"  [新增] {k} = {v}")
            continue
        if any(k.startswith(pre) for pre in ADVISORY_METRICS):
            print(f"  [advisory] {k}: {base[k]} → {v}（雜訊過大，不進 pass/fail）")
            continue
        eps = 0.0
        if k.startswith("judge_"):
            eps = next((e for pre, e in JUDGE_EPSILON_OVERRIDE.items()
                        if k.startswith(pre)), JUDGE_EPSILON)
        good = v >= base[k] - eps
        print(f"  [{'✓' if good else '✗ 退步'}] {k}: {base[k]} → {v}")
        ok = ok and good
    if missing:
        print(f"  [✗ 缺失] 基準有、本次未產出：{missing}（評審被打斷？用 --rejudge 補評）")
        return "incomplete"
    return "pass" if ok else "fail"


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                              capture_output=True, text=True).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _latest(pattern: str) -> Path | None:
    files = sorted(SCORE_DIR.glob(pattern))
    return files[-1] if files else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="只跑 Tier 0")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--rejudge", action="store_true",
                    help="讀最近一次的 *_replies.json / *_dialogues.json / *_s4.json 重新評審（不重跑 GPU 生成）")
    ap.add_argument("--gen-only", action="store_true",
                    help="只生成並存檔（GPU + Claude 扮學生），完全不評審——之後用 --rejudge 補評。"
                         "把耗額度的評審與耗 GPU 的生成拆開，評審失敗可無限便宜重來。")
    args = ap.parse_args()

    metrics: dict = {}
    print("=== Tier 0：單元 + 資料集（無 GPU）===")
    if not tier0():
        print("\n✗ Tier 0 失敗，中止")
        sys.exit(1)
    metrics["tier0"] = 1.0

    LANGS = ("zh", "en")
    items, dialogue_records, s4_records, multiturn_records = [], [], [], []
    if args.rejudge:
        if not claude_available():
            print("\n✗ 找不到 claude CLI")
            sys.exit(1)
        rp, dp = _latest("*_replies.json"), _latest("*_dialogues.json")
        if not rp:
            print("\n✗ 找不到既有的 *_replies.json，先跑一次完整版")
            sys.exit(1)
        saved = json.loads(rp.read_text(encoding="utf-8"))
        items = saved["items"]
        metrics.update(saved["structural_metrics"])   # 結構指標沿用該次生成
        print(f"\n（rejudge 模式：沿用 {rp.name} 的生成結果與結構指標）")
        for lg in LANGS:
            lg_items = [it for it in items if it.get("lang", "zh") == lg]
            if lg_items:
                print(f"\n=== Tier 2（{lg}）：Claude 逐題評審 ===")
                tier2_judge(lg_items, metrics, lg)
        if dp:
            dialogue_records = [
                {**r, "history": [tuple(t) for t in r["history"]]}
                for r in json.loads(dp.read_text(encoding="utf-8"))]
            for lg in LANGS:
                lg_dlg = [r for r in dialogue_records if r.get("lang", "zh") == lg]
                if lg_dlg:
                    print(f"\n=== Tier 3（{lg}）：既有對話重新評審 ===")
                    tier3_judge(lg_dlg, metrics, lg)
        sp = _latest("*_s4.json")
        if sp:
            s4_records = json.loads(sp.read_text(encoding="utf-8"))
            for lg in LANGS:
                if any(r.get("lang", "zh") == lg for r in s4_records):
                    print(f"\n=== S4（{lg}）：既有記錄重新評審 ===")
                    tier_s4_judge(s4_records, metrics, lg)
        print("\n=== Tier 4：審閱後盾（Ollama + Claude 判定）===")
        tier4_backstop(metrics)
    elif not args.quick:
        if not claude_available():
            print("\n✗ 找不到 claude CLI（評審/學生角色必需）。裝設後重跑，或用 --quick。")
            sys.exit(1)
        tok, model = load_model()
        for lg in LANGS:
            print(f"\n=== Tier 1（{lg}）：19 深度題生成 + 結構指標（GPU）===")
            items += tier1(tok, model, metrics, lg)
            print(f"\n=== Tier 1b（{lg}）：多輪確定性探針（結構不變式，不經評審）===")
            multiturn_records += tier1_multiturn(tok, model, metrics, lg)
            if not args.gen_only:
                print(f"\n=== Tier 2（{lg}）：Claude 逐題評審（math_ok / S2 / reveal / 品質）===")
                tier2_judge([it for it in items if it.get("lang") == lg], metrics, lg)
            print(f"\n=== Tier 3（{lg}）：Claude 扮學生多輪對話 ===")
            dlg = tier3_generate(tok, model, lg)
            dialogue_records += dlg
            if not args.gen_only:
                tier3_judge(dlg, metrics, lg)
            print(f"\n=== S4（{lg}）：學生用不同但正確證法（生成）===")
            s4 = tier_s4_generate(tok, model, lg)
            s4_records += s4
            if not args.gen_only:
                tier_s4_judge(s4, metrics, lg)
        if not args.gen_only:
            print("\n=== Tier 4：審閱後盾（Ollama + Claude 判定）===")
            tier4_backstop(metrics)

    record = {"timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
              "commit": _git_sha(), "judge_model": JUDGE_MODEL,
              "judge_backend": JUDGE_BACKEND, "metrics": metrics}
    SCORE_DIR.mkdir(exist_ok=True)
    stem = f"{record['timestamp'].replace(':', '')}_{record['commit']}"
    (SCORE_DIR / f"{stem}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    if items and not args.rejudge:
        structural = {k: v for k, v in metrics.items()
                      if not k.startswith("judge_") and k != "tier0"}
        (SCORE_DIR / f"{stem}_replies.json").write_text(
            json.dumps({"items": items, "structural_metrics": structural},
                       ensure_ascii=False, indent=2), encoding="utf-8")
    if dialogue_records:
        (SCORE_DIR / f"{stem}_dialogues.json").write_text(
            json.dumps(dialogue_records, ensure_ascii=False, indent=2), encoding="utf-8")
    if s4_records:
        (SCORE_DIR / f"{stem}_s4.json").write_text(
            json.dumps(s4_records, ensure_ascii=False, indent=2), encoding="utf-8")
    if multiturn_records:
        # 存檔用途有二：人工檢視多輪行為，以及日後與本輪逐字比對——多輪探針的
        # 學生台詞是寫死的，greedy 下同輸入必同輸出，逐字差異＝生成端真的變了。
        (SCORE_DIR / f"{stem}_multiturn.json").write_text(
            json.dumps(multiturn_records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n計分卡：{SCORE_DIR / (stem + '.json')}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

    if args.gen_only:
        print("\n（gen-only 模式：生成材料已全部存檔，之後用 --rejudge 補評審，不做基準比較）")
        return
    status = compare_with_baseline(metrics, check_missing=not args.quick)
    if status == "pass" and not args.quick and (args.update_baseline or not BASELINE.exists()):
        BASELINE.write_text(json.dumps(record, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print(f"基準已更新：{BASELINE}")
    if status == "incomplete":
        print("\n△ 評審不完整（限額/連線中斷）：生成已存檔，稍後 --rejudge 補評")
        sys.exit(2)
    if status == "fail":
        print("\n✗ 回歸失敗：有指標低於基準")
        sys.exit(1)
    print("\n✓ 回歸通過：全部指標 ≥ 基準")


if __name__ == "__main__":
    main()
