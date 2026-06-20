# Project Evidence Strength

Use this reference when judging how much to trust GitHub project claims.

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
| Installability | Package metadata, lockfiles, install docs, first command, smoke test. |

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
