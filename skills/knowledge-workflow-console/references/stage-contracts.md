# Stage Contracts

Pass information between skills through files. Do not rely only on conversation context.

## Supervision

Producer: subagent-supervisor

Consumers: knowledge-workflow-console, delegated stage skills, user-facing closeout

Location: `logs\`

Create these artifacts only when delegation is used:
- supervisor_plan.md
- subagent_handoffs.jsonl
- subagent_returns.md
- acceptance_report.md
- rework_notes.md

Handoffs must record the assigned route or stage, allowed scope, expected artifacts, stop conditions, and return contract. Acceptance reports must record checked files, pass/partial/rework/fail decisions, and any rework notes.

## 00_scout

Producer: web-intent-scout

Consumers: knowledge-workflow-console, knowledge-video-decomposer

Key artifacts:
- candidate_videos.json
- source_ledger.md
- scout_report.md
- recommendation.md

## 10_video

Producer: knowledge-video-decomposer

Consumer: knowledge-document-composer

Key artifacts:
- metadata.json
- acquisition_notes.md
- chrome_page_snapshot.md
- chrome_screenshot.png
- chrome_notes.md
- raw_transcript.jsonl
- clean_transcript.jsonl
- clean_transcript.md
- syntax_segments.json
- argument_segments.json
- concepts.json
- examples.json
- claims.json
- analogies.json
- source_logic.md
- logic_graph.json
- gap_check.md
- video_analysis_pack.md

## 20_document

Producer: knowledge-document-composer

Consumers: knowledge-workflow-console, user, final export tools

Key artifacts:
- composer_intake.json
- commitments.md
- claim_map.json
- expansion_plan.md
- report_outline.md
- draft_report.md
- quality_check.md
- final_report.md

## 30_final

Producer: knowledge-document-composer or document, presentation, and PDF tools

Consumer: user

Key artifacts:
- final_report.md
- final_report.docx
- final_report.pdf
- presentation_outline.md
- slides.pptx
- briefing_note.md

## General Rules

- Check whether upstream artifacts exist before starting each stage.
- Reuse upstream artifacts when they exist and the user did not request a rerun.
- Return to the corresponding stage when required artifacts are incomplete.
- Record source, tool, timestamp, and confidence for each stage.
- Preserve source spans or timestamps for analysis conclusions whenever possible.
- Keep Source, Inference, and Extension separate.
- When subagent-supervisor is used, check acceptance_report.md before continuing to the next stage or final response.

## End-to-End Runner Contract

Producer: knowledge-workflow-console

Consumers: knowledge-workflow-console, user-facing closeout

Use `scripts/end_to_end_runner.py` only for the local transcript/subtitle route.
It orchestrates existing stage scripts and writes:

```text
logs/run_state.json
logs/end_to_end_steps.json
logs/end_to_end_summary.json
10_video/video_analysis_pack.md
20_document/composer_intake.json
20_document/commitments.md
20_document/source_reconstruction.md
20_document/claim_map.json
20_document/expansion_plan.md
20_document/report_outline.md
20_document/quality_check.md
```

It must not write:

```text
20_document/draft_report.md
20_document/final_report.md
30_final/*
```

If any stage fails, stop at that stage and read `logs/end_to_end_steps.json`
before retrying.

### logs/run_state.json

Purpose: resumable machine state for long local transcript workflows.

Suggested fields:

```json
{
  "runner": "knowledge-workflow-end-to-end-runner",
  "schema_version": 1,
  "mode": "local_transcript",
  "status": "running|completed|failed",
  "project_root": "",
  "video_root": "",
  "document_root": "",
  "input_transcript": "",
  "resume_enabled": false,
  "current_stage": "",
  "next_stage": "",
  "stages": [
    {
      "stage": "transcript_normalizer",
      "status": "running|completed|failed|skipped",
      "returncode": 0,
      "command": [],
      "started_at": "",
      "completed_at": "",
      "failed_at": "",
      "stderr": ""
    }
  ]
}
```

Resume rule:

- `--resume` may skip a stage only when run state marks that stage
  `completed` or `skipped` and the stage's expected output files still exist.
- If expected outputs are missing, rerun the stage.
- If a stage fails, preserve the failed record and do not continue downstream.
