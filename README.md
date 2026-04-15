# Practical Loop Memory Benchmark

Practical long-term memory benchmark focused on real repair loops:

1. understand current state,
2. propose initial fix,
3. adapt to requirement change,
4. react to failure signal,
5. produce revised repair plan.

## Main Assets

- `tasks/generated_practical_loop_tasks.json`  
  Base practical loop tasks.
- `tasks/generated_practical_loop_tasks_hard.json`  
  Hard mode tasks with stricter constraints and explicit expectations.
- `scripts/build_practical_loop_tasks.py`  
  Generator that produces practical loop tasks.
- `research/PRACTICAL_LOOP_PROTOCOL.md`  
  Protocol and phase template for manual or scripted evaluation.

## Generate Hard Practical Tasks

```bash
python scripts/build_practical_loop_tasks.py \
  --input_json tasks/generated_practical_loop_tasks.json \
  --output_json tasks/generated_practical_loop_tasks_hard.json \
  --max_tasks 80 \
  --hard_mode
```

## Inspect Task Details

```bash
python scripts/inspect_tasks.py \
  --tasks_json tasks/generated_practical_loop_tasks_hard.json \
  --task_id PRACT-00001
```

## Run Model Pair Evaluation

Set provider credentials (OpenRouter example):

```bash
export OPENROUTER_API_KEY="YOUR_OPENROUTER_KEY"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
```

Run evaluation:

```bash
TASKS_JSON=tasks/generated_practical_loop_tasks_hard.json \
REQUEST_INTERVAL_S=3 \
MAX_RETRIES=10 \
MAX_TOKENS=300 \
./scripts/run_pair_local.sh "MODEL_A" "MODEL_B" 10
```

Analyze summary:

```bash
python scripts/analyze_pair_summary.py \
  --summary_csv results/pair_runs/<run_id>_summary.csv \
  --model_a "MODEL_A" \
  --model_b "MODEL_B"
```

Use `--include_latency` if you want speed to affect score.
