"""Ingest acquisition bundles into source-gated workflow artifacts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import bundle, source_gate, source_status_contract


REPO_ROOT = Path(__file__).resolve().parents[1]
VIDEO = REPO_ROOT / "skills" / "knowledge-video-decomposer"
DOCUMENT = REPO_ROOT / "skills" / "knowledge-document-composer"
ALLOWED_DECOMPOSITION_STATUSES = {"source_confirmed", "source_partial"}
TRANSCRIPT_TYPES = {"transcript", "subtitle", "page_markdown", "page_text"}
MEDIA_TYPES = {"audio", "video"}
PROVENANCE_KEYS = (
    "run_id",
    "attempt_id",
    "bundle_id",
    "source_id",
    "source_fingerprint",
    "analysis_target",
    "operation",
    "gate_input_sha256",
)


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


def write_source_status(video_source_root: Path, status: dict[str, Any]) -> Path:
    """Publish one canonical status atomically and verify the stored payload."""
    source_status_contract.require_valid_source_status(status)
    video_source_root.mkdir(parents=True, exist_ok=True)
    status_path = video_source_root / "source_status.json"
    temp_path = video_source_root / f".source_status.{uuid.uuid4().hex}.tmp"
    try:
        bundle.write_json(temp_path, status)
        stored_candidate = read_json(temp_path)
        source_status_contract.require_valid_source_status(stored_candidate)
        os.replace(temp_path, status_path)
    finally:
        temp_path.unlink(missing_ok=True)
    stored = read_json(status_path)
    source_status_contract.require_valid_source_status(stored)
    return status_path


def write_text(path: Path, text: str) -> None:
    bundle.write_text(path, text)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path: Path) -> str:
    return bundle.sha256_file(path) if path.is_file() else ""


def provenance_from_status(status: dict[str, Any], *, generated_by: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "generated_by": generated_by,
        **{key: status.get(key) or "" for key in PROVENANCE_KEYS},
        "source_status": status.get("source_status") or "",
    }


def write_gate_receipt(video_source_root: Path, status: dict[str, Any], *, derived_artifacts: list[dict[str, Any]] | None = None) -> Path:
    status_path = video_source_root / "source_status.json"
    receipt = provenance_from_status(status, generated_by="source-gated-evidence-layer")
    receipt["source_status_sha256"] = file_sha256(status_path)
    receipt["approved_scope"] = status.get("approved_scope") or []
    receipt["uncovered_scopes"] = status.get("uncovered_scopes") or []
    receipt["derived_artifacts"] = derived_artifacts or []
    path = video_source_root / "gate_receipt.json"
    write_json(path, receipt)
    return path


def archive_stale_downstream(project_root: Path, manifest: dict[str, Any]) -> Path | None:
    source_status_path = project_root / "10_video" / "00_source" / "source_status.json"
    previous = read_json(source_status_path)
    if not previous:
        return None
    previous_bundle = str(previous.get("bundle_id") or "legacy")
    current_bundle = str(manifest.get("bundle_id") or "legacy")
    if previous_bundle == current_bundle:
        return None
    archive_root = project_root / "run_history" / (str(previous.get("attempt_id") or previous_bundle) or "legacy")
    if archive_root.exists():
        archive_root = archive_root.with_name(archive_root.name + "-" + datetime.now(timezone.utc).strftime("%H%M%S%f"))
    moved = False
    for name in ("10_video", "20_document", "30_final"):
        source = project_root / name
        if not source.exists():
            continue
        archive_root.mkdir(parents=True, exist_ok=True)
        source.replace(archive_root / name)
        moved = True
    return archive_root if moved else None


def receipt_matches_status(receipt: dict[str, Any], status: dict[str, Any]) -> bool:
    return bool(receipt) and all((receipt.get(key) or "") == (status.get(key) or "") for key in PROVENANCE_KEYS)


def derived_artifact_reasons(project_root: Path, gate: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for index, artifact in enumerate(gate.get("derived_artifacts") or []):
        if not isinstance(artifact, dict):
            reasons.append(f"gate derived artifact {index} is not an object")
            continue
        raw_path = artifact.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            reasons.append(f"gate derived artifact {index} has no path")
            continue
        path = (project_root / raw_path).resolve()
        try:
            bundle.relative_path_within(project_root, path)
        except ValueError:
            reasons.append(f"gate derived artifact escapes the project root: {raw_path}")
            continue
        if not path.is_file():
            reasons.append(f"gate derived artifact is missing: {raw_path}")
            continue
        expected_bytes = artifact.get("bytes")
        if isinstance(expected_bytes, int) and path.stat().st_size != expected_bytes:
            reasons.append(f"gate derived artifact byte count changed: {raw_path}")
        expected_sha256 = artifact.get("sha256")
        if isinstance(expected_sha256, str) and expected_sha256 and file_sha256(path) != expected_sha256:
            reasons.append(f"gate derived artifact hash changed: {raw_path}")
    return reasons


def current_provenance(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    manifest_path = project_root / "00_acquisition" / "manifest.json"
    source_status_path = project_root / "10_video" / "00_source" / "source_status.json"
    gate_receipt_path = project_root / "10_video" / "00_source" / "gate_receipt.json"
    status = read_json(source_status_path)
    gate = read_json(gate_receipt_path)
    reasons: list[str] = []
    status_errors = source_status_contract.validate_source_status(status) if status else ["source status is missing"]
    reasons.extend(f"invalid source status contract: {error}" for error in status_errors)
    if not manifest_path.is_file():
        reasons.append("current acquisition manifest is missing")
    elif status.get("gate_input_sha256") != file_sha256(manifest_path):
        reasons.append("source status does not match the current acquisition manifest hash")
    if not receipt_matches_status(gate, status):
        reasons.append("gate receipt does not match the current source status")
    elif gate.get("source_status_sha256") != file_sha256(source_status_path):
        reasons.append("source status changed after the gate receipt was written")
    else:
        reasons.extend(derived_artifact_reasons(project_root, gate))

    gate_current = not reasons
    analysis_receipt = read_json(project_root / "10_video" / "analysis_receipt.json")
    composer_receipt = read_json(project_root / "20_document" / "composer_receipt.json")
    final_receipt = read_json(project_root / "20_document" / "final_report_receipt.json")
    analysis_current = gate_current and receipt_matches_status(analysis_receipt, status)
    if analysis_current:
        pack_path = project_root / "10_video" / str(analysis_receipt.get("analysis_pack") or "video_analysis_pack.md")
        analysis_current = bool(
            pack_path.is_file()
            and analysis_receipt.get("analysis_pack_sha256") == file_sha256(pack_path)
            and analysis_receipt.get("gate_receipt_sha256") == file_sha256(gate_receipt_path)
        )
    composer_current = analysis_current and receipt_matches_status(composer_receipt, status)
    if composer_current:
        claim_map_path = project_root / "20_document" / "claim_map.json"
        intake_path = project_root / "20_document" / "composer_intake.json"
        composer_current = bool(
            claim_map_path.is_file()
            and intake_path.is_file()
            and composer_receipt.get("claim_map_sha256") == file_sha256(claim_map_path)
            and composer_receipt.get("composer_intake_sha256") == file_sha256(intake_path)
            and composer_receipt.get("analysis_receipt_sha256") == file_sha256(project_root / "10_video" / "analysis_receipt.json")
        )
    final_current = composer_current and receipt_matches_status(final_receipt, status)
    if final_current:
        report_path = project_root / "20_document" / "final_report.md"
        final_current = bool(
            report_path.is_file()
            and final_receipt.get("final_report_sha256") == file_sha256(report_path)
            and final_receipt.get("composer_receipt_sha256") == file_sha256(project_root / "20_document" / "composer_receipt.json")
        )
    return {
        "gate_current": gate_current,
        "analysis_current": analysis_current,
        "composer_current": composer_current,
        "final_report_current": final_current,
        "reasons": reasons,
        "source_status": status,
    }


def source_permissions(source_status: str, analysis_target: str = "video_content") -> tuple[bool, bool, str]:
    return source_status_contract.permissions_for_status(source_status, analysis_target)


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
    if manifest.get("schema_version") == 1:
        inferred_target = source_gate.infer_analysis_target(str(manifest.get("platform") or "unknown"))
        manifest = {**manifest, "analysis_target": inferred_target}
        artifacts = [
            {
                **item,
                "content_scope": item.get("content_scope")
                or source_gate.infer_content_scope(str(item.get("type") or "unknown"), str(manifest.get("platform") or "unknown")),
            }
            if isinstance(item, dict)
            else item
            for item in artifacts
        ]
        manifest["artifacts"] = artifacts
    primary = source_gate.matching_primary_artifacts(manifest)
    partial = source_gate.matching_partial_artifacts(manifest)
    audio_or_video = [
        item
        for item in artifacts
        if isinstance(item, dict)
        and item.get("source_class") in {"primary", "partial_primary"}
        and item.get("type") in {"audio", "video"}
    ]

    if status == "material_acquired" and primary:
        return "source_confirmed"
    if status == "partial_material_acquired" and partial:
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


def build_source_status(manifest: dict[str, Any], source_status: str, *, manifest_path: Path | None = None) -> dict[str, Any]:
    manifest_sha256 = bundle.sha256_file(manifest_path) if manifest_path and manifest_path.is_file() else ""
    return source_status_contract.build_source_status(
        manifest,
        source_status,
        gate_input_sha256=manifest_sha256,
    )


def status_reason(manifest: dict[str, Any], source_status: str) -> str:
    analysis_target = str(
        manifest.get("analysis_target")
        or source_gate.infer_analysis_target(str(manifest.get("platform") or "unknown"))
    )
    scope_status = source_status_contract.scope_status_for(manifest, source_status, analysis_target)
    return source_status_contract.status_reason(manifest, source_status, scope_status)


def default_next_step(source_status: str) -> str:
    return source_status_contract.default_next_step(source_status)


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


def choose_primary_text_artifact_entry(
    manifest_path: Path,
    manifest: dict[str, Any],
    source_status: str,
) -> tuple[dict[str, Any], Path] | None:
    wanted_class = "partial_primary" if source_status == "source_partial" else "primary"
    target = str(manifest.get("analysis_target") or "video_content")
    allowed_scopes = source_gate.TARGET_PRIMARY_SCOPES.get(target, set())
    candidates: list[tuple[dict[str, Any], Path]] = []
    for artifact, path in artifact_paths(manifest_path, manifest):
        if (
            artifact.get("source_class") == wanted_class
            and artifact.get("type") in TRANSCRIPT_TYPES
            and artifact.get("content_scope") in allowed_scopes
        ):
            candidates.append((artifact, path))
    if not candidates and source_status == "source_partial":
        for artifact, path in artifact_paths(manifest_path, manifest):
            if (
                artifact.get("source_class") == "primary"
                and artifact.get("type") in TRANSCRIPT_TYPES
                and artifact.get("content_scope") in allowed_scopes
            ):
                candidates.append((artifact, path))
    return candidates[0] if candidates else None


def choose_primary_text_artifact(manifest_path: Path, manifest: dict[str, Any], source_status: str) -> Path | None:
    chosen = choose_primary_text_artifact_entry(manifest_path, manifest, source_status)
    return chosen[1] if chosen else None


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
        env={
            **__import__("os").environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        },
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
    if language and language != "unknown":
        command.extend(["--language", language])
    if asr_jsonl:
        command.extend(["--asr-jsonl", str(asr_jsonl.expanduser().resolve())])
    if pretty:
        command.append("--pretty")

    completed = run_command(command, cwd=VIDEO / "scripts")
    if completed.returncode == 0:
        status_path = video_root / "00_source" / "source_status.json"
        transcript_path = video_root / "01_transcript" / "clean_transcript.jsonl"
        if not transcript_path.is_file() or transcript_path.stat().st_size == 0:
            reason = "ASR command completed without producing clean_transcript.jsonl"
            failed_manifest = {
                **manifest,
                "status": "failed",
                "failures": [*list(manifest.get("failures") or []), {"stage": "asr_pipeline", "reason": reason}],
                "next_action": "Fix the ASR runtime/media file or provide a transcript/subtitle.",
            }
            status = build_source_status(failed_manifest, "source_failed", manifest_path=manifest_path)
            write_source_status(video_root / "00_source", status)
            write_gate_receipt(video_root / "00_source", status)
            write_text(video_root / "00_source" / "degraded_source_report.md", degraded_report_text(failed_manifest, status))
            return {"status": "failed", "source_status": "source_failed", "error": reason}
        derived_artifact = {
            "path": bundle.relative_path_within(project_root, transcript_path).as_posix(),
            "type": "transcript",
            "content_scope": "video_transcript",
            "bytes": transcript_path.stat().st_size,
            "sha256": file_sha256(transcript_path),
            "created_by": "asr_pipeline",
        }
        derived_manifest = {
            **manifest,
            "status": "material_acquired",
            "artifacts": [
                *list(manifest.get("artifacts") or []),
                {
                    **derived_artifact,
                    "source_class": "primary",
                },
            ],
        }
        status = build_source_status(derived_manifest, "source_confirmed", manifest_path=manifest_path)
        status.update(
            {
                "approved_scope": ["video_transcript"],
                "uncovered_scopes": [],
                "source_classes": ["primary_audio_asr"],
                "status_reason": "Primary local media was transcribed into a usable transcript by the ASR pipeline.",
                "next_step": "run_evidence_audit",
            }
        )
        write_source_status(video_root / "00_source", status)
        write_gate_receipt(video_root / "00_source", status, derived_artifacts=[derived_artifact])
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
    status = build_source_status(failed_manifest, "source_failed", manifest_path=manifest_path)
    write_source_status(video_root / "00_source", status)
    write_gate_receipt(video_root / "00_source", status)
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


def normalize_primary_text(
    manifest_path: Path,
    manifest: dict[str, Any],
    project_root: Path,
    source_status: str,
) -> dict[str, Any] | None:
    chosen = choose_primary_text_artifact_entry(manifest_path, manifest, source_status)
    if chosen is None:
        return None
    artifact, artifact_path = chosen
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
    transcript_path = video_root / "01_transcript" / "clean_transcript.jsonl"
    if not transcript_path.is_file() or transcript_path.stat().st_size == 0:
        raise IngestError("transcript normalizer completed without producing clean_transcript.jsonl")
    if not has_usable_text(transcript_path):
        raise IngestError("normalized clean_transcript.jsonl contains no usable text")
    try:
        relative_path = bundle.relative_path_within(project_root, transcript_path).as_posix()
        source_relative_path = bundle.relative_path_within(project_root, artifact_path).as_posix()
    except ValueError as exc:
        raise IngestError("normalized transcript or its source artifact escaped the project root") from exc
    return {
        "path": relative_path,
        "type": "transcript",
        "content_scope": str(artifact.get("content_scope") or "video_transcript"),
        "bytes": transcript_path.stat().st_size,
        "sha256": file_sha256(transcript_path),
        "created_by": "transcript_normalizer",
        "derived_from": source_relative_path,
        "derived_from_sha256": file_sha256(artifact_path),
    }


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
            manifest_path=manifest_path,
        )
        invalid_source_root = project_root / "10_video" / "00_source"
        write_source_status(invalid_source_root, status)
        write_gate_receipt(invalid_source_root, status)
        write_text(project_root / "10_video" / "00_source" / "degraded_source_report.md", degraded_report_text({"status": "failed", "artifacts": []}, status))
        return {"valid": False, "source_status": source_status, "errors": validation["errors"]}

    manifest = validation["manifest"]
    project_root = project_root.resolve()
    archive_stale_downstream(project_root, manifest)
    video_source_root = project_root / "10_video" / "00_source"
    video_source_root.mkdir(parents=True, exist_ok=True)
    source_status = classify_source_status(manifest)
    status = build_source_status(manifest, source_status, manifest_path=manifest_path)

    try:
        if source_status in ALLOWED_DECOMPOSITION_STATUSES:
            derived_artifact = normalize_primary_text(manifest_path, manifest, project_root, source_status)
            normalized = read_json(video_source_root / "source_status.json")
            normalized.update(
                {
                    "acquisition_bundle_status": manifest.get("status"),
                    "acquisition_layer": manifest.get("acquisition_layer"),
                    "active_backend": manifest.get("active_backend"),
                    "next_step": "run_evidence_audit",
                }
            )
            normalized.update(status)
            write_source_status(video_source_root, normalized)
            write_gate_receipt(
                video_source_root,
                read_json(video_source_root / "source_status.json"),
                derived_artifacts=[derived_artifact] if derived_artifact else [],
            )
        else:
            write_source_status(video_source_root, status)
            write_gate_receipt(video_source_root, status)
            write_text(video_source_root / "degraded_source_report.md", degraded_report_text(manifest, status))
    except IngestError as exc:
        failed_manifest = {
            **manifest,
            "status": "failed",
            "failures": [*list(manifest.get("failures") or []), {"stage": "ingest", "reason": str(exc)}],
            "next_action": "Provide a non-empty transcript/subtitle or fix the source artifact.",
        }
        status = build_source_status(failed_manifest, "source_failed", manifest_path=manifest_path)
        write_source_status(video_source_root, status)
        write_gate_receipt(video_source_root, status)
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
    try:
        source_status_contract.require_valid_source_status(source_status)
    except source_status_contract.SourceStatusContractError as exc:
        raise IngestError(f"refusing to audit an invalid source status: {exc}") from exc
    state = source_status.get("source_status")
    if state not in ALLOWED_DECOMPOSITION_STATUSES:
        return {"status": "skipped", "reason": f"source gate does not allow audit: {state}"}
    provenance = current_provenance(project_root)
    if not provenance["gate_current"]:
        return {"status": "skipped", "reason": "source gate provenance is stale: " + "; ".join(provenance["reasons"])}
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
        stage_name = Path(stage[1]).name
        completed.append(stage_name)
        if stage_name != "document_composer_runner.py":
            write_source_status(video_root / "00_source", source_status)
        if stage_name == "video_analysis_pack_builder.py" and source_status.get("analysis_target") != "video_content":
            legacy_pack = video_root / "video_analysis_pack.md"
            source_pack = video_root / "source_analysis_pack.md"
            if legacy_pack.is_file():
                shutil.copy2(legacy_pack, source_pack)
        if stage_name == "video_analysis_pack_builder.py":
            pack_name = "source_analysis_pack.md" if source_status.get("analysis_target") != "video_content" else "video_analysis_pack.md"
            pack_path = video_root / pack_name
            if not pack_path.is_file():
                raise IngestError(f"analysis pack stage did not produce {pack_name}")
            receipt = provenance_from_status(source_status, generated_by="source-gated-evidence-layer.audit")
            receipt.update(
                {
                    "gate_receipt_sha256": file_sha256(video_root / "00_source" / "gate_receipt.json"),
                    "analysis_pack": pack_name,
                    "analysis_pack_sha256": file_sha256(pack_path),
                    "evidence_audit_sha256": file_sha256(video_root / "05_gap_check" / "evidence_audit.json"),
                }
            )
            write_json(video_root / "analysis_receipt.json", receipt)
        if stage_name == "document_composer_runner.py":
            analysis_receipt_path = video_root / "analysis_receipt.json"
            claim_map_path = document_root / "claim_map.json"
            intake_path = document_root / "composer_intake.json"
            if not analysis_receipt_path.is_file() or not claim_map_path.is_file() or not intake_path.is_file():
                raise IngestError("document composer did not produce provenance-ready planning artifacts")
            receipt = provenance_from_status(source_status, generated_by="knowledge-document-composer")
            receipt.update(
                {
                    "analysis_receipt_sha256": file_sha256(analysis_receipt_path),
                    "claim_map_sha256": file_sha256(claim_map_path),
                    "composer_intake_sha256": file_sha256(intake_path),
                    "quality_check_sha256": file_sha256(document_root / "quality_check.md"),
                }
            )
            write_json(document_root / "composer_receipt.json", receipt)
    return {"status": "completed", "stages": completed}


def compose_final_report(*, project_root: Path, pretty: bool = False) -> dict[str, Any]:
    project_root = project_root.resolve()
    document_root = project_root / "20_document"
    provenance = current_provenance(project_root)
    if not provenance["composer_current"]:
        raise IngestError("refusing to compose from stale or unverified document artifacts")
    command = [
        sys.executable,
        str(DOCUMENT / "scripts" / "final_report_writer.py"),
        "--document-root",
        str(document_root),
    ]
    if pretty:
        command.append("--pretty")
    run_required(command, cwd=DOCUMENT / "scripts")
    report_path = document_root / "final_report.md"
    if not report_path.is_file():
        raise IngestError("final report writer completed without producing final_report.md")
    status = provenance["source_status"]
    receipt = provenance_from_status(status, generated_by="knowledge-document-composer.final-report")
    receipt.update(
        {
            "composer_receipt_sha256": file_sha256(document_root / "composer_receipt.json"),
            "final_report_sha256": file_sha256(report_path),
            "quality_gate_sha256": file_sha256(document_root / "quality_gate.json"),
        }
    )
    write_json(document_root / "final_report_receipt.json", receipt)
    return {"status": "completed", "final_report": str(document_root / "final_report.md")}
