#!/usr/bin/env python
"""Probe platform video sources and write auditable acquisition state.

This runner performs bounded acquisition probes. By default it does not download
media and does not treat "subtitles/formats are listed" as primary material.
Only an actually acquired subtitle file, transcript file, or downstream ASR
output may unlock source-confirmed decomposition.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import acquisition_probe
import doctor
from write_artifact import ArtifactWriteError, write_artifact


RUNNER_NAME = "knowledge-video-acquisition-runner"
DEFAULT_TIMEOUT_SECONDS = 90


BLOCK_PATTERNS: list[tuple[str, str]] = [
    ("http_429", r"\b429\b|too many requests"),
    ("bot_check", r"sign in to confirm|confirm you.?re not a bot|not a bot|bot check|bot confirmation"),
    ("captcha", r"captcha"),
    ("login_required", r"login required|sign in required|please log in|authentication required"),
    ("permission_required", r"private video|permission|not available in your country|age-restricted|region"),
    ("request_blocked", r"requestblocked|request blocked|blocked from accessing"),
]

FAILURE_PATTERNS: list[tuple[str, str]] = [
    ("dpapi_or_app_bound_cookie_failure", r"dpapi|app-bound|app bound|could not copy chrome cookie|decrypt"),
    ("n_challenge_failed", r"n challenge|nsig|only images are available"),
    ("unsupported_url", r"unsupported url|no suitable extractor"),
]


@dataclass
class CommandResult:
    name: str
    command_kind: str
    returncode: int | None
    stdout: str
    stderr: str
    timeout: bool
    duration_seconds: float
    output_path: str | None = None
    cookies_used: bool = False
    js_runtime_used: bool = False
    remote_components_used: bool = False

    def combined_text(self) -> str:
        return f"{self.stdout}\n{self.stderr}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "command_kind": self.command_kind,
            "returncode": self.returncode,
            "timeout": self.timeout,
            "duration_seconds": round(self.duration_seconds, 3),
            "stdout_path": self.output_path,
            "stderr_path": self.output_path.replace(".stdout.txt", ".stderr.txt") if self.output_path else None,
            "cookies_used": self.cookies_used,
            "js_runtime_used": self.js_runtime_used,
            "remote_components_used": self.remote_components_used,
        }


class AcquisitionRunnerError(Exception):
    """Expected CLI-facing acquisition runner failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def write_json(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return write_artifact(path, json_text(payload), json_mode=True, mkdirs=True, overwrite=True)


def write_text(path: Path, text: str) -> dict[str, Any]:
    return write_artifact(path, text, mkdirs=True, overwrite=True)


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def classify_source(value: str) -> dict[str, str]:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        host = parsed.netloc.lower()
        if "youtube.com" in host or "youtu.be" in host:
            platform = "youtube"
        elif host == "x.com" or host.endswith(".x.com") or "twitter.com" in host:
            platform = "x"
        elif "xiaohongshu.com" in host or "xhslink.com" in host:
            platform = "xiaohongshu"
        elif "douyin.com" in host:
            platform = "douyin"
        else:
            platform = "generic_web"
        return {"source_type": "platform_url", "platform": platform, "input_kind": "url"}

    path = Path(value).expanduser()
    suffix = path.suffix.lower()
    if suffix in {".mp4", ".mkv", ".mov", ".webm", ".m4a", ".mp3", ".wav", ".aac", ".flac"}:
        return {"source_type": "local_media", "platform": "local_file", "input_kind": "local_media"}
    if suffix in {".txt", ".md", ".srt", ".vtt", ".json", ".jsonl"}:
        return {"source_type": "local_transcript", "platform": "local_file", "input_kind": "local_transcript"}
    return {"source_type": "unknown", "platform": "unknown", "input_kind": "unknown"}


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def resolve_ytdlp(explicit: str | None = None) -> Path | None:
    if explicit:
        candidate = Path(explicit).expanduser()
        return candidate if candidate.is_file() else None
    found = shutil.which("yt-dlp")
    if found:
        return Path(found)
    home = Path.home()
    return first_existing(
        [
            home / ".codex" / "tools" / "hearsay-venv" / "Scripts" / "yt-dlp.exe",
            home / ".codex" / "tools" / "VideoLingo" / ".venv" / "Scripts" / "yt-dlp.exe",
        ]
    )


def resolve_node(explicit: str | None = None) -> Path | None:
    if explicit:
        candidate = Path(explicit).expanduser()
        return candidate if candidate.is_file() else None
    found = shutil.which("node")
    if found:
        return Path(found)
    return (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "node"
        / "bin"
        / "node.exe"
    )


def run_command(
    *,
    name: str,
    command_kind: str,
    args: list[str],
    timeout_seconds: int,
    raw_dir: Path,
    cookies_used: bool = False,
    js_runtime_used: bool = False,
    remote_components_used: bool = False,
) -> CommandResult:
    start = datetime.now(timezone.utc)
    timeout = False
    returncode: int | None = None
    stdout = ""
    stderr = ""

    def decode_stream(value: bytes | str | None) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return value.decode("utf-8", "backslashreplace")

    try:
        proc = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            shell=False,
        )
        returncode = proc.returncode
        stdout = decode_stream(proc.stdout)
        stderr = decode_stream(proc.stderr)
    except subprocess.TimeoutExpired as exc:
        timeout = True
        stdout = decode_stream(exc.stdout)
        stderr = decode_stream(exc.stderr)
        stderr = f"{stderr}\nCommand timed out after {timeout_seconds}s".strip()

    duration = (datetime.now(timezone.utc) - start).total_seconds()
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "probe"
    stdout_path = raw_dir / f"{stem}.stdout.txt"
    stderr_path = raw_dir / f"{stem}.stderr.txt"
    write_text(stdout_path, stdout if stdout else "(empty)\n")
    write_text(stderr_path, stderr if stderr else "(empty)\n")
    return CommandResult(
        name=name,
        command_kind=command_kind,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timeout=timeout,
        duration_seconds=duration,
        output_path=str(stdout_path.resolve()),
        cookies_used=cookies_used,
        js_runtime_used=js_runtime_used,
        remote_components_used=remote_components_used,
    )


