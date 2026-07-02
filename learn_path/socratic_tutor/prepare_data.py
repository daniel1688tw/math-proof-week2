"""prepare_data.py — 下載並轉換蘇格拉底式數學教學資料為 SFT 對話格式。

資料來源（皆為 HF 公開資料集，走 Xet 後端可下載；本機封鎖的是舊 cdn-lfs）：
  1. eth-nlped/mathdial   — 2.3K 真人師生「引導式」輔導對話（多輪）。
  2. openai/gsm8k (socratic) — 7.5K 題「引導性子問題逐步分解」（已改成多輪一問一等）。
  3. problems.CALCULUS_SEEDS — 10 題微積分第一輪引導黃金種子（只進訓練集）。

兩個公開資料集都是小學數學文字題，但教的是「蘇格拉底引導行為」（問引導問題、不直接給
答案、拆解步驟、回應學生迷思），此行為可遷移到微積分；微積分的內容知識靠 Qwen3 基底。

improve.md 修正要點：
  * 問題①：種子題改由 problems.py 統一管理，**只進訓練集**；評估用 HELDOUT_PROBLEMS。
  * 問題⑤：GSM8K-socratic 改成「多輪、一問一等」，不再把整條拆解塞進單一 assistant 訊息。
  * 問題⑥/⑦：種子每題做「帶前綴 / 不帶前綴」兩版、單一文字重複次數由 15 降到 7。

輸出：data/train.jsonl, data/val.jsonl
  每行一筆：{"messages": [{"role": "...", "content": "..."}, ...]}
  role ∈ {system, user(=學生), assistant(=老師)}；訓練時只對 assistant 算 loss。

執行：
  conda run -n lora_project --live-stream python prepare_data.py
"""

from __future__ import annotations

import json
import os
import random
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from common import (
    DATA_DIR,
    STUDENT_NO_ATTEMPT_PREFIX,
    SYSTEM_SOCRATIC_COMPACT,
    TRAIN_JSONL,
    VAL_JSONL,
    build_grounded_system_compact,
)
from problems import CALCULUS_SEEDS  # 單一題目來源（improve.md 問題①：seeds 只進訓練集）

# 全面改用精簡 system prompt（~70 token）。完整版 ~380 token 吃掉 512 的 74%，
# 把對話預算壓到 ~130 token，使 MathDial 多輪被砍光、grounded 範例塞不進 512。
SYSTEM = SYSTEM_SOCRATIC_COMPACT

# 種子的簡短參考解（gen_seed_references.py 產出），給 grounded 訓練範例用
import json as _json
_SEED_REF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_references.json")
SEED_REFERENCES = _json.load(open(_SEED_REF_PATH, encoding="utf-8")) if os.path.exists(_SEED_REF_PATH) else {}

random.seed(42)

# MathDial 每筆對話的過濾上限（避免少數退化的超長重複對話污染訓練）
MAX_CONV_CHARS = 4000
MAX_TURNS = 14
# GSM8K-socratic 取樣數。improve.md 問題⑤：原本把整條拆解塞進「單一 assistant 訊息」，
# 與「問 ONE 個問題、等學生回答」的目標相反。現已改成「多輪、一問一等」格式
# （見 build_gsm8k_socratic），每個子問題是一個獨立 assistant 回合。
GSM8K_SOCRATIC_N = 1200
VAL_RATIO = 0.04
# improve.md 問題⑥/⑦：每條種子的「每一版文字」重複次數。原本單版重複 15 次易記憶；
# 現在改成「帶前綴 / 不帶前綴」兩版各重複 SEED_REPEAT 次（10 題 × 2 版 × 7 = 140 筆），
# 既降低單一文字的重複次數（15→7，減少死背），又讓模型對「純題目」本身也能引導。
SEED_REPEAT = 7


def _download_parquet(repo_id: str, filename: str, revision: str) -> str:
    """用 huggingface_hub 下載單一 parquet（resolve→Xet 後端，本機可通）。"""
    from huggingface_hub import hf_hub_download

    return hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        repo_type="dataset",
        revision=revision,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MathDial：多輪引導對話
