# Real-World Validation Log

This log tracks v0.5.0 real-world validation. Default entries are offline and
deterministic so they can be repeated in CI. Live platform entries must record
the date, environment, and external access condition because those results can
change.

## Acceptance Rules

- A successful sample must produce `result_index.md`.
- A complete analysis must have confirmed or partial primary material.
- Final reports are reusable only when `quality_gate.json` approves them.
- Failed samples must explain the next action and must not produce a fake
  complete report.
- URL-only, metadata-only, screenshot-only, or blocked samples are not source
  material for a full report.

## Offline Samples

| ID | Sample | Route | Purpose | Expected Result | Evidence |
| --- | --- | --- | --- | --- | --- |
| RW-001 | `examples/real_world/transcript_interview.txt` | local transcript | Validate realistic transcript input. | Full audit report can be produced. | Covered by `test_real_world_examples`. |
| RW-002 | `examples/real_world/subtitle_talk.srt` | local subtitle | Validate timestamped subtitle input. | Full audit report can be produced. | Covered by `test_real_world_examples`. |
| RW-003 | `examples/real_world/long_transcript.txt` | long transcript | Validate longer decomposition and Source / Inference / Extension boundaries. | Full audit report can be produced. | Covered by `test_real_world_examples`. |
| RW-004 | `examples/real_world/batch_links.csv` | batch | Validate multi-item synthesis from approved local samples. | Batch status and synthesis files are produced. | Covered by `test_real_world_examples`. |
| RW-005 | `examples/chrome_probe/chrome_observation_url_only.json` | browser observation | Validate URL-only failure boundary. | Source remains failed/degraded until primary material is fetched. | Covered by `test_chrome_url_only_gate`. |
| RW-006 | empty local transcript fixture | invalid transcript | Validate clear failure path. | CLI exits non-zero with a user-facing next action and no final report. | Covered by `test_empty_transcript_failure_is_actionable`. |
| RW-007 | missing local input path | invalid path | Validate missing file classification. | CLI exits non-zero with a user-facing missing/classification error. | Covered by `test_missing_input_failure_is_actionable`. |

## Live Platform Samples

Live rows are optional and should be filled by the maintainer when authorized
test URLs are available.

| Date | URL / Source | Route Tried | Environment | Result | Next Action |
| --- | --- | --- | --- | --- | --- |
| pending | YouTube with subtitles | platform subtitles | maintainer-provided URL | pending | Set `KW_YOUTUBE_WITH_SUBTITLES_URL` and run `tests/live_platform_smoke.py`. |
| pending | YouTube without subtitles | platform audio or ASR | maintainer-provided URL | pending | Confirm ASR availability or record degraded status. |
| pending | cookies-required page | authorized cookies | maintainer-provided cookies | pending | Use only user-exported cookies; never commit cookies. |
| 2026-07-03 | Marxism / alienated labor / subjectivity-loss video candidates | YouTube, Bilibili, Chrome page observation, Hearsay fallback | Windows, Asia/Shanghai; no exported cookies; no committed primary media | blocked/degraded | See `docs/live-marx-alienation-validation-2026-07-03.md`. Provide an official transcript/subtitle, local media for ASR, browser-derived transcript export, or authorized cookies before expecting a full report. |

## Issue Triage

Classify every finding before fixing it:

- `must_fix`: fake complete report, wrong source status, broken local route, or
  missing quality gate.
- `should_fix`: confusing CLI output, unclear documentation, or missing next
  action.
- `defer`: live platform access, account, region, CAPTCHA, paywall, or local
  dependency condition outside the offline product contract.
