---
name: web-intent-scout
description: Search the open web with intent mapping, query families, source ledgers, claim checks, freshness checks, bias/risk checks, scorecards, and practical recommendations. Use when the user asks to look up, compare, verify, recommend, or evaluate websites, products, tools, services, courses, policies, institutions, news, documentation, reviews, prices, or current information, especially when broad wording, SEO results, marketing claims, privacy, cost, regional availability, or high-stakes accuracy matter. Also use for Chinese requests such as "帮我网上找", "浏览器搜一下", "查一下哪个靠谱", "找官网/价格/评价", "现在最新情况", "帮我比较这些网站/产品/工具".
---

# Web Intent Scout

## Purpose

Use this skill to find reliable web information and practical recommendations, not merely the first search results.

Core rule: search for the user's decision and evidence needs, not only the user's literal words.

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
- `references/query-families.md`: before building search queries.
- `references/source-ledger.md`: before ranking source credibility.
- `references/claim-check.md`: before recommending or trusting a product/service/tool claim.
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

### Phase 2: Orientation Run

Use an orientation run when the request has several strong branches, such as "best AI tool", "good course", "reliable website", "document tool", "research support", or "which platform".

Orientation output is not a final ranking. It should map 2-5 likely directions, name likely wrong branches, and ask concise direction questions.

If the user explicitly says not to ask, write `Search Assumptions` and continue.

### Phase 3: Query Families

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

### Phase 4: Source Ledger

Do not mix source types as if they have equal authority.

Track serious sources as:

- `Official`: homepage, docs, pricing, privacy policy, help center;
- `Primary`: original law/policy, official notice, paper, dataset, product docs;
- `Professional`: specialist media, standards bodies, credible reviews;
- `UserFeedback`: community posts, forums, store reviews;
- `SEO/Affiliate`: ranking pages, sponsored lists, affiliate articles;
- `RiskSource`: complaints, refund issues, security/privacy reports, outages;
- `Secondary`: summaries that cite primary sources.

### Phase 5: Claim Check

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

### Phase 6: Freshness Check

Check recency when the topic can change:

- publish date and update date;
- current pricing and feature pages;
- policy/law effective date;
- product changelog or release notes;
- whether old reviews describe a replaced version.

When dates conflict, prefer current official/primary sources and explain the conflict.

### Phase 7: Risk And Bias Check

For products, services, tools, and courses, inspect:

- sponsored or affiliate bias;
- SEO listicle bias;
- missing pricing or hidden limits;
- refund/cancellation complaints;
- privacy or data-upload concerns;
- region/payment/access constraints;
- claims only repeated from the vendor.

Do not present affiliate/SEO pages as neutral proof.

### Phase 8: Score And Recommend

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
4. `Query Families`
5. `Source Ledger`
6. `Candidate List`
7. `Claim Checks`
8. `Freshness Check`
9. `Risk / Bias Check`
10. `Scorecard`
11. `Recommendation`
12. `Remaining Uncertainty`

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
