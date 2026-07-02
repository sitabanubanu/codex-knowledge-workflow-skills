# Phase 5 Plan: Templates And Examples

## Goal

Make template outputs useful as reusable knowledge assets rather than simple
report excerpts.

## Scope

- Keep the existing template names.
- Render structured outputs for study notes, research brief, creator script,
  prompt pack, and action plan.
- Use only approved final-report sections and claim-map entries.
- Add regression coverage for every template.
- Document the no-new-source-claims boundary.

## Out Of Scope

- No model-written freeform synthesis.
- No external research.
- No new claims beyond the final report, video analysis pack, and claim map.
- No change to final-report approval gates.

## Measures

- `kw.py template --list` exposes all templates.
- Each template writes a distinct section structure.
- Each template repeats source-gate status and quality-gate approval.
- Each template states that it reorganizes approved material and does not add
  new source claims.

## Validation

- Generate all templates from a deterministic local transcript run.
- Assert template-specific headings exist.
- Assert the no-new-source-claims boundary exists.
- Run the full offline regression suite.
