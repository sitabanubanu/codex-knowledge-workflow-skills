#!/usr/bin/env python
"""Validate evidence-bound source reanalysis before learning reconstruction."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

from learning_common import first_text, now_iso, sha256_file


RUNNER_NAME = "knowledge-learning-source-reanalysis-validator"
ALLOWED_REASONS = {
    "upstream_semantic_inventory_incomplete",
    "upstream_inventory_empty",
    "heuristic_segmentation",
    "manual_evidence_reanalysis",
}
SCOPE_ROWS = {
    "source_framing": ("source_framing", "agent_framing_"),
    "concepts": ("concepts", "agent_concept_"),
    "examples": ("examples", "agent_example_"),
    "argument_structure": ("argument_nodes", "agent_argument_"),
}
REPAIR_SCOPE = {
    "source_concepts_empty": "concepts",
    "source_concepts_unanchored": "concepts",
    "source_examples_empty": "examples",
    "source_examples_unanchored": "examples",
    "argument_segments_empty": "argument_structure",
    "argument_segments_unanchored": "argument_structure",
    "argument_segments_heuristic": "argument_structure",
}


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def add_finding(
    findings: list[dict[str, str]], severity: str, code: str, message: str, item_id: str = ""
) -> None:
    findings.append({"severity": severity, "code": code, "message": message, "item_id": item_id})


def normalized_match_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return "".join(char for char in text if char.isalnum())


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def upstream_inventory_issues(
    claims: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> list[str]:
    issues: list[str] = []
    source_claims = [
        row
        for row in claims
        if str(row.get("claim_type") or "") == "source_claim" and isinstance(row.get("evidence_spans"), list) and row.get("evidence_spans")
    ]
    if not source_claims:
        issues.append("source_claims_missing")
    if not concepts:
        issues.append("source_concepts_empty")
    elif not any(isinstance(row.get("evidence_spans"), list) and row.get("evidence_spans") for row in concepts):
        issues.append("source_concepts_unanchored")
    if not examples:
        issues.append("source_examples_empty")
    elif not any(isinstance(row.get("evidence_spans"), list) and row.get("evidence_spans") for row in examples):
        issues.append("source_examples_unanchored")
    if not segments:
        issues.append("argument_segments_empty")
    else:
        if not any(isinstance(row.get("evidence_spans"), list) and row.get("evidence_spans") for row in segments):
            issues.append("argument_segments_unanchored")
        heuristic_text = " ".join(
            " ".join(str(row.get(field) or "") for field in ("title", "summary", "notes"))
            for row in segments
        ).lower()
        if "heuristic" in heuristic_text:
            issues.append("argument_segments_heuristic")
    return issues


def load_source_index(path: Path, findings: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        add_finding(findings, "block", "source_artifact_unreadable", f"Cannot read source artifact: {exc}")
        return rows
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            add_finding(
                findings,
                "block",
                "source_artifact_invalid_jsonl",
                f"Invalid JSONL at line {line_number}: {exc}",
            )
            continue
        if not isinstance(row, dict):
            add_finding(findings, "block", "source_row_not_object", f"Source row {line_number} is not an object")
            continue
        row_id = str(row.get("id") or "").strip()
        text = first_text(row.get("normalized_text"), row.get("text"))
        if not row_id or not text:
            add_finding(
                findings,
                "block",
                "source_row_incomplete",
                f"Source row {line_number} requires id and text",
                row_id,
            )
            continue
        if row_id in rows:
            add_finding(findings, "block", "duplicate_source_id", f"Duplicate source row id: {row_id}", row_id)
            continue
        rows[row_id] = row
    if not rows:
        add_finding(findings, "block", "source_artifact_empty", "Source artifact has no usable evidence rows")
    return rows


def validate_span(
    span: dict[str, Any],
    item_id: str,
    source_index: dict[str, dict[str, Any]],
    findings: list[dict[str, str]],
) -> bool:
    before = len(findings)
    transcript_ids = string_list(span.get("transcript_ids"))
    if not transcript_ids:
        add_finding(findings, "block", "evidence_ids_missing", "Evidence span requires transcript_ids", item_id)
        return False

    missing = [row_id for row_id in transcript_ids if row_id not in source_index]
    if missing:
        add_finding(
            findings,
            "block",
            "evidence_ids_not_found",
            f"Evidence IDs do not exist in admitted source: {missing}",
            item_id,
        )
        return False

    selected = [source_index[row_id] for row_id in transcript_ids]
    starts = [float(row["start"]) for row in selected if is_number(row.get("start"))]
    ends = [float(row["end"]) for row in selected if is_number(row.get("end"))]
    if starts and ends:
        start = span.get("start")
        end = span.get("end")
        if not is_number(start) or not is_number(end) or float(end) < float(start):
            add_finding(
                findings,
                "block",
                "evidence_time_invalid",
                "Timed source evidence requires a valid start/end range",
                item_id,
            )
        elif float(start) > min(starts) + 0.35 or float(end) < max(ends) - 0.35:
            add_finding(
                findings,
                "block",
                "evidence_time_mismatch",
                f"Evidence range {start}-{end} does not cover referenced rows {min(starts)}-{max(ends)}",
                item_id,
            )

    excerpt = first_text(span.get("verbatim_excerpt"))
    normalized_excerpt = normalized_match_text(excerpt)
    if len(normalized_excerpt) < 6:
        add_finding(
            findings,
            "block",
            "verbatim_excerpt_missing",
            "Each reanalysis evidence span requires a verbatim_excerpt of at least 6 normalized characters",
            item_id,
        )
    else:
        selected_text = normalized_match_text(
            " ".join(first_text(row.get("normalized_text"), row.get("text")) for row in selected)
        )
        if normalized_excerpt not in selected_text:
            add_finding(
                findings,
                "block",
                "verbatim_excerpt_mismatch",
                "verbatim_excerpt is not present in the referenced source rows",
                item_id,
            )
    return len(findings) == before


def validate_reanalysis_row(
    row: dict[str, Any],
    scope: str,
    required_prefix: str,
    source_index: dict[str, dict[str, Any]],
    claim_ids: set[str],
    upstream_ids: set[str],
    findings: list[dict[str, str]],
) -> dict[str, Any]:
    before = len(findings)
    item_id = str(row.get("id") or "").strip()
    if not item_id:
        add_finding(findings, "block", "reanalysis_id_missing", f"{scope} row requires an id")
        item_id = "<missing>"
    elif not item_id.startswith(required_prefix):
        add_finding(
            findings,
            "block",
            "reanalysis_id_namespace",
            f"New {scope} id must start with {required_prefix}",
            item_id,
        )
    elif item_id in upstream_ids:
        add_finding(
            findings,
            "block",
            "reanalysis_overwrites_upstream",
            "Reanalysis rows may not overwrite an upstream inventory ID",
            item_id,
        )

    allowed_categories = {"Source", "Inference"} if scope == "source_framing" else {"Source"}
    if str(row.get("category") or "") not in allowed_categories:
        add_finding(
            findings,
            "block",
            "reanalysis_category_invalid",
            f"Category for {scope} must be one of {sorted(allowed_categories)}",
            item_id,
        )

    required_fields = {
        "source_framing": ("field", "text"),
        "concepts": ("term", "definition", "why_it_matters"),
        "examples": ("name", "what_it_is", "why_introduced", "what_it_supports"),
        "argument_structure": ("title", "summary"),
    }[scope]
    missing_fields = [field for field in required_fields if not first_text(row.get(field))]
    if missing_fields:
        add_finding(
            findings,
            "block",
            "reanalysis_content_incomplete",
            f"Required fields are empty: {missing_fields}",
            item_id,
        )

    rationale = first_text(row.get("support_rationale"))
    if len(normalized_match_text(rationale)) < 8:
        add_finding(
            findings,
            "block",
            "support_rationale_missing",
            "Each reanalysis evidence row requires an explicit support_rationale",
            item_id,
        )

    linked_claim_ids = string_list(row.get("source_claim_ids"))
    missing_claims = [claim_id for claim_id in linked_claim_ids if claim_id not in claim_ids]
    if missing_claims:
        add_finding(
            findings,
            "block",
            "source_claim_id_not_found",
            f"Referenced source claim IDs do not exist: {missing_claims}",
            item_id,
        )

    spans = row.get("evidence_spans") if isinstance(row.get("evidence_spans"), list) else []
    if not spans:
        add_finding(
            findings,
            "block",
            "reanalysis_evidence_missing",
            "Each reanalysis evidence row requires evidence_spans",
            item_id,
        )
    valid_spans = 0
    for span in spans:
        if isinstance(span, dict) and validate_span(span, item_id, source_index, findings):
            valid_spans += 1

    return {
        "id": item_id,
        "scope": scope,
        "status": "pass" if len(findings) == before else "block",
        "evidence_spans": len(spans),
        "valid_evidence_spans": valid_spans,
        "support_rationale_present": bool(rationale),
    }


def validate_source_reanalysis(
    project_root: Path,
    gate_receipt: dict[str, Any],
    enrichment: dict[str, Any],
    claims: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return an auditable fail-closed report for normal or reanalysis mode."""

    project_root = project_root.expanduser().resolve()
    findings: list[dict[str, str]] = []
    row_checks: list[dict[str, Any]] = []
    detected_issues = upstream_inventory_issues(claims, concepts, examples, segments)
    config = enrichment.get("source_reanalysis") if isinstance(enrichment.get("source_reanalysis"), dict) else {}
    agent_rows_present = any(
        isinstance(enrichment.get(key), list) and any(isinstance(row, dict) for row in enrichment.get(key, []))
        for key in ("source_framing", "concepts", "examples", "argument_nodes")
    )
    legacy_framing = [
        key
        for key in ("core_question", "thesis", "source_structure_summary")
        if first_text(enrichment.get(key))
    ]
    if legacy_framing:
        add_finding(
            findings,
            "block",
            "unvalidated_source_framing",
            f"Source framing must use evidence-bound source_framing rows, not free-text fields: {legacy_framing}",
        )

    mode = "evidence_bound" if config else "normal"
    source_artifact = ""
    source_artifact_sha256 = ""
    scopes: list[str] = []
    outcomes: dict[str, str] = {}

    if not config:
        if agent_rows_present:
            add_finding(
                findings,
                "block",
                "undeclared_source_reanalysis",
                "Agent-authored Source inventories require an explicit source_reanalysis contract",
            )
        for issue in detected_issues:
            add_finding(
                findings,
                "block",
                issue,
                "Upstream semantic inventory is incomplete; run evidence-bound source reanalysis or repair upstream analysis",
            )
    else:
        declared_mode = str(config.get("mode") or "")
        if declared_mode != "evidence_bound":
            add_finding(findings, "block", "reanalysis_mode_invalid", "source_reanalysis.mode must be evidence_bound")
        reason = str(config.get("reason") or "")
        if reason not in ALLOWED_REASONS:
            add_finding(
                findings,
                "block",
                "reanalysis_reason_invalid",
                f"source_reanalysis.reason must be one of {sorted(ALLOWED_REASONS)}",
            )
        scopes = string_list(config.get("scopes"))
        invalid_scopes = [scope for scope in scopes if scope not in SCOPE_ROWS]
        if not scopes or invalid_scopes:
            add_finding(
                findings,
                "block",
                "reanalysis_scopes_invalid",
                f"Reanalysis scopes must be chosen from {sorted(SCOPE_ROWS)}; invalid={invalid_scopes}",
            )
        if "source_framing" not in scopes:
            add_finding(
                findings,
                "block",
                "source_framing_scope_missing",
                "Evidence-bound reanalysis requires the source_framing scope",
            )

        raw_outcomes = config.get("inventory_outcomes")
        outcomes = {str(key): str(value) for key, value in raw_outcomes.items()} if isinstance(raw_outcomes, dict) else {}
        notes = config.get("inventory_notes") if isinstance(config.get("inventory_notes"), dict) else {}
        for issue in detected_issues:
            required_scope = REPAIR_SCOPE.get(issue)
            if required_scope and required_scope not in scopes:
                add_finding(
                    findings,
                    "block",
                    "reanalysis_scope_missing",
                    f"Detected issue {issue} requires scope {required_scope}",
                )
            elif required_scope is None:
                add_finding(
                    findings,
                    "block",
                    issue,
                    "This upstream failure cannot be repaired inside Learning Article",
                )

        source_value = str(config.get("source_artifact") or "").strip()
        source_index: dict[str, dict[str, Any]] = {}
        if not source_value:
            add_finding(
                findings,
                "block",
                "source_artifact_missing",
                "Evidence-bound reanalysis requires a project-relative source_artifact",
            )
        else:
            candidate = Path(source_value)
            if candidate.is_absolute():
                add_finding(
                    findings,
                    "block",
                    "source_artifact_not_relative",
                    "source_artifact must be project-relative",
                )
            else:
                resolved = (project_root / candidate).resolve()
                try:
                    resolved.relative_to(project_root)
                except ValueError:
                    add_finding(
                        findings,
                        "block",
                        "source_artifact_outside_project",
                        "source_artifact must remain inside the workflow project",
                    )
                else:
                    source_artifact = candidate.as_posix()
                    if not resolved.is_file():
                        add_finding(
                            findings,
                            "block",
                            "source_artifact_not_found",
                            f"Declared source artifact does not exist: {source_artifact}",
                        )
                    else:
                        source_artifact_sha256 = sha256_file(resolved)
                        admitted_artifacts = (
                            gate_receipt.get("derived_artifacts")
                            if isinstance(gate_receipt.get("derived_artifacts"), list)
                            else []
                        )
                        admitted = any(
                            isinstance(row, dict)
                            and str(row.get("path") or "").replace("\\", "/") == source_artifact
                            and str(row.get("sha256") or "") == source_artifact_sha256
                            for row in admitted_artifacts
                        )
                        if not admitted:
                            add_finding(
                                findings,
                                "block",
                                "source_artifact_not_admitted",
                                "Declared source artifact path and hash are not admitted by the current gate receipt",
                            )
                        source_index = load_source_index(resolved, findings)

        upstream_ids_by_scope = {
            "source_framing": set(),
            "concepts": {str(row.get("id")) for row in concepts if row.get("id")},
            "examples": {str(row.get("id")) for row in examples if row.get("id")},
            "argument_structure": {str(row.get("id")) for row in segments if row.get("id")},
        }
        claim_ids = {str(row.get("id")) for row in claims if row.get("id")}
        rows_by_scope: dict[str, list[dict[str, Any]]] = {}
        for scope, (key, required_prefix) in SCOPE_ROWS.items():
            rows = [row for row in enrichment.get(key, []) if isinstance(row, dict)] if isinstance(enrichment.get(key), list) else []
            rows_by_scope[scope] = rows
            if rows and scope not in scopes:
                add_finding(
                    findings,
                    "block",
                    "reanalysis_rows_outside_scope",
                    f"{key} contains reanalysis rows but scope {scope} was not declared",
                )
            if scope not in scopes:
                continue
            outcome = outcomes.get(scope, "")
            allowed_outcomes = {"reconstructed"}
            if scope == "examples":
                allowed_outcomes.add("none_identified_in_source")
            if outcome not in allowed_outcomes:
                add_finding(
                    findings,
                    "block",
                    "inventory_outcome_invalid",
                    f"Outcome for {scope} must be one of {sorted(allowed_outcomes)}",
                )
            if outcome == "reconstructed" and not rows:
                add_finding(
                    findings,
                    "block",
                    "reanalysis_rows_missing",
                    f"Outcome reconstructed requires at least one {key} row",
                )
            if outcome == "none_identified_in_source":
                if rows:
                    add_finding(
                        findings,
                        "block",
                        "none_outcome_has_rows",
                        "none_identified_in_source cannot be combined with reconstructed example rows",
                    )
                if len(normalized_match_text(notes.get(scope))) < 8:
                    add_finding(
                        findings,
                        "block",
                        "none_outcome_rationale_missing",
                        "none_identified_in_source requires an inventory_notes rationale",
                    )
            for row in rows:
                row_checks.append(
                    validate_reanalysis_row(
                        row,
                        scope,
                        required_prefix,
                        source_index,
                        claim_ids,
                        upstream_ids_by_scope[scope],
                        findings,
                    )
                )

        framing_rows = rows_by_scope.get("source_framing", [])
        framing_fields = [str(row.get("field") or "") for row in framing_rows]
        required_framing = {"core_question", "thesis", "source_structure_summary"}
        missing_framing = sorted(required_framing - set(framing_fields))
        invalid_framing = sorted(set(framing_fields) - required_framing)
        duplicate_framing = sorted({field for field in framing_fields if field and framing_fields.count(field) > 1})
        if missing_framing or invalid_framing or duplicate_framing:
            add_finding(
                findings,
                "block",
                "source_framing_fields_invalid",
                f"source_framing requires one row for each field; missing={missing_framing}, invalid={invalid_framing}, duplicate={duplicate_framing}",
            )

        concept_ids = upstream_ids_by_scope["concepts"] | {
            str(row.get("id")) for row in rows_by_scope.get("concepts", []) if row.get("id")
        }
        example_ids = upstream_ids_by_scope["examples"] | {
            str(row.get("id")) for row in rows_by_scope.get("examples", []) if row.get("id")
        }
        argument_ids = {
            str(row.get("id")) for row in rows_by_scope.get("argument_structure", []) if row.get("id")
        }
        for row in rows_by_scope.get("concepts", []):
            item_id = str(row.get("id") or "")
            for example_id in string_list(row.get("linked_example_ids")):
                if example_id not in example_ids:
                    add_finding(findings, "block", "linked_example_not_found", f"Unknown example id: {example_id}", item_id)
            relationships = row.get("relationships") if isinstance(row.get("relationships"), list) else []
            for relation in relationships:
                target_id = str(relation.get("target_id") or "") if isinstance(relation, dict) else ""
                if target_id and target_id not in concept_ids:
                    add_finding(findings, "block", "relationship_target_not_found", f"Unknown concept id: {target_id}", item_id)
        for row in rows_by_scope.get("examples", []):
            item_id = str(row.get("id") or "")
            for concept_id in string_list(row.get("linked_concept_ids")):
                if concept_id not in concept_ids:
                    add_finding(findings, "block", "linked_concept_not_found", f"Unknown concept id: {concept_id}", item_id)
        edges = enrichment.get("argument_edges") if isinstance(enrichment.get("argument_edges"), list) else []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            left = str(edge.get("from") or "")
            right = str(edge.get("to") or "")
            if left not in argument_ids or right not in argument_ids:
                add_finding(
                    findings,
                    "block",
                    "argument_edge_target_not_found",
                    f"Argument edge references unknown nodes: {left} -> {right}",
                )

    blocking = [row for row in findings if row["severity"] == "block"]
    return {
        "schema_version": "learning-source-reanalysis-validation.v1",
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "mode": mode,
        "requested": bool(config),
        "approved_for_learning_analysis": not blocking,
        "detected_upstream_issues": detected_issues,
        "declared_scopes": scopes,
        "inventory_outcomes": outcomes,
        "source_artifact": source_artifact,
        "source_artifact_sha256": source_artifact_sha256,
        "rows_checked": len(row_checks),
        "spans_checked": sum(int(row.get("evidence_spans") or 0) for row in row_checks),
        "row_checks": row_checks,
        "findings": findings,
        "blocking_codes": sorted({row["code"] for row in blocking}),
        "semantic_support_policy": "Every reconstructed Source row and every Source/Inference framing row has a verbatim admitted-source anchor and an explicit Agent support rationale; deterministic validation does not replace human/Agent semantic judgment.",
    }
