#!/usr/bin/env python
"""Audit a learning article against provenance, structure, and pedagogy gates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from learning_common import LearningPipelineError, read_json, read_text, validate_learning_receipt, write_json


RUNNER_NAME = "knowledge-learning-article-auditor"


def gate(name: str, status: str, evidence: str, revision: str = "") -> dict[str, str]:
    return {"gate": name, "status": status, "evidence": evidence, "required_revision": revision}


def contains_any(text: str, terms: list[str]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def audit_learning_article(project_root: Path, candidate: Path | None = None) -> dict[str, Any]:
    state = validate_learning_receipt(project_root)
    pack = read_json(state["learning_pack_path"])
    candidate_path = (candidate or state["project_root"] / "20_document" / "learning_article_candidate.md").expanduser().resolve()
    article = read_text(candidate_path, required=True)
    language = str(pack.get("request", {}).get("final_language") or "zh-CN").lower()
    zh = language.startswith("zh") or "chinese" in language
    gates: list[dict[str, str]] = []

    gates.append(gate("Provenance", "pass", "Current gate, analysis receipt, and learning receipt hashes match."))

    reanalysis = pack.get("source_reanalysis") if isinstance(pack.get("source_reanalysis"), dict) else {}
    reanalysis_validation = state.get("source_reanalysis_validation") if isinstance(state.get("source_reanalysis_validation"), dict) else {}
    if reanalysis.get("mode") == "evidence_bound":
        reanalysis_visible = contains_any(article[:1000], ["证据重分析", "evidence-bound reanalysis"])
        if not reanalysis_validation.get("approved_for_learning_analysis") or not reanalysis_visible:
            gates.append(
                gate(
                    "Evidence-bound reanalysis",
                    "block",
                    f"Validation approved={reanalysis_validation.get('approved_for_learning_analysis')}; visible={reanalysis_visible}",
                    "Bind every Source reconstruction to admitted evidence and disclose reanalysis near the opening.",
                )
            )
        else:
            gates.append(
                gate(
                    "Evidence-bound reanalysis",
                    "pass",
                    f"Validated {reanalysis_validation.get('rows_checked', 0)} reconstructed Source rows against {reanalysis.get('source_artifact', '')}.",
                )
            )
    else:
        gates.append(gate("Evidence-bound reanalysis", "pass", "Normal mode uses complete upstream semantic inventory."))

    learning_boundary_visible = contains_any(article[:1600], ["学习设计边界", "learning-design boundary"])
    if not learning_boundary_visible:
        gates.append(
            gate(
                "Learning synthesis boundary",
                "block",
                "The opening does not distinguish Agent learning synthesis from source statements.",
                "Disclose that relationships, priorities, prerequisites, transfer methods, and practice steps are Inference or Extension.",
            )
        )
    else:
        gates.append(
            gate(
                "Learning synthesis boundary",
                "pass",
                "The article visibly distinguishes source-grounded content from Agent learning synthesis.",
            )
        )

    partial = bool(pack.get("partial_scope"))
    partial_visible = contains_any(article[:600], ["部分范围", "partial scope"])
    if partial and not partial_visible:
        gates.append(gate("Source scope", "block", "Partial source status is not visible near the opening.", "Add a visible Partial Scope / 部分范围 label and do not fill missing source sequence."))
    else:
        gates.append(gate("Source scope", "pass", "Source scope is compatible with the article opening."))

    required_zh = ["值得学什么", "知识地图", "学习顺序", "关键例子", "怎样学习", "Source / Inference / Extension", "原文定位"]
    required_en = ["worth learning", "knowledge map", "learning order", "key examples", "how to learn", "source / inference / extension", "source location"]
    required = required_zh if zh else required_en
    missing = [term for term in required if term.lower() not in article.lower()]
    if missing:
        gates.append(gate("Template coverage", "block", f"Missing required article functions: {missing}", "Add the missing learning-article sections."))
    else:
        gates.append(gate("Template coverage", "pass", "All required learning-article functions are present."))

    concepts = [row for row in pack.get("knowledge_map", {}).get("concepts", []) if isinstance(row, dict)]
    concept_terms = [str(row.get("term")) for row in concepts if row.get("term")]
    missing_concepts = [term for term in concept_terms if term not in article]
    if concepts and missing_concepts:
        gates.append(gate("Knowledge structure", "block", f"Concepts omitted from article: {missing_concepts}", "Explain every selected concept or lower its inclusion priority in the learning pack."))
    elif not concepts:
        gates.append(gate("Knowledge structure", "block", "No validated concepts are available.", "Repair upstream inventory or run declared evidence-bound source reanalysis."))
    else:
        gates.append(gate("Knowledge structure", "pass", f"Article covers {len(concepts)} validated concept nodes."))

    headings = re.findall(r"^#{1,6}\s+(.+)$", article, flags=re.MULTILINE)
    timestamp_headings = [heading for heading in headings if re.match(r"^\s*(?:\d{1,2}:){1,2}\d{2}", heading)]
    if timestamp_headings:
        gates.append(gate("Semantic organization", "block", f"Timestamp-led headings found: {timestamp_headings}", "Use semantic concept or argument headings; keep timestamps only as evidence locators."))
    else:
        gates.append(gate("Semantic organization", "pass", "No timestamp-led headings were found."))

    examples = [row for row in pack.get("examples", []) if isinstance(row, dict)]
    missing_examples = [str(row.get("name")) for row in examples if row.get("name") and str(row.get("name")) not in article]
    example_function_visible = contains_any(article, ["为什么引入", "它支持什么", "why it appears", "what it supports"])
    examples_outcome = str(reanalysis.get("inventory_outcomes", {}).get("examples") or "") if isinstance(reanalysis.get("inventory_outcomes"), dict) else ""
    if not examples and examples_outcome != "none_identified_in_source":
        gates.append(gate("Example completeness", "block", "No validated examples or explicit none-in-source outcome are available.", "Repair upstream example extraction or declare and justify none_identified_in_source during evidence-bound reanalysis."))
    elif missing_examples or (examples and not example_function_visible):
        gates.append(gate("Example completeness", "block", f"Missing examples: {missing_examples}; example function visible: {example_function_visible}", "Explain what each important example is, why it appears, how it works, and what it supports."))
    else:
        gates.append(gate("Example completeness", "pass", f"All {len(examples)} registered examples retain their instructional role."))

    path = pack.get("learning_path") if isinstance(pack.get("learning_path"), dict) else {}
    first_action = str(path.get("first_action") or "")
    check_question = str(path.get("check_question") or "")
    if not first_action or not check_question or first_action not in article or check_question not in article:
        gates.append(gate("Actionability", "block", "First action or understanding check is missing from the final prose.", "Include the exact first action and focused check from learning_path.json."))
    else:
        gates.append(gate("Actionability", "pass", "Article contains a concrete first action and understanding check."))

    if not contains_any(article, ["Source：", "Source:"]) or not contains_any(article, ["Inference：", "Inference:"]) or not contains_any(article, ["Extension：", "Extension:"]):
        gates.append(gate("Source / Inference / Extension", "block", "Evidence categories are not all visible.", "Explain Source, Inference, and Extension boundaries explicitly."))
    else:
        gates.append(gate("Source / Inference / Extension", "pass", "All evidence categories are visible."))

    if zh:
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", article))
        ratio = cjk_count / max(1, len(article))
        mojibake = contains_any(article, ["锛", "鈥", "鏉ユ簮", "璇佹嵁", "鍐呭"])
        if ratio < 0.12 or mojibake:
            gates.append(gate("Language and encoding", "block", f"Chinese ratio={ratio:.3f}; mojibake={mojibake}", "Write the article in valid UTF-8 Chinese and remove mojibake."))
        else:
            gates.append(gate("Language and encoding", "pass", f"Chinese ratio={ratio:.3f}; no known mojibake markers found."))
    else:
        gates.append(gate("Language and encoding", "pass", "Requested non-Chinese output is present."))

    if len(article.strip()) < 900:
        gates.append(gate("Learning depth", "block", f"Article length is only {len(article.strip())} characters.", "Add enough explanation to connect concepts, examples, reasoning, and learning actions."))
    elif not pack.get("enrichment_present") and pack.get("request", {}).get("depth") in {"standard", "deep"}:
        gates.append(gate("Learning depth", "warn", "Article uses the conservative baseline because no Agent enrichment was supplied.", "For the strongest result, add evidence-grounded relationships, prerequisites, transfer patterns, and learning priorities in learning_enrichment.json."))
    else:
        gates.append(gate("Learning depth", "pass", "Article depth and enrichment level are compatible with the request."))

    blocking = [row["gate"] for row in gates if row["status"] == "block"]
    warnings = [row["gate"] for row in gates if row["status"] == "warn"]
    return {
        "schema_version": "learning-quality-gate.v1",
        "runner": RUNNER_NAME,
        "project_root": str(state["project_root"]),
        "candidate": str(candidate_path),
        "source_status": pack.get("source_status"),
        "partial_scope": partial,
        "approved_for_learning_article": not blocking,
        "gates": gates,
        "blocking_gates": blocking,
        "warning_gates": warnings,
        "files_checked": [
            str(state["learning_pack_path"]),
            str(state["learning_receipt_path"]),
            str(state["source_reanalysis_validation_path"]),
            str(candidate_path),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a learning article candidate.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = audit_learning_article(args.project_root, args.candidate)
    except LearningPipelineError as exc:
        print(json.dumps({"runner": RUNNER_NAME, "error": str(exc)}, ensure_ascii=False))
        return 1
    output = args.output or args.project_root / "20_document" / "learning_quality_gate.json"
    write_json(output.expanduser().resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["approved_for_learning_article"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
