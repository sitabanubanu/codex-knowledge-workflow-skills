#!/usr/bin/env python
"""Summarize a knowledge workflow run into one user-facing status object."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


RUNNER_NAME = "knowledge-workflow-status-summary"


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def exists(path: Path) -> bool:
    return path.is_file()


def build_summary(project_root: Path) -> dict[str, Any]:
    project_root = project_root.expanduser().resolve()
    video_root = project_root / "10_video"
    document_root = project_root / "20_document"
    logs_root = project_root / "logs"
    acquisition_root = project_root / "00_acquisition"

    run_state = read_json(logs_root / "run_state.json") or {}
    acquisition_manifest = read_json(acquisition_root / "manifest.json") or {}
    source_status = read_json(video_root / "00_source" / "source_status.json") or {}
    quality_gate = read_json(document_root / "quality_gate.json") or {}
    platform_result = read_json(video_root / "00_source" / "platform_media_result.json") or {}

    source_state = source_status.get("source_status") or run_state.get("source_status") or "unknown"
    final_report_exists = exists(document_root / "final_report.md")
    pack_exists = exists(video_root / "video_analysis_pack.md")
    transcript_exists = exists(video_root / "01_transcript" / "clean_transcript.jsonl")

    if final_report_exists:
        current_stage = "final_report_ready"
    elif quality_gate:
        current_stage = "final_quality_gate"
    elif pack_exists:
        current_stage = "video_analysis_pack_ready"
    elif transcript_exists:
        current_stage = "transcript_ready"
    elif source_state in {"secondary_only", "source_blocked", "source_failed", "degraded_report_only"}:
        current_stage = "acquisition_degraded_or_blocked"
    else:
        current_stage = run_state.get("current_stage") or "unknown"

    full_allowed = bool(source_status.get("can_enter_full_decomposition")) and source_state == "source_confirmed"
    approved = bool(quality_gate.get("approved_for_final_report"))
    user_action = (
        run_state.get("user_action_required")
        or source_status.get("next_step")
        or platform_result.get("material_decision", {}).get("next_step")
        or ""
    )

    if final_report_exists:
        next_step = "Read 20_document/final_report.md or export it to the desired format."
    elif pack_exists:
        next_step = "Run document_composer_runner, then final_report_writer."
    elif transcript_exists:
        next_step = "Continue segmentation, inventory, source logic, evidence audit, and pack builder."
    elif user_action:
        next_step = str(user_action)
    else:
        next_step = "Run preflight or acquisition to determine the next safe route."

    return {
        "runner": RUNNER_NAME,
        "project_root": str(project_root),
        "current_stage": current_stage,
        "acquisition_status": acquisition_manifest.get("status") or run_state.get("acquisition_status") or "unknown",
        "source_status": source_state,
        "primary_material_available": bool(source_status.get("primary_material_available")),
        "full_analysis_allowed": full_allowed,
        "video_analysis_pack_exists": pack_exists,
        "final_report_exists": final_report_exists,
        "quality_gate_approved": approved,
        "failure_reason": run_state.get("failure_reason") or source_status.get("status_reason") or "",
        "user_action_required": user_action,
        "next_step": next_step,
        "key_outputs": {
            "acquisition_manifest": str(acquisition_root / "manifest.json"),
            "source_status": str(video_root / "00_source" / "source_status.json"),
            "transcript": str(video_root / "01_transcript" / "clean_transcript.jsonl"),
            "video_analysis_pack": str(video_root / "video_analysis_pack.md"),
            "quality_gate": str(document_root / "quality_gate.json"),
            "final_report": str(document_root / "final_report.md"),
        },
    }


def emit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Workflow Status",
        "",
        f"- Current stage: `{payload['current_stage']}`",
        f"- Acquisition status: `{payload['acquisition_status']}`",
        f"- Source status: `{payload['source_status']}`",
        f"- Primary material available: `{payload['primary_material_available']}`",
        f"- Full analysis allowed: `{payload['full_analysis_allowed']}`",
        f"- Video analysis pack exists: `{payload['video_analysis_pack_exists']}`",
        f"- Final report exists: `{payload['final_report_exists']}`",
        f"- Quality gate approved: `{payload['quality_gate_approved']}`",
        f"- User action required: {payload['user_action_required'] or 'None recorded'}",
        f"- Next step: {payload['next_step']}",
        "",
        "## Key Outputs",
        "",
    ]
    lines.extend(f"- {name}: `{path}`" for name, path in payload["key_outputs"].items())
    if payload.get("failure_reason"):
        lines.extend(["", "## Failure Or Gate Reason", "", str(payload["failure_reason"])])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a knowledge workflow project status.")
    parser.add_argument("--project-root", type=Path, required=False)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        import tempfile

        with tempfile.TemporaryDirectory(prefix="kw-status-summary-") as tmp:
            root = Path(tmp)
            status_dir = root / "10_video" / "00_source"
            status_dir.mkdir(parents=True)
            status_dir.joinpath("source_status.json").write_text(
                json.dumps(
                    {
                        "source_status": "secondary_only",
                        "primary_material_available": False,
                        "can_enter_full_decomposition": False,
                        "status_reason": "metadata only",
                        "next_step": "request_primary_material",
                    }
                ),
                encoding="utf-8",
            )
            payload = build_summary(root)
            assert payload["current_stage"] == "acquisition_degraded_or_blocked", payload
            assert payload["full_analysis_allowed"] is False, payload
        print("workflow_status_summary self-test passed")
        return 0

    if not args.project_root:
        parser.error("--project-root is required unless --self-test is used")
    payload = build_summary(args.project_root)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_md:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(emit_markdown(payload), encoding="utf-8")
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2 if args.pretty else None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
