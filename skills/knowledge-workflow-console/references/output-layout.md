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
- run_state.json
- tool_calls.md
- decisions.md
- errors.md
- supervisor_plan.md
- subagent_handoffs.jsonl
- subagent_returns.md
- acceptance_report.md
- rework_notes.md

## Naming Rules

- Use both .jsonl and .md formats for transcripts.
- Use .json for structured analysis.
- Use .md for human-readable notes.
- Use .md for final documents first, then optionally export to .docx, .pdf, or .pptx.
- Store Chrome page state artifacts in `10_video\00_source`.
