"""Convert upstream backend output into evidence-layer canonical artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CanonicalizationError(Exception):
    """Raised when backend output does not contain the expected source material."""


TEXT_KEYS = {
    "body",
    "caption",
    "content",
    "content_text",
    "desc",
    "description",
    "note_text",
    "text",
    "title",
}
ERROR_KEYS = {"error", "error_code", "error_message", "message"}
BLOCK_MARKERS = ("auth_required", "captcha", "login required", "not authenticated", "permission denied")


def parse_json_output(stdout: str) -> Any:
    text = stdout.strip()
    if not text:
        raise CanonicalizationError("backend returned empty output")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise CanonicalizationError(f"backend output is not valid JSON: {exc}") from exc


def _collect_text(value: Any, rows: list[tuple[str, str]], *, parent_key: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in TEXT_KEYS and isinstance(child, (str, int, float)):
                text = str(child).strip()
                if text:
                    rows.append((lowered, text))
            else:
                _collect_text(child, rows, parent_key=lowered)
    elif isinstance(value, list):
        for child in value:
            _collect_text(child, rows, parent_key=parent_key)
    elif isinstance(value, str) and parent_key in TEXT_KEYS:
        text = value.strip()
        if text:
            rows.append((parent_key, text))


def _block_reason(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    values = []
    for key, value in payload.items():
        if str(key).lower() in ERROR_KEYS and isinstance(value, (str, int)):
            values.append(str(value))
    combined = " ".join(values).lower()
    return combined if any(marker in combined for marker in BLOCK_MARKERS) else ""


def canonical_page_text(stdout: str) -> tuple[str, Any]:
    payload = parse_json_output(stdout)
    blocked = _block_reason(payload)
    if blocked:
        raise CanonicalizationError(blocked)
    rows: list[tuple[str, str]] = []
    _collect_text(payload, rows)
    seen: set[str] = set()
    paragraphs: list[str] = []
    for key, value in rows:
        normalized = " ".join(value.split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        label = key.replace("_", " ").title()
        paragraphs.append(f"{label}: {normalized}")
    if not paragraphs:
        raise CanonicalizationError("backend JSON contained no recognized title/content/text fields")
    return "\n\n".join(paragraphs) + "\n", payload


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _collect_subtitle_rows(value: Any, rows: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        text_value = value.get("content") or value.get("text") or value.get("subtitle")
        if isinstance(text_value, str) and text_value.strip():
            start = _as_float(value.get("from", value.get("start")))
            end = _as_float(value.get("to", value.get("end")))
            rows.append(
                {
                    "start": start,
                    "end": end,
                    "text": " ".join(text_value.split()),
                    "source": "opencli_bilibili_subtitle",
                }
            )
            return
        for child in value.values():
            _collect_subtitle_rows(child, rows)
    elif isinstance(value, list):
        for child in value:
            _collect_subtitle_rows(child, rows)


def canonical_subtitle_json(stdout: str) -> tuple[dict[str, Any], Any]:
    payload = parse_json_output(stdout)
    blocked = _block_reason(payload)
    if blocked:
        raise CanonicalizationError(blocked)
    rows: list[dict[str, Any]] = []
    _collect_subtitle_rows(payload, rows)
    if not rows:
        raise CanonicalizationError("backend JSON contained no subtitle rows")
    return {"segments": rows}, payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
