# Pipeline 檢查報告

題目：chain_rule_sin_x2

## Stage 1 — Problem Parser

- **problem_id**: chain_rule_and_sin_x2
- **目標 (text)**: d/dx sin(x^2) = 2*x*cos(x^2)
- **目標 (symbolic)**: `Eq(Derivative(sin(x**2),x),2*x*cos(x**2))`
- **假設**: ['f is differentiable at x', 'g is differentiable at x']
- **變數**: ['x', 'f', 'g']


## Stage 2 — Contract Builder

**義務 (obligations)**:
- [O1] Prove the stated goal

**允許引用**: 


## Stage 3 — Graph Planner

**goal_node_id**: G1

**節點**:
- [A1] (assumption) f is differentiable at x
- [A2] (assumption) g is differentiable at x
- [G1] (goal) d/dx sin(x^2) = 2*x*cos(x^2) ← GOAL
- [L1] (lemma) d/dx sin(u) = cos(u) * du/dx
- [S1] (side_condition) u = x^2

**推理**:
- I1: A1 + S1 → L1 (rule: R1)
- I2: L1 + A2 → G1 (rule: R2)


## Stage 4 — Graph Prover

**[G1]** d/dx sin(x^2) = 2*x*cos(x^2)

  1. d/dx sin(u) = cos(u) * du/dx _(reason: Lemma L1)_
  2. Let u = x^2 _(reason: Substitution)_
  3. d/dx x^2 = 2x _(reason: Power rule)_
  4. d/dx sin(x^2) = cos(x^2) * d/dx x^2 _(reason:  Chain rule)_
  5. d/dx sin(x^2) = cos(x^2) * 2x _(reason: Substitution)_
  6. d/dx sin(x^2) = 2x * cos(x^2) _(reason: Commutativity of multiplication)_
  7. d/dx sin(x^2) = 2x * cos(x^2) _(reason: Conclusion)_

**[L1]** d/dx sin(u) = cos(u) * du/dx

  1. d/dx sin(u) = cos(u) * du/dx _(reason: Chain Rule)_
  2. d/dx sin(x^2) = cos(x^2) * d/dx(x^2) _(reason: Substitution of u = x^2 into the chain rule)_
  3. d/dx(x^2) = 2x _(reason: Power Rule)_
  4. d/dx sin(x^2) = cos(x^2) * 2x _(reason: Multiplication of derivatives)_
  5. d/dx sin(x^2) = 2x * cos(x^2) _(reason: Commutativity of multiplication)_

**[S1]** u = x^2

  (無 steps)


## Stage 5 — Verifiers

**結果**: REJECTED  |  錯誤數: 8

**錯誤列表**:
- [E1] **MEDIUM** (structural) node=None: O1 is not listed in any node.covers_obligations.
- [E2] **HIGH** (structural) node=L1: R1 is not in allowed_references.
- [E3] **HIGH** (structural) node=G1: R2 is not in allowed_references.
- [E4] **HIGH** (structural) node=G1: Goal node does not align with Eq(Derivative(sin(x**2),x),2*x*cos(x**2)).
- [E5] **LOW** (critic) node=None: ValueError('no complete JSON object found')
- [E6] **MEDIUM** (critic) node=None: domain constraint for x: all real numbers is not clearly addressed.
- [E7] **LOW** (critic) node=L1: ValueError('no complete JSON object found')
- [E8] **LOW** (critic) node=G1: ValueError('no complete JSON object found')


**Obligation 狀態**:
- ❌ [O1] Prove the stated goal → fail


## Stage 6 — Export Trace

**accepted**: False

**trace entries**: 1


## Stage 5 — Verifiers

**結果**: ACCEPTED  |  錯誤數: 2

**錯誤列表**:
- [E1] **MEDIUM** (structural) node=None: O1 is not listed in any node.covers_obligations.
- [E2] **MEDIUM** (critic) node=None: domain constraint for x: all real numbers is not clearly addressed.


**Obligation 狀態**:
- ✅ [O1] Prove the stated goal → pass


## Stage 6 — Export Trace

**accepted**: True

**trace entries**: 1


