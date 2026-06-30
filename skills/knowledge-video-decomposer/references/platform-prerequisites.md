# Platform Acquisition Prerequisites

Use this reference before processing YouTube or other platform video pages where
bot checks, sign-in checks, JavaScript player challenges, browser cookies, or
missing subtitles may affect source acquisition.

This file defines environment prerequisites, safe user handoff points, and
recovery routes. It does not authorize bypassing paywalls, CAPTCHA, region locks,
private videos, account permissions, or platform access controls.

## Required Tools

For YouTube and similar platform video acquisition, check these tools before
declaring a route failed:

- `yt-dlp`: required for metadata, subtitles, audio, and format discovery.
- `ffmpeg`: required for audio/video fixups and downstream media handling.
- Local ASR, such as `faster-whisper`: required when no reliable subtitles exist
  but an allowed audio/video file can be acquired.
- A JavaScript runtime for yt-dlp, preferably Node.js or Deno: often required
  for YouTube player `n` challenge solving.
- A safe cookies handoff path: required when bare yt-dlp hits YouTube
  bot/sign-in checks and browser-cookie decryption fails.

Run `scripts/doctor.py` before long platform acquisition runs, when the
environment is unknown, or after any tool-path/authentication setup failure.
Doctor is a read-only environment check. It does not fetch media, launch Chrome,
copy cookie values, or contact video platforms.

Recommended output location:

```powershell
python scripts/doctor.py `
  --output-json 00_source/logs/doctor_report.json `
  --output-md 00_source/logs/doctor_report.md `
  --pretty
```

Use the doctor capability matrix to decide which local prerequisite sets are
present. These values do not prove that a platform request will succeed; they
only say the local toolchain is ready to try that route.

- `youtube_public_metadata_prerequisites`
- `youtube_cookies_js_subtitle_audio_prerequisites`
- `local_audio_video_asr_prerequisites`
- `x_video_metadata_download_prerequisites`
- `xiaohongshu_metadata_download_prerequisites`
- `chrome_page_probe_prerequisites`
- `safe_utf8_artifact_writes`

## Acquisition Runner

Use `scripts/acquisition_runner.py` as the first programmatic platform probe
when a task starts from a video URL. It combines local doctor output, bounded
yt-dlp metadata/subtitle/format checks, source-status gating, and stable UTF-8
artifact writing.

Recommended probe-only command:

```powershell
python scripts/acquisition_runner.py `
  --input <video-url> `
  --output-root outputs/knowledge-workflow/<run-id> `
  --youtube-cookies work/youtube-cookies/youtube.cookies.txt `
  --list-subtitles `
  --list-formats `
  --use-js-runtime `
  --pretty
```

Add `--use-remote-components` only when the user accepts yt-dlp fetching the
recommended remote solver component for current YouTube player challenges.

Default behavior is conservative:

- Listing subtitles or media formats records an available route, not acquired
  primary material.
- `source_confirmed` requires an actual local subtitle/transcript file, a
  browser-visible transcript, browser-derived media processed into transcript,
  or ASR output from an acquired/local audio/video file.
- Raw stdout/stderr probe logs go under `00_source/raw/`.
- Cookie values must never be copied into reports, logs, chat, or Git.

If the user explicitly allows subtitle acquisition, add:

```powershell
--download-subtitles
```

This downloads subtitles only. It still does not download audio/video media.
If subtitle download succeeds and local subtitle files are written, the source
can be marked as `source_confirmed` for transcript-based decomposition.

## Platform Media Runner

Use `scripts/platform_media_runner.py` when the workflow needs a productized
URL-to-material acquisition step instead of a probe-only report. It wraps
`acquisition_runner.py`, tries subtitles first, and can download audio for
downstream ASR.

Recommended auto command:

```powershell
python scripts/platform_media_runner.py `
  --input <video-url> `
  --output-root outputs/knowledge-workflow/<run-id>/10_video `
  --youtube-cookies work/youtube-cookies/youtube.cookies.txt `
  --use-js-runtime `
  --mode auto `
  --pretty
```

Modes:

- `probe`: run metadata/subtitle/format probes only.
- `subtitles`: try subtitle acquisition only.
- `audio`: download audio for ASR.
- `auto`: try subtitles first, then audio when media formats are available and
  no subtitle was acquired.

Output:

```text
00_source/platform_media_result.json
00_source/platform_media_notes.md
```

Gate rule:

- A downloaded subtitle may be passed to `transcript_normalizer.py`.
- A downloaded audio file must be passed to `asr_pipeline.py`.
- Downloaded audio is recorded as `pending_primary_media_for_asr`; it must not
  be treated as `primary_audio_asr` or `source_confirmed` until ASR succeeds.
- Listed formats, metadata, and discovered media URLs do not unlock full
  decomposition by themselves.

## Recommended yt-dlp Baseline

Use the newest available yt-dlp in the active runtime before diagnosing platform
blocks. If a stable release fails on current YouTube player challenges, try the
newest pre-release only when the user accepts using a pre-release dependency.

Record the version used in acquisition notes.

## YouTube Acquisition Order

Use this order for YouTube:

