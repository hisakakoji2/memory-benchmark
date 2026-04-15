#!/usr/bin/env python3
import argparse
import json
import random
from pathlib import Path


PYTHON_REPO_HINTS = (
    "python/",
    "django/",
    "pallets/",
    "fastapi/",
    "pydantic/",
    "pandas/",
    "numpy/",
)


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def is_python_event(row):
    repo = (row.get("repo") or "").lower()
    lang = (row.get("language") or "").lower()
    return lang == "python" or any(repo.startswith(h) for h in PYTHON_REPO_HINTS)


def clean_text(text, limit=220):
    t = " ".join((text or "").split())
    return t[:limit]


def make_memory_block(bundle):
    # Build an explicit long-term-memory challenge:
    # older context + newer override + compatibility constraint.
    older = clean_text(bundle[0].get("text", ""))
    mid = clean_text(bundle[1].get("text", ""))
    newer = clean_text(bundle[2].get("text", ""))
    return [
        f"Older context (may be outdated): {older}",
        f"Compatibility constraint from prior work: {mid}",
        f"Latest decision takes precedence when conflicting: {newer}",
    ]


def build_task(repo, bundle, idx):
    trigger = bundle[-1]
    prompt = clean_text(trigger.get("text", ""), 320)
    if len(prompt) < 40:
        return None

    task = {
        "id": f"PYMEM-{idx:05d}",
        "title": f"Python long-memory task from {repo}",
        "category": "python-long-memory",
        "difficulty": "medium",
        "memory_challenge_type": "update-priority-conflict",
        "repo_context": {
            "language": "python",
            "framework": trigger.get("framework", "python"),
            "test_command": trigger.get("test_command", "pytest"),
        },
        "session_1_memory": make_memory_block(bundle),
        "session_2_prompt": prompt,
        "expected_outcomes": [
            "Implements the requested Python change.",
            "Applies latest decision over older conflicting memory.",
            "Preserves compatibility constraints where possible.",
        ],
        "checks": {
            "must_pass_tests": True,
            "must_follow_memory_constraints": True,
            "max_changed_files": 6,
        },
        "provenance": {
            "source_id": trigger.get("source_id", "SRC-PY-LONGMEM-001"),
            "source_events": [
                {
                    "event_type": e.get("event_type", "unknown"),
                    "event_id": e.get("event_id", "unknown"),
                    "url": e.get("url", ""),
                }
                for e in bundle
            ],
            "license": trigger.get("license", "public"),
        },
    }
    return task


def main():
    parser = argparse.ArgumentParser(description="Build Python-focused long-memory benchmark tasks.")
    parser.add_argument(
        "--input_events_jsonl",
        default="research/normalized_events_multi.jsonl",
        help="Normalized events JSONL (from build_open_300_tasks.py or similar).",
    )
    parser.add_argument("--output_json", default="tasks/generated_python_longmem_tasks.json")
    parser.add_argument("--window_size", type=int, default=4)
    parser.add_argument("--max_tasks", type=int, default=120)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input_events_jsonl))
    py_rows = [r for r in rows if is_python_event(r)]
    py_rows.sort(key=lambda x: x.get("timestamp", ""))

    by_repo = {}
    for r in py_rows:
        by_repo.setdefault(r["repo"], []).append(r)

    tasks = []
    idx = 1
    for repo, evs in by_repo.items():
        if len(evs) < args.window_size:
            continue
        for i in range(args.window_size - 1, len(evs)):
            bundle = evs[i - args.window_size + 1 : i + 1]
            t = build_task(repo, bundle, idx)
            if t:
                tasks.append(t)
                idx += 1

    # Dedupe by prompt
    dedup = {}
    for t in tasks:
        key = t["session_2_prompt"].lower()
        if key not in dedup:
            dedup[key] = t
    tasks = list(dedup.values())

    random.seed(args.seed)
    random.shuffle(tasks)
    tasks = tasks[: args.max_tasks]

    out = {
        "version": "0.1-python-longmem",
        "description": "Python-focused long-term memory benchmark tasks with explicit update-priority constraints.",
        "task_count": len(tasks),
        "tasks": tasks,
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=True, indent=2)

    print(f"python_events: {len(py_rows)}")
    print(f"tasks_written: {len(tasks)}")
    print(f"output_json:   {out_path}")


if __name__ == "__main__":
    main()
