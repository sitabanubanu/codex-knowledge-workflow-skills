# Full Upstream Handoff

Agent-Reach owns all 15 native channels. Do not label a channel unsupported
only because this repository has no bespoke `kw acquire` adapter for it.

1. Run `python kw.py agent-reach matrix` and inspect the current doctor state.
2. For `structured_adapter`, use `kw acquire` when the operation is supported.
3. For `native_export_import`, follow the current native command in the
   installed `$agent-reach` skill, then save only task-primary text, subtitle,
   or media to a local file.
4. Import that artifact with `kw agent-reach import`; provide the original URL,
   canonical platform id, target, operation, and a real browser host when the
   native route used OpenCLI.
5. Continue only from the promoted Bundle v2 manifest. Never give raw native
   JSON, YAML, search results, screenshots, or page metadata directly to the
   evidence or composer layers.

Example:

```powershell
python kw.py agent-reach import `
  --input-file .\exports\reddit-primary.txt `
  --source-url <reddit-post-url> `
  --platform reddit `
  --target social_post `
  --operation read `
  --browser-host edge `
  --credentialed-session `
  --project-root <project>
```

Read `docs/agent-reach-integration-guide.md` in the repository for the full
channel map, setup details, and source-gate boundaries.
