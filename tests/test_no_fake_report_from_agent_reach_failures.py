#!/usr/bin/env python
"""Ensure failed acquisition bundles cannot create normal final reports."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from kw_cli import bundle, ingest


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_INDEX_WRITER = REPO_ROOT / "skills" / "knowledge-workflow-console" / "scripts" / "result_index_writer.py"


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def make_blocked_manifest(project: Path, status: str) -> Path:
    artifacts = []
    if status == "metadata_only":
        metadata = project / "00_acquisition" / "artifacts" / "metadata.json"
        bundle.write_json(metadata, {"title": "Only metadata"})
        artifacts.append(
            bundle.artifact_entry(
                bundle_root=project / "00_acquisition",
                path=metadata,
                artifact_type="metadata",
                source_class="metadata_only",
            )
        )
    manifest = bundle.make_manifest(
        project_root=project,
        input_value="https://example.com/video",
        source_url="https://example.com/video",
        platform="web",
        status=status,
        artifacts=artifacts,
        failures=[{"stage": "acquisition", "reason": status}],
        next_action="Provide primary transcript or subtitle.",
    )
    return bundle.write_manifest(project, manifest)


def run_case(status: str, failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix=f"kw-no-fake-{status}-") as tmp:
        project = Path(tmp) / "project"
        manifest_path = make_blocked_manifest(project, status)
        ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
        completed = subprocess.run(
            [sys.executable, str(RESULT_INDEX_WRITER), "--project-root", str(project)],
            cwd=str(REPO_ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        assert_true(f"{status} result index writer passes", completed.returncode == 0, failures)
        assert_true(f"{status} no final report", not (project / "20_document" / "final_report.md").exists(), failures)
        index_text = (project / "result_index.md").read_text(encoding="utf-8")
        assert_true(f"{status} result_index writes next_action", "Provide primary transcript or subtitle" in index_text, failures)


def main() -> int:
    failures: list[str] = []
    run_case("blocked", failures)
    run_case("metadata_only", failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_no_fake_report_from_agent_reach_failures passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
