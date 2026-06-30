# Chrome Routing Gate

This file defines when and how `knowledge-video-decomposer` must use Chrome to inspect video pages, probe for media assets, and — when the page is blocked to bare external extraction — retry yt-dlp with the user's own Chrome browser identity. It is an execution rule set for downstream agents, not a suggestion list.

## When Chrome Is Required

Chrome is the required next step when any of the following is true:

- The source is YouTube, Bilibili, Coursera, a membership site, a course page, a podcast page, an embedded video page, or another platform page, and page state affects transcript, subtitle, description, chapter, login state, or visible content.
- `yt-dlp` (bare, without `--cookies-from-browser`) returns HTTP 429, bot confirmation, robot check, CAPTCHA, Sign in to confirm, login required, RequestBlocked, or a similar platform block.
- `youtube_transcript_api` returns blocked, RequestBlocked, TooManyRequests, TranscriptsDisabled, login required, or a bot/consent/region-related block.
- Hearsay URL ingestion times out on a platform URL metadata fetch, and the source is a platform URL, not a local audio/video file.
- The page may have a visible transcript, caption panel, description, chapters, show notes, course handouts, resource links, or other first-hand material that needs human-visible state confirmation.
- The user explicitly asks to use Chrome, the browser, the current login state, or the visible page to confirm the source.

The goal of Chrome inspection is to confirm "what the page actually shows": title, author/channel, whether the page opens, whether a transcript exists, whether login/CAPTCHA/paywall is required, and whether there is downloadable or copyable first-hand text or exposed media.

## Required Sequence: Chrome Deep Probe

When Chrome opens a platform video page and no visible transcript or caption UI is immediately present, the agent MUST NOT stop at "no visible transcript." It must execute this layered probe sequence and record the result of each layer:

### Layer 1 — Visible Transcript / Caption UI

- Look for a visible transcript panel, "Show transcript" button, caption toggle, subtitle menu, or language selector.
- If a visible transcript is found, capture it. Record `visible_transcript_status: "available"`.
- If a transcript button exists but is not expanded, click it and re-inspect.

### Layer 2 — pageAssets Inventory

- Call `pageAssets.list()` and inspect the returned asset inventory.
- Look for assets of kind `"video"`, assets with `.vtt`/`.srt`/`.sbv`/`.xml` (subtitle MIME or extension), and assets whose URL or name suggests subtitle/caption content.
- Record what kinds were found, even if none are media assets.

### Layer 3 — pageAssets Bundle (only when assets discovered)

- If Layer 2 found video, font, or stylesheet assets that may include subtitle or media data, call `pageAssets.bundle()` with the relevant `kinds` and `assetIds`.
- Record whether any media or subtitle files were exported to the local artifact directory.
- If a subtitle file (`.vtt`, `.srt`, etc.) was exported, it qualifies as `browser_derived_media`.

### Layer 4 — Playwright evaluate for Player Data

- Use `tab.playwright.evaluate()` to inspect the page DOM for:
  - `player.response` or similar player-state objects containing `captions` / `captionTracks` / `timedtext`.
  - `<track>` elements on `<video>` or `<audio>` tags with public `src` attributes.
  - Publicly-exposed media URLs in `<source>` tags, `data-setup`, or player configuration objects.
  - Any `ytInitialPlayerResponse` or equivalent platform player bootstrap data containing caption/transcript URLs.
- Record what was found. A public subtitle track URL is a valid `browser_derived_media` when it can be fetched and saved.

### Layer 5 — Network / Media Asset Inspection (when supported)

- If the current Chrome plugin documentation exposes a network-asset or media-asset inspection capability, use it to observe visible media or subtitle asset states.
- If the plugin documentation does NOT expose such a capability, record that it was not available and move on. Do not pretend to have executed CDP `Network.*` commands when no stable interface is documented.

### After All Layers

After all layers have been tried and their results recorded:

- If ANY layer produced an actual local subtitle file, an exported media file, or a confirmed public downloadable media/subtitle URL → proceed to ASR or subtitle parsing. The material qualifies as `browser_derived_media` (see `source-status.md`).
- If ALL layers failed → record `chrome_deep_probe_exhausted: true`. The agent may now conclude that no primary media is available from the page. Proceed to request user-provided local files or enter the appropriate degraded/blocked source status.

## yt-dlp with Chrome Cookies

When yt-dlp bare requests are blocked by YouTube or another platform, the agent MUST retry with the user's own Chrome browser identity:

```
yt-dlp --cookies-from-browser chrome <URL>
```

This is the user's own browser identity on their own machine. It is not a bypass, not a credential handoff to a third party, and not a bulk-scraping technique. The user is already watching the page in Chrome — yt-dlp merely uses the same identity to fetch subtitles or audio that the user is already authorized to access.

After yt-dlp with Chrome cookies:

- If subtitles (`.vtt`, `.srt`, etc.) are obtained → they qualify as `primary_transcript`. Source status may be `source_confirmed`.
- If audio is obtained (`.m4a`, `.opus`, `.mp3`, etc.) → it qualifies as `primary_audio_asr` after local ASR succeeds. Source status may be `source_confirmed`.
- If yt-dlp with Chrome cookies also fails → record the failure and continue the Chrome deep-probe sequence for any remaining observable page state.

