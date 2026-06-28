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
5. When a yt-dlp bare request or youtube_transcript_api hits a platform block (HTTP 429, bot check, sign-in required, RequestBlocked), the agent MUST try yt-dlp with `--cookies-from-browser chrome` before declaring the path dead. The user's own browser identity is not a bypass — it is the legitimate identity they already use to watch the same page.
6. After yt-dlp with Chrome cookies or Chrome page inspection obtains subtitles, audio, or a browser-visible transcript, that material must pass through source-status gating (references/source-status.md) before entering full decomposition.
7. When Chrome opens a page and no visible transcript or caption UI is present, do not immediately stop. Run the Chrome deep-probe sequence defined in references/chrome-routing.md: visible transcript → pageAssets inventory → pageAssets bundle (only when assets are discovered) → Playwright evaluate for captionTracks / player response / public media or source tags → network/media asset inspection when the current plugin documentation supports it. Record every layer's result. Only after all layers fail may the agent conclude that no primary media is available from the page.
8. If Chrome deep-probe succeeds (an actual local media file or subtitle file was exported, or a public downloadable media/subtitle URL was confirmed and fetched), and subsequent ASR or subtitle parsing succeeds, the material qualifies as browser_derived_media — a primary source class that can support source_confirmed. Refer to references/source-status.md for the exact definition and recording requirements.
9. If no primary transcript, no browser-derived media, and no user-provided local file exists, stop full decomposition and request primary material. Record that the missing requirement is primary media/transcript, not merely a better prompt.
10. Prefer reliable existing subtitles or transcripts from the platform, yt-dlp (with or without Chrome cookies as needed), user-provided files, or local parsers — subject to the source-status gate.
11. Normalize transcript material into timestamped artifacts and record transcript provenance, model choice, language, runtime, and confidence.
12. Segment the transcript syntactically and semantically.
13. Extract concepts, examples, claims, analogies, and argument segments.
14. Reconstruct the source-faithful logic of the speaker only when the source-status gate permits it.
15. Preserve evidence links to timestamps or source spans.
16. For Chinese, non-ASCII, Markdown, or JSON artifacts, use scripts/write_artifact.py, apply_patch, or another verified UTF-8 path. Do not write long Chinese artifacts through shell here-strings, inline command strings, or other paths that can silently turn characters into question marks.
17. In `source_blocked`, `source_failed`, `secondary_only`, or `degraded_report_only`, do not pre-create the full analysis directory shape (`01_transcript`, `02_segments`, `03_inventory`, `04_logic`, `05_gap_check`) and do not create `video_analysis_pack.md`. Write only `00_source` notes plus a clearly labeled degraded/acquisition report.
18. Validate outputs with scripts/artifact_validator.py before handing them downstream.
19. Output a video_analysis_pack for knowledge-document-composer only after validation passes for an allowed full or explicitly partial source status.

Runner guidance:
- Use scripts/workflow_runner.py as a low-cost hard-gate runner for acquisition signals and minimal blocked/degraded status outputs.
- Do not treat workflow_runner.py as a full analyzer: it does not fetch media, launch Chrome, create transcripts, segment content, or produce a complete video_analysis_pack.

Read references/chrome-routing.md before processing video URLs and whenever Chrome route, page-state, platform block, Hearsay URL timeout, 429, bot, CAPTCHA, login, RequestBlocked, visible-transcript, or Chrome deep-probe decisions arise.
Read references/source-status.md before processing video URLs and before deciding whether full, partial, blocked, secondary-only, or degraded outputs are allowed.
Read references/artifact-schema.md before writing intermediate artifacts.
Read references/transcription-fallback.md before running ASR when reliable subtitles or transcripts are unavailable.
