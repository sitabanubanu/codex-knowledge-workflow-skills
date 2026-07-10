# Changelog

## Unreleased

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
