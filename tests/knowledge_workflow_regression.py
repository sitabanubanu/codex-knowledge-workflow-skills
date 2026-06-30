#!/usr/bin/env python
"""Regression tests for the knowledge workflow skill chain.

The suite is intentionally offline. It verifies the current productized paths:
local transcript end-to-end, ASR resume, Chrome probe gating, document composer
gating, and blocked-output validation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
VIDEO = REPO_ROOT / "skills" / "knowledge-video-decomposer"
CONSOLE = REPO_ROOT / "skills" / "knowledge-workflow-console"
DOCUMENT = REPO_ROOT / "skills" / "knowledge-document-composer"


class RegressionFailure(Exception):
    """Regression assertion failure."""


def run(command: list[str], *, cwd: Path, timeout: int = 180) -> dict[str, Any]:
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


def run_ok(command: list[str], *, cwd: Path, timeout: int = 180) -> dict[str, Any]:
    result = run(command, cwd=cwd, timeout=timeout)
    if result["returncode"] != 0:
        raise RegressionFailure(
            f"command failed: {' '.join(command)}\nstdout:\n{result['stdout']}\nstderr:\n{result['stderr']}"
        )
    return result


def parse_last_json(stdout: str) -> dict[str, Any]:
    if not stdout:
        return {}
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = json.loads(stdout.splitlines()[-1])
    if not isinstance(payload, dict):
        raise RegressionFailure("expected JSON object output")
    return payload


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def assert_true(name: str, condition: bool, details: str = "") -> None:
    if not condition:
        raise RegressionFailure(f"{name}: assertion failed{': ' + details if details else ''}")


def assert_eq(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise RegressionFailure(f"{name}: expected {expected!r}, got {actual!r}")


def test_local_transcript_e2e(base: Path) -> None:
    transcript = base / "local_e2e" / "fixture.txt"
    project_root = base / "local_e2e" / "project"
    write_text(
        transcript,
        "\n\n".join(
            [
                "Source Gate means confirmed primary material.",
                "For example, metadata alone cannot support speaker logic.",
                "Therefore we must preserve transcript evidence before writing reports.",
                "This creates a workflow where claims remain tied to their source.",
            ]
        )
        + "\n",
    )
    result = run_ok(
        [
            sys.executable,
            str(CONSOLE / "scripts" / "end_to_end_runner.py"),
            "--input-transcript",
            str(transcript),
            "--project-root",
            str(project_root),
            "--language",
            "en",
            "--document-goal",
            "Write an auditable report",
            "--final-language",
            "zh-CN",
        ],
        cwd=CONSOLE / "scripts",
    )
    payload = parse_last_json(result["stdout"])
    assert_eq("e2e steps", len(payload["steps"]), 7)
    assert_true("pack exists", (project_root / "10_video" / "video_analysis_pack.md").is_file())
    assert_true("composer intake exists", (project_root / "20_document" / "composer_intake.json").is_file())
    assert_true("final report not written", not (project_root / "20_document" / "final_report.md").exists())


def test_asr_resume(base: Path) -> None:
    root = base / "asr_resume" / "10_video"
    media = base / "asr_resume" / "fixture.mp3"
    asr_jsonl = base / "asr_resume" / "asr.jsonl"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"placeholder media")
    rows = [
        {"id": "t0001", "start": 0.0, "end": 3.0, "text": "ASR source text.", "source": "ASR", "language": "en"},
        {"id": "t0002", "start": 3.0, "end": 6.0, "text": "Evidence stays linked.", "source": "ASR", "language": "en"},
    ]
    write_text(asr_jsonl, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    result = run_ok(
        [
            sys.executable,
            str(VIDEO / "scripts" / "asr_pipeline.py"),
            "--input-media",
            str(media),
            "--asr-jsonl",
            str(asr_jsonl),
            "--output-root",
            str(root),
            "--model",
            "base",
            "--language",
            "en",
        ],
        cwd=VIDEO / "scripts",
    )
    payload = parse_last_json(result["stdout"])
    assert_eq("asr source class", payload["source_class"], "primary_audio_asr")
    status = json.loads((root / "00_source" / "source_status.json").read_text(encoding="utf-8"))
    assert_eq("status class", status["source_classes"], ["primary_audio_asr"])
    assert_true("clean transcript", (root / "01_transcript" / "clean_transcript.jsonl").is_file())


def test_chrome_url_only_gate(base: Path) -> None:
    input_json = base / "chrome_url_only" / "input.json"
    output_root = base / "chrome_url_only" / "10_video"
    write_json(
        input_json,
        {
            "source_url": "https://example.invalid/video",
            "visible_transcript_status": "not_visible",
            "page_state_observed": "opened",
            "layers": [
                {
                    "layer": "playwright_evaluate",
                    "executed": True,
                    "result": "success",
                    "public_urls": ["https://cdn.example.invalid/captions.vtt"],
                    "confirmed_public_downloadable": True,
                }
            ],
        },
    )
    result = run_ok(
        [
            sys.executable,
            str(VIDEO / "scripts" / "chrome_media_probe.py"),
            "--input-json",
            str(input_json),
            "--output-root",
            str(output_root),
        ],
        cwd=VIDEO / "scripts",
    )
    payload = parse_last_json(result["stdout"])
    assert_eq("url-only signal", payload["suggested_acquisition_signal"], "browser_derived_media_url_found")
    assert_eq("url-only not confirmed", payload["suggested_source_status"], "source_failed")
    assert_true("url-only not exported", payload["browser_derived_media_exported"] is False)


def test_document_composer_blocks_bad_primary_flag(base: Path) -> None:
    # Reuse the document runner self-test because it explicitly covers malformed
    # truthy primary_material_available and audit errors.
    run_ok(
        [sys.executable, str(DOCUMENT / "scripts" / "document_composer_runner.py"), "--self-test"],
        cwd=DOCUMENT / "scripts",
    )


def test_blocked_validator(base: Path) -> None:
    root = base / "blocked_validator"
    status = {
        "source_status": "secondary_only",
        "can_enter_full_decomposition": False,
        "can_enter_document_composer": True,
        "allowed_report_type": "degraded_source_report",
        "source_classes": ["firecrawl_context"],
        "primary_material_available": False,
        "status_reason": "regression fixture",
        "failed_probes": [],
        "next_step": "request_primary_transcript_audio_or_authorized_page_access",
    }
    write_json(root / "00_source" / "source_status.json", status)
    write_text(root / "video_analysis_pack.md", "# Video Analysis Pack\n\nFull source-confirmed analysis.\n")
    result = run(
        [
            sys.executable,
            str(VIDEO / "scripts" / "artifact_validator.py"),
            "--artifact-root",
            str(root),
            "--source-status-json",
            str(root / "00_source" / "source_status.json"),
        ],
        cwd=VIDEO / "scripts",
    )
    assert_true("validator should fail blocked full pack", result["returncode"] != 0)


def main() -> int:
    tests = [
        test_local_transcript_e2e,
        test_asr_resume,
        test_chrome_url_only_gate,
        test_document_composer_blocks_bad_primary_flag,
        test_blocked_validator,
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="knowledge-regression-") as tmp:
        base = Path(tmp)
        for test in tests:
            try:
                test(base)
                print(f"PASS {test.__name__}")
            except Exception as exc:
                failures.append(f"{test.__name__}: {exc}")
                print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print("\nFailures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("regression suite passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
