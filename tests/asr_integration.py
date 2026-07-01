#!/usr/bin/env python
"""ASR integration smoke tests for local media routes.

The default path uses fixture ASR JSONL so the test verifies workflow plumbing
without requiring a model download. Set KW_REAL_ASR_SMOKE=1 to run a real ASR
engine against provided media paths.
"""

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
VIDEO = REPO_ROOT / "skills" / "knowledge-video-decomposer"


class AsrIntegrationFailure(Exception):
    """ASR integration assertion failure."""


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
        raise AsrIntegrationFailure(
            f"command failed: {' '.join(command)}\nstdout:\n{result['stdout']}\nstderr:\n{result['stderr']}"
        )
    return result


def parse_last_json(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = json.loads(stdout.splitlines()[-1])
    if not isinstance(payload, dict):
        raise AsrIntegrationFailure("expected JSON object output")
    return payload


def assert_true(name: str, condition: bool, details: str = "") -> None:
    if not condition:
        raise AsrIntegrationFailure(f"{name}: assertion failed{': ' + details if details else ''}")


def assert_eq(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise AsrIntegrationFailure(f"{name}: expected {expected!r}, got {actual!r}")


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def build_asr_record(
    *,
    case_id: str,
    media: Path,
    output_root: Path,
    command_result: dict[str, Any] | None,
    mode: str,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    report_path = output_root / "00_source" / "asr_pipeline_report.json"
    quality: dict[str, Any] = {}
    language_detected = None
    segments_count = None
    asr_engine = "fixture-jsonl" if mode == "fixture" else "faster-whisper"
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        quality = dict(report.get("quality") or {})
        language_detected = report.get("language")
        segments_count = report.get("segments_count")
        asr_engine = report.get("engine") or asr_engine
    transcript_path = output_root / "01_transcript" / "clean_transcript.jsonl"
    if transcript_path.is_file() and segments_count is None:
        segments_count = sum(1 for line in transcript_path.read_text(encoding="utf-8").splitlines() if line.strip())
    low_confidence_segments = quality.get("low_confidence_segments")
    if low_confidence_segments is None:
        low_confidence_segments = 0
    return {
        "case_id": case_id,
        "mode": mode,
        "input_media": str(media.resolve()),
        "duration_seconds": quality.get("duration_seconds"),
        "language_detected": language_detected,
        "segments_count": segments_count,
        "transcript_exists": transcript_path.is_file(),
        "quality_report_exists": report_path.is_file(),
        "alignment_report_exists": (output_root / "00_source" / "asr_alignment_report.json").is_file(),
        "diarization_report_exists": (output_root / "00_source" / "asr_diarization.json").is_file(),
        "low_confidence_segments": low_confidence_segments,
        "asr_engine": asr_engine,
        "status": "passed" if failure_reason is None else "failed",
        "failure_reason": failure_reason,
        "command_returncode": None if command_result is None else command_result.get("returncode"),
    }


def run_fixture_asr(media: Path, output_root: Path) -> dict[str, Any]:
    result = run_ok(
        [
            sys.executable,
            str(VIDEO / "scripts" / "asr_pipeline.py"),
            "--input-media",
            str(media),
            "--asr-jsonl",
            str(FIXTURES / "asr_sample.jsonl"),
            "--output-root",
            str(output_root),
            "--model",
            "base",
            "--language",
            "en",
        ],
        cwd=VIDEO / "scripts",
    )
    return parse_last_json(result["stdout"])


def assert_asr_outputs(output_root: Path, expected_media: Path) -> None:
    status = json.loads((output_root / "00_source" / "source_status.json").read_text(encoding="utf-8"))
    report = json.loads((output_root / "00_source" / "asr_pipeline_report.json").read_text(encoding="utf-8"))
    alignment = json.loads((output_root / "00_source" / "asr_alignment_report.json").read_text(encoding="utf-8"))
    diarization = json.loads((output_root / "00_source" / "asr_diarization.json").read_text(encoding="utf-8"))
    assert_eq("source status", status["source_status"], "source_confirmed")
    assert_eq("source classes", status["source_classes"], ["primary_audio_asr"])
    assert_true("primary material", status["primary_material_available"] is True)
    assert_eq("input media recorded", Path(report["input_media"]).resolve(), expected_media.resolve())
    assert_true("verified verbatim false", report["quality"]["verified_verbatim"] is False)
    assert_true("alignment report", "word_timestamp_coverage" in alignment)
    assert_true("diarization report", "speaker_coverage" in diarization)
    assert_true("clean transcript", (output_root / "01_transcript" / "clean_transcript.jsonl").is_file())


def test_fixture_mp3_and_mp4(base: Path, records: list[dict[str, Any]]) -> None:
    cases = [
        ("mp3", FIXTURES / "fixture.mp3"),
        ("mp4", FIXTURES / "fixture.mp4"),
    ]
    for name, media in cases:
        output_root = base / name / "10_video"
        payload = run_fixture_asr(media, output_root)
        assert_eq(f"{name} source class", payload["source_class"], "primary_audio_asr")
        assert_asr_outputs(output_root, media)
        records.append(
            build_asr_record(
                case_id=f"fixture_{name}",
                media=media,
                output_root=output_root,
                command_result=None,
                mode="fixture",
            )
        )


def test_optional_real_asr(base: Path, records: list[dict[str, Any]]) -> None:
    if os.environ.get("KW_REAL_ASR_SMOKE") != "1":
        print("SKIP optional real ASR smoke; set KW_REAL_ASR_SMOKE=1 to enable")
        return
    media_values = [os.environ.get("KW_REAL_ASR_MP3"), os.environ.get("KW_REAL_ASR_MP4")]
    media_paths = [Path(value).expanduser() for value in media_values if value]
    assert_true("real ASR media configured", bool(media_paths), "set KW_REAL_ASR_MP3 or KW_REAL_ASR_MP4")
    for media in media_paths:
        assert_true(f"real media exists {media}", media.is_file())
        output_root = base / "real" / media.stem / "10_video"
        command = [
            sys.executable,
            str(VIDEO / "scripts" / "asr_pipeline.py"),
            "--input-media",
            str(media),
            "--output-root",
            str(output_root),
            "--model",
            os.environ.get("KW_REAL_ASR_MODEL", "tiny"),
            "--language",
            os.environ.get("KW_REAL_ASR_LANGUAGE", "en"),
            "--asr-timeout-seconds",
            os.environ.get("KW_REAL_ASR_TIMEOUT_SECONDS", "120"),
        ]
        asr_python = os.environ.get("KW_REAL_ASR_PYTHON")
        if asr_python:
            command.extend(["--asr-python", asr_python])
        result = run(command, cwd=VIDEO / "scripts", timeout=300)
        failure_reason = None if result["returncode"] == 0 else (result["stderr"] or result["stdout"] or "ASR command failed")
        records.append(
            build_asr_record(
                case_id=f"real_{media.stem}",
                media=media,
                output_root=output_root,
                command_result=result,
                mode="real",
                failure_reason=failure_reason,
            )
        )
        assert_true(f"real ASR command returned for {media.name}", result["returncode"] == 0, result["stderr"])
        assert_asr_outputs(output_root, media)


def main() -> int:
    tests = [test_fixture_mp3_and_mp4, test_optional_real_asr]
    failures: list[str] = []
    output_root = REPO_ROOT / "test_outputs" / "asr_integration" / timestamp_id()
    base = output_root / "work"
    base.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    try:
        for test in tests:
            try:
                test(base, records)
                print(f"PASS {test.__name__}")
            except Exception as exc:
                failures.append(f"{test.__name__}: {exc}")
                print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    finally:
        write_json(
            output_root / "summary.json",
            {
                "mode": "real" if os.environ.get("KW_REAL_ASR_SMOKE") == "1" else "fixture",
                "real_enabled": os.environ.get("KW_REAL_ASR_SMOKE") == "1",
                "records": records,
                "failures": failures,
            },
        )
        write_json(
            output_root / "suite_summary.json",
            {
                "output_root": str(output_root.resolve()),
                "failures": failures,
                "passed": not failures,
            },
        )
    if failures:
        print("\nFailures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        print(f"summary: {output_root / 'suite_summary.json'}", file=sys.stderr)
        return 1
    print(f"ASR integration suite passed; summary: {output_root / 'suite_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
