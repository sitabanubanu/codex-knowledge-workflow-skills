#!/usr/bin/env python
"""Tests for full Agent-Reach native export handoff into Bundle v2."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kw_cli import agent_reach_adapter, bundle, ingest


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def test_social_native_export(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-agent-reach-reddit-") as tmp:
        root = Path(tmp)
        export = root / "reddit-post.txt"
        export.write_text(
            "Post title: Evidence requires a source boundary.\n\n"
            "Post body: A source gate should keep unsupported summaries from becoming reports.\n",
            encoding="utf-8",
        )
        project = root / "project"
        manifest_path = bundle.build_agent_reach_export_bundle(
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
        assert_true("native Reddit export validates", bundle.validate_manifest(manifest_path)["valid"], failures)
        assert_true("native Reddit export confirms social source", result.get("source_status") == "source_confirmed", failures)
        assert_true("native Reddit export keeps Agent-Reach layer", manifest.get("acquisition_layer") == "agent_reach_export", failures)
        assert_true("native Reddit export records Edge", manifest.get("metadata", {}).get("browser_host") == "edge", failures)
        assert_true("native Reddit export records credentialed session", manifest.get("privacy", {}).get("cookies_used") is True, failures)


def test_podcast_native_transcript_export(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-agent-reach-podcast-") as tmp:
        root = Path(tmp)
        export = root / "podcast.txt"
        export.write_text(
            "The speaker explains that primary material must be preserved before analysis.\n",
            encoding="utf-8",
        )
        project = root / "project"
        manifest_path = bundle.build_agent_reach_export_bundle(
            input_path=export,
            source_url="https://www.xiaoyuzhoufm.com/episode/example",
            platform="xiaoyuzhou",
            project_root=project,
            analysis_target="video_content",
            operation="extract_transcript",
        )
        result = ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
        manifest = ingest.read_json(manifest_path)
        assert_true("podcast transcript validates", bundle.validate_manifest(manifest_path)["valid"], failures)
        assert_true("podcast transcript confirms video source", result.get("source_status") == "source_confirmed", failures)
        assert_true("podcast transcript has transcript scope", manifest["artifacts"][0].get("content_scope") == "video_transcript", failures)


def test_complete_channel_catalog(failures: list[str]) -> None:
    payload = agent_reach_adapter.capability_matrix_payload(
        {
            "web": {"status": "ok", "active_backend": "Jina Reader"},
            "reddit": {"status": "warn", "message": "requires login"},
        }
    )
    channels = payload.get("channels") or []
    names = {item.get("channel") for item in channels if isinstance(item, dict)}
    assert_true("all 15 Agent-Reach channels are cataloged", len(channels) == 15, failures)
    assert_true("catalog includes every required channel", {"web", "reddit", "xiaoyuzhou", "xueqiu", "linkedin"}.issubset(names), failures)
    reddit = next((item for item in channels if item.get("channel") == "reddit"), {})
    assert_true("matrix preserves doctor status", reddit.get("doctor_status") == "warn", failures)
    assert_true("matrix declares native import route", reddit.get("integration_mode") == "native_export_import", failures)


def test_upstream_cookie_import_requires_opt_in(failures: list[str]) -> None:
    assert_true("twitter install can auto-import cookies", agent_reach_adapter.channels_may_auto_import_cookies("twitter"), failures)
    assert_true("all-channel install can auto-import cookies", agent_reach_adapter.channels_may_auto_import_cookies("all"), failures)
    assert_true("OpenCLI install does not auto-import cookies", not agent_reach_adapter.channels_may_auto_import_cookies("opencli,reddit"), failures)


def main() -> int:
    failures: list[str] = []
    test_social_native_export(failures)
    test_podcast_native_transcript_export(failures)
    test_complete_channel_catalog(failures)
    test_upstream_cookie_import_requires_opt_in(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_agent_reach_native_export passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
