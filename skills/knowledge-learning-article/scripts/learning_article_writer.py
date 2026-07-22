#!/usr/bin/env python
"""Render a source-grounded learning article candidate from a learning pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from learning_common import LearningPipelineError, first_text, read_json, validate_learning_receipt, write_text


RUNNER_NAME = "knowledge-learning-article-writer"
RELATION_LABELS = {
    "requires": "依赖",
    "enables": "使之成为可能",
    "contrasts": "对照",
    "causes": "导致",
    "explains": "解释",
    "applies": "应用于",
    "qualifies": "限定",
}
ARGUMENT_ROLE_LABELS = {
    "question": "提出问题",
    "setup": "建立情境",
    "mechanism": "解释机制",
    "explanation": "展开解释",
    "qualification": "补充边界",
    "critique": "反向质疑",
    "conclusion": "形成结论",
    "development": "推进论证",
}
EXAMPLE_ROLE_LABELS = {
    "foundational": "基础案例",
    "illustrative": "说明性比喻",
    "counterexample": "反例",
    "boundary": "边界条件",
}


def values(items: Any) -> list[dict[str, Any]]:
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def evidence_label(item: dict[str, Any], limit: int | None = 3) -> str:
    spans = values(item.get("evidence"))
    labels: list[str] = []
    selected_spans = spans if limit is None else spans[:limit]
    for span in selected_spans:
        transcript_ids = [str(value) for value in span.get("transcript_ids", []) if value]
        ids = ""
        if len(transcript_ids) == 1:
            ids = transcript_ids[0]
        elif transcript_ids:
            ids = f"{transcript_ids[0]}–{transcript_ids[-1]}"
        start = span.get("start")
        end = span.get("end")
        timing = ""
        if isinstance(start, (int, float)):
            timing = f"{start:.1f}s" + (f"–{end:.1f}s" if isinstance(end, (int, float)) else "")
        value = " / ".join(part for part in (ids, timing) if part)
        if value:
            labels.append(value)
    return "；".join(labels) or "上游结构化来源（无精确时间定位）"


def title_from(pack: dict[str, Any]) -> str:
    question = first_text(pack.get("source", {}).get("core_question"), default="学习材料")
    question = question.rstrip("？?")
    prefix = "部分范围｜" if pack.get("partial_scope") else ""
    return f"{prefix}{question}：一份面向理解与行动的学习文章"


def render_concept_map(pack: dict[str, Any]) -> list[str]:
    concepts = values(pack.get("knowledge_map", {}).get("concepts"))
    term_by_id = {
        str(item.get("id")): str(item.get("term"))
        for item in concepts
        if item.get("id") and item.get("term")
    }
    prerequisites = values(pack.get("prerequisites"))
    lines: list[str] = []
    if prerequisites:
        lines.append("- 前置层：" + "、".join(item.get("name", "") for item in prerequisites if item.get("name")))
    core = [item.get("term", "") for item in concepts if item.get("priority") == "core"]
    supporting = [item.get("term", "") for item in concepts if item.get("priority") != "core"]
    if core:
        lines.append("- 核心层：" + " → ".join(value for value in core if value))
    if supporting:
        lines.append("- 支撑层：" + "、".join(value for value in supporting if value))
    relationships = values(pack.get("knowledge_map", {}).get("relationships"))
    for relation in relationships[:12]:
        left = first_text(relation.get("from"))
        right = first_text(relation.get("target_id"), relation.get("to"))
        raw_relation_type = first_text(relation.get("type"), relation.get("relation"), default="关联")
        relation_type = RELATION_LABELS.get(raw_relation_type, raw_relation_type)
        explanation = first_text(relation.get("explanation"))
        if left and right:
            left_label = term_by_id.get(left, left)
            right_label = term_by_id.get(right, right)
            lines.append(f"- 关系：**{left_label}** —{relation_type}→ **{right_label}**" + (f"；{explanation}" if explanation else ""))
    if not lines:
        lines.append("- 上游没有形成足够的概念关系；本文将以声明、例子和论证步骤作为保守结构。")
    return lines


def render_article_zh(pack: dict[str, Any]) -> str:
    source = pack.get("source", {})
    concepts = values(pack.get("knowledge_map", {}).get("concepts"))
    argument_nodes = values(pack.get("argument_graph", {}).get("nodes"))
    examples = values(pack.get("examples"))
    transfer_patterns = values(pack.get("transfer_patterns"))
    claims = values(pack.get("claims"))
    prerequisites = values(pack.get("prerequisites"))
    priorities = pack.get("learning_priorities") if isinstance(pack.get("learning_priorities"), dict) else {}
    learning_path = pack.get("learning_path") if isinstance(pack.get("learning_path"), dict) else {}
    reanalysis = pack.get("source_reanalysis") if isinstance(pack.get("source_reanalysis"), dict) else {}

    lines = [
        f"# {title_from(pack)}",
        "",
    ]
    if pack.get("partial_scope"):
        lines.extend(["> **部分范围**：当前只有部分一手材料。本文只分析已覆盖内容，不补写缺失的原始论证。", ""])
    if reanalysis.get("mode") == "evidence_bound":
        lines.extend(
            [
                "> **证据重分析**：上游结构化语义库存不完整。本文直接回到已验收的来源材料；核心问题、来源主张、结构概括，以及每个 Source 概念、案例和论证节点，都通过真实来源 ID、时间范围、逐字锚点和支持理由校验。综合性表述会明确标为 Inference。",
                "",
            ]
        )

    lines.extend(
        [
            "> **学习设计边界**：概念关系、学习优先级、前置知识、迁移方法和练习步骤，是 Agent 基于已验证 Source 内容做出的 Inference 或 Extension，不是作者原话，也不会被伪装成来源事实。",
            "",
        ]
    )

    lines.extend(["## 先给你结论：这份内容值得学什么（Inference）", ""])
    worth = [str(value) for value in priorities.get("worth_learning", []) if str(value).strip()]
    if worth:
        lines.extend(f"- {value}" for value in worth)
    else:
        lines.append(f"- 最值得掌握的是材料如何回答“{source.get('core_question', '')}”，以及这个回答依赖的概念、例子和推理连接。")
    lines.extend(
        [
            "",
            "不要把时间戳当成知识结构。时间只负责帮助你回到原文；真正需要学习的是概念之间的关系、例子承担的论证作用，以及这些内容如何转化为可复用的方法。",
            "",
            "## 这份材料在解决什么问题",
            "",
            f"**核心问题（{source.get('core_question_category', 'Source')}）：** {source.get('core_question', '未提取到核心问题。')}",
            "",
            f"**来源主张（{source.get('thesis_category', 'Source')}）：** {source.get('thesis', '未提取到可验证的核心主张。')}",
            "",
        ]
    )
    if source.get("core_question_support_rationale"):
        lines.extend(
            [
                f"核心问题的证据理由：{source['core_question_support_rationale']}",
                f"证据定位：{evidence_label({'evidence': source.get('core_question_evidence', [])}, limit=None)}",
                "",
            ]
        )
    if source.get("thesis_support_rationale"):
        lines.extend(
            [
                f"来源主张的证据理由：{source['thesis_support_rationale']}",
                f"证据定位：{evidence_label({'evidence': source.get('thesis_evidence', [])}, limit=None)}",
                "",
            ]
        )
    if source.get("source_structure_summary"):
        lines.extend(
            [
                f"原始材料的展开方式（{source.get('source_structure_category', 'Source')}）可以概括为：{source['source_structure_summary']}",
                *(
                    [
                        f"结构概括的证据理由：{source['source_structure_support_rationale']}",
                        f"证据定位：{evidence_label({'evidence': source.get('source_structure_evidence', [])}, limit=None)}",
                    ]
                    if source.get("source_structure_support_rationale")
                    else []
                ),
                "",
            ]
        )

    lines.extend(["## 一页知识地图（Source 概念；Inference 关系）", "", *render_concept_map(pack), ""])

    if prerequisites:
        lines.extend(["## 开始之前，需要哪些前置知识（Inference）", ""])
        for item in prerequisites:
            lines.extend(
                [
                    f"### {item.get('name', '前置知识')}",
                    "",
                    f"- 为什么需要：{item.get('why_needed', '它帮助理解后续核心概念。')}",
                    f"- 最低掌握标准：{item.get('minimum_mastery', '能够解释基本含义并识别简单例子。')}",
                    f"- 内容类型：{item.get('category', 'Inference')}",
                    "",
                ]
            )

    lines.extend(["## 按照学习顺序理解核心知识", ""])
    if concepts:
        for index, concept in enumerate(concepts, start=1):
            lines.extend(
                [
                    f"### {index}. {concept.get('term', '未命名概念')}",
                    "",
                    f"**它是什么：** {concept.get('definition', '来源没有给出完整定义。')}",
                    "",
                    f"**为什么重要：** {concept.get('why_it_matters', '它是理解材料的重要节点。')}",
                    "",
                ]
            )
            prereq = [str(value) for value in concept.get("prerequisites", []) if str(value).strip()]
            if prereq:
                lines.extend([f"**理解它之前：** 先确认你能解释{'、'.join(prereq)}。", ""])
            if concept.get("learning_notes"):
                lines.extend([f"**学习提示：** {concept['learning_notes']}", ""])
            if concept.get("support_rationale"):
                lines.extend([f"**证据为何支持：** {concept['support_rationale']}", ""])
            lines.extend(
                [
                    f"**证据定位：** {evidence_label(concept)}",
                    "",
                ]
            )
    else:
        lines.extend(["上游没有提取出稳定概念，因此本文不伪造概念体系。请先依据下面的声明、例子和论证步骤学习。", ""])

    lines.extend(["## 作者的内容是怎样展开的", ""])
    if argument_nodes:
        for index, node in enumerate(argument_nodes, start=1):
            raw_role = str(node.get("role") or "development")
            lines.extend(
                [
                    f"### 第 {index} 步：{node.get('title', '论证步骤')}",
                    "",
                    f"- 在原文中的作用：{ARGUMENT_ROLE_LABELS.get(raw_role, raw_role)}",
                    f"- 这一步说了什么：{node.get('summary', '未提供摘要。')}",
                    *([f"- 证据为何支持：{node['support_rationale']}"] if node.get("support_rationale") else []),
                    f"- 原文定位：{evidence_label(node)}",
                    "",
                ]
            )
    else:
        lines.extend(["上游没有形成可靠的论证分段。本文不会从零补写作者的完整推理链。", ""])

    lines.extend(["## 关键例子：它们为什么出现在这里", ""])
    if examples:
        for example in examples:
            raw_role = str(example.get("role") or "illustrative")
            lines.extend(
                [
                    f"### {example.get('name', '未命名例子')}",
                    "",
                    f"- 例子本身：{example.get('what_it_is', '未提供具体描述。')}",
                    f"- 为什么引入：{example.get('why_introduced', '用于连接抽象观点和具体情境。')}",
                    f"- 它如何发挥作用：{example.get('how_it_works') or '结合上下文展示观点在具体情境中的含义。'}",
                    f"- 它支持什么：{example.get('what_it_supports', '需要结合相邻声明判断。')}",
                    *([f"- 证据为何支持：{example['support_rationale']}"] if example.get("support_rationale") else []),
                    f"- 例子角色：{EXAMPLE_ROLE_LABELS.get(raw_role, raw_role)}",
                    f"- 原文定位：{evidence_label(example)}",
                    "",
                ]
            )
    else:
        lines.extend(["来源中没有提取出可验证的关键例子，因此不使用虚构案例填充文章。", ""])

    lines.extend(["## 可以迁移到其他问题的方法（Inference / Extension）", ""])
    if transfer_patterns:
        for pattern in transfer_patterns:
            lines.extend(
                [
                    f"### {pattern.get('name', '迁移模式')}",
                    "",
                    f"- 模式：{pattern.get('pattern', pattern.get('description', ''))}",
                    f"- 适用时机：{pattern.get('use_when', '在相似问题出现时。')}",
                    f"- 边界：{pattern.get('limits', '需要结合具体情境重新验证。')}",
                    f"- 内容类型：{pattern.get('category', 'Extension')}",
                    "",
                ]
            )
    else:
        inference_claims = [row for row in claims if row.get("category") == "Inference"]
        if inference_claims:
            for claim in inference_claims:
                lines.append(f"- **可迁移推断：** {claim.get('text')}（Inference，需在新情境中验证）")
        else:
            lines.append("- 当前材料只足以支持来源复原，还不足以形成稳定的迁移方法。")
        lines.append("")

    lines.extend(["## 你应该怎样学习这份内容（Inference / Extension）", ""])
    learn_first = [str(value) for value in learning_path.get("learn_first", []) if str(value).strip()]
    learn_next = [str(value) for value in learning_path.get("learn_next", []) if str(value).strip()]
    skip = [str(value) for value in learning_path.get("skip_for_now", []) if str(value).strip()]
    lines.extend(
        [
            f"1. **先学：** {' → '.join(learn_first) if learn_first else '先明确核心问题和来源主张。'}",
            f"2. **再学：** {' → '.join(learn_next) if learn_next else '再回看例子与论证步骤。'}",
            f"3. **暂时跳过：** {'、'.join(skip) if skip else '没有明确需要跳过的部分；但不要一开始就追逐所有旁支细节。'}",
            f"4. **今天的第一步：** {learning_path.get('first_action', '用自己的话解释核心问题。')}",
            f"5. **理解检查：** {learning_path.get('check_question', '你能不看原文解释核心概念及其关系吗？')}",
            "",
        ]
    )
    review_prompts = [str(value) for value in learning_path.get("review_prompts", []) if str(value).strip()]
    if review_prompts:
        lines.extend(["复习时依次回答：", ""])
        lines.extend(f"- {value}" for value in review_prompts)
        lines.append("")

    lines.extend(["## 证据边界与不确定性", ""])
    for uncertainty in pack.get("uncertainties", []) or ["没有记录额外不确定性。"]:
        lines.append(f"- {uncertainty}")
    lines.extend(
        [
            "",
            "## Source / Inference / Extension",
            "",
            "- **Source：** 原始材料明确表达、并且能够回到 transcript 或上游证据定位的内容。",
            "- **Inference：** 为了帮助理解而从来源中推导出的关系、前置知识或学习顺序，不等于作者原话。",
            "- **Extension：** 面向应用、迁移、练习或外部框架增加的内容，必须单独验证。",
            "",
            "## 原文定位索引",
            "",
        ]
    )
    located = concepts + examples + argument_nodes
    if located:
        for item in located:
            name = first_text(item.get("term"), item.get("name"), item.get("title"), default=str(item.get("id") or "条目"))
            lines.append(f"- {name}：{evidence_label(item)}")
    else:
        lines.append("- 上游没有提供精确定位。")
    lines.append("")
    return "\n".join(lines)


def render_article_en(pack: dict[str, Any]) -> str:
    source = pack.get("source", {})
    concepts = values(pack.get("knowledge_map", {}).get("concepts"))
    examples = values(pack.get("examples"))
    path = pack.get("learning_path", {})
    reanalysis = pack.get("source_reanalysis") if isinstance(pack.get("source_reanalysis"), dict) else {}
    lines = [
        f"# {title_from(pack)}",
        "",
    ]
    if reanalysis.get("mode") == "evidence_bound":
        lines.extend(
            [
                "> **Evidence-bound reanalysis**: Upstream semantic inventory was incomplete. Core framing and every Source concept, example, and argument node are bound to admitted source IDs, ranges, a verbatim anchor, and a support rationale. Synthesized framing is labeled Inference.",
                "",
            ]
        )
    lines.extend(
        [
            "> **Learning-design boundary**: Relationships, priorities, prerequisites, transfer methods, and practice steps are Agent Inference or Extension derived from validated Source material; they are not represented as the author's words.",
            "",
        ]
    )
    lines.extend(
        [
            "## What is worth learning",
            "",
            *[f"- {value}" for value in pack.get("learning_priorities", {}).get("worth_learning", [])],
            "",
            "## Core question and source thesis",
            "",
            f"- Core question: {source.get('core_question', '')}",
            f"- Source thesis: {source.get('thesis', '')}",
            "",
            "## Knowledge map",
            "",
            *render_concept_map(pack),
            "",
            "## Concepts in learning order",
            "",
        ]
    )
    for item in concepts:
        lines.extend([f"### {item.get('term')}", "", item.get("definition", ""), "", f"Why it matters: {item.get('why_it_matters', '')}", ""])
    lines.extend(["## Key examples and their role", ""])
    for item in examples:
        lines.extend([f"### {item.get('name')}", "", f"What it is: {item.get('what_it_is')}", "", f"Why it appears: {item.get('why_introduced')}", ""])
    lines.extend(
        [
            "## How to learn it",
            "",
            f"- Learn first: {', '.join(path.get('learn_first', []))}",
            f"- Learn next: {', '.join(path.get('learn_next', []))}",
            f"- First action: {path.get('first_action', '')}",
            f"- Check: {path.get('check_question', '')}",
            "",
            "## Evidence and limits",
            "",
            *[f"- {value}" for value in pack.get("uncertainties", [])],
            "",
            "## Source / Inference / Extension",
            "",
            "- Source is explicitly grounded in admitted primary material.",
            "- Inference is derived for understanding and is not a source quotation.",
            "- Extension adds application or practice and requires separate validation.",
            "",
            "## Source location index",
            "",
        ]
    )
    for item in concepts + examples:
        name = first_text(item.get("term"), item.get("name"), default=str(item.get("id") or "item"))
        lines.append(f"- {name}: {evidence_label(item)}")
    return "\n".join(lines)


def write_learning_article(args: argparse.Namespace) -> dict[str, Any]:
    state = validate_learning_receipt(args.project_root)
    pack = read_json(state["learning_pack_path"])
    language = str(pack.get("request", {}).get("final_language") or "zh-CN").lower()
    article = render_article_zh(pack) if language.startswith("zh") or "chinese" in language else render_article_en(pack)
    output = args.output or state["project_root"] / "20_document" / "learning_article_candidate.md"
    output = output.expanduser().resolve()
    write_text(output, article)
    return {
        "runner": RUNNER_NAME,
        "candidate": str(output),
        "source_status": pack.get("source_status"),
        "partial_scope": bool(pack.get("partial_scope")),
        "language": language,
        "next_step": "audit_learning_article_candidate",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a learning article candidate from a current learning analysis receipt.")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = write_learning_article(args)
    except LearningPipelineError as exc:
        print(json.dumps({"runner": RUNNER_NAME, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
