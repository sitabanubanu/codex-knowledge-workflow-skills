# GitHub Conflict Resolution

Use this reference when README, code, runtime, maintenance, popularity, wrapper, or upstream evidence conflicts.

## Core Rule

Do not average conflicts. Decide which evidence is stronger, or mark the conflict unresolved and lower recommendation confidence.

## Conflict Types

- README vs code.
- README vs runtime.
- Docs vs current release.
- High stars vs stale repo.
- Low-star adapter vs strong upstream.
- Broad format claim vs narrow parser implementation.
- Local-first claim vs API calls.
- Simple install claim vs missing dependencies.
- Fork/host-port vs original upstream.
- Examples work but production claim is overstated.

## Resolution Priority

Prefer evidence in this order:

1. Runtime result.
2. Current implementation.
3. Manifest, config, or tool schema.
4. Examples and tests.
5. Current docs and release notes.
6. README.
7. Repo metadata and stars.
8. Third-party summaries.

Use recency inside each tier. Current code can beat stale docs; a current release note can beat an old README section.

## Wrapper / Upstream Conflicts

- Score wrapper and upstream separately.
- Strong upstream does not prove wrapper quality.
- Weak wrapper does not invalidate upstream.
- If wrapper is thin but clear, classify it as `host-adapter` with adapter risk.
- If wrapper hides data boundary or version compatibility, mark a caveat.
- If the upstream is strong but host integration is weak, recommend `component-use` or a composite toolchain rather than direct-use.

## Conflict Output

```text
Conflict:
- Claim:
- Evidence A:
- Evidence B:
- Stronger evidence:
- Resolution:
- Confidence:
- Adoption impact:
- What would settle it:
```

## Resolution Table

| Conflict | Resolution |
|---|---|
| README claims parser but no parser code exists | Mark `Overstated` or `Unsupported`. |
| README lists many formats but only generic fallback exists | Mark `PartiallySupported` or `Overstated`. |
| Runtime fails but README says easy install | Prefer runtime; mark `RuntimeFailed` or `RuntimeBlocked`. |
| High stars but stale/archived repo | Treat popularity as adoption history, not current fit. |
| Low-star adapter wraps strong upstream cleanly | Keep upstream strength; label adapter maturity risk. |
| Local-first claim but code calls external APIs with user content | Mark privacy/data-boundary caveat or disqualifier. |
| Examples work but production claim is broad | Support example-level behavior; mark production claim `Overstated` or `Unverified`. |
| Fork/host-port copies upstream without meaningful changes | Map family relationship; do not double-count as independent evidence. |

## Unresolved Conflicts

If a conflict cannot be resolved:

- Do not force a strong recommendation.
- Lower confidence.
- Mark adoption class as compare-before-choosing, component-use, reference-only, or unverified as appropriate.
- Name what evidence would settle it: runtime test, source inspection, maintainer docs, release note, issue, or user constraint.

## Scorecard Impact

Evidence conflicts should affect scoring:

- Lower evidence strength when a required claim is unresolved.
- Lower installability when setup claims conflict with dependencies or runtime.
- Lower maturity/maintenance when current activity conflicts with popularity.
- Lower portability when wrapper compatibility or data boundary is unclear.
