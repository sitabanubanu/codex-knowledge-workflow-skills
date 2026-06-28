#!/usr/bin/env python
"""Minimal acquisition-gated workflow runner.

This runner does not fetch media, start browsers, or create analysis artifacts.
It only converts acquisition probe signals into source_status.json, writes the
smallest permitted status/report files, and validates that the workflow stopped
before unsupported downstream artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import acquisition_probe
import artifact_validator
from write_artifact import ArtifactWriteError, write_artifact


RUNNER_NAME = "knowledge-video-minimal-workflow-runner"

BLOCKED_OR_DEGRADED_STATUSES = {
    "secondary_only",
    "source_blocked",
    "source_failed",
    "degraded_report_only",
}

DEGRADED_SIGNALS = {"degraded_report_only", "degraded_only", "user_accepts_degraded"}


class WorkflowRunnerError(Exception):
    """Expected CLI-facing runner failure."""


def json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def input_signals(values: list[str] | None) -> set[str]:
    return {acquisition_probe.canonical_signal(item) for item in acquisition_probe.split_values(values)}


def apply_degraded_override(status: dict[str, Any], signals: set[str]) -> dict[str, Any]:
    if not signals.intersection(DEGRADED_SIGNALS):
        return status

    current = str(status.get("source_status", ""))
    if current == "source_confirmed":
        return status

    full, composer, report_type, next_step = acquisition_probe.permissions_for_status("degraded_report_only")
    previous_reason = str(status.get("status_reason", "")).strip()
    status.update(
        {
            "source_status": "degraded_report_only",
            "can_enter_full_decomposition": full,
            "can_enter_document_composer": composer,
            "allowed_report_type": report_type,
            "primary_material_available": False,
            "status_reason": (
                "Degraded report only was explicitly requested after acquisition could not confirm "
                f"primary material. Previous status: {current}. {previous_reason}"
            ).strip(),
            "next_step": next_step,
        }
    )
    return status


def build_source_status(args: argparse.Namespace) -> dict[str, Any]:
    probe_args = argparse.Namespace(
        source_type=args.source_type,
        probe=args.probe,
        signal=args.signal,
        attempts=1,
        max_time_seconds=120,
    )
    status = acquisition_probe.build_summary(probe_args)
    if args.url:
        status["url"] = args.url

    status = apply_degraded_override(status, input_signals(args.signal))
    status["runner_policy"] = {
        "runner": RUNNER_NAME,
        "network_access_performed": False,
        "media_extraction_performed": False,
        "browser_launched": False,
        "transcript_written": False,
        "analysis_artifacts_written": False,
    }
    return status


def write_json_artifact(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return write_artifact(path, json_text(payload), json_mode=True, mkdirs=True)


def write_text_artifact(path: Path, content: str) -> dict[str, Any]:
    return write_artifact(path, content, mkdirs=True)


def render_partial_status(status: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Partial Source Status",
            "",
            f"Source status: `{status['source_status']}`.",
            "",
            "Primary material is available only in partial form. This runner did not write transcript, segmentation, inventory, or logic artifacts.",
            "",
            f"Reason: {status.get('status_reason', '')}",
            f"Next step: {status.get('next_step', '')}",
            "",
            "Required follow-up: provide the missing primary transcript/audio span or explicitly accept a partial-scope decomposition.",
            "",
        ]
    )


def render_acquisition_failure_report(status: dict[str, Any]) -> str:
    chrome_line = ""
    if status.get("chrome_required"):
        chrome_line = (
            "\nChrome page-state inspection is required next. This runner did not launch Chrome "
            "or retry the blocked extractor."
        )

    failed_probes = json.dumps(status.get("failed_probes", []), ensure_ascii=False, indent=2)
    return "\n".join(
        [
            "# Acquisition Failure Report",
            "",
            f"Source status: `{status['source_status']}`.",
            "",
            "No primary transcript, audio, or browser-visible transcript was confirmed from the provided acquisition signals.",
            "The workflow stopped before decomposition artifacts were written.",
            chrome_line.strip(),
            "",
            f"Reason: {status.get('status_reason', '')}",
            f"Next step: {status.get('next_step', '')}",
            "",
            "Failed probes:",
            "",
            "```json",
            failed_probes,
            "```",
            "",
        ]
    )


def render_degraded_report(status: dict[str, Any]) -> str:
    source_classes = json.dumps(status.get("source_classes", []), ensure_ascii=False)
    return "\n".join(
        [
            "# Degraded Source Report",
            "",
            f"Source status: `{status['source_status']}`.",
            "",
            "Only secondary or context material was indicated. No primary transcript, audio, or browser-visible transcript was confirmed.",
            "The runner stopped before transcript, segmentation, inventory, or logic artifacts were written.",
            "",
            f"Source classes: `{source_classes}`",
            f"Reason: {status.get('status_reason', '')}",
            f"Next step: {status.get('next_step', '')}",
            "",
            "Required follow-up: provide primary transcript/audio material or authorized page evidence before decomposition.",
            "",
        ]
    )


def write_status_specific_artifacts(output_root: Path, status: dict[str, Any]) -> list[dict[str, Any]]:
    source_status = status.get("source_status")
    if source_status == "source_confirmed":
        return []
    if source_status == "source_partial":
        return [write_text_artifact(output_root / "partial_source_status.md", render_partial_status(status))]
    if source_status in {"secondary_only", "degraded_report_only"}:
        return [write_text_artifact(output_root / "degraded_source_report.md", render_degraded_report(status))]
    if source_status in {"source_blocked", "source_failed"}:
        return [
            write_text_artifact(
                output_root / "acquisition_failure_report.md",
                render_acquisition_failure_report(status),
            )
        ]
    raise WorkflowRunnerError(f"unknown source_status: {source_status!r}")


def run_workflow(args: argparse.Namespace) -> dict[str, Any]:
    if args.output_root is None:
        raise WorkflowRunnerError("--output-root is required unless --self-test is used")

    output_root = args.output_root.expanduser().resolve()
    status = build_source_status(args)
    status_path = output_root / "source_status.json"

    written_summaries: list[dict[str, Any]] = []
    written_summaries.append(write_json_artifact(status_path, status))
    written_summaries.extend(write_status_specific_artifacts(output_root, status))

    validation = artifact_validator.validate_artifact_root(output_root, status_path, mode="strict")

    return {
        "runner": RUNNER_NAME,
        "url": args.url,
        "output_root": str(output_root),
        "source_status": status.get("source_status"),
        "allowed_report_type": status.get("allowed_report_type"),
        "can_enter_full_decomposition": status.get("can_enter_full_decomposition"),
        "primary_material_available": status.get("primary_material_available"),
        "chrome_required": status.get("chrome_required"),
        "chrome_route_used": status.get("chrome_route_used"),
        "transcript_written": False,
        "video_analysis_pack_written": False,
        "network_access_performed": False,
        "media_extraction_performed": False,
        "files_written": [str(item.get("path", "")) for item in written_summaries],
        "write_warnings": [
            warning
            for item in written_summaries
            for warning in item.get("warnings", [])
        ],
        "validation": validation,
        "next_step": validation.get("next_step") or status.get("next_step"),
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the minimal acquisition gate and stop unsupported video workflows.",
    )
    parser.add_argument("--url", default=None, help="Optional source URL for downstream records.")
    parser.add_argument(
        "--source-type",
        choices=["platform_url", "local_media", "local_transcript", "unknown"],
        default="unknown",
    )
    parser.add_argument(
        "--probe",
        action="append",
        help="Repeatable or comma-separated probe names, e.g. yt-dlp,Chrome,Firecrawl.",
    )
    parser.add_argument(
        "--signal",
        action="append",
        help="Repeatable or comma-separated result signals, e.g. http_429,transcript_available.",
    )
    parser.add_argument("--output-root", type=Path, default=None, help="Directory for minimal runner output.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in runner tests.")
    return parser


def test_args(
    output_root: Path,
    *,
    source_type: str = "unknown",
    probe: list[str] | None = None,
    signal: list[str] | None = None,
    url: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        url=url,
        source_type=source_type,
        probe=probe,
        signal=signal,
        output_root=output_root,
        pretty=False,
        self_test=False,
    )


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="workflow-runner-") as tmp:
        base = Path(tmp)

        confirmed_root = base / "transcript_available"
        confirmed = run_workflow(
            test_args(
                confirmed_root,
                probe=["youtube_transcript_api"],
                signal=["transcript_available"],
            )
        )
        confirmed_status = read_json(confirmed_root / "source_status.json")
        assert_true(
            "transcript_available status",
            confirmed.get("source_status") == "source_confirmed",
            failures,
        )
        assert_true(
            "transcript_available permits downstream full state",
            confirmed_status.get("can_enter_full_decomposition") is True,
            failures,
        )
        assert_true(
            "transcript_available does not fabricate transcript directory",
            not (confirmed_root / "01_transcript").exists(),
            failures,
        )
        assert_true(
            "transcript_available does not write pack shell",
            not (confirmed_root / "video_analysis_pack.md").exists(),
            failures,
        )
        assert_true("transcript_available validates", confirmed["validation"].get("valid") is True, failures)

        blocked_root = base / "yt_dlp_429"
        blocked = run_workflow(
            test_args(
                blocked_root,
                source_type="platform_url",
                probe=["yt-dlp"],
                signal=["http_429"],
            )
        )
        blocked_report = (blocked_root / "acquisition_failure_report.md").read_text(encoding="utf-8")
        assert_true("yt-dlp 429 blocked", blocked.get("source_status") == "source_blocked", failures)
        assert_true("yt-dlp 429 requires Chrome", blocked.get("chrome_required") is True, failures)
        assert_true(
            "yt-dlp 429 report names Chrome next step",
            "Chrome page-state inspection is required next" in blocked_report,
            failures,
        )
        assert_true("yt-dlp 429 validates", blocked["validation"].get("valid") is True, failures)

        secondary_root = base / "firecrawl_secondary"
        secondary = run_workflow(
            test_args(
                secondary_root,
                probe=["Firecrawl"],
                signal=["metadata_available"],
            )
        )
        assert_true("Firecrawl secondary status", secondary.get("source_status") == "secondary_only", failures)
        assert_true(
            "Firecrawl secondary writes degraded report",
            (secondary_root / "degraded_source_report.md").is_file(),
            failures,
        )
        assert_true(
            "Firecrawl secondary does not write logic artifact",
            not (secondary_root / "04_logic").exists(),
            failures,
        )
        assert_true(
            "Firecrawl secondary does not write pack shell",
            not (secondary_root / "video_analysis_pack.md").exists(),
            failures,
        )
        assert_true("Firecrawl secondary validates", secondary["validation"].get("valid") is True, failures)

        failed_root = base / "hearsay_timeout"
        failed = run_workflow(
            test_args(
                failed_root,
                source_type="platform_url",
                probe=["Hearsay"],
                signal=["timeout"],
            )
        )
        assert_true("Hearsay timeout status", failed.get("source_status") == "source_failed", failures)
        assert_true("Hearsay platform timeout requires Chrome", failed.get("chrome_required") is True, failures)
        assert_true(
            "Hearsay timeout writes failure report",
            (failed_root / "acquisition_failure_report.md").is_file(),
            failures,
        )
        failed_report = (failed_root / "acquisition_failure_report.md").read_text(encoding="utf-8")
        assert_true(
            "Hearsay timeout report names Chrome next step",
            "Chrome page-state inspection is required next" in failed_report,
            failures,
        )
        assert_true("Hearsay timeout validates", failed["validation"].get("valid") is True, failures)

        degraded_root = base / "explicit_degraded"
        degraded = run_workflow(
            test_args(
                degraded_root,
                probe=["Firecrawl"],
                signal=["metadata_available,degraded_report_only"],
            )
        )
        assert_true(
            "explicit degraded status",
            degraded.get("source_status") == "degraded_report_only",
            failures,
        )
        assert_true("explicit degraded validates", degraded["validation"].get("valid") is True, failures)

        bad_root = base / "validator_blocks_bad_full_product"
        bad_status = {
            "source_status": "secondary_only",
            "can_enter_full_decomposition": False,
            "can_enter_document_composer": True,
            "allowed_report_type": "degraded_source_report",
            "source_classes": ["firecrawl_context"],
            "primary_material_available": False,
            "status_reason": "self-test secondary-only status",
            "failed_probes": [],
            "next_step": "request_primary_transcript_audio_or_authorized_page_access",
        }
        write_json_artifact(bad_root / "source_status.json", bad_status)
        write_text_artifact(
            bad_root / "video_analysis_pack.md",
            "# Video Analysis Pack\n\nSource-confirmed analysis.\n",
        )
        write_text_artifact(
            bad_root / "04_logic" / "source_logic.md",
            "# Source Logic\n\nSpeaker logic reconstruction.\n",
        )
        bad_validation = artifact_validator.validate_artifact_root(
            bad_root,
            bad_root / "source_status.json",
            mode="strict",
        )
        assert_true(
            "validator blocks bad full product",
            bad_validation.get("valid") is False,
            failures,
            json.dumps(bad_validation.get("findings", []), ensure_ascii=False),
        )
        assert_true(
            "validator reports blocked outputs",
            bool(bad_validation.get("blocked_outputs_detected")),
            failures,
        )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("self-test passed")
    return 0


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    try:
        summary = run_workflow(args)
    except (ArtifactWriteError, WorkflowRunnerError) as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "error": exc.__class__.__name__,
                "message": str(exc),
                "network_access_performed": False,
                "media_extraction_performed": False,
            },
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return 1

    emit_json(summary, pretty=args.pretty)
    return 0 if summary["validation"].get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
