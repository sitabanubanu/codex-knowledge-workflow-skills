---
name: knowledge-workflow-console
description: Route and orchestrate the full knowledge workflow across web scouting, video decomposition, document composition, browser inspection, and extraction tools. Use when Codex needs to decide whether to search for videos, inspect a video webpage, process a direct video link, analyze an existing transcript, compose a report, or continue editing prior knowledge-workflow artifacts.
---

# Knowledge Workflow Console

Use this skill as the high-level controller for the knowledge workflow.

Core workflow:
1. Classify the user's entry type before doing task work.
2. Route complex, multi-stage, parallel, high-risk, or explicitly delegated tasks through subagent-supervisor before or around the stage route.
3. Route the request by following references/routing.md.
4. Create or reuse the project directory described in references/output-layout.md.
5. Pass intermediate artifacts between stages by following references/stage-contracts.md.
6. Use scripts/end_to_end_runner.py for the productized local transcript/subtitle path when the user provides an existing transcript file and wants the full gated workflow through `10_video` and `20_document` planning artifacts.
7. Treat Chrome as a high-priority visual page reconnaissance tool for real webpage state, video pages, visible transcripts, login-state context, dynamic content, screenshots, and page context checks.
8. Do not directly perform detailed video analysis, document writing, or subagent supervision inside this skill; delegate those details to knowledge-video-decomposer, knowledge-document-composer, and subagent-supervisor.
9. When the user needs a report, run the video decomposition stage before the document composition stage unless a complete upstream analysis pack already exists.
10. Finish by reporting which stages were used, where artifacts were saved, and what the next step is.

Runner guidance:
- `scripts/end_to_end_runner.py` orchestrates the currently productized local transcript/subtitle route: transcript normalizer, segmenter, inventory extractor, source logic builder, evidence auditor, video analysis pack builder, and document composer runner.
- Treat `end_to_end_runner.py` as an orchestrator, not an analyzer. It calls the stage scripts and records `logs/end_to_end_steps.json` plus `logs/end_to_end_summary.json`; it does not inspect Chrome, fetch media, run ASR, or draft `final_report.md`.
- For platform URLs, browser-derived media, or audio/video requiring ASR, route through the video decomposer acquisition, Chrome, and ASR stages first instead of forcing this local transcript runner.

Read references/routing.md before deciding which skill or tool should run.
Read references/stage-contracts.md before passing artifacts between skills.
Read references/output-layout.md before creating project directories or naming outputs.
