#!/usr/bin/env python
"""Regression tests for the console-to-learning handoff."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from kw_cli import main as kw_main


REPO_ROOT = Path(__file__).resolve().parents[1]
LEARNING_SCRIPTS = REPO_ROOT / "skills" / "knowledge-learning-article" / "scripts"
CONSOLE_SCRIPTS = REPO_ROOT / "skills" / "knowledge-workflow-console" / "scripts"
sys.path.insert(0, str(LEARNING_SCRIPTS))
sys.path.insert(0, str(CONSOLE_SCRIPTS))

from learning_pipeline_runner import write_fixture  # noqa: E402
from workflow_provenance import inspect_provenance  # noqa: E402


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def test_request_is_bound_to_admitted_transcript(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-learning-handoff-") as tmp:
        root = Path(tmp)
        write_fixture(root)
        (root / "15_learning" / "learning_enrichment.json").unlink()
        request_path = kw_main.prepare_learning_enrichment_request(
            project_root=root,
            learning_goal="Understand the source-gated workflow.",
            audience="test learner",
            learner_level="beginner",
            final_language="en",
            depth="standard",
        )
        request = kw_main.read_json(request_path)
        source = request.get("admitted_source_artifact") or {}
        issues = request.get("detected_upstream_issues") or []
        assert_true(
            "learning request binds the gate-admitted normalized transcript",
            source.get("path") == "10_video/01_transcript/clean_transcript.jsonl"
            and bool(source.get("sha256"))
            and int(source.get("bytes") or 0) > 0,
            failures,
        )
        assert_true("learning request preserves the heuristic safety finding", "argument_segments_heuristic" in issues, failures)
        assert_true(
            "standard learning cannot silently continue without Agent enrichment",
            kw_main.install_learning_enrichment(root, None) is None,
            failures,
        )


def test_kw_learn_runs_and_enrichment_tamper_invalidates_provenance(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-learning-command-") as tmp:
        root = Path(tmp)
        write_fixture(root)
        completed = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "kw.py"),
                "learn",
                "--project-root",
                str(root),
                "--final-language",
                "zh-CN",
                "--depth",
                "standard",
            ],
            cwd=str(REPO_ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=180,
            check=False,
        )
        assert_true(
            "kw learn production command succeeds with valid Agent enrichment",
            completed.returncode == 0,
            failures,
        )
        assert_true(
            "kw learn writes the approved final article and receipt",
            (root / "20_document" / "learning_article.md").is_file()
            and (root / "20_document" / "learning_article_receipt.json").is_file(),
            failures,
        )
        assert_true(
            "learning article provenance is current after kw learn",
            inspect_provenance(root)["learning_article_current"],
            failures,
        )
        enrichment = root / "15_learning" / "learning_enrichment.json"
        enrichment.write_text(enrichment.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        assert_true(
            "changing Agent enrichment invalidates learning provenance",
            not inspect_provenance(root)["learning_article_current"],
            failures,
        )


def main() -> int:
    failures: list[str] = []
    test_request_is_bound_to_admitted_transcript(failures)
    test_kw_learn_runs_and_enrichment_tamper_invalidates_provenance(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_learning_console_handoff passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
