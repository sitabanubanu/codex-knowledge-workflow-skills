# Search Rounds

Use this reference to keep GitHub discovery iterative and auditable.

## Contents

- Core Rule
- Validation Mode
- Round Log
- Stop Conditions
- Late Candidate Re-rank
- Drift Handling
- Search Failure Fallback
- Blocked Step
- Visible Summary

## Core Rule

Search in rounds. After each round, record what the results taught, what drifted, and what query should come next.

Before the first real search, state one short execution line:

```text
Search Depth: quick/standard/deep. Output Mode: compact/dossier/appendix. Reason: ...
```

Choose automatically. Ask the user only when branches are unclear enough to materially change the search.

Search depth controls internal checking; output mode controls how much is shown. A deep search may still end with compact output.

## Validation Mode

Use validation mode when the user is testing, replaying, comparing, auditing, or reviewing this skill's own behavior, not when they simply want projects.

- Default to `deep`.
- Use `compact` for "result + evaluation".
- Use `dossier` for explicit audit, strict replay, or comparison report.
- Do not use `appendix` unless the user asks to save or expand all details.

Validation mode must summarize: search depth, output mode, references read, search failures, recovery used, deviations, runtime status, evidence level, remaining risks, and whether behavior followed the skill.

## Round Log

| Round | Query family | What surfaced | Drift/dead ends | Next pivot |
|---|---|---|---|---|
| 1 | Literal |  |  |  |
| 2 | Mechanism |  |  |  |
| 3 | Evidence/code |  |  |  |

After each round, record:

- `learnings`: what the results taught about the ecosystem.
- `dead_ends`: terms that produced misleading results.
- `follow_up_queries`: more specific queries to try next.

## Stop Conditions

Stop when the selected depth has enough evidence. Stop rules prevent over-search; they are not time or token budgets.

`quick` may stop when:

- 2-3 clearly relevant candidates are found.
- 1 strong match plus 1-2 alternatives are found.
- No direct match appears, but a reasonable adjacent direction is identified.

Quick does not need full Project Notes, Claim Ledger, or Full Dossier.

`standard` may stop when:

- About 5 candidates are found.
- The top 2-3 serious candidates have file-level evidence checks.
- The recommendation and high-star wrong-category exclusions can be explained.
- Runtime status is explicit: actual status or `RuntimeUnverified`.

`deep` may stop when:

- Candidate families are classified.
- Main serious candidates have Project Notes and Claim Ledger checks.
- Late candidate re-rank has been handled when triggered.
- Wrong-category exclusions are recorded when relevant.
- Design Miner Handoff is included only when useful.

Also stop when searches repeat the same candidates or remaining uncertainty is better resolved by user constraints.

## Late Candidate Re-rank

If a late candidate changes answer shape, mechanism fit, or adoption class, revisit earlier rankings before final recommendation.

Trigger this when:

- A later candidate fits the mechanism better than the current Best Match.
- A later candidate changes the answer shape, such as from workflow to direct tool.
- A later candidate is an official upstream, migration tool, or host-native option.
- Evidence shows the current Best Match is only `component-use` or `reference-only`.

If re-ranking happens, include: `Re-rank note: A late candidate changed the ranking because ...`

## Drift Handling

When drift appears, pivot vocabulary rather than adding more words to the same query family.

Examples:

- If `agent` returns model-role frameworks, pivot to `coding agent`, `worktree`, `terminal agent`, `CLI agent`.
- If `document analysis` returns SaaS apps, pivot to `parser`, `RAG`, `citation`, `chunking`, `OCR`, `local`.
- If repo search misses skills/plugins, pivot to code search for `SKILL.md`, manifests, commands, or supported formats.
- If code search is low-yield, record it and fall back to smaller evidence terms, repo search, and candidate file-tree inspection.

Repo search or web search can discover candidates. Repository file inspection is the main evidence source. Code search is a horizontal discovery and supplemental verification tool; low-yield code search does not lower candidate value by itself.

## Search Failure Fallback

Use the shortest recovery path that preserves evidence quality:

| Failure Type | Recovery |
|---|---|
| code search empty | Split terms, use repo search, inspect file trees. |
| API rate limit | Reduce candidate set, use opened sources, mark unverified gaps. |
| `gh` auth unavailable | Use web search, GitHub web/browser, or raw URL fallback. |
| README encoding failure | Use raw file, GitHub page, API contents, or alternate file view. |
| raw file unavailable | Use GitHub page, repo tree, or package metadata. |
| path 404 | Check branch, repo tree, renamed paths, and README claims; mark conflict if unresolved. |
| package registry missing | Mark install source `unknown` or `GitHub only`. |

Do not conclude "no project exists" from empty code search alone. After fallback, record evidence lost or confidence impact when it matters.

## Blocked Step

Only output this block when a real stall, skip, reroute, or degraded check happened:

```text
Blocked Step:
Cause:
Recovery Used:
Did Recovery Follow Skill:
Evidence Lost:
Confidence Impact:
```

## Visible Summary

For substantial searches, include the useful parts of the round log in the final dossier. For compact answers, include only search terms that worked and any important failed direction.

Track enough for an execution log: references read, repo searches, code searches, candidates inspected, files checked, runtime tests, and deviations.
