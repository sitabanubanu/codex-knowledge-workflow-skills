# Troubleshooting

## `agent-reach` Not Found

Run:

```powershell
python -m pip install https://github.com/Panniantong/Agent-Reach/archive/main.zip
agent-reach install --env=auto --safe
agent-reach doctor --json
```

Or through the wrapper:

```powershell
python .\kw.py agent-reach install --safe
python .\kw.py agent-reach doctor
```

If still missing, the acquisition layer should write a `failed` bundle. Ingest
will produce `source_failed` and no final report.

## Acquisition Succeeded But No Report Was Written

Check:

```text
00_acquisition/manifest.json
10_video/00_source/source_status.json
result_index.md
```

Common safe outcomes:

- `metadata_only` -> `secondary_only`
- `blocked` -> `source_blocked`
- `failed` -> `source_failed`
- `unsupported` -> `degraded_report_only`

These states intentionally block normal `final_report.md`.

## YouTube Bot Check Or Sign-In

Do not loop over private browser profiles and do not read cookie values.

Allowed next actions:

- provide an authorized subtitle/transcript;
- provide local audio/video for ASR;
- configure Agent-Reach or an upstream tool outside the repository;
- record `blocked` and write degraded output.

`manifest.json` may record `cookies_used=true`, but never cookie contents.

## Bilibili Metadata Only

Bilibili metadata or page details are not a transcript. They cannot support a
complete video analysis. Provide subtitles, transcript, or local media for ASR.

## Empty Transcript

An empty transcript should become `source_failed` or degraded. It must not
create `video_analysis_pack.md` or `final_report.md`.

## Local Audio Without ASR

The bundle can record local audio/video, but the evidence layer needs a
transcript before full analysis. Run ASR or provide a transcript/subtitle.

## Result Index Looks Degraded

That usually means the gate worked. Read the next action in:

```text
result_index.md
10_video/00_source/degraded_source_report.md
```

## Do Not Commit

Before committing, check:

```powershell
git status --short
```

Do not commit:

- `work/`
- cookies
- tokens
- `outputs/`
- `test_outputs/`
- `__pycache__/`
- private logs
