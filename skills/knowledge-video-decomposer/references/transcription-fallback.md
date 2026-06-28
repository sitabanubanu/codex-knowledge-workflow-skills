# Transcription Fallback

Use this order when a workflow needs transcript material:

1. Prefer existing reliable subtitles or transcripts from the source page, yt-dlp, user-provided files, or platform caption APIs.
2. If Chrome can play the page but no visible transcript exists, do not treat Chrome playback as an audio file. First check whether a user-provided local video/audio file or a public, non-cookie media extraction is actually available.
3. If an allowed local video/audio file exists, run the direct local faster-whisper fallback script.
4. Use Hearsay MCP, WhisperX, or another ASR route only as a backup when the direct script is unavailable or fails.

## Allowed ASR Inputs

Allowed inputs:

- User-provided local `.mp4`, `.m4a`, `.mp3`, `.wav`, `.webm`, `.mkv`, or similar media files.
- User-provided transcript/subtitle files.
- Public subtitles or media files obtained without passing Chrome cookies, logged-in browser state, private tokens, or restricted player streams to an extractor.

Not allowed as ASR inputs:

- A Chrome tab merely playing a video.
- Chrome cookies, browser session state, signed player URLs, private playback tokens, or restricted media segments copied from the browser into `yt-dlp` or another extractor.
- Material that requires bypassing CAPTCHA, paywall, login, region lock, account permission, or platform anti-bot controls.

If none of the allowed inputs exists, stop and request primary material instead of inventing content from metadata.

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

- Source type: official subtitle, automatic caption, user transcript, direct faster-whisper, Hearsay, WhisperX, or other.
- Tool and version if available.
- Model name for ASR.
- Language setting.
- Whether VAD was used.
- Runtime or elapsed time when available.
- Confidence split: exact wording confidence and structural-summary confidence.
- Known limitations: missing captions, noisy audio, uncertain language, clipped source, unavailable timestamps, or partial transcript.