# ─────────────────────────────────────────────────────────────────────────────

_MOVE_TAG = re.compile(r"^\s*\([^)]*\)\s*")  # 老師動作標籤，如 (probing) (telling)


def _strip_move_tags(text: str) -> str:
    prev = None
    while prev != text:  # 少數情況連續多個括號標籤
        prev = text
        text = _MOVE_TAG.sub("", text)
    return text.strip()


def _student_name(profile: str) -> str:
    """從 student_profile 取學生名字（例：'Steven is a 7th grade...' → 'Steven'）。"""
    profile = (profile or "").strip()
    if not profile:
        return ""
    first = re.split(r"[\s,.]", profile)[0]
    if first.isalpha() and first[:1].isupper() and first.lower() not in {
        "the", "a", "this", "student", "he", "she", "they"
    }:
        return first
    return ""


def _strip_name(text: str, name: str) -> str:
    """移除老師回合中對學生的稱呼名字，避免模型學會叫一個訓練資料裡的固定名字。"""
    if not name:
        return text
    text = re.sub(rf"\b{re.escape(name)}\b[,]?\s*", "", text)  # "Steven, " / "Steven "
    text = re.sub(r"^[\s,]+", "", text)                         # 清掉開頭殘留標點
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _parse_mathdial_conversation(convo: str, name: str = "") -> list[dict]:
    """把 'Teacher: (probing)..|EOM|Student: ..' 轉成 user/assistant 交替訊息。"""
    turns = [t.strip() for t in convo.split("|EOM|") if t.strip()]
    msgs: list[dict] = []
    for t in turns:
        if t.startswith("Teacher:"):
            content = _strip_name(_strip_move_tags(t[len("Teacher:"):]), name)
            role = "assistant"
        else:
            # 學生回合：開頭可能是 "Student:" 或學生名字 "Steven:"，去掉到第一個冒號
            content = t.split(":", 1)[1].strip() if ":" in t else t.strip()
            role = "user"
        if not content:
            continue
        # 合併連續同角色回合
        if msgs and msgs[-1]["role"] == role:
            msgs[-1]["content"] += "\n" + content
        else:
            msgs.append({"role": role, "content": content})
    return msgs


def build_mathdial() -> list[dict]:
    import pandas as pd

    path = _download_parquet(
        "eth-nlped/mathdial", "default/train/0000.parquet", "refs/convert/parquet"
    )
    df = pd.read_parquet(path)
    print(f"  MathDial 原始筆數: {len(df)}")

    examples: list[dict] = []
    for _, row in df.iterrows():
        convo = str(row.get("conversation") or "")
        if not convo or len(convo) > MAX_CONV_CHARS:
            continue
        name = _student_name(str(row.get("student_profile") or ""))
        dialogue = _parse_mathdial_conversation(convo, name)
        if len(dialogue) > MAX_TURNS:
            continue
        # 至少要有一個老師回合（assistant）才有訓練目標
        if not any(m["role"] == "assistant" for m in dialogue):
            continue

        problem = str(row.get("question") or "").strip()
        wrong = str(row.get("student_incorrect_solution") or "").strip()
        # 用題目 + 學生的（錯誤）嘗試當作學生的開場 user 訊息，讓老師有上下文可引導
        opening = f"I'm working on this problem:\n\n{problem}"
        if wrong:
            opening += f"\n\nHere is my attempt:\n{wrong}\n\nIs this correct?"
        else:
            opening += "\n\nCan you help me get started?"

        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": opening},
        ]
        # 原對話第一回合就是老師，接在 opening 之後恰好交替
        messages.extend(dialogue)
        # 若 opening 後第一個是 user（罕見），合併進 opening
        if messages[2]["role"] == "user":
            messages[1]["content"] += "\n" + messages[2]["content"]
            del messages[2]
        examples.append({"messages": messages})

    print(f"  MathDial 轉換後可用筆數: {len(examples)}")
    return examples


# ─────────────────────────────────────────────────────────────────────────────
# GSM8K-socratic：多輪、一問一等
# ─────────────────────────────────────────────────────────────────────────────