### What IS allowed with yt-dlp

- `--cookies-from-browser chrome` — use the user's own Chrome profile.
- `--write-subs` / `--write-auto-subs` — download subtitles.
- `-f bestaudio` / audio-only format selection for local ASR.
- `--skip-download` + `--write-subs` — subtitles only, no media download.

### What IS NOT allowed with yt-dlp

- Using cookies extracted from a different user's profile or a remote session.
- Passing cookies, tokens, or session state to a third-party service.
- Circumventing CAPTCHA, paywall, region lock, course permissions, account authorization, or platform anti-bot controls through automation, forged headers, or credential theft.
- Bulk-scraping content from restricted platforms.

## Chrome Is Not an Unauthorized Bypass

Chrome route is a legitimate page-state inspection and media-probe tool. It is not an anti-bot bypass, a bulk-scraping vector, or a credential-theft bridge. Downstream agents must respect these boundaries:

- Allowed: record page state, visible metadata, publicly visible transcript status, page facts the user is already authorized to see, and page assets exposed through supported plugin capabilities.
- Allowed: use yt-dlp with `--cookies-from-browser chrome` to fetch subtitles or audio that the user's own browser identity is authorized to access.
- Not allowed: require or attempt CAPTCHA solving, bot-check circumvention, paywall bypass, course-permission bypass, region-lock bypass, age-restriction bypass, or account-permission escalation.
- Not allowed: use Chrome as a bridge to pass restricted player streams, signed playback URLs, or private tokens to yt-dlp or another extractor when the material is behind a paywall, login wall, or access-control barrier that the user has not already cleared.
- Not allowed: batch-scrape restricted content through repeated automated navigation.

If the task objective requires bypassing access controls to continue, stop that branch and hand the source state to the blocked-state handler in `source-status.md`.

## Chrome Can Play But No Transcript Is Visible

When Chrome renders the video player successfully but no visible transcript, caption UI, or downloadable transcript is immediately present, do NOT record this as a dead end. Execute the Chrome deep-probe sequence defined above. The fact that the player renders means the page is accessible — it does not yet mean media extraction is impossible.

Record separately:
- "Page is playable" — the player rendered, the video is available.
- "No visible transcript" — no transcript panel or caption UI was found in Layer 1.
- Deep-probe results from Layers 2–5.
- Final conclusion after all layers.

Do not promote "page is playable" to `primary_audio_asr` or `browser_derived_media`. Only an actual exported local media file, a fetched public subtitle URL, or a confirmed local subtitle export qualifies.

## Bootstrap Rules

When the available skill list includes `chrome:control-chrome`, do not conclude Chrome is unavailable just because no direct `chrome.*` tool namespace is visible.

Execution order:

1. First read the `chrome:control-chrome` skill's `SKILL.md`.
2. Follow that skill's instructions to read the required browser documentation or browser-client docs.
3. Connect to and control Chrome using that skill's Node/browser-client bootstrap method.
4. Only when the skill is missing, documentation read fails, Chrome connection fails, the browser cannot open the target page, or the user declines to use Chrome may the agent record Chrome route as not executable.

Prohibited behaviors:

- Do not record `Chrome unavailable` merely because the tool list does not show `chrome.open`, `chrome.navigate`, or a `chrome.*` namespace.
- Do not skip the `chrome:control-chrome` bootstrap documentation and guess how to call it.
- Do not repeatedly retry the same 429/bot-blocked extractor after Chrome has been triggered.

## Trigger Conditions

When any of the following signals appear, the agent MUST enter the Chrome route decision and stop same-class external extraction retries:

- `yt-dlp` (bare) returns HTTP 429, bot confirmation, robot check, CAPTCHA, Sign in to confirm, login required, RequestBlocked, or a similar platform block.
- `youtube_transcript_api` returns blocked, RequestBlocked, TooManyRequests, TranscriptsDisabled, login required, or a bot/consent/region-related block.
- Hearsay URL ingestion times out on a platform metadata fetch or URL stage, and the source is a platform URL, not a local audio/video file.
- Platform-page transcript existence needs human-visible state confirmation.
- The user explicitly asks to "use Chrome", "use the browser", "use the login state", or "check whether the page has a transcript/subtitle".

After triggering:

1. Record the trigger reason.
2. Retry yt-dlp with `--cookies-from-browser chrome`. If it succeeds, record the acquired material and proceed.
3. If yt-dlp with Chrome cookies also fails, use Chrome to open or locate the target page.
4. Observe whether the page opens, whether the title matches, login/CAPTCHA/paywall state, visible transcript or caption entry points.
5. Execute the Chrome deep-probe sequence (Layers 1–5) to search for media or subtitle assets.
6. Only collect first-hand text when a visible transcript or user-authorized first-hand material is accessible.
7. If no first-hand material is found after all layers, enter the blocked or degraded state from `source-status.md`.

## Stop Conditions

