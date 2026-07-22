# Real-World Validation Log

> Historical v0.5/v0.6 record. Commands and dependency names below are kept as
> experiment evidence and are not current v0.7 usage. Use `docs/validation.md`
> for the active validation matrix.

## v0.6 Architecture Reset

The 2026-07-03 Marx alienation live validation showed the right product
failure mode:

- YouTube pages were visible but yt-dlp hit bot/sign-in checks.
- Bilibili candidates did not yield usable subtitles or primary transcript.
- Search and article results were useful background but not video primary
  material.
- The workflow did not create `video_analysis_pack.md` or `final_report.md`
  without primary material.

That result validates the source gate and motivates the architecture reset.
The problem was not report writing. The problem was that platform acquisition
and evidence judgment lived in the same second skill.

## New Validation Target

The new target is not "all platforms work." The target is:

```text
Agent-Reach acquisition
  -> acquisition_bundle
  -> source-gated evidence
  -> auditable report generation
```

Acceptance checks:

- URL acquisition writes `00_acquisition/manifest.json`.
- Agent-Reach doctor output is saved when available.
- Bundle ingest writes `10_video/00_source/source_status.json`.
- Metadata-only, blocked, failed, and unsupported acquisition do not create
  normal final reports.
- Local transcript/subtitle still reaches source-confirmed analysis.
- Document composer still enforces Source / Inference / Extension.

## Evidence From Prior Live Run

See:

```text
docs/live-marx-alienation-validation-2026-07-03.md
```

Observed statuses:

- YouTube candidates: `source_blocked`
- Bilibili candidates: `source_failed`
- `primary_material_available`: `false`
- `full_analysis_allowed`: `false`
- `video_analysis_pack.md`: not created
- `final_report.md`: not created

In v0.6 terms, those platform attempts should become failed or blocked
acquisition bundles first, then evidence-layer degraded outputs.

## Regression Commands

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
