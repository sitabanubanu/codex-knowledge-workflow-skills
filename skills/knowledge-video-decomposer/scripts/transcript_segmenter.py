#!/usr/bin/env python
"""Create syntax and argument segments from normalized transcript artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import artifact_validator
from subtitle_line_breaker import (
    line_width_ok,
    reading_speed_cps,
    sentence_complete,
    split_subtitle_lines,
    subtitle_confidence,
)
from write_artifact import ArtifactWriteError, write_artifact


RUNNER_NAME = "knowledge-video-transcript-segmenter"
ALLOWED_SOURCE_STATUSES = {"source_confirmed", "source_partial"}
ARGUMENT_ROLES = {
    "opening",
    "question",
    "example",
    "definition",
    "claim",
    "contrast",
    "causal_chain",
    "analogy",
    "transition",
    "conclusion",
    "aside",
}
CJK_SENTENCE_ENDINGS = ("\u3002", "\uff1f", "\uff01", ".", "?", "!")
CJK_SENTENCE_SPLIT_RE = r"[\u3002\uff01\uff1f.!?]\s*"
QUESTION_TOKENS = ["why", "how", "what", "\u4e3a\u4ec0\u4e48", "\u5982\u4f55", "\u4ec0\u4e48"]
EXAMPLE_TOKENS = ["for example", "\u6bd4\u5982", "\u4f8b\u5982", "\u4e3e\u4e2a\u4f8b\u5b50", "case"]
DEFINITION_TOKENS = ["means", "defined", "definition", "\u6240\u8c13", "\u5b9a\u4e49", "\u610f\u601d\u662f"]
ANALOGY_TOKENS = ["like", "as if", "\u597d\u50cf", "\u5c31\u50cf", "\u7c7b\u6bd4"]
CONTRAST_TOKENS = [
    "however",
    "but",
    "on the other hand",
    "\u4f46\u662f",
    "\u7136\u800c",
    "\u53cd\u8fc7\u6765",
    "\u76f8\u53cd",
]
CAUSAL_TOKENS = [
    "because",
    "therefore",
    "so",
    "leads to",
    "causes",
    "as a result",
    "\u56e0\u4e3a",
    "\u6240\u4ee5",
    "\u56e0\u6b64",
    "\u5bfc\u81f4",
]
TRANSITION_TOKENS = [
    "next",
    "then",
    "finally",
    "first",
    "second",
    "\u7136\u540e",
    "\u63a5\u4e0b\u6765",
    "\u6700\u540e",
    "\u9996\u5148",
]
CLAIM_TOKENS = [
    "i think",
    "we should",
    "must",
    "\u6211\u8ba4\u4e3a",
    "\u5e94\u8be5",
    "\u5fc5\u987b",
    "\u7ed3\u8bba",
]


class TranscriptSegmenterError(Exception):
    """Expected CLI-facing segmentation failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def write_json(path: Path, payload: Any, *, pretty: bool = True) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None)
    return write_artifact(path, text, json_mode=True, mkdirs=True, overwrite=True)


