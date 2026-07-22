# Provider-Neutral External Handoff

An external CLI, API, browser, or user export may supply a channel for which
this repository has no bespoke `kw acquire` adapter.

1. Run `kw source matrix` and inspect the current provider state.
2. For `native_adapter`, use `kw acquire` when the operation is supported.
3. Otherwise, use an authorized external provider and save only task-primary
   text, subtitle, audio, or video to a local file.
4. Import that artifact with `kw source import`; provide the original URL,
   canonical platform id, target, operation, and a real browser host when the
   native route used OpenCLI.
5. Continue only from the promoted Bundle v2 manifest. Never give raw native
   JSON, YAML, search results, screenshots, or page metadata directly to the
   evidence or composer layers.

Example:

```powershell
kw source import `
  --input-file .\exports\reddit-primary.txt `
  --source-url <reddit-post-url> `
  --platform reddit `
  --target social_post `
  --operation read `
  --browser-host edge `
  --credentialed-session `
  --project-root <project>
```

Read `provider-routing.md` for the supported structured routes and their
source-gate boundaries.
