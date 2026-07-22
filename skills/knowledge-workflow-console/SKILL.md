---
name: knowledge-workflow-console
description: Start here for end-to-end source-gated knowledge work from broad learning needs, URLs, queries, transcripts, subtitles, media, web articles, social posts, and repositories. Route optional web discovery through web-intent-scout, then acquisition and evidence, and finally a learning article or source-faithful document; report provenance-aware status and do not acquire or write claims directly.
---

# Knowledge Workflow Console

Use this skill as the product controller.

1. Classify whether the user needs source discovery, processing of an already
   selected source, or both.
2. For a broad open-web learning need, comparison, recommendation, or
   source-selection request, route discovery to `web-intent-scout`. Ask it for
   an intent map, source ledger, candidate shortlist, and selection rationale.
   Skip discovery when the user already supplied the source and did not ask to
   compare, verify, or find alternatives.
3. Treat Web Scout outputs as planning artifacts only. Select a URL or explicit
   query for acquisition; never promote snippets, scorecards, or dossier claims
   directly into source evidence.
4. State the intended `analysis_target` and resolve the required acquisition
   `operation` for the selected source.
5. Run preflight for live URLs, media, or unclear expectations.
6. Route URL/query acquisition to `agent-reach-console`; local files use the
   same Bundle v2 contract through the local builder.
7. When Agent-Reach has a ready native channel without a bespoke `kw acquire`
   adapter, use its native command to obtain task-primary material, then route
   the saved artifact through `kw agent-reach import`; never downgrade it to a
   generic web fallback.
8. Route the promoted manifest to `source-gated-evidence-layer`.
9. For a source-faithful report, continue to `knowledge-document-composer` only
   when the current gate and analysis receipts allow it. For personal learning,
   route the same current audited pack to `knowledge-learning-article` and
   require its learning quality gate and receipt before delivery.
10. Treat `knowledge-video-decomposer` as an internal script library, never as
   a competing user-facing route.
11. Use a new project root by default. Reuse requires `--resume` and an exact
   source, target, and operation match.
12. Finish with provenance-aware status and result index. Report discovery
    artifacts, source-faithful reports, and learning articles separately, and
    report stale output files separately from current deliverables.

Browser state may supply authorized visible artifacts, but it does not bypass
Bundle v2 or the source gate. Load `$browser-host-identity` whenever Chrome,
Edge, OpenCLI, cookies, an extension, or a browser export is involved. Record
the actual host, never infer it from a tool name, and never fall back from one
browser to the other. Metadata, snippets, screenshots, comments, and captions
must not be silently promoted to another content scope.

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
