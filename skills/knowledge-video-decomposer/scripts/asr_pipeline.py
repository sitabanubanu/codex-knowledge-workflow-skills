#!/usr/bin/env python
"""Run or resume local ASR and normalize it into transcript artifacts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import artifact_validator
from write_artifact import write_artifact


RUNNER_NAME = "knowledge-video-asr-pipeline"
MEDIA_SUFFIXES = {".mp4", ".m4a", ".mp3", ".wav", ".webm", ".mkv", ".mov", ".aac", ".flac", ".ogg", ".opus"}
DEFAULT_HEARSAY_PYTHON = Path.home() / ".codex" / "tools" / "hearsay-venv" / "Scripts" / "python.exe"


class AsrPipelineError(Exception):
    """Expected CLI-facing ASR pipeline failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def write_json(path: Path, payload: Any) -> dict[str, Any]:
    return write_artifact(path, json.dumps(payload, ensure_ascii=False, indent=2), json_mode=True, mkdirs=True, overwrite=True)


def write_text(path: Path, text: str) -> dict[str, Any]:
    return write_artifact(path, text, mkdirs=True, overwrite=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise AsrPipelineError(f"invalid JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise AsrPipelineError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AsrPipelineError(f"JSON file is not an object: {path}")
    return payload


def validate_media(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise AsrPipelineError(f"input media is not a file: {resolved}")
    if resolved.suffix.lower() not in MEDIA_SUFFIXES:
        raise AsrPipelineError(f"unsupported media suffix {resolved.suffix!r}; supported: {', '.join(sorted(MEDIA_SUFFIXES))}")
    if resolved.stat().st_size <= 0:
        raise AsrPipelineError(f"input media is empty: {resolved}")
    return resolved


def resolve_python(value: str | None) -> Path:
    if value:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise AsrPipelineError(f"ASR Python runtime does not exist: {path}")
        return path
    if DEFAULT_HEARSAY_PYTHON.is_file():
        return DEFAULT_HEARSAY_PYTHON
    return Path(sys.executable).resolve()


def run_command(command: list[str], *, cwd: Path, timeout: int | None = None) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": 124,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "error": "timeout",
        }
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": (completed.stdout or "").strip(),
        "stderr": (completed.stderr or "").strip(),
    }


def check_runtime(python_exe: Path) -> dict[str, Any]:
    ffmpeg_path = shutil.which("ffmpeg")
    whisper_check = run_command(
        [str(python_exe), "-c", "import faster_whisper; print('ok')"],
        cwd=Path.cwd(),
        timeout=20,
    )
    return {
        "python": str(python_exe),
        "ffmpeg": {
            "available": bool(ffmpeg_path),
            "path": ffmpeg_path or "",
        },
        "faster_whisper": {
            "available": bool(whisper_check.get("ok")),
            "check": whisper_check,
        },
    }


def require_runtime(runtime: dict[str, Any]) -> None:
    if not runtime["ffmpeg"]["available"]:
        raise AsrPipelineError("ffmpeg is not available; install ffmpeg or add it to PATH before ASR")
    if not runtime["faster_whisper"]["available"]:
        raise AsrPipelineError("faster_whisper is not importable in the selected ASR Python runtime")


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise AsrPipelineError(f"could not read ASR JSONL: {exc}") from exc
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AsrPipelineError(f"invalid ASR JSONL line {index}: {exc}") from exc
        if isinstance(row, dict):
            rows.append(row)
    if not rows:
        raise AsrPipelineError("ASR JSONL contains no segments")
    return rows


def row_words(row: dict[str, Any]) -> list[dict[str, Any]]:
    words = row.get("words")
    return [word for word in words if isinstance(word, dict)] if isinstance(words, list) else []


def has_word_timestamps(row: dict[str, Any]) -> bool:
    words = row_words(row)
    return bool(words) and all(isinstance(word.get("start"), (int, float)) and isinstance(word.get("end"), (int, float)) for word in words)


def has_speaker(row: dict[str, Any]) -> bool:
    return bool(str(row.get("speaker") or "").strip())


def collect_asr_warnings(rows: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if not any(has_word_timestamps(row) for row in rows):
        warnings.append("No word-level timestamps are available; evidence should use segment timestamps and transcript IDs.")
    if not any(has_speaker(row) for row in rows):
        warnings.append("No speaker labels are available; diarization is absent or not trusted.")
    return warnings


def infer_row_engine(rows: list[dict[str, Any]], fallback: str) -> str:
    engines = sorted({str(row.get("engine")).strip() for row in rows if str(row.get("engine") or "").strip()})
    if len(engines) == 1:
        return engines[0]
    if len(engines) > 1:
        return "mixed_external_asr"
    return fallback


def alignment_report(rows: list[dict[str, Any]], engine: str) -> dict[str, Any]:
    aligned_rows = [row for row in rows if isinstance(row.get("alignment"), dict)]
    word_rows = [row for row in rows if has_word_timestamps(row)]
    return {
        "schema_version": 1,
        "engine": engine,
        "whisperx_compatible": True,
        "status": "word_aligned" if word_rows else "segment_only",
        "segments": len(rows),
        "segments_with_word_timestamps": len(word_rows),
        "word_timestamp_coverage": len(word_rows) / len(rows) if rows else 0.0,
        "segments_with_alignment_metadata": len(aligned_rows),
        "notes": [
            "Alignment status is derived from supplied word timestamps and alignment metadata.",
            "WhisperX alignment can populate words and alignment metadata later without changing the clean transcript schema.",
        ],
    }


def diarization_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    speaker_rows = [row for row in rows if has_speaker(row)]
    speakers = sorted({str(row.get("speaker")) for row in speaker_rows if row.get("speaker")})
    diarized_rows = [row for row in rows if isinstance(row.get("diarization"), dict)]
    return {
        "schema_version": 1,
        "status": "speaker_labels_present" if speaker_rows else "not_available",
        "segments": len(rows),
        "segments_with_speaker": len(speaker_rows),
        "speaker_coverage": len(speaker_rows) / len(rows) if rows else 0.0,
        "speakers": speakers,
        "segments_with_diarization_metadata": len(diarized_rows),
        "notes": [
            "Missing speaker labels are allowed; downstream stages must not infer speakers from ASR text alone.",
            "WhisperX or another diarization tool can populate this artifact later.",
        ],
    }


def quality_from_model(model: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    model_key = str(model or "").lower()
    if "tiny" in model_key:
        exact = "low"
        structural = "medium-low"
    elif "base" in model_key:
        exact = "medium-low"
        structural = "medium"
    elif "small" in model_key:
        exact = "medium"
        structural = "medium-high"
    else:
        exact = "medium"
        structural = "medium"
    timed = sum(1 for row in rows if isinstance(row.get("start"), (int, float)) and isinstance(row.get("end"), (int, float)))
    word_timed = sum(1 for row in rows if has_word_timestamps(row))
    speaker_labeled = sum(1 for row in rows if has_speaker(row))
    durations = [
        max(0.0, float(row["end"]) - float(row["start"]))
        for row in rows
        if isinstance(row.get("start"), (int, float)) and isinstance(row.get("end"), (int, float))
    ]
    return {
        "segments": len(rows),
        "timed_segments": timed,
        "timestamp_coverage": timed / len(rows) if rows else 0.0,
        "segments_with_word_timestamps": word_timed,
        "word_timestamp_coverage": word_timed / len(rows) if rows else 0.0,
        "segments_with_speaker": speaker_labeled,
        "speaker_coverage": speaker_labeled / len(rows) if rows else 0.0,
        "total_segment_duration": round(sum(durations), 3),
        "exact_wording_confidence": exact,
        "structural_summary_confidence": structural,
        "alignment_status": "word_aligned" if word_timed else "segment_only",
        "diarization_status": "speaker_labels_present" if speaker_labeled else "not_available",
        "verified_verbatim": False,
        "warnings": collect_asr_warnings(rows),
        "known_limitations": [
            "ASR may contain wording errors and should not be treated as verbatim unless reviewed.",
            "Speaker labels are not guaranteed.",
            "Noisy audio, music, accents, or overlapping speech may reduce confidence.",
        ],
    }


def render_report(report: dict[str, Any]) -> str:
    quality = report["quality"]
    runtime = report["runtime"]
    lines = [
        "# ASR Pipeline Report",
        "",
        f"- Runner: `{RUNNER_NAME}`",
        f"- Source media: `{report['input_media']}`",
        f"- ASR JSONL: `{report['asr_jsonl']}`",
        f"- ASR Markdown: `{report['asr_markdown']}`",
        f"- Engine: `{report['engine']}`",
        f"- Model: `{report['model']}`",
        f"- Language: `{report['language'] or 'auto'}`",
        f"- VAD: `{str(report['vad_filter']).lower()}`",
        f"- Python: `{runtime['python']}`",
        f"- ffmpeg available: `{str(runtime['ffmpeg']['available']).lower()}`",
        f"- faster_whisper available: `{str(runtime['faster_whisper']['available']).lower()}`",
        "",
        "## Quality",
        "",
        f"- Segments: `{quality['segments']}`",
        f"- Timed segments: `{quality['timed_segments']}`",
        f"- Timestamp coverage: `{quality['timestamp_coverage']}`",
        f"- Segments with word timestamps: `{quality['segments_with_word_timestamps']}`",
        f"- Word timestamp coverage: `{quality['word_timestamp_coverage']}`",
        f"- Segments with speaker labels: `{quality['segments_with_speaker']}`",
        f"- Speaker coverage: `{quality['speaker_coverage']}`",
        f"- Alignment status: `{quality['alignment_status']}`",
        f"- Diarization status: `{quality['diarization_status']}`",
        f"- Verified verbatim: `{str(quality['verified_verbatim']).lower()}`",
        f"- Exact wording confidence: `{quality['exact_wording_confidence']}`",
        f"- Structural summary confidence: `{quality['structural_summary_confidence']}`",
        "",
        "## Warnings",
        "",
    ]
    if quality.get("warnings"):
        lines.extend(f"- {item}" for item in quality["warnings"])
    else:
        lines.append("- No ASR quality warnings were generated.")
    lines.extend(
        [
            "",
            "## Compatibility Artifacts",
            "",
            "- Alignment report: `00_source/asr_alignment_report.json`",
            "- Diarization report: `00_source/asr_diarization.json`",
            "",
            "These artifacts are compatible placeholders for future WhisperX alignment or diarization. Empty or `not_available` status does not fail the ASR pipeline.",
            "",
        ]
    )
    lines.extend(
        [
        "## Limitations",
        "",
        ]
    )
    lines.extend(f"- {item}" for item in quality["known_limitations"])
    lines.extend(["", "## Next Step", "", f"- `{report['next_step']}`", ""])
    return "\n".join(lines)


def append_acquisition_notes(output_root: Path, report: dict[str, Any]) -> None:
    notes_path = output_root / "00_source" / "acquisition_notes.md"
    existing = notes_path.read_text(encoding="utf-8-sig") if notes_path.is_file() else ""
    addition = "\n".join(
        [
            "",
            "## ASR Provenance",
            "",
            f"- Input media: `{report['input_media']}`",
            f"- Engine: `{report['engine']}`",
            f"- Model: `{report['model']}`",
            f"- Language: `{report['language'] or 'auto'}`",
            f"- VAD: `{str(report['vad_filter']).lower()}`",
            f"- Source class: `primary_audio_asr`",
            f"- Exact wording confidence: `{report['quality']['exact_wording_confidence']}`",
            f"- Structural summary confidence: `{report['quality']['structural_summary_confidence']}`",
            "- Treat this transcript as ASR-derived, not as official subtitles or verbatim source text unless reviewed.",
            "",
        ]
    )
    write_text(notes_path, existing.rstrip() + "\n" + addition)


def patch_source_status(output_root: Path, report: dict[str, Any]) -> dict[str, Any]:
    path = output_root / "00_source" / "source_status.json"
    status = read_json(path)
    status.update(
        {
            "source_classes": ["primary_audio_asr"],
            "primary_material_available": True,
            "asr_pipeline": {
                "runner": RUNNER_NAME,
                "input_media": report["input_media"],
                "engine": report["engine"],
                "model": report["model"],
                "language": report["language"],
                "vad_filter": report["vad_filter"],
                "quality": report["quality"],
                "quality_report": "00_source/asr_pipeline_report.json",
                "alignment_report": "00_source/asr_alignment_report.json",
                "diarization_report": "00_source/asr_diarization.json",
            },
            "asr_quality": report["quality"],
            "status_reason": "Primary material is available as ASR transcript derived from local audio/video.",
            "next_step": "enter_segmentation_inventory_logic_gap_check",
        }
    )
    write_json(path, status)
    return status


def run_transcription(
    *,
    python_exe: Path,
    script: Path,
    input_media: Path,
    markdown_path: Path,
    jsonl_path: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    command = [
        str(python_exe),
        str(script),
        str(input_media),
        str(markdown_path),
        str(jsonl_path),
        "--model",
        args.model,
        "--device",
        args.device,
        "--compute-type",
        args.compute_type,
        "--timeout-seconds",
        str(args.timeout_seconds),
    ]
    if args.language:
        command.extend(["--language", args.language])
    command.append("--vad" if args.vad_filter else "--no-vad")
    if args.local_files_only:
        command.append("--local-files-only")
    result = run_command(command, cwd=script.parent, timeout=int(args.timeout_seconds) + 30 if args.timeout_seconds else None)
    if not result.get("ok"):
        raise AsrPipelineError(f"faster-whisper transcription failed: {result.get('stderr') or result.get('stdout')}")
    return result


def run_normalizer(output_root: Path, asr_jsonl: Path, language: str | None) -> dict[str, Any]:
    script = Path(__file__).resolve().parent / "transcript_normalizer.py"
    command = [
        sys.executable,
        str(script),
        "--input",
        str(asr_jsonl),
        "--output-root",
        str(output_root),
        "--language",
        language or "unknown",
    ]
    result = run_command(command, cwd=script.parent, timeout=None)
    if not result.get("ok"):
        raise AsrPipelineError(f"transcript normalization failed: {result.get('stderr') or result.get('stdout')}")
    try:
        parsed = json.loads(result["stdout"].splitlines()[-1] if result.get("stdout") else "{}")
    except json.JSONDecodeError:
        parsed = {}
    return parsed if isinstance(parsed, dict) else {}


def run_asr_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.expanduser().resolve()
    input_media = validate_media(args.input_media)
    python_exe = resolve_python(args.asr_python)
    runtime = check_runtime(python_exe)
    if not args.asr_jsonl:
        require_runtime(runtime)

    asr_jsonl = (args.asr_jsonl.expanduser().resolve() if args.asr_jsonl else output_root / "01_transcript" / "asr_transcript.jsonl")
    asr_markdown = output_root / "01_transcript" / "asr_transcript.md"
    transcription_result: dict[str, Any] | None = None
    if args.asr_jsonl:
        if not asr_jsonl.is_file():
            raise AsrPipelineError(f"--asr-jsonl does not exist: {asr_jsonl}")
        rows = parse_jsonl(asr_jsonl)
        if not asr_markdown.exists():
            write_text(asr_markdown, "# ASR Transcript\n\n" + "\n".join(str(row.get("text", "")).strip() for row in rows if row.get("text")) + "\n")
    else:
        transcription_result = run_transcription(
            python_exe=python_exe,
            script=Path(__file__).resolve().parent / "transcribe_faster_whisper.py",
            input_media=input_media,
            markdown_path=asr_markdown,
            jsonl_path=asr_jsonl,
            args=args,
        )
        rows = parse_jsonl(asr_jsonl)

    normalizer_summary = run_normalizer(output_root, asr_jsonl, args.language)
    engine = infer_row_engine(rows, "external_asr_jsonl" if args.asr_jsonl else "faster-whisper")
    quality = quality_from_model(args.model, rows)
    alignment = alignment_report(rows, engine)
    diarization = diarization_report(rows)
    report = {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "input_media": str(input_media),
        "output_root": str(output_root),
        "asr_jsonl": str(asr_jsonl),
        "asr_markdown": str(asr_markdown),
        "engine": engine,
        "model": args.model,
        "language": args.language,
        "vad_filter": args.vad_filter,
        "runtime": runtime,
        "quality": quality,
        "alignment_report": alignment,
        "diarization_report": diarization,
        "word_timestamp_policy": {
            "available": quality["segments_with_word_timestamps"] > 0,
            "required": False,
            "fallback": "segment_timestamps_and_transcript_ids",
        },
        "asr_verbatim_policy": {
            "verified_verbatim": False,
            "boundary": "ASR-derived transcript supports source-grounded analysis but must not be called verbatim unless independently reviewed.",
        },
        "engine_boundary": {
            "faster_whisper": "segment-level ASR transcript generation; may include word timestamps when supplied by upstream JSONL or engine output.",
            "whisperx": "future optional alignment and diarization layer; not required for this pipeline to succeed.",
        },
        "transcription_result": transcription_result,
        "normalizer_summary": normalizer_summary,
        "next_step": "enter_segmentation_inventory_logic_gap_check",
    }
    patch_source_status(output_root, report)
    append_acquisition_notes(output_root, report)
    written = [
        write_json(output_root / "00_source" / "asr_pipeline_report.json", report),
        write_json(output_root / "00_source" / "asr_alignment_report.json", alignment),
        write_json(output_root / "00_source" / "asr_diarization.json", diarization),
        write_text(output_root / "00_source" / "asr_pipeline_report.md", render_report(report)),
    ]
    validation = artifact_validator.validate_artifact_root(
        output_root,
        output_root / "00_source" / "source_status.json",
        mode="strict",
    )
    if validation.get("valid") is not True:
        findings = validation.get("findings") if isinstance(validation.get("findings"), list) else []
        details = "; ".join(
            str(item.get("message") or item.get("code") or item)
            if isinstance(item, dict)
            else str(item)
            for item in findings
        )
        raise AsrPipelineError(
            "strict artifact validation failed"
            + (f": {details}" if details else "")
        )
    return {
        "runner": RUNNER_NAME,
        "output_root": str(output_root),
        "input_media": str(input_media),
        "source_status": "source_confirmed",
        "source_class": "primary_audio_asr",
        "engine": engine,
        "segments": quality["segments"],
        "timestamp_coverage": quality["timestamp_coverage"],
        "word_timestamp_coverage": quality["word_timestamp_coverage"],
        "speaker_coverage": quality["speaker_coverage"],
        "alignment_status": quality["alignment_status"],
        "diarization_status": quality["diarization_status"],
        "exact_wording_confidence": quality["exact_wording_confidence"],
        "structural_summary_confidence": quality["structural_summary_confidence"],
        "files_written": [item["path"] for item in written] + [str(asr_jsonl), str(asr_markdown)],
        "validation": validation,
        "next_step": "enter_segmentation_inventory_logic_gap_check",
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local faster-whisper ASR and normalize transcript artifacts.")
    parser.add_argument("--input-media", type=Path, required=False, help="Local audio/video file.")
    parser.add_argument("--output-root", type=Path, required=False, help="10_video artifact root.")
    parser.add_argument("--asr-jsonl", type=Path, default=None, help="Existing ASR JSONL to normalize instead of running faster-whisper.")
    parser.add_argument("--asr-python", default=None, help="Python runtime that can import faster_whisper.")
    parser.add_argument("--model", default="base", help="faster-whisper model name or local path.")
    parser.add_argument("--language", default=None, help="Optional language code such as zh or en.")
    parser.add_argument("--device", default="cpu", help="faster-whisper device.")
    parser.add_argument("--compute-type", default="int8", help="faster-whisper compute type.")
    parser.add_argument("--timeout-seconds", type=float, default=0.0, help="Soft transcription timeout seconds.")
    parser.add_argument("--local-files-only", action="store_true", help="Do not download model files.")
    vad_group = parser.add_mutually_exclusive_group()
    vad_group.add_argument("--vad", dest="vad_filter", action="store_true", help="Enable VAD filtering.")
    vad_group.add_argument("--no-vad", dest="vad_filter", action="store_false", help="Disable VAD filtering.")
    parser.set_defaults(vad_filter=True)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="asr-pipeline-") as tmp:
        base = Path(tmp)
        media = base / "fixture.mp3"
        media.write_bytes(b"not real audio; self-test uses --asr-jsonl\n")
        asr_jsonl = base / "fixture_asr.jsonl"
        rows = [
            {
                "id": "t0001",
                "start": 0.0,
                "end": 3.0,
                "text": "Source Gate means confirmed primary material.",
                "source": "ASR",
                "engine": "faster-whisper",
                "model": "base",
                "language": "en",
                "confidence": "medium",
                "raw_index": 0,
            },
            {
                "id": "t0002",
                "start": 3.0,
                "end": 8.0,
                "text": "Metadata alone cannot support speaker logic.",
                "source": "ASR",
                "engine": "faster-whisper",
                "model": "base",
                "language": "en",
                "confidence": "medium",
                "raw_index": 1,
            },
        ]
        write_text(asr_jsonl, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
        output_root = base / "10_video"
        result = run_asr_pipeline(
            argparse.Namespace(
                input_media=media,
                output_root=output_root,
                asr_jsonl=asr_jsonl,
                asr_python=None,
                model="base",
                language="en",
                device="cpu",
                compute_type="int8",
                timeout_seconds=0.0,
                local_files_only=False,
                vad_filter=True,
            )
        )
        assert_true("status confirmed", result["source_status"] == "source_confirmed", failures)
        assert_true("source class", result["source_class"] == "primary_audio_asr", failures)
        assert_true("clean transcript", (output_root / "01_transcript" / "clean_transcript.jsonl").is_file(), failures)
        assert_true("asr report json", (output_root / "00_source" / "asr_pipeline_report.json").is_file(), failures)
        status = read_json(output_root / "00_source" / "source_status.json")
        assert_true("status source class patched", status.get("source_classes") == ["primary_audio_asr"], failures)
        assert_true("status primary true", status.get("primary_material_available") is True, failures)
        report = read_json(output_root / "00_source" / "asr_pipeline_report.json")
        alignment = read_json(output_root / "00_source" / "asr_alignment_report.json")
        diarization = read_json(output_root / "00_source" / "asr_diarization.json")
        assert_true("jsonl engine preserved", report.get("engine") == "faster-whisper", failures, json.dumps(report, ensure_ascii=False))
        assert_true("alignment engine preserved", alignment.get("engine") == "faster-whisper", failures, json.dumps(alignment, ensure_ascii=False))
        assert_true("no words segment only", report["quality"]["alignment_status"] == "segment_only", failures)
        assert_true("no speaker diarization absent", report["quality"]["diarization_status"] == "not_available", failures)
        assert_true("alignment artifact", alignment.get("status") == "segment_only", failures, json.dumps(alignment, ensure_ascii=False))
        assert_true("diarization artifact", diarization.get("status") == "not_available", failures, json.dumps(diarization, ensure_ascii=False))
        assert_true("not verified verbatim", report["quality"]["verified_verbatim"] is False, failures)
        assert_true("validation ok", result["validation"]["valid"] is True, failures, json.dumps(result["validation"], ensure_ascii=False))

        word_jsonl = base / "fixture_words_asr.jsonl"
        word_rows = [
            {
                "id": "t0001",
                "start": 0.0,
                "end": 1.0,
                "text": "Hello world.",
                "source": "ASR",
                "engine": "fixture-asr",
                "model": "base",
                "language": "en",
                "confidence": "medium",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.4, "confidence": 0.9},
                    {"word": "world", "start": 0.5, "end": 0.9, "confidence": 0.88},
                ],
                "alignment": {"engine": "fixture"},
                "diarization": {"engine": "fixture"},
                "raw_index": 0,
            }
        ]
        write_text(word_jsonl, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in word_rows))
        word_output = base / "10_video_words"
        word_result = run_asr_pipeline(
            argparse.Namespace(
                input_media=media,
                output_root=word_output,
                asr_jsonl=word_jsonl,
                asr_python=None,
                model="base",
                language="en",
                device="cpu",
                compute_type="int8",
                timeout_seconds=0.0,
                local_files_only=False,
                vad_filter=True,
            )
        )
        word_report = read_json(word_output / "00_source" / "asr_pipeline_report.json")
        word_alignment = read_json(word_output / "00_source" / "asr_alignment_report.json")
        word_diarization = read_json(word_output / "00_source" / "asr_diarization.json")
        clean_line = json.loads((word_output / "01_transcript" / "clean_transcript.jsonl").read_text(encoding="utf-8-sig").splitlines()[0])
        assert_true("word timestamp coverage", word_result["word_timestamp_coverage"] == 1.0, failures, json.dumps(word_result, ensure_ascii=False))
        assert_true("speaker coverage", word_result["speaker_coverage"] == 1.0, failures, json.dumps(word_result, ensure_ascii=False))
        assert_true("word report aligned", word_report["quality"]["alignment_status"] == "word_aligned", failures)
        assert_true("word alignment artifact", word_alignment["status"] == "word_aligned", failures)
        assert_true("external jsonl engine preserved", word_report.get("engine") == "fixture-asr", failures, json.dumps(word_report, ensure_ascii=False))
        assert_true("external alignment engine preserved", word_alignment.get("engine") == "fixture-asr", failures, json.dumps(word_alignment, ensure_ascii=False))
        assert_true("word diarization artifact", word_diarization["status"] == "speaker_labels_present", failures)
        assert_true("normalizer preserves words", clean_line.get("word_timestamps_available") is True and len(clean_line.get("words") or []) == 2, failures, json.dumps(clean_line, ensure_ascii=False))
        assert_true("normalizer preserves speaker", clean_line.get("speaker") == "SPEAKER_00", failures, json.dumps(clean_line, ensure_ascii=False))

        bad_media = base / "bad.txt"
        bad_media.write_text("not media", encoding="utf-8")
        try:
            run_asr_pipeline(
                argparse.Namespace(
                    input_media=bad_media,
                    output_root=base / "bad_out",
                    asr_jsonl=asr_jsonl,
                    asr_python=None,
                    model="base",
                    language="en",
                    device="cpu",
                    compute_type="int8",
                    timeout_seconds=0.0,
                    local_files_only=False,
                    vad_filter=True,
                )
            )
        except AsrPipelineError:
            pass
        else:
            failures.append("bad media suffix: expected AsrPipelineError")

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

    if args.input_media is None or args.output_root is None:
        parser.error("--input-media and --output-root are required unless --self-test is used")

    try:
        summary = run_asr_pipeline(args)
    except AsrPipelineError as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "error": "asr_pipeline_failed",
                "message": str(exc),
            },
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return 1

    emit_json(summary, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
