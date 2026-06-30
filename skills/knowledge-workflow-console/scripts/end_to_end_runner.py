#!/usr/bin/env python
"""Orchestrate the local transcript-to-document knowledge workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


RUNNER_NAME = "knowledge-workflow-end-to-end-runner"
RUN_STATE_SCHEMA_VERSION = 2
STAGE_ORDER = [
    "platform_media_runner",
    "transcript_normalizer",
    "asr_pipeline",
    "transcript_segmenter",
    "inventory_extractor",
    "source_logic_builder",
    "evidence_auditor",
    "video_analysis_pack_builder",
    "document_composer_runner",
]
STAGE_OUTPUTS = {
    "platform_media_runner": [
        "10_video/00_source/platform_media_result.json",
        "10_video/00_source/platform_media_notes.md",
        "10_video/00_source/source_status.json",
    ],
    "asr_pipeline": [
        "10_video/00_source/source_status.json",
        "10_video/01_transcript/clean_transcript.jsonl",
        "10_video/00_source/asr_pipeline_report.json",
        "10_video/00_source/asr_alignment_report.json",
        "10_video/00_source/asr_diarization.json",
    ],
    "transcript_normalizer": [
        "10_video/00_source/source_status.json",
        "10_video/01_transcript/clean_transcript.jsonl",
    ],
    "transcript_segmenter": [
        "10_video/02_segments/argument_segments.json",
        "10_video/02_segments/subtitle_segments.json",
        "10_video/02_segments/syntax_segments.json",
    ],
    "inventory_extractor": [
        "10_video/03_inventory/claims.json",
        "10_video/03_inventory/examples.json",
        "10_video/03_inventory/concepts.json",
        "10_video/03_inventory/analogies.json",
    ],
    "source_logic_builder": [
        "10_video/04_logic/source_logic.md",
        "10_video/04_logic/logic_graph.json",
    ],
    "evidence_auditor": [
        "10_video/05_gap_check/evidence_audit.json",
        "10_video/05_gap_check/gap_check.md",
    ],
    "video_analysis_pack_builder": [
        "10_video/video_analysis_pack.md",
    ],
    "document_composer_runner": [
        "20_document/composer_intake.json",
        "20_document/commitments.md",
        "20_document/claim_map.json",
        "20_document/quality_check.md",
    ],
}

STAGE_RESUME_OUTPUTS = {
    "platform_media_runner": [
        "10_video/00_source/platform_media_result.json",
        "10_video/00_source/platform_media_notes.md",
    ],
}

STAGE_INPUTS = {
    "transcript_segmenter": [
        "10_video/00_source/source_status.json",
        "10_video/01_transcript/clean_transcript.jsonl",
    ],
    "inventory_extractor": [
        "10_video/01_transcript/clean_transcript.jsonl",
        "10_video/02_segments/argument_segments.json",
        "10_video/02_segments/subtitle_segments.json",
        "10_video/02_segments/syntax_segments.json",
    ],
    "source_logic_builder": [
        "10_video/02_segments/argument_segments.json",
        "10_video/03_inventory/claims.json",
        "10_video/03_inventory/examples.json",
        "10_video/03_inventory/concepts.json",
        "10_video/03_inventory/analogies.json",
    ],
    "evidence_auditor": [
        "10_video/01_transcript/clean_transcript.jsonl",
        "10_video/02_segments/argument_segments.json",
        "10_video/02_segments/subtitle_segments.json",
        "10_video/02_segments/syntax_segments.json",
        "10_video/03_inventory/claims.json",
        "10_video/03_inventory/examples.json",
        "10_video/03_inventory/concepts.json",
        "10_video/03_inventory/analogies.json",
        "10_video/04_logic/source_logic.md",
        "10_video/04_logic/logic_graph.json",
    ],
    "video_analysis_pack_builder": [
        "10_video/00_source/source_status.json",
        "10_video/03_inventory/claims.json",
        "10_video/03_inventory/examples.json",
        "10_video/03_inventory/concepts.json",
        "10_video/03_inventory/analogies.json",
        "10_video/04_logic/source_logic.md",
        "10_video/04_logic/logic_graph.json",
        "10_video/05_gap_check/evidence_audit.json",
        "10_video/05_gap_check/gap_check.md",
    ],
    "document_composer_runner": [
        "10_video/00_source/source_status.json",
        "10_video/video_analysis_pack.md",
        "10_video/03_inventory/claims.json",
        "10_video/04_logic/source_logic.md",
        "10_video/04_logic/logic_graph.json",
        "10_video/05_gap_check/evidence_audit.json",
        "10_video/05_gap_check/gap_check.md",
    ],
}

GUIDANCE_BY_STAGE = {
    "platform_media_runner": "Provide primary material or working platform access: official subtitles, a downloadable audio/video file, a user-exported cookies.txt when platform access is blocked, or a browser-derived media/subtitle export.",
    "transcript_normalizer": "Provide a readable transcript/subtitle file in UTF-8 text, SRT, VTT, JSONL, or supported JSON form.",
    "asr_pipeline": "Provide a readable local audio/video file, a valid ASR JSONL, and the local ASR runtime requirements such as ffmpeg and faster-whisper when live ASR is needed.",
    "transcript_segmenter": "Fix or regenerate clean_transcript.jsonl and source_status.json before segmenting.",
    "inventory_extractor": "Fix or regenerate transcript segment artifacts before extracting concepts, examples, claims, and analogies.",
    "source_logic_builder": "Fix or regenerate inventory artifacts and argument segments before reconstructing source logic.",
    "evidence_auditor": "Fix missing transcript spans, inventory evidence, or source logic artifacts before auditing evidence.",
    "video_analysis_pack_builder": "Resolve evidence audit errors or regenerate the audited upstream artifacts before building video_analysis_pack.md.",
    "document_composer_runner": "Provide an allowed video_analysis_pack with passing evidence audit before document planning.",
}


class EndToEndRunnerError(Exception):
    """Expected CLI-facing end-to-end runner failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_text(path: Path, text: str) -> dict[str, Any]:
    target = path.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    temp_path = target.parent / f".{target.name}.{os.getpid()}.tmp"
    temp_path.write_bytes(data)
    os.replace(temp_path, target)
    if target.read_bytes() != data:
        raise EndToEndRunnerError(f"readback mismatch after writing {target}")
    return {"path": str(target), "bytes": len(data), "encoding": "utf-8"}


