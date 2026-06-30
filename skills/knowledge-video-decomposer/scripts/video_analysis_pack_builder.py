#!/usr/bin/env python
"""Build the final video_analysis_pack.md from audited decomposition artifacts."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import artifact_validator
import evidence_auditor
from write_artifact import write_artifact


RUNNER_NAME = "knowledge-video-analysis-pack-builder"
ALLOWED_SOURCE_STATUSES = {"source_confirmed", "source_partial"}


class VideoAnalysisPackBuilderError(Exception):
    """Expected CLI-facing pack builder failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def write_text(path: Path, text: str) -> dict[str, Any]:
    return write_artifact(path, text, mkdirs=True, overwrite=True)


def read_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise VideoAnalysisPackBuilderError(f"required JSON file is missing: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise VideoAnalysisPackBuilderError(f"invalid JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise VideoAnalysisPackBuilderError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise VideoAnalysisPackBuilderError(f"JSON file is not an object: {path}")
    return payload


def read_text(path: Path, *, required: bool = True) -> str:
    if not path.is_file():
        if required:
            raise VideoAnalysisPackBuilderError(f"required text file is missing: {path}")
        return ""
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise VideoAnalysisPackBuilderError(f"could not read text file {path}: {exc}") from exc


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise VideoAnalysisPackBuilderError(f"required JSONL file is missing: {path}")
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise VideoAnalysisPackBuilderError(f"could not read JSONL file {path}: {exc}") from exc
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise VideoAnalysisPackBuilderError(f"invalid JSONL line {index} in {path}: {exc}") from exc
        if not isinstance(row, dict):
            raise VideoAnalysisPackBuilderError(f"JSONL line {index} in {path} is not an object")
        rows.append(row)
    if not rows:
        raise VideoAnalysisPackBuilderError(f"JSONL file has no rows: {path}")
    return rows


def load_source_status(path: Path) -> dict[str, Any]:
    status = read_json(path)
    source_status = status.get("source_status")
    if source_status not in ALLOWED_SOURCE_STATUSES:
        raise VideoAnalysisPackBuilderError(
            f"pack builder requires source_confirmed or source_partial; got {source_status!r}"
        )
    if not status.get("primary_material_available"):
        raise VideoAnalysisPackBuilderError("pack builder requires primary_material_available=true")
    return status


def load_evidence_audit(path: Path, source_status: str, output_root: Path) -> dict[str, Any]:
    audit = read_json(path)
    audit_status = audit.get("source_status")
    if audit_status != source_status:
        raise VideoAnalysisPackBuilderError(
            f"evidence audit source_status {audit_status!r} does not match source status {source_status!r}"
        )
    audit_root = audit.get("output_root")
    if Path(str(audit_root or "")).expanduser().resolve() != output_root.expanduser().resolve():
        raise VideoAnalysisPackBuilderError("evidence audit output_root does not match the requested output root")
    counts = audit.get("severity_counts")
    if not isinstance(counts, dict):
        raise VideoAnalysisPackBuilderError("evidence_audit.json is missing severity_counts")
    if int(counts.get("error") or 0) > 0:
        raise VideoAnalysisPackBuilderError("evidence audit has error findings; fix them before building pack")
    findings = audit.get("findings")
    if not isinstance(findings, list):
        raise VideoAnalysisPackBuilderError("evidence_audit.json is missing findings")
    if any(isinstance(finding, dict) and finding.get("severity") == "error" for finding in findings):
        raise VideoAnalysisPackBuilderError("evidence audit findings contain errors; fix them before building pack")
    gate = audit.get("pack_gate")
    if not isinstance(gate, dict):
        raise VideoAnalysisPackBuilderError("evidence_audit.json is missing pack_gate")
    if source_status == "source_confirmed" and gate.get("can_build_video_analysis_pack") is not True:
        raise VideoAnalysisPackBuilderError("evidence audit does not allow full video_analysis_pack")
    if source_status == "source_partial" and gate.get("can_build_partial_pack") is not True:
        raise VideoAnalysisPackBuilderError("evidence audit does not allow partial video_analysis_pack")
    evidence_map = read_json(output_root / "05_gap_check" / "evidence_map.json")
    if Path(str(evidence_map.get("output_root") or "")).expanduser().resolve() != output_root.expanduser().resolve():
        raise VideoAnalysisPackBuilderError("evidence_map.json output_root does not match the requested output root")
    entries = evidence_map.get("entries")
    if not isinstance(entries, list) or not entries:
        raise VideoAnalysisPackBuilderError("evidence_map.json is missing evidence entries")
    evidence_summary = evidence_map.get("summary")
    if not isinstance(evidence_summary, dict):
        raise VideoAnalysisPackBuilderError("evidence_map.json is missing summary")
    audit_evidence_summary = audit.get("evidence_map_summary")
    if isinstance(audit_evidence_summary, dict) and audit_evidence_summary != evidence_summary:
        raise VideoAnalysisPackBuilderError("evidence_audit.json evidence_map_summary does not match evidence_map.json summary")
    claim_source_audit = read_json(output_root / "05_gap_check" / "claim_source_audit.json")
    if Path(str(claim_source_audit.get("output_root") or "")).expanduser().resolve() != output_root.expanduser().resolve():
        raise VideoAnalysisPackBuilderError("claim_source_audit.json output_root does not match the requested output root")
    claims = claim_source_audit.get("claims")
    if not isinstance(claims, list):
        raise VideoAnalysisPackBuilderError("claim_source_audit.json is missing claims")
    claim_summary = claim_source_audit.get("summary")
    if not isinstance(claim_summary, dict):
        raise VideoAnalysisPackBuilderError("claim_source_audit.json is missing summary")
    audit_claim_summary = audit.get("claim_source_audit_summary")
    if isinstance(audit_claim_summary, dict) and audit_claim_summary != claim_summary:
        raise VideoAnalysisPackBuilderError("evidence_audit.json claim_source_audit_summary does not match claim_source_audit.json summary")
    if int(claim_summary.get("blocking_claims") or 0) > 0:
        raise VideoAnalysisPackBuilderError("claim_source_audit.json has blocking claims")
    audit["_evidence_map_summary"] = evidence_summary
    audit["_claim_source_audit_summary"] = claim_summary
    return audit


def load_list(path: Path, key: str) -> list[dict[str, Any]]:
    payload = read_json(path)
    values = payload.get(key)
    if not isinstance(values, list):
        raise VideoAnalysisPackBuilderError(f"{path.name} must contain a {key} list")
    return [item for item in values if isinstance(item, dict)]


def first_text(*values: Any, default: str = "") -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return compact(text, 280)
    return default


def compact(text: str, limit: int = 220) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) > limit:
        return normalized[: limit - 3].rstrip() + "..."
    return normalized


