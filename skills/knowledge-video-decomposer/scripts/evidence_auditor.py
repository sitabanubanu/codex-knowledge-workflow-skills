#!/usr/bin/env python
"""Audit evidence coverage before building a video analysis pack."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import artifact_validator
from write_artifact import write_artifact


RUNNER_NAME = "knowledge-video-evidence-auditor"
ALLOWED_SOURCE_STATUSES = {"source_confirmed", "source_partial"}
FULL_PACK_STATUS = "source_confirmed"
PARTIAL_PACK_STATUS = "source_partial"
CLAIM_TYPES = {"source_claim", "inferred_claim", "uncertain_claim"}
NODE_TYPES = {"claim", "example", "concept", "analogy", "conclusion", "question"}
EDGE_TYPES = {"supports", "explains", "contrasts", "leads_to", "defines", "analogizes"}


class EvidenceAuditError(Exception):
    """Expected CLI-facing evidence audit failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def write_json(path: Path, payload: Any, *, pretty: bool = True) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None)
    return write_artifact(path, text, json_mode=True, mkdirs=True, overwrite=True)


def write_text(path: Path, text: str) -> dict[str, Any]:
    return write_artifact(path, text, mkdirs=True, overwrite=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise EvidenceAuditError(f"invalid JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise EvidenceAuditError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise EvidenceAuditError(f"JSON file is not an object: {path}")
    return payload


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise EvidenceAuditError(f"could not read JSONL file {path}: {exc}") from exc
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvidenceAuditError(f"invalid JSONL line {index} in {path}: {exc}") from exc
        if not isinstance(row, dict):
            raise EvidenceAuditError(f"JSONL line {index} in {path} is not an object")
        rows.append(row)
    return rows


def add_finding(
    findings: list[dict[str, Any]],
    severity: str,
    code: str,
    message: str,
    *,
    file: str | None = None,
    item_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    row: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if file:
        row["file"] = file
    if item_id:
        row["item_id"] = item_id
    if details:
        row["details"] = details
    findings.append(row)


def load_source_status(path: Path) -> dict[str, Any]:
    status = read_json(path)
    source_status = status.get("source_status")
    if source_status not in ALLOWED_SOURCE_STATUSES:
        raise EvidenceAuditError(
            f"evidence audit requires source_confirmed or source_partial; got {source_status!r}"
        )
    if not status.get("primary_material_available"):
        raise EvidenceAuditError("evidence audit requires primary_material_available=true")
    return status


def require_file(path: Path, findings: list[dict[str, Any]], label: str) -> bool:
    if path.is_file():
        return True
    add_finding(
        findings,
        "error",
        "required_artifact_missing",
        f"Required artifact is missing: {label}.",
        file=str(path),
    )
    return False


def span_transcript_ids(span: Any) -> list[str]:
    if not isinstance(span, dict):
        return []
    tids = span.get("transcript_ids")
    if isinstance(tids, list):
        return [str(item) for item in tids if str(item).strip()]
    return []


def audit_evidence_spans(
    *,
    item: dict[str, Any],
    item_id: str,
    item_kind: str,
    transcript_ids: set[str],
    findings: list[dict[str, Any]],
    file: str,
    require_non_empty: bool = True,
) -> None:
    spans = item.get("evidence_spans")
    if not isinstance(spans, list):
        add_finding(
            findings,
            "error",
            "evidence_spans_not_list",
            f"{item_kind} must have evidence_spans as a list.",
            file=file,
            item_id=item_id,
        )
        return
    if require_non_empty and not spans:
        add_finding(
            findings,
            "error",
            "evidence_spans_empty",
            f"{item_kind} has no evidence spans.",
            file=file,
            item_id=item_id,
        )
        return
    for index, span in enumerate(spans, start=1):
        tids = span_transcript_ids(span)
        if not tids:
            add_finding(
                findings,
                "warning",
                "evidence_span_without_transcript_ids",
                f"{item_kind} evidence span {index} has no transcript_ids.",
                file=file,
                item_id=item_id,
            )
            continue
        unknown = sorted(tid for tid in tids if tid not in transcript_ids)
        if unknown:
            add_finding(
                findings,
                "error",
                "evidence_span_unknown_transcript_ids",
                f"{item_kind} evidence span references transcript IDs not present in clean_transcript.jsonl.",
                file=file,
                item_id=item_id,
                details={"unknown_transcript_ids": unknown},
            )


def load_list_file(
    path: Path,
    key: str,
    findings: list[dict[str, Any]],
    label: str,
) -> list[dict[str, Any]]:
    if not require_file(path, findings, label):
        return []
    try:
        payload = read_json(path)
    except EvidenceAuditError as exc:
        add_finding(findings, "error", "artifact_unreadable", str(exc), file=str(path))
        return []
    values = payload.get(key)
    if not isinstance(values, list):
        add_finding(
            findings,
            "error",
            "artifact_list_missing",
            f"{path.name} must contain a {key} list.",
            file=str(path),
        )
        return []
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            add_finding(
                findings,
                "error",
                "artifact_item_not_object",
                f"{path.name} item {index} is not an object.",
                file=str(path),
            )
            continue
        item_id = str(value.get("id") or "").strip()
        if not item_id:
            add_finding(
                findings,
                "error",
                "artifact_item_missing_id",
                f"{path.name} item {index} is missing id.",
                file=str(path),
            )
            continue
        if item_id in seen:
            add_finding(
                findings,
                "error",
                "artifact_item_duplicate_id",
                f"{path.name} contains duplicate id {item_id}.",
                file=str(path),
                item_id=item_id,
            )
        seen.add(item_id)
        items.append(value)
    return items


def audit_transcript(path: Path, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not require_file(path, findings, "01_transcript/clean_transcript.jsonl"):
        return []
    try:
        rows = read_jsonl(path)
    except EvidenceAuditError as exc:
        add_finding(findings, "error", "transcript_unreadable", str(exc), file=str(path))
        return []
    if not rows:
        add_finding(findings, "error", "transcript_empty", "Clean transcript has no rows.", file=str(path))
        return []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        row_id = str(row.get("id") or "").strip()
        text = str(row.get("normalized_text") or row.get("text") or "").strip()
        if not row_id:
            add_finding(findings, "error", "transcript_row_missing_id", "Transcript row is missing id.", file=str(path))
            continue
        if row_id in seen:
            add_finding(
                findings,
                "error",
                "transcript_row_duplicate_id",
                "Transcript row id is duplicated.",
                file=str(path),
                item_id=row_id,
            )
        seen.add(row_id)
        if not text:
            add_finding(
                findings,
                "error",
                "transcript_row_empty_text",
                "Transcript row has no text.",
                file=str(path),
                item_id=row_id,
                details={"line": index},
            )
    return rows


def audit_argument_segments(
    path: Path,
    transcript_ids: set[str],
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    segments = load_list_file(path, "segments", findings, "02_segments/argument_segments.json")
    seen_segment_ids: set[str] = set()
    for segment in segments:
        segment_id = str(segment.get("id"))
        seen_segment_ids.add(segment_id)
        tids = segment.get("transcript_ids")
        if not isinstance(tids, list) or not tids:
            add_finding(
                findings,
                "error",
                "segment_transcript_ids_missing",
                "Argument segment has no transcript_ids.",
                file=str(path),
                item_id=segment_id,
            )
        else:
            unknown = sorted(str(tid) for tid in tids if str(tid) not in transcript_ids)
            if unknown:
                add_finding(
                    findings,
                    "error",
                    "segment_unknown_transcript_ids",
                    "Argument segment references transcript IDs not present in clean_transcript.jsonl.",
                    file=str(path),
                    item_id=segment_id,
                    details={"unknown_transcript_ids": unknown},
                )
        audit_evidence_spans(
            item=segment,
            item_id=segment_id,
            item_kind="argument segment",
            transcript_ids=transcript_ids,
            findings=findings,
            file=str(path),
        )
    return segments


def audit_inventory(
    output_root: Path,
    transcript_ids: set[str],
    segment_ids: set[str],
    findings: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    inventory_dir = output_root / "03_inventory"
    inventory = {
        "concepts": load_list_file(inventory_dir / "concepts.json", "concepts", findings, "03_inventory/concepts.json"),
        "examples": load_list_file(inventory_dir / "examples.json", "examples", findings, "03_inventory/examples.json"),
        "claims": load_list_file(inventory_dir / "claims.json", "claims", findings, "03_inventory/claims.json"),
        "analogies": load_list_file(inventory_dir / "analogies.json", "analogies", findings, "03_inventory/analogies.json"),
    }
    claim_ids = {str(item.get("id")) for item in inventory["claims"]}
    example_ids = {str(item.get("id")) for item in inventory["examples"]}
    for key, items in inventory.items():
        file = str(inventory_dir / f"{key}.json")
        for item in items:
            item_id = str(item.get("id"))
            audit_evidence_spans(
                item=item,
                item_id=item_id,
                item_kind=key.rstrip("s"),
                transcript_ids=transcript_ids,
                findings=findings,
                file=file,
            )
            item_segment_ids = item.get("source_argument_segment_ids", [])
            if isinstance(item_segment_ids, list):
                unknown_segments = sorted(str(seg_id) for seg_id in item_segment_ids if str(seg_id) not in segment_ids)
                if unknown_segments:
                    add_finding(
                        findings,
                        "error",
                        "inventory_unknown_argument_segment_ids",
                        "Inventory item references source_argument_segment_ids not present in argument_segments.json.",
                        file=file,
                        item_id=item_id,
                        details={"unknown_segment_ids": unknown_segments},
                    )
    for claim in inventory["claims"]:
        claim_id = str(claim.get("id"))
        claim_type = claim.get("claim_type")
        if claim_type not in CLAIM_TYPES:
            add_finding(
                findings,
                "error",
                "claim_type_invalid",
                "Claim has an unknown claim_type.",
                file=str(inventory_dir / "claims.json"),
                item_id=claim_id,
                details={"claim_type": claim_type, "allowed": sorted(CLAIM_TYPES)},
            )
        linked_examples = claim.get("linked_example_ids", [])
        if isinstance(linked_examples, list):
            unknown_examples = sorted(str(ex_id) for ex_id in linked_examples if str(ex_id) not in example_ids)
            if unknown_examples:
                add_finding(
                    findings,
                    "error",
                    "claim_unknown_linked_example_ids",
                    "Claim references examples not present in examples.json.",
                    file=str(inventory_dir / "claims.json"),
                    item_id=claim_id,
                    details={"unknown_example_ids": unknown_examples},
                )
    for example in inventory["examples"]:
        example_id = str(example.get("id"))
        linked_claims = example.get("linked_claim_ids", [])
        if isinstance(linked_claims, list):
            unknown_claims = sorted(str(claim_id) for claim_id in linked_claims if str(claim_id) not in claim_ids)
            if unknown_claims:
                add_finding(
                    findings,
                    "error",
                    "example_unknown_linked_claim_ids",
                    "Example references claims not present in claims.json.",
                    file=str(inventory_dir / "examples.json"),
                    item_id=example_id,
                    details={"unknown_claim_ids": unknown_claims},
                )
    for concept in inventory["concepts"]:
        if not str(concept.get("definition_in_source") or "").strip():
            add_finding(
                findings,
                "warning",
                "concept_definition_missing",
                "Concept has no source-local definition; keep it as a candidate in the final pack.",
                file=str(inventory_dir / "concepts.json"),
                item_id=str(concept.get("id")),
            )
    for analogy in inventory["analogies"]:
        mapping = analogy.get("mapping")
        if mapping == []:
            add_finding(
                findings,
                "warning",
                "analogy_mapping_empty",
                "Analogy has no explicit source-to-target mapping.",
                file=str(inventory_dir / "analogies.json"),
                item_id=str(analogy.get("id")),
            )
    return inventory


def audit_logic(
    output_root: Path,
    transcript_ids: set[str],
    inventory_ids: set[str],
    segment_ids: set[str],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    source_logic_path = output_root / "04_logic" / "source_logic.md"
    logic_graph_path = output_root / "04_logic" / "logic_graph.json"
    if require_file(source_logic_path, findings, "04_logic/source_logic.md"):
        try:
            text = source_logic_path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            add_finding(findings, "error", "source_logic_unreadable", str(exc), file=str(source_logic_path))
        else:
            lowered = text.lower()
            if "source boundary" not in lowered:
                add_finding(
                    findings,
                    "warning",
                    "source_logic_boundary_missing",
                    "source_logic.md does not explicitly state the source boundary.",
                    file=str(source_logic_path),
                )
            for marker in ("external theory", "downstream interpretation", "outside critique"):
                if marker in lowered and "does not add" not in lowered:
                    add_finding(
                        findings,
                        "warning",
                        "source_logic_possible_extension_language",
                        "source_logic.md contains language that may belong downstream, not in source logic.",
                        file=str(source_logic_path),
                        details={"marker": marker},
                    )
    graph: dict[str, Any] = {}
    if not require_file(logic_graph_path, findings, "04_logic/logic_graph.json"):
        return graph
    try:
        graph = read_json(logic_graph_path)
    except EvidenceAuditError as exc:
        add_finding(findings, "error", "logic_graph_unreadable", str(exc), file=str(logic_graph_path))
        return {}
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list):
        add_finding(findings, "error", "logic_graph_nodes_missing", "logic_graph.json must contain a nodes list.", file=str(logic_graph_path))
        nodes = []
    if not isinstance(edges, list):
        add_finding(findings, "error", "logic_graph_edges_missing", "logic_graph.json must contain an edges list.", file=str(logic_graph_path))
        edges = []
    node_ids: set[str] = set()
    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            add_finding(findings, "error", "logic_node_not_object", f"Logic node {index} is not an object.", file=str(logic_graph_path))
            continue
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            add_finding(findings, "error", "logic_node_missing_id", f"Logic node {index} is missing id.", file=str(logic_graph_path))
            continue
        if node_id in node_ids:
            add_finding(findings, "error", "logic_node_duplicate_id", "Logic node id is duplicated.", file=str(logic_graph_path), item_id=node_id)
        node_ids.add(node_id)
        if node.get("type") not in NODE_TYPES:
            add_finding(
                findings,
                "error",
                "logic_node_type_invalid",
                "Logic node has an unknown type.",
                file=str(logic_graph_path),
                item_id=node_id,
                details={"node_type": node.get("type"), "allowed": sorted(NODE_TYPES)},
            )
        source_segment_ids = node.get("source_argument_segment_ids", [])
        if isinstance(source_segment_ids, list):
            unknown_segments = sorted(str(seg_id) for seg_id in source_segment_ids if str(seg_id) not in segment_ids)
            if unknown_segments:
                add_finding(
                    findings,
                    "error",
                    "logic_node_unknown_argument_segment_ids",
                    "Logic node references argument segments not present in argument_segments.json.",
                    file=str(logic_graph_path),
                    item_id=node_id,
                    details={"unknown_segment_ids": unknown_segments},
                )
        if not node_id.startswith("arg_") and node_id not in inventory_ids:
            add_finding(
                findings,
                "warning",
                "logic_node_not_inventory_or_argument",
                "Logic node does not correspond to an inventory item or argument segment node.",
                file=str(logic_graph_path),
                item_id=node_id,
            )
        audit_evidence_spans(
            item=node,
            item_id=node_id,
            item_kind="logic node",
            transcript_ids=transcript_ids,
            findings=findings,
            file=str(logic_graph_path),
        )
    for index, edge in enumerate(edges, start=1):
        if not isinstance(edge, dict):
            add_finding(findings, "error", "logic_edge_not_object", f"Logic edge {index} is not an object.", file=str(logic_graph_path))
            continue
        edge_id = str(edge.get("id") or f"edge_{index}").strip()
        source = str(edge.get("source") or "").strip()
        target = str(edge.get("target") or "").strip()
        if edge.get("type") not in EDGE_TYPES:
            add_finding(
                findings,
                "error",
                "logic_edge_type_invalid",
                "Logic edge has an unknown type.",
                file=str(logic_graph_path),
                item_id=edge_id,
                details={"edge_type": edge.get("type"), "allowed": sorted(EDGE_TYPES)},
            )
        unknown_nodes = [node_id for node_id in (source, target) if node_id not in node_ids]
        if unknown_nodes:
            add_finding(
                findings,
                "error",
                "logic_edge_unknown_node_ids",
                "Logic edge references nodes not present in logic_graph.json.",
                file=str(logic_graph_path),
                item_id=edge_id,
                details={"unknown_node_ids": unknown_nodes},
            )
    return graph


def severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for finding in findings:
        severity = str(finding.get("severity") or "info")
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def render_gap_check(audit: dict[str, Any]) -> str:
    findings = audit["findings"]
    errors = [finding for finding in findings if finding.get("severity") == "error"]
    warnings = [finding for finding in findings if finding.get("severity") == "warning"]

    def render_items(items: list[dict[str, Any]]) -> list[str]:
        if not items:
            return ["- None recorded."]
        lines: list[str] = []
        for item in items:
            location = f" `{item.get('file')}`" if item.get("file") else ""
            item_ref = f" `{item.get('item_id')}`" if item.get("item_id") else ""
            lines.append(f"- `{item.get('code')}`{item_ref}{location}: {item.get('message')}")
        return lines

    pack_gate = audit["pack_gate"]
    lines = [
        "# Gap Check",
        "",
        "## Evidence Audit Summary",
        "",
        f"- Source status: `{audit['source_status']}`",
        f"- Errors: `{audit['severity_counts'].get('error', 0)}`",
        f"- Warnings: `{audit['severity_counts'].get('warning', 0)}`",
        f"- Can build full video_analysis_pack: `{str(pack_gate['can_build_video_analysis_pack']).lower()}`",
        f"- Can build partial video_analysis_pack: `{str(pack_gate['can_build_partial_pack']).lower()}`",
        f"- Next step: `{pack_gate['next_step']}`",
        "",
        "## Missing or Weak Evidence",
        "",
        *render_items(errors),
        "",
        "## Unexplained Concepts",
        "",
        *render_items([item for item in warnings if item.get("code") == "concept_definition_missing"]),
        "",
        "## Incomplete Examples",
        "",
        *render_items([item for item in warnings if item.get("code") in {"evidence_span_without_transcript_ids"}]),
        "",
        "## Reasoning Jumps",
        "",
        *render_items([item for item in findings if str(item.get("code", "")).startswith("logic_edge")]),
        "",
        "## Source / Inference / Extension Risks",
        "",
        *render_items(
            [
                item
                for item in warnings
                if item.get("code") in {"source_logic_boundary_missing", "source_logic_possible_extension_language"}
            ]
        ),
        "",
        "## Acquisition Issues",
        "",
        "- Acquisition status is read from `00_source/source_status.json`; no new acquisition probing was performed in this stage.",
        "",
        "## Downstream Notes",
        "",
        "- This auditor does not create `video_analysis_pack.md`.",
        "- Build the final pack only when the pack gate allows it, and carry warnings into downstream document composition.",
        "",
    ]
    return "\n".join(lines)


def build_pack_gate(source_status: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    has_errors = any(finding.get("severity") == "error" for finding in findings)
    can_full = source_status == FULL_PACK_STATUS and not has_errors
    can_partial = source_status == PARTIAL_PACK_STATUS and not has_errors
    if can_full:
        next_step = "enter_video_analysis_pack_builder"
    elif can_partial:
        next_step = "enter_partial_video_analysis_pack_builder"
    else:
        next_step = "fix_evidence_audit_findings"
    return {
        "can_build_video_analysis_pack": can_full,
        "can_build_partial_pack": can_partial,
        "next_step": next_step,
    }


def run_evidence_audit(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.expanduser().resolve()
    source_status_path = args.source_status or output_root / "00_source" / "source_status.json"
    source_status = load_source_status(source_status_path)
    findings: list[dict[str, Any]] = []

    transcript = audit_transcript(output_root / "01_transcript" / "clean_transcript.jsonl", findings)
    transcript_ids = {str(row.get("id")) for row in transcript if row.get("id")}
    argument_segments = audit_argument_segments(output_root / "02_segments" / "argument_segments.json", transcript_ids, findings)
    segment_ids = {str(segment.get("id")) for segment in argument_segments if segment.get("id")}
    inventory = audit_inventory(output_root, transcript_ids, segment_ids, findings)
    inventory_ids = {
        str(item.get("id"))
        for values in inventory.values()
        for item in values
        if item.get("id")
    }
    graph = audit_logic(output_root, transcript_ids, inventory_ids, segment_ids, findings)

    if (output_root / "video_analysis_pack.md").exists():
        add_finding(
            findings,
            "warning",
            "pack_already_exists",
            "video_analysis_pack.md already exists; ensure it is rebuilt after this audit rather than treated as pre-audited.",
            file=str(output_root / "video_analysis_pack.md"),
        )

    counts = severity_counts(findings)
    pack_gate = build_pack_gate(str(source_status.get("source_status")), findings)
    audit = {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "output_root": str(output_root),
        "source_status": source_status.get("source_status"),
        "source_status_path": str(source_status_path.expanduser().resolve()),
        "counts": {
            "transcript_rows": len(transcript),
            "argument_segments": len(argument_segments),
            "concepts": len(inventory["concepts"]),
            "examples": len(inventory["examples"]),
            "claims": len(inventory["claims"]),
            "analogies": len(inventory["analogies"]),
            "logic_nodes": len(graph.get("nodes", [])) if isinstance(graph.get("nodes"), list) else 0,
            "logic_edges": len(graph.get("edges", [])) if isinstance(graph.get("edges"), list) else 0,
        },
        "severity_counts": counts,
        "findings": findings,
        "pack_gate": pack_gate,
    }
    written = [
        write_json(output_root / "05_gap_check" / "evidence_audit.json", audit),
        write_text(output_root / "05_gap_check" / "gap_check.md", render_gap_check(audit)),
    ]
    validation = artifact_validator.validate_artifact_root(
        output_root,
        source_status_path,
        mode="strict",
    )
    return {
        "runner": RUNNER_NAME,
        "output_root": str(output_root),
        "source_status": source_status.get("source_status"),
        "severity_counts": counts,
        "pack_gate": pack_gate,
        "files_written": [item["path"] for item in written],
        "validation": validation,
        "next_step": pack_gate["next_step"],
        "validation_next_step": validation.get("next_step"),
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit evidence coverage before writing video_analysis_pack.md.")
    parser.add_argument("--output-root", type=Path, required=False, help="Artifact root containing transcript, segments, inventory, and logic artifacts.")
    parser.add_argument("--source-status", type=Path, default=None, help="Optional source_status.json override.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def span(tids: list[str], quote: str, start: float, end: float) -> dict[str, Any]:
    return {
        "transcript_ids": tids,
        "start": start,
        "end": end,
        "quote": quote,
        "source": "clean_transcript",
    }


def write_status(path: Path, *, source_status: str = "source_confirmed", primary: bool = True) -> None:
    if source_status == "source_confirmed":
        allowed_report_type = "full_video_analysis_pack"
    elif source_status == "source_partial":
        allowed_report_type = "partial_video_analysis_pack"
    else:
        allowed_report_type = "degraded_source_report"
    write_json(
        path,
        {
            "source_status": source_status,
            "can_enter_full_decomposition": source_status in ALLOWED_SOURCE_STATUSES,
            "can_enter_document_composer": True,
            "allowed_report_type": allowed_report_type,
            "source_classes": ["primary_transcript"] if primary else [],
            "primary_material_available": primary,
            "status_reason": "self-test status",
            "failed_probes": [],
            "next_step": "enter_gap_evidence_audit",
        },
    )


def write_clean_transcript(path: Path) -> None:
    rows = [
        {
            "id": "t0001",
            "start": 0.0,
            "end": 3.0,
            "text": "Source Gate means confirmed primary material.",
            "normalized_text": "Source Gate means confirmed primary material.",
            "source_ids": ["raw_0001"],
            "language": "en",
            "speaker": "",
            "confidence": "high",
        },
        {
            "id": "t0002",
            "start": 4.0,
            "end": 8.0,
            "text": "For example, metadata alone cannot support speaker logic.",
            "normalized_text": "For example, metadata alone cannot support speaker logic.",
            "source_ids": ["raw_0002"],
            "language": "en",
            "speaker": "",
            "confidence": "high",
        },
        {
            "id": "t0003",
            "start": 9.0,
            "end": 13.0,
            "text": "Therefore we must preserve transcript evidence before writing reports.",
            "normalized_text": "Therefore we must preserve transcript evidence before writing reports.",
            "source_ids": ["raw_0003"],
            "language": "en",
            "speaker": "",
            "confidence": "high",
        },
    ]
    write_text(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def write_argument_segments(path: Path, *, bad_transcript_id: bool = False) -> None:
    claim_tid = "missing_tid" if bad_transcript_id else "t0003"
    write_json(
        path,
        {
            "segments": [
                {
                    "id": "seg_argument_001",
                    "start": 0.0,
                    "end": 3.0,
                    "role": "definition",
                    "title": "Source Gate",
                    "summary": "Defines source gate.",
                    "transcript_ids": ["t0001"],
                    "evidence_spans": [span(["t0001"], "Source Gate means confirmed primary material.", 0.0, 3.0)],
                },
                {
                    "id": "seg_argument_002",
                    "start": 4.0,
                    "end": 8.0,
                    "role": "example",
                    "title": "Metadata example",
                    "summary": "Metadata alone is insufficient.",
                    "transcript_ids": ["t0002"],
                    "evidence_spans": [span(["t0002"], "metadata alone", 4.0, 8.0)],
                },
                {
                    "id": "seg_argument_003",
                    "start": 9.0,
                    "end": 13.0,
                    "role": "claim",
                    "title": "Preserve evidence",
                    "summary": "Preserve transcript evidence.",
                    "transcript_ids": [claim_tid],
                    "evidence_spans": [span([claim_tid], "preserve transcript evidence", 9.0, 13.0)],
                },
            ]
        },
    )


def write_inventory(root: Path, *, bad_example_link: bool = False, empty_concept_definition: bool = False) -> None:
    linked_claim = "missing_claim" if bad_example_link else "claim_001"
    definition = "" if empty_concept_definition else "A gate that requires primary source material."
    write_json(
        root / "03_inventory" / "concepts.json",
        {
            "concepts": [
                {
                    "id": "concept_001",
                    "term": "Source Gate",
                    "normalized_term": "source gate",
                    "definition_in_source": definition,
                    "evidence_spans": [span(["t0001"], "Source Gate means confirmed primary material.", 0.0, 3.0)],
                    "importance": "high",
                    "notes": "",
                    "source_argument_segment_ids": ["seg_argument_001"],
                }
            ]
        },
    )
    write_json(
        root / "03_inventory" / "examples.json",
        {
            "examples": [
                {
                    "id": "ex_001",
                    "name": "Metadata example",
                    "description": "Metadata alone cannot support speaker logic.",
                    "what_it_demonstrates": "Why primary transcript is needed.",
                    "evidence_spans": [span(["t0002"], "metadata alone", 4.0, 8.0)],
                    "linked_claim_ids": [linked_claim],
                    "source_argument_segment_ids": ["seg_argument_002"],
                }
            ]
        },
    )
    write_json(
        root / "03_inventory" / "claims.json",
        {
            "claims": [
                {
                    "id": "claim_001",
                    "text": "We must preserve transcript evidence before writing reports.",
                    "claim_type": "source_claim",
                    "evidence_spans": [span(["t0003"], "preserve transcript evidence", 9.0, 13.0)],
                    "confidence": "high",
                    "linked_example_ids": ["ex_001"],
                    "source_argument_segment_ids": ["seg_argument_003"],
                }
            ]
        },
    )
    write_json(
        root / "03_inventory" / "analogies.json",
        {
            "analogies": []
        },
    )


def write_logic(root: Path, *, bad_edge: bool = False) -> None:
    nodes = [
        {
            "id": "arg_seg_argument_001",
            "type": "claim",
            "label": "Source Gate",
            "summary": "Defines source gate.",
            "evidence_spans": [span(["t0001"], "Source Gate means confirmed primary material.", 0.0, 3.0)],
            "source_argument_segment_ids": ["seg_argument_001"],
        },
        {
            "id": "ex_001",
            "type": "example",
            "label": "Metadata example",
            "summary": "Metadata alone is insufficient.",
            "evidence_spans": [span(["t0002"], "metadata alone", 4.0, 8.0)],
            "source_argument_segment_ids": ["seg_argument_002"],
        },
        {
            "id": "claim_001",
            "type": "claim",
            "label": "Preserve evidence",
            "summary": "Preserve transcript evidence.",
            "evidence_spans": [span(["t0003"], "preserve transcript evidence", 9.0, 13.0)],
            "source_argument_segment_ids": ["seg_argument_003"],
        },
    ]
    target = "missing_node" if bad_edge else "claim_001"
    write_json(
        root / "04_logic" / "logic_graph.json",
        {
            "runner": "self-test",
            "generated_at": now_iso(),
            "nodes": nodes,
            "edges": [
                {
                    "id": "edge_001",
                    "source": "ex_001",
                    "target": target,
                    "type": "supports",
                    "rationale": "Example supports the claim.",
                }
            ],
        },
    )
    write_text(
        root / "04_logic" / "source_logic.md",
        "\n".join(
            [
                "# Source Logic",
                "",
                "## Source Boundary",
                "",
                "- This file reconstructs source-internal flow from transcript evidence.",
                "- It does not add outside critique, external theory, or downstream interpretation.",
                "",
            ]
        ),
    )


def build_fixture(
    root: Path,
    *,
    source_status: str = "source_confirmed",
    primary: bool = True,
    bad_edge: bool = False,
    bad_example_link: bool = False,
    bad_transcript_id: bool = False,
    empty_concept_definition: bool = False,
) -> None:
    write_status(root / "00_source" / "source_status.json", source_status=source_status, primary=primary)
    write_clean_transcript(root / "01_transcript" / "clean_transcript.jsonl")
    write_text(root / "01_transcript" / "clean_transcript.md", "# Clean Transcript\n\nTranscript fixture.\n")
    write_argument_segments(root / "02_segments" / "argument_segments.json", bad_transcript_id=bad_transcript_id)
    write_inventory(root, bad_example_link=bad_example_link, empty_concept_definition=empty_concept_definition)
    write_logic(root, bad_edge=bad_edge)


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="evidence-audit-") as tmp:
        base = Path(tmp)

        full = base / "full"
        build_fixture(full)
        full_result = run_evidence_audit(argparse.Namespace(output_root=full, source_status=None))
        assert_true("full gate", full_result["pack_gate"]["can_build_video_analysis_pack"], failures)
        assert_true("full no errors", full_result["severity_counts"]["error"] == 0, failures)
        assert_true("audit written", (full / "05_gap_check" / "evidence_audit.json").is_file(), failures)
        assert_true("gap written", (full / "05_gap_check" / "gap_check.md").is_file(), failures)
        assert_true("pack not written", not (full / "video_analysis_pack.md").exists(), failures)

        partial = base / "partial"
        build_fixture(partial, source_status="source_partial")
        partial_result = run_evidence_audit(argparse.Namespace(output_root=partial, source_status=None))
        assert_true("partial full false", not partial_result["pack_gate"]["can_build_video_analysis_pack"], failures)
        assert_true("partial gate", partial_result["pack_gate"]["can_build_partial_pack"], failures)

        blocked = base / "blocked"
        build_fixture(blocked, source_status="secondary_only", primary=False)
        try:
            run_evidence_audit(argparse.Namespace(output_root=blocked, source_status=None))
        except EvidenceAuditError:
            pass
        else:
            failures.append("blocked gate: expected EvidenceAuditError")
        assert_true("blocked no audit", not (blocked / "05_gap_check" / "evidence_audit.json").exists(), failures)

        bad_edge = base / "bad-edge"
        build_fixture(bad_edge, bad_edge=True)
        bad_edge_result = run_evidence_audit(argparse.Namespace(output_root=bad_edge, source_status=None))
        assert_true("bad edge blocks pack", not bad_edge_result["pack_gate"]["can_build_video_analysis_pack"], failures)
        assert_true("bad edge has errors", bad_edge_result["severity_counts"]["error"] > 0, failures)

        bad_inventory = base / "bad-inventory"
        build_fixture(bad_inventory, bad_example_link=True)
        bad_inventory_result = run_evidence_audit(argparse.Namespace(output_root=bad_inventory, source_status=None))
        assert_true("bad inventory has errors", bad_inventory_result["severity_counts"]["error"] > 0, failures)

        bad_segment = base / "bad-segment"
        build_fixture(bad_segment, bad_transcript_id=True)
        bad_segment_result = run_evidence_audit(argparse.Namespace(output_root=bad_segment, source_status=None))
        assert_true("bad segment has errors", bad_segment_result["severity_counts"]["error"] > 0, failures)

        warning_only = base / "warning-only"
        build_fixture(warning_only, empty_concept_definition=True)
        warning_result = run_evidence_audit(argparse.Namespace(output_root=warning_only, source_status=None))
        assert_true("warning-only still allows full", warning_result["pack_gate"]["can_build_video_analysis_pack"], failures)
        assert_true("warning-only warning present", warning_result["severity_counts"]["warning"] > 0, failures)

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

    if args.output_root is None:
        parser.error("--output-root is required unless --self-test is used")

    try:
        summary = run_evidence_audit(args)
    except EvidenceAuditError as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "output_root": str(args.output_root.expanduser().resolve()) if args.output_root else None,
                "error": "evidence_audit_failed",
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
