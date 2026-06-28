# Known Failures

Use this file before hardening or debugging the knowledge-video workflow. It freezes the failures observed during real workflow runs so later changes solve the actual problems instead of adding more loose instructions.

## Purpose

This is not a user-facing apology log. It is the repair backlog for the executable workflow.

Each failure below must be handled by one or more future hardening items such as `chrome-routing.md`, `source-status.md`, `acquisition_probe.py`, `workflow_runner.py`, `artifact_validator.py`, `write_artifact.py`, or stricter subagent budget rules.

## Failure 1: Platform Block Did Not Switch To Chrome

Observed behavior:

- A YouTube URL returned bot-confirmation and HTTP 429 from yt-dlp.
- The workflow continued trying alternate external extraction paths instead of switching immediately to Chrome page inspection.
- The run consumed excessive time and tokens without acquiring a transcript or audio source.

Cause:

- The skill said Chrome was high priority, but the route did not define a hard stop condition for `yt-dlp bot/429 -> Chrome required`.
- The agent treated the platform block as an extraction retry problem instead of a browser-state problem.
- Chrome setup instructions were not encoded in the video workflow as a required branch.

Consequence:

- The workflow spent too long on failing extractors.
- The user did not receive the requested transcript or complete video analysis.
- The final output became a degraded report instead of the intended video decomposition.

Repair direction:

- Add `references/chrome-routing.md`.
- Add a hard rule: bot confirmation, HTTP 429, RequestBlocked, CAPTCHA, login-required, or robot-check from a platform extractor must set `source_status = chrome_required`.
- Stop further external extractor retries after this status.
- If Chrome is unavailable, set `source_status = blocked_chrome_unavailable` and stop rather than continuing to secondary sources.

## Failure 2: Chrome Skill Was Present But Not Correctly Used

Observed behavior:

- The environment contained the Chrome skill.
- The agent looked for a direct `chrome.*` tool and concluded Chrome was not callable.
- The correct Chrome route required reading the Chrome skill bootstrap and using the browser-client through the Node REPL.

Cause:

- The video workflow did not include concrete Chrome bootstrap instructions or a reference to the Chrome skill workflow.
- The agent confused "no direct chrome namespace was visible" with "Chrome cannot be used."

Consequence:

- The workflow skipped the user's preferred browser path.
- Visible page state, transcript buttons, subtitles, description, and chapters were not checked in Chrome.

Repair direction:

- `chrome-routing.md` must explicitly say how to proceed when Chrome is requested or required.
- The workflow console must treat Chrome as a required route after platform blocking.
- Chrome failure must be recorded as `blocked_chrome_unavailable`, not silently replaced by unrelated web scraping.

## Failure 3: No Transcript Or Audio But Analysis Continued

Observed behavior:

- No original transcript, captions, or audio-derived ASR were acquired.
- The workflow still created a `video_analysis_pack.md` and a `final_report.md`.
- The report was caveated, but the stage shape still resembled a completed decomposition.

Cause:

- The workflow had no executable source-status gate.
- The skill described desired artifacts but did not enforce which source states are allowed to enter full decomposition.

Consequence:

- A secondary-source outline could be mistaken for a valid analysis input.
- The workflow looked more complete than it really was.

Repair direction:

- Add `references/source-status.md`.
- Add `acquisition_status.json` with `can_enter_full_decomposition`.
- For `metadata_only`, `secondary_outline_only`, `blocked_platform`, or `blocked_chrome_unavailable`, forbid full video decomposition.
- Allow only `acquisition_failure_report.md` or explicitly degraded acquisition reports.

## Failure 4: Secondary Sources Were Used Too Late And Too Broadly

Observed behavior:

- Podwise and search snippets were used after primary extraction failed.
- They helped identify the video and outline, but they could not replace the original transcript.

Cause:

- The workflow lacked a source-type hierarchy.
- Firecrawl, Podwise, and search snippets were not clearly marked as context-only or secondary evidence.

Consequence:

- A secondary outline risked being treated as enough material for content analysis.
- The report could overstate confidence if not carefully caveated.

Repair direction:

