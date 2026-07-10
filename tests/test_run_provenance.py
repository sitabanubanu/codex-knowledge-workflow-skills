#!/usr/bin/env python
"""Regression tests for immutable runs and downstream provenance receipts."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kw_cli import bundle, ingest


REPO_ROOT = Path(__file__).resolve().parents[1]


def demo_text() -> str:
    return (REPO_ROOT / "examples" / "demo_transcript" / "input.txt").read_text(encoding="utf-8")


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def build_full_run(project: Path, transcript: Path) -> Path:
    manifest_path = bundle.build_local_bundle(input_path=transcript, project_root=project)
    result = ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
    if result.get("source_status") != "source_confirmed":
        raise RuntimeError(f"fixture ingest failed: {result}")
    audit = ingest.run_audit_pipeline(
        project_root=project,
        document_goal="provenance regression fixture",
        final_language="en",
        audience="test reader",
    )
    if audit.get("status") != "completed":
        raise RuntimeError(f"fixture audit failed: {audit}")
    ingest.compose_final_report(project_root=project)
    return manifest_path


def test_resume_archives_old_outputs(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-provenance-resume-") as tmp:
        root = Path(tmp)
        project = root / "project"
        transcript = root / "input.txt"
        transcript.write_text(demo_text(), encoding="utf-8")
        first_manifest = build_full_run(project, transcript)
        first_bundle_id = bundle.load_manifest(first_manifest)["bundle_id"]
        assert_true("full fixture report is current", ingest.current_provenance(project)["final_report_current"], failures)

        try:
            bundle.build_local_bundle(input_path=transcript, project_root=project)
        except bundle.BundleError:
            pass
        else:
            failures.append("project root reuse without --resume must fail")

        second_manifest = bundle.build_local_bundle(input_path=transcript, project_root=project, resume=True)
        second_bundle_id = bundle.load_manifest(second_manifest)["bundle_id"]
        assert_true("resume produces a new bundle id", first_bundle_id != second_bundle_id, failures)
        assert_true("old acquisition is archived", any((project / "acquisition_history").glob("*/manifest.json")), failures)
        assert_true("old final report becomes non-current immediately", not ingest.current_provenance(project)["final_report_current"], failures)

        ingest.ingest_bundle(manifest_path=second_manifest, project_root=project)
        assert_true("old downstream final report moved to run_history", any((project / "run_history").glob("*/20_document/final_report.md")), failures)
        assert_true("main final report removed after new ingest", not (project / "20_document" / "final_report.md").exists(), failures)


def test_content_change_cannot_resume_same_run(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-provenance-content-") as tmp:
        root = Path(tmp)
        project = root / "project"
        transcript = root / "input.txt"
        transcript.write_text("Original source material.\n", encoding="utf-8")
        bundle.build_local_bundle(input_path=transcript, project_root=project)
        transcript.write_text("Changed source material.\n", encoding="utf-8")
        try:
            bundle.build_local_bundle(input_path=transcript, project_root=project, resume=True)
        except bundle.BundleError:
            pass
        else:
            failures.append("changed local content must not resume under the old run identity")


def test_report_hash_tamper_invalidates_delivery(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-provenance-report-") as tmp:
        root = Path(tmp)
        project = root / "project"
        transcript = root / "input.txt"
        transcript.write_text(demo_text(), encoding="utf-8")
        build_full_run(project, transcript)
        report = project / "20_document" / "final_report.md"
        report.write_text(report.read_text(encoding="utf-8") + "\nUnreceipted edit.\n", encoding="utf-8")
        provenance = ingest.current_provenance(project)
        assert_true("tampered final report is not current", not provenance["final_report_current"], failures)
        assert_true("upstream composer remains current", provenance["composer_current"], failures)


def main() -> int:
    failures: list[str] = []
    test_resume_archives_old_outputs(failures)
    test_content_change_cannot_resume_same_run(failures)
    test_report_hash_tamper_invalidates_delivery(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_run_provenance passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
