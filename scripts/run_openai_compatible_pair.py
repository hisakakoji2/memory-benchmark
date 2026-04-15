#!/usr/bin/env python3
import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def load_tasks(path: Path):
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj.get("tasks", [])


def build_messages(task):
    memory_lines = "\n".join([f"- {m}" for m in task.get("session_1_memory", [])])
    task_prompt = task.get("session_2_prompt", "")
    content = (
        "Session 1 memory constraints:\n"
        f"{memory_lines}\n\n"
        "Session 2 implementation request:\n"
        f"{task_prompt}\n\n"
        "Respond in two sections:\n"
        "1) Implementation approach (short)\n"
        "2) Explicitly list which memory constraints you applied"
    )
    return [{"role": "user", "content": content}]


def call_chat_completion(
    base_url,
    api_key,
    model,
    messages,
    temperature=0.0,
    max_tokens=700,
    max_retries=6,
):
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    attempt = 0
    retryable_status = {429, 500, 502, 503, 504}
    while True:
        attempt += 1
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                elapsed_ms = int((time.time() - start) * 1000)
                body = json.loads(res.read().decode("utf-8"))
                return body, elapsed_ms
        except urllib.error.HTTPError as e:
            code = int(e.code)
            if code not in retryable_status or attempt > max_retries:
                # Print API body for easier debugging on non-retryable failures.
                try:
                    err_body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    err_body = ""
                if err_body:
                    print(f"[error] model={model} status={code} body={err_body[:500]}")
                raise
            retry_after = e.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait_s = int(retry_after)
            else:
                wait_s = min(60, 2 ** attempt)
            print(f"[retry] status={code} model={model}, attempt={attempt}, waiting {wait_s}s")
            time.sleep(wait_s)
        except urllib.error.URLError as e:
            # Transient network errors: retry similarly.
            if attempt > max_retries:
                raise
            wait_s = min(60, 2 ** attempt)
            print(f"[retry] network error model={model}, attempt={attempt}, waiting {wait_s}s: {e}")
            time.sleep(wait_s)


def fetch_model_ids(base_url, api_key):
    url = base_url.rstrip("/") + "/models"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as res:
        body = json.loads(res.read().decode("utf-8"))
    return [m.get("id", "") for m in body.get("data", []) if m.get("id")]


def suggest_models(requested_model, available_ids, max_items=8):
    needle = requested_model.lower()
    requested_tail = needle.split("/")[-1]
    scored = []
    for mid in available_ids:
        low = mid.lower()
        score = 0
        if needle == low:
            score += 100
        if requested_tail and requested_tail in low:
            score += 50
        if "claude" in requested_tail and "claude" in low:
            score += 10
        if "gpt" in requested_tail and "gpt" in low:
            score += 10
        if "gemini" in requested_tail and "gemini" in low:
            score += 10
        if score > 0:
            scored.append((score, mid))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [mid for _, mid in scored[:max_items]]


def normalize_text(text):
    return " ".join((text or "").lower().split())


def memory_hit_rate(task, response_text):
    checks = task.get("session_1_memory", [])
    if not checks:
        return 0.0
    response_norm = normalize_text(response_text)
    hits = 0
    for memory in checks:
        words = [w for w in normalize_text(memory).split(" ") if len(w) >= 4]
        if not words:
            continue
        # Hit if at least one salient word appears.
        if any(w in response_norm for w in words[:6]):
            hits += 1
    return round(hits / max(len(checks), 1), 4)


