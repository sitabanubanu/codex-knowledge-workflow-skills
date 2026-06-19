# Scorecard

Use this before comparing candidates.

## Standard Criteria

Score 0-5 when comparing serious candidates:

| Criterion | Meaning |
|---|---|
| `Relevance` | matches user task and constraints |
| `Source Strength` | supported by official/primary/credible sources |
| `Freshness` | current enough for the decision |
| `Evidence Consistency` | sources agree or conflicts are explained |
| `Practical Fit` | region, language, platform, budget, workflow |
| `Risk` | privacy, cost, safety, reliability risk; higher score means lower risk |
| `Usability` | easy to start and understand |
| `Cost Clarity` | pricing and limits are clear |

Optional:

- `Chinese Support`
- `Local Availability`
- `Privacy`
- `Export Ability`
- `Free Trial`
- `Professional Fit`

## Weighted Default

```text
total =
  relevance * 0.25 +
  source_strength * 0.20 +
  freshness * 0.15 +
  evidence_consistency * 0.10 +
  practical_fit * 0.10 +
  risk * 0.10 +
  usability * 0.05 +
  cost_clarity * 0.05
```

Adjust weights when the user states priorities.

## Adoption Classes

| Class | Meaning |
|---|---|
| `try-first` | best practical first option |
| `use-with-caveats` | useful but check named risks |
| `compare-before-choosing` | close candidate, not clear winner |
| `specific-use-only` | good for one narrow scenario |
| `avoid` | not recommended for this task |
| `unverified` | insufficient evidence |

Do not make a top recommendation without at least one caveat or limit.
