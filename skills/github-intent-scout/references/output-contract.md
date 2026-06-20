# Output Contract

Use this reference when shaping final GitHub scout answers.

## Core Rule

Always include links to used sources. For each recommendation, explain the mechanism match in plain language and state what evidence was checked.

## Output Modes

Search Depth controls internal work. Output Mode controls what is shown.

| Mode | Use When | Show |
|---|---|---|
| `compact` | Normal chat answer | Conclusion, 1-3 best candidates, minimal evidence, caveat, runtime status. |
| `dossier` | User asks for a fuller research report | Scout sections, more candidates, scorecard, claim checks, selected Project Notes. |
| `appendix` | User asks to audit, save, or hand off work | Full Project Notes, Claim Ledger, Execution Log, and handoff details. |

Deep search can still produce compact output. Do not print full Project Notes or Claim Ledgers in compact mode unless the user asks.

## Best Match Minimum Evidence

Every Best Match must show a minimal evidence chain:

```text
Evidence: Files checked: ...
Claim status: ...
Caveat: ...
Runtime status: ...
```

For compact output, this can be one line per candidate. For dossier output, expand it. For appendix output, include full Project Note and Claim Ledger rows.

Runtime status is mandatory for serious candidates. If no runtime test was performed, write:

```text
RuntimeUnverified: No install/run was requested or performed in this scout pass.
```

## Full GitHub Scout Dossier

For substantial searches, produce a `GitHub Scout Dossier` with these sections:

1. `Search Depth`: quick, standard, or deep, and why.
2. `Search Assumptions` or `Orientation Result`: what was assumed, or what the user confirmed after orientation.
3. `Intent Map`: target, assumptions, key interpretations, chosen branch.
4. `Answer Shape`: skill, plugin/MCP, library/CLI, platform, workflow, or composite toolchain.
5. `Search Rounds`: queries that worked, queries that drifted, pivots.
6. `Project Family Map`: origin, ports, descendants, parallel projects, and practical consequences.
7. `Best Matches`: direct and adaptable candidates with links and best use roles.
8. `Necessary Architecture Checks`: what implementation files were inspected and what they proved or failed to prove.
9. `Composite Recommendation`: when relevant, map core engine + adapter + method skill + parser/platform.
10. `Candidate Scorecard`: sub-scores, total score, portability label, workflow completeness, and adapter/upstream notes when relevant.
11. `Adoption Classification`: direct-use, light-adapt, component-use, reference-only, near-miss, or exclude.
12. `Claim Checks`: important README/docs claims compared with implementation evidence.
13. `Runtime Verification`: smoke test status, what was attempted, or why it was not attempted.
14. `Evidence Notes`: what was checked and support statuses for important claims.
15. `Near Misses And Exclusions`: projects that looked relevant but were not.
16. `Adoption Recommendation`: use today, adapt, use as component, combine, or build custom.
17. `Optional Handoff To Design Miner`: include only when it will help a later design-mining pass avoid duplicated discovery.
18. `Remaining Uncertainty`: what would need deeper verification.
19. `Execution Log`: references read, repo searches, code searches, candidates inspected, files checked, runtime tests, deviations.

## Conditional Sections

Include these only when triggered:

```text
Family Map:
| Project | Family role | Relationship evidence | Practical consequence |
|---|---|---|---|

Re-rank note:
A late candidate changed the ranking because ...

High-star wrong-category exclusions:
- Repo:
  Why excluded:

Design Miner Handoff:
- Target repo:
- Why hand off:
- Patterns to inspect:
- Weak or overstated claims:
- Remaining unknowns:
```

Compact output may limit family maps and high-star exclusions to 2-3 items. Do not force these sections when they do not apply.

## Compact Final Requirements

For small searches, keep the final answer compact but still include:

- Best matches.
- Answer shape: whether the result is a skill, plugin/MCP, library, platform, workflow, or toolchain.
- Why they fit.
- What evidence was checked.
- Whether claims were checked against implementation when relevant.
- Adoption class for each serious candidate.
- Runtime status when the user may actually adopt the project.
- Any important support status or caveat.
- What is uncertain.
- Search terms that worked.
- Short execution log when search was standard/deep.

## Compact Final Shape

```text
I found three categories:

1. Direct matches
2. Adaptable or underlying tools
3. Popular but wrong-category projects

Best next action:
...

Why I trust this:
...

Search terms that worked:
...

Execution Log:
- References/searches/runtime/deviations: ...

Remaining uncertainty:
...
```

## Execution Log

For `standard` and `deep` work, include a short execution log:

```text
Execution Log:
- References read:
- Repo searches:
- Code searches:
- Candidates inspected:
- Files checked:
- Runtime tests:
- Deviations:
```

In compact output, collapse this to one short line if needed.

## Deviation Notes

Deviation notes are transparency markers, not apologies. Use them when work is compressed or a gate takes a fallback path:

- `Deviation: Project Notes and Claim Ledger were summarized rather than fully printed to keep output compact.`
- `Deviation: Code search had low yield; candidate verification used repo file inspection instead.`
- `Deviation: Runtime status is RuntimeUnverified because no install/use was requested.`

## Red Flags To Keep Visible

- Results are all generic LLM frameworks when the user asked for installable skills/plugins.
- Results are all chat rooms or apps when the user asked for task/workflow tools.
- The search is going deep before task direction has been checked for a broad request.
- The final answer assumes a single answer shape when evidence points to a toolchain.
- Repo name matches but README lacks install, examples, commands, manifests, or source.
- Project claims match in README, but code has no adapters, tools, docs, releases, or tests.
- README claims broad format support, but implementation only detects formats or falls back to plaintext/generic handling.
- A host-specific port has weak adoption and no meaningful changes beyond path/branding edits.
- Stars are high but the project requires replacing the user's toolchain.
- Recommendation would require sending private data to an unknown service without a clear privacy story.

## High-Star Wrong-Category Exclusions

When a popular project appears but is not the right answer shape, briefly explain why it is not a Best Match.

Use when a high-star project is a generic framework, awesome list, collection, wrong host/tool class, or would require replacing the user's toolchain.

Do not treat high stars as negative. Explain why the project is not the best fit for this task.
