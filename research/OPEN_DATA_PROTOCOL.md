# Open Data Protocol for Paper Submission

This protocol defines a reproducible way to build long-term memory coding tasks from public history.

## 1) Research Goal

Measure whether practical coding usability differs between assistants even when generic benchmark scores are similar.

Primary hypothesis:

- H1: Model A and Model B have similar static benchmark performance but differ on practical long-term memory coding tasks.

## 2) Allowed Open Sources

Use only publicly accessible data:

- Public Git repositories and commit history
- Public pull requests, reviews, and issue discussions
- Public CI logs if license allows reuse
- Public code style guides and contribution docs

Do not use private IDE history, private chats, or unpublished internal tickets.

## 3) License and Governance Rules

- Record repo license for every data source.
- Exclude repositories with unclear or restrictive reuse terms.
- Store only minimal text needed for benchmarking.
- Keep full traceability: every generated task must map to source URLs and commit/PR IDs.

## 4) Unit of Data Collection

Collect history events in a normalized JSONL format:

- `repo`
- `event_type` (commit, pr_review, issue_comment, ci_failure, ci_fix)
- `event_id`
- `timestamp`
- `author`
- `text`
- `url`
- `license`

## 5) Task Construction Policy

Create one benchmark task from a small event bundle:

- Context event(s): prior decisions (naming, API behavior, migration policy)
- Trigger event: new bug/feature request
- Acceptance evidence: test expectation or review condition

Each task must include:

- Session 1 memory constraints (from older events)
- Session 2 implementation prompt (from newer event)
- Objective checks (tests, naming, scope boundaries)
- Provenance block (source URLs and IDs)

## 6) Split Strategy (Leakage Control)

Use time-based split:

- Train/dev tasks from older period
- Blind test tasks from newer period

Hard rule:

- No overlapping repositories between dev and blind test in the main evaluation.
- Optional cross-repo generalization split as secondary experiment.

## 7) Evaluation Setup

For each model:

- Same repo snapshot
- Same prompt text
- Same turn limit
- Same tool policy
- Same tests and scoring rubric

Repeat each task with multiple random seeds where applicable.

## 8) Metrics

Use the benchmark scoring guide plus provenance metrics:

- PracticalScore (weighted)
- Constraint fidelity
- Test pass rate
- Turns to completion
- Token budget
- Unrelated edit rate

Report with confidence intervals and bootstrap significance tests.

## 9) Statistical Analysis

Recommended:

- Paired bootstrap on per-task score deltas
- Wilcoxon signed-rank for robustness
- Effect size (Cliff's delta or matched Cohen's d)

## 10) Threats to Validity

- Source bias toward popular OSS stacks
- Reviewer subjectivity in practical UX scoring
- Temporal drift in model versions
- Tooling differences across providers

Mitigation:

- Diverse repositories
- Double annotation for subset
- Frozen model version tags
- Transparent run logs

## 11) Reproducibility Package

Release:

- Source registry CSV
- Normalized event JSONL (license-compliant subset)
- Task JSON
- Prompts
- Run logs
- Scoring scripts
- Final tables and plots