def evidence_ref(item: dict[str, Any]) -> str:
    spans = item.get("evidence_spans")
    if not isinstance(spans, list) or not spans:
        return "evidence: unknown"
    refs: list[str] = []
    for span in spans[:2]:
        if not isinstance(span, dict):
            continue
        tids = span.get("transcript_ids")
        tid_text = ", ".join(str(tid) for tid in tids) if isinstance(tids, list) else ""
        start = span.get("start")
        end = span.get("end")
        if start is not None and end is not None:
            refs.append(f"{tid_text or 'transcript'} {start}-{end}")
        else:
            refs.append(tid_text or "transcript")
    return "evidence: " + "; ".join(ref for ref in refs if ref) if refs else "evidence: unknown"


def bullet(lines: list[str], text: str = "") -> None:
    lines.append(f"- {text}" if text else "-")


def numbered(lines: list[str], index: int, text: str) -> None:
    lines.append(f"{index}. {text}")


def render_source_summary(metadata: dict[str, Any], status: dict[str, Any], partial: bool) -> list[str]:
    title = first_text(metadata.get("title"), metadata.get("source_url"), default="Untitled source")
    lines = [
        "## Source Summary",
        "",
        f"- Title: {title}",
        f"- Source status: `{status.get('source_status')}`",
        f"- Source type: `{metadata.get('source_type', 'unknown')}`",
        f"- Platform: `{metadata.get('platform', 'unknown')}`",
        f"- Speaker or channel: {first_text(metadata.get('speaker_or_channel'), default='unknown')}",
        f"- Language: `{metadata.get('language', 'unknown')}`",
    ]
    if metadata.get("source_url"):
        lines.append(f"- Source URL: {metadata.get('source_url')}")
    if partial:
        lines.append("- Scope label: partial source analysis. Do not present this pack as a complete source reconstruction.")
    return lines


