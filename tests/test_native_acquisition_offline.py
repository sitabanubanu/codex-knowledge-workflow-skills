#!/usr/bin/env python
"""Offline regression tests for the project-owned acquisition layer."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from kw_cli import acquisition_adapter, bundle, ingest, main as kw_main


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def completed(command: list[str], code: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, code, stdout, stderr)


def provider(status: str, backend: str = "", *, message: str = "", hosts: list[str] | None = None) -> dict:
    return {
        "status": status,
        "active_backend": backend,
        "backends": [backend] if backend else [],
        "message": message,
        "provider_id": backend.lower().replace(" ", "_") if backend else "",
        "browser_hosts": hosts or [],
    }


def acquire_with_report(*, report: dict, fake_run, input_value: str, project: Path, **kwargs) -> Path:
    with patch("kw_cli.acquisition_adapter.write_capability_report", return_value=report):
        with patch("kw_cli.acquisition_adapter.run_capture", side_effect=fake_run):
            return acquisition_adapter.acquire_source_material(
                input_value=input_value,
                project_root=project,
                **kwargs,
            )


def test_missing_native_provider_blocks_safely(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-missing-") as tmp:
        def must_not_run(command: list[str], **_kwargs):
            failures.append(f"missing provider executed a command: {command}")
            return completed(command, code=1)

        manifest_path = acquire_with_report(
            report={"youtube": provider("off", message="yt-dlp and OpenCLI are unavailable.")},
            fake_run=must_not_run,
            input_value="https://www.youtube.com/watch?v=abc",
            project=Path(tmp) / "project",
        )
        manifest = load_manifest(manifest_path)
        assert_true("missing provider becomes blocked", manifest.get("status") == "blocked", failures)
        assert_true("native acquisition layer is recorded", manifest.get("acquisition_layer") == "knowledge_workflow_native", failures)
        assert_true("blocked bundle has no fabricated artifacts", not manifest.get("artifacts"), failures)


def test_web_page_markdown(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-web-") as tmp:
        def fake_run(command: list[str], **_kwargs):
            if command and command[0] == "curl":
                return completed(command, stdout="# Page\n\nPrimary article body.")
            return completed(command, code=1, stderr="unexpected")

        manifest_path = acquire_with_report(
            report={"web": provider("ok", "Jina Reader")},
            fake_run=fake_run,
            input_value="https://example.com/page",
            project=Path(tmp) / "project",
        )
        manifest = load_manifest(manifest_path)
        assert_true("web page material acquired", manifest.get("status") == "material_acquired", failures)
        assert_true(
            "web page is a primary Markdown artifact",
            any(item.get("type") == "page_markdown" and item.get("source_class") == "primary" for item in manifest.get("artifacts", [])),
            failures,
        )
        assert_true("web bundle validates", bundle.validate_manifest(manifest_path)["valid"], failures)


def test_youtube_subtitle_and_provider_override(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-youtube-") as tmp:
        root = Path(tmp)
        project = root / "project"
        ytdlp = root / "yt-dlp.exe"
        ytdlp.write_text("fixture", encoding="utf-8")

        def fake_run(command: list[str], **_kwargs):
            if "--dump-single-json" in command:
                return completed(command, stdout=json.dumps({"id": "abc", "title": "Video"}))
            if "--write-subs" in command:
                output_template = Path(command[command.index("-o") + 1])
                subtitle = Path(str(output_template).replace("%(ext)s", "en.vtt"))
                subtitle.parent.mkdir(parents=True, exist_ok=True)
                subtitle.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello.\n", encoding="utf-8")
                return completed(command)
            return completed(command, code=1, stderr="unexpected")

        options = {"ytdlp": ytdlp, "platform_mode": "subtitles", "subtitle_languages": "en"}
        lookup = acquisition_adapter.provider_path_lookup(options)
        assert_true("configured yt-dlp overrides PATH", lookup("yt-dlp") == str(ytdlp.resolve()), failures)
        manifest_path = acquire_with_report(
            report={"youtube": provider("ok", "yt-dlp")},
            fake_run=fake_run,
            input_value="https://www.youtube.com/watch?v=abc",
            project=project,
            youtube_options=options,
        )
        manifest = load_manifest(manifest_path)
        assert_true("YouTube subtitle material acquired", manifest.get("status") == "material_acquired", failures)
        assert_true(
            "YouTube subtitle is primary",
            any(item.get("type") == "subtitle" and item.get("content_scope") == "video_transcript" for item in manifest.get("artifacts", [])),
            failures,
        )


def test_youtube_media_is_deferred_to_evidence_asr(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-youtube-media-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if "--dump-single-json" in command:
                return completed(command, stdout=json.dumps({"id": "abc", "title": "Video"}))
            if "--write-subs" in command:
                return completed(command, code=1, stderr="no subtitles")
            if any("bestaudio/best" in item for item in command):
                output_template = Path(command[command.index("-o") + 1])
                media = Path(str(output_template).replace("%(ext)s", "m4a"))
                media.parent.mkdir(parents=True, exist_ok=True)
                media.write_bytes(b"fixture-media")
                return completed(command)
            return completed(command, code=1, stderr="unexpected")

        manifest_path = acquire_with_report(
            report={"youtube": provider("ok", "yt-dlp")},
            fake_run=fake_run,
            input_value="https://www.youtube.com/watch?v=abc",
            project=project,
            operation="extract_transcript",
        )
        manifest = load_manifest(manifest_path)
        media = [item for item in manifest.get("artifacts", []) if item.get("content_scope") == "media"]
        assert_true("downloaded YouTube media is admitted as primary material", manifest.get("status") == "material_acquired" and bool(media), failures)
        assert_true("media route records evidence-layer ASR handoff", manifest.get("metadata", {}).get("execution_backend") == "yt-dlp_media_then_evidence_asr", failures)


def test_youtube_locked_browser_cookie_falls_back_to_public_route(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-youtube-cookie-fallback-") as tmp:
        project = Path(tmp) / "project"
        executed: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs):
            executed.append(command)
            if "--dump-single-json" in command and "--cookies-from-browser" in command:
                return completed(command, code=1, stderr="ERROR: Could not copy Chrome cookie database.")
            if "--dump-single-json" in command:
                return completed(command, stdout=json.dumps({"id": "abc", "title": "Public Video"}))
            if "--write-subs" in command:
                output_template = Path(command[command.index("-o") + 1])
                subtitle = Path(str(output_template).replace("%(ext)s", "en.vtt"))
                subtitle.parent.mkdir(parents=True, exist_ok=True)
                subtitle.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nPublic subtitle.\n", encoding="utf-8")
                return completed(command)
            return completed(command, code=1, stderr="unexpected")

        with patch("kw_cli.acquisition_adapter.shutil.which", return_value=None):
            manifest_path = acquire_with_report(
                report={"youtube": provider("ok", "yt-dlp")},
                fake_run=fake_run,
                input_value="https://www.youtube.com/watch?v=abc",
                project=project,
                analysis_target="video_content",
                operation="extract_transcript",
                youtube_options={
                    "browser_host": "edge",
                    "youtube_browser": "edge",
                    "platform_mode": "subtitles",
                    "subtitle_languages": "en",
                },
            )
        manifest = load_manifest(manifest_path)
        fallback = manifest.get("metadata", {}).get("browser_access_fallback", {})
        assert_true("locked browser cookies do not block a public YouTube route", manifest.get("status") == "material_acquired", failures)
        assert_true("public fallback is explicitly recorded", fallback.get("anonymous_public_route_used") is True, failures)
        assert_true(
            "browser cookies are attempted before public fallback",
            any("--cookies-from-browser" in command for command in executed),
            failures,
        )
        assert_true(
            "subtitle acquisition uses the cookie-free route after fallback",
            any("--write-subs" in command and "--cookies-from-browser" not in command for command in executed),
            failures,
        )


def test_x_embedded_video_subtitle_uses_native_ytdlp(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-x-video-") as tmp:
        project = Path(tmp) / "project"
        executed: list[list[str]] = []
        subtitle_attempts = 0

        def fake_run(command: list[str], **_kwargs):
            nonlocal subtitle_attempts
            executed.append(command)
            if "--dump-single-json" in command:
                return completed(
                    command,
                    stdout=json.dumps(
                        {
                            "id": "123",
                            "title": "X video",
                            "subtitles": {"zh": [{"ext": "vtt", "url": "https://video.example/subtitle"}]},
                        }
                    ),
                )
            if "--write-subs" in command:
                subtitle_attempts += 1
                if subtitle_attempts == 1:
                    return completed(command, code=1, stderr="transient subtitle request failure")
                output_template = Path(command[command.index("-o") + 1])
                subtitle = Path(str(output_template).replace("%(ext)s", "zh.vtt"))
                subtitle.parent.mkdir(parents=True, exist_ok=True)
                subtitle.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n你好。\n", encoding="utf-8")
                return completed(command)
            return completed(command, code=1, stderr="unexpected")

        manifest_path = acquire_with_report(
            report={
                "twitter": provider("off", message="Tweet-text providers are unavailable."),
                "x_video": provider("ok", "yt-dlp"),
            },
            fake_run=fake_run,
            input_value="https://x.com/example/status/123",
            project=project,
            analysis_target="video_content",
            operation="extract_transcript",
            youtube_options={"platform_mode": "subtitles", "subtitle_languages": "zh"},
        )
        manifest = load_manifest(manifest_path)
        plan = manifest.get("metadata", {}).get("route_plan", {})
        assert_true("X video subtitle material acquired", manifest.get("status") == "material_acquired", failures)
        assert_true("X video route selects yt-dlp", manifest.get("active_backend") == "yt-dlp", failures)
        assert_true("X video capability key is operation-specific", plan.get("capability_key") == "x_video", failures)
        assert_true(
            "X embedded subtitle is task-primary video evidence",
            any(
                item.get("type") == "subtitle"
                and item.get("source_class") == "primary"
                and item.get("content_scope") == "video_transcript"
                for item in manifest.get("artifacts", [])
            ),
            failures,
        )
        assert_true("X video route does not invoke OpenCLI", all(command[0] != "opencli" for command in executed), failures)
        assert_true("X video subtitle route retries one transient failure", subtitle_attempts == 2, failures)
        assert_true(
            "X video route omits YouTube-only extractor arguments",
            all("youtube:" not in " ".join(command) for command in executed),
            failures,
        )
        assert_true("X video bundle validates", bundle.validate_manifest(manifest_path)["valid"], failures)


def test_x_embedded_video_media_is_deferred_to_evidence_asr(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-x-video-media-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if "--dump-single-json" in command:
                return completed(command, stdout=json.dumps({"id": "123", "title": "X video"}))
            if "--write-subs" in command:
                return completed(command, code=1, stderr="no subtitles")
            if any("bestaudio/best" in item for item in command):
                output_template = Path(command[command.index("-o") + 1])
                media = Path(str(output_template).replace("%(ext)s", "mp4"))
                media.parent.mkdir(parents=True, exist_ok=True)
                media.write_bytes(b"fixture-media")
                return completed(command)
            return completed(command, code=1, stderr="unexpected")

        manifest_path = acquire_with_report(
            report={"x_video": provider("ok", "yt-dlp")},
            fake_run=fake_run,
            input_value="https://x.com/example/status/123",
            project=project,
            analysis_target="video_content",
            operation="extract_transcript",
        )
        manifest = load_manifest(manifest_path)
        media = [item for item in manifest.get("artifacts", []) if item.get("content_scope") == "media"]
        assert_true("downloaded X media is admitted for evidence-layer ASR", manifest.get("status") == "material_acquired" and bool(media), failures)
        assert_true(
            "X media route records evidence-layer ASR handoff",
            manifest.get("metadata", {}).get("execution_backend") == "yt-dlp_media_then_evidence_asr",
            failures,
        )


def test_login_platform_never_falls_back_anonymously(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-x-block-") as tmp:
        def must_not_run(command: list[str], **_kwargs):
            failures.append(f"X without provider executed a command: {command}")
            return completed(command, code=1)

        manifest_path = acquire_with_report(
            report={"twitter": provider("off", message="No authorized provider.")},
            fake_run=must_not_run,
            input_value="https://x.com/example/status/123",
            project=Path(tmp) / "project",
        )
        manifest = load_manifest(manifest_path)
        plan = manifest.get("metadata", {}).get("route_plan", {})
        assert_true("X platform is preserved", manifest.get("platform") == "x", failures)
        assert_true("X without provider is blocked", manifest.get("status") == "blocked", failures)
        assert_true("X anonymous fallback is disabled", plan.get("anonymous_web_fallback_allowed") is False, failures)


def test_opencli_requires_declared_host(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-opencli-host-") as tmp:
        executed: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs):
            executed.append(command)
            return completed(command, code=1, stderr="must not execute")

        manifest_path = acquire_with_report(
            report={"xiaohongshu": provider("ok", "OpenCLI", hosts=["edge"])},
            fake_run=fake_run,
            input_value="https://www.xiaohongshu.com/explore/fixture?xsec_token=abc",
            project=Path(tmp) / "project",
        )
        manifest = load_manifest(manifest_path)
        plan = manifest.get("metadata", {}).get("route_plan", {})
        assert_true("OpenCLI without host is blocked", manifest.get("status") == "blocked", failures)
        assert_true("OpenCLI route declares host requirement", plan.get("browser_host_required") is True, failures)
        assert_true("OpenCLI did not execute", not executed, failures)


def test_xiaohongshu_opencli_and_redaction(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-xhs-") as tmp:
        project = Path(tmp) / "project"

        def fake_run(command: list[str], **_kwargs):
            if command[:3] == ["opencli", "xiaohongshu", "note"]:
                return completed(command, stdout=json.dumps([{"field": "title", "value": "note"}, {"field": "content", "value": "primary text"}]))
            return completed(command, code=1, stderr="unexpected")

        secret = "TOPSECRET_XHS_VALUE"
        url = f"https://www.xiaohongshu.com/explore/fixture?xsec_token={secret}"
        manifest_path = acquire_with_report(
            report={"xiaohongshu": provider("ok", "OpenCLI", hosts=["edge"])},
            fake_run=fake_run,
            input_value=url,
            project=project,
            youtube_options={"browser_host": "edge"},
        )
        manifest = load_manifest(manifest_path)
        assert_true("Xiaohongshu OpenCLI material acquired", manifest.get("status") == "material_acquired", failures)
        result = ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
        assert_true("Xiaohongshu material passes source gate", result.get("source_status") == "source_confirmed", failures)
        kw_main.run_preflight(url, "standard", project, False)
        persisted = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in project.rglob("*") if path.is_file())
        assert_true("Xiaohongshu token is not persisted", secret not in persisted, failures)


def test_search_is_secondary_only(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-native-search-") as tmp:
        def fake_run(command: list[str], **_kwargs):
            if command[:2] == ["mcporter", "call"]:
                return completed(command, stdout="- Result one\n- Result two\n")
            return completed(command, code=1, stderr="unexpected")

        manifest_path = acquire_with_report(
            report={"exa_search": provider("ok", "Exa via mcporter")},
            fake_run=fake_run,
            input_value="source gate design",
            project=Path(tmp) / "project",
        )
        manifest = load_manifest(manifest_path)
        assert_true("search result stays secondary", manifest.get("status") == "secondary_only", failures)
        assert_true("search result cannot become primary evidence", all(item.get("source_class") == "secondary" for item in manifest.get("artifacts", [])), failures)


def test_conflicting_browser_hosts_are_rejected(failures: list[str]) -> None:
    try:
        acquisition_adapter.browser_host_from_options({"browser_host": "edge", "youtube_browser": "chrome"})
    except acquisition_adapter.AcquisitionAdapterError:
        return
    failures.append("conflicting browser hosts are rejected")


def main() -> int:
    failures: list[str] = []
    assert_true(
        "locked browser cookie database is blocked",
        acquisition_adapter.blocked_status_from_reason("Could not copy Chrome cookie database") == "blocked",
        failures,
    )
    test_missing_native_provider_blocks_safely(failures)
    test_web_page_markdown(failures)
    test_youtube_subtitle_and_provider_override(failures)
    test_youtube_media_is_deferred_to_evidence_asr(failures)
    test_youtube_locked_browser_cookie_falls_back_to_public_route(failures)
    test_x_embedded_video_subtitle_uses_native_ytdlp(failures)
    test_x_embedded_video_media_is_deferred_to_evidence_asr(failures)
    test_login_platform_never_falls_back_anonymously(failures)
    test_opencli_requires_declared_host(failures)
    test_xiaohongshu_opencli_and_redaction(failures)
    test_search_is_secondary_only(failures)
    test_conflicting_browser_hosts_are_rejected(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_native_acquisition_offline passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
