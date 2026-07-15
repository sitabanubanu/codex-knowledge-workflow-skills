"""Run a source-grounded pilot review for the 10 complete materials."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from score_minimum import load_ordinary, quote_supported, source_text_for  # noqa: E402


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def workflow_rows(root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    path = root / "results.jsonl"
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("task_id"):
            rows[str(value["task_id"])] = value
    return rows


def task_manifest() -> dict[str, dict[str, Any]]:
    value = read_json(HERE / "manifest.json")
    tasks = value.get("tasks") if isinstance(value, dict) else []
    return {str(task["id"]): task for task in tasks if isinstance(task, dict) and task.get("id")}


def report_text_for_workflow(root: Path, task_id: str) -> str:
    path = root / task_id / "project" / "20_document" / "final_report.md"
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def report_text_for_ordinary(row: dict[str, Any]) -> str:
    return str(row.get("report_markdown") or "")


def claim_coverage(report: str, claims: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
    text = norm(report)
    details: list[dict[str, Any]] = []
    matched = 0
    for claim in claims:
        terms = [norm(term) for term in claim.get("terms") or [] if norm(term)]
        hits = [term for term in terms if term in text]
        # This is deliberately a screening proxy, not a semantic adjudication.
        threshold = max(1, (len(terms) + 1) // 2)
        ok = len(hits) >= threshold
        if ok:
            matched += 1
        details.append({"claim_id": claim.get("id"), "matched": ok, "term_hits": hits, "term_count": len(terms)})
    return matched, details


def structure_score(report: str) -> int:
    text = norm(report)
    return sum(marker in text for marker in ("source", "inference", "extension"))


def workflow_evidence(row: dict[str, Any]) -> tuple[int, int, int, str]:
    summary = row.get("claim_audit_summary") if isinstance(row.get("claim_audit_summary"), dict) else {}
    total = int(summary.get("claims") or 0)
    traceable = int(summary.get("claims_with_transcript_span") or 0)
    return total, traceable, max(0, total - traceable), "built-in claim audit"


def ordinary_evidence(row: dict[str, Any], task: dict[str, Any]) -> tuple[int, int, int, str]:
    claims = row.get("claims") if isinstance(row.get("claims"), list) else []
    source = source_text_for(task)
    total = traceable = 0
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        total += 1
        if quote_supported(source, claim.get("quote_or_null")):
            traceable += 1
    return total, traceable, max(0, total - traceable), "quote check"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-root", type=Path, required=True)
    parser.add_argument("--ordinary-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    gold = read_json(HERE / "fidelity_gold.json") or {}
    gold_claims = gold.get("claims") if isinstance(gold.get("claims"), dict) else {}
    manifest = task_manifest()
    wf = workflow_rows(args.workflow_root)
    ordinary = load_ordinary(args.ordinary_root)
    task_rows: list[dict[str, Any]] = []
    for task_id in gold.get("source_set") or []:
        task = manifest.get(task_id, {"id": task_id})
        claims = gold_claims.get(task_id) if isinstance(gold_claims.get(task_id), list) else []
        wf_row = wf.get(task_id, {})
        ordinary_row = ordinary.get(task_id, {})
        wf_report = report_text_for_workflow(args.workflow_root, task_id)
        ordinary_report = report_text_for_ordinary(ordinary_row)
        wf_matched, wf_details = claim_coverage(wf_report, claims)
        ord_matched, ord_details = claim_coverage(ordinary_report, claims)
        wf_total, wf_trace, wf_unsupported, wf_method = workflow_evidence(wf_row)
        ord_total, ord_trace, ord_unsupported, ord_method = ordinary_evidence(ordinary_row, task)
        task_rows.extend([
            {
                "task_id": task_id,
                "group": "Knowledge Workflow",
                "report_exists": bool(wf_report.strip()),
                "gold_claims": len(claims),
                "gold_claims_covered_proxy": wf_matched,
                "gold_coverage_proxy": wf_matched / len(claims) if claims else None,
                "claim_total": wf_total,
                "traceable_claims": wf_trace,
                "unsupported_claims": wf_unsupported,
                "traceability_rate": wf_trace / wf_total if wf_total else None,
                "source_inference_extension_sections": structure_score(wf_report),
                "evidence_method": wf_method,
                "coverage_details": wf_details,
            },
            {
                "task_id": task_id,
                "group": "普通 Agent",
                "report_exists": bool(ordinary_report.strip()),
                "gold_claims": len(claims),
                "gold_claims_covered_proxy": ord_matched,
                "gold_coverage_proxy": ord_matched / len(claims) if claims else None,
                "claim_total": ord_total,
                "traceable_claims": ord_trace,
                "unsupported_claims": ord_unsupported,
                "traceability_rate": ord_trace / ord_total if ord_total else None,
                "source_inference_extension_sections": structure_score(ordinary_report),
                "evidence_method": ord_method,
                "coverage_details": ord_details,
            },
        ])

    groups: dict[str, dict[str, Any]] = {}
    for group in ("普通 Agent", "Knowledge Workflow"):
        rows = [row for row in task_rows if row["group"] == group]
        coverage = [row["gold_coverage_proxy"] for row in rows if row["gold_coverage_proxy"] is not None]
        claims = sum(row["claim_total"] for row in rows)
        trace = sum(row["traceable_claims"] for row in rows)
        groups[group] = {
            "task_count": len(rows),
            "report_exists_rate": sum(bool(row["report_exists"]) for row in rows) / len(rows) if rows else None,
            "gold_coverage_proxy": sum(coverage) / len(coverage) if coverage else None,
            "traceability_rate": trace / claims if claims else None,
            "unsupported_claim_rate": (claims - trace) / claims if claims else None,
            "average_section_presence": sum(row["source_inference_extension_sections"] for row in rows) / len(rows) if rows else None,
            "human_usability_score": None,
        }
    result = {
        "protocol": gold.get("protocol"),
        "groups": groups,
        "task_rows": task_rows,
        "caveats": [
            "Gold coverage is a term-matching screening proxy and is not a substitute for a blinded human semantic review.",
            "The Workflow claim-audit denominator excludes tasks that could not reach report composition, such as KW-04 and KW-05.",
            "Human usability is intentionally left null until 2–3 independent reviewers score the blinded reports.",
        ],
    }
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# KW-FIDELITY-20260715 自动预审",
        "",
        "| 指标 | 普通 Agent | Knowledge Workflow |",
        "|---|---:|---:|",
    ]
    for key, label in [("report_exists_rate", "报告存在率"), ("gold_coverage_proxy", "核心观点覆盖代理"), ("traceability_rate", "结论可回溯率"), ("unsupported_claim_rate", "无依据结论率")]:
        left = groups["普通 Agent"].get(key)
        right = groups["Knowledge Workflow"].get(key)
        if left is None or right is None:
            lines.append(f"| {label} | — | — |")
        else:
            lines.append(f"| {label} | {float(left) * 100:.1f}% | {float(right) * 100:.1f}% |")
    lines += [
        "",
        "这是一轮机器辅助预审；人工可用性和语义正确性仍需盲审。",
    ]
    (args.output_root / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(args.output_root / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
