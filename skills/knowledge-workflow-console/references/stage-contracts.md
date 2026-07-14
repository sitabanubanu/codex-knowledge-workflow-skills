# Stage Contracts

## Preflight

Producer: workflow console.

Outputs:

```text
logs/preflight.json
logs/preflight.md
```

Input URLs must be redacted before persistence. Preflight estimates a route; it
does not acquire or approve material.

## Run Identity

```text
logs/run_identity.json
```

Binds one project root to run id, platform, source id/fingerprint, target, and
operation. Reuse requires explicit matching resume.

## Acquisition

Producer: agent-reach-console or local bundle builder.

```text
00_acquisition/manifest.json
00_acquisition/artifacts/*
00_acquisition/logs/agent_reach_doctor.json
00_acquisition/logs/route_plan.json
00_acquisition/logs/commands.jsonl
```

Bundle v2 artifacts require contained relative paths, scope, class, coverage,
run/source ids, bytes, and SHA-256. The bundle must validate before promotion.

## Source Gate

Producer: source-gated-evidence-layer.

```text
10_video/00_source/source_status.json
10_video/00_source/gate_receipt.json
10_video/00_source/degraded_source_report.md   # when blocked/degraded
```

The gate compares target with artifact scope. Every outcome gets a receipt.

## Normalization or ASR

```text
10_video/01_transcript/clean_transcript.jsonl
```

Normalization runs only on admitted task-primary text. Local media requires
ASR; the derived transcript hash is added to the gate receipt.

## Evidence Audit

```text
10_video/02_segments/*
10_video/03_inventory/*
10_video/04_logic/*
10_video/05_gap_check/evidence_audit.json
10_video/video_analysis_pack.md
10_video/source_analysis_pack.md               # non-video target
10_video/analysis_receipt.json
```

The analysis receipt binds the current gate, evidence audit, and selected pack.

## Document Planning

Producer: knowledge-document-composer.

```text
20_document/composer_intake.json
20_document/claim_map.json
20_document/report_outline.md
20_document/composer_receipt.json
```

The composer receipt binds claim map and intake to the analysis receipt.

## Final Delivery

```text
20_document/quality_gate.json
20_document/final_report.md
20_document/final_report_receipt.json
```

The final receipt binds quality gate and report to the composer receipt. Export,
quality review, normal templates, and batch synthesis require this receipt.

## Status and Result

```text
logs/run_state.json
logs/status_summary.json
logs/status_summary.md
logs/result_index.json
result_index.md
```

These consumers read receipts and hashes. They may report stale files, but must
never convert stale file existence into success.

## History

```text
acquisition_history/<attempt-or-bundle-id>/
run_history/<attempt-or-bundle-id>/
```

History is read-only evidence of prior attempts and is never current output.
