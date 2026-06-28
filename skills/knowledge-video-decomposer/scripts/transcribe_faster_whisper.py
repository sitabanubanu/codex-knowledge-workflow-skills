#!/usr/bin/env python
"""Direct faster-whisper transcription fallback for knowledge-video-decomposer."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HEARSAY_VENV_PYTHON = r"C:\Users\Socrates\.codex\tools\hearsay-venv\Scripts\python.exe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe a local audio/video file with faster-whisper.",
    )
    parser.add_argument("input_media", type=Path, help="Path to a local audio or video file.")
    parser.add_argument("output_markdown", type=Path, help="Path for timestamped markdown output.")
    parser.add_argument("output_jsonl", type=Path, help="Path for JSONL segment output.")
    parser.add_argument(
        "--model",
        default="tiny",
        help="faster-whisper model name or local model path. Defaults to tiny.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Optional language code such as en, zh, or ja. Omit for auto-detect.",
    )
    vad_group = parser.add_mutually_exclusive_group()
    vad_group.add_argument(
        "--vad",
        dest="vad_filter",
        action="store_true",
        help="Enable faster-whisper VAD filtering. This is the default.",
    )
    vad_group.add_argument(
        "--no-vad",
        dest="vad_filter",
        action="store_false",
        help="Disable VAD filtering.",
    )
    parser.set_defaults(vad_filter=True)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=0.0,
        help=(
            "Soft timeout in seconds. 0 means no timeout. It is checked when "
            "control returns to this script and may not interrupt model download, "
            "model loading, or an internal transcription call immediately."
        ),
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Device passed to WhisperModel. Defaults to cpu.",
    )
    parser.add_argument(
        "--compute-type",
        default="int8",
        help="Compute type passed to WhisperModel. Defaults to int8.",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Load only cached model files; do not download model files.",
    )
    return parser.parse_args()


def fail(message: str, exit_code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def import_whisper_model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        fail(
            "faster_whisper is not installed for this Python. "
            f"Try running this script with {HEARSAY_VENV_PYTHON}."
        )
        raise exc
    return WhisperModel


def resolve_path_for_comparison(path: Path, *, must_exist: bool = False) -> Path:
    try:
        return path.expanduser().resolve(strict=must_exist)
    except OSError as exc:
        fail(f"could not resolve path {path}: {exc}")
        raise exc


def path_key(path: Path) -> str:
    return os.path.normcase(str(path))


def validate_paths(input_path: Path, markdown_path: Path, jsonl_path: Path) -> tuple[Path, Path, Path]:
    input_media = resolve_path_for_comparison(input_path, must_exist=True)
    output_markdown = resolve_path_for_comparison(markdown_path)
    output_jsonl = resolve_path_for_comparison(jsonl_path)

    if not input_media.is_file():
        fail(f"input media is not a file: {input_media}")

    input_key = path_key(input_media)
    markdown_key = path_key(output_markdown)
    jsonl_key = path_key(output_jsonl)
    if markdown_key == jsonl_key:
        fail(f"output markdown and output JSONL paths must be different: {output_markdown}")
    if markdown_key == input_key:
        fail(f"output markdown path must not equal input media path: {output_markdown}")
    if jsonl_key == input_key:
        fail(f"output JSONL path must not equal input media path: {output_jsonl}")

    return input_media, output_markdown, output_jsonl


def seconds_to_stamp(seconds: float) -> str:
    millis = int(round(max(0.0, seconds) * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def check_timeout(started_at: float, timeout_seconds: float, stage: str) -> None:
    if timeout_seconds <= 0:
        return
    elapsed = time.monotonic() - started_at
    if elapsed > timeout_seconds:
        raise TimeoutError(f"timeout after {elapsed:.1f}s during {stage}")


def write_markdown(path: Path, input_media: Path, model_name: str, language: str, segments: list[dict]) -> None:
    lines = [
        "# Faster Whisper Transcript",
        "",
        f"- source: {input_media}",
        f"- model: {model_name}",
        f"- language: {language or 'unknown'}",
        f"- segments: {len(segments)}",
        "",
    ]
    for segment in segments:
        lines.append(
            f"[{seconds_to_stamp(segment['start'])}-{seconds_to_stamp(segment['end'])}] "
            f"{segment['text']}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_jsonl(path: Path, segments: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for segment in segments:
            handle.write(json.dumps(segment, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    input_media, output_markdown, output_jsonl = validate_paths(
        args.input_media,
        args.output_markdown,
        args.output_jsonl,
    )

    started_at = time.monotonic()
    WhisperModel = import_whisper_model()

    print(
        f"loading faster-whisper model={args.model} device={args.device} compute_type={args.compute_type}",
        file=sys.stderr,
    )
    try:
        model = WhisperModel(
            args.model,
            device=args.device,
            compute_type=args.compute_type,
            local_files_only=args.local_files_only,
        )
        check_timeout(started_at, args.timeout_seconds, "model loading")
    except TimeoutError as exc:
        fail(str(exc), exit_code=124)
    except Exception as exc:
        fail(
            f"could not load model {args.model!r}: {exc}. "
            "Use --local-files-only for cached models or keep --model tiny for the smallest default."
        )

    print(
        f"transcribing input={input_media} language={args.language or 'auto'} vad={args.vad_filter}",
        file=sys.stderr,
    )
    try:
        segment_iter, info = model.transcribe(
            str(input_media),
            language=args.language,
            vad_filter=args.vad_filter,
        )
        detected_language = args.language or getattr(info, "language", None) or ""
        duration = float(getattr(info, "duration", 0.0) or 0.0)
        segments: list[dict] = []
        next_progress_at = 30.0
        for index, segment in enumerate(segment_iter, start=1):
            check_timeout(started_at, args.timeout_seconds, "transcription")
            text = (segment.text or "").strip()
            if not text:
                continue
            start = max(0.0, float(segment.start))
            end = max(start, float(segment.end))
            segments.append(
                {
                    "id": f"t{len(segments) + 1:04d}",
                    "start": start,
                    "end": end,
                    "text": text,
                    "source": "ASR",
                    "engine": "faster-whisper",
                    "model": args.model,
                    "language": detected_language,
                    "confidence": "medium",
                    "raw_index": index - 1,
                }
            )
            if end >= next_progress_at:
                if duration > 0:
                    print(f"progress {min(end, duration):.1f}/{duration:.1f}s", file=sys.stderr)
                else:
                    print(f"progress {end:.1f}s", file=sys.stderr)
                next_progress_at += 30.0
        check_timeout(started_at, args.timeout_seconds, "finalization")
    except TimeoutError as exc:
        fail(str(exc), exit_code=124)
    except Exception as exc:
        fail(f"transcription failed: {exc}")

    write_markdown(output_markdown, input_media, args.model, detected_language, segments)
    write_jsonl(output_jsonl, segments)

    elapsed = time.monotonic() - started_at
    print(
        f"done segments={len(segments)} language={detected_language or 'unknown'} elapsed={elapsed:.1f}s",
        file=sys.stderr,
    )
    print(str(output_markdown))
    print(str(output_jsonl))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
