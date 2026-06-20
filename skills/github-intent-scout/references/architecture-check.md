# Architecture Check

Use this reference for serious candidates when README-level evidence is not enough.

## Core Rule

Architecture inspection is "验货": inspect enough to recommend, reject, mark as a component, or mark as unverified. Do not turn a scout task into a full migration or design-mining plan.

## Use When

- README claims a capability that is easy to fake or overstate.
- The user may install, run, or adapt the project.
- The candidate is a skill, plugin, MCP server, parser, adapter, agent workflow, or data/document analysis tool.
- Stars, descriptions, or AI-written README prose are the main evidence so far.

## Minimum Evidence By Shape

| Shape | Inspect At Least |
|---|---|
| `skill` | `SKILL.md`, prompt/reference files, bundled tools/scripts, examples if present |
| `plugin-mcp` | manifest/config, tool definitions, server entry point, setup instructions |
| `library-cli` | package metadata, CLI/API entry point, core parser/adapter module, example call |
| `platform` | ingest/index/query pipeline, deployment path, data boundary, auth/storage notes |
| `workflow` | procedure file, required inputs, intermediate artifacts, verification steps |
| `composite-toolchain` | role of each component and whether interfaces actually connect |

## Verification Questions

- What is the real entry point?
- What files or modules implement the advertised mechanism?
- Does it have parser/adapter/tool code, or only prompt/README prose?
- What intermediate artifacts are produced?
- What does it require from the user: credentials, host, runtime, model, database, local files?
- What parts are verified, partial, inferred, or unimplemented?

## Codex Path Check

For Codex-related claims, verify which skill path the project actually targets: `.codex/skills`, `~/.codex/skills`, `.agents/skills`, `~/.agents/skills`, or a custom path. Flag version/path ambiguity instead of treating all "Codex support" claims as equal.

## Stop Conditions

| Decision | Meaning |
|---|---|
| `Recommend` | Mechanism and adoption path are sufficiently supported. |
| `Reject` | Implementation evidence contradicts the claimed fit or adoption cost is unreasonable. |
| `Component` | It solves a useful subproblem but is not the user's full answer. |
| `ReferenceOnly` | It has design ideas but is not suitable to use. |
| `Unverified` | Evidence remains insufficient and runtime/deeper inspection is not justified yet. |

## Deep-Dive Gate

Escalate from README inspection to code/dependency inspection when:

- The user will spend significant time or money based on the recommendation.
- The project claims to implement a mechanism that is easy to fake in README prose.
- The ecosystem requires a real manifest, CLI, API, MCP server, or installable skill/plugin.
- The top candidates are close and the difference matters.
- Security, privacy, local data, or high-stakes decisions are involved.

## Evidence Levels

| Level | Name | What To Check | When Enough |
|---|---|---|---|
| L1 | Surface check | README, description, stars, updated date, license | Quick lookup or early triage |
| L2 | Mechanism check | SKILL.md, manifest, examples, docs, install commands, at least one code-search path for skill/plugin searches | Normal recommendation |
| L3 | Implementation check | Key source files, parsers, scripts, dependency files, tests, claim-vs-implementation table | Claims are easy to fake or user will adopt |
| L4 | Runtime check | Clone/install/run sample or smoke test | User asks to install/use now, or behavior is uncertain |

Deep dive can include shallow clone or file-by-file API reads, entry point inspection, examples/tests/dependency checks, code search for claimed adapters, and minimal smoke tests when safe.
