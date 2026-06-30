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
    durations = [
        max(0.0, float(row["end"]) - float(row["start"]))
        for row in rows
        if isinstance(row.get("start"), (int, float)) and isinstance(row.get("end"), (int, float))
    ]
    return {
        "segments": len(rows),
        "timed_segments": timed,
        "timestamp_coverage": timed / len(rows) if rows else 0.0,
        "total_segment_duration": round(sum(durations), 3),
        "exact_wording_confidence": exact,
        "structural_summary_confidence": structural,
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
        f"- Exact wording confidence: `{quality['exact_wording_confidence']}`",
        f"- Structural summary confidence: `{quality['structural_summary_confidence']}`",
        "",
        "## Limitations",
        "",
    ]
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
            f"- Engine: `faster-whisper`",
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
                "engine": "faster-whisper",
                "model": report["model"],
                "language": report["language"],
                "vad_filter": report["vad_filter"],
                "quality": report["quality"],
            },
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
    quality = quality_from_model(args.model, rows)
    report = {
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "input_media": str(input_media),
        "output_root": str(output_root),
        "asr_jsonl": str(asr_jsonl),
        "asr_markdown": str(asr_markdown),
        "model": args.model,
        "language": args.language,
        "vad_filter": args.vad_filter,
        "runtime": runtime,
        "quality": quality,
        "transcription_result": transcription_result,
        "normalizer_summary": normalizer_summary,
        "next_step": "enter_segmentation_inventory_logic_gap_check",
    }
    patch_source_status(output_root, report)
    append_acquisition_notes(output_root, report)
    written = [
        write_json(output_root / "00_source" / "asr_pipeline_report.json", report),
        write_text(output_root / "00_source" / "asr_pipeline_report.md", render_report(report)),
    ]
    validation = artifact_validator.validate_artifact_root(
        output_root,
        output_root / "00_source" / "source_status.json",
        mode="strict",
    )
    return {
        "runner": RUNNER_NAME,
        "output_root": str(output_root),
        "input_media": str(input_media),
        "source_status": "source_confirmed",
        "source_class": "primary_audio_asr",
        "segments": quality["segments"],
        "timestamp_coverage": quality["timestamp_coverage"],
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
        assert_true("validation ok", result["validation"]["valid"] is True, failures, json.dumps(result["validation"], ensure_ascii=False))

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
