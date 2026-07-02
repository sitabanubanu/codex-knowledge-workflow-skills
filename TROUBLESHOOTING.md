# Troubleshooting

Start with the run's `result_index.md`. It is the user-facing entry point and
usually contains the source status, whether full analysis was allowed, and the
next action.

## The Demo Fails

Run:

```powershell
python .\kw.py demo
python .\kw.py result --project-root .\outputs\knowledge-workflow\demo-transcript
```

Then inspect:

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
outputs/knowledge-workflow/demo-transcript/logs/run_state.json
```

## Doctor Says Warn Or Fail

Run:

```powershell
python .\kw.py doctor --youtube-cookies auto
```

Read the default route summary first. It tells you which paths are ready, which
paths need setup, and which warning still matters.

For a full diagnostic record, run:

```powershell
python .\kw.py doctor `
  --youtube-cookies auto `
  --output-md .\test_outputs\doctor.md `
  --output-json .\test_outputs\doctor.json `
  --overwrite
```

In the full Markdown or JSON report, read these sections first:

- `route_readiness`: what you can try now.
- `setup_requirements`: which route-specific setup is missing.
- `privacy`: confirms doctor did not fetch media, launch Chrome, or report
  cookie values.

Interpretation:

- Minimal local transcript demo should be available even when platform URL
  prerequisites are missing.
- Local audio/video requires ffmpeg, ffprobe, and faster-whisper.
- Platform URL preflight requires yt-dlp, but success is still best effort.
- YouTube cookies + JavaScript routes may require Node.js and a user-exported
  Netscape cookies file.
- Chinese Markdown/JSON should use UTF-8-safe artifact writers, `apply_patch`,
  or `PYTHONUTF8=1` when the environment reports non-UTF-8 console encodings.

## Only Metadata Was Found

Metadata cannot support a complete video analysis. Provide one of:

- transcript (`.txt`, `.md`, `.jsonl`, `.json`),
- subtitles (`.srt`, `.vtt`),
- local audio/video,
- authorized cookies only when appropriate.

## Platform URL Is Blocked

Common causes:

- bot or sign-in checks,
- HTTP 429,
- CAPTCHA,
- private or region-locked content,
- missing subtitles,
- yt-dlp player challenge changes.

Expected behavior: the workflow writes `source_blocked`, `source_failed`,
`secondary_only`, or `degraded_report_only`. It should not write a complete
analysis pack.

## ASR Does Not Run

Check:

```powershell
python .\kw.py doctor
```

Real ASR may require ffmpeg/ffprobe and faster-whisper dependencies. For smoke
tests using fixture inputs:

```powershell
python .\tests\asr_integration.py
```

For real ASR tests, set explicit environment variables and provide media:

```powershell
$env:KW_REAL_ASR_SMOKE='1'
$env:KW_REAL_ASR_MP3='C:\path\sample.mp3'
$env:KW_REAL_ASR_MP4='C:\path\sample.mp4'
python .\tests\asr_integration.py
```

## Final Report Was Not Written

Common causes:

- no accepted Source claim,
- evidence audit did not allow a full pack,
- source status was partial, blocked, failed, secondary-only, or degraded,
- required document planning artifacts are missing.

Read:

```text
20_document/quality_check.md
20_document/quality_gate.json
10_video/05_gap_check/claim_source_audit.json
```

## Chinese Text Looks Corrupted

Use UTF-8 write paths such as Python scripts, `apply_patch`, or the provided
artifact writers. Avoid writing long Chinese Markdown through PowerShell
redirection or inline command strings.
