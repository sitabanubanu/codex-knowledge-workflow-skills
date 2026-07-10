"""Agent-Reach acquisition adapter.

This module intentionally keeps acquisition separate from source judgment. It
creates acquisition bundles and never approves evidence or reports.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

from . import bundle


SUPPORTED_PLATFORMS = {
    "web",
    "youtube",
    "bilibili",
    "github",
    "search",
    "local_file",
    "x",
    "xiaohongshu",
}
AGENT_REACH_INSTALL_SOURCE = "https://github.com/Panniantong/Agent-Reach/archive/main.zip"
LOGIN_REQUIRED_PLATFORMS = {"x", "xiaohongshu"}


PLATFORM_SETUP_HINTS = {
    "x": {
        "agent_reach_channel": "twitter",
        "install_commands": [
            "python kw.py agent-reach install --channels twitter",
            "agent-reach install --channels twitter",
        ],
        "manual_steps": [
            "Install twitter-cli or OpenCLI as reported by agent-reach doctor.",
            "For twitter-cli, configure TWITTER_AUTH_TOKEN and TWITTER_CT0 from a user-authorized browser session.",
            "For OpenCLI, keep Chrome open and logged in to x.com.",
        ],
    },
    "xiaohongshu": {
        "agent_reach_channel": "xiaohongshu/opencli",
        "install_commands": [
            "python kw.py agent-reach install --channels opencli",
            "agent-reach install --channels opencli",
        ],
        "manual_steps": [
            "Install the OpenCLI Chrome extension when prompted by Agent-Reach.",
            "Keep Chrome open and logged in to xiaohongshu.com.",
            "Use a full note URL that includes xsec_token; when missing, search/feed first and read the returned URL.",
        ],
    },
}


class AgentReachAdapterError(Exception):
    """Raised when the adapter cannot create a bundle."""


def detect_platform(value: str) -> str:
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    if not parsed.scheme and Path(value).exists():
        return "local_file"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if host in {"x.com", "twitter.com"} or host.endswith(".x.com") or host.endswith(".twitter.com"):
        return "x"
    if "xiaohongshu.com" in host or "xhslink.com" in host:
        return "xiaohongshu"
    if "bilibili.com" in host or "b23.tv" in host:
        return "bilibili"
    if "github.com" in host:
        return "github"
    if parsed.scheme in {"http", "https"} and host:
        return "web"
    return "search"


def source_id_for(value: str, platform: str) -> str:
    parsed = urlparse(value)
    if platform == "youtube":
        query = parsed.query
        for part in query.split("&"):
            if part.startswith("v="):
                return part.split("=", 1)[1]
        return Path(parsed.path).name or "youtube"
    if platform == "github":
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        return "/".join(parts[:2]) if len(parts) >= 2 else (Path(parsed.path).name or "github")
    if platform == "bilibili":
        return Path(parsed.path.strip("/")).name or "bilibili"
    if platform in {"x", "xiaohongshu"}:
        return parsed.netloc + parsed.path
    if platform == "web":
        return parsed.netloc + parsed.path
    return Path(value).stem or "source"


def sanitize_command(command: list[str]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    sensitive_markers = ("cookie", "token", "authorization", "password", "secret")
    for item in command:
        lowered = item.lower()
        if redact_next:
            redacted.append("[REDACTED]")
            redact_next = False
            continue
        if any(marker in lowered for marker in sensitive_markers):
            if "=" in item:
                key = item.split("=", 1)[0]
                redacted.append(f"{key}=[REDACTED]")
            elif ":" in item:
                key = item.split(":", 1)[0]
                redacted.append(f"{key}:[REDACTED]")
            elif "?" in item:
                redacted.append("[REDACTED_URL_WITH_SECRET_QUERY]")
            else:
                redacted.append(item)
                redact_next = True
            continue
        redacted.append(item)
    return redacted


def redact_value_for_record(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.query:
        return value
    sensitive_markers = ("cookie", "token", "authorization", "password", "secret", "session")
    pairs = []
    changed = False
    for key, item_value in parse_qsl(parsed.query, keep_blank_values=True):
        if any(marker in key.lower() for marker in sensitive_markers):
            pairs.append((key, "[REDACTED]"))
            changed = True
        else:
            pairs.append((key, item_value))
    if not changed:
        return value
    return urlunparse(parsed._replace(query=urlencode(pairs, doseq=True)))


def append_command_log(log_path: Path, *, command: list[str], returncode: int, note: str = "") -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "command": sanitize_command(command),
        "returncode": returncode,
        "note": note,
        "secrets_redacted": True,
    }
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def resolve_command_for_subprocess(command: list[str]) -> list[str]:
    if not command:
        return command
    executable = command[0]
    if Path(executable).is_absolute() or "\\" in executable or "/" in executable:
        return command
    resolved = shutil.which(executable)
    if resolved:
        return [resolved, *command[1:]]
    if sys.platform == "win32":
        for suffix in (".cmd", ".exe", ".bat"):
            resolved = shutil.which(executable + suffix)
            if resolved:
                return [resolved, *command[1:]]
    return command


def run_capture(command: list[str], *, cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        resolve_command_for_subprocess(command),
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )


def write_doctor(project_root: Path, command_log: Path) -> dict[str, Any]:
    doctor_path = project_root / "00_acquisition" / "logs" / "agent_reach_doctor.json"
    command = ["agent-reach", "doctor", "--json"]
    try:
        completed = run_capture(command, timeout=90)
    except (OSError, subprocess.SubprocessError) as exc:
        append_command_log(command_log, command=command, returncode=1, note=str(exc))
        payload = {"error": str(exc), "status": "failed"}
        bundle.write_json(doctor_path, payload)
        return payload
    append_command_log(command_log, command=command, returncode=completed.returncode)
    if completed.returncode == 0:
        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError:
            payload = {"raw_stdout": completed.stdout, "status": "unparseable"}
    else:
        payload = {
            "status": "failed",
            "returncode": completed.returncode,
            "stderr": completed.stderr[-2000:],
        }
    bundle.write_json(doctor_path, payload)
    return payload if isinstance(payload, dict) else {"doctor": payload}


def active_backend_from_doctor(doctor: dict[str, Any], platform: str) -> str:
    if platform == "search":
        platform = "exa_search"
    if platform == "x":
        platform = "twitter"
    item = doctor.get(platform)
    if isinstance(item, dict):
        return str(item.get("active_backend") or "")
    return ""


def doctor_key_for_platform(platform: str) -> str:
    if platform == "search":
        return "exa_search"
    if platform == "x":
        return "twitter"
    return platform


def doctor_item_for_platform(doctor: dict[str, Any], platform: str) -> dict[str, Any]:
    item = doctor.get(doctor_key_for_platform(platform))
    return item if isinstance(item, dict) else {}


def active_backend_is_ready(doctor: dict[str, Any], platform: str) -> bool:
    item = doctor_item_for_platform(doctor, platform)
    return bool(active_backend_from_doctor(doctor, platform)) and item.get("status") == "ok"


def web_fallback_backend(doctor: dict[str, Any]) -> str:
    item = doctor.get("web")
    if isinstance(item, dict) and item.get("active_backend"):
        return str(item["active_backend"])
    return "Jina Reader"


def is_probable_xhs_note_url(value: str) -> bool:
    parsed = urlparse(value)
    return "xiaohongshu.com" in parsed.netloc.lower() and "/explore/" in parsed.path


def xhs_note_parts(value: str) -> tuple[str, str]:
    parsed = urlparse(value)
    note_id = Path(parsed.path.strip("/")).name if parsed.path else ""
    xsec_token = parse_qs(parsed.query).get("xsec_token", [""])[0]
    return note_id, xsec_token


def route_plan_for(platform: str, doctor: dict[str, Any], input_value: str) -> dict[str, Any]:
    item = doctor_item_for_platform(doctor, platform)
    active_backend = active_backend_from_doctor(doctor, platform)
    plan: dict[str, Any] = {
        "platform": platform,
        "doctor_key": doctor_key_for_platform(platform),
        "doctor_status": item.get("status") or "",
        "doctor_message": item.get("message") or "",
        "active_backend": active_backend,
        "active_backend_ready": active_backend_is_ready(doctor, platform),
        "backend_order": item.get("backends") or [],
        "uses_agent_reach_active_backend": active_backend_is_ready(doctor, platform),
        "anonymous_web_fallback_allowed": platform not in LOGIN_REQUIRED_PLATFORMS,
        "install_commands": [],
        "preferred_commands": [],
        "manual_steps": [],
        "source_boundary": "Only acquired primary text, transcript, subtitle, or audio-derived transcript may enter full analysis.",
    }

    hints = PLATFORM_SETUP_HINTS.get(platform)
    if hints and not active_backend_is_ready(doctor, platform):
        plan["install_commands"] = hints["install_commands"]
        plan["manual_steps"] = hints["manual_steps"]
    if active_backend and not active_backend_is_ready(doctor, platform):
        plan["blocked_until_ready_reason"] = "Agent-Reach selected this backend, but doctor did not report status ok."

    if platform == "x":
        if active_backend == "twitter-cli":
            plan["preferred_commands"] = ["twitter tweet <URL_OR_ID>"]
            plan["primary_scope"] = "tweet_text_and_thread_context_if_returned; not video transcript"
        elif active_backend == "OpenCLI":
            plan["preferred_commands"] = [
                "opencli twitter article <URL_OR_ID> -f yaml",
                "opencli twitter user-posts <USERNAME> -f yaml",
                "opencli twitter search <QUERY> -f yaml",
            ]
            plan["primary_scope"] = "documented OpenCLI Twitter routes; single status URLs may still require twitter-cli or browser export"
        elif not active_backend:
            plan["blocked_without_backend_reason"] = "Twitter/X is a login/session platform in Agent-Reach; do not retry anonymous Jina/curl as the main route."
    elif platform == "xiaohongshu":
        if active_backend == "OpenCLI":
            plan["preferred_commands"] = ["opencli xiaohongshu note <NOTE_URL_WITH_XSEC_TOKEN> -f yaml"]
            plan["primary_scope"] = "note_text_and_visible_engagement_data; not embedded video transcript"
        elif active_backend == "xiaohongshu-mcp":
            plan["preferred_commands"] = [
                "mcporter call 'xiaohongshu.check_login_status()' --timeout 120000",
                "mcporter call 'xiaohongshu.get_feed_detail(feed_id: <NOTE_ID>, xsec_token: <XSEC_TOKEN>)' --timeout 120000",
            ]
            plan["primary_scope"] = "note_text_and_comments_returned_by_mcp; not embedded video transcript"
        elif active_backend.startswith("xhs-cli"):
            plan["preferred_commands"] = ["xhs read <NOTE_URL_OR_ID_FROM_SEARCH_RESULT>"]
            plan["primary_scope"] = "note_text_returned_by_xhs_cli; not embedded video transcript"
        elif not active_backend:
            plan["blocked_without_backend_reason"] = "Xiaohongshu requires an authorized OpenCLI/MCP/xhs route; anonymous page readers usually see only a shell or login page."
        if is_probable_xhs_note_url(input_value):
            _, xsec_token = xhs_note_parts(input_value)
            if not xsec_token:
                plan["manual_steps"] = [
                    *plan.get("manual_steps", []),
                    "This note URL has no xsec_token. Search/feed first, then read the returned full URL.",
                ]
    elif platform == "youtube":
        plan["preferred_commands"] = [
            'yt-dlp --dump-json "<URL>"',
            'yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en" --skip-download -o "<OUT>/%(id)s" "<URL>"',
            'agent-reach transcribe "<URL_OR_LOCAL_AUDIO>"',
        ]
        plan["manual_steps"] = [
            "If yt-dlp reports sign-in, bot check, or cookie errors, use user-authorized YouTube cookies or provide local audio/video/transcript material.",
            "Do not bypass CAPTCHA or account permissions; only analyze material the user is authorized to access.",
        ]
        plan["primary_scope"] = "subtitle/transcript/audio-derived transcript"
    elif platform == "bilibili":
        plan["preferred_commands"] = [
            "bili video <BV_ID_OR_URL>",
            "opencli bilibili subtitle <BV_ID>",
            "bili audio <BV_ID>",
        ]
        plan["primary_scope"] = "subtitle or audio-derived transcript; bili metadata alone is metadata_only"
    elif platform == "search":
        plan["preferred_commands"] = ["mcporter call exa.web_search_exa query=<QUERY> numResults=5"]
        plan["primary_scope"] = "search results are secondary triage material, not primary evidence"
    return plan


def write_route_plan(project_root: Path, plan: dict[str, Any]) -> Path:
    path = project_root / "00_acquisition" / "logs" / "route_plan.json"
    bundle.write_json(path, plan)
    return path


def jina_error_reason(stdout: str) -> str:
    text = stdout.strip()
    if not text.startswith("{"):
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""
    if payload.get("data") is not None:
        return ""
    reason = payload.get("readableMessage") or payload.get("message") or payload.get("name")
    return str(reason) if reason else ""


def blocked_status_from_reason(reason: str) -> str:
    lowered = reason.lower()
    blockers = (
        "403",
        "blocked",
        "captcha",
        "login",
        "sign in",
        "not a bot",
        "anonymous access",
        "permission",
        "paywall",
        "private",
        "too many requests",
    )
    return "blocked" if any(marker in lowered for marker in blockers) else "failed"


def primary_missing_limit(platform: str, status: str) -> list[str]:
    if status in {"material_acquired", "partial_material_acquired"}:
        return []
    if platform in {"youtube", "bilibili"}:
        return ["No primary transcript/subtitle was confirmed by acquisition."]
    if platform in {"x", "xiaohongshu", "web", "github"}:
        return ["No primary page text, transcript, subtitle, or media-derived transcript was confirmed by acquisition."]
    return ["No primary material was confirmed by acquisition."]


def youtube_next_action(failures: list[dict[str, Any]], *, metadata_only: bool = False) -> str:
    text = "\n".join(str(item.get("reason", "")) for item in failures if isinstance(item, dict)).lower()
    if any(marker in text for marker in ("sign in", "not a bot", "bot", "cookies", "captcha", "429", "403")):
        return (
            "Resolve YouTube access with user-authorized cookies/browser material, "
            "or provide transcript, subtitle, local audio/video, or an audio-derived transcript."
        )
    if metadata_only:
        return "Provide transcript/subtitle, authorized local audio/video, or run an authorized transcription route."
    return "Provide transcript/subtitle or authorized local audio/video."


def make_failed_manifest(
    *,
    project_root: Path,
    input_value: str,
    platform: str,
    status: str,
    reason: str,
    active_backend: str = "",
    source_url: str = "",
    metadata: dict[str, Any] | None = None,
    next_action: str | None = None,
) -> Path:
    manifest = bundle.make_manifest(
        project_root=project_root,
        input_value=redact_value_for_record(input_value),
        source_url=redact_value_for_record(source_url if source_url else input_value if urlparse(input_value).scheme else ""),
        source_id=source_id_for(input_value, platform),
        platform=platform,
        acquisition_layer="agent-reach",
        active_backend=active_backend,
        status=status,
        artifacts=[],
        metadata=metadata or {},
        privacy={
            "cookies_used": False,
            "browser_session_used": False,
            "secrets_redacted": True,
            "contains_user_private_data": False,
        },
        limits=[reason],
        failures=[{"stage": "acquisition", "reason": reason}],
        next_action=next_action or "Provide transcript, subtitle, local audio/video, or supported authorized material.",
    )
    notes = project_root / "00_acquisition" / "logs" / "acquisition_notes.md"
    bundle.write_text(notes, f"# Acquisition Failed\n\n- Platform: `{platform}`\n- Reason: {reason}\n")
    return bundle.write_manifest(project_root, manifest)


def _write_stdout_artifact(path: Path, stdout: str) -> bool:
    if not stdout.strip():
        return False
    bundle.write_text(path, stdout)
    return path.is_file() and path.stat().st_size > 0


def command_blocked_status(completed: subprocess.CompletedProcess[str]) -> str:
    text = f"{completed.stdout}\n{completed.stderr}".lower()
    blockers = (
        "auth_required",
        "login",
        "not_authenticated",
        "captcha",
        "verify",
        "403",
        "429",
        "blocked",
        "sign in",
        "permission",
    )
    return "blocked" if any(marker in text for marker in blockers) else "failed"


def stdout_primary_artifact(
    *,
    bundle_root: Path,
    path: Path,
    stdout: str,
    artifact_type: str,
    description: str,
    created_by: str,
) -> list[dict[str, Any]]:
    if not _write_stdout_artifact(path, stdout):
        return []
    return [
        bundle.artifact_entry(
            bundle_root=bundle_root,
            path=path,
            artifact_type=artifact_type,
            source_class="primary",
            description=description,
            created_by=created_by,
        )
    ]


def acquire_web(input_value: str, project_root: Path, command_log: Path) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str]:
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"
    output = artifacts_root / "page.md"
    reader_url = "https://r.jina.ai/" + input_value
    command = ["curl", "-L", "--max-time", "45", reader_url]
    try:
        completed = run_capture(command, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        append_command_log(command_log, command=command, returncode=1, note=str(exc))
        return "failed", [], {}, [{"stage": "web", "reason": str(exc)}], "Provide a local page export or try again later."
    append_command_log(command_log, command=command, returncode=completed.returncode, note="Jina Reader route")
    if completed.returncode == 0:
        error_reason = jina_error_reason(completed.stdout)
        if error_reason:
            return blocked_status_from_reason(error_reason), [], {}, [{"stage": "web_jina", "reason": error_reason}], "Provide a local page export or use an authorized browser/session route."
    if completed.returncode == 0 and _write_stdout_artifact(output, completed.stdout):
        entry = bundle.artifact_entry(
            bundle_root=bundle_root,
            path=output,
            artifact_type="page_markdown",
            source_class="secondary",
            description="Web page Markdown acquired through Jina Reader route.",
            created_by="curl_jina_reader",
        )
        return "secondary_only", [entry], {"reader_url": redact_value_for_record(reader_url)}, [], "Ingest as secondary/degraded material unless this page is the primary source."
    return "failed", [], {}, [{"stage": "web", "reason": completed.stderr[-1000:] or "empty page output"}], "Provide page text or a supported primary artifact."


def acquire_x(
    input_value: str,
    project_root: Path,
    command_log: Path,
    *,
    doctor: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str, str, dict[str, bool]]:
    active_backend = active_backend_from_doctor(doctor, "x")
    plan = route_plan_for("x", doctor, input_value)
    metadata = {"route_plan": plan}
    privacy = {"cookies_used": False, "browser_session_used": False}
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"

    if not active_backend_is_ready(doctor, "x"):
        item = doctor_item_for_platform(doctor, "x")
        return (
            "blocked",
            [],
            metadata,
            [
                {
                    "stage": "twitter_active_backend",
                    "reason": item.get("message")
                    or "No ready Agent-Reach Twitter/X backend is active. Configure twitter-cli or OpenCLI before reading X.",
                }
            ],
            "Run `python kw.py agent-reach install --channels twitter` or configure OpenCLI/browser session, then retry.",
            active_backend,
            privacy,
        )

    if active_backend == "twitter-cli":
        command = ["twitter", "tweet", input_value]
        output = artifacts_root / "x_tweet.txt"
        privacy["cookies_used"] = True
        try:
            completed = run_capture(command, timeout=90)
        except (OSError, subprocess.SubprocessError) as exc:
            append_command_log(command_log, command=command, returncode=1, note=str(exc))
            return "failed", [], metadata, [{"stage": "twitter_cli", "reason": str(exc)}], "Install/configure twitter-cli or provide primary material.", active_backend, privacy
        append_command_log(command_log, command=command, returncode=completed.returncode, note="Agent-Reach Twitter/X twitter-cli route")
        if completed.returncode == 0:
            artifacts = stdout_primary_artifact(
                bundle_root=bundle_root,
                path=output,
                stdout=completed.stdout,
                artifact_type="page_text",
                description="Tweet text/thread context acquired through twitter-cli.",
                created_by="twitter-cli",
            )
            if artifacts:
                metadata["primary_scope"] = "tweet_text_not_embedded_video_transcript"
                return "material_acquired", artifacts, metadata, [], "ingest_bundle", active_backend, privacy
        reason = completed.stderr[-1000:] or completed.stdout[-1000:] or "empty twitter-cli output"
        return command_blocked_status(completed), [], metadata, [{"stage": "twitter_cli", "reason": reason}], "Refresh Twitter/X authorization or provide primary material.", active_backend, privacy

    if active_backend == "OpenCLI":
        return (
            "blocked",
            [],
            metadata,
            [
                {
                    "stage": "twitter_opencli_single_status",
                    "reason": "Agent-Reach documents OpenCLI for Twitter search/article/user-posts; this adapter does not yet treat a single status URL as a documented OpenCLI primary route.",
                }
            ],
            "Use twitter-cli for single tweet URLs, or export browser-visible text/media subtitles through Chrome/OpenCLI and provide the artifact.",
            active_backend,
            {"cookies_used": False, "browser_session_used": True},
        )

    return (
        "unsupported",
        [],
        metadata,
        [{"stage": "twitter_backend", "reason": f"Unsupported Twitter/X backend for this adapter: {active_backend}"}],
        "Use a documented Agent-Reach Twitter/X route or provide local primary material.",
        active_backend,
        privacy,
    )


def acquire_xiaohongshu(
    input_value: str,
    project_root: Path,
    command_log: Path,
    *,
    doctor: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str, str, dict[str, bool]]:
    active_backend = active_backend_from_doctor(doctor, "xiaohongshu")
    plan = route_plan_for("xiaohongshu", doctor, input_value)
    metadata = {"route_plan": plan}
    privacy = {"cookies_used": False, "browser_session_used": False}
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"

    if not active_backend_is_ready(doctor, "xiaohongshu"):
        item = doctor_item_for_platform(doctor, "xiaohongshu")
        return (
            "blocked",
            [],
            metadata,
            [
                {
                    "stage": "xiaohongshu_active_backend",
                    "reason": item.get("message")
                    or "No ready Agent-Reach Xiaohongshu backend is active. Configure OpenCLI/browser session or xiaohongshu-mcp before reading notes.",
                }
            ],
            "Run `python kw.py agent-reach install --channels opencli`, install the Chrome extension, log in to Xiaohongshu in Chrome, then retry.",
            active_backend,
            privacy,
        )

    if active_backend == "OpenCLI":
        command = ["opencli", "xiaohongshu", "note", input_value, "-f", "yaml"]
        output = artifacts_root / "xiaohongshu_note.yaml"
        privacy["browser_session_used"] = True
        try:
            completed = run_capture(command, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            append_command_log(command_log, command=command, returncode=1, note=str(exc))
            return "failed", [], metadata, [{"stage": "xiaohongshu_opencli", "reason": str(exc)}], "Install/configure OpenCLI or provide primary material.", active_backend, privacy
        append_command_log(command_log, command=command, returncode=completed.returncode, note="Agent-Reach Xiaohongshu OpenCLI route")
        if completed.returncode == 0:
            artifacts = stdout_primary_artifact(
                bundle_root=bundle_root,
                path=output,
                stdout=completed.stdout,
                artifact_type="page_text",
                description="Xiaohongshu note text acquired through OpenCLI browser-session route.",
                created_by="opencli_xiaohongshu",
            )
            if artifacts:
                metadata["primary_scope"] = "note_text_not_embedded_video_transcript"
                return "material_acquired", artifacts, metadata, [], "ingest_bundle", active_backend, privacy
        reason = completed.stderr[-1000:] or completed.stdout[-1000:] or "empty OpenCLI output"
        return command_blocked_status(completed), [], metadata, [{"stage": "xiaohongshu_opencli", "reason": reason}], "Refresh Xiaohongshu login in Chrome, keep OpenCLI extension active, or provide primary material.", active_backend, privacy

    if active_backend == "xiaohongshu-mcp":
        note_id, xsec_token = xhs_note_parts(input_value)
        if not note_id or not xsec_token:
            return (
                "blocked",
                [],
                metadata,
                [{"stage": "xiaohongshu_mcp_route", "reason": "xiaohongshu-mcp requires feed_id and xsec_token from search/feed output."}],
                "Search/feed first, then retry with a full Xiaohongshu note URL containing xsec_token.",
                active_backend,
                privacy,
            )
        command = [
            "mcporter",
            "call",
            f'xiaohongshu.get_feed_detail(feed_id: "{note_id}", xsec_token: "{xsec_token}")',
            "--timeout",
            "120000",
        ]
        output = artifacts_root / "xiaohongshu_note.json"
        privacy["browser_session_used"] = True
        try:
            completed = run_capture(command, timeout=140)
        except (OSError, subprocess.SubprocessError) as exc:
            append_command_log(command_log, command=command, returncode=1, note=str(exc))
            return "failed", [], metadata, [{"stage": "xiaohongshu_mcp", "reason": str(exc)}], "Start/login xiaohongshu-mcp or provide primary material.", active_backend, privacy
        append_command_log(command_log, command=command, returncode=completed.returncode, note="Agent-Reach Xiaohongshu MCP route")
        if completed.returncode == 0:
            artifacts = stdout_primary_artifact(
                bundle_root=bundle_root,
                path=output,
                stdout=completed.stdout,
                artifact_type="page_text",
                description="Xiaohongshu note detail acquired through xiaohongshu-mcp.",
                created_by="xiaohongshu-mcp",
            )
            if artifacts:
                metadata["primary_scope"] = "note_text_and_mcp_returned_comments_not_embedded_video_transcript"
                return "material_acquired", artifacts, metadata, [], "ingest_bundle", active_backend, privacy
        reason = completed.stderr[-1000:] or completed.stdout[-1000:] or "empty MCP output"
        return command_blocked_status(completed), [], metadata, [{"stage": "xiaohongshu_mcp", "reason": reason}], "Check xiaohongshu-mcp login status or provide primary material.", active_backend, privacy

    if active_backend.startswith("xhs-cli"):
        command = ["xhs", "read", input_value]
        output = artifacts_root / "xiaohongshu_note.txt"
        privacy["cookies_used"] = True
        try:
            completed = run_capture(command, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            append_command_log(command_log, command=command, returncode=1, note=str(exc))
            return "failed", [], metadata, [{"stage": "xhs_cli", "reason": str(exc)}], "Configure xhs-cli or provide primary material.", active_backend, privacy
        append_command_log(command_log, command=command, returncode=completed.returncode, note="Agent-Reach Xiaohongshu xhs-cli route")
        if completed.returncode == 0:
            artifacts = stdout_primary_artifact(
                bundle_root=bundle_root,
                path=output,
                stdout=completed.stdout,
                artifact_type="page_text",
                description="Xiaohongshu note text acquired through xhs-cli.",
                created_by="xhs-cli",
            )
            if artifacts:
                metadata["primary_scope"] = "note_text_not_embedded_video_transcript"
                return "material_acquired", artifacts, metadata, [], "ingest_bundle", active_backend, privacy
        reason = completed.stderr[-1000:] or completed.stdout[-1000:] or "empty xhs-cli output"
        return command_blocked_status(completed), [], metadata, [{"stage": "xhs_cli", "reason": reason}], "Refresh xhs-cli authorization or provide primary material.", active_backend, privacy

    return (
        "unsupported",
        [],
        metadata,
        [{"stage": "xiaohongshu_backend", "reason": f"Unsupported Xiaohongshu backend for this adapter: {active_backend}"}],
        "Use a documented Agent-Reach Xiaohongshu route or provide local primary material.",
        active_backend,
        privacy,
    )


def acquire_youtube(input_value: str, project_root: Path, command_log: Path) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str]:
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"
    metadata_path = artifacts_root / "metadata.json"
    output_template = str(artifacts_root / "youtube.%(ext)s")
    metadata_command = ["yt-dlp", "--skip-download", "--dump-single-json", input_value]
    subtitle_command = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "all,-live_chat",
        "--convert-subs",
        "vtt",
        "-o",
        output_template,
        input_value,
    ]
    artifacts: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    failures: list[dict[str, Any]] = []
    try:
        meta = run_capture(metadata_command, timeout=90)
        append_command_log(command_log, command=metadata_command, returncode=meta.returncode, note="yt-dlp metadata")
        if meta.returncode == 0 and meta.stdout.strip():
            try:
                parsed = json.loads(meta.stdout)
                bundle.write_json(metadata_path, parsed)
                artifacts.append(
                    bundle.artifact_entry(
                        bundle_root=bundle_root,
                        path=metadata_path,
                        artifact_type="metadata",
                        source_class="metadata_only",
                        description="yt-dlp metadata.",
                        created_by="yt-dlp",
                    )
                )
                metadata["title"] = parsed.get("title")
            except json.JSONDecodeError:
                bundle.write_text(metadata_path, meta.stdout)
        else:
            failures.append({"stage": "youtube_metadata", "reason": meta.stderr[-1000:]})
        subs = run_capture(subtitle_command, timeout=120)
        append_command_log(command_log, command=subtitle_command, returncode=subs.returncode, note="yt-dlp subtitles")
    except (OSError, subprocess.SubprocessError) as exc:
        failures.append({"stage": "youtube", "reason": str(exc)})
        return "failed", artifacts, metadata, failures, youtube_next_action(failures)

    subtitle_files = sorted(artifacts_root.glob("youtube*.vtt")) + sorted(artifacts_root.glob("youtube*.srt"))
    for subtitle in subtitle_files:
        artifacts.append(
            bundle.artifact_entry(
                bundle_root=bundle_root,
                path=subtitle,
                artifact_type="subtitle",
                source_class="primary",
                description="Subtitle acquired by yt-dlp.",
                created_by="yt-dlp",
            )
        )
    if any(item.get("source_class") == "primary" for item in artifacts):
        return "material_acquired", artifacts, metadata, failures, "ingest_bundle"
    if artifacts:
        return "metadata_only", artifacts, metadata, failures, youtube_next_action(failures, metadata_only=True)
    return "blocked" if failures else "failed", artifacts, metadata, failures, youtube_next_action(failures)


def acquire_bilibili(input_value: str, project_root: Path, command_log: Path) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str]:
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"
    metadata_path = artifacts_root / "metadata.json"
    command = ["bili", "video", input_value]
    try:
        completed = run_capture(command, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        append_command_log(command_log, command=command, returncode=1, note=str(exc))
        return "failed", [], {}, [{"stage": "bilibili", "reason": str(exc)}], "Provide Bilibili subtitle/transcript or local media."
    append_command_log(command_log, command=command, returncode=completed.returncode, note="bili-cli metadata")
    if completed.returncode == 0 and _write_stdout_artifact(metadata_path, completed.stdout):
        entry = bundle.artifact_entry(
            bundle_root=bundle_root,
            path=metadata_path,
            artifact_type="metadata",
            source_class="metadata_only",
            description="Bilibili metadata/detail output.",
            created_by="bili-cli",
        )
        return "metadata_only", [entry], {}, [], "Provide subtitles, transcript, or local media for ASR before full analysis."
    return "failed", [], {}, [{"stage": "bilibili", "reason": completed.stderr[-1000:] or "empty metadata output"}], "Provide subtitle/transcript or local media."


def copy_repo_readme(clone_root: Path, output_path: Path) -> bool:
    readmes = sorted(
        path
        for path in clone_root.iterdir()
        if path.is_file() and path.name.lower().startswith("readme")
    )
    if not readmes:
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(readmes[0], output_path)
    return output_path.is_file() and output_path.stat().st_size > 0


def acquire_github(input_value: str, project_root: Path, command_log: Path) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str]:
    platform_id = source_id_for(input_value, "github")
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"
    metadata_path = artifacts_root / "metadata.json"
    readme_path = artifacts_root / "page.md"
    metadata_command = ["gh", "repo", "view", platform_id, "--json", "name,description,url,homepageUrl"]
    artifacts: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    try:
        completed = run_capture(metadata_command, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        append_command_log(command_log, command=metadata_command, returncode=1, note=str(exc))
        failures.append({"stage": "gh metadata", "reason": str(exc)})
    else:
        append_command_log(command_log, command=metadata_command, returncode=completed.returncode, note="gh metadata")
        if completed.returncode == 0 and _write_stdout_artifact(metadata_path, completed.stdout):
            artifacts.append(
                bundle.artifact_entry(
                    bundle_root=bundle_root,
                    path=metadata_path,
                    artifact_type="metadata",
                    source_class="metadata_only",
                    description="gh metadata",
                    created_by="gh",
                )
            )
        else:
            failures.append({"stage": "gh metadata", "reason": completed.stderr[-1000:] or "empty output"})

    with tempfile.TemporaryDirectory(prefix="kw-gh-readme-") as tmp:
        clone_target = Path(tmp) / "repo"
        clone_command = ["gh", "repo", "clone", platform_id, str(clone_target), "--", "--depth", "1"]
        try:
            completed = run_capture(clone_command, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            append_command_log(command_log, command=clone_command, returncode=1, note=str(exc))
            failures.append({"stage": "gh readme", "reason": str(exc)})
        else:
            append_command_log(command_log, command=clone_command, returncode=completed.returncode, note="gh readme clone")
            if completed.returncode == 0 and copy_repo_readme(clone_target, readme_path):
                artifacts.append(
                    bundle.artifact_entry(
                        bundle_root=bundle_root,
                        path=readme_path,
                        artifact_type="page_markdown",
                        source_class="primary",
                        description="README file copied from a shallow GitHub repository clone.",
                        created_by="gh_repo_clone",
                    )
                )
            else:
                failures.append({"stage": "gh readme", "reason": completed.stderr[-1000:] or "README file was not found"})
    if any(item.get("source_class") == "primary" for item in artifacts):
        return "material_acquired", artifacts, {}, failures, "ingest_bundle"
    if artifacts:
        return "metadata_only", artifacts, {}, failures, "Provide README/source text export if full source analysis is needed."
    return "failed", [], {}, failures, "Install/authenticate gh CLI or provide local source material."


def acquire_search(input_value: str, project_root: Path, command_log: Path) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str]:
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"
    output = artifacts_root / "search_results.md"
    command = ["mcporter", "call", "exa.web_search_exa", f"query={input_value}", "numResults=5"]
    try:
        completed = run_capture(command, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        append_command_log(command_log, command=command, returncode=1, note=str(exc))
        return "failed", [], {}, [{"stage": "search", "reason": str(exc)}], "Install/configure Agent-Reach search or provide primary local material."
    append_command_log(command_log, command=command, returncode=completed.returncode, note="Agent-Reach Exa search via mcporter")
    if completed.returncode == 0 and _write_stdout_artifact(output, completed.stdout):
        entry = bundle.artifact_entry(
            bundle_root=bundle_root,
            path=output,
            artifact_type="search_result",
            source_class="secondary",
            description="Search results acquired through Agent-Reach search route.",
            created_by="mcporter_exa",
        )
        return "secondary_only", [entry], {"query": input_value}, [], "Use search results only for triage; provide primary material for full analysis."
    return "failed", [], {}, [{"stage": "search", "reason": completed.stderr[-1000:] or "empty search output"}], "Provide primary material or configure Agent-Reach search."


def acquire_with_agent_reach(*, input_value: str, project_root: Path) -> Path:
    project_root = project_root.resolve()
    bundle_root = project_root / "00_acquisition"
    (bundle_root / "artifacts").mkdir(parents=True, exist_ok=True)
    (bundle_root / "logs").mkdir(parents=True, exist_ok=True)
    command_log = bundle_root / "logs" / "commands.jsonl"
    platform = detect_platform(input_value)

    if platform == "local_file":
        return bundle.build_local_bundle(input_path=Path(input_value), project_root=project_root)
    if platform not in SUPPORTED_PLATFORMS:
        return make_failed_manifest(
            project_root=project_root,
            input_value=input_value,
            platform=platform,
            status="unsupported",
            reason=f"platform is not supported by the first adapter version: {platform}",
        )
    if shutil.which("agent-reach") is None:
        return make_failed_manifest(
            project_root=project_root,
            input_value=input_value,
            platform=platform,
            status="failed",
            reason="agent-reach command not found",
        )

    doctor = write_doctor(project_root, command_log)
    active_backend = active_backend_from_doctor(doctor, platform)
    route_plan = route_plan_for(platform, doctor, input_value)
    write_route_plan(project_root, route_plan)
    privacy_flags: dict[str, bool] = {
        "cookies_used": False,
        "browser_session_used": False,
    }

    if platform == "web":
        status, artifacts, metadata, failures, next_action = acquire_web(input_value, project_root, command_log)
    elif platform == "youtube":
        status, artifacts, metadata, failures, next_action = acquire_youtube(input_value, project_root, command_log)
    elif platform == "bilibili":
        status, artifacts, metadata, failures, next_action = acquire_bilibili(input_value, project_root, command_log)
    elif platform == "github":
        status, artifacts, metadata, failures, next_action = acquire_github(input_value, project_root, command_log)
    elif platform == "search":
        status, artifacts, metadata, failures, next_action = acquire_search(input_value, project_root, command_log)
    elif platform == "x":
        status, artifacts, metadata, failures, next_action, active_backend, privacy_flags = acquire_x(
            input_value,
            project_root,
            command_log,
            doctor=doctor,
        )
    elif platform == "xiaohongshu":
        status, artifacts, metadata, failures, next_action, active_backend, privacy_flags = acquire_xiaohongshu(
            input_value,
            project_root,
            command_log,
            doctor=doctor,
        )
    else:
        status, artifacts, metadata, failures, next_action = (
            "unsupported",
            [],
            {},
            [{"stage": "routing", "reason": f"unsupported platform: {platform}"}],
            "Provide local primary material.",
        )
    if isinstance(metadata, dict) and "route_plan" not in metadata:
        metadata = {**metadata, "route_plan": route_plan}

    manifest = bundle.make_manifest(
        project_root=project_root,
        input_value=redact_value_for_record(input_value),
        source_url=redact_value_for_record(input_value),
        source_id=source_id_for(input_value, platform),
        platform=platform,
        acquisition_layer="agent-reach",
        active_backend=active_backend,
        status=status,
        artifacts=artifacts,
        metadata=metadata,
        privacy={
            "cookies_used": privacy_flags.get("cookies_used", False),
            "browser_session_used": privacy_flags.get("browser_session_used", False),
            "secrets_redacted": True,
            "contains_user_private_data": False,
        },
        limits=primary_missing_limit(platform, status),
        failures=failures,
        next_action=next_action,
    )
    notes = [
        "# Acquisition Notes",
        "",
        f"- Input: `{input_value}`",
        f"- Platform: `{platform}`",
        f"- Active backend: `{active_backend or 'unknown'}`",
        f"- Status: `{status}`",
        f"- Next action: {next_action}",
        f"- Route plan: `00_acquisition/logs/route_plan.json`",
        "",
    ]
    bundle.write_text(bundle_root / "logs" / "acquisition_notes.md", "\n".join(notes))
    return bundle.write_manifest(project_root, manifest)


def _channel_set(channels: str) -> set[str]:
    return {item.strip().lower() for item in channels.split(",") if item.strip()}


def npm_command() -> str:
    if sys.platform == "win32":
        return shutil.which("npm.cmd") or shutil.which("npm") or "npm.cmd"
    return shutil.which("npm") or "npm"


def install_npm_global(package: str) -> int:
    command = [npm_command(), "install", "-g", package]
    print("Installing npm package: " + package)
    try:
        completed = subprocess.run(resolve_command_for_subprocess(command))
    except OSError as exc:
        print(f"npm install failed to start: {exc}", file=sys.stderr)
        return 1
    return completed.returncode


def configure_exa_search() -> None:
    if shutil.which("mcporter") is None:
        return
    command = ["mcporter", "config", "add", "exa", "https://mcp.exa.ai/mcp"]
    try:
        subprocess.run(resolve_command_for_subprocess(command), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass


def remediate_windows_agent_reach_install(channels: str) -> int:
    if sys.platform != "win32":
        return 0
    requested = _channel_set(channels)
    if not requested:
        requested = set()
    status = 0
    if shutil.which("mcporter") is None:
        status = install_npm_global("mcporter") or status
    configure_exa_search()
    needs_opencli = bool(requested & {"opencli", "xiaohongshu", "reddit", "facebook", "instagram", "all"})
    if needs_opencli and shutil.which("opencli") is None:
        status = install_npm_global("@jackwener/opencli") or status
    return status


def agent_reach_install(*, safe: bool = False, dry_run: bool = False, channels: str = "") -> int:
    if shutil.which("agent-reach") is None:
        bootstrap = [sys.executable, "-m", "pip", "install", AGENT_REACH_INSTALL_SOURCE]
        if dry_run:
            print("[dry-run] Would install Agent-Reach CLI:")
            print("  " + " ".join(bootstrap))
        else:
            print("Installing Agent-Reach CLI...")
            completed = subprocess.run(bootstrap)
            if completed.returncode != 0:
                return completed.returncode

    command = ["agent-reach", "install", "--env=auto"]
    if channels:
        command.extend(["--channels", channels])
    if safe:
        command.append("--safe")
    if dry_run:
        command.append("--dry-run")
        if shutil.which("agent-reach") is None:
            print("[dry-run] Agent-Reach is not installed yet; skipping nested agent-reach install probe.")
            return 0
    try:
        completed = subprocess.run(resolve_command_for_subprocess(command))
    except OSError as exc:
        print(f"agent-reach install failed to start: {exc}", file=sys.stderr)
        return 1
    if not safe and not dry_run:
        remediation_status = remediate_windows_agent_reach_install(channels)
        if completed.returncode == 0 and remediation_status != 0:
            return remediation_status
    return completed.returncode


def agent_reach_doctor(*, output_json: Path | None = None) -> int:
    command = ["agent-reach", "doctor", "--json"]
    try:
        completed = run_capture(command, timeout=90)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"agent-reach doctor failed: {exc}", file=sys.stderr)
        return 1
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(completed.stdout or "{}\n", encoding="utf-8")
    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    return completed.returncode


def agent_reach_route_plan(*, input_value: str, output_json: Path | None = None) -> int:
    platform = detect_platform(input_value)
    command = ["agent-reach", "doctor", "--json"]
    try:
        completed = run_capture(command, timeout=90)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"agent-reach doctor failed: {exc}", file=sys.stderr)
        return 1
    if completed.returncode != 0:
        print(completed.stderr or completed.stdout, file=sys.stderr, end="")
        return completed.returncode
    try:
        doctor = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        print(f"agent-reach doctor returned invalid JSON: {exc}", file=sys.stderr)
        return 1
    plan = route_plan_for(platform, doctor if isinstance(doctor, dict) else {}, input_value)
    payload = {"input": redact_value_for_record(input_value), "platform": platform, "route_plan": plan}
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0
