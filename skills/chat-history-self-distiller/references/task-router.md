# Task Router

Route the user's request before deep analysis. The route decides which files to read, which claims are allowed, and what output shape is appropriate.

## Routes

| Route | User Wants | Minimum Evidence | Output |
|---|---|---|---|
| `orientation` | "Can this data answer my question?" | structure + stats | data map and next questions |
| `profile` | understand one person | per-sender samples + cross-time evidence | evidence-backed portrait |
| `relationship` | understand two or more people | profiles for all sides + interaction samples | relationship dynamics |
| `theme-evolution` | recurring topics or changes over time | monthly/quarterly samples | theme timeline |
| `conflict-review` | contradictions, unresolved tensions, inconsistent statements | paired claims with sources | conflict table |
| `duplication-review` | repeated topics or duplicated content | similarity or repeated phrase evidence | repetition map |
| `timeline` | what happened and when | dated records | chronological timeline |
| `claim-extraction` | facts, promises, preferences, decisions | direct quotes or document spans | claim ledger |
| `paper-report-review` | analyze papers, reports, policies, or long docs | document map + section evidence | structured document review |
| `deep-self-skill` | generate reusable self/persona skill | high-confidence profile + user confirmation | draft skill files |

## Direction Check

Ask or run orientation first when these choices materially change the result:

- person profile vs. relationship dynamics
- personal self-analysis vs. generic document analysis
- summary vs. contradiction checking
- single document vs. multi-document comparison
- quick answer vs. reusable skill generation
- local/private only vs. external conversion allowed

## Route Rules

- Do not run `deep-self-skill` unless the user explicitly wants a reusable personal skill or long-term memory.
- Do not present third-party profiles as complete truths; keep them context-bound.
- Do not use a profile template for papers, reports, or policy documents. Use `paper-report-review`.
- For broad requests, deliver `orientation` first, then ask the user which branch to deepen.

## Output Templates

### Profile

- footprint
- speech style
- judgment priority
- motivation
- defense pattern
- growth trajectory
- tension
- evidence table

### Relationship

- participants and data coverage
- interaction rhythm
- support/conflict patterns
- asymmetries
- unspoken or unresolved themes, if evidence supports them
- privacy notes

### Theme Evolution

- theme
- early/middle/recent expression
- representative quotes
- strength and confidence
- open questions

### Paper / Report Review

- document map
- main claims
- evidence and methods
- assumptions
- gaps
- contradictions or inconsistencies
- action summary
