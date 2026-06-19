---
name: web-intent-scout
description: Search the open web with intent mapping, query families, source ledgers, claim checks, freshness checks, bias/risk checks, scorecards, and practical recommendations. Use when the user asks to look up, compare, verify, recommend, or evaluate websites, products, tools, services, courses, policies, institutions, news, documentation, reviews, prices, or current information, especially when broad wording, SEO results, marketing claims, privacy, cost, regional availability, or high-stakes accuracy matter. Also use for Chinese requests such as "帮我网上找", "浏览器搜一下", "查一下哪个靠谱", "找官网/价格/评价", "现在最新情况", "帮我比较这些网站/产品/工具".
---

# Web Intent Scout

## Purpose

Use this skill to find reliable web information and practical recommendations, not merely the first search results.

Core rule: search for the user's decision and evidence needs, not only the user's literal words.

Hard rule: do not answer directly from raw search results. Convert sources into source notes, source notes into claims, and claims into a final answer.

This is a web scouting and recommendation workflow. It covers open-web information, products, tools, services, courses, policies, institutions, news, documentation, reviews, and current facts. For GitHub repositories, code projects, skills, plugins, or MCP servers, prefer `github-intent-scout`.

## Search Depth

Choose the smallest depth that can support the user's decision.

| Mode | Use When | Search Rounds | Evidence Depth | Output |
|---|---|---:|---|---|
| `quick` | exact lookup, low-stakes fact, known source | 1-2 | official or primary source | compact answer |
| `standard` | normal comparison, recommendation, or verification | 2-4 | official + independent sources | short Web Scout Dossier |
| `deep` | spending money/time, privacy, health/legal/financial/policy, "latest", or high-stakes accuracy | 4+ or until convergence | source ledger, claim checks, freshness, risk/bias | full Web Scout Dossier |

Escalate from `quick` to `standard` when search results conflict, are SEO-heavy, or affect adoption. Escalate to `deep` when currentness, money, privacy, safety, or policy matters.

## Mandatory Browse Cases

Browse before answering when the user asks for:

- current/latest/today/recent information;
- prices, availability, product features, policies, schedules, laws, regulations, or news;
- recommendations that could cost time, money, privacy, or trust;
- direct quotes, links, or source attribution;
- verification of a specific webpage, institution, product, course, or claim.

## Navigation

Read references only when needed:

- `references/intent-map.md`: before searching broad or ambiguous requests.
- `references/research-brief.md`: after intent mapping and before searching, especially for standard/deep tasks.
- `references/task-type-routing.md`: when the target is a product, tool, course, policy, service, news, tutorial, institution, or high-stakes topic.
- `references/query-families.md`: before building search queries.
- `references/source-ledger.md`: before classifying sources and writing source notes.
- `references/source-credibility.md`: before ranking source strength or using a source to support a core claim.
- `references/claim-check.md`: before recommending or trusting a product/service/tool claim.
- `references/claim-ledger.md`: before final recommendations on standard/deep searches.
- `references/conflict-resolution.md`: when credible sources disagree or old/current information conflicts.
- `references/freshness-check.md`: for current, changing, policy, price, news, or product-feature searches.
- `references/risk-bias-check.md`: for products, services, courses, reviews, SEO-heavy topics, privacy, or safety.
- `references/scorecard.md`: before comparing candidates.
- `references/output-contract.md`: before final delivery.

## Workflow

### Phase 1: Intent Map

Restate the user's target in one sentence.

Build a compact intent map when wording is broad:

| Term | Possible meaning | Signals | Search vocabulary | Needed source type |
|---|---|---|---|---|

Ask up to 3 direction-setting questions only when branch choice materially changes the answer. Otherwise state assumptions and search multiple branches.

### Phase 2: Research Brief

For `standard` and `deep` work, write a compact research brief before searching:

- the user's real decision;
- the 3-7 questions that must be answered;
- the claims or facts that must be verified;
- boundaries: what not to search or over-answer;
- source types required for confidence;
- whether user clarification is necessary.

For `quick` work, include a one-line brief internally or in the answer if assumptions matter.

### Phase 3: Task Type Routing

Route the task before building queries. Different tasks need different evidence:

- products/tools: official docs, pricing, limits, user feedback, risk sources;
- policies/laws/current facts: primary sources, effective dates, jurisdiction;
- courses/services/institutions: official pages, pricing, outcomes, complaints;
- news/events: timeline, original reporting, later corrections, primary statements;
- tutorials/docs: version, environment, update date, maintainer credibility;
- high-stakes topics: primary/official sources and explicit uncertainty.

### Phase 4: Orientation Run

Use an orientation run when the request has several strong branches, such as "best AI tool", "good course", "reliable website", "document tool", "research support", or "which platform".

Orientation output is not a final ranking. It should map 2-5 likely directions, name likely wrong branches, and ask concise direction questions.

If the user explicitly says not to ask, write `Search Assumptions` and continue.

### Phase 5: Query Families

Generate search queries in families:

- `literal`: user wording;
- `mechanism`: actual function or decision need;
- `official`: official site, docs, pricing, privacy, help center;
- `comparison`: alternatives, best, review, vs;
- `user-feedback`: Reddit, Zhihu, forums, app stores, comments;
- `risk`: privacy, refund, complaint, scam, limitation, vulnerability;
- `freshness`: latest, 2026, changelog, release notes, updated;
- `regional`: China availability, Chinese support, payment, access, local alternatives.

Use Chinese and English queries when it may change the result.

### Phase 6: Source Notes And Ledger

Do not mix source types as if they have equal authority.

Track serious sources as:

- `Official`: homepage, docs, pricing, privacy policy, help center;
- `Primary`: original law/policy, official notice, paper, dataset, product docs;
- `Professional`: specialist media, standards bodies, credible reviews;
- `UserFeedback`: community posts, forums, store reviews;
- `SEO/Affiliate`: ranking pages, sponsored lists, affiliate articles;
- `RiskSource`: complaints, refund issues, security/privacy reports, outages;
- `Secondary`: summaries that cite primary sources.

For substantial searches, convert each serious source into a source note before using it:

```text
Source:
Type:
Date:
What it says:
What it proves:
What it does not prove:
Credibility:
Caveat:
```

### Phase 7: Source Credibility

Score or rank sources before using them to support core conclusions:

- `A`: official, primary, laws/regulations, standards, original papers, official docs;
- `B`: reputable professional sources, specialist reviews with methods, credible media;
- `C`: user communities, forums, app reviews, personal blogs;
- `D`: SEO listicles, affiliate pages, sponsored pages, copied summaries, unclear sources.

Use `D` sources only for discovery. Do not let a `D` source support a final claim by itself. Use `C` sources for lived experience, not product facts or legal/policy facts.

### Phase 8: Claim Ledger

For every recommendation-changing claim, compare marketing/summary claims against stronger evidence.

Examples:

- claimed supported formats vs help docs/examples;
- claimed free plan vs pricing limits;
- claimed privacy/local processing vs privacy policy/network behavior;
- claimed Chinese support vs docs/user feedback;
- claimed "best" vs independent reviews and user complaints.

Use statuses:

```text
Supported
PartiallySupported
ReasonableInference
Ambiguous
Overstated
Unsupported
StaleOrSuperseded
Unverified
Opinion
```

For substantial searches, use a claim ledger:

```text
Claim:
Supporting sources:
Conflicting sources:
Freshness:
Confidence:
Actionability:
```

### Phase 9: Conflict Resolution

When credible sources conflict, do not average them. Resolve using:

1. official/primary source;
2. current effective date or current version;
3. source proximity to the event/product/policy;
4. method transparency;
5. repeated independent confirmation;
6. user feedback pattern for lived experience only.

If the conflict cannot be resolved, say so and lower confidence.

### Phase 10: Freshness Check

Check recency when the topic can change:

- publish date and update date;
- current pricing and feature pages;
- policy/law effective date;
- product changelog or release notes;
- whether old reviews describe a replaced version.

When dates conflict, prefer current official/primary sources and explain the conflict.

### Phase 11: Risk And Bias Check

For products, services, tools, and courses, inspect:

- sponsored or affiliate bias;
- SEO listicle bias;
- missing pricing or hidden limits;
- refund/cancellation complaints;
- privacy or data-upload concerns;
- region/payment/access constraints;
- claims only repeated from the vendor.

Do not present affiliate/SEO pages as neutral proof.

### Phase 12: Score And Recommend

Score candidates against the user's decision, not search ranking.

Use relevance, source strength, freshness, evidence consistency, practical fit, risk, usability, cost clarity, and regional fit when relevant.

Then give an adoption answer:

```text
try first / use with caveats / compare before choosing / specific-use-only / avoid / unverified
```

## Output Modes

For small tasks, answer compactly:

```text
Answer
Sources checked
Why this is reliable
Caveat
Next step
```

For substantial searches, produce a `Web Scout Dossier`:

1. `Search Depth`
2. `Search Assumptions` or `Orientation Result`
3. `Intent Map`
4. `Research Brief`
5. `Task Type Routing`
6. `Query Families`
7. `Source Notes / Source Ledger`
8. `Source Credibility`
9. `Claim Ledger`
10. `Conflict Resolution`
11. `Freshness Check`
12. `Risk / Bias Check`
13. `Scorecard`
14. `Recommendation`
15. `Remaining Uncertainty`

Always include links to used sources.

## Red Flags

Treat these as search risk:

- top results are all SEO listicles;
- product pages hide pricing or limits;
- reviews are old for fast-changing tools;
- official claims have no docs or examples;
- user feedback consistently contradicts marketing;
- the answer depends on local access, payment, privacy, or legal/policy details;
- sources cite each other but no primary source.

When red flags appear, pivot queries and say what changed.

## Failure Output

Use explicit uncertainty when evidence is insufficient:

- `InsufficientEvidence`: not enough reliable sources found;
- `StaleEvidence`: sources are old for the decision;
- `ConflictingEvidence`: strong sources disagree;
- `NeedsUserConstraint`: budget, region, platform, risk tolerance, or purpose changes the answer;
- `UnverifiedCandidate`: promising but not enough evidence to recommend.

Do not force a recommendation when the evidence cannot support one.
