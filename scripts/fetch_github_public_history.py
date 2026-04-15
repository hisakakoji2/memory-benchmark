#!/usr/bin/env python3
import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


API_BASE = "https://api.github.com"


def github_get(path: str, token: str = ""):
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "memory-benchmark-open-history")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read().decode("utf-8"))


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def compact_text(*parts):
    merged = " ".join([p.strip() for p in parts if p and p.strip()])
    return " ".join(merged.split())


def is_noisy_text(text: str):
    low = text.lower()
    return low.startswith("merge branch") or low.startswith("merge pull request")


def fetch_pulls(repo: str, limit: int, token: str):
    q = urllib.parse.urlencode({"state": "closed", "per_page": min(limit, 100)})
    pulls = github_get(f"/repos/{repo}/pulls?{q}", token)
    out = []
    for pr in pulls[:limit]:
        text = compact_text(pr.get("title", ""), pr.get("body", ""))[:500]
        if is_noisy_text(text):
            continue
        out.append(
            {
                "event_type": "issue_comment",
                "event_id": f"PR-{pr['number']}",
                "timestamp": pr.get("updated_at") or pr.get("created_at"),
                "author": (pr.get("user") or {}).get("login", "unknown"),
                "text": text,
                "url": pr.get("html_url", ""),
            }
        )
    return out


def fetch_issues(repo: str, limit: int, token: str):
    q = urllib.parse.urlencode({"state": "closed", "per_page": min(limit, 100)})
    issues = github_get(f"/repos/{repo}/issues?{q}", token)
    out = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        text = compact_text(issue.get("title", ""), issue.get("body", ""))[:500]
        if is_noisy_text(text):
            continue
        out.append(
            {
                "event_type": "issue_comment",
                "event_id": f"ISSUE-{issue['number']}",
                "timestamp": issue.get("updated_at") or issue.get("created_at"),
                "author": (issue.get("user") or {}).get("login", "unknown"),
                "text": text,
                "url": issue.get("html_url", ""),
            }
        )
        if len(out) >= limit:
            break
    return out


def fetch_commits(repo: str, limit: int, token: str):
    q = urllib.parse.urlencode({"per_page": min(limit, 100)})
    commits = github_get(f"/repos/{repo}/commits?{q}", token)
    out = []
    for c in commits[:limit]:
        commit = c.get("commit", {})
        author = (commit.get("author") or {}).get("name", "unknown")
        text = compact_text(commit.get("message", ""))[:500]
        if is_noisy_text(text):
            continue
        out.append(
            {
                "event_type": "commit",
                "event_id": c.get("sha", "unknown")[:12],
                "timestamp": (commit.get("author") or {}).get("date"),
                "author": author,
                "text": text,
                "url": c.get("html_url", ""),
            }
        )
    return out


def main():
    parser = argparse.ArgumentParser(description="Fetch normalized open history from a public GitHub repo.")
    parser.add_argument("--repo", default="microsoft/vscode", help="Repository in owner/name format")
    parser.add_argument("--out_jsonl", default="research/normalized_events_vscode.jsonl", help="Output JSONL path")
    parser.add_argument("--max_prs", type=int, default=30, help="Number of PR events")
    parser.add_argument("--max_issues", type=int, default=30, help="Number of issue events")
    parser.add_argument("--max_commits", type=int, default=40, help="Number of commit events")
    parser.add_argument("--source_id", default="SRC-VSCODE-001", help="Source ID for provenance")
    parser.add_argument("--license", default="MIT", help="Repo license string for provenance")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN", "")
    events = []
    events.extend(fetch_pulls(args.repo, args.max_prs, token))
    time.sleep(0.2)
    events.extend(fetch_issues(args.repo, args.max_issues, token))
    time.sleep(0.2)
    events.extend(fetch_commits(args.repo, args.max_commits, token))

    normalized = []
    for ev in events:
        ts = ev.get("timestamp")
        if not ts:
            ts = iso_now()
        normalized.append(
            {
                "source_id": args.source_id,
                "repo": args.repo,
                "event_type": ev.get("event_type", "unknown"),
                "event_id": ev.get("event_id", "unknown"),
                "timestamp": ts,
                "author": ev.get("author", "unknown"),
                "text": ev.get("text", ""),
                "url": ev.get("url", ""),
                "license": args.license,
                "language": "typescript",
                "framework": "electron",
                "test_command": "npm test"
            }
        )

    normalized.sort(key=lambda x: x["timestamp"])

    out_path = Path(args.out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in normalized:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")

    print(f"Wrote {len(normalized)} events to {out_path}")


if __name__ == "__main__":
    main()
