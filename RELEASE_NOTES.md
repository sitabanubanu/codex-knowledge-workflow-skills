# Release Notes

## Unreleased

### Added

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

Latest local validation:

```powershell
python .\kw.py validate --include-sync --output-root .\test_outputs\phase8-validate-full
```

Result: all default offline checks and sync verification passed.

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
