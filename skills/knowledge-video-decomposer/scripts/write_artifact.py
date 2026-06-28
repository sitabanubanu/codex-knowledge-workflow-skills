#!/usr/bin/env python
"""Safely write knowledge-video artifacts as UTF-8 text."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any


ENCODING = "utf-8"

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


class ArtifactWriteError(Exception):
    """Expected CLI-facing write failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_content_file(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ArtifactWriteError("content_file_read_failed", f"could not read content file: {exc}") from exc
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ArtifactWriteError("content_file_not_utf8", f"content file is not valid UTF-8: {exc}") from exc


def stable_json_text(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ArtifactWriteError("invalid_json", f"content is not valid JSON: {exc}") from exc
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def detect_text_warnings(text: str) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []

    if "\ufffd" in text:
        warnings.append(
            {
                "code": "replacement_character",
                "message": "content contains the Unicode replacement character.",
            }
        )

    marker_hits = sorted({marker for marker in MOJIBAKE_MARKERS if marker != "\ufffd" and marker in text})
    if marker_hits:
        warnings.append(
            {
                "code": "mojibake_marker",
                "message": "content contains common mojibake markers.",
                "markers": marker_hits[:8],
            }
        )

    visible = max(1, len(re.sub(r"\s+", "", text)))
    question_count = text.count("?")
    if re.search(r"\?{4,}", text) or (visible >= 200 and question_count >= 20 and question_count / visible >= 0.05):
        warnings.append(
            {
                "code": "excessive_question_marks",
                "message": "content contains an abnormal number of question marks.",
                "question_count": question_count,
                "visible_characters": visible,
            }
        )

    return warnings


def prepare_target(path: Path, mkdirs: bool, overwrite: bool) -> tuple[Path, bool]:
    target = path.expanduser().resolve()
    parent = target.parent

    if target.exists() and target.is_dir():
        raise ArtifactWriteError("target_is_directory", "target path is a directory.")

    if not parent.exists():
        if not mkdirs:
            raise ArtifactWriteError("parent_missing", "parent directory does not exist; pass --mkdirs to create it.")
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ArtifactWriteError("mkdir_failed", f"could not create parent directory: {exc}") from exc

    if not parent.is_dir():
        raise ArtifactWriteError("parent_not_directory", "target parent is not a directory.")

    existed = target.exists()
    if existed and not overwrite:
        raise ArtifactWriteError("target_exists", "target already exists; pass --overwrite to replace it.")

    return target, existed


def write_temp_file(parent: Path, target_name: str, text: str) -> Path:
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{target_name}.", suffix=".tmp", dir=str(parent))
    except OSError as exc:
        raise ArtifactWriteError("temp_create_failed", f"could not create temporary file: {exc}") from exc

    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding=ENCODING, newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        finally:
            raise
    return temp_path


def install_temp_file(temp_path: Path, target: Path, overwrite: bool) -> None:
    try:
        if overwrite:
            os.replace(temp_path, target)
            return

        try:
            os.link(temp_path, target)
        except FileExistsError as exc:
            raise ArtifactWriteError("target_exists", "target already exists; pass --overwrite to replace it.") from exc
        finally:
            temp_path.unlink(missing_ok=True)
    except ArtifactWriteError:
        raise
    except OSError as exc:
        raise ArtifactWriteError("atomic_write_failed", f"could not install temporary file atomically: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)


def verify_readback(target: Path, expected_bytes: bytes) -> bool:
    try:
        actual = target.read_bytes()
    except OSError as exc:
        raise ArtifactWriteError("readback_failed", f"could not read written file: {exc}") from exc

    try:
        actual.decode(ENCODING)
    except UnicodeDecodeError as exc:
        raise ArtifactWriteError("readback_not_utf8", f"written file is not valid UTF-8: {exc}") from exc

    if actual != expected_bytes:
        raise ArtifactWriteError("readback_mismatch", "written bytes did not match requested UTF-8 content.")

    return True


def write_artifact(
    path: Path,
    content: str,
    *,
    json_mode: bool = False,
    mkdirs: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    target, existed = prepare_target(path, mkdirs=mkdirs, overwrite=overwrite)
    text = normalize_newlines(content)
    if json_mode:
        text = stable_json_text(text)

    encoded = text.encode(ENCODING)
    warnings = detect_text_warnings(text)
    temp_path = write_temp_file(target.parent, target.name, text)
    install_temp_file(temp_path, target, overwrite=overwrite)
    valid_utf8 = verify_readback(target, encoded)

    return {
        "path": str(target),
        "bytes": len(encoded),
        "encoding": ENCODING,
        "overwritten": existed and overwrite,
        "valid_utf8": valid_utf8,
        "warnings": warnings,
    }


def emit_json(payload: dict[str, Any], stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def assert_true(name: str, condition: bool, details: str = "") -> list[str]:
    if condition:
        return []
    return [f"{name}: assertion failed{': ' + details if details else ''}"]


def assert_raises(name: str, code: str, func: Any, *args: Any, **kwargs: Any) -> list[str]:
    try:
        func(*args, **kwargs)
    except ArtifactWriteError as exc:
        if exc.code == code:
            return []
        return [f"{name}: expected {code!r}, got {exc.code!r}: {exc.message}"]
    return [f"{name}: expected {code!r}, but call succeeded"]


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="write-artifact-") as tmp:
        base = Path(tmp)

        md_path = base / "nested" / "report.md"
        md_text = "# 标题\n\n中文内容正常写入，不能变成问号。\n"
        md_summary = write_artifact(md_path, md_text, mkdirs=True)
        failures.extend(assert_true("markdown summary valid_utf8", md_summary["valid_utf8"]))
        failures.extend(assert_true("markdown roundtrip", md_path.read_text(encoding=ENCODING) == md_text))
        failures.extend(assert_true("markdown keeps Chinese", "中文内容" in md_path.read_text(encoding=ENCODING)))

        json_path = base / "metadata.json"
        json_summary = write_artifact(
            json_path,
            '{"title":"中文标题","items":["测试","分析"]}',
            json_mode=True,
            mkdirs=True,
        )
        json_text = json_path.read_text(encoding=ENCODING)
        failures.extend(assert_true("json summary valid_utf8", json_summary["valid_utf8"]))
        failures.extend(assert_true("json keeps Chinese", "中文标题" in json_text and "测试" in json_text))
        failures.extend(assert_true("json does not escape Chinese", "\\u4e2d" not in json_text))
        failures.extend(assert_true("json loads", json.loads(json_text)["title"] == "中文标题"))

        failures.extend(
            assert_raises(
                "no-overwrite rejects existing file",
                "target_exists",
                write_artifact,
                md_path,
                "new text",
                mkdirs=True,
            )
        )

        overwrite_summary = write_artifact(md_path, "覆盖后的内容\n", mkdirs=True, overwrite=True)
        failures.extend(assert_true("overwrite summary", overwrite_summary["overwritten"]))
        failures.extend(assert_true("overwrite content", md_path.read_text(encoding=ENCODING) == "覆盖后的内容\n"))

        warning_path = base / "warning.md"
        warning_summary = write_artifact(warning_path, "Broken � text Ã© with ???????? markers.", mkdirs=True)
        warning_codes = {warning["code"] for warning in warning_summary["warnings"]}
        failures.extend(assert_true("replacement warning", "replacement_character" in warning_codes))
        failures.extend(assert_true("mojibake warning", "mojibake_marker" in warning_codes))
        failures.extend(assert_true("question mark warning", "excessive_question_marks" in warning_codes))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("self-test passed")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely write a UTF-8 knowledge-video artifact.")
    parser.add_argument("--path", type=Path, help="Artifact path to write.")
    content_group = parser.add_mutually_exclusive_group()
    content_group.add_argument("--content", default=None, help="Text content to write.")
    content_group.add_argument("--content-file", type=Path, default=None, help="UTF-8 text file containing content.")
    parser.add_argument("--json", action="store_true", help="Validate content as JSON and write stable JSON.")
    parser.add_argument("--mkdirs", action="store_true", help="Create parent directories if needed.")
    overwrite_group = parser.add_mutually_exclusive_group()
    overwrite_group.add_argument("--overwrite", action="store_true", help="Replace an existing artifact.")
    overwrite_group.add_argument("--no-overwrite", action="store_true", help="Refuse to replace an existing artifact.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in writer tests.")
    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    if args.path is None:
        parser.error("--path is required unless --self-test is used")

    try:
        if args.content_file is not None:
            content = read_content_file(args.content_file)
        else:
            content = args.content if args.content is not None else ""

        summary = write_artifact(
            args.path,
            content,
            json_mode=args.json,
            mkdirs=args.mkdirs,
            overwrite=args.overwrite and not args.no_overwrite,
        )
    except ArtifactWriteError as exc:
        emit_json(
            {
                "path": str(args.path.expanduser().resolve()) if args.path is not None else None,
                "error": exc.code,
                "message": exc.message,
            },
            stream=sys.stderr,
        )
        return 1

    emit_json(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
