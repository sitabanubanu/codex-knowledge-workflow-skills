# Evidence Audit

Retain the existing evidence audit rules from `knowledge-video-decomposer`.

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
