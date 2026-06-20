# Design Miner Handoff

Use this reference only when scout findings should be handed to a later design-mining workflow.

## Core Rule

The handoff is a compact evidence package, not a second report. It should let a separate design-mining workflow skip broad discovery and start from already-checked candidates.

## Handoff Triggers

Use handoff only when at least one condition is true:

- No candidate is good enough for `direct-use` or `light-adapt`, but several contain useful design ideas.
- The user says they already have a skill/plugin/tool and may want to improve it.
- The user asks what can be learned from candidates, while the current task is still primarily scouting.
- Architecture checks surfaced promising patterns, but a full migration plan would exceed scout scope.
- The user asks to learn how other projects work, borrow from similar projects, inspect architecture/bottom-level logic, or hand results to design miner.

For these trigger cases, include a brief handoff by default. Do not include it by default in compact lookups unrelated to learning or design transfer.

## Brief Handoff

Use this format in compact or dossier output:

```text
Design Miner Handoff:
- Target repo:
- Why hand off:
- Patterns to inspect:
- Weak or overstated claims:
- Remaining unknowns:
```

This is not a design migration report. Stop at the evidence package needed for design miner to continue.

## Handoff YAML Template

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

## What To Include

- Serious candidates with checked evidence.
- Rejected candidates and concise reasons.
- Suggested deep-dive targets.
- Promising patterns, not a full migration plan.
- Remaining unknowns that design mining should resolve.
