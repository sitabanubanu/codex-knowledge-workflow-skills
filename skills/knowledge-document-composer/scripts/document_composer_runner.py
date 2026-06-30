#!/usr/bin/env python
"""Create gated document-composer planning artifacts from a video analysis pack."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNNER_NAME = "knowledge-document-composer-runner"
ALLOWED_SOURCE_STATUSES = {"source_confirmed", "source_partial"}
SOURCE_STATUS_TO_DECISION = {
    "source_confirmed": "full",
    "source_partial": "partial",
}
CLAIM_TYPE_TO_CATEGORY = {
    "source_claim": "Source",
    "inferred_claim": "Inference",
    "uncertain_claim": "Inference",
}


class DocumentComposerRunnerError(Exception):
    """Expected CLI-facing document-composer failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def write_text(path: Path, text: str) -> dict[str, Any]:
    target = path.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = normalize_newlines(text).encode("utf-8")
    temp_path = target.parent / f".{target.name}.{os.getpid()}.tmp"
    temp_path.write_bytes(encoded)
    os.replace(temp_path, target)
    readback = target.read_bytes()
    if readback != encoded:
        raise DocumentComposerRunnerError(f"readback mismatch after writing {target}")
    return {"path": str(target), "bytes": len(encoded), "encoding": "utf-8"}


def write_json(path: Path, payload: Any) -> dict[str, Any]:
    return write_text(path, stable_json(payload))


def read_text(path: Path, *, required: bool = True) -> str:
    if not path.is_file():
        if required:
            raise DocumentComposerRunnerError(f"required text file is missing: {path}")
        return ""
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise DocumentComposerRunnerError(f"could not read text file {path}: {exc}") from exc


def read_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise DocumentComposerRunnerError(f"required JSON file is missing: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise DocumentComposerRunnerError(f"invalid JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise DocumentComposerRunnerError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise DocumentComposerRunnerError(f"JSON file is not an object: {path}")
    return payload


def load_list(path: Path, key: str, *, required: bool = True) -> list[dict[str, Any]]:
    payload = read_json(path, required=required)
    values = payload.get(key, [])
    if not isinstance(values, list):
        raise DocumentComposerRunnerError(f"{path.name} must contain a {key} list")
    return [item for item in values if isinstance(item, dict)]


def load_source_status(video_root: Path) -> dict[str, Any]:
    status = read_json(video_root / "00_source" / "source_status.json")
    source_status = status.get("source_status")
    if source_status not in ALLOWED_SOURCE_STATUSES:
        raise DocumentComposerRunnerError(
            f"normal document composition requires source_confirmed or source_partial; got {source_status!r}"
        )
    if not status.get("primary_material_available"):
        raise DocumentComposerRunnerError("normal document composition requires primary_material_available=true")
    return status


def load_evidence_audit(video_root: Path, source_status: str) -> dict[str, Any]:
    audit_path = video_root / "05_gap_check" / "evidence_audit.json"
    audit = read_json(audit_path)
    audit_status = audit.get("source_status")
    if audit_status != source_status:
        raise DocumentComposerRunnerError("evidence audit source_status does not match source status")
    audit_root = Path(str(audit.get("output_root") or "")).expanduser().resolve()
    if audit_root != video_root.expanduser().resolve():
        raise DocumentComposerRunnerError("evidence audit output_root does not match video root")
    counts = audit.get("severity_counts")
    if not isinstance(counts, dict):
        raise DocumentComposerRunnerError("evidence_audit.json is missing severity_counts")
    if int(counts.get("error") or 0) > 0:
        raise DocumentComposerRunnerError("evidence audit has errors; do not compose a normal report")
    findings = audit.get("findings")
    if not isinstance(findings, list):
        raise DocumentComposerRunnerError("evidence_audit.json is missing findings")
    if any(isinstance(finding, dict) and finding.get("severity") == "error" for finding in findings):
        raise DocumentComposerRunnerError("evidence audit findings contain errors; do not compose a normal report")
    gate = audit.get("pack_gate")
    if not isinstance(gate, dict):
        raise DocumentComposerRunnerError("evidence_audit.json is missing pack_gate")
    if source_status == "source_confirmed" and gate.get("can_build_video_analysis_pack") is not True:
        raise DocumentComposerRunnerError("evidence audit does not allow a full pack")
    if source_status == "source_partial" and gate.get("can_build_partial_pack") is not True:
        raise DocumentComposerRunnerError("evidence audit does not allow a partial pack")
    return audit


def compact(text: Any, limit: int = 260) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) > limit:
        return normalized[: limit - 3].rstrip() + "..."
    return normalized


