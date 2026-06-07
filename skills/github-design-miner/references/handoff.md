# Scout Handoff

Use this when the user already ran `github-intent-scout` or provides a handoff block.

## Expected Shape

```yaml
handoff_to_design_miner:
  user_intent: ""
  answer_shape: ""
  searched_queries:
    - ""
  serious_candidates:
    - repo: ""
      url: ""
      adoption_class: ""
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

## How To Use It

- Treat `serious_candidates` as seed references, not final truth.
- Start with `suggested_deep_dive_targets` if present.
- Reuse `checked_files`; do not re-read broad README material unless needed.
- Deepen `promising_patterns` by inspecting implementation files.
- Use `weak_or_overstated_claims` as claim-check targets.
- Use `remaining_unknowns` to guide focused code search.

## When To Search Again

Search again only when:

- the handoff has fewer than 2 useful references
- the user's improvement goal changed
- the handoff is stale for fast-moving tools
- the checked evidence does not cover architecture
- the current project needs a pattern family not represented in the handoff

## Handoff Output Back To User

When using a handoff, say:

- which candidates were reused
- which broad search steps were skipped
- what evidence still needed deeper inspection