def write_json(path: Path, payload: Any) -> dict[str, Any]:
    return write_text(path, stable_json(payload))


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise EndToEndRunnerError(f"invalid JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise EndToEndRunnerError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise EndToEndRunnerError(f"JSON file is not an object: {path}")
    return payload


def default_skill_root(skill_name: str) -> Path:
    return Path.home() / ".codex" / "skills" / skill_name


def script_path(skill_root: Path, name: str) -> Path:
    path = skill_root / "scripts" / name
    if not path.is_file():
        raise EndToEndRunnerError(f"required stage script is missing: {path}")
    return path


def run_command(stage: str, command: list[str], cwd: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    payload: dict[str, Any] | None = None
    if stdout:
        try:
            loaded = json.loads(stdout.splitlines()[-1] if len(stdout.splitlines()) > 1 else stdout)
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = None
    result = {
        "stage": stage,
        "command": command,
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "summary": payload,
    }
    return result


def stage_summary(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("summary")
    slim: dict[str, Any] = {
        "stage": result.get("stage"),
        "returncode": result.get("returncode"),
    }
    if isinstance(summary, dict):
        for key in (
            "runner",
            "source_status",
            "material_state",
            "next_step",
            "validation_next_step",
            "composer_decision",
            "final_report_written",
            "pack_path",
            "document_root",
            "output_root",
            "acquired_subtitle_files",
            "acquired_audio_files",
            "workflow_outcome",
        ):
            if key in summary:
                slim[key] = summary[key]
    return slim


def sanitize_project_id(value: str) -> str:
    stem = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-_")
    return stem[:60] or "knowledge-workflow"


def make_project_id_from_path(input_path: Path) -> str:
    return sanitize_project_id(input_path.expanduser().resolve().stem)


def make_project_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "")
    if "youtube.com" in host:
        query = parsed.query
        video_id = ""
        for item in query.split("&"):
            if item.startswith("v="):
                video_id = item[2:]
                break
        if video_id:
            return sanitize_project_id(f"youtube-{video_id}")
    path_tail = Path(parsed.path).name or host or "url"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return sanitize_project_id(f"{host}-{path_tail}-{digest}")


def determine_input_mode(args: argparse.Namespace) -> str:
    provided = [
        bool(args.input_transcript),
        bool(getattr(args, "input_media", None)),
        bool(getattr(args, "input_url", None)),
    ]
    if sum(provided) != 1:
        raise EndToEndRunnerError("exactly one of --input-transcript, --input-media, or --input-url is required")
    if args.input_transcript:
        return "local_transcript"
    if getattr(args, "input_media", None):
        return "local_media"
    return "platform_url"


def input_identity(args: argparse.Namespace, mode: str) -> str:
    if mode == "local_transcript":
        return str(args.input_transcript.expanduser().resolve())
    if mode == "local_media":
        return str(args.input_media.expanduser().resolve())
    return str(args.input_url)


def hash_payload(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def file_snapshot(path: Path) -> dict[str, Any]:
    target = path.expanduser()
    try:
        resolved = target.resolve(strict=False)
    except OSError:
        resolved = target.absolute()
    if not resolved.is_file():
        return {"path": str(resolved), "exists": False, "bytes": 0, "sha256": ""}
    data = resolved.read_bytes()
    return {
        "path": str(resolved),
        "exists": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def snapshots_hash(snapshots: list[dict[str, Any]], *, extra: dict[str, Any] | None = None) -> str:
    return hash_payload(
        {
            "files": sorted(snapshots, key=lambda item: str(item.get("path") or "")),
            "extra": extra or {},
        }
    )


def command_option_path(command: list[str], option: str) -> Path | None:
    try:
        index = command.index(option)
    except ValueError:
        return None
    value_index = index + 1
    if value_index >= len(command):
        return None
    value = command[value_index]
    if option == "--input" and urlparse(value).scheme in {"http", "https"}:
        return None
    return Path(value).expanduser()


def command_input_paths(command: list[str]) -> list[Path]:
    paths: list[Path] = []
    for option in ("--input", "--input-media", "--asr-jsonl", "--youtube-cookies"):
        path = command_option_path(command, option)
        if path is not None:
            paths.append(path)
    return paths


def resolve_roots(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.project_root:
        project_root = args.project_root.expanduser().resolve()
    else:
        base = args.output_base.expanduser().resolve()
        mode = determine_input_mode(args)
        if mode == "platform_url":
            project_root = base / make_project_id_from_url(str(args.input_url))
        elif mode == "local_media":
            project_root = base / make_project_id_from_path(args.input_media)
        else:
            project_root = base / make_project_id_from_path(args.input_transcript)
    return project_root, project_root / "10_video", project_root / "20_document"


def stage_expected_paths(project_root: Path, stage: str) -> list[Path]:
    return [project_root / item for item in STAGE_OUTPUTS.get(stage, [])]


def stage_resume_output_paths(project_root: Path, stage: str) -> list[Path]:
    return [project_root / item for item in STAGE_RESUME_OUTPUTS.get(stage, STAGE_OUTPUTS.get(stage, []))]


def expected_outputs_exist(project_root: Path, stage: str) -> bool:
    expected = stage_expected_paths(project_root, stage)
    return bool(expected) and all(path.is_file() for path in expected)


def stage_output_snapshots(project_root: Path, stage: str) -> list[dict[str, Any]]:
    return [file_snapshot(path) for path in stage_expected_paths(project_root, stage)]


def stage_input_snapshots(project_root: Path, stage: str, command: list[str]) -> list[dict[str, Any]]:
    paths = [project_root / item for item in STAGE_INPUTS.get(stage, [])]
    paths.extend(command_input_paths(command))
    unique: dict[str, Path] = {}
    for path in paths:
        try:
            key = str(path.expanduser().resolve(strict=False))
        except OSError:
            key = str(path.expanduser().absolute())
        unique[key] = path
    return [file_snapshot(path) for key, path in sorted(unique.items())]


def stage_input_hash(project_root: Path, stage: str, command: list[str]) -> tuple[list[dict[str, Any]], str]:
    snapshots = stage_input_snapshots(project_root, stage, command)
    return snapshots, snapshots_hash(snapshots, extra={"stage": stage, "command": command})


def stage_output_hash(project_root: Path, stage: str) -> tuple[list[dict[str, Any]], str]:
    snapshots = stage_output_snapshots(project_root, stage)
    return snapshots, snapshots_hash(snapshots, extra={"stage": stage})


def stage_resume_output_hash(project_root: Path, stage: str) -> tuple[list[dict[str, Any]], str]:
    snapshots = [file_snapshot(path) for path in stage_resume_output_paths(project_root, stage)]
    return snapshots, snapshots_hash(snapshots, extra={"stage": stage, "resume_outputs": True})


def workflow_input_hash(args: argparse.Namespace, mode: str) -> str:
    snapshots: list[dict[str, Any]] = []
    if mode == "local_transcript" and args.input_transcript:
        snapshots.append(file_snapshot(args.input_transcript))
    elif mode == "local_media" and args.input_media:
        snapshots.append(file_snapshot(args.input_media))
    if getattr(args, "asr_jsonl", None):
        snapshots.append(file_snapshot(args.asr_jsonl))
    return snapshots_hash(
        snapshots,
        extra={
            "mode": mode,
            "input_identity": input_identity(args, mode),
            "input_url": str(getattr(args, "input_url", "") or ""),
        },
    )


def stage_order_index(stage: str) -> int:
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return len(STAGE_ORDER)


def should_force_rerun_from(stage: str, resume_from_stage: str) -> bool:
    if not resume_from_stage:
        return False
    if resume_from_stage not in STAGE_ORDER:
        raise EndToEndRunnerError(f"unknown --resume-from-stage: {resume_from_stage}")
    return stage_order_index(stage) >= stage_order_index(resume_from_stage)


def normalize_resume_from_stage(args: argparse.Namespace) -> str:
    resume_from_stage = str(getattr(args, "resume_from_stage", "") or "")
    resume_after_stage = str(getattr(args, "resume_after_stage", "") or "")
    if resume_from_stage and resume_after_stage:
        raise EndToEndRunnerError("use only one of --resume-from-stage or --resume-after-stage")
    if resume_after_stage:
        if resume_after_stage not in STAGE_ORDER:
            raise EndToEndRunnerError(f"unknown --resume-after-stage: {resume_after_stage}")
        next_index = stage_order_index(resume_after_stage) + 1
        if next_index >= len(STAGE_ORDER):
            raise EndToEndRunnerError(f"--resume-after-stage {resume_after_stage} has no later stage")
        return STAGE_ORDER[next_index]
    return resume_from_stage


def resume_requested(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "resume", False) or normalize_resume_from_stage(args))


def retry_policy_for_stage(stage: str) -> dict[str, Any]:
    return {
        "automatic_retry_allowed": False,
        "resume_from_stage": stage,
        "resume_hint": f"--resume --resume-from-stage {stage}",
        "user_action_required": GUIDANCE_BY_STAGE.get(stage, "Inspect the failed stage outputs and rerun from this stage after fixing the input artifacts."),
    }


def failure_reason_for_stage(stage: str, result: dict[str, Any]) -> str:
    detail = str(result.get("stderr") or result.get("stdout") or "").strip()
    return detail or f"{stage} returned exit code {result.get('returncode')}"


def latest_stage_record(state: dict[str, Any], stage: str) -> dict[str, Any]:
    stages = state.get("stages")
    if not isinstance(stages, list):
        return {}
    for row in reversed(stages):
        if isinstance(row, dict) and row.get("stage") == stage:
            return row
    return {}


def load_run_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return read_json(path)
    except EndToEndRunnerError:
        return {}


def initialize_run_state(
    args: argparse.Namespace,
    project_root: Path,
    video_root: Path,
    document_root: Path,
    mode: str,
) -> dict[str, Any]:
    return {
        "runner": RUNNER_NAME,
        "schema_version": RUN_STATE_SCHEMA_VERSION,
        "mode": mode,
        "status": "running",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "project_root": str(project_root),
        "video_root": str(video_root),
        "document_root": str(document_root),
        "input_transcript": str(args.input_transcript.expanduser().resolve()) if args.input_transcript else "",
        "input_media": str(args.input_media.expanduser().resolve()) if getattr(args, "input_media", None) else "",
        "input_url": str(getattr(args, "input_url", "") or ""),
        "input_identity": input_identity(args, mode),
        "input_hash": workflow_input_hash(args, mode),
        "resume_enabled": resume_requested(args),
        "resume_from_stage": normalize_resume_from_stage(args),
        "resume_after_stage": str(getattr(args, "resume_after_stage", "") or ""),
        "resume_policy": "stage_input_hash_output_hash_and_expected_outputs",
        "current_stage": "",
        "next_stage": "platform_media_runner" if mode == "platform_url" else ("asr_pipeline" if mode == "local_media" else "transcript_normalizer"),
        "stages": [],
    }


def validate_resume_state(state: dict[str, Any], args: argparse.Namespace, project_root: Path, mode: str) -> None:
    if not state:
        return
    previous_project = str(state.get("project_root") or "")
    if previous_project and Path(previous_project).expanduser().resolve() != project_root.expanduser().resolve():
        raise EndToEndRunnerError("run_state project_root does not match the requested project root")
    previous_mode = str(state.get("mode") or "")
    if previous_mode and previous_mode != mode:
        raise EndToEndRunnerError("run_state mode does not match the requested input mode")
    previous_input = str(state.get("input_identity") or state.get("input_transcript") or state.get("input_media") or state.get("input_url") or "")
    current_input = input_identity(args, mode)
    if previous_input and previous_input != current_input:
        raise EndToEndRunnerError("run_state input does not match the requested input")
    previous_hash = str(state.get("input_hash") or "")
    current_hash = workflow_input_hash(args, mode)
    if previous_hash and previous_hash != current_hash:
        raise EndToEndRunnerError("run_state input hash does not match the requested input")


def state_stage_index(state: dict[str, Any], stage: str) -> int | None:
    stages = state.get("stages")
    if not isinstance(stages, list):
        return None
    for index, row in enumerate(stages):
        if isinstance(row, dict) and row.get("stage") == stage:
            return index
    return None


def upsert_stage(state: dict[str, Any], stage_record: dict[str, Any]) -> None:
    stages = state.setdefault("stages", [])
    if not isinstance(stages, list):
        state["stages"] = stages = []
    history = state.setdefault("stage_history", [])
    if not isinstance(history, list):
        state["stage_history"] = history = []
    index = state_stage_index(state, str(stage_record.get("stage")))
    if index is None:
        stages.append(stage_record)
    else:
        stages[index] = stage_record
    history.append(stage_record)
    state["updated_at"] = now_iso()


def write_run_state(path: Path, state: dict[str, Any]) -> None:
    write_json(path, state)


def completed_in_state(state: dict[str, Any], stage: str) -> bool:
    row = latest_stage_record(state, stage)
    return row.get("status") in {"completed", "skipped"}


def stage_record_from_result(
    result: dict[str, Any],
    status: str,
    *,
    input_files: list[dict[str, Any]],
    input_hash: str,
    output_files: list[dict[str, Any]],
    output_hash: str,
    resume_output_files: list[dict[str, Any]],
    resume_output_hash: str,
    resume_decision: str,
) -> dict[str, Any]:
    record = stage_summary(result)
    record.update(
        {
            "status": status,
            "command": result.get("command", []),
            "input_files": input_files,
            "input_hash": input_hash,
            "output_files": output_files,
            "output_hash": output_hash,
            "resume_output_files": resume_output_files,
            "resume_output_hash": resume_output_hash,
            "resume_decision": resume_decision,
            "completed_at": now_iso() if status == "completed" else "",
            "failed_at": now_iso() if status == "failed" else "",
            "stderr": result.get("stderr", ""),
            "failure_reason": failure_reason_for_stage(str(result.get("stage") or ""), result) if status == "failed" else "",
            "skipped_reason": "",
            "retry_policy": retry_policy_for_stage(str(result.get("stage") or "")),
        }
    )
    return record


def ensure_no_final_report(document_root: Path) -> None:
    if (document_root / "final_report.md").exists():
        raise EndToEndRunnerError("document runner unexpectedly left final_report.md in place")


def first_existing_file(paths: list[str]) -> Path | None:
    for item in paths:
        path = Path(item).expanduser()
        if path.is_file() and path.stat().st_size > 0:
            return path.resolve()
    return None


def render_degraded_report(*, input_value: str, mode: str, source_status: dict[str, Any], platform_result: dict[str, Any] | None) -> str:
    lines = [
        "# Degraded Acquisition Report",
        "",
        f"- Input mode: `{mode}`",
        f"- Input: `{input_value}`",
        f"- Source status: `{source_status.get('source_status', 'unknown')}`",
        f"- Primary material available: `{str(bool(source_status.get('primary_material_available'))).lower()}`",
        f"- Full decomposition allowed: `{str(bool(source_status.get('can_enter_full_decomposition'))).lower()}`",
        f"- Next step: `{source_status.get('next_step', '')}`",
        "",
        "## Reason",
        "",
        str(source_status.get("status_reason") or "No primary transcript or ASR-ready transcript was produced."),
        "",
        "## Boundary",
        "",
        "This report is an acquisition/degraded report only. It is not a video analysis pack, speaker logic reconstruction, or complete source-faithful content analysis.",
        "",
    ]
    if platform_result:
        lines.extend(
            [
                "## Platform Material State",
                "",
                f"- Material state: `{platform_result.get('material_state') or platform_result.get('decision', {}).get('material_state', '')}`",
                f"- Acquired subtitles: `{len(platform_result.get('acquired_subtitle_files') or [])}`",
                f"- Acquired audio files: `{len(platform_result.get('acquired_audio_files') or [])}`",
                "",
            ]
        )
    return "\n".join(lines)


def run_workflow(args: argparse.Namespace) -> dict[str, Any]:
    mode = determine_input_mode(args)
    video_skill_root = args.video_skill_root.expanduser().resolve()
    document_skill_root = args.document_skill_root.expanduser().resolve()
    project_root, video_root, document_root = resolve_roots(args)
    logs_root = project_root / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    run_state_path = logs_root / "run_state.json"
    resume_active = resume_requested(args)
    previous_state = load_run_state(run_state_path) if resume_active else {}
    if resume_active:
        validate_resume_state(previous_state, args, project_root, mode)
    state = initialize_run_state(args, project_root, video_root, document_root, mode)
    if resume_active and previous_state:
        state["created_at"] = previous_state.get("created_at") or state["created_at"]
        state["stages"] = previous_state.get("stages") if isinstance(previous_state.get("stages"), list) else []
        state["stage_history"] = previous_state.get("stage_history") if isinstance(previous_state.get("stage_history"), list) else []
    write_run_state(run_state_path, state)

    def run_stage(stage: str, command: list[str], cwd: Path) -> None:
        input_files, input_hash = stage_input_hash(project_root, stage, command)
        current_output_files, current_output_hash = stage_output_hash(project_root, stage)
        current_resume_output_files, current_resume_output_hash = stage_resume_output_hash(project_root, stage)
        previous_record = latest_stage_record(state, stage)
        effective_resume_from_stage = normalize_resume_from_stage(args)
        force_rerun = should_force_rerun_from(stage, effective_resume_from_stage)
        can_skip = (
            resume_active
            and not force_rerun
            and completed_in_state(state, stage)
            and expected_outputs_exist(project_root, stage)
            and previous_record.get("input_hash") == input_hash
            and previous_record.get("resume_output_hash", previous_record.get("output_hash")) == current_resume_output_hash
        )
        if can_skip:
            skipped = {
                "stage": stage,
                "returncode": 0,
                "summary": {
                    "runner": RUNNER_NAME,
                    "next_step": "resume_skipped_completed_stage",
                },
                "command": command,
                "stdout": "",
                "stderr": "",
            }
            steps.append(skipped)
            upsert_stage(
                state,
                {
                    "stage": stage,
                    "status": "skipped",
                    "returncode": 0,
                    "command": command,
                    "input_files": input_files,
                    "input_hash": input_hash,
                    "output_files": current_output_files,
                    "output_hash": current_output_hash,
                    "resume_output_files": current_resume_output_files,
                    "resume_output_hash": current_resume_output_hash,
                    "skipped_at": now_iso(),
                    "reason": "resume_completed_hashes_and_outputs_present",
                    "skipped_reason": "resume_completed_hashes_and_outputs_present",
                    "resume_decision": "skipped_completed_hashes_and_outputs_present",
                    "failure_reason": "",
                    "stderr": "",
                    "retry_policy": retry_policy_for_stage(stage),
                },
            )
            state["current_stage"] = stage
            state["next_stage"] = "next"
            write_run_state(run_state_path, state)
            write_json(logs_root / "end_to_end_steps.json", [stage_summary(step) for step in steps])
            return
        rerun_reason = "fresh_run"
        if resume_active:
            if force_rerun:
                rerun_reason = f"forced_from_stage:{effective_resume_from_stage}"
            elif not completed_in_state(state, stage):
                rerun_reason = "no_completed_stage_record"
            elif not expected_outputs_exist(project_root, stage):
                rerun_reason = "expected_outputs_missing"
            elif previous_record.get("input_hash") != input_hash:
                rerun_reason = "stage_input_hash_changed"
            elif previous_record.get("resume_output_hash", previous_record.get("output_hash")) != current_resume_output_hash:
                rerun_reason = "stage_output_hash_changed"
        upsert_stage(
            state,
            {
                "stage": stage,
                "status": "running",
                "returncode": None,
                "command": command,
                "input_files": input_files,
                "input_hash": input_hash,
                "output_files": current_output_files,
                "output_hash": current_output_hash,
                "resume_output_files": current_resume_output_files,
                "resume_output_hash": current_resume_output_hash,
                "resume_decision": rerun_reason,
                "started_at": now_iso(),
                "retry_policy": retry_policy_for_stage(stage),
            },
        )
        state["current_stage"] = stage
        state["next_stage"] = stage
        write_run_state(run_state_path, state)
        result = run_command(stage, command, cwd)
        steps.append(result)
        write_json(logs_root / "end_to_end_steps.json", [stage_summary(step) for step in steps])
        output_files, output_hash = stage_output_hash(project_root, stage)
        resume_output_files, resume_output_hash = stage_resume_output_hash(project_root, stage)
        if result["returncode"] != 0:
            upsert_stage(
                state,
                stage_record_from_result(
                    result,
                    "failed",
                    input_files=input_files,
                    input_hash=input_hash,
                    output_files=output_files,
                    output_hash=output_hash,
                    resume_output_files=resume_output_files,
                    resume_output_hash=resume_output_hash,
                    resume_decision=rerun_reason,
                ),
            )
            state["status"] = "failed"
            state["failed_stage"] = stage
            state["error"] = result.get("stderr") or result.get("stdout")
            state["failure_reason"] = failure_reason_for_stage(stage, result)
            state["user_action_required"] = retry_policy_for_stage(stage)["user_action_required"]
            state["next_stage"] = stage
            write_run_state(run_state_path, state)
            raise EndToEndRunnerError(
                f"stage {stage} failed with exit code {result['returncode']}: {result.get('stderr') or result.get('stdout')}"
            )
        upsert_stage(
            state,
            stage_record_from_result(
                result,
                "completed",
                input_files=input_files,
                input_hash=input_hash,
                output_files=output_files,
                output_hash=output_hash,
                resume_output_files=resume_output_files,
                resume_output_hash=resume_output_hash,
                resume_decision=rerun_reason,
            ),
        )
        state["next_stage"] = "next"
        write_run_state(run_state_path, state)

    video_scripts = video_skill_root / "scripts"
    document_scripts = document_skill_root / "scripts"
    py = sys.executable

    if mode == "platform_url":
        platform_command = [
            py,
            str(script_path(video_skill_root, "platform_media_runner.py")),
            "--input",
            str(args.input_url),
            "--output-root",
            str(video_root),
            "--mode",
            args.platform_mode,
            "--timeout-seconds",
            str(args.platform_timeout_seconds),
            "--subtitle-languages",
            args.subtitle_languages,
        ]
        if args.youtube_cookies:
            platform_command.extend(["--youtube-cookies", args.youtube_cookies])
        if args.ytdlp:
            platform_command.extend(["--ytdlp", args.ytdlp])
        if args.node:
            platform_command.extend(["--node", args.node])
        if args.no_doctor:
            platform_command.append("--no-doctor")
        if args.use_js_runtime:
            platform_command.append("--use-js-runtime")
        if args.use_remote_components:
            platform_command.append("--use-remote-components")
        run_stage("platform_media_runner", platform_command, video_scripts)
        platform_result = read_json(video_root / "00_source" / "platform_media_result.json")
        subtitle_file = first_existing_file(list(platform_result.get("acquired_subtitle_files") or []))
        audio_file = first_existing_file(list(platform_result.get("acquired_audio_files") or []))
        if subtitle_file:
            state["route_decision"] = "normalize_acquired_subtitle"
            write_run_state(run_state_path, state)
            run_stage(
                "transcript_normalizer",
                [
                    py,
                    str(script_path(video_skill_root, "transcript_normalizer.py")),
                    "--input",
                    str(subtitle_file),
                    "--output-root",
                    str(video_root),
                    "--language",
                    args.language,
                ],
                video_scripts,
            )
        elif audio_file:
            state["route_decision"] = "run_asr_on_acquired_audio"
            write_run_state(run_state_path, state)
            asr_command = [
                py,
                str(script_path(video_skill_root, "asr_pipeline.py")),
                "--input-media",
                str(audio_file),
                "--output-root",
                str(video_root),
                "--model",
                args.asr_model,
                "--language",
                args.language if args.language != "unknown" else "",
                "--device",
                args.asr_device,
                "--compute-type",
                args.asr_compute_type,
                "--timeout-seconds",
                str(args.asr_timeout_seconds),
                "--vad" if args.asr_vad else "--no-vad",
            ]
            if args.asr_python:
                asr_command.extend(["--asr-python", args.asr_python])
            if args.asr_jsonl:
                asr_command.extend(["--asr-jsonl", str(args.asr_jsonl.expanduser().resolve())])
            run_stage("asr_pipeline", [item for item in asr_command if item != ""], video_scripts)
        else:
            source_status = read_json(video_root / "00_source" / "source_status.json")
            degraded = write_text(
                video_root / "00_source" / "degraded_acquisition_report.md",
                render_degraded_report(
                    input_value=str(args.input_url),
                    mode=mode,
                    source_status=source_status,
                    platform_result=platform_result,
                ),
            )
            state["status"] = "completed"
            state["workflow_outcome"] = "degraded_acquisition_only"
            state["route_decision"] = "stop_without_primary_material"
            state["degraded_reason"] = source_status.get("status_reason") or "No primary transcript or ASR-ready media was acquired."
            state["user_action_required"] = (
                "Provide one of: an official subtitle/transcript file, a local audio/video file for ASR, "
                "a browser-derived media/subtitle export, or platform access material such as a user-exported cookies.txt."
            )
            state["current_stage"] = "platform_media_runner"
            state["next_stage"] = source_status.get("next_step") or "request_primary_material"
            state["completed_at"] = now_iso()
            write_run_state(run_state_path, state)
            summary = {
                "runner": RUNNER_NAME,
                "mode": mode,
                "workflow_outcome": "degraded_acquisition_only",
                "generated_at": now_iso(),
                "project_root": str(project_root),
                "video_root": str(video_root),
                "document_root": str(document_root),
                "steps": [stage_summary(step) for step in steps],
                "source_status": source_status.get("source_status"),
                "can_enter_full_decomposition": False,
                "video_analysis_pack": "",
                "composer_intake": "",
                "final_report_written": False,
                "degraded_report": degraded["path"],
                "run_state": str(run_state_path),
                "resume_enabled": resume_active,
                "next_step": source_status.get("next_step") or "request_primary_material",
            }
            write_json(logs_root / "end_to_end_summary.json", summary)
            return summary
    elif mode == "local_media":
        asr_command = [
            py,
            str(script_path(video_skill_root, "asr_pipeline.py")),
            "--input-media",
            str(args.input_media.expanduser().resolve()),
            "--output-root",
            str(video_root),
            "--model",
            args.asr_model,
            "--language",
            args.language if args.language != "unknown" else "",
            "--device",
            args.asr_device,
            "--compute-type",
            args.asr_compute_type,
            "--timeout-seconds",
            str(args.asr_timeout_seconds),
            "--vad" if args.asr_vad else "--no-vad",
        ]
        if args.asr_python:
            asr_command.extend(["--asr-python", args.asr_python])
        if args.asr_jsonl:
            asr_command.extend(["--asr-jsonl", str(args.asr_jsonl.expanduser().resolve())])
        run_stage("asr_pipeline", [item for item in asr_command if item != ""], video_scripts)
    else:
        run_stage(
            "transcript_normalizer",
            [
                py,
                str(script_path(video_skill_root, "transcript_normalizer.py")),
                "--input",
                str(args.input_transcript.expanduser().resolve()),
                "--output-root",
                str(video_root),
                "--language",
                args.language,
            ],
            video_scripts,
        )

    for stage, command in [
        (
            "transcript_segmenter",
            [py, str(script_path(video_skill_root, "transcript_segmenter.py")), "--output-root", str(video_root)],
        ),
        (
            "inventory_extractor",
            [py, str(script_path(video_skill_root, "inventory_extractor.py")), "--output-root", str(video_root)],
        ),
        (
            "source_logic_builder",
            [py, str(script_path(video_skill_root, "source_logic_builder.py")), "--output-root", str(video_root)],
        ),
        (
            "evidence_auditor",
            [py, str(script_path(video_skill_root, "evidence_auditor.py")), "--output-root", str(video_root)],
        ),
        (
            "video_analysis_pack_builder",
            [py, str(script_path(video_skill_root, "video_analysis_pack_builder.py")), "--output-root", str(video_root)],
        ),
    ]:
        run_stage(stage, command, video_scripts)

    run_stage(
        "document_composer_runner",
        [
            py,
            str(script_path(document_skill_root, "document_composer_runner.py")),
            "--video-root",
            str(video_root),
            "--document-root",
            str(document_root),
            "--document-goal",
            args.document_goal,
            "--final-language",
            args.final_language,
            "--audience",
            args.audience,
        ],
        document_scripts,
    )
    ensure_no_final_report(document_root)
    state["status"] = "completed"
    state["current_stage"] = "document_composer_runner"
    state["next_stage"] = "draft_report_with_quality_gates"
    state["completed_at"] = now_iso()
    write_run_state(run_state_path, state)

    summary = {
        "runner": RUNNER_NAME,
        "mode": mode,
        "workflow_outcome": "analysis_pack_and_document_planning",
        "generated_at": now_iso(),
        "project_root": str(project_root),
        "video_root": str(video_root),
        "document_root": str(document_root),
        "steps": [stage_summary(step) for step in steps],
        "video_analysis_pack": str(video_root / "video_analysis_pack.md"),
        "composer_intake": str(document_root / "composer_intake.json"),
        "final_report_written": False,
        "run_state": str(run_state_path),
        "resume_enabled": resume_active,
        "next_step": "draft_report_with_quality_gates",
    }
    write_json(logs_root / "end_to_end_summary.json", summary)
    return summary


def run_local_transcript_workflow(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_transcript is None:
        raise EndToEndRunnerError("--input-transcript is required for local-transcript mode")
    return run_workflow(args)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run transcript, media, or URL input through the knowledge workflow.")
    parser.add_argument("--input-transcript", type=Path, default=None, help="Local transcript/subtitle file.")
    parser.add_argument("--input-media", type=Path, default=None, help="Local audio/video file for ASR.")
    parser.add_argument("--input-url", default=None, help="Platform video URL.")
    parser.add_argument("--project-root", type=Path, default=None, help="Project root containing 10_video and 20_document.")
    parser.add_argument("--output-base", type=Path, default=Path("outputs") / "knowledge-workflow", help="Base output directory when project-root is omitted.")
    parser.add_argument("--language", default="unknown", help="Transcript language label.")
    parser.add_argument("--document-goal", default="source-faithful knowledge report", help="Document goal passed to document composer.")
    parser.add_argument("--final-language", default="current conversation language", help="Final report language instruction.")
    parser.add_argument("--audience", default="reader who needs an auditable source-faithful explanation", help="Intended audience.")
    parser.add_argument("--video-skill-root", type=Path, default=default_skill_root("knowledge-video-decomposer"), help="knowledge-video-decomposer skill root.")
    parser.add_argument("--document-skill-root", type=Path, default=default_skill_root("knowledge-document-composer"), help="knowledge-document-composer skill root.")
    parser.add_argument("--platform-mode", choices=["auto", "probe", "subtitles", "audio"], default="auto", help="Platform media acquisition mode for URL input.")
    parser.add_argument("--youtube-cookies", default=None, help="Path to user-exported Netscape cookies.txt.")
    parser.add_argument("--ytdlp", default=None, help="Optional yt-dlp executable override.")
    parser.add_argument("--node", default=None, help="Optional Node.js executable override.")
    parser.add_argument("--platform-timeout-seconds", type=int, default=90, help="Timeout for platform acquisition commands.")
    parser.add_argument("--no-doctor", action="store_true", help="Skip doctor during platform acquisition.")
    parser.add_argument("--use-js-runtime", action="store_true", help="Pass Node.js to yt-dlp through platform media runner.")
    parser.add_argument("--use-remote-components", action="store_true", help="Allow yt-dlp remote solver components through platform media runner.")
    parser.add_argument("--subtitle-languages", default="all,-live_chat", help="Subtitle language selector for platform media runner.")
    parser.add_argument("--asr-jsonl", type=Path, default=None, help="Existing ASR JSONL to normalize instead of running ASR.")
    parser.add_argument("--asr-python", default=None, help="Python runtime for faster-whisper.")
    parser.add_argument("--asr-model", default="base", help="faster-whisper model name or local path.")
    parser.add_argument("--asr-device", default="cpu", help="faster-whisper device.")
    parser.add_argument("--asr-compute-type", default="int8", help="faster-whisper compute type.")
    parser.add_argument("--asr-timeout-seconds", type=float, default=0.0, help="Soft ASR timeout seconds.")
    parser.add_argument("--no-vad", dest="asr_vad", action="store_false", help="Disable VAD filtering for ASR.")
    parser.set_defaults(asr_vad=True)
    parser.add_argument("--resume", action="store_true", help="Resume a previous transcript, media, or URL run by skipping completed stages whose expected outputs still exist.")
    parser.add_argument(
        "--resume-from-stage",
        choices=STAGE_ORDER,
        default="",
        help="Resume a previous run but rerun this stage and every later stage. Earlier stages may still be skipped when their hashes and outputs match.",
    )
    parser.add_argument(
        "--resume-after-stage",
        choices=STAGE_ORDER,
        default="",
        help="Resume a previous run after this stage by rerunning the next stage and every later stage. Earlier stages may still be skipped when their hashes and outputs match.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def assert_stage_state_fields(state: dict[str, Any], failures: list[str]) -> None:
    stages = state.get("stages")
    assert_true("run state stages list", isinstance(stages, list) and bool(stages), failures)
    if not isinstance(stages, list):
        return
    required = ("input_hash", "output_files", "output_hash", "status", "retry_policy")
    for row in stages:
        if not isinstance(row, dict):
            failures.append("run state stage row: expected object")
            continue
        missing = [key for key in required if key not in row]
        assert_true(
            f"stage state fields {row.get('stage')}",
            not missing,
            failures,
            ",".join(missing),
        )


def write_fixture_transcript(path: Path) -> None:
    write_text(
        path,
        "\n\n".join(
            [
                "Source Gate means confirmed primary material.",
                "For example, metadata alone cannot support speaker logic.",
                "Therefore we must preserve transcript evidence before writing reports.",
                "This creates a workflow where claims remain tied to their source.",
            ]
        )
        + "\n",
    )


def write_fake_skill_scripts(base: Path) -> tuple[Path, Path]:
    video_root = base / "fake_video_skill"
    document_root = base / "fake_document_skill"
    video_scripts = video_root / "scripts"
    document_scripts = document_root / "scripts"
    video_scripts.mkdir(parents=True, exist_ok=True)
    document_scripts.mkdir(parents=True, exist_ok=True)

    common = r'''
import argparse, json
from pathlib import Path

def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")

def write_json(path, payload):
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

def emit(payload):
    print(json.dumps(payload, ensure_ascii=False))
'''

    write_text(
        video_scripts / "platform_media_runner.py",
        common
        + r'''
p = argparse.ArgumentParser()
p.add_argument("--input", required=True)
p.add_argument("--output-root", type=Path, required=True)
p.add_argument("--mode", default="auto")
p.add_argument("--timeout-seconds", default="1")
p.add_argument("--subtitle-languages", default="all")
p.add_argument("--youtube-cookies", default=None)
p.add_argument("--ytdlp", default=None)
p.add_argument("--node", default=None)
p.add_argument("--no-doctor", action="store_true")
p.add_argument("--use-js-runtime", action="store_true")
p.add_argument("--use-remote-components", action="store_true")
args = p.parse_args()
root = args.output_root
source_status = {
    "source_status": "secondary_only",
    "can_enter_full_decomposition": False,
    "can_enter_document_composer": True,
    "allowed_report_type": "degraded_source_report",
    "source_classes": ["platform_metadata"],
    "primary_material_available": False,
    "status_reason": "fake metadata only",
    "failed_probes": [],
    "next_step": "request_primary_material",
}
subtitles = []
audio = []
material_state = "no_primary_material_acquired"
if "subtitle" in args.input:
    sub = root / "00_source" / "raw" / "subtitles" / "fake.srt"
    write_text(sub, "1\n00:00:00,000 --> 00:00:02,000\nFake subtitle text.\n")
    subtitles = [str(sub.resolve())]
    source_status.update({
        "source_status": "source_confirmed",
        "can_enter_full_decomposition": True,
        "can_enter_document_composer": True,
        "allowed_report_type": "full_video_analysis_pack",
        "source_classes": ["primary_transcript"],
        "primary_material_available": True,
        "status_reason": "fake subtitle acquired",
        "next_step": "normalize_acquired_subtitle",
    })
    material_state = "subtitle_acquired"
elif "audio" in args.input:
    media = root / "00_source" / "raw" / "audio" / "fake.mp3"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake audio")
    audio = [str(media.resolve())]
    source_status.update({
        "status_reason": "fake audio acquired pending ASR",
        "next_step": "run_asr_pipeline_on_acquired_audio",
        "pending_primary_media_for_asr": audio,
    })
    material_state = "audio_acquired_pending_asr"
elif "blocked" in args.input:
    source_status.update({
        "source_status": "source_blocked",
        "allowed_report_type": "acquisition_failure_report",
        "can_enter_document_composer": True,
        "source_classes": [],
        "status_reason": "fake platform block",
        "next_step": "request_primary_material",
    })
write_json(root / "00_source" / "source_status.json", source_status)
result = {
    "runner": "fake-platform-media-runner",
    "input": args.input,
    "source_status": source_status,
    "acquired_subtitle_files": subtitles,
    "acquired_audio_files": audio,
    "decision": {"material_state": material_state, "next_step": source_status["next_step"]},
    "material_state": material_state,
}
write_json(root / "00_source" / "platform_media_result.json", result)
write_text(root / "00_source" / "platform_media_notes.md", "# Fake Platform Media Notes\n")
emit({"runner": "fake-platform-media-runner", "source_status": source_status["source_status"], "material_state": material_state, "acquired_subtitle_files": subtitles, "acquired_audio_files": audio, "next_step": source_status["next_step"]})
''',
    )

    write_text(
        video_scripts / "transcript_normalizer.py",
        common
        + r'''
p = argparse.ArgumentParser()
p.add_argument("--input", required=True)
p.add_argument("--output-root", type=Path, required=True)
p.add_argument("--language", default="unknown")
args = p.parse_args()
root = args.output_root
status = {
    "source_status": "source_confirmed",
    "can_enter_full_decomposition": True,
    "can_enter_document_composer": True,
    "allowed_report_type": "full_video_analysis_pack",
    "source_classes": ["primary_transcript"],
    "primary_material_available": True,
    "status_reason": "fake normalized transcript",
    "failed_probes": [],
    "next_step": "enter_segmentation_inventory_logic_gap_check",
}
write_json(root / "00_source" / "source_status.json", status)
write_text(root / "01_transcript" / "clean_transcript.jsonl", json.dumps({"id":"t001","text":"Fake transcript text.","normalized_text":"Fake transcript text.","source_ids":["raw_001"],"language":args.language}, ensure_ascii=False) + "\n")
write_text(root / "01_transcript" / "clean_transcript.md", "# Clean Transcript\n\nFake transcript text.\n")
emit({"runner": "fake-transcript-normalizer", "source_status": "source_confirmed", "next_step": "enter_segmentation_inventory_logic_gap_check"})
''',
    )

    write_text(
        video_scripts / "asr_pipeline.py",
        common
        + r'''
p = argparse.ArgumentParser()
p.add_argument("--input-media", type=Path, required=True)
p.add_argument("--output-root", type=Path, required=True)
p.add_argument("--model", default="base")
p.add_argument("--language", default=None)
p.add_argument("--device", default="cpu")
p.add_argument("--compute-type", default="int8")
p.add_argument("--timeout-seconds", default="0")
p.add_argument("--asr-python", default=None)
p.add_argument("--asr-jsonl", default=None)
p.add_argument("--vad", action="store_true")
p.add_argument("--no-vad", action="store_true")
args = p.parse_args()
root = args.output_root
status = {
    "source_status": "source_confirmed",
    "can_enter_full_decomposition": True,
    "can_enter_document_composer": True,
    "allowed_report_type": "full_video_analysis_pack",
    "source_classes": ["primary_audio_asr"],
    "primary_material_available": True,
    "status_reason": "fake ASR transcript",
    "failed_probes": [],
    "next_step": "enter_segmentation_inventory_logic_gap_check",
}
write_json(root / "00_source" / "source_status.json", status)
write_json(root / "00_source" / "asr_pipeline_report.json", {"runner":"fake-asr-pipeline","input_media":str(args.input_media),"quality":{"verified_verbatim":False,"word_timestamp_coverage":0.0,"speaker_coverage":0.0}})
write_json(root / "00_source" / "asr_alignment_report.json", {"schema_version":1,"status":"segment_only","word_timestamp_coverage":0.0})
write_json(root / "00_source" / "asr_diarization.json", {"schema_version":1,"status":"not_available","speaker_coverage":0.0})
write_text(root / "01_transcript" / "clean_transcript.jsonl", json.dumps({"id":"t001","text":"Fake ASR text.","normalized_text":"Fake ASR text.","source_ids":["asr_001"],"language":args.language or "unknown"}, ensure_ascii=False) + "\n")
write_text(root / "01_transcript" / "clean_transcript.md", "# Clean Transcript\n\nFake ASR text.\n")
emit({"runner": "fake-asr-pipeline", "source_status": "source_confirmed", "source_class": "primary_audio_asr", "next_step": "enter_segmentation_inventory_logic_gap_check"})
''',
    )

    write_text(
        video_scripts / "transcript_segmenter.py",
        common
        + r'''
p = argparse.ArgumentParser(); p.add_argument("--output-root", type=Path, required=True); args = p.parse_args(); root = args.output_root
write_json(root / "02_segments" / "subtitle_segments.json", {"segments":[{"id":"seg_subtitle_001","transcript_ids":["t001"],"lines":["Fake text."],"text":"Fake text.","segmentation_confidence":"high"}]})
write_json(root / "02_segments" / "syntax_segments.json", {"segments":[{"id":"seg_syntax_001","transcript_ids":["t001"],"text":"Fake text."}]})
write_json(root / "02_segments" / "argument_segments.json", {"segments":[{"id":"seg_argument_001","role":"opening","transcript_ids":["t001"],"source_subtitle_segment_ids":["seg_subtitle_001"],"evidence_spans":[{"transcript_ids":["t001"],"quote":"Fake text.","source":"clean_transcript"}]}]})
emit({"runner":"fake-transcript-segmenter","next_step":"enter_inventory_extractor"})
''',
    )
    write_text(
        video_scripts / "inventory_extractor.py",
        common
        + r'''
p = argparse.ArgumentParser(); p.add_argument("--output-root", type=Path, required=True); args = p.parse_args(); root = args.output_root
span = [{"transcript_ids":["t001"],"quote":"Fake text.","source":"clean_transcript"}]
write_json(root / "03_inventory" / "claims.json", {"claims":[{"id":"claim_001","text":"Fake claim.","claim_type":"source_claim","evidence_spans":span}]})
write_json(root / "03_inventory" / "examples.json", {"examples":[]})
write_json(root / "03_inventory" / "concepts.json", {"concepts":[]})
write_json(root / "03_inventory" / "analogies.json", {"analogies":[]})
emit({"runner":"fake-inventory-extractor","next_step":"enter_source_logic_builder"})
''',
    )
    write_text(
        video_scripts / "source_logic_builder.py",
        common
        + r'''
p = argparse.ArgumentParser(); p.add_argument("--output-root", type=Path, required=True); args = p.parse_args(); root = args.output_root
span = [{"transcript_ids":["t001"],"quote":"Fake text.","source":"clean_transcript"}]
write_text(root / "04_logic" / "source_logic.md", "# Source Logic\n\nFake source logic.\n")
write_json(root / "04_logic" / "logic_graph.json", {"nodes":[{"id":"claim_001","type":"claim","evidence_spans":span}],"edges":[]})
emit({"runner":"fake-source-logic-builder","next_step":"enter_evidence_auditor"})
''',
    )
    write_text(
        video_scripts / "evidence_auditor.py",
        common
        + r'''
p = argparse.ArgumentParser(); p.add_argument("--output-root", type=Path, required=True); args = p.parse_args(); root = args.output_root
write_json(root / "05_gap_check" / "evidence_audit.json", {"runner":"fake-evidence-auditor","source_status":"source_confirmed","severity_counts":{"error":0,"warning":0,"info":0},"findings":[],"pack_gate":{"can_build_video_analysis_pack":True,"can_build_partial_pack":False,"next_step":"enter_video_analysis_pack_builder"}})
write_text(root / "05_gap_check" / "gap_check.md", "# Gap Check\n")
emit({"runner":"fake-evidence-auditor","validation_next_step":"enter_video_analysis_pack_builder"})
''',
    )
    write_text(
        video_scripts / "video_analysis_pack_builder.py",
        common
        + r'''
p = argparse.ArgumentParser(); p.add_argument("--output-root", type=Path, required=True); args = p.parse_args(); root = args.output_root
write_text(root / "video_analysis_pack.md", "# Video Analysis Pack\n\nFake pack.\n")
emit({"runner":"fake-video-analysis-pack-builder","pack_path":str((root / "video_analysis_pack.md").resolve()),"next_step":"enter_document_composer"})
''',
    )
    write_text(
        document_scripts / "document_composer_runner.py",
        common
        + r'''
p = argparse.ArgumentParser()
p.add_argument("--video-root", type=Path, required=True)
p.add_argument("--document-root", type=Path, required=True)
p.add_argument("--document-goal", default="")
p.add_argument("--final-language", default="")
p.add_argument("--audience", default="")
args = p.parse_args()
root = args.document_root
write_json(root / "composer_intake.json", {"composer_decision":"full","video_root":str(args.video_root)})
write_text(root / "commitments.md", "# Commitments\n")
write_text(root / "source_reconstruction.md", "# Source Reconstruction\n")
write_json(root / "claim_map.json", {"claims":[]})
write_text(root / "expansion_plan.md", "# Expansion Plan\n")
write_text(root / "report_outline.md", "# Report Outline\n")
write_text(root / "quality_check.md", "# Quality Check\n")
emit({"runner":"fake-document-composer-runner","composer_decision":"full","final_report_written":False,"document_root":str(root.resolve()),"next_step":"draft_report_with_quality_gates"})
''',
    )
    return video_root, document_root


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="knowledge-e2e-") as tmp:
        base = Path(tmp)
        transcript = base / "fixture.txt"
        project_root = base / "project"
        write_fixture_transcript(transcript)
        args = argparse.Namespace(
            input_transcript=transcript,
            project_root=project_root,
            output_base=base / "outputs",
            language="en",
            document_goal="Write an auditable source-faithful report",
            final_language="zh-CN",
            audience="workflow reviewer",
            video_skill_root=default_skill_root("knowledge-video-decomposer"),
            document_skill_root=default_skill_root("knowledge-document-composer"),
            resume=False,
        )
        result = run_local_transcript_workflow(args)
        assert_true("project root", Path(result["project_root"]).is_dir(), failures)
        assert_true("video pack exists", (project_root / "10_video" / "video_analysis_pack.md").is_file(), failures)
        assert_true("composer intake exists", (project_root / "20_document" / "composer_intake.json").is_file(), failures)
        assert_true("final not written", not (project_root / "20_document" / "final_report.md").exists(), failures)
        assert_true("seven steps", len(result["steps"]) == 7, failures)
        intake = read_json(project_root / "20_document" / "composer_intake.json")
        assert_true("composer full decision", intake.get("composer_decision") == "full", failures)
        audit = read_json(project_root / "10_video" / "05_gap_check" / "evidence_audit.json")
        assert_true("audit no errors", audit.get("severity_counts", {}).get("error") == 0, failures)
        run_state = read_json(project_root / "logs" / "run_state.json")
        assert_true("run state completed", run_state.get("status") == "completed", failures)
        assert_true("run state schema v2", run_state.get("schema_version") == RUN_STATE_SCHEMA_VERSION, failures)
        assert_true("workflow input hash", bool(run_state.get("input_hash")), failures)
        assert_true("stage history records attempts", len(run_state.get("stage_history", [])) >= len(run_state.get("stages", [])), failures)
        assert_stage_state_fields(run_state, failures)

        resume_result = run_local_transcript_workflow(
            argparse.Namespace(
                input_transcript=transcript,
                project_root=project_root,
                output_base=base / "outputs",
                language="en",
                document_goal="Write an auditable source-faithful report",
                final_language="zh-CN",
                audience="workflow reviewer",
                video_skill_root=default_skill_root("knowledge-video-decomposer"),
                document_skill_root=default_skill_root("knowledge-document-composer"),
                resume=True,
            )
        )
        assert_true("resume enabled", resume_result["resume_enabled"] is True, failures)
        resume_state = read_json(project_root / "logs" / "run_state.json")
        skipped = [row for row in resume_state.get("stages", []) if row.get("status") == "skipped"]
        assert_true("resume skipped stages", len(skipped) >= 7, failures, json.dumps(resume_state, ensure_ascii=False))
        assert_true("resume skipped stderr", all("stderr" in row for row in skipped), failures)
        assert_true("resume skipped reason", all(row.get("skipped_reason") for row in skipped), failures)
        assert_stage_state_fields(resume_state, failures)

        deleted_segment = project_root / "10_video" / "02_segments" / "argument_segments.json"
        deleted_segment.unlink()
        rerun_missing = run_local_transcript_workflow(
            argparse.Namespace(
                input_transcript=transcript,
                project_root=project_root,
                output_base=base / "outputs",
                language="en",
                document_goal="Write an auditable source-faithful report",
                final_language="zh-CN",
                audience="workflow reviewer",
                video_skill_root=default_skill_root("knowledge-video-decomposer"),
                document_skill_root=default_skill_root("knowledge-document-composer"),
                resume=True,
            )
        )
        assert_true("deleted segment regenerated", deleted_segment.is_file(), failures)
        missing_resume_state = read_json(project_root / "logs" / "run_state.json")
        segmenter_row = latest_stage_record(missing_resume_state, "transcript_segmenter")
        assert_true("missing artifact reruns stage", segmenter_row.get("status") == "completed", failures, json.dumps(segmenter_row, ensure_ascii=False))
        assert_true("missing artifact rerun reason", segmenter_row.get("resume_decision") == "expected_outputs_missing", failures, json.dumps(segmenter_row, ensure_ascii=False))
        assert_true("missing artifact resume result", rerun_missing["resume_enabled"] is True, failures)
        assert_true(
            "stage history preserves rerun attempts",
            len(missing_resume_state.get("stage_history", [])) > len(missing_resume_state.get("stages", [])),
            failures,
            json.dumps(missing_resume_state, ensure_ascii=False),
        )

        forced_resume = run_local_transcript_workflow(
            argparse.Namespace(
                input_transcript=transcript,
                project_root=project_root,
                output_base=base / "outputs",
                language="en",
                document_goal="Write an auditable source-faithful report",
                final_language="zh-CN",
                audience="workflow reviewer",
                video_skill_root=default_skill_root("knowledge-video-decomposer"),
                document_skill_root=default_skill_root("knowledge-document-composer"),
                resume=False,
                resume_from_stage="inventory_extractor",
                resume_after_stage="",
            )
        )
        forced_state = read_json(project_root / "logs" / "run_state.json")
        forced_inventory = latest_stage_record(forced_state, "inventory_extractor")
        forced_segmenter = latest_stage_record(forced_state, "transcript_segmenter")
        assert_true("forced resume enabled", forced_resume["resume_enabled"] is True, failures)
        assert_true("forced stage reruns", forced_inventory.get("status") == "completed", failures, json.dumps(forced_inventory, ensure_ascii=False))
        assert_true("earlier stage can skip", forced_segmenter.get("status") == "skipped", failures, json.dumps(forced_segmenter, ensure_ascii=False))

        forced_after = run_local_transcript_workflow(
            argparse.Namespace(
                input_transcript=transcript,
                project_root=project_root,
                output_base=base / "outputs",
                language="en",
                document_goal="Write an auditable source-faithful report",
                final_language="zh-CN",
                audience="workflow reviewer",
                video_skill_root=default_skill_root("knowledge-video-decomposer"),
                document_skill_root=default_skill_root("knowledge-document-composer"),
                resume=False,
                resume_from_stage="",
                resume_after_stage="inventory_extractor",
            )
        )
        forced_after_state = read_json(project_root / "logs" / "run_state.json")
        after_inventory = latest_stage_record(forced_after_state, "inventory_extractor")
        after_logic = latest_stage_record(forced_after_state, "source_logic_builder")
        assert_true("forced after resume enabled", forced_after["resume_enabled"] is True, failures)
        assert_true("resume after earlier stage skipped", after_inventory.get("status") == "skipped", failures, json.dumps(after_inventory, ensure_ascii=False))
        assert_true("resume after next stage reruns", after_logic.get("status") == "completed", failures, json.dumps(after_logic, ensure_ascii=False))

        other_transcript = base / "other_fixture.txt"
        write_fixture_transcript(other_transcript)
        try:
            run_local_transcript_workflow(
                argparse.Namespace(
                    input_transcript=other_transcript,
                    project_root=project_root,
                    output_base=base / "outputs",
                    language="en",
                    document_goal="Write an auditable source-faithful report",
                    final_language="zh-CN",
                    audience="workflow reviewer",
                    video_skill_root=default_skill_root("knowledge-video-decomposer"),
                    document_skill_root=default_skill_root("knowledge-document-composer"),
                    resume=True,
                )
            )
        except EndToEndRunnerError:
            pass
        else:
            failures.append("resume changed input: expected EndToEndRunnerError")

        fake_video_root, fake_document_root = write_fake_skill_scripts(base)

        def fake_args(**overrides: Any) -> argparse.Namespace:
            payload: dict[str, Any] = {
                "input_transcript": None,
                "input_media": None,
                "input_url": None,
                "project_root": base / "fake_project",
                "output_base": base / "outputs",
                "language": "en",
                "document_goal": "Fake document",
                "final_language": "zh-CN",
                "audience": "workflow reviewer",
                "video_skill_root": fake_video_root,
                "document_skill_root": fake_document_root,
                "platform_mode": "auto",
                "youtube_cookies": None,
                "ytdlp": None,
                "node": None,
                "platform_timeout_seconds": 1,
                "no_doctor": True,
                "use_js_runtime": False,
                "use_remote_components": False,
                "subtitle_languages": "all,-live_chat",
                "asr_jsonl": None,
                "asr_python": None,
                "asr_model": "base",
                "asr_device": "cpu",
                "asr_compute_type": "int8",
                "asr_timeout_seconds": 0.0,
                "asr_vad": True,
                "resume": False,
                "resume_from_stage": "",
                "resume_after_stage": "",
            }
            payload.update(overrides)
            return argparse.Namespace(**payload)

        url_sub_project = base / "url_subtitle_project"
        url_subtitle = run_workflow(
            fake_args(input_url="https://example.invalid/subtitle", project_root=url_sub_project)
        )
        assert_true("url subtitle mode", url_subtitle["mode"] == "platform_url", failures)
        assert_true("url subtitle pack", (url_sub_project / "10_video" / "video_analysis_pack.md").is_file(), failures)
        url_sub_stage_names = [step["stage"] for step in url_subtitle["steps"]]
        assert_true("url subtitle platform stage", "platform_media_runner" in url_sub_stage_names, failures)
        assert_true("url subtitle normalizer stage", "transcript_normalizer" in url_sub_stage_names, failures)

        url_subtitle_resume = run_workflow(
            fake_args(input_url="https://example.invalid/subtitle", project_root=url_sub_project, resume=True)
        )
        resume_state = read_json(url_sub_project / "logs" / "run_state.json")
        platform_rows = [row for row in resume_state.get("stages", []) if row.get("stage") == "platform_media_runner"]
        assert_true(
            "url resume skips platform stage",
            platform_rows and platform_rows[-1].get("status") == "skipped",
            failures,
            json.dumps(resume_state, ensure_ascii=False),
        )
        assert_stage_state_fields(resume_state, failures)
        assert_true("url resume enabled", url_subtitle_resume["resume_enabled"] is True, failures)

        url_audio_project = base / "url_audio_project"
        url_audio = run_workflow(fake_args(input_url="https://example.invalid/audio", project_root=url_audio_project))
        assert_true("url audio pack", (url_audio_project / "10_video" / "video_analysis_pack.md").is_file(), failures)
        url_audio_stage_names = [step["stage"] for step in url_audio["steps"]]
        assert_true("url audio asr stage", "asr_pipeline" in url_audio_stage_names, failures)

        local_media_project = base / "local_media_project"
        media = base / "fake_media.mp3"
        media.write_bytes(b"fake media")
        local_media = run_workflow(fake_args(input_media=media, project_root=local_media_project))
        assert_true("local media mode", local_media["mode"] == "local_media", failures)
        assert_true("local media asr stage", local_media["steps"][0]["stage"] == "asr_pipeline", failures)

        metadata_project = base / "metadata_project"
        metadata_only = run_workflow(fake_args(input_url="https://example.invalid/metadata", project_root=metadata_project))
        assert_true("metadata degraded outcome", metadata_only["workflow_outcome"] == "degraded_acquisition_only", failures)
        assert_true("metadata no pack", not (metadata_project / "10_video" / "video_analysis_pack.md").exists(), failures)
        assert_true("metadata no segments", not (metadata_project / "10_video" / "02_segments").exists(), failures)

        blocked_project = base / "blocked_project"
        blocked = run_workflow(fake_args(input_url="https://example.invalid/blocked", project_root=blocked_project))
        assert_true("blocked degraded outcome", blocked["workflow_outcome"] == "degraded_acquisition_only", failures)
        assert_true("blocked source status", blocked["source_status"] == "source_blocked", failures)
        assert_true("blocked no pack", not (blocked_project / "10_video" / "video_analysis_pack.md").exists(), failures)
        assert_true("blocked no segments", not (blocked_project / "10_video" / "02_segments").exists(), failures)
        assert_true("blocked no document intake", not (blocked_project / "20_document" / "composer_intake.json").exists(), failures)
        blocked_state = read_json(blocked_project / "logs" / "run_state.json")
        assert_true("blocked reason recorded", bool(blocked_state.get("degraded_reason")), failures, json.dumps(blocked_state, ensure_ascii=False))
        assert_true("blocked user action recorded", bool(blocked_state.get("user_action_required")), failures, json.dumps(blocked_state, ensure_ascii=False))
        assert_stage_state_fields(blocked_state, failures)

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
        summary = run_workflow(args)
    except EndToEndRunnerError as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "error": "end_to_end_runner_failed",
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
