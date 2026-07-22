#!/usr/bin/env python
"""Shared provenance and file helpers for the learning-article pipeline."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROVENANCE_KEYS = (
    "run_id",
    "bundle_id",
    "source_id",
    "source_fingerprint",
    "analysis_target",
    "gate_input_sha256",
)
ALLOWED_SOURCE_STATES = {"source_confirmed", "source_partial"}


class LearningPipelineError(RuntimeError):
    """Raised when a learning artifact cannot be produced safely."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise LearningPipelineError(f"required JSON file is missing: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LearningPipelineError(f"cannot read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LearningPipelineError(f"JSON root must be an object: {path}")
    return payload


def read_text(path: Path, *, required: bool = False) -> str:
    if not path.is_file():
        if required:
            raise LearningPipelineError(f"required text file is missing: {path}")
        return ""
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n").rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def sha256_file(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def receipt_matches(receipt: dict[str, Any], status: dict[str, Any]) -> bool:
    return bool(receipt) and all((receipt.get(key) or "") == (status.get(key) or "") for key in PROVENANCE_KEYS)


def copy_provenance(status: dict[str, Any]) -> dict[str, Any]:
    return {key: status.get(key) or "" for key in PROVENANCE_KEYS}


def list_items(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def first_text(*values: Any, default: str = "") -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return default


def compact(text: str, limit: int = 600) -> str:
    value = " ".join(str(text or "").split())
    return value if len(value) <= limit else value[: max(0, limit - 1)].rstrip() + "…"


def evidence_refs(item: dict[str, Any]) -> list[dict[str, Any]]:
    spans = item.get("evidence_spans")
    if not isinstance(spans, list):
        return []
    refs: list[dict[str, Any]] = []
    for span in spans:
        if not isinstance(span, dict):
            continue
        refs.append(
            {
                "transcript_ids": [str(value) for value in span.get("transcript_ids", []) if value],
                "start": span.get("start"),
                "end": span.get("end"),
                "quote": first_text(span.get("verbatim_excerpt"), span.get("quote"), span.get("text")),
                "verbatim_excerpt": first_text(span.get("verbatim_excerpt")),
            }
        )
    return refs


def validate_upstream(project_root: Path) -> dict[str, Any]:
    """Validate the current source-gate and analysis receipt chain."""

    project_root = project_root.expanduser().resolve()
    manifest_path = project_root / "00_acquisition" / "manifest.json"
    video_root = project_root / "10_video"
    source_status_path = video_root / "00_source" / "source_status.json"
    gate_path = video_root / "00_source" / "gate_receipt.json"
    analysis_path = video_root / "analysis_receipt.json"

    manifest = read_json(manifest_path)
    status = read_json(source_status_path)
    gate = read_json(gate_path)
    analysis = read_json(analysis_path)

    source_state = str(status.get("source_status") or "")
    if source_state not in ALLOWED_SOURCE_STATES:
        raise LearningPipelineError(f"source status {source_state or 'missing'} does not allow a learning article")
    if status.get("gate_input_sha256") != sha256_file(manifest_path):
        raise LearningPipelineError("source status is stale relative to the acquisition manifest")
    if not receipt_matches(gate, status):
        raise LearningPipelineError("gate receipt does not match current source status")
    if gate.get("source_status_sha256") != sha256_file(source_status_path):
        raise LearningPipelineError("source status changed after the gate receipt was written")

    analysis_pack_name = str(analysis.get("analysis_pack") or "video_analysis_pack.md")
    analysis_pack_path = video_root / analysis_pack_name
    if not receipt_matches(analysis, status):
        raise LearningPipelineError("analysis receipt does not match current source status")
    if analysis.get("gate_receipt_sha256") != sha256_file(gate_path):
        raise LearningPipelineError("analysis receipt is stale relative to the gate receipt")
    if analysis.get("analysis_pack_sha256") != sha256_file(analysis_pack_path):
        raise LearningPipelineError("analysis pack is missing or does not match its receipt")

    evidence_audit_path = video_root / "05_gap_check" / "evidence_audit.json"
    evidence_audit = read_json(evidence_audit_path, required=False)
    severity = evidence_audit.get("severity_counts") if isinstance(evidence_audit.get("severity_counts"), dict) else {}
    if int(severity.get("error") or 0) > 0:
        raise LearningPipelineError("evidence audit contains blocking errors")
    claim_summary = evidence_audit.get("claim_source_audit_summary")
    if isinstance(claim_summary, dict) and int(claim_summary.get("blocking_claims") or 0) > 0:
        raise LearningPipelineError("claim source audit contains blocking claims")

    return {
        "project_root": project_root,
        "video_root": video_root,
        "manifest": manifest,
        "source_status": status,
        "source_status_path": source_status_path,
        "gate_receipt": gate,
        "gate_receipt_path": gate_path,
        "analysis_receipt": analysis,
        "analysis_receipt_path": analysis_path,
        "analysis_pack_path": analysis_pack_path,
        "evidence_audit": evidence_audit,
        "evidence_audit_path": evidence_audit_path,
        "partial_scope": source_state == "source_partial",
    }


def validate_learning_receipt(project_root: Path) -> dict[str, Any]:
    upstream = validate_upstream(project_root)
    project_root = upstream["project_root"]
    learning_root = project_root / "15_learning"
    receipt_path = learning_root / "learning_analysis_receipt.json"
    receipt = read_json(receipt_path)
    status = upstream["source_status"]
    pack_path = learning_root / str(receipt.get("learning_analysis_pack") or "learning_analysis_pack.json")
    if not receipt_matches(receipt, status):
        raise LearningPipelineError("learning analysis receipt does not match current source status")
    if receipt.get("analysis_receipt_sha256") != sha256_file(upstream["analysis_receipt_path"]):
        raise LearningPipelineError("learning analysis receipt is stale relative to source analysis")
    if receipt.get("learning_analysis_pack_sha256") != sha256_file(pack_path):
        raise LearningPipelineError("learning analysis pack is missing or hash-mismatched")

    enrichment_path_value = str(receipt.get("enrichment_path") or "")
    enrichment_sha256 = str(receipt.get("enrichment_sha256") or "")
    if enrichment_path_value:
        enrichment_path = Path(enrichment_path_value).expanduser().resolve()
        if enrichment_sha256 != sha256_file(enrichment_path):
            raise LearningPipelineError("learning analysis receipt is stale relative to Agent enrichment")
    elif enrichment_sha256:
        raise LearningPipelineError("learning analysis receipt has an enrichment hash without a path")

    validation_name = str(receipt.get("source_reanalysis_validation") or "")
    validation_path = learning_root / validation_name if validation_name else Path()
    validation = read_json(validation_path) if validation_name else {}
    if not validation_name or receipt.get("source_reanalysis_validation_sha256") != sha256_file(validation_path):
        raise LearningPipelineError("source reanalysis validation is missing or hash-mismatched")
    if not validation.get("approved_for_learning_analysis"):
        raise LearningPipelineError("source reanalysis validation does not approve learning analysis")
    if str(validation.get("mode") or "") != str(receipt.get("source_reanalysis_mode") or ""):
        raise LearningPipelineError("source reanalysis mode does not match its validation artifact")

    source_artifact_value = str(receipt.get("source_artifact") or "")
    source_artifact_sha256 = str(receipt.get("source_artifact_sha256") or "")
    if receipt.get("source_reanalysis_mode") == "evidence_bound":
        if not source_artifact_value or not source_artifact_sha256:
            raise LearningPipelineError("evidence-bound reanalysis receipt lacks a source artifact binding")
        source_artifact_path = (project_root / source_artifact_value).resolve()
        try:
            source_artifact_path.relative_to(project_root)
        except ValueError as exc:
            raise LearningPipelineError("reanalysis source artifact resolves outside the project") from exc
        if source_artifact_sha256 != sha256_file(source_artifact_path):
            raise LearningPipelineError("reanalysis source artifact changed after learning analysis")
    upstream.update(
        {
            "learning_root": learning_root,
            "learning_receipt": receipt,
            "learning_receipt_path": receipt_path,
            "learning_pack_path": pack_path,
            "source_reanalysis_validation": validation,
            "source_reanalysis_validation_path": validation_path,
        }
    )
    return upstream
