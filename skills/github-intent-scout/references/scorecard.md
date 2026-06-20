# Scorecard

Use this reference to compare candidates against the user's actual need, not search popularity.

## Core Rule

Score from evidence. Do not use a high total score to hide weak mechanism fit, missing implementation evidence, or an unsuitable adoption path.

For serious candidates, score only after Project Notes and Claim Ledger exist. Do not score from raw README impressions, search snippets, or stars. Use the Claim Ledger to lower evidence strength, installability, maturity, portability, or adoption signal when required or important claims are weak, unresolved, or unverified.

## Quick Scorecard

Use 0-2 for `quick` searches:

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Mechanism fit | Different problem | Adjacent | Directly solves it |
| Evidence strength | Name/description only | README claim | Docs/code/examples confirm |
| Workflow completeness | Loose script or prompt only | Covers some adoption steps | Covers intake, run, verify, update, and recovery |
| Usability | Abandoned or unclear | Usable with caveats | Easy to try |
| Maturity | Toy/empty | Early | Active/community/proven |
| Installability | Unknown/heavy | Some setup/glue | Clear install path |
| Portability | Rewrite needed | Portable with edits | Native or mostly compatible |

## Standard/Deep Scorecard

Use 0-5 for `standard` and `deep` searches. Show sub-scores for every recommended candidate instead of only a final score.

Weighted score:

```text
total_score =
  mechanism_fit * 0.30 +
  evidence_strength * 0.20 +
  workflow_completeness * 0.10 +
  installability * 0.10 +
  maturity * 0.10 +
  maintenance * 0.10 +
  portability * 0.05 +
  adoption_signal * 0.05
```

`portability` is intentionally low-weight because a useful project can be moved across agent hosts. Increase it only when the user explicitly requires a specific host or marketplace.

## Workflow Completeness

For skills and plugins, score higher when the project covers:

- Intake questions.
- Source ingestion.
- Chunking or parsing.
- Analysis prompts.
- Evidence/citation handling.
- User confirmation.
- File writing.
- Updates/corrections.
- Rollback/versioning.
- Invocation instructions.

## Adapter Scoring

For adapters, optionally include:

- `upstream_strength`: maturity and fit of the wrapped project.
- `adapter_quality`: clarity and robustness of the wrapper itself.
- `adapter_risk`: low adoption, stale pins, unclear data flow, or fragile setup.

These do not replace the main score. They explain why a low-star adapter may still be worth using, or why a famous upstream is not enough.

## Optional Repository Signals

- `activity_score`: recent commits/releases, not archived, issue health.
- `quality_score`: README/docs, license, tests/examples, dependency clarity.
- `semantic_score`: how closely README/docs match the user's mechanism.
- `adoption_score`: stars/forks/downloads, treated as secondary.

Prefer a low-star exact mechanism over a famous wrong-category project, but label maturity risk clearly.
