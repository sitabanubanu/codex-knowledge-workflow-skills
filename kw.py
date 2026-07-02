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
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent
CONSOLE = REPO_ROOT / "skills" / "knowledge-workflow-console"
VIDEO = REPO_ROOT / "skills" / "knowledge-video-decomposer"
DOCUMENT = REPO_ROOT / "skills" / "knowledge-document-composer"
OUTPUT_BASE = REPO_ROOT / "outputs" / "knowledge-workflow"

TRANSCRIPT_EXTENSIONS = {".txt", ".md", ".srt", ".vtt", ".jsonl", ".json"}
MEDIA_EXTENSIONS = {".mp3", ".mp4", ".m4a", ".webm", ".wav", ".mov", ".opus"}
TEMPLATE_NAMES = {"study_notes", "research_brief", "creator_script", "prompt_pack", "action_plan"}


class KwError(Exception):
    """User-facing CLI failure."""


def run_command(command: list[str], *, cwd: Path, show_output: bool = True) -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
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


def slugify(value: str) -> str:
    if is_url(value):
        parsed = urlparse(value)
        basis = f"{parsed.netloc}-{Path(parsed.path).name or 'video'}"
    else:
        basis = Path(value).stem or "workflow"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", basis).strip("-").lower()
    return slug[:48] or "workflow"


