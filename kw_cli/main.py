#!/usr/bin/env python
"""Product entrypoint for the Knowledge Workflow repository."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from . import agent_reach_adapter, bundle, ingest, source_gate
from .redaction import redact_text


REPO_ROOT = Path(__file__).resolve().parents[1]
CONSOLE = REPO_ROOT / "skills" / "knowledge-workflow-console"
VIDEO = REPO_ROOT / "skills" / "knowledge-video-decomposer"
DOCUMENT = REPO_ROOT / "skills" / "knowledge-document-composer"
OUTPUT_BASE = REPO_ROOT / "outputs" / "knowledge-workflow"
DEFAULT_YOUTUBE_COOKIES = REPO_ROOT / "work" / "youtube-cookies" / "youtube.cookies.txt"

TRANSCRIPT_EXTENSIONS = {".txt", ".md", ".srt", ".vtt", ".jsonl", ".json"}
MEDIA_EXTENSIONS = {".mp3", ".mp4", ".m4a", ".webm", ".wav", ".mov", ".opus"}
TEMPLATE_NAMES = {"study_notes", "research_brief", "creator_script", "prompt_pack", "action_plan"}

RUN_OPTION_DEFAULTS = {
    "target": "auto",
    "operation": "auto",
    "resume": False,
    "platform_mode": "auto",
    "youtube_cookies": None,
    "youtube_browser": None,
    "browser_host": None,
    "ytdlp": None,
    "node": None,
    "platform_timeout_seconds": 90,
    "subtitle_languages": "all,-live_chat",
    "use_js_runtime": False,
    "use_remote_components": False,
    "ytdlp_extractor_args": (),
    "ytdlp_player_clients": "default,mweb,web,android_vr",
    "youtube_visitor_data": None,
    "youtube_po_token": (),
    "ytdlp_proxy": None,
    "ytdlp_impersonate": None,
    "ytdlp_sleep_requests": None,
    "ytdlp_retry_sleep": (),
    "asr_jsonl": None,
    "asr_python": None,
    "asr_device": "cpu",
    "asr_compute_type": "int8",
    "asr_timeout_seconds": 0.0,
    "asr_vad": True,
    "browser_source_url": None,
    "browser_platform": None,
    "content_scope": None,
    "partial_export": False,
}


class KwError(Exception):
    """User-facing CLI failure."""


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except OSError:
                pass


def run_command(command: list[str], *, cwd: Path, show_output: bool = True) -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if show_output:
        completed = subprocess.run(command, cwd=str(cwd), env=env)
    else:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        if completed.returncode != 0:
            if completed.stdout:
                print(completed.stdout, file=sys.stderr)
            if completed.stderr:
                print(completed.stderr, file=sys.stderr)
    return completed.returncode


def run_required(command: list[str], *, cwd: Path) -> None:
    code = run_command(command, cwd=cwd, show_output=False)
    if code != 0:
        raise KwError(f"command failed with exit code {code}: {' '.join(command)}")


def youtube_cookies_cli_value(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def apply_run_option_defaults(args: argparse.Namespace) -> argparse.Namespace:
    for key, value in RUN_OPTION_DEFAULTS.items():
        if not hasattr(args, key):
            setattr(args, key, value)
    return args


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def classify_input(value: str) -> str:
    if is_url(value):
        return "url"
    suffix = Path(value).suffix.lower()
    if suffix in MEDIA_EXTENSIONS:
        return "media"
    if suffix in TRANSCRIPT_EXTENSIONS:
        return "transcript"
    if Path(value).exists():
        return "transcript"
    raise KwError(f"cannot classify input as URL, media, or transcript: {value}")


def normalize_input(value: str) -> str:
    if is_url(value):
        return value
    return str(Path(value).resolve())


def has_usable_transcript_text(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper() == "WEBVTT":
            continue
        if stripped.isdigit():
            continue
        if "-->" in stripped:
            continue
        return True
    return False


def validate_local_transcript_input(input_value: str) -> None:
    path = Path(input_value)
    if not path.is_file():
        raise KwError(f"input transcript file does not exist: {path}")
    if not has_usable_transcript_text(path):
        raise KwError(
            "input transcript contains no usable text. Provide a transcript, "
            "subtitle file, local media for ASR, or an authorized source that "
            "can produce primary material."
        )


def slugify(value: str) -> str:
    if is_url(value):
        parsed = urlparse(value)
        basis = f"{parsed.netloc}-{Path(parsed.path).name or 'video'}"
    else:
        basis = Path(value).stem or "workflow"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", basis).strip("-").lower()
    return slug[:48] or "workflow"


def default_project_root(value: str) -> Path:
    return OUTPUT_BASE / f"{slugify(value)}-{timestamp_id()}"


def ensure_project_root(args: argparse.Namespace) -> Path:
    basis = (
        getattr(args, "input", None)
        or getattr(args, "source_url", None)
        or str(getattr(args, "input_file", "workflow"))
    )
    root = args.project_root.resolve() if args.project_root else default_project_root(str(basis))
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    return root


def contained_child_path(parent: Path, child: Path, label: str) -> Path:
    resolved_parent = parent.resolve()
    resolved_child = child.resolve()
    if resolved_child == resolved_parent:
        raise KwError(f"refusing to use {label} as the output root itself: {resolved_child}")
    try:
        resolved_child.relative_to(resolved_parent)
    except ValueError as exc:
        raise KwError(f"refusing to use {label} outside output root: {resolved_child}") from exc
    return resolved_child


def run_preflight(input_value: str, mode: str, project_root: Path, pretty: bool) -> None:
    command = [
        sys.executable,
        str(CONSOLE / "scripts" / "workflow_preflight.py"),
        "--input",
        redact_text(input_value),
        "--mode",
        mode,
        "--output-json",
        str(project_root / "logs" / "preflight.json"),
        "--output-md",
        str(project_root / "logs" / "preflight.md"),
    ]
    if pretty:
        command.append("--pretty")
    run_required(command, cwd=CONSOLE / "scripts")


def write_status(project_root: Path, pretty: bool) -> None:
    command = [
        sys.executable,
        str(CONSOLE / "scripts" / "workflow_status_summary.py"),
        "--project-root",
        str(project_root),
        "--output-json",
        str(project_root / "logs" / "status_summary.json"),
        "--output-md",
        str(project_root / "logs" / "status_summary.md"),
    ]
    if pretty:
        command.append("--pretty")
    run_required(command, cwd=CONSOLE / "scripts")


def write_result(project_root: Path, pretty: bool) -> None:
    command = [
        sys.executable,
        str(CONSOLE / "scripts" / "result_index_writer.py"),
        "--project-root",
        str(project_root),
    ]
    if pretty:
        command.append("--pretty")
    run_required(command, cwd=CONSOLE / "scripts")


def current_source_status(project_root: Path) -> dict:
    return read_json(project_root / "10_video" / "00_source" / "source_status.json")


def current_acquisition_manifest(project_root: Path) -> dict:
    return read_json(project_root / "00_acquisition" / "manifest.json")


def write_run_state(
    *,
    project_root: Path,
    mode: str,
    input_kind: str,
    input_value: str,
    status: str,
    workflow_outcome: str,
    failure_reason: str = "",
    degraded_reason: str = "",
    user_action_required: str = "",
) -> None:
    source_status = current_source_status(project_root)
    manifest = current_acquisition_manifest(project_root)
    provenance = ingest.current_provenance(project_root)
    payload = {
        "runner": "knowledge-workflow-cli",
        "schema_version": 3,
        "mode": "platform_url" if input_kind == "url" else "local_file",
        "requested_mode": mode,
        "status": status,
        "workflow_outcome": workflow_outcome,
        "project_root": str(project_root),
        "input": redact_text(input_value),
        "input_kind": input_kind,
        "acquisition_status": manifest.get("status") or "unknown",
        "source_status": source_status.get("source_status") or "unknown",
        "run_id": manifest.get("run_id") or source_status.get("run_id") or "",
        "attempt_id": manifest.get("attempt_id") or source_status.get("attempt_id") or "",
        "bundle_id": manifest.get("bundle_id") or source_status.get("bundle_id") or "",
        "source_fingerprint": manifest.get("source_fingerprint") or source_status.get("source_fingerprint") or "",
        "analysis_target": manifest.get("analysis_target") or source_status.get("analysis_target") or "",
        "gate_provenance_current": bool(provenance["gate_current"]),
        "analysis_provenance_current": bool(provenance["analysis_current"]),
        "final_report_provenance_current": bool(provenance["final_report_current"]),
        "current_stage": "result_index",
        "failure_reason": failure_reason,
        "degraded_reason": degraded_reason,
        "user_action_required": user_action_required or source_status.get("next_step") or manifest.get("next_action") or "",
    }
    write_text(project_root / "logs" / "run_state.json", json.dumps(payload, ensure_ascii=False, indent=2))


def youtube_options_from_args(args: argparse.Namespace) -> dict[str, object]:
    args = apply_run_option_defaults(args)
    return {
        "platform_mode": getattr(args, "platform_mode", "auto"),
        "youtube_cookies": youtube_cookies_cli_value(getattr(args, "youtube_cookies", None)),
        "youtube_browser": getattr(args, "youtube_browser", None),
        "browser_host": getattr(args, "browser_host", None),
        "opencli_window": getattr(args, "opencli_window", "foreground"),
        "opencli_site_session": getattr(args, "opencli_site_session", "persistent"),
        "opencli_keep_tab": bool(getattr(args, "opencli_keep_tab", True)),
        "ytdlp": getattr(args, "ytdlp", None),
        "node": getattr(args, "node", None),
        "platform_timeout_seconds": getattr(args, "platform_timeout_seconds", 90),
        "subtitle_languages": getattr(args, "subtitle_languages", "all,-live_chat"),
        "use_js_runtime": bool(getattr(args, "use_js_runtime", False)),
        "use_remote_components": bool(getattr(args, "use_remote_components", False)),
        "ytdlp_extractor_args": list(getattr(args, "ytdlp_extractor_args", ()) or ()),
        "ytdlp_player_clients": getattr(args, "ytdlp_player_clients", "default,mweb,web,android_vr"),
        "youtube_visitor_data": getattr(args, "youtube_visitor_data", None),
        "youtube_po_token": list(getattr(args, "youtube_po_token", ()) or ()),
        "ytdlp_proxy": getattr(args, "ytdlp_proxy", None),
        "ytdlp_impersonate": getattr(args, "ytdlp_impersonate", None),
        "ytdlp_sleep_requests": getattr(args, "ytdlp_sleep_requests", None),
        "ytdlp_retry_sleep": list(getattr(args, "ytdlp_retry_sleep", ()) or ()),
    }


def print_flow_summary(project_root: Path) -> None:
    manifest = current_acquisition_manifest(project_root)
    source_status = current_source_status(project_root)
    provenance = ingest.current_provenance(project_root)
    source_state = source_status.get("source_status") or "unknown"
    full_allowed = bool(provenance["gate_current"] and source_status.get("can_enter_full_decomposition")) and source_state in {"source_confirmed", "source_partial"}
    print(f"Acquisition status: {manifest.get('status', 'unknown')}")
    print(f"Source status: {source_state}")
    print(f"Full report allowed: {str(full_allowed).lower()}")
    print(f"Result index: {project_root / 'result_index.md'}")


def run_new_flow(args: argparse.Namespace) -> int:
    args = apply_run_option_defaults(args)
    project_root = ensure_project_root(args)
    input_kind = classify_input(args.input)
    input_value = normalize_input(args.input)
    exit_code = 0
    failure_reason = ""
    degraded_reason = ""
    user_action_required = ""
    workflow_outcome = "source_gated_flow"
    try:
        if input_kind == "transcript":
            validate_local_transcript_input(input_value)
        run_preflight(args.browser_source_url or input_value, args.mode, project_root, args.pretty)
        if args.mode == "quick":
            workflow_outcome = "preflight_only"
            write_run_state(
                project_root=project_root,
                mode=args.mode,
                input_kind=input_kind,
                input_value=input_value,
                status="completed",
                workflow_outcome=workflow_outcome,
            )
            write_result(project_root, args.pretty)
            print_flow_summary(project_root)
            return 0

        if args.browser_source_url:
            if not args.browser_platform:
                raise KwError("--browser-platform is required with --browser-source-url")
            manifest_path = bundle.build_browser_export_bundle(
                input_path=Path(input_value),
                source_url=args.browser_source_url,
                platform=args.browser_platform,
                project_root=project_root,
                language=args.language,
                source_class="partial_primary" if args.partial_export else "primary",
                analysis_target=args.target,
                operation=args.operation,
                content_scope=args.content_scope or "",
                browser_host=args.browser_host or "",
                resume=args.resume,
            )
        elif input_kind == "url":
            manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                input_value=input_value,
                project_root=project_root,
                analysis_target=args.target,
                operation=args.operation,
                resume=args.resume,
                youtube_options=youtube_options_from_args(args),
            )
        else:
            manifest_path = bundle.build_local_bundle(
                input_path=Path(input_value),
                project_root=project_root,
                analysis_target=args.target,
                operation=args.operation,
                resume=args.resume,
            )

        ingest_result = ingest.ingest_bundle(manifest_path=manifest_path, project_root=project_root)
        source_status = current_source_status(project_root)
        source_state = source_status.get("source_status")
        if input_kind == "media" and source_state == "degraded_report_only":
            manifest = current_acquisition_manifest(project_root)
            asr_result = ingest.run_asr_for_media_bundle(
                manifest_path=manifest_path,
                manifest=manifest,
                project_root=project_root,
                asr_model=args.asr_model,
                language=args.language,
                asr_python=args.asr_python,
                asr_jsonl=args.asr_jsonl,
                asr_device=args.asr_device,
                asr_compute_type=args.asr_compute_type,
                asr_timeout_seconds=args.asr_timeout_seconds,
                asr_vad=args.asr_vad,
                pretty=args.pretty,
            )
            source_status = current_source_status(project_root)
            source_state = source_status.get("source_status")
            if asr_result.get("status") == "failed":
                degraded_reason = source_status.get("status_reason") or str(asr_result.get("error") or "")
                user_action_required = source_status.get("next_step") or ""
        if source_state in {"source_confirmed", "source_partial"} and args.mode in {"standard", "audit"}:
            audit_result = ingest.run_audit_pipeline(
                project_root=project_root,
                document_goal=args.document_goal,
                final_language=args.final_language,
                audience=args.audience,
                pretty=args.pretty,
            )
            if audit_result.get("status") == "completed":
                workflow_outcome = "analysis_pack_and_document_planning"
            elif audit_result.get("status") == "skipped":
                workflow_outcome = "transcript_ready"
            else:
                workflow_outcome = "audit_failed"
        else:
            workflow_outcome = "degraded_acquisition_only"
            degraded_reason = source_status.get("status_reason") or str(ingest_result.get("error") or "")
            user_action_required = source_status.get("next_step") or ""

        if (
            args.mode == "audit"
            and workflow_outcome == "analysis_pack_and_document_planning"
            and (project_root / "20_document" / "composer_intake.json").is_file()
        ):
            ingest.compose_final_report(project_root=project_root, pretty=args.pretty)
            workflow_outcome = "final_report_ready"
    except (KwError, bundle.BundleError, ingest.IngestError, agent_reach_adapter.AgentReachAdapterError) as exc:
        exit_code = 1
        failure_reason = str(exc)
        workflow_outcome = "failed"
        print(str(exc), file=sys.stderr)
    finally:
        try:
            write_run_state(
                project_root=project_root,
                mode=args.mode,
                input_kind=input_kind,
                input_value=input_value,
                status="failed" if exit_code else "completed",
                workflow_outcome=workflow_outcome,
                failure_reason=failure_reason,
                degraded_reason=degraded_reason,
                user_action_required=user_action_required,
            )
            write_status(project_root, args.pretty)
            write_result(project_root, args.pretty)
        except KwError as exc:
            exit_code = 1
            print(str(exc), file=sys.stderr)

    print(f"Project: {project_root}")
    print_flow_summary(project_root)
    return exit_code


def cmd_doctor(args: argparse.Namespace) -> int:
    command = [sys.executable, str(VIDEO / "scripts" / "doctor.py")]
    cookies_value = youtube_cookies_cli_value(args.youtube_cookies)
    if cookies_value:
        command.extend(["--youtube-cookies", cookies_value])
    if args.asr_python:
        command.extend(["--asr-python", args.asr_python])
    if args.output_json:
        command.extend(["--output-json", str(args.output_json.resolve())])
    if args.output_md:
        command.extend(["--output-md", str(args.output_md.resolve())])
    if args.overwrite:
        command.append("--overwrite")
    if args.json:
        command.append("--json")
    if args.pretty:
        command.append("--pretty")
    return run_command(command, cwd=VIDEO / "scripts")


def cmd_preflight(args: argparse.Namespace) -> int:
    project_root = ensure_project_root(args)
    input_value = normalize_input(args.input)
    try:
        run_preflight(input_value, args.mode, project_root, args.pretty)
        write_result(project_root, args.pretty)
    except KwError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Project: {project_root}")
    print(f"Result index: {project_root / 'result_index.md'}")
    return 0


def cmd_agent_reach_install(args: argparse.Namespace) -> int:
    return agent_reach_adapter.agent_reach_install(
        safe=args.safe,
        dry_run=args.dry_run,
        channels=args.channels or "",
        allow_upstream_cookie_import=bool(args.allow_upstream_cookie_import),
    )


def cmd_agent_reach_doctor(args: argparse.Namespace) -> int:
    return agent_reach_adapter.agent_reach_doctor(output_json=args.output_json)


def cmd_agent_reach_matrix(args: argparse.Namespace) -> int:
    return agent_reach_adapter.agent_reach_capability_matrix(
        output_json=args.output_json,
        output_md=args.output_md,
    )


def cmd_agent_reach_plan(args: argparse.Namespace) -> int:
    return agent_reach_adapter.agent_reach_route_plan(
        input_value=args.input,
        output_json=args.output_json,
        analysis_target=args.target,
        operation=args.operation,
        browser_host=args.browser_host or "",
    )


def cmd_agent_reach_import(args: argparse.Namespace) -> int:
    project_root = ensure_project_root(args)
    try:
        manifest_path = bundle.build_agent_reach_export_bundle(
            input_path=args.input_file,
            source_url=args.source_url,
            platform=args.platform,
            project_root=project_root,
            language=args.language,
            source_class="partial_primary" if args.partial else "primary",
            analysis_target=args.target,
            operation=args.operation,
            content_scope=args.content_scope or "",
            browser_host=args.browser_host or "",
            credentialed_session=bool(args.credentialed_session),
            resume=args.resume,
        )
    except bundle.BundleError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    manifest = read_json(manifest_path)
    print(f"Acquisition status: {manifest.get('status', 'unknown')}")
    print(f"Manifest: {manifest_path}")
    return 0


def cmd_acquire(args: argparse.Namespace) -> int:
    args = apply_run_option_defaults(args)
    project_root = ensure_project_root(args)
    input_value = normalize_input(args.input) if not args.query else args.input
    try:
        manifest_path = agent_reach_adapter.acquire_with_agent_reach(
            input_value=input_value,
            project_root=project_root,
            analysis_target=args.target,
            operation=args.operation,
            resume=args.resume,
            platform_override="search" if args.query else "",
            youtube_options=youtube_options_from_args(args),
        )
    except (bundle.BundleError, agent_reach_adapter.AgentReachAdapterError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    manifest = read_json(manifest_path)
    print(f"Acquisition status: {manifest.get('status', 'unknown')}")
    print(f"Manifest: {manifest_path}")
    return 0


def cmd_browser_import(args: argparse.Namespace) -> int:
    project_root = ensure_project_root(args)
    try:
        manifest_path = bundle.build_browser_export_bundle(
            input_path=args.input_file,
            source_url=args.source_url,
            platform=args.platform,
            project_root=project_root,
            language=args.language,
            source_class="partial_primary" if args.partial else "primary",
            analysis_target=args.target,
            operation=args.operation,
            content_scope=args.content_scope or "",
            browser_host=args.browser_host or "",
            resume=args.resume,
        )
    except bundle.BundleError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    manifest = read_json(manifest_path)
    print(f"Acquisition status: {manifest.get('status', 'unknown')}")
    print(f"Manifest: {manifest_path}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    project_root = args.project_root.resolve()
    try:
        result = ingest.ingest_bundle(manifest_path=args.bundle.resolve(), project_root=project_root)
        write_status(project_root, args.pretty)
        write_result(project_root, args.pretty)
    except (bundle.BundleError, ingest.IngestError, KwError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Source status: {result.get('source_status', 'unknown')}")
    print(f"Result index: {project_root / 'result_index.md'}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    project_root = args.project_root.resolve()
    try:
        result = ingest.run_audit_pipeline(
            project_root=project_root,
            document_goal=args.document_goal,
            final_language=args.final_language,
            audience=args.audience,
            pretty=args.pretty,
        )
        write_status(project_root, args.pretty)
        write_result(project_root, args.pretty)
    except (ingest.IngestError, KwError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Audit status: {result.get('status', 'unknown')}")
    print(f"Result index: {project_root / 'result_index.md'}")
    return 0 if result.get("status") in {"completed", "skipped"} else 1


def cmd_compose(args: argparse.Namespace) -> int:
    project_root = args.project_root.resolve()
    try:
        result = ingest.compose_final_report(project_root=project_root, pretty=args.pretty)
        write_status(project_root, args.pretty)
        write_result(project_root, args.pretty)
    except (ingest.IngestError, KwError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Compose status: {result.get('status', 'unknown')}")
    print(f"Result index: {project_root / 'result_index.md'}")
    return 0


def cmd_validate_bundle(args: argparse.Namespace) -> int:
    return bundle.cli_validate(args.bundle.resolve())


def cmd_run(args: argparse.Namespace) -> int:
    return run_new_flow(args)


def cmd_status(args: argparse.Namespace) -> int:
    project_root = args.project_root.resolve()
    try:
        write_status(project_root, args.pretty)
        write_result(project_root, args.pretty)
    except KwError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Result index: {project_root / 'result_index.md'}")
    return 0


def cmd_result(args: argparse.Namespace) -> int:
    project_root = args.project_root.resolve()
    try:
        write_result(project_root, args.pretty)
    except KwError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Result index: {project_root / 'result_index.md'}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    demo_input = REPO_ROOT / "examples" / "demo_transcript" / "input.txt"
    if not demo_input.is_file():
        print(f"missing demo input: {demo_input}", file=sys.stderr)
        return 1
    project_root = args.project_root.resolve() if args.project_root else (OUTPUT_BASE / "demo-transcript")
    if not args.resume and project_root.exists():
        resolved_project = project_root.resolve()
        resolved_output_base = OUTPUT_BASE.resolve()
        if resolved_project == resolved_output_base or not str(resolved_project).startswith(str(resolved_output_base)):
            print(f"refusing to refresh demo outside output base: {resolved_project}", file=sys.stderr)
            return 1
        shutil.rmtree(resolved_project)
    run_args = argparse.Namespace(
        input=str(demo_input),
        mode="audit",
        project_root=project_root,
        language="en",
        final_language="en",
        document_goal="Write an auditable knowledge report from the demo transcript.",
        audience="reader evaluating the Knowledge Workflow demo",
        asr_model="base",
        platform_mode="auto",
        youtube_cookies=None,
        resume=args.resume,
        pretty=args.pretty,
    )
    return cmd_run(run_args)


def cmd_export(args: argparse.Namespace) -> int:
    project_root = args.project_root.resolve()
    source = project_root / "20_document" / "final_report.md"
    if args.format != "md":
        print("only --format md is supported by the thin CLI export command for now", file=sys.stderr)
        return 1
    if not ingest.current_provenance(project_root)["final_report_current"]:
        print(f"final report is missing, stale, or does not belong to the current acquisition run: {source}", file=sys.stderr)
        return 1
    output = args.output.resolve() if args.output else (project_root / "30_final" / "final_report.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    print(f"Exported: {output}")
    return 0


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def quality_check(name: str, passed: bool, evidence: str, required_action: str = "") -> dict[str, object]:
    return {
        "check": name,
        "passed": bool(passed),
        "evidence": evidence,
        "required_action": required_action,
    }


def build_quality_review(project_root: Path) -> dict[str, object]:
    provenance = ingest.current_provenance(project_root)
    source_status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
    quality_gate = read_json(project_root / "20_document" / "quality_gate.json")
    claim_map = read_json(project_root / "20_document" / "claim_map.json")
    final_report = project_root / "20_document" / "final_report.md"
    final_text = final_report.read_text(encoding="utf-8") if provenance["final_report_current"] else ""
    gate_names = {item.get("gate"): item for item in quality_gate.get("gates", []) if isinstance(item, dict)}
    claims = claim_map.get("claims") if isinstance(claim_map.get("claims"), list) else []
    accepted_source_claims = [
        claim
        for claim in claims
        if isinstance(claim, dict)
        and claim.get("category") == "Source"
        and claim.get("status") == "accepted"
    ]
    checks = [
        quality_check(
            "current_run_provenance",
            bool(provenance["final_report_current"]),
            "Final report, quality gate, composer, analysis, and source gate receipts match." if provenance["final_report_current"] else "; ".join(provenance["reasons"]) or "Downstream receipt mismatch.",
            "Rerun ingest, audit, and compose for the current acquisition bundle.",
        ),
        quality_check(
            "source_status_known",
            bool(source_status.get("source_status")),
            str(source_status.get("source_status") or "missing"),
            "Run preflight/acquisition before quality review.",
        ),
        quality_check(
            "primary_material_labeled",
            "primary_material_available" in source_status,
            f"primary_material_available={source_status.get('primary_material_available')}",
            "Regenerate source_status.json with primary material labeling.",
        ),
        quality_check(
            "full_report_gate_approved",
            bool(provenance["final_report_current"] and quality_gate.get("approved_for_final_report")),
            f"approved_for_final_report={quality_gate.get('approved_for_final_report')}",
            "Inspect quality_gate.json and revise the final report.",
        ),
        quality_check("source_section_present", "## Source" in final_text, "Final report Source heading."),
        quality_check("inference_section_present", "## Inference" in final_text, "Final report Inference heading."),
        quality_check("extension_section_present", "## Extension" in final_text, "Final report Extension heading."),
        quality_check(
            "accepted_source_claims_present",
            bool(accepted_source_claims),
            f"accepted Source claims={len(accepted_source_claims)}",
            "Inspect claim_map.json and upstream evidence inventory.",
        ),
        quality_check(
            "claim_ids_visible",
            "doc_claim_" in final_text,
            "Final report contains registered claim ids.",
            "Keep source claim ids visible in the report.",
        ),
        quality_check(
            "language_match_gate_present",
            "Language Match" in gate_names,
            "Quality gate contains Language Match.",
            "Regenerate final report audit with language matching enabled.",
        ),
        quality_check(
            "gap_or_limits_present",
            "Evidence And Limits" in final_text or "gap" in final_text.lower(),
            "Final report names evidence limits or gaps.",
            "Add an Evidence And Limits section before final use.",
        ),
        quality_check(
            "no_cookie_literal",
            "cookie" not in final_text.lower() or "cookie values" not in final_text.lower(),
            "No obvious cookie-value disclosure marker found.",
            "Remove cookies, tokens, and private account data from outputs.",
        ),
    ]
    dimensions = [
        {
            "dimension": "Source faithfulness",
            "passed": all(item["passed"] for item in checks if item["check"] in {"accepted_source_claims_present", "claim_ids_visible"}),
        },
        {
            "dimension": "Source / Inference / Extension separation",
            "passed": all(item["passed"] for item in checks if item["check"].endswith("_section_present")),
        },
        {
            "dimension": "Claim quality",
            "passed": bool(provenance["final_report_current"] and quality_gate.get("approved_for_final_report")),
        },
        {
            "dimension": "Uncertainty",
            "passed": any(item["check"] == "gap_or_limits_present" and item["passed"] for item in checks),
        },
        {
            "dimension": "Safety and privacy",
            "passed": any(item["check"] == "no_cookie_literal" and item["passed"] for item in checks),
        },
    ]
    passed = all(bool(item["passed"]) for item in checks)
    return {
        "runner": "kw-quality-review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(project_root),
        "overall": "pass" if passed else "needs_review",
        "source_status": source_status.get("source_status", "unknown"),
        "approved_for_final_report": bool(provenance["final_report_current"] and quality_gate.get("approved_for_final_report")),
        "final_report_provenance_current": bool(provenance["final_report_current"]),
        "checks": checks,
        "dimensions": dimensions,
    }


def render_quality_review(review: dict[str, object]) -> str:
    lines = [
        "# Quality Review",
        "",
        f"- Project: `{review['project_root']}`",
        f"- Overall: `{review['overall']}`",
        f"- Source status: `{review['source_status']}`",
        f"- Approved final report: `{review['approved_for_final_report']}`",
        "",
        "## Rubric Dimensions",
        "",
        "| Dimension | Pass |",
        "| --- | --- |",
    ]
    for item in review["dimensions"]:  # type: ignore[index]
        lines.append(f"| {item['dimension']} | `{item['passed']}` |")
    lines.extend(["", "## Checks", "", "| Check | Pass | Evidence | Required Action |", "| --- | --- | --- | --- |"])
    for item in review["checks"]:  # type: ignore[index]
        lines.append(
            "| "
            + " | ".join(
                [
                    md_cell(item["check"]),
                    f"`{item['passed']}`",
                    md_cell(item["evidence"]),
                    md_cell(item["required_action"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Rubric", "", "See `quality_rubric.md` for the human review dimensions.", ""])
    return "\n".join(lines)


def cmd_quality(args: argparse.Namespace) -> int:
    project_root = args.project_root.resolve()
    review = build_quality_review(project_root)
    output = args.output or (project_root / "30_final" / "quality_review.md")
    json_output = args.output_json or output.with_suffix(".json")
    write_text(output, render_quality_review(review))
    write_text(json_output, json.dumps(review, ensure_ascii=False, indent=2))
    print(f"Quality review: {output}")
    print(f"Quality review JSON: {json_output}")
    return 0 if review["overall"] == "pass" or args.allow_needs_review else 1


def markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "Preamble"
    sections[current] = []
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def compact_excerpt(text: str, *, limit: int = 1200) -> str:
    cleaned = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "\n\n[Excerpt truncated; open the source artifact for the full text.]"


def accepted_claim_bullets(claim_map: dict) -> list[str]:
    claims = claim_map.get("claims")
    if not isinstance(claims, list):
        return []
    bullets: list[str] = []
    for claim in claims:
        if not isinstance(claim, dict) or claim.get("status") != "accepted":
            continue
        claim_id = claim.get("id") or "claim"
        category = claim.get("category") or "Unknown"
        text = str(claim.get("text") or "").strip()
        if text:
            bullets.append(f"- `{claim_id}` `{category}`: {text}")
    return bullets


def template_section(name: str, body: str) -> list[str]:
    return [f"## {name}", "", body.strip() or "No approved material available for this section.", ""]


def render_structured_template(
    template_name: str,
    sections: dict[str, str],
    claim_bullets: list[str],
    source_status: dict,
    quality_gate: dict,
) -> str:
    source = compact_excerpt(sections.get("Source", ""), limit=1400)
    inference = compact_excerpt(sections.get("Inference", ""), limit=900)
    extension = compact_excerpt(sections.get("Extension", ""), limit=900)
    examples = compact_excerpt(sections.get("Concrete Examples", ""), limit=900)
    limits = compact_excerpt(sections.get("Evidence And Limits", ""), limit=900)
    synthesis = compact_excerpt(sections.get("Final Synthesis", ""), limit=900)
    claims = "\n".join(claim_bullets) or "No accepted claims were available."
    source_line = (
        f"Source status: `{source_status.get('source_status', 'unknown')}`; "
        f"quality approved: `{bool(quality_gate.get('approved_for_final_report'))}`."
    )

    if template_name == "study_notes":
        parts = [
            template_section("Core Ideas", claims),
            template_section("Key Examples", examples),
            template_section("Important Distinctions", limits),
            template_section("Questions For Review", "- Which claims are Source, and which are Extension?\n- What gaps remain?"),
            template_section("Source / Inference / Extension Notes", f"{source_line}\n\n### Source\n{source}\n\n### Inference\n{inference}\n\n### Extension\n{extension}"),
        ]
    elif template_name == "research_brief":
        parts = [
            template_section("Research Question", "What does the approved source material establish, and how reusable is it?"),
            template_section("Main Thesis", synthesis),
            template_section("Evidence-Backed Claims", claims),
            template_section("Uncertainties And Gaps", limits),
            template_section("Relevance And Recommended Next Step", extension),
        ]
    elif template_name == "creator_script":
        parts = [
            template_section("Hook", "Start from the source-backed tension, not an invented anecdote."),
            template_section("Narrative Spine", synthesis),
            template_section("Source-Backed Talking Points", claims),
            template_section("Transitions", sections.get("Language Logic", "")),
            template_section("Ending", extension),
            template_section("Extension Notes", "Any application beyond the source must be labeled as Extension."),
        ]
    elif template_name == "prompt_pack":
        parts = [
            template_section("Source Method Summary", source),
            template_section("Reusable Prompt Patterns", "- Ask for Source / Inference / Extension separation.\n- Ask for evidence anchors before synthesis."),
            template_section("Example Prompts", "- Turn the accepted Source claims into study notes without adding external facts.\n- List gaps before proposing extensions."),
            template_section("Boundaries And Failure Modes", limits),
            template_section("Source / Extension Labels", f"### Source\n{claims}\n\n### Extension\n{extension}"),
        ]
    elif template_name == "action_plan":
        parts = [
            template_section("Objective", sections.get("Source Status", "")),
            template_section("Constraints From The Source", claims),
            template_section("Step-By-Step Plan", extension or synthesis),
            template_section("Risks", limits),
            template_section("Validation Checks", "- Confirm source status before execution.\n- Confirm quality gate before reuse.\n- Keep extensions labeled."),
        ]
    else:
        parts = [template_section("Approved Material", source or synthesis)]
    return "\n".join(line for part in parts for line in part).strip()


def render_template_output(project_root: Path, template_name: str) -> str:
    template_path = REPO_ROOT / "templates" / f"{template_name}.md"
    template_text = template_path.read_text(encoding="utf-8")
    provenance = ingest.current_provenance(project_root)
    final_report = project_root / "20_document" / "final_report.md"
    analysis_receipt = read_json(project_root / "10_video" / "analysis_receipt.json")
    pack = project_root / "10_video" / str(analysis_receipt.get("analysis_pack") or "video_analysis_pack.md")
    source_status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
    quality_gate = read_json(project_root / "20_document" / "quality_gate.json")
    claim_map = read_json(project_root / "20_document" / "claim_map.json")
    source_text = final_report.read_text(encoding="utf-8") if provenance["final_report_current"] else ""
    pack_text = pack.read_text(encoding="utf-8") if provenance["analysis_current"] and pack.is_file() else ""
    if not source_text and not pack_text and provenance["gate_current"]:
        degraded = project_root / "10_video" / "00_source" / "degraded_source_report.md"
        pack_text = degraded.read_text(encoding="utf-8") if degraded.is_file() else ""
    sections = markdown_sections(source_text or pack_text)
    draft = render_structured_template(
        template_name,
        sections,
        accepted_claim_bullets(claim_map),
        source_status,
        quality_gate,
    )
    return "\n".join(
        [
            f"# {template_name.replace('_', ' ').title()}",
            "",
            "## Template Contract",
            "",
            template_text.strip(),
            "",
            "## Source Gate",
            "",
            f"- Source status: `{source_status.get('source_status', 'unknown')}`",
            f"- Quality gate approved: `{bool(quality_gate.get('approved_for_final_report'))}`",
            "",
            "## Generated Draft",
            "",
            "This is a deterministic template projection from existing workflow artifacts.",
            "It reorganizes approved material and does not add new source claims.",
            "",
            draft,
            "",
        ]
    )


def cmd_template(args: argparse.Namespace) -> int:
    if args.list:
        for name in sorted(TEMPLATE_NAMES):
            print(name)
        return 0
    if args.project_root is None:
        print("--project-root is required unless --list is used", file=sys.stderr)
        return 1
    project_root = args.project_root.resolve()
    if args.template not in TEMPLATE_NAMES:
        print(f"unknown template: {args.template}", file=sys.stderr)
        return 1
    source_status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
    quality_gate = read_json(project_root / "20_document" / "quality_gate.json")
    provenance = ingest.current_provenance(project_root)
    state = source_status.get("source_status")
    if not provenance["gate_current"]:
        print("template output refuses stale or unverified source-gate artifacts", file=sys.stderr)
        return 1
    if state not in {"source_confirmed", "source_partial"} and not args.allow_degraded:
        print("template output requires source_confirmed/source_partial unless --allow-degraded is used", file=sys.stderr)
        return 1
    if not (provenance["final_report_current"] and quality_gate.get("approved_for_final_report")) and not args.allow_degraded:
        print("template output requires an approved final report unless --allow-degraded is used", file=sys.stderr)
        return 1
    output = args.output or (project_root / "30_final" / f"{args.template}.md")
    write_text(output, render_template_output(project_root, args.template))
    print(f"Template output: {output}")
    return 0


def resolve_batch_input(csv_path: Path, value: str) -> str:
    if is_url(value):
        return value
    path = Path(value)
    if not path.is_absolute():
        path = (csv_path.parent / path).resolve()
    return str(path)


def md_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def batch_priority_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(value.strip().lower(), 3)


def batch_readiness_rank(row: dict[str, str]) -> int:
    if row.get("status") != "completed":
        return 3
    if row.get("quality_gate_approved") == "True":
        return 0
    if row.get("source_status") in {"source_confirmed", "source_partial"}:
        return 1
    return 2


def collect_batch_item_status(
    row: dict[str, str],
    item_project: Path,
    result_index: Path,
    template_name: str,
    status: str,
    message: str,
) -> dict[str, str]:
    source_status = read_json(item_project / "10_video" / "00_source" / "source_status.json")
    quality_gate = read_json(item_project / "20_document" / "quality_gate.json")
    provenance = ingest.current_provenance(item_project)
    final_report = item_project / "20_document" / "final_report.md"
    video_pack = item_project / "10_video" / "video_analysis_pack.md"
    template_output = item_project / "30_final" / f"{template_name}.md" if template_name else None
    return {
        "id": row["id"],
        "priority": row.get("priority") or "",
        "goal": row.get("goal") or "",
        "mode": row["mode"],
        "language": row["language"],
        "template": template_name,
        "status": status,
        "source_status": str(source_status.get("source_status") or "unknown"),
        "full_analysis_allowed": str(bool(provenance["gate_current"] and source_status.get("can_enter_full_decomposition"))),
        "quality_gate_approved": str(bool(provenance["final_report_current"] and quality_gate.get("approved_for_final_report"))),
        "final_report_exists": str(bool(provenance["final_report_current"])),
        "template_output_exists": str(bool(template_output and template_output.is_file())),
        "project": str(item_project),
        "result_index": str(result_index),
        "final_report": str(final_report),
        "template_output": str(template_output or ""),
        "message": message,
    }


def render_batch_summary(status_rows: list[dict[str, str]]) -> str:
    completed = [row for row in status_rows if row["status"] == "completed"]
    approved = [row for row in status_rows if row["quality_gate_approved"] == "True"]
    source_counts: dict[str, int] = {}
    for row in status_rows:
        source_counts[row["source_status"]] = source_counts.get(row["source_status"], 0) + 1
    lines = [
        "# Batch Summary",
        "",
        f"- Items: `{len(status_rows)}`",
        f"- Completed: `{len(completed)}`",
        f"- Failed or partial: `{len(status_rows) - len(completed)}`",
        f"- Quality-approved final reports: `{len(approved)}`",
        "",
        "## Source Status Counts",
        "",
    ]
    for key in sorted(source_counts):
        lines.append(f"- `{key}`: `{source_counts[key]}`")
    lines.extend(
        [
            "",
            "## Item Index",
            "",
            "| ID | Priority | Status | Source | Quality | Result | Final | Template |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in status_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_cell(row["id"]),
                    md_cell(row["priority"]),
                    md_cell(row["status"]),
                    md_cell(row["source_status"]),
                    md_cell(row["quality_gate_approved"]),
                    md_cell(row["result_index"]),
                    md_cell(row["final_report"]),
                    md_cell(row["template_output"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Start with `batch_status.csv` for machine-readable status, then use",
            "`recommended_watch_order.md` to read approved items first.",
            "",
        ]
    )
    return "\n".join(lines)


def render_recommended_order(status_rows: list[dict[str, str]]) -> str:
    ordered = sorted(
        status_rows,
        key=lambda row: (batch_priority_rank(row["priority"]), batch_readiness_rank(row), row["id"]),
    )
    lines = [
        "# Recommended Watch / Read Order",
        "",
        "Order is deterministic: priority first, then source/quality readiness, then ID.",
        "",
    ]
    for idx, row in enumerate(ordered, start=1):
        rationale = []
        if row["priority"]:
            rationale.append(f"priority={row['priority']}")
        rationale.append(f"source={row['source_status']}")
        rationale.append(f"quality={row['quality_gate_approved']}")
        lines.append(f"{idx}. `{row['id']}` - {row['goal'] or row['result_index']}")
        lines.append(f"   - Rationale: {', '.join(rationale)}.")
        lines.append(f"   - Start: `{row['result_index']}`")
    lines.append("")
    return "\n".join(lines)


def render_comparative_report(status_rows: list[dict[str, str]]) -> str:
    lines = [
        "# Comparative Report",
        "",
        "This deterministic batch report compares workflow readiness, not source",
        "claims. Use each item final report for content-level synthesis.",
        "",
        "## Reliability Tiers",
        "",
    ]
    tiers = [
        ("Ready for synthesis", lambda row: row["quality_gate_approved"] == "True"),
        (
            "Needs review before synthesis",
            lambda row: row["status"] == "completed" and row["quality_gate_approved"] != "True",
        ),
        ("Not ready", lambda row: row["status"] != "completed"),
    ]
    for title, predicate in tiers:
        matching = [row for row in status_rows if predicate(row)]
        ids = ", ".join(f"`{row['id']}`" for row in matching) or "None"
        lines.append(f"- {title}: {ids}")
    lines.extend(
        [
            "",
            "## Item Matrix",
            "",
            "| ID | Goal | Priority | Source | Quality | Template | Next Action |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in status_rows:
        if row["status"] != "completed":
            next_action = row["message"] or "Inspect item result and logs."
        elif row["quality_gate_approved"] != "True":
            next_action = "Inspect quality gate before using this item in synthesis."
        elif row["template_output_exists"] == "True":
            next_action = "Use final report and template output."
        else:
            next_action = "Use final report."
        lines.append(
            "| "
            + " | ".join(
                [
                    md_cell(row["id"]),
                    md_cell(row["goal"]),
                    md_cell(row["priority"]),
                    md_cell(row["source_status"]),
                    md_cell(row["quality_gate_approved"]),
                    md_cell(row["template"]),
                    md_cell(next_action),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Synthesis Boundary",
            "",
            "Only compare claims after opening the per-item final reports and checking",
            "their Source / Inference / Extension sections. Batch-level metadata is not",
            "evidence for source claims.",
            "",
        ]
    )
    return "\n".join(lines)


def batch_approved_claims(status_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    for row in status_rows:
        if row.get("status") != "completed" or row.get("quality_gate_approved") != "True":
            continue
        project = Path(row.get("project") or "")
        claim_map = read_json(project / "20_document" / "claim_map.json")
        for claim in claim_map.get("claims", []):
            if not isinstance(claim, dict) or claim.get("status") != "accepted":
                continue
            text = str(claim.get("text") or "").strip()
            if not text:
                continue
            claims.append(
                {
                    "item_id": row["id"],
                    "claim_id": str(claim.get("id") or ""),
                    "category": str(claim.get("category") or "Unknown"),
                    "text": text,
                    "goal": row.get("goal") or "",
                    "final_report": row.get("final_report") or "",
                }
            )
    return claims


def claim_theme(text: str) -> str:
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text)
        if word.lower()
        not in {
            "that",
            "this",
            "with",
            "from",
            "into",
            "before",
            "after",
            "therefore",
            "means",
            "must",
        }
    ]
    return words[0] if words else "general"


def build_theme_clusters(claims: list[dict[str, str]]) -> list[dict[str, object]]:
    clusters: dict[str, list[dict[str, str]]] = {}
    for claim in claims:
        clusters.setdefault(claim_theme(claim["text"]), []).append(claim)
    return [
        {
            "theme": theme,
            "items": sorted({claim["item_id"] for claim in grouped}),
            "claims": grouped,
        }
        for theme, grouped in sorted(clusters.items())
    ]


def render_cross_source_synthesis(claims: list[dict[str, str]], clusters: list[dict[str, object]]) -> str:
    lines = [
        "# Cross-Source Synthesis",
        "",
        "This synthesis uses only accepted claims from completed, quality-approved",
        "batch items. It does not use batch metadata as source evidence.",
        "",
        "## Source Boundary",
        "",
        "- Failed, partial, or unapproved items are excluded.",
        "- Every synthesized point below cites item id and claim id.",
        "- Open the per-item final report before reusing content claims.",
        "",
        "## Theme Clusters",
        "",
    ]
    if not clusters:
        lines.append("No approved claims were available for synthesis.")
    for cluster in clusters:
        claims_in_cluster = cluster["claims"]
        lines.append(f"### {cluster['theme']}")
        lines.append("")
        for claim in claims_in_cluster:  # type: ignore[assignment]
            lines.append(f"- `{claim['item_id']}` / `{claim['claim_id']}`: {claim['text']}")
        lines.append("")
    lines.extend(
        [
            "## Reuse Guidance",
            "",
            "Use repeated themes for study order and unique claims for deeper review.",
            "Do not present any synthesized statement without its item and claim IDs.",
            "",
        ]
    )
    return "\n".join(lines)


def render_repeated_claims(claims: list[dict[str, str]]) -> str:
    by_text: dict[str, list[dict[str, str]]] = {}
    for claim in claims:
        key = " ".join(claim["text"].lower().split())
        by_text.setdefault(key, []).append(claim)
    repeated = [group for group in by_text.values() if len({claim["item_id"] for claim in group}) > 1]
    lines = ["# Repeated Claims", ""]
    if not repeated:
        lines.append("No repeated accepted claims were detected across approved batch items.")
    for group in repeated:
        lines.append(f"- {group[0]['text']}")
        lines.append("  - Evidence: " + ", ".join(f"`{claim['item_id']}`/`{claim['claim_id']}`" for claim in group))
    lines.append("")
    return "\n".join(lines)


def render_unique_insights(claims: list[dict[str, str]]) -> str:
    by_text: dict[str, list[dict[str, str]]] = {}
    for claim in claims:
        key = " ".join(claim["text"].lower().split())
        by_text.setdefault(key, []).append(claim)
    lines = ["# Unique Insights", ""]
    unique = [group[0] for group in by_text.values() if len({claim["item_id"] for claim in group}) == 1]
    if not unique:
        lines.append("No unique accepted claims were detected.")
    for claim in unique:
        lines.append(f"- `{claim['item_id']}` / `{claim['claim_id']}`: {claim['text']}")
    lines.append("")
    return "\n".join(lines)


def render_conflict_map(claims: list[dict[str, str]]) -> str:
    return "\n".join(
        [
            "# Conflict Map",
            "",
            "No deterministic conflicts were detected.",
            "",
            "This first-pass map does not infer contradiction from wording alone.",
            "A future reviewer should mark conflicts only when approved claims make",
            "incompatible assertions over the same subject, scope, and time frame.",
            "",
            f"- Approved claims inspected: `{len(claims)}`",
            "",
        ]
    )


def render_recommended_research_path(claims: list[dict[str, str]]) -> str:
    item_ids = []
    for claim in claims:
        if claim["item_id"] not in item_ids:
            item_ids.append(claim["item_id"])
    lines = ["# Recommended Research Path", ""]
    if not item_ids:
        lines.append("No approved items are ready for content-level synthesis.")
    for idx, item_id in enumerate(item_ids, start=1):
        item_claims = [claim for claim in claims if claim["item_id"] == item_id]
        lines.append(f"{idx}. `{item_id}`")
        lines.append(f"   - Approved claims available: `{len(item_claims)}`")
        lines.append("   - Start with the item final report, then inspect claim IDs.")
    lines.append("")
    return "\n".join(lines)


def write_batch_synthesis(output_root: Path, status_rows: list[dict[str, str]]) -> None:
    claims = batch_approved_claims(status_rows)
    clusters = build_theme_clusters(claims)
    write_text(output_root / "theme_clusters.json", json.dumps(clusters, ensure_ascii=False, indent=2))
    write_text(output_root / "cross_source_synthesis.md", render_cross_source_synthesis(claims, clusters))
    write_text(output_root / "repeated_claims.md", render_repeated_claims(claims))
    write_text(output_root / "unique_insights.md", render_unique_insights(claims))
    write_text(output_root / "conflict_map.md", render_conflict_map(claims))
    write_text(output_root / "recommended_research_path.md", render_recommended_research_path(claims))


def cmd_batch(args: argparse.Namespace) -> int:
    csv_path = args.input.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append({key: (value or "").strip() for key, value in row.items()})

    status_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        item_id = row.get("id") or f"{index:03d}"
        item_input = row.get("input") or row.get("url") or ""
        item_mode = row.get("mode") or args.mode
        item_language = row.get("language") or args.language
        template_name = row.get("template") or ""
        batch_row = {
            "id": item_id,
            "priority": row.get("priority") or "",
            "goal": row.get("goal") or "",
            "mode": item_mode,
            "language": item_language,
        }
        item_project = contained_child_path(output_root, output_root / item_id, "batch item output")
        status = "failed"
        result_index = item_project / "result_index.md"
        message = ""
        try:
            if item_project.exists():
                shutil.rmtree(item_project)
            resolved_input = resolve_batch_input(csv_path, item_input)
            run_args = argparse.Namespace(
                input=resolved_input,
                mode=item_mode,
                project_root=item_project,
                language=item_language,
                final_language=item_language,
                document_goal=row.get("goal") or "batch research item",
                audience="batch research reader",
                asr_model=args.asr_model,
                platform_mode="auto",
                youtube_cookies=None,
                resume=False,
                pretty=False,
            )
            code = cmd_run(run_args)
            status = "completed" if code == 0 else "failed"
            if code == 0 and template_name:
                template_args = argparse.Namespace(
                    project_root=item_project,
                    template=template_name,
                    output=None,
                    list=False,
                    allow_degraded=False,
                )
                template_code = cmd_template(template_args)
                if template_code != 0:
                    status = "template_failed"
            message = "ok" if status == "completed" else status
        except Exception as exc:  # noqa: BLE001 - batch should continue across items
            message = str(exc)
        status_rows.append(
            collect_batch_item_status(
                batch_row,
                item_project,
                result_index,
                template_name,
                status,
                message,
            )
        )

    status_csv = output_root / "batch_status.csv"
    with status_csv.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "id",
            "priority",
            "goal",
            "mode",
            "language",
            "template",
            "status",
            "source_status",
            "full_analysis_allowed",
            "quality_gate_approved",
            "final_report_exists",
            "template_output_exists",
            "project",
            "result_index",
            "final_report",
            "template_output",
            "message",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(status_rows)
    write_text(output_root / "batch_items.json", json.dumps(status_rows, ensure_ascii=False, indent=2))

    completed = [row for row in status_rows if row["status"] == "completed"]
    write_text(output_root / "batch_summary.md", render_batch_summary(status_rows))
    write_text(output_root / "recommended_watch_order.md", render_recommended_order(status_rows))
    write_text(output_root / "comparative_report.md", render_comparative_report(status_rows))
    write_batch_synthesis(output_root, status_rows)
    print(f"Batch output: {output_root}")
    print(f"Batch status: {status_csv}")
    return 0 if len(completed) == len(status_rows) else 1


def cmd_chrome_probe(args: argparse.Namespace) -> int:
    project_root = args.project_root.resolve()
    video_root = project_root / "10_video"
    command = [
        sys.executable,
        str(VIDEO / "scripts" / "chrome_media_probe.py"),
        "--input-json",
        str(args.input_json.resolve()),
        "--output-root",
        str(video_root),
    ]
    if args.pretty:
        command.append("--pretty")
    code = run_command(command, cwd=VIDEO / "scripts", show_output=args.pretty)
    try:
        write_result(project_root, args.pretty)
    except KwError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Chrome probe artifacts: {video_root / '00_source'}")
    print(f"Result index: {project_root / 'result_index.md'}")
    return code


def validation_command_list(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    commands: list[tuple[str, list[str]]] = [
        (
            "compile",
            [
                sys.executable,
                "-m",
                "py_compile",
                "kw.py",
                "kw_cli/main.py",
                "kw_cli/bundle.py",
                "kw_cli/agent_reach_adapter.py",
                "kw_cli/ingest.py",
                "kw_cli/canonicalize.py",
                "kw_cli/redaction.py",
                "kw_cli/run_context.py",
                "kw_cli/source_gate.py",
                str(CONSOLE / "scripts" / "workflow_provenance.py"),
                str(CONSOLE / "scripts" / "workflow_preflight.py"),
                str(CONSOLE / "scripts" / "workflow_status_summary.py"),
                str(CONSOLE / "scripts" / "result_index_writer.py"),
                str(VIDEO / "scripts" / "doctor.py"),
                str(VIDEO / "scripts" / "chrome_media_probe.py"),
                "tests/knowledge_workflow_regression.py",
            ],
        ),
        ("demo", [sys.executable, "kw.py", "demo"]),
        ("regression", [sys.executable, "tests/knowledge_workflow_regression.py"]),
        ("real_workflow_acceptance", [sys.executable, "tests/real_workflow_acceptance.py"]),
        ("acquisition_bundle_schema", [sys.executable, "tests/test_acquisition_bundle_schema.py"]),
        ("local_bundle_ingest", [sys.executable, "tests/test_local_bundle_ingest.py"]),
        ("agent_reach_acquire_offline", [sys.executable, "tests/test_agent_reach_acquire_offline.py"]),
        ("agent_reach_native_export", [sys.executable, "tests/test_agent_reach_native_export.py"]),
        ("source_gate_from_bundle", [sys.executable, "tests/test_source_gate_from_bundle.py"]),
        ("no_fake_report_from_agent_reach_failures", [sys.executable, "tests/test_no_fake_report_from_agent_reach_failures.py"]),
        ("run_provenance", [sys.executable, "tests/test_run_provenance.py"]),
        ("browser_export_flow", [sys.executable, "tests/test_browser_export_flow.py"]),
    ]
    if args.include_live_platform:
        commands.append(("live_platform_smoke", [sys.executable, "tests/live_platform_smoke.py"]))
    if args.include_real_asr:
        commands.append(("asr_integration", [sys.executable, "tests/asr_integration.py"]))
    if args.include_sync:
        if os.name == "nt":
            commands.append(("sync_verify", ["powershell", "-NoProfile", "-File", "sync_to_codex_skills.ps1", "-VerifyOnly"]))
        else:
            commands.append(("sync_verify", ["sh", "sync_to_codex_skills.sh", "--verify-only"]))
    return commands


def cmd_validate(args: argparse.Namespace) -> int:
    commands = validation_command_list(args)
    output_root = (args.output_root or (REPO_ROOT / "test_outputs" / "validation" / timestamp_id())).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for name, command in commands:
        record: dict[str, object] = {
            "name": name,
            "command": command,
            "status": "planned" if args.dry_run else "pending",
            "returncode": None,
        }
        if args.dry_run:
            records.append(record)
            continue
        started = datetime.now(timezone.utc)
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        stdout_path = output_root / f"{name}.stdout.txt"
        stderr_path = output_root / f"{name}.stderr.txt"
        write_text(stdout_path, completed.stdout)
        write_text(stderr_path, completed.stderr)
        record.update(
            {
                "status": "pass" if completed.returncode == 0 else "fail",
                "returncode": completed.returncode,
                "started_at": started.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
            }
        )
        records.append(record)
    passed = all(record["status"] in {"planned", "pass"} for record in records)
    summary = {
        "runner": "kw-validate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": bool(args.dry_run),
        "passed": passed,
        "output_root": str(output_root),
        "commands": records,
    }
    write_text(output_root / "validation_summary.json", json.dumps(summary, ensure_ascii=False, indent=2))
    lines = [
        "# Validation Summary",
        "",
        f"- Dry run: `{bool(args.dry_run)}`",
        f"- Passed: `{passed}`",
        "",
        "| Check | Status | Return Code |",
        "| --- | --- | --- |",
    ]
    for record in records:
        lines.append(f"| {record['name']} | `{record['status']}` | `{record['returncode']}` |")
    lines.append("")
    write_text(output_root / "validation_summary.md", "\n".join(lines))
    print(f"Validation summary: {output_root / 'validation_summary.md'}")
    return 0 if passed else 1


def add_source_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--target",
        choices=sorted(source_gate.ANALYSIS_TARGETS),
        default="auto",
        help="Material scope that must pass the source gate.",
    )
    parser.add_argument(
        "--operation",
        choices=sorted(source_gate.OPERATIONS),
        default="auto",
        help="Acquisition capability required from the active backend.",
    )


def add_youtube_acquisition_arguments(parser: argparse.ArgumentParser, *, include_platform_mode: bool = True) -> None:
    if include_platform_mode:
        parser.add_argument("--platform-mode", choices=["auto", "probe", "subtitles", "audio"], default="auto")
    access = parser.add_mutually_exclusive_group()
    access.add_argument("--youtube-cookies", help="Path to user-exported Netscape cookies.txt, or 'auto' for work/youtube-cookies/youtube.cookies.txt.")
    access.add_argument(
        "--youtube-browser",
        choices=["edge", "chrome"],
        help="Use the named local browser profile through yt-dlp --cookies-from-browser. Do not guess this from the control plugin name.",
    )
    parser.add_argument(
        "--browser-host",
        choices=["edge", "chrome"],
        help="Actual host browser for an OpenCLI session or browser export. Never infer it from a tool or extension name.",
    )
    parser.add_argument("--opencli-window", choices=["foreground", "background"], default="foreground", help="Window mode for an authorized OpenCLI acquisition. Foreground is the stable default for interactive platforms.")
    parser.add_argument("--opencli-site-session", choices=["persistent", "ephemeral"], default="persistent", help="OpenCLI site-session lifecycle for authorized platform acquisition.")
    parser.add_argument("--opencli-keep-tab", action=argparse.BooleanOptionalAction, default=True, help="Keep the authorized OpenCLI tab after acquisition. Use --no-opencli-keep-tab to close it after the command.")
    parser.add_argument("--ytdlp", type=Path, help="Optional yt-dlp executable override.")
    parser.add_argument("--node", type=Path, help="Optional Node.js executable override for yt-dlp JavaScript challenge handling.")
    parser.add_argument("--platform-timeout-seconds", type=int, default=90)
    parser.add_argument("--subtitle-languages", default="all,-live_chat")
    parser.add_argument("--use-js-runtime", action="store_true", help="Pass Node.js to yt-dlp for YouTube player challenge handling.")
    parser.add_argument("--use-remote-components", action="store_true", help="Allow yt-dlp remote EJS solver components.")
    parser.add_argument("--ytdlp-extractor-args", action="append", default=[], help="Raw yt-dlp --extractor-args value, e.g. youtube:fetch_pot=auto.")
    parser.add_argument("--ytdlp-player-clients", default="default,mweb,web,android_vr", help="Comma-separated YouTube player_client list. Use an empty string to disable.")
    parser.add_argument("--youtube-visitor-data", help="Visitor Data passed to yt-dlp; never persisted in clear text.")
    parser.add_argument("--youtube-po-token", action="append", default=[], help="PO Token passed to yt-dlp; never persisted in clear text.")
    parser.add_argument("--ytdlp-proxy", help="Proxy URL passed to yt-dlp --proxy.")
    parser.add_argument("--ytdlp-impersonate", help="Client passed to yt-dlp --impersonate, e.g. chrome.")
    parser.add_argument("--ytdlp-sleep-requests", type=float, help="Seconds passed to yt-dlp --sleep-requests.")
    parser.add_argument("--ytdlp-retry-sleep", action="append", default=[], help="Repeatable yt-dlp --retry-sleep expression.")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Knowledge Workflow product CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local workflow prerequisites.")
    doctor.add_argument("--youtube-cookies", help="Path to user-exported Netscape cookies.txt, or 'auto' for work/youtube-cookies/youtube.cookies.txt.")
    doctor.add_argument("--asr-python")
    doctor.add_argument("--output-json", type=Path)
    doctor.add_argument("--output-md", type=Path)
    doctor.add_argument("--overwrite", action="store_true")
    doctor.add_argument("--json", action="store_true", help="Print full compact JSON to stdout.")
    doctor.add_argument("--pretty", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    preflight = subparsers.add_parser("preflight", help="Estimate route and required user actions.")
    preflight.add_argument("--input", required=True)
    preflight.add_argument("--mode", choices=["quick", "standard", "audit"], default="audit")
    preflight.add_argument("--project-root", type=Path)
    preflight.add_argument("--pretty", action="store_true")
    preflight.set_defaults(func=cmd_preflight)

    agent_reach = subparsers.add_parser("agent-reach", help="Manage Agent-Reach acquisition readiness.")
    agent_reach_sub = agent_reach.add_subparsers(dest="agent_reach_command", required=True)
    agent_reach_install = agent_reach_sub.add_parser("install", help="Install or update Agent-Reach.")
    agent_reach_install.add_argument("--safe", action="store_true", help="Safe mode: do not auto-install system packages.")
    agent_reach_install.add_argument("--dry-run", action="store_true", help="Show what would be done.")
    agent_reach_install.add_argument("--channels", default="", help="Comma-separated optional Agent-Reach channels, e.g. opencli,twitter,xiaohongshu.")
    agent_reach_install.add_argument("--allow-upstream-cookie-import", action="store_true", help="Allow Agent-Reach's own automatic Chrome/Firefox cookie import for selected channels.")
    agent_reach_install.set_defaults(func=cmd_agent_reach_install)
    agent_reach_doctor = agent_reach_sub.add_parser("doctor", help="Run agent-reach doctor --json.")
    agent_reach_doctor.add_argument("--output-json", type=Path)
    agent_reach_doctor.set_defaults(func=cmd_agent_reach_doctor)
    agent_reach_matrix = agent_reach_sub.add_parser("matrix", help="Show all Agent-Reach channels and their current integration path.")
    agent_reach_matrix.add_argument("--output-json", type=Path)
    agent_reach_matrix.add_argument("--output-md", type=Path)
    agent_reach_matrix.set_defaults(func=cmd_agent_reach_matrix)
    agent_reach_plan = agent_reach_sub.add_parser("plan", help="Show Agent-Reach route plan for an input.")
    agent_reach_plan.add_argument("--input", required=True)
    agent_reach_plan.add_argument("--output-json", type=Path)
    add_source_target_arguments(agent_reach_plan)
    agent_reach_plan.add_argument("--browser-host", choices=["edge", "chrome"])
    agent_reach_plan.set_defaults(func=cmd_agent_reach_plan)
    agent_reach_import = agent_reach_sub.add_parser(
        "import",
        help="Import task-primary material exported by a native Agent-Reach channel into Bundle v2.",
    )
    agent_reach_import.add_argument("--input-file", type=Path, required=True)
    agent_reach_import.add_argument("--source-url", required=True)
    agent_reach_import.add_argument("--platform", choices=sorted(source_gate.UPSTREAM_AGENT_REACH_PLATFORMS), required=True)
    agent_reach_import.add_argument("--project-root", type=Path)
    agent_reach_import.add_argument("--language", default="unknown")
    agent_reach_import.add_argument("--content-scope", choices=sorted(source_gate.CONTENT_SCOPES - {"unknown"}))
    agent_reach_import.add_argument("--partial", action="store_true")
    agent_reach_import.add_argument("--credentialed-session", action="store_true", help="Record that the upstream export used an authorized login or cookie session.")
    agent_reach_import.add_argument("--browser-host", choices=["edge", "chrome"], help="Actual Edge or Chrome host when the native route used OpenCLI.")
    add_source_target_arguments(agent_reach_import)
    agent_reach_import.add_argument("--resume", action="store_true")
    agent_reach_import.set_defaults(func=cmd_agent_reach_import)

    acquire = subparsers.add_parser("acquire", help="Acquire URL/query material into 00_acquisition/manifest.json.")
    acquire.add_argument("--input", required=True, help="URL or query to acquire.")
    acquire.add_argument("--project-root", type=Path)
    acquire.add_argument("--query", action="store_true", help="Treat --input as a query rather than a path.")
    add_source_target_arguments(acquire)
    add_youtube_acquisition_arguments(acquire)
    acquire.add_argument("--resume", action="store_true", help="Retry the same source and target in this project root.")
    acquire.set_defaults(func=cmd_acquire)

    browser_import = subparsers.add_parser(
        "browser-import",
        help="Import a local artifact exported from an authorized browser session into Bundle v2.",
    )
    browser_import.add_argument("--input-file", type=Path, required=True)
    browser_import.add_argument("--source-url", required=True)
    browser_import.add_argument("--platform", choices=["bilibili", "github", "web", "x", "xiaohongshu", "youtube"], required=True)
    browser_import.add_argument("--project-root", type=Path)
    browser_import.add_argument("--language", default="unknown")
    browser_import.add_argument("--content-scope", choices=sorted(source_gate.CONTENT_SCOPES - {"unknown"}))
    browser_import.add_argument("--partial", action="store_true")
    add_source_target_arguments(browser_import)
    browser_import.add_argument("--browser-host", choices=["edge", "chrome"], help="Actual Edge or Chrome host that produced the export.")
    browser_import.add_argument("--resume", action="store_true")
    browser_import.set_defaults(func=cmd_browser_import)

    ingest_cmd = subparsers.add_parser("ingest", help="Validate and ingest an acquisition bundle.")
    ingest_cmd.add_argument("--bundle", type=Path, required=True, help="Path to 00_acquisition/manifest.json.")
    ingest_cmd.add_argument("--project-root", type=Path, required=True)
    ingest_cmd.add_argument("--pretty", action="store_true")
    ingest_cmd.set_defaults(func=cmd_ingest)

    validate_bundle = subparsers.add_parser("validate-bundle", help="Validate an acquisition bundle manifest.")
    validate_bundle.add_argument("--bundle", type=Path, required=True)
    validate_bundle.set_defaults(func=cmd_validate_bundle)

    audit = subparsers.add_parser("audit", help="Run source-gated decomposition and document planning.")
    audit.add_argument("--project-root", type=Path, required=True)
    audit.add_argument("--document-goal", default="source-faithful knowledge report")
    audit.add_argument("--final-language", default="current conversation language")
    audit.add_argument("--audience", default="reader who needs an auditable source-faithful explanation")
    audit.add_argument("--pretty", action="store_true")
    audit.set_defaults(func=cmd_audit)

    compose = subparsers.add_parser("compose", help="Run final report writer from document planning artifacts.")
    compose.add_argument("--project-root", type=Path, required=True)
    compose.add_argument("--pretty", action="store_true")
    compose.set_defaults(func=cmd_compose)

    run = subparsers.add_parser("run", help="Run a local transcript, media file, or URL through the workflow.")
    run.add_argument("--input", required=True)
    run.add_argument("--mode", choices=["quick", "standard", "audit"], default="audit")
    run.add_argument("--project-root", type=Path)
    run.add_argument("--language", default="unknown")
    run.add_argument("--final-language", default="current conversation language")
    run.add_argument("--document-goal", default="source-faithful knowledge report")
    run.add_argument("--audience", default="reader who needs an auditable source-faithful explanation")
    add_source_target_arguments(run)
    run.add_argument("--browser-source-url", help="Original URL for a local artifact exported from an authorized browser session.")
    run.add_argument("--browser-platform", choices=["bilibili", "github", "web", "x", "xiaohongshu", "youtube"])
    run.add_argument("--content-scope", choices=sorted(source_gate.CONTENT_SCOPES - {"unknown"}))
    run.add_argument("--partial-export", action="store_true", help="Mark a browser export as partial primary material.")
    run.add_argument("--asr-model", default="base")
    run.add_argument("--asr-jsonl", type=Path, help="Existing ASR JSONL to normalize instead of running faster-whisper.")
    run.add_argument("--asr-python", help="Python runtime that can import faster_whisper.")
    run.add_argument("--asr-device", default="cpu")
    run.add_argument("--asr-compute-type", default="int8")
    run.add_argument("--asr-timeout-seconds", type=float, default=0.0)
    asr_vad = run.add_mutually_exclusive_group()
    asr_vad.add_argument("--asr-vad", dest="asr_vad", action="store_true", help="Enable VAD filtering for ASR.")
    asr_vad.add_argument("--no-asr-vad", dest="asr_vad", action="store_false", help="Disable VAD filtering for ASR.")
    run.set_defaults(asr_vad=True)
    add_youtube_acquisition_arguments(run)
    run.add_argument("--resume", action="store_true")
    run.add_argument("--pretty", action="store_true")
    run.set_defaults(func=cmd_run)

    status = subparsers.add_parser("status", help="Refresh status summary and result index.")
    status.add_argument("--project-root", type=Path, required=True)
    status.add_argument("--pretty", action="store_true")
    status.set_defaults(func=cmd_status)

    result = subparsers.add_parser("result", help="Write or refresh result_index.md.")
    result.add_argument("--project-root", type=Path, required=True)
    result.add_argument("--pretty", action="store_true")
    result.set_defaults(func=cmd_result)

    demo = subparsers.add_parser("demo", help="Run the built-in local transcript demo.")
    demo.add_argument("--project-root", type=Path)
    demo.add_argument("--resume", action="store_true")
    demo.add_argument("--pretty", action="store_true")
    demo.set_defaults(func=cmd_demo)

    export = subparsers.add_parser("export", help="Export the final report to 30_final.")
    export.add_argument("--project-root", type=Path, required=True)
    export.add_argument("--format", choices=["md"], default="md")
    export.add_argument("--output", type=Path)
    export.set_defaults(func=cmd_export)

    quality = subparsers.add_parser("quality", help="Write a source-gate aligned quality review.")
    quality.add_argument("--project-root", type=Path, required=True)
    quality.add_argument("--output", type=Path)
    quality.add_argument("--output-json", type=Path)
    quality.add_argument("--allow-needs-review", action="store_true")
    quality.set_defaults(func=cmd_quality)

    template = subparsers.add_parser("template", help="Create a deterministic template output from approved artifacts.")
    template.add_argument("--project-root", type=Path)
    template.add_argument("--template", choices=sorted(TEMPLATE_NAMES), default="research_brief")
    template.add_argument("--output", type=Path)
    template.add_argument("--allow-degraded", action="store_true")
    template.add_argument("--list", action="store_true")
    template.set_defaults(func=cmd_template)

    batch = subparsers.add_parser("batch", help="Run a CSV batch and write batch research summaries.")
    batch.add_argument("--input", type=Path, required=True)
    batch.add_argument("--output-root", type=Path, required=True)
    batch.add_argument("--mode", choices=["quick", "standard", "audit"], default="audit")
    batch.add_argument("--language", default="en")
    batch.add_argument("--asr-model", default="base")
    batch.set_defaults(func=cmd_batch)

    chrome_probe = subparsers.add_parser("chrome-probe", help="Normalize a Chrome observation JSON into workflow artifacts.")
    chrome_probe.add_argument("--input-json", type=Path, required=True)
    chrome_probe.add_argument("--project-root", type=Path, required=True)
    chrome_probe.add_argument("--pretty", action="store_true")
    chrome_probe.set_defaults(func=cmd_chrome_probe)

    validate = subparsers.add_parser("validate", help="Run or plan repository validation checks.")
    validate.add_argument("--output-root", type=Path)
    validate.add_argument("--include-live-platform", action="store_true")
    validate.add_argument("--include-real-asr", action="store_true")
    validate.add_argument("--include-sync", action="store_true")
    validate.add_argument("--dry-run", action="store_true")
    validate.set_defaults(func=cmd_validate)
    return parser


def main() -> int:
    configure_stdio()
    parser = make_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except KwError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
