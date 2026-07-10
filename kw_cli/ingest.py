"""Ingest acquisition bundles into source-gated workflow artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import bundle


REPO_ROOT = Path(__file__).resolve().parents[1]
VIDEO = REPO_ROOT / "skills" / "knowledge-video-decomposer"
DOCUMENT = REPO_ROOT / "skills" / "knowledge-document-composer"
ALLOWED_DECOMPOSITION_STATUSES = {"source_confirmed", "source_partial"}
TRANSCRIPT_TYPES = {"transcript", "subtitle", "page_markdown", "page_text"}
MEDIA_TYPES = {"audio", "video"}


class IngestError(Exception):
    """Raised when bundle ingest cannot proceed."""


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: Any) -> None:
    bundle.write_json(path, payload)


def write_text(path: Path, text: str) -> None:
    bundle.write_text(path, text)


def source_permissions(source_status: str) -> tuple[bool, bool, str]:
    if source_status == "source_confirmed":
        return True, True, "full_video_analysis_pack"
    if source_status == "source_partial":
        return True, True, "partial_video_analysis_pack"
    if source_status == "secondary_only":
        return False, False, "degraded_source_report"
    if source_status == "source_blocked":
        return False, False, "blocked_source_report"
    if source_status == "source_failed":
        return False, False, "failed_source_report"
    return False, False, "degraded_report_only"


def artifact_paths(manifest_path: Path, manifest: dict[str, Any]) -> list[tuple[dict[str, Any], Path]]:
    bundle_root = manifest_path.parent
    pairs: list[tuple[dict[str, Any], Path]] = []
    for artifact in manifest.get("artifacts") or []:
        if isinstance(artifact, dict) and isinstance(artifact.get("path"), str):
            pairs.append((artifact, bundle.normalize_artifact_path(bundle_root, artifact["path"])))
    return pairs


def classify_source_status(manifest: dict[str, Any]) -> str:
    status = manifest.get("status")
    artifacts = manifest.get("artifacts") or []
    primary = [
        item
        for item in artifacts
        if isinstance(item, dict)
        and item.get("source_class") == "primary"
        and item.get("type") in TRANSCRIPT_TYPES
    ]
    partial = [
        item
        for item in artifacts
        if isinstance(item, dict)
        and item.get("source_class") == "partial_primary"
        and item.get("type") in TRANSCRIPT_TYPES
    ]
    audio_or_video = [
        item
        for item in artifacts
        if isinstance(item, dict)
        and item.get("source_class") in {"primary", "partial_primary"}
        and item.get("type") in {"audio", "video"}
    ]

    if status == "material_acquired" and primary:
        return "source_confirmed"
    if status == "partial_material_acquired" and (partial or primary):
        return "source_partial"
    if status == "material_acquired" and audio_or_video:
        return "degraded_report_only"
    if status == "metadata_only":
        return "secondary_only"
    if status == "secondary_only":
        return "secondary_only"
    if status == "blocked":
        return "source_blocked"
    if status == "failed":
        return "source_failed"
    if status == "unsupported":
        return "degraded_report_only"
    return "degraded_report_only"


def build_source_status(manifest: dict[str, Any], source_status: str) -> dict[str, Any]:
    full, composer, report_type = source_permissions(source_status)
    primary_available = source_status in {"source_confirmed", "source_partial"}
    has_media = any(
        isinstance(item, dict)
        and item.get("type") in {"audio", "video"}
        and item.get("source_class") in {"primary", "partial_primary"}
        for item in manifest.get("artifacts") or []
    )
    next_step = manifest.get("next_action") or default_next_step(source_status)
    if has_media and source_status == "degraded_report_only":
        next_step = "Run ASR for the local media or provide a transcript/subtitle."
    return {
        "source_status": source_status,
        "can_enter_full_decomposition": full,
        "can_enter_document_composer": composer,
        "allowed_report_type": report_type,
        "primary_material_available": primary_available,
        "source_classes": sorted(
            {
                str(item.get("source_class"))
                for item in manifest.get("artifacts") or []
                if isinstance(item, dict) and item.get("source_class")
            }
        ),
        "status_reason": status_reason(manifest, source_status),
        "acquisition_bundle_status": manifest.get("status"),
        "acquisition_layer": manifest.get("acquisition_layer"),
        "active_backend": manifest.get("active_backend"),
        "next_step": next_step,
    }


def status_reason(manifest: dict[str, Any], source_status: str) -> str:
    if source_status == "source_confirmed":
        return "Primary transcript/subtitle/text material was acquired through the acquisition bundle."
    if source_status == "source_partial":
        return "Partial primary material was acquired through the acquisition bundle."
    if any(isinstance(item, dict) and item.get("type") in {"audio", "video"} for item in manifest.get("artifacts") or []):
        return "Local audio/video exists, but no transcript has been produced yet."
    failures = manifest.get("failures") or []
    if failures:
        first = failures[0]
        if isinstance(first, dict):
            return str(first.get("reason") or first)
    if manifest.get("limits"):
        return "; ".join(str(item) for item in manifest["limits"])
    return "No primary transcript/subtitle material was available."


def default_next_step(source_status: str) -> str:
    if source_status in {"source_confirmed", "source_partial"}:
        return "run_evidence_audit"
    if source_status == "source_blocked":
        return "Resolve access manually or provide primary local material."
    if source_status == "source_failed":
        return "Fix acquisition failure or provide primary local material."
    return "Provide transcript, subtitle, local audio/video, or authorized primary material."


def has_usable_text(path: Path) -> bool:
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


def choose_primary_text_artifact(manifest_path: Path, manifest: dict[str, Any], source_status: str) -> Path | None:
    wanted_class = "partial_primary" if source_status == "source_partial" else "primary"
    candidates = []
    for artifact, path in artifact_paths(manifest_path, manifest):
        if artifact.get("source_class") == wanted_class and artifact.get("type") in TRANSCRIPT_TYPES:
            candidates.append(path)
    if not candidates and source_status == "source_partial":
        for artifact, path in artifact_paths(manifest_path, manifest):
            if artifact.get("source_class") == "primary" and artifact.get("type") in TRANSCRIPT_TYPES:
                candidates.append(path)
    return candidates[0] if candidates else None


def choose_primary_media_artifact(manifest_path: Path, manifest: dict[str, Any]) -> Path | None:
    for artifact, path in artifact_paths(manifest_path, manifest):
        if artifact.get("source_class") in {"primary", "partial_primary"} and artifact.get("type") in MEDIA_TYPES:
            return path
    return None


def run_command(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )


def run_asr_for_media_bundle(
    *,
    manifest_path: Path,
    manifest: dict[str, Any],
    project_root: Path,
    asr_model: str = "base",
    language: str = "unknown",
    asr_python: str | None = None,
    asr_jsonl: Path | None = None,
    asr_device: str = "cpu",
    asr_compute_type: str = "int8",
    asr_timeout_seconds: float = 0.0,
    asr_vad: bool = True,
    pretty: bool = False,
) -> dict[str, Any]:
    media_path = choose_primary_media_artifact(manifest_path, manifest)
    if media_path is None:
        return {"status": "skipped", "reason": "no primary media artifact in acquisition bundle"}
    video_root = project_root.resolve() / "10_video"
    command = [
        sys.executable,
        str(VIDEO / "scripts" / "asr_pipeline.py"),
        "--input-media",
        str(media_path),
        "--output-root",
        str(video_root),
        "--model",
        asr_model,
        "--language",
        language if language != "unknown" else "",
        "--device",
        asr_device,
        "--compute-type",
        asr_compute_type,
        "--timeout-seconds",
        str(asr_timeout_seconds),
        "--vad" if asr_vad else "--no-vad",
    ]
    if asr_python:
        command.extend(["--asr-python", asr_python])
    if asr_jsonl:
        command.extend(["--asr-jsonl", str(asr_jsonl.expanduser().resolve())])
    if pretty:
        command.append("--pretty")

    completed = run_command([item for item in command if item != ""], cwd=VIDEO / "scripts")
    if completed.returncode == 0:
        status_path = video_root / "00_source" / "source_status.json"
        status = read_json(status_path)
        status.update(
            {
                "acquisition_bundle_status": manifest.get("status"),
                "acquisition_layer": manifest.get("acquisition_layer"),
                "active_backend": manifest.get("active_backend"),
                "next_step": "run_evidence_audit",
            }
        )
        write_json(status_path, status)
        return {
            "status": "completed",
            "source_status": status.get("source_status"),
            "source_status_path": str(status_path),
        }

    reason = (completed.stderr or completed.stdout or "ASR command failed")[-2000:]
    failed_manifest = {
        **manifest,
        "status": "failed",
        "failures": [*list(manifest.get("failures") or []), {"stage": "asr_pipeline", "reason": reason}],
        "next_action": "Fix the ASR runtime/media file or provide a transcript/subtitle.",
    }
    status = build_source_status(failed_manifest, "source_failed")
    write_json(video_root / "00_source" / "source_status.json", status)
    write_text(video_root / "00_source" / "degraded_source_report.md", degraded_report_text(failed_manifest, status))
    return {"status": "failed", "source_status": "source_failed", "error": reason}


def run_required(command: list[str], *, cwd: Path) -> None:
    completed = run_command(command, cwd=cwd)
    if completed.returncode != 0:
        raise IngestError(
            "command failed: "
            + " ".join(command)
            + "\n"
            + (completed.stderr or completed.stdout)[-2000:]
        )


def normalize_primary_text(manifest_path: Path, manifest: dict[str, Any], project_root: Path, source_status: str) -> None:
    artifact_path = choose_primary_text_artifact(manifest_path, manifest, source_status)
    if artifact_path is None:
        return
    if not has_usable_text(artifact_path):
        raise IngestError(f"primary text artifact contains no usable text: {artifact_path}")
    video_root = project_root / "10_video"
    command = [
        sys.executable,
        str(VIDEO / "scripts" / "transcript_normalizer.py"),
        "--input",
        str(artifact_path),
        "--output-root",
        str(video_root),
    ]
    run_required(command, cwd=VIDEO / "scripts")
    if source_status == "source_partial":
        status_path = video_root / "00_source" / "source_status.json"
        status = read_json(status_path)
        full, composer, report_type = source_permissions("source_partial")
        status.update(
            {
                "source_status": "source_partial",
                "can_enter_full_decomposition": full,
                "can_enter_document_composer": composer,
                "allowed_report_type": report_type,
                "primary_material_available": True,
                "status_reason": "Partial primary material was acquired through the acquisition bundle.",
            }
        )
        write_json(status_path, status)


def degraded_report_text(manifest: dict[str, Any], status: dict[str, Any]) -> str:
    artifacts = manifest.get("artifacts") or []
    lines = [
        "# Degraded Source Report",
        "",
        f"- Acquisition status: `{manifest.get('status')}`",
        f"- Source status: `{status.get('source_status')}`",
        f"- Platform: `{manifest.get('platform')}`",
        f"- Active backend: `{manifest.get('active_backend') or 'unknown'}`",
        "",
        "## What Was Acquired",
        "",
    ]
    if artifacts:
        for artifact in artifacts:
            if isinstance(artifact, dict):
                lines.append(
                    f"- `{artifact.get('type')}` / `{artifact.get('source_class')}`: `{artifact.get('path')}`"
                )
    else:
        lines.append("- No usable artifact was acquired.")
    lines.extend(
        [
            "",
            "## What Is Missing",
            "",
            "Primary transcript, subtitle, browser-visible transcript, or an audio-derived transcript is missing.",
            "",
            "## Why Full Analysis Is Not Allowed",
            "",
            str(status.get("status_reason") or "The source gate did not confirm primary material."),
            "",
            "## Next Action",
            "",
            str(status.get("next_step") or manifest.get("next_action") or default_next_step(str(status.get("source_status")))),
            "",
        ]
    )
    return "\n".join(lines)


def ingest_bundle(*, manifest_path: Path, project_root: Path) -> dict[str, Any]:
    validation = bundle.validate_manifest(manifest_path)
    if not validation["valid"]:
        source_status = "source_failed"
        project_root = project_root.resolve()
        status = build_source_status(
            {
                "status": "failed",
                "artifacts": [],
                "failures": [{"stage": "validate_bundle", "reason": "; ".join(validation["errors"])}],
                "next_action": "Fix acquisition bundle manifest before ingest.",
            },
            source_status,
        )
        write_json(project_root / "10_video" / "00_source" / "source_status.json", status)
        write_text(project_root / "10_video" / "00_source" / "degraded_source_report.md", degraded_report_text({"status": "failed", "artifacts": []}, status))
        return {"valid": False, "source_status": source_status, "errors": validation["errors"]}

    manifest = validation["manifest"]
    project_root = project_root.resolve()
    video_source_root = project_root / "10_video" / "00_source"
    video_source_root.mkdir(parents=True, exist_ok=True)
    source_status = classify_source_status(manifest)
    status = build_source_status(manifest, source_status)

    try:
        if source_status in ALLOWED_DECOMPOSITION_STATUSES:
            normalize_primary_text(manifest_path, manifest, project_root, source_status)
            normalized = read_json(video_source_root / "source_status.json")
            normalized.update(
                {
                    "acquisition_bundle_status": manifest.get("status"),
                    "acquisition_layer": manifest.get("acquisition_layer"),
                    "active_backend": manifest.get("active_backend"),
                    "next_step": "run_evidence_audit",
                }
            )
            if source_status == "source_partial":
                normalized.update(status)
            write_json(video_source_root / "source_status.json", normalized)
        else:
            write_json(video_source_root / "source_status.json", status)
            write_text(video_source_root / "degraded_source_report.md", degraded_report_text(manifest, status))
    except IngestError as exc:
        failed_manifest = {
            **manifest,
            "status": "failed",
            "failures": [*list(manifest.get("failures") or []), {"stage": "ingest", "reason": str(exc)}],
            "next_action": "Provide a non-empty transcript/subtitle or fix the source artifact.",
        }
        status = build_source_status(failed_manifest, "source_failed")
        write_json(video_source_root / "source_status.json", status)
        write_text(video_source_root / "degraded_source_report.md", degraded_report_text(failed_manifest, status))
        return {"valid": True, "source_status": "source_failed", "error": str(exc)}

    return {
        "valid": True,
        "source_status": status.get("source_status") if source_status not in ALLOWED_DECOMPOSITION_STATUSES else read_json(video_source_root / "source_status.json").get("source_status"),
        "source_status_path": str(video_source_root / "source_status.json"),
        "can_enter_full_decomposition": bool(read_json(video_source_root / "source_status.json").get("can_enter_full_decomposition")),
    }


def run_audit_pipeline(*, project_root: Path, document_goal: str, final_language: str, audience: str, pretty: bool = False) -> dict[str, Any]:
    project_root = project_root.resolve()
    video_root = project_root / "10_video"
    document_root = project_root / "20_document"
    source_status = read_json(video_root / "00_source" / "source_status.json")
    state = source_status.get("source_status")
    if state not in ALLOWED_DECOMPOSITION_STATUSES:
        return {"status": "skipped", "reason": f"source gate does not allow audit: {state}"}
    if not (video_root / "01_transcript" / "clean_transcript.jsonl").is_file():
        return {"status": "skipped", "reason": "clean transcript is missing"}

    stages = [
        [sys.executable, str(VIDEO / "scripts" / "transcript_segmenter.py"), "--output-root", str(video_root)],
        [sys.executable, str(VIDEO / "scripts" / "inventory_extractor.py"), "--output-root", str(video_root)],
        [sys.executable, str(VIDEO / "scripts" / "source_logic_builder.py"), "--output-root", str(video_root)],
        [sys.executable, str(VIDEO / "scripts" / "evidence_auditor.py"), "--output-root", str(video_root)],
        [sys.executable, str(VIDEO / "scripts" / "video_analysis_pack_builder.py"), "--output-root", str(video_root)],
        [
            sys.executable,
            str(DOCUMENT / "scripts" / "document_composer_runner.py"),
            "--video-root",
            str(video_root),
            "--document-root",
            str(document_root),
            "--document-goal",
            document_goal,
            "--final-language",
            final_language,
            "--audience",
            audience,
        ],
    ]
    if pretty:
        for stage in stages:
            stage.append("--pretty")
    completed: list[str] = []
    for stage in stages:
        run_required(stage, cwd=Path(stage[1]).parent)
        completed.append(Path(stage[1]).name)
    return {"status": "completed", "stages": completed}


def compose_final_report(*, project_root: Path, pretty: bool = False) -> dict[str, Any]:
    document_root = project_root.resolve() / "20_document"
    command = [
        sys.executable,
        str(DOCUMENT / "scripts" / "final_report_writer.py"),
        "--document-root",
        str(document_root),
    ]
    if pretty:
        command.append("--pretty")
    run_required(command, cwd=DOCUMENT / "scripts")
    return {"status": "completed", "final_report": str(document_root / "final_report.md")}
