# Installation

This project has three setup levels. Start with Level 1 unless you already know
you need local media transcription or platform URL acquisition.

## Level 1: Minimal Local Transcript Demo

Use this level to prove the core workflow. It does not require platform URLs,
cookies, browser state, ffmpeg, or ASR.

Requirements:

- Python 3.10 or newer.
- Git.
- Codex installed on the machine where you want to use the skills.

Create and activate a virtual environment if desired:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install the Codex skills.

Windows:

```powershell
.\sync_to_codex_skills.ps1 -DryRun
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly
```

macOS / Linux:

```bash
./sync_to_codex_skills.sh --dry-run
./sync_to_codex_skills.sh
./sync_to_codex_skills.sh --verify-only
```

Run the demo:

```powershell
python .\kw.py demo
```

macOS / Linux:

```bash
python kw.py demo
```

Open:

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

## Level 2: Local Audio / Video And ASR

Use this level when you have a local audio or video file but no transcript or
subtitle file.

Additional requirements:

- `ffmpeg`
- `ffprobe`
- `faster-whisper` in the selected ASR Python environment
- enough local disk and compute for the chosen ASR model

Example dependency installs:

```powershell
python -m pip install faster-whisper
```

macOS with Homebrew:

```bash
brew install ffmpeg
python -m pip install faster-whisper
```

Ubuntu / Debian:

```bash
sudo apt-get update
sudo apt-get install ffmpeg
python -m pip install faster-whisper
```

Check the environment:

```powershell
python .\kw.py doctor
```

The default doctor output is a short route-readiness summary for humans. Use
`--pretty` or `--json` when you need the full machine-readable diagnostic data,
or `--output-md doctor.md` when you want a Markdown report to keep with a run.

Run with a local media file:

```powershell
python .\kw.py run `
  --input C:\path\to\video.mp4 `
  --mode audit `
  --language en `
  --final-language en
```

ASR transcripts are not guaranteed verbatim. The workflow records timestamp
coverage, missing word timestamps, speaker-label limits, and other evidence
limits before allowing downstream reports.

## Level 3: Platform URLs / YouTube

Use this level only after the local transcript demo works.

Platform URL support is best effort. It can fail because of missing subtitles,
HTTP 429, bot checks, login state, cookies, player changes, region rules, or
network conditions. Failure should produce blocked or degraded diagnostics, not
a fake complete report.

Additional tools may be useful:

- `yt-dlp`
- Node.js
- `yt-dlp-ejs`
- `curl_cffi`
- user-exported Netscape `cookies.txt`, when authorized
- Codex Chrome plugin, when Chrome page observation is needed

Example installs for the Python runtime used by `yt-dlp`:

```powershell
python -m pip install yt-dlp yt-dlp-ejs curl_cffi
```

Important: install `yt-dlp-ejs` and `curl_cffi` in the same Python environment
that actually runs `yt-dlp`. The active repository virtual environment may not
be the same runtime if `yt-dlp` is found on PATH or from a bundled Codex tool.
Use `python .\kw.py doctor --youtube-cookies auto --pretty` to see which
runtime is being checked.

Check the route:

```powershell
python .\kw.py doctor --youtube-cookies auto --pretty
python .\kw.py preflight --input "https://www.youtube.com/watch?v=..." --mode audit
```

Run a platform URL:

```powershell
python .\kw.py run `
  --input "https://www.youtube.com/watch?v=..." `
  --mode audit `
  --platform-mode auto `
  --youtube-cookies auto `
  --use-js-runtime `
  --use-remote-components
```

`--youtube-cookies auto` only means this fixed ignored local path:

```text
work/youtube-cookies/youtube.cookies.txt
```

It does not scan Downloads, browser profiles, or the full disk. Do not paste
cookie values into chat, issues, logs, Markdown reports, or commit history.

## Boundaries

This project does not attempt to bypass:

- CAPTCHA
- paywalls
- private videos
- region restrictions
- account permission barriers
- access-control systems
- platform anti-abuse controls

When primary material cannot be acquired safely, provide a transcript, subtitle
file, local audio/video file, or authorized cookies file. Otherwise the workflow
should stop at blocked or degraded status.

## Validation

Default offline checks:

```powershell
python .\kw.py demo
python .\tests\knowledge_workflow_regression.py
python .\tests\real_workflow_acceptance.py
.\sync_to_codex_skills.ps1 -VerifyOnly
```

macOS / Linux sync verification:

```bash
./sync_to_codex_skills.sh --verify-only
```
