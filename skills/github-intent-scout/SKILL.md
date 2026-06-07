---
name: github-intent-scout
description: >-
  Use when the user asks to search GitHub or the web for repositories, skills,
  plugins, tools, frameworks, examples, or comparable projects, especially when
  the terms are ambiguous, high-star results may be misleading, or the user wants
  recommendations. Also use for Chinese requests such as "帮我在 GitHub 上找",
  "GitHub 上有没有", "去 GitHub 找", or "帮我找项目/skill/插件". This skill produces
  an evidence-backed GitHub Scout Dossier: intent map, query rounds, candidate
  ledger, necessary architecture checks, evidence checks, scorecard, excluded
  projects, actionable recommendations, and optional handoff notes for a separate
  design-mining workflow.
---

# GitHub Intent Scout

Use this skill to find the right GitHub projects, not merely popular projects.

Core rule: search for the user's intended mechanism and adoption path, not only the user's literal words.

This is a scouting and adoption-recommendation skill. It may inspect architecture, but only to the depth needed to decide whether a project is worth using, adapting, using as a component, or excluding. Do not turn a normal scouting task into a full design-transfer study unless the user explicitly asks for that.

This skill is a lightweight investigation protocol inspired by:

- Deep-research agents: iterative breadth/depth search, learnings, and follow-up queries.
- GitHub research skills: staged discovery, filtering, deeper evidence checks, and resumable outputs.
- Repository recommendation agents: multi-factor ranking across relevance, quality, activity, and installability.
- Evidence-disciplined research skills: every nontrivial recommendation gets a support status and caveats.

## Search Depth

Pick a search depth before starting. If the user explicitly asks to be thorough, says "do not be lazy", asks for recommendations, or will make a meaningful adoption decision, use `deep`. If the user asks a casual or narrow lookup, use `quick`. Otherwise use `standard`.

| Mode | Use When | Search Rounds | Evidence Depth | Output |
|---|---|---:|---|---|
| `quick` | Exact or low-stakes lookup | 1-2 | README or primary manifest | Compact recommendation |
| `standard` | Normal recommendations or comparisons | 2-4 | README + docs/SKILL/manifest/examples where relevant | Short Scout Dossier |
| `deep` | High-stakes, private data, spending time/money, or "do not be lazy" | 4+ or until convergence | File evidence, source snippets, dependency checks, optional clone/smoke test | Full Scout Dossier |

Depth is a throttle, not a cage. If a `quick` search uncovers ambiguity or risk, escalate to `standard`. If a `standard` search finds a strong direct match but an important claim is easy to fake, escalate the evidence check for that candidate only.

## Search Rhythm

Use two stages when the task direction is broad or ambiguous:

1. `orientation run`: a fast map of possible answer shapes and task branches. Run 1-2 broad search rounds, give a rough category map, and ask up to 3 direction-setting questions.
2. `focused deep run`: after the user confirms the direction, run the full evidence-backed search with code search, family mapping, claim checks, scorecard, and adoption recommendation.

Skip the orientation run only when the user already gave a narrow target, named exact constraints, or explicitly asked you to proceed without questions. If skipping orientation for a broad request, state the assumptions before searching and name which branches are out of scope.

Orientation output is intentionally not a final ranking. It should help the user choose the right search branch before you spend depth on verification.

## When To Use

Use when the user asks to:

- Find repos, examples, open-source tools, skills, plugins, MCP servers, agents, frameworks, or libraries.
- Compare GitHub projects and recommend what to use.
- Search for "latest", "current", "high-star", "best", "better", or "mature" projects.
- Investigate whether a type of tool exists.
- Improve a skill/plugin by learning from similar projects.

Do not use the full workflow for a trivial lookup where the user named one exact repository and only needs its URL.

## Operating Principles