1. Try public metadata/subtitle discovery with yt-dlp bare.
2. If yt-dlp bare returns `Sign in to confirm`, bot check, HTTP 429, login
   required, or RequestBlocked, try `yt-dlp --cookies-from-browser chrome`.
3. If `--cookies-from-browser chrome` fails with DPAPI/App-Bound decryption
   errors, do not loop over the same Chrome profile. Switch to a user-exported
   `cookies.txt` handoff.
4. If a user-exported `cookies.txt` is available, retry yt-dlp with
   `--cookies <cookies.txt>`.
5. If yt-dlp with cookies reports `n challenge solving failed`, `Only images are
   available`, or only storyboard formats appear, add a JavaScript runtime and
   the recommended remote solver component:

```powershell
yt-dlp --cookies <cookies.txt> `
  --js-runtimes node:<path-to-node.exe> `
  --remote-components ejs:github `
  --list-formats <url>
```

6. If subtitles exist, download subtitles and treat them as `primary_transcript`.
7. If no subtitles exist but audio formats are available, download audio and run
   local ASR. Treat successful ASR output as `primary_audio_asr`.
8. If cookies plus JavaScript runtime still cannot expose subtitles, audio, or a
   browser-derived media file, stop full decomposition and request primary
   material or produce only a degraded/acquisition report.

## User-Exported cookies.txt Handoff

Use a user-exported Netscape-format `cookies.txt` when direct browser-cookie
decryption fails. This is a user handoff, not an automated credential extraction
route.

Allowed:

- Ask the user to install or use a trusted local browser extension that exports
  Netscape-format cookies, such as a locally operating `cookies.txt` exporter.
- Ask the user to export cookies for YouTube or the target site and place the
  file in a local workspace path.
- Use the exported file only for the requested source acquisition.
- Store the file under an ignored local working directory such as
  `work/youtube-cookies/`.
- Record that a user-exported cookies file was used, without copying cookie
  values into reports, logs, chat, or Git.

Not allowed:

- Do not install browser extensions on the user's behalf.
- Do not click through extension permission prompts without explicit user action.
- Do not paste cookie contents into chat.
- Do not commit cookies files or include them in artifacts.
- Do not pass cookies to third-party services.
- Do not use cookies to access material the user is not authorized to view.

## Common Failure Signals and Routes

### `Sign in to confirm you're not a bot`

Meaning: bare yt-dlp is blocked by YouTube.

Next route:

1. Try `--cookies-from-browser chrome`.
2. If that fails with DPAPI/App-Bound, request user-exported `cookies.txt`.

### `Failed to decrypt with DPAPI`

Meaning: yt-dlp could not decrypt Chromium cookies from the local profile. On
newer Windows Chrome versions this often indicates App-Bound cookie encryption.

Next route:

1. Do not repeat the same profile in a loop.
2. Try another browser only if it is present and not locked.
3. Prefer user-exported `cookies.txt`.

### `Could not copy Chrome cookie database`

Meaning: the browser cookie database may be locked by a running browser process
or unavailable to the current runtime.

Next route:

1. Ask the user to close that browser if they want to use it.
2. Otherwise use a user-exported `cookies.txt`.

### `n challenge solving failed`

Meaning: yt-dlp could not solve the current YouTube player JavaScript challenge.
The symptom may be that only storyboard/image formats are listed.

Next route:

1. Add a supported JavaScript runtime with `--js-runtimes`.
2. If yt-dlp asks for a solver component, allow the recommended remote component
   only when the user accepts network dependency fetching:

```powershell
--remote-components ejs:github
```

3. Retry format listing before declaring media unavailable.

### `Only images are available`

Meaning: yt-dlp did not expose audio/video formats, often because JavaScript
challenge solving failed.

Next route:

1. Add JavaScript runtime and remote solver as above.
2. Retry `--list-formats`.
3. If audio appears, download audio and run ASR.

### No subtitles found

Meaning: the platform does not expose manual or automatic captions to yt-dlp.

Next route:

1. If audio/video is available through an allowed route, download audio and run
   local ASR.
2. If no media is available, run Chrome deep-probe per `chrome-routing.md`.
3. If no primary material is available, stop at degraded/acquisition reporting.

## Recording Requirements

When any of these routes are used, record:

- yt-dlp version.
- Whether cookies were bare, browser-derived, or user-exported `cookies.txt`.
- Whether Chrome cookie decryption failed with DPAPI/App-Bound symptoms.
- Whether a JavaScript runtime was used.
- Whether `--remote-components ejs:github` was used.
- Whether subtitles were absent.
- Whether audio was downloaded.
- ASR model, language, runtime, and confidence if ASR was used.

Never record cookie values.

## Doctor Checks To Add

`scripts/doctor.py` should check:

- yt-dlp import and version.
- ffmpeg availability.
- faster-whisper availability.
- Node.js availability for yt-dlp JavaScript challenge solving. Deno can be
  added later as a second JavaScript runtime check.
- Chrome plugin file availability.
- DPAPI/App-Bound failure detection.
- Presence of a local ignored cookies file path.
- Whether output writing preserves UTF-8.

It must not record cookie values, run platform downloads, or bypass access
controls. Network health probes such as listing YouTube subtitles can be added
later behind an explicit opt-in flag, but the default doctor must remain
read-only and local.