_CALC = re.compile(r"<<[^>]*>>")


def _parse_socratic_steps(ans: str) -> list[tuple[str, str]]:
    """把 GSM8K-socratic 的 answer 解析成 [(引導問句, 該步驟的計算/結論句), ...]。

    原始格式：每行 "子問題? ** 計算結論句<<48/2=24>>"，行間以 \\n 分隔，最後一行為 "#### N"。
    """
    ans = _CALC.sub("", ans)  # 去掉 <<48/2=24>> 計算註記
    steps: list[tuple[str, str]] = []
    for line in ans.split("\n"):
        line = line.strip()
        if not line or line.startswith("####"):
            continue
        if " ** " in line:
            q, _, a = line.partition(" ** ")
            q, a = q.strip(), a.strip()
            if q and a:
                steps.append((q, a))
        elif steps:  # 沒有 ' ** ' 的延續行 → 併入上一步的結論
            steps[-1] = (steps[-1][0], (steps[-1][1] + " " + line).strip())
    return steps


def build_gsm8k_socratic(n: int) -> list[dict]:
    """改成「多輪、一問一等」：每個子問題是獨立 assistant 回合，學生回合提供該步計算。

    improve.md 問題⑤：原本整條拆解塞進單一 assistant 訊息，等於教模型「一口氣寫完」，
    與 system prompt 的「問 ONE 個問題、等學生回答」矛盾。改成多輪後：
      [system, user(題目), assistant(問1), user(學生算1), assistant(問2), ...]
    只有 assistant（問句）算 loss → 模型學「在 Q&A 歷史下問下一個引導問題」。
    為避免洩漏答案，丟掉最後一個學生回合，讓對話以 assistant 的問句收尾。
    """
    import pandas as pd

    path = _download_parquet(
        "openai/gsm8k", "socratic/train/0000.parquet", "refs/convert/parquet"
    )
    df = pd.read_parquet(path)
    print(f"  GSM8K-socratic 原始筆數: {len(df)}")
    if n < len(df):
        df = df.sample(n=n, random_state=42)

    examples: list[dict] = []
    for _, row in df.iterrows():
        problem = str(row.get("question") or "").strip()
        steps = _parse_socratic_steps(str(row.get("answer") or ""))
        if not problem or not steps:
            continue
        user = (
            f"{problem}\n\n"
            "Walk me through this step by step. Ask me ONE short leading question "
            "at a time and wait for my answer before moving on."
        )
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ]
        for q, a in steps:
            messages.append({"role": "assistant", "content": q})
            messages.append({"role": "user", "content": a})
        # 丟掉最後一個學生回合 → 對話以 assistant 的引導問句收尾（不洩漏最終答案）
        if messages[-1]["role"] == "user":
            messages.pop()
        examples.append({"messages": messages})
    print(f"  GSM8K-socratic 轉換後可用筆數: {len(examples)}（多輪、一問一等）")
    return examples


# ─────────────────────────────────────────────────────────────────────────────
# 微積分黃金種子：第一輪蘇格拉底引導範例（來自 problems.CALCULUS_SEEDS）
# ─────────────────────────────────────────────────────────────────────────────
# 問題根源：MathDial 訓練樣本的學生回合都已有一個錯誤嘗試，老師才有具體迷思可引導。
# 但評估時直接送原始題目，模型缺少對應的訓練樣本，退化成「can you walk me through?」。
# 解法：手寫黃金範例，示範「學生剛收到題目 → 老師問一個具體微積分問題」。
# improve.md 問題①：種子題目集中在 problems.py，且**只進訓練集**；評估改用 HELDOUT_PROBLEMS。
# improve.md 問題⑦：每題各做「帶前綴 / 不帶前綴」兩版，降低對 STUDENT_NO_ATTEMPT_PREFIX 依賴。


