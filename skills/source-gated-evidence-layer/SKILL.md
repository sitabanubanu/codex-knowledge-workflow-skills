---
name: source-gated-evidence-layer
description: Validate acquisition bundles, build source_status, run source gate, evidence audit, claim production, quality gates, and degraded outputs. Does not fetch from platforms.
---

# Source-Gated Evidence Layer

Use this skill after `agent-reach-console` or a local bundle builder has written
an acquisition bundle.

Core rule: Evidence layer audits material; it does not acquire platform data.

Workflow:

1. Validate `00_acquisition/manifest.json`.
2. Build `source_status.json`.
3. Continue only when source status is `source_confirmed` or `source_partial`.
4. Normalize primary transcript/subtitle/text artifacts with
   `transcript_normalizer.py`.
5. Run segmentation, inventory extraction, source logic, evidence audit, and pack
   building only when the source gate allows it.
6. Keep `video_analysis_pack.md` compatibility while gradually introducing
   `source_analysis_pack.md`.
7. Send only audited packs to `knowledge-document-composer`.

Status rules:

- `source_confirmed` and `source_partial` can enter full or partial
  decomposition.
- `secondary_only`, `metadata_only`, `source_blocked`, `source_failed`, and
  `degraded_report_only` can only produce degraded output.
- Metadata, search results, snippets, titles, comments, and page context cannot
  be upgraded into Source claims.

Do not:

- call Agent-Reach or platform tools;
- fetch URLs;
- repair or invent primary material;
- let composer read raw acquisition output;
- write a normal `final_report.md` for blocked, failed, metadata-only, or
  secondary-only input.

CLI wrappers:

```powershell
python kw.py ingest --bundle <project>\00_acquisition\manifest.json --project-root <project>
python kw.py audit --project-root <project>
python kw.py compose --project-root <project>
```

Required references:

1. `references/source-gate.md`
2. `references/evidence-audit.md`
3. `references/claim-map.md`
4. `references/quality-gate.md`
5. `references/degraded-output.md`
