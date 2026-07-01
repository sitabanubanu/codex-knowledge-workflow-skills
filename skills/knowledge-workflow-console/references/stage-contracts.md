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
- subtitle_segments.json
- syntax_segments.json
- argument_segments.json
- concepts.json
- examples.json
- claims.json
- analogies.json
- source_logic.md
- logic_graph.json
- evidence_map.json
- claim_source_audit.json
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

Use `scripts/end_to_end_runner.py` for the productized transcript-to-document
workflow. Supported inputs:

- `--input-transcript`: normalize a local transcript/subtitle, then run the
  decomposition and document planning stages.
- `--input-media`: run local ASR, then run the decomposition and document
  planning stages.
- `--input-url`: run platform media acquisition first. If subtitles are
  acquired, normalize them. If audio is acquired, run ASR. If no primary
  material is acquired, stop at degraded acquisition output without creating a
  full analysis pack.

It orchestrates existing stage scripts and writes:

```text
logs/run_state.json
logs/end_to_end_steps.json
logs/end_to_end_summary.json
10_video/05_gap_check/evidence_audit.json
10_video/05_gap_check/evidence_map.json
10_video/05_gap_check/claim_source_audit.json
10_video/05_gap_check/gap_check.md
10_video/video_analysis_pack.md
20_document/composer_intake.json
20_document/commitments.md
20_document/source_reconstruction.md
20_document/claim_map.json
20_document/expansion_plan.md
20_document/report_outline.md
20_document/quality_check.md
```

URL mode may also write:

```text
10_video/00_source/platform_media_result.json
10_video/00_source/platform_media_notes.md
10_video/00_source/degraded_acquisition_report.md
```

When URL mode stops degraded, it must not write:

```text
10_video/01_transcript/*
10_video/02_segments/*
10_video/03_inventory/*
10_video/04_logic/*
10_video/05_gap_check/*
10_video/video_analysis_pack.md
20_document/*
```

It must not write:

```text
20_document/draft_report.md
20_document/final_report.md
30_final/*
```

If any stage fails, stop at that stage and read `logs/end_to_end_steps.json`
before retrying.

## Preflight Contract

Producer: knowledge-workflow-console

Consumer: user-facing closeout, end-to-end runner planning

Use `scripts/workflow_preflight.py` before long or uncertain runs. It writes
only advisory planning artifacts when requested:

```text
logs/preflight.json
logs/preflight.md
```

It must not create `10_video`, `20_document`, `video_analysis_pack.md`, or
`final_report.md`.

Suggested fields:

```json
{
  "runner": "knowledge-workflow-preflight",
  "input_kind": "url|media|transcript_or_subtitle|unknown",
  "platform": "youtube|x|xiaohongshu|douyin|bilibili|web_video|local|unknown",
  "requested_mode": "quick|standard|audit",
  "estimated_success": "high|medium-high|medium|low-medium|low|unknown",
  "route": "",
  "primary_material_policy": "",
  "possible_primary_paths": "",
  "user_action_likely": "",
  "full_report_possible": "",
  "allowed_outputs": [],
  "next_step": ""
}
```

## Status Summary Contract

Producer: knowledge-workflow-console

Consumer: user-facing closeout

Use `scripts/workflow_status_summary.py` to condense current project state into:

```text
logs/status_summary.json
logs/status_summary.md
```

It reads existing artifacts only. It must not change source status, create
analysis artifacts, or approve final reports.

### logs/run_state.json

Purpose: resumable machine state for long transcript, media, and URL workflows.

Suggested fields:

```json
{
  "runner": "knowledge-workflow-end-to-end-runner",
  "schema_version": 2,
  "mode": "local_transcript|local_media|platform_url",
  "status": "running|completed|failed",
  "workflow_outcome": "analysis_pack_and_document_planning|degraded_acquisition_only",
  "project_root": "",
  "video_root": "",
  "document_root": "",
  "input_transcript": "",
  "input_media": "",
  "input_url": "",
  "input_identity": "",
  "input_hash": "",
  "route_decision": "",
  "resume_enabled": false,
  "resume_from_stage": "",
  "resume_after_stage": "",
  "resume_policy": "stage_input_hash_output_hash_and_expected_outputs",
  "degraded_reason": "",
  "failure_reason": "",
  "user_action_required": "",
  "current_stage": "",
  "next_stage": "",
  "stages": [
    {
      "stage": "transcript_normalizer",
      "status": "running|completed|failed|skipped",
      "returncode": 0,
      "command": [],
      "input_files": [],
      "input_hash": "",
      "output_files": [],
      "output_hash": "",
      "resume_output_files": [],
      "resume_output_hash": "",
      "resume_decision": "",
      "skipped_reason": "",
      "failure_reason": "",
      "retry_policy": {
        "automatic_retry_allowed": false,
        "resume_from_stage": "transcript_normalizer",
        "resume_hint": "--resume --resume-from-stage transcript_normalizer",
        "user_action_required": ""
      },
      "started_at": "",
      "completed_at": "",
      "failed_at": "",
      "stderr": ""
    }
  ],
  "stage_history": []
}
```

Resume rule:

- `--resume` may skip a stage only when run state marks that stage
  `completed` or `skipped`, the stage's expected output files still exist, the
  current stage input hash matches the recorded input hash, and the current
  stable resume output hash matches the recorded resume output hash.
- `stages` stores the latest record for each stage. `stage_history` appends
  every running, skipped, completed, and failed record so failed attempts remain
  auditable after a later rerun.
- If expected outputs are missing, rerun the stage and record
  `resume_decision: "expected_outputs_missing"`.
- If the workflow input file content changes at the same path, reject resume
  before running stages.
- Use `--resume-from-stage <stage>` to rerun that stage and all later stages
  while still allowing earlier matching stages to be skipped.
- Use `--resume-after-stage <stage>` to rerun the stage immediately after the
  named stage and all later stages. Do not pass both `--resume-from-stage` and
  `--resume-after-stage` in the same run.
- URL mode may skip `platform_media_runner` only when
  `10_video/00_source/platform_media_result.json`,
  `10_video/00_source/platform_media_notes.md`, and
  `10_video/00_source/source_status.json` still exist.
- Because URL subtitle normalization or ASR can legitimately update
  `00_source/source_status.json`, `platform_media_runner` uses only
  `platform_media_result.json` and `platform_media_notes.md` for its stable
  resume output hash while still requiring `source_status.json` to exist.
- If a stage fails, preserve the failed record and do not continue downstream.
- Failed and degraded runs must write `failure_reason`, `degraded_reason`, or
  `user_action_required` so the next agent can see whether the user should
  provide subtitles, a transcript, local audio/video, exported cookies, or a
  corrected upstream artifact.
