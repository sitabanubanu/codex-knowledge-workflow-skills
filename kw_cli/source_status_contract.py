"""Canonical SourceStatus v1 construction and validation.

This module owns the machine contract used by the public kw.py evidence path.
It does not fetch material, run ASR, or write provenance receipts.
"""

from __future__ import annotations

from typing import Any

from . import source_gate


SCHEMA_VERSION = 1

SOURCE_STATUSES = {
    "source_confirmed",
    "source_partial",
    "secondary_only",
    "source_blocked",
    "source_failed",
    "degraded_report_only",
}

SCOPE_STATUSES = {
    "matched",
    "partial_match",
    "target_mismatch",
    "pending_derivation",
    "not_evaluated",
}

PIPELINE_DECISIONS = {
    "continue_full",
    "continue_partial",
    "stop_before_audit",
}

REQUIRED_FIELDS = {
    "schema_version",
    "source_status",
    "scope_status",
    "pipeline_decision",
    "can_enter_full_decomposition",
    "can_enter_document_composer",
    "allowed_report_type",
    "primary_material_available",
    "source_classes",
    "status_reason",
    "failed_probes",
    "next_step",
    "acquisition_bundle_status",
    "acquisition_layer",
    "active_backend",
    "run_id",
    "attempt_id",
    "bundle_id",
    "source_id",
    "source_fingerprint",
    "analysis_target",
    "operation",
    "approved_scope",
    "uncovered_scopes",
    "gate_input_sha256",
}


class SourceStatusContractError(ValueError):
    """Raised when a canonical source status violates the contract."""


def permissions_for_status(source_status: str, analysis_target: str) -> tuple[bool, bool, str]:
    if source_status == "source_confirmed":
        return True, True, source_gate.allowed_report_type(source_status, analysis_target)
    if source_status == "source_partial":
        return True, True, source_gate.allowed_report_type(source_status, analysis_target)
    if source_status == "secondary_only":
        return False, False, "degraded_source_report"
    if source_status == "source_blocked":
        return False, False, "blocked_source_report"
    if source_status == "source_failed":
        return False, False, "failed_source_report"
    return False, False, "degraded_report_only"


def default_next_step(source_status: str) -> str:
    if source_status in {"source_confirmed", "source_partial"}:
        return "run_evidence_audit"
    if source_status == "source_blocked":
        return "Resolve access manually or provide primary local material."
    if source_status == "source_failed":
        return "Fix acquisition failure or provide primary local material."
    return "Provide transcript, subtitle, local audio/video, or authorized primary material."


def _primary_artifacts(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in manifest.get("artifacts") or []
        if isinstance(item, dict) and item.get("source_class") in {"primary", "partial_primary"}
    ]


def scope_status_for(manifest: dict[str, Any], source_status: str, analysis_target: str) -> str:
    if source_status == "source_confirmed":
        return "matched"
    if source_status == "source_partial":
        return "partial_match"

    primary = _primary_artifacts(manifest)
    if (
        analysis_target == "video_content"
        and any(item.get("type") in {"audio", "video"} for item in primary)
        and not any(item.get("content_scope") == "video_transcript" for item in primary)
    ):
        return "pending_derivation"

    required = source_gate.TARGET_PRIMARY_SCOPES.get(analysis_target, set())
    available = {str(item.get("content_scope") or "") for item in primary}
    if primary and required and not (required & available):
        return "target_mismatch"
    return "not_evaluated"


def pipeline_decision_for(source_status: str) -> str:
    if source_status == "source_confirmed":
        return "continue_full"
    if source_status == "source_partial":
        return "continue_partial"
    return "stop_before_audit"


def status_reason(manifest: dict[str, Any], source_status: str, scope_status: str) -> str:
    if source_status == "source_confirmed":
        return "Primary transcript/subtitle/text material was acquired through the acquisition bundle."
    if source_status == "source_partial":
        return "Partial primary material was acquired through the acquisition bundle."
    if scope_status == "pending_derivation":
        return "Local audio/video exists, but no transcript has been produced yet."
    if scope_status == "target_mismatch":
        target = str(manifest.get("analysis_target") or "")
        primary_scopes = sorted(
            {
                str(item.get("content_scope"))
                for item in _primary_artifacts(manifest)
                if item.get("content_scope")
            }
        )
        return f"Acquired primary material scopes {primary_scopes!r} do not satisfy analysis target {target!r}."
    failures = manifest.get("failures") or []
    if failures:
        first = failures[0]
        if isinstance(first, dict):
            return str(first.get("reason") or first)
        return str(first)
    if manifest.get("limits"):
        return "; ".join(str(item) for item in manifest["limits"])
    return "No primary transcript/subtitle material was available."


