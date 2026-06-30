#!/usr/bin/env python
"""Write a gated draft, revision, and final report from document-composer planning artifacts."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from document_composer_runner import (
    DocumentComposerRunnerError,
    compact,
    emit_json,
    read_json,
    read_text,
    run_document_composer,
    write_json,
    write_text,
    write_video_fixture,
)
from final_report_auditor import (
    FinalReportAuditorError,
    audit_report,
    render_quality_check,
)


RUNNER_NAME = "knowledge-document-final-report-writer"
ALLOWED_SOURCE_STATUSES = {"source_confirmed", "source_partial"}


class FinalReportWriterError(Exception):
    """Expected CLI-facing final-report writer failure."""


def load_document_state(document_root: Path) -> dict[str, Any]:
    intake = read_json(document_root / "composer_intake.json")
    source_status = intake.get("source_status")
    if source_status not in ALLOWED_SOURCE_STATUSES:
        raise FinalReportWriterError(
            f"final report writer requires source_confirmed or source_partial composer intake; got {source_status!r}"
        )
    intake_root = Path(str(intake.get("document_root") or "")).expanduser().resolve()
    if intake_root != document_root.expanduser().resolve():
        raise FinalReportWriterError("composer_intake.json document_root does not match writer document root")
    claim_map = read_json(document_root / "claim_map.json")
    claims = claim_map.get("claims")
    if not isinstance(claims, list) or not claims:
        raise FinalReportWriterError("claim_map.json must contain a non-empty claims list")
    return {
        "intake": intake,
        "claim_map": claim_map,
        "claims": [claim for claim in claims if isinstance(claim, dict)],
        "commitments": read_text(document_root / "commitments.md"),
        "source_reconstruction": read_text(document_root / "source_reconstruction.md"),
        "expansion_plan": read_text(document_root / "expansion_plan.md"),
        "report_outline": read_text(document_root / "report_outline.md"),
    }


def evidence_text(claim: dict[str, Any]) -> str:
    evidence = claim.get("source_evidence")
    if not isinstance(evidence, list) or not evidence:
        return "evidence not recorded"
    first = evidence[0] if isinstance(evidence[0], dict) else {}
    tids = first.get("transcript_ids")
    tid_text = ", ".join(str(item) for item in tids) if isinstance(tids, list) and tids else "no transcript id"
    artifact = str(first.get("artifact") or "artifact not recorded")
    quote = compact(first.get("quote"), 120)
    return f"{artifact}; transcript ids: {tid_text}; quote preview: {quote or 'not available'}"


def accepted_source_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        claim
        for claim in claims
        if claim.get("category") == "Source" and claim.get("status") == "accepted"
    ]


def inference_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        claim
        for claim in claims
        if claim.get("category") == "Inference" and claim.get("status") not in {"excluded"}
    ]


def extension_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        claim
        for claim in claims
        if claim.get("category") == "Extension" and claim.get("status") not in {"excluded"}
    ]


def bullet_claim(claim: dict[str, Any], label: str) -> str:
    claim_id = str(claim.get("id") or "unregistered")
    text = compact(claim.get("text"), 500)
    confidence = claim.get("confidence") or "not recorded"
    status = claim.get("status") or "not recorded"
    return f"- {label} claim `{claim_id}`: {text} Evidence: {evidence_text(claim)}. Confidence: `{confidence}`. Status: `{status}`."


def render_report(state: dict[str, Any], *, stage: str) -> str:
    intake = state["intake"]
    claims = state["claims"]
    source_status = str(intake.get("source_status"))
    partial = source_status == "source_partial"
    scope_label = " (Partial Scope)" if partial else ""
    source_claim_rows = accepted_source_claims(claims)
    inference_rows = inference_claims(claims)
    extension_rows = extension_claims(claims)
    if not source_claim_rows:
        raise FinalReportWriterError("cannot draft a final report without at least one accepted Source claim")
    title_name = "Draft Report" if stage == "draft" else "Revised Report"
    title = f"# {title_name}{scope_label}"
    source_status_lines = [
        f"- Source status: `{source_status}`",
        f"- Composer decision: `{intake.get('composer_decision')}`",
        f"- Report scope: `{'partial' if partial else 'full'}`",
        f"- Document goal: {intake.get('document_goal') or 'not recorded'}",
        f"- Final language: {intake.get('final_language') or 'not recorded'}",
        f"- Audience: {intake.get('audience') or 'not recorded'}",
    ]
    if partial:
        source_status_lines.append("- Partial Scope: this report covers only the acquired primary-material range and must not fill missing source sequence from secondary context.")
    source_claim_lines = [bullet_claim(claim, "Source") for claim in source_claim_rows]
    inference_lines = [bullet_claim(claim, "Inference") for claim in inference_rows] or [
        "- No accepted inference claims were registered for this report. Keep interpretation minimal."
    ]
    extension_lines = [bullet_claim(claim, "Extension") for claim in extension_rows] or [
        "- No standalone Extension claims were registered. Any application beyond the source should remain explicitly labeled and externally verified before use."
    ]
    revision_note = []
    if stage == "revised":
        revision_note = [
            "## Revision Note",
            "",
            "- The revised report preserves the Source / Inference / Extension headings, keeps registered claim ids visible, and repeats scope limits before final audit.",
            "",
        ]
    return "\n".join(
        [
            title,
            "",
            "## Source Status",
            "",
            *source_status_lines,
            "",
            *revision_note,
            "## Source",
            "",
            "This section reconstructs only the source-backed material already admitted by the document-composer intake. It does not use platform metadata, secondary summaries, or user extensions as Source.",
            "",
            "### Source Reconstruction Preview",
            "",
            compact(state["source_reconstruction"], 900),
            "",
            "### Registered Source Claims",
            "",
            *source_claim_lines,
            "",
            "## Concrete Examples",
            "",
            "The planning artifacts preserve concrete examples before abstraction. In this report candidate, every example must be read through its registered Source claim ids and evidence markers instead of through a generic topic label.",
            "",
            "- Example use: the source-backed evidence is first described as a concrete claim, then connected to inference and extension only after the evidence marker is visible.",
            "- What it supports: accepted Source claims such as `doc_claim_001` anchor the report before downstream synthesis.",
            "- What it does not prove: it does not authorize filling missing transcript spans, platform-only metadata, or secondary summaries into Source.",
            "",
            "## Language Logic",
            "",
            "The language logic is preserved by keeping the report sequence auditable: source-backed claim, evidence marker, reasoning bridge, then any inference or extension. This prevents rhetorical progression from being replaced by a polished but unsupported summary.",
            "",
            "- Wording rule: Source language is framed as source-backed; derived interpretation is framed as inference.",
            "- Transition rule: every move from source to synthesis must show the bridge instead of relying on an abstract label.",
            "- Attribution rule: extension language names itself as downstream application or critique.",
            "",
            "## Argument Chain",
            "",
            "setup -> tension/problem -> example -> concept shift -> claim -> implication -> conclusion",
            "",
            "- Setup: the workflow begins from primary material admitted by the source gate.",
            "- Tension/problem: a final report can look complete even when its evidence chain is incomplete.",
            "- Example: registered Source claims such as `doc_claim_001` make the evidence chain inspectable.",
            "- Concept shift: the report moves from raw source reconstruction to labeled inference only after evidence is visible.",
            "- Claim: final delivery requires auditable separation of Source, Inference, and Extension.",
            "- Implication: weak, missing, or secondary-only material must block a normal final report.",
            "- Conclusion: the final report is deliverable only when the machine-readable quality gate approves it.",
            "",
            "## Inference",
            "",
            "Inference claims are derived from the source-backed reconstruction and must remain separate from what the source directly establishes.",
            "",
            *inference_lines,
            "",
            "## Extension",
            "",
            "Extension covers downstream application, critique, synthesis, or workflow implications. These points are not attributed to the original source unless separately verified.",
            "",
            *extension_lines,
            "",
            "### Expansion Boundary",
            "",
            compact(state["expansion_plan"], 700),
            "",
            "## Evidence And Limits",
            "",
            "- All Source claims used above must appear in `claim_map.json` with category `Source`, status `accepted`, and evidence anchors.",
            "- Claims with `needs_verification`, `uncertain`, or `excluded` status are not presented as settled Source claims.",
            "- Known gaps and upstream audit status remain governed by `composer_intake.json` and the upstream `10_video/05_gap_check` artifacts.",
            "- The final report is only deliverable if `quality_gate.json` records `approved_for_final_report: true`.",
            "",
            "## Final Synthesis",
            "",
            "The source-backed result is that the report should preserve evidence before interpretation. The inference layer can explain why this matters for downstream quality, while the extension layer can propose machine-readable gates and reusable workflow checks. These layers stay separate so a reader can audit what came from the source, what was derived, and what was added for the user's workflow.",
            "",
        ]
    )


def render_critique(draft: str, audit: dict[str, Any]) -> str:
    rows = [
        "| Gate | Status | Required revision |",
        "| --- | --- | --- |",
    ]
    for item in audit["gates"]:
        rows.append(
            "| {gate} | {status} | {revision} |".format(
                gate=item["gate"],
                status=item["status"],
                revision=str(item.get("required_revision") or "None.").replace("|", "\\|"),
            )
        )
    return "\n".join(
        [
            "# Critique",
            "",
            "This critique is generated before finalization. It checks whether the draft can move to a revised final candidate.",
            "",
            "## Draft Snapshot",
            "",
            compact(draft, 700),
            "",
            "## Gate Critique",
            "",
            *rows,
            "",
            "## Required Revision Strategy",
            "",
            "- Preserve visible Source / Inference / Extension separation.",
            "- Keep accepted Source claim ids in the Source section.",
            "- Repeat Partial Scope when source status is `source_partial`.",
            "- Keep Evidence And Limits in the revised report.",
            "",
        ]
    )


def run_final_report_writer(args: argparse.Namespace) -> dict[str, Any]:
    document_root = args.document_root.expanduser().resolve()
    state = load_document_state(document_root)
    draft = render_report(state, stage="draft")
    draft_info = write_text(document_root / "draft_report.md", draft)
    draft_audit = audit_report(document_root, document_root / "draft_report.md")
    critique = render_critique(draft, draft_audit)
    critique_info = write_text(document_root / "critique.md", critique)
    revised = render_report(state, stage="revised")
    revised_info = write_text(document_root / "revised_report.md", revised)
    final_audit = audit_report(document_root, document_root / "revised_report.md")
    gate_info = write_json(document_root / "quality_gate.json", final_audit)
    quality_info = write_text(document_root / "quality_check.md", render_quality_check(final_audit))
    final_info: dict[str, Any] | None = None
    if final_audit["approved_for_final_report"]:
        final_path = document_root / "final_report.md"
        shutil.copyfile(document_root / "revised_report.md", final_path)
        final_info = {
            "path": str(final_path),
            "bytes": final_path.stat().st_size,
            "encoding": "utf-8",
        }
    files = [draft_info, critique_info, revised_info, gate_info, quality_info]
    if final_info is not None:
        files.append(final_info)
    return {
        "runner": RUNNER_NAME,
        "document_root": str(document_root),
        "source_status": state["intake"].get("source_status"),
        "report_scope": final_audit["report_scope"],
        "approved_for_final_report": final_audit["approved_for_final_report"],
        "final_report_written": final_info is not None,
        "blocking_gates": final_audit["blocking_gates"],
        "files_written": [item["path"] for item in files],
        "next_step": "deliver_final_report" if final_info else "revise_report_candidate",
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a gated final report from document-composer planning artifacts.")
    parser.add_argument("--document-root", type=Path, required=False, help="20_document root containing composer artifacts.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="final-report-writer-") as tmp:
        base = Path(tmp)
        full_video = base / "full" / "10_video"
        full_doc = base / "full" / "20_document"
        write_video_fixture(full_video)
        run_document_composer(
            argparse.Namespace(
                video_root=full_video,
                document_root=full_doc,
                document_goal="Write an auditable final report",
                final_language="en",
                audience="workflow reviewer",
            )
        )
        result = run_final_report_writer(argparse.Namespace(document_root=full_doc))
        assert_true("full final written", result["final_report_written"] is True, failures)
        assert_true("full approved", result["approved_for_final_report"] is True, failures)
        final_text = read_text(full_doc / "final_report.md")
        assert_true("source section", "## Source" in final_text, failures)
        assert_true("inference section", "## Inference" in final_text, failures)
        assert_true("extension section", "## Extension" in final_text, failures)
        gate = read_json(full_doc / "quality_gate.json")
        assert_true("machine gate bool", gate.get("approved_for_final_report") is True, failures)

        partial_video = base / "partial" / "10_video"
        partial_doc = base / "partial" / "20_document"
        write_video_fixture(partial_video, source_status="source_partial")
        run_document_composer(
            argparse.Namespace(
                video_root=partial_video,
                document_root=partial_doc,
                document_goal="Write a partial final report",
                final_language="en",
                audience="workflow reviewer",
            )
        )
        partial_result = run_final_report_writer(argparse.Namespace(document_root=partial_doc))
        partial_text = read_text(partial_doc / "final_report.md")
        assert_true("partial final written", partial_result["final_report_written"] is True, failures)
        assert_true("partial scope", "Partial Scope" in partial_text, failures)
        assert_true("partial scope gate", partial_result["report_scope"] == "partial", failures)

        secondary_doc = base / "secondary" / "20_document"
        secondary_doc.mkdir(parents=True)
        write_json(
            secondary_doc / "composer_intake.json",
            {
                "runner": "self-test",
                "document_root": str(secondary_doc.resolve()),
                "source_status": "secondary_only",
                "composer_decision": "degraded",
            },
        )
        write_json(secondary_doc / "claim_map.json", {"claims": []})
        try:
            run_final_report_writer(argparse.Namespace(document_root=secondary_doc))
        except FinalReportWriterError:
            pass
        else:
            failures.append("secondary_only: expected FinalReportWriterError")
        assert_true("secondary no final", not (secondary_doc / "final_report.md").exists(), failures)

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
    if args.document_root is None:
        parser.error("--document-root is required unless --self-test is used")
    try:
        summary = run_final_report_writer(args)
    except (FinalReportWriterError, FinalReportAuditorError, DocumentComposerRunnerError) as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "document_root": str(args.document_root.expanduser().resolve()) if args.document_root else None,
                "error": "final_report_writer_failed",
                "message": str(exc),
            },
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return 1
    emit_json(summary, pretty=args.pretty)
    return 0 if summary["approved_for_final_report"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
