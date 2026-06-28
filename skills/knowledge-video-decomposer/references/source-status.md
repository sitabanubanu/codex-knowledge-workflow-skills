# Source Status Gate

This file defines the source-acquisition state machine for `knowledge-video-decomposer`. Downstream agents MUST determine source status before deciding whether to enter a full `video_analysis_pack`.

## State Enumeration

`source_status` must use only the following machine-executable enum values:

- `source_confirmed`
- `source_partial`
- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`

Do not invent ad-hoc statuses to bypass the gate. When additional detail is needed, write it into `status_reason`, `source_classes`, `failed_probes`, `next_step`, or acquisition notes.

## Hard Gate

- Only `source_confirmed` may directly enter a full `video_analysis_pack`.
- `source_partial` may enter a partial-labeled `video_analysis_pack` only when the material scope, gaps, time ranges, source types, and confidence are explicitly annotated; it must not be presented as a complete video analysis.
- `secondary_only` must not be disguised as a complete video analysis. Speaker logic reconstruction is forbidden.
- `degraded_report_only` may only generate a degraded explanation or source-acquisition report, not a complete video analysis pack.
- `source_blocked` and `source_failed` must stop full decomposition, or request the user to provide a local file, transcript, audio, authorized page access, or an explicit approval of a local plan.
- Without first-hand transcript/audio/browser-visible transcript or browser-derived media, the document composer may only write "degraded explanation based on visible page/secondary material." Speaker logic reconstruction, complete argument flow, or complete source logic is forbidden.

## Source Classes

Source classes describe the type of material backing the analysis. Each source class is either primary (supports full decomposition) or secondary (context/background only).

### Primary Source Classes (support full decomposition)

- `primary_transcript`: official subtitles, platform transcript, user-provided transcript, reliable subtitle file, or subtitles acquired via yt-dlp (bare or with `--cookies-from-browser chrome`).
- `primary_audio_asr`: ASR transcript derived from a user-provided or legitimately acquired audio/video file.
- `browser_visible_transcript`: Chrome page-visible, copyable, citable transcript or subtitle text.
- `browser_derived_media`: a subtitle or media file exported from Chrome via pageAssets, or fetched from a confirmed public downloadable media/subtitle URL discovered during the Chrome deep-probe, which then passed through ASR or subtitle parsing successfully.

### Secondary / Background Source Classes (context only)

- `platform_metadata`: title, channel, publish time, description, chapters, page-visible metadata.
- `secondary_summary`: Podwise, page summaries, course page summaries, third-party notes.
- `search_snippet`: search result fragments.
- `firecrawl_context`: Firecrawl-fetched page body, description, public page context.
- `page_observation`: Chrome-observed page state, buttons, prompts, permission state, screenshot-level facts.

Firecrawl, web search, Podwise, third-party summaries, and generic page descriptions can only supplement background, identify the video, build a source ledger, or generate degraded reports; they cannot substitute for first-hand transcript/audio and cannot unlock full decomposition.

### `browser_derived_media` — Definition and Requirements

`browser_derived_media` is a primary source class. It supports `source_confirmed` only when ALL of the following are true:

1. **An actual local file was produced.** Either:
   - A subtitle file (`.vtt`, `.srt`, `.sbv`, etc.) was exported via Chrome `pageAssets.bundle()` and saved locally; or
   - A media file (`.mp4`, `.m4a`, `.webm`, etc.) was exported via Chrome `pageAssets.bundle()` and saved locally; or
   - A public downloadable media/subtitle URL was confirmed through the Chrome deep-probe, fetched via an allowed tool (yt-dlp, curl, etc.), and the resulting file was saved locally.
2. **The file was processed successfully.** Either:
   - The subtitle file was parsed and produced valid timestamped transcript segments; or
   - The media file was transcribed via local ASR and produced valid transcript output.
3. **Acquisition notes record the full chain:** which Chrome capability found the asset (pageAssets, Playwright evaluate, etc.), the asset URL or page element, whether the asset was publicly accessible or within the user's authorized page context, the local save path, the ASR or parsing tool used, and a confidence assessment.

`browser_derived_media` does NOT include:
- "Chrome can play the video."
- "I saw a media URL in the DOM" — without actually fetching and saving the file.
- A temporary signed playback URL, private token, or restricted player stream copied from the browser.
- A URL that requires CAPTCHA, paywall, login, region unlock, or permission escalation to access.

## State Definitions

### `source_confirmed`

Entry conditions:

- A complete or sufficiently complete first-hand transcript, audio-derived transcript, or browser-derived media has been acquired.
- The transcript has a traceable source: platform subtitles, user file, Chrome-visible transcript, legitimately acquired local audio/video ASR, yt-dlp Chrome-cookies subtitles/audio, or Chrome pageAssets export.
- Timestamps, transcript IDs, or source spans can be provided for major claims, examples, concepts, and logic.
- Acquisition notes record tools, source, language, confidence, and major failed branches.

Allowed outputs:

- Complete `video_analysis_pack`.
- Standard artifacts: `01_transcript`, `02_segments`, `03_inventory`, `04_logic`, `05_gap_check`.
- Source-faithful speaker logic reconstruction.

Prohibited outputs:

- Do not write secondary summaries as first-hand transcripts.
- Do not hide transcript gaps or label low-quality ASR as complete/verbatim.

### `source_partial`

Entry conditions:

- A first-hand source has been acquired, but there are explicit gaps: partial time coverage, incomplete subtitle language, low ASR quality, missing timestamps, truncated transcript, or missing segments.
- The gap scope is describable, and the remaining material is still sufficient to support limited video content decomposition.
- Acquisition notes explicitly label the partial reason, coverage scope, and which analysis scopes cannot be supported.

Allowed outputs:

- Partial-labeled `video_analysis_pack`.
- Local segmentation, inventory, and logic notes with evidence spans.
- Source logic summary that explicitly states "only covers acquired transcript/audio scope."

Prohibited outputs:

- Do not write as a complete whole-video analysis.
- Do not fill in missing segments with Firecrawl, Podwise, or search results and then call it source-faithful.

### `secondary_only`

Entry conditions:

- No first-hand transcript, audio, browser-visible transcript, or browser-derived media has been acquired.
- Only Firecrawl, web search, Podwise, page description, title, chapters, show notes, search snippets, comments, third-party summaries, or platform metadata are available.
- These materials can identify the video topic or background but cannot trace speaker expressions sentence by sentence.

Allowed outputs:

- `acquisition_failure_report.md`.
- `degraded_source_notes.md`.
- Background explanation based on secondary material, source ledger, visible page summary, next-step suggestions.

Prohibited outputs:

- Do not generate a complete `video_analysis_pack`.
- Do not write `04_logic/source_logic.md`-style speaker logic reconstruction.
- Do not assert the speaker's complete argument chain, concept definitions, example functions, or wording.
- Do not label secondary summaries as transcript, primary source, or source-confirmed evidence.

### `source_blocked`

Entry conditions:

- The platform or page explicitly blocks first-hand source acquisition: HTTP 429, bot check, CAPTCHA, login required, paywall, permission required, private video, region block, age restriction, course permission, or account permission.
- yt-dlp with Chrome cookies also failed.
- All five layers of the Chrome deep-probe sequence have been exhausted without finding primary media.
- Continuing would require bypassing access controls, passing cookies to a third party, circumventing CAPTCHA/paywall, or violating the user's authorization boundary.

Allowed outputs:

- Block explanation.
- Observed page state record.
- Request the user to provide files, transcript, audio, authorized access, or alternative sources.
- Clear failure paths and next-step options.

Prohibited outputs:

- Do not continue retrying the same blocked extractor.
- Do not switch to Firecrawl/search and then write secondary material as a complete analysis.
- Do not attempt to bypass CAPTCHA/paywall.

### `source_failed`

Entry conditions:

- No external permission block, but the tool chain failed: file corruption, unsupported format, local ASR failure, Hearsay failure, model load failure, download failure, parse failure, or time budget exceeded.
- Allowed paths have been attempted per acquisition probe cost limits, and no usable first-hand material was obtained.

Allowed outputs:

- Tool failure report.
- Acquisition notes, failed probes, reproducible error summary.
- Request the user to provide alternative files, shorter segments, existing transcripts, or allow longer local runs.

Prohibited outputs:

- Do not continue writing a complete video analysis based on metadata or search summaries.
- Do not unboundedly retry the same tool.
- Do not write "content analysis complete" when the tool failed.

### `degraded_report_only`

Entry conditions:

- The user accepts a degraded explanation without first-hand transcript/audio, or the current task objective is only to explain source acquisition failure, page state, background material, and follow-up plans.
- The upstream state is typically `secondary_only`, `source_blocked`, or `source_failed`.

Allowed outputs:

- Degraded report.
- Source acquisition failure explanation.
- Background summary based on visible page/secondary material, with each segment explicitly labeled by material source.
- Follow-up acquisition suggestions.

Prohibited outputs:

- Do not output a complete `video_analysis_pack`.
- Do not write speaker logic reconstruction.
- Do not use wording like "complete decomposition", "complete analysis", or "source-confirmed".
- Do not mix secondary material with first-hand transcript as the same evidence tier.

## Acquisition Probe Cost Limits

Each source acquisition probe must have a maximum time, retry count, path switch, and failure record. Downstream agents must not wait indefinitely for Hearsay, repeatedly run `yt-dlp`, or loop on the same block signal.

Default limits:

- Platform metadata/caption quick check: at most 1 normal attempt per tool, at most 1 parameter-correction retry; total duration target ≤ 2 minutes.
- `yt-dlp` (bare): on HTTP 429, bot confirmation, CAPTCHA, login required, RequestBlocked, immediately stop bare requests and switch to `yt-dlp --cookies-from-browser chrome`; do not repeatedly retry the same URL bare.
- `yt-dlp` (with `--cookies-from-browser chrome`): at most 1 normal attempt + 1 parameter-correction retry; if it also fails, continue to Chrome deep-probe.
- `youtube_transcript_api`: on blocked, TooManyRequests, TranscriptsDisabled, login/consent/region/bot related failure, record at most 1 time; do not loop.
- Chrome route: per `chrome-routing.md`, execute the full deep-probe sequence once; stop when the page cannot open, no visible transcript, all deep-probe layers exhausted, or CAPTCHA/paywall/permission is triggered.
- Hearsay URL ingestion: on platform URL metadata fetch timeout, record at most 1 time; if a platform block signal already exists, do not repeat Hearsay URL ingestion.
- Local ASR: per `transcription-fallback.md`, select model and timeout; after timeout, only downgrade model per user goal or request longer run time; do not silently wait indefinitely.
- Firecrawl/web search/Podwise: only as secondary/context probe; success cannot change `secondary_only` to `source_confirmed`.

Each probe failure must record:

```json
{
  "probe": "yt-dlp|yt-dlp-chrome-cookies|youtube_transcript_api|Chrome|Hearsay|local_asr|Firecrawl|search|Podwise|other",
  "source_class_attempted": "primary_transcript|primary_audio_asr|browser_visible_transcript|browser_derived_media|platform_metadata|secondary_summary|search_snippet|firecrawl_context",
  "max_time_seconds": 0,
  "attempts": 0,
  "result": "success|partial|blocked|failed|timeout|skipped",
  "failure_reason": "",
  "next_route": ""
}
```

## State Record Template

Each acquisition decision must write a machine-readable summary with at minimum:

```json
{
  "source_status": "source_confirmed|source_partial|secondary_only|source_blocked|source_failed|degraded_report_only",
  "can_enter_full_decomposition": false,
  "can_enter_document_composer": false,
  "allowed_report_type": "full_video_analysis_pack|partial_video_analysis_pack|acquisition_failure_report|degraded_source_report",
  "source_classes": [],
  "primary_material_available": false,
  "status_reason": "",
  "failed_probes": [],
  "next_step": ""
}
```

`can_enter_full_decomposition` rules:

- `source_confirmed`: `true`
- `source_partial`: `true` only when partial scope is adequately annotated and the user's goal allows it
- `secondary_only`: `false`
- `source_blocked`: `false`
- `source_failed`: `false`
- `degraded_report_only`: `false`

`can_enter_document_composer` rules:

- Full report: only `source_confirmed`. `source_partial` may only enter a partial document that clearly labels scope and gaps; it must not be written as a complete report.
- Degraded explanation: `secondary_only`, `source_blocked`, `source_failed`, `degraded_report_only` are allowed.
- Without first-hand transcript/audio or browser-derived media, the document composer's `allowed_report_type` must be `degraded_source_report` or `acquisition_failure_report`.

## Document Writing Gate

Before handing off to `knowledge-document-composer`, execute the following judgment:

1. If `source_status` is `source_confirmed`, allow writing a complete source-faithful document.
2. If `source_status` is adequately annotated `source_partial`, only write a partial document; must preserve gap and scope explanations.
3. If `source_status` is `secondary_only`, `source_blocked`, `source_failed`, or `degraded_report_only`, only write "degraded explanation based on visible page/secondary material."
4. Without first-hand transcript/audio/browser-visible transcript/browser-derived media, writing speaker logic reconstruction, complete argument graph, complete claims inventory, or complete source logic is forbidden.
5. Degraded reports must label degraded in the title, summary, and source explanation; they must not use the appearance of a complete analysis pack to confuse the state.

Any agent that cannot determine the current state must select the more conservative state and request the user to provide first-hand material or allow the next acquisition step; it must not default to entering full decomposition.
