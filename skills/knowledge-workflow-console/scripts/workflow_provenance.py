"""Validate that workflow outputs belong to the current acquisition run."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROVENANCE_KEYS = ("run_id", "bundle_id", "source_id", "source_fingerprint", "analysis_target", "gate_input_sha256")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


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


def contained_receipt_path(project_root: Path, value: str, *, base: Path | None = None) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else ((base or project_root) / candidate).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError:
        return None
    return resolved


def inspect_provenance(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    manifest_path = project_root / "00_acquisition" / "manifest.json"
    source_status_path = project_root / "10_video" / "00_source" / "source_status.json"
    gate_path = project_root / "10_video" / "00_source" / "gate_receipt.json"
    analysis_path = project_root / "10_video" / "analysis_receipt.json"
    learning_path = project_root / "15_learning" / "learning_analysis_receipt.json"
    composer_path = project_root / "20_document" / "composer_receipt.json"
    final_path = project_root / "20_document" / "final_report_receipt.json"
    learning_final_path = project_root / "20_document" / "learning_article_receipt.json"

    status = read_json(source_status_path)
    gate = read_json(gate_path)
    reasons: list[str] = []
    if not manifest_path.is_file():
        reasons.append("current acquisition manifest is missing")
    elif status.get("gate_input_sha256") != sha256_file(manifest_path):
        reasons.append("source status does not match the current acquisition manifest")
    if not receipt_matches(gate, status):
        reasons.append("gate receipt does not match source status")
    elif gate.get("source_status_sha256") != sha256_file(source_status_path):
        reasons.append("source status changed after gate receipt")
    gate_current = not reasons

    analysis = read_json(analysis_path)
    analysis_pack = project_root / "10_video" / str(analysis.get("analysis_pack") or "video_analysis_pack.md")
    analysis_current = bool(
        gate_current
        and receipt_matches(analysis, status)
        and analysis_pack.is_file()
        and analysis.get("analysis_pack_sha256") == sha256_file(analysis_pack)
        and analysis.get("gate_receipt_sha256") == sha256_file(gate_path)
    )
    learning = read_json(learning_path)
    learning_pack = project_root / "15_learning" / str(learning.get("learning_analysis_pack") or "learning_analysis_pack.json")
    learning_root = project_root / "15_learning"
    enrichment_value = str(learning.get("enrichment_path") or "")
    enrichment_path = contained_receipt_path(project_root, enrichment_value)
    enrichment_current = bool(
        (not enrichment_value and not learning.get("enrichment_sha256"))
        or (
            enrichment_path
            and enrichment_path.is_file()
            and learning.get("enrichment_sha256") == sha256_file(enrichment_path)
        )
    )
    validation_value = str(learning.get("source_reanalysis_validation") or "")
    validation_path = contained_receipt_path(project_root, validation_value, base=learning_root)
    validation_current = bool(
        validation_path
        and validation_path.is_file()
        and learning.get("source_reanalysis_validation_sha256") == sha256_file(validation_path)
    )
    source_artifact_value = str(learning.get("source_artifact") or "")
    source_artifact_path = contained_receipt_path(project_root, source_artifact_value)
    source_artifact_current = bool(
        learning.get("source_reanalysis_mode") != "evidence_bound"
        or (
            source_artifact_path
            and source_artifact_path.is_file()
            and learning.get("source_artifact_sha256") == sha256_file(source_artifact_path)
        )
    )
    learning_current = bool(
        analysis_current
        and receipt_matches(learning, status)
        and learning.get("analysis_receipt_sha256") == sha256_file(analysis_path)
        and learning_pack.is_file()
        and learning.get("learning_analysis_pack_sha256") == sha256_file(learning_pack)
        and enrichment_current
        and validation_current
        and source_artifact_current
    )
    composer = read_json(composer_path)
    composer_current = bool(
        analysis_current
        and receipt_matches(composer, status)
        and composer.get("analysis_receipt_sha256") == sha256_file(analysis_path)
        and composer.get("claim_map_sha256") == sha256_file(project_root / "20_document" / "claim_map.json")
        and composer.get("composer_intake_sha256") == sha256_file(project_root / "20_document" / "composer_intake.json")
    )
    final = read_json(final_path)
    final_report = project_root / "20_document" / "final_report.md"
    final_current = bool(
        composer_current
        and receipt_matches(final, status)
        and final.get("composer_receipt_sha256") == sha256_file(composer_path)
        and final.get("final_report_sha256") == sha256_file(final_report)
        and final.get("quality_gate_sha256") == sha256_file(project_root / "20_document" / "quality_gate.json")
    )
    learning_final = read_json(learning_final_path)
    learning_article = project_root / "20_document" / "learning_article.md"
    learning_article_current = bool(
        learning_current
        and receipt_matches(learning_final, status)
        and learning_final.get("learning_analysis_receipt_sha256") == sha256_file(learning_path)
        and learning_final.get("learning_article_sha256") == sha256_file(learning_article)
        and learning_final.get("learning_quality_gate_sha256")
        == sha256_file(project_root / "20_document" / "learning_quality_gate.json")
        and learning_final.get("approved_for_learning_article") is True
    )
    return {
        "gate_current": gate_current,
        "analysis_current": analysis_current,
        "learning_analysis_current": learning_current,
        "composer_current": composer_current,
        "final_report_current": final_current,
        "learning_article_current": learning_article_current,
        "analysis_pack": analysis_pack,
        "learning_analysis_pack": learning_pack,
        "reasons": reasons,
    }
