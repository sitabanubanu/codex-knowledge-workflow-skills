# Routing

## Three-Part Product Route

```text
1. Discover and select sources (optional)
   web-intent-scout

2. Acquire, gate, and audit the selected source (required)
   knowledge-workflow-console
     -> agent-reach-console or local Bundle v2 builder
     -> source-gated-evidence-layer

3. Turn the audited pack into a learning deliverable (when requested)
   knowledge-learning-article
```

The first part is optional when the user already supplied the source. The
second part is never optional for a normal learning article. The third part is
selected only for personal learning; a source-faithful report uses the document
route below instead.

## Web Discovery Route

Use `web-intent-scout` before acquisition when the user starts with a broad
learning need, asks which sources are worth studying, or needs current web
sources compared or verified. Its handoff should identify:

- the interpreted learning or decision intent;
- serious candidate URLs and source types;
- freshness, credibility, conflict, and risk notes;
- the selected candidate and why it fits the request.

Store the dossier and selection under `logs/discovery/` when a project root is
being used. These are planning artifacts, not Source evidence. The selected URL
or explicit query must still pass normal acquisition, Bundle v2 validation,
target/scope gating, and evidence audit. Search snippets and comparison claims
must not enter the audited pack unless the corresponding source material is
separately acquired and admitted.

Skip Web Scout when the user supplied a local file, transcript, subtitle, or a
specific URL and did not ask to compare, verify, or find alternatives.

## Source-Faithful Route

```text
knowledge-workflow-console
  -> agent-reach-console
  -> source-gated-evidence-layer
  -> knowledge-document-composer
```

## Learning-Article Route

```text
knowledge-workflow-console
  -> agent-reach-console or local Bundle v2 builder
  -> source-gated-evidence-layer
  -> knowledge-learning-article
```

Use the learning route when the user asks what is worth learning, how concepts
connect, what prerequisites are required, how to study the material, or requests
a systematic learning article instead of a timestamp or source-audit report.
Both delivery routes consume the same current audited analysis pack. Neither
downstream skill may read un-gated acquisition or Web Scout artifacts directly.

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

After acquisition, treat `learning_article` as a downstream delivery operation,
not as a replacement for the platform acquisition operation recorded in Bundle v2.

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
8. Continue to evidence and the selected document/learning route only with current receipts.

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

- discovery status and selected source when Web Scout was used;
- acquisition status;
- source status and target;
- full-analysis permission;
- gate/analysis/final provenance state;
- stale output presence;
- result index and next safe action.
