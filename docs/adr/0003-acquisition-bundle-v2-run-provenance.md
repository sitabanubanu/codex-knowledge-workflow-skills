# ADR 0003: Acquisition Bundle v2 and Run-Scoped Provenance

Status: accepted

Date: 2026-07-10

## Context

The first Agent-Reach integration established the correct high-level boundary,
but several implementation gaps could still produce misleading results:

- a backend could be healthy for search but unable to perform transcript
  extraction;
- social-post text could be mistaken for an embedded-video transcript;
- an interrupted or retried acquisition could reuse files from an earlier
  attempt;
- downstream status used file existence, so an old final report could make a
  blocked run look successful;
- backend JSON, URLs, and command logs used inconsistent redaction;
- CLI options existed without reaching the new acquisition path.

These are contract problems, not isolated platform bugs.

## Decision

Adopt Acquisition Bundle schema v2 and make every deliverable run-scoped.

### User-facing layers

The product exposes four skills:

1. `knowledge-workflow-console`: route, preflight, stage control, status, and
   result index.
2. `agent-reach-console`: doctor, capability planning, acquisition, and bundle
   writing only.
3. `source-gated-evidence-layer`: bundle validation, target/scope source gate,
   normalization, claims, and evidence audit.
4. `knowledge-document-composer`: document planning, Source / Inference /
   Extension separation, quality gate, and final report.

`knowledge-video-decomposer` remains an internal compatibility library for the
normalizer, ASR, segmenter, inventory, logic, audit, and pack-builder scripts.
It is no longer a user-facing workflow skill and is not synced as one.

### Capability before execution

An Agent-Reach `active_backend` is executable only when both conditions hold:

- doctor reports `status: ok`;
- the adapter implements the requested `operation` for that backend and input.

Search readiness never implies transcript readiness. A capability mismatch
must create a `blocked` bundle and must not call an unrelated backend command.

### Target and scope

Every v2 bundle records `analysis_target` and every artifact records
`content_scope`. The evidence layer admits primary material only when the
artifact scope satisfies the target. In particular, `social_post_text` cannot
unlock `video_content`; that requires `video_transcript`.

### Immutable run and staged attempts

Each project root owns one `run_id`, source fingerprint, target, and operation.
Reusing it requires `--resume` and an exact identity match. Every acquisition
uses a fresh `attempt_id` under `.kw_staging/`; only a validated bundle is
promoted. Prior bundles move to `acquisition_history/`. Prior downstream
outputs move to `run_history/` when a new bundle is ingested.

### Integrity and provenance

Bundle artifacts carry byte counts and SHA-256 hashes. Relative paths must stay
inside `00_acquisition/`. The evidence and document stages write:

- `10_video/00_source/gate_receipt.json`;
- `10_video/analysis_receipt.json`;
- `20_document/composer_receipt.json`;
- `20_document/final_report_receipt.json`.

Each receipt binds its output hashes to the current run, bundle, source,
target, and upstream receipt. Status, result, export, quality, template, and
batch commands must use these receipts rather than raw file existence.

### Redaction

URLs, command logs, manifests, run state, preflight output, backend JSON, and
failure text pass through centralized redaction before persistence. Cookie
contents are never read or copied. Authorized cookie paths and challenge
parameters may be passed to the upstream command, but their values must not be
persisted.

## Consequences

- Schema v1 remains ingestible as a legacy format, but lacks v2 integrity
  guarantees and emits a warning.
- Explicit project-root reuse without `--resume` now fails by design.
- A changed local file cannot resume under the old run identity.
- Existing old output files may remain in history, but cannot be reported as
  current.
- Browser/Chrome state remains an authorized upstream acquisition mechanism,
  not a source-gate bypass. CAPTCHA, private access, paywalls, and account
  permissions are never bypassed.
- Platform support is reported per operation, not as a single optimistic
  platform checkbox.

## Rollback

The pre-reset release remains protected by the existing stable reference at
commit `e4240c9`. The first reset snapshot is protected by branch
`codex/agent-reach-reset-v1-snapshot` at commit `8309eaf`. This ADR can be
reverted without deleting either protected state.
