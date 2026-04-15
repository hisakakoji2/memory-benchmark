#!/usr/bin/env python3
import argparse
import csv
from collections import defaultdict
from pathlib import Path


def to_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def load_rows(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def choose_score(row, include_latency=False):
    # If manual quality is present, combine it with automatic memory score.
    quality = row.get("quality_score_manual", "").strip()
    ux = row.get("practical_ux_manual", "").strip()
    mem = to_float(row.get("memory_hit_rate", 0.0)) * 100.0
    latency = to_float(row.get("latency_ms", 0.0))
    # Lower latency is better; clamp to 0-100 with simple transform.
    eff = max(0.0, min(100.0, 100.0 - latency / 80.0))

    if quality and ux:
        q = to_float(quality, 0.0)
        u = to_float(ux, 0.0)
        return 0.45 * q + 0.35 * mem + 0.20 * u
    if include_latency:
        return 0.65 * mem + 0.35 * eff
    return mem


def mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def main():
    parser = argparse.ArgumentParser(description="Analyze pair benchmark summary CSV.")
    parser.add_argument("--summary_csv", required=True)
    parser.add_argument("--model_a", required=True)
    parser.add_argument("--model_b", required=True)
    parser.add_argument(
        "--include_latency",
        action="store_true",
        help="Include latency-based efficiency in auto score (default: off)",
    )
    args = parser.parse_args()

    rows = load_rows(Path(args.summary_csv))
    by_model = defaultdict(list)
    by_task = defaultdict(dict)

    for r in rows:
        m = r.get("model", "")
        s = choose_score(r, include_latency=args.include_latency)
        by_model[m].append(s)
        by_task[r.get("task_id", "")][m] = s

    a_scores = by_model.get(args.model_a, [])
    b_scores = by_model.get(args.model_b, [])
    paired_deltas = []
    for _, item in by_task.items():
        if args.model_a in item and args.model_b in item:
            paired_deltas.append(item[args.model_b] - item[args.model_a])

    print("=== Pair Benchmark Report ===")
    print(f"Scoring mode: {'memory+latency' if args.include_latency else 'memory-only (manual preferred)'}")
    print(f"Model A: {args.model_a} avg_score={mean(a_scores):.2f} n={len(a_scores)}")
    print(f"Model B: {args.model_b} avg_score={mean(b_scores):.2f} n={len(b_scores)}")
    print(f"Paired tasks: {len(paired_deltas)}")
    if paired_deltas:
        gt = len([d for d in paired_deltas if d > 0])
        lt = len([d for d in paired_deltas if d < 0])
        eq = len([d for d in paired_deltas if d == 0])
        print(f"Win/Loss/Tie for model_b over model_a: {gt}/{lt}/{eq}")
        print(f"Mean paired delta (model_b - model_a): {mean(paired_deltas):.2f}")


if __name__ == "__main__":
    main()