1. Treat project names, descriptions, and stars as leads, not proof.
2. Prefer exact mechanism fit over popularity.
3. Search in rounds, and pivot when results drift.
4. For skills, plugins, MCP servers, and agent workflows, treat code search as a first-class discovery path, not an optional refinement.
5. Inspect evidence before recommending: README, docs, examples, manifests, scripts, code entry points, releases, and activity signals as relevant.
6. Cross-check advertised capabilities against implementation when the project claims parsers, adapters, commands, architecture, or format support.
7. Separate direct matches, adaptable matches, underlying tools, references, near misses, and exclusions.
8. State what was verified, what was inferred, and what remains uncertain.
9. Detect the answer shape before ranking. The best answer may be a skill, plugin/MCP, library, platform, workflow, or composite toolchain.
10. Give the user an adoption answer: can they use it today, adapt it, use it as a component, combine it with other tools, or should they build a small custom version?
11. Use architecture inspection as "验货": enough to verify the README and adoption path, not enough to redesign the user's project.
12. When projects are not directly adoptable but contain useful design ideas, record them as handoff material instead of expanding the scout output into a full migration plan.

If the user asks for "latest", "current", "high-star", "recent", or recommendations, browse GitHub/web before answering.

## Workflow

### Phase 1: Intent Map

Restate the user's target in one sentence.

Build a compact intent table before searching:

| Term | Possible meaning | Signals | Search vocabulary |
|---|---|---|---|

Include 2-5 plausible interpretations. Pick the primary branch and say why. Search adjacent branches when the wrong branch would be costly.

Example for "agent":

- LLM role/prompt agent: `multi-agent framework`, `agent framework`, `CrewAI`, `AutoGen`.
- Tool/coding agent: `Claude Code`, `Codex CLI`, `coding agent`, `terminal agent`, `worktree`.
- Agent workflow/config: `AGENTS.md`, `CLAUDE.md`, `.codex/skills`, `.claude/skills`, `hooks`.
- Runtime/protocol agent: `MCP`, `A2A`, `agent protocol`, `agent runtime`.

Ask a clarifying question only when all likely branches are materially different and a reasonable assumption would waste substantial work. Otherwise state the assumption and search multiple branches.

See `references/intent-calibration.md` for more ambiguity patterns.

#### Task Direction Check

Before deep searching, explicitly check the task direction when the user's wording is broad. Common direction splits:

| Broad term | Direction questions |
|---|---|
| `document analysis` | Existing documents or generating new content? Single document or many documents? Q&A, extraction, summary, comparison, or formal review? |
| `research` | Literature discovery, analysis of an existing library, automatic paper generation, experiment workflow, or writing support? |
| `skill/plugin` | Must be installable in one host, or is a library/platform/MCP/workflow acceptable? |
| `chat/history/memory` | Personal self-analysis, relationship analysis, workplace memory, or generic conversation statistics? |
| `agent` | Prompt/workflow agent, coding agent, MCP tool, runtime protocol, or multi-agent framework? |

If the branch choice materially changes the recommendation, do an orientation run first and ask up to 3 questions. Prefer questions that determine:

- Existing material analysis vs. new content generation.
- Q&A/retrieval vs. structured synthesis/reporting.
- Single-file vs. multi-file/corpus workflow.
- Local/privacy-first vs. cloud/API acceptable.
- Required host/tool vs. any agent ecosystem.

#### Answer Shape Detection

Classify the likely answer shape before ranking candidates:

| Shape | Use When | Example adoption answer |
|---|---|---|
| `skill` | The user wants agent instructions, reusable workflow, or host-native skill files. | Install or port the skill. |
| `plugin-mcp` | The user needs an agent-callable tool or connector. | Add the MCP/plugin and point it at data. |
| `library-cli` | The best implementation is a package or command-line tool. | Use it as the engine behind a small skill. |
| `platform` | The user needs a hosted/self-hosted app with UI, indexing, permissions, or knowledge bases. | Deploy/use the platform. |
| `workflow` | The main value is method, protocol, checklist, or analysis structure. | Use it as the agent's procedure. |
| `composite-toolchain` | No single project covers the need; several components fit together. | Combine engine + adapter + method skill + parser. |

