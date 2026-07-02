# Phase 8 Plan: Quality Evaluation

## Goal

Make quality review inspectable by both humans and automation. A report should
not be considered reusable only because it exists; it should pass checks for
source faithfulness, evidence-tier separation, uncertainty, and safety.

## Scope

- Expand `kw.py quality` from a short Markdown checklist into a structured
  review.
- Write both Markdown and JSON quality review artifacts.
- Map checks back to rubric dimensions.
- Keep the review source-gate aligned.

## Out Of Scope

- No model-based grading.
- No weakening final-report quality gates.
- No external fact checking.
- No automatic rewriting of failed reports.

## Measures

- Quality review records source status and final-report approval.
- Checks cover source labels, Source / Inference / Extension sections,
  accepted claim IDs, language match gate, evidence gaps, and privacy.
- Rubric dimensions summarize whether the report is reusable.
- JSON output is available for automation.

## Validation

- Generate a deterministic final report.
- Run `kw.py quality` with Markdown and JSON outputs.
- Assert the review passes and records rubric dimensions.
- Run the full offline regression suite.
