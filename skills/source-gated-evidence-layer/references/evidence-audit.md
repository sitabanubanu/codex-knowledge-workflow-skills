# Evidence Audit

Reuse the internal evidence-audit scripts from `knowledge-video-decomposer`.
That directory is a compatibility library, not a user-facing route.

Required:

- Every claim must have a source span.
- Every source logic node must have evidence.
- Every example must include enough context to be inspectable.
- `evidence_map.json` must exist before pack building.
- `claim_source_audit.json` must exist before pack building.
- `evidence_audit.json` must contain a pack gate decision.
- Pack builder can run only when the audit gate allows a full or partial pack.

The evidence layer may reuse these scripts:

- `transcript_segmenter.py`
- `inventory_extractor.py`
- `source_logic_builder.py`
- `evidence_auditor.py`
- `video_analysis_pack_builder.py`

Do not weaken evidence audit to make acquisition failures look successful.

Before audit, require a current `gate_receipt.json`. After pack generation,
write `analysis_receipt.json` with the gate-receipt hash, evidence-audit hash,
pack filename, and pack SHA-256. A pack without a matching receipt is stale.
