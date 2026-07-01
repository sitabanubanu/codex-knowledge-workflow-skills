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
from datetime import datetime, timezone
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


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def route_from_material_state(material_state: str, status: dict[str, Any]) -> str:
    if material_state == "subtitle_acquired":
        return "subtitle"
    if material_state == "audio_acquired_pending_asr":
        return "audio"
    source_status = status.get("source_status")
    if source_status == "source_blocked":
        return "blocked"
    if source_status == "source_failed":
        return "failed"
    if source_status in {"secondary_only", "degraded_report_only"}:
        return "metadata_only"
    return material_state or "unknown"


def expected_route_compatible(expected_route: str, observed_route: str) -> bool:
    compatible = {
        "subtitle": {"subtitle"},
        "audio_or_metadata_only": {"audio", "metadata_only", "blocked", "failed"},
        "cookies_or_blocked": {"blocked", "failed", "metadata_only"},
        "blocked_or_metadata_only": {"blocked", "metadata_only", "failed"},
        "failed": {"failed"},
    }
    return observed_route in compatible.get(expected_route, {expected_route})


def status_text(status: dict[str, Any] | None) -> str:
    if not status:
        return ""
    return json.dumps(status, ensure_ascii=False, sort_keys=True).lower()


def has_degraded_or_block_reason(status: dict[str, Any] | None, failure_reason: str | None) -> bool:
    text = f"{status_text(status)} {(failure_reason or '').lower()}"
    markers = [
        "blocked",
        "captcha",
        "login",
        "sign",
        "metadata",
        "no primary",
        "failed",
        "timeout",
        "request",
        "unavailable",
        "cookies",
    ]
    return any(marker in text for marker in markers)


def has_cookie_or_auth_signal(status: dict[str, Any] | None, failure_reason: str | None) -> bool:
    text = f"{status_text(status)} {(failure_reason or '').lower()}"
    markers = ["cookie", "cookies", "login", "sign in", "auth", "bot", "captcha", "chrome"]
    return any(marker in text for marker in markers)


def load_live_cases() -> list[dict[str, Any]]:
    case_path = FIXTURES / "live_cases.json"
    if not case_path.exists():
        return []
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    return list(payload.get("cases") or [])