def render_acquisition(status: dict[str, Any], metadata: dict[str, Any], audit: dict[str, Any]) -> list[str]:
    classes = status.get("source_classes")
    class_text = ", ".join(str(item) for item in classes) if isinstance(classes, list) else ""
    lines = [
        "## Acquisition Confidence",
        "",
        f"- Allowed report type: `{status.get('allowed_report_type')}`",
        f"- Primary material available: `{str(bool(status.get('primary_material_available'))).lower()}`",
        f"- Source classes: {class_text or 'not recorded'}",
        f"- Acquisition confidence: `{metadata.get('confidence', 'unknown')}`",
        f"- Status reason: {first_text(status.get('status_reason'), default='not recorded')}",
        f"- Evidence audit errors: `{audit.get('severity_counts', {}).get('error', 0)}`",
        f"- Evidence audit warnings: `{audit.get('severity_counts', {}).get('warning', 0)}`",
    ]
    return lines


def render_asr_quality(status: dict[str, Any]) -> list[str]:
    asr = status.get("asr_pipeline") if isinstance(status.get("asr_pipeline"), dict) else {}
    quality = status.get("asr_quality") if isinstance(status.get("asr_quality"), dict) else asr.get("quality")
    if not isinstance(quality, dict):
        return []
    return [
        "## ASR Quality",
        "",
        "- Quality report: `00_source/asr_pipeline_report.json`",
        f"- Alignment report: `{asr.get('alignment_report', '00_source/asr_alignment_report.json')}`",
        f"- Diarization report: `{asr.get('diarization_report', '00_source/asr_diarization.json')}`",
        f"- Exact wording confidence: `{quality.get('exact_wording_confidence', 'unknown')}`",
        f"- Structural summary confidence: `{quality.get('structural_summary_confidence', 'unknown')}`",
        f"- Word timestamp coverage: `{quality.get('word_timestamp_coverage', 0.0)}`",
        f"- Speaker coverage: `{quality.get('speaker_coverage', 0.0)}`",
        f"- Alignment status: `{quality.get('alignment_status', 'unknown')}`",
        f"- Diarization status: `{quality.get('diarization_status', 'unknown')}`",
        f"- Verified verbatim: `{str(bool(quality.get('verified_verbatim'))).lower()}`",
        "- Boundary: ASR-derived transcript must remain labeled as ASR and must not be presented as a verified verbatim transcript unless reviewed.",
    ]


def render_transcript(output_root: Path, transcript_rows: list[dict[str, Any]]) -> list[str]:
    first_row = transcript_rows[0]
    last_row = transcript_rows[-1]
    lines = [
        "## Transcript Location",
        "",
        "- Machine transcript: `01_transcript/clean_transcript.jsonl`",
        "- Readable transcript: `01_transcript/clean_transcript.md`",
        f"- Transcript rows: `{len(transcript_rows)}`",
        f"- First transcript id: `{first_row.get('id')}`",
        f"- Last transcript id: `{last_row.get('id')}`",
    ]
    if (output_root / "01_transcript" / "raw_transcript.jsonl").is_file():
        lines.append("- Raw transcript: `01_transcript/raw_transcript.jsonl`")
    return lines


def render_thesis(claims: list[dict[str, Any]]) -> list[str]:
    source_claims = [claim for claim in claims if claim.get("claim_type") == "source_claim"]
    claim = source_claims[0] if source_claims else (claims[0] if claims else {})
    thesis = first_text(claim.get("text"), default="No thesis claim was extracted.")
    return [
        "## Speaker Thesis",
        "",
        f"- {thesis}",
        f"- Evidence: {evidence_ref(claim) if claim else 'unknown'}",
    ]


def render_argument_flow(segments: list[dict[str, Any]]) -> list[str]:
    lines = ["## Argument Flow", ""]
    if not segments:
        lines.append("- No argument segments were available.")
        return lines
    for index, segment in enumerate(segments, start=1):
        label = first_text(segment.get("title"), segment.get("summary"), segment.get("id"), default=str(segment.get("id")))
        role = segment.get("role", "unknown")
        numbered(lines, index, f"`{segment.get('id')}` `{role}`: {label} ({evidence_ref(segment)})")
    return lines


