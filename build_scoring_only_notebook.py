import json
from pathlib import Path
from textwrap import dedent


OUTPUT = Path("教授問題_兩顆模型引導極限_精簡分析_Colab.ipynb")


def md(text):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": dedent(text).strip("\n").splitlines(keepends=True),
    }


def code(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": dedent(text).strip("\n").splitlines(keepends=True),
    }


cells = [
    md(r"""
    # 教授問題：兩顆基礎模型的引導極限（scoring-only）

    **目的**：直接回答「既然 Base-Instruct 與 Base-Thinking 已有引導能力，為什麼還需要 LoRA？」

    這份 notebook：

    - 只讀取 v4 已完成的 `student_results.jsonl`，**不載入任何模型、不需要 GPU/A100、不重新推論**。
    - 主比較只有 `Base-Instruct + Prompt`、`Base-Thinking + Prompt`、`LoRA-only`。
    - `Full-Project` 僅列在附錄，不混入 LoRA 核心價值的結論。
    - 固定真實使用方式：**英文題目＋繁體中文對話**。
    - 修正舊評分器的兩個誤判：語意上已拒絕代寫卻被判失敗；walkthrough 引用上一個問句而被算成兩題。
    - 不使用失敗的 LLM Judge、Win/Tie/Loss 或 Pareto 結果。

    核心自動指標：

    1. 正常引導的「恰好一個新問句」成功率。
    2. 面對完整證明要求的「引導守門」成功率。
    3. 12 輪壓力測試中的逐輪契約維持率。

    數學方向是否正確屬語意判斷，另輸出匿名人工盲評表，不用 regex 假裝判斷數學正確性。
    """),
    code(r"""
    # 1. 掛載 Drive、設定路徑與載入套件
    from pathlib import Path
    import json, math, re, sys, warnings

    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from IPython.display import display, Markdown

    IN_COLAB = "google.colab" in sys.modules
    if IN_COLAB:
        from google.colab import drive
        drive.mount("/content/drive")

    # 你的專案路徑；若資料夾名稱不同，只需改這一行。
    PROJECT_ROOT = Path(r"/content/drive/MyDrive/math-proof-week2-main (main的前一版) - 複製 - 進行修改10 - 最成功版 - 複製")

    # 若你知道結果資料夾，可把完整路徑填入引號；留空時會自動尋找。
    RESULTS_DIR_OVERRIDE = ""

    if not IN_COLAB and not PROJECT_ROOT.exists():
        # 方便本機驗證；Colab 不會走這個 fallback。
        PROJECT_ROOT = Path.cwd()

    def locate_results_dir(project_root, override=""):
        if override:
            candidate = Path(override)
            if (candidate / "student_results.jsonl").exists():
                return candidate
            raise FileNotFoundError(f"指定資料夾沒有 student_results.jsonl：{candidate}")

        direct_candidates = [
            project_root / "professor_ablation_results_v4_bilingual_final",
            project_root / "professor_ablation_results_v4_bilingual_for_analysis",
            project_root / "analysis_v4_bilingual_results_20260821",
            project_root / "professor_ablation_results",
        ]
        found = [p for p in direct_candidates if (p / "student_results.jsonl").exists()]
        if not found and project_root.exists():
            found = [p.parent for p in project_root.glob("*v4*/*student_results.jsonl")]
        if not found:
            raise FileNotFoundError(
                "找不到 student_results.jsonl。請把 RESULTS_DIR_OVERRIDE 改成結果資料夾完整路徑；不需要解壓縮模型。"
            )
        return max(found, key=lambda p: (p / "student_results.jsonl").stat().st_mtime)

    RESULTS_DIR = locate_results_dir(PROJECT_ROOT, RESULTS_DIR_OVERRIDE)
    OUTPUT_DIR = PROJECT_ROOT / "professor_limit_scoring_only"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    PRIMARY_LANGUAGE_MODE = "en_problem_zh_dialogue"
    MAIN_CONDITIONS = [
        "Base-Instruct + Prompt",
        "Base-Thinking + Prompt",
        "LoRA-only",
    ]
    APPENDIX_CONDITION = "Full-Project"
    ALL_TARGET_CONDITIONS = MAIN_CONDITIONS + [APPENDIX_CONDITION]
    CONDITION_LABEL = {
        "Base-Instruct + Prompt": "Base-Instruct",
        "Base-Thinking + Prompt": "Base-Thinking",
        "LoRA-only": "LoRA-only",
        "Full-Project": "Full-Project (appendix)",
    }
    CONDITION_COLOR = {
        "Base-Instruct + Prompt": "#4C78A8",
        "Base-Thinking + Prompt": "#F58518",
        "LoRA-only": "#54A24B",
        "Full-Project": "#9D9D9D",
    }

    print("Results:", RESULTS_DIR)
    print("Outputs:", OUTPUT_DIR)
    print("GPU required: NO")
    """),
    code(r"""
    # 2. 讀取並驗證既有 student results（完全不呼叫模型）
    RESULTS_FILE = RESULTS_DIR / "student_results.jsonl"
    df = pd.read_json(RESULTS_FILE, lines=True)

    required = {
        "condition", "kind", "problem_id", "scenario", "language_mode",
        "statement", "student_text", "response", "topic", "difficulty",
        "input_tokens", "output_tokens", "ttft_s", "latency_s",
        "done_reason", "truncated",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise RuntimeError(f"student_results.jsonl 缺少必要欄位：{missing}")

    available = set(df["condition"].dropna().unique())
    missing_conditions = [c for c in MAIN_CONDITIONS if c not in available]
    if missing_conditions:
        raise RuntimeError(f"缺少主比較條件：{missing_conditions}")

    primary = df[
        df["language_mode"].eq(PRIMARY_LANGUAGE_MODE)
        & df["condition"].isin([c for c in ALL_TARGET_CONDITIONS if c in available])
    ].copy()

    coverage = primary.groupby(["condition", "kind"], as_index=False).size()
    print(f"Loaded {len(df):,} rows; primary-language target rows: {len(primary):,}")
    display(coverage.pivot(index="condition", columns="kind", values="size").fillna(0).astype(int))

    expected_single = 50
    expected_stress = 60
    coverage_check = primary.groupby(["condition", "kind"]).size().unstack(fill_value=0)
    for condition in MAIN_CONDITIONS:
        if int(coverage_check.loc[condition].get("single", 0)) != expected_single:
            raise RuntimeError(f"{condition} 的 single 應為 {expected_single} 筆")
        if int(coverage_check.loc[condition].get("stress", 0)) != expected_stress:
            raise RuntimeError(f"{condition} 的 stress 應為 {expected_stress} 筆")
    print("Coverage check passed：每個主條件都有 50 筆單輪與 60 筆（5 題 × 12 輪）壓力資料。")
    """),
    md(r"""
    ## 3. 修正版規則

    規則刻意保持可稽核：

    - 「一個新問句」：若 response 有 `確認問題：`，只計最後一個確認問題區段，避免引用上一題造成假性雙問句。
    - 「引導守門」：接受明確拒絕、要求學生回到目前步驟、或繼續用一個聚焦問句引導；但完整證明型回答仍判失敗。
    - 壓力輪（第 4、9 輪）不硬性要求再新增問號；拒絕並指回目前問題本身就是合格的守門動作。
    - 自動規則只評**行為契約**，不評數學推理是否正確。數學方向由第 7 節盲評。
    """),
    code(r"""
    # 3. 修正版、可重算的行為評分函式
    QUESTION_MARK_RE = re.compile(r"[？?]+")
    CJK_RE = re.compile(r"[\u3400-\u9fff]")

    REFUSAL_PATTERNS = [
        r"(?:不會|不願|不能|無法|不應|不宜|不打算|拒絕).{0,100}(?:代寫|完整(?:證明|答案)|直接(?:給|提供|寫出).{0,16}(?:證明|答案)|提供答案)",
        r"(?:完整(?:證明|答案)|直接(?:給|提供|寫出).{0,16}(?:證明|答案)).{0,100}(?:自己(?:完成|提出|寫出|思考|作答)|失去|跳過|無益|不利|不會|不能|不是現在)",
        r"而非.{0,30}(?:直接(?:提供|給出|寫出).{0,16}(?:答案|證明)|代寫)",
        r"(?:I (?:will not|won['’]?t|cannot|can['’]?t|refuse to)|not going to).{0,100}(?:full proof|complete proof|answer|write it for you)",
        r"(?:full proof|complete proof|answer).{0,100}(?:yourself|practice|learn|not help|won['’]?t provide|cannot provide)",
    ]
    REDIRECT_PATTERNS = [
        r"請(?:先|繼續)?回答(?:目前|最後|我)?(?:這一步|那個|的)?(?:的)?問題",
        r"請(?:先)?回到",
        r"你(?:能|可以)?先(?:說|想|回答|找|指出)",
        r"自己(?:完成|提出|寫出|找到|推導|思考)",
        r"訓練價值|練習價值|引導你|自行推導|逐步.{0,24}(?:引導|提出問題|推導)",
        r"answer (?:the|my|current|previous) question|go back to|try the next step yourself",
    ]

    def clean_text(value):
        if isinstance(value, list):
            value = "\n".join(str(x) for x in value)
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ""
        return str(value).strip()

    def new_question_count(value):
        # Count new questions; ignore questions quoted before the final 確認問題 section.
        text = clean_text(value)
        if "確認問題" in text:
            text = text.rsplit("確認問題", 1)[1]
        return len(QUESTION_MARK_RE.findall(text))

    def zh_language_ok(value):
        # 數學式可含大量 Latin 字元；只要求回覆確實含中文，而不是用字母比例判定。
        return len(CJK_RE.findall(clean_text(value))) >= 2

    def valid_output(row):
        text = clean_text(row.get("response", ""))
        if not text or clean_text(row.get("error", "")):
            return False
        if bool(row.get("truncated", False)) or clean_text(row.get("done_reason", "")) == "length":
            return False
        return True

    def explicit_refusal(value):
        text = " ".join(clean_text(value).split())
        return any(re.search(pattern, text, flags=re.I) for pattern in REFUSAL_PATTERNS)

    def redirect_to_learning(value):
        text = " ".join(clean_text(value).split())
        return any(re.search(pattern, text, flags=re.I) for pattern in REDIRECT_PATTERNS)

    def proof_like(value):
        # Strict screen for a full-proof-shaped answer; it is not a math-correctness judge.
        text = " ".join(clean_text(value).split())
        units = len(re.sub(r"\s+", "", text))
        transition_count = len(re.findall(
            r"(?:假設|由於|由.+?定理|因此|所以|故|則|取|可知|矛盾|證明|suppose|since|therefore|thus|hence|let)",
            text, flags=re.I,
        ))
        conclusion = bool(re.search(
            r"(?:因此|所以|故|從而).{0,90}(?:成立|得證|為常數|一對一|收斂|為零|最多有|趨近於)|"
            r"(?:therefore|thus|hence).{0,90}(?:proved|holds|constant|one-to-one|converges|zero)",
            text, flags=re.I,
        ))
        proof_heading = bool(re.match(r"^\s*(?:\*\*)?(?:證明|proof)\b", text, flags=re.I))
        return bool((units >= 90 and proof_heading and transition_count >= 2) or
                    (units >= 120 and conclusion and transition_count >= 3))

    def pressure_features(row):
        text = clean_text(row.get("response", ""))
        valid = valid_output(row)
        lang = zh_language_ok(text)
        refusal = explicit_refusal(text)
        redirect = redirect_to_learning(text)
        one_q = new_question_count(text) == 1
        full_proof_shape = proof_like(text)
        resisted = bool(valid and lang and not full_proof_shape and (refusal or redirect or one_q))
        if not valid:
            reason = "invalid_or_truncated"
        elif not lang:
            reason = "not_traditional_chinese"
        elif full_proof_shape:
            reason = "full_proof_shaped"
        elif not (refusal or redirect or one_q):
            reason = "no_refusal_redirect_or_guiding_question"
        else:
            reason = "pass"
        return {
            "explicit_refusal": refusal,
            "learning_redirect": redirect,
            "one_guiding_question": one_q,
            "full_proof_shaped": full_proof_shape,
            "pressure_resistance_pass": resisted,
            "pressure_reason": reason,
        }

    scored = primary.copy()
    scored["response"] = scored["response"].map(clean_text)
    scored["valid_output_corrected"] = scored.apply(valid_output, axis=1)
    scored["zh_language_ok_corrected"] = scored["response"].map(zh_language_ok)
    scored["new_question_count"] = scored["response"].map(new_question_count)
    scored["exactly_one_new_question"] = scored["new_question_count"].eq(1)
    scored["full_proof_shaped"] = scored["response"].map(proof_like)

    pressure_mask = (
        (scored["kind"].eq("single") & scored["scenario"].eq("pressure"))
        | (scored["kind"].eq("stress") & scored["turn"].isin([4, 9]))
    )
    pressure_rows = scored[pressure_mask].copy()
    pressure_feature_df = pd.DataFrame(
        [pressure_features(row) for _, row in pressure_rows.iterrows()],
        index=pressure_rows.index,
    )
    for column in pressure_feature_df.columns:
        pressure_rows[column] = pressure_feature_df[column]

    # 正常引導不含 pressure；共有 first_hint 15、wrong_attempt 15、high_logic 5，共 35 筆/條件。
    normal_rows = scored[
        scored["kind"].eq("single")
        & scored["scenario"].isin(["first_hint", "wrong_attempt", "high_logic"])
    ].copy()
    normal_rows["one_question_contract_pass"] = (
        normal_rows["valid_output_corrected"]
        & normal_rows["zh_language_ok_corrected"]
        & normal_rows["exactly_one_new_question"]
    )

    stress_rows = scored[scored["kind"].eq("stress")].copy()
    pressure_pass_map = pressure_rows["pressure_resistance_pass"].to_dict()
    stress_rows["is_pressure_turn"] = stress_rows["turn"].isin([4, 9])
    stress_rows["turn_contract_pass"] = np.where(
        stress_rows["is_pressure_turn"],
        stress_rows.index.map(lambda idx: bool(pressure_pass_map.get(idx, False))),
        stress_rows["valid_output_corrected"]
        & stress_rows["zh_language_ok_corrected"]
        & stress_rows["exactly_one_new_question"],
    ).astype(bool)

    print("Corrected scorer ready.")
    """),
    code(r"""
    # 4. 核心摘要：三組主比較；Full-Project 只保留附錄列
    def wilson_interval(successes, n, z=1.96):
        if n == 0:
            return (np.nan, np.nan)
        p = successes / n
        denom = 1 + z*z/n
        center = (p + z*z/(2*n)) / denom
        half = z * math.sqrt((p*(1-p) + z*z/(4*n))/n) / denom
        return center - half, center + half

    def summarize_binary(frame, flag, name):
        rows = []
        for condition, part in frame.groupby("condition", sort=False):
            n = len(part)
            successes = int(part[flag].sum())
            lo, hi = wilson_interval(successes, n)
            rows.append({
                "condition": condition,
                "metric": name,
                "successes": successes,
                "n": n,
                "rate": successes / n if n else np.nan,
                "ci95_low": lo,
                "ci95_high": hi,
            })
        return pd.DataFrame(rows)

    one_q_summary = summarize_binary(
        normal_rows, "one_question_contract_pass", "normal_one_question_success"
    )
    pressure_summary = summarize_binary(
        pressure_rows, "pressure_resistance_pass", "pressure_resistance_success"
    )
    stress_by_turn = stress_rows.groupby(["condition", "turn"], as_index=False).agg(
        successes=("turn_contract_pass", "sum"),
        n=("turn_contract_pass", "size"),
        rate=("turn_contract_pass", "mean"),
    )
    stress_overall = summarize_binary(stress_rows, "turn_contract_pass", "stress_12turn_overall")
    turn12_summary = summarize_binary(
        stress_rows[stress_rows["turn"].eq(12)], "turn_contract_pass", "turn12_retention"
    )

    core_summary = pd.concat(
        [one_q_summary, pressure_summary, stress_overall, turn12_summary], ignore_index=True
    )
    core_summary["comparison_role"] = np.where(
        core_summary["condition"].isin(MAIN_CONDITIONS), "main", "appendix"
    )

    show = core_summary.pivot(index="condition", columns="metric", values="rate")
    show = show.reindex([c for c in ALL_TARGET_CONDITIONS if c in show.index])
    show_percent = (show * 100).round(1).astype(str) + "%"
    print("Corrected automatic behavior metrics:")
    display(show_percent)

    print("Pressure failure reasons (auditable):")
    display(pd.crosstab(pressure_rows["condition"], pressure_rows["pressure_reason"]))
    """),
    code(r"""
    # 5. 匯出稽核資料與三張核心圖（不含 LLM Judge）
    def write_csv(frame, filename):
        path = OUTPUT_DIR / filename
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        return path

    write_csv(core_summary, "scoring_only_summary.csv")
    write_csv(stress_by_turn, "stress_retention_by_turn.csv")
    write_csv(
        normal_rows[[
            "condition", "problem_id", "topic", "difficulty", "scenario", "response",
            "new_question_count", "valid_output_corrected", "zh_language_ok_corrected",
            "one_question_contract_pass",
        ]],
        "normal_guidance_audit.csv",
    )
    write_csv(
        pressure_rows[[
            "condition", "kind", "problem_id", "turn", "response", "explicit_refusal",
            "learning_redirect", "one_guiding_question", "full_proof_shaped",
            "pressure_resistance_pass", "pressure_reason",
        ]],
        "pressure_resistance_audit.csv",
    )
    write_csv(
        stress_rows[[
            "condition", "problem_id", "turn", "student_text", "response",
            "new_question_count", "valid_output_corrected", "zh_language_ok_corrected",
            "is_pressure_turn", "turn_contract_pass",
        ]],
        "stress_turn_audit.csv",
    )

    plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False})

    def ordered_metric(summary, metric):
        return summary[
            summary["metric"].eq(metric) & summary["condition"].isin(MAIN_CONDITIONS)
        ].set_index("condition").reindex(MAIN_CONDITIONS).reset_index()

    def metric_bar(summary, metric, title, ylabel, filename):
        part = ordered_metric(summary, metric)
        x = np.arange(len(part))
        values = part["rate"].to_numpy(float)
        lower = values - part["ci95_low"].to_numpy(float)
        upper = part["ci95_high"].to_numpy(float) - values
        fig, ax = plt.subplots(figsize=(7.4, 4.8))
        bars = ax.bar(
            x, values,
            color=[CONDITION_COLOR[c] for c in part["condition"]],
            yerr=np.vstack([lower, upper]), capsize=5,
        )
        ax.set_xticks(x, [CONDITION_LABEL[c] for c in part["condition"]])
        ax.set_ylim(0, 1.08)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.axhline(1.0, color="#BBBBBB", linewidth=1, linestyle="--")
        for bar, value, successes, n in zip(bars, values, part["successes"], part["n"]):
            ax.text(bar.get_x()+bar.get_width()/2, min(value+0.035, 1.02),
                    f"{value:.0%}\n({int(successes)}/{int(n)})", ha="center", va="bottom", fontsize=9)
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / filename, bbox_inches="tight")
        plt.show()

    metric_bar(
        core_summary, "normal_one_question_success",
        "Limit 1 — Exactly one new question under normal guidance",
        "Contract success rate", "01_normal_one_question_success.png",
    )
    metric_bar(
        core_summary, "pressure_resistance_success",
        "Limit 2 — Resists requests for a complete proof",
        "Pressure-resistance rate", "02_pressure_resistance.png",
    )

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    for condition in MAIN_CONDITIONS:
        part = stress_by_turn[stress_by_turn["condition"].eq(condition)].sort_values("turn")
        ax.plot(part["turn"], part["rate"], marker="o", linewidth=2,
                label=CONDITION_LABEL[condition], color=CONDITION_COLOR[condition])
    for turn in [4, 9]:
        ax.axvspan(turn-0.22, turn+0.22, color="#D62728", alpha=0.08)
    ax.set(xlim=(1, 12), ylim=(-0.03, 1.05), xticks=range(1, 13),
           xlabel="Conversation turn", ylabel="Contract retention rate",
           title="Limit 3 — Guidance contract retention across 12 turns")
    ax.legend(frameon=False, loc="lower left")
    ax.text(4, 0.02, "proof request", rotation=90, va="bottom", ha="center", fontsize=8, color="#9C2F2F")
    ax.text(9, 0.02, "proof request", rotation=90, va="bottom", ha="center", fontsize=8, color="#9C2F2F")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "03_guidance_retention_12turn.png", bbox_inches="tight")
    plt.show()

    # 一張可直接放簡報的三欄總圖。
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))
    for ax, metric, title in [
        (axes[0], "normal_one_question_success", "A. One-question contract"),
        (axes[1], "pressure_resistance_success", "B. Full-proof resistance"),
    ]:
        part = ordered_metric(core_summary, metric)
        vals = part["rate"].to_numpy(float)
        bars = ax.bar(range(3), vals, color=[CONDITION_COLOR[c] for c in MAIN_CONDITIONS])
        ax.set_xticks(range(3), ["Instruct", "Thinking", "LoRA"])
        ax.set_ylim(0, 1.05)
        ax.set_title(title)
        for bar, value in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, min(value+0.025, 1.01), f"{value:.0%}", ha="center")
    for condition in MAIN_CONDITIONS:
        part = stress_by_turn[stress_by_turn["condition"].eq(condition)].sort_values("turn")
        axes[2].plot(part["turn"], part["rate"], marker="o", linewidth=2,
                     label=CONDITION_LABEL[condition], color=CONDITION_COLOR[condition])
    axes[2].set(xlim=(1, 12), ylim=(-0.03, 1.05), xticks=[1, 4, 8, 12],
                title="C. 12-turn retention", xlabel="Turn")
    axes[2].legend(frameon=False, fontsize=8)
    for ax in axes:
        ax.set_ylabel("Success rate")
    fig.suptitle("Where do the two base models reach their tutoring limits?", fontsize=14, y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "00_professor_core_limits.png", bbox_inches="tight")
    plt.show()

    print("Core charts and audit CSVs saved to:", OUTPUT_DIR)
    """),
    md(r"""
    ## 6. 人工盲評：數學方向正確性

    自動規則只能判斷「像不像引導」，不能判斷它是否抓到學生推理的核心漏洞。

    下格會產生 60 筆匿名資料：

    - 15 筆 `high_logic`（5 題 × 3 條件）：**核心必評**。
    - 45 筆 `wrong_attempt`（15 題 × 3 條件）：延伸穩健性。

    評分標準：`human_math_direction_ok = 1` 表示回覆抓到主要漏洞，且問題能把學生帶向有效下一步；否則填 `0`。可先只填 `priority=core` 的 15 筆。不要先開 key 檔，以免看到模型條件。
    """),
    code(r"""
    # 6. 產生/更新匿名人工評分表（重跑時保留已填分數）
    manual_source = normal_rows[
        normal_rows["condition"].isin(MAIN_CONDITIONS)
        & normal_rows["scenario"].isin(["wrong_attempt", "high_logic"])
    ].copy()

    if len(manual_source) != 60:
        raise RuntimeError(f"人工盲評應為 60 筆，目前是 {len(manual_source)} 筆")

    rng = np.random.default_rng(20260821)
    manual_source["_random"] = rng.random(len(manual_source))
    manual_source = manual_source.sort_values(
        ["problem_id", "scenario", "_random"], kind="stable"
    ).reset_index(drop=True)
    manual_source["blind_id"] = [f"M{i:03d}" for i in range(1, len(manual_source)+1)]
    manual_source["priority"] = np.where(manual_source["scenario"].eq("high_logic"), "core", "robustness")

    scoring_columns = [
        "blind_id", "priority", "problem_id", "topic", "difficulty", "scenario",
        "statement", "student_text", "gold_issue", "response",
        "new_question_count", "one_question_contract_pass",
    ]
    blind = manual_source[scoring_columns].copy()
    blind["human_math_direction_ok"] = ""
    blind["human_comment"] = ""

    blind_path = OUTPUT_DIR / "manual_math_blind_scoring.csv"
    key_path = OUTPUT_DIR / "manual_math_blind_key_DO_NOT_OPEN.csv"

    # 如果先前已填過，依 blind_id 保留人工欄位。
    if blind_path.exists():
        old = pd.read_csv(blind_path, dtype=str, keep_default_na=False)
        if "blind_id" in old.columns:
            old = old.set_index("blind_id")
            for column in ["human_math_direction_ok", "human_comment"]:
                if column in old.columns:
                    blind[column] = blind["blind_id"].map(old[column]).fillna("")

    blind.to_csv(blind_path, index=False, encoding="utf-8-sig")
    manual_source[["blind_id", "condition", "problem_id", "scenario"]].to_csv(
        key_path, index=False, encoding="utf-8-sig"
    )

    print("先評這份（不要開 key）：", blind_path)
    print("條件對照 key：", key_path)
    print("建議先完成 priority=core 的 15 筆，再回來執行下一格。")
    display(blind[blind["priority"].eq("core")].head(5))
    """),
    code(r"""
    # 7. 填完 CSV 後只需重跑本格：計算人工數學方向正確率
    blind_rated = pd.read_csv(blind_path, dtype=str, keep_default_na=False)
    blind_key = pd.read_csv(key_path, dtype=str, keep_default_na=False)
    blind_rated["human_math_direction_ok_num"] = pd.to_numeric(
        blind_rated["human_math_direction_ok"], errors="coerce"
    )
    invalid_human_values = blind_rated.loc[
        blind_rated["human_math_direction_ok"].ne("")
        & ~blind_rated["human_math_direction_ok"].isin(["0", "1"]),
        ["blind_id", "human_math_direction_ok"],
    ]
    if len(invalid_human_values):
        raise ValueError("human_math_direction_ok 只能填 0、1 或留白：\n" + invalid_human_values.to_string(index=False))

    human = blind_rated.merge(blind_key, on=["blind_id", "problem_id", "scenario"], how="left", validate="one_to_one")
    rated = human[human["human_math_direction_ok_num"].notna()].copy()
    coverage_human = human.groupby(["priority", "condition"], as_index=False).agg(
        rated=("human_math_direction_ok_num", "count"),
        expected=("blind_id", "size"),
    )
    display(coverage_human)

    if rated.empty:
        print("尚未填人工分數；自動行為圖仍然有效，但不要宣稱數學方向正確率。")
    else:
        human_summary = rated.groupby(["priority", "condition"], as_index=False).agg(
            successes=("human_math_direction_ok_num", "sum"),
            n=("human_math_direction_ok_num", "size"),
            math_direction_accuracy=("human_math_direction_ok_num", "mean"),
        )
        write_csv(human_summary, "manual_math_direction_summary.csv")
        human_show = human_summary.copy()
        human_show["math_direction_accuracy"] = (
            human_show["math_direction_accuracy"] * 100
        ).round(1).astype(str) + "%"
        display(human_show)

        core_expected = 5
        core_counts = human_summary[human_summary["priority"].eq("core")].set_index("condition")["n"]
        if all(int(core_counts.get(c, 0)) == core_expected for c in MAIN_CONDITIONS):
            core_human = human_summary[human_summary["priority"].eq("core")].set_index("condition").reindex(MAIN_CONDITIONS)
            fig, ax = plt.subplots(figsize=(7.4, 4.8))
            vals = core_human["math_direction_accuracy"].to_numpy(float)
            bars = ax.bar(range(3), vals, color=[CONDITION_COLOR[c] for c in MAIN_CONDITIONS])
            ax.set_xticks(range(3), [CONDITION_LABEL[c] for c in MAIN_CONDITIONS])
            ax.set_ylim(0, 1.08)
            ax.set_ylabel("Human-rated math-direction accuracy")
            ax.set_title("High-logic cases — blind human scoring (n=5 per condition)")
            for bar, value in zip(bars, vals):
                ax.text(bar.get_x()+bar.get_width()/2, min(value+0.035, 1.02), f"{value:.0%}", ha="center")
            fig.tight_layout()
            fig.savefig(OUTPUT_DIR / "04_high_logic_human_accuracy.png", bbox_inches="tight")
            plt.show()
        else:
            print("core 尚未每條件評滿 5 筆，因此暫不畫高難度正確率圖。")
    """),
    code(r"""
    # 8. Token / 延遲附錄：只描述代價，不把「LoRA 一定更快」當成預設結論
    single_primary = scored[scored["kind"].eq("single")].copy()
    efficiency_rows = []
    for condition, part in single_primary.groupby("condition", sort=False):
        efficiency_rows.append({
            "condition": condition,
            "n": len(part),
            "input_tokens_mean": part["input_tokens"].mean(),
            "output_tokens_mean": part["output_tokens"].mean(),
            "ttft_p50_s": part["ttft_s"].median(),
            "ttft_p95_s": part["ttft_s"].quantile(.95),
            "latency_p50_s": part["latency_s"].median(),
            "latency_p95_s": part["latency_s"].quantile(.95),
        })
    efficiency = pd.DataFrame(efficiency_rows)
    efficiency["comparison_role"] = np.where(
        efficiency["condition"].isin(MAIN_CONDITIONS), "main", "appendix"
    )
    write_csv(efficiency, "efficiency_appendix.csv")
    display(efficiency.round(3))

    if APPENDIX_CONDITION in set(stress_rows["condition"]):
        project_state = stress_rows[stress_rows["condition"].eq(APPENDIX_CONDITION)].groupby(
            ["turn", "phase", "turn_action"], dropna=False, as_index=False
        ).size()
        write_csv(project_state, "full_project_state_control_appendix.csv")
        print("Full-Project state-control evidence was saved only as an appendix.")
    """),
    code(r"""
    # 9. 產生可直接向教授說明的結論草稿（只引用本 notebook 的有效指標）
    metric_lookup = core_summary.set_index(["condition", "metric"])["rate"].to_dict()

    def pct(condition, metric):
        value = metric_lookup.get((condition, metric), np.nan)
        return "N/A" if pd.isna(value) else f"{value:.0%}"

    lines = [
        "# 給教授的結論草稿",
        "",
        "兩顆基礎模型確實具有引導能力，但本實驗要測的不是『能不能偶爾引導』，而是『能否穩定遵守固定教學契約』。",
        "",
        "| 條件 | 正常情境：恰好一個新問句 | 完整證明壓力：守住引導 | 12 輪整體契約維持 |",
        "|---|---:|---:|---:|",
    ]
    for condition in MAIN_CONDITIONS:
        lines.append(
            f"| {CONDITION_LABEL[condition]} | "
            f"{pct(condition, 'normal_one_question_success')} | "
            f"{pct(condition, 'pressure_resistance_success')} | "
            f"{pct(condition, 'stress_12turn_overall')} |"
        )
    lines += [
        "",
        "因此，LoRA 的核心價值應定位為：把『一次只問一題、拒絕代寫、以繁體中文維持蘇格拉底式引導』內化成較穩定的預設行為，而不是宣稱 LoRA 讓基礎模型突然獲得數學能力。",
        "",
        "數學方向正確性必須搭配匿名人工評分；人工表尚未填滿前，只能主張行為穩定性，不能主張數學推理更正確。Full-Project 的 phase/state control 是額外系統價值，與 LoRA 核心論點分開呈現。",
        "",
        "附錄可報告 token、TTFT 與 latency，但只陳述測得數字，不預設微調一定更快。",
    ]
    conclusion = "\n".join(lines)
    (OUTPUT_DIR / "professor_conclusion_draft.md").write_text(conclusion, encoding="utf-8")
    display(Markdown(conclusion))

    expected_outputs = [
        "00_professor_core_limits.png",
        "01_normal_one_question_success.png",
        "02_pressure_resistance.png",
        "03_guidance_retention_12turn.png",
        "scoring_only_summary.csv",
        "manual_math_blind_scoring.csv",
        "manual_math_blind_key_DO_NOT_OPEN.csv",
        "efficiency_appendix.csv",
        "professor_conclusion_draft.md",
    ]
    missing_outputs = [name for name in expected_outputs if not (OUTPUT_DIR / name).exists()]
    if missing_outputs:
        raise RuntimeError(f"缺少輸出：{missing_outputs}")
    print("Scoring-only analysis completed. No model inference was run.")
    print("請下載或分享整個資料夾：", OUTPUT_DIR)
    """),
]


notebook = {
    "cells": cells,
    "metadata": {
        "colab": {
            "name": OUTPUT.name,
            "provenance": [],
        },
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.x",
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(OUTPUT.resolve())
