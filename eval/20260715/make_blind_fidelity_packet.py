"""Build a deterministic blind packet for independent report reviewers."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from score_minimum import load_ordinary  # noqa: E402


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def source_path(task_id: str) -> Path:
    mapping = {
        "KW-01": ROOT / "tests/fixtures/transcript_sample.txt",
        "KW-02": ROOT / "tests/fixtures/subtitle_sample.srt",
        "KW-03": ROOT / "tests/fixtures/subtitle_sample.vtt",
        "KW-04": ROOT / "tests/fixtures/asr_sample.jsonl",
        "KW-05": ROOT / "tests/fixtures/asr_sample.jsonl",
        "KW-06": ROOT / "README.md",
        "KW-07": ROOT / "README.zh-CN.md",
        "KW-08": ROOT / "docs/architecture.md",
        "KW-09": ROOT / "docs/agent-reach-integration-guide.md",
        "KW-10": ROOT / "docs/output-quality-standard.md",
    }
    return mapping[task_id]


def main() -> int:
    output = ROOT / "test_outputs/eval_20260715/fidelity_blind"
    output.mkdir(parents=True, exist_ok=True)
    gold = read_json(HERE / "fidelity_gold.json") or {}
    claims = gold.get("claims") if isinstance(gold.get("claims"), dict) else {}
    ordinary = load_ordinary(ROOT / "test_outputs/eval_20260715/ordinary_v2_normalized")
    workflow: dict[str, dict[str, Any]] = {}
    for line in (ROOT / "test_outputs/eval_20260715/workflow_v2/results.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("task_id"):
            workflow[str(value["task_id"])] = value

    entries: list[dict[str, Any]] = []
    mapping: dict[str, dict[str, str]] = {}
    rng = random.Random(20260715)
    for task_id in gold.get("source_set") or []:
        report_items = [
            ("ordinary", str((ordinary.get(task_id) or {}).get("report_markdown") or "")),
            ("workflow", ""),
        ]
        report_path = ROOT / f"test_outputs/eval_20260715/workflow_v2/{task_id}/project/20_document/final_report.md"
        if report_path.is_file():
            report_items[1] = ("workflow", report_path.read_text(encoding="utf-8", errors="replace"))
        rng.shuffle(report_items)
        blind_ids = []
        for index, (group, report) in enumerate(report_items, start=1):
            blind_id = f"{task_id}-R{index}"
            blind_ids.append(blind_id)
            entries.append({
                "blind_id": blind_id,
                "task_id": task_id,
                "source_file": str(source_path(task_id).resolve()),
                "report_markdown": report if report.strip() else "[NO REPORT WAS DELIVERED]",
                "gold_core_claims": claims.get(task_id) or [],
                "review_instruction": "Score core coverage, omissions/limits, unsupported factual claims, fact-vs-inference separation, and usability. Cite short evidence for every nontrivial score.",
            })
            mapping[blind_id] = {"task_id": task_id, "group": group}
    (output / "review_packet.json").write_text(json.dumps({"protocol": "blind-report-review", "entries": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (output / "mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(output / "review_packet.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