def render_examples(examples: list[dict[str, Any]]) -> list[str]:
    lines = ["## Key Examples", ""]
    if not examples:
        lines.append("- No examples were extracted.")
        return lines
    for example in examples:
        linked_claims = example.get("linked_claim_ids")
        linked = ", ".join(str(item) for item in linked_claims) if isinstance(linked_claims, list) else ""
        bullet(
            lines,
            f"`{example.get('id')}` {first_text(example.get('name'), example.get('description'), default='Unnamed example')}: "
            f"{first_text(example.get('what_it_demonstrates'), example.get('description'), default='role not recorded')} "
            f"({evidence_ref(example)}; linked claims: {linked or 'none'})",
        )
    return lines


def render_concepts(concepts: list[dict[str, Any]]) -> list[str]:
    lines = ["## Concepts", ""]
    if not concepts:
        lines.append("- No concepts were extracted.")
        return lines
    for concept in concepts:
        definition = first_text(concept.get("definition_in_source"), concept.get("notes"), default="source-local definition not established")
        bullet(lines, f"`{concept.get('id')}` {first_text(concept.get('term'), default='Unnamed concept')}: {definition} ({evidence_ref(concept)})")
    return lines


def render_claims(claims: list[dict[str, Any]]) -> list[str]:
    lines = ["## Claims", ""]
    if not claims:
        lines.append("- No claims were extracted.")
        return lines
    grouped = {
        "source_claim": [claim for claim in claims if claim.get("claim_type") == "source_claim"],
        "inferred_claim": [claim for claim in claims if claim.get("claim_type") == "inferred_claim"],
        "uncertain_claim": [claim for claim in claims if claim.get("claim_type") == "uncertain_claim"],
    }
    headings = {
        "source_claim": "Source Claims",
        "inferred_claim": "Inferred Claims",
        "uncertain_claim": "Uncertain Claims",
    }
    for claim_type, items in grouped.items():
        lines.extend(["", f"### {headings[claim_type]}", ""])
        if not items:
            lines.append("- None recorded.")
            continue
        for claim in items:
            bullet(lines, f"`{claim.get('id')}` {first_text(claim.get('text'), default='Claim text missing')} ({evidence_ref(claim)})")
    return lines


def render_analogies(analogies: list[dict[str, Any]]) -> list[str]:
    lines = ["## Analogies", ""]
    if not analogies:
        lines.append("- No analogies were extracted.")
        return lines
    for analogy in analogies:
        source_domain = first_text(analogy.get("source_domain"), default="source domain not recorded")
        target_domain = first_text(analogy.get("target_domain"), default="target domain not recorded")
        purpose = first_text(analogy.get("purpose"), default="purpose not recorded")
        bullet(lines, f"`{analogy.get('id')}` {source_domain} -> {target_domain}: {purpose} ({evidence_ref(analogy)})")
    return lines


def render_logic(logic_graph: dict[str, Any], source_logic: str) -> list[str]:
    nodes = logic_graph.get("nodes") if isinstance(logic_graph.get("nodes"), list) else []
    edges = logic_graph.get("edges") if isinstance(logic_graph.get("edges"), list) else []
    source_logic_lines = [line.strip() for line in source_logic.splitlines() if line.strip() and not line.startswith("#")]
    summary = compact(source_logic_lines[0], 260) if source_logic_lines else "Source logic summary is available in 04_logic/source_logic.md."
    return [
        "## Source Logic Summary",
        "",
        f"- Logic source: `04_logic/source_logic.md`",
        f"- Logic graph: `04_logic/logic_graph.json`",
        f"- Logic nodes: `{len(nodes)}`",
        f"- Logic edges: `{len(edges)}`",
        f"- Summary anchor: {summary}",
    ]