def default_project_root(value: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return OUTPUT_BASE / f"{slugify(value)}-{stamp}"


def ensure_project_root(args: argparse.Namespace) -> Path:
    root = args.project_root.resolve() if args.project_root else default_project_root(args.input)
    root.mkdir(parents=True, exist_ok=True)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    return root


def run_preflight(input_value: str, mode: str, project_root: Path, pretty: bool) -> None:
    command = [
        sys.executable,
        str(CONSOLE / "scripts" / "workflow_preflight.py"),
        "--input",
        input_value,
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


def cmd_doctor(args: argparse.Namespace) -> int:
    command = [sys.executable, str(VIDEO / "scripts" / "doctor.py")]
    if args.youtube_cookies:
        command.extend(["--youtube-cookies", str(args.youtube_cookies)])
    if args.asr_python:
        command.extend(["--asr-python", args.asr_python])
    if args.output_json:
        command.extend(["--output-json", str(args.output_json)])
    if args.output_md:
        command.extend(["--output-md", str(args.output_md)])
    if args.overwrite:
        command.append("--overwrite")
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


def cmd_run(args: argparse.Namespace) -> int:
    project_root = ensure_project_root(args)
    input_kind = classify_input(args.input)
    input_value = normalize_input(args.input)
    exit_code = 0
    try:
        run_preflight(input_value, args.mode, project_root, args.pretty)
        if args.mode == "quick":
            write_result(project_root, args.pretty)
            print(f"Quick preflight complete: {project_root / 'result_index.md'}")
            return 0

        runner = [
            sys.executable,
            str(CONSOLE / "scripts" / "end_to_end_runner.py"),
            "--project-root",
            str(project_root),
            "--language",
            args.language,
            "--document-goal",
            args.document_goal,
            "--final-language",
            args.final_language,
            "--audience",
            args.audience,
            "--video-skill-root",
            str(VIDEO),
            "--document-skill-root",
            str(DOCUMENT),
            "--asr-model",
            args.asr_model,
            "--platform-mode",
            args.platform_mode,
        ]
        if input_kind == "url":
            runner.extend(["--input-url", input_value])
        elif input_kind == "media":
            runner.extend(["--input-media", input_value])
        else:
            runner.extend(["--input-transcript", input_value])
        if args.youtube_cookies:
            runner.extend(["--youtube-cookies", str(args.youtube_cookies)])
        if args.ytdlp:
            runner.extend(["--ytdlp", str(args.ytdlp)])
        if args.node:
            runner.extend(["--node", str(args.node)])
        if args.platform_timeout_seconds:
            runner.extend(["--platform-timeout-seconds", str(args.platform_timeout_seconds)])
        if args.subtitle_languages:
            runner.extend(["--subtitle-languages", args.subtitle_languages])
        if args.use_js_runtime:
            runner.append("--use-js-runtime")
        if args.use_remote_components:
            runner.append("--use-remote-components")
        for extractor_arg in args.ytdlp_extractor_args or []:
            runner.extend(["--ytdlp-extractor-args", extractor_arg])
        if args.ytdlp_player_clients:
            runner.extend(["--ytdlp-player-clients", args.ytdlp_player_clients])
        if args.youtube_visitor_data:
            runner.extend(["--youtube-visitor-data", args.youtube_visitor_data])
        for po_token in args.youtube_po_token or []:
            runner.extend(["--youtube-po-token", po_token])
        if args.ytdlp_proxy:
            runner.extend(["--ytdlp-proxy", args.ytdlp_proxy])
        if args.ytdlp_impersonate:
            runner.extend(["--ytdlp-impersonate", args.ytdlp_impersonate])
        if args.ytdlp_sleep_requests is not None:
            runner.extend(["--ytdlp-sleep-requests", str(args.ytdlp_sleep_requests)])
        for retry_sleep in args.ytdlp_retry_sleep or []:
            runner.extend(["--ytdlp-retry-sleep", retry_sleep])
        if args.resume:
            runner.append("--resume")
        if args.pretty:
            runner.append("--pretty")
        run_required(runner, cwd=CONSOLE / "scripts")

        if args.mode == "audit" and (project_root / "20_document" / "composer_intake.json").is_file():
            final_writer = [
                sys.executable,
                str(DOCUMENT / "scripts" / "final_report_writer.py"),
                "--document-root",
                str(project_root / "20_document"),
            ]
            if args.pretty:
                final_writer.append("--pretty")
            run_required(final_writer, cwd=DOCUMENT / "scripts")
    except KwError as exc:
        exit_code = 1
        print(str(exc), file=sys.stderr)
    finally:
        try:
            if (project_root / "10_video").exists() or (project_root / "logs" / "run_state.json").exists():
                write_status(project_root, args.pretty)
            write_result(project_root, args.pretty)
        except KwError as exc:
            exit_code = 1
            print(str(exc), file=sys.stderr)

    print(f"Project: {project_root}")
    print(f"Result index: {project_root / 'result_index.md'}")
    return exit_code


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
    if not source.is_file():
        print(f"missing final report: {source}", file=sys.stderr)
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


def cmd_quality(args: argparse.Namespace) -> int:
    project_root = args.project_root.resolve()
    source_status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
    quality_gate = read_json(project_root / "20_document" / "quality_gate.json")
    final_report = project_root / "20_document" / "final_report.md"
    final_text = final_report.read_text(encoding="utf-8") if final_report.is_file() else ""
    checks = [
        ("source_status_known", bool(source_status.get("source_status"))),
        ("primary_material_labeled", "primary_material_available" in source_status),
        ("full_report_gate_approved", bool(quality_gate.get("approved_for_final_report"))),
        ("source_section_present", "## Source" in final_text),
        ("inference_section_present", "## Inference" in final_text),
        ("extension_section_present", "## Extension" in final_text),
        ("no_cookie_literal", "cookie" not in final_text.lower() or "cookies" not in final_text.lower()),
    ]
    passed = all(value for _, value in checks)
    lines = [
        "# Quality Review",
        "",
        f"- Project: `{project_root}`",
        f"- Overall: `{'pass' if passed else 'needs_review'}`",
        f"- Source status: `{source_status.get('source_status', 'unknown')}`",
        "",
        "## Checks",
        "",
        "| Check | Pass |",
        "| --- | --- |",
    ]
    for name, value in checks:
        lines.append(f"| {name} | `{bool(value)}` |")
    lines.extend(
        [
            "",
            "## Rubric",
            "",
            "See `quality_rubric.md` for the human review dimensions: source faithfulness, Source / Inference / Extension separation, claim quality, uncertainty, reusability, and safety.",
            "",
        ]
    )
    output = args.output or (project_root / "30_final" / "quality_review.md")
    write_text(output, "\n".join(lines))
    print(f"Quality review: {output}")
    return 0 if passed or args.allow_needs_review else 1


def render_template_output(project_root: Path, template_name: str) -> str:
    template_path = REPO_ROOT / "templates" / f"{template_name}.md"
    template_text = template_path.read_text(encoding="utf-8")
    final_report = project_root / "20_document" / "final_report.md"
    pack = project_root / "10_video" / "video_analysis_pack.md"
    source_status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
    quality_gate = read_json(project_root / "20_document" / "quality_gate.json")
    source_text = final_report.read_text(encoding="utf-8") if final_report.is_file() else ""
    pack_text = pack.read_text(encoding="utf-8") if pack.is_file() else ""
    excerpt = (source_text or pack_text)[:3500].strip()
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
            "This is a deterministic template projection from existing workflow artifacts. It does not add new source claims.",
            "",
            excerpt or "No final report or video analysis pack was available.",
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
    state = source_status.get("source_status")
    if state not in {"source_confirmed", "source_partial"} and not args.allow_degraded:
        print("template output requires source_confirmed/source_partial unless --allow-degraded is used", file=sys.stderr)
        return 1
    if not quality_gate.get("approved_for_final_report") and not args.allow_degraded:
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
        item_project = output_root / item_id
        status = "failed"
        result_index = item_project / "result_index.md"
        message = ""
        try:
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
            {
                "id": item_id,
                "priority": row.get("priority") or "",
                "goal": row.get("goal") or "",
                "mode": item_mode,
                "language": item_language,
                "template": template_name,
                "status": status,
                "project": str(item_project),
                "result_index": str(result_index),
                "message": message,
            }
        )

    status_csv = output_root / "batch_status.csv"
    with status_csv.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["id", "priority", "goal", "mode", "language", "template", "status", "project", "result_index", "message"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(status_rows)

    completed = [row for row in status_rows if row["status"] == "completed"]
    write_text(
        output_root / "batch_summary.md",
        "# Batch Summary\n\n"
        + f"- Items: `{len(status_rows)}`\n"
        + f"- Completed: `{len(completed)}`\n"
        + f"- Failed or partial: `{len(status_rows) - len(completed)}`\n\n"
        + "Start with `batch_status.csv`, then open each item `result_index.md`.\n",
    )
    ordered = sorted(status_rows, key=lambda row: {"high": 0, "medium": 1, "low": 2}.get(row["priority"], 3))
    write_text(
        output_root / "recommended_watch_order.md",
        "# Recommended Order\n\n"
        + "\n".join(f"{idx}. `{row['id']}` - {row['goal'] or row['result_index']}" for idx, row in enumerate(ordered, start=1))
        + "\n",
    )
    write_text(
        output_root / "comparative_report.md",
        "# Comparative Report\n\n"
        "This deterministic batch report records item status and priority. Use the per-item final reports and template outputs for detailed synthesis.\n\n"
        + "| ID | Priority | Status | Goal |\n| --- | --- | --- | --- |\n"
        + "\n".join(f"| {row['id']} | {row['priority']} | {row['status']} | {row['goal']} |" for row in status_rows)
        + "\n",
    )
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


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Knowledge Workflow product CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local workflow prerequisites.")
    doctor.add_argument("--youtube-cookies", type=Path)
    doctor.add_argument("--asr-python")
    doctor.add_argument("--output-json", type=Path)
    doctor.add_argument("--output-md", type=Path)
    doctor.add_argument("--overwrite", action="store_true")
    doctor.add_argument("--pretty", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    preflight = subparsers.add_parser("preflight", help="Estimate route and required user actions.")
    preflight.add_argument("--input", required=True)
    preflight.add_argument("--mode", choices=["quick", "standard", "audit"], default="audit")
    preflight.add_argument("--project-root", type=Path)
    preflight.add_argument("--pretty", action="store_true")
    preflight.set_defaults(func=cmd_preflight)

    run = subparsers.add_parser("run", help="Run a local transcript, media file, or URL through the workflow.")
    run.add_argument("--input", required=True)
    run.add_argument("--mode", choices=["quick", "standard", "audit"], default="audit")
    run.add_argument("--project-root", type=Path)
    run.add_argument("--language", default="unknown")
    run.add_argument("--final-language", default="current conversation language")
    run.add_argument("--document-goal", default="source-faithful knowledge report")
    run.add_argument("--audience", default="reader who needs an auditable source-faithful explanation")
    run.add_argument("--asr-model", default="base")
    run.add_argument("--platform-mode", choices=["auto", "probe", "subtitles", "audio"], default="auto")
    run.add_argument("--youtube-cookies", type=Path)
    run.add_argument("--ytdlp", type=Path, help="Optional yt-dlp executable override.")
    run.add_argument("--node", type=Path, help="Optional Node.js executable override for yt-dlp JavaScript challenge handling.")
    run.add_argument("--platform-timeout-seconds", type=int, default=90)
    run.add_argument("--subtitle-languages", default="all,-live_chat")
    run.add_argument("--use-js-runtime", action="store_true", help="Pass Node.js to yt-dlp for YouTube player challenge handling.")
    run.add_argument("--use-remote-components", action="store_true", help="Allow yt-dlp remote EJS solver components.")
    run.add_argument("--ytdlp-extractor-args", action="append", default=[], help="Raw yt-dlp --extractor-args value, e.g. youtube:fetch_pot=auto.")
    run.add_argument("--ytdlp-player-clients", default="default,mweb,web,android_vr", help="Comma-separated YouTube player_client probe matrix, e.g. default,mweb,web,android_vr. Use an empty string to disable.")
    run.add_argument("--youtube-visitor-data", help="Visitor Data passed to yt-dlp as youtube:visitor_data=...; never logged.")
    run.add_argument("--youtube-po-token", action="append", default=[], help="PO Token passed to yt-dlp, e.g. web.gvs+XXX or web.subs+XXX; never logged.")
    run.add_argument("--ytdlp-proxy", help="Proxy URL passed to yt-dlp --proxy.")
    run.add_argument("--ytdlp-impersonate", help="Client passed to yt-dlp --impersonate, e.g. chrome.")
    run.add_argument("--ytdlp-sleep-requests", type=float, help="Seconds passed to yt-dlp --sleep-requests.")
    run.add_argument("--ytdlp-retry-sleep", action="append", default=[], help="Repeatable yt-dlp --retry-sleep expression.")
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
    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except KwError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