def write_text(path: Path, text: str) -> dict[str, Any]:
    return write_artifact(path, text, mkdirs=True, overwrite=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise TranscriptSegmenterError(f"invalid JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise TranscriptSegmenterError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TranscriptSegmenterError(f"JSON file is not an object: {path}")
    return payload


def load_source_status(path: Path) -> dict[str, Any]:
    status = read_json(path)
    source_status = status.get("source_status")
    if source_status not in ALLOWED_SOURCE_STATUSES:
        raise TranscriptSegmenterError(
            f"segmentation requires source_confirmed or source_partial; got {source_status!r}"
        )
    if not status.get("primary_material_available"):
        raise TranscriptSegmenterError("segmentation requires primary_material_available=true")
    return status


def load_transcript(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise TranscriptSegmenterError(f"clean transcript not found: {path}")
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise TranscriptSegmenterError(f"could not read clean transcript: {exc}") from exc
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TranscriptSegmenterError(f"invalid clean transcript JSONL line {line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise TranscriptSegmenterError(f"clean transcript line {line_no} is not an object")
        row_id = str(row.get("id") or "").strip()
        text = str(row.get("normalized_text") or row.get("text") or "").strip()
        if not row_id or not text:
            raise TranscriptSegmenterError(f"clean transcript line {line_no} is missing id or text")
        rows.append(row)
    if not rows:
        raise TranscriptSegmenterError("clean transcript contains no usable rows")
    return rows


def numeric_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def row_text(row: dict[str, Any]) -> str:
    return re.sub(r"\s+", " ", str(row.get("normalized_text") or row.get("text") or "")).strip()


def row_chapter_key(row: dict[str, Any]) -> str:
    for key in ("chapter_id", "chapter", "chapter_title", "section"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def make_evidence_span(rows: list[dict[str, Any]]) -> dict[str, Any]:
    texts = [row_text(row) for row in rows if row_text(row)]
    quote = " ".join(texts)
    if len(quote) > 180:
        quote = quote[:177].rstrip() + "..."
    starts = [numeric_or_none(row.get("start")) for row in rows]
    ends = [numeric_or_none(row.get("end")) for row in rows]
    starts = [value for value in starts if value is not None]
    ends = [value for value in ends if value is not None]
    return {
        "transcript_ids": [str(row["id"]) for row in rows],
        "start": min(starts) if starts else None,
        "end": max(ends) if ends else None,
        "quote": quote,
        "source": "clean_transcript",
    }


def should_split(
    current_rows: list[dict[str, Any]],
    next_row: dict[str, Any],
    *,
    max_chars: int,
    max_seconds: float,
    gap_seconds: float,
) -> tuple[bool, str]:
    if not current_rows:
        return False, ""
    current_text = " ".join(row_text(row) for row in current_rows)
    next_text = row_text(next_row)
    if len(current_text) + len(next_text) > max_chars:
        return True, "length_limit"
    current_chapter = row_chapter_key(current_rows[-1])
    next_chapter = row_chapter_key(next_row)
    if current_chapter and next_chapter and current_chapter != next_chapter:
        return True, "chapter_boundary"
    first_start = numeric_or_none(current_rows[0].get("start"))
    last_end = numeric_or_none(current_rows[-1].get("end"))
    next_start = numeric_or_none(next_row.get("start"))
    if first_start is not None and last_end is not None and last_end - first_start >= max_seconds:
        return True, "length_limit"
    if last_end is not None and next_start is not None and next_start - last_end >= gap_seconds:
        return True, "pause"
    if current_text.rstrip().endswith(CJK_SENTENCE_ENDINGS) and len(current_text) >= max_chars * 0.55:
        return True, "sentence_boundary"
    return False, ""


def build_subtitle_segments(
    rows: list[dict[str, Any]],
    *,
    max_line_chars: int,
    max_lines: int,
    max_reading_cps: float,
    gap_seconds: float,
) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    previous_end: float | None = None
    previous_chapter = ""
    for index, row in enumerate(rows, start=1):
        text = row_text(row)
        lines = split_subtitle_lines(text, max_line_chars=max_line_chars, max_lines=max_lines)
        start = numeric_or_none(row.get("start"))
        end = numeric_or_none(row.get("end"))
        cps = reading_speed_cps(text, start, end)
        complete = sentence_complete(text)
        chapter = row_chapter_key(row)
        issues: list[str] = []
        if start is None or end is None:
            issues.append("missing_timestamp")
        elif end <= start:
            issues.append("invalid_timestamp_range")
        if previous_end is not None and start is not None:
            if start < previous_end:
                issues.append("timestamp_overlap")
            elif start - previous_end >= gap_seconds:
                issues.append("timestamp_gap_before")
        if previous_chapter and chapter and chapter != previous_chapter:
            issues.append("chapter_boundary")
        if not line_width_ok(lines, max_line_chars=max_line_chars):
            issues.append("line_width_exceeded")
        if len(lines) > max_lines:
            issues.append("line_count_exceeded")
        if cps is not None and cps > max_reading_cps:
            issues.append("reading_speed_high")
        if not complete:
            issues.append("sentence_incomplete")
        confidence = subtitle_confidence(
            issues=issues,
            has_timing=start is not None and end is not None and end > start,
            sentence_is_complete=complete,
        )
        segments.append(
            {
                "id": f"seg_subtitle_{index:03d}",
                "start": start,
                "end": end,
                "text": text,
                "lines": lines,
                "transcript_ids": [str(row["id"])],
                "source_transcript_ids": [str(row["id"])],
                "line_width_chars": max((len(line) for line in lines), default=0),
                "max_line_chars": max_line_chars,
                "reading_speed_cps": cps,
                "timestamp_continuity": "missing" if "missing_timestamp" in issues else "overlap" if "timestamp_overlap" in issues else "gap_before" if "timestamp_gap_before" in issues else "continuous",
                "sentence_complete": complete,
                "chapter": chapter,
                "issues": issues,
                "segmentation_confidence": confidence,
            }
        )
        if end is not None:
            previous_end = end
        if chapter:
            previous_chapter = chapter
    return segments


def build_syntax_segments(
    rows: list[dict[str, Any]],
    *,
    max_chars: int,
    max_seconds: float,
    gap_seconds: float,
) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    split_reason = "manual"
    for row in rows:
        split, reason = should_split(
            current,
            row,
            max_chars=max_chars,
            max_seconds=max_seconds,
            gap_seconds=gap_seconds,
        )
        if split and current:
            segments.append(make_syntax_segment(len(segments) + 1, current, split_reason or reason))
            current = []
            split_reason = reason
        current.append(row)
        if not split_reason:
            split_reason = reason
    if current:
        segments.append(make_syntax_segment(len(segments) + 1, current, split_reason or "manual"))
    return segments


def make_syntax_segment(index: int, rows: list[dict[str, Any]], split_reason: str) -> dict[str, Any]:
    span = make_evidence_span(rows)
    return {
        "id": f"seg_syntax_{index:03d}",
        "start": span["start"],
        "end": span["end"],
        "text": " ".join(row_text(row) for row in rows),
        "transcript_ids": span["transcript_ids"],
        "split_reason": split_reason,
    }


def contains_marker(text: str, tokens: list[str]) -> bool:
    for token in tokens:
        if any(ord(ch) > 127 for ch in token):
            if token in text:
                return True
            continue
        if re.search(rf"\b{re.escape(token)}\b", text):
            return True
    return False


def classify_role(text: str, index: int, total: int) -> str:
    lowered = text.lower()
    if "?" in text or "\uff1f" in text or contains_marker(lowered, QUESTION_TOKENS):
        return "question"
    if contains_marker(lowered, EXAMPLE_TOKENS):
        return "example"
    if contains_marker(lowered, CONTRAST_TOKENS):
        return "contrast"
    if contains_marker(lowered, CAUSAL_TOKENS):
        return "causal_chain"
    if contains_marker(lowered, DEFINITION_TOKENS):
        return "definition"
    if contains_marker(lowered, ANALOGY_TOKENS):
        return "analogy"
    if contains_marker(lowered, TRANSITION_TOKENS):
        return "transition"
    if contains_marker(lowered, CLAIM_TOKENS):
        return "claim"
    if index == 1:
        return "opening"
    if index == total:
        return "conclusion"
    return "claim"


def title_for(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Untitled segment"
    sentence = re.split(CJK_SENTENCE_SPLIT_RE, text, maxsplit=1)[0].strip()
    if len(sentence) > 64:
        return sentence[:61].rstrip() + "..."
    return sentence


def build_argument_segments(
    syntax_segments: list[dict[str, Any]],
    subtitle_segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    total = len(syntax_segments)
    subtitle_by_transcript_id: dict[str, str] = {}
    for subtitle in subtitle_segments:
        subtitle_id = str(subtitle.get("id") or "")
        for transcript_id in subtitle.get("transcript_ids") or []:
            subtitle_by_transcript_id[str(transcript_id)] = subtitle_id
    for index, syntax in enumerate(syntax_segments, start=1):
        text = str(syntax.get("text") or "")
        transcript_ids = list(syntax.get("transcript_ids") or [])
        span = {
            "transcript_ids": transcript_ids,
            "start": syntax.get("start"),
            "end": syntax.get("end"),
            "quote": text[:177].rstrip() + "..." if len(text) > 180 else text,
            "source": "clean_transcript",
        }
        role = classify_role(text, index, total)
        if role not in ARGUMENT_ROLES:
            role = "claim"
        segments.append(
            {
                "id": f"seg_argument_{index:03d}",
                "start": syntax.get("start"),
                "end": syntax.get("end"),
                "role": role,
                "title": title_for(text),
                "summary": (
                    "Heuristic argument segment derived from transcript continuity. "
                    "Requires later inventory and source-logic review."
                ),
                "transcript_ids": transcript_ids,
                "evidence_spans": [span],
                "source_syntax_segment_ids": [syntax["id"]],
                "source_subtitle_segment_ids": sorted(
                    {
                        subtitle_by_transcript_id[transcript_id]
                        for transcript_id in transcript_ids
                        if transcript_id in subtitle_by_transcript_id
                    }
                ),
                "segmentation_confidence": "medium",
            }
        )
    return segments


def confidence_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for item in items:
        confidence = str(item.get("segmentation_confidence") or "low")
        if confidence not in counts:
            confidence = "low"
        counts[confidence] += 1
    return counts


def overall_segmentation_confidence(
    *,
    timestamp_coverage: float,
    subtitle_segments: list[dict[str, Any]],
    argument_segments: list[dict[str, Any]],
) -> str:
    subtitle_counts = confidence_counts(subtitle_segments)
    low_share = subtitle_counts["low"] / len(subtitle_segments) if subtitle_segments else 1.0
    if not argument_segments or timestamp_coverage < 0.5 or low_share > 0.35:
        return "low"
    if timestamp_coverage < 0.8 or low_share > 0.0:
        return "medium"
    return "high"


def render_segmentation_gap(
    *,
    status: dict[str, Any],
    transcript_rows: list[dict[str, Any]],
    subtitle_segments: list[dict[str, Any]],
    syntax_segments: list[dict[str, Any]],
    argument_segments: list[dict[str, Any]],
) -> str:
    timed_rows = [
        row
        for row in transcript_rows
        if numeric_or_none(row.get("start")) is not None and numeric_or_none(row.get("end")) is not None
    ]
    coverage = len(timed_rows) / len(transcript_rows) if transcript_rows else 0.0
    subtitle_counts = confidence_counts(subtitle_segments)
    argument_counts = confidence_counts(argument_segments)
    overall_confidence = overall_segmentation_confidence(
        timestamp_coverage=coverage,
        subtitle_segments=subtitle_segments,
        argument_segments=argument_segments,
    )
    return "\n".join(
        [
            "# Segmentation Gap Check",
            "",
            "## Segmentation Status",
            "",
            f"- Source status: `{status.get('source_status')}`",
            f"- Transcript rows: `{len(transcript_rows)}`",
            f"- Subtitle segments: `{len(subtitle_segments)}`",
            f"- Syntax segments: `{len(syntax_segments)}`",
            f"- Argument segments: `{len(argument_segments)}`",
            f"- Timestamp coverage: `{coverage:.3f}`",
            f"- Overall segmentation confidence: `{overall_confidence}`",
            f"- Subtitle confidence counts: `{json.dumps(subtitle_counts, ensure_ascii=False)}`",
            f"- Argument confidence counts: `{json.dumps(argument_counts, ensure_ascii=False)}`",
            "",
            "## Remaining Limits",
            "",
            "- Subtitle segments optimize reading display and timing continuity; they are not claims or argument moves.",
            "- Argument roles are heuristic labels, not final source-logic reconstruction.",
            "- Claims, concepts, examples, analogies, and logic graph have not been extracted yet.",
            "- Do not write `video_analysis_pack.md` until inventory and source logic stages are complete.",
            "",
            "## Next Step",
            "",
            "- Run the inventory extraction stage over `02_segments/argument_segments.json` and `01_transcript/clean_transcript.jsonl`.",
            "",
        ]
    )


def run_segmentation(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.expanduser().resolve()
    source_status_path = args.source_status or output_root / "00_source" / "source_status.json"
    transcript_path = args.transcript or output_root / "01_transcript" / "clean_transcript.jsonl"

    status = load_source_status(source_status_path)
    rows = load_transcript(transcript_path)
    subtitle_max_line_chars = int(getattr(args, "subtitle_max_line_chars", 42))
    subtitle_max_lines = int(getattr(args, "subtitle_max_lines", 2))
    subtitle_max_reading_cps = float(getattr(args, "subtitle_max_reading_cps", 20.0))
    subtitle_segments = build_subtitle_segments(
        rows,
        max_line_chars=subtitle_max_line_chars,
        max_lines=subtitle_max_lines,
        max_reading_cps=subtitle_max_reading_cps,
        gap_seconds=args.gap_seconds,
    )
    syntax_segments = build_syntax_segments(
        rows,
        max_chars=args.max_chars,
        max_seconds=args.max_seconds,
        gap_seconds=args.gap_seconds,
    )
    argument_segments = build_argument_segments(syntax_segments, subtitle_segments)

    written = [
        write_json(
            output_root / "02_segments" / "subtitle_segments.json",
            {
                "runner": RUNNER_NAME,
                "generated_at": now_iso(),
                "source_transcript": str(transcript_path.resolve()),
                "line_policy": {
                    "max_line_chars": subtitle_max_line_chars,
                    "max_lines": subtitle_max_lines,
                    "max_reading_cps": subtitle_max_reading_cps,
                },
                "segments": subtitle_segments,
                "notes": "Subtitle-layer segmentation for display/readability. Do not treat these as argument or claim segments.",
            },
            pretty=True,
        ),
        write_json(
            output_root / "02_segments" / "syntax_segments.json",
            {
                "runner": RUNNER_NAME,
                "generated_at": now_iso(),
                "source_transcript": str(transcript_path.resolve()),
                "segments": syntax_segments,
            },
            pretty=True,
        ),
        write_json(
            output_root / "02_segments" / "argument_segments.json",
            {
                "runner": RUNNER_NAME,
                "generated_at": now_iso(),
                "source_transcript": str(transcript_path.resolve()),
                "segments": argument_segments,
                "notes": "Heuristic argument segmentation. Inventory and source-logic stages must verify roles and evidence.",
            },
            pretty=True,
        ),
        write_text(
            output_root / "05_gap_check" / "segmentation_gap_check.md",
            render_segmentation_gap(
                status=status,
                transcript_rows=rows,
                subtitle_segments=subtitle_segments,
                syntax_segments=syntax_segments,
                argument_segments=argument_segments,
            ),
        ),
    ]
    validation = artifact_validator.validate_artifact_root(
        output_root,
        source_status_path,
        mode="strict",
    )
    return {
        "runner": RUNNER_NAME,
        "output_root": str(output_root),
        "source_status": status.get("source_status"),
        "subtitle_segments": len(subtitle_segments),
        "syntax_segments": len(syntax_segments),
        "argument_segments": len(argument_segments),
        "files_written": [item["path"] for item in written],
        "validation": validation,
        "next_step": "enter_inventory_extraction",
        "validation_next_step": validation.get("next_step"),
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Segment normalized transcript artifacts.")
    parser.add_argument("--output-root", type=Path, required=False, help="Artifact root containing 00_source and 01_transcript.")
    parser.add_argument("--source-status", type=Path, default=None, help="Optional source_status.json override.")
    parser.add_argument("--transcript", type=Path, default=None, help="Optional clean_transcript.jsonl override.")
    parser.add_argument("--max-chars", type=int, default=1200, help="Target maximum characters per syntax segment.")
    parser.add_argument("--max-seconds", type=float, default=180.0, help="Target maximum seconds per timed syntax segment.")
    parser.add_argument("--gap-seconds", type=float, default=8.0, help="Timestamp gap that triggers a split.")
    parser.add_argument("--subtitle-max-line-chars", type=int, default=42, help="Maximum characters per subtitle display line.")
    parser.add_argument("--subtitle-max-lines", type=int, default=2, help="Preferred maximum subtitle display lines per transcript row.")
    parser.add_argument("--subtitle-max-reading-cps", type=float, default=20.0, help="Reading-speed warning threshold in characters per second.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def write_status(path: Path, *, source_status: str = "source_confirmed", primary: bool = True) -> None:
    if source_status == "source_confirmed":
        allowed_report_type = "full_video_analysis_pack"
    elif source_status == "source_partial":
        allowed_report_type = "partial_video_analysis_pack"
    else:
        allowed_report_type = "degraded_source_report"
    payload = {
        "source_status": source_status,
        "can_enter_full_decomposition": source_status in ALLOWED_SOURCE_STATUSES,
        "can_enter_document_composer": True,
        "allowed_report_type": allowed_report_type,
        "source_classes": ["primary_transcript"] if primary else [],
        "primary_material_available": primary,
        "status_reason": "self-test status",
        "failed_probes": [],
        "next_step": "enter_segmentation_inventory_logic_gap_check",
    }
    write_json(path, payload)


def write_clean_transcript(path: Path, rows: list[dict[str, Any]]) -> None:
    text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    write_text(path, text)


def test_rows() -> list[dict[str, Any]]:
    question = "\u4eca\u5929\u6211\u4eec\u5148\u63d0\u51fa\u4e00\u4e2a\u95ee\u9898\uff1a\u4e3a\u4ec0\u4e48\u77e5\u8bc6\u89c6\u9891\u4e0d\u80fd\u76f4\u63a5\u603b\u7ed3\uff1f"
    example = "\u6bd4\u5982\uff0c\u5982\u679c\u6ca1\u6709 transcript\uff0c\u5c31\u65e0\u6cd5\u6838\u9a8c speaker \u7684\u771f\u5b9e\u8868\u8fbe\u3002"
    transition = "\u6240\u4ee5\u6211\u4eec\u5fc5\u987b\u5148\u83b7\u5f97\u4e00\u624b\u6750\u6599\uff0c\u7136\u540e\u518d\u505a\u7ed3\u6784\u5316\u5206\u6790\u3002"
    return [
        {
            "id": "t0001",
            "start": 0.0,
            "end": 4.0,
            "text": question,
            "normalized_text": question,
            "source_ids": ["raw_0001"],
            "language": "zh",
            "speaker": "",
            "confidence": "high",
        },
        {
            "id": "t0002",
            "start": 5.0,
            "end": 10.0,
            "text": example,
            "normalized_text": example,
            "source_ids": ["raw_0002"],
            "language": "zh",
            "speaker": "",
            "confidence": "high",
        },
        {
            "id": "t0003",
            "start": 20.0,
            "end": 24.0,
            "text": transition,
            "normalized_text": transition,
            "source_ids": ["raw_0003"],
            "language": "zh",
            "speaker": "",
            "confidence": "high",
        },
    ]


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="transcript-segmenter-") as tmp:
        base = Path(tmp)
        root = base / "confirmed"
        write_status(root / "00_source" / "source_status.json")
        write_clean_transcript(root / "01_transcript" / "clean_transcript.jsonl", test_rows())
        result = run_segmentation(
            argparse.Namespace(
                output_root=root,
                source_status=None,
                transcript=None,
                max_chars=80,
                max_seconds=180.0,
                gap_seconds=8.0,
                pretty=False,
                self_test=False,
            )
        )
        assert_true("confirmed validates", result["validation"]["valid"] is True, failures, json.dumps(result["validation"], ensure_ascii=False))
        assert_true("writes subtitles", (root / "02_segments" / "subtitle_segments.json").is_file(), failures)
        assert_true("writes syntax", (root / "02_segments" / "syntax_segments.json").is_file(), failures)
        assert_true("writes arguments", (root / "02_segments" / "argument_segments.json").is_file(), failures)
        assert_true("no inventory", not (root / "03_inventory").exists(), failures)
        assert_true("no logic", not (root / "04_logic").exists(), failures)
        assert_true("no pack", not (root / "video_analysis_pack.md").exists(), failures)
        subtitles = read_json(root / "02_segments" / "subtitle_segments.json")
        assert_true("subtitle count", len(subtitles["segments"]) == len(test_rows()), failures)
        assert_true(
            "subtitle line width tracked",
            all("line_width_chars" in segment and "reading_speed_cps" in segment for segment in subtitles["segments"]),
            failures,
        )
        arguments = read_json(root / "02_segments" / "argument_segments.json")
        roles = {segment["role"] for segment in arguments["segments"]}
        assert_true("argument roles valid", roles.issubset(ARGUMENT_ROLES), failures, str(roles))
        assert_true("semantic roles include causal", "causal_chain" in roles, failures, str(roles))
        gap_check = (root / "05_gap_check" / "segmentation_gap_check.md").read_text(encoding="utf-8")
        assert_true("gap confidence", "Overall segmentation confidence" in gap_check, failures)

        english = base / "english"
        write_status(english / "00_source" / "source_status.json")
        write_clean_transcript(
            english / "01_transcript" / "clean_transcript.jsonl",
            [
                {
                    "id": "t0001",
                    "start": 0.0,
                    "end": 3.0,
                    "text": "The first claim is that metadata is not enough.",
                    "normalized_text": "The first claim is that metadata is not enough.",
                    "source_ids": ["raw_0001"],
                    "language": "en",
                },
                {
                    "id": "t0002",
                    "start": 3.2,
                    "end": 6.5,
                    "text": "However, a transcript lets us verify the argument.",
                    "normalized_text": "However, a transcript lets us verify the argument.",
                    "source_ids": ["raw_0002"],
                    "language": "en",
                },
                {
                    "id": "t0003",
                    "start": 6.8,
                    "end": 9.0,
                    "text": "Next, we map examples to claims.",
                    "normalized_text": "Next, we map examples to claims.",
                    "source_ids": ["raw_0003"],
                    "language": "en",
                },
            ],
        )
        run_segmentation(
            argparse.Namespace(
                output_root=english,
                source_status=None,
                transcript=None,
                max_chars=70,
                max_seconds=180.0,
                gap_seconds=8.0,
                subtitle_max_line_chars=42,
                subtitle_max_lines=2,
                subtitle_max_reading_cps=20.0,
                pretty=False,
                self_test=False,
            )
        )
        english_roles = {segment["role"] for segment in read_json(english / "02_segments" / "argument_segments.json")["segments"]}
        assert_true("english contrast role", "contrast" in english_roles, failures, str(english_roles))

        long_sentence = base / "long_sentence"
        write_status(long_sentence / "00_source" / "source_status.json")
        long_text = "This is a very long subtitle line without a clean sentence ending and it should be split for readable subtitle display even before semantic analysis"
        write_clean_transcript(
            long_sentence / "01_transcript" / "clean_transcript.jsonl",
            [{"id": "t0001", "start": 0.0, "end": 2.0, "text": long_text, "normalized_text": long_text}],
        )
        run_segmentation(
            argparse.Namespace(
                output_root=long_sentence,
                source_status=None,
                transcript=None,
                max_chars=200,
                max_seconds=180.0,
                gap_seconds=8.0,
                subtitle_max_line_chars=24,
                subtitle_max_lines=2,
                subtitle_max_reading_cps=20.0,
                pretty=False,
                self_test=False,
            )
        )
        long_subtitle = read_json(long_sentence / "02_segments" / "subtitle_segments.json")["segments"][0]
        assert_true("long sentence split", len(long_subtitle["lines"]) > 1, failures, json.dumps(long_subtitle, ensure_ascii=False))
        assert_true("long sentence flagged", "sentence_incomplete" in long_subtitle["issues"], failures, json.dumps(long_subtitle, ensure_ascii=False))

        missing_time = base / "missing_time"
        write_status(missing_time / "00_source" / "source_status.json")
        write_clean_transcript(
            missing_time / "01_transcript" / "clean_transcript.jsonl",
            [{"id": "t0001", "text": "A transcript row without timestamps.", "normalized_text": "A transcript row without timestamps."}],
        )
        run_segmentation(
            argparse.Namespace(
                output_root=missing_time,
                source_status=None,
                transcript=None,
                max_chars=200,
                max_seconds=180.0,
                gap_seconds=8.0,
                subtitle_max_line_chars=42,
                subtitle_max_lines=2,
                subtitle_max_reading_cps=20.0,
                pretty=False,
                self_test=False,
            )
        )
        missing_subtitle = read_json(missing_time / "02_segments" / "subtitle_segments.json")["segments"][0]
        assert_true("missing timestamp flagged", "missing_timestamp" in missing_subtitle["issues"], failures, json.dumps(missing_subtitle, ensure_ascii=False))

        chaptered = base / "chaptered"
        write_status(chaptered / "00_source" / "source_status.json")
        write_clean_transcript(
            chaptered / "01_transcript" / "clean_transcript.jsonl",
            [
                {"id": "t0001", "start": 0.0, "end": 4.0, "text": "Chapter one setup.", "normalized_text": "Chapter one setup.", "chapter": "one"},
                {"id": "t0002", "start": 4.1, "end": 8.0, "text": "Chapter two claim.", "normalized_text": "Chapter two claim.", "chapter": "two"},
            ],
        )
        run_segmentation(
            argparse.Namespace(
                output_root=chaptered,
                source_status=None,
                transcript=None,
                max_chars=500,
                max_seconds=180.0,
                gap_seconds=8.0,
                subtitle_max_line_chars=42,
                subtitle_max_lines=2,
                subtitle_max_reading_cps=20.0,
                pretty=False,
                self_test=False,
            )
        )
        chapter_syntax = read_json(chaptered / "02_segments" / "syntax_segments.json")["segments"]
        chapter_subtitle = read_json(chaptered / "02_segments" / "subtitle_segments.json")["segments"][1]
        assert_true("chapter boundary syntax split", len(chapter_syntax) == 2 and chapter_syntax[1]["split_reason"] == "chapter_boundary", failures, json.dumps(chapter_syntax, ensure_ascii=False))
        assert_true("chapter boundary subtitle flagged", "chapter_boundary" in chapter_subtitle["issues"], failures, json.dumps(chapter_subtitle, ensure_ascii=False))

        blocked = base / "blocked"
        write_status(blocked / "00_source" / "source_status.json", source_status="secondary_only", primary=False)
        write_clean_transcript(blocked / "01_transcript" / "clean_transcript.jsonl", test_rows())
        blocked_failed = False
        try:
            run_segmentation(
                argparse.Namespace(
                    output_root=blocked,
                    source_status=None,
                    transcript=None,
                    max_chars=80,
                    max_seconds=180.0,
                    gap_seconds=8.0,
                    pretty=False,
                    self_test=False,
                )
            )
        except TranscriptSegmenterError:
            blocked_failed = True
        assert_true("blocked status fails", blocked_failed, failures)
        assert_true("blocked creates no 02", not (blocked / "02_segments").exists(), failures)

        bad = base / "bad_transcript"
        write_status(bad / "00_source" / "source_status.json")
        write_text(bad / "01_transcript" / "clean_transcript.jsonl", '{"id":"t0001","text":""}\n')
        bad_failed = False
        try:
            run_segmentation(
                argparse.Namespace(
                    output_root=bad,
                    source_status=None,
                    transcript=None,
                    max_chars=80,
                    max_seconds=180.0,
                    gap_seconds=8.0,
                    pretty=False,
                    self_test=False,
                )
            )
        except TranscriptSegmenterError:
            bad_failed = True
        assert_true("bad transcript fails", bad_failed, failures)

        partial = base / "partial"
        write_status(partial / "00_source" / "source_status.json", source_status="source_partial", primary=True)
        write_clean_transcript(partial / "01_transcript" / "clean_transcript.jsonl", test_rows())
        partial_result = run_segmentation(
            argparse.Namespace(
                output_root=partial,
                source_status=None,
                transcript=None,
                max_chars=80,
                max_seconds=180.0,
                gap_seconds=8.0,
                pretty=False,
                self_test=False,
            )
        )
        assert_true("partial primary runs", partial_result["source_status"] == "source_partial", failures)
        assert_true("partial writes segments", (partial / "02_segments" / "argument_segments.json").is_file(), failures)

        confirmed_no_primary = base / "confirmed_no_primary"
        write_status(
            confirmed_no_primary / "00_source" / "source_status.json",
            source_status="source_confirmed",
            primary=False,
        )
        write_clean_transcript(confirmed_no_primary / "01_transcript" / "clean_transcript.jsonl", test_rows())
        confirmed_no_primary_failed = False
        try:
            run_segmentation(
                argparse.Namespace(
                    output_root=confirmed_no_primary,
                    source_status=None,
                    transcript=None,
                    max_chars=80,
                    max_seconds=180.0,
                    gap_seconds=8.0,
                    pretty=False,
                    self_test=False,
                )
            )
        except TranscriptSegmenterError:
            confirmed_no_primary_failed = True
        assert_true("confirmed without primary fails", confirmed_no_primary_failed, failures)
        assert_true("confirmed without primary creates no 02", not (confirmed_no_primary / "02_segments").exists(), failures)

        secondary_with_primary = base / "secondary_with_primary"
        write_status(
            secondary_with_primary / "00_source" / "source_status.json",
            source_status="secondary_only",
            primary=True,
        )
        write_clean_transcript(secondary_with_primary / "01_transcript" / "clean_transcript.jsonl", test_rows())
        secondary_with_primary_failed = False
        try:
            run_segmentation(
                argparse.Namespace(
                    output_root=secondary_with_primary,
                    source_status=None,
                    transcript=None,
                    max_chars=80,
                    max_seconds=180.0,
                    gap_seconds=8.0,
                    pretty=False,
                    self_test=False,
                )
            )
        except TranscriptSegmenterError:
            secondary_with_primary_failed = True
        assert_true("secondary with primary fails", secondary_with_primary_failed, failures)
        assert_true("secondary with primary creates no 02", not (secondary_with_primary / "02_segments").exists(), failures)

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
    if args.output_root is None:
        parser.error("--output-root is required unless --self-test is used")
    if args.max_chars <= 0:
        parser.error("--max-chars must be > 0")
    if args.max_seconds <= 0:
        parser.error("--max-seconds must be > 0")
    if args.gap_seconds < 0:
        parser.error("--gap-seconds must be >= 0")
    if args.subtitle_max_line_chars <= 0:
        parser.error("--subtitle-max-line-chars must be > 0")
    if args.subtitle_max_lines <= 0:
        parser.error("--subtitle-max-lines must be > 0")
    if args.subtitle_max_reading_cps <= 0:
        parser.error("--subtitle-max-reading-cps must be > 0")
    try:
        summary = run_segmentation(args)
    except (TranscriptSegmenterError, ArtifactWriteError, OSError) as exc:
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
