# Transcription Fallback

Use this order when a workflow needs transcript material:

## Priority of Paths (highest to lowest)

1. **Already-available subtitles or transcripts** — from the source page, platform caption APIs, or user-provided transcript/subtitle files.
2. **yt-dlp with Chrome cookies** — when yt-dlp bare is blocked by a platform, retry with `--cookies-from-browser chrome`. This uses the user's own browser identity to fetch subtitles or audio that they are already authorized to access. This is the fastest path from "blocked" to "primary material in hand" and must be attempted before falling back to slower routes.
3. **yt-dlp bare** — when the platform does not block bare requests, use yt-dlp without cookies to download subtitles or audio.
4. **Chrome-derived media probe** — when neither direct yt-dlp nor yt-dlp with Chrome cookies has succeeded, use the Chrome deep-probe sequence (defined in `chrome-routing.md`) to search for exportable subtitle or media assets through the Codex Chrome extension. This path is slower and more involved than yt-dlp with Chrome cookies, so it runs only after yt-dlp paths have been exhausted.
5. **User-provided local video/audio file** — when no remote path yields material and the user provides a local `.mp4`, `.m4a`, `.mp3`, `.wav`, `.webm`, `.mkv`, or similar media file, run the direct local faster-whisper fallback script.
6. **Hearsay MCP, WhisperX, or another ASR route** — only as a backup when the direct script is unavailable or fails.

## Path 1: Already-Available Subtitles or Transcripts

Prefer existing reliable subtitles or transcripts from the source page, yt-dlp, user-provided files, or platform caption APIs. Record the source and confidence.

## Path 2: yt-dlp with Chrome Cookies (primary fast path after block)

When a yt-dlp bare request returns HTTP 429, bot check, sign-in required, RequestBlocked, or a similar platform block on a platform like YouTube, the agent MUST retry with:

```
yt-dlp --cookies-from-browser chrome <URL>
```

This uses the user's own Chrome profile cookies. It is the user's own browser identity on their own machine — not a credential handoff to a third party, not a bypass technique.

After yt-dlp with Chrome cookies:

- **If subtitles are obtained** (`.vtt`, `.srt`, etc.): they qualify as `primary_transcript`. The source may enter `source_confirmed`.
- **If audio is obtained** (`.m4a`, `.opus`, `.mp3`, etc.): it qualifies as `primary_audio_asr` after local ASR succeeds. The source may enter `source_confirmed`.
- **If yt-dlp with Chrome cookies also fails**: record the failure and continue to Path 4 (Chrome-derived media probe).

Useful yt-dlp flags for this path:

```
# Subtitles only, with auto-generated captions
yt-dlp --cookies-from-browser chrome --skip-download --write-subs --write-auto-subs <URL>

# Audio only for downstream ASR
yt-dlp --cookies-from-browser chrome -f bestaudio --extract-audio --audio-format mp3 <URL>

# List available subtitles
yt-dlp --cookies-from-browser chrome --list-subs <URL>
```

## Path 3: yt-dlp Bare

When the platform does not block bare requests, use yt-dlp without cookies. Same flags as above, without `--cookies-from-browser chrome`.

## Path 4: Chrome-Derived Media Probe

When yt-dlp with Chrome cookies also fails, execute the Chrome deep-probe sequence defined in `chrome-routing.md`:

1. Visible transcript / caption UI inspection
2. `pageAssets.list()` — inventory page assets
3. `pageAssets.bundle()` — export discovered subtitle or media assets
4. Playwright `evaluate()` — inspect DOM for captionTracks, player response data, `<track>` elements, public media `<source>` tags
5. Network / media asset inspection — when supported by the current plugin documentation

A Chrome-derived media asset qualifies as `browser_derived_media` (see `source-status.md`) only when:
- An actual local subtitle or media file was exported via pageAssets; or
- A public downloadable media/subtitle URL was confirmed and fetched, then saved locally; and
- Subsequent ASR or subtitle parsing succeeds.

"Chrome can play the page" alone does NOT qualify as `browser_derived_media`.

## Path 5: User-Provided Local File + Direct faster-whisper

If an allowed local video/audio file exists, run the direct local faster-whisper fallback script.

