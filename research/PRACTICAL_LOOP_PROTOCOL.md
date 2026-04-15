# Practical Repair-Loop Protocol

This protocol evaluates long-term memory under practical coding dynamics:

1. Current code context is provided.
2. Initial fix request is given.
3. Requirement changes after first solution.
4. Runtime/test failure signal is injected.
5. Model must repair while preserving prior constraints.

## Why this is closer to real work

- Requirements often change after first patch.
- Regressions are discovered only after tests/runtime checks.
- Teams expect continuity with prior conventions and constraints.

## Recommended evaluation

- Constraint retention after phase changes
- Regression handling quality after failure signal
- Scope control (avoid unrelated edits)
- Final correctness and explanation clarity

## Prompting Template (Manual)

Phase 0:
"Here is the current code context: <context_snippet>. Summarize the issue."

Phase 1:
"Apply an initial fix using these prior constraints: <memory list>."

Phase 2:
"Requirement changed: <phase_2 instruction>. Update your plan."

Phase 3:
"Runtime/Test feedback: <failing_signal>."

Phase 4:
"Provide final repaired solution and explain changes from initial fix."
