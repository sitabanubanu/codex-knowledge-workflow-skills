#!/usr/bin/env python
"""Orchestrate the local transcript-to-document knowledge workflow."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNNER_NAME = "knowledge-workflow-end-to-end-runner"


class EndToEndRunnerError(Exception):
    """Expected CLI-facing end-to-end runner failure."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_json(payload: dict[str, Any], *, pretty: bool, stream: Any = sys.stdout) -> None:
    stream.write(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty))
    stream.write("\n")


def stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_text(path: Path, text: str) -> dict[str, Any]:
    target = path.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    temp_path = target.parent / f".{target.name}.{os.getpid()}.tmp"
    temp_path.write_bytes(data)
    os.replace(temp_path, target)
    if target.read_bytes() != data:
        raise EndToEndRunnerError(f"readback mismatch after writing {target}")
    return {"path": str(target), "bytes": len(data), "encoding": "utf-8"}


def write_json(path: Path, payload: Any) -> dict[str, Any]:
    return write_text(path, stable_json(payload))


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise EndToEndRunnerError(f"invalid JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise EndToEndRunnerError(f"could not read JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise EndToEndRunnerError(f"JSON file is not an object: {path}")
    return payload


def default_skill_root(skill_name: str) -> Path:
    return Path.home() / ".codex" / "skills" / skill_name


def script_path(skill_root: Path, name: str) -> Path:
    path = skill_root / "scripts" / name
    if not path.is_file():
        raise EndToEndRunnerError(f"required stage script is missing: {path}")
    return path


def run_command(stage: str, command: list[str], cwd: Path) -> dict[str, Any]:
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
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    payload: dict[str, Any] | None = None
    if stdout:
        try:
            loaded = json.loads(stdout.splitlines()[-1] if len(stdout.splitlines()) > 1 else stdout)
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = None
    result = {
        "stage": stage,
        "command": command,
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "summary": payload,
    }
    if completed.returncode != 0:
        raise EndToEndRunnerError(f"stage {stage} failed with exit code {completed.returncode}: {stderr or stdout}")
    return result


def stage_summary(result: dict[str, Any]) -> dict[str, Any]:
    summary = result.get("summary")
    slim: dict[str, Any] = {
        "stage": result.get("stage"),
        "returncode": result.get("returncode"),
    }
    if isinstance(summary, dict):
        for key in (
            "runner",
            "source_status",
            "next_step",
            "validation_next_step",
            "composer_decision",
            "final_report_written",
            "pack_path",
            "document_root",
            "output_root",
        ):
            if key in summary:
                slim[key] = summary[key]
    return slim


def make_project_id(input_path: Path) -> str:
    stem = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in input_path.stem).strip("-_")
    return stem[:60] or "knowledge-workflow"


