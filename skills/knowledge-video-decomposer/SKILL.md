---
name: knowledge-video-decomposer
description: Decompose knowledge-heavy videos, video pages, local video/audio files, subtitles, and transcripts into structured analysis artifacts. Use when Codex needs to extract or normalize transcripts, inspect video source context, segment content, identify concepts/examples/claims/analogies, reconstruct the speaker's argument logic, and produce a video_analysis_pack for downstream document composition.
---

# Knowledge Video Decomposer

Use this skill to turn a video or transcript source into a structured knowledge package.

Core workflow:
1. Inspect the source and collect metadata.
2. Before processing any video URL or platform page, read references/chrome-routing.md and references/source-status.md.
3. Use scripts/acquisition_probe.py to record source status, source classes, failed probes, Chrome routing state, and the next allowed route.
4. Platform blocks, HTTP 429, bot/CAPTCHA/login barriers, RequestBlocked errors, or Hearsay URL timeouts on platform URLs must enter the Chrome route decision in references/chrome-routing.md instead of repeating the same extractor.
5. Do not enter a full video_analysis_pack unless a primary transcript, primary audio-derived transcript, or browser-visible transcript is available. If only metadata, search, Firecrawl, Podwise, screenshots, page observations, or summaries exist, follow the degraded/blocked statuses in references/source-status.md.
6. Prefer reliable existing subtitles or transcripts from the platform, yt-dlp, user-provided files, or local parsers when allowed by the source-status gate.
7. If Chrome can open/play the page but no browser-visible transcript exists, do not conclude that full analysis is impossible until checking for an allowed audio path: a user-provided local video/audio file, a user-provided transcript, or a public media/subtitle extraction that succeeds without cookie handoff or access-control bypass.
8. If an allowed local video/audio file is available, run the direct local faster-whisper fallback before MCP ASR paths, selecting the ASR model according to the user's accuracy/cost goal.
9. If no reliable transcript and no allowed local/public audio source exists, stop full decomposition and request primary material. Record that the missing requirement is primary media/transcript, not merely a better prompt.
10. Do not pass Chrome cookies, logged-in browser state, private tokens, or restricted player streams to yt-dlp or another extractor. Do not use Chrome as a bridge for bypassing platform anti-bot, paywall, login, region, CAPTCHA, or account restrictions.
11. Use Hearsay MCP, WhisperX, or another ASR route only as a backup when subtitles and the direct local fallback are unavailable or fail.
12. Normalize transcript material into timestamped artifacts and record transcript provenance, model choice, language, runtime, and confidence.
13. Segment the transcript syntactically and semantically.
14. Extract concepts, examples, claims, analogies, and argument segments.
15. Reconstruct the source-faithful logic of the speaker only when the source-status gate permits it.
16. Preserve evidence links to timestamps or source spans.
17. For Chinese, non-ASCII, Markdown, or JSON artifacts, use scripts/write_artifact.py, apply_patch, or another verified UTF-8 path. Do not write long Chinese artifacts through shell here-strings, inline command strings, or other paths that can silently turn characters into question marks.
18. In `source_blocked`, `source_failed`, `secondary_only`, or `degraded_report_only`, do not pre-create the full analysis directory shape (`01_transcript`, `02_segments`, `03_inventory`, `04_logic`, `05_gap_check`) and do not create `video_analysis_pack.md`. Write only `00_source` notes plus a clearly labeled degraded/acquisition report.
19. Validate outputs with scripts/artifact_validator.py before handing them downstream.
20. Output a video_analysis_pack for knowledge-document-composer only after validation passes for an allowed full or explicitly partial source status.

Runner guidance:
- Use scripts/workflow_runner.py as a low-cost hard-gate runner for acquisition signals and minimal blocked/degraded status outputs.
- Do not treat workflow_runner.py as a full analyzer: it does not fetch media, launch Chrome, create transcripts, segment content, or produce a complete video_analysis_pack.

Read references/workflow.md when the detailed workflow exists.
Read references/chrome-routing.md before processing video URLs and whenever Chrome route, page-state, platform block, Hearsay URL timeout, 429, bot, CAPTCHA, login, RequestBlocked, or visible-transcript decisions arise.
Read references/source-status.md before processing video URLs and before deciding whether full, partial, blocked, secondary-only, or degraded outputs are allowed.
Read references/artifact-schema.md before writing intermediate artifacts.
Read references/transcription-fallback.md before running ASR when reliable subtitles or transcripts are unavailable.