def extract_json(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(text[start : end + 1])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def detect_signals(results: list[CommandResult], metadata: dict[str, Any] | None, acquired_subtitles: list[Path]) -> set[str]:
    signals: set[str] = set()
    if acquired_subtitles:
        signals.add("transcript_available")
    if metadata:
        signals.add("metadata_available")
    for result in results:
        text = result.combined_text().lower()
        if result.timeout:
            signals.add("timeout")
        for signal, pattern in BLOCK_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                signals.add(signal)
        if result.returncode not in {0, None} and not metadata:
            signals.add("tool_failed")
        for signal, pattern in FAILURE_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                signals.add(signal)
    if not signals:
        signals.add("tool_failed")
    return signals


def subtitle_languages(metadata: dict[str, Any] | None) -> dict[str, list[str]]:
    if not metadata:
        return {"subtitles": [], "automatic_captions": []}
    subs = metadata.get("subtitles") if isinstance(metadata.get("subtitles"), dict) else {}
    autos = metadata.get("automatic_captions") if isinstance(metadata.get("automatic_captions"), dict) else {}
    return {
        "subtitles": sorted(str(key) for key in subs.keys()),
        "automatic_captions": sorted(str(key) for key in autos.keys()),
    }


def has_media_formats(metadata: dict[str, Any] | None) -> bool:
    if not metadata:
        return False
    formats = metadata.get("formats")
    return isinstance(formats, list) and any(isinstance(item, dict) and item.get("url") for item in formats)


def build_ytdlp_base(
    *,
    ytdlp: Path,
    url: str,
    cookies_path: Path | None,
    node_path: Path | None,
    use_remote_components: bool,
) -> tuple[list[str], bool, bool]:
    args = [str(ytdlp)]
    js_used = False
    remote_used = False
    if cookies_path is not None:
        args.extend(["--cookies", str(cookies_path)])
    if node_path is not None and node_path.is_file():
        args.extend(["--js-runtimes", f"node:{node_path}"])
        js_used = True
    if use_remote_components:
        args.extend(["--remote-components", "ejs:github"])
        remote_used = True
    args.append(url)
    return args, js_used, remote_used


def run_ytdlp_probe(args: argparse.Namespace, raw_dir: Path, source: dict[str, str]) -> tuple[list[CommandResult], dict[str, Any] | None, list[Path]]:
    ytdlp = resolve_ytdlp(args.ytdlp)
    if ytdlp is None:
        raise AcquisitionRunnerError("yt-dlp was not found; run doctor.py and install or expose yt-dlp first.")

    cookies_path = Path(args.youtube_cookies).expanduser().resolve() if args.youtube_cookies else None
    if cookies_path is not None and not cookies_path.is_file():
        raise AcquisitionRunnerError(f"cookies file was not found: {cookies_path}")

    node_path = resolve_node(args.node)
    use_js = bool(args.use_js_runtime and node_path is not None and node_path.is_file())
    use_remote = bool(args.use_remote_components)

    results: list[CommandResult] = []
    metadata: dict[str, Any] | None = None

    bare = [
        str(ytdlp),
        "--no-warnings",
        "--dump-single-json",
        "--skip-download",
        args.input,
    ]
    bare_result = run_command(
        name="yt_dlp_bare_metadata",
        command_kind="yt-dlp:dump-single-json",
        args=bare,
        timeout_seconds=args.timeout_seconds,
        raw_dir=raw_dir,
    )
    results.append(bare_result)
    metadata = extract_json(bare_result.stdout)

    bare_blocked = bool(detect_signals([bare_result], metadata, set()) & acquisition_probe.BLOCKED_SIGNALS)
    should_try_cookies = cookies_path is not None and (bare_blocked or source["platform"] == "youtube" or metadata is None)
    if should_try_cookies:
        cookie_base, js_used, remote_used = build_ytdlp_base(
            ytdlp=ytdlp,
            url=args.input,
            cookies_path=cookies_path,
            node_path=node_path if use_js else None,
            use_remote_components=use_remote,
        )
        cookie_metadata = [
            *cookie_base[:-1],
            "--no-warnings",
            "--dump-single-json",
            "--skip-download",
            cookie_base[-1],
        ]
        cookie_result = run_command(
            name="yt_dlp_cookies_metadata",
            command_kind="yt-dlp:cookies:dump-single-json",
            args=cookie_metadata,
            timeout_seconds=args.timeout_seconds,
            raw_dir=raw_dir,
            cookies_used=True,
            js_runtime_used=js_used,
            remote_components_used=remote_used,
        )
        results.append(cookie_result)
        cookie_json = extract_json(cookie_result.stdout)
        if cookie_json:
            metadata = cookie_json

    if args.list_subtitles:
        list_subs = [str(ytdlp), "--list-subs", args.input]
        if cookies_path is not None:
            list_subs = [str(ytdlp), "--cookies", str(cookies_path), "--list-subs", args.input]
        list_result = run_command(
            name="yt_dlp_list_subtitles",
            command_kind="yt-dlp:list-subs",
            args=list_subs,
            timeout_seconds=args.timeout_seconds,
            raw_dir=raw_dir,
            cookies_used=cookies_path is not None,
        )
        results.append(list_result)

    if args.list_formats:
        list_formats = [str(ytdlp), "--list-formats", args.input]
        if cookies_path is not None:
            list_formats = [str(ytdlp), "--cookies", str(cookies_path), "--list-formats", args.input]
        format_result = run_command(
            name="yt_dlp_list_formats",
            command_kind="yt-dlp:list-formats",
            args=list_formats,
            timeout_seconds=args.timeout_seconds,
            raw_dir=raw_dir,
            cookies_used=cookies_path is not None,
        )
        results.append(format_result)

    acquired_subtitles: list[Path] = []
    if args.download_subtitles:
        subtitles_dir = raw_dir / "subtitles"
        subtitles_dir.mkdir(parents=True, exist_ok=True)
        before_subtitles = {
            path.resolve(): (path.stat().st_size, path.stat().st_mtime)
            for path in subtitles_dir.rglob("*")
            if path.is_file()
        }
        dl_args = [
            str(ytdlp),
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            args.subtitle_languages,
            "--convert-subs",
            "srt",
            "-o",
            str(subtitles_dir / "%(id)s.%(ext)s"),
        ]
        if cookies_path is not None:
            dl_args.extend(["--cookies", str(cookies_path)])
        dl_args.append(args.input)
        dl_result = run_command(
            name="yt_dlp_download_subtitles",
            command_kind="yt-dlp:download-subtitles",
            args=dl_args,
            timeout_seconds=args.timeout_seconds,
            raw_dir=raw_dir,
            cookies_used=cookies_path is not None,
        )
        results.append(dl_result)
        if dl_result.returncode == 0:
            acquired_subtitles = sorted(
                path
                for path in subtitles_dir.rglob("*")
                if path.suffix.lower() in {".srt", ".vtt", ".sbv", ".ass"}
                and path.is_file()
                and path.stat().st_size > 0
                and (
                    path.resolve() not in before_subtitles
                    or path.stat().st_size != before_subtitles[path.resolve()][0]
                    or path.stat().st_mtime > before_subtitles[path.resolve()][1]
                )
            )
    return results, metadata, acquired_subtitles


def source_status_from_probe(
    *,
    source: dict[str, str],
    results: list[CommandResult],
    metadata: dict[str, Any] | None,
    acquired_subtitles: list[Path],
    timeout_seconds: int,
) -> dict[str, Any]:
    probes = {"yt-dlp"}
    if any(result.cookies_used for result in results):
        probes.add("yt-dlp-chrome-cookies")
    signals = detect_signals(results, metadata, acquired_subtitles)
    if metadata and signals.intersection(acquisition_probe.BLOCKED_SIGNALS):
        signals.add("metadata_available")

    probe_args = argparse.Namespace(
        source_type=source["source_type"],
        probe=sorted(probes),
        signal=sorted(signals),
        attempts=len(results),
        max_time_seconds=timeout_seconds,
    )
    status = acquisition_probe.build_summary(probe_args)

    available = []
    langs = subtitle_languages(metadata)
    if langs["subtitles"] or langs["automatic_captions"]:
        available.append("subtitles_or_automatic_captions_listed")
    if has_media_formats(metadata):
        available.append("media_formats_listed")

    if status["source_status"] == "secondary_only" and available:
        status["next_step"] = (
            "download_subtitles_or_audio_then_parse_or_run_asr"
            if "subtitles_or_automatic_captions_listed" in available
            else "download_audio_then_run_local_asr"
        )
        status["status_reason"] = (
            "Platform metadata and first-hand acquisition routes are visible, but no local transcript/audio "
            "artifact has been acquired or processed yet."
        )
    status["available_primary_routes_not_yet_acquired"] = available
    return status


def local_transcript_status(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    details: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
        "readable": False,
    }
    ok = False
    reason = ""
    if not path.exists():
        reason = "Local transcript path does not exist."
    elif not path.is_file():
        reason = "Local transcript path is not a file."
    elif details["size_bytes"] <= 0:
        reason = "Local transcript file is empty."
    else:
        try:
            path.read_text(encoding="utf-8-sig")
            details["readable"] = True
            ok = True
        except UnicodeDecodeError:
            reason = "Local transcript file is not valid UTF-8 text."
        except OSError as exc:
            reason = f"Local transcript file could not be read: {exc}"

    probe_args = argparse.Namespace(
        source_type="local_transcript" if ok else "unknown",
        probe=["user_file"],
        signal=["local_transcript"] if ok else ["tool_failed"],
        attempts=1,
        max_time_seconds=0,
    )
    status = acquisition_probe.build_summary(probe_args)
    if not ok:
        status["source_classes"] = []
        status["primary_material_available"] = False
        status["can_enter_full_decomposition"] = False
        status["status_reason"] = reason
        status["next_step"] = "provide_existing_non_empty_utf8_transcript_or_media_file"
    return status, details


def render_notes(report: dict[str, Any]) -> str:
    status = report["source_status"]
    lines = [
        "# Source Acquisition Notes",
        "",
        f"Input: `{report['input']}`",
        f"Platform: `{report['platform']}`",
        f"Source status: `{status['source_status']}`",
        f"Allowed report type: `{status['allowed_report_type']}`",
        f"Decomposition gate open: `{status['can_enter_full_decomposition']}`",
        "",
        "## Decision",
        "",
        status.get("status_reason", ""),
        "",
        f"Next step: `{status.get('next_step', '')}`",
        "",
        "## Available Primary Routes Not Yet Acquired",
        "",
    ]
    routes = status.get("available_primary_routes_not_yet_acquired", [])
    if routes:
        lines.extend([f"- `{route}`" for route in routes])
    else:
        lines.append("- None confirmed.")
    lines.extend(
        [
            "",
            "## Privacy",
            "",
            "- Cookie values reported: `False`",
            f"- User-exported cookies used: `{report['privacy']['cookies_used']}`",
            f"- Media download performed: `{report['privacy']['media_download_performed']}`",
            "",
            "## Probe Summary",
            "",
        ]
    )
    for item in report["probe_results"]:
        lines.append(f"- `{item['name']}`: returncode=`{item['returncode']}`, timeout=`{item['timeout']}`")
    lines.append("")
    return "\n".join(lines)


def run_doctor_if_requested(args: argparse.Namespace, output_root: Path) -> dict[str, Any] | None:
    if args.no_doctor:
        return None
    doc_args = argparse.Namespace(
        youtube_cookies=args.youtube_cookies,
        asr_python=None,
        chrome_plugin_root=None,
        output_json=str(output_root / "00_source" / "logs" / "doctor_report.json"),
        output_md=str(output_root / "00_source" / "logs" / "doctor_report.md"),
        overwrite=True,
        pretty=False,
        self_test=False,
    )
    report = doctor.build_report(doc_args)
    doctor.write_outputs(report, doc_args)
    return report


def run_acquisition(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.expanduser().resolve()
    raw_dir = output_root / "00_source" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    source = classify_source(args.input)

    doctor_report = run_doctor_if_requested(args, output_root)
    results: list[CommandResult] = []
    metadata: dict[str, Any] | None = None
    acquired_subtitles: list[Path] = []

    if source["input_kind"] == "url":
        results, metadata, acquired_subtitles = run_ytdlp_probe(args, raw_dir, source)
    elif source["input_kind"] == "local_transcript":
        path = Path(args.input).expanduser().resolve()
        status, local_details = local_transcript_status(path)
        metadata = {"local_path": str(path), "local_transcript": local_details}
    else:
        raise AcquisitionRunnerError("Phase 2 acquisition runner currently supports platform URLs and local transcripts.")

    if source["input_kind"] == "local_transcript":
        status = status
    else:
        status = source_status_from_probe(
            source=source,
            results=results,
            metadata=metadata,
            acquired_subtitles=acquired_subtitles,
            timeout_seconds=args.timeout_seconds,
        )

    status.update(
        {
            "runner": RUNNER_NAME,
            "url": args.input if source["input_kind"] == "url" else None,
            "platform": source["platform"],
            "generated_at": now_iso(),
            "cost_limits": {
                **status.get("cost_limits", {}),
                "network_access_performed": source["input_kind"] == "url",
                "media_extraction_performed": bool(acquired_subtitles),
            },
        }
    )

    metadata_summary = {
        "id": metadata.get("id") if metadata else None,
        "title": metadata.get("title") if metadata else None,
        "uploader": metadata.get("uploader") if metadata else None,
        "duration": metadata.get("duration") if metadata else None,
        "webpage_url": metadata.get("webpage_url") if metadata else None,
        "subtitle_languages": subtitle_languages(metadata),
        "media_formats_listed": has_media_formats(metadata),
    }
    report = {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "input": args.input,
        "source_type": source["source_type"],
        "platform": source["platform"],
        "source_status": status,
        "metadata_summary": metadata_summary,
        "acquired_subtitle_files": [str(path.resolve()) for path in acquired_subtitles],
        "probe_results": [result.as_dict() for result in results],
        "doctor_overall_status": doctor_report.get("overall_status") if doctor_report else None,
        "privacy": {
            "cookie_values_reported": False,
            "cookies_used": any(result.cookies_used for result in results),
            "cookie_source": "user_exported_cookies_txt" if any(result.cookies_used for result in results) else None,
            "js_runtime_used": any(result.js_runtime_used for result in results),
            "remote_components_used": any(result.remote_components_used for result in results),
            "network_probe_performed": source["input_kind"] == "url",
            "media_download_performed": bool(acquired_subtitles),
            "browser_launched": False,
            "raw_outputs_may_contain_temporary_media_urls": source["input_kind"] == "url",
        },
    }

    write_json(output_root / "00_source" / "source_status.json", status)
    write_json(output_root / "00_source" / "acquisition_runner_report.json", report)
    write_text(output_root / "00_source" / "acquisition_notes.md", render_notes(report))
    return {
        "runner": RUNNER_NAME,
        "output_root": str(output_root),
        "source_status": status["source_status"],
        "allowed_report_type": status["allowed_report_type"],
        "can_enter_full_decomposition": status["can_enter_full_decomposition"],
        "primary_material_available": status["primary_material_available"],
        "next_step": status["next_step"],
        "available_primary_routes_not_yet_acquired": status.get("available_primary_routes_not_yet_acquired", []),
        "doctor_overall_status": report["doctor_overall_status"],
        "files_written": [
            str((output_root / "00_source" / "source_status.json").resolve()),
            str((output_root / "00_source" / "acquisition_runner_report.json").resolve()),
            str((output_root / "00_source" / "acquisition_notes.md").resolve()),
        ],
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe a platform video source and write acquisition artifacts.")
    parser.add_argument("--input", required=False, help="Platform URL or local transcript path.")
    parser.add_argument("--output-root", type=Path, default=None, help="Directory for acquisition artifacts.")
    parser.add_argument("--youtube-cookies", default=None, help="Path to user-exported Netscape cookies.txt.")
    parser.add_argument("--ytdlp", default=None, help="Optional yt-dlp executable override.")
    parser.add_argument("--node", default=None, help="Optional Node.js executable override.")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--no-doctor", action="store_true", help="Skip local doctor report.")
    parser.add_argument("--list-subtitles", action="store_true", help="Run yt-dlp --list-subs.")
    parser.add_argument("--list-formats", action="store_true", help="Run yt-dlp --list-formats.")
    parser.add_argument("--use-js-runtime", action="store_true", help="Pass Node.js to yt-dlp for player challenge solving.")
    parser.add_argument("--use-remote-components", action="store_true", help="Allow yt-dlp remote ejs solver component.")
    parser.add_argument("--download-subtitles", action="store_true", help="Download subtitles only; no media download.")
    parser.add_argument("--subtitle-languages", default="all,-live_chat")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests without network.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def fake_result(name: str, stdout: str = "", stderr: str = "", returncode: int = 0, cookies: bool = False) -> CommandResult:
    return CommandResult(
        name=name,
        command_kind="fake",
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timeout=False,
        duration_seconds=0.0,
        output_path=None,
        cookies_used=cookies,
    )


def run_self_test() -> int:
    failures: list[str] = []
    youtube = classify_source("https://www.youtube.com/watch?v=abc")
    assert_true("classify youtube", youtube["platform"] == "youtube", failures)
    x = classify_source("https://x.com/a/status/1")
    assert_true("classify x", x["platform"] == "x", failures)
    xhs = classify_source("https://www.xiaohongshu.com/explore/1")
    assert_true("classify xhs", xhs["platform"] == "xiaohongshu", failures)

    metadata = {
        "id": "abc",
        "title": "Test",
        "subtitles": {"en": [{"ext": "vtt"}]},
        "automatic_captions": {},
        "formats": [{"format_id": "140", "url": "https://example.invalid/audio.m4a"}],
    }
    status = source_status_from_probe(
        source=youtube,
        results=[fake_result("yt_dlp_bare_metadata", stdout=json.dumps(metadata))],
        metadata=metadata,
        acquired_subtitles=[],
        timeout_seconds=10,
    )
    assert_true("listed subtitles are not confirmed", status["source_status"] == "secondary_only", failures)
    assert_true("listed subtitles next step", status["next_step"] == "download_subtitles_or_audio_then_parse_or_run_asr", failures)
    assert_true("listed routes recorded", "subtitles_or_automatic_captions_listed" in status["available_primary_routes_not_yet_acquired"], failures)

    confirmed = source_status_from_probe(
        source=youtube,
        results=[fake_result("yt_dlp_download_subtitles")],
        metadata=metadata,
        acquired_subtitles=[Path("abc.en.srt")],
        timeout_seconds=10,
    )
    assert_true("downloaded subtitle confirms source", confirmed["source_status"] == "source_confirmed", failures)

    stale = source_status_from_probe(
        source=youtube,
        results=[fake_result("yt_dlp_download_subtitles", returncode=1)],
        metadata=metadata,
        acquired_subtitles=[],
        timeout_seconds=10,
    )
    assert_true("failed subtitle download not confirmed", stale["source_status"] != "source_confirmed", failures)

    blocked = source_status_from_probe(
        source=youtube,
        results=[fake_result("yt_dlp_bare_metadata", stderr="Sign in to confirm you're not a bot", returncode=1)],
        metadata=None,
        acquired_subtitles=[],
        timeout_seconds=10,
    )
    assert_true("bot check blocked", blocked["source_status"] == "source_blocked", failures)
    assert_true("bot check next step", blocked["next_step"] == "retry_yt_dlp_with_chrome_cookies", failures)

    cookies_blocked = source_status_from_probe(
        source=youtube,
        results=[
            fake_result("yt_dlp_bare_metadata", stderr="Sign in to confirm you're not a bot", returncode=1),
            fake_result("yt_dlp_cookies_metadata", stderr="request blocked", returncode=1, cookies=True),
        ],
        metadata=None,
        acquired_subtitles=[],
        timeout_seconds=10,
    )
    assert_true("cookies attempted", cookies_blocked["yt_dlp_chrome_cookies_attempted"] is True, failures)
    assert_true("cookies failure goes chrome", cookies_blocked["next_step"] == "perform_chrome_deep_probe", failures)

    missing_status, missing_details = local_transcript_status(Path("definitely-missing-transcript-file.md"))
    assert_true("missing local transcript fails", missing_status["source_status"] == "source_failed", failures)
    assert_true("missing local transcript not primary", missing_status["primary_material_available"] is False, failures)
    assert_true("missing local transcript details", missing_details["exists"] is False, failures)

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
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    if args.output_root is None:
        parser.error("--output-root is required unless --self-test is used")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be > 0")
    try:
        summary = run_acquisition(args)
    except (AcquisitionRunnerError, ArtifactWriteError, OSError) as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "error": exc.__class__.__name__,
                "message": str(exc),
                "cookie_values_reported": False,
            },
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return 1
    emit_json(summary, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
