# Supported Platforms And Inputs

The workflow is strongest when it starts from first-hand material: local
transcripts, subtitles, or local media that can be transcribed. Platform URL
support is intentionally conservative.

| Input | Stability | Full Report | Notes |
| --- | --- | --- | --- |
| Local transcript (`.txt`, `.md`, `.jsonl`, `.json`) | High | Yes | Best first-run and demo path. |
| Local subtitles (`.srt`, `.vtt`) | High | Yes | Timestamped evidence can be preserved. |
| Local audio/video (`.mp3`, `.mp4`, `.m4a`, `.webm`, `.wav`, `.mov`, `.opus`) | Medium-high | Yes, after ASR | Depends on ASR dependencies, language, audio quality, and run time. |
| YouTube public video | Medium-high | Yes, when subtitles/audio are acquired | May require cookies, Node.js support for yt-dlp, or local ASR. |
| X video | Low-medium | Unstable | Often blocked or metadata-only. Prefer user-provided media/transcript. |
| Xiaohongshu | Low | Usually no from URL alone | Prefer user-provided subtitle, recording, audio, or transcript. |
| Douyin | Low | Usually no from URL alone | Prefer user-provided primary material. |
| Generic web video page | Medium | Depends on exposed transcript/media | Chrome probe may help record page state. |
| Private/paywalled/CAPTCHA/region/account-gated page | Not a bypass target | No, unless user provides allowed primary material | The workflow records blocked/degraded status. |

## Source Status Rules

Full decomposition requires one of:

- `primary_transcript`
- `primary_audio_asr`
- `browser_visible_transcript`
- `browser_derived_media`

Metadata, screenshots, search snippets, Firecrawl context, and third-party
summaries are background only. They cannot upgrade a source to
`source_confirmed`.

## Recommended First Route

Run the local transcript demo first:

```powershell
python .\kw.py demo
```

Then use `kw.py preflight` before platform URLs:

```powershell
python .\kw.py preflight --input "https://www.youtube.com/watch?v=..." --mode audit
```
