# Phase 7 Plan: Validation Hardening

## Goal

Make validation repeatable and auditable from one CLI entry point while keeping
live platform and real ASR checks explicit opt-ins.

## Scope

- Add `kw.py validate`.
- Write JSON and Markdown validation summaries.
- Capture stdout/stderr logs per command.
- Keep default validation offline and deterministic.
- Document release and validation usage.

## Out Of Scope

- No CI service setup in this phase.
- No mandatory live platform checks.
- No mandatory real ASR model execution.
- No weakening tests to make validation pass.

## Measures

- `kw.py validate --dry-run` shows the planned checks and writes summaries.
- Default validation includes compile, demo, regression, and real workflow
  acceptance.
- Sync verification is explicit through `--include-sync`.
- Live platform and ASR checks are explicit through `--include-live-platform`
  and `--include-real-asr`.

## Validation

- Compile `kw.py` and regression tests.
- Run `kw.py validate --dry-run`.
- Add regression coverage for the dry-run summary.
- Run the full offline regression suite.
