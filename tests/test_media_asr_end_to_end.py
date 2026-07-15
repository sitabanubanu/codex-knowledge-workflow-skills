#!/usr/bin/env python
"""Offline MP3/MP4 ASR-to-final-report regression tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kw_cli import bundle, ingest, source_status_contract


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def run_case(media_name: str, failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix=f"kw-media-asr-e2e-{Path(media_name).suffix[1:]}-") as tmp:
        project = Path(tmp) / "project"
        manifest_path = bundle.build_local_bundle(
            input_path=FIXTURES / media_name,
            project_root=project,
        )
        ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
        pending = ingest.read_json(project / "10_video" / "00_source" / "source_status.json")
        assert_true(f"{media_name}: pending ASR scope", pending.get("scope_status") == "pending_derivation", failures)
        assert_true(f"{media_name}: pending ASR stopped", pending.get("pipeline_decision") == "stop_before_audit", failures)

        manifest = ingest.read_json(manifest_path)
        asr = ingest.run_asr_for_media_bundle(
            manifest_path=manifest_path,
            manifest=manifest,
            project_root=project,
            asr_model="base",
            language="en",
            asr_jsonl=FIXTURES / "asr_sample.jsonl",
        )
        status = ingest.read_json(project / "10_video" / "00_source" / "source_status.json")
        assert_true(f"{media_name}: ASR completed", asr.get("status") == "completed", failures)
        assert_true(f"{media_name}: canonical status valid", not source_status_contract.validate_source_status(status), failures)
        assert_true(f"{media_name}: status schema", status.get("schema_version") == 1, failures)
        assert_true(f"{media_name}: scope matched", status.get("scope_status") == "matched", failures)
        assert_true(f"{media_name}: full continuation", status.get("pipeline_decision") == "continue_full", failures)
        assert_true(f"{media_name}: failed probes retained", isinstance(status.get("failed_probes"), list), failures)

        provenance = ingest.current_provenance(project)
        assert_true(f"{media_name}: gate receipt current", provenance.get("gate_current") is True, failures)

        audit = ingest.run_audit_pipeline(
            project_root=project,
            document_goal="Produce a source-grounded learning report.",
            final_language="en",
            audience="general learner",
        )
        assert_true(f"{media_name}: audit completed", audit.get("status") == "completed", failures)

        final = ingest.compose_final_report(project_root=project)
        assert_true(f"{media_name}: final compose completed", final.get("status") == "completed", failures)
        assert_true(
            f"{media_name}: final report exists",
            (project / "20_document" / "final_report.md").is_file(),
            failures,
        )
        quality_gate = ingest.read_json(project / "20_document" / "quality_gate.json")
        assert_true(
            f"{media_name}: quality gate approved",
            quality_gate.get("approved_for_final_report") is True,
            failures,
        )
        final_provenance = ingest.current_provenance(project)
        assert_true(
            f"{media_name}: final provenance current",
            final_provenance.get("final_report_current") is True,
            failures,
        )
        transcript = project / "10_video" / "01_transcript" / "clean_transcript.jsonl"
        transcript.write_text(transcript.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        tampered = ingest.current_provenance(project)
        assert_true(f"{media_name}: transcript tamper closes gate", tampered.get("gate_current") is False, failures)
        assert_true(
            f"{media_name}: transcript tamper reason",
            any("derived artifact" in str(item) for item in tampered.get("reasons") or []),
            failures,
        )


def main() -> int:
    failures: list[str] = []
    run_case("fixture.mp3", failures)
    run_case("fixture.mp4", failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_media_asr_end_to_end passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
