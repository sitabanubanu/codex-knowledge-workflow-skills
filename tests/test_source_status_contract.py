#!/usr/bin/env python
"""Table-driven tests for the canonical SourceStatus v1 contract."""

from __future__ import annotations

import copy
import tempfile
from pathlib import Path

from kw_cli import ingest, source_status_contract


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def manifest(*, status: str, target: str = "video_content", artifacts: list[dict] | None = None) -> dict:
    return {
        "schema_version": 2,
        "status": status,
        "acquisition_layer": "fixture",
        "active_backend": "fixture",
        "run_id": "run_fixture",
        "attempt_id": "attempt_fixture",
        "bundle_id": "bundle_fixture",
        "source_id": "source_fixture",
        "source_fingerprint": "fingerprint_fixture",
        "analysis_target": target,
        "operation": "extract_transcript" if target == "video_content" else "read",
        "artifacts": artifacts or [],
        "failures": [],
        "next_action": "ingest_bundle",
    }


def artifact(*, artifact_type: str, scope: str, source_class: str = "primary") -> dict:
    return {
        "path": f"artifacts/fixture.{artifact_type}",
        "type": artifact_type,
        "content_scope": scope,
        "source_class": source_class,
    }


def build(value: dict, state: str) -> dict:
    return source_status_contract.build_source_status(
        value,
        state,
        gate_input_sha256="a" * 64,
    )


def test_state_matrix(failures: list[str]) -> None:
    cases = [
        (
            "confirmed",
            manifest(status="material_acquired", artifacts=[artifact(artifact_type="transcript", scope="video_transcript")]),
            "source_confirmed",
            "matched",
            "continue_full",
        ),
        (
            "partial",
            manifest(status="partial_material_acquired", artifacts=[artifact(artifact_type="transcript", scope="video_transcript", source_class="partial_primary")]),
            "source_partial",
            "partial_match",
            "continue_partial",
        ),
        (
            "target mismatch",
            manifest(status="material_acquired", artifacts=[artifact(artifact_type="page_text", scope="article_body")]),
            "degraded_report_only",
            "target_mismatch",
            "stop_before_audit",
        ),
        (
            "pending ASR",
            manifest(status="material_acquired", artifacts=[artifact(artifact_type="audio", scope="media")]),
            "degraded_report_only",
            "pending_derivation",
            "stop_before_audit",
        ),
        (
            "secondary",
            manifest(status="secondary_only", artifacts=[artifact(artifact_type="metadata", scope="metadata", source_class="metadata_only")]),
            "secondary_only",
            "not_evaluated",
            "stop_before_audit",
        ),
        ("blocked", manifest(status="blocked"), "source_blocked", "not_evaluated", "stop_before_audit"),
        ("failed", manifest(status="failed"), "source_failed", "not_evaluated", "stop_before_audit"),
        ("unsupported", manifest(status="unsupported"), "degraded_report_only", "not_evaluated", "stop_before_audit"),
    ]
    for name, value, state, scope, decision in cases:
        status = build(value, state)
        assert_true(f"{name}: valid", not source_status_contract.validate_source_status(status), failures)
        assert_true(f"{name}: scope", status.get("scope_status") == scope, failures)
        assert_true(f"{name}: decision", status.get("pipeline_decision") == decision, failures)
        assert_true(f"{name}: failed probes list", isinstance(status.get("failed_probes"), list), failures)


def test_invalid_combinations(failures: list[str]) -> None:
    valid = build(
        manifest(status="material_acquired", artifacts=[artifact(artifact_type="transcript", scope="video_transcript")]),
        "source_confirmed",
    )
    missing = copy.deepcopy(valid)
    missing.pop("failed_probes")
    assert_true(
        "missing failed_probes rejected",
        any("missing required fields" in item for item in source_status_contract.validate_source_status(missing)),
        failures,
    )
    contradictory = copy.deepcopy(valid)
    contradictory["can_enter_full_decomposition"] = False
    assert_true(
        "contradictory confirmed permissions rejected",
        bool(source_status_contract.validate_source_status(contradictory)),
        failures,
    )
    mismatch = copy.deepcopy(valid)
    mismatch["scope_status"] = "target_mismatch"
    assert_true(
        "confirmed target mismatch rejected",
        bool(source_status_contract.validate_source_status(mismatch)),
        failures,
    )

    blocked = build(manifest(status="blocked"), "source_blocked")
    blocked_composer = copy.deepcopy(blocked)
    blocked_composer["can_enter_document_composer"] = True
    assert_true(
        "blocked composer permission rejected",
        bool(source_status_contract.validate_source_status(blocked_composer)),
        failures,
    )
    blocked_primary = copy.deepcopy(blocked)
    blocked_primary["primary_material_available"] = True
    assert_true(
        "blocked primary-material flag rejected",
        bool(source_status_contract.validate_source_status(blocked_primary)),
        failures,
    )
    blocked_report = copy.deepcopy(blocked)
    blocked_report["allowed_report_type"] = "full_video_analysis_pack"
    assert_true(
        "blocked full-report type rejected",
        bool(source_status_contract.validate_source_status(blocked_report)),
        failures,
    )
    confirmed_report = copy.deepcopy(valid)
    confirmed_report["allowed_report_type"] = "degraded_source_report"
    assert_true(
        "confirmed degraded-report type rejected",
        bool(source_status_contract.validate_source_status(confirmed_report)),
        failures,
    )


def test_atomic_writer_preserves_valid_status(failures: list[str]) -> None:
    valid = build(
        manifest(status="material_acquired", artifacts=[artifact(artifact_type="transcript", scope="video_transcript")]),
        "source_confirmed",
    )
    with tempfile.TemporaryDirectory(prefix="kw-source-status-contract-") as tmp:
        source_root = Path(tmp) / "00_source"
        ingest.write_source_status(source_root, valid)
        original = ingest.read_json(source_root / "source_status.json")
        invalid = copy.deepcopy(valid)
        invalid.pop("failed_probes")
        try:
            ingest.write_source_status(source_root, invalid)
        except source_status_contract.SourceStatusContractError:
            pass
        else:
            failures.append("invalid atomic write should raise")
        assert_true(
            "invalid atomic write preserves previous status",
            ingest.read_json(source_root / "source_status.json") == original,
            failures,
        )


def main() -> int:
    failures: list[str] = []
    test_state_matrix(failures)
    test_invalid_combinations(failures)
    test_atomic_writer_preserves_valid_status(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_source_status_contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
