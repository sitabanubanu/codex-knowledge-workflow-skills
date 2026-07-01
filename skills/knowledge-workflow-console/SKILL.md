---
name: knowledge-workflow-console
description: Start here for video, audio, subtitle, transcript, or video URL knowledge workflows. Routes inputs through preflight, acquisition, decomposition, document planning, and status summaries. Use for end-to-end runs; do not use for direct report writing.
---

# Knowledge Workflow Console

Use this skill as the high-level controller for the knowledge workflow.

Core workflow:
1. Classify the user's entry type before doing task work.
2. If subagent-supervisor is installed and the user explicitly requests delegated verification, use it as an optional review layer. Otherwise keep the workflow inside the three released skills.
3. Choose quick, standard, or audit mode as defined in references/routing.md.
4. Run scripts/workflow_preflight.py before long URL/media runs or when user expectations are unclear.
5. Route the request by following references/routing.md.
6. Create or reuse the project directory described in references/output-layout.md.
7. Pass intermediate artifacts between stages by following references/stage-contracts.md.
8. Use scripts/end_to_end_runner.py for the productized transcript-to-document workflow when the user provides an existing transcript/subtitle file, a local media file, or a platform URL and wants the gated workflow through `10_video` and `20_document` planning artifacts.
9. Treat Chrome as a high-priority visual page reconnaissance tool for real webpage state, video pages, visible transcripts, login-state context, dynamic content, screenshots, and page context checks.
10. Do not directly perform detailed video analysis or document writing inside this skill; delegate those details to knowledge-video-decomposer and knowledge-document-composer.
11. When the user needs a report, run the video decomposition stage before the document composition stage unless a complete upstream analysis pack already exists.
12. Finish by running scripts/workflow_status_summary.py when a project directory exists, then report the user-facing status, key artifacts, and next step.

Runner guidance:
- `scripts/workflow_preflight.py` produces a user-facing route estimate before acquisition. It does not fetch media or create analysis artifacts.
- `scripts/end_to_end_runner.py` orchestrates the productized local transcript/subtitle route, local media ASR route, and platform URL route. URL mode calls `knowledge-video-decomposer/scripts/platform_media_runner.py` first, normalizes acquired subtitles, runs ASR on acquired audio when needed, or stops at a degraded acquisition report when no primary material exists.
- Treat `end_to_end_runner.py` as an orchestrator, not an analyzer. It calls the stage scripts and records `logs/run_state.json`, `logs/end_to_end_steps.json`, and `logs/end_to_end_summary.json`; it does not inspect Chrome itself, reconstruct source logic itself, or draft `final_report.md`.
- Use `end_to_end_runner.py --resume` to continue a previous transcript, media, or URL run. Resume skips stages only when the prior run state marks them complete/skipped and the expected output files still exist. In URL mode this prevents repeated platform media acquisition when `platform_media_result.json` already exists.
- For Chrome deep-probe work, browser-visible transcript capture, or pageAssets inspection, route through the video decomposer Chrome gate before or around URL mode. The end-to-end runner consumes acquired files and source-status artifacts; it does not control Chrome.
- `scripts/workflow_status_summary.py` condenses `run_state.json`, `source_status.json`, `quality_gate.json`, and output existence into a user-facing status object.

Read references/routing.md before deciding which skill or tool should run.
Read references/stage-contracts.md before passing artifacts between skills.
Read references/output-layout.md before creating project directories or naming outputs.