def resolve_roots(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.project_root:
        project_root = args.project_root.expanduser().resolve()
    else:
        if args.input_transcript is None:
            raise EndToEndRunnerError("--input-transcript is required when --project-root is omitted")
        base = args.output_base.expanduser().resolve()
        project_root = base / make_project_id(args.input_transcript.expanduser().resolve())
    return project_root, project_root / "10_video", project_root / "20_document"


def ensure_no_final_report(document_root: Path) -> None:
    if (document_root / "final_report.md").exists():
        raise EndToEndRunnerError("document runner unexpectedly left final_report.md in place")


def run_local_transcript_workflow(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_transcript is None:
        raise EndToEndRunnerError("--input-transcript is required for local-transcript mode")

    video_skill_root = args.video_skill_root.expanduser().resolve()
    document_skill_root = args.document_skill_root.expanduser().resolve()
    project_root, video_root, document_root = resolve_roots(args)
    logs_root = project_root / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []

    def run_stage(stage: str, command: list[str], cwd: Path) -> None:
        result = run_command(stage, command, cwd)
        steps.append(result)
        write_json(logs_root / "end_to_end_steps.json", [stage_summary(step) for step in steps])

    video_scripts = video_skill_root / "scripts"
    document_scripts = document_skill_root / "scripts"
    py = sys.executable

    run_stage(
        "transcript_normalizer",
        [
            py,
            str(script_path(video_skill_root, "transcript_normalizer.py")),
            "--input",
            str(args.input_transcript.expanduser().resolve()),
            "--output-root",
            str(video_root),
            "--language",
            args.language,
        ],
        video_scripts,
    )
    run_stage(
        "transcript_segmenter",
        [py, str(script_path(video_skill_root, "transcript_segmenter.py")), "--output-root", str(video_root)],
        video_scripts,
    )
    run_stage(
        "inventory_extractor",
        [py, str(script_path(video_skill_root, "inventory_extractor.py")), "--output-root", str(video_root)],
        video_scripts,
    )
    run_stage(
        "source_logic_builder",
        [py, str(script_path(video_skill_root, "source_logic_builder.py")), "--output-root", str(video_root)],
        video_scripts,
    )
    run_stage(
        "evidence_auditor",
        [py, str(script_path(video_skill_root, "evidence_auditor.py")), "--output-root", str(video_root)],
        video_scripts,
    )
    run_stage(
        "video_analysis_pack_builder",
        [py, str(script_path(video_skill_root, "video_analysis_pack_builder.py")), "--output-root", str(video_root)],
        video_scripts,
    )
    run_stage(
        "document_composer_runner",
        [
            py,
            str(script_path(document_skill_root, "document_composer_runner.py")),
            "--video-root",
            str(video_root),
            "--document-root",
            str(document_root),
            "--document-goal",
            args.document_goal,
            "--final-language",
            args.final_language,
            "--audience",
            args.audience,
        ],
        document_scripts,
    )
    ensure_no_final_report(document_root)

    summary = {
        "runner": RUNNER_NAME,
        "mode": "local_transcript",
        "generated_at": now_iso(),
        "project_root": str(project_root),
        "video_root": str(video_root),
        "document_root": str(document_root),
        "steps": [stage_summary(step) for step in steps],
        "video_analysis_pack": str(video_root / "video_analysis_pack.md"),
        "composer_intake": str(document_root / "composer_intake.json"),
        "final_report_written": False,
        "next_step": "draft_report_with_quality_gates",
    }
    write_json(logs_root / "end_to_end_summary.json", summary)
    return summary


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local transcript through the knowledge workflow.")
    parser.add_argument("--input-transcript", type=Path, default=None, help="Local transcript/subtitle file.")
    parser.add_argument("--project-root", type=Path, default=None, help="Project root containing 10_video and 20_document.")
    parser.add_argument("--output-base", type=Path, default=Path("outputs") / "knowledge-workflow", help="Base output directory when project-root is omitted.")
    parser.add_argument("--language", default="unknown", help="Transcript language label.")
    parser.add_argument("--document-goal", default="source-faithful knowledge report", help="Document goal passed to document composer.")
    parser.add_argument("--final-language", default="current conversation language", help="Final report language instruction.")
    parser.add_argument("--audience", default="reader who needs an auditable source-faithful explanation", help="Intended audience.")
    parser.add_argument("--video-skill-root", type=Path, default=default_skill_root("knowledge-video-decomposer"), help="knowledge-video-decomposer skill root.")
    parser.add_argument("--document-skill-root", type=Path, default=default_skill_root("knowledge-document-composer"), help="knowledge-document-composer skill root.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print summary JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in tests.")
    return parser


def assert_true(name: str, condition: bool, failures: list[str], details: str = "") -> None:
    if not condition:
        failures.append(f"{name}: assertion failed{': ' + details if details else ''}")


def write_fixture_transcript(path: Path) -> None:
    write_text(
        path,
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


def run_self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="knowledge-e2e-") as tmp:
        base = Path(tmp)
        transcript = base / "fixture.txt"
        project_root = base / "project"
        write_fixture_transcript(transcript)
        args = argparse.Namespace(
            input_transcript=transcript,
            project_root=project_root,
            output_base=base / "outputs",
            language="en",
            document_goal="Write an auditable source-faithful report",
            final_language="zh-CN",
            audience="workflow reviewer",
            video_skill_root=default_skill_root("knowledge-video-decomposer"),
            document_skill_root=default_skill_root("knowledge-document-composer"),
        )
        result = run_local_transcript_workflow(args)
        assert_true("project root", Path(result["project_root"]).is_dir(), failures)
        assert_true("video pack exists", (project_root / "10_video" / "video_analysis_pack.md").is_file(), failures)
        assert_true("composer intake exists", (project_root / "20_document" / "composer_intake.json").is_file(), failures)
        assert_true("final not written", not (project_root / "20_document" / "final_report.md").exists(), failures)
        assert_true("seven steps", len(result["steps"]) == 7, failures)
        intake = read_json(project_root / "20_document" / "composer_intake.json")
        assert_true("composer full decision", intake.get("composer_decision") == "full", failures)
        audit = read_json(project_root / "10_video" / "05_gap_check" / "evidence_audit.json")
        assert_true("audit no errors", audit.get("severity_counts", {}).get("error") == 0, failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("self-test passed")
    return 0


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    try:
        summary = run_local_transcript_workflow(args)
    except EndToEndRunnerError as exc:
        emit_json(
            {
                "runner": RUNNER_NAME,
                "error": "end_to_end_runner_failed",
                "message": str(exc),
            },
            pretty=args.pretty,
            stream=sys.stderr,
        )
        return 1

    emit_json(summary, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
