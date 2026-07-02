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
import tempfile
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
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[3]
DEFAULT_YOUTUBE_COOKIES = REPO_ROOT / "work" / "youtube-cookies" / "youtube.cookies.txt"


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
    ("js_runtime_missing", r"no supported javascript runtime|javascript runtime.*not found|js runtime"),
    ("po_token_required", r"po token|potoken|proof of origin"),
    ("impersonation_unavailable", r"impersonate target .* is not available|curl_cffi.*unavailable"),
    ("ejs_solver_missing", r"ejs|remote components|yt-dlp-ejs"),
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


def resolve_youtube_cookies_path(value: str | Path | None, *, allow_missing_auto: bool = True) -> tuple[Path | None, dict[str, Any]]:
    meta: dict[str, Any] = {
        "configured": False,
        "source": None,
        "auto_default_path": str(DEFAULT_YOUTUBE_COOKIES),
        "exists": False,
        "size_bytes": None,
        "last_modified": None,
        "status": "not_configured",
    }
    if value is None:
        return None, meta
    text = str(value).strip()
    if not text:
        return None, meta

    is_auto = text.lower() == "auto"
    path = DEFAULT_YOUTUBE_COOKIES if is_auto else Path(text).expanduser()
    path = path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()
    meta.update({"configured": True, "source": "auto_default_path" if is_auto else "explicit_path", "path": str(path)})

    if not path.exists():
        meta["status"] = "missing"
        if is_auto and allow_missing_auto:
            return None, meta
        raise AcquisitionRunnerError(f"cookies file was not found: {path}")
    if not path.is_file():
        meta["status"] = "not_file"
        raise AcquisitionRunnerError(f"cookies path is not a file: {path}")

    stat = path.stat()
    meta.update(
        {
            "exists": True,
            "size_bytes": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "status": "available",
        }
    )
    return path, meta


def runtime_cookies_copy(source: Path | None, label: str, cleanup_paths: list[Path]) -> Path | None:
    if source is None:
        return None
    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-") or "cookies"
    handle = tempfile.NamedTemporaryFile(prefix=f"kw-ytdlp-{safe_label}-", suffix=".cookies.txt", delete=False)
    runtime_path = Path(handle.name)
    handle.close()
    shutil.copy2(source, runtime_path)
    cleanup_paths.append(runtime_path)
    return runtime_path


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
    if not signals and any(result.returncode not in {0, None} or result.timeout for result in results):
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


def listed_media_formats(results: list[CommandResult]) -> bool:
    return any(
        result.returncode == 0
        and "list-formats" in result.command_kind
        and ("[info] available formats" in result.stdout.lower() or "format code" in result.stdout.lower())
        for result in results
    )


def listed_subtitles(results: list[CommandResult]) -> bool:
    return any(
        result.returncode == 0
        and "list-subs" in result.command_kind
        and ("available subtitles" in result.stdout.lower() or "language" in result.stdout.lower())
        for result in results
    )


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


def split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def extra_ytdlp_options(
    args: argparse.Namespace,
    *,
    player_client: str | None = None,
    include_sensitive: bool = True,
) -> list[str]:
    options: list[str] = []
    proxy = getattr(args, "ytdlp_proxy", None)
    if proxy:
        options.extend(["--proxy", str(proxy)])
    impersonate = getattr(args, "ytdlp_impersonate", None)
    if impersonate:
        options.extend(["--impersonate", str(impersonate)])
    sleep_requests = getattr(args, "ytdlp_sleep_requests", None)
    if sleep_requests is not None:
        options.extend(["--sleep-requests", str(sleep_requests)])
    for retry_sleep in getattr(args, "ytdlp_retry_sleep", []) or []:
        options.extend(["--retry-sleep", str(retry_sleep)])

    youtube_parts: list[str] = []
    passthrough_extractor_args: list[str] = []
    for raw in getattr(args, "ytdlp_extractor_args", []) or []:
        raw_text = str(raw).strip()
        if not raw_text:
            continue
        if raw_text.lower().startswith("youtube:"):
            youtube_parts.append(raw_text.split(":", 1)[1])
        else:
            passthrough_extractor_args.append(raw_text)
    if player_client:
        youtube_parts.append(f"player_client={player_client}")
    visitor_data = getattr(args, "youtube_visitor_data", None)
    if visitor_data and include_sensitive:
        youtube_parts.append(f"visitor_data={visitor_data}")
    for po_token in getattr(args, "youtube_po_token", []) or []:
        if po_token and include_sensitive:
            youtube_parts.append(f"po_token={po_token}")

    if youtube_parts:
        options.extend(["--extractor-args", f"youtube:{';'.join(youtube_parts)}"])
    for extractor_arg in passthrough_extractor_args:
        options.extend(["--extractor-args", extractor_arg])
    return options


