#!/usr/bin/env python
"""Regression tests for the knowledge workflow skill chain.

The suite is intentionally offline. It verifies the current productized paths:
local transcript end-to-end, ASR resume, Chrome probe gating, document composer
gating, and blocked-output validation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
VIDEO = REPO_ROOT / "skills" / "knowledge-video-decomposer"
CONSOLE = REPO_ROOT / "skills" / "knowledge-workflow-console"
DOCUMENT = REPO_ROOT / "skills" / "knowledge-document-composer"


class RegressionFailure(Exception):
    """Regression assertion failure."""


def run(command: list[str], *, cwd: Path, timeout: int = 180) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def run_ok(command: list[str], *, cwd: Path, timeout: int = 180) -> dict[str, Any]:
    result = run(command, cwd=cwd, timeout=timeout)
    if result["returncode"] != 0:
        raise RegressionFailure(
            f"command failed: {' '.join(command)}\nstdout:\n{result['stdout']}\nstderr:\n{result['stderr']}"
        )
    return result


def parse_last_json(stdout: str) -> dict[str, Any]:
    if not stdout:
        return {}
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = json.loads(stdout.splitlines()[-1])
    if not isinstance(payload, dict):
        raise RegressionFailure("expected JSON object output")
    return payload


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def write_json(path: Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def assert_true(name: str, condition: bool, details: str = "") -> None:
    if not condition:
        raise RegressionFailure(f"{name}: assertion failed{': ' + details if details else ''}")


def assert_eq(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise RegressionFailure(f"{name}: expected {expected!r}, got {actual!r}")


def test_local_transcript_e2e(base: Path) -> None:
    transcript = base / "local_e2e" / "fixture.txt"
    project_root = base / "local_e2e" / "project"
    write_text(
        transcript,
        "\n\n".join(
            [
                "Source Gate means confirmed primary material.",
                "For example, metadata alone cannot support speaker logic.",
                "Therefore we must preserve transcript evidence before writing reports.",
                "This creates a workflow where claims remain tied to their source.",
            ]
        )
        + "\n",
    )
    result = run_ok(
        [
            sys.executable,
            str(CONSOLE / "scripts" / "end_to_end_runner.py"),
            "--input-transcript",
            str(transcript),
            "--project-root",
            str(project_root),
            "--language",
            "en",
            "--document-goal",
            "Write an auditable report",
            "--final-language",
            "zh-CN",
        ],
        cwd=CONSOLE / "scripts",
    )
    payload = parse_last_json(result["stdout"])
    assert_eq("e2e steps", len(payload["steps"]), 7)
    assert_true("pack exists", (project_root / "10_video" / "video_analysis_pack.md").is_file())
    assert_true("composer intake exists", (project_root / "20_document" / "composer_intake.json").is_file())
    assert_true("final report not written", not (project_root / "20_document" / "final_report.md").exists())


def test_zh_cn_final_report(base: Path) -> None:
    transcript = base / "zh_cn_report" / "fixture.txt"
    project_root = base / "zh_cn_report" / "project"
    write_text(
        transcript,
        "\n\n".join(
            [
                "Source Gate means confirmed primary material.",
                "For example, metadata alone cannot support speaker logic.",
                "Therefore we must preserve transcript evidence before writing reports.",
                "This creates a workflow where claims remain tied to their source.",
            ]
        )
        + "\n",
    )
    run_ok(
        [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "run",
            "--input",
            str(transcript),
            "--project-root",
            str(project_root),
            "--mode",
            "audit",
            "--language",
            "en",
            "--final-language",
            "zh-CN",
            "--document-goal",
            "写一份中文可审计知识报告",
            "--audience",
            "中文研究型用户",
        ],
        cwd=REPO_ROOT,
        timeout=240,
    )
    final_report = project_root / "20_document" / "final_report.md"
    quality_gate = project_root / "20_document" / "quality_gate.json"
    composer_intake = project_root / "20_document" / "composer_intake.json"
    assert_true("zh final exists", final_report.is_file())
    text = final_report.read_text(encoding="utf-8")
    assert_true("zh goal preserved", "写一份中文可审计知识报告" in text)
    assert_true("zh audience preserved", "中文研究型用户" in text)
    assert_true("zh body present", "来源状态" in text and "推断" in text and "延伸" in text)
    gate = json.loads(quality_gate.read_text(encoding="utf-8"))
    assert_true("zh final approved", gate.get("approved_for_final_report") is True)
    gate_names = {item.get("gate") for item in gate.get("gates", [])}
    assert_true("language match gate present", "Language Match" in gate_names)
    intake = json.loads(composer_intake.read_text(encoding="utf-8"))
    assert_eq("zh final language intake", intake.get("final_language"), "zh-CN")
    assert_eq("zh audience intake", intake.get("audience"), "中文研究型用户")


def test_template_outputs_are_structured(base: Path) -> None:
    transcript = base / "template_outputs" / "fixture.txt"
    project_root = base / "template_outputs" / "project"
    write_text(
        transcript,
        "\n\n".join(
            [
                "Source Gate means confirmed primary material.",
                "For example, metadata alone cannot support speaker logic.",
                "Therefore we must preserve transcript evidence before writing reports.",
                "This creates a workflow where claims remain tied to their source.",
            ]
        )
        + "\n",
    )
    run_ok(
        [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "run",
            "--input",
            str(transcript),
            "--project-root",
            str(project_root),
            "--mode",
            "audit",
            "--language",
            "en",
            "--final-language",
            "en",
            "--document-goal",
            "Create reusable template outputs",
        ],
        cwd=REPO_ROOT,
        timeout=240,
    )
    listed = run_ok([sys.executable, str(REPO_ROOT / "kw.py"), "template", "--list"], cwd=REPO_ROOT)
    templates = [line.strip() for line in listed["stdout"].splitlines() if line.strip()]
    assert_true("template list includes action_plan", "action_plan" in templates)
    quality_md = project_root / "30_final" / "quality_review.md"
    quality_json = project_root / "30_final" / "quality_review.json"
    run_ok(
        [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "quality",
            "--project-root",
            str(project_root),
            "--output",
            str(quality_md),
            "--output-json",
            str(quality_json),
        ],
        cwd=REPO_ROOT,
    )
    assert_true("quality md exists", quality_md.is_file())
    assert_true("quality json exists", quality_json.is_file())
    quality = json.loads(quality_json.read_text(encoding="utf-8"))
    assert_eq("quality overall", quality.get("overall"), "pass")
    dimensions = {item.get("dimension") for item in quality.get("dimensions", [])}
    assert_true("quality source dimension", "Source faithfulness" in dimensions)
    assert_true("quality checks recorded", len(quality.get("checks", [])) >= 8)
    required_markers = {
        "study_notes": "## Core Ideas",
        "research_brief": "## Evidence-Backed Claims",
        "creator_script": "## Source-Backed Talking Points",
        "prompt_pack": "## Reusable Prompt Patterns",
        "action_plan": "## Step-By-Step Plan",
    }
    for name, marker in required_markers.items():
        run_ok(
            [
                sys.executable,
                str(REPO_ROOT / "kw.py"),
                "template",
                "--project-root",
                str(project_root),
                "--template",
                name,
            ],
            cwd=REPO_ROOT,
        )
        output = project_root / "30_final" / f"{name}.md"
        assert_true(f"{name} output exists", output.is_file())
        text = output.read_text(encoding="utf-8")
        assert_true(f"{name} marker", marker in text)
        assert_true(f"{name} no-new-claims boundary", "does not add new source claims" in text)
        assert_true(f"{name} source gate", "Source status: `source_confirmed`" in text)


def test_end_to_end_runner_self_test(base: Path) -> None:
    result = run_ok(
        [sys.executable, str(CONSOLE / "scripts" / "end_to_end_runner.py"), "--self-test"],
        cwd=CONSOLE / "scripts",
        timeout=240,
    )
    assert_true("end-to-end self-test", "self-test passed" in result["stdout"])


def test_workflow_preflight_and_status_self_tests(base: Path) -> None:
    preflight = run_ok(
        [sys.executable, str(CONSOLE / "scripts" / "workflow_preflight.py"), "--self-test"],
        cwd=CONSOLE / "scripts",
    )
    assert_true("preflight self-test", "self-test passed" in preflight["stdout"])
    status = run_ok(
        [sys.executable, str(CONSOLE / "scripts" / "workflow_status_summary.py"), "--self-test"],
        cwd=CONSOLE / "scripts",
    )
    assert_true("status self-test", "self-test passed" in status["stdout"])
    result_index = run_ok(
        [sys.executable, str(CONSOLE / "scripts" / "result_index_writer.py"), "--self-test"],
        cwd=CONSOLE / "scripts",
    )
    assert_true("result index self-test", "self-test passed" in result_index["stdout"])


def test_asr_resume(base: Path) -> None:
    root = base / "asr_resume" / "10_video"
    media = base / "asr_resume" / "fixture.mp3"
    asr_jsonl = base / "asr_resume" / "asr.jsonl"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"placeholder media")
    rows = [
        {"id": "t0001", "start": 0.0, "end": 3.0, "text": "ASR source text.", "source": "ASR", "language": "en"},
        {"id": "t0002", "start": 3.0, "end": 6.0, "text": "Evidence stays linked.", "source": "ASR", "language": "en"},
    ]
    write_text(asr_jsonl, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    result = run_ok(
        [
            sys.executable,
            str(VIDEO / "scripts" / "asr_pipeline.py"),
            "--input-media",
            str(media),
            "--asr-jsonl",
            str(asr_jsonl),
            "--output-root",
            str(root),
            "--model",
            "base",
            "--language",
            "en",
        ],
        cwd=VIDEO / "scripts",
    )
    payload = parse_last_json(result["stdout"])
    assert_eq("asr source class", payload["source_class"], "primary_audio_asr")
    status = json.loads((root / "00_source" / "source_status.json").read_text(encoding="utf-8"))
    assert_eq("status class", status["source_classes"], ["primary_audio_asr"])
    assert_true("clean transcript", (root / "01_transcript" / "clean_transcript.jsonl").is_file())


def test_chrome_url_only_gate(base: Path) -> None:
    input_json = base / "chrome_url_only" / "input.json"
    output_root = base / "chrome_url_only" / "10_video"
    write_json(
        input_json,
        {
            "source_url": "https://example.invalid/video",
            "visible_transcript_status": "not_visible",
            "page_state_observed": "opened",
            "layers": [
                {
                    "layer": "playwright_evaluate",
                    "executed": True,
                    "result": "success",
                    "public_urls": ["https://cdn.example.invalid/captions.vtt"],
                    "confirmed_public_downloadable": True,
                }
            ],
        },
    )
    result = run_ok(
        [
            sys.executable,
            str(VIDEO / "scripts" / "chrome_media_probe.py"),
            "--input-json",
            str(input_json),
            "--output-root",
            str(output_root),
        ],
        cwd=VIDEO / "scripts",
    )
    payload = parse_last_json(result["stdout"])
    assert_eq("url-only signal", payload["suggested_acquisition_signal"], "browser_derived_media_url_found")
    assert_eq("url-only not confirmed", payload["suggested_source_status"], "source_failed")
    assert_true("url-only not exported", payload["browser_derived_media_exported"] is False)


def test_chrome_probe_relative_exported_subtitle(base: Path) -> None:
    project_root = base / "chrome_exported_subtitle"
    result = run_ok(
        [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "chrome-probe",
            "--input-json",
            str(REPO_ROOT / "examples" / "chrome_probe" / "chrome_observation_exported_subtitle.json"),
            "--project-root",
            str(project_root),
        ],
        cwd=REPO_ROOT,
    )
    assert_true("chrome wrapper result index", "Result index:" in result["stdout"])
    probe_json = project_root / "10_video" / "00_source" / "chrome_media_probe.json"
    probe_md = project_root / "10_video" / "00_source" / "chrome_media_probe.md"
    assert_true("chrome probe json", probe_json.is_file())
    assert_true("chrome probe markdown", probe_md.is_file())
    payload = json.loads(probe_json.read_text(encoding="utf-8"))
    decision = payload.get("decision", {})
    assert_true("chrome relative exported", decision.get("browser_derived_media_exported") is True)
    assert_true("chrome local file resolved", bool(decision.get("local_media_files")))
    assert_true("chrome result index", (project_root / "result_index.md").is_file())


def test_chrome_probe_visible_transcript_example(base: Path) -> None:
    project_root = base / "chrome_visible_transcript"
    run_ok(
        [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "chrome-probe",
            "--input-json",
            str(REPO_ROOT / "examples" / "chrome_probe" / "chrome_observation_visible_transcript.json"),
            "--project-root",
            str(project_root),
        ],
        cwd=REPO_ROOT,
    )
    probe_json = project_root / "10_video" / "00_source" / "chrome_media_probe.json"
    payload = json.loads(probe_json.read_text(encoding="utf-8"))
    decision = payload.get("decision", {})
    assert_eq("visible transcript signal", decision.get("suggested_acquisition_signal"), "chrome_visible_transcript")
    assert_eq("visible transcript source hint", decision.get("suggested_source_status"), "source_confirmed")
    visible_layer = next(item for item in payload.get("layers", []) if item.get("layer") == "visible_transcript")
    assert_true("visible transcript local file", bool(visible_layer.get("existing_local_files")))


def test_platform_media_runner_gate(base: Path) -> None:
    result = run_ok(
        [sys.executable, str(VIDEO / "scripts" / "platform_media_runner.py"), "--self-test"],
        cwd=VIDEO / "scripts",
    )
    assert_true("platform media self-test", "self-test passed" in result["stdout"])


def test_doctor_self_test(base: Path) -> None:
    result = run_ok(
        [sys.executable, str(VIDEO / "scripts" / "doctor.py"), "--self-test"],
        cwd=VIDEO / "scripts",
    )
    assert_true("doctor self-test", "self-test passed" in result["stdout"])


def test_doctor_cli_relative_outputs(base: Path) -> None:
    work = base / "doctor_cli"
    work.mkdir(parents=True, exist_ok=True)
    result = run(
        [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "doctor",
            "--output-json",
            "doctor.json",
            "--output-md",
            "doctor.md",
            "--overwrite",
        ],
        cwd=work,
        timeout=240,
    )
    assert_true("doctor command returned diagnostic status", result["returncode"] in {0, 1})
    assert_true("doctor default summary", result["stdout"].startswith("Knowledge Workflow Doctor"))
    json_path = work / "doctor.json"
    md_path = work / "doctor.md"
    assert_true("doctor json written relative to caller", json_path.is_file())
    assert_true("doctor markdown written relative to caller", md_path.is_file())
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert_true("doctor route readiness exists", len(payload.get("route_readiness", [])) >= 3)
    assert_true("doctor markdown route table", "What You Can Try Now" in md_path.read_text(encoding="utf-8"))


def test_batch_research_outputs(base: Path) -> None:
    output_root = base / "batch_research"
    run_ok(
        [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "batch",
            "--input",
            str(REPO_ROOT / "examples" / "batch_research" / "batch_links.csv"),
            "--output-root",
            str(output_root),
        ],
        cwd=REPO_ROOT,
        timeout=240,
    )
    status_csv = output_root / "batch_status.csv"
    summary_md = output_root / "batch_summary.md"
    order_md = output_root / "recommended_watch_order.md"
    comparative_md = output_root / "comparative_report.md"
    items_json = output_root / "batch_items.json"
    assert_true("batch status csv", status_csv.is_file())
    assert_true("batch summary", summary_md.is_file())
    assert_true("batch order", order_md.is_file())
    assert_true("batch comparative", comparative_md.is_file())
    assert_true("batch items json", items_json.is_file())
    status_text = status_csv.read_text(encoding="utf-8")
    assert_true("batch status source field", "source_status" in status_text)
    assert_true("batch status quality field", "quality_gate_approved" in status_text)
    items = json.loads(items_json.read_text(encoding="utf-8"))
    assert_true("batch items count", len(items) == 2)
    assert_true("batch items approved", all(item["quality_gate_approved"] == "True" for item in items))
    assert_true("batch summary item index", "## Item Index" in summary_md.read_text(encoding="utf-8"))
    assert_true(
        "batch recommended rationale",
        "Rationale:" in order_md.read_text(encoding="utf-8"),
    )
    assert_true(
        "batch synthesis boundary",
        "Batch-level metadata is not" in comparative_md.read_text(encoding="utf-8"),
    )


def test_validate_dry_run(base: Path) -> None:
    output_root = base / "validation_plan"
    result = run_ok(
        [
            sys.executable,
            str(REPO_ROOT / "kw.py"),
            "validate",
            "--dry-run",
            "--output-root",
            str(output_root),
        ],
        cwd=REPO_ROOT,
    )
    assert_true("validate summary path", "Validation summary:" in result["stdout"])
    summary_json = output_root / "validation_summary.json"
    summary_md = output_root / "validation_summary.md"
    assert_true("validate summary json", summary_json.is_file())
    assert_true("validate summary markdown", summary_md.is_file())
    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    names = {item["name"] for item in payload.get("commands", [])}
    assert_true("validate default regression", "regression" in names)
    assert_true("validate default no live", "live_platform_smoke" not in names)
    assert_true("validate default no real asr", "asr_integration" not in names)


def test_document_composer_blocks_bad_primary_flag(base: Path) -> None:
    # Reuse the document runner self-test because it explicitly covers malformed
    # truthy primary_material_available and audit errors.
    run_ok(
        [sys.executable, str(DOCUMENT / "scripts" / "document_composer_runner.py"), "--self-test"],
        cwd=DOCUMENT / "scripts",
    )


def test_blocked_validator(base: Path) -> None:
    root = base / "blocked_validator"
    status = {
        "source_status": "secondary_only",
        "can_enter_full_decomposition": False,
        "can_enter_document_composer": True,
        "allowed_report_type": "degraded_source_report",
        "source_classes": ["firecrawl_context"],
        "primary_material_available": False,
        "status_reason": "regression fixture",
        "failed_probes": [],
        "next_step": "request_primary_transcript_audio_or_authorized_page_access",
    }
    write_json(root / "00_source" / "source_status.json", status)
    write_text(root / "video_analysis_pack.md", "# Video Analysis Pack\n\nFull source-confirmed analysis.\n")
    result = run(
        [
            sys.executable,
            str(VIDEO / "scripts" / "artifact_validator.py"),
            "--artifact-root",
            str(root),
            "--source-status-json",
            str(root / "00_source" / "source_status.json"),
        ],
        cwd=VIDEO / "scripts",
    )
    assert_true("validator should fail blocked full pack", result["returncode"] != 0)


def main() -> int:
    tests = [
        test_local_transcript_e2e,
        test_zh_cn_final_report,
        test_template_outputs_are_structured,
        test_end_to_end_runner_self_test,
        test_workflow_preflight_and_status_self_tests,
        test_asr_resume,
        test_chrome_url_only_gate,
        test_chrome_probe_relative_exported_subtitle,
        test_chrome_probe_visible_transcript_example,
        test_platform_media_runner_gate,
        test_doctor_self_test,
        test_doctor_cli_relative_outputs,
        test_batch_research_outputs,
        test_validate_dry_run,
        test_document_composer_blocks_bad_primary_flag,
        test_blocked_validator,
    ]
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="knowledge-regression-") as tmp:
        base = Path(tmp)
        for test in tests:
            try:
                test(base)
                print(f"PASS {test.__name__}")
            except Exception as exc:
                failures.append(f"{test.__name__}: {exc}")
                print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print("\nFailures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("regression suite passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
