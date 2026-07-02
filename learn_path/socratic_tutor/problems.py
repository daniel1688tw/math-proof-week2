"""problems.py — 微積分證明題目的「單一真實來源」。

improve.md 問題①：原本 prepare_data.py 的 10 條黃金種子，與 compare.py 的 10 題測試題
逐字相同（且種子被重複訓練），導致「拿訓練資料考微調模型」、對比結果嚴重高估。

修正：把題目集中在此模組，明確分成兩組，且**互不重疊**：

  * CALCULUS_SEEDS  — 10 題「第一輪引導黃金範例」(id, problem, ideal_first_response)。
                      僅供 prepare_data.py 注入「訓練集」。評估時最多只當「記憶 sanity
                      check」（看模型有沒有把種子背起來），不可當作泛化證據。

  * HELDOUT_PROBLEMS — 12 題「未出現在訓練集中的」微積分題 (id, topic, difficulty,
                       problem)。這是評估**泛化能力**的主要測試集。題目刻意涵蓋與種子
                       相同的技巧家族（數列收斂 / 連續性 / 中值定理 / 介值定理 / 積分 /
                       ε-δ / 級數 / 不動點），但每一題的敘述都不同，確保「考的是會不會
                       教，而不是有沒有背過」。

任何評估腳本請 import HELDOUT_PROBLEMS 當主測試集；種子分數務必與 held-out 分數分開報告。
"""

from __future__ import annotations

import json
import os

