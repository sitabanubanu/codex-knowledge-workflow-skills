# Architecture Decomposition Template

Use this template for each selected reference project. Keep it evidence-backed and concise.

## Project Card

| Field | Notes |
|---|---|
| Project | repo name and URL |
| Why selected | direct peer, adjacent pattern, component, mature platform, low-star POC, or counterexample |
| Evidence inspected | files, docs, manifests, examples, source modules |
| Confidence | high, medium, low |

## Decomposition

| Dimension | What To Capture |
|---|---|
| Problem solved | What user/job pain it addresses |
| Core mechanism | The actual working mechanism, not marketing |
| Entry points | CLI, API, skill trigger, app route, MCP tool, command |
| Input model | file types, data schema, user prompt, external services |
| Output model | reports, JSON, UI, generated files, database entries |
| Module boundaries | parser, router, analyzer, renderer, storage, validation |
| Intermediate artifacts | manifests, ledgers, chunks, indexes, temp tables, drafts |
| Control flow | step-by-step run path |
| Validation | tests, smoke tests, schema checks, claim checks, user confirmation |
| Failure handling | unsupported formats, missing fields, credentials, partial results |
| Data boundary | local vs cloud, privacy, credentials, destructive actions |
| Product delivery | install path, commands, exports, review flow, UI |
| What not to copy | project-specific assumptions or bad tradeoffs |

## Evidence Rules

- Prefer implementation files over README prose.
- Label claims as supported, partial, inferred, or unverified.
- If a project is valuable only as a pattern, say so.
- Do not confuse "popular" with "architecturally useful".

## Compact Output

```text
Project:
Why studied:
Mechanism:
Architecture:
Useful patterns:
Do not copy:
Evidence:
Uncertainty:
```
