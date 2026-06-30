# Knowledge Workflow Routing

knowledge-workflow-console is the controller. It only decides the route, invokes the appropriate skill or tool, checks intermediate artifacts, and decides whether to continue to the next stage. It does not directly handle detailed video analysis or document writing.

## Supervisor Dispatch Layer

Use subagent-supervisor before or around the normal route when the task is complex, multi-stage, parallelizable, high-risk, or when the user explicitly asks for subagents, delegation, a worker, a reviewer, a manager, or independent verification.

subagent-supervisor wraps the route; it does not replace web-intent-scout, Chrome, knowledge-video-decomposer, or knowledge-document-composer. The console still chooses the route and project layout, while subagent-supervisor creates bounded handoffs, coordinates parallel work, verifies returns, records acceptance, and requests rework when needed.

Do not use subagent-supervisor for simple single-stage routing unless the user asks for delegated work.

When the task is a small rules patch, progress audit, route choice, artifact check, or low-cost test run, keep it supervisor-owned unless an independent reviewer would clearly reduce risk. Do not spawn a new subagent just because the workflow-console or subagent-supervisor skill is active.

Before spawning, check whether an existing same-chain subagent should be reused. Prefer reuse for follow-up rework on the same artifact family, and prefer supervisor-only for bounded edits that the main agent can verify directly.

Subagent budget rules:
- Default to 0 subagents.
- For an ordinary delegated stage, use at most 1 worker.
- Add at most 1 reviewer only when independent verification is necessary.
- Do not expand worker or reviewer count to bypass source, Chrome, or document handoff gates.

## Entry Types

### 1. Topic Discovery

Use when the user gives a topic, person, direction, or question instead of a specific video.

Examples:
- "帮我找几个讲 AI agent workflow 的视频"
- "找黄仁勋讲 AI factory 的高质量视频"
- "找几个适合拆解 prompt 到 loop 的视频"

Route:
1. web-intent-scout
2. candidate_videos.json
3. User confirmation or highest-priority video selection
4. knowledge-video-decomposer
5. knowledge-document-composer

### 2. Direct Video URL

Use when the user gives a YouTube, X, Bilibili, course site, public video page, conference page, podcast page, or other video page link.

Route:
1. knowledge-video-decomposer acquisition/source gate before any full decomposition or document writing. The video decomposer must read and apply its `references/chrome-routing.md` and `references/source-status.md` rules for every video URL or platform page.
2. If the user asks for Chrome, the page state matters, or a platform block appears, route through the video decomposer Chrome routing gate before repeating extractors or falling back to secondary sources.
3. Continue to full or partial video decomposition only when the source gate allows it.
4. knowledge-document-composer only after the Source Status Handoff Gate below allows the requested report type.
5. Stop at transcript artifacts if the user only wants a transcript.

If the user asks for a low-cost or quick validation run, use the Low-Cost / Fast Pass Mode below before doing the full route.

### 3. Existing Transcript Or Subtitle

Use when the user gives an existing transcript, subtitle file, json3, vtt, srt, Markdown, or plain text.

Route:
1. knowledge-video-decomposer for normalization and segmentation
2. knowledge-document-composer for reports and document generation

Productized runner:

- When the input is a local transcript/subtitle file and the user wants the full
  gated workflow through video analysis pack plus document planning, use
  `scripts/end_to_end_runner.py`.
- The runner currently covers only the local transcript/subtitle route. It does
  not fetch media, launch Chrome, run ASR, or process a platform URL directly.

If the user explicitly only wants an article or report, route directly to knowledge-document-composer.

### 4. Existing Video Analysis Pack

Use when the user gives structured materials such as video_analysis_pack.md, logic_graph.json, claims.json, or source_logic.md.

Route:
1. knowledge-document-composer

### 5. Existing Draft Or Report Revision

Use when the user wants to revise, expand, rewrite, or convert an existing report into a script, research note, or presentation outline.

Route:
1. knowledge-document-composer

### 6. Page Verification / Browser-State Task

Use when the user needs to confirm real page state, login state, dynamic content, visible transcript, subtitle controls, expand buttons, comments, description, screenshots, or webpage context.

Route:
1. Chrome plugin
2. Firecrawl, yt-dlp, knowledge-video-decomposer, or knowledge-document-composer based on the Chrome result

## Chrome Calling Rules

Chrome is a high-priority visual page reconnaissance tool. Prefer Chrome when the task involves real webpage state, video pages, platform pages, visible subtitles, login state, interactive buttons, screenshots, or page context judgment.

For video URLs and platform pages, Chrome is controlled by the knowledge-video-decomposer Chrome routing gate. The console must route the task into that gate when Chrome is requested or when platform access is blocked, rather than treating Chrome as an optional post-processing check.

