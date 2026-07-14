# Roadmap

## v0.6 - Architecture Reset and Bundle v2 (implemented)

- Split acquisition from evidence judgment.
- Add ADR for Agent-Reach as the acquisition layer.
- Define `acquisition_bundle` as the stable handoff protocol.
- Add `agent-reach-console` and `source-gated-evidence-layer`.
- Keep `10_video` output compatibility while documenting the future
  `10_source` migration.
- Add run-scoped provenance, staged attempts, scope gates, integrity hashes,
  centralized redaction, and explicit resume/history behavior.

## v0.7 - Browser Handoff and More Operations

- Define a first-class browser-export artifact handoff for authorized Chrome
  and OpenCLI sessions without coupling the evidence layer to browser control.
- Add operation adapters only when Agent-Reach exposes stable documented
  commands, especially X single-status OpenCLI and Bilibili routes.
- Add richer per-platform live acceptance fixtures and latency recording.
- Keep old platform runners as internal legacy code only.

## v0.8 - Evidence Layer Migration

- Move source-gate references from video-only wording to source-wide wording.
- Add first-class `source_analysis_pack.md`.
- Keep `video_analysis_pack.md` compatibility until downstream users migrate.
- Extend source gate mapping for page, repository, RSS, and search-derived
  source workflows.

## v0.9 - Integrated Workflow

- Make `kw run` fully acquisition-bundle native for URL, local transcript,
  local subtitle, and local media routes.
- Add source-layer ASR pending/resume handling.
- Improve result index and status summaries across degraded paths.
- Add validation fixtures for first-party page text and repository material.

## v1.0 - Source-Gated Agent-Reach Workflow

- Stabilize Agent-Reach acquisition + source-gated evidence + auditable report
  generation as the default product path.
- Complete `10_source` migration.
- Publish compatibility and migration guidance for older `10_video` consumers.
- Keep the project promise: no primary material, no fake report.
