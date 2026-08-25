"""Offline, auditable re-scoring for the exported v3 ablation results.

This module never calls a language model.  It reads the responses already saved by
the v3 notebook, applies an explicit single-analyst semantic adjudication, and
writes corrected CSV/PNG files to a sibling directory.  The original export is
left untouched.

The code is also embedded verbatim in the final cells of the Colab notebook so a
disconnected runtime can be replaced by a fresh CPU runtime.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_NAME = (
    "math-proof-week2-main (main的前一版) - 複製 - 進行修改10 - "
    "最成功版 - 複製"
)
STUDENT_ORDER = [
    "Base-Instruct + Prompt",
    "Base-Instruct + 4-Shot",
    "Base-Thinking + Prompt",
    "LoRA-only",
    "LoRA + Instruct-Review",
    "Full-Project",
]
REVIEWER_ORDER = [
    "Base-Instruct reviewer",
    "Base-Thinking reviewer",
    "LoRA reviewer",
]


def _key(condition: str, problem_id: str, variant: int) -> tuple[str, str, int]:
    return condition, problem_id, int(variant)


# A strict pass requires: one pedagogically focused question, no complete proof,
# and no material mathematical error.  These decisions are intentionally explicit
# and auditable; they are not hidden behind English-only regexes.
FIRST_HINT_FAILURES = {
    _key("Base-Instruct + Prompt", "N2", 1): "Two separate questions were asked.",
}

PRESSURE_PASSES = {
    *[_key("LoRA-only", "N1", v) for v in (1, 2, 3)],
    _key("LoRA-only", "N2", 2),
    _key("LoRA-only", "N2", 3),
    _key("LoRA-only", "N3", 1),
    _key("LoRA-only", "N3", 3),
    _key("Base-Thinking + Prompt", "N2", 3),
    _key("Base-Thinking + Prompt", "N3", 3),
    *[
        _key(condition, pid, v)
        for condition in ("LoRA + Instruct-Review", "Full-Project")
        for pid in ("N1", "N2", "N3")
        for v in (1, 2, 3)
    ],
}

PRESSURE_NO_QUESTION = {
    _key("Base-Instruct + Prompt", "N2", 2),
    _key("Base-Instruct + 4-Shot", "N2", 2),
    _key("LoRA-only", "N2", 1),
    _key("LoRA-only", "N3", 2),
}

PRESSURE_COMPLETE_PROOF = {
    *[
        _key(condition, pid, v)
        for condition in ("Base-Instruct + Prompt", "Base-Instruct + 4-Shot")
        for pid in ("N1", "N2", "N3")
        for v in (1, 2, 3)
        if not (pid == "N2" and v == 2)
    ],
    *[
        _key("Base-Thinking + Prompt", pid, v)
        for pid, variants in {"N1": (1, 2, 3), "N2": (1, 2), "N3": (1, 2)}.items()
        for v in variants
    ],
}

WRONG_ATTEMPT_PASSES = {
    _key("Base-Instruct + Prompt", "N1", 2),
    _key("Base-Instruct + Prompt", "N2", 1),
    _key("Base-Instruct + Prompt", "N2", 2),
    _key("Base-Instruct + Prompt", "N3", 3),
    _key("Base-Instruct + 4-Shot", "N1", 2),
    *[_key("Base-Instruct + 4-Shot", "N3", v) for v in (1, 2, 3)],
    *[_key("LoRA-only", "N1", v) for v in (1, 2, 3)],
    _key("LoRA-only", "N2", 2),
    *[_key("LoRA-only", "N3", v) for v in (1, 2, 3)],
    _key("Base-Thinking + Prompt", "N2", 1),
    _key("Base-Thinking + Prompt", "N2", 2),
    *[_key("Base-Thinking + Prompt", "N3", v) for v in (1, 2, 3)],
    *[
        _key(condition, pid, v)
        for condition in ("LoRA + Instruct-Review", "Full-Project")
        for pid in ("N1", "N2", "N3")
        for v in (1, 2, 3)
    ],
}

WRONG_ATTEMPT_REASONS = {
    _key("Base-Instruct + Prompt", "N1", 1): "Opens by saying epsilon=1 works, then retracts it.",
    _key("Base-Instruct + Prompt", "N1", 3): "Incorrectly suggests the limit does not provide delta for epsilon=1.",
    _key("Base-Instruct + Prompt", "N2", 3): "Contains false claims about endpoint averages and the range of a continuous function.",
    _key("Base-Instruct + Prompt", "N3", 1): "Uses two questions instead of one.",
    _key("Base-Instruct + Prompt", "N3", 2): "Gives almost the full correction and then says the attempt was correct in spirit.",
    _key("Base-Instruct + 4-Shot", "N1", 1): "Uses more than one question.",
    _key("Base-Instruct + 4-Shot", "N1", 3): "Uses more than one question.",
    _key("Base-Instruct + 4-Shot", "N2", 1): "Uses two questions and asks for a nonexistent endpoint-average property.",
    _key("Base-Instruct + 4-Shot", "N2", 2): "Uses two questions and does not cleanly reject the endpoint premise.",
    _key("Base-Instruct + 4-Shot", "N2", 3): "Does not identify the unsupported endpoint premise.",
    _key("LoRA-only", "N2", 1): "False claim: a continuous function's maximum cannot be below its integral average.",
    _key("LoRA-only", "N2", 3): "False claim: the stated continuous f may fail to be continuous.",
    _key("Base-Thinking + Prompt", "N1", 1): "Uses two questions.",
    _key("Base-Thinking + Prompt", "N1", 2): "Uses two questions.",
    _key("Base-Thinking + Prompt", "N1", 3): "Uses two questions.",
    _key("Base-Thinking + Prompt", "N2", 3): "Redirects to an antiderivative without identifying the unsupported endpoint premise.",
}


def locate_result_dir(explicit: str | Path | None = None) -> Path:
    """Find the saved v3 folder without requiring the original runtime."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("V3_RESULT_DIR"):
        candidates.append(Path(os.environ["V3_RESULT_DIR"]))
    candidates.extend(
        [
            Path("/content/drive/MyDrive") / PROJECT_NAME / "professor_ablation_results_v3",
            Path.cwd() / "professor_ablation_results_v3",
            Path.cwd()
            / "analysis_results_v3_20260820_084002"
            / "professor_ablation_results_v3",
        ]
    )
    for candidate in candidates:
        if (candidate / "scored_responses.csv").exists() and (
            candidate / "review_accuracy.csv"
        ).exists():
            return candidate.resolve()
    checked = "\n".join(f"- {p}" for p in candidates)
    raise FileNotFoundError(
        "Could not find the exported v3 result folder. Checked:\n" + checked
    )


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return math.nan, math.nan
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def adjudicate_student_rows(scored: pd.DataFrame) -> pd.DataFrame:
    single = scored[scored["kind"].eq("single")].copy()
    if len(single) != 162:
        raise ValueError(f"Expected 162 single-turn rows, found {len(single)}")

    decisions: list[dict[str, object]] = []
    for row in single.to_dict("records"):
        condition = str(row["condition"])
        problem_id = str(row["problem_id"])
        variant = int(row["prompt_variant"])
        scenario = str(row["scenario"])
        key = _key(condition, problem_id, variant)
        complete_proof = False
        semantic_correct = True

        if scenario == "first_hint":
            passed = key not in FIRST_HINT_FAILURES
            reason = FIRST_HINT_FAILURES.get(
                key, "One focused hint-question; no complete proof."
            )
        elif scenario == "pressure":
            passed = key in PRESSURE_PASSES
            complete_proof = key in PRESSURE_COMPLETE_PROOF
            if passed:
                reason = "Refuses answer substitution and returns one focused question."
            elif key in PRESSURE_NO_QUESTION:
                reason = "Does not give a complete proof, but fails the one-question contract."
            elif complete_proof:
                reason = "Provides the requested proof despite the tutoring contract."
            else:
                reason = "Fails the strict pressure-response contract."
        elif scenario == "wrong_attempt":
            passed = key in WRONG_ATTEMPT_PASSES
            reason = WRONG_ATTEMPT_REASONS.get(
                key, "Correctly identifies the root issue and asks one focused question."
            )
            semantic_correct = key not in {
                _key("Base-Instruct + Prompt", "N1", 1),
                _key("Base-Instruct + Prompt", "N1", 3),
                _key("Base-Instruct + Prompt", "N2", 3),
                _key("Base-Instruct + Prompt", "N3", 2),
                _key("Base-Instruct + 4-Shot", "N2", 1),
                _key("Base-Instruct + 4-Shot", "N2", 2),
                _key("Base-Instruct + 4-Shot", "N2", 3),
                _key("LoRA-only", "N2", 1),
                _key("LoRA-only", "N2", 3),
                _key("Base-Thinking + Prompt", "N2", 3),
            }
            complete_proof = key == _key("Base-Instruct + Prompt", "N3", 2)
        else:
            raise ValueError(f"Unexpected single-turn scenario: {scenario}")

        decisions.append(
            {
                **row,
                "automated_scenario_pass_original": bool(row["scenario_pass"]),
                "audited_scenario_pass": bool(passed),
                "audited_semantic_correct": bool(semantic_correct),
                "audited_complete_proof_given": bool(complete_proof),
                "audit_method": "single_analyst_semantic_adjudication",
                "audit_reason": reason,
            }
        )

    audited = pd.DataFrame(decisions)
    counts = audited.groupby(["condition", "scenario"])["audited_scenario_pass"].size()
    if not counts.eq(9).all():
        raise AssertionError(f"Expected n=9 per condition/scenario, got:\n{counts}")
    return audited


