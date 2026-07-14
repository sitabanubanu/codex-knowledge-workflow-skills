#!/usr/bin/env python
"""Extract conservative inventory artifacts from transcript segments."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import artifact_validator
from write_artifact import ArtifactWriteError, write_artifact


RUNNER_NAME = "knowledge-video-inventory-extractor"
ALLOWED_SOURCE_STATUSES = {"source_confirmed", "source_partial"}
EXAMPLE_TOKENS = ["for example", "example", "case", "\u6bd4\u5982", "\u4f8b\u5982", "\u4e3e\u4e2a\u4f8b\u5b50"]
ANALOGY_TOKENS = ["like", "as if", "analogy", "\u597d\u50cf", "\u5c31\u50cf", "\u7c7b\u6bd4"]
DEFINITION_TOKENS = ["means", "defined", "definition", "\u6240\u8c13", "\u5b9a\u4e49", "\u610f\u601d\u662f"]
CLAIM_TOKENS = [
    "i think",
    "we should",
    "must",
    "therefore",
    "so",
    "\u6211\u8ba4\u4e3a",
    "\u5e94\u8be5",
    "\u5fc5\u987b",
    "\u6240\u4ee5",
    "\u56e0\u6b64",
    "\u7ed3\u8bba",
]
STOPWORDS = {
    "this",
    "that",
    "with",
    "from",
    "have",
    "what",
    "when",
    "where",
    "there",
    "their",
    "about",
    "because",
    "therefore",
    "should",
    "would",
    "could",
    "transcript",
    "speaker",
}


class InventoryExtractorError(Exception):
    """Expected CLI-facing inventory extraction failure."""


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
        raise InventoryExtractorError(f"invalid JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise InventoryExtractorError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise InventoryExtractorError(f"JSON file is not an object: {path}")
    return payload


def load_source_status(path: Path) -> dict[str, Any]:
    status = read_json(path)
    source_status = status.get("source_status")
    if source_status not in ALLOWED_SOURCE_STATUSES:
        raise InventoryExtractorError(
            f"inventory extraction requires source_confirmed or source_partial; got {source_status!r}"
        )
    if not status.get("primary_material_available"):
        raise InventoryExtractorError("inventory extraction requires primary_material_available=true")
    return status


def load_transcript(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise InventoryExtractorError(f"clean transcript not found: {path}")
    rows: dict[str, dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise InventoryExtractorError(f"could not read clean transcript: {exc}") from exc
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InventoryExtractorError(f"invalid clean transcript JSONL line {line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise InventoryExtractorError(f"clean transcript line {line_no} is not an object")
        row_id = str(row.get("id") or "").strip()
        text = str(row.get("normalized_text") or row.get("text") or "").strip()
        if not row_id or not text:
            raise InventoryExtractorError(f"clean transcript line {line_no} is missing id or text")
        rows[row_id] = row
    if not rows:
        raise InventoryExtractorError("clean transcript contains no usable rows")
    return rows


def load_argument_segments(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    segments = payload.get("segments")
    if not isinstance(segments, list) or not segments:
        raise InventoryExtractorError("argument_segments.json must contain a non-empty segments list")
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            raise InventoryExtractorError(f"argument segment {index} is not an object")
        if not str(segment.get("id") or "").strip():
            raise InventoryExtractorError(f"argument segment {index} is missing id")
        if not isinstance(segment.get("transcript_ids"), list) or not segment.get("transcript_ids"):
            raise InventoryExtractorError(f"argument segment {segment.get('id')} has no transcript_ids")
        if not isinstance(segment.get("evidence_spans"), list) or not segment.get("evidence_spans"):
            raise InventoryExtractorError(f"argument segment {segment.get('id')} has no evidence_spans")
    return segments


def row_text(row: dict[str, Any]) -> str:
    return re.sub(r"\s+", " ", str(row.get("normalized_text") or row.get("text") or "")).strip()


def segment_text(segment: dict[str, Any], transcript: dict[str, dict[str, Any]]) -> str:
    texts = []
    for tid in segment.get("transcript_ids", []):
        row = transcript.get(str(tid))
        if row:
            texts.append(row_text(row))
    if texts:
        return " ".join(texts)
    spans = segment.get("evidence_spans") or []
    if spans and isinstance(spans[0], dict):
        return str(spans[0].get("quote") or "").strip()
    return str(segment.get("summary") or segment.get("title") or "").strip()


def compact_quote(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def evidence_for(segment: dict[str, Any], text: str) -> list[dict[str, Any]]:
    spans = segment.get("evidence_spans")
    if isinstance(spans, list) and spans and isinstance(spans[0], dict):
        normalized_spans: list[dict[str, Any]] = []
        for raw_span in spans:
            if not isinstance(raw_span, dict):
                continue
            span = dict(raw_span)
            span["transcript_ids"] = [str(item) for item in span.get("transcript_ids", [])]
            span["quote"] = compact_quote(str(span.get("quote") or text))
            span["source"] = str(span.get("source") or "clean_transcript")
            normalized_spans.append(span)
        if normalized_spans:
            return normalized_spans
    return [
        {
            "transcript_ids": [str(item) for item in segment.get("transcript_ids", [])],
            "start": segment.get("start"),
            "end": segment.get("end"),
            "quote": compact_quote(text),
            "source": "clean_transcript",
        }
    ]


def has_any(text: str, tokens: list[str]) -> bool:
    lowered = text.lower()
    for token in tokens:
        token_lower = token.lower()
        if token_lower.isascii() and re.fullmatch(r"[a-z0-9_ -]+", token_lower):
            pattern = r"(?<![a-z0-9_])" + re.escape(token_lower).replace(r"\ ", r"\s+") + r"(?![a-z0-9_])"
            if re.search(pattern, lowered):
                return True
        elif token_lower in lowered:
            return True
    return False


def claim_type_for(role: str, text: str, *, analysis_target: str = "video_content") -> str:
    if analysis_target in {"social_post", "web_article", "repository"}:
        return "source_claim"
    if role in {"claim", "conclusion"} or has_any(text, CLAIM_TOKENS):
        return "source_claim"
    if role in {"opening", "transition", "definition"}:
        return "inferred_claim"
    return "uncertain_claim"


def extract_claims(
    argument_segments: list[dict[str, Any]],
    transcript: dict[str, dict[str, Any]],
    *,
    analysis_target: str = "video_content",
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for segment in argument_segments:
        role = str(segment.get("role") or "")
        text = segment_text(segment, transcript)
        if not text:
            continue
        if role in {"example", "analogy", "aside"} and not has_any(text, CLAIM_TOKENS):
            continue
        claim_id = f"claim_{len(claims) + 1:03d}"
        claims.append(
            {
                "id": claim_id,
                "text": compact_quote(text, limit=240),
                "claim_type": claim_type_for(role, text, analysis_target=analysis_target),
                "evidence_spans": evidence_for(segment, text),
                "confidence": "medium" if role in {"claim", "conclusion"} else "low",
                "linked_example_ids": [],
                "source_argument_segment_ids": [segment["id"]],
                "notes": "Heuristic inventory item; verify during source-logic stage.",
            }
        )
    return claims


def extract_examples(
    argument_segments: list[dict[str, Any]],
    transcript: dict[str, dict[str, Any]],
    claims: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for segment in argument_segments:
        role = str(segment.get("role") or "")
        text = segment_text(segment, transcript)
        if role != "example" and not has_any(text, EXAMPLE_TOKENS):
            continue
        ex_id = f"ex_{len(examples) + 1:03d}"
        examples.append(
            {
                "id": ex_id,
                "name": str(segment.get("title") or f"Example {len(examples) + 1}"),
                "description": compact_quote(text, limit=300),
                "what_it_demonstrates": "Candidate example role detected from source wording; verify against linked claims.",
                "evidence_spans": evidence_for(segment, text),
                "linked_claim_ids": [],
                "source_argument_segment_ids": [segment["id"]],
                "notes": "No claim link is assigned automatically; source logic stage must verify support relations.",
            }
        )
    return examples


def extract_analogies(argument_segments: list[dict[str, Any]], transcript: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    analogies: list[dict[str, Any]] = []
    for segment in argument_segments:
        role = str(segment.get("role") or "")
        text = segment_text(segment, transcript)
        if role != "analogy" and not has_any(text, ANALOGY_TOKENS):
            continue
        analogies.append(
            {
                "id": f"analogy_{len(analogies) + 1:03d}",
                "source_domain": "",
                "target_domain": "",
                "mapping": [],
                "evidence_spans": evidence_for(segment, text),
                "purpose": "Candidate analogy marker detected; domain mapping must be completed in source-logic stage.",
                "source_argument_segment_ids": [segment["id"]],
            }
        )
    return analogies


def candidate_terms_from_text(text: str) -> list[str]:
    terms: list[str] = []
    for match in re.finditer(r"`([^`]{2,80})`|\"([^\"]{2,80})\"|'([^']{2,80})'", text):
        value = next(group for group in match.groups() if group)
        terms.append(value.strip())
    for match in re.finditer(r"\b[A-Z][A-Za-z0-9_-]{3,}\b|\b[a-z][a-z0-9_-]{4,}\b", text):
        value = match.group(0).strip()
        if value.lower() not in STOPWORDS:
            terms.append(value)
    return terms


def extract_concepts(argument_segments: list[dict[str, Any]], transcript: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    term_counts: Counter[str] = Counter()
    term_sources: dict[str, dict[str, Any]] = {}
    for segment in argument_segments:
        text = segment_text(segment, transcript)
        role = str(segment.get("role") or "")
        terms = candidate_terms_from_text(text)
        if role == "definition" or has_any(text, DEFINITION_TOKENS):
            prefix = re.split(r"\bmeans\b|\bdefined\b|\bdefinition\b|\u662f|\u5b9a\u4e49|\u610f\u601d\u662f", text, maxsplit=1)[0]
            prefix = compact_quote(prefix, limit=40)
            if 2 <= len(prefix) <= 40:
                terms.append(prefix)
        for term in terms:
            normalized = re.sub(r"\s+", " ", term).strip()
            if not normalized:
                continue
            key = normalized.lower()
            term_counts[key] += 1
            term_sources.setdefault(
                key,
                {
                    "term": normalized,
                    "segment": segment,
                    "text": text,
                },
            )
    concepts: list[dict[str, Any]] = []
    for key, count in term_counts.most_common(20):
        source = term_sources[key]
        concepts.append(
            {
                "id": f"concept_{len(concepts) + 1:03d}",
                "term": source["term"],
                "normalized_term": key,
                "definition_in_source": "",
                "evidence_spans": evidence_for(source["segment"], source["text"]),
                "importance": "high" if count >= 2 else "medium",
                "notes": "Candidate concept extracted from repeated, quoted, capitalized, or definition-like source wording.",
                "source_argument_segment_ids": [source["segment"]["id"]],
            }
        )
    return concepts


def render_inventory_gap(
    *,
    concepts: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    analogies: list[dict[str, Any]],
) -> str:
    weak_claims = [claim["id"] for claim in claims if claim.get("claim_type") != "source_claim"]
    undefined_concepts = [concept["id"] for concept in concepts if not concept.get("definition_in_source")]
    return "\n".join(
        [
            "# Inventory Gap Check",
            "",
            "## Inventory Counts",
            "",
            f"- Concepts: `{len(concepts)}`",
            f"- Examples: `{len(examples)}`",
            f"- Claims: `{len(claims)}`",
            f"- Analogies: `{len(analogies)}`",
            "",
            "## Remaining Limits",
            "",
            "- Inventory items are heuristic candidates anchored to transcript evidence.",
            "- Source logic has not been reconstructed yet.",
            "- Empty concept definitions mean the extractor found a candidate term but did not prove an in-source definition.",
            f"- Claims requiring later verification: `{weak_claims}`",
            f"- Candidate concepts without extracted definitions: `{undefined_concepts}`",
            "",
            "## Next Step",
            "",
            "- Run the source logic builder over `03_inventory` and `02_segments`.",
            "",
        ]
    )


def run_inventory(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.expanduser().resolve()
    source_status_path = args.source_status or output_root / "00_source" / "source_status.json"
    transcript_path = args.transcript or output_root / "01_transcript" / "clean_transcript.jsonl"
    argument_segments_path = args.argument_segments or output_root / "02_segments" / "argument_segments.json"

    status = load_source_status(source_status_path)
    transcript = load_transcript(transcript_path)
    argument_segments = load_argument_segments(argument_segments_path)
    analysis_target = str(status.get("analysis_target") or "video_content")
    claims = extract_claims(argument_segments, transcript, analysis_target=analysis_target)
    examples = extract_examples(argument_segments, transcript, claims)
    analogies = extract_analogies(argument_segments, transcript)
    concepts = extract_concepts(argument_segments, transcript)

    written = [
        write_json(
            output_root / "03_inventory" / "concepts.json",
            {
                "runner": RUNNER_NAME,
                "generated_at": now_iso(),
                "concepts": concepts,
            },
        ),
        write_json(
            output_root / "03_inventory" / "examples.json",
            {
                "runner": RUNNER_NAME,
                "generated_at": now_iso(),
                "examples": examples,
            },
        ),
        write_json(
            output_root / "03_inventory" / "claims.json",
            {
                "runner": RUNNER_NAME,
                "generated_at": now_iso(),
                "claims": claims,
            },
        ),
        write_json(
            output_root / "03_inventory" / "analogies.json",
            {
                "runner": RUNNER_NAME,
                "generated_at": now_iso(),
                "analogies": analogies,
            },
        ),
        write_text(
            output_root / "05_gap_check" / "inventory_gap_check.md",
            render_inventory_gap(concepts=concepts, examples=examples, claims=claims, analogies=analogies),
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
        "concepts": len(concepts),
        "examples": len(examples),
        "claims": len(claims),
        "analogies": len(analogies),
        "files_written": [item["path"] for item in written],
        "validation": validation,
        "next_step": "enter_source_logic_builder",
        "validation_next_step": validation.get("next_step"),
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract inventory artifacts from transcript argument segments.")
    parser.add_argument("--output-root", type=Path, required=False, help="Artifact root containing 00_source, 01_transcript, and 02_segments.")
    parser.add_argument("--source-status", type=Path, default=None, help="Optional source_status.json override.")
    parser.add_argument("--transcript", type=Path, default=None, help="Optional clean_transcript.jsonl override.")
    parser.add_argument("--argument-segments", type=Path, default=None, help="Optional argument_segments.json override.")
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
    write_json(
        path,
        {
            "source_status": source_status,
            "can_enter_full_decomposition": source_status in ALLOWED_SOURCE_STATUSES,
            "can_enter_document_composer": True,
            "allowed_report_type": allowed_report_type,
            "source_classes": ["primary_transcript"] if primary else [],
            "primary_material_available": primary,
            "status_reason": "self-test status",
            "failed_probes": [],
            "next_step": "enter_inventory_extraction",
        },
    )


def write_clean_transcript(path: Path) -> None:
    rows = [
        {
            "id": "t0001",
            "start": 0.0,
            "end": 3.0,
            "text": "Source Gate means confirmed primary material.",
            "normalized_text": "Source Gate means confirmed primary material.",
            "source_ids": ["raw_0001"],
            "language": "en",
            "speaker": "",
            "confidence": "high",
        },
        {
            "id": "t0002",
            "start": 4.0,
            "end": 8.0,
            "text": "For example, metadata alone cannot support speaker logic.",
            "normalized_text": "For example, metadata alone cannot support speaker logic.",
            "source_ids": ["raw_0002"],
            "language": "en",
            "speaker": "",
            "confidence": "high",
        },
        {
            "id": "t0003",
            "start": 9.0,
            "end": 13.0,
            "text": "Therefore we must preserve transcript evidence before writing reports.",
            "normalized_text": "Therefore we must preserve transcript evidence before writing reports.",
            "source_ids": ["raw_0003"],
            "language": "en",
            "speaker": "",
            "confidence": "high",
        },
    ]
    write_text(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def span(tids: list[str], quote: str, start: float, end: float) -> dict[str, Any]:
    return {
        "transcript_ids": tids,
        "start": start,
        "end": end,
        "quote": quote,
        "source": "clean_transcript",
    }


def write_argument_segments(path: Path) -> None:
    payload = {
        "segments": [
            {
                "id": "seg_argument_001",
                "start": 0.0,
                "end": 3.0,
                "role": "definition",
                "title": "Source Gate",
                "summary": "Definition segment",
                "transcript_ids": ["t0001"],
                "evidence_spans": [span(["t0001"], "Source Gate means confirmed primary material.", 0.0, 3.0)],
            },
            {
                "id": "seg_argument_002",
                "start": 4.0,
                "end": 8.0,
                "role": "example",
                "title": "metadata example",
                "summary": "Example segment",
                "transcript_ids": ["t0002"],
                "evidence_spans": [span(["t0002"], "For example, metadata alone cannot support speaker logic.", 4.0, 8.0)],
            },
            {
                "id": "seg_argument_003",
                "start": 9.0,
                "end": 13.0,
                "role": "claim",
                "title": "preserve transcript evidence",
                "summary": "Claim segment",
                "transcript_ids": ["t0003"],
                "evidence_spans": [span(["t0003"], "Therefore we must preserve transcript evidence before writing reports.", 9.0, 13.0)],
            },
        ]
    }
    write_json(path, payload)


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="inventory-extractor-") as tmp:
        base = Path(tmp)
        root = base / "confirmed"
        write_status(root / "00_source" / "source_status.json")
        write_clean_transcript(root / "01_transcript" / "clean_transcript.jsonl")
        write_argument_segments(root / "02_segments" / "argument_segments.json")
        result = run_inventory(
            argparse.Namespace(
                output_root=root,
                source_status=None,
                transcript=None,
                argument_segments=None,
                pretty=False,
                self_test=False,
            )
        )
        assert_true("confirmed validates", result["validation"]["valid"] is True, failures, json.dumps(result["validation"], ensure_ascii=False))
        assert_true("writes concepts", (root / "03_inventory" / "concepts.json").is_file(), failures)
        assert_true("writes examples", (root / "03_inventory" / "examples.json").is_file(), failures)
        assert_true("writes claims", (root / "03_inventory" / "claims.json").is_file(), failures)
        assert_true("writes analogies", (root / "03_inventory" / "analogies.json").is_file(), failures)
        assert_true("no logic", not (root / "04_logic").exists(), failures)
        assert_true("no pack", not (root / "video_analysis_pack.md").exists(), failures)
        claims = read_json(root / "03_inventory" / "claims.json")["claims"]
        examples = read_json(root / "03_inventory" / "examples.json")["examples"]
        concepts = read_json(root / "03_inventory" / "concepts.json")["concepts"]
        assert_true("claim evidence", bool(claims and claims[0]["evidence_spans"]), failures)
        assert_true("example evidence", bool(examples and examples[0]["evidence_spans"]), failures)
        assert_true("example does not auto-link claim", examples[0]["linked_claim_ids"] == [], failures)
        assert_true("concept evidence", bool(concepts and concepts[0]["evidence_spans"]), failures)
        claim_types = {claim["claim_type"] for claim in claims}
        assert_true("claim type distribution", "source_claim" in claim_types and "inferred_claim" in claim_types, failures, str(claim_types))

        partial = base / "partial"
        write_status(partial / "00_source" / "source_status.json", source_status="source_partial", primary=True)
        write_clean_transcript(partial / "01_transcript" / "clean_transcript.jsonl")
        write_argument_segments(partial / "02_segments" / "argument_segments.json")
        partial_result = run_inventory(
            argparse.Namespace(
                output_root=partial,
                source_status=None,
                transcript=None,
                argument_segments=None,
                pretty=False,
                self_test=False,
            )
        )
        assert_true("partial primary runs", partial_result["source_status"] == "source_partial", failures)

        blocked = base / "blocked"
        write_status(blocked / "00_source" / "source_status.json", source_status="secondary_only", primary=False)
        write_clean_transcript(blocked / "01_transcript" / "clean_transcript.jsonl")
        write_argument_segments(blocked / "02_segments" / "argument_segments.json")
        blocked_failed = False
        try:
            run_inventory(
                argparse.Namespace(
                    output_root=blocked,
                    source_status=None,
                    transcript=None,
                    argument_segments=None,
                    pretty=False,
                    self_test=False,
                )
            )
        except InventoryExtractorError:
            blocked_failed = True
        assert_true("blocked fails", blocked_failed, failures)
        assert_true("blocked creates no 03", not (blocked / "03_inventory").exists(), failures)

        confirmed_no_primary = base / "confirmed_no_primary"
        write_status(
            confirmed_no_primary / "00_source" / "source_status.json",
            source_status="source_confirmed",
            primary=False,
        )
        write_clean_transcript(confirmed_no_primary / "01_transcript" / "clean_transcript.jsonl")
        write_argument_segments(confirmed_no_primary / "02_segments" / "argument_segments.json")
        confirmed_no_primary_failed = False
        try:
            run_inventory(
                argparse.Namespace(
                    output_root=confirmed_no_primary,
                    source_status=None,
                    transcript=None,
                    argument_segments=None,
                    pretty=False,
                    self_test=False,
                )
            )
        except InventoryExtractorError:
            confirmed_no_primary_failed = True
        assert_true("confirmed without primary fails", confirmed_no_primary_failed, failures)
        assert_true("confirmed without primary creates no 03", not (confirmed_no_primary / "03_inventory").exists(), failures)

        missing_segments = base / "missing_segments"
        write_status(missing_segments / "00_source" / "source_status.json")
        write_clean_transcript(missing_segments / "01_transcript" / "clean_transcript.jsonl")
        missing_failed = False
        try:
            run_inventory(
                argparse.Namespace(
                    output_root=missing_segments,
                    source_status=None,
                    transcript=None,
                    argument_segments=None,
                    pretty=False,
                    self_test=False,
                )
            )
        except InventoryExtractorError:
            missing_failed = True
        assert_true("missing argument segments fails", missing_failed, failures)
        assert_true("missing argument creates no 03", not (missing_segments / "03_inventory").exists(), failures)

        no_evidence = base / "no_evidence"
        write_status(no_evidence / "00_source" / "source_status.json")
        write_clean_transcript(no_evidence / "01_transcript" / "clean_transcript.jsonl")
        write_json(
            no_evidence / "02_segments" / "argument_segments.json",
            {
                "segments": [
                    {
                        "id": "seg_argument_001",
                        "role": "claim",
                        "title": "bad segment",
                        "transcript_ids": ["t0001"],
                        "evidence_spans": [],
                    }
                ]
            },
        )
        no_evidence_failed = False
        try:
            run_inventory(
                argparse.Namespace(
                    output_root=no_evidence,
                    source_status=None,
                    transcript=None,
                    argument_segments=None,
                    pretty=False,
                    self_test=False,
                )
            )
        except InventoryExtractorError:
            no_evidence_failed = True
        assert_true("missing evidence spans fails", no_evidence_failed, failures)
        assert_true("missing evidence creates no 03", not (no_evidence / "03_inventory").exists(), failures)

        multi_span = base / "multi_span"
        write_status(multi_span / "00_source" / "source_status.json")
        write_clean_transcript(multi_span / "01_transcript" / "clean_transcript.jsonl")
        payload = {
            "segments": [
                {
                    "id": "seg_argument_001",
                    "start": 0.0,
                    "end": 8.0,
                    "role": "claim",
                    "title": "multi span",
                    "summary": "Claim segment",
                    "transcript_ids": ["t0001", "t0002"],
                    "evidence_spans": [
                        span(["t0001"], "Source Gate means confirmed primary material.", 0.0, 3.0),
                        span(["t0002"], "For example, metadata alone cannot support speaker logic.", 4.0, 8.0),
                    ],
                }
            ]
        }
        write_json(multi_span / "02_segments" / "argument_segments.json", payload)
        multi_result = run_inventory(
            argparse.Namespace(
                output_root=multi_span,
                source_status=None,
                transcript=None,
                argument_segments=None,
                pretty=False,
                self_test=False,
            )
        )
        multi_claims = read_json(multi_span / "03_inventory" / "claims.json")["claims"]
        assert_true("multi-span runs", multi_result["claims"] == 1, failures)
        assert_true("multi-span preserved", len(multi_claims[0]["evidence_spans"]) == 2, failures)

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
    try:
        summary = run_inventory(args)
    except (InventoryExtractorError, ArtifactWriteError, OSError) as exc:
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
