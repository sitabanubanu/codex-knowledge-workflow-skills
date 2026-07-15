"""Aggregate the independent blind-review JSON files."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REVIEW_ROOT = ROOT / "test_outputs/eval_20260715/fidelity_blind"


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def load_reviews() -> dict[str, dict[str, dict[str, Any]]]:
    reviewers: dict[str, dict[str, dict[str, Any]]] = {}
    for directory in sorted(REVIEW_ROOT.glob("reviewer-*")):
        files = list(directory.glob("reviewer.json")) + list(directory.glob("review.json"))
        if not files:
            continue
        value = read_json(files[0])
        items = value.get("reviews") if isinstance(value, dict) else value
        if isinstance(items, list):
            reviewers[directory.name] = {str(item["blind_id"]): item for item in items if isinstance(item, dict) and item.get("blind_id")}
    return reviewers


def mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def main() -> int:
    mapping = read_json(REVIEW_ROOT / "mapping.json") or {}
    reviewers = load_reviews()
    by_group: dict[str, list[dict[str, Any]]] = {"普通 Agent": [], "Knowledge Workflow": []}
    for reviewer_rows in reviewers.values():
        for blind_id, row in reviewer_rows.items():
            info = mapping.get(blind_id) or {}
            group = info.get("group")
            if group in by_group:
                by_group[group].append(row)

    groups: dict[str, dict[str, Any]] = {}
    for group, rows in by_group.items():
        groups[group] = {
            "review_count": len(rows),
            "report_exists_rate": mean([1.0 if row.get("report_exists") else 0.0 for row in rows]),
            "core_coverage_rate": mean([float(row.get("core_coverage_rate")) for row in rows if isinstance(row.get("core_coverage_rate"), (int, float))]),
            "unsupported_claim_count_mean": mean([float(row.get("unsupported_claim_count")) for row in rows if isinstance(row.get("unsupported_claim_count"), (int, float))]),
            "important_omissions_mean": mean([float(len(row.get("important_omissions") or [])) for row in rows]),
            "fact_inference_separation_mean": mean([float(row.get("fact_inference_separation")) for row in rows if isinstance(row.get("fact_inference_separation"), (int, float))]),
            "usability_mean": mean([float(row.get("usability")) for row in rows if isinstance(row.get("usability"), (int, float))]),
            "overall_fidelity_mean": mean([float(row.get("overall_fidelity")) for row in rows if isinstance(row.get("overall_fidelity"), (int, float))]),
        }

    pair_diffs: list[float] = []
    pair_exact: list[float] = []
    blind_ids = sorted({blind_id for rows in reviewers.values() for blind_id in rows})
    for blind_id in blind_ids:
        ratings = [float(rows[blind_id].get("overall_fidelity")) for rows in reviewers.values() if blind_id in rows and isinstance(rows[blind_id].get("overall_fidelity"), (int, float))]
        for left in range(len(ratings)):
            for right in range(left + 1, len(ratings)):
                pair_diffs.append(abs(ratings[left] - ratings[right]))
                pair_exact.append(1.0 if ratings[left] == ratings[right] else 0.0)

    result = {
        "reviewers_found": sorted(reviewers),
        "entries_reviewed": sum(len(rows) for rows in reviewers.values()),
        "groups": groups,
        "inter_rater": {
            "pair_count": len(pair_diffs),
            "mean_absolute_overall_fidelity_difference": mean(pair_diffs),
            "exact_agreement_rate": mean(pair_exact),
        },
        "caveats": [
            "This is a model-assisted blind review, not a substitute for independent human reviewers.",
            "Averages include the no-report outcome for tasks that did not reach composition.",
            "Semantic coverage and unsupported-claim counts depend on reviewer judgment and evidence notes.",
        ],
    }
    (REVIEW_ROOT / "final_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# KW-FIDELITY-20260715 盲审汇总",
        "",
        "| 指标 | 普通 Agent | Knowledge Workflow |",
        "|---|---:|---:|",
    ]
    for key, label in [("report_exists_rate", "报告存在率"), ("core_coverage_rate", "核心观点覆盖率"), ("unsupported_claim_count_mean", "平均无依据结论数"), ("important_omissions_mean", "平均重要遗漏数"), ("fact_inference_separation_mean", "事实/推断区分"), ("usability_mean", "可用性"), ("overall_fidelity_mean", "总体忠实度")]:
        left = groups["普通 Agent"].get(key)
        right = groups["Knowledge Workflow"].get(key)
        lines.append(f"| {label} | {'—' if left is None else f'{float(left):.2f}'} | {'—' if right is None else f'{float(right):.2f}'} |")
    agreement = result["inter_rater"]["exact_agreement_rate"]
    agreement_text = "—" if agreement is None else f"{float(agreement) * 100:.1f}%"
    lines += [
        "",
        f"评审者：{', '.join(sorted(reviewers)) or '—'}；盲条目数：{result['entries_reviewed']}。",
        f"总体忠实度精确一致率：{agreement_text}。",
        "",
        "详细证据与逐条评分见 `final_summary.json` 以及各 reviewer 子目录。",
    ]
    (REVIEW_ROOT / "final_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(REVIEW_ROOT / "final_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