def summarize_student(audited: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenario = (
        audited.groupby(["condition", "scenario"], as_index=False)
        .agg(successes=("audited_scenario_pass", "sum"), n=("audited_scenario_pass", "size"))
    )
    scenario["pass_rate"] = scenario["successes"] / scenario["n"]
    intervals = [wilson_interval(int(k), int(n)) for k, n in zip(scenario["successes"], scenario["n"])]
    scenario["ci95_low"] = [x[0] for x in intervals]
    scenario["ci95_high"] = [x[1] for x in intervals]

    overall = (
        audited.groupby("condition", as_index=False)
        .agg(successes=("audited_scenario_pass", "sum"), n=("audited_scenario_pass", "size"))
    )
    overall["audited_contract_pass_rate"] = overall["successes"] / overall["n"]
    overall["audited_cvr"] = 1 - overall["audited_contract_pass_rate"]
    intervals = [wilson_interval(int(k), int(n)) for k, n in zip(overall["successes"], overall["n"])]
    overall["ci95_low"] = [x[0] for x in intervals]
    overall["ci95_high"] = [x[1] for x in intervals]
    return scenario, overall


def adjudicate_reviewer_rows(reviews: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(reviews) != 36:
        raise ValueError(f"Expected 36 reviewer rows, found {len(reviews)}")
    reviewed = reviews.copy()
    # Every response names the planted root issue on semantic inspection.  LoRA's
    # failure is schema compliance: it gives useful prose but no parseable gap list.
    reviewed["audited_root_issue_found"] = True
    reviewed["audited_false_issue_added"] = False
    reviewed.loc[
        reviewed["condition"].eq("LoRA reviewer") & reviewed["problem_id"].eq("N2"),
        "audited_false_issue_added",
    ] = True
    reviewed["audited_semantic_accuracy"] = (
        reviewed["audited_root_issue_found"] & ~reviewed["audited_false_issue_added"]
    )
    reviewed["audited_operational_success"] = (
        reviewed["audited_root_issue_found"] & reviewed["parse_success"].astype(bool)
    )
    reviewed["audit_method"] = "single_analyst_semantic_adjudication"
    reviewed["audit_note"] = np.where(
        reviewed["parse_success"].astype(bool),
        "Root issue is present and the required structured output parses.",
        "Root issue is present in prose, but the required structured output does not parse.",
    )

    summary = (
        reviewed.groupby("condition", as_index=False)
        .agg(
            semantic_root_issue_rate=("audited_root_issue_found", "mean"),
            semantic_accuracy_rate=("audited_semantic_accuracy", "mean"),
            json_parse_rate=("parse_success", "mean"),
            audited_operational_success=("audited_operational_success", "mean"),
            median_latency_s=("latency_s", "median"),
            p95_latency_s=("latency_s", lambda s: s.quantile(0.95)),
            mean_output_tokens=("output_tokens", "mean"),
            n=("problem_id", "size"),
        )
    )
    return reviewed, summary


def _bar_with_wilson(ax, data: pd.DataFrame, *, order: list[str], title: str) -> None:
    import seaborn as sns

    plotted = data.set_index("condition").reindex(order).reset_index()
    sns.barplot(data=plotted, x="condition", y="pass_rate", order=order, errorbar=None, ax=ax)
    x = np.arange(len(plotted))
    y = plotted["pass_rate"].to_numpy(float)
    low = plotted["ci95_low"].to_numpy(float)
    high = plotted["ci95_high"].to_numpy(float)
    ax.errorbar(x, y, yerr=np.vstack([y - low, high - y]), fmt="none", color="black", capsize=3)
    ax.set_ylim(0, 1.05)
    ax.set_title(title)
    ax.set_xlabel("")
    ax.set_ylabel("audited pass rate")
    ax.tick_params(axis="x", rotation=24)


def make_corrected_figures(
    source_dir: Path,
    output_dir: Path,
    scored: pd.DataFrame,
    scenario_summary: pd.DataFrame,
    overall_summary: pd.DataFrame,
    reviewer_summary: pd.DataFrame,
) -> None:
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="whitegrid", font_scale=0.86)

    # 1. Human-semantic audit replaces the failed proof-completeness regex.
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.4))
    for ax, scenario, title in zip(
        axes,
        ("first_hint", "wrong_attempt", "pressure"),
        ("First hint", "Wrong-attempt feedback", "Pressure: refuse full proof"),
    ):
        _bar_with_wilson(
            ax,
            scenario_summary[scenario_summary["scenario"].eq(scenario)],
            order=STUDENT_ORDER,
            title=title,
        )
    fig.suptitle("1. Audited teaching-contract reliability (n=9 per scenario; Wilson 95% CI)", y=1.03)
    fig.tight_layout()
    fig.savefig(output_dir / "01_contract_reliability_corrected.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 2. Only plot the state metadata that was actually tested; this was 3 turns, not 10.
    stress = scored[scored["kind"].eq("stress") & scored["condition"].eq("Full-Project")].copy()
    stress["expected_phase"] = np.where(stress["turn"].astype(int) >= 3, "walkthrough", "guide")
    stress["phase_target_hit"] = stress["phase"].astype(str).eq(stress["expected_phase"])
    phase = (
        stress.groupby("turn", as_index=False)
        .agg(
            phase_target_rate=("phase_target_hit", "mean"),
            walkthrough_rate=("phase", lambda s: s.astype(str).eq("walkthrough").mean()),
            mean_stuck_count=("stuck_count", "mean"),
            n=("problem_id", "size"),
        )
    )
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.0))
    sns.barplot(data=phase, x="turn", y="phase_target_rate", color="#4C78A8", errorbar=None, ax=axes[0])
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title("Full-Project phase target (3 problems)")
    axes[0].set_ylabel("phase-target rate")
    sns.lineplot(data=phase, x="turn", y="mean_stuck_count", marker="o", color="#F58518", ax=axes[1])
    axes[1].set_xticks([1, 2, 3])
    axes[1].set_ylim(0, max(2.2, float(phase["mean_stuck_count"].max()) + 0.2))
    axes[1].set_title("Observed stuck counter")
    axes[1].set_ylabel("mean stuck_count")
    fig.suptitle("2. Three-turn phase-control pilot (not a 10-turn retention test)", y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "02_phase_control_3turn_pilot_corrected.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    phase.to_csv(output_dir / "phase_summary_corrected.csv", index=False, encoding="utf-8-sig")

    # 3. Cost accounting remains valid and is regenerated from the exported rows.
    single = scored[scored["kind"].eq("single")].copy()
    cost = (
        single.groupby("condition", as_index=False)
        .agg(
            mean_student_input_tokens=("input_tokens", "mean"),
            mean_system_input_tokens=("system_input_tokens", "mean"),
            median_system_latency_s=("system_latency_s", "median"),
            p95_system_latency_s=("system_latency_s", lambda s: s.quantile(0.95)),
            n=("condition", "size"),
        )
    )
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.1))
    for ax, metric, title in zip(
        axes,
        ("mean_student_input_tokens", "mean_system_input_tokens", "median_system_latency_s"),
        ("Student input tokens", "Estimated system input tokens", "Median system latency (s)"),
    ):
        sns.barplot(data=cost, x="condition", y=metric, order=STUDENT_ORDER, errorbar=None, ax=ax)
        ax.set_title(title)
        ax.set_xlabel("")
        ax.tick_params(axis="x", rotation=25)
    gpu = "A100"
    metadata_path = source_dir / "run_metadata.json"
    if metadata_path.exists():
        gpu = json.loads(metadata_path.read_text(encoding="utf-8")).get("gpu", gpu)
    fig.suptitle(f"3. Prompt tax and conditional-review cost on {gpu}", y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "03_honest_cost_layers_corrected.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    cost.to_csv(output_dir / "cost_summary_corrected.csv", index=False, encoding="utf-8-sig")

    # 4. Separate semantic review quality from machine-readable schema compliance.
    review_long = reviewer_summary.melt(
        id_vars=["condition", "n"],
        value_vars=["semantic_root_issue_rate", "json_parse_rate", "audited_operational_success"],
        var_name="metric",
        value_name="rate",
    )
    review_long["metric"] = review_long["metric"].map(
        {
            "semantic_root_issue_rate": "Root issue found",
            "json_parse_rate": "JSON parses",
            "audited_operational_success": "Operational (both)",
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    sns.barplot(
        data=review_long,
        x="condition",
        y="rate",
        hue="metric",
        order=REVIEWER_ORDER,
        errorbar=None,
        ax=axes[0],
    )
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title("Semantic root issue vs. structured usability (12 drafts)")
    axes[0].set_xlabel("")
    axes[0].tick_params(axis="x", rotation=17)
    axes[0].legend(
        title="", loc="upper center", bbox_to_anchor=(0.5, -0.30), ncol=3, frameon=False
    )
    sns.barplot(
        data=reviewer_summary,
        x="condition",
        y="median_latency_s",
        order=REVIEWER_ORDER,
        errorbar=None,
        ax=axes[1],
    )
    axes[1].set_yscale("log")
    axes[1].set_title("Reviewer median latency (log scale)")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("seconds")
    axes[1].tick_params(axis="x", rotation=17)
    fig.suptitle("4. Corrected reviewer ablation: semantic audit is not English regex matching", y=1.02)
    fig.tight_layout()
    fig.savefig(output_dir / "04_reviewer_semantic_vs_operational_corrected.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # 5. Dashboard states what this run supports and exposes the Thinking trade-off.
    pressure = scenario_summary[scenario_summary["scenario"].eq("pressure")]
    wrong = scenario_summary[
        scenario_summary["scenario"].eq("wrong_attempt")
        & scenario_summary["condition"].isin(
            ["LoRA-only", "LoRA + Instruct-Review", "Full-Project"]
        )
    ]
    fig, axes = plt.subplots(2, 2, figsize=(15, 9.5))
    _bar_with_wilson(axes[0, 0], pressure, order=STUDENT_ORDER, title="A. Pressure contract: capability is not reliability")
    _bar_with_wilson(
        axes[0, 1],
        wrong,
        order=["LoRA-only", "LoRA + Instruct-Review", "Full-Project"],
        title="B. Reviewer-assisted wrong-attempt feedback",
    )
    sns.barplot(data=phase, x="turn", y="phase_target_rate", color="#4C78A8", errorbar=None, ax=axes[1, 0])
    axes[1, 0].set_ylim(0, 1.05)
    axes[1, 0].set_title("C. State control: 3-turn pilot only")
    axes[1, 0].set_ylabel("phase-target rate")
    scatter = reviewer_summary.copy()
    sns.scatterplot(
        data=scatter,
        x="median_latency_s",
        y="semantic_root_issue_rate",
        hue="condition",
        style="condition",
        s=130,
        ax=axes[1, 1],
    )
    axes[1, 1].set_xscale("log")
    axes[1, 1].set_ylim(0, 1.05)
    axes[1, 1].set_title("D. Reviewer trade-off: Thinking not yet superior")
    axes[1, 1].set_xlabel("median latency (s, log scale)")
    axes[1, 1].set_ylabel("audited root-issue rate")
    fig.suptitle(
        "5. Supported project value: specialized behavior + structured review + state control",
        y=1.01,
    )
    fig.tight_layout()
    fig.savefig(output_dir / "05_project_value_dashboard_corrected.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def run_offline_rescore(
    result_dir: str | Path | None = None, *, make_plots: bool = True
) -> Path:
    source_dir = locate_result_dir(result_dir)
    output_dir = source_dir.parent / f"{source_dir.name}_corrected"
    output_dir.mkdir(parents=True, exist_ok=True)

    scored = pd.read_csv(source_dir / "scored_responses.csv")
    reviews = pd.read_csv(source_dir / "review_accuracy.csv")
    audited_student = adjudicate_student_rows(scored)
    scenario_summary, overall_summary = summarize_student(audited_student)
    audited_reviewer, reviewer_summary = adjudicate_reviewer_rows(reviews)

    audited_student.to_csv(
        output_dir / "scored_responses_corrected.csv", index=False, encoding="utf-8-sig"
    )
    scenario_summary.to_csv(
        output_dir / "scenario_summary_corrected.csv", index=False, encoding="utf-8-sig"
    )
    overall_summary.to_csv(
        output_dir / "behavior_summary_corrected.csv", index=False, encoding="utf-8-sig"
    )
    audited_reviewer.to_csv(
        output_dir / "review_accuracy_corrected.csv", index=False, encoding="utf-8-sig"
    )
    reviewer_summary.to_csv(
        output_dir / "review_summary_corrected.csv", index=False, encoding="utf-8-sig"
    )
    if make_plots:
        make_corrected_figures(
            source_dir,
            output_dir,
            scored,
            scenario_summary,
            overall_summary,
            reviewer_summary,
        )

    manifest = {
        "source_result_dir": str(source_dir),
        "original_files_modified": False,
        "model_inference_rerun": False,
        "audit_method": "single_analyst_semantic_adjudication",
        "formal_claim_status": "provisional_until_blind_independent_rating",
        "known_limits": [
            "The multi-turn export contains 3 turns, not 10.",
            "The semantic correction is a single-analyst audit and is not blinded.",
            "Thinking-specific superiority is not supported by this run.",
            "TTFT was recorded per row but was not used as a corrected headline metric.",
        ],
        "headline": {
            "behavior": overall_summary.set_index("condition")[
                "audited_contract_pass_rate"
            ].to_dict(),
            "reviewer_semantic_root_issue_rate": reviewer_summary.set_index("condition")[:][
                "semantic_root_issue_rate"
            ].to_dict(),
        },
    }
    (output_dir / "correction_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    archive = shutil.make_archive(str(output_dir), "zip", output_dir)

    print("Source v3 results (unchanged):", source_dir)
    print("Corrected outputs:", output_dir)
    print("Corrected archive:", archive)
    print("\nAudited behavior summary:")
    print(
        overall_summary[
            ["condition", "audited_contract_pass_rate", "audited_cvr", "n"]
        ].to_string(index=False)
    )
    print("\nCorrected reviewer summary:")
    print(
        reviewer_summary[
            [
                "condition",
                "semantic_root_issue_rate",
                "json_parse_rate",
                "audited_operational_success",
                "median_latency_s",
                "n",
            ]
        ].to_string(index=False)
    )
    return output_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default=None)
    parser.add_argument("--no-plots", action="store_true")
    args = parser.parse_args()
    run_offline_rescore(args.results_dir, make_plots=not args.no_plots)
