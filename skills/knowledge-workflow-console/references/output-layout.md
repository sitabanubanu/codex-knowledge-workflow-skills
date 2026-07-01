# Output Layout

Use this root directory for knowledge workflow outputs:

```text
outputs\knowledge-workflow\<project-id>\
```

## Project ID

- Prefer the video ID, webpage slug, or short topic name.
- Append a date or sequence number when there is a conflict.
- Avoid special characters.
- Keep the name readable.

## Directory Structure

```text
outputs\knowledge-workflow\<project-id>\
  result_index.md
  00_scout\
  10_video\
    00_source\
    01_transcript\
    02_segments\
    03_inventory\
    04_logic\
    05_gap_check\
  20_document\
  30_final\
  logs\
```

## Logs

Store workflow logs in `logs\`:
- preflight.json
- preflight.md
- status_summary.json
- status_summary.md
- result_index.json
- run_state.json
- tool_calls.md
- decisions.md
- errors.md
- supervisor_plan.md
- subagent_handoffs.jsonl
- subagent_returns.md
- acceptance_report.md
- rework_notes.md

## URL / Media Acquisition Outputs

When `end_to_end_runner.py` starts from `--input-url`, store platform
acquisition outputs under `10_video\00_source\`:

- platform_media_result.json
- platform_media_notes.md
- acquisition_runner_report.json
- acquisition_notes.md
- degraded_acquisition_report.md, only when no primary material was acquired

If URL mode acquires subtitles, the normal transcript layout under
`10_video\01_transcript\` may be created by the transcript normalizer.

If URL mode or `--input-media` runs ASR, ASR provenance goes under
`10_video\00_source\` and transcript artifacts under `10_video\01_transcript\`.

## Evidence Audit Outputs

When full or partial decomposition reaches the evidence stage, store pre-pack
audit artifacts under `10_video\05_gap_check\`:

- evidence_audit.json
- evidence_map.json
- claim_source_audit.json
- gap_check.md

`video_analysis_pack.md` and `20_document\` planning artifacts should be created
only after the evidence audit gate passes and `claim_source_audit.json` has zero
blocking claims.

If URL mode has only metadata, blocked state, or failed acquisition, do not
create the full analysis directory appearance beyond `00_source\`, and do not
create `video_analysis_pack.md` or `20_document\` planning artifacts.

## Naming Rules

- Use both .jsonl and .md formats for transcripts.
- Use .json for structured analysis.
- Use .md for human-readable notes.
- Use .md for final documents first, then optionally export to .docx, .pdf, or .pptx.
- Store Chrome page state artifacts in `10_video\00_source`.
- Always treat `result_index.md` as the first user-facing file to open after a run.
