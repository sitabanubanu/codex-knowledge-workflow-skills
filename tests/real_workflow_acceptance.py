#!/usr/bin/env python
"""Acceptance smoke for the local transcript-to-final-report workflow."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"


class AcceptanceFailure(Exception):
    """Workflow acceptance assertion failure."""


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run(command: list[str], *, cwd: Path, timeout: int = 240) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def run_ok(command: list[str], *, cwd: Path, timeout: int = 240) -> dict[str, Any]:
    result = run(command, cwd=cwd, timeout=timeout)
    if result["returncode"] != 0:
        raise AcceptanceFailure(
            f"command failed: {' '.join(command)}\nstdout:\n{result['stdout']}\nstderr:\n{result['stderr']}"
        )
    return result


def parse_last_json(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = json.loads(stdout.splitlines()[-1])
    if not isinstance(payload, dict):
        raise AcceptanceFailure("expected JSON object output")
    return payload


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_true(name: str, condition: bool, details: str = "") -> None:
    if not condition:
        raise AcceptanceFailure(f"{name}: assertion failed{': ' + details if details else ''}")


def main() -> int:
    output_root = REPO_ROOT / "test_outputs" / "real_workflow_acceptance" / timestamp_id()
    project_root = output_root / "project"
    failures: list[str] = []
    summary: dict[str, Any] = {
        "output_root": str(output_root.resolve()),
        "project_root": str(project_root.resolve()),
        "input": str((FIXTURES / "transcript_sample.txt").resolve()),
        "route": "local_transcript_to_final_report",
        "passed": False,
        "failures": failures,
    }
    try:
        product_result = run_ok(
            [
                sys.executable,
                str(REPO_ROOT / "kw.py"),
                "run",
                "--input",
                str(FIXTURES / "transcript_sample.txt"),
                "--project-root",
                str(project_root),
                "--target",
                "video_content",
                "--operation",
                "extract_transcript",
                "--mode",
                "audit",
                "--language",
                "en",
                "--document-goal",
                "Write an auditable final report from a confirmed transcript.",
                "--final-language",
                "en",
            ],
            cwd=REPO_ROOT,
            timeout=240,
        )
        summary["product_run"] = product_result
        summary["result_index_writer"] = read_json(project_root / "logs" / "result_index.json")

        required_files = [
            project_root / "result_index.md",
            project_root / "logs" / "run_identity.json",
            project_root / "00_acquisition" / "manifest.json",
            project_root / "10_video" / "00_source" / "source_status.json",
            project_root / "10_video" / "00_source" / "gate_receipt.json",
            project_root / "10_video" / "01_transcript" / "clean_transcript.jsonl",
            project_root / "10_video" / "02_segments" / "argument_segments.json",
            project_root / "10_video" / "03_inventory" / "claims.json",
            project_root / "10_video" / "04_logic" / "logic_graph.json",
            project_root / "10_video" / "05_gap_check" / "evidence_audit.json",
            project_root / "10_video" / "video_analysis_pack.md",
            project_root / "10_video" / "analysis_receipt.json",
            project_root / "20_document" / "composer_intake.json",
            project_root / "20_document" / "claim_map.json",
            project_root / "20_document" / "composer_receipt.json",
            project_root / "20_document" / "quality_gate.json",
            project_root / "20_document" / "final_report.md",
            project_root / "20_document" / "final_report_receipt.json",
        ]
        for path in required_files:
            assert_true(f"required file {path.name}", path.is_file(), str(path))

        source_status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
        quality_gate = read_json(project_root / "20_document" / "quality_gate.json")
        final_text = (project_root / "20_document" / "final_report.md").read_text(encoding="utf-8")
        assert_true("source confirmed", source_status.get("source_status") == "source_confirmed")
        assert_true("primary material", source_status.get("primary_material_available") is True)
        assert_true("final approved", quality_gate.get("approved_for_final_report") is True)
        assert_true("result index success", summary["result_index_writer"].get("status") == "success")
        assert_true("gate provenance current", summary["result_index_writer"].get("gate_provenance_current") is True)
        assert_true("analysis provenance current", summary["result_index_writer"].get("analysis_provenance_current") is True)
        assert_true("final provenance current", summary["result_index_writer"].get("final_report_provenance_current") is True)
        assert_true("source section", "## Source" in final_text)
        assert_true("inference section", "## Inference" in final_text)
        assert_true("extension section", "## Extension" in final_text)

        summary.update(
            {
                "source_status": source_status.get("source_status"),
                "analysis_pack_exists": (project_root / "10_video" / "video_analysis_pack.md").is_file(),
                "final_report_exists": (project_root / "20_document" / "final_report.md").is_file(),
                "quality_gate_approved": quality_gate.get("approved_for_final_report"),
                "passed": True,
            }
        )
    except Exception as exc:
        failures.append(str(exc))
        print(f"FAIL real workflow acceptance: {exc}", file=sys.stderr)
    finally:
        write_json(output_root / "summary.json", summary)

    if failures:
        print(f"summary: {output_root / 'summary.json'}", file=sys.stderr)
        return 1
    print(f"real workflow acceptance passed; summary: {output_root / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
