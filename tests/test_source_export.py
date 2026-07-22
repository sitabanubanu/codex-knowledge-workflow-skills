#!/usr/bin/env python
"""Tests for provider-neutral source exports entering Bundle v2."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kw_cli import acquisition_adapter, bundle, ingest


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def test_social_export(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-source-reddit-") as tmp:
        root = Path(tmp)
        export = root / "reddit-post.txt"
        export.write_text("Post title: Source boundaries.\n\nPost body: Preserve primary material.\n", encoding="utf-8")
        project = root / "project"
        manifest_path = bundle.build_source_export_bundle(
            input_path=export,
            source_url="https://www.reddit.com/r/example/comments/abc/source-gate/",
            platform="reddit",
            project_root=project,
            analysis_target="social_post",
            operation="read",
            browser_host="edge",
            credentialed_session=True,
        )
        manifest = ingest.read_json(manifest_path)
        result = ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
        assert_true("Reddit export validates", bundle.validate_manifest(manifest_path)["valid"], failures)
        assert_true("Reddit export confirms social source", result.get("source_status") == "source_confirmed", failures)
        assert_true("provider-neutral layer is recorded", manifest.get("acquisition_layer") == "external_source_export", failures)
        assert_true("declared Edge host is recorded", manifest.get("metadata", {}).get("browser_host") == "edge", failures)
        assert_true("credentialed session is recorded without secrets", manifest.get("privacy", {}).get("cookies_used") is True, failures)


def test_podcast_transcript_export(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-source-podcast-") as tmp:
        root = Path(tmp)
        export = root / "podcast.txt"
        export.write_text("The speaker explains why primary material must be preserved.\n", encoding="utf-8")
        project = root / "project"
        manifest_path = bundle.build_source_export_bundle(
            input_path=export,
            source_url="https://www.xiaoyuzhoufm.com/episode/example",
            platform="xiaoyuzhou",
            project_root=project,
            analysis_target="video_content",
            operation="extract_transcript",
        )
        manifest = ingest.read_json(manifest_path)
        result = ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
        assert_true("podcast transcript validates", bundle.validate_manifest(manifest_path)["valid"], failures)
        assert_true("podcast transcript confirms source", result.get("source_status") == "source_confirmed", failures)
        assert_true("podcast transcript has video transcript scope", manifest["artifacts"][0].get("content_scope") == "video_transcript", failures)


def test_complete_channel_catalog(failures: list[str]) -> None:
    payload = acquisition_adapter.capability_matrix_payload(
        {
            "web": {"status": "ok", "active_backend": "Jina Reader"},
            "reddit": {"status": "external_export", "message": "authorized export"},
        }
    )
    channels = payload.get("channels") or []
    names = {item.get("channel") for item in channels if isinstance(item, dict)}
    assert_true("all 15 acquisition channels are cataloged", len(channels) == 15, failures)
    assert_true("catalog includes long-tail channels", {"web", "reddit", "xiaoyuzhou", "xueqiu", "linkedin"}.issubset(names), failures)
    reddit = next((item for item in channels if item.get("channel") == "reddit"), {})
    assert_true("matrix preserves provider status", reddit.get("provider_status") == "external_export", failures)
    assert_true("matrix declares external export route", reddit.get("integration_mode") == "external_export", failures)
    assert_true("every channel has an auditable handoff", all(item.get("auditable_handoff") == "kw source import" for item in channels), failures)


def main() -> int:
    failures: list[str] = []
    test_social_export(failures)
    test_podcast_transcript_export(failures)
    test_complete_channel_catalog(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_source_export passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