Prioritize Chrome when:
- The user gives a YouTube, X, Bilibili, course site, public video page, conference page, podcast page, or product launch page.
- The user asks what is on a webpage, what a video page is, or whether the page exposes a transcript.
- The task requires confirmation of actual visible page content.
- The page may involve login state, region differences, dynamic loading, expand buttons, subtitle panels, comments, or descriptions.
- The task requires judging whether a video is an original source, secondary edit, short clip, or repost.
- The task requires saving a screenshot of page state.
- The task requires reading page title, description, publication time, author, channel, engagement data, linked context, or surrounding page context.
- The task requires confirming transcript availability, subtitle language, automatic captions, chapters, or timeline.
- yt-dlp or Firecrawl metadata may differ from the visible page state.
- The user explicitly asks to use Chrome, inspect a page, open a webpage, or confirm in the browser.
- A platform extractor reports HTTP 429, bot/CAPTCHA checks, login requirements, permission barriers, RequestBlocked, Hearsay URL timeout on a platform URL, or similar platform obstruction.

Chrome can be skipped when:
- The user gives a local transcript, subtitle file, PDF, Markdown, or plain text.
- yt-dlp has already reliably obtained official subtitles and complete metadata, and page context is not needed.
- Firecrawl has already obtained complete webpage text, and page state does not affect the decision.
- The user only wants document processing from existing text.
- The task is offline and does not involve webpage state.
- The user explicitly asks to conserve tokens, run quickly, or only validate the workflow, and yt-dlp can obtain enough public metadata, subtitles, chapters, or audio to proceed. In that case, record that Chrome was skipped for cost control and use Chrome only if extraction fails or page state becomes central.

## Source Status Handoff Gate

Before sending any video-derived task to knowledge-document-composer, inspect the source status produced by knowledge-video-decomposer. Do not infer a permissive status from metadata, search results, Firecrawl output, screenshots, page observations, or third-party summaries.

Rules:

1. `source_confirmed`: full `video_analysis_pack` and full source-faithful document composition are allowed.
2. `source_partial`: only clearly labeled partial decomposition and partial document composition are allowed, and only when the available source range, gaps, source class, and confidence are explicit.
3. `secondary_only`, `source_blocked`, `source_failed`, or `degraded_report_only`: full decomposition and full report writing are forbidden. Do not send the task to knowledge-document-composer for a complete report, speaker logic reconstruction, complete argument graph, complete claims inventory, or complete source logic.
4. When no primary transcript, primary audio-derived transcript, or browser-visible transcript is available, knowledge-document-composer may only write an acquisition failure report or a degraded source report.
5. Firecrawl, web-intent-scout, search snippets, platform metadata, screenshots, page observations, Podwise, and third-party summaries are background or degraded-report inputs only. They cannot replace first-hand transcript/audio and cannot upgrade the source status to `source_confirmed`.
6. If a degraded report is allowed and requested, the output filename, title, summary, and source explanation must explicitly include `degraded`, for example `degraded_source_report.md` or `degraded_acquisition_report.md`.
7. If the current source status is unknown, blocked, or ambiguous, choose the more conservative status and ask for first-hand material or permission for the next acquisition step instead of continuing to full document composition.

## Low-Cost / Fast Pass Mode

Trigger this mode when the user says "bie fei token", "shao hua token", "low cost", "fast pass", "quick run", "quick validation", "xian shiyan", "xian yanshou", or otherwise asks for speed or cost control.

Rules:

1. Default to zero subagents. Use supervisor-only unless a separate reviewer is explicitly worth the cost.
2. Do not open Chrome first if yt-dlp can obtain enough public metadata, subtitles, chapters, or audio for the requested test.
3. Prefer existing subtitles or transcript files. If none exist, run the direct faster-whisper fallback before Hearsay.
4. Use Hearsay only after the direct local fallback is unavailable, fails, or the user specifically asks for Hearsay.
5. Prefer a quick ASR model only for rough workflow validation. Mark transcript confidence clearly and avoid pretending the transcript is exact.
6. Produce the minimum artifacts needed to close the requested stage. Do not paste a full transcript into chat unless the user explicitly asks for it.
7. Final response should be concise: stage completed, key artifact paths, confidence or limitations, and next recommended step.

## Tool Priority Principles

- Real webpage state judgment: Chrome first.
- Structured subtitle, audio, and metadata extraction: yt-dlp first.
- Webpage text and publication context: Firecrawl first, but only as background or degraded-report material when first-hand transcript/audio is unavailable.
- No reliable transcript: direct faster-whisper fallback first; Hearsay MCP, WhisperX, or another ASR route only as backup.
- Early video cleanup and segmentation mode: refer to VideoLingo.
- Document generation and reprocessing: knowledge-document-composer.
- Large artifact writing: use file-based generation, a reusable script, or small scoped patches. Avoid putting long reports or transcripts inside one huge shell command, because Windows command length limits can corrupt the run.

## Stop Conditions

- If the user only asks to find videos, stop at 00_scout.
- If the user only asks for a transcript, stop at 10_video transcript artifacts.
- If the user asks for video content analysis, stop at video_analysis_pack.
- If the user asks for a report, article, or script, continue to 20_document.
- If the user asks for a final deliverable file, continue to 30_final.
