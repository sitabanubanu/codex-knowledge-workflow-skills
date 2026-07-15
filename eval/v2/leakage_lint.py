#!/usr/bin/env python
"""Fail when neutral evaluation inputs expose gold labels or answer hints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs" / "tasks.json"

FORBIDDEN_KEYS = {
    "class",
    "expected_action",
    "expected_decision",
    "gold",
    "material_status",
    "learning_goal",
    "pipeline_decision",
    "scope_status",
    "full_report_permission",
    "response_mode",
}

FORBIDDEN_PHRASES = {
    "must_stop",
    "reject article text",
    "reject a video transcript",
    "reject post text",
    "respond to a failed acquisition",
    "secondary explanation",
    "acquisition outcome note",
}


def walk(value: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_KEYS:
                findings.append(f"{path}.{key}: forbidden key")
            findings.extend(walk(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(walk(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        folded = value.casefold()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in folded:
                findings.append(f"{path}: forbidden phrase {phrase!r}")
    return findings


def main() -> int:
    payload = json.loads(INPUTS.read_text(encoding="utf-8"))
    findings = walk(payload)
    for path in sorted((ROOT / "inputs" / "materials").glob("*")):
        if not path.is_file():
            continue
        folded = path.read_text(encoding="utf-8", errors="replace").casefold()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in folded:
                findings.append(f"{path.relative_to(ROOT)}: forbidden phrase {phrase!r}")
    if findings:
        print("Evaluation input leakage detected:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print(f"leakage lint passed: {len(payload.get('tasks') or [])} neutral tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