def build_source_status(
    manifest: dict[str, Any],
    source_status: str,
    *,
    gate_input_sha256: str = "",
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if source_status not in SOURCE_STATUSES:
        raise SourceStatusContractError(f"unsupported source_status: {source_status!r}")

    analysis_target = str(
        manifest.get("analysis_target")
        or source_gate.infer_analysis_target(str(manifest.get("platform") or "unknown"))
    )
    full, composer, report_type = permissions_for_status(source_status, analysis_target)
    scope_status = scope_status_for(manifest, source_status, analysis_target)
    has_media = any(
        item.get("type") in {"audio", "video"}
        for item in _primary_artifacts(manifest)
    )
    next_step = manifest.get("next_action") or default_next_step(source_status)
    if source_status in {"source_confirmed", "source_partial"} and next_step == "ingest_bundle":
        next_step = "run_evidence_audit"
    if has_media and scope_status == "pending_derivation":
        next_step = "Run ASR for the local media or provide a transcript/subtitle."

    approved_scopes, uncovered_scopes = source_gate.scope_summary(
        {**manifest, "analysis_target": analysis_target}
    )
    failed_probes = manifest.get("failed_probes")
    if not isinstance(failed_probes, list):
        failures = manifest.get("failures")
        failed_probes = list(failures) if isinstance(failures, list) else []

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "source_status": source_status,
        "scope_status": scope_status,
        "pipeline_decision": pipeline_decision_for(source_status),
        "can_enter_full_decomposition": full,
        "can_enter_document_composer": composer,
        "allowed_report_type": report_type,
        "primary_material_available": source_status in {"source_confirmed", "source_partial"},
        "source_classes": sorted(
            {
                str(item.get("source_class"))
                for item in manifest.get("artifacts") or []
                if isinstance(item, dict) and item.get("source_class")
            }
        ),
        "status_reason": status_reason(manifest, source_status, scope_status),
        "failed_probes": failed_probes,
        "acquisition_bundle_status": manifest.get("status") or "",
        "acquisition_layer": manifest.get("acquisition_layer") or "",
        "active_backend": manifest.get("active_backend") or "",
        "run_id": manifest.get("run_id") or "",
        "attempt_id": manifest.get("attempt_id") or "",
        "bundle_id": manifest.get("bundle_id") or "",
        "source_id": manifest.get("source_id") or "",
        "source_fingerprint": manifest.get("source_fingerprint") or "",
        "analysis_target": analysis_target,
        "operation": manifest.get("operation") or "",
        "approved_scope": approved_scopes,
        "uncovered_scopes": uncovered_scopes,
        "next_step": str(next_step),
        "gate_input_sha256": gate_input_sha256,
    }
    if overrides:
        payload.update(overrides)
    require_valid_source_status(payload)
    return payload


def validate_source_status(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(payload))
    if missing:
        errors.append("missing required fields: " + ", ".join(missing))
        return errors

    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    state = payload.get("source_status")
    scope = payload.get("scope_status")
    decision = payload.get("pipeline_decision")
    if state not in SOURCE_STATUSES:
        errors.append(f"invalid source_status: {state!r}")
    if scope not in SCOPE_STATUSES:
        errors.append(f"invalid scope_status: {scope!r}")
    if decision not in PIPELINE_DECISIONS:
        errors.append(f"invalid pipeline_decision: {decision!r}")

    for key in ("can_enter_full_decomposition", "can_enter_document_composer", "primary_material_available"):
        if not isinstance(payload.get(key), bool):
            errors.append(f"{key} must be a boolean")
    for key in ("source_classes", "failed_probes", "approved_scope", "uncovered_scopes"):
        if not isinstance(payload.get(key), list):
            errors.append(f"{key} must be a list")
    for key in (
        "allowed_report_type",
        "status_reason",
        "next_step",
        "acquisition_bundle_status",
        "acquisition_layer",
        "active_backend",
        "run_id",
        "attempt_id",
        "bundle_id",
        "source_id",
        "source_fingerprint",
        "analysis_target",
        "operation",
        "gate_input_sha256",
    ):
        if not isinstance(payload.get(key), str):
            errors.append(f"{key} must be a string")

    if state in SOURCE_STATUSES and isinstance(payload.get("analysis_target"), str):
        expected_full, expected_composer, expected_report = permissions_for_status(
            str(state), str(payload.get("analysis_target") or "auto")
        )
        expected_primary = state in {"source_confirmed", "source_partial"}
        expected_permissions = {
            "can_enter_full_decomposition": expected_full,
            "can_enter_document_composer": expected_composer,
            "primary_material_available": expected_primary,
        }
        for key, expected in expected_permissions.items():
            if payload.get(key) is not expected:
                errors.append(f"{state} requires {key}={str(expected).lower()}")
        if payload.get("allowed_report_type") != expected_report:
            errors.append(f"{state} requires allowed_report_type={expected_report!r}")

    if state == "source_confirmed":
        if scope != "matched" or decision != "continue_full":
            errors.append("source_confirmed requires matched scope and continue_full")
        if not all(payload.get(key) is True for key in ("can_enter_full_decomposition", "can_enter_document_composer", "primary_material_available")):
            errors.append("source_confirmed requires full, composer, and primary permissions")
    elif state == "source_partial":
        if scope != "partial_match" or decision != "continue_partial":
            errors.append("source_partial requires partial_match and continue_partial")
        if not all(payload.get(key) is True for key in ("can_enter_full_decomposition", "can_enter_document_composer", "primary_material_available")):
            errors.append("source_partial requires partial, composer, and primary permissions")
    else:
        if scope in {"matched", "partial_match"}:
            errors.append("non-admitted source statuses cannot declare matched scope")
        if decision != "stop_before_audit":
            errors.append("non-admitted source statuses must stop before audit")

    if scope == "target_mismatch" and state != "degraded_report_only":
        errors.append("target_mismatch requires degraded_report_only compatibility status")

    approved = payload.get("approved_scope")
    uncovered = payload.get("uncovered_scopes")
    if isinstance(approved, list) and isinstance(uncovered, list) and set(approved) & set(uncovered):
        errors.append("approved_scope and uncovered_scopes must not overlap")
    return errors


def require_valid_source_status(payload: dict[str, Any]) -> None:
    errors = validate_source_status(payload)
    if errors:
        raise SourceStatusContractError("; ".join(errors))
