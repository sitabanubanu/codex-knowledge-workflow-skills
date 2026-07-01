#!/usr/bin/env python
"""Smoke tests for real-world knowledge workflow routes.

Default mode is offline and deterministic. Live platform probes are opt-in via
KW_LIVE_PLATFORM_SMOKE=1 because platform availability, cookies, and bot checks
are intentionally unstable.
"""

from __future__ import annotations

import argparse
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
DOCUMENT = REPO_ROOT / "skills" / "knowledge-document-composer"


class SmokeFailure(Exception):
    """Smoke-test assertion failure."""


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
        raise SmokeFailure(
            f"command failed: {' '.join(command)}\nstdout:\n{result['stdout']}\nstderr:\n{result['stderr']}"
        )
    return result


def parse_last_json(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = json.loads(stdout.splitlines()[-1])
    if not isinstance(payload, dict):
        raise SmokeFailure("expected JSON object output")
    return payload


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def assert_true(name: str, condition: bool, details: str = "") -> None:
    if not condition:
        raise SmokeFailure(f"{name}: assertion failed{': ' + details if details else ''}")


def assert_eq(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise SmokeFailure(f"{name}: expected {expected!r}, got {actual!r}")


def test_transcript_and_subtitle_fixtures(base: Path) -> None:
    cases = [
        ("txt transcript", FIXTURES / "transcript_sample.txt"),
        ("srt subtitle", FIXTURES / "subtitle_sample.srt"),
        ("vtt subtitle", FIXTURES / "subtitle_sample.vtt"),
    ]
    for name, fixture in cases:
        output = base / "normalizer" / fixture.suffix.strip(".") / "10_video"
        result = run_ok(
            [
                sys.executable,
                str(VIDEO / "scripts" / "transcript_normalizer.py"),
                "--input",
                str(fixture),
                "--output-root",
                str(output),
                "--language",
                "en",
            ],
            cwd=VIDEO / "scripts",
        )
        payload = parse_last_json(result["stdout"])
        assert_eq(f"{name} source status", payload["source_status"], "source_confirmed")
        assert_true(f"{name} clean transcript", (output / "01_transcript" / "clean_transcript.jsonl").is_file())
        status = json.loads((output / "00_source" / "source_status.json").read_text(encoding="utf-8"))
        assert_eq(f"{name} primary", status["primary_material_available"], True)


def test_chrome_metadata_only_gate(base: Path) -> None:
    input_json = base / "chrome_metadata_only" / "input.json"
    output = base / "chrome_metadata_only" / "10_video"
    write_json(
        input_json,
        {
            "source_url": "https://example.invalid/video",
            "visible_transcript_status": "not_visible",
            "page_state_observed": "opened",
            "metadata": {"title": "Metadata only fixture", "description": "No primary material."},
            "layers": [
                {"layer": "visible_transcript", "executed": True, "result": "not_found"},
                {"layer": "pageAssets_list", "executed": True, "result": "not_found"},
                {"layer": "playwright_evaluate", "executed": True, "result": "not_found"},
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
            str(output),
        ],
        cwd=VIDEO / "scripts",
    )
    payload = parse_last_json(result["stdout"])
    assert_true("metadata-only not confirmed", payload["suggested_source_status"] != "source_confirmed")
    assert_true("metadata-only no transcript dir", not (output / "01_transcript").exists())
    assert_true("metadata-only no pack", not (output / "video_analysis_pack.md").exists())


def test_platform_blocked_fixtures(base: Path) -> None:
    cases = [
        ("x blocked", "https://x.com/example/status/123", "login_required"),
        ("xiaohongshu blocked", "https://www.xiaohongshu.com/explore/fixture", "request_blocked"),
        ("douyin blocked", "https://www.douyin.com/jingxuan?modal_id=fixture", "captcha"),
    ]
    for name, url, signal in cases:
        output = base / "blocked" / name.replace(" ", "_") / "source_status.json"
        run_ok(
            [
                sys.executable,
                str(VIDEO / "scripts" / "acquisition_probe.py"),
                "--url",
                url,
                "--source-type",
                "platform_url",
                "--probe",
                "yt-dlp,Chrome",
                "--signal",
                signal,
                "--output",
                str(output),
            ],
            cwd=VIDEO / "scripts",
        )
        payload = json.loads(output.read_text(encoding="utf-8"))
        assert_eq(f"{name} status", payload["source_status"], "source_blocked")
        assert_eq(f"{name} full gate", payload["can_enter_full_decomposition"], False)
        assert_true(f"{name} output written", output.is_file())


def test_youtube_fixture_cases(base: Path) -> None:
    cases = json.loads((FIXTURES / "platform_cases.json").read_text(encoding="utf-8"))["offline_cases"]
    by_name = {case["name"]: case for case in cases}
    subtitle_case = by_name["youtube_with_subtitles_fixture"]
    subtitle_root = base / "youtube_fixtures" / "with_subtitles" / "10_video"
    result = run_ok(
        [
            sys.executable,
            str(VIDEO / "scripts" / "transcript_normalizer.py"),
            "--input",
            str(FIXTURES / "subtitle_sample.vtt"),
            "--output-root",
            str(subtitle_root),
            "--language",
            "en",
        ],
        cwd=VIDEO / "scripts",
    )
    payload = parse_last_json(result["stdout"])
    assert_eq("youtube subtitles fixture expected route", subtitle_case["expected_route"], "subtitle_acquired")
    assert_eq("youtube subtitles confirmed", payload["source_status"], "source_confirmed")
    assert_true("youtube subtitles transcript", (subtitle_root / "01_transcript" / "clean_transcript.jsonl").is_file())

    no_subtitle_case = by_name["youtube_without_subtitles_fixture"]
    no_subtitle_status = base / "youtube_fixtures" / "without_subtitles" / "source_status.json"
    run_ok(
        [
            sys.executable,
            str(VIDEO / "scripts" / "acquisition_probe.py"),
            "--url",
            no_subtitle_case["url"],
            "--source-type",
            "platform_url",
            "--probe",
            "yt-dlp",
            "--signal",
            "metadata_only,no_subtitles",
            "--output",
            str(no_subtitle_status),
        ],
        cwd=VIDEO / "scripts",
    )
    no_subtitle_payload = json.loads(no_subtitle_status.read_text(encoding="utf-8"))
    assert_eq("youtube no subtitles fixture expected route", no_subtitle_case["expected_route"], "metadata_only_or_audio_required")
    assert_true("youtube no subtitles not full", no_subtitle_payload["can_enter_full_decomposition"] is False)
    assert_true("youtube no subtitles no primary", no_subtitle_payload["primary_material_available"] is False)


def test_final_report_audit(base: Path) -> None:
    sys.path.insert(0, str(DOCUMENT / "scripts"))
    from document_composer_runner import run_document_composer, write_video_fixture
    from final_report_writer import run_final_report_writer

    video = base / "final_report" / "10_video"
    doc = base / "final_report" / "20_document"
    write_video_fixture(video)
    run_document_composer(
        argparse.Namespace(
            video_root=video,
            document_root=doc,
            document_goal="Write an auditable final report",
            final_language="en",
            audience="workflow reviewer",
        )
    )
    summary = run_final_report_writer(argparse.Namespace(document_root=doc))
    assert_eq("final approved", summary["approved_for_final_report"], True)
    assert_true("final report", (doc / "final_report.md").is_file())
    gate = json.loads((doc / "quality_gate.json").read_text(encoding="utf-8"))
    gate_names = {item.get("gate") for item in gate.get("gates", [])}
    required = {
        "Evidence",
        "Example Completeness",
        "Language Logic",
        "Argument Continuity",
        "Source / Inference / Extension",
        "User Fit",
        "Gap",
        "No-Empty-Abstraction",
        "Template Coverage",
        "Final Approval",
    }
    assert_true("final audit gates", required.issubset(gate_names), f"missing {sorted(required - gate_names)}")

    blocked_doc = base / "final_report_blocked" / "20_document"
    blocked_doc.mkdir(parents=True)
    write_json(
        blocked_doc / "composer_intake.json",
        {
            "runner": "stage8-smoke",
            "document_root": str(blocked_doc.resolve()),
            "source_status": "secondary_only",
            "composer_decision": "degraded",
        },
    )
    write_json(blocked_doc / "claim_map.json", {"claims": []})
    write_text(
        blocked_doc / "revised_report.md",
        "# Degraded Candidate\n\n## Source\n\nNo primary source.\n\n## Inference\n\nNone.\n\n## Extension\n\nNone.\n",
    )
    from final_report_auditor import audit_report, write_audit_outputs
    from final_report_writer import FinalReportWriterError

    blocked_audit = audit_report(blocked_doc, blocked_doc / "revised_report.md")
    write_audit_outputs(blocked_doc, blocked_audit)
    assert_true("blocked final not approved", blocked_audit["approved_for_final_report"] is False)
    assert_true("blocked final source eligibility", "Source Eligibility" in blocked_audit["blocking_gates"])
    try:
        run_final_report_writer(argparse.Namespace(document_root=blocked_doc))
    except FinalReportWriterError:
        pass
    else:
        raise SmokeFailure("secondary_only final writer should fail")
    assert_true("blocked final report absent", not (blocked_doc / "final_report.md").exists())


def test_optional_live_platform_smoke(base: Path) -> None:
    if os.environ.get("KW_LIVE_PLATFORM_SMOKE") != "1":
        print("SKIP optional live platform smoke; set KW_LIVE_PLATFORM_SMOKE=1 to enable")
        return
    cases = [
        ("youtube_with_subtitles", os.environ.get("KW_YOUTUBE_WITH_SUBTITLES_URL"), {"source_confirmed"}),
        ("youtube_without_subtitles", os.environ.get("KW_YOUTUBE_WITHOUT_SUBTITLES_URL"), {"secondary_only", "source_failed", "source_blocked"}),
        ("x_blocked", os.environ.get("KW_X_BLOCKED_URL"), {"source_blocked"}),
        ("xiaohongshu_blocked", os.environ.get("KW_XIAOHONGSHU_BLOCKED_URL"), {"source_blocked"}),
        ("douyin_blocked", os.environ.get("KW_DOUYIN_BLOCKED_URL"), {"source_blocked"}),
    ]
    cookies = os.environ.get("KW_YOUTUBE_COOKIES")
    ran = False
    for name, url, expected_statuses in cases:
        if not url:
            continue
        ran = True
        output = base / "live" / name / "10_video"
        command = [
            sys.executable,
            str(VIDEO / "scripts" / "platform_media_runner.py"),
            "--input",
            url,
            "--output-root",
            str(output),
            "--mode",
            "probe",
            "--timeout-seconds",
            "30",
            "--pretty",
        ]
        if cookies:
            command.extend(["--youtube-cookies", cookies])
        result = run(command, cwd=VIDEO / "scripts", timeout=90)
        status_path = output / "00_source" / "source_status.json"
        result_path = output / "00_source" / "platform_media_result.json"
        assert_true(f"{name} wrote source status", status_path.is_file())
        status = json.loads(status_path.read_text(encoding="utf-8"))
        assert_true(f"{name} expected status", status["source_status"] in expected_statuses, json.dumps(status, ensure_ascii=False))
        assert_true(f"{name} result written", result_path.is_file())
        if name.endswith("blocked"):
            assert_true(f"{name} full gate closed", status["can_enter_full_decomposition"] is False)
        if name == "youtube_with_subtitles":
            assert_true(f"{name} primary material", status["primary_material_available"] is True)
        assert_true(f"{name} no full pack in platform smoke", not (output / "video_analysis_pack.md").exists())
    assert_true("live env has at least one URL", ran, "set at least one KW_*_URL environment variable")


def main() -> int:
    tests = [
        test_transcript_and_subtitle_fixtures,
        test_youtube_fixture_cases,
        test_chrome_metadata_only_gate,
        test_platform_blocked_fixtures,
        test_final_report_audit,
        test_optional_live_platform_smoke,
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="kw-live-smoke-") as tmp:
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
    print("live platform smoke suite passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