Chrome route must stop when any of the following is true, without further automation to bypass:

- Chrome page cannot open, crashes, connection fails, or the target URL cannot load.
- All five layers of the Chrome deep-probe sequence have been exhausted without finding a primary media asset.
- The page requires CAPTCHA, bot verification, paywall, course permission, membership permission, account permission, region unlock, or login the user has not authorized.
- The page shows the video is unavailable, deleted, private, regionally unavailable, or age/permission-restricted.
- Continuing would require batch-scraping restricted content, passing cookies to a third party, bypassing access controls, or circumventing platform restrictions.

After stopping, record the reason and select `source_blocked`, `source_failed`, `secondary_only`, or `degraded_report_only` per `source-status.md`. Do not disguise the result as a complete video analysis. The stop explanation must distinguish "page is playable but all deep-probe layers failed — no extractable media found" from "page is completely inaccessible."

## Output Requirements

Any workflow that executes or explicitly skips the Chrome route must record the following fields in acquisition notes, metadata, or run state:

Prefer writing the standard machine artifact with:

```powershell
python scripts/chrome_media_probe.py `
  --input-json <chrome-layer-observations.json> `
  --output-root outputs/knowledge-workflow/<run-id>/10_video `
  --pretty
```

`chrome_media_probe.py` does not launch Chrome. It normalizes observations
already collected by Chrome, pageAssets, Playwright evaluate, or manual page
state inspection into `00_source/chrome_media_probe.json` and
`00_source/chrome_media_probe.md`, then returns the acquisition signal that
should feed the source-status gate.

```json
{
  "chrome_route_used": true,
  "visible_transcript_status": "available|partial|not_visible|not_checked|blocked|unknown",
  "page_state_observed": "opened|failed_to_open|login_required|captcha_required|paywalled|permission_required|video_unavailable|metadata_only|unknown",
  "chrome_deep_probe_exhausted": false,
  "deep_probe_layers_executed": ["visible_transcript", "pageAssets_list", "pageAssets_bundle", "playwright_evaluate"],
  "deep_probe_media_found": false,
  "browser_derived_media_exported": false,
  "yt_dlp_chrome_cookies_attempted": false,
  "yt_dlp_chrome_cookies_succeeded": false,
  "why_chrome_was_or_was_not_used": ""
}
```

Field rules:

- `chrome_route_used`: `true` when Chrome was actually used; `false` when it was not, with an explanation of why.
- `visible_transcript_status`: only record Chrome-visible page facts. Do not write Firecrawl, search snippets, Podwise, or guesses as a visible transcript.
- `page_state_observed`: record the most specific page-state value; use `unknown` when uncertain, with an explanation.
- `chrome_deep_probe_exhausted`: `true` when all five layers were attempted and none produced primary media.
- `deep_probe_layers_executed`: list which layers were actually run.
- `deep_probe_media_found`: `true` when any layer found a usable media or subtitle asset.
- `browser_derived_media_exported`: `true` when a local file was actually exported and saved.
- `yt_dlp_chrome_cookies_attempted`: `true` when yt-dlp was retried with `--cookies-from-browser chrome`.
- `yt_dlp_chrome_cookies_succeeded`: `true` when that retry produced subtitles or audio.
- `why_chrome_was_or_was_not_used`: must include the trigger condition, bootstrap result, stop condition, or skip reason.

Minimum record example:

```json
{
  "chrome_route_used": true,
  "visible_transcript_status": "not_visible",
  "page_state_observed": "opened",
  "chrome_deep_probe_exhausted": false,
  "deep_probe_layers_executed": ["visible_transcript", "pageAssets_list", "pageAssets_bundle", "playwright_evaluate"],
  "deep_probe_media_found": true,
  "browser_derived_media_exported": true,
  "yt_dlp_chrome_cookies_attempted": true,
  "yt_dlp_chrome_cookies_succeeded": true,
  "why_chrome_was_or_was_not_used": "yt-dlp bare returned HTTP 429, so yt-dlp with Chrome cookies was attempted and succeeded in downloading subtitles. Chrome deep-probe was also run and confirmed no additional visible transcript beyond what yt-dlp already captured."
}
```

## Relationship with Source-Status Gate

Chrome can confirm page state and — through the deep-probe sequence or yt-dlp with Chrome cookies — can surface primary media or transcript material. Only the following Chrome results may enter a full `video_analysis_pack`:

- A visible, citable transcript on the page was captured and can form timestamps or source spans.
- Chrome confirmed and captured platform public subtitles, an official transcript, or a first-hand transcript from a page the user is authorized to access.
- Chrome deep-probe exported a subtitle file or media file via pageAssets, or confirmed a public downloadable media/subtitle URL that was then fetched and saved.
- yt-dlp with `--cookies-from-browser chrome` successfully obtained subtitles or audio.
- Chrome helped locate a locally downloaded or user-provided first-hand transcript/audio, and subsequent transcript/audio acquisition succeeded.

If Chrome only yields title, description, chapters, public summary, comments, page screenshots, or second-hand links, the result is at most `secondary_only` or `degraded_report_only` — it cannot enter full video decomposition.
