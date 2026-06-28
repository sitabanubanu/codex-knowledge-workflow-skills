#!/usr/bin/env python
"""Summarize acquisition probe signals for knowledge-video-decomposer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable


SOURCE_STATUSES = {
    "source_confirmed",
    "source_partial",
    "secondary_only",
    "source_blocked",
    "source_failed",
    "degraded_report_only",
}

PRIMARY_FULL_SIGNALS = {
    "transcript_available",
    "audio_available",
    "chrome_visible_transcript",
    "user_file",
    "local_transcript",
    "subtitles_acquired_via_chrome_cookies",
    "audio_acquired_via_chrome_cookies",
    "browser_derived_media_acquired",
}
PRIMARY_PARTIAL_SIGNALS = {"partial_transcript"}
BLOCKED_SIGNALS = {
    "http_429",
    "bot_check",
    "bot_confirmation",
    "captcha",
    "login_required",
    "request_blocked",
    "paywall",
    "permission_required",
}
FAILED_SIGNALS = {
    "timeout",
    "tool_failed",
    "chrome_no_transcript",
    "chrome_deep_probe_exhausted",
}
SECONDARY_SIGNALS = {"secondary_summary_available", "metadata_available"}

KNOWN_PROBES = {
    "yt-dlp",
    "yt-dlp-chrome-cookies",
    "youtube_transcript_api",
    "Chrome",
    "Hearsay",
    "local_asr",
    "Firecrawl",
    "search",
    "Podwise",
    "user_file",
}

SECONDARY_PROBES = {"Firecrawl", "search", "Podwise"}

SIGNAL_ALIASES = {
    "bot": "bot_check",
    "bot_detected": "bot_check",
    "bot_signin": "bot_check",
    "bot_sign_in": "bot_check",
    "bot_sign_in_required": "bot_check",
    "sign_in_to_confirm": "bot_check",
    "signin_to_confirm": "bot_check",
    "sign_in_required": "login_required",
    "signin_required": "login_required",
    "requestblocked": "request_blocked",
    "too_many_requests": "http_429",
    "ytdlp_chrome_cookies_subtitles": "subtitles_acquired_via_chrome_cookies",
    "ytdlp_chrome_cookies_audio": "audio_acquired_via_chrome_cookies",
    "pageassets_exported_media": "browser_derived_media_acquired",
    "deep_probe_exhausted": "chrome_deep_probe_exhausted",
}


def split_values(values: Iterable[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        for item in value.split(","):
            item = item.strip()
            if item:
                result.append(item)
    return result


def canonical_probe(probe: str) -> str:
    lowered = probe.lower()
    for known in KNOWN_PROBES:
        if known.lower() == lowered:
            return known
    return probe


def canonical_signal(signal: str) -> str:
    normalized = signal.strip().lower().replace("-", "_").replace(" ", "_")
    return SIGNAL_ALIASES.get(normalized, normalized)


def source_classes_for(
    source_type: str,
    probes: set[str],
    signals: set[str],
) -> list[str]:
    classes: set[str] = set()

    if "transcript_available" in signals or "local_transcript" in signals:
        classes.add("primary_transcript")
    if source_type == "local_transcript":
        classes.add("primary_transcript")
    if "user_file" in signals and source_type in {"local_transcript", "unknown"}:
        classes.add("primary_transcript")
    if "user_file" in probes and source_type != "local_media":
        classes.add("primary_transcript")
    if "subtitles_acquired_via_chrome_cookies" in signals:
        classes.add("primary_transcript")
    if "audio_available" in signals or "audio_acquired_via_chrome_cookies" in signals or (
        ("user_file" in signals or "user_file" in probes) and source_type == "local_media"
    ):
        classes.add("primary_audio_asr")
    if "chrome_visible_transcript" in signals:
        classes.add("browser_visible_transcript")
    if "browser_derived_media_acquired" in signals:
        classes.add("browser_derived_media")
    if "partial_transcript" in signals:
        classes.add("primary_transcript")

    if "metadata_available" in signals:
        classes.add("platform_metadata")
    if "secondary_summary_available" in signals or "Podwise" in probes:
        classes.add("secondary_summary")
    if "search" in probes:
        classes.add("search_snippet")
    if "Firecrawl" in probes:
        classes.add("firecrawl_context")
    if "Chrome" in probes and not classes.intersection(
        {"browser_visible_transcript", "primary_transcript", "browser_derived_media"}
    ):
        classes.add("page_observation")

    order = [
        "primary_transcript",
        "primary_audio_asr",
        "browser_visible_transcript",
        "browser_derived_media",
        "platform_metadata",
        "secondary_summary",
        "search_snippet",
        "firecrawl_context",
        "page_observation",
    ]
    return [item for item in order if item in classes]


def probe_source_class(probe: str) -> str:
    if probe == "youtube_transcript_api":
        return "primary_transcript"
    if probe == "yt-dlp":
        return "primary_transcript"
    if probe == "yt-dlp-chrome-cookies":
        return "primary_transcript"
    if probe == "Chrome":
        return "browser_visible_transcript"
    if probe in {"Hearsay", "local_asr"}:
        return "primary_audio_asr"
    if probe == "Firecrawl":
        return "firecrawl_context"
    if probe == "search":
        return "search_snippet"
    if probe == "Podwise":
        return "secondary_summary"
    if probe == "user_file":
        return "primary_transcript"
    return "unknown"


def result_for_probe(probe: str, signals: set[str], status: str) -> tuple[str, str]:
    if status == "source_blocked" and signals & BLOCKED_SIGNALS:
        return "blocked", ", ".join(sorted(signals & BLOCKED_SIGNALS))
    if "timeout" in signals:
        return "timeout", "timeout"
    if "tool_failed" in signals:
        return "failed", "tool_failed"
    if "chrome_no_transcript" in signals and probe == "Chrome":
        return "failed", "chrome_no_transcript"
    if "chrome_deep_probe_exhausted" in signals and probe == "Chrome":
        return "failed", "chrome_deep_probe_exhausted"
    if status == "source_partial":
        return "partial", "partial_transcript"
    if status in {"source_confirmed", "secondary_only"}:
        return "success", ""
    return "failed", "no usable primary or secondary material"


def build_failed_probes(
    probes: set[str],
    signals: set[str],
    status: str,
    attempts: int,
    max_time_seconds: int,
    chrome_required: bool,
    yt_dlp_chrome_cookies_needed: bool,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    blocked_or_failed_results = {"blocked", "failed", "timeout"}

    for probe in sorted(probes, key=str.lower):
        result, reason = result_for_probe(probe, signals, status)
        if result not in blocked_or_failed_results:
            continue
        next_route = ""
        if probe == "yt-dlp" and result in {"blocked", "failed", "timeout"}:
            # The immediate next step after yt-dlp bare fails is to retry with Chrome cookies.
            next_route = "retry_yt_dlp_with_chrome_cookies"
        elif probe == "yt-dlp-chrome-cookies" and result in {"blocked", "failed", "timeout"}:
            # After yt-dlp with Chrome cookies fails, go to Chrome deep-probe.
            next_route = "chrome_deep_probe"
        elif chrome_required and result in {"blocked", "failed", "timeout"} and probe not in {"yt-dlp", "yt-dlp-chrome-cookies"}:
            next_route = "Chrome"
        elif result in {"failed", "timeout"}:
            next_route = "user_provided_primary_material"
        rows.append(
            {
                "probe": probe,
                "source_class_attempted": probe_source_class(probe),
                "max_time_seconds": max_time_seconds,
                "attempts": attempts,
                "result": result,
                "failure_reason": reason,
                "next_route": next_route,
            }
        )
    return rows


def determine_status(
    source_type: str,
    probes: set[str],
    signals: set[str],
) -> tuple[str, str]:
    # yt-dlp-chrome-cookies success produces primary material just like bare yt-dlp would.
    has_yt_cookies_success = bool(
        signals & {"subtitles_acquired_via_chrome_cookies", "audio_acquired_via_chrome_cookies"}
    ) and "yt-dlp-chrome-cookies" in probes

    has_primary_full = (
        bool(signals & PRIMARY_FULL_SIGNALS)
        or source_type == "local_transcript"
        or ("user_file" in probes and not bool(signals & (BLOCKED_SIGNALS | FAILED_SIGNALS)))
        or has_yt_cookies_success
    )
    has_primary_partial = bool(signals & PRIMARY_PARTIAL_SIGNALS)
    has_block = bool(signals & BLOCKED_SIGNALS)
    has_failure = bool(signals & FAILED_SIGNALS)
    has_secondary = bool(signals & SECONDARY_SIGNALS) or bool(probes & SECONDARY_PROBES)

    # Browser-derived media can support source_confirmed:
    if "browser_derived_media_acquired" in signals:
        return "source_confirmed", "Browser-derived media was exported and processed into transcript material."

    # Primary material wins over failed helper probes; partial remains explicitly marked.
    if has_primary_partial:
        return "source_partial", "Primary transcript material is available only in partial form."
    if has_primary_full:
        return "source_confirmed", "Primary transcript, audio, Chrome-visible transcript, Chrome-cookies subtitles/audio, or user file is available."
    if has_block:
        return "source_blocked", "A platform or page access block prevents primary source acquisition."
    if has_secondary:
        return "secondary_only", "Only metadata, search, Firecrawl, Podwise, or other secondary context is available."
    if has_failure:
        return "source_failed", "Probe failed or timed out without an access-block signal or usable source material."
    return "source_failed", "No useful primary or secondary source signal was provided."


def chrome_summary(
    source_type: str,
    probes: set[str],
    signals: set[str],
) -> tuple[bool, bool, bool, str, str, str, bool, bool]:
    chrome_used = "Chrome" in probes
    chrome_deep_probe_done = chrome_used and (
        "chrome_no_transcript" in signals
        or "chrome_deep_probe_exhausted" in signals
        or "browser_derived_media_acquired" in signals
    )
    chrome_failed_or_no_transcript = bool(
        signals & {"chrome_no_transcript", "chrome_deep_probe_exhausted"}
    )
    blocked_platform = source_type == "platform_url" and bool(signals & BLOCKED_SIGNALS)
    hearsay_platform_timeout = (
        source_type == "platform_url" and "Hearsay" in probes and "timeout" in signals
    )

    # yt-dlp bare blocked → yt-dlp Chrome cookies should be tried
    yt_dlp_bare_blocked = "yt-dlp" in probes and bool(signals & BLOCKED_SIGNALS)
    yt_dlp_chrome_cookies_attempted = "yt-dlp-chrome-cookies" in probes
    yt_dlp_chrome_cookies_succeeded = bool(
        signals & {"subtitles_acquired_via_chrome_cookies", "audio_acquired_via_chrome_cookies"}
    )

    chrome_required = (
        (blocked_platform or hearsay_platform_timeout)
        and not (chrome_used and chrome_failed_or_no_transcript)
        and not yt_dlp_chrome_cookies_succeeded
    )

    if "chrome_visible_transcript" in signals:
        visible = "available"
    elif "partial_transcript" in signals and chrome_used:
        visible = "partial"
    elif "chrome_no_transcript" in signals:
        visible = "not_visible"
    elif "chrome_deep_probe_exhausted" in signals:
        visible = "not_visible"
    elif "browser_derived_media_acquired" in signals and chrome_used:
        visible = "available"
    elif bool(signals & BLOCKED_SIGNALS) and chrome_used:
        visible = "blocked"
    elif chrome_used:
        visible = "unknown"
    else:
        visible = "not_checked"

    if "captcha" in signals:
        page_state = "captcha_required"
    elif "login_required" in signals:
        page_state = "login_required"
    elif "paywall" in signals:
        page_state = "paywalled"
    elif "permission_required" in signals:
        page_state = "permission_required"
    elif "chrome_visible_transcript" in signals:
        page_state = "opened"
    elif "browser_derived_media_acquired" in signals:
        page_state = "opened"
    elif "chrome_no_transcript" in signals:
        page_state = "opened"
    elif "chrome_deep_probe_exhausted" in signals:
        page_state = "opened"
    elif "metadata_available" in signals:
        page_state = "metadata_only"
    elif chrome_used and bool(signals & {"timeout", "tool_failed"}):
        page_state = "failed_to_open"
    elif bool(signals & BLOCKED_SIGNALS):
        page_state = "unknown"
    else:
        page_state = "unknown"

    if chrome_used:
        if yt_dlp_chrome_cookies_succeeded:
            why = (
                "Chrome route was used alongside yt-dlp with Chrome cookies, "
                "which succeeded in acquiring primary material."
            )
        elif chrome_deep_probe_done:
            why = (
                "Chrome deep-probe sequence was executed after yt-dlp Chrome cookies "
                "did not produce primary material."
            )
        else:
            why = "Chrome route was reported as used by the probe input."
    elif yt_dlp_bare_blocked and not yt_dlp_chrome_cookies_attempted:
        why = (
            "yt-dlp bare was blocked. yt-dlp with --cookies-from-browser chrome "
            "must be attempted before Chrome page-state inspection."
        )
    elif chrome_required and hearsay_platform_timeout:
        why = (
            "Hearsay URL ingestion timed out on a platform URL. "
            "yt-dlp with Chrome cookies or Chrome page-state inspection is required next."
        )
    elif chrome_required:
        why = (
            "Platform URL had an access-block signal. "
            "yt-dlp with Chrome cookies or Chrome page-state inspection is required next."
        )
    else:
        why = "Chrome was not required by the provided source type and signals."

    return (
        chrome_required,
        chrome_used,
        chrome_deep_probe_done,
        visible,
        page_state,
        why,
        yt_dlp_chrome_cookies_attempted,
        yt_dlp_chrome_cookies_succeeded,
    )


def permissions_for_status(status: str) -> tuple[bool, bool, str, str]:
    if status == "source_confirmed":
        return True, True, "full_video_analysis_pack", "enter_segmentation_inventory_logic_gap_check"
    if status == "source_partial":
        return False, True, "partial_video_analysis_pack", "continue_only_with_explicit_partial_scope"
    if status == "secondary_only":
        return False, True, "degraded_source_report", "request_primary_transcript_audio_or_authorized_page_access"
    if status == "source_blocked":
        return False, True, "acquisition_failure_report", "stop_full_decomposition_and_request_primary_material_or_chrome_check"
    if status == "degraded_report_only":
        return False, True, "degraded_source_report", "write_degraded_source_report_only"
    return False, True, "acquisition_failure_report", "request_alternate_transcript_audio_or_longer_authorized_probe"


def build_summary(args: argparse.Namespace) -> dict[str, object]:
    probes = {canonical_probe(item) for item in split_values(args.probe)}
    signals = {canonical_signal(item) for item in split_values(args.signal)}
    status, reason = determine_status(args.source_type, probes, signals)
    full, composer, report_type, next_step = permissions_for_status(status)
    classes = source_classes_for(args.source_type, probes, signals)
    (
        chrome_required,
        chrome_used,
        chrome_deep_probe_done,
        visible,
        page_state,
        chrome_reason,
        yt_cookies_attempted,
        yt_cookies_succeeded,
    ) = chrome_summary(args.source_type, probes, signals)

    # Determine next_step based on acquisition state
    yt_dlp_bare_blocked = "yt-dlp" in probes and bool(signals & BLOCKED_SIGNALS)
    if yt_dlp_bare_blocked and not yt_cookies_attempted:
        next_step = "retry_yt_dlp_with_chrome_cookies"
    elif yt_cookies_attempted and not yt_cookies_succeeded and not chrome_used:
        next_step = "perform_chrome_deep_probe"
    elif chrome_required and not chrome_used and not yt_cookies_succeeded:
        next_step = "perform_chrome_page_state_inspection"
    elif chrome_used and signals & {"chrome_deep_probe_exhausted"}:
        next_step = "request_user_provided_local_file_or_accept_degraded_report"

    primary_available = bool(
        set(classes)
        & {"primary_transcript", "primary_audio_asr", "browser_visible_transcript", "browser_derived_media"}
    )

    return {
        "source_status": status,
        "can_enter_full_decomposition": full,
        "can_enter_document_composer": composer,
        "allowed_report_type": report_type,
        "source_classes": classes,
        "primary_material_available": primary_available,
        "chrome_required": chrome_required,
        "chrome_route_used": chrome_used,
        "chrome_deep_probe_exhausted": chrome_deep_probe_done and bool(
            signals & {"chrome_deep_probe_exhausted"}
        ),
        "visible_transcript_status": visible,
        "page_state_observed": page_state,
        "yt_dlp_chrome_cookies_attempted": yt_cookies_attempted,
        "yt_dlp_chrome_cookies_succeeded": yt_cookies_succeeded,
        "why_chrome_was_or_was_not_used": chrome_reason,
        "status_reason": reason,
        "failed_probes": build_failed_probes(
            probes,
            signals,
            status,
            args.attempts,
            args.max_time_seconds,
            chrome_required,
            yt_cookies_succeeded,
        ),
        "next_step": next_step,
        "cost_limits": {
            "attempts": args.attempts,
            "max_time_seconds": args.max_time_seconds,
            "network_access_performed": False,
            "media_extraction_performed": False,
        },
    }


def write_json(payload: dict[str, object], output: Path | None, pretty: bool) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty)
    text += "\n"
    if output is None:
        sys.stdout.write(text)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert acquisition probe results into source-status JSON.",
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
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--max-time-seconds", type=int, default=120)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in decision tests.")
    return parser


def assert_case(name: str, cli_args: list[str], expected: dict[str, object]) -> list[str]:
    parser = make_parser()
    args = parser.parse_args(cli_args)
    payload = build_summary(args)
    failures: list[str] = []
    for key, value in expected.items():
        if payload.get(key) != value:
            failures.append(f"{name}: expected {key}={value!r}, got {payload.get(key)!r}")
    return failures


def run_self_test() -> int:
    cases = [
        (
            "transcript available",
            ["--probe", "youtube_transcript_api", "--signal", "transcript_available"],
            {"source_status": "source_confirmed", "can_enter_full_decomposition": True},
        ),
        (
            "partial transcript",
            ["--probe", "youtube_transcript_api", "--signal", "partial_transcript"],
            {"source_status": "source_partial"},
        ),
        (
            "yt-dlp 429 platform url",
            ["--source-type", "platform_url", "--probe", "yt-dlp", "--signal", "http_429"],
            {
                "source_status": "source_blocked",
                "chrome_required": True,
                "next_step": "retry_yt_dlp_with_chrome_cookies",
                "yt_dlp_chrome_cookies_attempted": False,
            },
        ),
        (
            "yt-dlp bot check platform url",
            [
                "--source-type",
                "platform_url",
                "--probe",
                "yt-dlp",
                "--signal",
                "bot_check",
            ],
            {
                "source_status": "source_blocked",
                "chrome_required": True,
                "next_step": "retry_yt_dlp_with_chrome_cookies",
            },
        ),
        (
            "yt-dlp sign in to confirm alias",
            [
                "--source-type",
                "platform_url",
                "--probe",
                "yt-dlp",
                "--signal",
                "sign_in_to_confirm",
            ],
            {
                "source_status": "source_blocked",
                "chrome_required": True,
                "next_step": "retry_yt_dlp_with_chrome_cookies",
            },
        ),
        (
            "yt-dlp Chrome cookies subtitles success",
            [
                "--source-type",
                "platform_url",
                "--probe",
                "yt-dlp,yt-dlp-chrome-cookies",
                "--signal",
                "subtitles_acquired_via_chrome_cookies",
            ],
            {
                "source_status": "source_confirmed",
                "can_enter_full_decomposition": True,
                "yt_dlp_chrome_cookies_attempted": True,
                "yt_dlp_chrome_cookies_succeeded": True,
                "primary_material_available": True,
            },
        ),
        (
            "yt-dlp Chrome cookies audio success",
            [
                "--source-type",
                "platform_url",
                "--probe",
                "yt-dlp,yt-dlp-chrome-cookies",
                "--signal",
                "audio_acquired_via_chrome_cookies",
            ],
            {
                "source_status": "source_confirmed",
                "can_enter_full_decomposition": True,
                "yt_dlp_chrome_cookies_attempted": True,
                "yt_dlp_chrome_cookies_succeeded": True,
                "primary_material_available": True,
            },
        ),
        (
            "yt-dlp Chrome cookies also fails → next step is Chrome deep probe",
            [
                "--source-type",
                "platform_url",
                "--probe",
                "yt-dlp,yt-dlp-chrome-cookies",
                "--signal",
                "http_429,request_blocked",
            ],
            {
                "source_status": "source_blocked",
                "next_step": "perform_chrome_deep_probe",
                "yt_dlp_chrome_cookies_attempted": True,
                "yt_dlp_chrome_cookies_succeeded": False,
            },
        ),
        (
            "browser derived media acquired via pageAssets",
            [
                "--source-type",
                "platform_url",
                "--probe",
                "yt-dlp,yt-dlp-chrome-cookies,Chrome",
                "--signal",
                "browser_derived_media_acquired",
            ],
            {
                "source_status": "source_confirmed",
                "can_enter_full_decomposition": True,
                "primary_material_available": True,
            },
        ),
        (
            "Chrome deep probe exhausted",
            [
                "--source-type",
                "platform_url",
                "--probe",
                "yt-dlp,yt-dlp-chrome-cookies,Chrome",
                "--signal",
                "http_429,request_blocked,chrome_deep_probe_exhausted",
            ],
            {
                "source_status": "source_blocked",
                "next_step": "request_user_provided_local_file_or_accept_degraded_report",
                "chrome_deep_probe_exhausted": True,
            },
        ),
        (
            "Firecrawl Podwise secondary only",
            [
                "--probe",
                "Firecrawl,Podwise",
                "--signal",
                "metadata_available,secondary_summary_available",
            ],
            {"source_status": "secondary_only", "can_enter_full_decomposition": False},
        ),
        (
            "Hearsay timeout only",
            ["--probe", "Hearsay", "--signal", "timeout"],
            {"source_status": "source_failed"},
        ),
        (
            "Hearsay platform URL timeout requires Chrome or yt-dlp Chrome cookies",
            [
                "--source-type",
                "platform_url",
                "--probe",
                "Hearsay",
                "--signal",
                "timeout",
            ],
            {
                "source_status": "source_failed",
                "chrome_required": True,
                "next_step": "perform_chrome_page_state_inspection",
            },
        ),
    ]

    failures: list[str] = []
    for name, cli_args, expected in cases:
        failures.extend(assert_case(name, cli_args, expected))

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

    if args.attempts < 0:
        parser.error("--attempts must be >= 0")
    if args.max_time_seconds < 0:
        parser.error("--max-time-seconds must be >= 0")

    payload = build_summary(args)
    if args.url:
        payload["url"] = args.url
    write_json(payload, args.output, args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