# ─────────────────────────────────────────────────────────────────────────────
# 訓練用：10 題第一輪引導黃金種子 (id, problem, ideal_first_response)
# ─────────────────────────────────────────────────────────────────────────────
CALCULUS_SEEDS: list[tuple[str, str, str]] = [
    (
        "seed_cauchy_summable_differences",
        "Let (a_n) be a sequence of real numbers such that |a_{n+1} - a_n| <= 1/2^n "
        "for every n >= 1. Prove that the sequence (a_n) converges.",
        "A standard strategy is to show (a_n) is a Cauchy sequence. "
        "For m > n, can you bound |a_m - a_n| by summing the telescoping differences "
        "|a_{k+1} - a_k| from k = n to m-1, and then estimate that sum using "
        "the geometric series formula?",
    ),
    (
        "seed_iterated_map_to_zero",
        "Let f: [0,1] -> [0,1] be continuous, with f(0) = 0 and f(x) < x for all "
        "x in (0,1]. Define a sequence by x_0 in [0,1] and x_{n+1} = f(x_n) for "
        "n >= 0. Prove that x_n -> 0 as n -> infinity, for any choice of x_0 in [0,1].",
        "Since f(x) < x for x in (0,1], the sequence (x_n) is strictly decreasing "
        "(when x_0 > 0) and bounded below by 0, so it converges to some limit L. "
        "What equation must L satisfy, and why does that force L = 0?",
    ),
    (
        "seed_periodic_two_critical_points",
        "Suppose f: R -> R is differentiable everywhere, periodic with period 1 "
        "(that is, f(x+1) = f(x) for all real x), and f is not a constant function. "
        "Prove that f' has at least two distinct zeros in the interval [0,1).",
        "Periodicity gives f(0) = f(1). What does the Mean Value Theorem applied "
        "to f on [0, 1] guarantee about f' on (0, 1)?",
    ),
    (
        "seed_nonneg_zero_integral",
        "Let f: [0,1] -> R be continuous, with f(x) >= 0 for all x in [0,1]. "
        "Suppose that the integral from 0 to 1 of f(x) dx equals 0. "
        "Prove that f(x) = 0 for all x in [0,1].",
        "Suppose for contradiction that f(c) > 0 for some c in [0,1]. "
        "Since f is continuous at c, what does the ε-δ definition guarantee "
        "about the values of f on a small open interval around c, "
        "and how does that contradict the integral being zero?",
    ),
    (
        "seed_cauchy_functional_equation",
        "Let f: R -> R be a continuous function such that f(x+y) = f(x) + f(y) "
        "for all real numbers x and y. Prove that there exists a constant c "
        "such that f(x) = c*x for all x in R.",
        "Let's build up from the simplest case. Setting x = y = 0 in the "
        "functional equation f(x+y) = f(x) + f(y), what does f(0) equal?",
    ),
    (
        "seed_recursive_sequence_limit",
        "Define a sequence (a_n) by a_1 = 1 and a_{n+1} = 1/(2 + a_n) for n >= 1. "
        "Prove that the sequence (a_n) converges, and find its limit.",
        "To apply the Monotone Convergence Theorem we need the sequence to be "
        "bounded and monotone. Can you first show by induction that 0 < a_n <= 1 "
        "for all n >= 1?",
    ),
    (
        "seed_uniform_limit_continuous",
        "Let (f_n) be a sequence of continuous functions on [a,b], and suppose "
        "f_n converges uniformly to f on [a,b]. Prove that f is continuous on [a,b].",
        "Fix x_0 in [a,b] and ε > 0. Uniform convergence lets you choose N so "
        "that |f_N(x) - f(x)| < ε/3 for every x in [a,b]. "
        "How does the continuity of f_N at x_0 let you complete an ε/3 argument "
        "to show |f(x) - f(x_0)| < ε?",
    ),
    (
        "seed_derivative_limit_average",
        "Let f: [0, infinity) -> R be differentiable, and suppose that "
        "lim_{x -> infinity} f'(x) = L for some finite real number L. "
        "Prove that lim_{x -> infinity} f(x)/x = L.",
        "Since lim f'(x) = L, for any ε > 0 there is M such that "
        "|f'(t) - L| < ε for all t > M. If you apply the Mean Value Theorem "
        "to f on the interval [M, x] — rather than [0, x] — what expression "
        "do you get for f(x) - f(M), and why does this choice of M matter?",
    ),
    (
        "seed_contraction_unique_fixed_point",
        "Let f: R -> R be a function such that there exists a constant k with "
        "0 < k < 1 satisfying |f(x) - f(y)| <= k|x - y| for all real numbers "
        "x and y. Prove that f has exactly one fixed point, i.e., there exists "
        "a unique real number p such that f(p) = p.",
        "Let's first prove uniqueness, since it only takes one line. "
        "Suppose f(p) = p and f(q) = q with p ≠ q. "
        "What does the contraction condition |f(p) - f(q)| <= k|p - q| "
        "say about |p - q|, and why is that a contradiction?",
    ),
    (
        "seed_gronwall_zero_function",
        "Let f: [0,1] -> R be continuous on [0,1] and differentiable on (0,1), "
        "with f(0) = 0. Suppose that |f'(x)| <= |f(x)| for all x in (0,1). "
        "Prove that f(x) = 0 for all x in [0,1].",
        "Consider the auxiliary function g(x) = e^{-x} f(x). "
        "Compute g'(x) using the product rule, then use |f'(x)| <= |f(x)| "
        "to bound |g'(x)|. What does that bound tell you about how g can change?",
    ),
]

# 方便其他模組只取題目敘述（記憶 sanity check 用）
SEED_PROBLEMS: list[tuple[str, str]] = [(pid, prob) for pid, prob, _ in CALCULUS_SEEDS]


