#!/usr/bin/env python
"""Tests for source_status generation from acquisition bundles."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kw_cli import bundle, ingest


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def make_manifest(project: Path, *, status: str, artifact_type: str | None = None, source_class: str | None = None) -> Path:
    artifacts = []
    if artifact_type:
        artifact_path = project / "00_acquisition" / "artifacts" / f"artifact.{ 'txt' if artifact_type == 'transcript' else 'json' }"
        if artifact_type == "transcript":
            bundle.write_text(artifact_path, "Primary transcript text.\n")
        else:
            bundle.write_json(artifact_path, {"title": "Metadata"})
        artifacts.append(
            bundle.artifact_entry(
                bundle_root=project / "00_acquisition",
                path=artifact_path,
                artifact_type=artifact_type,
                source_class=source_class or "unknown",
            )
        )
    manifest = bundle.make_manifest(
        project_root=project,
        input_value="https://example.com",
        source_url="https://example.com",
        platform="web",
        status=status,
        artifacts=artifacts,
        next_action="next",
    )
    return bundle.write_manifest(project, manifest)


def ingest_status(manifest_path: Path, project: Path) -> dict:
    ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
    return ingest.read_json(project / "10_video" / "00_source" / "source_status.json")


def test_primary_artifact_allows_decomposition(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-source-primary-") as tmp:
        project = Path(tmp) / "project"
        status = ingest_status(make_manifest(project, status="material_acquired", artifact_type="transcript", source_class="primary"), project)
        assert_true("primary artifact -> source_confirmed", status.get("source_status") == "source_confirmed", failures)
        assert_true("primary artifact -> can_enter_full_decomposition true", status.get("can_enter_full_decomposition") is True, failures)


def test_blocked_states_do_not_allow_full(failures: list[str]) -> None:
    cases = [
        ("metadata_only", "metadata", "metadata_only"),
        ("blocked", None, None),
        ("failed", None, None),
        ("secondary_only", "metadata", "metadata_only"),
    ]
    for status_value, artifact_type, source_class in cases:
        with tempfile.TemporaryDirectory(prefix=f"kw-source-{status_value}-") as tmp:
            project = Path(tmp) / "project"
            status = ingest_status(
                make_manifest(project, status=status_value, artifact_type=artifact_type, source_class=source_class),
                project,
            )
            assert_true(f"{status_value} -> false", status.get("can_enter_full_decomposition") is False, failures)
            assert_true(f"{status_value} no primary", status.get("primary_material_available") is False, failures)


def main() -> int:
    failures: list[str] = []
    test_primary_artifact_allows_decomposition(failures)
    test_blocked_states_do_not_allow_full(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_source_gate_from_bundle passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
