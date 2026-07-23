#!/usr/bin/env python
"""Create a user-facing result index for a knowledge workflow project."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from workflow_provenance import inspect_provenance, sha256_file


RUNNER_NAME = "knowledge-workflow-result-index-writer"
BLOCKING_SOURCE_STATES = {"secondary_only", "source_blocked", "source_failed", "degraded_report_only"}


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def relpath(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def file_entry(root: Path, label: str, path: Path) -> dict[str, Any]:
    return {"label": label, "path": relpath(root, path), "exists": path.is_file()}


def choose_status(
    *,
    run_state: dict[str, Any],
    source_state: str,
    final_report_exists: bool,
    pack_exists: bool,
    transcript_exists: bool,
    quality_approved: bool,
    preflight_exists: bool,
) -> str:
    if final_report_exists and quality_approved:
        return "success"
    if run_state.get("status") == "failed":
        return "failed"
    if source_state in BLOCKING_SOURCE_STATES or run_state.get("workflow_outcome") == "degraded_acquisition_only":
        return "degraded"
    if pack_exists:
        return "analysis_ready"
    if transcript_exists:
        return "transcript_ready"
    if preflight_exists:
        return "preflight_ready"
    return "unknown"


def action_items(status: str, user_action: str, *, learning_article_exists: bool = False) -> list[str]:
    if status == "success":
        if learning_article_exists:
            return [
                "Read 20_document/learning_article.md first.",
                "Use 15_learning/learning_analysis_pack.md to inspect the knowledge map and learning path.",
                "Use 20_document/learning_quality_gate.json to inspect learning-quality approval details.",
            ]
        return [
            "Read 20_document/final_report.md first.",
            "Use 10_video/video_analysis_pack.md when you need the structured source decomposition.",
            "Use 20_document/quality_gate.json when you need to inspect final approval details.",
        ]
    if status == "analysis_ready":
        return [
            "Run the document final writer to create 20_document/final_report.md.",
            "Inspect 10_video/05_gap_check/evidence_audit.json before treating the report as source-grounded.",
        ]
    if status == "transcript_ready":
        return [
            "Continue segmentation, inventory extraction, source logic, evidence audit, and pack building.",
            "Use the resume flag if this project was interrupted mid-run.",
        ]
    if status == "degraded":
        items = []
        if user_action:
            items.append(str(user_action))
        items.extend([
            "Provide a subtitle or transcript file when available.",
            "Provide a local audio or video file when ASR is acceptable.",
            "Provide a user-exported cookies.txt only when you are authorized to access the same page.",
            "Use quick mode only when a non-primary triage is enough.",
        ])
        return items
    if status == "failed":
        return [
            "Read logs/run_state.json for the failed stage and retry hint.",
            "Fix the missing input, dependency, or upstream artifact before resuming.",
            "Run the status command again after the retry.",
        ]
    if status == "preflight_ready":
        return [
            "Run the workflow if the estimated route and required user actions are acceptable.",
            "Prefer the local transcript demo before trying unstable platform URLs.",
        ]
    if user_action:
        return [str(user_action)]
    return ["Run preflight or acquisition to determine the next safe route."]


def build_result(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    logs_root = project_root / "logs"
    video_root = project_root / "10_video"
    learning_root = project_root / "15_learning"
    document_root = project_root / "20_document"
    acquisition_root = project_root / "00_acquisition"

    run_state = read_json(logs_root / "run_state.json")
    acquisition_manifest = read_json(acquisition_root / "manifest.json")
    source_status = read_json(video_root / "00_source" / "source_status.json")
    quality_gate = read_json(document_root / "quality_gate.json")
    learning_quality_gate = read_json(document_root / "learning_quality_gate.json")
    platform_result = read_json(video_root / "00_source" / "platform_media_result.json")
    preflight = read_json(logs_root / "preflight.json")
    provenance = inspect_provenance(project_root)

    source_state = source_status.get("source_status") or run_state.get("source_status") or "unknown"
    raw_final_report_exists = (document_root / "final_report.md").is_file()
    raw_learning_article_exists = (document_root / "learning_article.md").is_file()
    raw_learning_pack_exists = (learning_root / "learning_analysis_pack.json").is_file()
    raw_pack_exists = (video_root / "video_analysis_pack.md").is_file() or (video_root / "source_analysis_pack.md").is_file()
    raw_transcript_exists = (video_root / "01_transcript" / "clean_transcript.jsonl").is_file()
    final_report_exists = bool(provenance["final_report_current"])
    learning_article_exists = bool(provenance["learning_article_current"])
    learning_analysis_exists = bool(provenance["learning_analysis_current"])
    pack_exists = bool(provenance["analysis_current"])
    transcript_exists = bool(provenance["gate_current"] and raw_transcript_exists)
    quality_approved = bool(
        (final_report_exists and quality_gate.get("approved_for_final_report"))
        or (learning_article_exists and learning_quality_gate.get("approved_for_learning_article"))
    )
    full_allowed = bool(provenance["gate_current"] and source_status.get("can_enter_full_decomposition")) and source_state in {"source_confirmed", "source_partial"}
    stale_output_files_present = bool(
        (raw_final_report_exists and not final_report_exists)
        or (raw_learning_article_exists and not learning_article_exists)
        or (raw_learning_pack_exists and not learning_analysis_exists)
        or (raw_pack_exists and not pack_exists)
        or (raw_transcript_exists and not transcript_exists)
    )
    material_decision = platform_result.get("material_decision") if isinstance(platform_result, dict) else {}
    material_decision = material_decision if isinstance(material_decision, dict) else {}

    status = choose_status(
        run_state=run_state,
        source_state=source_state,
        final_report_exists=final_report_exists or learning_article_exists,
        pack_exists=pack_exists,
        transcript_exists=transcript_exists,
        quality_approved=quality_approved,
        preflight_exists=bool(preflight),
    )
    reason = (
        run_state.get("failure_reason")
        or run_state.get("degraded_reason")
        or material_decision.get("reason")
        or source_status.get("status_reason")
        or ""
    )
    user_action = (
        run_state.get("user_action_required")
        or source_status.get("next_step")
        or material_decision.get("next_step")
        or ""
    )
    if status == "success":
        reason = (
            "Learning article exists and the learning quality gate approved it."
            if learning_article_exists
            else "Final report exists and the quality gate approved it."
        )
        user_action = ""
    elif stale_output_files_present and not reason:
        reason = "Output files exist, but their provenance receipts do not match the current acquisition run."

    key_files = [
        file_entry(project_root, "Result index", project_root / "result_index.md"),
        file_entry(project_root, "Acquisition manifest", acquisition_root / "manifest.json"),
        file_entry(project_root, "Preflight", logs_root / "preflight.md"),
        file_entry(project_root, "Run state", logs_root / "run_state.json"),
        file_entry(project_root, "Source status", video_root / "00_source" / "source_status.json"),
        file_entry(project_root, "Clean transcript", video_root / "01_transcript" / "clean_transcript.jsonl"),
        file_entry(project_root, "Evidence audit", video_root / "05_gap_check" / "evidence_audit.json"),
        file_entry(project_root, "Video analysis pack", video_root / "video_analysis_pack.md"),
        file_entry(project_root, "Learning analysis pack", learning_root / "learning_analysis_pack.md"),
        file_entry(project_root, "Learning path", learning_root / "learning_path.json"),
        file_entry(project_root, "Learning quality gate", document_root / "learning_quality_gate.json"),
        file_entry(project_root, "Learning article", document_root / "learning_article.md"),
        file_entry(project_root, "Quality gate", document_root / "quality_gate.json"),
        file_entry(project_root, "Final report", document_root / "final_report.md"),
    ]

    return {
        "runner": RUNNER_NAME,
        "project_root": str(project_root),
        "status": status,
        "acquisition_status": acquisition_manifest.get("status") or run_state.get("acquisition_status") or "unknown",
        "mode": run_state.get("mode") or preflight.get("requested_mode") or "unknown",
        "source_status": source_state,
        "primary_material_available": bool(source_status.get("primary_material_available")),
        "full_analysis_allowed": full_allowed,
        "video_analysis_pack_exists": pack_exists,
        "final_report_exists": final_report_exists,
        "learning_analysis_pack_exists": learning_analysis_exists,
        "learning_article_exists": learning_article_exists,
        "quality_gate_approved": quality_approved,
        "gate_provenance_current": bool(provenance["gate_current"]),
        "analysis_provenance_current": bool(provenance["analysis_current"]),
        "learning_analysis_provenance_current": bool(provenance["learning_analysis_current"]),
        "final_report_provenance_current": bool(provenance["final_report_current"]),
        "learning_article_provenance_current": bool(provenance["learning_article_current"]),
        "stale_output_files_present": stale_output_files_present,
        "reason": reason,
        "user_action_required": user_action,
        "next_actions": action_items(status, str(user_action or ""), learning_article_exists=learning_article_exists),
        "key_files": key_files,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Workflow Result",
        "",
        f"- Status: `{payload['status']}`",
        f"- Acquisition status: `{payload.get('acquisition_status', 'unknown')}`",
        f"- Mode: `{payload['mode']}`",
        f"- Source status: `{payload['source_status']}`",
        f"- Primary material available: `{payload['primary_material_available']}`",
        f"- Full analysis allowed: `{payload['full_analysis_allowed']}`",
        f"- Video analysis pack exists: `{payload['video_analysis_pack_exists']}`",
        f"- Final report exists: `{payload['final_report_exists']}`",
        f"- Learning analysis pack exists: `{payload['learning_analysis_pack_exists']}`",
        f"- Learning article exists: `{payload['learning_article_exists']}`",
        f"- Quality gate approved: `{payload['quality_gate_approved']}`",
        f"- Gate provenance current: `{payload['gate_provenance_current']}`",
        f"- Analysis provenance current: `{payload['analysis_provenance_current']}`",
        f"- Learning analysis provenance current: `{payload['learning_analysis_provenance_current']}`",
        f"- Final report provenance current: `{payload['final_report_provenance_current']}`",
        f"- Learning article provenance current: `{payload['learning_article_provenance_current']}`",
        f"- Stale output files present: `{payload['stale_output_files_present']}`",
        "",
    ]
    if payload.get("reason"):
        lines.extend(["## Why", "", str(payload["reason"]), ""])

    lines.extend(["## Start Here", ""])
    for index, action in enumerate(payload.get("next_actions") or [], start=1):
        lines.append(f"{index}. {action}")
    lines.append("")

    lines.extend(["## Key Files", "", "| File | Path | Exists |", "| --- | --- | --- |"])
    for item in payload.get("key_files") or []:
        lines.append(f"| {item['label']} | `{item['path']}` | `{item['exists']}` |")
    lines.append("")

    if not payload.get("full_analysis_allowed"):
        lines.extend(
            [
                "## Important",
                "",
                "A complete video analysis requires first-hand transcript, subtitles, browser-visible transcript, or transcribable local media. Metadata, screenshots, search snippets, and secondary summaries cannot unlock a full report.",
                "",
            ]
        )
    return "\n".join(lines)


def write_result_index(project_root: Path, *, output_md: Path | None = None, output_json: Path | None = None) -> dict[str, Any]:
    payload = build_result(project_root)
    root = Path(payload["project_root"])
    md_path = output_md or root / "result_index.md"
    json_path = output_json or root / "logs" / "result_index.json"
    for item in payload.get("key_files") or []:
        if item.get("label") == "Result index":
            item["path"] = relpath(root, md_path)
            item["exists"] = True
    write_text(md_path, render_markdown(payload))
    write_json(json_path, payload)
    payload["result_index"] = str(md_path)
    payload["result_index_json"] = str(json_path)
    return payload


def self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        stale_root = Path(tmp) / "stale"
        write_json(
            stale_root / "10_video" / "00_source" / "source_status.json",
            {
                "source_status": "source_confirmed",
                "can_enter_full_decomposition": True,
                "primary_material_available": True,
                "status_reason": "primary transcript is available",
            },
        )
        write_json(stale_root / "20_document" / "quality_gate.json", {"approved_for_final_report": True})
        write_text(stale_root / "20_document" / "final_report.md", "# Old Final Report\n")
        stale = write_result_index(stale_root)
        assert stale["status"] != "success", stale
        assert stale["stale_output_files_present"] is True, stale

        root = Path(tmp) / "success"
        manifest_path = root / "00_acquisition" / "manifest.json"
        write_json(manifest_path, {"schema_version": 2, "status": "material_acquired"})
        ids = {
            "run_id": "run_fixture",
            "bundle_id": "bundle_fixture",
            "source_id": "source_fixture",
            "source_fingerprint": "fingerprint_fixture",
            "analysis_target": "video_content",
            "gate_input_sha256": sha256_file(manifest_path),
        }
        source_status_path = root / "10_video" / "00_source" / "source_status.json"
        write_json(
            source_status_path,
            {
                **ids,
                "source_status": "source_confirmed",
                "can_enter_full_decomposition": True,
                "primary_material_available": True,
            },
        )
        gate_path = root / "10_video" / "00_source" / "gate_receipt.json"
        write_json(gate_path, {**ids, "source_status": "source_confirmed", "source_status_sha256": sha256_file(source_status_path)})
        pack_path = root / "10_video" / "video_analysis_pack.md"
        write_text(pack_path, "# Analysis Pack\n")
        analysis_path = root / "10_video" / "analysis_receipt.json"
        write_json(
            analysis_path,
            {
                **ids,
                "source_status": "source_confirmed",
                "analysis_pack": "video_analysis_pack.md",
                "analysis_pack_sha256": sha256_file(pack_path),
                "gate_receipt_sha256": sha256_file(gate_path),
            },
        )
        claim_map = root / "20_document" / "claim_map.json"
        intake = root / "20_document" / "composer_intake.json"
        write_json(claim_map, {"claims": [{"id": "doc_claim_001"}]})
        write_json(intake, {"source_status": "source_confirmed"})
        composer_path = root / "20_document" / "composer_receipt.json"
        write_json(
            composer_path,
            {
                **ids,
                "source_status": "source_confirmed",
                "analysis_receipt_sha256": sha256_file(analysis_path),
                "claim_map_sha256": sha256_file(claim_map),
                "composer_intake_sha256": sha256_file(intake),
            },
        )
        quality_path = root / "20_document" / "quality_gate.json"
        final_path = root / "20_document" / "final_report.md"
        write_json(quality_path, {"approved_for_final_report": True})
        write_text(final_path, "# Final Report\n")
        write_json(
            root / "20_document" / "final_report_receipt.json",
            {
                **ids,
                "source_status": "source_confirmed",
                "composer_receipt_sha256": sha256_file(composer_path),
                "quality_gate_sha256": sha256_file(quality_path),
                "final_report_sha256": sha256_file(final_path),
            },
        )
        success = write_result_index(root)
        assert success["status"] == "success", success
        assert (root / "result_index.md").is_file()

        learning_pack = root / "15_learning" / "learning_analysis_pack.json"
        learning_receipt = root / "15_learning" / "learning_analysis_receipt.json"
        reanalysis_validation = root / "15_learning" / "source_reanalysis_validation.json"
        learning_quality = root / "20_document" / "learning_quality_gate.json"
        learning_article = root / "20_document" / "learning_article.md"
        write_json(learning_pack, {"schema_version": "learning-analysis-pack.v1", "knowledge_map": {}})
        write_json(
            reanalysis_validation,
            {
                "schema_version": "learning-source-reanalysis-validation.v1",
                "mode": "normal",
                "approved_for_learning_analysis": True,
            },
        )
        write_json(
            learning_receipt,
            {
                **ids,
                "source_status": "source_confirmed",
                "analysis_receipt_sha256": sha256_file(analysis_path),
                "learning_analysis_pack": "learning_analysis_pack.json",
                "learning_analysis_pack_sha256": sha256_file(learning_pack),
                "source_reanalysis_mode": "normal",
                "source_reanalysis_validation": "source_reanalysis_validation.json",
                "source_reanalysis_validation_sha256": sha256_file(reanalysis_validation),
                "enrichment_path": "",
                "enrichment_sha256": "",
            },
        )
        write_json(learning_quality, {"approved_for_learning_article": True, "blocking_gates": []})
        write_text(learning_article, "# Learning Article\n")
        write_json(
            root / "20_document" / "learning_article_receipt.json",
            {
                **ids,
                "source_status": "source_confirmed",
                "learning_analysis_receipt_sha256": sha256_file(learning_receipt),
                "learning_quality_gate_sha256": sha256_file(learning_quality),
                "learning_article_sha256": sha256_file(learning_article),
                "approved_for_learning_article": True,
            },
        )
        learning_success = write_result_index(root)
        assert learning_success["learning_analysis_pack_exists"] is True, learning_success
        assert learning_success["learning_article_exists"] is True, learning_success
        assert learning_success["status"] == "success", learning_success
        assert "learning_article.md" in learning_success["next_actions"][0], learning_success

        degraded = Path(tmp) / "degraded"
        write_json(
            degraded / "10_video" / "00_source" / "source_status.json",
            {
                "source_status": "secondary_only",
                "can_enter_full_decomposition": False,
                "primary_material_available": False,
                "status_reason": "metadata only",
                "next_step": "request_primary_material",
            },
        )
        degraded_payload = write_result_index(degraded)
        assert degraded_payload["status"] == "degraded", degraded_payload
        assert "metadata only" in (degraded / "result_index.md").read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a user-facing result_index.md for a workflow project.")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("result_index_writer self-test passed")
        return 0
    if args.project_root is None:
        parser.error("--project-root is required unless --self-test is used")

    payload = write_result_index(args.project_root, output_md=args.output_md, output_json=args.output_json)
    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