def build_calculus_seeds(repeat: int = SEED_REPEAT) -> list[dict]:
    """微積分第一輪引導黃金種子，注入訓練集。

    每題各做兩版 user 訊息：
      (1) 題目 + STUDENT_NO_ATTEMPT_PREFIX（模擬「學生剛看到題目、尚未嘗試」）
      (2) 純題目（不帶前綴）
    各重複 repeat 次。assistant 回覆示範正確的第一個引導問句。
    """
    base: list[dict] = []
    for _pid, problem, response in CALCULUS_SEEDS:
        for user_content in (problem + STUDENT_NO_ATTEMPT_PREFIX, problem):
            base.append({
                "messages": [
                    {"role": "system",    "content": SYSTEM},
                    {"role": "user",      "content": user_content},
                    {"role": "assistant", "content": response},
                ]
            })
    seeds = base * repeat
    print(f"  微積分黃金種子（plain）：{len(CALCULUS_SEEDS)} 題 × 2 版 × {repeat} = {len(seeds)} 筆")
    return seeds


def build_grounded_seeds(repeat: int = SEED_REPEAT) -> list[dict]:
    """grounded 種子範例：system 含「精簡參考解」，教模型『讀 <reference> → 問引導問句、不洩漏』。

    修「訓練沒在 grounding 下做」的分佈不一致。需要 seed_references.json（gen_seed_references.py）。
    參考解刻意精簡（≤90 字），確保精簡 system + 參考解 + 對話塞得進 MAX_LEN=512。
    """
    if not SEED_REFERENCES:
        print("  [警告] 找不到 seed_references.json → 跳過 grounded 種子（請先跑 gen_seed_references.py）")
        return []
    base: list[dict] = []
    for pid, problem, response in CALCULUS_SEEDS:
        ref = SEED_REFERENCES.get(pid, "")
        if not ref:
            continue
        sys_g = build_grounded_system_compact(ref)
        for user_content in (problem + STUDENT_NO_ATTEMPT_PREFIX, problem):
            base.append({
                "messages": [
                    {"role": "system",    "content": sys_g},
                    {"role": "user",      "content": user_content},
                    {"role": "assistant", "content": response},
                ]
            })
    seeds = base * repeat
    print(f"  微積分黃金種子（grounded）：{len(base)//2} 題 × 2 版 × {repeat} = {len(seeds)} 筆")
    return seeds


# ─────────────────────────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    print("[1/4] 下載並轉換 MathDial（真人引導對話）…")
    mathdial = build_mathdial()

    print("[2/4] 下載並轉換 GSM8K-socratic（多輪一問一等）…")
    gsm8k = build_gsm8k_socratic(GSM8K_SOCRATIC_N)

    print("[3/4] 建立微積分黃金種子資料（plain + grounded）…")
    seeds = build_calculus_seeds()
    grounded_seeds = build_grounded_seeds()
    all_seeds = seeds + grounded_seeds

    # 先合併 MathDial + GSM8K，shuffle 後再疊加 seeds（確保種子在各 epoch 都能見到）
    data = mathdial + gsm8k
    random.shuffle(data)
    # 種子放在最後，但 val 只從前段（MathDial+GSM8K）切，確保種子不洩漏進驗證集
    n_val = max(1, int(len(data) * VAL_RATIO))
    val, train_main = data[:n_val], data[n_val:]
    train = train_main + all_seeds

    with open(TRAIN_JSONL, "w", encoding="utf-8") as f:
        for ex in train:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    with open(VAL_JSONL, "w", encoding="utf-8") as f:
        for ex in val:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print("[4/4] 完成")
    print(f"  train: {len(train)} 筆 → {TRAIN_JSONL}")
    print(f"    其中種子：plain {len(seeds)} + grounded {len(grounded_seeds)} = {len(all_seeds)} 筆"
          f"（占 {len(all_seeds)/len(train)*100:.1f}%）")
    print(f"  val:   {len(val)} 筆 → {VAL_JSONL}（不含種子）")
    print("\n--- 範例：黃金種子第一筆 ---")
    ex = seeds[0]
    for m in ex["messages"]:
        preview = m["content"].replace("\n", " ")
        print(f"  [{m['role']}] {preview[:160]}")


if __name__ == "__main__":
    main()
