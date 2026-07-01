# Release Notes

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