- Add source classes such as `primary_transcript`, `primary_audio_asr`, `browser_visible_transcript`, `platform_metadata`, `secondary_summary`, and `search_snippet`.
- Only primary transcript/audio/browser-visible transcript can support full decomposition.
- Firecrawl and Podwise can support context, metadata, and degraded outlines only.

## Failure 5: Hearsay Timeout Was Treated As A Tool Mystery

Observed behavior:

- Hearsay timed out while fetching YouTube metadata.
- Earlier discussion spent time on whether Hearsay was broken or unpaid.

Cause:

- The workflow lacked separate timeout categories for metadata fetch, audio acquisition, model loading, and transcription.
- Hearsay URL ingestion was attempted even after platform-level blocking signals were already present.

Consequence:

- Time was spent diagnosing the wrong layer.
- The run did not move toward Chrome or local-file fallback quickly enough.

Repair direction:

- `acquisition_probe.py` must distinguish metadata timeout, platform block, download failure, ASR timeout, and model-load timeout.
- Hearsay URL ingestion should not be tried repeatedly after `chrome_required` is set.
- Hearsay should be used mainly when a local media source is available or when URL metadata acquisition has not already shown platform blocking.

## Failure 6: Chinese Artifacts Were Corrupted By The Write Path

Observed behavior:

- A first write path through PowerShell replaced Chinese text with question marks.
- Files were later repaired by writing through Node with UTF-8.

Cause:

- Long Chinese artifacts were written through an unsafe shell text path.
- The workflow lacked an artifact writer and post-write encoding validation.

Consequence:

- Generated reports and metadata became unreadable.
- Extra time was spent rewriting artifacts.

Repair direction:

- Add `scripts/write_artifact.py`.
- Require UTF-8 writes and immediate read-back verification.
- Reject artifacts with abnormal question-mark ratios or missing expected CJK characters.
- Avoid PowerShell here-string writes for Chinese reports, transcripts, or JSON.

## Failure 7: Skill Referenced Missing Files

Observed behavior:

- `knowledge-video-decomposer/SKILL.md` referenced `references/workflow.md` and `references/chrome-routing.md`.
- These files did not exist at the time of the run.

Cause:

- The skill body pointed to planned references before they were implemented.
- Validation checked skill structure, not semantic existence of referenced files.

Consequence:

- The agent saw an instruction to read a file and hit a missing reference during task execution.
- Chrome routing remained vague and unenforced.

Repair direction:

- Add missing reference files or remove stale references.
- Add an internal reference-existence check to future validators.
- Keep `SKILL.md` references one level deep and real.

## Failure 8: Subagents Were Over-Spawned In Earlier Work

Observed behavior:

- The user observed many subagents created across the project history.
- Some project logs showed subagent handoffs, but not a complete global registry covering all dispatches.

Cause:

- "Use subagent-supervisor" was sometimes interpreted as "spawn subagents" rather than "make a dispatch decision."
- The workflow lacked a global or per-project mandatory registry and hard budget.

Consequence:

- Token use increased.
- Task continuity decreased.
- The supervisor role became less reliable because coordination overhead grew.

Repair direction:

- Strengthen subagent budget rules.
- Default to zero subagents for video workflow runs.
- Forbid subagents for progress audits, route decisions, failure reviews, Chrome decisioning, acquisition probing, and low-cost validation.
- Require registry check and explicit dispatch decision before any spawn.

## Failure 9: No Runner Meant The Agent Could Freestyle The Pipeline

Observed behavior:

- The workflow depended on the agent remembering the intended route.
- When the agent made a wrong route choice, the pipeline kept moving in the wrong direction.

Cause:

- Skills were mostly natural-language instructions.
- There was no executable `workflow_runner.py` to enforce stage order, allowed transitions, source status, or stop gates.

Consequence:

- The run continued after source acquisition should have stopped.
- A degraded report was generated in a shape similar to a full report.
- Tool retries were not bounded by a deterministic state machine.

Repair direction:

- Add `scripts/workflow_runner.py`.
- Require stages such as acquisition probe, Chrome inspection, transcript, segmentation, inventory, logic, gap check, and pack generation to have explicit inputs, outputs, success conditions, and allowed next states.
- Write and read `logs/run_state.json` at each stage.

