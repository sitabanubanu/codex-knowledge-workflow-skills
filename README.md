# Knowledge Workflow Skills

Auditable Codex workflow for turning videos, audio, subtitles, and transcripts into evidence-grounded knowledge reports.

给使用 Codex / 本地 Agent 的研究型用户，把长视频、音频、字幕和文字稿转成可审计知识资产。

## What This Is

This project is not a universal video crawler and not a casual video summarizer. It is a Codex skill package and local workflow that:

- checks whether first-hand material exists before analysis,
- turns transcripts, subtitles, or transcribable media into structured source artifacts,
- separates Source / Inference / Extension in the final report,
- writes degraded reports instead of pretending when primary material is unavailable.

## Who It Is For

Use it if you:

- use Codex or a local coding agent as a research assistant,
- analyze long videos, courses, interviews, podcasts, talks, or research material,
- need evidence-linked notes, reports, scripts, or knowledge-base inputs,
- care about knowing when a workflow is blocked or degraded.

It is not for bypassing CAPTCHA, paywalls, private videos, region locks, account permission barriers, or platform access controls.

## Three-Minute Start

First run the local transcript demo. Do not start with platform URLs.

```powershell
git clone https://github.com/sitabanubanu/codex-knowledge-workflow-skills
cd codex-knowledge-workflow-skills

.\sync_to_codex_skills.ps1 -DryRun
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly

python .\kw.py demo
```

After the demo finishes, open:

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

That file tells you the status, whether full analysis was allowed, where the final report is, and what to inspect next.

For a slower but stricter acceptance check:

```powershell
python .\tests\real_workflow_acceptance.py
```

## Why The Demo Comes First

Platform URLs can fail because of missing subtitles, login state, bot checks, cookies, region rules, player changes, or network conditions. The demo uses a local transcript, so it proves the core workflow first:

```text
local transcript
  -> source gate
  -> transcript normalization
  -> segmentation
  -> inventory
  -> source logic
  -> evidence audit
  -> video_analysis_pack.md
  -> document planning
  -> quality_gate.json
  -> final_report.md
  -> result_index.md
```

## Product Modes

| Mode | Use When | Primary Requirement | Allowed Output |
| --- | --- | --- | --- |
| `quick` | You only need a low-cost first look. | Metadata, visible page context, or secondary context may be enough. | Non-primary triage only. No complete analysis pack. |
| `standard` | You want the video content decomposed. | Transcript, subtitles, browser-visible transcript, or local media for ASR. | `video_analysis_pack.md` when source gates allow. |
| `audit` | You want a report, article, brief, or reusable knowledge asset. | Source gate + evidence audit + report quality gate. | `quality_gate.json` and `final_report.md` when approved. |

## Unified CLI

`kw.py` is a thin product wrapper around the existing scripts. It does not replace the three skills; it makes the first-run path easier.

```powershell
python .\kw.py doctor
python .\kw.py demo
python .\kw.py preflight --input .\examples\demo_transcript\input.txt --mode audit
python .\kw.py run --input .\examples\demo_transcript\input.txt --mode audit --language en --final-language en
python .\kw.py status --project-root .\outputs\knowledge-workflow\demo-transcript
python .\kw.py result --project-root .\outputs\knowledge-workflow\demo-transcript
python .\kw.py export --project-root .\outputs\knowledge-workflow\demo-transcript --format md
python .\kw.py quality --project-root .\outputs\knowledge-workflow\demo-transcript
python .\kw.py template --project-root .\outputs\knowledge-workflow\demo-transcript --template research_brief
python .\kw.py batch --input .\examples\batch_research\batch_links.csv --output-root .\outputs\knowledge-workflow\batch-demo
```

For Codex usage, you can still ask the agent directly:

```text
Use knowledge-workflow-console for this input.
Run preflight first. If first-hand material is available, create the video analysis pack and final report.
If primary material is unavailable, do not write a complete analysis. Write the degraded status and tell me what material is needed next.
```

## Supported Inputs

| Input | Stability | Notes |
| --- | --- | --- |
| Local transcript (`.txt`, `.md`, `.jsonl`, `.json`) | High | Best first-run path. |
| Local subtitles (`.srt`, `.vtt`) | High | Preserves timestamped source spans when available. |
| Local audio/video (`.mp3`, `.mp4`, `.m4a`, `.webm`, `.wav`, `.mov`, `.opus`) | Medium-high | Requires working ASR dependencies for real transcription. |
| YouTube public URL | Medium-high | Works best when subtitles or downloadable audio are available. Cookies may be needed. |
| X / Xiaohongshu / Douyin URLs | Low to medium | Often blocked or degraded. Prefer user-provided subtitles, audio, video, or transcript. |
| Private/paywalled/CAPTCHA/region/account-gated pages | Not a bypass target | The workflow may record blocked status, but it will not circumvent access controls. |

## What Success Produces

```text
outputs/knowledge-workflow/<project>/
  result_index.md
  logs/
    preflight.json
    run_state.json
    status_summary.json
    result_index.json
  10_video/
    00_source/source_status.json
    01_transcript/clean_transcript.jsonl
    05_gap_check/evidence_audit.json
    video_analysis_pack.md
  20_document/
    claim_map.json
    quality_gate.json
    final_report.md
  30_final/
```

Start with `result_index.md`. It is the user-facing entry point for every run.

## What Happens When It Fails

The workflow should not fake a complete report. If it cannot get first-hand material, it writes a degraded or blocked result that explains:

- the source status,
- whether full analysis is allowed,
- which route failed,
- what you can provide next: transcript, subtitles, local audio/video, or an authorized cookies file.

## Skill Package

The released package contains three skills:

- `knowledge-workflow-console`: route selection, preflight, end-to-end runner, status summaries, result index.
- `knowledge-video-decomposer`: source gates, acquisition checks, transcript normalization, ASR, segmentation, inventory, source logic, evidence audit, video analysis pack.
- `knowledge-document-composer`: document planning, Source / Inference / Extension separation, final report writer, quality gate.

`subagent-supervisor` is not part of this release package. It may be used locally as an optional coordination layer only when explicitly requested.

## Direct Script Entrypoints

The CLI wraps these scripts, but advanced users can still call them directly:

```powershell
python .\skills\knowledge-video-decomposer\scripts\doctor.py --self-test
python .\skills\knowledge-workflow-console\scripts\workflow_preflight.py --self-test
python .\skills\knowledge-workflow-console\scripts\end_to_end_runner.py --self-test
python .\skills\knowledge-workflow-console\scripts\workflow_status_summary.py --self-test
python .\skills\knowledge-workflow-console\scripts\result_index_writer.py --self-test
python .\skills\knowledge-document-composer\scripts\final_report_writer.py --self-test
```

## Tests

Default tests are offline and fixture-based:

```powershell
python .\tests\knowledge_workflow_regression.py
python .\tests\live_platform_smoke.py
python .\tests\asr_integration.py
python .\tests\real_workflow_acceptance.py
```

Optional live platform and real ASR tests require explicit environment variables and user-provided samples:

```powershell
$env:KW_LIVE_PLATFORM_SMOKE='1'
$env:KW_REAL_ASR_SMOKE='1'
```

## Current Status

Beta. The local transcript/subtitle path is the strongest route. Local media ASR is usable when dependencies are installed. Platform URL handling is intentionally conservative and may stop at degraded status when first-hand material is unavailable.

Current product entry work includes quickstart, examples, result indexing, unified CLI, security/privacy docs, batch research, output templates, Chrome probe normalization, and validation matrices.

## More Documentation

- [Quickstart](QUICKSTART.md)
- [中文说明](README.zh-CN.md)
- [User manual](USER_MANUAL.md)
- [Supported platforms](SUPPORTED_PLATFORMS.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Security](SECURITY.md)
- [Privacy](PRIVACY.md)
- [Architecture](docs/architecture.md)
- [Chrome probe integration](docs/chrome-probe-integration.md)
- [Validation matrix](docs/validation.md)
- [Release notes](RELEASE_NOTES.md)