def run_model(
    tasks,
    model_name,
    base_url,
    api_key,
    out_jsonl: Path,
    request_interval_s=0.0,
    max_retries=6,
    max_tokens=700,
):
    rows = []
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as logf:
        for task in tasks:
            messages = build_messages(task)
            body, latency_ms = call_chat_completion(
                base_url,
                api_key,
                model_name,
                messages,
                max_tokens=max_tokens,
                max_retries=max_retries,
            )
            choice = (body.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            text = message.get("content", "")
            usage = body.get("usage") or {}

            record = {
                "model": model_name,
                "task_id": task.get("id", "UNKNOWN"),
                "response": text,
                "latency_ms": latency_ms,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "memory_hit_rate": memory_hit_rate(task, text),
            }
            logf.write(json.dumps(record, ensure_ascii=True) + "\n")
            rows.append(record)
            if request_interval_s > 0:
                time.sleep(request_interval_s)
    return rows


def write_csv(rows, path: Path, run_id: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "run_id",
                "model",
                "task_id",
                "memory_hit_rate",
                "latency_ms",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "quality_score_manual",
                "practical_ux_manual",
                "notes"
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "run_id": run_id,
                    "model": r["model"],
                    "task_id": r["task_id"],
                    "memory_hit_rate": r["memory_hit_rate"],
                    "latency_ms": r["latency_ms"],
                    "prompt_tokens": r["prompt_tokens"],
                    "completion_tokens": r["completion_tokens"],
                    "total_tokens": r["total_tokens"],
                    "quality_score_manual": "",
                    "practical_ux_manual": "",
                    "notes": "",
                }
            )


def main():
    parser = argparse.ArgumentParser(description="Run pair benchmark on OpenAI-compatible API.")
    parser.add_argument("--tasks_json", required=True)
    parser.add_argument("--model_a", required=True)
    parser.add_argument("--model_b", required=True)
    parser.add_argument("--output_dir", default="results/pair_runs")
    parser.add_argument("--max_tasks", type=int, default=20)
    parser.add_argument("--base_url", default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--api_key", default=os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--run_id", default="")
    parser.add_argument("--request_interval_s", type=float, default=1.0, help="Delay between requests")
    parser.add_argument("--max_retries", type=int, default=6, help="Retries for 429 responses")
    parser.add_argument("--max_tokens", type=int, default=700, help="Max completion tokens per request")
    parser.add_argument("--validate_models", action="store_true", help="Validate model IDs before running")
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("Missing API key. Set OPENAI_API_KEY or pass --api_key.")

    tasks = load_tasks(Path(args.tasks_json))[: args.max_tasks]
    if not tasks:
        raise SystemExit("No tasks found.")

    if args.validate_models:
        try:
            available = fetch_model_ids(args.base_url, args.api_key)
        except Exception as e:
            print(f"[warn] model validation skipped: failed to fetch /models ({e})")
            available = []

        if available:
            missing = [m for m in [args.model_a, args.model_b] if m not in available]
            if missing:
                print("[error] Requested model ID not found in provider model list:")
                for m in missing:
                    print(f"  - {m}")
                    suggestions = suggest_models(m, available)
                    if suggestions:
                        print("    suggestions:")
                        for s in suggestions:
                            print(f"      * {s}")
                raise SystemExit("Model validation failed. Use a valid model ID from suggestions.")

    run_id = args.run_id or f"pair-{int(time.time())}"
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows_a = run_model(
        tasks,
        args.model_a,
        args.base_url,
        args.api_key,
        out_dir / f"{run_id}_{args.model_a}_raw.jsonl",
        request_interval_s=args.request_interval_s,
        max_retries=args.max_retries,
        max_tokens=args.max_tokens,
    )
    rows_b = run_model(
        tasks,
        args.model_b,
        args.base_url,
        args.api_key,
        out_dir / f"{run_id}_{args.model_b}_raw.jsonl",
        request_interval_s=args.request_interval_s,
        max_retries=args.max_retries,
        max_tokens=args.max_tokens,
    )
    all_rows = rows_a + rows_b
    write_csv(all_rows, out_dir / f"{run_id}_summary.csv", run_id)

    print(f"Completed run_id={run_id}")
    print(f"Wrote raw logs and summary under {out_dir}")


if __name__ == "__main__":
    main()
