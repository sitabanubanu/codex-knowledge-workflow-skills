# Stage Contracts

## Web Discovery

Producer: web-intent-scout, orchestrated by the workflow console. Optional when
the user already supplied the source.

```text
logs/discovery/web_scout_dossier.md
logs/discovery/candidate_shortlist.json
logs/discovery/selection.json
```

The shortlist records candidate URLs and source types. The selection records
the chosen URL or explicit acquisition query plus the selection rationale.
Persisted URLs must follow the same redaction policy as preflight records.

Discovery artifacts support route selection only. They are not acquisition
artifacts, do not establish `source_status`, and must never be cited as Source
evidence merely because Web Scout inspected or summarized a page. The selected
material must be acquired again through Bundle v2 and pass the source gate.

## Preflight

Producer: workflow console.

Outputs:

```text
logs/preflight.json
logs/preflight.md
```

Input URLs must be redacted before persistence. Preflight estimates a route; it
does not acquire or approve material.

## Run Identity

```text
logs/run_identity.json
```

Binds one project root to run id, platform, source id/fingerprint, target, and
operation. Reuse requires explicit matching resume.

## Acquisition

Producer: agent-reach-console or local bundle builder.

```text
00_acquisition/manifest.json
00_acquisition/artifacts/*
00_acquisition/logs/agent_reach_doctor.json
00_acquisition/logs/route_plan.json
00_acquisition/logs/commands.jsonl
```

Bundle v2 artifacts require contained relative paths, scope, class, coverage,
run/source ids, bytes, and SHA-256. The bundle must validate before promotion.

## Source Gate

Producer: source-gated-evidence-layer.

```text
10_video/00_source/source_status.json
10_video/00_source/gate_receipt.json
10_video/00_source/degraded_source_report.md   # when blocked/degraded
```

The gate compares target with artifact scope. Every outcome gets a receipt.

## Normalization or ASR

```text
10_video/01_transcript/clean_transcript.jsonl
```

Normalization runs only on admitted task-primary text. Local media requires
ASR; the derived transcript hash is added to the gate receipt.

## Evidence Audit

```text
10_video/02_segments/*
10_video/03_inventory/*
10_video/04_logic/*
10_video/05_gap_check/evidence_audit.json
10_video/video_analysis_pack.md
10_video/source_analysis_pack.md               # non-video target
10_video/analysis_receipt.json
```

The analysis receipt binds the current gate, evidence audit, and selected pack.

## Learning Analysis And Learning Article

Producer: knowledge-learning-article. Use only for a learning-article request.

```text
15_learning/learning_request.json
15_learning/learning_enrichment.json          # optional Agent enrichment
15_learning/knowledge_map.json
15_learning/argument_graph.json
15_learning/concept_cards.json
15_learning/example_roles.json
15_learning/prerequisite_map.json
15_learning/transfer_patterns.json
15_learning/learning_path.json
15_learning/learning_analysis_pack.json
15_learning/learning_analysis_pack.md
15_learning/learning_analysis_receipt.json
20_document/learning_article_candidate.md
20_document/learning_quality_gate.json
20_document/learning_article.md
20_document/learning_article_receipt.json
```

The learning analysis receipt binds the current source analysis receipt and
learning pack hashes. The learning article receipt binds the learning receipt,
quality gate, and final article hash. Timestamps remain evidence locators, not
the primary article structure.

## Document Planning

Producer: knowledge-document-composer.

```text
20_document/composer_intake.json
20_document/claim_map.json
20_document/report_outline.md
20_document/composer_receipt.json
```

The composer receipt binds claim map and intake to the analysis receipt.

## Final Delivery

```text
20_document/quality_gate.json
20_document/final_report.md
20_document/final_report_receipt.json
```

The final receipt binds quality gate and report to the composer receipt. Export,
quality review, normal templates, and batch synthesis require this receipt.

For the learning route, `learning_article.md` is deliverable only with a current
`learning_article_receipt.json` whose quality gate approves the article.

## Status and Result

```text
logs/run_state.json
logs/status_summary.json
logs/status_summary.md
logs/result_index.json
result_index.md
```

These consumers read receipts and hashes. They may report stale files, but must
never convert stale file existence into success.

## History

```text
acquisition_history/<attempt-or-bundle-id>/
run_history/<attempt-or-bundle-id>/
```

History is read-only evidence of prior attempts and is never current output.
