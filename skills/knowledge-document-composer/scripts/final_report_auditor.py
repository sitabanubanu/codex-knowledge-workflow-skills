#!/usr/bin/env python
"""Audit a document-composer report candidate before final delivery."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from document_composer_runner import (
    DocumentComposerRunnerError,
    emit_json,
    read_json,
    stable_json,
    write_text,
)


RUNNER_NAME = "knowledge-document-final-report-auditor"
ALLOWED_SOURCE_STATUSES = {"source_confirmed", "source_partial"}
KNOWN_SOURCE_STATUSES = {
    "source_confirmed",
    "source_partial",
    "secondary_only",
    "source_blocked",
    "source_failed",
    "degraded_report_only",
}
WEAK_STATUSES = {"needs_verification", "uncertain", "excluded"}
REQUIRED_SECTIONS = ("Source", "Inference", "Extension")
CLAIM_ID_RE = re.compile(r"\bdoc_claim_\d{3,}\b")


class FinalReportAuditorError(Exception):
    """Expected CLI-facing final-report audit failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path, *, required: bool = True) -> str:
    if not path.is_file():
        if required:
            raise FinalReportAuditorError(f"required text file is missing: {path}")
        return ""
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise FinalReportAuditorError(f"could not read text file {path}: {exc}") from exc


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def has_section(report: str, name: str) -> bool:
    return re.search(rf"(?im)^##\s+{re.escape(name)}\s*$", report) is not None


def extract_section(report: str, name: str) -> str:
    pattern = re.compile(rf"(?ims)^##\s+{re.escape(name)}\s*$.*?(?=^##\s+|\Z)")
    match = pattern.search(report)
    return match.group(0) if match else ""


def contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def wants_zh_cn(value: Any) -> bool:
    text = str(value or "").lower()
    return "zh" in text or "chinese" in text or "中文" in text


def wants_english(value: Any) -> bool:
    text = str(value or "").lower().strip()
    return text in {"en", "en-us", "en-gb", "english"}


def language_counts(text: str) -> dict[str, int]:
    cjk = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    latin = sum(1 for char in text if ("a" <= char.lower() <= "z"))
    return {"cjk": cjk, "latin": latin}


def report_matches_language(report: str, final_language: str) -> tuple[bool, str]:
    counts = language_counts(report)
    if wants_zh_cn(final_language):
        if counts["cjk"] >= 80 and counts["cjk"] >= int(counts["latin"] * 0.25):
            return True, f"zh-CN requested; cjk={counts['cjk']}; latin={counts['latin']}."
        return False, f"zh-CN requested but report body is not substantially Chinese; cjk={counts['cjk']}; latin={counts['latin']}."
    if wants_english(final_language):
        if counts["latin"] >= 200 and counts["latin"] >= counts["cjk"]:
            return True, f"English requested; latin={counts['latin']}; cjk={counts['cjk']}."
        return False, f"English requested but report body does not look English-dominant; latin={counts['latin']}; cjk={counts['cjk']}."
    return True, f"No strict language heuristic for final_language={final_language!r}; skipped."


def nonempty_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def gate(name: str, status: str, evidence: str, required_revision: str = "") -> dict[str, str]:
    return {
        "gate": name,
        "status": status,
        "evidence": evidence,
        "required_revision": required_revision,
    }


def gate_status(gates: list[dict[str, str]]) -> bool:
    return all(item["status"] == "pass" for item in gates)


