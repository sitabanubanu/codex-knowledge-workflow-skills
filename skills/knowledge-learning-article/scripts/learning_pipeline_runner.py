#!/usr/bin/env python
"""Run learning analysis, article writing, quality audit, and receipt creation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from learning_analysis_pack_builder import build_learning_pack
from learning_article_auditor import audit_learning_article
from learning_article_writer import write_learning_article
from learning_common import (
    LearningPipelineError,
    copy_provenance,
    now_iso,
    read_json,
    read_text,
    sha256_file,
    validate_learning_receipt,
    write_json,
    write_text,
)


RUNNER_NAME = "knowledge-learning-article-pipeline"


def run_pipeline(args: argparse.Namespace) -> dict:
    builder_args = argparse.Namespace(
        project_root=args.project_root,
        output_root=None,
        enrichment=args.enrichment,
        learning_goal=args.learning_goal,
        audience=args.audience,
        learner_level=args.learner_level,
        final_language=args.final_language,
        depth=args.depth,
    )
    analysis_result = build_learning_pack(builder_args)
    writer_result = write_learning_article(argparse.Namespace(project_root=args.project_root, output=None))
    project_root = args.project_root.expanduser().resolve()
    document_root = project_root / "20_document"
    candidate = Path(writer_result["candidate"])
    quality = audit_learning_article(project_root, candidate)
    quality_path = document_root / "learning_quality_gate.json"
    write_json(quality_path, quality)

    final_path = document_root / "learning_article.md"
    receipt_path = document_root / "learning_article_receipt.json"
    final_written = False
    if quality["approved_for_learning_article"]:
        write_text(final_path, read_text(candidate, required=True))
        state = validate_learning_receipt(project_root)
        status = state["source_status"]
        receipt = {
            "schema_version": "learning-article-receipt.v1",
            "runner": RUNNER_NAME,
            "generated_at": now_iso(),
            **copy_provenance(status),
            "source_status": status.get("source_status"),
            "partial_scope": state["partial_scope"],
            "source_reanalysis_mode": state["learning_receipt"].get("source_reanalysis_mode"),
            "source_reanalysis_validation_sha256": state["learning_receipt"].get("source_reanalysis_validation_sha256"),
            "source_artifact": state["learning_receipt"].get("source_artifact"),
            "source_artifact_sha256": state["learning_receipt"].get("source_artifact_sha256"),
            "learning_analysis_receipt_sha256": sha256_file(state["learning_receipt_path"]),
            "learning_quality_gate_sha256": sha256_file(quality_path),
            "learning_article": "learning_article.md",
            "learning_article_sha256": sha256_file(final_path),
            "approved_for_learning_article": True,
        }
        write_json(receipt_path, receipt)
        final_written = True

    return {
        "runner": RUNNER_NAME,
        "project_root": str(project_root),
        "analysis": analysis_result,
        "candidate": str(candidate),
        "quality_gate": str(quality_path),
        "approved_for_learning_article": quality["approved_for_learning_article"],
        "blocking_gates": quality["blocking_gates"],
        "warning_gates": quality["warning_gates"],
        "learning_article_written": final_written,
        "learning_article": str(final_path) if final_written else "",
        "learning_article_receipt": str(receipt_path) if final_written else "",
        "next_step": "deliver_learning_article" if final_written else "revise_learning_enrichment_or_upstream_analysis",
    }


def fixture_span(transcript_id: str, excerpt: str, start: float, end: float) -> dict:
    return {
        "transcript_ids": [transcript_id],
        "start": start,
        "end": end,
        "verbatim_excerpt": excerpt,
        "quote": excerpt,
    }


def write_fixture(root: Path) -> None:
    manifest_path = root / "00_acquisition" / "manifest.json"
    write_json(manifest_path, {"schema_version": 2, "status": "material_acquired"})
    ids = {
        "run_id": "run_learning_fixture",
        "bundle_id": "bundle_learning_fixture",
        "source_id": "source_learning_fixture",
        "source_fingerprint": "fingerprint_learning_fixture",
        "analysis_target": "video_content",
        "gate_input_sha256": sha256_file(manifest_path),
    }
    video_root = root / "10_video"
    status_path = video_root / "00_source" / "source_status.json"
    write_json(
        status_path,
        {
            **ids,
            "source_status": "source_confirmed",
            "primary_material_available": True,
            "can_enter_full_decomposition": True,
            "allowed_report_type": "full",
        },
    )
    transcript_rows = [
        {"id": "t0001", "start": 0.0, "end": 12.0, "text": "普通摘要会丢失知识结构，只罗列时间点无法形成学习结构。", "normalized_text": "普通摘要会丢失知识结构，只罗列时间点无法形成学习结构。"},
        {"id": "t0002", "start": 12.0, "end": 28.0, "text": "概念关系和证据共同形成知识结构。", "normalized_text": "概念关系和证据共同形成知识结构。"},
        {"id": "t0003", "start": 28.0, "end": 36.0, "text": "时间只负责定位。", "normalized_text": "时间只负责定位。"},
        {"id": "t0004", "start": 36.0, "end": 48.0, "text": "按照依赖来组织学习顺序。", "normalized_text": "按照依赖来组织学习顺序。"},
    ]
    transcript_path = video_root / "01_transcript" / "clean_transcript.jsonl"
    write_text(
        transcript_path,
        "\n".join(json.dumps(row, ensure_ascii=False) for row in transcript_rows),
    )
    gate_path = video_root / "00_source" / "gate_receipt.json"
    write_json(
        gate_path,
        {
            **ids,
            "source_status": "source_confirmed",
            "source_status_sha256": sha256_file(status_path),
            "derived_artifacts": [
                {
                    "path": "10_video/01_transcript/clean_transcript.jsonl",
                    "sha256": sha256_file(transcript_path),
                    "type": "transcript",
                    "content_scope": "video_transcript",
                }
            ],
        },
    )
    pack_path = video_root / "video_analysis_pack.md"
    write_text(pack_path, "# Video Analysis Pack\n\nThe source explains why evidence and structure must remain connected.\n")
    analysis_path = video_root / "analysis_receipt.json"
    write_json(
        analysis_path,
        {
            **ids,
            "source_status": "source_confirmed",
            "analysis_pack": "video_analysis_pack.md",
            "analysis_pack_sha256": sha256_file(pack_path),
            "gate_receipt_sha256": sha256_file(gate_path),
        },
    )
    write_json(
        video_root / "02_segments" / "argument_segments.json",
        {
            "segments": [
                {
                    "id": "seg_001",
                    "role": "problem",
                    "title": "为什么普通摘要不利于学习",
                    "summary": "Heuristic argument segment derived from transcript continuity.",
                    "evidence_spans": [fixture_span("t0001", "普通摘要会丢失知识结构", 0.0, 12.0)],
                },
                {
                    "id": "seg_002",
                    "role": "claim",
                    "title": "知识必须被重建成关系网络",
                    "summary": "Heuristic argument segment derived from transcript continuity.",
                    "evidence_spans": [fixture_span("t0002", "概念关系和证据共同形成知识结构", 12.0, 28.0)],
                },
            ]
        },
    )
    write_json(
        video_root / "03_inventory" / "claims.json",
        {
            "claims": [
                {
                    "id": "claim_001",
                    "text": "学习型文章必须保留概念关系和证据来源。",
                    "claim_type": "source_claim",
                    "confidence": "high",
                    "evidence_spans": [fixture_span("t0002", "概念关系和证据共同形成知识结构", 12.0, 28.0)],
                },
                {
                    "id": "claim_002",
                    "text": "时间戳应当只作为定位工具，而不是文章结构。",
                    "claim_type": "inferred_claim",
                    "confidence": "medium",
                    "evidence_spans": [fixture_span("t0003", "时间只负责定位", 28.0, 36.0)],
                },
            ]
        },
    )
    write_json(
        video_root / "03_inventory" / "concepts.json",
        {"concepts": []},
    )
    write_json(
        video_root / "03_inventory" / "examples.json",
        {"examples": []},
    )
    write_json(video_root / "04_logic" / "logic_graph.json", {"nodes": [], "edges": []})
    write_text(video_root / "04_logic" / "source_logic.md", "# Source Logic\n\n问题 → 反例 → 知识结构 → 学习顺序。\n")
    write_json(
        video_root / "05_gap_check" / "evidence_audit.json",
        {
            "severity_counts": {"error": 0, "warning": 0, "info": 0},
            "claim_source_audit_summary": {"blocking_claims": 0},
        },
    )
    write_text(video_root / "05_gap_check" / "gap_check.md", "# Gap Check\n\n没有阻断性缺口。\n")
    write_json(
        root / "15_learning" / "learning_enrichment.json",
        {
            "source_reanalysis": {
                "mode": "evidence_bound",
                "reason": "upstream_semantic_inventory_incomplete",
                "source_artifact": "10_video/01_transcript/clean_transcript.jsonl",
                "scopes": ["source_framing", "concepts", "examples", "argument_structure"],
                "inventory_outcomes": {
                    "source_framing": "reconstructed",
                    "concepts": "reconstructed",
                    "examples": "reconstructed",
                    "argument_structure": "reconstructed",
                },
            },
            "source_framing": [
                {
                    "id": "agent_framing_core_question",
                    "field": "core_question",
                    "text": "怎样把视频原始内容重建成真正方便学习的知识文章？",
                    "category": "Inference",
                    "support_rationale": "来源先指出普通摘要会丢失知识结构，因此可将学习问题重建为怎样生成真正方便学习的文章。",
                    "evidence_spans": [fixture_span("t0001", "普通摘要会丢失知识结构", 0.0, 12.0)],
                },
                {
                    "id": "agent_framing_thesis",
                    "field": "thesis",
                    "text": "学习文章应保留概念、关系与证据，并按学习依赖重新组织，而不是按时间点罗列。",
                    "category": "Inference",
                    "support_rationale": "来源分别说明知识结构由概念关系和证据构成、时间只负责定位、学习应按依赖组织，三者共同支持该综合主张。",
                    "evidence_spans": [
                        fixture_span("t0002", "概念关系和证据共同形成知识结构", 12.0, 28.0),
                        fixture_span("t0003", "时间只负责定位", 28.0, 36.0),
                        fixture_span("t0004", "按照依赖来组织学习顺序", 36.0, 48.0),
                    ],
                },
                {
                    "id": "agent_framing_source_structure",
                    "field": "source_structure_summary",
                    "text": "材料先指出时间线摘要的局限，再提出知识结构与学习顺序。",
                    "category": "Inference",
                    "support_rationale": "来源先否定时间清单，随后说明知识结构与依赖顺序，支持这一顺序概括。",
                    "evidence_spans": [
                        fixture_span("t0001", "只罗列时间点无法形成学习结构", 0.0, 12.0),
                        fixture_span("t0004", "按照依赖来组织学习顺序", 36.0, 48.0),
                    ],
                },
            ],
            "learning_structure_summary": "先理解知识结构，再学习如何按依赖安排学习顺序。",
            "concepts": [
                {
                    "id": "agent_concept_001",
                    "term": "知识结构",
                    "definition": "概念、关系、证据和例子共同形成的可理解网络。",
                    "why_it_matters": "它决定读者看到的是知识网络还是片段清单。",
                    "support_rationale": "对应来源明确把概念关系和证据共同描述为知识结构。",
                    "source_claim_ids": ["claim_001"],
                    "evidence_spans": [fixture_span("t0002", "概念关系和证据共同形成知识结构", 12.0, 28.0)],
                    "category": "Source",
                },
                {
                    "id": "agent_concept_002",
                    "term": "学习顺序",
                    "definition": "按照前置知识和概念依赖重新组织材料。",
                    "why_it_matters": "它把理解转化为可执行的学习行动。",
                    "support_rationale": "对应来源直接提出按照依赖组织学习顺序。",
                    "source_claim_ids": ["claim_001"],
                    "evidence_spans": [fixture_span("t0004", "按照依赖来组织学习顺序", 36.0, 48.0)],
                    "category": "Source",
                },
            ],
            "examples": [
                {
                    "id": "agent_example_001",
                    "name": "时间戳目录",
                    "what_it_is": "按分钟罗列视频讲了什么。",
                    "why_introduced": "用于展示只有时间定位而没有知识结构的失败产物。",
                    "what_it_supports": "定位信息不等于知识结构。",
                    "support_rationale": "对应来源直接指出只罗列时间点无法形成学习结构。",
                    "linked_concept_ids": ["agent_concept_001"],
                    "source_claim_ids": ["claim_001"],
                    "evidence_spans": [fixture_span("t0001", "只罗列时间点无法形成学习结构", 0.0, 12.0)],
                    "category": "Source",
                }
            ],
            "argument_nodes": [
                {
                    "id": "agent_argument_001",
                    "role": "question",
                    "title": "指出时间线摘要的局限",
                    "summary": "材料先说明按分钟罗列只能定位，不能形成可学习的知识结构。",
                    "support_rationale": "对应来源把时间的作用限定为定位，并否定时间清单等同于知识结构。",
                    "source_claim_ids": ["claim_002"],
                    "evidence_spans": [fixture_span("t0003", "时间只负责定位", 28.0, 36.0)],
                    "category": "Source",
                },
                {
                    "id": "agent_argument_002",
                    "role": "conclusion",
                    "title": "改用知识关系和学习依赖组织",
                    "summary": "随后提出保留概念、关系、证据与例子，并按依赖重排学习顺序。",
                    "support_rationale": "对应来源明确把依赖关系作为学习顺序的组织依据。",
                    "source_claim_ids": ["claim_001"],
                    "evidence_spans": [fixture_span("t0004", "按照依赖来组织学习顺序", 36.0, 48.0)],
                    "category": "Source",
                },
            ],
            "concept_enrichment": {
                "agent_concept_001": {
                    "priority": "core",
                    "why_it_matters": "它决定读者看到的是知识网络还是片段清单。",
                    "relationships": [
                        {
                            "target_id": "agent_concept_002",
                            "type": "enables",
                            "explanation": "先识别知识结构，才能确定合理学习顺序。",
                        }
                    ],
                    "learning_notes": "尝试画出概念、例子和声明之间的连接。",
                },
                "agent_concept_002": {
                    "priority": "core",
                    "why_it_matters": "它把理解转化为可执行的学习行动。",
                    "prerequisites": ["知识结构"],
                },
            },
            "example_enrichment": {
                "agent_example_001": {
                    "why_introduced": "用一个常见失败产物说明定位与理解的区别。",
                    "how_it_works": "先展示按时间罗列的表面完整，再指出它缺少概念关系和学习动作。",
                    "role": "foundational",
                }
            },
            "prerequisites": [
                {
                    "name": "主题与概念的区别",
                    "why_needed": "主题只说明谈了什么，概念还要说明含义与关系。",
                    "minimum_mastery": "能够把一个宽泛主题拆成两个可定义概念。",
                }
            ],
            "learning_priorities": {
                "worth_learning": [
                    "区分时间定位与知识结构。",
                    "识别概念、例子和声明之间的关系。",
                    "把来源顺序重组为学习顺序。",
                ]
            },
            "transfer_patterns": [
                {
                    "name": "从片段清单到关系网络",
                    "pattern": "先提取节点，再标注节点关系，最后按前置依赖重排。",
                    "use_when": "处理视频、文章、课程或访谈记录时。",
                    "limits": "来源本身没有支持的关系必须标为 Inference。",
                    "category": "Extension",
                }
            ],
            "learning_path": {
                "learn_first": ["主题与概念的区别", "知识结构"],
                "learn_next": ["学习顺序", "从片段清单到关系网络"],
                "skip_for_now": ["完整逐字稿背诵"],
                "first_action": "选一个视频片段，写出一个概念、一个例子和它们支持的声明。",
                "check_question": "为什么“第 12 分钟讲了知识结构”仍然不是一条合格的学习笔记？",
            },
        },
    )


def fixture_args(root: Path) -> argparse.Namespace:
    return argparse.Namespace(
        project_root=root,
        enrichment=None,
        learning_goal="系统理解视频内容并形成可执行学习路径",
        audience="中文自学者",
        learner_level="beginner",
        final_language="zh-CN",
        depth="deep",
    )


def expect_pipeline_blocked(args: argparse.Namespace, expected_code: str) -> None:
    try:
        run_pipeline(args)
    except LearningPipelineError as exc:
        assert expected_code in str(exc), (expected_code, str(exc))
    else:
        raise AssertionError(f"pipeline unexpectedly passed; expected block code {expected_code}")


def promote_fixture_to_normal_upstream(root: Path) -> None:
    enrichment_path = root / "15_learning" / "learning_enrichment.json"
    enrichment = read_json(enrichment_path)
    concepts = enrichment.pop("concepts")
    examples = enrichment.pop("examples")
    segments = enrichment.pop("argument_nodes")
    enrichment.pop("source_framing", None)
    enrichment.pop("argument_edges", None)
    enrichment.pop("source_reanalysis", None)
    write_json(root / "10_video" / "03_inventory" / "concepts.json", {"concepts": concepts})
    write_json(root / "10_video" / "03_inventory" / "examples.json", {"examples": examples})
    write_json(root / "10_video" / "02_segments" / "argument_segments.json", {"segments": segments})
    write_json(enrichment_path, enrichment)


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="knowledge-learning-article-") as tmp:
        base = Path(tmp)

        reanalysis_root = base / "valid-reanalysis"
        write_fixture(reanalysis_root)
        result = run_pipeline(fixture_args(reanalysis_root))
        assert result["approved_for_learning_article"] is True, result
        assert result["learning_article_written"] is True, result
        assert result["analysis"]["source_reanalysis_mode"] == "evidence_bound", result
        article = read_text(reanalysis_root / "20_document" / "learning_article.md", required=True)
        assert "证据重分析" in article and "知识结构" in article and "学习顺序" in article, article
        assert not any(line.startswith("## 00:") for line in article.splitlines()), article
        validation = read_json(reanalysis_root / "15_learning" / "source_reanalysis_validation.json")
        assert validation["approved_for_learning_analysis"] is True, validation
        assert validation["rows_checked"] == 8 and validation["blocking_codes"] == [], validation
        receipt = read_json(reanalysis_root / "20_document" / "learning_article_receipt.json")
        assert receipt["learning_article_sha256"] == sha256_file(reanalysis_root / "20_document" / "learning_article.md"), receipt
        assert receipt["source_artifact_sha256"] == sha256_file(
            reanalysis_root / "10_video" / "01_transcript" / "clean_transcript.jsonl"
        ), receipt

        enrichment_path = reanalysis_root / "15_learning" / "learning_enrichment.json"
        changed_enrichment = read_json(enrichment_path)
        changed_enrichment["uncertainties"] = ["receipt freshness test"]
        write_json(enrichment_path, changed_enrichment)
        try:
            validate_learning_receipt(reanalysis_root)
        except LearningPipelineError as exc:
            assert "stale relative to Agent enrichment" in str(exc), str(exc)
        else:
            raise AssertionError("changed enrichment unexpectedly matched the prior learning receipt")

        normal_root = base / "valid-normal"
        write_fixture(normal_root)
        promote_fixture_to_normal_upstream(normal_root)
        normal_result = run_pipeline(fixture_args(normal_root))
        assert normal_result["approved_for_learning_article"] is True, normal_result
        assert normal_result["analysis"]["source_reanalysis_mode"] == "normal", normal_result
        normal_article = read_text(normal_root / "20_document" / "learning_article.md", required=True)
        assert "证据重分析" not in normal_article, normal_article

        no_example_root = base / "valid-none-in-source-examples"
        write_fixture(no_example_root)
        no_example_path = no_example_root / "15_learning" / "learning_enrichment.json"
        no_example = read_json(no_example_path)
        no_example["source_reanalysis"]["inventory_outcomes"]["examples"] = "none_identified_in_source"
        no_example["source_reanalysis"]["inventory_notes"] = {
            "examples": "逐行复核已验收来源后，没有识别出承担论证作用的具体案例。"
        }
        no_example["examples"] = []
        no_example["example_enrichment"] = {}
        write_json(no_example_path, no_example)
        no_example_result = run_pipeline(fixture_args(no_example_root))
        assert no_example_result["approved_for_learning_article"] is True, no_example_result
        no_example_article = read_text(no_example_root / "20_document" / "learning_article.md", required=True)
        assert "不使用虚构案例" in no_example_article, no_example_article

        undeclared_root = base / "undeclared-empty-inventory"
        write_fixture(undeclared_root)
        undeclared_path = undeclared_root / "15_learning" / "learning_enrichment.json"
        undeclared = read_json(undeclared_path)
        for key in ("source_reanalysis", "source_framing", "concepts", "examples", "argument_nodes", "argument_edges"):
            undeclared.pop(key, None)
        write_json(undeclared_path, undeclared)
        expect_pipeline_blocked(fixture_args(undeclared_root), "source_concepts_empty")

        legacy_framing_root = base / "legacy-free-text-framing"
        write_fixture(legacy_framing_root)
        legacy_framing_path = legacy_framing_root / "15_learning" / "learning_enrichment.json"
        legacy_framing = read_json(legacy_framing_path)
        legacy_framing["thesis"] = "这是一条没有证据行约束的自由文本主论点。"
        write_json(legacy_framing_path, legacy_framing)
        expect_pipeline_blocked(fixture_args(legacy_framing_root), "unvalidated_source_framing")

        missing_framing_root = base / "missing-source-framing"
        write_fixture(missing_framing_root)
        missing_framing_path = missing_framing_root / "15_learning" / "learning_enrichment.json"
        missing_framing = read_json(missing_framing_path)
        missing_framing["source_framing"] = [
            row for row in missing_framing["source_framing"] if row.get("field") != "thesis"
        ]
        write_json(missing_framing_path, missing_framing)
        expect_pipeline_blocked(fixture_args(missing_framing_root), "source_framing_fields_invalid")

        fake_id_root = base / "fake-evidence-id"
        write_fixture(fake_id_root)
        fake_id_path = fake_id_root / "15_learning" / "learning_enrichment.json"
        fake_id = read_json(fake_id_path)
        fake_id["concepts"][0]["evidence_spans"][0]["transcript_ids"] = ["t9999"]
        write_json(fake_id_path, fake_id)
        expect_pipeline_blocked(fixture_args(fake_id_root), "evidence_ids_not_found")

        excerpt_root = base / "mismatched-excerpt"
        write_fixture(excerpt_root)
        excerpt_path = excerpt_root / "15_learning" / "learning_enrichment.json"
        excerpt = read_json(excerpt_path)
        excerpt["concepts"][0]["evidence_spans"][0]["verbatim_excerpt"] = "来源里完全不存在的句子"
        write_json(excerpt_path, excerpt)
        expect_pipeline_blocked(fixture_args(excerpt_root), "verbatim_excerpt_mismatch")

        time_root = base / "mismatched-time"
        write_fixture(time_root)
        time_path = time_root / "15_learning" / "learning_enrichment.json"
        time_data = read_json(time_path)
        time_data["concepts"][0]["evidence_spans"][0]["start"] = 30.0
        time_data["concepts"][0]["evidence_spans"][0]["end"] = 31.0
        write_json(time_path, time_data)
        expect_pipeline_blocked(fixture_args(time_root), "evidence_time_mismatch")

        missing_source_root = base / "missing-source-artifact"
        write_fixture(missing_source_root)
        missing_source_path = missing_source_root / "15_learning" / "learning_enrichment.json"
        missing_source = read_json(missing_source_path)
        missing_source["source_reanalysis"]["source_artifact"] = "10_video/01_transcript/missing.jsonl"
        write_json(missing_source_path, missing_source)
        expect_pipeline_blocked(fixture_args(missing_source_root), "source_artifact_not_found")

        unadmitted_root = base / "unadmitted-source-artifact"
        write_fixture(unadmitted_root)
        admitted_path = unadmitted_root / "10_video" / "01_transcript" / "clean_transcript.jsonl"
        unadmitted_path = unadmitted_root / "10_video" / "01_transcript" / "unadmitted.jsonl"
        write_text(unadmitted_path, read_text(admitted_path, required=True))
        unadmitted_enrichment_path = unadmitted_root / "15_learning" / "learning_enrichment.json"
        unadmitted = read_json(unadmitted_enrichment_path)
        unadmitted["source_reanalysis"]["source_artifact"] = "10_video/01_transcript/unadmitted.jsonl"
        write_json(unadmitted_enrichment_path, unadmitted)
        expect_pipeline_blocked(fixture_args(unadmitted_root), "source_artifact_not_admitted")

        secondary_root = base / "secondary-source"
        write_fixture(secondary_root)
        status_path = secondary_root / "10_video" / "00_source" / "source_status.json"
        blocked = read_json(status_path)
        blocked["source_status"] = "secondary_only"
        write_json(status_path, blocked)
        expect_pipeline_blocked(fixture_args(secondary_root), "source status secondary_only")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the complete audited learning-article pipeline.")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--enrichment", type=Path)
    parser.add_argument("--learning-goal", default="系统理解这份材料，并知道应该如何学习和应用其中的知识")
    parser.add_argument("--audience", default="希望系统学习该主题的读者")
    parser.add_argument("--learner-level", default="unknown")
    parser.add_argument("--final-language", default="zh-CN")
    parser.add_argument("--depth", choices=("brief", "standard", "deep"), default="standard")
    parser.add_argument("--self-test", action="store_true")
    return parser


def main() -> int:
    args = make_parser().parse_args()
    if args.self_test:
        self_test()
        print("knowledge-learning-article self-test passed")
        return 0
    if args.project_root is None:
        raise SystemExit("--project-root is required unless --self-test is used")
    try:
        result = run_pipeline(args)
    except LearningPipelineError as exc:
        print(json.dumps({"runner": RUNNER_NAME, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["approved_for_learning_article"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
