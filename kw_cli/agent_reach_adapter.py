"""Agent-Reach acquisition adapter.

This module intentionally keeps acquisition separate from source judgment. It
creates acquisition bundles and never approves evidence or reports.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

from . import bundle, canonicalize, run_context, source_gate
from .redaction import redact_text, redact_url, sanitize_command as redact_command, sanitize_data


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
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_YOUTUBE_COOKIES = REPO_ROOT / "work" / "youtube-cookies" / "youtube.cookies.txt"


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
    return redact_command(command)


def redact_value_for_record(value: str) -> str:
    return redact_url(value)


def append_command_log(log_path: Path, *, command: list[str], returncode: int, note: str = "") -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "command": sanitize_command(command),
        "returncode": returncode,
        "note": redact_text(note),
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
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        resolve_command_for_subprocess(command),
        cwd=str(cwd) if cwd else None,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        env=env,
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


def backend_supports_operation(platform: str, backend: str, operation: str, input_value: str) -> bool:
    lowered = backend.lower()
    if not backend:
        return False
    if platform == "bilibili":
        if "search api" in lowered or "搜索 api" in lowered:
            return False
        if backend == "OpenCLI":
            return operation == "extract_transcript"
        return ("bili-cli" in lowered or "bili cli" in lowered) and operation in {"read", "extract_transcript"}
    if platform == "x":
        if "twitter-cli" in lowered:
            return operation == "read" and "/status/" in urlparse(input_value).path
        return False
    if platform == "xiaohongshu":
        return operation == "read"
    if platform == "search":
        return operation == "search"
    if platform == "youtube":
        return operation in {"read", "extract_transcript"}
    if platform in {"web", "github"}:
        return operation == "read"
    return True


def route_plan_for(
    platform: str,
    doctor: dict[str, Any],
    input_value: str,
    *,
    analysis_target: str = "auto",
    operation: str = "auto",
) -> dict[str, Any]:
    item = doctor_item_for_platform(doctor, platform)
    active_backend = active_backend_from_doctor(doctor, platform)
    chosen_target = source_gate.infer_analysis_target(platform, analysis_target)
    chosen_operation = source_gate.infer_operation(chosen_target, operation)
    backend_ready = active_backend_is_ready(doctor, platform)
    operation_supported = backend_supports_operation(platform, active_backend, chosen_operation, input_value)
    plan: dict[str, Any] = {
        "platform": platform,
        "analysis_target": chosen_target,
        "operation": chosen_operation,
        "doctor_key": doctor_key_for_platform(platform),
        "doctor_status": item.get("status") or "",
        "doctor_message": item.get("message") or "",
        "active_backend": active_backend,
        "active_backend_ready": backend_ready,
        "operation_supported": operation_supported,
        "capability_ready": backend_ready and operation_supported,
        "backend_order": item.get("backends") or [],
        "uses_agent_reach_active_backend": backend_ready and operation_supported,
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
    elif active_backend and not operation_supported:
        plan["blocked_until_ready_reason"] = f"The active backend does not support operation {chosen_operation!r} for this input."

    if platform == "x":
        if active_backend == "twitter-cli":
            plan["preferred_commands"] = ["twitter tweet <URL_OR_ID>"]
            plan["primary_scope"] = "tweet_text_and_thread_context_if_returned; not video transcript"
        elif active_backend == "OpenCLI":
            plan["preferred_commands"] = [
                "opencli twitter article <URL_OR_ID> -f json",
                "opencli twitter user-posts <USERNAME> -f json",
                "opencli twitter search <QUERY> -f json",
            ]
            plan["primary_scope"] = "documented OpenCLI Twitter routes; single status URLs may still require twitter-cli or browser export"
        elif not active_backend:
            plan["blocked_without_backend_reason"] = "Twitter/X is a login/session platform in Agent-Reach; do not retry anonymous Jina/curl as the main route."
    elif platform == "xiaohongshu":
        if active_backend == "OpenCLI":
            plan["preferred_commands"] = ["opencli xiaohongshu note <NOTE_URL_WITH_XSEC_TOKEN> -f json"]
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
            "opencli bilibili subtitle <BV_ID> -f json",
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
        "cookie database",
        "failed to decrypt with dpapi",
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
    if "could not copy chrome cookie database" in text or "failed to decrypt with dpapi" in text:
        return (
            "The selected browser profile is locked or unavailable to yt-dlp. "
            "Close that browser only if you approve interruption, or provide a fresh user-exported cookies file, transcript, subtitle, or local media."
        )
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
    run_id: str = "",
    attempt_id: str = "",
    analysis_target: str = "auto",
    operation: str = "auto",
    source_fingerprint: str = "",
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
        run_id=run_id,
        attempt_id=attempt_id,
        analysis_target=analysis_target,
        operation=operation,
        source_fingerprint=source_fingerprint,
    )
    notes = project_root / "00_acquisition" / "logs" / "acquisition_notes.md"
    bundle.write_text(notes, f"# Acquisition Failed\n\n- Platform: `{platform}`\n- Reason: {redact_text(reason)}\n")
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


def acquire_web(
    input_value: str,
    project_root: Path,
    command_log: Path,
    *,
    analysis_target: str,
) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str]:
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
        is_task_primary = analysis_target == "web_article"
        entry = bundle.artifact_entry(
            bundle_root=bundle_root,
            path=output,
            artifact_type="page_markdown",
            source_class="primary" if is_task_primary else "secondary",
            content_scope="article_body",
            description="Web page Markdown acquired through Jina Reader route.",
            created_by="curl_jina_reader",
        )
        return (
            "material_acquired" if is_task_primary else "secondary_only",
            [entry],
            {"reader_url": redact_value_for_record(reader_url)},
            [],
            "ingest_bundle" if is_task_primary else "Use as secondary context or provide task-primary material.",
        )
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
        if is_probable_xhs_note_url(input_value) and not xhs_note_parts(input_value)[1]:
            return (
                "blocked",
                [],
                metadata,
                [{"stage": "xiaohongshu_opencli_route", "reason": "Xiaohongshu note URL is missing xsec_token."}],
                "Search/feed first, then retry with the complete note URL returned by Xiaohongshu.",
                active_backend,
                privacy,
            )
        command = ["opencli", "xiaohongshu", "note", input_value, "-f", "json"]
        raw_output = artifacts_root / "xiaohongshu_note.raw.json"
        output = artifacts_root / "xiaohongshu_note.txt"
        privacy["browser_session_used"] = True
        try:
            completed = run_capture(command, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            append_command_log(command_log, command=command, returncode=1, note=str(exc))
            return "failed", [], metadata, [{"stage": "xiaohongshu_opencli", "reason": str(exc)}], "Install/configure OpenCLI or provide primary material.", active_backend, privacy
        append_command_log(command_log, command=command, returncode=completed.returncode, note="Agent-Reach Xiaohongshu OpenCLI route")
        if completed.returncode == 0:
            try:
                canonical_text, raw_payload = canonicalize.canonical_page_text(completed.stdout)
            except canonicalize.CanonicalizationError as exc:
                reason = str(exc)
                return command_blocked_status(completed), [], metadata, [{"stage": "xiaohongshu_opencli_parse", "reason": reason}], "Provide a complete authorized note URL or local export.", active_backend, privacy
            bundle.write_json(raw_output, sanitize_data(raw_payload))
            bundle.write_text(output, canonical_text)
            artifacts = [
                bundle.artifact_entry(
                    bundle_root=bundle_root,
                    path=output,
                    artifact_type="page_text",
                    source_class="primary",
                    content_scope="social_post_text",
                    description="Canonical Xiaohongshu note text acquired through OpenCLI.",
                    created_by="opencli_xiaohongshu",
                ),
                bundle.artifact_entry(
                    bundle_root=bundle_root,
                    path=raw_output,
                    artifact_type="metadata",
                    source_class="metadata_only",
                    content_scope="metadata",
                    description="Redacted raw OpenCLI JSON response.",
                    created_by="opencli_xiaohongshu",
                ),
            ]
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
        raw_output = artifacts_root / "xiaohongshu_note.raw.json"
        output = artifacts_root / "xiaohongshu_note.txt"
        privacy["browser_session_used"] = True
        try:
            completed = run_capture(command, timeout=140)
        except (OSError, subprocess.SubprocessError) as exc:
            append_command_log(command_log, command=command, returncode=1, note=str(exc))
            return "failed", [], metadata, [{"stage": "xiaohongshu_mcp", "reason": str(exc)}], "Start/login xiaohongshu-mcp or provide primary material.", active_backend, privacy
        append_command_log(command_log, command=command, returncode=completed.returncode, note="Agent-Reach Xiaohongshu MCP route")
        if completed.returncode == 0:
            try:
                canonical_text, raw_payload = canonicalize.canonical_page_text(completed.stdout)
            except canonicalize.CanonicalizationError as exc:
                reason = str(exc)
                return command_blocked_status(completed), [], metadata, [{"stage": "xiaohongshu_mcp_parse", "reason": reason}], "Check MCP login/output or provide a local note export.", active_backend, privacy
            bundle.write_json(raw_output, sanitize_data(raw_payload))
            bundle.write_text(output, canonical_text)
            artifacts = [
                bundle.artifact_entry(
                    bundle_root=bundle_root,
                    path=output,
                    artifact_type="page_text",
                    source_class="primary",
                    content_scope="social_post_text",
                    description="Canonical Xiaohongshu note text acquired through xiaohongshu-mcp.",
                    created_by="xiaohongshu-mcp",
                ),
                bundle.artifact_entry(
                    bundle_root=bundle_root,
                    path=raw_output,
                    artifact_type="metadata",
                    source_class="metadata_only",
                    content_scope="metadata",
                    description="Redacted raw xiaohongshu-mcp JSON response.",
                    created_by="xiaohongshu-mcp",
                ),
            ]
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


def _split_csv(value: Any) -> list[str]:
    if value is None:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _youtube_common_options(options: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    command_options: list[str] = []
    applied: dict[str, Any] = {
        "access_file_used": False,
        "browser_name": "",
        "js_runtime_used": False,
        "remote_components_used": False,
        "proxy_used": False,
        "impersonation_used": False,
    }

    cookies_value = str(options.get("youtube_cookies") or "").strip()
    browser_value = str(options.get("youtube_browser") or "").strip().lower()
    if cookies_value and browser_value:
        raise AgentReachAdapterError("Use only one of --youtube-cookies or --youtube-browser.")
    if cookies_value:
        cookies_path = DEFAULT_YOUTUBE_COOKIES if cookies_value.lower() == "auto" else Path(cookies_value).expanduser().resolve()
        if not cookies_path.is_file():
            raise AgentReachAdapterError(
                f"YouTube cookies file does not exist: {cookies_path}. Export an authorized Netscape cookies.txt or omit --youtube-cookies."
            )
        command_options.extend(["--cookies", str(cookies_path)])
        applied["access_file_used"] = True
    if browser_value:
        if browser_value not in {"edge", "chrome"}:
            raise AgentReachAdapterError("--youtube-browser must be edge or chrome")
        command_options.extend(["--cookies-from-browser", browser_value])
        applied["browser_name"] = browser_value

    if bool(options.get("use_js_runtime")):
        node_value = options.get("node")
        node_path = Path(node_value).expanduser().resolve() if node_value else Path(shutil.which("node") or "")
        if not node_path.is_file():
            raise AgentReachAdapterError("--use-js-runtime was requested, but a Node.js executable was not found")
        command_options.extend(["--js-runtimes", f"node:{node_path}"])
        applied["js_runtime_used"] = True

    if bool(options.get("use_remote_components")):
        command_options.extend(["--remote-components", "ejs:github"])
        applied["remote_components_used"] = True

    proxy = str(options.get("ytdlp_proxy") or "").strip()
    if proxy:
        command_options.extend(["--proxy", proxy])
        applied["proxy_used"] = True
    impersonate = str(options.get("ytdlp_impersonate") or "").strip()
    if impersonate:
        command_options.extend(["--impersonate", impersonate])
        applied["impersonation_used"] = True
    sleep_requests = options.get("ytdlp_sleep_requests")
    if sleep_requests is not None:
        command_options.extend(["--sleep-requests", str(sleep_requests)])
        applied["sleep_requests"] = float(sleep_requests)
    retry_sleep = [str(item).strip() for item in options.get("ytdlp_retry_sleep") or [] if str(item).strip()]
    for item in retry_sleep:
        command_options.extend(["--retry-sleep", item])
    if retry_sleep:
        applied["retry_sleep"] = retry_sleep

    youtube_parts: list[str] = []
    passthrough: list[str] = []
    for raw in options.get("ytdlp_extractor_args") or []:
        text = str(raw).strip()
        if not text:
            continue
        if text.lower().startswith("youtube:"):
            youtube_parts.append(text.split(":", 1)[1])
        else:
            passthrough.append(text)
    player_clients = _split_csv(options.get("ytdlp_player_clients"))
    if player_clients:
        youtube_parts.append("player_client=" + ",".join(player_clients))
        applied["player_clients"] = player_clients
    visitor_data = str(options.get("youtube_visitor_data") or "").strip()
    if visitor_data:
        youtube_parts.append(f"visitor_data={visitor_data}")
        applied["browser_challenge_context_used"] = True
    po_tokens = [str(item).strip() for item in options.get("youtube_po_token") or [] if str(item).strip()]
    for token in po_tokens:
        youtube_parts.append(f"po_token={token}")
    if po_tokens:
        applied["proof_context_count"] = len(po_tokens)
    if youtube_parts:
        command_options.extend(["--extractor-args", "youtube:" + ";".join(youtube_parts)])
    for extractor_arg in passthrough:
        command_options.extend(["--extractor-args", extractor_arg])
    if passthrough:
        applied["passthrough_extractor_args"] = len(passthrough)
    return command_options, applied


def _safe_youtube_metadata(payload: dict[str, Any], input_value: str) -> dict[str, Any]:
    safe_keys = (
        "id",
        "title",
        "description",
        "duration",
        "timestamp",
        "upload_date",
        "uploader",
        "uploader_id",
        "channel",
        "channel_id",
        "availability",
        "live_status",
        "language",
    )
    result = {key: payload.get(key) for key in safe_keys if payload.get(key) is not None}
    result["webpage_url"] = redact_value_for_record(str(payload.get("webpage_url") or input_value))
    subtitles = payload.get("subtitles") if isinstance(payload.get("subtitles"), dict) else {}
    auto_captions = payload.get("automatic_captions") if isinstance(payload.get("automatic_captions"), dict) else {}
    result["subtitle_languages"] = sorted(str(key) for key in subtitles)
    result["automatic_caption_languages"] = sorted(str(key) for key in auto_captions)
    return sanitize_data(result)


def _youtube_privacy(applied: dict[str, Any]) -> dict[str, bool]:
    browser_used = bool(applied.get("browser_name"))
    return {
        "cookies_used": bool(applied.get("access_file_used")) or browser_used,
        "browser_session_used": browser_used,
    }


def _youtube_transcribe(
    *,
    input_value: str,
    artifacts_root: Path,
    bundle_root: Path,
    command_log: Path,
    timeout: int,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    output = artifacts_root / "youtube_transcript.txt"
    command = ["agent-reach", "transcribe", input_value, "-o", str(output)]
    try:
        completed = run_capture(command, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        append_command_log(command_log, command=command, returncode=1, note=str(exc))
        return [], {"stage": "youtube_transcribe", "reason": str(exc)}
    append_command_log(command_log, command=command, returncode=completed.returncode, note="Agent-Reach YouTube transcription fallback")
    if completed.returncode == 0 and output.is_file() and output.stat().st_size > 0:
        return [
            bundle.artifact_entry(
                bundle_root=bundle_root,
                path=output,
                artifact_type="transcript",
                source_class="primary",
                content_scope="video_transcript",
                description="Transcript produced by the Agent-Reach transcription route.",
                created_by="agent-reach_transcribe",
            )
        ], None
    reason = completed.stderr[-1000:] or completed.stdout[-1000:] or "transcription route produced no transcript"
    return [], {"stage": "youtube_transcribe", "reason": reason}


def acquire_youtube(
    input_value: str,
    project_root: Path,
    command_log: Path,
    *,
    options: dict[str, Any],
    operation: str,
) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str, dict[str, bool]]:
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    metadata_path = artifacts_root / "metadata.json"
    output_template = str(artifacts_root / "youtube.%(ext)s")
    ytdlp_value = options.get("ytdlp")
    ytdlp = str(Path(ytdlp_value).expanduser().resolve()) if ytdlp_value else "yt-dlp"
    if ytdlp_value and not Path(ytdlp).is_file():
        raise AgentReachAdapterError(f"yt-dlp executable does not exist: {ytdlp}")
    common_options, applied = _youtube_common_options(options)
    timeout = int(options.get("platform_timeout_seconds") or 90)
    if timeout <= 0:
        raise AgentReachAdapterError("--platform-timeout-seconds must be greater than zero")
    mode = str(options.get("platform_mode") or "auto")
    if mode not in {"auto", "probe", "subtitles", "audio"}:
        raise AgentReachAdapterError(f"unsupported YouTube platform mode: {mode}")
    if operation == "read":
        if mode not in {"auto", "probe"}:
            raise AgentReachAdapterError("YouTube operation 'read' only supports --platform-mode auto/probe")
        mode = "probe"
    subtitle_languages = str(options.get("subtitle_languages") or "all,-live_chat")
    metadata_command = [ytdlp, *common_options, "--skip-download", "--dump-single-json", input_value]
    subtitle_command = [
        ytdlp,
        *common_options,
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        subtitle_languages,
        "--convert-subs",
        "vtt",
        "-o",
        output_template,
        input_value,
    ]
    artifacts: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {"platform_mode": mode, "applied_options": applied}
    failures: list[dict[str, Any]] = []
    try:
        meta = run_capture(metadata_command, timeout=timeout)
        append_command_log(command_log, command=metadata_command, returncode=meta.returncode, note="yt-dlp metadata")
        if meta.returncode == 0 and meta.stdout.strip():
            try:
                parsed = json.loads(meta.stdout)
                safe_metadata = _safe_youtube_metadata(parsed if isinstance(parsed, dict) else {}, input_value)
                bundle.write_json(metadata_path, safe_metadata)
                artifacts.append(
                    bundle.artifact_entry(
                        bundle_root=bundle_root,
                        path=metadata_path,
                        artifact_type="metadata",
                        source_class="metadata_only",
                        content_scope="metadata",
                        description="yt-dlp metadata.",
                        created_by="yt-dlp",
                    )
                )
                metadata["title"] = safe_metadata.get("title")
            except json.JSONDecodeError:
                failures.append({"stage": "youtube_metadata_parse", "reason": "yt-dlp metadata was not valid JSON"})
        else:
            failures.append({"stage": "youtube_metadata", "reason": meta.stderr[-1000:] or meta.stdout[-1000:]})
        if mode in {"auto", "subtitles"}:
            subs = run_capture(subtitle_command, timeout=max(timeout, 120))
            append_command_log(command_log, command=subtitle_command, returncode=subs.returncode, note="yt-dlp subtitles")
            if subs.returncode != 0:
                failures.append({"stage": "youtube_subtitles", "reason": subs.stderr[-1000:] or subs.stdout[-1000:]})
    except (OSError, subprocess.SubprocessError) as exc:
        failures.append({"stage": "youtube", "reason": str(exc)})
        return "failed", artifacts, metadata, failures, youtube_next_action(failures), _youtube_privacy(applied)

    subtitle_files = sorted(artifacts_root.glob("youtube*.vtt")) + sorted(artifacts_root.glob("youtube*.srt"))
    for subtitle in subtitle_files:
        artifacts.append(
            bundle.artifact_entry(
                bundle_root=bundle_root,
                path=subtitle,
                artifact_type="subtitle",
                source_class="primary",
                content_scope="video_transcript",
                description="Subtitle acquired by yt-dlp.",
                created_by="yt-dlp",
            )
        )
    if any(item.get("source_class") == "primary" for item in artifacts):
        return "material_acquired", artifacts, metadata, failures, "ingest_bundle", _youtube_privacy(applied)
    if mode in {"auto", "audio"}:
        transcript_artifacts, transcript_failure = _youtube_transcribe(
            input_value=input_value,
            artifacts_root=artifacts_root,
            bundle_root=bundle_root,
            command_log=command_log,
            timeout=max(timeout, 180),
        )
        artifacts.extend(transcript_artifacts)
        if transcript_failure:
            failures.append(transcript_failure)
        if transcript_artifacts:
            return "material_acquired", artifacts, metadata, failures, "ingest_bundle", _youtube_privacy(applied)
    if artifacts:
        return "metadata_only", artifacts, metadata, failures, youtube_next_action(failures, metadata_only=True), _youtube_privacy(applied)
    combined_reason = "\n".join(str(item.get("reason") or "") for item in failures)
    status = blocked_status_from_reason(combined_reason) if failures else "failed"
    return status, artifacts, metadata, failures, youtube_next_action(failures), _youtube_privacy(applied)


def acquire_bilibili(
    input_value: str,
    project_root: Path,
    command_log: Path,
    *,
    doctor: dict[str, Any],
    operation: str,
) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str]:
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    active_backend = active_backend_from_doctor(doctor, "bilibili")
    item = doctor_item_for_platform(doctor, "bilibili")
    metadata: dict[str, Any] = {"operation": operation}
    artifacts: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    if not active_backend_is_ready(doctor, "bilibili"):
        return (
            "blocked",
            [],
            metadata,
            [{"stage": "bilibili_active_backend", "reason": item.get("message") or "No ready Bilibili backend."}],
            "Configure a Bilibili backend reported ready by Agent-Reach, then retry.",
        )

    if operation == "extract_transcript" and active_backend == "OpenCLI":
        command = ["opencli", "bilibili", "subtitle", input_value, "-f", "json"]
        raw_path = artifacts_root / "bilibili_subtitle.raw.json"
        transcript_path = artifacts_root / "bilibili_subtitle.json"
        try:
            completed = run_capture(command, timeout=120)
        except (OSError, subprocess.SubprocessError) as exc:
            append_command_log(command_log, command=command, returncode=1, note=str(exc))
            return "failed", [], metadata, [{"stage": "bilibili_opencli", "reason": str(exc)}], "Restore OpenCLI browser connectivity or provide subtitles."
        append_command_log(command_log, command=command, returncode=completed.returncode, note="Agent-Reach Bilibili OpenCLI subtitle route")
        if completed.returncode != 0:
            reason = completed.stderr[-1000:] or completed.stdout[-1000:] or "OpenCLI subtitle command failed"
            return command_blocked_status(completed), [], metadata, [{"stage": "bilibili_opencli", "reason": reason}], "Log in through Chrome/OpenCLI or provide subtitles."
        try:
            canonical, raw_payload = canonicalize.canonical_subtitle_json(completed.stdout)
        except canonicalize.CanonicalizationError as exc:
            return "failed", [], metadata, [{"stage": "bilibili_opencli_parse", "reason": str(exc)}], "Provide a subtitle export or retry the OpenCLI subtitle route."
        bundle.write_json(raw_path, sanitize_data(raw_payload))
        bundle.write_json(transcript_path, canonical)
        artifacts.extend(
            [
                bundle.artifact_entry(
                    bundle_root=bundle_root,
                    path=transcript_path,
                    artifact_type="transcript",
                    source_class="primary",
                    content_scope="video_transcript",
                    description="Canonical Bilibili subtitle transcript acquired through OpenCLI.",
                    created_by="opencli_bilibili",
                ),
                bundle.artifact_entry(
                    bundle_root=bundle_root,
                    path=raw_path,
                    artifact_type="metadata",
                    source_class="metadata_only",
                    content_scope="metadata",
                    description="Redacted raw OpenCLI Bilibili subtitle JSON.",
                    created_by="opencli_bilibili",
                ),
            ]
        )
        return "material_acquired", artifacts, metadata, [], "ingest_bundle"

    backend_lower = active_backend.lower()
    if "bili-cli" not in backend_lower and "bili cli" not in backend_lower:
        return (
            "blocked",
            [],
            {**metadata, "capability_mismatch": True},
            [
                {
                    "stage": "bilibili_capability",
                    "reason": f"Active backend {active_backend!r} does not support {operation!r} for this URL.",
                }
            ],
            "Install/activate OpenCLI for subtitles or bili-cli for audio/detail; the search API cannot extract video content.",
        )

    metadata_path = artifacts_root / "metadata.json"
    command = ["bili", "video", input_value]
    try:
        completed = run_capture(command, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        append_command_log(command_log, command=command, returncode=1, note=str(exc))
        return "failed", [], metadata, [{"stage": "bilibili", "reason": str(exc)}], "Provide Bilibili subtitle/transcript or local media."
    append_command_log(command_log, command=command, returncode=completed.returncode, note="bili-cli metadata")
    if completed.returncode == 0 and completed.stdout.strip():
        try:
            metadata_payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            failures.append({"stage": "bilibili_metadata_parse", "reason": "bili-cli metadata was not valid JSON"})
        else:
            bundle.write_json(metadata_path, sanitize_data(metadata_payload))
            artifacts.append(bundle.artifact_entry(
                bundle_root=bundle_root,
                path=metadata_path,
                artifact_type="metadata",
                source_class="metadata_only",
                content_scope="metadata",
                description="Redacted Bilibili metadata/detail output.",
                created_by="bili-cli",
            ))
    else:
        failures.append({"stage": "bilibili_metadata", "reason": completed.stderr[-1000:] or "empty metadata output"})

    if operation != "extract_transcript":
        if artifacts:
            return "metadata_only", artifacts, metadata, failures, "Provide subtitles/transcript when content analysis is required."
        return "failed", [], metadata, failures, "Provide a supported Bilibili URL or local material."

    audio_command = ["bili", "audio", input_value]
    try:
        audio_result = run_capture(audio_command, cwd=artifacts_root, timeout=180)
    except (OSError, subprocess.SubprocessError) as exc:
        append_command_log(command_log, command=audio_command, returncode=1, note=str(exc))
        failures.append({"stage": "bilibili_audio", "reason": str(exc)})
    else:
        append_command_log(command_log, command=audio_command, returncode=audio_result.returncode, note="Agent-Reach bili-cli audio route")
        if audio_result.returncode != 0:
            failures.append({"stage": "bilibili_audio", "reason": audio_result.stderr[-1000:] or audio_result.stdout[-1000:] or "audio command failed"})

    audio_files = [
        path
        for suffix in ("*.mp3", "*.m4a", "*.wav", "*.opus")
        for path in artifacts_root.glob(suffix)
        if path.is_file()
    ]
    if audio_files:
        audio_path = sorted(audio_files)[0]
        transcript_path = artifacts_root / "bilibili_transcript.txt"
        transcribe_command = ["agent-reach", "transcribe", str(audio_path), "-o", str(transcript_path)]
        try:
            transcribed = run_capture(transcribe_command, timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            append_command_log(command_log, command=transcribe_command, returncode=1, note=str(exc))
            failures.append({"stage": "bilibili_transcribe", "reason": str(exc)})
        else:
            append_command_log(command_log, command=transcribe_command, returncode=transcribed.returncode, note="Agent-Reach transcription route")
            if transcribed.returncode == 0 and transcript_path.is_file() and transcript_path.stat().st_size > 0:
                artifacts.append(
                    bundle.artifact_entry(
                        bundle_root=bundle_root,
                        path=transcript_path,
                        artifact_type="transcript",
                        source_class="primary",
                        content_scope="video_transcript",
                        description="Bilibili audio-derived transcript.",
                        created_by="agent-reach_transcribe",
                    )
                )
                return "material_acquired", artifacts, metadata, failures, "ingest_bundle"
            failures.append({"stage": "bilibili_transcribe", "reason": transcribed.stderr[-1000:] or "transcription produced no file"})

    if artifacts:
        return "metadata_only", artifacts, metadata, failures, "Provide subtitles or configure the authorized audio transcription route."
    return "failed", [], metadata, failures, "Provide Bilibili subtitles/transcript or authorized local media."


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


def acquire_search(
    input_value: str,
    project_root: Path,
    command_log: Path,
    *,
    doctor: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], str]:
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"
    output = artifacts_root / "search_results.md"
    if not active_backend_is_ready(doctor, "search"):
        item = doctor_item_for_platform(doctor, "search")
        return (
            "blocked",
            [],
            {},
            [{"stage": "search_active_backend", "reason": item.get("message") or "Exa search backend is not ready."}],
            "Configure Exa in the mcporter home scope, then retry.",
        )
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


def _acquire_with_agent_reach_into(
    *,
    input_value: str,
    project_root: Path,
    run_id: str,
    attempt_id: str,
    analysis_target: str,
    operation: str,
    source_fingerprint: str,
    platform_override: str = "",
    youtube_options: dict[str, Any] | None = None,
) -> Path:
    project_root = project_root.resolve()
    bundle_root = project_root / "00_acquisition"
    (bundle_root / "artifacts").mkdir(parents=True, exist_ok=True)
    (bundle_root / "logs").mkdir(parents=True, exist_ok=True)
    command_log = bundle_root / "logs" / "commands.jsonl"
    platform = platform_override or detect_platform(input_value)

    if platform == "local_file":
        raise AgentReachAdapterError("local files must use build_local_bundle")
    if platform not in SUPPORTED_PLATFORMS:
        return make_failed_manifest(
            project_root=project_root,
            input_value=input_value,
            platform=platform,
            status="unsupported",
            reason=f"platform is not supported by the first adapter version: {platform}",
            run_id=run_id,
            attempt_id=attempt_id,
            analysis_target=analysis_target,
            operation=operation,
            source_fingerprint=source_fingerprint,
        )
    if shutil.which("agent-reach") is None:
        return make_failed_manifest(
            project_root=project_root,
            input_value=input_value,
            platform=platform,
            status="failed",
            reason="agent-reach command not found",
            run_id=run_id,
            attempt_id=attempt_id,
            analysis_target=analysis_target,
            operation=operation,
            source_fingerprint=source_fingerprint,
        )

    doctor = write_doctor(project_root, command_log)
    active_backend = active_backend_from_doctor(doctor, platform)
    route_plan = route_plan_for(
        platform,
        doctor,
        input_value,
        analysis_target=analysis_target,
        operation=operation,
    )
    write_route_plan(project_root, route_plan)
    privacy_flags: dict[str, bool] = {
        "cookies_used": False,
        "browser_session_used": False,
    }

    if not route_plan.get("capability_ready"):
        status, artifacts, metadata, failures, next_action = (
            "blocked",
            [],
            {"route_plan": route_plan, "capability_mismatch": True},
            [
                {
                    "stage": "active_backend_capability",
                    "reason": route_plan.get("blocked_until_ready_reason")
                    or f"No ready backend supports operation {operation!r} for {platform!r}.",
                }
            ],
            "Configure a ready backend that supports the requested operation, or provide task-primary local material.",
        )
    elif platform == "web":
        status, artifacts, metadata, failures, next_action = acquire_web(input_value, project_root, command_log, analysis_target=analysis_target)
    elif platform == "youtube":
        status, artifacts, metadata, failures, next_action, privacy_flags = acquire_youtube(
            input_value,
            project_root,
            command_log,
            options=youtube_options or {},
            operation=operation,
        )
    elif platform == "bilibili":
        status, artifacts, metadata, failures, next_action = acquire_bilibili(input_value, project_root, command_log, doctor=doctor, operation=operation)
    elif platform == "github":
        status, artifacts, metadata, failures, next_action = acquire_github(input_value, project_root, command_log)
    elif platform == "search":
        status, artifacts, metadata, failures, next_action = acquire_search(input_value, project_root, command_log, doctor=doctor)
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
    if isinstance(metadata, dict):
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
        run_id=run_id,
        attempt_id=attempt_id,
        analysis_target=analysis_target,
        operation=operation,
        source_fingerprint=source_fingerprint,
    )
    notes = [
        "# Acquisition Notes",
        "",
        f"- Input: `{redact_value_for_record(input_value)}`",
        f"- Platform: `{platform}`",
        f"- Active backend: `{active_backend or 'unknown'}`",
        f"- Status: `{status}`",
        f"- Next action: {next_action}",
        f"- Route plan: `00_acquisition/logs/route_plan.json`",
        "",
    ]
    bundle.write_text(bundle_root / "logs" / "acquisition_notes.md", "\n".join(notes))
    return bundle.write_manifest(project_root, manifest)


def acquire_with_agent_reach(
    *,
    input_value: str,
    project_root: Path,
    analysis_target: str = "auto",
    operation: str = "auto",
    resume: bool = False,
    platform_override: str = "",
    youtube_options: dict[str, Any] | None = None,
) -> Path:
    project_root = project_root.resolve()
    platform = platform_override or detect_platform(input_value)
    if platform_override and platform_override not in SUPPORTED_PLATFORMS:
        raise AgentReachAdapterError(f"unsupported platform override: {platform_override}")
    if platform == "local_file":
        return bundle.build_local_bundle(
            input_path=Path(input_value),
            project_root=project_root,
            analysis_target=analysis_target,
            operation=operation,
            resume=resume,
        )

    chosen_target = source_gate.infer_analysis_target(platform, analysis_target)
    chosen_operation = source_gate.infer_operation(chosen_target, operation)
    source_id = source_id_for(input_value, platform)
    try:
        identity = run_context.ensure_run_identity(
            project_root=project_root,
            platform=platform,
            source_id=source_id,
            source_value=input_value,
            analysis_target=chosen_target,
            operation=chosen_operation,
            resume=resume,
        )
        attempt = run_context.prepare_attempt(project_root=project_root, identity=identity)
    except run_context.RunContextError as exc:
        raise AgentReachAdapterError(str(exc)) from exc

    try:
        staged_manifest = _acquire_with_agent_reach_into(
            input_value=input_value,
            project_root=attempt.work_project_root,
            run_id=attempt.run_id,
            attempt_id=attempt.attempt_id,
            analysis_target=attempt.analysis_target,
            operation=attempt.operation,
            source_fingerprint=str(identity["source_fingerprint"]),
            platform_override=platform,
            youtube_options=youtube_options,
        )
        validation = bundle.validate_manifest(staged_manifest)
        if not validation["valid"]:
            raise AgentReachAdapterError("acquisition bundle failed validation: " + "; ".join(validation["errors"]))
        return run_context.promote_attempt(attempt)
    except Exception:
        run_context.abandon_attempt(attempt)
        raise


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
    command = ["mcporter", "config", "add", "exa", "https://mcp.exa.ai/mcp", "--scope", "home"]
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


def agent_reach_route_plan(
    *,
    input_value: str,
    output_json: Path | None = None,
    analysis_target: str = "auto",
    operation: str = "auto",
) -> int:
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
    plan = route_plan_for(
        platform,
        doctor if isinstance(doctor, dict) else {},
        input_value,
        analysis_target=analysis_target,
        operation=operation,
    )
    payload = {"input": redact_value_for_record(input_value), "platform": platform, "route_plan": plan}
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0