Do not force the final answer to be a skill/plugin if the best solution is a library, platform, or toolchain. Explain the shape mismatch plainly.

#### Orientation Run

Use orientation when:

- The user's request has multiple strong branches.
- The literal terms are broad (`document`, `agent`, `research`, `memory`, `plugin`, `skill`).
- The user will likely spend time installing or adopting the result.
- Private/local data or high-stakes accuracy matters.
- Direct search terms are likely to collide with unrelated ecosystems.

Orientation procedure:

1. Run 1-2 broad searches across literal terms, mechanism terms, and evidence terms.
2. Report 2-5 candidate directions with 1-2 representative projects each.
3. Name likely wrong branches and why.
4. Ask up to 3 concise direction questions.
5. After the user answers, start the focused run.

If the user explicitly requests a full run without questions, use a `Search Assumptions` note instead of stopping:

```text
Search Assumptions:
- I will treat "document analysis" as multi-document research synthesis, not personal chat analysis.
- I will include libraries and MCP servers, not only host-native skills.
- I will prioritize local/private workflows where possible.
```

### Phase 2: Query Families

Generate at least three query families:

- Literal terms from the user.
- Mechanism terms describing how the thing works.
- Ecosystem terms naming likely tools, file formats, CLIs, manifests, protocols, or config files.
- Evidence terms that reveal real implementation, such as `SKILL.md`, `.codex-plugin/plugin.json`, `.claude/skills`, `mcpServers`, `pyproject.toml`, `examples`, `scripts`, `Dockerfile`, or API names.
- Negative or exclusion terms when common drift appears.

Use query families rather than one heroic query.

For GitHub repo discovery:

```text
<literal phrase> GitHub
<mechanism phrase> GitHub
<tool names> <mechanism> GitHub
site:github.com <tool names> <mechanism>
```

For `gh` CLI when available:

```powershell
gh search repos "<query>" --limit 20 --json fullName,description,stargazersCount,updatedAt,url
gh search repos "<query>" --sort stars --limit 20 --json fullName,description,stargazersCount,updatedAt,url
gh search repos "<query>" --sort updated --limit 20 --json fullName,description,stargazersCount,updatedAt,url
gh search code "<needle>" --limit 20 --json repository,path,url
```

For skill/plugin searches, run at least one code-search round unless GitHub code search is unavailable:

```powershell
gh search code "SKILL.md" "<mechanism term>" --limit 20 --json repository,path,url
gh search code "<command or trigger phrase>" --limit 20 --json repository,path,url
gh search code "<claimed format or adapter>" "<project family term>" --limit 20 --json repository,path,url
```

Good code-search needles include:

- Skill and plugin artifacts: `SKILL.md`, `skill.md`, `.codex-plugin/plugin.json`, `.claude/skills`, `mcpServers`.
- Agent workflow artifacts: `prompts/`, `tools/`, `commands`, `hooks`, `memory`, `persona`, `planner`, `router`.
- Claim-verification artifacts: parser names, import names, CLI flags, supported formats, API route names, dependency package names.

Use multiple sort orders:

- Default relevance: first map likely matches.
- `--sort stars`: mature or high-signal projects.
- `--sort updated`: emerging projects and new terminology.

Do not pass `--sort best-match` to `gh search repos`; default relevance is already best match in current `gh`.

See `references/github-search-syntax.md` for copied/paraphrased search syntax patterns.

#### Literal Search Fallback

If literal repo searches are empty or noisy, pivot automatically instead of declaring no result:

1. Domain terms: `systematic review`, `literature review`, `scientific papers`, `contracts`, `chat export`, `knowledge base`.
2. Mechanism terms: `RAG`, `vector search`, `citation`, `evidence synthesis`, `parser`, `chunking`, `OCR`, `index`.
3. Entry-point terms: `SKILL.md`, `mcpServers`, `pyproject.toml`, `Dockerfile`, `CLI`, `examples`, `prompts`, `tools`.
4. Known upstream tools: e.g. `PaperQA`, `GROBID`, `MarkItDown`, `Zotero`, `DocsGPT`, `LlamaIndex`, `LangChain`.
5. Host terms: `Claude skill`, `Codex skill`, `OpenClaw skill`, `MCP server`, `Cursor`, `OpenCode`, `AGENTS.md`.

Record the pivot in Search Rounds: what failed, what vocabulary replaced it, and what new candidates surfaced.

### Phase 3: Search Rounds

Search in rounds. Keep a private or visible search log depending on the task size:

| Round | Query family | What surfaced | Drift/dead ends | Next pivot |
|---|---|---|---|---|

After each round, record:

- `learnings`: what the results taught about the ecosystem.
- `dead_ends`: terms that produced misleading results.
- `follow_up_queries`: more specific queries to try next.

Stop when at least one of these is true:

- Direct matches are verified enough to recommend.
- Adjacent matches prove there is no direct mature match.
- Additional searches are repeating the same candidates.
- The remaining uncertainty is better resolved by user constraints.

### Phase 4: Candidate Ledger

For each plausible candidate, collect a compact ledger:

| Candidate | Category | Stars | Updated | Host/format | Best use role | Evidence checked | Fit notes |
|---|---|---:|---|---|---|---|---|

Recommended categories:

- `Direct`: same mechanism and directly usable in at least one agent/tool host.
- `Adaptable`: close mechanism, needs glue or conversion.
- `UnderlyingTool`: useful component, not a skill/plugin/workflow by itself.
- `ReferencePattern`: useful design pattern only.
- `NearMiss`: adjacent but likely not worth using.
- `Excluded`: misleading or unsuitable.

Treat agent host or ecosystem as an adoption note, not a core quality penalty, unless the user explicitly requires one host. A strong Claude/OpenClaw/Cursor skill may still be the best answer for a Codex user if the mechanism is right and porting is realistic.

Assign a `Best use role` so the user knows what to do with each candidate:

| Role | Meaning |
|---|---|
| `core-solution` | Best candidate to actually use as the main path. |
| `host-adapter` | Useful because it adapts a stronger upstream project to the user's agent host. |
| `supporting-component` | Useful for conversion, parsing, indexing, retrieval, or other sub-work. |
| `architecture-reference` | Useful design pattern, but not the main tool to install. |
| `inspiration-only` | Interesting idea; do not rely on implementation. |
| `exclude` | Do not use for this task. |

For composite recommendations, a candidate can be the best in its layer even if it is not the final answer by itself. Example layers:

- `core engine`: the strongest implementation of the main mechanism.
- `agent adapter`: MCP/plugin/skill wrapper around the engine.
- `method skill`: procedure for reading, screening, synthesis, or reporting.
- `parser/converter`: document ingestion, OCR, format conversion, metadata extraction.
- `knowledge platform`: persistent UI, indexing, team workflow, or private deployment.

Use a portability label instead of over-penalizing ecosystem mismatch:

| Portability | Meaning |
|---|---|
| `native` | Works directly in the user's requested host/tool. |
| `mostly-compatible` | Same skill/plugin style; minor path or command edits likely. |
| `portable-with-edits` | Mechanism is right but host assumptions need adaptation. |
| `component-only` | Useful parser/library/workflow, not an installable skill/plugin. |
| `rewrite-needed` | Only the idea transfers; implementation is not reusable. |

Evidence to check as relevant:

- README and docs.
- `SKILL.md`, `skill.md`, `.claude/skills`, `.codex/skills`.
- `.codex-plugin/plugin.json` or equivalent manifest.
- MCP server config, tools, connector setup, or API entry points.
- Examples, demos, screenshots, CLI commands, tests, releases.
- Dependency files and setup instructions.
- Recent commits, issue/release activity, archived status.
- Key source files when README claims need confirmation.

For skill/plugin requests, do not recommend from name/description alone. Verify the actual skill/plugin mechanism or clearly label it as inferred.

### Phase 4.2: Necessary Architecture Check

For serious candidates, inspect enough architecture to verify adoption fit. This is not a full design-mining pass; stop when you can responsibly recommend, reject, or mark the candidate unverified.

Use this check when:

- README claims a capability that is easy to fake or overstate.
- The user may actually install, run, or adapt the project.
- The candidate is a skill, plugin, MCP server, parser, adapter, agent workflow, or data/document analysis tool.
- Stars, descriptions, or AI-written README prose are the main evidence so far.

Minimum architecture evidence by project shape:

| Shape | Inspect At Least |
|---|---|
| `skill` | `SKILL.md`, prompt/reference files, bundled tools/scripts, examples if present |
| `plugin-mcp` | manifest/config, tool definitions, server entry point, setup instructions |
| `library-cli` | package metadata, CLI/API entry point, core parser/adapter module, example call |
| `platform` | ingest/index/query pipeline, deployment path, data boundary, auth/storage notes |
| `workflow` | procedure file, required inputs, intermediate artifacts, verification steps |
| `composite-toolchain` | role of each component and whether interfaces actually connect |

Ask these verification questions:

- What is the real entry point?
- What files or modules implement the advertised mechanism?
- Does it have parser/adapter/tool code, or only prompt/README prose?
- What intermediate artifacts are produced?
- What does it require from the user: credentials, host, runtime, model, database, local files?
- What parts are verified, partial, inferred, or unimplemented?

Stop conditions:

- `Recommend`: mechanism and adoption path are sufficiently supported.
- `Reject`: implementation evidence contradicts the claimed fit or adoption cost is unreasonable.
- `Component`: it solves a useful subproblem but is not the user's full answer.
- `ReferenceOnly`: it has design ideas but is not suitable to use.
- `Unverified`: evidence remains insufficient and runtime/deeper inspection is not justified yet.

Do not produce a migration map here. If the architecture reveals useful patterns for the user's own project, record them under `Handoff To Design Miner`.

### Phase 4.5: Project Family Map

When multiple candidates share a concept, naming pattern, README phrasing, architecture, or explicit acknowledgements, map the family before ranking:

| Project | Family role | Relationship evidence | Practical consequence |
|---|---|---|---|

Suggested family roles:

- `origin`: likely original or strongest upstream.
- `fork`: GitHub fork or direct copy.
- `host-port`: adaptation to another agent host, CLI, model, or runtime.
- `model-port`: same idea bound to a different model/provider.
- `architecture-descendant`: reuses the architecture in another domain.
- `parallel`: similar solution without clear lineage.
- `unrelated-name-match`: name or terms overlap but mechanism differs.

Use the family map to avoid double-counting the same idea. Prefer a mature upstream for trust, a host-port for installation clues, and architecture-descendants for design ideas. Do not let a low-star host-port outrank a stronger upstream solely because it names the user's host; mark it as `host-adapter` unless its implementation is independently stronger.

#### Adapter Upstream Strength

For low-star adapters, wrappers, MCP servers, or host ports, score the wrapper and upstream separately:

| Adapter Check | What To Ask |
|---|---|
| Upstream strength | Is the wrapped library/platform mature, maintained, licensed, documented, and fit for the mechanism? |
| Wrapper thinness | Is the adapter mostly configuration/glue, or does it add complex fragile behavior? |
| Interface clarity | Are commands, config, environment variables, indexing paths, and failure modes documented? |
| Version pinning | Does the adapter pin compatible upstream versions or explain supported ranges? |
| Data boundary | Does the adapter clearly state what data goes local, to APIs, or to external services? |

