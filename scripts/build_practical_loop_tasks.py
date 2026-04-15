#!/usr/bin/env python3
import argparse
import json
import random
from pathlib import Path


def load_tasks(path: Path):
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj.get("tasks", [])


def shorten(text: str, n: int):
    return " ".join((text or "").split())[:n]


def infer_error_hint(prompt: str, language: str):
    p = (prompt or "").lower()
    if language == "python":
        if "type" in p or "nullable" in p:
            return "TypeError: incompatible type assignment detected in updated path."
        return "AssertionError: expected behavior changed after patch."
    if language in ("typescript", "javascript"):
        if "type" in p or "nullable" in p:
            return "TS2322: Type 'null' is not assignable to expected type."
        return "Jest test failed: regression in updated logic."
    if language == "go":
        return "go test failed: expected key format mismatch after update."
    if language == "rust":
        return "cargo test failed: borrow checker error after quick fix."
    return "Unit test failed after update; behavior mismatch found."


def infer_second_error_hint(prompt: str, language: str):
    p = (prompt or "").lower()
    if language == "python":
        if "abi" in p or "android" in p:
            return "ImportError: ABI mismatch on fallback runtime path."
        return "RegressionError: compatibility test fails on legacy branch."
    if language in ("typescript", "javascript"):
        return "BuildError: downstream typings break in legacy consumer."
    if language == "go":
        return "go test failed: compatibility scenario broken on old API path."
    if language == "rust":
        return "cargo test failed: edge-case compatibility regression."
    return "Compatibility test failed after second patch."


def build_expectation(task, hard_mode):
    checks = task.get("checks", {})
    max_files = checks.get("max_changed_files", 5)
    if hard_mode:
        max_files = min(max_files, 3)
    base = {
        "must_have": [
            "Addresses the requested change in the prompt.",
            "Preserves backward compatibility unless explicitly overridden.",
            "Uses latest decision when memory constraints conflict.",
            "Provides repair reasoning after runtime/test feedback.",
        ],
        "must_not": [
            "Ignore runtime/test feedback and repeat initial patch unchanged.",
            "Introduce broad unrelated refactors outside the requested scope.",
            "Discard compatibility constraints without explicit justification.",
        ],
        "phase_success_criteria": {
            "phase_1_initial_request": "Proposes an initial actionable fix tied to current context.",
            "phase_2_requirement_change": "Updates plan to satisfy changed constraints with minimal scope.",
            "phase_3_runtime_feedback": "Diagnoses failure signal and identifies likely root cause.",
            "phase_4_repair_request": "Returns revised solution and explains delta vs initial approach.",
        },
        "strict_pass_conditions": {
            "must_follow_memory_constraints": True,
            "must_show_repair_reasoning": True,
            "max_changed_files": max_files,
        },
    }
    if hard_mode:
        base["must_have"].append("Handles a second feedback cycle without losing prior constraints.")
        base["phase_success_criteria"]["phase_5_secondary_feedback"] = (
            "Incorporates second failure signal while preserving earlier fixes."
        )
    return base


def to_practical_task(task, idx, hard_mode=False):
    lang = (task.get("repo_context", {}) or {}).get("language", "unknown")
    mem = task.get("session_1_memory", [])
    prompt = task.get("session_2_prompt", "")
    outcomes = task.get("expected_outcomes", [])
    checks = task.get("checks", {})

    if not prompt or len(prompt) < 20:
        return None

    base_context = shorten(prompt, 420 if hard_mode else 260)
    req1 = "Apply an initial fix for the issue described in current code context."
    req2 = "Requirement changed: keep backward compatibility and minimize touched files."
    err = infer_error_hint(prompt, lang)
    req3 = "Given the new failing test/error, revise the fix and explain what changed."
    err2 = infer_second_error_hint(prompt, lang)

    phases = {
        "phase_0_current_state": {
            "instruction": "Understand the current implementation context first.",
            "context_snippet": base_context,
        },
        "phase_1_initial_request": {
            "instruction": req1,
            "memory_from_previous_discussion": mem[:3],
        },
        "phase_2_requirement_change": {
            "instruction": req2,
            "change_reason": "Product/maintainer direction changed after initial proposal.",
        },
        "phase_3_runtime_feedback": {
            "failing_signal": err,
            "instruction": "Use this failure signal to update your patch."
        },
        "phase_4_repair_request": {
            "instruction": req3
        }
    }
    if hard_mode:
        phases["phase_2b_scope_pressure"] = {
            "instruction": "Additional constraint: touch at most 3 files and avoid schema/interface changes."
        }
        phases["phase_5_secondary_feedback"] = {
            "failing_signal": err2,
            "instruction": "A second regression surfaced. Produce a final patch plan preserving both fixes."
        }

    return {
        "id": f"PRACT-{idx:05d}",
        "title": f"Practical repair-loop task from {task.get('title', 'open history')}",
        "category": "practical-repair-loop",
        "difficulty": "hard" if hard_mode else task.get("difficulty", "medium"),
        "repo_context": task.get("repo_context", {}),
        "phases": phases,
        "expected_outcomes": outcomes + [
            "Adapts to changing requirements without losing prior constraints.",
            "Handles runtime/test feedback in the final revision."
        ] + (["Survives a second regression cycle with coherent final repair."] if hard_mode else []),
        "expectation": build_expectation(task, hard_mode),
        "checks": {
            "must_pass_tests": checks.get("must_pass_tests", True),
            "must_follow_memory_constraints": True,
            "max_changed_files": min(checks.get("max_changed_files", 5), 3) if hard_mode else checks.get("max_changed_files", 5),
            "must_show_repair_reasoning": True,
            "must_handle_second_feedback_cycle": hard_mode
        },
        "provenance": task.get("provenance", {}),
    }


def main():
    parser = argparse.ArgumentParser(description="Convert memory tasks to practical repair-loop tasks.")
    parser.add_argument("--input_json", required=True)
    parser.add_argument("--output_json", required=True)
    parser.add_argument("--max_tasks", type=int, default=80)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--hard_mode", action="store_true", help="Generate longer, stricter, multi-feedback tasks")
    args = parser.parse_args()

    tasks = load_tasks(Path(args.input_json))
    random.seed(args.seed)
    random.shuffle(tasks)
    tasks = tasks[: args.max_tasks]

    out_tasks = []
    idx = 1
    for t in tasks:
        nt = to_practical_task(t, idx, hard_mode=args.hard_mode)
        if nt:
            out_tasks.append(nt)
            idx += 1

    out = {
        "version": "0.2-practical-loop-hard" if args.hard_mode else "0.2-practical-loop",
        "description": (
            "Practical multi-turn repair-loop benchmark tasks with explicit expectations "
            "(current state -> fix -> requirement change -> error -> repair)."
        ),
        "task_count": len(out_tasks),
        "hard_mode": args.hard_mode,
        "tasks": out_tasks,
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=True, indent=2)

    print(f"input_tasks:  {len(tasks)}")
    print(f"output_tasks: {len(out_tasks)}")
    print(f"output_json:  {out_path}")


if __name__ == "__main__":
    main()
