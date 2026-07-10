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


def test_path_traversal_is_rejected(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-bundle-traversal-") as tmp:
        root = Path(tmp)
        transcript = root / "input.txt"
        transcript.write_text("A usable transcript line.\n", encoding="utf-8")
        manifest_path = bundle.build_local_bundle(input_path=transcript, project_root=root / "project")
        payload = load(manifest_path)
        payload["artifacts"][0]["path"] = "../outside.txt"
        bundle.write_json(manifest_path, payload)
        result = bundle.validate_manifest(manifest_path)
        assert_true("path traversal fails", not result["valid"], failures)


def test_artifact_hash_tamper_is_rejected(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-bundle-hash-") as tmp:
        root = Path(tmp)
        transcript = root / "input.txt"
        transcript.write_text("A usable transcript line.\n", encoding="utf-8")
        manifest_path = bundle.build_local_bundle(input_path=transcript, project_root=root / "project")
        payload = load(manifest_path)
        artifact_path = manifest_path.parent / payload["artifacts"][0]["path"]
        artifact_path.write_text("Tampered after manifest creation.\n", encoding="utf-8")
        result = bundle.validate_manifest(manifest_path)
        assert_true("artifact hash tamper fails", not result["valid"], failures)


def test_browser_export_preserves_url_scope_and_privacy(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-browser-export-") as tmp:
        root = Path(tmp)
        export = root / "post.txt"
        export.write_text("A browser-visible post body.\n", encoding="utf-8")
        manifest_path = bundle.build_browser_export_bundle(
            input_path=export,
            source_url="https://x.com/example/status/1?token=secret",
            platform="x",
            project_root=root / "project",
            analysis_target="social_post",
            operation="read",
        )
        payload = load(manifest_path)
        result = bundle.validate_manifest(manifest_path)
        assert_true("browser export bundle passes", result["valid"], failures)
        assert_true("browser export is page text", payload["artifacts"][0]["type"] == "page_text", failures)
        assert_true("browser export social scope", payload["artifacts"][0]["content_scope"] == "social_post_text", failures)
        assert_true("browser session recorded", payload["privacy"]["browser_session_used"] is True, failures)
        persisted = manifest_path.read_text(encoding="utf-8")
        assert_true("browser URL token redacted", "token=secret" not in persisted and "%5BREDACTED%5D" in persisted, failures)
        resumed = bundle.build_browser_export_bundle(
            input_path=export,
            source_url="https://x.com/example/status/1?token=rotated",
            platform="x",
            project_root=root / "project",
            analysis_target="social_post",
            operation="read",
            resume=True,
        )
        assert_true("browser token rotation can resume", bundle.validate_manifest(resumed)["valid"], failures)


def test_browser_export_rejects_wrong_scope(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-browser-scope-") as tmp:
        root = Path(tmp)
        export = root / "post.txt"
        export.write_text("A browser-visible post body.\n", encoding="utf-8")
        try:
            bundle.build_browser_export_bundle(
                input_path=export,
                source_url="https://x.com/example/status/1",
                platform="x",
                project_root=root / "project",
                analysis_target="social_post",
                content_scope="article_body",
            )
        except bundle.BundleError:
            return
        failures.append("browser export wrong scope rejected")


def main() -> int:
    failures: list[str] = []
    test_valid_local_transcript_bundle(failures)
    test_missing_artifact_fails(failures)
    test_invalid_status_fails(failures)
    test_metadata_only_cannot_be_primary(failures)
    test_secret_fields_are_rejected(failures)
    test_path_traversal_is_rejected(failures)
    test_artifact_hash_tamper_is_rejected(failures)
    test_browser_export_preserves_url_scope_and_privacy(failures)
    test_browser_export_rejects_wrong_scope(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_acquisition_bundle_schema passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
