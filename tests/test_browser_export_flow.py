#!/usr/bin/env python
"""End-to-end tests for authorized browser-export handoff."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kw_cli import bundle, ingest


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="kw-browser-flow-") as tmp:
        root = Path(tmp)
        transcript = root / "transcript.txt"
        transcript.write_text(
            "The speaker argues that agent systems need narrow responsibilities.\n"
            "They explain that evidence gates should prevent unsupported reports.\n",
            encoding="utf-8",
        )
        project = root / "project"
        manifest = bundle.build_browser_export_bundle(
            input_path=transcript,
            source_url="https://www.youtube.com/watch?v=example",
            platform="youtube",
            project_root=project,
            analysis_target="video_content",
            operation="extract_transcript",
            browser_host="edge",
        )
        result = ingest.ingest_bundle(manifest_path=manifest, project_root=project)
        status = ingest.read_json(project / "10_video" / "00_source" / "source_status.json")
        receipt = ingest.read_json(project / "10_video" / "00_source" / "gate_receipt.json")
        assert_true("browser transcript confirms source", result.get("source_status") == "source_confirmed", failures)
        assert_true("browser transcript target scope", status.get("analysis_target") == "video_content", failures)
        assert_true("browser transcript can decompose", status.get("can_enter_full_decomposition") is True, failures)
        assert_true("browser transcript receipt", bool(receipt.get("bundle_id")), failures)
        assert_true("browser transcript records Edge", ingest.read_json(manifest).get("metadata", {}).get("browser_host") == "edge", failures)

        social = root / "social.txt"
        social.write_text(
            "Author: Example\nThe source post directly states that browser exports must remain auditable.\n",
            encoding="utf-8",
        )
        social_project = root / "social-project"
        social_manifest = bundle.build_browser_export_bundle(
            input_path=social,
            source_url="https://x.com/example/status/1",
            platform="x",
            project_root=social_project,
            analysis_target="social_post",
            operation="read",
            browser_host="edge",
        )
        ingest.ingest_bundle(manifest_path=social_manifest, project_root=social_project)
        audit = ingest.run_audit_pipeline(
            project_root=social_project,
            document_goal="source-faithful test report",
            final_language="en",
            audience="test reader",
        )
        claims = ingest.read_json(social_project / "10_video" / "03_inventory" / "claims.json").get("claims") or []
        assert_true("social browser export audit completes", audit.get("status") == "completed", failures)
        assert_true("social direct text becomes source claim", any(claim.get("claim_type") == "source_claim" for claim in claims), failures)

        media = root / "browser-audio.mp3"
        media.write_bytes(b"fixture media requiring ASR")
        media_project = root / "media-project"
        media_manifest = bundle.build_browser_export_bundle(
            input_path=media,
            source_url="https://www.youtube.com/watch?v=media",
            platform="youtube",
            project_root=media_project,
            analysis_target="video_content",
            operation="extract_transcript",
            browser_host="edge",
        )
        media_payload = ingest.read_json(media_manifest)
        media_ingest = ingest.ingest_bundle(manifest_path=media_manifest, project_root=media_project)
        assert_true("browser media retains media scope", media_payload["artifacts"][0]["content_scope"] == "media", failures)
        assert_true("browser media does not pass transcript gate", media_ingest.get("source_status") == "degraded_report_only", failures)

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_browser_export_flow passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
