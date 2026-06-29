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
from write_artifact import ArtifactWriteError, write_artifact


RUNNER_NAME = "knowledge-video-transcript-segmenter"
ALLOWED_SOURCE_STATUSES = {"source_confirmed", "source_partial"}
ARGUMENT_ROLES = {
    "opening",
    "question",
    "example",
    "definition",
    "claim",
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
TRANSITION_TOKENS = [
    "however",
    "but",
    "therefore",
    "so",
    "\u4f46\u662f",
    "\u7136\u800c",
    "\u6240\u4ee5",
    "\u56e0\u6b64",
    "\u63a5\u4e0b\u6765",
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


def classify_role(text: str, index: int, total: int) -> str:
    lowered = text.lower()
    if index == 1:
        return "opening"
    if index == total:
        return "conclusion"
    if "?" in text or "\uff1f" in text or any(token in lowered for token in QUESTION_TOKENS):
        return "question"
    if any(token in lowered for token in EXAMPLE_TOKENS):
        return "example"
    if any(token in lowered for token in DEFINITION_TOKENS):
        return "definition"
    if any(token in lowered for token in ANALOGY_TOKENS):
        return "analogy"
    if any(token in lowered for token in TRANSITION_TOKENS):
        return "transition"
    if any(token in lowered for token in CLAIM_TOKENS):
        return "claim"
    return "claim"


def title_for(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "Untitled segment"
    sentence = re.split(CJK_SENTENCE_SPLIT_RE, text, maxsplit=1)[0].strip()
    if len(sentence) > 64:
        return sentence[:61].rstrip() + "..."
    return sentence


def build_argument_segments(syntax_segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    total = len(syntax_segments)
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
            }
        )
    return segments


def render_segmentation_gap(
    *,
    status: dict[str, Any],
    transcript_rows: list[dict[str, Any]],
    syntax_segments: list[dict[str, Any]],
    argument_segments: list[dict[str, Any]],
) -> str:
    timed_rows = [
        row
        for row in transcript_rows
        if numeric_or_none(row.get("start")) is not None and numeric_or_none(row.get("end")) is not None
    ]
    coverage = len(timed_rows) / len(transcript_rows) if transcript_rows else 0.0
    return "\n".join(
        [
            "# Segmentation Gap Check",
            "",
            "## Segmentation Status",
            "",
            f"- Source status: `{status.get('source_status')}`",
            f"- Transcript rows: `{len(transcript_rows)}`",
            f"- Syntax segments: `{len(syntax_segments)}`",
            f"- Argument segments: `{len(argument_segments)}`",
            f"- Timestamp coverage: `{coverage:.3f}`",
            "",
            "## Remaining Limits",
            "",
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
    syntax_segments = build_syntax_segments(
        rows,
        max_chars=args.max_chars,
        max_seconds=args.max_seconds,
        gap_seconds=args.gap_seconds,
    )
    argument_segments = build_argument_segments(syntax_segments)

    written = [
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
    return [
        {
            "id": "t0001",
            "start": 0.0,
            "end": 4.0,
            "text": "今天我们先提出一个问题：为什么知识视频不能直接总结？",
            "normalized_text": "今天我们先提出一个问题：为什么知识视频不能直接总结？",
            "source_ids": ["raw_0001"],
            "language": "zh",
            "speaker": "",
            "confidence": "high",
        },
        {
            "id": "t0002",
            "start": 5.0,
            "end": 10.0,
            "text": "比如，如果没有 transcript，就无法核验 speaker 的真实表达。",
            "normalized_text": "比如，如果没有 transcript，就无法核验 speaker 的真实表达。",
            "source_ids": ["raw_0002"],
            "language": "zh",
            "speaker": "",
            "confidence": "high",
        },
        {
            "id": "t0003",
            "start": 20.0,
            "end": 24.0,
            "text": "所以我们必须先获得一手材料，然后再做结构化分析。",
            "normalized_text": "所以我们必须先获得一手材料，然后再做结构化分析。",
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
        assert_true("writes syntax", (root / "02_segments" / "syntax_segments.json").is_file(), failures)
        assert_true("writes arguments", (root / "02_segments" / "argument_segments.json").is_file(), failures)
        assert_true("no inventory", not (root / "03_inventory").exists(), failures)
        assert_true("no logic", not (root / "04_logic").exists(), failures)
        assert_true("no pack", not (root / "video_analysis_pack.md").exists(), failures)
        arguments = read_json(root / "02_segments" / "argument_segments.json")
        roles = {segment["role"] for segment in arguments["segments"]}
        assert_true("argument roles valid", roles.issubset(ARGUMENT_ROLES), failures, str(roles))

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
