# Chrome Probe Contract

This contract defines the structured record that an Agent must produce after
Chrome page inspection, pageAssets inspection, Playwright evaluation, or any
manual browser-visible video-page probe. It is a recording contract, not a
browser automation implementation.

Use this contract whenever a platform URL reaches the Chrome route, especially
when a page opens but no visible transcript is found. The record should be saved
as the input to `scripts/chrome_media_probe.py` or embedded in acquisition notes
when the script cannot be run.

## Required JSON Shape

```json
{
  "schema_version": 1,
  "url": "",
  "platform": "youtube|x|xiaohongshu|douyin|bilibili|course|other|unknown",
  "page_loaded": false,
  "page_state_observed": "opened|failed_to_open|login_required|captcha_required|paywalled|permission_required|video_unavailable|metadata_only|unknown",
  "login_state_visible": "logged_in|logged_out|unknown|not_checked",
  "bot_check_visible": false,
  "title_visible": false,
  "description_visible": false,
  "chapters_visible": false,
  "visible_transcript_checked": false,
  "visible_transcript_status": "available|partial|not_visible|not_checked|blocked|unknown",
  "transcript_available": false,
  "caption_button_visible": false,
  "caption_tracks_found": false,
  "media_candidates_found": false,
  "page_assets_checked": false,
  "page_assets_bundle_attempted": false,
  "player_data_checked": false,
  "network_media_checked": "checked|not_supported|not_checked",
  "browser_derived_files": [],
  "public_media_or_subtitle_urls": [],
  "yt_dlp_chrome_cookies_attempted": false,
  "yt_dlp_chrome_cookies_succeeded": false,
  "cookies_required": false,
  "chrome_deep_probe_exhausted": false,
  "deep_probe_layers_executed": [],
  "deep_probe_media_found": false,
  "browser_derived_media_exported": false,
  "next_route": "normalize_transcript|parse_subtitle|local_asr|yt_dlp_with_cookies|request_cookies|request_primary_material|degraded|blocked|failed",
  "status_reason": "",
  "operator_notes": ""
}
```

## Field Rules

- `url` must be the inspected URL, not a search result or redirected summary page.
- `platform` should be conservative. Use `unknown` when the page identity is not
  clear.
- `page_loaded` means the browser rendered the target page enough to inspect
  video state. It does not mean media was acquired.
- `visible_transcript_checked` must be `true` only after the transcript/caption
  UI was actually inspected.
- `transcript_available` may be `true` only when transcript text is visible,
  copyable, or exported as a local subtitle/transcript artifact.
- `caption_tracks_found` may be `true` for discovered tracks, but discovered URLs
  alone are candidates. They are not primary material until fetched and parsed.
- `media_candidates_found` may be `true` for candidate media sources, but it does
  not open the source gate by itself.
- `browser_derived_files` must list local files only. Do not list private tokens,
  signed playback URLs, or raw cookies.
- `public_media_or_subtitle_urls` may list confirmed public URLs, but the source
  class remains candidate-only until a local file is saved and processed.
- `cookies_required` must be `true` when acquisition is blocked by sign-in,
  cookie decryption failure, bot check, age/region/account state, or a platform
  request that likely needs user-exported cookies.
- `chrome_deep_probe_exhausted` may be `true` only after the required layers in
  `chrome-routing.md` have been tried or explicitly marked unavailable.
- `next_route` must choose the next safe route. Do not choose a full analysis
  route unless primary transcript, subtitle, browser-visible transcript, or
  transcribable local media exists.

## Allowed Next Routes

- `normalize_transcript`: browser-visible transcript or exported text transcript
  exists and can be normalized.
- `parse_subtitle`: local `.srt`, `.vtt`, `.sbv`, or equivalent subtitle file
  exists.
- `local_asr`: local audio/video file exists and may be transcribed.
- `yt_dlp_with_cookies`: bare extraction was blocked but Chrome/user cookies have
  not yet been tried.
- `request_cookies`: Chrome cookie extraction failed or sign-in/bot state needs a
  user-exported Netscape `cookies.txt`.
- `request_primary_material`: no safe acquisition route remains; ask the user for
  transcript, subtitle, audio, or video.
- `degraded`: only title, description, chapters, screenshots, or secondary
  context are available.
- `blocked`: CAPTCHA, paywall, private, permission, region, or account barrier
  prevents first-hand acquisition.
- `failed`: local or tool failure occurred without a permission block.

## Minimal Metadata-Only Example

```json
{
  "schema_version": 1,
  "url": "https://example.invalid/video",
  "platform": "other",
  "page_loaded": true,
  "page_state_observed": "metadata_only",
  "login_state_visible": "unknown",
  "bot_check_visible": false,
  "title_visible": true,
  "description_visible": true,
  "chapters_visible": false,
  "visible_transcript_checked": true,
  "visible_transcript_status": "not_visible",
  "transcript_available": false,
  "caption_button_visible": false,
  "caption_tracks_found": false,
  "media_candidates_found": false,
  "page_assets_checked": true,
  "page_assets_bundle_attempted": false,
  "player_data_checked": true,
  "network_media_checked": "not_supported",
  "browser_derived_files": [],
  "public_media_or_subtitle_urls": [],
  "yt_dlp_chrome_cookies_attempted": false,
  "yt_dlp_chrome_cookies_succeeded": false,
  "cookies_required": false,
  "chrome_deep_probe_exhausted": true,
  "deep_probe_layers_executed": ["visible_transcript", "pageAssets_list", "playwright_evaluate"],
  "deep_probe_media_found": false,
  "browser_derived_media_exported": false,
  "next_route": "request_primary_material",
  "status_reason": "Only title and description were visible; no transcript, subtitle, or media file was acquired.",
  "operator_notes": ""
}
```

## Gate Reminder

Chrome can support full decomposition only after it produces or helps acquire
first-hand material:

- browser-visible transcript text,
- a local subtitle/transcript file,
- a local media file that ASR successfully transcribes, or
- a public subtitle/media URL that was fetched, saved, and processed.

If Chrome only confirms title, description, chapters, screenshots, metadata, or
blocked page state, the result must stay `secondary_only`, `source_blocked`,
`source_failed`, or `degraded_report_only`.
