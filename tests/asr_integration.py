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
import tempfile
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


def test_fixture_mp3_and_mp4(base: Path) -> None:
    cases = [
        ("mp3", FIXTURES / "fixture.mp3"),
        ("mp4", FIXTURES / "fixture.mp4"),
    ]
    for name, media in cases:
        output_root = base / name / "10_video"
        payload = run_fixture_asr(media, output_root)
        assert_eq(f"{name} source class", payload["source_class"], "primary_audio_asr")
        assert_asr_outputs(output_root, media)


def test_optional_real_asr(base: Path) -> None:
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
        assert_true(f"real ASR command returned for {media.name}", result["returncode"] == 0, result["stderr"])
        assert_asr_outputs(output_root, media)


def main() -> int:
    tests = [test_fixture_mp3_and_mp4, test_optional_real_asr]
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="kw-asr-integration-") as tmp:
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
    print("ASR integration suite passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
