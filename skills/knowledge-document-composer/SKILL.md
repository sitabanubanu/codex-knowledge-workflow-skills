---
name: knowledge-document-composer
description: Compose structured knowledge artifacts into reports, essays, briefings, research notes, scripts, outlines, and other documents. Use when Codex needs to transform a video_analysis_pack, transcript, claim map, logic graph, or source notes into a coherent document with source/inference/extension separation, argument reconstruction, critique, revision, and final quality checks.
---

# Knowledge Document Composer

Use this skill to turn structured source material into a finished document.

Core workflow:
1. Before processing any video_analysis_pack, transcript, claim map, logic graph, source notes, or derived artifact, read source status from upstream source metadata, acquisition notes, gap checks, or the user-provided artifact header.
2. Read references/source-gate.md and apply it as a hard gate before writing commitments, source reconstruction, claim inventory, argument flow, or final prose.
3. Load only the source artifacts allowed by the source gate, such as video_analysis_pack, clean_transcript, concepts, examples, claims, source_logic, and logic_graph.
4. Read references/artifact-schema.md before writing intermediate or final artifacts.
5. Read references/workflow.md for the detailed stage process.
6. Use scripts/document_composer_runner.py after an upstream `10_video/video_analysis_pack.md` exists. It verifies upstream source status, evidence audit, `evidence_map.json`, `claim_source_audit.json`, pack gate, and writes gated planning artifacts under `20_document`. It must not write `final_report.md`.
7. Build a commitment file that captures the source status, source's core question, thesis, narrative spine, document goal, final language, audience, must-preserve evidence, and expansion boundaries.
8. Reconstruct the source's argument flow, examples, concept transitions, and language logic before drafting only when the source gate permits that reconstruction.
9. Build a claim map that separates Source, Inference, and Extension content, and never upgrade degraded or secondary material into Source claims.
10. Read references/report-template.md before drafting a report.
11. Use scripts/final_report_writer.py after the planning artifacts exist. It creates `draft_report.md`, `critique.md`, `revised_report.md`, runs the final auditor, writes machine-readable `quality_gate.json`, and creates `final_report.md` only when the final gate approves.
12. Use scripts/final_report_auditor.py independently when checking a manually edited report candidate. It must reject secondary-only/degraded intake, unregistered Source claims, missing Source / Inference / Extension separation, and missing partial-scope labels.
13. Draft, critique, revise, and then read references/quality-gates.md before final delivery. If the user did not specify a final language, use the current conversation language and treat language mismatch as a quality failure.
14. Output the final document and supporting maps only in the report mode allowed by the source gate.

Runner guidance:
- Use scripts/document_composer_runner.py as the first document-composer runner for audited video workflows. It consumes `10_video/video_analysis_pack.md`, `00_source/source_status.json`, `05_gap_check/evidence_audit.json`, `05_gap_check/evidence_map.json`, `05_gap_check/claim_source_audit.json`, inventory, source logic, and gap check artifacts, then writes `20_document/composer_intake.json`, `commitments.md`, `source_reconstruction.md`, `claim_map.json`, `expansion_plan.md`, `report_outline.md`, and `quality_check.md`.
- Treat `document_composer_runner.py` as an intake-to-outline gate, not as a full writing engine. It intentionally does not create `draft_report.md` or `final_report.md`; those require the draft, critique, revision, and final quality-gate workflow.
- Use scripts/final_report_writer.py as the normal planning-to-final runner. It consumes `20_document/composer_intake.json`, `commitments.md`, `source_reconstruction.md`, `claim_map.json`, `expansion_plan.md`, and `report_outline.md`, then writes `draft_report.md`, `critique.md`, `revised_report.md`, `quality_gate.json`, refreshed `quality_check.md`, and, only if approved, `final_report.md`.
- Use scripts/final_report_auditor.py for an independent final gate. It writes `quality_gate.json` with `approved_for_final_report`, `report_scope`, gate statuses, blocking gates, checked files, and source claim ids used.
- If the upstream source status is blocked, failed, secondary-only, degraded, missing primary material, the evidence audit has errors, required evidence sidecars are missing, or `claim_source_audit.json` has blocking claims, do not use the normal document runner to create full-report planning artifacts.
- If `source_status` is `source_partial`, the final report may be approved only as a visible partial-scope report.
- If `source_status` is `secondary_only`, `source_blocked`, `source_failed`, or `degraded_report_only`, the final writer and auditor must not create a normal `final_report.md`.

Required reference order:
1. references/source-gate.md
2. references/artifact-schema.md
3. references/workflow.md
4. references/report-template.md
5. references/quality-gates.md
