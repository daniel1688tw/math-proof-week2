# Pipeline 檢查報告

題目：ivt_general

## Stage 1 — Problem Parser

- **problem_id**: intermediate_value_theorem
- **目標 (text)**: There exists c in [a, b] such that f(c) = N
- **目標 (symbolic)**: `Eq(f(c), N)`
- **假設**: ['f is continuous on [a, b]', 'N lies between f(a) and f(b)']
- **變數**: ['c', 'a', 'b', 'N', 'f']


## Stage 2 — Contract Builder

**義務 (obligations)**:
- [O1] Prove the stated goal

**允許引用**: 


## Stage 3 — Graph Planner

**goal_node_id**: N

**節點**:
- [A1] (assumption) f is continuous on [a, b]
- [A2] (assumption) N lies between f(a) and f(b)
- [O1] (goal) There exists c in [a, b] such that f(c) = N
- [L1] (lemma) f is continuous on [a, b] implies f is continuous on [a, b] (redundant)
- [L2] (lemma) N lies between f(a) and f(b) implies N lies between f(a) and f(b) (redundant)
- [L3] (lemma) If f is continuous on [a, b] and N lies between f(a) and f(b), then there exists c in [a, b] such that f(c) = N

**推理**:
- I1: A1 + A2 → L3 (rule: R1, R2, R3)
- I2: L1 + L2 → L3 (rule: R1, R2, R3)