Do not reject a thin adapter only because it has few stars if it wraps a strong upstream and has clear setup. Label the adapter maturity risk separately from the upstream strength.

### Phase 5: Evidence Check

Assign one support status to each nontrivial recommendation claim:

| Status | Meaning |
|---|---|
| `Supported` | Checked evidence directly supports the claim. |
| `PartiallySupported` | Evidence supports part of the claim, with scope limits. |
| `ReasonableInference` | Evidence supports a cautious inference beyond direct observation. |
| `Ambiguous` | Credible evidence points in multiple directions. |
| `Overstated` | Project claims more than the evidence supports. |
| `Unsupported` | Checked evidence fails to support the claim. |
| `StaleOrSuperseded` | Newer evidence or project state changes the claim. |
| `Unverified` | Not enough evidence was checked. |
| `Opinion` | Judgment, preference, or recommendation. |

Use this authority order:

1. User constraints and current task needs.
2. Primary project artifacts: repo files, source code, manifests, docs, examples, releases.
3. Official ecosystem documentation or package registries.
4. Reproducible scripts, tests, or benchmark outputs.
5. Transparent secondary sources that cite primary artifacts.
6. README claims and project descriptions.
7. Stars, popularity, social proof, and model judgment.

If sources conflict, explain the conflict and what would resolve it.

#### Claim vs Implementation Check

For every important project claim that affects adoption, create a small claim check:

| Claim | Evidence source | Implementation source | Status | Caveat |
|---|---|---|---|---|

Check at least these claims when relevant:

- Supported file formats or import sources.
- Install path, trigger command, or manifest compatibility.
- Parser/adaptor coverage.
- Local/private processing versus cloud/API processing.
- Update, correction, memory, versioning, or persistence features.
- Benchmarks, tests, examples, demos, or production-readiness claims.

If README says a format or adapter is supported but the code only detects it, routes it to fallback behavior, or lacks a parser, mark the claim `PartiallySupported` or `Overstated`. This check is especially important for personal data, document analysis, and agent tools, where false confidence can waste time or risk private data.

Each `Best Match` must include at least two evidence notes when available:

- One note supporting the mechanism fit.
- One note covering a limitation, caveat, or verified absence.

Use this compact format:

```text
Evidence:
- Supported: README and SKILL.md define a runnable skill with /command entrypoint.
- PartiallySupported: README claims format X support, but parser code only implements Y/Z.
```

### Phase 6: Scorecard

Score candidates against the user's actual need, not search popularity.

Use 0-2 for `quick` searches and 0-5 for `standard`/`deep` searches. Include the raw dimensions, not only the total. For `standard` and `deep`, show sub-scores for every recommended candidate instead of only a final score.

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Mechanism fit | Different problem | Adjacent | Directly solves it |
| Evidence strength | Name/description only | README claim | Docs/code/examples confirm |
| Workflow completeness | Loose script or prompt only | Covers some adoption steps | Covers intake, run, verify, update, and recovery |
| Usability | Abandoned or unclear | Usable with caveats | Easy to try |
| Maturity | Toy/empty | Early | Active/community/proven |
| Installability | Unknown/heavy | Some setup/glue | Clear install path |
| Portability | Rewrite needed | Portable with edits | Native or mostly compatible |

For deeper GitHub selection, use a weighted score:

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

`portability` is intentionally low-weight because a useful project can be moved across agent hosts. Increase its weight only when the user explicitly requires a specific host or marketplace.

`workflow_completeness` measures whether an agent can actually carry the user from raw input to a trustworthy result. For skills and plugins, score higher when the project covers intake questions, source ingestion, chunking or parsing, analysis prompts, evidence/citation handling, user confirmation, file writing, updates/corrections, rollback/versioning, and invocation instructions.

For adapters, optionally include:

- `upstream_strength`: maturity and fit of the wrapped project.
- `adapter_quality`: clarity and robustness of the wrapper itself.
- `adapter_risk`: low adoption, stale pins, unclear data flow, or fragile setup.

These do not replace the main score; they explain why a low-star adapter may still be worth using, or why a famous upstream is not enough.

Optional repository signals:

- `activity_score`: recent commits/releases, not archived, issue health.
- `quality_score`: README/docs, license, tests/examples, dependency clarity.
- `semantic_score`: how closely README/docs match the user's mechanism.
- `adoption_score`: stars/forks/downloads, treated as secondary.

Prefer a low-star exact mechanism over a famous wrong-category project, but label maturity risk clearly.

### Phase 6.5: Adoption Classification

Classify each serious candidate by what the user should do with it now:

| Adoption Class | Meaning | Typical Next Step |
|---|---|---|
| `direct-use` | Meets the user's core need with a clear adoption path. | Try or install it first. |
| `light-adapt` | Mechanism fits, but needs small path, host, config, or prompt edits. | Try after a small adapter/change. |
| `component-use` | Solves a subproblem such as parsing, indexing, conversion, or UI. | Use inside a toolchain or custom skill. |
| `reference-only` | Not worth adopting, but useful to understand the ecosystem or design. | Keep as evidence or handoff material. |
| `near-miss` | Close but misses a decisive user constraint. | Do not prioritize unless constraints change. |
| `exclude` | Misleading, unsupported, stale, unsafe, or wrong category. | Do not use. |

Keep this separate from `Best use role`:

- `Best use role` says where the candidate sits in the solution architecture.
- `Adoption Class` says what action the user should take.

For direct recommendations, include the smallest adoption path:

```text
adoption:
- command or install path, if verified
- first sample task to try
- expected output
- known blocker or caveat
```

If no candidate reaches `direct-use` or `light-adapt`, say that plainly. Do not stretch a `component-use` or `reference-only` project into a recommendation just to have an answer.

### Phase 7: Deep-Dive Gate

Escalate from README inspection to code/dependency inspection when:

- The user will spend significant time or money based on the recommendation.
- The project claims to implement a mechanism that is easy to fake in README prose.
- The ecosystem requires a real manifest, CLI, API, MCP server, or installable skill/plugin.
- The top candidates are close and the difference matters.
- Security, privacy, local data, or high-stakes decisions are involved.

Use these evidence levels:

| Level | Name | What To Check | When Enough |
|---|---|---|---|
| L1 | Surface check | README, description, stars, updated date, license | Quick lookup or early triage |
| L2 | Mechanism check | SKILL.md, manifest, examples, docs, install commands, at least one code-search path for skill/plugin searches | Normal recommendation |
| L3 | Implementation check | Key source files, parsers, scripts, dependency files, tests, claim-vs-implementation table | Claims are easy to fake or user will adopt |
| L4 | Runtime check | Clone/install/run sample or smoke test | User asks to install/use now, or behavior is uncertain |

#### Adoption Smoke Test Gate

Do not run every candidate by default. Escalate to an L4 smoke test when at least one of these is true:

- The user wants to actually use/install/adopt the project now.
- The project is a low-star or personal project but highly matched to the user's concrete task.
- The README is empty, sparse, or mostly marketing, and the code appears to be the real evidence.
- The recommendation depends on a CLI, parser, MCP server, plugin, or script actually starting successfully.
- The project claims are easy to fake and a small sample run can verify the main mechanism.
- Top candidates are close and runtime behavior is the deciding factor.

Keep smoke tests minimal and task-shaped:

- Prefer clone/install/import/run one tiny example over broad test suites.
- Use a toy input that matches the user's likely use case.
- Avoid sending private data to external APIs during smoke tests unless the user explicitly approves and understands the boundary.
- Avoid expensive, destructive, or long-running setup. If setup is heavy, inspect install instructions and mark runtime status instead.
- If credentials, paid APIs, GPU, large models, or unavailable services are required, do not fake success; state the blocker.

