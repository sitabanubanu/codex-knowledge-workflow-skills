# User Manual

## Start With the Result Index

Every run writes:

```text
result_index.md
logs/result_index.json
logs/status_summary.json
```

The result index reports acquisition status, source status, target, whether
full analysis is allowed, whether each provenance layer is current, stale-file
presence, and the next safe action.

## Choose the Target, Not Only the URL

Use `--target` to state what material you intend to analyze:

```text
video_content   requires video_transcript
social_post     requires social_post_text
web_article     requires article_body
repository      requires repository_document
search_triage   remains secondary
```

`--operation auto` selects the corresponding operation. You can also set
`read`, `search`, or `extract_transcript` explicitly.

Examples:

```powershell
python .\kw.py run --input <youtube-or-bilibili-url> --target video_content --operation extract_transcript --mode audit
python .\kw.py run --input <x-or-xiaohongshu-url> --target social_post --operation read --mode audit
python .\kw.py run --input https://example.com/article --target web_article --operation read --mode audit
python .\kw.py run --input https://github.com/owner/repo --target repository --operation read --mode audit
```

Do not select `social_post` when the actual task is to analyze an embedded
video. The post caption and video transcript are separate source scopes.

## Inspect Capability Before a Live Run

```powershell
python .\kw.py agent-reach doctor
python .\kw.py agent-reach plan --input <url> --target <target> --operation <operation>
```

The plan distinguishes `active_backend_ready`, `operation_supported`, and
`capability_ready`. Acquisition executes only when capability is ready.

## End-to-End Run

```powershell
python .\kw.py run --input <url-or-file> --target <target> --operation <operation> --mode audit
```

The route is:

```text
preflight
  -> staged acquisition attempt
  -> validated Bundle v2
  -> target/scope source gate
  -> normalization or ASR
  -> claims and evidence audit
  -> document planning
  -> quality gate and final report
  -> provenance-aware result index
```

## Run Stages Separately

```powershell
python .\kw.py acquire --input <url-or-query> --target <target> --operation <operation> --project-root <project>
python .\kw.py validate-bundle --bundle <project>\00_acquisition\manifest.json
python .\kw.py ingest --bundle <project>\00_acquisition\manifest.json --project-root <project>
python .\kw.py audit --project-root <project>
python .\kw.py compose --project-root <project>
python .\kw.py status --project-root <project>
python .\kw.py result --project-root <project>
```

Raw Agent-Reach output is never sent directly to the composer.

## Search

Use `--query` to force the input to the search route, even if the text resembles
a local path:

```powershell
python .\kw.py acquire --query --input "research question" --target search_triage --operation search --project-root <project>
```

Search results remain secondary and cannot unlock a normal final report.

## YouTube Options

The primary `kw run` and `kw acquire` paths apply these options to yt-dlp:

- `--youtube-cookies <path|auto>`;
- `--youtube-browser edge|chrome` to select the browser that actually owns the
  authorized login state. The browser-control plugin name is not evidence of
  the host browser identity. Use only one of `--youtube-cookies` and
  `--youtube-browser`;
- `--ytdlp`, `--node`, `--use-js-runtime`;
- `--use-remote-components`;
- `--subtitle-languages`;
- `--ytdlp-player-clients`, `--ytdlp-extractor-args`;
- `--youtube-visitor-data`, `--youtube-po-token`;
- `--ytdlp-proxy`, `--ytdlp-impersonate`;
- request sleep, retry sleep, and timeout options.

Sensitive values are passed to the process but redacted from persisted output.
`--platform-mode probe` reads metadata only; `subtitles` avoids transcription
fallback; `audio` uses the Agent-Reach transcription route; `auto` tries
subtitles and then transcription.

## Resume and History

A project root belongs to one source, target, and operation. Reuse without
`--resume` fails.

```powershell
python .\kw.py run --input <same-input> --target <same-target> --operation <same-operation> --project-root <same-project> --resume
```

Resume creates a new attempt. Previous acquisition and downstream trees move
to `acquisition_history/` and `run_history/`. A changed local file, different
target, or different operation requires a new project root.

## Blocked or Degraded Runs

A safe degraded run answers:

1. What was acquired?
2. Which target scope is still missing?
3. Why is full analysis blocked?
4. Which authorized artifact or backend is needed next?

It may ask for a transcript, subtitle, local media for ASR, an authorized
browser export, or a healthy backend. It must not manufacture missing source
material.

## Delivery Conditions

`final_report.md` is deliverable only when:

- source status is `source_confirmed` or `source_partial`;
- the target-compatible scope passed the gate;
- evidence audit and claim map are present;
- quality gate approves the report;
- gate, analysis, composer, and final-report receipts all match current hashes.

`kw export`, normal templates, quality review, and batch synthesis reject stale
or unverified outputs even when old files remain on disk.
