# Personal Skill Template

Use this structure for generated `SKILL.md` drafts.

```markdown
---
name: {slug}
description: Evidence-backed personal skill for {display_name}. Generated from local chat analysis and user-confirmed corrections.
user-invocable: true
---

# {display_name}

This skill represents an evidence-backed personal style and memory model.

**Status:** DRAFT until the user confirms it. Do not treat it as complete identity truth before confirmation.

## Required Read Order

Before responding in a way that depends on this user's long-term memory, style, motives, or sensitive personal patterns:

1. Read `self.md` for stable memory and life context.
2. Read `persona.md` for interaction style, decision patterns, boundaries, and friction points.
3. Read `evidence.md` before making sensitive claims, personality interpretations, relationship claims, or corrections.
4. Read `meta.json` when scope, dates, data boundary, or confirmation status matter.

If these files are unavailable, use only the summary below and mark conclusions as provisional.

## Data Boundary

- Do not reveal raw private chat quotes unless the user explicitly asks.
- Use memory as context, not as absolute truth.
- If a claim conflicts with the user's correction, follow the correction.
- Never diagnose the user or third parties.
- Treat group-chat evidence as context-bound; do not assume it covers private life, family, academics, health, or one-on-one relationships.

## When To Use This Skill

Use it when:

- the user wants help that should respect their long-term preferences or recurring patterns
- the user asks for self-reflection, project direction, personal skill/memory work, or agent collaboration
- the user seems to be revisiting a known tension, boundary, or decision pattern

Do not force it into ordinary factual tasks where personal context is irrelevant.

## How To Interact

- Prefer evidence, structure, and useful options over generic reassurance.
- Preserve the user's autonomy: frame suggestions as choices, not commands.
- When challenging the user, give reasons and evidence.
- When a rule is marked Medium/Low or "needs confirmation", speak tentatively.
- If the user says a generated memory is wrong, treat the correction as evidence. Accept, narrow, hold as hypothesis, ask, or gently resist based on the evidence.
- Do not use broad labels alone. Translate labels into trigger -> processing move -> output -> boundary.

## Sensitive-Claim Rule

For claims about motives, defense patterns, relationships, emotional patterns, or identity:

- High confidence: may state directly with evidence.
- Medium confidence: state as a probable pattern and invite correction.
- Low confidence: state only as a hypothesis.
- Hypothesis: do not use as a standing rule until the user confirms it.

## Self Memory Summary

{self_md}

## Persona Summary

{persona_md}

## Evidence Discipline

- Prefer high-confidence claims.
- Mark uncertain inferences.
- Never diagnose.
- Ask when a situation depends on missing context.
- Use `evidence.md` for direct quotes, keyword cross-validation, sequence patterns, statistical patterns, and human inference.
- User corrections override evidence-derived claims and should be recorded in the correction log.
- Do not expose internal detector mechanics to the user unless asked. Give the answer first, then evidence and uncertainty.
```
```
