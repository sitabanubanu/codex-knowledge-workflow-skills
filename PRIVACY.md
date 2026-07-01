# Privacy

Knowledge Workflow is designed as a local Codex workflow. It writes artifacts
to the project output directory you choose, usually:

```text
outputs/knowledge-workflow/<project-id>/
```

## What The Workflow May Read

Depending on the route, the workflow may read:

- local transcript or subtitle files,
- local audio or video files,
- platform metadata and public subtitle/audio information,
- user-exported cookies when explicitly provided,
- browser-observed page state when a Chrome probe is used.

## What The Workflow May Write

Outputs may include:

- normalized transcript files,
- ASR-derived transcript files,
- source status and acquisition notes,
- evidence maps and claim audits,
- final reports,
- result indexes,
- logs describing attempted routes and failure reasons.

Do not assume these outputs are anonymous. They can contain quotes, titles,
source URLs, timestamps, and derived claims.

## Local Versus External Processing

The repository scripts run locally. However, your surrounding Codex session,
browser tools, ASR setup, or model provider may involve external services
depending on how you invoke them. Before processing private material, confirm
which tools are active in your environment and whether they send data outside
your machine.

## Deleting Workflow Data

To remove a run, delete its project directory:

```powershell
Remove-Item -Recurse -Force .\outputs\knowledge-workflow\<project-id>
```

Only delete paths you have verified are inside the intended output directory.

## Private Or Restricted Material

For private videos, paid courses, account-only pages, or sensitive internal
recordings, prefer user-provided transcript or local media files that you are
allowed to process. Do not publish outputs unless the source owner permits it.

## Degraded Reports

When first-hand material is unavailable, the workflow may write a degraded
report based on visible page state or secondary context. Such reports should be
explicitly labeled and must not be presented as complete video analysis.
