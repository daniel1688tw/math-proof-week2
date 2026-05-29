BENCHMARK_PROBLEMS = [
    {"problem_id": "chain_rule_sin_x2", "raw_problem": "Prove the chain rule and use it to prove that d/dx sin(x^2) = 2*x*cos(x^2).", "kind": "chain_rule", "expr": "sin(x**2)", "expected": "2*x*cos(x**2)", "goal_symbolic": "d/dx sin(x^2) = 2*x*cos(x^2)"},
    {"problem_id": "mean_value_theorem_general", "raw_problem": "Prove the Mean Value Theorem: if f is continuous on [a,b] and differentiable on (a,b), then there exists c in (a,b) such that f'(c) = (f(b)-f(a))/(b-a).", "kind": "mean_value_theorem", "expr": "f", "interval": ["a", "b"], "expected": "exists c in (a,b) such that f'(c) = (f(b)-f(a))/(b-a)", "goal_symbolic": "exists c in (a,b) such that f'(c) = (f(b)-f(a))/(b-a)"},
    {"problem_id": "ivt_general", "raw_problem": "Prove the Intermediate Value Theorem: if f is continuous on [a,b] and N lies between f(a) and f(b), then there exists c in [a,b] such that f(c)=N.", "kind": "intermediate_value_theorem", "expr": "f", "interval": ["a", "b"], "expected": "exists c in [a,b] such that f(c)=N", "goal_symbolic": "exists c in [a,b] such that f(c)=N"},
]

THEOREM_LIBRARY = [
    "assumption_use", "goal_alignment", "algebraic_simplification",
    "derivative_rule", "chain_rule", "product_rule", "quotient_rule", "power_rule",
    "implicit_differentiation",
    "limit_rule", "lhopital_rule", "squeeze_theorem", "epsilon_delta_definition",
    "integration_by_parts", "substitution_rule", "fundamental_theorem_of_calculus",
    "continuity", "differentiability", "uniform_continuity",
    "mean_value_theorem", "rolles_theorem", "intermediate_value_theorem", "IVT",
    "extreme_value_theorem", "taylor_series", "taylor_theorem",
    "convergence", "divergence_test", "comparison_test",
]
