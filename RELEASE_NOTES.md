# Release Notes

## Unreleased

### Added

- ADR 0001 for using Agent-Reach as the acquisition layer.
- `docs/acquisition-bundle-protocol.md` defining the stable handoff between
  acquisition and evidence.
- `agent-reach-console` skill for installation, doctor, routing, and bundle
  creation guidance.
- `source-gated-evidence-layer` skill for bundle validation, source gate,
  evidence audit, claim-map rules, quality gates, and degraded outputs.
- `kw_cli/bundle.py`, `kw_cli/agent_reach_adapter.py`, and `kw_cli/ingest.py`
  as CLI-callable skeletons.
- CLI commands: `kw agent-reach install`, `kw agent-reach doctor`,
  `kw acquire`, `kw ingest`, `kw audit`, `kw compose`, and
  `kw validate-bundle`.
- Offline tests for acquisition bundles, local ingest, Agent-Reach acquisition
  mocks, source-gate mapping, and no-fake-report failure paths.

### Changed

- `kw run` now uses the acquisition-bundle route as the primary path.
- Workflow console routing now sends URL/query input through
  `agent-reach-console -> acquisition_bundle -> source-gated-evidence-layer`.
- `knowledge-video-decomposer` platform acquisition scripts are documented as
  legacy compatibility paths.
- `knowledge-document-composer` recognizes `source_analysis_pack.md` before
  falling back to legacy `video_analysis_pack.md`.
- README, Chinese README, installation, user manual, supported-platforms,
  troubleshooting, roadmap, architecture, and validation docs now describe the
  v0.6 architecture reset.

### Validation

Planned local checks:

```powershell
python -m py_compile kw.py kw_cli/main.py kw_cli/bundle.py kw_cli/agent_reach_adapter.py kw_cli/ingest.py
python .\kw.py demo
python .\tests\knowledge_workflow_regression.py
python .\tests\real_workflow_acceptance.py
python .\tests\test_acquisition_bundle_schema.py
python .\tests\test_local_bundle_ingest.py
python .\tests\test_agent_reach_acquire_offline.py
python .\tests\test_source_gate_from_bundle.py
python .\tests\test_no_fake_report_from_agent_reach_failures.py
```

## v0.5.0-real-world-validation

### Added

- `examples/real_world/` with realistic offline transcript, subtitle, long
  transcript, and batch validation samples.
- `docs/real-world-validation-log.md` for tracking offline and live validation
  results.
- `docs/output-quality-standard.md` defining Source / Inference / Extension,
  traceability, gate, and failure standards.
- Regression tests for realistic local samples, real-world batch synthesis,
  empty transcript failures, and missing input failures.

### Changed

- The CLI now catches empty transcript/subtitle inputs before launching the full
  workflow and returns a direct next-action message.
- `USER_MANUAL.md` is reorganized around real user tasks: local transcript,
  subtitle, URL preflight, batch research, output reading, failure handling, and
  validation.
- `README.md` and `docs/validation.md` now point to the realistic offline sample
  path and the v0.5.0 quality documents.

### Validation

Local validation passed with:

```powershell
python .\kw.py validate --include-sync --output-root .\test_outputs\v0.5.0-validate
```

Checks passed:

- compile
- demo
- regression
- real_workflow_acceptance
- sync_verify

## v0.4.0-cli-synthesis-and-ci

### Added

- Editable Python package installation with the `kw` console command.
- `kw_cli` package entrypoint while preserving `python kw.py ...`.
- Batch content-level synthesis artifacts:
  - `cross_source_synthesis.md`
  - `theme_clusters.json`
  - `conflict_map.md`
  - `repeated_claims.md`
  - `unique_insights.md`
  - `recommended_research_path.md`
- Chrome visible transcript example with a saved local transcript artifact.
- Multi-platform CI matrix for Ubuntu and Windows on Python 3.10, 3.11, and
  3.12.
- Release checklist for safe artifact publication.

### Changed

- GitHub Actions now installs the package in editable mode and runs `kw demo`.
- Batch synthesis reads only completed, quality-approved item claim maps and
  cites item IDs plus claim IDs.
- CLI internals are now prepared for further command-level decomposition.

### Validation

Latest GitHub Actions `offline-validation` passed across all matrix jobs:

- Ubuntu latest / Python 3.10, 3.11, 3.12
- Windows latest / Python 3.10, 3.11, 3.12

## v0.3.1-validation-and-release

### Added

- GitHub Actions offline validation for push and pull request checks.
- Chinese final-report rendering and a Language Match quality gate for
  requested Chinese output.
