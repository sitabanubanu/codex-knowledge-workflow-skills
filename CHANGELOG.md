# Changelog

## Unreleased

No unreleased changes recorded yet.

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
