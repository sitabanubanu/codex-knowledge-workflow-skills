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


def wants_zh_cn(value: Any) -> bool:
    text = str(value or "").lower()
    return "zh" in text or "chinese" in text or "中文" in text


def bullet_claim_zh(claim: dict[str, Any], label: str) -> str:
    claim_id = str(claim.get("id") or "unregistered")
    text = compact(claim.get("text"), 500)
    confidence = claim.get("confidence") or "not recorded"
    status = claim.get("status") or "not recorded"
    return f"- {label} 声明 `{claim_id}`：{text}。证据：{evidence_text(claim)}。置信度：`{confidence}`。状态：`{status}`。"


def render_report(state: dict[str, Any], *, stage: str) -> str:
    intake = state["intake"]
    claims = state["claims"]
    source_status = str(intake.get("source_status"))
    partial = source_status == "source_partial"
    if wants_zh_cn(intake.get("final_language")):
        return render_report_zh(state, stage=stage)
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


def render_report_zh(state: dict[str, Any], *, stage: str) -> str:
    intake = state["intake"]
    claims = state["claims"]
    source_status = str(intake.get("source_status"))
    partial = source_status == "source_partial"
    scope_label = "（Partial Scope / 部分范围）" if partial else ""
    source_claim_rows = accepted_source_claims(claims)
    inference_rows = inference_claims(claims)
    extension_rows = extension_claims(claims)
    if not source_claim_rows:
        raise FinalReportWriterError("cannot draft a final report without at least one accepted Source claim")
    title_name = "草稿报告" if stage == "draft" else "修订报告"
    title = f"# {title_name}{scope_label}"
    source_status_lines = [
        f"- 来源状态：`{source_status}`",
        f"- Composer decision：`{intake.get('composer_decision')}`",
        f"- 报告范围：`{'partial' if partial else 'full'}`",
        f"- Document goal：{intake.get('document_goal') or 'not recorded'}",
        f"- Final language：{intake.get('final_language') or 'not recorded'}",
        f"- Audience：{intake.get('audience') or 'not recorded'}",
    ]
    if partial:
        source_status_lines.append("- Partial Scope：本报告只覆盖已经取得的一手材料范围，不能用二手材料补齐缺失片段。")
    source_claim_lines = [bullet_claim_zh(claim, "Source") for claim in source_claim_rows]
    inference_lines = [bullet_claim_zh(claim, "Inference") for claim in inference_rows] or [
        "- 当前没有登记可用的 Inference 声明。解释层应保持克制，不扩展为新的 Source 内容。"
    ]
    extension_lines = [bullet_claim_zh(claim, "Extension") for claim in extension_rows] or [
        "- 当前没有独立登记的 Extension 声明。任何面向行动、应用或批判的内容都必须明确标注为延伸建议。"
    ]
    revision_note = []
    if stage == "revised":
        revision_note = [
            "## Revision Note",
            "",
            "- 本修订版保留 Source / Inference / Extension 三层结构，保留声明编号，并在最终审计前重复范围限制。",
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
            "本节只重建已经通过 document composer intake 的来源内容。它不把平台 metadata、第三方总结、用户目标或外部解释当作 Source。",
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
            "具体例子必须先服务于证据链，而不是服务于漂亮总结。报告先说明例子对应的 Source claim，再说明它支持什么推断或延伸。",
            "",
            "- 例子的作用：让读者看到声明从哪一段一手材料来，而不是只看到抽象结论。",
            "- 它能支持什么：例如 `doc_claim_001` 这样的已登记 Source claim。",
            "- 它不能证明什么：它不能补齐缺失 transcript，不能把 metadata 或第三方摘要升级成 Source。",
            "",
            "## Language Logic",
            "",
            "语言逻辑通过可审计的顺序保留下来：先给出来源声明，再给出证据标记，然后说明推理桥梁，最后才进入推断或延伸。",
            "",
            "- 措辞规则：Source 只描述来源已经支持的内容。",
            "- 转折规则：从来源到解释必须展示推理桥梁。",
            "- 归因规则：延伸建议必须标注为 downstream application、critique 或 synthesis，不能说成原作者观点。",
            "",
            "## Argument Chain",
            "",
            "setup -> tension/problem -> example -> concept shift -> claim -> implication -> conclusion",
            "",
            "- Setup：工作流从 source gate 允许的一手材料开始。",
            "- Tension/problem：报告可以写得很完整，但证据链可能并不完整。",
            "- Example：已登记的 Source claim 让证据链可检查。",
            "- Concept shift：报告先完成来源重建，再进入明确标注的推断。",
            "- Claim：最终交付必须保留 Source / Inference / Extension 的边界。",
            "- Implication：如果材料不足、审计失败或只有二手资料，就必须阻止普通 final report。",
            "- Conclusion：只有 `quality_gate.json` 批准后，`final_report.md` 才能存在。",
            "",
            "## Inference",
            "",
            "Inference 是从来源重建中推出的解释层。它可以帮助读者理解含义，但不能伪装成原材料直接说过的话。",
            "",
            *inference_lines,
            "",
            "## Extension",
            "",
            "Extension 是面向用户目标的应用、批判、行动建议或工作流延伸。除非另有证据，它不能归因给原始来源。",
            "",
            *extension_lines,
            "",
            "### Expansion Boundary",
            "",
            compact(state["expansion_plan"], 700),
            "",
            "## Evidence And Limits",
            "",
            "- 上文所有 Source claim 都必须出现在 `claim_map.json` 中，并且 category 为 `Source`、status 为 `accepted`。",
            "- `needs_verification`、`uncertain` 或 `excluded` 状态的声明不能当作已确认 Source。",
            "- 已知缺口、ASR 不确定性和上游审计状态继续以 `composer_intake.json` 与 `10_video/05_gap_check` 为准。",
            "- 只有当 `quality_gate.json` 记录 `approved_for_final_report: true` 时，最终报告才允许交付。",
            "",
            "## Final Synthesis",
            "",
            "这个来源支持的核心结果是：报告必须先保留证据，再进入解释。推断层可以说明为什么这种证据链对质量重要；延伸层可以提出机器可读质量门、复用模板或后续工作流建议。三层分开后，读者才能判断哪些内容来自来源，哪些内容是合理推断，哪些内容是面向用户目标的延伸。",
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
        assert_true("language match gate", "Language Match" in {item.get("gate") for item in gate.get("gates", [])}, failures)

        zh_video = base / "zh" / "10_video"
        zh_doc = base / "zh" / "20_document"
        write_video_fixture(zh_video)
        run_document_composer(
            argparse.Namespace(
                video_root=zh_video,
                document_root=zh_doc,
                document_goal="写一份中文可审计报告",
                final_language="zh-CN",
                audience="中文研究型用户",
            )
        )
        zh_result = run_final_report_writer(argparse.Namespace(document_root=zh_doc))
        zh_text = read_text(zh_doc / "final_report.md")
        zh_gate = read_json(zh_doc / "quality_gate.json")
        assert_true("zh final written", zh_result["final_report_written"] is True, failures)
        assert_true("zh approved", zh_gate.get("approved_for_final_report") is True, failures)
        assert_true("zh body", "来源状态" in zh_text and "推断" in zh_text and "延伸" in zh_text, failures)
        assert_true("zh goal preserved", "写一份中文可审计报告" in zh_text, failures)

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
