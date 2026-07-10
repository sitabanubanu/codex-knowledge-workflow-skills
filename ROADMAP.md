# Roadmap

## v0.6 - Architecture Reset

- Split acquisition from evidence judgment.
- Add ADR for Agent-Reach as the acquisition layer.
- Define `acquisition_bundle` as the stable handoff protocol.
- Add `agent-reach-console` and `source-gated-evidence-layer`.
- Keep `10_video` output compatibility while documenting the future
  `10_source` migration.

## v0.7 - Agent-Reach Shell

- Harden `kw acquire` around Agent-Reach doctor output and active backend
  routing.
- Expand offline mocks for YouTube, Bilibili, web pages, GitHub, and search.
- Improve blocked/failed bundle notes and command redaction.
- Keep old platform runners as legacy fallback only.

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