def render_gaps(audit: dict[str, Any], gap_check: str) -> list[str]:
    findings = audit.get("findings")
    warnings = [item for item in findings if isinstance(item, dict) and item.get("severity") == "warning"] if isinstance(findings, list) else []
    errors = [item for item in findings if isinstance(item, dict) and item.get("severity") == "error"] if isinstance(findings, list) else []
    lines = [
        "## Gaps",
        "",
        "- Evidence audit: `05_gap_check/evidence_audit.json`",
        "- Evidence map: `05_gap_check/evidence_map.json`",
        "- Claim source audit: `05_gap_check/claim_source_audit.json`",
        "- Gap check: `05_gap_check/gap_check.md`",
        f"- Blocking errors at pack time: `{len(errors)}`",
        f"- Warnings carried downstream: `{len(warnings)}`",
    ]
    evidence_summary = audit.get("_evidence_map_summary") if isinstance(audit.get("_evidence_map_summary"), dict) else {}
    claim_summary = audit.get("_claim_source_audit_summary") if isinstance(audit.get("_claim_source_audit_summary"), dict) else {}
    if evidence_summary:
        lines.append(f"- Evidence entries with transcript span: `{evidence_summary.get('entries_with_transcript_span', 0)}`")
    if claim_summary:
        lines.append(f"- Claims with transcript span: `{claim_summary.get('claims_with_transcript_span', 0)}`")
    if warnings:
        for warning in warnings[:10]:
            bullet(lines, f"`{warning.get('code')}` {warning.get('message')}")
    elif gap_check.strip():
        lines.append("- No warning findings were recorded by the evidence audit.")
    return lines


def render_downstream(source_status: str, partial: bool) -> list[str]:
    lines = [
        "## Downstream Notes",
        "",
        "- Treat Source, Inference, and Extension as separate layers in document composition.",
        "- Use source claims as source-grounded material; keep inferred and uncertain claims labeled.",
        "- Do not add external critique or outside frameworks inside source-logic reconstruction.",
        "- Carry evidence audit warnings into any report draft, critique, and final quality gate.",
    ]
    if partial:
        lines.append("- Because this is partial, the document composer must keep the scope label visible.")
    else:
        lines.append(f"- Source status `{source_status}` allows full pack handoff, subject to downstream document quality gates.")
    return lines


