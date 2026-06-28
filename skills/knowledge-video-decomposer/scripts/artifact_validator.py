#!/usr/bin/env python
"""Validate knowledge-video-decomposer artifacts against source-status gates."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


SOURCE_STATUSES = {
    "source_confirmed",
    "source_partial",
    "secondary_only",
    "source_blocked",
    "source_failed",
    "degraded_report_only",
}

BLOCKED_FULL_STATUSES = {
    "secondary_only",
    "source_blocked",
    "source_failed",
    "degraded_report_only",
}

PRIMARY_SOURCE_CLASSES = {
    "primary_transcript",
    "primary_audio_asr",
    "browser_visible_transcript",
}

REQUIRED_STATUS_FIELDS = {
    "source_status",
    "can_enter_full_decomposition",
    "can_enter_document_composer",
    "allowed_report_type",
    "source_classes",
    "primary_material_available",
    "status_reason",
    "failed_probes",
    "next_step",
}

TEXT_EXTENSIONS = {
    ".csv",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".text",
    ".txt",
    ".yaml",
    ".yml",
}

CANONICAL_FULL_ARTIFACTS = {
    "video_analysis_pack.md",
    "01_transcript/clean_transcript.jsonl",
    "01_transcript/clean_transcript.md",
    "02_segments/argument_segments.json",
    "03_inventory/concepts.json",
    "03_inventory/examples.json",
    "03_inventory/claims.json",
    "03_inventory/analogies.json",
    "04_logic/source_logic.md",
    "04_logic/logic_graph.json",
    "05_gap_check/gap_check.md",
}

CANONICAL_FULL_DIRS = {
    "00_source",
    "01_transcript",
    "02_segments",
    "03_inventory",
    "04_logic",
    "05_gap_check",
}

BLOCKED_OUTPUT_RULES = (
    ("speaker_logic_reconstruction", re.compile(r"speaker[-_ ]logic|logic[-_ ]reconstruction")),
    ("source_logic", re.compile(r"source[-_ ]logic")),
    ("argument_graph", re.compile(r"argument[-_ ]graph|logic[-_ ]graph")),
    ("claims_inventory", re.compile(r"claims?[-_ ]inventory|\bclaims\b")),
)

FULL_REPORT_PATTERNS = (
    re.compile(r"\bcomplete\b.*\b(video|source|speaker|analysis|decomposition)\b", re.I),
    re.compile(r"\bfull\b.*\b(video|source|speaker|analysis|decomposition)\b", re.I),
    re.compile(r"\bvideo analysis pack\b", re.I),
    re.compile(r"\bsource-confirmed\b", re.I),
    re.compile(r"\bspeaker logic reconstruction\b", re.I),
    re.compile(r"\bcomplete claims inventory\b", re.I),
)

DEGRADED_PATTERNS = (
    re.compile(r"\bdegraded\b", re.I),
    re.compile(r"\bacquisition failure\b", re.I),
    re.compile(r"\bsource blocked\b", re.I),
    re.compile(r"\bsecondary[-_ ]only\b", re.I),
    re.compile(r"\bno primary\b", re.I),
)

MOJIBAKE_MARKERS = (
    "\ufffd",
    "\u00ef\u00bf\u00bd",
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac",
    "\u20ac?",
    "\u6d93",
    "\u951b",
    "\u7ec2",
    "\u7d16",
    "\u9428",
    "\u9296",
    "\u4e73",
)


def normalize_rel(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return str(path)
    return rel.as_posix()


def add_finding(
    findings: list[dict[str, Any]],
    severity: str,
    code: str,
    message: str,
    file: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    row: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if file:
        row["file"] = file
    if details:
        row["details"] = details
    findings.append(row)


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def iter_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted((path for path in root.rglob("*") if path.is_file()), key=lambda p: p.as_posix())


def read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError as exc:
        return None, f"not valid UTF-8: {exc}"
    except OSError as exc:
        return None, f"could not read file: {exc}"


def load_json_file(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    text, error = read_text(path)
    if error:
        return None, error
    try:
        payload = json.loads(text or "")
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return None, "source-status JSON must be an object"
    return payload, None


def candidate_status_paths(root: Path) -> list[Path]:
    names = (
        "acquisition_status.json",
        "source_status.json",
        "00_source/acquisition_status.json",
        "00_source/source_status.json",
    )
    paths = [root / name for name in names]
    if root.exists():
        paths.extend(
            sorted(
                (
                    path
                    for path in root.rglob("*.json")
                    if "status" in path.name.lower() or "acquisition" in path.name.lower()
                ),
                key=lambda p: p.as_posix(),
            )
        )
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            result.append(path)
    return result


def find_source_status_json(root: Path) -> Path | None:
    for path in candidate_status_paths(root):
        if not path.is_file():
            continue
        payload, _ = load_json_file(path)
        if payload and "source_status" in payload:
            return path
    return None


def validate_source_status(
    status_payload: dict[str, Any] | None,
    status_path: Path | None,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    if status_payload is None:
        add_finding(
            findings,
            "error",
            "source_status_missing",
            "No source-status JSON with source_status was found.",
            str(status_path) if status_path else None,
        )
        return {}

    missing = sorted(field for field in REQUIRED_STATUS_FIELDS if field not in status_payload)
    if missing:
        add_finding(
            findings,
            "error",
            "source_status_required_fields_missing",
            "Source-status JSON is missing required machine fields.",
            str(status_path) if status_path else None,
            {"missing_fields": missing},
        )

    source_status = status_payload.get("source_status")
    if source_status not in SOURCE_STATUSES:
        add_finding(
            findings,
            "error",
            "source_status_unknown",
            "source_status is missing or not one of the allowed values.",
            str(status_path) if status_path else None,
            {"source_status": source_status, "allowed": sorted(SOURCE_STATUSES)},
        )

    if "can_enter_full_decomposition" in status_payload and not isinstance(
        status_payload["can_enter_full_decomposition"], bool
    ):
        add_finding(
            findings,
            "error",
            "source_status_bad_type",
            "can_enter_full_decomposition must be a boolean.",
            str(status_path) if status_path else None,
        )

    if "primary_material_available" in status_payload and not isinstance(
        status_payload["primary_material_available"], bool
    ):
        add_finding(
            findings,
            "error",
            "source_status_bad_type",
            "primary_material_available must be a boolean.",
            str(status_path) if status_path else None,
        )

    if "can_enter_document_composer" in status_payload and not isinstance(
        status_payload["can_enter_document_composer"], bool
    ):
        add_finding(
            findings,
            "error",
            "source_status_bad_type",
            "can_enter_document_composer must be a boolean.",
            str(status_path) if status_path else None,
        )

    if "source_classes" in status_payload and not isinstance(status_payload["source_classes"], list):
        add_finding(
            findings,
            "error",
            "source_status_bad_type",
            "source_classes must be a list.",
            str(status_path) if status_path else None,
        )

    if "failed_probes" in status_payload and not isinstance(status_payload["failed_probes"], list):
        add_finding(
            findings,
            "error",
            "source_status_bad_type",
            "failed_probes must be a list.",
            str(status_path) if status_path else None,
        )

    return status_payload


def has_primary_material(status_payload: dict[str, Any]) -> bool:
    if status_payload.get("primary_material_available") is True:
        return True
    classes = status_payload.get("source_classes")
    if isinstance(classes, list) and PRIMARY_SOURCE_CLASSES.intersection(str(item) for item in classes):
        return True
    return status_payload.get("source_status") == "source_confirmed" and status_payload.get(
        "can_enter_full_decomposition"
    ) is True


def rel_set(paths: list[Path], root: Path) -> set[str]:
    return {normalize_rel(path, root).lower() for path in paths}


def detect_full_pack_shape(root: Path, files: list[Path]) -> tuple[bool, list[str]]:
    existing_files = rel_set(files, root)
    existing_dirs = {
        normalize_rel(path, root).lower()
        for path in sorted(root.rglob("*"), key=lambda p: p.as_posix())
        if path.is_dir()
    }
    canonical_hits = sorted(path for path in CANONICAL_FULL_ARTIFACTS if path.lower() in existing_files)
    dir_hits = sorted(path for path in CANONICAL_FULL_DIRS if path.lower() in existing_dirs)

    has_pack = "video_analysis_pack.md" in existing_files
    full_shape = (has_pack and len(dir_hits) >= 3) or len(canonical_hits) >= 5 or len(dir_hits) >= 5
    evidence = canonical_hits + [f"{path}/" for path in dir_hits]
    return full_shape, evidence


def first_markdown_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def is_degraded_text(text: str) -> bool:
    return any(pattern.search(text) for pattern in DEGRADED_PATTERNS)


def title_claims_full_report(text: str, path: Path) -> bool:
    sample = "\n".join(text.splitlines()[:20])
    heading = first_markdown_heading(text)
    target = f"{path.name}\n{heading}\n{sample}"
    return any(pattern.search(target) for pattern in FULL_REPORT_PATTERNS) and not is_degraded_text(target)


def detect_blocked_outputs(
    root: Path,
    files: list[Path],
    file_text: dict[Path, str],
    source_status: str | None,
    primary_available: bool,
    mode: str,
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    full_shape, full_shape_evidence = detect_full_pack_shape(root, files)

    if source_status in BLOCKED_FULL_STATUSES and full_shape:
        blocked.append(
            {
                "type": "full_video_analysis_pack_shape",
                "files": full_shape_evidence,
            }
        )
        add_finding(
            findings,
            "error",
            "blocked_full_pack_shape",
            "Blocked or degraded source status must not contain a full video_analysis_pack shape.",
            details={"source_status": source_status, "evidence": full_shape_evidence},
        )

    if source_status in BLOCKED_FULL_STATUSES:
        for path in files:
            rel = normalize_rel(path, root)
            if rel.lower() == "video_analysis_pack.md":
                blocked.append({"type": "video_analysis_pack_shell_for_blocked_status", "file": rel})
                add_finding(
                    findings,
                    "error",
                    "video_analysis_pack_shell_for_blocked_status",
                    "Blocked or degraded source status must not contain a video_analysis_pack.md shell.",
                    rel,
                    {"source_status": source_status},
                )

    if not primary_available:
        for path, text in file_text.items():
            rel = normalize_rel(path, root)
            rel_lower = rel.lower()
            stem_path = rel_lower.replace("/", " ")
            for kind, pattern in BLOCKED_OUTPUT_RULES:
                if pattern.search(stem_path):
                    if path.stat().st_size > 0:
                        blocked.append({"type": kind, "file": rel})
                        add_finding(
                            findings,
                            "error",
                            f"blocked_{kind}",
                            "No primary transcript, audio, or browser-visible transcript is available, so this output is not allowed.",
                            rel,
                            {"mode": mode},
                        )
                    break
            if path.suffix.lower() == ".md" and title_claims_full_report(text, path):
                blocked.append({"type": "full_report_title", "file": rel})
                add_finding(
                    findings,
                    "error",
                    "full_report_title_without_primary",
                    "Report title or opening text claims a complete/full analysis without primary source material.",
                    rel,
                )

    if source_status in BLOCKED_FULL_STATUSES:
        for path, text in file_text.items():
            rel = normalize_rel(path, root)
            if path.name.lower() in {"final_report.md", "video_analysis_pack.md"} and title_claims_full_report(
                text, path
            ):
                blocked.append({"type": "degraded_report_disguised_as_full", "file": rel})
                add_finding(
                    findings,
                    "error",
                    "degraded_report_disguised_as_full",
                    "A blocked/degraded source status cannot be paired with a title that presents the output as complete analysis.",
                    rel,
                    {"source_status": source_status},
                )

    return blocked


def detect_encoding_issues(
    root: Path,
    path: Path,
    text: str | None,
    read_error: str | None,
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rel = normalize_rel(path, root)
    issues: list[dict[str, Any]] = []

    if read_error:
        issue = {"file": rel, "type": "utf8_decode_error", "detail": read_error}
        issues.append(issue)
        add_finding(findings, "error", "encoding_utf8_decode_error", read_error, rel)
        return issues

    text = text or ""
    if "\ufffd" in text:
        issue = {"file": rel, "type": "replacement_character"}
        issues.append(issue)
        add_finding(findings, "error", "encoding_replacement_character", "File contains replacement characters.", rel)

    marker_hits = sorted({marker for marker in MOJIBAKE_MARKERS if marker != "\ufffd" and marker in text})
    if marker_hits:
        issue = {"file": rel, "type": "mojibake_marker", "markers": marker_hits[:8]}
        issues.append(issue)
        add_finding(
            findings,
            "error",
            "encoding_mojibake_marker",
            "File contains typical mojibake markers.",
            rel,
            {"markers": marker_hits[:8]},
        )

    visible = max(1, len(re.sub(r"\s+", "", text)))
    question_count = text.count("?")
    has_many_question_marks = bool(re.search(r"\?{4,}", text)) or (
        visible >= 200 and question_count >= 20 and question_count / visible >= 0.05
    )
    if has_many_question_marks:
        issue = {
            "file": rel,
            "type": "excessive_question_marks",
            "question_count": question_count,
            "visible_characters": visible,
        }
        issues.append(issue)
        add_finding(
            findings,
            "error",
            "encoding_excessive_question_marks",
            "File contains an abnormal number of question marks, which may indicate a broken write path.",
            rel,
            {"question_count": question_count, "visible_characters": visible},
        )

    return issues


def validate_structured_text(
    root: Path,
    path: Path,
    text: str,
    findings: list[dict[str, Any]],
) -> None:
    rel = normalize_rel(path, root)
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            add_finding(findings, "error", "json_invalid", f"Invalid JSON: {exc}", rel)
    elif suffix == ".jsonl":
        for index, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                add_finding(
                    findings,
                    "error",
                    "jsonl_invalid",
                    f"Invalid JSONL on line {index}: {exc}",
                    rel,
                    {"line": index},
                )
                break


def next_step_for(
    valid: bool,
    source_status: str | None,
    blocked_outputs: list[dict[str, Any]],
    encoding_issues: list[dict[str, Any]],
    findings: list[dict[str, Any]],
) -> str:
    codes = {str(item.get("code", "")) for item in findings}
    if "source_status_missing" in codes or "source_status_required_fields_missing" in codes:
        return "write_or_fix_acquisition_status_json_before_downstream_use"
    if encoding_issues:
        return "rewrite_artifacts_as_utf8_and_rerun_validator"
    if blocked_outputs:
        return "remove_blocked_full_analysis_outputs_or_provide_primary_material"
    if not valid:
        return "fix_validator_findings_and_rerun"
    if source_status == "source_confirmed":
        return "safe_to_continue_to_document_composer"
    if source_status == "source_partial":
        return "continue_only_with_explicit_partial_scope"
    if source_status in BLOCKED_FULL_STATUSES:
        return "continue_only_with_degraded_or_acquisition_failure_report"
    return "no_action_required"


def validate_artifact_root(
    artifact_root: Path,
    source_status_json: Path | None = None,
    mode: str = "strict",
) -> dict[str, Any]:
    root = artifact_root.resolve()
    findings: list[dict[str, Any]] = []
    checked_files: list[str] = []
    file_text: dict[Path, str] = {}
    encoding_issues: list[dict[str, Any]] = []

    if not root.exists():
        add_finding(findings, "error", "artifact_root_missing", "Artifact root does not exist.", str(root))
        return {
            "valid": False,
            "severity": "error",
            "findings": findings,
            "source_status": None,
            "checked_files": [],
            "blocked_outputs_detected": [],
            "encoding_issues": [],
            "next_step": "provide_existing_artifact_root",
        }

    status_path = source_status_json.resolve() if source_status_json else find_source_status_json(root)
    status_payload: dict[str, Any] | None = None
    if status_path and status_path.is_file():
        status_payload, status_error = load_json_file(status_path)
        checked_files.append(str(status_path))
        if status_error:
            add_finding(findings, "error", "source_status_json_invalid", status_error, str(status_path))
    else:
        status_error = None

    status_payload = validate_source_status(status_payload, status_path, findings)
    source_status = status_payload.get("source_status") if status_payload else None
    primary_available = has_primary_material(status_payload)

    files = iter_files(root)
    for path in files:
        checked_files.append(str(path))
        if path.stat().st_size == 0:
            add_finding(
                findings,
                "error",
                "empty_artifact_file",
                "Artifact file is empty.",
                normalize_rel(path, root),
            )
            continue
        if not is_text_file(path):
            continue

        text, read_error = read_text(path)
        encoding_issues.extend(detect_encoding_issues(root, path, text, read_error, findings))
        if read_error or text is None:
            continue
        file_text[path] = text
        validate_structured_text(root, path, text, findings)

    blocked_outputs = detect_blocked_outputs(
        root,
        files,
        file_text,
        str(source_status) if source_status else None,
        primary_available,
        mode,
        findings,
    )

    if mode == "strict" and source_status in BLOCKED_FULL_STATUSES:
        allowed = status_payload.get("allowed_report_type")
        if allowed not in {"acquisition_failure_report", "degraded_source_report"}:
            add_finding(
                findings,
                "error",
                "blocked_status_bad_allowed_report_type",
                "Blocked/degraded source status must allow only acquisition failure or degraded source reports.",
                str(status_path) if status_path else None,
                {"allowed_report_type": allowed},
            )

    error_count = sum(1 for finding in findings if finding.get("severity") == "error")
    warning_count = sum(1 for finding in findings if finding.get("severity") == "warning")
    valid = error_count == 0
    severity = "error" if error_count else "warning" if warning_count else "ok"

    return {
        "valid": valid,
        "severity": severity,
        "findings": findings,
        "source_status": source_status,
        "checked_files": sorted(set(checked_files)),
        "blocked_outputs_detected": blocked_outputs,
        "encoding_issues": encoding_issues,
        "next_step": next_step_for(valid, str(source_status) if source_status else None, blocked_outputs, encoding_issues, findings),
    }


def write_json(payload: dict[str, Any], output: Path | None, pretty: bool) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty)
    text += "\n"
    if output is None:
        sys.stdout.write(text)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")


def write_status(path: Path, **overrides: Any) -> None:
    payload: dict[str, Any] = {
        "source_status": "source_confirmed",
        "can_enter_full_decomposition": True,
        "can_enter_document_composer": True,
        "allowed_report_type": "full_video_analysis_pack",
        "primary_material_available": True,
        "source_classes": ["primary_transcript"],
        "status_reason": "self-test status",
        "failed_probes": [],
        "next_step": "enter_segmentation_inventory_logic_gap_check",
    }
    payload.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8", newline="\n")


def write_full_artifacts(root: Path) -> None:
    files = {
        "00_source/acquisition_status.json": None,
        "01_transcript/clean_transcript.jsonl": {"id": "t001", "text": "hello", "start": 0, "end": 1},
        "02_segments/argument_segments.json": {"segments": [{"id": "seg_argument_001"}]},
        "03_inventory/claims.json": {"claims": [{"id": "claim_001", "text": "A source claim."}]},
        "04_logic/source_logic.md": "# Source Logic\n\n## Argument Flow\nSource-faithful logic.",
        "04_logic/logic_graph.json": {"nodes": [{"id": "claim_001"}], "edges": []},
        "05_gap_check/gap_check.md": "# Gap Check\n\nNo gaps.",
        "video_analysis_pack.md": "# Video Analysis Pack\n\nSource-confirmed analysis.",
    }
    for rel, payload in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".jsonl"):
            path.write_text(json.dumps(payload) + "\n", encoding="utf-8", newline="\n")
        elif rel.endswith(".json"):
            if payload is not None:
                path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
        else:
            path.write_text(str(payload), encoding="utf-8", newline="\n")


def assert_case(name: str, report: dict[str, Any], expected_valid: bool) -> list[str]:
    if report.get("valid") == expected_valid:
        return []
    return [
        f"{name}: expected valid={expected_valid!r}, got {report.get('valid')!r}; findings={report.get('findings')!r}"
    ]


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="artifact-validator-") as tmp:
        base = Path(tmp)

        case1 = base / "source_confirmed_full"
        write_full_artifacts(case1)
        write_status(case1 / "00_source" / "acquisition_status.json")
        failures.extend(assert_case("source_confirmed + full artifacts", validate_artifact_root(case1), True))

        case2 = base / "secondary_logic"
        write_status(
            case2 / "00_source" / "acquisition_status.json",
            source_status="secondary_only",
            can_enter_full_decomposition=False,
            allowed_report_type="degraded_source_report",
            primary_material_available=False,
            source_classes=["secondary_summary"],
        )
        logic_path = case2 / "04_logic" / "source_logic.md"
        logic_path.parent.mkdir(parents=True, exist_ok=True)
        logic_path.write_text("# Source Logic\n\nSpeaker logic reconstruction.", encoding="utf-8", newline="\n")
        failures.extend(assert_case("secondary_only + logic artifact", validate_artifact_root(case2), False))

        case3 = base / "blocked_complete_final"
        write_status(
            case3 / "00_source" / "acquisition_status.json",
            source_status="source_blocked",
            can_enter_full_decomposition=False,
            allowed_report_type="acquisition_failure_report",
            primary_material_available=False,
            source_classes=["platform_metadata"],
        )
        final_path = case3 / "final_report.md"
        final_path.write_text("# Complete Video Analysis\n\nThis is a full decomposition.", encoding="utf-8", newline="\n")
        failures.extend(assert_case("source_blocked + complete final_report", validate_artifact_root(case3), False))

        case4 = base / "encoding_issue"
        write_status(case4 / "00_source" / "acquisition_status.json")
        bad_path = case4 / "01_transcript" / "clean_transcript.md"
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("# Clean Transcript\n\nBroken \ufffd text with \u00c3\u00a9 marker.", encoding="utf-8", newline="\n")
        failures.extend(assert_case("replacement char or mojibake", validate_artifact_root(case4), False))

        case5 = base / "degraded_ok_report"
        write_status(
            case5 / "00_source" / "acquisition_status.json",
            source_status="degraded_report_only",
            can_enter_full_decomposition=False,
            allowed_report_type="degraded_source_report",
            primary_material_available=False,
            source_classes=["secondary_summary"],
        )
        degraded = case5 / "degraded_source_report.md"
        degraded.write_text("# Degraded Source Report\n\nNo primary transcript is available.", encoding="utf-8", newline="\n")
        failures.extend(assert_case("degraded-ok allows degraded report", validate_artifact_root(case5, mode="degraded-ok"), True))

        logic = case5 / "04_logic" / "source_logic.md"
        logic.parent.mkdir(parents=True, exist_ok=True)
        logic.write_text("# Source Logic\n\nSpeaker logic reconstruction.", encoding="utf-8", newline="\n")
        failures.extend(
            assert_case(
                "degraded-ok still blocks logic reconstruction",
                validate_artifact_root(case5, mode="degraded-ok"),
                False,
            )
        )

        case6 = base / "missing_required_fields"
        write_status(
            case6 / "00_source" / "acquisition_status.json",
            can_enter_document_composer=None,
            source_classes=None,
            status_reason=None,
            failed_probes=None,
            next_step=None,
        )
        status6 = case6 / "00_source" / "acquisition_status.json"
        payload6 = json.loads(status6.read_text(encoding="utf-8"))
        for key in ["can_enter_document_composer", "source_classes", "status_reason", "failed_probes", "next_step"]:
            payload6.pop(key, None)
        status6.write_text(json.dumps(payload6, ensure_ascii=False), encoding="utf-8", newline="\n")
        failures.extend(assert_case("missing required source-status fields", validate_artifact_root(case6), False))

        case7 = base / "blocked_bare_pack_shell"
        write_status(
            case7 / "00_source" / "acquisition_status.json",
            source_status="source_blocked",
            can_enter_full_decomposition=False,
            can_enter_document_composer=True,
            allowed_report_type="acquisition_failure_report",
            primary_material_available=False,
            source_classes=["platform_metadata"],
            status_reason="blocked self-test",
        )
        bare_pack = case7 / "video_analysis_pack.md"
        bare_pack.write_text("# Degraded Notes\n\nNo primary transcript is available.", encoding="utf-8", newline="\n")
        failures.extend(assert_case("blocked status + bare video_analysis_pack shell", validate_artifact_root(case7), False))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("self-test passed")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate knowledge-video-decomposer artifacts against source-status gates.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="Path to a video_analysis_pack root or workflow output directory.",
    )
    parser.add_argument(
        "--source-status-json",
        type=Path,
        default=None,
        help="Optional path to acquisition/source status JSON.",
    )
    parser.add_argument(
        "--mode",
        choices=["strict", "degraded-ok"],
        default="strict",
        help="Validation mode. degraded-ok permits properly labeled degraded reports, never full logic outputs.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON report output path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in validator tests.")
    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    if args.artifact_root is None:
        parser.error("--artifact-root is required unless --self-test is used")

    report = validate_artifact_root(args.artifact_root, args.source_status_json, args.mode)
    write_json(report, args.output, args.pretty)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
