# ADR 0005: Own the Acquisition Provider Layer

## Status

Accepted for the native-acquisition migration.

## Context

Knowledge Workflow already owns platform execution, Bundle v2, source gating,
ASR, evidence audit, learning delivery, and document delivery. The remaining
Agent-Reach runtime dependency is limited to installation, capability probing,
and two transcription fallbacks. A global readiness check currently blocks all
URL acquisition when Agent-Reach is absent, even when the selected native tool
is installed.

The stable product boundary is `00_acquisition/manifest.json`, not a particular
upstream orchestrator.

## Decision

Replace Agent-Reach with a provider-neutral acquisition layer owned by this
repository.

- Introduce `acquire-source-material` as the acquisition-only Skill.
- Probe and route native providers directly.
- Keep Bundle v2 and the acquisition-to-evidence handoff stable.
- Download admissible media as a Bundle artifact and let the evidence layer
  perform ASR after the source gate.
- Keep explicit browser-host declaration, redaction, staged attempts, hashes,
  and privacy rules unchanged; the separate browser identity project is not a
  workflow dependency.
- Accept historical Agent-Reach bundle values as legacy input, but never
  require or execute Agent-Reach in the current runtime.

## Options Considered

1. Delete Agent-Reach calls and let the workflow console invoke tools directly.
   Rejected because it would mix orchestration, acquisition, and evidence.
2. Vendor the Agent-Reach package. Rejected because it preserves the unwanted
   runtime and update dependency.
3. Own a small provider registry behind Bundle v2. Chosen because it preserves
   the safety boundary and makes providers independently replaceable.

## Consequences

- Native tools such as Jina/curl, yt-dlp, OpenCLI, bili-cli, gh, and MCP remain
  optional external providers; Agent-Reach is no longer an intermediary.
- Provider readiness and route plans become project-owned artifacts.
- Historical manifests remain readable.
- The project must maintain provider probes and operation support tests.
- Agent-Reach removal is reversible through the remote backup branch
  `codex/backup-pre-native-acquisition-20260723`.

## Validation

- Run the full offline validation suite with Agent-Reach resolution disabled.
- Verify native doctor, matrix, plan, URL acquisition, exports, media-ASR,
  source gating, no-fake-report, provenance, and installed-skill synchronization.
- Confirm the active code and Skill routes do not import, execute, or require
  Agent-Reach.
