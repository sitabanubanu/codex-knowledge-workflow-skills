#!/usr/bin/env python
"""Tests for acquisition bundle schema validation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from kw_cli import bundle


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_local_transcript_bundle(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-bundle-schema-") as tmp:
        root = Path(tmp)
        transcript = root / "input.txt"
        transcript.write_text("A usable transcript line.\n", encoding="utf-8")
        manifest_path = bundle.build_local_bundle(input_path=transcript, project_root=root / "project")
        result = bundle.validate_manifest(manifest_path)
        assert_true("valid local transcript bundle passes", result["valid"], failures)


def test_missing_artifact_fails(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-bundle-missing-") as tmp:
        root = Path(tmp)
        transcript = root / "input.txt"
        transcript.write_text("A usable transcript line.\n", encoding="utf-8")
        manifest_path = bundle.build_local_bundle(input_path=transcript, project_root=root / "project")
        payload = load(manifest_path)
        payload["artifacts"][0]["path"] = "artifacts/missing.txt"
        bundle.write_json(manifest_path, payload)
        result = bundle.validate_manifest(manifest_path)
        assert_true("missing artifact fails", not result["valid"], failures)


def test_invalid_status_fails(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-bundle-status-") as tmp:
        root = Path(tmp)
        transcript = root / "input.txt"
        transcript.write_text("A usable transcript line.\n", encoding="utf-8")
        manifest_path = bundle.build_local_bundle(input_path=transcript, project_root=root / "project")
        payload = load(manifest_path)
        payload["status"] = "source_confirmed"
        bundle.write_json(manifest_path, payload)
        result = bundle.validate_manifest(manifest_path)
        assert_true("invalid status fails", not result["valid"], failures)


def test_metadata_only_cannot_be_primary(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-bundle-metadata-") as tmp:
        root = Path(tmp) / "project"
        artifact = root / "00_acquisition" / "artifacts" / "metadata.json"
        bundle.write_json(artifact, {"title": "metadata"})
        entry = bundle.artifact_entry(
            bundle_root=root / "00_acquisition",
            path=artifact,
            artifact_type="metadata",
            source_class="primary",
        )
        manifest = bundle.make_manifest(
            project_root=root,
            input_value="https://example.com",
            source_url="https://example.com",
            platform="web",
            status="metadata_only",
            artifacts=[entry],
        )
        manifest_path = bundle.write_manifest(root, manifest)
        result = bundle.validate_manifest(manifest_path)
        assert_true("metadata_only cannot be primary", not result["valid"], failures)


def test_secret_fields_are_rejected(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-bundle-secret-") as tmp:
        root = Path(tmp)
        transcript = root / "input.txt"
        transcript.write_text("A usable transcript line.\n", encoding="utf-8")
        manifest_path = bundle.build_local_bundle(input_path=transcript, project_root=root / "project")
        payload = load(manifest_path)
        payload["metadata"]["token"] = "secret-value"
        bundle.write_json(manifest_path, payload)
        result = bundle.validate_manifest(manifest_path)
        assert_true("secrets fields are not present", not result["valid"], failures)


def main() -> int:
    failures: list[str] = []
    test_valid_local_transcript_bundle(failures)
    test_missing_artifact_fails(failures)
    test_invalid_status_fails(failures)
    test_metadata_only_cannot_be_primary(failures)
    test_secret_fields_are_rejected(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_acquisition_bundle_schema passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
