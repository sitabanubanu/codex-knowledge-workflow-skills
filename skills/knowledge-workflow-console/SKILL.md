---
name: knowledge-workflow-console
description: Start here for end-to-end source-gated knowledge work from URLs, queries, transcripts, subtitles, media, web articles, social posts, and repositories. Select target and operation, route the four workflow skills, and report provenance-aware status; do not acquire or write claims directly.
---

# Knowledge Workflow Console

Use this skill as the product controller.

1. Classify the input and state the intended `analysis_target` before work.
2. Resolve the required acquisition `operation`.
3. Run preflight for live URLs, media, or unclear expectations.
4. Route URL/query acquisition to `agent-reach-console`; local files use the
   same Bundle v2 contract through the local builder.
5. Route the promoted manifest to `source-gated-evidence-layer`.
6. Continue to `knowledge-document-composer` only when the current gate and
   analysis receipts allow it.
7. Treat `knowledge-video-decomposer` as an internal script library, never as
   a competing user-facing route.
8. Use a new project root by default. Reuse requires `--resume` and an exact
   source, target, and operation match.
9. Finish with provenance-aware status and result index. Report stale output
   files separately from current deliverables.

Chrome/OpenCLI may supply authorized visible artifacts, but browser state does
not bypass Bundle v2 or the source gate. Metadata, snippets, screenshots,
comments, and captions must not be silently promoted to another content scope.

Primary command:

```powershell
python kw.py run --input <url-or-file> --target <target> --operation <operation> --mode audit
```

Use explicit stages when diagnosing:

```powershell
python kw.py acquire ...
python kw.py ingest ...
python kw.py audit ...
python kw.py compose ...
python kw.py status --project-root <project>
python kw.py result --project-root <project>
```

Read `references/routing.md`, `references/stage-contracts.md`, and
`references/output-layout.md` before changing routing or handoff behavior.
