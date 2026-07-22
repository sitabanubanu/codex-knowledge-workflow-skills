# Source Credibility

Use this before allowing a source to support a core conclusion.

## Core Rule

Source strength depends on what the claim is.

Official docs are strong for product features, but weak for lived user experience. Forums are useful for pain patterns, but weak for legal or pricing facts.

## Credibility Levels

| Level | Source | Can Support |
|---|---|---|
| `A` | official docs, official pricing, primary law/policy, regulator notice, original paper, standard, dataset | core factual claims |
| `B` | reputable specialist media, named expert review, standards body explainer, credible benchmark | context and independent evaluation |
| `C` | forums, Reddit, Zhihu, app reviews, issue threads, personal blogs | user pain, reliability patterns, edge cases |
| `D` | SEO listicles, affiliate articles, sponsored rankings, copied summaries, unclear authorship | discovery only |

## Claim-To-Source Fit

| Claim Type | Preferred Source |
|---|---|
| price, free plan, limits | official pricing/docs |
| current version/features | official docs, changelog, release notes |
| law/policy | primary legal/policy text |
| reliability/usability | repeated user feedback + issue patterns |
| security/privacy | privacy policy, security docs, audits, incident reports |
| academic/scientific claim | papers, systematic reviews, official datasets |
| institution facts | official institution pages and official notices |

## Scoring Heuristic

Use a simple score when ranking many sources:

```text
A = 85-100
B = 65-85
C = 40-70
D = 0-45
```

Adjust upward for:

- current date;
- transparent method;
- direct access to primary data;
- named author or accountable organization;
- multiple independent confirmations.

Adjust downward for:

- no date;
- obvious affiliate incentive;
- anonymous authorship;
- copied claims without citations;
- stale content;
- mismatch between source type and claim type.

## Hard Rules

- A `D` source cannot support a final recommendation alone.
- A `C` source cannot override official facts unless there is a repeated real-world failure pattern.
- A stale `A` source can be weaker than a current `A` source.
- When source strength and recency conflict, explain the tradeoff.