## Failure 10: No Acquisition Probe Fast-Fail Gate

Observed behavior:

- The run spent too long testing multiple extraction branches.
- There was no two-minute acquisition decision.

Cause:

- The workflow had no dedicated `acquisition_probe.py`.
- Tool attempts were chosen by the agent instead of a bounded probe.

Consequence:

- The workflow could waste time before knowing whether it had primary source material.
- Platform blocking was not converted into a single clear state.

Repair direction:

- Add `scripts/acquisition_probe.py`.
- Bound the probe time.
- Attempt only approved quick checks.
- Output `acquisition_status.json`.
- Stop further source extraction once a blocking state is reached.

## Failure 11: No Artifact Validator

Observed behavior:

- JSON parse checks and encoding checks were done manually after files were written.
- There was no reusable validator to prevent invalid artifacts from entering downstream stages.

Cause:

- The workflow lacked `artifact_validator.py`.

Consequence:

- Bad or degraded artifacts could be consumed by later stages.
- The agent had to remember validation rules manually.

Repair direction:

- Add `scripts/artifact_validator.py`.
- Validate JSON, JSONL, UTF-8, transcript availability, source status, evidence spans, and allowed report type.
- Make downstream stages depend on validator pass/fail.

## Failure 12: Document Composer Did Not Have A Hard Source Gate

Observed behavior:

- The document stage could create a final report even when upstream material was only metadata or secondary outline.

Cause:

- The document-composer workflow did not require `acquisition_status.json`.
- Quality gates were written for report quality, not source eligibility.

Consequence:

- A polished report could be generated from insufficient evidence.

Repair direction:

- Update document-composer to read source status before drafting.
- If `can_enter_full_decomposition = false`, only allow acquisition failure reports or clearly degraded reports.
- Forbid a normal `final_report.md` unless source eligibility passes or the file is explicitly labeled degraded.

## Failure 13: Firecrawl Boundary Was Not Explicit Enough

Observed behavior:

- Firecrawl successfully acquired secondary page context, but it did not acquire the original video transcript.

Cause:

- The workflow did not clearly separate page/context scraping from media/transcript acquisition.

Consequence:

- Firecrawl success could create false confidence about video content access.

Repair direction:

- Define Firecrawl as a context and webpage extraction tool, not a media transcript substitute.
- Allow Firecrawl to support metadata, page context, descriptions, public summaries, and source ledgers.
- Do not allow Firecrawl-only evidence to unlock full video decomposition.

## Failure 14: Low-Cost Mode Was Not Strong Enough

Observed behavior:

- The workflow consumed too much time and context despite the user's cost sensitivity.

Cause:

- Low-cost mode existed in routing text, but it was not enforced by a runner.

Consequence:

- The agent could still spend time trying multiple branches.

Repair direction:

- In low-cost mode, default to no subagents, one quick acquisition probe, and hard stop after blocked states.
- Require concise final response with paths and limitations.
- Do not paste full transcripts or long reports into chat unless explicitly requested.

## Failure 15: Failure Was Framed Too Positively

Observed behavior:

- A degraded acquisition result was described in language close to a successful validation.

Cause:

- The workflow lacked strict status labels and allowed report types.

Consequence:

- Project progress could be overstated.
- The user had to correct the status interpretation.

Repair direction:

- Use explicit run statuses:
  - `completed_full_decomposition`
  - `completed_degraded_report`
  - `blocked_chrome_required`
  - `blocked_chrome_unavailable`
  - `blocked_no_primary_source`
  - `failed_tooling`
- Final responses must state whether the run is full success, degraded success, blocked, or failed.

## Repair Priority

Implement in this order:

1. `chrome-routing.md`
2. `source-status.md`
3. `acquisition_probe.py`
4. `artifact_validator.py`
5. `write_artifact.py`
6. minimal `workflow_runner.py` for acquisition-stage gating
7. workflow-console routing changes
8. document-composer source gate
9. subagent-supervisor budget hardening

## Acceptance For This Failure Log

This file is complete for phase one when:

- It records all real failure classes observed so far.
- Each failure has observed behavior, cause, consequence, and repair direction.
- It does not claim the repairs are implemented.
- It can serve as the input list for later hardening phases.
