# Task Type Routing

Use this before query planning.

## Core Rule

Different web tasks require different evidence. Do not run every request through one generic search pattern.

## Routes

| Route | Use For | Required Evidence | Extra Checks |
|---|---|---|---|
| `product-tool` | software, AI tools, apps, devices | official docs, pricing, limits, changelog, user feedback | privacy, lock-in, region, maintenance |
| `current-fact` | latest info, current status, prices, schedules | official/current source | timestamp, update date, replacement notices |
| `policy-law` | law, school/company policy, government rules | primary official text | jurisdiction, effective date, summary-vs-primary mismatch |
| `course-learning` | courses, tutorials, bootcamps | curriculum, instructor, date, price/refund, outcomes | outdated content, marketing claims |
| `service-institution` | agencies, platforms, schools, clinics, vendors | official service details, pricing, reviews, complaints | cancellation, dispute history, local availability |
| `news-event` | event explanation, timeline, controversy | original reporting, primary statements, later corrections | rumor, partisan framing, date order |
| `documentation` | technical docs, APIs, how-to | official docs, examples, versioned pages | version mismatch, deprecated APIs |
| `high-stakes` | medical, legal, financial, safety | primary/official authoritative sources | explicit uncertainty, no overconfident advice |

## Route Output

For standard/deep searches, include:

```text
Task Route:
Required evidence:
Disqualifying gaps:
Extra risk checks:
```

## Disqualifying Gaps

Use these to avoid weak recommendations:

- no official source for a product fact;
- no current source for a changing fact;
- no jurisdiction for policy/legal claims;
- only SEO pages support the recommendation;
- user reviews show repeated severe failure;
- pricing, privacy, or cancellation is hidden.