def build_ytdlp_command(
    *,
    ytdlp: Path,
    url: str,
    cookies_path: Path | None,
    node_path: Path | None,
    use_js_runtime: bool,
    use_remote_components: bool,
    command_args: list[str],
    options_args: argparse.Namespace | None = None,
    player_client: str | None = None,
) -> tuple[list[str], bool, bool, bool]:
    base, js_used, remote_used = build_ytdlp_base(
        ytdlp=ytdlp,
        url=url,
        cookies_path=cookies_path,
        node_path=node_path if use_js_runtime else None,
        use_remote_components=use_remote_components,
    )
    extra_options = extra_ytdlp_options(options_args, player_client=player_client) if options_args else []
    return [*base[:-1], *extra_options, *command_args, base[-1]], cookies_path is not None, js_used, remote_used


def classify_primary_failure(signals: set[str], results: list[CommandResult]) -> str:
    priority = [
        "bot_check",
        "login_required",
        "http_429",
        "request_blocked",
        "po_token_required",
        "js_runtime_missing",
        "n_challenge_failed",
        "ejs_solver_missing",
        "dpapi_or_app_bound_cookie_failure",
        "impersonation_unavailable",
        "permission_required",
        "captcha",
        "unsupported_url",
        "tool_failed",
        "timeout",
    ]
    for item in priority:
        if item in signals:
            return item
    if any(result.returncode not in {0, None} for result in results):
        return "tool_failed"
    return "unknown"


