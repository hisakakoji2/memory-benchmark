#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def group_by_repo(rows):
    grouped = {}
    for row in rows:
        repo = row.get("repo", "unknown")
        grouped.setdefault(repo, []).append(row)
    for repo in grouped:
        grouped[repo] = sorted(grouped[repo], key=lambda x: x.get("timestamp", ""))
    return grouped


def build_task(repo, bundle, idx):
    memory_events = [e for e in bundle[:-1] if e.get("event_type") in ("pr_review", "issue_comment", "commit")]
    trigger = bundle[-1]

    session_1_memory = []
    for e in memory_events[:3]:
        txt = (e.get("text") or "").strip().replace("\n", " ")
        if txt:
            session_1_memory.append(txt[:180])

    trigger_text = (trigger.get("text") or "Implement the requested change.").strip()
    task = {
        "id": f"OPEN-{idx:04d}",
        "title": f"Open-history task from {repo}",
        "category": "open-history",
        "difficulty": "medium",
        "repo_context": {
            "language": trigger.get("language", "unknown"),
            "framework": trigger.get("framework", "unknown"),
            "test_command": trigger.get("test_command", "run project tests")
        },
        "session_1_memory": session_1_memory or ["Follow prior repository decisions from earlier events."],
        "session_2_prompt": trigger_text[:280],
        "expected_outcomes": [
            "Implements the requested change.",
            "Respects prior historical constraints."
        ],
        "checks": {
            "must_pass_tests": True,
            "must_follow_memory_constraints": True,
            "max_changed_files": 5
        },
        "provenance": {
            "source_id": trigger.get("source_id", "SRC-UNKNOWN"),
            "source_events": [
                {
                    "event_type": e.get("event_type", "unknown"),
                    "event_id": e.get("event_id", "unknown"),
                    "url": e.get("url", "")
                }
                for e in bundle
            ],
            "license": trigger.get("license", "unknown")
        }
    }
    return task


def main():
    parser = argparse.ArgumentParser(description="Generate benchmark tasks from normalized open history events.")
    parser.add_argument("--input_jsonl", required=True, help="Path to normalized events JSONL")
    parser.add_argument("--output_json", required=True, help="Path to write generated tasks JSON")
    parser.add_argument("--window_size", type=int, default=4, help="Number of events per task bundle")
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input_jsonl))
    grouped = group_by_repo(rows)

    tasks = []
    idx = 1
    for repo, events in grouped.items():
        if len(events) < args.window_size:
            continue
        for i in range(args.window_size - 1, len(events)):
            bundle = events[i - args.window_size + 1 : i + 1]
            tasks.append(build_task(repo, bundle, idx))
            idx += 1

    out = {
        "version": "0.1-open-history",
        "description": "Tasks generated from normalized public repository history.",
        "tasks": tasks
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=True, indent=2)

    print(f"Generated {len(tasks)} tasks -> {out_path}")


if __name__ == "__main__":
    main()
