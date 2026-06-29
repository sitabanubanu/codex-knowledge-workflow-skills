#!/usr/bin/env python
"""Build source-faithful logic artifacts from segments and inventory."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import artifact_validator
from write_artifact import ArtifactWriteError, write_artifact


RUNNER_NAME = "knowledge-video-source-logic-builder"
ALLOWED_SOURCE_STATUSES = {"source_confirmed", "source_partial"}
NODE_TYPES = {"claim", "example", "concept", "analogy", "conclusion", "question"}
EDGE_TYPES = {"supports", "explains", "contrasts", "leads_to", "defines", "analogizes"}


class SourceLogicBuilderError(Exception):
    """Expected CLI-facing source logic failure."""


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
        raise SourceLogicBuilderError(f"invalid JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise SourceLogicBuilderError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SourceLogicBuilderError(f"JSON file is not an object: {path}")
    return payload


def load_source_status(path: Path) -> dict[str, Any]:
    status = read_json(path)
    source_status = status.get("source_status")
    if source_status not in ALLOWED_SOURCE_STATUSES:
        raise SourceLogicBuilderError(
            f"source logic requires source_confirmed or source_partial; got {source_status!r}"
        )
    if not status.get("primary_material_available"):
        raise SourceLogicBuilderError("source logic requires primary_material_available=true")
    return status


def load_segments(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    segments = payload.get("segments")
    if not isinstance(segments, list) or not segments:
        raise SourceLogicBuilderError("argument_segments.json must contain a non-empty segments list")
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            raise SourceLogicBuilderError(f"argument segment {index} is not an object")
        if not str(segment.get("id") or "").strip():
            raise SourceLogicBuilderError(f"argument segment {index} is missing id")
        if not isinstance(segment.get("transcript_ids"), list) or not segment.get("transcript_ids"):
            raise SourceLogicBuilderError(f"argument segment {segment.get('id')} has no transcript_ids")
        if not isinstance(segment.get("evidence_spans"), list) or not segment.get("evidence_spans"):
            raise SourceLogicBuilderError(f"argument segment {segment.get('id')} has no evidence_spans")
    return segments


def load_inventory_file(path: Path, key: str) -> list[dict[str, Any]]:
    payload = read_json(path)
    values = payload.get(key)
    if not isinstance(values, list):
        raise SourceLogicBuilderError(f"{path.name} must contain a {key} list")
    for index, item in enumerate(values, start=1):
        if not isinstance(item, dict):
            raise SourceLogicBuilderError(f"{path.name} item {index} is not an object")
        if not str(item.get("id") or "").strip():
            raise SourceLogicBuilderError(f"{path.name} item {index} is missing id")
        if not isinstance(item.get("evidence_spans"), list):
            raise SourceLogicBuilderError(f"{item.get('id')} in {path.name} has no evidence_spans list")
    return values


def load_inventory(root: Path) -> dict[str, list[dict[str, Any]]]:
    inventory_dir = root / "03_inventory"
    return {
        "concepts": load_inventory_file(inventory_dir / "concepts.json", "concepts"),
        "examples": load_inventory_file(inventory_dir / "examples.json", "examples"),
        "claims": load_inventory_file(inventory_dir / "claims.json", "claims"),
        "analogies": load_inventory_file(inventory_dir / "analogies.json", "analogies"),
    }


def compact(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def first_span(item: dict[str, Any]) -> dict[str, Any]:
    spans = item.get("evidence_spans")
    if isinstance(spans, list) and spans and isinstance(spans[0], dict):
        return dict(spans[0])
    return {
        "transcript_ids": [],
        "start": item.get("start"),
        "end": item.get("end"),
        "quote": compact(item.get("text") or item.get("summary") or item.get("title") or ""),
        "source": "clean_transcript",
    }


def segment_label(segment: dict[str, Any]) -> str:
    return compact(segment.get("title") or segment.get("summary") or first_span(segment).get("quote") or segment["id"], 90)


def item_label(item: dict[str, Any], fallback: str) -> str:
    return compact(
        item.get("text")
        or item.get("name")
        or item.get("term")
        or item.get("purpose")
        or item.get("title")
        or fallback,
        90,
    )


def node(
    node_id: str,
    node_type: str,
    label: str,
    summary: str,
    evidence_spans: list[dict[str, Any]],
    **extra: Any,
) -> dict[str, Any]:
    if node_type not in NODE_TYPES:
        node_type = "claim"
    payload = {
        "id": node_id,
        "type": node_type,
        "label": compact(label, 90),
        "summary": compact(summary, 220),
        "evidence_spans": evidence_spans,
    }
    payload.update(extra)
    return payload


def edge(edge_id: str, source: str, target: str, edge_type: str, rationale: str) -> dict[str, Any]:
    if edge_type not in EDGE_TYPES:
        edge_type = "leads_to"
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "type": edge_type,
        "rationale": compact(rationale, 220),
    }


def build_nodes(argument_segments: list[dict[str, Any]], inventory: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for segment in argument_segments:
        role = str(segment.get("role") or "claim")
        node_type = "question" if role == "question" else "conclusion" if role == "conclusion" else "claim"
        nodes.append(
            node(
                f"arg_{segment['id']}",
                node_type,
                segment_label(segment),
                str(segment.get("summary") or "Argument segment in source order."),
                list(segment.get("evidence_spans") or []),
                source_argument_segment_ids=[segment["id"]],
                role=role,
            )
        )
    for claim in inventory["claims"]:
        nodes.append(
            node(
                claim["id"],
                "claim",
                item_label(claim, claim["id"]),
                f"{claim.get('claim_type', 'claim')} candidate from inventory.",
                list(claim.get("evidence_spans") or []),
                claim_type=claim.get("claim_type"),
                source_argument_segment_ids=claim.get("source_argument_segment_ids", []),
            )
        )
    for example in inventory["examples"]:
        nodes.append(
            node(
                example["id"],
                "example",
                item_label(example, example["id"]),
                str(example.get("what_it_demonstrates") or "Example candidate from inventory."),
                list(example.get("evidence_spans") or []),
                source_argument_segment_ids=example.get("source_argument_segment_ids", []),
            )
        )
    for concept in inventory["concepts"]:
        nodes.append(
            node(
                concept["id"],
                "concept",
                item_label(concept, concept["id"]),
                str(concept.get("definition_in_source") or concept.get("notes") or "Concept candidate from inventory."),
                list(concept.get("evidence_spans") or []),
                source_argument_segment_ids=concept.get("source_argument_segment_ids", []),
            )
        )
    for analogy in inventory["analogies"]:
        nodes.append(
            node(
                analogy["id"],
                "analogy",
                item_label(analogy, analogy["id"]),
                str(analogy.get("purpose") or "Analogy candidate from inventory."),
                list(analogy.get("evidence_spans") or []),
                source_argument_segment_ids=analogy.get("source_argument_segment_ids", []),
            )
        )
    return nodes


def first_claim_id(inventory: dict[str, list[dict[str, Any]]]) -> str | None:
    source_claims = [claim for claim in inventory["claims"] if claim.get("claim_type") == "source_claim"]
    if source_claims:
        return str(source_claims[0]["id"])
    if inventory["claims"]:
        return str(inventory["claims"][0]["id"])
    return None


def build_edges(argument_segments: list[dict[str, Any]], inventory: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    edge_index = 1
    for left, right in zip(argument_segments, argument_segments[1:]):
        edges.append(
            edge(
                f"edge_{edge_index:03d}",
                f"arg_{left['id']}",
                f"arg_{right['id']}",
                "leads_to",
                "Adjacent argument segments appear in this source order.",
            )
        )
        edge_index += 1
    target_claim = first_claim_id(inventory)
    for example in inventory["examples"]:
        for linked_claim_id in example.get("linked_claim_ids", []):
            if not any(claim.get("id") == linked_claim_id for claim in inventory["claims"]):
                continue
            edges.append(
                edge(
                    f"edge_{edge_index:03d}",
                    example["id"],
                    str(linked_claim_id),
                    "supports",
                    "Example-to-claim relation was explicitly present in inventory and still requires final evidence audit.",
                )
            )
            edge_index += 1
    for concept in inventory["concepts"]:
        segment_ids = concept.get("source_argument_segment_ids") or []
        if segment_ids:
            edges.append(
                edge(
                    f"edge_{edge_index:03d}",
                    f"arg_{segment_ids[0]}",
                    concept["id"],
                    "defines",
                    "Concept candidate is anchored in this argument segment.",
                )
            )
            edge_index += 1
    for analogy in inventory["analogies"]:
        target_claim = first_claim_id(inventory)
        if target_claim:
            edges.append(
                edge(
                    f"edge_{edge_index:03d}",
                    analogy["id"],
                    target_claim,
                    "analogizes",
                    "Candidate analogy relation; domain mapping remains to be verified.",
                )
            )
            edge_index += 1
    return edges


def render_source_logic(
    *,
    source_status: dict[str, Any],
    argument_segments: list[dict[str, Any]],
    inventory: dict[str, list[dict[str, Any]]],
    edges: list[dict[str, Any]],
) -> str:
    claims = inventory["claims"]
    source_claims = [claim for claim in claims if claim.get("claim_type") == "source_claim"]
    thesis = source_claims[0]["text"] if source_claims else (claims[0]["text"] if claims else "No explicit thesis candidate extracted.")
    lines = [
        "# Source Logic",
        "",
        "## Source Boundary",
        "",
        f"- Source status: `{source_status.get('source_status')}`",
        "- This file reconstructs source-internal flow from transcript segments and inventory candidates.",
        "- It does not add outside critique, external theory, or downstream interpretation.",
        "",
        "## Core Question",
        "",
    ]
    questions = [segment for segment in argument_segments if segment.get("role") == "question"]
    if questions:
        for segment in questions:
            lines.append(f"- `{segment['id']}`: {segment_label(segment)}")
    else:
        lines.append("- No explicit question segment was detected; infer only from opening flow during document composition.")
    lines.extend(["", "## Speaker Thesis", "", f"- {compact(thesis, 260)}", "", "## Argument Flow", ""])
    for index, segment in enumerate(argument_segments, start=1):
        span = first_span(segment)
        tids = ", ".join(str(item) for item in span.get("transcript_ids", []))
        lines.append(
            f"{index}. `{segment['id']}` `{segment.get('role', 'claim')}`: {segment_label(segment)}"
            f" (evidence: {tids or 'unknown'})"
        )
    lines.extend(["", "## Key Reasoning Moves", ""])
    for edge_item in edges:
        lines.append(
            f"- `{edge_item['source']}` -> `{edge_item['target']}` `{edge_item['type']}`: {edge_item['rationale']}"
        )
    lines.extend(["", "## Example-to-Claim Links", ""])
    example_edges = [item for item in edges if item["type"] == "supports"]
    if example_edges:
        for edge_item in example_edges:
            lines.append(f"- `{edge_item['source']}` supports `{edge_item['target']}`: {edge_item['rationale']}")
    else:
        lines.append("- No example-to-claim support relation was generated.")
    lines.extend(["", "## Ambiguities", ""])
    uncertain = [claim for claim in claims if claim.get("claim_type") != "source_claim"]
    if uncertain:
        for claim in uncertain:
            lines.append(f"- `{claim['id']}` is `{claim.get('claim_type')}` and requires later evidence audit.")
    else:
        lines.append("- No non-source-claim inventory claims were present.")
    undefined = [concept for concept in inventory["concepts"] if not concept.get("definition_in_source")]
    if undefined:
        lines.append(f"- Candidate concepts without source-local definitions: {', '.join(concept['id'] for concept in undefined)}")
    lines.append("")
    return "\n".join(lines)


def render_logic_gap(inventory: dict[str, list[dict[str, Any]]], edges: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# Source Logic Gap Check",
            "",
            "## Logic Coverage",
            "",
            f"- Claims: `{len(inventory['claims'])}`",
            f"- Examples: `{len(inventory['examples'])}`",
            f"- Concepts: `{len(inventory['concepts'])}`",
            f"- Analogies: `{len(inventory['analogies'])}`",
            f"- Logic edges: `{len(edges)}`",
            "",
            "## Remaining Limits",
            "",
            "- Logic graph edges are conservative source-order and candidate support links.",
            "- Source logic has been reconstructed from transcript-derived artifacts only.",
            "- A final evidence audit is still required before `video_analysis_pack.md` is written.",
            "",
        ]
    )


def run_source_logic(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.expanduser().resolve()
    source_status_path = args.source_status or output_root / "00_source" / "source_status.json"
    argument_segments_path = args.argument_segments or output_root / "02_segments" / "argument_segments.json"

    source_status = load_source_status(source_status_path)
    argument_segments = load_segments(argument_segments_path)
    inventory = load_inventory(output_root)
    nodes = build_nodes(argument_segments, inventory)
    edges = build_edges(argument_segments, inventory)
    graph = {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "nodes": nodes,
        "edges": edges,
    }
    written = [
        write_text(
            output_root / "04_logic" / "source_logic.md",
            render_source_logic(
                source_status=source_status,
                argument_segments=argument_segments,
                inventory=inventory,
                edges=edges,
            ),
        ),
        write_json(output_root / "04_logic" / "logic_graph.json", graph),
        write_text(output_root / "05_gap_check" / "source_logic_gap_check.md", render_logic_gap(inventory, edges)),
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
        "nodes": len(nodes),
        "edges": len(edges),
        "files_written": [item["path"] for item in written],
        "validation": validation,
        "next_step": "enter_gap_evidence_audit",
        "validation_next_step": validation.get("next_step"),
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build source logic artifacts from segments and inventory.")
    parser.add_argument("--output-root", type=Path, required=False, help="Artifact root containing source, segments, and inventory.")
    parser.add_argument("--source-status", type=Path, default=None, help="Optional source_status.json override.")
    parser.add_argument("--argument-segments", type=Path, default=None, help="Optional argument_segments.json override.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


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
            "next_step": "enter_source_logic_builder",
        },
    )


def span(tids: list[str], quote: str, start: float, end: float) -> dict[str, Any]:
    return {
        "transcript_ids": tids,
        "start": start,
        "end": end,
        "quote": quote,
        "source": "clean_transcript",
    }


def write_argument_segments(path: Path) -> None:
    write_json(
        path,
        {
            "segments": [
                {
                    "id": "seg_argument_001",
                    "start": 0.0,
                    "end": 3.0,
                    "role": "question",
                    "title": "Why source gates matter",
                    "summary": "Opening question",
                    "transcript_ids": ["t0001"],
                    "evidence_spans": [span(["t0001"], "Why does source gating matter?", 0.0, 3.0)],
                },
                {
                    "id": "seg_argument_002",
                    "start": 4.0,
                    "end": 8.0,
                    "role": "example",
                    "title": "Metadata example",
                    "summary": "Example",
                    "transcript_ids": ["t0002"],
                    "evidence_spans": [span(["t0002"], "Metadata alone cannot support speaker logic.", 4.0, 8.0)],
                },
                {
                    "id": "seg_argument_003",
                    "start": 9.0,
                    "end": 13.0,
                    "role": "claim",
                    "title": "Preserve transcript evidence",
                    "summary": "Claim",
                    "transcript_ids": ["t0003"],
                    "evidence_spans": [span(["t0003"], "Therefore we must preserve transcript evidence.", 9.0, 13.0)],
                },
            ]
        },
    )


def write_inventory(root: Path, *, missing: str | None = None) -> None:
    inventory = root / "03_inventory"
    payloads = {
        "concepts.json": {
            "concepts": [
                {
                    "id": "concept_001",
                    "term": "Source Gate",
                    "normalized_term": "source gate",
                    "definition_in_source": "A gate that requires primary source material.",
                    "evidence_spans": [span(["t0001"], "source gating", 0.0, 3.0)],
                    "importance": "high",
                    "notes": "",
                    "source_argument_segment_ids": ["seg_argument_001"],
                }
            ]
        },
        "examples.json": {
            "examples": [
                {
                    "id": "ex_001",
                    "name": "Metadata example",
                    "description": "Metadata alone cannot support speaker logic.",
                    "what_it_demonstrates": "Why primary transcript is needed.",
                    "evidence_spans": [span(["t0002"], "Metadata alone cannot support speaker logic.", 4.0, 8.0)],
                    "linked_claim_ids": ["claim_001"],
                    "source_argument_segment_ids": ["seg_argument_002"],
                }
            ]
        },
        "claims.json": {
            "claims": [
                {
                    "id": "claim_001",
                    "text": "Therefore we must preserve transcript evidence.",
                    "claim_type": "source_claim",
                    "evidence_spans": [span(["t0003"], "Therefore we must preserve transcript evidence.", 9.0, 13.0)],
                    "confidence": "medium",
                    "linked_example_ids": [],
                    "source_argument_segment_ids": ["seg_argument_003"],
                },
                {
                    "id": "claim_002",
                    "text": "Source gating is the implied organizing question.",
                    "claim_type": "inferred_claim",
                    "evidence_spans": [span(["t0001"], "Why does source gating matter?", 0.0, 3.0)],
                    "confidence": "low",
                    "linked_example_ids": [],
                    "source_argument_segment_ids": ["seg_argument_001"],
                },
            ]
        },
        "analogies.json": {"analogies": []},
    }
    for name, payload in payloads.items():
        if name != missing:
            write_json(inventory / name, payload)


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="source-logic-builder-") as tmp:
        base = Path(tmp)
        root = base / "confirmed"
        write_status(root / "00_source" / "source_status.json")
        write_argument_segments(root / "02_segments" / "argument_segments.json")
        write_inventory(root)
        result = run_source_logic(
            argparse.Namespace(
                output_root=root,
                source_status=None,
                argument_segments=None,
                pretty=False,
                self_test=False,
            )
        )
        assert_true("confirmed validates", result["validation"]["valid"] is True, failures, json.dumps(result["validation"], ensure_ascii=False))
        assert_true("writes source logic", (root / "04_logic" / "source_logic.md").is_file(), failures)
        assert_true("writes graph", (root / "04_logic" / "logic_graph.json").is_file(), failures)
        assert_true("no pack", not (root / "video_analysis_pack.md").exists(), failures)
        graph = read_json(root / "04_logic" / "logic_graph.json")
        node_types = {item["type"] for item in graph["nodes"]}
        edge_types = {item["type"] for item in graph["edges"]}
        assert_true("node types valid", node_types.issubset(NODE_TYPES), failures, str(node_types))
        assert_true("edge types valid", edge_types.issubset(EDGE_TYPES), failures, str(edge_types))
        assert_true("has support edge", "supports" in edge_types, failures, str(edge_types))
        logic_text = (root / "04_logic" / "source_logic.md").read_text(encoding="utf-8")
        assert_true("logic boundary", "does not add outside critique" in logic_text, failures)

        partial = base / "partial"
        write_status(partial / "00_source" / "source_status.json", source_status="source_partial", primary=True)
        write_argument_segments(partial / "02_segments" / "argument_segments.json")
        write_inventory(partial)
        partial_result = run_source_logic(
            argparse.Namespace(
                output_root=partial,
                source_status=None,
                argument_segments=None,
                pretty=False,
                self_test=False,
            )
        )
        assert_true("partial runs", partial_result["source_status"] == "source_partial", failures)

        blocked = base / "blocked"
        write_status(blocked / "00_source" / "source_status.json", source_status="secondary_only", primary=False)
        write_argument_segments(blocked / "02_segments" / "argument_segments.json")
        write_inventory(blocked)
        blocked_failed = False
        try:
            run_source_logic(
                argparse.Namespace(
                    output_root=blocked,
                    source_status=None,
                    argument_segments=None,
                    pretty=False,
                    self_test=False,
                )
            )
        except SourceLogicBuilderError:
            blocked_failed = True
        assert_true("blocked fails", blocked_failed, failures)
        assert_true("blocked creates no 04", not (blocked / "04_logic").exists(), failures)

        missing_inventory = base / "missing_inventory"
        write_status(missing_inventory / "00_source" / "source_status.json")
        write_argument_segments(missing_inventory / "02_segments" / "argument_segments.json")
        write_inventory(missing_inventory, missing="claims.json")
        missing_failed = False
        try:
            run_source_logic(
                argparse.Namespace(
                    output_root=missing_inventory,
                    source_status=None,
                    argument_segments=None,
                    pretty=False,
                    self_test=False,
                )
            )
        except SourceLogicBuilderError:
            missing_failed = True
        assert_true("missing inventory fails", missing_failed, failures)
        assert_true("missing inventory creates no 04", not (missing_inventory / "04_logic").exists(), failures)

        confirmed_no_primary = base / "confirmed_no_primary"
        write_status(
            confirmed_no_primary / "00_source" / "source_status.json",
            source_status="source_confirmed",
            primary=False,
        )
        write_argument_segments(confirmed_no_primary / "02_segments" / "argument_segments.json")
        write_inventory(confirmed_no_primary)
        confirmed_no_primary_failed = False
        try:
            run_source_logic(
                argparse.Namespace(
                    output_root=confirmed_no_primary,
                    source_status=None,
                    argument_segments=None,
                    pretty=False,
                    self_test=False,
                )
            )
        except SourceLogicBuilderError:
            confirmed_no_primary_failed = True
        assert_true("confirmed without primary fails", confirmed_no_primary_failed, failures)
        assert_true("confirmed without primary creates no 04", not (confirmed_no_primary / "04_logic").exists(), failures)

        secondary_with_primary = base / "secondary_with_primary"
        write_status(
            secondary_with_primary / "00_source" / "source_status.json",
            source_status="secondary_only",
            primary=True,
        )
        write_argument_segments(secondary_with_primary / "02_segments" / "argument_segments.json")
        write_inventory(secondary_with_primary)
        secondary_with_primary_failed = False
        try:
            run_source_logic(
                argparse.Namespace(
                    output_root=secondary_with_primary,
                    source_status=None,
                    argument_segments=None,
                    pretty=False,
                    self_test=False,
                )
            )
        except SourceLogicBuilderError:
            secondary_with_primary_failed = True
        assert_true("secondary with primary fails", secondary_with_primary_failed, failures)
        assert_true("secondary with primary creates no 04", not (secondary_with_primary / "04_logic").exists(), failures)

        bad_inventory = base / "bad_inventory"
        write_status(bad_inventory / "00_source" / "source_status.json")
        write_argument_segments(bad_inventory / "02_segments" / "argument_segments.json")
        write_inventory(bad_inventory)
        bad_claims = read_json(bad_inventory / "03_inventory" / "claims.json")
        bad_claims["claims"][0].pop("evidence_spans", None)
        write_json(bad_inventory / "03_inventory" / "claims.json", bad_claims)
        bad_inventory_failed = False
        try:
            run_source_logic(
                argparse.Namespace(
                    output_root=bad_inventory,
                    source_status=None,
                    argument_segments=None,
                    pretty=False,
                    self_test=False,
                )
            )
        except SourceLogicBuilderError:
            bad_inventory_failed = True
        assert_true("bad inventory evidence fails", bad_inventory_failed, failures)
        assert_true("bad inventory creates no 04", not (bad_inventory / "04_logic").exists(), failures)

        bad_segment = base / "bad_segment"
        write_status(bad_segment / "00_source" / "source_status.json")
        write_argument_segments(bad_segment / "02_segments" / "argument_segments.json")
        write_inventory(bad_segment)
        bad_segments = read_json(bad_segment / "02_segments" / "argument_segments.json")
        bad_segments["segments"][0]["evidence_spans"] = []
        write_json(bad_segment / "02_segments" / "argument_segments.json", bad_segments)
        bad_segment_failed = False
        try:
            run_source_logic(
                argparse.Namespace(
                    output_root=bad_segment,
                    source_status=None,
                    argument_segments=None,
                    pretty=False,
                    self_test=False,
                )
            )
        except SourceLogicBuilderError:
            bad_segment_failed = True
        assert_true("bad segment evidence fails", bad_segment_failed, failures)
        assert_true("bad segment creates no 04", not (bad_segment / "04_logic").exists(), failures)

        unlinked = base / "unlinked_example"
        write_status(unlinked / "00_source" / "source_status.json")
        write_argument_segments(unlinked / "02_segments" / "argument_segments.json")
        write_inventory(unlinked)
        examples = read_json(unlinked / "03_inventory" / "examples.json")
        examples["examples"][0]["linked_claim_ids"] = []
        write_json(unlinked / "03_inventory" / "examples.json", examples)
        unlinked_result = run_source_logic(
            argparse.Namespace(
                output_root=unlinked,
                source_status=None,
                argument_segments=None,
                pretty=False,
                self_test=False,
            )
        )
        unlinked_graph = read_json(unlinked / "04_logic" / "logic_graph.json")
        assert_true("unlinked example runs", unlinked_result["validation"]["valid"] is True, failures)
        assert_true(
            "unlinked example has no support edge",
            not any(edge_item["type"] == "supports" for edge_item in unlinked_graph["edges"]),
            failures,
        )

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
        summary = run_source_logic(args)
    except (SourceLogicBuilderError, ArtifactWriteError, OSError) as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "error": exc.__class__.__name__,
                "message": str(exc),
            },
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return 1
    emit_json(summary, pretty=args.pretty)
    return 0 if summary["validation"].get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
