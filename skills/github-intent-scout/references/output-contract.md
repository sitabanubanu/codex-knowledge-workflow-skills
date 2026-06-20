# Output Contract

Use this reference when shaping final GitHub scout answers.

## Core Rule

Always include links to used sources. For each recommendation, explain the mechanism match in plain language and state what evidence was checked.

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

Remaining uncertainty:
...
```

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