def render_pack(
    *,
    output_root: Path,
    source_status: dict[str, Any],
    metadata: dict[str, Any],
    transcript_rows: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    analogies: list[dict[str, Any]],
    logic_graph: dict[str, Any],
    source_logic: str,
    evidence_audit: dict[str, Any],
    gap_check: str,
) -> str:
    status = str(source_status.get("source_status"))
    partial = status == "source_partial"
    title = "# Video Analysis Pack (Partial Scope)" if partial else "# Video Analysis Pack"
    lines = [
        title,
        "",
        f"_Generated by `{RUNNER_NAME}` at `{now_iso()}`._",
        "",
    ]
    sections = [
        render_source_summary(metadata, source_status, partial),
        render_acquisition(source_status, metadata, evidence_audit),
        render_asr_quality(source_status),
        render_transcript(output_root, transcript_rows),
        render_thesis(claims),
        render_argument_flow(segments),
        render_examples(examples),
        render_concepts(concepts),
        render_claims(claims),
        render_analogies(analogies),
        render_logic(logic_graph, source_logic),
        render_gaps(evidence_audit, gap_check),
        render_downstream(status, partial),
    ]
    for section in sections:
        lines.extend(section)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_pack_builder(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.expanduser().resolve()
    source_status_path = output_root / "00_source" / "source_status.json"
    audit_path = output_root / "05_gap_check" / "evidence_audit.json"
    source_status = load_source_status(source_status_path)
    evidence_audit = load_evidence_audit(audit_path, str(source_status.get("source_status")), output_root)

    metadata = read_json(output_root / "00_source" / "metadata.json", required=False)
    transcript_rows = read_jsonl(output_root / "01_transcript" / "clean_transcript.jsonl")
    segments = load_list(output_root / "02_segments" / "argument_segments.json", "segments")
    concepts = load_list(output_root / "03_inventory" / "concepts.json", "concepts")
    examples = load_list(output_root / "03_inventory" / "examples.json", "examples")
    claims = load_list(output_root / "03_inventory" / "claims.json", "claims")
    analogies = load_list(output_root / "03_inventory" / "analogies.json", "analogies")
    logic_graph = read_json(output_root / "04_logic" / "logic_graph.json")
    source_logic = read_text(output_root / "04_logic" / "source_logic.md")
    gap_check = read_text(output_root / "05_gap_check" / "gap_check.md")

    pack_text = render_pack(
        output_root=output_root,
        source_status=source_status,
        metadata=metadata,
        transcript_rows=transcript_rows,
        segments=segments,
        concepts=concepts,
        examples=examples,
        claims=claims,
        analogies=analogies,
        logic_graph=logic_graph,
        source_logic=source_logic,
        evidence_audit=evidence_audit,
        gap_check=gap_check,
    )
    pack_path = output_root / "video_analysis_pack.md"
    had_existing_pack = pack_path.exists()
    existing_pack_bytes = pack_path.read_bytes() if had_existing_pack else None
    written = write_text(pack_path, pack_text)
    validation = artifact_validator.validate_artifact_root(
        output_root,
        source_status_path,
        mode="strict",
    )
    if not validation.get("valid"):
        if had_existing_pack and existing_pack_bytes is not None:
            pack_path.write_bytes(existing_pack_bytes)
        else:
            pack_path.unlink(missing_ok=True)
        raise VideoAnalysisPackBuilderError(
            f"artifact validation failed after pack render: {validation.get('next_step')}"
        )
    return {
        "runner": RUNNER_NAME,
        "output_root": str(output_root),
        "source_status": source_status.get("source_status"),
        "pack_path": written["path"],
        "bytes": written["bytes"],
        "validation": validation,
        "next_step": "enter_document_composer" if validation.get("valid") else validation.get("next_step"),
        "validation_next_step": validation.get("next_step"),
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build video_analysis_pack.md from audited decomposition artifacts.")
    parser.add_argument("--output-root", type=Path, required=False, help="Artifact root containing audited decomposition artifacts.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def write_metadata(root: Path) -> None:
    evidence_auditor.write_json(
        root / "00_source" / "metadata.json",
        {
            "source_url": "https://example.invalid/video",
            "canonical_url": "https://example.invalid/video",
            "title": "Fixture Video",
            "speaker_or_channel": "Fixture Speaker",
            "platform": "local",
            "published_at": "",
            "duration": "13",
            "language": "en",
            "source_type": "transcript",
            "collected_at": now_iso(),
            "tools_used": ["self-test"],
            "confidence": "high",
            "notes": "self-test fixture",
        },
    )


def build_audited_fixture(root: Path, *, source_status: str = "source_confirmed", bad_edge: bool = False) -> None:
    evidence_auditor.build_fixture(root, source_status=source_status, bad_edge=bad_edge)
    write_metadata(root)
    status_path = root / "00_source" / "source_status.json"
    status = read_json(status_path)
    status["source_classes"] = ["primary_audio_asr"]
    status["asr_quality"] = {
        "exact_wording_confidence": "medium-low",
        "structural_summary_confidence": "medium",
        "word_timestamp_coverage": 0.0,
        "speaker_coverage": 0.0,
        "alignment_status": "segment_only",
        "diarization_status": "not_available",
        "verified_verbatim": False,
    }
    status["asr_pipeline"] = {
        "quality_report": "00_source/asr_pipeline_report.json",
        "alignment_report": "00_source/asr_alignment_report.json",
        "diarization_report": "00_source/asr_diarization.json",
        "quality": status["asr_quality"],
    }
    evidence_auditor.write_json(status_path, status)
    evidence_auditor.run_evidence_audit(argparse.Namespace(output_root=root, source_status=None))


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="video-pack-builder-") as tmp:
        base = Path(tmp)

        full = base / "full"
        build_audited_fixture(full)
        full_result = run_pack_builder(argparse.Namespace(output_root=full))
        pack_text = (full / "video_analysis_pack.md").read_text(encoding="utf-8")
        assert_true("full pack exists", (full / "video_analysis_pack.md").is_file(), failures)
        assert_true("full pack title", "# Video Analysis Pack" in pack_text, failures)
        assert_true("full pack has sections", "## Claims" in pack_text and "## Gaps" in pack_text, failures)
        assert_true("full pack has asr quality", "## ASR Quality" in pack_text and "Verified verbatim: `false`" in pack_text, failures)
        assert_true("full validation ok", full_result["validation"]["valid"], failures)

        partial = base / "partial"
        build_audited_fixture(partial, source_status="source_partial")
        partial_result = run_pack_builder(argparse.Namespace(output_root=partial))
        partial_text = (partial / "video_analysis_pack.md").read_text(encoding="utf-8")
        assert_true("partial pack exists", (partial / "video_analysis_pack.md").is_file(), failures)
        assert_true("partial scope title", "Partial Scope" in partial_text, failures)
        assert_true("partial validation ok", partial_result["validation"]["valid"], failures)

        bad = base / "bad"
        build_audited_fixture(bad, bad_edge=True)
        try:
            run_pack_builder(argparse.Namespace(output_root=bad))
        except VideoAnalysisPackBuilderError:
            pass
        else:
            failures.append("bad audit: expected VideoAnalysisPackBuilderError")
        assert_true("bad audit no pack", not (bad / "video_analysis_pack.md").exists(), failures)

        missing_audit = base / "missing-audit"
        evidence_auditor.build_fixture(missing_audit)
        write_metadata(missing_audit)
        try:
            run_pack_builder(argparse.Namespace(output_root=missing_audit))
        except VideoAnalysisPackBuilderError:
            pass
        else:
            failures.append("missing audit: expected VideoAnalysisPackBuilderError")
        assert_true("missing audit no pack", not (missing_audit / "video_analysis_pack.md").exists(), failures)

        missing_sidecar = base / "missing-sidecar"
        build_audited_fixture(missing_sidecar)
        (missing_sidecar / "05_gap_check" / "claim_source_audit.json").unlink()
        try:
            run_pack_builder(argparse.Namespace(output_root=missing_sidecar))
        except VideoAnalysisPackBuilderError:
            pass
        else:
            failures.append("missing claim source audit: expected VideoAnalysisPackBuilderError")
        assert_true("missing sidecar no pack", not (missing_sidecar / "video_analysis_pack.md").exists(), failures)

        stale_sidecar = base / "stale-sidecar"
        build_audited_fixture(stale_sidecar)
        stale_map_path = stale_sidecar / "05_gap_check" / "evidence_map.json"
        stale_map = read_json(stale_map_path)
        stale_map["summary"]["entries"] = 999
        evidence_auditor.write_json(stale_map_path, stale_map)
        try:
            run_pack_builder(argparse.Namespace(output_root=stale_sidecar))
        except VideoAnalysisPackBuilderError:
            pass
        else:
            failures.append("stale evidence map summary: expected VideoAnalysisPackBuilderError")
        assert_true("stale sidecar no pack", not (stale_sidecar / "video_analysis_pack.md").exists(), failures)

        mismatched_audit = base / "mismatched-audit"
        build_audited_fixture(mismatched_audit)
        other = base / "other"
        build_audited_fixture(other)
        (mismatched_audit / "05_gap_check" / "evidence_audit.json").write_bytes(
            (other / "05_gap_check" / "evidence_audit.json").read_bytes()
        )
        try:
            run_pack_builder(argparse.Namespace(output_root=mismatched_audit))
        except VideoAnalysisPackBuilderError:
            pass
        else:
            failures.append("mismatched audit root: expected VideoAnalysisPackBuilderError")
        assert_true("mismatched audit no pack", not (mismatched_audit / "video_analysis_pack.md").exists(), failures)

        inconsistent_findings = base / "inconsistent-findings"
        build_audited_fixture(inconsistent_findings)
        audit_path = inconsistent_findings / "05_gap_check" / "evidence_audit.json"
        audit = read_json(audit_path)
        audit["severity_counts"]["error"] = 0
        audit["pack_gate"]["can_build_video_analysis_pack"] = True
        audit["findings"].append({"severity": "error", "code": "self_test_error", "message": "contract mismatch"})
        evidence_auditor.write_json(audit_path, audit)
        try:
            run_pack_builder(argparse.Namespace(output_root=inconsistent_findings))
        except VideoAnalysisPackBuilderError:
            pass
        else:
            failures.append("inconsistent findings: expected VideoAnalysisPackBuilderError")
        assert_true("inconsistent findings no pack", not (inconsistent_findings / "video_analysis_pack.md").exists(), failures)

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
        summary = run_pack_builder(args)
    except VideoAnalysisPackBuilderError as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "output_root": str(args.output_root.expanduser().resolve()) if args.output_root else None,
                "error": "video_analysis_pack_builder_failed",
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