def first_text(*values: Any, default: str = "") -> str:
    for value in values:
        text = compact(value)
        if text:
            return text
    return default


def evidence_ref(item: dict[str, Any], artifact: str) -> dict[str, Any]:
    spans = item.get("evidence_spans")
    if isinstance(spans, list) and spans and isinstance(spans[0], dict):
        span = spans[0]
        return {
            "artifact": artifact,
            "transcript_ids": span.get("transcript_ids") if isinstance(span.get("transcript_ids"), list) else [],
            "start": span.get("start"),
            "end": span.get("end"),
            "quote": compact(span.get("quote"), 180),
            "notes": "Imported from upstream video decomposition.",
        }
    return {
        "artifact": artifact,
        "transcript_ids": [],
        "start": None,
        "end": None,
        "quote": "",
        "notes": "No precise evidence span was available; preserve as a caveat.",
    }


def markdown_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- None recorded."]


def derive_thesis(claims: list[dict[str, Any]]) -> str:
    source_claims = [claim for claim in claims if claim.get("claim_type") == "source_claim"]
    claim = source_claims[0] if source_claims else (claims[0] if claims else {})
    return first_text(claim.get("text"), default="No source thesis candidate was available.")


def render_commitments(
    *,
    source_status: dict[str, Any],
    metadata: dict[str, Any],
    claims: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
    audit: dict[str, Any],
    document_goal: str,
    final_language: str,
    audience: str,
) -> str:
    status = str(source_status.get("source_status"))
    partial = status == "source_partial"
    source_classes = source_status.get("source_classes")
    source_class_text = ", ".join(str(item) for item in source_classes) if isinstance(source_classes, list) else ""
    title = "# Commitments (Partial Scope)" if partial else "# Commitments"
    must_preserve = [
        f"Example `{item.get('id')}`: {first_text(item.get('name'), item.get('description'), default='unnamed example')}"
        for item in examples[:8]
    ]
    must_preserve.extend(
        f"Claim `{item.get('id')}`: {first_text(item.get('text'), default='claim text missing')}"
        for item in claims[:8]
    )
    undefined_concepts = [str(item.get("id")) for item in concepts if not str(item.get("definition_in_source") or "").strip()]
    lines = [
        title,
        "",
        "## Source Status",
        "",
        f"- Source status: `{status}`",
        f"- Composer decision: `{SOURCE_STATUS_TO_DECISION[status]}`",
        f"- Allowed report type: `{source_status.get('allowed_report_type')}`",
        f"- Primary material available: `{str(bool(source_status.get('primary_material_available'))).lower()}`",
        f"- Source classes: {source_class_text or 'not recorded'}",
        f"- Evidence audit warnings: `{audit.get('severity_counts', {}).get('warning', 0)}`",
        f"- Partial scope: `{str(partial).lower()}`",
        "",
        "## Source Question",
        "",
        "- Derive the final source question from `video_analysis_pack.md`, `source_logic.md`, and the user's document goal during drafting.",
        "",
        "## Source Thesis",
        "",
        f"- {derive_thesis(claims)}",
        "",
        "## Narrative Spine",
        "",
        "- Preserve the upstream `Argument Flow` and `Source Logic Summary` before adding interpretation.",
        "",
        "## Target Document Goal",
        "",
        f"- {document_goal}",
        "",
        "## Final Language",
        "",
        f"- {final_language}",
        "",
        "## Audience",
        "",
        f"- {audience}",
        "",
        "## Must-Preserve Evidence",
        "",
        *markdown_list(must_preserve),
        "",
        "## Expansion Boundaries",
        "",
        "- Source reconstruction must stay inside upstream transcript, inventory, source logic, and pack evidence.",
        "- Inference must be labeled and tied to the reasoning bridge.",
        "- Extension must be labeled as user goal, critique, application, or outside synthesis.",
        "- Do not present unverified external claims as source content.",
    ]
    if partial:
        lines.append("- Keep the partial-scope label visible in every downstream artifact.")
    if undefined_concepts:
        lines.append(f"- Concepts without source-local definitions need careful handling: `{undefined_concepts}`.")
    lines.append("")
    return "\n".join(lines)


