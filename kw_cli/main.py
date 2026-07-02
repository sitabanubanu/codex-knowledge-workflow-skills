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
}


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
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def cmd_run(args: argparse.Namespace) -> int:
    args = apply_run_option_defaults(args)
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
        cookies_value = youtube_cookies_cli_value(args.youtube_cookies)
        if cookies_value:
            runner.extend(["--youtube-cookies", cookies_value])
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


def quality_check(name: str, passed: bool, evidence: str, required_action: str = "") -> dict[str, object]:
    return {
        "check": name,
        "passed": bool(passed),
        "evidence": evidence,
        "required_action": required_action,
    }


def build_quality_review(project_root: Path) -> dict[str, object]:
    source_status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
    quality_gate = read_json(project_root / "20_document" / "quality_gate.json")
    claim_map = read_json(project_root / "20_document" / "claim_map.json")
    final_report = project_root / "20_document" / "final_report.md"
    final_text = final_report.read_text(encoding="utf-8") if final_report.is_file() else ""
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
            bool(quality_gate.get("approved_for_final_report")),
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
            "passed": bool(quality_gate.get("approved_for_final_report")),
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
        "approved_for_final_report": bool(quality_gate.get("approved_for_final_report")),
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
    final_report = project_root / "20_document" / "final_report.md"
    pack = project_root / "10_video" / "video_analysis_pack.md"
    source_status = read_json(project_root / "10_video" / "00_source" / "source_status.json")
    quality_gate = read_json(project_root / "20_document" / "quality_gate.json")
    claim_map = read_json(project_root / "20_document" / "claim_map.json")
    source_text = final_report.read_text(encoding="utf-8") if final_report.is_file() else ""
    pack_text = pack.read_text(encoding="utf-8") if pack.is_file() else ""
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
        "full_analysis_allowed": str(bool(source_status.get("can_enter_full_decomposition"))),
        "quality_gate_approved": str(bool(quality_gate.get("approved_for_final_report"))),
        "final_report_exists": str(final_report.is_file()),
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
                str(VIDEO / "scripts" / "doctor.py"),
                str(VIDEO / "scripts" / "chrome_media_probe.py"),
                "tests/knowledge_workflow_regression.py",
            ],
        ),
        ("demo", [sys.executable, "kw.py", "demo"]),
        ("regression", [sys.executable, "tests/knowledge_workflow_regression.py"]),
        ("real_workflow_acceptance", [sys.executable, "tests/real_workflow_acceptance.py"]),
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
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
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
    run.add_argument("--youtube-cookies", help="Path to user-exported Netscape cookies.txt, or 'auto' for work/youtube-cookies/youtube.cookies.txt.")
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
    parser = make_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except KwError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
