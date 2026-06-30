# Project Notes

Use this reference before serious candidates enter claim checks, scoring, or adoption recommendations.

## Contents

- Core Rule
- When To Write Project Notes
- Project Note Template
- Field Guidance
- Evidence Compression Rules
- Decision Use
- Compact Output
- Project Note Quality Check

## Core Rule

A Project Note is the bridge between raw repo discovery and final recommendation. Do not score or recommend a serious candidate until its claims, evidence, caveats, and adoption path are compressed into a Project Note.

## When To Write Project Notes

Write a Project Note when:

- The candidate is a likely best match.
- The user may install, adapt, or use it.
- README claims are broad, vague, or easy to fake.
- The project handles private or local data.
- The candidate is low-star but highly relevant.
- The candidate is a wrapper or adapter around a stronger upstream.
- The candidate is one layer in a composite toolchain.

For quick lookups, a brief note is enough. For standard/deep recommendations, every serious candidate should have one.

## Project Note Template

```markdown
Project Note:
- Repo:
- URL:
- Answer shape:
- Subtype:
- Direction:
- Candidate category:
- Best use role:
- Adoption class:
- Evidence level:
- Upstream / family relationship:
- Claimed mechanism:
- Verified mechanism:
- Entry point:
- Files checked:
- Evidence strength:
- Supported claims:
- Weak / overstated claims:
- Runtime status:
- Data boundary:
- Install source:
- Security/data boundary:
- Transform semantics:
- Copy or sync only:
- Host-specific rewrite:
- Target host validation:
- Maintenance signal:
- Smallest adoption path:
- Caveat:
- Recommendation impact:
```

## Field Guidance

| Field | Use |
|---|---|
| Answer shape | Skill, plugin/MCP, library/CLI, platform, workflow, or composite-toolchain. |
| Subtype | For agent-skill ecosystem tasks: skill-pack, skill-creator, skill-converter, skill-sync, skill-manager, skill-marketplace, migrator-to-host, host-bridge, or plugin-mcp-wrapper. |
| Candidate category | Direct, Adaptable, UnderlyingTool, ReferencePattern, NearMiss, or Excluded. |
| Best use role | Core solution, host adapter, supporting component, architecture reference, inspiration-only, or exclude. |
| Adoption class | Direct-use, light-adapt, component-use, reference-only, near-miss, or exclude. |
| Evidence level | Tags such as README-verified, source-path-checked, package-metadata-checked, runtime-unverified, conflict-unresolved, path-ambiguous, or direction-ambiguous. |
| Evidence strength | Strongest evidence level and adoption-critical gaps. |
| Runtime status | SmokeTested, PartiallySmokeTested, RuntimeBlocked, RuntimeUnverified, or RuntimeFailed. |
| Direction | Source/target direction for skill migration, sync, converter, or host-bridge projects. |
| Install source | GitHub only, npm, pip, cargo/crates, Homebrew, binary release, install script, or unknown. |
| Security/data boundary | Local files only, runs install scripts, starts MCP server, may call external API, writes config/files, or unknown. |
| Transform semantics | yes/no/partial/unknown for whether content meaning is converted. |
| Copy or sync only | yes/no/partial/unknown for file movement without semantic conversion. |
| Host-specific rewrite | yes/no/unknown for target-host markers, paths, or metadata rewrite. |
| Target host validation | yes/no/unknown for checking target host rules. |
| Recommendation impact | Why this note changes ranking, caveats, or adoption action. |

## Evidence Compression Rules

- Do not repeat the whole README.
- Compress to adoption-relevant facts.
- Separate claimed mechanism from verified mechanism.
- Separate upstream strength from wrapper quality.
- Separate runtime status from source inspection.
- Mark missing evidence explicitly.
- Treat stars and topics as discovery/adoption signals, not capability proof.
- Note the data boundary when user files, private repos, logs, embeddings, or API calls matter.
- Do not imply local/privacy safety when the security/data boundary is unknown.

## Decision Use

The Project Note:

- Feeds `github-claim-ledger.md` by naming adoption-relevant claims to test.
- Feeds `scorecard.md` by summarizing verified fit, maturity, installability, and caveats.
- Feeds `adoption-classification.md` by naming the smallest realistic adoption path.
- Can feed `design-miner-handoff.md` when adoption is weak but patterns are valuable.

## Compact Output

Project Notes may be summarized instead of fully printed in compact output. When doing that, include:

```text
Deviation: Project Notes and Claim Ledger were summarized rather than fully printed to keep output compact.
```

## Project Note Quality Check

Before using a note for recommendation, verify it includes:

- Repo and URL.
- Claimed mechanism and verified mechanism.
- Files or artifacts checked.
- At least one supported claim and one caveat or missing-evidence note.
- Adoption class and smallest adoption path when the candidate may be used.
