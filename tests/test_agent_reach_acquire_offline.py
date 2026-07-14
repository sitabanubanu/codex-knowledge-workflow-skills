#!/usr/bin/env python
"""Offline tests for Agent-Reach acquisition adapter."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from kw_cli import agent_reach_adapter, bundle, ingest, main as kw_main


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def completed(cmd: list[str], code: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(cmd, code, stdout, stderr)


def is_agent_reach_doctor(command: list[str]) -> bool:
    return len(command) >= 3 and Path(command[0]).stem.lower() == "agent-reach" and command[1:3] == ["doctor", "--json"]


def test_agent_reach_missing_failed_bundle(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-missing-") as tmp:
        with patch.dict(os.environ, {"KW_GITHUB_TOOLS_ROOT": str(Path(tmp) / "isolated")}, clear=False):
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
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"youtube": {"status": "ok", "active_backend": "yt-dlp"}}))
            if "--dump-single-json" in command:
                return completed(command, stdout=json.dumps({"title": "Video"}))
            if command and command[0] == "yt-dlp":
                output_template = Path(command[command.index("-o") + 1])
                subtitle_path = Path(str(output_template).replace("%(ext)s", "en.vtt"))
                subtitle_path.parent.mkdir(parents=True, exist_ok=True)
                subtitle_path.write_text(
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
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"bilibili": {"status": "ok", "active_backend": "bili-cli"}}))
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
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"web": {"status": "ok", "active_backend": "Jina Reader"}}))
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
            if is_agent_reach_doctor(command):
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
            if is_agent_reach_doctor(command):
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
            if is_agent_reach_doctor(command):
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


def test_x_opencli_status_primary_artifact(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-x-opencli-") as tmp:
        project = Path(tmp) / "project"
        executed: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs):
            executed.append(command)
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"twitter": {"status": "ok", "active_backend": "OpenCLI"}}))
            if command[:3] == ["opencli", "twitter", "article"]:
                return completed(command, stdout=json.dumps({"author": "fixture", "content": "primary status text"}))
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://x.com/example/status/123",
                    project_root=project,
                    youtube_options={"browser_host": "edge"},
                )
        manifest = load_manifest(manifest_path)
        assert_true("x OpenCLI -> material_acquired", manifest.get("status") == "material_acquired", failures)
        assert_true("x OpenCLI records Edge host", manifest.get("metadata", {}).get("browser_host") == "edge", failures)
        assert_true("x OpenCLI records browser session", manifest.get("privacy", {}).get("browser_session_used") is True, failures)
        assert_true(
            "x OpenCLI executes the documented article route",
            any(command[:3] == ["opencli", "twitter", "article"] for command in executed),
            failures,
        )
        assert_true(
            "x OpenCLI creates primary post artifact",
            any(item.get("type") == "page_text" and item.get("content_scope") == "social_post_text" for item in manifest.get("artifacts", [])),
            failures,
        )


def test_xiaohongshu_opencli_primary_artifact(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-xhs-opencli-") as tmp:
        project = Path(tmp) / "project"
        executed: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs):
            executed.append(command)
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"xiaohongshu": {"status": "ok", "active_backend": "OpenCLI"}}))
            if command[:3] == ["opencli", "xiaohongshu", "note"]:
                return completed(
                    command,
                    stdout=json.dumps(
                        [
                            {"field": "title", "value": "note"},
                            {"field": "content", "value": "primary text"},
                        ]
                    ),
                )
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.xiaohongshu.com/explore/fixture?xsec_token=TOPSECRET_XHS_VALUE",
                    project_root=project,
                    youtube_options={"browser_host": "edge"},
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
        assert_true("xiaohongshu OpenCLI records Edge host", manifest.get("metadata", {}).get("browser_host") == "edge", failures)
        assert_true(
            "xiaohongshu OpenCLI uses persistent foreground session",
            any("--site-session" in command and "persistent" in command and "--window" in command and "foreground" in command for command in executed),
            failures,
        )
        ingest_result = ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
        source_status = ingest.read_json(project / "10_video" / "00_source" / "source_status.json")
        assert_true("xiaohongshu bundle ingests end to end", ingest_result.get("source_status") == "source_confirmed", failures)
        assert_true("xiaohongshu source target is social_post", source_status.get("analysis_target") == "social_post", failures)
        assert_true("xiaohongshu clean transcript exists", (project / "10_video" / "01_transcript" / "clean_transcript.jsonl").is_file(), failures)
        secret_url = "https://www.xiaohongshu.com/explore/fixture?xsec_token=TOPSECRET_XHS_VALUE"
        kw_main.run_preflight(secret_url, "standard", project, False)
        kw_main.write_run_state(
            project_root=project,
            mode="standard",
            input_kind="url",
            input_value=secret_url,
            status="completed",
            workflow_outcome="transcript_ready",
        )
        persisted_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in project.rglob("*")
            if path.is_file()
        )
        assert_true("xiaohongshu token is absent from persisted tree", "TOPSECRET_XHS_VALUE" not in persisted_text, failures)


def test_xiaohongshu_opencli_warn_blocks_until_ready(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-xhs-opencli-warn-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if is_agent_reach_doctor(command):
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
                    youtube_options={"browser_host": "edge"},
                )
        manifest = load_manifest(manifest_path)
        plan = manifest.get("metadata", {}).get("route_plan", {})
        assert_true("xiaohongshu warn OpenCLI -> blocked", manifest.get("status") == "blocked", failures)
        assert_true("xiaohongshu warn backend not ready", plan.get("active_backend_ready") is False, failures)
        assert_true("xiaohongshu warn keeps active backend name", manifest.get("active_backend") == "OpenCLI", failures)


def test_opencli_requires_declared_browser_host(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-opencli-host-") as tmp:
        project = Path(tmp) / "project"
        executed: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs):
            executed.append(command)
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"xiaohongshu": {"status": "ok", "active_backend": "OpenCLI"}}))
            return completed(command, code=1, stderr="OpenCLI must not execute without a declared host")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.xiaohongshu.com/explore/fixture?xsec_token=abc",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        plan = manifest.get("metadata", {}).get("route_plan", {})
        assert_true("OpenCLI without host is blocked", manifest.get("status") == "blocked", failures)
        assert_true("OpenCLI host is required", plan.get("browser_host_required") is True, failures)
        assert_true("OpenCLI host is unresolved", plan.get("browser_host") == "unknown", failures)
        assert_true("OpenCLI host mismatch stops command", not any(command[:3] == ["opencli", "xiaohongshu", "note"] for command in executed), failures)


def test_github_readme_from_clone(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-github-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"github": {"status": "ok", "active_backend": "gh CLI"}}))
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
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"exa_search": {"status": "ok", "active_backend": "Exa via mcporter"}}))
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
        assert_true("query active backend from exa_search", manifest.get("active_backend") == "Exa via mcporter", failures)
        assert_true(
            "query artifact is secondary search_result",
            any(item.get("type") == "search_result" and item.get("source_class") == "secondary" for item in manifest.get("artifacts", [])),
            failures,
        )


def test_bilibili_search_backend_cannot_claim_transcript(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-bili-capability-") as tmp:
        project = Path(tmp) / "project"
        executed: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs):
            executed.append(command)
            if is_agent_reach_doctor(command):
                return completed(
                    command,
                    stdout=json.dumps(
                        {"bilibili": {"status": "ok", "active_backend": "B站搜索 API", "message": "search only"}}
                    ),
                )
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.bilibili.com/video/BV1xx411",
                    project_root=project,
                )
        manifest = load_manifest(manifest_path)
        assert_true("Bilibili search-only backend -> blocked", manifest.get("status") == "blocked", failures)
        assert_true(
            "Bilibili capability mismatch does not call content commands",
            not any(command and command[0] in {"bili", "opencli"} for command in executed),
            failures,
        )
        assert_true(
            "Bilibili route plan records operation mismatch",
            manifest.get("metadata", {}).get("route_plan", {}).get("operation_supported") is False,
            failures,
        )


def test_youtube_options_are_applied_and_redacted(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-youtube-options-") as tmp:
        root = Path(tmp)
        project = root / "project"
        ytdlp = root / "yt-dlp.exe"
        node = root / "node.exe"
        cookies = root / "TOPSECRET_COOKIE_FILE.txt"
        for path in (ytdlp, node, cookies):
            path.write_text("fixture", encoding="utf-8")
        executed: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs):
            executed.append(command)
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"youtube": {"status": "ok", "active_backend": "yt-dlp"}}))
            if "--dump-single-json" in command:
                return completed(command, stdout=json.dumps({"id": "abc", "title": "Video"}))
            if "--write-subs" in command:
                return completed(command, code=1, stderr="no subtitles")
            return completed(command, code=1, stderr="unexpected")

        options = {
            "platform_mode": "subtitles",
            "youtube_cookies": str(cookies),
            "ytdlp": ytdlp,
            "node": node,
            "platform_timeout_seconds": 45,
            "subtitle_languages": "en,zh-Hans",
            "use_js_runtime": True,
            "use_remote_components": True,
            "ytdlp_extractor_args": ["youtube:fetch_pot=auto"],
            "ytdlp_player_clients": "web,mweb",
            "youtube_visitor_data": "VISITOR_SECRET_VALUE",
            "youtube_po_token": ["web.gvs+PO_SECRET_VALUE"],
            "ytdlp_proxy": "http://user:PROXY_SECRET_VALUE@proxy.example:8080",
            "ytdlp_impersonate": "chrome",
            "ytdlp_sleep_requests": 1.5,
            "ytdlp_retry_sleep": ["http:linear=1::2"],
        }
        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.youtube.com/watch?v=abc",
                    project_root=project,
                    youtube_options=options,
                )
        manifest = load_manifest(manifest_path)
        ytdlp_commands = [command for command in executed if command and command[0] == str(ytdlp.resolve())]
        combined_command = "\n".join(" ".join(command) for command in ytdlp_commands)
        for expected in (
            "--cookies",
            "--js-runtimes",
            "--remote-components",
            "--proxy",
            "--impersonate",
            "--sleep-requests",
            "--retry-sleep",
            "VISITOR_SECRET_VALUE",
            "PO_SECRET_VALUE",
            "en,zh-Hans",
        ):
            assert_true(f"YouTube option applied: {expected}", expected in combined_command, failures)
        assert_true("YouTube options bundle remains valid", bundle.validate_manifest(manifest_path)["valid"], failures)
        assert_true("YouTube subtitle-only failure is metadata_only", manifest.get("status") == "metadata_only", failures)
        persisted_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in project.rglob("*")
            if path.is_file()
        )
        for secret in ("TOPSECRET_COOKIE_FILE", "VISITOR_SECRET_VALUE", "PO_SECRET_VALUE", "PROXY_SECRET_VALUE"):
            assert_true(f"YouTube secret not persisted: {secret}", secret not in persisted_text, failures)


def test_youtube_opencli_transcript_is_primary(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-youtube-opencli-") as tmp:
        project = Path(tmp) / "project"
        executed: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs):
            executed.append(command)
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"youtube": {"status": "ok", "active_backend": "yt-dlp"}}))
            if command[:3] == ["opencli", "youtube", "transcript"]:
                return completed(command, stdout=json.dumps([{"timestamp": "0:00", "text": "primary transcript"}, {"timestamp": "0:05", "text": "second segment"}]))
            return completed(command, code=1, stderr="yt-dlp should not run after a primary OpenCLI transcript")

        def fake_which(name: str) -> str | None:
            return name if name in {"agent-reach", "opencli"} else None

        with patch("kw_cli.agent_reach_adapter.shutil.which", side_effect=fake_which):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.youtube.com/watch?v=fixture",
                    project_root=project,
                    analysis_target="video_content",
                    operation="extract_transcript",
                    youtube_options={"browser_host": "edge"},
                )
        manifest = load_manifest(manifest_path)
        assert_true("YouTube OpenCLI -> material_acquired", manifest.get("status") == "material_acquired", failures)
        assert_true("YouTube OpenCLI records Edge", manifest.get("metadata", {}).get("browser_host") == "edge", failures)
        assert_true("YouTube OpenCLI records execution backend", manifest.get("metadata", {}).get("execution_backend") == "OpenCLI", failures)
        assert_true("YouTube OpenCLI records browser session", manifest.get("privacy", {}).get("browser_session_used") is True, failures)
        assert_true(
            "YouTube OpenCLI transcript is primary",
            any(item.get("type") == "transcript" and item.get("source_class") == "primary" for item in manifest.get("artifacts", [])),
            failures,
        )
        assert_true(
            "YouTube OpenCLI precedes yt-dlp",
            any(command[:3] == ["opencli", "youtube", "transcript"] for command in executed)
            and not any(command and command[0] == "yt-dlp" for command in executed),
            failures,
        )


def test_youtube_edge_browser_is_explicit(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-ar-youtube-edge-") as tmp:
        root = Path(tmp)
        project = root / "project"
        ytdlp = root / "yt-dlp.exe"
        ytdlp.write_text("fixture", encoding="utf-8")
        executed: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs):
            executed.append(command)
            if is_agent_reach_doctor(command):
                return completed(command, stdout=json.dumps({"youtube": {"status": "ok", "active_backend": "yt-dlp"}}))
            if "--dump-single-json" in command:
                return completed(command, stdout=json.dumps({"id": "edge", "title": "Video"}))
            if "--write-subs" in command:
                return completed(command, code=1, stderr="no subtitles")
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.agent_reach_adapter.shutil.which", return_value="agent-reach"):
            with patch("kw_cli.agent_reach_adapter.run_capture", side_effect=fake_run):
                manifest_path = agent_reach_adapter.acquire_with_agent_reach(
                    input_value="https://www.youtube.com/watch?v=edge",
                    project_root=project,
                    youtube_options={
                        "platform_mode": "subtitles",
                        "youtube_browser": "edge",
                        "ytdlp": ytdlp,
                    },
                )
        manifest = load_manifest(manifest_path)
        ytdlp_commands = [command for command in executed if command and command[0] == str(ytdlp.resolve())]
        assert_true(
            "YouTube Edge browser option applied",
            all("--cookies-from-browser" in command and "edge" in command for command in ytdlp_commands),
            failures,
        )
        assert_true("YouTube Edge records cookies used", manifest.get("privacy", {}).get("cookies_used") is True, failures)
        assert_true("YouTube Edge records browser session", manifest.get("privacy", {}).get("browser_session_used") is True, failures)
        assert_true("YouTube Edge route plan records host", manifest.get("metadata", {}).get("route_plan", {}).get("browser_host") == "edge", failures)
        assert_true("YouTube Edge bundle valid", bundle.validate_manifest(manifest_path)["valid"], failures)


def test_conflicting_browser_hosts_are_rejected(failures: list[str]) -> None:
    try:
        agent_reach_adapter.browser_host_from_options(
            {"browser_host": "edge", "youtube_browser": "chrome"}
        )
    except agent_reach_adapter.AgentReachAdapterError:
        return
    failures.append("conflicting browser hosts are rejected")


def test_windows_batch_url_is_quoted(failures: list[str]) -> None:
    quoted = agent_reach_adapter.quote_windows_batch_argument(
        "https://www.xiaohongshu.com/explore/example?xsec_token=abc&xsec_source=pc_feed"
    )
    assert_true("Windows batch URL keeps ampersand inside quotes", quoted.startswith('"') and quoted.endswith('"') and "&xsec_source" in quoted, failures)


def main() -> int:
    failures: list[str] = []
    assert_true(
        "locked browser cookie database is blocked",
        agent_reach_adapter.blocked_status_from_reason("Could not copy Chrome cookie database") == "blocked",
        failures,
    )
    assert_true(
        "locked browser cookie database has actionable next step",
        "selected browser profile is locked" in agent_reach_adapter.youtube_next_action(
            [{"reason": "Could not copy Chrome cookie database"}]
        ),
        failures,
    )
    test_agent_reach_missing_failed_bundle(failures)
    test_youtube_subtitle_material_acquired(failures)
    test_bilibili_metadata_only(failures)
    test_web_page_markdown_artifact(failures)
    test_x_jina_block_keeps_platform(failures)
    test_xiaohongshu_fallback_keeps_platform(failures)
    test_x_twitter_cli_primary_artifact(failures)
    test_x_opencli_status_primary_artifact(failures)
    test_xiaohongshu_opencli_primary_artifact(failures)
    test_xiaohongshu_opencli_warn_blocks_until_ready(failures)
    test_opencli_requires_declared_browser_host(failures)
    test_github_readme_from_clone(failures)
    test_query_search_secondary_bundle(failures)
    test_bilibili_search_backend_cannot_claim_transcript(failures)
    test_youtube_options_are_applied_and_redacted(failures)
    test_youtube_opencli_transcript_is_primary(failures)
    test_youtube_edge_browser_is_explicit(failures)
    test_conflicting_browser_hosts_are_rejected(failures)
    test_windows_batch_url_is_quoted(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_agent_reach_acquire_offline passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
