# Project Evidence Strength

Use this reference when judging how much to trust GitHub project claims.

## Contents

- Core Rule
- Evidence Strength Ladder
- Claim-To-Evidence Fit
- Install Source Strength
- Security/Data Boundary Signal
- Evidence Level Tags
- Search Evidence Positioning
- Weak Evidence Rules
- Evidence Strength Output
- Best Match Minimum

## Core Rule

Treat README claims, stars, names, descriptions, and search snippets as leads, not proof. Prefer runtime behavior, implementation files, interfaces, examples, and current project artifacts.

## Evidence Strength Ladder

| Strength | Evidence Type | Typical Meaning |
|---|---|---|
| `Runtime` | Smoke test, real run, import, CLI works | Behavior confirmed. |
| `Implementation` | Key source files, parser, adapter, tool code | Mechanism exists. |
| `Interface` | Manifest, config, tool schema, package metadata | Project exposes a usable entry point. |
| `ExampleTest` | Examples, tests, demos | Behavior is exercised. |
| `MaintainerDocs` | Docs, release notes, changelog | Intended use and current state. |
| `ReadmeClaim` | README feature claim | Claim only; needs verification. |
| `RepoMetadata` | Description, topics, stars, forks | Discovery or adoption signal only. |
| `ThirdParty` | Blogs, lists, summaries | Orientation only. |

Use the strongest available evidence for adoption-critical claims. Do not let popularity turn into capability proof.

## Claim-To-Evidence Fit

| Claim Type | Strong Evidence |
|---|---|
| Supported formats | Parser code, format-specific tests, examples with real files. |
| MCP/plugin support | Manifest, tool definitions, server entry point, setup path. |
| Skill support | `SKILL.md`, prompt/reference files, bundled tools/scripts. |
| Local/private processing | Code path, config, docs, privacy/data-flow notes. |
| Active maintenance | Recent commits, releases, issue activity, changelog. |
| Production readiness | Tests, examples, CI, release history, documented failure modes. |
| Upstream wrapper quality | Dependency pins, config clarity, interface docs, data boundary. |
| Installability | Package registry, release artifact, install script, package metadata, first command, smoke test. |

## Install Source Strength

For serious candidates, identify install source when adoption matters: `GitHub only`, `npm`, `pip`, `cargo/crates`, `Homebrew`, `binary release`, `install script`, or `unknown`. Registry entries, release artifacts, and install scripts are stronger installability evidence than README wording alone. `unknown` lowers installability confidence.

## Security/Data Boundary Signal

For tools, scripts, plugins, MCP servers, or private-data workflows, identify the boundary when evidence allows: `local files only`, `runs install scripts`, `starts MCP server`, `may call external API`, `writes config/files`, or `unknown`. Unknown boundary is a caveat; do not imply local/private safety without evidence.

## Evidence Labels

| Status | GitHub Meaning |
|---|---|
| `Supported` | Runtime or implementation evidence supports the claim. |
| `PartiallySupported` | Evidence supports part of the claim, with clear scope limits. |
| `ReasonableInference` | Files/docs support a cautious inference, but direct proof is missing. |
| `Ambiguous` | Credible evidence points in multiple directions. |
| `Overstated` | README/docs claim more than implementation appears to support. |
| `Unsupported` | Checked implementation fails to support the claim. |
| `StaleOrSuperseded` | Current release/commit state changes older docs or claims. |
| `Unverified` | Not enough evidence was checked. |
| `Opinion` | Judgment, preference, or recommendation rather than evidence. |

README-only claims are usually `ReasonableInference` or `Unverified` unless backed by files. Stars cannot make a claim `Supported`. Missing parser/adapter code turns broad support claims into `Overstated` or `Unsupported`.

## Evidence Level Tags

Keep adoption recommendation separate from evidence level. Adoption says how to use the project; Evidence Level says what checked evidence supports that action.

Use lightweight tags for Best Match or serious candidates:

- `README-claimed`
- `README-verified`
- `source-path-checked`
- `package-metadata-checked`
- `install-source-verified`
- `runtime-verified`
- `runtime-unverified`
- `conflict-unresolved`
- `path-ambiguous`
- `direction-ambiguous`

Do not turn these tags into a scoring system. Use only the tags that matter.

## Search Evidence Positioning

Repo search and web search can discover candidates. Repository file inspection is the main evidence source. Code search is useful for horizontal discovery and supplemental checks, but low-yield code search does not automatically lower a candidate's value.

When code search is empty, mark it as low-yield and move to repo search, file tree, README, package metadata, and source-path checks. Do not conclude that no project exists from code search alone.

When fallback loses evidence, note the loss: `runtime-unverified`, `path-ambiguous`, `install-source unknown`, or `conflict-unresolved`.

## Weak Evidence Rules

- README is not proof.
- Star count is not proof.
- A dependency in package metadata is not proof that the project uses it correctly.
- A file extension detector is not proof of real parser support.
- A demo screenshot is weaker than a runnable example or test.
- Old release notes may be stale.
- Third-party summaries are useful for orientation, not adoption-critical proof.
- Generated-looking docs require implementation checks for serious recommendations.

## Evidence Strength Output

Use this compact form in Project Notes or final evidence notes:

```text
Evidence Strength:
- Strongest evidence:
- Weakest adoption-critical evidence:
- Claims still unverified:
- Evidence gap impact:
```

## Best Match Minimum

Each Best Match should include at least:

- One mechanism-fit evidence note.
- One limitation, caveat, or verified absence.
- Runtime status when the user may actually adopt it now.
- Evidence strength label for adoption-critical claims.
