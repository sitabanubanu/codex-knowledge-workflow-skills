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
STAGE_OUTPUTS = {
    "transcript_normalizer": [
        "10_video/00_source/source_status.json",
        "10_video/01_transcript/clean_transcript.jsonl",
    ],
    "transcript_segmenter": [
        "10_video/02_segments/argument_segments.json",
        "10_video/02_segments/syntax_segments.json",
    ],
    "inventory_extractor": [
        "10_video/03_inventory/claims.json",
        "10_video/03_inventory/examples.json",
        "10_video/03_inventory/concepts.json",
        "10_video/03_inventory/analogies.json",
    ],
    "source_logic_builder": [
        "10_video/04_logic/source_logic.md",
        "10_video/04_logic/logic_graph.json",
    ],
    "evidence_auditor": [
        "10_video/05_gap_check/evidence_audit.json",
        "10_video/05_gap_check/gap_check.md",
    ],
    "video_analysis_pack_builder": [
        "10_video/video_analysis_pack.md",
    ],
    "document_composer_runner": [
        "20_document/composer_intake.json",
        "20_document/commitments.md",
        "20_document/claim_map.json",
        "20_document/quality_check.md",
    ],
}


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


def expected_outputs_exist(project_root: Path, stage: str) -> bool:
    expected = STAGE_OUTPUTS.get(stage, [])
    return bool(expected) and all((project_root / item).is_file() for item in expected)


def load_run_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return read_json(path)
    except EndToEndRunnerError:
        return {}


def initialize_run_state(args: argparse.Namespace, project_root: Path, video_root: Path, document_root: Path) -> dict[str, Any]:
    return {
        "runner": RUNNER_NAME,
        "schema_version": 1,
        "mode": "local_transcript",
        "status": "running",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "project_root": str(project_root),
        "video_root": str(video_root),
        "document_root": str(document_root),
        "input_transcript": str(args.input_transcript.expanduser().resolve()) if args.input_transcript else "",
        "resume_enabled": bool(getattr(args, "resume", False)),
        "current_stage": "",
        "next_stage": "transcript_normalizer",
        "stages": [],
    }


def validate_resume_state(state: dict[str, Any], args: argparse.Namespace, project_root: Path) -> None:
    if not state:
        return
    previous_project = str(state.get("project_root") or "")
    if previous_project and Path(previous_project).expanduser().resolve() != project_root.expanduser().resolve():
        raise EndToEndRunnerError("run_state project_root does not match the requested project root")
    previous_input = str(state.get("input_transcript") or "")
    current_input = str(args.input_transcript.expanduser().resolve()) if args.input_transcript else ""
    if previous_input and Path(previous_input).expanduser().resolve() != Path(current_input).expanduser().resolve():
        raise EndToEndRunnerError("run_state input_transcript does not match the requested input transcript")


def state_stage_index(state: dict[str, Any], stage: str) -> int | None:
    stages = state.get("stages")
    if not isinstance(stages, list):
        return None
    for index, row in enumerate(stages):
        if isinstance(row, dict) and row.get("stage") == stage:
            return index
    return None


def upsert_stage(state: dict[str, Any], stage_record: dict[str, Any]) -> None:
    stages = state.setdefault("stages", [])
    if not isinstance(stages, list):
        state["stages"] = stages = []
    index = state_stage_index(state, str(stage_record.get("stage")))
    if index is None:
        stages.append(stage_record)
    else:
        stages[index] = stage_record
    state["updated_at"] = now_iso()


def write_run_state(path: Path, state: dict[str, Any]) -> None:
    write_json(path, state)


def completed_in_state(state: dict[str, Any], stage: str) -> bool:
    stages = state.get("stages")
    if not isinstance(stages, list):
        return False
    return any(
        isinstance(row, dict) and row.get("stage") == stage and row.get("status") in {"completed", "skipped"}
        for row in stages
    )