def render_source_reconstruction(
    *,
    source_status: str,
    segments: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
    source_logic: str,
    gap_check: str,
) -> str:
    title = "# Source Reconstruction (Partial Scope)" if source_status == "source_partial" else "# Source Reconstruction"
    lines = [
        title,
        "",
        "## Core Question",
        "",
        "- Use the source's own opening question or tension from the argument flow. Do not infer missing portions from secondary material.",
        "",
        "## Source Thesis",
        "",
        f"- {derive_thesis(claims)}",
        "",
        "## Language and Argument Flow",
        "",
    ]
    if segments:
        for index, segment in enumerate(segments, start=1):
            lines.append(
                f"{index}. `{segment.get('id')}` `{segment.get('role', 'unknown')}`: "
                f"{first_text(segment.get('title'), segment.get('summary'), default='segment summary missing')}"
            )
    else:
        lines.append("- No argument segments were available; use `video_analysis_pack.md` with lower confidence.")
    lines.extend(["", "## Key Examples", ""])
    for example in examples:
        lines.append(
            f"- `{example.get('id')}` {first_text(example.get('name'), default='Unnamed example')}: "
            f"{first_text(example.get('description'), example.get('what_it_demonstrates'), default='description missing')}"
        )
    if not examples:
        lines.append("- No examples were available.")
    lines.extend(["", "## Key Concepts", ""])
    for concept in concepts:
        lines.append(
            f"- `{concept.get('id')}` {first_text(concept.get('term'), default='Unnamed concept')}: "
            f"{first_text(concept.get('definition_in_source'), concept.get('notes'), default='definition not established')}"
        )
    if not concepts:
        lines.append("- No concepts were available.")
    lines.extend(["", "## Key Claims", ""])
    for claim in claims:
        lines.append(f"- `{claim.get('id')}` `{claim.get('claim_type')}`: {first_text(claim.get('text'), default='claim text missing')}")
    if not claims:
        lines.append("- No claims were available.")
    lines.extend(
        [
            "",
            "## Source Logic Anchor",
            "",
            "- Detailed upstream source logic remains in `10_video/04_logic/source_logic.md`.",
            f"- Local preview: {compact(source_logic, 420) if source_logic.strip() else 'source_logic.md was empty.'}",
            "",
            "## Source Gaps and Ambiguities",
            "",
            "- Detailed gap check remains in `10_video/05_gap_check/gap_check.md`.",
            f"- Local preview: {compact(gap_check, 420) if gap_check.strip() else 'gap_check.md was empty.'}",
            "",
        ]
    )
    return "\n".join(lines)


def build_claim_map(claims: list[dict[str, Any]], source_status: str) -> dict[str, Any]:
    doc_claims: list[dict[str, Any]] = []
    for index, claim in enumerate(claims, start=1):
        claim_type = str(claim.get("claim_type") or "uncertain_claim")
        category = CLAIM_TYPE_TO_CATEGORY.get(claim_type, "Inference")
        status = "accepted" if claim_type == "source_claim" else "uncertain" if claim_type == "uncertain_claim" else "needs_verification"
        if source_status == "source_partial" and category == "Source":
            status = "accepted"
        doc_claims.append(
            {
                "id": f"doc_claim_{index:03d}",
                "upstream_claim_id": claim.get("id"),
                "text": first_text(claim.get("text"), default="Claim text missing."),
                "category": category,
                "source_evidence": [evidence_ref(claim, "10_video/03_inventory/claims.json")],
                "confidence": claim.get("confidence", "medium"),
                "status": status,
                "document_use": "section_claim" if category == "Source" else "caveat",
                "notes": "Imported from upstream claim inventory. Keep category visible during drafting.",
            }
        )
    return {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "source_status": source_status,
        "claims": doc_claims,
    }