def build_case_record(
    *,
    case: dict[str, Any],
    output: Path,
    command_result: dict[str, Any],
    status: dict[str, Any] | None,
    media_result: dict[str, Any] | None,
    failure_reason: str | None,
) -> dict[str, Any]:
    material_state = str((media_result or {}).get("material_decision", {}).get("material_state") or "")
    route = route_from_material_state(material_state, status or {})
    transcript_exists = (output / "01_transcript" / "clean_transcript.jsonl").is_file()
    media_files = list((output / "00_source" / "raw" / "audio").rglob("*")) if (output / "00_source" / "raw" / "audio").exists() else []
    return {
        "case_id": case.get("id"),
        "url": os.environ.get(str(case.get("url_env") or ""), ""),
        "platform": case.get("platform"),
        "source_status": (status or {}).get("source_status"),
        "route": route,
        "expected_route": case.get("expected_route"),
        "route_compatible": expected_route_compatible(str(case.get("expected_route") or ""), route),
        "requires_cookies": bool(case.get("requires_cookies")),
        "cookies_supplied": bool(os.environ.get("KW_YOUTUBE_COOKIES")),
        "cookies_signal_observed": has_cookie_or_auth_signal(status, failure_reason),
        "status_reason": (status or {}).get("status_reason"),
        "next_step": (status or {}).get("next_step"),
        "transcript_exists": transcript_exists,
        "media_exists": any(path.is_file() for path in media_files),
        "analysis_pack_exists": (output / "video_analysis_pack.md").is_file(),
        "final_report_exists": (output.parent / "20_document" / "final_report.md").is_file(),
        "failure_reason": failure_reason,
        "resume_safe": bool((output.parent / "logs" / "run_state.json").exists() or (output / "00_source" / "platform_media_result.json").exists()),
        "command_returncode": command_result.get("returncode"),
    }


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
    summary_path = base.parent / "summary.json"
    records: list[dict[str, Any]] = []
    if os.environ.get("KW_LIVE_PLATFORM_SMOKE") != "1":
        write_json(
            summary_path,
            {
                "mode": "fixture",
                "live_enabled": False,
                "records": records,
                "message": "Set KW_LIVE_PLATFORM_SMOKE=1 to enable live platform smoke.",
            },
        )
        print("SKIP optional live platform smoke; set KW_LIVE_PLATFORM_SMOKE=1 to enable")
        return
    cases = load_live_cases()
    cookies = os.environ.get("KW_YOUTUBE_COOKIES")
    ran = False
    try:
        for case in cases:
            name = str(case.get("id"))
            url = os.environ.get(str(case.get("url_env") or ""))
            expected_statuses = set(case.get("expected_min_statuses") or [])
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
                "auto",
                "--timeout-seconds",
                "30",
                "--pretty",
            ]
            if cookies:
                command.extend(["--youtube-cookies", cookies])
            result = run(command, cwd=VIDEO / "scripts", timeout=90)
            status_path = output / "00_source" / "source_status.json"
            result_path = output / "00_source" / "platform_media_result.json"
            status = None
            media_result = None
            failure_reason = None
            if status_path.is_file():
                status = json.loads(status_path.read_text(encoding="utf-8"))
            if result_path.is_file():
                media_result = json.loads(result_path.read_text(encoding="utf-8"))
            if result["returncode"] != 0:
                failure_reason = result["stderr"] or result["stdout"] or "platform_media_runner failed"
            records.append(
                build_case_record(
                    case=case,
                    output=output,
                    command_result=result,
                    status=status,
                    media_result=media_result,
                    failure_reason=failure_reason,
                )
            )
            record = records[-1]
            assert_true(f"{name} wrote source status", status_path.is_file())
            assert_true(f"{name} expected status", status["source_status"] in expected_statuses, json.dumps(status, ensure_ascii=False))
            assert_true(f"{name} result written", result_path.is_file())
            assert_true(
                f"{name} expected route",
                record["route_compatible"] is True,
                json.dumps(record, ensure_ascii=False),
            )
            if case.get("requires_cookies") and not os.environ.get("KW_YOUTUBE_COOKIES"):
                assert_true(
                    f"{name} cookie/auth signal",
                    record["cookies_signal_observed"] is True,
                    json.dumps(record, ensure_ascii=False),
                )
            if case.get("expected_route") in {"blocked_or_metadata_only", "failed", "cookies_or_blocked"}:
                assert_true(f"{name} full gate closed", status["can_enter_full_decomposition"] is False)
                if record["route"] != "blocked":
                    assert_true(
                        f"{name} degraded/failure reason",
                        has_degraded_or_block_reason(status, failure_reason),
                        json.dumps(record, ensure_ascii=False),
                    )
            if case.get("expected_route") == "subtitle":
                assert_true(f"{name} primary material", status["primary_material_available"] is True)
            assert_true(f"{name} no full pack in platform smoke", not (output / "video_analysis_pack.md").exists())
    finally:
        write_json(
            summary_path,
            {
                "mode": "live",
                "live_enabled": True,
                "records": records,
            },
        )
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
    output_root = REPO_ROOT / "test_outputs" / "live_platform_smoke" / timestamp_id()
    base = output_root / "work"
    base.mkdir(parents=True, exist_ok=True)
    try:
        for test in tests:
            try:
                test(base)
                print(f"PASS {test.__name__}")
            except Exception as exc:
                failures.append(f"{test.__name__}: {exc}")
                print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    finally:
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
    print(f"live platform smoke suite passed; summary: {output_root / 'suite_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
