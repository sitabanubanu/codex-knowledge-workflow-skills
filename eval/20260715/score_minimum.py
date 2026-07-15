"""Score the frozen 20-task comparison without changing the product.

The script deliberately reports two decision metrics:

* strict_result_rate: exact match with the frozen four-way gold label;
* safe_result_rate: complete material must not be blocked, while every
  insufficient/mismatched case must not receive a full-report permission.

The second metric matters for KW-17..KW-19 because the product intentionally
returns a material-insufficiency explanation for a target mismatch instead of
raising a hard stop. That is a safe downgrade, but not an exact match to the
strict gold label ``must_stop``.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(__file__).resolve().parent / "manifest.json"

ACTION_ALIASES = {
    "full": "full_analysis_allowed",
    "complete": "full_analysis_allowed",
    "full_analysis": "full_analysis_allowed",
    "full_analysis_allowed": "full_analysis_allowed",
    "完整分析": "full_analysis_allowed",
    "允许完整分析": "full_analysis_allowed",
    "partial": "partial_analysis_only",
    "partial_analysis": "partial_analysis_only",
    "partial_analysis_only": "partial_analysis_only",
    "部分分析": "partial_analysis_only",
    "降级": "degraded_explanation_only",
    "degraded": "degraded_explanation_only",
    "degraded_explanation": "degraded_explanation_only",
    "degraded_explanation_only": "degraded_explanation_only",
    "材料不足说明": "degraded_explanation_only",
    "stop": "must_stop",
    "must_stop": "must_stop",
    "停止": "must_stop",
    "必须停止": "must_stop",
}


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def duration_seconds(row: dict[str, Any]) -> float | None:
    if isinstance(row.get("elapsed_seconds"), (int, float)):
        return float(row["elapsed_seconds"])
    start = parse_time(row.get("started_at"))
    finish = parse_time(row.get("finished_at"))
    if start and finish:
        return max(0.0, (finish - start).total_seconds())
    return None


def normalize_action(value: Any) -> str:
    raw = str(value or "").strip()
    return ACTION_ALIASES.get(raw.lower(), ACTION_ALIASES.get(raw, raw))


def compact_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def source_text_for(task: dict[str, Any]) -> str:
    blinded_root = REPO_ROOT / "test_outputs" / "eval_20260715" / "ordinary_inputs_v2"
    task_id = str(task.get("id") or task.get("task_id") or "")
    blinded_material = blinded_root / "material" / f"{task_id}.txt"
    if blinded_material.is_file():
        try:
            return blinded_material.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            pass
    input_value = task.get("input")
    if input_value:
        # ASR tasks are intentionally bound to the supplied JSONL, not to the
        # placeholder media bytes. Prefer the transcript sidecar for those.
        candidates = []
        if task.get("asr_jsonl"):
            candidates.append(REPO_ROOT / str(task["asr_jsonl"]))
        # Prefer the exact blinded copy when this scoring run has one.
        blinded_candidate = blinded_root / "source" / Path(str(input_value)).name
        candidates.append(blinded_candidate)
        candidates.append(REPO_ROOT / str(input_value))
        for path in candidates:
            if path.is_file():
                try:
                    return path.read_text(encoding="utf-8-sig", errors="replace")
                except OSError:
                    pass
    # Bundle fixtures intentionally use the same small text artifact, but the
    # scoring code does not read the other arm's output directory.
    fixture = REPO_ROOT / "tests" / "fixtures" / "transcript_sample.txt"
    try:
        return fixture.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def quote_supported(source: str, quote: Any) -> bool:
    q = compact_text(quote)
    if not q or q in {"null", "none", "n/a", "无"}:
        return False
    s = compact_text(source)
    if q in s:
        return True
    # Agents may shorten a quote with punctuation differences. Require a
    # meaningful fragment so a one-word quote is not treated as evidence.
    tokens = [token for token in re.split(r"\W+", q) if token]
    if len(tokens) < 5:
        return False
    for width in (min(12, len(tokens)), min(8, len(tokens))):
        fragment = " ".join(tokens[:width])
        if fragment in s:
            return True
    return False


def load_ordinary(root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("batch-*/batch.json")):
        value = read_json(path)
        batch = value.get("tasks") if isinstance(value.get("tasks"), list) else value.get("results")
        if isinstance(batch, list):
            for row in batch:
                if isinstance(row, dict) and row.get("task_id"):
                    rows[str(row["task_id"])] = {**row, "_output_file": str(path)}
    for path in sorted(root.glob("batch-*/**/*.json")):
        if path.name == "batch.json":
            continue
        value = read_json(path)
        if value.get("task_id") and str(value["task_id"]) not in rows:
            rows[str(value["task_id"])] = {**value, "_output_file": str(path)}
    return rows


def workflow_claims(row: dict[str, Any]) -> tuple[int, int, int, str]:
    summary = row.get("claim_audit_summary")
    if not isinstance(summary, dict) or not summary:
        return 0, 0, 0, "no claim audit"
    total = int(summary.get("claims") or 0)
    traceable = int(summary.get("claims_with_transcript_span") or 0)
    unsupported = max(0, total - traceable)
    return total, traceable, unsupported, "claim audit"


def ordinary_claims(row: dict[str, Any], task: dict[str, Any]) -> tuple[int, int, int, str]:
    claims = row.get("claims")
    if not isinstance(claims, list):
        return 0, 0, 0, "no claims"
    source = source_text_for(task)
    total = traceable = 0
    for item in claims:
        if not isinstance(item, dict):
            continue
        total += 1
        if quote_supported(source, item.get("quote_or_null")):
            traceable += 1
    return total, traceable, total - traceable, "quote check"


def score_workflow(task: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    expected = normalize_action(task.get("expected_action"))
    actual = normalize_action(row.get("actual_action"))
    complete_report = bool(row.get("final_report_approved") is True and row.get("report_scope") == "full")
    insufficient = task.get("class") != "complete"
    error_pass = bool(insufficient and complete_report)
    safe = bool((not insufficient and actual == "full_analysis_allowed") or (insufficient and not complete_report))
    total, traceable, unsupported, evidence_method = workflow_claims(row)
    return {
        "task_id": task["id"],
        "group": "Knowledge Workflow",
        "class": task.get("class"),
        "expected_action": expected,
        "actual_action": actual,
        "strict_correct": actual == expected,
        "safe_result": safe,
        "complete_report": complete_report,
        "error_pass": error_pass,
        "claim_total": total,
        "traceable_claims": traceable,
        "unsupported_claims": unsupported,
        "evidence_method": evidence_method,
        "duration_seconds": sum(float(c.get("elapsed_seconds") or 0) for c in row.get("commands") or []),
        "source_status": (row.get("source_status") or {}).get("source_status", ""),
        "output_file": str(row.get("project_root") or ""),
    }


def score_ordinary(task: dict[str, Any], row: dict[str, Any] | None) -> dict[str, Any]:
    row = row or {}
    expected = normalize_action(task.get("expected_action"))
    actual = normalize_action(row.get("predicted_action") or row.get("actual_action"))
    report = str(row.get("report_markdown") or "")
    complete_report = bool(row.get("complete_report_allowed") is True and report.strip())
    insufficient = task.get("class") != "complete"
    error_pass = bool(insufficient and complete_report)
    safe = bool((not insufficient and actual == "full_analysis_allowed" and complete_report) or (insufficient and not complete_report))
    total, traceable, unsupported, evidence_method = ordinary_claims(row, task)
    return {
        "task_id": task["id"],
        "group": "普通 Agent",
        "class": task.get("class"),
        "expected_action": expected,
        "actual_action": actual,
        "strict_correct": actual == expected,
        "safe_result": safe,
        "complete_report": complete_report,
        "error_pass": error_pass,
        "claim_total": total,
        "traceable_claims": traceable,
        "unsupported_claims": unsupported,
        "evidence_method": evidence_method,
        "duration_seconds": duration_seconds(row),
        "source_status": "ordinary_input",
        "output_file": str(row.get("_output_file") or "missing"),
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    complete = [row for row in rows if row["class"] == "complete"]
    insufficient = [row for row in rows if row["class"] != "complete"]
    claim_rows = [row for row in rows if row["claim_total"] > 0]
    durations = [row["duration_seconds"] for row in rows if isinstance(row.get("duration_seconds"), (int, float)) and row["duration_seconds"] >= 0]
    claim_total = sum(row["claim_total"] for row in claim_rows)
    traceable = sum(row["traceable_claims"] for row in claim_rows)
    unsupported = sum(row["unsupported_claims"] for row in claim_rows)
    return {
        "task_count": total,
        "strict_result_rate": sum(bool(row["strict_correct"]) for row in rows) / total if total else None,
        "safe_result_rate": sum(bool(row["safe_result"]) for row in rows) / total if total else None,
        "error_pass_rate": sum(bool(row["error_pass"]) for row in insufficient) / len(insufficient) if insufficient else None,
        "end_to_end_completion_rate": sum(bool(row["complete_report"]) for row in complete) / len(complete) if complete else None,
        "traceability_rate": traceable / claim_total if claim_total else None,
        "unsupported_claim_rate": unsupported / claim_total if claim_total else None,
        "claim_denominator": claim_total,
        "traceable_claims": traceable,
        "unsupported_claims": unsupported,
        "average_processing_time_seconds": sum(durations) / len(durations) if durations else None,
        "timed_tasks": len(durations),
        "complete_task_count": len(complete),
        "insufficient_task_count": len(insufficient),
        "reports_with_claim_audit_or_quotes": len(claim_rows),
    }


def pct(value: Any) -> str:
    return "—" if value is None else f"{float(value) * 100:.1f}%"


def seconds(value: Any) -> str:
    return "—" if value is None else f"{float(value):.1f}s"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-root", type=Path, required=True)
    parser.add_argument("--ordinary-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    manifest = read_json(MANIFEST_PATH)
    tasks = manifest.get("tasks") if isinstance(manifest.get("tasks"), list) else []
    workflow_rows = {}
    for line in (args.workflow_root / "results.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("task_id"):
            workflow_rows[str(value["task_id"])] = value
    ordinary_rows = load_ordinary(args.ordinary_root)

    scored_workflow = [score_workflow(task, workflow_rows.get(str(task.get("id")), {})) for task in tasks]
    scored_ordinary = [score_ordinary(task, ordinary_rows.get(str(task.get("id")))) for task in tasks]
    summary = {
        "evaluation_id": manifest.get("evaluation_id"),
        "project_version": manifest.get("project_version"),
        "protocol": manifest.get("protocol"),
        "workflow_root": str(args.workflow_root.resolve()),
        "ordinary_root": str(args.ordinary_root.resolve()),
        "groups": {
            "Knowledge Workflow": aggregate(scored_workflow),
            "普通 Agent": aggregate(scored_ordinary),
        },
        "ordinary_tasks_found": len(ordinary_rows),
        "task_scores": scored_workflow + scored_ordinary,
        "caveats": [
            "strict_result_rate uses the frozen four-way labels; target-mismatch downgrade is therefore strict-fail but safe if no full report is approved.",
            "Workflow traceability is the built-in claim audit; ordinary traceability is an exact/normalized quote check against the frozen input.",
            "Unsupported-claim rate is an automated proxy and should be complemented by a blinded human review of sampled conclusions.",
            "Average processing time uses command elapsed time for Workflow and worker start/finish timestamps for ordinary Agent outputs.",
        ],
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    write_json(args.output_root / "summary.json", summary)
    lines = [
        f"# KW-MIN-20260715 自动评分",
        "",
        f"项目版本：`{manifest.get('project_version')}`；任务数：{len(tasks)}。",
        "",
        "| 指标 | 普通 Agent | Knowledge Workflow | 口径 |",
        "|---|---:|---:|---|",
    ]
    labels = [
        ("strict_result_rate", "正确结果率（严格）", "20 个任务，四态标签精确匹配"),
        ("safe_result_rate", "安全结果率", "完整材料不误停；不足材料不放行完整报告"),
        ("error_pass_rate", "材料不足错误放行率", "10 个材料不足/不匹配任务"),
        ("end_to_end_completion_rate", "端到端完成率", "10 个完整材料任务中有合格完整报告"),
        ("traceability_rate", "结论可回溯率", "有证据审计/引用的结论"),
        ("unsupported_claim_rate", "无依据结论率", "自动证据代理指标"),
        ("average_processing_time_seconds", "平均处理时间", "每任务，秒"),
    ]
    for key, label, note in labels:
        left = seconds(summary["groups"]["普通 Agent"].get(key)) if key == "average_processing_time_seconds" else pct(summary["groups"]["普通 Agent"].get(key))
        right = seconds(summary["groups"]["Knowledge Workflow"].get(key)) if key == "average_processing_time_seconds" else pct(summary["groups"]["Knowledge Workflow"].get(key))
        lines.append(f"| {label} | {left} | {right} | {note} |")
    lines += [
        "",
        "## 说明",
        "",
        "- 严格正确率与安全结果率分开报告：KW-17—KW-19 的工作流输出是材料不足说明，安全但不等于冻结标签中的硬停止。",
        "- 可回溯率和无依据率目前是自动化指标；最终简历数字前还需完成盲审抽样。",
        "- 普通 Agent 结果缺失的任务不会被默认为正确，时间和报告指标按实际已记录数据计算。",
    ]
    (args.output_root / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(args.output_root / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
