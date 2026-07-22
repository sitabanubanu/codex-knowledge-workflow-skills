# Changelog

## v0.7.0

- Removed Agent Reach imports, commands, installer, runtime resolver, and
  user-facing acquisition skill.
- Added a project-owned native Provider registry and `kw source` command group.
- Added the `acquire-source-material` Skill and provider-neutral export import.
- Added `web-intent-scout` and `knowledge-learning-article` to the repository
  and managed workflow sync set.
- Changed URL media acquisition to hand raw media to the evidence-layer ASR
  path instead of using an upstream transcription fallback.
- Updated active architecture, installation, manual, platform, protocol,
  troubleshooting, and validation documentation.
- Added independence and no-fabrication regressions for the new acquisition
  boundary.
- Enforced evaluation v2 task/result JSON Schemas and added negative schema
  contract tests.
- Bumped package version to `0.7.0`.

## v0.6.1

- Added Source Status Contract v1 with one authoritative derivation path for
  source state, scope state, pipeline decision, and report permission.
- Made ingest status publication atomic and bound gate receipts to run,
  attempt, operation, artifact bytes, and derived transcript hashes.
- Distinguished local media awaiting ASR from target/scope mismatch.
- Changed ASR artifact validation to fail closed and rebuild the final source
  status from the derived transcript rather than stale pre-ASR state.
- Added MP3/MP4 end-to-end regression coverage through audit, quality gate,
  final report, and transcript-tamper detection.
- Preserved the 2026-07-15 engineering pilot with an explicit limitations
  notice, and added an offline evaluation v2 contract harness with neutral
  inputs, physically separate gold labels, structured scoring, and dirty-run
  release guards.
- Kept the evaluation v2 eight-task track explicitly non-release-grade; it is
  a harness acceptance smoke, not a product superiority result.

## v0.6.0

- Added Acquisition Bundle schema v2 with run, attempt, bundle, target,
  operation, scope, byte-count, and SHA-256 fields.
- Added immutable project-run identity, staged attempts, explicit resume, and
  acquisition/downstream history archives.
- Added backend operation capability checks on top of Agent-Reach doctor.
- Added target/scope source gates so social captions cannot unlock embedded
  video analysis.
- Added gate, analysis, composer, and final-report provenance receipts.
- Changed status, result, export, quality, templates, and batch synthesis to
  reject stale outputs.
- Wired all exposed YouTube acquisition options into the Bundle v2 path and
  added Agent-Reach transcription fallback.
- Added canonical JSON handling for Xiaohongshu and Bilibili OpenCLI output.
- Added centralized persisted-output redaction and new integrity, redaction,
  capability, scope, and provenance tests.
- Reduced the user-facing skill set to four; `knowledge-video-decomposer` is an
  internal compatibility library.
- Added `kw browser-import` and end-to-end browser-export options for formal
  handoff from authorized browser-visible artifacts into Bundle v2.
- Added direct-source claim handling for social posts, web articles, and
  repository documents.
- Added explicit `--youtube-browser edge|chrome` routing and browser-lock
  diagnostics so the control plugin name is not mistaken for login ownership.
- Added a shared Agent-Reach runtime boundary outside Hermes-private Python
  environments, with resolver checks and isolation regression tests.
- Rewrote the default README in Chinese with the project problem statement and
  a direct comparison with Agent-Reach.

## v0.5.0-real-world-validation

- Added realistic offline validation examples for transcript, subtitle, long
  transcript, and batch routes.
- Added a real-world validation log and output quality standard.
- Added regression coverage for realistic local samples and batch synthesis.
- Added actionable failure-path coverage for empty transcripts and missing
  input files.
- Improved CLI handling for empty transcript inputs before expensive workflow
  execution.
- Reworked the user manual around real user tasks, failure handling, and output
  quality checks.

## v0.4.0-cli-synthesis-and-ci

- Added editable `kw` console command installation.
- Split the CLI compatibility entrypoint into `kw_cli.main`.
- Added batch content-level synthesis outputs based on approved claim maps.
- Added Chrome visible transcript example.
- Expanded GitHub Actions offline validation to Ubuntu and Windows across
  Python 3.10, 3.11, and 3.12.
- Added release checklist documentation.

## v0.3.1-validation-and-release

- Added product quickstart, install guide, and demo transcript example.
- Added `kw.py` CLI wrappers for doctor, validation, batch, templates, quality,
  Chrome probe, and result indexing.
- Added Chinese final-report support and language-match auditing.
- Added route-readiness diagnostics and Markdown/JSON doctor outputs.
- Added richer batch research indexing and structured batch JSON.
- Added structured deterministic template outputs.
- Added Chrome probe relative-file handoff and exported-subtitle example.
- Added aggregate validation summaries through `kw.py validate`.
- Added cross-platform sync script for macOS/Linux shells.

## v0.2-real-workflow-alpha

- Added real workflow acceptance tooling.
- Added sync script for local Codex skill installation.
- Added live platform and ASR smoke summaries.
- Added Chrome probe contract.

## v0.1.0-beta

- Initial public beta package for the three knowledge workflow skills.
