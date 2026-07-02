# Supported Platforms And Inputs

The workflow is strongest when it starts from first-hand material: local
transcripts, subtitles, or local media that can be transcribed. Platform URL
support is intentionally conservative.

| Input | Stability | Full Report | Notes |
| --- | --- | --- | --- |
| Local transcript | High | Yes | Best first-run and demo path. |
| Local subtitles | High | Yes | Timestamped evidence can be preserved. |
| Local audio/video | Medium-high | Yes, after ASR | Depends on ASR setup and audio quality. |
| YouTube public video | Medium-high | Yes, when material is acquired. | May require cookies or ASR. |
| X video | Low-medium | Unstable | Often blocked or metadata-only. |
| Xiaohongshu | Low | Usually no from URL alone. | Prefer user-provided material. |
| Douyin | Low | Usually no from URL alone. | Prefer user-provided material. |
| Generic web video page | Medium | Depends on exposed material. | Chrome probe may help. |
| Private or gated page | Not a bypass target. | No, unless material is provided. | Records blocked/degraded status. |

Local transcript extensions:

- `.txt`
- `.md`
- `.jsonl`
- `.json`

Local subtitle extensions:

- `.srt`
- `.vtt`

Local audio/video extensions:

- `.mp3`
- `.mp4`
- `.m4a`
- `.webm`
- `.wav`
- `.mov`
- `.opus`

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
