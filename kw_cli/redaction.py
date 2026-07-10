"""Central secret redaction for persisted workflow records."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


REDACTED = "[REDACTED]"
SENSITIVE_MARKERS = (
    "authorization",
    "auth_token",
    "cookie",
    "ct0",
    "password",
    "po_token",
    "secret",
    "session",
    "token",
    "visitor_data",
    "xsec_token",
)
ALLOWED_BOOLEAN_KEYS = {
    "browser_session_used",
    "cookies_used",
    "secrets_redacted",
}


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(marker == lowered or marker in lowered for marker in SENSITIVE_MARKERS)


def redact_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return value
    changed = False
    pairs: list[tuple[str, str]] = []
    for key, item_value in parse_qsl(parsed.query, keep_blank_values=True):
        if is_sensitive_key(key):
            pairs.append((key, REDACTED))
            changed = True
        else:
            pairs.append((key, item_value))
    netloc = parsed.netloc
    if parsed.username is not None or parsed.password is not None:
        host = parsed.hostname or ""
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        netloc = f"redacted@{host}"
        changed = True
    if not changed:
        return value
    return urlunparse(parsed._replace(netloc=netloc, query=urlencode(pairs, doseq=True)))


_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b(?:authorization|auth_token|cookie|ct0|password|po_token|secret|session(?:_id)?|token|visitor_data|xsec_token)\b\s*[:=]\s*)(\[REDACTED\]|[^\s,;&)\]}'\"]+)"
)
_HEADER_RE = re.compile(r"(?im)^(\s*(?:authorization|cookie|set-cookie)\s*:\s*).+$")
_URL_RE = re.compile(r"https?://[^\s<>`\"']+")


def redact_text(value: str) -> str:
    def redact_url_match(match: re.Match[str]) -> str:
        raw = match.group(0)
        trailing = ""
        while raw and raw[-1] in ".,;:)}":
            trailing = raw[-1] + trailing
            raw = raw[:-1]
        return redact_url(raw) + trailing

    redacted = _HEADER_RE.sub(lambda match: match.group(1) + REDACTED, value)
    redacted = _ASSIGNMENT_RE.sub(lambda match: match.group(1) + REDACTED, redacted)
    return _URL_RE.sub(redact_url_match, redacted)


def sanitize_data(value: Any, *, key: str = "") -> Any:
    if key and is_sensitive_key(key) and key not in ALLOWED_BOOLEAN_KEYS:
        return REDACTED
    if isinstance(value, dict):
        return {str(child_key): sanitize_data(child, key=str(child_key)) for child_key, child in value.items()}
    if isinstance(value, list):
        return [sanitize_data(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_data(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def sanitize_command(command: list[str]) -> list[str]:
    result: list[str] = []
    redact_next = False
    for item in command:
        if redact_next:
            result.append(REDACTED)
            redact_next = False
            continue
        lowered = item.lower()
        if lowered.startswith("--") and is_sensitive_key(lowered.lstrip("-")) and "=" not in item:
            result.append(item)
            redact_next = True
            continue
        result.append(redact_text(item))
    return result


def contains_unredacted_secret(value: str) -> bool:
    return redact_text(value) != value
