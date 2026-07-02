# Phase 3 Plan: Doctor And Installation Diagnostics

## Goal

Make setup failures actionable. A user should be able to run `kw.py doctor` and
understand which route is ready, which route needs setup, and which warning is
only informational.

## Scope

- Add route-readiness diagnostics to the doctor report.
- Keep the full JSON and Markdown report available for audits.
- Make the default CLI output readable for humans.
- Align installation and troubleshooting docs with the new output shape.

## Out Of Scope

- No source acquisition changes.
- No platform bypass behavior.
- No new downloader, ASR, or browser automation dependency.
- No weakening of source gates or document quality gates.

## Measures

- `doctor` reports route readiness for local transcript, local subtitle,
  local media ASR, platform preflight, YouTube cookies + JavaScript, Chrome
  observation, and Chinese artifact writing.
- Default stdout is concise.
- `--json`, `--pretty`, `--output-json`, and `--output-md` preserve full
  machine-readable and auditable diagnostics.
- Troubleshooting tells users how to interpret warn/fail states without
  implying platform success is guaranteed.

## Validation

- Compile `kw.py` and `doctor.py`.
- Run doctor self-test.
- Generate real JSON and Markdown doctor outputs.
- Confirm route-readiness rows exist in both JSON and Markdown.
- Run regression and real workflow acceptance tests.
- Sync installed skills and verify installed copies.
