# Final Report Template

Use this before writing a calibrated final report.

## Core Rule

The final report is not a merged column summary. It is a structured record of the questions that changed the model.

Use question-driven sections.

## Main Report Shape

```markdown
# Calibrated Self Report

## 0. Report Basis
- Upstream source:
- User answers used:
- Weighting rule:
- Important boundaries:

## 1. [Core Question]

Short answer:

Why this question matters:

Initial judgment:

Key evidence:

User correction:

Weight change:

Final judgment:

Action impact:

## 2. [Core Question]
...

## User Calibration Record
| Original Claim | User Correction | Classification | Change |
|---|---|---|---|

## Low-Weight Episodes And Over-Interpretation Risks

## Action Implications

## Final Synthesis
```

## Section Count

Use 5-7 main questions for a full report.

Use 3-5 for brief reports.

Move lower-weight material to appendices.

## Do Not Over-Mechanize

Use the full chain only for high-weight sections:

```text
Question -> initial judgment -> evidence -> user correction -> weight change -> final judgment
```

For lower-weight sections, compress:

```text
This remains a secondary line because...
```

## Report Routing

Adapt questions to the evidence center of gravity:

- relationship-heavy: questions about repeated relationship loops;
- work-heavy: questions about execution, ability, constraints;
- creation-heavy: questions about output path and tool use;
- family-heavy: questions about role and boundaries;
- mixed: questions about current dominant line, historical root, and secondary lines.

## Final Synthesis

The final synthesis should come after the question sections, not before them.

It should summarize:

- what is now confirmed;
- what was downgraded;
- what remains uncertain;
- what the person should do next.
