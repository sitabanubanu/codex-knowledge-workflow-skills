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
