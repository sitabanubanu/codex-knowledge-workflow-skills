---
name: source-gated-evidence-layer
description: Validate Acquisition Bundle v2, enforce analysis-target and artifact-scope gates, normalize or transcribe admitted material, produce claims and evidence audits, write provenance receipts, and degrade safely. Never fetch platform data.
---

# Source-Gated Evidence Layer

Use this skill only after a promoted acquisition bundle exists.

1. Validate schema, contained paths, byte counts, SHA-256, run/source binding,
   privacy fields, and status invariants.
2. Compare `analysis_target` with artifact `content_scope`. Primary post text
   cannot satisfy an embedded-video target.
3. Write `source_status.json` and `gate_receipt.json` for every outcome,
   including blocked and failed outcomes.
4. Continue only for `source_confirmed` or `source_partial` with current gate
   provenance.
5. Normalize admitted text or run ASR for admitted local media. Bind derived
   transcript hashes into the gate receipt.
6. Run segmentation, inventory, source logic, claims, evidence audit, and pack
   building.
7. Write `analysis_receipt.json` bound to the current gate and pack hash.
8. Send only the current audited pack to `knowledge-document-composer`.
9. On a new bundle, archive prior downstream trees under `run_history/`.

For `secondary_only`, `source_blocked`, `source_failed`, or
`degraded_report_only`, write an explicit degraded report and next action. Do
not fetch URLs, call Agent-Reach, repair missing material, promote metadata, or
write a normal final report.

```powershell
python kw.py ingest --bundle <project>\00_acquisition\manifest.json --project-root <project>
python kw.py audit --project-root <project>
```

Read all files under `references/` before changing gate, claim, audit, or
degraded-output behavior.
