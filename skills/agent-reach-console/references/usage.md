# Agent-Reach Console Usage

## URL Input

```powershell
python kw.py acquire --input <url> --project-root <project>
python kw.py ingest --bundle <project>\00_acquisition\manifest.json --project-root <project>
```

URL acquisition writes:

```text
00_acquisition/
  manifest.json
  artifacts/
  logs/
```

The next stage is always `source-gated-evidence-layer`.

## Local File Input

Local transcript, subtitle, audio, or video files can bypass Agent-Reach while
still using the same bundle protocol:

```powershell
python kw.py run --input .\input.vtt --mode audit
```

The CLI builds a local `00_acquisition/manifest.json` with
`acquisition_layer=local_file`, then sends it to ingest.

## Query Or Search Input

The first version records unsupported query/search routes as an
`unsupported` or degraded bundle unless a supported platform route is selected.
Future versions can route search through Agent-Reach search channels.

## Output Location

The manifest is the only stable output contract:

```text
<project>\00_acquisition\manifest.json
```

Do not use acquired artifacts directly for report writing. Pass the manifest to
`source-gated-evidence-layer`.
