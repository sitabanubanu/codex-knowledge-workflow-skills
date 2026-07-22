"""Shared JSON Schema enforcement for evaluation v2 inputs and results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


def read_schema(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"schema is not a JSON object: {path}")
    Draft202012Validator.check_schema(payload)
    return payload


def validate_instance(instance: Any, schema_path: Path, *, label: str) -> None:
    validator = Draft202012Validator(read_schema(schema_path))
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    if not errors:
        return
    messages = []
    for error in errors:
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        messages.append(f"{location}: {error.message}")
    raise ValueError(f"{label} failed JSON Schema validation: " + "; ".join(messages))