def load_document_state(document_root: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    intake = read_json(document_root / "composer_intake.json")
    source_status = intake.get("source_status")
    if source_status not in KNOWN_SOURCE_STATUSES:
        raise FinalReportAuditorError(
            f"composer_intake.json has unknown source_status; got {source_status!r}"
        )
    intake_root = Path(str(intake.get("document_root") or "")).expanduser().resolve()
    if intake_root != document_root.expanduser().resolve():
        raise FinalReportAuditorError("composer_intake.json document_root does not match audit document root")
    claim_map = read_json(document_root / "claim_map.json", required=source_status in ALLOWED_SOURCE_STATUSES)
    claims = claim_map.get("claims")
    if source_status in ALLOWED_SOURCE_STATUSES and (not isinstance(claims, list) or not claims):
        raise FinalReportAuditorError("claim_map.json must contain a non-empty claims list")
    if not isinstance(claims, list):
        claims = []
    typed_claims = [claim for claim in claims if isinstance(claim, dict)]
    if len(typed_claims) != len(claims):
        raise FinalReportAuditorError("claim_map.json claims must be objects")
    return intake, claim_map, typed_claims


def audit_report(document_root: Path, report_path: Path) -> dict[str, Any]:
    document_root = document_root.expanduser().resolve()
    report_path = report_path.expanduser().resolve()
    intake, _claim_map, claims = load_document_state(document_root)
    report = normalize_newlines(read_text(report_path))
    source_status = str(intake.get("source_status"))
    report_scope = "partial" if source_status == "source_partial" else "full" if source_status == "source_confirmed" else "blocked"
    claims_by_id = {str(claim.get("id")): claim for claim in claims}
    source_claims = [
        claim
        for claim in claims
        if claim.get("category") == "Source" and claim.get("status") == "accepted"
    ]
    source_section = extract_section(report, "Source")
    source_ids = sorted(set(CLAIM_ID_RE.findall(source_section)))
    all_report_ids = sorted(set(CLAIM_ID_RE.findall(report)))
    unknown_ids = [claim_id for claim_id in all_report_ids if claim_id not in claims_by_id]
    invalid_source_ids = [
        claim_id
        for claim_id in source_ids
        if claim_id not in claims_by_id
        or claims_by_id[claim_id].get("category") != "Source"
        or claims_by_id[claim_id].get("status") != "accepted"
    ]
    weak_source_ids = [
        claim_id
        for claim_id in source_ids
        if claim_id in claims_by_id and str(claims_by_id[claim_id].get("status")) in WEAK_STATUSES
    ]
    section_results = [name for name in REQUIRED_SECTIONS if has_section(report, name)]
    partial_label_present = "Partial Scope" in report or "partial scope" in report.lower()
    evidence_limits_present = has_section(report, "Evidence And Limits")
    concrete_examples_present = has_section(report, "Concrete Examples") or contains_any(report, ["example", "examples"])
    language_logic_present = has_section(report, "Language Logic") or contains_any(report, ["language logic", "rhetorical progression", "transition"])
    argument_chain_present = has_section(report, "Argument Chain") or "setup -> tension/problem -> example -> concept shift -> claim -> implication -> conclusion" in report
    document_goal = str(intake.get("document_goal") or "").strip()
    final_language = str(intake.get("final_language") or "").strip()
    report_mentions_goal = bool(document_goal and document_goal in report)
    report_mentions_language = bool(final_language and final_language in report)
    language_ok, language_evidence = report_matches_language(report, final_language)
    no_empty_abstraction_present = bool(source_ids) and contains_any(
        report,
        ["Evidence:", "Reasoning bridge", "claim `doc_claim_", "证据：", "声明 `doc_claim_"],
    )
    template_sections = ["Source Status", "Source", "Inference", "Extension", "Evidence And Limits", "Final Synthesis"]
    template_missing = [name for name in template_sections if not has_section(report, name)]
    gates: list[dict[str, str]] = []
    if source_status not in ALLOWED_SOURCE_STATUSES:
        gates.append(
            gate(
                "Source Eligibility",
                "block",
                f"Normal final reports require source_confirmed or source_partial; got {source_status}.",
                "Produce only a degraded/background note or rerun acquisition with primary transcript/audio material.",
            )
        )
    else:
        gates.append(
            gate(
                "Source Eligibility",
                "pass",
                f"Composer intake permits a {'partial' if source_status == 'source_partial' else 'full'} final report.",
            )
        )
    if source_status not in ALLOWED_SOURCE_STATUSES:
        gates.append(
            gate(
                "Evidence",
                "block",
                "No normal Source-claim audit is allowed for this source status.",
                "Do not create a normal final_report.md from secondary-only, blocked, failed, or degraded material.",
            )
        )
    elif not source_ids:
        gates.append(
            gate(
                "Evidence",
                "block",
                "No registered Source claim ids were found in the Source section.",
                "Cite at least one accepted Source claim id from claim_map.json in the Source section.",
            )
        )
    elif unknown_ids or invalid_source_ids or weak_source_ids:
        gates.append(
            gate(
                "Evidence",
                "block",
                f"unknown={unknown_ids}; invalid_source={invalid_source_ids}; weak_source={weak_source_ids}",
                "Remove unregistered, non-Source, or weak claims from Source, or fix claim_map.json before finalizing.",
            )
        )
    else:
        gates.append(
            gate(
                "Evidence",
                "pass",
                f"Source section cites accepted Source claims: {', '.join(source_ids)}.",
            )
        )
    if len(section_results) == len(REQUIRED_SECTIONS):
        gates.append(gate("Source / Inference / Extension", "pass", "Required sections are present."))
    else:
        missing = [name for name in REQUIRED_SECTIONS if name not in section_results]
        gates.append(
            gate(
                "Source / Inference / Extension",
                "block",
                f"Missing sections: {', '.join(missing)}.",
                "Add visible Source, Inference, and Extension sections before finalizing.",
            )
        )
    if concrete_examples_present:
        gates.append(gate("Example Completeness", "pass", "The report includes an example section or explicit example discussion."))
    else:
        gates.append(
            gate(
                "Example Completeness",
                "block",
                "No concrete example discussion was found.",
                "Add a Concrete Examples section explaining what examples are, why they appear, and what claims they support.",
            )
        )
    if language_logic_present:
        gates.append(gate("Language Logic", "pass", "The report includes language logic, rhetorical progression, or transition discussion."))
    else:
        gates.append(
            gate(
                "Language Logic",
                "block",
                "No language-logic or rhetorical progression discussion was found.",
                "Add a Language Logic section that explains wording, sequence, contrasts, and transitions.",
            )
        )
    if argument_chain_present:
        gates.append(gate("Argument Continuity", "pass", "The report includes an argument chain or the required reasoning path."))
    else:
        gates.append(
            gate(
                "Argument Continuity",
                "block",
                "No argument-chain structure was found.",
                "Add an Argument Chain section that shows setup -> tension/problem -> example -> concept shift -> claim -> implication -> conclusion.",
            )
        )
    if source_status == "source_partial" and not partial_label_present:
        gates.append(
            gate(
                "Partial Scope",
                "block",
                "source_partial intake requires a visible partial-scope label.",
                "Add Partial Scope to the title or source-status section and preserve coverage limits.",
            )
        )
    else:
        gates.append(
            gate(
                "Partial Scope",
                "pass",
                "Partial label is present when required." if source_status == "source_partial" else "Full source status does not require partial label.",
            )
        )
    if report_mentions_goal and report_mentions_language:
        gates.append(gate("User Fit", "pass", "The report repeats the recorded document goal and final language."))
    else:
        gates.append(
            gate(
                "User Fit",
                "block",
                f"document_goal_present={report_mentions_goal}; final_language_present={report_mentions_language}.",
                "State the recorded document goal and final language in the report before finalizing.",
            )
        )
    if language_ok:
        gates.append(gate("Language Match", "pass", language_evidence))
    else:
        gates.append(
            gate(
                "Language Match",
                "block",
                language_evidence,
                "Rewrite the report body in the requested final language before finalizing.",
            )
        )
    if evidence_limits_present and contains_any(extract_section(report, "Evidence And Limits"), ["gap", "limit", "uncertain", "partial", "evidence"]):
        gates.append(gate("Gap", "pass", "Evidence And Limits section names evidence limits or gaps."))
    else:
        gates.append(
            gate(
                "Gap",
                "block",
                "Evidence limits or gaps are not sufficiently marked.",
                "Add an Evidence And Limits section that names source gaps and uncertainty.",
            )
        )
    if no_empty_abstraction_present:
        gates.append(gate("No-Empty-Abstraction", "pass", "The report ties abstract claims to registered claim ids or evidence markers."))
    else:
        gates.append(
            gate(
                "No-Empty-Abstraction",
                "block",
                "The report does not visibly tie abstraction to claim ids or evidence markers.",
                "Ground abstract synthesis in registered claim ids, evidence markers, and reasoning bridges.",
            )
        )
    if len(report.strip()) >= 500 and not template_missing:
        gates.append(gate("Template Coverage", "pass", "Required final-report sections are present and the report is long enough for audit."))
    else:
        gates.append(
            gate(
                "Template Coverage",
                "block",
                f"Report is too short or missing sections: {', '.join(template_missing) if template_missing else 'none'}.",
                "Expand the report using commitments, source reconstruction, claim map, outline, and required final sections.",
            )
        )
    prior_gates_pass = gate_status(gates)
    gates.append(
        gate(
            "Final Approval",
            "pass" if prior_gates_pass else "block",
            "All required machine-readable final gates pass." if prior_gates_pass else "One or more machine-readable final gates block delivery.",
            "" if prior_gates_pass else "Complete required revisions and rerun final_report_auditor.py.",
        )
    )
    approved = gate_status(gates)
    return {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "document_root": str(document_root),
        "report_path": str(report_path),
        "source_status": source_status,
        "report_scope": report_scope,
        "approved_for_final_report": approved,
        "gates": gates,
        "blocking_gates": [item["gate"] for item in gates if item["status"] == "block"],
        "registered_source_claims": [str(claim.get("id")) for claim in source_claims],
        "source_claims_used": source_ids,
        "files_checked": [
            str(document_root / "composer_intake.json"),
            str(document_root / "claim_map.json"),
            str(report_path),
        ],
    }


def render_quality_check(audit: dict[str, Any]) -> str:
    rows = [
        "| Gate | Status | Evidence | Required revision |",
        "| --- | --- | --- | --- |",
    ]
    for item in audit["gates"]:
        rows.append(
            "| {gate} | {status} | {evidence} | {required_revision} |".format(
                gate=item["gate"],
                status=item["status"],
                evidence=str(item["evidence"]).replace("|", "\\|"),
                required_revision=str(item.get("required_revision") or "None.").replace("|", "\\|"),
            )
        )
    approved = "yes" if audit["approved_for_final_report"] else "no"
    blocking = ", ".join(audit["blocking_gates"]) if audit["blocking_gates"] else "None"
    return "\n".join(
        [
            "# Quality Check",
            "",
            "This final quality gate was generated by `final_report_auditor.py`.",
            "",
            "## Machine-Readable Gate",
            "",
            "- See `quality_gate.json`.",
            "",
            "## Gate Results",
            "",
            *rows,
            "",
            "## Final Approval",
            "",
            f"- Blocking gates remaining: {blocking}",
            "- Revisions completed: yes" if audit["approved_for_final_report"] else "- Revisions completed: no",
            f"- Approved to create final_report.md: {approved}",
            "",
        ]
    )


def write_audit_outputs(document_root: Path, audit: dict[str, Any]) -> list[dict[str, Any]]:
    files = [
        write_text(document_root / "quality_gate.json", stable_json(audit)),
        write_text(document_root / "quality_check.md", render_quality_check(audit)),
    ]
    return files


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit a final report candidate.")
    parser.add_argument("--document-root", type=Path, required=False, help="20_document root containing composer artifacts.")
    parser.add_argument("--report-path", type=Path, required=False, help="Report candidate path. Defaults to revised_report.md.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def run_self_test() -> int:
    import argparse as _argparse
    import tempfile

    from document_composer_runner import run_document_composer, write_video_fixture

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="final-report-auditor-") as tmp:
        base = Path(tmp)
        video = base / "full" / "10_video"
        doc = base / "full" / "20_document"
        write_video_fixture(video)
        run_document_composer(
            _argparse.Namespace(
                video_root=video,
                document_root=doc,
                document_goal="Write an auditable final report",
                final_language="en",
                audience="workflow reviewer",
            )
        )
        good_report = doc / "revised_report.md"
        write_text(
            good_report,
            "\n".join(
                [
                    "# Final Report",
                    "",
                    "## Source Status",
                    "",
                    "- Document goal: Write an auditable final report",
                    "- Final language: en",
                    "",
                    "## Source",
                    "",
                    "- Source claim `doc_claim_001`: Reports should preserve transcript evidence. Evidence: self-test transcript fixture.",
                    "",
                    "## Concrete Examples",
                    "",
                    "- Example: the transcript fixture is used to show why source evidence must remain attached to report claims.",
                    "",
                    "## Language Logic",
                    "",
                    "- The report moves from source-backed wording to inference through an explicit transition and rhetorical progression.",
                    "",
                    "## Argument Chain",
                    "",
                    "setup -> tension/problem -> example -> concept shift -> claim -> implication -> conclusion",
                    "",
                    "## Inference",
                    "",
                    "- Inference claim `doc_claim_002`: The workflow can use this as a quality standard.",
                    "",
                    "## Extension",
                    "",
                    "- A downstream extension is to make quality gates machine-readable.",
                    "",
                    "## Evidence And Limits",
                    "",
                    "- Evidence is limited to the self-test transcript fixture and audited claim map.",
                    "",
                    "## Final Synthesis",
                    "",
                    "This candidate includes enough explanatory material to pass the minimum structural audit. "
                    * 8,
                ]
            ),
        )
        audit = audit_report(doc, good_report)
        write_audit_outputs(doc, audit)
        assert_true("good approved", audit["approved_for_final_report"] is True, failures)
        assert_true("quality gate written", (doc / "quality_gate.json").is_file(), failures)

        zh_doc = base / "zh-mismatch" / "20_document"
        zh_doc.mkdir(parents=True)
        write_text(
            zh_doc / "composer_intake.json",
            json.dumps(
                {
                    "document_root": str(zh_doc.resolve()),
                    "source_status": "source_confirmed",
                    "composer_decision": "full",
                    "document_goal": "写一份中文报告",
                    "final_language": "zh-CN",
                    "audience": "中文读者",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )
        write_text(
            zh_doc / "claim_map.json",
            json.dumps(
                {
                    "claims": [
                        {
                            "id": "doc_claim_001",
                            "category": "Source",
                            "status": "accepted",
                            "text": "Reports should preserve transcript evidence.",
                        }
                    ]
                },
                indent=2,
            )
            + "\n",
        )
        zh_mismatch = zh_doc / "revised_report.md"
        write_text(
            zh_mismatch,
            "\n".join(
                [
                    "# Final Report",
                    "",
                    "## Source Status",
                    "",
                    "- Document goal: 写一份中文报告",
                    "- Final language: zh-CN",
                    "",
                    "## Source",
                    "",
                    "- Source claim `doc_claim_001`: Reports should preserve transcript evidence.",
                    "",
                    "## Concrete Examples",
                    "",
                    "- Example: the transcript fixture is used as evidence.",
                    "",
                    "## Language Logic",
                    "",
                    "- The transition and rhetorical progression are explicit.",
                    "",
                    "## Argument Chain",
                    "",
                    "setup -> tension/problem -> example -> concept shift -> claim -> implication -> conclusion",
                    "",
                    "## Inference",
                    "",
                    "- None.",
                    "",
                    "## Extension",
                    "",
                    "- None.",
                    "",
                    "## Evidence And Limits",
                    "",
                    "- Evidence is limited to audited source claims.",
                    "",
                    "## Final Synthesis",
                    "",
                    "This report is intentionally English even though Chinese was requested. " * 10,
                ]
            ),
        )
        mismatch_audit = audit_report(zh_doc, zh_mismatch)
        assert_true("zh mismatch blocked", mismatch_audit["approved_for_final_report"] is False, failures)
        assert_true("zh mismatch language gate", "Language Match" in mismatch_audit["blocking_gates"], failures)

        bad_report = doc / "bad_report.md"
        write_text(
            bad_report,
            "# Bad Report\n\n## Source\n\n- Source claim `doc_claim_999`: unregistered.\n\n## Inference\n\n- None.\n\n## Extension\n\n- None.\n\n## Evidence And Limits\n\n- None.\n",
        )
        bad_audit = audit_report(doc, bad_report)
        assert_true("bad blocked", bad_audit["approved_for_final_report"] is False, failures)
        assert_true("bad evidence blocked", "Evidence" in bad_audit["blocking_gates"], failures)

        partial_video = base / "partial" / "10_video"
        partial_doc = base / "partial" / "20_document"
        write_video_fixture(partial_video, source_status="source_partial")
        run_document_composer(
            _argparse.Namespace(
                video_root=partial_video,
                document_root=partial_doc,
                document_goal="Write a partial report",
                final_language="en",
                audience="workflow reviewer",
            )
        )
        partial_report = partial_doc / "revised_report.md"
        write_text(
            partial_report,
            "\n".join(
                [
                    "# Final Report",
                    "",
                    "## Source Status",
                    "",
                    "- Document goal: Write a partial report",
                    "- Final language: en",
                    "",
                    "## Source",
                    "",
                    "- Source claim `doc_claim_001`: Reports should preserve transcript evidence.",
                    "",
                    "## Concrete Examples",
                    "",
                    "- Example: the partial fixture is used as the covered range.",
                    "",
                    "## Language Logic",
                    "",
                    "- The transition from source to inference is explicit.",
                    "",
                    "## Argument Chain",
                    "",
                    "setup -> tension/problem -> example -> concept shift -> claim -> implication -> conclusion",
                    "",
                    "## Inference",
                    "",
                    "- None.",
                    "",
                    "## Extension",
                    "",
                    "- None.",
                    "",
                    "## Evidence And Limits",
                    "",
                    "- Evidence is partial.",
                    "",
                    "This candidate intentionally lacks the required partial label. " * 10,
                ]
            ),
        )
        partial_audit = audit_report(partial_doc, partial_report)
        assert_true("partial label blocked", "Partial Scope" in partial_audit["blocking_gates"], failures)

        blocked_doc = base / "secondary" / "20_document"
        blocked_doc.mkdir(parents=True)
        write_text(
            blocked_doc / "composer_intake.json",
            json.dumps(
                {
                    "document_root": str(blocked_doc.resolve()),
                    "source_status": "secondary_only",
                    "composer_decision": "degraded",
                },
                indent=2,
            )
            + "\n",
        )
        write_text(blocked_doc / "claim_map.json", json.dumps({"claims": []}) + "\n")
        write_text(blocked_doc / "revised_report.md", "# Report\n")
        blocked_audit = audit_report(blocked_doc, blocked_doc / "revised_report.md")
        assert_true("secondary_only blocked", blocked_audit["approved_for_final_report"] is False, failures)
        assert_true("secondary source eligibility", "Source Eligibility" in blocked_audit["blocking_gates"], failures)

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
    document_root = args.document_root.expanduser().resolve()
    report_path = args.report_path.expanduser().resolve() if args.report_path else document_root / "revised_report.md"
    try:
        audit = audit_report(document_root, report_path)
        files = write_audit_outputs(document_root, audit)
    except (FinalReportAuditorError, DocumentComposerRunnerError) as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "document_root": str(document_root),
                "report_path": str(report_path),
                "error": "final_report_audit_failed",
                "message": str(exc),
            },
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return 1
    summary = dict(audit)
    summary["files_written"] = [item["path"] for item in files]
    emit_json(summary, pretty=args.pretty)
    return 0 if audit["approved_for_final_report"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
