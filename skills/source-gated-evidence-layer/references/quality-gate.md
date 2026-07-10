# Quality Gate

`final_report.md` is allowed only when all conditions pass:

- `source_status` is `source_confirmed` or `source_partial`.
- Evidence audit has no blocking errors.
- `claim_map.json` contains accepted Source claims.
- The report separates Source / Inference / Extension.
- A partial source must produce a visible partial-scope report.

Blocked states:

- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`
- bundle `metadata_only`
- bundle `blocked`
- bundle `failed`
- bundle `unsupported`

Blocked states may produce degraded reports and result indexes, never normal
final reports.