Report runtime status separately from evidence status:

| Runtime Status | Meaning |
|---|---|
| `SmokeTested` | A minimal install/import/run path succeeded. |
| `PartiallySmokeTested` | Some runtime path worked, but not the full claimed workflow. |
| `RuntimeBlocked` | Could not run because of credentials, OS, dependencies, cost, network, or unavailable service. |
| `RuntimeUnverified` | No runtime check was attempted. |
| `RuntimeFailed` | A reasonable minimal run failed. |

If no smoke test is performed for a project the user may adopt, say why and label runtime status `RuntimeUnverified`. Do not treat source inspection as equivalent to runtime verification.

Deep dive can include:

- Shallow clone or file-by-file API reads.
- Inspect entry points, examples, tests, and dependency files.
- Search code for claimed adapters, commands, classes, or APIs.
- Map claims to specific files/functions when recommending integration.
- Run a minimal smoke test when the user wants to use/install the candidate now and the repo can be exercised safely.

When deep dive is not performed, say so and label affected claims `Unverified` or `ReasonableInference`. When runtime verification is not performed, label runtime status `RuntimeUnverified`.

## Optional Handoff To Design Miner

Use this only when at least one of these is true:

- No candidate is good enough for `direct-use` or `light-adapt`, but several contain useful design ideas.
- The user says they already have a skill/plugin/tool and may want to improve it.
- The user asks what can be learned from the candidates, but the current task is still primarily scouting.
- You performed architecture checks that surfaced promising patterns, but a full migration plan would exceed the scout's scope.

The handoff is a compact evidence package, not a second report. It lets a separate design-mining workflow skip broad discovery and start from already-checked candidates.

Handoff format:

```yaml
handoff_to_design_miner:
  user_intent: ""
  answer_shape: ""
  searched_queries:
    - ""
  serious_candidates:
    - repo: ""
      url: ""
      adoption_class: "direct-use|light-adapt|component-use|reference-only|near-miss|exclude"
      best_use_role: ""
      portability: ""
      checked_files:
        - ""
      verified_claims:
        - ""
      weak_or_overstated_claims:
        - ""
      promising_patterns:
        - ""
      remaining_unknowns:
        - ""
  rejected_candidates:
    - repo: ""
      reason: ""
  suggested_deep_dive_targets:
    - repo: ""
      why: ""
```

Do not include this section by default in compact lookups. Include it when it will prevent duplicated search work later.

## Red Flags

Treat these as search drift or recommendation risk:

- Results are all generic LLM frameworks when the user asked for installable skills/plugins.
- Results are all chat rooms or apps when the user asked for task/workflow tools.
- Results are all API/model orchestration when the user asked for tools that operate files or terminals.
- The search is going deep before the task direction has been checked for a broad request.
- The final answer assumes a single answer shape when the evidence points to a toolchain.
- A project generates new content when the user asked to analyze existing material, or vice versa.
- The repo name matches but README lacks install, examples, commands, manifests, or source.
- Project claims match in README, but code has no adapters, tools, docs, releases, or tests.
- README claims broad format support, but implementation only detects formats or falls back to plaintext/generic handling.
- A host-specific port has weak adoption and no meaningful changes beyond path/branding edits.
- Several repos are the same concept copied across hosts or models, but lineage is unclear.
- Stars are high but the project requires replacing the user's toolchain.
- The project is archived, stale, or depends on unavailable services.
- The recommendation would require sending private data to an unknown service without a clear privacy story.
- The answer drifts from "should the user use this project?" into "how should the user's own project be redesigned?" without the user asking for design mining.

When drift appears, explicitly pivot vocabulary and say why.

## Output Contract

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

Always include links to used sources. For each recommendation, explain the mechanism match in plain language.

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