# ─────────────────────────────────────────────────────────────────────────────
# 評估用：12 題 held-out 題（不在訓練集中）(id, topic, difficulty, problem)
# ─────────────────────────────────────────────────────────────────────────────
HELDOUT_PROBLEMS: list[dict] = [
    {
        "id": "held_epsilon_delta_square",
        "topic": "ε-δ 連續性",
        "difficulty": "easy",
        "problem": "Using the ε-δ definition of a limit, prove that "
                   "lim_{x -> 2} x^2 = 4.",
    },
    {
        "id": "held_squeeze_sin_over_n",
        "topic": "數列極限 / 夾擠",
        "difficulty": "easy",
        "problem": "Prove that the sequence a_n = sin(n)/n converges, and find its limit.",
    },
    {
        "id": "held_nested_radical_sequence",
        "topic": "單調有界 / 遞迴數列",
        "difficulty": "medium",
        "problem": "Define a sequence by a_1 = sqrt(2) and a_{n+1} = sqrt(2 + a_n) "
                   "for n >= 1. Prove that (a_n) converges, and find its limit.",
    },
    {
        "id": "held_ivt_cubic_root",
        "topic": "介值定理 (IVT)",
        "difficulty": "easy",
        "problem": "Prove that the equation x^3 - x - 1 = 0 has at least one real "
                   "root in the open interval (1, 2).",
    },
    {
        "id": "held_rolle_zero_derivative",
        "topic": "Rolle 定理 / 中值定理",
        "difficulty": "easy",
        "problem": "Let f be continuous on [0, 2] and differentiable on (0, 2), "
                   "with f(0) = f(2) = 0. Prove that there exists c in (0, 2) "
                   "such that f'(c) = 0.",
    },
    {
        "id": "held_heine_cantor_uniform",
        "topic": "均勻連續 / 緊緻性",
        "difficulty": "hard",
        "problem": "Prove that every continuous function f: [0, 1] -> R is "
                   "uniformly continuous on [0, 1].",
    },
    {
        "id": "held_basel_p_series_converges",
        "topic": "級數收斂 / 比較審斂法",
        "difficulty": "medium",
        "problem": "Prove that the series sum_{n=1}^{infinity} 1/n^2 converges. "
                   "(You may use that the partial sums are increasing and bounded.)",
    },
    {
        "id": "held_diff_implies_continuous",
        "topic": "可微 ⇒ 連續",
        "difficulty": "easy",
        "problem": "Prove that if a function f: R -> R is differentiable at a point "
                   "a, then f is continuous at a.",
    },
    {
        "id": "held_mvt_lipschitz_bound",
        "topic": "中值定理 / Lipschitz",
        "difficulty": "medium",
        "problem": "Let f: R -> R be differentiable with |f'(x)| <= 1 for all real x. "
                   "Prove that |f(x) - f(y)| <= |x - y| for all real x and y.",
    },
    {
        "id": "held_integral_mvt",
        "topic": "積分中值定理",
        "difficulty": "medium",
        "problem": "Let f: [a, b] -> R be continuous. Prove that there exists a point "
                   "c in [a, b] such that the integral from a to b of f(x) dx "
                   "equals f(c) * (b - a).",
    },
    {
        "id": "held_nth_root_n_limit",
        "topic": "數列極限",
        "difficulty": "hard",
        "problem": "Prove that lim_{n -> infinity} n^(1/n) = 1.",
    },
    {
        "id": "held_convergent_implies_cauchy",
        "topic": "Cauchy 數列",
        "difficulty": "easy",
        "problem": "Prove that every convergent sequence of real numbers is a "
                   "Cauchy sequence.",
    },
]


def load_external_set(filename: str) -> list[dict]:
    """讀外部題目 JSON（schema：problem_id / topic / difficulty / raw_problem）。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    data = json.load(open(path, encoding="utf-8"))
    return [{"id": p["problem_id"], "problem": p["raw_problem"], "split": "v4",
             "topic": p.get("topic", ""), "difficulty": p.get("difficulty", "")}
            for p in data]


def all_eval_problems() -> list[dict]:
    """回傳評估用的全部題目。

    預設：held-out（split=held，泛化主指標）+ seed（split=seed，記憶 sanity）。
    若設環境變數 EVAL_SET=v4：改用 test_problems_v4.json（10 題較難應用型，split=v4）。
    """
    eval_set = os.environ.get("EVAL_SET", "").strip().lower()
    if eval_set == "v4":
        return load_external_set("test_problems_v4.json")

    out: list[dict] = []
    for p in HELDOUT_PROBLEMS:
        out.append({"id": p["id"], "problem": p["problem"], "split": "held",
                    "topic": p.get("topic", ""), "difficulty": p.get("difficulty", "")})
    for pid, prob in SEED_PROBLEMS:
        out.append({"id": pid, "problem": prob, "split": "seed",
                    "topic": "", "difficulty": ""})
    return out
