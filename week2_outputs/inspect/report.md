# Pipeline 檢查報告

題目：ivt_general

## Stage 1 — Problem Parser

- **problem_id**: intermediate_value_theorem
- **目標 (text)**: There exists c in [a, b] such that f(c) = N
- **目標 (symbolic)**: `Eq(f(c), N)`
- **假設**: ['f is continuous on [a, b]', 'N is between f(a) and f(b)']
- **變數**: ['c', 'a', 'b', 'N']


## Stage 2 — Contract Builder

**義務 (obligations)**:
- [O1] Show f is continuous on [a, b]

**允許引用**: continuity,  intermediate_value_theorem


## Stage 3 — Graph Planner

**goal_node_id**: C1

**節點**:
- [A1] (assumption) f is continuous on [a, b]
- [A2] (assumption) N is between f(a) and f(b)
- [O1] (lemma) f is continuous on [a, b]
- [C1] (goal) There exists c in [a, b] such that f(c) = N ← GOAL

**推理**:
- I1: A1 + A2 → O1 (rule: continuity)
- I2: O1 → C1 (rule: intermediate_value_theorem)


## Stage 4 — Graph Prover

**[O1]** f is continuous on [a, b]

  1. f is continuous on [a, b]  _(reason: Assumption A1)_
  2. N is between f(a) and f(b) _(reason: Assumption A2)_
  3. By the Intermediate Value Theorem _(reason: Continuity of f on [a, b] and N between f(a) and f(b))_
  4. There exists c in [a, b] such that f(c) = N _(reason: Conclusion of the Intermediate Value Theorem)_

**[C1]** There exists c in [a, b] such that f(c) = N

  1. f is continuous on [a, b]  _(reason: Assumption A1)_
  2. N is between f(a) and f(b) _(reason: Assumption A2)_
  3. By the Intermediate Value Theorem _(reason: Continuity of f on [a, b] and N between f(a) and f(b))_
  4. There exists c in [a, b] such that f(c) = N _(reason: Conclusion of the Intermediate Value Theorem)_


## Stage 5 — Verifiers

**結果**: REJECTED  |  錯誤數: 6

**錯誤列表**:
- [E1] **HIGH** (structural) node=None: problem_json.goal.symbolic uses undeclared variable/function(s): f.
- [E2] **MEDIUM** (structural) node=None: O1 is not listed in any node.covers_obligations.
- [E3] **HIGH** (structural) node=C1: intermediate_value_theorem is not in allowed_references.
- [E4] **LOW** (critic) node=None: ValueError('no complete JSON object found')
- [E5] **LOW** (critic) node=O1: ValueError('no complete JSON object found')
- [E6] **LOW** (critic) node=C1: ValueError('no complete JSON object found')


**Obligation 狀態**:
- ❌ [O1] Show f is continuous on [a, b] → fail


## Stage 6 — Export Trace

**accepted**: False

**trace entries**: 1


## Stage 3 — Graph Planner

**goal_node_id**: G1

**節點**:
- [A1] (assumption) f is continuous on [a, b]
- [A2] (assumption) N is between f(a) and f(b)
- [G1] (goal) There exists c in [a, b] such that f(c) = N ← GOAL

**推理**:
- I1: A1 + A2 → G1 (rule: continuity,  intermediate_value_theorem)


## Stage 4 — Graph Prover

**[G1]** There exists c in [a, b] such that f(c) = N

  1. f is continuous on [a, b] and N is between f(a) and f(b) _(reason: Given assumptions A1 and A2)_
  2. By the Intermediate Value Theorem _(reason: The Intermediate Value Theorem states that if a function f is continuous on a closed interval [a, b] and N is any number between f(a) and f(b), then there exists at least one number c in [a, b] such that f(c) = N)_
  3. There exists c in [a, b] such that f(c) = N _(reason: By the Intermediate Value Theorem)_


## Stage 5 — Verifiers

**結果**: REJECTED  |  錯誤數: 4

**錯誤列表**:
- [E1] **MEDIUM** (structural) node=None: O1 is not listed in any node.covers_obligations.
- [E2] **HIGH** (structural) node=G1:  intermediate_value_theorem is not in allowed_references.
- [E3] **LOW** (critic) node=None: ValueError('no complete JSON object found')
- [E4] **LOW** (critic) node=G1: ValueError('no complete JSON object found')


**Obligation 狀態**:
- ❌ [O1] Show f is continuous on [a, b] → fail


## Stage 6 — Export Trace

**accepted**: False

**trace entries**: 1


## Stage 3 — Graph Planner

**goal_node_id**: G

**節點**:
- [A1] (assumption) f is continuous on [a, b]
- [A2] (assumption) f(a) < N < f(b)
- [G] (goal) There exists c in [a, b] such that f(c) = N ← GOAL

**推理**:
- I1: A1 + A2 → G (rule: continuity, intermediate_value_theorem)


## Stage 4 — Graph Prover

**[G]** There exists c in [a, b] such that f(c) = N

  1. f is continuous on [a, b] and f(a) < N < f(b) _(reason: Given)_
  2. There exists c in [a, b] such that f(c) = N _(reason: Intermediate Value Theorem)_


## Stage 5 — Verifiers

**結果**: ACCEPTED  |  錯誤數: 3

**錯誤列表**:
- [E1] **MEDIUM** (structural) node=None: O1 is not listed in any node.covers_obligations.
- [E2] **LOW** (critic) node=None: ValueError('no complete JSON object found')
- [E3] **LOW** (critic) node=G: ValueError('no JSON object start found')


**Obligation 狀態**:
- ✅ [O1] Show f is continuous on [a, b] → pass


## Stage 6 — Export Trace

**accepted**: True

**trace entries**: 1


