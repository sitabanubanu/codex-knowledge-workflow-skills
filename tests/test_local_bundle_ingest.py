#!/usr/bin/env python
"""Tests for local acquisition bundle ingest."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kw_cli import bundle, ingest


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def read_status(project: Path) -> dict:
    return ingest.read_json(project / "10_video" / "00_source" / "source_status.json")


def run_local(path: Path, project: Path) -> dict:
    manifest = bundle.build_local_bundle(input_path=path, project_root=project)
    ingest.ingest_bundle(manifest_path=manifest, project_root=project)
    return read_status(project)


def test_local_transcript_confirmed(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-local-transcript-") as tmp:
        root = Path(tmp)
        source = root / "input.txt"
        source.write_text("This is a local transcript.\nIt has enough text.\n", encoding="utf-8")
        status = run_local(source, root / "project")
        assert_true("local transcript -> source_confirmed", status.get("source_status") == "source_confirmed", failures)
        assert_true("local transcript normalizes", (root / "project" / "10_video" / "01_transcript" / "clean_transcript.jsonl").is_file(), failures)


def test_local_subtitle_confirmed(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-local-subtitle-") as tmp:
        root = Path(tmp)
        source = root / "input.vtt"
        source.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nSubtitle text.\n", encoding="utf-8")
        status = run_local(source, root / "project")
        assert_true("local subtitle -> source_confirmed", status.get("source_status") == "source_confirmed", failures)


def test_empty_transcript_degrades(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-local-empty-") as tmp:
        root = Path(tmp)
        source = root / "empty.txt"
        source.write_text("\n\n", encoding="utf-8")
        status = run_local(source, root / "project")
        assert_true("empty transcript -> failure / degraded", status.get("source_status") in {"source_failed", "degraded_report_only"}, failures)
        assert_true("empty transcript no pack", not (root / "project" / "10_video" / "video_analysis_pack.md").exists(), failures)


def test_local_audio_without_asr_degrades(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-local-audio-") as tmp:
        root = Path(tmp)
        source = root / "audio.wav"
        source.write_bytes(b"not really audio")
        status = run_local(source, root / "project")
        assert_true("local audio without ASR -> degraded", status.get("source_status") == "degraded_report_only", failures)
        assert_true("local audio next action mentions ASR", "ASR" in str(status.get("next_step")), failures)


def test_local_audio_with_asr_jsonl_confirms_source(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-local-audio-asr-") as tmp:
        root = Path(tmp)
        source = root / "audio.mp3"
        source.write_bytes(b"fixture audio; ASR uses external JSONL\n")
        project = root / "project"
        manifest_path = bundle.build_local_bundle(input_path=source, project_root=project)
        ingest.ingest_bundle(manifest_path=manifest_path, project_root=project)
        manifest = ingest.read_json(manifest_path)
        result = ingest.run_asr_for_media_bundle(
            manifest_path=manifest_path,
            manifest=manifest,
            project_root=project,
            asr_model="base",
            language="en",
            asr_jsonl=FIXTURES / "asr_sample.jsonl",
        )
        status = read_status(project)
        assert_true("local audio ASR result completed", result.get("status") == "completed", failures)
        assert_true("local audio with ASR -> source_confirmed", status.get("source_status") == "source_confirmed", failures)
        assert_true("local audio ASR source class", status.get("source_classes") == ["primary_audio_asr"], failures)
        assert_true("local audio ASR clean transcript", (project / "10_video" / "01_transcript" / "clean_transcript.jsonl").is_file(), failures)


def main() -> int:
    failures: list[str] = []
    test_local_transcript_confirmed(failures)
    test_local_subtitle_confirmed(failures)
    test_empty_transcript_degrades(failures)
    test_local_audio_without_asr_degrades(failures)
    test_local_audio_with_asr_jsonl_confirms_source(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_local_bundle_ingest passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
