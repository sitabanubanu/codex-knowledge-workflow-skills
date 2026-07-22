# Claim Ledger

Use this before final recommendations in standard or deep searches.

## Core Rule

Final answers should be built from checked claims, not from raw source summaries.

## Ledger Shape

```markdown
| Claim | Support | Conflict | Freshness | Confidence | Actionability |
|---|---|---|---|---|---|
```

## Fields

- `Claim`: one decision-relevant statement.
- `Support`: strongest sources that support it.
- `Conflict`: sources or facts that weaken it.
- `Freshness`: current, dated, stale, unknown, or superseded.
- `Confidence`: High, Medium, Low, or Insufficient.
- `Actionability`: what the user can do with this claim.

## Claim Granularity

Use small claims:

- "Tool X supports PDF import" is a claim.
- "Tool X is best for document analysis" is a conclusion that requires several claims.

## Confidence Rules

`High`:

- supported by official/primary source or several independent strong sources;
- current enough for the decision;
- no strong conflict.

`Medium`:

- supported, but with limits, old dates, or incomplete source coverage.

`Low`:

- weak sources, unclear dates, or source-type mismatch.

`Insufficient`:

- not enough evidence to use.

## Recommendation Rule

Do not recommend a candidate strongly unless the core claims behind that recommendation are `High` or stable `Medium`.

If a candidate looks promising but key claims are `Low` or `Insufficient`, label it `unverified` or `compare before choosing`.
