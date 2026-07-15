#!/usr/bin/env python
"""Score structured gate dimensions after a v2 runner has closed outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parent
GOLD_PATH = EVAL_ROOT / "gold" / "decisions.json"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_results(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict) or not value.get("task_id"):
            raise ValueError("every result line must contain a task_id")
        rows[str(value["task_id"])] = value
    return rows


def upper_bound_zero_errors(n: int, alpha: float = 0.05) -> float | None:
    return None if n <= 0 else 1 - alpha ** (1 / n)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    gold_document = read_json(GOLD_PATH)
    gold = gold_document.get("tasks") if isinstance(gold_document.get("tasks"), dict) else {}
    results_path = args.results.resolve()
    results = read_results(results_path)
    manifest_path = results_path.parent / "run_manifest.json"
    run_manifest = read_json(manifest_path) if manifest_path.is_file() else {}
    dimensions = ("pipeline_decision", "full_report_permission", "response_mode", "scope_status")
    task_rows: list[dict[str, Any]] = []
    false_releases = 0
    insufficient = 0
    for task_id, expected in gold.items():
        actual = results.get(task_id) or {}
        dimension_scores = {key: actual.get(key) == expected.get(key) for key in dimensions}
        expected_full = expected.get("full_report_permission") is True
        actual_full = actual.get("full_report_permission") is True
        false_release = not expected_full and actual_full
        if not expected_full:
            insufficient += 1
            false_releases += int(false_release)
        task_rows.append(
            {
                "task_id": task_id,
                "found": bool(actual),
                "expected": expected,
                "actual": {key: actual.get(key) for key in dimensions},
                "dimension_scores": dimension_scores,
                "all_dimensions_correct": bool(actual) and all(dimension_scores.values()),
                "false_full_report_release": false_release,
            }
        )

    total = len(task_rows)
    completed = sum(bool(row["found"]) for row in task_rows)
    all_correct = all(bool(row["all_dimensions_correct"]) for row in task_rows)
    per_dimension = {
        key: sum(bool(row["dimension_scores"][key]) for row in task_rows) / total if total else None
        for key in dimensions
    }
    zero_upper = upper_bound_zero_errors(insufficient) if false_releases == 0 else None
    release_claim_allowed = (
        run_manifest.get("releasable") is True
        and insufficient >= 60
        and completed == total
        and all_correct
        and false_releases == 0
    )
    summary = {
        "protocol": gold_document.get("protocol"),
        "gold_sha256": sha256(GOLD_PATH),
        "results_path": str(results_path),
        "run_manifest_path": str(manifest_path) if manifest_path.is_file() else None,
        "run_manifest_sha256": sha256(manifest_path) if manifest_path.is_file() else None,
        "run_releasable": run_manifest.get("releasable") is True,
        "task_count": total,
        "results_found": len(results),
        "all_dimensions_correct_rate": (
            sum(bool(row["all_dimensions_correct"]) for row in task_rows) / total if total else None
        ),
        "per_dimension_accuracy": per_dimension,
        "insufficient_or_nonfull_cases": insufficient,
        "false_full_report_releases": false_releases,
        "false_full_report_release_rate": false_releases / insufficient if insufficient else None,
        "zero_error_one_sided_95_upper_bound": zero_upper,
        "release_claim_allowed": release_claim_allowed,
        "task_rows": task_rows,
        "caveats": [
            "This eight-task track validates the harness and contract mapping; it is not a release-grade performance claim.",
            "A release claim also requires a clean, complete, releasable run with every structured dimension correct.",
            "A zero-error observation with this denominator has a wide one-sided 95% upper bound.",
            "Ordinary-Agent, retrieval, ranking, fidelity, human review, and learning-effect tracks are not included.",
        ],
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    lines = [
        "# Evaluation v2 Contract Smoke",
        "",
        f"- Tasks: `{total}`",
        f"- Results found: `{len(results)}`",
        f"- All dimensions correct: `{summary['all_dimensions_correct_rate']:.1%}`",
        f"- False full-report releases: `{false_releases}/{insufficient}`",
        f"- One-sided 95% upper bound when zero errors: `{zero_upper:.1%}`" if zero_upper is not None else "- One-sided 95% upper bound: `n/a`",
        f"- Run marked releasable: `{summary['run_releasable']}`",
        f"- Release claim allowed: `{summary['release_claim_allowed']}`",
        "",
        "This is a harness acceptance smoke, not a product superiority claim.",
        "",
    ]
    (args.output_root / "summary.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(args.output_root / "summary.json")
    return 0 if len(results) == total and all(row["all_dimensions_correct"] for row in task_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
