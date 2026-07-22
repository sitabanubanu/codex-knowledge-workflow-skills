---
name: knowledge-learning-article
description: Transform a current provenance-checked source_analysis_pack or video_analysis_pack into a knowledge map, argument graph, prerequisite map, learning path, and evidence-grounded article optimized for personal learning. Use when the user asks what is worth learning from acquired videos, transcripts, articles, repositories, or other source-gated material; wants systematic understanding instead of timestamp summaries; asks how to learn the material; requests a learning article, concept map, prerequisite order, transferable methods, or study path; or needs explicit evidence-bound reanalysis of an incomplete semantic inventory without inventing Source content.
---

# Knowledge Learning Article

Use this skill only after `source-gated-evidence-layer` has produced a current
`gate_receipt.json`, `analysis_receipt.json`, and audited analysis pack.

1. Read `references/analysis-protocol.md` before interpreting source artifacts.
2. Read `references/artifact-schema.md` before writing learning enrichment or changing data fields.
3. Validate upstream provenance. Never treat file existence as freshness.
4. Inspect semantic inventory completeness before enrichment. Block when source claims are absent. Block empty, unanchored, or heuristic concept/example/argument inventories unless an explicit evidence-bound source reanalysis is prepared.
5. If reanalysis is required, read `references/evidence-reanalysis-contract.md`, return to the admitted normalized source, and validate every Source row against real IDs, ranges, verbatim excerpts, and support rationales. Reanalysis is never permission to fill empty fields from general knowledge.
6. Keep the source's original order separate from the recommended learning order.
7. Organize the article by concepts, relationships, examples, and learning dependencies. Keep timestamps only as evidence locators.
8. Create `15_learning/learning_enrichment.json` for `standard` or `deep` work. Ground every Source statement in upstream evidence; label reconstructed relationships, prerequisites, learning order, and advice as Inference or Extension, and disclose that learning-design boundary near the article opening.
9. Run the complete pipeline:

```powershell
python scripts/learning_pipeline_runner.py --project-root <project> --learning-goal "<goal>" --audience "<audience>" --learner-level <level> --final-language zh-CN --depth standard
```

10. Read `references/article-template.md` when revising the generated candidate.
11. Read `references/quality-gates.md` before delivery. Deliver only when
   `20_document/learning_article_receipt.json` is current and
   `learning_quality_gate.json.approved_for_learning_article` is true.

The deterministic baseline may be used for `brief` output only when the upstream
semantic inventory passes completeness checks. For `standard` or `deep` output,
enrich the audited source structure first so the result contains
real concept relationships, prerequisites, transfer patterns, priorities, and a
task-shaped learning path.

Do not acquire data, repair source status, invent missing claims or source
sequence, append a full transcript to the article, or route degraded/secondary-
only material into a normal learning article. Source sequence may be
semantically re-segmented only inside declared evidence-bound reanalysis.
