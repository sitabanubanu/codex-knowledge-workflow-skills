# GitHub Claim Ledger

Use this reference before recommending serious candidates.

## Contents

- Core Rule
- Claim Ledger Template
- Claim Types To Check
- Minimum Ledger For Best Match
- Common Claim Checks
- Link To Scoring
- Compact Output

## Core Rule

A GitHub recommendation is only as strong as the claims that survive implementation checks. The Project Note summarizes the candidate; the Claim Ledger tests the candidate; the Scorecard ranks only after the claim ledger.

## Claim Ledger Template

| Claim | Why It Matters | Claimed By | Checked Evidence | Conflict | Status | Confidence | Adoption Impact |
|---|---|---|---|---|---|---|---|

Use one row per adoption-relevant claim. Keep rows concise and link or name checked files where possible.

## Claim Types To Check

- Installability.
- Host compatibility.
- Direction for skill sync/conversion/migration.
- Supported formats.
- Parser/adapter coverage.
- Local/private vs cloud/API behavior.
- Data persistence, logs, caches, or embeddings.
- Maintenance and activity.
- Upstream dependency and wrapper quality.
- Examples/tests.
- Runtime behavior.
- License or adoption constraints.
- User workflow completeness.
- Install source and security/data boundary when adoption may run code or touch private files.

## Confidence Rules

| Confidence | Use When |
|---|---|
| `High` | Runtime or implementation evidence supports the claim, evidence is current enough, and no material conflict remains. |
| `Medium` | Implementation evidence is partial; docs/examples support the claim; runtime was not checked; or inference from files is reasonable. |
| `Low` | README-only, old docs, unclear implementation, or weak examples. |
| `Insufficient` | No meaningful evidence was found or checked. |

Do not assign `High` from README, stars, topics, or third-party summaries alone.

## Adoption Impact

Label each claim by how it affects the recommendation:

| Impact | Meaning |
|---|---|
| `required` | Must hold for the recommendation to be valid. |
| `important` | Materially changes ranking, caveats, or adoption path. |
| `caveat` | Should be disclosed but does not block adoption. |
| `nice-to-have` | Helpful but not central. |
| `disqualifier` | If false or risky, the candidate should not be recommended for this task. |

## Minimum Ledger For Best Match

Every Best Match should check at least:

- Mechanism fit.
- Install/adoption path.
- One limitation or caveat.
- Privacy/data boundary when user data matters.
- Runtime status when the user wants to use it now.

For agent skill, plugin, MCP, converter, sync, migrator, or host-bridge tasks, also check Direction, Codex path evidence, install source, security/data boundary, and whether behavior is semantic conversion or file sync.

## Status Guidance

- Use `Supported` only when implementation or runtime evidence backs the claim.
- Use `PartiallySupported` when support exists but scope is narrower than claimed.
- Use `Overstated` when README/docs exceed implementation evidence.
- Use `Unsupported` when checked files contradict the claim.
- Use `Unverified` when the claim matters but was not checked enough.
- Use `StaleOrSuperseded` when current release/commit evidence supersedes old docs.

## Common Claim Checks

| Claim | Check |
|---|---|
| "Supports format X" | Look for parser code, tests, and examples for X. |
| "MCP/plugin ready" | Check manifest, tool definitions, server entry point, setup docs. |
| "Local/private" | Check API calls, upload paths, logs, embeddings, cache behavior. |
| "Easy install" | Check package metadata, lockfiles, setup command, first run path. |
| "Actively maintained" | Check current commits, releases, issues, archived status. |
| "Wrapper for upstream Y" | Check dependency pins, supported versions, config clarity, data boundary. |
| "Codex support" | Check target path such as `.codex/skills`, `~/.codex/skills`, `.agents/skills`, or custom path. |
| "Migrates/syncs skills" | Check direction: source -> target, bidirectional, sync-only, migrator-into-host, from-host-supported, or unknown. |
| "Safe/local tool" | Check whether it reads local files, runs install scripts, starts MCP servers, calls APIs, or writes config/files. |

Code search can support these checks, but repository file inspection is the stronger evidence source. Empty or low-yield code search is a search failure to record and recover from, not proof that a claim is false or no project exists.

## Link To Scoring

Do not score a serious candidate until required and important claims have status and confidence. If a required claim is `Unverified`, `Unsupported`, or unresolved, lower confidence or change adoption class instead of forcing a recommendation.

Keep Adoption Recommendation and Evidence Level separate. A candidate can be `direct-use` while still carrying `runtime-unverified`, `path-ambiguous`, or `direction-ambiguous` evidence tags.

## Compact Output

Claim Ledger rows may be summarized instead of fully printed in compact output, but each Best Match must still show claim status, caveat, files checked, and runtime status.

Use this deviation note when rows are compressed:

```text
Deviation: Project Notes and Claim Ledger were summarized rather than fully printed to keep output compact.
```
