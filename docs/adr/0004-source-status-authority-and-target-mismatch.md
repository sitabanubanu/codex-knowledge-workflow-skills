# ADR 0004: Source-status authority and target mismatch

## Decision

The Source Gate is the final authority for `10_video/00_source/source_status.json`
and `gate_receipt.json` in the public `kw.py ingest/run/resume` workflow.

Internal processors such as transcript normalization and ASR may create or
update provisional stage artifacts, but the Source Gate must rebuild and
validate the final status before downstream audit is allowed.

New canonical statuses use `schema_version: 1`. The existing `source_status`
enum remains unchanged for v0.6 compatibility:

- `source_confirmed`
- `source_partial`
- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`

Two orthogonal fields make the gate decision explicit:

- `scope_status`: `matched`, `partial_match`, `target_mismatch`,
  `pending_derivation`, or `not_evaluated`;
- `pipeline_decision`: `continue_full`, `continue_partial`, or
  `stop_before_audit`.

Primary material with the wrong scope remains
`source_status: degraded_report_only` for compatibility, but it is recorded as
`scope_status: target_mismatch` and `pipeline_decision: stop_before_audit`.
The workflow may write a degraded mismatch explanation, but it must not enter
audit or produce a normal report.

Local audio or video awaiting ASR is not a target mismatch. It is recorded as
`scope_status: pending_derivation` and remains stopped before audit until a
derived transcript is validated.

## Context

The v0.6 ASR path could write a complete status, validate it, and then have
`kw_cli.ingest` replace it with a separately constructed status missing fields
required downstream. Strict ASR validation was also returned as data without
being enforced as a process failure.

The evaluation additionally used one action label to represent two different
questions: whether downstream analysis must stop and whether a user-facing
degraded explanation is allowed. That made safe target-mismatch behavior look
like a product error.

## Options considered

1. Add `failed_probes: []` only in the ASR caller.
   Rejected because other writers could continue to drift.
2. Add `target_mismatch` to the existing `source_status` enum.
   Rejected for this release because it would change the public state machine
   and still mix material facts with permissions.
3. Keep the public enum and add explicit scope and pipeline dimensions.
   Chosen because it fixes the ambiguity additively.

## Write transaction

Canonical status publication follows this order:

1. Build a candidate through the shared contract.
2. Validate it in memory.
3. Write a temporary file in the destination directory.
4. Atomically replace `source_status.json`.
5. Read and validate the stored status.
6. Write `gate_receipt.json` bound to the stored status hash and manifest hash.
7. Allow downstream audit only when both status and receipt are current.

Validation failure must stop the current stage. Validators must not silently
add missing required fields.

## Compatibility

Unversioned historical statuses may be displayed by status/reporting commands,
but a new canonical ingest or resume must regenerate a versioned status before
audit. Existing project trees are not rewritten in bulk.

Legacy acquisition and platform runners remain compatibility implementations.
They cannot bypass Bundle v2 or the final Source Gate publication step.

## Consequences

- ASR and normalization remain reusable internal processors.
- The public workflow has one final state authority.
- Target mismatch can stop analysis while still allowing a safe explanation.
- Existing enum consumers continue to work.
- New canonical outputs become stricter than historical unversioned outputs.

## Out of scope

- acquisition-provider routes or backend selection.
- Browser-host identity and browser control.
- Renaming `10_video` to `10_source`.
- Rewriting segmentation, evidence extraction, or document composition.
- Adding learning or practice features.

## Validation

- Table-driven contract tests for complete, partial, mismatch, pending ASR,
  secondary, blocked, failed, and unsupported cases.
- Negative tests for missing fields and contradictory permissions.
- MP3 and MP4 fixture paths through ASR, audit, compose, and final report.
- Receipt tamper checks for manifest, status, and derived transcript hashes.
