#!/usr/bin/env python3
import argparse
import json
import os
import random
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


API_BASE = "https://api.github.com"


DEFAULT_REPOS = [
    "microsoft/vscode",
    "microsoft/TypeScript",
    "vercel/next.js",
    "facebook/react",
    "nodejs/node",
    "python/cpython",
    "django/django",
    "pallets/flask",
    "rust-lang/rust",
    "golang/go",
]


def github_get(path: str, token: str = ""):
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "memory-benchmark-open-history")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as res:
        return json.loads(res.read().decode("utf-8"))


def compact_text(*parts):
    merged = " ".join([p.strip() for p in parts if p and p.strip()])
    return " ".join(merged.split())


def is_noisy_text(text: str):
    low = text.lower()
    return low.startswith("merge branch") or low.startswith("merge pull request")


def repo_language_hint(repo: str):
    low = repo.lower()
    if "typescript" in low or "next.js" in low or "react" in low or "vscode" in low or "node" in low:
        return "typescript"
    if "python" in low or "django" in low or "flask" in low or "cpython" in low:
        return "python"
    if "rust" in low:
        return "rust"
    if "golang" in low or low.endswith("/go"):
        return "go"
    return "unknown"


def repo_framework_hint(repo: str):
    low = repo.lower()
    if "vscode" in low:
        return "electron"
    if "next.js" in low:
        return "nextjs"
    if "react" in low:
        return "react"
    if "django" in low:
        return "django"
    if "flask" in low:
        return "flask"
    if "typescript" in low:
        return "typescript"
    return "general"


def test_command_hint(repo: str):
    low = repo.lower()
    if "python" in low or "django" in low or "flask" in low or "cpython" in low:
        return "pytest"
    if "rust" in low:
        return "cargo test"
    if "golang" in low or low.endswith("/go"):
        return "go test ./..."
    return "npm test"


def fetch_repo_events(repo: str, per_type: int, token: str, source_id: str):
    events = []

    q = urllib.parse.urlencode({"state": "closed", "per_page": min(per_type, 100)})
    pulls = github_get(f"/repos/{repo}/pulls?{q}", token)
    for pr in pulls[:per_type]:
        text = compact_text(pr.get("title", ""), pr.get("body", ""))[:500]
        if not text or is_noisy_text(text):
            continue
        events.append(
            {
                "source_id": source_id,
                "repo": repo,
                "event_type": "pr",
                "event_id": f"PR-{pr['number']}",
                "timestamp": pr.get("updated_at") or pr.get("created_at"),
                "author": (pr.get("user") or {}).get("login", "unknown"),
                "text": text,
                "url": pr.get("html_url", ""),
                "license": "public",
                "language": repo_language_hint(repo),
                "framework": repo_framework_hint(repo),
                "test_command": test_command_hint(repo),
            }
        )

    issues = github_get(f"/repos/{repo}/issues?{q}", token)
    count = 0
    for issue in issues:
        if "pull_request" in issue:
            continue
        text = compact_text(issue.get("title", ""), issue.get("body", ""))[:500]
        if not text or is_noisy_text(text):
            continue
        events.append(
            {
                "source_id": source_id,
                "repo": repo,
                "event_type": "issue",
                "event_id": f"ISSUE-{issue['number']}",
                "timestamp": issue.get("updated_at") or issue.get("created_at"),
                "author": (issue.get("user") or {}).get("login", "unknown"),
                "text": text,
                "url": issue.get("html_url", ""),
                "license": "public",
                "language": repo_language_hint(repo),
                "framework": repo_framework_hint(repo),
                "test_command": test_command_hint(repo),
            }
        )
        count += 1
        if count >= per_type:
            break

    cq = urllib.parse.urlencode({"per_page": min(per_type, 100)})
    commits = github_get(f"/repos/{repo}/commits?{cq}", token)
    for c in commits[:per_type]:
        commit = c.get("commit", {})
        text = compact_text(commit.get("message", ""))[:500]
        if not text or is_noisy_text(text):
            continue
        events.append(
            {
                "source_id": source_id,
                "repo": repo,
                "event_type": "commit",
                "event_id": c.get("sha", "unknown")[:12],
                "timestamp": (commit.get("author") or {}).get("date"),
                "author": (commit.get("author") or {}).get("name", "unknown"),
                "text": text,
                "url": c.get("html_url", ""),
                "license": "public",
                "language": repo_language_hint(repo),
                "framework": repo_framework_hint(repo),
                "test_command": test_command_hint(repo),
            }
        )

    events = [e for e in events if e.get("timestamp")]
    events.sort(key=lambda x: x["timestamp"])
    return events


def build_task(repo, bundle, idx):
    memory_events = bundle[:-1]
    trigger = bundle[-1]

    session_1 = []
    for e in memory_events[:3]:
        txt = (e.get("text") or "").replace("\n", " ").strip()
        if txt:
            session_1.append(txt[:180])
    if len(session_1) < 2:
        return None

    session_2 = (trigger.get("text") or "").strip()[:320]
    if len(session_2) < 40:
        return None

    task = {
        "id": f"OPEN-{idx:05d}",
        "title": f"Open-history task from {repo}",
        "category": "open-history",
        "difficulty": "medium",
        "repo_context": {
            "language": trigger.get("language", "unknown"),
            "framework": trigger.get("framework", "unknown"),
            "test_command": trigger.get("test_command", "run project tests"),
        },
        "session_1_memory": session_1,
        "session_2_prompt": session_2,
        "expected_outcomes": [
            "Implements the requested change.",
            "Respects prior historical constraints.",
        ],
        "checks": {
            "must_pass_tests": True,
            "must_follow_memory_constraints": True,
            "max_changed_files": 5,
        },
        "provenance": {
            "source_id": trigger.get("source_id", "SRC-OPEN-MULTI"),
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


def build_tasks_from_events(events, window_size, max_tasks, seed):
    by_repo = {}
    for ev in events:
        by_repo.setdefault(ev["repo"], []).append(ev)
    for repo in by_repo:
        by_repo[repo].sort(key=lambda x: x["timestamp"])

    tasks = []
    idx = 1
    for repo, evs in by_repo.items():
        if len(evs) < window_size:
            continue
        for i in range(window_size - 1, len(evs)):
            bundle = evs[i - window_size + 1 : i + 1]
            t = build_task(repo, bundle, idx)
            if t is None:
                continue
            tasks.append(t)
            idx += 1

    # Dedupe by prompt text.
    dedup = {}
    for t in tasks:
        key = t["session_2_prompt"].lower()
        if key not in dedup:
            dedup[key] = t
    tasks = list(dedup.values())

    random.seed(seed)
    random.shuffle(tasks)
    return tasks[:max_tasks]


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Build ~300 open-history long-memory tasks from public OSS repos.")
    parser.add_argument("--repos", default=",".join(DEFAULT_REPOS), help="Comma-separated owner/repo list")
    parser.add_argument("--per_type", type=int, default=18, help="Events per type (PR/Issue/Commit) per repo")
    parser.add_argument("--window_size", type=int, default=4)
    parser.add_argument("--max_tasks", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--events_out", default="research/normalized_events_multi.jsonl")
    parser.add_argument("--tasks_out", default="tasks/generated_open_tasks_300.json")
    parser.add_argument("--source_id", default="SRC-OPEN-MULTI-001")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN", "")
    repos = [r.strip() for r in args.repos.split(",") if r.strip()]

    all_events = []
    for repo in repos:
        try:
            evs = fetch_repo_events(repo, args.per_type, token, args.source_id)
            all_events.extend(evs)
            print(f"[ok] {repo}: {len(evs)} events")
        except Exception as e:
            print(f"[warn] {repo}: fetch failed ({e})")
        time.sleep(0.2)

    all_events.sort(key=lambda x: x["timestamp"])
    write_jsonl(Path(args.events_out), all_events)

    tasks = build_tasks_from_events(
        all_events,
        window_size=args.window_size,
        max_tasks=args.max_tasks,
        seed=args.seed,
    )
    out = {
        "version": "0.2-open-history-multi",
        "description": "Open-history long-memory tasks generated from multiple public OSS repositories.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_count": len(repos),
        "event_count": len(all_events),
        "task_count": len(tasks),
        "tasks": tasks,
    }
    out_path = Path(args.tasks_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=True, indent=2)

    print(f"Wrote events: {args.events_out}")
    print(f"Wrote tasks:  {args.tasks_out}")
    print(f"Task count:   {len(tasks)}")


if __name__ == "__main__":
    main()
