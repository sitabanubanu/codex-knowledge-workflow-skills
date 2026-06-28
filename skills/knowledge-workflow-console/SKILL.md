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
6. Treat Chrome as a high-priority visual page reconnaissance tool for real webpage state, video pages, visible transcripts, login-state context, dynamic content, screenshots, and page context checks.
7. Do not directly perform detailed video analysis, document writing, or subagent supervision inside this skill; delegate those details to knowledge-video-decomposer, knowledge-document-composer, and subagent-supervisor.
8. When the user needs a report, run the video decomposition stage before the document composition stage unless a complete upstream analysis pack already exists.
9. Finish by reporting which stages were used, where artifacts were saved, and what the next step is.

Read references/routing.md before deciding which skill or tool should run.
Read references/stage-contracts.md before passing artifacts between skills.
Read references/output-layout.md before creating project directories or naming outputs.
