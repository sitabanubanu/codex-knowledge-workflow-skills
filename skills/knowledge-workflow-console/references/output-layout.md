# Output Layout

```text
<project>/
  logs/
    run_identity.json
    preflight.json
    preflight.md
    run_state.json
    status_summary.json
    status_summary.md
    result_index.json
  .kw_staging/                         # temporary only
  acquisition_history/                # prior bundles
  run_history/                        # prior downstream trees
  00_acquisition/
    manifest.json
    artifacts/
    logs/
      agent_reach_doctor.json
      route_plan.json
      commands.jsonl
      acquisition_notes.md
  10_video/                            # compatibility name
    00_source/
      source_status.json
      gate_receipt.json
      degraded_source_report.md
    01_transcript/
      clean_transcript.jsonl
    02_segments/
    03_inventory/
    04_logic/
    05_gap_check/
      evidence_audit.json
    video_analysis_pack.md
    source_analysis_pack.md
    analysis_receipt.json
  20_document/
    composer_intake.json
    claim_map.json
    report_outline.md
    composer_receipt.json
    quality_gate.json
    final_report.md
    final_report_receipt.json
  30_final/
  result_index.md
```

## Stable Paths

The stable acquisition handoff is `00_acquisition/manifest.json`. The stable
user entry is `result_index.md`.

`10_video` remains for compatibility even for non-video source targets. Use
`source_analysis_pack.md` for non-video target output when present.

## Current Versus Existing

An output is current only when its receipt matches the current run, bundle,
source, target, upstream receipt hash, and output hash. Existing files without
that chain are stale. Status may list them as stale but must not offer them as
deliverables.

## Generated and Private Data

Keep outputs, histories, staging attempts, cookies, tokens, private browser
exports, and research scratch directories out of Git.
