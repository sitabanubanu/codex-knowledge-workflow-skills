#!/usr/bin/env python
"""Acquire platform subtitles or audio as the first-hand material bridge.

This runner is intentionally conservative: downloaded audio is recorded as
pending ASR material, not as source-confirmed transcript evidence. Only an
acquired subtitle/transcript file, or a later successful ASR run, may open the
full decomposition gate.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import acquisition_runner
from write_artifact import ArtifactWriteError, write_artifact


RUNNER_NAME = "knowledge-video-platform-media-runner"
AUDIO_SUFFIXES = {".m4a", ".mp3", ".webm", ".opus", ".ogg", ".wav", ".aac", ".flac"}
DEFAULT_AUDIO_FORMAT_SELECTOR = "bestaudio/best"
DEFAULT_AUDIO_FORMAT = "mp3"


class PlatformMediaRunnerError(Exception):
    """Expected CLI-facing platform media runner failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_json(payload: dict[str, Any], *, pretty: bool) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))


def write_json(path: Path, payload: Any) -> dict[str, Any]:
    return write_artifact(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2),
        json_mode=True,
        mkdirs=True,
        overwrite=True,
    )


def write_text(path: Path, text: str) -> dict[str, Any]:
    return write_artifact(path, text, mkdirs=True, overwrite=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise PlatformMediaRunnerError(f"invalid JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise PlatformMediaRunnerError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PlatformMediaRunnerError(f"JSON file is not an object: {path}")
    return payload


def make_acquisition_args(args: argparse.Namespace, *, download_subtitles: bool) -> argparse.Namespace:
    return argparse.Namespace(
        input=args.input,
        output_root=args.output_root,
        youtube_cookies=args.youtube_cookies,
        ytdlp=args.ytdlp,
        node=args.node,
        timeout_seconds=args.timeout_seconds,
        no_doctor=args.no_doctor,
        list_subtitles=True,
        list_formats=True,
        use_js_runtime=args.use_js_runtime,
        use_remote_components=args.use_remote_components,
        download_subtitles=download_subtitles,
        subtitle_languages=args.subtitle_languages,
        pretty=False,
        self_test=False,
    )


def run_acquisition(args: argparse.Namespace, *, download_subtitles: bool) -> dict[str, Any]:
    return acquisition_runner.run_acquisition(make_acquisition_args(args, download_subtitles=download_subtitles))


def load_acquisition_report(output_root: Path) -> dict[str, Any]:
    return read_json(output_root / "00_source" / "acquisition_runner_report.json")


def existing_audio_files(audio_dir: Path) -> dict[Path, tuple[int, float]]:
    if not audio_dir.exists():
        return {}
    return {
        path.resolve(): (path.stat().st_size, path.stat().st_mtime)
        for path in audio_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_SUFFIXES
    }


def new_audio_files(audio_dir: Path, before: dict[Path, tuple[int, float]]) -> list[Path]:
    if not audio_dir.exists():
        return []
    files: list[Path] = []
    for path in audio_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in AUDIO_SUFFIXES or path.stat().st_size <= 0:
            continue
        resolved = path.resolve()
        previous = before.get(resolved)
        if previous is None or path.stat().st_size != previous[0] or path.stat().st_mtime > previous[1]:
            files.append(path)
    return sorted(files)


def build_audio_command(args: argparse.Namespace, audio_dir: Path) -> tuple[list[str], bool, bool, bool]:
    ytdlp = acquisition_runner.resolve_ytdlp(args.ytdlp)
    if ytdlp is None:
        raise PlatformMediaRunnerError("yt-dlp was not found; run doctor.py and install or expose yt-dlp first.")

    command = [
        str(ytdlp),
        "--no-playlist",
        "-f",
        args.audio_format_selector,
        "--extract-audio",
        "--audio-format",
        args.audio_format,
        "-o",
        str(audio_dir / "%(id)s.%(ext)s"),
    ]

    cookies_used = False
    if args.youtube_cookies:
        cookies_path = Path(args.youtube_cookies).expanduser().resolve()
        if not cookies_path.is_file():
            raise PlatformMediaRunnerError(f"cookies file was not found: {cookies_path}")
        command.extend(["--cookies", str(cookies_path)])
        cookies_used = True

    js_used = False
    if args.use_js_runtime:
        node = acquisition_runner.resolve_node(args.node)
        if node is not None and node.is_file():
            command.extend(["--js-runtimes", f"node:{node}"])
            js_used = True

    remote_used = False
    if args.use_remote_components:
        command.extend(["--remote-components", "ejs:github"])
        remote_used = True

    command.append(args.input)
    return command, cookies_used, js_used, remote_used


def should_try_audio(args: argparse.Namespace, acquisition_summary: dict[str, Any], report: dict[str, Any]) -> tuple[bool, str]:
    if args.mode == "probe":
        return False, "probe_mode_only"
    if args.mode == "subtitles":
        return False, "subtitle_mode_only"

    status = str(acquisition_summary.get("source_status") or "")
    if status == "source_confirmed":
        return False, "subtitle_or_transcript_already_acquired"
    if status == "source_blocked":
        return False, "source_blocked_requires_chrome_or_user_material"

    metadata = report.get("metadata_summary") if isinstance(report.get("metadata_summary"), dict) else {}
    media_formats_listed = bool(metadata.get("media_formats_listed"))
    if args.mode == "audio":
        return True, "audio_mode_requested"
    if media_formats_listed:
        return True, "media_formats_listed"
    return False, "no_media_formats_listed"


def download_audio(args: argparse.Namespace, output_root: Path) -> tuple[dict[str, Any], list[Path]]:
    audio_dir = output_root / "00_source" / "raw" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    before = existing_audio_files(audio_dir)
    command, cookies_used, js_used, remote_used = build_audio_command(args, audio_dir)
    result = acquisition_runner.run_command(
        name="yt_dlp_download_audio",
        command_kind="yt-dlp:download-audio",
        args=command,
        timeout_seconds=args.timeout_seconds,
        raw_dir=output_root / "00_source" / "raw",
        cookies_used=cookies_used,
        js_runtime_used=js_used,
        remote_components_used=remote_used,
    )
    files = new_audio_files(audio_dir, before) if result.returncode == 0 else []
    return result.as_dict(), files


def mark_audio_pending(output_root: Path, audio_files: list[Path]) -> dict[str, Any]:
    status_path = output_root / "00_source" / "source_status.json"
    status = read_json(status_path)
    status["primary_material_available"] = False
    status["can_enter_full_decomposition"] = False
    status["can_enter_document_composer"] = False
    status["next_step"] = "run_asr_pipeline_on_acquired_audio"
    status["pending_primary_media_for_asr"] = [str(path.resolve()) for path in audio_files]
    status["pending_source_classes"] = ["primary_audio_asr_after_successful_asr"]
    status["status_reason"] = (
        f"{status.get('status_reason', '').strip()} Local audio was acquired, but it has not yet been "
        "transcribed. Full decomposition remains closed until asr_pipeline.py produces transcript artifacts."
    ).strip()
    cost_limits = status.setdefault("cost_limits", {})
    if isinstance(cost_limits, dict):
        cost_limits["media_extraction_performed"] = True
    write_json(status_path, status)
    return status


def material_decision(status: dict[str, Any], acquired_subtitles: list[str], acquired_audio: list[str]) -> dict[str, Any]:
    if acquired_subtitles:
        return {
            "material_state": "subtitle_acquired",
            "next_step": "normalize_acquired_subtitle",
            "can_enter_full_decomposition": bool(status.get("can_enter_full_decomposition")),
        }
    if acquired_audio:
        return {
            "material_state": "audio_acquired_pending_asr",
            "next_step": "run_asr_pipeline_on_acquired_audio",
            "can_enter_full_decomposition": False,
        }
    return {
        "material_state": "no_primary_material_acquired",
        "next_step": str(status.get("next_step") or "request_primary_material_or_chrome_deep_probe"),
        "can_enter_full_decomposition": False,
    }


def render_notes(result: dict[str, Any]) -> str:
    lines = [
        "# Platform Media Runner Notes",
        "",
        f"- Runner: `{RUNNER_NAME}`",
        f"- Input: `{result['input']}`",
        f"- Mode: `{result['mode']}`",
        f"- Source status: `{result['source_status']['source_status']}`",
        f"- Material state: `{result['decision']['material_state']}`",
        f"- Next step: `{result['decision']['next_step']}`",
        "",
        "## Acquired Material",
        "",
    ]
    subtitles = result.get("acquired_subtitle_files") or []
    audio = result.get("acquired_audio_files") or []
    lines.append("- Subtitles:")
    lines.extend(f"  - `{item}`" for item in subtitles) if subtitles else lines.append("  - None")
    lines.append("- Audio:")
    lines.extend(f"  - `{item}`" for item in audio) if audio else lines.append("  - None")
    lines.extend(
        [
            "",
            "## Gate Boundary",
            "",
            "- Downloaded subtitles may be normalized as primary transcript material.",
            "- Downloaded audio is pending ASR and must not be treated as transcript evidence yet.",
            "- Metadata, listed formats, and discovered URLs do not unlock full decomposition by themselves.",
            "",
        ]
    )
    if result.get("audio_download"):
        item = result["audio_download"]
        lines.extend(
            [
                "## Audio Download Attempt",
                "",
                f"- Return code: `{item.get('returncode')}`",
                f"- Timeout: `{item.get('timeout')}`",
                f"- Cookies used: `{item.get('cookies_used')}`",
                f"- JavaScript runtime used: `{item.get('js_runtime_used')}`",
                f"- Remote components used: `{item.get('remote_components_used')}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_platform_media(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.expanduser().resolve()
    if acquisition_runner.classify_source(args.input)["input_kind"] != "url":
        raise PlatformMediaRunnerError("platform media runner requires a platform URL input.")

    download_subtitles = args.mode in {"auto", "subtitles"}
    acquisition_summary = run_acquisition(args, download_subtitles=download_subtitles)
    report = load_acquisition_report(output_root)
    acquired_subtitles = list(report.get("acquired_subtitle_files") or [])

    acquired_audio: list[Path] = []
    audio_download: dict[str, Any] | None = None
    try_audio, audio_reason = should_try_audio(args, acquisition_summary, report)
    if try_audio:
        audio_download, acquired_audio = download_audio(args, output_root)

    status = read_json(output_root / "00_source" / "source_status.json")
    if acquired_audio:
        status = mark_audio_pending(output_root, acquired_audio)

    acquired_audio_strings = [str(path.resolve()) for path in acquired_audio]
    decision = material_decision(status, acquired_subtitles, acquired_audio_strings)
    result = {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "input": args.input,
        "mode": args.mode,
        "output_root": str(output_root),
        "source_status": status,
        "acquisition_summary": acquisition_summary,
        "acquired_subtitle_files": acquired_subtitles,
        "acquired_audio_files": acquired_audio_strings,
        "audio_attempt_reason": audio_reason,
        "audio_download": audio_download,
        "decision": decision,
        "privacy": {
            "cookie_values_reported": False,
            "cookies_used": bool(args.youtube_cookies) or bool(report.get("privacy", {}).get("cookies_used")),
            "js_runtime_used": bool(args.use_js_runtime),
            "remote_components_used": bool(args.use_remote_components),
        },
    }
    write_json(output_root / "00_source" / "platform_media_result.json", result)
    write_text(output_root / "00_source" / "platform_media_notes.md", render_notes(result))
    return {
        "runner": RUNNER_NAME,
        "output_root": str(output_root),
        "source_status": status.get("source_status"),
        "material_state": decision["material_state"],
        "next_step": decision["next_step"],
        "can_enter_full_decomposition": decision["can_enter_full_decomposition"],
        "acquired_subtitle_files": acquired_subtitles,
        "acquired_audio_files": acquired_audio_strings,
        "audio_attempt_reason": audio_reason,
        "files_written": [
            str((output_root / "00_source" / "platform_media_result.json").resolve()),
            str((output_root / "00_source" / "platform_media_notes.md").resolve()),
        ],
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Acquire platform subtitles first, then audio for ASR when needed.")
    parser.add_argument("--input", required=False, help="Platform video URL.")
    parser.add_argument("--output-root", type=Path, default=None, help="10_video artifact root.")
    parser.add_argument("--mode", choices=["auto", "probe", "subtitles", "audio"], default="auto")
    parser.add_argument("--youtube-cookies", default=None, help="Path to user-exported Netscape cookies.txt.")
    parser.add_argument("--ytdlp", default=None, help="Optional yt-dlp executable override.")
    parser.add_argument("--node", default=None, help="Optional Node.js executable override.")
    parser.add_argument("--timeout-seconds", type=int, default=acquisition_runner.DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--no-doctor", action="store_true", help="Skip local doctor report.")
    parser.add_argument("--use-js-runtime", action="store_true", help="Pass Node.js to yt-dlp for player challenge solving.")
    parser.add_argument("--use-remote-components", action="store_true", help="Allow yt-dlp remote ejs solver component.")
    parser.add_argument("--subtitle-languages", default="all,-live_chat")
    parser.add_argument("--audio-format-selector", default=DEFAULT_AUDIO_FORMAT_SELECTOR)
    parser.add_argument("--audio-format", default=DEFAULT_AUDIO_FORMAT)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in offline tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def run_self_test() -> int:
    failures: list[str] = []
    secondary = {
        "source_status": "secondary_only",
        "can_enter_full_decomposition": False,
        "can_enter_document_composer": True,
        "allowed_report_type": "degraded_source_report",
        "source_classes": ["platform_metadata"],
        "primary_material_available": False,
        "status_reason": "metadata only.",
        "failed_probes": [],
        "next_step": "download_audio_then_run_local_asr",
    }
    assert_true(
        "subtitle decision",
        material_decision({"can_enter_full_decomposition": True, "next_step": "enter_normalizer"}, ["a.srt"], [])[
            "material_state"
        ]
        == "subtitle_acquired",
        failures,
    )
    assert_true(
        "audio decision keeps gate closed",
        material_decision(secondary, [], ["a.mp3"])["can_enter_full_decomposition"] is False,
        failures,
    )
    with tempfile.TemporaryDirectory(prefix="platform-media-runner-") as tmp:
        root = Path(tmp) / "10_video"
        write_json(root / "00_source" / "source_status.json", secondary)
        audio = root / "00_source" / "raw" / "audio" / "fixture.mp3"
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(b"not real audio but non-empty")
        updated = mark_audio_pending(root, [audio])
        assert_true("pending audio recorded", "pending_primary_media_for_asr" in updated, failures)
        assert_true("pending audio not primary", updated["primary_material_available"] is False, failures)
        assert_true("pending audio gate closed", updated["can_enter_full_decomposition"] is False, failures)
        assert_true("no primary_audio_asr before ASR", "primary_audio_asr" not in updated.get("source_classes", []), failures)

    original_run_acquisition = globals()["run_acquisition"]
    original_load_acquisition_report = globals()["load_acquisition_report"]
    original_download_audio = globals()["download_audio"]
    try:
        with tempfile.TemporaryDirectory(prefix="platform-media-flow-") as tmp:
            root = Path(tmp) / "10_video"

            def fake_run_acquisition(args: argparse.Namespace, *, download_subtitles: bool) -> dict[str, Any]:
                write_json(root / "00_source" / "source_status.json", secondary)
                return {
                    "runner": "fake-acquisition",
                    "source_status": "secondary_only",
                    "can_enter_full_decomposition": False,
                    "primary_material_available": False,
                    "next_step": "download_audio_then_run_local_asr",
                }

            def fake_load_acquisition_report(output_root: Path) -> dict[str, Any]:
                return {
                    "acquired_subtitle_files": [],
                    "metadata_summary": {"media_formats_listed": True},
                    "privacy": {"cookies_used": False},
                }

            def fake_download_audio(args: argparse.Namespace, output_root: Path) -> tuple[dict[str, Any], list[Path]]:
                audio_path = output_root / "00_source" / "raw" / "audio" / "fake.mp3"
                audio_path.parent.mkdir(parents=True, exist_ok=True)
                audio_path.write_bytes(b"fake audio")
                return (
                    {
                        "name": "yt_dlp_download_audio",
                        "returncode": 0,
                        "timeout": False,
                        "cookies_used": False,
                        "js_runtime_used": False,
                        "remote_components_used": False,
                    },
                    [audio_path],
                )

            globals()["run_acquisition"] = fake_run_acquisition
            globals()["load_acquisition_report"] = fake_load_acquisition_report
            globals()["download_audio"] = fake_download_audio
            flow = run_platform_media(
                argparse.Namespace(
                    input="https://www.youtube.com/watch?v=fake",
                    output_root=root,
                    mode="auto",
                    youtube_cookies=None,
                    ytdlp=None,
                    node=None,
                    timeout_seconds=1,
                    no_doctor=True,
                    use_js_runtime=False,
                    use_remote_components=False,
                    subtitle_languages="all,-live_chat",
                    audio_format_selector=DEFAULT_AUDIO_FORMAT_SELECTOR,
                    audio_format=DEFAULT_AUDIO_FORMAT,
                    pretty=False,
                )
            )
            assert_true("flow audio pending", flow["material_state"] == "audio_acquired_pending_asr", failures)
            assert_true("flow gate closed", flow["can_enter_full_decomposition"] is False, failures)
            flow_status = read_json(root / "00_source" / "source_status.json")
            assert_true("flow status has pending audio", bool(flow_status.get("pending_primary_media_for_asr")), failures)
            assert_true("flow status not source confirmed", flow_status.get("source_status") != "source_confirmed", failures)
            assert_true("flow result written", (root / "00_source" / "platform_media_result.json").is_file(), failures)
    finally:
        globals()["run_acquisition"] = original_run_acquisition
        globals()["load_acquisition_report"] = original_load_acquisition_report
        globals()["download_audio"] = original_download_audio
    if failures:
        for failure in failures:
            print(failure, file=os.sys.stderr)
        return 1
    print("platform_media_runner self-test passed")
    return 0


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    if args.output_root is None:
        parser.error("--output-root is required unless --self-test is used")
    try:
        summary = run_platform_media(args)
    except (PlatformMediaRunnerError, acquisition_runner.AcquisitionRunnerError, ArtifactWriteError, OSError) as exc:
        emit_json({"runner": RUNNER_NAME, "ok": False, "error": str(exc)}, pretty=args.pretty)
        return 1
    emit_json(summary, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
