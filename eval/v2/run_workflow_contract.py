#!/usr/bin/env python
"""Run the offline Source Gate decision track without reading gold labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parent
REPO_ROOT = EVAL_ROOT.parents[1]
INPUT_PATH = EVAL_ROOT / "inputs" / "tasks.json"
FIXTURE_PATH = EVAL_ROOT / "harness" / "workflow_fixtures.json"

sys.path.insert(0, str(REPO_ROOT))

from kw_cli import bundle, ingest  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return (result.stdout or "").strip()


def response_mode(status: dict[str, Any]) -> str:
    state = str(status.get("source_status") or "")
    if state == "source_confirmed":
        return "full_report"
    if state == "source_partial":
        return "partial_report"
    if state in {"source_blocked", "source_failed"}:
        return "failure_notice"
    return "degraded_explanation"


def validate_result(result: dict[str, Any]) -> None:
    required = {
        "task_id",
        "group",
        "pipeline_decision",
        "full_report_permission",
        "response_mode",
        "scope_status",
        "source_status",
        "elapsed_seconds",
    }
    missing = sorted(required - set(result))
    if missing:
        raise ValueError("result missing fields: " + ", ".join(missing))
    if result["pipeline_decision"] not in {"continue_full", "continue_partial", "stop_before_audit"}:
        raise ValueError(f"invalid pipeline_decision: {result['pipeline_decision']!r}")
    if not isinstance(result["full_report_permission"], bool):
        raise ValueError("full_report_permission must be boolean")


def material_path(task: dict[str, Any]) -> Path | None:
    relative = task.get("material_path")
    if relative is None:
        return None
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"invalid material_path for {task.get('task_id')}")
    path = (EVAL_ROOT / "inputs" / relative).resolve()
    try:
        path.relative_to((EVAL_ROOT / "inputs").resolve())
    except ValueError as exc:
        raise ValueError(f"material escapes input root: {relative}") from exc
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def build_bundle(task: dict[str, Any], fixture: dict[str, Any], project: Path) -> Path:
    source = material_path(task)
    artifacts: list[dict[str, Any]] = []
    if source is not None:
        destination = project / "00_acquisition" / "artifacts" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        artifacts.append(
            bundle.artifact_entry(
                bundle_root=project / "00_acquisition",
                path=destination,
                artifact_type=str(fixture["artifact_type"]),
                source_class=str(fixture["source_class"]),
                content_scope=str(fixture["content_scope"]),
                created_by="eval-v2-fixture",
            )
        )
    failures = []
    if fixture.get("failure_reason"):
        failures.append({"stage": "fixture_acquisition", "reason": str(fixture["failure_reason"])})
    manifest = bundle.make_manifest(
        project_root=project,
        input_value=str(task["request"]),
        platform="local_file" if source is not None else "web",
        acquisition_layer="eval-v2-fixture",
        active_backend="offline-fixture",
        status=str(fixture["bundle_status"]),
        artifacts=artifacts,
        failures=failures,
        next_action="ingest_bundle",
        analysis_target=str(task["target"]),
        operation=str(task["operation"]),
    )
    return bundle.write_manifest(project, manifest)


def run_task(task: dict[str, Any], fixture: dict[str, Any], output_root: Path) -> dict[str, Any]:
    task_id = str(task["task_id"])
    project = output_root / "tasks" / task_id / "project"
    if project.exists():
        shutil.rmtree(project)
    started = time.perf_counter()
    manifest_path = build_bundle(task, fixture, project)
    ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
    status = ingest.read_json(project / "10_video" / "00_source" / "source_status.json")
    result = {
        "task_id": task_id,
        "group": "Knowledge Workflow",
        "pipeline_decision": status.get("pipeline_decision"),
        "full_report_permission": bool(
            status.get("source_status") == "source_confirmed"
            and status.get("pipeline_decision") == "continue_full"
        ),
        "response_mode": response_mode(status),
        "scope_status": status.get("scope_status"),
        "source_status": status.get("source_status"),
        "status_schema_version": status.get("schema_version"),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "project_root": str(project.resolve()),
    }
    validate_result(result)
    result_path = output_root / "tasks" / task_id / "result.json"
    bundle.write_json(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    dirty_lines = git_value("status", "--porcelain").splitlines()
    dirty = bool(dirty_lines)
    if dirty and not args.allow_dirty:
        print("refusing release evaluation from a dirty worktree; use --allow-dirty for development", file=sys.stderr)
        return 2

    inputs = read_json(INPUT_PATH)
    fixtures = read_json(FIXTURE_PATH)
    tasks = inputs.get("tasks") if isinstance(inputs.get("tasks"), list) else []
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    results_path = output_root / "results.jsonl"
    results_path.write_text("", encoding="utf-8", newline="\n")
    started_at = utc_now()
    failures: list[str] = []
    for task in tasks:
        task_id = str(task.get("task_id") or "") if isinstance(task, dict) else ""
        try:
            result = run_task(task, fixtures[task_id], output_root)
        except Exception as exc:  # preserve the completed task shards before failing the run
            failures.append(f"{task_id}: {exc}")
            continue
        with results_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "protocol": inputs.get("protocol"),
        "runner": "eval-v2-workflow-contract",
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_dirty": dirty,
        "releasable": not dirty and not failures,
        "python": sys.version,
        "platform": platform.platform(),
        "input_sha256": sha256(INPUT_PATH),
        "fixture_map_sha256": sha256(FIXTURE_PATH),
        "task_count": len(tasks),
        "completed_tasks": len(tasks) - len(failures),
        "timeout_seconds_per_task": 0,
        "retry_limit": 0,
        "random_seed": 0,
        "network_allowed": False,
        "started_at": started_at,
        "finished_at": utc_now(),
        "failures": failures,
    }
    bundle.write_json(output_root / "run_manifest.json", manifest)
    print(results_path)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
