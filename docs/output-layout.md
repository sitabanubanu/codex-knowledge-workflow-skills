# Output Layout

Default root:

```text
outputs/knowledge-workflow/<project-id>/
```

Start with `result_index.md`.

Important current-run files:

```text
logs/run_identity.json
logs/preflight.json
logs/run_state.json
logs/status_summary.json
logs/result_index.json
00_acquisition/manifest.json
10_video/00_source/source_status.json
10_video/00_source/gate_receipt.json
10_video/01_transcript/clean_transcript.jsonl
10_video/05_gap_check/evidence_audit.json
10_video/video_analysis_pack.md
10_video/source_analysis_pack.md
10_video/analysis_receipt.json
20_document/claim_map.json
20_document/composer_receipt.json
20_document/quality_gate.json
20_document/final_report.md
20_document/final_report_receipt.json
30_final/
```

Retry history lives under `acquisition_history/` and `run_history/`. Those
files are auditable history, not current deliverables.

An output is current only when its receipt and hash chain matches the current
acquisition manifest. File existence alone is insufficient.
