# Knowledge Workflow Skills User Manual

This manual explains how to use the workflow after the quickstart. Start with
`README.md` and `QUICKSTART.md` if this is your first run.

## 1. Install

From the repository root:

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

The sync script installs only:

- `knowledge-workflow-console`
- `knowledge-video-decomposer`
- `knowledge-document-composer`

It does not install or publish `subagent-supervisor`.

For Python environments, ASR setup, and platform URL prerequisites, read
`INSTALL.md`.

## 2. First Run

Use the deterministic local transcript demo:

```powershell
python .\kw.py demo
```

Open:

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

If the demo succeeds, the core local transcript workflow is working.

## 3. Main Commands

```powershell
python .\kw.py doctor
python .\kw.py preflight --input <file-or-url> --mode audit
python .\kw.py run --input <file-or-url> --mode audit
python .\kw.py status --project-root <project-root>
python .\kw.py result --project-root <project-root>
python .\kw.py quality --project-root <project-root>
python .\kw.py template --project-root <project-root> --template research_brief
python .\kw.py batch `
  --input .\examples\batch_research\batch_links.csv `
  --output-root .\outputs\knowledge-workflow\batch-demo
```

`doctor` is the first diagnostic command when a route fails. The default output
is a concise route-readiness summary. Use `--pretty` for full JSON or
`--output-md doctor.md` for a Markdown report.

`quality` writes a human Markdown review and a sibling JSON file by default.
Use `--output-json` when another tool needs a specific JSON path.

## 4. Modes

| Mode | Use Case | Output Boundary |
| --- | --- | --- |
| `quick` | Low-cost first look. | Non-primary triage; no complete analysis pack. |
| `standard` | Video decomposition. | `video_analysis_pack.md` when source gates allow. |
| `audit` | Final report or reusable knowledge asset. | `quality_gate.json` and `final_report.md` when approved. |

## 5. Inputs

Recommended first:

- `.txt`
- `.md`
- `.srt`
- `.vtt`
- `.jsonl`
- `.json`

Supported with ASR:

- `.mp3`
- `.mp4`
- `.m4a`
- `.webm`
- `.wav`
- `.mov`
- `.opus`

Platform URLs are supported conservatively. Run preflight first.

## 6. Output Entry Point

Always start with:

```text
result_index.md
```

It tells you:

- status,
- source status,
- whether full analysis is allowed,
- whether the final report exists,
- where to look next.

## 7. Batch Research

Create a CSV with:

```csv
id,input,priority,goal,mode,language,template
001,path\to\transcript.txt,high,Understand the workflow,audit,en,research_brief
```

Run:

```powershell
python .\kw.py batch --input batch_links.csv --output-root .\outputs\knowledge-workflow\batch-demo
```

Batch outputs:

- `batch_status.csv`
- `batch_items.json`
- `batch_summary.md`
- `recommended_watch_order.md`
- `comparative_report.md`
- one project directory per item

Use `batch_summary.md` as the human index and `batch_items.json` for structured
automation. The comparative report compares readiness and source-gate status;
it does not replace the per-item final reports.

## 8. Templates

Available templates:

```powershell
python .\kw.py template --list
```

Current templates:

- `study_notes`
- `research_brief`
- `creator_script`
- `prompt_pack`
- `action_plan`

Templates are deterministic projections from approved workflow artifacts. They
reorganize the final report and claim map for a specific use case, but they do
not add new source claims.

Templates are deterministic projections from existing approved artifacts. They
do not add new source claims.

## 9. Chrome Probe

Chrome probe support normalizes a browser observation JSON. It does not control
Chrome by itself.

```powershell
python .\kw.py chrome-probe `
  --input-json .\examples\chrome_probe\chrome_observation_url_only.json `
  --project-root .\outputs\knowledge-workflow\chrome-probe-demo
```

URL-only observations do not unlock full analysis until actual subtitle/media
material is fetched, saved, and parsed or transcribed.

## 10. Troubleshooting

Read `TROUBLESHOOTING.md` first. The short rule is:

- if primary material exists, continue the workflow;
- if only metadata exists, do not write a complete analysis;
- if blocked, provide transcript, subtitles, local media, or authorized cookies
  when appropriate.

## 11. Validation

Default:

```powershell
python .\kw.py demo
python .\tests\knowledge_workflow_regression.py
python .\tests\live_platform_smoke.py
python .\tests\asr_integration.py
python .\tests\real_workflow_acceptance.py
```

Optional live platform and real ASR validation require explicit user-provided
URLs or media. See `docs/validation.md`.
