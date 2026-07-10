#!/usr/bin/env python
"""Create a user-facing preflight plan before a knowledge workflow run."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


RUNNER_NAME = "knowledge-workflow-preflight"


def detect_input_kind(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return "url"
    suffix = Path(value).suffix.lower()
    if suffix in {".txt", ".md", ".srt", ".vtt", ".jsonl", ".json"}:
        return "transcript_or_subtitle"
    if suffix in {".mp3", ".mp4", ".m4a", ".webm", ".wav", ".mov", ".opus"}:
        return "media"
    return "unknown"


def detect_platform(value: str) -> str:
    host = urlparse(value).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if host in {"x.com", "twitter.com"} or host.endswith(".x.com") or host.endswith(".twitter.com"):
        return "x"
    if "xiaohongshu.com" in host:
        return "xiaohongshu"
    if "douyin.com" in host:
        return "douyin"
    if "bilibili.com" in host:
        return "bilibili"
    if host:
        return "web_video"
    return "unknown"


def support_for_platform(platform: str) -> dict[str, str]:
    matrix = {
        "youtube": {
            "success_estimate": "medium-high",
            "primary_paths": "official subtitles, auto subtitles, yt-dlp audio, cookies-assisted acquisition, local ASR",
            "user_actions": "May need exported cookies.txt for bot/sign-in blocks.",
            "full_report": "yes, when subtitles or ASR transcript are acquired",
        },
        "x": {
            "success_estimate": "low-medium",
            "primary_paths": "media acquisition when public and accessible; otherwise user-provided media/transcript",
            "user_actions": "May need browser inspection or user-provided material.",
            "full_report": "unstable; degraded output is common",
        },
        "xiaohongshu": {
            "success_estimate": "low",
            "primary_paths": "user-provided transcript, subtitle, screen recording, or local media",
            "user_actions": "Usually needs user-provided primary material.",
            "full_report": "low unless primary material is provided",
        },
        "douyin": {
            "success_estimate": "low",
            "primary_paths": "user-provided transcript, subtitle, screen recording, or local media",
            "user_actions": "Usually needs user-provided primary material.",
            "full_report": "low unless primary material is provided",
        },
        "bilibili": {
            "success_estimate": "medium",
            "primary_paths": "subtitles when available, audio/video acquisition, local ASR",
            "user_actions": "May need cookies or user-provided media depending on access.",
            "full_report": "yes, when subtitles or ASR transcript are acquired",
        },
        "web_video": {
            "success_estimate": "medium",
            "primary_paths": "visible transcript, page media/subtitle assets, local ASR",
            "user_actions": "May need Chrome page inspection or user-provided media.",
            "full_report": "depends on primary material acquisition",
        },
    }
    return matrix.get(
        platform,
        {
            "success_estimate": "unknown",
            "primary_paths": "existing transcript/subtitle, local media, or user-provided material",
            "user_actions": "Provide primary material if acquisition fails.",
            "full_report": "unknown until source gate runs",
        },
    )


def build_preflight(args: argparse.Namespace) -> dict[str, Any]:
    input_kind = detect_input_kind(args.input)
    platform = detect_platform(args.input) if input_kind == "url" else "local"
    mode = args.mode
    support = support_for_platform(platform)

    if input_kind == "transcript_or_subtitle":
        route = "normalize_transcript_then_decompose"
        estimate = "high"
        user_actions = "Ensure the file is readable UTF-8 text, SRT, VTT, JSONL, or supported JSON."
        can_full = "likely yes, after source gate and evidence audit"
    elif input_kind == "media":
        route = "local_asr_then_decompose"
        estimate = "medium-high"
        user_actions = "Ensure ffmpeg/ffprobe and faster-whisper are installed, or provide an existing transcript."
        can_full = "yes, if ASR succeeds with usable transcript coverage"
    elif input_kind == "url":
        route = "agent_reach_acquisition_bundle_then_source_gate"
        estimate = support["success_estimate"]
        user_actions = support["user_actions"]
        can_full = support["full_report"]
    else:
        route = "request_clarification_or_primary_material"
        estimate = "unknown"
        user_actions = "Provide a URL, transcript/subtitle file, or local audio/video file."
        can_full = "unknown"

    allowed_outputs = {
        "quick": ["preflight summary", "degraded/secondary source notes when no primary material exists"],
        "standard": ["video_analysis_pack when source gate allows", "partial/degraded report when source gate does not allow full analysis"],
        "audit": ["video_analysis_pack", "document planning", "quality_gate.json", "final_report.md when approved"],
    }[mode]

    return {
        "runner": RUNNER_NAME,
        "input": args.input,
        "input_kind": input_kind,
        "platform": platform,
        "requested_mode": mode,
        "estimated_success": estimate,
        "route": route,
        "primary_material_policy": "No full video analysis without transcript, subtitles, browser-visible transcript, or transcribable media.",
        "possible_primary_paths": support.get("primary_paths") if input_kind == "url" else route,
        "user_action_likely": user_actions,
        "full_report_possible": can_full,
        "allowed_outputs": allowed_outputs,
        "next_step": next_step_for(input_kind, mode),
    }


def next_step_for(input_kind: str, mode: str) -> str:
    if input_kind == "url":
        return "Run Agent-Reach doctor, create an acquisition bundle, then ingest through the source gate."
    if input_kind == "media":
        return "Run doctor, then local ASR; continue only if transcript artifacts are produced."
    if input_kind == "transcript_or_subtitle":
        return "Normalize transcript/subtitle and continue through the selected workflow mode."
    if mode == "quick":
        return "Ask for a clearer URL or file, or produce a clearly labeled non-primary quick triage."
    return "Ask the user for primary material before analysis."


def emit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Workflow Preflight",
        "",
        f"- Input kind: `{payload['input_kind']}`",
        f"- Platform: `{payload['platform']}`",
        f"- Requested mode: `{payload['requested_mode']}`",
        f"- Estimated success: `{payload['estimated_success']}`",
        f"- Route: `{payload['route']}`",
        f"- Full report possible: {payload['full_report_possible']}",
        f"- User action likely: {payload['user_action_likely']}",
        f"- Next step: {payload['next_step']}",
        "",
        "## Primary Material Policy",
        "",
        payload["primary_material_policy"],
        "",
        "## Allowed Outputs",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["allowed_outputs"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a preflight plan for a knowledge workflow input.")
    parser.add_argument("--input", help="URL, transcript/subtitle path, or media path.")
    parser.add_argument("--mode", choices=["quick", "standard", "audit"], default="standard")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        samples = [
            ("https://www.youtube.com/watch?v=abc", "standard", "url", "youtube"),
            ("sample.srt", "audit", "transcript_or_subtitle", "local"),
            ("sample.mp4", "standard", "media", "local"),
        ]
        for value, mode, expected_kind, expected_platform in samples:
            payload = build_preflight(argparse.Namespace(input=value, mode=mode))
            assert payload["input_kind"] == expected_kind, payload
            assert payload["platform"] == expected_platform, payload
        print("workflow_preflight self-test passed")
        return 0

    if not args.input:
        parser.error("--input is required unless --self-test is used")
    payload = build_preflight(args)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(emit_markdown(payload), encoding="utf-8")
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
