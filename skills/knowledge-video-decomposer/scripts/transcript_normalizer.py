#!/usr/bin/env python
"""Normalize local transcript/subtitle files into knowledge-video transcript artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import acquisition_probe
import artifact_validator
from write_artifact import ArtifactWriteError, write_artifact


RUNNER_NAME = "knowledge-video-transcript-normalizer"
SUPPORTED_SUFFIXES = {".txt", ".md", ".srt", ".vtt", ".jsonl", ".json"}


@dataclass
class Segment:
    raw_id: str
    start: float | None
    end: float | None
    text: str
    source: str
    language: str
    confidence: str
    raw_index: int
    speaker: str = ""
    words: list[dict[str, Any]] | None = None
    asr_confidence: float | None = None
    alignment: dict[str, Any] | None = None
    diarization: dict[str, Any] | None = None


class TranscriptNormalizerError(Exception):
    """Expected CLI-facing transcript normalization failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_text(payload: Any, *, pretty: bool = False) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None)


def write_json(path: Path, payload: Any, *, pretty: bool = False) -> dict[str, Any]:
    return write_artifact(path, json_text(payload, pretty=pretty), json_mode=True, mkdirs=True, overwrite=True)


def write_text(path: Path, text: str) -> dict[str, Any]:
    return write_artifact(path, text, mkdirs=True, overwrite=True)


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def read_utf8(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TranscriptNormalizerError(f"input transcript is not valid UTF-8 text: {exc}") from exc
    except OSError as exc:
        raise TranscriptNormalizerError(f"could not read input transcript: {exc}") from exc


def validate_input(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise TranscriptNormalizerError(f"input transcript does not exist: {resolved}")
    if not resolved.is_file():
        raise TranscriptNormalizerError(f"input transcript is not a file: {resolved}")
    if resolved.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise TranscriptNormalizerError(
            f"unsupported transcript suffix {resolved.suffix!r}; supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
        )
    if resolved.stat().st_size <= 0:
        raise TranscriptNormalizerError(f"input transcript is empty: {resolved}")
    return resolved


def parse_timestamp(value: str) -> float:
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours = "0"
        minutes, seconds = parts
    else:
        raise ValueError(f"invalid timestamp: {value}")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def stamp(seconds: float | None) -> str:
    if seconds is None:
        return "--:--:--"
    millis = int(round(max(0.0, seconds) * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def normalize_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_plain_text(text: str, *, language: str, source: str) -> list[Segment]:
    chunks = [normalize_text(chunk) for chunk in re.split(r"\n\s*\n+", text) if normalize_text(chunk)]
    if not chunks:
        chunks = [normalize_text(line) for line in text.splitlines() if normalize_text(line)]
    return [
        Segment(
            raw_id=f"raw_{idx:04d}",
            start=None,
            end=None,
            text=chunk,
            source=source,
            language=language,
            confidence="medium",
            raw_index=idx - 1,
        )
        for idx, chunk in enumerate(chunks, start=1)
    ]


def parse_srt(text: str, *, language: str) -> list[Segment]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n+", normalized.strip())
    segments: list[Segment] = []
    for raw_index, block in enumerate(blocks):
        lines = [line.strip("\ufeff ") for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if re.fullmatch(r"\d+", lines[0]):
            lines = lines[1:]
        if not lines or "-->" not in lines[0]:
            continue
        left, right = [part.strip() for part in lines[0].split("-->", 1)]
        right = right.split()[0]
        try:
            start = parse_timestamp(left)
            end = parse_timestamp(right)
        except ValueError:
            continue
        body = normalize_text(" ".join(lines[1:]))
        if not body:
            continue
        segments.append(
            Segment(
                raw_id=f"raw_{len(segments) + 1:04d}",
                start=start,
                end=max(start, end),
                text=body,
                source="subtitle",
                language=language,
                confidence="high",
                raw_index=raw_index,
            )
        )
    return segments


def parse_vtt(text: str, *, language: str) -> list[Segment]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in normalized.splitlines():
        stripped = line.strip()
        if stripped.startswith("WEBVTT") or stripped.startswith("NOTE") or stripped.startswith("STYLE"):
            continue
        lines.append(line)
    return parse_srt("\n".join(lines), language=language)


def parse_jsonl(text: str, *, language: str) -> list[Segment]:
    segments: list[Segment] = []
    for raw_index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TranscriptNormalizerError(f"invalid JSONL on line {raw_index + 1}: {exc}") from exc
        if not isinstance(payload, dict):
            raise TranscriptNormalizerError(f"JSONL line {raw_index + 1} is not an object")
        text_value = normalize_text(str(payload.get("text") or payload.get("normalized_text") or ""))
        if not text_value:
            continue
        start_value = payload.get("start")
        end_value = payload.get("end")
        start = float(start_value) if isinstance(start_value, (int, float)) else None
        end = float(end_value) if isinstance(end_value, (int, float)) else None
        words = payload.get("words")
        normalized_words = [word for word in words if isinstance(word, dict)] if isinstance(words, list) else None
        asr_confidence_value = payload.get("asr_confidence", payload.get("avg_logprob"))
        asr_confidence = float(asr_confidence_value) if isinstance(asr_confidence_value, (int, float)) else None
        alignment = payload.get("alignment") if isinstance(payload.get("alignment"), dict) else None
        diarization = payload.get("diarization") if isinstance(payload.get("diarization"), dict) else None
        segments.append(
            Segment(
                raw_id=f"raw_{len(segments) + 1:04d}",
                start=start,
                end=max(start, end) if start is not None and end is not None else end,
                text=text_value,
                source=str(payload.get("source") or "provided_transcript"),
                language=str(payload.get("language") or language),
                confidence=str(payload.get("confidence") or "medium"),
                raw_index=raw_index,
                speaker=str(payload.get("speaker") or ""),
                words=normalized_words,
                asr_confidence=asr_confidence,
                alignment=alignment,
                diarization=diarization,
            )
        )
    return segments


def parse_json(text: str, *, language: str) -> list[Segment]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TranscriptNormalizerError(f"invalid JSON transcript: {exc}") from exc
    if isinstance(payload, dict):
        rows = payload.get("segments") or payload.get("transcript") or []
    else:
        rows = payload
    if not isinstance(rows, list):
        raise TranscriptNormalizerError("JSON transcript must be a list or contain a segments/transcript list")
    return parse_jsonl("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), language=language)


def parse_input(path: Path, *, language: str) -> list[Segment]:
    text = read_utf8(path)
    suffix = path.suffix.lower()
    if suffix == ".srt":
        segments = parse_srt(text, language=language)
    elif suffix == ".vtt":
        segments = parse_vtt(text, language=language)
    elif suffix == ".jsonl":
        segments = parse_jsonl(text, language=language)
    elif suffix == ".json":
        segments = parse_json(text, language=language)
    else:
        segments = split_plain_text(text, language=language, source="provided_transcript")
    if not segments:
        raise TranscriptNormalizerError("input transcript contained no usable text segments")
    return segments


def raw_rows(segments: list[Segment]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for segment in segments:
        row = {
            "id": segment.raw_id,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "source": segment.source,
            "language": segment.language,
            "confidence": segment.confidence,
            "raw_index": segment.raw_index,
        }
        if segment.speaker:
            row["speaker"] = segment.speaker
        if segment.words:
            row["words"] = segment.words
        if segment.asr_confidence is not None:
            row["asr_confidence"] = segment.asr_confidence
        if segment.alignment:
            row["alignment"] = segment.alignment
        if segment.diarization:
            row["diarization"] = segment.diarization
        rows.append(row)
    return rows


def clean_rows(segments: list[Segment]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, segment in enumerate(segments, start=1):
        row: dict[str, Any] = {
            "id": f"t{idx:04d}",
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "normalized_text": normalize_text(segment.text),
            "source_ids": [segment.raw_id],
            "language": segment.language,
            "speaker": segment.speaker,
            "confidence": segment.confidence,
        }
        if segment.words:
            row["words"] = segment.words
            row["word_timestamps_available"] = True
        else:
            row["word_timestamps_available"] = False
        if segment.asr_confidence is not None:
            row["asr_confidence"] = segment.asr_confidence
        if segment.alignment:
            row["alignment"] = segment.alignment
        if segment.diarization:
            row["diarization"] = segment.diarization
        rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    return write_text(path, text)


def render_clean_markdown(rows: list[dict[str, Any]], source_path: Path) -> str:
    lines = [
        "# Clean Transcript",
        "",
        f"- source_file: `{source_path}`",
        f"- segments: `{len(rows)}`",
        "",
    ]
    for row in rows:
        start = stamp(row.get("start") if isinstance(row.get("start"), (int, float)) else None)
        end = stamp(row.get("end") if isinstance(row.get("end"), (int, float)) else None)
        lines.append(f"[{start}-{end}] {row['id']}: {row['normalized_text']}")
    lines.append("")
    return "\n".join(lines)


def build_source_status(*, source_path: Path, timed_segments: int, total_segments: int) -> dict[str, Any]:
    probe_args = argparse.Namespace(
        source_type="local_transcript",
        probe=["user_file"],
        signal=["local_transcript"],
        attempts=1,
        max_time_seconds=0,
    )
    status = acquisition_probe.build_summary(probe_args)
    status.update(
        {
            "runner": RUNNER_NAME,
            "url": None,
            "platform": "local_file",
            "generated_at": now_iso(),
            "input_file": str(source_path),
            "transcript_segments": total_segments,
            "timed_segments": timed_segments,
            "timestamp_coverage": timed_segments / total_segments if total_segments else 0.0,
            "next_step": "enter_segmentation_inventory_logic_gap_check",
        }
    )
    return status


def render_acquisition_notes(args: argparse.Namespace, source_path: Path, rows: list[dict[str, Any]], status: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Source Transcript Normalization Notes",
            "",
            f"Input file: `{source_path}`",
            f"Input kind: `{source_path.suffix.lower().lstrip('.')}`",
            f"Language: `{args.language}`",
            f"Source status: `{status['source_status']}`",
            f"Segments written: `{len(rows)}`",
            f"Timed segments: `{status['timed_segments']}`",
            "",
            "## Provenance",
            "",
            "The transcript material came from a local user-provided transcript/subtitle file or a local subtitle file produced by a prior acquisition step.",
            "No platform request, browser launch, media download, or ASR run was performed by this normalizer.",
            "",
            "## Limitations",
            "",
            "- Plain text and Markdown inputs may not include timestamps.",
            "- Subtitle inputs preserve cue timestamps where parseable.",
            "- This stage does not extract concepts, claims, argument segments, or speaker logic.",
            "",
        ]
    )


def render_gap_check(status: dict[str, Any]) -> str:
    timestamp_note = (
        "All transcript segments include timestamps."
        if status["timestamp_coverage"] >= 1.0
        else "Some or all transcript segments lack timestamps; downstream evidence must rely on transcript IDs for those spans."
    )
    return "\n".join(
        [
            "# Gap Check",
            "",
            "## Acquisition Issues",
            "",
            f"- {timestamp_note}",
            "- Transcript has been normalized, but semantic segmentation and source logic reconstruction have not been run yet.",
            "",
            "## Downstream Notes",
            "",
            "- Use `01_transcript/clean_transcript.jsonl` as the evidence base for stage four segmentation.",
            "- Do not write `video_analysis_pack.md` until segments, inventory, source logic, and gap review are produced.",
            "",
        ]
    )


def run_normalization(args: argparse.Namespace) -> dict[str, Any]:
    if args.output_root is None:
        raise TranscriptNormalizerError("--output-root is required unless --self-test is used")
    source_path = validate_input(Path(args.input))
    segments = parse_input(source_path, language=args.language)
    raw = raw_rows(segments)
    clean = clean_rows(segments)
    timed_segments = sum(1 for row in clean if isinstance(row.get("start"), (int, float)) and isinstance(row.get("end"), (int, float)))
    output_root = args.output_root.expanduser().resolve()
    status = build_source_status(source_path=source_path, timed_segments=timed_segments, total_segments=len(clean))
    metadata = {
        "source_url": "",
        "canonical_url": "",
        "title": source_path.stem,
        "speaker_or_channel": "",
        "platform": "local_file",
        "published_at": "",
        "duration": "",
        "language": args.language,
        "source_type": "subtitle" if source_path.suffix.lower() in {".srt", ".vtt"} else "transcript",
        "collected_at": now_iso(),
        "tools_used": [RUNNER_NAME],
        "confidence": "high" if timed_segments == len(clean) else "medium",
        "notes": "Normalized local transcript/subtitle material.",
    }

    written = [
        write_json(output_root / "00_source" / "source_status.json", status, pretty=True),
        write_json(output_root / "00_source" / "metadata.json", metadata, pretty=True),
        write_text(output_root / "00_source" / "acquisition_notes.md", render_acquisition_notes(args, source_path, clean, status)),
        write_jsonl(output_root / "01_transcript" / "raw_transcript.jsonl", raw),
        write_jsonl(output_root / "01_transcript" / "clean_transcript.jsonl", clean),
        write_text(output_root / "01_transcript" / "clean_transcript.md", render_clean_markdown(clean, source_path)),
        write_text(output_root / "05_gap_check" / "gap_check.md", render_gap_check(status)),
    ]
    validation = artifact_validator.validate_artifact_root(
        output_root,
        output_root / "00_source" / "source_status.json",
        mode="strict",
    )
    return {
        "runner": RUNNER_NAME,
        "output_root": str(output_root),
        "source_status": status["source_status"],
        "can_enter_full_decomposition": status["can_enter_full_decomposition"],
        "primary_material_available": status["primary_material_available"],
        "segments": len(clean),
        "timed_segments": timed_segments,
        "timestamp_coverage": status["timestamp_coverage"],
        "files_written": [item["path"] for item in written],
        "validation": validation,
        "next_step": status["next_step"],
        "validation_next_step": validation.get("next_step"),
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize local transcript/subtitle files into 01_transcript artifacts.")
    parser.add_argument("--input", default=None, help="Local .txt/.md/.srt/.vtt/.jsonl/.json transcript file.")
    parser.add_argument("--output-root", type=Path, default=None, help="Artifact root to write.")
    parser.add_argument("--language", default="unknown", help="Language label to attach when input lacks one.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="transcript-normalizer-") as tmp:
        base = Path(tmp)
        srt = base / "sample.srt"
        srt.write_text(
            "1\n00:00:01,000 --> 00:00:03,500\nHello world.\n\n2\n00:00:04,000 --> 00:00:05,000\nSecond cue.\n",
            encoding="utf-8",
        )
        srt_result = run_normalization(
            argparse.Namespace(input=str(srt), output_root=base / "srt_out", language="en", pretty=False, self_test=False)
        )
        assert_true("srt confirmed", srt_result["source_status"] == "source_confirmed", failures)
        assert_true("srt segments", srt_result["segments"] == 2, failures)
        assert_true("srt timed", srt_result["timestamp_coverage"] == 1.0, failures)
        assert_true("srt validates", srt_result["validation"]["valid"] is True, failures, json.dumps(srt_result["validation"], ensure_ascii=False))

        txt = base / "sample.txt"
        txt.write_text("First paragraph.\n\nSecond paragraph.", encoding="utf-8")
        txt_result = run_normalization(
            argparse.Namespace(input=str(txt), output_root=base / "txt_out", language="en", pretty=False, self_test=False)
        )
        assert_true("txt confirmed", txt_result["source_status"] == "source_confirmed", failures)
        assert_true("txt untimed", txt_result["timestamp_coverage"] == 0.0, failures)
        assert_true("txt validates", txt_result["validation"]["valid"] is True, failures, json.dumps(txt_result["validation"], ensure_ascii=False))
        assert_true("txt does not create semantic segments", not (base / "txt_out" / "02_segments").exists(), failures)
        assert_true("txt does not create inventory", not (base / "txt_out" / "03_inventory").exists(), failures)
        assert_true("txt does not create logic", not (base / "txt_out" / "04_logic").exists(), failures)
        assert_true("txt does not create pack", not (base / "txt_out" / "video_analysis_pack.md").exists(), failures)

        jsonl = base / "sample.jsonl"
        jsonl.write_text(
            json.dumps({"start": 0, "end": 1.5, "text": "JSONL segment.", "language": "en"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        jsonl_result = run_normalization(
            argparse.Namespace(input=str(jsonl), output_root=base / "jsonl_out", language="unknown", pretty=False, self_test=False)
        )
        assert_true("jsonl confirmed", jsonl_result["source_status"] == "source_confirmed", failures)
        assert_true("jsonl timed", jsonl_result["timestamp_coverage"] == 1.0, failures)

        words_jsonl = base / "words.jsonl"
        words_jsonl.write_text(
            json.dumps(
                {
                    "start": 0,
                    "end": 1.5,
                    "text": "Word timed segment.",
                    "language": "en",
                    "speaker": "SPEAKER_00",
                    "words": [{"word": "Word", "start": 0.0, "end": 0.4, "confidence": 0.9}],
                    "alignment": {"engine": "fixture"},
                    "diarization": {"engine": "fixture"},
                    "asr_confidence": 0.88,
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        words_result = run_normalization(
            argparse.Namespace(input=str(words_jsonl), output_root=base / "words_out", language="unknown", pretty=False, self_test=False)
        )
        words_clean = json.loads((base / "words_out" / "01_transcript" / "clean_transcript.jsonl").read_text(encoding="utf-8-sig").splitlines()[0])
        assert_true("words jsonl confirmed", words_result["source_status"] == "source_confirmed", failures)
        assert_true("words preserved", words_clean.get("word_timestamps_available") is True and len(words_clean.get("words") or []) == 1, failures, json.dumps(words_clean, ensure_ascii=False))
        assert_true("speaker preserved", words_clean.get("speaker") == "SPEAKER_00", failures, json.dumps(words_clean, ensure_ascii=False))
        assert_true("alignment preserved", isinstance(words_clean.get("alignment"), dict), failures, json.dumps(words_clean, ensure_ascii=False))

        missing_failed = False
        try:
            run_normalization(
                argparse.Namespace(input=str(base / "missing.srt"), output_root=base / "missing_out", language="en", pretty=False, self_test=False)
            )
        except TranscriptNormalizerError:
            missing_failed = True
        assert_true("missing fails", missing_failed, failures)

        empty = base / "empty.txt"
        empty.write_text("", encoding="utf-8")
        empty_failed = False
        try:
            run_normalization(
                argparse.Namespace(input=str(empty), output_root=base / "empty_out", language="en", pretty=False, self_test=False)
            )
        except TranscriptNormalizerError:
            empty_failed = True
        assert_true("empty fails", empty_failed, failures)
        assert_true("empty creates no output", not (base / "empty_out").exists(), failures)

        no_text_srt = base / "no_text.srt"
        no_text_srt.write_text("1\n00:00:01,000 --> 00:00:03,000\n   \n", encoding="utf-8")
        no_text_failed = False
        try:
            run_normalization(
                argparse.Namespace(input=str(no_text_srt), output_root=base / "no_text_out", language="en", pretty=False, self_test=False)
            )
        except TranscriptNormalizerError:
            no_text_failed = True
        assert_true("no-text srt fails", no_text_failed, failures)
        assert_true("no-text srt creates no output", not (base / "no_text_out").exists(), failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("self-test passed")
    return 0


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    try:
        summary = run_normalization(args)
    except (TranscriptNormalizerError, ArtifactWriteError, OSError) as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "error": exc.__class__.__name__,
                "message": str(exc),
            },
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return 1
    emit_json(summary, pretty=args.pretty)
    return 0 if summary["validation"].get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