- Route-readiness diagnostics in `kw.py doctor`, including concise default
  output plus full JSON and Markdown diagnostic reports.
- `kw.py validate`, an aggregate offline validation runner that writes JSON,
  Markdown, and per-command logs.
- `batch_items.json` and richer batch summary, recommended order, and
  comparative reports.
- Structured template outputs for study notes, research brief, creator script,
  prompt pack, and action plan.
- Chrome probe exported-subtitle example and relative local-file handoff
  support.
- Cross-platform installation docs, `requirements.txt`, and
  `sync_to_codex_skills.sh`.

### Changed

- `kw.py quality` now writes both Markdown and JSON quality reviews mapped to
  rubric dimensions.
- `kw.py doctor --output-json/--output-md` resolves relative output paths from
  the caller's working directory.
- Batch status now records source status, full-analysis permission, quality
  approval, final report path, and template output path.
- Release and validation docs now point to `kw.py validate --include-sync` for
  local release checks.

### Validation

Latest local validation before release:

```powershell
python .\kw.py validate --include-sync --output-root .\test_outputs\phase9-final-validate
```

Result: all default offline checks and sync verification passed.

GitHub Actions runs the default offline checks on push and pull request:

- `python kw.py demo`
- `python tests/knowledge_workflow_regression.py`
- `python tests/real_workflow_acceptance.py`

## v0.3-product-entry-alpha

Prepared locally as:

```text
dist/codex-knowledge-workflow-skills-v0.3-product-entry-alpha.zip
```

### Added

- Productized `README.md` first screen with a local transcript demo path.
- `QUICKSTART.md` for a predictable first run that avoids platform URL instability.
- `examples/demo_transcript/` with input, run script, and compact expected output shapes.
- `kw.py`, a thin repository CLI for doctor, preflight, run, status, result, demo, and Markdown export.
- `skills/knowledge-workflow-console/scripts/result_index_writer.py`, which
  writes `result_index.md` and `logs/result_index.json` as the user-facing entry
  point for a workflow project.
- Trust and onboarding files: `LICENSE`, `SECURITY.md`, `PRIVACY.md`,
  `SUPPORTED_PLATFORMS.md`, `TROUBLESHOOTING.md`, `CONTRIBUTING.md`,
  `ROADMAP.md`, `CHANGELOG.md`, and `README.zh-CN.md`.
- Quality, template, batch, Chrome probe, and validation productization artifacts.

### Changed

- Workflow console guidance now finishes runs with both status summary and result index artifacts.
- Generated `outputs/` are ignored by Git.
- Product documentation is split into focused entry, security, privacy,
  platform, troubleshooting, architecture, and release-process pages.

## v0.2-real-workflow-alpha

This release moves the project from a beta skill package toward a real local
workflow acceptance build.

### Added

- `sync_to_codex_skills.ps1` for dry-run, sync, and verify workflows between the
  repository and the installed Codex skills directory.
- `tests/fixtures/live_cases.json` for optional real-platform smoke cases.
- Persistent machine-readable summaries for live platform smoke tests.
- Persistent machine-readable summaries for ASR integration smoke tests.
- `tests/real_workflow_acceptance.py`, which validates the local transcript to
  `video_analysis_pack.md`, `quality_gate.json`, and `final_report.md` path.
- `chrome-probe-contract.md`, a structured Chrome deep-probe recording contract
  for future browser-derived media work.

### Changed

- Live platform smoke tests now assert route compatibility, cookie/auth signals
  for cookie-required cases, degraded/failure reasons, and strict failed-URL
  behavior.
- README, user manual, and test documentation now explain sync, summaries, and
  the local acceptance path.
- `knowledge-video-decomposer` now explicitly references the Chrome probe
  contract before Chrome/pageAssets/Playwright inspection.

### Validation

The release was validated with:

```powershell
.\sync_to_codex_skills.ps1 -VerifyOnly
python .\tests\knowledge_workflow_regression.py
python .\tests\live_platform_smoke.py
python .\tests\asr_integration.py
python .\tests\real_workflow_acceptance.py
python .\skills\knowledge-video-decomposer\scripts\doctor.py --self-test
```

### Known Limits

- Live platform coverage still requires user-provided real URLs, optional
  exported cookies, and network/platform availability.
- Real ASR coverage is opt-in and requires local media plus a working
  faster-whisper/ffmpeg environment.
- Chrome deep-probe is now standardized as a contract, but not yet fully
  automated end to end.
