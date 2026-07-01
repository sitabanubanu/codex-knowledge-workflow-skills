# Output Layout

Default root:

```text
outputs/knowledge-workflow/<project-id>/
```

Important files:

```text
result_index.md
logs/preflight.json
logs/run_state.json
logs/status_summary.json
logs/result_index.json
10_video/00_source/source_status.json
10_video/01_transcript/clean_transcript.jsonl
10_video/05_gap_check/evidence_audit.json
10_video/video_analysis_pack.md
20_document/quality_gate.json
20_document/final_report.md
30_final/
```

Start with `result_index.md`. It is designed for users. The deeper JSON and
Markdown files are for audit, debugging, and reuse.
