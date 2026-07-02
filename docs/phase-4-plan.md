# Phase 4 Plan: Batch Research Workflow

## Goal

Turn batch mode from a thin loop into a usable research index. A user should be
able to run a CSV batch, see which items succeeded, identify approved reports,
and choose a reading order without opening every project directory first.

## Scope

- Keep each item on the existing `kw.py run` path.
- Enrich `batch_status.csv` with source and quality-gate fields.
- Add `batch_items.json` for structured automation.
- Improve `batch_summary.md`, `recommended_watch_order.md`, and
  `comparative_report.md`.
- Document that batch comparison is readiness-level metadata, not new source
  synthesis.

## Out Of Scope

- No live platform batch crawling.
- No automated cross-source claim synthesis.
- No weakening of per-item source gates.
- No change to individual transcript, ASR, URL, or document-composer behavior.

## Measures

- Every item has a project directory and result index when its run reaches that
  point.
- Batch status records source status, full-analysis permission, quality-gate
  approval, final report path, and template output path.
- Recommended order is deterministic: priority, readiness, then ID.
- Comparative report explicitly separates readiness comparison from source
  claim synthesis.

## Validation

- Run the deterministic batch example.
- Confirm `batch_status.csv`, `batch_items.json`, `batch_summary.md`,
  `recommended_watch_order.md`, and `comparative_report.md`.
- Add regression coverage for the batch outputs.
- Run the full offline regression suite.