def render_expansion_plan(source_status: str, document_goal: str) -> str:
    partial_note = "\n- Because source status is partial, extensions must not fill missing source sequence." if source_status == "source_partial" else ""
    return "\n".join(
        [
            "# Expansion Plan" + (" (Partial Scope)" if source_status == "source_partial" else ""),
            "",
            "## User-Requested Additions",
            "",
            f"- Document goal: {document_goal}",
            "",
            "## Source Logic Available for Extension",
            "",
            "- Use only the audited video analysis pack, source reconstruction, claim map, and gap check as the source base.",
            "",
            "## Compatible Extensions",
            "",
            "- Add applications, critique, or synthesis only after source reconstruction and with an Extension label.",
            "",
            "## Needs External Verification",
            "",
            "- Any factual claim not present in the upstream source material requires external verification before being asserted.",
            "",
            "## Must Not Be Attributed to Source",
            "",
            "- User goals, outside frameworks, recommendations, and critique must not be phrased as the speaker's own claims." + partial_note,
            "",
            "## Integration Strategy",
            "",
            "- Draft source-faithful reconstruction first, then add labeled Inference or Extension sections as needed.",
            "",
        ]
    )


def render_report_outline(source_status: str, final_language: str, document_goal: str) -> str:
    title = "# Report Outline (Partial Scope)" if source_status == "source_partial" else "# Report Outline"
    return "\n".join(
        [
            title,
            "",
            "## Working Title",
            "",
            "- To be finalized during drafting after the source question is stated.",
            "",
            "## Reader Promise",
            "",
            f"- Deliver `{document_goal}` in `{final_language}` while preserving Source / Inference / Extension boundaries.",
            "",
            "## Section Outline",
            "",
            "1. Source status and evidence basis.",
            "2. Core question and source thesis.",
            "3. Source reconstruction in the speaker's sequence.",
            "4. Concrete examples and what they support.",
            "5. Concept map and claim map.",
            "6. Inference or extension section, if useful for the user's goal.",
            "7. Limits, gaps, and final synthesis.",
            "",
            "## Evidence Placement",
            "",
            "- Cite transcript IDs, segment IDs, claim IDs, and upstream artifact names near important Source claims.",
            "",
            "## Source / Inference / Extension Placement",
            "",
            "- Keep Source reconstruction separate from Inference and Extension sections.",
            "",
            "## Open Questions Before Draft",
            "",
            "- Confirm final document type, desired depth, and whether critique or external verification is requested.",
            "",
        ]
    )


def render_quality_check(source_status: str) -> str:
    return "\n".join(
        [
            "# Quality Check",
            "",
            "This is a pre-draft gate generated by `document_composer_runner.py`. It does not approve final delivery.",
            "",
            "## Gate Results",
            "",
            "| Gate | Status | Evidence | Required revision |",
            "| --- | --- | --- | --- |",
            "| Evidence | pass | Upstream evidence audit has no error findings. | Recheck after draft. |",
            "| Example completeness | revise | Examples are listed in planning artifacts. | Draft must explain each important example concretely. |",
            "| Language logic | revise | Source logic is available upstream. | Draft must reconstruct wording and sequence before synthesis. |",
            "| Argument continuity | revise | Argument flow is available in planning artifacts. | Draft must make reasoning bridges explicit. |",
            "| Source / Inference / Extension | pass | Claim map categories are initialized. | Preserve labels in draft and final report. |",
            "| User fit | revise | Document goal and language are recorded. | Confirm draft answers the user's actual requested format. |",
            "| Gap | pass | Upstream gap check is referenced. | Carry gaps into draft. |",
            "| No-empty-abstraction | revise | Planning artifacts warn against abstraction. | Draft must pair abstract labels with concrete evidence. |",
            "| Template coverage | revise | Outline covers required functions. | Draft must implement sections or record omissions. |",
            "",
            "## Final Approval",
            "",
            "- Blocking gates remaining: draft not yet produced.",
            "- Revisions completed: no draft revisions yet.",
            "- Approved to create final_report.md: no",
            f"- Source status: `{source_status}`",
            "",
        ]
    )


