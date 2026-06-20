---
name: github-intent-scout
description: >-
  Use when the user asks to search GitHub or the web for repositories, skills,
  plugins, tools, frameworks, examples, or comparable projects, especially when
  the terms are ambiguous, high-star results may be misleading, or the user wants
  recommendations. Also use for Chinese requests such as "帮我在 GitHub 上找",
  "GitHub 上有没有", "去 GitHub 找", or "帮我找项目/skill/插件". This skill produces
  an evidence-backed GitHub Scout Dossier with intent map, research brief,
  query rounds, candidate ledger, project notes, architecture checks, claim
  checks, scorecard, adoption recommendations, and optional handoff notes for a
  separate design-mining workflow.
---

# GitHub Intent Scout

Use this skill to find the right GitHub projects, not merely popular projects.

Core rule: search for the user's intended mechanism and adoption path, not only
the user's literal words.

This is a scouting and adoption-recommendation skill. It may inspect
architecture, but only to the depth needed to decide whether a project is worth
using, adapting, using as a component, or excluding.

Architecture inspection is "验货": enough to verify the README, mechanism, and
adoption path, not enough to redesign the user's project.

Do not turn a normal scouting task into a full design-transfer study unless the
user explicitly asks for that.

## When To Use

Use when the user asks to:

- Find repos, examples, open-source tools, skills, plugins, MCP servers, agents,
  frameworks, libraries, or comparable projects.
- Compare GitHub projects and recommend what to use.
- Search for "latest", "current", "high-star", "best", "better", "mature",
  or otherwise current recommendations.
- Investigate whether a type of tool exists.
- Improve a skill/plugin/tool by learning from similar projects.

Do not use the full workflow for a trivial lookup where the user named one exact
repository and only needs its URL.

If the user asks for "latest", "current", "high-star", "recent", or
recommendations, browse GitHub/web before answering.

## Core Rules

1. Treat project names, descriptions, READMEs, and stars as leads, not proof.
2. Prefer mechanism fit and adoption path over popularity.
3. Detect answer shape before ranking candidates.
4. For skills, plugins, MCP servers, and agent workflows, use code search as a
   first-class discovery path when relevant.
5. Inspect evidence before recommending: README, docs, examples, manifests,
   scripts, entry points, releases, activity, and source files as needed.
6. When adoption matters, check README/docs claims against implementation or
   label them unverified.
7. Separate direct matches, adaptable matches, components, reference patterns,
   near misses, and exclusions.
8. State what was verified, what was inferred, and what remains uncertain.
9. Give the user an adoption answer: use today, light-adapt, use as component,
   combine into a toolchain, or exclude.
10. Do not turn scout output into design mining unless the user asks for design
    transfer.
11. If useful patterns appear but adoption is weak, prepare optional
    design-miner handoff material instead of bloating the scout answer.
12. Do not recommend serious candidates from README alone; use project notes and
    claim checks when relevant.

## Search Depth

Pick a search depth before starting. If the user explicitly asks to be thorough,
says "do not be lazy", asks for recommendations, or will make a meaningful
adoption decision, use `deep`. If the user asks a casual or narrow lookup, use
`quick`. Otherwise use `standard`.

| Mode | Use When | Search Rounds | Evidence Depth | Output |
|---|---|---:|---|---|
| `quick` | Exact or low-stakes lookup | 1-2 | README or primary manifest | Compact recommendation |
| `standard` | Normal recommendations or comparisons | 2-4 | README + docs/SKILL/manifest/examples where relevant | Short Scout Dossier |
| `deep` | High-stakes, private data, spending time/money, or "do not be lazy" | 4+ or until convergence | File evidence, source snippets, dependency checks, optional clone/smoke test | Full Scout Dossier |

Depth is a throttle, not a cage. If a `quick` search uncovers ambiguity or risk,
escalate to `standard`. If a `standard` search finds a strong direct match but
an important claim is easy to fake, escalate the evidence check for that
candidate only.

## Output Mode

Search Depth controls internal work. Output Mode controls what is shown.

