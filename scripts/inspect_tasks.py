#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_tasks(path: Path):
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj.get("tasks", []), obj


def print_task(task):
    print(f"id: {task.get('id','')}")
    print(f"title: {task.get('title','')}")
    print(f"category: {task.get('category','')}")
    print(f"difficulty: {task.get('difficulty','')}")
    rc = task.get("repo_context", {})
    print(f"repo_context.language: {rc.get('language','')}")
    print(f"repo_context.framework: {rc.get('framework','')}")
    print(f"repo_context.test_command: {rc.get('test_command','')}")
    print("\nsession_1_memory:")
    for i, m in enumerate(task.get("session_1_memory", []), start=1):
        print(f"  {i}. {m}")
    print("\nsession_2_prompt:")
    print(f"  {task.get('session_2_prompt','')}")
    print("\nexpected_outcomes:")
    for i, m in enumerate(task.get("expected_outcomes", []), start=1):
        print(f"  {i}. {m}")
    checks = task.get("checks", {})
    print("\nchecks:")
    print(f"  must_pass_tests: {checks.get('must_pass_tests')}")
    print(f"  must_follow_memory_constraints: {checks.get('must_follow_memory_constraints')}")
    print(f"  max_changed_files: {checks.get('max_changed_files')}")
    prov = task.get("provenance", {})
    print("\nprovenance:")
    print(f"  source_id: {prov.get('source_id','')}")
    print(f"  license: {prov.get('license','')}")
    for i, ev in enumerate(prov.get("source_events", []), start=1):
        print(f"  event_{i}: {ev.get('event_type','')} {ev.get('event_id','')} {ev.get('url','')}")


def main():
    parser = argparse.ArgumentParser(description="Inspect benchmark task contents.")
    parser.add_argument("--tasks_json", required=True, help="Path to task JSON")
    parser.add_argument("--task_id", default="", help="Task ID, e.g. OPEN-00137")
    parser.add_argument("--head", type=int, default=0, help="Print first N task IDs")
    args = parser.parse_args()

    tasks, meta = load_tasks(Path(args.tasks_json))
    print(f"task_file: {args.tasks_json}")
    print(f"task_count: {len(tasks)}")
    if "repo_count" in meta:
        print(f"repo_count: {meta.get('repo_count')}")
    if "event_count" in meta:
        print(f"event_count: {meta.get('event_count')}")

    if args.head > 0:
        print("\nfirst task ids:")
        for t in tasks[: args.head]:
            print(f"  - {t.get('id','')} : {t.get('title','')}")

    if args.task_id:
        found = [t for t in tasks if t.get("id") == args.task_id]
        if not found:
            print(f"\nTask not found: {args.task_id}")
            return
        print("\n--- task detail ---")
        print_task(found[0])


if __name__ == "__main__":
    main()
