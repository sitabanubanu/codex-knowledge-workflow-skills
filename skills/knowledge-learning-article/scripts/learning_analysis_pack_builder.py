#!/usr/bin/env python
"""Build a provenance-bound learning analysis pack from audited source artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from learning_common import (
    LearningPipelineError,
    compact,
    copy_provenance,
    evidence_refs,
    first_text,
    list_items,
    now_iso,
    read_json,
    read_text,
    sha256_file,
    validate_upstream,
    write_json,
    write_text,
)
from learning_source_reanalysis_validator import validate_source_reanalysis


RUNNER_NAME = "knowledge-learning-analysis-pack-builder"
CLAIM_CATEGORY = {
    "source_claim": "Source",
    "inferred_claim": "Inference",
    "uncertain_claim": "Inference",
    "extension_claim": "Extension",
}


def mapping(value: Any) -> dict[str, dict[str, Any]]:
    if isinstance(value, dict):
        return {str(key): row for key, row in value.items() if isinstance(row, dict)}
    if isinstance(value, list):
        return {str(row.get("id")): row for row in value if isinstance(row, dict) and row.get("id")}
    return {}


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def source_framing_map(enrichment: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = enrichment.get("source_framing")
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("field")): row
        for row in rows
        if isinstance(row, dict) and str(row.get("field") or "").strip()
    }


def merge_agent_rows(upstream: list[dict[str, Any]], agent_value: Any, kind: str) -> list[dict[str, Any]]:
    """Merge Agent-authored concepts/examples without impersonating upstream IDs."""

    rows = [dict(row) for row in upstream if isinstance(row, dict)]
    positions = {
        str(row.get("id")): index
        for index, row in enumerate(rows)
        if str(row.get("id") or "").strip()
    }
    if not isinstance(agent_value, list):
        return rows

    required_prefix = f"agent_{kind}_"
    for item in agent_value:
        if not isinstance(item, dict):
            continue
        row_id = str(item.get("id") or "").strip()
        if not row_id:
            raise LearningPipelineError(f"Agent-authored {kind} rows require an id")
        if row_id in positions:
            merged = dict(rows[positions[row_id]])
            merged.update(item)
            rows[positions[row_id]] = merged
            continue
        if not row_id.startswith(required_prefix):
            raise LearningPipelineError(
                f"new Agent-authored {kind} id must start with {required_prefix}: {row_id}"
            )
        positions[row_id] = len(rows)
        rows.append(dict(item))
    return rows


def evidence_category(item: dict[str, Any], extra: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    requested = first_text(extra.get("category"), item.get("category"))
    if requested not in {"Source", "Inference", "Extension"}:
        requested = "Source" if evidence else "Inference"
    return "Inference" if requested == "Source" and not evidence else requested


def derive_core_question(segments: list[dict[str, Any]], enrichment: dict[str, Any]) -> str:
    explicit = first_text(enrichment.get("core_question"))
    if explicit:
        return explicit
    preferred = ("question", "problem", "tension", "setup", "opening")
    for role in preferred:
        for segment in segments:
            if role in str(segment.get("role") or "").lower():
                return first_text(segment.get("title"), segment.get("summary"))
    if segments:
        return first_text(segments[0].get("title"), segments[0].get("summary"))
    return "这份材料试图解决什么问题？"


def build_claims(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for claim in claims:
        claim_type = str(claim.get("claim_type") or "uncertain_claim")
        rows.append(
            {
                "id": str(claim.get("id") or f"claim_{len(rows) + 1:03d}"),
                "text": first_text(claim.get("text"), default="未提供声明文本。"),
                "category": CLAIM_CATEGORY.get(claim_type, "Inference"),
                "claim_type": claim_type,
                "confidence": str(claim.get("confidence") or "medium"),
                "evidence": evidence_refs(claim),
            }
        )
    return rows


def build_concepts(
    concepts: list[dict[str, Any]],
    examples: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    enrichment: dict[str, Any],
) -> list[dict[str, Any]]:
    concepts = merge_agent_rows(concepts, enrichment.get("concepts"), "concept")
    examples = merge_agent_rows(examples, enrichment.get("examples"), "example")
    enrich_map = mapping(enrichment.get("concept_enrichment"))
    example_by_concept: dict[str, list[str]] = {}
    for example in examples:
        for concept_id in string_list(example.get("linked_concept_ids")):
            example_by_concept.setdefault(concept_id, []).append(str(example.get("id") or ""))

    rows: list[dict[str, Any]] = []
    for index, concept in enumerate(concepts, start=1):
        concept_id = str(concept.get("id") or f"concept_{index:03d}")
        extra = enrich_map.get(concept_id, {})
        definition = first_text(concept.get("definition_in_source"), concept.get("definition"), concept.get("notes"))
        why = first_text(
            extra.get("why_it_matters"),
            concept.get("why_it_matters"),
            default=(f"它帮助理解来源中的核心主张：{claims[0]['text']}" if claims else "它是理解材料结构的重要节点。"),
        )
        relationships = (
            extra.get("relationships")
            if isinstance(extra.get("relationships"), list)
            else concept.get("relationships")
            if isinstance(concept.get("relationships"), list)
            else []
        )
        prerequisites = string_list(extra.get("prerequisites")) or string_list(concept.get("prerequisites"))
        linked_claim_ids = (
            string_list(extra.get("source_claim_ids"))
            or string_list(concept.get("source_claim_ids"))
            or string_list(concept.get("linked_claim_ids"))
        )
        evidence = evidence_refs(concept)
        rows.append(
            {
                "id": concept_id,
                "term": first_text(concept.get("term"), concept.get("name"), default=f"概念 {index}"),
                "definition": definition or "原始材料没有给出完整定义，需要在文章中显式标注这一缺口。",
                "why_it_matters": why,
                "priority": str(extra.get("priority") or concept.get("priority") or ("core" if index <= 5 else "supporting")),
                "prerequisites": prerequisites,
                "relationships": relationships,
                "linked_example_ids": (
                    string_list(extra.get("linked_example_ids"))
                    or string_list(concept.get("linked_example_ids"))
                    or example_by_concept.get(concept_id, [])
                ),
                "source_claim_ids": linked_claim_ids,
                "learning_notes": first_text(extra.get("learning_notes"), concept.get("learning_notes")),
                "support_rationale": first_text(concept.get("support_rationale")),
                "category": evidence_category(concept, extra, evidence),
                "evidence": evidence,
            }
        )
    return rows


def build_examples(examples: list[dict[str, Any]], enrichment: dict[str, Any]) -> list[dict[str, Any]]:
    examples = merge_agent_rows(examples, enrichment.get("examples"), "example")
    enrich_map = mapping(enrichment.get("example_enrichment"))
    rows: list[dict[str, Any]] = []
    for index, example in enumerate(examples, start=1):
        example_id = str(example.get("id") or f"example_{index:03d}")
        extra = enrich_map.get(example_id, {})
        linked_claims = (
            string_list(extra.get("source_claim_ids"))
            or string_list(example.get("source_claim_ids"))
            or string_list(example.get("linked_claim_ids"))
        )
        demonstration = first_text(extra.get("what_it_supports"), example.get("what_it_supports"), example.get("what_it_demonstrates"))
        evidence = evidence_refs(example)
        rows.append(
            {
                "id": example_id,
                "name": first_text(example.get("name"), default=f"例子 {index}"),
                "what_it_is": first_text(extra.get("what_it_is"), example.get("what_it_is"), example.get("description"), default="原始材料中的具体例子。"),
                "why_introduced": first_text(extra.get("why_introduced"), example.get("why_introduced"), demonstration, default="用于把抽象观点落到具体情境。"),
                "how_it_works": first_text(extra.get("how_it_works"), example.get("how_it_works")),
                "what_it_supports": demonstration or "需要结合相邻声明判断其论证作用。",
                "role": str(extra.get("role") or example.get("role") or ("foundational" if linked_claims else "illustrative")),
                "source_claim_ids": linked_claims,
                "support_rationale": first_text(example.get("support_rationale")),
                "category": evidence_category(example, extra, evidence),
                "evidence": evidence,
            }
        )
    return rows


def build_argument_graph(
    segments: list[dict[str, Any]], logic_graph: dict[str, Any], enrichment: dict[str, Any]
) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    agent_nodes = enrichment.get("argument_nodes")
    using_agent_nodes = isinstance(agent_nodes, list) and any(isinstance(row, dict) for row in agent_nodes)
    source_nodes = agent_nodes if using_agent_nodes else segments
    for index, segment in enumerate(source_nodes, start=1):
        if not isinstance(segment, dict):
            continue
        node_id = str(segment.get("id") or (f"agent_argument_{index:03d}" if using_agent_nodes else f"segment_{index:03d}"))
        if using_agent_nodes and not node_id.startswith("agent_argument_"):
            raise LearningPipelineError(f"new Agent-authored argument id must start with agent_argument_: {node_id}")
        evidence = evidence_refs(segment)
        nodes.append(
            {
                "id": node_id,
                "role": str(segment.get("role") or "development"),
                "title": first_text(segment.get("title"), default=f"论证步骤 {index}"),
                "summary": first_text(segment.get("summary"), segment.get("description")),
                "source_claim_ids": string_list(segment.get("source_claim_ids")),
                "support_rationale": first_text(segment.get("support_rationale")),
                "category": evidence_category(segment, {}, evidence),
                "evidence": evidence,
            }
        )
    edges: list[dict[str, Any]] = []
    for left, right in zip(nodes, nodes[1:]):
        edges.append({"from": left["id"], "to": right["id"], "relation": "source_sequence"})
    extra_edges = enrichment.get("argument_edges") if using_agent_nodes else logic_graph.get("edges")
    for edge in extra_edges if isinstance(extra_edges, list) else []:
        if isinstance(edge, dict):
            row = {
                "from": first_text(edge.get("from"), edge.get("source")),
                "to": first_text(edge.get("to"), edge.get("target")),
                "relation": first_text(edge.get("relation"), edge.get("type"), default="supports"),
            }
            if row["from"] and row["to"] and row not in edges:
                edges.append(row)
    return {"nodes": nodes, "edges": edges, "source_order": [node["id"] for node in nodes]}


def build_prerequisites(concepts: list[dict[str, Any]], enrichment: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = enrichment.get("prerequisites")
    if isinstance(explicit, list):
        rows = []
        for index, item in enumerate(explicit, start=1):
            if isinstance(item, dict):
                rows.append(
                    {
                        "id": str(item.get("id") or f"prerequisite_{index:03d}"),
                        "name": first_text(item.get("name"), item.get("term"), default=f"前置知识 {index}"),
                        "why_needed": first_text(item.get("why_needed"), default="它解锁后续核心概念。"),
                        "minimum_mastery": first_text(item.get("minimum_mastery"), default="能够用自己的话解释并识别一个例子。"),
                        "category": str(item.get("category") or "Inference"),
                    }
                )
        return rows

    seen: set[str] = set()
    rows = []
    for concept in concepts:
        for value in concept.get("prerequisites", []):
            name = str(value).strip()
            if name and name not in seen:
                seen.add(name)
                rows.append(
                    {
                        "id": f"prerequisite_{len(rows) + 1:03d}",
                        "name": name,
                        "why_needed": f"它是理解“{concept['term']}”的前置条件。",
                        "minimum_mastery": "能够解释基本含义，并识别它在一个简单例子中的作用。",
                        "category": "Inference",
                    }
                )
    return rows


def build_learning_path(
    concepts: list[dict[str, Any]], prerequisites: list[dict[str, Any]], enrichment: dict[str, Any]
) -> dict[str, Any]:
    explicit = enrichment.get("learning_path") if isinstance(enrichment.get("learning_path"), dict) else {}
    core = [row["term"] for row in concepts if row.get("priority") == "core"]
    supporting = [row["term"] for row in concepts if row.get("priority") != "core"]
    prereq_names = [row["name"] for row in prerequisites]
    first_topic = (core or supporting or prereq_names or ["核心问题"])[0]
    return {
        "learn_first": string_list(explicit.get("learn_first")) or (prereq_names + core[:2]),
        "learn_next": string_list(explicit.get("learn_next")) or (core[2:] + supporting),
        "skip_for_now": string_list(explicit.get("skip_for_now")),
        "first_action": first_text(
            explicit.get("first_action"),
            default=f"先不用复述整篇内容：用自己的话解释“{first_topic}”，再找出材料中支持它的一个例子。",
        ),
        "check_question": first_text(
            explicit.get("check_question"),
            default=f"如果不看原文，你能解释“{first_topic}”解决什么问题，以及它为什么重要吗？",
        ),
        "review_prompts": string_list(explicit.get("review_prompts"))
        or ["核心问题是什么？", "关键概念之间是什么关系？", "哪个例子真正支撑了核心结论？"],
    }


def render_pack_markdown(pack: dict[str, Any]) -> str:
    source = pack["source"]
    lines = [
        "# Learning Analysis Pack" + ("（部分范围）" if pack["partial_scope"] else ""),
        "",
        "## 学习请求",
        "",
        f"- 学习目标：{pack['request']['learning_goal']}",
        f"- 读者：{pack['request']['audience']}",
        f"- 当前水平：{pack['request']['learner_level']}",
        f"- 深度：{pack['request']['depth']}",
        f"- Agent enrichment：`{pack['enrichment_present']}`",
        f"- 来源重分析模式：`{pack['source_reanalysis']['mode']}`",
        "",
        "## 核心问题与来源主张",
        "",
        f"- 核心问题：{source['core_question']}",
        f"- 来源主张：{source['thesis']}",
        "",
        "## 概念地图",
        "",
    ]
    for concept in pack["knowledge_map"]["concepts"]:
        lines.append(f"- `{concept['id']}` **{concept['term']}**：{concept['definition']}（重要性：{concept['why_it_matters']}）")
    if not pack["knowledge_map"]["concepts"]:
        lines.append("- 上游没有提供可用概念；文章只能围绕声明和例子保守组织。")
    lines.extend(["", "## 来源结构", ""])
    for index, node in enumerate(pack["argument_graph"]["nodes"], start=1):
        lines.append(f"{index}. `{node['role']}` {node['title']}：{node['summary']}")
    lines.extend(["", "## 关键例子及作用", ""])
    for example in pack["examples"]:
        lines.append(f"- **{example['name']}**：{example['what_it_is']}；作用：{example['why_introduced']}；支持：{example['what_it_supports']}")
    lines.extend(["", "## 建议学习顺序", ""])
    path = pack["learning_path"]
    lines.append(f"- 先学：{', '.join(path['learn_first']) or '未确定'}")
    lines.append(f"- 再学：{', '.join(path['learn_next']) or '未确定'}")
    lines.append(f"- 暂时跳过：{', '.join(path['skip_for_now']) or '没有明确标记'}")
    lines.append(f"- 第一步：{path['first_action']}")
    lines.append(f"- 检查问题：{path['check_question']}")
    lines.extend(["", "## 边界和不确定性", ""])
    for value in pack["uncertainties"] or ["未记录额外不确定性。"]:
        lines.append(f"- {value}")
    return "\n".join(lines)


def build_learning_pack(args: argparse.Namespace) -> dict[str, Any]:
    upstream = validate_upstream(args.project_root)
    project_root: Path = upstream["project_root"]
    video_root: Path = upstream["video_root"]
    learning_root = (args.output_root or project_root / "15_learning").expanduser().resolve()
    enrichment_path = args.enrichment.expanduser().resolve() if args.enrichment else learning_root / "learning_enrichment.json"
    enrichment = read_json(enrichment_path, required=False) if enrichment_path.is_file() else {}

    claims_raw = list_items(read_json(video_root / "03_inventory" / "claims.json", required=False), "claims")
    concepts_raw = list_items(read_json(video_root / "03_inventory" / "concepts.json", required=False), "concepts")
    examples_raw = list_items(read_json(video_root / "03_inventory" / "examples.json", required=False), "examples")
    segments = list_items(read_json(video_root / "02_segments" / "argument_segments.json", required=False), "segments")
    logic_graph = read_json(video_root / "04_logic" / "logic_graph.json", required=False)
    evidence_audit = read_json(video_root / "05_gap_check" / "evidence_audit.json", required=False)
    source_logic = read_text(video_root / "04_logic" / "source_logic.md")

    learning_root.mkdir(parents=True, exist_ok=True)
    reanalysis_validation = validate_source_reanalysis(
        project_root,
        upstream["gate_receipt"],
        enrichment,
        claims_raw,
        concepts_raw,
        examples_raw,
        segments,
    )
    reanalysis_validation_path = learning_root / "source_reanalysis_validation.json"
    write_json(reanalysis_validation_path, reanalysis_validation)
    if not reanalysis_validation["approved_for_learning_analysis"]:
        codes = ", ".join(reanalysis_validation.get("blocking_codes", [])) or "unknown"
        raise LearningPipelineError(f"source reanalysis gate blocked learning analysis: {codes}")

    claims = build_claims(claims_raw)
    concepts = build_concepts(concepts_raw, examples_raw, claims_raw, enrichment)
    examples = build_examples(examples_raw, enrichment)
    argument_graph = build_argument_graph(segments, logic_graph, enrichment)
    prerequisites = build_prerequisites(concepts, enrichment)
    learning_path = build_learning_path(concepts, prerequisites, enrichment)
    source_claims = [claim for claim in claims if claim["category"] == "Source"]
    framing = source_framing_map(enrichment)
    core_question_row = framing.get("core_question", {})
    thesis_row = framing.get("thesis", {})
    source_structure_row = framing.get("source_structure_summary", {})
    core_question = first_text(core_question_row.get("text"), derive_core_question(segments, {}))
    thesis = first_text(thesis_row.get("text"), source_claims[0]["text"] if source_claims else "", claims[0]["text"] if claims else "")
    source_structure_summary = first_text(source_structure_row.get("text"), compact(source_logic, 700))

    worth_learning = string_list((enrichment.get("learning_priorities") or {}).get("worth_learning")) if isinstance(enrichment.get("learning_priorities"), dict) else []
    if not worth_learning:
        worth_learning = [f"{row['term']}：{row['why_it_matters']}" for row in concepts if row.get("priority") == "core"]
    transfer_patterns = enrichment.get("transfer_patterns") if isinstance(enrichment.get("transfer_patterns"), list) else []
    transfer_patterns = [row for row in transfer_patterns if isinstance(row, dict)]

    uncertainties: list[str] = []
    if upstream["partial_scope"]:
        uncertainties.append("当前来源只覆盖部分范围，学习结构不得补全缺失的原始论证。")
    if reanalysis_validation["mode"] == "evidence_bound":
        uncertainties.append(
            "上游语义库存不完整；本文进入显式证据重分析模式，Source 条目均绑定已验收来源锚点和支持理由。"
        )
    severity_counts = evidence_audit.get("severity_counts") if isinstance(evidence_audit.get("severity_counts"), dict) else {}
    audit_errors = int(severity_counts.get("error") or 0)
    audit_warnings = int(severity_counts.get("warning") or 0)
    if audit_errors or audit_warnings:
        uncertainties.append(
            f"上游证据审计记录 {audit_errors} 条错误、{audit_warnings} 条非阻断警告；详情见 10_video/05_gap_check/evidence_audit.json。"
        )
    if any("没有给出完整定义" in row["definition"] for row in concepts):
        uncertainties.append("部分概念缺少来源内定义，需要保持为学习提示而不是伪造定义。")
    uncertainties.extend(string_list(enrichment.get("uncertainties")))

    request = {
        "learning_goal": args.learning_goal,
        "audience": args.audience,
        "learner_level": args.learner_level,
        "final_language": args.final_language,
        "depth": args.depth,
    }
    pack = {
        "schema_version": "learning-analysis-pack.v1",
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        "project_root": str(project_root),
        "source_status": upstream["source_status"].get("source_status"),
        "partial_scope": upstream["partial_scope"],
        "enrichment_present": bool(enrichment),
        "source_reanalysis": {
            "mode": reanalysis_validation["mode"],
            "requested": reanalysis_validation["requested"],
            "approved": reanalysis_validation["approved_for_learning_analysis"],
            "detected_upstream_issues": reanalysis_validation["detected_upstream_issues"],
            "declared_scopes": reanalysis_validation["declared_scopes"],
            "inventory_outcomes": reanalysis_validation["inventory_outcomes"],
            "source_artifact": reanalysis_validation["source_artifact"],
            "source_artifact_sha256": reanalysis_validation["source_artifact_sha256"],
            "validation_artifact": "source_reanalysis_validation.json",
        },
        "request": request,
        "source": {
            "core_question": core_question,
            "core_question_category": first_text(core_question_row.get("category"), default="Source"),
            "core_question_evidence": evidence_refs(core_question_row),
            "core_question_support_rationale": first_text(core_question_row.get("support_rationale")),
            "thesis": thesis or "上游没有形成可验证的核心主张。",
            "thesis_category": first_text(thesis_row.get("category"), default="Source"),
            "thesis_evidence": evidence_refs(thesis_row),
            "thesis_support_rationale": first_text(thesis_row.get("support_rationale")),
            "source_structure_summary": source_structure_summary,
            "source_structure_category": first_text(source_structure_row.get("category"), default="Source"),
            "source_structure_evidence": evidence_refs(source_structure_row),
            "source_structure_support_rationale": first_text(source_structure_row.get("support_rationale")),
            "source_claim_ids": [row["id"] for row in source_claims],
        },
        "knowledge_map": {
            "concepts": concepts,
            "relationships": [
                {"from": concept["id"], **relation}
                for concept in concepts
                for relation in concept.get("relationships", [])
                if isinstance(relation, dict)
            ],
            "learning_structure_summary": first_text(enrichment.get("learning_structure_summary")),
        },
        "argument_graph": argument_graph,
        "claims": claims,
        "examples": examples,
        "prerequisites": prerequisites,
        "transfer_patterns": transfer_patterns,
        "learning_priorities": {
            "worth_learning": worth_learning,
            "skip_for_now": learning_path["skip_for_now"],
        },
        "learning_path": learning_path,
        "uncertainties": uncertainties,
    }

    files = {
        "learning_request.json": request,
        "knowledge_map.json": pack["knowledge_map"],
        "argument_graph.json": argument_graph,
        "concept_cards.json": {"concepts": concepts},
        "example_roles.json": {"examples": examples},
        "prerequisite_map.json": {"prerequisites": prerequisites},
        "transfer_patterns.json": {"transfer_patterns": transfer_patterns},
        "learning_path.json": learning_path,
        "learning_analysis_pack.json": pack,
    }
    for name, payload in files.items():
        write_json(learning_root / name, payload)
    write_text(learning_root / "learning_analysis_pack.md", render_pack_markdown(pack))

    status = upstream["source_status"]
    receipt = {
        "schema_version": "learning-analysis-receipt.v1",
        "runner": RUNNER_NAME,
        "generated_at": now_iso(),
        **copy_provenance(status),
        "source_status": status.get("source_status"),
        "partial_scope": upstream["partial_scope"],
        "analysis_receipt_sha256": sha256_file(upstream["analysis_receipt_path"]),
        "source_reanalysis_mode": reanalysis_validation["mode"],
        "source_reanalysis_validation": "source_reanalysis_validation.json",
        "source_reanalysis_validation_sha256": sha256_file(reanalysis_validation_path),
        "source_artifact": reanalysis_validation["source_artifact"],
        "source_artifact_sha256": reanalysis_validation["source_artifact_sha256"],
        "learning_analysis_pack": "learning_analysis_pack.json",
        "learning_analysis_pack_sha256": sha256_file(learning_root / "learning_analysis_pack.json"),
        "learning_analysis_pack_md_sha256": sha256_file(learning_root / "learning_analysis_pack.md"),
        "knowledge_map_sha256": sha256_file(learning_root / "knowledge_map.json"),
        "learning_path_sha256": sha256_file(learning_root / "learning_path.json"),
        "enrichment_path": str(enrichment_path) if enrichment_path.is_file() else "",
        "enrichment_sha256": sha256_file(enrichment_path) if enrichment_path.is_file() else "",
    }
    write_json(learning_root / "learning_analysis_receipt.json", receipt)
    return {
        "runner": RUNNER_NAME,
        "learning_root": str(learning_root),
        "learning_analysis_pack": str(learning_root / "learning_analysis_pack.json"),
        "learning_analysis_pack_md": str(learning_root / "learning_analysis_pack.md"),
        "learning_analysis_receipt": str(learning_root / "learning_analysis_receipt.json"),
        "enrichment_present": bool(enrichment),
        "source_reanalysis_mode": reanalysis_validation["mode"],
        "concepts": len(concepts),
        "examples": len(examples),
        "claims": len(claims),
        "next_step": "write_learning_article_candidate",
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a learning analysis pack from a current audited workflow project.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--enrichment", type=Path)
    parser.add_argument("--learning-goal", default="系统理解这份材料，并知道应该如何学习和应用其中的知识")
    parser.add_argument("--audience", default="希望系统学习该主题的读者")
    parser.add_argument("--learner-level", default="unknown")
    parser.add_argument("--final-language", default="zh-CN")
    parser.add_argument("--depth", choices=("brief", "standard", "deep"), default="standard")
    return parser


def main() -> int:
    args = make_parser().parse_args()
    try:
        result = build_learning_pack(args)
    except LearningPipelineError as exc:
        print(json.dumps({"runner": RUNNER_NAME, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
