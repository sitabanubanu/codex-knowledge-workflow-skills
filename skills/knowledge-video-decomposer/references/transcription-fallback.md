# Transcription Fallback

Use this order when a workflow needs transcript material:

## Priority of Paths (highest to lowest)

1. **Already-available subtitles or transcripts** - from the source page, platform caption APIs, or user-provided transcript/subtitle files.
2. **yt-dlp with Chrome cookies** - when yt-dlp bare is blocked by a platform, retry with `--cookies-from-browser chrome`. This uses the user's own browser identity to fetch subtitles or audio that they are already authorized to access. This is the fastest path from "blocked" to "primary material in hand" and must be attempted before falling back to slower routes.
3. **User-exported cookies.txt** - when browser-cookie decryption fails (for example DPAPI/App-Bound errors on Windows Chrome), ask the user to export Netscape-format cookies and use `--cookies <cookies.txt>`. See `platform-prerequisites.md`.
4. **yt-dlp with JavaScript runtime / solver** - when cookies work but yt-dlp reports `n challenge solving failed`, `Only images are available`, or only storyboards appear, add a supported JavaScript runtime and the recommended solver component before declaring audio unavailable.
5. **yt-dlp bare** - when the platform does not block bare requests, use yt-dlp without cookies to download subtitles or audio.
6. **Chrome-derived media probe** - when neither direct yt-dlp nor cookie-backed yt-dlp has succeeded, use the Chrome deep-probe sequence (defined in `chrome-routing.md`) to search for exportable subtitle or media assets through the Codex Chrome extension. This path is slower and more involved than yt-dlp with cookies, so it runs only after yt-dlp paths have been exhausted.
7. **User-provided local video/audio file** - when no remote path yields material and the user provides a local `.mp4`, `.m4a`, `.mp3`, `.wav`, `.webm`, `.mkv`, or similar media file, run the direct local faster-whisper fallback script.
8. **Hearsay MCP, WhisperX, or another ASR route** - only as a backup when the direct script is unavailable or fails.

## Path 1: Already-Available Subtitles or Transcripts

Prefer existing reliable subtitles or transcripts from the source page, yt-dlp, user-provided files, or platform caption APIs. Record the source and confidence.

## Path 2: yt-dlp with Chrome Cookies (primary fast path after block)

When a yt-dlp bare request returns HTTP 429, bot check, sign-in required, RequestBlocked, or a similar platform block on a platform like YouTube, the agent MUST retry with:

```
yt-dlp --cookies-from-browser chrome <URL>
```

This uses the user's own Chrome profile cookies. It is the user's own browser identity on their own machine - not a credential handoff to a third party, not a bypass technique.

After yt-dlp with Chrome cookies:

- **If subtitles are obtained** (`.vtt`, `.srt`, etc.): they qualify as `primary_transcript`. The source may enter `source_confirmed`.
- **If audio is obtained** (`.m4a`, `.opus`, `.mp3`, etc.): it qualifies as `primary_audio_asr` after local ASR succeeds. The source may enter `source_confirmed`.
- **If yt-dlp with Chrome cookies also fails**: record the failure and continue to Path 3 when the failure is browser-cookie decryption, or Path 6 when all yt-dlp routes are exhausted.

Useful yt-dlp flags for this path:

```
# Subtitles only, with auto-generated captions
yt-dlp --cookies-from-browser chrome --skip-download --write-subs --write-auto-subs <URL>

# Audio only for downstream ASR
yt-dlp --cookies-from-browser chrome -f bestaudio --extract-audio --audio-format mp3 <URL>

# List available subtitles
yt-dlp --cookies-from-browser chrome --list-subs <URL>
```

## Path 3: User-Exported cookies.txt

When yt-dlp bare is blocked and `--cookies-from-browser chrome` fails with
DPAPI/App-Bound, locked database, or similar local browser-cookie errors, switch
to a user-exported Netscape cookies file.

The agent may prepare a local ignored path and a validation script, but the user
must perform the sensitive browser extension install/export action. Do not paste
cookie contents into chat, do not log cookie values, and do not commit cookies.

Example commands:

```powershell
# Check subtitles with an exported cookies file
yt-dlp --cookies .\work\youtube-cookies\youtube.cookies.txt --list-subs <URL>

# Check formats with cookies
yt-dlp --cookies .\work\youtube-cookies\youtube.cookies.txt --list-formats <URL>
```

If the cookies file works but subtitles are unavailable, continue to audio
format discovery and ASR.

## Path 4: yt-dlp JavaScript Runtime / Solver

YouTube may require a JavaScript runtime for player challenge solving. Symptoms:

- `n challenge solving failed`
- `Only images are available`
- `--list-formats` shows only `sb0`, `sb1`, `sb2`, or other storyboard/image rows

If a Node.js or Deno runtime is available, retry with:

```powershell
yt-dlp --cookies <cookies.txt> `
  --js-runtimes node:<path-to-node.exe> `
  --remote-components ejs:github `
  --list-formats <URL>
```

If audio formats appear, download an audio-only format such as `140`, `251`,
or another suitable audio row, then run local ASR.

Record that JavaScript challenge solving and `--remote-components ejs:github`
were used. Do not use this route to bypass access controls; it is only for
normal player challenge handling after authorized source access is established.

## Path 5: yt-dlp Bare

When the platform does not block bare requests, use yt-dlp without cookies. Same flags as above, without `--cookies-from-browser chrome`.

## Path 6: Chrome-Derived Media Probe

When all yt-dlp routes fail to expose subtitles or media, execute the Chrome deep-probe sequence defined in `chrome-routing.md`:

1. Visible transcript / caption UI inspection
2. `pageAssets.list()` - inventory page assets
3. `pageAssets.bundle()` - export discovered subtitle or media assets
4. Playwright `evaluate()` - inspect DOM for captionTracks, player response data, `<track>` elements, public media `<source>` tags
5. Network / media asset inspection - when supported by the current plugin documentation

A Chrome-derived media asset qualifies as `browser_derived_media` (see `source-status.md`) only when:
- An actual local subtitle or media file was exported via pageAssets; or
- A public downloadable media/subtitle URL was confirmed and fetched, then saved locally; and
- Subsequent ASR or subtitle parsing succeeds.

"Chrome can play the page" alone does NOT qualify as `browser_derived_media`.

## Path 7: User-Provided Local File + Direct faster-whisper

If an allowed local video/audio file exists, run the direct local faster-whisper fallback script.

## Path 8: Hearsay MCP / WhisperX / Other ASR

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

If none of the allowed inputs exists after all acquisition paths have been exhausted, stop and request primary material instead of inventing content from metadata.

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