def stage_record_from_result(result: dict[str, Any], status: str) -> dict[str, Any]:
    record = stage_summary(result)
    record.update(
        {
            "status": status,
            "command": result.get("command", []),
            "completed_at": now_iso() if status == "completed" else "",
            "failed_at": now_iso() if status == "failed" else "",
            "stderr": result.get("stderr", ""),
        }
    )
    return record


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
    run_state_path = logs_root / "run_state.json"
    previous_state = load_run_state(run_state_path) if args.resume else {}
    if args.resume:
        validate_resume_state(previous_state, args, project_root)
    state = initialize_run_state(args, project_root, video_root, document_root)
    if args.resume and previous_state:
        state["created_at"] = previous_state.get("created_at") or state["created_at"]
        state["stages"] = previous_state.get("stages") if isinstance(previous_state.get("stages"), list) else []
    write_run_state(run_state_path, state)

    def run_stage(stage: str, command: list[str], cwd: Path) -> None:
        if args.resume and completed_in_state(state, stage) and expected_outputs_exist(project_root, stage):
            skipped = {
                "stage": stage,
                "returncode": 0,
                "summary": {
                    "runner": RUNNER_NAME,
                    "next_step": "resume_skipped_completed_stage",
                },
                "command": command,
                "stdout": "",
                "stderr": "",
            }
            steps.append(skipped)
            upsert_stage(
                state,
                {
                    "stage": stage,
                    "status": "skipped",
                    "returncode": 0,
                    "command": command,
                    "skipped_at": now_iso(),
                    "reason": "resume_completed_outputs_present",
                    "stderr": "",
                },
            )
            state["current_stage"] = stage
            state["next_stage"] = "next"
            write_run_state(run_state_path, state)
            write_json(logs_root / "end_to_end_steps.json", [stage_summary(step) for step in steps])
            return
        upsert_stage(
            state,
            {
                "stage": stage,
                "status": "running",
                "returncode": None,
                "command": command,
                "started_at": now_iso(),
            },
        )
        state["current_stage"] = stage
        state["next_stage"] = stage
        write_run_state(run_state_path, state)
        result = run_command(stage, command, cwd)
        steps.append(result)
        write_json(logs_root / "end_to_end_steps.json", [stage_summary(step) for step in steps])
        if result["returncode"] != 0:
            upsert_stage(state, stage_record_from_result(result, "failed"))
            state["status"] = "failed"
            state["failed_stage"] = stage
            state["error"] = result.get("stderr") or result.get("stdout")
            state["next_stage"] = stage
            write_run_state(run_state_path, state)
            raise EndToEndRunnerError(
                f"stage {stage} failed with exit code {result['returncode']}: {result.get('stderr') or result.get('stdout')}"
            )
        upsert_stage(state, stage_record_from_result(result, "completed"))
        state["next_stage"] = "next"
        write_run_state(run_state_path, state)

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
    state["status"] = "completed"
    state["current_stage"] = "document_composer_runner"
    state["next_stage"] = "draft_report_with_quality_gates"
    state["completed_at"] = now_iso()
    write_run_state(run_state_path, state)

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
        "run_state": str(run_state_path),
        "resume_enabled": bool(args.resume),
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
    parser.add_argument("--resume", action="store_true", help="Resume a previous local transcript run by skipping completed stages whose expected outputs still exist.")
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
            resume=False,
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
        run_state = read_json(project_root / "logs" / "run_state.json")
        assert_true("run state completed", run_state.get("status") == "completed", failures)

        resume_result = run_local_transcript_workflow(
            argparse.Namespace(
                input_transcript=transcript,
                project_root=project_root,
                output_base=base / "outputs",
                language="en",
                document_goal="Write an auditable source-faithful report",
                final_language="zh-CN",
                audience="workflow reviewer",
                video_skill_root=default_skill_root("knowledge-video-decomposer"),
                document_skill_root=default_skill_root("knowledge-document-composer"),
                resume=True,
            )
        )
        assert_true("resume enabled", resume_result["resume_enabled"] is True, failures)
        resume_state = read_json(project_root / "logs" / "run_state.json")
        skipped = [row for row in resume_state.get("stages", []) if row.get("status") == "skipped"]
        assert_true("resume skipped stages", len(skipped) >= 7, failures, json.dumps(resume_state, ensure_ascii=False))
        assert_true("resume skipped stderr", all("stderr" in row for row in skipped), failures)

        other_transcript = base / "other_fixture.txt"
        write_fixture_transcript(other_transcript)
        try:
            run_local_transcript_workflow(
                argparse.Namespace(
                    input_transcript=other_transcript,
                    project_root=project_root,
                    output_base=base / "outputs",
                    language="en",
                    document_goal="Write an auditable source-faithful report",
                    final_language="zh-CN",
                    audience="workflow reviewer",
                    video_skill_root=default_skill_root("knowledge-video-decomposer"),
                    document_skill_root=default_skill_root("knowledge-document-composer"),
                    resume=True,
                )
            )
        except EndToEndRunnerError:
            pass
        else:
            failures.append("resume changed input: expected EndToEndRunnerError")

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
