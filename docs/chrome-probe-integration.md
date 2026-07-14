# Authorized Browser Export Integration

The current browser handoff is intentionally a two-layer workflow:

1. A browser-capable agent observes page state and writes a stable JSON contract.
2. The repository imports the local artifact into Acquisition Bundle v2 and
   applies the normal source gate.

The repository CLI does not control Chrome by itself.

## Current CLI

```powershell
python .\kw.py browser-import `
  --input-file .\exports\visible-transcript.txt `
  --source-url https://www.youtube.com/watch?v=example `
  --platform youtube `
  --target video_content `
  --operation extract_transcript `
  --project-root .\outputs\browser-video
```

Use `kw run` with `--browser-source-url` and `--browser-platform` for the
complete ingest, audit, and compose flow. The manifest records
`acquisition_layer: browser_export`, hashes the artifact, preserves a redacted
source URL, and records browser-session use without copying credentials.
Page-body exports must be UTF-8 `.txt` or `.md`. Video targets may also import
subtitles or raw audio/video; raw media remains `content_scope: media` until
ASR creates a traceable `video_transcript`.

## Legacy Observation CLI

URL-only candidate example:

```powershell
python .\kw.py chrome-probe `
  --input-json .\examples\chrome_probe\chrome_observation_url_only.json `
  --project-root .\outputs\knowledge-workflow\chrome-probe-demo
```

Local exported subtitle example:

```powershell
python .\kw.py chrome-probe `
  --input-json .\examples\chrome_probe\chrome_observation_exported_subtitle.json `
  --project-root .\outputs\knowledge-workflow\chrome-probe-exported-subtitle
```

Visible transcript example:

```powershell
python .\kw.py chrome-probe `
  --input-json .\examples\chrome_probe\chrome_observation_visible_transcript.json `
  --project-root .\outputs\knowledge-workflow\chrome-probe-visible-transcript
```

Relative local file paths in the observation JSON are resolved relative to the
JSON file itself. This makes browser-agent handoff folders portable.

`chrome-probe` is retained for compatibility and diagnostics. It writes a
legacy observation report under `10_video/00_source`; it does not create a
Bundle v2 manifest and must not be treated as a successful current run.

## Important Boundary

"Chrome can play the video" is not primary material. Full analysis requires:

- exported subtitle file that can be parsed,
- exported media file that can be transcribed,
- browser-visible transcript that can be cited,
- or a confirmed public media/subtitle URL that is fetched and saved locally.

URL-only observations remain blocked or failed until the material is actually
acquired and processed.

A visible transcript observation is useful only after the transcript text is
saved as a local, citeable artifact and then normalized through the transcript
route.
