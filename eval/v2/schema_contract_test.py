#!/usr/bin/env python
"""Negative tests proving evaluation v2 schemas are enforced."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from schema_validation import validate_instance


ROOT = Path(__file__).resolve().parent


def must_reject(instance: object, schema: Path, name: str, failures: list[str]) -> None:
    try:
        validate_instance(instance, schema, label=name)
    except ValueError:
        return
    failures.append(name)


def main() -> int:
    failures: list[str] = []
    input_schema = ROOT / "schemas" / "task_inputs.schema.json"
    result_schema = ROOT / "schemas" / "decision_result.schema.json"
    inputs = json.loads((ROOT / "inputs" / "tasks.json").read_text(encoding="utf-8"))
    validate_instance(inputs, input_schema, label="valid inputs")
    leaked = copy.deepcopy(inputs)
    leaked["tasks"][0]["answer_hint"] = "continue_full"
    must_reject(leaked, input_schema, "unknown answer-like input field", failures)

    result = {
        "task_id": "fixture",
        "group": "Knowledge Workflow",
        "pipeline_decision": "stop_before_audit",
        "full_report_permission": False,
        "response_mode": "degraded_explanation",
        "scope_status": "not_evaluated",
        "source_status": "source_blocked",
        "elapsed_seconds": 0.1,
        "status_schema_version": 1,
        "project_root": "fixture/project"
    }
    validate_instance(result, result_schema, label="valid result")
    for field, value in (
        ("response_mode", "invented_mode"),
        ("scope_status", "invented_scope"),
        ("elapsed_seconds", -1),
    ):
        invalid = {**result, field: value}
        must_reject(invalid, result_schema, f"invalid {field}", failures)
    extra = {**result, "answer": "stop"}
    must_reject(extra, result_schema, "unknown result field", failures)

    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("evaluation v2 schema contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
