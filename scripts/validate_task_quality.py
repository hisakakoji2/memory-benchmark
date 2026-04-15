#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def load_tasks(path: Path):
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj


def normalize(s: str):
    return " ".join((s or "").lower().split())


def has_meaningful_memory(task):
    mem = task.get("session_1_memory", [])
    if len(mem) < 2:
        return False
    unique = {normalize(m) for m in mem if normalize(m)}
    return len(unique) >= 2


def prompt_good(task, min_len=40):
    p = normalize(task.get("session_2_prompt", ""))
    return len(p) >= min_len


def duplicate_memory_ratio(task):
    mem = [normalize(m) for m in task.get("session_1_memory", []) if normalize(m)]
    if not mem:
        return 1.0
    unique = len(set(mem))
    return 1.0 - (unique / len(mem))


def score_task(task):
    score = 100
    if not has_meaningful_memory(task):
        score -= 40
    if not prompt_good(task):
        score -= 30
    dup = duplicate_memory_ratio(task)
    if dup > 0.34:
        score -= 20
    if dup > 0.66:
        score -= 20
    return max(0, score)


def main():
    parser = argparse.ArgumentParser(description="Validate and filter benchmark task quality.")
    parser.add_argument("--input_json", required=True)
    parser.add_argument("--output_json", required=True)
    parser.add_argument("--min_score", type=int, default=70)
    parser.add_argument("--max_tasks", type=int, default=0, help="0 means keep all passing tasks")
    args = parser.parse_args()

    obj = load_tasks(Path(args.input_json))
    tasks = obj.get("tasks", [])

    kept = []
    dropped = 0
    for t in tasks:
        s = score_task(t)
        t["quality_score_auto"] = s
        if s >= args.min_score:
            kept.append(t)
        else:
            dropped += 1

    if args.max_tasks > 0:
        kept = kept[: args.max_tasks]

    out = dict(obj)
    out["description"] = (obj.get("description", "") + " | quality-filtered").strip()
    out["task_count"] = len(kept)
    out["tasks"] = kept
    out["quality_filter"] = {
        "min_score": args.min_score,
        "input_count": len(tasks),
        "kept_count": len(kept),
        "dropped_count": dropped,
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=True, indent=2)

    print(f"input_count:  {len(tasks)}")
    print(f"kept_count:   {len(kept)}")
    print(f"dropped:      {dropped}")
    print(f"output_json:  {out_path}")


if __name__ == "__main__":
    main()
