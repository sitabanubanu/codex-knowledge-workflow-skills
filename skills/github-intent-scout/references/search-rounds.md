# Search Rounds

Use this reference to keep GitHub discovery iterative and auditable.

## Core Rule

Search in rounds. After each round, record what the results taught, what drifted, and what query should come next.

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

Stop when at least one condition is true:

- Direct matches are verified enough to recommend.
- Adjacent matches prove there is no direct mature match.
- Additional searches are repeating the same candidates.
- Remaining uncertainty is better resolved by user constraints.

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

## Visible Summary

For substantial searches, include the useful parts of the round log in the final dossier. For compact answers, include only search terms that worked and any important failed direction.

Track enough for an execution log: references read, repo searches, code searches, candidates inspected, files checked, runtime tests, and deviations.
