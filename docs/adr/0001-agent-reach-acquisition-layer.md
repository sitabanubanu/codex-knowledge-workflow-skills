# ADR 0001: Use Agent-Reach as the acquisition layer

## Status

Accepted for the v0.6 architecture reset.

## Context

The current v0.5.0 workflow already has a trustworthy local knowledge pipeline:
local transcripts and subtitles can pass the source gate, enter normalization,
segmentation, inventory extraction, evidence audit, claim production, document
planning, and final quality gates.

The stable value is not platform crawling. The stable value is that the project
does not write a full report without first-hand material, and that accepted
claims remain auditable through Source / Inference / Extension separation.

The weak area is platform URL acquisition. Live validation exposed YouTube bot
checks, Bilibili yt-dlp unreliability, missing visible transcripts, and URL runs
that correctly degraded because no primary material was acquired. The old
`knowledge-video-decomposer` therefore carries too many responsibilities:

| Old module | Current responsibility | New owner | Keep or replace | Reason |
| --- | --- | --- | --- | --- |
| `knowledge-workflow-console` | Route selection, preflight, end-to-end runner, status and result index | Workflow console | Keep and reroute | It remains the product controller, but URL/query inputs must route through acquisition bundles. |
| `knowledge-video-decomposer` source gate | `source_status.json`, source statuses, `primary_material_available`, `can_enter_full_decomposition` | `source-gated-evidence-layer` | Keep | This is the core safety gate and should survive the acquisition reset. |
| `transcript_normalizer.py` | Normalize transcript/subtitle files and write canonical transcript artifacts | Evidence layer, reused through legacy `10_video` root | Keep | This is stable first-hand material handling. |
| `asr_pipeline.py` | Convert authorized local audio/video into transcript artifacts | Evidence layer, reused through legacy `10_video` root | Keep | ASR is primary-material processing after acquisition, not platform scraping. |
| `transcript_segmenter.py` | Segment confirmed or partial transcript material | Evidence layer | Keep | Segmentation depends on accepted source status. |
| `inventory_extractor.py` | Extract candidate concepts, examples, claims, and analogies with evidence spans | Evidence layer | Keep | It supports auditable claim production. |
| `source_logic_builder.py` | Reconstruct source-faithful logic from candidate inventory | Evidence layer | Keep | It is evidence analysis, not acquisition. |
| `evidence_auditor.py` | Require evidence spans, maps, claim audit, and pack gate | Evidence layer | Keep | This is the strongest anti-fake-report control. |
| `video_analysis_pack_builder.py` | Build `video_analysis_pack.md` only after audit gate permits | Evidence layer | Keep with compatibility | It remains the compatibility pack builder while `source_analysis_pack.md` is introduced. |
| Document composer claim map and quality gate | Source / Inference / Extension and final report approval | Document composer | Keep and extend | Composer should consume source packs, never raw acquisition output. |
| `acquisition_runner.py` platform probing | Platform acquisition probes, yt-dlp/cookies/browser route state | Agent-Reach acquisition layer or legacy fallback | Legacy | Platform probing should not remain the primary route inside evidence logic. |
| `platform_media_runner.py` URL-to-material chain | URL subtitles/audio acquisition and degraded media result | Agent-Reach acquisition layer or legacy fallback | Legacy | First-class acquisition should create an `acquisition_bundle` instead. |
| `chrome_media_probe.py` as main acquisition route | Normalize Chrome observations into acquisition signal | Legacy/manual evidence adapter | Legacy | Chrome can still produce user-approved artifacts, but should not be the main platform layer. |
| YouTube cookies main flow | Safe local cookie handoff for yt-dlp | Agent-Reach/user-managed upstream route | Legacy | The new layer records whether cookies were used, never values. |
| Bilibili generic web fallback | Generic page fallback when platform tools fail | Agent-Reach route or degraded bundle | Legacy | Metadata/page fallback must not masquerade as video primary material. |

Agent-Reach is a capability layer. It selects, installs, health-checks, and
routes upstream tools. It does not replace our evidence judgment. Reading is
done by upstream tools such as yt-dlp, Jina Reader, bili-cli, gh CLI, RSS
parsers, or search tools. Its channel contract includes `name`, `description`,
ordered `backends`, `tier`, and `active_backend`, and `agent-reach doctor --json`
is the health-check entrypoint.

## Decision

Use Agent-Reach as the acquisition layer.

- Add `agent-reach-console` as the acquisition controller.
- Add `source-gated-evidence-layer` as the evidence controller.
- Use `acquisition_bundle` as the stable protocol between them.
- Evidence layer reads bundles and builds `source_status.json`; it does not
  fetch from platforms.
- Agent-Reach layer creates bundles; it does not perform source gate, evidence
  audit, claim production, or final report writing.
- Composer consumes audited packs; it does not repair source status or read
  Agent-Reach output directly.

## Options considered

1. Continue maintaining the old platform acquisition in
   `knowledge-video-decomposer`.
2. Fork Agent-Reach and merge all of its logic into this repository.
3. Use Agent-Reach as the upstream acquisition layer and connect it through a
   local `acquisition_bundle` protocol.

## Chosen option

Choose option 3.

Agent-Reach replaces the old second skill's primary acquisition layer, but it
does not replace source gate, evidence audit, or claim production.

## Consequences

- Platform acquisition can follow the Agent-Reach ecosystem instead of being
  hard-coded into this project.
- This project focuses on trustworthy evidence handling, claim auditing, and
  report gates.
- The repository must maintain a stable `acquisition_bundle` schema.
- Old URL acquisition scripts move to legacy compatibility rather than being
  deleted immediately.
- The short-term output layout can keep `10_video` so existing tests and users
  do not break; the medium-term layout should rename this stage to `10_source`.

## Validation

- Local transcript demo still passes.
- Agent-Reach acquire can create `00_acquisition/manifest.json`.
- Bundle ingest can create `10_video/00_source/source_status.json`.
- No primary material means no `video_analysis_pack.md` and no
  `final_report.md`.
- `source_confirmed` and `source_partial` remain the only normal report entry
  statuses.
- `metadata_only`, `secondary_only`, `blocked`, `failed`, or `unsupported`
  produce degraded output and next actions only.
