# Acceptance Checklist

Supervisor must not accept based only on summary.

## Required Checks

- Confirm claimed files exist.
- Confirm only allowed files changed.
- Confirm expected artifacts present.
- Confirm content satisfies criteria.
- Confirm validation run.
- Confirm no forbidden next step was taken.
- Confirm there is no mojibake, empty file, or placeholder content.
- Confirm risks reported.

## Verification Practice

The main Agent must inspect the real workspace before accepting returned work. Read the relevant files directly, run the requested or appropriate validation, and when scope or timing matters, check LastWriteTime values or the directory tree to verify what was created or changed.

## Acceptance Status

- Pass: all required checks pass and no material risk remains.
- Partial: useful work is present, but a limited issue or missing evidence remains.
- Rework: the result can be corrected within the original scope.
- Fail: the result is unusable, unsafe, out of scope, or should be reassigned.

## Acceptance Report Template

Status:

Evidence Checked:

Issues:

Required Rework:

Next Step:
