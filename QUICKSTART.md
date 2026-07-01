# Quickstart

This quickstart proves the core workflow with a local transcript. It avoids platform URLs, cookies, ASR setup, and browser state so the first run is predictable.

## 1. Install The Skills

From the repository root:

```powershell
.\sync_to_codex_skills.ps1 -DryRun
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly
```

`VERIFY OK` means the installed Codex skills match the repository copy.

## 2. Run The Demo

```powershell
python .\kw.py demo
```

The demo uses:

```text
examples/demo_transcript/input.txt
```

It writes output under:

```text
outputs/knowledge-workflow/demo-transcript/
```

## 3. Open The Result Index

Start here:

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

If the demo succeeds, the most important output is:

```text
outputs/knowledge-workflow/demo-transcript/20_document/final_report.md
```

If it does not succeed, `result_index.md` explains the source status, failure reason, and next action.

## 4. Try Your Own Transcript

```powershell
python .\kw.py run `
  --input C:\path\to\transcript.txt `
  --mode audit `
  --language en `
  --final-language en
```

For Chinese reports:

```powershell
python .\kw.py run `
  --input C:\path\to\transcript.txt `
  --mode audit `
  --language zh-CN `
  --final-language zh-CN
```

## 5. Try Platform URLs Later

Use preflight before running a platform URL:

```powershell
python .\kw.py preflight --input "https://www.youtube.com/watch?v=..." --mode audit
```

Platform URLs may need subtitles, local media, authorized cookies, or may stop at degraded status. That is expected behavior, not a fake-success failure.

## 6. Useful Commands

```powershell
python .\kw.py doctor
python .\kw.py status --project-root .\outputs\knowledge-workflow\demo-transcript
python .\kw.py result --project-root .\outputs\knowledge-workflow\demo-transcript
python .\kw.py export --project-root .\outputs\knowledge-workflow\demo-transcript --format md
```

## What To Check

- `result_index.md`: user-facing status and next action.
- `10_video/video_analysis_pack.md`: structured source decomposition.
- `20_document/quality_gate.json`: final report approval gate.
- `20_document/final_report.md`: final report.
