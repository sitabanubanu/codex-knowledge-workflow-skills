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
6. Build a commitment file that captures the source status, source's core question, thesis, narrative spine, document goal, final language, audience, must-preserve evidence, and expansion boundaries.
7. Reconstruct the source's argument flow, examples, concept transitions, and language logic before drafting only when the source gate permits that reconstruction.
8. Build a claim map that separates Source, Inference, and Extension content, and never upgrade degraded or secondary material into Source claims.
9. Read references/report-template.md before drafting a report.
10. Draft, critique, revise, and then read references/quality-gates.md before final delivery. If the user did not specify a final language, use the current conversation language and treat language mismatch as a quality failure.
11. Output the final document and supporting maps only in the report mode allowed by the source gate.

Required reference order:
1. references/source-gate.md
2. references/artifact-schema.md
3. references/workflow.md
4. references/report-template.md
5. references/quality-gates.md