- `compact`: normal chat answer with conclusions, key candidates, minimal evidence, caveats, and runtime status.
- `dossier`: fuller scout report with scorecard, claim checks, and more candidates.
- `appendix`: audit/save mode with full Project Notes, Claim Ledger, Execution Log, and handoff details when needed.

Default to `compact` unless the user asks for a full report or audit trail. Deep searches can still use compact output.

## Navigation

Read references only when needed. The main file keeps the route; references keep
the depth.

- `references/intent-calibration.md`: read when broad terms or task ambiguity matter, especially overloaded words such as `agent`.
- `references/research-brief.md`: read before standard/deep search or when adoption decision, branch choice, or must-verify facts are unclear.
- `references/answer-shape-routing.md`: read before ranking candidates or when the best answer might be a skill, plugin/MCP, library/CLI, platform, workflow, or toolchain.
- `references/query-families.md`: read before query planning, literal fallback, or code-search vocabulary design.
- `references/github-search-syntax.md`: read when using GitHub search qualifiers, `gh` CLI patterns, or precise repo/code searches.
- `references/search-rounds.md`: read for standard/deep iterative searches, drift tracking, pivots, and stop conditions.
- `references/candidate-ledger.md`: read before classifying plausible candidates, assigning best use role, or labeling portability.
- `references/project-notes.md`: read before serious candidates enter scoring or recommendation.
- `references/project-family-map.md`: read when candidates share lineage, forks, host ports, wrappers, upstreams, or copied concepts.
- `references/architecture-check.md`: read when README-level evidence is not enough or a serious candidate may be installed/adapted.
- `references/project-evidence-strength.md`: read when judging evidence quality, support status, or authority order.
- `references/github-claim-ledger.md`: read before recommending serious candidates or checking README/docs claims against implementation.
- `references/github-conflict-resolution.md`: read when README, code, runtime, maintenance, stars, or upstream evidence conflicts.
- `references/scorecard.md`: read before comparing candidates with scores or weighted dimensions.
- `references/adoption-classification.md`: read before final adoption recommendation.
- `references/runtime-smoke-test.md`: read when runtime behavior may decide the recommendation or the user wants to install/use a project now.
- `references/design-miner-handoff.md`: read when scout findings should hand off to design mining.
- `references/output-contract.md`: read before final answer, especially for a full GitHub Scout Dossier.

Do not use a reference file as a black box. Load the files named by the relevant
phase or gate and apply their tables, templates, and checklists.

## Workflow

Follow these phases in order. Keep lightweight tasks lightweight, but do not skip
mandatory gates when the recommendation depends on them.

### Phase 1: Intent Map

Restate the user's target in one sentence.

Identify whether the user's words are overloaded across ecosystems. Include 2-5
plausible interpretations when ambiguity matters, then pick the primary branch
and say why.

Search adjacent branches when the wrong branch would be costly.

If broad terms or ambiguous agent/tool language matter, read:

- `references/intent-calibration.md`
- `references/research-brief.md`

Ask a clarifying question only when likely branches are materially different and
a reasonable assumption would waste substantial work. Otherwise state the
assumption and search multiple branches.

### Phase 2: Research Brief

Define the user's adoption or comparison decision before deep searching.

Capture:

- Primary branch.
- Adjacent branches worth checking.
- Out-of-scope branches.
- Must-verify facts.
- Risk boundary: privacy, cost, runtime, host, license, or maintenance.

For `standard` or `deep` tasks, or when adoption decision is unclear, read:

- `references/research-brief.md`

Use orientation before deep search when branch choice materially changes the
recommendation.

### Phase 3: Answer Shape Routing

Classify the likely answer shape before ranking candidates:

- `skill`
- `plugin-mcp`
- `library-cli`
- `platform`
- `workflow`
- `composite-toolchain`

Read:

- `references/answer-shape-routing.md`

Do not force a final answer to be a skill/plugin if the best solution is a
library, platform, workflow, or toolchain. Explain the shape mismatch plainly.

### Phase 4: Query Families And Search Rounds

Generate multiple query families instead of one heroic query: literal terms, mechanism terms, ecosystem terms, implementation evidence terms, and negative/exclusion terms when drift appears.

