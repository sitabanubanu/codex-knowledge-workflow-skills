---
name: knowledge-video-decomposer
description: Decompose knowledge-heavy videos, video pages, local video/audio files, subtitles, and transcripts into structured analysis artifacts. Use when Codex needs to extract or normalize transcripts, inspect video source context, segment content, identify concepts/examples/claims/analogies, reconstruct the speaker's argument logic, and produce a video_analysis_pack for downstream document composition.
---

# Knowledge Video Decomposer

Use this skill to turn a video or transcript source into a structured knowledge package.

Core workflow:
1. Inspect the source and collect metadata.
2. Before processing any video URL or platform page, read references/chrome-routing.md, references/source-status.md, and references/platform-prerequisites.md.
3. When starting a new platform workflow or diagnosing an environment failure, run scripts/doctor.py and save doctor_report.json / doctor_report.md under logs or 00_source. Doctor is read-only: it checks local tools, cookies-file presence, Chrome plugin files, ASR modules, and UTF-8 writing, but does not fetch media or reveal cookie values.
4. Use scripts/acquisition_runner.py for first-pass platform acquisition probing when starting from a video URL. It should write `00_source/source_status.json`, `00_source/acquisition_runner_report.json`, `00_source/acquisition_notes.md`, and raw probe logs before any decomposition artifact is created.
5. Use scripts/acquisition_probe.py to record source status, source classes, failed probes, Chrome routing state, and the next allowed route when probe results already exist or when another tool produced the evidence.
6. Platform blocks, HTTP 429, bot/CAPTCHA/login barriers, RequestBlocked errors, or Hearsay URL timeouts on platform URLs must enter the Chrome route decision in references/chrome-routing.md instead of repeating the same extractor.
7. When a yt-dlp bare request or youtube_transcript_api hits a platform block (HTTP 429, bot check, sign-in required, RequestBlocked), the agent MUST try yt-dlp with `--cookies-from-browser chrome` or a user-exported Netscape `cookies.txt` before declaring the path dead. The user's own browser identity is not a bypass - it is the legitimate identity they already use to watch the same page.
8. If `--cookies-from-browser chrome` fails with DPAPI/App-Bound decryption errors, do not loop over Chrome profiles. Follow references/platform-prerequisites.md: request a user-exported Netscape `cookies.txt`, use `--cookies <cookies.txt>`, and never record or commit cookie values.
9. If yt-dlp with cookies exposes only storyboards/images or reports `n challenge solving failed`, add a supported JavaScript runtime such as Node.js and, when accepted, `--remote-components ejs:github` before declaring media unavailable.
10. After yt-dlp with cookies, Chrome page inspection, or browser-derived probing obtains subtitles, audio, or a browser-visible transcript, that material must pass through source-status gating (references/source-status.md) before entering full decomposition.
11. When Chrome opens a page and no visible transcript or caption UI is present, do not immediately stop. Run the Chrome deep-probe sequence defined in references/chrome-routing.md: visible transcript -> pageAssets inventory -> pageAssets bundle (only when assets are discovered) -> Playwright evaluate for captionTracks / player response / public media or source tags -> network/media asset inspection when the current plugin documentation supports it. Record every layer's result. Only after all layers fail may the agent conclude that no primary media is available from the page.
12. If Chrome deep-probe succeeds (an actual local media file or subtitle file was exported, or a public downloadable media/subtitle URL was confirmed and fetched), and subsequent ASR or subtitle parsing succeeds, the material qualifies as browser_derived_media - a primary source class that can support source_confirmed. Refer to references/source-status.md for the exact definition and recording requirements.
13. If no primary transcript, no browser-derived media, and no user-provided or legitimately acquired local file exists, stop full decomposition and request primary material. Record that the missing requirement is primary media/transcript, not merely a better prompt.
14. Prefer reliable existing subtitles or transcripts from the platform, yt-dlp (with or without Chrome cookies / user-exported cookies as needed), user-provided files, or local parsers - subject to the source-status gate.
15. Use scripts/transcript_normalizer.py to normalize local transcript/subtitle material (`.txt`, `.md`, `.srt`, `.vtt`, `.jsonl`, `.json`) into `01_transcript/raw_transcript.jsonl`, `01_transcript/clean_transcript.jsonl`, and `01_transcript/clean_transcript.md`. The normalizer may open the decomposition gate for source-confirmed transcript material, but it must not write segments, inventory, logic, or video_analysis_pack.
16. Normalize transcript material into timestamped artifacts where timestamps exist, and record transcript provenance, language, confidence, and known limitations.
17. Segment the transcript syntactically and semantically.
18. Extract concepts, claims, examples, analogies, and argument segments.
19. Reconstruct the source-faithful logic of the speaker only when the source-status gate permits it.
20. Preserve evidence links to timestamps or source spans.
21. For Chinese, non-ASCII, Markdown, or JSON artifacts, use scripts/write_artifact.py, apply_patch, or another verified UTF-8 path. Do not write long Chinese artifacts through shell here-strings, inline command strings, PowerShell `>` redirection, or other paths that can silently change encoding or turn characters into question marks.
22. In `source_blocked`, `source_failed`, `secondary_only`, or `degraded_report_only`, do not pre-create the full analysis directory shape (`01_transcript`, `02_segments`, `03_inventory`, `04_logic`, `05_gap_check`) and do not create `video_analysis_pack.md`. Write only `00_source` notes plus a clearly labeled degraded/acquisition report.
23. Validate outputs with scripts/artifact_validator.py before handing them downstream.
24. Output a video_analysis_pack for knowledge-document-composer only after validation passes for an allowed full or explicitly partial source status.

Runner guidance:
- Use scripts/doctor.py before acquisition when the environment is unknown, after a tool-path failure, or before long platform runs. Treat doctor failures as environment/setup issues, not source-content failures.
- Use scripts/acquisition_runner.py as the first platform-URL acquisition runner. It may run bounded yt-dlp metadata/subtitle/format probes, optionally run doctor, and write `00_source` artifacts. Listed subtitles or media formats are only available routes; they are not `source_confirmed` until a local subtitle/transcript/audio-derived transcript artifact exists.
- Use scripts/transcript_normalizer.py after a transcript/subtitle file exists. It writes transcript artifacts and source-status metadata only; it does not perform semantic decomposition.
- Use scripts/workflow_runner.py as a low-cost hard-gate runner for acquisition signals and minimal blocked/degraded status outputs.
- Do not treat workflow_runner.py as a full analyzer: it does not fetch media, launch Chrome, create transcripts, segment content, or produce a complete video_analysis_pack.

Read references/platform-prerequisites.md before processing YouTube or platform URLs where yt-dlp, cookies, JavaScript runtime, bot/sign-in checks, DPAPI/App-Bound failures, `n challenge`, missing subtitles, or local ASR routes may arise.
Read references/chrome-routing.md before processing video URLs and whenever Chrome route, page-state, platform block, Hearsay URL timeout, 429, bot, CAPTCHA, login, RequestBlocked, visible-transcript, or Chrome deep-probe decisions arise.
Read references/source-status.md before processing video URLs and before deciding whether full, partial, blocked, secondary-only, or degraded outputs are allowed.
Read references/artifact-schema.md before writing intermediate artifacts.
Read references/transcription-fallback.md before running ASR when reliable subtitles or transcripts are unavailable.
