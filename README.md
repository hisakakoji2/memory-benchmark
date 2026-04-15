# Memory Benchmark Trial Pack

Small trial benchmark to compare practical coding usability between assistants (for example GPT and Claude), with emphasis on long-term memory.

## Included Files

- `tasks/sample_tasks.json`: 6 practical long-term memory tasks
- `eval/scoring_guide.md`: scoring rules and penalties
- `results/results_template.csv`: result logging template

## How To Run (Manual Trial)

1. Pick one task from `tasks/sample_tasks.json`.
2. Provide the model with `session_1_memory` first.
3. In a new turn/session, provide only `session_2_prompt`.
4. Let the model implement the change in your target repo.
5. Run task test command (`repo_context.test_command`).
6. Score the result using `eval/scoring_guide.md`.
7. Save the row into `results/results_template.csv`.
8. Repeat under same conditions for another model.

## Fair Comparison Rules

- Same repository snapshot for each model
- Same prompts (copy exactly)
- Same max number of turns
- Same test command and same reviewer

## Suggested First Experiment

- Run `TASK-001`, `TASK-003`, `TASK-004` first.
- These three tasks usually expose memory carry-over and practical coding behavior differences quickly.

## Next Step

If this trial works for you, expand from 6 to 30+ tasks by mining your own:

- Git commits
- PR review comments
- Issue decisions
- Team coding conventions

## Paper-Ready Open Data Pipeline

For publication-grade experiments using only open sources:

- `research/OPEN_DATA_PROTOCOL.md`: full protocol (license, splits, statistics)
- `research/source_registry_template.csv`: track source repositories
- `research/normalized_events_sample.jsonl`: normalized event format example
- `tasks/open_task_schema.json`: schema with provenance requirements
- `scripts/generate_tasks_from_events.py`: deterministic task generation script

Generate tasks from normalized public history:

```bash
python scripts/generate_tasks_from_events.py \
  --input_jsonl research/normalized_events_sample.jsonl \
  --output_json tasks/generated_open_tasks.json \
  --window_size 4
```

Then evaluate generated tasks exactly like the manual trial.

Example with VS Code OSS (`microsoft/vscode`):

```bash
python scripts/fetch_github_public_history.py \
  --repo microsoft/vscode \
  --out_jsonl research/normalized_events_vscode.jsonl \
  --max_prs 20 --max_issues 20 --max_commits 30 \
  --source_id SRC-VSCODE-001 --license MIT

python scripts/generate_tasks_from_events.py \
  --input_jsonl research/normalized_events_vscode.jsonl \
  --output_json tasks/generated_vscode_tasks.json \
  --window_size 4
```

## Pair Runner (Old vs New Models)

You can run two models under exactly the same task set using an OpenAI-compatible API.

Required env:

```bash
export OPENAI_API_KEY="YOUR_KEY"
# Optional for OpenRouter or other compatible providers:
# export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
```

OpenRouter shortcut:

```bash
export OPENROUTER_API_KEY="YOUR_OPENROUTER_KEY"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
```

Using Gemini API key (OpenAI-compatible endpoint):

```bash
export GEMINI_API_KEY="YOUR_GEMINI_KEY"
# Optional override (default is set automatically by run_pair_local.sh)
# export OPENAI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"
```

Run pair benchmark:

```bash
python scripts/run_openai_compatible_pair.py \
  --tasks_json tasks/generated_vscode_tasks.json \
  --model_a "OLD_MODEL_ID" \
  --model_b "NEW_MODEL_ID" \
  --max_tasks 20 \
  --validate_models \
  --output_dir results/pair_runs
```

This writes:

- raw responses: `results/pair_runs/<run_id>_<model>_raw.jsonl`
- summary sheet: `results/pair_runs/<run_id>_summary.csv`

Analyze summary:

```bash
python scripts/analyze_pair_summary.py \
  --summary_csv results/pair_runs/<run_id>_summary.csv \
  --model_a "OLD_MODEL_ID" \
  --model_b "NEW_MODEL_ID"
```

By default, analysis ignores latency (memory-only scoring).
To include latency again:

```bash
python scripts/analyze_pair_summary.py \
  --summary_csv results/pair_runs/<run_id>_summary.csv \
  --model_a "OLD_MODEL_ID" \
  --model_b "NEW_MODEL_ID" \
  --include_latency
```

Shortcut wrapper (run + analyze latest):

```bash
chmod +x scripts/run_pair_local.sh
./scripts/run_pair_local.sh "OLD_MODEL_ID" "NEW_MODEL_ID" 20
```

Gemini example:

```bash
./scripts/run_pair_local.sh "gemini-2.5-flash" "gemini-2.5-pro" 20
```

If OpenRouter returns "No endpoints found", list available model IDs:

```bash
python3 - <<'PY'
import os, json, urllib.request
base = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
req = urllib.request.Request(base + "/models")
req.add_header("Authorization", f"Bearer {os.environ['OPENAI_API_KEY']}")
with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read().decode())
for m in sorted(x["id"] for x in data.get("data", []) if "id" in x):
    print(m)
PY
```

## Generate ~300 Open Tasks

Build a larger task set from multiple public OSS repos:

```bash
python scripts/build_open_300_tasks.py \
  --max_tasks 300 \
  --per_type 18 \
  --window_size 4 \
  --events_out research/normalized_events_multi.jsonl \
  --tasks_out tasks/generated_open_tasks_300.json
```

Optional: set `GITHUB_TOKEN` to reduce GitHub API rate limits.

## Cursor-Only Local Generation (No Model API)

If you want to prepare benchmark suites inside Cursor without calling model APIs:

```bash
# 1) Build Python-focused long-memory tasks from existing normalized events
python scripts/build_python_longmem_suite.py \
  --input_events_jsonl research/normalized_events_multi.jsonl \
  --output_json tasks/generated_python_longmem_tasks.json \
  --max_tasks 120

# 2) Quality-filter generic 300-task suite
python scripts/validate_task_quality.py \
  --input_json tasks/generated_open_tasks_300.json \
  --output_json tasks/generated_open_tasks_300_filtered.json \
  --min_score 70 --max_tasks 250

# 3) Quality-filter Python suite
python scripts/validate_task_quality.py \
  --input_json tasks/generated_python_longmem_tasks.json \
  --output_json tasks/generated_python_longmem_tasks_filtered.json \
  --min_score 70

# 4) Build harder practical repair-loop tasks with explicit expectation rubric
python scripts/build_practical_loop_tasks.py \
  --input_json tasks/generated_python_longmem_tasks_filtered.json \
  --output_json tasks/generated_practical_loop_tasks_hard.json \
  --max_tasks 80 --hard_mode
```

If you hit rate-limit errors (HTTP 429), slow requests down:

```bash
REQUEST_INTERVAL_S=3 MAX_RETRIES=10 ./scripts/run_pair_local.sh "OLD_MODEL_ID" "NEW_MODEL_ID" 10
```

The runner also retries transient provider errors (500/502/503/504).

If you hit OpenRouter credit errors (HTTP 402), reduce output token budget:

```bash
MAX_TOKENS=300 REQUEST_INTERVAL_S=3 MAX_RETRIES=10 ./scripts/run_pair_local.sh "OLD_MODEL_ID" "NEW_MODEL_ID" 5
```
