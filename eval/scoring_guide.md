# Practical Memory Benchmark Scoring Guide

This guide is designed to compare coding assistants (for example GPT vs Claude) in practical coding workflows.

## Score Dimensions

- Quality (0-100)
  - Tests pass
  - No obvious regressions
  - Scope is correct (no unrelated edits)

- Efficiency (0-100)
  - Fewer turns to completion
  - Lower total token usage
  - Fewer retries after failure

- Long-Term Memory Use (0-100)
  - Correctly applies prior session constraints
  - Reuses historical naming/decision rules
  - Avoids contradiction with previous decisions

- Practical UX (0-100)
  - Output is easy to review
  - Handles ambiguity without derailing
  - Recovers quickly from context mismatch

## Final Score

Use this weighted formula:

PracticalScore = 0.35 * Quality + 0.25 * Efficiency + 0.25 * LongTermMemory + 0.15 * PracticalUX

## Penalty Rules

- -20 if tests fail and task requires passing tests
- -25 if session_1_memory constraints are violated
- -10 if changed_files exceeds max_changed_files
- -15 if assistant modifies unrelated files

## Minimal Human Review Checklist

For each task, reviewer answers:

1. Did the assistant follow all memory constraints from session 1?
2. Does the code change solve the requested task?
3. Is there any unnecessary or risky change?
4. Is the response easy for a teammate to merge?

Suggested scale: 1 (poor) to 5 (excellent), then convert to 0-100.
