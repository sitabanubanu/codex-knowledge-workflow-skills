"""Aggregate the search-quality experiment from worker JSON outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).resolve().parent / "search_manifest.json"


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def load_group(root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for batch in sorted(root.glob("batch-*/batch.json")):
        value = read_json(batch)
        items = value.get("tasks") if isinstance(value, dict) else None
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("task_id"):
                    rows[str(item["task_id"])] = {**item, "_file": str(batch)}
    for path in sorted(root.glob("batch-*/S-*.json")):
        value = read_json(path)
        if isinstance(value, dict) and value.get("task_id"):
            rows.setdefault(str(value["task_id"]), {**value, "_file": str(path)})
    return rows


def candidate_total(candidate: dict[str, Any]) -> int | None:
    keys = ["relevance_0_3", "depth_0_2", "reliability_0_2", "complete_material_0_2", "study_fit_0_1"]
    if not all(isinstance(candidate.get(key), (int, float)) for key in keys):
        return None
    return sum(int(candidate[key]) for key in keys)


def is_complete(candidate: dict[str, Any]) -> bool:
    access = str(candidate.get("material_access") or "")
    return access in {"full_text", "full_transcript"} and int(candidate.get("complete_material_0_2") or 0) >= 2


def is_bad(candidate: dict[str, Any]) -> bool:
    access = str(candidate.get("material_access") or "")
    return int(candidate.get("relevance_0_3") or 0) == 0 or access in {"metadata_only", "blocked", "unknown"}


def aggregate(tasks: list[dict[str, Any]], rows: dict[str, dict[str, Any]], group: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scored_tasks: list[dict[str, Any]] = []
    all_candidates: list[dict[str, Any]] = []
    elapsed: list[float] = []
    for task in tasks:
        row = rows.get(str(task["id"])) or {}
        candidates = row.get("candidates") if isinstance(row.get("candidates"), list) else []
        candidates = candidates[:5]
        scored: list[dict[str, Any]] = []
        for rank, candidate in enumerate(candidates, start=1):
            if not isinstance(candidate, dict):
                continue
            item = {**candidate, "rank": candidate.get("rank", rank)}
            item["total_score"] = candidate_total(item)
            item["valid"] = bool(item["total_score"] is not None and item["total_score"] >= 6)
            item["strong"] = bool(item["total_score"] is not None and item["total_score"] >= 8)
            item["complete_material"] = is_complete(item)
            item["bad_candidate"] = is_bad(item)
            scored.append(item)
            all_candidates.append(item)
        if isinstance(row.get("elapsed_seconds"), (int, float)):
            elapsed.append(float(row["elapsed_seconds"]))
        else:
            start = row.get("started_at")
            finish = row.get("finished_at")
            if isinstance(start, str) and isinstance(finish, str):
                from datetime import datetime
                try:
                    elapsed.append((datetime.fromisoformat(finish.replace("Z", "+00:00")) - datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds())
                except ValueError:
                    pass
        scored_tasks.append({
            "task_id": task["id"],
            "group": group,
            "candidate_count": len(scored),
            "valid_count": sum(bool(c["valid"]) for c in scored),
            "strong_in_top3": any(bool(c["strong"]) for c in scored[:3]),
            "complete_count": sum(bool(c["complete_material"]) for c in scored),
            "bad_count": sum(bool(c["bad_candidate"]) for c in scored),
            "elapsed_seconds": row.get("elapsed_seconds") if isinstance(row.get("elapsed_seconds"), (int, float)) else None,
            "candidates": scored,
            "output_file": str(row.get("_file") or "missing"),
        })
    denominator = len(tasks) * 5
    summary = {
        "group": group,
        "task_count": len(tasks),
        "tasks_with_five_candidates": sum(t["candidate_count"] == 5 for t in scored_tasks),
        "average_valid_candidates_top5": sum(t["valid_count"] for t in scored_tasks) / len(tasks) if tasks else None,
        "top3_with_strong_match_rate": sum(bool(t["strong_in_top3"]) for t in scored_tasks) / len(tasks) if tasks else None,
        "complete_original_material_rate": sum(bool(c["complete_material"]) for c in all_candidates) / denominator if denominator else None,
        "irrelevant_or_unobtainable_rate": sum(bool(c["bad_candidate"]) for c in all_candidates) / denominator if denominator else None,
        "average_processing_time_seconds": sum(elapsed) / len(elapsed) if elapsed else None,
        "candidate_denominator": denominator,
        "candidate_rows_recorded": len(all_candidates),
        "timed_tasks": len(elapsed),
    }
    return summary, scored_tasks


def pct(value: Any) -> str:
    return "—" if value is None else f"{float(value) * 100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ordinary-root", type=Path, required=True)
    parser.add_argument("--workflow-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    manifest = read_json(MANIFEST)
    tasks = manifest.get("tasks") if isinstance(manifest, dict) and isinstance(manifest.get("tasks"), list) else []
    ordinary_summary, ordinary_tasks = aggregate(tasks, load_group(args.ordinary_root), "普通 Agent")
    workflow_summary, workflow_tasks = aggregate(tasks, load_group(args.workflow_root), "Knowledge Workflow")
    result = {
        "evaluation_id": manifest.get("evaluation_id") if isinstance(manifest, dict) else None,
        "protocol": "search-quality-10x5",
        "ordinary": ordinary_summary,
        "workflow": workflow_summary,
        "task_scores": ordinary_tasks + workflow_tasks,
        "caveats": [
            "A candidate is valid at score >= 6 and strong at score >= 8, using the frozen 10-point rubric.",
            "complete_original_material_rate counts only explicit full_text/full_transcript checks; unknown is not treated as complete.",
            "The machine score is a screening result; final résumé numbers should include a blinded human review of source relevance and depth.",
        ],
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# KW-SEARCH-20260715 自动评分",
        "",
        "| 指标 | 普通 Agent | Knowledge Workflow |",
        "|---|---:|---:|",
        f"| 前5平均有效候选数 | {ordinary_summary['average_valid_candidates_top5']:.2f} | {workflow_summary['average_valid_candidates_top5']:.2f} |",
        f"| 前3至少一个强匹配 | {pct(ordinary_summary['top3_with_strong_match_rate'])} | {pct(workflow_summary['top3_with_strong_match_rate'])} |",
        f"| 可获得完整原始材料 | {pct(ordinary_summary['complete_original_material_rate'])} | {pct(workflow_summary['complete_original_material_rate'])} |",
        f"| 明显不相关或无法获取 | {pct(ordinary_summary['irrelevant_or_unobtainable_rate'])} | {pct(workflow_summary['irrelevant_or_unobtainable_rate'])} |",
        f"| 平均处理时间 | {ordinary_summary['average_processing_time_seconds']:.1f}s | {workflow_summary['average_processing_time_seconds']:.1f}s |",
        "",
        "候选分数、可获取性和逐任务明细见同目录 `summary.json`。",
    ]
    (args.output_root / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(args.output_root / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