def ytdlp_diagnostics(
    *,
    source: dict[str, str],
    results: list[CommandResult],
    metadata: dict[str, Any] | None,
    acquired_subtitles: list[Path],
    signals: set[str],
    available_routes: list[str],
    ytdlp: Path,
    node_path: Path | None,
    cookies_path: Path | None,
    use_js_runtime: bool,
    use_remote_components: bool,
    options_args: argparse.Namespace | None = None,
    cookies_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attempts = []
    for result in results:
        attempts.append(
            {
                "name": result.name,
                "command_kind": result.command_kind,
                "returncode": result.returncode,
                "timeout": result.timeout,
                "duration_seconds": round(result.duration_seconds, 3),
                "cookies_used": result.cookies_used,
                "js_runtime_used": result.js_runtime_used,
                "remote_components_used": result.remote_components_used,
                "stdout_path": result.output_path,
                "stderr_path": result.output_path.replace(".stdout.txt", ".stderr.txt") if result.output_path else None,
                "signals": sorted(detect_signals([result], metadata, acquired_subtitles)),
            }
        )
    block_reason = classify_primary_failure(signals, results)
    if acquired_subtitles:
        next_step = "normalize_acquired_subtitle"
    elif "subtitles_or_automatic_captions_listed" in available_routes:
        next_step = "download_subtitles_then_normalize"
    elif "media_formats_listed" in available_routes:
        next_step = "download_audio_then_run_local_asr"
    elif block_reason in {"bot_check", "login_required", "request_blocked", "http_429"}:
        if cookies_meta and cookies_meta.get("status") == "missing":
            next_step = "place_exported_youtube_cookies_at_default_path_or_pass_explicit_cookies"
        elif cookies_path is None:
            next_step = "provide_user_exported_youtube_cookies_or_browser_visible_transcript"
        else:
            next_step = "refresh_or_re_export_youtube_cookies_or_use_browser_visible_transcript"
    elif block_reason == "po_token_required":
        next_step = "provide_po_token_or_use_browser_visible_transcript_or_local_media"
    elif block_reason in {"js_runtime_missing", "ejs_solver_missing", "n_challenge_failed"}:
        next_step = "enable_node_js_runtime_and_remote_ejs_components"
    else:
        next_step = "provide_primary_material_or_run_chrome_deep_probe"
    return {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "source": source,
        "yt_dlp": {
            "path": str(ytdlp.resolve()),
            "cookies_configured": cookies_path is not None,
            "cookies_request": cookies_meta
            or {
                "configured": cookies_path is not None,
                "source": "explicit_path" if cookies_path else None,
                "auto_default_path": str(DEFAULT_YOUTUBE_COOKIES),
                "exists": cookies_path.is_file() if cookies_path else False,
                "size_bytes": cookies_path.stat().st_size if cookies_path and cookies_path.is_file() else None,
                "last_modified": datetime.fromtimestamp(cookies_path.stat().st_mtime, timezone.utc).isoformat()
                if cookies_path and cookies_path.is_file()
                else None,
                "status": "available" if cookies_path else "not_configured",
            },
            "cookie_values_reported": False,
            "node_path": str(node_path.resolve()) if node_path and node_path.is_file() else None,
            "js_runtime_requested": use_js_runtime,
            "remote_components_requested": use_remote_components,
            "raw_extractor_args_count": len(getattr(options_args, "ytdlp_extractor_args", []) or []) if options_args else 0,
            "player_client_probes": split_csv(getattr(options_args, "ytdlp_player_clients", "")) if options_args else [],
            "visitor_data_configured": bool(getattr(options_args, "youtube_visitor_data", None)) if options_args else False,
            "po_token_count": len(getattr(options_args, "youtube_po_token", []) or []) if options_args else 0,
            "sensitive_extractor_values_reported": False,
            "proxy_configured": bool(getattr(options_args, "ytdlp_proxy", None)) if options_args else False,
            "proxy_value_reported": False,
            "impersonate": getattr(options_args, "ytdlp_impersonate", None) if options_args else None,
            "sleep_requests": getattr(options_args, "ytdlp_sleep_requests", None) if options_args else None,
            "retry_sleep_count": len(getattr(options_args, "ytdlp_retry_sleep", []) or []) if options_args else 0,
        },
        "summary": {
            "metadata_available": metadata is not None,
            "acquired_subtitle_files": [str(path.resolve()) for path in acquired_subtitles],
            "available_primary_routes_not_yet_acquired": available_routes,
            "signals": sorted(signals),
            "block_reason": block_reason,
            "next_step": next_step,
        },
        "attempts": attempts,
    }


def render_ytdlp_diagnostics_md(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    tool = payload.get("yt_dlp", {})
    cookie_request = tool.get("cookies_request") if isinstance(tool.get("cookies_request"), dict) else {}
    lines = [
        "# yt-dlp Diagnostics",
        "",
        f"- yt-dlp: `{tool.get('path')}`",
        f"- Cookies configured: `{tool.get('cookies_configured')}`",
        f"- Cookies source: `{cookie_request.get('source')}`",
        f"- Cookies status: `{cookie_request.get('status')}`",
        f"- Default cookies path: `{cookie_request.get('auto_default_path')}`",
        f"- Cookies file size bytes: `{cookie_request.get('size_bytes')}`",
        f"- Cookies values reported: `{tool.get('cookie_values_reported')}`",
        f"- JavaScript runtime requested: `{tool.get('js_runtime_requested')}`",
        f"- Node path: `{tool.get('node_path')}`",
        f"- Remote components requested: `{tool.get('remote_components_requested')}`",
        f"- Raw extractor args count: `{tool.get('raw_extractor_args_count')}`",
        f"- Player client probes: `{', '.join(tool.get('player_client_probes') or [])}`",
        f"- Visitor Data configured: `{tool.get('visitor_data_configured')}`",
        f"- PO Token count: `{tool.get('po_token_count')}`",
        f"- Sensitive extractor values reported: `{tool.get('sensitive_extractor_values_reported')}`",
        f"- Proxy configured: `{tool.get('proxy_configured')}`",
        f"- Proxy value reported: `{tool.get('proxy_value_reported')}`",
        f"- Impersonate: `{tool.get('impersonate')}`",
        f"- Sleep requests: `{tool.get('sleep_requests')}`",
        f"- Retry sleep count: `{tool.get('retry_sleep_count')}`",
        f"- Metadata available: `{summary.get('metadata_available')}`",
        f"- Block reason: `{summary.get('block_reason')}`",
        f"- Next step: `{summary.get('next_step')}`",
        "",
        "## Available Routes",
        "",
    ]
    routes = summary.get("available_primary_routes_not_yet_acquired") or []
    lines.extend(f"- `{route}`" for route in routes) if routes else lines.append("- None")
    lines.extend(["", "## Attempts", ""])
    for attempt in payload.get("attempts", []):
        lines.extend(
            [
                f"### {attempt.get('name')}",
                "",
                f"- Kind: `{attempt.get('command_kind')}`",
                f"- Return code: `{attempt.get('returncode')}`",
                f"- Timeout: `{attempt.get('timeout')}`",
                f"- Cookies used: `{attempt.get('cookies_used')}`",
                f"- JavaScript runtime used: `{attempt.get('js_runtime_used')}`",
                f"- Remote components used: `{attempt.get('remote_components_used')}`",
                f"- Signals: `{', '.join(attempt.get('signals') or [])}`",
                f"- stdout: `{attempt.get('stdout_path')}`",
                f"- stderr: `{attempt.get('stderr_path')}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_ytdlp_probe(args: argparse.Namespace, raw_dir: Path, source: dict[str, str]) -> tuple[list[CommandResult], dict[str, Any] | None, list[Path]]:
    ytdlp = resolve_ytdlp(args.ytdlp)
    if ytdlp is None:
        raise AcquisitionRunnerError("yt-dlp was not found; run doctor.py and install or expose yt-dlp first.")

    cookies_path, cookies_meta = resolve_youtube_cookies_path(args.youtube_cookies, allow_missing_auto=True)
    cookie_cleanup_paths: list[Path] = []
    if cookies_path is not None:
        cookies_meta["runtime_copy_used"] = True

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
        cookie_metadata, cookies_used, js_used, remote_used = build_ytdlp_command(
            ytdlp=ytdlp,
            url=args.input,
            cookies_path=runtime_cookies_copy(cookies_path, "metadata", cookie_cleanup_paths),
            node_path=node_path,
            use_js_runtime=use_js,
            use_remote_components=use_remote,
            command_args=["--no-warnings", "--dump-single-json", "--skip-download"],
            options_args=args,
        )
        cookie_result = run_command(
            name="yt_dlp_cookies_metadata",
            command_kind="yt-dlp:cookies:dump-single-json",
            args=cookie_metadata,
            timeout_seconds=args.timeout_seconds,
            raw_dir=raw_dir,
            cookies_used=cookies_used,
            js_runtime_used=js_used,
            remote_components_used=remote_used,
        )
        results.append(cookie_result)
        cookie_json = extract_json(cookie_result.stdout)
        if cookie_json:
            metadata = cookie_json

    if args.list_subtitles:
        list_subs, cookies_used, js_used, remote_used = build_ytdlp_command(
            ytdlp=ytdlp,
            url=args.input,
            cookies_path=runtime_cookies_copy(cookies_path, "list-subs", cookie_cleanup_paths),
            node_path=node_path,
            use_js_runtime=use_js,
            use_remote_components=use_remote,
            command_args=["--list-subs"],
            options_args=args,
        )
        list_result = run_command(
            name="yt_dlp_list_subtitles",
            command_kind="yt-dlp:list-subs",
            args=list_subs,
            timeout_seconds=args.timeout_seconds,
            raw_dir=raw_dir,
            cookies_used=cookies_used,
            js_runtime_used=js_used,
            remote_components_used=remote_used,
        )
        results.append(list_result)

    if args.list_formats:
        list_formats, cookies_used, js_used, remote_used = build_ytdlp_command(
            ytdlp=ytdlp,
            url=args.input,
            cookies_path=runtime_cookies_copy(cookies_path, "list-formats", cookie_cleanup_paths),
            node_path=node_path,
            use_js_runtime=use_js,
            use_remote_components=use_remote,
            command_args=["--list-formats"],
            options_args=args,
        )
        format_result = run_command(
            name="yt_dlp_list_formats",
            command_kind="yt-dlp:list-formats",
            args=list_formats,
            timeout_seconds=args.timeout_seconds,
            raw_dir=raw_dir,
            cookies_used=cookies_used,
            js_runtime_used=js_used,
            remote_components_used=remote_used,
        )
        results.append(format_result)

    player_clients = split_csv(getattr(args, "ytdlp_player_clients", "")) if source["platform"] == "youtube" else []
    for player_client in player_clients:
        safe_client = re.sub(r"[^A-Za-z0-9_.-]+", "_", player_client).strip("_") or "client"
        if args.list_subtitles:
            client_list_subs, cookies_used, js_used, remote_used = build_ytdlp_command(
                ytdlp=ytdlp,
                url=args.input,
                cookies_path=runtime_cookies_copy(cookies_path, f"{safe_client}-list-subs", cookie_cleanup_paths),
                node_path=node_path,
                use_js_runtime=use_js,
                use_remote_components=use_remote,
                command_args=["--list-subs"],
                options_args=args,
                player_client=player_client,
            )
            client_subs_result = run_command(
                name=f"yt_dlp_player_client_{safe_client}_list_subtitles",
                command_kind="yt-dlp:player-client:list-subs",
                args=client_list_subs,
                timeout_seconds=args.timeout_seconds,
                raw_dir=raw_dir,
                cookies_used=cookies_used,
                js_runtime_used=js_used,
                remote_components_used=remote_used,
            )
            results.append(client_subs_result)
        if args.list_formats:
            client_list_formats, cookies_used, js_used, remote_used = build_ytdlp_command(
                ytdlp=ytdlp,
                url=args.input,
                cookies_path=runtime_cookies_copy(cookies_path, f"{safe_client}-list-formats", cookie_cleanup_paths),
                node_path=node_path,
                use_js_runtime=use_js,
                use_remote_components=use_remote,
                command_args=["--list-formats"],
                options_args=args,
                player_client=player_client,
            )
            client_formats_result = run_command(
                name=f"yt_dlp_player_client_{safe_client}_list_formats",
                command_kind="yt-dlp:player-client:list-formats",
                args=client_list_formats,
                timeout_seconds=args.timeout_seconds,
                raw_dir=raw_dir,
                cookies_used=cookies_used,
                js_runtime_used=js_used,
                remote_components_used=remote_used,
            )
            results.append(client_formats_result)

    acquired_subtitles: list[Path] = []
    if args.download_subtitles:
        subtitles_dir = raw_dir / "subtitles"
        subtitles_dir.mkdir(parents=True, exist_ok=True)
        before_subtitles = {
            path.resolve(): (path.stat().st_size, path.stat().st_mtime)
            for path in subtitles_dir.rglob("*")
            if path.is_file()
        }
        dl_args, cookies_used, js_used, remote_used = build_ytdlp_command(
            ytdlp=ytdlp,
            url=args.input,
            cookies_path=runtime_cookies_copy(cookies_path, "download-subtitles", cookie_cleanup_paths),
            node_path=node_path,
            use_js_runtime=use_js,
            use_remote_components=use_remote,
            command_args=[
                "--skip-download",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs",
                args.subtitle_languages,
                "--convert-subs",
                "srt",
                "-o",
                str(subtitles_dir / "%(id)s.%(ext)s"),
            ],
            options_args=args,
        )
        dl_result = run_command(
            name="yt_dlp_download_subtitles",
            command_kind="yt-dlp:download-subtitles",
            args=dl_args,
            timeout_seconds=args.timeout_seconds,
            raw_dir=raw_dir,
            cookies_used=cookies_used,
            js_runtime_used=js_used,
            remote_components_used=remote_used,
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
    for cookie_copy in cookie_cleanup_paths:
        try:
            cookie_copy.unlink(missing_ok=True)
        except OSError:
            pass
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
    if langs["subtitles"] or langs["automatic_captions"] or listed_subtitles(results):
        available.append("subtitles_or_automatic_captions_listed")
    if has_media_formats(metadata) or listed_media_formats(results):
        available.append("media_formats_listed")

    if available and status["source_status"] in {"secondary_only", "source_blocked"}:
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
        signals = detect_signals(results, metadata, acquired_subtitles)
        status["block_reason"] = classify_primary_failure(signals, results)
        failed_stage = next((result.name for result in reversed(results) if result.returncode not in {0, None} or result.timeout), None)
        if failed_stage:
            status["yt_dlp_stage_failed"] = failed_stage

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

    if source["input_kind"] == "url":
        ytdlp = resolve_ytdlp(args.ytdlp)
        if ytdlp is not None:
            node_path = resolve_node(args.node)
            diagnostic_cookies_path, diagnostic_cookies_meta = resolve_youtube_cookies_path(args.youtube_cookies, allow_missing_auto=True)
            diagnostics = ytdlp_diagnostics(
                source=source,
                results=results,
                metadata=metadata,
                acquired_subtitles=acquired_subtitles,
                signals=detect_signals(results, metadata, acquired_subtitles),
                available_routes=status.get("available_primary_routes_not_yet_acquired", []),
                ytdlp=ytdlp,
                node_path=node_path,
                cookies_path=diagnostic_cookies_path,
                use_js_runtime=bool(args.use_js_runtime),
                use_remote_components=bool(args.use_remote_components),
                options_args=args,
                cookies_meta=diagnostic_cookies_meta,
            )
            write_json(output_root / "00_source" / "yt_dlp_diagnostics.json", diagnostics)
            write_text(output_root / "00_source" / "yt_dlp_diagnostics.md", render_ytdlp_diagnostics_md(diagnostics))
            status["cookies_request"] = diagnostics["yt_dlp"].get("cookies_request")
            status["yt_dlp_next_step"] = diagnostics["summary"].get("next_step")
            report["yt_dlp_diagnostics"] = {
                "json": str((output_root / "00_source" / "yt_dlp_diagnostics.json").resolve()),
                "markdown": str((output_root / "00_source" / "yt_dlp_diagnostics.md").resolve()),
                "block_reason": diagnostics["summary"]["block_reason"],
                "next_step": diagnostics["summary"]["next_step"],
            }

    write_json(output_root / "00_source" / "source_status.json", status)
    write_json(output_root / "00_source" / "acquisition_runner_report.json", report)
    write_text(output_root / "00_source" / "acquisition_notes.md", render_notes(report))
    files_written = [
        str((output_root / "00_source" / "source_status.json").resolve()),
        str((output_root / "00_source" / "acquisition_runner_report.json").resolve()),
        str((output_root / "00_source" / "acquisition_notes.md").resolve()),
    ]
    if source["input_kind"] == "url":
        files_written.extend(
            [
                str((output_root / "00_source" / "yt_dlp_diagnostics.json").resolve()),
                str((output_root / "00_source" / "yt_dlp_diagnostics.md").resolve()),
            ]
        )
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
        "files_written": files_written,
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe a platform video source and write acquisition artifacts.")
    parser.add_argument("--input", required=False, help="Platform URL or local transcript path.")
    parser.add_argument("--output-root", type=Path, default=None, help="Directory for acquisition artifacts.")
    parser.add_argument("--youtube-cookies", default=None, help="Path to user-exported Netscape cookies.txt, or 'auto' for work/youtube-cookies/youtube.cookies.txt.")
    parser.add_argument("--ytdlp", default=None, help="Optional yt-dlp executable override.")
    parser.add_argument("--node", default=None, help="Optional Node.js executable override.")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--no-doctor", action="store_true", help="Skip local doctor report.")
    parser.add_argument("--list-subtitles", action="store_true", help="Run yt-dlp --list-subs.")
    parser.add_argument("--list-formats", action="store_true", help="Run yt-dlp --list-formats.")
    parser.add_argument("--use-js-runtime", action="store_true", help="Pass Node.js to yt-dlp for player challenge solving.")
    parser.add_argument("--use-remote-components", action="store_true", help="Allow yt-dlp remote ejs solver component.")
    parser.add_argument("--ytdlp-extractor-args", action="append", default=[], help="Raw yt-dlp --extractor-args value.")
    parser.add_argument("--ytdlp-player-clients", default="default,mweb,web,android_vr", help="Comma-separated YouTube player_client probe matrix. Use an empty string to disable.")
    parser.add_argument("--youtube-visitor-data", default=None, help="Visitor Data passed to yt-dlp without logging the value.")
    parser.add_argument("--youtube-po-token", action="append", default=[], help="PO Token passed to yt-dlp without logging the value.")
    parser.add_argument("--ytdlp-proxy", default=None, help="Proxy URL passed to yt-dlp --proxy.")
    parser.add_argument("--ytdlp-impersonate", default=None, help="Client passed to yt-dlp --impersonate.")
    parser.add_argument("--ytdlp-sleep-requests", type=float, default=None, help="Seconds passed to yt-dlp --sleep-requests.")
    parser.add_argument("--ytdlp-retry-sleep", action="append", default=[], help="Repeatable yt-dlp --retry-sleep expression.")
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
