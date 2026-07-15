# Validation Matrix

Default tests are offline and fixture-based. Real platform and real ASR tests
are opt-in because they depend on external sites, local media, network state,
and user authorization.

## Default Validation

Use the aggregate validator for local release checks:

```powershell
python .\kw.py validate --include-sync
```

For a command plan without running checks:

```powershell
python .\kw.py validate --dry-run
```

The validator writes `validation_summary.json`, `validation_summary.md`, and
per-command logs under `test_outputs/validation/<timestamp>/` unless
`--output-root` is provided.

Equivalent individual commands:

```powershell
python .\kw.py demo
python .\tests\knowledge_workflow_regression.py
python .\tests\real_workflow_acceptance.py
python .\tests\test_acquisition_bundle_schema.py
python .\tests\test_local_bundle_ingest.py
python .\tests\test_source_status_contract.py
python .\tests\test_media_asr_end_to_end.py
python .\tests\test_agent_reach_acquire_offline.py
python .\tests\test_source_gate_from_bundle.py
python .\tests\test_no_fake_report_from_agent_reach_failures.py
python .\tests\test_run_provenance.py
```

The default regression suite also runs realistic offline samples under
`examples/real_world/` and verifies common failure paths such as empty
transcripts and missing input files.

The source-status contract test covers complete, partial, mismatch, pending
ASR, secondary, blocked, failed, and unsupported decisions. The media ASR
end-to-end test uses fixture MP3/MP4 files plus deterministic ASR JSONL and
must reach audit, document quality gate, and `final_report.md`. It also verifies
that changing the derived transcript invalidates the gate receipt.

For manual batch validation:

```powershell
python .\kw.py batch `
  --input .\examples\real_world\batch_links.csv `
  --output-root .\outputs\knowledge-workflow\real-world-batch
```

Record non-CI live runs in `docs/real-world-validation-log.md` and judge output
readiness with `docs/output-quality-standard.md`.

Live platform and real ASR checks stay opt-in:

```powershell
python .\kw.py validate --include-live-platform --include-real-asr
```

## Live Platform Matrix

See:

```text
validation/live_platform_matrix.csv
```

Run only after setting explicit URL environment variables:

```powershell
$env:KW_LIVE_PLATFORM_SMOKE='1'
$env:KW_YOUTUBE_WITH_SUBTITLES_URL='...'
$env:KW_YOUTUBE_WITHOUT_SUBTITLES_URL='...'
$env:KW_YOUTUBE_COOKIES_REQUIRED_URL='...'
$env:KW_X_BLOCKED_URL='...'
$env:KW_XIAOHONGSHU_BLOCKED_URL='...'
$env:KW_DOUYIN_BLOCKED_URL='...'
$env:KW_INVALID_FAILED_URL='https://example.invalid/not-a-video'
python .\tests\live_platform_smoke.py
```

## Real ASR Matrix

See:

```text
validation/real_asr_matrix.csv
```

Run only after setting explicit media environment variables:

```powershell
$env:KW_REAL_ASR_SMOKE='1'
$env:KW_REAL_ASR_MP3='C:\path\sample.mp3'
$env:KW_REAL_ASR_MP4='C:\path\sample.mp4'
python .\tests\asr_integration.py
```

Record `source_status`, transcript existence, ASR reports, quality notes, and
failure reasons for each real sample.
