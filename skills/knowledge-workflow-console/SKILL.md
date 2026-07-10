---
name: knowledge-workflow-console
description: Start here for video, audio, subtitle, transcript, or video URL knowledge workflows. Routes inputs through preflight, acquisition, decomposition, document planning, and status summaries. Use for end-to-end runs; do not use for direct report writing.
---

# Knowledge Workflow Console

Use this skill as the high-level controller for the knowledge workflow.

Core workflow:
1. Classify the user's entry type before doing task work.
2. If subagent-supervisor is installed and the user explicitly requests delegated verification, use it as an optional review layer. Otherwise keep the workflow inside the released workflow skills.
3. Choose quick, standard, or audit mode as defined in references/routing.md.
4. Run scripts/workflow_preflight.py before long URL/media runs or when user expectations are unclear.
5. Route the request by following references/routing.md.
6. Create or reuse the project directory described in references/output-layout.md.
7. Pass intermediate artifacts between stages by following references/stage-contracts.md.
8. For URL or query input, route first to `agent-reach-console`, require `00_acquisition/manifest.json`, then route to `source-gated-evidence-layer`.
9. For local files, build a local acquisition bundle first, then route to `source-gated-evidence-layer`.
10. Use scripts/end_to_end_runner.py only as the legacy compatibility runner while the acquisition-bundle route is the primary path.
11. Treat Chrome as a user-approved reconnaissance or artifact-export route, not as the default platform acquisition path.
12. Do not directly perform detailed evidence analysis or document writing inside this skill; delegate acquisition to `agent-reach-console`, evidence gates to `source-gated-evidence-layer`, and writing to `knowledge-document-composer`.
13. When the user needs a report, run the evidence layer before the document composition stage unless a complete upstream analysis pack already exists.
14. Finish by running scripts/workflow_status_summary.py and scripts/result_index_writer.py when a project directory exists, then report acquisition status, source status, whether a full report is allowed, key artifacts, and next step.

Runner guidance:
- `kw.py run` is now the primary productized route. URL inputs create
  `00_acquisition/manifest.json`, ingest it into `10_video/00_source/source_status.json`,
  and continue only when the source gate allows.
- `scripts/workflow_preflight.py` produces a user-facing route estimate before acquisition. It does not fetch media or create analysis artifacts.
- `scripts/end_to_end_runner.py` remains a legacy compatibility orchestrator. URL mode in that runner calls `knowledge-video-decomposer/scripts/platform_media_runner.py`, but it is no longer the primary route for new URL acquisition.
- Treat `end_to_end_runner.py` as an orchestrator, not an analyzer. It calls the stage scripts and records `logs/run_state.json`, `logs/end_to_end_steps.json`, and `logs/end_to_end_summary.json`; it does not inspect Chrome itself, reconstruct source logic itself, or draft `final_report.md`.
- Use `end_to_end_runner.py --resume` to continue a previous transcript, media, or URL run. Resume skips stages only when the prior run state marks them complete/skipped and the expected output files still exist. In URL mode this prevents repeated platform media acquisition when `platform_media_result.json` already exists.
- For YouTube bot/sign-in blocks, do not read, display, copy, or commit cookie values. The acquisition bundle may record `cookies_used=true` only when a user-authorized route used cookies; it must not record cookie contents.
- For Chrome deep-probe work, browser-visible transcript capture, or pageAssets inspection, create or ingest user-approved artifacts through the acquisition bundle. Do not treat Chrome page metadata as primary material unless it contains the transcript or exported media.
- `scripts/workflow_status_summary.py` condenses `run_state.json`, `source_status.json`, `quality_gate.json`, and output existence into a user-facing status object.
- `scripts/result_index_writer.py` writes `result_index.md` and `logs/result_index.json` as the user-facing entry point for a run. It reads existing artifacts only and must not change source status, create analysis artifacts, or approve final reports.

Read references/routing.md before deciding which skill or tool should run.
Read references/stage-contracts.md before passing artifacts between skills.
Read references/output-layout.md before creating project directories or naming outputs.
