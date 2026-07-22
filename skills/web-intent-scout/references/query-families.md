# Query Families

Use this before searching.

## Core Rule

Use query families rather than one heroic query.

## Families

| Family | Purpose | Example |
|---|---|---|
| `literal` | user's words | `"AI PDF reader"` |
| `mechanism` | function or mechanism | `"PDF question answering citations"` |
| `official` | primary product or institution pages | `"product name pricing official"` |
| `comparison` | alternatives and category map | `"product name alternatives"` |
| `user-feedback` | real user experience | `"product name reddit review"` |
| `risk` | complaints, privacy, refund, scam, limitations | `"product name privacy policy"` |
| `freshness` | current state | `"product name changelog 2026"` |
| `regional` | local constraints | `"product name China access Chinese support"` |

## Language Strategy

Use both Chinese and English when:

- Chinese access, payment, policy, or local alternatives matter;
- English docs are more authoritative;
- user feedback differs by region;
- the product has separate domestic and international versions.

## Pivot Rules

If results drift:

- from tools to marketing lists: add `official`, `docs`, `pricing`, `privacy`;
- from official pages to praise only: add `complaint`, `refund`, `limitations`, `reddit`, `知乎`;
- from old results: add year, `latest`, `changelog`, `release notes`;
- from broad category to wrong use case: add mechanism terms and exclusions.

Record useful pivots in the final answer for substantial searches.