def build_intake(
    *,
    video_root: Path,
    document_root: Path,
    source_status: dict[str, Any],
    audit: dict[str, Any],
    document_goal: str,
    final_language: str,
    audience: str,
    files_written: list[str],
) -> dict[str, Any]:
    return {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "video_root": str(video_root),
        "document_root": str(document_root),
        "source_status": source_status.get("source_status"),
        "allowed_report_type": source_status.get("allowed_report_type"),
        "composer_decision": SOURCE_STATUS_TO_DECISION[str(source_status.get("source_status"))],
        "document_goal": document_goal,
        "final_language": final_language,
        "audience": audience,
        "evidence_audit": {
            "severity_counts": audit.get("severity_counts"),
            "pack_gate": audit.get("pack_gate"),
        },
        "files_written": files_written,
        "next_step": "draft_report_with_quality_gates",
    }


def run_document_composer(args: argparse.Namespace) -> dict[str, Any]:
    video_root = args.video_root.expanduser().resolve()
    document_root = args.document_root.expanduser().resolve()
    source_status = load_source_status(video_root)
    status_value = str(source_status.get("source_status"))
    audit = load_evidence_audit(video_root, status_value)
    pack_text = read_text(video_root / "video_analysis_pack.md")
    if not pack_text.strip():
        raise DocumentComposerRunnerError("video_analysis_pack.md is empty")
    metadata = read_json(video_root / "00_source" / "metadata.json", required=False)
    claims = load_list(video_root / "03_inventory" / "claims.json", "claims", required=False)
    examples = load_list(video_root / "03_inventory" / "examples.json", "examples", required=False)
    concepts = load_list(video_root / "03_inventory" / "concepts.json", "concepts", required=False)
    segments = load_list(video_root / "02_segments" / "argument_segments.json", "segments", required=False)
    source_logic = read_text(video_root / "04_logic" / "source_logic.md", required=False)
    gap_check = read_text(video_root / "05_gap_check" / "gap_check.md", required=False)
    document_goal = args.document_goal or "source-faithful knowledge report"
    final_language = args.final_language or "current conversation language"
    audience = args.audience or "reader who needs an auditable source-faithful explanation"

    files: list[dict[str, Any]] = []
    files.append(
        write_text(
            document_root / "commitments.md",
            render_commitments(
                source_status=source_status,
                metadata=metadata,
                claims=claims,
                examples=examples,
                concepts=concepts,
                audit=audit,
                document_goal=document_goal,
                final_language=final_language,
                audience=audience,
            ),
        )
    )
    files.append(
        write_text(
            document_root / "source_reconstruction.md",
            render_source_reconstruction(
                source_status=status_value,
                segments=segments,
                claims=claims,
                examples=examples,
                concepts=concepts,
                source_logic=source_logic,
                gap_check=gap_check,
            ),
        )
    )
    files.append(write_json(document_root / "claim_map.json", build_claim_map(claims, status_value)))
    files.append(write_text(document_root / "expansion_plan.md", render_expansion_plan(status_value, document_goal)))
    files.append(write_text(document_root / "report_outline.md", render_report_outline(status_value, final_language, document_goal)))
    files.append(write_text(document_root / "quality_check.md", render_quality_check(status_value)))
    intake = build_intake(
        video_root=video_root,
        document_root=document_root,
        source_status=source_status,
        audit=audit,
        document_goal=document_goal,
        final_language=final_language,
        audience=audience,
        files_written=[item["path"] for item in files],
    )
    files.append(write_json(document_root / "composer_intake.json", intake))
    return {
        "runner": RUNNER_NAME,
        "video_root": str(video_root),
        "document_root": str(document_root),
        "source_status": status_value,
        "composer_decision": SOURCE_STATUS_TO_DECISION[status_value],
        "files_written": [item["path"] for item in files],
        "final_report_written": (document_root / "final_report.md").exists(),
        "next_step": "draft_report_with_quality_gates",
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create gated document-composer planning artifacts from a video root.")
    parser.add_argument("--video-root", type=Path, required=False, help="Upstream 10_video root containing video_analysis_pack.md.")
    parser.add_argument("--document-root", type=Path, required=False, help="Target 20_document output root.")
    parser.add_argument("--document-goal", default=None, help="User-facing document goal.")
    parser.add_argument("--final-language", default=None, help="Requested final language.")
    parser.add_argument("--audience", default=None, help="Intended audience.")
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


def write_video_fixture(root: Path, *, source_status: str = "source_confirmed", audit_error: bool = False) -> None:
    partial = source_status == "source_partial"
    write_json(
        root / "00_source" / "source_status.json",
        {
            "source_status": source_status,
            "can_enter_full_decomposition": source_status in ALLOWED_SOURCE_STATUSES,
            "can_enter_document_composer": source_status in ALLOWED_SOURCE_STATUSES,
            "allowed_report_type": "partial_video_analysis_pack" if partial else "full_video_analysis_pack",
            "source_classes": ["primary_transcript"],
            "primary_material_available": True,
            "status_reason": "self-test source",
            "failed_probes": [],
            "next_step": "enter_document_composer",
        },
    )
    write_json(
        root / "00_source" / "metadata.json",
        {
            "title": "Fixture Video",
            "speaker_or_channel": "Fixture Speaker",
            "language": "en",
            "source_type": "transcript",
            "confidence": "high",
        },
    )
    write_text(root / "video_analysis_pack.md", "# Video Analysis Pack\n\n## Speaker Thesis\n\n- Preserve evidence.\n")
    write_json(
        root / "05_gap_check" / "evidence_audit.json",
        {
            "runner": "self-test",
            "generated_at": now_iso(),
            "output_root": str(root.expanduser().resolve()),
            "source_status": source_status,
            "severity_counts": {"error": 1 if audit_error else 0, "warning": 0, "info": 0},
            "findings": [{"severity": "error", "code": "bad", "message": "bad"}] if audit_error else [],
            "pack_gate": {
                "can_build_video_analysis_pack": source_status == "source_confirmed" and not audit_error,
                "can_build_partial_pack": source_status == "source_partial" and not audit_error,
                "next_step": "fix_evidence_audit_findings" if audit_error else "enter_video_analysis_pack_builder",
            },
        },
    )
    write_text(root / "05_gap_check" / "gap_check.md", "# Gap Check\n\nNo blocking gaps.\n")
    write_text(root / "04_logic" / "source_logic.md", "# Source Logic\n\nThe source argues for preserving evidence.\n")
    write_json(root / "04_logic" / "logic_graph.json", {"nodes": [], "edges": []})
    write_json(
        root / "02_segments" / "argument_segments.json",
        {
            "segments": [
                {
                    "id": "seg_argument_001",
                    "role": "claim",
                    "title": "Preserve evidence",
                    "summary": "The source argues for preserving transcript evidence.",
                    "transcript_ids": ["t0001"],
                    "evidence_spans": [span(["t0001"], "preserve transcript evidence", 0.0, 4.0)],
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
                    "text": "Reports should preserve transcript evidence.",
                    "claim_type": "source_claim",
                    "evidence_spans": [span(["t0001"], "preserve transcript evidence", 0.0, 4.0)],
                    "confidence": "high",
                },
                {
                    "id": "claim_002",
                    "text": "A downstream report can use this as a quality standard.",
                    "claim_type": "inferred_claim",
                    "evidence_spans": [span(["t0001"], "preserve transcript evidence", 0.0, 4.0)],
                    "confidence": "medium",
                },
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
                    "what_it_demonstrates": "Primary evidence is needed.",
                    "evidence_spans": [span(["t0001"], "metadata alone", 0.0, 4.0)],
                    "linked_claim_ids": ["claim_001"],
                }
            ]
        },
    )
    write_json(
        root / "03_inventory" / "concepts.json",
        {
            "concepts": [
                {
                    "id": "concept_001",
                    "term": "Evidence preservation",
                    "definition_in_source": "Keeping transcript anchors visible.",
                    "evidence_spans": [span(["t0001"], "transcript evidence", 0.0, 4.0)],
                }
            ]
        },
    )
    write_json(root / "03_inventory" / "analogies.json", {"analogies": []})


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="document-composer-") as tmp:
        base = Path(tmp)
        full_video = base / "full" / "10_video"
        full_doc = base / "full" / "20_document"
        write_video_fixture(full_video)
        result = run_document_composer(
            argparse.Namespace(
                video_root=full_video,
                document_root=full_doc,
                document_goal="Write an auditable report",
                final_language="zh-CN",
                audience="workflow reviewer",
            )
        )
        assert_true("full decision", result["composer_decision"] == "full", failures)
        assert_true("commitments written", (full_doc / "commitments.md").is_file(), failures)
        assert_true("claim map written", (full_doc / "claim_map.json").is_file(), failures)
        assert_true("quality check written", (full_doc / "quality_check.md").is_file(), failures)
        assert_true("final not written", not (full_doc / "final_report.md").exists(), failures)
        claim_map = read_json(full_doc / "claim_map.json")
        categories = {claim.get("category") for claim in claim_map.get("claims", [])}
        assert_true("source category", "Source" in categories, failures)
        assert_true("inference category", "Inference" in categories, failures)

        partial_video = base / "partial" / "10_video"
        partial_doc = base / "partial" / "20_document"
        write_video_fixture(partial_video, source_status="source_partial")
        partial_result = run_document_composer(
            argparse.Namespace(
                video_root=partial_video,
                document_root=partial_doc,
                document_goal=None,
                final_language=None,
                audience=None,
            )
        )
        assert_true("partial decision", partial_result["composer_decision"] == "partial", failures)
        assert_true("partial label", "Partial Scope" in (partial_doc / "commitments.md").read_text(encoding="utf-8"), failures)

        bad_video = base / "bad" / "10_video"
        bad_doc = base / "bad" / "20_document"
        write_video_fixture(bad_video, audit_error=True)
        try:
            run_document_composer(
                argparse.Namespace(
                    video_root=bad_video,
                    document_root=bad_doc,
                    document_goal=None,
                    final_language=None,
                    audience=None,
                )
            )
        except DocumentComposerRunnerError:
            pass
        else:
            failures.append("audit error: expected DocumentComposerRunnerError")
        assert_true("bad no commitments", not (bad_doc / "commitments.md").exists(), failures)

        blocked_video = base / "blocked" / "10_video"
        blocked_doc = base / "blocked" / "20_document"
        write_video_fixture(blocked_video, source_status="source_confirmed")
        status = read_json(blocked_video / "00_source" / "source_status.json")
        status["source_status"] = "secondary_only"
        status["primary_material_available"] = False
        write_json(blocked_video / "00_source" / "source_status.json", status)
        try:
            run_document_composer(
                argparse.Namespace(
                    video_root=blocked_video,
                    document_root=blocked_doc,
                    document_goal=None,
                    final_language=None,
                    audience=None,
                )
            )
        except DocumentComposerRunnerError:
            pass
        else:
            failures.append("blocked source: expected DocumentComposerRunnerError")
        assert_true("blocked no commitments", not (blocked_doc / "commitments.md").exists(), failures)

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

    if args.video_root is None or args.document_root is None:
        parser.error("--video-root and --document-root are required unless --self-test is used")

    try:
        summary = run_document_composer(args)
    except DocumentComposerRunnerError as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "video_root": str(args.video_root.expanduser().resolve()) if args.video_root else None,
                "document_root": str(args.document_root.expanduser().resolve()) if args.document_root else None,
                "error": "document_composer_runner_failed",
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