Evidence terms include `SKILL.md`, `.codex-plugin/plugin.json`, `.claude/skills`, `mcpServers`, `pyproject.toml`, `examples`, `scripts`, `Dockerfile`, commands, adapters, parsers, and API names.

Read:

- `references/query-families.md`
- `references/github-search-syntax.md`
- `references/search-rounds.md`

For skills, plugins, MCP servers, and agent workflows, run at least one
code-search round unless GitHub code search is unavailable.

Use multiple sort and discovery modes when useful: relevance, stars, updated
date, and code search. If literal searches are empty or noisy, pivot to domain,
mechanism, entry-point, known-upstream, or host terms.

Record useful pivots. Stop when direct matches are verified enough, adjacent
matches prove no mature direct match exists, searches repeat the same candidates,
or remaining uncertainty is better resolved by user constraints.

### Phase 5: Candidate Ledger

Collect plausible candidates before scoring:

| Candidate | Category | Stars | Updated | Host/format | Best use role | Evidence checked | Fit notes |
|---|---|---:|---|---|---|---|---|

Classify candidates as:

- `Direct`
- `Adaptable`
- `UnderlyingTool`
- `ReferencePattern`
- `NearMiss`
- `Excluded`

Assign best use role and portability so the user knows what each candidate is
for. Treat ecosystem mismatch as an adoption note unless the user requires a
specific host.

Read:

- `references/candidate-ledger.md`
- `references/project-notes.md` for serious candidates

Do not recommend a skill/plugin from name or description alone. Verify the
actual mechanism or clearly label it as inferred.

### Phase 6: Architecture And Evidence Check

For serious candidates, inspect enough implementation to verify adoption fit.
This is not full design mining.

Use architecture checks when:

- README claims a capability that is easy to fake or overstate.
- The user may install, run, or adapt the project.
- The candidate is a skill, plugin, MCP server, parser, adapter, agent workflow, or document/data analysis tool.
- Stars, descriptions, or polished README prose are the main evidence so far.

Read:

- `references/architecture-check.md`
- `references/project-evidence-strength.md`

Check real entry points, manifests, examples, key source files, setup
requirements, and data boundaries as appropriate for the answer shape.

Use support labels such as `Supported`, `PartiallySupported`,
`ReasonableInference`, `Ambiguous`, `Overstated`, `Unsupported`,
`StaleOrSuperseded`, `Unverified`, and `Opinion` when evidence quality matters.

### Phase 7: Claim Checks And Conflict Resolution

When a project claim affects adoption, compare the claim against implementation
or mark it unverified.

Check claims about:

- Supported file formats or import sources.
- Install path, trigger command, or manifest compatibility.
- Parser/adapter coverage.
- Local/private processing versus cloud/API processing.
- Persistence, memory, update, correction, or versioning.
- Benchmarks, tests, examples, demos, or production-readiness.

Read:

- `references/github-claim-ledger.md`
- `references/github-conflict-resolution.md` when evidence conflicts

If README and code conflict, prefer code. If runtime and promotional docs
conflict, prefer runtime. If a wrapper and upstream differ in quality, discuss
them separately.

### Phase 8: Scorecard And Adoption Class

Score candidates against the user's actual need, not search popularity.

For `quick`, 0-2 scoring is enough. For `standard` and `deep`, use 0-5
sub-scores and show the dimensions for recommended candidates.

Read:

- `references/scorecard.md`
- `references/adoption-classification.md`

Classify serious candidates as:

- `direct-use`
- `light-adapt`
- `component-use`
- `reference-only`
- `near-miss`
- `exclude`

Keep adoption class separate from best use role. If no candidate reaches
`direct-use` or `light-adapt`, say that plainly.

### Phase 9: Runtime Gate

Do not run every candidate by default.

Escalate to a minimal task-shaped smoke test when the user wants to install/use
a project now, runtime behavior is uncertain, claims are easy to fake, or top
candidates are close and runtime is the deciding factor.

Read:

- `references/runtime-smoke-test.md`

