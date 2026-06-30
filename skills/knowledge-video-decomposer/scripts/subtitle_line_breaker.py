#!/usr/bin/env python
"""Small subtitle-line helpers used by transcript_segmenter."""

from __future__ import annotations

import re
from typing import Any


SENTENCE_ENDINGS = ("\u3002", "\uff1f", "\uff01", ".", "?", "!")
SOFT_BREAK_RE = re.compile(r"([,;:\uFF0C\uFF1B\uFF1A\u3001])\s*")


def numeric_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def sentence_complete(text: str) -> bool:
    return normalize_space(text).endswith(SENTENCE_ENDINGS)


def reading_speed_cps(text: str, start: Any, end: Any) -> float | None:
    start_value = numeric_or_none(start)
    end_value = numeric_or_none(end)
    if start_value is None or end_value is None or end_value <= start_value:
        return None
    return round(len(normalize_space(text)) / (end_value - start_value), 3)


def split_subtitle_lines(text: str, *, max_line_chars: int = 42, max_lines: int = 2) -> list[str]:
    cleaned = normalize_space(text)
    if not cleaned:
        return []
    if len(cleaned) <= max_line_chars:
        return [cleaned]

    pieces: list[str] = []
    for raw_piece in SOFT_BREAK_RE.sub(r"\1|", cleaned).split("|"):
        piece = raw_piece.strip()
        if piece:
            pieces.append(piece)
    if not pieces:
        pieces = [cleaned]

    lines: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current} {piece}".strip() if current else piece
        if len(candidate) <= max_line_chars:
            current = candidate
            continue
        if current:
            lines.append(current)
        while len(piece) > max_line_chars:
            lines.append(piece[:max_line_chars].rstrip())
            piece = piece[max_line_chars:].lstrip()
        current = piece
    if current:
        lines.append(current)

    if len(lines) <= max_lines:
        return lines

    kept = lines[: max_lines - 1]
    tail = " ".join(lines[max_lines - 1 :]).strip()
    while len(tail) > max_line_chars:
        kept.append(tail[:max_line_chars].rstrip())
        tail = tail[max_line_chars:].lstrip()
    if tail:
        kept.append(tail)
    return kept


def line_width_ok(lines: list[str], *, max_line_chars: int) -> bool:
    return bool(lines) and all(len(line) <= max_line_chars for line in lines)


def subtitle_confidence(*, issues: list[str], has_timing: bool, sentence_is_complete: bool) -> str:
    score = 1.0
    if not has_timing:
        score -= 0.25
    if not sentence_is_complete:
        score -= 0.15
    score -= min(0.45, 0.12 * len(issues))
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"
