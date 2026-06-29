#!/usr/bin/env python
"""Environment doctor for knowledge-video-decomposer.

The doctor is read-only with respect to platforms and credentials. It checks
local tool availability, versions, safe cookies handoff state, and UTF-8 output
health before a workflow tries acquisition.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from write_artifact import ArtifactWriteError, write_artifact


DOCTOR_NAME = "knowledge-video-decomposer-doctor"
STATUS_ORDER = {"ok": 0, "skip": 1, "warn": 2, "fail": 3}


@dataclass
class Check:
    name: str
    status: str
    summary: str
    details: dict[str, Any]
    next_step: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
        }
        if self.next_step:
            payload["next_step"] = self.next_step
        return payload


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(args: list[str], *, timeout: int = 10) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
    except FileNotFoundError as exc:
        return {"ok": False, "error": "not_found", "message": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "error": "timeout",
            "message": f"Command timed out after {timeout}s",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }

    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def resolve_executable(name: str, extra_candidates: list[Path] | None = None) -> Path | None:
    found = shutil.which(name)
    if found:
        return Path(found)
    return first_existing(extra_candidates or [])


def home_path(*parts: str) -> Path:
    return Path.home().joinpath(*parts)


def check_executable(
    *,
    name: str,
    executable: str,
    version_args: list[str],
    extra_candidates: list[Path] | None = None,
    required: bool = True,
    timeout: int = 10,
) -> Check:
    path = resolve_executable(executable, extra_candidates)
    if path is None:
        status = "fail" if required else "warn"
        return Check(
            name=name,
            status=status,
            summary=f"{executable} was not found.",
            details={"executable": executable, "candidates_checked": [str(p) for p in extra_candidates or []]},
            next_step=f"Install {executable} or add it to PATH.",
        )

    command = [str(path), *version_args]
    result = run_command(command, timeout=timeout)
    if not result.get("ok"):
        status = "fail" if required else "warn"
        return Check(
            name=name,
            status=status,
            summary=f"{executable} exists but version check failed.",
            details={"path": str(path), "command": command, "result": result},
            next_step=f"Verify {executable} can run from this environment.",
        )

    version = result.get("stdout") or result.get("stderr") or "version output empty"
    return Check(
        name=name,
        status="ok",
        summary=f"{executable} is available.",
        details={"path": str(path), "version": str(version).splitlines()[0], "command": command},
    )


def check_python_module(module: str, *, python_exe: Path | None = None, required: bool = False) -> Check:
    if python_exe is None:
        found = importlib.util.find_spec(module) is not None
        if found:
            return Check(
                name=f"python_module:{module}",
                status="ok",
                summary=f"Python module {module} is importable.",
                details={"python": sys.executable, "module": module},
            )
        return Check(
            name=f"python_module:{module}",
            status="fail" if required else "warn",
            summary=f"Python module {module} is not importable in the active Python.",
            details={"python": sys.executable, "module": module},
            next_step=f"Install {module} in the active environment or use a runtime that already has it.",
        )

    if not python_exe.is_file():
        return Check(
            name=f"python_module:{module}",
            status="warn",
            summary=f"Python runtime for checking {module} was not found.",
            details={"python": str(python_exe), "module": module},
        )
    result = run_command(
        [str(python_exe), "-c", f"import {module}; print('ok')"],
        timeout=15,
    )
    if result.get("ok"):
        return Check(
            name=f"python_module:{module}",
            status="ok",
            summary=f"Python module {module} is importable.",
            details={"python": str(python_exe), "module": module},
        )
    return Check(
        name=f"python_module:{module}",
        status="fail" if required else "warn",
        summary=f"Python module {module} is not importable.",
        details={"python": str(python_exe), "module": module, "result": result},
        next_step=f"Install {module} in this Python environment or select a different ASR runtime.",
    )


def check_youtube_cookies(path: Path | None) -> Check:
    if path is None:
        path = Path("work") / "youtube-cookies" / "youtube.cookies.txt"
    path = path.expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists():
        return Check(
            name="youtube_cookies_file",
            status="warn",
            summary="No user-exported YouTube cookies file was found.",
            details={"path": str(path), "exists": False},
            next_step="For YouTube bot/sign-in blocks, ask the user to export Netscape cookies.txt into this ignored local path.",
        )
    if not path.is_file():
        return Check(
            name="youtube_cookies_file",
            status="fail",
            summary="Configured YouTube cookies path is not a file.",
            details={"path": str(path), "exists": True, "is_file": False},
        )

    stat = path.stat()
    sample = path.read_text(encoding="utf-8", errors="replace")[:2048]
    has_netscape_header = "Netscape HTTP Cookie File" in sample
    has_youtube_domain = any(domain in sample for domain in [".youtube.com", "youtube.com", ".google.com"])
    status = "ok" if stat.st_size > 0 and has_netscape_header and has_youtube_domain else "warn"
    summary = (
        "User-exported Netscape cookies file is present."
        if status == "ok"
        else "Cookies file exists but is not a confirmed Netscape-format YouTube cookies file."
    )
    return Check(
        name="youtube_cookies_file",
        status=status,
        summary=summary,
        details={
            "path": str(path),
            "exists": True,
            "size_bytes": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "netscape_header_detected": has_netscape_header,
            "youtube_or_google_domain_detected": has_youtube_domain,
            "cookie_file_sample_read_for_validation": True,
            "cookie_values_reported": False,
        },
        next_step="" if status == "ok" else "Re-export cookies for youtube.com using a Netscape-format local exporter.",
    )


def check_chrome_plugin(plugin_root: Path | None) -> Check:
    if plugin_root is None:
        base = home_path(".codex", "plugins", "cache", "openai-bundled", "chrome")
        candidates = sorted(base.glob("*/scripts/browser-client.mjs")) if base.exists() else []
        script = candidates[-1] if candidates else None
    else:
        script = plugin_root.expanduser() / "scripts" / "browser-client.mjs"

    if script is None or not script.is_file():
        return Check(
            name="chrome_plugin",
            status="warn",
            summary="Chrome plugin browser-client was not found.",
            details={"browser_client": str(script) if script else None},
            next_step="Install or repair the Chrome plugin before Chrome page-state probing.",
        )
    skill = script.parent.parent / "skills" / "control-chrome" / "SKILL.md"
    return Check(
        name="chrome_plugin",
        status="ok" if skill.is_file() else "warn",
        summary="Chrome plugin files are present." if skill.is_file() else "Chrome browser-client exists but skill file was not found.",
        details={"browser_client": str(script), "skill": str(skill), "skill_exists": skill.is_file()},
        next_step="" if skill.is_file() else "Check Chrome plugin installation.",
    )


def check_chromium_app_bound_state() -> Check:
    candidates = [
        home_path("AppData", "Local", "Google", "Chrome", "User Data", "Local State"),
        home_path("AppData", "Local", "Microsoft", "Edge", "User Data", "Local State"),
        home_path("AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data", "Local State"),
    ]
    found = [path for path in candidates if path.is_file()]
    if not found:
        return Check(
            name="chromium_app_bound_state",
            status="skip",
            summary="No Chromium Local State file was found in common locations.",
            details={"candidates_checked": [str(path) for path in candidates]},
        )

    observations: list[dict[str, Any]] = []
    app_bound_detected = False
    for path in found:
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, json.JSONDecodeError) as exc:
            observations.append(
                {
                    "path": str(path),
                    "readable": False,
                    "error": exc.__class__.__name__,
                }
            )
            continue
        os_crypt = data.get("os_crypt") if isinstance(data, dict) else {}
        has_app_bound = isinstance(os_crypt, dict) and bool(os_crypt.get("app_bound_encrypted_key"))
        app_bound_detected = app_bound_detected or has_app_bound
        observations.append(
            {
                "path": str(path),
                "readable": True,
                "app_bound_encrypted_key_present": has_app_bound,
                "encrypted_key_present": isinstance(os_crypt, dict) and bool(os_crypt.get("encrypted_key")),
                "cookie_values_reported": False,
                "local_state_read_for_app_bound_marker": True,
            }
        )

    if app_bound_detected:
        return Check(
            name="chromium_app_bound_state",
            status="warn",
            summary="Chromium App-Bound encryption is present; direct browser-cookie decryption may fail.",
            details={"local_state_files": observations},
            next_step="Prefer user-exported Netscape cookies.txt when yt-dlp --cookies-from-browser chrome fails with DPAPI/App-Bound errors.",
        )
    return Check(
        name="chromium_app_bound_state",
        status="ok",
        summary="No Chromium App-Bound encryption marker was detected in readable Local State files.",
        details={"local_state_files": observations},
    )


def check_utf8_write() -> Check:
    content = "中文 utf-8 check\nemoji-safe-as-input: ok\n"
    try:
        with tempfile.TemporaryDirectory(prefix="kw-doctor-") as tmp:
            path = Path(tmp) / "utf8_check.md"
            write_artifact(path, content, mkdirs=True)
            read_back = path.read_text(encoding="utf-8")
            ok = read_back == content
    except (OSError, ArtifactWriteError) as exc:
        return Check(
            name="utf8_write",
            status="fail",
            summary="UTF-8 artifact write check failed.",
            details={"error": exc.__class__.__name__, "message": str(exc)},
            next_step="Use scripts/write_artifact.py or apply_patch for Markdown/JSON artifacts.",
        )
    return Check(
        name="utf8_write",
        status="ok" if ok else "fail",
        summary="UTF-8 artifact write check passed." if ok else "UTF-8 artifact readback differed.",
        details={"roundtrip_ok": ok},
        next_step="" if ok else "Avoid shell redirection and use scripts/write_artifact.py.",
    )


def summarize(checks: list[Check]) -> str:
    worst = "ok"
    for check in checks:
        if STATUS_ORDER[check.status] > STATUS_ORDER[worst]:
            worst = check.status
    if worst == "fail":
        return "fail"
    if any(check.status == "warn" for check in checks):
        return "warn"
    return "ok"


def capability_matrix(checks: list[Check]) -> dict[str, Any]:
    by_name = {check.name: check for check in checks}

    def is_ok(name: str) -> bool:
        return by_name.get(name, Check(name, "fail", "", {})).status == "ok"

    yt = is_ok("yt_dlp")
    ffmpeg = is_ok("ffmpeg") and is_ok("ffprobe")
    node = is_ok("node_js")
    cookies_status = by_name.get("youtube_cookies_file")
    cookies = cookies_status is not None and cookies_status.status == "ok"
    asr = by_name.get("python_module:faster_whisper")
    asr_ok = asr is not None and asr.status == "ok"
    chrome = is_ok("chrome_plugin")

    return {
        "youtube_public_metadata_prerequisites": yt,
        "youtube_cookies_js_subtitle_audio_prerequisites": yt and node and cookies,
        "local_audio_video_asr_prerequisites": ffmpeg and asr_ok,
        "x_video_metadata_download_prerequisites": yt,
        "xiaohongshu_metadata_download_prerequisites": yt,
        "chrome_page_probe_prerequisites": chrome,
        "safe_utf8_artifact_writes": is_ok("utf8_write"),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Knowledge Video Decomposer Doctor Report",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## Capability Matrix",
        "",
        "These values are local prerequisites only. They do not prove that a platform request will succeed.",
        "",
    ]
    for key, value in report["capabilities"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Checks", ""])
    for check in report["checks"]:
        lines.append(f"### {check['name']}")
        lines.append("")
        lines.append(f"- Status: `{check['status']}`")
        lines.append(f"- Summary: {check['summary']}")
        if check.get("next_step"):
            lines.append(f"- Next step: {check['next_step']}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(check["details"], ensure_ascii=False, indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    hearsay_python = home_path(".codex", "tools", "hearsay-venv", "Scripts", "python.exe")
    hearsay_ytdlp = home_path(".codex", "tools", "hearsay-venv", "Scripts", "yt-dlp.exe")
    videolingo_ytdlp = home_path(".codex", "tools", "VideoLingo", ".venv", "Scripts", "yt-dlp.exe")
    bundled_node = home_path(
        ".cache",
        "codex-runtimes",
        "codex-primary-runtime",
        "dependencies",
        "node",
        "bin",
        "node.exe",
    )

    checks = [
        Check(
            name="host",
            status="ok",
            summary="Host environment identified.",
            details={
                "platform": platform.platform(),
                "python": sys.executable,
                "cwd": str(Path.cwd()),
                "path_entries": len(os.environ.get("PATH", "").split(os.pathsep)),
            },
        ),
        check_executable(
            name="yt_dlp",
            executable="yt-dlp",
            version_args=["--version"],
            extra_candidates=[hearsay_ytdlp, videolingo_ytdlp],
            required=True,
        ),
        check_executable(name="ffmpeg", executable="ffmpeg", version_args=["-version"], required=False),
        check_executable(name="ffprobe", executable="ffprobe", version_args=["-version"], required=False),
        check_executable(
            name="node_js",
            executable="node",
            version_args=["--version"],
            extra_candidates=[bundled_node],
            required=False,
        ),
        check_python_module("faster_whisper", python_exe=Path(args.asr_python) if args.asr_python else hearsay_python),
        check_youtube_cookies(Path(args.youtube_cookies) if args.youtube_cookies else None),
        check_chromium_app_bound_state(),
        check_chrome_plugin(Path(args.chrome_plugin_root) if args.chrome_plugin_root else None),
        check_utf8_write(),
    ]
    cookie_sample_read = any(
        check.name == "youtube_cookies_file"
        and bool(check.details.get("cookie_file_sample_read_for_validation"))
        for check in checks
    )

    report = {
        "doctor": DOCTOR_NAME,
        "generated_at": now_iso(),
        "overall_status": summarize(checks),
        "checks": [check.as_dict() for check in checks],
        "capabilities": capability_matrix(checks),
        "privacy": {
            "cookie_file_sample_read_for_validation": cookie_sample_read,
            "cookie_values_reported": False,
            "network_probe_performed": False,
            "media_download_performed": False,
            "browser_launched": False,
        },
    }
    return report


def write_outputs(report: dict[str, Any], args: argparse.Namespace) -> None:
    if args.output_json:
        write_artifact(
            Path(args.output_json),
            json.dumps(report, ensure_ascii=False),
            json_mode=True,
            mkdirs=True,
            overwrite=args.overwrite,
        )
    if args.output_md:
        write_artifact(Path(args.output_md), render_markdown(report), mkdirs=True, overwrite=args.overwrite)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check local prerequisites for knowledge-video acquisition.")
    parser.add_argument("--youtube-cookies", default=None, help="Path to user-exported Netscape cookies.txt.")
    parser.add_argument("--asr-python", default=None, help="Python executable used for faster-whisper checks.")
    parser.add_argument("--chrome-plugin-root", default=None, help="Optional Chrome plugin root override.")
    parser.add_argument("--output-json", default=None, help="Write full doctor report JSON to this path.")
    parser.add_argument("--output-md", default=None, help="Write Markdown doctor report to this path.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing output report files.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON to stdout.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in doctor tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def run_self_test() -> int:
    failures: list[str] = []
    ok = Check("ok_check", "ok", "ok", {})
    warn = Check("warn_check", "warn", "warn", {})
    fail = Check("fail_check", "fail", "fail", {})
    assert_true("summarize ok", summarize([ok]) == "ok", failures)
    assert_true("summarize warn", summarize([ok, warn]) == "warn", failures)
    assert_true("summarize fail", summarize([ok, warn, fail]) == "fail", failures)

    with tempfile.TemporaryDirectory(prefix="kw-doctor-self-") as tmp:
        tmp_path = Path(tmp)
        cookies = tmp_path / "youtube.cookies.txt"
        cookies.write_text(
            "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tREDACTED\n",
            encoding="utf-8",
        )
        cookie_check = check_youtube_cookies(cookies)
        assert_true("cookies ok", cookie_check.status == "ok", failures, json.dumps(cookie_check.as_dict()))
        empty = tmp_path / "empty.cookies.txt"
        empty.write_text("", encoding="utf-8")
        empty_check = check_youtube_cookies(empty)
        assert_true("empty cookies warn", empty_check.status == "warn", failures)
        no_header = tmp_path / "no_header.cookies.txt"
        no_header.write_text(".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tREDACTED\n", encoding="utf-8")
        no_header_check = check_youtube_cookies(no_header)
        assert_true("cookies without Netscape header warn", no_header_check.status == "warn", failures)

    utf8 = check_utf8_write()
    assert_true("utf8 write", utf8.status == "ok", failures, json.dumps(utf8.as_dict(), ensure_ascii=False))
    md = render_markdown(
        {
            "generated_at": "2026-06-29T00:00:00+00:00",
            "overall_status": "ok",
            "capabilities": {"safe_utf8_artifact_writes": True},
            "checks": [ok.as_dict()],
        }
    )
    assert_true("markdown render", "Overall status" in md and "ok_check" in md, failures)
    with tempfile.TemporaryDirectory(prefix="kw-doctor-output-") as tmp:
        out = Path(tmp) / "doctor.json"
        args_no_overwrite = argparse.Namespace(output_json=str(out), output_md=None, overwrite=False)
        args_overwrite = argparse.Namespace(output_json=str(out), output_md=None, overwrite=True)
        report = {
            "doctor": DOCTOR_NAME,
            "generated_at": "2026-06-29T00:00:00+00:00",
            "overall_status": "ok",
            "checks": [],
            "capabilities": {},
            "privacy": {},
        }
        write_outputs(report, args_no_overwrite)
        no_overwrite_failed = False
        try:
            write_outputs(report, args_no_overwrite)
        except ArtifactWriteError:
            no_overwrite_failed = True
        assert_true("no-overwrite refuses existing output", no_overwrite_failed, failures)
        write_outputs(report, args_overwrite)
        assert_true("overwrite replaces existing output", out.is_file(), failures)

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
        report = build_report(args)
        write_outputs(report, args)
    except (ArtifactWriteError, OSError) as exc:
        payload = {
            "doctor": DOCTOR_NAME,
            "overall_status": "fail",
            "error": exc.__class__.__name__,
            "message": str(exc),
        }
        sys.stderr.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return 1

    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=args.pretty))
    sys.stdout.write("\n")
    return 0 if report["overall_status"] in {"ok", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