Avoid private data, expensive setup, destructive operations, and unapproved API
use. If credentials, paid APIs, GPU, large models, unavailable services, OS
mismatch, or heavy dependencies block the test, do not fake success.

Report runtime status separately:

- `SmokeTested`
- `PartiallySmokeTested`
- `RuntimeBlocked`
- `RuntimeUnverified`
- `RuntimeFailed`

### Phase 10: Recommendation And Optional Handoff

Produce an adoption recommendation, not only a ranking.

Explain:

- Best matches.
- Answer shape.
- Why the mechanism fits.
- What evidence was checked.
- Claim status and caveats when relevant.
- Adoption class.
- Runtime status when relevant.
- Execution log summary for standard/deep work.
- Remaining uncertainty.
- Search terms or query families that worked.

Read:

- `references/output-contract.md`
- `references/design-miner-handoff.md` only when handoff is useful

Include design-miner handoff only when it will prevent duplicated search work or
when candidates are not directly usable but contain useful design ideas.
When the user asks to learn from projects, improve their own skill/plugin/tool, or hand off to design miner, include a brief handoff by default instead of doing full design mining here.

## Mandatory Gates

### Direction Gate

If the user's wording is broad and branch choice changes the result, do an
orientation run or research brief before deep search.

### Answer Shape Gate

Do not rank candidates before classifying answer shape.

### Code Search Gate

For skills, plugins, MCP servers, and agent workflows, run at least one
code-search round unless unavailable. If unavailable, say so.

### Architecture Gate

For serious candidates, inspect entry points, manifests, examples, or key source
files before recommending.

### Claim Gate

If a README/docs claim affects adoption, check it against implementation or mark
it unverified.

### Conflict Gate

When README, code, runtime, maintenance, popularity, wrapper, or upstream
evidence conflicts, resolve the conflict explicitly.

### Runtime Gate

If the user wants to actually use/install now and runtime behavior is uncertain,
attempt a minimal smoke test or explicitly mark runtime status.

### Handoff Gate

If candidates are not directly usable but contain useful design ideas, prepare
optional design-miner handoff material instead of expanding the scout output
into a migration plan.

### Family Map Gate

If candidates share upstreams, forks, wrappers, host ports, or near-identical names/READMEs, show a short family map before ranking.

### Late Candidate Re-rank Gate

If a late candidate changes answer shape, mechanism fit, or adoption class, revisit earlier rankings before final recommendation.

## Red Flags

Treat these as search drift or recommendation risk:

- High stars but wrong answer category.
- Broad request searched deeply before direction check.
- Repo name matches but README lacks install, examples, commands, manifests, or source.
- Claimed plugin/MCP has no manifest, server entry point, tool definition, or connector setup.
- README claims broad format/support coverage, but implementation only detects formats or falls back to plaintext/generic handling.
- Project claims match in README, but code has no adapters, tools, docs, releases, or tests.
- Host-specific port is weak while upstream is strong; separate adapter risk from upstream value.
- Several repos copy the same concept across forks or hosts without clear lineage.
- Project is archived, stale, or depends on unavailable services.
- Recommendation would send private data to an unknown service without a clear privacy story.
- Results are all generic LLM frameworks when the user asked for installable skills/plugins or file/terminal tools.
- High-star projects can be wrong-category for the current task; explain exclusion without treating popularity as a negative.
- Scout output drifts from "should the user use this project?" into "how should the user's project be redesigned?" without the user asking for design mining.

When drift appears, pivot vocabulary and say why.

## Output

For small searches, keep the final answer compact but still include:

- Best matches.
- Answer shape.
- Why they fit.
- What evidence was checked.
- Adoption class for serious candidates.
- Runtime status when the user may adopt a project.
- Important caveats and support status.
- Remaining uncertainty.
- Search terms that worked.

For substantial searches, produce a `GitHub Scout Dossier` using
`references/output-contract.md`. Do not copy the full dossier template into this
main file.

Always include links to used sources. For each recommendation, explain the
mechanism match in plain language.

For detailed tables, templates, and checklists, load only the reference files
named by the relevant phase or gate.