## Path 6: Hearsay MCP / WhisperX / Other ASR

Use Hearsay MCP, WhisperX, or another ASR route only as a backup when the direct script is unavailable or fails.

## Allowed ASR Inputs

Allowed inputs:

- User-provided local `.mp4`, `.m4a`, `.mp3`, `.wav`, `.webm`, `.mkv`, or similar media files.
- User-provided transcript/subtitle files.
- Public subtitles or media files obtained through yt-dlp (bare or with `--cookies-from-browser chrome`).
- Subtitle or media files exported through Chrome pageAssets, or fetched from a confirmed public downloadable URL discovered during the Chrome deep-probe.

Not allowed as ASR inputs:

- A Chrome tab merely playing a video (no actual file exported).
- Material that requires bypassing CAPTCHA, paywall, login, region lock, account permission, or platform anti-bot controls.
- Restricted media segments obtained by circumventing access controls.

If none of the allowed inputs exists after all six paths have been exhausted, stop and request primary material instead of inventing content from metadata.

## ASR Quality Policy

Do not treat every ASR transcript as a complete verbatim transcript. Choose the model and confidence label based on the user's goal:

- `tiny`: use for low-cost workflow validation, rough topic extraction, and fast structure tests. Mark exact wording confidence as low or medium-low, especially for Chinese, accents, music, noisy audio, or overlapping speech.
- `base`: use as the default minimum for normal knowledge-video decomposition when no official subtitle exists and the user expects usable content analysis.
- `small`: prefer for Chinese knowledge videos, serious reports, full transcript requests, or any case where the report will rely on wording and examples.
- Larger models may be used only when the user asks for higher accuracy and accepts the extra time.

Language selection:

- Use `--language zh` for Chinese audio when known.
- Use `--language en` for English audio when known.
- Omit the language only when the language is uncertain or mixed.

If a quick model is used because the user requested speed or low token cost, state this in `00_source/acquisition_notes.md`, `05_gap_check/gap_check.md`, and the final response. Do not call the transcript "complete" or "verbatim" unless the subtitle source or ASR quality supports that claim.

## Failure and Timeout Policy

The first local ASR run may spend time downloading or loading a model. A timeout does not necessarily mean the account has no quota or the tool is broken. Check whether the delay came from model download, model load, long audio duration, CPU-only execution, or blocking transcription.

If faster-whisper times out:

1. Record the command, model, language, audio duration when known, elapsed time, and failure point in `00_source/acquisition_notes.md`.
2. Retry with a smaller model only for rough workflow validation, or with a larger timeout for serious transcript work.
3. Try Hearsay, WhisperX, or another ASR route only after the direct fallback is unavailable, fails repeatedly, or the user asks for that route.
4. If no transcript can be produced, stop at a degraded source-status artifact instead of inventing content from metadata.

Example command:

```powershell
& 'C:\Users\Socrates\.codex\tools\hearsay-venv\Scripts\python.exe' `
  'C:\Users\Socrates\.codex\skills\knowledge-video-decomposer\scripts\transcribe_faster_whisper.py' `
  'C:\path\to\input.mp4' `
  'C:\path\to\01_transcript\clean_transcript.md' `
  'C:\path\to\01_transcript\clean_transcript.jsonl' `
  --model base --language zh --vad --timeout-seconds 3600
```

Record the chosen source and any failed branches in `00_source/acquisition_notes.md`.

`--timeout-seconds` is a soft timeout. It is checked when control returns to the script, so it may not interrupt a model download, model load, or blocking internal faster-whisper transcription call until that call returns.

## Required Transcript Provenance

Every transcript artifact must record:

- Source type: official subtitle, automatic caption, user transcript, yt-dlp Chrome cookies subtitle, yt-dlp Chrome cookies audio + ASR, Chrome pageAssets export, Chrome deep-probe URL fetch, direct faster-whisper, Hearsay, WhisperX, or other.
- Tool and version if available.
- Model name for ASR.
- Language setting.
- Whether VAD was used.
- Runtime or elapsed time when available.
- Confidence split: exact wording confidence and structural-summary confidence.
- Known limitations: missing captions, noisy audio, uncertain language, clipped source, unavailable timestamps, or partial transcript.
