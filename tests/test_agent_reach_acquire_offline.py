#!/usr/bin/env python
"""Offline tests for Agent-Reach acquisition adapter."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from kw_cli import agent_reach_adapter, bundle


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def completed(cmd: list[str], code: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(cmd, code, stdout, stderr)


def test_agent_reach_missing_failed_bundle(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-missing-") as tmp:
        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value=None):
            manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                input_value="https://www.youtube.com/watch?v=abc",
                project_root=Path(tmp) / "project",
            )
        manifest = load_manifest(manifest_path)
        assert_true("agent-reach missing -> failed bundle", manifest.get("status") == "failed", failures)


def test_youtube_subtitle_material_acquired(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-youtube-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["agent-reach", "doctor", "--json"]:
                return completed(command, stdout=json.dumps({"youtube": {"active_backend": "yt-dlp"}}))
            if command[:3] == ["yt-dlp", "--skip-download", "--dump-single-json"]:
                return completed(command, stdout=json.dumps({"title": "Video"}))
            if command and command[0] == "yt-dlp":
                (project / "00_acquisition" / "artifacts").mkdir(parents=True, exist_ok=True)
                (project / "00_acquisition" / "artifacts" / "youtube.en.vtt").write_text(
                    "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello.\n",
                    encoding="utf-8",
                )
                return completed(command)
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.youtube.com/watch?v=abc",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        assert_true("doctor returns backend -> manifest active_backend set", manifest.get("active_backend") == "yt-dlp", failures)
        assert_true("YouTube subtitle artifact -> material_acquired", manifest.get("status") == "material_acquired", failures)


def test_bilibili_metadata_only(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-bili-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["agent-reach", "doctor", "--json"]:
                return completed(command, stdout=json.dumps({"bilibili": {"active_backend": "bili-cli"}}))
            if command[:2] == ["bili", "video"]:
                return completed(command, stdout='{"title":"bili"}')
            return completed(command)

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.bilibili.com/video/BV1xx411",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        assert_true("Bilibili metadata only -> metadata_only", manifest.get("status") == "metadata_only", failures)


def test_web_page_markdown_artifact(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-web-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["agent-reach", "doctor", "--json"]:
                return completed(command, stdout=json.dumps({"web": {"active_backend": "Jina Reader"}}))
            if command and command[0] == "curl":
                return completed(command, stdout="# Page\n\nBody")
            return completed(command)

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://example.com/page",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        artifact_types = {item.get("type") for item in manifest.get("artifacts", [])}
        assert_true("web page markdown -> page_markdown artifact", "page_markdown" in artifact_types, failures)
        assert_true("web page markdown validates", bundle.validate_manifest(manifest_path)["valid"], failures)


def test_x_jina_block_keeps_platform(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-x-block-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["agent-reach", "doctor", "--json"]:
                return completed(
                    command,
                    stdout=json.dumps(
                        {
                            "twitter": {"active_backend": None},
                            "web": {"active_backend": "Jina Reader"},
                        }
                    ),
                )
            if command and command[0] == "curl":
                failures.append("x without backend should not call Jina/curl")
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://x.com/example/status/123",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        assert_true("x platform preserved", manifest.get("platform") == "x", failures)
        assert_true("x no active backend -> blocked", manifest.get("status") == "blocked", failures)
        assert_true("x blocked does not write page artifact", not manifest.get("artifacts"), failures)
        assert_true(
            "x route plan disables anonymous fallback",
            manifest.get("metadata", {}).get("route_plan", {}).get("anonymous_web_fallback_allowed") is False,
            failures,
        )


def test_xiaohongshu_fallback_keeps_platform(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-xhs-fallback-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["agent-reach", "doctor", "--json"]:
                return completed(
                    command,
                    stdout=json.dumps(
                        {
                            "xiaohongshu": {"active_backend": None},
                            "web": {"active_backend": "Jina Reader"},
                        }
                    ),
                )
            if command and command[0] == "curl":
                failures.append("xiaohongshu without backend should not call Jina/curl")
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.xiaohongshu.com/explore/fixture",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        assert_true("xiaohongshu platform preserved", manifest.get("platform") == "xiaohongshu", failures)
        assert_true("xiaohongshu no active backend -> blocked", manifest.get("status") == "blocked", failures)
        assert_true(
            "xiaohongshu route plan suggests opencli",
            "opencli" in " ".join(manifest.get("metadata", {}).get("route_plan", {}).get("install_commands", [])),
            failures,
        )


def test_x_twitter_cli_primary_artifact(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-x-twitter-cli-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["agent-reach", "doctor", "--json"]:
                return completed(command, stdout=json.dumps({"twitter": {"status": "ok", "active_backend": "twitter-cli"}}))
            if command[:2] == ["twitter", "tweet"]:
                return completed(command, stdout="tweet: primary text from status\n")
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://x.com/example/status/123",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        assert_true("x twitter-cli -> material_acquired", manifest.get("status") == "material_acquired", failures)
        assert_true("x active backend twitter-cli", manifest.get("active_backend") == "twitter-cli", failures)
        assert_true(
            "x tweet text primary artifact",
            any(item.get("type") == "page_text" and item.get("source_class") == "primary" for item in manifest.get("artifacts", [])),
            failures,
        )
        assert_true("x twitter-cli records cookies_used", manifest.get("privacy", {}).get("cookies_used") is True, failures)


def test_xiaohongshu_opencli_primary_artifact(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-xhs-opencli-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["agent-reach", "doctor", "--json"]:
                return completed(command, stdout=json.dumps({"xiaohongshu": {"status": "ok", "active_backend": "OpenCLI"}}))
            if command[:3] == ["opencli", "xiaohongshu", "note"]:
                return completed(command, stdout="title: note\ncontent: primary text\n")
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.xiaohongshu.com/explore/fixture?xsec_token=abc",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        assert_true("xiaohongshu OpenCLI -> material_acquired", manifest.get("status") == "material_acquired", failures)
        assert_true("xiaohongshu active backend OpenCLI", manifest.get("active_backend") == "OpenCLI", failures)
        assert_true(
            "xiaohongshu note primary artifact",
            any(item.get("type") == "page_text" and item.get("source_class") == "primary" for item in manifest.get("artifacts", [])),
            failures,
        )
        assert_true("xiaohongshu OpenCLI records browser_session_used", manifest.get("privacy", {}).get("browser_session_used") is True, failures)


def test_xiaohongshu_opencli_warn_blocks_until_ready(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-xhs-opencli-warn-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["agent-reach", "doctor", "--json"]:
                return completed(
                    command,
                    stdout=json.dumps(
                        {
                            "xiaohongshu": {
                                "status": "warn",
                                "active_backend": "OpenCLI",
                                "message": "OpenCLI installed but Chrome extension is missing.",
                            }
                        }
                    ),
                )
            if command[:3] == ["opencli", "xiaohongshu", "note"]:
                failures.append("warn OpenCLI backend should not execute")
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.xiaohongshu.com/explore/fixture?xsec_token=abc",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        plan = manifest.get("metadata", {}).get("route_plan", {})
        assert_true("xiaohongshu warn OpenCLI -> blocked", manifest.get("status") == "blocked", failures)
        assert_true("xiaohongshu warn backend not ready", plan.get("active_backend_ready") is False, failures)
        assert_true("xiaohongshu warn keeps active backend name", manifest.get("active_backend") == "OpenCLI", failures)


def test_github_readme_from_clone(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-github-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["agent-reach", "doctor", "--json"]:
                return completed(command, stdout=json.dumps({"github": {"active_backend": "gh"}}))
            if command[:4] == ["gh", "repo", "view", "cli/cli"]:
                assert "--json" in command
                assert "readme" not in command[-1]
                return completed(command, stdout=json.dumps({"name": "cli", "description": "GitHub CLI"}))
            if command[:4] == ["gh", "repo", "clone", "cli/cli"]:
                clone_target = Path(command[4])
                clone_target.mkdir(parents=True, exist_ok=True)
                (clone_target / "README.md").write_text("# GitHub CLI\n\nPrimary repository README.\n", encoding="utf-8")
                return completed(command)
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://github.com/cli/cli",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        assert_true("GitHub README clone -> material_acquired", manifest.get("status") == "material_acquired", failures)
        assert_true(
            "GitHub README is primary page_markdown",
            any(item.get("type") == "page_markdown" and item.get("source_class") == "primary" for item in manifest.get("artifacts", [])),
            failures,
        )


def test_query_search_secondary_bundle(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-query-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["agent-reach", "doctor", "--json"]:
                return completed(command, stdout=json.dumps({"exa_search": {"active_backend": "mcporter/exa"}}))
            if command[:2] == ["mcporter", "call"]:
                return completed(command, stdout="- Search result one\n- Search result two\n")
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="marx alienation",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        assert_true("query search -> secondary_only", manifest.get("status") == "secondary_only", failures)
        assert_true("query active backend from exa_search", manifest.get("active_backend") == "mcporter/exa", failures)
        assert_true(
            "query artifact is secondary search_result",
            any(item.get("type") == "search_result" and item.get("source_class") == "secondary" for item in manifest.get("artifacts", [])),
            failures,
        )


def main() -> int:
    failures: list[str] = []
    test_agent_reach_missing_failed_bundle(failures)
    test_youtube_subtitle_material_acquired(failures)
    test_bilibili_metadata_only(failures)
    test_web_page_markdown_artifact(failures)
    test_x_jina_block_keeps_platform(failures)
    test_xiaohongshu_fallback_keeps_platform(failures)
    test_x_twitter_cli_primary_artifact(failures)
    test_xiaohongshu_opencli_primary_artifact(failures)
    test_xiaohongshu_opencli_warn_blocks_until_ready(failures)
    test_github_readme_from_clone(failures)
    test_query_search_secondary_bundle(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_agent_reach_acquire_offline passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
