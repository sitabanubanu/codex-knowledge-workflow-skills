# Routing

## Four-Layer Route

```text
knowledge-workflow-console
  -> agent-reach-console
  -> source-gated-evidence-layer
  -> knowledge-document-composer
```

`knowledge-video-decomposer` is an internal script library used by the evidence
layer. Do not route users to it as an alternative workflow.

## Select the Task Target

| Input/task | Target | Operation |
| --- | --- | --- |
| YouTube/Bilibili/local media content | `video_content` | `extract_transcript` |
| X/Xiaohongshu post body | `social_post` | `read` |
| Ordinary web article | `web_article` | `read` |
| GitHub repository document | `repository` | `read` |
| Open-web query | `search_triage` | `search` |

Ask or infer the target from the requested analysis, not only the URL host. A
social post containing a video is ambiguous: post analysis and video analysis
require different scopes.

## Modes

- `quick`: preflight only; no evidence or final-report claim.
- `standard`: acquire, gate, and audit when allowed; final writing is optional.
- `audit`: acquire, gate, audit, compose, quality-check, and write a final
  report only when every receipt is current.

## URL and Query Route

1. Run preflight with a redacted input record.
2. Run Agent-Reach doctor.
3. Write a route plan for the selected target and operation.
4. Require backend health plus implemented operation support.
5. Create a staged Bundle v2 attempt and promote only after validation.
6. Ingest through the target/scope source gate.
7. Stop degraded when the matching primary scope is absent.
8. Continue to evidence and composer only with current receipts.

## Local Route

Local transcript, subtitle, audio, and video use the same Bundle v2 contract.
The local source fingerprint includes file content SHA-256. Audio/video remains
degraded until ASR produces a usable transcript bound into the gate receipt.

## Resume

Default to a new project root. `--resume` is valid only for the same source
fingerprint, target, and operation. A resume is a new attempt, not permission
to reuse output files. Old bundles and downstream outputs move to history.

## Browser and Chrome

Use OpenCLI only when Agent-Reach doctor reports it ready. A Codex Chrome
session can inspect or export authorized visible material, but the export must
become a bundle artifact. Browser metadata, screenshots, page shell, and login
state are not source evidence by themselves.

## Optional Independent Review

When the user explicitly asks for a subagent or independent verification,
`subagent-supervisor` may review route decisions or outputs. It does not replace
any workflow layer and must not approve evidence without the same receipts.

## Completion Summary

Always report:

- acquisition status;
- source status and target;
- full-analysis permission;
- gate/analysis/final provenance state;
- stale output presence;
- result index and next safe action.
