#!/usr/bin/env python
"""Normalize Chrome deep-probe observations into machine-readable artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from write_artifact import write_artifact


RUNNER_NAME = "knowledge-video-chrome-media-probe"
LAYER_ORDER = [
    "visible_transcript",
    "pageAssets_list",
    "pageAssets_bundle",
    "playwright_evaluate",
    "network_media_inspection",
]
VISIBLE_TRANSCRIPT_STATUSES = {"available", "partial", "not_visible", "not_checked", "blocked", "unknown"}
PAGE_STATES = {
    "opened",
    "failed_to_open",
    "login_required",
    "captcha_required",
    "paywalled",
    "permission_required",
    "video_unavailable",
    "metadata_only",
    "unknown",
}
MEDIA_SUFFIXES = {".vtt", ".srt", ".sbv", ".json3", ".xml", ".mp4", ".m4a", ".mp3", ".wav", ".webm", ".mkv", ".mov", ".aac", ".flac", ".ogg", ".opus"}
SUBTITLE_SUFFIXES = {".vtt", ".srt", ".sbv", ".json3", ".xml"}
BLOCKED_PAGE_STATES = {"login_required", "captcha_required", "paywalled", "permission_required", "video_unavailable"}


class ChromeMediaProbeError(Exception):
    """Expected CLI-facing Chrome media probe failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def write_json(path: Path, payload: Any) -> dict[str, Any]:
    return write_artifact(path, json.dumps(payload, ensure_ascii=False, indent=2), json_mode=True, mkdirs=True, overwrite=True)


