# Contributing

Contributions should preserve the project's core contract: no complete video
analysis without first-hand material.

## Development Flow

1. Run the local demo first.
2. Make a focused change.
3. Run the relevant self-test or regression suite.
4. Do not commit generated outputs, cookies, private media, or local secrets.

## Useful Commands

```powershell
python .\kw.py demo
python .\tests\knowledge_workflow_regression.py
python .\tests\real_workflow_acceptance.py
.\sync_to_codex_skills.ps1 -VerifyOnly
```

## Source Gate Rules

Do not weaken:

- `source_confirmed`
- `source_partial`
- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`

If a route has only metadata, screenshots, search snippets, or third-party
summaries, it must not produce a complete `video_analysis_pack.md`.

## Pull Requests

Good PRs include:

- a clear user problem,
- files changed,
- validation run,
- any source gate or output contract impact,
- screenshots or sample output when changing docs or product entrypoints.
