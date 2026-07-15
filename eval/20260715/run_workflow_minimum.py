#!/usr/bin/env python
"""Run the frozen 20-task minimum set through the real Knowledge Workflow.

This evaluator only creates evaluation outputs under test_outputs. It does not
modify product code or fabricate an acquisition result. Bundle cases are
constructed with the same Bundle v2 and source-gate functions used by kw.py so
that insufficient-material decisions are exercised without network access.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).resolve().parent / "manifest.json"
BASE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "transcript_sample.txt"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def run_command(command: list[str], *, timeout: int = 360) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"},
        )
        return {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "timeout": True,
        }


def actual_action(status: dict[str, Any], *, final_report: Path) -> str:
    source_status = str(status.get("source_status") or "")
    if source_status == "source_confirmed":
        return "full_analysis_allowed"
    if source_status == "source_partial":
        if final_report.is_file() and "partial scope" not in final_report.read_text(encoding="utf-8", errors="replace").lower():
            return "degraded_explanation_only"
        return "partial_analysis_only"
    if source_status in {"source_blocked", "source_failed"}:
        return "must_stop"
    reason = str(status.get("status_reason") or "").lower()
    if "does not satisfy analysis target" in reason or str(status.get("acquisition_bundle_status")) in {"unsupported", "blocked", "failed"}:
        return "must_stop"
    return "degraded_explanation_only"


def make_bundle_case(task: dict[str, Any], project_root: Path) -> Path:
    from kw_cli import bundle

    case = str(task["case"])
    acquisition_root = project_root / "00_acquisition"
    artifacts_root = acquisition_root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    source_path = artifacts_root / "material.txt"
    source_path.write_text(BASE_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")

    artifact: dict[str, Any] | None = None
    status = "failed"
    platform = "youtube"
    source_class = "unknown"
    artifact_type = "unknown"
    content_scope = "unknown"
    coverage = "unknown"

    if case == "metadata_only_video":
        status, source_class, artifact_type, content_scope = "metadata_only", "metadata_only", "metadata", "metadata"
    elif case == "search_result_for_article":
        status, source_class, artifact_type, content_scope, platform = "secondary_only", "secondary", "search_result", "search_result", "search"
    elif case == "partial_video_transcript":
        status, source_class, artifact_type, content_scope, coverage = "partial_material_acquired", "partial_primary", "transcript", "video_transcript", "partial"
    elif case == "secondary_article_context":
        status, source_class, artifact_type, content_scope, platform = "secondary_only", "secondary", "page_text", "article_body", "web"
    elif case == "media_pending_asr":
        status, source_class, artifact_type, content_scope = "material_acquired", "primary", "audio", "media"
    elif case == "article_body_for_video":
        status, source_class, artifact_type, content_scope, platform = "material_acquired", "primary", "page_text", "article_body", "web"
    elif case == "video_transcript_for_article":
        status, source_class, artifact_type, content_scope = "material_acquired", "primary", "transcript", "video_transcript"
    elif case == "social_post_for_video":
        status, source_class, artifact_type, content_scope, platform = "material_acquired", "primary", "page_text", "social_post_text", "x"
    elif case == "unsupported_route":
        status = "unsupported"
    elif case == "failed_acquisition":
        status = "failed"
    else:
        raise ValueError(f"unknown bundle case: {case}")

    run_id = bundle.run_context.new_id("run")
    source_id = f"eval-{task['id'].lower()}"
    if artifact_type != "unknown":
        artifact = bundle.artifact_entry(
            bundle_root=acquisition_root,
            path=source_path,
            artifact_type=artifact_type,
            source_class=source_class,
            content_scope=content_scope,
            coverage=coverage,
            run_id=run_id,
            source_id=source_id,
            description=f"Frozen evaluation case: {case}",
            created_by="run_workflow_minimum",
        )

    manifest = bundle.make_manifest(
        project_root=project_root,
        input_value=f"evaluation:{task['id']}",
        source_url=f"https://evaluation.invalid/{task['id']}",
        source_id=source_id,
        platform=platform,
        acquisition_layer="evaluation_fixture",
        active_backend="evaluation_fixture",
        status=status,
        artifacts=[artifact] if artifact else [],
        metadata={"evaluation_case": case},
        limits=["Evaluation fixture; no network acquisition performed."],
        failures=[{"stage": "fixture", "reason": f"Frozen case: {case}"}] if status in {"failed", "blocked"} else [],
        next_action="ingest_bundle",
        run_id=run_id,
        analysis_target=task["target"],
        operation=task["operation"],
    )
    manifest_path = bundle.write_manifest(project_root, manifest)
    validation = bundle.validate_manifest(manifest_path)
    if not validation["valid"]:
        raise RuntimeError(f"fixture manifest invalid: {validation['errors']}")
    return manifest_path


def run_task(task: dict[str, Any], output_root: Path) -> dict[str, Any]:
    task_root = output_root / task["id"]
    if task_root.exists():
        shutil.rmtree(task_root)
    task_root.mkdir(parents=True, exist_ok=True)
    project_root = task_root / "project"
    started_at = utc_now()
    commands: list[dict[str, Any]] = []

    if task["route"] == "local_run":
        command = [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "run",
            "--input",
            str(REPO_ROOT / task["input"]),
            "--project-root",
            str(project_root),
            "--target",
            task["target"],
            "--operation",
            task["operation"],
            "--mode",
            "audit",
            "--document-goal",
            task["learning_goal"],
            "--final-language",
            "zh-CN" if task["id"] == "KW-07" else "en",
        ]
        commands.append(run_command(command))
    elif task["route"] == "local_run_asr_resume":
        command = [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "run",
            "--input",
            str(REPO_ROOT / task["input"]),
            "--project-root",
            str(project_root),
            "--target",
            task["target"],
            "--operation",
            task["operation"],
            "--mode",
            "audit",
            "--language",
            "en",
            "--asr-jsonl",
            str(REPO_ROOT / task["asr_jsonl"]),
            "--document-goal",
            task["learning_goal"],
            "--final-language",
            "en",
        ]
        commands.append(run_command(command, timeout=420))
    elif task["route"] == "browser_export_web":
        command = [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "browser-import",
            "--input-file",
            str(REPO_ROOT / task["input"]),
            "--source-url",
            f"https://evaluation.invalid/{task['id']}",
            "--platform",
            "web",
            "--project-root",
            str(project_root),
            "--target",
            task["target"],
            "--operation",
            task["operation"],
            "--browser-host",
            "chrome",
        ]
        commands.append(run_command(command))
        if commands[-1].get("returncode") == 0:
            manifest_path = project_root / "00_acquisition" / "manifest.json"
            commands.append(run_command([sys.executable, str(REPO_ROOT / "kw.py"), "ingest", "--bundle", str(manifest_path), "--project-root", str(project_root)]))
            status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
            if status.get("source_status") in {"source_confirmed", "source_partial"}:
                commands.append(run_command([
                    sys.executable,
                    str(REPO_ROOT / "kw.py"),
                    "audit",
                    "--project-root",
                    str(project_root),
                    "--document-goal",
                    task["learning_goal"],
                    "--final-language",
                    "zh-CN" if task["id"] == "KW-07" else "en",
                    "--audience",
                    "evaluation reviewer",
                ], timeout=420))
                commands.append(run_command([sys.executable, str(REPO_ROOT / "kw.py"), "compose", "--project-root", str(project_root)], timeout=420))
    elif task["route"] == "bundle_case":
        try:
            manifest_path = make_bundle_case(task, project_root)
            commands.append(run_command([sys.executable, str(REPO_ROOT / "kw.py"), "ingest", "--bundle", str(manifest_path), "--project-root", str(project_root)]))
            status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
            if status.get("source_status") in {"source_confirmed", "source_partial"}:
                commands.append(run_command([
                    sys.executable,
                    str(REPO_ROOT / "kw.py"),
                    "audit",
                    "--project-root",
                    str(project_root),
                    "--document-goal",
                    task["learning_goal"],
                    "--final-language",
                    "en",
                    "--audience",
                    "evaluation reviewer",
                ], timeout=420))
                commands.append(run_command([sys.executable, str(REPO_ROOT / "kw.py"), "compose", "--project-root", str(project_root)], timeout=420))
        except Exception as exc:
            commands.append({"command": ["fixture"], "returncode": 1, "stdout": "", "stderr": str(exc), "elapsed_seconds": 0.0})
    else:
        raise ValueError(f"unsupported route: {task['route']}")

    finished_at = utc_now()
    status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
    final_report = project_root / "20_document" / "final_report.md"
    quality_gate = read_json(project_root / "20_document" / "quality_gate.json")
    claim_audit = read_json(project_root / "10_video" / "05_gap_check" / "claim_source_audit.json")
    evidence_audit = read_json(project_root / "10_video" / "05_gap_check" / "evidence_audit.json")
    result = {
        "task_id": task["id"],
        "expected_action": task["expected_action"],
        "started_at": started_at,
        "finished_at": finished_at,
        "commands": commands,
        "project_root": str(project_root.resolve()),
        "source_status": status,
        "actual_action": actual_action(status, final_report=final_report),
        "final_report_exists": final_report.is_file(),
        "final_report_approved": quality_gate.get("approved_for_final_report") is True,
        "report_scope": quality_gate.get("report_scope", ""),
        "claim_audit_summary": claim_audit.get("summary", {}),
        "evidence_audit_summary": {
            "pack_gate": evidence_audit.get("pack_gate", {}),
            "severity_counts": evidence_audit.get("severity_counts", {}),
        },
    }
    write_json(task_root / "result.json", result)
    for index, command in enumerate(commands, start=1):
        write_json(task_root / f"command_{index:02d}.json", {key: value for key, value in command.items() if key not in {"stdout", "stderr"}})
        (task_root / f"command_{index:02d}.stdout.txt").write_text(str(command.get("stdout") or ""), encoding="utf-8")
        (task_root / f"command_{index:02d}.stderr.txt").write_text(str(command.get("stderr") or ""), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()
    manifest = read_json(args.manifest)
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for task in manifest.get("tasks") or []:
        results.append(run_task(task, output_root))
    with (output_root / "results.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    write_json(output_root / "run_summary.json", {
        "evaluation_id": manifest.get("evaluation_id"),
        "project_version": manifest.get("project_version"),
        "task_count": len(results),
        "results_path": str((output_root / "results.jsonl").resolve()),
        "completed_processes": sum(1 for result in results if result.get("source_status")),
    })
    print(output_root / "run_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