def write_text(path: Path, text: str) -> dict[str, Any]:
    return write_artifact(path, text, mkdirs=True, overwrite=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ChromeMediaProbeError(f"invalid JSON input: {exc}") from exc
    except OSError as exc:
        raise ChromeMediaProbeError(f"could not read input JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ChromeMediaProbeError("input JSON must be an object")
    return payload


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def compact(text: Any, limit: int = 240) -> str:
    value = " ".join(str(text or "").split())
    if len(value) > limit:
        return value[: limit - 3].rstrip() + "..."
    return value


def suffix_for(path_or_url: str) -> str:
    clean = path_or_url.split("?", 1)[0].split("#", 1)[0]
    return Path(clean).suffix.lower()


def normalize_layer(raw: dict[str, Any], index: int) -> dict[str, Any]:
    layer = str(raw.get("layer") or raw.get("name") or "").strip()
    if layer not in LAYER_ORDER:
        raise ChromeMediaProbeError(f"layer {index} has unknown layer name {layer!r}; allowed: {', '.join(LAYER_ORDER)}")
    local_files = [str(item) for item in as_list(raw.get("local_files")) if str(item).strip()]
    public_urls = [str(item) for item in as_list(raw.get("public_urls")) if str(item).strip()]
    asset_kinds = [str(item) for item in as_list(raw.get("asset_kinds")) if str(item).strip()]
    executed = as_bool(raw.get("executed"), default=bool(raw.get("result") or local_files or public_urls or asset_kinds))
    media_like_files = [item for item in local_files if suffix_for(item) in MEDIA_SUFFIXES]
    subtitle_files = [item for item in local_files if suffix_for(item) in SUBTITLE_SUFFIXES]
    media_like_urls = [item for item in public_urls if suffix_for(item) in MEDIA_SUFFIXES]
    confirmed_public_downloadable = as_bool(raw.get("confirmed_public_downloadable"), default=False)
    return {
        "layer": layer,
        "executed": executed,
        "result": str(raw.get("result") or ("success" if media_like_files or media_like_urls else "not_found")),
        "asset_kinds": asset_kinds,
        "media_found": as_bool(raw.get("media_found"), default=bool(media_like_files or media_like_urls)),
        "local_files": local_files,
        "subtitle_files": subtitle_files,
        "media_files": media_like_files,
        "public_urls": public_urls,
        "media_urls": media_like_urls,
        "confirmed_public_downloadable": confirmed_public_downloadable,
        "notes": compact(raw.get("notes")),
    }


def normalize_layers(input_payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_layers = as_list(input_payload.get("layers") or input_payload.get("deep_probe_layers"))
    layers = [normalize_layer(item, index) for index, item in enumerate(raw_layers, start=1) if isinstance(item, dict)]
    seen = {layer["layer"] for layer in layers}
    for layer in LAYER_ORDER:
        if layer not in seen:
            layers.append(
                {
                    "layer": layer,
                    "executed": False,
                    "result": "not_run",
                    "asset_kinds": [],
                    "media_found": False,
                    "local_files": [],
                    "subtitle_files": [],
                    "media_files": [],
                    "public_urls": [],
                    "media_urls": [],
                    "confirmed_public_downloadable": False,
                    "notes": "",
                }
            )
    return sorted(layers, key=lambda item: LAYER_ORDER.index(item["layer"]))


def derive_decision(payload: dict[str, Any], layers: list[dict[str, Any]]) -> dict[str, Any]:
    visible_status = str(payload.get("visible_transcript_status") or "unknown")
    if visible_status not in VISIBLE_TRANSCRIPT_STATUSES:
        visible_status = "unknown"
    page_state = str(payload.get("page_state_observed") or "unknown")
    if page_state not in PAGE_STATES:
        page_state = "unknown"

    executed_layers = [layer["layer"] for layer in layers if layer["executed"]]
    all_layers_executed = set(executed_layers) == set(LAYER_ORDER)
    local_media_files = [file for layer in layers for file in layer["media_files"]]
    subtitle_files = [file for layer in layers for file in layer["subtitle_files"]]
    confirmed_public_urls = [
        url
        for layer in layers
        if layer["confirmed_public_downloadable"]
        for url in layer["media_urls"]
    ]
    browser_derived_media_exported = bool(local_media_files)
    deep_probe_media_found = browser_derived_media_exported or bool(confirmed_public_urls)
    blocked = page_state in BLOCKED_PAGE_STATES or visible_status == "blocked"
    exhausted = all_layers_executed and not deep_probe_media_found and visible_status not in {"available", "partial"} and not blocked

    if visible_status == "available":
        source_signal = "chrome_visible_transcript"
        next_step = "capture_visible_transcript_then_normalize"
        status_hint = "source_confirmed"
    elif visible_status == "partial":
        source_signal = "partial_transcript"
        next_step = "capture_partial_visible_transcript_then_normalize"
        status_hint = "source_partial"
    elif deep_probe_media_found:
        source_signal = "browser_derived_media_acquired"
        next_step = "parse_subtitle_or_run_asr_pipeline"
        status_hint = "source_confirmed"
    elif blocked:
        source_signal = {
            "login_required": "login_required",
            "captcha_required": "captcha",
            "paywalled": "paywall",
            "permission_required": "permission_required",
            "video_unavailable": "tool_failed",
        }.get(page_state, "request_blocked")
        next_step = "enter_source_blocked_or_request_user_authorization"
        status_hint = "source_blocked"
    elif exhausted:
        source_signal = "chrome_deep_probe_exhausted"
        next_step = "request_primary_transcript_audio_or_user_file"
        status_hint = "source_failed"
    else:
        source_signal = "chrome_no_transcript"
        next_step = "continue_chrome_deep_probe_or_record_incomplete_probe"
        status_hint = "source_failed"

    return {
        "visible_transcript_status": visible_status,
        "page_state_observed": page_state,
        "chrome_deep_probe_exhausted": exhausted,
        "deep_probe_layers_executed": executed_layers,
        "deep_probe_media_found": deep_probe_media_found,
        "browser_derived_media_exported": browser_derived_media_exported,
        "local_media_files": local_media_files,
        "subtitle_files": subtitle_files,
        "confirmed_public_media_or_subtitle_urls": confirmed_public_urls,
        "suggested_acquisition_signal": source_signal,
        "suggested_source_status": status_hint,
        "next_step": next_step,
    }


def render_report(probe: dict[str, Any]) -> str:
    lines = [
        "# Chrome Media Probe",
        "",
        f"- URL: {probe.get('source_url') or 'not recorded'}",
        f"- Chrome route used: `{str(probe['chrome_route_used']).lower()}`",
        f"- Page state: `{probe['decision']['page_state_observed']}`",
        f"- Visible transcript: `{probe['decision']['visible_transcript_status']}`",
        f"- Deep probe exhausted: `{str(probe['decision']['chrome_deep_probe_exhausted']).lower()}`",
        f"- Media found: `{str(probe['decision']['deep_probe_media_found']).lower()}`",
        f"- Browser-derived media exported: `{str(probe['decision']['browser_derived_media_exported']).lower()}`",
        f"- Suggested signal: `{probe['decision']['suggested_acquisition_signal']}`",
        f"- Next step: `{probe['decision']['next_step']}`",
        "",
        "## Layers",
        "",
    ]
    for layer in probe["layers"]:
        lines.extend(
            [
                f"### {layer['layer']}",
                "",
                f"- Executed: `{str(layer['executed']).lower()}`",
                f"- Result: `{layer['result']}`",
                f"- Media found: `{str(layer['media_found']).lower()}`",
                f"- Local files: `{layer['local_files']}`",
                f"- Public URLs: `{layer['public_urls']}`",
                f"- Notes: {layer['notes'] or 'None.'}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- Page playability alone is not primary material.",
            "- Browser-derived media requires an actual local file or confirmed public downloadable URL that can be fetched and processed.",
            "- Restricted signed playback URLs, CAPTCHA, paywall, or permission escalation must be treated as blocked.",
            "",
        ]
    )
    return "\n".join(lines)


def run_chrome_media_probe(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.expanduser().resolve()
    payload = read_json(args.input_json)
    layers = normalize_layers(payload)
    decision = derive_decision(payload, layers)
    probe = {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "source_url": payload.get("source_url") or payload.get("url") or "",
        "title": payload.get("title") or "",
        "trigger_reason": payload.get("trigger_reason") or "",
        "chrome_route_used": as_bool(payload.get("chrome_route_used"), default=True),
        "yt_dlp_chrome_cookies_attempted": as_bool(payload.get("yt_dlp_chrome_cookies_attempted"), default=False),
        "yt_dlp_chrome_cookies_succeeded": as_bool(payload.get("yt_dlp_chrome_cookies_succeeded"), default=False),
        "why_chrome_was_or_was_not_used": payload.get("why_chrome_was_or_was_not_used") or payload.get("trigger_reason") or "",
        "layers": layers,
        "decision": decision,
        "acquisition_probe_hint": {
            "probe": "Chrome",
            "signal": decision["suggested_acquisition_signal"],
            "source_status_hint": decision["suggested_source_status"],
            "next_step": decision["next_step"],
        },
    }
    written = [
        write_json(output_root / "00_source" / "chrome_media_probe.json", probe),
        write_text(output_root / "00_source" / "chrome_media_probe.md", render_report(probe)),
    ]
    return {
        "runner": RUNNER_NAME,
        "output_root": str(output_root),
        "source_url": probe["source_url"],
        "chrome_route_used": probe["chrome_route_used"],
        "visible_transcript_status": decision["visible_transcript_status"],
        "page_state_observed": decision["page_state_observed"],
        "chrome_deep_probe_exhausted": decision["chrome_deep_probe_exhausted"],
        "deep_probe_layers_executed": decision["deep_probe_layers_executed"],
        "deep_probe_media_found": decision["deep_probe_media_found"],
        "browser_derived_media_exported": decision["browser_derived_media_exported"],
        "suggested_acquisition_signal": decision["suggested_acquisition_signal"],
        "suggested_source_status": decision["suggested_source_status"],
        "files_written": [item["path"] for item in written],
        "next_step": decision["next_step"],
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize Chrome deep-probe observations.")
    parser.add_argument("--input-json", type=Path, required=False, help="JSON file containing Chrome probe observations.")
    parser.add_argument("--output-root", type=Path, required=False, help="10_video artifact root.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def run_fixture(base: Path, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    input_path = base / f"{name}.json"
    output_root = base / name / "10_video"
    write_json(input_path, payload)
    return run_chrome_media_probe(argparse.Namespace(input_json=input_path, output_root=output_root))


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="chrome-media-probe-") as tmp:
        base = Path(tmp)

        visible = run_fixture(
            base,
            "visible",
            {
                "source_url": "https://example.invalid/video",
                "visible_transcript_status": "available",
                "page_state_observed": "opened",
                "layers": [{"layer": "visible_transcript", "executed": True, "result": "success"}],
            },
        )
        assert_true("visible signal", visible["suggested_acquisition_signal"] == "chrome_visible_transcript", failures)
        assert_true("visible not exhausted", visible["chrome_deep_probe_exhausted"] is False, failures)

        exported = run_fixture(
            base,
            "exported",
            {
                "source_url": "https://example.invalid/video",
                "visible_transcript_status": "not_visible",
                "page_state_observed": "opened",
                "layers": [
                    {"layer": "visible_transcript", "executed": True, "result": "not_found"},
                    {"layer": "pageAssets_list", "executed": True, "result": "success", "asset_kinds": ["video", "stylesheet"]},
                    {"layer": "pageAssets_bundle", "executed": True, "result": "success", "local_files": ["C:/tmp/captions.vtt"]},
                ],
            },
        )
        assert_true("exported media", exported["browser_derived_media_exported"] is True, failures)
        assert_true("exported signal", exported["suggested_acquisition_signal"] == "browser_derived_media_acquired", failures)

        exhausted = run_fixture(
            base,
            "exhausted",
            {
                "visible_transcript_status": "not_visible",
                "page_state_observed": "opened",
                "layers": [{"layer": layer, "executed": True, "result": "not_found"} for layer in LAYER_ORDER],
            },
        )
        assert_true("exhausted true", exhausted["chrome_deep_probe_exhausted"] is True, failures)
        assert_true("exhausted signal", exhausted["suggested_acquisition_signal"] == "chrome_deep_probe_exhausted", failures)

        blocked = run_fixture(
            base,
            "blocked",
            {
                "visible_transcript_status": "blocked",
                "page_state_observed": "captcha_required",
                "layers": [{"layer": "visible_transcript", "executed": True, "result": "blocked"}],
            },
        )
        assert_true("blocked status", blocked["suggested_source_status"] == "source_blocked", failures)
        assert_true("blocked signal", blocked["suggested_acquisition_signal"] == "captcha", failures)

        try:
            run_fixture(base, "bad", {"layers": [{"layer": "unknown_layer", "executed": True}]})
        except ChromeMediaProbeError:
            pass
        else:
            failures.append("bad layer: expected ChromeMediaProbeError")

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

    if args.input_json is None or args.output_root is None:
        parser.error("--input-json and --output-root are required unless --self-test is used")

    try:
        summary = run_chrome_media_probe(args)
    except ChromeMediaProbeError as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "error": "chrome_media_probe_failed",
                "message": str(exc),
            },
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return 1

    emit_json(summary, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
