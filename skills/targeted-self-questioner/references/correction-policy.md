# Correction Policy

Use this when processing user answers, objections, or corrections.

## Core Rule

User correction is modeling data, not automatic truth and not a command to flatter.

## Classification

Classify each user answer:

| Class | Meaning | Action |
|---|---|---|
| `Accept` | user answer matches evidence and sharpens the claim | keep claim, improve wording |
| `Narrow` | original claim was too broad | restrict scope |
| `Downgrade` | original claim was overweighted | lower weight or move to appendix |
| `Override` | user provides clear factual correction | replace model inference |
| `Hold` | plausible but evidence is weak | mark as hypothesis |
| `Resist` | conflicts with strong evidence | keep tension visible and explain why |

## Required Output

For each correction:

```text
Original claim:
User answer:
Classification:
Reason:
Updated claim:
Weight change:
Report impact:
```

## Do Not

- Do not silently absorb user correction.
- Do not argue just because the upstream report had evidence.
- Do not promote user-preferred labels without scope and evidence.
- Do not turn a correction into a stable self-model unless it is supported or explicitly marked as user-confirmed.

## Direction Drift

If the user says the report is "not what I meant", "too shallow", "too generic", or points to a different center:

1. Identify whether this is a fact correction, weight correction, report-routing correction, or depth challenge.
2. Update claim weights before rewriting prose.
3. Ask a focused follow-up only if the correction cannot be resolved from current materials.

## Resist Case

Use `Resist` sparingly.

When resisting, write:

```text
I would not delete this claim yet because...
The evidence still supports...
But I will narrow it to...
What would fully overturn it is...
```
