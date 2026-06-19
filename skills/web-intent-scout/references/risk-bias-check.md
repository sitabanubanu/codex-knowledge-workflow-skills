# Risk And Bias Check

Use this for products, services, courses, tools, reviews, shopping, privacy, or safety-sensitive searches.

## Bias Types

| Bias | Signal |
|---|---|
| sponsored | ad labels, paid placement, promotional wording |
| affiliate | tracking links, "best X" pages monetized by referrals |
| SEO | generic ranking pages with shallow testing |
| vendor echo | multiple pages repeat vendor claims without testing |
| stale review | review describes old UI/pricing/features |
| region mismatch | product works in one country but not user region |

## Risk Areas

Check:

- privacy and data upload;
- hidden limits or unclear pricing;
- refund/cancellation complaints;
- account lock-in and export limits;
- regional access and payment;
- safety/legal/health/financial implications;
- user complaints about reliability.

## Output Shape

```markdown
## Risk / Bias Check

| Risk | Evidence | Severity | Practical Impact |
|---|---|---|---|
```

Severity:

- `High`: could waste money, expose private data, violate rules, or cause serious harm;
- `Medium`: important caveat before adoption;
- `Low`: minor preference or inconvenience.

## Rule

Do not recommend a paid, privacy-sensitive, or high-stakes option without naming the main risk and how the user should verify it.
