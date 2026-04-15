#!/usr/bin/env bash
set -euo pipefail

# Create GitHub repository and push current branch.
# Required:
#   export GITHUB_TOKEN=...
# Usage:
#   ./scripts/create_repo_and_push.sh hisakakoji2 memory-benchmark

OWNER="${1:-}"
REPO="${2:-memory-benchmark}"
VISIBILITY="${VISIBILITY:-public}" # public|private

if [[ -z "${OWNER}" ]]; then
  echo "Usage: ./scripts/create_repo_and_push.sh <github-owner> [repo-name]"
  exit 1
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN is required."
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT_DIR}"

python3 - <<'PY'
import json, os, urllib.request, urllib.error

owner = os.environ["OWNER"]
repo = os.environ["REPO"]
visibility = os.environ["VISIBILITY"]
token = os.environ["GITHUB_TOKEN"]

url = "https://api.github.com/user/repos"
payload = {
    "name": repo,
    "private": visibility != "public",
    "auto_init": False,
    "description": "Practical long-memory benchmark toolkit for code-repair loops.",
}
req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
req.add_header("Accept", "application/vnd.github+json")
req.add_header("User-Agent", "memory-benchmark-agent")
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Content-Type", "application/json")

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("Repository created:", r.status)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="ignore")
    # 422 usually means repository already exists; allow continuation.
    if e.code == 422 and "name already exists" in body.lower():
        print("Repository already exists; continuing.")
    else:
        print("Repository creation failed:", e.code, body[:500])
        raise
PY

REMOTE_URL="https://github.com/${OWNER}/${REPO}.git"
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "${REMOTE_URL}"
else
  git remote add origin "${REMOTE_URL}"
fi

git branch -M main
git push -u "https://${GITHUB_TOKEN}@github.com/${OWNER}/${REPO}.git" main

echo "Pushed to: ${REMOTE_URL}"
